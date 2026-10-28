"""
Antar — Self-Healing RAG orchestrator  (WI-3)
=================================================
Invoked ONLY when the first template query returns 0 rows or an ungrounded result. It
diagnoses why and repairs, in three escalating scenarios (the caller pays nothing on a
direct hit):

  Sc A — Direct hit .......... handled by the caller; self_heal is never entered.
  (repair) Structured heal ... GLM-4/deterministic intent → reroute to the correct template
                               → relational SQL miner with progressive relaxation.
  Sc B — Semantic gap ........ dense Second-Brain recall finds meaning-matches (different words).
  Sc C — Fragment match ...... hybrid BM25(sparse)+dense index finds keyword fragments.
  dead-end ................... honest "no exact match" + nearest-matches hint (never a bare
                               "No matching records").

Language-preserving; offline-safe (every LLM touch is optional). Returns rows + a heal
trace; the caller composes the final answer from the (possibly related) rows.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from app.core.db_path import DB_PATH
from app.services.zcql_local import _dict_factory
from app.agents.intent_parser import parse_intent, Intent
from app.agents.system_catalog import INTENTS
from app.core.db_path import registry_connect

LLM = Callable[..., Awaitable[str]]

CLOSEST_EN = "No exact match — showing the closest related records:"
CLOSEST_KN = "ನಿಖರ ಹೊಂದಾಣಿಕೆ ಇಲ್ಲ — ಹತ್ತಿರದ ಸಂಬಂಧಿತ ದಾಖಲೆಗಳನ್ನು ತೋರಿಸಲಾಗುತ್ತಿದೆ:"

_PERIOD_MONTHS = {"this_month": 1, "last_month": 1, "last_week": 1,
                  "last_3_months": 3, "last_6_months": 6, "this_year": 12, "last_year": 12}


@dataclass
class SelfHealResult:
    rows: list = field(default_factory=list)
    citations: list = field(default_factory=list)
    template_id: Optional[str] = None
    params: dict = field(default_factory=dict)
    trace: list = field(default_factory=list)
    related_only: bool = False
    entity_satisfied: bool = False  # rows are BY CONSTRUCTION about the named entity (T9/T2/id join)
    scenario: str = "none"          # repaired_direct | semantic_gap | fragment | dead_end
    lead: Optional[str] = None       # localized "closest matches" lead when related_only
    dead_end_message: Optional[str] = None


def _cites(rows: list) -> list:
    try:
        from app.agents.query_agent import extract_citations
        return extract_citations(rows)
    except Exception:
        return []


def _fetch_by_ids(crime_ids: list[str]) -> list[dict]:
    ids = [str(c) for c in crime_ids if c][:25]
    if not ids:
        return []
    try:
        conn = registry_connect(DB_PATH)
        conn.row_factory = _dict_factory
        ph = ",".join("?" * len(ids))
        rows = conn.execute(
            "SELECT crime_id, fir_number, crime_type, act, acts_sections, zone, district, "
            f"station_code, occurred_at, status, io_name FROM crimes WHERE crime_id IN ({ph})",
            ids).fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def _semantic_rows(query: str, k: int = 8) -> list[dict]:
    """Sc B — dense meaning-match via the Second-Brain recall, mapped to crime rows."""
    try:
        import json
        from app.second_brain.index import brain_index
        if getattr(brain_index, "size", 0) == 0:
            return []                       # empty index → skip the embedder/reranker load
        from app.second_brain.retrieval import semantic_recall
        hits = semantic_recall(query, k=k) or []
        cids: list[str] = []
        for h in hits:
            raw = h.get("crime_ids_json") or h.get("crime_ids") or "[]"
            try:
                ids = raw if isinstance(raw, list) else json.loads(raw)
            except Exception:
                ids = []
            cids.extend(str(x) for x in ids)
        return _fetch_by_ids(list(dict.fromkeys(cids)))
    except Exception:
        return []


def intent_to_template(intent: Intent) -> tuple[Optional[str], dict]:
    """Map an aggregation/special intent to its whitelisted template + params.
    list_cases returns (None, {}) — those go to the relational SQL miner instead."""
    t = INTENTS.get(intent.intent_type, {}).get("template")
    if not t:
        return None, {}
    months = _PERIOD_MONTHS.get(intent.period or "", 12)
    if t == "T9" and intent.suspect_id:
        return "T9", {"suspect_id": intent.suspect_id}
    if t == "T2":
        name = " ".join(intent.keywords[:3]) or intent.raw
        return "T2", {"name_or_alias": name}
    if t == "T3":
        return "T3", {"crime_types": intent.crime_types, "zones": intent.zones, "months": months}
    if t == "T11":
        return "T11", {"crime_types": intent.crime_types, "zones": intent.zones,
                       "period": intent.period}
    if t == "T13":
        return "T13", {"zones": intent.zones, "period": intent.period}
    if t == "T8":
        return "T8", {"zones": intent.zones}
    if t == "T5":
        return "T5", {}
    if t == "T7":
        return "T7", {}
    if t == "T12":
        return "T12", {"zones": intent.zones}
    if t == "T16":
        return "T16", {"year": intent.year} if intent.year else ("T16", {})
    return None, {}


def _run_template_safe(template_id: str, params: dict) -> list[dict]:
    try:
        from app.agents.query_agent import run_template
        rows, _ = run_template(template_id, params)
        return rows
    except Exception:
        return []


def _dead_end_message(intent: Intent, lang: str) -> str:
    kn = lang == "kn"
    parts: list[str] = []
    try:
        conn = registry_connect(DB_PATH)
        if intent.crime_types:
            ct = intent.crime_types[0]
            n = conn.execute("SELECT COUNT(*) FROM crimes WHERE TRIM(UPPER(crime_type))=?",
                             (ct.strip().upper(),)).fetchone()[0]
            if n:
                parts.append(f"{n:,} {ct} ದಾಖಲೆಗಳು ರಾಜ್ಯಾದ್ಯಂತ ಇವೆ" if kn
                             else f"{n:,} {ct} records exist statewide")
        if intent.zones:
            z = intent.zones[0]
            row = conn.execute(
                "SELECT crime_type, COUNT(*) n FROM crimes WHERE TRIM(UPPER(zone))=? "
                "GROUP BY crime_type ORDER BY n DESC LIMIT 1", (z.strip().upper(),)).fetchone()
            if row and row[0]:
                parts.append(f"{z} ನಲ್ಲಿ ಅತಿ ಸಾಮಾನ್ಯ: {row[0]} ({row[1]})" if kn
                             else f"in {z}, the most common is {row[0]} ({row[1]} cases)")
        conn.close()
    except Exception:
        pass
    head = ("ನಿಮ್ಮ ನಿಖರ ಪ್ರಶ್ನೆಗೆ ದಾಖಲೆಗಳಿಲ್ಲ." if kn
            else "No records match your exact query.")
    if parts:
        near = ("; ".join(parts))
        tail = (f" ಹತ್ತಿರದ: {near}." if kn else f" Nearest: {near}.")
        return head + tail
    return head + ("\nಹೀಗೆ ಪ್ರಯತ್ನಿಸಿ:\n• ದಿನಾಂಕ ಅಥವಾ ಸ್ಥಳ ಫಿಲ್ಟರ್ ತೆಗೆದುಹಾಕಿ\n"
                   "• ಅಪರಾಧ ಪ್ರಕಾರವನ್ನು ತಿಳಿಸಿ (ಕಳ್ಳತನ, ದರೋಡೆ…)\n• ಸ್ಥಳ ಅಥವಾ ಹೆಸರಿನ ಕಾಗುಣಿತ ಪರಿಶೀಲಿಸಿ" if kn
                   else "\nTry:\n• removing the date or place filter\n"
                   "• naming a crime type (theft, robbery…)\n• checking the spelling of the place or name")


_covers_from: list = []


def _register_starts() -> Optional[str]:
    """First date a slim copy holds (scripts/build_cloud_db.py --slim), or None for the full register."""
    if not _covers_from:
        try:
            conn = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
            try:
                row = conn.execute("SELECT value FROM register_meta WHERE key = 'covers_from'").fetchone()
            finally:
                conn.close()
            _covers_from.append(row[0] if row else None)
        except sqlite3.Error:
            _covers_from.append(None)
    return _covers_from[0]


def _before_coverage(params: dict) -> Optional[str]:
    """The copy's start date when the asked period ends before it; else None."""
    start = _register_starts()
    if not start:
        return None
    end = str(params.get("date_to") or "")
    if not end and str(params.get("year") or "").isdigit():
        end = f"{params['year']}-12-31"
    return start if end and end[:10] < start else None


