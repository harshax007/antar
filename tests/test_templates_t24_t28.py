"""
T24–T28, sub-headings, police stations and the routing fixes of 2026-10-20.

  T24  case stages and pendency (under investigation, pending trial, how long open)
  T25  what a crime group is made of: sub-headings, or burglary by day vs night
  T26  day-of-week / month-of-year pattern (by registration date)
  T27  two or more districts, stations or years side by side
  T28  case outcomes by the Act / section a case was registered under

Each question here was asked by an officer and answered wrongly before (audit log).
Runs against the local SQLite dataset, read-only (no LLM, no network, no session).
"""

from __future__ import annotations

import asyncio

import pytest

from app.agents.answer_writer import write_answer
from app.agents.heuristics import extract_entities, heuristic_select
from app.agents.query_agent import run_template, unapplied
from app.services.zcql_repo import (TEMPLATES, build_spec, head_label, render_zcql, resolve_heads,
                                    resolve_stations, resolve_zones)


def route(q: str, lang: str = "en") -> dict:
    return asyncio.run(heuristic_select(q, lang))


def answer(q: str) -> str:
    c = route(q)
    tid, prm = c["template_id"], dict(c.get("params") or {})
    rows, _ = run_template(tid, prm)
    notes = unapplied(q, tid, prm)
    if notes:
        prm["unapplied"] = notes
    return write_answer(rows, tid, "en", prm, q) or ""


# ── registry ──────────────────────────────────────────────────────────────────

def test_new_templates_are_selectable_and_build_from_defaults():
    for tid in ("T24", "T25", "T26", "T27", "T28"):
        assert tid in TEMPLATES and not TEMPLATES[tid].internal
        build_spec(tid, {})


# ── routing: the questions that were answered wrongly ─────────────────────────

@pytest.mark.parametrize("q,tid", [
    ("Stations with highest pending investigation count in Mysuru", "T24"),
    ("How many extortion cases are currently under investigation?", "T24"),
    ("How many POCSO cases reached trial stage in 2023?", "T24"),
    ("cases under investigation for more than 1 year in Mysuru City", "T24"),
    ("Show the breakdown of case statuses (under investigation, charge-sheeted, convicted) in Davanagere", "T24"),
    ("What proportion of reported thefts involve two-wheelers?", "T25"),
    ("Are burglaries more frequent during night hours or day hours?", "T25"),
    ("Day of week distribution for chain snatching incidents", "T26"),
    ("Lowest weekday for theft, and by how much?", "T26"),
    ("which months see the most burglary", "T26"),
    ("Conviction rate comparison between Bengaluru City and Mysuru", "T27"),
    ("compare theft in Hassan vs Mandya", "T27"),
    ("murder cases 2022 vs 2023 in Belagavi", "T27"),
    ("Which act sections have the lowest conviction rate?", "T28"),
    ("Monthly trend of robbery cases across Karnataka in 2023", "T3"),
    ("Show crime history and profile for suspect Saleem Malik", "T2"),
    ("Find phone number hash shared across multiple police districts", "T19"),
    ("Identify emerging crime cluster corridors between Bengaluru and Tumakuru", "T19"),
    ("Which beats in Jayanagar require heightened night patrol?", "T23"),
    ("Where should patrol vans be deployed in Belagavi?", "T23"),
    ("Rank all districts by total crime volume in 2023", "T11"),
])
def test_routing(q, tid):
    assert route(q)["template_id"] == tid


def test_existing_questions_keep_their_route():
    for q, tid in (("Compare crime totals in 2022 versus 2023", "T16"),
                   ("Fastest-growing crime groups 2021 to 2022?", "T16"),
                   ("Peak month for cybercrime in 2022?", "T3"),
                   ("Show me all unsolved burglary cases from last month", "T1"),
                   ("Conviction rate by district in 2023", "T22"),
                   ("top suspects in Rajajinagar", "T4"),
                   ("Find burglary cases involving night entry through rear windows or ventilators", "T1")):
        assert route(q)["template_id"] == tid, q


# ── places, stations and sub-headings ─────────────────────────────────────────

def test_city_names_mean_the_real_districts():
    assert "Mangaluru City" in resolve_zones(["Mangaluru"])
    assert "Hubballi Dharwad City" in resolve_zones(["Hubballi"])
    assert {"Belagavi City", "Belagavi Dist"} <= set(resolve_zones(["Belagavi"]))
    assert extract_entities("cybercrime in Hubballi-Dharwad City")["zones"] == ["Hubballi Dharwad City"]
    assert resolve_zones(extract_entities("extortion in Vijayapura")["zones"]) == ["Vijayapur"]


