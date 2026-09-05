"""Record operating expenses (transport, salary, rent, etc.)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.expense import Expense
from app.models.organization import Branch
from app.api.v1.config import expense_category_rows
from app.services import accounting

router = APIRouter(prefix="/expenses", tags=["expenses"])


class ExpenseIn(BaseModel):
    branch_id: int
    expense_date: date | None = None
    category: str = Field(min_length=1)
    payee: str | None = None
    amount: Decimal = Field(gt=0)
    mode: str = "cash"
    note: str | None = None


def _row(e: Expense, branch_name: str | None = None) -> dict:
    return {
        "id": e.id,
        "branch_id": e.branch_id,
        "branch_name": branch_name,
        "expense_date": e.expense_date.isoformat(),
        "category": e.category,
        "payee": e.payee,
        "amount": float(e.amount),
        "mode": e.mode,
        "note": e.note,
    }


@router.get("/categories")
def list_categories(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return expense_category_rows(db, current.organization_id)


@router.get("")
def list_expenses(
    branch_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    category: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    current: CurrentUser = Depends(require_permission(rbac.P_EXPENSE_MANAGE)),
    db: Session = Depends(get_db),
) -> list[dict]:
    today = date.today()
    start = start or today.replace(day=1)
    end = end or today
    stmt = select(Expense).where(
        Expense.organization_id == current.organization_id,
        Expense.expense_date >= start,
        Expense.expense_date <= end,
    )
    if branch_id is not None:
        current.assert_branch_access(branch_id)
        stmt = stmt.where(Expense.branch_id == branch_id)
    elif not current.sees_all_branches:
        stmt = stmt.where(Expense.branch_id.in_(current.branch_ids or [-1]))
    if category:
        stmt = stmt.where(Expense.category == category)
    rows = db.scalars(stmt.order_by(Expense.expense_date.desc(), Expense.id.desc()).limit(limit)).all()
    branches = {b.id: b.name for b in db.scalars(
        select(Branch).where(Branch.organization_id == current.organization_id)
    ).all()}
    return [_row(e, branches.get(e.branch_id)) for e in rows]


@router.post("", status_code=201)
def create_expense(
    payload: ExpenseIn,
    current: CurrentUser = Depends(require_permission(rbac.P_EXPENSE_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    current.assert_branch_access(payload.branch_id)
    cat = (payload.category or "").strip().lower()
    allowed = {r["key"] for r in expense_category_rows(db, current.organization_id)}
    if cat not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown category. Use one of: {', '.join(sorted(allowed))}",
        )
    amount = Decimal(payload.amount).quantize(Decimal("0.01"))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    expense = Expense(
        organization_id=current.organization_id,
        branch_id=payload.branch_id,
        created_by_user_id=current.id,
        expense_date=payload.expense_date or date.today(),
        category=cat,
        payee=payload.payee,
        amount=amount,
        mode=payload.mode or "cash",
        note=payload.note,
    )
    db.add(expense)
    db.flush()
    accounting.post_expense(
        db,
        organization_id=current.organization_id,
        branch_id=payload.branch_id,
        entry_date=expense.expense_date,
        expense_id=expense.id,
        amount=amount,
        mode=expense.mode,
        category=cat,
        payee=expense.payee,
    )
    record_audit(
        db, action="create", entity_type="expense", entity_id=expense.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=expense.branch_id,
        changes={"category": cat, "amount": str(amount)},
    )
    db.commit()
    branch = db.get(Branch, expense.branch_id)
    return _row(expense, branch.name if branch else None)
