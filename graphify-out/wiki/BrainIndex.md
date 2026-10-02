# BrainIndex

> 36 nodes · cohesion 0.10

## Key Concepts

- **BrainIndex** (31 connections) — `app/second_brain/index.py`
- **._build_bm25_index()** (7 connections) — `app/second_brain/index.py`
- **.cosine_topk()** (7 connections) — `app/second_brain/index.py`
- **TestIndexToleratesWrongWidth** (7 connections) — `tests/test_query_vector_space.py`
- **.append()** (6 connections) — `app/second_brain/index.py`
- **._fit()** (6 connections) — `app/second_brain/index.py`
- **ndarray** (6 connections)
- **._append_bm25()** (5 connections) — `app/second_brain/index.py`
- **._build_faiss_index()** (5 connections) — `app/second_brain/index.py`
- **.hybrid_search()** (5 connections) — `app/second_brain/index.py`
- **.rebuild()** (5 connections) — `app/second_brain/index.py`
- **._idx()** (5 connections) — `tests/test_query_vector_space.py`
- **._bm25_add()** (4 connections) — `app/second_brain/index.py`
- **.bm25_search()** (4 connections) — `app/second_brain/index.py`
- **._faiss_search()** (4 connections) — `app/second_brain/index.py`
- **._numpy_search()** (4 connections) — `app/second_brain/index.py`
- **.sync_faiss()** (4 connections) — `app/second_brain/index.py`
- **._tokenize()** (4 connections) — `app/second_brain/index.py`
- **._bm25_reset()** (3 connections) — `app/second_brain/index.py`
- **.test_768_query_works()** (3 connections) — `tests/test_query_vector_space.py`
- **.test_384_query_does_not_raise()** (2 connections) — `tests/test_query_vector_space.py`
- **.test_append_pads_to_index_width()** (2 connections) — `tests/test_query_vector_space.py`
- **Coerce any embedding to the index width (_DIM), returning (1, _DIM). Documents…** (1 connections) — `app/second_brain/index.py`
- **Hot-append a new embedding without full rebuild.** (1 connections) — `app/second_brain/index.py`
- **Index one document into the postings list. O(unique terms in doc).** (1 connections) — `app/second_brain/index.py`
- *... and 11 more nodes in this community*

## Relationships

- [embedder.py](embedder.py.md) (5 shared connections)
- [index.py](index.py.md) (4 shared connections)
- [second_brain/store.py](second_brain-store.py.md) (2 shared connections)
- [_rand_unit](_rand_unit.md) (2 shared connections)
- [semantic_recall](semantic_recall.md) (1 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `app/second_brain/index.py`
- `tests/test_query_vector_space.py`

## Audit Trail

- EXTRACTED: 76 (96%)
- INFERRED: 3 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*