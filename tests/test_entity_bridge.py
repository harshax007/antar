"""
Phase P0 Acceptance Tests: Entity Bridge & Cross-World Unification
==================================================================
Verifies that:
  • entity_bridge.get_bridge() maps seed suspects and evidence ledger accused to canonical IDs
  • entity_bridge.search_all() returns hits across both data worlds
  • /api/profile/search?q=ACC-... resolves evidence entities with risk scores
  • /api/profile/{accused_id} returns a valid 4-factor profile for evidence entities
  • /api/graph/{accused_id} returns a valid cross-world bridge graph
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.services import entity_bridge, evidence_ledger


class TestEntityBridgeService:
    def test_get_bridge_contains_both_worlds(self):
        bridge = entity_bridge.get_bridge()
        assert len(bridge) > 100
        sources = {r["source"] for r in bridge}
        assert "seed" in sources, "seed suspects missing from bridge"
        assert "evidence" in sources, "evidence ledger accused missing from bridge"

    def test_search_all_seed_hit(self):
        hits = entity_bridge.search_all("Yellappa")
        assert any(h.get("source") == "seed" for h in hits)

    def test_search_all_evidence_hit(self):
        hits = entity_bridge.search_all("ACC-", limit=5)
        assert len(hits) > 0
        for h in hits:
            assert h["source"] == "evidence"
            assert h["match_method"] == "evidence_ledger"
            assert 0 <= (h["risk_score"] or 0) <= 100


class TestEntityBridgeEndpoints:
    @pytest.mark.anyio
    async def test_bridge_endpoint_200(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get("/api/profile/bridge")
        assert resp.status_code == 200
        data = resp.json()
        assert "bridge" in data and data["count"] > 100

    @pytest.mark.anyio
    async def test_profile_search_evidence_200(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get("/api/profile/search?q=ACC-&limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0
        assert any(h["source"] == "evidence" for h in data["hits"])

    @pytest.mark.anyio
    async def test_profile_detail_evidence_200(self):
        from main import app as fastapi_app
        aid = evidence_ledger.search("ACC-", limit=1)[0]["accused_id"]
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get(f"/api/profile/{aid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["suspect_id"] == aid
        assert "risk_score" in data
        assert "factors" in data
        assert "mo_summary" in data
        assert data.get("source") == "evidence"

    @pytest.mark.anyio
    async def test_graph_detail_evidence_200(self):
        from main import app as fastapi_app
        aid = evidence_ledger.search("ACC-", limit=1)[0]["accused_id"]
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get(f"/api/graph/{aid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data and len(data["nodes"]) >= 1
        assert "edges" in data
        assert "Cross-World Evidence Bridge" in str(data.get("brain_banner", ""))
