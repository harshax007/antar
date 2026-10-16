"""
Antar — Heuristic Router (offline / DEMO_MODE fallback)
============================================================
A deterministic, no-LLM mapping of NL → {template_id, params}. Used when QuickML
credentials aren't configured yet (local dev before G4) and as a resilient
DEMO_MODE fallback if the LLM is slow/unavailable mid-demo.

It is NOT a replacement for the LLM supervisor/selector — it's keyword-based and
covers the common + demo queries. In production with G4 green, the LLM path runs.
"""

from __future__ import annotations

import datetime as _dt
import re
from functools import lru_cache

from app.services.zcql_repo import (CRIME_TYPES, ALL_ZONES, REGIONS, WOMEN_CRIMES,
                                    CRIME_TYPE_SYNONYMS, normalize_crime_types)
from app.agents.system_catalog import STATUS_SYNONYMS, normalize_statuses

_ZONE_LOOKUP = {z.lower(): z for z in ALL_ZONES}
_REGION_LOOKUP = {r.lower(): r for r in REGIONS}
_MONTHS_RE = re.compile(r"(\d+)\s*month")

# Zero-width joiners/non-joiners appear in real Kannada input (e.g. 'ಹಾಟ್‌ಸ್ಪಾಟ್') and
# break naive substring matching — strip them before any keyword/entity check.
_ZW = dict.fromkeys(map(ord, "‌‍​"), None)


def _norm(s: str) -> str:
    """Lowercase + strip zero-width chars so EN and KN keyword matching is robust."""
    return (s or "").translate(_ZW).lower()


# Kannada → English zone / region names (demo-relevant). Values must be real zones
# (ALL_ZONES) or REGIONS keys so resolve_zones() can expand/validate them.
_KN_ZONES = {
    "ರಾಜಾಜಿನಗರ": "Rajajinagar", "ಗಾಂಧಿನಗರ": "Gandhinagar", "ಜಯನಗರ": "Jayanagar",
    "ಮಲ್ಲೇಶ್ವರಂ": "Malleshwaram", "ಇಂದಿರಾನಗರ": "Indiranagar", "ವೈಟ್ಫೀಲ್ಡ್": "Whitefield",
    "ಯಶವಂತಪುರ": "Yeshwanthpur", "ಬನಶಂಕರಿ": "Banashankari", "ಹೆಬ್ಬಾಳ": "Hebbal",
    "ಮೈಸೂರು": "Mysuru",
}
# District / city names officers use in Kannada (values: REGIONS keys or real zone labels).
_KN_ZONES.update({
    "ಬೆಂಗಳೂರು ನಗರ": "Bengaluru City", "ಬೆಂಗಳೂರು": "Bengaluru", "ಬೆಳಗಾವಿ": "Belagavi",
    "ಮಂಗಳೂರು": "Mangalore", "ಹುಬ್ಬಳ್ಳಿ": "Hubli", "ಕಲಬುರಗಿ": "Kalaburagi", "ತುಮಕೂರು": "Tumakuru",
    "ಶಿವಮೊಗ್ಗ": "Shivamogga", "ಬಳ್ಳಾರಿ": "Ballari", "ಉಡುಪಿ": "Udupi", "ಮಂಡ್ಯ": "Mandya",
    "ಹಾಸನ": "Hassan",
})

# Words that follow "in/at/from" but are not places ("in 2023", "in the last month").
_NOT_PLACES = {"ip", "upi", "acc", "karnataka", "india", "the", "this", "last", "next", "past", "my", "our", "all",
               "total", "general", "ipc", "bns", "sll", "fir", "firs", "january", "february",
               "march", "april", "may", "june", "july", "august", "september", "october",
               "november", "december"}

# Longest phrase first — "last 30 days" must win before "last 3".
# Day-level words were missing entirely, so "how many thefts yesterday" carried no period
# at all and the date filter never existed: the officer got the all-time count.
_PERIOD_WORDS = [
    ("last 6 months", "last_6_months"), ("past 6 months", "last_6_months"),
    ("last 3 months", "last_3_months"), ("past 3 months", "last_3_months"),
    ("last 30 days", "last_30_days"), ("past 30 days", "last_30_days"),
    ("last 7 days", "last_7_days"), ("past 7 days", "last_7_days"),
    ("last 24 hours", "last_24_hours"), ("past 24 hours", "last_24_hours"),
    ("last month", "last_month"), ("previous month", "last_month"), ("this month", "this_month"),
    ("last week", "last_week"), ("past week", "last_week"), ("this week", "this_week"),
    ("day before yesterday", "last_2_days"),
    ("yesterday", "yesterday"), ("today", "today"), ("tonight", "today"),
    ("so far this year", "this_year"), ("year to date", "this_year"),
    ("ಕಳೆದ 3 ತಿಂಗಳು", "last_3_months"), ("ಕಳೆದ ತಿಂಗಳು", "last_month"), ("ಈ ತಿಂಗಳು", "this_month"),
    ("ಕಳೆದ ವಾರ", "last_week"), ("ಈ ವಾರ", "this_week"),
    ("ನಿನ್ನೆ", "yesterday"), ("ಇಂದು", "today"), ("ಇವತ್ತು", "today"),
]


@lru_cache(maxsize=1)
def _db_places() -> dict[str, str]:
    """Every zone label actually present in the FIR data ("Bengaluru City", "Mysuru Dist", …).
    The static lists only held the 16 synthetic zones, so real district names were never
    recognised and "how many murders in Bengaluru City?" answered for all of Karnataka."""
    try:
        import sqlite3
        from app.core.db_path import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        vals = [r[0] for r in conn.execute("SELECT DISTINCT zone FROM crimes WHERE zone IS NOT NULL")]
        conn.close()
        return {str(v).strip().lower(): str(v).strip() for v in vals if v and len(str(v).strip()) > 3}
    except Exception:
        return {}


def _match_places(low: str) -> list[str]:
    """Place names in the text; the most specific wins ("bengaluru city" over the "bengaluru"
    region it contains, "bengaluru north" over "bengaluru")."""
    found: dict[str, str] = {}
    for k, v in {**_db_places(), **_ZONE_LOOKUP, **_REGION_LOOKUP}.items():
        if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", low):
            found[k] = v
    for k, v in _KN_ZONES.items():
        if _norm(k) in low:
            found[_norm(k)] = v
    keep = [v for k, v in found.items() if not any(k != o and k in o for o in found)]
    return list(dict.fromkeys(keep))


