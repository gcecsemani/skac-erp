"""Farmer / customer master."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.customer import Customer, CustomerPayment, CustomerPaymentAllocation
from app.models.enums import InvoiceStatus
from app.models.sales import Invoice
from app.models.organization import Branch, Organization
from app.schemas.masters import CustomerCreate, CustomerOut, CustomerWrite
from app.services import accounting, whatsapp

router = APIRouter(prefix="/customers", tags=["customers"])


def _normalize_aadhaar(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    if not digits:
        return None
    if len(digits) != 12:
        raise HTTPException(status_code=400, detail="Aadhaar number must be 12 digits")
    return digits


def _assert_unique_aadhaar(db: Session, org_id: int, aadhaar: str | None, exclude_id: int | None = None) -> None:
    if not aadhaar:
        return
    stmt = select(Customer).where(
        Customer.organization_id == org_id,
        Customer.aadhaar_no == aadhaar,
        Customer.is_deleted.is_(False),
    )
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    if db.scalar(stmt):
        raise HTTPException(status_code=409, detail="A farmer with this Aadhaar number already exists")


def _find_by_phone(
    db: Session, org_id: int, phone: str | None, exclude_id: int | None = None
) -> Customer | None:
    """Phone uniqueness is org-wide, including soft-deleted farmers."""
    if not phone:
        return None
    stmt = select(Customer).where(
        Customer.organization_id == org_id,
        Customer.phone == phone,
    )
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    return db.scalar(stmt)


def _assert_unique_phone(db: Session, org_id: int, phone: str | None, exclude_id: int | None = None) -> None:
    existing = _find_by_phone(db, org_id, phone, exclude_id=exclude_id)
    if existing is None:
        return
    if existing.is_deleted:
        raise HTTPException(
            status_code=409,
            detail="This phone belongs to a deleted farmer. Add them again from POS to restore the old record.",
        )
    raise HTTPException(status_code=409, detail="A farmer with this phone number already exists")


def _attach_last_bill_dates(db: Session, org_id: int, customers: list[Customer]) -> list[Customer]:
    """POS picker uses this to tell walk-in staff who still shops here."""
    ids = [c.id for c in customers]
    last: dict[int, date] = {}
    if ids:
        last = dict(
            db.execute(
                select(Invoice.customer_id, func.max(Invoice.invoice_date))
                .where(
                    Invoice.organization_id == org_id,
                    Invoice.status == InvoiceStatus.finalized,
                    Invoice.customer_id.in_(ids),
                )
                .group_by(Invoice.customer_id)
            ).all()
        )
    for customer in customers:
        customer.last_bill_date = last.get(customer.id)
    return customers


@router.get("", response_model=list[CustomerOut])
def list_customers(
    search: str | None = None,
    limit: int = Query(80, ge=1, le=2000),
    outstanding_only: bool = False,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Customer]:
    stmt = select(Customer).where(
        Customer.organization_id == current.organization_id,
        Customer.is_deleted.is_(False),
    )
    if search:
        q = search.strip()
        like = f"%{q}%"
        conds = [Customer.name.ilike(like), Customer.phone.ilike(like), Customer.village.ilike(like)]
        digits = "".join(ch for ch in q if ch.isdigit())
        if digits:
            conds.append(Customer.phone.ilike(f"%{digits}%"))
            conds.append(Customer.aadhaar_no.ilike(f"{digits}%"))
        stmt = stmt.where(or_(*conds))
    if outstanding_only:
        stmt = stmt.where(Customer.outstanding_balance > 0)
    stmt = stmt.order_by(Customer.outstanding_balance.desc(), Customer.name.asc()).limit(limit)
    return _attach_last_bill_dates(db, current.organization_id, list(db.scalars(stmt).all()))


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(
    payload: CustomerCreate,
    current: CurrentUser = Depends(require_permission(rbac.P_CUSTOMER_MANAGE)),
    db: Session = Depends(get_db),
) -> Customer:
    data = payload.model_dump()
    data["aadhaar_no"] = _normalize_aadhaar(data.get("aadhaar_no"))
    _assert_unique_aadhaar(db, current.organization_id, data["aadhaar_no"])
    existing = _find_by_phone(db, current.organization_id, data.get("phone"))
    if existing is not None and not existing.is_deleted:
        raise HTTPException(status_code=409, detail="A farmer with this phone number already exists")
    if existing is not None and existing.is_deleted:
        # Dump/legacy deletes keep the phone unique, so recreating the same
        # farmer must restore the old row (and their bill history) instead of INSERT.
        for key, value in data.items():
            setattr(existing, key, value)
        existing.is_deleted = False
        existing.deleted_at = None
        record_audit(
            db, action="restore", entity_type="customer", entity_id=existing.id,
            actor_user_id=current.id, organization_id=current.organization_id,
            changes=payload.model_dump(mode="json"),
        )
        db.commit()
        db.refresh(existing)
        return _attach_last_bill_dates(db, current.organization_id, [existing])[0]
    customer = Customer(organization_id=current.organization_id, **data)
    db.add(customer)
    db.flush()
    record_audit(
        db, action="create", entity_type="customer", entity_id=customer.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        changes=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(customer)
    return customer


def _get_owned_customer(db: Session, customer_id: int, org_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None or customer.organization_id != org_id or customer.is_deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    payload: CustomerWrite,
    current: CurrentUser = Depends(require_permission(rbac.P_CUSTOMER_MANAGE)),
    db: Session = Depends(get_db),
) -> Customer:
    customer = _get_owned_customer(db, customer_id, current.organization_id)
    data = payload.model_dump()
    data["aadhaar_no"] = _normalize_aadhaar(data.get("aadhaar_no"))
    _assert_unique_aadhaar(db, current.organization_id, data["aadhaar_no"], exclude_id=customer.id)
    _assert_unique_phone(db, current.organization_id, data.get("phone"), exclude_id=customer.id)
    for key, value in data.items():
        setattr(customer, key, value)
    record_audit(
        db, action="update", entity_type="customer", entity_id=customer.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        changes=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_CUSTOMER_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    customer = _get_owned_customer(db, customer_id, current.organization_id)
    if customer.outstanding_balance and customer.outstanding_balance != Decimal("0"):
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a farmer with an outstanding khata balance.",
        )
    customer.is_deleted = True
    record_audit(
        db, action="delete", entity_type="customer", entity_id=customer.id,
        actor_user_id=current.id, organization_id=current.organization_id,
    )
    db.commit()
    return {"status": "deleted", "id": customer_id}


class CustomerPaymentIn(BaseModel):
    amount: Decimal = Field(gt=0)
    mode: str = "cash"
    branch_id: int | None = None
    note: str | None = None


class ReversePaymentIn(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


def _default_payment_branch(
    db: Session, current: CurrentUser, customer_id: int, payload_branch_id: int | None
) -> int | None:
    if payload_branch_id is not None:
        current.assert_branch_access(payload_branch_id)
        return payload_branch_id
    if len(current.branch_ids) == 1:
        return current.branch_ids[0]
    unpaid_branch = db.scalar(
        select(Invoice.branch_id)
        .where(
            Invoice.customer_id == customer_id,
            Invoice.organization_id == current.organization_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.grand_total > Invoice.amount_paid,
        )
        .order_by(Invoice.invoice_date.asc(), Invoice.id.asc())
        .limit(1)
    )
    if unpaid_branch is not None:
        return unpaid_branch
    ids = db.scalars(
        select(Branch.id).where(Branch.organization_id == current.organization_id).limit(2)
    ).all()
    if len(ids) == 1:
        return ids[0]
    return None


def _allocate_receipt_to_invoices(
    db: Session, *, customer_id: int, amount: Decimal, payment_id: int
) -> Decimal:
    """Apply a receipt FIFO to the farmer's unpaid invoices. Returns leftover."""
    remaining = Decimal(amount)
    invoices = db.scalars(
        select(Invoice)
        .where(
            Invoice.customer_id == customer_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.grand_total > Invoice.amount_paid,
        )
        .order_by(Invoice.invoice_date.asc(), Invoice.id.asc())
    ).all()
    for inv in invoices:
        due = (inv.grand_total - inv.amount_paid)
        if due <= 0:
            continue
        apply = due if remaining >= due else remaining
        apply = apply.quantize(Decimal("0.01"))
        inv.amount_paid = (inv.amount_paid + apply).quantize(Decimal("0.01"))
        db.add(CustomerPaymentAllocation(
            payment_id=payment_id, invoice_id=inv.id, amount=apply,
        ))
        remaining = (remaining - apply).quantize(Decimal("0.01"))
        if remaining <= 0:
            break
    return remaining


