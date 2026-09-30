"""Map forecasting, Phase 1 — coordinate hygiene, geo_units and the weekly cube.

Two layers:
  * a small in-memory registry, where every expected number is known by construction;
  * the real main.db cube, reconciled against FIRs for sampled beats (read-only).
"""
import sqlite3
from datetime import date

import pytest

from app.forecast import asof, store
from app.forecast.categories import categorize

_COLS = ("station", "Beat_Name", "district_norm", "CrimeGroup_Name", "crime_type", "date",
         "Latitude", "Longitude", "lat_r", "lon_r", "is_synthetic_row")


def _registry(rows):
    con = sqlite3.connect(":memory:")
    con.execute(f"CREATE TABLE FIRs (id INTEGER PRIMARY KEY, {', '.join(_COLS)})")
    con.executemany(f"INSERT INTO FIRs ({', '.join(_COLS)}) VALUES ({', '.join('?' * len(_COLS))})",
                    rows)
    con.commit()
    return con


def _row(station="Alpha PS", beat="Beat 1", group="THEFT", d="2023-10-04",
         lat=12.30, lon=76.65, synth=0, district="Mysuru City"):
    return (station, beat, district, group, group, d, lat, lon,
            None if lat is None else round(lat, 2), None if lon is None else round(lon, 2), synth)


@pytest.fixture()
def registry():
    rows = [
        _row(lat=12.30, lon=76.65),                          # good
        _row(lat=12.32, lon=76.66, d="2023-10-08"),          # good, Sunday → same ISO week
        _row(lat=76.64, lon=12.31, d="2023-10-09"),          # swapped → fixed, next week
        _row(lat=131.0, lon=777.0, d="2023-10-10"),          # impossible → rejected
        _row(lat=0, lon=0, d="2023-10-10"),                  # zeros → rejected
        _row(lat=None, lon=None, d="2023-10-10"),            # no coordinates
        _row(lat=6.75, lon=97.41, d="2023-10-11"),           # India bbox corner → rejected
        _row(group="MURDER", beat="beat 1 ", d="2023-10-11"),  # same beat after TRIM/UPPER
        _row(synth=1, d="2023-10-11"),                        # seeded: in n, not n_real
        _row(station="Beta PS", beat="", d="2023-10-11"),    # no beat: station level only
        _row(d="2017-06-01"),                                 # before CUBE_FROM: excluded
    ]
    con = _registry(rows)
    store.build(con)
    yield con
    con.close()


def test_geo_ok_keeps_karnataka_and_fixes_swaps(registry):
    got = registry.execute("SELECT id, geo_ok, geo_lat, geo_lon FROM FIRs ORDER BY id").fetchall()
    ok = {r[0]: r[1] for r in got}
    assert [ok[i] for i in (1, 2, 3)] == [1, 1, 1]
    assert [ok[i] for i in (4, 5, 7)] == [0, 0, 0]
    assert ok[6] in (0, None)                       # NULL coordinates never pass
    swapped = next(r for r in got if r[0] == 3)
    assert swapped[2:] == (12.31, 76.64)
    for _, is_ok, lat, lon in got:
        if is_ok:
            assert store.LAT_MIN <= lat <= store.LAT_MAX and store.LON_MIN <= lon <= store.LON_MAX


def test_geo_columns_follow_edits(registry):
    """Generated, not backfilled: an edited FIR is re-judged immediately."""
    registry.execute("UPDATE FIRs SET Latitude = 99, lat_r = 99 WHERE id = 1")
    assert registry.execute("SELECT geo_ok FROM FIRs WHERE id = 1").fetchone()[0] == 0


def test_cube_counts_by_week_and_category(registry):
    cube = {(t, c, w, u): (n, nr) for t, c, w, u, n, nr in
            registry.execute("SELECT * FROM forecast_cube")}
    beat = "Alpha PS | BEAT 1"
    # Week of Mon 2023-10-02: rows 1, 2 (Sun 10-08) → theft
    assert cube[("beat", "PROPERTY", "2023-10-02", beat)] == (2, 2)
    # Week of Mon 2023-10-09: rows 3-7 theft + seeded theft (row 9) → 6 in n, 5 real
    assert cube[("beat", "PROPERTY", "2023-10-09", beat)] == (6, 5)
    assert cube[("beat", "MURDER", "2023-10-09", beat)] == (1, 1)
    # Beta PS has no beat → station row only
    assert ("station", "PROPERTY", "2023-10-09", "Beta PS") in cube
    assert not any(u.startswith("Beta PS |") for (_, _, _, u) in cube)
    # Nothing before CUBE_FROM
    assert min(w for (_, _, w, _) in cube) >= store.CUBE_FROM
    # Station totals equal the FIRs they were built from
    total = registry.execute("SELECT COUNT(*) FROM FIRs WHERE date >= ?", (store.CUBE_FROM,)).fetchone()[0]
    assert sum(n for (t, *_), (n, _) in cube.items() if t == "station") == total


