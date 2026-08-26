"""Accounting & finance reports: accounts, day-book, P&L, GST, aging."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.models.accounting import LedgerAccount
from app.models.customer import Customer
from app.models.enums import InvoiceStatus
from app.models.sales import Invoice, InvoiceItem
from app.models.vendor import Vendor
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
    current: CurrentUser = Depends(require_permission(rbac.P_ACCOUNTING_VIEW)),
    db: Session = Depends(get_db),
) -> list[dict]:
    s, e = _parse(start, end)
    return acc.daybook(db, organization_id=current.organization_id, start=s, end=e,
                       branch_ids=_branch_scope(current))


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
    stmt = (
        select(
            InvoiceItem.gst_rate,
            func.coalesce(func.sum(InvoiceItem.taxable_value), 0),
            func.coalesce(func.sum(InvoiceItem.tax_amount), 0),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .where(
            Invoice.organization_id == current.organization_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.invoice_date >= s, Invoice.invoice_date <= e,
        )
        .group_by(InvoiceItem.gst_rate)
    )
    scope = _branch_scope(current)
    if scope is not None:
        stmt = stmt.where(Invoice.branch_id.in_(scope))
    rows = db.execute(stmt).all()
    slabs = []
    total_taxable = total_tax = 0.0
    for rate, taxable, tax in rows:
        taxable, tax = float(taxable), float(tax)
        total_taxable += taxable
        total_tax += tax
        slabs.append({
            "gst_rate": float(rate), "taxable_value": round(taxable, 2),
            "cgst": round(tax / 2, 2), "sgst": round(tax / 2, 2),
            "total_tax": round(tax, 2),
        })
    return {"start": s.isoformat(), "end": e.isoformat(), "slabs": slabs,
            "total_taxable": round(total_taxable, 2), "total_tax": round(total_tax, 2)}


@router.get("/receivables-aging")
def receivables_aging(
    current: CurrentUser = Depends(require_permission(rbac.P_ACCOUNTING_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    """Age unpaid invoice balances into 0-30 / 31-60 / 61-90 / 90+ buckets."""
    stmt = select(Invoice).where(
        Invoice.organization_id == current.organization_id,
        Invoice.status == InvoiceStatus.finalized,
        Invoice.grand_total > Invoice.amount_paid,
    )
    scope = _branch_scope(current)
    if scope is not None:
        stmt = stmt.where(Invoice.branch_id.in_(scope))
    buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    today = date.today()
    for inv in db.scalars(stmt).all():
        due = float(inv.grand_total - inv.amount_paid)
        age = (today - inv.invoice_date).days
        key = "0-30" if age <= 30 else "31-60" if age <= 60 else "61-90" if age <= 90 else "90+"
        buckets[key] += due
    buckets = {k: round(v, 2) for k, v in buckets.items()}
    return {"buckets": buckets, "total": round(sum(buckets.values()), 2)}


@router.get("/payables")
def payables(
    current: CurrentUser = Depends(require_permission(rbac.P_ACCOUNTING_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.scalars(select(Vendor).where(
        Vendor.organization_id == current.organization_id,
        Vendor.outstanding_balance > 0,
    ).order_by(Vendor.outstanding_balance.desc())).all()
    return {
        "vendors": [{"name": v.name, "outstanding": float(v.outstanding_balance)} for v in rows],
        "total": round(sum(float(v.outstanding_balance) for v in rows), 2),
    }
