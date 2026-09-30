"""
Antar — Intent Parser  (self-healing RAG · WI-3)
====================================================
Turns any user phrasing (EN or KN) into a structured, catalog-validated `Intent`.

Two paths, both safe:
  • deterministic  — synonym / regex / keyword scan over the raw text. Always runs; it is
    the offline oracle and the backstop when the LLM drops entities (the #1 failure the
    self-heal loop repairs).
  • GLM-4 (QuickML) — optional. Parses intent against the hardcoded system catalog, then
    is MERGED over the deterministic result (deterministic ids always win; entity lists are
    unioned; the LLM only fills gaps). Never trusted blindly, never required.

Returns a validated Intent — never raises.
"""
from __future__ import annotations

import os as _os
import re
import json
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel, Field

from app.services.zcql_repo import normalize_crime_types, CRIME_TYPE_SYNONYMS, CRIME_TYPES
from app.agents.system_catalog import (
    INTENTS, STATUS_SYNONYMS, normalize_statuses, resolve_zones_catalog, known_zones,
    catalog_prompt,
)

LLM = Callable[..., Awaitable[str]]

_ID_SUSPECT = re.compile(r"\bS\d{3,}\b", re.I)
_ID_FIR = re.compile(r"\b\d{4}-[A-Z]{2,4}-\d{3,}\b", re.I)
_YEAR = re.compile(r"\b(20\d{2})\b")

# Relative-time phrases → canonical period keyword (EN + KN). Longest phrase first.
_PERIOD_PHRASES = [
    ("last three months", "last_3_months"), ("last 3 months", "last_3_months"),
    ("past three months", "last_3_months"), ("past 3 months", "last_3_months"),
    ("last six months", "last_6_months"), ("last 6 months", "last_6_months"),
    ("this month", "this_month"), ("current month", "this_month"),
    ("last month", "last_month"), ("previous month", "last_month"),
    ("last week", "last_week"), ("past week", "last_week"), ("this week", "last_week"),
    ("this year", "this_year"), ("current year", "this_year"),
    ("last year", "last_year"), ("previous year", "last_year"),
    ("ಕಳೆದ ಮೂರು ತಿಂಗಳ", "last_3_months"), ("ಕಳೆದ ಮೂರು ತಿಂಗಳಲ್ಲಿ", "last_3_months"),
    ("ಕಳೆದ ತಿಂಗಳು", "last_month"), ("ಈ ತಿಂಗಳು", "this_month"),
    ("ಈ ವರ್ಷ", "this_year"), ("ಕಳೆದ ವರ್ಷ", "last_year"),
]

# Intent keyword rules (checked in order; first match wins). KN cues included.
_INTENT_RULES = [
    ("suspect_lookup", ("who is", "look up suspect", "find suspect", "profile of", "ಯಾರು")),
    ("trend", ("trend", "over time", "monthly", "over the last", "change over",
               "ಪ್ರವೃತ್ತಿ", "ಬದಲಾವಣೆ")),
    ("hotspots", ("hotspot", "most", "top zone", "which zone", "which area", "where are",
                  "where should", "highest", "ಹೆಚ್ಚು", "ಎಲ್ಲಿ")),
    ("type_breakdown", ("breakdown", "by type", "which crime types", "distribution",
                        "ಪ್ರಕಾರದ ಪ್ರಕಾರ")),
    ("status_counts", ("how many are open", "how many open", "status of", "by status")),
    ("repeat_offenders", ("repeat offender", "habitual", "recidiv", "ಪುನರಾವರ್ತಿತ")),
    ("demographics", ("age group", "gender", "demographic", "victim age", "ವಯಸ್ಸು", "ಲಿಂಗ")),
    ("recent", ("latest", "recent", "most recent", "ಇತ್ತೀಚಿನ")),
    ("year_summary", ("summary of 20", "what happened in 20", "in 20")),
]


class Intent(BaseModel):
    intent_type: str = "list_cases"
    crime_types: list[str] = Field(default_factory=list)
    zones: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    suspect_id: Optional[str] = None
    fir_number: Optional[str] = None
    period: Optional[str] = None
    year: Optional[int] = None
    keywords: list[str] = Field(default_factory=list)
    raw: str = ""
    lang: str = "en"

    def template(self) -> Optional[str]:
        return INTENTS.get(self.intent_type, {}).get("template")


_STOP = {"the", "a", "an", "of", "in", "on", "for", "to", "and", "or", "me", "my", "all",
         "show", "list", "give", "find", "cases", "case", "crime", "crimes", "from", "with",
         "what", "which", "who", "where", "how", "many", "is", "are", "last", "this", "past"}


def _keywords(text: str) -> list[str]:
    toks = re.findall(r"[A-Za-zಀ-೿]{3,}", (text or "").lower())
    return [t for t in dict.fromkeys(toks) if t not in _STOP][:8]


def _scan_crime_types(text: str) -> list[str]:
    """Deterministic crime-type extraction: match synonym keys + canonical types in text."""
    low = " " + (text or "").lower() + " "
    found: list[str] = []
    for key in CRIME_TYPE_SYNONYMS:
        if key and key.lower() in low:
            found.append(key)
    for ct in CRIME_TYPES:
        c = ct.strip().lower()
        if c and (c in low or c.replace("_", " ") in low):
            found.append(ct)
    return normalize_crime_types(found)


