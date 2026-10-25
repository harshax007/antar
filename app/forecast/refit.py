"""Fresh data and refit - the weekly job.

The engine is fitted on the real record, which ends on a fixed date; the live board runs on
rows seeded after it. Two things follow, and this module does both:

  data_label()   says so in one sentence, for the page (it is already said in chat)
  run_once()     the weekly job: refit the forecasts when the week or the registry moved,
                 re-run the back-test when the real record or the model changed, and
                 regenerate the two reports from it

A back-test on an unchanged real record with an unchanged model gives the same numbers, so
it is not re-run for its own sake: `due()` names the reason, or there is none.

    python -m app.forecast.refit            what is due, then do it
    python -m app.forecast.refit --check    only say what is due
    python -m app.forecast.refit --force    re-run the back-test regardless

Schedule it weekly, after Sunday closes the week (Windows Task Scheduler, cron, or a
Catalyst cron job). The running app also refits the forecasts by itself when the week
moves (orchestrator tick), but leaves the back-test to this job: it takes minutes of CPU
and does not belong inside a server answering officers.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import time

from app.forecast import asof as asof_mod
from app.forecast import backtest as BT
from app.forecast import run as R
from app.forecast import store
from app.core.db_path import registry_connect

META_KEY = "refit.last"
_DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"


def data_label(conn: sqlite3.Connection) -> dict:
    """Whether this week's forecast stands on real record or on seeded rows."""
    a = asof_mod.resolve(conn)
    info = R.run_info(conn, a.history_end.isoformat()) or {}
    share = info.get("real_share")
    ends = a.real_end.isoformat() if a.real_end else None
    seeded = share is not None and share < 0.99
    if share is None:
        text = "No forecast has been fitted for this week yet."
    elif not seeded:
        text = "Built on the real record."
    else:
        text = (f"Demonstration data. The real FIR record ends on {ends}; the weeks after it are seeded. "
                f"This week's figures show the method at work, not live crime. "
                f"The accuracy figures are measured on the real record only.")
    return {"seeded": seeded, "real_share": share, "real_record_ends": ends, "text": text}


def due(conn: sqlite3.Connection) -> dict:
    """What the weekly job would do now, and why. Empty lists mean nothing is due."""
    asof_mod._real_end_cache.clear()          # a long-running process must notice new real rows
    a = asof_mod.resolve(conn)
    forecasts, backtest = [], []
    info = R.run_info(conn, a.history_end.isoformat())
    if not info:
        forecasts.append(f"No forecast is held for the week of {a.history_end.isoformat()}.")
    elif info.get("signature") != store._signature(conn):
        forecasts.append("The registry has changed since the forecasts were fitted.")
    elif info.get("model_version") != R.MODEL_VERSION:
        forecasts.append("The model has changed since the forecasts were fitted.")
    bt = BT.load(conn)
    ends = a.real_end.isoformat() if a.real_end else None
    if ends is None:
        pass                                  # nothing real to test on; nothing to re-run
    elif not bt:
        backtest.append("No back-test is stored.")
    elif bt.get("real_record_ends") != ends:
        backtest.append(f"The real record now runs to {ends}; the back-test covers it to {bt.get('real_record_ends')}.")
    elif bt.get("model_version") != R.MODEL_VERSION:
        backtest.append("The model has changed since the back-test was run.")
    return {"forecasts": forecasts, "backtest": backtest}


def last(conn: sqlite3.Connection) -> dict | None:
    try:
        row = conn.execute("SELECT value FROM forecast_meta WHERE key = ?", (META_KEY,)).fetchone()
    except sqlite3.OperationalError:
        return None
    return json.loads(row[0]) if row else None


def state(conn: sqlite3.Connection) -> dict:
    """For the page and the operator: the data label, the last run, and what is due."""
    d = due(conn)
    return {"data": data_label(conn), "last_run": last(conn), "due": d,
            "note": ("The back-test is due. Run: python -m app.forecast.refit" if d["backtest"] else None)}


def _write_reports(conn: sqlite3.Connection, bt: dict) -> list[str]:
    """The back-test report and the fairness report, both generated from the stored run."""
    from app.forecast import fairness, report
    written = []
    try:
        written.append(pathlib.Path(report.write(bt)).name)
        out = _DOCS / "FORECAST_FAIRNESS.md"
        out.write_text(fairness.report(conn), encoding="utf-8")
        written.append(out.name)
    except OSError:
        pass                                  # a read-only image: the numbers are still in the database
    return written


def run_once(conn: sqlite3.Connection, *, force: bool = False, backtest: bool = True, log=print) -> dict:
    """Do what is due. `backtest=False` is the in-app tick: forecasts only."""
    t0 = time.perf_counter()
    d = due(conn)
    refitted = []
    if d["forecasts"] or force:
        for spec in (None, "real"):
            try:
                info = R.ensure(conn, spec)
                refitted.append(info.get("as_of_week"))
                log(f"  forecasts as of {info.get('as_of')}: {info.get('models')} models")
            except ValueError as e:           # no real record to anchor to, or an empty week
                log(f"  forecasts ({spec or 'configured'}) skipped: {e}")
    reran, reports = False, []
    if backtest and (force or d["backtest"]) and asof_mod.real_record_end(conn):
        bt = BT.run(conn, log=log)
        BT.save(conn, bt)
        reran, reports = True, _write_reports(conn, bt)
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "reasons": d["forecasts"] + (d["backtest"] if backtest else []),
           "forecasts_refitted": [w for w in refitted if w], "backtest_rerun": reran, "reports": reports,
           "seconds": round(time.perf_counter() - t0, 1)}
    if refitted or reran:
        conn.execute("CREATE TABLE IF NOT EXISTS forecast_meta (key TEXT PRIMARY KEY, value TEXT) WITHOUT ROWID")
        conn.execute("INSERT OR REPLACE INTO forecast_meta VALUES (?, ?)", (META_KEY, json.dumps(out)))
        conn.commit()
    return out


if __name__ == "__main__":
    import sys
    from app.core.db_path import DB_PATH
    con = registry_connect(DB_PATH, timeout=60)
    if "--check" in sys.argv:
        print(json.dumps(state(con), indent=2))
    elif "--forecasts-only" in sys.argv:              # the server's hourly tick, as a child process
        from app.forecast import child
        child.emit(run_once(con, backtest=False, log=lambda *_: None))
    else:
        res = run_once(con, force="--force" in sys.argv)
        print(json.dumps(res, indent=2))
        if not (res["forecasts_refitted"] or res["backtest_rerun"]):
            print("Nothing was due.")
