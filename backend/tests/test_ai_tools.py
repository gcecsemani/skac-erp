"""Margin ranking was moved into SQL; guard the ordering and the edge cases."""
from decimal import Decimal

from app.services.ai.tools import ToolContext, highest_margin_products


def _ctx(db, org):
    return ToolContext(db=db, organization_id=org.id, branch_ids=None)


def test_products_are_ranked_by_margin_and_capped(db, org, make_product):
    make_product(name="Thin", sku="T1", purchase_price=Decimal("95"),
                 sale_price=Decimal("100"))
    make_product(name="Fat", sku="F1", purchase_price=Decimal("20"),
                 sale_price=Decimal("100"))
    make_product(name="Mid", sku="M1", purchase_price=Decimal("50"),
                 sale_price=Decimal("100"))
    db.flush()

    items = highest_margin_products(_ctx(db, org))["items"]

    assert [i["product"] for i in items] == ["Fat", "Mid", "Thin"]
    assert items[0]["margin_pct"] == 80.0
    assert items[0]["purchase_price"] == 20.0

    assert len(highest_margin_products(_ctx(db, org), limit=2)["items"]) == 2


def test_zero_and_missing_sale_prices_are_skipped_not_divided_by(
    db, org, make_product
):
    """The SQL margin expression divides by sale_price, so these must be filtered."""
    make_product(name="Priced", sku="P1", purchase_price=Decimal("40"),
                 sale_price=Decimal("100"))
    make_product(name="Free", sku="Z1", purchase_price=Decimal("10"),
                 sale_price=Decimal("0"))
    make_product(name="Unpriced", sku="N1", purchase_price=Decimal("10"),
                 sale_price=None)
    db.flush()

    items = highest_margin_products(_ctx(db, org))["items"]

    assert [i["product"] for i in items] == ["Priced"]


def test_min_margin_pct_filters_in_sql(db, org, make_product):
    make_product(name="Fat", sku="F1", purchase_price=Decimal("20"),
                 sale_price=Decimal("100"))
    make_product(name="Thin", sku="T1", purchase_price=Decimal("95"),
                 sale_price=Decimal("100"))
    db.flush()

    items = highest_margin_products(_ctx(db, org), min_margin_pct=50)["items"]

    assert [i["product"] for i in items] == ["Fat"]


def test_deleted_products_stay_out_of_the_ranking(db, org, make_product):
    keep = make_product(name="Keep", sku="K1", purchase_price=Decimal("10"),
                        sale_price=Decimal("100"))
    gone = make_product(name="Gone", sku="G1", purchase_price=Decimal("1"),
                        sale_price=Decimal("100"))
    gone.is_deleted = True
    db.flush()

    items = highest_margin_products(_ctx(db, org))["items"]

    assert [i["product"] for i in items] == [keep.name]
