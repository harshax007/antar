"""
Predict screen backend — GET /api/predict/board, GET /api/predict/{zone}/reasoning,
and the field-scoped /api/profile/search.

Covers:
  • board: 200, field contract, UI risk values, limit respected
  • reasoning: 200, 7-node DAG contract, real-valued sublabels, trace format
  • reasoning: unknown zone degrades gracefully (no 500)
  • search field param: restriction honoured per field, unknown field = all
"""

import pytest
from httpx import AsyncClient, ASGITransport


async def _get(path: str):
    from main import app as fastapi_app
    async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                           base_url="http://test") as c:
        return await c.get(path)


# ── /api/predict/board ────────────────────────────────────────────────────────

class TestPredictBoard:
    @pytest.mark.anyio
    async def test_200_and_top_keys(self):
        resp = await _get("/api/predict/board")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("predictions", "count", "engine"):
            assert key in data, f"missing top-level key: {key}"

    @pytest.mark.anyio
    async def test_prediction_field_contract(self):
        data = (await _get("/api/predict/board")).json()
        assert data["count"] == len(data["predictions"])
        required = {"zone", "crime_type", "risk", "confidence", "z_score", "band",
                    "coverage", "observed", "festival_driver", "why"}
        for p in data["predictions"]:
            missing = required - set(p.keys())
            assert not missing, f"prediction missing fields: {missing}"
            assert p["risk"] in {"HIGH", "MEDIUM", "LOW"}
            assert 0.0 <= p["confidence"] <= 1.0
            assert p["why"], "why must never be empty"

    @pytest.mark.anyio
    async def test_limit_respected(self):
        data = (await _get("/api/predict/board?limit=3")).json()
        assert len(data["predictions"]) <= 3

    @pytest.mark.anyio
    async def test_cached_board_speed_and_force_refresh(self):
        import time
        # 1. Warm up product cache (cold run or reuse existing)
        await _get("/api/predict/board?limit=2")

        # 2. Hot lookup — should hit warning_ledger:board:all instantly (< 0.5s)
        t0 = time.time()
        data_cached = (await _get("/api/predict/board?limit=2")).json()
        dt_cached = time.time() - t0
        assert dt_cached < 0.5, f"cached lookup took {dt_cached:.3f}s, expected < 0.5s"
        assert len(data_cached["predictions"]) <= 2

        # 3. Verify force=true bypasses cache and returns valid board
        data_force = (await _get("/api/predict/board?limit=2&force=true")).json()
        assert "predictions" in data_force and len(data_force["predictions"]) <= 2


# ── /api/predict/{zone}/reasoning ─────────────────────────────────────────────

class TestPredictReasoning:
    @pytest.mark.anyio
    async def test_dag_contract_for_board_zone(self):
        board = (await _get("/api/predict/board?limit=1")).json()
        if not board["predictions"]:
            pytest.skip("no alerts in seed world")
        p0 = board["predictions"][0]
        resp = await _get(f"/api/predict/{p0['zone']}/reasoning?crime_type={p0['crime_type']}")
        assert resp.status_code == 200
        d = resp.json()
        assert d["zone"] == p0["zone"]
        ids = [n["id"] for n in d["nodes"]]
        assert ids == ["data", "seasonal", "pattern", "forecast", "network", "supervisor", "out"]
        assert len(d["edges"]) == 8
        for n in d["nodes"]:
            assert n["sublabel"], f"node {n['id']} has empty sublabel"
        # trace lines follow the "agent ▸ message" format the UI parses
        assert len(d["trace"]) >= 5
        for line in d["trace"]:
            assert " ▸ " in line, f"malformed trace line: {line!r}"
        assert d["prediction"]["risk"] in {"HIGH", "MEDIUM", "LOW"}

    @pytest.mark.anyio
    async def test_unknown_zone_degrades_gracefully(self):
        resp = await _get("/api/predict/Nowhereville/reasoning")
        assert resp.status_code == 200
        d = resp.json()
        assert d["nodes"] and d["trace"]
        assert d["prediction"]["risk"] in {"HIGH", "MEDIUM", "LOW"}


# ── /api/profile/search?field= ────────────────────────────────────────────────

class TestSearchFieldScope:
    @pytest.mark.anyio
    async def test_alias_scope_only_matches_alias(self):
        d = (await _get("/api/profile/search?q=Tiger&threshold=0.55&field=alias")).json()
        assert d["field"] == "alias"
        for h in d["hits"]:
            assert h["match_field"] == "alias", f"{h['suspect_id']} matched {h['match_field']}"

    @pytest.mark.anyio
    async def test_name_scope_excludes_alias_matches(self):
        d = (await _get("/api/profile/search?q=Raju&threshold=0.55&field=name")).json()
        for h in d["hits"]:
            assert h["match_field"] == "full_name"

    @pytest.mark.anyio
    async def test_phone_scope_exact_hash_only(self):
        # grab a real phone hash from the seed world, then search scoped to phone
        from app.services.zcql_local import _world
        suspects = _world().get("suspects", [])
        target = next((s for s in suspects if s.get("phone_hash")), None)
        if target is None:
            pytest.skip("seed world has no phone hashes")
        d = (await _get(f"/api/profile/search?q={target['phone_hash']}&field=phone")).json()
        assert d["count"] >= 1
        assert d["hits"][0]["suspect_id"] == target["suspect_id"]
        assert d["hits"][0]["match_method"] == "phone_exact"
        # and the same hash scoped to name must NOT match
        d2 = (await _get(f"/api/profile/search?q={target['phone_hash']}&field=name")).json()
        assert all(h["suspect_id"] != target["suspect_id"] or h["match_field"] != "phone_hash"
                   for h in d2["hits"])

    @pytest.mark.anyio
    async def test_unknown_field_falls_back_to_all(self):
        d_all = (await _get("/api/profile/search?q=Raju&threshold=0.55")).json()
        d_bogus = (await _get("/api/profile/search?q=Raju&threshold=0.55&field=bogus")).json()
        assert d_bogus["field"] == "all"
        assert d_bogus["count"] == d_all["count"]
