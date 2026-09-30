"""
Antar — Layer 4: Hypothesis Lifecycle Ledger & RBAC API
=========================================================
Endpoints for human-in-the-loop transition of intelligence hypotheses:
  proposed → shown → confirmed | rejected

Enforces:
  1. RBAC (Inspector+ role required to confirm or reject)
  2. Cryptographic audit logging via record_hypothesis_event
  3. Second Brain institutional memory integration (learning from confirmed/disproven hypotheses)
  4. ADVERSARIAL REVIEW — see below

Adversarial gate (adversarial_audit)
----------------------------------
Confirming transitions a hypothesis from Inferred to Known. That is the single most
consequential state change in the system: after it, downstream agents treat the claim as
fact and the Second Brain ingests it as institutional memory. A bad promotion does not
just produce a wrong answer, it teaches the system to keep being wrong.

So every confirm runs the hypothesis past `adversarial_audit` first. If the adversarial
review finds the evidence collapses under its own base rates, the confirm is REFUSED with
409 and the full rebuttal in the response — until the officer resubmits with
`acknowledge_challenge=true` AND a written reason.

This deliberately does not block the officer. They hold authority the system does not, and
an investigator who knows something the data cannot see must be able to proceed. What it
does is make overriding a considered, recorded act rather than a click: the verdict and the
officer's stated reason are written into the audit chain together.

Rejection is never gated — that is the safe direction — but the review is still attached,
and whether the officer AGREED with it is recorded. That agreement rate is the calibration
signal for whether the adversarial layer is earning its place.
"""

import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from app.core.security import public_message as _public_message
from pydantic import BaseModel

from app.services.product_store import get_product, put_product, list_products
from app.services.audit_store import record_hypothesis_event
from app.second_brain.ingestion import ingest_confirmed_hypothesis, ingest_disproven_hypothesis

router = APIRouter(tags=["hypothesis"])

INSPECTOR_PLUS_ROLES = {
    "inspector",
    "dcp",
    "acp",
    "admin",
    "commissioner",
    "superintendent",
    "sub-inspector",
}

# Verdicts that require an explicit, reasoned override before a confirm is allowed.
# UNASSESSABLE is deliberately NOT gated: when the subjects cannot be resolved there is no
# argument to answer, and refusing would be the system blocking on its own blind spot.
GATED_VERDICTS = {"COLLAPSES", "WEAKENED"}


class HypothesisActionRequest(BaseModel):
    officer: str = "OF-1004"
    role: str = "Inspector"
    reason: str = ""
    # Set true to proceed past a COLLAPSES/WEAKENED adversarial verdict. Requires `reason`.
    acknowledge_challenge: bool = False


def _bind_identity(req: "HypothesisActionRequest", request: Request) -> "HypothesisActionRequest":
    """With signed identity on, WHO confirmed a hypothesis comes from the verified token,
    never from the request body. Header mode keeps the body fields (demo compatibility)."""
    from app.core.auth_middleware import auth_mode, current_identity
    if auth_mode() == "signed":
        if request is None:          # direct (non-HTTP) call cannot prove who it is
            raise HTTPException(status_code=401, detail="Authentication required.")
        ident = current_identity(request)
        return req.model_copy(update={"officer": ident.officer, "role": ident.role})
    return req


@router.get("/hypothesis")
async def list_hypotheses(limit: int = 20) -> dict:
    """List stored hypotheses from product_store."""
    keys = list_products(prefix="hypothesis:")
    items = []
    for k in keys[:limit]:
        p = get_product(k)
        if p:
            items.append(p)
    return {"count": len(items), "hypotheses": items}


@router.get("/hypothesis/{hypothesis_id}")
async def get_hypothesis(hypothesis_id: str) -> dict:
    """Get a specific hypothesis by ID."""
    key = f"hypothesis:{hypothesis_id}"
    p = get_product(key)
    if not p:
        # Return default structured hypothesis representation if not found
        p = {
            "id": hypothesis_id,
            "kind": "association",
            "claim": f"Inferred pattern candidate for {hypothesis_id}",
            "state": "proposed",
            "score": 0.78,
            "badge": "INFERRED",
        }
    return p


