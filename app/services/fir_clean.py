"""
fir_clean.py — Deterministic FIR data cleaners for Antar Lab (Phase L1.1).

Pure functions with no database dependencies, covering:
1. canonical_stage: Raw FIR_Stage text -> (CaseStatusName, CaseStatusID)
2. parse_act_section: Statute text -> list of {"order", "act_raw", "act_code", "section"}
3. clean_coords: (Latitude, Longitude) -> (clean_lat, clean_lon, reason)
4. signature: 13-field deduplication key -> SHA-1 hex digest
"""

from __future__ import annotations

import difflib
import hashlib
import re
from typing import Any, Mapping

# ── 1. CaseStatusMaster mappings (13 canonical statuses) ──────────────────────
STATUS_MASTER: dict[int, str] = {
    1: "Pending Trial",
    2: "False Case",
    3: "Traced",
    4: "Dis/Acq",
    5: "Under Investigation",
    6: "Undetected",
    7: "Transferred - Under Investigation",
    9: "Compounded",
    11: "Convicted",
    12: "Abated",
    15: "Other Disposal",
    23: "Un Traced",
    226: "BoundOver",
}

CANONICAL_NAME_MAP: dict[str, tuple[str, int]] = {
    name.strip().upper(): (name, sid) for sid, name in STATUS_MASTER.items()
}

# Hand-written alias table for common variations and abbreviations
STAGE_ALIASES: dict[str, tuple[str, int]] = {
    "DIS / ACQ": ("Dis/Acq", 4),
    "DIS-ACQ": ("Dis/Acq", 4),
    "DIS/ACQ": ("Dis/Acq", 4),
    "ACQUITTED": ("Dis/Acq", 4),
    "DISCHARGED": ("Dis/Acq", 4),
    "DISPOSAL": ("Other Disposal", 15),
    "OTHER DISPOSALS": ("Other Disposal", 15),
    "PENDING TRIAL": ("Pending Trial", 1),
    "PT": ("Pending Trial", 1),
    "UNDER INVESTIGATION": ("Under Investigation", 5),
    "UI": ("Under Investigation", 5),
    "U.I": ("Under Investigation", 5),
    "U.I.": ("Under Investigation", 5),
    "BOUND OVER": ("BoundOver", 226),
    "BOUNDOVER": ("BoundOver", 226),
    "UNTRACED": ("Un Traced", 23),
    "UN TRACED": ("Un Traced", 23),
    "FALSE": ("False Case", 2),
    "FALSE CASE": ("False Case", 2),
    "TRACED": ("Traced", 3),
    "CONVICTED": ("Convicted", 11),
    "UNDETECTED": ("Undetected", 6),
    "COMPOUNDED": ("Compounded", 9),
    "ABATED": ("Abated", 12),
}


def canonical_stage(raw: str | None) -> tuple[str, int | None]:
    """
    Map raw FIR_Stage string (343 variations in extract) to canonical
    (CaseStatusName, CaseStatusID).

    Rule order:
    1. Exact match against canonical names (case-insensitive, trimmed)
    2. Exact match against alias table
    3. Prefix check: starts with 'TRANSFER' -> ('Transferred - Under Investigation', 7)
    4. difflib close match with cutoff >= 0.85
    5. Fallback: ('Other Disposal', 15)
    """
    if not raw or not str(raw).strip() or str(raw).strip().lower() == "nan":
        return ("Other Disposal", 15)

    s = " ".join(str(raw).strip().split())
    su = s.upper()

    if su in CANONICAL_NAME_MAP:
        return CANONICAL_NAME_MAP[su]

    if su in STAGE_ALIASES:
        return STAGE_ALIASES[su]

    if su.startswith("TRANSFER"):
        return ("Transferred - Under Investigation", 7)

    # Fuzzy match against the 13 canonical names
    canonical_list = list(CANONICAL_NAME_MAP.keys())
    matches = difflib.get_close_matches(su, canonical_list, n=1, cutoff=0.85)
    if matches:
        return CANONICAL_NAME_MAP[matches[0]]

    return ("Other Disposal", 15)


