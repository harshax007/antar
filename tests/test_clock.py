"""
Tests for app/core/clock.py and system clock synchronization (Phase L1b).
"""
import os
from datetime import date, datetime, timedelta, timezone
from app.core import clock
from app.services.zcql_repo import data_today, real_data_today

_IST = timezone(timedelta(hours=5, minutes=30))


def test_clock_defaults_to_ist_today(monkeypatch):
    monkeypatch.delenv("ANTAR_TODAY", raising=False)
    assert not clock.is_fixed()
    assert clock.today() == datetime.now(_IST).date()


def test_clock_fixed_date(monkeypatch):
    monkeypatch.setenv("ANTAR_TODAY", "2024-03-31")
    assert clock.is_fixed()
    assert clock.today() == date(2024, 3, 31)


def test_clock_real_record_end(monkeypatch):
    monkeypatch.setenv("ANTAR_TODAY", "real")
    clock._real_end.cache_clear()
    real_end = clock._real_end()
    assert real_end is not None
    assert clock.today() == real_end
    # The real record ends in March 2024
    assert clock.today().year == 2024
    assert clock.today().month == 3


def test_data_today_respects_clock(monkeypatch):
    monkeypatch.setenv("ANTAR_TODAY", "2024-03-31")
    data_today.cache_clear()
    real_data_today.cache_clear()
    
    # data_today() should be capped at 2024-03-31
    dt = data_today()
    assert dt <= date(2024, 3, 31)
    
    rdt = real_data_today()
    assert rdt <= date(2024, 3, 31)
