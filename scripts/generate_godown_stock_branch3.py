#!/usr/bin/env python3
"""Build a single-shot Godown stock load for branch 3.

  python3 scripts/generate_godown_stock_branch3.py

Reads:
  Stock Master 16-09-2026.xlsx  (Products, Packing, Godown, Expiry)
  Dump20260916.sql              (live product dump)

Writes:
  deploy/mysql/migrate_from_dump/25_stock_godown_branch3.sql

Blank Godown cells are skipped. 0 is treated as counted (stock set to 0).
Blank product names inherit the previous row (merged packing variants).
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "Stock Master 16-09-2026.xlsx"
DUMP = ROOT / "Dump20260916.sql"
OUT = ROOT / "deploy" / "mysql" / "migrate_from_dump" / "25_stock_godown_branch3.sql"

ORG_ID = 1
BRANCH_ID = 3
BATCH_NO = "STOCK-ON-HAND"

# Sheet name+pack -> live product.name (spelling / brand-prefix variants)
ALIASES: dict[tuple[str, str], str] = {
    ("AQUACOL", "500ML"): "AQUACAL - 500 ML",
    ("CHEETA", "1L"): "CHEETAH - 1 L",
    ("GALAXY EXPERT 0 001", "100ML"): "GALAXY EXPERT - 100 ML",
    ("GSP SICKLE", "250ML"): "SICKLE - 250 ML",
    ("GSP SICKLE", "500ML"): "SICKLE - 500 ML",
    ("GSP SICKLE", "1L"): "SICKLE - 1 LTR",
    ("HUMIRICH F", "500ML"): "HUMI RICH - 500 ML",
    ("HUMIRICH F", "1L"): "HUMI RICH - 1 LTR",
    ("HURRICAN PLUS", "100ML"): "HURRICANE PLUS - 100 ML",
    ("HURRICAN PLUS", "250ML"): "HURRICANE PLUS - 250 ML",
    ("KANTROL PLUS", "100ML"): "KANTROL PLUSS - 100 ML",
    ("KANTROL PLUS", "250ML"): "KANTROL PLUSS - 250 ML",
    ("KANTROL PLUS", "500ML"): "KANTROL PLUSS - 500 ML",
    ("KINGZYME GR", "5KG"): "KING ZYME BUCKET - 5 KGS",
    ("PRETI SUPER", "600ML"): "PRETI EW - 600 ML",
    ("PENDIKEM XTRA", "350ML"): "PENDIKEM CS - 350 ML",
    ("PENDIKEM XTRA", "700ML"): "PENDIKEM CS - 700 ML",
    ("PROGIB EASY", "2.5G"): "PROGIBB EASY - 2.5 GMS",
    ("PYRAKIL", "100ML"): "PYRAKILL - 100 ML",
    ("PYRAKIL", "250ML"): "PYRAKILL - 250 ML",
    ("RASHAYANCHLOR", "500ML"): "RASAYAN CHLOR - 500 ML",
    ("RICH BORON", "100G"): "RICH BOR - 100 GMS",
    ("SAMTA MAGICAL", "250ML"): "MAGICAL - 250 ML",
    ("SAMTA MAGICAL", "500ML"): "MAGICAL - 500 ML",
    ("SPIC CYTOZ", "500ML"): "SPIC CYTOZYME - 500 ML",
    ("SUMI PREMT", "100ML"): "SUMI PREMPT - 100MLS",
    ("TEJA EW", "100ML"): "TEJA - 100 ML",
    ("TEJA EW", "250ML"): "TEJA - 250 ML",
    ("TEJA EW", "500ML"): "TEJA - 500 ML",
    ("TEPRONIL", "1KG"): "TEPROANIL - 1 KGS",
    ("THUNDERBOLT", "100ML"): "THUNDER BOLD - 100 ML",
    ("THUNDERBOLT", "500ML"): "THUNDER BOLD - 500 ML",
    ("VAJRA 19 19 19", "100ML"): "19:19:19 VAJRA - 100 ML",
    ("VASUDHA", "1KG"): "VASUDHAA - 1 KGS",
    ("VASUDHA", "3KG"): "VASUDHAA - 3 KGS",
    ("VISWAJITH", "100G"): "VISWAJIT - 100 GMS",
    ("WEED BLAZE", "250ML"): "WEED BLLAZE - 250 ML",
    ("WEED BLAZE", "400ML"): "WEED BLLAZE - 400 ML",
    ("WEED BLAZE", "1L"): "WEED BLLAZE - 1 LTR",
    ("WILLOWWOOD VAL XTRA", "100ML"): "VALXTRA - 100 ML",
    ("WILLOWWOOD VAL XTRA", "250ML"): "VALXTRA - 250 ML",
}


def sql_str(value: object | None) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def sql_qty(value: Decimal) -> str:
    if value == value.to_integral():
        return str(int(value))
    return format(value, "f")


def as_qty(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None


def norm_name(text: str) -> str:
    s = str(text or "").upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def compact_name(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", norm_name(text))


def norm_pack(text: str) -> str:
    s = re.sub(r"\s+", "", str(text or "").upper())
    reps = (
        "MILLILITRES",
        "MILLILITERS",
        "MILLILITRE",
        "MILLILITER",
        "MLS",
        "LITRES",
        "LITERS",
        "LITRE",
        "LTRS",
        "LTR",
        "LITR",
        "LTRE",
        "KILOGRAMS",
        "KILOGRAM",
        "KGS",
        "GRAMS",
        "GRAM",
        "GMS",
    )
    units = {
        "MILLILITRES": "ML",
        "MILLILITERS": "ML",
        "MILLILITRE": "ML",
        "MILLILITER": "ML",
        "MLS": "ML",
        "LITRES": "L",
        "LITERS": "L",
        "LITRE": "L",
        "LTRS": "L",
        "LTR": "L",
        "LITR": "L",
        "LTRE": "L",
        "KILOGRAMS": "KG",
        "KILOGRAM": "KG",
        "KGS": "KG",
        "GRAMS": "G",
        "GRAM": "G",
        "GMS": "G",
    }
    for token in reps:
        if s.endswith(token):
            s = s[: -len(token)] + units[token]
            break
    if s.endswith("GM") and not s.endswith("KG"):
        s = s[:-2] + "G"
    if s.endswith("MML"):
        s = s[:-3] + "ML"
    if s.endswith("MO"):
        s = s[:-2] + "ML"
    return s


def split_sql_values(s: str) -> list[str]:
    fields: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] in " \t\n\r":
            i += 1
            continue
        if s[i] == "'":
            i += 1
            buf: list[str] = []
            while i < n:
                if s[i] == "\\" and i + 1 < n:
                    buf.append(s[i : i + 2])
                    i += 2
                    continue
                if s[i] == "'":
                    if i + 1 < n and s[i + 1] == "'":
                        buf.append("''")
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(s[i])
                i += 1
            fields.append("'" + "".join(buf) + "'")
        else:
            j = i
            while j < n and s[j] != ",":
                j += 1
            fields.append(s[i:j].strip())
            i = j
        if i < n and s[i] == ",":
            i += 1
    return fields


def unquote(v: str | None) -> str | None:
    if v is None or v == "NULL":
        return None
    if v.startswith("'") and v.endswith("'"):
        inner = v[1:-1]
        return (
            inner.replace("\\\\", "\\")
            .replace("\\'", "'")
            .replace("''", "'")
            .replace('\\"', '"')
        )
    return v


def parse_dump_tuples(text: str) -> list[str]:
    inserts = re.findall(r"INSERT INTO `product` VALUES (.*?);", text, re.S)
    raw = ",".join(inserts).strip()
    body = raw[1:-1]
    tuples: list[str] = []
    buf: list[str] = []
    in_str = False
    esc = False
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if in_str:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_str = False
            i += 1
            continue
        if ch == "'":
            in_str = True
            buf.append(ch)
            i += 1
            continue
        if ch == ")" and i + 1 < n and body[i + 1] == "," and i + 2 < n and body[i + 2] == "(":
            tuples.append("".join(buf))
            buf = []
            i += 3
            continue
        buf.append(ch)
        i += 1
    if buf:
        tuples.append("".join(buf))
    return tuples


def parse_products() -> list[dict]:
    text = DUMP.read_text(encoding="utf-8")
    rows = []
    for t in parse_dump_tuples(text):
        fields = split_sql_values(t)
        sku = unquote(fields[1])
        name = unquote(fields[3]) or ""
        attrs = unquote(fields[22]) or ""
        pid = int(fields[23])
        deleted = int(fields[26]) == 1
        pack = ""
        m = re.search(r'"packing"\s*:\s*"([^"]*)"', attrs)
        if m:
            pack = m.group(1)
        if " - " in name:
            item, name_pack = name.rsplit(" - ", 1)
        else:
            item, name_pack = name, pack
        rows.append(
            {
                "id": pid,
                "sku": sku,
                "name": name,
                "item": item,
                "pack": pack or name_pack,
                "deleted": deleted,
            }
        )
    return rows


def prefer(cands: list[dict]) -> dict | None:
    live = [c for c in cands if not c["deleted"]] or cands
    uniq = {c["id"]: c for c in live}
    if len(uniq) == 1:
        return next(iter(uniq.values()))
    if not live:
        return None
    return max(live, key=lambda c: c["id"])


class Matcher:
    def __init__(self, products: list[dict]):
        self.products = products
        self.by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
        self.by_compact: dict[tuple[str, str], list[dict]] = defaultdict(list)
        self.by_pack: dict[str, list[dict]] = defaultdict(list)
        self.by_full: dict[str, dict] = {}
        for p in products:
            key = (norm_name(p["item"]), norm_pack(p["pack"]))
            self.by_key[key].append(p)
            self.by_compact[(compact_name(p["item"]), norm_pack(p["pack"]))].append(p)
            self.by_pack[norm_pack(p["pack"])].append(p)
            self.by_full[p["name"].upper()] = p

    def match(self, product: str, packing: str) -> tuple[dict | None, str]:
        n = norm_name(product)
        p = norm_pack(packing)
        alias = ALIASES.get((n, p))
        if alias:
            hit = self.by_full.get(alias.upper())
            if hit:
                return hit, "alias"
        c = compact_name(product)
        hits = self.by_key.get((n, p), [])
        if hits:
            return prefer(hits), "exact"
        hits = self.by_compact.get((c, p), [])
        if hits:
            return prefer(hits), "compact-name"
        sheet_tokens = [t for t in n.split() if t]
        scored: list[tuple[tuple, dict]] = []
        for row in self.by_pack.get(p, []):
            item_n = norm_name(row["item"])
            item_set = set(item_n.split())
            if not sheet_tokens:
                continue
            overlap = sum(1 for t in sheet_tokens if t in item_set)
            if overlap == 0:
                continue
            standalone = compact_name(row["item"]) in {"PLUS", "POW", "GR", "HD"}
            score = (overlap, 0 if not standalone else -5, len(item_n))
            if overlap == len(sheet_tokens) or (overlap >= 2 and overlap >= len(sheet_tokens) - 1):
                scored.append((score, row))
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            best_score = scored[0][0]
            best = [row for score, row in scored if score[:2] == best_score[:2]]
            live = [x for x in best if not x["deleted"]] or best
            ids = {x["id"] for x in live}
            if len(ids) == 1:
                return prefer(live), "packing+tokens"
            return None, "ambiguous:" + "/".join(sorted({x["name"] for x in live})[:4])
        return None, "unmatched"


def fmt_expiry(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def load_sheet() -> list[dict]:
    import sys

    sys.path.insert(0, "/tmp/pydeps")
    import openpyxl

    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["Sheet1"]
    rows = []
    last_name = ""
    for r in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=4, values_only=True):
        raw_name = str(r[0]).strip() if r[0] is not None else ""
        pack = str(r[1]).strip() if r[1] is not None else ""
        if raw_name:
            last_name = raw_name
        name = raw_name or last_name
        if not name:
            continue
        rows.append(
            {
                "name": name,
                "pack": pack,
                "qty": as_qty(r[2]),
                "expiry": fmt_expiry(r[3]),
            }
        )
    return rows


def main() -> None:
    products = parse_products()
    matcher = Matcher(products)
    sheet = load_sheet()
    print(f"Products {len(products)}  sheet rows {len(sheet)}")

    matched: list[dict] = []
    unmatched: list[dict] = []
    skipped = 0
    for row in sheet:
        if row["qty"] is None:
            skipped += 1
            continue
        hit, how = matcher.match(row["name"], row["pack"])
        if not hit:
            unmatched.append({**row, "how": how})
            continue
        matched.append({**row, "product": hit, "how": how})

    # Collapse multiple counted rows that map to the same live product_id.
    # Same sheet name+pack: last non-zero wins (duplicate listing / recount).
    # Different sheet names: quantities are added (two labels for one SKU).
    by_pid: dict[int, dict] = {}
    dupes: list[str] = []
    for row in matched:
        pid = row["product"]["id"]
        if pid not in by_pid:
            by_pid[pid] = dict(row)
            continue
        prev = by_pid[pid]
        same_label = (
            norm_name(prev["name"]) == norm_name(row["name"])
            and norm_pack(prev["pack"]) == norm_pack(row["pack"])
        )
        if same_label:
            if row["qty"] != 0:
                prev["qty"] = row["qty"]
                prev["expiry"] = row["expiry"] or prev["expiry"]
                prev["how"] = row["how"]
            dupes.append(
                f"product_id={pid} recount {prev['name']}/{prev['pack']} "
                f"kept qty={prev['qty']}"
            )
        else:
            merged = (prev["qty"] or Decimal("0")) + (row["qty"] or Decimal("0"))
            dupes.append(
                f"product_id={pid} summed {prev['name']}/{prev['pack']}={prev['qty']} "
                f"+ {row['name']}/{row['pack']}={row['qty']} -> {merged}"
            )
            prev["qty"] = merged
            prev["expiry"] = row["expiry"] or prev["expiry"]
            prev["name"] = f"{prev['name']} + {row['name']}"
            prev["pack"] = f"{prev['pack']} + {row['pack']}"
            prev["how"] = f"{prev['how']}+{row['how']}"
    matched_unique = list(by_pid.values())
    matched_unique.sort(key=lambda x: (x["product"]["name"], x["product"]["id"]))

    product_ids = [m["product"]["id"] for m in matched_unique]
    id_list = ", ".join(str(i) for i in sorted(product_ids))
    qty_sum = sum((m["qty"] or Decimal("0")) for m in matched_unique)
    expiry_rows = [m for m in matched_unique if m["expiry"]]

    lines: list[str] = [
        "-- Godown physical stock from Stock Master 16-09-2026.xlsx (Sheet1)",
        "-- Products matched against Dump20260916.sql",
        "-- Review before running. Safe to re-run (upserts branch 3 STOCK-ON-HAND only).",
        "--",
        f"-- Target: organization_id = {ORG_ID}, branch_id = {BRANCH_ID}",
        "-- Branch 3 must already exist. This script does not create the branch",
        "-- and does not change stock on branch 1 (AVL) or branch 2 (TVM).",
        "--",
        "-- Skip rules: blank Godown is skipped. 0 is treated as counted (stock set to 0).",
        "-- Blank product names inherit the previous row (merged packing variants).",
        "-- Counted qty is stored on a STOCK-ON-HAND batch looked up/created by product_id.",
        "--",
        f"-- Sheet rows: {len(sheet)}  skipped (no qty): {skipped}",
        f"-- Matched with qty: {len(matched)}  unique products: {len(matched_unique)}  unmatched: {len(unmatched)}",
        f"-- Duplicate sheet→product mappings (last row wins): {len(dupes)}",
        "--",
        "--   mysql -u root -p skac_new < deploy/mysql/migrate_from_dump/25_stock_godown_branch3.sql",
        "",
        "USE skac_new;",
        "SET NAMES utf8mb4;",
        "",
        "START TRANSACTION;",
        "",
        "-- ---------------------------------------------------------------------------",
        "-- STEP 0) STOCK-ON-HAND batch per counted product",
        "-- ---------------------------------------------------------------------------",
        "INSERT INTO batch (organization_id, product_id, batch_no, expiry_date, purchase_price)",
        "SELECT p.organization_id, p.id, 'STOCK-ON-HAND', NULL, COALESCE(p.purchase_price, 0)",
        "FROM product p",
        f"WHERE p.organization_id = {ORG_ID} AND p.id IN ({id_list})",
        "  AND NOT EXISTS (",
        "    SELECT 1 FROM batch b",
        "    WHERE b.organization_id = p.organization_id",
        "      AND b.product_id = p.id",
        "      AND b.batch_no = 'STOCK-ON-HAND'",
        "  );",
        "",
        "-- ---------------------------------------------------------------------------",
        "-- STEP 1) Counted Godown qty (insert missing rows, then set quantities)",
        "-- ---------------------------------------------------------------------------",
        "INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity)",
        "SELECT x.organization_id, x.branch_id, x.product_id, b.id, x.qty",
        "FROM (",
    ]

    union_lines = []
    for i, row in enumerate(matched_unique):
        pid = row["product"]["id"]
        qty = sql_qty(row["qty"])
        prefix = "  " if i == 0 else "  UNION ALL "
        comment = (
            f"{row['product']['name']}  sheet {row['name']} / {row['pack']}  "
            f"qty={sql_qty(row['qty'])}  match={row['how']}"
        )
        union_lines.append(
            f"{prefix}SELECT {ORG_ID} AS organization_id, {BRANCH_ID} AS branch_id, "
            f"{pid} AS product_id, CAST({qty} AS DECIMAL(14,3)) AS qty  -- {comment}"
        )
    lines += union_lines
    lines += [
        ") x",
        "JOIN batch b ON b.organization_id = x.organization_id",
        "          AND b.product_id = x.product_id",
        f"          AND b.batch_no = '{BATCH_NO}'",
        "WHERE NOT EXISTS (",
        "  SELECT 1 FROM stock s",
        "  WHERE s.branch_id = x.branch_id AND s.batch_id = b.id",
        ");",
        "",
        "UPDATE stock s",
        "JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND'",
        "JOIN (",
    ]
    lines += union_lines
    lines += [
        ") x ON x.product_id = s.product_id",
        "   AND x.organization_id = s.organization_id",
        "   AND x.branch_id = s.branch_id",
        "SET s.quantity = x.qty, s.updated_at = NOW()",
        f"WHERE s.organization_id = {ORG_ID} AND s.branch_id = {BRANCH_ID};",
        "",
    ]

    if expiry_rows:
        lines += [
            "-- ---------------------------------------------------------------------------",
            "-- STEP 2) Expiry on STOCK-ON-HAND (from sheet, where present)",
            "-- ---------------------------------------------------------------------------",
        ]
        for row in expiry_rows:
            pid = row["product"]["id"]
            exp = sql_str(row["expiry"])
            lines.append(
                "UPDATE batch SET "
                f"expiry_date = {exp}, updated_at = NOW() "
                f"WHERE organization_id = {ORG_ID} AND product_id = {pid} "
                f"AND batch_no = '{BATCH_NO}' "
                f"AND (expiry_date IS NULL OR expiry_date <> {exp});"
            )
        lines.append("")

    lines += [
        "COMMIT;",
        "",
        "-- ---------------------------------------------------------------------------",
        "-- Unmatched sheet rows (not applied). Add aliases or create the packing in product.",
        "-- ---------------------------------------------------------------------------",
        "",
    ]
    for row in unmatched:
        lines.append(
            f"-- {row['name']} / {row['pack']}   Godown={sql_qty(row['qty'])}   ({row['how']})"
        )

    if dupes:
        lines += ["", "-- Duplicate mappings (merged):"]
        for note in dupes:
            lines.append(f"--   {note}")

    lines += [
        "",
        f"-- Applied unique products: {len(matched_unique)}  qty {qty_sum}",
        f"-- Unmatched counted rows: {len(unmatched)}",
        "",
        "-- Quick check after load:",
        f"--   SELECT COUNT(*), SUM(quantity) FROM stock WHERE organization_id = {ORG_ID} AND branch_id = {BRANCH_ID};",
        "",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"matched {len(matched)} unique {len(matched_unique)} unmatched {len(unmatched)} skipped {skipped}")
    print(f"qty sum {qty_sum}  dupes {len(dupes)}")
    print("unmatched:")
    for row in unmatched:
        print(f"  {row['name']} / {row['pack']}  qty={row['qty']}  {row['how']}")


if __name__ == "__main__":
    main()
