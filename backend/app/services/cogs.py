"""Cost of goods sold for billed invoice lines.

Purchase price on the product (and on batches) is the *pack* cost — a 50 kg
bag, a 25 kg bag, a 100 ml bottle. POS can bill fertilizer loose in kg, and
those lines store kg on InvoiceItem.quantity. Reports that did
`qty * product.purchase_price` then costed every kilo as a full bag, which
made a few high-volume SKUs (and the dashboard) show a heavy loss.

COGS is pack-equivalent qty × lot cost (batch price, else product master).

`app.core.units` is the only place that decides pack size and whether a line
is loose, and those rules cannot be reproduced in SQL: pack size comes from
the product *name* suffix first ("UREA - 45KGS" beats a stale
`attributes.packing` of "50 KGS"), and packing strings like "1x50 KGS" do not
survive a CAST. So SQL sums cost in *billed* units grouped by
(product, billed unit, unit price) and `grouped_totals` applies the Python
divisor once per group.

A second historical wrinkle: pre-loose POS wrote `unit=kg` on whole bags at
bag price. Those lines are priced as a pack (`billed_as_pack`) so they are
not divided.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.units import is_loose_sale, loose_unit_price, pack_info
from app.models.inventory import Batch
from app.models.product import Product
from app.models.sales import InvoiceItem

_ONE = Decimal("1")


def billed_as_pack(product, unit, unit_price) -> bool:
    """True when the unit looks loose but the price is a whole-pack price.

    Before loose billing, POS stored the product's base unit (`kg`) on bag
    sales at `sale_price`. Stock issued a full bag. Costing those as
    qty / pack_size (1 kg ÷ 50) overstates profit. A true loose kilo is
    priced near sale_price / pack_size (₹22 on a ₹1,100 bag).
    """
    if unit_price is None or product is None or not is_loose_sale(product, unit):
        return False
    pack_price = Decimal(getattr(product, "sale_price", 0) or 0)
    if pack_price <= 0:
        return False
    billed = Decimal(unit_price)
    per_loose = loose_unit_price(pack_price, product)
    return abs(billed - pack_price) <= abs(billed - per_loose)


def line_cogs_amount(product, quantity, unit, pack_cost, unit_price=None) -> Decimal:
    """Python-side COGS for one billed line (tests / one-off calcs)."""
    return (Decimal(quantity) / pack_divisor(product, unit, unit_price)) * Decimal(pack_cost)


def pack_divisor(product, unit, unit_price=None) -> Decimal:
    """Billed qty ÷ this = pack-equivalent qty; 1 unless the line is loose.

    The aggregate-friendly form of billed→stock conversion: constant for a
    given (product, billed unit, unit price), so a SUM over many lines can
    be divided once.
    """
    if product is None or not is_loose_sale(product, unit) or billed_as_pack(product, unit, unit_price):
        return _ONE
    size = pack_info(product).pack_size
    return size if size > 0 else _ONE


def unit_cost_expr():
    """Pack cost: the sold batch if priced, otherwise the product master."""
    batch_price = (
        select(Batch.purchase_price)
        .where(Batch.id == InvoiceItem.batch_id, Batch.purchase_price > 0)
        .scalar_subquery()
    )
    return func.coalesce(batch_price, Product.purchase_price)


def billed_cogs_expr():
    """Line cost in *billed* units — divide by `pack_divisor` for loose lines."""
    return InvoiceItem.quantity * unit_cost_expr()


# Trailing columns of every line_totals_stmt(), in this order.
# unit_price is in the key so kg@bag-price and kg@per-kg do not share a divisor.
_LINE_KEYS = (InvoiceItem.product_id, InvoiceItem.unit, InvoiceItem.unit_price)
_METRICS = 6  # qty, taxable, tax, total, cogs, discount
_TAIL = len(_LINE_KEYS) + _METRICS


@dataclass
class LineTotals:
    """Invoice-line sums with loose lines already reduced to pack equivalents."""

    qty: Decimal = field(default_factory=Decimal)
    taxable: Decimal = field(default_factory=Decimal)
    tax: Decimal = field(default_factory=Decimal)
    total: Decimal = field(default_factory=Decimal)
    cogs: Decimal = field(default_factory=Decimal)
    discount: Decimal = field(default_factory=Decimal)


def line_totals_stmt(*dims):
    """Aggregate invoice lines by `dims`, ready for `grouped_totals`.

    Also groups by product, billed unit and unit price so the loose divisor
    can be applied in Python; the caller adds its own joins and filters.
    """
    return select(
        *dims,
        *_LINE_KEYS,
        func.coalesce(func.sum(InvoiceItem.quantity), 0),
        func.coalesce(func.sum(InvoiceItem.taxable_value), 0),
        func.coalesce(func.sum(InvoiceItem.tax_amount), 0),
        func.coalesce(func.sum(InvoiceItem.line_total), 0),
        func.coalesce(func.sum(billed_cogs_expr()), 0),
        func.coalesce(func.sum(InvoiceItem.discount), 0),
    ).group_by(*dims, *_LINE_KEYS)


def _dec(value) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal(0)


def _products(db: Session, ids) -> dict[int, Product]:
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    return {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(ids))).all()}


def grouped_totals(db: Session, stmt) -> dict[tuple, LineTotals]:
    """Run a `line_totals_stmt` and fold the (product, unit) rows onto `dims`."""
    rows = db.execute(stmt).all()
    products = _products(db, {row[-_TAIL] for row in rows})
    out: dict[tuple, LineTotals] = {}
    for row in rows:
        product_id, unit, unit_price, qty, taxable, tax, total, cost, discount = row[-_TAIL:]
        divisor = pack_divisor(products.get(product_id), unit, unit_price)
        totals = out.setdefault(tuple(row[:-_TAIL]), LineTotals())
        totals.qty += _dec(qty) / divisor
        totals.taxable += _dec(taxable)
        totals.tax += _dec(tax)
        totals.total += _dec(total)
        totals.cogs += _dec(cost) / divisor
        totals.discount += _dec(discount)
    return out


def overall_totals(db: Session, stmt) -> LineTotals:
    """`grouped_totals` for a `line_totals_stmt()` with no dimensions."""
    return grouped_totals(db, stmt).get((), LineTotals())
