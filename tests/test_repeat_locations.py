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
    assert not any(k in c for c in r["cases"] for k in ("IOName", "Accused_ID", "Complaint_Mode"))
    assert all(c["accused"] is None or isinstance(c["accused"], int) for c in r["cases"])   # a count, not a name


def test_day_case_details_hold_no_names_or_placeholders():
    """Complaint_Mode carries a complainant's name in the seeded rows; it never leaves."""
    import asyncio
    from app.api.map_api import day_cases
    r = asyncio.run(day_cases("2026-10-20"))
    for c in r["cases"]:
        assert "complaint" not in " ".join(c).lower()
        assert not (c["place"] or "").lower().startswith("random")
        assert c["fir_no"] is None or c["fir_no"][:4].isdigit()


def test_unit_positions_are_not_places():
    """Demonstration rows filed under a unit code with no area, and the generic
    '<City> Central PS / Beat 1' point, are a unit's own position - not a repeat location."""
    import re
    code = re.compile(r"^[A-Z0-9]+(-[A-Z0-9]+)+$")
    r = repeat_locations(date(2026, 10, 20))
    for loc in r["locations"]:
        assert not (all(code.match(s) for s in loc["stations"]) and not loc["area"])
        assert not all(s.upper().endswith("CENTRAL PS") for s in loc["stations"])
        assert isinstance(loc["active"], bool) and loc["days_since_last"] >= 0


def test_firs_metres_apart_across_a_rounding_line_are_one_spot():
    """Three-decimal rounding put 12.97149 and 12.97151 - two metres apart - in different
    cells, so a real repeat could fall under the threshold. H3 spots claim across the edge."""
    from app.services.repeat_locations import _spots, _metres
    # four FIRs within ~5 m of each other, straddling the 12.9715 rounding line
    pts = [(12.97149, 77.59461), (12.97151, 77.59462), (12.97148, 77.59463), (12.97152, 77.59460)]
    assert len({(round(a, 3), round(b, 3)) for a, b in pts}) == 2          # the old way: two cells
    rows = [(f"F{i}", a, b, f"2023-01-0{i + 1}", "X PS", "D", "THEFT", "B", "A") for i, (a, b) in enumerate(pts)]
    spots = _spots(rows)
    assert len(spots) == 1 and len(spots[0]) == 4


def test_a_spot_never_reaches_past_its_radius():
    from app.services.repeat_locations import _spots, _metres, SPOT_M
    import h3
    # a line of FIRs every 40 m: no spot may hold two FIRs more than 2 x SPOT_M apart
    rows = [(f"F{i}", 12.97 + i * 0.00036, 77.59, "2023-01-01", "X PS", "D", "THEFT", "B", "A") for i in range(30)]
    for spot in _spots(rows):
        for a in spot:
            for b in spot:
                assert _metres((a[1], a[2]), (b[1], b[2])) <= 2 * SPOT_M + 1
    assert sum(len(s) for s in _spots(rows)) == len(rows)                   # every FIR in exactly one spot
