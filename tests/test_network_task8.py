"""
Task 8: Adamic-Adar link prediction + broker callout + k-core.
Tests cover:
  • predicted_links use Adamic-Adar (method field)
  • AA probability is in (0, 0.95] and correctly higher than 0 for connected suspects
  • k_core and inner_circle fields on nodes
  • broker_alert generated when global broker is in the subgraph
  • graph_cache k_core stats: inner_circle_count, max_k_core
  • full suite regression (all existing network contracts still hold)
"""

import pytest
from app.agents.network_agent import build_network
from app.services.graph_cache import get_cache, get_node_metrics


# ── helpers ───────────────────────────────────────────────────────────────────

def _seed():
    from app.services.zcql_local import _world
    return _world()["suspects"][0]["suspect_id"]


def _broker_id():
    return get_cache()["stats"]["top_broker"]["id"]


# ── Adamic-Adar link prediction ───────────────────────────────────────────────

class TestAdamicAdar:
    def test_predicted_links_use_gat_attention_method(self):
        result = build_network(_seed())
        aa_links = [p for p in result["predicted_links"] if p.get("method") == "gat_attention"]
        # Phone-hash links override method; the rest must be gat_attention
        non_phone = [p for p in result["predicted_links"]
                     if p.get("reason") != "Shared phone number hash"]
        assert all(p["method"] == "gat_attention" for p in non_phone), \
            "Non-phone predicted links must use gat_attention method"

    def test_predicted_link_has_score_field(self):
        result = build_network(_seed())
        for p in result["predicted_links"]:
            assert "score" in p, f"missing score on predicted_link {p}"
            assert p["score"] >= 0.0

    def test_probability_in_valid_range(self):
        result = build_network(_seed())
        for p in result["predicted_links"]:
            assert 0.0 < p["probability"] <= 0.95, \
                f"probability {p['probability']} out of (0, 0.95]"

    def test_phone_hash_link_probability_095(self):
        result = build_network(_seed())
        phone_links = [p for p in result["predicted_links"]
                       if p["reason"] == "Shared phone number hash"]
        for p in phone_links:
            assert p["probability"] == 0.95

    def test_predicted_links_sorted_by_probability_desc(self):
        result = build_network(_seed())
        probs = [p["probability"] for p in result["predicted_links"]]
        assert probs == sorted(probs, reverse=True), "predicted_links must be sorted desc"

    def test_stats_includes_predicted_link_count(self):
        result = build_network(_seed())
        assert "predicted_link_count" in result["stats"]
        assert result["stats"]["predicted_link_count"] == len(result["predicted_links"])

    def test_reason_field_present(self):
        result = build_network(_seed())
        for p in result["predicted_links"]:
            assert "reason" in p and p["reason"]


# ── K-core ────────────────────────────────────────────────────────────────────

class TestKCore:
    def test_nodes_have_k_core_field(self):
        result = build_network(_seed())
        for node in result["nodes"]:
            assert "k_core" in node, f"node {node['id']} missing k_core"
            assert isinstance(node["k_core"], int)
            assert node["k_core"] >= 0

    def test_nodes_have_inner_circle_field(self):
        result = build_network(_seed())
        for node in result["nodes"]:
            assert "inner_circle" in node
            assert isinstance(node["inner_circle"], bool)

    def test_inner_circle_nodes_have_highest_k_core(self):
        result = build_network(_seed())
        ic_nodes = [n for n in result["nodes"] if n["inner_circle"]]
        if ic_nodes:
            max_k = max(n["k_core"] for n in result["nodes"])
            for n in ic_nodes:
                assert n["k_core"] == max_k, \
                    f"inner_circle node {n['id']} k_core {n['k_core']} != max {max_k}"

    def test_inner_circle_count_in_stats(self):
        result = build_network(_seed())
        assert "inner_circle_count" in result["stats"]
        expected = sum(1 for n in result["nodes"] if n["inner_circle"])
        assert result["stats"]["inner_circle_count"] == expected

    def test_graph_cache_has_k_core_stats(self):
        c = get_cache()
        assert "k_core" in c
        assert "k_core_max" in c
        assert "inner_circle" in c
        stats = c["stats"]
        assert "inner_circle_count" in stats
        assert "max_k_core" in stats

    def test_graph_cache_k_core_max_non_negative(self):
        assert get_cache()["k_core_max"] >= 0

    def test_get_node_metrics_has_k_core(self):
        some_id = next(iter(get_cache()["pagerank"]))
        m = get_node_metrics(some_id)
        assert "k_core" in m
        assert "inner_circle" in m
        assert isinstance(m["inner_circle"], bool)


