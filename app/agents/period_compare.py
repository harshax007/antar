"""
Antar - "is crime rising this week?": one window against the one before it
==========================================================================
"Is crime rising in Bengaluru City this week?", "compare this week with last week",
"how does today compare with yesterday", "this month against last month".

The monthly trend (T3) cannot answer these: it reads whole months, and on the real record.
They used to land on a list of the newest FIRs in the state (the place dropped), or on a
list of last week's FIRs with no comparison in it.

Deterministic and model-free. Both windows are counted with the same validated filters
every list and ranking uses (answer_writer._total_like over T1), so a number here matches
the number the officer gets by asking for either window alone. Windows end on the
register's today (data_today), never past it:

  week   the 7 days to today against the 7 days before   ("this week", "past 7 days")
         "last week with the week before" shifts both back 7 days
  day    today against yesterday, and against the median day of the 28 before
  month  the 30 days to today against the 30 before (only when a month is compared)

A rise or fall under 10%, or on counts too small to read (fewer than 10 in both windows),
is said as "about the same": a difference of 3 against 2 is not a trend.
"""
from __future__ import annotations

import re
import statistics
from datetime import date, timedelta

_UP_DOWN = (r"\b(ris(?:e|es|ing)|going up|go(?:ne)? up|increas\w*|ris(?:en)|more than usual|"
            r"fall(?:s|ing|en)?|going down|go(?:ne)? down|decreas\w*|drop(?:s|ped|ping)?|declin\w*|"
            r"up or down|compar\w*|vs\.?|versus|against|change[sd]?|busier|quieter)\b")
# "is theft rising this month": a direction asked of one month. Not "higher"/"lower", which
# also rank ("districts with lower crime this month" is a ranking).
_DIRECTION = re.compile(r"\b(ris(?:e|es|ing|en)|going up|go(?:ne)? up|increas\w*|fall(?:s|ing|en)?|going down|"
                        r"go(?:ne)? down|decreas\w*|drop(?:s|ped|ping)?|declin\w*|up or down)\b", re.I)
_WEEK = re.compile(r"\b(this week|past week|last 7 days|past 7 days|previous 7 days|week on week|week over week|"
                   r"this week'?s|last week)\b", re.I)
_DAY = re.compile(r"\b(today|yesterday|day before)\b", re.I)
_MONTH_CMP = re.compile(r"\b(this month|past month|last 30 days)\b[^.?!]{0,40}\b(last|previous|prior|the month before)\s+month\b"
                        r"|\bmonth on month\b|\bmonth over month\b", re.I)
_LAST_WEEK_ONLY = re.compile(r"\blast week\b[^.?!]{0,40}\b(week before|previous week|prior week)\b", re.I)


_KN = (("ಈ ವಾರ", " this week "), ("ಕಳೆದ ವಾರ", " last week "), ("ಹಿಂದಿನ ವಾರ", " last week "),
       ("ಈ ತಿಂಗಳ", " this month "), ("ಕಳೆದ ತಿಂಗಳ", " last month "), ("ಇಂದು", " today "), ("ಇವತ್ತು", " today "),
       ("ನಿನ್ನೆ", " yesterday "), ("ಹೆಚ್ಚಾಗ", " rising "), ("ಏರಿಕೆ", " rising "), ("ಇಳಿಕೆ", " falling "),
       ("ಕಡಿಮೆಯಾಗ", " falling "), ("ಹೋಲಿಸ", " compare "), ("ಸಾಮಾನ್ಯಕ್ಕಿಂತ", " than usual "))


def kn_words(text: str) -> str:
    """The Kannada for this week / today / rising / compare, read as the English the rules match."""
    t = text or ""
    for k, e in _KN:
        t = t.replace(k, k + e)
    return t


