"""
Antar — Social Insight API (M4 / N6)
=========================================
GET /api/social/demographics → victim + offender demographic breakdowns +
crime×occupation correlation + the mandatory correlation-only framing.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.agents import social_agent

router = APIRouter()


@router.get("/demographics")
async def demographics() -> dict:
    return social_agent.demographics()
