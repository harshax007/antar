"""The Map's crime pills reach the register's own spellings.

The pills send keys ("theft", "vehicle_theft"); the register writes "THEFT", "BURGLARY -
NIGHT" and puts vehicle theft in a sub-heading. Compared as is, "Theft" counted only the
demonstration rows and "Vehicle theft" nothing from the register.
"""
import sqlite3

from fastapi.testclient import TestClient

H = {"X-Role": "Inspector", "X-Officer": "map-filter-test"}


def _busiest_theft_day():
    from app.core.db_path import DB_PATH
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        return con.execute(
            "SELECT SUBSTR(date,1,10) d, COUNT(*) n FROM FIRs WHERE zone IS NOT NULL AND UPPER(TRIM(crime_type)) = 'THEFT' "
            "AND date >= '2026-01-01' AND date < '2026-10-01' GROUP BY d ORDER BY n DESC LIMIT 1").fetchone()
    finally:
        con.close()


def test_the_theft_pill_counts_the_register_spelling_too():
    from main import app
    day, n_upper = _busiest_theft_day()
    got = TestClient(app).get("/api/map/day_cases", params={"date": day, "crime_type": "theft"}, headers=H).json()
    assert got["total"] >= n_upper > 0
    assert all(c["crime"].upper() == "THEFT" for c in got["cases"])


def test_vehicle_theft_finds_register_firs_by_sub_heading():
    from app.services.crime_filter import crime_sql
    from app.core.db_path import DB_PATH
    where, args = crime_sql("vehicle_theft")
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        n = con.execute(f"SELECT COUNT(*) FROM FIRs WHERE ({where}) AND crime_type <> 'vehicle_theft'", args).fetchone()[0]
    finally:
        con.close()
    assert n > 0


def test_the_window_counts_and_the_district_card_use_the_same_filter():
    from datetime import date
    from app.services.anomaly import gi_star_surface
    from app.services.crime_filter import row_matcher
    every = sum(z["observed"] or 0 for z in gi_star_surface(None, days=30, end_date=date(2026, 9, 30)))
    theft = sum(z["observed"] or 0 for z in gi_star_surface("theft", days=30, end_date=date(2026, 9, 30)))
    assert 0 < theft < every
    assert row_matcher(None)({}) is True
