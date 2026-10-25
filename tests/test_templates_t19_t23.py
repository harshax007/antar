"""
T19–T23 and the T8 / T12 extensions: routing, query results and the written answers.

  T19  identifiers shared by FIRs in several districts (cross-station links)
  T20  every FIR carrying one UPI ID / IP address
  T21  one accused ID's history
  T22  case outcomes (conviction / charge-sheet / arrest / undetected)
  T23  beat and village/area hotspots
  T8   status counts, now filterable by crime type and period
  T12  recent crimes, now filterable by crime type

Runs against the local SQLite dataset (no LLM, no network).
"""

from __future__ import annotations

import asyncio

import pytest

from app.agents.answer_writer import no_hit_answer, write_answer
from app.agents.heuristics import heuristic_select
from app.agents.query_agent import run_template
from app.services.zcql_repo import (TEMPLATES, build_spec, detect_identifier, normalize_accused_id,
                                    resolve_identifier)


def route(q: str, lang: str = "en") -> dict:
    return asyncio.run(heuristic_select(q, lang))


# ── Registry ──────────────────────────────────────────────────────────────────

def test_registry_has_all_23_templates():
    expected = {"T1", "T2", "T3", "T4", "T5", "T7", "T8", "T9", "T11", "T12", "T13", "T14", "T15",
                "T16", "T17", "T18", "T19", "T20", "T21", "T22", "T23", "AST"}
    assert expected <= set(TEMPLATES)
    for tid in ("T19", "T20", "T21", "T22", "T23"):
        assert not TEMPLATES[tid].internal, f"{tid} must be selectable"
        build_spec(tid, {})                  # builds from defaults


def test_loose_llm_params_are_coerced():
    spec = build_spec("T22", {"dimension": "zone-wise", "order": "descending", "limit": "5"})
    assert ("dimension", "=", "district") in [(f.column, f.op, f.value) for f in spec.filters]
    assert spec.order_by == ("conviction_rate", "desc")
    spec = build_spec("T19", {"key_type": "UPI ID", "min_districts": "1"})
    assert ("key_type", "=", "upi") in [(f.column, f.op, f.value) for f in spec.filters]
    assert ("min_districts", "=", 2) in [(f.column, f.op, f.value) for f in spec.filters]
    assert build_spec("T11", {"order": "lowest"}).order_by == ("n", "asc")
    assert build_spec("T23", {"dimension": "villages"}).select[0] == "Village_Area_Name"


# ── Routing (English + Kannada) ───────────────────────────────────────────────

@pytest.mark.parametrize("q,lang,tid", [
    ("which UPI IDs are used in more than one district", "en", "T19"),
    ("accused who appear across multiple districts", "en", "T19"),
    ("vehicles linked to FIRs in 3 or more districts", "en", "T19"),
    ("ಹಲವು ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಬಳಸಿದ UPI ಐಡಿಗಳು", "kn", "T19"),
    ("FIRs for UPI geetha.achar40@okicici", "en", "T20"),
    ("cases linked to IP 103.87.106.22", "en", "T20"),
    ("cases for accused ACC-KA-500777", "en", "T21"),
    ("history of acc ka 102883", "en", "T21"),
    ("ACC-KA-500777 ಆರೋಪಿಯ ಪ್ರಕರಣಗಳು", "kn", "T21"),
    ("conviction rate by district in 2023", "en", "T22"),
    ("which district has the lowest conviction rate", "en", "T22"),
    ("charge sheet rate for murder cases", "en", "T22"),
    ("ಜಿಲ್ಲಾವಾರು ಶಿಕ್ಷೆ ಪ್ರಮಾಣ", "kn", "T22"),
    ("top beats for theft in Bengaluru City", "en", "T23"),
    ("which villages in Mysuru Dist have the most crime", "en", "T23"),
    ("ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಬೀಟ್‌ಗಳು", "kn", "T23"),
    ("open theft cases by status in 2024", "en", "T8"),
    ("recent burglary cases in Whitefield", "en", "T12"),
])
def test_routing(q, lang, tid):
    assert route(q, lang)["template_id"] == tid


