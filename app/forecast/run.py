"""Fit every category and persist the forecasts — Phase 2 of docs/MAP_FORECASTING_PLAN.md.

`compute(conn, as_of)` fits station and beat models for all 17 categories plus all crime,
at 7 and 28 days, predicts from the as-of week and writes:

    forecast_output   one row per unit × category × horizon: expected FIRs, 80/90% bands,
                      P(at least one), the baseline, and the driver multipliers
    forecast_models   the fitted parameters and held-out scores per model (→ model card)
    forecast_meta     run.<as_of week>.* : series, data basis, signature, timing

The API (Phase 4) only ever reads these tables. `ensure(as_of)` recomputes when the
registry changed or the as-of week moved.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import date, timedelta

import numpy as np

from app.forecast import asof as asof_mod
from app.forecast import features as F
from app.forecast import model as M
from app.forecast import store
from app.forecast.categories import CATEGORIES
from app.core.db_path import registry_connect

# The near-repeat feature changes the design matrix, so fitted models from the other
# setting are not comparable and must not be reused: the version string carries the flag
# and `ensure()` recomputes when it changes (see F.NEAR_REPEAT).
MODEL_VERSION = "5+nr" if F.NEAR_REPEAT else "5"
UNIT_TYPES = ("station", "beat")
MIN_EXPECTED = 0.02            # rows below this with no history are not stored (≈ zero)

_OUT_COLS = ("expected", "lo80", "hi80", "lo90", "hi90", "p_any", "baseline",
             "usual_level", "x_level", "x_recent", "x_last_year", "x_neighbours", "x_area",
             "x_season", "recent4", "last_year_h", "n52")


def series_for(a: asof_mod.AsOf) -> str:
    """Real-record forecasts read real rows only; later ones read the whole registry."""
    return "n_real" if a.real_end and a.history_end + timedelta(days=6) <= a.real_end else "n"


def categories() -> list[str]:
    return [F.ALL] + list(CATEGORIES)


def _ensure_tables(conn: sqlite3.Connection) -> None:
    have = [r[1] for r in conn.execute("PRAGMA table_info(forecast_output)")]
    if have and have[5:] != list(_OUT_COLS):          # derived data: rebuild, don't migrate
        conn.execute("DROP TABLE forecast_output")
        conn.execute("DROP TABLE IF EXISTS forecast_models")
        conn.execute("DELETE FROM forecast_meta WHERE key LIKE 'run.%'")
        conn.commit()
    cols = ", ".join(f"{c} REAL" for c in _OUT_COLS)
    conn.execute(f"""CREATE TABLE IF NOT EXISTS forecast_output (
        as_of_week TEXT NOT NULL, unit_type TEXT NOT NULL, category TEXT NOT NULL,
        horizon INTEGER NOT NULL, unit TEXT NOT NULL, {cols},
        PRIMARY KEY (as_of_week, unit_type, category, horizon, unit)) WITHOUT ROWID""")
    conn.execute("""CREATE TABLE IF NOT EXISTS forecast_models (
        as_of_week TEXT NOT NULL, unit_type TEXT NOT NULL, category TEXT NOT NULL,
        horizon INTEGER NOT NULL, fit TEXT NOT NULL,
        PRIMARY KEY (as_of_week, unit_type, category, horizon)) WITHOUT ROWID""")
    conn.execute("CREATE TABLE IF NOT EXISTS forecast_meta "
                 "(key TEXT PRIMARY KEY, value TEXT) WITHOUT ROWID")


def data_basis(conn: sqlite3.Connection, a: asof_mod.AsOf) -> dict:
    """How much of the 13 weeks before the as-of date is real record vs seeded."""
    lo = (a.history_end - timedelta(weeks=12)).isoformat()
    n, real = conn.execute(
        "SELECT COALESCE(SUM(n), 0), COALESCE(SUM(n_real), 0) FROM forecast_cube "
        "WHERE unit_type = 'station' AND week_start BETWEEN ? AND ?",
        (lo, a.history_end.isoformat())).fetchone()
    return {"firs_13w": int(n), "real_13w": int(real),
            "real_share": round(real / n, 3) if n else None}


def compute(conn: sqlite3.Connection, a: asof_mod.AsOf, *,
            cats: list[str] | None = None, unit_types=UNIT_TYPES) -> dict:
    """Fit, predict and persist for one as-of. Returns a run summary."""
    t0 = time.perf_counter()
    store.ensure(conn)
    _ensure_tables(conn)
    series = series_for(a)
    cal = F.calendar(conn, series, a.history_end)
    T = cal.history_end
    if not cal.covered[T]:
        raise ValueError(f"no FIRs on record in the week of {a.history_end} — nothing to "
                         f"forecast from")
    units = {"station": F.load_units(conn, "station")}
    if "beat" in unit_types:
        units["beat"] = F.load_units(conn, "beat")
    wk = a.history_end.isoformat()
    rows, fits = [], []
    for cat in cats or categories():
        station_fits: dict[int, M.Parent] = {}
        for ut in unit_types:           # stations first: beats are reconciled to them
            p = F.load_panel(conn, units[ut], units["station"] if ut == "beat" else None, cat, cal)
            n52 = p.Y_raw[:, max(0, T - 51): T + 1].sum(axis=1)
            for hd, h in M.HORIZONS.items():
                parent = station_fits.get(hd) if ut == "beat" else None
                f = M.fit(p, T - h, hd, parent=parent)
                pr = M.predict(p, f, T, parent)
                if ut == "station":
                    station_fits[hd] = M.Parent(p, f)
                keep = np.flatnonzero((pr["expected"] >= MIN_EXPECTED) | (n52 > 0))
                cols = {**pr, "n52": n52}
                for i in keep:
                    rows.append((wk, ut, cat, hd, p.units.names[i],
                                 *(round(float(cols[c][i]), 4) for c in _OUT_COLS)))
                fits.append((wk, ut, cat, hd, json.dumps(f.to_dict())))
    basis = data_basis(conn, a)
    summary = {
        "as_of": a.as_of.isoformat(), "mode": a.mode, "as_of_week": wk, "series": series,
        "model_version": MODEL_VERSION, "signature": store._signature(conn),
        "rows": len(rows), "models": len(fits),
        "glm_models": sum(1 for *_, j in fits if json.loads(j)["method"] == "glm"),
        "seconds": round(time.perf_counter() - t0, 1),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"), **basis,
    }
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM forecast_output WHERE as_of_week = ?", (wk,))
        conn.execute("DELETE FROM forecast_models WHERE as_of_week = ?", (wk,))
        conn.executemany(f"INSERT INTO forecast_output VALUES ({','.join('?' * (5 + len(_OUT_COLS)))})", rows)
        conn.executemany("INSERT INTO forecast_models VALUES (?,?,?,?,?)", fits)
        conn.execute("DELETE FROM forecast_meta WHERE key LIKE ?", (f"run.{wk}.%",))
        conn.executemany("INSERT INTO forecast_meta VALUES (?, ?)",
                         [(f"run.{wk}.{k}", json.dumps(v)) for k, v in summary.items()])
        _prune(conn, keep={wk, _real_week(a), asof_mod.resolve(conn).history_end.isoformat()})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return summary


def _real_week(a: asof_mod.AsOf) -> str | None:
    if not a.real_end:
        return None
    last_sunday = a.real_end - timedelta(days=(a.real_end.weekday() + 1) % 7)
    return asof_mod.week_start(last_sunday).isoformat()


def _prune(conn: sqlite3.Connection, keep: set[str | None]) -> None:
    """The wall clock moves a week at a time; keep only the run just made, the configured
    as-of's and the real-record run (the back-test and model card read it)."""
    weeks = {r[0] for r in conn.execute("SELECT DISTINCT as_of_week FROM forecast_models")}
    for old in weeks - keep:
        conn.execute("DELETE FROM forecast_output WHERE as_of_week = ?", (old,))
        conn.execute("DELETE FROM forecast_models WHERE as_of_week = ?", (old,))
        conn.execute("DELETE FROM forecast_meta WHERE key LIKE ?", (f"run.{old}.%",))


