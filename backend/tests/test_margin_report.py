"""Margin / P&L reports must cost a loose sale as a fraction of a pack.

These go through the real billing service so the report sees exactly what POS
writes: kg on InvoiceItem.quantity and the billed unit on InvoiceItem.unit.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.services import billing
from app.services.report_tables import run_report

TODAY = date.today()


def _bill(db, org, branch, product, qty, unit=None, unit_price=None):
    inv = billing.create_and_finalize(
        db,
        organization_id=org.id,
        data=billing.InvoiceInput(
            branch_id=branch.id,
            lines=[
                billing.LineInput(
                    product_id=product.id,
                    quantity=Decimal(str(qty)),
                    unit=unit,
                    unit_price=None if unit_price is None else Decimal(str(unit_price)),
                )
            ],
        ),
        created_by_user_id=None,
    )
    db.flush()
    return inv


def _margin(db, org, sku):
    rows = run_report(
        db, key="product_profit", org_id=org.id, scope=None, start=TODAY, end=TODAY
    )["rows"]
    return next(r for r in rows if r["sku"] == sku)


def test_whole_pack_sale_costs_one_pack_each(db, org, branch, make_product, receive):
    p = make_product(
        name="FACT AVALURPET - 50 KGS", sku="F50", sale_price="1500",
        attributes={"packing": "50 KGS"},
    )
    receive(p, "B1", 10, purchase_price="1200")

    _bill(db, org, branch, p, 3, unit="50 KGS")

    row = _margin(db, org, "F50")
    assert row["qty"] == 3.0
    # 3 x 1500 taxable, 3 bags x Rs.1200 cost.
    assert row["sales"] == 4500.0
    assert row["cost"] == 3600.0
    assert row["profit"] == 900.0


def test_loose_kg_sale_costs_a_fraction_of_the_pack(
    db, org, branch, make_product, receive
):
    p = make_product(
        name="FACT AVALURPET - 50 KGS", sku="F50", sale_price="1500",
        attributes={"packing": "50 KGS"},
    )
    receive(p, "B1", 10, purchase_price="1200")

    # 10 kg scooped out of a 50 kg bag = one fifth of a bag.
    _bill(db, org, branch, p, 10, unit="kg")

    row = _margin(db, org, "F50")
    assert row["qty"] == 0.2
    # loose price is 1500/50 = Rs.30/kg, so 10 kg = Rs.300 taxable.
    assert row["sales"] == 300.0
    assert row["cost"] == 240.0
    assert row["profit"] == 60.0


def test_name_pack_size_beats_stale_attributes_packing(
    db, org, branch, make_product, receive
):
    """Staff renamed the bag to 45 KGS; attributes.packing still says 50 KGS."""
    p = make_product(
        name="UREA - 45KGS", sku="U45", sale_price="900",
        attributes={"packing": "50 KGS"},
    )
    receive(p, "B1", 10, purchase_price="450")

    # 45 kg loose is exactly one bag, so COGS is one bag: Rs.450.
    _bill(db, org, branch, p, 45, unit="kg")

    row = _margin(db, org, "U45")
    assert row["qty"] == 1.0
    assert row["sales"] == 900.0
    assert row["cost"] == 450.0
    assert row["profit"] == 450.0


def test_unparseable_packing_string_still_divides_by_the_bag(
    db, org, branch, make_product, receive
):
    """CAST('1x50 KGS') reads 1, which used to cost 50 kg as 50 whole bags."""
    p = make_product(
        name="DAP - 50KGS", sku="D50", sale_price="1500",
        attributes={"packing": "1x50 KGS"},
    )
    receive(p, "B1", 10, purchase_price="1350")

    _bill(db, org, branch, p, 50, unit="kg")

    row = _margin(db, org, "D50")
    assert row["qty"] == 1.0
    # Old report: 50 x Rs.1350 = Rs.67,500 cost and a Rs.66,000 "loss".
    assert row["cost"] == 1350.0
    assert row["profit"] == 150.0


def test_bottle_pack_is_never_divided(db, org, branch, make_product, receive):
    p = make_product(
        name="AAGOR - 100MLS", sku="A100", sale_price="250",
        attributes={"packing": "100MLS"}, base_unit="bottle",
    )
    receive(p, "B1", 10, purchase_price="200")

    _bill(db, org, branch, p, 2, unit="100MLS")

    row = _margin(db, org, "A100")
    assert row["qty"] == 2.0
    assert row["cost"] == 400.0
    assert row["profit"] == 100.0


def test_whole_packet_billed_in_grams_is_not_loose(
    db, org, branch, make_product, receive
):
    """Unit 'gms' on a 500 g packet means two packets, not two grams."""
    p = make_product(
        name="SEED PACK - 500GMS", sku="S500", sale_price="200",
        attributes={"packing": "500GMS"}, base_unit="packet",
    )
    receive(p, "B1", 10, purchase_price="150")

    _bill(db, org, branch, p, 2, unit="gms", unit_price="200")

    row = _margin(db, org, "S500")
    assert row["qty"] == 2.0
    # Dividing by 500 made this cost 60 paise and look like a 99.8% margin.
    assert row["cost"] == 300.0
    assert row["profit"] == 100.0


def test_profit_loss_and_dashboard_agree_with_the_margin_report(
    db, org, branch, make_product, receive
):
    from app.api.v1.reports import dashboard_gross_profit

    p = make_product(
        name="UREA - 45KGS", sku="U45", sale_price="900",
        attributes={"packing": "50 KGS"},
    )
    receive(p, "B1", 10, purchase_price="450")
    _bill(db, org, branch, p, 45, unit="kg")
    _bill(db, org, branch, p, 2, unit="45kg")

    margin = _margin(db, org, "U45")
    assert margin["cost"] == 1350.0  # 3 bags
    assert margin["profit"] == 1350.0

    pl = {r["line"]: r["amount"] for r in run_report(
        db, key="profit_loss", org_id=org.id, scope=None, start=TODAY, end=TODAY
    )["rows"]}
    assert pl["Cost of goods sold"] == 1350.0
    assert pl["Gross profit"] == 1350.0

    assert dashboard_gross_profit(db, org.id, None, TODAY, TODAY) == 1350.0


def test_product_sales_qty_is_pack_equivalent(db, org, branch, make_product, receive):
    p = make_product(
        name="UREA - 45KGS", sku="U45", sale_price="900",
        attributes={"packing": "50 KGS"},
    )
    receive(p, "B1", 10, purchase_price="450")
    _bill(db, org, branch, p, 45, unit="kg")

    rows = run_report(
        db, key="product_sales", org_id=org.id, scope=None, start=TODAY, end=TODAY
    )["rows"]
    assert next(r for r in rows if r["product"] == "UREA - 45KGS")["qty"] == 1.0


def test_kg_at_bag_price_costs_the_bag_that_left_the_godown(
    db, org, branch, make_product, receive
):
    """Historical POS wrote unit=kg on a ₹1,100 bag. Stock issued 1 bag."""
    from app.models.enums import InvoiceStatus, PaymentMode
    from app.models.sales import Invoice, InvoiceItem

    p = make_product(
        name="PADDY 50KG", sku="PADDY-50KG", sale_price="1100",
        purchase_price="1000", base_unit="kg",
    )
    batch = receive(p, "B1100", 20, purchase_price="1000")

    inv = Invoice(
        organization_id=org.id,
        branch_id=branch.id,
        invoice_date=TODAY,
        status=InvoiceStatus.finalized,
        payment_mode=PaymentMode.cash,
    )
    db.add(inv)
    db.flush()
    # Whole bag stored as kg @ bag price (the live AVL/00006 shape).
    db.add(InvoiceItem(
        invoice_id=inv.id, product_id=p.id, batch_id=batch.id,
        product_name=p.name, unit="kg", quantity=Decimal("1"),
        unit_price=Decimal("1100"), taxable_value=Decimal("1100"),
        tax_amount=Decimal("0"), line_total=Decimal("1100"),
    ))
    # True loose kilo on the same SKU.
    db.add(InvoiceItem(
        invoice_id=inv.id, product_id=p.id, batch_id=batch.id,
        product_name=p.name, unit="kg", quantity=Decimal("1"),
        unit_price=Decimal("22"), taxable_value=Decimal("22"),
        tax_amount=Decimal("0"), line_total=Decimal("22"),
    ))
    db.flush()

    row = _margin(db, org, "PADDY-50KG")
    assert row["qty"] == 1.02
    assert row["sales"] == 1122.0
    assert row["cost"] == 1020.0
    assert row["profit"] == 102.0


def test_editing_batch_cost_updates_the_margin_report(
    db, org, branch, make_product, receive
):
    from app.api.v1.inventory import update_batch_cost
    from app.core.deps import CurrentUser
    from app.models.user import Role, User
    from app.schemas.masters import BatchCostIn

    p = make_product(name="UREA 50KG", sku="UREA-50KG", sale_price="310", purchase_price="300")
    batch = receive(p, "RETTEST01", 10, purchase_price="100")
    _bill(db, org, branch, p, 1, unit="50kg")

    assert _margin(db, org, "UREA-50KG")["cost"] == 100.0

    role = Role(key="owner", name="Owner")
    db.add(role)
    db.flush()
    user = User(
        organization_id=org.id, role_id=role.id, full_name="Owner",
        email="owner@test.in", hashed_password="x",
    )
    db.add(user)
    db.flush()
    current = CurrentUser(user=user, role_key="owner", branch_ids=[])
    update_batch_cost(batch.id, BatchCostIn(purchase_price=Decimal("300")), current, db)

    row = _margin(db, org, "UREA-50KG")
    assert row["cost"] == 300.0
    assert row["profit"] == 10.0


def test_farmer_margin_uses_pack_equivalent_cost(
    db, org, branch, make_product, receive
):
    from app.models.customer import Customer

    farmer = Customer(organization_id=org.id, name="Selvam", village="Kalvai")
    db.add(farmer)
    db.flush()

    p = make_product(
        name="UREA - 45KGS", sku="U45", sale_price="900",
        attributes={"packing": "50 KGS"},
    )
    receive(p, "B1", 10, purchase_price="450")
    billing.create_and_finalize(
        db,
        organization_id=org.id,
        data=billing.InvoiceInput(
            branch_id=branch.id,
            customer_id=farmer.id,
            lines=[billing.LineInput(product_id=p.id, quantity=Decimal("45"), unit="kg")],
        ),
        created_by_user_id=None,
    )
    db.flush()

    rows = run_report(
        db, key="farmer_profit", org_id=org.id, scope=None, start=TODAY, end=TODAY
    )["rows"]
    row = next(r for r in rows if r["farmer"] == "Selvam")
    assert row["bills"] == 1
    assert row["cost"] == 450.0
    assert row["profit"] == 450.0


def test_discount_cuts_sales_and_profit_not_list_price_or_cost(
    db, org, branch, make_product, receive
):
    """POS stores list rate + discount. Margin must use the net taxable."""
    p = make_product(
        name="UREA - 50KGS", sku="U50", sale_price="310", gst_rate="0",
        attributes={"packing": "50 KGS"},
    )
    receive(p, "B1", 10, purchase_price="300")

    inv = billing.create_and_finalize(
        db,
        organization_id=org.id,
        data=billing.InvoiceInput(
            branch_id=branch.id,
            lines=[
                billing.LineInput(
                    product_id=p.id, quantity=Decimal("1"), unit="50 KGS",
                    unit_price=Decimal("310"), discount=Decimal("10"),
                )
            ],
        ),
        created_by_user_id=None,
    )
    db.flush()

    from app.models.sales import InvoiceItem
    item = db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)).one()
    assert item.unit_price == Decimal("310.00")
    assert item.discount == Decimal("10.00")
    assert item.taxable_value == Decimal("300.00")

    row = _margin(db, org, "U50")
    assert row["discount"] == 10.0
    assert row["sales"] == 300.0
    assert row["cost"] == 300.0
    assert row["profit"] == 0.0

    pl = {r["line"]: r["amount"] for r in run_report(
        db, key="profit_loss", org_id=org.id, scope=None, start=TODAY, end=TODAY
    )["rows"]}
    assert pl["Gross sales (excl. GST)"] == 310.0
    assert pl["Less: Discounts"] == 10.0
    assert pl["Net sales (excl. GST)"] == 300.0
    assert pl["Gross profit"] == 0.0