def _syn_hit(key: str, low: str) -> bool:
    """Whole-word synonym match that also accepts plurals ("robberies", "murders")."""
    k = _norm(key)
    if not k.isascii():
        return k in low
    stem = (re.escape(k[:-1]) + r"(?:y|ies)") if k.endswith("y") else (re.escape(k) + r"(?:s|es)?")
    return re.search(r"(?<![a-z])" + stem + r"(?![a-z])", low) is not None


# ── Kannada → English rule bridge ────────────────────────────────────────────
# The routing rules below are written in English keywords, and Kannada terms were added
# to them one at a time, so the SAME question routed differently in the two languages:
# a battery of the 50-question bank found 18 of 57 Kannada questions landing on a
# different template than their English twin ("ಚಾರ್ಜ್‌ಶೀಟ್ ಪಾಲು" fell back to a plain
# count instead of the case-outcome template).
#
# Rather than repeat every keyword in both languages forever, we append the English
# equivalent of any Kannada analytic term we find. The rules stay single-language, and a
# Kannada question reaches exactly the rule its English twin does. Entity extraction
# (zones, crime types, periods) keeps its own Kannada tables — this bridge only feeds the
# keyword rules.
_KN_BRIDGE = {
    # what is being asked for
    "ಸಂಜ್ಞೇಯ": "cognizable", "ದಾಖಲಾದ": "registered", "ದಾಖಲಾಗಿವೆ": "registered",
    "ಚಾರ್ಜ್ಶೀಟ್": "chargesheet", "ದೋಷಾರೋಪ": "chargesheet", "ಆರೋಪಪಟ್ಟಿ": "chargesheet",
    "ಶಿಕ್ಷೆ": "conviction", "ಅಪರಾಧ ಸಾಬೀತು": "conviction",
    "ಪತ್ತೆ ಪ್ರಮಾಣ": "detection rate", "ಇತ್ಯರ್ಥ": "disposal rate",
    "ಪಾಲು": "share", "ಶೇಕಡಾ": "percentage", "ಪ್ರಮಾಣ": "rate",
    "ಕಾಗ್ನಿಸಬಲ್": "cognizable", "ರಾಜ್ಯಾದ್ಯಂತ": "statewide", "ಅಪರಾಧ ವರ್ಗ": "crime type",
    "ಅಪರಾಧ ಪ್ರಕಾರ": "crime type", "ಪ್ರಾಬಲ್ಯ": "dominates", "ಅಂಕಿಅಂಶ": "statistics",
    # units of grouping
    "ಠಾಣೆ": "station", "ಪೊಲೀಸ್ ಠಾಣೆ": "police station", "ಬೀಟ್": "beat",
    "ಜಿಲ್ಲೆ": "district", "ಜಿಲ್ಲಾ": "district", "ವಲಯ": "zone", "ವಿಭಾಗ": "category",
    "ವಾರದ ದಿನ": "weekday", "ತಿಂಗಳು": "month", "ವರ್ಷ": "year", "ಋತು": "season",
    "ಕಾಲೋಚಿತ": "seasonal",
    # shape of the question
    "ಪ್ರವೃತ್ತಿ": "trend", "ಏರಿಳಿತ": "trend", "ಬೆಳೆಯುತ್ತಿರುವ": "growing",
    "ವೇಗವಾಗಿ": "fastest", "ಹೆಚ್ಚಳ": "increase", "ಇಳಿಕೆ": "decrease",
    "ಹೋಲಿಸಿದರೆ": "compared", "ಹೋಲಿಕೆ": "comparison",
    "ಪ್ರಚಲಿತ": "prevalent", "ಸಾಮಾನ್ಯ": "common", "ಒಟ್ಟಾರೆ": "overall",
    "ಹಾಟ್ಸ್ಪಾಟ್": "hotspot", "ಮುನ್ಸೂಚನೆ": "forecast", "ಮುನ್ಸೂಚಿಸಿ": "forecast",
    "ಟಾಪ್": "top", "ಅತಿ ಹೆಚ್ಚು": "most", "ಹೆಚ್ಚು": "most", "ಅತ್ಯಂತ ಕಡಿಮೆ": "lowest",
    "ಕಡಿಮೆ": "lowest", "ಯಾವ": "which", "ಎಲ್ಲಿ": "where", "ಎಷ್ಟು": "how many",
    "ಒಟ್ಟು": "total", "ಪಟ್ಟಿ": "list", "ಸಾರಾಂಶ": "summary", "ಎಲ್ಲಾ": "all",
    # people and links
    "ಆರೋಪಿ": "accused", "ಅಪರಾಧಿ": "offender", "ಸಂಶಯಿತ": "suspect",
    "ಒಟ್ಟಿಗೆ": "together", "ಜೊತೆಗೆ": "together", "ಸಂಪರ್ಕ": "linked", "ಕೊಂಡಿ": "linked",
    "ಜಾಲ": "network", "ಗುಂಪು": "group",
    # case state
    "ಬಾಕಿ": "pending", "ಬಗೆಹರಿಯದ": "unsolved", "ತನಿಖೆ": "investigation",
    "ತಲೆಮರೆಸಿಕೊಂಡ": "absconding",
}
_SCRIPT_SEAM = re.compile(r"(?<=[0-9a-z])(?=[ಀ-೿])|(?<=[ಀ-೿])(?=[0-9a-z])")
# Longest Kannada terms first, so "ಅತಿ ಹೆಚ್ಚು" wins before "ಹೆಚ್ಚು".
_KN_BRIDGE_ORDER = sorted(_KN_BRIDGE.items(), key=lambda kv: -len(kv[0]))