def wants_compare(text: str) -> str | None:
    """'week' / 'day' / 'month' when the question compares a short window with the one before."""
    t = kn_words(text)
    if not re.search(_UP_DOWN, t, re.I):
        return None
    if _MONTH_CMP.search(t) or (re.search(r"\b(this month|past month|last 30 days)\b", t, re.I) and _DIRECTION.search(t)):
        return "month"
    if _WEEK.search(t):
        return "week"
    if _DAY.search(t) and re.search(r"\b(yesterday|usual|normal|average|typical|compar\w*|vs|versus|against|ris\w*|"
                                    r"increas\w*|fall\w*|drop\w*|higher|lower|busier|quieter)\b", t, re.I):
        return "day"
    return None


def _count(cts, zones, d0: date, d1: date) -> int:
    from app.agents.answer_writer import _total_like
    return _total_like("T1", {"crime_types": cts, "zones": zones,
                              "date_from": d0.isoformat(), "date_to": d1.isoformat()}) or 0


def _by_type(zones, d0: date, d1: date) -> dict[str, int]:
    from app.services.zcql_repo import build_spec
    from app.services.zcql_local import run_query
    try:
        rows = run_query(build_spec("T13", {"zones": zones, "date_from": d0.isoformat(),
                                             "date_to": d1.isoformat(), "limit": 50}))
    except Exception:
        return {}
    out: dict[str, int] = {}
    for r in rows:
        k = str(r.get("crime_type") or "").strip().upper().replace("_", " ")
        if k:
            out[k] = out.get(k, 0) + int(r.get("n") or 0)
    return out


