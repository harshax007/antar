"""
Antar — Full-graph metrics cache (§5: materialization)
============================================================
Precomputes PageRank, Louvain communities, and betweenness centrality
over the entire suspect + relationship graph on startup (< 1 s for 289 nodes).

build_network() reads from this cache instead of running networkx on every
request — cuts per-request networkx compute from ~30 ms to < 1 ms.

Startup wiring (main.py lifespan):
    from app.services.graph_cache import refresh as refresh_graph
    refresh_graph()

Refresh strategy: once at startup; call refresh() again from a periodic cron
if the graph changes (new arrests → new relationships).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

_cache: Optional[dict] = None


def refresh() -> dict:
    """Rebuild full-graph metrics. Safe to call at startup or from a cron task."""
    global _cache

    from app.services.zcql_local import _world
    import networkx as nx

    world = _world()
    suspects = world["suspects"]
    relationships = world["relationships"]

    G = nx.Graph()
    for s in suspects:
        G.add_node(s["suspect_id"])
    for r in relationships:
        a, b = r["suspect_a"], r["suspect_b"]
        raw_strength = r.get("strength", 1.0)
        if isinstance(raw_strength, str):
            w_map = {"high": 3.0, "medium": 2.0, "low": 1.0}
            w = w_map.get(raw_strength.lower(), 1.0)
        else:
            try:
                w = float(raw_strength)
            except ValueError:
                w = 1.0
        G.add_edge(a, b, weight=w)

    # PageRank — node influence (Boss = largest node in Brain 2.1 globe)
    try:
        pagerank = nx.pagerank(G, weight="weight")
    except Exception:
        n = max(1, G.number_of_nodes())
        pagerank = {nid: 1.0 / n for nid in G.nodes()}

    # Louvain communities — gang/cell grouping (color-coded in globe)
    try:
        from networkx.algorithms.community import louvain_communities
        communities_sets = louvain_communities(G, weight="weight", seed=42)
        community_map: dict[str, int] = {}
        for idx, comm in enumerate(communities_sets):
            for sid in comm:
                community_map[sid] = idx
        community_count = len(communities_sets)
        community_sizes = {idx: len(comm) for idx, comm in enumerate(communities_sets)}
    except Exception:
        community_map = {nid: 0 for nid in G.nodes()}
        community_count = 1
        community_sizes = {0: G.number_of_nodes()}

    # Betweenness centrality — Broker identification (Freeman 1977)
    # Brokers bridge communities and are often the highest-value arrest targets.
    try:
        betweenness = nx.betweenness_centrality(G, normalized=True, weight="weight")
    except Exception:
        betweenness = {nid: 0.0 for nid in G.nodes()}

    # K-core decomposition — inner circle vs periphery
    try:
        k_core = nx.core_number(G)
        max_k = max(k_core.values()) if k_core else 0
        inner_circle = [sid for sid, k in k_core.items() if k == max_k]
    except Exception:
        k_core = {nid: 0 for nid in G.nodes()}
        max_k = 0
        inner_circle = []

    name_map = {s["suspect_id"]: s.get("full_name", s["suspect_id"]) for s in suspects}

    top_boss_id   = max(pagerank,    key=pagerank.get)    if pagerank    else None
    top_broker_id = max(betweenness, key=betweenness.get) if betweenness else None

    # ── Layer 2: UNSUB Profiles, Knowledge Boundaries, and Predicted Edges ────
    try:
        from app.services.patterns import find_unsubs
        unsubs = find_unsubs()
    except Exception:
        unsubs = []

    knowledge_boundaries: dict[str, float] = {}
    for s in suspects:
        sid = s["suspect_id"]
        u_gaps = sum(1 for k in ("vehicle", "phone_hash", "upi", "address_zone") if not s.get(k))
        k_facts = 1 + sum(1 for k in ("full_name", "vehicle", "phone_hash", "upi", "address_zone") if s.get(k)) + int(s.get("prior_count", 0))
        knowledge_boundaries[sid] = round(u_gaps / float(k_facts + 1.0), 3)
    for u in unsubs:
        knowledge_boundaries[u["id"]] = 1.0

    predicted_edges: list[dict] = []
    try:
        from app.agents.research_agent import _score_hypothesis_pair
        existing_edges = set()
        for r in relationships:
            a, b = r["suspect_a"], r["suspect_b"]
            existing_edges.add((a, b))
            existing_edges.add((b, a))

        from collections import defaultdict
        sus_crimes: dict[str, set[str]] = defaultdict(set)
        for cs in world["crime_suspects"]:
            sus_crimes[cs["suspect_id"]].add(cs["crime_id"])

        cand_pairs = []
        for i in range(min(len(suspects), 40)):
            for j in range(i + 1, min(len(suspects), 150)):
                sa = suspects[i]
                sb = suspects[j]
                if (sa["suspect_id"], sb["suspect_id"]) in existing_edges:
                    continue
                cand_pairs.append((sa, sb))

        for sa, sb in cand_pairs:
            score_res = _score_hypothesis_pair(sa, sb, sus_crimes)
            if score_res and score_res.get("score", 0.0) >= 0.35:
                predicted_edges.append({
                    "source": sa["suspect_id"],
                    "target": sb["suspect_id"],
                    "type": "inferred",
                    "score": round(score_res["score"], 2),
                    "reasons": [s["name"] for s in score_res.get("signals", [])],
                    "label": f"Inferred Link ({int(score_res['score']*100)}% confidence)",
                })
        predicted_edges.sort(key=lambda x: x["score"], reverse=True)
        predicted_edges = predicted_edges[:25]
        try:
            from app.services.product_store import put_product
            put_product("predicted_edges:all", predicted_edges, ttl=86400)
        except Exception:
            pass
    except Exception:
        pass

    _cache = {
        "pagerank":        pagerank,
        "betweenness":     betweenness,
        "community_map":   community_map,
        "community_count": community_count,
        "community_sizes": community_sizes,
        "k_core":          k_core,
        "k_core_max":      max_k,
        "inner_circle":    inner_circle,
        "unsubs":          unsubs,
        "knowledge_boundaries": knowledge_boundaries,
        "predicted_edges": predicted_edges,
        "stats": {
            "node_count":         G.number_of_nodes(),
            "edge_count":         G.number_of_edges(),
            "unsub_count":        len(unsubs),
            "predicted_edge_count": len(predicted_edges),
            "community_count":    community_count,
            "inner_circle_count": len(inner_circle),
            "max_k_core":         max_k,
            "top_boss": {
                "id":       top_boss_id,
                "name":     name_map.get(top_boss_id, top_boss_id),
                "pagerank": round(pagerank.get(top_boss_id, 0), 4),
            } if top_boss_id else None,
            "top_broker": {
                "id":          top_broker_id,
                "name":        name_map.get(top_broker_id, top_broker_id),
                "betweenness": round(betweenness.get(top_broker_id, 0), 4),
            } if top_broker_id else None,
        },
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }
    return _cache


def get_cache() -> dict:
    """Return the cache, computing lazily if not yet initialized."""
    if _cache is None:
        refresh()
    return _cache  # type: ignore[return-value]


def get_node_metrics(suspect_id: str) -> dict:
    """Instant per-node lookup: pagerank, betweenness, k-core, community, role flags."""
    c = get_cache()
    top_boss   = c["stats"].get("top_boss")   or {}
    top_broker = c["stats"].get("top_broker") or {}
    return {
        "pagerank":     round(c["pagerank"].get(suspect_id, 0.0), 4),
        "betweenness":  round(c["betweenness"].get(suspect_id, 0.0), 4),
        "k_core":       c["k_core"].get(suspect_id, 0),
        "inner_circle": suspect_id in c["inner_circle"],
        "community":    c["community_map"].get(suspect_id, 0),
        "community_count": c["community_count"],
        "knowledge_boundary": c.get("knowledge_boundaries", {}).get(suspect_id, 0.5),
        "is_boss":   top_boss.get("id")   == suspect_id,
        "is_broker": top_broker.get("id") == suspect_id,
    }