def kn_bridge(low: str) -> str:
    """Append the English equivalent of every Kannada analytic term present.

    Additive only: the original text is untouched, so a rule that already matched a
    Kannada keyword keeps matching. Idempotent for English input.
    """
    if not low or not any("ಀ" <= ch <= "೿" for ch in low):
        return low
    # Kannada fuses case suffixes onto numbers and Latin words: "2023ರಲ್ಲಿ", "FIRಗಳು".
    # A Kannada letter is a word character to the regex engine, so \b2023\b never matched
    # and the year was silently lost. Split at every script boundary first.
    low = _SCRIPT_SEAM.sub(" ", low)
    extra = []
    for kn_term, en_term in _KN_BRIDGE_ORDER:
        if kn_term in low and en_term not in extra:
            extra.append(en_term)
    return f"{low} {' '.join(extra)}" if extra else low


def is_kannada(text: str) -> bool:
    """Detect Kannada by Unicode block U+0C80–U+0CFF (no LLM needed)."""
    return any("ಀ" <= ch <= "೿" for ch in text)


# Phrases that can only be ABOUT the previous answer ("why did you say that").
_EXPLAIN_PHRASES = ["why did you", "why do you", "how did you", "how do you know",
                    "explain that", "explain this", "explain the answer", "explain your",
                    "show your reasoning", "your reasoning",
                    "ನೀವು ಏಕೆ", "ನೀವು ಹೇಗೆ", "ಇದನ್ನು ವಿವರಿಸಿ", "ಹೇಗೆ ತಿಳಿಯಿತು"]
# A bare "why?" on its own line is an explain request; the same word inside a real
# question is not. Matching the substring is what sent "What should the night shift
# watch tonight, and why?" and every Kannada question containing "ಹೇಗೆ" (how) to the
# explain path, which then answered "there is no previous answer to explain".
_EXPLAIN_BARE = {"why", "why?", "why is that", "how", "explain", "reasoning",
                 "ಏಕೆ", "ಏಕೆ?", "ಯಾಕೆ", "ಯಾಕೆ?", "ವಿವರಿಸಿ", "ಹೇಗೆ"}
_EXPLAIN_MAX_WORDS = 4


def is_explain_request(text: str, has_previous: bool = True) -> bool:
    """True if the user is asking us to justify the previous answer (Explain / M9).

    Only explicit phrases ("why did you…") or a bare "why?" of a few words count. A lone
    "why?" with nothing answered yet is still an explain request; the caller replies
    that there is nothing to explain yet. `has_previous` is accepted for callers that
    know the history, but the word-count rule is what separates a real question
    containing "why" from a request to justify.
    """
    low = " ".join((text or "").lower().strip().split())
    if not low:
        return False
    if any(p in low for p in _EXPLAIN_PHRASES):
        return True
    stripped = low.rstrip("?.!।").strip()
    return stripped in _EXPLAIN_BARE or (
        len(stripped.split()) <= _EXPLAIN_MAX_WORDS
        and any(w.rstrip("?.!।") in _EXPLAIN_BARE for w in stripped.split())
    )


# ── Slash commands (/think /connect /anticipate) ───────────────────────────────
# Brand verbs exposed as chat commands: /think = full reasoning trail,
# /connect = force linkage agents (network/profile), /anticipate = force
# forecast agents (geo/predict/pattern).
_SLASH_RE = re.compile(r"^/(think|connect|anticipate)\b[:\s]*(.*)$", re.IGNORECASE | re.DOTALL)

SLASH_COMMANDS = {
    "think":      {"forces": [],                             "deep_think": True,
                   "label": "Deep reasoning — full trail shown"},
    "connect":    {"forces": ["network", "profile"],         "deep_think": False,
                   "label": "Linkage mode — network & profile agents forced"},
    "anticipate": {"forces": ["geo", "predict", "pattern"],  "deep_think": False,
                   "label": "Forecast mode — geo, predict & pattern agents forced"},
}


def parse_slash_command(text: str) -> tuple[str | None, str]:
    """Parse a leading /think, /connect or /anticipate command.

    Returns (command, remaining_text). command is None when the text does not
    start with a known slash command. A bare command (no question after it)
    returns the command with remaining_text == "".
    """
    m = _SLASH_RE.match(text.strip())
    if not m:
        return None, text
    return m.group(1).lower(), m.group(2).strip()


def _match_crime_terms(low: str) -> list[str]:
    """Crime labels and synonyms found in the text, LONGEST MATCH FIRST.

    Two bugs lived in the line this replaces:

        [c for c in CRIME_TYPES if c.replace("_", " ") in low or c in low]

    **Case.** `low` is lowercased by `_norm`, and every entry in `CRIME_TYPES` is the
    registry's own UPPERCASE label — `'RIOTS' in 'how many riots cases'` is False. That
    comparison never matched anything, so all 115 registry labels were unreachable by
    their own names and only the 71 hand-written synonyms worked. `RIOTS` (19,825 FIRs)
    simply vanished from the question, the crime filter came out empty, and the answer
    became the size of the whole registry — tagged `[VERIFIED]`, at 0.99 confidence.

    **Specificity.** Synonyms matched as substrings, so `murder` claimed
    "attempt to murder" and the officer got an answer about a different offence.
    `ATTEMPT TO MURDER` is its own crime group.

    Now: candidates are matched on word boundaries, tried longest first, and a match is
    rejected if its span overlaps one already claimed. "attempt to murder" therefore wins
    over "murder", and `AFFRAY`/`CRPC`/`RIOTS` are reachable without a curated synonym.
    """
    claimed: list[tuple[int, int]] = []
    found: list[str] = []
    # (surface form, canonical value). Registry labels and synonyms compete in one pass —
    # whichever is longer wins the span, regardless of which list it came from.
    cands: list[tuple[str, str]] = [(str(c).replace("_", " "), c) for c in CRIME_TYPES]
    cands += [(str(k), v) for k, v in CRIME_TYPE_SYNONYMS.items()]
    for surface, canon_val in sorted(cands, key=lambda kv: -len(kv[0])):
        s = _norm(surface)
        if not s:
            continue
        if not s.isascii():
            idx = low.find(s)
            if idx < 0:
                continue
            span = (idx, idx + len(s))
        else:
            # Same plural tolerance as _syn_hit, so "robberies" and "murders" still match.
            stem = (re.escape(s[:-1]) + r"(?:y|ies)") if s.endswith("y") else (re.escape(s) + r"(?:s|es)?")
            m = re.search(r"(?<![a-z])" + stem + r"(?![a-z])", low)
            if not m:
                continue
            span = m.span()
        if any(span[0] < c_hi and c_lo < span[1] for c_lo, c_hi in claimed):
            continue                      # a longer, more specific term already took it
        claimed.append(span)
        found.append(canon_val)
    return found


