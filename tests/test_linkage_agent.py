"""
Acceptance Tests: A3 Linkage Agent (MO Case-Matcher) — REAL data.
=================================================================
Linkage candidates are COMPUTED from the evidence ledger via shared hard keys
(accused / vehicle / UPI / IP / place). Tests assert computed properties — real
candidate refs, transparent reason chips citing the shared key, determinism,
provenance — and that an id NOT in the evidence layer honestly yields zero candidates.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.agents import linkage_agent
from app.services import evidence_ledger as ev


def _priority_ref() -> str:
    refs = ev.priority_fir_refs(limit=1)
    assert refs, "expected at least one multi-FIR offender in the ledger"
    return refs[0]


class TestLinkageAgent:
    def test_real_linkage_has_candidates_and_chips(self):
        ref = _priority_ref()
        res = linkage_agent.compile_linkage(ref)
        assert res["fir_id"] == ref.upper()
        assert res["candidate_count"] >= 1, "a multi-FIR offender must link to ≥1 other FIR"
        c = res["candidates"][0]
        assert "total_score" in c and c["total_score"] >= 1
        assert c["reason_chips"], "every candidate must cite the shared key"
        assert c["linked_fir_id"].startswith("EV-")
        assert c["confidence"] in ("High", "Medium", "Low")

    def test_provenance_names_real_method(self):
        res = linkage_agent.compile_linkage(_priority_ref())
        assert res["provenance"]["agent"] == "A3: Linkage MO Case-Matcher"
        assert "shared hard-key" in res["provenance"]["method"]

    def test_deterministic(self):
        ref = _priority_ref()
        a = linkage_agent.compile_linkage(ref)["candidates"]
        b = linkage_agent.compile_linkage(ref)["candidates"]
        assert [(c["linked_fir_id"], c["total_score"]) for c in a] == [(c["linked_fir_id"], c["total_score"]) for c in b]

    def test_unknown_id_yields_zero_not_fabrication(self):
        # an official-style FIR id is not in the evidence layer → honest empty, no fake match
        res = linkage_agent.compile_linkage("FIR-2026-9999")
        assert res["candidate_count"] == 0
        assert res["candidates"] == []
        assert res["provenance"]["agent"] == "A3: Linkage MO Case-Matcher"


class TestLinkageEndpoints:
    @pytest.mark.anyio
    async def test_get_fir_linkage_endpoint(self):
        ref = _priority_ref()
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get(f"/api/linkage/{ref}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["linkage"]["fir_id"] == ref.upper()
        assert len(data["linkage"]["candidates"]) >= 1