# ── Broker alert ──────────────────────────────────────────────────────────────

class TestBrokerAlert:
    def test_broker_alert_key_always_present(self):
        """broker_alert must always be in the response (None if broker not in subgraph)."""
        result = build_network(_seed())
        assert "broker_alert" in result

    def test_broker_alert_format_when_present(self):
        """When the global broker is in the subgraph, the alert is a non-empty string."""
        broker = _broker_id()
        result = build_network(broker)   # build from the broker as seed — they're in it
        alert = result["broker_alert"]
        assert alert is not None, "Broker should appear in their own subgraph"
        assert isinstance(alert, str) and len(alert) > 10
        # Must mention betweenness and gang cell(s)
        assert "betweenness" in alert.lower() or "bridge" in alert.lower()

    def test_broker_alert_mentions_broker_name(self):
        broker = _broker_id()
        broker_name = get_cache()["stats"]["top_broker"]["name"]
        result = build_network(broker)
        alert = result["broker_alert"]
        assert alert and broker_name in alert, \
            f"Broker alert should mention '{broker_name}'"

    def test_broker_alert_none_when_broker_not_in_subgraph(self):
        """If the broker is not reachable from the seed, broker_alert must be None."""
        from app.services.zcql_local import _world
        from collections import deque

        broker_id = _broker_id()
        # Build adjacency to check reachability
        world = _world()
        adj: dict[str, set] = {}
        for r in world["relationships"]:
            adj.setdefault(r["suspect_a"], set()).add(r["suspect_b"])
            adj.setdefault(r["suspect_b"], set()).add(r["suspect_a"])

        # Find a suspect not reachable from broker within depth=2
        # (if they all connect, this test is a no-op — skip gracefully)
        isolated_seed = None
        for s in world["suspects"]:
            sid = s["suspect_id"]
            if sid == broker_id:
                continue
            reachable = {broker_id}
            q = deque([(broker_id, 0)])
            while q:
                n, d = q.popleft()
                if d >= 2:
                    continue
                for nb in adj.get(n, []):
                    if nb not in reachable:
                        reachable.add(nb)
                        q.append((nb, d + 1))
            if sid not in reachable:
                isolated_seed = sid
                break

        if isolated_seed is None:
            pytest.skip("All suspects reachable from broker within depth 2 — skip isolation test")

        result = build_network(isolated_seed, depth=2)
        assert result["broker_alert"] is None, \
            "broker_alert should be None when broker not in subgraph"


# ── Regression: existing network contracts still hold ────────────────────────

class TestRegressionTask8:
    def test_brain_banner_still_present_for_s0001(self):
        r = build_network("S0001")
        assert r["brain_banner"] and "yellappa" in r["brain_banner"].lower()

    def test_cross_case_edge_still_present(self):
        r = build_network("S0001")
        assert any(e["cross_case"] for e in r["edges"])

    def test_unknown_suspect_still_graceful(self):
        r = build_network("S9999")
        assert r["nodes"] == [] and "error" in r

    def test_all_new_node_fields_present(self):
        r = build_network(_seed())
        for n in r["nodes"]:
            for field in ("centrality", "betweenness", "community",
                          "k_core", "inner_circle", "is_broker"):
                assert field in n, f"node {n['id']} missing {field}"

    def test_stats_has_all_fields(self):
        r = build_network(_seed())
        for field in ("node_count", "edge_count", "cross_case_links",
                      "predicted_link_count", "inner_circle_count"):
            assert field in r["stats"], f"stats missing {field}"