# ── 2. Official Act Master (138 Acts from KSP Registry) ────────────────────────
# ActCode -> ActDescription (from Act table)
ACT_MASTER: dict[str, str] = {
    "IPC 1860": "IPC 1860",
    "KARNATAKA POLICE ACT, 1963": "KARNATAKA POLICE ACT, 1963",
    "KARNATAKA POLICE ACT 1963": "KARNATAKA POLICE ACT, 1963",
    "KARNATAKA EXCISE ACT, 1965": "KARNATAKA EXCISE ACT, 1965",
    "KARNATAKA EXCISE ACT 1965": "KARNATAKA EXCISE ACT, 1965",
    "PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT 2012": "PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT 2012",
    "POCSO": "PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT 2012",
    "RELIGIOUS INSTITUTIONS (PREVENTION OF MISUSE) ACT, 1988": "RELIGIOUS INSTITUTIONS (PREVENTION OF MISUSE) ACT, 1988",
    "Prohibition of Child Marriage Act 2006": "Prohibition of Child Marriage Act 2006",
    "ANCIENT MONUMENT & ARCH.SITES & REMAINS ACT,1958": "ANCIENT MONUMENT & ARCH.SITES & REMAINS ACT,1958",
    "INFORMATION TECHNOLOGY ACT 2008": "INFORMATION TECHNOLOGY ACT 2008",
    "INFORMATION TECHNOLOGY ACT 2000": "INFORMATION TECHNOLOGY ACT 2008",
    "IT ACT": "INFORMATION TECHNOLOGY ACT 2008",
    "KARNATAKA POLICE (AMENDMENT) ACT, 2021": "KARNATAKA POLICE (AMENDMENT) ACT, 2021",
    "INDIAN MOTOR VEHICLES ACT, 1988": "INDIAN MOTOR VEHICLES ACT, 1988",
    "MOTOR VEHICLES ACT": "INDIAN MOTOR VEHICLES ACT, 1988",
    "IMV ACT": "INDIAN MOTOR VEHICLES ACT, 1988",
    "NARCOTIC DRUGS & PSYCHOTROPIC SUBSTANCES ACT, 1985": "NARCOTIC DRUGS & PSYCHOTROPIC SUBSTANCES ACT, 1985",
    "NDPS ACT": "NARCOTIC DRUGS & PSYCHOTROPIC SUBSTANCES ACT, 1985",
    "ESSENTIAL COMMODITIES ACT, 1955": "ESSENTIAL COMMODITIES ACT, 1955",
    "KARNATAKA OPEN PLACE DISFIGUREMENT ACT 1951 & 1981": "KARNATAKA OPEN PLACE DISFIGUREMENT ACT 1951 & 1981",
    "THE KARNATAKA PREVENTION OF SLAUGHTER AND PRESERVATION OF CA": "THE KARNATAKA PREVENTION OF SLAUGHTER AND PRESERVATION OF CA",
    "PREVENTION OF CRUELTY TO ANIMALS ACT, 1960": "PREVENTION OF CRUELTY TO ANIMALS ACT, 1960",
    "ARMS ACT, 1959": "ARMS ACT, 1959",
    "ARMS ACT": "ARMS ACT, 1959",
    "EXPLOSIVE SUBSTANCES ACT, 1908": "EXPLOSIVE SUBSTANCES ACT, 1908",
    "EXPLOSIVES ACT, 1884": "EXPLOSIVES ACT, 1884",
    "PASSPORT (ENTRY INTO INDIA) ACT, 1920": "PASSPORT (ENTRY INTO INDIA) ACT, 1920",
    "PASSPORTS ACT, 1967": "PASSPORTS ACT, 1967",
    "FOREIGNERS ACT, 1946": "FOREIGNERS ACT, 1946",
    "CINEMATOGRAPH ACT, 1952": "CINEMATOGRAPH ACT, 1952",
    "COPY RIGHT ACT, 1957": "COPY RIGHT ACT, 1957",
    "COTPA 2003": "COTPA 2003",
    "CIGARETTES AND OTHER TOBACCO PRODUCTS ACT 2003": "COTPA 2003",
    "THE SC/ST (PREVENTION OF ATROCITIES) ACT, 1989": "THE SC/ST (PREVENTION OF ATROCITIES) ACT, 1989",
    "SC/ST (POA) ACT": "THE SC/ST (PREVENTION OF ATROCITIES) ACT, 1989",
    "PREVENTION OF CORRUPTION ACT, 1988": "PREVENTION OF CORRUPTION ACT, 1988",
    "KARNATAKA MONEY LENDERS ACT, 1961": "KARNATAKA MONEY LENDERS ACT, 1961",
    "KARNATAKA PROHIBITION OF CHARGING EXORBITANT INTEREST ACT, 2": "KARNATAKA PROHIBITION OF CHARGING EXORBITANT INTEREST ACT, 2",
    "GAMBLING ACT": "KARNATAKA POLICE ACT, 1963",
}

_ACT_NORM_LOOKUP: dict[str, str] = {
    re.sub(r"[^A-Z0-9]", "", k.upper()): v for k, v in ACT_MASTER.items()
}


def _match_act_code(act_raw: str) -> str | None:
    """Match raw act description against official ActCode."""
    s = act_raw.strip().upper()
    if s in ACT_MASTER:
        return ACT_MASTER[s]

    sn = re.sub(r"[^A-Z0-9]", "", s)
    if sn in _ACT_NORM_LOOKUP:
        return _ACT_NORM_LOOKUP[sn]

    # Substring match against known acts
    for code, desc in ACT_MASTER.items():
        if code.upper() in s or s in code.upper():
            return desc

    # difflib match
    candidates = list(ACT_MASTER.keys())
    m = difflib.get_close_matches(act_raw.strip(), candidates, n=1, cutoff=0.75)
    if m:
        return ACT_MASTER[m[0]]

    return None


