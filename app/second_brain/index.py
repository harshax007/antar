"""
Antar — Second Brain HNSW + Brute-Force Fallback Index (Task #10)
=======================================================================
Architecture (v5.0 — Brain Scale):

  Primary search path: FAISS IndexHNSWFlat (O(log n) ANN)
    M=32, efConstruction=200, efSearch=64 — standard config for
    recall@10 > 0.99 at 384-dim (Johnson et al. 2017, FAISS paper).
    METRIC_INNER_PRODUCT on L2-normalised vectors ≡ cosine similarity.

  Fallback (kind_filter or FAISS unavailable): NumPy brute-force dot product
    Keeps backward compat with consolidation.py which uses kind_filter and
    mutates _matrix in-place. Call sync_faiss() after in-place mutations.

  Public API is unchanged from v4.0:
    rebuild(rows), append(vec, row_id, meta), cosine_topk(query_vec, k, kind_filter)
    size (property), _matrix, _row_ids, _metadata (all preserved for
    callers that access them directly — ingestion, consolidation, tests).

  New:
    sync_faiss() — rebuild FAISS index from current _matrix (after mutations).
    _matrix_idx field injected into every result dict for MMR vector lookup.
"""

from __future__ import annotations

import base64
import numpy as np
from dataclasses import dataclass, field

# ── FAISS import (graceful degradation if not installed) ──────────────────────
try:
    import faiss as _faiss
    _FAISS_OK = True
except ImportError:
    _faiss  = None            # type: ignore[assignment]
    _FAISS_OK = False

# HNSW hyperparameters — validated against FAISS benchmark suite
_HNSW_M               = 32    # bi-directional links per node (higher = better recall, more RAM)
_HNSW_EF_CONSTRUCTION = 200   # beam width during construction (trade build-time for recall)
_HNSW_EF_SEARCH       = 64    # beam width during search (>= k for recall guarantee)
_DIM                  = 768   # 384 (Text BGE) + 384 (Vision BGE)