def _coverage_message(start: str, lang: str) -> str:
    from datetime import date
    d = date.fromisoformat(start)
    if lang == "kn":
        return (f"ಈ ಆನ್‌ಲೈನ್ ಪ್ರತಿಯಲ್ಲಿ {d.day} ಜನವರಿ {d.year} ರಿಂದ ದಾಖಲಾದ FIRಗಳು ಮಾತ್ರ ಇವೆ, ಆದ್ದರಿಂದ "
                f"ಆ ಅವಧಿಯ ದಾಖಲೆಗಳು ಇಲ್ಲಿಲ್ಲ. 2016 ರಿಂದ ಪೂರ್ಣ ದಾಖಲೆ ಮುಖ್ಯ Antar ವ್ಯವಸ್ಥೆಯಲ್ಲಿದೆ.")
    return (f"This online copy holds FIRs registered from {d.day} {d:%b %Y} on, so it has no "
            f"records for that period. The full register, from 2016, is on the main Antar system.")


async def self_heal(user_text: str, lang: str, template_id: str, params: dict,
                    rows: list, history: Optional[list] = None,
                    select_llm: Optional[LLM] = None,
                    officer_id: Optional[str] = None) -> SelfHealResult:
    """Diagnose + repair an empty/ungrounded query. Never raises."""
    trace: list[dict] = [{"step": "self_heal",
                          "detail": f"'{template_id}' returned {len(rows)} usable row(s) — self-healing."}]
    # A period this copy does not hold has no answer here. Relaxing the date or a fuzzy
    # search would answer it with rows from other years.
    start = _before_coverage(params or {})
    if start:
        trace.append({"step": "self_heal", "detail": f"Asked period ends before this copy starts ({start})."})
        return SelfHealResult(rows=[], trace=trace, scenario="dead_end",
                              dead_end_message=_coverage_message(start, lang))
    try:
        intent = await parse_intent(user_text, lang, llm=select_llm)
    except Exception:
        intent = Intent(raw=user_text, lang=lang)
    trace.append({"step": "self_heal",
                  "detail": f"Parsed intent={intent.intent_type}; types={intent.crime_types}; "
                            f"zones={len(intent.zones)}; status={intent.statuses}; "
                            f"period={intent.period}; suspect={intent.suspect_id}"})

    # ── Structured repair: reroute to the correct template (aggregation intents) ──
    t_id, t_params = intent_to_template(intent)
    if t_id and (t_id != template_id or t_params != params):
        rr = _run_template_safe(t_id, t_params)
        trace.append({"step": "self_heal", "detail": f"Rerouted to {t_id} -> {len(rr)} row(s)"})
        if rr:
            return SelfHealResult(rows=rr, citations=_cites(rr), template_id=t_id,
                                  params=t_params, trace=trace, scenario="repaired_direct",
                                  entity_satisfied=t_id in ("T9", "T2"))

    # ── Structured repair: relational SQL miner with progressive relaxation ──
    from app.services.sql_miner import mine_until_hit
    mrows, relax, mtrace = mine_until_hit(intent)
    trace.extend(mtrace)
    if mrows:
        return SelfHealResult(rows=mrows, citations=_cites(mrows), template_id="MINER",
                              params=intent.model_dump(), trace=trace,
                              related_only=relax > 0 and not (intent.suspect_id or intent.fir_number),
                              entity_satisfied=bool(intent.suspect_id or intent.fir_number),
                              lead=(CLOSEST_KN if lang == "kn" else CLOSEST_EN)
                                   if (relax > 0 and not (intent.suspect_id or intent.fir_number)) else None,
                              scenario="repaired_direct")

    # ── Sc B — semantic gap (dense) ──
    srows = _semantic_rows(user_text, k=8)
    trace.append({"step": "self_heal", "detail": f"Semantic recall (dense) -> {len(srows)} row(s)"})
    if srows:
        return SelfHealResult(rows=srows, citations=_cites(srows), template_id="SEMANTIC",
                              params=intent.model_dump(), trace=trace, related_only=True,
                              lead=CLOSEST_KN if lang == "kn" else CLOSEST_EN,
                              scenario="semantic_gap")

    # ── Sc C — fragment match (hybrid BM25 sparse + dense) ──
    try:
        from app.services.hybrid_index import get_index
        frows = get_index().search(user_text, k=10)
    except Exception:
        frows = []
    trace.append({"step": "self_heal", "detail": f"Hybrid BM25 fragment search -> {len(frows)} row(s)"})
    if frows:
        return SelfHealResult(rows=frows, citations=_cites(frows), template_id="HYBRID",
                              params=intent.model_dump(), trace=trace, related_only=True,
                              lead=CLOSEST_KN if lang == "kn" else CLOSEST_EN,
                              scenario="fragment")

    # ── Honest dead-end ──
    msg = _dead_end_message(intent, lang)
    trace.append({"step": "self_heal", "detail": "No rows after all repair stages — honest dead-end."})
    return SelfHealResult(rows=[], trace=trace, scenario="dead_end", dead_end_message=msg)
