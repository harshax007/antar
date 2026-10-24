"""
Antar — Profile API (M5/M6, F5) + Repeat-Offender Registry (N7)
===================================================================
GET /api/profile/registry        → habitual offenders, sorted by risk        [Inspector+]
GET /api/profile/search          → fuzzy + phonetic name/alias/phone search  [Inspector+]
GET /api/profile/{suspect_id}     → 4-factor risk + MO + similar + leads      [Inspector+]

(RBAC enforced in Phase 6; open in dev.) /registry and /search are declared first so
neither is captured by the /{suspect_id} path param.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents import profile_agent
from app.services import entity_bridge
from app.services.zcql_repo import build_spec
from app.services.zcql_local import run_query, _world

router = APIRouter()


@router.get("/bridge")
async def get_bridge_mapping() -> dict:
    """Entity bridge table (P0): canonical ID mapping across seed suspects and evidence ledger."""
    bridge = entity_bridge.get_bridge()
    return {"bridge": bridge, "count": len(bridge)}


@router.get("/registry")
async def registry(min_priors: int = 5, limit: int = 50) -> dict:
    """Repeat-offender registry (N7): habitual offenders with risk, sorted high→low."""
    from app.services import product_store
    cached = product_store.get_product("registry:habitual")
    if cached:
        filtered = [o for o in cached["offenders"] if (o.get("prior_count") or 0) >= min_priors][:limit]
        return {"offenders": filtered, "count": len(filtered)}
    world = _world()
    rows = run_query(build_spec("T5", {"min_priors": min_priors, "limit": limit}))
    risks = profile_agent.risk_scores(world)
    offenders = [{
        "suspect_id": r["suspect_id"], "full_name": r.get("full_name"), "alias": r.get("alias"),
        "prior_count": r.get("prior_count"), "zone": r.get("address_zone"),
        "risk_score": risks.get(r["suspect_id"]),
    } for r in rows]
    offenders.sort(key=lambda x: (x["risk_score"] or 0), reverse=True)
    return {"offenders": offenders, "count": len(offenders)}


# UI filter chip → resolver field restriction. Unknown values fall back to "all"
# so old clients keep working.
_FIELD_MAP: dict[str, tuple[str, ...] | None] = {
    "all": None,
    "name": ("full_name",),
    "alias": ("alias",),
    "father": ("father_name",),
    "phone": ("phone_hash",),
}


from pydantic import BaseModel
from datetime import datetime


class TrackUnknownRequest(BaseModel):
    query: str
    field: str = "all"
    note: str = ""


@router.post("/track_unknown")
async def track_unknown(req: TrackUnknownRequest) -> dict:
    """Creates a Second Brain [GAP] memory product for an unknown search query."""
    from app.services import product_store
    gap_id = f"GAP-{abs(hash(req.query)) % 90000 + 10000}"
    gap_record = {
        "id": gap_id,
        "query": req.query,
        "field": req.field,
        "note": req.note or f"Officer initiated tracking on unknown search lead: '{req.query}'",
        "state": "U",
        "badge": "GAP (SECTION 91 TRACKED)",
        "created_at": datetime.now().isoformat(),
    }
    product_store.put_product(f"gap:lead:{gap_id}", gap_record)
    return {"status": "success", "gap_id": gap_id, "record": gap_record}


@router.get("/search")
async def search(q: str, limit: int = 10, threshold: float = 0.82, field: str = "all") -> dict:
    """Fuzzy + phonetic suspect search (N9, WOW-2) — name / alias / father / phone_hash.

    Layer 5 Additions:
      • Unknown-first search: when hits == 0, returns phonetic nearest neighbors (< threshold)
        + matching UNSUB series + one-click Track action.
      • Cross-source identity hypotheses: suggests candidate identity links across records (§0.2).
    """
    world = _world()
    hits = entity_bridge.search_all(q, limit=limit, threshold=threshold, field=field, world=world)

    # Compute cross-source identity hypotheses across world records
    from app.services.entity_resolver import suggest_identity_links
    identity_hypotheses = suggest_identity_links(world, threshold=0.75)

    unknown_discovery = None
    if len(hits) == 0:
        # Lower threshold to discover nearest known phonetic neighbors
        nearest_hits = entity_bridge.search_all(q, limit=3, threshold=0.60, field=field, world=world)
        from app.services import product_store
        unsubs = product_store.get_product("unsub:all") or []
        q_low = q.lower()
        matching_unsubs = [
            u for u in unsubs
            if q_low in u.get("label", "").lower() or any(q_low in c.lower() for c in u.get("common_mo", []))
        ][:3]

        unknown_discovery = {
            "status": "UNKNOWN_LEAD",
            "message": f"Zero exact hits for '{q}' — initiated Unknown-First discovery protocol (§0.2 / improveX P0).",
            "nearest_neighbors": nearest_hits,
            "matching_unsubs": matching_unsubs,
            "track_action": {
                "endpoint": "/api/profile/track_unknown",
                "method": "POST",
                "query": q,
                "field": field,
            },
        }

    return {
        "query": q,
        "field": field if field in _FIELD_MAP else "all",
        "hits": hits,
        "count": len(hits),
        "unknown_discovery": unknown_discovery,
        "identity_hypotheses": identity_hypotheses[:5],
    }


@router.get("/{suspect_id}/cases")
async def cases(suspect_id: str) -> dict:
    """The FIRs that name this person (crime_suspects), newest first: their criminal history,
    each one openable as a case (/case/{fir_id})."""
    import sqlite3
    from datetime import date
    from app.core.db_path import DB_PATH, registry_connect
    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT f.fir_id, SUBSTR(f.date, 1, 10) AS d, COALESCE(f.district_norm, f.District_Name) AS district, "
            "f.station, COALESCE(f.CrimeHead_Name, f.crime_type) AS crime, f.crime_type, f.FIR_Stage, cs.role "
            "FROM crime_suspects cs JOIN FIRs f ON f.fir_id = cs.crime_id "
            "WHERE cs.suspect_id = ? AND f.date <= ? ORDER BY f.date DESC LIMIT 200",
            (suspect_id, date.today().isoformat())).fetchall()
    finally:
        con.close()
    seen, out = set(), []
    for r in rows:                       # a fir_id can repeat in the register; one row per case
        if r["fir_id"] in seen:
            continue
        seen.add(r["fir_id"])
        tidy = lambda v: " ".join(str(v or "").replace("_", " ").split())   # noqa: E731 ("Under_Investigation")
        out.append({"fir_id": r["fir_id"], "date": r["d"], "district": r["district"], "station": r["station"],
                    "crime": tidy(r["crime"]).capitalize(), "crime_type": tidy(r["crime_type"]),
                    "stage": tidy(r["FIR_Stage"]).title(), "role": tidy(r["role"])})
    return {"suspect_id": suspect_id, "count": len(out), "cases": out,
            "districts": sorted({c["district"] for c in out if c["district"]})}


@router.get("/{suspect_id}")
async def profile(suspect_id: str) -> dict:
    prof = profile_agent.compute_profile(suspect_id)
    if not prof:
        raise HTTPException(status_code=404, detail=f"Suspect {suspect_id} not found")
    return prof

