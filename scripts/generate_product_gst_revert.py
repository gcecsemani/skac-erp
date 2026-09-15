#!/usr/bin/env python3
"""Undo 22_product_gst.sql + 23_product_purchase_gst.sql on an already-loaded DB.

Restores dump listed sale_price / purchase_price and the legacy gst_rate
(almost all 0) from 08_product.sql so POS bills the shop's original pack
prices again. Opening batches that 23 touched are restored too.

  python3 scripts/generate_product_gst_revert.py

Writes deploy/mysql/migrate_from_dump/24_revert_product_gst_prices.sql
"""
from __future__ import annotations

import sys
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

OUT = ROOT / "deploy" / "mysql" / "migrate_from_dump" / "24_revert_product_gst_prices.sql"


def money(value: Decimal) -> str:
    return f"{value.quantize(TWOPLACES):.2f}"


def parse_products() -> list[dict]:
    text = SRC.read_text(encoding="utf-8")
    rows = []
    for m in ROW_RE.finditer(text):
        pid, sku, _barcode, name, category, hsn_raw, old_gst, _mrp, purchase, sale = m.groups()
        name = name.replace("\\'", "'")
        old_gst_d = Decimal(old_gst)
        old_purchase = Decimal(purchase)
        old_sale = Decimal(sale)
        new_gst = gst_for(category)
        new_sale, _ = exclusive_price(old_sale, new_gst)
        new_purchase, _ = exclusive_price(old_purchase, new_gst)
        if new_sale == old_sale and new_purchase == old_purchase and new_gst == old_gst_d:
            continue
        rows.append({
            "id": int(pid),
            "name": name,
            "category": category,
            "old_gst": old_gst_d,
            "new_gst": new_gst,
            "old_sale": old_sale,
            "new_sale": new_sale,
            "old_purchase": old_purchase,
            "new_purchase": new_purchase,
        })
    if len(rows) < 1000:
        raise SystemExit(f"parsed only {len(rows)} revert rows from {SRC}")
    return rows


