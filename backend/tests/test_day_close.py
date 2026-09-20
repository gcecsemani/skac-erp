"""Day close must reconcile the till from invoices, receipts and payouts."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from app.models.customer import Customer, CustomerPayment
from app.models.enums import InvoiceStatus, PaymentMode
from app.models.expense import Expense
from app.models.organization import Branch
from app.models.sales import Invoice
from app.services.day_close import compute_expected

# `_payment_shop_date` reinterprets a naive timestamp as UTC when it lands on
# today or yesterday, so pin the close date well clear of that window to keep
# these assertions independent of the wall clock and the machine timezone.
CLOSE = date.today() - timedelta(days=30)
AT_NOON = datetime.combine(CLOSE, time(12, 0))


def _invoice(db, org, branch, total, paid, mode=PaymentMode.cash, customer=None):
    inv = Invoice(
        organization_id=org.id,
        branch_id=branch.id,
        customer_id=customer.id if customer else None,
        invoice_date=CLOSE,
        status=InvoiceStatus.finalized,
        payment_mode=mode,
        grand_total=Decimal(total),
        amount_paid=Decimal(paid),
    )
    db.add(inv)
    db.flush()
    return inv


def _customer(db, org, name="Farmer"):
    c = Customer(organization_id=org.id, name=name, credit_allowed=True)
    db.add(c)
    db.flush()
    return c


def _expected(db, org, branch, include_unscoped=False):
    return compute_expected(
        db,
        org_id=org.id,
        branch_id=branch.id,
        close_date=CLOSE,
        include_unscoped=include_unscoped,
    )


def test_cash_and_digital_are_bucketed_separately(db, org, branch):
    _invoice(db, org, branch, "1000", "1000", PaymentMode.cash)
    _invoice(db, org, branch, "500", "500", PaymentMode.upi)
    _invoice(db, org, branch, "250", "250", PaymentMode.cash)

    r = _expected(db, org, branch)

    assert r["bill_count"] == 3
    assert r["sales_total"] == Decimal("1750.00")
    assert r["cash_in"] == Decimal("1250.00")
    assert r["digital_in"] == Decimal("500.00")
    assert r["khata_new"] == Decimal("0.00")


def test_credit_bill_adds_to_khata_and_not_to_the_till(db, org, branch):
    c = _customer(db, org)
    _invoice(db, org, branch, "2000", "0", PaymentMode.credit, customer=c)
    _invoice(db, org, branch, "1000", "1000", PaymentMode.cash)

    r = _expected(db, org, branch)

    assert r["sales_total"] == Decimal("3000.00")
    assert r["khata_new"] == Decimal("2000.00")
    # The credit bill contributes nothing to cash counted at the counter.
    assert r["cash_in"] == Decimal("1000.00")
    assert r["collected_total"] == Decimal("1000.00")


def test_partly_paid_credit_bill_splits_between_khata_and_till(db, org, branch):
    c = _customer(db, org)
    _invoice(db, org, branch, "1000", "400", PaymentMode.credit, customer=c)

    r = _expected(db, org, branch)

    assert r["khata_new"] == Decimal("600.00")
    # amount_paid on a credit bill is settled later as a receipt, not at the till.
    assert r["cash_in"] == Decimal("0.00")


def test_khata_receipt_counts_against_the_branch_that_billed_the_farmer(
    db, org, branch
):
    other = Branch(organization_id=org.id, code="BR02", name="Second")
    db.add(other)
    db.flush()

    c = _customer(db, org)
    # The farmer's most recent bill is at `other`, so an untagged receipt
    # belongs to that shop, not this one.
    _invoice(db, org, other, "5000", "0", PaymentMode.credit, customer=c)
    db.add(
        CustomerPayment(
            organization_id=org.id,
            branch_id=None,
            customer_id=c.id,
            paid_at=AT_NOON,
            amount=Decimal("1500"),
            mode="cash",
        )
    )
    db.flush()

    here = _expected(db, org, branch)
    there = _expected(db, org, other)

    assert here["khata_collected"] == Decimal("0.00")
    assert there["khata_collected"] == Decimal("1500.00")
    assert there["cash_in"] == Decimal("1500.00")


def test_reversed_receipt_is_ignored(db, org, branch):
    c = _customer(db, org)
    _invoice(db, org, branch, "5000", "0", PaymentMode.credit, customer=c)
    db.add(
        CustomerPayment(
            organization_id=org.id,
            branch_id=branch.id,
            customer_id=c.id,
            paid_at=AT_NOON,
            amount=Decimal("900"),
            mode="cash",
            reversed_at=datetime.now(),
        )
    )
    db.flush()

    assert _expected(db, org, branch)["khata_collected"] == Decimal("0.00")


def test_expenses_reduce_expected_cash(db, org, branch):
    _invoice(db, org, branch, "1000", "1000", PaymentMode.cash)
    db.add(
        Expense(
            organization_id=org.id,
            branch_id=branch.id,
            expense_date=CLOSE,
            category="transport",
            amount=Decimal("300"),
            mode="cash",
        )
    )
    db.flush()

    r = _expected(db, org, branch)
    assert r["expense_total"] == Decimal("300.00")
    assert r["cash_out"] == Decimal("300.00")
    assert r["expected_cash"] == Decimal("700.00")


def test_empty_day_reconciles_to_zero(db, org, branch):
    r = _expected(db, org, branch)
    assert r["bill_count"] == 0
    assert r["sales_total"] == Decimal("0.00")
    assert r["expected_cash"] == Decimal("0.00")
