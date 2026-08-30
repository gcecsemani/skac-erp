"""Sales / POS: create finalized invoices and reconcile offline outbox."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.customer import Customer
from app.models.enums import PaymentMode
from app.models.organization import Branch
from app.models.sales import Invoice
from app.schemas.sales import InvoiceCreate, InvoiceOut, SyncInvoicesRequest
from app.services import billing
from app.services.inventory import InsufficientStock, describe_shortfall

router = APIRouter(prefix="/sales", tags=["sales"])


def _branch_address(b: Branch | None) -> str | None:
    if b is None:
        return None
    parts = [p for p in [b.address_line1, b.address_line2, b.city, b.district, b.state, b.pincode] if p]
    return ", ".join(parts) or None


def _invoice_out(inv: Invoice) -> InvoiceOut:
    data = InvoiceOut.model_validate(inv)
    b = getattr(inv, "branch", None)
    c = getattr(inv, "customer", None)
    org = getattr(b, "organization", None) if b is not None else None
    return data.model_copy(update={
        "branch_name": b.name if b is not None else None,
        "branch_code": b.code if b is not None else None,
        "branch_phone": b.phone if b is not None else None,
        "branch_gstin": b.gstin if b is not None else None,
        "branch_address": _branch_address(b),
        "branch_fco_license": b.fco_license_no if b is not None else None,
        "branch_pesticide_license": b.pesticide_license_no if b is not None else None,
        "branch_seed_license": b.seed_license_no if b is not None else None,
        "organization_name": org.name if org is not None else None,
        "thermal_paper_mm": (b.thermal_paper_mm if b is not None else None) or 80,
        "printer_name": b.printer_name if b is not None else None,
        "printer_type": b.printer_type if b is not None else None,
        "customer_name": c.name if c is not None else None,
        "customer_phone": c.phone if c is not None else None,
        "customer_village": c.village if c is not None else None,
    })


def _invoice_load():
    return (
        selectinload(Invoice.items),
        joinedload(Invoice.branch).joinedload(Branch.organization),
        joinedload(Invoice.customer),
    )


def _to_input(payload: InvoiceCreate) -> billing.InvoiceInput:
    return billing.InvoiceInput(
        branch_id=payload.branch_id,
        customer_id=payload.customer_id,
        payment_mode=payload.payment_mode,
        tax_type=payload.tax_type,
        invoice_date=payload.invoice_date,
        amount_paid=payload.amount_paid,
        client_uuid=payload.client_uuid,
        lines=[
            billing.LineInput(
                product_id=l.product_id,
                quantity=l.quantity,
                unit_price=l.unit_price,
                discount=l.discount,
                unit=l.unit,
            )
            for l in payload.lines
        ],
    )


@router.post("/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(
    payload: InvoiceCreate,
    current: CurrentUser = Depends(require_permission(rbac.P_SALE_CREATE)),
    db: Session = Depends(get_db),
) -> Invoice:
    current.assert_branch_access(payload.branch_id)
    try:
        invoice = billing.create_and_finalize(
            db,
            organization_id=current.organization_id,
            data=_to_input(payload),
            created_by_user_id=current.id,
        )
    except InsufficientStock as exc:
        raise HTTPException(status_code=409, detail=describe_shortfall(db, exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    record_audit(
        db, action="create", entity_type="invoice", entity_id=invoice.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=invoice.branch_id, changes={"grand_total": str(invoice.grand_total)},
    )
    db.commit()
    db.refresh(invoice)
    invoice = db.execute(
        select(Invoice).options(*_invoice_load()).where(Invoice.id == invoice.id)
    ).unique().scalar_one()
    return _invoice_out(invoice)


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    branch_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    search: str | None = None,
    payment_mode: PaymentMode | None = None,
    unpaid_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InvoiceOut]:
    today = date.today()
    start = start or today.replace(day=1)
    end = end or today
    stmt = (
        select(Invoice)
        .options(*_invoice_load())
        .where(
            Invoice.organization_id == current.organization_id,
            Invoice.invoice_date >= start,
            Invoice.invoice_date <= end,
        )
    )
    if branch_id is not None:
        current.assert_branch_access(branch_id)
        stmt = stmt.where(Invoice.branch_id == branch_id)
    elif not current.sees_all_branches:
        stmt = stmt.where(Invoice.branch_id.in_(current.branch_ids or [-1]))
    if payment_mode is not None:
        stmt = stmt.where(Invoice.payment_mode == payment_mode)
    if unpaid_only:
        stmt = stmt.where(Invoice.grand_total > Invoice.amount_paid)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.outerjoin(Customer, Customer.id == Invoice.customer_id).where(
            or_(
                Invoice.invoice_no.ilike(like),
                Customer.name.ilike(like),
                Customer.phone.ilike(like),
            )
        )
    stmt = stmt.order_by(Invoice.id.desc()).limit(limit)
    return [_invoice_out(inv) for inv in db.scalars(stmt).unique().all()]


@router.get("/invoices/find", response_model=list[InvoiceOut])
def find_invoices(
    q: str = Query(""),
    limit: int = Query(12, ge=1, le=50),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InvoiceOut]:
    """Lookup by printed invoice no (AVL/2026-27/00003), numeric id, or farmer name. Not date-filtered."""
    needle = q.strip()
    stmt = (
        select(Invoice)
        .options(*_invoice_load())
        .outerjoin(Customer, Invoice.customer_id == Customer.id)
        .where(Invoice.organization_id == current.organization_id)
    )
    if needle:
        like = f"%{needle}%"
        conds = [
            Invoice.invoice_no.ilike(like),
            Customer.name.ilike(like),
        ]
        if needle.isdigit():
            conds.append(Invoice.id == int(needle))
        stmt = stmt.where(or_(*conds))
    if not current.sees_all_branches:
        stmt = stmt.where(Invoice.branch_id.in_(current.branch_ids or [-1]))
    stmt = stmt.order_by(Invoice.id.desc()).limit(limit)
    return [_invoice_out(inv) for inv in db.scalars(stmt).unique().all()]


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceOut:
    invoice = db.execute(
        select(Invoice).options(*_invoice_load()).where(Invoice.id == invoice_id)
    ).unique().scalar_one_or_none()
    if invoice is None or invoice.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    current.assert_branch_access(invoice.branch_id)
    return _invoice_out(invoice)


@router.post("/sync", response_model=list[InvoiceOut])
def sync_offline_invoices(
    payload: SyncInvoicesRequest,
    current: CurrentUser = Depends(require_permission(rbac.P_SALE_CREATE)),
    db: Session = Depends(get_db),
) -> list[InvoiceOut]:
    """Reconcile a branch's offline outbox. Idempotent per client_uuid.

    Offline sales are honoured even if they would oversell (a finalized farmer
    invoice is never silently voided); overselling surfaces as negative stock
    for reconciliation rather than a hard rejection.
    """
    ids: list[int] = []
    for item in payload.invoices:
        current.assert_branch_access(item.branch_id)
        invoice = billing.create_and_finalize(
            db,
            organization_id=current.organization_id,
            data=_to_input(item),
            created_by_user_id=current.id,
            allow_oversell=True,
        )
        ids.append(invoice.id)
    db.commit()
    rows = db.scalars(
        select(Invoice).options(*_invoice_load()).where(Invoice.id.in_(ids))
    ).unique().all()
    by_id = {r.id: r for r in rows}
    return [_invoice_out(by_id[i]) for i in ids if i in by_id]
