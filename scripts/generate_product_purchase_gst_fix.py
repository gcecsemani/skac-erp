#!/usr/bin/env python3
"""Build a reviewable GST back-out UPDATE for product.purchase_price.

22_product_gst.sql made sale_price GST-exclusive so POS still charges today's
listed pack total. purchase_price was left as the dump listed cost, so P&L
compared exclusive sales to inclusive cost and understated margin.

This script stores the exclusive purchase that, plus statutory GST, reconstructs
the listed cost — same half-even rule as billing.py / 22_product_gst.sql.

  python3 scripts/generate_product_purchase_gst_fix.py

Writes deploy/mysql/migrate_from_dump/23_product_purchase_gst.sql
"""
from __future__ import annotations

import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_product_gst_fix import (
    BATCH,
    ORG_ID,
    ROOT,
    ROW_RE,
    SRC,
    TWOPLACES,
    exclusive_price,
    gst_for,
)

OUT = ROOT / "deploy" / "mysql" / "migrate_from_dump" / "23_product_purchase_gst.sql"


def money(value: Decimal) -> str:
    return f"{value.quantize(TWOPLACES):.2f}"


def parse_products() -> list[dict]:
    text = SRC.read_text(encoding="utf-8")
    rows = []
    for m in ROW_RE.finditer(text):
        pid, sku, _barcode, name, category, hsn_raw, old_gst, _mrp, purchase, sale = m.groups()
        hsn = None if hsn_raw == "NULL" else hsn_raw.strip("'")
        name = name.replace("\\'", "'")
        rows.append({
            "id": int(pid),
            "sku": sku,
            "name": name,
            "category": category,
            "hsn": hsn,
            "old_gst": Decimal(old_gst),
            "old_purchase": Decimal(purchase),
            "old_sale": Decimal(sale),
            "new_gst": gst_for(category),
        })
    if len(rows) < 1000:
        raise SystemExit(f"parsed only {len(rows)} products from {SRC}")
    return rows


