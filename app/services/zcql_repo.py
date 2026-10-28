"""
Antar — ZCQL Template Repository (the anti-hallucination heart)
===================================================================
The LLM NEVER writes SQL. It only picks a template_id + params. The backend owns
the query. This module is the whitelist.

Design: each template is a pure function `params -> QuerySpec`. A QuerySpec is a
structured, backend-agnostic description of a query. Two interpreters consume it:
  • render_zcql(spec)      → a ZCQL string for Catalyst Data Store (production)
  • run_local(spec, world) → filters the seed JSON in memory (dev/test; see zcql_local.py)

Why a spec instead of raw strings: one definition, two backends, zero SQL parsing,
injection-safe (params validated by Pydantic; values escaped on render). Reproducible
= explainable (M9): same template_id + params ⇒ same rows ⇒ same answer.

To add a template: add a TEMPLATES entry with a Pydantic param model + a builder fn.
[VERIFY] exact ZCQL dialect (function names, date literals, LIMIT/OFFSET) against
docs.catalyst.zoho.com on first live run — the local executor is the dev oracle until then.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from typing import Annotated, Any, Callable, Literal, Optional

from pydantic import BaseModel, BeforeValidator, Field, field_validator
from app.core.db_path import registry_connect


def _as_str_list(v: Any) -> list[str]:
    """Coerce the LLM's loose output into a list[str]: a bare string → [string],
    None → [], a comma-string → split. (LLMs often return 'robbery' not ['robbery'].)"""
    if v is None:
        return []
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [str(v)]


# A list[str] field that leniently accepts a bare string from the LLM.
StrList = Annotated[list[str], BeforeValidator(_as_str_list)]


def _as_crime_list(v: Any) -> list[str]:
    """Coerce + normalize crime types (any language/synonym → canonical English)."""
    return normalize_crime_types(_as_str_list(v))


# crime_types field: bare string OK, and Kannada/synonyms map to canonical English.
CrimeTypeList = Annotated[list[str], BeforeValidator(_as_crime_list)]


def _as_months(v: Any) -> int:
    """Coerce the LLM's time spec into a month COUNT for trend windows. Accepts an int,
    a numeric string, or a relative period keyword the LLM tends to emit INSTEAD (e.g.
    'last_3_months', 'this_year') — T3 has no `period` field, so the model sometimes stuffs
    the period into `months`. Pulls a number out of 'last_4_months' etc. Falls back to 12.
    (Same philosophy as dates: never trust the LLM's format — normalize in the backend.)"""
    if isinstance(v, bool):
        return 12                                   # bool is an int subclass — ignore it
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not s:
        return 12
    period_months = {
        "this_month": 1, "current_month": 1, "last_month": 1, "previous_month": 1,
        "this_week": 1, "last_week": 1, "past_week": 1,
        "last_3_months": 3, "last_three_months": 3, "past_3_months": 3, "quarter": 3,
        "last_6_months": 6, "past_6_months": 6, "half_year": 6,
        "this_year": 12, "current_year": 12, "last_year": 12, "previous_year": 12,
    }
    if s in period_months:
        return period_months[s]
    m = re.search(r"\d+", s)                         # 'last_4_months' / '4_months' / '4'
    return int(m.group()) if m else 12


# months field: accepts an int, a numeric string, or a period keyword the LLM may emit.
Months = Annotated[int, BeforeValidator(_as_months)]

# ── Known dimension values (validate params against these) ───────────────────
# Mirror of the seed generator's zones (keep in sync with app/seeds/generator.py).
BENGALURU_ZONES = ["Rajajinagar", "Gandhinagar", "Jayanagar", "Malleshwaram",
                   "Indiranagar", "Whitefield", "Yeshwanthpur", "Banashankari",
                   "KR Puram", "Hebbal"]
DISTRICT_ZONES = ["Mysuru-Devaraja", "Mysuru-Nazarbad", "Hubballi", "Belagavi",
                  "Mangaluru", "Kalaburagi"]
ALL_ZONES = BENGALURU_ZONES + DISTRICT_ZONES

# Statewide police units that register FIRs under their own name in the district column.
# They are not places: a rise in "CID" is a rise in what one unit registered across the
# state, and no beat can be sent to it. Screens that rank or forecast areas list them
# apart. (K.G.F is a police district and is an area.)
POLICE_UNITS = {
    "CID": "Criminal Investigation Department, statewide",
    "Coastal Security Police": "Coastal Security Police, along the coast",
    "Karnataka Railways": "Railway Police, on railway premises and trains",
    "ISD Bengaluru": "Internal Security Division",
}


def is_police_unit(name: str | None) -> bool:
    return (name or "").strip() in POLICE_UNITS

# Convenience regions → concrete zones — expanded to real KSP districts
REGIONS = {
    # Bengaluru crime lives under BOTH district-level labels (real KSP data) AND the
    # synthetic sub-zones — expand to all so "in Bengaluru" catches everything (WI-4 fix).
    "Bengaluru": ["Bengaluru City", "Bengaluru Dist", "ISD Bengaluru"] + BENGALURU_ZONES,
    "Bengaluru North": ["Rajajinagar", "Malleshwaram", "Yeshwanthpur", "Hebbal"],
    "Bengaluru South": ["Jayanagar", "Banashankari", "Indiranagar", "Whitefield"],
    "Bangalore": ["Bengaluru City", "Bengaluru Dist", "ISD Bengaluru"] + BENGALURU_ZONES,
    # A city name means its real police districts. "Mangaluru", "Hubballi" and "Belagavi"
    # are also seeded localities with ~150 rows each; matched alone they shadowed the real
    # districts (Mangaluru City holds 15,743 FIRs), so "murders in Mangaluru" counted the
    # seeded locality only. The localities stay in, so nothing that matched before is lost.
    "Mysore": ["Mysuru City", "Mysuru Dist", "Mysuru-Devaraja", "Mysuru-Nazarbad"],
    "Mysuru": ["Mysuru City", "Mysuru Dist", "Mysuru-Devaraja", "Mysuru-Nazarbad"],
    "Hubli": ["Hubballi Dharwad City", "Dharwad", "Hubballi"],
    "Hubballi": ["Hubballi Dharwad City", "Hubballi"],
    "Mangalore": ["Mangaluru City", "Dakshina Kannada", "Mangaluru"],
    "Mangaluru": ["Mangaluru City", "Mangaluru"],
    "Belagavi": ["Belagavi City", "Belagavi Dist", "Belagavi"],
    "Belgaum": ["Belagavi City", "Belagavi Dist", "Belagavi"],
    "Kalaburagi": ["Kalaburagi"],
    # Other spellings officers use for districts on the register
    "Vijayapura": ["Vijayapur"], "Bijapur": ["Vijayapur"],
    "Gulbarga": ["Kalaburagi", "Kalaburagi City"],
    "Davangere": ["Davanagere"], "Shimoga": ["Shivamogga"], "Tumkur": ["Tumakuru"],
    "Bellary": ["Ballari"], "Chikkaballapura": ["Chickballapura"], "Chikballapur": ["Chickballapura"],
    "Chikmagalur": ["Chikkamagaluru"], "Chamarajanagara": ["Chamarajanagar"],
    "Coorg": ["Kodagu"], "Madikeri": ["Kodagu"], "Karwar": ["Uttara Kannada"],
    "Hubli Dharwad": ["Hubballi Dharwad City"], "Hubballi Dharwad": ["Hubballi Dharwad City"],
    "Kolar Gold Fields": ["K.G.F"], "KGF": ["K.G.F"],
    "Udupi": ["Udupi"],
    "Ballari": ["Ballari"],
    "Shivamogga": ["Shivamogga"],
    "Tumakuru": ["Tumakuru"],
}

# Real KSP CrimeGroup_Name values from FIR_Details_Data.csv + synthetic types
CRIME_TYPES = [
    "THEFT", "ROBBERY", "CASES OF HURT", "CHEATING", "MURDER",
    "NARCOTICS", "MOTOR VEHICLE ACCIDENTS NON-FATAL", "MISSING PERSON",
    "KARNATAKA POLICE ACT 1963", "Karnataka State Local Act",
    " CYBER CRIME", "MOTOR VEHICLE ACCIDENTS FATAL", "BURGLARY",
    "KIDNAPPING AND ABDUCTION", "ASSAULT ON WOMEN", "DACOITY",
    "CHAIN_SNATCHING", "VEHICLE_THEFT", "CYBERCRIME", "DOMESTIC_VIOLENCE",
    "RIOTING", "ASSAULT", "CHEATING_FRAUD"
]

# Crimes against women — the exact CrimeGroup_Name values present in the FIR data, so
# "crimes against women 2023 + top districts?" filters on real rows.
WOMEN_CRIMES = [
    "ASSAULT ON WOMEN", "ASSAULT OR USE OF CRIMINAL FORCE TO DISROBE WOMAN",
    "CRIMES RELATED TO WOMEN", "CRUELTY BY HUSBAND", "DOWRY DEATHS", "IMMORAL TRAFFIC",
    "INSULTING MODESTY OF WOMEN (EVE TEASING)", "MOLESTATION", "POCSO", "RAPE",
    "domestic_violence",
]
CRIME_TYPES += [c for c in WOMEN_CRIMES if c not in CRIME_TYPES]

# Map the many ways a user/LLM may name a crime → canonical KSP CrimeGroup_Name
CRIME_TYPE_SYNONYMS = {
    "theft": "THEFT", "stealing": "THEFT", "larceny": "THEFT",
    "chain snatching": "CHAIN_SNATCHING", "chain_snatching": "CHAIN_SNATCHING",
    "snatching": "CHAIN_SNATCHING", "vehicle theft": "VEHICLE_THEFT",
    "vehicle_theft": "VEHICLE_THEFT", "auto theft": "VEHICLE_THEFT",
    "ಕಳ್ಳತನ": "THEFT", "ಕಲ್ಲತನ": "THEFT", "kalattana": "THEFT", "kallatana": "THEFT",
    "robbery": "ROBBERY", "darode": "ROBBERY", "ದರೋಡೆ": "ROBBERY",
    "dacoity": "DACOITY", "dacoit": "DACOITY",
    "burglary": "BURGLARY", "housebreaking": "BURGLARY",
    "assault": "ASSAULT", "hurt": "CASES OF HURT", "fight": "CASES OF HURT",
    "murder": "MURDER", "killing": "MURDER", "homicide": "MURDER",
    "ಕೊಲೆ": "MURDER", "kole": "MURDER",
    "cheating": "CHEATING", "fraud": "CHEATING",
    "cyber": " CYBER CRIME", "cybercrime": " CYBER CRIME", "cyber crime": " CYBER CRIME", "online fraud": " CYBER CRIME",
    "narcotics": "NARCOTICS", "drugs": "NARCOTICS", "ndps": "NARCOTICS",
    "kidnapping": "KIDNAPPING AND ABDUCTION", "abduction": "KIDNAPPING AND ABDUCTION",
    "missing": "MISSING PERSON", "missing person": "MISSING PERSON",
    "accident": "MOTOR VEHICLE ACCIDENTS NON-FATAL",
    "road accident": "MOTOR VEHICLE ACCIDENTS NON-FATAL",
    "fatal accident": "MOTOR VEHICLE ACCIDENTS FATAL",
    "domestic_violence": "DOMESTIC_VIOLENCE",
    "rioting": "RIOTING",
    "cheating_fraud": "CHEATING_FRAUD",
    # ── Kannada crime terms (self-healing RAG · KN input) ──
    "ಸರಗಳ್ಳತನ": "CHAIN_SNATCHING", "ಸರ ಕಳ್ಳತನ": "CHAIN_SNATCHING", "ಸರಗಳವಿ": "CHAIN_SNATCHING",
    "ಮನೆಗಳ್ಳತನ": "BURGLARY", "ಕನ್ನ": "BURGLARY",
    "ವಾಹನ ಕಳ್ಳತನ": "VEHICLE_THEFT",
    "ಸೈಬರ್": " CYBER CRIME", "ಸೈಬರ್ ಅಪರಾಧ": " CYBER CRIME",
    "ವಂಚನೆ": "CHEATING", "ಮೋಸ": "CHEATING",
    "ಮಾದಕ": "NARCOTICS", "ಮಾದಕ ವಸ್ತು": "NARCOTICS",
    "ಅಪಹರಣ": "KIDNAPPING AND ABDUCTION",
}


CRIME_TYPE_SYNONYMS.update({
    "rape": "RAPE", "molestation": "MOLESTATION", "pocso": "POCSO",
    "dowry": "DOWRY DEATHS", "dowry death": "DOWRY DEATHS",
    "eve teasing": "INSULTING MODESTY OF WOMEN (EVE TEASING)",
    "cruelty by husband": "CRUELTY BY HUSBAND", "immoral traffic": "IMMORAL TRAFFIC",
    "ಅತ್ಯಾಚಾರ": "RAPE", "ವರದಕ್ಷಿಣೆ": "DOWRY DEATHS", "ಲೈಂಗಿಕ ಕಿರುಕುಳ": "MOLESTATION",
})


# ── Crime vocabulary, grounded in the data ───────────────────────────────────────
# The hand-written CRIME_TYPES above covers ~33 names. The FIR registry holds 142
# distinct CrimeGroup_Name values, so a question about any of the other 109 used to
# resolve to nothing — and an empty crime filter means "all crimes", so the officer got
# a confident answer to a DIFFERENT question. Worse, a name like "BURGLARY" exists in
# the vocabulary but matches only 837 seeded rows while the real burglary FIRs are
# filed under "BURGLARY - DAY" / "BURGLARY - NIGHT" (26,442 rows) and were invisible.
#
# So the vocabulary is now read FROM the registry, spelling variants are merged, and a
# handful of families map one everyday word onto the several official names it covers.

def _crime_key(s: Any) -> str:
    """Comparison key: case, '&' vs 'and', punctuation and spacing all stop mattering.

    Only punctuation is stripped — \\w keeps Kannada (and any other script) intact. An
    A-Z-only filter would flatten every Kannada synonym to the same empty key and make
    them collide, so ಕಳ್ಳತನ would resolve to whichever alias happened to be added last.
    """
    t = str(s or "").strip().upper().replace("&", " AND ")
    t = re.sub(r"[^\w ]+", " ", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=1)
def data_crime_groups() -> tuple[str, ...]:
    """Every CrimeGroup_Name actually present in the FIR registry."""
    try:
        import sqlite3
        # db_path, NOT zcql_local: zcql_local imports this module, so reaching for its
        # DB_PATH while this module is still initialising is a circular import. It failed
        # silently and left the vocabulary empty.
        from app.core.db_path import DB_PATH
        con = registry_connect(str(DB_PATH))      # not a file: URI — a Windows path's
        try:                                     # backslashes are not URI-safe
            return tuple(r[0] for r in con.execute(
                "SELECT DISTINCT CrimeGroup_Name FROM FIRs "
                "WHERE CrimeGroup_Name IS NOT NULL AND TRIM(CrimeGroup_Name) <> ''") if r[0])
        finally:
            con.close()
    except Exception:
        return ()


# One everyday word → every official name it legitimately covers. Only families where
# the wider match is unambiguously what an officer means; nothing is merged on a guess.
_CRIME_FAMILIES: dict[str, tuple[str, ...]] = {
    "BURGLARY": ("BURGLARY",),                       # + " - DAY" / " - NIGHT"
    "NARCOTICS": ("NARCOTIC",),                      # + the full NDPS name
    "RIOTING": ("RIOT",),
    "SCHEDULED CASTE AND THE SCHEDULED TRIBES": ("SCHEDULED CASTE",),
}


@lru_cache(maxsize=1)
def _concept_map() -> dict[str, tuple[str, ...]]:
    """canonical concept → the concrete CrimeGroup_Name values it selects."""
    groups = data_crime_groups()
    by_key: dict[str, list[str]] = {}
    for g in groups:                       # merge pure spelling/case/spacing variants
        by_key.setdefault(_crime_key(g), []).append(g)

    # When the registry holds several spellings of one group ("CHAIN_SNATCHING" and
    # "chain_snatching"), the canonical form is the one the hand-written vocabulary
    # already uses — callers and tests match on that exact string.
    legacy = {_crime_key(t): t.strip() for t in CRIME_TYPES if str(t).strip()}
    concepts: dict[str, tuple[str, ...]] = {}
    for key, vals in by_key.items():
        canon = legacy.get(key) or max(vals, key=len).strip() or vals[0]
        concepts[canon] = tuple(vals)

    # widen the families over whatever the registry actually spells
    for canon, prefixes in _CRIME_FAMILIES.items():
        hit = [g for g in groups
               if any(_crime_key(g).startswith(_crime_key(p)) for p in prefixes)]
        if hit:
            concepts[canon] = tuple(dict.fromkeys(hit))

    # keep every legacy vocabulary entry addressable, even with no rows behind it
    for t in CRIME_TYPES:
        concepts.setdefault(t.strip() or t, (t,))
    return concepts


@lru_cache(maxsize=1)
def _lookup() -> dict[str, str]:
    """normalised user term → canonical concept."""
    out: dict[str, str] = {}

    def put(raw: str, concept: str, *, overwrite: bool) -> None:
        k = _crime_key(raw)
        if not k:                       # an empty key would collide with every other one
            return
        if overwrite or k not in out:
            out[k] = concept

    for concept in _concept_map():
        put(concept, concept, overwrite=False)
    for raw, canon in CRIME_TYPE_SYNONYMS.items():          # hand-written aliases win
        put(raw, _resolve_legacy(canon), overwrite=True)
    for t in CRIME_TYPES:
        put(t, _resolve_legacy(t), overwrite=False)
    return out


def _resolve_legacy(name: str) -> str:
    """A legacy vocabulary name → the concept that owns it (e.g. BURGLARY → the family)."""
    k = _crime_key(name)
    for concept in _concept_map():
        if _crime_key(concept) == k:
            return concept
    return name


def _match_one(raw: str) -> Optional[str]:
    term = str(raw or "").strip()
    if not term:
        return None
    lut = _lookup()
    key = _crime_key(term)
    if not key:
        alt = CRIME_TYPE_SYNONYMS.get(term.lower()) or CRIME_TYPE_SYNONYMS.get(term)
        return _resolve_legacy(alt) if alt else None
    if key in lut:
        return lut[key]
    if key.endswith("S") and key[:-1] in lut:            # "robberies" handled by synonyms
        return lut[key[:-1]]
    if (key + "S") in lut:
        return lut[key + "S"]
    alt = CRIME_TYPE_SYNONYMS.get(term.lower()) or CRIME_TYPE_SYNONYMS.get(term)
    if alt:
        return _resolve_legacy(alt)
    und = term.lower().replace(" ", "_")
    if _crime_key(und) in lut:
        return lut[_crime_key(und)]
    return None


def resolve_crime_types(values: list[str]) -> tuple[list[str], list[str]]:
    """(concepts we matched, terms we could NOT match).

    The second list is the one that matters: an unmatched crime term must NEVER be
    silently discarded, because a dropped filter turns "kidnapping in Mysuru" into
    "every crime in Mysuru" and the answer looks perfectly confident.
    """
    ok, bad = [], []
    for v in values or []:
        m = _match_one(v)
        (ok if m else bad).append(m or str(v).strip())
    return list(dict.fromkeys(ok)), list(dict.fromkeys(b for b in bad if b))


def normalize_crime_types(values: list[str]) -> list[str]:
    """Map free-form crime names (any language) to canonical concepts; drop unknowns.

    Kept for callers that only want the matches; use resolve_crime_types() when you
    need to know that something failed to match.
    """
    return resolve_crime_types(values)[0]


def expand_crime_types(concepts: list[str]) -> list[str]:
    """Concepts → the concrete CrimeGroup_Name values to filter on.

    Filters go through this so "burglary" reaches BURGLARY, BURGLARY - DAY and
    BURGLARY - NIGHT, while the concept stays clean for display in the answer.
    """
    cmap = _concept_map()
    out: list[str] = []
    for c in concepts or []:
        vals = cmap.get(c)
        if vals is None:
            m = _match_one(c)
            vals = cmap.get(m, (c,)) if m else (c,)
        out.extend(vals)
    return list(dict.fromkeys(out))


@lru_cache(maxsize=1)
def _real_crime_groups() -> frozenset:
    """Crime groups that have at least one row of the real KSP record."""
    import sqlite3
    from app.core.db_path import get_db_path
    try:
        con = sqlite3.connect(f"file:{get_db_path()}?mode=ro", uri=True, timeout=10)
        try:
            return frozenset(r[0] for r in con.execute(
                "SELECT DISTINCT crime_type FROM FIRs WHERE is_synthetic_row = 0"))
        finally:
            con.close()
    except Exception:
        return frozenset()


def demo_only_crime_types(concepts: list[str]) -> list[str]:
    """The named crime types that exist ONLY in seeded demonstration rows. The real
    register has no "vehicle theft" or "chain snatching" head; a statewide figure for one
    is a count of demonstration records and the answer has to say so."""
    real = _real_crime_groups()
    if not real:
        return []                       # could not tell: say nothing rather than guess
    return [c for c in concepts or [] if not any(v in real for v in expand_crime_types([c]))]


# Make every concept the registry knows about nameable by the template selector, so the
# LLM can pick "ATTEMPT TO MURDER" or "CRIMINAL TRESPASS" instead of guessing a near-miss.
CRIME_TYPES += [c for c in _concept_map() if c not in CRIME_TYPES]


# ── Crime sub-headings (CrimeHead_Name) ──────────────────────────────────────────────
# The register files a case under a crime GROUP (Theft) and a sub-heading under it
# (Of Automobiles - Of Two Wheelers, House Theft, Extortion ...). Officers ask in the
# sub-heading's words: "two-wheeler thefts", "extortion cases", "sand theft". None of
# those is a group, so they matched nothing and the question was answered for all crime.
# Each phrase maps to the exact sub-heading values on the register.
HEAD_ALIASES: list[tuple[str, tuple[str, ...]]] = [
    (r"two[- ]?wheelers?|bikes?|motor ?cycles?|motor ?bikes?|scooters?",
     ("Of Automobiles - Of Two Wheelers",)),
    (r"three[- ]?wheelers?|auto[- ]?rickshaws?|autos",
     ("Of Automobiles - Of Three Wheelers",)),
    (r"four[- ]?wheelers?|cars?|jeeps?", ("Of Automobiles - Of Cars/Jeeps",)),
    (r"vehicle (?:parts|accessories)|accessories of (?:motor )?vehicles?", ("Of Accessories Of Motor Vehicle",)),
    (r"house[- ]?theft|house[- ]?break(?:ing|ins?)?|home theft", ("House Theft",)),
    (r"residential(?: premises)?|homes?", ("At Residential Premises",)),
    (r"commercial(?: places?| premises| establishments?)?|shops?|establishments?",
     ("At Commercial Places / Establishments",)),
    (r"temples?", ("Temple Theft",)),
    (r"jewell?e?ry|gold ornaments?|gold", ("Jewellery",)),
    (r"sand", ("Of Sand",)),
    (r"cattle|cows?|livestock", ("Of Cattle",)),
    (r"cash", ("Cash",)),
    (r"extortion|extort\w*", ("Extortion", "To Extort Property")),
    (r"servant theft|domestic servants?", ("Servant Theft",)),
    (r"electronic goods|electronics", ("Electronic Goods (Radio,TV,VCR,ACs,Office Automation Equipments)",)),
    (r"matka", ("Gambling - Matka (78 Class C)",)),
    (r"street gambling", ("Street Gambling (87)",)),
    (r"betting", ("Betting",)),
    (r"national highways?", ("National Highways",)),
    (r"state highways?", ("State Highways",)),
    (r"excise|illicit liquor|arrack", ("Karnataka Excise Act 1965",)),
    (r"cow slaughter", ("Karnataka Cow Slaughter Act",)),
    (r"illegal mining|mining|minerals?", ("Mmdr (Mines & Minerals Regulation Development) Act 1957",
                                          "Karnataka Minor Mineral Consistent Rule 1994")),
    (r"missing girls?", ("Missing-Girl",)),
    (r"missing boys?", ("Missing-Boy",)),
]
# "vehicle theft" is Theft of an automobile on the real register. The seeded VEHICLE_THEFT
# label holds ~250 demonstration rows; asked by its name it answered 175 FIRs for
# Bengaluru City against the ~19,000 two-wheeler thefts registered there.
VEHICLE_HEADS = ("Of Automobiles - Of Two Wheelers", "Of Automobiles - Of Three Wheelers",
                 "Of Automobiles - Of Cars/Jeeps")


# Concepts the real register files as a sub-heading of a broader group, and the seeded
# demonstration rows file under a label of their own (with no sub-heading). Asked by name,
# both must count: the real cases (Robbery › Chain Snatching, 3,253 FIRs) and the seeded
# ones (chain_snatching, 318). Before, only the seeded label matched.
HEAD_BACKED: dict[str, tuple[str, tuple[str, ...]]] = {
    "CHAIN_SNATCHING": ("ROBBERY", ("Chain Snatching",)),
    "VEHICLE_THEFT": ("THEFT", VEHICLE_HEADS),
}


def resolve_heads(low: str) -> list[str]:
    """Sub-headings named in a (lower-cased) question, as register values."""
    out: list[str] = []
    for rx, heads in HEAD_ALIASES:
        if re.search(r"(?<![a-z])(?:" + rx + r")(?![a-z])", low or ""):
            out.extend(heads)
    return list(dict.fromkeys(out))


def head_label(head: str) -> str:
    """A sub-heading as an officer says it: "Of Automobiles - Of Two Wheelers" → "two-wheelers"."""
    h = " ".join(str(head or "").split())
    for k, v in {"Of Automobiles - Of Two Wheelers": "two-wheelers", "Of Automobiles - Of Three Wheelers": "three-wheelers",
                 "Of Automobiles - Of Cars/Jeeps": "cars and jeeps", "Of Accessories Of Motor Vehicle": "vehicle accessories",
                 "At Residential Premises": "homes", "At Commercial Places / Establishments": "shops and establishments",
                 "Electronic Goods (Radio,TV,VCR,ACs,Office Automation Equipments)": "electronic goods",
                 "Gambling - Matka (78 Class C)": "matka gambling", "Street Gambling (87)": "street gambling",
                 "Mmdr (Mines & Minerals Regulation Development) Act 1957": "mining (MMDR Act)",
                 "Other Items Not Included Above": "other items",
                 "Extortion": "extortion", "To Extort Property": "extortion",
                 "To Extort Confession": "extortion of a confession"}.items():
        if h.lower() == k.lower():
            return v
    h = re.sub(r"^(?:Of|At|In)\s+", "", h)
    # An Act keeps its capitals ("Karnataka Excise Act 1965"); anything else reads in lower case.
    return h if re.search(r"\bAct\b", h) else h.lower()


# ── Police stations ──────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def station_index() -> dict[str, list[tuple[str, str]]]:
    """Station base name (lower case, without "PS") → [(station, district)].

    "Koramangala" is no district, so "thefts in Koramangala" was answered for all of
    Karnataka. It is a police station (Koramangala PS, Bengaluru City, 2,104 FIRs)."""
    out: dict[str, list[tuple[str, str]]] = {}
    try:
        import sqlite3
        from app.core.db_path import DB_PATH
        con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            rows = con.execute("SELECT station, MIN(district_norm), COUNT(*) FROM FIRs "
                               "WHERE station IS NOT NULL AND TRIM(station) <> '' GROUP BY station").fetchall()
        finally:
            con.close()
    except Exception:
        return out
    for st, dist, n in rows:
        name = " ".join(str(st).split())
        base = re.sub(r"\s+(?:police station|ps)$", "", name, flags=re.I).strip().lower()
        if len(base) >= 4 and n >= 20:
            out.setdefault(base, []).append((name, str(dist or "")))
    return out


_STATION_KINDS = ("traffic", "cen", "women", "rural", "town", "east", "west", "north", "south", "extension")


def resolve_stations(text: str, districts: Optional[list[str]] = None) -> list[str]:
    """Police stations named in a question.

    "Koramangala PS", "Jayanagar police station" or a bare "Koramangala" (when it names
    no district). A base name matches its law-and-order station; the Traffic / CEN /
    Women stations of the same name only when that word is said too. With districts
    named, a station name shared across districts (Vijayanagar) keeps the one asked."""
    low = " ".join((text or "").lower().split())
    idx = station_index()
    if not idx or not low:
        return []
    want_kind = [k for k in _STATION_KINDS if re.search(r"(?<![a-z])" + k + r"(?![a-z])", low)]
    found: list[str] = []
    for base, items in idx.items():
        root = base
        kind = next((k for k in _STATION_KINDS if root.endswith(" " + k)), None)
        if kind:
            root = root[: -len(kind) - 1]
            if kind not in want_kind:
                continue
        if not re.search(r"(?<![a-z])" + re.escape(root) + r"(?![a-z])", low):
            continue
        for name, dist in items:
            if districts and dist and not any(dist.lower() == d.lower() or d.lower() in dist.lower() for d in districts):
                continue
            found.append(name)
    # the longest name wins its words: "Whitefield CEN Crime PS" over "Whitefield PS" when CEN was said
    return list(dict.fromkeys(found))


def stations_district(stations: list[str]) -> list[str]:
    idx = station_index()
    by = {n.lower(): d for items in idx.values() for n, d in items}
    return list(dict.fromkeys(by[s.lower()] for s in stations if s.lower() in by and by[s.lower()]))


def resolve_zones(names: list[str]) -> list[str]:
    """Expand region names to concrete zones; pass through exact zone names."""
    out: list[str] = []
    for n in names or []:
        if n in REGIONS:
            out.extend(REGIONS[n])
        else:
            out.append(n)
    return list(dict.fromkeys(out))  # de-dup, keep order


# Relative time periods the LLM can name (it must NOT compute absolute dates — it's bad at it).
PERIODS = ["today", "yesterday", "this_week", "last_week", "this_month", "last_month",
           "last_7_days", "last_30_days", "last_3_months", "last_6_months",
           "this_year", "last_year"]


def _valid_iso_date(s: Any) -> Optional[str]:
    """Return a YYYY-MM-DD string if `s` is a real ISO date, else None (ignore LLM placeholders)."""
    if not isinstance(s, str):
        return None
    try:
        return date.fromisoformat(s[:10]).isoformat()
    except ValueError:
        return None


@lru_cache(maxsize=1)
def data_today() -> date:
    """The dataset's 'today' = latest occurred_at in the world. Relative periods anchor
    here, not the wall clock: the demo world is generated up to a fixed date, so
    date.today()-based windows ("this month") turn empty the moment the real calendar
    rolls past it. Cached per process; a reseed needs a restart anyway."""
    try:
        import sqlite3
        from app.core.db_path import DB_PATH
        # Was `MAX(occurred_at) FROM crimes` — no such table in main.db, so this raised
        # every time, was swallowed, and the anchor silently fell back to the wall clock.
        # It now reads the registry it actually queries; min() keeps the wall clock as the
        # ceiling, so relative windows never run past today.
        con = registry_connect(str(DB_PATH))
        try:
            top = con.execute("SELECT MAX(date) FROM FIRs").fetchone()[0]
        finally:
            con.close()
        from app.core import clock
        if top:
            return min(date.fromisoformat(str(top)[:10]), clock.today())
    except Exception:
        pass
    from app.core import clock
    return clock.today()


@lru_cache(maxsize=1)
def real_data_today() -> date:
    """The last date covered by NON-synthetic FIRs (the real KSP extract).

    The registry carries a band of seeded demo rows (2025-01 → 2026-12, ~1.5k a month)
    that sit nine months after the real record ends. Any "last N months" window measured
    from the wall clock lands entirely inside that band, so a trend describing Karnataka
    crime was really describing ~1.5k seeded rows a month while ignoring months of 30k
    real ones. Trends anchor here instead; everything else still anchors to data_today().
    """
    try:
        import sqlite3
        from app.core.db_path import DB_PATH
        con = registry_connect(str(DB_PATH))
        try:
            top = con.execute(
                "SELECT MAX(date) FROM FIRs WHERE is_synthetic_row = 0").fetchone()[0]
        finally:
            con.close()
        from app.core import clock
        if top:
            return min(date.fromisoformat(str(top)[:10]), clock.today())
    except Exception:
        pass
    return data_today()


def resolve_period(period: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Map a relative period keyword → (date_from, date_to) ISO strings, computed from the
    dataset's 'today' (see data_today). The backend owns dates so the LLM never has to
    (it returns junk like 'current_month_start')."""
    if not period:
        return (None, None)
    p = str(period).lower().replace("-", "_").replace(" ", "_")
    today = data_today()
    iso = lambda d: d.isoformat()
    if p in ("this_month", "current_month"):
        return iso(today.replace(day=1)), iso(today)
    if p in ("last_month", "previous_month"):
        prev_last = today.replace(day=1) - timedelta(days=1)
        return iso(prev_last.replace(day=1)), iso(prev_last)
    if p in ("last_week", "past_week", "this_week"):
        return iso(today - timedelta(days=7)), iso(today)
    if p in ("last_3_months", "last_three_months", "past_3_months", "quarter"):
        return iso(today - timedelta(days=90)), iso(today)
    if p in ("last_6_months", "past_6_months"):
        return iso(today - timedelta(days=180)), iso(today)
    if p in ("this_year", "current_year"):
        return iso(today.replace(month=1, day=1)), iso(today)
    if p in ("last_year", "previous_year"):
        return iso(date(today.year - 1, 1, 1)), iso(date(today.year - 1, 12, 31))
    # Day-level windows. Without these, "how many thefts yesterday" fell through to
    # (None, None) — and a period that resolves to nothing removes the date filter
    # entirely, so the officer was shown the all-time count as if it were yesterday's.
    if p in ("today", "todays", "this_day"):
        return iso(today), iso(today)
    if p in ("yesterday", "yesterdays", "previous_day", "last_day"):
        y = today - timedelta(days=1)
        return iso(y), iso(y)
    if p in ("last_24_hours", "past_24_hours"):
        return iso(today - timedelta(days=1)), iso(today)
    m = re.fullmatch(r"(?:last|past)_(\d{1,4})_(day|days|week|weeks|month|months|year|years)", p)
    if m:
        n, unit = int(m.group(1)), m.group(2).rstrip("s")
        days = n * {"day": 1, "week": 7, "month": 30, "year": 365}[unit]
        return iso(today - timedelta(days=days)), iso(today)
    return (None, None)


def period_is_known(period: Optional[str]) -> bool:
    """True when `period` resolves to a real window. A period the officer named that
    resolves to nothing must be refused, never silently dropped."""
    return not period or resolve_period(period) != (None, None)


@lru_cache(maxsize=1)
def data_first_year() -> int:
    """The year of the earliest FIR on the register. With data_today() it bounds what a
    question about "the year N" can be answered from."""
    try:
        import sqlite3
        from app.core.db_path import DB_PATH
        con = registry_connect(str(DB_PATH))
        try:
            low = con.execute("SELECT MIN(date) FROM FIRs WHERE date >= '1990'").fetchone()[0]
        finally:
            con.close()
        if low:
            return int(str(low)[:4])
    except Exception:
        pass
    return 2016


def _date_range(date_from: Any, date_to: Any, period: Any) -> tuple[Optional[str], Optional[str]]:
    """Prefer valid explicit ISO dates; otherwise resolve the period keyword.
    Guards the LLM's bad dates: a window starting after the dataset's last record (e.g. a
    wall-clock 'this month' computed past the world's end) is dropped in favour of the
    period keyword — which itself re-anchors to the data; an end date past the data is
    clamped so "…to today" windows stay non-empty.

    Dropping a future window removes the date filter, so it must only ever happen to a date
    the model invented. A period the OFFICER named that lies after the last record ("the
    split for 2028") never reaches here: query_agent.outside_record() refuses it first."""
    df, dt = _valid_iso_date(date_from), _valid_iso_date(date_to)
    if df and dt:
        anchor = data_today().isoformat()
        if df > anchor:
            return resolve_period(period)
        return df, min(dt, anchor)
    return resolve_period(period)


# ── QuerySpec — the backend-agnostic query description ───────────────────────
Op = Literal["=", "!=", ">", "<", ">=", "<=", "in", "like", "between"]


@dataclass
class Filter:
    column: str
    op: Op
    value: Any


@dataclass
class Aggregate:
    func: Literal["count", "sum", "avg", "min", "max"]
    column: str
    alias: str


@dataclass
class QuerySpec:
    table: str
    select: list[str] = field(default_factory=list)          # plain columns
    aggregates: list[Aggregate] = field(default_factory=list)
    filters: list[Filter] = field(default_factory=list)
    group_by: list[str] = field(default_factory=list)
    order_by: Optional[tuple[str, Literal["asc", "desc"]]] = None
    limit: int = 100
    olap: bool = False                                        # route to OLAP engine
    rename: dict = field(default_factory=dict)                # result key -> the key readers expect


# ── Pydantic-based ZCQL AST (Build 03 Dynamic Query Engine) ───────────────────
from pydantic import BaseModel, Field

class ASTFilter(BaseModel):
    column: str
    op: Literal["=", "!=", ">", "<", ">=", "<=", "in", "like", "between"]
    value: Any

class ASTAggregate(BaseModel):
    func: Literal["count", "sum", "avg", "min", "max"]
    column: str
    alias: str

class ZCQLQueryAST(BaseModel):
    table: str
    select: list[str] = Field(default_factory=list)
    aggregates: list[ASTAggregate] = Field(default_factory=list)
    filters: list[ASTFilter] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    order_by: Optional[tuple[str, Literal["asc", "desc"]]] = None
    limit: Optional[int] = 100

class ASTParams(BaseModel):
    ast: ZCQLQueryAST

def ast_to_spec(ast: ZCQLQueryAST) -> QuerySpec:
    """Validate table and columns against allowed schemas to prevent hallucination/injection."""
    allowed_tables = {
        "crimes", "suspects", "crime_suspects", "stations", "officers",
        "property", "victims", "relationships", "financial_links",
        "alerts", "audit_log", "brain_embeddings", "brain_links"
    }
    if ast.table not in allowed_tables:
        raise ValueError(f"Unauthorized table access: {ast.table}")

    allowed_columns = {
        "stations": {"station_code", "name", "district", "zone", "unit_type", "range_name", "sub_division", "lat", "lon"},
        "officers": {"officer_id", "name", "rank", "station_code", "role_name"},
        "crimes": {"crime_id", "fir_number", "crime_type", "act", "acts_sections", "cognizable", "station_code", "district", "zone", "lat", "lon", "occurred_at", "reported_at", "status", "severity", "complainant_name", "io_officer_id", "io_name", "io_rank", "narrative_doc_id", "lat_r", "lon_r", "month"},
        "suspects": {"suspect_id", "full_name", "father_name", "alias", "age", "gender", "nationality", "phone_hash", "address_zone", "occupation", "prior_count", "arrest_status"},
        "property": {"property_id", "crime_id", "fir_number", "property_type", "value_inr", "status"},
        "victims": {"victim_id", "fir_id", "age_band", "age_group", "gender", "occupation", "zone", "district",
                    "crime_type", "relation"},
        "crime_suspects": {"id", "crime_id", "suspect_id", "role"},
        "relationships": {"rel_id", "suspect_a", "suspect_b", "rel_type", "strength", "source_crime_id"},
        "financial_links": {"link_id", "suspect_id", "counterparty", "txn_count", "amount_band", "flag_reason"},
        "alerts": {"alert_id", "created_at", "crime_type", "zone", "window", "observed", "expected", "z_score", "brain_match_id", "status", "pushed"},
        "audit_log": {"log_id", "ts", "officer_id", "role", "action", "agent_name", "query_text", "result_rows", "session_id"},
        "brain_embeddings": {"row_id", "kind", "summary_text", "vector_b64", "ref_session_id", "suspect_ids_json", "crime_ids_json", "station_code", "created_at"},
        "brain_links": {"link_id", "suspect_id", "matched_row_id", "overlap_type", "score", "first_seen"}
    }

    cols = allowed_columns[ast.table]

    for c in ast.select:
        if c not in cols:
            raise ValueError(f"Unauthorized column in select: {c} for table {ast.table}")

    for a in ast.aggregates:
        if a.column not in cols and a.column != "*":
            raise ValueError(f"Unauthorized column in aggregate: {a.column} for table {ast.table}")

    for f in ast.filters:
        for part in f.column.split("|"):
            if part not in cols:
                raise ValueError(f"Unauthorized column in filter: {part} for table {ast.table}")

    for g in ast.group_by:
        if g not in cols:
            raise ValueError(f"Unauthorized column in group_by: {g} for table {ast.table}")

    if ast.order_by and ast.order_by[0] not in cols:
        raise ValueError(f"Unauthorized column in order_by: {ast.order_by[0]} for table {ast.table}")

    spec_filters = [Filter(f.column, f.op, f.value) for f in ast.filters]
    spec_aggs = [Aggregate(a.func, a.column, a.alias) for a in ast.aggregates]

    return QuerySpec(
        table=ast.table,
        select=ast.select,
        aggregates=spec_aggs,
        filters=spec_filters,
        group_by=ast.group_by,
        order_by=ast.order_by,
        limit=ast.limit or 100,
        olap=len(ast.group_by) > 0
    )

def _t_ast(p: ASTParams) -> QuerySpec:
    return ast_to_spec(p.ast)


# ── ZCQL renderer (production path) ──────────────────────────────────────────

def _esc(v: Any) -> str:
    """Escape a literal for ZCQL. Numbers bare; strings single-quoted + escaped."""
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


# Row-identity columns: never NULL, one per FIR. COUNT(col) on these is by definition
# COUNT(*) — but SQLite must fetch the column for every row to test it for NULL, which
# turns a 99 ms index-only group-by into a 777 ms one with a table lookup per row.
_ROW_ID_COLUMNS = {"*", "crime_id", "fir_id"}

# Columns whose values cannot vary by case (ISO dates), so UPPER() is the identity —
# and wrapping an indexed column in a function makes its index unusable.
_CASE_INVARIANT_COLUMNS = {"date", "occurred_at", "is_synthetic_row"}


# ── Named predicates ───────────────────────────────────────────────────────────
# Fixed, reviewed SQL fragments a template may attach BY NAME. A parameter selects the
# key; user text never reaches SQL — the same rule as every other template filter.
#
# "absconding": a named accused not yet arrested in a LIVE case. Accused > arrested alone
# is not enough — it also matches 60k convicted and 29k false cases — so it is limited to
# the open stages (pending trial, under investigation, transferred for investigation).
_OPEN_STAGES = ("'PENDING TRIAL'", "'UNDER INVESTIGATION'", "'TRANSFERRED - UNDER INVESTIGATION'",
                "'CHARGESHEETED'", "'CHARGE SHEETED'")
NAMED_PREDICATES: dict[str, str] = {
    "absconding": ("accused > arrested AND UPPER(REPLACE(TRIM(status), '_', ' ')) IN ("
                   + ", ".join(_OPEN_STAGES) + ")"),
    # internal: used to tell "no absconding accused here" from "no arrest data here"
    "has_accused_data": "accused IS NOT NULL AND arrested IS NOT NULL",
}
ARREST_STATUSES = ("absconding",)


def _named(key: Optional[str]) -> list["Filter"]:
    return [Filter(key, "pred", True)] if key in NAMED_PREDICATES else []


def _like_prefix(pattern: Any) -> Optional[str]:
    """The uppercase literal prefix of a `prefix%` LIKE pattern, or None.

    Only a pattern that is one trailing '%' after plain ASCII text qualifies. Anything
    with a leading/inner wildcard, an escape, or a non-ASCII character is left as a LIKE:
    the range rewrite relies on ASCII ordering matching SQLite's byte comparison, and on
    the last character having a successor.
    """
    s = str(pattern or "")
    if not s.endswith("%"):
        return None
    head = s[:-1]
    if not head or not head.isascii():
        return None
    if any(c in head for c in "%_\\"):
        return None
    up = head.upper()
    return up if up.isascii() and ord(up[-1]) < 0x10FFFF else None


def render_zcql(spec: QuerySpec) -> str:
    """Render a QuerySpec to a ZCQL string."""
    cols = list(spec.select)
    for a in spec.aggregates:
        col = "*" if (a.func.lower() == "count" and a.column in _ROW_ID_COLUMNS) else a.column
        cols.append(f"{a.func.upper()}({col}) AS {a.alias}")
    select = ", ".join(cols) if cols else "*"
    sql = f"SELECT {select} FROM {spec.table}"

    clauses = []
    for f in spec.filters:
        if f.op == "pred":
            if f.column not in NAMED_PREDICATES:
                raise ValueError(f"unknown named predicate: {f.column!r}")
            clauses.append(f"({NAMED_PREDICATES[f.column]})")
            continue
        caseless = f.column in _CASE_INVARIANT_COLUMNS
        if f.op == "head_or":
            heads, labels, type_col = f.value
            hv = ", ".join(_esc(str(x).strip().upper()) for x in heads) or "''"
            lv = ", ".join(_esc(str(x).strip().upper()) for x in labels) or "''"
            clauses.append(f"(TRIM(UPPER({f.column})) IN ({hv}) OR TRIM(UPPER({type_col})) IN ({lv}))")
            continue
        if f.op == "in":
            # TRIM both sides so messy real values (' CYBER CRIME' vs 'CYBER CRIME',
            # zone case/whitespace variants) match reliably. The matching expression
            # indexes live in zcql_local._ensure_indexes so this stays index-backed.
            if caseless:
                vals = ", ".join(_esc(str(x).strip()) for x in f.value)
                clauses.append(f"{f.column} IN ({vals})")
            else:
                vals = ", ".join(_esc(str(x).strip().upper()) for x in f.value)
                clauses.append(f"TRIM(UPPER({f.column})) IN ({vals})")
        elif f.op == "between":
            lo, hi = f.value
            clauses.append(f"{f.column} BETWEEN {_esc(lo)} AND {_esc(hi)}")
        elif f.op == "like":
            # A prefix pattern ('IPC%') is exactly a range, and a range can use an index
            # while this LIKE never could: SQLite only applies its LIKE optimisation to a
            # literal pattern, and the right-hand side here is the function call
            # UPPER('IPC%'). Rewritten, the same count went 5,839 ms → 158 ms, identical.
            prefix = _like_prefix(f.value)
            if prefix:
                hi = prefix[:-1] + chr(ord(prefix[-1]) + 1)
                clauses.append(f"UPPER({f.column}) >= {_esc(prefix)} "
                               f"AND UPPER({f.column}) < {_esc(hi)}")
            else:
                clauses.append(f"UPPER({f.column}) LIKE UPPER({_esc(f.value)})")
        elif caseless and f.column == "date" and f.op == "<=":
            # The bound-to-today cap matches nearly every row; through the date index it
            # cost a million lookups (6.6 s for one vehicle plate). "+" keeps it off the index
            # so the selective filter beside it (plate, accused ID, zone) drives the query.
            clauses.append(f"+{f.column} <= {_esc(f.value)}")
        elif caseless:
            clauses.append(f"{f.column} {f.op} {_esc(f.value)}")
        else:
            clauses.append(f"UPPER({f.column}) {f.op} UPPER({_esc(f.value)})")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    if spec.group_by:
        sql += " GROUP BY " + ", ".join(spec.group_by)
    if spec.order_by:
        col = spec.order_by[0]
        # An exact lookup (one plate, one accused ID) matches a handful of FIRs. Ordering it
        # through the date index walked all million rows (8.8 s); "+date" sorts the few hits.
        if spec.table == "FIRs" and col == "date" and any(
                f.op == "=" and f.column not in _CASE_INVARIANT_COLUMNS for f in spec.filters):
            col = "+date"
        sql += f" ORDER BY {col} {spec.order_by[1].upper()}"
    if spec.limit is not None:
        sql += f" LIMIT {int(spec.limit)}"
    return sql


# ── Param models + template builders ─────────────────────────────────────────
# Each template: a Pydantic model (validation) + a builder (params -> QuerySpec).


def _place_head_filters(p, station_col: str = "station_code", head_col: str = "sub_head") -> list["Filter"]:
    """The police-station filter: `stations` narrows a district to the stations named
    ("thefts in Koramangala"). Sub-headings are applied with the crime type, below."""
    st = [x for x in (getattr(p, "stations", None) or []) if str(x).strip()]
    return [Filter(station_col, "in", st)] if st else []


def _crime_head_filters(p, type_col: str = "crime_type", head_col: str = "sub_head") -> list["Filter"]:
    """Crime-type and sub-heading filters together.

    Plain: crime_type IN (the groups asked) AND sub-heading IN (the sub-headings asked).
    A head-backed concept (chain snatching, vehicle theft) also brings its parent group and
    its sub-headings, and a row counts when it has one of those sub-headings OR carries the
    concept's own seeded label:
        crime_type IN (labels ∪ parent) AND (sub-heading IN heads OR crime_type IN labels)
    so the real register and the seeded rows are counted together, and an explicit broader
    group in the same question ("robbery and chain snatching") still counts in full."""
    cts = [c for c in (getattr(p, "crime_types", None) or []) if str(c).strip()]
    heads = [h for h in (getattr(p, "heads", None) or []) if str(h).strip()]
    backed = [c for c in cts if str(c).strip().upper() in HEAD_BACKED]
    out: list[Filter] = []
    if backed:
        labels = expand_crime_types(cts)
        parents = [HEAD_BACKED[str(c).strip().upper()][0] for c in backed]
        bheads = [h for c in backed for h in HEAD_BACKED[str(c).strip().upper()][1]]
        out.append(Filter(type_col, "in", list(dict.fromkeys(labels + expand_crime_types(parents)))))
        out.append(Filter(head_col, "head_or", (tuple(dict.fromkeys(bheads + heads)), tuple(labels), type_col)))
        return out
    if cts:
        out.append(Filter(type_col, "in", expand_crime_types(cts)))
    if heads:
        out.append(Filter(head_col, "in", heads))
    return out

class TypeZonePeriod(BaseModel):
    crime_types: CrimeTypeList = Field(default_factory=list)
    zones: StrList = Field(default_factory=list)
    status: StrList = Field(default_factory=list)   # NL status words (unsolved/open/solved…)
    date_from: Optional[str] = None      # ISO date 'YYYY-MM-DD' (else use `period`)
    date_to: Optional[str] = None
    period: Optional[str] = None         # relative keyword (this_month, last_3_months, …)
    arrest_status: Optional[str] = None   # a NAMED_PREDICATES key, e.g. "absconding"
    stations: StrList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)
    limit: int = 100
    order: Literal["desc", "asc"] = "desc"   # "asc": oldest first ("sort by elapsed time")

    @field_validator("limit")
    @classmethod
    def _vl(cls, v):
        return max(1, min(int(v), 500))


def _t1(p: TypeZonePeriod) -> QuerySpec:
    filters = []
    filters += _crime_head_filters(p, "crime_type", "sub_head")
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    if p.status:
        # Map NL status words → real DB status values (unsolved → open buckets, etc.).
        from app.agents.system_catalog import normalize_statuses
        st = normalize_statuses(p.status)
        if st:
            filters.append(Filter("status", "in", st))
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("occurred_at", "between", (df, dt + " 23:59")))
    filters += _named(p.arrest_status)
    filters += _place_head_filters(p)
    return QuerySpec(
        table="crimes",
        select=["crime_id", "fir_number", "crime_type", "act", "acts_sections", "zone",
                "district", "station_code", "occurred_at", "status", "io_name"]
               + (["accused", "arrested"] if p.arrest_status else []),
        filters=filters, order_by=("occurred_at", getattr(p, "order", "desc")), limit=p.limit,
    )


class SuspectLookup(BaseModel):
    name_or_alias: str

    @field_validator("name_or_alias")
    @classmethod
    def _nz(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("name_or_alias required")
        return v


def _t2(p: SuspectLookup) -> QuerySpec:
    # Local executor treats `like` as case-insensitive substring on EITHER column.
    return QuerySpec(
        table="suspects",
        select=["suspect_id", "full_name", "alias", "age", "gender",
                "address_zone", "occupation", "prior_count"],
        filters=[Filter("full_name|alias", "like", f"%{p.name_or_alias}%")],
        limit=25,
    )


class TrendByMonth(BaseModel):
    crime_types: CrimeTypeList = Field(default_factory=list)
    zones: StrList = Field(default_factory=list)
    months: Months = 12
    # A named span ("peak month for cybercrime in 2022") replaces the rolling window.
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    # Restrict the series to the real KSP extract and anchor it to where that record
    # actually ends. run_template() tries this first for every trend and only falls back
    # to the full registry when the filter has no real rows at all (the seeded demo
    # sub-zones — Rajajinagar, Whitefield, Jayanagar — are synthetic-only by design).
    real_only: bool = False
    stations: StrList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)

    @field_validator("months")
    @classmethod
    def _vm(cls, v):
        return max(1, min(int(v), 36))


def _t3(p: TrendByMonth) -> QuerySpec:
    filters = []
    filters += _crime_head_filters(p, "crime_type", "sub_head")
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    # "last N months" = window starting on the 1st of the month (N-1) months back from the
    # dataset's latest date — NOT the wall clock. The data ends on a fixed date, so a
    # date.today() window turns empty the moment the real calendar rolls past it (this was
    # the "trend last 3 months -> No matching records" bug). Anchor to data_today() like the
    # other templates do via _date_range / resolve_period.
    if p.real_only:
        filters.append(Filter("is_synthetic_row", "=", 0))
    filters += _place_head_filters(p)
    df, dt = _date_range(p.date_from, p.date_to, None)
    if df and dt:
        filters.append(Filter("occurred_at", "between", (df, dt + " 23:59")))
        return QuerySpec(table="crimes", select=["month"], aggregates=[Aggregate("count", "crime_id", "n")],
                         filters=filters, group_by=["month"], order_by=("month", "asc"), limit=36, olap=True)
    today = real_data_today() if p.real_only else data_today()
    m, y = today.month - (p.months - 1), today.year
    while m <= 0:
        m += 12
        y -= 1
    filters.append(Filter("occurred_at", ">=", date(y, m, 1).isoformat()))
    if p.real_only:
        # Cap the window too: without it the range is open-ended and the seeded band
        # (nine months later) would be pulled back in despite the filter above.
        filters.append(Filter("occurred_at", "<=", today.isoformat()))
    return QuerySpec(
        table="crimes",
        select=["month"],                       # derived in executor: YYYY-MM of occurred_at
        aggregates=[Aggregate("count", "crime_id", "n")],
        filters=filters, group_by=["month"], order_by=("month", "asc"),
        limit=max(p.months, 36), olap=True,
    )


class ZoneFilter(BaseModel):
    zones: StrList = Field(default_factory=list)
    limit: int = 10


def _t4(p: ZoneFilter) -> QuerySpec:
    # Top suspects by number of linked crimes in given zones (join crimes↔crime_suspects).
    # Executor handles the join; spec carries the intent + filter.
    zones = resolve_zones(p.zones)
    filters = [Filter("zone", "in", zones)] if zones else []
    return QuerySpec(table="__top_suspects_by_zone__", filters=filters,
                     order_by=("crime_count", "desc"), limit=max(1, min(p.limit, 50)))


class RepeatOffenders(BaseModel):
    min_priors: int = 5
    limit: int = 20
    zones: StrList = Field(default_factory=list)

    @field_validator("min_priors")
    @classmethod
    def _vp(cls, v):
        return max(1, min(int(v), 50))


def _t5(p: RepeatOffenders) -> QuerySpec:
    filters = [Filter("prior_count", ">=", p.min_priors)]
    if p.zones:
        filters.append(Filter("address_zone", "in", p.zones))
    return QuerySpec(
        table="suspects",
        select=["suspect_id", "full_name", "alias", "prior_count", "address_zone"],
        filters=filters,
        order_by=("prior_count", "desc"), limit=p.limit,
    )


_VALID_DIMS = {"age_band", "gender", "occupation", "zone", "address_zone", "relation", "age_group"}
_DIM_SYNONYMS = {"age": "age_band", "sex": "gender", "job": "occupation",
                 "profession": "occupation", "area": "zone", "location": "zone",
                 "region": "zone", "place": "zone", "relationship": "relation",
                 "relation_to_accused": "relation", "child": "age_group", "children": "age_group"}


def _as_dimension(v: Any) -> str:
    """Coerce a loose LLM dimension to a valid one (e.g. 'age'→'age_band'); unknown → 'gender'."""
    s = str(v or "").strip().lower().replace(" ", "_")
    s = _DIM_SYNONYMS.get(s, s)
    return s if s in _VALID_DIMS else "gender"


Dimension = Annotated[Literal["age_band", "gender", "occupation", "zone", "address_zone", "relation", "age_group"],
                      BeforeValidator(_as_dimension)]


class DemographicBreakdown(BaseModel):
    entity: Literal["victims", "suspects"] = "victims"
    dimension: Dimension = "gender"
    # victims: each row carries its FIR's crime type and place; suspects: through their linked cases
    crime_types: CrimeTypeList = Field(default_factory=list)
    zones: StrList = Field(default_factory=list)


def _t7(p: DemographicBreakdown) -> QuerySpec:
    dim = p.dimension
    if p.entity == "suspects" and dim == "age_band":
        dim = "age"  # suspects table has raw age
    if p.entity == "suspects" and dim == "zone":
        dim = "address_zone"
    if p.entity == "suspects" and dim in ("relation", "age_group"):
        dim = "gender"                       # a victim's attributes, not a suspect's
    if p.entity == "suspects" and (p.crime_types or p.zones):
        # "accused across theft cases": a suspect counts once, if linked to a case that matches
        filters = [Filter("dimension", "=", dim)]
        if p.crime_types:
            filters.append(Filter("crime_type", "in", expand_crime_types(p.crime_types)))
        zones = resolve_zones(p.zones)
        if zones:
            filters.append(Filter("zone", "in", zones))
        return QuerySpec(table="__suspect_demographics__", select=[dim], filters=filters,
                         order_by=("n", "desc"), limit=50)
    filters = []
    if p.entity == "victims":
        if p.crime_types:
            filters.append(Filter("crime_type", "in", expand_crime_types(p.crime_types)))
        zones = resolve_zones(p.zones)
        if zones:
            filters.append(Filter("zone", "in", zones))
    return QuerySpec(
        table=p.entity, select=[dim],
        aggregates=[Aggregate("count", f"{p.entity[:-1]}_id", "n")],
        filters=filters, group_by=[dim], order_by=("n", "desc"), limit=50, olap=True,
    )


def _as_geo_dimension(v: Any) -> str:
    s = str(v or "").strip().lower().replace(" ", "_")
    if s in ("station", "stations", "station_code", "police_station", "unit", "units", "ps"):
        return "station_code"
    if s in ("io", "io_name", "officer", "officers", "investigating_officer", "investigating_officers"):
        return "io_name"
    return "zone"


GeoDimension = Annotated[Literal["zone", "district", "station_code", "io_name"], BeforeValidator(_as_geo_dimension)]


def _as_order(v: Any) -> str:
    """'descending' / 'lowest' / 'ASC' → 'desc' | 'asc'. The LLM rarely emits the literal."""
    s = str(v or "desc").strip().lower()
    return "asc" if (s.startswith("asc") or s in ("lowest", "least", "fewest", "low", "bottom")) else "desc"


Order = Annotated[Literal["desc", "asc"], BeforeValidator(_as_order)]


class ZoneHotspots(BaseModel):
    crime_types: CrimeTypeList = Field(default_factory=list)
    zones: StrList = Field(default_factory=list)      # rank the stations inside these districts
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None
    dimension: GeoDimension = "zone"
    limit: int = 10
    order: Order = "desc"     # "asc" answers "least crime district"
    arrest_status: Optional[str] = None   # a NAMED_PREDICATES key, e.g. "absconding"
    stations: StrList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)

    @field_validator("limit")
    @classmethod
    def _vl(cls, v):
        return max(1, min(int(v), 100))


def _t11(p: ZoneHotspots) -> QuerySpec:
    filters = []
    filters += _crime_head_filters(p, "crime_type", "sub_head")
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("occurred_at", "between", (df, dt + " 23:59")))
    filters += _named(p.arrest_status)
    filters += _place_head_filters(p)
    dim = getattr(p, "dimension", "zone") or "zone"
    # A ranking "by district" groups on the district, not on `zone`: 3,868 seeded rows
    # carry a locality there (Jayanagar, Whitefield, Mysuru-Devaraja) and each was listed
    # as a district of its own. `district` holds the parent for every row.
    # Readers of these rows look the place up under "zone", so the result keeps that key.
    rename = {}
    if dim == "zone":
        dim, rename = "district", {"district": "zone"}
    lim = getattr(p, "limit", 10) or 10
    return QuerySpec(
        table="crimes", select=[dim], rename=rename,
        aggregates=[Aggregate("count", "crime_id", "n")],
        filters=filters, group_by=[dim], order_by=("n", "asc" if p.order == "asc" else "desc"),
        limit=lim, olap=True,
    )


