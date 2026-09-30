"""
Brain · 02 overview officer panels and the Crime Graph profile.

The contracts: the deadline clock's buckets add up; outcome rates are percentages of the
same FIR count; data-gap months are None, never a fake zero; and the crime profile counts
EXACTLY the FIRs the radial chart beside it draws (same field, same year scope) — the
panel once showed a different peak month and total from the chart.
"""

import asyncio

import pytest

from app.api.dataset import _crime_profile, _officer_view, dataset_cycles


@pytest.fixture(scope="module")
def ov():
    return _officer_view(None, None, None, None, None)


def test_deadline_buckets_add_up(ov):
    d = ov["deadline"]
    assert d["within_60"] + d["d61_90"] + d["over_90"] == d["open_total"]
    assert 0 <= d["due_7"] <= d["within_60"] + d["d61_90"]


def test_top_overdue_lists_are_ranked(ov):
    ns = [s["n"] for s in ov["deadline"]["top_stations_over_90"]]
    assert ns == sorted(ns, reverse=True)
    assert sum(x["n"] for x in ov["deadline"]["top_districts_over_90"]) <= ov["deadline"]["over_90"]


def test_outcome_rates_are_percentages(ov):
    per = ov["outcomes"]["per_100"]
    assert all(0 <= v <= 100 for v in per.values())
    acc = ov["outcomes"]["accused"]
    assert 0 <= acc["arrest_rate"] <= 100 and 0 <= acc["conviction_rate"] <= 100


def test_monthly_is_24_months_with_gaps_as_none(ov):
    m = ov["monthly"]
    assert len(m) == 24
    assert all(x["n"] is None or x["n"] >= 0 for x in m)
    assert m[-1]["month"] == ov["as_of"][:7]


def test_filtered_view_is_a_subset(ov):
    theft = _officer_view(None, None, "THEFT", None, None)
    assert theft["deadline"]["open_total"] <= ov["deadline"]["open_total"]
    assert theft["outcomes"]["firs"] <= ov["outcomes"]["firs"]


def test_profile_matches_the_chart_it_sits_beside():
    c = asyncio.run(dataset_cycles())
    years = ",".join(map(str, c["scope_years"]))
    g = next(x for x in c["groups"] if x["name"].strip().upper() == "MURDER")
    chart_months = [sum(g["bins"][i * 3:i * 3 + 3]) for i in range(12)]
    p = _crime_profile("MURDER", None, None, years)
    assert p["total"] == g["n"]
    assert [m["n"] for m in p["months"]] == chart_months


def test_profile_shares_and_peaks_are_consistent():
    p = _crime_profile("THEFT", None, None, None)
    assert p["total"] > 0
    assert sum(w["n"] for w in p["weekdays"]) == p["total"]
    assert sum(p["month_thirds"].values()) == p["total"]
    assert p["peak_month"] == max(p["months"], key=lambda m: m["n"])["m"]
    assert all(0 < d["share"] <= 100 for d in p["top_districts"])


def test_profile_requires_a_crime():
    from fastapi.testclient import TestClient
    from main import app
    assert TestClient(app).get("/api/dataset/crime_profile").status_code == 422
