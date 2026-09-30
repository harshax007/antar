"""
Antar/Antar — Evidence Ledger API (P0, build03_improveX)
=============================================================
Thin reads over the in-memory evidence layer (the synthetic FIR CSV with per-accused /
vehicle / UPI / IP linkage). Additive: does not touch the official FIRs endpoints.

GET /api/evidence/stats                 → coverage summary
GET /api/evidence/search?q=&limit=      → resolve id / alias name / vehicle / UPI / IP → entities
GET /api/evidence/entity/{accused_id}   → full evidence dossier (rows, linkage keys, districts)

This is the P0 bridge that lets Search/Chat answer about the ACC- entities Brain shows —
closing the "two data worlds" gap for the evidence layer. Deterministic, LLM-free.
"""

from fastapi import APIRouter, HTTPException

from app.services import evidence_ledger as ev

router = APIRouter()


@router.get("/stats")
async def stats() -> dict:
    from app.services import product_store
    cached = product_store.get_product("evidence:stats")
    return cached if cached else ev.stats()


@router.get("/search")
async def search(q: str, limit: int = 20) -> dict:
    hits = ev.search(q, limit=limit)
    return {"query": q, "hits": hits, "count": len(hits)}


@router.get("/entity/{accused_id}")
async def entity(accused_id: str) -> dict:
    e = ev.entity(accused_id)
    if not e:
        raise HTTPException(status_code=404, detail=f"No evidence entity for {accused_id}")
    return e
