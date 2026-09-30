"""Forecast data layer — Phase 1 of docs/MAP_FORECASTING_PLAN.md.

Three things, all owned by code so a freshly staged database builds them itself:

1. **Coordinate hygiene.** ~13k FIRs carry impossible coordinates (lat 131, lon 777,
   zeros, the corners of India's bounding box). Nothing is deleted: three VIRTUAL generated
   columns on FIRs expose the usable point —
       geo_lat / geo_lon   the point, if it lies in Karnataka's bounding box — or lands
                           there once latitude and longitude are swapped (a common entry
                           error); NULL otherwise
       geo_ok              1 when geo_lat / geo_lon are usable
   Generated columns cost no storage, need no backfill and stay right when a FIR is
   ingested or edited. Every spatial query must read these, never Latitude / lat_r.

2. **geo_units** — one row per police station and per beat: district, the MEDIAN of its
   geo_ok points (median, not mean: a few stray points drag a mean kilometres off), how
   many of its FIRs are real vs seeded, and an estimated **area** (km²). The data carries
   no beat boundaries, so area is a Voronoi estimate: Karnataka is laid out as a 1-km
   grid, cells within LAND_KM of any real FIR point count as land, and each land cell goes
   to the nearest unit centroid. The back-test's PAI (% of crime ÷ % of area) needs it.

3. **forecast_cube** — FIR counts per unit × crime category × ISO week, from 2018 on,
   carrying `n` (every row) and `n_real` (the real KSP record only). Forecasts and the
   back-test read this table, never FIRs, which is what makes them instant.

Both tables are WITHOUT ROWID on purpose: the test-suite guard in tests/conftest.py
deletes rows above each table's pre-run rowid mark, which would silently truncate a cube
rebuilt during a test run.
"""
from __future__ import annotations

import sqlite3
import threading
import time

from app.forecast.categories import categorize

CUBE_VERSION = "2"
CUBE_FROM = "2018-01-01"      # a year before training starts (2019), for the same-week-last-year lag

# Karnataka's bounding box (plan §4.1). Deliberately a box, not the state polygon: it only
# has to reject impossible points; a point in the box but in the wrong district is a
# different problem that the median centroids absorb.
LAT_MIN, LAT_MAX = 11.5, 18.5
LON_MIN, LON_MAX = 74.0, 78.6
# Land mask radius. 3 km gives 209,334 km² of "land" against Karnataka's official
# 191,791 km² — the bounding box takes in a strip of neighbouring states along the border.
LAND_KM = 3.0
MIN_AREA_KM2 = 0.5          # a centroid that wins no grid cell still covers some ground

_LAT = "CAST(COALESCE(Latitude, lat_r) AS REAL)"
_LON = "CAST(COALESCE(Longitude, lon_r) AS REAL)"


def _in_box(lat: str, lon: str) -> str:
    return f"({lat} BETWEEN {LAT_MIN} AND {LAT_MAX} AND {lon} BETWEEN {LON_MIN} AND {LON_MAX})"


GEO_COLUMNS = {
    "geo_lat": f"CASE WHEN {_in_box(_LAT, _LON)} THEN {_LAT} "
               f"WHEN {_in_box(_LON, _LAT)} THEN {_LON} END",
    "geo_lon": f"CASE WHEN {_in_box(_LAT, _LON)} THEN {_LON} "
               f"WHEN {_in_box(_LON, _LAT)} THEN {_LAT} END",
    "geo_ok": "geo_lat IS NOT NULL",
}

# ISO week (Monday) of a FIR date; 'weekday 0' moves to the Sunday on or after the date.
WEEK_SQL = "date(date, 'weekday 0', '-6 days')"
_VALID_DATE = "date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'"
STATION_SQL = "TRIM(station)"
BEAT_SQL = "TRIM(station) || ' | ' || UPPER(TRIM(Beat_Name))"
_HAS_BEAT = "Beat_Name IS NOT NULL AND TRIM(Beat_Name) != ''"


def ensure_geo_columns(conn: sqlite3.Connection) -> bool:
    """Add the geo_* generated columns to FIRs if missing. Returns True if it changed."""
    have = {r[1] for r in conn.execute("PRAGMA table_xinfo(FIRs)")}
    if not {"Latitude", "Longitude", "lat_r", "lon_r"} <= have:
        return False                              # not the FIR registry schema
    added = False
    for name, expr in GEO_COLUMNS.items():         # order matters: geo_ok reads geo_lat
        if name not in have:
            conn.execute(f"ALTER TABLE FIRs ADD COLUMN {name} "
                         f"GENERATED ALWAYS AS ({expr}) VIRTUAL")
            added = True
    if added:
        conn.commit()
    return added


def _signature(conn: sqlite3.Connection) -> str:
    n, top = conn.execute("SELECT COUNT(*), COALESCE(MAX(rowid), 0) FROM FIRs").fetchone()
    return f"v{CUBE_VERSION}:{n}:{top}"


