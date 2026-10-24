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


@router.get("/demographics")
async def demographics() -> dict:
    return social_agent.demographics()


@router.get("/indicators")
async def indicators() -> dict:
    return await asyncio.to_thread(social_indicators.analysis)
