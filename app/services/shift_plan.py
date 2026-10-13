"""
Antar - Shift plan
==================
A forecast says where the record points. An officer starting a shift needs the next step:
which beats, which kinds of case, which days, what is still open there, and what is coming.
This puts those on one page for one station.

Everything is counted from the record or taken from the back-tested forecast. Nothing is
worded by a language model; the sentences are fixed templates filled with those counts, so
the page is the same with or without a model. Three limits are stated on the page itself:

  * the forecast is of registered FIRs, not of crime;
  * the register holds the DATE of an FIR, not the hour, so the plan names days of the
    week and never a time of day;
  * it suggests. A deployment is a proposal that a supervising officer approves
    (app/core/hitl.py) - this module has no way to issue one.
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import date, timedelta

from app.forecast import service as S

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MIN_FOR_PATTERN = 60          # FIRs in the year before a weekday pattern is worth stating
STANDS_OUT = 1.25             # a day must run this far above the average day


def _rng(b: dict | None) -> str:
    if not b:
        return ""
    return f"{b['lo']}" if b["lo"] == b["hi"] else f"{b['lo']} to {b['hi']}"


def _title(t: str | None) -> str:
    """The register writes crime heads in capitals."""
    w = str(t or "").replace("_", " ").split()
    act = any(x.lower() == "act" for x in w)
    return " ".join(x.capitalize() if (i == 0 or act) else x.lower() for i, x in enumerate(w))


def weekday_pattern(dates: list[str]) -> dict:
    """Which days of the week FIRs were registered on. A day is named only when the count
    is large enough to mean something and the day clearly stands out; otherwise the plan
    says no day stands out. Registration day, not the day or hour of the offence."""
    counts = Counter()
    for d in dates:
        try:
            counts[date.fromisoformat(str(d)[:10]).weekday()] += 1
        except ValueError:
            continue
    n = sum(counts.values())
    by_day = [{"day": DAYS[i], "firs": counts.get(i, 0)} for i in range(7)]
    if n < MIN_FOR_PATTERN:
        return {"firs": n, "by_day": by_day, "stands_out": [],
                "text": f"Too few FIRs in the past year ({n}) to say which days are busier."}
    mean = n / 7
    top = [x for x in sorted(by_day, key=lambda x: -x["firs"]) if x["firs"] >= STANDS_OUT * mean][:2]
    if not top:
        return {"firs": n, "by_day": by_day, "stands_out": [],
                "text": "No day of the week stands out: registrations are spread evenly."}
    names = " and ".join(x["day"] for x in top)
    share = round(100 * sum(x["firs"] for x in top) / n)
    return {"firs": n, "by_day": by_day, "stands_out": [x["day"] for x in top],
            "text": f"{names} carried {share}% of the past year's {n:,} FIRs here "
                    f"(an even spread would be {round(100 * len(top) / 7)}%)."}


def _station_rows(conn: sqlite3.Connection, station: str, lo: str, hi: str, real_only: bool) -> list[sqlite3.Row]:
    sql = ("SELECT CrimeNo, fir_id, date, CrimeHead_Name, CrimeGroup_Name, Beat_Name, FIR_Stage, "
           "Accused_Count, Accused_ChargeSheeted_Count FROM FIRs "
           "WHERE TRIM(UPPER(station)) = UPPER(TRIM(?)) AND date BETWEEN ? AND ?")
    if real_only:
        sql += " AND is_synthetic_row = 0"
    cur = conn.execute(sql, (station, lo, hi))
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def build(conn: sqlite3.Connection, station: str, as_of: str | None = None) -> dict:
    """The plan for one station. Raises LookupError when the station is not known."""
    try:
        detail = S.unit_detail(conn, station, unit_type="station", as_of=as_of)
    except (S.Refusal, S.NotReady):
        raise                                    # the forecast's own refusals keep their wording
    except Exception as e:                       # an unknown name
        raise LookupError("That station is not in the forecast.") from e
    unit, district = detail["unit"], detail.get("district")
    f7 = (detail.get("forecast") or {}).get("7")
    basis = detail.get("as_of") or {}
    a, info = S._as_of(conn, as_of)

    # 1. where: the station's beats, ranked by the forecast
    beats = []
    try:
        hot = S.hotspots(conn, horizon=7, category="ALL", unit_type="beat", limit=3, station=unit, as_of=as_of)
        for it in hot.get("items") or []:
            if it.get("history") == "thin":
                continue
            beats.append({"name": it["name"], "unit": it["unit"], "expected": it["expected"],
                          "likely": _rng(it.get("band80")), "very_likely": _rng(it.get("band90")),
                          "usual": it.get("usual"),
                          "reason": (it.get("drivers") or [{}])[0].get("text")})
    except Exception:
        beats = []

    # 2. what: the kinds of case the forecast expects most of
    kinds = [{"label": k["label"], "expected": k["expected"], "likely": _rng({"lo": k["lo80"], "hi": k["hi80"]})}
             for k in (detail.get("by_category_7d") or []) if (k.get("expected") or 0) >= 0.3][:4]

    # 3. when, and 4. what is still open: from the past year of this station's FIRs
    end = a.history_end + timedelta(days=6)
    rows = _station_rows(conn, unit, (a.history_end - timedelta(weeks=51)).isoformat(), end.isoformat(),
                         real_only=info.get("series") == "n_real")
    days = weekday_pattern([r["date"] for r in rows])
    open_rows = [r for r in rows if (r.get("Accused_ChargeSheeted_Count") or 0) == 0
                 and str(r.get("FIR_Stage") or "").strip().lower() == "under investigation"]
    open_rows.sort(key=lambda r: str(r["date"]), reverse=True)
    beat_names = {b["unit"].split(" | ", 1)[-1].strip().upper() for b in beats}
    in_beats = [r for r in open_rows if str(r.get("Beat_Name") or "").strip().upper() in beat_names]
    open_cases = {
        "total": len(open_rows), "in_listed_beats": len(in_beats),
        "newest": [{"fir": r["CrimeNo"] or r.get("fir_id"), "date": str(r["date"])[:10], "crime": _title(r.get("CrimeHead_Name") or r.get("CrimeGroup_Name")),
                    "beat": S.display_name(str(r.get("Beat_Name") or "").strip() or "not recorded", "beat"),
                    "accused_named": int(r.get("Accused_Count") or 0)}
                   for r in (in_beats or open_rows)[:5]],
        "definition": "Under investigation with no accused charge-sheeted, registered in the past year.",
    }

    # 5. what is coming: events whose effect the record has measured for this district
    events = []
    try:
        from app.services import events as E
        for ev in E.upcoming(a.as_of):
            d = E.describe(ev)
            if not (d.get("statewide") or district in (d.get("places") or [])):
                continue
            o = d.get("overall") or {}
            line = None
            if o.get("clear") and o.get("percent") is not None:
                line = (f"In {o.get('years')} past years, registered cases here ran {abs(o['percent'])}% "
                        f"{'lower' if o['percent'] < 0 else 'higher'} during it.")
            watch = [(_title(w.get("crime")), w.get("percent")) for w in (d.get("watch") or [])[:2]]
            events.append({"name": d["name"], "when": d.get("when"), "effect": line,
                           "watch": [f"{c} (possibly {p:+d}%)" for c, p in watch if p is not None]})
    except Exception:
        events = []

    plan = {
        "station": detail.get("name") or unit, "unit": unit, "district": district,
        "as_of": basis.get("as_of"), "basis": basis.get("basis"),
        "forecast": ({"expected": f7["expected"], "likely": _rng(f7.get("band80")), "very_likely": _rng(f7.get("band90")),
                      "usual": f7.get("usual"), "summary": f7.get("summary"), "thin": f7.get("history") == "thin"} if f7 else None),
        "beats": beats, "kinds": kinds, "days": days, "open_cases": open_cases, "events": events,
        "accuracy": (detail.get("accuracy") or {}).get("text"),
        "limits": [
            "A forecast of registered FIRs, not of crime. Where more is policed, more is registered.",
            "The register holds the date of an FIR, not the hour. Days are named; times of day are not.",
            "A suggestion. A deployment needs a supervising officer's approval.",
        ],
        "evidence_class": "I",
    }
    plan["text"] = as_text(plan)
    return plan


def as_text(p: dict) -> str:
    """The plan as plain text for a briefing note. Fixed sentences, filled with the counts."""
    out = [f"Shift plan: {p['station']}" + (f", {p['district']}" if p.get("district") else "")]
    f = p.get("forecast")
    if f and not f.get("thin"):
        out.append(f"Next 7 days: likely {f['likely']} FIRs (very likely {f['very_likely']}); a usual week is {f['usual']:g}.")
    elif f:
        out.append("Too little history here for a reliable forecast.")
    if p["beats"]:
        out.append("Beats to cover first: " + "; ".join(
            f"{b['name']} (likely {b['likely']})" for b in p["beats"]) + ".")
    if p["kinds"]:
        out.append("Expected most: " + ", ".join(k["label"] for k in p["kinds"]) + ".")
    out.append("Days: " + p["days"]["text"])
    oc = p["open_cases"]
    if oc["total"]:
        out.append(f"Open: {oc['total']:,} FIRs from the past year are under investigation with no accused charge-sheeted"
                   + (f", {oc['in_listed_beats']} of them in the beats above." if oc["in_listed_beats"] else "."))
    for e in p["events"]:
        out.append(f"{e['name']}: {e['when']}." + (f" {e['effect']}" if e.get("effect") else ""))
    out.append("Decision support only. " + p["limits"][0])
    return "\n".join(out)
