"""Map forecasting, Phase 3 — the rolling back-test, its report and the model card.

Runs on the synthetic registry from test_forecast_model (known rates, a 5× recording
step, a data hole), through the real back-test.
"""
import sqlite3

import pytest

from app.forecast import backtest as BT
from app.forecast import card, model as M, report, run
from tests.test_forecast_model import _registry


@pytest.fixture(scope="module")
def reg():
    con = _registry(seed=11)
    yield con
    con.close()


@pytest.fixture(scope="module")
def bt(reg):
    seen = []
    real_fit = M.fit

    def spy(p, last_origin, horizon_days, **kw):
        seen.append((p.cal.history_end, last_origin, M.HORIZONS[horizon_days]))
        return real_fit(p, last_origin, horizon_days, **kw)

    M.fit = spy
    try:
        result = BT.run(reg, cats=["PROPERTY"], log=lambda *_: None)
    finally:
        M.fit = real_fit
    result["_fits"] = seen
    return result


def test_no_refit_sees_its_future(bt):
    assert bt["_fits"]
    for history_end, last_origin, h in bt["_fits"]:
        # the latest training/calibration target ends on or before the refit's as-of week
        assert last_origin + h <= history_end


def test_window_and_refits(bt):
    w = bt["window"]
    assert w["first_target_week"] == "2023-10-02"
    assert w["last_target_week"] == "2024-03-04"
    assert w["refits"] == -(-w["origins"] // w["refit_every_weeks"])


@pytest.mark.parametrize("ut", ["station", "beat"])
@pytest.mark.parametrize("hd", ["7", "28"])
def test_scores_are_sane(bt, ut, hd):
    m = bt["results"][ut]["PROPERTY"][hd]
    assert m["events"] > 0 and m["origins"] > 0
    for k, c in m["capture"].items():
        # the ceiling bounds every ranking
        assert c["oracle"] >= max(c["model"], c["last4"], c["last52w"]) - 1e-9, k
        assert 0 <= c["model"] <= 1
    for k, p in m["pai"].items():
        assert p["oracle"]["hit"] >= p["model"]["hit"] - 1e-9
        assert 0 < p["model"]["area"] <= 1
    assert 0.8 <= m["calibration"] <= 1.25
    assert m["coverage"]["90"]["coverage"] >= 0.8
    assert m["coverage"]["80"]["coverage"] <= m["coverage"]["90"]["coverage"]


def test_the_model_ranks_better_than_last_weeks_hotspots(bt):
    """On stable true rates, last-4-weeks counts are mostly noise; the model is not."""
    c = bt["results"]["beat"]["PROPERTY"]["7"]["capture"]["top_10pct"]
    assert c["model"] >= c["last4"]


def test_all_crime_is_scored_even_when_not_asked_for(bt):
    # ALL defines which units were active; it is loaded but only reported when asked
    assert "ALL" not in bt["results"]["beat"]


def test_save_load_and_report(reg, bt, tmp_path):
    clean = {k: v for k, v in bt.items() if not k.startswith("_")}
    BT.save(reg, clean)
    assert BT.load(reg)["built_at"] == clean["built_at"]
    path = report.write(clean, str(tmp_path / "r.md"))
    text = open(path, encoding="utf-8").read()
    assert "Do not edit by hand" in text and "Property Crimes" in text


# ── the scorecard ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ut", ["station", "beat"])
def test_weekly_ledger_is_the_backtest_week_by_week(bt, ut):
    from datetime import date
    m = bt["results"][ut]["PROPERTY"]["7"]
    wk = [date.fromisoformat(r["week"]) for r in m["weekly"]]
    assert len(wk) == m["origins"]
    assert wk[0].isoformat() == bt["window"]["first_target_week"]
    assert wk[-1].isoformat() == bt["window"]["last_target_week"]
    assert all((b - a).days == 7 for a, b in zip(wk, wk[1:]))
    # the ledger and the headline calibration are the same sums, so they cannot disagree
    fc, ac = sum(r["forecast"] for r in m["weekly"]), sum(r["actual"] for r in m["weekly"])
    assert fc / ac == pytest.approx(m["calibration"], abs=0.01)
    assert "weekly" not in bt["results"][ut]["PROPERTY"]["28"]


def test_scorecard_numbers_are_the_backtest_numbers(reg, bt, monkeypatch):
    from app.forecast import service as S
    # S.backtest caches for 5 minutes; without this the next test file would be served
    # this synthetic registry's back-test as if it were the real one.
    monkeypatch.setitem(S._bt_cache, "value", None)
    monkeypatch.setitem(S._bt_cache, "at", 0.0)
    BT.save(reg, {k: v for k, v in bt.items() if not k.startswith("_")})
    sc = S.scorecard(reg, unit_type="beat", category="theft")
    c5 = bt["results"]["beat"]["PROPERTY"]["7"]["capture"]["top_5pct"]
    assert sc["category"] == "PROPERTY" and sc["evidence_class"] == "D"
    assert sc["summary"]["weeks_better_than_last4"] == c5["model_beats_last4_weeks"]
    assert sc["summary"]["weeks_ranked"] == c5["weeks"]
    assert f"{sc['summary']['actual_total']:,} recorded" in sc["text"]
    assert all(r["error"] == pytest.approx(r["forecast"] - r["actual"], abs=0.06) for r in sc["weeks"])
    # an ungraded category is refused as not ready, never answered with another's record
    with pytest.raises(S.NotReady):
        S.scorecard(reg, unit_type="beat", category="murder")


# ── the model card ───────────────────────────────────────────────────────────

def test_card_says_not_measured_without_a_backtest():
    con = _registry(seed=3)
    try:
        c = card.build(con)
        assert c["accuracy"] is None
        assert any("not yet measured" in e for e in c["evaluation"])
        assert "DBSCAN" not in c["architecture"] and "CCTNS live replica" not in c["data_provenance"]
    finally:
        con.close()


def test_card_numbers_are_the_backtest_numbers(reg):
    """The card can never drift from the back-test: it is read from it."""
    full = BT.run(reg, cats=["ALL", "PROPERTY"], log=lambda *_: None)
    BT.save(reg, full)
    c = card.build(reg)
    beat = full["headline"]["beat.ALL"]
    assert c["accuracy"]["beat_all_7d"] == beat
    assert c["accuracy"]["measured_at"] == full["built_at"]
    text = " ".join(c["evaluation"])
    assert f"{100 * beat['top5_caught']:.1f}%" in text
    assert f"{beat['pai5']:.1f}" in text
    assert c["evidence_class"] == "I"


def test_card_discloses_seeded_history_and_fallbacks(reg):
    a = run.asof_mod.resolve(reg, "2024-03-10")
    run.compute(reg, a, cats=["PROPERTY", "MURDER"])
    c = card.build(reg, today=a.as_of)
    assert any("baseline" in b and "Murder" in b for b in c["bias_disclosure"])
    assert "real record" in c["data_provenance"]
