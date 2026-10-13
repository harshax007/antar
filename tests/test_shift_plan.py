"""Shift plan (app/services/shift_plan.py): counted and templated. It names a day only when
the record supports it, never a time of day, and says less rather than fill a gap."""
from datetime import date, timedelta

import pytest

from app.services import shift_plan as SP


def _dates(per_day):
    """per_day: FIR counts for Monday..Sunday, spread over past weeks."""
    monday = date(2024, 1, 1)
    out = []
    for wd, n in enumerate(per_day):
        out += [(monday + timedelta(days=wd, weeks=i)).isoformat() for i in range(n)]
    return out


def test_a_day_is_named_only_when_it_clearly_stands_out():
    p = SP.weekday_pattern(_dates([10, 10, 10, 10, 10, 30, 28]))
    assert p["stands_out"] == ["Saturday", "Sunday"] and p["firs"] == 108
    assert "Saturday and Sunday carried 54%" in p["text"] and "29%" in p["text"]


def test_an_even_spread_says_so():
    p = SP.weekday_pattern(_dates([15, 16, 15, 14, 16, 15, 15]))
    assert p["stands_out"] == [] and "No day of the week stands out" in p["text"]


def test_too_few_firs_is_not_a_pattern():
    p = SP.weekday_pattern(_dates([1, 0, 0, 0, 0, 9, 0]))
    assert p["stands_out"] == [] and "Too few FIRs" in p["text"]


def test_bad_dates_are_skipped_not_guessed():
    assert SP.weekday_pattern(["", None, "not a date", "2024-01-01"])["firs"] == 1


def _plan(**over):
    p = {"station": "Test PS", "district": "Test Dist",
         "forecast": {"expected": 5.2, "likely": "3 to 7", "very_likely": "2 to 9", "usual": 4.5, "thin": False},
         "beats": [{"name": "Beat 2", "likely": "1 to 3"}], "kinds": [{"label": "Property Crimes"}],
         "days": {"text": "No day of the week stands out: registrations are spread evenly."},
         "open_cases": {"total": 12, "in_listed_beats": 4}, "events": [],
         "limits": ["A forecast of registered FIRs, not of crime. Where more is policed, more is registered."]}
    p.update(over)
    return p


def test_the_note_is_fixed_sentences_filled_with_the_counts():
    text = SP.as_text(_plan())
    assert "likely 3 to 7 FIRs (very likely 2 to 9); a usual week is 4.5" in text
    assert "Beat 2 (likely 1 to 3)" in text and "12 FIRs" in text and "4 of them in the beats above" in text
    assert text.splitlines()[-1].startswith("Decision support only.")


def test_no_time_of_day_and_no_calendar_date_is_ever_written():
    import re
    text = SP.as_text(_plan(events=[{"name": "Mysuru Dasara", "when": "Under way, 6 days left", "effect": None}]))
    assert not re.search(r"\b\d{1,2}\s?(?:am|pm)\b|\b\d{1,2}:\d{2}\b|\b20\d{2}-\d{2}-\d{2}\b", text, re.I)
    assert "Mysuru Dasara: Under way, 6 days left." in text


def test_a_thin_history_is_said_not_forecast():
    text = SP.as_text(_plan(forecast={"thin": True}, beats=[], kinds=[], open_cases={"total": 0, "in_listed_beats": 0}))
    assert "Too little history" in text and "likely" not in text and "Open:" not in text


def test_on_the_stored_forecast_the_plan_is_built_from_records_only(monkeypatch):
    import sqlite3
    from app.core.db_path import DB_PATH
    from app.services import quickml
    # no model may be called to build a plan
    async def boom(*a, **k):
        raise AssertionError("the shift plan called a language model")
    monkeypatch.setattr(quickml, "quickml_generate", boom)
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        row = conn.execute("SELECT unit FROM forecast_output WHERE unit_type='station' AND category='ALL' AND horizon=7 "
                           "ORDER BY as_of_week DESC, expected DESC LIMIT 1").fetchone()
    except sqlite3.Error:
        pytest.skip("no forecast table in this database")
    if not row:
        pytest.skip("no stored forecasts")
    p = SP.build(conn, row[0])
    assert p["station"] and p["forecast"] and p["text"].startswith("Shift plan:")
    assert len(p["limits"]) == 3 and p["evidence_class"] == "I"
    assert all(set(c) == {"fir", "date", "crime", "beat", "accused_named"} for c in p["open_cases"]["newest"])