@dataclass
class BrainIndex:
    """
    In-memory vector index over Second Brain embeddings.

    Keeps a canonical NumPy matrix (_matrix) as the source of truth for:
      • consolidation.py in-place row mutation
      • MMR pairwise cosine computation
      • backward-compat attribute access in tests

    FAISS HNSW sits alongside as a read-only search cache, rebuilt from
    _matrix on startup and after explicit sync_faiss() calls.
    """

    _matrix:     np.ndarray = field(default_factory=lambda: np.empty((0, _DIM), dtype=np.float32))
    _row_ids:    list[str]  = field(default_factory=list)
    _metadata:   list[dict] = field(default_factory=list)
    _faiss_index: object    = field(default=None, repr=False)  # faiss.Index | None

    # ── Build ──────────────────────────────────────────────────────────────────

    def rebuild(self, rows: list[dict]) -> None:
        """Rebuild the index from Data Store rows (called at startup).
        Each row must have: row_id, vector_b64, kind, summary_text, …
        """
        if not rows:
            print("  ⚠️  Second Brain index empty — no rows in Data Store yet")
            self._matrix      = np.empty((0, _DIM), dtype=np.float32)
            self._row_ids     = []
            self._metadata    = []
            self._faiss_index = None
            return

        vectors  : list[np.ndarray] = []
        row_ids  : list[str]        = []
        metadata : list[dict]       = []

        for row in rows:
            try:
                vec_bytes = base64.b64decode(row["vector_b64"])
                vec = np.frombuffer(vec_bytes, dtype=np.float32)
                # Legacy 384-dim (text-only) rows are zero-padded into the text half.
                # Shared with append() so both entry points agree on the index width.
                vectors.append(self._fit(vec).reshape(-1))
                row_ids.append(row["row_id"])
                metadata.append({
                    "kind":                row.get("kind"),
                    "summary_text":        row.get("summary_text", ""),
                    "suspect_ids_json":    row.get("suspect_ids_json", "[]"),
                    "crime_ids_json":      row.get("crime_ids_json", "[]"),
                    "station_code":        row.get("station_code"),
                    "ref_session_id":      row.get("ref_session_id"),
                    "verification_status": row.get("verification_status", "unverified"),
                    "confidence":          float(row.get("confidence", 0.5)),
                    "officer_role":        row.get("officer_role", "system"),
                    "created_at":          row.get("created_at"),
                })
            except Exception as e:
                print(f"  ⚠️  Skipping malformed brain row {row.get('row_id')}: {e}")

        if vectors:
            self._matrix   = np.vstack(vectors).astype(np.float32)
            self._row_ids  = row_ids
            self._metadata = metadata
            self._build_faiss_index()
            self._build_bm25_index()
            print(f"  ✅ Brain index rebuilt: {len(vectors)} vectors, shape {self._matrix.shape}"
                  f" | search: {'HNSW+BM25 Hybrid' if _FAISS_OK else 'NumPy+BM25 Hybrid'}")
        else:
            self._matrix      = np.empty((0, _DIM), dtype=np.float32)
            self._faiss_index = None
            self._doc_tokens  = []
            self._doc_freqs   = {}
            self._avg_dl      = 1.0

    @staticmethod
    def _fit(vec: np.ndarray) -> np.ndarray:
        """Coerce any embedding to the index width (_DIM), returning (1, _DIM).

        Documents live in [text | vision] space. `embed()` (ingestion) yields a 384-dim
        TEXT vector, so it is zero-padded into the text half — the same thing rebuild()
        does for legacy store rows. Without this, append() adopted the first vector's
        width and silently redefined the matrix to 384: queries (768) then could not be
        multiplied against it, consolidation's `cluster_vecs[:, 384:]` vision slice came
        back empty, and a FAISS build (IndexHNSWFlat(_DIM)) would reject the matrix.
        """
        v = np.asarray(vec, dtype=np.float32).reshape(-1)
        if v.shape[0] < _DIM:
            v = np.concatenate([v, np.zeros(_DIM - v.shape[0], dtype=np.float32)])
        elif v.shape[0] > _DIM:
            v = v[:_DIM]
        return v.reshape(1, _DIM)

    def append(self, vec: np.ndarray, row_id: str, meta: dict) -> None:
        """Hot-append a new embedding without full rebuild."""
        vec = self._fit(vec)
        if self._matrix.shape[0] == 0:
            self._matrix = vec
            self._build_faiss_index()
        else:
            self._matrix = np.vstack([self._matrix, vec])
            # Incremental FAISS add (HNSW supports it natively)
            if self._faiss_index is not None:
                self._faiss_index.add(vec)
            else:
                self._build_faiss_index()
        self._row_ids.append(row_id)
        self._metadata.append(meta)
        self._append_bm25(row_id, meta)

    # ── FAISS & BM25 management ────────────────────────────────────────────────

    def _tokenize(self, text: str) -> list[str]:
        import re
        return [t for t in re.findall(r"\w+", (text or "").casefold()) if len(t) > 1]

    def _bm25_reset(self) -> None:
        from collections import Counter
        self._doc_tokens: list[list[str]] = []
        self._doc_freqs = Counter()          # term -> document frequency (for IDF)
        self._postings: dict[str, list[tuple[int, int]]] = {}   # term -> [(doc_idx, tf)]
        self._doc_len: list[int] = []
        self._total_len = 0
        self._avg_dl = 1.0

    def _bm25_add(self, tokens: list[str]) -> None:
        """Index one document into the postings list. O(unique terms in doc)."""
        from collections import Counter
        idx = len(self._doc_tokens)
        self._doc_tokens.append(tokens)
        self._doc_len.append(len(tokens))
        self._total_len += len(tokens)
        for t, tf in Counter(tokens).items():
            self._doc_freqs[t] += 1
            self._postings.setdefault(t, []).append((idx, tf))
        self._avg_dl = max(1.0, self._total_len / max(1, len(self._doc_tokens)))

    def _build_bm25_index(self) -> None:
        """Build the BM25 inverted index (term -> postings) across all summaries.

        The postings list is what makes bm25_search O(matching postings) instead of
        O(docs x doc_length): previously every query term rescanned EVERY document
        with list.count(), which measured 5ms @500 docs -> 51ms @5000 docs (linear).
        Scores are unchanged — this is purely how they're reached.
        """
        self._bm25_reset()
        for m in self._metadata:
            self._bm25_add(self._tokenize(f"{m.get('summary_text', '')} {m.get('kind', '')}"))

    def _append_bm25(self, row_id: str, meta: dict) -> None:
        if not hasattr(self, "_postings"):
            self._bm25_reset()
        self._bm25_add(self._tokenize(f"{meta.get('summary_text', '')} {meta.get('kind', '')}"))

    def _build_faiss_index(self) -> None:
        """Build IndexHNSWFlat from self._matrix. No-op if FAISS unavailable."""
        if not _FAISS_OK or self._matrix.shape[0] == 0:
            self._faiss_index = None
            return
        index = _faiss.IndexHNSWFlat(_DIM, _HNSW_M, _faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = _HNSW_EF_CONSTRUCTION
        index.hnsw.efSearch       = _HNSW_EF_SEARCH
        # FAISS needs a contiguous C float32 array
        index.add(np.ascontiguousarray(self._matrix, dtype=np.float32))
        self._faiss_index = index

    def sync_faiss(self) -> None:
        """Rebuild FAISS & BM25 indices from current state."""
        self._build_faiss_index()
        self._build_bm25_index()

    # ── Search ─────────────────────────────────────────────────────────────────

    def bm25_search(self, query_text: str, k: int = 10, kind_filter: str | None = None) -> list[dict]:
        """Keyword search using BM25 scoring formula."""
        import math
        if not hasattr(self, "_doc_tokens") or not self._doc_tokens:
            return []
        q_tokens = self._tokenize(query_text)
        if not q_tokens:
            return []
        n = len(self._doc_tokens)
        k1, b = 1.5, 0.75
        scores = np.zeros(n, dtype=np.float32)
        # Walk only the postings for each query term (documents that actually contain
        # it) instead of rescanning the whole corpus. Same BM25 score, far less work.
        # NB: iterate q_tokens (not a set) so a repeated query term contributes twice,
        # exactly as the previous implementation did — this change is speed-only.
        for t in q_tokens:
            df = self._doc_freqs.get(t, 0)
            if df == 0:
                continue
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
            for idx, tf in self._postings.get(t, ()):
                dl = self._doc_len[idx]
                scores[idx] += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / self._avg_dl)))
        if kind_filter:
            mask = np.array([m.get("kind") == kind_filter for m in self._metadata])
            scores = np.where(mask, scores, -1.0)
        top_idx = np.argsort(scores)[::-1][:k]
        results = []
        for idx in top_idx:
            if scores[idx] <= 0:
                continue
            results.append({
                "score": float(scores[idx]),
                "row_id": self._row_ids[idx],
                "_matrix_idx": int(idx),
                **self._metadata[idx],
            })
        return results

    def hybrid_search(
        self,
        query_vec: np.ndarray,
        query_text: str,
        k: int = 10,
        alpha: float = 0.7,
        kind_filter: str | None = None,
        fusion: str = "rrf",
        rrf_k: int = 60,
    ) -> list[dict]:
        """Hybrid search fusing semantic (vector) and lexical (BM25) retrieval.

        fusion="rrf" (default) — Reciprocal Rank Fusion:  score = Σ wᵢ / (rrf_k + rankᵢ).
            Fuses on RANK, so the two score distributions never have to be made
            comparable. That matters here: cosine sits in a narrow band (~0.6-0.9)
            while BM25 is unbounded, so under max-normalisation a single outlier
            lexical hit crushes every other keyword signal toward 0. Rank fusion is
            what LlamaIndex's QueryFusionRetriever and Elasticsearch/Weaviate use, and
            it's the behaviour we want for exact-identifier lookups (ACC-id, FIR no.,
            vehicle reg, UPI) where BM25 puts the right row at rank 1 but with a raw
            score whose magnitude is meaningless next to a cosine.
            `alpha` stays the semantic/lexical weight (alpha vs 1-alpha).
        fusion="linear" — previous behaviour: max-normalise each list then
            alpha*vec + (1-alpha)*bm25. Retained for comparison and rollback.

        Returned `score` is normalised to [0,1] in BOTH modes, because callers
        (retrieval.py blends 0.8*score + 0.2*attention_score) assume that range.
        """
        vec_list = self.cosine_topk(query_vec, k=k * 2, kind_filter=kind_filter)
        bm_list = self.bm25_search(query_text, k=k * 2, kind_filter=kind_filter)
        vec_results = {r["row_id"]: r for r in vec_list}
        bm_results = {r["row_id"]: r for r in bm_list}

        all_ids = set(vec_results.keys()) | set(bm_results.keys())
        if not all_ids:
            return []

        # raw values kept for transparency in both modes
        max_vec = max((r["score"] for r in vec_results.values()), default=1.0) or 1.0
        max_bm = max((r["score"] for r in bm_results.values()), default=1.0) or 1.0

        blended = []
        if fusion == "rrf":
            vec_rank = {r["row_id"]: i for i, r in enumerate(vec_list)}
            bm_rank = {r["row_id"]: i for i, r in enumerate(bm_list)}
            for rid in all_ids:
                s = 0.0
                if rid in vec_rank:
                    s += alpha / (rrf_k + vec_rank[rid] + 1)
                if rid in bm_rank:
                    s += (1.0 - alpha) / (rrf_k + bm_rank[rid] + 1)
                base_item = vec_results.get(rid) or bm_results.get(rid)
                blended.append({
                    **base_item,
                    "score": float(s),
                    "semantic_score": float(vec_results[rid]["score"] / max_vec) if rid in vec_results else 0.0,
                    "keyword_score": float(bm_results[rid]["score"] / max_bm) if rid in bm_results else 0.0,
                })
            # rescale to [0,1] so downstream blending stays meaningful (RRF is ~1/rrf_k)
            top = max((c["score"] for c in blended), default=0.0) or 1.0
            for c in blended:
                c["score"] = float(c["score"] / top)
        else:
            for rid in all_ids:
                v_item = vec_results.get(rid)
                b_item = bm_results.get(rid)
                v_score = (v_item["score"] / max_vec) if v_item else 0.0
                b_score = (b_item["score"] / max_bm) if b_item else 0.0
                base_item = v_item or b_item
                blended.append({
                    **base_item,
                    "score": float(alpha * v_score + (1.0 - alpha) * b_score),
                    "semantic_score": float(v_score),
                    "keyword_score": float(b_score),
                })

        blended.sort(key=lambda x: x["score"], reverse=True)
        return blended[:k]

    def cosine_topk(
        self,
        query_vec:   np.ndarray,
        k:           int = 5,
        kind_filter: str | None = None,
    ) -> list[dict]:
        """Top-k search by cosine similarity (= inner product on normalised vectors).

        Primary path: FAISS HNSW (O(log n)) — used when no kind_filter.
        Fallback: NumPy brute-force — used when kind_filter is set (FAISS has no
        native predicate filter) or FAISS is unavailable.

        Every returned dict carries _matrix_idx for MMR vector lookup.
        """
        n = self._matrix.shape[0]
        if n == 0:
            return []

        # Safety net: coerce the query to the index width. A caller handing us a 384-dim
        # (text-space) vector used to blow up in _numpy_search with
        # "matmul: size 384 is different from 768", which semantic_recall swallowed —
        # so recall silently returned nothing. Zero-padding scores against the text half,
        # which is the sane degradation. Callers should still build query-space vectors.
        q = self._fit(query_vec)

        if self._faiss_index is not None and not kind_filter:
            return self._faiss_search(q, k)

        return self._numpy_search(q, k, kind_filter)

    def _faiss_search(self, q: np.ndarray, k: int) -> list[dict]:
        """HNSW ANN search — O(log n), sub-millisecond at Brain scale."""
        actual_k = min(k, self._matrix.shape[0])
        scores, indices = self._faiss_index.search(q, actual_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or score < 0:
                continue
            results.append({
                "score":       float(score),
                "row_id":      self._row_ids[idx],
                "_matrix_idx": int(idx),
                **self._metadata[idx],
            })
        return results

    def _numpy_search(
        self,
        q:           np.ndarray,
        k:           int,
        kind_filter: str | None,
    ) -> list[dict]:
        """Brute-force cosine via NumPy dot product — O(n) fallback."""
        scores = (self._matrix @ q.T).flatten()
        if kind_filter:
            mask   = np.array([m.get("kind") == kind_filter for m in self._metadata])
            scores = np.where(mask, scores, -2.0)
        actual_k = min(k, len(scores))
        if actual_k < len(scores):
            part_idx = np.argpartition(scores, -actual_k)[-actual_k:]
            top_idx = part_idx[np.argsort(scores[part_idx])[::-1]]
        else:
            top_idx = np.argsort(scores)[::-1]
        results = []
        for idx in top_idx:
            if scores[idx] < 0:
                continue
            results.append({
                "score":       float(scores[idx]),
                "row_id":      self._row_ids[idx],
                "_matrix_idx": int(idx),
                **self._metadata[idx],
            })
        return results

    # ── Accessors ──────────────────────────────────────────────────────────────

    @property
    def size(self) -> int:
        return self._matrix.shape[0]


# Singleton — imported by agents and startup
brain_index = BrainIndex()
