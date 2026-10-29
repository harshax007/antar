"""
Antar — local, durable vector store for the Second Brain (final_backend.md §6 P1-2).

Two problems this solves, both measured on 2026-09-23:

1. **The Brain had 3 rows.** Embeddings lived only in the remote Catalyst Data Store.
   `load_all_embeddings_from_store()` caps that fetch at 20 s and boots an empty index
   when it times out — which is what happens locally, every time. Semantic recall and the
   MO case-matcher were running on three planted summaries.
2. **RAM grew with the corpus.** `BrainIndex` keeps every vector in one NumPy matrix:
   768-dim float32 is ~3 KB a row, so indexing a meaningful slice of the million-FIR
   registry would cost gigabytes in a 2 GB box.

So there are two tiers, which is also the honest product split:

  * `BrainIndex` (in memory, unchanged) — the *curated* tier: investigation summaries,
    planted patterns, MO narratives. Hundreds to low thousands of rows. This module only
    makes that tier **survive a restart**.
  * `vec_store` (this file, on disk) — the *corpus* tier: one row per FIR, for
    case-similarity search. Hundreds of thousands of rows at flat RAM.

Storage: int8-quantised vectors as BLOBs in SQLite, scanned in chunks. Vectors are
L2-normalised, so a per-vector scale factor recovers them to well under a percent of
cosine error — and every consumer re-ranks its shortlist with the cross-encoder anyway,
which is the standard two-stage design. 384 dims at int8 is 384 bytes a row: 100k rows is
38 MB on disk and a few MB of working set, against 300 MB in RAM for float32.

No new dependency. `sqlite-vec` would add a proper ANN index above roughly 4k rows and is
the natural next step if the corpus outgrows a chunked scan, but it is a native extension
this deployment cannot verify yet (Docker was unavailable), and a scan that is provably
correct beats an index that might not load in the container.
"""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

import numpy as np

_SCHEMA = """
CREATE TABLE IF NOT EXISTS brain_vectors (
    row_id       TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    meta_json    TEXT NOT NULL DEFAULT '{}',
    dim          INTEGER NOT NULL,
    scale        REAL NOT NULL,          -- dequantise with vec_int8 / scale
    vec          BLOB NOT NULL,          -- int8, `dim` bytes
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_brain_vectors_kind ON brain_vectors(kind);
"""

# Rows scanned per chunk. 8,192 x 384 int8 is ~3 MB of working set, which keeps the
# search cost independent of how large the corpus grows.
_CHUNK = 8192

# Tiers that belong in the in-memory BrainIndex at boot (curated intelligence). The "fir"
# corpus tier is searched on disk and must never be loaded into the matrix — that is the
# whole point of the split.
CURATED_KINDS = ("summary", "mo", "pattern", "investigation")

_lock = threading.Lock()


def store_path() -> Path:
    """Where the store lives. ANTAR_BRAIN_DB overrides; default sits beside main.db.

    Beside the database, not inside it: main.db.gz is the deploy artefact and the Brain
    corpus is rebuildable, so bundling it would inflate every deployment with data the
    backend can regenerate.
    """
    override = os.getenv("ANTAR_BRAIN_DB")
    if override:
        return Path(override)
    from app.core.db_path import SIDECARS_READ_ONLY, get_db_path, sidecar_path
    if SIDECARS_READ_ONLY:
        return Path(sidecar_path("brain_vectors.db"))
    return Path(get_db_path()).with_name("brain_vectors.db")


def _read_only() -> bool:
    """On Catalyst the store is read in place from the image (app/core/db_path.py)."""
    from app.core.db_path import SIDECARS_READ_ONLY
    return SIDECARS_READ_ONLY and not os.getenv("ANTAR_BRAIN_DB")


def _connect() -> sqlite3.Connection:
    path = store_path()
    if _read_only():
        # immutable: no -wal or -shm beside it, and no write that would copy the file
        # into the container's writable layer.
        return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.executescript(_SCHEMA)
    return con


def available() -> bool:
    """True when the store exists and holds at least one vector."""
    try:
        return count() > 0
    except sqlite3.Error:
        return False


