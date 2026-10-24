"""
Antar — Direct-answer writer (deterministic · English + Kannada)
=================================================================
Every answer opens with ONE plain sentence that answers the question as asked —
"Bengaluru City has the most theft cases — 26,466 FIRs, 17% of the Karnataka total" —
then the direction of travel, then the ranked evidence. An officer should be able to
stop reading after the first line and still have the answer.

This is what officers see whenever the language model is unavailable, and it is the
SAFE path either way: every number is read from the rows the whitelisted query returned
or from one extra COUNT over the same filters. Nothing here is generated.

`write_answer()` returns None for a template it does not handle, so the caller falls
back to the legacy formatter instead of guessing.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date

_MONTH_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MONTH_KN = ["ಜನವರಿ", "ಫೆಬ್ರವರಿ", "ಮಾರ್ಚ್", "ಏಪ್ರಿಲ್", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗಸ್ಟ್",
             "ಸೆಪ್ಟೆಂಬರ್", "ಅಕ್ಟೋಬರ್", "ನವೆಂಬರ್", "ಡಿಸೆಂಬರ್"]

from app.agents.display_names import (display_crime, display_direction, display_dimension,
                                      _KN_CRIME, _DIR_EN, _DIR_KN, _DIM_EN, _DIM_KN)

_EN_GENDER = {"M": "male", "F": "female", "O": "other"}
_KN_GENDER = {"M": "ಪುರುಷರು", "F": "ಮಹಿಳೆಯರು", "O": "ಇತರರು"}

_PERIOD_EN = {"today": "today", "yesterday": "yesterday", "last_24_hours": "in the last 24 hours",
              "last_2_days": "in the last 2 days", "last_7_days": "in the last 7 days",
              "last_30_days": "in the last 30 days",
              "this_week": "this week", "last_week": "last week", "this_month": "this month",
              "last_month": "last month", "last_3_months": "in the last 3 months",
              "last_6_months": "in the last 6 months", "this_year": "this year",
              "last_year": "last year"}
_PERIOD_KN = {"today": "ಇಂದು", "yesterday": "ನಿನ್ನೆ", "last_24_hours": "ಕಳೆದ 24 ಗಂಟೆಗಳಲ್ಲಿ",
              "last_2_days": "ಕಳೆದ 2 ದಿನಗಳಲ್ಲಿ", "last_7_days": "ಕಳೆದ 7 ದಿನಗಳಲ್ಲಿ",
              "last_30_days": "ಕಳೆದ 30 ದಿನಗಳಲ್ಲಿ",
              "this_week": "ಈ ವಾರ", "last_week": "ಕಳೆದ ವಾರ", "this_month": "ಈ ತಿಂಗಳು",
              "last_month": "ಕಳೆದ ತಿಂಗಳು", "last_3_months": "ಕಳೆದ 3 ತಿಂಗಳಲ್ಲಿ",
              "last_6_months": "ಕಳೆದ 6 ತಿಂಗಳಲ್ಲಿ", "this_year": "ಈ ವರ್ಷ", "last_year": "ಕಳೆದ ವರ್ಷ"}


# ── small formatters ─────────────────────────────────────────────────────────────

def _key(v) -> str:
    return str(v or "").replace("_", " ").strip().upper()


def _fmt(n) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return str(n)


def _pct(part, whole):
    try:
        return round(100 * part / whole) if whole else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _crime_en(v) -> str:
    return display_crime(v, "en", sentence_start=True)


def _crime_word(v, kn: bool) -> str:
    """The crime type as it reads inside a sentence."""
    return display_crime(v, "kn" if kn else "en")


def _mon(ym, kn: bool) -> str:
    try:
        y, m = str(ym).split("-")[:2]
        return f"{(_MONTH_KN if kn else _MONTH_EN)[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return str(ym)


def _win(w, kn: bool) -> str:
    a, b = w
    return _mon(a, kn) if a == b else f"{_mon(a, kn)}–{_mon(b, kn)}"


def _date(v) -> str:
    return str(v or "")[:10]


# Raw status spellings that are the same stage ('ChargeSheeted' / 'charge_sheeted').
_STATUS_CANON = {
    "chargesheeted": "Charge sheeted", "charge sheeted": "Charge sheeted",
    "dis/acq": "Disposed / acquitted", "un traced": "Undetected", "boundover": "Bound over",
}


def _nice_status(v) -> str:
    s = str(v or "Unknown").replace("_", " ").strip()
    if not s:
        return "Unknown"
    return _STATUS_CANON.get(s.lower()) or (s[:1].upper() + s[1:].lower())


def _blank(v) -> bool:
    """A missing value, including the string forms a JSON round-trip leaves behind.
    Without this a period of "null" printed straight through as "(null)" in the answer."""
    return v is None or str(v).strip().lower() in ("", "null", "none", "nan", "undefined")


# ── Absconding qualifier ──────────────────────────────────────────────────────────
# When the "absconding" predicate is on, every sentence has to say so, and nothing that
# ignores it (the T3 direction line, which cannot take the filter) may be shown beside it
# — otherwise the headline would describe absconding cases and the trend all crime.
def _absc(params) -> bool:
    return (params or {}).get("arrest_status") == "absconding"


def _absq(params, kn: bool) -> str:
    if not _absc(params):
        return ""
    return " (ಆರೋಪಿ ತಲೆಮರೆಸಿಕೊಂಡಿರುವ)" if kn else " with accused still at large"


def _accused_note(r, kn: bool) -> str:
    """Per-FIR: how many named accused are still not arrested."""
    a, b = r.get("accused"), r.get("arrested")
    if a is None or b is None:
        return ""
    try:
        left = int(a) - int(b)
    except (TypeError, ValueError):
        return ""
    if left <= 0:
        return ""
    return f" · {left}/{int(a)} ಆರೋಪಿ ಬಂಧನವಾಗಿಲ್ಲ" if kn else f" · {left} of {int(a)} accused not arrested"


def _scope(params: dict, kn: bool) -> str:
    df, dt, per = params.get("date_from"), params.get("date_to"), params.get("period")
    df = None if _blank(df) else df
    dt = None if _blank(dt) else dt
    per = None if _blank(per) else per
    label = params.get("period_label")
    if label and df and dt and not kn:
        return str(label)              # "in March 2023", "since 2020", "in the last 2 years"
    if df and dt:
        df, dt = str(df), str(dt)
        if df[:4] == dt[:4] and df[5:10] == "01-01" and dt[5:10] == "12-31":
            return f"{df[:4]} ರಲ್ಲಿ" if kn else f"in {df[:4]}"
        return f"{df} ರಿಂದ {dt} ರವರೆಗೆ" if kn else f"between {df} and {dt}"
    if per:
        return _PERIOD_KN.get(per, per) if kn else _PERIOD_EN.get(per, str(per).replace("_", " "))
    return "ದಾಖಲಾದ ಎಲ್ಲಾ ವರ್ಷಗಳಲ್ಲಿ" if kn else "across all years on record"


_KN_STATUS = {
    "under investigation": "ತನಿಖೆಯಲ್ಲಿ", "pending trial": "ವಿಚಾರಣೆ ಬಾಕಿ", "convicted": "ಶಿಕ್ಷೆಯಾಗಿದೆ",
    "undetected": "ಪತ್ತೆಯಾಗಿಲ್ಲ", "traced": "ಪತ್ತೆಯಾಗಿದೆ", "false case": "ಸುಳ್ಳು ಪ್ರಕರಣ",
    "transferred - under investigation": "ವರ್ಗಾವಣೆ — ತನಿಖೆಯಲ್ಲಿ", "compounded": "ರಾಜಿ",
    "charge sheeted": "ದೋಷಾರೋಪ ಪಟ್ಟಿ ಸಲ್ಲಿಕೆ", "disposed": "ವಿಲೇವಾರಿ", "acquitted": "ಖುಲಾಸೆ",
    "closed": "ಮುಕ್ತಾಯ", "open": "ತೆರೆದ",
    "disposed / acquitted": "ವಿಲೇವಾರಿ / ಖುಲಾಸೆ", "bound over": "ಮುಚ್ಚಳಿಕೆ", "abated": "ರದ್ದಾಗಿದೆ",
    "other disposal": "ಇತರ ವಿಲೇವಾರಿ",
}


def _status(v, kn: bool) -> str:
    s = _nice_status(v)
    return _KN_STATUS.get(s.lower(), s) if kn else s


_AGE_BANDS = [(17, "under 18", "18 ಕ್ಕಿಂತ ಕಡಿಮೆ"), (25, "18–25", "18–25"), (35, "26–35", "26–35"),
              (45, "36–45", "36–45"), (60, "46–60", "46–60"), (200, "over 60", "60 ಕ್ಕಿಂತ ಹೆಚ್ಚು")]


def _band(v, kn: bool):
    """Raw ages → readable bands ("aged 49 — 4%" told nobody anything). (label, sort index)."""
    try:
        a = int(float(v))
    except (TypeError, ValueError):
        return str(v or "—"), 99
    for i, (hi, en, kn_l) in enumerate(_AGE_BANDS):
        if a <= hi:
            return (kn_l if kn else en), i
    return str(v), 99


def _in_loc(where: str, kn: bool) -> str:
    """'in Karnataka' / 'ಕರ್ನಾಟಕದಲ್ಲಿ' — Kannada attaches the case ending to the place."""
    if kn:
        return "ಕರ್ನಾಟಕದಲ್ಲಿ" if where == "ಕರ್ನಾಟಕ" else f"{where} ನಲ್ಲಿ"
    return f"in {where}"


_COUNT_RE = re.compile(r"\b(how many|how much|total|number of|count|statewide)\b")
_FORECAST_RE = re.compile(r"\b(predict|prediction|forecast|next month|next week|projection)\b")


def _is_count_q(text: str) -> bool:
    """ "how many…", "total…", "ಎಷ್ಟು…", or "<crime> FIRs in 2023" — the officer wants a number."""
    low = (text or "").lower()
    if _COUNT_RE.search(low) or "ಎಷ್ಟು" in low or "ಒಟ್ಟು" in low:
        return True
    return bool(re.search(r"\b20[12]\d\b", low) and re.search(r"\b(firs?|registered)\b", low))


def _is_women(cts) -> bool:
    try:
        from app.services.zcql_repo import WOMEN_CRIMES
    except Exception:
        return False
    return len(set(cts or []) & set(WOMEN_CRIMES)) >= 4


def _breakdown(template_id: str, params: dict, key: str) -> list[tuple[str, int]]:
    """A second whitelisted query over the same filters — e.g. which districts a count came from."""
    try:
        from app.agents.query_agent import run_template
        rows, _ = run_template(template_id, params)
        return [(r.get(key), int(r.get("n") or 0)) for r in rows if r.get(key) is not None]
    except Exception:
        return []


def _yi(year):
    """The official yearly record (year_intel) for one year."""
    try:
        from app.agents.query_agent import run_template
        rows, _ = run_template("T16", {"year": int(year)})
        return rows[0] if rows else None
    except Exception:
        return None


# ── the two extra facts a direct answer needs: a total, and a direction ───────────

def _total_like(template_id: str, params: dict):
    """COUNT over exactly the same validated filters the template used.

    A share like "17% of the Karnataka total" needs the denominator, and the template's
    own rows are capped (top 10), so summing them would silently understate it. This
    rebuilds the template's spec, drops grouping/ordering/limit and counts.
    """
    try:
        from app.services.zcql_repo import build_spec, Aggregate
        from app.services.zcql_local import run_query
        from app.agents.query_agent import _bound_to_today
        spec = build_spec(template_id, dict(params or {}))
        if not spec.aggregates:
            spec.aggregates = [Aggregate("count", "crime_id" if spec.table == "crimes" else "*", "n")]
        spec.select = []
        spec.group_by = []
        spec.order_by = None
        spec.limit = None
        _bound_to_today(spec)
        rows = run_query(spec)
        v = rows[0].get("n") if rows else None
        return int(v) if v is not None else None
    except Exception:
        return None


def _partial_months() -> set[str]:
    """Months that cannot be compared with a full one, because they are cut short.

    Two of them, not one. The wall-clock month is obviously still running, but so is the
    month where the REAL FIR record stops: that extract ends on the 10th, so its last
    month holds ~9.5k rows against ~31k for the months before it. Counting it as complete
    made every trend read as a steep fall that was purely the truncation — "crime down
    26%" when nothing had happened except the data running out.
    """
    import calendar
    from app.services.zcql_repo import real_data_today
    out: set[str] = set()
    for anchor in (date.today(), real_data_today()):
        try:
            if anchor.day < calendar.monthrange(anchor.year, anchor.month)[1]:
                out.add(anchor.strftime("%Y-%m"))
        except Exception:
            continue
    return out


def _complete(series: list[tuple[str, int]]):
    """Split a monthly series into complete months and the one still in progress."""
    cut = _partial_months()
    cur = date.today().strftime("%Y-%m")
    done = [(m, n) for m, n in series if m and m < cur and m not in cut]
    partial = next(((m, n) for m, n in series if m in cut), None)
    return done, partial


def _direction(done: list[tuple[str, int]]):
    """Last 3 complete months vs the 3 before; ±5% counts as stable."""
    if len(done) < 2:
        return None
    if len(done) >= 6:
        a = sum(n for _, n in done[-6:-3])
        b = sum(n for _, n in done[-3:])
        wa, wb = (done[-6][0], done[-4][0]), (done[-3][0], done[-1][0])
    else:
        a, b = done[0][1], done[-1][1]
        wa, wb = (done[0][0],) * 2, (done[-1][0],) * 2
    pct = (100 if b > 0 else 0) if a == 0 else round(100 * (b - a) / a)
    word = "UPWARD" if pct > 5 else "DOWNWARD" if pct < -5 else "STABLE"
    return {"word": word, "pct": pct, "from": wa, "to": wb}


def _trend(crime_types, zones):
    try:
        from app.agents.query_agent import run_template
        rows, _ = run_template("T3", {"crime_types": list(crime_types or []),
                                      "zones": list(zones or []), "months": 7})
        done, _ = _complete([(str(r.get("month")), int(r.get("n") or 0)) for r in rows])
        return _direction(done)
    except Exception:
        return None


def _dir_line(d, kn: bool, where: str = ""):
    if not d:
        return None
    to, fr, p = _win(d["to"], kn), _win(d["from"], kn), abs(d["pct"])
    if kn:
        tail = (f"{fr} ಗಿಂತ {to} ಅವಧಿಯಲ್ಲಿ {p}% ಹೆಚ್ಚು" if d["word"] == "UPWARD"
                else f"{fr} ಗಿಂತ {to} ಅವಧಿಯಲ್ಲಿ {p}% ಕಡಿಮೆ" if d["word"] == "DOWNWARD"
                else f"{fr} ಮತ್ತು {to} ನಡುವೆ ಬದಲಾವಣೆ ±5% ಒಳಗೆ")
        return f"• ಪ್ರವೃತ್ತಿ: {where}{_DIR_KN[d['word']]} — {tail}."
    # Antar's voice (docs/ANTAR_CONSTITUTION.md): a sentence, not a shouted code word.
    # The "Direction:" label is structural — antar_identity.shape() lifts it into CONTEXT.
    state = {"UPWARD": "Rising", "DOWNWARD": "Falling", "STABLE": "Steady"}[d["word"]]
    verb = {"UPWARD": f"up {p}%", "DOWNWARD": f"down {p}%", "STABLE": "within ±5%"}[d["word"]]
    return f"• Direction: {state}{(' in ' + where) if where else ''} — {verb}, {to} vs {fr}."


# ── writers, one per template ───────────────────────────────────────────────────

def _runners_up(rows, dim: str, kn: bool) -> str:
    """ ", followed by Bengaluru Dist (953) and Belagavi Dist (640)" — the next two places.

    A ranking's bottom line should read like a colleague saying it, not stop at first place:
    the gap to second place is usually the point.
    """
    nxt = [r for r in rows[1:3] if r.get(dim)]
    if not nxt:
        return ""
    parts = [f"{r.get(dim)} ({_fmt(r.get('n') or 0)})" for r in nxt]
    if kn:
        return ", ನಂತರ " + " ಮತ್ತು ".join(parts)
    return ", followed by " + " and ".join(parts)


def _w_rank(rows, kn, params, template_id):
    """T11 — "most theft?", "which district has the most crime?", "least crime district"."""
    dim = next((k for k in rows[0] if k != "n"), "zone")
    cts = params.get("crime_types") or []
    asc = str(params.get("order") or "").lower() == "asc"
    total = _total_like(template_id, params)
    place = str(rows[0].get(dim) or "—")
    n = int(rows[0].get("n") or 0)
    share = _pct(n, total)
    scope = _scope(params, kn)
    women = _is_women(cts)
    if kn:
        what = ("ಮಹಿಳೆಯರ ವಿರುದ್ಧದ ಅಪರಾಧಗಳು" if women else
                (", ".join(_crime_word(c, True) for c in cts) + " ಪ್ರಕರಣಗಳು") if cts else "ಅಪರಾಧ ಪ್ರಕರಣಗಳು") + _absq(params, True)
        share_s = f", ಒಟ್ಟು ಪ್ರಕರಣಗಳ {share}%" if share is not None else ""
        runners = _runners_up(rows, dim, True)
        lead = (f"[COMPUTED] **{place}** ನಲ್ಲಿ {'ಅತಿ ಕಡಿಮೆ' if asc else 'ಅತಿ ಹೆಚ್ಚು'} {what} ದಾಖಲಾಗಿವೆ — "
                f"**{_fmt(n)}** FIR{share_s}{runners}" + (f", {scope}." if runners else f" ({scope})."))
    else:
        what = ("crimes against women" if women else
                (" / ".join(_crime_word(c, False) for c in cts) + " cases") if cts else "crime")
        if _absc(params):
            what = ("crimes against women" if women else
                    (" / ".join(_crime_word(c, False) for c in cts) + " cases") if cts else "cases") + _absq(params, False)
        amount = ("the least" if what == "crime" else "the fewest") if asc else "the most"
        _in = ", ".join(params.get("zones") or [])
        share_s = (f", {share}% of the total in {_in}" if _in else f", {share}% of the Karnataka total") if share is not None else ""
        runners = _runners_up(rows, dim, False)
        # "(640) (across all years …)" read as a stutter; after the runners-up the scope
        # follows as a clause instead.
        tail = f", {scope}." if runners else f" ({scope})."
        lead = f"[COMPUTED] **{place}** has {amount} {what} — **{_fmt(n)}** FIRs{share_s}{runners}{tail}"
    lines = [lead]
    # The direction compares the latest months — meaningless under a past-period question
    # ("crimes against women 2023") — so it is shown only for open-ended scopes.
    if dim in ("zone", "district") and not asc and not params.get("date_from") and not _absc(params):
        lines.append(_dir_line(_trend(cts, [place]), kn, f"{place} ನಲ್ಲಿ " if kn else place))
    if kn:
        lines.append(f"{'ಕಡಿಮೆ ಇರುವ' if asc else 'ಅಗ್ರ'} {len(rows)} {_DIM_KN.get(dim, 'ಸ್ಥಳಗಳು')}:")
    else:
        lines.append(f"{'Lowest' if asc else 'Top'} {len(rows)} {_DIM_EN.get(dim, 'places')}:")
    for i, r in enumerate(rows, 1):
        c = int(r.get("n") or 0)
        p = _pct(c, total)
        lines.append(f"{i}. {r.get(dim) or '—'} — {_fmt(c)}" + (f" ({p}%)" if p is not None else ""))
    return lines


def _w_types(rows, kn, params, template_id):
    """T13 — "which crime is most common?"."""
    key = next((k for k in rows[0] if k != "n"), "crime_type")
    total = _total_like(template_id, params)
    top, n = rows[0].get(key), int(rows[0].get("n") or 0)
    share = _pct(n, total)
    zones = params.get("zones") or []
    where = ", ".join(zones) if zones else ("ಕರ್ನಾಟಕ" if kn else "Karnataka")
    scope = _scope(params, kn)
    if kn:
        share_s = f", ಒಟ್ಟು ಪ್ರಕರಣಗಳ {share}%" if share is not None else ""
        lead = (f"[COMPUTED] {_in_loc(where, True)} ಅತಿ ಹೆಚ್ಚು ದಾಖಲಾದ ಅಪರಾಧ **{_crime_word(top, True)}** — "
                f"**{_fmt(n)}** FIR{share_s} ({scope}).")
    else:
        share_s = f", {share}% of all cases" if share is not None else ""
        among = " among cases with accused still at large" if _absc(params) else ""
        lead = (f"[COMPUTED] **{_crime_en(top)}** is the most common crime in {where}{among} — "
                f"**{_fmt(n)}** FIRs{share_s} ({scope}).")
    lines = [lead] + ([] if _absc(params) or params.get("stations") else [_dir_line(_trend([top], zones), kn)])
    lines.append("ಪ್ರಮುಖ ಅಪರಾಧ ಪ್ರಕಾರಗಳು:" if kn else "Most common crime types:")
    for i, r in enumerate(rows[:6], 1):
        c = int(r.get("n") or 0)
        p = _pct(c, total)
        label = _crime_word(r.get(key), True) if kn else _crime_en(r.get(key))
        lines.append(f"{i}. {label} — {_fmt(c)}" + (f" ({p}%)" if p is not None else ""))
    return lines


_PEAK_RE = re.compile(r"\b(peak|busiest|worst|highest)\s+month\b|\bwhich month\b|\bmonth (?:with|had) the most\b", re.I)


def _w_trend(rows, kn, params, template_id):
    """T3 — "is theft rising?"."""
    series = [(str(r.get("month")), int(r.get("n") or 0)) for r in rows if r.get("month")]
    if not series:
        return None
    done, partial = _complete(series)
    cts = params.get("crime_types") or []
    zones = params.get("zones") or []
    what = ", ".join(_crime_word(c, kn) for c in cts) if cts else ("ಅಪರಾಧ" if kn else "crime")
    where = ", ".join(zones) if zones else ("ಕರ್ನಾಟಕ" if kn else "Karnataka")
    d = _direction(done)
    lines = []
    q = str(params.get("_q") or "")
    if done and (_PEAK_RE.search(q) or "ಗರಿಷ್ಠ ತಿಂಗಳು" in q or "ಯಾವ ತಿಂಗಳು" in q):
        # "peak month for cybercrime in 2022" asks for a month: lead with it.
        pm, pn = max(done, key=lambda x: x[1])
        avg = sum(n for _, n in done) / len(done)
        above = round(100 * (pn - avg) / avg) if avg else 0
        lines.append(f"[COMPUTED] {_in_loc(where, True)} {what} ಪ್ರಕರಣಗಳು **{_mon(pm, kn)}** ರಲ್ಲಿ ಗರಿಷ್ಠ — "
                     f"**{_fmt(pn)}**, ಮಾಸಿಕ ಸರಾಸರಿಗಿಂತ {above}% ಹೆಚ್ಚು." if kn else
                     f"[COMPUTED] {what.capitalize()} cases in {where} peaked in **{_mon(pm, kn)}** — "
                     f"**{_fmt(pn)}**, {above}% above the monthly average of {_fmt(round(avg))}.")
        for m, n in done[-12:]:
            lines.append(f"• {_mon(m, kn)}: {_fmt(n)} {'ಪ್ರಕರಣಗಳು' if kn else 'cases'}")
        return lines
    if d:
        span = f"{_win(d['to'], kn)} vs {_win(d['from'], kn)}"
        if kn:
            sign = "+" if d["pct"] > 0 else ""
            lines.append(f"[COMPUTED] {_in_loc(where, True)} {what} ಪ್ರಕರಣಗಳಲ್ಲಿ **{_DIR_KN[d['word']]}** — "
                         f"{sign}{d['pct']}% ({span}).")
        else:
            state = {"UPWARD": "rising", "DOWNWARD": "falling", "STABLE": "steady"}[d["word"]]
            verb = {"UPWARD": f"up {abs(d['pct'])}%", "DOWNWARD": f"down {abs(d['pct'])}%",
                    "STABLE": "little change"}[d["word"]]
            lines.append(f"[COMPUTED] {what.capitalize()} cases in {where} are **{state}** — {verb} ({span}).")
        fc = _forecast_line(done, kn, params)
        if fc:
            lines.append(fc)
    else:
        m, n = (done or series)[-1]
        lines.append(f"[COMPUTED] {_in_loc(where, True)} ಒಂದೇ ಪೂರ್ಣ ತಿಂಗಳ ದತ್ತಾಂಶ ಇದೆ ({_mon(m, kn)}: {_fmt(n)}) — "
                     f"ಪ್ರವೃತ್ತಿ ಹೇಳಲು ಸಾಕಾಗುವುದಿಲ್ಲ." if kn else
                     f"[COMPUTED] Only one complete month is on record for {what} in {where} "
                     f"({_mon(m, kn)}: {_fmt(n)} cases) — not enough to call a direction.")
    for m, n in done[-8:]:
        lines.append(f"• {_mon(m, kn)}: {_fmt(n)} {'ಪ್ರಕರಣಗಳು' if kn else 'cases'}")
    if done:
        pm, pn = max(done, key=lambda x: x[1])
        lines.append(f"ಗರಿಷ್ಠ: {_mon(pm, kn)} ({_fmt(pn)})." if kn else f"Peak: {_mon(pm, kn)} with {_fmt(pn)} cases.")
    if partial:
        pm, pn = partial
        # Two different reasons a month is short: it has not finished yet, or the FIR
        # record simply stops partway through it. Saying "still in progress" about a month
        # two years in the past would read as a mistake to an officer.
        running = pm == date.today().strftime("%Y-%m")
        if kn:
            lines.append(f"{_mon(pm, kn)} ಇನ್ನೂ ಮುಗಿದಿಲ್ಲ (ಇಲ್ಲಿಯವರೆಗೆ {_fmt(pn)}) — ಪ್ರವೃತ್ತಿಯಲ್ಲಿ ಸೇರಿಸಿಲ್ಲ."
                         if running else
                         f"{_mon(pm, kn)} ರ ದಾಖಲೆ ಅಪೂರ್ಣ ({_fmt(pn)} ಮಾತ್ರ) — ಪ್ರವೃತ್ತಿಯಲ್ಲಿ ಸೇರಿಸಿಲ್ಲ.")
        else:
            lines.append(f"{_mon(pm, kn)} is still in progress ({_fmt(pn)} so far) and is left out of the direction."
                         if running else
                         f"The record for {_mon(pm, kn)} is incomplete ({_fmt(pn)} FIRs) and is left out of the direction.")
    return lines


def _forecast_line(done, kn, params):
    """ "predict theft next month" — a plain estimate from the last 3 complete months."""
    q = str(params.get("_q") or "")
    if not (_FORECAST_RE.search(q.lower()) or "ಮುನ್ಸೂಚನೆ" in q) or len(done) < 3:
        return None
    last3 = [n for _, n in done[-3:]]
    est, lo, hi = round(sum(last3) / 3), min(last3), max(last3)
    if kn:
        return (f"• ಮುಂದಿನ ತಿಂಗಳ ಅಂದಾಜು: ಸುಮಾರು **{_fmt(est)}** ಪ್ರಕರಣಗಳು "
                f"(ಇತ್ತೀಚಿನ ವ್ಯಾಪ್ತಿ {_fmt(lo)}–{_fmt(hi)}), ಕಳೆದ 3 ಪೂರ್ಣ ತಿಂಗಳ ಆಧಾರದಲ್ಲಿ.")
    return (f"• Next month (estimate): about **{_fmt(est)}** cases (recent range "
            f"{_fmt(lo)}–{_fmt(hi)}), based on the last 3 complete months.")


def _w_split(rows, kn, params, template_id):
    """T7 (victim/suspect demographics) and T8 (case status)."""
    key = next((k for k in rows[0] if k != "n"), None)
    if not key:
        return None
    is_age = key in ("age", "age_band")
    merged: dict[str, int] = {}
    order: dict[str, int] = {}
    for r in rows:
        raw = r.get(key)
        if template_id == "T8":
            lab = _status(raw, kn)                # 'charge_sheeted' and 'Charge Sheeted' are one status
        elif key == "gender":
            lab = (_KN_GENDER if kn else _EN_GENDER).get(str(raw).upper(), str(raw))
        elif is_age:
            lab, order[_band(raw, kn)[0]] = _band(raw, kn)
        else:
            lab = str(raw or "—")
        merged[lab] = merged.get(lab, 0) + int(r.get("n") or 0)
    by_count = sorted(merged.items(), key=lambda x: -x[1])
    # Age bands read youngest → oldest; everything else by size.
    items = sorted(merged.items(), key=lambda x: order.get(x[0], 99)) if is_age else by_count
    total = sum(merged.values()) or None
    if template_id == "T8":
        # Every status counts toward the total, not only the groups the query returned.
        total = max(total or 0, _total_like(template_id, params) or 0) or None
    top, n = by_count[0]
    p = _pct(n, total)
    if template_id == "T8":
        cts = params.get("crime_types") or []
        zones = params.get("zones") or []
        dated = bool(params.get("date_from") or params.get("period"))
        if kn:
            what = (", ".join(_crime_word(c, True) for c in cts) + " ಪ್ರಕರಣಗಳಲ್ಲಿ") if cts else "ಪ್ರಕರಣಗಳಲ್ಲಿ"
            loc = f"{', '.join(zones)} ನಲ್ಲಿ " if zones else ""
            when = f"{_scope(params, True)} " if dated else ""
            lead = f"[COMPUTED] {loc}{when}{what} ಹೆಚ್ಚಿನವು **{top}** ಹಂತದಲ್ಲಿವೆ — {_fmt(total)} ರಲ್ಲಿ {_fmt(n)} ({p}%)."
        else:
            what = (" / ".join(_crime_word(c, False) for c in cts) + " cases") if cts else "cases"
            loc = f" in {', '.join(zones)}" if zones else ""
            when = f" {_scope(params, False)}" if dated else ""
            lead = f"[COMPUTED] Most {what}{loc}{when} are **{top}** — {_fmt(n)} of {_fmt(total)} ({p}%)."
        head = "ಸ್ಥಿತಿವಾರು:" if kn else "By status:"
    else:
        ent = params.get("entity") or "victims"
        ent_kn = "ಸಂತ್ರಸ್ತರು" if ent == "victims" else "ಶಂಕಿತರು"
        # victims are linked to FIRs, so the crime and the place asked about are named
        cts, zones = params.get("crime_types") or [], params.get("zones") or []
        who = ent
        if ent == "victims" and not kn and (cts or zones):
            who = ((" / ".join(_crime_word(c, False) for c in cts) + " ") if cts else "") + "victims"                   + (f" in {', '.join(zones)}" if zones else "")
        dim = params.get("dimension")
        if kn:
            label = f"{top} ವಯಸ್ಸಿನವರು" if is_age else top
        elif key == "gender" or dim == "age_group":
            label = {"adult": "adults", "child": "children"}.get(str(top), top)
        elif dim == "relation":
            label = f"{top} to the accused" if str(top) in ("family", "in-laws", "neighbour", "employee") else str(top)
            if str(top) in ("stranger", "stranger, online"):
                label = "strangers to the accused" if top == "stranger" else "strangers met online"
            elif str(top) in ("acquaintance", "business contact"):
                label = f"{top}s of the accused"
            elif str(top) == "spouse":
                label = "the accused's spouse"
        elif dim == "occupation":
            label = str(top)
        else:
            label = f"aged {top}"
        lead = (f"[COMPUTED] ಹೆಚ್ಚಿನ {ent_kn} **{label}** — {_fmt(total)} ರಲ್ಲಿ {_fmt(n)} ({p}%)." if kn else
                f"[COMPUTED] Most {who} are **{label}** — {_fmt(n)} of {_fmt(total)} ({p}%).")
        head = "ವಿಭಜನೆ:" if kn else "Breakdown:"
    lines = [lead, head]
    for i, (lab, c) in enumerate(items[:8], 1):
        lines.append(f"{i}. {lab} — {_fmt(c)} ({_pct(c, total)}%)")
    return lines


def _w_top_suspects(rows, kn, params, template_id):
    """T4 — most-linked suspects."""
    r0 = rows[0]
    name = r0.get("full_name") or r0.get("suspect_id")
    zone = f", {r0['address_zone']}" if r0.get("address_zone") else ""
    lead = (f"[COMPUTED] ಅತಿ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳಿಗೆ ಸಂಬಂಧಿಸಿದ ಶಂಕಿತ **{name}** ({r0.get('suspect_id')}{zone}) — "
            f"**{_fmt(r0.get('crime_count'))}** ಪ್ರಕರಣಗಳು." if kn else
            f"[COMPUTED] The most-linked suspect is **{name}** ({r0.get('suspect_id')}{zone}) — "
            f"linked to **{_fmt(r0.get('crime_count'))}** cases.")
    lines = [lead, "ಪ್ರಮುಖ ಶಂಕಿತರು:" if kn else "Most-linked suspects:"]
    for i, r in enumerate(rows[:8], 1):
        z = f", {r['address_zone']}" if r.get("address_zone") else ""
        lines.append(f"{i}. {r.get('full_name') or r.get('suspect_id')} ({r.get('suspect_id')}{z}) — "
                     f"{_fmt(r.get('crime_count'))} {'ಪ್ರಕರಣಗಳು' if kn else 'cases'}")
    return lines


def _w_repeat(rows, kn, params, template_id):
    """T5 — repeat offenders."""
    ranked = sorted(rows, key=lambda r: -int(r.get("prior_count") or 0))
    r0 = ranked[0]
    mp = params.get("min_priors") or 5
    lead = (f"[VERIFIED] ಅತಿ ಹೆಚ್ಚು ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿ **{r0.get('full_name')}** ({r0.get('suspect_id')}) — "
            f"**{_fmt(r0.get('prior_count'))}** ಹಿಂದಿನ ಅಪರಾಧಗಳು." if kn else
            f"[VERIFIED] The most prolific repeat offender is **{r0.get('full_name')}** ({r0.get('suspect_id')}) — "
            f"**{_fmt(r0.get('prior_count'))}** prior offences.")
    lines = [lead, f"{mp}+ ಹಿಂದಿನ ಅಪರಾಧಗಳಿರುವ ಅಗ್ರ {len(ranked)}:" if kn
             else f"Top {len(ranked)} offenders with {mp}+ priors:"]
    for i, r in enumerate(ranked[:10], 1):
        z = f", {r['address_zone']}" if r.get("address_zone") else ""
        lines.append(f"{i}. {r.get('full_name')} ({r.get('suspect_id')}{z}) — {_fmt(r.get('prior_count'))}")
    return lines


def _w_suspects(rows, kn, params, template_id):
    """T2 — look up a suspect by name or alias."""
    term = str(params.get("name_or_alias") or "").strip()
    tl = term.casefold()
    exact = next((r for r in rows if tl and tl in (str(r.get("full_name") or "").casefold(),
                                                   str(r.get("alias") or "").casefold())), None)
    best = exact or rows[0]
    bits = [best.get("suspect_id")]
    if best.get("alias"):
        bits.append(f"alias “{best['alias']}”" if not kn else f"ಉಪನಾಮ “{best['alias']}”")
    if best.get("age"):
        bits.append(f"{best['age']}")
    if best.get("address_zone"):
        bits.append(best["address_zone"])
    label = ("ನಿಖರ ಹೊಂದಾಣಿಕೆ" if exact else "ಮೊದಲ ಹೊಂದಾಣಿಕೆ") if kn else ("Exact match" if exact else "First match")
    lead = (f"[VERIFIED] “{term}” ಗೆ **{len(rows)}** ಶಂಕಿತರು ಹೊಂದಾಣಿಕೆಯಾಗಿದ್ದಾರೆ. {label}: "
            f"**{best.get('full_name')}** ({', '.join(str(b) for b in bits if b)})." if kn else
            f"[VERIFIED] **{len(rows)}** suspect{'s' if len(rows) != 1 else ''} match “{term}”. {label}: "
            f"**{best.get('full_name')}** ({', '.join(str(b) for b in bits if b)}).")
    lines = [lead]
    others = [r for r in rows if r is not best][:6]
    if others:
        lines.append("ಇತರ ಹೊಂದಾಣಿಕೆಗಳು:" if kn else "Other matches:")
        for i, r in enumerate(others, 1):
            z = f", {r['address_zone']}" if r.get("address_zone") else ""
            al = f" “{r['alias']}”" if r.get("alias") else ""
            lines.append(f"{i}. {r.get('full_name')}{al} ({r.get('suspect_id')}{z})")
    return lines


def _w_linked(rows, kn, params, template_id):
    """T9 — every case linked to one suspect."""
    sid = params.get("suspect_id") or "—"
    ranked = sorted(rows, key=lambda r: str(r.get("occurred_at") or ""), reverse=True)
    r0 = ranked[0]
    fir = r0.get("fir_number") or r0.get("crime_id")
    lead = (f"[VERIFIED] **{sid}** **{len(rows)}** ಪ್ರಕರಣಗಳಿಗೆ ಸಂಬಂಧಿಸಿದ್ದಾರೆ; ಇತ್ತೀಚಿನದು FIR {fir} — "
            f"{_crime_word(r0.get('crime_type'), True)}, {r0.get('zone')}, {_date(r0.get('occurred_at'))}." if kn else
            f"[VERIFIED] **{sid}** is linked to **{len(rows)}** case{'s' if len(rows) != 1 else ''}; the most recent is "
            f"FIR {fir} — {_crime_word(r0.get('crime_type'), False)}, {r0.get('zone')}, {_date(r0.get('occurred_at'))}.")
    lines = [lead, "ಸಂಬಂಧಿತ ಪ್ರಕರಣಗಳು:" if kn else "Linked cases:"]
    for i, r in enumerate(ranked[:10], 1):
        f = r.get("fir_number") or r.get("crime_id")
        ct = _crime_word(r.get("crime_type"), True) if kn else _crime_en(r.get("crime_type"))
        st = f" · {_status(r.get('status'), kn)}" if r.get("status") else ""
        lines.append(f"{i}. FIR {f} — {ct}, {r.get('zone')}, {_date(r.get('occurred_at'))}{st}")
    return lines


def _statq(params: dict, kn: bool) -> str:
    """The status filter, said in the headline. A list run with status=Undetected used to be
    headed "445 burglary cases in Tumakuru", with nothing to say they were the undetected ones."""
    st = [s for s in (params.get("status") or []) if s]
    if not st:
        return ""
    try:
        from app.agents.system_catalog import STATUS_CLOSED, STATUS_OPEN
        if set(st) == set(STATUS_OPEN):
            return " (ಇನ್ನೂ ತೆರೆದಿರುವ)" if kn else " that are still open"
        if set(st) == set(STATUS_CLOSED):
            return " (ಮುಕ್ತಾಯಗೊಂಡ)" if kn else " that are closed"
    except Exception:
        pass
    names = list(dict.fromkeys(_status(s, kn) for s in st))
    shown = ", ".join(names[:3]) + ("…" if len(names) > 3 else "")
    return f" ({shown})" if kn else f" with status {shown}"


def _w_list(rows, kn, params, template_id):
    """T1 / T12 — case lists ("theft cases in Rajajinagar", "recent crimes")."""
    cts = params.get("crime_types") or []
    zones = params.get("zones") or []
    # Rows that came back only after filters were dropped are "the closest records", not a
    # count of anything: with no filters left, the total would be the whole register.
    total = None if params.get("related_only") else _total_like(template_id, params)
    r0 = rows[0]
    latest, zone0 = _date(r0.get("occurred_at")), r0.get("zone") or "—"
    scoped = bool(params.get("date_from") or params.get("period"))
    if kn:
        what = ((", ".join(_crime_word(c, True) for c in cts) + " ಪ್ರಕರಣಗಳು") if cts else "ಪ್ರಕರಣಗಳು") + _absq(params, True)
        where = f"{', '.join(zones)} ನಲ್ಲಿ " if zones else ""
        scope = f" ({_scope(params, True)})" if scoped else ""
        count = f"ಒಟ್ಟು **{_fmt(total)}** {what} ದಾಖಲಾಗಿವೆ{scope}; " if total else ""
        lead = f"[VERIFIED] {where}{count}ಇತ್ತೀಚಿನ {len(rows)} ಕೆಳಗಿವೆ — ಕೊನೆಯದು **{latest}** ({zone0})."
    else:
        what = ((" / ".join(_crime_word(c, False) for c in cts) + " cases") if cts else "cases") + _absq(params, False) + _statq(params, False)
        where = f" in {', '.join(zones)}" if zones else ""
        scope = f" {_scope(params, False)}" if scoped else ""
        if total:
            lead = (f"[VERIFIED] **{_fmt(total)}** {what}{where} are on record{scope}; here are the latest "
                    f"{len(rows)} — the most recent on **{latest}** ({zone0}).")
        else:
            lead = f"[VERIFIED] The {len(rows)} most recent {what}{where} — the latest on **{latest}** ({zone0})."
    lines = [lead]
    for i, r in enumerate(rows[:12], 1):
        f = r.get("fir_number") or r.get("crime_id") or "—"
        ct = _crime_word(r.get("crime_type"), True) if kn else _crime_en(r.get("crime_type"))
        st = f" · {_status(r.get('status'), kn)}" if r.get("status") else ""
        lines.append(f"{i}. FIR {f} — {ct}, {r.get('zone') or '—'}, {_date(r.get('occurred_at'))}{st}"
                     f"{_accused_note(r, kn)}")
    return lines


def _cats(s):
    """ "Theft (319), Motor Vehicle Accidents Non-Fatal (228), …" → [(name, n), …]."""
    return [(m.group(1).strip(), int(m.group(2))) for m in re.finditer(r"([^,(]+?)\s*\((\d+)\)", s or "")]


def _year_note(r, kn):
    yr = int(r.get("year") or 0)
    if "partial" in str(r.get("summary") or "").lower():
        return (f"ಗಮನಿಸಿ: {yr} ಭಾಗಶಃ ವರ್ಷ (ಜನವರಿ–ಮಾರ್ಚ್ ಮಾತ್ರ)." if kn else
                f"Note: {yr} is a partial year (January–March only).")
    if not r.get("is_real", 1):
        return (f"ಗಮನಿಸಿ: {yr} ರ ಅಂಕಿಅಂಶಗಳು ಡೆಮೊ ಪದರದಿಂದ ಬಂದಿವೆ, ಅಧಿಕೃತ ದಾಖಲೆಯಲ್ಲ." if kn else
                f"Note: {yr} figures come from the forward/demo layer, not the official record.")
    return None


def _comparable(r) -> bool:
    return bool(r) and bool(r.get("is_real", 1)) and "partial" not in str(r.get("summary") or "").lower()


def _yoy_line(word, pct, y1, n1, kn):
    if kn:
        tail = (f"{y1} ಕ್ಕೆ ಹೋಲಿಸಿದರೆ ±5% ಒಳಗೆ" if word == "STABLE"
                else f"{y1} ಗಿಂತ {abs(pct)}% {'ಹೆಚ್ಚು' if pct > 0 else 'ಕಡಿಮೆ'}")
        return f"• ಪ್ರವೃತ್ತಿ: {_DIR_KN[word]} — {tail} ({y1}: {_fmt(n1)})."
    verb = {"UPWARD": f"up {abs(pct)}%", "DOWNWARD": f"down {abs(pct)}%", "STABLE": "within ±5%"}[word]
    state = {"UPWARD": "Rising", "DOWNWARD": "Falling", "STABLE": "Steady"}[word]
    return f"• Direction: {state} — {verb} on {y1} ({_fmt(n1)} FIRs)."


def _word(pct):
    return "UPWARD" if pct > 5 else "DOWNWARD" if pct < -5 else "STABLE"


def _w_year(rows, kn, params, template_id):
    """T16 — "how many FIRs in 2023?"; year-vs-year when two years are named."""
    years = sorted({int(y) for y in re.findall(r"\b(20[12]\d)\b", str(params.get("_q") or ""))})
    if len(years) >= 2:
        out = _w_compare(years[0], years[-1], kn)
        if out:
            return out
    r0 = rows[0]
    yr, n = int(r0.get("year")), int(r0.get("fir_count") or 0)
    lead = (f"[VERIFIED] {yr} ರಲ್ಲಿ ಕರ್ನಾಟಕದಲ್ಲಿ **{_fmt(n)}** FIR ಗಳು ದಾಖಲಾಗಿವೆ." if kn else
            f"[VERIFIED] Karnataka registered **{_fmt(n)}** FIRs in {yr}.")
    lines = [lead]
    q = str(params.get("_q") or "")
    if re.search(r"cogni[sz]able", q, re.I) or "ಸಂಜ್ಞೇಯ" in q:
        # The official total does not split cognizable from non-cognizable. The registry's
        # rows for the year carry the flag; when the year is only partly held, the SHARE is
        # the figure to read, not the count of rows.
        try:
            from app.services.zcql_local import year_cognizable
            cog, held = year_cognizable(yr)
        except Exception:
            cog, held = 0, 0
        if held:
            pct = round(100 * cog / held)
            partial = held < 0.9 * n
            if kn:
                lines.append(f"• ಸಂಜ್ಞೇಯ: ದಾಖಲೆಯಲ್ಲಿರುವ {yr} ರ FIR ಗಳಲ್ಲಿ **{pct}%** ಸಂಜ್ಞೇಯ ({_fmt(cog)} / {_fmt(held)})."
                             + (" ದಾಖಲೆಯಲ್ಲಿ ಆ ವರ್ಷದ ಒಂದು ಭಾಗ ಮಾತ್ರ ಇದೆ; ಪಾಲನ್ನು ಓದಿ, ಸಾಲುಗಳ ಎಣಿಕೆಯನ್ನಲ್ಲ." if partial else ""))
            else:
                lines.append(f"• Cognizable: **{pct}%** of the {yr} FIRs held in the registry are cognizable "
                             f"({_fmt(cog)} of {_fmt(held)})."
                             + (" The registry holds only part of that year, so read the share, not the row count; "
                                "the official total does not split the two." if partial else ""))
    prev = _yi(yr - 1)
    if _comparable(r0) and _comparable(prev) and prev.get("fir_count"):
        pn = int(prev["fir_count"])
        pct = round(100 * (n - pn) / pn)
        lines.append(_yoy_line(_word(pct), pct, yr - 1, pn, kn))
    cats = _cats(r0.get("top_categories"))
    if cats:
        lines.append(f"{yr} ರ ಪ್ರಮುಖ ಅಪರಾಧ ಗುಂಪುಗಳು:" if kn else f"Top crime groups in {yr}:")
        sample = yr <= 2022        # 2016-2022 rows are a partial extract (about a third of each year)
        for i, (name, c) in enumerate(cats[:5], 1):
            label = _crime_word(name, True) if kn else _crime_en(name)
            lines.append(f"{i}. {label}" + ("" if sample else f" — {_fmt(c)}"))
    note = _year_note(r0, kn)
    if note:
        lines.append(note)
    return lines


def _type_shares(year) -> dict[str, float]:
    params = {"date_from": f"{year}-01-01", "date_to": f"{year}-12-31"}
    rows = _breakdown("T13", params, "crime_type")
    total = _total_like("T13", params)
    if not rows or not total:
        return {}
    return {str(t): 100 * c / total for t, c in rows}


def _w_compare(y1, y2, kn):
    """ "compare 2022 vs 2023" / "fastest-growing crime groups 2022 to 2023"."""
    a, b = _yi(y1), _yi(y2)
    if not a or not b or not a.get("fir_count") or not b.get("fir_count"):
        return None
    na, nb = int(a["fir_count"]), int(b["fir_count"])
    pct = round(100 * (nb - na) / na)
    if kn:
        lead = (f"[VERIFIED] ಕರ್ನಾಟಕದಲ್ಲಿ {y2} ರಲ್ಲಿ **{_fmt(nb)}** FIR, {y1} ರಲ್ಲಿ **{_fmt(na)}** — "
                f"{abs(pct)}% {'ಹೆಚ್ಚು' if pct > 0 else 'ಕಡಿಮೆ'}.")
    else:
        lead = (f"[VERIFIED] Karnataka registered **{_fmt(nb)}** FIRs in {y2} against **{_fmt(na)}** "
                f"in {y1} — {'up' if pct > 0 else 'down'} {abs(pct)}%.")
    lines = [lead, _yoy_line(_word(pct), pct, y1, na, kn)]
    for r in (a, b):
        note = _year_note(r, kn)
        if note:
            lines.append(note)
    sa, sb = _type_shares(y1), _type_shares(y2)
    common = [t for t in sb if t in sa and sa[t] >= 0.5 and sb[t] >= 0.5]
    if common:
        ranked = sorted(common, key=lambda t: sb[t] - sa[t], reverse=True)
        lines.append(f"ವೇಗವಾಗಿ ಬೆಳೆಯುತ್ತಿರುವ ಅಪರಾಧ ಗುಂಪುಗಳು (ಎಲ್ಲಾ FIR ಗಳಲ್ಲಿ ಪಾಲು, {y1} → {y2}):" if kn else
                     f"Fastest-growing crime groups (share of all FIRs, {y1} → {y2}):")
        for i, t in enumerate(ranked[:5], 1):
            label = _crime_word(t, True) if kn else _crime_en(t)
            lines.append(f"{i}. {label} — {sa[t]:.1f}% → {sb[t]:.1f}% "
                         f"({sb[t] - sa[t]:+.1f} {'ಅಂಕ' if kn else 'pts'})")
        if y1 <= 2022:
            lines.append("ಪಾಲು ಹೋಲಿಸಲಾಗಿದೆ: 2016–2022 ರ FIR ಸಾಲುಗಳು ಪ್ರತಿ ವರ್ಷದ ಸುಮಾರು ಮೂರನೇ ಒಂದು ಭಾಗ ಮಾತ್ರ; "
                         "ಮೇಲಿನ ಒಟ್ಟು ಅಂಕಿಅಂಶಗಳು ಅಧಿಕೃತ ವಾರ್ಷಿಕ ಸಂಖ್ಯೆಗಳು." if kn else
                         "Shares are compared because the registry holds only part of each year from 2016 to 2022 "
                         "(about a third); the totals above are the official annual figures.")
    return lines


def _w_count(rows, kn, params, template_id):
    """ "how many theft cases in 2024?" — the number first, then where/what, then the latest FIRs."""
    cts = params.get("crime_types") or []
    zones = params.get("zones") or []
    total = _total_like(template_id, params)
    if total is None:
        return None
    where = ", ".join(zones) if zones else ("ಕರ್ನಾಟಕ" if kn else "Karnataka")
    scope = _scope(params, kn)
    women = _is_women(cts)
    if kn:
        what = ("ಮಹಿಳೆಯರ ವಿರುದ್ಧದ ಅಪರಾಧಗಳು" if women else
                (", ".join(_crime_word(c, True) for c in cts) + " ಪ್ರಕರಣಗಳು") if cts else "FIR ಗಳು") + _absq(params, True)
        lead = f"[VERIFIED] {_in_loc(where, True)} ಒಟ್ಟು **{_fmt(total)}** {what} ದಾಖಲಾಗಿವೆ ({scope})."
    else:
        what = ("crimes against women" if women else
                (" / ".join(_crime_word(c, False) for c in cts) + " cases") if cts else "FIRs") + _absq(params, False) + _statq(params, False)
        lead = f"[VERIFIED] **{_fmt(total)}** {what} are on record {_in_loc(where, False)} ({scope})."
    lines = [lead]
    if not params.get("date_from") and not _absc(params) and not params.get("stations") and not params.get("heads"):
        lines.append(_dir_line(_trend(cts, zones), kn))
    dates = {k: params.get(k) for k in ("date_from", "date_to", "period")}
    for k in ("stations", "heads"):          # the breakdown counts exactly what the total counted
        if params.get(k):
            dates[k] = params[k]
    if _absc(params):
        dates["arrest_status"] = "absconding"   # the breakdown must carry the same filter
    if params.get("stations"):
        br, head, label = [], "", str         # one station: a district breakdown says nothing
    elif not zones:
        br = _breakdown("T11", {"crime_types": cts, "limit": 5, **dates}, "zone")
        head, label = ("ಹೆಚ್ಚು ದಾಖಲಾದ ಜಿಲ್ಲೆಗಳು:" if kn else "Where they were registered:"), str
    elif not cts:
        br = _breakdown("T13", {"zones": zones, **dates}, "crime_type")
        head = "ಪ್ರಮುಖ ಅಪರಾಧ ಪ್ರಕಾರಗಳು:" if kn else "Most common crime types:"
        label = (lambda v: _crime_word(v, True)) if kn else _crime_en
    else:
        br, head, label = [], "", str
    if br:
        lines.append(head)
        for i, (v, c) in enumerate(br[:5], 1):
            p = _pct(c, total)
            lines.append(f"{i}. {label(v)} — {_fmt(c)}" + (f" ({p}%)" if p is not None else ""))
    if rows:
        lines.append("ಇತ್ತೀಚಿನ ಪ್ರಕರಣಗಳು:" if kn else "Latest cases:")
        for i, r in enumerate(rows[:3], 1):
            f = r.get("fir_number") or r.get("crime_id") or "—"
            ct = _crime_word(r.get("crime_type"), True) if kn else _crime_en(r.get("crime_type"))
            lines.append(f"{i}. FIR {f} — {ct}, {r.get('zone') or '—'}, {_date(r.get('occurred_at'))}")
    return lines


def _count_extra(template_id, params, extra):
    """COUNT over the template's filters plus one more (e.g. act LIKE 'IPC%')."""
    try:
        from app.services.zcql_repo import build_spec, Aggregate
        from app.services.zcql_local import run_query
        from app.agents.query_agent import _bound_to_today
        spec = build_spec(template_id, dict(params or {}))
        spec.aggregates = [Aggregate("count", "crime_id", "n")]
        spec.select, spec.group_by, spec.order_by, spec.limit = [], [], None, None
        spec.filters = list(spec.filters) + [extra]
        _bound_to_today(spec)
        r = run_query(spec)
        return int(r[0].get("n") or 0) if r else 0
    except Exception:
        return None


