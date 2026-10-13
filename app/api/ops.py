"""
Antar — Orchestrator Ops API
=================================
GET  /api/orchestrator/status   — agent registry, telemetry, circuit states,
                                  autonomous-loop stats (production orchestration)
POST /api/orchestrator/refresh  — force-refresh all registered products now
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth_middleware import require_role

from app.core import orchestrator

router = APIRouter()


@router.get("/status")
async def orchestrator_status() -> dict:
    return orchestrator.status()


@router.get("/egress", dependencies=[Depends(require_role("Admin"))])
async def outbound_calls() -> dict:
    """What this server may call, and what it has called or refused since it started.
    Hosts and purposes only - never a body, a path or a credential."""
    from app.core import egress
    from app.services import llm
    return {**egress.snapshot(), "language_model": llm.describe()}


@router.post("/refresh")
async def orchestrator_refresh() -> dict:
    from app.services import product_store
    latencies = product_store.refresh_all()
    return {"refreshed": latencies, "count": len(latencies)}
