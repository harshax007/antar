"""
Antar — Grounded Follow-up Agent
=====================================
Suggested questions that are guaranteed answerable: every candidate is built
from the ACTUAL result context (real zones / crime types / suspect ids taken
from the returned rows), resolved to a whitelisted query template + params,
then dry-run against the local database — only suggestions whose query
returns rows are emitted. Deterministic, no LLM.

Public API:
  grounded_followups(template_id, params, rows, max_out=3) -> list[str]
  grounded_starters(max_out=3) -> list[str]
"""

from __future__ import annotations

from collections import Counter

from app.services.zcql_repo import build_spec
from app.services.zcql_local import run_query


def _has_rows(template_id: str, params: dict) -> bool:
    """Dry-run a candidate query. Cheap (local SQLite) and side-effect free."""
    try:
        return len(run_query(build_spec(template_id, params))) > 0
    except Exception:
        return False


def _most_common(rows: list[dict], *keys: str) -> str | None:
    values = [str(r[k]).strip() for r in rows for k in keys
              if r.get(k) and str(r[k]).strip()]
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _context(params: dict, rows: list[dict]) -> dict:
    """Pull the grounding entities out of the answered query's params + rows."""
    zone = None
    if params.get("zones"):
        zone = params["zones"][0]
    if not zone:
        zone = _most_common(rows, "zone", "address_zone")

    crime_type = None
    if params.get("crime_types"):
        crime_type = params["crime_types"][0]
    if not crime_type:
        crime_type = _most_common(rows, "crime_type")

    suspect_id = next((r["suspect_id"] for r in rows if r.get("suspect_id")), None)
    return {"zone": zone, "crime_type": crime_type, "suspect_id": suspect_id}


def _candidates(template_id: str, ctx: dict, lang: str = "en") -> list[tuple[str, str, dict]]:
    """(question, template_id, params) candidates in priority order.
    Question wording mirrors the template examples so the router maps the
    suggestion back onto the same whitelisted template when clicked. Crime-type /
    zone / id tokens are kept in sentence case using display_crime()."""
    from app.agents.display_names import display_crime
    zone, ct, sid = ctx["zone"], ctx["crime_type"], ctx["suspect_id"]
    kn = lang == "kn"
    # Display-friendly crime type for chip text
    ct_display = display_crime(ct, lang) if ct else None
    cands: list[tuple[str, str, dict]] = []

    if ct and zone:
        cands.append(((f"{zone} ನಲ್ಲಿ ಕಳೆದ 6 ತಿಂಗಳ {ct_display} ಪ್ರವೃತ್ತಿ" if kn
                       else f"Show the {ct_display} trend in {zone} last 6 months"),
                      "T3", {"crime_types": [ct], "zones": [zone], "months": 6}))
    if zone:
        cands.append(((f"{zone} ನಲ್ಲಿ ಪ್ರಮುಖ ಶಂಕಿತರು" if kn else f"Top suspects in {zone}"),
                      "T4", {"zones": [zone]}))
    if ct:
        cands.append(((f"ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ {ct_display} ಹೆಚ್ಚು?" if kn else f"Which districts have the most {ct_display}?"),
                      "T11", {"crime_types": [ct]}))
    if zone:
        cands.append(((f"{zone} ನಲ್ಲಿ ಇತ್ತೀಚಿನ ಪ್ರಕರಣಗಳು" if kn else f"Latest cases in {zone}"),
                      "T12", {"zones": [zone], "limit": 5}))
    if sid:
        cands.append(((f"{sid} ಯಾವ ಅಪರಾಧಗಳಿಗೆ ಸಂಬಂಧಿಸಿದೆ?" if kn else f"What crimes is {sid} linked to?"),
                      "T9", {"suspect_id": sid}))

    # Generic but still validated fillers.
    cands.append(((("ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು ಯಾರು?" if kn else "Who are the repeat offenders?")),
                  "T5", {"min_priors": 2, "limit": 10}))
    cands.append(((("ಅಪರಾಧಗಳ ಪ್ರಕಾರವಾರು ವಿಂಗಡಣೆ" if kn else "Breakdown of crimes by type")),
                  "T13", {}))

    # Never re-suggest the query that was just answered.
    return [(q, t, p) for q, t, p in cands if t != template_id]


def grounded_followups(template_id: str, params: dict, rows: list[dict],
                       max_out: int = 3, lang: str = "en") -> list[str]:
    """Context-generated, DB-validated follow-up questions (answer guaranteed)."""
    out: list[str] = []
    for question, tid, tparams in _candidates(template_id, _context(params or {}, rows or []), lang):
        if len(out) >= max_out:
            break
        if _has_rows(tid, tparams):
            out.append(question)
    return out


_STARTER_CANDIDATES: list[tuple[str, str, str, dict]] = [
    ("Show robbery trends in Bengaluru North last 3 months",
     "ಬೆಂಗಳೂರು ನಾರ್ತ್‌ನಲ್ಲಿ ಕಳೆದ 3 ತಿಂಗಳ ದರೋಡೆ ಪ್ರವೃತ್ತಿ",
     "T3", {"crime_types": ["robbery"], "zones": ["Bengaluru North"], "months": 3}),
    ("Who are the repeat offenders?",
     "ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು ಯಾರು?",
     "T5", {"min_priors": 2, "limit": 10}),
    ("Where are the theft hotspots this month?",
     "ಈ ತಿಂಗಳು ಕಳ್ಳತನ ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳು ಎಲ್ಲಿ?",
     "T11", {"crime_types": ["theft"]}),
    ("Breakdown of crimes by type",
     "ಅಪರಾಧಗಳ ಪ್ರಕಾರವಾರು ವಿಂಗಡಣೆ",
     "T13", {}),
]


def grounded_starters(max_out: int = 3, lang: str = "en") -> list[str]:
    """Empty-state starters, validated the same way (never a dead suggestion)."""
    kn = lang == "kn"
    out = [(q_kn if kn else q_en) for q_en, q_kn, tid, p in _STARTER_CANDIDATES
           if _has_rows(tid, p)][:max_out]
    # If the database is entirely unreachable, better no suggestions than dead ones.
    return out