class SuspectCrimes(BaseModel):
    suspect_id: str


def _t9(p: SuspectCrimes) -> QuerySpec:
    return QuerySpec(table="__suspect_crimes__",
                     filters=[Filter("suspect_id", "=", p.suspect_id)],
                     order_by=("occurred_at", "desc"), limit=100)


class RecentCrimes(BaseModel):
    zones: StrList = Field(default_factory=list)
    crime_types: CrimeTypeList = Field(default_factory=list)
    arrest_status: Optional[str] = None   # a NAMED_PREDICATES key, e.g. "absconding"
    stations: StrList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)
    limit: int = 10


def _t12(p: RecentCrimes) -> QuerySpec:
    zones = resolve_zones(p.zones)
    filters = [Filter("zone", "in", zones)] if zones else []
    filters += _crime_head_filters(p, "crime_type", "sub_head")
    # Cap to data_today so future-dated synthetic rows never bubble up (drop_future_rows
    # would strip them anyway, leaving an empty result for a perfectly valid "recent" query).
    # ponytail: simple date cap; upgrade to a configurable horizon if needed
    anchor = data_today().isoformat()
    filters.append(Filter("occurred_at", "<=", anchor))
    filters += _named(p.arrest_status)
    filters += _place_head_filters(p)
    return QuerySpec(table="crimes",
                     select=["crime_id", "fir_number", "crime_type", "zone",
                             "occurred_at", "status"] + (["accused", "arrested"] if p.arrest_status else []),
                     filters=filters, order_by=("occurred_at", "desc"),
                     limit=max(1, min(p.limit, 50)))