def _law_name(act: str) -> str:
    s = re.split(r"\s+U/s|&&", str(act or ""))[0].strip().rstrip(",")
    s = re.sub(r"\s+", " ", s)
    return s.title().replace("Ipc", "IPC").replace("Ndps", "NDPS") if s else "—"


def _w_acts(rows, kn, params, template_id):
    """T17 — "IPC/BNS vs SLL split for 2023?"."""
    from app.services.zcql_repo import Filter
    total = _total_like(template_id, params)
    ipc = _count_extra(template_id, params, Filter("act", "like", "IPC%"))
    bns_a = _count_extra(template_id, params, Filter("act", "like", "BNS%"))
    bns_b = _count_extra(template_id, params, Filter("act", "like", "BHARATIYA%"))
    if not total or None in (ipc, bns_a, bns_b):
        return None
    bns = bns_a + bns_b
    code = ipc + bns
    sll = max(0, total - code)
    pc, ps = _pct(code, total), _pct(sll, total)
    df, dt = str(params.get("date_from") or ""), str(params.get("date_to") or "")
    yr = df[:4] if (df[:4] and df[:4] == dt[:4] and df[5:10] == "01-01") else None
    if kn:
        when = f"{yr} ರಲ್ಲಿ" if yr else _scope(params, True)
        lead = (f"[COMPUTED] {when} **{pc}%** FIR ಗಳು ({_fmt(code)}) IPC/BNS ಅಡಿಯಲ್ಲಿ ಮತ್ತು "
                f"**{ps}%** ({_fmt(sll)}) ವಿಶೇಷ ಮತ್ತು ಸ್ಥಳೀಯ ಕಾನೂನುಗಳ (SLL) ಅಡಿಯಲ್ಲಿ ದಾಖಲಾಗಿವೆ.")
    else:
        when = f"In {yr}," if yr else f"{_scope(params, False)[:1].upper()}{_scope(params, False)[1:]},"
        lead = (f"[COMPUTED] {when} **{pc}%** of FIRs ({_fmt(code)}) were registered under IPC/BNS and "
                f"**{ps}%** ({_fmt(sll)}) under special & local laws (SLL).")
    lines = [lead,
             f"• IPC/BNS: {_fmt(code)} ({pc}%)"
             + (f" — {_fmt(bns)} {'BNS ಅಡಿಯಲ್ಲಿ' if kn else 'of them under BNS'}" if bns else ""),
             f"• SLL: {_fmt(sll)} ({ps}%)"]
    laws: dict[str, int] = {}
    for r in rows:
        a = str(r.get("act") or "")
        if not a or re.match(r"(?i)\s*(ipc|bns|bharatiya)", a):
            continue
        k = _law_name(a)
        laws[k] = laws.get(k, 0) + int(r.get("n") or 0)
    top = sorted(laws.items(), key=lambda x: -x[1])[:5]
    if top:
        lines.append("ಪ್ರಮುಖ ವಿಶೇಷ ಮತ್ತು ಸ್ಥಳೀಯ ಕಾನೂನುಗಳು:" if kn else "Largest special & local laws:")
        for i, (k, c) in enumerate(top, 1):
            lines.append(f"{i}. {k} — {_fmt(c)} ({_pct(c, total)}%)")
    return lines


