"""The Accounting page and the GST report must never disagree."""
from datetime import date, timedelta
from decimal import Decimal

from app.models.enums import InvoiceStatus, PaymentMode
from app.models.sales import Invoice, InvoiceItem
from app.services import accounting
from app.services.report_tables import run_report

START = date.today() - timedelta(days=10)
END = date.today()


def _bill(db, org, branch, lines, when=None, status=InvoiceStatus.finalized):
    inv = Invoice(
        organization_id=org.id,
        branch_id=branch.id,
        invoice_date=when or END,
        status=status,
        payment_mode=PaymentMode.cash,
    )
    db.add(inv)
    db.flush()
    for rate, taxable, tax in lines:
        db.add(
            InvoiceItem(
                invoice_id=inv.id,
                product_id=1,
                product_name="Item",
                quantity=Decimal("1"),
                unit_price=Decimal(taxable),
                gst_rate=Decimal(rate),
                taxable_value=Decimal(taxable),
                tax_amount=Decimal(tax),
                line_total=Decimal(taxable) + Decimal(tax),
            )
        )
    db.flush()
    return inv


def test_slabs_group_by_rate_and_split_tax_evenly(db, org, branch):
    _bill(db, org, branch, [("5", "1000", "50"), ("18", "2000", "360")])
    _bill(db, org, branch, [("5", "500", "25")])

    slabs = accounting.gst_slabs(db, organization_id=org.id, start=START, end=END)

    assert [s["gst_rate"] for s in slabs] == [5.0, 18.0]
    five, eighteen = slabs
    assert five["taxable_value"] == 1500.0
    assert five["total_tax"] == 75.0
    assert five["cgst"] == five["sgst"] == 37.5
    assert eighteen["taxable_value"] == 2000.0
    assert eighteen["cgst"] == eighteen["sgst"] == 180.0


def test_draft_and_out_of_period_bills_are_excluded(db, org, branch):
    _bill(db, org, branch, [("5", "1000", "50")])
    _bill(db, org, branch, [("5", "9999", "500")], status=InvoiceStatus.draft)
    _bill(db, org, branch, [("5", "7777", "389")], when=START - timedelta(days=5))

    slabs = accounting.gst_slabs(db, organization_id=org.id, start=START, end=END)

    assert len(slabs) == 1
    assert slabs[0]["taxable_value"] == 1000.0


def test_report_table_and_accounting_summary_report_the_same_totals(
    db, org, branch
):
    _bill(db, org, branch, [("5", "1000", "50"), ("12", "800", "96")])
    _bill(db, org, branch, [("18", "2000", "360")])

    slabs = accounting.gst_slabs(db, organization_id=org.id, start=START, end=END)
    table = run_report(db, key="gst", org_id=org.id, scope=None, start=START, end=END)

    assert [r["gst_rate"] for r in table["rows"]] == [s["gst_rate"] for s in slabs]
    # The report renames the column but must carry the same value.
    assert [r["taxable"] for r in table["rows"]] == [
        s["taxable_value"] for s in slabs
    ]
    assert [r["total_tax"] for r in table["rows"]] == [s["total_tax"] for s in slabs]

    summary = {s["label"]: s["value"] for s in table["summary"]}
    assert summary["Taxable"] == round(sum(s["taxable_value"] for s in slabs), 2)
    assert summary["GST"] == round(sum(s["total_tax"] for s in slabs), 2)


def test_branch_scope_is_honoured(db, org, branch):
    from app.models.organization import Branch

    other = Branch(organization_id=org.id, code="BR02", name="Second")
    db.add(other)
    db.flush()

    _bill(db, org, branch, [("5", "1000", "50")])
    _bill(db, org, other, [("5", "4000", "200")])

    mine = accounting.gst_slabs(
        db, organization_id=org.id, start=START, end=END, branch_ids=[branch.id]
    )
    everything = accounting.gst_slabs(
        db, organization_id=org.id, start=START, end=END
    )

    assert mine[0]["taxable_value"] == 1000.0
    assert everything[0]["taxable_value"] == 5000.0
