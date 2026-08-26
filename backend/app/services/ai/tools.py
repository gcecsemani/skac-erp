"""Secure, vetted business-query tools for the AI assistant.

The LLM is NEVER given raw SQL access. It may only choose one of these
registered tools and supply typed, validated arguments. Each tool runs a
parameterized query scoped to the caller's organization and branch access.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.enums import InvoiceStatus, ProductCategory
from app.models.product import Product
from app.models.sales import Invoice, InvoiceItem
from app.services.ai import forecasting


@dataclass
class ToolContext:
    db: Session
    organization_id: int
    branch_ids: list[int] | None  # None => all branches (owner/admin)


# --- date range helpers ---
def _period_range(period: str) -> tuple[date, date]:
    today = date.today()
    if period == "today":
        return today, today
    if period == "this_week":
        return today - timedelta(days=today.weekday()), today
    if period == "this_month":
        return today.replace(day=1), today
    if period == "last_month":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    if period == "mtd":
        return today.replace(day=1), today
    if period == "ytd":
        fy_start = today.year if today.month >= 4 else today.year - 1
        return date(fy_start, 4, 1), today
    if period == "last_90_days":
        return today - timedelta(days=90), today
    if period == "last_30_days":
        return today - timedelta(days=30), today
    # default: this month
    return today.replace(day=1), today


def _scope(stmt, ctx: ToolContext):
    stmt = stmt.where(Invoice.organization_id == ctx.organization_id)
    if ctx.branch_ids is not None:
        stmt = stmt.where(Invoice.branch_id.in_(ctx.branch_ids))
    return stmt.where(Invoice.status == InvoiceStatus.finalized)


# --- Tools ---
def top_selling_products(ctx: ToolContext, period: str = "this_month", limit: int = 10, category: str | None = None) -> dict:
    start, end = _period_range(period)
    stmt = (
        select(
            InvoiceItem.product_id,
            InvoiceItem.product_name,
            func.sum(InvoiceItem.quantity).label("qty"),
            func.sum(InvoiceItem.line_total).label("revenue"),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .group_by(InvoiceItem.product_id, InvoiceItem.product_name)
        .order_by(func.sum(InvoiceItem.line_total).desc())
        .limit(limit)
    )
    stmt = _scope(stmt, ctx).where(
        Invoice.invoice_date >= start, Invoice.invoice_date <= end
    )
    if category:
        stmt = stmt.join(Product, Product.id == InvoiceItem.product_id).where(
            Product.category == ProductCategory(category)
        )
    rows = ctx.db.execute(stmt).all()
    return {
        "period": period,
        "items": [
            {"product": r.product_name, "quantity": float(r.qty or 0),
             "revenue": float(r.revenue or 0)}
            for r in rows
        ],
    }


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
    return {
        "period": period,
        "revenue": float(row.revenue or 0),
        "invoice_count": int(row.invoices or 0),
    }


def profit_summary(ctx: ToolContext, period: str = "this_month") -> dict:
    """Estimated gross profit = taxable revenue - (qty * product purchase price)."""
    start, end = _period_range(period)
    stmt = (
        select(
            func.coalesce(func.sum(InvoiceItem.taxable_value), 0).label("revenue"),
            func.coalesce(func.sum(InvoiceItem.quantity * Product.purchase_price), 0).label("cost"),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
    )
    stmt = _scope(stmt, ctx).where(
        Invoice.invoice_date >= start, Invoice.invoice_date <= end
    )
    row = ctx.db.execute(stmt).one()
    revenue = float(row.revenue or 0)
    cost = float(row.cost or 0)
    return {
        "period": period,
        "revenue": round(revenue, 2),
        "cost": round(cost, 2),
        "gross_profit": round(revenue - cost, 2),
        "margin_pct": round((revenue - cost) / revenue * 100, 1) if revenue else 0.0,
    }


def highest_margin_products(ctx: ToolContext, limit: int = 10, min_margin_pct: float | None = None) -> dict:
    products = ctx.db.scalars(
        select(Product).where(
            Product.organization_id == ctx.organization_id,
            Product.is_deleted.is_(False),
        )
    ).all()
    out = []
    for p in products:
        if p.sale_price and p.sale_price > 0:
            margin = float((p.sale_price - p.purchase_price) / p.sale_price * 100)
            out.append({"product": p.name, "margin_pct": round(margin, 1),
                        "sale_price": float(p.sale_price),
                        "purchase_price": float(p.purchase_price)})
    if min_margin_pct is not None:
        out = [o for o in out if o["margin_pct"] >= min_margin_pct]
    out.sort(key=lambda o: o["margin_pct"], reverse=True)
    return {"items": out[:limit]}


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
    return {
        "customers": [
            {"name": c.name, "phone": c.phone, "village": c.village,
             "outstanding": float(c.outstanding_balance)}
            for c in rows
        ]
    }


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
    return {"days": days, "count": len(stale), "products": stale}


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
    return {"within_days": within_days, "products": soon}


def purchase_recommendations(ctx: ToolContext) -> dict:
    branch_id = ctx.branch_ids[0] if ctx.branch_ids and len(ctx.branch_ids) == 1 else None
    recs = forecasting.forecast_all(
        ctx.db, organization_id=ctx.organization_id, branch_id=branch_id,
        only_needing_purchase=True,
    )
    return {"recommendations": recs}


def compare_periods(ctx: ToolContext, period_a: str = "this_month", period_b: str = "last_month") -> dict:
    a = sales_summary(ctx, period=period_a)
    b = sales_summary(ctx, period=period_b)
    delta = a["revenue"] - b["revenue"]
    pct = (delta / b["revenue"] * 100) if b["revenue"] else 0.0
    return {
        "period_a": a, "period_b": b,
        "change": round(delta, 2), "change_pct": round(pct, 1),
    }


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
        {"period": {"type": "string", "enum": ["today", "this_week", "this_month", "last_month", "mtd", "ytd", "last_30_days", "last_90_days"]}},
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
}


def run_tool(ctx: ToolContext, name: str, arguments: dict | None = None) -> dict:
    tool = TOOLS.get(name)
    if tool is None:
        raise ValueError(f"Unknown tool: {name}")
    # Only pass through arguments declared in the tool schema (whitelist).
    allowed = {k: v for k, v in (arguments or {}).items() if k in tool.parameters}
    return tool.fn(ctx, **allowed)
