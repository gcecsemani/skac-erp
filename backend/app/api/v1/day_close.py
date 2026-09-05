"""End-of-day cashier checkout."""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models.day_close import DayClose
from app.models.organization import Branch
from app.models.user import User
from app.services.day_close import apply_counts, compute_expected, serialize

router = APIRouter(prefix="/day-close", tags=["day-close"])
TWO = Decimal("0.01")


class DayCloseIn(BaseModel):
    branch_id: int
    close_date: date | None = None
    opening_cash: Decimal = Field(default=Decimal("0"), ge=0)
    counted_cash: Decimal = Field(default=Decimal("0"), ge=0)
    counted_digital: Decimal = Field(default=Decimal("0"), ge=0)
    note: str | None = None


def _money(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(TWO)


def _include_unscoped(current: CurrentUser) -> bool:
    return not current.sees_all_branches


def _get_close(db: Session, org_id: int, branch_id: int, close_date: date) -> DayClose | None:
    return db.scalar(
        select(DayClose).where(
            DayClose.organization_id == org_id,
            DayClose.branch_id == branch_id,
            DayClose.close_date == close_date,
        )
    )


@router.get("/preview")
def preview_day_close(
    branch_id: int,
    close_date: date | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    current.assert_branch_access(branch_id)
    day = close_date or date.today()
    expected = compute_expected(
        db,
        org_id=current.organization_id,
        branch_id=branch_id,
        close_date=day,
        include_unscoped=_include_unscoped(current),
    )
    existing = _get_close(db, current.organization_id, branch_id, day)
    branch = db.get(Branch, branch_id)
    out = {
        **expected,
        "branch_id": branch_id,
        "branch_name": branch.name if branch else None,
        "close_date": day.isoformat(),
        "closed": existing is not None,
        "existing": serialize(existing) if existing else None,
        "opening_cash": float(expected["opening_cash"]),
        "cash_in": float(expected["cash_in"]),
        "cash_out": float(expected["cash_out"]),
        "expected_cash": float(expected["expected_cash"]),
        "digital_in": float(expected["digital_in"]),
        "digital_out": float(expected["digital_out"]),
        "expected_digital": float(expected["expected_digital"]),
        "sales_total": float(expected["sales_total"]),
        "collected_total": float(expected["collected_total"]),
        "khata_new": float(expected["khata_new"]),
        "khata_collected": float(expected["khata_collected"]),
        "expense_total": float(expected["expense_total"]),
        "vendor_paid": float(expected["vendor_paid"]),
        "unscoped_in": float(expected["unscoped_in"]),
        "unscoped_out": float(expected["unscoped_out"]),
    }
    return out


@router.get("")
def list_day_closes(
    branch_id: int | None = None,
    limit: int = Query(30, ge=1, le=120),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(DayClose).where(DayClose.organization_id == current.organization_id)
    if branch_id is not None:
        current.assert_branch_access(branch_id)
        stmt = stmt.where(DayClose.branch_id == branch_id)
    elif not current.sees_all_branches:
        stmt = stmt.where(DayClose.branch_id.in_(current.branch_ids or [-1]))
    rows = db.scalars(stmt.order_by(DayClose.close_date.desc(), DayClose.id.desc()).limit(limit)).all()
    branches = {
        b.id: b.name
        for b in db.scalars(select(Branch).where(Branch.organization_id == current.organization_id)).all()
    }
    users = {
        u.id: u.full_name
        for u in db.scalars(select(User).where(User.organization_id == current.organization_id)).all()
    }
    return [
        serialize(r, extra={
            "branch_name": branches.get(r.branch_id),
            "closed_by": users.get(r.closed_by_user_id) if r.closed_by_user_id else None,
        })
        for r in rows
    ]


@router.post("")
def save_day_close(
    payload: DayCloseIn,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    current.assert_branch_access(payload.branch_id)
    day = payload.close_date or date.today()
    expected = compute_expected(
        db,
        org_id=current.organization_id,
        branch_id=payload.branch_id,
        close_date=day,
        include_unscoped=_include_unscoped(current),
    )
    snap = apply_counts(
        expected,
        opening_cash=_money(payload.opening_cash),
        counted_cash=_money(payload.counted_cash),
        counted_digital=_money(payload.counted_digital),
    )
    row = _get_close(db, current.organization_id, payload.branch_id, day)
    created = row is None
    if row is None:
        row = DayClose(
            organization_id=current.organization_id,
            branch_id=payload.branch_id,
            close_date=day,
        )
        db.add(row)
    row.closed_by_user_id = current.id
    row.closed_at = datetime.utcnow()
    row.note = (payload.note or "").strip() or None
    for key, value in snap.items():
        setattr(row, key, value)
    row.breakdown = json.dumps({
        "in_by": expected["in_by"],
        "out_by": expected["out_by"],
        "khata_collected": float(expected["khata_collected"]),
        "vendor_paid": float(expected["vendor_paid"]),
        "previous_close_date": expected["previous_close_date"],
        "unscoped_in": float(expected["unscoped_in"]),
        "unscoped_out": float(expected["unscoped_out"]),
    })
    db.flush()
    record_audit(
        db,
        action="create" if created else "update",
        entity_type="day_close",
        entity_id=row.id,
        actor_user_id=current.id,
        organization_id=current.organization_id,
        branch_id=payload.branch_id,
        changes={
            "close_date": day.isoformat(),
            "cash_variance": str(snap["cash_variance"]),
            "digital_variance": str(snap["digital_variance"]),
        },
    )
    db.commit()
    db.refresh(row)
    return serialize(row)
