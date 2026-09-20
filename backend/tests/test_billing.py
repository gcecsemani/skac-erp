"""Invoice finalization: expiry-first allocation, stock ledger, numbering."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.enums import InvoiceStatus, MovementType
from app.models.inventory import Stock, StockMovement
from app.models.sales import Invoice, InvoiceItem
from app.services import billing
from app.services.inventory import InsufficientStock, allocate_fifo


def _finalize(db, org, branch, lines, **kw):
    return billing.create_and_finalize(
        db,
        organization_id=org.id,
        data=billing.InvoiceInput(branch_id=branch.id, lines=lines, **kw),
        created_by_user_id=None,
    )


def test_allocates_earliest_expiry_first(db, org, branch, make_product, receive):
    p = make_product()
    receive(p, "LATE", 10, expiry=date(2027, 12, 1))
    receive(p, "SOON", 10, expiry=date(2026, 6, 1))
    receive(p, "NOEXP", 10, expiry=None)

    allocs = allocate_fifo(db, branch_id=branch.id, product_id=p.id, quantity=Decimal("25"))

    # Earliest expiry drains first, undated stock sorts last.
    assert [(a.batch_no, a.quantity) for a in allocs] == [
        ("SOON", Decimal("10.000")),
        ("LATE", Decimal("10.000")),
        ("NOEXP", Decimal("5.000")),
    ]


def test_invoice_splits_lines_across_batches_and_decrements_stock(
    db, org, branch, make_product, receive
):
    p = make_product(sale_price="100", gst_rate="5")
    receive(p, "B1", 3, expiry=date(2026, 6, 1))
    receive(p, "B2", 5, expiry=date(2027, 6, 1))

    inv = _finalize(db, org, branch, [billing.LineInput(product_id=p.id, quantity=Decimal("4"))])
    db.flush()

    items = db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)).all()
    assert sorted(i.batch_no for i in items) == ["B1", "B2"]
    assert sum(i.quantity for i in items) == Decimal("4.000")

    # 4 x 100 = 400 taxable, 5% GST = 20.
    assert inv.subtotal == Decimal("400.00")
    assert inv.tax_total == Decimal("20.00")
    assert inv.grand_total == Decimal("420.00")

    on_hand = db.scalar(
        select(func.sum(Stock.quantity)).where(
            Stock.branch_id == branch.id, Stock.product_id == p.id
        )
    )
    assert on_hand == Decimal("4.000")

    moves = db.scalars(
        select(StockMovement).where(
            StockMovement.ref_type == "invoice", StockMovement.ref_id == inv.id
        )
    ).all()
    assert len(moves) == 2
    assert all(m.movement_type is MovementType.sale for m in moves)
    assert sum(m.quantity for m in moves) == Decimal("-4.000")


def test_invoice_numbers_run_sequentially_without_gaps(
    db, org, branch, make_product, receive
):
    p = make_product()
    receive(p, "B1", 100, expiry=date(2027, 6, 1))

    numbers = []
    for _ in range(3):
        inv = _finalize(
            db, org, branch, [billing.LineInput(product_id=p.id, quantity=Decimal("1"))]
        )
        db.flush()
        numbers.append(inv.invoice_no)

    today = date.today()
    fy_start = today.year if today.month >= 4 else today.year - 1
    fy = f"{fy_start}-{str(fy_start + 1)[-2:]}"
    assert numbers == [f"BR01/{fy}/0000{n}" for n in (1, 2, 3)]


def test_invoice_number_skips_an_already_taken_number(
    db, org, branch, make_product, receive
):
    """A number claimed out of band must not collide with uq_invoice_branch_no."""
    p = make_product()
    receive(p, "B1", 100, expiry=date(2027, 6, 1))

    first = _finalize(
        db, org, branch, [billing.LineInput(product_id=p.id, quantity=Decimal("1"))]
    )
    db.flush()

    taken = first.invoice_no.rsplit("/", 1)
    squatter = Invoice(
        organization_id=org.id,
        branch_id=branch.id,
        invoice_no=f"{taken[0]}/{int(taken[1]) + 1:05d}",
        invoice_date=date.today(),
        status=InvoiceStatus.finalized,
    )
    db.add(squatter)
    db.flush()

    nxt = _finalize(
        db, org, branch, [billing.LineInput(product_id=p.id, quantity=Decimal("1"))]
    )
    db.flush()
    assert nxt.invoice_no != squatter.invoice_no
    assert int(nxt.invoice_no.rsplit("/", 1)[1]) == int(taken[1]) + 2


def test_oversell_is_rejected(db, org, branch, make_product, receive):
    p = make_product()
    receive(p, "B1", 2, expiry=date(2027, 6, 1))

    with pytest.raises(InsufficientStock):
        _finalize(
            db, org, branch, [billing.LineInput(product_id=p.id, quantity=Decimal("5"))]
        )


def test_repeat_product_on_two_lines_still_resolves(
    db, org, branch, make_product, receive
):
    """Products are now bulk-loaded once; the same SKU twice must still work."""
    p = make_product()
    receive(p, "B1", 10, expiry=date(2027, 6, 1))

    inv = _finalize(
        db,
        org,
        branch,
        [
            billing.LineInput(product_id=p.id, quantity=Decimal("2")),
            billing.LineInput(product_id=p.id, quantity=Decimal("3")),
        ],
    )
    db.flush()
    items = db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)).all()
    assert sum(i.quantity for i in items) == Decimal("5.000")


def test_unknown_product_raises(db, org, branch, make_product, receive):
    with pytest.raises(ValueError, match="Product 9999 not found"):
        _finalize(
            db, org, branch, [billing.LineInput(product_id=9999, quantity=Decimal("1"))]
        )


def test_client_uuid_is_idempotent(db, org, branch, make_product, receive):
    p = make_product()
    receive(p, "B1", 10, expiry=date(2027, 6, 1))

    first = _finalize(
        db,
        org,
        branch,
        [billing.LineInput(product_id=p.id, quantity=Decimal("1"))],
        client_uuid="abc-123",
    )
    db.flush()
    again = _finalize(
        db,
        org,
        branch,
        [billing.LineInput(product_id=p.id, quantity=Decimal("1"))],
        client_uuid="abc-123",
    )
    assert again.id == first.id
    # The replay must not have taken stock a second time.
    on_hand = db.scalar(
        select(func.sum(Stock.quantity)).where(Stock.product_id == p.id)
    )
    assert on_hand == Decimal("9.000")
