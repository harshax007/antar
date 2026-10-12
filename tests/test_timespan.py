"""The period a question names (app/agents/timespan.py), and what is said when a named
constraint cannot be applied (query_agent.unapplied / outside_record).

Each case here was a real answer to a different question before: "March 2023" came back as
all of 2023, "before 2019" as 2019 only, "the last 2 years" as every year on record.
"""
from datetime import date

import pytest

from app.agents import query_agent as QA
from app.agents.timespan import find_span, mentions_time
from app.services import zcql_repo as Z

TODAY = date(2026, 10, 13)


@pytest.mark.parametrize("question, start, end, kind", [
    ("How many thefts in March 2023?",                       "2023-03-01", "2023-03-31", "month"),
    ("thefts in Mysuru City in Jan 2024",                    "2024-01-01", "2024-01-31", "month"),
    ("FIRs registered in Q1 2023",                           "2023-01-01", "2023-03-31", "quarter"),
    ("second quarter of 2022",                               "2022-04-01", "2022-06-30", "quarter"),
    ("thefts last quarter",                                  "2026-07-01", "2026-09-30", "quarter"),
    ("thefts in the first half of 2023",                     "2023-01-01", "2023-06-30", "half"),
    ("burglary from January to March 2023 in Bengaluru City", "2023-01-01", "2023-03-31", "months"),
    ("murders on 15 August 2023",                            "2023-08-15", "2023-08-15", "day"),
    ("murders on 2023-08-15",                                "2023-08-15", "2023-08-15", "day"),
    ("thefts on 05/03/2023",                                 "2023-03-05", "2023-03-05", "day"),   # day first
    ("robbery cases between 2021 and 2023",                  "2021-01-01", "2023-12-31", "years"),
    ("thefts during 2019-2021",                              "2019-01-01", "2021-12-31", "years"),
    ("kidnapping cases since 2020",                          "2020-01-01", "2026-10-13", "since"),
    ("cases from 2020 onwards",                              "2020-01-01", "2026-10-13", "since"),
    ("murder cases before 2019",                             "2016-01-01", "2018-12-31", "before"),
    ("thefts until 2018",                                    "2016-01-01", "2018-12-31", "before"),
    ("cheating cases after 2022",                            "2023-01-01", "2026-10-13", "after"),
    ("thefts in the last 2 years",                           "2024-10-13", "2026-10-13", "last_n"),
    ("cyber crime in the past 10 days",                      "2026-10-03", "2026-10-13", "last_n"),
    ("theft in December",                                    "2025-12-01", "2025-12-31", "month"),   # the latest one
    ("theft in May",                                         "2026-05-01", "2026-05-31", "month"),
    ("thefts in '23",                                        "2023-01-01", "2023-12-31", "year"),
    ("IPC/BNS vs SLL split for 2023?",                       "2023-01-01", "2023-12-31", "year"),
])
def test_the_window_asked_for_is_the_window_read(question, start, end, kind):
    sp = find_span(question, TODAY, 2016)
    assert sp is not None, question
    assert (sp.date_from, sp.date_to, sp.kind) == (start, end, kind)


@pytest.mark.parametrize("question", [
    "cases under Information Technology Act 2000 in Mysuru",   # a law's year
    "check vehicle KA-02-M-2028",                              # a plate
    "FIR 104/2028 details",                                    # an FIR number
    "theft trend in Mysuru",
    "how many thefts may occur",                               # "may" the verb
])
def test_numbers_and_words_that_are_not_a_period(question):
    assert find_span(question, TODAY, 2016) is None


def test_the_label_is_how_the_answer_names_the_window():
    assert find_span("thefts in March 2023", TODAY).label == "in March 2023"
    assert find_span("murder cases before 2019", TODAY).label == "before 2019"
    assert find_span("thefts in the last 2 years", TODAY).label == "in the last 2 years"
    assert find_span("theft in December", TODAY).label == "in December 2025, the latest December on record"