class CountByStatus(BaseModel):
    zones: StrList = Field(default_factory=list)
    crime_types: CrimeTypeList = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None
    stations: StrList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)


def _t8(p: CountByStatus) -> QuerySpec:
    """Case counts by investigation status, optionally for a crime type, place and period
    ("open theft cases in Mysuru this year")."""
    filters = []
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    filters += _crime_head_filters(p, "crime_type", "sub_head")
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("occurred_at", "between", (df, dt + " 23:59")))
    filters += _place_head_filters(p)
    # 20 groups: the status column holds ~18 raw spellings; 10 silently dropped the tail.
    return QuerySpec(table="crimes", select=["status"],
                     aggregates=[Aggregate("count", "crime_id", "n")],
                     filters=filters, group_by=["status"],
                     order_by=("n", "desc"), limit=20, olap=True)


class CrimeTypeBreakdown(BaseModel):
    zones: StrList = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None
    arrest_status: Optional[str] = None   # a NAMED_PREDICATES key, e.g. "absconding"
    stations: StrList = Field(default_factory=list)


def _t13(p: CrimeTypeBreakdown) -> QuerySpec:
    """Crime counts grouped by crime_type (dashboard breakdown / 'which types are common')."""
    filters = []
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("occurred_at", "between", (df, dt + " 23:59")))
    filters += _named(p.arrest_status)
    filters += _place_head_filters(p)
    return QuerySpec(
        table="crimes", select=["crime_type"],
        aggregates=[Aggregate("count", "crime_id", "n")],
        filters=filters, group_by=["crime_type"], order_by=("n", "desc"),
        limit=20, olap=True,
    )


