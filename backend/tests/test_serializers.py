"""Serializers that batch-load their lookups must still produce full rows."""
from datetime import date
from decimal import Decimal

from app.api.v1.purchasing import _serialize_grn, _serialize_purchase_return
from app.api.v1.transfers import _serialize
from app.models.enums import TransferStatus
from app.models.purchase import GRN, GRNItem, PurchaseReturn, PurchaseReturnItem
from app.models.transfer import StockTransfer, StockTransferItem
from app.models.vendor import Vendor


def _vendor(db, org, name="Agri Supplies"):
    v = Vendor(organization_id=org.id, name=name, gstin="33ABCDE1234F1Z5", phone="9876543210")
    db.add(v)
    db.flush()
    return v


def test_grn_serializer_resolves_every_line(db, org, branch, make_product, receive):
    """Two products and two batches, previously two queries per line."""
    vendor = _vendor(db, org)
    p1 = make_product(name="Urea", sku="U1")
    p2 = make_product(name="DAP", sku="D1")
    b1 = receive(p1, "B1", 10, expiry=date(2027, 1, 1))
    b2 = receive(p2, "B2", 20, expiry=date(2027, 2, 1))

    grn = GRN(
        organization_id=org.id, branch_id=branch.id, vendor_id=vendor.id,
        received_date=date.today(), grn_no="GRN/2026/00001",
        vendor_invoice_no="INV-9", total_value=Decimal("1000"),
    )
    grn.items = [
        GRNItem(product_id=p1.id, batch_id=b1.id, batch_no="B1",
                quantity=Decimal("10"), unit_price=Decimal("50")),
        GRNItem(product_id=p2.id, batch_id=b2.id, batch_no="B2",
                quantity=Decimal("20"), unit_price=Decimal("25")),
    ]
    db.add(grn)
    db.flush()

    out = _serialize_grn(db, grn)

    assert out["vendor"] == "Agri Supplies"
    assert out["item_count"] == 2
    names = {i["product_name"] for i in out["items"]}
    assert names == {"Urea", "DAP"}
    on_hand = {i["product_name"]: i["on_hand"] for i in out["items"]}
    assert on_hand == {"Urea": 10.0, "DAP": 20.0}
    # Nothing returned yet, so the whole receipt is still returnable.
    assert {i["returnable"] for i in out["items"]} == {10.0, 20.0}


def test_grn_serializer_nets_off_what_was_already_returned(
    db, org, branch, make_product, receive
):
    vendor = _vendor(db, org)
    p = make_product(name="Urea", sku="U1")
    b = receive(p, "B1", 10, expiry=date(2027, 1, 1))

    grn = GRN(
        organization_id=org.id, branch_id=branch.id, vendor_id=vendor.id,
        received_date=date.today(), grn_no="GRN/2026/00002", total_value=Decimal("500"),
    )
    grn.items = [
        GRNItem(product_id=p.id, batch_id=b.id, batch_no="B1",
                quantity=Decimal("10"), unit_price=Decimal("50"))
    ]
    db.add(grn)
    db.flush()

    note = PurchaseReturn(
        organization_id=org.id, branch_id=branch.id, vendor_id=vendor.id,
        grn_id=grn.id, note_date=date.today(), note_no="DN/1", total=Decimal("150"),
    )
    note.items = [
        PurchaseReturnItem(
            grn_item_id=grn.items[0].id, product_id=p.id, product_name="Urea",
            batch_no="B1", quantity=Decimal("3"), unit_price=Decimal("50"),
            line_total=Decimal("150"),
        )
    ]
    db.add(note)
    db.flush()

    out = _serialize_grn(db, grn)
    line = out["items"][0]
    assert line["returned_quantity"] == 3.0
    assert line["returnable"] == 7.0


def test_purchase_return_serializer_pulls_expiry_from_the_grn_line(
    db, org, branch, make_product, receive
):
    vendor = _vendor(db, org)
    p = make_product(name="Urea", sku="U1")
    b = receive(p, "B1", 10, expiry=date(2027, 3, 4))

    grn = GRN(
        organization_id=org.id, branch_id=branch.id, vendor_id=vendor.id,
        received_date=date.today(), grn_no="GRN/2026/00003",
        vendor_invoice_no="INV-11", total_value=Decimal("500"),
    )
    grn.items = [
        GRNItem(product_id=p.id, batch_id=b.id, batch_no="B1",
                expiry_date=date(2027, 3, 4),
                quantity=Decimal("10"), unit_price=Decimal("50"))
    ]
    db.add(grn)
    db.flush()

    note = PurchaseReturn(
        organization_id=org.id, branch_id=branch.id, vendor_id=vendor.id,
        grn_id=grn.id, note_date=date.today(), note_no="DN/2", total=Decimal("105"),
    )
    note.items = [
        PurchaseReturnItem(
            grn_item_id=grn.items[0].id, product_id=p.id, product_name="Urea",
            batch_no="B1", quantity=Decimal("2"), unit_price=Decimal("50"),
            gst_rate=Decimal("5"), taxable_value=Decimal("100"),
            tax_amount=Decimal("5"), line_total=Decimal("105"),
        )
    ]
    db.add(note)
    db.flush()

    out = _serialize_purchase_return(db, note)

    assert out["vendor"] == "Agri Supplies"
    assert out["grn_no"] == "GRN/2026/00003"
    assert out["vendor_invoice_no"] == "INV-11"
    assert out["taxable_total"] == 100.0
    assert out["tax_total"] == 5.0
    # Expiry is carried over from the GRN line, which is now batch-loaded.
    assert out["items"][0]["expiry_date"] == "2027-03-04"


def test_transfer_serializer_resolves_branches_and_batches(
    db, org, branch, make_product, receive
):
    from app.models.organization import Branch

    dest = Branch(organization_id=org.id, code="BR02", name="Second")
    db.add(dest)
    db.flush()

    p = make_product(name="Urea", sku="U1")
    b = receive(p, "B1", 10, expiry=date(2027, 5, 6))

    t = StockTransfer(
        organization_id=org.id, from_branch_id=branch.id, to_branch_id=dest.id,
        transfer_date=date.today(), status=TransferStatus.requested,
        transfer_no="TR/2026/00001",
    )
    t.items = [
        StockTransferItem(product_id=p.id, product_name="Urea",
                          quantity=Decimal("4"), batch_id=b.id)
    ]
    db.add(t)
    db.flush()

    out = _serialize(db, t)

    assert out["from_branch"] == "Main"
    assert out["to_branch"] == "Second"
    assert out["items"][0]["batch_no"] == "B1"
    assert out["items"][0]["expiry_date"] == "2027-05-06"
    assert out["items"][0]["quantity"] == 4.0


def test_transfer_serializer_handles_a_line_with_no_batch_yet(
    db, org, branch, make_product
):
    """Requested transfers have no batch until they are approved."""
    from app.models.organization import Branch

    dest = Branch(organization_id=org.id, code="BR02", name="Second")
    db.add(dest)
    db.flush()
    p = make_product(name="Urea", sku="U1")

    t = StockTransfer(
        organization_id=org.id, from_branch_id=branch.id, to_branch_id=dest.id,
        transfer_date=date.today(), status=TransferStatus.requested,
    )
    t.items = [StockTransferItem(product_id=p.id, product_name="Urea", quantity=Decimal("2"))]
    db.add(t)
    db.flush()

    out = _serialize(db, t)
    assert out["items"][0]["batch_no"] is None
    assert out["items"][0]["expiry_date"] is None
