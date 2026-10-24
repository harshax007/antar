"""
District social indicators against crime (app/services/social_indicators.py, /api/social/indicators).
"""
import csv

from fastapi.testclient import TestClient

from app.services import social_indicators as si


def test_the_indicator_file_has_every_district_and_no_gaps():
    rows = list(csv.DictReader(open(si.DATA, encoding="utf-8")))
    assert len(rows) == 30
    assert all(v not in ("", None) for r in rows for v in r.values())


def test_every_police_district_in_the_register_has_a_home_or_is_statewide():
    import sqlite3
    from app.core.db_path import DB_PATH
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        names = {r[0] for r in con.execute("SELECT DISTINCT district_norm FROM FIRs WHERE is_synthetic_row = 0")}
    finally:
        con.close()
    homeless = {n for n in names if n and n not in si.POLICE_TO_REVENUE and n not in si.STATEWIDE_UNITS}
    assert not homeless, homeless
    revenue = {r["district"] for r in csv.DictReader(open(si.DATA, encoding="utf-8"))}
    assert set(si.POLICE_TO_REVENUE.values()) <= revenue


def test_links_carry_their_numbers_and_a_plain_sentence():
    a = si.analysis()
    assert a["districts"] == 30 and a["caveats"]
    for cat in si.CATEGORIES:
        links = a["correlations"][cat]["links"]
        assert links
        for l in links:
            assert -1 <= l["spearman"] <= 1 and 0 <= l["p"] <= 1 and l["sentence"]
            assert l["significant"] == (l["p"] < 0.05 and abs(l["spearman"]) >= 0.2)


def test_a_better_off_district_recording_more_crime_is_read_as_reporting():
    links = si.analysis()["correlations"]["all"]["links"]
    dev = [l for l in links if l["key"] in si.DEVELOPMENT and l["significant"] and l["spearman"] > 0]
    assert all("reporting" in (l["reading"] or "") for l in dev)


def test_the_endpoint_answers_without_a_case_level_role():
    from main import app
    r = TestClient(app).get("/api/social/indicators", headers={"X-Role": "Constable"})
    assert r.status_code == 200 and len(r.json()["table"]) == 30
