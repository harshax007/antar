"""
Antar - Brain console API
=========================
GET  /api/console/identity   who Antar is, how it thinks, and a card per console agent
GET  /api/console/evolution  how Antar has changed with use, counted from the stores that record it
GET  /api/console/learnings  what the records show today, as lines one agent tells another
POST /api/console/run        {agent, target} -> one agent's answer on one record
GET    /api/console/saved       the signed-in officer's saved findings, newest first
POST   /api/console/saved       keep a finding for a later investigation
DELETE /api/console/saved/{id}  remove one of the officer's own findings

`target` is either the node an officer dropped the agent on ({accused, fir_i, station,
district, crime_group}) or the word typed after `run <agent>`. See app/agents/brain_console.py.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.auth_middleware import current_identity

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


@router.get("/targets")
async def console_targets() -> dict:
    """Records to point an agent at when an answer names none of its own."""
    return await asyncio.to_thread(brain_console.starting_points)


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


# ── Saved findings: kept in the officer's own storage, never written to their disk ──

class SaveRequest(BaseModel):
    title: str = Field(default="", max_length=240)
    agent: str = Field(default="", max_length=32)
    label: str = Field(default="", max_length=200)
    result: dict = Field(default_factory=dict)
    was: str | None = Field(default=None, max_length=1400)
    was_at: str | None = Field(default=None, max_length=24)
    received_at: int | None = None


@router.get("/saved")
async def saved_list(request: Request, limit: int = 50) -> dict:
    from app.services import saved_findings
    return await asyncio.to_thread(saved_findings.list_for, current_identity(request).officer, limit)


@router.post("/saved")
async def saved_add(req: SaveRequest, request: Request) -> dict:
    """Keep a finding under the officer who is signed in. The officer comes from the
    sign-in token, never from the request body, so nobody saves into another's list."""
    from app.services import saved_findings
    try:
        return await asyncio.to_thread(saved_findings.save, current_identity(request).officer, req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/saved/{finding_id}")
async def saved_remove(finding_id: str, request: Request) -> dict:
    from app.services import saved_findings
    if not await asyncio.to_thread(saved_findings.remove, current_identity(request).officer, finding_id):
        raise HTTPException(status_code=404, detail="No saved finding with that id in your list.")
    return {"removed": finding_id}
