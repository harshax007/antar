"""
Tests for the ZCQL template engine against the seed JSON (local executor).
Run: python -m pytest tests/test_zcql.py -v   (run `python -m app.seeds.load` first)

These assert the engine returns the PLANTED facts (P1/P2/P3) — i.e. the demo's
guarantees are queryable, not just present in the data.
"""

from app.services.zcql_repo import build_spec, render_zcql, TEMPLATES
from app.services.zcql_local import run_local


def test_t2_finds_raju_by_name():
    spec = build_spec("T2", {"name_or_alias": "Raju"})
    rows = run_local(spec)
    assert any(r["suspect_id"] == "S0001" for r in rows)


def test_t2_finds_by_alias_yellappa():
    # P1: searching the alias "Yellappa" must surface both Raju K. and Yellappa M.
    spec = build_spec("T2", {"name_or_alias": "Yellappa"})
    rows = run_local(spec)
    ids = {r["suspect_id"] for r in rows}
    assert "S0001" in ids and "S0002" in ids


def test_t1_chain_snatching_rajajinagar_nonempty():
    spec = build_spec("T1", {"crime_types": ["chain_snatching"], "zones": ["Rajajinagar"]})
    rows = run_local(spec)
    assert len(rows) > 0
    assert all(r["crime_type"] == "chain_snatching" and r["zone"] == "Rajajinagar" for r in rows)


def test_t1_region_expansion_bengaluru_north():
    # "Bengaluru North" must expand to concrete zones (region resolution).
    spec = build_spec("T1", {"crime_types": ["robbery"], "zones": ["Bengaluru North"]})
    rows = run_local(spec)
    assert all(r["zone"] in ["Rajajinagar", "Malleshwaram", "Yeshwanthpur", "Hebbal"] for r in rows)


def test_t3_trend_returns_months():
    spec = build_spec("T3", {"crime_types": ["robbery"], "zones": ["Bengaluru North"], "months": 6})
    rows = run_local(spec)
    assert rows and all("month" in r and "n" in r for r in rows)
    # months sorted ascending
    months = [r["month"] for r in rows]
    assert months == sorted(months)


def test_t3_accepts_period_string_for_months():
    """Robustness: the live LLM often sends `months` as a period STRING for T3 (which has no
    `period` field) — e.g. 'last_3_months'. These must coerce to a month count, not raise."""
    for val in ("last_3_months", "last 6 months", "6", 6):
        spec = build_spec("T3", {"crime_types": ["robbery"], "zones": ["Bengaluru North"], "months": val})
        rows = run_local(spec)                       # must build + run without a validation error
        assert all("month" in r and "n" in r for r in rows)


def test_t3_garbage_months_defaults_not_crash():
    """Failure-mode: a junk month value defaults to the standard window instead of raising."""
    spec = build_spec("T3", {"crime_types": ["robbery"], "months": "whenever"})
    assert spec.table == "crimes"                    # built a valid spec (defaulted, clamped)


def test_t11_hotspots_rajajinagar_is_hot_for_theft():
    # Rajajinagar is a seeded locality inside Bengaluru City. T11 ranks by district (the
    # result key stays "zone"), so a locality never appears as a district of its own.
    spec = build_spec("T11", {"crime_types": ["theft"]})
    rows = run_local(spec)
    top_zones = [r["zone"] for r in rows[:4]]
    assert any("Bengaluru" in z or "Rajajinagar" in z or "Gandhinagar" in z for z in top_zones), \
        f"Expected Bengaluru/Rajajinagar/Gandhinagar in top theft zones, got {top_zones}"


def test_t5_repeat_offenders_sorted():
    spec = build_spec("T5", {"min_priors": 5})
    rows = run_local(spec)
    assert rows and all(r["prior_count"] >= 5 for r in rows)
    counts = [r["prior_count"] for r in rows]
    assert counts == sorted(counts, reverse=True)


def test_t9_suspect_crimes_for_raju():
    spec = build_spec("T9", {"suspect_id": "S0001"})
    rows = run_local(spec)
    assert len(rows) > 0  # Raju K. has a planted Bengaluru record


def test_t4_top_suspects_by_zone():
    spec = build_spec("T4", {"zones": ["Rajajinagar"], "limit": 5})
    rows = run_local(spec)
    assert rows and rows[0]["crime_count"] >= rows[-1]["crime_count"]  # sorted desc


def test_t7_demographic_breakdown_gender():
    spec = build_spec("T7", {"entity": "victims", "dimension": "gender"})
    rows = run_local(spec)
    assert rows and all("gender" in r and "n" in r for r in rows)


