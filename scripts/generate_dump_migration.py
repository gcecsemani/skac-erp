#!/usr/bin/env python3
"""Map Dump20260912.sql (old SKAC) into reviewable INSERT scripts for skac_new.

  python3 scripts/generate_dump_migration.py

Writes deploy/mysql/migrate_from_dump/*.sql
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DUMP = ROOT / "Dump20260912.sql"
SCHEMA = ROOT / "deploy" / "mysql" / "schema.sql"
OUT = ROOT / "deploy" / "mysql" / "migrate_from_dump"
DB = "skac_new"
ORG_ID = 1
BATCH = 200

PLACEHOLDER_PHONES = {
    "9999999999", "0000000000", "1234567890", "1111111111", "0", "00",
}
PASSWORD_HASHES = {
    1: "$2b$12$HqMzmebz2dRCJDW8dGGjn.RaVaEEchRUZJqFES6keYll1fLA.HdTO",  # MANI / 131149
    2: "$2b$12$d9hwW7iQjeyRY6BT3aOsQus9Sgr8DAplxCId.iOkBhcT3WFj4uaQ6",  # VADIVEL / 22149
    3: "$2b$12$GQ2AnODnnm4ppiSGDkn8OOsfzcIvBRJmsYbLb3zFksrdEDfZupnQO",  # SARAVANAN / 191181
    4: "$2b$12$SsSNNAAQbdsOjcPsglUr2uneKTZUTvzCKhQAGtIKEzxkqphYwm/mm",  # TVM / 1986
    5: "$2b$12$pG5WiWU1KN60E.D7BUELned/BUv0T.Jzn9NW6vALqkizg8nAHq.1.",  # TEMP1 / 2051316
}
CAT_TO_NEW = {
    1: "pesticide",  # PGR
    2: "fertilizer",
    3: "pesticide",
    4: "seed",
    5: "pesticide",
    6: "pesticide",  # FUNGI
    7: "pesticide",
    8: "fertilizer",  # MICRO
    9: "fertilizer",
    10: "pesticide",  # HERBI
    11: "pesticide",
}
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
STATS: dict[str, int] = defaultdict(int)


def sql_str(value: object | None) -> str:
    if value is None:
        return "NULL"
    text = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{text}'"


def sql_num(value: object) -> str:
    return str(value)


def sql_bool(value: bool) -> str:
    return "1" if value else "0"


def clip(value: object | None, n: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NULL", "NIL", "NILL", "NA", "NL"}:
        return None
    return text[:n]


def money(value: object | None) -> Decimal:
    if value is None or str(value).strip() in ("", "NULL"):
        return Decimal("0.00")
    try:
        return Decimal(str(value).strip()).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def as_int(value: object | None, default: int | None = 0) -> int | None:
    if value is None or str(value).strip() in ("", "NULL"):
        return default
    try:
        return int(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return default


def as_bit(value: object | None) -> bool:
    if value is True or value == 1:
        return True
    if value is False or value is None or value == 0:
        return False
    if isinstance(value, (bytes, bytearray)):
        return any(b not in (0, 48) for b in value)  # not NUL / '0'
    text = str(value)
    if text in {"", "0", "\0", "\\0"}:
        return False
    return any(ch not in {"\0", "0"} for ch in text)


def parse_quoted(s: str, i: int) -> tuple[str, int]:
    quote = s[i]
    i += 1
    out: list[str] = []
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n:
            nxt = s[i + 1]
            out.append({"0": "\0", "n": "\n", "r": "\r", "t": "\t", "Z": "\x1a"}.get(nxt, nxt))
            i += 2
            continue
        if ch == quote:
            if i + 1 < n and s[i + 1] == quote:
                out.append(quote)
                i += 2
                continue
            return "".join(out), i + 1
        out.append(ch)
        i += 1
    return "".join(out), i


def parse_tuples(s: str) -> list[list]:
    rows: list[list] = []
    i = 0
    n = len(s)
    while True:
        while i < n and s[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        if s[i] != "(":
            i += 1
            continue
        i += 1
        row: list = []
        while i < n:
            while i < n and s[i] in " \t\r\n":
                i += 1
            if i < n and s[i] == ")":
                i += 1
                rows.append(row)
                break
            if s.startswith("_binary", i) or s.startswith("_BINARY", i):
                i += 7
                while i < n and s[i] == " ":
                    i += 1
                val, i = parse_quoted(s, i)
                row.append(as_bit(val))
            elif i < n and s[i] in "'\"":
                val, i = parse_quoted(s, i)
                row.append(val)
            elif s.startswith("NULL", i) and (i + 4 >= n or s[i + 4] in ",)"):
                row.append(None)
                i += 4
            else:
                j = i
                while i < n and s[i] not in ",)":
                    i += 1
                row.append(s[j:i].strip())
            while i < n and s[i] in " \t\r\n":
                i += 1
            if i < n and s[i] == ",":
                i += 1
        else:
            break
    return rows


def parse_insert_rows(line: str) -> list[list]:
    idx = line.find("VALUES")
    if idx < 0:
        return []
    body = line[idx + 6 :]
    body = body.strip()
    if body.endswith(";"):
        body = body[:-1]
    return parse_tuples(body)


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
    if not raw:
        return None
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    return digits if len(digits) == 12 else None


def normalize_gstin(raw: object | None) -> str | None:
    text = clip(raw, 20)
    if not text:
        return None
    cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    if len(cleaned) < 10:
        return None
    return cleaned[:20]


def normalize_email(raw: object | None) -> str | None:
    text = clip(raw, 200)
    if not text or "@" not in text or "." not in text.split("@")[-1]:
        return None
    return text.lower()


def dt(raw: object | None, fallback: str | None = None) -> str | None:
    if raw is None:
        return fallback
    text = str(raw).strip().replace("T", " ")
    if not text or text.startswith("0000") or text.startswith("0001"):
        return fallback
    if len(text) >= 19:
        return text[:19]
    if len(text) >= 10:
        return text[:10] + " 00:00:00"
    return fallback


def as_date(raw: object | None, fallback: str | None = None) -> str | None:
    text = dt(raw, fallback)
    return text[:10] if text else fallback


def farmer_name(raw: object | None, cust_id: object) -> str:
    name = clip(raw, 150)
    if not name:
        return f"Legacy farmer {cust_id}"
    if len(name) < 2:
        return f"{name}."
    return name


def digits(value: object | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def infer_category(name: str, hsn: str, cat_id: int | None) -> str:
    n = name.lower()
    if any(w in n for w in SEED_WORDS) or hsn.startswith(("10", "12", "07")):
        if not any(w in n for w in ("insect", "pest", "weed")):
            return "seed"
    if hsn.startswith(("31", "28", "25")):
        return "fertilizer"
    if any(w in n for w in FERT_WORDS) or re.search(r"\d{1,2}\s*:\s*\d{1,2}\s*:\s*\d{1,2}", n):
        return "fertilizer"
    if hsn.startswith("21") and any(w in n for w in ("seed", "bhendi", "gourd", "chilli", "radish")):
        return "seed"
    if hsn.startswith("21"):
        return "fertilizer"
    if hsn.startswith("38"):
        return "pesticide"
    return CAT_TO_NEW.get(cat_id or 0, "pesticide")


def legacy_gst_rate(cgst: object | None, sgst: object | None) -> Decimal:
    """Old item_details stored CGST% and SGST% separately. Combined = gst_rate."""
    total = money(cgst) + money(sgst)
    if total < 0:
        return Decimal("0.00")
    if total > Decimal("99.99"):
        return Decimal("99.99")
    return total.quantize(Decimal("0.01"))


def infer_base_unit(pack: str) -> str:
    """Stock is counted in sale packs (bottles/bags), not SI volume/weight."""
    raw = (pack or "").strip()
    token = raw.upper().replace(" ", "")
    if not token or token in {"UNIT", "UNITS"}:
        return "packet"
    return raw[:20]


def infer_npk(name: str) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    m = re.search(r"(\d{1,2})\s*:\s*(\d{1,2})\s*:\s*(\d{1,2})", name)
    if not m:
        return None, None, None
    return Decimal(m.group(1)), Decimal(m.group(2)), Decimal(m.group(3))


def expense_category(desc: str) -> str:
    n = (desc or "").lower()
    if any(w in n for w in ("rent", "shop rent")):
        return "rent"
    if any(w in n for w in ("salary", "wage", "wages")):
        return "salary"
    if any(w in n for w in ("eb ", "electric", "current bill", "currentbill")):
        return "electricity"
    if any(w in n for w in ("transport", "unloading", "labour", "labor", "lorry", "freight")):
        return "transport"
    if any(w in n for w in ("packing", "carry bag", "loading")):
        return "packing"
    if any(w in n for w in ("petrol", "diesel", "bike", "service", "repair", "maintain")):
        return "maintenance"
    return "other"


def payment_mode_from(text: str | None, balance: Decimal, given: Decimal, grand: Decimal) -> str:
    n = (text or "").lower()
    if any(w in n for w in ("gp", "gpay", "g pay", "upi", "phonepe", "paytm")):
        return "upi"
    if "card" in n:
        return "card"
    if balance > 0 or given + Decimal("0.50") < grand:
        return "credit"
    return "cash"


def vendor_pay_mode(raw: object | None) -> str:
    n = (str(raw or "")).upper()
    if n in {"UPI", "NEFT", "RTGS", "IMPS", "GPAY", "GP"}:
        return "upi"
    if "CARD" in n:
        return "card"
    return "cash"


def valid_user(uid: object | None) -> int | None:
    n = as_int(uid, None)
    return n if n in PASSWORD_HASHES else None


def valid_branch(bid: object | None) -> int | None:
    n = as_int(bid, None)
    return n if n in (1, 2) else None


class SqlFile:
    def __init__(self, path: Path, title: str, extra_header: str = "") -> None:
        self.path = path
        self.fh = path.open("w", encoding="utf-8")
        self.fh.write(f"-- {title}\n")
        self.fh.write(f"-- Source: {DUMP.name}  →  database {DB}\n")
        if extra_header:
            self.fh.write(extra_header.rstrip() + "\n")
        self.fh.write(f"\nUSE {DB};\nSET NAMES utf8mb4;\n")
        self.fh.write("SET FOREIGN_KEY_CHECKS = 0;\nSET UNIQUE_CHECKS = 0;\n\n")
        self.rows = 0

    def write_batches(self, header: str, values: list[str], batch: int = BATCH) -> None:
        for i in range(0, len(values), batch):
            chunk = values[i : i + batch]
            self.fh.write(header + "\n")
            self.fh.write(",\n".join(chunk))
            self.fh.write(";\n\n")
            self.rows += len(chunk)

    def auto_inc(self, table: str, max_id: int | None) -> None:
        if max_id and max_id > 0:
            self.fh.write(f"ALTER TABLE `{table}` AUTO_INCREMENT = {max_id + 1};\n\n")

    def close(self) -> None:
        self.fh.write("SET UNIQUE_CHECKS = 1;\nSET FOREIGN_KEY_CHECKS = 1;\n")
        self.fh.close()


def iter_dump_inserts(wanted: set[str]):
    with DUMP.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.startswith("INSERT INTO"):
                continue
            table = line.split("`")[1]
            if table in wanted:
                yield table, line


def write_schema() -> None:
    text = SCHEMA.read_text(encoding="utf-8")
    text = text.replace("CREATE DATABASE IF NOT EXISTS skac\n", f"CREATE DATABASE IF NOT EXISTS {DB}\n")
    text = text.replace("USE skac;", f"USE {DB};")
    (OUT / "00_schema.sql").write_text(text, encoding="utf-8")


def write_org() -> None:
    f = SqlFile(OUT / "01_organization.sql", "Organization (single tenant)")
    f.write_batches(
        "INSERT INTO organization (id, name, legal_name, is_deleted) VALUES",
        ["  (1, 'Sri Kumaran Agri Clinic', 'SKAC', 0)"],
        batch=1,
    )
    f.auto_inc("organization", 1)
    f.close()


def write_branches(rows: list[list]) -> None:
    f = SqlFile(OUT / "02_branch.sql", "Branches")
    values = []
    for r in rows:
        bid = as_int(r[0])
        code = clip(r[1], 20) or f"B{bid}"
        name = clip(r[2], 200) or code
        printer = clip(r[4], 120)
        ptype = "laser" if printer and "samsung" in printer.lower() else "thermal"
        values.append(
            "  ("
            + ", ".join(
                [
                    sql_num(bid),
                    sql_num(ORG_ID),
                    sql_str(code),
                    sql_str(name),
                    sql_str(name.title()),
                    sql_str("Tiruvannamalai"),
                    sql_str("Tamil Nadu"),
                    sql_str("33"),
                    sql_str(printer),
                    sql_str(ptype),
                    "80",
                    "0",
                ]
            )
            + ")"
        )
    f.write_batches(
        "INSERT INTO branch (\n"
        "  id, organization_id, code, name, city, district, state, state_code,\n"
        "  printer_name, printer_type, thermal_paper_mm, is_deleted\n"
        ") VALUES",
        values,
    )
    f.auto_inc("branch", max(as_int(r[0]) for r in rows))
    f.close()
    STATS["branch"] = len(values)


def write_users(users: list[list], maps: list[list]) -> None:
    f = SqlFile(
        OUT / "03_user.sql",
        "Users (legacy plaintext passwords hashed with bcrypt)",
        extra_header=(
            "-- Login emails: {username}@skac.local  (MANI, VADIVEL, SARAVANAN, TVM, TEMP1)\n"
            "-- Passwords unchanged from the old system.\n"
            "-- Group ADMIN → role_id 1 (owner), EXECUTIVE → role_id 2 (cashier).\n"
        ),
    )
    values = []
    for r in users:
        uid = as_int(r[0])
        name = clip(r[1], 150) or f"User {uid}"
        group_id = as_int(r[3], 2)
        role_id = 1 if group_id == 1 else 2
        email = f"{name.lower()}@skac.local"
        hashed = PASSWORD_HASHES.get(uid)
        if not hashed:
            continue
        values.append(
            "  ("
            + ", ".join(
                [
                    sql_num(uid),
                    sql_num(ORG_ID),
                    sql_num(role_id),
                    sql_str(name.title()),
                    sql_str(email),
                    sql_str(hashed),
                    "1",
                    "0",
                ]
            )
            + ")"
        )
    f.write_batches(
        "INSERT INTO `user` (\n"
        "  id, organization_id, role_id, full_name, email, hashed_password,\n"
        "  is_active, is_deleted\n"
        ") VALUES",
        values,
    )
    f.auto_inc("user", max(as_int(r[0]) for r in users))
    f.close()

    ub = SqlFile(OUT / "04_user_branch.sql", "User ↔ branch assignments")
    ub_vals = []
    seen = set()
    for r in maps:
        bid = valid_branch(r[1])
        uid = valid_user(r[2])
        if not bid or not uid or (uid, bid) in seen:
            continue
        seen.add((uid, bid))
        ub_vals.append(f"  ({uid}, {bid})")
    ub.write_batches("INSERT INTO user_branch (user_id, branch_id) VALUES", ub_vals)
    ub.close()
    STATS["user"] = len(values)
    STATS["user_branch"] = len(ub_vals)


def write_accounts() -> None:
    accounts = [
        ("1000", "Cash", "asset"),
        ("1010", "Bank", "asset"),
        ("1200", "Accounts Receivable (Debtors)", "asset"),
        ("1300", "Inventory", "asset"),
        ("1310", "GST Input Credit", "asset"),
        ("2000", "Accounts Payable (Creditors)", "liability"),
        ("2100", "GST Payable", "liability"),
        ("3000", "Sales", "income"),
        ("4000", "Purchases / COGS", "expense"),
        ("4100", "Transport Charges", "expense"),
        ("4200", "Salaries & Wages", "expense"),
        ("4300", "Rent", "expense"),
        ("4400", "Electricity & Utilities", "expense"),
        ("4500", "Other Operating Expenses", "expense"),
        ("5000", "Owner Capital", "equity"),
    ]
    f = SqlFile(OUT / "05_ledger_account.sql", "Chart of accounts")
    vals = []
    for i, (code, name, typ) in enumerate(accounts, 1):
        vals.append(
            f"  ({i}, {ORG_ID}, {sql_str(code)}, {sql_str(name)}, {sql_str(typ)}, 1)"
        )
    f.write_batches(
        "INSERT INTO ledger_account (id, organization_id, code, name, type, is_system) VALUES",
        vals,
    )
    f.auto_inc("ledger_account", len(accounts))
    f.close()
    STATS["ledger_account"] = len(vals)


def write_vendors(rows: list[list], ledger: list[list]) -> None:
    last_bal: dict[int, Decimal] = {}
    for r in ledger:
        sid = as_int(r[2])
        last_bal[sid] = money(r[7])
    f = SqlFile(OUT / "06_vendor.sql", "Vendors (old suppliers)")
    vals = []
    max_id = 0
    for r in rows:
        sid = as_int(r[0])
        max_id = max(max_id, sid)
        name = clip(r[1], 200) or f"Vendor {sid}"
        addr = clip(r[2], 400)
        gstin = normalize_gstin(r[3])
        phone = clip(r[4], 20)
        if phone and (phone in {"00", "0", "0000"} or not any(c.isdigit() for c in phone)):
            phone = None
        email = normalize_email(r[5])
        deleted = as_bit(r[6])
        vals.append(
            "  ("
            + ", ".join(
                [
                    sql_num(sid),
                    sql_num(ORG_ID),
                    sql_str(name),
                    sql_str(gstin),
                    sql_str(phone),
                    sql_str(email),
                    sql_str(addr),
                    sql_num(last_bal.get(sid, Decimal("0.00"))),
                    sql_bool(deleted),
                ]
            )
            + ")"
        )
    f.write_batches(
        "INSERT INTO vendor (\n"
        "  id, organization_id, name, gstin, phone, email, address,\n"
        "  outstanding_balance, is_deleted\n"
        ") VALUES",
        vals,
    )
    f.auto_inc("vendor", max_id)
    f.close()
    STATS["vendor"] = len(vals)


def write_customers(rows: list[list]) -> None:
    staged = []
    for r in rows:
        cid = as_int(r[0])
        phone = normalize_phone(r[3])
        if r[3] and not phone:
            STATS["customer_phone_cleared"] += 1
        aadhaar = normalize_aadhaar(r[12])
        due = money(r[4])
        staged.append(
            {
                "id": cid,
                "name": farmer_name(r[1], cid),
                "phone": phone,
                "village": clip(r[2], 120),
                "aadhaar": aadhaar,
                "due": due,
                "deleted": as_bit(r[10]),
                "created": dt(r[7], "2017-09-01 00:00:00"),
                "updated": dt(r[9]) or dt(r[7], "2017-09-01 00:00:00"),
            }
        )
        if due > 0:
            STATS["customer_with_due"] += 1
    by_phone: dict[str, list] = defaultdict(list)
    for item in staged:
        if item["phone"]:
            by_phone[item["phone"]].append(item)
    for items in by_phone.values():
        if len(items) < 2:
            continue
        winner = max(items, key=lambda x: (x["due"], x["id"]))
        for item in items:
            if item is not winner:
                item["phone"] = None
                STATS["customer_phone_dup"] += 1
    staged.sort(key=lambda x: x["id"])
    f = SqlFile(
        OUT / "07_customer.sql",
        "Farmers / customers",
        extra_header="-- Duplicate / placeholder phones stored as NULL (unique org+phone).\n",
    )
    vals = []
    for r in staged:
        credit = r["due"] > 0 or True
        vals.append(
            "  ("
            + ", ".join(
                [
                    sql_num(r["id"]),
                    sql_num(ORG_ID),
                    sql_str(r["name"]),
                    sql_str(r["phone"]),
                    sql_str(r["aadhaar"]),
                    sql_str(r["village"]),
                    sql_str("Tiruvannamalai"),
                    "1",
                    "10000.00",
                    sql_num(r["due"]),
                    sql_bool(r["deleted"]),
                    sql_str(r["created"]),
                    sql_str(r["updated"]),
                ]
            )
            + ")"
        )
    f.write_batches(
        "INSERT INTO customer (\n"
        "  id, organization_id, name, phone, aadhaar_no, village, district,\n"
        "  credit_allowed, credit_limit, outstanding_balance, is_deleted,\n"
        "  created_at, updated_at\n"
        ") VALUES",
        vals,
    )
    f.auto_inc("customer", max(r["id"] for r in staged) if staged else 0)
    f.close()
    STATS["customer"] = len(vals)
    return {r["id"] for r in staged}


def write_products(details: list[list], prices: list[list]) -> dict[int, dict]:
    items = {}
    for r in details:
        iid = as_int(r[0])
        items[iid] = {
            "name": clip(r[1], 180) or f"Item {iid}",
            "hsn": digits(r[4]),
            "cat": as_int(r[5], 11),
            "cgst": r[2],
            "sgst": r[3],
            "deleted": as_bit(r[12]),
            "favor": as_bit(r[13]),
        }
    products: dict[int, dict] = {}
    vals = []
    unit_vals = []
    for r in prices:
        pid = as_int(r[0])
        iid = as_int(r[1])
        pack = clip(r[2], 20) or "UNIT"
        item = items.get(
            iid,
            {"name": f"Item {iid}", "hsn": "", "cat": 11, "cgst": 0, "sgst": 0, "deleted": False, "favor": False},
        )
        hsn_raw = item["hsn"]
        hsn = hsn_raw if hsn_raw and hsn_raw != "0" else None
        if hsn and len(hsn) > 12:
            hsn = hsn[:12]
        name = f"{item['name']} - {pack}"[:200]
        category = infer_category(name, hsn or "", item["cat"])
        gst_rate = legacy_gst_rate(item.get("cgst"), item.get("sgst"))
        if gst_rate > 0:
            STATS["product_gst_nonzero"] += 1
        mrp = money(r[3])
        purchase = money(r[4])
        sale = money(r[5])
        if mrp == 0 and sale > 0:
            mrp = sale
        n, p, k = infer_npk(name)
        barcode = clip(r[7], 64)
        deleted = as_bit(r[8]) or item["deleted"]
        extra = json.dumps({"legacy_item_id": iid, "legacy_price_id": pid, "packing": pack}, separators=(",", ":"))
        base_unit = infer_base_unit(pack)
        products[pid] = {
            "name": name,
            "hsn": hsn,
            "unit": clip(pack, 20) or "unit",
            "base_unit": base_unit,
            "gst": gst_rate,
            "stock": as_int(r[6], 0) or 0,
            "purchase": purchase,
        }
        vals.append(
            "  ("
            + ", ".join(
                [
                    sql_num(pid),
                    sql_num(ORG_ID),
                    sql_str(f"P{pid}"),
                    sql_str(barcode),
                    sql_str(name),
                    sql_str(category),
                    sql_str(hsn),
                    sql_num(gst_rate),
                    sql_str(base_unit),
                    sql_num(mrp),
                    sql_num(purchase),
                    sql_num(sale),
                    "0",
                    sql_bool(not deleted),
                    sql_bool(item["favor"]),
                    sql_num(n) if n is not None else "NULL",
                    sql_num(p) if p is not None else "NULL",
                    sql_num(k) if k is not None else "NULL",
                    sql_str(extra),
                    sql_bool(deleted),
                ]
            )
            + ")"
        )
        unit_vals.append(f"  ({pid}, {sql_str(clip(pack, 20) or 'unit')}, 1.0000)")
    f = SqlFile(
        OUT / "08_product.sql",
        "Products (one row per old packing / item_price.PriceId)",
        extra_header=(
            "-- product.id = old item_price.PriceId so sales/purchase lines keep the same FK.\n"
            "-- SKU is P{price_id}. Packing and old ids are in attributes JSON.\n"
            "-- gst_rate = old item_details.Cgst + Sgst (almost all 0 in the legacy DB).\n"
        ),
    )
    f.write_batches(
        "INSERT INTO product (\n"
        "  id, organization_id, sku, barcode, name, category, hsn_code, gst_rate, base_unit,\n"
        "  mrp, purchase_price, sale_price, reorder_level, is_active, is_favorite,\n"
        "  npk_n, npk_p, npk_k, attributes, is_deleted\n"
        ") VALUES",
        vals,
    )
    f.auto_inc("product", max(products) if products else 0)
    f.close()
    u = SqlFile(OUT / "09_product_unit.sql", "Packing units (factor 1 to base)")
    u.write_batches("INSERT INTO product_unit (product_id, unit, factor_to_base) VALUES", unit_vals)
    u.auto_inc("product_unit", len(unit_vals))
    u.close()
    STATS["product"] = len(vals)
    return products


def write_batch_stock(products: dict[int, dict], invoice_child: list[list]) -> dict[tuple[int, str], int]:
    """Create GRN batches plus one LEGACY-OPENING batch per product for on-hand qty."""
    keys: dict[tuple[int, str], dict] = {}
    next_id = 1

    def add(pid: int, batch_no: str, expiry: str | None, price: Decimal) -> None:
        nonlocal next_id
        key = (pid, batch_no)
        if key in keys:
            return
        keys[key] = {"id": next_id, "expiry": expiry, "price": price}
        next_id += 1

    for r in invoice_child:
        pid = as_int(r[3])
        if pid not in products:
            continue
        bno = clip(r[4], 80) or "UNKNOWN"
        add(pid, bno, as_date(r[5]), money(r[7]))
    for pid, meta in products.items():
        add(pid, "LEGACY-OPENING", None, meta["purchase"])

    f = SqlFile(
        OUT / "10_batch.sql",
        "Batches from purchase lots + LEGACY-OPENING for current stock",
    )
    bvals = []
    for (pid, bno), meta in keys.items():
        bvals.append(
            "  ("
            + ", ".join(
                [
                    sql_num(meta["id"]),
                    sql_num(ORG_ID),
                    sql_num(pid),
                    sql_str(bno),
                    sql_str(meta["expiry"]),
                    sql_num(meta["price"]),
                ]
            )
            + ")"
        )
    f.write_batches(
        "INSERT INTO batch (id, organization_id, product_id, batch_no, expiry_date, purchase_price) VALUES",
        bvals,
    )
    f.auto_inc("batch", next_id - 1)
    f.close()

    s = SqlFile(
        OUT / "11_stock.sql",
        "Opening stock snapshot (old item_price.Stock is not per-branch)",
        extra_header="-- Entire on-hand quantity is placed on branch 1 (AVL). Review before go-live.\n",
    )
    svals = []
    sid = 1
    for pid, meta in products.items():
        bid = keys[(pid, "LEGACY-OPENING")]["id"]
        svals.append(
            f"  ({sid}, {ORG_ID}, 1, {pid}, {bid}, {sql_num(Decimal(meta['stock']))})"
        )
        sid += 1
    s.write_batches(
        "INSERT INTO stock (id, organization_id, branch_id, product_id, batch_id, quantity) VALUES",
        svals,
    )
    s.auto_inc("stock", sid - 1)
    s.close()
    STATS["batch"] = len(bvals)
    STATS["stock"] = len(svals)
    return {(pid, bno): meta["id"] for (pid, bno), meta in keys.items()}


def write_expenses(rows: list[list]) -> None:
    f = SqlFile(
        OUT / "12_expense.sql",
        "Expenses",
        extra_header="-- Category inferred from description (rent/transport/salary/…). Mode = cash.\n",
    )
    vals = []
    max_id = 0
    for r in rows:
        eid = as_int(r[0])
        max_id = max(max_id, eid)
        desc = clip(r[1], 255) or "Expense"
        amt = money(r[2])
        edate = as_date(r[3], "2017-09-01")
        branch = valid_branch(r[4]) or 1
        user = valid_user(r[5])
        created = dt(r[6], edate + " 00:00:00")
        if as_bit(r[7]):
            STATS["expense_deleted_skipped"] += 1
            continue
        vals.append(
            "  ("
            + ", ".join(
                [
                    sql_num(eid),
                    sql_num(ORG_ID),
                    sql_num(branch),
                    sql_num(user) if user else "NULL",
                    sql_str(edate),
                    sql_str(expense_category(desc)),
                    "NULL",
                    sql_num(amt),
                    sql_str("cash"),
                    sql_str(desc),
                    sql_str(created),
                    sql_str(created),
                ]
            )
            + ")"
        )
    f.write_batches(
        "INSERT INTO expense (\n"
        "  id, organization_id, branch_id, created_by_user_id, expense_date,\n"
        "  category, payee, amount, mode, note, created_at, updated_at\n"
        ") VALUES",
        vals,
    )
    f.auto_inc("expense", max_id)
    f.close()
    STATS["expense"] = len(vals)


def write_day_close(rows: list[list]) -> None:
    """Keep the last cashout per (branch, date) because day_close is unique on that pair."""
    latest: dict[tuple[int, str], list] = {}
    for r in rows:
        if as_bit(r[25]):
            continue
        branch = valid_branch(r[23])
        if not branch:
            continue
        d = as_date(r[1])
        if not d:
            continue
        latest[(branch, d)] = r
    f = SqlFile(
        OUT / "13_day_close.sql",
        "Day close (from cashout)",
        extra_header="-- Old system allowed many cashouts per day; only the last SeqNo per branch+date is kept.\n",
    )
    vals = []
    max_id = 0
    for r in latest.values():
        sid = as_int(r[0])
        max_id = max(max_id, sid)
        billed = money(r[3])
        settled = money(r[4])
        credit = money(r[5])
        expenses = money(r[7])
        prev = money(r[8])
        counted = money(r[9])
        expected = prev + settled - expenses
        closed_at = dt(r[1], "2017-09-01 00:00:00")
        d = as_date(r[1], "2017-09-01")
        branch = valid_branch(r[23]) or 1
        user = valid_user(r[24])
        denoms = {
            "2000": as_int(r[12], 0),
            "1000": as_int(r[13], 0),
            "500": as_int(r[14], 0),
            "200": as_int(r[15], 0),
            "100": as_int(r[16], 0),
            "50": as_int(r[17], 0),
            "20": as_int(r[18], 0),
            "10": as_int(r[19], 0),
            "5": as_int(r[20], 0),
            "2": as_int(r[21], 0),
            "1": as_int(r[22], 0),
        }
        vals.append(
            "  ("
            + ", ".join(
                [
                    sql_num(sid),
                    sql_num(ORG_ID),
                    sql_num(branch),
                    sql_num(user) if user else "NULL",
                    sql_str(d),
                    sql_str(closed_at),
                    sql_num(prev),
                    sql_num(settled),
                    sql_num(expenses),
                    sql_num(expected),
                    sql_num(counted),
                    sql_num(counted - expected),
                    sql_num(billed),
                    sql_num(settled),
                    sql_num(credit),
                    sql_num(expenses),
                    sql_str(clip(r[11], 255)),
                    sql_str(json.dumps(denoms, separators=(",", ":"))),
                ]
            )
            + ")"
        )
    f.write_batches(
        "INSERT INTO day_close (\n"
        "  id, organization_id, branch_id, closed_by_user_id, close_date, closed_at,\n"
        "  opening_cash, cash_in, cash_out, expected_cash, counted_cash, cash_variance,\n"
        "  sales_total, collected_total, khata_new, expense_total, note, breakdown\n"
        ") VALUES",
        vals,
    )
    f.auto_inc("day_close", max_id)
    f.close()
    STATS["day_close"] = len(vals)
    STATS["cashout_source"] = len(rows)


def write_grn(masters: list[list], children: list[list], products: dict[int, dict],
              batch_ids: dict[tuple[int, str], int], vendor_ids: set[int]) -> None:
    f = SqlFile(
        OUT / "14_grn.sql",
        "Goods receipts (old invoice_master)",
        extra_header="-- grn.id = old InvoiceId. vendor_invoice_no = old InvoiceNo.\n",
    )
    vals = []
    kept = set()
    max_id = 0
    for r in masters:
        gid = as_int(r[0])
        vid = as_int(r[2])
        if vid not in vendor_ids:
            STATS["grn_skipped_vendor"] += 1
            continue
        if as_bit(r[9]):
            STATS["grn_deleted_skipped"] += 1
            continue
        branch = valid_branch(r[8]) or 1
        user = valid_user(r[10])
        received = as_date(r[3], "2017-09-01")
        entered = dt(r[11], received + " 00:00:00")
        max_id = max(max_id, gid)
        kept.add(gid)
        vals.append(
            "  ("
            + ", ".join(
                [
                    sql_num(gid),
                    sql_num(ORG_ID),
                    sql_num(branch),
                    sql_num(vid),
                    sql_num(user) if user else "NULL",
                    sql_str(f"GRN-{gid}"[:40]),
                    sql_str(received),
                    sql_str(clip(r[1], 60)),
                    sql_num(money(r[6])),
                    sql_str(entered),
                    sql_str(entered),
                ]
            )
            + ")"
        )
    f.write_batches(
        "INSERT INTO grn (\n"
        "  id, organization_id, branch_id, vendor_id, created_by_user_id,\n"
        "  grn_no, received_date, vendor_invoice_no, total_value, created_at, updated_at\n"
        ") VALUES",
        vals,
    )
    f.auto_inc("grn", max_id)
    f.close()

    g = SqlFile(OUT / "15_grn_item.sql", "GRN lines (old invoice_child)")
    ivals = []
    max_seq = 0
    for r in children:
        seq = as_int(r[0])
        gid = as_int(r[1])
        pid = as_int(r[3])
        if gid not in kept:
            continue
        if pid not in products:
            STATS["grn_item_skipped_product"] += 1
            continue
        if as_bit(r[10]):
            continue
        bno = clip(r[4], 80) or "UNKNOWN"
        bid = batch_ids.get((pid, bno))
        max_seq = max(max_seq, seq)
        ivals.append(
            "  ("
            + ", ".join(
                [
                    sql_num(seq),
                    sql_num(gid),
                    sql_num(pid),
                    sql_num(bid) if bid else "NULL",
                    sql_str(bno),
                    sql_str(as_date(r[5])),
                    sql_num(as_int(r[6], 0)),
                    sql_num(money(r[7])),
                ]
            )
            + ")"
        )
    g.write_batches(
        "INSERT INTO grn_item (\n"
        "  id, grn_id, product_id, batch_id, batch_no, expiry_date, quantity, unit_price\n"
        ") VALUES",
        ivals,
    )
    g.auto_inc("grn_item", max_seq)
    g.close()
    STATS["grn"] = len(vals)
    STATS["grn_item"] = len(ivals)


def write_invoices(customer_ids: set[int], products: dict[int, dict]) -> dict[str, int]:
    """Assign sequential invoice.id; keep old OrderId in invoice_no."""
    f = SqlFile(
        OUT / "16_invoice.sql",
        "Sales invoices (old order_master)",
        extra_header=(
            "-- invoice.id is new sequential. invoice_no is the old OrderId (AVL123 / TVM456).\n"
            "-- status: cancelled if old IsDeleted, else finalized.\n"
            "-- payment_mode: upi from remarks (GP/GPAY), else credit if balance due, else cash.\n"
        ),
    )
    header = (
        "INSERT INTO invoice (\n"
        "  id, organization_id, branch_id, customer_id, created_by_user_id,\n"
        "  invoice_no, invoice_date, status, tax_type, payment_mode,\n"
        "  subtotal, discount_total, tax_total, grand_total, amount_paid,\n"
        "  finalized_at, created_at, updated_at\n"
        ") VALUES"
    )
    order_map: dict[str, int] = {}
    buf: list[str] = []
    new_id = 0
    wanted = {"order_master"}
    for _, line in iter_dump_inserts(wanted):
        for r in parse_insert_rows(line):
            order_id = str(r[0])
            branch = valid_branch(r[2])
            if not branch:
                STATS["invoice_skipped_branch"] += 1
                continue
            cust = as_int(r[1], None)
            if cust not in customer_ids:
                cust = None
                STATS["invoice_customer_nulled"] += 1
            user = valid_user(r[12])
            deleted = as_bit(r[13])
            when = dt(r[3], "2017-09-01 00:00:00")
            idate = (when or "2017-09-01 00:00:00")[:10]
            sub = money(r[4])
            tax = money(r[5]) + money(r[6])
            disc = money(r[8])
            grand = money(r[9])
            given = money(r[10])
            bal = money(r[11])
            remarks = clip(r[14], 255)
            new_id += 1
            order_map[order_id] = new_id
            buf.append(
                "  ("
                + ", ".join(
                    [
                        sql_num(new_id),
                        sql_num(ORG_ID),
                        sql_num(branch),
                        sql_num(cust) if cust else "NULL",
                        sql_num(user) if user else "NULL",
                        sql_str(clip(order_id, 40)),
                        sql_str(idate),
                        sql_str("cancelled" if deleted else "finalized"),
                        sql_str("intra"),
                        sql_str(payment_mode_from(remarks, bal, given, grand)),
                        sql_num(sub),
                        sql_num(disc),
                        sql_num(tax),
                        sql_num(grand),
                        sql_num(given),
                        sql_str(when),
                        sql_str(when),
                        sql_str(when),
                    ]
                )
                + ")"
            )
            if len(buf) >= BATCH:
                f.write_batches(header, buf)
                buf = []
                if new_id % 50000 == 0:
                    print(f"  invoices {new_id:,}", flush=True)
    if buf:
        f.write_batches(header, buf)
    f.auto_inc("invoice", new_id)
    f.close()
    STATS["invoice"] = new_id
    print(f"  invoices done {new_id:,}", flush=True)

    items = SqlFile(
        OUT / "17_invoice_item.sql",
        "Sales invoice lines (old order_child)",
        extra_header="-- invoice_id is the new sequential id from 16_invoice.sql. product_id = old PriceId.\n",
    )
    iheader = (
        "INSERT INTO invoice_item (\n"
        "  id, invoice_id, product_id, product_name, hsn_code, batch_no,\n"
        "  unit, quantity, unit_price, discount, gst_rate,\n"
        "  taxable_value, tax_amount, line_total\n"
        ") VALUES"
    )
    ibuf: list[str] = []
    seq_out = 0
    for _, line in iter_dump_inserts({"order_child"}):
        for r in parse_insert_rows(line):
            oid = str(r[1])
            inv_id = order_map.get(oid)
            if not inv_id:
                STATS["invoice_item_skipped_header"] += 1
                continue
            pid = as_int(r[2])
            prod = products.get(pid)
            if not prod:
                STATS["invoice_item_skipped_product"] += 1
                continue
            qty = Decimal(as_int(r[5], 0) or 0)
            price = money(r[4])
            tax_amt = money(r[6]) + money(r[7])
            total = money(r[8])
            taxable = (price * qty).quantize(Decimal("0.01"))
            if taxable > 0 and tax_amt > 0:
                gst_rate = (tax_amt / taxable * Decimal("100")).quantize(Decimal("0.01"))
            else:
                gst_rate = Decimal("0.00")
            seq_out += 1
            ibuf.append(
                "  ("
                + ", ".join(
                    [
                        sql_num(seq_out),
                        sql_num(inv_id),
                        sql_num(pid),
                        sql_str(prod["name"]),
                        sql_str(prod["hsn"]),
                        sql_str(clip(r[9], 80)),
                        sql_str(prod["unit"]),
                        sql_num(qty),
                        sql_num(price),
                        "0.00",
                        sql_num(gst_rate),
                        sql_num(taxable),
                        sql_num(tax_amt),
                        sql_num(total),
                    ]
                )
                + ")"
            )
            if len(ibuf) >= BATCH:
                items.write_batches(iheader, ibuf)
                ibuf = []
                if seq_out % 100000 == 0:
                    print(f"  invoice items {seq_out:,}", flush=True)
    if ibuf:
        items.write_batches(iheader, ibuf)
    items.auto_inc("invoice_item", seq_out)
    items.close()
    STATS["invoice_item"] = seq_out
    print(f"  invoice items done {seq_out:,}", flush=True)
    return order_map


def write_customer_payments(rows: list[list], customer_ids: set[int]) -> None:
    """Derive payment amounts from successive remaining-balance snapshots per bill."""
    grouped: dict[tuple[int, str], list] = defaultdict(list)
    for r in rows:
        cid = as_int(r[1])
        oid = str(r[2] or "")
        grouped[(cid, oid)].append(r)
    f = SqlFile(
        OUT / "18_customer_payment.sql",
        "Customer collections (derived from customer_ledger)",
        extra_header=(
            "-- Old ledger stored bill total (Given) + remaining (Balance).\n"
            "-- Payment = drop in remaining balance on that bill. Zero/negative skipped.\n"
        ),
    )
    vals = []
    pid = 0
    for (cid, oid), entries in grouped.items():
        if cid not in customer_ids:
            continue
        entries.sort(key=lambda x: as_int(x[0]))
        prev_rem: Decimal | None = None
        billed_first: Decimal | None = None
        for r in entries:
            billed = money(r[3])
            remaining = money(r[4])
            when = dt(r[7], "2017-09-01 00:00:00")
            user = valid_user(r[6])
            if billed_first is None:
                billed_first = billed
                paid = billed - remaining
            else:
                paid = prev_rem - remaining  # type: ignore[operator]
            prev_rem = remaining
            if paid <= 0:
                continue
            note = clip(f"{clip(r[5], 80) or 'Settlement'} {oid}".strip(), 255)
            pid += 1
            vals.append(
                "  ("
                + ", ".join(
                    [
                        sql_num(pid),
                        sql_num(ORG_ID),
                        "NULL",
                        sql_num(cid),
                        sql_str(when),
                        sql_num(paid),
                        sql_str("cash"),
                        sql_str(note),
                    ]
                )
                + ")"
            )
    f.write_batches(
        "INSERT INTO customer_payment (\n"
        "  id, organization_id, branch_id, customer_id, paid_at, amount, mode, note\n"
        ") VALUES",
        vals,
    )
    f.auto_inc("customer_payment", pid)
    f.close()
    STATS["customer_payment"] = len(vals)


def write_vendor_payments(rows: list[list], vendor_ids: set[int]) -> None:
    f = SqlFile(
        OUT / "19_vendor_payment.sql",
        "Vendor payments (supplier_ledger TxnType = D)",
        extra_header="-- Credit (C) rows are invoice postings, not payments, and are skipped.\n",
    )
    vals = []
    max_id = 0
    for r in rows:
        txn = str(r[4] or "").upper()
        if txn != "D":
            continue
        vid = as_int(r[2])
        if vid not in vendor_ids:
            continue
        amt = money(r[6])
        if amt <= 0:
            continue
        when = dt(r[9], "2017-09-01 00:00:00")
        lid = as_int(r[0])
        max_id = max(max_id, lid)
        vals.append(
            "  ("
            + ", ".join(
                [
                    sql_num(lid),
                    sql_num(ORG_ID),
                    "NULL",
                    sql_num(vid),
                    sql_str(when),
                    sql_num(amt),
                    sql_str(vendor_pay_mode(r[3])),
                    sql_str(clip(r[10], 255)),
                ]
            )
            + ")"
        )
    f.write_batches(
        "INSERT INTO vendor_payment (\n"
        "  id, organization_id, branch_id, vendor_id, paid_at, amount, mode, note\n"
        ") VALUES",
        vals,
    )
    f.auto_inc("vendor_payment", max_id)
    f.close()
    STATS["vendor_payment"] = len(vals)


def write_readme() -> None:
    lines = [
        f"-- Migration pack for {DB} from {DUMP.name}",
        "--",
        "-- 1. Review each numbered file (mapping notes are in the header).",
        "-- 2. Run in this order (from repo root):",
        "--",
        f"--   mysql -u root -p < deploy/mysql/migrate_from_dump/00_schema.sql",
    ]
    files = sorted(p.name for p in OUT.glob("*.sql") if p.name != "00_schema.sql" and p.name != "README.sql")
    for name in files:
        lines.append(f"--   mysql -u root -p {DB} < deploy/mysql/migrate_from_dump/{name}")
    lines += [
        "--",
        "-- Or:  sh deploy/mysql/migrate_from_dump/run.sh",
        "--",
        "-- Row counts written by the generator:",
    ]
    for k in sorted(STATS):
        lines.append(f"--   {k}: {STATS[k]}")
    lines += [
        "--",
        "-- Review before go-live:",
        "--   * Stock is all on branch 1 (old system had no per-branch stock).",
        "--   * Duplicate phones were nulled.",
        "--   * Day-close keeps only the last cashout per branch+date.",
        "--   * Invoice numbers are the old AVL/TVM ids; invoice.id is new.",
        "--   * Users log in as {username}@skac.local with the old passwords.",
        "--",
    ]
    (OUT / "README.sql").write_text("\n".join(lines) + "\n", encoding="utf-8")
    scripts = [
        "#!/bin/sh",
        "set -e",
        'ROOT="$(cd "$(dirname "$0")" && pwd)"',
        'echo "Creating schema on skac_new..."',
        'mysql -u root -p < "$ROOT/00_schema.sql"',
    ]
    for name in files:
        scripts.append(f'echo "Loading {name}..."')
        scripts.append(f'mysql -u root -p {DB} < "$ROOT/{name}"')
    scripts.append('echo "Done."')
    run = OUT / "run.sh"
    run.write_text("\n".join(scripts) + "\n", encoding="utf-8")
    run.chmod(0o755)


def main() -> None:
    if not DUMP.exists():
        raise SystemExit(f"Dump not found: {DUMP}")
    OUT.mkdir(parents=True, exist_ok=True)
    print("Writing schema…")
    write_schema()
    print("Parsing dump (small + medium tables)…")
    buckets: dict[str, list[list]] = defaultdict(list)
    first = {
        "branches", "users", "users_map_branches", "suppliers", "supplier_ledger",
        "customers", "item_details", "item_price", "expenses", "cashout",
        "invoice_master", "invoice_child", "customer_ledger",
    }
    for table, line in iter_dump_inserts(first):
        buckets[table].extend(parse_insert_rows(line))
        print(f"  {table}: {len(buckets[table]):,} rows", flush=True)

    write_org()
    write_branches(buckets["branches"])
    write_users(buckets["users"], buckets["users_map_branches"])
    write_accounts()
    vendor_ids = {as_int(r[0]) for r in buckets["suppliers"]}
    write_vendors(buckets["suppliers"], buckets["supplier_ledger"])
    customer_ids = write_customers(buckets["customers"])
    products = write_products(buckets["item_details"], buckets["item_price"])
    batch_ids = write_batch_stock(products, buckets["invoice_child"])
    write_expenses(buckets["expenses"])
    write_day_close(buckets["cashout"])
    write_grn(buckets["invoice_master"], buckets["invoice_child"], products, batch_ids, vendor_ids)
    write_customer_payments(buckets["customer_ledger"], customer_ids)
    write_vendor_payments(buckets["supplier_ledger"], vendor_ids)
    del buckets
    print("Parsing sales (order_master / order_child)…")
    write_invoices(customer_ids, products)
    write_readme()
    print(f"Wrote {OUT}")
    for k, v in sorted(STATS.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