def _scan_zones(text: str) -> list[str]:
    low = (text or "").lower()
    hits = [z for z in known_zones() if z and z.lower() in low]
    for city in ("bengaluru", "bangalore", "mysuru", "mysore", "hubballi", "hubli",
                 "mangaluru", "mangalore", "belagavi", "belgaum", "kalaburagi",
                 "ಬೆಂಗಳೂರ", "ಮೈಸೂರ"):
        if city in low:
            hits.append(city)
    return list(dict.fromkeys(hits))


def _scan_statuses(text: str) -> list[str]:
    """Match status words on WORD BOUNDARIES so 'solved' does not fire inside 'unsolved'
    (that bug unioned every status). Kannada keys use substring (no ASCII boundaries)."""
    low = (text or "").lower()
    out: list[str] = []
    for k in STATUS_SYNONYMS:
        kl = k.lower()
        if kl.isascii():
            if re.search(r"\b" + re.escape(kl) + r"\b", low):
                out.append(k)
        elif kl in low:
            out.append(k)
    return out


def _scan_period(text: str) -> Optional[str]:
    low = (text or "").lower()
    for phrase, period in _PERIOD_PHRASES:
        if phrase in low:
            return period
    return None


def _scan_intent(text: str, has_suspect_id: bool) -> str:
    if has_suspect_id and re.search(r"link|connect|associat|crime|case|involv", text, re.I):
        return "suspect_crimes"
    low = (text or "").lower()
    for name, cues in _INTENT_RULES:
        if any(c in low for c in cues):
            return name
    return "list_cases"


def _extract_deterministic(text: str, lang: str) -> Intent:
    sid = _ID_SUSPECT.search(text or "")
    fir = _ID_FIR.search(text or "")
    yr = _YEAR.search(text or "")
    return Intent(
        intent_type=_scan_intent(text, bool(sid)),
        crime_types=_scan_crime_types(text),
        zones=resolve_zones_catalog(_scan_zones(text)),
        statuses=normalize_statuses(_scan_statuses(text)),
        suspect_id=sid.group(0).upper() if sid else None,
        fir_number=fir.group(0).upper() if fir else None,
        period=_scan_period(text),
        year=int(yr.group(1)) if (yr and "year_summary" == _scan_intent(text, bool(sid))) else None,
        keywords=_keywords(text),
        raw=text or "",
        lang=lang,
    )


_PARSE_SYSTEM = ("You classify a Karnataka police officer's question into ONE intent and "
                 "extract entities. You do NOT write SQL. Respond ONLY with JSON.")


def _merge_llm(base: Intent, data: dict) -> Intent:
    """Merge LLM output OVER the deterministic base. Deterministic ids win; entity lists
    are unioned; intent_type is taken from the LLM only if the base was the default guess."""
    if not isinstance(data, dict):
        return base
    it = str(data.get("intent_type") or "").strip()
    if it in INTENTS and base.intent_type == "list_cases":
        base.intent_type = it
    base.crime_types = list(dict.fromkeys(base.crime_types + normalize_crime_types(
        data.get("crime_types") or [])))
    base.zones = list(dict.fromkeys(base.zones + resolve_zones_catalog(data.get("zones") or [])))
    base.statuses = list(dict.fromkeys(base.statuses + normalize_statuses(
        data.get("statuses") or [])))
    if not base.period and data.get("period"):
        p = str(data["period"]).lower().replace("-", "_").replace(" ", "_")
        base.period = p
    if not base.suspect_id and data.get("suspect_id"):
        m = _ID_SUSPECT.search(str(data["suspect_id"]))
        if m:
            base.suspect_id = m.group(0).upper()
    if not base.year and data.get("year"):
        try:
            base.year = int(data["year"])
        except (ValueError, TypeError):
            pass
    return base


async def parse_intent(user_text: str, lang: str = "en",
                       llm: Optional[LLM] = None) -> Intent:
    """Parse `user_text` into a validated Intent. Deterministic first (always), then an
    optional GLM-4 pass merged on top. Never raises."""
    base = _extract_deterministic(user_text, lang)
    if llm is None:
        return base
    try:
        from app.services.quickml import parse_json_response
        prompt = (
            catalog_prompt() + "\n\n"
            f"Question (language={lang}): {user_text}\n\n"
            'Respond ONLY with JSON: {"intent_type":"...", "crime_types":[...], '
            '"zones":[...], "statuses":[...], "suspect_id":"S....|null", '
            '"period":"...|null", "year":null}'
        )
        # This is an ENRICHMENT pass over an answer the deterministic parse already
        # produced, so it gets a short leash: self_heal can call it several times in one
        # turn, and an unbounded wait here multiplied straight into the officer's latency.
        import asyncio as _a
        raw = await _a.wait_for(
            llm(system=_PARSE_SYSTEM, user=prompt, json_mode=True,
                max_tokens=220, temperature=0.1),
            timeout=float(_os.environ.get("ANTAR_INTENT_TIMEOUT_S", "6")))
        data = parse_json_response(raw)
        return _merge_llm(base, data)
    except Exception:
        return base
