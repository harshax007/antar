"""
Task #9: Fuzzy/phonetic entity resolution.
Tests cover:
  • jaro() — similarity contract
  • jaro_winkler() — prefix bonus + clamp to [0,1]
  • soundex() — phonetic grouping of Indian name variants
  • fuzzy_match_suspects() — multi-signal search over seed world
  • GET /api/profile/search — endpoint contract + WOW-2 demo
  • Regression: /registry and /{suspect_id} still work
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.services.entity_resolver import jaro, jaro_winkler, soundex, fuzzy_match_suspects
from app.services.zcql_local import _world


# ── jaro() ───────────────────────────────────────────────────────────────────

class TestJaro:
    def test_identical_strings(self):
        assert jaro("RAJU", "RAJU") == 1.0

    def test_empty_string(self):
        assert jaro("", "RAJU") == 0.0
        assert jaro("RAJU", "") == 0.0

    def test_both_empty(self):
        assert jaro("", "") == 1.0

    def test_completely_different(self):
        assert jaro("RAJU", "ZZZZ") < 0.5

    def test_close_names(self):
        # Yellappa / Yellapa — one character difference
        assert jaro("YELLAPPA", "YELLAPA") > 0.90

    def test_symmetry(self):
        assert abs(jaro("RAJU", "RAJOO") - jaro("RAJOO", "RAJU")) < 1e-9

    def test_result_in_range(self):
        for a, b in [("KRISHNAPPA", "KRISHNA"), ("RAVI", "RAJI"), ("A", "B")]:
            assert 0.0 <= jaro(a, b) <= 1.0


# ── jaro_winkler() ───────────────────────────────────────────────────────────

class TestJaroWinkler:
    def test_identical(self):
        assert jaro_winkler("YELLAPPA", "YELLAPPA") == 1.0

    def test_prefix_bonus_raises_above_jaro(self):
        # Shared prefix should push JW above raw Jaro
        j  = jaro("YELLAPPA", "YELLAPA")
        jw = jaro_winkler("YELLAPPA", "YELLAPA")
        assert jw >= j

    def test_yellappa_yellapa_above_threshold(self):
        assert jaro_winkler("YELLAPPA", "YELLAPA") >= 0.93

    def test_raju_rajoo_above_threshold(self):
        # Measured: 0.848 — above default threshold 0.82 but fractionally below 0.85
        assert jaro_winkler("RAJU", "RAJOO") >= 0.84

    def test_different_names_below_threshold(self):
        # Names with no phonetic or spelling relation
        assert jaro_winkler("RAJU", "SHARMA") < 0.70

    def test_clamped_to_one(self):
        # With p=0.5 (huge prefix weight) should not exceed 1.0
        assert jaro_winkler("AABB", "AABB", p=0.5) <= 1.0

    def test_result_in_range(self):
        for a, b in [("MAHESH", "MAHES"), ("X", "Y"), ("KRISHNAPPA", "KRISHNAPAA")]:
            assert 0.0 <= jaro_winkler(a, b) <= 1.0

    def test_symmetry(self):
        assert abs(
            jaro_winkler("YELLAPPA", "YELLAPA") - jaro_winkler("YELLAPA", "YELLAPPA")
        ) < 1e-9


# ── soundex() ────────────────────────────────────────────────────────────────

class TestSoundex:
    def test_yellappa_yellapa_same(self):
        """WOW-2 alias variant: Yellappa and Yellapa must share a Soundex code."""
        assert soundex("Yellappa") == soundex("Yellapa")

    def test_raju_raaju_same(self):
        """Doubled-vowel variant: Raju / Raaju → same code."""
        assert soundex("Raju") == soundex("Raaju")

    def test_krishnappa_krishna_same(self):
        assert soundex("Krishnappa") == soundex("Krishna")

    def test_empty_name(self):
        assert soundex("") == "Z000"

    def test_four_char_output(self):
        for name in ["A", "Raju", "Yellappa", "Mahadeva", "Krishnappa"]:
            assert len(soundex(name)) == 4

    def test_first_letter_preserved(self):
        assert soundex("Raju")[0] == "R"
        assert soundex("Yellappa")[0] == "Y"
        assert soundex("Mahesh")[0] == "M"

    def test_different_names_different_code(self):
        # Raju and Sharma are phonetically dissimilar
        assert soundex("Raju") != soundex("Sharma")

    def test_numeric_only_returns_z000(self):
        assert soundex("123") == "Z000"


# ── fuzzy_match_suspects() ───────────────────────────────────────────────────

class TestFuzzyMatchSuspects:
    def setup_method(self):
        self.world = _world()

    def test_exact_match_returns_suspect(self):
        """Exact substring 'Yellappa' matches both alias=Yellappa and full_name=Yellappa M."""
        hits = fuzzy_match_suspects("Yellappa", self.world)
        ids = [h["suspect_id"] for h in hits]
        assert "S0001" in ids or "S0002" in ids

    def test_typo_yellapa_finds_yellappa(self):
        """WOW-2: one-p typo 'Yellapa' must find the Yellappa suspects via Jaro-Winkler."""
        hits = fuzzy_match_suspects("Yellapa", self.world)
        ids = [h["suspect_id"] for h in hits]
        assert "S0001" in ids or "S0002" in ids, \
            f"Neither S0001 nor S0002 found; got {ids}"

    def test_soundex_raju_raaju(self):
        """Doubled-vowel typo 'Raaju' must find Raju K. (S0001) via Soundex/JW."""
        hits = fuzzy_match_suspects("Raaju", self.world)
        ids = [h["suspect_id"] for h in hits]
        assert "S0001" in ids, f"S0001 not found; got {ids}"

    def test_father_name_search(self):
        """Searching by father_name token 'Krishnappa' finds S0001."""
        hits = fuzzy_match_suspects("Krishnappa", self.world)
        ids = [h["suspect_id"] for h in hits]
        assert "S0001" in ids, f"S0001 not found via father_name; got {ids}"

    def test_sorted_by_score_desc(self):
        hits = fuzzy_match_suspects("Yellappa", self.world)
        scores = [h["match_score"] for h in hits]
        assert scores == sorted(scores, reverse=True)

    def test_all_hits_have_required_fields(self):
        hits = fuzzy_match_suspects("Raju", self.world)
        required = {"suspect_id", "full_name", "alias", "match_score",
                    "match_field", "match_method"}
        for h in hits:
            missing = required - set(h.keys())
            assert not missing, f"hit missing fields: {missing}"

    def test_match_score_in_range(self):
        for h in fuzzy_match_suspects("Yellappa", self.world):
            assert 0.0 <= h["match_score"] <= 1.0

    def test_empty_query_returns_empty(self):
        assert fuzzy_match_suspects("", self.world) == []
        assert fuzzy_match_suspects("   ", self.world) == []

    def test_limit_respected(self):
        hits = fuzzy_match_suspects("a", self.world, threshold=0.0, limit=3)
        assert len(hits) <= 3

    def test_high_threshold_filters_jw_but_soundex_can_still_fire(self):
        """threshold=0.99 blocks JW-only hits but Soundex still surfaces phonetic matches
        (it has its own _SOUNDEX_MIN_JW=0.65 floor, independent of threshold).
        Verify: a clearly unrelated query at 0.99 returns nothing."""
        hits = fuzzy_match_suspects("XQZWVVVVVVV", self.world, threshold=0.99)
        assert hits == [], f"Nonsense query should return empty at high threshold; got {hits}"

    def test_no_duplicate_suspect_ids(self):
        hits = fuzzy_match_suspects("Raju", self.world)
        ids = [h["suspect_id"] for h in hits]
        assert len(ids) == len(set(ids)), "duplicate suspect_ids in results"

    def test_match_method_values(self):
        hits = fuzzy_match_suspects("Yellappa", self.world)
        valid_methods = {"exact", "jaro_winkler", "soundex", "phone_exact"}
        for h in hits:
            assert h["match_method"] in valid_methods

    def test_wow2_s0001_alias_yellappa(self):
        """WOW-2 demo: querying the alias variant must surface S0001 (Raju K. / Yellappa)."""
        hits = fuzzy_match_suspects("Yellapa", self.world, threshold=0.82)
        s0001 = next((h for h in hits if h["suspect_id"] == "S0001"), None)
        assert s0001 is not None, "S0001 (Yellappa alias) not found for query 'Yellapa'"
        assert s0001["match_score"] >= 0.82

    def test_wow2_s0002_full_name_yellappa(self):
        """WOW-2 demo: querying 'Yellapa' must also surface S0002 (Yellappa M.)."""
        hits = fuzzy_match_suspects("Yellapa", self.world, threshold=0.82)
        s0002 = next((h for h in hits if h["suspect_id"] == "S0002"), None)
        assert s0002 is not None, "S0002 (Yellappa M.) not found for query 'Yellapa'"


# ── GET /api/profile/search ───────────────────────────────────────────────────

class TestSearchEndpoint:
    @pytest.mark.anyio
    async def test_200_ok(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            resp = await c.get("/api/profile/search", params={"q": "Yellappa"})
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_top_level_keys(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/profile/search",
                                params={"q": "Yellappa"})).json()
        for key in ("query", "hits", "count"):
            assert key in data

    @pytest.mark.anyio
    async def test_count_matches_hits_length(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/profile/search",
                                params={"q": "Raju"})).json()
        assert data["count"] == len(data["hits"])

    @pytest.mark.anyio
    async def test_query_echoed(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/profile/search",
                                params={"q": "Yellapa"})).json()
        assert data["query"] == "Yellapa"

    @pytest.mark.anyio
    async def test_hits_sorted_by_score_desc(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/profile/search",
                                params={"q": "Yellappa"})).json()
        scores = [h["match_score"] for h in data["hits"]]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.anyio
    async def test_missing_q_returns_422(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            resp = await c.get("/api/profile/search")
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_limit_param(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/profile/search",
                                params={"q": "a", "limit": 2, "threshold": 0.0})).json()
        assert len(data["hits"]) <= 2

    @pytest.mark.anyio
    async def test_wow2_yellapa_typo_via_endpoint(self):
        """WOW-2: querying 'Yellapa' (one-p typo) must find the Yellappa suspects."""
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/profile/search",
                                params={"q": "Yellapa"})).json()
        ids = [h["suspect_id"] for h in data["hits"]]
        assert "S0001" in ids or "S0002" in ids, \
            f"WOW-2: Yellappa suspects not found; got {ids}"

    @pytest.mark.anyio
    async def test_hit_fields_present(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/profile/search",
                                params={"q": "Yellappa"})).json()
        required = {"suspect_id", "full_name", "alias", "match_score",
                    "match_field", "match_method"}
        for h in data["hits"]:
            assert required <= set(h.keys())

    @pytest.mark.anyio
    async def test_no_results_returns_empty_hits(self):
        """A clearly nonsense query at default threshold should return empty, not 500."""
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/profile/search",
                                params={"q": "XQZWVVVVVVV"})).json()
        assert data["count"] == 0
        assert data["hits"] == []


# ── Regression: existing profile endpoints ────────────────────────────────────

class TestProfileRegression:
    @pytest.mark.anyio
    async def test_registry_still_works(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            resp = await c.get("/api/profile/registry")
        assert resp.status_code == 200
        assert resp.json()["count"] > 0

    @pytest.mark.anyio
    async def test_suspect_profile_still_works(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            resp = await c.get("/api/profile/S0001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["suspect_id"] == "S0001"
        assert "risk_score" in data

    @pytest.mark.anyio
    async def test_search_not_captured_as_suspect_id(self):
        """FastAPI must NOT route /search to the /{suspect_id} handler."""
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            resp = await c.get("/api/profile/search", params={"q": "Raju"})
        # If routing is wrong this returns a 404 for suspect "search"; must be 200
        assert resp.status_code == 200
        assert "hits" in resp.json()


# ── Bipartite Graph Embeddings & Linkage (Recommendation C) ───────────────────
class TestBipartiteGraphLinkage:
    def test_bipartite_linkage_score_shared_edges(self):
        from app.services.entity_resolver import bipartite_linkage_score
        a = {"suspect_name": "Raju K", "zone": "Rajajinagar", "crime_type": "chain_snatching", "phone_hash": "H123"}
        b = {"suspect_name": "Raaju K", "zone": "Rajajinagar", "crime_type": "chain_snatching", "phone_hash": "H123"}
        score, reasons, meta = bipartite_linkage_score(a, b)
        assert score > 0.85
        assert meta["bipartite_cosine_sim"] == 1.0
        assert any("Bipartite" in r or "Shared bipartite" in r for r in reasons)

    def test_suggest_identity_links_returns_bipartite_meta(self):
        from app.services.entity_resolver import suggest_identity_links
        rows = [
            {"id": "U1", "suspect_name": "Kumar", "zone": "Central", "phone_hash": "P1"},
            {"id": "U2", "suspect_name": "Kumaar", "zone": "Central", "phone_hash": "P1"},
        ]
        hyps = suggest_identity_links(rows, threshold=0.60)
        assert len(hyps) >= 1
        assert "bipartite_meta" in hyps[0]
        assert hyps[0]["bipartite_meta"]["bipartite_cosine_sim"] > 0.0


def test_identity_links_are_kept_with_the_world_they_were_computed_from():
    """Scored once per world, not on every search; a new world is scored afresh."""
    from app.services import entity_resolver as er
    w1 = {"suspects": [{"suspect_id": "A", "full_name": "Ravi Kumar", "phone_hash": "p1"},
                       {"suspect_id": "B", "full_name": "Ravi Kumaar", "phone_hash": "p1"}]}
    first = er.suggest_identity_links(w1, threshold=0.75)
    calls = []
    real = er._suggest_identity_links
    er._suggest_identity_links = lambda *a, **k: calls.append(1) or real(*a, **k)
    try:
        assert er.suggest_identity_links(w1, threshold=0.75) == first and not calls     # kept
        w2 = {"suspects": [dict(s) for s in w1["suspects"]]}
        er.suggest_identity_links(w2, threshold=0.75)
        assert calls == [1]                                                                   # new world
        er.suggest_identity_links(w2, threshold=0.9)
        assert calls == [1, 1]                                                                # new threshold
    finally:
        er._suggest_identity_links = real