_SECTION_RUN_RE = re.compile(
    r"^\s*([0-9A-Za-z()/\.\-]+(?:\s*,\s*[0-9A-Za-z()/\.\-]+)*)", re.ASCII
)


def parse_act_section(raw: str | None) -> list[dict[str, Any]]:
    """
    Parse an ActSection string into structured entries.
    Example input:
    'PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT 2012 U/s: 12 IPC 1860 U/s: 306,363 PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT 2012 U/s: 18 '

    Returns list of dicts:
    [
      {"order": 0, "act_raw": "...", "act_code": "...", "section": "12"},
      {"order": 1, "act_raw": "IPC 1860", "act_code": "IPC 1860", "section": "306"},
      {"order": 1, "act_raw": "IPC 1860", "act_code": "IPC 1860", "section": "363"},
      {"order": 2, "act_raw": "...", "act_code": "...", "section": "18"},
    ]
    """
    if not raw or not str(raw).strip() or str(raw).strip().lower() == "nan":
        return []

    text = str(raw).strip()
    pieces = re.split(r"(?i)\s*u/s:\s*", text)
    if len(pieces) < 2:
        # Fallback when no U/s: is present
        act_code = _match_act_code(text)
        return [{"order": 0, "act_raw": text, "act_code": act_code, "section": ""}]

    results: list[dict[str, Any]] = []
    current_act = pieces[0].strip()

    for i, piece in enumerate(pieces[1:]):
        m = _SECTION_RUN_RE.match(piece)
        if m:
            sec_run = m.group(1).strip()
            next_act = piece[m.end():].strip()
        else:
            sec_run = ""
            next_act = piece.strip()

        act_clean = " ".join(current_act.split()).rstrip(",")
        act_code = _match_act_code(act_clean)

        raw_sections = [s.strip() for s in sec_run.split(",") if s.strip()]
        if not raw_sections:
            results.append({
                "order": i,
                "act_raw": act_clean,
                "act_code": act_code,
                "section": "",
            })
        else:
            for sec in raw_sections:
                results.append({
                    "order": i,
                    "act_raw": act_clean,
                    "act_code": act_code,
                    "section": sec,
                })

        current_act = next_act

    return results


# ── 3. Spatial Coordinate Cleaning ────────────────────────────────────────────
LAT_MIN, LAT_MAX = 11.5, 18.5
LON_MIN, LON_MAX = 74.0, 78.6


def clean_coords(
    lat: Any, lon: Any
) -> tuple[float | None, float | None, str]:
    """
    Inspect raw coordinates and classify them:
    - 'ok': in Karnataka bounding box (11.5-18.5 N, 74.0-78.6 E)
    - 'swapped': lat and lon reversed but within bounds when swapped
    - 'outside': numeric coordinates outside Karnataka box
    - 'missing': None, NaN, 0.0, or unparseable
    """
    if lat is None or lon is None:
        return (None, None, "missing")

    import math
    try:
        flat = float(str(lat).strip())
        flon = float(str(lon).strip())
    except (ValueError, TypeError):
        return (None, None, "missing")

    if math.isnan(flat) or math.isnan(flon) or flat == 0.0 or flon == 0.0:
        return (None, None, "missing")

    # Regular Karnataka box
    if LAT_MIN <= flat <= LAT_MAX and LON_MIN <= flon <= LON_MAX:
        return (round(flat, 6), round(flon, 6), "ok")

    # Swapped coordinates
    if LON_MIN <= flat <= LON_MAX and LAT_MIN <= flon <= LAT_MAX:
        return (round(flon, 6), round(flat, 6), "swapped")

    return (None, None, "outside")


# ── 4. De-duplication Signature ───────────────────────────────────────────────
_SIGNATURE_FIELDS = [
    "District_Name",
    "UnitName",
    "FIR_YEAR",
    "FIR_MONTH",
    "FIR_Day",
    "FIR_Type",
    "CrimeGroup_Name",
    "CrimeHead_Name",
    "KGID",
    "Beat_Name",
    "Village_Area_Name",
    "Accused_Count",
    "Place_of_Offence",
]

_INT_FIELDS = {"FIR_YEAR", "FIR_MONTH", "FIR_Day", "Accused_Count"}


def _norm_field(v: Any, is_int: bool = False) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return ""
    if is_int:
        try:
            return str(int(float(s)))
        except (ValueError, TypeError):
            return s.upper()
    return " ".join(s.split()).upper()


def signature(row: Mapping[str, Any]) -> str:
    """
    Generate SHA-1 signature over 13 key fields for deduplication.
    Normalized with str(v).strip().upper() and integers with int(float(v)).
    Does NOT include ActSection or FIR_Stage.
    """
    parts = []
    for f in _SIGNATURE_FIELDS:
        is_int = f in _INT_FIELDS
        # Handle field name differences between CSV ('FIR Type', 'Accused Count')
        # and DB ('FIR_Type', 'Accused_Count')
        v = row.get(f)
        if v is None:
            spaced = f.replace("_", " ")
            v = row.get(spaced)
        parts.append(_norm_field(v, is_int=is_int))

    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