def test_a_time_phrase_is_noticed_even_when_it_cannot_be_read():
    assert mentions_time("thefts yesterday", TODAY) == "yesterday"
    assert mentions_time("robberies tomorrow", TODAY) == "tomorrow"
    assert mentions_time("which district has the most thefts", TODAY) is None


# ── what cannot exist is refused ────────────────────────────────────────────────

@pytest.fixture
def register(monkeypatch):
    monkeypatch.setattr(Z, "data_today", lambda: TODAY)
    monkeypatch.setattr(Z, "data_first_year", lambda: 2016)


def test_a_month_that_has_not_happened_is_refused(register):
    msg, _ = QA.outside_record("thefts in December 2026")
    assert "no records for December 2026 yet" in msg


def test_time_ahead_without_a_date_is_refused_and_points_to_the_forecast(register):
    msg, again = QA.outside_record("how many thefts next year")
    assert "“next year” has not happened yet" in msg and "forecast" in msg
    assert again


def test_a_place_in_another_state_is_refused(register):
    msg, _ = QA.outside_record("thefts in Chennai")
    assert msg.startswith("Chennai is outside Karnataka")
    assert QA.outside_record("thefts in Mysuru City") is None


# ── what is named and not applied is said ───────────────────────────────────────

@pytest.mark.parametrize("question, template, params, must_say", [
    ("thefts at night in Bengaluru City", "T1", {"crime_types": ["THEFT"], "zones": ["Bengaluru City"]}, "time of day"),
    ("murders with a knife in 2023", "T1", {"crime_types": ["MURDER"], "date_from": "2023-01-01", "date_to": "2023-12-31"}, "weapon"),
    ("robberies on weekends in 2023", "T1", {"crime_types": ["ROBBERY"], "date_from": "2023-01-01", "date_to": "2023-12-31"}, "day of the week"),
    ("thefts above 1 lakh value", "T1", {"crime_types": ["THEFT"]}, "value of property"),
    ("juvenile accused in theft cases", "T1", {"crime_types": ["THEFT"]}, "age or gender"),
    ("top suspects in 2023", "T4", {"limit": 10}, "the period “2023” was not applied"),
    ("districts with more than 5000 thefts", "T11", {"crime_types": ["THEFT"]}, "threshold"),
])
def test_an_unapplied_constraint_is_reported(register, question, template, params, must_say):
    notes = QA.unapplied(question, template, params)
    assert any(must_say in n for n in notes), notes


@pytest.mark.parametrize("question, template, params", [
    ("How many thefts in March 2023?", "T1", {"crime_types": ["THEFT"], "date_from": "2023-03-01", "date_to": "2023-03-31"}),
    ("how many cognizable cases", "T1", {"limit": 10}),
    ("show me all cases in Kodagu", "T1", {"zones": ["Kodagu"]}),
    ("Which district has the most kidnapping cases?", "T11", {"crime_types": ["KIDNAPPING AND ABDUCTION"]}),
    ("theft trend in Mysuru over the last 6 months", "T3", {"crime_types": ["THEFT"], "zones": ["Mysuru"], "months": 6}),
    ("burglary at night in Tumakuru", "T1", {"crime_types": ["BURGLARY - NIGHT"], "zones": ["Tumakuru"]}),
    ("cases for accused ACC-KA-500777", "T21", {"accused_id": "ACC-KA-500777"}),
])
def test_a_question_that_was_fully_applied_carries_no_note(register, question, template, params):
    assert QA.unapplied(question, template, params) == []


def test_the_note_leads_the_answer_inside_its_tag():
    from app.agents.answer_writer import write_answer
    rows = [{"zone": "Bengaluru City", "n": 10}, {"zone": "Mysuru City", "n": 4}]
    text = write_answer(rows, "T11", "en", {"crime_types": ["THEFT"], "unapplied": ["“on weekends” was not applied"]},
                        "which district has the most thefts on weekends")
    if text:        # the writer needs the register for its totals; without one it declines
        first = text.splitlines()[0]
        assert first.startswith("[COMPUTED] This answers a broader question than you asked: “on weekends” was not applied.")
