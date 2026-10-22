"""
Antar — Full-graph metrics cache (§5: materialization)
============================================================
Precomputes PageRank, Louvain communities, and betweenness centrality
over the entire suspect + relationship graph on startup (< 1 s for 289 nodes).

Two additions (2026-10-23):
  * Gangs are found on the recorded relationships PLUS shared keys: suspects on the same
    phone number, or paying the same flagged counterparty account, are linked even when no
    relationship was recorded - mules on one burner phone form a star or a chain that
    relationships alone leave in pieces. Louvain can return a "community" whose members
    are not connected to each other; each one is split into its connected parts (the
    guarantee Leiden adds over Louvain, without the igraph/leidenalg dependency).
  * Proximity to serious cases: Personalized PageRank seeded on the suspects named in
    serious crimes (SERIOUS). Someone NOT named in one, yet close to several through
    people, phones or accounts, is listed with the path that puts them there - a lead for
    the officer to check, never a finding.

build_network() reads from this cache instead of running networkx on every
request — cuts per-request networkx compute from ~30 ms to < 1 ms.

Startup wiring (main.py lifespan):
    from app.services.graph_cache import refresh as refresh_graph
    refresh_graph()

Refresh strategy: once at startup; call refresh() again from a periodic cron
if the graph changes (new arrests → new relationships).
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Optional

_cache: Optional[dict] = None

# Crime types whose accused seed the proximity score (matched case-insensitively).
SERIOUS = re.compile(r"MURDER|ROBBERY|DACOITY|KIDNAP|ABDUCTION|NARCOTIC|NDPS|POCSO|RAPE|ARMS|EXTORTION", re.I)
HIDDEN_TOP = 5          # how many "close to serious cases" leads the stats carry


def _key_links(world: dict) -> list[tuple[str, str, float, str]]:
    """(a, b, weight, why) links between suspects that share a phone number or a flagged
    counterparty account. Each shared key joins its holders in a chain, not a clique, so
    one busy key cannot dominate the graph."""
    out: list[tuple[str, str, float, str]] = []
    by_phone: dict[str, list[str]] = {}
    for s in world.get("suspects", []):
        ph = str(s.get("phone_hash") or "").strip()
        if ph:
            by_phone.setdefault(ph, []).append(s["suspect_id"])
    by_acct: dict[str, list[str]] = {}
    for f in world.get("financial_links", []):
        cp = str(f.get("counterparty") or "").strip()
        if cp and f.get("suspect_id"):
            by_acct.setdefault(cp, []).append(f["suspect_id"])
    for key, holders, w, why in ([(k, v, 2.5, "same phone") for k, v in by_phone.items()]
                                  + [(k, v, 2.0, "same account") for k, v in by_acct.items()]):
        hs = sorted(set(holders))
        for a, b in zip(hs, hs[1:]):
            out.append((a, b, w, f"{why} {key}"))
    return out


def _connected_communities(G, sets) -> list[set]:
    """Split every community into its connected parts: a gang whose members do not reach
    each other inside it is not one gang."""
    import networkx as nx
    parts: list[set] = []
    for comm in sets:
        parts.extend(set(c) for c in nx.connected_components(G.subgraph(comm)))
    return sorted(parts, key=lambda c: (-len(c), min(c)))


def _serious_proximity(G, world: dict, name_map: dict) -> tuple[dict, list[dict], int]:
    """Personalized PageRank seeded on suspects named in serious crimes.

    Returns ({suspect: proximity 0..1 as a percentile among suspects}, the HIDDEN_TOP
    non-seed suspects closest to serious cases with the path that explains each, seeds)."""
    import networkx as nx
    serious_crimes = {c["crime_id"]: c.get("crime_type", "") for c in world.get("crimes", [])
                      if SERIOUS.search(str(c.get("crime_type", "")))}
    seeds: dict[str, int] = {}
    seed_crime: dict[str, str] = {}
    for cs in world.get("crime_suspects", []):
        ct = serious_crimes.get(cs.get("crime_id"))
        if ct:
            seeds[cs["suspect_id"]] = seeds.get(cs["suspect_id"], 0) + 1
            seed_crime.setdefault(cs["suspect_id"], ct.strip().upper())
    seeds = {k: v for k, v in seeds.items() if k in G}
    if not seeds or G.number_of_edges() == 0:
        return {}, [], len(seeds)
    # Accounts take part as nodes too, so money moving through one account connects payers.
    H = G.copy()
    for f in world.get("financial_links", []):
        cp, sid = str(f.get("counterparty") or "").strip(), f.get("suspect_id")
        if cp and sid in H:
            H.add_edge(sid, f"acct:{cp}", weight=1.0 + math.log1p(float(f.get("txn_count") or 0)))
    ppr = nx.pagerank(H, alpha=0.85, personalization=seeds, weight="weight")
    suspects = [n for n in G.nodes]
    order = sorted(suspects, key=lambda n: ppr.get(n, 0.0))
    pct = {n: round(i / max(1, len(order) - 1), 3) for i, n in enumerate(order)}
    # Leads: not seeds themselves, connected to something, highest score first.
    cands = sorted((n for n in suspects if n not in seeds and G.degree(n) > 0),
                   key=lambda n: -ppr.get(n, 0.0))[:HIDDEN_TOP]
    lengths, paths = nx.multi_source_dijkstra(H, set(seeds), weight=None)
    hidden = []
    for n in cands:
        path = paths.get(n) or []
        seed = path[0] if path else None
        hidden.append({
            "id": n, "name": name_map.get(n, n), "proximity": pct.get(n, 0.0),
            "nearest_serious": seed, "nearest_serious_name": name_map.get(seed, seed) if seed else None,
            "nearest_serious_crime": seed_crime.get(seed) if seed else None,
            "steps": int(lengths.get(n)) if n in lengths else None,
            "via": [name_map.get(p, p) if not str(p).startswith("acct:") else p[5:] for p in path[1:-1]],
        })
    return pct, hidden, len(seeds)


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

    # Relationships plus shared phones / accounts: the graph gangs are found on. PageRank,
    # betweenness and k-core above and below stay on the recorded relationships, so the
    # boss / broker / inner-circle readings do not move.
    key_links = _key_links(world)
    G_keys = G.copy()
    for a, b, w, why in key_links:
        if a in G_keys and b in G_keys:
            if G_keys.has_edge(a, b):
                G_keys[a][b]["weight"] = max(G_keys[a][b]["weight"], w)
            else:
                G_keys.add_edge(a, b, weight=w, via=why)

    # Louvain communities — gang/cell grouping (color-coded in globe), each split into its
    # connected parts
    communities_split = 0
    try:
        from networkx.algorithms.community import louvain_communities
        raw_sets = louvain_communities(G_keys, weight="weight", seed=42)
        communities_sets = _connected_communities(G_keys, raw_sets)
        communities_split = len(communities_sets) - len(raw_sets)
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

    try:
        serious_proximity, hidden_near_serious, serious_seeds = _serious_proximity(G_keys, world, name_map)
    except Exception:
        serious_proximity, hidden_near_serious, serious_seeds = {}, [], 0

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
        "serious_proximity": serious_proximity,
        "hidden_near_serious": hidden_near_serious,
        "stats": {
            "node_count":         G.number_of_nodes(),
            "edge_count":         G.number_of_edges(),
            "unsub_count":        len(unsubs),
            "predicted_edge_count": len(predicted_edges),
            "community_count":    community_count,
            "communities_split":  communities_split,       # Louvain groups that were not connected
            "key_links":          len(key_links),          # shared-phone / shared-account links added
            "serious_seeds":      serious_seeds,           # suspects named in serious crimes
            "hidden_near_serious": hidden_near_serious,
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
        # 0..1 percentile of closeness to serious cases (Personalized PageRank); a lead only
        "serious_proximity": c.get("serious_proximity", {}).get(suspect_id, 0.0),
        "near_serious": any(h["id"] == suspect_id for h in c.get("hidden_near_serious", [])),
    }
