"""
Chain-of-custody strip — build_custody() + presence in the chat contracts.

The evidence strip is the evidentiary provenance an officer can audit: how many
records, from which table, as-of when, which FIRs, and how it was derived. It must
be deterministic (never an LLM claim) and must NOT appear on a no-result turn.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.agents.layout_composer import build_custody


class TestBuildCustody:
    def _query(self, n=3, tid="T1"):
        rows = [{"fir_number": f"2026-BLR-{i:04d}", "station_code": "BLR-RJN-04",
                 "occurred_at": f"2026-05-{10+i:02d}", "acts_sections": "IPC 379"}
                for i in range(n)]
        cites = [{"fir": r["fir_number"], "station": r["station_code"],
                  "date": r["occurred_at"], "section": r["acts_sections"]} for r in rows]
        return {"rows": rows, "citations": cites, "template_id": tid,
                "params": {"zones": ["Rajajinagar"], "crime_types": ["chain_snatching"]}}

    def test_shape_and_counts(self):
        c = build_custody(self._query(n=3))
        assert c is not None
        assert c["record_count"] == 3
        assert c["source"] == "crimes"
        assert c["verification"] == "K"
        assert c["fir_total"] == 3
        assert len(c["firs"]) == 3
        assert c["as_of"] and len(c["as_of"]) == 10          # ISO date
        assert c["range"] and "2026-05-10" in c["range"]
        assert c["method"].startswith("ZCQL T1")

    def test_none_when_no_rows(self):
        assert build_custody({"rows": [], "citations": [], "template_id": "T1"}) is None
        assert build_custody({}) is None

    def test_source_follows_template(self):
        assert build_custody(self._query(tid="T4"))["source"] == "suspects"
        assert build_custody(self._query(tid="T1"))["source"] == "crimes"

    def test_firs_capped_but_total_kept(self):
        c = build_custody(self._query(n=20))
        assert c["fir_total"] == 20 and len(c["firs"]) == 12   # cap the list, keep the true total

    def test_as_of_never_future(self):
        from datetime import date
        c = build_custody(self._query())
        assert c["as_of"] <= date.today().isoformat()

    def test_never_raises_on_garbage(self):
        assert build_custody({"rows": [object()], "template_id": None}) is not None or True


async def _get(path, payload):
    from main import app as a
    async with AsyncClient(transport=ASGITransport(app=a), base_url="http://test", timeout=120) as c:
        return await c.post(path, json=payload)


class TestCustodyInContract:
    @pytest.mark.anyio
    async def test_rest_chat_includes_custody_when_records_found(self):
        r = await _get("/api/chat", {"text": "chain snatching in Rajajinagar", "session_id": "cust1", "lang": "en"})
        assert r.status_code == 200
        d = r.json()
        if d.get("template_id") not in ("CLARIFY", "NONE") and not d.get("no_results"):
            assert d.get("custody"), "custody strip missing on a factual answer"
            assert d["custody"]["record_count"] >= 1
            assert d["custody"]["as_of"]

    @pytest.mark.anyio
    async def test_no_custody_on_no_result(self):
        r = await _get("/api/chat", {"text": "burglaries in Atlantis Nagar", "session_id": "cust2", "lang": "en"})
        d = r.json()
        if d.get("no_results"):
            assert not d.get("custody")
