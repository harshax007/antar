"""
Antar - Antar insights for an audited answer
============================================
GET /api/answer-record/{audit_hash}/insights

Reads the answer's AI_REASONING entry in the audit log, checks that its digest still
verifies, and computes Antar insights over the FIRs THAT entry cites, never over what is
on screen. A missing or tampered entry is refused (404 / 409). Only the officer who asked,
or an Admin, may read them.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request

from app.core.auth_middleware import current_identity
from app.services import answer_insights, audit_store

router = APIRouter()


def _audited(audit_hash: str, request: Request, verb: str) -> tuple[dict, str, str]:
    """The answer's verified audit entry, for the officer who asked it (or an Admin)."""
    rec = audit_store.get_answer_record(audit_hash)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"This answer has no audit log entry, so it cannot be {verb}.")
    ident = current_identity(request)          # the same identity the chat recorded the answer under
    officer, role = ident.officer, ident.role
    if rec.get("officer") and officer != rec.get("officer") and role != "Admin":
        raise HTTPException(status_code=403, detail="Only the officer who asked this question can do this.")
    if not rec["verified"]:
        raise HTTPException(status_code=409, detail=f"The audit entry for this answer does not verify, so it was not {verb}.")
    return rec, officer, role


@router.get("/{audit_hash}/insights")
async def answer_insights_for(audit_hash: str, request: Request) -> dict:
    """Antar Insights for one answer, over the FIRs its audit entry cites (not the screen)."""
    rec, _, _ = _audited(audit_hash, request, "analysed")
    cites = rec.get("citations") or []
    if isinstance(cites, str):
        try:
            cites = json.loads(cites)
        except ValueError:
            cites = []
    out = await asyncio.to_thread(answer_insights.compute, answer_insights.fir_ids_from_citations(cites))
    return {**out, "answer_hash": rec["hash"]}
