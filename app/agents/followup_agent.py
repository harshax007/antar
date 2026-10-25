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
        p = dict(params); p["limit"] = 1; return len(run_query(build_spec(template_id, p))) > 0
    except Exception:
        return False


# Aggregates over a filter (rate, ranking, weekday, kinds). Each returns rows exactly when some
# FIR matches its filter, so the indexed "latest case" lookup on that filter answers the
# dry-run in milliseconds; running the aggregate itself costs up to 3s per suggestion.
_GROUPED = {"T11", "T13", "T22", "T23", "T25", "T26"}


def _answerable(template_id: str, params: dict) -> bool:
    if template_id in _GROUPED:
        probe = {k: params[k] for k in ("zones", "crime_types", "date_from", "date_to") if params.get(k)}
        return _has_rows("T12", probe)
    return _has_rows(template_id, params)


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
    # The first row of a ranking is what an officer asks about next ("...and in Mysuru?").
    # Only a ranking has a leader; the first FIR of a case list is just the newest one.
    first = rows[0] if rows and ("n" in rows[0] or "grp" in rows[0]) else {}
    place_keys = ("zone", "district", "district_norm") + (
        ("grp",) if params.get("dimension") in ("district", "zone") else ())
    top_zone = None if params.get("zones") else next(
        (str(first[k]).strip() for k in place_keys if first.get(k)), None)
    top_crime = None if params.get("crime_types") else (str(first.get("crime_type") or "").strip() or None)

    def ident(*keys):
        return next((str(r[k]).strip() for r in rows for k in keys if r.get(k) and str(r[k]).strip()), None)
    return {"zone": zone, "crime_type": crime_type, "suspect_id": suspect_id,
            "top_zone": top_zone, "top_crime": top_crime,
            "accused_id": ident("accused_id", "Accused_ID"), "upi": ident("upi_id", "UPI_ID"),
            "vehicle": ident("vehicle", "Vehicle_Reg_No", "plate")}


def _route(question: str) -> tuple[str | None, dict]:
    """What the chat would run for this exact text (the offline router, no LLM). The router
    is declared async but awaits nothing, so it is driven to completion directly."""
    from app.agents.heuristics import heuristic_select
    coro = heuristic_select(question, "en")
    try:
        coro.send(None)
    except StopIteration as done:
        r = done.value or {}
        return r.get("template_id"), dict(r.get("params") or {})
    except Exception:
        return None, {}
    finally:
        coro.close()
    return None, {}


def _drafts(ctx: dict, lang: str) -> list[tuple[str, str, dict | None]]:
    """(question, intended template, params) in priority order. params=None means "route the
    text and use what the router produces", so a click runs exactly what was checked."""
    from app.agents.display_names import display_crime
    # A ranking's leader is the place the officer drills into next.
    zone, ct, sid = ctx["zone"] or ctx.get("top_zone"), ctx["crime_type"], ctx["suspect_id"]
    kn = lang == "kn"
    ct_display = display_crime(ct, lang) if ct else None
    d: list[tuple[str, str, dict | None]] = []

    if not kn:
        # Investigative next steps, most specific first.
        if ctx.get("accused_id"):
            d.append((f"cases for accused {ctx['accused_id']}", "T21", None))
        if ctx.get("upi"):
            d.append((f"FIRs for UPI {ctx['upi']}", "T20", None))
        if ctx.get("vehicle"):
            d.append((f"FIRs linked to vehicle {ctx['vehicle']}", "T18", None))
        if sid:
            d.append((f"What crimes is {sid} linked to?", "T9", {"suspect_id": sid}))
        if ctx.get("top_crime"):
            d.append((f"Which districts have the most {display_crime(ctx['top_crime'], lang).lower()}?", "T11", None))
        if ct and zone:
            c = ct_display.lower()
            d += [(f"Conviction rate for {c} in {zone}", "T22", None),
                  (f"Top beats for {c} in {zone}", "T23", None),
                  (f"Which day of the week has the most {c} in {zone}?", "T26", None),
                  (f"What kinds of {c} happen in {zone}?", "T25", None)]
        elif zone:
            d += [(f"Top beats in {zone}", "T23", None),
                  (f"Conviction rate in {zone}", "T22", None),
                  (f"Which day of the week has the most crime in {zone}?", "T26", None)]
        elif ct:
            c = ct_display.lower()
            d += [(f"Conviction rate by district for {c}", "T22", None),
                  (f"Which day of the week has the most {c}?", "T26", None),
                  (f"What kinds of {c} are registered?", "T25", None)]

    # The original validated set (also the whole Kannada set).
    if ct and zone:
        d.append(((f"{zone} ನಲ್ಲಿ ಕಳೆದ 6 ತಿಂಗಳ {ct_display} ಪ್ರವೃತ್ತಿ" if kn
                   else f"Show the {ct_display} trend in {zone} last 6 months"),
                  "T3", {"crime_types": [ct], "zones": [zone], "months": 6}))
    if zone:
        d.append(((f"{zone} ನಲ್ಲಿ ಪ್ರಮುಖ ಶಂಕಿತರು" if kn else f"Top suspects in {zone}"),
                  "T4", {"zones": [zone]}))
    if ct:
        d.append(((f"ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ {ct_display} ಹೆಚ್ಚು?" if kn else f"Which districts have the most {ct_display}?"),
                  "T11", {"crime_types": [ct]}))
    if zone:
        d.append(((f"{zone} ನಲ್ಲಿ ಇತ್ತೀಚಿನ ಪ್ರಕರಣಗಳು" if kn else f"Latest cases in {zone}"),
                  "T12", {"zones": [zone], "limit": 5}))
    if sid:
        d.append(((f"{sid} ಯಾವ ಅಪರಾಧಗಳಿಗೆ ಸಂಬಂಧಿಸಿದೆ?" if kn else f"What crimes is {sid} linked to?"),
                  "T9", {"suspect_id": sid}))

    # Generic but still validated fillers.
    if not kn:
        d.append(("Conviction rate by district", "T22", None))
    d.append(((("ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು ಯಾರು?" if kn else "Who are the repeat offenders?")),
              "T5", {"min_priors": 2, "limit": 10}))
    d.append(((("ಅಪರಾಧಗಳ ಪ್ರಕಾರವಾರು ವಿಂಗಡಣೆ" if kn else "Breakdown of crimes by type")),
              "T13", {}))
    return d