def test_geo_units_use_the_median_of_clean_points(registry):
    lat, lon, n_firs, n_real, n_geo = registry.execute(
        "SELECT lat, lon, n_firs, n_real, n_geo FROM geo_units "
        "WHERE unit_type = 'beat' AND unit = 'Alpha PS | BEAT 1'").fetchone()
    assert (n_firs, n_real) == (10, 9)
    # clean points: 12.30, 12.32, 12.31 (swapped), 12.30 (murder), 12.30 (seeded), 12.30
    # (2017). The rejected ones (131 N, 0 N, 6.75 N) would have dragged a mean to ~24 N.
    assert lat == pytest.approx(12.30) and lon == pytest.approx(76.65)
    assert n_geo == 6


def test_store_tables_survive_the_conftest_rowid_guard(registry):
    """conftest deletes rows above each table's rowid mark; WITHOUT ROWID is exempt."""
    for t in ("forecast_cube", "geo_units", "forecast_meta"):
        with pytest.raises(sqlite3.OperationalError):
            registry.execute(f"SELECT rowid FROM {t}")


def test_ensure_rebuilds_only_when_the_registry_changes(registry):
    assert store.ensure(registry, check_now=True) is None           # current
    registry.execute("INSERT INTO FIRs (station, Beat_Name, CrimeGroup_Name, date, is_synthetic_row) "
                     "VALUES ('Alpha PS', 'Beat 1', 'THEFT', '2023-10-12', 0)")
    registry.commit()
    stats = store.ensure(registry, check_now=True)
    assert stats and stats["cube_rows"] > 0


def test_categories_match_the_crime_graph():
    assert categorize("THEFT") == "PROPERTY"
    assert categorize("CHAIN_SNATCHING") == "PROPERTY"
    assert categorize("MOTOR VEHICLE ACCIDENTS NON-FATAL") == "ROAD"
    assert categorize("CRUELTY BY HUSBAND") == "WOMEN"
    assert categorize("ASSAULT ON PUBLIC SERVANT IS A VICTIM") == "VIOLENT"
    assert categorize("CYBER CRIME") == "CYBER"
    assert categorize(None) == "OTHER"


# ── as-of ────────────────────────────────────────────────────────────────────

def test_as_of_uses_complete_weeks(registry):
    a = asof.resolve(registry, "2026-09-18")                 # a Friday
    assert a.history_end == date(2026, 9, 7)                 # week ending Sun 13 Sep
    assert a.target_weeks(7) == [date(2026, 9, 14)]
    assert len(a.target_weeks(28)) == 4
    sunday = asof.resolve(registry, "2024-03-10")
    assert sunday.history_end == date(2024, 3, 4)            # a Sunday closes its week


def test_as_of_real_anchors_to_the_real_record(registry):
    a = asof.resolve(registry, "real")
    assert a.as_of == date(2023, 10, 11)                     # the seeded row is ignored
    assert a.mode == "real"
    with pytest.raises(ValueError):
        asof.resolve(registry, "next tuesday")


# ── the real registry (read-only) ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def live():
    from app.core.db_path import DB_PATH
    from app.services.zcql_local import ensure_indexes
    ensure_indexes()                      # what the first query does: geo columns + crimes view
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name = 'forecast_cube'").fetchone():
        pytest.skip("forecast cube not built yet (runs at backend startup)")
    yield con
    con.close()


def test_live_cube_reconciles_with_firs_for_sampled_beats(live):
    beats = [r[0] for r in live.execute(
        "SELECT unit FROM geo_units WHERE unit_type = 'beat' AND n_real > 200 "
        "ORDER BY unit LIMIT 3")]
    assert len(beats) == 3
    for beat in beats:
        cube = live.execute("SELECT SUM(n), SUM(n_real) FROM forecast_cube "
                            "WHERE unit_type = 'beat' AND unit = ?", (beat,)).fetchone()
        firs = live.execute(
            f"SELECT COUNT(*), SUM(is_synthetic_row = 0) FROM FIRs "
            f"WHERE {store.BEAT_SQL} = ? AND date >= ? AND date GLOB '[0-9][0-9][0-9][0-9]-*'",
            (beat, store.CUBE_FROM)).fetchone()
        assert cube == firs, beat


def test_live_geo_ok_rejects_everything_outside_karnataka(live):
    bad = live.execute(
        "SELECT COUNT(*) FROM FIRs WHERE geo_ok = 1 AND NOT (geo_lat BETWEEN ? AND ? "
        "AND geo_lon BETWEEN ? AND ?)",
        (store.LAT_MIN, store.LAT_MAX, store.LON_MIN, store.LON_MAX)).fetchone()[0]
    assert bad == 0
    assert live.execute("SELECT COUNT(*) FROM FIRs WHERE geo_ok = 1").fetchone()[0] > 400_000


def test_live_crimes_view_serves_clean_points(live):
    worst = live.execute("SELECT MAX(lat), MAX(lon), MIN(lat) FROM crimes").fetchone()
    assert worst[0] <= store.LAT_MAX and worst[1] <= store.LON_MAX and worst[2] >= store.LAT_MIN