# ── Identifier, accused, outcome and beat writers (T18–T23) ───────────────────

_OPEN_STATUS = re.compile(r"investigation|pending|undetected", re.I)
_IDENT_LABEL = {"upi": ("UPI ID", "UPI ID"), "ip": ("IP address", "IP ವಿಳಾಸ"),
                "vehicle": ("vehicle", "ವಾಹನ"), "accused": ("accused ID", "ಆರೋಪಿ ID"),
                "mo": ("modus operandi", "ಕಾರ್ಯವಿಧಾನ (MO)")}
_IDENT_PLURAL = {"upi": ("UPI IDs", "UPI ID ಗಳು"), "ip": ("IP addresses", "IP ವಿಳಾಸಗಳು"),
                 "vehicle": ("vehicles", "ವಾಹನಗಳು"), "accused": ("accused IDs", "ಆರೋಪಿ ID ಗಳು")}
_IDENT_THIS = {"upi": ("this UPI ID", "ಈ UPI ID ಗೆ"), "ip": ("this IP address", "ಈ IP ವಿಳಾಸಕ್ಕೆ"),
               "vehicle": ("this vehicle", "ಈ ವಾಹನಕ್ಕೆ"), "accused": ("this accused ID", "ಈ ಆರೋಪಿಗೆ"),
               "mo": ("this modus operandi", "ಈ ಕಾರ್ಯವಿಧಾನಕ್ಕೆ")}
