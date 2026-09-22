"""Farmer list used by POS must include last bill date."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.api.v1.customers import create_customer, list_customers
from app.core.deps import CurrentUser
from app.models.customer import Customer
from app.models.user import Role, User
from app.schemas.masters import CustomerCreate
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


def test_create_customer_restores_soft_deleted_same_phone(db, org):
    current = _current(db, org)
    old = Customer(
        organization_id=org.id, name="VENAYAGAM", phone="8098521749",
        village="Aarpakkam", district="Tiruvannamalai", is_deleted=True,
    )
    db.add(old)
    db.flush()

    restored = create_customer(
        CustomerCreate(
            name="VENAYAGAM",
            phone="8098521749",
            village="AARPAKKAM",
            district="Tiruvannamalai",
        ),
        current=current,
        db=db,
    )
    db.refresh(old)
    assert restored.id == old.id
    assert old.is_deleted is False
    assert old.village == "AARPAKKAM"


def test_customer_ledger_shows_sales_return_without_cancelling_invoice(db, org, branch):
    from datetime import date
    from app.api.v1.customers import customer_ledger
    from app.models.enums import InvoiceStatus, PaymentMode
    from app.models.returns import CreditNote
    from app.models.sales import Invoice

    current = _current(db, org)
    farmer = Customer(
        organization_id=org.id, name="Ramesh", phone="9000000301",
        village="Kalvai", outstanding_balance=Decimal("800"), credit_allowed=True,
    )
    db.add(farmer)
    db.flush()
    inv = Invoice(
        organization_id=org.id, branch_id=branch.id, customer_id=farmer.id,
        invoice_date=date.today(), status=InvoiceStatus.finalized,
        payment_mode=PaymentMode.credit, invoice_no="INV/1",
        grand_total=Decimal("1000"), amount_paid=Decimal("0"),
    )
    db.add(inv)
    db.flush()
    db.add(CreditNote(
        organization_id=org.id, branch_id=branch.id, invoice_id=inv.id,
        customer_id=farmer.id, note_no="CN/1", note_date=date.today(),
        reason="Damaged", total=Decimal("200"),
    ))
    db.flush()

    out = customer_ledger(farmer.id, current, db)
    assert inv.status == InvoiceStatus.finalized
    kinds = [e["kind"] for e in out["entries"]]
    assert kinds == ["invoice", "return"]
    assert out["entries"][-1]["balance"] == 800.0
    assert out["invoices"][0]["returned"] == 200.0
    assert out["invoices"][0]["outstanding"] == 800.0
    assert out["has_opening"] is False


def test_collection_does_not_settle_already_returned_amount(db, org, branch):
    from datetime import date
    from app.api.v1.customers import _allocate_receipt_to_invoices
    from app.models.customer import CustomerPayment
    from app.models.enums import InvoiceStatus, PaymentMode
    from app.models.returns import CreditNote
    from app.models.sales import Invoice

    farmer = Customer(
        organization_id=org.id, name="Ramesh", phone="9000000302",
        village="Kalvai", outstanding_balance=Decimal("800"), credit_allowed=True,
    )
    db.add(farmer)
    db.flush()
    inv = Invoice(
        organization_id=org.id, branch_id=branch.id, customer_id=farmer.id,
        invoice_date=date.today(), status=InvoiceStatus.finalized,
        payment_mode=PaymentMode.credit, invoice_no="INV/2",
        grand_total=Decimal("1000"), amount_paid=Decimal("0"),
    )
    db.add(inv)
    db.flush()
    db.add(CreditNote(
        organization_id=org.id, branch_id=branch.id, invoice_id=inv.id,
        customer_id=farmer.id, note_no="CN/2", note_date=date.today(),
        reason="Damaged", total=Decimal("200"),
    ))
    pay = CustomerPayment(
        organization_id=org.id, branch_id=branch.id, customer_id=farmer.id,
        amount=Decimal("1000"), mode="cash",
    )
    db.add(pay)
    db.flush()

    leftover = _allocate_receipt_to_invoices(
        db, customer_id=farmer.id, amount=Decimal("1000"), payment_id=pay.id,
    )
    assert inv.amount_paid == Decimal("800.00")
    assert leftover == Decimal("200.00")


def test_create_customer_rejects_duplicate_active_phone(db, org):
    current = _current(db, org)
    db.add(Customer(
        organization_id=org.id, name="Existing", phone="8098521749",
        village="Aarpakkam", district="Tiruvannamalai",
    ))
    db.flush()

    with pytest.raises(HTTPException) as err:
        create_customer(
            CustomerCreate(
                name="VENAYAGAM",
                phone="8098521749",
                village="AARPAKKAM",
                district="Tiruvannamalai",
            ),
            current=current,
            db=db,
        )
    assert err.value.status_code == 409
