"""
Antar - Brain console API
=========================
GET  /api/console/identity   who Antar is, how it thinks, and a card per console agent
GET  /api/console/evolution  how Antar has changed with use, counted from the stores that record it
GET  /api/console/learnings  what the records show today, as lines one agent tells another
POST /api/console/run        {agent, target} -> one agent's answer on one record

`target` is either the node an officer dropped the agent on ({accused, fir_i, station,
district, crime_group}) or the word typed after `run <agent>`. See app/agents/brain_console.py.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents import brain_console, manifest

router = APIRouter()


class RunRequest(BaseModel):
    agent: str = Field(min_length=1, max_length=32)
    target: Any = None


@router.get("/identity")
async def console_identity() -> dict:
    return brain_console.identity_pack()


@router.get("/evolution")
async def console_evolution() -> dict:
    return await asyncio.to_thread(brain_console.evolution)


@router.get("/learnings")
async def console_learnings() -> dict:
    return await asyncio.to_thread(brain_console.learnings)


@router.post("/run")
async def console_run(req: RunRequest) -> dict:
    card = brain_console.AGENTS.get(req.agent.strip().lower())
    declared = manifest.load().agents.get(card.manifest) if card else None
    timeout = declared.timeout_s if declared else 8.0
    try:
        return await asyncio.wait_for(asyncio.to_thread(brain_console.run, req.agent, req.target),
                                      timeout=timeout)
    except asyncio.TimeoutError:
        return {"agent": req.agent, "status": "error", "evidence_class": None,
                "bottom_line": f"The {req.agent} agent did not finish within {timeout:.0f} seconds.",
                "context": "", "evidence": [], "limits": ["Nothing is shown rather than a partial result."],
                "next": [], "method": list(card.method) if card else []}
