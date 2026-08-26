"""Default picklists seeded once per organization."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.config import (
    KIND_DISTRICT, KIND_EXPENSE, KIND_GST, KIND_HSN, KIND_PAYMENT,
    KIND_STATE, KIND_TOXICITY, KIND_UNIT, KIND_VILLAGE, ConfigItem,
)
from app.models.organization import Organization


def slug(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return s or "item"


TN_DISTRICTS = (
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
    "Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kanchipuram",
    "Kanniyakumari", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai",
    "Nagapattinam", "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai",
    "Ramanathapuram", "Ranipet", "Salem", "Sivaganga", "Tenkasi",
    "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli",
    "Tirupathur", "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur",
    "Vellore", "Viluppuram", "Virudhunagar",
)

TN_VILLAGES = {
    "erode": (
        "Bhavani", "Perundurai", "Gobichettipalayam", "Sathyamangalam",
        "Anthiyur", "Modakurichi", "Kodumudi", "Chennimalai", "Nambiyur",
        "Thingalur",
    ),
    "salem": (
        "Attur", "Mettur", "Omalur", "Edappadi", "Sankari", "Valapady",
    ),
    "namakkal": ("Rasipuram", "Tiruchengode", "Paramathi"),
    "tiruppur": ("Avinashi", "Palladam", "Kangeyam", "Dharapuram"),
    "coimbatore": ("Mettupalayam", "Pollachi", "Sulur"),
}

FALLBACK_EXPENSE_CATEGORIES = (
    ("transport", "Transport charges", "4100"),
    ("salary", "Employee salary", "4200"),
    ("rent", "Rent", "4300"),
    ("electricity", "Electricity & utilities", "4400"),
    ("packing", "Packing / loading", "4500"),
    ("maintenance", "Maintenance", "4500"),
    ("other", "Other", "4500"),
)


def _has_kind(db: Session, org_id: int, kind: str) -> bool:
    return db.scalar(
        select(ConfigItem.id).where(
            ConfigItem.organization_id == org_id,
            ConfigItem.kind == kind,
            ConfigItem.is_deleted.is_(False),
        ).limit(1)
    ) is not None


def _add(db: Session, org_id: int, kind: str, code: str, name: str, *,
         parent_id: int | None = None, extra: dict | None = None, sort_order: int = 0) -> ConfigItem:
    row = ConfigItem(
        organization_id=org_id, kind=kind, code=code, name=name,
        parent_id=parent_id, extra=extra, is_active=True, sort_order=sort_order,
    )
    db.add(row)
    return row


def ensure_config_defaults(db: Session) -> None:
    orgs = db.scalars(select(Organization).where(Organization.is_deleted.is_(False))).all()
    for org in orgs:
        _seed_org(db, org.id)
    db.flush()


def _seed_org(db: Session, org_id: int) -> None:
    if not _has_kind(db, org_id, KIND_DISTRICT):
        by_code: dict[str, ConfigItem] = {}
        for i, name in enumerate(TN_DISTRICTS):
            row = _add(db, org_id, KIND_DISTRICT, slug(name), name, sort_order=i)
            db.flush()
            by_code[row.code] = row
        for dist_code, villages in TN_VILLAGES.items():
            parent = by_code.get(dist_code)
            if parent is None:
                continue
            for i, name in enumerate(villages):
                _add(db, org_id, KIND_VILLAGE, slug(name), name, parent_id=parent.id, sort_order=i)
        db.flush()

    if not _has_kind(db, org_id, KIND_UNIT):
        for i, name in enumerate(("bag", "kg", "litre", "packet", "bottle", "tin", "piece")):
            _add(db, org_id, KIND_UNIT, slug(name), name, sort_order=i)

    if not _has_kind(db, org_id, KIND_GST):
        for i, rate in enumerate(("0", "5", "12", "18", "28")):
            _add(db, org_id, KIND_GST, rate, f"{rate}%", extra={"rate": float(rate)}, sort_order=i)

    if not _has_kind(db, org_id, KIND_HSN):
        hsn = (
            ("31021000", "Urea / nitrogenous fertilizers", 5),
            ("31053000", "DAP / phosphatic fertilizers", 5),
            ("31052000", "NPK mixtures", 5),
            ("38089199", "Insecticides / pesticides", 18),
            ("10061010", "Paddy seed", 0),
            ("1209", "Seeds for sowing", 0),
        )
        for i, (code, name, gst) in enumerate(hsn):
            _add(db, org_id, KIND_HSN, code, name, extra={"gst_rate": gst}, sort_order=i)

    if not _has_kind(db, org_id, KIND_EXPENSE):
        for i, (code, name, account) in enumerate(FALLBACK_EXPENSE_CATEGORIES):
            _add(db, org_id, KIND_EXPENSE, code, name, extra={"account": account}, sort_order=i)

    if not _has_kind(db, org_id, KIND_TOXICITY):
        for i, name in enumerate(("Class Ia", "Class Ib", "Class II", "Class III", "Class IV")):
            _add(db, org_id, KIND_TOXICITY, slug(name), name, sort_order=i)

    if not _has_kind(db, org_id, KIND_PAYMENT):
        payments = (
            ("cash", "Cash", ["pos", "khata", "expense", "purchase", "invoice_filter"]),
            ("upi", "UPI", ["pos", "khata", "expense", "purchase", "invoice_filter"]),
            ("card", "Card", ["pos", "khata", "invoice_filter"]),
            ("credit", "Credit (Khata)", ["pos", "invoice_filter"]),
            ("bank", "Bank", ["expense", "purchase"]),
        )
        for i, (code, name, use_in) in enumerate(payments):
            _add(db, org_id, KIND_PAYMENT, code, name, extra={"use_in": use_in}, sort_order=i)

    if not _has_kind(db, org_id, KIND_STATE):
        _add(db, org_id, KIND_STATE, "33", "Tamil Nadu", extra={"state_code": "33"}, sort_order=0)
