"""
Antar — Second Brain Durable Store (Data Store rows)
=========================================================
Source-of-truth persistence for embeddings: the `brain_embeddings` table.
The in-memory cosine index (index.py) is rebuilt from here at every boot.

Phase 2 status: minimal real signatures so `main.py` boots and the index can
rebuild from an EMPTY store (no Catalyst creds yet). Phase 4 (Gate G3) fills in
the actual Data Store insert/select via app.core.catalyst.get_app().

Vectors are stored as base64-encoded float32 in the `vector_b64` column (≤ ~2 KB).
"""

from __future__ import annotations

import base64
import json

import numpy as np

from app.core.settings import settings

TABLE = "brain_embeddings"


def vec_to_b64(vec: np.ndarray) -> str:
    """Encode a float32 vector → base64 string for the Data Store text column."""
    return base64.b64encode(np.asarray(vec, dtype=np.float32).tobytes()).decode("ascii")


def b64_to_vec(b64: str) -> np.ndarray:
    return np.frombuffer(base64.b64decode(b64), dtype=np.float32)


def _local_curated_rows() -> list[dict]:
    """Curated Brain rows held in the local durable store, in rebuild()'s shape.

    The FIR corpus tier is deliberately excluded: it is searched on disk by
    `vec_store.search()` and must never be pulled into the in-memory matrix, which is
    what kept RAM proportional to the corpus.
    """
    try:
        from app.second_brain import vec_store
        rows: list[dict] = []
        for kind in vec_store.CURATED_KINDS:
            rows.extend(vec_store.all_rows(kind=kind))
        return rows
    except Exception as e:                                  # never block boot on the store
        print(f"  ⚠️  local brain store unavailable ({e})")
        return []


async def load_all_embeddings_from_store() -> list[dict]:
    """
    Return all brain_embeddings rows for the boot index rebuild.

    Local durable store FIRST, Catalyst Data Store second. The remote fetch is capped at
    20 s and that cap is reached routinely — every local boot came up with an empty index
    and the Brain ran on three planted summaries (measured 2026-09-23). Reading the local
    store first means the Brain survives a restart with whatever was indexed, and the
    remote is a synchronisation source rather than a single point of failure.
    """
    local = _local_curated_rows()
    if local:
        print(f"  🧠 Brain: {len(local)} curated row(s) from the local store")
        return local

    # An EMPTY curated tier is not the same as an absent store, and conflating the two
    # cost 20 seconds on every single boot.
    #
    # `_local_curated_rows()` deliberately excludes the `fir` tier (it is searched on disk,
    # never loaded into the in-memory matrix). After P1-2 the local store holds 100,000
    # FIR rows and zero curated ones — a perfectly normal state, since nothing has been
    # curated yet. The old code read that empty list as "no local store" and fell through
    # to the Catalyst fetch, which then timed out at its 20 s cap. Measured: every local
    # start paid a 20-second stall to discover nothing, before answering a single request.
    #
    # If the store exists and holds rows, it IS the source of truth for the boot index.
    # An empty curated tier is an honest answer to give immediately.
    try:
        from app.second_brain import vec_store
        if vec_store.count() > 0:
            print("  🧠 Brain: local store present, curated tier empty — "
                  "skipping the remote fetch")
            return []
    except Exception:                       # noqa: BLE001 — fall through to the remote
        pass

    if not (settings.CATALYST_PROJECT_ID and settings.QUICKML_CLIENT_ID):
        return []
    try:
        import asyncio
        from app.core.catalyst import zcql_query

        # zcql_query is a SYNCHRONOUS network call into the Catalyst SDK with no timeout
        # of its own. Awaiting it directly from an `async def` blocked the event loop:
        # with credentials configured but the Data Store slow or unreachable, startup
        # wedged here indefinitely and the whole API stopped answering — /api/health
        # included — even though uvicorn had already logged "Application startup
        # complete". Push it to a worker thread and cap it; an empty index is a degraded
        # Brain, which the rest of the system already handles, whereas a hung event loop
        # is a dead server.
        return await asyncio.wait_for(
            asyncio.to_thread(zcql_query, f"SELECT * FROM {TABLE} LIMIT 2000"),
            timeout=20.0,
        )
    except asyncio.TimeoutError:
        print("  ⚠️  brain store load timed out after 20s — booting with empty index")
        return []
    except Exception as e:  # pragma: no cover
        print(f"  ⚠️  brain store load failed ({e}) — booting with empty index")
        return []


async def insert_embedding(row: dict) -> None:
    """
    Persist one brain_embeddings row. `row` must include row_id, kind, summary_text,
    vector_b64, and the *_json metadata fields (see 6_D/05_Backend_Schema.md).
    Phase 4 wires the real insert.  [VERIFY G3]
    """
    if not (settings.CATALYST_PROJECT_ID and settings.QUICKML_CLIENT_ID):
        raise RuntimeError("Catalyst creds required to persist brain embeddings")
    from app.core.catalyst import get_app
    get_app().datastore().table(TABLE).insert_row(row)


def serialize_meta(suspect_ids: list[str] | None = None,
                   crime_ids: list[str] | None = None) -> dict:
    """Helper: JSON-encode the list metadata columns."""
    return {
        "suspect_ids_json": json.dumps(suspect_ids or []),
        "crime_ids_json": json.dumps(crime_ids or []),
    }