def main() -> None:
    products = parse_products()
    changes: list[dict] = []
    by_gst = Counter()
    by_diff = Counter()
    already_loss = 0
    still_loss = 0
    flipped_ok = 0
    for p in products:
        by_gst[p["new_gst"]] += 1
        new_purchase, reconstructed = exclusive_price(p["old_purchase"], p["new_gst"])
        new_sale, _billed_sale = exclusive_price(p["old_sale"], p["new_gst"])
        p["new_purchase"] = new_purchase
        p["reconstructed"] = reconstructed
        p["new_sale"] = new_sale
        diff = reconstructed - p["old_purchase"]
        by_diff[diff] += 1
        if p["old_purchase"] > p["old_sale"] > 0:
            already_loss += 1
        if new_purchase > new_sale > 0:
            still_loss += 1
        if p["old_purchase"] > new_sale >= new_purchase > 0:
            flipped_ok += 1
        if new_purchase == p["old_purchase"]:
            continue
        changes.append(p)

    paise_under = [p for p in changes if p["reconstructed"] < p["old_purchase"]]
    paise_over = [p for p in changes if p["reconstructed"] > p["old_purchase"]]

    lines: list[str] = []
    w = lines.append
    w("-- Back GST out of dump-loaded purchase_price so P&L compares exclusive")
    w("-- cost to exclusive sale (22_product_gst.sql already did this for sale_price).")
    w("--")
    w("-- Reports (report_tables._profit_loss / product profit) do:")
    w("--   gross profit = invoice taxable (excl. GST) - qty * product.purchase_price")
    w("-- After 22, sale is exclusive and purchase was still the listed pack cost,")
    w("-- so a ₹90 pesticide (₹80 cost) billed the farmer ₹90 but showed a loss")
    w("-- of ₹3.73. Exclusive purchase ₹67.80 restores the ~₹8.47 GST-free margin.")
    w("--")
    w("-- Same statutory rates as 22_product_gst.sql (from product.category):")
    w("--   seed         0%   — purchase_price unchanged")
    w("--   fertilizer   5%")
    w("--   pesticide   18%")
    w("-- MRP, historical invoice lines, and GRN lot prices are not touched.")
    w("-- Opening batches that copied the master listed cost are updated:")
    w("--   LEGACY-OPENING (10_batch.sql) and STOCK-ON-HAND (21_stock_on_hand.sql).")
    w("--")
    w("-- Exclusive price is chosen so listed cost + GST (half-even, 2 dp)")
    w("-- matches today's purchase_price. Amounts that cannot hit exactly at")
    w("-- 5%/18% land 1 paise under. Zero listed costs stay 0.")
    w("--")
    w("-- Review before running. Idempotent: skips a row if purchase_price moved")
    w("-- or attributes.gst_purchase_backed_out is already true. Run after 22.")
    w("-- Safe on an already-loaded DB (22 may already have been applied).")
    w("--")
    w(f"--   mysql -u root -p skac_new < deploy/mysql/migrate_from_dump/23_product_purchase_gst.sql")
    w("--")
    w(f"-- Products in 08_product.sql: {len(products)}")
    w(f"--   seed 0%:        {by_gst[Decimal('0.00')]}")
    w(f"--   fertilizer 5%:  {by_gst[Decimal('5.00')]}")
    w(f"--   pesticide 18%:  {by_gst[Decimal('18.00')]}")
    w(f"-- Rows updated: {len(changes)}  (seeds / zero cost / unchanged omitted)")
    w(f"-- Reconstructed vs listed cost: exact {by_diff[Decimal('0.00')]}  "
      f"-₹0.01 {by_diff[Decimal('-0.01')]}  +₹0.01 {by_diff[Decimal('0.01')]}")
    w(f"-- purchase > listed sale in dump: {already_loss}")
    w(f"-- exclusive purchase > exclusive sale after this script: {still_loss}")
    w(f"-- SKUs that looked like a loss after 22 but are profitable exclusive-to-exclusive: {flipped_ok}")
    if paise_over:
        w("-- +₹0.01 SKUs (no exclusive 2 dp total hits the listed cost without going over):")
        for p in paise_over:
            w(f"--   id={p['id']} {p['name']} listed {money(p['old_purchase'])} "
              f"exclusive {money(p['new_purchase'])} reconstructed {money(p['reconstructed'])} "
              f"@ {money(p['new_gst'])}%")
    w("")
    w("USE skac_new;")
    w("SET NAMES utf8mb4;")
    w("")
    w("DROP TEMPORARY TABLE IF EXISTS product_purchase_gst_fix;")
    w("CREATE TEMPORARY TABLE product_purchase_gst_fix (")
    w("  id INT PRIMARY KEY,")
    w("  new_gst DECIMAL(5,2) NOT NULL,")
    w("  old_purchase DECIMAL(12,2) NOT NULL,")
    w("  new_purchase DECIMAL(12,2) NOT NULL,")
    w("  reconstructed DECIMAL(12,2) NOT NULL")
    w(");")
    w("")

    for i in range(0, len(changes), BATCH):
        chunk = changes[i:i + BATCH]
        w("INSERT INTO product_purchase_gst_fix "
          "(id, new_gst, old_purchase, new_purchase, reconstructed) VALUES")
        vals = []
        for p in chunk:
            vals.append(
                f"  ({p['id']}, {money(p['new_gst'])}, "
                f"{money(p['old_purchase'])}, {money(p['new_purchase'])}, "
                f"{money(p['reconstructed'])})"
            )
        w(",\n".join(vals) + ";")
        w("")

    w("-- Review: exclusive vs listed cost by GST rate.")
    w("SELECT f.new_gst AS gst_pct, COUNT(*) AS sku,")
    w("       SUM(f.old_purchase) AS listed_cost, SUM(f.new_purchase) AS exclusive_cost,")
    w("       SUM(f.reconstructed) AS reconstructed,")
    w("       SUM(f.reconstructed) - SUM(f.old_purchase) AS reconstructed_minus_listed")
    w("FROM product_purchase_gst_fix f")
    w("GROUP BY f.new_gst")
    w("ORDER BY f.new_gst;")
    w("")
    w("SELECT p.id, p.sku, p.name, p.category,")
    w("       f.old_purchase, f.new_purchase, p.sale_price AS exclusive_sale,")
    w("       (f.new_purchase > p.sale_price) AS still_cost_above_sale")
    w("FROM product_purchase_gst_fix f")
    w("JOIN product p ON p.id = f.id")
    w("WHERE f.new_purchase > p.sale_price AND p.sale_price > 0")
    w("ORDER BY (f.new_purchase - p.sale_price) DESC, p.name")
    w("LIMIT 40;")
    w("")
    w("-- Write. Safe to re-run: only rows still sitting at the dump listed cost.")
    w("UPDATE product p")
    w("JOIN product_purchase_gst_fix f ON f.id = p.id")
    w("SET")
    w("  p.purchase_price = f.new_purchase,")
    w("  p.attributes = JSON_SET(")
    w("    COALESCE(p.attributes, JSON_OBJECT()),")
    w("    '$.legacy_purchase_price', f.old_purchase,")
    w("    '$.gst_purchase_backed_out', TRUE")
    w("  )")
    w(f"WHERE p.organization_id = {ORG_ID}")
    w("  AND p.purchase_price = f.old_purchase")
    w("  AND IFNULL(JSON_EXTRACT(p.attributes, '$.gst_purchase_backed_out'), FALSE) = FALSE;")
    w("")
    w("SELECT ROW_COUNT() AS products_updated;")
    w("")
    w("-- Opening stock lots copied the master listed cost. Historical GRN lots")
    w("-- keep the dump invoice price (may already be exclusive or mixed).")
    w("UPDATE batch b")
    w("JOIN product_purchase_gst_fix f ON f.id = b.product_id")
    w("SET b.purchase_price = f.new_purchase")
    w(f"WHERE b.organization_id = {ORG_ID}")
    w("  AND b.batch_no IN ('LEGACY-OPENING', 'STOCK-ON-HAND')")
    w("  AND b.purchase_price = f.old_purchase;")
    w("")
    w("SELECT ROW_COUNT() AS opening_batches_updated;")
    w("")
    w("-- Spot-check: exclusive sale vs exclusive purchase vs farmer bill.")
    w("SELECT p.id, p.name, p.category, p.gst_rate,")
    w("       p.purchase_price, p.sale_price,")
    w("       JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.legacy_purchase_price')) AS listed_cost_was,")
    w("       JSON_UNQUOTE(JSON_EXTRACT(p.attributes, '$.legacy_sale_price')) AS listed_sale_was,")
    w("       ROUND(p.sale_price + ROUND(p.sale_price * p.gst_rate / 100, 2), 2) AS billed_sale")
    w("FROM product p")
    w("JOIN product_purchase_gst_fix f ON f.id = p.id")
    w("ORDER BY p.category, p.name")
    w("LIMIT 25;")
    w("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"products {len(products)}  updates {len(changes)}")
    print(f"  gst 0/5/18 = {by_gst[Decimal('0.00')]}/{by_gst[Decimal('5.00')]}/{by_gst[Decimal('18.00')]}")
    print(f"  reconstructed exact/-0.01/+0.01 = "
          f"{by_diff[Decimal('0.00')]}/{by_diff[Decimal('-0.01')]}/{by_diff[Decimal('0.01')]}")
    print(f"  dump purchase>sale {already_loss}  after exclusive-to-exclusive {still_loss}")
    print(f"  recovered from 22 false-loss {flipped_ok}")
    print(f"  paise under/over among changes {len(paise_under)}/{len(paise_over)}")
    print(f"  wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
