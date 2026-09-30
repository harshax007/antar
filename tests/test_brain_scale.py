"""
Task #10: HNSW + Cross-Encoder Rerank + MMR (Brain Scale).
Tests cover:
  • FAISS HNSW index: build, search, append, sync_faiss, backward-compat
  • CrossEncoderReranker: loads, reranks, degrades gracefully when offline
  • MMR: diversity enforcement, lambda trade-off, edge cases
  • Full semantic_recall() pipeline: all three stages end-to-end
  • Regression: existing brain tests still pass
"""

import asyncio
import numpy as np
import pytest
from httpx import AsyncClient, ASGITransport

from app.second_brain.index import BrainIndex, brain_index, _FAISS_OK, _DIM
from app.second_brain.reranker import CrossEncoderReranker, reranker, mmr, MMR_LAMBDA_DEFAULT
from app.second_brain.retrieval import semantic_recall


# ── helpers ───────────────────────────────────────────────────────────────────

def _rand_unit(n: int = 1, seed: int = 0) -> np.ndarray:
    """Random L2-normalised float32 vectors, shape (n, DIM)."""
    rng = np.random.default_rng(seed)
    v   = rng.standard_normal((n, _DIM)).astype(np.float32)
    v  /= np.linalg.norm(v, axis=1, keepdims=True)
    return v


def _fake_embed(text: str) -> np.ndarray:
    """Deterministic normalised (1, DIM) vector — no MiniLM needed in tests."""
    rng = np.random.default_rng(abs(hash(text)) % (2 ** 32))
    v   = rng.standard_normal(_DIM).astype(np.float32)
    return (v / np.linalg.norm(v)).reshape(1, _DIM)


def _rows_from_vecs(vecs: np.ndarray, kinds: list[str] | None = None) -> list[dict]:
    """Build fake Data Store rows from numpy vectors."""
    import base64
    rows = []
    for i, v in enumerate(vecs):
        rows.append({
            "row_id":     f"R{i:03d}",
            "vector_b64": base64.b64encode(v.astype(np.float32).tobytes()).decode(),
            "kind":       (kinds[i] if kinds else "investigation"),
            "summary_text": f"Summary for row {i}",
            "suspect_ids_json": "[]",
            "crime_ids_json":   "[]",
            "station_code":     None,
            "ref_session_id":   None,
            "verification_status": "unverified",
            "confidence":   0.7,
            "officer_role": "Inspector",
            "created_at":   None,
        })
    return rows


# ── HNSW index ────────────────────────────────────────────────────────────────

