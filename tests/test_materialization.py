"""
Task 5: Materialized graph metrics + district aggregates.
Tests cover:
  • graph_cache: refresh, get_cache, get_node_metrics, content contract
  • district_cache: refresh, get_all, get_district, content contract
  • network_agent: build_network reads from cache (betweenness + is_broker in payload)
  • HTTP endpoints: /api/graph/stats, /api/map/district/{zone}, /api/map/districts/rich
"""

import pytest
from app.services import graph_cache, district_cache
from app.agents.network_agent import build_network


# ── graph_cache ───────────────────────────────────────────────────────────────

class TestGraphCache:
    def test_refresh_returns_dict(self):
        c = graph_cache.refresh()
        assert isinstance(c, dict)

    def test_required_keys_present(self):
        c = graph_cache.get_cache()
        for key in ("pagerank", "betweenness", "community_map",
                    "community_count", "stats", "refreshed_at"):
            assert key in c, f"missing key: {key}"

    def test_stats_keys_present(self):
        stats = graph_cache.get_cache()["stats"]
        for key in ("node_count", "edge_count", "community_count",
                    "top_boss", "top_broker"):
            assert key in stats, f"stats missing: {key}"

    def test_node_count_positive(self):
        stats = graph_cache.get_cache()["stats"]
        assert stats["node_count"] > 0

    def test_community_count_positive(self):
        c = graph_cache.get_cache()
        assert c["community_count"] >= 1

    def test_top_boss_has_name_and_score(self):
        boss = graph_cache.get_cache()["stats"]["top_boss"]
        assert boss is not None
        assert boss["name"]
        assert boss["pagerank"] >= 0

    def test_top_broker_has_name_and_score(self):
        broker = graph_cache.get_cache()["stats"]["top_broker"]
        assert broker is not None
        assert broker["name"]
        assert broker["betweenness"] >= 0

    def test_pagerank_sums_to_approx_one(self):
        pr = graph_cache.get_cache()["pagerank"]
        total = sum(pr.values())
        assert abs(total - 1.0) < 0.01, f"PageRank sum {total:.4f} not ≈ 1"

    def test_betweenness_values_in_0_1(self):
        bt = graph_cache.get_cache()["betweenness"]
        for sid, v in bt.items():
            assert 0.0 <= v <= 1.0, f"{sid} betweenness {v} out of [0,1]"

    def test_get_node_metrics_known_node(self):
        cache = graph_cache.get_cache()
        some_id = next(iter(cache["pagerank"]))
        m = graph_cache.get_node_metrics(some_id)
        for key in ("pagerank", "betweenness", "community", "community_count",
                    "is_boss", "is_broker"):
            assert key in m, f"get_node_metrics missing: {key}"

    def test_get_node_metrics_unknown_node(self):
        m = graph_cache.get_node_metrics("UNKNOWN_XYZ")
        assert m["pagerank"] == 0.0
        assert m["betweenness"] == 0.0
        assert m["is_boss"] is False
        assert m["is_broker"] is False

    def test_lazy_init_works(self):
        graph_cache._cache = None
        c = graph_cache.get_cache()
        assert c is not None
        assert "pagerank" in c


# ── district_cache ────────────────────────────────────────────────────────────

