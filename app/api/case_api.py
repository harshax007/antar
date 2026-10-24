"""
Antar - Case timeline API
=========================
GET /api/case/{fir_id}   one FIR: an automated summary, its investigation timeline, how
                         cases like it ended, and the accused's other FIRs.

Case-level data, so Constable and above (mounted with that dependency in main.py), and the
same need-to-know rule as chat: below Analyst, an officer with a posting opens cases of
their own district only. A Policymaker never reaches it (the gateway allowlist).
"""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services import case_timeline
from app.services.zcql_repo import scoped_posting

router = APIRouter()


@router.get("/{fir_id}")
async def case(fir_id: str, station: Optional[str] = None) -> dict:
    fir = " ".join(str(fir_id or "").split())[:40]
    if not fir:
        raise HTTPException(status_code=422, detail="An FIR id is required.")
    data = await asyncio.to_thread(case_timeline.timeline, fir, station)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No FIR {fir} in the register.")
    posting = scoped_posting()
    if posting and posting.strip().upper() not in {str(data.get("zone") or "").strip().upper(),
                                                   str(data.get("district") or "").strip().upper()}:
        raise HTTPException(status_code=403, detail=f"This FIR is outside your posting ({posting}).")
    data.pop("zone", None)
    return data