def _kept(question: str, ctx: dict, params: dict) -> bool:
    """The router drops a zone or crime type it does not recognise, which would turn "Top
    beats in X" into a statewide answer. Every context value the text names must survive."""
    from app.agents.display_names import display_crime
    q = question.lower()
    zone = ctx.get("zone") or ctx.get("top_zone")
    if zone and zone.lower() in q and zone.lower() not in [str(z).lower() for z in params.get("zones") or []]:
        return False
    for ct in {ctx.get("crime_type"), ctx.get("top_crime")} - {None}:
        if display_crime(ct, "en").lower() in q and ct.upper() not in [str(c).upper() for c in params.get("crime_types") or []]:
            return False
    return True


def _candidates(template_id: str, ctx: dict, lang: str = "en") -> list[tuple[str, str, dict]]:
    """(question, template_id, params) candidates in priority order, each the query the chat
    really runs when the officer clicks it. A draft whose text routes to a different
    template than intended is dropped: it would answer some other question."""
    out, seen = [], set()
    for q, want, params in _drafts(ctx, lang):
        if q in seen or want == template_id:
            continue      # never re-suggest the kind of query that was just answered
        seen.add(q)
        if params is None:
            got, params = _route(q)
            if got != want or not _kept(q, ctx, params):
                continue
        out.append((q, want, params))
    return out


def grounded_followups(template_id: str, params: dict, rows: list[dict],
                       max_out: int = 3, lang: str = "en") -> list[str]:
    """Context-generated, DB-validated follow-up questions (answer guaranteed). One per
    kind of query, so three suggestions are three different next steps."""
    out: list[str] = []
    kinds: set[str] = set()
    for question, tid, tparams in _candidates(template_id, _context(params or {}, rows or []), lang):
        if len(out) >= max_out:
            break
        if tid in kinds:
            continue
        if _answerable(tid, tparams):
            out.append(question)
            kinds.add(tid)
    return out


# Answered from the real record. "Bengaluru North", the repeat-offender list and "this
# month" all read seeded demo rows only.
_STARTER_CANDIDATES: list[tuple[str, str, str, dict]] = [
    ("Which districts had the most theft in 2022?",
     "2022 ರಲ್ಲಿ ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ನಡೆದಿದೆ?",
     "T11", {"crime_types": ["THEFT"], "date_from": "2022-01-01", "date_to": "2022-12-31"}),
    ("Which districts had the most murders in 2022?",
     "2022 ರಲ್ಲಿ ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚು ಕೊಲೆಗಳು ದಾಖಲಾಗಿವೆ?",
     "T11", {"crime_types": ["MURDER"], "date_from": "2022-01-01", "date_to": "2022-12-31"}),
    ("Top areas for theft in Mysuru City",
     "ಮೈಸೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಪ್ರದೇಶಗಳು",
     "T23", {"zones": ["Mysuru City"], "crime_types": ["THEFT"], "dimension": "area"}),
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
