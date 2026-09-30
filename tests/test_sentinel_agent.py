"""
Phase 1 Acceptance Tests: A1 Sentinel Agent (Watchlists & Tripwires)
====================================================================
Verifies that:
  • Watchlists can be listed and registered
  • Scanning watchlists triggers deterministic watchhit products and alerts
  • /api/sentinel/watches and /api/sentinel/scan return expected shapes
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.agents import sentinel_agent
from app.services import alerts_store, product_store


class TestSentinelAgent:
    def test_list_and_register_watch(self):
        initial = len(sentinel_agent.list_watches())
        watch = sentinel_agent.register_watch(
            watch_type="zone",
            target="Indiranagar",
            label="Test Watch: Indiranagar",
            officer_id="TestOfficer"
        )
        assert watch["watch_id"].startswith("W-")
        assert len(sentinel_agent.list_watches()) == initial + 1
        assert len(sentinel_agent.list_watches(officer_id="TestOfficer")) >= 1

    def test_scan_watches_generates_hits(self):
        hits = sentinel_agent.scan_watches()
        assert len(hits) >= 1
        hit = hits[0]
        assert "hit_id" in hit
        assert "evidence_rows" in hit
        assert hit["provenance"]["agent"] == "A1: Sentinel Watchdog"
        
        # Check alerts store received the tripwire alert
        recent_alerts = alerts_store.list_recent(limit=10)
        assert any(a.get("alert_type") == "sentinel_tripwire" for a in recent_alerts)


class TestSentinelEndpoints:
    @pytest.mark.anyio
    async def test_get_watches_endpoint(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get("/api/sentinel/watches")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert isinstance(data["watches"], list)

    @pytest.mark.anyio
    async def test_run_scan_endpoint(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.post("/api/sentinel/scan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["hits_detected"] >= 1
