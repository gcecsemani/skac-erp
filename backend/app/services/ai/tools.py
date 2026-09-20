"""Secure, vetted business-query tools for the AI assistant.

The LLM is NEVER given raw SQL access. It may only choose one of these
registered tools and supply typed, validated arguments. Each tool runs a
parameterized query scoped to the caller's organization and branch access.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.enums import InvoiceStatus, ProductCategory
from app.models.expense import Expense
from app.models.product import Product
from app.models.sales import Invoice, InvoiceItem
from app.services import report_tables
from app.services.ai import forecasting
from app.services.cogs import grouped_totals, line_totals_stmt, overall_totals


@dataclass
class ToolContext:
    db: Session
    organization_id: int
    branch_ids: list[int] | None  # None => all branches (owner/admin)


PERIODS = [
    "today", "this_week", "this_month", "last_month", "mtd", "ytd",
    "last_30_days", "last_90_days",
]
REPORT_KEYS = [c["key"] for c in report_tables.CATALOG]


def _clamp_int(v, default: int, lo: int, hi: int) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _period_range(period: str) -> tuple[date, date]:
    today = date.today()
    p = (period or "").lower().strip().replace(" ", "_")
    custom = re.search(r"last_(\d+)_days?", p)
    if custom:
        n = _clamp_int(custom.group(1), 30, 1, 3650)
        return today - timedelta(days=n), today
    if p == "today":
        return today, today
    if p == "this_week":
        return today - timedelta(days=today.weekday()), today
    if p == "this_month":
        return today.replace(day=1), today
    if p == "last_month":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    if p == "mtd":
        return today.replace(day=1), today
    if p == "ytd":
        fy_start = today.year if today.month >= 4 else today.year - 1
        return date(fy_start, 4, 1), today
    if p == "last_90_days":
        return today - timedelta(days=90), today
    if p == "last_30_days":
        return today - timedelta(days=30), today
    return today.replace(day=1), today


def _with_report(payload: dict, title: str, columns: list[dict], rows: list[dict]) -> dict:
    clean_rows = []
    for r in rows:
        if not isinstance(r, dict):
            clean_rows.append(r)
            continue
        clean_rows.append({k: v for k, v in r.items() if k not in ("columns", "rows", "title")})
    return {
        **payload,
        "title": title,
        "columns": columns,
        "rows": clean_rows,
        "row_count": len(clean_rows),
    }


def _scope(stmt, ctx: ToolContext):
    stmt = stmt.where(Invoice.organization_id == ctx.organization_id)
    if ctx.branch_ids is not None:
        stmt = stmt.where(Invoice.branch_id.in_(ctx.branch_ids))
    return stmt.where(Invoice.status == InvoiceStatus.finalized)


# --- Tools ---
def top_selling_products(ctx: ToolContext, period: str = "this_month", limit: int = 10, category: str | None = None) -> dict:
    start, end = _period_range(period)
    stmt = (
        line_totals_stmt(InvoiceItem.product_id, InvoiceItem.product_name)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
    )
    stmt = _scope(stmt, ctx).where(
        Invoice.invoice_date >= start, Invoice.invoice_date <= end
    )
    if category:
        stmt = stmt.where(Product.category == ProductCategory(category))
    # Loose kg lines are folded to pack equivalents in Python, so the top-N cut
    # happens here rather than in SQL.
    items = [
        {"product": name, "quantity": float(t.qty), "revenue": round(float(t.total), 2)}
        for (_pid, name), t in grouped_totals(ctx.db, stmt).items()
    ]
    items.sort(key=lambda r: r["revenue"], reverse=True)
    items = items[:limit]
    return _with_report(
        {"period": period, "items": items},
        f"Top selling products ({period})",
        [
            {"key": "product", "label": "Product"},
            {"key": "quantity", "label": "Qty", "num": True},
            {"key": "revenue", "label": "Revenue", "num": True, "money": True},
        ],
        items,
    )


def sales_summary(ctx: ToolContext, period: str = "today") -> dict:
    start, end = _period_range(period)
    stmt = _scope(
        select(
            func.coalesce(func.sum(Invoice.grand_total), 0).label("revenue"),
            func.count(Invoice.id).label("invoices"),
        ),
        ctx,
    ).where(Invoice.invoice_date >= start, Invoice.invoice_date <= end)
    row = ctx.db.execute(stmt).one()
    data = {
        "period": period,
        "revenue": round(float(row.revenue or 0), 2),
        "invoice_count": int(row.invoices or 0),
    }
    return _with_report(
        data,
        f"Sales summary ({period})",
        [
            {"key": "period", "label": "Period"},
            {"key": "invoice_count", "label": "Bills", "num": True},
            {"key": "revenue", "label": "Revenue", "num": True, "money": True},
        ],
        [data],
    )


def profit_summary(ctx: ToolContext, period: str = "this_month") -> dict:
    """Estimated gross profit = taxable revenue - pack-equivalent COGS."""
    start, end = _period_range(period)
    stmt = (
        line_totals_stmt()
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
    )
    stmt = _scope(stmt, ctx).where(
        Invoice.invoice_date >= start, Invoice.invoice_date <= end
    )
    totals = overall_totals(ctx.db, stmt)
    revenue = float(totals.taxable)
    cost = float(totals.cogs)
    data = {
        "period": period,
        "revenue": round(revenue, 2),
        "cost": round(cost, 2),
        "gross_profit": round(revenue - cost, 2),
        "margin_pct": round((revenue - cost) / revenue * 100, 1) if revenue else 0.0,
    }
    return _with_report(
        data,
        f"Profit summary ({period})",
        [
            {"key": "period", "label": "Period"},
            {"key": "revenue", "label": "Revenue", "num": True, "money": True},
            {"key": "cost", "label": "Cost", "num": True, "money": True},
            {"key": "gross_profit", "label": "Gross profit", "num": True, "money": True},
            {"key": "margin_pct", "label": "Margin %", "num": True},
        ],
        [data],
    )


def highest_margin_products(ctx: ToolContext, limit: int = 10, min_margin_pct: float | None = None) -> dict:
    # Margin is pure master-data arithmetic; rank and cut it in SQL rather than
    # hydrating every product row to pick the top few.
    margin = (Product.sale_price - Product.purchase_price) / Product.sale_price * 100
    stmt = select(
        Product.name, Product.purchase_price, Product.sale_price, margin
    ).where(
        Product.organization_id == ctx.organization_id,
        Product.is_deleted.is_(False),
        Product.sale_price > 0,
    )
    if min_margin_pct is not None:
        stmt = stmt.where(margin >= min_margin_pct)
    stmt = stmt.order_by(margin.desc()).limit(limit)

    items = [
        {
            "product": name,
            "purchase_price": float(cost),
            "sale_price": float(price),
            "margin_pct": round(float(pct), 1),
        }
        for name, cost, price, pct in ctx.db.execute(stmt).all()
    ]
    return _with_report(
        {"items": items},
        "Highest-margin products",
        [
            {"key": "product", "label": "Product"},
            {"key": "purchase_price", "label": "Cost", "num": True, "money": True},
            {"key": "sale_price", "label": "Sale price", "num": True, "money": True},
            {"key": "margin_pct", "label": "Margin %", "num": True},
        ],
        items,
    )


def customers_highest_outstanding(ctx: ToolContext, limit: int = 10, min_amount: float | None = None) -> dict:
    stmt = (
        select(Customer)
        .where(
            Customer.organization_id == ctx.organization_id,
            Customer.outstanding_balance > 0,
        )
        .order_by(Customer.outstanding_balance.desc())
        .limit(limit)
    )
    if min_amount is not None:
        stmt = stmt.where(Customer.outstanding_balance >= min_amount)
    rows = ctx.db.scalars(stmt).all()
    customers = [
        {"name": c.name, "phone": c.phone or "—", "village": c.village or "—",
         "outstanding": round(float(c.outstanding_balance), 2)}
        for c in rows
    ]
    return _with_report(
        {"customers": customers},
        "Farmers with outstanding credit",
        [
            {"key": "name", "label": "Farmer"},
            {"key": "phone", "label": "Phone"},
            {"key": "village", "label": "Village"},
            {"key": "outstanding", "label": "Outstanding", "num": True, "money": True},
        ],
        customers,
    )


def products_not_sold_since(ctx: ToolContext, days: int = 90) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=days)
    sold_recently = select(InvoiceItem.product_id).join(
        Invoice, Invoice.id == InvoiceItem.invoice_id
    )
    sold_recently = _scope(sold_recently, ctx).where(Invoice.invoice_date >= cutoff.date())
    sold_ids = {r for (r,) in ctx.db.execute(sold_recently).all()}
    products = ctx.db.scalars(
        select(Product).where(
            Product.organization_id == ctx.organization_id,
            Product.is_deleted.is_(False),
            Product.is_active.is_(True),
        )
    ).all()
    stale = [{"product": p.name, "category": p.category.value}
             for p in products if p.id not in sold_ids]
    return _with_report(
        {"days": days, "count": len(stale), "products": stale},
        f"Products with no sales in {days} days",
        [
            {"key": "product", "label": "Product"},
            {"key": "category", "label": "Category"},
        ],
        stale,
    )


def products_running_out(ctx: ToolContext, within_days: int = 14) -> dict:
    branch_id = ctx.branch_ids[0] if ctx.branch_ids and len(ctx.branch_ids) == 1 else None
    forecasts = forecasting.forecast_all(
        ctx.db, organization_id=ctx.organization_id, branch_id=branch_id
    )
    soon = []
    for f in forecasts:
        so = f.get("estimated_stockout_date")
        if so:
            days = (date.fromisoformat(so) - date.today()).days
            if days <= within_days:
                soon.append({**f, "days_to_stockout": days})
    soon.sort(key=lambda x: x["days_to_stockout"])
    rows = [
        {
            "product": p.get("product_name"),
            "stock": p.get("current_stock"),
            "days_to_stockout": p.get("days_to_stockout"),
            "recommended_qty": p.get("recommended_purchase_qty"),
        }
        for p in soon
    ]
    return _with_report(
        {"within_days": within_days, "products": soon},
        f"Stock running out within {within_days} days",
        [
            {"key": "product", "label": "Product"},
            {"key": "stock", "label": "On hand", "num": True},
            {"key": "days_to_stockout", "label": "Days left", "num": True},
            {"key": "recommended_qty", "label": "Buy qty", "num": True},
        ],
        rows,
    )


def purchase_recommendations(ctx: ToolContext) -> dict:
    branch_id = ctx.branch_ids[0] if ctx.branch_ids and len(ctx.branch_ids) == 1 else None
    recs = forecasting.forecast_all(
        ctx.db, organization_id=ctx.organization_id, branch_id=branch_id,
        only_needing_purchase=True,
    )
    rows = [
        {
            "product": r.get("product_name"),
            "stock": r.get("current_stock"),
            "avg_daily_sales": r.get("avg_daily_sales"),
            "recommended_qty": r.get("recommended_purchase_qty"),
        }
        for r in recs
    ]
    return _with_report(
        {"recommendations": recs},
        "Purchase recommendations",
        [
            {"key": "product", "label": "Product"},
            {"key": "stock", "label": "On hand", "num": True},
            {"key": "avg_daily_sales", "label": "Avg daily sales", "num": True},
            {"key": "recommended_qty", "label": "Buy qty", "num": True},
        ],
        rows,
    )


def compare_periods(ctx: ToolContext, period_a: str = "this_month", period_b: str = "last_month") -> dict:
    a = sales_summary(ctx, period=period_a)
    b = sales_summary(ctx, period=period_b)
    delta = a["revenue"] - b["revenue"]
    pct = (delta / b["revenue"] * 100) if b["revenue"] else 0.0
    rows = [
        {"period": period_a, "revenue": a["revenue"], "bills": a["invoice_count"]},
        {"period": period_b, "revenue": b["revenue"], "bills": b["invoice_count"]},
    ]
    return _with_report(
        {
            "period_a": {"period": period_a, "revenue": a["revenue"], "invoice_count": a["invoice_count"]},
            "period_b": {"period": period_b, "revenue": b["revenue"], "invoice_count": b["invoice_count"]},
            "change": round(delta, 2),
            "change_pct": round(pct, 1),
        },
        f"Sales: {period_a} vs {period_b}",
        [
            {"key": "period", "label": "Period"},
            {"key": "bills", "label": "Bills", "num": True},
            {"key": "revenue", "label": "Revenue", "num": True, "money": True},
        ],
        rows,
    )


def inactive_credit_customers(
    ctx: ToolContext, days: int = 30, min_amount: float | None = None, limit: int = 2000,
) -> dict:
    """Farmers with outstanding credit who have not billed in the last N days."""
    days = _clamp_int(days, 30, 1, 3650)
    limit = _clamp_int(limit, 500, 1, 2000)
    cutoff = date.today() - timedelta(days=days)

    last_sale = (
        select(
            Invoice.customer_id,
            func.max(Invoice.invoice_date).label("last_date"),
            func.count(Invoice.id).label("bills"),
            func.coalesce(func.sum(Invoice.grand_total), 0).label("lifetime_sales"),
        )
        .where(
            Invoice.organization_id == ctx.organization_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.customer_id.isnot(None),
        )
        .group_by(Invoice.customer_id)
    )
    if ctx.branch_ids is not None:
        last_sale = last_sale.where(Invoice.branch_id.in_(ctx.branch_ids))
    last_sale = last_sale.subquery()

    stmt = (
        select(Customer, last_sale.c.last_date, last_sale.c.bills, last_sale.c.lifetime_sales)
        .outerjoin(last_sale, last_sale.c.customer_id == Customer.id)
        .where(
            Customer.organization_id == ctx.organization_id,
            Customer.is_deleted.is_(False),
            Customer.outstanding_balance > 0,
            or_(last_sale.c.last_date.is_(None), last_sale.c.last_date <= cutoff),
        )
        .order_by(Customer.outstanding_balance.desc())
        .limit(limit)
    )
    if min_amount is not None:
        stmt = stmt.where(Customer.outstanding_balance >= float(min_amount))

    agg = select(
        func.count(Customer.id),
        func.coalesce(func.sum(Customer.outstanding_balance), 0),
    ).select_from(Customer).outerjoin(
        last_sale, last_sale.c.customer_id == Customer.id
    ).where(
        Customer.organization_id == ctx.organization_id,
        Customer.is_deleted.is_(False),
        Customer.outstanding_balance > 0,
        or_(last_sale.c.last_date.is_(None), last_sale.c.last_date <= cutoff),
    )
    if min_amount is not None:
        agg = agg.where(Customer.outstanding_balance >= float(min_amount))
    total_count, total_os = ctx.db.execute(agg).one()

    today = date.today()
    rows = []
    for c, last_date, bills, lifetime in ctx.db.execute(stmt).all():
        outstanding = round(float(c.outstanding_balance), 2)
        rows.append({
            "name": c.name,
            "phone": c.phone or "—",
            "village": c.village or "—",
            "district": c.district or "—",
            "outstanding": outstanding,
            "last_purchase": last_date.isoformat() if last_date else "Never",
            "days_since_visit": (today - last_date).days if last_date else None,
            "lifetime_bills": int(bills or 0),
            "lifetime_sales": round(float(lifetime or 0), 2),
        })
    total_count = int(total_count or 0)
    total = round(float(total_os or 0), 2)
    payload = _with_report(
        {
            "days": days,
            "count": total_count,
            "total_outstanding": total,
            "truncated": total_count > len(rows),
        },
        f"Credit farmers with no visit in {days} days",
        [
            {"key": "name", "label": "Farmer"},
            {"key": "phone", "label": "Phone"},
            {"key": "village", "label": "Village"},
            {"key": "district", "label": "District"},
            {"key": "outstanding", "label": "Outstanding", "num": True, "money": True},
            {"key": "last_purchase", "label": "Last bill"},
            {"key": "days_since_visit", "label": "Days since visit", "num": True},
            {"key": "lifetime_bills", "label": "Lifetime bills", "num": True},
            {"key": "lifetime_sales", "label": "Lifetime sales", "num": True, "money": True},
        ],
        rows,
    )
    payload["row_count"] = len(rows)
    return payload


def expenses_summary(ctx: ToolContext, period: str = "this_month") -> dict:
    start, end = _period_range(period)
    stmt = select(
        Expense.category,
        Expense.mode,
        func.coalesce(func.sum(Expense.amount), 0).label("amount"),
        func.count(Expense.id).label("count"),
    ).where(
        Expense.organization_id == ctx.organization_id,
        Expense.expense_date >= start,
        Expense.expense_date <= end,
    )
    if ctx.branch_ids is not None:
        stmt = stmt.where(Expense.branch_id.in_(ctx.branch_ids))
    stmt = stmt.group_by(Expense.category, Expense.mode).order_by(func.sum(Expense.amount).desc())
    rows = [
        {
            "category": r.category,
            "mode": r.mode,
            "count": int(r.count or 0),
            "amount": round(float(r.amount or 0), 2),
        }
        for r in ctx.db.execute(stmt).all()
    ]
    total = round(sum(r["amount"] for r in rows), 2)
    return _with_report(
        {"period": period, "total": total},
        f"Expenses ({period})",
        [
            {"key": "category", "label": "Category"},
            {"key": "mode", "label": "Mode"},
            {"key": "count", "label": "Count", "num": True},
            {"key": "amount", "label": "Amount", "num": True, "money": True},
        ],
        rows,
    )


def run_business_report(ctx: ToolContext, report_key: str = "daily_sales", period: str = "this_month") -> dict:
    """Run any SKAC operational report (same catalogue as the Reports screen)."""
    key = (report_key or "").strip()
    if key not in REPORT_KEYS:
        return _with_report(
            {"error": f"Unknown report '{report_key}'", "available": REPORT_KEYS},
            "Available reports",
            [
                {"key": "key", "label": "Report key"},
                {"key": "label", "label": "Name"},
            ],
            [{"key": c["key"], "label": c["label"]} for c in report_tables.CATALOG],
        )
    start, end = _period_range(period)
    payload = report_tables.run_report(
        ctx.db,
        org_id=ctx.organization_id,
        scope=ctx.branch_ids,
        key=key,
        start=start,
        end=end,
    )
    rows = list(payload.get("rows") or [])[:2000]
    return _with_report(
        {
            "report_key": key,
            "period": period,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "summary": payload.get("summary"),
        },
        payload.get("title") or key,
        payload.get("columns") or [],
        rows,
    )


def list_capabilities(ctx: ToolContext) -> dict:
    rows = [
        {"name": t.name.replace("_", " "), "description": t.description}
        for t in TOOLS.values()
        if t.name != "list_capabilities"
    ]
    return _with_report(
        {"reports": [c["label"] for c in report_tables.visible_catalog()]},
        "What the assistant can look up",
        [
            {"key": "name", "label": "Topic"},
            {"key": "description", "label": "What you can ask"},
        ],
        rows,
    )


# --- Registry ---
@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable[..., dict]


TOOLS: dict[str, Tool] = {
    "sales_summary": Tool(
        "sales_summary",
        "Total sales revenue and invoice count for a period (today, this_week, this_month, last_month, mtd, ytd).",
        {"period": {"type": "string", "enum": PERIODS}},
        sales_summary,
    ),
    "top_selling_products": Tool(
        "top_selling_products",
        "Top selling products by revenue for a period, optionally filtered by category.",
        {"period": {"type": "string"}, "limit": {"type": "integer"}, "category": {"type": "string", "enum": ["fertilizer", "pesticide", "seed"]}},
        top_selling_products,
    ),
    "profit_summary": Tool(
        "profit_summary",
        "Estimated gross profit, cost, revenue and margin for a period.",
        {"period": {"type": "string"}},
        profit_summary,
    ),
    "highest_margin_products": Tool(
        "highest_margin_products",
        "Products with the highest profit margin percentage; optional min_margin_pct filter.",
        {"limit": {"type": "integer"}, "min_margin_pct": {"type": "number"}},
        highest_margin_products,
    ),
    "customers_highest_outstanding": Tool(
        "customers_highest_outstanding",
        "Customers with the highest outstanding credit balance; optional min_amount filter.",
        {"limit": {"type": "integer"}, "min_amount": {"type": "number"}},
        customers_highest_outstanding,
    ),
    "products_not_sold_since": Tool(
        "products_not_sold_since",
        "Products with no sales in the last N days (default 90).",
        {"days": {"type": "integer"}},
        products_not_sold_since,
    ),
    "products_running_out": Tool(
        "products_running_out",
        "Products forecast to run out of stock within N days.",
        {"within_days": {"type": "integer"}},
        products_running_out,
    ),
    "purchase_recommendations": Tool(
        "purchase_recommendations",
        "AI recommended purchase quantities for products that need restocking.",
        {},
        purchase_recommendations,
    ),
    "compare_periods": Tool(
        "compare_periods",
        "Compare sales revenue between two periods (e.g. this_month vs last_month).",
        {"period_a": {"type": "string"}, "period_b": {"type": "string"}},
        compare_periods,
    ),
    "inactive_credit_customers": Tool(
        "inactive_credit_customers",
        "Farmers with unpaid credit (khata) who have not billed / visited the shop in the last N days. Use when the user asks who owes money and has not come recently. Returns a full downloadable report.",
        {"days": {"type": "integer"}, "min_amount": {"type": "number"}, "limit": {"type": "integer"}},
        inactive_credit_customers,
    ),
    "expenses_summary": Tool(
        "expenses_summary",
        "Shop expenses grouped by category and payment mode for a period.",
        {"period": {"type": "string"}},
        expenses_summary,
    ),
    "run_business_report": Tool(
        "run_business_report",
        "Generate any SKAC operational report as a downloadable table. "
        f"report_key must be one of: {', '.join(REPORT_KEYS)}. "
        "Use when the user asks to generate / download / export a named report "
        "(sales, GST, inventory, outstanding, field visits, profit, etc.).",
        {
            "report_key": {"type": "string", "enum": REPORT_KEYS},
            "period": {"type": "string"},
        },
        run_business_report,
    ),
    "list_capabilities": Tool(
        "list_capabilities",
        "List what the assistant can answer. Use when the user asks what you can do or for help.",
        {},
        list_capabilities,
    ),
}


def run_tool(ctx: ToolContext, name: str, arguments: dict | None = None) -> dict:
    tool = TOOLS.get(name)
    if tool is None:
        raise ValueError(f"Unknown tool: {name}")
    allowed: dict = {}
    for key, value in (arguments or {}).items():
        spec = tool.parameters.get(key)
        if spec is None or value is None:
            continue
        kind = spec.get("type")
        if kind == "integer":
            allowed[key] = _clamp_int(value, 0, -10**9, 10**9)
        elif kind == "number":
            try:
                allowed[key] = float(value)
            except (TypeError, ValueError):
                continue
        else:
            allowed[key] = str(value) if kind == "string" else value
    return tool.fn(ctx, **allowed)
