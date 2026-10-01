"""A sales return reduces khata only for what is still unpaid."""
from decimal import Decimal

from app.api.v1.returns import CreditNoteIn, ReturnItemIn, create_credit_note, split_return_amounts
from app.models.customer import Customer
from app.models.enums import PaymentMode
from app.models.user import Role, User
from app.core.deps import CurrentUser
from app.services import billing


def _current(db, org):
    role = Role(key="owner", name="Owner")
    db.add(role)
    db.flush()
    user = User(
        organization_id=org.id, role_id=role.id, full_name="Owner",
        email="owner-ret@test.in", hashed_password="x",
    )
    db.add(user)
    db.flush()
    return CurrentUser(user=user, role_key="owner", branch_ids=[])


def _farmer(db, org, phone, outstanding="0"):
    farmer = Customer(
        organization_id=org.id, name="Ravi", phone=phone,
        credit_allowed=True, outstanding_balance=Decimal(outstanding),
    )
    db.add(farmer)
    db.flush()
    return farmer


def _sell(db, org, branch, farmer, product, paid):
    return billing.create_and_finalize(
        db,
        organization_id=org.id,
        created_by_user_id=None,
        data=billing.InvoiceInput(
            branch_id=branch.id,
            customer_id=farmer.id,
            payment_mode=PaymentMode.credit if Decimal(paid) == 0 else PaymentMode.cash,
            amount_paid=Decimal(paid),
            lines=[billing.LineInput(product_id=product.id, quantity=Decimal("1"))],
        ),
    )


def test_split_keeps_paid_money_out_of_khata():
    khata, refund = split_return_amounts(
        grand_total=Decimal("500"), amount_paid=Decimal("500"),
        prior_credits=Decimal("0"), return_total=Decimal("500"),
        outstanding=Decimal("0"),
    )
    assert khata == Decimal("0.00")
    assert refund == Decimal("500.00")


def test_cash_return_does_not_make_outstanding_negative(db, org, branch, make_product, receive):
    farmer = _farmer(db, org, "9000000401")
    product = make_product(sale_price="500", gst_rate="0", sku="RET1")
    receive(product, "B1", 5)
    inv = _sell(db, org, branch, farmer, product, "500")
    assert farmer.outstanding_balance == Decimal("0.00")

    out = create_credit_note(
        CreditNoteIn(invoice_id=inv.id, reason="Wrong product", items=[ReturnItemIn(product_id=product.id, quantity=Decimal("1"))]),
        _current(db, org),
        db,
    )
    assert out["khata_amount"] == 0
    assert out["refund_amount"] == 500
    assert out["outstanding_balance"] == 0
    assert farmer.outstanding_balance == Decimal("0.00")


def test_credit_return_reduces_outstanding(db, org, branch, make_product, receive):
    farmer = _farmer(db, org, "9000000402")
    product = make_product(sale_price="500", gst_rate="0", sku="RET2")
    receive(product, "B1", 5)
    inv = _sell(db, org, branch, farmer, product, "0")
    assert farmer.outstanding_balance == Decimal("500.00")

    out = create_credit_note(
        CreditNoteIn(invoice_id=inv.id, reason="Damaged bag", items=[ReturnItemIn(product_id=product.id, quantity=Decimal("1"))]),
        _current(db, org),
        db,
    )
    assert out["khata_amount"] == 500
    assert out["refund_amount"] == 0
    assert farmer.outstanding_balance == Decimal("0.00")


def test_partial_payment_return_splits_khata_and_refund(db, org, branch, make_product, receive):
    farmer = _farmer(db, org, "9000000403")
    product = make_product(sale_price="500", gst_rate="0", sku="RET3")
    receive(product, "B1", 5)
    inv = _sell(db, org, branch, farmer, product, "200")
    assert farmer.outstanding_balance == Decimal("300.00")

    out = create_credit_note(
        CreditNoteIn(invoice_id=inv.id, reason="Farmer changed mind", items=[ReturnItemIn(product_id=product.id, quantity=Decimal("1"))]),
        _current(db, org),
        db,
    )
    assert out["khata_amount"] == 300
    assert out["refund_amount"] == 200
    assert farmer.outstanding_balance == Decimal("0.00")
