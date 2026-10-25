"""
Antar Insights - what the FIRs behind an answer have in common
==============================================================
Given the FIRs an answer cites (read from its audit log entry, never from the screen),
this reads those FIRs and states what stands out about them: shared accused, vehicles or
payment ids, a repeated method, child victims, arrests that have not happened, cases
stuck in investigation compared with the state, a station or beat that recurs, a day of
the week that recurs.

Rules every insight keeps:
  * Arithmetic over the rows, nothing generated. Each one carries the FIR ids it rests on,
    so an officer can open them and check.
  * Said only when it holds. A pattern needs at least two FIRs and a real share of the
    set; a comparison with the state needs enough cases to compare with.
  * Class K (read straight from the records) or D (calculated from them). Never a finding:
    a shared accused id is a lead to check, not a link that has been proved.
"""
from __future__ import annotations

import sqlite3
import threading
from collections import Counter
from datetime import date

from app.core.db_path import DB_PATH, registry_connect

MAX_FIRS = 50
MAX_ITEMS = 8
MIN_BASELINE = 200            # fewer same-type cases than this: no state comparison

_OPEN = {"UNDER INVESTIGATION", "UNDER_INVESTIGATION", "TRANSFERRED - UNDER INVESTIGATION", "TRACED"}
_BLANK = {"", "NONE", "NULL", "NAN", "0", "-", "NA", "N/A", "UNKNOWN"}
_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_COLS = ("fir_id, district_norm, station, crime_type, CrimeHead_Name, date, FIR_Stage, status, "
         "Accused_Count, Arrested_Count_No_, Accused_ChargeSheeted_Count, Female, Girl, Boy, "
         "Accused_ID, Vehicle_Reg_No, UPI_ID, IP_Address, Beat_Name, MO_Details")

_baseline: dict[str, tuple[int, int]] = {}
_baseline_lock = threading.Lock()


def _int(v) -> int:
    try:
        return max(0, int(float(v or 0)))
    except (TypeError, ValueError):
        return 0


def _val(v) -> str:
    s = " ".join(str(v or "").split())
    return "" if s.upper() in _BLANK else s


def _stage(r) -> str:
    return (_val(r["FIR_Stage"]) or _val(r["status"])).upper()


def _pct(n: int, d: int) -> int:
    return round(100 * n / d) if d else 0


def _of(n: int, d: int) -> str:
    return f"{n} of {d}"


def _plural(n: int, one: str, many: str | None = None) -> str:
    return one if n == 1 else (many or one + "s")


def _nice(iso: str) -> str:
    try:
        return date.fromisoformat(str(iso)[:10]).strftime("%d %b %Y").lstrip("0")
    except ValueError:
        return str(iso or "")


def _open_rate(con: sqlite3.Connection, crime_type: str) -> tuple[int, int]:
    """(open, total) for every FIR of this crime type in the state. Cached: the register
    does not change between two questions, and one type can take a second to count."""
    key = crime_type.strip().upper()
    with _baseline_lock:
        if key in _baseline:
            return _baseline[key]
    rows = con.execute("SELECT UPPER(TRIM(COALESCE(NULLIF(FIR_Stage, ''), status))) AS st, COUNT(*) AS n "
                       "FROM FIRs WHERE TRIM(UPPER(crime_type)) = ? AND date <= ? GROUP BY 1",
                       (key, date.today().isoformat())).fetchall()
    total = sum(n for _, n in rows)
    opened = sum(n for st, n in rows if (st or "") in _OPEN)
    with _baseline_lock:
        _baseline[key] = (opened, total)
    return opened, total


def fir_ids_from_citations(citations) -> list[str]:
    """The register ids an answer cites, in order, without repeats. A citation's `id` is the
    fir_id; `fir` can be a crime number that repeats across stations, so it is the fallback."""
    out: list[str] = []
    for c in citations or []:
        if not isinstance(c, dict):
            continue
        fid = _val(c.get("id")) or _val(c.get("fir"))
        if fid and fid not in out:
            out.append(fid)
    return out[:MAX_FIRS]


def _item(kind: str, title: str, text: str, cls: str, firs: list[str], priority: int) -> dict:
    return {"kind": kind, "title": title, "text": text, "cls": cls, "firs": firs[:20], "priority": priority}


