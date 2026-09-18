"""Sale/stock unit labels and pack ↔ loose conversion.

Migrated SKUs are one packing each (a 100ml bottle, a 50kg bag). On-hand
quantity is the pack count. Fertilizer bags can also be sold loose (1 kg from
a 50 kg / 45 kg / 25 kg bag): billed qty is in kg, stock is reduced by
billed_kg / pack_size_kg.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

_GENERIC = {"unit", "units", "packet", "pcs", "nos"}
_SI_FAMILY = {"litre", "liter", "l", "kg", "kilogram", "g", "gm", "gms"}
_STOCK_QTY = Decimal("0.001")
_LOOSE_ALIASES = {"kg", "kgs", "kilogram", "kilograms", "g", "gm", "gms", "gram", "grams"}
# Invoice lines billed in these units are loose weight, not whole packs.
# Used by SQL COGS so 10 kg from a 50 kg bag is costed as 0.2 bags, not 10 bags.
LOOSE_BILLED_UNITS = frozenset(_LOOSE_ALIASES | {"1kg", "1g"})

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
_WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kgs?|g(?:ms?)?)(?![a-z])", re.I)


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


def packing_from_name(name: str | None) -> str | None:
    """Packing token from the name, e.g. 'UREA - 45KGS' → '45KGS' or 'DAP 25kg' → '25kg'."""
    text = str(name or "")
    m = re.search(r"\s[-–]\s*(\d[\w.\s]*)$", text)
    if m:
        raw = m.group(1).strip()
        if raw:
            return raw
    parsed = parse_weight(text)
    if parsed:
        qty, unit = parsed
        return f"{_fmt_qty(qty)}{unit}"
    return None


def name_packing_of(product: object) -> str | None:
    return packing_from_name(getattr(product, "name", None))


def sale_unit_of(product: object) -> str:
    # Name suffix wins over dump attributes.packing. Staff rename 50kg urea
    # bags to 45kg; the JSON packing often stays "50KGS" and would price
    # loose kg as sale_price/50.
    from_name = name_packing_of(product)
    if from_name:
        return pretty_pack(from_name) or from_name
    pack = packing_of(product)
    if pack:
        return pretty_pack(pack) or pack
    base = str(getattr(product, "base_unit", None) or "").strip()
    if base and base.lower() not in _SI_FAMILY:
        return base
    return base or "pcs"


def _fmt_qty(qty: Decimal) -> str:
    s = format(qty.normalize(), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def parse_weight(label: str | None) -> tuple[Decimal, str] | None:
    """Find a kg/g pack size in labels like 50kg, 45KGS, 25 kg, 50 Kg Bag."""
    if not label:
        return None
    matches = list(_WEIGHT_RE.finditer(str(label)))
    if not matches:
        compact = pretty_pack(str(label)).replace(" ", "")
        m = re.match(r"^(\d+(?:\.\d+)?)(kg|g)$", compact, re.I)
        if not m:
            return None
        qty = Decimal(m.group(1))
        return (qty, m.group(2).lower()) if qty > 0 else None
    m = matches[-1]
    qty = Decimal(m.group(1))
    if qty <= 0:
        return None
    unit = m.group(2).lower()
    return qty, ("kg" if unit.startswith("kg") else "g")


def _attrs(product: object) -> dict:
    extra = getattr(product, "attributes", None)
    return extra if isinstance(extra, dict) else {}


def pack_info(product: object) -> PackInfo:
    sale = sale_unit_of(product)
    extra = _attrs(product)
    parsed = (
        parse_weight(sale)
        or parse_weight(packing_of(product) or "")
        or parse_weight(getattr(product, "name", None))
    )
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

    flag = extra.get("sell_loose")
    if pack_size > 1 and loose_unit not in _LOOSE_OK:
        # Explicit pack size (25 / 45 / 50) with "sell loose" still means kg.
        if flag is not False:
            loose_unit = "kg"

    allows = pack_size > 1 and loose_unit in _LOOSE_OK
    if flag is False:
        allows = False
    elif flag is True and pack_size > 1:
        loose_unit = loose_unit if loose_unit in _LOOSE_OK else "kg"
        allows = True

    if allows and loose_unit in _LOOSE_OK:
        sale = f"{_fmt_qty(pack_size)}{loose_unit}"

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
    if billed == (info.loose_unit or ""):
        return True
    # POS / staff may type kg, kgs, 1kg
    billed_weight = parse_weight(unit)
    if billed_weight and billed_weight[1] == (info.loose_unit or "kg"):
        return billed_weight[0] == 1 or billed in _LOOSE_ALIASES
    return billed in _LOOSE_ALIASES and (info.loose_unit or "kg") == "kg"


def billed_to_stock_qty(product: object, quantity: Decimal, unit: str | None) -> Decimal:
    """Convert billed qty (bags or kg) to on-hand pack qty.

    1 kg from a 50 kg bag → 0.020 bags; 1 kg from a 25 kg bag → 0.040 bags.
    Selling a whole bag (unit 50kg / 25kg / 45kg) reduces stock by that bag count.
    """
    qty = Decimal(quantity)
    info = pack_info(product)
    if is_loose_sale(product, unit):
        if info.pack_size <= 0:
            return qty.quantize(_STOCK_QTY, rounding=ROUND_HALF_UP)
        qty = qty / info.pack_size
    return qty.quantize(_STOCK_QTY, rounding=ROUND_HALF_UP)


def loose_unit_price(pack_price: Decimal, product: object) -> Decimal:
    info = pack_info(product)
    if info.pack_size <= 0:
        return Decimal(pack_price)
    return (Decimal(pack_price) / info.pack_size).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