def test_routing_parameters():
    p = route("vehicles linked to FIRs in 3 or more districts")["params"]
    assert p["key_type"] == "vehicle" and p["min_districts"] == 3
    p = route("which district has the lowest conviction rate")["params"]
    assert p["dimension"] == "district" and p["order"] == "asc"
    p = route("open theft cases by status in 2024")["params"]
    assert p["crime_types"] == ["THEFT"] and p["date_from"] == "2024-01-01"


def test_neighbouring_questions_do_not_change_route():
    assert route("vehicle theft across districts")["template_id"] != "T19"
    assert route("who are the repeat offenders")["template_id"] == "T5"
    assert route("how many open cases by status")["template_id"] == "T8"
    assert route("mail the report to officer@ksp.gov.in")["template_id"] != "T20"
    assert route("Check if vehicle KA-02-M-2093 has any pending challans or FIRs")["template_id"] == "T18"


# ── Normalisation ─────────────────────────────────────────────────────────────

def test_identifier_normalisation():
    assert normalize_accused_id("acc ka 500777") == "ACC-KA-500777"
    assert detect_identifier("geetha.achar40@okicici") == "upi"
    assert detect_identifier("103.87.106.22") == "ip"
    assert detect_identifier("KA-02-M-2093") == "vehicle"
    assert detect_identifier("ACC-KA-500777") == "accused"
    assert resolve_identifier({"value": "ka02m2093", "key_type": "vehicle"}) == ("vehicle", "KA-02-M-2093")


def test_empty_lookups_match_nothing():
    for tid in ("T18", "T20", "T21"):
        rows, _ = run_template(tid, {})
        assert rows == [], f"{tid} with no identifier must not return FIRs with blank fields"


# ── T19 cross-station links ───────────────────────────────────────────────────

def test_t19_shared_upi_ids():
    rows, _ = run_template("T19", {"key_type": "upi"})
    assert rows and all(r["key_type"] == "upi" and r["districts"] >= 2 for r in rows)
    assert rows[0]["type_total"] >= len(rows)
    assert [r["districts"] for r in rows] == sorted((r["districts"] for r in rows), reverse=True)
    text = write_answer(rows, "T19", "en", {"key_type": "upi"}, "which UPI IDs are used in more than one district")
    assert "UPI IDs appear in FIRs from 2 or more districts" in text
    assert rows[0]["key_value"] in text and "Verify before acting" in text


def test_t19_any_covers_every_identifier_type():
    rows, _ = run_template("T19", {"key_type": "any", "limit": 3})
    assert {r["key_type"] for r in rows} == {"upi", "ip", "vehicle", "accused"}
    text = write_answer(rows, "T19", "en", {"key_type": "any", "limit": 3}, "cross district links")
    assert text.startswith("[COMPUTED] Identifiers shared by FIRs in 2 or more districts")


def test_t19_min_districts_and_round_trip_to_t20():
    rows, _ = run_template("T19", {"key_type": "upi", "min_districts": 3})
    assert rows and all(r["districts"] >= 3 for r in rows)
    top = rows[0]
    firs, _ = run_template("T20", {"value": top["key_value"]})
    assert len({r["fir_id"] for r in firs}) == top["firs"]
    assert len({r["district_norm"] for r in firs}) == top["districts"]


def test_t19_kannada_answer():
    rows, _ = run_template("T19", {"key_type": "upi"})
    text = write_answer(rows, "T19", "kn", {"key_type": "upi"}, "ಹಲವು ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಬಳಸಿದ UPI ಐಡಿಗಳು")
    assert "ಜಿಲ್ಲೆಗಳ FIR ಗಳಲ್ಲಿ" in text


