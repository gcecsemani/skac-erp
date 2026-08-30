#!/usr/bin/env python3
"""Import farmers from the old SKAC MySQL dump into the new ERP `customer` table.

Does not change application code or schema. Maps:

  old dump                  new `customer`
  ------------------------  --------------------------------
  custname                  name
  custcity                  village
  custphone                 phone  (placeholder / invalid / duplicate → NULL)
  dueamount                 outstanding_balance
                            credit_allowed = true when dueamount > 0
  adharno                   aadhaar_no (12 digits only)
  isdeleted                 is_deleted (+ deleted_at when true)
  createdon / updatedon     created_at / updated_at

Not stored (no matching column): custid, branchid, createdby, updatedby,
isfavor, lastbilldate.

The new farmer master is organization-wide (no branch_id). Old branch 1 / 2
rows all land in the same org.

Usage (from the repo root):

  backend/.venv/bin/python scripts/import_legacy_customers.py
  backend/.venv/bin/python scripts/import_legacy_customers.py --commit

Reads DATABASE_URL / DB_* from backend/.env (same as the app).
Default dump path: ./skac_customers.sql
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DEFAULT_DUMP = ROOT / "skac_customers.sql"

PLACEHOLDER_PHONES = {
    "9999999999",
    "0000000000",
    "1234567890",
    "1111111111",
    "0",
    "00",
}


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip().strip("'").strip('"')
        env[key.strip()] = val
    return env


def database_url(env: dict[str, str]) -> str:
    if env.get("DB_HOST") and env.get("DB_NAME"):
        user = env.get("DB_USER", "")
        password = env.get("DB_PASSWORD", "")
        host = env["DB_HOST"]
        port = env.get("DB_PORT", "3306")
        name = env["DB_NAME"]
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
    return env.get("DATABASE_URL") or env.get("database_url") or ""


def resolve_sqlite_path(url: str) -> Path:
    # sqlite:///./dev.db is relative to backend/ when the app runs there.
    raw = url.replace("sqlite:///", "", 1)
    path = Path(raw)
    if not path.is_absolute():
        path = (BACKEND / path).resolve()
    return path


# --- dump parser -------------------------------------------------------------

def parse_dump(sql: str) -> list[list[object]]:
    rows: list[list[object]] = []
    key = "INSERT INTO `customers` VALUES"
    i = 0
    n = len(sql)
    while True:
        j = sql.find(key, i)
        if j < 0:
            break
        i = j + len(key)
        while i < n:
            while i < n and sql[i] in " \t\r\n,":
                i += 1
            if i >= n:
                break
            if sql[i] == ";":
                i += 1
                break
            if sql[i] != "(":
                raise ValueError(f"expected '(' in dump at offset {i}: {sql[i:i + 80]!r}")
            i += 1
            vals: list[object] = []
            while True:
                while i < n and sql[i] in " \t\r\n":
                    i += 1
                if i >= n:
                    raise ValueError("unexpected end of dump inside a row")
                if sql.startswith("_binary", i):
                    i += 7
                    while i < n and sql[i] in " \t":
                        i += 1
                if sql.startswith("NULL", i) and (
                    i + 4 >= n or not (sql[i + 4].isalnum() or sql[i + 4] == "_")
                ):
                    vals.append(None)
                    i += 4
                elif sql[i] in "'\"":
                    q = sql[i]
                    i += 1
                    buf: list[str] = []
                    while i < n:
                        ch = sql[i]
                        if ch == "\\" and i + 1 < n:
                            nxt = sql[i + 1]
                            mapping = {
                                "0": "\0",
                                "n": "\n",
                                "r": "\r",
                                "t": "\t",
                                "\\": "\\",
                                "'": "'",
                                '"': '"',
                                "Z": "\x1a",
                            }
                            buf.append(mapping.get(nxt, nxt))
                            i += 2
                            continue
                        if ch == q:
                            if i + 1 < n and sql[i + 1] == q:
                                buf.append(q)
                                i += 2
                                continue
                            i += 1
                            break
                        buf.append(ch)
                        i += 1
                    else:
                        raise ValueError("unterminated string in dump")
                    vals.append("".join(buf))
                else:
                    k = i
                    if sql[k] == "-":
                        k += 1
                    while k < n and (sql[k].isdigit() or sql[k] in ".eE+"):
                        k += 1
                    if k == i:
                        raise ValueError(f"bad token in dump: {sql[i:i + 60]!r}")
                    vals.append(sql[i:k])
                    i = k
                while i < n and sql[i] in " \t\r\n":
                    i += 1
                if i >= n:
                    raise ValueError("unexpected end of dump after a value")
                if sql[i] == ",":
                    i += 1
                    continue
                if sql[i] == ")":
                    i += 1
                    break
                raise ValueError(f"unexpected dump token: {sql[i:i + 40]!r}")
            rows.append(vals)
    return rows


def as_bool(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (int, float, Decimal)):
        return value != 0
    text = str(value)
    if text in ("", "0", "\x00"):
        return False
    if text in ("1", "\x01"):
        return True
    return any(ord(ch) == 1 for ch in text)


def as_decimal(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal("0")


def as_datetime(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19] if fmt.endswith("%S") else text[:10], fmt)
        except ValueError:
            continue
    return None


def normalize_phone(raw: object) -> str | None:
    if raw is None:
        return None
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if digits.startswith("91") and len(digits) >= 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if not digits or digits in PLACEHOLDER_PHONES:
        return None
    if len(digits) != 10:
        return None
    return digits


def normalize_aadhaar(raw: object) -> str | None:
    if not raw:
        return None
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    return digits if len(digits) == 12 else None


def clip(value: object | None, n: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:n]


def farmer_name(raw: object, custid: object) -> str:
    name = clip(raw, 150)
    if not name:
        return f"Legacy farmer {custid}"
    if len(name) < 2:
        return f"{name}."
    return name


# --- mapping -----------------------------------------------------------------

def mapped_rows(raw_rows: list[list[object]], skip_deleted: bool) -> tuple[list[dict], dict]:
    stats = {
        "source": len(raw_rows),
        "skipped_deleted": 0,
        "skipped_bad": 0,
        "phone_cleared_placeholder": 0,
        "phone_cleared_duplicate": 0,
        "aadhaar_dropped": 0,
        "aadhaar_cleared_duplicate": 0,
        "with_due": 0,
        "due_total": Decimal("0"),
    }
    staged: list[dict] = []
    for row in raw_rows:
        if len(row) != 14:
            stats["skipped_bad"] += 1
            continue
        (
            custid,
            custname,
            custcity,
            custphone,
            dueamount,
            _branchid,
            _createdby,
            createdon,
            _updatedby,
            updatedon,
            isdeleted,
            _isfavor,
            adharno,
            _lastbilldate,
        ) = row
        deleted = as_bool(isdeleted)
        if deleted and skip_deleted:
            stats["skipped_deleted"] += 1
            continue
        phone = normalize_phone(custphone)
        if custphone and not phone:
            stats["phone_cleared_placeholder"] += 1
        aadhaar = normalize_aadhaar(adharno)
        if adharno and str(adharno).strip() and not aadhaar:
            stats["aadhaar_dropped"] += 1
        due = as_decimal(dueamount).quantize(Decimal("0.01"))
        created = as_datetime(createdon) or datetime.utcnow()
        updated = as_datetime(updatedon) or created
        staged.append(
            {
                "legacy_id": int(custid) if str(custid).isdigit() else None,
                "name": farmer_name(custname, custid),
                "village": clip(custcity, 120),
                "phone": phone,
                "aadhaar_no": aadhaar,
                "outstanding_balance": due,
                "credit_allowed": due > 0,
                "credit_limit": Decimal("0"),
                "is_deleted": deleted,
                "deleted_at": updated if deleted else None,
                "created_at": created,
                "updated_at": updated,
            }
        )
        if due > 0:
            stats["with_due"] += 1
            stats["due_total"] += due

    def keep_winner(groups: dict[str, list[dict]], field: str, stat_key: str) -> None:
        for key, items in groups.items():
            if not key or len(items) < 2:
                continue
            winner = max(
                items,
                key=lambda r: (
                    r["outstanding_balance"],
                    r["updated_at"] or datetime.min,
                    -(r["legacy_id"] or 0),
                ),
            )
            for item in items:
                if item is winner:
                    continue
                item[field] = None
                stats[stat_key] += 1

    by_phone: dict[str, list[dict]] = defaultdict(list)
    by_aadhaar: dict[str, list[dict]] = defaultdict(list)
    for item in staged:
        if item["phone"]:
            by_phone[item["phone"]].append(item)
        if item["aadhaar_no"]:
            by_aadhaar[item["aadhaar_no"]].append(item)
    keep_winner(by_phone, "phone", "phone_cleared_duplicate")
    keep_winner(by_aadhaar, "aadhaar_no", "aadhaar_cleared_duplicate")
    return staged, stats


# --- database ----------------------------------------------------------------

class Db:
    def __init__(self, url: str):
        self.url = url
        self.kind = "sqlite" if url.startswith("sqlite") else "mysql"
        self.conn: object
        if self.kind == "sqlite":
            path = resolve_sqlite_path(url)
            if not path.exists():
                raise SystemExit(f"SQLite database not found: {path}")
            self.conn = sqlite3.connect(str(path))
            self.conn.row_factory = sqlite3.Row
            self.param = "?"
        else:
            try:
                import pymysql  # type: ignore
            except ImportError as exc:
                raise SystemExit("pymysql is required for MySQL. Use backend/.venv/bin/python") from exc
            parsed = urlparse(url.replace("mysql+pymysql://", "mysql://", 1))
            self.conn = pymysql.connect(
                host=parsed.hostname or "127.0.0.1",
                port=parsed.port or 3306,
                user=unquote(parsed.username or ""),
                password=unquote(parsed.password or ""),
                database=unquote(parsed.path.lstrip("/")),
                charset="utf8mb4",
                autocommit=False,
            )
            self.param = "%s"

    def execute(self, sql: str, args: tuple = ()):
        cur = self.conn.cursor()
        cur.execute(sql, args)
        return cur

    def fetchone(self, sql: str, args: tuple = ()):
        return self.execute(sql, args).fetchone()

    def fetchall(self, sql: str, args: tuple = ()):
        return self.execute(sql, args).fetchall()

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


def org_id_from(db: Db, explicit: int | None) -> int:
    if explicit:
        row = db.fetchone(
            f"SELECT id, name FROM organization WHERE id = {db.param} AND COALESCE(is_deleted, 0) = 0",
            (explicit,),
        )
        if not row:
            raise SystemExit(f"organization id {explicit} not found")
        return int(row[0])
    row = db.fetchone(
        "SELECT id, name FROM organization WHERE COALESCE(is_deleted, 0) = 0 ORDER BY id LIMIT 1"
    )
    if not row:
        raise SystemExit("No organization row in the new database")
    print(f"Using organization #{row[0]} ({row[1]})")
    return int(row[0])


def existing_keys(db: Db, org_id: int) -> tuple[set[str], set[str], int]:
    rows = db.fetchall(
        f"SELECT phone, aadhaar_no FROM customer WHERE organization_id = {db.param}",
        (org_id,),
    )
    phones: set[str] = set()
    aadhaars: set[str] = set()
    for phone, aadhaar in rows:
        if phone:
            phones.add(str(phone))
        if aadhaar:
            aadhaars.add(str(aadhaar))
    count_row = db.fetchone(
        f"SELECT COUNT(*) FROM customer WHERE organization_id = {db.param}",
        (org_id,),
    )
    return phones, aadhaars, int(count_row[0])


def insert_rows(db: Db, org_id: int, rows: list[dict]) -> int:
    sql = f"""
        INSERT INTO customer (
            organization_id, name, phone, aadhaar_no, village, district,
            land_holding_acres, gstin, credit_allowed, credit_limit,
            outstanding_balance, created_at, updated_at, is_deleted, deleted_at
        ) VALUES (
            {", ".join([db.param] * 15)}
        )
    """
    cur = db.conn.cursor()
    payload = []
    for r in rows:
        payload.append(
            (
                org_id,
                r["name"],
                r["phone"],
                r["aadhaar_no"],
                r["village"],
                None,
                None,
                None,
                1 if r["credit_allowed"] else 0,
                str(r["credit_limit"]),
                str(r["outstanding_balance"]),
                r["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                r["updated_at"].strftime("%Y-%m-%d %H:%M:%S"),
                1 if r["is_deleted"] else 0,
                r["deleted_at"].strftime("%Y-%m-%d %H:%M:%S") if r["deleted_at"] else None,
            )
        )
    cur.executemany(sql, payload)
    return cur.rowcount if cur.rowcount and cur.rowcount > 0 else len(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import legacy SKAC farmers into the new ERP")
    parser.add_argument("--dump", type=Path, default=DEFAULT_DUMP, help="Path to skac_customers.sql")
    parser.add_argument("--org-id", type=int, default=None, help="Target organization.id (default: first org)")
    parser.add_argument("--skip-deleted", action="store_true", help="Omit farmers marked isdeleted in the dump")
    parser.add_argument("--force", action="store_true", help="Insert even if the new DB already has many farmers")
    parser.add_argument("--commit", action="store_true", help="Write rows. Without this flag, dry-run only.")
    args = parser.parse_args()

    if not args.dump.exists():
        raise SystemExit(f"Dump not found: {args.dump}")

    env = load_env(BACKEND / ".env")
    url = database_url(env)
    if not url:
        raise SystemExit("No DATABASE_URL / DB_* in backend/.env")

    print(f"Reading {args.dump} …")
    raw = parse_dump(args.dump.read_text(encoding="utf-8", errors="replace"))
    staged, stats = mapped_rows(raw, skip_deleted=args.skip_deleted)
    print(
        f"Dump rows: {stats['source']:,}  →  mapped: {len(staged):,}  "
        f"(skipped deleted: {stats['skipped_deleted']:,})"
    )
    print(
        f"Phones cleared (placeholder/invalid): {stats['phone_cleared_placeholder']:,}  "
        f"duplicate phones: {stats['phone_cleared_duplicate']:,}"
    )
    print(
        f"Aadhaar dropped (not 12 digits): {stats['aadhaar_dropped']:,}  "
        f"duplicate Aadhaar: {stats['aadhaar_cleared_duplicate']:,}"
    )
    print(f"Farmers with outstanding: {stats['with_due']:,}  total due: ₹{stats['due_total']:,}")

    db = Db(url)
    try:
        org_id = org_id_from(db, args.org_id)
        phones, aadhaars, existing = existing_keys(db, org_id)
        print(f"Existing farmers in new DB: {existing:,}")
        if existing > 50 and not args.force:
            raise SystemExit(
                f"New DB already has {existing} farmers. Refusing to insert again "
                "(would create duplicates). Pass --force if you really mean it."
            )

        skipped_existing_phone = 0
        skipped_existing_aadhaar = 0
        to_insert: list[dict] = []
        used_phones = set(phones)
        used_aadhaar = set(aadhaars)
        for row in staged:
            if row["phone"] and row["phone"] in used_phones:
                skipped_existing_phone += 1
                row = {**row, "phone": None}
            if row["aadhaar_no"] and row["aadhaar_no"] in used_aadhaar:
                skipped_existing_aadhaar += 1
                row = {**row, "aadhaar_no": None}
            if row["phone"]:
                used_phones.add(row["phone"])
            if row["aadhaar_no"]:
                used_aadhaar.add(row["aadhaar_no"])
            to_insert.append(row)

        print(
            f"Will insert {len(to_insert):,}  "
            f"(cleared phone already in new DB: {skipped_existing_phone}, "
            f"cleared Aadhaar already in new DB: {skipped_existing_aadhaar})"
        )

        if not args.commit:
            print("Dry run only. Re-run with --commit to insert.")
            return 0

        inserted = insert_rows(db, org_id, to_insert)
        db.commit()
        print(f"Inserted {inserted:,} farmers.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
