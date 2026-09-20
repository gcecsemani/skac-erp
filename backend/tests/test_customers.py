"""Farmer list used by POS must include last bill date."""
from datetime import date, timedelta
from decimal import Decimal

from app.api.v1.customers import list_customers
from app.core.deps import CurrentUser
from app.models.customer import Customer
from app.models.user import Role, User
from app.services import billing


def _current(db, org):
    role = Role(key="owner", name="Owner")
    db.add(role)
    db.flush()
    user = User(
        organization_id=org.id, role_id=role.id, full_name="Owner",
        email="owner-cust@test.in", hashed_password="x",
    )
    db.add(user)
    db.flush()
    return CurrentUser(user=user, role_key="owner", branch_ids=[])


def test_list_customers_includes_last_bill_date(db, org, branch, make_product, receive):
    current = _current(db, org)
    active = Customer(
        organization_id=org.id, name="Active Farmer", phone="9000000001",
        village="Kalvai", district="TVMalai",
    )
    quiet = Customer(
        organization_id=org.id, name="Quiet Farmer", phone="9000000002",
        village="Kalvai", district="TVMalai",
    )
    db.add_all([active, quiet])
    db.flush()

    p = make_product()
    receive(p, "B1", 10)
    last = date.today() - timedelta(days=4)
    billing.create_and_finalize(
        db,
        organization_id=org.id,
        data=billing.InvoiceInput(
            branch_id=branch.id,
            customer_id=active.id,
            invoice_date=last,
            lines=[billing.LineInput(product_id=p.id, quantity=Decimal("1"))],
        ),
        created_by_user_id=None,
    )
    db.flush()

    rows = {c.name: c for c in list_customers(search="Farmer", limit=80, current=current, db=db)}
    assert rows["Active Farmer"].last_bill_date == last
    assert rows["Quiet Farmer"].last_bill_date is None


def test_customer_bills_include_line_items(db, org, branch, make_product, receive):
    current = _current(db, org)
    farmer = Customer(
        organization_id=org.id, name="Billed Farmer", phone="9000000003",
        village="Kalvai", district="TVMalai",
    )
    db.add(farmer)
    db.flush()

    p = make_product(name="UREA 50KG", sku="U50")
    receive(p, "B1", 10)
    billing.create_and_finalize(
        db,
        organization_id=org.id,
        data=billing.InvoiceInput(
            branch_id=branch.id,
            customer_id=farmer.id,
            lines=[billing.LineInput(product_id=p.id, quantity=Decimal("2"))],
        ),
        created_by_user_id=None,
    )
    db.flush()

    from app.api.v1.customers import customer_bills
    bills = customer_bills(farmer.id, limit=12, current=current, db=db)
    assert len(bills) == 1
    assert bills[0]["items"][0]["product_name"] == "UREA 50KG"
    assert bills[0]["items"][0]["quantity"] == 2.0
