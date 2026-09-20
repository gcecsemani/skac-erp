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
    # Last known cost, so a recommendation can be turned into a priced PO
    # without a second round-trip per line.
    purchase_price: float
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


def build_forecast(
    *,
    product_id: int,
    product_name: str,
    purchase_price: Decimal | float | None,
    sold_in_window: Decimal,
    sold_last_30: Decimal,
    sold_prev_30: Decimal,
    current_stock: Decimal,
    window_days: int = 90,
    lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
    safety_days: int = DEFAULT_SAFETY_DAYS,
    target_coverage_days: int = DEFAULT_TARGET_COVERAGE_DAYS,
) -> Forecast:
    """The forecast maths, given quantities already read from the ledger.

    Single-product and whole-catalogue forecasting differ only in how they
    fetch those quantities, so the arithmetic lives here once.
    """
    avg_daily = (sold_in_window / Decimal(window_days)) if window_days else Decimal("0")

    # Trend: last 30 days vs the 30 days before that.
    if sold_prev_30 > 0:
        trend_pct = float((sold_last_30 - sold_prev_30) / sold_prev_30 * 100)
    elif sold_last_30 > 0:
        trend_pct = 100.0
    else:
        trend_pct = 0.0
    trend = "rising" if trend_pct > 10 else "falling" if trend_pct < -10 else "stable"

    reorder_point = avg_daily * Decimal(lead_time_days + safety_days)

    stockout_date: str | None = None
    if avg_daily > 0:
        days_left = int(current_stock / avg_daily)
        stockout_date = (date.today() + timedelta(days=days_left)).isoformat()

    target_qty = avg_daily * Decimal(target_coverage_days)
    recommended = target_qty + reorder_point - current_stock
    if recommended < 0:
        recommended = Decimal("0")

    return Forecast(
        product_id=product_id,
        product_name=product_name,
        purchase_price=round(float(purchase_price or 0), 2),
        current_stock=float(current_stock),
        avg_daily_sales=round(float(avg_daily), 3),
        weekly_sales=round(float(avg_daily * 7), 2),
        monthly_sales=round(float(avg_daily * 30), 2),
        trend=trend,
        trend_pct=round(trend_pct, 1),
        reorder_point=round(float(reorder_point), 2),
        estimated_stockout_date=stockout_date,
        recommended_purchase_qty=round(float(recommended), 2),
    )


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

    def sold(since_days: int, until_days: int | None = None) -> Decimal:
        return _sold_quantity(
            db, organization_id=organization_id, product_id=product.id,
            branch_id=branch_id, since=now - timedelta(days=since_days),
            until=None if until_days is None else now - timedelta(days=until_days),
        )

    return build_forecast(
        product_id=product.id,
        product_name=product.name,
        purchase_price=product.purchase_price,
        sold_in_window=sold(window_days),
        sold_last_30=sold(30),
        sold_prev_30=sold(60, 30),
        current_stock=_current_stock(
            db, organization_id=organization_id, product_id=product.id,
            branch_id=branch_id,
        ),
        window_days=window_days,
        lead_time_days=lead_time_days,
        safety_days=safety_days,
        target_coverage_days=target_coverage_days,
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
    if not products:
        return []

    now = datetime.utcnow()
    window_days = 90
    lead_time_days = DEFAULT_LEAD_TIME_DAYS
    safety_days = DEFAULT_SAFETY_DAYS
    target_coverage_days = DEFAULT_TARGET_COVERAGE_DAYS

    def sold_by_product(since: datetime, until: datetime | None = None) -> dict[int, Decimal]:
        stmt = select(
            StockMovement.product_id,
            func.coalesce(func.sum(-StockMovement.quantity), 0),
        ).where(
            StockMovement.organization_id == organization_id,
            StockMovement.movement_type == MovementType.sale,
            StockMovement.occurred_at >= since,
        )
        if until is not None:
            stmt = stmt.where(StockMovement.occurred_at < until)
        if branch_id is not None:
            stmt = stmt.where(StockMovement.branch_id == branch_id)
        stmt = stmt.group_by(StockMovement.product_id)
        return {int(pid): Decimal(qty or 0) for pid, qty in db.execute(stmt)}

    sold_90 = sold_by_product(now - timedelta(days=window_days))
    sold_30 = sold_by_product(now - timedelta(days=30))
    sold_prev = sold_by_product(now - timedelta(days=60), now - timedelta(days=30))

    stock_stmt = select(
        Stock.product_id, func.coalesce(func.sum(Stock.quantity), 0),
    ).where(Stock.organization_id == organization_id)
    if branch_id is not None:
        stock_stmt = stock_stmt.where(Stock.branch_id == branch_id)
    stock_map = {
        int(pid): Decimal(qty or 0)
        for pid, qty in db.execute(stock_stmt.group_by(Stock.product_id))
    }

    results = []
    for product in products:
        forecast = build_forecast(
            product_id=product.id,
            product_name=product.name,
            purchase_price=product.purchase_price,
            sold_in_window=sold_90.get(product.id, Decimal("0")),
            sold_last_30=sold_30.get(product.id, Decimal("0")),
            sold_prev_30=sold_prev.get(product.id, Decimal("0")),
            current_stock=stock_map.get(product.id, Decimal("0")),
            window_days=window_days,
            lead_time_days=lead_time_days,
            safety_days=safety_days,
            target_coverage_days=target_coverage_days,
        )
        if only_needing_purchase and forecast.recommended_purchase_qty <= 0:
            continue
        results.append(forecast.to_dict())
    results.sort(key=lambda r: r["recommended_purchase_qty"], reverse=True)
    return results