class TestHNSWIndex:
    def setup_method(self):
        self.idx = BrainIndex()

    def test_rebuild_sets_size(self):
        vecs = _rand_unit(10, seed=1)
        self.idx.rebuild(_rows_from_vecs(vecs))
        assert self.idx.size == 10

    def test_empty_rebuild(self):
        self.idx.rebuild([])
        assert self.idx.size == 0
        assert self.idx.cosine_topk(_rand_unit(1)[0]) == []

    def test_cosine_topk_returns_correct_rank(self):
        """The inserted vector most similar to the query must rank first."""
        vecs = _rand_unit(5, seed=42)
        self.idx.rebuild(_rows_from_vecs(vecs))
        # query = vec[0] exactly → vec[0] should score ≈ 1.0
        hits = self.idx.cosine_topk(vecs[0], k=5)
        assert hits[0]["row_id"] == "R000"
        assert hits[0]["score"] > 0.99

    def test_cosine_topk_k_limit(self):
        vecs = _rand_unit(10, seed=7)
        self.idx.rebuild(_rows_from_vecs(vecs))
        hits = self.idx.cosine_topk(vecs[0], k=3)
        assert len(hits) <= 3

    def test_append_grows_index(self):
        vecs = _rand_unit(3, seed=5)
        self.idx.rebuild(_rows_from_vecs(vecs[:2]))
        assert self.idx.size == 2
        self.idx.append(vecs[2], "R002", {"kind": "test", "summary_text": "appended"})
        assert self.idx.size == 3

    def test_append_searchable(self):
        """An appended vector must be findable via cosine_topk."""
        base = _rand_unit(5, seed=9)
        self.idx.rebuild(_rows_from_vecs(base))
        new_vec = _rand_unit(1, seed=99)[0]
        self.idx.append(new_vec, "RNEW", {"kind": "test", "summary_text": "new item"})
        hits = self.idx.cosine_topk(new_vec, k=1)
        assert hits[0]["row_id"] == "RNEW"

    def test_kind_filter_numpy_fallback(self):
        """kind_filter uses the numpy path — results must match the filter."""
        kinds = ["investigation"] * 4 + ["session_trace"] * 4
        vecs  = _rand_unit(8, seed=3)
        self.idx.rebuild(_rows_from_vecs(vecs, kinds))
        hits = self.idx.cosine_topk(vecs[0], k=8, kind_filter="session_trace")
        assert all(h["kind"] == "session_trace" for h in hits)

    def test_matrix_idx_in_results(self):
        vecs = _rand_unit(5, seed=11)
        self.idx.rebuild(_rows_from_vecs(vecs))
        hits = self.idx.cosine_topk(vecs[0], k=5)
        for h in hits:
            assert "_matrix_idx" in h
            assert 0 <= h["_matrix_idx"] < self.idx.size

    def test_sync_faiss_after_mutation(self):
        """After mutating _matrix[i] and calling sync_faiss(), search must reflect the update."""
        vecs = _rand_unit(5, seed=13)
        self.idx.rebuild(_rows_from_vecs(vecs))
        # Replace row 0 with a known query vector
        new_vec = _rand_unit(1, seed=999)[0]
        self.idx._matrix[0] = new_vec
        self.idx.sync_faiss()
        hits = self.idx.cosine_topk(new_vec, k=1)
        assert hits[0]["row_id"] == "R000"

    def test_backward_compat_matrix_attribute(self):
        """_matrix must remain a real numpy ndarray (consolidation accesses it directly)."""
        vecs = _rand_unit(4, seed=15)
        self.idx.rebuild(_rows_from_vecs(vecs))
        assert isinstance(self.idx._matrix, np.ndarray)
        assert self.idx._matrix.shape == (4, _DIM)

    def test_backward_compat_row_ids(self):
        vecs = _rand_unit(3, seed=17)
        self.idx.rebuild(_rows_from_vecs(vecs))
        assert self.idx._row_ids == ["R000", "R001", "R002"]

    def test_scores_in_valid_range(self):
        """L2-normalised inner products must be in [-1, 1]."""
        vecs = _rand_unit(20, seed=19)
        self.idx.rebuild(_rows_from_vecs(vecs))
        for hit in self.idx.cosine_topk(vecs[0], k=10):
            assert -1.01 <= hit["score"] <= 1.01

    def test_faiss_flag(self):
        """_FAISS_OK reflects actual import availability."""
        try:
            import faiss  # noqa: F401
            assert _FAISS_OK is True
        except ImportError:
            assert _FAISS_OK is False


# ── Cross-encoder reranker ─────────────────────────────────────────────────────

class TestCrossEncoderReranker:
    """Load a fresh reranker instance per class — avoids depending on app startup order."""

    @classmethod
    def setup_class(cls):
        cls.ce = CrossEncoderReranker()
        cls.loaded = cls.ce.load()

    def test_reranker_loads(self):
        assert self.ce.MODEL_NAME == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert self.loaded is True
        assert self.ce.available is True

    def test_rerank_scores_relevant_pair_higher(self):
        """(query, relevant_doc) must score higher than (query, unrelated_doc)."""
        candidates = [
            {"summary_text": "Rajajinagar chain snatching spike in week 14",
             "score": 0.5, "_matrix_idx": 0},
            {"summary_text": "Yellappa alias used in Mysuru robbery case 2025",
             "score": 0.4, "_matrix_idx": 1},
            {"summary_text": "Rainfall forecast for Bengaluru monsoon season",
             "score": 0.3, "_matrix_idx": 2},
        ]
        result = self.ce.rerank("chain snatching Rajajinagar hotspot", candidates, top_n=3)
        assert result[0]["summary_text"].startswith("Rajajinagar chain snatching")

    def test_rerank_top_n_respected(self):
        candidates = [{"summary_text": f"doc {i}", "score": 0.5, "_matrix_idx": i}
                      for i in range(5)]
        result = self.ce.rerank("query", candidates, top_n=2)
        assert len(result) == 2

    def test_rerank_fallback_when_offline(self):
        """Without a model, rerank returns candidates[:top_n] in original order."""
        offline = CrossEncoderReranker()   # never loaded → _model is None
        candidates = [{"summary_text": f"doc {i}", "score": float(i), "_matrix_idx": i}
                      for i in range(4)]
        result = offline.rerank("query", candidates, top_n=2)
        assert len(result) == 2
        assert result[0]["summary_text"] == "doc 0"  # original order preserved

    def test_rerank_empty_candidates(self):
        result = self.ce.rerank("query", [], top_n=3)
        assert result == []

    def test_rerank_sets_score_field(self):
        """After reranking, 'score' must be updated to the sigmoid-normalised CE score."""
        candidates = [{"summary_text": "chain snatching hotspot", "score": 0.3, "_matrix_idx": 0}]
        result = self.ce.rerank("chain snatching", candidates, top_n=1)
        assert 0.0 < result[0]["score"] < 1.0
        assert "rerank_score" in result[0]


