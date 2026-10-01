"""Sales returns issued as immutable credit notes (restocks + ledger reversal)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.core.units import billed_to_stock_qty
from app.models.customer import Customer
from app.models.enums import MovementType
from app.models.organization import Branch
from app.models.product import Product
from app.models.returns import CreditNote, CreditNoteItem
from app.models.sales import Invoice, InvoiceItem
from app.services import accounting, inventory as inv

router = APIRouter(prefix="/returns", tags=["returns"])

TWO = Decimal("0.01")
DIGITAL_REFUND = {"upi", "card", "bank"}


def split_return_amounts(
    *,
    grand_total: Decimal,
    amount_paid: Decimal,
    prior_credits: Decimal,
    return_total: Decimal,
    outstanding: Decimal | None,
) -> tuple[Decimal, Decimal]:
    """Split a return into khata reduction and a till refund.

    Outstanding stays at or above zero. Money the farmer already paid is
    refunded instead of being stored as a negative balance.
    """
    unpaid = (Decimal(grand_total) - Decimal(amount_paid) - Decimal(prior_credits)).quantize(TWO)
    if unpaid < 0:
        unpaid = Decimal("0")
    if outstanding is None:
        khata = Decimal("0")
    else:
        room = Decimal(outstanding) if Decimal(outstanding) > 0 else Decimal("0")
        khata = min(Decimal(return_total), unpaid, room)
    khata = khata.quantize(TWO)
    refund = (Decimal(return_total) - khata).quantize(TWO)
    return khata, refund


def _refund_mode(invoice: Invoice) -> str:
    mode = invoice.payment_mode.value if hasattr(invoice.payment_mode, "value") else str(invoice.payment_mode or "")
    mode = mode.lower()
    tenders = list(getattr(invoice, "tenders", None) or [])
    kinds = {str(t.mode).lower() for t in tenders if Decimal(t.amount or 0) > 0}
    if kinds == {"upi"} or (not kinds and mode == "upi"):
        return "upi"
    if kinds == {"card"} or (not kinds and mode == "card"):
        return "card"
    if mode in DIGITAL_REFUND and (not kinds or kinds == {mode}):
        return mode
    return "cash"


class ReturnItemIn(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0)


class CreditNoteIn(BaseModel):
    invoice_id: int
    reason: str | None = Field(default=None, min_length=3)
    items: list[ReturnItemIn] = Field(min_length=1)


@router.get("")
def list_credit_notes(
    search: str | None = None,
    branch_id: int | None = None,
    on: date | None = None,
    limit: int = Query(200, ge=1, le=1000),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = (
        select(CreditNote, Invoice.invoice_no, Customer.name, Customer.village, Customer.phone, Branch.name)
        .outerjoin(Invoice, Invoice.id == CreditNote.invoice_id)
        .outerjoin(Customer, Customer.id == CreditNote.customer_id)
        .outerjoin(Branch, Branch.id == CreditNote.branch_id)
        .where(CreditNote.organization_id == current.organization_id)
        .order_by(CreditNote.id.desc())
    )
    if branch_id is not None:
        current.assert_branch_access(branch_id)
        stmt = stmt.where(CreditNote.branch_id == branch_id)
    elif not current.sees_all_branches:
        stmt = stmt.where(CreditNote.branch_id.in_(current.branch_ids or [-1]))
    if on is not None:
        stmt = stmt.where(CreditNote.note_date == on)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(
            CreditNote.note_no.ilike(like),
            CreditNote.reason.ilike(like),
            Invoice.invoice_no.ilike(like),
            Customer.name.ilike(like),
            Customer.phone.ilike(like),
            Customer.village.ilike(like),
        ))
    rows = db.execute(stmt.limit(limit)).all()
    return [
        {
            "id": c.id, "note_no": c.note_no, "invoice_id": c.invoice_id,
            "invoice_no": invoice_no,
            "customer_name": farmer_name,
            "customer_village": village,
            "customer_phone": phone,
            "branch_id": c.branch_id,
            "branch_name": branch_name,
            "date": c.note_date.isoformat(), "reason": c.reason, "total": float(c.total),
        }
        for c, invoice_no, farmer_name, village, phone, branch_name in rows
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
        # Restock returned goods to the originating batch (pack qty).
        if line.batch_id:
            product = db.get(Product, it.product_id)
            stock_qty = billed_to_stock_qty(product, it.quantity, line.unit) if product else it.quantity
            inv.receive_stock(
                db, organization_id=current.organization_id, branch_id=invoice.branch_id,
                product_id=it.product_id, batch_id=line.batch_id, quantity=stock_qty,
                movement_type=MovementType.sale_return, ref_type="credit_note", ref_id=note.id)
        total += line_total
        taxable_total += taxable
        tax_total += tax

    note.total = total
    count = db.scalar(select(func.count(CreditNote.id)).where(
        CreditNote.organization_id == current.organization_id)) or 0
    note.note_no = f"CN/{date.today().year}/{count:05d}"

    prior = db.scalar(select(func.coalesce(func.sum(CreditNote.total), 0)).where(
        CreditNote.invoice_id == invoice.id, CreditNote.id != note.id,
    )) or Decimal("0")
    customer = db.get(Customer, invoice.customer_id) if invoice.customer_id else None
    khata, refund = split_return_amounts(
        grand_total=invoice.grand_total,
        amount_paid=invoice.amount_paid,
        prior_credits=Decimal(prior),
        return_total=total,
        outstanding=None if customer is None else Decimal(customer.outstanding_balance or 0),
    )
    note.khata_amount = khata
    note.refund_amount = refund
    note.refund_mode = _refund_mode(invoice) if refund > 0 else None
    if customer is not None and khata > 0:
        customer.outstanding_balance = (Decimal(customer.outstanding_balance or 0) - khata).quantize(TWO)
    accounting.post_credit_note(
        db, organization_id=current.organization_id, branch_id=invoice.branch_id,
        entry_date=note.note_date, credit_note_id=note.id,
        taxable=taxable_total, tax=tax_total, total=total,
        khata_amount=khata, refund_amount=refund, refund_mode=note.refund_mode or "cash")

    record_audit(db, action="create", entity_type="credit_note", entity_id=note.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 branch_id=invoice.branch_id, changes={"total": str(total)})
    db.commit()
    return {
        "id": note.id,
        "note_no": note.note_no,
        "total": float(total),
        "khata_amount": float(khata),
        "refund_amount": float(refund),
        "refund_mode": note.refund_mode,
        "outstanding_balance": float(customer.outstanding_balance) if customer is not None else None,
    }