def _volume_q(low: str) -> bool:
    """A ranking of ALL crime: "by FIR volume", "most FIRs", "busiest stations"."""
    return bool(re.search(r"\b(fir volume|by volume|volume of firs?|most firs|by firs?|busiest)\b", low)
                or "ಪ್ರಮಾಣದ ಪ್ರಕಾರ" in low)


def extract_entities(text: str, history: list[dict] | None = None) -> dict:
    """Pull crime_types, zones (incl. regions), months hint, geo dimensions, limits, and date ranges from EN or KN text.
    Carries over missing entities from the immediate previous user turn if history is provided."""
    low = _norm(text)
    crime_types = _match_crime_terms(low)
    if "snatch" in low and "chain_snatching" not in crime_types:
        crime_types.append("chain_snatching")
    # The word "vehicle" used to add vehicle theft to every question that contained it:
    # "motor vehicle accidents fatal in Mysuru City" was answered as accidents PLUS thefts.
    if "vehicle" in low and "vehicle_theft" not in crime_types \
            and not any("VEHICLE" in str(c).upper() for c in crime_types) and "accident" not in low:
        crime_types.append("vehicle_theft")
    # The register files burglary by day and by night; a question that says which one gets it.
    if any(str(c).upper() == "BURGLARY" for c in crime_types):
        _when = ("NIGHT" if re.search(r"\b(at night|by night|night[- ]?time|night)\b", low)
                 else "DAY" if re.search(r"\b(by day|day[- ]?time|during the day|in the day)\b", low) else None)
        if _when:
            crime_types = [f"BURGLARY - {_when}" if str(c).upper() == "BURGLARY" else c for c in crime_types]
    # "crimes against women" names a category; "chain snatching by women" names who did it,
    # which is not a crime type (and not something the templates can filter on).
    if (re.search(r"\b(women|woman)\b", low) and not re.search(
            r"\bby (?:a |the )?wom[ae]n\b|\bwom[ae]n (?:accused|offenders?|suspects?)\b|"
            r"\bwom[ae]n (?:who |that )?(?:were |was |are |is |got |have been )?(?:arrested|accused|caught|convicted|charged|booked|involved)\b", low)) \
            or "ಮಹಿಳೆ" in low:
        crime_types += WOMEN_CRIMES
    crime_types = normalize_crime_types(crime_types)          # canonicalize + de-dup
    zones = _match_places(low)
    unknown_place = None
    if not zones:
        # A capitalised place the data doesn't know ("theft in Atlantis"). The answer must say
        # so up front instead of silently answering for all of Karnataka as if that had been
        # the question; the query itself runs state-wide.
        m = re.search(r"\b(?:in|at|from|near)\s+([A-Z][a-zA-Z.]+(?:\s+[A-Z][a-zA-Z.]+)?)", text or "")
        if m and m.group(1).split()[0].lower() not in _NOT_PLACES:
            unknown_place = m.group(1).strip()
    months = None
    m = _MONTHS_RE.search(low)
    if m:
        months = int(m.group(1))

    # Extract limit (e.g. top 10, top 5)
    limit_val = 10
    top_match = re.search(r"\b(?:top|first|first\s+top|last)\s+(\d+)\b(?!\s*(?:hours?|days?|weeks?|months?|years?)\b)", low)
    if top_match:
        try:
            limit_val = max(1, min(int(top_match.group(1)), 100))
        except ValueError:
            pass

    # Extract geo dimension (city/district/zone vs station)
    geo_dim = "zone"
    if any(w in low for w in ("station", "stations", "station code", "police station", "ps", "ಠಾಣೆ")):
        geo_dim = "station_code"

    # Extract year / date range
    date_from, date_to, period = None, None, None
    # `202\d` only. The registry starts in **2016**, so "in 2018" and "in 2016"
    # matched nothing and the year filter was silently dropped - the officer asked about
    # one year and got every year, still tagged [VERIFIED] at 0.99 confidence. Measured on
    # the calibration set: "attempt to murder in Kodagu in 2018" answered 197 (all years)
    # against a true 25. A wider pattern lower in this same file already disagreed with
    # this one about what a year looks like.
    # No upper bound either: a year past the register ("the split for 2028") used to fail
    # the range test here, lose its filter the same way, and be answered with all years.
    # A year the register does not hold is refused by query_agent.outside_record().
    #
    # And a year is not the only way to name a period. "March 2023", "Q1 2023", "from
    # January to March 2023", "15 August 2023", "since 2020", "before 2019", "the last 2
    # years" were all reduced to a calendar year or lost. app/agents/timespan.py reads the
    # window that was asked for; `period_label` carries its wording to the answer.
    period_label, span_kind = None, None
    from app.agents.timespan import find_span
    from app.services.zcql_repo import data_first_year, data_today
    # Kannada fuses its case suffix onto the year ("2022ರಲ್ಲಿ"); split the seam first or
    # \b never matches and the question is answered for every year on record.
    span = find_span(_SCRIPT_SEAM.sub(" ", low), data_today(), data_first_year())
    if span:
        date_from, date_to = span.date_from, span.date_to
        period_label, span_kind = span.label, span.kind
    elif "this year" in low or "ಈ ವರ್ಷ" in low:
        period = "this_year"
    elif "last year" in low or "ಹಿಂದಿನ ವರ್ಷ" in low:
        period = "last_year"
    else:
        period = next((p for k, p in _PERIOD_WORDS if k in low), None)

    # Contextual carry-over from history
    if history and len(history) >= 2:
        last_user = next((t for t in reversed(history[:-1]) if t.get("role") == "user"), None)
        if last_user:
            prev_ent = extract_entities(last_user["text"], history=None)
            if not crime_types and prev_ent.get("crime_types"):
                crime_types = prev_ent["crime_types"]
            if not zones and prev_ent.get("zones"):
                zones = prev_ent["zones"]

    # status words (unsolved/open/solved…) — word-boundary so 'solved' does not fire in 'unsolved'
    statuses = []
    for k in STATUS_SYNONYMS:
        kl = _norm(k)
        if (kl.isascii() and re.search(r"\b" + re.escape(kl) + r"\b", low)) or (not kl.isascii() and kl in low):
            statuses.append(k)
    if "pending trial" in statuses:
        statuses = [s for s in statuses if s != "pending"]     # the longer phrase is the one meant
    statuses = normalize_statuses(statuses)

    return {
        "crime_types": crime_types, "zones": zones, "months": months,
        "limit": limit_val, "dimension": geo_dim, "statuses": statuses,
        "date_from": date_from, "date_to": date_to, "period": period,
        "period_label": period_label, "span_kind": span_kind,
        "unknown_place": unknown_place,
    }


