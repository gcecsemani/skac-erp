"""Reporting & analytics: consolidated dashboard, valuation, movers, history."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from time import monotonic

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.models.customer import Customer
from app.models.enums import InvoiceStatus, MovementType
from app.models.expense import Expense
from app.models.inventory import Batch, Stock, StockMovement
from app.models.organization import Branch
from app.models.product import Product
from app.models.sales import Invoice, InvoiceItem
from app.models.vendor import Vendor
from app.services.report_tables import run_report, visible_catalog

router = APIRouter(prefix="/reports", tags=["reports"])

_DASH_TTL_SEC = 20.0
_dash_cache: dict[tuple, tuple[float, dict]] = {}


def _dash_get(key: tuple) -> dict | None:
    hit = _dash_cache.get(key)
    if hit and monotonic() - hit[0] < _DASH_TTL_SEC:
        return hit[1]
    return None


def _dash_set(key: tuple, value: dict) -> dict:
    _dash_cache[key] = (monotonic(), value)
    if len(_dash_cache) > 64:
        cutoff = monotonic() - _DASH_TTL_SEC
        stale = [k for k, (ts, _) in _dash_cache.items() if ts < cutoff]
        for k in stale:
            _dash_cache.pop(k, None)
    return value


def _scope(current: CurrentUser, branch_id: int | None) -> list[int] | None:
    if branch_id is not None:
        current.assert_branch_access(branch_id)
        return [branch_id]
    return None if current.sees_all_branches else (current.branch_ids or [-1])


def _period(preset: str | None, start: date | None, end: date | None) -> tuple[date, date, str]:
    today = date.today()
    if start and end:
        if end < start:
            start, end = end, start
        return start, end, "custom"
    key = (preset or "mtd").lower()
    if key == "today":
        return today, today, "today"
    if key in {"7d", "last_7"}:
        return today - timedelta(days=6), today, "7d"
    if key in {"qtd", "quarter"}:
        q_month = ((today.month - 1) // 3) * 3 + 1
        return date(today.year, q_month, 1), today, "qtd"
    if key in {"fy", "ytd"}:
        fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
        return fy_start, today, "fy"
    return today.replace(day=1), today, "mtd"


def _trend_points(start: date, end: date) -> list[tuple[date, date, str]]:
    """Daily buckets, or weekly when the range is long."""
    days = (end - start).days
    # A single-day view still charts the last 14 days so the sparkline has shape.
    if days <= 1:
        today = end
        return [(today - timedelta(days=i), today - timedelta(days=i), (today - timedelta(days=i)).isoformat())
                for i in range(13, -1, -1)]
    if days > 90:
        points = []
        cursor = start
        while cursor <= end:
            week_end = min(cursor + timedelta(days=6), end)
            points.append((cursor, week_end, cursor.isoformat()))
            cursor = week_end + timedelta(days=1)
        return points
    return [(d, d, d.isoformat()) for i in range(days + 1) for d in [start + timedelta(days=i)]]


def _sum_range(daily: dict[date, dict], start: date, end: date, key: str = "sales") -> tuple[float, int]:
    total = 0.0
    count = 0
    cur = start
    while cur <= end:
        row = daily.get(cur)
        if row:
            total += row[key]
            count += row["count"]
        cur += timedelta(days=1)
    return total, count


@router.get("/dashboard")
def dashboard(
    branch_id: int | None = None,
    preset: str | None = Query("mtd"),
    start: date | None = None,
    end: date | None = None,
    current: CurrentUser = Depends(require_permission(rbac.P_REPORT_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    org_id = current.organization_id
    scope = _scope(current, branch_id)
    period_start, period_end, resolved = _period(preset, start, end)
    today = date.today()
    fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
    cache_key = (org_id, tuple(scope) if scope is not None else None, resolved, period_start, period_end)
    cached = _dash_get(cache_key)
    if cached is not None:
        return cached

    trend_points = _trend_points(period_start, period_end)
    span_start = min(fy_start, trend_points[0][0], period_start)
    span_end = max(today, period_end)

    daily_stmt = (
        select(
            Invoice.invoice_date,
            func.coalesce(func.sum(Invoice.grand_total), 0),
            func.coalesce(func.sum(Invoice.amount_paid), 0),
            func.count(Invoice.id),
        )
        .where(
            Invoice.organization_id == org_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.invoice_date >= span_start,
            Invoice.invoice_date <= span_end,
        )
        .group_by(Invoice.invoice_date)
    )
    if scope is not None:
        daily_stmt = daily_stmt.where(Invoice.branch_id.in_(scope))
    daily = {
        d: {"sales": float(s or 0), "paid": float(p or 0), "count": int(c or 0)}
        for d, s, p, c in db.execute(daily_stmt)
    }

    sales_period, inv_count = _sum_range(daily, period_start, period_end)
    collections_period, _ = _sum_range(daily, period_start, period_end, "paid")
    sales_today, _ = _sum_range(daily, today, today)
    sales_ytd, _ = _sum_range(daily, fy_start, today)
    trend = [{"date": label, "revenue": _sum_range(daily, a, b)[0]} for a, b, label in trend_points]

    gp_stmt = (
        select(
            func.coalesce(func.sum(InvoiceItem.taxable_value), 0),
            func.coalesce(func.sum(InvoiceItem.quantity * Product.purchase_price), 0),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
        .where(
            Invoice.organization_id == org_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.invoice_date >= period_start, Invoice.invoice_date <= period_end,
        )
    )
    if scope is not None:
        gp_stmt = gp_stmt.where(Invoice.branch_id.in_(scope))
    rev, cost = db.execute(gp_stmt).one()
    gross_profit = float(rev) - float(cost)

    recv_stmt = select(
        func.coalesce(func.sum(Invoice.grand_total - Invoice.amount_paid), 0),
        func.count(Invoice.id),
    ).where(
        Invoice.organization_id == org_id,
        Invoice.status == InvoiceStatus.finalized,
        Invoice.grand_total > Invoice.amount_paid,
    )
    if scope is not None:
        recv_stmt = recv_stmt.where(Invoice.branch_id.in_(scope))
    receivables_total, unpaid_count = db.execute(recv_stmt).one()

    cat_stmt = (
        select(Product.category, func.coalesce(func.sum(InvoiceItem.line_total), 0))
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
        .where(
            Invoice.organization_id == org_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.invoice_date >= period_start,
            Invoice.invoice_date <= period_end,
        )
        .group_by(Product.category)
    )
    if scope is not None:
        cat_stmt = cat_stmt.where(Invoice.branch_id.in_(scope))
    category_split = [
        {"category": c.value if hasattr(c, "value") else str(c), "revenue": float(v)}
        for c, v in db.execute(cat_stmt).all()
    ]

    branch_stmt = (
        select(Branch.name, func.coalesce(func.sum(Invoice.grand_total), 0))
        .outerjoin(Invoice, and_(
            Invoice.branch_id == Branch.id,
            Invoice.organization_id == org_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.invoice_date >= period_start,
            Invoice.invoice_date <= period_end,
        ))
        .where(Branch.organization_id == org_id, Branch.is_deleted.is_(False))
        .group_by(Branch.id, Branch.name)
        .order_by(Branch.name)
    )
    if scope is not None:
        branch_stmt = branch_stmt.where(Branch.id.in_(scope))
    branch_comparison = [{"branch": name, "revenue": float(v or 0)} for name, v in db.execute(branch_stmt)]

    near_expiry = db.scalar(
        select(func.count(func.distinct(Batch.id)))
        .join(Stock, Stock.batch_id == Batch.id)
        .where(
            Batch.organization_id == org_id, Stock.quantity > 0,
            Batch.expiry_date.is_not(None),
            Batch.expiry_date <= today + timedelta(days=30),
            Batch.expiry_date >= today,
        )
    ) or 0

    exp_cat_stmt = (
        select(
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0),
            func.count(Expense.id),
        )
        .where(
            Expense.organization_id == org_id,
            Expense.expense_date >= period_start,
            Expense.expense_date <= period_end,
        )
        .group_by(Expense.category)
    )
    if scope is not None:
        exp_cat_stmt = exp_cat_stmt.where(Expense.branch_id.in_(scope))
    expense_by_category = []
    expenses_period = 0.0
    exp_count = 0
    for c, amount, cnt in db.execute(exp_cat_stmt):
        amount_f = float(amount or 0)
        expenses_period += amount_f
        exp_count += int(cnt or 0)
        expense_by_category.append({"category": c, "amount": amount_f})

    payables_stmt = select(func.coalesce(func.sum(Vendor.outstanding_balance), 0)).where(
        Vendor.organization_id == org_id,
        Vendor.outstanding_balance > 0,
        Vendor.is_deleted.is_(False),
    )
    payables_total = float(db.scalar(payables_stmt) or 0)

    khata_count = db.scalar(
        select(func.count(Customer.id)).where(
            Customer.organization_id == org_id,
            Customer.is_deleted.is_(False),
            Customer.outstanding_balance > 0,
        )
    ) or 0

    pay_stmt = (
        select(Invoice.payment_mode, func.coalesce(func.sum(Invoice.grand_total), 0))
        .where(
            Invoice.organization_id == org_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.invoice_date >= period_start,
            Invoice.invoice_date <= period_end,
        )
        .group_by(Invoice.payment_mode)
    )
    if scope is not None:
        pay_stmt = pay_stmt.where(Invoice.branch_id.in_(scope))
    payment_split = [
        {"mode": m.value if hasattr(m, "value") else str(m), "revenue": float(v)}
        for m, v in db.execute(pay_stmt).all()
    ]

    payload = {
        "preset": resolved,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "sales_period": sales_period,
        "sales_today": sales_today,
        "sales_mtd": sales_period,
        "sales_ytd": sales_ytd,
        "invoice_count_today": int(inv_count),
        "invoice_count": int(inv_count),
        "gross_profit_mtd": round(gross_profit, 2),
        "gross_profit": round(gross_profit, 2),
        "receivables_total": round(float(receivables_total or 0), 2),
        "near_expiry_count": int(near_expiry),
        "expenses_period": round(expenses_period, 2),
        "expense_count": int(exp_count),
        "net_after_expenses": round(sales_period - expenses_period, 2),
        "collections_period": round(collections_period, 2),
        "unpaid_invoice_count": int(unpaid_count or 0),
        "payables_total": round(payables_total, 2),
        "khata_farmer_count": int(khata_count),
        "expense_by_category": expense_by_category,
        "payment_split": payment_split,
        "sales_trend": trend,
        "category_split": category_split,
        "branch_comparison": branch_comparison,
    }
    return _dash_set(cache_key, payload)


@router.get("/stock-valuation")
def stock_valuation(
    branch_id: int | None = None,
    current: CurrentUser = Depends(require_permission(rbac.P_REPORT_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    scope = _scope(current, branch_id)
    stmt = (
        select(Product.name, Product.category, func.sum(Stock.quantity),
               func.sum(Stock.quantity * Batch.purchase_price))
        .join(Stock, Stock.product_id == Product.id)
        .join(Batch, Batch.id == Stock.batch_id)
        .where(Product.organization_id == current.organization_id, Stock.quantity > 0)
        .group_by(Product.id, Product.name, Product.category)
    )
    if scope is not None:
        stmt = stmt.where(Stock.branch_id.in_(scope))
    items = []
    total = 0.0
    for name, cat, qty, val in db.execute(stmt).all():
        v = float(val or 0)
        total += v
        items.append({"product": name, "category": cat.value if hasattr(cat, "value") else str(cat),
                      "quantity": float(qty or 0), "value": round(v, 2)})
    items.sort(key=lambda x: x["value"], reverse=True)
    return {"items": items, "total_value": round(total, 2)}


@router.get("/movers")
def movers(
    days: int = 30, branch_id: int | None = None,
    current: CurrentUser = Depends(require_permission(rbac.P_REPORT_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    scope = _scope(current, branch_id)
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(Product.id, Product.name,
               func.coalesce(func.sum(-StockMovement.quantity), 0))
        .join(StockMovement, StockMovement.product_id == Product.id)
        .where(
            Product.organization_id == current.organization_id,
            StockMovement.movement_type == MovementType.sale,
            StockMovement.occurred_at >= since,
        )
        .group_by(Product.id, Product.name)
    )
    if scope is not None:
        stmt = stmt.where(StockMovement.branch_id.in_(scope))
    rows = [{"product": n, "sold": float(q)} for _, n, q in db.execute(stmt).all()]
    rows.sort(key=lambda r: r["sold"], reverse=True)
    return {"fast": rows[:10], "slow": rows[-10:][::-1] if len(rows) > 10 else []}


@router.get("/farmer/{customer_id}/history")
def farmer_history(
    customer_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_REPORT_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    filt = (
        Invoice.organization_id == current.organization_id,
        Invoice.customer_id == customer_id,
    )
    invoice_count = int(db.scalar(select(func.count(Invoice.id)).where(*filt)) or 0)
    total_purchased = float(db.scalar(select(func.coalesce(func.sum(Invoice.grand_total), 0)).where(*filt)) or 0)
    rows = db.execute(
        select(
            Invoice.invoice_no, Invoice.invoice_date, Invoice.grand_total, Invoice.amount_paid,
        )
        .where(*filt)
        .order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
        .limit(50)
    ).all()
    return {
        "customer_id": customer_id,
        "invoice_count": invoice_count,
        "total_purchased": round(total_purchased, 2),
        "invoices": [
            {"invoice_no": no, "date": d.isoformat(),
             "total": float(total),
             "outstanding": float(total - paid)}
            for no, d, total, paid in rows
        ],
    }


@router.get("/catalog")
def report_catalog(
    current: CurrentUser = Depends(require_permission(rbac.P_REPORT_VIEW)),
) -> list[dict]:
    return visible_catalog()


@router.get("/table")
def report_table(
    type: str = Query(..., alias="type"),
    branch_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    current: CurrentUser = Depends(require_permission(rbac.P_REPORT_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    period_start, period_end, _ = _period("custom" if start and end else "mtd", start, end)
    scope = _scope(current, branch_id)
    return run_report(
        db,
        org_id=current.organization_id,
        scope=scope,
        key=type,
        start=period_start,
        end=period_end,
    )