_IDENT_EXAMPLE = {"vehicle": "KA-02-M-2093", "upi": "name@bank", "ip": "103.87.106.22", "accused": "ACC-KA-500777",
                  "mo": "MO-A1-festival-lockedhouse"}
_IDENT_ORDER = ("upi", "ip", "vehicle", "accused")
_CHALLAN_NOTE = ("• ಗಮನಿಸಿ: ಸಂಚಾರ ದಂಡ (ಚಲನ್) ದಾಖಲೆಗಳು Antar ದತ್ತಾಂಶದಲ್ಲಿಲ್ಲ; FIR ಗಳನ್ನು ಮಾತ್ರ ಪರಿಶೀಲಿಸಲಾಗಿದೆ.",
                 "• Note: traffic challans aren't part of Antar's data; only FIRs were checked.")


def _cap1(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _as_int(v, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _fir_no(r) -> str:
    return str(r.get("CrimeNo") or r.get("fir_number") or r.get("fir_id") or "—")


def _unique_firs(rows):
    """FIRs holds one row per accused; count and list each FIR (fir_id) once.
    CrimeNo is not a key: the same crime number exists at many stations."""
    seen, out = set(), []
    for r in rows:
        k = r.get("fir_id") or (r.get("CrimeNo"), r.get("UnitName"), r.get("date"))
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def _mix(counter, kn: bool, crime: bool = False, top: int = 4) -> str:
    label = (lambda v: _crime_word(v, True) if kn else _crime_en(v)) if crime else str
    return " · ".join(f"{label(k)} ({_fmt(c)})" for k, c in counter.most_common(top))


def _fir_lines(rows, kn: bool, limit: int = 10) -> list[str]:
    out = []
    for i, r in enumerate(rows[:limit], 1):
        ct = _crime_word(r.get("crime_type"), True) if kn else _crime_en(r.get("crime_type"))
        raw = r.get("status") or r.get("FIR_Stage")
        st = f" · {_status(raw, kn)}" if raw else ""
        out.append(f"{i}. FIR {_fir_no(r)} — {ct}, {r.get('zone') or '—'}, "
                   f"{_date(r.get('date') or r.get('occurred_at'))}{st}")
    return out


def _w_ident(rows, kn, params, template_id):
    """T18 (vehicle) and T20 (UPI ID / IP address; vehicle and accused IDs also accepted)."""
    q = str(params.get("_q") or "")
    if template_id == "T18":
        kt, value = "vehicle", rows[0].get("Vehicle_Reg_No") or params.get("plate")
    else:
        from app.services.zcql_repo import resolve_identifier, LOOKUP_COLUMNS
        kt, value = resolve_identifier(params)
        value = rows[0].get(LOOKUP_COLUMNS[kt]) or value
    capped = len(rows) >= 300
    rows = _unique_firs(rows)
    total, r0 = len(rows), rows[0]
    districts = Counter(r.get("district_norm") or r.get("zone") for r in rows
                        if r.get("district_norm") or r.get("zone"))
    nd = len(districts)
    label_en, label_kn = _IDENT_LABEL[kt]
    ct0, place0, d0 = _crime_word(r0.get("crime_type"), kn), r0.get("zone") or "—", _date(r0.get("date"))
    if kn:
        spread = f", **{nd}** ಜಿಲ್ಲೆಗಳಲ್ಲಿ" if nd > 1 else ""
        lead = (f"[VERIFIED] {label_kn} **{value}** **{_fmt(total)}** FIR ಗಳಲ್ಲಿ ದಾಖಲಾಗಿದೆ{spread}; "
                f"ಇತ್ತೀಚಿನದು FIR {_fir_no(r0)} — {ct0}, {place0}, {d0}.")
    else:
        spread = f" across **{nd}** districts" if nd > 1 else ""
        lead = (f"[VERIFIED] {_cap1(label_en)} **{value}** appears in **{_fmt(total)}** "
                f"FIR{'s' if total != 1 else ''}{spread}; the most recent is FIR {_fir_no(r0)} — "
                f"{ct0}, {place0}, {d0}.")
    lines = [lead]
    if capped:
        lines.append("• ದಾಖಲೆಗಳು ಹೆಚ್ಚು; ಇತ್ತೀಚಿನವುಗಳನ್ನು ಮಾತ್ರ ಎಣಿಸಲಾಗಿದೆ." if kn else
                     "• Many records: only the most recent were counted.")
    else:                           # every FIR is in hand, so the open count is exact
        open_n = sum(1 for r in rows if _OPEN_STATUS.search(str(r.get("status") or "")))
        lines.append(f"• ಇನ್ನೂ ತೆರೆದಿರುವವು: {_fmt(total)} ರಲ್ಲಿ {_fmt(open_n)} (ತನಿಖೆ, ವಿಚಾರಣೆ ಬಾಕಿ ಅಥವಾ ಪತ್ತೆಯಾಗಿಲ್ಲ)" if kn else
                     f"• Still open: {_fmt(open_n)} of {_fmt(total)} (under investigation, pending trial or undetected)")
    if nd > 1:
        lines.append(f"• {'ಜಿಲ್ಲೆಗಳು' if kn else 'Districts'}: {_mix(districts, kn, top=6)}")
    crimes = Counter(r.get("crime_type") for r in rows if r.get("crime_type"))
    if crimes:
        lines.append(f"• {'ಅಪರಾಧ ಪ್ರಕಾರಗಳು' if kn else 'Crime types'}: {_mix(crimes, kn, crime=True)}")
    if kt == "vehicle" and (re.search(r"challan", q, re.I) or "ಚಲನ್" in q):
        lines.append(_CHALLAN_NOTE[0 if kn else 1])
    this_en, this_kn = _IDENT_THIS[kt]
    lines.append(f"{this_kn} ಸಂಬಂಧಿಸಿದ FIR ಗಳು:" if kn else
                 (f"FIRs linked to {this_en}:" if total <= 10 else f"Latest 10 FIRs linked to {this_en}:"))
    lines += _fir_lines(rows, kn)
    return lines


def _w_accused(rows, kn, params, template_id):
    """T21 — one accused ID's history: where, what, and how the cases ended."""
    from app.services.zcql_repo import normalize_accused_id
    acc = normalize_accused_id(params.get("accused_id"))
    capped = len(rows) >= 300
    rows = _unique_firs(rows)
    total = len(rows)
    dates = sorted(_date(r.get("date")) for r in rows if r.get("date"))
    districts = Counter(r.get("district_norm") or r.get("zone") for r in rows
                        if r.get("district_norm") or r.get("zone"))
    crimes = Counter(r.get("crime_type") for r in rows if r.get("crime_type"))
    stages = Counter(_status(r.get("FIR_Stage") or r.get("status"), kn) for r in rows)
    arrested = sum(1 for r in rows if _as_int(r.get("Arrested_Count_No_")) > 0)
    charged = sum(1 for r in rows if _as_int(r.get("Accused_ChargeSheeted_Count")) > 0)
    convicted = sum(1 for r in rows if _as_int(r.get("Conviction_Count")) > 0)
    nd = len(districts)
    span = (f"{dates[0]} – {dates[-1]}" if dates and dates[0] != dates[-1] else (dates[0] if dates else "—"))
    if kn:
        lead = (f"[VERIFIED] ಆರೋಪಿ **{acc}** **{_fmt(total)}** FIR ಗಳಲ್ಲಿ ದಾಖಲಾಗಿದ್ದಾರೆ"
                f"{f', **{nd}** ಜಿಲ್ಲೆಗಳಲ್ಲಿ' if nd > 1 else ''} ({span}).")
    else:
        lead = (f"[VERIFIED] Accused **{acc}** appears in **{_fmt(total)}** FIR{'s' if total != 1 else ''}"
                f"{f' across **{nd}** districts' if nd > 1 else ''} ({span}).")
    lines = [lead]
    if capped:
        lines.append("• ದಾಖಲೆಗಳು ಹೆಚ್ಚು; ಇತ್ತೀಚಿನವುಗಳನ್ನು ಮಾತ್ರ ಎಣಿಸಲಾಗಿದೆ." if kn else
                     "• Many records: only the most recent were counted.")
    if districts:
        lines.append(f"• {'ಜಿಲ್ಲೆಗಳು' if kn else ('Districts' if nd > 1 else 'District')}: {_mix(districts, kn, top=6)}")
    if crimes:
        lines.append(f"• {'ಅಪರಾಧ ಪ್ರಕಾರಗಳು' if kn else 'Crime types'}: {_mix(crimes, kn, crime=True)}")
    lines.append(f"• ಫಲಿತಾಂಶ: {arrested} FIR ಗಳಲ್ಲಿ ಬಂಧನ · {charged} ರಲ್ಲಿ ದೋಷಾರೋಪ ಪಟ್ಟಿ · {convicted} ರಲ್ಲಿ ಶಿಕ್ಷೆ" if kn else
                 f"• Outcomes: arrested in {arrested} FIRs · charge-sheeted in {charged} · convicted in {convicted}")
    lines.append(f"• {'ಪ್ರಕರಣ ಹಂತಗಳು' if kn else 'Case stages'}: {_mix(stages, kn)}")
    if nd >= 3:
        lines.append(f"• ಬಹು-ಜಿಲ್ಲಾ ಆರೋಪಿ: {nd} ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಸಕ್ರಿಯ; ಸಂಯೋಜಿತ ಕ್ರಮಕ್ಕೆ ಬಲವಾದ ಸುಳಿವು." if kn else
                     f"• Cross-district offender: active in {nd} districts, a strong lead for coordinated action.")
    lines.append("ಇತ್ತೀಚಿನ FIR ಗಳು:" if kn else "Latest FIRs:")
    lines += _fir_lines(rows, kn)
    return lines


def _w_shared(rows, kn, params, template_id):
    """T19 — identifiers that tie FIRs in several districts together."""
    min_d = max(2, _as_int(params.get("min_districts"), 2))
    limit = max(1, _as_int(params.get("limit"), 10))
    zones = params.get("zones") or []
    cts = params.get("crime_types") or []
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r.get("key_type"), []).append(r)
    types = [t for t in _IDENT_ORDER if t in groups]
    if not types:
        return None
    if kn:
        scope = ((f"{', '.join(zones)} ಗೆ ಸಂಬಂಧಿಸಿದ " if zones else "")
                 + (f"{', '.join(_crime_word(c, True) for c in cts)} FIR ಗಳ " if cts else ""))
    else:
        scope = ((f" touching {', '.join(zones)}" if zones else "")
                 + (f" in {' / '.join(_crime_word(c, False) for c in cts)} FIRs" if cts else ""))

    def line(i, r):
        dl = ", ".join(x.strip() for x in str(r.get("district_list") or "").split(",") if x.strip())
        if kn:
            return (f"{i}. {r['key_value']} — {_fmt(r['firs'])} FIR · {r['districts']} ಜಿಲ್ಲೆಗಳು: {dl}"
                    f" · ಕೊನೆಯದು {_date(r.get('last_date'))}")
        return (f"{i}. {r['key_value']} — {_fmt(r['firs'])} FIRs · {r['districts']} districts: {dl}"
                f" · last seen {_date(r.get('last_date'))}")

    def hint(t, key):
        ask = f"cases for {key}" if t == "accused" else f"FIRs for {key}"
        return f"• ಪ್ರತಿ ಪ್ರಕರಣ ನೋಡಲು “{ask}” ಎಂದು ಕೇಳಿ." if kn else f"• Ask “{ask}” to open every case."

    lines: list[str] = []
    if len(types) == 1:
        t = types[0]
        grp = groups[t]
        top = grp[0]
        total = grp[0].get("type_total") or len(grp)
        pl_en, pl_kn = _IDENT_PLURAL[t]
        if kn:
            lines.append(f"[COMPUTED] {scope}**{_fmt(total)}** {pl_kn} {min_d} ಅಥವಾ ಹೆಚ್ಚು ಜಿಲ್ಲೆಗಳ FIR ಗಳಲ್ಲಿ "
                         f"ಕಾಣಿಸಿಕೊಂಡಿವೆ. ಅತಿ ವ್ಯಾಪಕ: **{top['key_value']}**, **{top['districts']}** ಜಿಲ್ಲೆಗಳ "
                         f"**{_fmt(top['firs'])}** FIR ಗಳಲ್ಲಿ.")
            lines.append(f"ಅತಿ ವ್ಯಾಪಕ {pl_kn}:")
        else:
            lines.append(f"[COMPUTED] **{_fmt(total)}** {pl_en} appear in FIRs from {min_d} or more districts{scope}. "
                         f"The widest spread: **{top['key_value']}**, in **{_fmt(top['firs'])}** FIRs across "
                         f"**{top['districts']}** districts.")
            lines.append(f"Most widespread {pl_en}:")
        lines += [line(i, r) for i, r in enumerate(grp[:limit], 1)]
        lines.append(hint(t, top["key_value"]))
    else:
        parts = " · ".join(f"**{_fmt(groups[t][0].get('type_total') or len(groups[t]))}** "
                           f"{_IDENT_PLURAL[t][1 if kn else 0]}" for t in types)
        lines.append(f"[COMPUTED] {scope}{min_d} ಅಥವಾ ಹೆಚ್ಚು ಜಿಲ್ಲೆಗಳ FIR ಗಳಲ್ಲಿ ಹಂಚಿಕೊಂಡ ಗುರುತುಗಳು: {parts}." if kn else
                     f"[COMPUTED] Identifiers shared by FIRs in {min_d} or more districts{scope}: {parts}.")
        per = max(1, min(3, limit))
        for t in types:
            lines.append(f"{_cap1(_IDENT_PLURAL[t][1 if kn else 0])}:")
            lines += [line(i, r) for i, r in enumerate(groups[t][:per], 1)]
        best = max(rows, key=lambda r: (r.get("districts") or 0, r.get("firs") or 0))
        lines.append(hint(best["key_type"], best["key_value"]))
    lines.append("• ಇವು FIR ಗಳಲ್ಲಿ ದಾಖಲಾದ ಗುರುತುಗಳ ನಿಖರ ಹೊಂದಾಣಿಕೆಗಳು. ಕ್ರಮಕ್ಕೆ ಮುನ್ನ ಪರಿಶೀಲಿಸಿ." if kn else
                 "• These are exact matches on identifiers recorded in FIRs. Verify before acting.")
    return lines


_STAGE_KEYS = ("under_investigation", "pending_trial", "convicted", "disposed", "undetected", "traced", "false_case")
_STAGE_LABEL = {
    "under_investigation": ("Under investigation", "ತನಿಖೆಯಲ್ಲಿ"),
    "pending_trial": ("Pending trial / charge-sheeted", "ವಿಚಾರಣೆ ಬಾಕಿ / ದೋಷಾರೋಪ ಪಟ್ಟಿ"),
    "convicted": ("Convicted", "ಶಿಕ್ಷೆಯಾಗಿದೆ"),
    "disposed": ("Disposed / acquitted / compounded", "ವಿಲೇವಾರಿ / ಖುಲಾಸೆ / ರಾಜಿ"),
    "undetected": ("Undetected", "ಪತ್ತೆಯಾಗಿಲ್ಲ"),
    "traced": ("Traced", "ಪತ್ತೆಯಾಗಿದೆ"),
    "false_case": ("False case", "ಸುಳ್ಳು ಪ್ರಕರಣ"),
}
def _rate(v) -> str:
    return "—" if v is None else f"{v:.0f}%"


# Each outcome rate: (rate field, base field, part field, EN name, KN name).
_METRICS = {
    "conviction": ("conviction_rate", "chargesheeted", "convicted_accused", "conviction rate", "ಶಿಕ್ಷೆ ಪ್ರಮಾಣ"),
    "chargesheet": ("chargesheet_rate", "accused", "chargesheeted", "charge-sheet rate", "ದೋಷಾರೋಪ ಪಟ್ಟಿ ಪ್ರಮಾಣ"),
    "arrest": ("arrest_rate", "accused", "arrested", "arrest rate", "ಬಂಧನ ಪ್ರಮಾಣ"),
    "undetected": ("undetected_share", "firs", "undetected", "undetected share", "ಪತ್ತೆಯಾಗದ ಪ್ರಮಾಣ"),
}
# Rankings skip groups too small for a rate to mean anything.
_MIN_BASE = {"chargesheeted": 100, "accused": 100, "firs": 200}
_BASE_LABEL = {"chargesheeted": ("charge-sheeted accused", "ದೋಷಾರೋಪಿತ ಆರೋಪಿಗಳು"),
               "accused": ("accused", "ಆರೋಪಿಗಳು"), "firs": ("FIRs", "FIR ಗಳು")}


def _outcome_metric(q: str) -> str:
    """The rate the officer asked about; the answer leads with it and ranks by it."""
    low = (q or "").lower()
    kq = re.sub(r"[\u200b-\u200d\ufeff]", "", q or "")      # "ಚಾರ್ಜ್‌ಶೀಟ್" carries a zero-width joiner
    if re.search(r"charge[- ]?sheet|chargesheet", low) or "ದೋಷಾರೋಪ" in kq or "ಚಾರ್ಜ್ಶೀಟ್" in kq \
            or "ಆರೋಪಪಟ್ಟಿ" in kq:
        return "chargesheet"
    if re.search(r"\barrest", low) or "ಬಂಧನ" in (q or ""):
        return "arrest"
    if re.search(r"undetected|detection", low) or "ಪತ್ತೆ" in (q or ""):
        return "undetected"
    return "conviction"


def _metric_parts(m: str, r: dict) -> tuple[int, int]:
    _, base_f, part_f, _, _ = _METRICS[m]
    base = r.get(base_f) or 0
    part = r.get(part_f) or 0
    return (min(part, base) if base else part), base


def _metric_sentence(m: str, r: dict, kn: bool) -> str:
    part, base = _metric_parts(m, r)
    rate = _rate(r.get(_METRICS[m][0]))
    if kn:
        return {
            "conviction": f"ದೋಷಾರೋಪ ಪಟ್ಟಿ ಸಲ್ಲಿಸಿದ ಆರೋಪಿಗಳಲ್ಲಿ **{rate}** ಶಿಕ್ಷೆಗೊಳಗಾಗಿದ್ದಾರೆ: {_fmt(base)} ರಲ್ಲಿ {_fmt(part)}",
            "chargesheet": f"ಆರೋಪಿಗಳಲ್ಲಿ **{rate}** ರವರ ವಿರುದ್ಧ ದೋಷಾರೋಪ ಪಟ್ಟಿ ಸಲ್ಲಿಸಲಾಗಿದೆ: {_fmt(base)} ರಲ್ಲಿ {_fmt(part)}",
            "arrest": f"ಆರೋಪಿಗಳಲ್ಲಿ **{rate}** ಬಂಧಿತರಾಗಿದ್ದಾರೆ: {_fmt(base)} ರಲ್ಲಿ {_fmt(part)}",
            "undetected": f"FIR ಗಳಲ್ಲಿ **{rate}** ಪತ್ತೆಯಾಗಿಲ್ಲ: {_fmt(base)} ರಲ್ಲಿ {_fmt(part)}",
        }[m]
    return {
        "conviction": f"**{rate}** of charge-sheeted accused were convicted: {_fmt(part)} of {_fmt(base)}",
        "chargesheet": f"**{rate}** of accused were charge-sheeted: {_fmt(part)} of {_fmt(base)}",
        "arrest": f"**{rate}** of accused were arrested: {_fmt(part)} of {_fmt(base)}",
        "undetected": f"**{rate}** of FIRs are undetected: {_fmt(part)} of {_fmt(base)}",
    }[m]


def _metric_bullet(m: str, r: dict, kn: bool) -> str:
    part, base = _metric_parts(m, r)
    rate = _rate(r.get(_METRICS[m][0]))
    name = {"conviction": ("Convicted", "ಶಿಕ್ಷೆ"), "chargesheet": ("Charge-sheeted", "ದೋಷಾರೋಪ ಪಟ್ಟಿ"),
            "arrest": ("Arrested", "ಬಂಧನ"), "undetected": ("Undetected", "ಪತ್ತೆಯಾಗಿಲ್ಲ")}[m]
    of = {"conviction": "of charge-sheeted accused", "chargesheet": "of accused",
          "arrest": "of accused", "undetected": "of FIRs"}[m]
    if kn:
        return f"• {name[1]}: {rate} ({_fmt(base)} ರಲ್ಲಿ {_fmt(part)})"
    return f"• {name[0]}: {rate} {of} ({_fmt(part)} of {_fmt(base)})"


def _w_outcomes(rows, kn, params, template_id):
    """T22 — conviction, charge-sheet, arrest and undetected rates. The lead and the ranking
    follow the rate that was asked ("charge sheet rate …" leads with the charge-sheet rate)."""
    from app.services.zcql_repo import _as_outcome_dimension, _as_act_dimension
    dim = _as_act_dimension(params.get("dimension")) if template_id == "T28" else _as_outcome_dimension(params.get("dimension"))
    if template_id == "T28":
        # "IPC 1860 s.00MP" is the missing-person register entry, not a section of a law
        rows = [r for r in rows if "00MP" not in str(r.get("grp") or "").upper() and str(r.get("grp") or "") != "NOT RECORDED"]
        if not rows:
            return None
    metric = _outcome_metric(str(params.get("_q") or ""))
    rate_f, base_f, _, name_en, name_kn = _METRICS[metric]
    floor = _MIN_BASE[base_f]
    base_en, base_kn = _BASE_LABEL[base_f]
    asc = str(params.get("order") or "").lower().startswith("asc")
    limit = max(1, _as_int(params.get("limit"), 10))
    zones = params.get("zones") or []
    cts = params.get("crime_types") or []
    where = ", ".join(zones) if zones else ("ಕರ್ನಾಟಕ" if kn else "Karnataka")
    what_en = (" / ".join(_crime_word(c, False) for c in cts) + " cases") if cts else ""
    what_kn = (", ".join(_crime_word(c, True) for c in cts) + " ಪ್ರಕರಣಗಳಲ್ಲಿ ") if cts else ""
    scope = _scope(params, kn)
    note = ("• ಶಿಕ್ಷೆ ಪ್ರಮಾಣ = ಶಿಕ್ಷೆಗೊಳಗಾದ ಆರೋಪಿಗಳು ÷ ದೋಷಾರೋಪ ಪಟ್ಟಿ ಸಲ್ಲಿಸಿದ ಆರೋಪಿಗಳು; ದೋಷಾರೋಪ ಮತ್ತು ಬಂಧನ ಪ್ರಮಾಣ ಎಲ್ಲಾ ಆರೋಪಿಗಳ ಮೇಲೆ. "
            "ಪ್ರಕರಣ ಹಂತಗಳು FIR ಗಳನ್ನು ಎಣಿಸುತ್ತವೆ." if kn else
            "• Conviction rate = convicted accused ÷ charge-sheeted accused; charge-sheet and arrest rates are "
            "out of all accused. Case stages count FIRs.")

    def label(r):
        g = r.get("grp")
        if dim == "crime_type":
            return _crime_word(g, True) if kn else _crime_en(g)
        return str(g or "—")

    if dim == "none":
        r = rows[0]
        firs = r.get("firs") or 0
        if kn:
            lead = f"[COMPUTED] {_in_loc(where, True)} {what_kn}({scope}) {_metric_sentence(metric, r, True)}."
        else:
            lead = (f"[COMPUTED] In {where}{' for ' + what_en if what_en else ''} ({scope}), "
                    f"{_metric_sentence(metric, r, False)}.")
        lines = [lead] + [_metric_bullet(m, r, kn) for m in _METRICS if m != metric]
        lines.append(f"ಪ್ರಕರಣ ಹಂತಗಳು ({_fmt(firs)} FIR):" if kn else f"Case stages ({_fmt(firs)} FIRs):")
        i = 0
        for k, c in sorted(((k, r.get(k) or 0) for k in _STAGE_KEYS), key=lambda x: -x[1]):
            if c:
                i += 1
                lines.append(f"{i}. {_STAGE_LABEL[k][1 if kn else 0]} — {_fmt(c)} ({_pct(c, firs)}%)")
        if len(zones) != 1:          # the best and worst districts put the number in context
            try:
                from app.agents.query_agent import run_template
                sub = {k: v for k, v in params.items()
                       if k in ("zones", "crime_types", "date_from", "date_to", "period")}
                br, _ = run_template("T22", {**sub, "dimension": "district"})
                ok = [x for x in br if (x.get(base_f) or 0) >= floor and x.get(rate_f) is not None]
                if len(ok) >= 2:
                    hi = max(ok, key=lambda x: x[rate_f])
                    lo = min(ok, key=lambda x: x[rate_f])
                    lines.append(
                        f"• ಅತಿ ಹೆಚ್ಚು {name_kn}: {hi['grp']} {_rate(hi[rate_f])} · ಅತಿ ಕಡಿಮೆ: "
                        f"{lo['grp']} {_rate(lo[rate_f])} ({floor}+ {base_kn} ಇರುವ ಜಿಲ್ಲೆಗಳು)" if kn else
                        f"• Highest {name_en}: {hi['grp']} {_rate(hi[rate_f])} · Lowest: "
                        f"{lo['grp']} {_rate(lo[rate_f])} (districts with {floor}+ {base_en})")
            except Exception:
                pass
        lines.append(note)
        return lines

    ok = [r for r in rows if (r.get(base_f) or 0) >= floor and r.get(rate_f) is not None]
    used_floor = floor if ok else 0
    ok = ok or [r for r in rows if r.get(rate_f) is not None]
    if not ok:
        return None
    ranked = sorted(ok, key=lambda r: r[rate_f], reverse=not asc)
    top = ranked[0]
    tot_part = sum(_metric_parts(metric, r)[0] for r in rows)
    tot_base = sum(_metric_parts(metric, r)[1] for r in rows)
    among_en = {"district": "districts", "act": "Acts", "section": "sections"}.get(dim, "crime types")
    among_kn = {"district": "ಜಿಲ್ಲೆಗಳಲ್ಲಿ", "act": "ಕಾಯ್ದೆಗಳಲ್ಲಿ", "section": "ಸೆಕ್ಷನ್‌ಗಳಲ್ಲಿ"}.get(dim, "ಅಪರಾಧ ಪ್ರಕಾರಗಳಲ್ಲಿ")
    if kn:
        lead = (f"[COMPUTED] {among_kn} {'ಅತಿ ಕಡಿಮೆ' if asc else 'ಅತಿ ಹೆಚ್ಚು'} {name_kn} **{label(top)}** ನಲ್ಲಿ"
                f"{(' (' + ', '.join(zones) + ')') if zones else ''} ({scope}): {_metric_sentence(metric, top, True)}.")
        head = f"{'ಕಡಿಮೆ' if asc else 'ಹೆಚ್ಚು'} {name_kn}{f' ({used_floor}+ {base_kn})' if used_floor else ''}:"
    else:
        lead = (f"[COMPUTED] **{label(top)}** has the {'lowest' if asc else 'highest'} {name_en} among {among_en}"
                f"{' in ' + ', '.join(zones) if zones else ''}{' for ' + what_en if what_en else ''} ({scope}): "
                f"{_metric_sentence(metric, top, False)}.")
        head = (f"{'Lowest' if asc else 'Highest'} {name_en}s"
                f"{f' ({among_en} with {used_floor}+ {base_en})' if used_floor else ''}:")
    lines = [lead]
    if tot_base:
        lines.append(f"• ಒಟ್ಟಾರೆ {name_kn}: {_pct(tot_part, tot_base)}%" if kn else
                     f"• Overall: {_pct(tot_part, tot_base)}% {name_en}")
    lines.append(head)
    for i, r in enumerate(ranked[:limit], 1):
        if kn:
            lines.append(f"{i}. {label(r)} — ಶಿಕ್ಷೆ {_rate(r['conviction_rate'])} · ದೋಷಾರೋಪ {_rate(r.get('chargesheet_rate'))}"
                         f" · ಬಂಧನ {_rate(r.get('arrest_rate'))} · ಪತ್ತೆಯಾಗಿಲ್ಲ {_rate(r.get('undetected_share'))}"
                         f" · {_fmt(r.get('firs'))} FIR")
        else:
            lines.append(f"{i}. {label(r)} — convicted {_rate(r['conviction_rate'])} · charge-sheeted "
                         f"{_rate(r.get('chargesheet_rate'))} · arrested {_rate(r.get('arrest_rate'))} · undetected "
                         f"{_rate(r.get('undetected_share'))} · {_fmt(r.get('firs'))} FIRs")
    lines.append(note)
    return lines


def _w_beats(rows, kn, params, template_id):
    """T23 — beat or village/area hotspots, for patrol planning."""
    area = "Village_Area_Name" in rows[0]
    name_key, ctx_key = ("Village_Area_Name", "district_norm") if area else ("Beat_Name", "UnitName")
    asc = str(params.get("order") or "").lower().startswith("asc")
    zones = params.get("zones") or []
    cts = params.get("crime_types") or []
    total = _total_like(template_id, params)
    where = ", ".join(zones) if zones else ("ಕರ್ನಾಟಕ" if kn else "Karnataka")
    scope = _scope(params, kn)

    def label(r):
        name = str(r.get(name_key) or "—").strip()
        ctx = str(r.get(ctx_key) or "").strip()
        return f"{name} · {ctx}" if ctx and ctx.lower() not in name.lower() else name

    r0 = rows[0]
    n0 = int(r0.get("n") or 0)
    share = _pct(n0, total)
    if kn:
        unit = "ಗ್ರಾಮ/ಪ್ರದೇಶ" if area else "ಬೀಟ್"
        what = (", ".join(_crime_word(c, True) for c in cts) + " ಪ್ರಕರಣಗಳು") if cts else "ಅಪರಾಧ ಪ್ರಕರಣಗಳು"
        share_s = f", ಒಟ್ಟು ಪ್ರಕರಣಗಳ {share}%" if share is not None else ""
        lead = (f"[COMPUTED] {_in_loc(where, True)} {'ಅತಿ ಕಡಿಮೆ' if asc else 'ಅತಿ ಹೆಚ್ಚು'} {what} ಇರುವ {unit} "
                f"**{label(r0)}** — **{_fmt(n0)}** FIR{share_s} ({scope}).")
        head = f"{'ಕಡಿಮೆ ಇರುವ' if asc else 'ಅಗ್ರ'} {len(rows)} {'ಗ್ರಾಮ/ಪ್ರದೇಶಗಳು' if area else 'ಬೀಟ್‌ಗಳು'}:"
    else:
        unit, units = ("area", "areas") if area else ("beat", "beats")
        what = (" / ".join(_crime_word(c, False) for c in cts) + " cases") if cts else "crime"
        share_s = f", {share}% of the total there" if share is not None else ""
        lead = (f"[COMPUTED] **{label(r0)}** is the {'quietest' if asc else 'busiest'} {unit} for {what} in {where} — "
                f"**{_fmt(n0)}** FIRs{share_s} ({scope}).")
        head = f"{'Quietest' if asc else 'Top'} {len(rows)} {units} in {where}:"
    lines = [lead, head]
    for i, r in enumerate(rows, 1):
        c = int(r.get("n") or 0)
        p = _pct(c, total)
        lines.append(f"{i}. {label(r)} — {_fmt(c)}" + (f" ({p}%)" if p is not None else ""))
    if not area:
        lines.append("• ಬೀಟ್ ಸಂಖ್ಯೆಗಳು ಠಾಣೆಗಳ ನಡುವೆ ಪುನರಾವರ್ತನೆಯಾಗುವುದರಿಂದ ಪ್ರತಿ ಬೀಟ್ ಅನ್ನು ಅದರ ಠಾಣೆಯೊಂದಿಗೆ ತೋರಿಸಲಾಗಿದೆ." if kn else
                     "• Each beat is shown with its police station, because beat numbers repeat across stations.")
    if not zones:
        lines.append("• ಗಸ್ತು ಮಟ್ಟದ ವಿವರಕ್ಕೆ ಜಿಲ್ಲೆಯ ಹೆಸರು ಸೇರಿಸಿ, ಉದಾ. “ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಬೀಟ್‌ಗಳು”." if kn else
                     "• Name a district for patrol-level detail, e.g. “top beats for theft in Bengaluru City”.")
    return lines


# ── T24–T28 ──────────────────────────────────────────────────────────────────────

def _days_word(d: int, kn: bool) -> str:
    if d >= 365 and d % 365 == 0:
        y = d // 365
        return (f"{y} ವರ್ಷ" if kn else f"{y} year" + ("s" if y > 1 else ""))
    if d >= 30 and d % 30 == 0:
        m = d // 30
        return (f"{m} ತಿಂಗಳು" if kn else f"{m} month" + ("s" if m > 1 else ""))
    return f"{d} ದಿನ" if kn else f"{d} days"


def _what(cts, heads, kn: bool) -> str:
    """The crime the answer is about, in the officer's words (sub-heading first)."""
    from app.services.zcql_repo import head_label
    if heads:
        return ", ".join(dict.fromkeys(head_label(h) for h in heads[:3])) + (" ಪ್ರಕರಣಗಳು" if kn else " cases")
    if cts:
        return (", ".join(_crime_word(c, True) for c in cts) + " ಪ್ರಕರಣಗಳು") if kn else \
               (" / ".join(_crime_word(c, False) for c in cts) + " cases")
    return "ಪ್ರಕರಣಗಳು" if kn else "cases"


def _w_stages(rows, kn, params, template_id):
    """T24 — where cases sit (under investigation, pending trial …) and how long the open
    investigations have been open."""
    from app.services.zcql_repo import _as_pend_dimension
    dim = _as_pend_dimension(params.get("dimension"))
    q = str(params.get("_q") or "").lower()
    older = _as_int(params.get("older_than_days"), 0)
    trial = bool(re.search(r"trial|charge[- ]?sheet", q)) and not re.search(r"under investigation|pending investigation", q)
    zones = params.get("zones") or []
    where = ", ".join(zones) if zones else ("ಕರ್ನಾಟಕ" if kn else "Karnataka")
    what = _what(params.get("crime_types"), params.get("heads"), kn)
    scope = _scope(params, kn)
    lim = max(1, _as_int(params.get("limit"), 10))
    note = ("• ಹಂತವು FIR ನ ಇಂದಿನ ಹಂತ; ಅವಧಿಯನ್ನು FIR ದಾಖಲಾದ ದಿನದಿಂದ ಎಣಿಸಲಾಗಿದೆ." if kn else
            "• Stage is each FIR's current stage on the register; time open is counted from the date it was registered.")
    if dim == "none":
        r = rows[0]
        firs = r.get("firs") or 0
        ui, pt = r.get("under_investigation") or 0, r.get("pending_trial") or 0
        o90, o365, oo = r.get("ui_over_90") or 0, r.get("ui_over_365") or 0, r.get("ui_older") or 0
        if kn:
            if trial:
                lead = f"[COMPUTED] {_in_loc(where, True)} {what} ({scope}): **{_fmt(pt)}** ವಿಚಾರಣೆ ಬಾಕಿ / ದೋಷಾರೋಪ ಪಟ್ಟಿ ಹಂತದಲ್ಲಿವೆ — {_fmt(firs)} FIR ಗಳಲ್ಲಿ {_pct(pt, firs)}%."
            elif older:
                lead = f"[COMPUTED] {_in_loc(where, True)} {what} ({scope}): **{_fmt(oo)}** {_days_word(older, True)} ಗಿಂತ ಹೆಚ್ಚು ಕಾಲದಿಂದ ತನಿಖೆಯಲ್ಲಿವೆ."
            else:
                lead = f"[COMPUTED] {_in_loc(where, True)} {what} ({scope}): **{_fmt(ui)}** ತನಿಖೆಯಲ್ಲಿವೆ — {_fmt(o365)} ಒಂದು ವರ್ಷಕ್ಕಿಂತ ಹಳೆಯವು."
        else:
            if trial:
                lead = (f"[COMPUTED] **{_fmt(pt)}** {what} in {where} ({scope}) are pending trial or charge-sheeted — "
                        f"{_pct(pt, firs)}% of {_fmt(firs)} FIRs.")
            elif older:
                lead = (f"[COMPUTED] **{_fmt(oo)}** {what} in {where} ({scope}) have been under investigation "
                        f"for more than {_days_word(older, False)}, of {_fmt(ui)} under investigation.")
            else:
                lead = (f"[COMPUTED] **{_fmt(ui)}** {what} in {where} ({scope}) are under investigation — "
                        f"{_fmt(o90)} for more than 90 days and {_fmt(o365)} for more than a year.")
        lines = [lead]
        if r.get("oldest_open") and not trial:
            lines.append(f"• ಅತಿ ಹಳೆಯ ತೆರೆದ ತನಿಖೆ: {_date(r['oldest_open'])} ರಿಂದ" if kn else
                         f"• Oldest open investigation: registered {_date(r['oldest_open'])}")
        lines.append(f"ಪ್ರಕರಣ ಹಂತಗಳು ({_fmt(firs)} FIR):" if kn else f"Case stages ({_fmt(firs)} FIRs):")
        i = 0
        for k, c in sorted(((k, r.get(k) or 0) for k in _STAGE_KEYS), key=lambda x: -x[1]):
            if c:
                i += 1
                lines.append(f"{i}. {_STAGE_LABEL[k][1 if kn else 0]} — {_fmt(c)} ({_pct(c, firs)}%)")
        lines.append(note)
        return lines
    key = "ui_older" if older else ("pending_trial" if trial else "under_investigation")
    asc = str(params.get("order") or "").lower().startswith("asc")
    ranked = sorted([r for r in rows if r.get("grp")], key=lambda r: (r.get(key) or 0), reverse=not asc)
    if not ranked:
        return None

    def label(r):
        g = r.get("grp")
        if dim == "crime_type":
            return _crime_word(g, True) if kn else _crime_en(g)
        if dim == "station" and r.get("district") and len(zones) != 1:
            return f"{g} ({r['district']})"
        return str(g)

    top = ranked[0]
    unit_en = {"station": "police station", "district": "district", "crime_type": "crime type"}[dim]
    unit_kn = {"station": "ಠಾಣೆ", "district": "ಜಿಲ್ಲೆ", "crime_type": "ಅಪರಾಧ ಪ್ರಕಾರ"}[dim]
    state_en = (f"under investigation for more than {_days_word(older, False)}" if older else
                "pending trial or charge-sheeted" if trial else "under investigation")
    state_kn = (f"{_days_word(older, True)} ಗಿಂತ ಹೆಚ್ಚು ಕಾಲದಿಂದ ತನಿಖೆಯಲ್ಲಿ" if older else
                "ವಿಚಾರಣೆ ಬಾಕಿ" if trial else "ತನಿಖೆಯಲ್ಲಿ")
    total = sum((r.get(key) or 0) for r in rows)
    if kn:
        lead = (f"[COMPUTED] {_in_loc(where, True)} {state_kn} ಇರುವ {what} {'ಅತಿ ಕಡಿಮೆ' if asc else 'ಅತಿ ಹೆಚ್ಚು'} "
                f"**{label(top)}** {unit_kn}ಯಲ್ಲಿ — **{_fmt(top.get(key))}** ({scope}).")
        head = f"{'ಕಡಿಮೆ' if asc else 'ಅಗ್ರ'} {min(lim, len(ranked))}:"
    else:
        lead = (f"[COMPUTED] **{label(top)}** has the {'fewest' if asc else 'most'} {what} {state_en} among "
                f"{unit_en}s in {where} — **{_fmt(top.get(key))}**, of {_fmt(total)} ({scope}).")
        head = f"{'Fewest' if asc else 'Most'} {state_en}:"
    lines = [lead, head]
    for i, r in enumerate(ranked[:lim], 1):
        if kn:
            lines.append(f"{i}. {label(r)} — ತನಿಖೆಯಲ್ಲಿ {_fmt(r.get('under_investigation'))}"
                         f" · 1 ವರ್ಷ+ {_fmt(r.get('ui_over_365'))} · ವಿಚಾರಣೆ ಬಾಕಿ {_fmt(r.get('pending_trial'))}"
                         f" · {_fmt(r.get('firs'))} FIR")
        else:
            lines.append(f"{i}. {label(r)} — {_fmt(r.get('under_investigation'))} under investigation"
                         f" ({_fmt(r.get('ui_over_365'))} over a year) · {_fmt(r.get('pending_trial'))} pending trial"
                         f" · {_fmt(r.get('firs'))} FIRs")
    lines.append(note)
    return lines


def _w_heads(rows, kn, params, template_id):
    """T25 — what a crime is made of: its sub-headings, or day against night."""
    from app.services.zcql_repo import head_label
    by_group = "crime_type" in rows[0]
    key = "crime_type" if by_group else "CrimeHead_Name"
    total = _total_like(template_id, params) or sum(int(r.get("n") or 0) for r in rows)
    zones = params.get("zones") or []
    where = ", ".join(zones) if zones else ("ಕರ್ನಾಟಕ" if kn else "Karnataka")
    scope = _scope(params, kn)
    cts = params.get("crime_types") or []
    crime_en = " / ".join(_crime_word(c, False) for c in cts) if cts else "crime"
    crime_kn = ", ".join(_crime_word(c, True) for c in cts) if cts else "ಅಪರಾಧ"
    if by_group:
        night = sum(int(r.get("n") or 0) for r in rows if "NIGHT" in str(r.get(key)).upper())
        day = sum(int(r.get("n") or 0) for r in rows if "DAY" in str(r.get(key)).upper())
        unsplit = total - night - day
        if not (night or day):
            return None
        ratio = (night / day) if day else None
        if kn:
            lead = (f"[COMPUTED] {_in_loc(where, True)} ಕನ್ನಗಳವು **ರಾತ್ರಿ {_fmt(night)}**, ಹಗಲು {_fmt(day)} ದಾಖಲಾಗಿವೆ"
                    + (f" — ರಾತ್ರಿಯಲ್ಲಿ {ratio:.1f} ಪಟ್ಟು" if ratio else "") + f" ({scope}).")
            lines = [lead]
            if unsplit > 0:
                lines.append(f"• {_fmt(unsplit)} FIR ಗಳಲ್ಲಿ ಹಗಲು/ರಾತ್ರಿ ದಾಖಲಾಗಿಲ್ಲ.")
            lines.append("• ಹಗಲು/ರಾತ್ರಿ ವಿಭಾಗವು FIR ದಾಖಲಾದ ಅಪರಾಧ ಶೀರ್ಷಿಕೆಯಿಂದ; ನಿಖರ ಸಮಯ ದಾಖಲೆಯಲ್ಲಿಲ್ಲ.")
            return lines
        lead = (f"[COMPUTED] Burglaries in {where} are registered far more often by night: **{_fmt(night)}** night "
                f"burglaries against **{_fmt(day)}** by day" + (f" — {ratio:.1f} times as many" if ratio else "") + f" ({scope}).")
        lines = [lead]
        if unsplit > 0:
            lines.append(f"• {_fmt(unsplit)} more FIRs are filed as burglary without saying day or night.")
        lines.append("• Day and night come from the head each FIR is registered under (Burglary - Day / - Night); "
                     "the register does not record the hour.")
        return lines
    asked = [h.upper() for h in (params.get("heads") or [])]
    hit = sum(int(r.get("n") or 0) for r in rows if str(r.get(key) or "").strip().upper() in asked)
    named = [r for r in rows if r.get(key)]
    if not named:
        return None
    top = named[0]
    if asked and hit:
        nm = ", ".join(head_label(h) for h in (params.get("heads") or [])[:2])
        lead = (f"[COMPUTED] {_in_loc(where, True)} {crime_kn} ಪ್ರಕರಣಗಳಲ್ಲಿ **{_pct(hit, total)}%** {nm}: "
                f"{_fmt(total)} ರಲ್ಲಿ {_fmt(hit)} ({scope})." if kn else
                f"[COMPUTED] **{_pct(hit, total)}%** of {crime_en.lower()} cases in {where} are {nm}: "
                f"{_fmt(hit)} of {_fmt(total)} ({scope}).")
    else:
        t = int(top.get("n") or 0)
        lead = (f"[COMPUTED] {_in_loc(where, True)} {crime_kn} ಪ್ರಕರಣಗಳಲ್ಲಿ ಅತಿ ದೊಡ್ಡ ಭಾಗ **{head_label(top.get(key))}** — "
                f"{_fmt(t)} ({_pct(t, total)}%) ({scope})." if kn else
                f"[COMPUTED] The largest part of {crime_en.lower()} in {where} is **{head_label(top.get(key))}** — "
                f"**{_fmt(t)}** FIRs, {_pct(t, total)}% of {_fmt(total)} ({scope}).")
    lines = [lead, "ಉಪ-ಶೀರ್ಷಿಕೆವಾರು:" if kn else "By sub-heading on the register:"]
    for i, r in enumerate(named[:10], 1):
        c = int(r.get("n") or 0)
        lines.append(f"{i}. {head_label(r.get(key))} — {_fmt(c)} ({_pct(c, total)}%)")
    return lines


def _w_time(rows, kn, params, template_id):
    """T26 — day-of-week, day-of-month (paydays) or month-of-year pattern, by registration date."""
    weekday = (rows[0].get("dimension") == "weekday")
    rs = [r for r in rows if r.get("slot")]
    if not rs:
        return None
    if rows[0].get("dimension") == "monthday":
        total = sum(r["n"] for r in rs)
        pay = sum(r["n"] for r in rs if int(r.get("slot_index") or 0) <= 5)       # the 1st to the 5th
        mid = sum(r["n"] for r in rs if 6 <= int(r.get("slot_index") or 0) <= 25)
        share = _pct(pay, total)
        even = round(100 * 5 / 30.4)
        rel = round(100 * (pay / 5) / (mid / 20) - 100) if mid else None
        zones = params.get("zones") or []
        where = ", ".join(zones) if zones else ("ಕರ್ನಾಟಕ" if kn else "Karnataka")
        what = _what(params.get("crime_types"), params.get("heads"), kn)
        scope = _scope(params, kn)
        if kn:
            lead = (f"[COMPUTED] {_in_loc(where, True)} {what}: ತಿಂಗಳ 1–5 ದಿನಗಳಲ್ಲಿ **{share}%** ({_fmt(pay)}), "
                    f"ಸಮ ಹಂಚಿಕೆಯಲ್ಲಿ ಸುಮಾರು {even}% ({scope}).")
        else:
            lead = (f"[COMPUTED] **{share}%** of {what} in {where} are registered on the 1st to the 5th of the month "
                    f"(the usual paydays), against about {even}% if they were spread evenly"
                    + (f" — a payday is {abs(rel)}% {'busier' if rel > 0 else 'quieter'} than a mid-month day" if rel else "")
                    + f" ({scope}).")
        top = sorted(rs, key=lambda r: -r["n"])[:3]
        lines = [lead, ("ಹೆಚ್ಚು ದಾಖಲಾದ ದಿನಾಂಕಗಳು: " if kn else "Busiest dates of the month: ")
                 + ", ".join(f"{r['slot']} ({_fmt(r['n'])})" for r in top)]
        lines.append("• FIR ದಾಖಲಾದ ದಿನಾಂಕದ ಪ್ರಕಾರ; ಸಂಬಳ ದಿನವನ್ನು ತಿಂಗಳ 1–5 ಎಂದು ತೆಗೆದುಕೊಳ್ಳಲಾಗಿದೆ." if kn else
                     "• By the date each FIR was registered; paydays are taken as the 1st to the 5th. The register does not record where along a road or ATM a case happened.")
        return lines
    total = sum(r["n"] for r in rs)
    hi = max(rs, key=lambda r: r["n"])
    lo = min(rs, key=lambda r: r["n"])
    zones = params.get("zones") or []
    where = ", ".join(zones) if zones else ("ಕರ್ನಾಟಕ" if kn else "Karnataka")
    what = _what(params.get("crime_types"), params.get("heads"), kn)
    scope = _scope(params, kn)
    gap = round(100 * (hi["n"] - lo["n"]) / hi["n"]) if hi["n"] else 0
    order = sorted(rs, key=lambda r: r.get("slot_index") or 0)
    if weekday:
        even = round(100 / 7)
        lead = (f"[COMPUTED] {_in_loc(where, True)} {what} ಹೆಚ್ಚು ದಾಖಲಾಗುವ ದಿನ **{hi['slot']}** — {_fmt(hi['n'])} "
                f"({_pct(hi['n'], total)}%); ಕಡಿಮೆ {lo['slot']} — {_fmt(lo['n'])}, {gap}% ಕಡಿಮೆ ({scope})." if kn else
                f"[COMPUTED] **{hi['slot']}** is the busiest day for {what} in {where}: **{_fmt(hi['n'])}** FIRs "
                f"({_pct(hi['n'], total)}% of the week, against an even {even}%). The quietest is {lo['slot']} with "
                f"{_fmt(lo['n'])}, {gap}% fewer ({scope}).")
    else:
        lead = (f"[COMPUTED] {_in_loc(where, True)} {what} ಹೆಚ್ಚು ದಾಖಲಾಗುವ ತಿಂಗಳು **{hi['slot']}** — {_fmt(hi['n'])}; "
                f"ಕಡಿಮೆ {lo['slot']} — {_fmt(lo['n'])} ({scope})." if kn else
                f"[COMPUTED] **{hi['slot']}** is the busiest month of the year for {what} in {where}: "
                f"**{_fmt(hi['n'])}** FIRs across the years on record; the quietest is {lo['slot']} with {_fmt(lo['n'])}, "
                f"{gap}% fewer ({scope}).")
    lines = [lead, ("ದಿನವಾರು:" if weekday else "ತಿಂಗಳುವಾರು:") if kn else ("By day of the week:" if weekday else "By month of the year:")]
    for r in order:
        lines.append(f"• {r['slot']} — {_fmt(r['n'])} ({_pct(r['n'], total)}%)")
    lines.append("• FIR ದಾಖಲಾದ ದಿನಾಂಕದ ಪ್ರಕಾರ; ಅಪರಾಧ ನಡೆದ ದಿನ ಅಥವಾ ಸಮಯ ದಾಖಲೆಯಲ್ಲಿಲ್ಲ." if kn else
                 "• By the date each FIR was registered; the register does not hold the day or time of the offence itself.")
    if not weekday:
        lines.append("• ವರ್ಷಗಳ ವ್ಯಾಪ್ತಿ ಸಮಾನವಾಗಿಲ್ಲ (2016–2022 ಭಾಗಶಃ ದಾಖಲೆ), ಆದ್ದರಿಂದ ತಿಂಗಳುಗಳ ಹೋಲಿಕೆ ಸೂಚಕ ಮಾತ್ರ." if kn else
                     "• Years are not covered evenly (2016–2022 are a partial extract), so read the months as a pattern, not exact totals.")
    return lines


def _w_link(rows, kn, params, template_id):
    """T29 — what links two FIRs, key by key."""
    if len(rows) < 2:
        return None
    a, b = rows[0], rows[1]
    missing = [r["fir"] for r in (a, b) if not r.get("found")]
    if missing:
        return [(f"[VERIFIED] FIR {', '.join(missing)} ದಾಖಲೆಯಲ್ಲಿ ಇಲ್ಲ; FIR ಸಂಖ್ಯೆ ಪರಿಶೀಲಿಸಿ." if kn else
                 f"[VERIFIED] FIR {', '.join(missing)} is not on the register, so the two cannot be compared. Check the FIR number.")]
    shared = a.get("shared") or []
    strong = [s for s in shared if s["key"] in ("Accused_ID", "Vehicle_Reg_No", "UPI_ID", "IP_Address", "MO_Details")]
    gap = a.get("days_apart")
    def vals(s):
        return ", ".join(s["values"][:3])
    if kn:
        lead = (f"[VERIFIED] FIR {a['fir']} ಮತ್ತು FIR {b['fir']} ಅನ್ನು ಜೋಡಿಸುವುದು: "
                + "; ".join(f"{s['label']} **{vals(s)}**" for s in strong) + "." if strong else
                f"[VERIFIED] FIR {a['fir']} ಮತ್ತು FIR {b['fir']} ನಡುವೆ ಯಾವುದೇ ಹಂಚಿದ ಆರೋಪಿ, ವಾಹನ, UPI, IP ಅಥವಾ MO ಇಲ್ಲ.")
    else:
        lead = (f"[VERIFIED] FIR {a['fir']} and FIR {b['fir']} are linked by "
                + "; ".join(f"the same {s['label']} **{vals(s)}**" for s in strong) + "." if strong else
                f"[VERIFIED] FIR {a['fir']} and FIR {b['fir']} share no accused, vehicle, UPI ID, IP address or modus operandi.")
    lines = [lead]
    soft = [s for s in shared if s not in strong]
    if soft:
        lines.append(("• ಇನ್ನೂ ಹಂಚಿರುವುದು: " if kn else "• They also share: ")
                     + "; ".join(f"{s['label']} {vals(s)}" for s in soft))
    if gap is not None:
        lines.append(f"• ಎರಡು FIR ಗಳ ನಡುವೆ {gap} ದಿನಗಳು ({a['date']} ಮತ್ತು {b['date']})." if kn else
                     f"• Registered {gap} days apart ({a['date']} and {b['date']}).")
    for r in (a, b):
        k = r["keys"]
        place = ", ".join(k.get("station", [])[:1] + k.get("district_norm", [])[:1])
        crime = _crime_word((k.get("crime_type") or ["—"])[0], kn)
        lines.append(f"• FIR {r['fir']} — {crime}, {place}, {r['date']} · {r.get('stage') or '—'}")
    lines.append("• ಹಂಚಿದ ಕೀ ಪ್ರಕರಣಗಳನ್ನು ಜೋಡಿಸುತ್ತದೆ; ಅದು ಮಾತ್ರ ಒಟ್ಟಿಗೆ ಕೃತ್ಯ ಎಸಗಿದ್ದನ್ನು ತೋರಿಸುವುದಿಲ್ಲ." if kn else
                 "• A shared key links the cases on the register; on its own it does not show the same person acted in both.")
    return lines


def _low_crime(c) -> str:
    """A crime group in running text: lower case, except an Act keeps its name."""
    s = _crime_en(c)
    if re.search(r"\bact\b", s, re.I):
        return re.sub(r"\b(\w)", lambda m: m.group(1).upper(), s.lower()).replace(" Act ", " Act ")
    return s.lower()


def _w_event(rows, kn, params, template_id):
    """T30 — what past years show an event did to registered crime."""
    r = rows[0]
    o = r.get("overall")
    name, where = r.get("name"), r.get("measured_in")
    def pct_word(ef, kn):
        p = abs(ef["percent"])
        return (f"{p}% {'ಹೆಚ್ಚು' if ef['percent'] > 0 else 'ಕಡಿಮೆ'}" if kn else
                f"{p}% {'higher' if ef['percent'] > 0 else 'lower'}")
    ups = (r.get("rises") or []) + (r.get("watch") or [])
    if not o and not ups:
        return [(f"[COMPUTED] {name}: ಅಳೆಯಲು ಹಿಂದಿನ ವರ್ಷಗಳ ದಾಖಲೆ ಸಾಕಷ್ಟಿಲ್ಲ." if kn else
                 f"[COMPUTED] The register holds too few past years of {name} in {where} to measure what it does.")]
    if kn:
        head = (f"[COMPUTED] {name} ಸಮಯದಲ್ಲಿ {where} ನಲ್ಲಿ ಹಿಂದಿನ {o['years']} ವರ್ಷಗಳಲ್ಲಿ ಎಲ್ಲ ಪ್ರಕರಣಗಳು ಸುತ್ತಲಿನ ವಾರಗಳಿಗಿಂತ "
                f"{pct_word(o, True)} ({_fmt(o['seen'])} vs {_fmt(round(o['expected']))})." if o else f"[COMPUTED] {name}:")
        if ups:
            head += " ಏರಿಕೆ: " + ", ".join(f"**{_crime_word(u['crime'], True)}** {pct_word(u, True)}" for u in ups[:3]) + "."
    else:
        head = (f"[COMPUTED] In {o['years']} past years ({o['from_year']}–{o['to_year']}), {where} registered "
                f"{pct_word(o, False)} cases overall during {name} than in the weeks around it "
                f"({_fmt(o['seen'])} against {_fmt(round(o['expected']))} expected)." if o else f"[COMPUTED] {name}:")
        if ups:
            head += " What goes up: " + ", ".join(
                f"**{_low_crime(u['crime'])}** {pct_word(u, False)} (higher in {u['years_higher']} of {u['years']} years"
                + ("" if u in (r.get('rises') or []) else ", less certain") + ")" for u in ups[:3]) + "."
    lines = [head]
    falls = r.get("falls") or []
    if falls:
        lines.append(("• ಇಳಿಕೆ: " if kn else "• What goes down: ")
                     + ", ".join(f"{(_crime_word(f['crime'], True) if kn else _low_crime(f['crime']))} {pct_word(f, kn)}" for f in falls[:3]))
    if r.get("when"):
        lines.append(f"• ಮುಂದಿನದು: {r['when']}" if kn else f"• Next: {r['when']}.")
    if o and o.get("percent", 0) < 0 and not kn:
        lines.append("• Fewer registered cases during an event can mean less crime, or slower reporting and registration while it is on; the record does not say which.")
    lines.append("• ಉತ್ಸವದ ದಿನಾಂಕ ಕ್ಯಾಲೆಂಡರ್‌ನಿಂದ; ಪರಿಣಾಮವನ್ನು ಹಿಂದಿನ FIR ಗಳಿಂದ ಅಳೆಯಲಾಗಿದೆ (ಸುತ್ತಲಿನ 4 ವಾರಗಳೊಂದಿಗೆ ಹೋಲಿಕೆ)." if kn else
                 "• The date comes from the event calendar; the effect is measured from past FIRs against the 4 weeks either side — the same figures as the Predict page.")
    return lines


def _w_sides(rows, kn, params, template_id):
    """T27 — places, stations or years side by side: counts first, outcomes beside them."""
    dim = str(params.get("dimension") or "district")
    rs = [r for r in rows if r.get("grp")]
    if dim == "year":
        rs.sort(key=lambda r: str(r.get("grp")))
    else:                                       # in the order the officer named them
        asked = [str(z).lower() for z in (params.get("stations") if dim == "station" else params.get("zones")) or []]
        pos = lambda g: next((i for i, z in enumerate(asked) if z == g.lower() or z in g.lower() or g.lower() in z), 99)
        rs.sort(key=lambda r: pos(str(r.get("grp"))))
    if not rs:
        return None
    zones_y = params.get("zones") or []
    if dim == "year" and len(rs) >= 2 and not re.search(r"convict|charge[- ]?sheet|chargesheet|arrest|undetected|outcome", str(params.get("_q") or ""), re.I):
        what_y = _what(params.get("crime_types"), params.get("heads"), kn)
        where_y = ", ".join(zones_y) if zones_y else ("ಕರ್ನಾಟಕ" if kn else "Karnataka")
        first, last = rs[0], rs[-1]
        n1, n2 = int(first.get("firs") or 0), int(last.get("firs") or 0)
        ch = round(100 * (n2 - n1) / n1) if n1 else None
        if kn:
            lead = (f"[COMPUTED] {_in_loc(where_y, True)} {what_y}: {first['grp']} ರಲ್ಲಿ **{_fmt(n1)}**, {last['grp']} ರಲ್ಲಿ **{_fmt(n2)}**"
                    + (f" ({abs(ch)}% {'ಹೆಚ್ಚು' if ch > 0 else 'ಕಡಿಮೆ'})" if ch else "") + ".")
        else:
            lead = (f"[COMPUTED] {what_y[:1].upper() + what_y[1:]} in {where_y}: **{_fmt(n1)}** in {first['grp']} against "
                    f"**{_fmt(n2)}** in {last['grp']}" + (f" — {'up' if ch > 0 else 'down'} {abs(ch)}%" if ch else "") + ".")
        rows = rs
        params = {**params, "_lead": lead}
    q = str(params.get("_q") or "")
    outcome = bool(re.search(r"convict|charge[- ]?sheet|chargesheet|arrest|undetected|detection|outcome|solv", q, re.I))
    metric = _outcome_metric(q)
    rate_f = _METRICS[metric][0]
    what = _what(params.get("crime_types"), params.get("heads"), kn)
    scope = _scope(params, kn) if dim != "year" else ""
    a, b = rs[0], rs[1] if len(rs) > 1 else None
    if outcome and b:
        name = _METRICS[metric][4] if kn else _METRICS[metric][3]
        lead = (f"[COMPUTED] {name}: **{a['grp']} {_rate(a.get(rate_f))}** · **{b['grp']} {_rate(b.get(rate_f))}**"
                + ("".join(f" · {r['grp']} {_rate(r.get(rate_f))}" for r in rs[2:5]))
                + (f" ({scope})." if scope else "."))
    elif b:
        na, nb = int(a.get("firs") or 0), int(b.get("firs") or 0)
        diff = (round(100 * (na - nb) / nb) if nb else None)
        if kn:
            lead = (f"[COMPUTED] {what}: **{a['grp']} {_fmt(na)}** · **{b['grp']} {_fmt(nb)}**"
                    + ("".join(f" · {r['grp']} {_fmt(r.get('firs'))}" for r in rs[2:5])) + (f" ({scope})." if scope else "."))
        else:
            rel = (f" — {abs(diff)}% {'more' if diff > 0 else 'fewer'} in {a['grp']}" if diff not in (None, 0) else "")
            lead = (f"[COMPUTED] **{a['grp']}** recorded **{_fmt(na)}** {what} against **{_fmt(nb)}** in **{b['grp']}**{rel}"
                    + (f" ({scope})." if scope else "."))
    else:
        lead = (f"[COMPUTED] {what}: **{a['grp']} {_fmt(a.get('firs'))}** FIR." if kn else
                f"[COMPUTED] Only {a['grp']} has {what} on record for this comparison: **{_fmt(a.get('firs'))}** FIRs.")
    lead = params.get("_lead") or lead
    lines = [lead, "ಪಕ್ಕಪಕ್ಕದಲ್ಲಿ:" if kn else "Side by side:"]
    for r in rs[:8]:
        if kn:
            lines.append(f"• {r['grp']} — {_fmt(r.get('firs'))} FIR · ಶಿಕ್ಷೆ {_rate(r.get('conviction_rate'))} · ದೋಷಾರೋಪ "
                         f"{_rate(r.get('chargesheet_rate'))} · ಬಂಧನ {_rate(r.get('arrest_rate'))} · ಪತ್ತೆಯಾಗಿಲ್ಲ {_rate(r.get('undetected_share'))}")
        else:
            lines.append(f"• {r['grp']} — {_fmt(r.get('firs'))} FIRs · convicted {_rate(r.get('conviction_rate'))} · "
                         f"charge-sheeted {_rate(r.get('chargesheet_rate'))} · arrested {_rate(r.get('arrest_rate'))} · "
                         f"undetected {_rate(r.get('undetected_share'))}")
    if dim == "year":
        ys = [str(r.get("grp")) for r in rs]
        if any(y <= "2022" for y in ys) and any(y >= "2023" for y in ys):
            lines.append("• ಗಮನಿಸಿ: 2016–2022 ದಾಖಲೆ ಪ್ರತಿ ವರ್ಷದ ಸುಮಾರು ಮೂರನೇ ಒಂದು ಭಾಗ ಮಾತ್ರ, ಆದ್ದರಿಂದ ಎಣಿಕೆಗಳನ್ನು ನೇರವಾಗಿ ಹೋಲಿಸಬೇಡಿ; ಪ್ರಮಾಣಗಳನ್ನು ಹೋಲಿಸಿ." if kn else
                         "• Note: the register holds only about a third of each year's FIRs for 2016–2022, so compare the rates, not the raw counts, across that line.")
    if any(str(r.get("grp")) in ("Mysuru-Devaraja", "Mysuru-Nazarbad", "Mangaluru", "Hubballi", "Belagavi") for r in rs):
        lines.append("• ಕೆಲವು ಸಾಲುಗಳು ಪ್ರಾತ್ಯಕ್ಷಿಕೆ ಪ್ರದೇಶಗಳು." if kn else "• Rows named after a locality are demonstration records.")
    lines.append("• ಶಿಕ್ಷೆ ಪ್ರಮಾಣ = ಶಿಕ್ಷೆಗೊಳಗಾದ ÷ ದೋಷಾರೋಪಿತ ಆರೋಪಿಗಳು." if kn else
                 "• Conviction rate = convicted accused ÷ charge-sheeted accused; charge-sheet and arrest rates are out of all accused.")
    return lines


def no_hit_answer(template_id: str, params: dict | None, user_text: str = "", lang: str = "en") -> str | None:
    """Answer for identifier templates that found nothing: "not on record" IS the answer."""
    kn = lang == "kn"
    params = params or {}
    q = user_text or ""
    if template_id in ("T18", "T20"):
        from app.services.zcql_repo import normalize_plate, resolve_identifier
        if template_id == "T18":
            kt, value = "vehicle", normalize_plate(params.get("plate"))
        else:
            kt, value = resolve_identifier(params)
        label_en, label_kn = _IDENT_LABEL[kt]
        challan = kt == "vehicle" and (bool(re.search(r"challan", q, re.I)) or "ಚಲನ್" in q)
        if kn:
            msg = [f"[VERIFIED] {label_kn} **{value}** ಬಗ್ಗೆ ಯಾವುದೇ FIR ದಾಖಲೆಯಲ್ಲಿಲ್ಲ."]
            if challan:
                msg.append(_CHALLAN_NOTE[0])
            msg += ["ಹೀಗೆ ಪ್ರಯತ್ನಿಸಿ:", f"• ಸ್ವರೂಪ ಪರಿಶೀಲಿಸಿ (ಉದಾ. {_IDENT_EXAMPLE[kt]})", "• ವ್ಯಕ್ತಿಯ ಹೆಸರಿನಿಂದ ಹುಡುಕಿ"]
        else:
            msg = [f"[VERIFIED] No FIR on record mentions {label_en} **{value}**."]
            if challan:
                msg.append(_CHALLAN_NOTE[1])
            msg += ["Try:", f"• checking the format (e.g. {_IDENT_EXAMPLE[kt]})", "• searching by the person's name instead"]
        return "\n".join(msg)
    if template_id == "T21":
        from app.services.zcql_repo import normalize_accused_id
        acc = normalize_accused_id(params.get("accused_id"))
        if kn:
            return (f"[VERIFIED] ಆರೋಪಿ **{acc}** ಯಾವುದೇ FIR ನಲ್ಲಿ ದಾಖಲಾಗಿಲ್ಲ.\nಹೀಗೆ ಪ್ರಯತ್ನಿಸಿ:\n"
                    f"• ID ಸ್ವರೂಪ ಪರಿಶೀಲಿಸಿ (ಉದಾ. ACC-KA-500777)\n• ವ್ಯಕ್ತಿಯ ಹೆಸರಿನಿಂದ ಹುಡುಕಿ")
        return (f"[VERIFIED] No FIR on record lists accused **{acc}**.\nTry:\n"
                f"• checking the ID format (e.g. ACC-KA-500777)\n• searching by the person's name instead")
    if template_id == "T19":
        from app.services.zcql_repo import _as_key_type
        kt = _as_key_type(params.get("key_type"))
        min_d = max(2, _as_int(params.get("min_districts"), 2))
        zones = params.get("zones") or []
        cts = params.get("crime_types") or []
        noun_en, noun_kn = _IDENT_PLURAL.get(kt, ("identifiers", "ಗುರುತುಗಳು"))
        if kn:
            return (f"[COMPUTED] {min_d} ಅಥವಾ ಹೆಚ್ಚು ಜಿಲ್ಲೆಗಳ FIR ಗಳಲ್ಲಿ ಕಾಣಿಸಿಕೊಂಡ {noun_kn} ಇಲ್ಲ.\nಹೀಗೆ ಪ್ರಯತ್ನಿಸಿ:\n"
                    f"• ಜಿಲ್ಲೆಗಳ ಸಂಖ್ಯೆ ಕಡಿಮೆ ಮಾಡಿ (2 ಅಥವಾ ಹೆಚ್ಚು)\n• ಅಪರಾಧ ಪ್ರಕಾರ ಅಥವಾ ಸ್ಥಳ ಫಿಲ್ಟರ್ ತೆಗೆದುಹಾಕಿ")
        scope = ((f" touching {', '.join(zones)}" if zones else "")
                 + (f" in {' / '.join(_crime_word(c, False) for c in cts)} FIRs" if cts else ""))
        return (f"[COMPUTED] No {noun_en} appear in FIRs from {min_d} or more districts{scope}.\nTry:\n"
                f"• lowering the district count (2 or more)\n• removing the crime type or place filter")
    return None


_WRITERS = {
    "T18": _w_ident, "T19": _w_shared, "T20": _w_ident, "T21": _w_accused,
    "T22": _w_outcomes, "T23": _w_beats,
    "T11": _w_rank, "T13": _w_types, "T3": _w_trend, "T7": _w_split, "T8": _w_split,
    "T4": _w_top_suspects, "T5": _w_repeat, "T2": _w_suspects, "T9": _w_linked,
    "T1": _w_list, "T12": _w_list, "T16": _w_year, "T17": _w_acts,
    "T24": _w_stages, "T25": _w_heads, "T26": _w_time, "T27": _w_sides, "T28": _w_outcomes,
    "T29": _w_link, "T30": _w_event,
}


def _seeded_window_note(p: dict, template_id: str, kn: bool) -> str | None:
    """Say so when the period asked about lies after the real KSP record.

    The registry carries seeded demonstration rows after the real record ends (10 March
    2024). An answer about 2025 or 2026 read like any other: "Bengaluru City has the most
    theft cases - 598 FIRs". Wholly after the end: the whole answer is demonstration data.
    Across the end (2024): the part after it is. No period named: nothing is said here.
    """
    try:
        from app.services.zcql_repo import _date_range, real_data_today
        if template_id == "T16" and p.get("year"):
            df, dt = f"{int(p['year'])}-01-01", f"{int(p['year'])}-12-31"
        else:
            df, dt = _date_range(p.get("date_from"), p.get("date_to"), p.get("period"))
        if not df:
            return None
        end = real_data_today()
    except Exception:
        return None
    end_s = f"{end.day} {_mon(end.strftime('%Y-%m'), kn)}"
    if df > end.isoformat():
        return (f"• ಗಮನಿಸಿ: ಇವು ಪ್ರಾತ್ಯಕ್ಷಿಕೆ ದಾಖಲೆಗಳು, ನೋಂದಾಯಿತ FIR ಗಳಲ್ಲ — ನೈಜ KSP ದಾಖಲೆ {end_s} ರಂದು ಕೊನೆಗೊಳ್ಳುತ್ತದೆ." if kn else
                f"• Note: these are demonstration records, not registered FIRs. The real KSP record ends on {end_s}.")
    if dt and dt > end.isoformat():
        return (f"• ಗಮನಿಸಿ: {end_s} ರ ನಂತರದ ಸಾಲುಗಳು ಪ್ರಾತ್ಯಕ್ಷಿಕೆ ದಾಖಲೆಗಳು, ನೋಂದಾಯಿತ FIR ಗಳಲ್ಲ." if kn else
                f"• Note: rows after {end_s} are demonstration records, not registered FIRs; the real KSP record ends there.")
    return None


def write_answer(rows: list[dict], template_id: str, lang: str = "en",
                 params: dict | None = None, user_text: str = "") -> str | None:
    """Direct answer for `rows`, or None when this template has no writer."""
    if not rows or not isinstance(rows[0], dict):
        return None
    kn = lang == "kn"
    p = dict(params or {})
    p["_q"] = user_text or ""          # writers that depend on phrasing (compare, forecast)
    lines = None
    if template_id in ("T1", "T12") and _is_count_q(user_text):
        lines = _w_count(rows, kn, p, template_id)
    if not lines:
        fn = _WRITERS.get(template_id)
        if not fn:
            return None
        lines = fn(rows, kn, p, template_id)
    if not lines:
        return None
    # A police station named: the answer is about the station, not the district or the state.
    st = [s_ for s_ in (p.get("stations") or []) if s_]
    if st and lines:
        lines = list(lines)
        label = ", ".join(st[:3])
        zones_s = ", ".join(p.get("zones") or [])
        first = lines[0]
        if zones_s and zones_s in first:
            first = first.replace(zones_s, label, 1)
        elif "Karnataka" in first:
            first = first.replace("Karnataka", label, 1)
        elif "ಕರ್ನಾಟಕ" in first:
            first = first.replace("ಕರ್ನಾಟಕ", label, 1)
        elif " are on record" in first:
            first = first.replace(" are on record", f" are on record in {label}", 1)
        else:
            lines.insert(1, ("• ಪೊಲೀಸ್ ಠಾಣೆ: " if kn else "• Police station: ") + label + ".")
        lines[0] = first
        for i in range(1, min(4, len(lines))):        # list headers ("Top 9 beats in Karnataka:")
            if not zones_s and lines[i].rstrip().endswith(":"):
                lines[i] = lines[i].replace("in Karnataka", f"in {label}").replace("ಕರ್ನಾಟಕ", label)
    # A sub-heading asked ("two-wheeler thefts") narrows the count; say which, unless the
    # writer already named it in its lead.
    hd = [h for h in (p.get("heads") or []) if h]
    if hd and template_id not in ("T24", "T25", "T26", "T27") and lines:
        from app.services.zcql_repo import head_label
        lines = list(lines)
        lines.insert(1, ("• ಉಪ-ಶೀರ್ಷಿಕೆ ಮಾತ್ರ: " if kn else "• Counted under the sub-heading only: ")
                     + ", ".join(dict.fromkeys(head_label(h) for h in hd)) + ".")
    try:
        from app.services.zcql_repo import demo_only_crime_types
        named = p.get("crime_types") or []
        demo = demo_only_crime_types(named)
        # Chain snatching and vehicle theft now also count the real register's sub-headings
        # (Robbery › Chain Snatching, Theft › two-wheelers …), so they are not demo-only.
        from app.services.zcql_repo import HEAD_BACKED
        demo = [c for c in demo if str(c).strip().upper() not in HEAD_BACKED]
        # Only when the WHOLE count is demonstration data. "Crimes against women" carries
        # one seeded spelling (domestic_violence) beside ten real heads; the count is real.
        if len(set(demo)) < len(set(named)):
            demo = []
    except Exception:
        demo = []
    if demo:
        names = ", ".join(_crime_word(c, kn) for c in demo)
        lines = list(lines)
        lines.insert(1, f"• ಗಮನಿಸಿ: ನೈಜ KSP ದಾಖಲೆಯಲ್ಲಿ “{names}” ಎಂಬ ಪ್ರತ್ಯೇಕ ಶೀರ್ಷಿಕೆ ಇಲ್ಲ. ಈ ಎಣಿಕೆ ಪ್ರಾತ್ಯಕ್ಷಿಕೆ ದಾಖಲೆಗಳದ್ದು, ನೋಂದಾಯಿತ FIR ಗಳದ್ದಲ್ಲ." if kn else
                        f"• Note: the real KSP register has no separate head for {names}. These are demonstration records, not registered FIRs; "
                        f"the register files such cases under a broader head such as Theft.")
    if not demo:
        seeded = _seeded_window_note(p, template_id, kn)
        if seeded:
            lines = list(lines)
            lines.insert(1, seeded)
    up = p.get("unknown_place")
    if up and not p.get("unapplied"):          # otherwise it is said in the lead, below
        lines = list(lines)
        lines.insert(1, f"• ಗಮನಿಸಿ: “{up}” ಎಂಬ ಜಿಲ್ಲೆ/ಠಾಣೆ ದಾಖಲೆಯಲ್ಲಿಲ್ಲ — ಕರ್ನಾಟಕದಾದ್ಯಂತದ ಫಲಿತಾಂಶ ತೋರಿಸಲಾಗಿದೆ." if kn else
                        f"• Note: “{up}” isn't a district or police station on record — showing all of Karnataka instead.")
    # What the officer named and the query could not apply goes FIRST, inside the lead
    # sentence: an answer that is broader than the question must say so before it gives a
    # number, not in a trail nobody opens.
    notes = [n for n in (p.get("unapplied") or []) if n]
    if notes and lines:
        lines = list(lines)
        said = ("ಕೇಳಿದ್ದಕ್ಕಿಂತ ವಿಶಾಲವಾದ ಉತ್ತರ: " if kn else "This answers a broader question than you asked: ") \
            + "; ".join(notes) + "."
        tag = re.match(r"^\s*(\[[A-Z ]+\]\s*)?", lines[0])
        lines[0] = f"{tag.group(0)}{said} {lines[0][tag.end():]}"
    return "\n".join(line for line in lines if line)
