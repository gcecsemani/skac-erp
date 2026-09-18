"""COGS must use pack-equivalent qty, not billed kg × pack cost."""
from decimal import Decimal

from app.core.units import billed_to_stock_qty, is_loose_sale, pack_info
from app.services.cogs import line_cogs_amount


class _P:
    def __init__(self, name, **attrs):
        self.name = name
        self.attributes = attrs
        self.base_unit = "kg"


def test_loose_kg_from_50kg_bag_is_fraction_of_pack():
    p = _P(
        "FACT AVALURPET - 50 KGS",
        packing="50 KGS",
        pack_size="50",
        loose_unit="kg",
        sell_loose=True,
    )
    assert pack_info(p).pack_size == Decimal("50")
    assert is_loose_sale(p, "kg")
    assert billed_to_stock_qty(p, Decimal("50"), "kg") == Decimal("1.000")
    # Old reports did 50 × ₹2136 = ₹1,06,800. Real COGS is one bag.
    assert line_cogs_amount(p, 50, "kg", 2136) == Decimal("2136.000")
    assert billed_to_stock_qty(p, Decimal("167"), "kg") == Decimal("3.340")


def test_whole_bag_stays_one_pack():
    p = _P(
        "FACT AVALURPET - 50 KGS",
        packing="50 KGS",
        pack_size="50",
        loose_unit="kg",
        sell_loose=True,
    )
    assert not is_loose_sale(p, "50kg")
    assert not is_loose_sale(p, "50 KGS")
    assert billed_to_stock_qty(p, Decimal("3"), "50 KGS") == Decimal("3.000")
    assert line_cogs_amount(p, 3, "50 KGS", 2136) == Decimal("6408.000")


def test_bottle_is_not_treated_as_loose_weight():
    p = _P("AAGOR - 100MLS", packing="100MLS")
    assert not pack_info(p).allows_loose
    assert billed_to_stock_qty(p, Decimal("2"), "100MLS") == Decimal("2.000")
    assert billed_to_stock_qty(p, Decimal("2"), "ml") == Decimal("2.000")