def test_places_keep_the_order_they_were_asked_in():
    assert extract_entities("compare theft in Hassan vs Mandya")["zones"] == ["Hassan", "Mandya"]


def test_police_stations_are_recognised():
    assert resolve_stations("Koramangala") == ["Koramangala PS"]
    e = extract_entities("thefts in Koramangala")
    assert e["stations"] == ["Koramangala PS"] and not e["unknown_place"]
    # a Traffic / CEN station only when that word is said
    assert "Jayanagar Traffic PS" not in resolve_stations("Jayanagar")
    assert "Jayanagar Traffic PS" in resolve_stations("Jayanagar traffic")


def test_sub_headings():
    assert resolve_heads("two wheeler thefts") == ["Of Automobiles - Of Two Wheelers"]
    assert "Extortion" in resolve_heads("extortion cases")
    assert head_label("Of Automobiles - Of Two Wheelers") == "two-wheelers"
    # a generic word gives no sub-heading on its own, nor one the crime asked is never filed under
    assert extract_entities("accidents involving cars in Mysuru")["heads"] == []


def test_vehicle_theft_and_chain_snatching_count_the_real_register():
    """Both used to match only ~300 seeded rows; the register files them as sub-headings."""
    vt = run_template("T11", {"crime_types": ["VEHICLE_THEFT"], "limit": 1})[0]
    assert vt and vt[0]["n"] > 10_000
    cs = run_template("T11", {"crime_types": ["CHAIN_SNATCHING"], "limit": 1})[0]
    assert cs and cs[0]["n"] > 1_000
    # the seeded demonstration stories still match
    rj = run_template("T1", {"crime_types": ["CHAIN_SNATCHING"], "zones": ["Rajajinagar"], "limit": 5})[0]
    assert rj


def test_station_filter_narrows():
    all_bc = run_template("T1", {"crime_types": ["THEFT"], "zones": ["Bengaluru City"], "limit": 1})
    kor = answer("thefts in Koramangala")
    assert "Koramangala PS" in kor.split("\n")[0]
    assert all_bc


# ── results and written answers ───────────────────────────────────────────────

def test_t24_pendency_by_station():
    a = answer("Stations with highest pending investigation count in Mysuru")
    assert "under investigation" in a and "PS" in a.split("\n")[0]


def test_t24_trial_stage():
    a = answer("How many POCSO cases reached trial stage in 2023?")
    assert "pending trial" in a.split("\n")[0] and "2023" in a.split("\n")[0]


def test_t24_ageing_threshold():
    rows, _ = run_template("T24", {"zones": ["Mysuru City"], "older_than_days": 365})
    r = rows[0]
    assert 0 < r["ui_older"] <= r["under_investigation"]
    assert r["ui_over_365"] == r["ui_older"]


def test_t25_share_of_a_sub_heading():
    a = answer("What proportion of reported thefts involve two-wheelers?")
    assert "%" in a.split("\n")[0] and "two-wheelers" in a.split("\n")[0]


def test_t25_day_vs_night_burglary_and_no_time_of_day_disclaimer():
    a = answer("Are burglaries more frequent during night hours or day hours?")
    assert "by night" in a.split("\n")[0]
    assert "broader question" not in a


def test_t26_weekday_pattern_is_by_registration_date():
    a = answer("Day of week distribution for chain snatching incidents")
    assert "busiest day" in a and "registered" in a
    assert "broader question" not in a


def test_t27_compares_in_question_order():
    a = answer("compare theft in Hassan vs Mandya")
    lead = a.split("\n")[0]
    assert lead.index("Hassan") < lead.index("Mandya")


def test_t27_years_carry_the_partial_extract_note():
    a = answer("murder cases 2022 vs 2023 in Belagavi")
    assert "2022" in a and "2023" in a and "third of each year" in a


def test_t28_ranks_sections_and_skips_the_missing_person_entry():
    a = answer("Which act sections have the lowest conviction rate?")
    assert "s." in a.split("\n")[0] and "00MP" not in a


def test_phone_links_say_what_was_not_used():
    a = answer("Find phone number hash shared across multiple police districts")
    assert "phone numbers are not recorded" in a


def test_time_of_day_is_reported_as_not_recorded():
    a = answer("At what hours of the day do most robberies occur in Kalaburagi?")
    assert "not the time of day" in a


def test_exact_lookups_do_not_order_through_the_date_index():
    sql = render_zcql(build_spec("T18", {"plate": "KA-04-MH-1234"}))
    assert "ORDER BY +date" in sql