class ScanWindow(BaseModel):
    """No params — returns the (crime_type, zone, occurred_at) of every crime so the
    Forecast Agent can bucket weekly counts per series. Internal (not LLM-selectable)."""
    pass


def _t14(p: ScanWindow) -> QuerySpec:
    filters = []
    try:
        from app.core import clock
        if clock.is_fixed():
            filters.append(Filter("occurred_at", "<=", clock.today().isoformat()))
    except Exception:
        pass
    return QuerySpec(table="crimes", select=["crime_id", "fir_number", "crime_type", "zone", "occurred_at"],
                     filters=filters, order_by=("occurred_at", "desc"), limit=60000)

class YearSummary(BaseModel):
    year: Optional[int] = None

def _t16(p: YearSummary) -> QuerySpec:
    """Overall yearly summary and total FIR counts for a specific year (T16)."""
    filters = []
    if p.year:
        filters.append(Filter("year", "==", p.year))
    return QuerySpec(
        table="year_intel",
        select=["year", "fir_count", "summary", "top_categories", "is_real"],
        filters=filters
    )


class MapCrimes(BaseModel):
    crime_types: CrimeTypeList = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None


def _t15(p: MapCrimes) -> QuerySpec:
    """Crimes with coordinates for the geospatial map (aggregated by zone/district in
    the endpoint). Internal (not LLM-selectable)."""
    filters = []
    if p.crime_types:
        filters.append(Filter("crime_type", "in", expand_crime_types(p.crime_types)))
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("occurred_at", "between", (df, dt + " 23:59")))
    return QuerySpec(
        table="crimes",
        select=["crime_id", "crime_type", "zone", "district", "lat", "lon", "occurred_at"],
        filters=filters, order_by=("occurred_at", "desc"), limit=20000,
    )


