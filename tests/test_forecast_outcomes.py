"""Forecast outcomes (app/services/forecast_outcomes.py): forecasts are kept, scored once
the week is in, and recent accuracy can lower the confidence level by itself."""
import sqlite3

import pytest

from app.services import forecast_outcomes as FO


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / "fo.db")
    monkeypatch.setattr(FO, "DB_PATH", path)
    monkeypatch.setattr(FO, "ensure_db_staged", lambda: None)
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE forecast_output (as_of_week, unit_type, category, horizon, unit, expected, lo80, hi80, lo90, hi90)")
    c.execute("CREATE TABLE forecast_cube (unit_type, category, week_start, unit, n, n_real)")
    c.commit()
    return c


def _forecast(c, week, units):
    for u, (e, lo8, hi8, lo9, hi9) in units.items():
        c.execute("INSERT INTO forecast_output VALUES (?, 'station', 'ALL', 7, ?, ?, ?, ?, ?, ?)", (week, u, e, lo8, hi8, lo9, hi9))
    c.execute("INSERT INTO forecast_output VALUES (?, 'beat', 'ALL', 7, 'X | 1', 1, 0, 2, 0, 3)", (week,))       # not kept: beats
    c.execute("INSERT INTO forecast_output VALUES (?, 'station', 'THEFT', 7, 'A PS', 1, 0, 2, 0, 3)", (week,))    # not kept: one category
    c.commit()


def _recorded(c, week, counts):
    for u, n in counts.items():
        c.execute("INSERT INTO forecast_cube VALUES ('station', 'THEFT', ?, ?, ?, 0)", (week, u, n // 2))
        c.execute("INSERT INTO forecast_cube VALUES ('station', 'ROAD', ?, ?, ?, 0)", (week, u, n - n // 2))
    c.commit()


W1, W2, W3 = "2026-09-21", "2026-09-28", "2026-10-05"
UNITS = {"A PS": (6.0, 4, 8, 2, 10), "B PS": (2.0, 1, 3, 0, 4), "C PS": (10.0, 7, 13, 5, 16)}


def test_a_week_is_kept_once_and_only_the_station_all_crime_forecast(db):
    _forecast(db, W1, UNITS)
    assert FO.snapshot(W1) == 3 and FO.snapshot(W1) == 0 and FO.kept_weeks() == 1


def test_nothing_is_scored_until_the_target_week_is_complete(db):
    _forecast(db, W1, UNITS)
    FO.snapshot(W1)                          # history runs to W1; the week it forecasts (W2) is not in yet
    assert FO.scored_weeks() == [] and FO.unit_last("A PS") is None
    tr = FO.trailing()
    assert tr["weeks"] == 0 and tr["kept_weeks"] == 1 and FO.confidence_cap(tr) is None


def test_a_kept_week_is_scored_against_what_was_recorded(db):
    _forecast(db, W1, UNITS)
    FO.snapshot(W1)
    _forecast(db, W2, UNITS)                 # a new week of history arrives: W2 is now complete
    _recorded(db, W2, {"A PS": 6, "B PS": 9, "C PS": 14})
    (s,) = FO.scored_weeks()
    assert s["target_week"] == W2 and s["units"] == 3
    assert s["coverage80"] == pytest.approx(1 / 3, abs=0.001)        # only A is inside its likely range
    assert s["coverage90"] == pytest.approx(2 / 3, abs=0.001)        # A and C inside the wider one
    assert s["forecast_total"] == 18.0 and s["recorded_total"] == 29
    last = FO.unit_last("B PS")
    assert last == {"target_week": W2, "likely": "1 to 3", "recorded": 9, "held": False,
                    "text": "The week before: forecast 1 to 3, recorded 9."}
    assert FO.unit_last("Nowhere PS") is None


def test_a_station_with_no_fir_that_week_is_scored_as_zero_not_skipped(db):
    _forecast(db, W1, UNITS)
    FO.snapshot(W1)
    _forecast(db, W2, UNITS)
    _recorded(db, W2, {"A PS": 6})
    assert FO.unit_last("B PS")["recorded"] == 0 and FO.scored_weeks()[0]["recorded_total"] == 6


class TestConfidence:
    def _tr(self, cov, weeks=8):
        return {"weeks": weeks, "coverage80": cov}

    def test_it_stays_silent_until_four_weeks_are_scored(self):
        assert FO.confidence_cap(self._tr(0.2, weeks=3)) is None and FO.confidence_cap({}) is None

    def test_ranges_that_hold_near_eighty_percent_count_for_the_forecast(self):
        c = FO.confidence_cap(self._tr(0.81))
        assert c["ok"] is True and c["cap"] is None and "81%" in c["text"]

    @pytest.mark.parametrize("cov,cap", [(0.65, "Moderate"), (0.55, "Limited"), (0.97, "Moderate")])
    def test_ranges_too_narrow_or_too_wide_lower_the_level(self, cov, cap):
        c = FO.confidence_cap(self._tr(cov))
        assert c["ok"] is False and c["cap"] == cap

    def test_eight_bad_weeks_change_the_level_the_page_shows(self, db):
        from datetime import date, timedelta
        start = date(2026, 7, 6)
        weeks = [(start + timedelta(weeks=i)).isoformat() for i in range(10)]
        for i, w in enumerate(weeks[:-1]):
            _forecast(db, w, UNITS)
            FO.snapshot(w)
            _recorded(db, weeks[i + 1], {"A PS": 40, "B PS": 40, "C PS": 40})     # far outside every range
        _forecast(db, weeks[-1], UNITS)
        tr = FO.trailing()
        assert tr["weeks"] == 8 and tr["coverage80"] == 0.0
        assert FO.confidence_cap(tr)["cap"] == "Limited"


class TestFeedback:
    def test_useful_needs_no_reason_and_not_useful_does(self, db):
        assert FO.feedback_add("OF-1", "forecast", "A PS", True) == {"saved": True}
        with pytest.raises(ValueError, match="why"):
            FO.feedback_add("OF-1", "shift_plan", "A PS", False, "")
        FO.feedback_add("OF-2", "shift_plan", "A PS", False, "  the beats listed are  not ours ")
        s = FO.feedback_summary()
        assert {"kind": "forecast", "useful": 1, "total": 1} in s["by_kind"]
        assert {"kind": "shift_plan", "useful": 0, "total": 1} in s["by_kind"]
        assert s["recent_not_useful"] == [{"kind": "shift_plan", "unit": "A PS", "reason": "the beats listed are not ours"}]

    @pytest.mark.parametrize("kind,unit", [("delete", "A PS"), ("forecast", "   ")])
    def test_anything_else_is_refused(self, db, kind, unit):
        with pytest.raises(ValueError):
            FO.feedback_add("OF-1", kind, unit, True)
