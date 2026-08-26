"""AI Smart Inventory: demand forecasting and purchase recommendations.

Pure, deterministic computations over the stock-movement ledger. These feed
both the /ai/forecast endpoints and the natural-language assistant tools.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import MovementType
from app.models.inventory import Stock, StockMovement
from app.models.product import Product

# Tunables (could later be per-product / per-branch config).
DEFAULT_LEAD_TIME_DAYS = 7
DEFAULT_SAFETY_DAYS = 5
DEFAULT_TARGET_COVERAGE_DAYS = 30


@dataclass
class Forecast:
    product_id: int
    product_name: str
    current_stock: float
    avg_daily_sales: float
    weekly_sales: float
    monthly_sales: float
    trend: str            # rising | falling | stable
    trend_pct: float
    reorder_point: float
    estimated_stockout_date: str | None
    recommended_purchase_qty: float

    def to_dict(self) -> dict:
        return asdict(self)


def _sold_quantity(
    db: Session, *, organization_id: int, product_id: int,
    branch_id: int | None, since: datetime, until: datetime | None = None,
) -> Decimal:
    """Total quantity sold (positive) in a window from the movement ledger."""
    stmt = select(func.coalesce(func.sum(-StockMovement.quantity), 0)).where(
        StockMovement.organization_id == organization_id,
        StockMovement.product_id == product_id,
        StockMovement.movement_type == MovementType.sale,
        StockMovement.occurred_at >= since,
    )
    if until is not None:
        stmt = stmt.where(StockMovement.occurred_at < until)
    if branch_id is not None:
        stmt = stmt.where(StockMovement.branch_id == branch_id)
    return Decimal(db.scalar(stmt) or 0)


def _current_stock(
    db: Session, *, organization_id: int, product_id: int, branch_id: int | None
) -> Decimal:
    stmt = select(func.coalesce(func.sum(Stock.quantity), 0)).where(
        Stock.organization_id == organization_id, Stock.product_id == product_id
    )
    if branch_id is not None:
        stmt = stmt.where(Stock.branch_id == branch_id)
    return Decimal(db.scalar(stmt) or 0)


def forecast_product(
    db: Session,
    *,
    organization_id: int,
    product: Product,
    branch_id: int | None = None,
    window_days: int = 90,
    lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
    safety_days: int = DEFAULT_SAFETY_DAYS,
    target_coverage_days: int = DEFAULT_TARGET_COVERAGE_DAYS,
) -> Forecast:
    now = datetime.utcnow()
    since = now - timedelta(days=window_days)

    sold = _sold_quantity(
        db, organization_id=organization_id, product_id=product.id,
        branch_id=branch_id, since=since,
    )
    avg_daily = (sold / Decimal(window_days)) if window_days else Decimal("0")

    # Trend: last 30 days vs the 30 days before that.
    recent = _sold_quantity(
        db, organization_id=organization_id, product_id=product.id,
        branch_id=branch_id, since=now - timedelta(days=30),
    )
    prev = _sold_quantity(
        db, organization_id=organization_id, product_id=product.id,
        branch_id=branch_id, since=now - timedelta(days=60),
        until=now - timedelta(days=30),
    )
    if prev > 0:
        trend_pct = float((recent - prev) / prev * 100)
    elif recent > 0:
        trend_pct = 100.0
    else:
        trend_pct = 0.0
    trend = "rising" if trend_pct > 10 else "falling" if trend_pct < -10 else "stable"

    current = _current_stock(
        db, organization_id=organization_id, product_id=product.id, branch_id=branch_id
    )

    reorder_point = avg_daily * Decimal(lead_time_days + safety_days)

    stockout_date: str | None = None
    if avg_daily > 0:
        days_left = int((current / avg_daily))
        stockout_date = (date.today() + timedelta(days=days_left)).isoformat()

    target_qty = avg_daily * Decimal(target_coverage_days)
    recommended = target_qty + reorder_point - current
    if recommended < 0:
        recommended = Decimal("0")

    return Forecast(
        product_id=product.id,
        product_name=product.name,
        current_stock=float(current),
        avg_daily_sales=round(float(avg_daily), 3),
        weekly_sales=round(float(avg_daily * 7), 2),
        monthly_sales=round(float(avg_daily * 30), 2),
        trend=trend,
        trend_pct=round(trend_pct, 1),
        reorder_point=round(float(reorder_point), 2),
        estimated_stockout_date=stockout_date,
        recommended_purchase_qty=round(float(recommended), 2),
    )


def forecast_all(
    db: Session,
    *,
    organization_id: int,
    branch_id: int | None = None,
    only_needing_purchase: bool = False,
) -> list[dict]:
    products = db.scalars(
        select(Product).where(
            Product.organization_id == organization_id,
            Product.is_active.is_(True),
            Product.is_deleted.is_(False),
        )
    ).all()
    results = []
    for product in products:
        fc = forecast_product(
            db, organization_id=organization_id, product=product, branch_id=branch_id
        )
        if only_needing_purchase and fc.recommended_purchase_qty <= 0:
            continue
        results.append(fc.to_dict())
    results.sort(key=lambda r: r["recommended_purchase_qty"], reverse=True)
    return results
