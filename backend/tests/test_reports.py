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


def _vendor(db, org, name):
    from app.models.vendor import Vendor
    v = Vendor(organization_id=org.id, name=name)
    db.add(v)
    db.flush()
    return v


def _grn_stock(db, org, branch, vendor, product, batch_no, qty, when=None, price="100"):
    from app.models.inventory import Batch
    from app.models.purchase import GRN, GRNItem
    from app.services import inventory as inv

    when = when or TODAY
    batch = Batch(
        organization_id=org.id, product_id=product.id, batch_no=batch_no,
        purchase_price=Decimal(price),
    )
    db.add(batch)
    db.flush()
    grn = GRN(
        organization_id=org.id, branch_id=branch.id, vendor_id=vendor.id,
        received_date=when, total_value=Decimal(price) * Decimal(qty),
    )
    db.add(grn)
    db.flush()
    db.add(GRNItem(
        grn_id=grn.id, product_id=product.id, batch_id=batch.id,
        batch_no=batch_no, quantity=Decimal(qty), unit_price=Decimal(price),
    ))
    inv.receive_stock(
        db, organization_id=org.id, branch_id=branch.id,
        product_id=product.id, batch_id=batch.id, quantity=Decimal(qty),
    )
    db.flush()
    return batch


def _vendor_stock(db, org, scope=None, start=TODAY, end=TODAY):
    return run_report(
        db, key="vendor_stock", org_id=org.id, scope=scope, start=start, end=end,
    )["rows"]


def test_vendor_stock_shows_received_sold_and_left(
    db, org, branch, make_product,
):
    from app.services import billing

    vendor = _vendor(db, org, "Coromandel")
    product = make_product(name="DAP 50kg", sku="DAP1")
    _grn_stock(db, org, branch, vendor, product, "B1", 10, price="1200")
    billing.create_and_finalize(
        db,
        organization_id=org.id,
        data=billing.InvoiceInput(
            branch_id=branch.id,
            lines=[billing.LineInput(product_id=product.id, quantity=Decimal("3"))],
        ),
        created_by_user_id=None,
    )
    db.flush()

    rows = {(r["vendor"], r["product"]): r for r in _vendor_stock(db, org)}
    row = rows[("Coromandel", "DAP 50kg")]
    assert row["received"] == 10.0
    assert row["sold"] == 3.0
    assert row["left"] == 7.0
    assert row["value"] == 8400.0


def test_vendor_stock_splits_two_suppliers(db, org, branch, make_product):
    a = _vendor(db, org, "Vendor A")
    b = _vendor(db, org, "Vendor B")
    urea = make_product(name="Urea", sku="U1")
    dap = make_product(name="DAP", sku="D1")
    _grn_stock(db, org, branch, a, urea, "UA", 8)
    _grn_stock(db, org, branch, b, dap, "DB", 4)

    rows = {(r["vendor"], r["product"]): r for r in _vendor_stock(db, org)}
    assert rows[("Vendor A", "Urea")]["received"] == 8.0
    assert rows[("Vendor A", "Urea")]["left"] == 8.0
    assert rows[("Vendor B", "DAP")]["received"] == 4.0
    assert ("Vendor A", "DAP") not in rows


def test_vendor_stock_counts_old_receipts_as_left_not_received(
    db, org, branch, make_product,
):
    from datetime import timedelta
    vendor = _vendor(db, org, "Old Stock Co")
    product = make_product(name="Potash", sku="P1")
    last_month = TODAY - timedelta(days=40)
    _grn_stock(db, org, branch, vendor, product, "OLD", 5, when=last_month)

    rows = {(r["vendor"], r["product"]): r for r in _vendor_stock(db, org)}
    row = rows[("Old Stock Co", "Potash")]
    assert row["received"] == 0.0
    assert row["sold"] == 0.0
    assert row["left"] == 5.0


def test_vendor_stock_is_listed_on_the_reports_screen():
    from app.services.report_tables import visible_catalog
    keys = [c["key"] for c in visible_catalog()]
    assert "vendor_stock" in keys


def _farmer(db, org, name, village, phone):
    from app.models.customer import Customer
    c = Customer(
        organization_id=org.id, name=name, village=village, phone=phone,
        credit_allowed=True,
    )
    db.add(c)
    db.flush()
    return c


