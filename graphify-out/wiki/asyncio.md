# asyncio

> 23 nodes · cohesion 0.13

## Key Concepts

- **asyncio** (43 connections)
- **test_chat_stream.py** (19 connections) — `tests/test_chat_stream.py`
- **sse.py** (10 connections) — `app/core/sse.py`
- **token_stream()** (10 connections) — `app/core/sse.py`
- **sse_event()** (8 connections) — `app/core/sse.py`
- **TestTokenStream** (6 connections) — `tests/test_chat_stream.py`
- **TestSSEEvent** (4 connections) — `tests/test_chat_stream.py`
- **.emit()** (3 connections) — `app/core/sse.py`
- **.test_empty_string()** (3 connections) — `tests/test_chat_stream.py`
- **.test_kannada_text_preserved()** (3 connections) — `tests/test_chat_stream.py`
- **.test_one_chunk_per_word()** (3 connections) — `tests/test_chat_stream.py`
- **.test_reassembled_text_matches_original()** (3 connections) — `tests/test_chat_stream.py`
- **.test_single_word()** (3 connections) — `tests/test_chat_stream.py`
- **Any** (2 connections)
- **sse_heartbeat()** (2 connections) — `app/core/sse.py`
- **.test_format_starts_with_data()** (2 connections) — `tests/test_chat_stream.py`
- **.test_type_field_present()** (2 connections) — `tests/test_chat_stream.py`
- **.test_unicode_preserved()** (2 connections) — `tests/test_chat_stream.py`
- **Antar — SSE utilities =========================== Tiny helpers for Server-Sent…** (1 connections) — `app/core/sse.py`
- **Format one SSE message: ``data: {...}\\n\\n``.** (1 connections) — `app/core/sse.py`
- **Keep-alive comment line (invisible to the client).** (1 connections) — `app/core/sse.py`
- **Split *text* into word-level chunks and yield each with ultra-low latency. 2…** (1 connections) — `app/core/sse.py`
- **Tests for chat SSE streaming — /api/chat/stream. Tests cover: • SSEQueue: emit…** (1 connections) — `tests/test_chat_stream.py`

## Relationships

- [SSEQueue](SSEQueue.md) (15 shared connections)
- [chat_stream.py](chat_stream.py.md) (5 shared connections)
- [pytest](pytest.md) (5 shared connections)
- [query_agent.py](query_agent.py.md) (3 shared connections)
- [quickml.py](quickml.py.md) (3 shared connections)
- [typing](typing.md) (2 shared connections)
- [_run_pipeline](_run_pipeline.md) (2 shared connections)
- [semantic_recall](semantic_recall.md) (2 shared connections)
- [_answer_confidence](_answer_confidence.md) (2 shared connections)
- [zcql_local.py](zcql_local.py.md) (1 shared connections)
- [advocate_agent_api.py](advocate_agent_api.py.md) (1 shared connections)
- [hitl_api.py](hitl_api.py.md) (1 shared connections)

## Source Files

- `app/core/sse.py`
- `tests/test_chat_stream.py`

## Audit Trail

- EXTRACTED: 99 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*