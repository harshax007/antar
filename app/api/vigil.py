"""
Antar — Vigil API (A5: Bias & Compliance Auditor · Phase 1)
================================================================
Endpoints for real-time audit receipts, BNSS statutory citations,
and demographic equality compliance checks.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.agents import vigil_agent

router = APIRouter()


class VigilScanRequest(BaseModel):
    query: str
    officer: str | None = "OFF-001"
    req_id: str | None = None


@router.post("/scan")
async def run_vigil_scan(payload: VigilScanRequest) -> dict:
    """Audit a query/prompt for prohibited targeting, PII over-collection, and BNSS compliance."""
    receipt = vigil_agent.audit_request(
        query=payload.query,
        req_id=payload.req_id,
        officer=payload.officer or "OFF-001"
    )
    return {"ok": True, "receipt": receipt}


@router.get("/{req_id}")
async def get_vigil_receipt(req_id: str) -> dict:
    """Retrieve an existing compliance receipt from the Product Store."""
    receipt = vigil_agent.get_receipt(req_id)
    if not receipt:
        return {"ok": False, "error": f"No compliance receipt found for request ID {req_id}."}
    return {"ok": True, "receipt": receipt}
