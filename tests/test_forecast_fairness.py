"""Fairness and feedback (app/forecast/fairness.py): measured from the stored back-test,
with what it cannot measure stated."""
import sqlite3

import pytest

from app.forecast import fairness as F


def test_city_commissionerates_are_told_from_the_register_s_own_names():
    assert F._group("Bengaluru City") == "city" and F._group("Mysuru City ") == "city"
    assert F._group("Belagavi Dist") == "district" and F._group(None) == "district" and F._group("Citypur") == "district"


@pytest.fixture(scope="module")
def f():
    from app.core.db_path import DB_PATH
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        got = F.measure(conn, "station")
    except sqlite3.Error:
        pytest.skip("no forecast store in this database")
    if not got:
        pytest.skip("no stored back-test")
    return got


def test_the_persistence_arithmetic_holds(f):
    p = f["persistence"]
    assert 0 < p["flagged_every_week"] <= f["flagged_per_week"] <= p["ever_flagged"]
    assert 0 <= p["share_of_flags_from_always_flagged"] <= 1 and 0 < p["share_of_units_ever_flagged"] <= 1


def test_the_groups_account_for_every_flag(f):
    assert sum(g["flagged_units"] for g in f["by_group"]) == f["persistence"]["ever_flagged"]
    assert sum(g["share_of_flags"] for g in f["by_group"]) == pytest.approx(1.0, abs=0.01)
    assert sum(g["share_of_cases_among_flagged"] for g in f["by_group"]) == pytest.approx(1.0, abs=0.01)


def test_it_says_a_stable_pattern_and_a_loop_look_the_same_and_what_it_cannot_measure(f):
    assert "cannot tell them apart" in f["findings"][0]
    assert any("never flagged" in x for x in f["not_measured"]) and any("deployment" in x for x in f["not_measured"])
    assert f["what_to_do"] and f["evidence_class"] == "D"


def test_the_engine_reads_no_field_about_a_person_or_a_community():
    """A property of the code, kept under test: the features the model is fitted on."""
    import inspect
    from app.forecast import features, model
    src = (inspect.getsource(features) + inspect.getsource(model)).lower()
    for field in ("caste", "religion", "gender", "accused_id", "male", "female", "age_0", "victim_count", "income"):
        assert field not in src, f"the forecast code mentions {field}"
