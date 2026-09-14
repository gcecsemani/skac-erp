#!/usr/bin/env python3
"""Generate MySQL INSERT scripts from old-customers.csv / old-products.csv.

  python3 scripts/generate_legacy_inserts.py

Writes:
  deploy/mysql/migrate_customers.sql
  deploy/mysql/migrate_products.sql

Requires organization.id = 1 (or edit @org_id in the generated files).
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deploy" / "mysql"
CUSTOMERS_CSV = ROOT / "old-customers.csv"
PRODUCTS_CSV = ROOT / "old-products.csv"

PLACEHOLDER_PHONES = {
    "9999999999", "0000000000", "1234567890", "1111111111", "0", "00",
}
BATCH = 80

SEED_WORDS = (
    "paddy", "seed", "seeds", "bhendi", "gourd", "radish", "chilli hy",
    "coriander hy", "bean", "gram", "brinjal", "tomato", "ridge", "ash gourd",
    "bitter gourd", "cowpea", "maize", "ragi", "cumbu", "cholam",
)
FERT_WORDS = (
    "urea", "dap", "potash", "gypsum", "ammonium", "ssp", "mop", "npk",
    "super phosphate", "zinc", "boron", "humic", "neem cake", "biofert",
    "minsol", "growmore", "20:20", "19:19", "13:00", "28:28", "10:26",
    "12:32", "18:46", "0:0:50", "0:52:34",
)


def sql_str(value: object | None) -> str:
    if value is None:
        return "NULL"
    text = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{text}'"


def sql_num(value: Decimal | int | str) -> str:
    return str(value)


def sql_bool(value: bool) -> str:
    return "1" if value else "0"


def clip(value: object | None, n: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() == "NULL":
        return None
    return text[:n]


def money(value: object | None) -> Decimal:
    if value is None or str(value).strip() in ("", "NULL"):
        return Decimal("0.00")
    try:
        return Decimal(str(value).strip()).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def normalize_phone(raw: object | None) -> str | None:
    if raw is None:
        return None
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if digits.startswith("91") and len(digits) >= 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if not digits or digits in PLACEHOLDER_PHONES:
        return None
    if len(digits) != 10 or digits[0] not in "6789":
        return None
    return digits


def normalize_aadhaar(raw: object | None) -> str | None:
    if not raw or str(raw).strip().upper() in ("", "NULL"):
        return None
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    return digits if len(digits) == 12 else None


def farmer_name(raw: object | None, cust_id: str) -> str:
    name = clip(raw, 150)
    if not name:
        return f"Legacy farmer {cust_id}"
    if len(name) < 2:
        return f"{name}."
    return name


def write_batches(fh, header: str, rows: list[str], batch: int = BATCH) -> None:
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        fh.write(header + "\n")
        fh.write(",\n".join(chunk))
        fh.write(";\n\n")


# --- customers ---------------------------------------------------------------

def map_customers(path: Path) -> tuple[list[dict], dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        raw = list(csv.DictReader(f))
    stats = {
        "source": len(raw),
        "phone_cleared": 0,
        "phone_dup": 0,
        "aadhaar_dropped": 0,
        "with_due": 0,
    }
    staged: list[dict] = []
    for r in raw:
        phone = normalize_phone(r.get("phone"))
        if r.get("phone") and not phone:
            stats["phone_cleared"] += 1
        aadhaar = normalize_aadhaar(r.get("aadhaar_no"))
        if r.get("aadhaar_no") and str(r.get("aadhaar_no")).strip() not in ("", "NULL") and not aadhaar:
            stats["aadhaar_dropped"] += 1
        due = money(r.get("outstanding_balance"))
        credit_limit = money(r.get("credit_limit"))
        staged.append(
            {
                "id": int(r["id"]),
                "name": farmer_name(r.get("name"), r["id"]),
                "phone": phone,
                "village": clip(r.get("village"), 120),
                "district": clip(r.get("district"), 120) or "Tiruvannamalai",
                "aadhaar_no": aadhaar,
                "outstanding_balance": due,
                "credit_allowed": True,
                "credit_limit": credit_limit,
            }
        )
        if due > 0:
            stats["with_due"] += 1

    by_phone: dict[str, list[dict]] = defaultdict(list)
    for item in staged:
        if item["phone"]:
            by_phone[item["phone"]].append(item)
    for items in by_phone.values():
        if len(items) < 2:
            continue
        winner = max(items, key=lambda x: (x["outstanding_balance"], x["id"]))
        for item in items:
            if item is not winner:
                item["phone"] = None
                stats["phone_dup"] += 1
    staged.sort(key=lambda x: x["id"])
    return staged, stats


def write_customers(rows: list[dict], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    max_id = max(r["id"] for r in rows)
    values = []
    for r in rows:
        values.append(
            "  ("
            + ", ".join(
                [
                    sql_num(r["id"]),
                    "@org_id",
                    sql_str(r["name"]),
                    sql_str(r["phone"]),
                    sql_str(r["aadhaar_no"]),
                    sql_str(r["village"]),
                    sql_str(r["district"]),
                    sql_bool(r["credit_allowed"]),
                    sql_num(r["credit_limit"]),
                    sql_num(r["outstanding_balance"]),
                    "0",
                ]
            )
            + ")"
        )
    with dest.open("w", encoding="utf-8") as fh:
        fh.write("-- Legacy farmer import from old-customers.csv\n")
        fh.write("-- Requires organization.id = 1 (change @org_id if needed).\n")
        fh.write("-- Duplicate / placeholder phones are stored as NULL (unique org+phone).\n")
        fh.write("--\n")
        fh.write("--   mysql -u root -p skac < deploy/mysql/migrate_customers.sql\n\n")
        fh.write("USE skac;\nSET NAMES utf8mb4;\nSET @org_id := 1;\n\n")
        write_batches(
            fh,
            "INSERT INTO customer (\n"
            "  id, organization_id, name, phone, aadhaar_no, village, district,\n"
            "  credit_allowed, credit_limit, outstanding_balance, is_deleted\n"
            ") VALUES",
            values,
        )
        fh.write(f"ALTER TABLE customer AUTO_INCREMENT = {max_id + 1};\n")


# --- products ----------------------------------------------------------------

def digits(value: object | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def infer_category(name: str, hsn: str) -> str:
    n = name.lower()
    if any(w in n for w in SEED_WORDS) or hsn.startswith(("10", "12", "07")):
        if not any(w in n for w in ("insect", "pest", "weed")):
            return "seed"
    if hsn.startswith(("31", "28", "25")):
        return "fertilizer"
    if any(w in n for w in FERT_WORDS) or re.search(r"\d{1,2}\s*:\s*\d{1,2}\s*:\s*\d{1,2}", n):
        return "fertilizer"
    if hsn.startswith("21") and any(w in n for w in ("seed", "bhendi", "gourd", "chilli", "radish", "bean", "gram")):
        return "seed"
    if hsn.startswith("21"):
        return "fertilizer"
    if hsn.startswith("38"):
        return "pesticide"
    return "pesticide"


def gst_for(category: str, hsn: str) -> Decimal:
    if category == "seed":
        return Decimal("0.00")
    if category == "fertilizer" or hsn.startswith(("31", "28", "25")):
        return Decimal("5.00")
    return Decimal("18.00")


def infer_unit(name: str) -> str:
    pack = name.upper().replace(" ", "")
    m = re.search(r"-(\d*\.?\d+)([A-Z]+)\s*$", pack) or re.search(r"-(\d*\.?\d+)([A-Z]+)$", pack)
    token = ""
    if m:
        token = m.group(2)
    else:
        m2 = re.search(r"(\d+)(ML|MLS|LTR|LTRS|LITR|L|GMS|GM|KG|KGS|SEEDS|UNIT)\s*$", pack)
        token = m2.group(2) if m2 else ""
    if token in ("ML", "MLS", "LTR", "LTRS", "LITR", "L"):
        return "litre"
    if token in ("GMS", "GM", "G", "KG", "KGS"):
        return "kg"
    if token in ("SEEDS",):
        return "packet"
    if token in ("UNIT",):
        return "piece"
    if "ML" in pack or "LTR" in pack or re.search(r"\dL\b", name.upper()):
        return "litre"
    if "KG" in pack or "GMS" in pack:
        return "kg"
    return "packet"


def infer_npk(name: str) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    m = re.search(r"(\d{1,2})\s*:\s*(\d{1,2})\s*:\s*(\d{1,2})", name)
    if not m:
        return None, None, None
    return Decimal(m.group(1)), Decimal(m.group(2)), Decimal(m.group(3))


def unique_sku(name: str, used: set[str]) -> str:
    base = re.sub(r"\s+", " ", name).strip()[:40] or "PROD"
    sku = base
    n = 2
    while sku.lower() in used:
        suffix = f"-{n}"
        sku = (base[: 40 - len(suffix)] + suffix).strip()
        n += 1
    used.add(sku.lower())
    return sku


def map_products(path: Path) -> tuple[list[dict], dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        raw = list(csv.DictReader(f))
    stats: Counter[str] = Counter()
    used_sku: set[str] = set()
    staged: list[dict] = []
    for r in raw:
        name = clip(r.get("name"), 200) or f"Legacy product {r.get('id')}"
        hsn_raw = digits(r.get("hsn_code"))
        hsn = hsn_raw if hsn_raw and hsn_raw != "0" else None
        if hsn and len(hsn) > 12:
            hsn = hsn[:12]
        category = infer_category(name, hsn or "")
        mrp = money(r.get("mrp"))
        purchase = money(r.get("purchase_price"))
        sale = money(r.get("sale_price"))
        if mrp == 0 and sale > 0:
            mrp = sale
        n, p, k = infer_npk(name)
        staged.append(
            {
                "legacy_id": int(r["id"]) if str(r.get("id", "")).isdigit() else None,
                "sku": unique_sku(name, used_sku),
                "name": name,
                "category": category,
                "hsn_code": hsn,
                "gst_rate": gst_for(category, hsn or ""),
                "base_unit": infer_unit(name),
                "mrp": mrp,
                "purchase_price": purchase,
                "sale_price": sale,
                "npk_n": n,
                "npk_p": p,
                "npk_k": k,
            }
        )
        stats[category] += 1
    return staged, dict(stats)


def write_products(rows: list[dict], dest: Path) -> None:
    values = []
    for r in rows:
        extra = {"legacy_id": r["legacy_id"]} if r["legacy_id"] is not None else None
        values.append(
            "  ("
            + ", ".join(
                [
                    "@org_id",
                    sql_str(r["sku"]),
                    sql_str(r["name"]),
                    sql_str(r["category"]),
                    sql_str(r["hsn_code"]),
                    sql_num(r["gst_rate"]),
                    sql_str(r["base_unit"]),
                    sql_num(r["mrp"]),
                    sql_num(r["purchase_price"]),
                    sql_num(r["sale_price"]),
                    "0",
                    "1",
                    "0",
                    sql_num(r["npk_n"]) if r["npk_n"] is not None else "NULL",
                    sql_num(r["npk_p"]) if r["npk_p"] is not None else "NULL",
                    sql_num(r["npk_k"]) if r["npk_k"] is not None else "NULL",
                    sql_str(json.dumps(extra, separators=(",", ":"))) if extra else "NULL",
                    "0",
                ]
            )
            + ")"
        )
    with dest.open("w", encoding="utf-8") as fh:
        fh.write("-- Legacy product import from old-products.csv\n")
        fh.write("-- One row per packing size. Old shared product ids are kept in attributes.legacy_id.\n")
        fh.write("-- Category inferred from HSN/name (CSV marked everything as pesticide).\n")
        fh.write("-- GST: seed 0%, fertilizer 5%, pesticide 18%.\n")
        fh.write("-- Requires organization.id = 1 (change @org_id if needed).\n")
        fh.write("--\n")
        fh.write("--   mysql -u root -p skac < deploy/mysql/migrate_products.sql\n\n")
        fh.write("USE skac;\nSET NAMES utf8mb4;\nSET @org_id := 1;\n\n")
        write_batches(
            fh,
            "INSERT INTO product (\n"
            "  organization_id, sku, name, category, hsn_code, gst_rate, base_unit,\n"
            "  mrp, purchase_price, sale_price, reorder_level, is_active, is_favorite,\n"
            "  npk_n, npk_p, npk_k, attributes, is_deleted\n"
            ") VALUES",
            values,
        )


def main() -> None:
    customers, cstats = map_customers(CUSTOMERS_CSV)
    products, pstats = map_products(PRODUCTS_CSV)
    cout = OUT / "migrate_customers.sql"
    pout = OUT / "migrate_products.sql"
    write_customers(customers, cout)
    write_products(products, pout)
    print(f"Customers: {cstats['source']} → {len(customers)}  "
          f"(phones cleared {cstats['phone_cleared']}, dup phones nulled {cstats['phone_dup']}, "
          f"aadhaar dropped {cstats['aadhaar_dropped']}, with due {cstats['with_due']})")
    print(f"  wrote {cout} ({cout.stat().st_size:,} bytes)")
    print(f"Products: {len(products)}  categories {pstats}")
    print(f"  wrote {pout} ({pout.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
