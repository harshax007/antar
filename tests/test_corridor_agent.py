"""
Acceptance Tests: A2 Corridor Agent (Movement Intelligence) — REAL data.
=======================================================================
Corridors are COMPUTED from the evidence ledger (an accused appearing in ≥2 districts
links that pair). These tests assert computed properties — determinism, structure,
provenance, and that every field traces to real accused — NOT hardcoded fixture values.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.agents import corridor_agent
from app.services import evidence_ledger as ev


class TestCorridorAgent:
    def test_compile_structure_and_provenance(self):
        corridors = corridor_agent.compile_corridors()
        assert len(corridors) >= 1
        c = corridors[0]
        assert "corridor_id" in c
        assert "next_district_estimate" in c
        assert c["provenance"]["agent"] == "A2: Corridor Movement Intelligence"
        # provenance must name the REAL method and cite the input accused
        assert "shared-accused" in c["provenance"]["method"]
        assert c["provenance"]["input_accused"], "must cite the accused that formed the corridor"

    def test_fields_are_computed_from_real_accused(self):
        c = corridor_agent.compile_corridors()[0]
        # src/dst are real, distinct districts; weight = # linking offenders (>=1)
        assert c["src"] and c["dst"] and c["src"] != c["dst"]
        assert c["weight"] >= 1
        # every involved offender is a real evidence-ledger accused, labeled synthetic
        for ent in c["involved_entities"]:
            assert ev.entity(ent["id"]) is not None, f"{ent['id']} must be a real ledger entity"
            assert ent["name_note"] == "synthetic alias"
            assert ent["name"] == ev.alias_for(ent["id"])
        # next-district probability is a real fraction, never fabricated > 1
        p = c["next_district_estimate"]["probability"]
        assert 0.0 <= p <= 1.0

    def test_deterministic(self):
        a = corridor_agent.compile_corridors()
        b = corridor_agent.compile_corridors()
        assert [(c["src"], c["dst"], c["weight"]) for c in a] == [(c["src"], c["dst"], c["weight"]) for c in b]

    def test_get_corridor_roundtrip(self):
        top = corridor_agent.compile_corridors()[0]
        got = corridor_agent.get_corridor(top["src"], top["dst"])
        assert got is not None
        assert got["src"] == top["src"] and got["dst"] == top["dst"]


class TestCorridorEndpoints:
    @pytest.mark.anyio
    async def test_list_corridors_endpoint(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get("/api/corridors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert isinstance(data["corridors"], list)

    @pytest.mark.anyio
    async def test_get_corridor_endpoint_real_pair(self):
        top = corridor_agent.compile_corridors()[0]
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get(f"/api/corridors/{top['src']}/{top['dst']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["corridor"]["src"] == top["src"]
