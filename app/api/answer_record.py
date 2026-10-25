"""
Antar - Copy an answer exactly as it was audited
================================================
POST /api/answer-record/{audit_hash}/copy
GET  /api/answer-record/{audit_hash}/insights   Antar Insights over the FIRs it cites

The Expert workspace's Copy button does not copy what is on screen. It asks for the
answer's own AI_REASONING entry in the audit log, checks that the entry's digest still
verifies, builds the brief from THAT text (question, answer, cited FIRs, audit id) and
records an ANSWER_COPIED event carrying the SHA-256 of the exact text returned. What
the officer pastes is therefore the audited answer, word for word, and the copy itself
is on the chain.

Refuses rather than falling back: an answer with no entry, or one whose digest no longer
verifies, is not copied (409). Only the officer who asked, or an Admin, may copy it.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request

from app.core.auth_middleware import current_identity
from app.services import answer_insights, audit_store

router = APIRouter()

_IST = timezone(timedelta(hours=5, minutes=30))


def _when(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).astimezone(_IST).strftime("%d %b %Y, %H:%M IST")
    except (TypeError, ValueError):
        return str(ts or "")


def _citation_line(c) -> str:
    if isinstance(c, dict):
        fir = c.get("fir") or c.get("id") or ""
        rest = [str(c.get(k)) for k in ("station", "section", "date") if c.get(k)]
        return f"- FIR {fir}" + (f", {', '.join(rest)}" if rest else "")
    return f"- {c}"


def build_copy_text(rec: dict) -> str:
    """The brief as it is placed on the clipboard. Every line comes from the audit entry."""
    cites = rec.get("citations") or []
    if isinstance(cites, str):
        try:
            cites = json.loads(cites)
        except ValueError:
            cites = []
    lines = [f"Antar brief · answered {_when(rec.get('ts'))}"]
    if rec.get("officer"):
        lines.append(f"Officer: {rec['officer']}")
    lines += ["", f"Question: {rec.get('user_text') or ''}", "", "Answer:", str(rec.get("answer") or "")]
    if cites:
        lines += ["", f"Cited FIRs ({len(cites)}):"] + [_citation_line(c) for c in cites]
    lines += ["", f"Audit log entry: {rec['hash']} (verified)",
              "Copied from the audit log, word for word. Verify against the cited FIRs before use."]
    return "\n".join(lines)


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


@router.post("/{audit_hash}/copy")
async def copy_answer(audit_hash: str, request: Request) -> dict:
    rec, officer, role = _audited(audit_hash, request, "copied")
    text = build_copy_text(rec)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    event = audit_store.record_answer_copied(officer, role, rec["hash"], sha, len(text))
    return {"text": text, "answer_hash": rec["hash"], "copy_sha256": sha, "copy_event_hash": event["hash"]}


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
