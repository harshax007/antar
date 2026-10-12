"""
Antar — System Catalog  (self-healing RAG · WI-3)
=====================================================
The single hardcoded source of truth the intent parser (GLM-4) and the relational
SQL miner both validate against. The LLM may only name intents / columns / values that
appear HERE — same anti-hallucination discipline as zcql_repo's whitelisted templates,
but expressed as a schema catalog so any phrasing can be mapped to a safe query.

Pure data + deterministic helpers. No LLM, no network (except a cached DISTINCT-zone
probe). Values were verified against the live `crimes` view on 2026-07-29.
"""
from __future__ import annotations

from functools import lru_cache

from app.services.zcql_repo import (
    CRIME_TYPES, CRIME_TYPE_SYNONYMS, ALL_ZONES, BENGALURU_ZONES, REGIONS,
    normalize_crime_types, PERIODS,
)

# Columns that actually exist on the `crimes` view (probed 2026-07-29).
CRIME_COLUMNS = [
    "crime_id", "fir_number", "crime_type", "act", "acts_sections", "zone",
    "district", "station_code", "occurred_at", "status", "io_name", "lat", "lon",
]

# Free-text columns worth matching a keyword fragment against (BM25 corpus + LIKE relax).
CRIME_TEXT_COLUMNS = ["crime_type", "zone", "district", "acts_sections", "act", "status",
                      "io_name", "fir_number"]

# ── Investigation status vocabulary (real, messy values — two solved-ness buckets) ──
# NB: the executor matches on TRIM(UPPER(status)); 'Under Investigation' and
# 'under_investigation' differ after upper (space vs underscore), so BOTH are kept.
STATUS_OPEN = ["Under Investigation", "under_investigation", "Pending Trial",
               "Undetected", "Transferred - Under Investigation"]
STATUS_CLOSED = ["Convicted", "ChargeSheeted", "charge_sheeted", "Traced",
                 "Compounded", "disposed", "Disposed", "Dis/Acq", "Abated", "Other Disposal"]

STATUS_SYNONYMS: dict[str, list[str]] = {
    "unsolved": STATUS_OPEN, "open": STATUS_OPEN, "pending": STATUS_OPEN,
    # "under investigation" is one status, not every open one: it used to bring in pending
    # trial and undetected cases as well.
    "under investigation": ["Under Investigation", "under_investigation", "Transferred - Under Investigation"],
    "active": STATUS_OPEN, "ongoing": STATUS_OPEN,
    "undetected": ["Undetected"],
    "solved": STATUS_CLOSED, "closed": STATUS_CLOSED, "resolved": STATUS_CLOSED,
    "disposed": ["disposed", "Disposed"], "convicted": ["Convicted"], "traced": ["Traced"],
    "charged": ["ChargeSheeted", "charge_sheeted"],
    "chargesheeted": ["ChargeSheeted", "charge_sheeted"],
    "charge sheeted": ["ChargeSheeted", "charge_sheeted"],
    # Named statuses that had no entry, so "acquitted cases in Kodagu" listed every case there.
    "acquitted": ["Dis/Acq"], "acquittal": ["Dis/Acq"], "acquittals": ["Dis/Acq"],
    "pending trial": ["Pending Trial"], "false case": ["False Case"], "false cases": ["False Case"],
    "compounded": ["Compounded"], "abated": ["Abated"], "bound over": ["BoundOver"],
    "untraced": ["Un Traced"], "un traced": ["Un Traced"],
    # Kannada
    "ಬಗೆಹರಿಯದ": STATUS_OPEN, "ಬಾಕಿ": STATUS_OPEN, "ತನಿಖೆ": STATUS_OPEN,
    "ಬಗೆಹರಿದ": STATUS_CLOSED, "ಮುಗಿದ": STATUS_CLOSED,
}