def run_info(conn: sqlite3.Connection, as_of_week: str) -> dict | None:
    try:
        rows = conn.execute("SELECT key, value FROM forecast_meta WHERE key LIKE ?",
                            (f"run.{as_of_week}.%",)).fetchall()
    except sqlite3.OperationalError:
        return None
    if not rows:
        return None
    return {k.split(".", 2)[2]: json.loads(v) for k, v in rows}


def ensure(conn: sqlite3.Connection | None = None, override: str | None = None) -> dict:
    """Forecasts for the configured as-of exist and are current; compute them if not."""
    own = conn is None
    if own:
        from app.core.db_path import DB_PATH
        conn = registry_connect(DB_PATH, timeout=60)
    try:
        store.ensure(conn)
        a = asof_mod.resolve(conn, override)
        info = run_info(conn, a.history_end.isoformat())
        current = (info and info.get("signature") == store._signature(conn)
                   and info.get("model_version") == MODEL_VERSION)
        return info if current else compute(conn, a)
    finally:
        if own:
            conn.close()


if __name__ == "__main__":                              # python -m app.forecast.run [as-of]
    import sys
    from app.core.db_path import DB_PATH
    con = registry_connect(DB_PATH, timeout=60)
    a = asof_mod.resolve(con, sys.argv[1] if len(sys.argv) > 1 else None)
    print(json.dumps(compute(con, a), indent=2))
