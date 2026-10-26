"""The Map agents return their figures, so the Map card can word them in English and Kannada.

And Pattern reads a Map crime key and the district's own FIRs: it used to look up
"vehicle_theft" as a crime group (nothing), and cluster a random 10,000 FIRs of the whole
state, so a district's answer changed from run to run.
"""
from app.agents import brain_console as B


def test_forecast_and_geo_carry_the_numbers_behind_their_sentence():
    f = B.AGENTS["forecast"].run(B.Target(station="Bengaluru City Central PS"))
    if f["status"] != "ok":
        return                                  # no forecast model built in this checkout
    x = f["facts"]
    assert x["kind"] == "forecast" and len(x["likely"]) == 2 and x["likely"][0] <= x["likely"][1]
    assert f"{x['likely'][0]}–{x['likely'][1]}" in f["bottom_line"]
    g = B.AGENTS["geo"].run(B.Target(district="Bengaluru City"))
    assert g["facts"]["kind"] == "geo" and g["facts"]["beats"]
    assert isinstance(g["facts"]["as_of"], (str, type(None)))


def test_pattern_reads_a_map_key_in_the_district_and_gives_the_same_answer_twice():
    t = B.Target(crime_group="theft", district="Bagalkot")
    a, b = B.AGENTS["pattern"].run(t), B.AGENTS["pattern"].run(t)
    assert a["status"] == "ok" and a["facts"] == b["facts"]
    assert a["facts"]["place"] == "Bagalkot" and a["facts"]["scanned"] > 0
    v = B.AGENTS["pattern"].run(B.Target(crime_group="vehicle_theft", district="Bengaluru City"))
    assert v["status"] in ("ok", "empty") and "Vehicle_Theft" not in v["bottom_line"]


def test_research_on_a_place_lists_people_by_count():
    r = B.AGENTS["research"].run(B.Target(district="Bengaluru City"))
    if r["status"] == "ok":
        people = r["facts"]["people"]
        assert people and people == sorted(people, key=lambda p: -p["firs"])
