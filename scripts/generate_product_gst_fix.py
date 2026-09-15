#!/usr/bin/env python3
"""Build a reviewable GST back-out UPDATE from migrate_from_dump/08_product.sql.

Legacy listed prices were billed as-is (gst_rate almost all 0). SKAC billing adds
GST on top of product.sale_price, so we set the statutory rate and store the
exclusive price that keeps the farmer's payable the same.

  python3 scripts/generate_product_gst_fix.py

Writes deploy/mysql/migrate_from_dump/22_product_gst.sql
"""
from __future__ import annotations

import re
from collections import Counter
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "deploy" / "mysql" / "migrate_from_dump" / "08_product.sql"
OUT = ROOT / "deploy" / "mysql" / "migrate_from_dump" / "22_product_gst.sql"
ORG_ID = 1
BATCH = 200
TWOPLACES = Decimal("0.01")

ROW_RE = re.compile(
    r"^\s*\((\d+), 1, '(P\d+)', (NULL|'[^']*'), '((?:\\'|[^'])*)', "
    r"'(fertilizer|pesticide|seed)', (NULL|'[^']*'), ([0-9.]+), "
    r"'[^']*', ([0-9.]+), ([0-9.]+), ([0-9.]+),",
    re.M,
)


def gst_for(category: str) -> Decimal:
    if category == "seed":
        return Decimal("0.00")
    if category == "fertilizer":
        return Decimal("5.00")
    return Decimal("18.00")


def billed(price: Decimal, rate: Decimal) -> Decimal:
    """Match backend/app/services/billing.py (Decimal quantize, half-even)."""
    taxable = price.quantize(TWOPLACES, rounding=ROUND_HALF_EVEN)
    tax = (taxable * rate / Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_EVEN)
    return (taxable + tax).quantize(TWOPLACES, rounding=ROUND_HALF_EVEN)


def exclusive_price(inclusive: Decimal, rate: Decimal) -> tuple[Decimal, Decimal]:
    """Exclusive sale_price so billed total stays as close as possible to today's price.

    Never picks a price that bills *more* than the listed amount when a
    same-or-lower option exists. Some 2-decimal totals cannot be hit exactly
    at 5%/18% — those land 1 paise under. Zero listed prices stay 0.
    """
    if rate == 0 or inclusive == 0:
        return inclusive, inclusive
    factor = Decimal(1) + rate / Decimal(100)
    seed = (inclusive / factor).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    best = seed
    best_key = (9, Decimal("99"), Decimal("99"))
    for delta in range(-8, 9):
        cand = seed + Decimal(delta) / 100
        if cand <= 0:
            continue
        total = billed(cand, rate)
        over = 1 if total > inclusive else 0
        key = (over, abs(total - inclusive), abs(cand - seed))
        if key < best_key:
            best, best_key = cand, key
    return best, billed(best, rate)


def parse_products() -> list[dict]:
    text = SRC.read_text(encoding="utf-8")
    rows = []
    for m in ROW_RE.finditer(text):
        pid, sku, _barcode, name, category, hsn_raw, old_gst, _mrp, _purchase, sale = m.groups()
        hsn = None if hsn_raw == "NULL" else hsn_raw.strip("'")
        name = name.replace("\\'", "'")
        rows.append({
            "id": int(pid),
            "sku": sku,
            "name": name,
            "category": category,
            "hsn": hsn,
            "old_gst": Decimal(old_gst),
            "old_sale": Decimal(sale),
            "new_gst": gst_for(category),
        })
    if len(rows) < 1000:
        raise SystemExit(f"parsed only {len(rows)} products from {SRC}")
    return rows


def money(value: Decimal) -> str:
    return f"{value.quantize(TWOPLACES):.2f}"


