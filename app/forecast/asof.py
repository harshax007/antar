"""The date a forecast is "as of", and the weeks it covers.

Decision D1 (2026-09-18): forecasts anchor to the **wall clock** by default. The registry
carries seeded demo rows through 2026, so a wall-clock forecast is built on them; the real
KSP record ends earlier (2024-03-10). Every forecast therefore states its as-of date and
how much of its recent history is real, and the back-test (which needs real outcomes)
always runs on the real record.

    ANTAR_FORECAST_AS_OF = wallclock   (default) today
                         = real        the last day of the real record
                         = YYYY-MM-DD  a fixed date (demos, tests)

Weeks are ISO weeks (Monday start). A forecast uses complete weeks only: the history ends
with the last Sunday on or before the as-of date, and "next 7 days" is the week after it.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from app.core.db_path import registry_connect

ENV = "ANTAR_FORECAST_AS_OF"


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


@dataclass(frozen=True)
class AsOf:
    as_of: date               # the date the officer is told
    mode: str                 # wallclock | real | fixed
    history_end: date         # Monday of the last complete week of history
    real_end: date | None     # last day of the real record

    def target_weeks(self, horizon_days: int) -> list[date]:
        """Week starts forecast for a horizon of 7 or 28 days."""
        n = max(1, horizon_days // 7)
        return [self.history_end + timedelta(weeks=i) for i in range(1, n + 1)]

    def to_dict(self) -> dict:
        return {"as_of": self.as_of.isoformat(), "mode": self.mode,
                "history_through": (self.history_end + timedelta(days=6)).isoformat(),
                "real_record_ends": self.real_end.isoformat() if self.real_end else None}


_real_end_cache: dict[str, date | None] = {}


def real_record_end(conn: sqlite3.Connection) -> date | None:
    key = str(conn.execute("PRAGMA database_list").fetchone()[2])   # '' for :memory:
    if key and key in _real_end_cache:
        return _real_end_cache[key]
    row = conn.execute("SELECT MAX(date) FROM FIRs WHERE is_synthetic_row = 0 "
                       "AND date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'").fetchone()
    end = date.fromisoformat(row[0]) if row and row[0] else None
    if key:
        _real_end_cache[key] = end
    return end


def resolve(conn: sqlite3.Connection, override: str | None = None,
            today: date | None = None) -> AsOf:
    spec = (override or os.getenv(ENV) or "wallclock").strip().lower()
    real_end = real_record_end(conn)
    if spec == "real":
        if real_end is None:
            raise ValueError("the registry has no real records to anchor to")
        d, mode = real_end, "real"
    elif spec in ("wallclock", "today", "now"):
        d, mode = today or date.today(), "wallclock"
    else:
        try:
            d = date.fromisoformat(spec)
        except ValueError as e:
            raise ValueError(f"unrecognised {ENV} value {spec!r}") from e
        mode = "fixed"
    # Sunday closes a week; any other day means that week is still open.
    last_sunday = d - timedelta(days=(d.weekday() + 1) % 7)
    return AsOf(as_of=d, mode=mode, history_end=week_start(last_sunday), real_end=real_end)


_current: dict = {"at": 0.0, "value": None}


def current(ttl_s: float = 60.0) -> AsOf:
    """The configured as-of for the running app — one date for every map layer (the
    forecast, Gi*, the anomaly scan, heat periods), so they never disagree about "today".
    Cached for a minute; the wall clock moves at most one day in that time."""
    import time
    if _current["value"] is None or time.monotonic() - _current["at"] > ttl_s:
        from app.core.db_path import DB_PATH
        con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            _current["value"] = resolve(con)
        finally:
            con.close()
        _current["at"] = time.monotonic()
    return _current["value"]
