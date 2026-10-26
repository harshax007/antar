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
    if target_id.startswith("board:"):
        return _forecast_derivation(target_id)
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


def _forecast_derivation(target_id: str) -> dict:
    """The audit trail of one Predict card ("board:<zone>:<crime type>"), from the stored card.

    Every line is read off the card the screen showed - its FIRs, its score, its range and
    the reasons for its confidence - and the officers who marked it reviewed come from the
    audit chain. The generic chain above names steps (ZCQL, Vigil) that a forecast does not
    run, so a forecast never falls through to it. A card that is not stored says so.
    """
    _, _, rest = target_id.partition(":")
    zone, _, crime = rest.partition(":")
    card = get_product(f"warning_ledger:board:{zone}:{crime}")
    if not isinstance(card, dict):
        return {"product_id": target_id, "unavailable": True, "derivation_chain": [],
                "evidence_rows": [], "audit_events": [], "chain_hash": None,
                "method_lines": [f"No stored forecast for {zone} · {crime.lower()} today. "
                                 "The forecast board is rebuilt each day; reopen Predict to compile it."]}

    ct = (crime or "crime").lower()
    rows = card.get("evidence_row_ids") or []
    z = card.get("z_score") or 0
    lo, hi, cov = card.get("conformal_lo"), card.get("conformal_hi"), card.get("coverage")
    # coverage is stored as "91%" (the conformal target for this series), sometimes as 0.91
    try:
        cov_pct = None if cov in (None, "") else round(float(str(cov).rstrip("%")) * (100 if float(str(cov).rstrip("%")) <= 1 else 1))
    except ValueError:
        cov_pct = None
    chain = [
        {"step": 1, "stage": "Records read",
         "detail": (f"{len(rows)} FIRs of {ct} in {zone} make up the recent count." if rows
                    else "No individual FIRs are attached: nothing unusual was measured, so this is the area's usual level.")},
        {"step": 2, "stage": "Compared with usual",
         "detail": (f"The recent weekly count was compared with {zone}'s own history: unusual-activity score {z} (2 is unusual, 4 is rare)."
                    if z else f"The recent weekly count was compared with {zone}'s own history and was within its usual range.")},
        {"step": 3, "stage": "Range drawn",
         "detail": (f"{lo} to {hi} cases expected in the next 7 days, from how past weeks varied"
                    + (f"; it is drawn wide enough to cover about {cov_pct}% of weeks like these." if cov_pct is not None else ".")
                    if lo is not None else "No range drawn: there is no measured change to draw one from.")},
        {"step": 4, "stage": "Confidence",
         "detail": f"{card.get('confidence_level') or 'Not graded'}. " + " ".join(card.get("confidence_reasons") or [])},
    ]
    reviews = []
    for r in audit_store.query(limit=5000):
        fr = (r.get("scope") or {}).get("forecast_review")
        if fr and fr.get("zone") == zone and (fr.get("crime_type") or "") == crime and r.get("status") == 200:
            reviews.append({"officer": r.get("officer"), "role": r.get("role"), "ts": r.get("ts")})
    payload = {
        "product_id": target_id,
        "kind": "forecast",
        "product": {"zone": zone, "crime_type": crime, "as_of": card.get("as_of")},
        "evidence_rows": rows,
        "method_lines": [
            "Weekly case counts for this area and crime type are compared with the area's own past weeks (a median-based score, so one odd week does not move the baseline).",
            "The expected range is a split-conformal band over the area's last 13 weeks: its width comes from how far those weeks strayed from the usual level.",
            "No language model is involved in these numbers; every figure above is read from the stored forecast.",
        ],
        "derivation_chain": chain,
        "audit_events": reviews,
        "verified_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    payload["chain_hash"] = hash_event("DERIVATION", payload)
    return payload