def test_t19_vehicle_question_does_not_filter_to_vehicle_theft():
    p = route("vehicles linked to FIRs in 3 or more districts")["params"]
    assert p["crime_types"] == []
    rows, _ = run_template("T19", p)
    assert rows and all(r["key_type"] == "vehicle" and r["districts"] >= 3 for r in rows)


# ── T20 identifier lookup ─────────────────────────────────────────────────────

def test_t20_upi_lookup_answer():
    rows, cites = run_template("T20", {"value": "geetha.achar40@okicici"})
    assert rows and cites
    text = write_answer(rows, "T20", "en", {"value": "geetha.achar40@okicici"}, "FIRs for UPI geetha.achar40@okicici")
    assert text.startswith("[VERIFIED] UPI ID **geetha.achar40@okicici** appears in")
    assert "Districts:" in text and "Crime types:" in text


def test_t20_is_case_insensitive():
    upper, _ = run_template("T20", {"value": "GEETHA.ACHAR40@OKICICI"})
    lower, _ = run_template("T20", {"value": "geetha.achar40@okicici"})
    assert len(upper) == len(lower) > 0


def test_t20_ip_lookup():
    rows, _ = run_template("T20", {"key_type": "ip", "value": "103.87.106.22"})
    assert rows and all(r["IP_Address"] == "103.87.106.22" for r in rows)


# ── T21 accused history ───────────────────────────────────────────────────────

def test_t21_accused_history():
    rows, _ = run_template("T21", {"accused_id": "acc-ka-500777"})
    assert rows
    text = write_answer(rows, "T21", "en", {"accused_id": "ACC-KA-500777"}, "cases for accused ACC-KA-500777")
    assert "Accused **ACC-KA-500777** appears in" in text
    assert "Outcomes: arrested in" in text and "Latest FIRs:" in text


# ── Not on record ─────────────────────────────────────────────────────────────

def test_no_hit_answers():
    assert "No FIR on record mentions UPI ID **nobody@bank**" in no_hit_answer("T20", {"value": "nobody@bank"})
    assert "No FIR on record lists accused **ACC-KA-999999**" in no_hit_answer("T21", {"accused_id": "ACC-KA-999999"})
    assert "No FIR on record mentions vehicle **KA-01-AB-1234**" in no_hit_answer(
        "T18", {"plate": "KA-01-AB-1234"}, "pending challans")
    assert "No UPI IDs appear in FIRs from 9 or more districts" in no_hit_answer(
        "T19", {"key_type": "upi", "min_districts": 9})
    assert "ದಾಖಲೆಯಲ್ಲಿಲ್ಲ" in no_hit_answer("T20", {"value": "nobody@bank"}, lang="kn")


# ── T22 case outcomes ─────────────────────────────────────────────────────────

_STAGES = ("under_investigation", "pending_trial", "convicted", "disposed", "undetected", "traced", "false_case")


def test_t22_overall_rates_are_consistent():
    rows, _ = run_template("T22", {})
    assert len(rows) == 1
    r = rows[0]
    assert r["firs"] > 0
    for k in ("conviction_rate", "arrest_rate", "chargesheet_rate", "undetected_share"):
        assert r[k] is not None and 0 <= r[k] <= 100
    assert sum(r[k] for k in _STAGES) <= r["firs"]
    text = write_answer(rows, "T22", "en", {}, "what is the conviction rate")
    assert "of charge-sheeted accused were convicted" in text and "Case stages" in text
    assert "Conviction rate = convicted accused" in text


def test_t22_by_district_ranks_by_rate():
    params = {"dimension": "district", "order": "asc", "date_from": "2023-01-01", "date_to": "2023-12-31"}
    rows, _ = run_template("T22", params)
    assert len(rows) > 5
    text = write_answer(rows, "T22", "en", params, "which district has the lowest conviction rate in 2023")
    assert "has the lowest conviction rate among districts" in text and "(in 2023)" in text


