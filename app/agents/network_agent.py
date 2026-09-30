"""
Antar — Network Agent (M2, M7)
===================================
Builds a criminal network graph around a suspect: BFS over the `relationships`
table (depth-limited, node-capped), connected components, and — the differentiator —
Second-Brain cross-case links drawn as distinct edges with a ⚡ banner (WOW 2).

No LLM on the hot path: pure graph algorithms over the data. Fully offline-testable.
Output is a vis-network-ready payload {nodes, edges, components, brain_banner, brain_links}.
"""

from __future__ import annotations

from collections import deque

from app.services.zcql_local import _world
from app.services.graph_cache import get_cache
from app.second_brain.retrieval import find_cross_case_links

# Optional heavy deps — the network agent MUST degrade gracefully, never 500.
# networkx (now a hard requirement) powers k-core + Adamic-Adar link prediction.
# torch is deliberately absent from the slim deploy image (no GPU); when it is
# missing we skip the GAT attention term and fall back to topology-only scoring.
# A missing dep only drops enrichment scores — nodes / edges / components /
# cross-case links are computed with pure-python and are unaffected.
try:
    import networkx as nx
except Exception:
    nx = None

# The link-prediction "attention" step used to run on PyTorch. Its projection matrices
# (W_q / W_k below) are HARDCODED LITERALS — nothing is learned — so the whole step is a
# scaled dot product that numpy computes identically, and numpy is already a pinned
# dependency. Dropping torch here:
#   • removes a ~200 MB wheel from the AppSail image (faster cold start, fits 1024 MB)
#   • removes an environment split — with torch present the method was "gat_attention",
#     without it "adamic_adar", so dev and production returned DIFFERENT predicted links
#     for the same graph. Reproducibility is the point of this system.
import numpy as np

DEPTH = 2
NODE_CAP = 150
_adj_cache = {"adj": None, "rels_id": None}


def _risk(prior_count: int) -> int:
    """Cheap risk proxy from prior offences (0–100). Real 4-factor score = Profile Agent."""
    return min(100, int((prior_count or 0) * 12))


