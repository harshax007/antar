"""
Antar — Linkage API (A3: MO Case-Matcher · Phase 1)
========================================================
Endpoints for retrieving compiled cross-case connections and MO similarity candidates.
"""

from fastapi import APIRouter
from app.agents import linkage_agent
from app.services import product_store

router = APIRouter()


@router.get("/{fir_id}")
async def get_fir_linkage(fir_id: str) -> dict:
    """Retrieve compiled linkage intelligence for a specific FIR."""
    key = f"linkage:{fir_id.upper()}"
    prod = product_store.get_product(key)
    if not prod:
        prod = linkage_agent.compile_linkage(fir_id)
    return {"ok": True, "linkage": prod}


@router.post("/compile")
async def compile_linkages_endpoint() -> dict:
    """Compile case linkage products for all known high-priority FIRs."""
    recompiled = linkage_agent.compile_all_linkages()
    return {"ok": True, "compiled_count": len(recompiled), "results": recompiled}