async def heuristic_select(user_text: str, lang: str, entities: dict | None = None, history: list[dict] | None = None) -> dict:
    """
    Map a question to {template_id, params, answer_lang} with keyword rules and Context Engineering.
    Mirrors the LLM selector's output shape so query_agent_run can use it directly.
    """
    # Kannada questions reach the same English keyword rules as their English twin.
    low = kn_bridge(_norm(user_text))
    ent = entities or extract_entities(user_text, history)
    ct = ent.get("crime_types") or []
    zones = ent.get("zones") or []
    months = ent.get("months") or 6        # 6 complete-ish months → a real direction, not 2 points
    limit_val = ent.get("limit") or 10
    geo_dim = ent.get("dimension") or "zone"
    date_from = ent.get("date_from")
    date_to = ent.get("date_to")
    period = ent.get("period")
    statuses = ent.get("statuses") or []
    answer_lang = lang or ("kn" if is_kannada(user_text) else "en")

    unknown_place = ent.get("unknown_place")
    period_label, span_kind = ent.get("period_label"), ent.get("span_kind")

    def choice(tid, params):
        if unknown_place and tid not in ("T2", "T5", "T7", "T9", "T18", "T19", "T20", "T21", "RESEARCH"):
            params = {**params, "unknown_place": unknown_place}   # the writer flags it
        if period_label and params.get("date_from") and span_kind != "year":
            params = {**params, "period_label": period_label}     # how the answer names the window
        # "which station in Bengaluru City has the most thefts" ranks stations INSIDE the
        # district. The ranking had no place filter, so it ranked every station in the state.
        if tid == "T11" and zones and params.get("dimension") == "station_code":
            params = {**params, "zones": zones}
        return {"template_id": tid, "params": params, "answer_lang": answer_lang}

    # suspect linkage: "what crimes is S0005 linked to" → T9 (deterministic reroute, WI-4)
    # Any suspect id ("profile of S0005", "show network of S0005") is a question about THAT
    # person: their linked cases are the grounded answer and the profile/network agents add
    # their sections on top. Without this "profile of S0005" listed all 419k FIRs.
    # ── Identifier questions come first: an exact ID in the question is the strongest signal.
    # T21 accused history: "cases for accused ACC-KA-500777"
    _acc = re.search(r"\bACC[\s_-]?KA[\s_-]?(\d{3,7})\b", (user_text or "").upper())
    if _acc:
        return choice("T21", {"accused_id": f"ACC-KA-{_acc.group(1)}"})
    # T20 identifier lookup: "cases linked to IP 103.87.106.22", "FIRs for UPI user1101@bank"
    _ip = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", user_text or "")
    if _ip:
        return choice("T20", {"key_type": "ip", "value": _ip.group(0)})
    # A UPI handle is name@provider with no dot after the @ (that would be an e-mail address).
    _upi = re.search(r"(?<![\w.@-])([\w.\-]{2,}@[A-Za-z][A-Za-z0-9]{1,20})(?![\w.@-])", user_text or "")
    if _upi:
        return choice("T20", {"key_type": "upi", "value": _upi.group(1)})
    # T19 cross-station links: "which UPI IDs are used in more than one district"
    _kt = ("upi" if re.search(r"\bupi\b", low) else
           "ip" if re.search(r"\bip\b|\bip address", low) else
           "vehicle" if (re.search(r"\b(vehicles?|number plates?|registration numbers?)\b", low) or "ವಾಹನ" in low)
                        and "theft" not in low and "ಕಳ್ಳತನ" not in low else
           "accused" if re.search(r"\b(accused|offenders?|criminals?)\b", low) or "ಆರೋಪಿ" in low else
           "any")
    _spread = bool(
        (re.search(r"\b(across|multiple|more than one|several|different|shared|same|common|"
                   r"cross[- ]?(district|station|city|jurisdiction)s?|in \d+ (or more )?districts)\b", low)
         and re.search(r"\b(districts?|stations?|cities|city|jurisdictions?)\b", low))
        or any(w in low for w in ("ಜಿಲ್ಲೆಗಳಲ್ಲಿ", "ಜಿಲ್ಲೆಗಳಾದ್ಯಂತ", "ಹಲವು ಜಿಲ್ಲೆ", "ಠಾಣೆಗಳಾದ್ಯಂತ", "ಬೇರೆ ಬೇರೆ ಜಿಲ್ಲೆ")))
    if _spread and (_kt != "any" or re.search(r"\b(identifiers?|links?|linked|connections?|connected|connects?)\b", low)):
        _md = re.search(r"\b(\d{1,2})\s*(?:\+|or more)?\s*districts\b", low)
        _min = int(_md.group(1)) if _md and int(_md.group(1)) >= 2 else 2
        # The word "vehicle" auto-adds VEHICLE_THEFT in extract_entities; for a link question
        # ("vehicles used in 3 districts") that filter is noise unless theft was actually said.
        _ct19 = [c for c in ct if not (c == "VEHICLE_THEFT" and "theft" not in low and "ಕಳ್ಳತನ" not in low)]
        return choice("T19", {"key_type": _kt, "min_districts": _min, "zones": zones,
                              "crime_types": _ct19, "limit": limit_val})

    # Vehicle registration ("Check if vehicle KA-02-M-2093 has any pending challans or FIRs").
    # Checked first: words like "pending" otherwise routed it to the case-status breakdown.
    _plate = re.search(r"\b([A-Z]{2})[\s-]?(\d{1,2})[\s-]?([A-Z]{1,3})[\s-]?(\d{1,4})\b", (user_text or "").upper())
    if _plate and (re.search(r"\b[A-Z]{2}-\d{1,2}-[A-Z]{1,3}-\d{1,4}\b", (user_text or "").upper())
                   or re.search(r"\b[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}\b", (user_text or "").upper())
                   or re.search(r"\b(vehicle|plate|registration|reg no|challan|car|bike|number)\b", low)
                   or any(w in low for w in ("ವಾಹನ", "ಚಲನ್"))):
        return {"template_id": "T18", "answer_lang": answer_lang,
                "params": {"plate": "-".join(_plate.groups())}}

    _sid = re.search(r"\bS\d{3,}\b", user_text, re.IGNORECASE)
    if _sid:
        return choice("T9", {"suspect_id": _sid.group(0).upper()})

    # deep research / KUL
    if any(w in low for w in ["deep research", "investigate", "everything about", "who could be behind", "research", "kul", "dossier"]):
        anchor_val = _extract_name(user_text) or (zones[0] if zones else user_text.replace("deep research", "").replace("research", "").replace("investigate", "").replace("on", "").strip())
        return choice("RESEARCH", {"anchor": anchor_val or user_text})

    # "suspects with more than 3 cases" is the repeat-offender list with its own bar. It
    # used to match nothing, and self-heal answered with every FIR on record.
    _many = re.search(r"\b(?:suspects?|offenders?|accused|criminals?|persons?|people)\s+(?:with|having|who have)\s+"
                      r"(more than|over|at least|above)\s+(\d{1,3})\s+(?:prior\s+|previous\s+)?(?:cases|firs|priors|offences|crimes)\b", low)
    if _many:
        n = int(_many.group(2)) + (0 if _many.group(1) == "at least" else 1)
        return choice("T5", {"min_priors": max(1, n), "limit": limit_val, "zones": zones})
    # repeat offenders
    if any(w in low for w in ["repeat offender", "habitual", "repeat criminal",
                              "ಪುನರಾವರ್ತಿತ", "ಪದೇಪದೇ", "ಅಭ್ಯಾಸ ಅಪರಾಧಿ"]):
        return choice("T5", {"min_priors": 5, "limit": limit_val, "zones": zones})
    # demographics
    # "age" as a whole word — as a substring it fired on "percentage", "average", "damage".
    _age = bool(re.search(r"\bages?\b", low))
    if _age or any(w in low for w in ["demographic", "gender", "victim",
                                      "ವಯಸ್ಸು", "ಲಿಂಗ", "ಸಂತ್ರಸ್ತ", "ಜನಸಂಖ್ಯಾ"]):
        entity = "victims" if ("victim" in low or "ಸಂತ್ರಸ್ತ" in low) else "suspects"
        dim = "age_band" if (_age or "ವಯಸ್ಸು" in low) else "gender"
        return choice("T7", {"entity": entity, "dimension": dim})
    # top suspects (MUST be checked before T11 so 'top suspects in Rajajinagar' routes to T4)
    if "top suspect" in low or ("suspect" in low and ("top" in low or "most" in low)) \
            or "ಪ್ರಮುಖ ಸಂಶಯಿತ" in low:
        return choice("T4", {"zones": zones, "limit": limit_val})

    years = sorted(set(re.findall(r"\b(20[12]\d)\b", low)))
    status_q = bool(statuses) or any(w in low for w in ("status", "open case", "pending",
                                                         "ತೆರೆದ", "ಸ್ಥಿತಿ", "ಬಾಕಿ"))
    rank_q = bool(re.search(r"\b(which|where|top|most|highest|hotspots?|rank|ranking|least|lowest|fewest|safest)\b", low)) \
        or any(w in low for w in ("ಯಾವ", "ಎಲ್ಲಿ", "ಅತಿ ಹೆಚ್ಚು", "ಕಡಿಮೆ", "ಹಾಟ್ಸ್ಪಾಟ್"))
    count_q = bool(re.search(r"\b(how many|how much|total|number of|count|statewide)\b", low)) \
        or "ಎಷ್ಟು" in low or "ಒಟ್ಟು" in low \
        or bool(years and re.search(r"\b(firs?|registered)\b", low))
    dates = {"date_from": date_from, "date_to": date_to, "period": period}
    # Case outcomes — "conviction rate by district in 2023", "charge sheet rate for murder"
    if re.search(r"\b(convict\w*|charge[- ]?sheet\w*|chargesheet\w*|arrest rates?|detection rates?|"
                 r"clearance rates?|disposal rates?|case outcomes?|outcomes? of cases|solv(e|ing) rates?)\b", low) \
            or any(w in low for w in ("ಶಿಕ್ಷೆ ಪ್ರಮಾಣ", "ಶಿಕ್ಷೆಯ ಪ್ರಮಾಣ", "ದೋಷಾರೋಪ", "ಬಂಧನ ಪ್ರಮಾಣ", "ಶಿಕ್ಷೆ ದರ")):
        _dim = ("district" if (re.search(r"\b(districts?|zones?|cities|district[- ]?wise|zone[- ]?wise)\b", low)
                               or "ಜಿಲ್ಲೆ" in low or "ಜಿಲ್ಲಾ" in low) else
                "crime_type" if re.search(r"\b(crime types?|by crime|which crimes?|type of crime|crime[- ]?wise)\b", low)
                else "none")
        _ord = "asc" if re.search(r"\b(lowest|worst|poorest|least|bottom|weakest|low)\b", low) or "ಕಡಿಮೆ" in low else "desc"
        return choice("T22", {"zones": zones, "crime_types": ct, "dimension": _dim, "order": _ord,
                              "limit": limit_val, **dates})
    # Beat / village-area hotspots — "top beats for theft in Bengaluru City"
    _beat = bool(re.search(r"\b(beats?|beat[- ]?wise)\b", low) or "ಬೀಟ್" in low)
    _area = bool(re.search(r"\b(villages?|localit(y|ies)|neighbou?rhoods?|area[- ]?wise)\b", low) or "ಗ್ರಾಮ" in low
                 or (zones and (re.search(r"\bareas?\b", low) or "ಪ್ರದೇಶ" in low)))
    if _beat or _area:
        return choice("T23", {"zones": zones, "crime_types": ct, "dimension": "beat" if _beat else "area",
                              "order": "asc" if re.search(r"\b(least|lowest|fewest|quietest|safest)\b", low) else "desc",
                              "limit": limit_val, **dates})
    # Peak month — "peak month for cybercrime in 2022": a monthly series over the span asked.
    if re.search(r"\b(peak|busiest|worst|highest)\s+month\b|\bwhich month\b|\bmonth (?:with|had) the most\b", low) \
            or "ಗರಿಷ್ಠ ತಿಂಗಳು" in low or "ಯಾವ ತಿಂಗಳು" in low:
        return choice("T3", {"crime_types": ct, "zones": zones, "months": 12,
                             "date_from": date_from, "date_to": date_to})
    # Law split — "IPC/BNS vs SLL split for 2023?"
    if re.search(r"\b(ipc|bns|sll)\b", low) or "special and local" in low or "special & local" in low:
        return choice("T17", {"zones": zones, **dates})
    # Year vs year — "compare crime 2022 vs 2023", "fastest-growing crime groups 2022 to 2023"
    # "stations with fewer than 10 FIRs in 2023" asks which places sit past a bar. No
    # template filters on a count, but the ranking from that end shows it, count by count;
    # it used to be answered with the statewide total for the year.
    _bar = re.search(r"\b(districts?|stations?|zones?|cities|areas?)\s+(?:with|having|that have|which have)\s+"
                     r"(more than|over|at least|above|fewer than|less than|under|below)\s+\d", low)
    if _bar:
        return choice("T11", {"crime_types": ct, "limit": limit_val, "dimension": geo_dim,
                              "order": "asc" if _bar.group(2) in ("fewer than", "less than", "under", "below") else "desc",
                              **dates})
    # "robbery cases between 2021 and 2023" names a span, not a comparison: it used to come
    # back as the statewide FIR totals of 2023 against 2021, with robbery nowhere in it.
    _compare = bool(re.search(r"\b(compare|comparison|vs|versus|growth|growing|grew|change)\b", low))
    if years and (_compare or (len(years) >= 2 and span_kind != "years")):
        return choice("T16", {"year": int(years[-1])})
    # A year's total — "Cognizable FIRs registered in Karnataka in 2022?" A month or a
    # quarter of that year is not the year: it goes on to the count below, with its dates.
    if years and span_kind in (None, "year") and not ct and not zones and not rank_q and not status_q \
            and re.search(r"\b(firs?|registered|cogni[sz]able|summary|what happened|overall|total|how many)\b", low):
        return choice("T16", {"year": int(years[0])})
    # Fewest — "least crime district", "safest district"
    if re.search(r"\b(least|lowest|fewest|minimum|safest)\b", low) or ("ಕಡಿಮೆ" in low and "ಯಾವ" in low):
        return choice("T11", {"crime_types": ct, "limit": limit_val, "dimension": geo_dim,
                              "order": "asc", **dates})
    # Forecast — "predict theft next month in Bengaluru City"
    if re.search(r"\b(predict|prediction|forecast|next month|next week|projection)\b", low) or "ಮುನ್ಸೂಚನೆ" in low:
        return choice("T3", {"crime_types": ct, "zones": zones, "months": 12})
    # Counts — "how many murders in Bengaluru City?", "total FIRs in Mysuru"
    if count_q and not status_q and not rank_q:
        return choice("T1", {"crime_types": ct, "zones": zones, "status": statuses, "limit": 10, **dates})
    # Superlatives — "most theft?", "which district has the highest crime", "ಅತಿ ಹೆಚ್ಚು ಕಳ್ಳತನ".
    # These are ranking questions and deserve a ranked answer. "most theft" has no place
    # word, so it used to fall through to the T1 case list and the officer got FIRs
    # instead of WHERE theft is highest. With no crime type, rank ALL crime rather than
    # asking which one: "most crimes?" has an answer. Skipped when a place is named (that
    # is a question about the place, handled below) and for "most recent"/"most wanted".
    if (re.search(r"\b(most|highest|maximum|max|worst|biggest|largest)\b", low)
            or any(w in low for w in ("ಅತಿ ಹೆಚ್ಚು", "ಅತ್ಯಧಿಕ", "ಅತೀ ಹೆಚ್ಚು"))) \
            and not zones and not any(w in low for w in ("most recent", "most wanted")):
        if any(w in low for w in ("common", "type of crime", "types of crime", "crime type",
                                  "which crime", "what crime", "ಯಾವ ಅಪರಾಧ", "ಸಾಮಾನ್ಯ")):
            return choice("T13", {"zones": zones, "date_from": date_from,
                                  "date_to": date_to, "period": period})
        return choice("T11", {"crime_types": ct, "limit": limit_val, "dimension": geo_dim,
                              "date_from": date_from, "date_to": date_to, "period": period})
    # hotspots / rankings / top cities / where / patrol / distribution / across dimensions.
    # A named place with no ranking word ("murders in Bengaluru City") is about that place,
    # not a ranking — the word "city" alone used to turn it into a district leaderboard.
    if not (zones and not rank_q) and any(w in low for w in ["hotspot", "where", "patrol", "which zone", "which area", "which station", "top", "cities", "city", "district", "districts", "stations", "station", "officers", "officer", "across", "distribution",
                              "ಹಾಟ್ಸ್ಪಾಟ್", "ಪ್ರಮುಖ ಸ್ಥಳ", "ಎಲ್ಲಿ", "ಯಾವ ಪ್ರದೇಶ", "ಯಾವ ವಲಯ",
                              "ಯಾವ ಊರ", "ಜಾಸ್ತಿ ಇದೆ", "ಹೆಚ್ಚು ಇದೆ", "ಯಾವ ಊರಿನಲ್ಲಿ", "ಎಲ್ಲಿವೆ", "ಜಿಲ್ಲೆ", "ಠಾಣೆ"]) and any(w in low for w in ["crime", "crimes", "case", "cases", "theft", "robbery", "hotspot", "top", "most", "highest", "in", "how many", "total", "count", "active", "summary", "across", "distribution", "reported", "ಅಪರಾಧ", "ಕಳ್ಳತನ", "ಕಲ್ಲತನ", "ದರೋಡೆ", "ಪ್ರಕರಣ", "ಹಾಟ್ಸ್ಪಾಟ್", "ಜಾಸ್ತಿ", "ಹೆಚ್ಚು"]):
        # "Top 10 stations by FIR volume" names no crime because it means all of them.
        if not ct and _volume_q(low):
            return choice("T11", {"crime_types": [], "limit": limit_val, "dimension": geo_dim,
                                  "date_from": date_from, "date_to": date_to, "period": period})
        if not ct and not any(w in low for w in ["top cities", "vehicle theft", "top suspects"]):
            # A place IS named ("most crimes in Bengaluru City", "which crime is most
            # common in Mysuru City") — that has a direct answer: the crime mix for that
            # place. Asking "which crime type?" back was not just unhelpful, it routed the
            # turn into self_heal, which spent ~12s on LLM calls and then answered about a
            # DIFFERENT district. Only a question with no place left to pin down clarifies.
            if zones:
                return choice("T13", {"zones": zones, "date_from": date_from,
                                      "date_to": date_to, "period": period})
            return choice("CLARIFY", {"missing": "crime_types", "intent": "hotspots"})
        return choice("T11", {
            "crime_types": ct, "limit": limit_val, "dimension": geo_dim,
            "date_from": date_from, "date_to": date_to, "period": period
        })
    # crime type breakdown
    if any(w in low for w in ["crime type", "types of crime", "breakdown", "which crimes are most common", "common crimes", "ಪ್ರಕಾರ"]):
        return choice("T13", {
            "zones": zones, "date_from": date_from, "date_to": date_to, "period": period
        })
    # trend
    if any(w in low for w in ["trend", "over time", "monthly", "increase", "rising",
                              "ಪ್ರವೃತ್ತಿ", "ಹೆಚ್ಚಳ", "ಮಾಸಿಕ", "ಏರಿಕೆ"]):
        if not ct:
            return choice("CLARIFY", {"missing": "crime_types", "intent": "trend"})
        return choice("T3", {"crime_types": ct, "zones": zones, "months": months})
    # status counts
    if any(w in low for w in ["open case", "status", "how many open", "pending",
                              "ತೆರೆದ ಪ್ರಕರಣ", "ಸ್ಥಿತಿ", "ಬಾಕಿ"]):
        return choice("T8", {"zones": zones, "crime_types": ct, **dates})
    # suspect lookup by name (capitalised token or after 'who is'/'find')
    name = _extract_name(user_text)
    if any(w in low for w in ["who is", "find suspect", "find name", "find -name", "find", "look up", "details of"]) or name:
        if name:
            return choice("T2", {"name_or_alias": name})
    # recent
    if any(w in low for w in ["recent", "latest", "last few",
                              "ಇತ್ತೀಚಿನ", "ಹೊಸ", "ಕೊನೆಯ"]):
        return choice("T12", {"zones": zones, "crime_types": ct, "limit": limit_val})
    # default: list crimes or top rankings if any crime/geo/police/summary terms present
    if ct or zones or any(w in low for w in ["crime", "crimes", "case", "cases", "incidents", "fir", "firs", "records", "top", "officer", "officers", "station", "stations", "active", "total", "count", "breakdown", "activity", "summary", "ಅಪರಾಧ", "ಕಳ್ಳತನ", "ಕಲ್ಲತನ", "ದರೋಡೆ", "ಪ್ರಕರಣ"]):
        if not (zones and not rank_q) and any(w in low for w in ("city", "cities", "district", "districts", "zone", "zones", "station", "stations", "area", "areas", "ಊರ", "ಪ್ರದೇಶ", "ವಲಯ", "ಜಿಲ್ಲೆ", "ಠಾಣೆ", "ಎಲ್ಲಿ")):
            if not ct and _volume_q(low):
                return choice("T11", {"crime_types": [], "limit": limit_val, "dimension": geo_dim,
                                      "date_from": date_from, "date_to": date_to, "period": period})
            if not ct:
                if zones:                      # see the note on the hotspots branch above
                    return choice("T13", {"zones": zones, "date_from": date_from,
                                          "date_to": date_to, "period": period})
                return choice("CLARIFY", {"missing": "crime_types", "intent": "hotspots"})
            return choice("T11", {
                "crime_types": ct, "limit": limit_val, "dimension": geo_dim,
                "date_from": date_from, "date_to": date_to, "period": period
            })
        # With NO constraint at all (no crime type, place, status or period), T1 is "every
        # FIR in Karnataka". That is the right answer to "how many FIRs in total?", and the
        # wrong one to "which repeat domestic complaints are escalating?" — which reached
        # here only because it contains the word "complaints", and answered "995,170 cases
        # are on record". Unconstrained, only a genuine total/listing request keeps T1;
        # anything else falls to NONE, where self-heal looks for records that are actually
        # related (semantic / fragment match) or the officer is asked to rephrase.
        constrained = bool(ct or zones or statuses or period or date_from or date_to)
        whole_registry_q = count_q or bool(re.search(
            r"\b(total|overall|all (crimes|cases|firs)|summary|breakdown|registry)\b", low))
        if constrained or whole_registry_q:
            return choice("T1", {"crime_types": ct, "zones": zones, "status": statuses, "limit": limit_val, "date_from": date_from, "date_to": date_to, "period": period})
    return {"template_id": "NONE", "reason": "no keyword match", "answer_lang": answer_lang}


_NAME_RE = re.compile(r"(?:who is|find suspect|find name|find -name|find|look up|details of|profile of)\s+([A-Z][\w.]+(?:\s+[A-Z][\w.]+)?)",
                      re.IGNORECASE)


def _extract_name(text: str) -> str | None:
    m = _NAME_RE.search(text)
    if m:
        return m.group(1).strip()
    # known alias shortcut for the demo
    if "yellappa" in text.lower():
        return "Yellappa"
    if "raju" in text.lower():
        return "Raju"
    return None
