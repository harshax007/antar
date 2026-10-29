"""
Antar — Social Insight API (M4 / N6)
=========================================
GET /api/social/demographics → victim + offender demographic breakdowns +
crime×occupation correlation + the mandatory correlation-only framing.
GET /api/social/indicators   → district social indicators (Census 2011, NFHS-5) against
crime rates, with rank correlations, urbanisation held constant, and what each can't say.
"""

from __future__ import annotations

from fastapi import APIRouter

import asyncio

from app.agents import social_agent
from app.services import social_indicators

router = APIRouter()


_demographics_cache: dict | None = None


@router.get("/demographics")
async def demographics() -> dict:
    global _demographics_cache
    if _demographics_cache is None:
        _demographics_cache = await asyncio.to_thread(social_agent.demographics)
    return _demographics_cache


@router.get("/indicators")
async def indicators() -> dict:
    return await asyncio.to_thread(social_indicators.analysis)