def main() -> None:
    changes = parse_products()
    sale_n = sum(1 for p in changes if p["new_sale"] != p["old_sale"])
    purch_n = sum(1 for p in changes if p["new_purchase"] != p["old_purchase"])
    gst_n = sum(1 for p in changes if p["new_gst"] != p["old_gst"])

    lines: list[str] = []
    w = lines.append
    w("-- Revert 22_product_gst.sql and 23_product_purchase_gst.sql")
    w("-- back to dump listed prices (08_product.sql).")
    w("--")
    w("-- Restores:")
    w("--   product.sale_price, product.purchase_price, product.gst_rate")
    w("--   LEGACY-OPENING / STOCK-ON-HAND batch.purchase_price")
    w("-- GST rate goes back to the legacy value (almost all 0). That is")
    w("-- required: SKAC billing adds gst_rate on top of sale_price, so leaving")
    w("-- 5%/18% on the listed pack price would overcharge the farmer.")
    w("-- Historical invoices and GRN lots are not touched.")
    w("--")
    w("-- Idempotent: only rows still at the exclusive prices 22/23 wrote,")
    w("-- or that still have the gst_backed_out JSON flags.")
    w("-- Skips a SKU if sale/purchase were edited away from those exclusive")
    w("-- values and the flags were already cleared.")
    w("--")
    w("--   mysql -u root -p skac_new < deploy/mysql/migrate_from_dump/24_revert_product_gst_prices.sql")
    w("--")
    w(f"-- Rows in revert set: {len(changes)}")
    w(f"--   sale_price to restore:     {sale_n}")
    w(f"--   purchase_price to restore: {purch_n}")
    w(f"--   gst_rate to restore:       {gst_n}")
    w("")
    w("USE skac_new;")
    w("SET NAMES utf8mb4;")
    w("")
    w("DROP TEMPORARY TABLE IF EXISTS product_gst_revert;")
    w("CREATE TEMPORARY TABLE product_gst_revert (")
    w("  id INT PRIMARY KEY,")
    w("  old_gst DECIMAL(5,2) NOT NULL,")
    w("  new_gst DECIMAL(5,2) NOT NULL,")
    w("  old_sale DECIMAL(12,2) NOT NULL,")
    w("  new_sale DECIMAL(12,2) NOT NULL,")
    w("  old_purchase DECIMAL(12,2) NOT NULL,")
    w("  new_purchase DECIMAL(12,2) NOT NULL")
    w(");")
    w("")

    for i in range(0, len(changes), BATCH):
        chunk = changes[i:i + BATCH]
        w("INSERT INTO product_gst_revert "
          "(id, old_gst, new_gst, old_sale, new_sale, old_purchase, new_purchase) VALUES")
        vals = []
        for p in chunk:
            vals.append(
                f"  ({p['id']}, {money(p['old_gst'])}, {money(p['new_gst'])}, "
                f"{money(p['old_sale'])}, {money(p['new_sale'])}, "
                f"{money(p['old_purchase'])}, {money(p['new_purchase'])})"
            )
        w(",\n".join(vals) + ";")
        w("")

    w("-- Review: what still looks exclusive vs already listed.")
    w("SELECT")
    w("  SUM(p.sale_price = f.new_sale) AS sale_still_exclusive,")
    w("  SUM(p.sale_price = f.old_sale) AS sale_already_listed,")
    w("  SUM(p.purchase_price = f.new_purchase) AS purchase_still_exclusive,")
    w("  SUM(p.purchase_price = f.old_purchase) AS purchase_already_listed,")
    w("  SUM(p.gst_rate = f.new_gst) AS gst_still_statutory")
    w("FROM product_gst_revert f")
    w("JOIN product p ON p.id = f.id;")
    w("")
    w("UPDATE product p")
    w("JOIN product_gst_revert f ON f.id = p.id")
    w("SET")
    w("  p.gst_rate = f.old_gst,")
    w("  p.sale_price = f.old_sale,")
    w("  p.purchase_price = f.old_purchase,")
    w("  p.attributes = JSON_REMOVE(")
    w("    COALESCE(p.attributes, JSON_OBJECT()),")
    w("    '$.legacy_sale_price',")
    w("    '$.gst_backed_out',")
    w("    '$.legacy_purchase_price',")
    w("    '$.gst_purchase_backed_out'")
    w("  )")
    w(f"WHERE p.organization_id = {ORG_ID}")
    w("  AND (")
    w("    p.sale_price = f.new_sale")
    w("    OR p.purchase_price = f.new_purchase")
    w("    OR JSON_EXTRACT(p.attributes, '$.legacy_sale_price') IS NOT NULL")
    w("    OR JSON_EXTRACT(p.attributes, '$.legacy_purchase_price') IS NOT NULL")
    w("    OR JSON_EXTRACT(p.attributes, '$.gst_backed_out') IS NOT NULL")
    w("    OR JSON_EXTRACT(p.attributes, '$.gst_purchase_backed_out') IS NOT NULL")
    w("  );")
    w("")
    w("SELECT ROW_COUNT() AS products_reverted;")
    w("")
    w("UPDATE batch b")
    w("JOIN product_gst_revert f ON f.id = b.product_id")
    w("SET b.purchase_price = f.old_purchase")
    w(f"WHERE b.organization_id = {ORG_ID}")
    w("  AND b.batch_no IN ('LEGACY-OPENING', 'STOCK-ON-HAND')")
    w("  AND b.purchase_price = f.new_purchase")
    w("  AND f.new_purchase <> f.old_purchase;")
    w("")
    w("SELECT ROW_COUNT() AS opening_batches_reverted;")
    w("")
    w("-- Spot-check: listed prices should match 08_product.sql again.")
    w("SELECT p.id, p.name, p.category, p.gst_rate, p.purchase_price, p.sale_price,")
    w("       JSON_EXTRACT(p.attributes, '$.gst_backed_out') AS gst_flag,")
    w("       JSON_EXTRACT(p.attributes, '$.gst_purchase_backed_out') AS purch_flag")
    w("FROM product p")
    w("JOIN product_gst_revert f ON f.id = p.id")
    w("ORDER BY p.category, p.name")
    w("LIMIT 25;")
    w("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"revert rows {len(changes)}  sale {sale_n}  purchase {purch_n}  gst {gst_n}")
    print(f"  wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
