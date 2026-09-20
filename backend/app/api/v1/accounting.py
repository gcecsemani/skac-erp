"""Accounting & finance reports: accounts, day-book, P&L, GST, aging."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.models.accounting import LedgerAccount
from app.models.enums import InvoiceStatus
from app.models.sales import Invoice
from app.services import accounting as acc

router = APIRouter(prefix="/accounting", tags=["accounting"])


def _branch_scope(current: CurrentUser) -> list[int] | None:
    return None if current.sees_all_branches else (current.branch_ids or [-1])


def _parse(start: str | None, end: str | None) -> tuple[date, date]:
    today = date.today()
    s = date.fromisoformat(start) if start else today.replace(day=1)
    e = date.fromisoformat(end) if end else today
    return s, e


@router.get("/accounts")
def chart_of_accounts(
    current: CurrentUser = Depends(require_permission(rbac.P_ACCOUNTING_VIEW)),
    db: Session = Depends(get_db),
) -> list[dict]:
    acc.ensure_accounts(db, current.organization_id)
    db.commit()
    rows = db.scalars(select(LedgerAccount).where(
        LedgerAccount.organization_id == current.organization_id
    ).order_by(LedgerAccount.code)).all()
    return [{"code": a.code, "name": a.name, "type": a.type.value} for a in rows]


@router.get("/daybook")
def daybook(
    start: str | None = None, end: str | None = None,
    limit: int = Query(400, ge=1, le=2000),
    current: CurrentUser = Depends(require_permission(rbac.P_ACCOUNTING_VIEW)),
    db: Session = Depends(get_db),
) -> list[dict]:
    s, e = _parse(start, end)
    return acc.daybook(db, organization_id=current.organization_id, start=s, end=e,
                       branch_ids=_branch_scope(current), limit=limit)


@router.get("/pnl")
def profit_and_loss(
    start: str | None = None, end: str | None = None,
    current: CurrentUser = Depends(require_permission(rbac.P_ACCOUNTING_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    s, e = _parse(start, end)
    return acc.profit_and_loss(db, organization_id=current.organization_id, start=s, end=e,
                               branch_ids=_branch_scope(current))


@router.get("/gst-summary")
def gst_summary(
    start: str | None = None, end: str | None = None,
    current: CurrentUser = Depends(require_permission(rbac.P_ACCOUNTING_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    """GSTR-1/3B-ready outward supply summary grouped by GST rate."""
    s, e = _parse(start, end)
    slabs = acc.gst_slabs(
        db, organization_id=current.organization_id, start=s, end=e,
        branch_ids=_branch_scope(current),
    )
    return {
        "start": s.isoformat(),
        "end": e.isoformat(),
        "slabs": slabs,
        "total_taxable": round(sum(r["taxable_value"] for r in slabs), 2),
        "total_tax": round(sum(r["total_tax"] for r in slabs), 2),
    }


@router.get("/receivables-aging")
def receivables_aging(
    current: CurrentUser = Depends(require_permission(rbac.P_ACCOUNTING_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    """Age unpaid invoice balances into 0-30 / 31-60 / 61-90 / 90+ buckets."""
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        age = func.julianday(func.current_date()) - func.julianday(Invoice.invoice_date)
    else:
        age = func.datediff(func.current_date(), Invoice.invoice_date)
    due = Invoice.grand_total - Invoice.amount_paid
    stmt = select(
        func.coalesce(func.sum(case((age <= 30, due), else_=0)), 0),
        func.coalesce(func.sum(case((and_(age > 30, age <= 60), due), else_=0)), 0),
        func.coalesce(func.sum(case((and_(age > 60, age <= 90), due), else_=0)), 0),
        func.coalesce(func.sum(case((age > 90, due), else_=0)), 0),
    ).where(
        Invoice.organization_id == current.organization_id,
        Invoice.status == InvoiceStatus.finalized,
        Invoice.grand_total > Invoice.amount_paid,
    )
    scope = _branch_scope(current)
    if scope is not None:
        stmt = stmt.where(Invoice.branch_id.in_(scope))
    b0, b1, b2, b3 = db.execute(stmt).one()
    buckets = {
        "0-30": round(float(b0 or 0), 2),
        "31-60": round(float(b1 or 0), 2),
        "61-90": round(float(b2 or 0), 2),
        "90+": round(float(b3 or 0), 2),
    }
    return {"buckets": buckets, "total": round(sum(buckets.values()), 2)}


@router.get("/payables")
def payables(
    current: CurrentUser = Depends(require_permission(rbac.P_ACCOUNTING_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    rows = acc.vendor_payables(db, organization_id=current.organization_id)
    return {
        "vendors": [{"name": v.name, "outstanding": float(v.outstanding_balance)} for v in rows],
        "total": round(sum(float(v.outstanding_balance) for v in rows), 2),
    }
