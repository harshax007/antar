"""
Antar - forecast outcomes
=========================
The back-test says how the forecast did on weeks in the past. This says how it is doing in
use: each week's station forecasts are kept, scored when that week's FIRs are in, and the
result is shown on the forecast itself ("last week: forecast 4 to 8, recorded 6").

  snapshot()        keep this week's station forecasts (all crime, next 7 days), once
  scored_weeks()    for each kept week whose target week is complete: how many units'
                    likely ranges held, and forecast against recorded totals
  unit_last()       one station's most recent scored forecast
  trailing()        range coverage over the last scored weeks
  confidence_cap()  the engine's confidence drops when that coverage leaves 70% to 90% -
                    a range that holds far more often than 80% is as wrong as one that
                    holds far less: it is too wide to be useful
  feedback          an officer marks a forecast or a shift plan useful or not, with a reason

Scoring starts with the first week kept after this was installed: forecasts made before
were not stored, and nothing here pretends they were. Until a kept week is complete the
page says there is nothing to score yet.

Kept in the application database. A forecast row holds a station name and counts; feedback
holds the officer id from the token and what they typed.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import date, timedelta

from app.core.db_path import DB_PATH, ensure_db_staged
from app.core.db_path import registry_connect

MIN_WEEKS = 4                 # scored weeks before recent accuracy may change the confidence level
LOW, HIGH = 0.70, 0.90


def _conn() -> sqlite3.Connection:
    ensure_db_staged()
    c = registry_connect(DB_PATH, timeout=10)
    c.execute("""CREATE TABLE IF NOT EXISTS forecast_kept (
        as_of_week TEXT NOT NULL, unit TEXT NOT NULL, expected REAL, lo80 REAL, hi80 REAL, lo90 REAL, hi90 REAL,
        kept_at INTEGER, PRIMARY KEY (as_of_week, unit))""")
    c.execute("""CREATE TABLE IF NOT EXISTS forecast_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL, officer TEXT NOT NULL, kind TEXT NOT NULL,
        unit TEXT NOT NULL, as_of_week TEXT, useful INTEGER NOT NULL, reason TEXT)""")
    return c


def snapshot(as_of_week: str) -> int:
    """Keep the station forecasts for `as_of_week` if they are not kept already."""
    c = _conn()
    try:
        if c.execute("SELECT 1 FROM forecast_kept WHERE as_of_week = ? LIMIT 1", (as_of_week,)).fetchone():
            return 0
        n = c.execute(
            "INSERT OR IGNORE INTO forecast_kept (as_of_week, unit, expected, lo80, hi80, lo90, hi90, kept_at) "
            "SELECT as_of_week, unit, expected, lo80, hi80, lo90, hi90, ? FROM forecast_output "
            "WHERE as_of_week = ? AND unit_type = 'station' AND category = 'ALL' AND horizon = 7",
            (int(time.time()), as_of_week)).rowcount
        c.commit()
        return n
    except sqlite3.OperationalError:
        return 0                     # no forecast store yet
    finally:
        c.close()


def _target(as_of_week: str) -> str:
    return (date.fromisoformat(as_of_week) + timedelta(weeks=1)).isoformat()


def _complete_through(c: sqlite3.Connection) -> str | None:
    """The last complete week of history: the newest week a forecast has been made from."""
    try:
        r = c.execute("SELECT MAX(as_of_week) FROM forecast_output").fetchone()
        return r[0] if r else None
    except sqlite3.OperationalError:
        return None


def _score_week(c: sqlite3.Connection, as_of_week: str) -> dict | None:
    target = _target(as_of_week)
    rows = c.execute(
        "SELECT k.unit, k.expected, k.lo80, k.hi80, k.lo90, k.hi90, COALESCE(a.n, 0) "
        "FROM forecast_kept k LEFT JOIN (SELECT unit, SUM(n) AS n FROM forecast_cube WHERE unit_type = 'station' "
        "AND week_start = ? GROUP BY unit) a ON a.unit = k.unit WHERE k.as_of_week = ?", (target, as_of_week)).fetchall()
    if not rows:
        return None
    in80 = sum(1 for _u, _e, lo8, hi8, _l9, _h9, n in rows if lo8 <= n <= hi8)
    in90 = sum(1 for _u, _e, _l8, _h8, lo9, hi9, n in rows if lo9 <= n <= hi9)
    return {"as_of_week": as_of_week, "target_week": target, "units": len(rows),
            "coverage80": round(in80 / len(rows), 3), "coverage90": round(in90 / len(rows), 3),
            "forecast_total": round(sum(r[1] or 0 for r in rows), 1), "recorded_total": int(sum(r[6] for r in rows))}


def scored_weeks(limit: int = 8) -> list[dict]:
    """Kept weeks whose target week is complete, newest first."""
    c = _conn()
    try:
        through = _complete_through(c)
        if not through:
            return []
        weeks = [r[0] for r in c.execute("SELECT DISTINCT as_of_week FROM forecast_kept ORDER BY 1 DESC")]
        out = []
        for w in weeks:
            if _target(w) > through:          # that week's FIRs are not all in yet
                continue
            s = _score_week(c, w)
            if s:
                out.append(s)
            if len(out) >= limit:
                break
        return out
    except sqlite3.OperationalError:
        return []
    finally:
        c.close()


def unit_last(unit: str) -> dict | None:
    """One station's most recent forecast that can be scored."""
    c = _conn()
    try:
        through = _complete_through(c)
        if not through:
            return None
        for (w,) in c.execute("SELECT as_of_week FROM forecast_kept WHERE unit = ? ORDER BY 1 DESC", (unit,)):
            target = _target(w)
            if target > through:
                continue
            k = c.execute("SELECT expected, lo80, hi80 FROM forecast_kept WHERE as_of_week = ? AND unit = ?", (w, unit)).fetchone()
            n = c.execute("SELECT COALESCE(SUM(n), 0) FROM forecast_cube WHERE unit_type = 'station' AND unit = ? AND week_start = ?",
                          (unit, target)).fetchone()[0]
            lo, hi = int(round(k[1])), int(round(k[2]))
            return {"target_week": target, "likely": f"{lo}" if lo == hi else f"{lo} to {hi}", "recorded": int(n),
                    "held": lo <= n <= hi,
                    "text": f"The week before: forecast {lo if lo == hi else f'{lo} to {hi}'}, recorded {int(n)}."}
        return None
    except sqlite3.OperationalError:
        return None
    finally:
        c.close()


