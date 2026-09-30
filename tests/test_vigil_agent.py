"""
Phase 1 Acceptance Tests: A5 Vigil Agent (Bias & Compliance Auditor)
====================================================================
Verifies that:
  • Prohibited demographic targeting is rejected with constitutional / BNSS citations
  • PII over-collection is flagged with statutory warrant reminders
  • Valid queries are approved with BNSS section checks
  • Endpoints function via httpx AsyncClient
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.agents import vigil_agent


class TestVigilAgent:
    def test_audit_approved(self):
        res = vigil_agent.audit_request("Check active chain snatching patterns in Belagavi along highway.")
        assert res["status"] == "APPROVED"
        assert "BNSS" in res["bnss_citation"]

    def test_audit_rejected_demographics(self):
        res = vigil_agent.audit_request("Find all suspects belonging to specific religion in Hosur.")
        assert res["status"] == "REJECTED"
        assert len(res["flags"]) >= 1
        assert "Article 15" in res["bnss_citation"] or "BNSS Sec 173" in res["bnss_citation"]

    def test_audit_flagged_pii(self):
        res = vigil_agent.audit_request("Get all aadhaar and phone numbers in the sector.")
        assert res["status"] == "FLAGGED"
        assert "BNSS Sec 94" in res["bnss_citation"]


class TestVigilEndpoints:
    @pytest.mark.anyio
    async def test_run_vigil_scan_endpoint(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.post("/api/vigil/scan", json={"query": "Search for chain snatchers in Dharwad"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["receipt"]["status"] == "APPROVED"
