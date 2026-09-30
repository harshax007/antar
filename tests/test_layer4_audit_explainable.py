"""
Tests for Layer 4 — Audit & Explainable-Ready AI
=================================================
Verifies:
  1. Hypothesis Lifecycle Ledger & RBAC transitions (confirm/reject)
  2. Derivation Chain Export (chargesheet-grade provenance + SHA-256 hash)
  3. Vigil Gate compliance verification (§0.4-2 enforcement)
"""

import pytest
from fastapi import HTTPException
from app.api.hypothesis import (
    confirm_hypothesis,
    reject_hypothesis,
    get_hypothesis,
    HypothesisActionRequest,
)
from app.api.audit import get_derivation_chain
from app.agents.agentic_spine import verify_claims


@pytest.mark.anyio
async def test_hypothesis_lifecycle_and_rbac():
    # 1. Test RBAC failure (Constable role cannot confirm)
    req_unauth = HypothesisActionRequest(officer="OF-999", role="Constable", reason="Attempted confirm")
    with pytest.raises(HTTPException) as exc_info:
        await confirm_hypothesis("HYP-TEST-L4-1", req_unauth)
    assert exc_info.value.status_code == 403
    assert "RBAC violation" in exc_info.value.detail

    # 2. Test successful confirm by Inspector
    req_auth = HypothesisActionRequest(officer="OF-1004", role="Inspector", reason="CCTV corroborated")
    res_confirm = await confirm_hypothesis("HYP-TEST-L4-1", req_auth)
    assert res_confirm["status"] == "confirmed"
    assert res_confirm["product"]["state"] == "confirmed"
    assert res_confirm["product"]["state_by"] == "OF-1004"
    assert res_confirm["audit_entry"]["type"] == "hypothesis_confirmed"
    assert "hash" in res_confirm["audit_entry"]
    assert res_confirm["memory_id"] == "CONF-HYP-TEST-L4-1"

    # 3. Test successful reject by ACP
    req_reject = HypothesisActionRequest(officer="OF-1001", role="ACP", reason="Alibi verified")
    res_reject = await reject_hypothesis("HYP-TEST-L4-2", req_reject)
    assert res_reject["status"] == "rejected"
    assert res_reject["product"]["state"] == "rejected"
    assert res_reject["audit_entry"]["type"] == "hypothesis_rejected"
    assert res_reject["memory_id"] == "DISP-HYP-TEST-L4-2"


@pytest.mark.anyio
async def test_derivation_chain_completeness():
    data = await get_derivation_chain("HYP-TEST-L4-1")
    assert data["product_id"] == "HYP-TEST-L4-1"
    assert "method_lines" in data
    assert len(data["method_lines"]) >= 3
    assert "derivation_chain" in data
    assert len(data["derivation_chain"]) == 4
    assert "chain_hash" in data
    assert len(data["chain_hash"]) == 64
    assert data["export_url"] == "/report/derivation/HYP-TEST-L4-1"


def test_vigil_compliance_gate():
    claims = [
        {
            "text": "FIR 2026-05 mentions suspect K.",
            "citation": {"fir": "2026-05"},
        },
        {
            "text": "[INFERRED] Inferred corridor link between Rajajinagar and Yeshwanthpur.",
            "kind": "inferred",
            "hypothesis_id": "HYP-101",
        },
        {
            "text": "Ungrounded claim with no evidence or markers",
        },
    ]

    # In audit mode, all claims are returned and tagged
    res_audit = verify_claims(claims, audit_mode=True)
    assert len(res_audit) == 3
    assert res_audit[0]["vigil_compliance"] == "APPROVED"
    assert res_audit[1]["vigil_compliance"] == "APPROVED"
    assert res_audit[2]["vigil_compliance"] == "FLAGGED"

    # In default/export mode, flagged claims are dropped
    res_export = verify_claims(claims, audit_mode=False)
    assert len(res_export) == 2
    assert all(c["vigil_compliance"] == "APPROVED" for c in res_export)