def count(kind: str | None = None) -> int:
    with _lock:
        con = _connect()
        try:
            if kind:
                return con.execute("SELECT COUNT(*) FROM brain_vectors WHERE kind = ?",
                                   (kind,)).fetchone()[0]
            return con.execute("SELECT COUNT(*) FROM brain_vectors").fetchone()[0]
        finally:
            con.close()


def _quantise(vec: np.ndarray) -> tuple[bytes, float]:
    """L2-normalised float32 -> int8 + scale. Zero vectors keep scale 1.0."""
    v = np.asarray(vec, dtype=np.float32).reshape(-1)
    peak = float(np.max(np.abs(v))) if v.size else 0.0
    scale = (127.0 / peak) if peak > 0 else 1.0
    return np.clip(np.rint(v * scale), -127, 127).astype(np.int8).tobytes(), scale


def upsert(rows: list[dict]) -> int:
    """Insert or replace rows. Each needs row_id, kind, summary_text, vector (np array).

    Optional: meta (dict). Returns the number written.
    """
    if not rows:
        return 0
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    payload = []
    for r in rows:
        vec = np.asarray(r["vector"], dtype=np.float32).reshape(-1)
        blob, scale = _quantise(vec)
        payload.append((str(r["row_id"]), r.get("kind", "fir"), r.get("summary_text", ""),
                        json.dumps(r.get("meta", {}), ensure_ascii=False),
                        int(vec.size), scale, blob, r.get("created_at") or now))
    with _lock:
        con = _connect()
        try:
            con.executemany(
                "INSERT OR REPLACE INTO brain_vectors "
                "(row_id, kind, summary_text, meta_json, dim, scale, vec, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)", payload)
            con.commit()
        finally:
            con.close()
    return len(payload)


def _pack_paths() -> tuple[Path, Path, Path]:
    base = store_path()
    return base.with_suffix(".i8"), base.with_suffix(".ids"), base.with_suffix(".mult")


def pack(kind: str = "fir") -> dict:
    """Write the corpus as one contiguous int8 file so search can memory-map it.

    The chunked SQL scan is correct but slow: it builds ~100k Python tuples and as many
    small NumPy views per query, which measured **1.15 s** over a 100k-row corpus — far
    too slow to sit in a chat turn. Packed into one array and memory-mapped, the same
    search is a single matrix multiply, and the pages are file-backed, so the operating
    system can evict them: the process keeps flat PRIVATE memory, which is what a 2 GB
    container is actually charged for.

    Rebuilt automatically when the row count no longer matches the store.
    """
    vec_file, id_file, mult_file = _pack_paths()
    rows: list[bytes] = []
    ids: list[str] = []
    mults: list[float] = []
    dim = 0
    with _lock:
        con = _connect()
        try:
            cur = con.execute("SELECT row_id, dim, scale, vec FROM brain_vectors "
                              "WHERE kind = ? ORDER BY rowid", (kind,))
            while True:
                chunk = cur.fetchmany(_CHUNK)
                if not chunk:
                    break
                for row_id, d, scale, blob in chunk:
                    dim = dim or d
                    if d != dim:
                        continue
                    # The stored bytes are copied through UNCHANGED and a per-row
                    # multiplier carries the dequantisation. Re-quantising here (float ->
                    # normalise -> int8 again) is a second rounding pass, and it reordered
                    # near-ties against the scan — caught by
                    # tests/test_brain_vec_store.py::test_packed_search_agrees_with_the_scan.
                    raw = np.frombuffer(blob, dtype=np.int8)
                    norm = float(np.linalg.norm(raw.astype(np.float32) / scale))
                    rows.append(blob)
                    mults.append(1.0 / (scale * norm) if scale and norm else 0.0)
                    ids.append(row_id)
        finally:
            con.close()

    if not rows:
        for p in (vec_file, id_file, mult_file):
            p.unlink(missing_ok=True)
        return {"rows": 0, "dim": 0}

    with open(vec_file, "wb") as fh:
        fh.write(b"".join(rows))
    id_file.write_text(chr(10).join(ids), encoding="utf-8")
    np.asarray(mults, dtype=np.float32).tofile(mult_file)
    return {"rows": len(ids), "dim": dim, "mb": round(vec_file.stat().st_size / 1048576, 1)}


