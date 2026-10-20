"""Repeat locations: real places only, never a station's own position or a typing default."""

from datetime import date

from app.services.repeat_locations import MIN_DAYS, MIN_FIRS, _placeholder, repeat_locations

END = date(2023, 12, 31)


def test_every_location_meets_the_rule():
    r = repeat_locations(END)
    assert r["locations"], "the 2023 register has repeat locations"
    for loc in r["locations"]:
        assert loc["firs"] >= MIN_FIRS and loc["days"] >= MIN_DAYS
        assert r["from"] <= loc["first"] <= loc["last"] <= r["to"]


def test_most_firs_first():
    firs = [l["firs"] for l in repeat_locations(END)["locations"]]
    assert firs == sorted(firs, reverse=True)


def test_online_missing_and_placeholders_left_out():
    for loc in repeat_locations(END)["locations"]:
        assert not _placeholder(loc["lat"], loc["lon"])
        assert not any(s.upper().split()[0] in ("CEN", "CYBER", "CID") for s in loc["stations"])
        for c in loc["crimes"]:
            assert "CYBER" not in c["crime"] and "MISSING" not in c["crime"] and c["crime"] != "CRPC"


def test_placeholder_detection():
    assert _placeholder(13.0, 77.0) and _placeholder(12.123, 75.123) and _placeholder(12.5, 76.5)
    assert not _placeholder(12.971, 77.594)


def test_district_filter_keeps_to_the_district():
    r = repeat_locations(END, districts=["Mysuru City"])
    assert r["locations"] and all(l["district"] == "Mysuru City" for l in r["locations"])


def test_day_cases_match_the_day_count():
    """The Map's Day dots are the same FIRs the day's count is made of (gi_star, days=0)."""
    import asyncio
    from app.api.map_api import day_cases
    from app.services.anomaly import gi_star_surface
    day = date(2026, 10, 17)
    r = asyncio.run(day_cases(day.isoformat()))
    counted = sum(z["observed"] for z in gi_star_surface(days=0, end_date=day))
    assert r["total"] == counted and r["date"] == day.isoformat()
    assert all(set(c) >= {"zone", "crime", "station", "lat", "lon"} for c in r["cases"])
    assert not any(k in c for c in r["cases"] for k in ("IOName", "Accused_ID", "accused"))


def test_day_case_details_hold_no_names_or_placeholders():
    """Complaint_Mode carries a complainant's name in the seeded rows; it never leaves."""
    import asyncio
    from app.api.map_api import day_cases
    r = asyncio.run(day_cases("2026-10-20"))
    for c in r["cases"]:
        assert "complaint" not in " ".join(c).lower()
        assert not (c["place"] or "").lower().startswith("random")
        assert c["fir_no"] is None or c["fir_no"][:4].isdigit()