def _unallocate_receipt(db: Session, *, payment: CustomerPayment) -> None:
    """Remove this receipt from the invoices it paid."""
    allocs = db.scalars(
        select(CustomerPaymentAllocation).where(
            CustomerPaymentAllocation.payment_id == payment.id
        )
    ).all()
    if allocs:
        allocated = {
            inv.id: inv
            for inv in db.scalars(
                select(Invoice).where(
                    Invoice.id.in_({row.invoice_id for row in allocs})
                )
            ).all()
        }
        for row in allocs:
            inv = allocated.get(row.invoice_id)
            if inv is not None:
                inv.amount_paid = (inv.amount_paid - row.amount).quantize(Decimal("0.01"))
                if inv.amount_paid < 0:
                    inv.amount_paid = Decimal("0")
        return
    remaining = Decimal(payment.amount)
    invoices = db.scalars(
        select(Invoice)
        .where(
            Invoice.customer_id == payment.customer_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.amount_paid > 0,
        )
        .order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
    ).all()
    for inv in invoices:
        take = inv.amount_paid if remaining >= inv.amount_paid else remaining
        inv.amount_paid = (inv.amount_paid - take).quantize(Decimal("0.01"))
        remaining = (remaining - take).quantize(Decimal("0.01"))
        if remaining <= 0:
            break


