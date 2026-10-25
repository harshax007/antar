"""
Regression tests for the six chat misses the demo-day end-to-end run found (2026-10-26):
a week compared with the week before, "any unusual spikes", deep research in the stream,
off-topic questions, the place kept in "is crime rising in X", and future rows from self-heal.

Offline (heuristic router, local executor), like the rest of the chat tests.
"""
import asyncio
from datetime import date

from app.agents import period_compare, spikes_answer
from app.agents.heuristics import heuristic_select
from app.agents.query_agent import query_agent_run
from tests.test_chat_qa_fixes import _stream


def _ask(text, lang="en"):
    return asyncio.new_event_loop().run_until_complete(
        query_agent_run(text, lang=lang, selector=heuristic_select, compose_llm=None))


class TestCompareTrigger:
    def test_week_day_month(self):
        assert period_compare.wants_compare("Is crime rising in Bengaluru City this week?") == "week"
        assert period_compare.wants_compare("Compare theft this week with last week") == "week"
        assert period_compare.wants_compare("Is today busier than usual?") == "day"
        assert period_compare.wants_compare("this month vs last month in Mysuru") == "month"
        assert period_compare.wants_compare("ಈ ವಾರ ಅಪರಾಧ ಹೆಚ್ಚಾಗಿದೆಯೇ?") == "week"

    def test_rankings_and_plain_lists_are_not_comparisons(self):
        for q in ("Districts with lower crime this month", "Which station has higher theft this week",
                  "FIRs registered today", "List last week's FIRs in Mandya", "theft cases this week"):
            assert period_compare.wants_compare(q) is None, q


class TestCompareAnswer:
    def test_week_keeps_the_place_and_both_counts(self):
        r = _ask("Is crime rising in Bengaluru City this week?")
        assert r["template_id"] == "COMPARE"
        p = r["params"]
        assert p["zones"] == ["Bengaluru City"] and p["unit"] == "week"
        assert f"**{p['now']:,}**" in r["answer"] and f"**{p['before']:,}**" in r["answer"]
        assert "Bengaluru City" in r["answer"]

    def test_windows_are_seven_days_and_adjacent(self):
        p = _ask("Compare FIRs this week with last week")["params"]
        a0, a1 = date.fromisoformat(p["date_from"]), date.fromisoformat(p["date_to"])
        b0, b1 = date.fromisoformat(p["prev_from"]), date.fromisoformat(p["prev_to"])
        assert (a1 - a0).days == 6 and (b1 - b0).days == 6 and (a0 - b1).days == 1

    def test_counts_match_the_list_filters(self):
        from app.agents.answer_writer import _total_like
        p = _ask("Is theft rising in Mysuru this week?")["params"]
        assert p["now"] == (_total_like("T1", {"crime_types": p["crime_types"], "zones": p["zones"],
                                               "date_from": p["date_from"], "date_to": p["date_to"]}) or 0)

    def test_small_change_is_about_the_same(self):
        assert period_compare._verdict(3, 2)[0] == "flat"
        assert period_compare._verdict(105, 100)[0] == "flat"
        assert period_compare._verdict(130, 100)[0] == "up"
        assert period_compare._verdict(70, 100)[0] == "down"

    def test_day_against_yesterday_and_usual(self):
        r = _ask("Is today busier than usual?")
        assert r["template_id"] == "COMPARE" and r["params"]["unit"] == "day"
        assert "usual day" in r["answer"]

    def test_kannada(self):
        r = _ask("ಈ ವಾರ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಅಪರಾಧ ಹೆಚ್ಚಾಗಿದೆಯೇ?", lang="kn")
        assert r["template_id"] == "COMPARE" and "ಹಿಂದಿನ ಅವಧಿ" in r["answer"]


class TestSpikes:
    def test_trigger(self):
        for q in ("Are there any unusual spikes right now?", "any early warnings?", "anything flagged this week",
                  "ಯಾವುದಾದರೂ ಅಸಾಮಾನ್ಯ ಏರಿಕೆ ಇದೆಯೇ?"):
            assert spikes_answer.wants_spikes(q), q
        for q in ("theft spike during Deepavali", "spike in 2023", "theft cases in Mysuru"):
            assert not spikes_answer.wants_spikes(q), q

    def test_answer_is_the_anomaly_scan(self):
        r = _ask("Are there any unusual spikes right now?")
        assert r["template_id"] == "ALERTS"
        assert "signal to look at, not a finding" in r["answer"] or "No unusual rise" in r["answer"]
        assert all((x.get("direction") or "up") != "down" for x in r["rows"])

    def test_place_narrows_the_flags(self):
        r = _ask("Any unusual spikes in Bengaluru City?")
        assert r["template_id"] == "ALERTS"
        assert all(str(x.get("zone")).upper() == "BENGALURU CITY" for x in r["rows"])


class TestOffTopic:
    def test_weather_is_not_a_crime_list(self):
        r = _ask("What is the weather in Mysuru today?")
        assert r["template_id"] in ("NONE", "CLARIFY") and not r["rows"]

    def test_crime_question_mentioning_rain_is_not_off_topic(self):
        r = _ask("Does rain affect theft in Mysuru?")
        assert r["template_id"] not in ("NONE", "CLARIFY") and r["params"].get("crime_types")


class TestSelfHealNeverLeaksFuture:
    def test_no_row_after_today(self):
        from app.services.zcql_repo import data_today
        r = _ask("Show recent chain snatching cases in Hubballi-Dharwad")
        today = data_today().isoformat()
        for row in r["rows"]:
            d = str(row.get("date") or row.get("crime_date") or "")[:10]
            assert not d or d <= today, row


class TestStream:
    def test_research_runs_and_writes_the_dossier(self):
        answer, complete = _stream("Deep research on Raju K", "t-e2e-research")
        assert complete["template_id"] == "RESEARCH"
        assert "research" in complete["agents_used"]
        assert "Who should be researched" not in answer

    def test_compare_in_stream_skips_the_model(self):
        answer, complete = _stream("Compare FIRs this week with last week in Bengaluru City", "t-e2e-cmp")
        assert complete["template_id"] == "COMPARE" and "against" in answer

    def test_spikes_in_stream(self):
        answer, complete = _stream("Are there any unusual spikes right now?", "t-e2e-spk")
        assert complete["template_id"] == "ALERTS"
        assert "alert_suggest" not in complete["agents_used"]