_PLATE_RE = re.compile(r"([A-Z]{2})[\s-]?(\d{1,2})[\s-]?([A-Z]{1,3})[\s-]?(\d{1,4})")


def normalize_plate(v: Any) -> str:
    """'ka02m2093', 'KA 02 M 2093' → 'KA-02-M-2093' (the format stored in FIRs.Vehicle_Reg_No)."""
    s = str(v or "").upper().strip()
    m = _PLATE_RE.search(s)
    if not m:
        return s
    st, dd, series, num = m.groups()
    return f"{st}-{int(dd):02d}-{series}-{num}"


class VehicleLookup(BaseModel):
    plate: Annotated[str, BeforeValidator(normalize_plate)] = ""


def _today_cap() -> str:
    """Upper date bound for queries on the raw FIRs table. _bound_to_today only guards the
    `crimes` view, and the data holds future-dated rows (up to 2026-12-31)."""
    from app.core import clock
    return clock.today().isoformat() + " 23:59"


_NO_VALUE = "__NO_VALUE__"   # an empty lookup must match nothing, not every FIR with a blank field


def _t18(p: VehicleLookup) -> QuerySpec:
    """FIRs that record this vehicle registration number (newest first, capped at today)."""
    return QuerySpec(
        table="FIRs",
        select=["fir_id", "CrimeNo", "crime_type", "zone", "district_norm", "UnitName", "date",
                "status", "ActSection", "Vehicle_Reg_No"],
        filters=[Filter("Vehicle_Reg_No", "=", p.plate or _NO_VALUE),
                 Filter("date", "<=", _today_cap())],
        # FIRs holds one row per accused, so a single FIR can repeat; fetch generously and
        # let the answer writer count distinct fir_id values (CrimeNo repeats across stations).
        order_by=("date", "desc"), limit=300,
    )