def trailing(n: int = 8) -> dict:
    weeks = scored_weeks(n)
    if not weeks:
        return {"weeks": 0, "coverage80": None, "kept_weeks": kept_weeks()}
    units = sum(w["units"] for w in weeks)
    return {"weeks": len(weeks), "kept_weeks": kept_weeks(),
            "coverage80": round(sum(w["coverage80"] * w["units"] for w in weeks) / units, 3),
            "forecast_total": round(sum(w["forecast_total"] for w in weeks), 1),
            "recorded_total": sum(w["recorded_total"] for w in weeks), "by_week": weeks}


def kept_weeks() -> int:
    c = _conn()
    try:
        return c.execute("SELECT COUNT(DISTINCT as_of_week) FROM forecast_kept").fetchone()[0]
    finally:
        c.close()


def confidence_cap(tr: dict) -> dict | None:
    """What recent use says about the confidence level: a reason, and a level to cap at (or
    None). Silent until MIN_WEEKS weeks have been scored - one bad week is not a trend."""
    if not tr or tr.get("weeks", 0) < MIN_WEEKS or tr.get("coverage80") is None:
        return None
    cov, w = tr["coverage80"], tr["weeks"]
    held = f"In use over the last {w} scored weeks, the likely range held {100 * cov:.0f}% of the time"
    if cov < LOW:
        return {"ok": False, "cap": "Limited" if cov < 0.60 else "Moderate",
                "text": f"{held}, well under the 80% it should. The ranges are too narrow at present."}
    if cov > HIGH:
        return {"ok": False, "cap": "Moderate",
                "text": f"{held}, well over the 80% it should. The ranges are wider than they need to be."}
    return {"ok": True, "cap": None, "text": f"{held}, close to the 80% it should."}


# ── officer feedback ─────────────────────────────────────────────────────────

KINDS = ("forecast", "shift_plan", "lead")


def feedback_add(officer: str, kind: str, unit: str, useful: bool, reason: str = "", as_of_week: str | None = None) -> dict:
    if kind not in KINDS:
        raise ValueError("unknown kind")
    unit = " ".join(str(unit or "").split())[:160]
    if not unit:
        raise ValueError("a unit is required")
    reason = " ".join(str(reason or "").split())[:500]
    if not useful and len(reason) < 3:
        raise ValueError("Say briefly why it was not useful.")
    c = _conn()
    try:
        c.execute("INSERT INTO forecast_feedback (at, officer, kind, unit, as_of_week, useful, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (int(time.time()), str(officer)[:64], kind, unit, as_of_week, 1 if useful else 0, reason))
        c.commit()
        return {"saved": True}
    finally:
        c.close()


def feedback_summary() -> dict:
    c = _conn()
    try:
        rows = c.execute("SELECT kind, SUM(useful), COUNT(*) FROM forecast_feedback GROUP BY kind").fetchall()
        recent = c.execute("SELECT kind, unit, reason, at FROM forecast_feedback WHERE useful = 0 AND reason <> '' "
                           "ORDER BY at DESC LIMIT 5").fetchall()
        return {"by_kind": [{"kind": k, "useful": int(u or 0), "total": int(n)} for k, u, n in rows],
                "recent_not_useful": [{"kind": k, "unit": u, "reason": r} for k, u, r, _a in recent]}
    finally:
        c.close()
