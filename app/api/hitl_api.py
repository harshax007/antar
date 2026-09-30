"""
Antar — Human-in-the-Loop approvals API (/api/hitl)
===================================================
The officer's identity and role come from auth_middleware.raw_identity(): the signed
bearer token when ANTAR_AUTH_SECRET is set, else the X-Officer / X-Role headers. All the
separation-of-duties rules live in app/core/hitl.py; this layer only maps them to HTTP.

  POST /api/hitl/propose                 propose an action           (Inspector/Analyst/Admin)
  GET  /api/hitl/queue?status=&mine=     list actions
  GET  /api/hitl/stats                   counts for the nav badge / dashboard
  GET  /api/hitl/types                   reviewable action types
  GET  /api/hitl/deployments             patrol orders currently in force
  GET  /api/hitl/{id}                    one action (integrity re-verified)
  POST /api/hitl/{id}/approve            approve + execute           (Approver, not the proposer)
  POST /api/hitl/{id}/reject             reject                      (Approver, not the proposer)
  POST /api/hitl/{id}/withdraw           withdraw own pending action (proposer)
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core import hitl
from app.core.auth_middleware import raw_identity

router = APIRouter()


class ProposeRequest(BaseModel):
    action_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    justification: str = ""
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=20)


class DecisionRequest(BaseModel):
    reason: str = ""
    payload_hash: str = ""      # the hash of the version the approver reviewed (approve only)


def _who(request: Request) -> tuple[str, str]:
    return raw_identity(request)


async def _call(fn, *args, **kwargs):
    try:
        return await asyncio.to_thread(fn, *args, **kwargs)
    except hitl.HitlError as e:
        raise HTTPException(status_code=e.code, detail=e.detail())


@router.post("/propose", status_code=201)
async def propose(req: ProposeRequest, request: Request) -> dict:
    officer, role = _who(request)
    return await _call(hitl.propose, req.action_type, req.payload, officer=officer, role=role,
                       justification=req.justification, evidence=req.evidence)


@router.get("/queue")
async def queue(request: Request, status: str = "pending", mine: bool = False,
                limit: int = 100) -> dict:
    officer = _who(request)[0] if mine else None
    items = await _call(hitl.list_actions, status=status, officer=officer, limit=limit)
    return {"count": len(items), "items": items}


@router.get("/stats")
async def stats() -> dict:
    return await _call(hitl.stats)


@router.get("/types")
async def types() -> dict:
    return {"types": [
        {"action_type": k, "label": v["label"], "risk": v["risk"], "ttl_hours": v["ttl_hours"], "agent": v["agent"]}
        for k, v in hitl.ACTION_TYPES.items()
    ], "proposer_roles": sorted(hitl.PROPOSER_ROLES), "approver_roles": sorted(hitl.APPROVER_ROLES)}


@router.get("/deployments")
async def deployments() -> dict:
    orders = hitl.active_deployments()
    return {"count": len(orders), "orders": orders}


@router.get("/{action_id}")
async def get_action(action_id: str) -> dict:
    return await _call(hitl.get, action_id)


@router.post("/{action_id}/approve")
async def approve(action_id: str, req: DecisionRequest, request: Request) -> dict:
    officer, role = _who(request)
    return await _call(hitl.approve, action_id, officer=officer, role=role,
                       reason=req.reason, reviewed_hash=req.payload_hash)


@router.post("/{action_id}/reject")
async def reject(action_id: str, req: DecisionRequest, request: Request) -> dict:
    officer, role = _who(request)
    return await _call(hitl.reject, action_id, officer=officer, role=role, reason=req.reason)


@router.post("/{action_id}/withdraw")
async def withdraw(action_id: str, req: DecisionRequest, request: Request) -> dict:
    officer, role = _who(request)
    return await _call(hitl.withdraw, action_id, officer=officer, role=role, reason=req.reason)