def test_t22_lead_follows_the_rate_asked():
    params = {"crime_types": ["MURDER"]}
    rows, _ = run_template("T22", params)
    text = write_answer(rows, "T22", "en", params, "charge sheet rate for murder cases")
    assert "of accused were charge-sheeted" in text.splitlines()[0]
    assert "• Convicted:" in text and "• Arrested:" in text
    grouped = {"dimension": "district", "order": "asc"}
    rows, _ = run_template("T22", grouped)
    text = write_answer(rows, "T22", "en", grouped, "which district has the lowest arrest rate")
    assert "has the lowest arrest rate among districts" in text


def test_t22_crime_filter_narrows():
    all_rows, _ = run_template("T22", {})
    murder, _ = run_template("T22", {"crime_types": ["MURDER"]})
    assert 0 < murder[0]["firs"] < all_rows[0]["firs"]


# ── T23 beat / area hotspots ──────────────────────────────────────────────────

def test_t23_beats_in_district():
    params = {"zones": ["Bengaluru City"], "crime_types": ["THEFT"]}
    rows, _ = run_template("T23", params)
    assert rows and "Beat_Name" in rows[0] and "UnitName" in rows[0]
    assert all(str(r["Beat_Name"]).strip().upper() != "OTHER BEAT" for r in rows)
    assert [r["n"] for r in rows] == sorted((r["n"] for r in rows), reverse=True)
    text = write_answer(rows, "T23", "en", params, "top beats for theft in Bengaluru City")
    assert "is the busiest beat for theft cases in Bengaluru City" in text
    assert "shown with its police station" in text


def test_t23_skips_placeholder_beats():
    rows, _ = run_template("T23", {"zones": ["Bengaluru City"], "crime_types": ["THEFT"], "limit": 50})
    names = {str(r["Beat_Name"]).strip().upper() for r in rows}
    assert rows and not names & {"OTHER", "OTHERS", "TEST", "OTHER BEAT", "NA", "N/A", "NIL"}


def test_t23_areas():
    rows, _ = run_template("T23", {"zones": ["Mysuru Dist"], "dimension": "area"})
    assert rows and "Village_Area_Name" in rows[0]


# ── T8 / T12 extensions ───────────────────────────────────────────────────────

def test_t8_filters_narrow_the_counts():
    all_rows, _ = run_template("T8", {})
    params = {"crime_types": ["THEFT"], "date_from": "2024-01-01", "date_to": "2024-12-31"}
    theft, _ = run_template("T8", params)
    assert 0 < sum(r["n"] for r in theft) < sum(r["n"] for r in all_rows)
    text = write_answer(theft, "T8", "en", params, "theft cases by status in 2024")
    assert text.startswith("[COMPUTED] Most theft cases in 2024 are")


def test_t12_crime_filter():
    rows, _ = run_template("T12", {"zones": ["Whitefield"], "crime_types": ["BURGLARY"]})
    assert rows and all("BURGLARY" in str(r["crime_type"]).upper() for r in rows)


# ── End to end through the query agent ───────────────────────────────────────

@pytest.mark.parametrize("q,tid,needle", [
    ("which UPI IDs are used in more than one district", "T19", "UPI IDs appear in FIRs"),
    ("FIRs for UPI geetha.achar40@okicici", "T20", "UPI ID **geetha.achar40@okicici** appears in"),
    ("cases for accused ACC-KA-500777", "T21", "Accused **ACC-KA-500777** appears in"),
    ("conviction rate by district in 2023", "T22", "conviction rate among districts"),
    ("top beats for theft in Bengaluru City", "T23", "busiest beat for theft cases"),
    ("FIRs for UPI nobody@bank", "T20", "No FIR on record mentions UPI ID"),
])
def test_query_agent_end_to_end(q, tid, needle):
    from app.agents.query_agent import query_agent_run
    out = asyncio.run(query_agent_run(q, lang="en", selector=heuristic_select, select_llm=None, compose_llm=None))
    assert out["template_id"] == tid
    assert needle in out["answer"]
    assert not out["answer"].startswith("No record matching")
