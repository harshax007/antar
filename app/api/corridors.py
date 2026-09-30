"""
Antar — Corridor API (A2: Movement Intelligence · Phase 1)
===============================================================
Endpoints for reading compiled inter-district offender movement corridors.
"""

from fastapi import APIRouter, HTTPException
from app.agents import corridor_agent

router = APIRouter()


@router.get("")
@router.get("/")
async def list_corridors() -> dict:
    """Retrieve all active offender movement corridors."""
    corridors = corridor_agent.get_all_corridors()
    return {"count": len(corridors), "corridors": corridors}


@router.get("/{src}/{dst}")
async def get_corridor_detail(src: str, dst: str) -> dict:
    """Retrieve intelligence for a specific inter-district corridor."""
    corridor = corridor_agent.get_corridor(src, dst)
    if not corridor:
        # Try reverse direction if direct not found
        corridor = corridor_agent.get_corridor(dst, src)
    if not corridor:
        raise HTTPException(status_code=404, detail=f"No active movement corridor found between {src} and {dst}.")
    return {"ok": True, "corridor": corridor}


@router.post("/compile")
async def trigger_compilation() -> dict:
    """Recompile all corridor products from historical transition matrices."""
    corridors = corridor_agent.compile_corridors()
    return {"ok": True, "recompiled_count": len(corridors), "corridors": corridors}