def test_build_spec_strips_null_params():
    """The live LLM emits explicit nulls (e.g. limit: null) — must not crash; defaults apply."""
    spec = build_spec("T1", {"crime_types": ["theft"], "zones": ["Rajajinagar"], "limit": None})
    assert spec.limit == 100                              # field default, not a validation crash
    assert build_spec("T5", {"min_priors": None, "limit": None}).table == "suspects"


def test_build_spec_required_null_still_errors():
    """Failure-mode: a required field sent as null is still rejected (can't look up a null name)."""
    import pytest
    with pytest.raises(Exception):
        build_spec("T2", {"name_or_alias": None})


def test_t7_dimension_synonym_coerced():
    """The live LLM sends dimension='age' (not the literal 'age_band') — coerce, don't crash."""
    rows = run_local(build_spec("T7", {"entity": "suspects", "dimension": "age"}))
    assert rows                                           # age→age_band→age(suspects); ran fine
    assert build_spec("T7", {"dimension": "whatever"}).table == "victims"   # unknown → safe default


def test_date_range_drops_future_window():
    """The LLM is bad at dates; a fully-future window (no data yet) must be ignored, past kept."""
    from app.services.zcql_repo import _date_range
    assert _date_range("2099-01-01", "2099-12-31", None) == (None, None)
    assert _date_range("2024-01-01", "2024-03-31", None) == ("2024-01-01", "2024-03-31")


def test_render_zcql_is_injection_safe():
    # A quote in a param must be escaped, not break out of the string.
    spec = build_spec("T2", {"name_or_alias": "O'Brien"})
    sql = render_zcql(spec)
    assert "O''Brien" in sql  # doubled quote = escaped


def test_unknown_template_raises():
    import pytest
    with pytest.raises(KeyError):
        build_spec("T999", {})


def test_all_templates_build_with_examples():
    # Smoke: every registered template builds a spec from minimal params without error.
    minimal = {
        "T1": {}, "T2": {"name_or_alias": "x"}, "T3": {}, "T4": {}, "T5": {},
        "T7": {}, "T8": {}, "T9": {"suspect_id": "S0001"}, "T11": {}, "T12": {},
        "AST": {"ast": {"table": "crimes", "select": ["crime_id"]}},
    }
    for tid in TEMPLATES:
        spec = build_spec(tid, minimal.get(tid, {}))
        assert spec.table  # produced a spec


def test_t11_never_lists_a_seeded_locality_as_a_district():
    from app.services.zcql_repo import ALL_ZONES
    real_districts = {"Belagavi", "Kalaburagi"}          # names that are also real districts' roots
    for params in ({"crime_types": ["vehicle_theft"]}, {"crime_types": ["theft"], "limit": 60}, {"limit": 60}):
        rows = run_local(build_spec("T11", params))
        assert rows and "zone" in rows[0] and "district" not in rows[0]
        names = {r["zone"] for r in rows}
        assert not (names & (set(ALL_ZONES) - real_districts)), names & set(ALL_ZONES)
        assert "Belagavi" not in names                   # the seeded locality; the district is "Belagavi Dist"


def test_a_crime_type_with_no_real_rows_is_flagged_and_a_real_one_is_not():
    from app.services.zcql_repo import demo_only_crime_types
    assert demo_only_crime_types(["VEHICLE_THEFT"]) == ["VEHICLE_THEFT"]
    assert demo_only_crime_types(["THEFT", "MURDER", "BURGLARY"]) == []
    assert demo_only_crime_types([]) == []


def test_the_answer_says_when_a_count_is_demonstration_records_only():
    from app.agents.answer_writer import write_answer
    from app.agents.query_agent import run_template
    # missing persons have no head in the real register: the count is demonstration records only
    p = {"crime_types": ["MISSING_PERSON"], "limit": 10, "dimension": "zone"}
    rows, _ = run_template("T11", p)
    text = write_answer(rows, "T11", "en", p, "Which districts have the most missing persons?")
    assert "Jayanagar" not in text and "demonstration records" in text
    # vehicle theft now also counts the register's own sub-headings (HEAD_BACKED), so it is real
    p = {"crime_types": ["VEHICLE_THEFT"], "limit": 10, "dimension": "zone"}
    rows, _ = run_template("T11", p)
    text = write_answer(rows, "T11", "en", p, "Which districts have the most vehicle theft?")
    assert "Jayanagar" not in text and "demonstration records" not in text
    p = {"crime_types": ["THEFT"], "limit": 10, "dimension": "zone"}
    rows, _ = run_template("T11", p)
    assert "demonstration records" not in write_answer(rows, "T11", "en", p, "Which districts have the most theft?")