@router.post("/{customer_id}/payments", status_code=201)
def record_customer_payment(
    customer_id: int,
    payload: CustomerPaymentIn,
    current: CurrentUser = Depends(require_permission(rbac.P_SALE_CREATE)),
    db: Session = Depends(get_db),
) -> dict:
    """Collect cash/UPI/card against a farmer's outstanding khata."""
    customer = _get_owned_customer(db, customer_id, current.organization_id)
    amount = Decimal(payload.amount).quantize(Decimal("0.01"))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero")
    outstanding = Decimal(customer.outstanding_balance or 0)
    if amount > outstanding:
        raise HTTPException(
            status_code=400,
            detail=f"Amount exceeds outstanding khata of ₹{outstanding}",
        )
    branch_id = _default_payment_branch(db, current, customer.id, payload.branch_id)

    payment = CustomerPayment(
        organization_id=current.organization_id,
        branch_id=branch_id,
        customer_id=customer.id,
        amount=amount,
        mode=payload.mode,
        note=payload.note,
        paid_at=datetime.now(),
    )
    db.add(payment)
    db.flush()
    _allocate_receipt_to_invoices(
        db, customer_id=customer.id, amount=amount, payment_id=payment.id,
    )
    customer.outstanding_balance = (outstanding - amount).quantize(Decimal("0.01"))
    accounting.post_customer_receipt(
        db,
        organization_id=current.organization_id,
        branch_id=branch_id,
        entry_date=date.today(),
        payment_id=payment.id,
        amount=amount,
        mode=payload.mode,
    )
    record_audit(
        db, action="create", entity_type="customer_payment", entity_id=payment.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=branch_id,
        changes={"customer_id": customer.id, "amount": str(amount), "branch_id": branch_id},
    )
    db.commit()
    return {
        "id": payment.id,
        "customer_id": customer.id,
        "amount": float(amount),
        "outstanding_balance": float(customer.outstanding_balance),
    }


@router.post("/{customer_id}/payments/{payment_id}/reverse")
def reverse_customer_payment(
    customer_id: int,
    payment_id: int,
    payload: ReversePaymentIn,
    current: CurrentUser = Depends(require_permission(rbac.P_SALE_CANCEL)),
    db: Session = Depends(get_db),
) -> dict:
    """Undo a khata collection posted to the wrong farmer. Does not delete the row."""
    customer = _get_owned_customer(db, customer_id, current.organization_id)
    payment = db.get(CustomerPayment, payment_id)
    if (
        payment is None
        or payment.organization_id != current.organization_id
        or payment.customer_id != customer.id
    ):
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.reversed_at is not None:
        raise HTTPException(status_code=409, detail="This payment is already reversed")
    if payment.branch_id is not None:
        current.assert_branch_access(payment.branch_id)
    elif not current.sees_all_branches:
        raise HTTPException(status_code=403, detail="No access to reverse this payment")

    reason = payload.reason.strip()
    _unallocate_receipt(db, payment=payment)
    amount = Decimal(payment.amount).quantize(Decimal("0.01"))
    customer.outstanding_balance = (Decimal(customer.outstanding_balance or 0) + amount).quantize(
        Decimal("0.01")
    )
    payment.reversed_at = datetime.now()
    payment.reversed_by_user_id = current.id
    payment.reversal_reason = reason
    accounting.post_customer_receipt_reversal(
        db,
        organization_id=current.organization_id,
        branch_id=payment.branch_id,
        entry_date=date.today(),
        payment_id=payment.id,
        amount=amount,
        mode=payment.mode,
    )
    record_audit(
        db, action="update", entity_type="customer_payment", entity_id=payment.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=payment.branch_id,
        changes={"reversed": True, "reason": reason, "amount": str(amount)},
    )
    db.commit()
    return {
        "id": payment.id,
        "reversed": True,
        "customer_id": customer.id,
        "amount": float(amount),
        "outstanding_balance": float(customer.outstanding_balance),
    }


