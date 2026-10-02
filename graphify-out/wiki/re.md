# re

> 22 nodes · cohesion 0.13

## Key Concepts

- **re** (21 connections)
- **hybrid_index.py** (18 connections) — `app/services/hybrid_index.py`
- **get_index()** (8 connections) — `app/services/hybrid_index.py`
- **BM25** (6 connections) — `app/services/hybrid_index.py`
- **tokenize()** (6 connections) — `app/services/hybrid_index.py`
- **HybridIndex** (5 connections) — `app/services/hybrid_index.py`
- **._dense_ranks()** (5 connections) — `app/services/hybrid_index.py`
- **.__init__()** (4 connections) — `app/services/hybrid_index.py`
- **.search()** (4 connections) — `app/services/hybrid_index.py`
- **.size()** (3 connections) — `app/second_brain/index.py`
- **_load_corpus()** (3 connections) — `app/services/hybrid_index.py`
- **test_hybrid_index_returns_fragment_matches()** (3 connections) — `tests/test_self_heal.py`
- **.scores()** (2 connections) — `app/services/hybrid_index.py`
- **.topk()** (2 connections) — `app/services/hybrid_index.py`
- **_text_block()** (2 connections) — `app/services/hybrid_index.py`
- **.__init__()** (1 connections) — `app/services/hybrid_index.py`
- **Antar — Hybrid Search Index (self-healing RAG · WI-3)…** (1 connections) — `app/services/hybrid_index.py`
- **Hybrid search: RRF-fuse BM25 (sparse) and dense ranks; return top-k crime rows.** (1 connections) — `app/services/hybrid_index.py`
- **Lazily build (once) and return the hybrid index over a bounded crimes slice.** (1 connections) — `app/services/hybrid_index.py`
- **Lowercase, unicode-aware word tokens (keeps Kannada), stopwords dropped.** (1 connections) — `app/services/hybrid_index.py`
- **Okapi BM25 over an inverted index (efficient: only scores docs that share a…** (1 connections) — `app/services/hybrid_index.py`
- **Corpus row indices ranked by the Second-Brain dense recall (best-effort).** (1 connections) — `app/services/hybrid_index.py`

## Relationships

- [test_self_heal.py](test_self_heal.py.md) (6 shared connections)
- [zcql_local.py](zcql_local.py.md) (3 shared connections)
- [anomaly.py](anomaly.py.md) (2 shared connections)
- [time](time.md) (2 shared connections)
- [semantic_recall](semantic_recall.md) (2 shared connections)
- [intent_parser.py](intent_parser.py.md) (2 shared connections)
- [chat_stream.py](chat_stream.py.md) (2 shared connections)
- [heuristic_select](heuristic_select.md) (2 shared connections)
- [BrainIndex](BrainIndex.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [answer_writer.py](answer_writer.py.md) (1 shared connections)

## Source Files

- `app/second_brain/index.py`
- `app/services/hybrid_index.py`
- `tests/test_self_heal.py`

## Audit Trail

- EXTRACTED: 66 (96%)
- INFERRED: 3 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*