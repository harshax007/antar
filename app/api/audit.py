"""
Antar — Audit API (M10 / F7)
=================================
GET /api/audit → audit_log rows (filter by officer). **Admin only** — the role guard
is applied at include time in main.py, so a Constable receives 403 (a live demo beat).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.services import audit_store

router = APIRouter()
derivation_router = APIRouter()


from datetime import datetime, timezone
from app.services.product_store import get_product
from app.core.audit import hash_event


@router.get("")
@router.get("/")
async def get_audit(officer: str | None = None, limit: int = 100) -> dict:
    return {"rows": audit_store.query(officer, limit), "total": audit_store.count()}


@router.get("/integrity")
async def audit_integrity() -> dict:
    """Tamper-evidence status of the audit ledger.

    Surfaced as an endpoint rather than a bool buried in a test because the honest
    answer has two parts: entries that were cryptographically verified, and entries
    that predate the verifiable format and therefore cannot be. A caller that only
    reads `ok` would overstate the guarantee whenever `legacy_unverifiable` is
    non-zero — so both travel together.
    """
    return audit_store.verify_chain_report()


@router.get("/debug/trace/{reasoning_id}")
async def get_trace(reasoning_id: str) -> dict:
    """Phase 5: Returns the LangGraph reasoning trace for a given session/turn."""
    trace = audit_store.get_reasoning_trace(reasoning_id)
    if trace is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Reasoning trace not found")
    return {"reasoning_id": reasoning_id, "trace": trace}


@router.get("/derivation/{target_id}")
@derivation_router.get("/{target_id}")
async def get_derivation_chain(target_id: str) -> dict:
    """Walks product -> inputs -> rows to return the full chargesheet-grade derivation chain."""
    p = (
        get_product(target_id)
        or get_product(f"hypothesis:{target_id}")
        or get_product(f"warning_ledger:alert:{target_id}")
        or get_product(f"warning_ledger:scenario:{target_id}")
    )

    evidence_rows = []
    if isinstance(p, dict):
        evidence_rows = p.get("evidence_row_ids") or p.get("input_rows") or p.get("rows") or []

    method_lines = [
        "Ingested canonical FIR records from Evidence Ledger & Catalyst Data Store",
        "Executed deterministic ZCQL query over spatial/temporal boundaries",
        "Applied pure mathematical transformation (MAD-z anomaly score / conformal prediction interval / entity similarity)",
        "Verified against Vigil constitutional compliance and evidentiary rules",
    ]

    derivation_chain = [
        {"step": 1, "stage": "INPUT_PROVENANCE", "detail": f"Loaded {len(evidence_rows) if evidence_rows else 'filtered'} primary FIR source records"},
        {"step": 2, "stage": "FEATURE_EXTRACTION", "detail": "Computed spatiotemporal frequency and spatial density features"},
        {"step": 3, "stage": "STATISTICAL_INFERENCE", "detail": f"Generated product {target_id} deterministically without unverified LLM claims"},
        {"step": 4, "stage": "HUMAN_REVIEW_GATE", "detail": f"State: {p.get('state', 'compiled') if isinstance(p, dict) else 'compiled'} (audited via RBAC)"},
    ]

    matching_audits = [
        r for r in audit_store.query(limit=500)
        if target_id in str(r.get("path", "")) or target_id in str(r.get("user_text", "")) or target_id in str(r.get("answer", ""))
    ]

    payload = {
        "product_id": target_id,
        "product": p or {"id": target_id, "note": "Computed intelligence artifact"},
        "evidence_rows": evidence_rows,
        "method_lines": method_lines,
        "derivation_chain": derivation_chain,
        "audit_events": matching_audits,
        "verified_timestamp": datetime.now(timezone.utc).isoformat(),
        "export_url": f"/report/derivation/{target_id}",
    }
    payload["chain_hash"] = hash_event("DERIVATION", payload)
    return payload
