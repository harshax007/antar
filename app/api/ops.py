"""
Antar — Orchestrator Ops API
=================================
GET  /api/orchestrator/status   — agent registry, telemetry, circuit states,
                                  autonomous-loop stats (production orchestration)
POST /api/orchestrator/refresh  — force-refresh all registered products now
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core import orchestrator

router = APIRouter()


@router.get("/status")
async def orchestrator_status() -> dict:
    return orchestrator.status()


@router.post("/refresh")
async def orchestrator_refresh() -> dict:
    from app.services import product_store
    latencies = product_store.refresh_all()
    return {"refreshed": latencies, "count": len(latencies)}
