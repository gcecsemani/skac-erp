"""Cost of goods sold for billed invoice lines.

Purchase price on the product (and on batches) is the *pack* cost — a 50 kg
bag, a 25 kg bag, a 100 ml bottle. POS can bill fertilizer loose in kg, and
those lines store kg on InvoiceItem.quantity. Reports that did
`qty * product.purchase_price` then costed every kilo as a full bag, which
made a few high-volume SKUs (and the dashboard) show a heavy loss.

COGS is pack-equivalent qty × lot cost (batch price, else product master).
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, and_, case, cast, func, select

from app.core.units import LOOSE_BILLED_UNITS, billed_to_stock_qty
from app.models.inventory import Batch
from app.models.product import Product
from app.models.sales import InvoiceItem

_PACK_DEC = Numeric(12, 4)


def line_cogs_amount(product, quantity, unit, pack_cost) -> Decimal:
    """Python-side COGS for one billed line (tests / one-off calcs)."""
    stock_qty = billed_to_stock_qty(product, Decimal(quantity), unit)
    return stock_qty * Decimal(pack_cost)


def pack_size_expr():
    """Pack kg/g from product JSON. CAST('50 KGS' AS DECIMAL) reads 50."""
    json_size = func.nullif(cast(Product.attributes["pack_size"].as_string(), _PACK_DEC), 0)
    packing_n = func.nullif(cast(Product.attributes["packing"].as_string(), _PACK_DEC), 0)
    return func.coalesce(json_size, packing_n, 1)


def billed_unit_norm_expr():
    return func.replace(func.lower(func.trim(InvoiceItem.unit)), " ", "")


def is_loose_line_expr():
    return billed_unit_norm_expr().in_(sorted(LOOSE_BILLED_UNITS))


def stock_qty_expr():
    """Billed qty converted to on-hand pack qty (1 kg of a 50 kg bag → 0.02)."""
    size = pack_size_expr()
    return case(
        (and_(is_loose_line_expr(), size > 1), InvoiceItem.quantity / size),
        else_=InvoiceItem.quantity,
    )


def unit_cost_expr():
    """Pack cost: the sold batch if priced, otherwise the product master."""
    batch_price = (
        select(Batch.purchase_price)
        .where(Batch.id == InvoiceItem.batch_id, Batch.purchase_price > 0)
        .scalar_subquery()
    )
    return func.coalesce(batch_price, Product.purchase_price)


def line_cogs_expr():
    """SQL expression: pack-equivalent qty × pack cost. Product must be joined."""
    return stock_qty_expr() * unit_cost_expr()