class ActSplit(BaseModel):
    zones: StrList = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None


def _t17(p: ActSplit) -> QuerySpec:
    """FIR counts grouped by the Act they were registered under (IPC/BNS vs special & local laws)."""
    filters = []
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("occurred_at", "between", (df, dt + " 23:59")))
    return QuerySpec(table="crimes", select=["act"],
                     aggregates=[Aggregate("count", "crime_id", "n")],
                     filters=filters, group_by=["act"], order_by=("n", "desc"),
                     limit=400, olap=True)


# ── Cross-station intelligence & case outcomes (T19–T23) ─────────────────────
# T19 and T22 need COUNT(DISTINCT …), HAVING and CASE, which QuerySpec cannot express, so,
# like T4 and T9, they are virtual tables: the builder validates and packs the params and
# zcql_local runs parameterised SQL (column names come only from the whitelists here).
# T20, T21 and T23 are plain QuerySpecs over the raw FIRs table, which carries the
# identifier, beat and outcome columns the `crimes` view does not expose.
# FIRs.CrimeNo is NOT unique (it repeats across stations); fir_id is the FIR key.

IDENTIFIER_COLUMNS = {"upi": "UPI_ID", "ip": "IP_Address", "vehicle": "Vehicle_Reg_No", "accused": "Accused_ID"}
# One-value lookups (T20) also take a modus-operandi code. It is kept out of
# IDENTIFIER_COLUMNS, which T19 scans in full: an MO code is a way of working, not a
# person's identifier, and it does not belong in the cross-district identity links.
LOOKUP_COLUMNS = {**IDENTIFIER_COLUMNS, "mo": "MO_Details"}
_MO_RE = re.compile(r"\bMO-[A-Z0-9][A-Z0-9-]{2,40}\b", re.I)

_KEY_ALIASES = {
    "upi": "upi", "upi_id": "upi", "upiid": "upi", "upi_ids": "upi", "vpa": "upi",
    "ip": "ip", "ip_address": "ip", "ipaddress": "ip", "ips": "ip", "ip_addresses": "ip",
    "vehicle": "vehicle", "vehicles": "vehicle", "plate": "vehicle", "vehicle_reg_no": "vehicle",
    "registration": "vehicle",
    "accused": "accused", "accused_id": "accused", "accused_ids": "accused",
    "offender": "accused", "offenders": "accused",
    "any": "any", "all": "any",
    "mo": "mo", "modus_operandi": "mo", "mo_details": "mo", "signature": "mo", "mo_signature": "mo",
}


def _as_key_type(v: Any) -> str:
    return _KEY_ALIASES.get(str(v or "").strip().lower().replace(" ", "_").replace("-", "_"), "any")


KeyType = Annotated[Literal["any", "upi", "ip", "vehicle", "accused", "mo"], BeforeValidator(_as_key_type)]

_IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
_ACC_RE = re.compile(r"ACC[\s_-]?KA[\s_-]?(\d{3,7})", re.I)


def normalize_accused_id(v: Any) -> str:
    """'acc ka 500777' / 'ACC-KA-500777' → 'ACC-KA-500777'."""
    s = str(v or "").strip()
    m = _ACC_RE.search(s)
    return f"ACC-KA-{m.group(1)}" if m else s.upper()


def detect_identifier(value: Any) -> Optional[str]:
    """Which identifier column a raw value belongs to, or None when it can't be told."""
    v = str(value or "").strip()
    if not v:
        return None
    if _ACC_RE.search(v):
        return "accused"
    if _MO_RE.fullmatch(v):
        return "mo"
    if _IPV4_RE.match(v):
        return "ip"
    if "@" in v and " " not in v:
        return "upi"
    if _PLATE_RE.fullmatch(v.upper()):
        return "vehicle"
    return None


# T19 ─ identifiers shared by FIRs in several districts ─────────────────────────
class SharedIdentifiers(BaseModel):
    key_type: KeyType = "any"
    min_districts: int = 2
    zones: StrList = Field(default_factory=list)
    # "corridors between Bengaluru and Tumakuru": only identifiers seen on FIRs in EACH place
    between: StrList = Field(default_factory=list)
    crime_types: CrimeTypeList = Field(default_factory=list)
    limit: int = 10

    @field_validator("min_districts")
    @classmethod
    def _vd(cls, v):
        return max(2, min(int(v), 10))

    @field_validator("limit")
    @classmethod
    def _vl(cls, v):
        return max(1, min(int(v), 50))


def _t19(p: SharedIdentifiers) -> QuerySpec:
    """UPI IDs / IP addresses / vehicles / accused IDs recorded in FIRs from min_districts+
    districts. With a zone, only identifiers that also appear in that zone."""
    filters = [Filter("key_type", "=", p.key_type), Filter("min_districts", "=", p.min_districts)]
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    if p.crime_types:
        filters.append(Filter("crime_type", "in", expand_crime_types(p.crime_types)))
    sides = [resolve_zones([b]) for b in p.between if str(b).strip()][:3]
    if len(sides) >= 2:
        filters.append(Filter("between", "=", tuple(tuple(x) for x in sides)))
    return QuerySpec(table="__shared_identifiers__", filters=filters, limit=p.limit)


# T20 ─ every FIR carrying one identifier ───────────────────────────────────────
class IdentifierLookup(BaseModel):
    value: str = ""
    key_type: KeyType = "any"


def resolve_identifier(params: Any) -> tuple[str, str]:
    """(key_type, normalised value) for a lookup. An explicit key_type wins; otherwise the
    value's shape decides (x@bank → UPI, 1.2.3.4 → IP, ACC-KA-… → accused, KA-02-M-… → vehicle)."""
    if isinstance(params, IdentifierLookup):
        p = params
    else:
        p = IdentifierLookup(**{k: v for k, v in dict(params or {}).items()
                                if k in ("value", "key_type") and v not in (None, "")})
    value = p.value.strip()
    kt = p.key_type if p.key_type != "any" else (detect_identifier(value) or "upi")
    if kt == "mo":
        value = value.strip()
    elif kt == "vehicle":
        value = normalize_plate(value)
    elif kt == "accused":
        value = normalize_accused_id(value)
    return kt, value


_FIR_CASE_COLUMNS = ["fir_id", "CrimeNo", "crime_type", "zone", "district_norm", "UnitName",
                     "date", "status", "ActSection"]


