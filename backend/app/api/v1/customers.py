"""Farmer / customer master."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.customer import Customer, CustomerPayment
from app.models.enums import InvoiceStatus
from app.models.sales import Invoice
from app.models.organization import Organization
from app.schemas.masters import CustomerBase, CustomerCreate, CustomerOut
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


@router.get("", response_model=list[CustomerOut])
def list_customers(
    search: str | None = None,
    limit: int = Query(100, ge=1, le=30000),
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
    stmt = stmt.order_by(Customer.name.asc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(
    payload: CustomerCreate,
    current: CurrentUser = Depends(require_permission(rbac.P_CUSTOMER_MANAGE)),
    db: Session = Depends(get_db),
) -> Customer:
    data = payload.model_dump()
    data["aadhaar_no"] = _normalize_aadhaar(data.get("aadhaar_no"))
    _assert_unique_aadhaar(db, current.organization_id, data["aadhaar_no"])
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
    payload: CustomerBase,
    current: CurrentUser = Depends(require_permission(rbac.P_CUSTOMER_MANAGE)),
    db: Session = Depends(get_db),
) -> Customer:
    customer = _get_owned_customer(db, customer_id, current.organization_id)
    data = payload.model_dump()
    data["aadhaar_no"] = _normalize_aadhaar(data.get("aadhaar_no"))
    _assert_unique_aadhaar(db, current.organization_id, data["aadhaar_no"], exclude_id=customer.id)
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


def _allocate_receipt_to_invoices(db: Session, *, customer_id: int, amount: Decimal) -> Decimal:
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
        inv.amount_paid = (inv.amount_paid + apply).quantize(Decimal("0.01"))
        remaining = (remaining - apply).quantize(Decimal("0.01"))
        if remaining <= 0:
            break
    return remaining


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
    if payload.branch_id is not None:
        current.assert_branch_access(payload.branch_id)

    payment = CustomerPayment(
        organization_id=current.organization_id,
        branch_id=payload.branch_id,
        customer_id=customer.id,
        amount=amount,
        mode=payload.mode,
        note=payload.note,
    )
    db.add(payment)
    db.flush()
    _allocate_receipt_to_invoices(db, customer_id=customer.id, amount=amount)
    customer.outstanding_balance = (outstanding - amount).quantize(Decimal("0.01"))
    accounting.post_customer_receipt(
        db,
        organization_id=current.organization_id,
        branch_id=payload.branch_id,
        entry_date=date.today(),
        payment_id=payment.id,
        amount=amount,
        mode=payload.mode,
    )
    record_audit(
        db, action="create", entity_type="customer_payment", entity_id=payment.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=payload.branch_id,
        changes={"customer_id": customer.id, "amount": str(amount)},
    )
    db.commit()
    return {
        "id": payment.id,
        "customer_id": customer.id,
        "amount": float(amount),
        "outstanding_balance": float(customer.outstanding_balance),
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
