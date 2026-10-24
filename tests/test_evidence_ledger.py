"""
Evidence Ledger (P0) — the synthetic FIR evidence layer + /api/evidence/*.

Covers:
  • alias_for(): exact JS-port arithmetic, determinism, membership, empty on no-digits
  • stats(): loads the CSV, sane coverage numbers
  • entity(): dossier contract, provenance rows, cross-district flag; None on unknown
  • search(): resolves by accused id / alias name / linkage key; deterministic ordering
  • endpoints: 200 contracts + 404 on unknown entity
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.services import evidence_ledger as ev


async def _get(path: str):
    from main import app as fastapi_app
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
        return await c.get(path)


# ── alias_for ─────────────────────────────────────────────────────────────────

class TestAliasFor:
    def test_matches_js_formula(self):
        # ACC-831453 → digits 831453 → FIRST[831453 % 24] + ' ' + LAST[(831453//24) % 16]
        first = ev._ALIAS_FIRST[831453 % len(ev._ALIAS_FIRST)]
        last = ev._ALIAS_LAST[(831453 // len(ev._ALIAS_FIRST)) % len(ev._ALIAS_LAST)]
        assert ev.alias_for("ACC-831453") == f"{first} {last}"

    def test_deterministic(self):
        assert ev.alias_for("ACC-217057") == ev.alias_for("ACC-217057")

    def test_membership(self):
        name = ev.alias_for("ACC-975758")
        f, l = name.split(" ", 1)
        assert f in ev._ALIAS_FIRST and l in ev._ALIAS_LAST

    def test_empty_on_no_digits(self):
        assert ev.alias_for("") == ""
        assert ev.alias_for(None) == ""
        assert ev.alias_for("ACC-") == ""


# ── stats / entity / search ─────────────────────────────────────────────────────

class TestStats:
    def test_loads_and_counts(self):
        s = ev.stats()
        assert s["rows"] > 2000, "evidence CSV should have loaded thousands of rows"
        assert s["accused"] > 100
        assert s["districts"] > 1
        assert isinstance(s["years"], list) and s["years"]
        assert "evidence layer" in s["source"]


class TestEntity:
    def _some_accused(self) -> str:
        hits = ev.search("ACC-", limit=1)
        assert hits, "expected at least one ACC- entity"
        return hits[0]["accused_id"]

    def test_dossier_contract(self):
        aid = self._some_accused()
        e = ev.entity(aid)
        assert e is not None
        for k in ("accused_id", "alias", "name_note", "fir_count", "districts",
                  "cross_district", "top_crimes", "vehicles", "upis", "ips", "years", "firs"):
            assert k in e, f"entity missing field {k}"
        assert e["accused_id"] == aid
        assert e["name_note"] == "synthetic alias"
        assert e["fir_count"] == len(ev._by_accused[aid])
        assert e["firs"], "entity must cite at least one FIR row"
        for f in e["firs"]:
            assert set(f) >= {"ref", "district", "crime", "year"}

    def test_unknown_returns_none(self):
        assert ev.entity("ACC-does-not-exist-000") is None


class TestSearch:
    def test_by_accused_id(self):
        aid = ev.search("ACC-", limit=1)[0]["accused_id"]
        hits = ev.search(aid, limit=5)
        assert any(h["accused_id"] == aid for h in hits)
        me = next(h for h in hits if h["accused_id"] == aid)
        assert me["match_field"] == "accused_id"

    def test_by_alias_name(self):
        aid = ev.search("ACC-", limit=1)[0]["accused_id"]
        name = ev.alias_for(aid)
        hits = ev.search(name, limit=25)
        assert any(h["accused_id"] == aid for h in hits), "alias name should resolve its entity"

    def test_deterministic_order(self):
        a = ev.search("ACC-", limit=10)
        b = ev.search("ACC-", limit=10)
        assert [h["accused_id"] for h in a] == [h["accused_id"] for h in b]

    def test_empty_query(self):
        assert ev.search("", limit=5) == []


# ── endpoints ────────────────────────────────────────────────────────────────

class TestEndpoints:
    @pytest.mark.anyio
    async def test_stats_200(self):
        r = await _get("/api/evidence/stats")
        assert r.status_code == 200
        assert r.json()["rows"] > 2000

    @pytest.mark.anyio
    async def test_search_200(self):
        r = await _get("/api/evidence/search?q=ACC-&limit=3")
        assert r.status_code == 200
        d = r.json()
        assert d["count"] == len(d["hits"]) and len(d["hits"]) <= 3

    @pytest.mark.anyio
    async def test_entity_200_and_404(self):
        aid = ev.search("ACC-", limit=1)[0]["accused_id"]
        ok = await _get(f"/api/evidence/entity/{aid}")
        assert ok.status_code == 200 and ok.json()["accused_id"] == aid
        missing = await _get("/api/evidence/entity/ACC-nope-000")
        assert missing.status_code == 404


def test_district_centroids_stay_in_karnataka():
    from app.services import evidence_ledger as e
    # a swapped pair is put back; a point outside the state is dropped
    assert e._ka_point(77.59, 12.97) == (12.97, 77.59)
    assert e._ka_point(28.6, 60.9) is None
    cent = e._district_centroids()
    assert cent and all(e._in_ka(c["lat"], c["lon"]) for c in cent.values())
