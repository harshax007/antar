"""
Phase 1 Acceptance Tests: A4 Shift Briefings & Compiled Intelligence
====================================================================
Verifies that:
  • /api/briefing/shift returns strict JSON matching the required schema
  • Repeat hits respond in < 30 ms from Product Store
  • Invalidation clears cached shift briefings
"""

import time
import pytest
from httpx import AsyncClient, ASGITransport

from app.agents import briefing_agent
from app.services import product_store


class TestBriefingAgent:
    def test_generate_shift_briefing_schema(self):
        res = briefing_agent.generate_shift_briefing(zone="all", window="12h")
        assert res["zone"] == "All Districts"
        assert res["window_hours"] == 12
        assert "generated_at" in res
        assert "executive_summary" in res and len(res["executive_summary"]) > 20
        assert isinstance(res["priority_actions"], list) and len(res["priority_actions"]) >= 1
        assert isinstance(res["key_incidents"], list)
        assert res["active_beacons"] >= 1

    def test_caching_and_repeat_latency_under_30ms(self):
        product_store.invalidate("briefing:shift:")
        
        t0 = time.perf_counter()
        res1 = briefing_agent.get_shift_briefing("Koramangala", "12h")
        _ = (time.perf_counter() - t0) * 1000
        
        t1 = time.perf_counter()
        res2 = briefing_agent.get_shift_briefing("Koramangala", "12h")
        dt2 = (time.perf_counter() - t1) * 1000
        
        assert res1["generated_at"] == res2["generated_at"]
        assert dt2 < 30.0, f"Repeat hit took {dt2:.2f} ms, expected < 30 ms"

    def test_invalidation_triggers_new_generation(self):
        res1 = briefing_agent.get_shift_briefing("Indiranagar", "24h")
        product_store.invalidate("briefing:shift:")
        res2 = briefing_agent.get_shift_briefing("Indiranagar", "24h")
        # generated_at or memory reference should update after invalidation
        assert res1 is not res2


class TestBriefingEndpoints:
    @pytest.mark.anyio
    async def test_briefing_shift_endpoint_200(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get("/api/briefing/shift?zone=all&window=12h")
        assert resp.status_code == 200
        data = resp.json()
        assert "executive_summary" in data
        assert "priority_actions" in data
        assert data["window_hours"] == 12
