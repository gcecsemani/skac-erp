"""Admin & compliance: users, roles, audit log, alerts, license & traceability."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.enums import StockDiscrepancyStatus
from app.models.inventory import Batch, Stock, StockDiscrepancy
from app.models.organization import Branch
from app.models.product import Product
from app.models.sales import Invoice, InvoiceItem
from app.models.user import Role, User

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Users & roles ---
class UserIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role_key: str
    phone: str | None = None
    branch_ids: list[int] = []


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    role_key: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    branch_ids: list[int] | None = None


def _assert_role(role_key: str) -> None:
    if role_key not in rbac.ALLOWED_ROLE_KEYS:
        raise HTTPException(status_code=400, detail="Role must be owner or cashier")


def _assert_cashier_branches(role_key: str, branch_ids: list[int] | None) -> None:
    if role_key == rbac.ROLE_CASHIER and not (branch_ids or []):
        raise HTTPException(
            status_code=400,
            detail="Assign the cashier to at least one branch",
        )


@router.get("/roles")
def list_roles(
    current: CurrentUser = Depends(require_permission(rbac.P_USER_MANAGE)),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(select(Role).where(Role.key.in_(rbac.ALLOWED_ROLE_KEYS))).all()
    return [{"id": r.id, "key": r.key, "name": r.name, "description": r.description} for r in rows]


@router.get("/users")
def list_users(
    current: CurrentUser = Depends(require_permission(rbac.P_USER_MANAGE)),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(select(User).options(joinedload(User.role)).where(
        User.organization_id == current.organization_id, User.is_deleted.is_(False))).unique().all()
    return [
        {"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role.key,
         "is_active": u.is_active, "totp_enabled": u.totp_enabled,
         "branch_ids": [b.id for b in u.branches],
         "branch_names": [b.name for b in u.branches]}
        for u in rows
    ]


@router.post("/users", status_code=201)
def create_user(
    payload: UserIn,
    current: CurrentUser = Depends(require_permission(rbac.P_USER_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    _assert_role(payload.role_key)
    _assert_cashier_branches(payload.role_key, payload.branch_ids)
    if db.scalar(select(User).where(
        User.organization_id == current.organization_id,
        User.email == payload.email,
        User.is_deleted.is_(False),
    )):
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    role = db.scalar(select(Role).where(Role.key == payload.role_key))
    if role is None:
        raise HTTPException(status_code=400, detail="Unknown role")
    user = User(
        organization_id=current.organization_id, role_id=role.id,
        full_name=payload.full_name, email=payload.email, phone=payload.phone,
        hashed_password=hash_password(payload.password),
    )
    if payload.branch_ids:
        user.branches = list(db.scalars(select(Branch).where(
            Branch.organization_id == current.organization_id,
            Branch.id.in_(payload.branch_ids))).all())
    db.add(user)
    db.flush()
    record_audit(db, action="create", entity_type="user", entity_id=user.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 changes={"email": payload.email, "role": payload.role_key})
    db.commit()
    return {"id": user.id, "email": user.email}


def _get_owned_user(db: Session, user_id: int, org_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or user.organization_id != org_id or user.is_deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    current: CurrentUser = Depends(require_permission(rbac.P_USER_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    user = _get_owned_user(db, user_id, current.organization_id)
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.hashed_password = hash_password(payload.password)
    if payload.role_key:
        _assert_role(payload.role_key)
        role = db.scalar(select(Role).where(Role.key == payload.role_key))
        if role is None:
            raise HTTPException(status_code=400, detail="Unknown role")
        user.role_id = role.id
    next_role = payload.role_key or user.role.key
    next_branches = payload.branch_ids if payload.branch_ids is not None else [b.id for b in user.branches]
    _assert_cashier_branches(next_role, next_branches)
    if payload.branch_ids is not None:
        user.branches = list(db.scalars(select(Branch).where(
            Branch.organization_id == current.organization_id,
            Branch.id.in_(payload.branch_ids))).all())
    record_audit(db, action="update", entity_type="user", entity_id=user.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 changes=payload.model_dump(mode="json", exclude_none=True, exclude={"password"}))
    db.commit()
    return {"id": user.id, "email": user.email}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_USER_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    if user_id == current.id:
        raise HTTPException(status_code=409, detail="You cannot delete your own account.")
    user = _get_owned_user(db, user_id, current.organization_id)
    user.is_deleted = True
    user.is_active = False
    record_audit(db, action="delete", entity_type="user", entity_id=user.id,
                 actor_user_id=current.id, organization_id=current.organization_id)
    db.commit()
    return {"status": "deleted", "id": user_id}


# --- Audit log ---
@router.get("/audit")
def audit_log(
    limit: int = 100,
    current: CurrentUser = Depends(require_permission(rbac.P_AUDIT_VIEW)),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(select(AuditLog).where(
        AuditLog.organization_id == current.organization_id
    ).order_by(AuditLog.id.desc()).limit(limit)).all()
    return [
        {"id": a.id, "action": a.action, "entity_type": a.entity_type,
         "entity_id": a.entity_id, "actor_user_id": a.actor_user_id,
         "branch_id": a.branch_id, "changes": a.changes,
         "created_at": a.created_at.isoformat() if a.created_at else None}
        for a in rows
    ]


# --- Alerts ---
@router.get("/alerts")
def alerts(
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    org_id = current.organization_id
    scope = None if current.sees_all_branches else (current.branch_ids or [-1])
    today = date.today()

    # Near-expiry (next 30 days).
    ne_stmt = (
        select(Product.name, Batch.batch_no, Batch.expiry_date, func.sum(Stock.quantity))
        .join(Stock, Stock.batch_id == Batch.id)
        .join(Product, Product.id == Batch.product_id)
        .where(
            Batch.organization_id == org_id, Stock.quantity > 0,
            Batch.expiry_date.is_not(None),
            Batch.expiry_date <= today + timedelta(days=30), Batch.expiry_date >= today,
        )
        .group_by(Batch.id, Product.name, Batch.batch_no, Batch.expiry_date)
    )
    if scope is not None:
        ne_stmt = ne_stmt.where(Stock.branch_id.in_(scope))
    near_expiry = [
        {"product": n, "batch_no": b, "expiry_date": e.isoformat(),
         "days_left": (e - today).days, "quantity": float(q)}
        for n, b, e, q in db.execute(ne_stmt).all()
    ]
    near_expiry.sort(key=lambda x: x["days_left"])

    # Low stock (on-hand below reorder level).
    ls_stmt = (
        select(Product.name, Product.reorder_level, func.coalesce(func.sum(Stock.quantity), 0))
        .join(Stock, Stock.product_id == Product.id)
        .where(Product.organization_id == org_id, Product.reorder_level > 0)
        .group_by(Product.id, Product.name, Product.reorder_level)
    )
    if scope is not None:
        ls_stmt = ls_stmt.where(Stock.branch_id.in_(scope))
    low_stock = [
        {"product": n, "reorder_level": float(rl), "on_hand": float(q)}
        for n, rl, q in db.execute(ls_stmt).all() if float(q) <= float(rl)
    ]

    case_stmt = (
        select(StockDiscrepancy, Product.name, Branch.name)
        .join(Product, Product.id == StockDiscrepancy.product_id)
        .join(Branch, Branch.id == StockDiscrepancy.branch_id)
        .where(
            StockDiscrepancy.organization_id == org_id,
            StockDiscrepancy.status.in_(
                (StockDiscrepancyStatus.open, StockDiscrepancyStatus.investigating)
            ),
        )
        .order_by(StockDiscrepancy.updated_at.desc())
        .limit(20)
    )
    if scope is not None:
        case_stmt = case_stmt.where(StockDiscrepancy.branch_id.in_(scope))
    stock_cases = [
        {
            "id": c.id,
            "product": pname,
            "branch": bname,
            "variance": float(c.variance),
            "counted_qty": float(c.counted_qty),
            "book_qty": float(c.book_qty),
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "note": c.note,
        }
        for c, pname, bname in db.execute(case_stmt).all()
    ]
    return {
        "near_expiry": near_expiry,
        "low_stock": low_stock,
        "stock_cases": stock_cases,
        "stock_case_open": len(stock_cases),
    }


# --- Compliance ---
@router.get("/licenses")
def license_expiry(
    within_days: int = 90,
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    today = date.today()
    branches = db.scalars(select(Branch).where(
        Branch.organization_id == current.organization_id, Branch.is_deleted.is_(False))).all()
    out = []
    for b in branches:
        if not current.sees_all_branches and b.id not in (current.branch_ids or []):
            continue
        for label, no, valid in [
            ("Fertilizer (FCO)", b.fco_license_no, b.fco_license_valid_to),
            ("Pesticide", b.pesticide_license_no, b.pesticide_license_valid_to),
            ("Seed", b.seed_license_no, b.seed_license_valid_to),
        ]:
            if no:
                days = (valid - today).days if valid else None
                out.append({
                    "branch": b.name, "license_type": label, "license_no": no,
                    "valid_to": valid.isoformat() if valid else None,
                    "days_to_expiry": days,
                    "status": ("expired" if days is not None and days < 0
                               else "expiring" if days is not None and days <= within_days
                               else "ok"),
                })
    return out


@router.get("/traceability")
def batch_traceability(
    batch_no: str,
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Which customers bought a given batch (recall support)."""
    stmt = (
        select(Invoice.invoice_no, Invoice.invoice_date, Invoice.customer_id,
               InvoiceItem.product_name, InvoiceItem.quantity)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .where(
            Invoice.organization_id == current.organization_id,
            InvoiceItem.batch_no == batch_no,
        )
        .order_by(Invoice.invoice_date.desc())
    )
    rows = db.execute(stmt).all()
    return {
        "batch_no": batch_no,
        "sales": [
            {"invoice_no": no, "date": d.isoformat(), "customer_id": cid,
             "product": p, "quantity": float(q)}
            for no, d, cid, p, q in rows
        ],
    }
