"""Billing service: build and finalize immutable GST invoices with batch lines."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.units import billed_to_stock_qty, is_loose_sale, loose_unit_price
from app.models.customer import Customer
from app.models.enums import InvoiceStatus, MovementType, PaymentMode, TaxType
from app.models.organization import Branch
from app.models.product import Product
from app.models.sales import Invoice, InvoiceItem
from app.services import accounting, inventory

TWOPLACES = Decimal("0.01")


@dataclass
class LineInput:
    product_id: int
    quantity: Decimal
    unit_price: Decimal | None = None  # defaults to product.sale_price
    discount: Decimal = Decimal("0")
    unit: str | None = None


@dataclass
class InvoiceInput:
    branch_id: int
    customer_id: int | None = None
    payment_mode: PaymentMode = PaymentMode.cash
    tax_type: TaxType = TaxType.intra
    invoice_date: date | None = None
    # None = paid in full at the counter. 0 (or any amount < grand_total) is
    # a credit / partial sale and requires a farmer with khata allowed.
    amount_paid: Decimal | None = None
    client_uuid: str | None = None
    lines: list[LineInput] = None  # type: ignore[assignment]


def _next_invoice_no(db: Session, branch: Branch) -> str:
    """Per-branch running invoice number, namespaced by Indian financial year."""
    today = date.today()
    fy_start = today.year if today.month >= 4 else today.year - 1
    fy = f"{fy_start}-{str(fy_start + 1)[-2:]}"
    count = db.scalar(
        select(func.count(Invoice.id)).where(
            Invoice.branch_id == branch.id,
            Invoice.status == InvoiceStatus.finalized,
        )
    ) or 0
    return f"{branch.code}/{fy}/{count + 1:05d}"


def create_and_finalize(
    db: Session,
    *,
    organization_id: int,
    data: InvoiceInput,
    created_by_user_id: int | None,
    allow_oversell: bool = False,
) -> Invoice:
    """Create a finalized, immutable invoice.

    Splits each requested line across batches (expiry-first) so every printed
    line carries its own batch/mfg/expiry — a regulatory requirement.
    Idempotent on `client_uuid` for offline sync.
    """
    # Idempotency: return the existing invoice if this client_uuid was synced.
    if data.client_uuid:
        existing = db.scalar(
            select(Invoice).where(Invoice.client_uuid == data.client_uuid)
        )
        if existing is not None:
            return existing

    branch = db.get(Branch, data.branch_id)
    if branch is None:
        raise ValueError("Branch not found")

    invoice = Invoice(
        organization_id=organization_id,
        branch_id=data.branch_id,
        customer_id=data.customer_id,
        created_by_user_id=created_by_user_id,
        client_uuid=data.client_uuid,
        invoice_date=data.invoice_date or date.today(),
        status=InvoiceStatus.finalized,
        tax_type=data.tax_type,
        payment_mode=data.payment_mode,
        finalized_at=datetime.utcnow(),
    )
    db.add(invoice)
    db.flush()  # assign invoice.id

    subtotal = Decimal("0")
    discount_total = Decimal("0")
    tax_total = Decimal("0")

    for line in data.lines or []:
        product = db.get(Product, line.product_id)
        if product is None:
            raise ValueError(f"Product {line.product_id} not found")

        billed_unit = line.unit or product.sale_unit
        if line.unit_price is not None:
            unit_price = line.unit_price
        elif is_loose_sale(product, billed_unit):
            unit_price = loose_unit_price(product.sale_price, product)
        else:
            unit_price = product.sale_price
        line_discount_in = Decimal(line.discount or 0)
        if line_discount_in < 0:
            raise ValueError("Discount cannot be negative")
        billed_qty = Decimal(line.quantity)
        if line_discount_in > (billed_qty * unit_price).quantize(TWOPLACES):
            raise ValueError(f"Discount on {product.name} exceeds line amount")

        stock_qty = billed_to_stock_qty(product, billed_qty, billed_unit)
        try:
            allocations = inventory.allocate_fifo(
                db,
                branch_id=data.branch_id,
                product_id=line.product_id,
                quantity=stock_qty,
                allow_oversell=allow_oversell,
            )
        except inventory.InsufficientStock as exc:
            exc.billed_unit = billed_unit
            exc.billed_qty = billed_qty
            raise

        # Spread the line-level discount proportionally across batch splits.
        total_stock = sum((a.quantity for a in allocations), Decimal("0")) or Decimal("1")
        for alloc in allocations:
            portion = alloc.quantity / total_stock
            billed_slice = (billed_qty * portion).quantize(Decimal("0.001"))
            line_discount = (Decimal(line.discount) * portion).quantize(TWOPLACES)
            taxable = (billed_slice * unit_price - line_discount).quantize(TWOPLACES)
            tax_amount = (taxable * product.gst_rate / Decimal("100")).quantize(TWOPLACES)
            line_total = (taxable + tax_amount).quantize(TWOPLACES)

            db.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=product.id,
                    batch_id=alloc.batch_id,
                    product_name=product.name,
                    hsn_code=product.hsn_code,
                    batch_no=alloc.batch_no,
                    mfg_date=alloc.mfg_date,
                    expiry_date=alloc.expiry_date,
                    unit=billed_unit,
                    quantity=billed_slice,
                    unit_price=unit_price,
                    discount=line_discount,
                    gst_rate=product.gst_rate,
                    taxable_value=taxable,
                    tax_amount=tax_amount,
                    line_total=line_total,
                )
            )
            subtotal += taxable
            discount_total += line_discount
            tax_total += tax_amount

        # Decrement stock + write movement ledger. Use the invoice date so
        # sales analytics / forecasting reflect when the sale actually happened.
        inventory.apply_issue(
            db,
            organization_id=organization_id,
            branch_id=data.branch_id,
            product_id=line.product_id,
            allocations=allocations,
            movement_type=MovementType.sale,
            ref_type="invoice",
            ref_id=invoice.id,
            occurred_at=datetime.combine(invoice.invoice_date, datetime.min.time()),
        )

    grand_total = (subtotal + tax_total).quantize(TWOPLACES)
    invoice.subtotal = subtotal.quantize(TWOPLACES)
    invoice.discount_total = discount_total.quantize(TWOPLACES)
    invoice.tax_total = tax_total.quantize(TWOPLACES)
    invoice.grand_total = grand_total

    paid = grand_total if data.amount_paid is None else Decimal(data.amount_paid).quantize(TWOPLACES)
    if paid < 0:
        raise ValueError("Amount paid cannot be negative")
    if paid > grand_total:
        raise ValueError("Amount paid cannot exceed invoice total")
    invoice.amount_paid = paid

    invoice.invoice_no = _next_invoice_no(db, branch)

    # Unpaid remainder is added to the farmer's khata (partial or full credit).
    outstanding = grand_total - paid
    if outstanding > 0:
        if not data.customer_id:
            raise ValueError("Select a farmer to record a partial or credit (khata) sale")
        customer = db.get(Customer, data.customer_id)
        if customer is None:
            raise ValueError("Farmer not found")
        if not customer.credit_allowed:
            raise ValueError("This farmer is not allowed credit (khata)")
        new_balance = (customer.outstanding_balance + outstanding).quantize(TWOPLACES)
        if customer.credit_limit > 0 and new_balance > customer.credit_limit:
            raise ValueError(
                f"Would exceed khata limit of ₹{customer.credit_limit} "
                f"(outstanding ₹{customer.outstanding_balance}, this bill due ₹{outstanding})"
            )
        customer.outstanding_balance = new_balance

    # Auto-post the double-entry journal for this sale.
    accounting.post_sale(
        db, organization_id=organization_id, branch_id=data.branch_id,
        entry_date=invoice.invoice_date, invoice_id=invoice.id,
        taxable=invoice.subtotal, tax=invoice.tax_total,
        grand_total=invoice.grand_total, amount_paid=invoice.amount_paid,
    )

    return invoice
