"""
Antar — Entity Bridge Service (P0: Unify the worlds)
=========================================================
Bridges the two disconnected data worlds:
  1. Seed world (`_world()` / SQLite `suspects` table: S0001 style)
  2. Evidence ledger (`evidence_ledger._by_accused`: ACC-831453 style)

Provides canonical ID mapping, unified multi-signal search, and cross-source profile/graph resolution.
Collision policy: never merge across sources without a shared hard key (phone/vehicle/UPI);
otherwise coexist cleanly with distinct canonical IDs.
"""

from __future__ import annotations

from typing import Any
from app.services.zcql_local import _world
from app.services import evidence_ledger as ev
from app.services.entity_resolver import fuzzy_match_suspects


def get_bridge() -> list[dict[str, Any]]:
    """Returns the full entity bridge table mapping canonical_id -> source / source_id."""
    world = _world()
    bridge: list[dict[str, Any]] = []
    
    # 1. Seed suspects
    for s in world.get("suspects", []):
        sid = s["suspect_id"]
        bridge.append({
            "canonical_id": sid,
            "source": "seed",
            "source_id": sid,
            "display_name": s.get("full_name") or s.get("alias") or sid,
            "name_note": "official record",
            "phone_hash": s.get("phone_hash"),
        })
        
    # 2. Evidence ledger accused
    for aid in ev.search("ACC-", limit=5000):
        acc_id = aid["accused_id"]
        bridge.append({
            "canonical_id": acc_id,
            "source": "evidence",
            "source_id": acc_id,
            "display_name": aid["alias"],
            "name_note": "synthetic alias",
            "phone_hash": None,
        })
        
    return bridge


def search_all(
    query: str,
    limit: int = 10,
    threshold: float = 0.82,
    field: str = "all",
    world: dict | None = None,
) -> list[dict[str, Any]]:
    """Unified search across seed suspects AND evidence ledger accused."""
    world = world or _world()
    q = query.strip()
    if not q:
        return []
        
    # 1. Search seed world
    fields_map = {
        "all": None,
        "name": ("full_name",),
        "alias": ("alias",),
        "father": ("father_name",),
        "phone": ("phone_hash",),
    }
    fields = fields_map.get(field, None)
    seed_hits = fuzzy_match_suspects(q, world, threshold=threshold, limit=limit, fields=fields)
    
    # Enrich seed hits with risk_score from profile agent calculation
    from app.agents import profile_agent
    risks = profile_agent.risk_scores(world)
    for h in seed_hits:
        h["risk_score"] = risks.get(h["suspect_id"])
        h["source"] = "seed"

    # 2. Search evidence ledger (if field is applicable)
    ev_hits: list[dict[str, Any]] = []
    if field in ("all", "name", "alias", "phone"):
        raw_ev = ev.search(q, limit=limit)
        for r in raw_ev:
            aid = r["accused_id"]
            alias = r["alias"]
            fir_count = r.get("fir_count", 1)
            # Calculate deterministic risk score for evidence accused
            risk = min(100, int(fir_count * 15))
            
            # Determine match score and method
            m_field = r.get("match_field", "alias")
            score = 1.0 if q.upper() in aid.upper() else 0.85
            
            ev_hits.append({
                "suspect_id": aid,
                "full_name": alias,
                "alias": f"{alias} (synthetic alias)",
                "age": None,
                "gender": "Unknown",
                "address_zone": ", ".join(r.get("districts", [])),
                "prior_count": fir_count,
                "arrest_status": "Wanted (Evidence Ledger)",
                "match_score": score,
                "match_field": "alias" if m_field in ("alias", "accused_id") else ("phone_hash" if m_field == "phone" else "full_name"),
                "match_method": "evidence_ledger",
                "risk_score": risk,
                "source": "evidence",
            })
            
    # Combine, sort by match_score desc (then risk_score desc), and trim to limit
    combined = seed_hits + ev_hits
    combined.sort(key=lambda x: (x.get("match_score", 0), x.get("risk_score", 0) or 0), reverse=True)
    
    # De-duplicate by suspect_id
    seen = set()
    result = []
    for item in combined:
        sid = item["suspect_id"]
        if sid not in seen:
            seen.add(sid)
            result.append(item)
            if len(result) >= limit:
                break
                
    return result