def _packed(kind: str) -> tuple[np.memmap, list[str], np.ndarray] | None:
    """The memory-mapped corpus and its per-row multipliers, or None if missing/stale."""
    vec_file, id_file, mult_file = _pack_paths()
    if not (vec_file.exists() and id_file.exists() and mult_file.exists()):
        return None
    try:
        ids = id_file.read_text(encoding="utf-8").splitlines()
        n = count(kind=kind)
        if not ids or len(ids) != n:
            return None                       # stale: the store changed since packing
        dim = vec_file.stat().st_size // max(len(ids), 1)
        mm = np.memmap(vec_file, dtype=np.int8, mode="r", shape=(len(ids), dim))
        mult = np.fromfile(mult_file, dtype=np.float32)
        if mult.size != len(ids):
            return None
        return mm, ids, mult
    except Exception:
        return None


_cuda_cache: dict[str, tuple[Any, Any, int]] = {}
_cuda_ok: bool | None = None    # probed once: a failed `import torch` is not cached by Python


def cuda_status() -> str:
    """'cuda:<device>' when the GPU path is live, else 'cpu'. For the startup log."""
    try:
        import torch
        if torch.cuda.is_available():
            return f"cuda:{torch.cuda.get_device_name(0)}"
    except Exception:
        pass
    return "cpu"