def _t20(p: IdentifierLookup) -> QuerySpec:
    """Every FIR that records this UPI ID or IP address (vehicle and accused IDs also accepted).
    The renderer compares UPPER() on both sides, so the lookup is case-insensitive."""
    kt, value = resolve_identifier(p)
    col = LOOKUP_COLUMNS[kt]
    return QuerySpec(table="FIRs", select=_FIR_CASE_COLUMNS + [col],
                     filters=[Filter(col, "=", value or _NO_VALUE), Filter("date", "<=", _today_cap())],
                     order_by=("date", "desc"), limit=300)


# T21 ─ one accused ID's history ────────────────────────────────────────────────
class AccusedHistory(BaseModel):
    accused_id: Annotated[str, BeforeValidator(normalize_accused_id)] = ""


def _t21(p: AccusedHistory) -> QuerySpec:
    """All FIRs listing this accused ID, with the per-FIR arrest / charge-sheet / conviction counts."""
    return QuerySpec(
        table="FIRs",
        select=_FIR_CASE_COLUMNS + ["FIR_Stage", "Accused_Count", "Arrested_Count_No_",
                                    "Accused_ChargeSheeted_Count", "Conviction_Count"],
        filters=[Filter("Accused_ID", "=", p.accused_id or _NO_VALUE), Filter("date", "<=", _today_cap())],
        order_by=("date", "desc"), limit=300,
    )


# T22 ─ case outcomes ───────────────────────────────────────────────────────────
def _as_outcome_dimension(v: Any) -> str:
    s = str(v or "").strip().lower().replace(" ", "_").replace("-", "_")
    if s in ("district", "districts", "zone", "zones", "city", "cities", "district_wise", "zone_wise"):
        return "district"
    if s in ("crime_type", "crime_types", "crime", "crimes", "type", "types", "crime_wise"):
        return "crime_type"
    return "none"


class CaseOutcomes(BaseModel):
    zones: StrList = Field(default_factory=list)
    crime_types: CrimeTypeList = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None
    dimension: Annotated[Literal["none", "district", "crime_type"], BeforeValidator(_as_outcome_dimension)] = "none"
    order: Order = "desc"
    limit: int = 10
    stations: StrList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)

    @field_validator("limit")
    @classmethod
    def _vl(cls, v):
        return max(1, min(int(v), 50))


def _t22(p: CaseOutcomes) -> QuerySpec:
    """Conviction, charge-sheet and arrest rates plus the case-stage mix: overall, by
    district or by crime type."""
    filters = [Filter("dimension", "=", p.dimension)]
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    filters += _crime_head_filters(p, "crime_type", "sub_head")
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("date", "between", (df, dt + " 23:59")))
    filters += _place_head_filters(p, "station", "sub_head")
    return QuerySpec(table="__case_outcomes__", filters=filters,
                     order_by=("conviction_rate", p.order), limit=p.limit)


# T23 ─ beat / village-area hotspots ────────────────────────────────────────────
_PLACEHOLDER_PLACES = ("", "Other Beat", "OTHER", "OTHERS", "TEST", "NA", "N/A", "NIL", "-", "0")
def _as_beat_dimension(v: Any) -> str:
    s = str(v or "").strip().lower()
    return "area" if any(w in s for w in ("area", "village", "locality", "neighbour", "neighbor")) else "beat"


class BeatHotspots(BaseModel):
    zones: StrList = Field(default_factory=list)
    crime_types: CrimeTypeList = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None
    dimension: Annotated[Literal["beat", "area"], BeforeValidator(_as_beat_dimension)] = "beat"
    order: Order = "desc"
    limit: int = 10
    stations: StrList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)

    @field_validator("limit")
    @classmethod
    def _vl(cls, v):
        return max(1, min(int(v), 50))


def _t23(p: BeatHotspots) -> QuerySpec:
    """FIR counts per beat (grouped with its police station, because beat numbers like
    'BEAT 2' repeat across stations) or per village/area (with its district)."""
    filters = [Filter("date", "<=", _today_cap())]
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    filters += _crime_head_filters(p, "crime_type", "CrimeHead_Name")
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("date", "between", (df, dt + " 23:59")))
    # Placeholder values ("OTHER", "TEST", "Other Beat") are data-entry fillers, not places:
    # left in, "OTHER · HSR Layout PS" ranked as Bengaluru City's top theft beat.
    col_name = "Village_Area_Name" if p.dimension == "area" else "Beat_Name"
    cols = [col_name, "district_norm"] if p.dimension == "area" else [col_name, "UnitName"]
    filters += [Filter(col_name, "!=", junk) for junk in _PLACEHOLDER_PLACES]
    filters += _place_head_filters(p, "station", "CrimeHead_Name")
    return QuerySpec(table="FIRs", select=cols, aggregates=[Aggregate("count", "fir_id", "n")],
                     filters=filters, group_by=cols, order_by=("n", p.order), limit=p.limit, olap=True)


# T24 ─ case stages and pendency, by station / district ─────────────────────────────
def _as_pend_dimension(v: Any) -> str:
    s = str(v or "").strip().lower().replace(" ", "_")
    if s in ("station", "stations", "station_code", "police_station", "ps", "unit", "units"):
        return "station"
    if s in ("district", "districts", "zone", "zones", "city", "cities"):
        return "district"
    if s in ("crime_type", "crime", "crimes", "type", "types"):
        return "crime_type"
    return "none"


class CaseStages(BaseModel):
    zones: StrList = Field(default_factory=list)
    stations: StrList = Field(default_factory=list)
    crime_types: CrimeTypeList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None
    dimension: Annotated[Literal["none", "station", "district", "crime_type"], BeforeValidator(_as_pend_dimension)] = "none"
    older_than_days: int = 0          # "under investigation for more than 90 days"
    order: Order = "desc"
    limit: int = 10

    @field_validator("limit")
    @classmethod
    def _vl(cls, v):
        return max(1, min(int(v), 50))

    @field_validator("older_than_days")
    @classmethod
    def _vo(cls, v):
        return max(0, min(int(v or 0), 3650))


def _t24(p: CaseStages) -> QuerySpec:
    """Every FIR's current stage (under investigation, pending trial, convicted …) and how
    long the open investigations have been open, by station, district or crime type."""
    filters = [Filter("dimension", "=", p.dimension), Filter("older_than_days", "=", p.older_than_days)]
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    filters += _crime_head_filters(p, "crime_type", "sub_head")
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("date", "between", (df, dt + " 23:59")))
    filters += _place_head_filters(p, "station", "sub_head")
    return QuerySpec(table="__case_stages__", filters=filters, order_by=("under_investigation", p.order), limit=p.limit)


# T25 ─ what a crime group is made of: its sub-headings ──────────────────────────────
def _as_head_by(v: Any) -> str:
    s = str(v or "").strip().lower()
    return "group" if s in ("group", "groups", "crime_type", "type", "day_night", "day/night") else "head"


class SubHeadBreakdown(BaseModel):
    crime_types: CrimeTypeList = Field(default_factory=list)
    zones: StrList = Field(default_factory=list)
    stations: StrList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)     # the sub-heading the officer asked about (led with)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None
    by: Annotated[Literal["head", "group"], BeforeValidator(_as_head_by)] = "head"
    limit: int = 12

    @field_validator("limit")
    @classmethod
    def _vl(cls, v):
        return max(1, min(int(v), 40))


def _t25(p: SubHeadBreakdown) -> QuerySpec:
    """FIR counts per sub-heading inside the crime group(s) asked ("which share of thefts
    are two-wheelers"), or per crime group when it splits by group (burglary by day vs night)."""
    filters = [Filter("date", "<=", _today_cap())]
    if p.crime_types:
        filters.append(Filter("crime_type", "in", expand_crime_types(p.crime_types)))
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("date", "between", (df, dt + " 23:59")))
    if p.stations:
        filters.append(Filter("station", "in", p.stations))
    col = "crime_type" if p.by == "group" else "CrimeHead_Name"
    return QuerySpec(table="FIRs", select=[col], aggregates=[Aggregate("count", "fir_id", "n")],
                     filters=filters, group_by=[col], order_by=("n", "desc"), limit=p.limit, olap=True)


# T26 ─ day-of-week and month-of-year pattern ─────────────────────────────────────────
def _as_time_dimension(v: Any) -> str:
    s = str(v or "").strip().lower().replace(" ", "_")
    if s in ("monthday", "day_of_month", "payday", "paydays", "salary_day", "date_of_month"):
        return "monthday"
    return "month" if s in ("month", "months", "month_of_year", "season", "seasonal", "monthly") else "weekday"


class TimePattern(BaseModel):
    crime_types: CrimeTypeList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)
    zones: StrList = Field(default_factory=list)
    stations: StrList = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None
    dimension: Annotated[Literal["weekday", "month", "monthday"], BeforeValidator(_as_time_dimension)] = "weekday"


def _t26(p: TimePattern) -> QuerySpec:
    """FIRs per day of the week, or per calendar month across years — by REGISTRATION date:
    the register holds the date a case was registered, not the time of the offence."""
    filters = [Filter("dimension", "=", p.dimension)]
    filters += _crime_head_filters(p, "crime_type", "sub_head")
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("date", "between", (df, dt + " 23:59")))
    filters += _place_head_filters(p, "station", "sub_head")
    return QuerySpec(table="__time_pattern__", filters=filters, limit=12)


# T27 ─ side-by-side comparison of places or years ────────────────────────────────────
def _as_compare_dimension(v: Any) -> str:
    s = str(v or "").strip().lower().replace(" ", "_")
    if s in ("year", "years", "yearly"):
        return "year"
    if s in ("station", "stations", "ps"):
        return "station"
    return "district"


def _as_year_list(v: Any) -> list[int]:
    out = []
    for x in _as_str_list(v) if not isinstance(v, list) else v:
        m = re.search(r"\b(19|20)\d\d\b", str(x))
        if m:
            out.append(int(m.group(0)))
    return sorted(set(out))


class CompareSides(BaseModel):
    zones: StrList = Field(default_factory=list)        # the places compared (two or more)
    stations: StrList = Field(default_factory=list)
    years: Annotated[list[int], BeforeValidator(_as_year_list)] = Field(default_factory=list)
    crime_types: CrimeTypeList = Field(default_factory=list)
    heads: StrList = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None
    dimension: Annotated[Literal["district", "station", "year"], BeforeValidator(_as_compare_dimension)] = "district"


def _t27(p: CompareSides) -> QuerySpec:
    """Counts and case outcomes for each place (or each year) named, side by side."""
    filters = [Filter("dimension", "=", p.dimension)]
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    filters += _crime_head_filters(p, "crime_type", "sub_head")
    if p.years:
        filters.append(Filter("year", "in", [str(y) for y in p.years]))
    else:
        df, dt = _date_range(p.date_from, p.date_to, p.period)
        if df and dt:
            filters.append(Filter("date", "between", (df, dt + " 23:59")))
    filters += _place_head_filters(p, "station", "sub_head")
    return QuerySpec(table="__case_outcomes__", filters=filters, order_by=("firs", "desc"), limit=50)


# T28 ─ case outcomes by the act / section a case was registered under ──────────────
def _as_act_dimension(v: Any) -> str:
    s = str(v or "").strip().lower()
    return "section" if s.startswith("section") or s in ("sec", "sections", "u/s") else "act"


class ActOutcomes(BaseModel):
    zones: StrList = Field(default_factory=list)
    crime_types: CrimeTypeList = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    period: Optional[str] = None
    dimension: Annotated[Literal["act", "section"], BeforeValidator(_as_act_dimension)] = "act"
    order: Order = "desc"
    limit: int = 10

    @field_validator("limit")
    @classmethod
    def _vl(cls, v):
        return max(1, min(int(v), 50))


def _t28(p: ActOutcomes) -> QuerySpec:
    """Conviction / charge-sheet / arrest rates per Act (IPC, NDPS, POCSO, IT Act …) or per
    section of an Act, from the act/section each FIR was registered under."""
    filters = [Filter("dimension", "=", p.dimension)]
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    if p.crime_types:
        filters.append(Filter("crime_type", "in", expand_crime_types(p.crime_types)))
    df, dt = _date_range(p.date_from, p.date_to, p.period)
    if df and dt:
        filters.append(Filter("date", "between", (df, dt + " 23:59")))
    return QuerySpec(table="__case_outcomes__", filters=filters,
                     order_by=("conviction_rate", p.order), limit=p.limit)


