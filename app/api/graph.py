"""
Antar — Graph API (M2)
GET /api/graph/stats           → full-graph summary (boss, broker, community count)
GET /api/graph/{suspect_id}    → criminal network + cross-case links (WOW 2)
Inspector+ in production (RBAC wired in Phase 6).
"""

from fastapi import APIRouter

from app.agents.network_agent import build_network
from app.services.graph_cache import get_cache, refresh as refresh_graph

router = APIRouter()


@router.get("/stats")
async def graph_stats() -> dict:
    """Precomputed full-graph summary — instant (< 1 ms, no networkx on hot path)."""
    from app.services import product_store
    cached = product_store.get_product("network:global_stats")
    return cached if cached else get_cache()["stats"]


@router.post("/refresh")
async def graph_refresh() -> dict:
    """Rebuild graph metrics cache (call after new arrests/relationships are ingested)."""
    cache = refresh_graph()
    from app.services import product_store
    product_store.invalidate("network:")
    product_store.put_product("network:global_stats", cache["stats"])
    return {"ok": True, "stats": cache["stats"], "refreshed_at": cache["refreshed_at"]}


@router.get("/predicted_edges")
async def get_predicted_edges() -> dict:
    """Layer 2: Top-20 inferred links (predicted_edges) scored via 5-factor engine."""
    from app.services import product_store
    cached = product_store.get_product("predicted_edges:all")
    if cached:
        return {"predicted_edges": cached}
    return {"predicted_edges": get_cache().get("predicted_edges", [])}


@router.get("/unsubs")
async def get_unsubs() -> dict:
    """Layer 2: Discovered synthetic UNSUB profiles from unsolved FIR clusters."""
    from app.services import product_store
    cached = product_store.get_product("unsub:all")
    if cached:
        return {"unsubs": cached}
    return {"unsubs": get_cache().get("unsubs", [])}


@router.get("/{suspect_id}")
async def get_graph(suspect_id: str, depth: int = 2) -> dict:
    """Network graph payload for vis-network: nodes, edges, components, brain banner."""
    return build_network(suspect_id, depth=depth)