def _meta(conn: sqlite3.Connection, key: str) -> str | None:
    try:
        row = conn.execute("SELECT value FROM forecast_meta WHERE key = ?", (key,)).fetchone()
    except sqlite3.OperationalError:
        return None
    return row[0] if row else None


def _category_map(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    groups = [r[0] for r in conn.execute(
        "SELECT DISTINCT COALESCE(CrimeGroup_Name, crime_type) FROM FIRs")]
    return [(g, categorize(g)) for g in groups if g is not None]


def _km(lat, lon):
    import numpy as np
    return np.column_stack([lat * 110.57, lon * 111.32 * np.cos(np.radians(lat))])


def _areas(rows: list[tuple], land_lat, land_lon) -> tuple[list[float | None], float]:
    """Voronoi area (km²) for each geo_units row with a centroid; and the land total."""
    import numpy as np
    from scipy.spatial import cKDTree

    pts = np.unique(np.round(np.column_stack([land_lat, land_lon]), 2), axis=0)
    if not len(pts):
        return [None] * len(rows), 0.0
    tree = cKDTree(_km(pts[:, 0], pts[:, 1]))
    cells = []
    for la in np.arange(LAT_MIN, LAT_MAX, 1 / 110.57):
        lo = np.arange(LON_MIN, LON_MAX, 1 / (111.32 * np.cos(np.radians(la))))
        cells.append(np.column_stack([np.full(len(lo), la), lo]))
    grid = np.vstack(cells)
    d, _ = tree.query(_km(grid[:, 0], grid[:, 1]), distance_upper_bound=LAND_KM)
    land = _km(*grid[d <= LAND_KM].T)
    out: list[float | None] = [None] * len(rows)
    for unit_type in ("station", "beat"):
        idx = [i for i, r in enumerate(rows) if r[0] == unit_type and r[4] is not None]
        if not idx:
            continue
        cen = np.array([[rows[i][4], rows[i][5]] for i in idx])
        _, owner = cKDTree(_km(cen[:, 0], cen[:, 1])).query(land)
        count = np.bincount(owner, minlength=len(idx))
        for j, i in enumerate(idx):
            out[i] = max(float(count[j]), MIN_AREA_KM2)
    return out, float(len(land))


def _build_units(conn: sqlite3.Connection) -> tuple[list[tuple], float]:
    """geo_units rows: median centroid, district, real/seeded counts and area per station
    & beat; and the land area the areas partition."""
    import pandas as pd

    df = pd.read_sql_query(
        f"SELECT {STATION_SQL} AS station, "
        f"CASE WHEN {_HAS_BEAT} THEN {BEAT_SQL} END AS beat, "
        f"district_norm AS district, is_synthetic_row AS synth, geo_lat AS lat, geo_lon AS lon "
        f"FROM FIRs WHERE station IS NOT NULL AND TRIM(station) != ''", conn)
    df["real"] = (df["synth"] == 0).astype(int)

    rows: list[tuple] = []
    for unit_type, key in (("station", "station"), ("beat", "beat")):
        d = df[df[key].notna()]
        g = d.groupby(key, sort=False)
        counts = g.agg(n_firs=("real", "size"), n_real=("real", "sum"))
        geo = d[d["lat"].notna()].groupby(key, sort=False).agg(
            lat=("lat", "median"), lon=("lon", "median"), n_geo=("lat", "size"))
        # A station's district is where most of its FIRs are filed.
        dist = (d.groupby([key, "district"], sort=False).size().reset_index(name="c")
                  .sort_values("c", ascending=False).drop_duplicates(key).set_index(key)["district"])
        station = (d.groupby(key, sort=False)["station"].first())
        out = counts.join(geo).join(dist).join(station.rename("parent"))
        for unit, r in out.iterrows():
            lat = None if pd.isna(r["lat"]) else round(float(r["lat"]), 6)
            lon = None if pd.isna(r["lon"]) else round(float(r["lon"]), 6)
            rows.append((unit_type, unit, r["parent"] if unit_type == "beat" else unit,
                         r["district"], lat, lon, int(r["n_firs"]), int(r["n_real"]),
                         0 if pd.isna(r["n_geo"]) else int(r["n_geo"])))
    real = df[(df["synth"] == 0) & df["lat"].notna()]
    areas, land = _areas(rows, real["lat"].to_numpy(), real["lon"].to_numpy())
    return [r + (a,) for r, a in zip(rows, areas)], land


_build_lock = threading.Lock()


def build(conn: sqlite3.Connection) -> dict:
    """(Re)build geo_units and forecast_cube. Swaps them in atomically; returns stats."""
    t0 = time.perf_counter()
    ensure_geo_columns(conn)
    catmap = _category_map(conn)
    units, land_km2 = _build_units(conn)
    t_units = time.perf_counter() - t0

    conn.execute("DROP TABLE IF EXISTS temp.fc_catmap")
    conn.execute("CREATE TEMP TABLE fc_catmap (grp TEXT PRIMARY KEY, category TEXT)")
    conn.executemany("INSERT INTO temp.fc_catmap VALUES (?, ?)", catmap)
    conn.commit()

    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DROP TABLE IF EXISTS forecast_cube_new")
        conn.execute("""CREATE TABLE forecast_cube_new (
            unit_type TEXT NOT NULL, category TEXT NOT NULL, week_start TEXT NOT NULL,
            unit TEXT NOT NULL, n INTEGER NOT NULL, n_real INTEGER NOT NULL,
            PRIMARY KEY (unit_type, category, week_start, unit)) WITHOUT ROWID""")
        for unit_type, unit_sql, extra in (("station", STATION_SQL, "station IS NOT NULL AND TRIM(station) != ''"),
                                            ("beat", BEAT_SQL, _HAS_BEAT + " AND station IS NOT NULL")):
            conn.execute(f"""
                INSERT INTO forecast_cube_new (unit_type, category, week_start, unit, n, n_real)
                SELECT '{unit_type}', m.category, {WEEK_SQL} AS wk, {unit_sql} AS u,
                       COUNT(*), SUM(COALESCE(f.is_synthetic_row, 1) = 0)
                FROM FIRs f JOIN temp.fc_catmap m ON m.grp = COALESCE(f.CrimeGroup_Name, f.crime_type)
                WHERE f.date >= '{CUBE_FROM}' AND f.{_VALID_DATE} AND {extra}
                GROUP BY 2, 3, 4""")
        conn.execute("DROP TABLE IF EXISTS forecast_cube")
        conn.execute("ALTER TABLE forecast_cube_new RENAME TO forecast_cube")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_forecast_cube_unit "
                     "ON forecast_cube(unit_type, unit, week_start)")

        conn.execute("DROP TABLE IF EXISTS geo_units")
        conn.execute("""CREATE TABLE geo_units (
            unit_type TEXT NOT NULL, unit TEXT NOT NULL, station TEXT, district TEXT,
            lat REAL, lon REAL, n_firs INTEGER, n_real INTEGER, n_geo INTEGER, area_km2 REAL,
            PRIMARY KEY (unit_type, unit)) WITHOUT ROWID""")
        conn.executemany("INSERT INTO geo_units VALUES (?,?,?,?,?,?,?,?,?,?)", units)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_geo_units_district ON geo_units(district, unit_type)")

        conn.execute("CREATE TABLE IF NOT EXISTS forecast_meta "
                     "(key TEXT PRIMARY KEY, value TEXT) WITHOUT ROWID")
        stats = {
            "signature": _signature(conn),
            "cube_rows": conn.execute("SELECT COUNT(*) FROM forecast_cube").fetchone()[0],
            "units": len(units),
            "land_km2": land_km2,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        stats["seconds"] = round(time.perf_counter() - t0, 1)
        stats["units_seconds"] = round(t_units, 1)
        conn.executemany("INSERT OR REPLACE INTO forecast_meta VALUES (?, ?)",
                         [(k, str(v)) for k, v in stats.items()])
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return stats


_checked_at = 0.0
_CHECK_EVERY_S = 60.0


def ensure(conn: sqlite3.Connection | None = None, *, check_now: bool = False,
           rebuild: bool = False) -> dict | None:
    """Build the store if it is missing or stale (the FIR registry changed since).

    Cheap when current: one signature query, at most once a minute per process unless
    `check_now`. `rebuild` rebuilds regardless. Returns build stats when it built, else None.
    """
    global _checked_at
    if not (check_now or rebuild) and time.monotonic() - _checked_at < _CHECK_EVERY_S:
        return None
    own = conn is None
    if own:
        from app.core.db_path import DB_PATH
        conn = sqlite3.connect(DB_PATH, timeout=60)
    try:
        with _build_lock:
            ensure_geo_columns(conn)
            stale = rebuild or _meta(conn, "signature") != _signature(conn)
            result = build(conn) if stale else None
            _checked_at = time.monotonic()
            return result
    finally:
        if own:
            conn.close()


def geo_stats(conn: sqlite3.Connection) -> dict:
    """Coordinate-hygiene counts, split real / seeded — recorded in PROGRESS.md."""
    rows = conn.execute(f"""
        SELECT is_synthetic_row = 0 AS real,
               SUM(COALESCE(Latitude, lat_r) IS NOT NULL) AS with_coords,
               SUM(geo_ok) AS usable,
               SUM(geo_ok AND NOT {_in_box(_LAT, _LON)}) AS swapped
        FROM FIRs GROUP BY 1""").fetchall()
    out = {}
    for real, with_coords, usable, swapped in rows:
        out["real" if real else "seeded"] = {
            "with_coords": with_coords, "usable": usable, "swapped_fixed": swapped,
            "rejected": with_coords - usable}
    return out