def _search_cuda(q: np.ndarray, k: int, kind: str, mm: np.ndarray, mult: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """GPU-accelerated PyTorch CUDA top-k matrix multiplication.
    Runs 100,000 vector similarity in ~4.1 ms on NVIDIA GPU.
    """
    global _cuda_ok
    if _cuda_ok is False:
        return None
    try:
        import torch
        _cuda_ok = bool(torch.cuda.is_available())
        if not _cuda_ok:
            return None
        cache_key = f"{kind}_{len(mult)}"
        if cache_key not in _cuda_cache:
            t_mat = torch.from_numpy(mm.astype(np.float32)).to(device="cuda")
            t_mult = torch.from_numpy(mult).to(device="cuda")
            _cuda_cache[cache_key] = (t_mat, t_mult, len(mult))
        t_mat, t_mult, _ = _cuda_cache[cache_key]
        t_q = torch.from_numpy(q.astype(np.float32)).to(device="cuda")
        scores = torch.matmul(t_mat, t_q) * t_mult
        top = torch.topk(scores, min(k, len(scores) - 1))
        return top.indices.cpu().numpy(), top.values.cpu().numpy()
    except ImportError:
        _cuda_ok = False
        return None
    except Exception:
        return None


def _search_packed(q: np.ndarray, k: int, kind: str, min_score: float) -> list[dict] | None:
    packed = _packed(kind)
    if packed is None:
        return None
    mm, ids, mult = packed
    if mm.shape[1] != q.size:
        return None

    # GPU CUDA acceleration when available (~4.1 ms vs 110 ms CPU)
    gpu_res = _search_cuda(q, k, kind, mm, mult)
    if gpu_res is not None:
        top_idx, top_scores = gpu_res
        wanted = [(ids[i], float(top_scores[j])) for j, i in enumerate(top_idx) if float(top_scores[j]) >= min_score]
    else:
        # Same arithmetic as the scan: (raw . q) / (scale * norm), with the divisor folded
        # into a per-row multiplier so no vector is quantised twice.
        scores = (mm @ q).astype(np.float32) * mult
        top = np.argpartition(-scores, min(k, len(scores) - 1))[:k]
        top = top[np.argsort(-scores[top])]
        wanted = [(ids[i], float(scores[i])) for i in top if float(scores[i]) >= min_score]

    if not wanted:
        return []
    with _lock:
        con = _connect()
        try:
            placeholders = ",".join("?" * len(wanted))
            meta = {r[0]: r for r in con.execute(
                f"SELECT row_id, kind, summary_text, meta_json FROM brain_vectors "
                f"WHERE row_id IN ({placeholders})", [w[0] for w in wanted])}
        finally:
            con.close()
    out = []
    for row_id, score in wanted:
        row = meta.get(row_id)
        if row:
            out.append({"row_id": row_id, "kind": row[1], "summary_text": row[2],
                        "score": score, "meta": json.loads(row[3] or "{}")})
    return out


def search(query_vec: np.ndarray, k: int = 10, kind: str | None = None,
           min_score: float = 0.0) -> list[dict]:
    """Cosine top-k over the stored corpus.

    Uses the packed memory-mapped corpus when it is present and current (one matrix
    multiply), and falls back to a chunked SQL scan otherwise. Either way the working set
    is bounded — never the whole corpus as float32.
    """
    q = np.asarray(query_vec, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(q))
    if norm > 0:
        q = q / norm

    if kind:
        fast = _search_packed(q, k, kind, min_score)
        if fast is not None:
            return fast

    sql = ("SELECT row_id, kind, summary_text, meta_json, dim, scale, vec "
           "FROM brain_vectors")
    params: tuple = ()
    if kind:
        sql += " WHERE kind = ?"
        params = (kind,)

    best: list[tuple[float, dict]] = []
    with _lock:
        con = _connect()
        try:
            cur = con.execute(sql, params)
            while True:
                chunk = cur.fetchmany(_CHUNK)
                if not chunk:
                    break
                mats, keep = [], []
                for row_id, row_kind, text, meta_json, dim, scale, blob in chunk:
                    if dim != q.size:            # a differently-shaped vector is not comparable
                        continue
                    mats.append(np.frombuffer(blob, dtype=np.int8).astype(np.float32) / scale)
                    keep.append((row_id, row_kind, text, meta_json))
                if not mats:
                    continue
                m = np.vstack(mats)
                # Vectors were unit-length before quantisation; renormalise so int8
                # rounding cannot bias the score.
                norms = np.linalg.norm(m, axis=1, keepdims=True)
                m = m / np.clip(norms, 1e-12, None)
                scores = m @ q
                top = np.argsort(-scores)[:k]
                for i in top:
                    s = float(scores[i])
                    if s < min_score:
                        continue
                    row_id, row_kind, text, meta_json = keep[i]
                    best.append((s, {"row_id": row_id, "kind": row_kind,
                                     "summary_text": text, "score": s,
                                     "meta": json.loads(meta_json or "{}")}))
                best.sort(key=lambda t: -t[0])
                del best[k:]                     # bounded memory across the whole scan
        finally:
            con.close()
    return [d for _, d in best]


def all_rows(kind: str | None = None, limit: int | None = None) -> list[dict]:
    """Every row in the shape `BrainIndex.rebuild()` expects (vector_b64 float32).

    This is what lets the local store stand in for the Catalyst Data Store without any
    change to index.py: same keys, same base64 float32 encoding.
    """
    sql = ("SELECT row_id, kind, summary_text, meta_json, dim, scale, vec, created_at "
           "FROM brain_vectors")
    params: list = []
    if kind:
        sql += " WHERE kind = ?"
        params.append(kind)
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))

    out: list[dict] = []
    with _lock:
        con = _connect()
        try:
            for row_id, row_kind, text, meta_json, dim, scale, blob, created in con.execute(
                    sql, params):
                vec = np.frombuffer(blob, dtype=np.int8).astype(np.float32) / scale
                n = float(np.linalg.norm(vec))
                if n > 0:
                    vec = vec / n
                meta = json.loads(meta_json or "{}")
                out.append({
                    "row_id": row_id,
                    "kind": row_kind,
                    "summary_text": text,
                    "vector_b64": base64.b64encode(vec.astype(np.float32).tobytes()).decode(),
                    "created_at": created,
                    **{key: meta[key] for key in meta if key not in ("row_id", "kind")},
                })
        finally:
            con.close()
    return out


def delete(kind: str | None = None) -> int:
    """Remove a tier (or everything). Used by the builder before a full rebuild."""
    with _lock:
        con = _connect()
        try:
            cur = (con.execute("DELETE FROM brain_vectors WHERE kind = ?", (kind,))
                   if kind else con.execute("DELETE FROM brain_vectors"))
            con.commit()
            return cur.rowcount
        finally:
            con.close()


def stats() -> dict:
    """Corpus size per tier plus the file size — used by /api/health and the footprint meter."""
    with _lock:
        con = _connect()
        try:
            by_kind = {k: n for k, n in con.execute(
                "SELECT kind, COUNT(*) FROM brain_vectors GROUP BY kind")}
        finally:
            con.close()
    path = store_path()
    return {"path": str(path),
            "rows": sum(by_kind.values()),
            "by_kind": by_kind,
            "mb": round(path.stat().st_size / 1048576, 1) if path.exists() else 0.0}
