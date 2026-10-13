"""
Antar - Event calendar and measured event effects
=================================================
What the forecast knows about the calendar, and what the record says each event does.

Two sources, kept apart:

  the calendar   WHEN an event falls. Festival dates move every year, so the upcoming
                 ones are read from a public holiday calendar on the internet
                 (ANTAR_EVENT_FEED_URL) and checked once a day. A built-in table of the
                 same festivals is the fallback when the feed cannot be reached, and it
                 supplies the years the feed does not carry. Only the DATE of a festival
                 on a fixed allow-list is taken from the feed - no text from it is ever
                 shown or stored.

  the record     WHAT an event does. Nothing here is assumed. For every past occurrence
                 inside the real FIR record, the cases registered in the event's window
                 are compared with the 28 days either side of it, per district and per
                 crime group. "Dasara raises theft by a third" used to be typed into this
                 file as a constant; measured over eight Dasaras, Mysuru registers FEWER
                 FIRs in that window and more fatal road accidents. The measurement is
                 what the officer is shown, with the counts behind it.

No future calendar date leaves this module (app/core/date_guard.py): an upcoming event
is described by how many days away it is, never by its date.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta

FEED_URL_DEFAULT = ("https://calendar.google.com/calendar/ical/"
                    "en.indian%23holiday%40group.v.calendar.google.com/public/basic.ics")
FEED_NAME = "Public holiday calendar for India (Google Calendar)"
FEED_MAX_AGE_S = 24 * 3600
FEED_TIMEOUT_S = 6.0
_FEED_FILE = os.path.join(tempfile.gettempdir(), "antar_event_feed.json")

BASELINE_DAYS = 28          # days compared on each side of an event's window
MIN_YEARS = 4               # occurrences needed before an effect is reported at all
MIN_EXPECTED = 10.0         # cases the baseline must predict for the window, summed
CLEAR_Z = 2.0               # how far from "no change" counts as a clear effect


@dataclass(frozen=True)
class Event:
    key: str
    name: str
    what: str                         # why it matters to a station, in a line
    feed: tuple[str, ...]             # the feed's own names for it
    before: int                       # window: days before the anchor date ...
    after: int                        # ... and after it
    places: tuple[str, ...] = ()      # districts where it centres; () = statewide
    area: str = "Karnataka"           # what those districts are called, taken together
    fixed: tuple[int, int] | None = None      # (month, day) when the date never moves
    dates: tuple[str, ...] = ()       # known anchor dates, ISO


# Anchor dates: the main day of each festival. The window around it is where a station
# feels it (Navaratri runs the nine days before Vijayadashami; Ganesha immersions run
# for ten days after the festival).
EVENTS: dict[str, Event] = {e.key: e for e in (
    Event("dasara", "Mysuru Dasara", "State festival: processions, crowds and tourist traffic, centred on Mysuru.",
          ("Dussehra",), 9, 0, ("Mysuru City", "Mysuru Dist", "Mysuru-Devaraja", "Mysuru-Nazarbad"), "Mysuru city and district",
          dates=("2016-10-11", "2017-09-30", "2018-10-19", "2019-10-08", "2020-10-25", "2021-10-15",
                 "2022-10-05", "2023-10-24", "2024-10-12", "2025-10-02", "2026-10-20", "2027-10-09")),
    Event("deepavali", "Deepavali", "Shopping rush, cash movement and fireworks across the state.",
          ("Diwali/Deepavali",), 1, 2,
          dates=("2016-10-30", "2017-10-19", "2018-11-07", "2019-10-27", "2020-11-14", "2021-11-04",
                 "2022-10-24", "2023-11-12", "2024-10-31", "2025-10-20", "2026-11-08", "2027-10-29")),
    Event("ganesha", "Ganesha Chaturthi", "Pandals and night immersion processions for about ten days.",
          ("Ganesh Chaturthi", "Vinayaka Chathurthi"), 0, 10,
          dates=("2016-09-05", "2017-08-25", "2018-09-13", "2019-09-02", "2020-08-22", "2021-09-10",
                 "2022-08-31", "2023-09-19", "2024-09-07", "2025-08-27", "2026-09-14", "2027-09-04")),
    Event("ugadi", "Ugadi", "Kannada new year: temple crowds and market rush.",
          ("Ugadi",), 1, 1,
          dates=("2016-04-08", "2017-03-29", "2018-03-18", "2019-04-06", "2020-03-25", "2021-04-13",
                 "2022-04-02", "2023-03-22", "2024-04-09", "2025-03-30", "2026-03-19", "2027-04-07")),
    Event("sankranti", "Makara Sankranti", "Harvest festival: fairs, cattle processions and travel.",
          ("Makar Sankranti",), 1, 1,
          dates=("2016-01-15", "2017-01-14", "2018-01-14", "2019-01-15", "2020-01-15", "2021-01-14",
                 "2022-01-14", "2023-01-15", "2024-01-15", "2025-01-14", "2026-01-14", "2027-01-15")),
    Event("ramzan", "Ramzan (Eid al-Fitr)", "Evening markets in the days before, congregational prayers on the day.",
          ("Ramzan Id", "Ramzan Id (tentative)"), 2, 1,
          dates=("2016-07-07", "2017-06-26", "2018-06-16", "2019-06-05", "2020-05-25", "2021-05-14",
                 "2022-05-03", "2023-04-22", "2024-04-11", "2025-03-31", "2026-03-21", "2027-03-10")),
    Event("newyear", "New Year's Eve", "Late-night gatherings and drink-driving, centred on Bengaluru.",
          ("New Year's Day",), 1, 0, ("Bengaluru City",), "Bengaluru City", fixed=(1, 1)),
)}


# ── the calendar: built-in dates, overlaid by the internet feed ──────────────────

_lock = threading.Lock()
_feed: dict | None = None          # {"fetched_at": epoch, "url": str, "dates": {key: [iso, ...]}}


def _feed_url() -> str:
    try:
        from app.core.settings import settings
        return str(getattr(settings, "ANTAR_EVENT_FEED_URL", FEED_URL_DEFAULT) or "").strip()
    except Exception:
        return FEED_URL_DEFAULT


def _parse_ics(text: str) -> dict[str, list[str]]:
    """Dates of the allow-listed festivals in an iCalendar file. Everything else in the
    file - and every character of its text - is discarded."""
    wanted = {name.lower(): e.key for e in EVENTS.values() for name in e.feed}
    out: dict[str, set[str]] = {}
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text.replace("\r\n ", "").replace("\r\n", "\n"), flags=re.S):
        d = re.search(r"^DTSTART(?:;VALUE=DATE)?:(\d{4})(\d{2})(\d{2})", block, flags=re.M)
        s = re.search(r"^SUMMARY:(.*)$", block, flags=re.M)
        if not d or not s:
            continue
        key = wanted.get(s.group(1).strip().lower())
        if not key:
            continue
        try:
            day = date(int(d.group(1)), int(d.group(2)), int(d.group(3)))
        except ValueError:
            continue
        out.setdefault(key, set()).add(day.isoformat())
    return {k: sorted(v) for k, v in out.items()}


def _load_feed_file() -> dict | None:
    try:
        with open(_FEED_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data.get("dates"), dict) else None
    except Exception:
        return None


def refresh_feed(force: bool = False) -> dict | None:
    """Read the public calendar if the copy held is older than a day. Never raises: an
    unreachable feed leaves the last good copy (or the built-in table) in place."""
    global _feed
    url = _feed_url()
    if not url:
        return None
    with _lock:
        if _feed is None:
            _feed = _load_feed_file()
        fresh = _feed and _feed.get("url") == url and time.time() - _feed.get("fetched_at", 0) < FEED_MAX_AGE_S
        if fresh and not force:
            return _feed
        try:
            import httpx
            from app.core import egress
            egress.check(url, "event_calendar")
            # no redirects: the allow-list is about where the request goes, and a redirect
            # is the feed choosing somewhere else
            r = httpx.get(url, timeout=FEED_TIMEOUT_S, follow_redirects=False)
            r.raise_for_status()
            dates = _parse_ics(r.text)
            if not dates:
                raise ValueError("no known festival in the feed")
            _feed = {"fetched_at": time.time(), "url": url, "dates": dates}
            try:
                with open(_FEED_FILE, "w", encoding="utf-8") as fh:
                    json.dump(_feed, fh)
            except OSError:
                pass
        except Exception as e:          # offline, blocked, changed format: keep what we have
            import structlog
            structlog.get_logger(__name__).warning("event_feed_unavailable", error=f"{type(e).__name__}: {e}")
            if _feed is not None:
                _feed = {**_feed, "last_error_at": time.time()}
        return _feed


def feed_status() -> dict:
    """Where the calendar came from, for the officer: the internet feed or the built-in
    table, and when the feed was last read."""
    url = _feed_url()
    f = _feed if _feed is not None else _load_feed_file()
    if not url:
        return {"source": "built-in", "name": "Built-in festival calendar", "checked_at": None,
                "stale": False, "note": "The internet calendar is switched off."}
    if not f:
        return {"source": "built-in", "name": "Built-in festival calendar", "checked_at": None,
                "stale": True, "note": "The internet calendar could not be reached; built-in dates are in use."}
    age = time.time() - f.get("fetched_at", 0)
    return {"source": "internet", "name": FEED_NAME,
            "checked_at": datetime.fromtimestamp(f["fetched_at"]).isoformat(timespec="minutes"),
            "stale": age > 2 * FEED_MAX_AGE_S,
            "note": ("Read from the internet and checked daily." if age <= 2 * FEED_MAX_AGE_S
                     else "The internet calendar has not answered recently; the last copy is in use.")}


def occurrences(key: str) -> list[date]:
    """Every known anchor date of an event, the feed's dates replacing the built-in ones
    for the years it carries."""
    e = EVENTS[key]
    if e.fixed:
        this = date.today().year
        return [date(y, *e.fixed) for y in range(2016, this + 3)]
    by_year = {int(d[:4]): date.fromisoformat(d) for d in e.dates}
    for d in ((_feed or {}).get("dates") or {}).get(key, []):
        dd = date.fromisoformat(d)
        by_year[dd.year] = dd
    return [by_year[y] for y in sorted(by_year)]


def _window(e: Event, anchor: date) -> tuple[date, date]:
    return anchor - timedelta(days=e.before), anchor + timedelta(days=e.after)


def _days(n: int) -> str:
    return "1 day" if n == 1 else f"{n} days"


def upcoming(as_of: date, horizon_days: int = 21) -> list[dict]:
    """Events under way on `as_of` or starting within the horizon. Relative timing only."""
    out = []
    feed_dates = (_feed or {}).get("dates") or {}
    for e in EVENTS.values():
        for anchor in occurrences(e.key):
            start, end = _window(e, anchor)
            if end < as_of or start > as_of + timedelta(days=horizon_days):
                continue
            starts_in, ends_in, peak_in = (start - as_of).days, (end - as_of).days, (anchor - as_of).days
            if starts_in <= 0:
                phase = "under way"
                when = ("Under way, ends today" if ends_in == 0 else f"Under way, {_days(ends_in)} left")
                if peak_in > 0:
                    when += f"; main day in {_days(peak_in)}"
            else:
                phase, when = "upcoming", f"Starts in {_days(starts_in)}"
            from_feed = not e.fixed and anchor.isoformat() in feed_dates.get(e.key, [])
            out.append({
                "key": e.key, "name": e.name, "what": e.what, "phase": phase, "when": when,
                "starts_in_days": max(0, starts_in), "ends_in_days": ends_in,
                "window_days": e.before + e.after + 1,
                "places": list(e.places), "statewide": not e.places, "measured_in": e.area,
                # in the next 7 days? that is the window the forecast speaks about
                "in_forecast_window": starts_in <= 7,
                "date_source": "internet" if from_feed else ("fixed date" if e.fixed else "built-in"),
            })
    out.sort(key=lambda x: (x["starts_in_days"], x["ends_in_days"]))
    return out


# ── the record: what each event has done, measured ───────────────────────────────

_effects: dict[str, dict] = {}          # key -> {"years": [...], "cells": {(zone, group): [win, base]}, ...}
_effects_lock = threading.Lock()


def _db() -> sqlite3.Connection:
    from app.core.db_path import DB_PATH, ensure_db_staged
    ensure_db_staged()
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def _real_end(conn: sqlite3.Connection) -> date | None:
    try:
        from app.forecast.asof import real_record_end
        return real_record_end(conn)
    except Exception:
        return None


def _measure(key: str) -> dict:
    """Window and baseline counts for one event, over every occurrence that lies wholly
    inside the real record. Counted once per process: the real record does not change."""
    with _effects_lock:
        if key in _effects:
            return _effects[key]
        e = EVENTS[key]
        conn = _db()
        try:
            real_end = _real_end(conn)
            first = conn.execute("SELECT MIN(date) FROM FIRs").fetchone()[0]
            first_day = date.fromisoformat(str(first)[:10]) if first else None
            # (zone, crime group) -> {year: (cases in the window, cases in the baseline days)}
            cells: dict[tuple[str, str], dict[int, tuple[int, int]]] = {}
            years: list[int] = []
            width = e.before + e.after + 1
            q = ("SELECT District_Name, UPPER(TRIM(CrimeGroup_Name)), "
                 "SUM(CASE WHEN date >= ? AND date <= ? THEN 1 ELSE 0 END), COUNT(*) "
                 "FROM FIRs WHERE date >= ? AND date <= ? GROUP BY 1, 2")
            for anchor in occurrences(key):
                start, end = _window(e, anchor)
                lo, hi = start - timedelta(days=BASELINE_DAYS), end + timedelta(days=BASELINE_DAYS)
                if not real_end or not first_day or hi > real_end or lo < first_day:
                    continue
                years.append(anchor.year)
                tot: dict[tuple[str, str], list[int]] = {}
                for zone, group, win, n in conn.execute(q, (start.isoformat(), end.isoformat(), lo.isoformat(), hi.isoformat())):
                    for k in ((zone, group), (zone, "*"), ("*", group), ("*", "*")):
                        t = tot.setdefault(k, [0, 0])
                        t[0] += win or 0
                        t[1] += n - (win or 0)
                for k, (w, bse) in tot.items():
                    cells.setdefault(k, {})[anchor.year] = (w, bse)
            _effects[key] = {"years": years, "cells": cells, "scale": width / (2 * BASELINE_DAYS)}
        finally:
            conn.close()
        return _effects[key]


def _norm_group(crime_group: str | None) -> str:
    return (crime_group or "").replace("_", " ").strip().upper() or "*"


def effect(key: str, zone: str | tuple | list | None = None, crime_group: str | None = None,
           strict: bool = False) -> dict | None:
    """What the record shows this event does to one district (or several taken together)
    and one crime group (None = all crime).

    Returns None when the record cannot say: too few past occurrences, or too few cases
    for the comparison to mean anything. `clear` is true only when the change is larger
    than week-to-week noise would produce AND it went the same way in most of the years -
    an unclear effect is context, never a basis for moving a forecast. `strict` raises the
    bar, for when many crime groups are scanned at once and some will stand out by chance.
    """
    m = _measure(key)
    if len(m["years"]) < MIN_YEARS:
        return None
    zones = [zone] if isinstance(zone, str) else list(zone or ["*"])
    group = _norm_group(crime_group)
    by_year: dict[int, list[int]] = {}
    for z in zones:
        for y, (w, bse) in (m["cells"].get((z, group)) or {}).items():
            t = by_year.setdefault(y, [0, 0])
            t[0] += w
            t[1] += bse
    seen = sum(w for w, _ in by_year.values())
    expected = sum(bse for _, bse in by_year.values()) * m["scale"]
    if expected < (20.0 if strict else MIN_EXPECTED):
        return None
    ratio = seen / expected
    pct = round((ratio - 1) * 100)
    # the baseline is itself a count (scaled), so its noise is added to the window's
    z_score = (seen - expected) / ((expected * (1 + m["scale"])) ** 0.5)
    n = len(m["years"])
    higher = sum(1 for w, bse in by_year.values() if w > bse * m["scale"])
    same_way = (higher if pct > 0 else n - higher) / n
    clear = abs(z_score) >= (2.5 if strict else CLEAR_Z) and abs(pct) >= 10 and same_way >= (0.7 if strict else 0.6)
    return {
        "ratio": round(ratio, 2), "percent": pct, "seen": int(seen), "expected": round(expected, 1),
        "years": n, "from_year": m["years"][0], "to_year": m["years"][-1],
        "years_higher": higher, "clear": clear,
        "direction": "higher" if pct > 0 else "lower" if pct < 0 else "same",
    }


def movers(key: str, zone: str | tuple | list | None = None, limit: int = 3) -> dict:
    """The crime groups the record shows clearly rising and clearly falling in the event's
    window, for a district, several taken together, or the whole state."""
    m = _measure(key)
    zones = {zone} if isinstance(zone, str) else set(zone or ["*"])
    groups = {g for (zz, g) in m["cells"] if zz in zones and g != "*"}
    rises, falls = [], []
    for g in groups:
        ef = effect(key, zone, g, strict=True)
        if ef and ef["clear"]:
            (rises if ef["percent"] > 0 else falls).append({"crime": g, **ef})
    rises.sort(key=lambda x: -x["percent"])
    falls.sort(key=lambda x: x["percent"])
    # Second tier: a rise that passes the ordinary test but not the strict one. It is
    # reported as "less certain" and never moves a forecast - one of many groups scanned
    # will look like this by chance.
    sure = {r["crime"] for r in rises}
    watch = []
    for g in groups - sure:
        ef = effect(key, zone, g)
        if ef and ef["clear"] and ef["percent"] >= 20:
            watch.append({"crime": g, **ef})
    watch.sort(key=lambda x: -x["seen"])
    return {"rises": rises[:limit], "falls": falls[:limit], "watch": watch[:2]}


def describe(ev: dict) -> dict:
    """An upcoming event with what the record shows for it: where it centres when it has a
    centre (the Mysuru districts for Dasara), the whole state otherwise."""
    key = ev["key"]
    e = EVENTS[key]
    place = tuple(e.places) or None
    return {**ev, "overall": effect(key, place), **movers(key, place),
            "occurrences_measured": len(_measure(key)["years"])}


# ── compatibility: the alerts feed asks which events touch a date and zone ───────

def get_events_for_date(target_date_str: str | None = None, zone: str | None = None) -> list[dict]:
    """Events under way or starting within a week of a date, optionally for one zone.

    Kept for app/api/alerts.py and alert_suggest_agent. `risk_types` is now the crime
    groups the record shows clearly rising in the event's window (it used to be a typed
    list), so an alert is only tied to an event the record supports.
    """
    try:
        dt = date.fromisoformat(str(target_date_str)[:10]) if target_date_str else date.today()
    except ValueError:
        dt = date.today()
    out = []
    for ev in upcoming(dt, horizon_days=7):
        if zone and ev["places"] and zone not in ev["places"]:
            continue
        try:
            rises = [r["crime"].lower() for r in movers(ev["key"], tuple(ev["places"]) or None)["rises"]]
        except Exception:
            rises = []
        out.append({"name": ev["name"], "zones": ev["places"] or ["All"], "risk_types": rises, "when": ev["when"]})
    return out