def _khata_bill(db, org, branch, farmer, total, paid="0", when=None):
    from app.models.enums import InvoiceStatus, PaymentMode
    from app.models.sales import Invoice
    inv = Invoice(
        organization_id=org.id,
        branch_id=branch.id,
        customer_id=farmer.id,
        invoice_date=when or TODAY,
        status=InvoiceStatus.finalized,
        payment_mode=PaymentMode.credit,
        grand_total=Decimal(total),
        amount_paid=Decimal(paid),
    )
    db.add(inv)
    db.flush()
    return inv


def test_khata_outstanding_uses_dates_and_shows_opening_billed_collected(
    db, org, branch,
):
    from datetime import datetime, timedelta
    from app.models.customer import CustomerPayment

    farmer = _farmer(db, org, "Ramesh", "Kalvai", "9000000101")
    last_month = TODAY - timedelta(days=40)
    _khata_bill(db, org, branch, farmer, "2000", when=last_month)
    db.add(CustomerPayment(
        organization_id=org.id, branch_id=branch.id, customer_id=farmer.id,
        amount=Decimal("500"), paid_at=datetime.combine(TODAY, datetime.min.time()),
        mode="cash",
    ))
    db.flush()

    rows = run_report(
        db, key="customer_outstanding", org_id=org.id, scope=None, start=TODAY, end=TODAY,
    )["rows"]
    row = next(r for r in rows if r["customer"] == "Ramesh")
    assert row["village"] == "Kalvai"
    assert row["opening"] == 2000.0
    assert row["billed"] == 0.0
    assert row["collected"] == 500.0
    assert row["outstanding"] == 1500.0


def test_khata_outstanding_respects_branch(db, org, branch):
    from app.models.organization import Branch
    other = Branch(organization_id=org.id, code="BR02", name="Second")
    db.add(other)
    db.flush()
    here = _farmer(db, org, "Here Farmer", "Kalvai", "9000000102")
    there = _farmer(db, org, "There Farmer", "Chetpet", "9000000103")
    _khata_bill(db, org, branch, here, "800")
    _khata_bill(db, org, other, there, "300")

    this_shop = run_report(
        db, key="customer_outstanding", org_id=org.id, scope=[branch.id],
        start=TODAY, end=TODAY,
    )["rows"]
    names = {r["customer"] for r in this_shop}
    assert "Here Farmer" in names
    assert "There Farmer" not in names
    assert this_shop[0]["outstanding"] == 800.0


def test_khata_by_village_rolls_up_closing_balance(db, org, branch):
    a = _farmer(db, org, "A", "Kalvai", "9000000104")
    b = _farmer(db, org, "B", "Kalvai", "9000000105")
    c = _farmer(db, org, "C", "Chetpet", "9000000106")
    _khata_bill(db, org, branch, a, "1000")
    _khata_bill(db, org, branch, b, "400")
    _khata_bill(db, org, branch, c, "250")

    rows = {
        r["village"]: r
        for r in run_report(
            db, key="khata_by_village", org_id=org.id, scope=None, start=TODAY, end=TODAY,
        )["rows"]
    }
    assert rows["Kalvai"]["farmers"] == 2
    assert rows["Kalvai"]["outstanding"] == 1400.0
    assert rows["Chetpet"]["outstanding"] == 250.0


def test_inactive_khata_lists_only_the_filtered_branch(db, org, branch):
    from datetime import timedelta
    from app.models.organization import Branch

    other = Branch(organization_id=org.id, code="BR02", name="Second")
    db.add(other)
    db.flush()
    here = _farmer(db, org, "Here Farmer", "Kalvai", "9000000201")
    there = _farmer(db, org, "There Farmer", "Chetpet", "9000000202")
    recent = _farmer(db, org, "Recent Farmer", "Kalvai", "9000000203")
    there.outstanding_balance = Decimal("9000")
    old = TODAY - timedelta(days=45)
    _khata_bill(db, org, branch, here, "800", when=old)
    _khata_bill(db, org, other, there, "300", when=old)
    _khata_bill(db, org, branch, recent, "100", when=TODAY)
    db.flush()

    rows = run_report(
        db, key="inactive_khata", org_id=org.id, scope=[branch.id], start=TODAY, end=TODAY,
    )["rows"]
    names = [r["customer"] for r in rows]
    assert names == ["Here Farmer"]
    assert rows[0]["branch"] == branch.name
    assert rows[0]["outstanding"] == 800.0
    assert rows[0]["village"] == "Kalvai"


def test_khata_reports_are_listed_on_the_reports_screen():
    from app.services.report_tables import visible_catalog
    keys = [c["key"] for c in visible_catalog()]
    assert "customer_outstanding" in keys
    assert "khata_by_village" in keys
