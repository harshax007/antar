"""
Tests for Layer 2: UNSUB Profiles, Predicted Edges, and Knowledge Boundary Index.
"""
from app.services.patterns import find_unsubs
from app.services.graph_cache import refresh as refresh_graph, get_node_metrics
from app.agents.network_agent import build_network


def test_find_unsubs_discovers_serial_clusters():
    unsubs = find_unsubs()
    assert len(unsubs) > 0
    u0 = unsubs[0]
    assert u0["id"].startswith("UNSUB-")
    assert "mo_signature" in u0
    assert u0["knowledge_boundary"] == 1.0
    assert u0["case_count"] >= 3
    assert len(u0["case_ids"]) == u0["case_count"]


def test_graph_cache_contains_layer2_products():
    cache = refresh_graph()
    assert "unsubs" in cache
    assert "predicted_edges" in cache
    assert "knowledge_boundaries" in cache
    assert len(cache["unsubs"]) > 0
    # Test individual node lookup has knowledge_boundary
    nm = get_node_metrics("S0001")
    assert "knowledge_boundary" in nm
    assert 0.0 <= nm["knowledge_boundary"] <= 1.0


def test_build_network_includes_layer2_fields():
    net = build_network("S0001")
    assert "nodes" in net
    assert len(net["nodes"]) > 0
    for n in net["nodes"]:
        assert "knowledge_boundary" in n
    assert "predicted_edges" in net
    assert "unsubs" in net
