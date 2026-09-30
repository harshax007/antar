"""
Antar — Sentinel API (A1: Watchlists & Tripwires · Phase 1)
================================================================
Endpoints for managing officer watchlists and scanning for tripwire hits.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.agents import sentinel_agent

router = APIRouter()

@router.get("")
@router.get("/")
async def get_sentinel_alerts(limit: int = 50) -> dict:
    from app.services import alerts_store
    alerts = alerts_store.list_recent(limit)
    sentinel_alerts = [a for a in alerts if a.get("alert_type") == "sentinel_tripwire"]
    return {"alerts": sentinel_alerts, "active": len(sentinel_alerts)}



class RegisterWatchRequest(BaseModel):
    watch_type: str
    target: str
    label: str = ""
    justification: str = ""
    evidence: list[dict] = []


@router.get("/watches")
async def get_watches(officer_id: str = None) -> dict:
    """List all registered watchlists and tripwires."""
    watches = sentinel_agent.list_watches(officer_id=officer_id)
    return {"count": len(watches), "watches": watches}


@router.post("/watches", status_code=202)
async def create_watch(req: RegisterWatchRequest, request: Request) -> dict:
    """Request a new watchlist tripwire.

    Putting a person or pattern under watch is a real-world effect, so this no longer
    registers the watch directly: it is parked for a supervising officer's approval
    (app/core/hitl.py) and only takes effect once approved. Returns 202 + the action.
    """
    import asyncio
    from app.core import hitl
    from app.core.auth_middleware import raw_identity
    _officer, _role = raw_identity(request)
    try:
        action = await asyncio.to_thread(
            hitl.propose, "watchlist_add",
            {"watch_type": req.watch_type, "target": req.target, "label": req.label},
            officer=_officer, role=_role,
            justification=req.justification, evidence=req.evidence)
    except hitl.HitlError as e:
        raise HTTPException(status_code=e.code, detail=e.detail())
    return {"ok": True, "status": "pending_approval", "action": action}


@router.post("/scan")
async def run_scan() -> dict:
    """Trigger a manual Sentinel scan against all active watchlists."""
    hits = sentinel_agent.scan_watches()
    return {"ok": True, "hits_detected": len(hits), "hits": hits}
