"""
One-off data fix — shift future-dated seed rows back by exactly one year.
=========================================================================
WHY
  The seed generator emitted 359 rows dated after today (max 2026-12-28). Because
  chat queries are recency-ordered, those rows dominated what officers actually saw:
  72% of the newest 500 rows, and 38 of the 39 rows in the flagship
  "chain snatching in Rajajinagar" slice. Answers cited a December-2026 crime as a
  CURRENT case — a credibility hole in a police tool.

  Owner decision (2026-07-21): fix the DATA, not just filter it. The runtime filter
  (query_agent.drop_future_rows) stays in place as a permanent safety net; after this
  migration it should filter ~0 rows.

HOW
  Shift every future row back by a FIXED NUMBER OF DAYS (`SHIFT_DAYS`) so the whole
  block 2026-07-22..2026-12-28 compresses into the days just BEFORE today, preserving
  chronological order within the block.

  Why days, not "-1 year": the anomaly scan detects spikes in a 13-week TRAILING window
  anchored at max(date). The WOW-3 Rajajinagar chain-snatching spike lives in this block,
  so a full -1yr shift moves the signal out of the recent window and the scan goes silent
  (regression caught in test_forecast_endpoint). A day-shift keeps the spike recent.

  SHIFT_DAYS is computed so the LATEST future row lands 1 day before today:
      shift = (max_future_date - today).days + 1     (= 161 on 2026-07-21)

  Touched in ONE transaction (crimes is a VIEW over FIRs — occurred_at & reported_at both
  map to FIRs.date, fir_number maps to FIRs.FIR_Type, so only base tables are written):
    FIRs.date       -= shift days
    FIRs.FIR_YEAR    = year(new date)
    FIRs.FIR_MONTH   = month(new date)
    FIRs.FIR_Day     = day(new date)
    FIRs.FIR_Type    2026-XXX-NNNN -> 2025-XXX-NNNN only if the year actually rolled back
    property.fir_number  kept consistent with the above

  crime_id (C00727 …) carries no year, so every foreign key stays intact.

USAGE
    .venv/Scripts/python.exe scripts/fix_future_dated_rows.py [--apply]
  Without --apply it runs read-only and reports what WOULD change.
  Take a DB backup first (antar.db.bak-before-datefix).
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import date

sys.path.insert(0, ".")
from app.services.zcql_local import DB_PATH  # noqa: E402


def report(con: sqlite3.Connection, today: str) -> dict:
    q = con.execute
    return {
        "crimes_future": q("SELECT COUNT(*) FROM crimes WHERE occurred_at>?", (today,)).fetchone()[0],
        "firs_future": q("SELECT COUNT(*) FROM FIRs WHERE date>?", (today,)).fetchone()[0],
        "crimes_max": q("SELECT MAX(occurred_at) FROM crimes").fetchone()[0],
        "rajajinagar_chain": q(
            "SELECT COUNT(*) FROM crimes WHERE crime_type='chain_snatching' AND zone='Rajajinagar'"
            " AND occurred_at<=?", (today,)).fetchone()[0],
    }


def main(apply: bool) -> int:
    today = date.today().isoformat()
    con = sqlite3.connect(DB_PATH)
    before = report(con, today)
    print(f"DB     : {DB_PATH}")
    print(f"today  : {today}")
    print(f"BEFORE : crimes_future={before['crimes_future']} firs_future={before['firs_future']} "
          f"max={before['crimes_max']} rajajinagar_chain_visible={before['rajajinagar_chain']}")

    if not apply:
        print("\n(dry run — pass --apply to write)")
        con.close()
        return 0

    from datetime import date as _date, timedelta as _td
    today_d = _date.fromisoformat(today)
    max_future = con.execute("SELECT MAX(date) FROM FIRs WHERE date>?", (today,)).fetchone()[0]
    if not max_future:
        print("\nNothing to do — no future-dated rows.")
        con.close()
        return 0
    shift = (_date.fromisoformat(str(max_future)[:10]) - today_d).days + 1  # land 1 day before today
    print(f"SHIFT  : {shift} days (max future {max_future} -> {(_date.fromisoformat(str(max_future)[:10]) - _td(days=shift)).isoformat()})")

    # Read the offending rows in Python (portable date math, no SQLite date quirks),
    # then write back one prepared UPDATE per row inside a single transaction.
    rows = con.execute(
        "SELECT rowid, date, FIR_Type FROM FIRs WHERE date>?", (today,)).fetchall()
    updates, prop_updates = [], []
    for rowid, d, fir_type in rows:
        nd = _date.fromisoformat(str(d)[:10]) - _td(days=shift)
        new_type = fir_type
        if isinstance(fir_type, str) and fir_type[:4].isdigit() and int(fir_type[:4]) != nd.year:
            new_type = f"{nd.year}{fir_type[4:]}"
        updates.append((nd.isoformat(), str(nd.year), str(nd.month), str(nd.day), new_type, rowid))
        if new_type != fir_type:
            prop_updates.append((new_type, fir_type))

    try:
        with con:  # single transaction: commits on success, rolls back on exception
            con.executemany(
                "UPDATE FIRs SET date=?, FIR_YEAR=?, FIR_MONTH=?, FIR_Day=?, FIR_Type=? WHERE rowid=?",
                updates)
            if prop_updates:
                con.executemany(
                    "UPDATE property SET fir_number=? WHERE fir_number=?", prop_updates)
    except Exception as e:
        print(f"ROLLED BACK — {type(e).__name__}: {e}")
        con.close()
        return 1

    after = report(con, today)
    print(f"AFTER  : crimes_future={after['crimes_future']} firs_future={after['firs_future']} "
          f"max={after['crimes_max']} rajajinagar_chain_visible={after['rajajinagar_chain']}")
    con.close()
    ok = after["crimes_future"] == 0 and after["firs_future"] == 0
    print("\nRESULT :", "OK — no future-dated rows remain" if ok else "STILL HAS FUTURE ROWS")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main("--apply" in sys.argv))