def _nice(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def _span(a: date, b: date) -> str:
    return _nice(a) if a == b else f"{_nice(a)}–{_nice(b)} {b.year}"


def _verdict(now: int, before: int) -> tuple[str, str]:
    if before == 0:
        return ("up", "none in the window before") if now else ("flat", "none in either window")
    pct = round(100 * (now - before) / before)
    if max(now, before) < 10 or abs(pct) < 10:
        return "flat", f"{'+' if pct > 0 else ''}{pct}%"
    return ("up" if pct > 0 else "down"), f"{'+' if pct > 0 else ''}{pct}%"


def answer(text: str, unit: str, ents: dict, lang: str = "en") -> dict:
    from app.services.zcql_repo import data_today
    from app.agents.answer_writer import _crime_word
    today = data_today()
    kn = lang == "kn"
    text = kn_words(text)
    cts, zones = ents.get("crime_types") or [], ents.get("zones") or []
    if unit == "day":
        a0 = a1 = today
        b0 = b1 = today - timedelta(days=1)
        if re.search(r"\byesterday\b", text, re.I) and not re.search(r"\btoday\b", text, re.I):
            a0 = a1 = today - timedelta(days=1)
            b0 = b1 = today - timedelta(days=2)
    elif unit == "month":
        a1, a0 = today, today - timedelta(days=29)
        b1, b0 = a0 - timedelta(days=1), a0 - timedelta(days=30)
    else:
        a1 = today - timedelta(days=7) if _LAST_WEEK_ONLY.search(text) else today
        a0 = a1 - timedelta(days=6)
        b1, b0 = a0 - timedelta(days=1), a0 - timedelta(days=7)
    now, before = _count(cts, zones, a0, a1), _count(cts, zones, b0, b1)
    way, pct = _verdict(now, before)
    what = (" / ".join(_crime_word(c, False) for c in cts) + " cases") if cts else "FIRs"
    where = f" in {', '.join(zones)}" if zones else " in Karnataka"
    word = {"up": "**up**", "down": "**down**", "flat": "**about the same**"}[way]
    if kn:
        word_kn = {"up": "**ಏರಿಕೆ**", "down": "**ಇಳಿಕೆ**", "flat": "**ಸುಮಾರು ಅಷ್ಟೇ**"}[way]
        what_kn = (", ".join(_crime_word(c, True) for c in cts) + " ಪ್ರಕರಣಗಳು") if cts else "FIR ಗಳು"
        where_kn = f"{', '.join(zones)} ನಲ್ಲಿ" if zones else "ಕರ್ನಾಟಕದಲ್ಲಿ"
        lead = (f"[COMPUTED] {where_kn} {what_kn}: {word_kn} — {_span(a0, a1)} ರಲ್ಲಿ **{now:,}**, "
                f"ಹಿಂದಿನ ಅವಧಿ {_span(b0, b1)} ರಲ್ಲಿ **{before:,}** ({pct}).")
    else:
        lead = (f"[COMPUTED] {what[0].upper() + what[1:]}{where} are {word}: **{now:,}** in {_span(a0, a1)} "
                f"against **{before:,}** in {_span(b0, b1)} ({pct}).")
    lines = [lead]
    if unit == "day":
        days = [_count(cts, zones, today - timedelta(days=i), today - timedelta(days=i)) for i in range(1, 29)]
        usual = statistics.median(days) if days else 0
        if usual:
            lines.append(f"- ಹಿಂದಿನ 4 ವಾರಗಳ ಸಾಮಾನ್ಯ ದಿನ: **{usual:g}** (ಮಧ್ಯಮ); {_nice(a1)} ಅದರ **{now / usual:.1f}×**." if kn else
                         f"- A usual day over the 4 weeks before: **{usual:g}** FIRs (median); "
                         f"{_nice(a1)} is **{now / usual:.1f}×** that.")
    if not cts:
        cur, prev = _by_type(zones, a0, a1), _by_type(zones, b0, b1)
        moves = sorted(((k, cur.get(k, 0) - prev.get(k, 0)) for k in set(cur) | set(prev)), key=lambda x: -abs(x[1]))
        ups = [f"{k.title()} ({prev.get(k, 0)} → {cur.get(k, 0)})" for k, d in moves if d > 0][:3]
        downs = [f"{k.title()} ({prev.get(k, 0)} → {cur.get(k, 0)})" for k, d in moves if d < 0][:2]
        if ups:
            lines.append(("- ಹೆಚ್ಚು ಏರಿದವು: " if kn else "- Biggest rises: ") + "; ".join(ups) + ".")
        if downs:
            lines.append(("- ಹೆಚ್ಚು ಇಳಿದವು: " if kn else "- Biggest falls: ") + "; ".join(downs) + ".")
    lines.append("ಇವು ಪ್ರತಿ ಅವಧಿಯಲ್ಲಿ ದಾಖಲಾದ FIR ಗಳು; ಚಿಕ್ಕ ಅವಧಿ ಕೆಲವೇ ಪ್ರಕರಣಗಳಿಂದ ಹೆಚ್ಚು ಬದಲಾಗುತ್ತದೆ." if kn else
                 "Counts are FIRs registered in each window, not incidents; a short window moves a lot "
                 "on a few cases, so read it with the monthly trend.")
    params = {"crime_types": cts, "zones": zones, "unit": unit, "date_from": a0.isoformat(), "date_to": a1.isoformat(),
              "prev_from": b0.isoformat(), "prev_to": b1.isoformat(), "now": now, "before": before}
    fups = []
    if zones:
        fups.append(f"Top police stations in {zones[0]} this week")
    fups.append(f"{'Theft' if not cts else cts[0].title()} trend in {zones[0] if zones else 'Karnataka'}")
    return {"answer": "\n".join(lines), "rows": [{"window": "current", "from": a0.isoformat(), "to": a1.isoformat(), "n": now},
                                                 {"window": "previous", "from": b0.isoformat(), "to": b1.isoformat(), "n": before}],
            "citations": [], "template_id": "COMPARE", "params": params, "agent": "query",
            "suggested_followups": fups, "llm_answer": False,
            "reasoning": [{"step": "compare", "detail": f"{unit}: {now} FIRs {a0}..{a1} vs {before} {b0}..{b1}, "
                                                         f"same filters as a list (T1 count)."}]}