def compute(fir_ids: list[str], con: sqlite3.Connection | None = None) -> dict:
    ids = [i for i in fir_ids if i][:MAX_FIRS]
    if not ids:
        return {"basis": 0, "items": [], "note": "This answer cites no FIRs, so there is nothing to compare."}
    own = con is None
    if own:
        con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        got = con.execute(f"SELECT {_COLS} FROM FIRs WHERE fir_id IN ({','.join('?' * len(ids))})", ids).fetchall()
        first: dict[str, sqlite3.Row] = {}
        for r in got:                         # a fir_id can sit on more than one register row
            first.setdefault(r["fir_id"], r)
        rows = [first[i] for i in ids if i in first]
        n = len(rows)
        if n < 2:
            return {"basis": n, "items": [], "note": "Insights compare FIRs, and this answer cites fewer than two that are on the register."}
        items: list[dict] = []
        every = [r["fir_id"] for r in rows]

        # Shared identifiers: the strongest lead an officer can get from a set of FIRs.
        for col, label in (("Accused_ID", "accused id"), ("Vehicle_Reg_No", "vehicle"),
                           ("UPI_ID", "UPI id"), ("IP_Address", "IP address")):
            seen: dict[str, list[str]] = {}
            for r in rows:
                v = _val(r[col])
                if v:
                    seen.setdefault(v.upper(), []).append(r["fir_id"])
            for v, firs in sorted(seen.items(), key=lambda kv: -len(kv[1])):
                if len(firs) >= 2:
                    items.append(_item("shared", f"Same {label} in {len(firs)} FIRs",
                                       f"{label[0].upper() + label[1:]} {v} appears in {_of(len(firs), n)} FIRs. "
                                       "A lead to check, not a proven link.", "K", firs, 95))
                    break

        # The same method of offence written down more than once.
        mo: dict[str, list[str]] = {}
        for r in rows:
            v = _val(r["MO_Details"])
            if len(v) >= 12:
                mo.setdefault(v.lower(), []).append(r["fir_id"])
        rep = max(mo.values(), key=len, default=[])
        if len(rep) >= 2:
            text = next(_val(r["MO_Details"]) for r in rows if r["fir_id"] == rep[0])
            short = text if len(text) <= 90 else text[:87].rstrip() + "…"
            items.append(_item("method", f"Same method in {len(rep)} FIRs",
                               f"“{short}” is recorded in {_of(len(rep), n)} FIRs.", "K", rep, 85))

        # Child and women victims: decides priority more than anything else in the set.
        kids = [r["fir_id"] for r in rows if _int(r["Girl"]) + _int(r["Boy"]) > 0]
        women = [r["fir_id"] for r in rows if _int(r["Female"]) > 0]
        if kids:
            extra = f" Women are victims in {len(women)}." if women else ""
            items.append(_item("victims", f"Child victims in {len(kids)} {_plural(len(kids), 'FIR')}",
                               f"{_of(len(kids), n)} FIRs record a child victim.{extra}", "K", kids, 100))
        elif len(women) >= 2 or (women and n <= 4):
            items.append(_item("victims", f"Women victims in {len(women)} {_plural(len(women), 'FIR')}",
                               f"{_of(len(women), n)} FIRs record a woman victim.", "K", women, 70))

        # Arrests: named accused who are not yet in custody.
        named = [r for r in rows if _int(r["Accused_Count"]) > 0]
        accused = sum(_int(r["Accused_Count"]) for r in named)
        if accused >= 3 or len(named) >= 2:
            arrested = sum(min(_int(r["Arrested_Count_No_"]), _int(r["Accused_Count"])) for r in named)
            charged = sum(_int(r["Accused_ChargeSheeted_Count"]) for r in named)
            none = [r["fir_id"] for r in named if _int(r["Arrested_Count_No_"]) == 0]
            p = _pct(arrested, accused)
            text = (f"{accused} accused named across {len(named)} {_plural(len(named), 'FIR')}; "
                    f"{arrested} arrested ({p}%)")
            text += f", {charged} charge-sheeted." if charged else "."
            if none:
                text += (f" No arrest yet in {'any of them' if len(none) == len(named) else f'{len(none)} of these {len(named)} FIRs'}.")
            items.append(_item("arrests", f"{p}% of named accused arrested", text, "D",
                               none or [r["fir_id"] for r in named], 80 if p < 50 else 40))

        # Investigation progress, against the state for the same crime types.
        opened = [r["fir_id"] for r in rows if _stage(r) in _OPEN]
        types = Counter(_val(r["crime_type"]).upper() for r in rows if _val(r["crime_type"]))
        expected, compared = 0.0, 0
        for t, k in types.items():
            o, tot = _open_rate(con, t)
            if tot >= MIN_BASELINE:
                expected += k * o / tot
                compared += k
        if compared >= 2 and compared >= n * 0.6:
            exp = expected * n / compared
            state = _pct(expected, compared)
            if len(opened) - exp >= 2 and len(opened) > exp * 1.25:
                items.append(_item("progress", f"{len(opened)} still under investigation",
                                   f"{_of(len(opened), n)} FIRs are still under investigation. For these crime types "
                                   f"about {round(exp)} would be expected ({state}% statewide).", "D", opened, 75))
            elif exp - len(opened) >= 2:
                items.append(_item("progress", f"Moving faster than usual",
                                   f"Only {_of(len(opened), n)} FIRs are still under investigation, against about "
                                   f"{round(exp)} expected for these crime types ({state}% statewide).", "D",
                                   opened or every, 30))
        elif len(opened) >= 2:
            items.append(_item("progress", f"{len(opened)} still under investigation",
                               f"{_of(len(opened), n)} FIRs are still under investigation.", "K", opened, 35))

        # Place: a station, or failing that a district, that holds a real share of the set.
        def top(col):
            c = Counter(_val(r[col]) for r in rows if _val(r[col]))
            return c.most_common(1)[0] if c else ("", 0)
        place_firs: set[str] = set()
        st, k = top("station")
        # "All of them" is worth saying only when the set is big enough for it to mean something.
        many = lambda k: k >= 2 and k / n >= 0.4 and (k < n or n >= 3)   # noqa: E731
        share = lambda k: f"All {n}" if k == n else _of(k, n)             # noqa: E731
        if many(k):
            firs = [r["fir_id"] for r in rows if _val(r["station"]) == st]
            place_firs = set(firs)
            items.append(_item("place", f"{k} at {st}", f"{share(k)} FIRs were registered at {st}.", "D", firs, 60))
        else:
            d, k = top("district_norm")
            if many(k):
                firs = [r["fir_id"] for r in rows if _val(r["district_norm"]) == d]
                items.append(_item("place", f"{k} in {d}", f"{share(k)} FIRs are from {d} district.", "D", firs, 55))
        beat, k = top("Beat_Name")
        if k >= 2 and k / n >= 0.3:
            firs = [r["fir_id"] for r in rows if _val(r["Beat_Name"]) == beat]
            if set(firs) != place_firs:       # the same FIRs as the station adds nothing
                items.append(_item("beat", f"{k} on beat {beat}", f"{_of(k, n)} FIRs fall on the same beat, {beat}.", "D", firs, 58))

        # Time: the span, and a day of the week that recurs.
        dated = []
        for r in rows:
            try:
                dated.append((date.fromisoformat(str(r["date"])[:10]), r["fir_id"]))
            except ValueError:
                pass
        if len(dated) >= 2:
            dated.sort()
            first, last = dated[0][0], dated[-1][0]
            span = (last - first).days
            if len(dated) >= 5 and len({d for d, _ in dated}) >= 3:
                wd = Counter(d.weekday() for d, _ in dated)
                day, k = wd.most_common(1)[0]
                if k >= 3 and k / len(dated) >= 0.4:
                    firs = [f for d, f in dated if d.weekday() == day]
                    items.append(_item("timing", f"{k} on a {_DAYS[day]}",
                                       f"{_of(k, len(dated))} FIRs happened on a {_DAYS[day]} (one day in seven would be "
                                       f"about {round(len(dated) / 7)}).", "D", firs, 50))
            length = (f"{span} {_plural(span, 'day')}" if span <= 60 else
                      f"about {round(span / 30)} months" if span <= 730 else f"about {span / 365:.1f} years")
            when = (f"All {len(dated)} on {_nice(first.isoformat())}." if span == 0 else
                    f"From {_nice(first.isoformat())} to {_nice(last.isoformat())}, {length}.")
            if span and span <= 31 and len(dated) >= 3:
                items.append(_item("timing", f"{len(dated)} within {span} {_plural(span, 'day')}", when, "D",
                                   [f for _, f in dated], 45))
            else:
                items.append(_item("span", "Time span", when, "D", [f for _, f in dated], 10))

        # What kind of crime the set is.
        head = Counter(_val(r["CrimeHead_Name"]) or _val(r["crime_type"]) for r in rows)
        h, k = head.most_common(1)[0] if head else ("", 0)
        if h and k >= 2 and k / n >= 0.5 and k < n:
            firs = [r["fir_id"] for r in rows if (_val(r["CrimeHead_Name"]) or _val(r["crime_type"])) == h]
            items.append(_item("mix", f"Mostly {h}", f"{_of(k, n)} FIRs are recorded as {h}.", "D", firs, 25))

        items.sort(key=lambda x: -x["priority"])
        return {"basis": n, "cited": len(ids), "items": items[:MAX_ITEMS],
                "note": f"Calculated from the {n} FIRs this answer cites. Each insight lists the FIRs it rests on."}
    finally:
        if own:
            con.close()
