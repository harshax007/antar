"""
Antar — Brain API (Second Brain · M2)
==========================================
GET  /api/brain/related ?suspect_ids=S0001[,S0002] → cross-case links + banner  [Inspector+]
POST /api/brain/seed                                → seed planted summaries (dev)  [Admin]

Cross-case discovery is DATA-driven (shared phone_hash + common contacts), so it works
even before the embedding index is seeded; the brain summary just enriches it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from app.core.auth_middleware import require_cron_secret, require_role

from app.second_brain.retrieval import find_cross_case_links
from app.second_brain.ingestion import seed_demo_brain, session_end_ingest
from app.second_brain.consolidation import consolidate_nightly
from app.second_brain.index import brain_index

router = APIRouter()


@router.get("/related")
async def related(suspect_ids: str = "") -> dict:
    ids = [s.strip() for s in suspect_ids.split(",") if s.strip()]
    results, banner = [], None
    for sid in ids:
        res = find_cross_case_links(sid)
        results.append({"suspect_id": sid, "links": res.get("links", []),
                        "banner": res.get("banner")})
        banner = banner or res.get("banner")
    return {"results": results, "banner": banner}


@router.post("/seed", dependencies=[Depends(require_role("Admin"))])
@router.post("/seed/", dependencies=[Depends(require_role("Admin"))])
async def seed() -> dict:
    return {"seeded": seed_demo_brain()}


@router.post("/consolidate", dependencies=[Depends(require_cron_secret)])
@router.post("/consolidate/", dependencies=[Depends(require_cron_secret)])
async def consolidate() -> dict:
    return await consolidate_nightly()

@router.post("/ingest_session")
async def ingest_session(session_id: str, request: Request) -> dict:
    # The role stamped on the memory is the caller's resolved role — it used to be a
    # query parameter, so any caller could label their own session "Superintendent".
    from app.core.auth_middleware import current_identity
    success = await session_end_ingest(session_id, current_identity(request).role)
    return {"ingested": success}

@router.get("/activity")
async def get_activity(limit: int = 10) -> dict:
    # Return recent fragments regardless of status
    recent = []
    for meta in reversed(brain_index._metadata):
        if meta.get("kind") == "session_trace":
            recent.append(meta)
            if len(recent) >= limit:
                break
    return {"activity": recent}

@router.get("/learnings")
async def get_learnings(limit: int = 5) -> dict:
    # Return ONLY 'verified' high-confidence findings
    learnings = []
    for meta in reversed(brain_index._metadata):
        if meta.get("kind") == "session_trace" and meta.get("verification_status") == "verified":
            learnings.append(meta)
            if len(learnings) >= limit:
                break
    return {"learnings": learnings}


@router.get("/similar")
async def similar_cases(q: str, k: int = 10, district: str | None = None,
                        crime_group: str | None = None) -> dict:
    """GET /api/brain/similar?q=… → FIRs whose recorded circumstances resemble the query.

    The case-similarity tier (final_backend.md §6 P1-2): one vector per FIR, searched on
    disk. Read-only and Inspector-gated like the rest of this router.

    Every hit carries the FIR text that matched and its metadata, so an answer can cite
    the case instead of asserting a resemblance. `corpus` reports what is actually
    indexed — an empty corpus is stated, never silently returned as "no similar cases".
    """
    from app.second_brain.retrieval import corpus_recall
    from app.second_brain import vec_store

    stats = vec_store.stats()
    indexed = stats["by_kind"].get("fir", 0)
    hits = corpus_recall(q, k=k, district=district, crime_group=crime_group)
    return {
        "query": q,
        "count": len(hits),
        "hits": [{"fir": h["meta"].get("fir_no"), "score": round(h["score"], 4),
                  "text": h["summary_text"], "district": h["meta"].get("district"),
                  "station": h["meta"].get("station"), "date": h["meta"].get("date"),
                  "crime_group": h["meta"].get("crime_group")} for h in hits],
        "corpus": {"indexed_firs": indexed, "mb": stats["mb"]},
        "evidence_class": "D",      # derived: similarity over recorded text, not a judgment
        "note": ("No FIR corpus is indexed yet — run scripts/build_brain_index.py. "
                 "This is missing data, not an absence of similar cases."
                 if indexed == 0 else None),
    }
