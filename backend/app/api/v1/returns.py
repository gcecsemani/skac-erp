"""Sales returns issued as immutable credit notes (restocks + ledger reversal)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.customer import Customer
from app.models.enums import MovementType
from app.models.product import Product
from app.models.returns import CreditNote, CreditNoteItem
from app.models.sales import Invoice, InvoiceItem
from app.services import accounting, inventory as inv

router = APIRouter(prefix="/returns", tags=["returns"])

TWO = Decimal("0.01")


class ReturnItemIn(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0)


class CreditNoteIn(BaseModel):
    invoice_id: int
    reason: str | None = Field(default=None, min_length=3)
    items: list[ReturnItemIn] = Field(min_length=1)


@router.get("")
def list_credit_notes(
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    stmt = select(CreditNote).where(
        CreditNote.organization_id == current.organization_id
    ).order_by(CreditNote.id.desc())
    if not current.sees_all_branches:
        stmt = stmt.where(CreditNote.branch_id.in_(current.branch_ids or [-1]))
    notes = db.scalars(stmt).all()
    invoice_ids = [c.invoice_id for c in notes]
    invoice_nos: dict[int, str] = {}
    if invoice_ids:
        rows = db.execute(select(Invoice.id, Invoice.invoice_no).where(Invoice.id.in_(invoice_ids))).all()
        invoice_nos = {row.id: row.invoice_no for row in rows}
    return [
        {"id": c.id, "note_no": c.note_no, "invoice_id": c.invoice_id,
         "invoice_no": invoice_nos.get(c.invoice_id),
         "date": c.note_date.isoformat(), "reason": c.reason, "total": float(c.total)}
        for c in notes
    ]


@router.post("", status_code=201)
def create_credit_note(
    payload: CreditNoteIn,
    current: CurrentUser = Depends(require_permission(rbac.P_SALE_CANCEL)),
    db: Session = Depends(get_db),
) -> dict:
    invoice = db.get(Invoice, payload.invoice_id)
    if invoice is None or invoice.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    current.assert_branch_access(invoice.branch_id)

    note = CreditNote(
        organization_id=current.organization_id, branch_id=invoice.branch_id,
        invoice_id=invoice.id, customer_id=invoice.customer_id,
        created_by_user_id=current.id, note_date=date.today(), reason=payload.reason,
    )
    db.add(note)
    db.flush()

    total = taxable_total = tax_total = Decimal("0")
    for it in payload.items:
        line = db.scalar(select(InvoiceItem).where(
            InvoiceItem.invoice_id == invoice.id, InvoiceItem.product_id == it.product_id))
        if line is None:
            raise HTTPException(status_code=400,
                                detail=f"Product {it.product_id} not on invoice")
        if it.quantity <= 0 or it.quantity > line.quantity:
            raise HTTPException(status_code=400, detail="Invalid return quantity")

        taxable = (it.quantity * line.unit_price).quantize(TWO)
        tax = (taxable * line.gst_rate / Decimal("100")).quantize(TWO)
        line_total = (taxable + tax).quantize(TWO)

        note.items.append(CreditNoteItem(
            product_id=it.product_id, batch_id=line.batch_id,
            product_name=line.product_name, quantity=it.quantity,
            unit_price=line.unit_price, tax_amount=tax, line_total=line_total,
        ))
        # Restock returned goods to the originating batch.
        if line.batch_id:
            inv.receive_stock(
                db, organization_id=current.organization_id, branch_id=invoice.branch_id,
                product_id=it.product_id, batch_id=line.batch_id, quantity=it.quantity,
                movement_type=MovementType.sale_return, ref_type="credit_note", ref_id=note.id)
        total += line_total
        taxable_total += taxable
        tax_total += tax

    note.total = total
    count = db.scalar(select(func.count(CreditNote.id)).where(
        CreditNote.organization_id == current.organization_id)) or 0
    note.note_no = f"CN/{date.today().year}/{count:05d}"

    # Reduce farmer outstanding + reverse the ledger.
    if invoice.customer_id:
        customer = db.get(Customer, invoice.customer_id)
        if customer is not None:
            customer.outstanding_balance = customer.outstanding_balance - total
    accounting.post_credit_note(
        db, organization_id=current.organization_id, branch_id=invoice.branch_id,
        entry_date=note.note_date, credit_note_id=note.id,
        taxable=taxable_total, tax=tax_total, total=total)

    record_audit(db, action="create", entity_type="credit_note", entity_id=note.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 branch_id=invoice.branch_id, changes={"total": str(total)})
    db.commit()
    return {"id": note.id, "note_no": note.note_no, "total": float(total)}