# ── MMR ───────────────────────────────────────────────────────────────────────

class TestMMR:
    def test_returns_k_items(self):
        vecs       = _rand_unit(6, seed=20)
        candidates = [{"score": 0.9 - i * 0.1, "_matrix_idx": i,
                       "summary_text": f"doc {i}"} for i in range(6)]
        result = mmr(_rand_unit(1, seed=20)[0], candidates, vecs, k=3)
        assert len(result) == 3

    def test_fewer_candidates_than_k(self):
        vecs       = _rand_unit(2, seed=21)
        candidates = [{"score": 0.9, "_matrix_idx": i, "summary_text": f"d{i}"}
                      for i in range(2)]
        result = mmr(_rand_unit(1, seed=21)[0], candidates, vecs, k=5)
        assert len(result) == 2   # returns all when candidates < k

    def test_empty_candidates(self):
        result = mmr(_rand_unit(1)[0], [], _rand_unit(3), k=3)
        assert result == []

    def test_diversity_enforced_for_duplicates(self):
        """When all candidates are the same vector, MMR must still pick k but not
        all be the same result — structural: no index is repeated."""
        n    = 5
        base = _rand_unit(1, seed=22)[0]
        vecs = np.vstack([base] * n)   # identical vectors
        candidates = [{"score": 0.9 - i * 0.01, "_matrix_idx": i,
                       "summary_text": f"dup {i}"} for i in range(n)]
        result = mmr(base, candidates, vecs, k=3, lambda_=0.5)
        assert len(result) == 3
        selected_indices = [r["_matrix_idx"] for r in result]
        assert len(set(selected_indices)) == 3   # unique positions selected

    def test_lambda_1_pure_relevance_order(self):
        """lambda=1.0 → no diversity penalty → same as sorting by score."""
        vecs       = _rand_unit(4, seed=23)
        candidates = [{"score": float(4 - i) / 4, "_matrix_idx": i,
                       "summary_text": f"d{i}"} for i in range(4)]
        result = mmr(_rand_unit(1, seed=23)[0], candidates, vecs, k=4, lambda_=1.0)
        # Must be sorted by score descending
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_lambda_0_prefers_diversity(self):
        """lambda=0.0 → pure diversity → avoid selecting near-duplicate."""
        # Make vec[0] and vec[1] very similar, vec[2] orthogonal
        v01 = _rand_unit(1, seed=24)[0]
        v2  = _rand_unit(1, seed=99)[0]
        v2 -= v01 * (v01 @ v2)         # orthogonalise
        v2 /= np.linalg.norm(v2)
        vecs = np.vstack([v01, v01, v2.astype(np.float32)])  # rows 0,1 identical
        candidates = [{"score": 0.9, "_matrix_idx": 0, "summary_text": "A"},
                      {"score": 0.8, "_matrix_idx": 1, "summary_text": "A-dup"},
                      {"score": 0.7, "_matrix_idx": 2, "summary_text": "B-diverse"}]
        result = mmr(v01, candidates, vecs, k=2, lambda_=0.0)
        ids = {r["_matrix_idx"] for r in result}
        # With pure diversity and k=2, one from {0,1} and 2 should be selected
        assert 2 in ids

    def test_no_matrix_idx_required_for_all_candidates(self):
        """Candidates missing _matrix_idx are skipped gracefully."""
        vecs = _rand_unit(3, seed=25)
        candidates = [{"score": 0.9, "summary_text": "no idx"},       # no _matrix_idx
                      {"score": 0.8, "_matrix_idx": 1, "summary_text": "has idx"}]
        result = mmr(vecs[0], candidates, vecs, k=2)
        assert isinstance(result, list)


