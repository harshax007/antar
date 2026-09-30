"""
The local durable vector store (final_backend.md §6 P1-2).

Two properties matter and both are tested against behaviour, not implementation:

  * **Durability** — the Brain came up with 3 planted rows because embeddings lived only
    in a remote Data Store whose fetch times out at 20 s. Whatever is indexed must
    survive a process restart.
  * **Flat RAM** — `BrainIndex` holds every vector in one matrix, so indexing a
    meaningful slice of a million FIRs would cost gigabytes in a 2 GB box. The store's
    working set must not grow with the corpus.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.second_brain import vec_store


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """A store in its own file, so tests never touch the real corpus."""
    monkeypatch.setenv("ANTAR_BRAIN_DB", str(tmp_path / "brain_test.db"))
    yield vec_store
    vec_store.delete()


def _unit(n: int, dim: int = 384, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.normal(size=(n, dim)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def _rows(vecs, kind="fir", offset=0):
    return [{"row_id": f"{kind}:{i + offset}", "kind": kind,
             "summary_text": f"case {i + offset}", "vector": v,
             "meta": {"district": "Bengaluru City" if i % 2 else "Mysuru City",
                      "fir_no": f"F{i + offset}"}}
            for i, v in enumerate(vecs)]


def test_roundtrip_and_search_ranks_by_cosine(store):
    vecs = _unit(50)
    store.upsert(_rows(vecs))
    assert store.count() == 50

    target = 7
    hits = store.search(vecs[target], k=5)
    assert hits, "search returned nothing for a vector that is in the store"
    assert hits[0]["row_id"] == f"fir:{target}", "the exact vector is not ranked first"
    assert hits[0]["score"] > 0.99, f"self-similarity degraded to {hits[0]['score']}"
    assert [h["score"] for h in hits] == sorted((h["score"] for h in hits), reverse=True)


def test_int8_quantisation_keeps_ranking_honest(store):
    """Vectors are stored int8 to fit the budget; that must not reorder results.

    384 bytes a row instead of 1,536 is what makes a 100k corpus 38 MB instead of 150 MB.
    The cost is rounding, and the thing to protect is the ORDER the officer sees.
    """
    vecs = _unit(200, seed=3)
    store.upsert(_rows(vecs))
    q = _unit(1, seed=99)[0]

    exact = np.argsort(-(vecs @ q))[:10]
    got = [int(h["row_id"].split(":")[1]) for h in store.search(q, k=10)]

    overlap = len(set(got) & set(exact.tolist()))
    assert overlap >= 9, f"int8 storage changed the top-10 ({overlap}/10 kept): {got} vs {exact.tolist()}"
    assert got[0] == int(exact[0]), "int8 storage changed the best match"


def test_survives_a_restart(store, tmp_path, monkeypatch):
    """The failure this module exists to fix: an index that is empty after every boot."""
    store.upsert(_rows(_unit(12), kind="summary"))
    assert store.count(kind="summary") == 12

    # Simulate a restart: nothing cached in this process, only the file on disk.
    import importlib
    from app.second_brain import vec_store as fresh
    importlib.reload(fresh)
    monkeypatch.setenv("ANTAR_BRAIN_DB", str(tmp_path / "brain_test.db"))

    assert fresh.count(kind="summary") == 12
    rows = fresh.all_rows(kind="summary")
    assert len(rows) == 12
    assert all("vector_b64" in r for r in rows), "rows are not in BrainIndex.rebuild()'s shape"


def test_working_set_does_not_grow_with_the_corpus(store):
    """Search must scan in chunks. A 20k-row corpus must not cost 20k rows of RAM.

    Measured as the process RSS delta across a search, which is the number that actually
    threatens a 2 GB container.
    """
    psutil = pytest.importorskip("psutil")
    proc = psutil.Process()

    store.upsert(_rows(_unit(20_000, seed=5)))
    q = _unit(1, seed=11)[0]
    store.search(q, k=5)                                   # warm any allocator growth

    before = proc.memory_info().rss
    for _ in range(3):
        hits = store.search(q, k=5)
    grew_mb = (proc.memory_info().rss - before) / 1048576

    assert hits, "search over a large corpus returned nothing"
    # One chunk is 8,192 x 384 float32 ~ 12 MB while it is held; the whole corpus as
    # float32 would be ~29 MB and would keep growing. Allow generous headroom and still
    # catch "the entire corpus was loaded".
    assert grew_mb < 25, f"search grew RSS by {grew_mb:.1f} MB — it is not scanning in chunks"


def test_kind_isolation_keeps_the_corpus_out_of_the_in_memory_index(store):
    """`all_rows(kind=…)` is what stops the FIR tier being loaded into BrainIndex.

    If the corpus tier ever leaked into the curated load, RAM would scale with the
    registry again — the exact regression this split prevents.
    """
    store.upsert(_rows(_unit(5), kind="summary"))
    store.upsert(_rows(_unit(30), kind="fir", offset=100))

    assert "fir" not in vec_store.CURATED_KINDS
    curated = [r for kind in vec_store.CURATED_KINDS for r in store.all_rows(kind=kind)]
    assert len(curated) == 5, "the FIR corpus leaked into the curated tier"
    assert store.count(kind="fir") == 30


def test_missing_store_is_not_an_error(tmp_path, monkeypatch):
    """No corpus yet must read as 'nothing indexed', never as a crash or a false empty."""
    monkeypatch.setenv("ANTAR_BRAIN_DB", str(tmp_path / "absent.db"))
    assert vec_store.count() == 0
    assert vec_store.available() is False
    assert vec_store.search(_unit(1)[0], k=5) == []
    assert vec_store.stats()["rows"] == 0


def test_packed_search_agrees_with_the_scan(store):
    """The memory-mapped fast path must return what the SQL scan returns.

    Packing exists because the scan measured 1.15 s over a 100k corpus — too slow for a
    chat turn. A faster path that ranks differently would be a silent regression in what
    the officer is shown, so the two are compared directly.
    """
    vecs = _unit(500, seed=13)
    store.upsert(_rows(vecs))
    q = _unit(1, seed=77)[0]

    scan = store.search(q, k=10, kind=None)          # kind=None never uses the packed file
    packed_info = store.pack(kind="fir")
    assert packed_info["rows"] == 500
    fast = store.search(q, k=10, kind="fir")

    assert [h["row_id"] for h in fast] == [h["row_id"] for h in scan], (
        "packed search ranks differently from the scan")
    for a, b in zip(fast, scan):
        assert abs(a["score"] - b["score"]) < 0.01, f"score drift {a['score']} vs {b['score']}"


def test_stale_pack_is_ignored_not_trusted(store):
    """Rows added after packing must not be invisible.

    A packed file that no longer matches the store is worse than no packed file: the
    corpus would silently stop growing. `_packed()` compares row counts and falls back.
    """
    store.upsert(_rows(_unit(20, seed=21)))
    store.pack(kind="fir")
    newcomer = _unit(1, seed=999)[0]
    store.upsert([{"row_id": "fir:new", "kind": "fir", "summary_text": "new case",
                   "vector": newcomer, "meta": {}}])

    hits = store.search(newcomer, k=1, kind="fir")
    assert hits and hits[0]["row_id"] == "fir:new", (
        "a row added after packing was invisible — the stale pack was trusted")
