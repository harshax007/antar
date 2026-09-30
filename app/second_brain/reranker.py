"""
Antar — Cross-Encoder Reranker + MMR Diversifier (Task #10)
================================================================
Two-stage refinement on top of HNSW ANN recall:

  Stage 2 — Cross-encoder rerank
    Jointly encodes (query, document) pairs for much higher relevance
    precision than bi-encoder cosine. Uses ms-marco-MiniLM-L-6-v2
    (Nogueira & Cho 2019 BERT MS-MARCO fine-tune; 22 MB).
    Raw logits → sigmoid → [0,1] for use as MMR relevance signal.

  Stage 3 — Maximal Marginal Relevance (MMR)
    Carbonell & Goldstein (1998): greedy selection that balances
    relevance to the query vs redundancy with already-chosen docs.
    Prevents surfacing five variants of the same case.
    λ=0.7 → 70 % relevance / 30 % diversity (tunable per call).

Both stages degrade gracefully: if the cross-encoder is unavailable
(no network, offline Catalyst deploy) the pipeline falls back to
HNSW cosine scores; if candidates ≤ k MMR is a no-op.
"""

from __future__ import annotations

import numpy as np

_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
MMR_LAMBDA_DEFAULT   = 0.7   # 70 % relevance, 30 % diversity


# ── Cross-encoder ─────────────────────────────────────────────────────────────

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500.0, 500.0)))


class CrossEncoderReranker:
    """Lazy-loaded ms-marco cross-encoder for two-stage Brain retrieval.

    Call `.load()` once at startup (non-fatal if offline). Then call
    `.rerank(query, candidates, top_n)` to re-score and trim candidates.
    """

    MODEL_NAME = _CROSS_ENCODER_MODEL

    def __init__(self) -> None:
        self._model = None
        self.backend = "none"

    def load(self) -> bool:
        """Load the cross-encoder. Returns True on success.

        Prefers the ONNX export (same weights, no torch — final_backend.md §4 step 6) and
        falls back to sentence-transformers, so a missing export costs memory, not
        reranking. ANTAR_BRAIN_BACKEND=torch skips ONNX; =onnx warns when it is absent.
        """
        import os

        mode = (os.getenv("ANTAR_BRAIN_BACKEND") or "auto").lower()
        if mode != "torch":
            try:
                from app.second_brain.onnx_backend import OnnxCrossEncoder, artifacts_for
                directory = artifacts_for(self.MODEL_NAME)
                if directory is not None:
                    self._model = OnnxCrossEncoder(directory)
                    self.backend = f"onnx/{self._model.variant}"
                    return True
                if mode == "onnx":
                    print(f"  ⚠️  ANTAR_BRAIN_BACKEND=onnx but no export for "
                          f"{self.MODEL_NAME} — falling back to torch")
            except Exception as e:
                print(f"  ⚠️  ONNX reranker unavailable ({e}) — falling back to torch")
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.MODEL_NAME, max_length=512)
            self.backend = "torch"
            return True
        except Exception as e:
            print(f"  ⚠️  CrossEncoder load failed (Brain reranking degraded): {e}")
            return False

    @property
    def available(self) -> bool:
        return self._model is not None

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_n: int,
    ) -> list[dict]:
        """Score (query, summary_text) pairs; sort descending; return top_n.

        Side-effect: sets `rerank_score` and updates `score` on each candidate
        (sigmoid-normalised to [0,1]) so the downstream MMR step gets a
        calibrated relevance signal instead of raw cosine.

        Falls back to `candidates[:top_n]` in original cosine order when the
        model is unavailable.
        """
        if not self._model or not candidates:
            return candidates[:top_n]

        pairs  = [(query, c.get("summary_text", "")) for c in candidates]
        raw    = self._model.predict(pairs)
        normed = _sigmoid(np.array(raw, dtype=np.float32))

        for i, c in enumerate(candidates):
            c["rerank_score"] = float(normed[i])
            c["score"]        = float(normed[i])   # MMR uses this as relevance

        ranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
        return ranked[:top_n]


# Module-level singleton — imported by retrieval.py and startup
reranker = CrossEncoderReranker()


# ── MMR ───────────────────────────────────────────────────────────────────────

def mmr(
    query_vec:    np.ndarray,
    candidates:   list[dict],
    brain_matrix: np.ndarray,
    k:            int,
    lambda_:      float = MMR_LAMBDA_DEFAULT,
) -> list[dict]:
    """Maximal Marginal Relevance — Carbonell & Goldstein (1998).

    Greedily selects k items maximising:
      MMR(d) = λ · relevance(d, query) − (1−λ) · max_{s∈S} cos(d, s)

    where S is the already-selected set.  Since all vectors are L2-normalised,
    cosine = dot product → fast matrix multiply with no extra normalisation.

    Args:
        query_vec:    (384,) query embedding (L2-normalised, unused in the
                      greedy loop but passed for API symmetry / future use).
        candidates:   hit dicts from cosine_topk / rerank; each must carry
                      '_matrix_idx' (row in brain_matrix) and 'score'
                      (relevance signal — cosine or sigmoid(rerank)).
        brain_matrix: full (n, 384) float32 matrix from brain_index._matrix.
        k:            desired result count.
        lambda_:      trade-off weight (1.0 = pure relevance, 0.0 = pure diversity).

    Returns list of up to k candidate dicts in MMR-selected order.
    """
    if not candidates:
        return []
    if len(candidates) <= k:
        return candidates

    # Build a (m, 384) matrix of candidate vectors and their relevance scores
    valid = [
        c for c in candidates
        if "_matrix_idx" in c and isinstance(c["_matrix_idx"], int) and 0 <= c["_matrix_idx"] < brain_matrix.shape[0]
    ]
    if not valid:
        return candidates[:k]

    idxs      = [c["_matrix_idx"] for c in valid]
    cand_vecs = brain_matrix[idxs].astype(np.float32)        # (m, 384)
    rel       = np.array([c.get("score", 0.0) for c in valid], dtype=np.float32)

    selected_pos: list[int]       = []
    selected_vecs: list[np.ndarray] = []
    remaining = list(range(len(valid)))

    while len(selected_pos) < k and remaining:
        mmr_vals: list[float] = []
        for i in remaining:
            relevance = float(rel[i])
            if selected_vecs:
                sel_mat    = np.vstack(selected_vecs)           # (s, 384)
                redundancy = float((sel_mat @ cand_vecs[i]).max())
            else:
                redundancy = 0.0
            mmr_vals.append(lambda_ * relevance - (1.0 - lambda_) * redundancy)

        best = remaining[int(np.argmax(mmr_vals))]
        selected_pos.append(best)
        selected_vecs.append(cand_vecs[best].reshape(1, -1))
        remaining.remove(best)

    return [valid[i] for i in selected_pos]
