"""
Antar — Hybrid Search Index  (self-healing RAG · WI-3)
=========================================================
A CPU-only, in-memory HYBRID retriever over the `crimes` corpus, used as the last
recall stage of the self-heal loop (Sc C — fragment match):

  • SPARSE : pure-python Okapi BM25 over tokenized text blocks (crime_type, zone,
             district, acts/sections, status, io_name, fir_number). No dependency.
  • DENSE  : reuses the existing Second-Brain BGE recall (semantic_recall) — already
             CPU / in-memory / offline-first — mapped back to crime ids.
  • FUSION : Reciprocal Rank Fusion (RRF) of the two rankings. Rank-based fusion lets an
             exact fragment win on BM25 while meaning-matches ride in on the dense side.

Bounded + lazy: built on FIRST self-heal use (never at startup, so Sc-A direct hits pay
nothing), over a capped slice (SELF_HEAL_CORPUS_MAX, default 40k: all suspect-linked
crimes + most-recent up to the cap). Pure-python; a few MB / a couple seconds to build.
"""
from __future__ import annotations

import math
import os
import re
import sqlite3
from collections import defaultdict
from typing import Optional

from app.core.db_path import DB_PATH
from app.services.zcql_local import _dict_factory
from app.agents.system_catalog import CRIME_TEXT_COLUMNS
from app.core.db_path import registry_connect

_CORPUS_MAX = int(os.getenv("SELF_HEAL_CORPUS_MAX", "40000"))
_RRF_K = 60
_STOP = {"the", "a", "an", "of", "in", "on", "for", "to", "and", "or", "with", "case",
         "cases", "crime", "crimes"}
_TOKEN_RE = re.compile(r"[a-z0-9ಀ-೿]{2,}")


def tokenize(text: str) -> list[str]:
    """Lowercase, unicode-aware word tokens (keeps Kannada), stopwords dropped."""
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOP]


def _text_block(row: dict) -> str:
    return " ".join(str(row.get(c, "") or "") for c in CRIME_TEXT_COLUMNS)


class BM25:
    """Okapi BM25 over an inverted index (efficient: only scores docs that share a term)."""

    def __init__(self, docs_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.N = len(docs_tokens)
        self.doc_len = [len(d) for d in docs_tokens]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)  # term -> (doc, tf)
        self.idf: dict[str, float] = {}
        df: dict[str, int] = defaultdict(int)
        for i, toks in enumerate(docs_tokens):
            tf: dict[str, int] = defaultdict(int)
            for t in toks:
                tf[t] += 1
            for t, c in tf.items():
                self.postings[t].append((i, c))
                df[t] += 1
        for t, n in df.items():
            self.idf[t] = math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def scores(self, query_tokens: list[str]) -> dict[int, float]:
        acc: dict[int, float] = defaultdict(float)
        for t in set(query_tokens):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for doc, tf in self.postings[t]:
                dl = self.doc_len[doc]
                denom = tf + self.k1 * (1 - self.b + self.b * (dl / self.avgdl if self.avgdl else 0))
                acc[doc] += idf * (tf * (self.k1 + 1)) / (denom or 1.0)
        return acc

    def topk(self, query_tokens: list[str], k: int) -> list[int]:
        acc = self.scores(query_tokens)
        return [d for d, _ in sorted(acc.items(), key=lambda x: x[1], reverse=True)[:k]]


class HybridIndex:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.id_to_idx = {str(r.get("crime_id")): i for i, r in enumerate(rows)}
        self.bm25 = BM25([tokenize(_text_block(r)) for r in rows])

    def _dense_ranks(self, query: str, k: int) -> list[int]:
        """Corpus row indices ranked by the Second-Brain dense recall (best-effort)."""
        try:
            import json
            from app.second_brain.index import brain_index
            if getattr(brain_index, "size", 0) == 0:
                return []
            from app.second_brain.retrieval import semantic_recall
            hits = semantic_recall(query, k=k) or []
            ranked: list[int] = []
            for h in hits:
                raw = h.get("crime_ids_json") or h.get("crime_ids") or "[]"
                try:
                    ids = raw if isinstance(raw, list) else json.loads(raw)
                except Exception:
                    ids = []
                for cid in ids:
                    idx = self.id_to_idx.get(str(cid))
                    if idx is not None and idx not in ranked:
                        ranked.append(idx)
            return ranked
        except Exception:
            return []

    def search(self, query: str, k: int = 10, use_dense: bool = True) -> list[dict]:
        """Hybrid search: RRF-fuse BM25 (sparse) and dense ranks; return top-k crime rows."""
        sparse = self.bm25.topk(tokenize(query), k=k * 3)
        fused: dict[int, float] = defaultdict(float)
        for rank, idx in enumerate(sparse):
            fused[idx] += 1.0 / (_RRF_K + rank)
        if use_dense:
            for rank, idx in enumerate(self._dense_ranks(query, k=k * 2)):
                fused[idx] += 1.0 / (_RRF_K + rank)
        top = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]
        return [self.rows[i] for i, _ in top]


_INDEX: Optional[HybridIndex] = None


def _load_corpus(cap: int) -> list[dict]:
    conn = registry_connect(DB_PATH)
    conn.row_factory = _dict_factory
    cols = ("crime_id, fir_number, crime_type, act, acts_sections, zone, district, "
            "station_code, occurred_at, status, io_name")
    try:
        linked = conn.execute(
            f"SELECT {cols} FROM crimes WHERE crime_id IN "
            f"(SELECT DISTINCT crime_id FROM crime_suspects) LIMIT ?", (cap,)).fetchall()
    except Exception:
        linked = []
    rows = linked
    remain = cap - len(rows)
    if remain > 0:
        seen = {r["crime_id"] for r in rows}
        try:
            recent = conn.execute(
                f"SELECT {cols} FROM crimes ORDER BY occurred_at DESC LIMIT ?",
                (remain + len(seen),)).fetchall()
            rows = rows + [r for r in recent if r["crime_id"] not in seen]
        except Exception:
            pass
    conn.close()
    return rows[:cap]


def get_index() -> HybridIndex:
    """Lazily build (once) and return the hybrid index over a bounded crimes slice."""
    global _INDEX
    if _INDEX is None:
        _INDEX = HybridIndex(_load_corpus(_CORPUS_MAX))
    return _INDEX
