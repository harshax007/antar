"""How the engine behaves overall (service.global_explanation): computed from the stored
forecasts and the stored back-test, with its own weak spots listed."""
import sqlite3

import pytest

from app.forecast import service as S


@pytest.fixture(scope="module")
def g():
    from app.core.db_path import DB_PATH
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        return S.global_explanation(conn)
    except (sqlite3.Error, S.NotReady):
        pytest.skip("no forecast store in this database")


def test_every_category_lists_all_six_reasons_largest_first(g):
    assert g["categories"], "no category had enough history"
    for c in g["categories"]:
        keys = [r["key"] for r in c["reasons"]]
        assert set(keys) == set(S._WHY_KEYS) and c["main_reason"] == keys[0]
        moves = [r["typical_move"] for r in c["reasons"]]
        assert moves == sorted(moves, reverse=True) and all(m >= 0 for m in moves)
        assert all(0 <= r["share_notable"] <= 1 for r in c["reasons"])


def test_the_back_test_figures_are_the_stored_ones_not_typed(g):
    conn = sqlite3.connect(f"file:{__import__('app.core.db_path', fromlist=['DB_PATH']).DB_PATH}?mode=ro", uri=True)
    allc = next(c for c in g["categories"] if c["category"] == S.ALL)
    acc = S.accuracy(conn, "station", S.ALL, 7)
    assert allc["backtest"]["coverage80"] == acc["coverage80"]
    assert allc["backtest"]["weeks_better_than_last4"] == acc["weeks_better_than_last4"]


def test_it_names_its_own_weak_spots(g):
    weak = {w["category"]: w["why"] for w in g["weakest"]}
    for c in g["categories"]:
        b = c["backtest"]
        if b and b.get("calibration") is not None and abs(b["calibration"] - 1) >= 0.10:
            assert c["category"] in weak and any("forecasts ran" in x for x in weak[c["category"]])
        if b and b["weeks_better_than_last4"] <= 0.65 * b["weeks"]:
            assert c["category"] in weak


def test_it_says_what_it_does_not_use(g):
    text = " ".join(g["not_used"]).lower()
    for word in ("caste", "religion", "time of day", "language model"):
        assert word in text
    assert g["evidence_class"] == "D"
