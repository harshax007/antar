"""
Prediction policy tests:
  1. PRIVACY — no future calendar date ever leaves a prediction endpoint
     (future-date compute is internal-only; relative windows are allowed).
  2. COVERAGE — the board covers every zone with assessable data, not one city.
  3. ROLLING DATE — as_of is today's date; recomputed per request.
"""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.date_guard import find_future_dates, redact_future_dates


class TestDateGuard:
    def test_finds_future_dates(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        assert find_future_dates({"a": [f"window {future}"]}) == [future]

    def test_ignores_past_and_today(self):
        past = (date.today() - timedelta(days=5)).isoformat()
        assert find_future_dates({"a": past, "b": date.today().isoformat()}) == []

    def test_redacts_bare_future_date(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        assert redact_future_dates({"forecast_date": future}) == {"forecast_date": None}

    def test_redacts_embedded_future_date(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        out = redact_future_dates({"label": f"week ending {future}"})
        assert out == {"label": "week ending upcoming"}

    def test_preserves_everything_else(self):
        payload = {"risk": "HIGH", "band": "8-11 incidents", "window": "next 7 days",
                   "n": 3, "past": "2025-01-01"}
        assert redact_future_dates(payload) == payload


@pytest.fixture(scope="module")
def board():
    from app.api.pattern_predict import compile_board
    return compile_board(0)


class TestBoard:
    def test_no_future_dates_anywhere(self, board):
        assert find_future_dates(board) == []

    def test_full_zone_coverage(self, board):
        zones = {c["zone"] for c in board["predictions"]}
        assert len(zones) >= 20, f"only {len(zones)} zones covered"
        assert board["zones_covered"] == len(zones)

    def test_as_of_is_today_and_rolls(self, board):
        assert board["as_of"] == date.today().isoformat()
        assert all(c["as_of"] == board["as_of"] for c in board["predictions"])

    def test_windows_are_relative_not_dated(self, board):
        for c in board["predictions"]:
            assert c["window"] == "next 7 days"

    def test_ranked_high_first(self, board):
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        ranks = [order[c["risk"]] for c in board["predictions"]]
        assert ranks == sorted(ranks)

    def test_limit_respected(self):
        from app.api.pattern_predict import compile_board
        assert len(compile_board(5)["predictions"]) == 5

    def test_board_product_registered_for_autonomous_refresh(self):
        from app.services import product_store
        product_store.setup_default_products()
        assert "warning_ledger:board:all" in product_store._generators
        cached = product_store.get_product("warning_ledger:board:all")
        assert cached and cached["as_of"] == date.today().isoformat()


class TestEndpoints:
    @pytest.mark.anyio
    async def test_forecast_endpoint_has_no_future_dates(self):
        from main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/analytics/forecast",
                                 params={"crime_type": "theft", "zone": "Bengaluru City"})
        assert r.status_code == 200
        assert find_future_dates(r.json()) == []

    @pytest.mark.anyio
    async def test_board_endpoint_has_no_future_dates(self):
        from main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/predict/board", params={"limit": 10})
        assert r.status_code == 200
        body = r.json()
        assert find_future_dates(body) == []
        assert body["as_of"] == date.today().isoformat()

    @pytest.mark.anyio
    async def test_scenario_endpoint_has_no_future_dates(self):
        from main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/predict/Bengaluru%20City/scenario")
        assert r.status_code == 200
        assert find_future_dates(r.json()) == []