# ── Intent taxonomy → existing whitelisted template (reroute target) ────────────
# template=None means "general list" → handled by the relational SQL miner, which can
# filter type + zone + STATUS + date and progressively relax (templates cannot filter status).
INTENTS: dict[str, dict] = {
    "list_cases":       {"template": None, "desc": "list crimes by type / zone / date / status"},
    "suspect_crimes":   {"template": "T9",  "desc": "crimes linked to a specific suspect id (Sxxxx)"},
    "suspect_lookup":   {"template": "T2",  "desc": "look up a suspect by name or alias"},
    "trend":            {"template": "T3",  "desc": "monthly crime trend / change over time"},
    "hotspots":         {"template": "T11", "desc": "which zones/districts have the most of a crime"},
    "type_breakdown":   {"template": "T13", "desc": "counts grouped by crime type"},
    "status_counts":    {"template": "T8",  "desc": "counts by investigation status"},
    "repeat_offenders": {"template": "T5",  "desc": "habitual / repeat offenders"},
    "demographics":     {"template": "T7",  "desc": "victim / suspect demographic breakdown"},
    "recent":           {"template": "T12", "desc": "most recent cases"},
    "year_summary":     {"template": "T16", "desc": "annual FIR summary for a given year"},
}

# City names in the data live as sub-zones, not "<City> City" — this is the fix for the
# "trend in Bengaluru → 0 rows" REGIONS bug (see Change_chatPage.md WI-4), applied here so
# the self-heal path resolves cities correctly.
_CITY_EXPANSIONS = {
    "bengaluru": BENGALURU_ZONES, "bangalore": BENGALURU_ZONES,
    "bengaluru city": BENGALURU_ZONES, "blr": BENGALURU_ZONES,
    "ಬೆಂಗಳೂರು": BENGALURU_ZONES, "ಬೆಂಗಳೂರ": BENGALURU_ZONES,
}


@lru_cache(maxsize=1)
def known_zones() -> list[str]:
    """DISTINCT zone values actually present in the DB (cached). Used for exact/fuzzy
    zone resolution so the miner filters on values that exist."""
    try:
        import sqlite3
        from app.core.db_path import DB_PATH
        rows = sqlite3.connect(DB_PATH).execute(
            "SELECT DISTINCT zone FROM crimes WHERE zone IS NOT NULL").fetchall()
        zones = [r[0] for r in rows if r[0]]
        return zones or list(ALL_ZONES)
    except Exception:
        return list(ALL_ZONES)


def normalize_statuses(words) -> list[str]:
    """Map NL status words (any language) → the real DB status values; drop unknowns."""
    out: list[str] = []
    known = set(STATUS_OPEN) | set(STATUS_CLOSED)
    for w in words or []:
        raw = str(w).strip()
        vals = STATUS_SYNONYMS.get(raw.lower()) or STATUS_SYNONYMS.get(raw)
        if vals:
            out.extend(vals)
        elif raw in known:
            out.append(raw)
    return list(dict.fromkeys(out))


def resolve_zones_catalog(names) -> list[str]:
    """Robust zone resolution: city → sub-zones, REGIONS expansion, exact/substring match
    against the DB's real zones. Falls back to the raw name (the miner TRIM/UPPER-matches,
    so a real district still filters)."""
    zk = known_zones()
    zk_lower = {z.lower(): z for z in zk}
    out: list[str] = []
    for n in names or []:
        raw = str(n).strip()
        key = raw.lower()
        if not key:
            continue
        if key in _CITY_EXPANSIONS:
            out.extend(_CITY_EXPANSIONS[key])
            continue
        if raw in REGIONS:
            out.extend(REGIONS[raw])
            continue
        if key in zk_lower:
            out.append(zk_lower[key])
            continue
        subs = [z for z in zk if key in z.lower() or z.lower() in key]
        if subs:
            out.extend(subs[:6])
            continue
        out.append(raw)  # last resort: pass through
    return list(dict.fromkeys(out))


def catalog_prompt() -> str:
    """Compact catalog text embedded in the GLM-4 intent-parse prompt. Keep it small."""
    intents = "\n".join(f"  - {k}: {v['desc']}" for k, v in INTENTS.items())
    return (
        "INTENTS (pick exactly one):\n" + intents + "\n\n"
        "CRIME TYPES (canonical): " + ", ".join(CRIME_TYPES) + "\n"
        "ZONES (examples): " + ", ".join(ALL_ZONES[:14]) + ", …\n"
        "STATUS words: unsolved/open/pending/undetected (open) · solved/closed/convicted/"
        "chargesheeted (closed)\n"
        "PERIODS: " + ", ".join(PERIODS) + "\n"
        "IDS: suspect id looks like S0005; FIR looks like 2025-MYS-0089."
    )
