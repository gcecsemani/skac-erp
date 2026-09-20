"""Single-product and whole-catalogue forecasts must agree exactly."""
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models.enums import MovementType
from app.models.inventory import StockMovement
from app.services.ai.forecasting import forecast_all, forecast_product


def _sell(db, org, branch, product, batch, qty, days_ago):
    db.add(
        StockMovement(
            organization_id=org.id,
            branch_id=branch.id,
            product_id=product.id,
            batch_id=batch.id,
            movement_type=MovementType.sale,
            quantity=Decimal(-qty),
            occurred_at=datetime.utcnow() - timedelta(days=days_ago),
        )
    )


def test_both_forecast_paths_agree(db, org, branch, make_product, receive):
    """forecast_all batches its queries; it must not drift from forecast_product."""
    rising = make_product(name="Rising", sku="R1")
    falling = make_product(name="Falling", sku="F1")
    idle = make_product(name="Idle", sku="I1")

    rb = receive(rising, "RB", 40)
    fb = receive(falling, "FB", 40)
    receive(idle, "IB", 40)

    for d in (5, 10, 15, 20):
        _sell(db, org, branch, rising, rb, 6, d)
    for d in (40, 45, 50, 55):
        _sell(db, org, branch, falling, fb, 6, d)
    db.flush()

    batched = {r["product_id"]: r for r in forecast_all(db, organization_id=org.id)}

    for product in (rising, falling, idle):
        one = forecast_product(db, organization_id=org.id, product=product).to_dict()
        assert batched[product.id] == one, f"mismatch for {product.name}"

    assert batched[rising.id]["trend"] == "rising"
    assert batched[falling.id]["trend"] == "falling"
    assert batched[idle.id]["trend"] == "stable"


def test_only_needing_purchase_filters_well_stocked_items(
    db, org, branch, make_product, receive
):
    slow = make_product(name="Overstocked", sku="O1")
    b = receive(slow, "OB", 5000)
    _sell(db, org, branch, slow, b, 1, 10)
    db.flush()

    everything = forecast_all(db, organization_id=org.id)
    needed = forecast_all(db, organization_id=org.id, only_needing_purchase=True)

    assert any(r["product_id"] == slow.id for r in everything)
    # 5000 on hand against ~1 unit sold in 90 days needs no purchase.
    assert all(r["recommended_purchase_qty"] > 0 for r in needed)
    assert not any(r["product_id"] == slow.id for r in needed)


def test_stockout_date_is_projected_from_recent_sales(
    db, org, branch, make_product, receive
):
    p = make_product(name="Steady", sku="S1")
    b = receive(p, "SB", 90)
    # One unit a day across the 90 day window. The sale sitting exactly on the
    # window edge may fall outside it, so allow for one.
    for d in range(1, 91):
        _sell(db, org, branch, p, b, 1, d)
    db.flush()

    f = forecast_product(db, organization_id=org.id, product=p)
    assert 0.98 <= f.avg_daily_sales <= 1.0
    # 90 on hand at ~1/day should project roughly three months out.
    assert f.estimated_stockout_date is not None
    assert 85 <= (date.fromisoformat(f.estimated_stockout_date) - date.today()).days <= 95