class TestDistrictCache:
    def test_refresh_returns_dict(self):
        d = district_cache.refresh()
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_get_all_returns_list(self):
        rows = district_cache.get_all()
        assert isinstance(rows, list)
        assert len(rows) > 0

    def test_each_district_has_required_fields(self):
        required = {"zone", "fir_count", "this_month", "prior_month",
                    "top_crimes", "risk_level", "trend", "predicted"}
        for row in district_cache.get_all():
            missing = required - set(row.keys())
            assert not missing, f"{row['zone']} missing fields: {missing}"

    def test_risk_level_valid_values(self):
        valid = {"High", "Medium", "Low"}
        for row in district_cache.get_all():
            assert row["risk_level"] in valid, \
                f"{row['zone']} has invalid risk_level: {row['risk_level']}"

    def test_trend_format(self):
        for row in district_cache.get_all():
            t = row["trend"]
            assert t == "—" or t.startswith("+") or t.startswith("-"), \
                f"Bad trend format: {t}"

    def test_predicted_non_negative(self):
        for row in district_cache.get_all():
            assert row["predicted"] >= 0

    def test_top_crimes_is_list(self):
        for row in district_cache.get_all():
            assert isinstance(row["top_crimes"], list)

    def test_get_district_known_zone(self):
        zones = [r["zone"] for r in district_cache.get_all()]
        if zones:
            data = district_cache.get_district(zones[0])
            assert data is not None
            assert data["zone"] == zones[0]

    def test_get_district_unknown_returns_none(self):
        result = district_cache.get_district("Nonexistent Zone XYZ")
        assert result is None

    def test_lazy_init_works(self):
        district_cache._cache = None
        rows = district_cache.get_all()
        assert len(rows) > 0


# ── network_agent uses cache ──────────────────────────────────────────────────

class TestNetworkAgentUsesCache:
    def _get_seed(self):
        from app.services.zcql_local import _world
        return _world()["suspects"][0]["suspect_id"]

    def test_nodes_have_betweenness(self):
        seed = self._get_seed()
        result = build_network(seed)
        for node in result["nodes"]:
            assert "betweenness" in node, f"node {node['id']} missing betweenness"
            assert 0.0 <= node["betweenness"] <= 1.0

    def test_nodes_have_is_broker(self):
        seed = self._get_seed()
        result = build_network(seed)
        for node in result["nodes"]:
            assert "is_broker" in node
            assert isinstance(node["is_broker"], bool)

    def test_broker_flag_consistent_with_cache(self):
        """Exactly one node in the cache is the broker — verify flag is consistent."""
        seed = self._get_seed()
        result = build_network(seed)
        broker_id = graph_cache.get_cache()["stats"]["top_broker"]["id"]
        broker_nodes = [n for n in result["nodes"] if n["is_broker"]]
        # The broker may or may not be in the 2-hop subgraph, but if present it must be flagged.
        for n in broker_nodes:
            assert n["id"] == broker_id

    def test_community_from_cache(self):
        seed = self._get_seed()
        result = build_network(seed)
        cache_community_map = graph_cache.get_cache()["community_map"]
        for node in result["nodes"]:
            expected = cache_community_map.get(node["id"], 0)
            assert node["community"] == expected, \
                f"{node['id']}: community {node['community']} != cache {expected}"

    def test_centrality_from_cache(self):
        seed = self._get_seed()
        result = build_network(seed)
        cache_pr = graph_cache.get_cache()["pagerank"]
        for node in result["nodes"]:
            expected = round(cache_pr.get(node["id"], 0.0), 4)
            assert node["centrality"] == expected, \
                f"{node['id']}: centrality mismatch"


# ── HTTP endpoints ────────────────────────────────────────────────────────────

class TestMaterializationEndpoints:
    @pytest.mark.anyio
    async def test_graph_stats_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        from main import app as fastapi_app
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/graph/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["node_count"] > 0
        assert data["community_count"] >= 1
        assert data["top_boss"] is not None
        assert data["top_broker"] is not None

    @pytest.mark.anyio
    async def test_districts_rich_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        from main import app as fastapi_app
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/map/districts/rich")
        assert resp.status_code == 200
        data = resp.json()
        assert "districts" in data
        assert data["total"] > 0

    @pytest.mark.anyio
    async def test_district_detail_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        from main import app as fastapi_app
        zones = [r["zone"] for r in district_cache.get_all()]
        zone = zones[0]
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/map/district/{zone}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["zone"] == zone
        assert "risk_level" in data
        assert "top_crimes" in data

    @pytest.mark.anyio
    async def test_district_detail_404_unknown(self):
        from httpx import AsyncClient, ASGITransport
        from main import app as fastapi_app
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/map/district/NoSuchZone_XYZ_999")
        assert resp.status_code == 404
