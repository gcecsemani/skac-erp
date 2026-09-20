"""Reports that were rewritten to filter in SQL must keep the same rows."""
from datetime import date
from decimal import Decimal

from app.services.report_tables import run_report

TODAY = date.today()


def _low_stock(db, org, scope=None):
    return run_report(
        db, key="low_stock", org_id=org.id, scope=scope, start=TODAY, end=TODAY
    )["rows"]


def test_low_stock_lists_items_at_or_below_reorder_level(
    db, org, branch, make_product, receive
):
    healthy = make_product(name="Healthy", sku="H1", reorder_level=Decimal("5"))
    at_level = make_product(name="AtLevel", sku="A1", reorder_level=Decimal("5"))
    below = make_product(name="Below", sku="B1", reorder_level=Decimal("5"))

    receive(healthy, "H", 20)
    receive(at_level, "A", 5)
    receive(below, "B", 2)

    rows = {r["product"]: r for r in _low_stock(db, org)}

    assert "Healthy" not in rows
    assert rows["AtLevel"]["status"] == "Low stock"
    assert rows["AtLevel"]["on_hand"] == 5.0
    assert rows["Below"]["status"] == "Low stock"


def test_low_stock_includes_products_with_no_stock_row_at_all(
    db, org, branch, make_product
):
    """A never-stocked SKU has no row in `stock`; the outer join must keep it."""
    make_product(name="NeverStocked", sku="N1", reorder_level=Decimal("0"))
    db.flush()

    rows = {r["product"]: r for r in _low_stock(db, org)}

    assert rows["NeverStocked"]["status"] == "Out of stock"
    assert rows["NeverStocked"]["on_hand"] == 0.0


def test_low_stock_keeps_zero_qty_even_when_no_reorder_level_is_set(
    db, org, branch, make_product, receive
):
    sold_out = make_product(name="SoldOut", sku="S1", reorder_level=Decimal("0"))
    stocked = make_product(name="Stocked", sku="K1", reorder_level=Decimal("0"))
    receive(sold_out, "S", 0)
    receive(stocked, "K", 7)

    rows = {r["product"]: r for r in _low_stock(db, org)}

    assert rows["SoldOut"]["status"] == "Out of stock"
    # No reorder level and stock on hand: nothing to flag.
    assert "Stocked" not in rows


def test_low_stock_respects_branch_scope(db, org, branch, make_product, receive):
    from app.models.inventory import Batch, Stock
    from app.models.organization import Branch

    other = Branch(organization_id=org.id, code="BR02", name="Second")
    db.add(other)
    db.flush()

    p = make_product(name="Split", sku="SP1", reorder_level=Decimal("10"))
    b = Batch(organization_id=org.id, product_id=p.id, batch_no="SB",
              purchase_price=Decimal("10"))
    db.add(b)
    db.flush()
    # 8 here, 8 at the other shop: short at each branch, healthy org-wide.
    db.add(Stock(organization_id=org.id, branch_id=branch.id, product_id=p.id,
                 batch_id=b.id, quantity=Decimal("8")))
    db.add(Stock(organization_id=org.id, branch_id=other.id, product_id=p.id,
                 batch_id=b.id, quantity=Decimal("8")))
    db.flush()

    this_branch = {r["product"]: r for r in _low_stock(db, org, scope=[branch.id])}
    org_wide = {r["product"]: r for r in _low_stock(db, org)}

    assert this_branch["Split"]["on_hand"] == 8.0
    assert "Split" not in org_wide
