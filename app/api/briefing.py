"""
Antar — Briefing API (A4: Shift Briefings · Phase 1)
=========================================================
GET /api/briefing/shift -> returns pre-compiled shift briefing intelligence.
"""

from fastapi import APIRouter
from app.agents import briefing_agent

router = APIRouter()


@router.get("/shift")
async def get_shift(zone: str = "all", window: str = "12h") -> dict:
    """Pre-compiled shift briefing intelligence (A4). Returns < 30 ms from Product Store."""
    return briefing_agent.get_shift_briefing(zone=zone, window=window)
