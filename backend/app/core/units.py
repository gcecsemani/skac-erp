"""Sale/stock unit labels and pack ↔ loose conversion.

Migrated SKUs are one packing each (a 100ml bottle, a 50kg bag). On-hand
quantity is the pack count. Fertilizer bags can also be sold loose (1 kg from
a 50 kg bag): billed qty is in kg, stock is reduced by billed / pack_size.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

_GENERIC = {"unit", "units", "packet", "pcs", "nos"}
_SI_FAMILY = {"litre", "liter", "l", "kg", "kilogram", "g", "gm", "gms"}
_STOCK_QTY = Decimal("0.001")

_UNIT_MAP = {
    "mls": "ml",
    "ml": "ml",
    "ltrs": "L",
    "ltr": "L",
    "l": "L",
    "litre": "L",
    "liter": "L",
    "kgs": "kg",
    "kg": "kg",
    "gms": "g",
    "gm": "g",
    "g": "g",
}

# Only weight packs are sold loose by default (not 100ml bottles).
_LOOSE_OK = {"kg", "g"}


@dataclass(frozen=True)
class PackInfo:
    sale_unit: str
    pack_size: Decimal
    loose_unit: str | None
    allows_loose: bool


def pretty_pack(raw: str | None) -> str:
    spaced = re.sub(r"\s+", " ", (raw or "").strip())
    if not spaced:
        return ""
    compact = spaced.replace(" ", "")
    m = re.match(r"^(\d+(?:\.\d+)?)(.*)$", compact, re.I)
    if not m:
        return spaced
    qty, unit = m.group(1), m.group(2).lower()
    mapped = _UNIT_MAP.get(unit)
    if mapped:
        return f"{qty}{mapped}"
    return spaced


def packing_of(product: object) -> str | None:
    extra = getattr(product, "attributes", None)
    if not isinstance(extra, dict):
        extra = {}
    pack = str(extra.get("packing") or getattr(product, "packing", None) or "").strip()
    if pack and pack.lower() not in _GENERIC:
        return pack
    return None


def sale_unit_of(product: object) -> str:
    pack = packing_of(product)
    if pack:
        return pretty_pack(pack) or pack
    name = str(getattr(product, "name", "") or "")
    m = re.search(r"\s[-–]\s*(\d[\w.\s]*)$", name)
    if m:
        pretty = pretty_pack(m.group(1))
        if pretty:
            return pretty
    base = str(getattr(product, "base_unit", None) or "").strip()
    if base and base.lower() not in _SI_FAMILY:
        return base
    return base or "pcs"


def _parse_weight(label: str | None) -> tuple[Decimal, str] | None:
    if not label:
        return None
    compact = pretty_pack(label).replace(" ", "")
    m = re.match(r"^(\d+(?:\.\d+)?)(kg|g)$", compact, re.I)
    if not m:
        return None
    qty = Decimal(m.group(1))
    if qty <= 0:
        return None
    return qty, m.group(2).lower()


def _attrs(product: object) -> dict:
    extra = getattr(product, "attributes", None)
    return extra if isinstance(extra, dict) else {}


def pack_info(product: object) -> PackInfo:
    sale = sale_unit_of(product)
    extra = _attrs(product)
    parsed = _parse_weight(sale) or _parse_weight(packing_of(product) or "")
    pack_size = Decimal("1")
    loose_unit: str | None = None
    if parsed:
        pack_size, loose_unit = parsed
    raw_size = extra.get("pack_size")
    if raw_size not in (None, ""):
        try:
            override = Decimal(str(raw_size))
            if override > 0:
                pack_size = override
        except Exception:
            pass
    if extra.get("loose_unit"):
        loose_unit = str(extra["loose_unit"]).strip().lower() or loose_unit

    allows = pack_size > 1 and loose_unit in _LOOSE_OK
    flag = extra.get("sell_loose")
    if flag is False:
        allows = False
    elif flag is True and pack_size > 1 and loose_unit in _LOOSE_OK:
        allows = True

    return PackInfo(
        sale_unit=sale,
        pack_size=pack_size,
        loose_unit=loose_unit if allows else (loose_unit if pack_size > 1 else None),
        allows_loose=allows,
    )


def _norm_unit(unit: str | None) -> str:
    return pretty_pack(unit or "").lower().replace(" ", "") or (unit or "").strip().lower()


def is_loose_sale(product: object, unit: str | None) -> bool:
    info = pack_info(product)
    if not info.allows_loose or not unit:
        return False
    billed = _norm_unit(unit)
    if billed == _norm_unit(info.sale_unit):
        return False
    return billed == (info.loose_unit or "")


def billed_to_stock_qty(product: object, quantity: Decimal, unit: str | None) -> Decimal:
    """Convert billed qty (bags or kg) to on-hand pack qty."""
    qty = Decimal(quantity)
    info = pack_info(product)
    if is_loose_sale(product, unit):
        qty = qty / info.pack_size
    return qty.quantize(_STOCK_QTY, rounding=ROUND_HALF_UP)


def loose_unit_price(pack_price: Decimal, product: object) -> Decimal:
    info = pack_info(product)
    if info.pack_size <= 0:
        return Decimal(pack_price)
    return (Decimal(pack_price) / info.pack_size).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
