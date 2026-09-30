"""
Second Brain hybrid retrieval — BM25 inverted index + Reciprocal Rank Fusion.

Covers:
  • BM25 postings index returns the SAME scores as a reference implementation
    (the inverted index is a speed change only, never a scoring change)
  • BM25 finds exact rare identifiers (ACC-id / vehicle reg) that vectors miss
  • RRF fusion surfaces an exact lexical hit that linear max-normalisation buries
  • hybrid scores stay in [0,1] in BOTH fusion modes — retrieval.py blends
    0.8*score + 0.2*attention_score and assumes that range
  • fusion="linear" still works (rollback path)
"""

import base64
import math

import numpy as np
import pytest

from app.second_brain.index import BrainIndex

DIM = 768


def _vec(seed: int) -> str:
    rng = np.random.default_rng(seed)
    v = rng.random(DIM).astype("float32")
    v /= np.linalg.norm(v) or 1.0
    return base64.b64encode(v.tobytes()).decode()


def _row(i: int, text: str) -> dict:
    return {"row_id": f"r{i}", "vector_b64": _vec(i), "summary_text": text, "kind": "fir"}


def _index(texts: list[str]) -> BrainIndex:
    bi = BrainIndex()
    bi.rebuild([_row(i, t) for i, t in enumerate(texts)])
    return bi


def _reference_bm25(bi: BrainIndex, query_text: str) -> np.ndarray:
    """The pre-inverted-index implementation, kept here as the scoring oracle."""
    q_tokens = bi._tokenize(query_text)
    n = len(bi._doc_tokens)
    k1, b = 1.5, 0.75
    scores = np.zeros(n, dtype=np.float32)
    for t in q_tokens:
        df = bi._doc_freqs.get(t, 0)
        if df == 0:
            continue
        idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
        for idx, d_tokens in enumerate(bi._doc_tokens):
            tf = d_tokens.count(t)
            if tf > 0:
                dl = len(d_tokens)
                scores[idx] += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / bi._avg_dl)))
    return scores


class TestBm25InvertedIndex:
    def test_scores_match_reference_implementation(self):
        texts = [
            "chain snatching near Rajajinagar market accused ACC-1029",
            "vehicle KA01AB1234 seen at toll during burglary",
            "cyber fraud UPI transfer traced to mule account",
            "theft of two wheeler reported in Jayanagar",
            "chain snatching repeat offender Rajajinagar theft",
        ]
        bi = _index(texts)
        q = "chain snatching Rajajinagar theft"
        ref = _reference_bm25(bi, q)
        got = np.zeros(len(texts), dtype=np.float32)
        for r in bi.bm25_search(q, k=len(texts)):
            got[r["_matrix_idx"]] = r["score"]
        assert np.allclose(ref, got, atol=1e-5), f"ref={ref} got={got}"

    def test_repeated_query_term_still_double_counts(self):
        """The postings rewrite must not silently switch to unique-term scoring."""
        bi = _index(["theft theft theft in Jayanagar", "burglary in Hebbal"])
        once = bi.bm25_search("theft", k=2)[0]["score"]
        twice = bi.bm25_search("theft theft", k=2)[0]["score"]
        assert twice == pytest.approx(once * 2, rel=1e-5)

    def test_finds_exact_rare_identifier(self):
        bi = _index([
            "chain snatching near market",
            "vehicle KA01AB1234 seen at toll gate",
            "burglary reported at residence",
        ])
        hits = bi.bm25_search("KA01AB1234", k=3)
        assert hits and hits[0]["_matrix_idx"] == 1

    def test_append_keeps_index_consistent(self):
        bi = _index(["theft in Jayanagar"])
        bi.append(np.zeros(DIM, dtype="float32"), "r-new",
                  {"summary_text": "burglary at Hebbal godown", "kind": "fir"})
        hits = bi.bm25_search("godown", k=5)
        assert hits and hits[0]["row_id"] == "r-new"


class TestFusion:
    def _corpus(self):
        # doc 3 is the only one containing the exact identifier
        return [
            "chain snatching reported near the market area",
            "snatching of chain in a crowded market street",
            "market area chain snatching during evening hours",
            "suspect linked to vehicle KA01AB1234 in an unrelated case",
        ]

    def test_rrf_surfaces_exact_identifier_match(self):
        """A rare-ID query must return the lexical hit, whatever the vectors say."""
        bi = _index(self._corpus())
        qv = np.zeros(DIM, dtype="float32")
        qv[0] = 1.0                      # arbitrary direction, unrelated to doc 3
        out = bi.hybrid_search(qv, "KA01AB1234", k=4, fusion="rrf")
        assert out, "hybrid returned nothing"
        assert out[0]["row_id"] == "r3", [ (o['row_id'], round(o['score'],3)) for o in out ]

    def test_scores_normalised_in_both_modes(self):
        bi = _index(self._corpus())
        qv = np.zeros(DIM, dtype="float32"); qv[0] = 1.0
        for mode in ("rrf", "linear"):
            out = bi.hybrid_search(qv, "chain snatching market", k=4, fusion=mode)
            assert out, mode
            for c in out:
                assert 0.0 <= c["score"] <= 1.0, f"{mode}: score {c['score']} out of range"

    def test_linear_mode_still_available(self):
        bi = _index(self._corpus())
        qv = np.zeros(DIM, dtype="float32"); qv[0] = 1.0
        out = bi.hybrid_search(qv, "chain snatching", k=3, fusion="linear")
        assert out and {"semantic_score", "keyword_score"} <= set(out[0])

    def test_results_are_ordered_descending(self):
        bi = _index(self._corpus())
        qv = np.zeros(DIM, dtype="float32"); qv[0] = 1.0
        out = bi.hybrid_search(qv, "chain snatching market", k=4)
        scores = [c["score"] for c in out]
        assert scores == sorted(scores, reverse=True)