def _default_hypothesis(hypothesis_id: str) -> dict:
    return {
        "id": hypothesis_id,
        "kind": "association",
        "claim": f"Inferred pattern candidate {hypothesis_id}",
        "score": 0.78,
    }


async def _review(hypothesis: dict) -> dict:
    """Run the adversarial review. Never raises — a broken auditor must not block an
    officer, but it must also never be mistaken for a clean bill of health, so a failure
    surfaces as UNASSESSABLE (which is not a gated verdict and not an endorsement)."""
    try:
        from app.agents import adversarial_audit as da
        return await asyncio.to_thread(da.challenge, hypothesis)
    except Exception as exc:                      # noqa: BLE001 — review is advisory
        return {
            "verdict": "UNASSESSABLE",
            "verdict_reason": _public_message(exc, "review"),
            "signals": [], "alternatives": [], "falsification_tests": [],
        }


def _digest(review: dict) -> dict:
    """The part of a review worth persisting on the hypothesis record."""
    return {
        "verdict": review.get("verdict"),
        "verdict_reason": review.get("verdict_reason"),
        "load_bearing_signals": review.get("load_bearing_signals", []),
        "discarded_signals": review.get("discarded_signals", []),
        "posterior_probability": (review.get("combined") or {}).get("posterior_probability"),
        "expected_false_matches": (review.get("selection_effect") or {}).get("expected_false_matches"),
        "reviewed_at": review.get("compiled_at"),
    }


@router.get("/hypothesis/{hypothesis_id}/challenge")
async def challenge_hypothesis(hypothesis_id: str) -> dict:
    """The case AGAINST this hypothesis, without acting on it.

    Read-only: this is what an officer should see next to the Confirm button, and it is
    the same review the confirm endpoint will run.
    """
    p = get_product(f"hypothesis:{hypothesis_id}") or _default_hypothesis(hypothesis_id)
    review = await _review(p)
    return {
        "hypothesis_id": hypothesis_id,
        "hypothesis": p,
        "review": review,
        "would_gate_confirm": review.get("verdict") in GATED_VERDICTS,
    }


