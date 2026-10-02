# CrossEncoderReranker

> 24 nodes · cohesion 0.09

## Key Concepts

- **CrossEncoderReranker** (10 connections) — `app/second_brain/reranker.py`
- **TestCrossEncoderReranker** (10 connections) — `tests/test_brain_scale.py`
- **reranker.py** (6 connections) — `app/second_brain/reranker.py`
- **.rerank()** (3 connections) — `app/second_brain/reranker.py`
- **_sigmoid()** (3 connections) — `app/second_brain/reranker.py`
- **.test_rerank_fallback_when_offline()** (3 connections) — `tests/test_brain_scale.py`
- **.load()** (2 connections) — `app/second_brain/reranker.py`
- **ndarray** (2 connections)
- **.setup_class()** (2 connections) — `tests/test_brain_scale.py`
- **.test_rerank_scores_relevant_pair_higher()** (2 connections) — `tests/test_brain_scale.py`
- **.test_rerank_sets_score_field()** (2 connections) — `tests/test_brain_scale.py`
- **.available()** (1 connections) — `app/second_brain/reranker.py`
- **.__init__()** (1 connections) — `app/second_brain/reranker.py`
- **Antar — Cross-Encoder Reranker + MMR Diversifier (Task #10)…** (1 connections) — `app/second_brain/reranker.py`
- **Lazy-loaded ms-marco cross-encoder for two-stage Brain retrieval. Call…** (1 connections) — `app/second_brain/reranker.py`
- **Download/load the cross-encoder. Returns True on success.** (1 connections) — `app/second_brain/reranker.py`
- **Score (query, summary_text) pairs; sort descending; return top_n. Side-effect:…** (1 connections) — `app/second_brain/reranker.py`
- **Load a fresh reranker instance per class — avoids depending on app startup…** (1 connections) — `tests/test_brain_scale.py`
- **(query, relevant_doc) must score higher than (query, unrelated_doc).** (1 connections) — `tests/test_brain_scale.py`
- **Without a model, rerank returns candidates[:top_n] in original order.** (1 connections) — `tests/test_brain_scale.py`
- **After reranking, 'score' must be updated to the sigmoid-normalised CE score.** (1 connections) — `tests/test_brain_scale.py`
- **.test_rerank_empty_candidates()** (1 connections) — `tests/test_brain_scale.py`
- **.test_rerank_top_n_respected()** (1 connections) — `tests/test_brain_scale.py`
- **.test_reranker_loads()** (1 connections) — `tests/test_brain_scale.py`

## Relationships

- [semantic_recall](semantic_recall.md) (3 shared connections)
- [_rand_unit](_rand_unit.md) (2 shared connections)
- [embedder.py](embedder.py.md) (1 shared connections)

## Source Files

- `app/second_brain/reranker.py`
- `tests/test_brain_scale.py`

## Audit Trail

- EXTRACTED: 31 (97%)
- INFERRED: 1 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*