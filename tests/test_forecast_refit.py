"""The weekly job (app/forecast/refit.py): it says when the page stands on seeded rows,
refits only when something moved, and re-runs the back-test only when its result could differ."""
import json
import sqlite3
from datetime import date

import pytest

from app.forecast import asof as asof_mod
from app.forecast import refit
from app.forecast import run as R

WEEK = date(2026, 10, 5)
REAL_END = date(2024, 3, 10)


@pytest.fixture
def world(monkeypatch, tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE forecast_meta (key TEXT PRIMARY KEY, value TEXT) WITHOUT ROWID")
    w = {"real_end": REAL_END, "sig": "s1", "run": {"signature": "s1", "model_version": R.MODEL_VERSION, "real_share": 0.0},
         "bt": {"real_record_ends": REAL_END.isoformat(), "model_version": R.MODEL_VERSION}, "calls": []}
    monkeypatch.setattr(asof_mod, "resolve", lambda c, override=None, today=None:
                        asof_mod.AsOf(as_of=date(2026, 10, 14), mode="wallclock", history_end=WEEK, real_end=w["real_end"]))
    monkeypatch.setattr(asof_mod, "real_record_end", lambda c: w["real_end"])
    monkeypatch.setattr(R, "run_info", lambda c, wk: w["run"])
    monkeypatch.setattr(refit.store, "_signature", lambda c: w["sig"])
    monkeypatch.setattr(refit.BT, "load", lambda c: w["bt"])

    def ensure(c, spec=None):
        w["calls"].append(("fit", spec))
        return {"as_of_week": "2024-03-04" if spec == "real" else WEEK.isoformat(), "as_of": "x", "models": 72}

    def bt_run(c, log=print):
        w["calls"].append(("backtest", None))
        return {"real_record_ends": w["real_end"].isoformat(), "model_version": R.MODEL_VERSION}

    monkeypatch.setattr(R, "ensure", ensure)
    monkeypatch.setattr(refit.BT, "run", bt_run)
    monkeypatch.setattr(refit.BT, "save", lambda c, bt: w["calls"].append(("save", None)))
    monkeypatch.setattr(refit, "_write_reports", lambda c, bt: ["FORECAST_BACKTEST.md", "FORECAST_FAIRNESS.md"])
    return conn, w


quiet = lambda *a, **k: None


class TestLabel:
    def test_seeded_weeks_are_named_with_the_date_the_real_record_ends(self, world):
        d = refit.data_label(world[0])
        assert d["seeded"] is True and d["real_record_ends"] == "2024-03-10"
        assert d["text"].startswith("Demonstration data.") and "2024-03-10" in d["text"] and "not live crime" in d["text"]

    def test_a_week_on_the_real_record_carries_no_warning(self, world):
        conn, w = world
        w["run"]["real_share"] = 1.0
        d = refit.data_label(conn)
        assert d["seeded"] is False and d["text"] == "Built on the real record."

    def test_no_forecast_yet_is_said_not_guessed(self, world):
        conn, w = world
        w["run"] = None
        d = refit.data_label(conn)
        assert d["seeded"] is False and d["real_share"] is None and "not been fitted" not in d["text"] and "No forecast" in d["text"]


class TestDue:
    def test_nothing_is_due_when_nothing_moved(self, world):
        assert refit.due(world[0]) == {"forecasts": [], "backtest": []}

    def test_a_new_week_or_a_changed_registry_makes_the_forecasts_due_but_not_the_back_test(self, world):
        conn, w = world
        w["run"] = None
        assert refit.due(conn)["forecasts"] and not refit.due(conn)["backtest"]
        w["run"] = {"signature": "old", "model_version": R.MODEL_VERSION}
        assert "registry has changed" in refit.due(conn)["forecasts"][0]

    def test_new_real_records_make_the_back_test_due(self, world):
        conn, w = world
        w["real_end"] = date(2026, 10, 11)
        (reason,) = refit.due(conn)["backtest"]
        assert "2026-10-11" in reason and "2024-03-10" in reason

    def test_a_changed_model_makes_both_due(self, world):
        conn, w = world
        w["run"]["model_version"] = w["bt"]["model_version"] = "0"
        d = refit.due(conn)
        assert d["forecasts"] and d["backtest"]

    def test_with_no_real_record_there_is_nothing_to_test_on(self, world):
        conn, w = world
        w["real_end"], w["bt"] = None, None
        assert refit.due(conn)["backtest"] == []


class TestRun:
    def test_an_idle_week_does_no_work_and_records_nothing(self, world):
        conn, w = world
        out = refit.run_once(conn, log=quiet)
        assert w["calls"] == [] and out["backtest_rerun"] is False and out["forecasts_refitted"] == []
        assert refit.last(conn) is None

    def test_a_new_week_refits_both_runs_and_leaves_the_back_test_alone(self, world):
        conn, w = world
        w["run"] = None
        out = refit.run_once(conn, log=quiet)
        assert w["calls"] == [("fit", None), ("fit", "real")]
        assert out["forecasts_refitted"] == [WEEK.isoformat(), "2024-03-04"] and out["backtest_rerun"] is False
        assert refit.last(conn)["forecasts_refitted"] == out["forecasts_refitted"]

    def test_new_real_records_rerun_the_back_test_and_regenerate_both_reports(self, world):
        conn, w = world
        w["real_end"] = date(2026, 10, 11)
        out = refit.run_once(conn, log=quiet)
        assert ("backtest", None) in w["calls"] and ("save", None) in w["calls"]
        assert out["backtest_rerun"] is True and out["reports"] == ["FORECAST_BACKTEST.md", "FORECAST_FAIRNESS.md"]
        assert json.loads(conn.execute("SELECT value FROM forecast_meta WHERE key = 'refit.last'").fetchone()[0])["backtest_rerun"]

    def test_the_in_app_tick_never_runs_the_back_test(self, world):
        conn, w = world
        w["real_end"], w["run"] = date(2026, 10, 11), None
        out = refit.run_once(conn, backtest=False, log=quiet)
        assert ("backtest", None) not in w["calls"] and out["backtest_rerun"] is False and out["forecasts_refitted"]

    def test_force_reruns_everything(self, world):
        conn, w = world
        out = refit.run_once(conn, force=True, log=quiet)
        assert [c[0] for c in w["calls"]] == ["fit", "fit", "backtest", "save"] and out["backtest_rerun"] is True

    def test_a_week_with_nothing_to_forecast_from_is_skipped_not_fatal(self, world, monkeypatch):
        conn, w = world
        w["run"] = None
        monkeypatch.setattr(R, "ensure", lambda c, spec=None: (_ for _ in ()).throw(ValueError("no FIRs on record")))
        out = refit.run_once(conn, backtest=False, log=quiet)
        assert out["forecasts_refitted"] == []


def test_state_tells_the_operator_what_to_run(world):
    conn, w = world
    w["real_end"] = date(2026, 10, 11)
    s = refit.state(conn)
    assert s["data"]["seeded"] is True and "python -m app.forecast.refit" in s["note"] and s["last_run"] is None


def test_the_first_tick_only_starts_the_clock(monkeypatch):
    import asyncio
    from app.core import orchestrator as O
    ran = []
    monkeypatch.setattr(O, "_refit_forecasts", lambda: ran.append(1) or {"ok": True})

    async def noop(*a, **k):
        return True, {}, {}
    monkeypatch.setattr(O, "run_agent", noop)
    monkeypatch.setitem(O._loop_state, "refit_checked_at", None)
    asyncio.run(O._autonomous_tick())
    assert ran == [] and O._loop_state["refit_checked_at"] is not None
    monkeypatch.setitem(O._loop_state, "refit_checked_at", O._loop_state["refit_checked_at"] - 3601)
    asyncio.run(O._autonomous_tick())
    assert ran == [1]
