"""A question about a year the register does not hold is refused, never widened.

"IPC/BNS vs SLL split for 2028?" was answered with the split for every year on record:
the offline router discarded 2028 for being too late, and the date guard dropped a
window that started after the last record. These tests use no database.
"""
from datetime import date

import pytest

from app.agents import query_agent as QA
from app.services import zcql_repo as Z


@pytest.fixture(autouse=True)
def _register_2016_to_oct_2026(monkeypatch):
    monkeypatch.setattr(Z, "data_today", lambda: date(2026, 10, 13))
    monkeypatch.setattr(Z, "data_first_year", lambda: 2016)


def test_a_future_year_is_refused_and_named():
    msg, again = QA.outside_record("IPC/BNS vs SLL split for 2028?")
    assert "no records for 2028" in msg
    assert "2016" in msg and "13 Oct 2026" in msg
    # the follow-ups are the same question for the years that can be answered
    assert again == ["IPC/BNS vs SLL split for 2026?", "IPC/BNS vs SLL split for 2025?"]


def test_next_year_is_refused_too():
    assert "2027" in QA.outside_record("how many thefts in Mysuru City in 2027")[0]


def test_a_year_before_the_register_is_refused():
    msg, again = QA.outside_record("FIRs in 2010")
    assert "no records for 2010" in msg and "starts in 2016" in msg
    assert again == ["FIRs in 2016", "FIRs in 2017"]


@pytest.mark.parametrize("q", [
    "IPC/BNS vs SLL split for 2023?",
    "theft in 2026",
    "compare crime 2022 vs 2023",
    "cases under Information Technology Act 2000 in Mysuru",      # a law's year, not a period
    "IT Act, 2008 offences this year",
    "check vehicle KA-02-M-2028",                                 # a plate
    "FIR 104/2028 details",                                       # an FIR number
    "incident at 2030 hrs in Hubballi",                           # a time
    "Which district has the most kidnapping cases?",
])
def test_years_on_record_and_numbers_that_are_not_years_pass(q):
    assert QA.outside_record(q) is None


def test_one_year_out_of_two_is_enough_to_refuse():
    msg, again = QA.outside_record("compare crime 2022 vs 2029")
    assert "2029" in msg
    assert again[0] == "compare crime 2022 vs 2026"


def test_the_refusal_comes_before_the_date_guard_can_widen():
    # The date guard drops a window that starts after the last record (it exists for dates
    # a model invents). So a future year the officer named must be refused BEFORE any
    # template runs - which is what outside_record() is for.
    assert Z._date_range("2028-01-01", "2028-12-31", None) == (None, None)
    assert QA.outside_record("IPC/BNS vs SLL split for 2028?") is not None
    # a window inside the register still has its end clamped to the last record
    assert Z._date_range("2026-01-01", "2026-12-31", None) == ("2026-01-01", "2026-10-13")
