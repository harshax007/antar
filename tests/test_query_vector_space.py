"""
Query vectors must live in INDEX space (768), on every path.

Regression for a live crash: `semantic_recall(..., terms=[...])` (used by forecast_agent)
built its vector with `embed_with_terms()` — a 384-dim DOCUMENT embedder — so
`_numpy_search` raised
    matmul: Input operand 1 has a mismatch in its core dimension 0 ... (384 vs 768)
which semantic_recall swallowed, leaving recall silently empty.
"""

import numpy as np
import pytest

from app.second_brain.embedder import load_embedder, embed_query, embed_query_with_terms
from app.second_brain.index import BrainIndex, _DIM


@pytest.fixture(scope="module", autouse=True)
def _model():
    load_embedder()


class TestQuerySpace:
    def test_both_query_builders_return_index_width(self):
        assert embed_query("theft in Rajajinagar").shape == (_DIM,)
        assert embed_query_with_terms("theft", ["Rajajinagar", "chain_snatching"]).shape == (_DIM,)

    def test_query_vectors_are_l2_normalised(self):
        for v in (embed_query("theft"), embed_query_with_terms("theft", ["Rajajinagar"])):
            assert np.isclose(np.linalg.norm(v), 1.0, atol=1e-5)

    def test_terms_actually_change_the_vector(self):
        plain = embed_query("theft")
        enriched = embed_query_with_terms("theft", ["Rajajinagar", "chain_snatching"])
        assert not np.allclose(plain, enriched), "terms must influence the query vector"


class TestIndexToleratesWrongWidth:
    """cosine_topk coerces to _DIM so a stray text-space vector degrades, never crashes."""

    def _idx(self):
        idx = BrainIndex()
        rng = np.random.default_rng(0)
        for i in range(3):
            v = rng.random(384).astype(np.float32)
            idx.append(v / np.linalg.norm(v), f"r{i}", {"summary_text": f"case {i}", "kind": "fir"})
        return idx

    def test_append_pads_to_index_width(self):
        idx = self._idx()
        assert idx._matrix.shape == (3, _DIM)

    def test_384_query_does_not_raise(self):
        idx = self._idx()
        q = np.ones(384, dtype=np.float32)
        q /= np.linalg.norm(q)
        assert len(idx.cosine_topk(q, k=2)) == 2          # degrades, no ValueError

    def test_768_query_works(self):
        idx = self._idx()
        assert len(idx.cosine_topk(embed_query("case"), k=2)) == 2


class TestSemanticRecallBothPaths:
    """Builds its OWN index state — `seed_demo_brain()` is idempotent, so relying on it
    made this order-dependent (passed alone, failed after other brain tests)."""

    def _build(self):
        import base64
        from app.second_brain.index import brain_index
        from app.second_brain.embedder import embed
        docs = [
            "Chain snatching surge in Rajajinagar, two-wheeler riders, evening hours.",
            "Vehicle theft near Jayanagar market, white pickup seen at the toll.",
            "Cyber fraud UPI mule account traced to an Indiranagar branch.",
        ]
        rows = []
        for i, d in enumerate(docs):
            v = embed(d)
            v = v[0] if getattr(v, "ndim", 1) == 2 else v
            rows.append({
                "row_id": f"qvs-{i}",
                "vector_b64": base64.b64encode(np.asarray(v, dtype=np.float32).tobytes()).decode(),
                "summary_text": d,
                "kind": "fir",
            })
        brain_index.rebuild(rows)
        return brain_index

    def test_recall_with_and_without_terms(self):
        idx = self._build()
        assert idx.size == 3
        from app.second_brain.retrieval import semantic_recall
        assert semantic_recall("chain snatching in Rajajinagar", k=3), "no-terms path returned nothing"
        assert semantic_recall("chain snatching spike", k=3,
                               terms=["Rajajinagar", "chain_snatching"]), "terms path returned nothing"
