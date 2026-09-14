#!/usr/bin/env python3
"""Map typed legacy customer villages to official LGD panchayat names.

Reads:
  deploy/mysql/master_villages.sql
  deploy/mysql/migrate_from_dump/07_customer.sql
  Dump20260912.sql (branch hint only)

Writes:
  deploy/mysql/migrate_from_dump/20_customer_village_fix.sql
  and rewrites village/district in 07_customer.sql

  python3 scripts/generate_customer_village_fix.py
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_dump_migration import (  # noqa: E402
    clip,
    iter_dump_inserts,
    parse_insert_rows,
    parse_tuples,
)

MASTER = ROOT / "deploy" / "mysql" / "master_villages.sql"
CUSTOMER_SQL = ROOT / "deploy" / "mysql" / "migrate_from_dump" / "07_customer.sql"
OUT_SQL = ROOT / "deploy" / "mysql" / "migrate_from_dump" / "20_customer_village_fix.sql"
ORG_ID = 1

DIST_LABEL = {
    "kallakurichi": "Kallakurichi",
    "tiruvannamalai": "Tiruvannamalai",
    "viluppuram": "Viluppuram",
}
DIST_CODE = {v: k for k, v in DIST_LABEL.items()}
CATCHMENT_BLOCKS = {
    "Kilpennathur",
    "Melmalayanur",
    "Thurinjapuram",
    "Kalasapakkam",
    "Tiruvannamalai",
    "Chetpet",
    "Chengam",
    "Polur",
    "Gingee",
    "Mugaiyur",
    "Thandarampet",
    "Pudupalayam",
}
GENERIC_STEMS = {
    "KUPPAM",
    "PUTHUR",
    "MOTTUR",
    "PATTU",
    "VADI",
    "KULAM",
    "NATHAM",
    "PURAM",
    "PUNDI",
    "BADI",
    "PADI",
    "NAGAR",
    "PET",
    "UR",
}

# Typed SKAC names → official panchayat (name, district). District must exist in master.
ALIASES: dict[str, tuple[str, str]] = {
    "VEDANTHAVADI": ("Vedandavadi", "Tiruvannamalai"),
    "VEDAANTHAVADI": ("Vedandavadi", "Tiruvannamalai"),
    "VEDANDAVADI": ("Vedandavadi", "Tiruvannamalai"),
    "VEDANTHAVADY": ("Vedandavadi", "Tiruvannamalai"),
    "VEDANTHAVDI": ("Vedandavadi", "Tiruvannamalai"),
    "K.P": ("Kovilporaiyur", "Viluppuram"),
    "KP": ("Kovilporaiyur", "Viluppuram"),
    "K.P.": ("Kovilporaiyur", "Viluppuram"),
    "K.PURAIUR": ("Kovilporaiyur", "Viluppuram"),
    "K. PURAIUR": ("Kovilporaiyur", "Viluppuram"),
    "K.PURAIOUR": ("Kovilporaiyur", "Viluppuram"),
    "K. PURAIOUR": ("Kovilporaiyur", "Viluppuram"),
    "K.PURAIYUR": ("Kovilporaiyur", "Viluppuram"),
    "KOVILPURAIYUR": ("Kovilporaiyur", "Viluppuram"),
    "KOVILPURAIUR": ("Kovilporaiyur", "Viluppuram"),
    "KOVILPORAIYUR": ("Kovilporaiyur", "Viluppuram"),
    "A.P": ("Avalurpettai", "Viluppuram"),
    "A.P.": ("Avalurpettai", "Viluppuram"),
    "AP": ("Avalurpettai", "Viluppuram"),
    "A P": ("Avalurpettai", "Viluppuram"),
    "AVALURPET": ("Avalurpettai", "Viluppuram"),
    "AVALURPETT": ("Avalurpettai", "Viluppuram"),
    "AVALURPETTAI": ("Avalurpettai", "Viluppuram"),
    "AVALOORPET": ("Avalurpettai", "Viluppuram"),
    "B.M": ("Boodamangalam", "Tiruvannamalai"),
    "BM": ("Boodamangalam", "Tiruvannamalai"),
    "BOOTHAMANGALAM": ("Boodamangalam", "Tiruvannamalai"),
    "BOODAMANGALAM": ("Boodamangalam", "Tiruvannamalai"),
    "BUTHAMANGALAM": ("Boodamangalam", "Tiruvannamalai"),
    "ANANTHAL": ("Ananandal", "Tiruvannamalai"),
    "ANATHAL": ("Ananandal", "Tiruvannamalai"),
    "ANANDAL": ("Ananandal", "Tiruvannamalai"),
    "ANANANDAL": ("Ananandal", "Tiruvannamalai"),
    "SANANTHAL": ("Sananandal", "Tiruvannamalai"),
    "SANANDAL": ("Sananandal", "Tiruvannamalai"),
    "SANANANDAL": ("Sananandal", "Tiruvannamalai"),
    "PALANANTHAL": ("Palanandal", "Tiruvannamalai"),
    "PALANANDAL": ("Palanandal", "Tiruvannamalai"),
    "MELPALANANTHAL": ("Palanandal", "Tiruvannamalai"),
    "MEL PALANANTHAL": ("Palanandal", "Tiruvannamalai"),
    "MELPALANANDHAL": ("Palanandal", "Tiruvannamalai"),
    "MELPALANADHAL": ("Palanandal", "Tiruvannamalai"),
    "PALANADHAL": ("Palanandal", "Tiruvannamalai"),
    "KILPALANANTHAL": ("Palanandal", "Tiruvannamalai"),
    "KEELPALANANTHAL": ("Palanandal", "Tiruvannamalai"),
    "SADAYANUDAI": ("Sadayanodai", "Tiruvannamalai"),
    "SADAYANODAI": ("Sadayanodai", "Tiruvannamalai"),
    "SADAYANODAY": ("Sadayanodai", "Tiruvannamalai"),
    "ERUMBUNDI": ("Erumpoondi", "Tiruvannamalai"),
    "ERUMPUNDI": ("Erumpoondi", "Tiruvannamalai"),
    "ERUMPOONDI": ("Erumpoondi", "Tiruvannamalai"),
    "ERUMBOONDI": ("Erumpoondi", "Tiruvannamalai"),
    "KEKLUR": ("Keekalur", "Tiruvannamalai"),
    "KEKKALUR": ("Keekalur", "Tiruvannamalai"),
    "KEEKALUR": ("Keekalur", "Tiruvannamalai"),
    "KEKALUR": ("Keekalur", "Tiruvannamalai"),
    "MEKLUR": ("Mekkalur", "Tiruvannamalai"),
    "MEKKALUR": ("Mekkalur", "Tiruvannamalai"),
    "KILIPATTU": ("Kiliyapattu", "Tiruvannamalai"),
    "KILIYAPATTU": ("Kiliyapattu", "Tiruvannamalai"),
    "KELAKUPPAM": ("Kilkuppam", "Tiruvannamalai"),
    "KILAKUPPAM": ("Kilkuppam", "Tiruvannamalai"),
    "KEELAKUPPAM": ("Kilkuppam", "Tiruvannamalai"),
    "KILKUPPAM": ("Kilkuppam", "Tiruvannamalai"),
    "NUKAMBADI": ("Nookkambadi", "Tiruvannamalai"),
    "NOOKAMBADI": ("Nookkambadi", "Tiruvannamalai"),
    "NOOKKAMBADI": ("Nookkambadi", "Tiruvannamalai"),
    "NOCHALUR": ("Nochalur", "Viluppuram"),
    "NOCHALLUR": ("Nochalur", "Viluppuram"),
    "NOCHILUR": ("Nochalur", "Viluppuram"),
    "VADUGAPUNDI": ("Vadukapoondi", "Viluppuram"),
    "VADUKAPUNDI": ("Vadukapoondi", "Viluppuram"),
    "VADUKAPOONDI": ("Vadukapoondi", "Viluppuram"),
    "ETHAPATTU": ("Edapattu", "Viluppuram"),
    "EDAPATTU": ("Edapattu", "Viluppuram"),
    "ETHAPPATTU": ("Edapattu", "Viluppuram"),
    "KODAPADI": ("Kodampadi", "Viluppuram"),
    "KODAMPADI": ("Kodampadi", "Viluppuram"),
    "KODAMPADY": ("Kodampadi", "Viluppuram"),
    "MANANTHAL": ("Manandal", "Viluppuram"),
    "MANANDAL": ("Manandal", "Viluppuram"),
    "METTUVAILAMBUR": ("Melvailamur", "Viluppuram"),
    "MELVAILAMBUR": ("Melvailamur", "Viluppuram"),
    "MELVAILAMUR": ("Melvailamur", "Viluppuram"),
    "KIZHVAILAMBUR": ("Kizhvailamur", "Viluppuram"),
    "KILVAILAMBUR": ("Kizhvailamur", "Viluppuram"),
    "KUNTHALAPATTU": ("Kunthalampattu", "Viluppuram"),
    "KUNTHALAMPATTU": ("Kunthalampattu", "Viluppuram"),
    "ARPAKKAM": ("Arppakkam", "Tiruvannamalai"),
    "ARPAKAM": ("Arppakkam", "Tiruvannamalai"),
    "ARPPAKKAM": ("Arppakkam", "Tiruvannamalai"),
    "PARAIYAPATTU": ("Paraiampattu", "Viluppuram"),
    "PARAIAMPATTU": ("Paraiampattu", "Viluppuram"),
    "KOTTAPUNDI": ("Kottapondi", "Viluppuram"),
    "KOTTAPONDI": ("Kottapondi", "Viluppuram"),
    "KOTTAPOONDI": ("Kottapondi", "Viluppuram"),
    "NAMINTHAL": ("So.namiyandal", "Tiruvannamalai"),
    "T.NAMINTHAL": ("So.namiyandal", "Tiruvannamalai"),
    "T. NAMINTHAL": ("So.namiyandal", "Tiruvannamalai"),
    "NAMIYANDAL": ("So.namiyandal", "Tiruvannamalai"),
    "SO.NAMIYANDAL": ("So.namiyandal", "Tiruvannamalai"),
    "SEYAPUNDI": ("Sevarapoondi", "Tiruvannamalai"),
    "SEVARAPUNDI": ("Sevarapoondi", "Tiruvannamalai"),
    "SEVARAPOONDI": ("Sevarapoondi", "Tiruvannamalai"),
    "THAYANUR": ("Thayanur", "Viluppuram"),
    "THAIYANUR": ("Thayanur", "Viluppuram"),
    "SINTHIPATTU": ("Sinthipattu", "Viluppuram"),
    "CHINTHIPATTU": ("Sinthipattu", "Viluppuram"),
    "MELMALAIYANUR": ("Melmaliyanur", "Viluppuram"),
    "MELMALAYANUR": ("Melmaliyanur", "Viluppuram"),
    "MELMALIYANUR": ("Melmaliyanur", "Viluppuram"),
    "KALASTHAMBADI": ("Kalasthambadi", "Tiruvannamalai"),
    "KALASTHAMBADY": ("Kalasthambadi", "Tiruvannamalai"),
    "VALLIVAGAI": ("Vallivagai", "Tiruvannamalai"),
    "VADAANDAPATTU": ("Vadaandapattu", "Tiruvannamalai"),
    "VADAANDAPATU": ("Vadaandapattu", "Tiruvannamalai"),
    "VADANDAPATTU": ("Vadaandapattu", "Tiruvannamalai"),
    "THURINJAPURAM": ("Thurinjapuram", "Tiruvannamalai"),
    "THURINGAPURAM": ("Thurinjapuram", "Tiruvannamalai"),
    "SENTHIPATTU": ("Sinthipattu", "Viluppuram"),
    "SENTHIPATU": ("Sinthipattu", "Viluppuram"),
    "SINDHIPATTU": ("Sinthipattu", "Viluppuram"),
    "CHINTHIPATTU": ("Sinthipattu", "Viluppuram"),
    "SAVARAPUNDI": ("Sevarapoondi", "Tiruvannamalai"),
    "SAVARAPOONDI": ("Sevarapoondi", "Tiruvannamalai"),
    "SANANDHAL": ("Sananandal", "Tiruvannamalai"),
    "SANANDHALL": ("Sananandal", "Tiruvannamalai"),
    "VELUGANADHAL": ("Veluganandal", "Tiruvannamalai"),
    "VELUGANANTHAL": ("Veluganandal", "Tiruvannamalai"),
    "VELUGANANDAL": ("Veluganandal", "Tiruvannamalai"),
    "VELUGANATHAL": ("Veluganandal", "Tiruvannamalai"),
    "VELUGANANDHAL": ("Veluganandal", "Tiruvannamalai"),
    "SEIYAPUNDI": ("Sevarapoondi", "Tiruvannamalai"),
    "CHIRUTHALAIPUNDI": ("Siruthlaipoondi", "Viluppuram"),
    "SIRUTHALAIPOONDI": ("Siruthlaipoondi", "Viluppuram"),
    "SIRUTHLAIPOONDI": ("Siruthlaipoondi", "Viluppuram"),
    "VADUGABUNDI": ("Vadukapoondi", "Viluppuram"),
    "AANDAPATTU": ("Andapattu", "Viluppuram"),
    "KUNNIYENTHAL": ("Kunniyandal", "Tiruvannamalai"),
    "KUNNIYANTHAL": ("Kunniyandal", "Tiruvannamalai"),
    "KAPPALAMPADI": ("Kapplampadi", "Viluppuram"),
    "KAPPLAMPADI": ("Kapplampadi", "Viluppuram"),
    "KAPPALAPADI": ("Kapplampadi", "Viluppuram"),
    "KEGALUR": ("Keekalur", "Tiruvannamalai"),
    "KALASTHAMABADI": ("Kalasthambadi", "Tiruvannamalai"),
    "KALASTHAMPADI": ("Kalasthambadi", "Tiruvannamalai"),
    "KALASTHAMBADY": ("Kalasthambadi", "Tiruvannamalai"),
    "KODAMBADI": ("Kodampadi", "Viluppuram"),
    "KAIKULAM": ("Kazhikulam", "Tiruvannamalai"),
    "KAZHIKULAM": ("Kazhikulam", "Tiruvannamalai"),
    "KALIKULAM": ("Kazhikulam", "Tiruvannamalai"),
    "PARAIYAMPATTU": ("Parayampattu", "Tiruvannamalai"),
    "PARAYAMPATTU": ("Parayampattu", "Tiruvannamalai"),
    "KOTHANDAVADI": ("Kothandavadi", "Tiruvannamalai"),
    "B.MANGALAM": ("Boodamangalam", "Tiruvannamalai"),
    "C.NAMINTHAL": ("C.Nammiyandal", "Tiruvannamalai"),
    "C.NAMMIYANDAL": ("C.Nammiyandal", "Tiruvannamalai"),
    "C.NAMMIYANTHAL": ("C.Nammiyandal", "Tiruvannamalai"),
    "D.NAMINTHAL": ("Durgainammiyandal", "Tiruvannamalai"),
    "D NAMMIYANTHAL": ("Durgainammiyandal", "Tiruvannamalai"),
    "D.NAMMIYANTHAL": ("Durgainammiyandal", "Tiruvannamalai"),
    "D.NAMIYANDAL": ("Durgainammiyandal", "Tiruvannamalai"),
    "DURGAINAMMIYANTHAL": ("Durgainammiyandal", "Tiruvannamalai"),
    "THURKAINAMINTHAL": ("Durgainammiyandal", "Tiruvannamalai"),
    "THURGAINAMINTHAL": ("Durgainammiyandal", "Tiruvannamalai"),
    "V 'VADI": ("Vedandavadi", "Tiruvannamalai"),
    "V VADI": ("Vedandavadi", "Tiruvannamalai"),
    "NAMMIYANTHAL": ("So.namiyandal", "Tiruvannamalai"),
    "NAMMIYANDAL": ("So.namiyandal", "Tiruvannamalai"),
    "AATHIPATTU": ("Athipattu", "Viluppuram"),
    "ATHIPATTU": ("Athipattu", "Viluppuram"),
    "PALANANDHAL": ("Palanandal", "Tiruvannamalai"),
    "KELPALANANTHAL": ("Palanandal", "Tiruvannamalai"),
    "KEELPALANANTHAL": ("Palanandal", "Tiruvannamalai"),
    "SAVARABUNDI": ("Sevarapoondi", "Tiruvannamalai"),
    "EYAKUNAM": ("Eayakunam", "Viluppuram"),
    "EAYAKUNAM": ("Eayakunam", "Viluppuram"),
    "IYAKUNAM": ("Eayakunam", "Viluppuram"),
    "THURINJAPUREM": ("Thurinjapuram", "Tiruvannamalai"),
    "KELKUPPAM": ("Kilkuppam", "Tiruvannamalai"),
    "KEELKUPPAM": ("Kilkuppam", "Tiruvannamalai"),
    "KANALAPADI": ("Ganalapadi", "Tiruvannamalai"),
    "GANALAPADI": ("Ganalapadi", "Tiruvannamalai"),
}

# Habitations / shop abbreviations that are not LGD village panchayats.
# Keep a single local spelling and a predicted district so POS can still filter.
HAMLETS: dict[str, tuple[str, str]] = {
    "THAYAKUNAM": ("Thayakunam", "Tiruvannamalai"),
    "THAYANKUNAM": ("Thayakunam", "Tiruvannamalai"),
    "THAIAKUNAM": ("Thayakunam", "Tiruvannamalai"),
    "MATHULAMBADI": ("Mathulambadi", "Tiruvannamalai"),
    "MATHULAMABADI": ("Mathulambadi", "Tiruvannamalai"),
    "MATHULAMPADI": ("Mathulambadi", "Tiruvannamalai"),
    "MATHULAMBADY": ("Mathulambadi", "Tiruvannamalai"),
    "T.KUPPAM": ("Thathankuppam", "Tiruvannamalai"),
    "T.KUPPM": ("Thathankuppam", "Tiruvannamalai"),
    "TKUPPAM": ("Thathankuppam", "Tiruvannamalai"),
    "THATHANKUPPAM": ("Thathankuppam", "Tiruvannamalai"),
    "TATHANKUPPAM": ("Thathankuppam", "Tiruvannamalai"),
    "T.K": ("Thathankuppam", "Tiruvannamalai"),
    "TK": ("Thathankuppam", "Tiruvannamalai"),
    "T K": ("Thathankuppam", "Tiruvannamalai"),
    "THOPPU": ("Thoppu", "Tiruvannamalai"),
    "TOPPU": ("Thoppu", "Tiruvannamalai"),
    "KUNNUMURINJI": ("Kunnumurinji", "Tiruvannamalai"),
    "KUNNUMURUNJI": ("Kunnumurinji", "Tiruvannamalai"),
    "KUNNUMURINJ": ("Kunnumurinji", "Tiruvannamalai"),
    "POIYANANTHAL": ("Poiyananthal", "Tiruvannamalai"),
    "POIYANANDAL": ("Poiyananthal", "Tiruvannamalai"),
    "POYANANTHAL": ("Poiyananthal", "Tiruvannamalai"),
    "POIYANATHAL": ("Poiyananthal", "Tiruvannamalai"),
    "KOOTHALAVADI": ("Koothalavadi", "Tiruvannamalai"),
    "KUTHALAVADI": ("Koothalavadi", "Tiruvannamalai"),
    "KUTHALAVADY": ("Koothalavadi", "Tiruvannamalai"),
    "MANSURAPATH": ("Mansurapath", "Tiruvannamalai"),
    "MANSURABATH": ("Mansurapath", "Tiruvannamalai"),
    "MANSURABADH": ("Mansurapath", "Tiruvannamalai"),
    "V.P.KUPPAM": ("V.P. Kuppam", "Tiruvannamalai"),
    "V.P KUPPAM": ("V.P. Kuppam", "Tiruvannamalai"),
    "VPKUPPAM": ("V.P. Kuppam", "Tiruvannamalai"),
    "SELVAPURAM": ("Selvapuram", "Tiruvannamalai"),
    "SELVAPUREM": ("Selvapuram", "Tiruvannamalai"),
    "VANIYAMTHANGAL": ("Vaniyamthangal", "Tiruvannamalai"),
    "VANIYANTHANGAL": ("Vaniyamthangal", "Tiruvannamalai"),
    "RAVANAPATTU": ("Ravanapattu", "Tiruvannamalai"),
    "MANNAPATTI": ("Mannapatti", "Tiruvannamalai"),
    "MAYANKULAM": ("Mayankulam", "Tiruvannamalai"),
    "MAYAKULAM": ("Mayankulam", "Tiruvannamalai"),
    "MANIYANTHAPATTU": ("Maniyanthapattu", "Tiruvannamalai"),
    "KALARPALAYAM": ("Kalarpalayam", "Tiruvannamalai"),
    "MATTAPARAI": ("Mattaparai", "Tiruvannamalai"),
    "SEKKADIKUPPAM": ("Sekkadikuppam", "Tiruvannamalai"),
    "CHATRAM": ("Chatram", "Tiruvannamalai"),
    "ILAVATHADI": ("Ilavathadi", "Tiruvannamalai"),
    "ELAVATHADI": ("Ilavathadi", "Tiruvannamalai"),
    "VAITHANAKUNAM": ("Vaithanakunam", "Tiruvannamalai"),
    "VAITHANAGUNAM": ("Vaithanakunam", "Tiruvannamalai"),
    "TVM": ("Tiruvannamalai", "Tiruvannamalai"),
    "T.V.M": ("Tiruvannamalai", "Tiruvannamalai"),
    "TIRUVANNAMALAI": ("Tiruvannamalai", "Tiruvannamalai"),
    "THIRUVANNAMALAI": ("Tiruvannamalai", "Tiruvannamalai"),
    "V.NAMINTHAL": ("V. Naminthal", "Tiruvannamalai"),
    "V. NAMINTHAL": ("V. Naminthal", "Tiruvannamalai"),
    "V NAMMIYANTHAL": ("V. Naminthal", "Tiruvannamalai"),
    "V.NAMMIYANTHAL": ("V. Naminthal", "Tiruvannamalai"),
    "M.PUTHUR": ("M. Puthur", "Tiruvannamalai"),
    "M PUDHUR": ("M. Puthur", "Tiruvannamalai"),
    "M.PUDHUR": ("M. Puthur", "Tiruvannamalai"),
    "M PUTHUR": ("M. Puthur", "Tiruvannamalai"),
    "RAMANATHAPURAM": ("Ramanathapuram", "Tiruvannamalai"),
    "RAMANATHAPURM": ("Ramanathapuram", "Tiruvannamalai"),
    "MELMAMPATTU": ("Melmampattu", "Tiruvannamalai"),
    "MEL MAMPATTU": ("Melmampattu", "Tiruvannamalai"),
    "RAVANAMPATTU": ("Ravanapattu", "Tiruvannamalai"),
    "KATTUKULAM": ("Kattukulam", "Tiruvannamalai"),
    "KODAPUNDI": ("Kodapundi", "Viluppuram"),
    "THELLANANTHAL": ("Thellananthal", "Tiruvannamalai"),
    "KORAGATHANGAL": ("Koragathangal", "Tiruvannamalai"),
    "AMMANKALODAI": ("Ammankalodai", "Tiruvannamalai"),
    "KARAPALLAM": ("Karapallam", "Tiruvannamalai"),
}


def sql_str(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def compact(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def phonetic(text: str) -> str:
    s = compact(text)
    reps = (
        ("THIRU", "TIRU"),
        ("BOOTHA", "BOODA"),
        ("PORAIYUR", "PURAIYUR"),
        ("PORAIUR", "PURAIYUR"),
        ("PURAIUR", "PURAIYUR"),
        ("POONDI", "PUNDI"),
        ("BUNDI", "PUNDI"),
        ("ANTHAL", "ANDAL"),
        ("ANANDHAL", "ANDAL"),
        ("NANDHAL", "NANDAL"),
        ("UDAI", "ODAI"),
        ("KEELA", "KIL"),
        ("KIZH", "KIL"),
        ("PETTAI", "PET"),
        ("OO", "U"),
        ("EE", "I"),
        ("TH", "D"),
        ("DH", "D"),
        ("KK", "K"),
        ("TT", "T"),
        ("PP", "P"),
        ("NN", "N"),
        ("LL", "L"),
        ("MM", "M"),
        ("SS", "S"),
        ("RR", "R"),
    )
    for a, b in reps:
        s = s.replace(a, b)
    return s


def parse_official() -> list[dict]:
    text = MASTER.read_text(encoding="utf-8")
    rows = re.findall(
        r"@d_(kallakurichi|tiruvannamalai|viluppuram) AS parent_id, "
        r"'([^']*)' AS code, '([^']*)' AS name, '(\{[^']*\})'",
        text,
    )
    official = []
    for dist, code, name, extra in rows:
        block_m = re.search(r'"block":"([^"]+)"', extra)
        official.append(
            {
                "dist_code": dist,
                "district": DIST_LABEL[dist],
                "name": name,
                "code": code,
                "block": block_m.group(1) if block_m else "",
                "key": compact(name),
                "ph": phonetic(name),
            }
        )
    return official


def load_dump_customers() -> list[tuple[int, str, str]]:
    """(cust_id, typed_village, branch_id) from the legacy dump."""
    out = []
    for _, line in iter_dump_inserts({"customers"}):
        for row in parse_insert_rows(line):
            cid = int(row[0])
            city = (clip(row[2], 120) or "").strip()
            out.append((cid, city, str(row[5])))
    return out


def variant_names(src: str, canonical: str) -> list[str]:
    names = {src, canonical, title_keep(src)}
    if src:
        names.add(src.upper())
        names.add(src.title())
    return sorted({n for n in names if n}, key=lambda s: (s != canonical, s.upper()))


def variant_names_many(sources: list[str], canonical: str, unique: Counter) -> list[str]:
    names: set[str] = {canonical}
    for src in sources:
        names.update(variant_names(src, canonical))
    return sorted(names, key=lambda s: (s != canonical, -unique.get(s, 0), s.upper()))


def emit_customer_tuple(fields: list, village: str | None, district: str) -> str:
    cid, org, name, phone, aadhaar, _v, _d, credit, lim, due, deleted, created, updated = fields[:13]

    def q(value: object | None) -> str:
        if value is None:
            return "NULL"
        return sql_str(str(value))

    return (
        f"({cid}, {org}, {sql_str(str(name))}, {q(phone)}, {q(aadhaar)}, "
        f"{q(village)}, {sql_str(district)}, {credit}, {lim}, {due}, {deleted}, "
        f"{q(created)}, {q(updated)})"
    )


def branch_hint(counts: Counter) -> str:
    avl = counts.get("1", 0)
    tvm = counts.get("2", 0)
    total = avl + tvm
    if total == 0:
        return "mixed"
    if avl / total >= 0.8:
        return "avl"
    if tvm / total >= 0.8:
        return "tvm"
    return "mixed"


def score_candidate(row: dict, hint: str) -> tuple:
    catchment = 0 if row["block"] in CATCHMENT_BLOCKS else 1
    dist_pref = {"tiruvannamalai": 0, "viluppuram": 1, "kallakurichi": 2}[row["dist_code"]]
    if hint == "avl":
        if row["dist_code"] == "viluppuram" and row["block"] == "Melmalayanur":
            dist_pref = -1
        elif row["dist_code"] == "tiruvannamalai" and row["block"] in {"Kilpennathur", "Thurinjapuram"}:
            dist_pref = 0
        elif row["dist_code"] == "kallakurichi":
            dist_pref = 5
    elif hint == "tvm":
        if row["dist_code"] != "tiruvannamalai":
            dist_pref += 2
    return (catchment, dist_pref, row["name"])


def prefer(cands: list[dict], hint: str) -> dict:
    return sorted(cands, key=lambda r: score_candidate(r, hint))[0]


def is_initialism(src: str) -> bool:
    compact_src = compact(src)
    return bool(re.fullmatch(r"[A-Z](?:\.[A-Z])+\.?", src.strip().upper())) or len(compact_src) <= 2


class Matcher:
    def __init__(self, official: list[dict], branch_by_village: dict[str, Counter]):
        self.official = official
        self.branch_by_village = branch_by_village
        self.by_key: dict[str, list[dict]] = defaultdict(list)
        self.by_ph: dict[str, list[dict]] = defaultdict(list)
        self.by_name: dict[tuple[str, str], dict] = {}
        for row in official:
            self.by_key[row["key"]].append(row)
            self.by_ph[row["ph"]].append(row)
            self.by_name[(row["name"], row["district"])] = row

    def resolve_pair(self, name: str, district: str) -> dict:
        hit = self.by_name.get((name, district))
        if not hit:
            raise SystemExit(f"Alias/hamlet target not in master and not marked hamlet: {name} / {district}")
        return hit

    def match(self, raw: str) -> tuple[str, str, str, str]:
        """Return (village, district, kind, note). kind=official|hamlet|unmatched."""
        src = (raw or "").strip()
        if not src:
            return src, "Tiruvannamalai", "unmatched", "empty"
        key = src.upper().strip()
        hint = branch_hint(self.branch_by_village.get(key, Counter()))

        if key in ALIASES:
            name, dist = ALIASES[key]
            row = self.by_name.get((name, dist))
            if not row:
                raise SystemExit(f"Alias target missing from master: {key} -> {name} / {dist}")
            return row["name"], row["district"], "official", f"alias:{row['block']}"

        if key in HAMLETS:
            name, dist = HAMLETS[key]
            return name, dist, "hamlet", "legacy-habitation"

        parts = [p.strip() for p in re.split(r"\s*[,/]\s*|\s+AND\s+", src) if p.strip()]
        if is_initialism(src) and key not in ALIASES and key not in HAMLETS:
            return src, "Tiruvannamalai", "unmatched", "abbrev"

        compact_src = compact(src)
        if compact_src in self.by_key:
            row = prefer(self.by_key[compact_src], hint)
            how = "exact" if len({(c["name"], c["district"]) for c in self.by_key[compact_src]}) == 1 else "exact-disambiguated"
            return row["name"], row["district"], "official", f"{how}:{row['block']}"

        ph = phonetic(src)
        if len(compact_src) >= 6 and ph in self.by_ph:
            row = prefer(self.by_ph[ph], hint)
            how = "phonetic" if len({(c["name"], c["district"]) for c in self.by_ph[ph]}) == 1 else "phonetic-disambiguated"
            return row["name"], row["district"], "official", f"{how}:{row['block']}"

        if len(parts) > 1:
            for part in parts:
                if part.upper() == key:
                    continue
                village, district, kind, note = self.match(part)
                if kind != "unmatched":
                    return village, district, kind, f"part:{note}"

        return src, "Tiruvannamalai", "unmatched", "no-lgd-match"


def title_keep(src: str) -> str:
    src = src.strip()
    if not src:
        return src
    if re.fullmatch(r"[A-Z](?:\.[A-Z./ ]*)+", src.upper()):
        return src.upper()
    parts = re.split(r"([^A-Za-z0-9]+)", src)
    out = []
    for part in parts:
        if not part or not part.isalnum():
            out.append(part)
        elif len(part) <= 2:
            out.append(part.upper())
        else:
            out.append(part[:1].upper() + part[1:].lower())
    return "".join(out)


def load_branch_hints() -> dict[str, Counter]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for _, line in iter_dump_inserts({"customers"}):
        for row in parse_insert_rows(line):
            city = str(row[2] or "").strip().upper()
            counts[city][str(row[5])] += 1
    return counts


def in_clause(values: list[str]) -> str:
    return ", ".join(sql_str(v) for v in values)


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "village"


def main() -> None:
    official = parse_official()
    print(f"Official villages: {len(official)}")
    dump_customers = load_dump_customers()
    villages = [city for _, city, _ in dump_customers if city]
    print(f"Dump customers: {len(dump_customers)} with village {len(villages)} unique {len(set(villages))}")
    branch_by_village = load_branch_hints()
    matcher = Matcher(official, branch_by_village)

    unique = Counter(villages)
    mapping: dict[str, tuple[str, str, str, str]] = {}
    stats = Counter()
    customers_by_kind = Counter()
    empty_village = sum(1 for _, city, _ in dump_customers if not city)
    for src, n in unique.items():
        village, district, kind, note = matcher.match(src)
        if kind == "unmatched":
            village = title_keep(src)
        mapping[src] = (village, district, kind, note)
        stats[kind] += 1
        customers_by_kind[kind] += n
    customers_by_kind["empty"] = empty_village

    official_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    hamlet_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    unmatched_rows = []
    for src, n in unique.most_common():
        village, district, kind, note = mapping[src]
        if kind == "official":
            official_groups[(village, district)].append(src)
        elif kind == "hamlet":
            hamlet_groups[(village, district)].append(src)
        else:
            unmatched_rows.append((n, src, village, district, note))

    hamlet_counts = Counter()
    for src, n in unique.items():
        village, district, kind, _ = mapping[src]
        if kind == "hamlet":
            hamlet_counts[(village, district)] += n

    lines: list[str] = []
    lines += [
        "-- Normalize customer.village / customer.district against LGD village panchayats",
        "-- in deploy/mysql/master_villages.sql, plus SKAC shop abbreviations.",
        "--",
        "-- Review before running. Safe to re-run (matches old typed names and official names).",
        "-- Run after 07_customer.sql (and after master_villages.sql so POS dropdowns exist).",
        "--",
        f"-- Customers from dump: {len(dump_customers)} (empty village: {empty_village})",
        f"-- Unique typed villages: {len(unique)}",
        f"-- Official LGD matches: {customers_by_kind['official']} customers, {stats['official']} spellings",
        f"-- Habitations not in LGD: {customers_by_kind['hamlet']} customers, {stats['hamlet']} spellings",
        f"-- Left unmatched (title-cased, district Tiruvannamalai): {customers_by_kind['unmatched']} customers, {stats['unmatched']} spellings",
        "--",
        "-- Shop abbreviations used only when the AVL/TVM split is clear:",
        "--   K.P / K.PURAIUR     → Kovilporaiyur (Viluppuram, Melmalayanur)",
        "--   A.P / AVALURPET     → Avalurpettai (Viluppuram)  [A.P is AVL-shop, not Ananthapuram]",
        "--   B.M                 → Boodamangalam (Tiruvannamalai)",
        "--   T.K / T.KUPPAM      → Thathankuppam (habitation, not in LGD)",
        "-- Duplicate panchayat names (Mangalam, Mottur, …) prefer Tiruvannamalai,",
        "-- or Viluppuram Melmalayanur when 80%+ of that spelling is AVL-shop.",
        "--",
        "-- mysql -u root -p skac_new < deploy/mysql/migrate_from_dump/20_customer_village_fix.sql",
        "",
        "USE skac_new;",
        "SET NAMES utf8mb4;",
        "",
        "SET @org_id := 1;",
        "SET @d_kallakurichi := (SELECT id FROM config_item WHERE organization_id=@org_id AND kind='district' AND code='kallakurichi' AND is_deleted=0 ORDER BY id LIMIT 1);",
        "SET @d_tiruvannamalai := (SELECT id FROM config_item WHERE organization_id=@org_id AND kind='district' AND code='tiruvannamalai' AND is_deleted=0 ORDER BY id LIMIT 1);",
        "SET @d_viluppuram := (SELECT id FROM config_item WHERE organization_id=@org_id AND kind='district' AND code='viluppuram' AND is_deleted=0 ORDER BY id LIMIT 1);",
        "",
        "-- ---------------------------------------------------------------------------",
        "-- A) Official LGD village panchayat names + district",
        "-- ---------------------------------------------------------------------------",
        "",
    ]

    for (village, district), sources in sorted(official_groups.items(), key=lambda kv: (-sum(unique[s] for s in kv[1]), kv[0][0])):
        sources_sorted = variant_names_many(sources, village, unique)
        n = sum(unique[s] for s in sources)
        typed = [s for s in sources if s != village]
        comment_src = ", ".join(f"{s} x{unique[s]}" for s in sorted(typed, key=lambda x: -unique[x])) or "already official spelling"
        lines.append(f"-- {n} customers  {comment_src}  →  {village} / {district}")
        lines.append(
            "UPDATE customer SET "
            f"village = {sql_str(village)}, district = {sql_str(district)} "
            f"WHERE organization_id = {ORG_ID} AND village IN ({in_clause(sources_sorted)});"
        )
        lines.append("")

    lines += [
        "-- ---------------------------------------------------------------------------",
        "-- B) Habitations that are not LGD village panchayats (normalized local names)",
        "--    Add them to config so POS district→village dropdowns still work.",
        "-- ---------------------------------------------------------------------------",
        "",
    ]
    parent_var = {
        "Kallakurichi": "@d_kallakurichi",
        "Tiruvannamalai": "@d_tiruvannamalai",
        "Viluppuram": "@d_viluppuram",
    }
    used_codes: set[str] = {row["code"] for row in official}
    for (village, district), n in sorted(hamlet_counts.items(), key=lambda kv: -kv[1]):
        code = slug(village)
        if code in used_codes:
            code = f"{code}-habitation"
        used_codes.add(code)
        lines.append(f"-- {n} customers  →  {village} / {district}  (not in LGD panchayat list)")
        lines.append(
            "INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)"
        )
        lines.append(
            f"SELECT @org_id, 'village', {parent_var[district]}, {sql_str(code)}, {sql_str(village)}, "
            "'{\"source\":\"skac-legacy-habitation\"}', 1, 9000"
        )
        lines.append("WHERE NOT EXISTS (")
        lines.append(
            "  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' "
            f"AND c.is_deleted=0 AND c.parent_id={parent_var[district]} AND (c.code={sql_str(code)} OR c.name={sql_str(village)})"
        )
        lines.append(");")
        lines.append("")

    for (village, district), sources in sorted(hamlet_groups.items(), key=lambda kv: (-sum(unique[s] for s in kv[1]), kv[0][0])):
        sources_sorted = variant_names_many(sources, village, unique)
        n = sum(unique[s] for s in sources)
        typed = [s for s in sources if s != village]
        comment_src = ", ".join(f"{s} x{unique[s]}" for s in sorted(typed, key=lambda x: -unique[x])) or "already canonical"
        lines.append(f"-- {n} customers  {comment_src}  →  {village} / {district}")
        lines.append(
            "UPDATE customer SET "
            f"village = {sql_str(village)}, district = {sql_str(district)} "
            f"WHERE organization_id = {ORG_ID} AND village IN ({in_clause(sources_sorted)});"
        )
        lines.append("")

    lines += [
        "-- ---------------------------------------------------------------------------",
        "-- C) Unmatched spellings (not updated). Title-cased only in 07_customer.sql.",
        "--     Add to Config or extend ALIASES in scripts/generate_customer_village_fix.py.",
        "-- ---------------------------------------------------------------------------",
        "",
    ]
    lines.append("-- count  typed_name")
    for n, src, village, district, note in unmatched_rows:
        if n >= 5:
            lines.append(f"-- {n:5}  {src}   ({note})")
    low = sum(n for n, *_ in unmatched_rows if n < 5)
    lines.append(f"-- … plus {low} customers across spellings with fewer than 5 farmers each")
    lines.append("")

    OUT_SQL.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_SQL}")

    id_to_city = {cid: city for cid, city, _ in dump_customers}
    text = CUSTOMER_SQL.read_text(encoding="utf-8")
    header_note = (
        "-- Village/district normalized against master_villages.sql "
        "(see 20_customer_village_fix.sql for the reviewable UPDATE).\n"
    )
    if "Village/district normalized" not in text:
        text = text.replace(
            "-- Duplicate / placeholder phones stored as NULL (unique org+phone).\n",
            "-- Duplicate / placeholder phones stored as NULL (unique org+phone).\n" + header_note,
        )

    out_lines = []
    nsub = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if not stripped.startswith("("):
            out_lines.append(line)
            continue
        ending = ",\n" if stripped.endswith(",") else ";\n" if stripped.endswith(";") else "\n"
        body = stripped.rstrip().rstrip(",").rstrip(";")
        parsed = parse_tuples(body)
        if not parsed:
            out_lines.append(line)
            continue
        fields = parsed[0]
        cid = int(fields[0])
        src = id_to_city.get(cid, fields[5] or "")
        if not src:
            village, district = None, "Tiruvannamalai"
        else:
            village, district, kind, _ = mapping[src]
            if kind == "unmatched":
                village = title_keep(src)
                district = "Tiruvannamalai"
        indent = line[: len(line) - len(line.lstrip())]
        out_lines.append(indent + emit_customer_tuple(fields, village, district) + ending)
        nsub += 1

    CUSTOMER_SQL.write_text("".join(out_lines), encoding="utf-8")
    print(f"Rewrote {nsub} customer rows in {CUSTOMER_SQL.name}")

    print("Customers by kind:", dict(customers_by_kind))
    print("Spellings by kind:", dict(stats))
    print("Top official mappings:")
    for (village, district), sources in sorted(official_groups.items(), key=lambda kv: -sum(unique[s] for s in kv[1]))[:15]:
        print(f"  {sum(unique[s] for s in sources):5} {village} / {district}")
    print("Top hamlets:")
    for (village, district), n in hamlet_counts.most_common(10):
        print(f"  {n:5} {village} / {district}")
    print("Top unmatched:")
    for row in unmatched_rows[:15]:
        print(f"  {row[0]:5} {row[1]}")


if __name__ == "__main__":
    main()