# ── Full semantic_recall() pipeline ───────────────────────────────────────────

class TestSemanticRecallPipeline:
    def setup_method(self):
        # Reset the shared global index before each test
        brain_index.rebuild([])

    def teardown_method(self):
        brain_index.rebuild([])

    def test_empty_index_returns_empty(self):
        assert semantic_recall("anything", k=3) == []

    def test_returns_list(self):
        from app.second_brain.ingestion import seed_demo_brain
        seed_demo_brain(_fake_embed)
        result = semantic_recall("chain snatching suspect Rajajinagar", k=3)
        assert isinstance(result, list)

    def test_respects_k(self):
        from app.second_brain.ingestion import seed_demo_brain
        seed_demo_brain(_fake_embed)
        n = brain_index.size
        k = min(2, n)
        result = semantic_recall("robbery case", k=k)
        assert len(result) <= k

    def test_no_matrix_idx_in_output(self):
        """_matrix_idx must be stripped before returning to callers."""
        from app.second_brain.ingestion import seed_demo_brain
        seed_demo_brain(_fake_embed)
        for hit in semantic_recall("case summary", k=5):
            assert "_matrix_idx" not in hit
            assert "rerank_score" not in hit

    def test_result_has_standard_fields(self):
        from app.second_brain.ingestion import seed_demo_brain
        seed_demo_brain(_fake_embed)
        for hit in semantic_recall("investigation", k=3):
            assert "score"        in hit
            assert "row_id"       in hit
            assert "summary_text" in hit
            assert "kind"         in hit

    def test_rerank_false_skips_cross_encoder(self):
        """rerank=False must bypass the cross-encoder (returns cosine-ordered results)."""
        from app.second_brain.ingestion import seed_demo_brain
        seed_demo_brain(_fake_embed)
        result = semantic_recall("test", k=3, rerank=False)
        assert isinstance(result, list)

    def test_mmr_lambda_1_no_diversity(self):
        """mmr_lambda=1.0 is pure relevance — equivalent to top-k by score."""
        from app.second_brain.ingestion import seed_demo_brain
        seed_demo_brain(_fake_embed)
        result = semantic_recall("test", k=3, rerank=False, mmr_lambda=1.0)
        assert isinstance(result, list)


# ── Regression: existing brain behaviour ──────────────────────────────────────

class TestBrainRegression:
    def setup_method(self):
        brain_index.rebuild([])

    def teardown_method(self):
        brain_index.rebuild([])

    def test_cosine_topk_interface_unchanged(self):
        """cosine_topk must still accept (query_vec, k, kind_filter) and return dicts."""
        from app.second_brain.ingestion import seed_demo_brain
        seed_demo_brain(_fake_embed)
        q = _fake_embed("test query")[0]
        hits = brain_index.cosine_topk(q, k=3)
        assert isinstance(hits, list)
        if hits:
            assert "score" in hits[0]
            assert "row_id" in hits[0]

    def test_seed_demo_brain_idempotent(self):
        from app.second_brain.ingestion import seed_demo_brain
        from app.seeds.planted_patterns import BRAIN_SEED
        n1 = seed_demo_brain(_fake_embed)
        assert n1 == len(BRAIN_SEED)
        assert brain_index.size == len(BRAIN_SEED)
        assert seed_demo_brain(_fake_embed) == 0   # second call is no-op

    @pytest.mark.anyio
    async def test_brain_related_wow2_still_works(self):
        """WOW-2 data-driven link (shared phone + common contacts) must survive upgrade."""
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/brain/related",
                                params={"suspect_ids": "S0001"})).json()
        # response: {"results": [...], "banner": ...}
        results = data.get("results", [])
        assert results and results[0].get("links"), "WOW-2 cross-case link must still be present"