@router.post("/hypothesis/{hypothesis_id}/confirm")
async def confirm_hypothesis(hypothesis_id: str, req: HypothesisActionRequest,
                             request: Request = None) -> dict:
    req = _bind_identity(req, request)
    """Confirm a hypothesis (RBAC: Inspector+ required). Transitions I -> K.

    Runs the adversarial review first; a gated verdict requires an acknowledged,
    reasoned override (409 otherwise). See the module docstring.
    """
    role_norm = (req.role or "").strip().lower()
    if role_norm not in INSPECTOR_PLUS_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"RBAC violation: Role '{req.role}' is not authorized to confirm hypotheses. Inspector or higher rank required."
        )

    key = f"hypothesis:{hypothesis_id}"
    p = get_product(key) or _default_hypothesis(hypothesis_id)

    # ── adversarial gate ──────────────────────────────────────────────────────
    review = await _review(p)
    verdict = review.get("verdict")
    gated = verdict in GATED_VERDICTS

    if gated and not req.acknowledge_challenge:
        raise HTTPException(status_code=409, detail={
            "error": "adversarial_review_not_acknowledged",
            "message": (f"Adversarial review returned {verdict}. This hypothesis cannot be "
                        "promoted to Known until the review is acknowledged in writing."),
            "hypothesis_id": hypothesis_id,
            "verdict": verdict,
            "verdict_reason": review.get("verdict_reason"),
            "load_bearing_signals": review.get("load_bearing_signals", []),
            "discarded_signals": review.get("discarded_signals", []),
            "alternatives": review.get("alternatives", []),
            "falsification_tests": review.get("falsification_tests", []),
            "selection_effect": review.get("selection_effect"),
            "how_to_proceed": ("resubmit with acknowledge_challenge=true and a non-empty "
                               "reason; both the verdict and your reason are written to the "
                               "audit log"),
        })

    if gated and not (req.reason or "").strip():
        raise HTTPException(status_code=422, detail={
            "error": "override_reason_required",
            "message": (f"Overriding a {verdict} adversarial verdict requires a written "
                        "reason. An unexplained override is not a record of a decision."),
            "hypothesis_id": hypothesis_id,
            "verdict": verdict,
        })

    # ── commit ────────────────────────────────────────────────────────────────
    p["state"] = "confirmed"
    p["state_by"] = req.officer
    p["state_role"] = req.role
    p["state_at"] = datetime.now(timezone.utc).isoformat()
    p["confirm_reason"] = req.reason
    p["adversarial_review"] = _digest(review)
    p["adversarial_override"] = gated
    put_product(key, p, ttl=86400 * 30)

    # The verdict travels inside `reason` rather than as a new payload key, so it is
    # covered by the audit hash AND survives the reload path (record_hypothesis_event
    # persists reason to the `answer` column; extra payload keys are not persisted).
    audit_reason = req.reason or "Confirmed by officer"
    audit_reason = f"[adversarial:{verdict}] " + (
        f"OVERRIDE — {audit_reason}" if gated else audit_reason)

    audit_entry = record_hypothesis_event(
        "hypothesis_confirmed",
        hypothesis_id=hypothesis_id,
        officer=req.officer,
        role=req.role,
        reason=audit_reason,
    )

    memory_id = ingest_confirmed_hypothesis(
        hypothesis_id=hypothesis_id,
        summary_text=p.get("claim", hypothesis_id),
    )

    return {
        "status": "confirmed",
        "hypothesis_id": hypothesis_id,
        "product": p,
        "audit_entry": audit_entry,
        "memory_id": memory_id,
        "adversarial_review": review,
        "adversarial_override": gated,
    }


@router.post("/hypothesis/{hypothesis_id}/reject")
async def reject_hypothesis(hypothesis_id: str, req: HypothesisActionRequest,
                            request: Request = None) -> dict:
    req = _bind_identity(req, request)
    """Reject a hypothesis (RBAC: Inspector+ required). Ingests disproven precedent."""
    role_norm = (req.role or "").strip().lower()
    if role_norm not in INSPECTOR_PLUS_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"RBAC violation: Role '{req.role}' is not authorized to reject hypotheses. Inspector or higher rank required."
        )

    key = f"hypothesis:{hypothesis_id}"
    p = get_product(key) or _default_hypothesis(hypothesis_id)

    # Rejection is never gated — it is the safe direction. The review is still attached,
    # and whether the officer reached the same conclusion is recorded: agreement rate is
    # the calibration signal for whether the adversarial layer is worth its latency.
    review = await _review(p)
    verdict = review.get("verdict")
    agreed = verdict in GATED_VERDICTS          # auditor also doubted it

    p["state"] = "rejected"
    p["state_by"] = req.officer
    p["state_role"] = req.role
    p["state_at"] = datetime.now(timezone.utc).isoformat()
    p["rejection_reason"] = req.reason
    p["adversarial_review"] = _digest(review)
    p["adversarial_agreement"] = agreed
    put_product(key, p, ttl=86400 * 30)

    audit_entry = record_hypothesis_event(
        "hypothesis_rejected",
        hypothesis_id=hypothesis_id,
        officer=req.officer,
        role=req.role,
        reason=f"[adversarial:{verdict}] " + (req.reason or "Rejected by officer"),
    )

    memory_id = ingest_disproven_hypothesis(
        hypothesis_id=hypothesis_id,
        summary_text=p.get("claim", hypothesis_id),
        reason=req.reason,
    )

    return {
        "status": "rejected",
        "hypothesis_id": hypothesis_id,
        "product": p,
        "audit_entry": audit_entry,
        "memory_id": memory_id,
        "adversarial_review": review,
        "adversarial_agreement": agreed,
    }