@router.get("/{customer_id}/bills")
def customer_bills(
    customer_id: int,
    limit: int = Query(12, ge=1, le=30),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Recent invoices with line items — used by POS while the farmer is on the bill."""
    customer = _get_owned_customer(db, customer_id, current.organization_id)
    invoices = db.scalars(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(
            Invoice.organization_id == current.organization_id,
            Invoice.customer_id == customer.id,
            Invoice.status == InvoiceStatus.finalized,
        )
        .order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
        .limit(limit)
    ).unique().all()
    return [
        {
            "id": inv.id,
            "invoice_no": inv.invoice_no,
            "date": inv.invoice_date.isoformat(),
            "grand_total": float(inv.grand_total),
            "amount_paid": float(inv.amount_paid),
            "payment_mode": (
                inv.payment_mode.value if hasattr(inv.payment_mode, "value") else str(inv.payment_mode)
            ),
            "items": [
                {
                    "product_name": it.product_name,
                    "quantity": float(it.quantity),
                    "unit": it.unit,
                    "unit_price": float(it.unit_price),
                    "discount": float(it.discount or 0),
                    "line_total": float(it.line_total),
                }
                for it in inv.items
            ],
        }
        for inv in invoices
    ]


@router.get("/{customer_id}/ledger")
def customer_ledger(
    customer_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Khata collections and invoice history for a farmer."""
    customer = _get_owned_customer(db, customer_id, current.organization_id)
    payments = db.scalars(
        select(CustomerPayment)
        .where(CustomerPayment.customer_id == customer.id)
        .order_by(CustomerPayment.paid_at.desc(), CustomerPayment.id.desc())
        .limit(200)
    ).all()
    invoices = db.execute(
        select(Invoice.invoice_no, Invoice.invoice_date, Invoice.grand_total, Invoice.amount_paid)
        .where(
            Invoice.organization_id == current.organization_id,
            Invoice.customer_id == customer.id,
            Invoice.status == InvoiceStatus.finalized,
        )
        .order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
        .limit(200)
    ).all()
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "village": customer.village,
        "outstanding_balance": float(customer.outstanding_balance or 0),
        "payments": [
            {
                "id": p.id,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "amount": float(p.amount),
                "mode": p.mode,
                "note": p.note,
                "reversed_at": p.reversed_at.isoformat() if p.reversed_at else None,
                "reversal_reason": p.reversal_reason,
            }
            for p in payments
        ],
        "invoices": [
            {
                "invoice_no": no,
                "date": d.isoformat(),
                "total": float(total),
                "outstanding": float(total - paid),
            }
            for no, d, total, paid in invoices
        ],
    }


@router.post("/{customer_id}/remind")
def remind_customer(
    customer_id: int,
    send: bool = True,
    current: CurrentUser = Depends(require_permission(rbac.P_CUSTOMER_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    """Build a WhatsApp khata reminder. Sends via Cloud API when configured; always returns a wa.me link."""
    customer = _get_owned_customer(db, customer_id, current.organization_id)
    outstanding = Decimal(customer.outstanding_balance or 0)
    if outstanding <= 0:
        raise HTTPException(status_code=400, detail="This farmer has no outstanding khata")
    if not customer.phone:
        raise HTTPException(status_code=400, detail="Add a mobile number before sending a WhatsApp reminder")
    org = db.get(Organization, current.organization_id)
    org_name = org.name if org else "Sri Kumaran Agri Clinic"
    message = whatsapp.reminder_message(
        org_name=org_name, farmer_name=customer.name, amount=outstanding,
    )
    link = whatsapp.wa_me_link(customer.phone, message)
    sent = False
    error = None
    if send and whatsapp.cloud_api_configured():
        sent, error = whatsapp.send_whatsapp_text(
            customer.phone, message, farmer_name=customer.name, amount=outstanding,
        )
        if sent:
            error = None
    record_audit(
        db, action="create", entity_type="whatsapp_reminder", entity_id=customer.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        changes={"customer_id": customer.id, "sent": sent},
    )
    db.commit()
    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "phone": customer.phone,
        "outstanding": float(outstanding),
        "message": message,
        "wa_link": link,
        "api_configured": whatsapp.cloud_api_configured(),
        "sent": sent,
        "error": error if not sent else None,
    }
