"""
Predict dashboard cards — GET /api/predict/dashboard (monthly aggregation).

Covers:
  • 200 + top-level contract (as_of, activity, volume)
  • activity matrix rows align with tactics, cols align with months
  • volume series points carry {label, value}; latest/prev are ints
  • query params clamped (months 3..12, top 1..8, trend_months ≥ 4)
  • as_of is never a future date (future-dated seed rows excluded)
"""

import pytest
from httpx import AsyncClient, ASGITransport


async def _get(path: str):
    from main import app as fastapi_app
    async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                           base_url="http://test") as c:
        return await c.get(path)


class TestPredictDashboard:
    @pytest.mark.anyio
    async def test_200_and_contract(self):
        resp = await _get("/api/predict/dashboard")
        assert resp.status_code == 200
        d = resp.json()
        assert {"as_of", "activity", "volume"} <= set(d)

        act = d["activity"]
        assert {"tactics", "months", "matrix", "max"} <= set(act)
        assert isinstance(act["tactics"], list)
        assert isinstance(act["months"], list)
        # one matrix row per tactic, one cell per month
        assert len(act["matrix"]) == len(act["tactics"])
        for row in act["matrix"]:
            assert len(row) == len(act["months"])
            assert all(isinstance(v, int) and v >= 0 for v in row)
        assert act["max"] >= 0

        vol = d["volume"]
        assert {"month", "year"} <= set(vol)
        for gran in ("month", "year"):
            g = vol[gran]
            assert {"series", "latest", "prev", "delta_pct", "direction", "peak", "total", "avg", "unit"} <= set(g)
            assert isinstance(g["latest"], int)
            assert isinstance(g["prev"], int)
            for p in g["series"]:
                assert {"label", "key", "value", "partial"} <= set(p)
                assert isinstance(p["value"], int) and p["value"] >= 0
        # year series is chronological and flags the in-progress (YTD) year
        yrs = [p["key"] for p in vol["year"]["series"]]
        assert yrs == sorted(yrs)

    @pytest.mark.anyio
    async def test_params_clamped(self):
        resp = await _get("/api/predict/dashboard?months=99&trend_months=1&top=99")
        assert resp.status_code == 200
        d = resp.json()
        assert len(d["activity"]["months"]) <= 12
        assert len(d["activity"]["tactics"]) <= 8
        assert len(d["volume"]["month"]["series"]) >= 1

    @pytest.mark.anyio
    async def test_as_of_not_future(self):
        from datetime import date
        resp = await _get("/api/predict/dashboard")
        d = resp.json()
        assert d["as_of"] <= date.today().isoformat()