# T29 ─ what links two FIRs ──────────────────────────────────────────────────────────
_FIR_ID_RE = re.compile(r"\b(?:[A-Z]{2,4}-20\d\d-[A-Z0-9]{3,10}|FIR-20\d\d-[\w-]{4,40}|C\d{5}|\d{15,19})\b")


class FirPair(BaseModel):
    fir_a: str = ""
    fir_b: str = ""


def _t29(p: FirPair) -> QuerySpec:
    """The two FIRs side by side, and every key they share: accused, vehicle, UPI ID, IP
    address, modus operandi, station, district, crime and act. "Named shared key per edge"."""
    a, b = (p.fir_a or "").strip().upper(), (p.fir_b or "").strip().upper()
    return QuerySpec(table="__fir_link__", filters=[Filter("fir_a", "=", a or _NO_VALUE), Filter("fir_b", "=", b or _NO_VALUE)],
                     limit=2)


# T30 ─ what an event does to registered crime ───────────────────────────────────
_EVENT_WORDS = {
    "deepavali": "deepavali", "diwali": "deepavali", "deepawali": "deepavali", "ದೀಪಾವಳಿ": "deepavali",
    "dasara": "dasara", "dussehra": "dasara", "dasera": "dasara", "ದಸರಾ": "dasara",
    "ganesha": "ganesha", "ganesh chaturthi": "ganesha", "ganeshotsava": "ganesha", "ಗಣೇಶ": "ganesha",
    "ugadi": "ugadi", "ಯುಗಾದಿ": "ugadi", "sankranti": "sankranti", "sankranthi": "sankranti", "ಸಂಕ್ರಾಂತಿ": "sankranti",
    "ramzan": "ramzan", "ramadan": "ramzan", "eid": "ramzan", "ರಂಜಾನ್": "ramzan",
    "new year": "newyear", "new year's eve": "newyear", "new years eve": "newyear", "ಹೊಸ ವರ್ಷ": "newyear",
}


def find_event(low: str) -> Optional[str]:
    """The festival or event named in a (lower-cased) question, as an events.py key."""
    for w, key in sorted(_EVENT_WORDS.items(), key=lambda kv: -len(kv[0])):
        if (w.isascii() and re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low or "")) or (not w.isascii() and w in (low or "")):
            return key
    return None


class EventEffect(BaseModel):
    event: str = ""
    zones: StrList = Field(default_factory=list)


def _t30(p: EventEffect) -> QuerySpec:
    """What past years show a festival or event did to registered cases: all crime, and the
    crime groups that clearly rose or fell, measured from the FIRs registered in its window
    against the four weeks either side. When it falls next comes from the event calendar."""
    filters = [Filter("event", "=", (p.event or "").strip().lower())]
    zones = resolve_zones(p.zones)
    if zones:
        filters.append(Filter("zone", "in", zones))
    return QuerySpec(table="__event_effect__", filters=filters, limit=1)


# ── The whitelist registry ───────────────────────────────────────────────────
@dataclass
class Template:
    id: str
    description: str
    examples: list[str]
    param_model: type[BaseModel]
    builder: Callable[[Any], QuerySpec]
    internal: bool = False    # internal analytics/scan templates: hidden from the LLM selector


TEMPLATES: dict[str, Template] = {
    "T1": Template("T1", "List crimes by type / zone / date range",
                   ["chain snatching in Rajajinagar last month",
                    "show robberies in Bengaluru North"], TypeZonePeriod, _t1),
    "T2": Template("T2", "Look up a suspect by name or alias",
                   ["who is Raju K", "find suspect Yellappa"], SuspectLookup, _t2),
    "T3": Template("T3", "Monthly crime trend (count per month)",
                   ["robbery trend in Bengaluru North last 3 months",
                    "theft trend this year"], TrendByMonth, _t3),
    "T4": Template("T4", "Top suspects by linked-crime count in a zone",
                   ["top suspects in Rajajinagar"], ZoneFilter, _t4),
    "T5": Template("T5", "Repeat offenders (prior_count ≥ N)",
                   ["who are the repeat offenders", "habitual criminals"], RepeatOffenders, _t5),
    "T7": Template("T7", "Demographic breakdown of victims/suspects",
                   ["age and gender of theft victims",
                    "victim gender breakdown"], DemographicBreakdown, _t7),
    "T8": Template("T8", "Crime counts by investigation status (filter by zone, crime type and period)",
                   ["how many cases are open in Jayanagar", "open theft cases by status in 2024"],
                   CountByStatus, _t8),
    "T9": Template("T9", "All crimes linked to a suspect",
                   ["what crimes is S0001 linked to"], SuspectCrimes, _t9),
    "T11": Template("T11", "Crime counts ranked by zone, district, or city (hotspots & city rankings)",
                    ["Give me the top 10. Cities of 2024 in crime",
                     "which zones have the most theft",
                     "where are the hotspots"], ZoneHotspots, _t11),
    "T12": Template("T12", "Most recent crimes (optionally by zone and crime type)",
                    ["latest cases in Whitefield", "recent burglaries in Whitefield"], RecentCrimes, _t12),
    "T13": Template("T13", "Crime counts by crime type (breakdown)",
                    ["breakdown of crimes by type", "which crime types are most common"],
                    CrimeTypeBreakdown, _t13),
    "T14": Template("T14", "(internal) all crimes for the weekly anomaly scan",
                    ["(internal)"], ScanWindow, _t14, internal=True),
    "T15": Template("T15", "(internal) crimes with coordinates for the map",
                    ["(internal)"], MapCrimes, _t15, internal=True),
    "T16": Template("T16", "Overall yearly summary and total FIR counts for a specific year",
                    ["Cognizable FIRs registered in Karnataka in 2022?", 
                     "what happened in 2022", "summary of 2021"],
                    YearSummary, _t16),
    "T17": Template("T17", "Split of FIRs by law: IPC/BNS vs special & local laws (SLL)",
                    ["IPC/BNS vs SLL split for 2022?", "how many FIRs under special and local laws"],
                    ActSplit, _t17),
    "T18": Template("T18", "FIRs linked to a vehicle registration number",
                    ["check if vehicle KA-02-M-2093 has any FIRs", "FIRs for KA-36-M-1021"],
                    VehicleLookup, _t18),
    "T19": Template("T19", "Identifiers (UPI ID, IP address, vehicle, accused ID) shared by FIRs in several districts: cross-station links",
                    ["which UPI IDs are used in more than one district",
                     "accused who appear across multiple districts",
                     "vehicles linked to FIRs in 3 or more districts"], SharedIdentifiers, _t19),
    "T20": Template("T20", "All FIRs linked to one UPI ID, IP address or modus-operandi code (identifier lookup)",
                    ["FIRs for UPI geetha.achar40@okicici", "cases linked to IP 103.87.106.22",
                     "FIRs sharing modus operandi MO-A1-festival-lockedhouse"],
                    IdentifierLookup, _t20),
    "T21": Template("T21", "Full FIR history of one accused ID across districts, with arrests, charge-sheets and convictions",
                    ["cases for accused ACC-KA-500777", "history of ACC-KA-102883"], AccusedHistory, _t21),
    "T22": Template("T22", "Case outcomes: conviction, charge-sheet, arrest and undetected rates, overall or by district or crime type",
                    ["conviction rate by district in 2023", "charge sheet rate for murder cases",
                     "which district has the lowest conviction rate"], CaseOutcomes, _t22),
    "T23": Template("T23", "Beat-level or village/area-level crime hotspots inside a district (patrol planning)",
                    ["top beats for theft in Bengaluru City",
                     "which villages in Mysuru Dist have the most crime"], BeatHotspots, _t23),
    "T24": Template("T24", "Case stages and pendency: cases under investigation, pending trial, convicted, and how long open investigations have been open, by police station, district or crime type",
                    ["stations with the most pending investigations in Mysuru",
                     "cases under investigation for more than 90 days in Bengaluru City",
                     "how many POCSO cases reached trial stage in 2023"], CaseStages, _t24),
    "T25": Template("T25", "What a crime group is made of: FIR counts by sub-heading (two-wheeler, house theft, jewellery, extortion …) or by day vs night",
                    ["what share of thefts are two-wheelers", "breakdown of theft by type",
                     "are burglaries more frequent by night or by day"], SubHeadBreakdown, _t25),
    "T26": Template("T26", "Day-of-week, day-of-month (paydays) or month-of-year pattern of registered FIRs (by registration date)",
                    ["day of week pattern for chain snatching", "which months see the most burglary",
                     "does snatching rise around paydays"],
                    TimePattern, _t26),
    "T27": Template("T27", "Side-by-side comparison of two or more districts, police stations or years: FIR counts and case outcomes",
                    ["compare conviction rate of Bengaluru City and Mysuru", "theft in Hassan vs Mandya",
                     "murder cases 2022 vs 2023 in Belagavi"], CompareSides, _t27),
    "T28": Template("T28", "Case outcomes by the Act or section a case was registered under (conviction, charge-sheet, arrest rates)",
                    ["which act sections have the lowest conviction rate", "conviction rate under the NDPS Act"],
                    ActOutcomes, _t28),
    "T29": Template("T29", "What links two FIRs: the keys they share (accused, vehicle, UPI ID, IP address, modus operandi, station, district, crime)",
                    ["what links FIR PRF-2025-909767 and FIR PRF-2025-909775"], FirPair, _t29),
    "T30": Template("T30", "What a festival or event does to registered crime (Deepavali, Dasara, Ganesha, Ugadi, Sankranti, Ramzan, New Year), measured from past FIRs",
                    ["what spikes before Deepavali, and where", "crime during Mysuru Dasara"], EventEffect, _t30),
    "AST": Template("AST", "(internal) Dynamic AST query representation",
                    ["(internal)"], ASTParams, _t_ast, internal=True),
}

TEMPLATE_LIST_FOR_LLM = "\n".join(
    f"- {t.id}: {t.description}. params: {list(t.param_model.model_fields.keys())}. "
    f"e.g. {t.examples[0]!r}"
    for t in TEMPLATES.values() if not t.internal
)


def build_spec(template_id: str, params: dict) -> QuerySpec:
    """Validate params for a template and build its QuerySpec. Raises on unknown id / bad params."""
    tmpl = TEMPLATES.get(template_id)
    if not tmpl:
        raise KeyError(f"Unknown template_id {template_id!r}. Valid: {list(TEMPLATES)}")
    # The LLM frequently emits explicit nulls or empty strings (e.g. {"limit": null} or
    # {"limit": ""}) for params it has no value for; either OVERRIDES the field default and
    # then fails int/str validation. Drop both so the model defaults apply.
    clean = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
    validated = tmpl.param_model(**clean)
    return need_to_know(tmpl.builder(validated))


# Roles from this rank up see case rows statewide.
STATEWIDE_FROM = "Analyst"


def scoped_posting() -> str:
    """The district this caller's case rows are limited to, or "" when they are not limited:
    no request context, a system task, a role of Analyst or above, or no posting recorded."""
    from app.core import security_context
    from app.core.auth_middleware import _RANK
    ctx = security_context.current()
    if ctx is None or ctx.origin == "system" or not ctx.posting:
        return ""
    return "" if _RANK.get(ctx.role, -1) >= _RANK[STATEWIDE_FROM] else ctx.posting


def need_to_know(spec: QuerySpec) -> QuerySpec:
    """Limit a listing of case rows to the caller's own district.

    Applies to a query that RETURNS cases (the crimes table, no aggregate, no grouping).
    Counts, trends and rankings are untouched: an Inspector may see that Mysuru City had
    134 burglaries, but reads the individual FIRs only for their own posting. If the
    officer named another district, the rows are still their own district's, and the
    context records what was asked so the answer can say so. An officer with no posting
    on record is not limited (and is counted as such), because there is nothing to limit to.
    """
    posting = scoped_posting()
    if not posting or spec.table != "crimes" or spec.aggregates or spec.group_by:
        return spec
    asked = [str(v) for f in spec.filters if f.column == "zone" and f.op == "in" for v in (f.value or [])]
    other = [z for z in asked if z.strip().upper() != posting.strip().upper()]
    filters = [f for f in spec.filters if f.column != "zone"] + [Filter("zone", "in", [posting])]
    from app.core import security_context
    ctx = security_context.current()
    if ctx is not None:
        # what the officer first asked for is kept across the further queries of one answer
        asked_for = other[:5] or (ctx.scope or {}).get("asked_for")
        ctx.scope = {"posting": posting, **({"asked_for": asked_for} if asked_for else {})}
    import dataclasses
    return dataclasses.replace(spec, filters=filters)
