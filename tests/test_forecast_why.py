"""The "why" of a forecast (app/forecast/service.py::why): a usual period times named
reasons, which must multiply to the forecast, with the forecast-without-it for each."""
import math

import pytest

from app.forecast import service as S


def _row(**x):
    row = {"unit": "Test PS", "usual_level": 5.0, "x_recent": 1.3, "x_last_year": 1.0, "x_neighbours": 1.1,
           "x_area": 0.98, "x_season": 1.02, "x_level": 1.0, "recent4": 26, "last_year_h": 5, "n52": 260}
    row.update(x)
    prod = math.prod(row[f"x_{k}"] for k in S._WHY_KEYS)
    row.setdefault("expected", row["usual_level"] * prod)
    return row


def test_the_reasons_multiply_to_the_forecast():
    w = S.why(_row(), "station", 7)
    assert w["reconciles"] is True
    assert w["usual"] * math.prod(s["factor"] for s in w["steps"]) == pytest.approx(w["expected"], rel=0.01)
    assert [s["key"] for s in w["steps"]][:2] == ["recent", "neighbours"]          # largest first
    assert {s["key"] for s in w["steps"]} == set(S._WHY_KEYS)                       # all six, not only the notable


def test_each_reason_carries_the_forecast_without_it():
    row = _row()
    w = S.why(row, "station", 7)
    recent = next(s for s in w["steps"] if s["key"] == "recent")
    assert recent["without"] == pytest.approx(row["expected"] / 1.3, abs=0.01)
    assert recent["notable"] is True and "last 4 weeks" in recent["text"]
    assert next(s for s in w["steps"] if s["key"] == "area")["notable"] is False   # 2% is not a reason worth a sentence


def test_a_usual_week_says_so_instead_of_inventing_a_reason():
    w = S.why(_row(x_recent=1.01, x_neighbours=1.02), "station", 7)
    assert w["plain"].startswith("Close to a usual period") and not any(s["notable"] for s in w["steps"])


def test_a_forecast_that_does_not_reconcile_is_flagged_not_hidden():
    assert S.why(_row(expected=9.9), "station", 7)["reconciles"] is False


@pytest.mark.parametrize("bad", [{"usual_level": 0}, {"expected": 0}])
def test_no_breakdown_without_a_usual_level(bad):
    assert S.why(_row(**bad), "beat", 7) is None


def test_it_holds_on_the_stored_forecasts():
    """On the real forecast table: every station forecast is its usual week times its reasons."""
    import sqlite3
    from app.core.db_path import DB_PATH
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        rows = conn.execute(f"SELECT {', '.join(S._COLS)} FROM forecast_output WHERE unit_type='station' AND horizon=7 "
                            "AND category='ALL' AND as_of_week=(SELECT MAX(as_of_week) FROM forecast_output) LIMIT 300").fetchall()
    except sqlite3.Error:
        pytest.skip("no forecast table in this database")
    if not rows:
        pytest.skip("no stored forecasts")
    ws = [S.why(dict(zip(S._COLS, r)), "station", 7) for r in rows]
    assert all(w["reconciles"] for w in ws if w)