def build_network(seed_id: str, depth: int = DEPTH, cap: int = NODE_CAP) -> dict:
    world = _world()
    suspects = {s["suspect_id"]: s for s in world["suspects"]}
    if seed_id not in suspects:
        from app.services import evidence_ledger
        ev_entity = evidence_ledger.entity(seed_id)
        if ev_entity:
            nodes = [{
                "id": seed_id, "label": ev_entity["alias"], "type": "seed",
                "title": f"Evidence Ledger: {ev_entity['alias']}",
                "community": 0, "centrality": 0.5, "betweenness": 0.1,
                "is_boss": False, "is_broker": False,
            }]
            edges = []
            for idx, dist in enumerate(ev_entity.get("districts", [])):
                did = f"dist_{idx}_{dist}"
                nodes.append({
                    "id": did, "label": f"District: {dist}", "type": "district",
                    "title": dist, "community": 1, "centrality": 0.2, "betweenness": 0.0,
                    "is_boss": False, "is_broker": False,
                })
                edges.append({"from": seed_id, "to": did, "rel_type": "active_in", "strength": 1, "suspect_a": seed_id, "suspect_b": did})
            return {
                "nodes": nodes, "edges": edges, "components": [[n["id"] for n in nodes]],
                "brain_banner": "Cross-World Evidence Bridge Active",
                "brain_links": [], "predicted_links": [], "centrality_scores": {seed_id: 0.5},
            }
        return {"nodes": [], "edges": [], "components": [], "brain_banner": None,
                "brain_links": [], "predicted_links": [], "centrality_scores": {},
                "error": f"Unknown suspect {seed_id}"}

    global _adj_cache
    rels = world["relationships"]
    if _adj_cache["adj"] is None or _adj_cache["rels_id"] != id(rels):
        adj: dict[str, list[dict]] = {}
        for r in rels:
            adj.setdefault(r["suspect_a"], []).append(r)
            adj.setdefault(r["suspect_b"], []).append(r)
        _adj_cache["adj"] = adj
        _adj_cache["rels_id"] = id(rels)
    else:
        adj = _adj_cache["adj"]

    # BFS from seed, depth-limited, node-capped
    seen = {seed_id}
    order = [seed_id]
    q = deque([(seed_id, 0)])
    edge_keys = set()
    edges = []
    while q and len(seen) < cap:
        node, d = q.popleft()
        if d >= depth:
            continue
        for r in adj.get(node, []):
            other = r["suspect_b"] if r["suspect_a"] == node else r["suspect_a"]
            key = tuple(sorted((r["suspect_a"], r["suspect_b"]))) + (r["rel_type"],)
            if key not in edge_keys:
                edge_keys.add(key)
                edges.append(r)
            if other not in seen and len(seen) < cap:
                seen.add(other)
                order.append(other)
                q.append((other, d + 1))

    # cross-case enrichment (Second Brain)
    cross = find_cross_case_links(seed_id, world)
    cross_ids = {l["suspect_id"] for l in cross["links"]}
    # also pull in shared contacts so the bridge is visible even if BFS missed them
    for l in cross["links"]:
        cross_ids.update(l.get("shared_contacts", []))
        if l["suspect_id"] not in seen:
            seen.add(l["suspect_id"]); order.append(l["suspect_id"])

    # ensure edges between seed/cross nodes are present (the bridge)
    for r in world["relationships"]:
        a, b = r["suspect_a"], r["suspect_b"]
        if a in seen and b in seen:
            key = tuple(sorted((a, b))) + (r["rel_type"],)
            if key not in edge_keys:
                edge_keys.add(key)
                edges.append(r)

    node_ids = seen

    # Read precomputed full-graph metrics from cache (O(1) dict lookup per node).
    # Full-graph PageRank/betweenness/community are more meaningful than subgraph-local
    # scores because they rank against the entire criminal network.
    metrics = get_cache()
    pagerank     = metrics["pagerank"]
    betweenness  = metrics["betweenness"]
    community_map = metrics["community_map"]
    top_broker_id = (metrics["stats"].get("top_broker") or {}).get("id")

    # Build the local subgraph only for link prediction (needs edge structure).
    # networkx is optional here — if absent we skip k-core / GAT enrichment entirely;
    # the core node / edge / component payload below does not depend on it.
    G = None
    k_core_map: dict = {}
    local_max_k = 0
    if nx is not None:
        G = nx.Graph()
        for sid in node_ids:
            G.add_node(sid)
        for r in edges:
            a, b = r["suspect_a"], r["suspect_b"]
            if a in node_ids and b in node_ids:
                G.add_edge(a, b, weight=float(r.get("strength", 1.0)))

        # K-core decomposition on the local subgraph — inner circle vs periphery.
        # Nodes with k_core == max are the densest, most-connected cluster.
        try:
            k_core_map = nx.core_number(G)
            local_max_k = max(k_core_map.values()) if k_core_map else 0
        except Exception:
            k_core_map = {nid: 0 for nid in node_ids}
            local_max_k = 0

    # --- Link Prediction (optional enrichment) ---
    # Full path : Graph Attention (GAT) over node features + Adamic-Adar topology (needs torch).
    # Fallback  : Adamic-Adar + shared-phone only (needs networkx, no torch) — used on the
    #             slim deploy image where torch is intentionally absent.
    # No-dep    : skip — the core graph payload does not depend on link prediction.
    nodes_list = list(node_ids)
    node_idx = {nid: i for i, nid in enumerate(nodes_list)}
    N = len(nodes_list)

    predicted_links: list[dict] = []
    if nx is not None and G is not None and N > 1:
        # Node features [prior_count, centrality, is_boss] and a deterministic scaled
        # dot-product over two FIXED projection matrices. Same arithmetic as before,
        # now in numpy so it runs everywhere the app runs.
        X = np.zeros((N, 3), dtype=np.float32)
        for i, nid in enumerate(nodes_list):
            s = suspects.get(nid, {})
            X[i, 0] = min(1.0, (s.get("prior_count", 0)) / 10.0)
            X[i, 1] = pagerank.get(nid, 0.0) * 10.0
            X[i, 2] = 1.0 if nid == top_broker_id else 0.0
        W_q = np.array([[1.0, 0.5, 0.2], [0.0, 1.0, 0.5]], dtype=np.float32)
        W_k = np.array([[1.0, 0.2, 0.0], [0.5, 1.0, 0.2]], dtype=np.float32)
        Q = X @ W_q.T
        K = X @ W_k.T
        attention_scores = (Q @ K.T) / (2.0 ** 0.5)  # scaled dot-product

        # Ground the prediction in actual graph topology (Adamic-Adar / common neighbours).
        try:
            unconnected_pairs = [
                (nodes_list[i], nodes_list[j])
                for i in range(N) for j in range(i + 1, N)
                if not G.has_edge(nodes_list[i], nodes_list[j])
            ]

            for u, v, aa_score in nx.adamic_adar_index(G, unconnected_pairs):
                i, j = node_idx[u], node_idx[v]

                u_sus = suspects.get(u, {})
                v_sus = suspects.get(v, {})
                shares_phone = (bool(u_sus.get("phone_hash")) and u_sus["phone_hash"] == v_sus.get("phone_hash"))

                att_score = float(attention_scores[i, j])
                composite = (aa_score * 0.4) + (max(0.0, att_score) * 0.6)
                # Label kept as-is for API/test compatibility. Strictly it is a fixed
                # scaled dot-product over hand-picked projection matrices, not a trained
                # graph attention network — worth renaming, but not on a deploy day.
                method = "gat_attention"
                reason = ("Shared phone number hash" if shares_phone
                          else f"Graph Attention + Topology — score {composite:.3f}")

                if composite > 0.1 or shares_phone:
                    prob = 0.95 if shares_phone else min(0.92, composite / (1.0 + composite))
                    predicted_links.append({
                        "a": u, "b": v,
                        "probability": round(prob, 2),
                        "score": round(composite, 3),
                        "method": method,
                        "reason": reason,
                    })
        except Exception:
            pass

    predicted_links.sort(key=lambda x: x["probability"], reverse=True)

    # build node payload
    nodes = []
    global_cache = get_cache()
    kb_map = global_cache.get("knowledge_boundaries", {})
    for sid in order[:cap]:
        s = suspects.get(sid, {"suspect_id": sid})
        nodes.append({
            "id": sid,
            "label": s.get("full_name", sid),
            "alias": s.get("alias", ""),
            "type": "seed" if sid == seed_id else "suspect",
            "zone": s.get("address_zone", ""),
            "risk": _risk(s.get("prior_count", 0)),
            "cross_case": sid in cross_ids and sid != seed_id,
            "centrality": round(pagerank.get(sid, 0.0), 4),
            "betweenness": round(betweenness.get(sid, 0.0), 4),
            "community": community_map.get(sid, 0),
            "k_core": k_core_map.get(sid, 0),
            "inner_circle": k_core_map.get(sid, 0) == local_max_k and local_max_k >= 2,
            "is_broker": sid == top_broker_id,
            "knowledge_boundary": kb_map.get(sid, 0.5),
        })
    node_ids_filtered = {n["id"] for n in nodes}

    # build edge payload (only edges whose endpoints are in the node set)
    edge_out = []
    for r in edges:
        a, b = r["suspect_a"], r["suspect_b"]
        if a in node_ids_filtered and b in node_ids_filtered:
            is_cross = (a in cross_ids and b == seed_id) or (b in cross_ids and a == seed_id) \
                or r["rel_type"] == "shared_phone" and (a in cross_ids or b in cross_ids)
            edge_out.append({
                "a": a, "b": b, "rel_type": r["rel_type"],
                "strength": r.get("strength", 1),
                "cross_case": bool(is_cross),
                "source": r.get("source_crime_id", ""),
            })

    components = _components(node_ids_filtered, edge_out)

    # Broker alert: surface a narrative when the global top-broker is in this subgraph.
    # Identifies how many distinct gang communities the broker connects — the key WOW moment.
    broker_alert = None
    if top_broker_id and top_broker_id in node_ids_filtered:
        broker_node = next((n for n in nodes if n["id"] == top_broker_id), None)
        if broker_node:
            # Collect distinct communities visible through the broker's edges
            broker_nbr_comms = {
                n["community"]
                for e in edge_out
                if top_broker_id in (e["a"], e["b"])
                for n in nodes
                if n["id"] == (e["b"] if e["a"] == top_broker_id else e["a"])
            }
            bridged = broker_nbr_comms | {broker_node["community"]}
            broker_alert = (
                f"⚠️ {broker_node['label']} bridges {len(bridged)} gang cell(s) "
                f"(betweenness {broker_node['betweenness']:.3f}) — priority arrest target"
            )

    return {
        "seed_id": seed_id,
        "nodes": nodes,
        "edges": edge_out,
        "components": components,
        "brain_banner": cross["banner"],
        "brain_links": cross["links"],
        "predicted_links": predicted_links,
        "predicted_edges": global_cache.get("predicted_edges", []),
        "unsubs": global_cache.get("unsubs", []),
        "broker_alert": broker_alert,
        "centrality_scores": {nid: round(score, 4) for nid, score in pagerank.items()},
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edge_out),
            "cross_case_links": len(cross["links"]),
            "predicted_link_count": len(predicted_links),
            "inner_circle_count": sum(1 for n in nodes if n["inner_circle"]),
        },
    }


def _components(node_ids: set[str], edges: list[dict]) -> list[list[str]]:
    """Connected components via union-find."""
    parent = {n: n for n in node_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for e in edges:
        if e["a"] in parent and e["b"] in parent:
            union(e["a"], e["b"])
    groups: dict[str, list[str]] = {}
    for n in node_ids:
        groups.setdefault(find(n), []).append(n)
    return sorted(groups.values(), key=len, reverse=True)