def main() -> None:
    products = parse_products()
    changes: list[dict] = []
    by_gst = Counter()
    by_diff = Counter()
    already_gst = 0
    for p in products:
        by_gst[p["new_gst"]] += 1
        if p["old_gst"] != 0:
            already_gst += 1
        new_sale, billed_after = exclusive_price(p["old_sale"], p["new_gst"])
        p["new_sale"] = new_sale
        p["billed_after"] = billed_after
        diff = billed_after - p["old_sale"]
        by_diff[diff] += 1
        if p["new_gst"] == p["old_gst"] and new_sale == p["old_sale"]:
            continue
        changes.append(p)

    paise_under = [p for p in changes if p["billed_after"] < p["old_sale"]]
    paise_over = [p for p in changes if p["billed_after"] > p["old_sale"]]

    lines: list[str] = []
    w = lines.append
    w("-- Set statutory GST on dump-loaded products and back it out of sale_price")
    w("-- so POS still charges the same listed amount the shop bills today.")
    w("--")
    w("-- Billing (app/services/billing.py) is GST-exclusive:")
    w("--   line_total = sale_price + sale_price * gst_rate / 100")
    w("-- Legacy rows in 08_product.sql copied item_details.Cgst+Sgst (almost all 0),")
    w("-- while sale_price was the farmer-facing pack price. If we only set gst_rate,")
    w("-- a ₹50 pesticide would print as ₹59. This script keeps that bill at ₹50.")
    w("--")
    w("-- GST from product.category (already inferred from HSN + name in 08_product.sql):")
    w("--   seed         0%   (HSN 10 / 12 / 07, sowing seed)     — sale_price unchanged")
    w("--   fertilizer   5%   (HSN 31 / 28 / 25, NPK, urea, micro)")
    w("--   pesticide   18%   (HSN 38 and everything else)")
    w("-- MRP is left as listed. purchase_price is backed out in 23_product_purchase_gst.sql.")
    w("-- Historical invoice lines are not touched.")
    w("--")
    w("-- Exclusive price is chosen so billed total (half-even, 2 dp, same as the API)")
    w("-- matches today's sale_price. Amounts that cannot hit exactly at 5%/18%")
    w("-- land 1 paise under. Zero listed prices stay 0 (GST rate is still set).")
    w("--")
    w("-- Review before running. Idempotent: skips a row if sale_price moved or")
    w("-- attributes.gst_backed_out is already true.")
    w("--")
    w(f"--   mysql -u root -p skac_new < deploy/mysql/migrate_from_dump/22_product_gst.sql")
    w("--")
    w(f"-- Products in 08_product.sql: {len(products)}")
    w(f"--   seed 0%:        {by_gst[Decimal('0.00')]}")
    w(f"--   fertilizer 5%:  {by_gst[Decimal('5.00')]}")
    w(f"--   pesticide 18%:  {by_gst[Decimal('18.00')]}")
    w(f"--   already had gst_rate > 0 in dump: {already_gst} (still backed out from listed sale_price)")
    w(f"-- Rows updated: {len(changes)}  (seeds with 0% and unchanged price omitted)")
    w(f"-- Billed vs listed: exact {by_diff[Decimal('0.00')]}  "
      f"-₹0.01 {by_diff[Decimal('-0.01')]}  +₹0.01 {by_diff[Decimal('0.01')]}")
    if paise_over:
        w("-- +₹0.01 SKUs (no exclusive 2 dp total hits the listed price without going over):")
        for p in paise_over:
            w(f"--   id={p['id']} {p['name']} listed {money(p['old_sale'])} "
              f"exclusive {money(p['new_sale'])} billed {money(p['billed_after'])} @ {money(p['new_gst'])}%")
    w("")
    w("USE skac_new;")
    w("SET NAMES utf8mb4;")
    w("")
    w("DROP TEMPORARY TABLE IF EXISTS product_gst_fix;")
    w("CREATE TEMPORARY TABLE product_gst_fix (")
    w("  id INT PRIMARY KEY,")
    w("  old_gst DECIMAL(5,2) NOT NULL,")
    w("  new_gst DECIMAL(5,2) NOT NULL,")
    w("  old_sale DECIMAL(12,2) NOT NULL,")
    w("  new_sale DECIMAL(12,2) NOT NULL,")
    w("  billed_after DECIMAL(12,2) NOT NULL")
    w(");")
    w("")

    for i in range(0, len(changes), BATCH):
        chunk = changes[i:i + BATCH]
        w("INSERT INTO product_gst_fix (id, old_gst, new_gst, old_sale, new_sale, billed_after) VALUES")
        vals = []
        for p in chunk:
            vals.append(
                f"  ({p['id']}, {money(p['old_gst'])}, {money(p['new_gst'])}, "
                f"{money(p['old_sale'])}, {money(p['new_sale'])}, {money(p['billed_after'])})"
            )
        w(",\n".join(vals) + ";")
        w("")

    w("-- Review: how many SKUs move to each rate, and the exclusive vs listed totals.")
    w("SELECT f.new_gst AS gst_pct, COUNT(*) AS sku,")
    w("       SUM(f.old_sale) AS listed_sale, SUM(f.new_sale) AS exclusive_sale,")
    w("       SUM(f.billed_after) AS billed_after,")
    w("       SUM(f.billed_after) - SUM(f.old_sale) AS billed_minus_listed")
    w("FROM product_gst_fix f")
    w("GROUP BY f.new_gst")
    w("ORDER BY f.new_gst;")
    w("")
    w("SELECT p.category, p.hsn_code, COUNT(*) AS sku, f.new_gst")
    w("FROM product_gst_fix f")
    w("JOIN product p ON p.id = f.id")
    w("GROUP BY p.category, p.hsn_code, f.new_gst")
    w("ORDER BY sku DESC, p.category, p.hsn_code")
    w("LIMIT 40;")
    w("")
    w("SELECT p.id, p.sku, p.name, p.category, p.hsn_code,")
    w("       f.old_gst, f.new_gst, f.old_sale, f.new_sale, f.billed_after,")
    w("       f.billed_after - f.old_sale AS paise_diff")
    w("FROM product_gst_fix f")
    w("JOIN product p ON p.id = f.id")
    w("WHERE f.billed_after <> f.old_sale")
    w("ORDER BY p.category, p.name, p.id;")
    w("")
    w("-- Write. Safe to re-run: only rows still sitting at the dump listed price.")
    w("UPDATE product p")
    w("JOIN product_gst_fix f ON f.id = p.id")
    w("SET")
    w("  p.gst_rate = f.new_gst,")
    w("  p.sale_price = f.new_sale,")
    w("  p.attributes = JSON_SET(")
    w("    COALESCE(p.attributes, JSON_OBJECT()),")
    w("    '$.legacy_sale_price', f.old_sale,")
    w("    '$.gst_backed_out', TRUE")
    w("  )")
    w(f"WHERE p.organization_id = {ORG_ID}")
    w("  AND p.sale_price = f.old_sale")
    w("  AND IFNULL(JSON_EXTRACT(p.attributes, '$.gst_backed_out'), FALSE) = FALSE;")
    w("")
    w("SELECT ROW_COUNT() AS products_updated;")
    w("")
    w("-- Spot-check: billed total vs the original listed price.")
    w("SELECT p.id, p.name, p.category, p.gst_rate, p.sale_price,")
    w("       JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.legacy_sale_price')) AS listed_was,")
    w("       ROUND(p.sale_price + ROUND(p.sale_price * p.gst_rate / 100, 2), 2) AS mysql_round_bill")
    w("FROM product p")
    w("JOIN product_gst_fix f ON f.id = p.id")
    w("ORDER BY p.category, p.name")
    w("LIMIT 25;")
    w("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"products {len(products)}  updates {len(changes)}")
    print(f"  gst 0/5/18 = {by_gst[Decimal('0.00')]}/{by_gst[Decimal('5.00')]}/{by_gst[Decimal('18.00')]}")
    print(f"  billed exact/-0.01/+0.01 = "
          f"{by_diff[Decimal('0.00')]}/{by_diff[Decimal('-0.01')]}/{by_diff[Decimal('0.01')]}")
    print(f"  wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
