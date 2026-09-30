"""
Tests for Phase 7 Alerts and Suggestion
"""
import pytest
from app.services.events import get_events_for_date

def test_events_for_date():
    # 10 is October, Dasara Festival
    events = get_events_for_date("2023-10-15T12:00:00")
    assert any(e["name"] == "Dasara Festival" for e in events)

    # 12 is Dec, New Year's Eve
    events_dec = get_events_for_date("2023-12-30T12:00:00")
    assert any(e["name"] == "New Year's Eve" for e in events_dec)
