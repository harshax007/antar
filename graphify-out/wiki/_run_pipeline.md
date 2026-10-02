# _run_pipeline

> 15 nodes · cohesion 0.28

## Key Concepts

- **_run_pipeline()** (63 connections) — `app/api/chat_stream.py`
- **_L()** (12 connections) — `app/api/chat_stream.py`
- **_degraded()** (9 connections) — `app/api/chat_stream.py`
- **is_explain_request()** (6 connections) — `app/agents/heuristics.py`
- **run_alerts_task()** (4 connections) — `app/api/chat_stream.py`
- **run_geo_task()** (4 connections) — `app/api/chat_stream.py`
- **run_network_task()** (4 connections) — `app/api/chat_stream.py`
- **run_osint_task()** (4 connections) — `app/api/chat_stream.py`
- **run_pattern_task()** (4 connections) — `app/api/chat_stream.py`
- **run_predict_task()** (4 connections) — `app/api/chat_stream.py`
- **run_profile_task()** (4 connections) — `app/api/chat_stream.py`
- **True if the user is asking us to justify the previous answer (Explain / M9).** (1 connections) — `app/agents/heuristics.py`
- **Full agentic pipeline that emits SSE events via *q* as it progresses. Mirrors…** (1 connections) — `app/api/chat_stream.py`
- **Pick the Kannada string when the (toggle-driven) lang is 'kn', else English.** (1 connections) — `app/api/chat_stream.py`
- **_keep()** (1 connections) — `app/api/chat_stream.py`

## Relationships

- [SSEQueue](SSEQueue.md) (15 shared connections)
- [chat_stream.py](chat_stream.py.md) (14 shared connections)
- [jobs.py](jobs.py.md) (6 shared connections)
- [sessions.py](sessions.py.md) (5 shared connections)
- [chat.py](chat.py.md) (4 shared connections)
- [heuristic_select](heuristic_select.md) (3 shared connections)
- [_answer_confidence](_answer_confidence.md) (2 shared connections)
- [asyncio](asyncio.md) (2 shared connections)
- [build_layout](build_layout.md) (2 shared connections)
- [chat_stream](chat_stream.md) (1 shared connections)
- [parse_slash_command](parse_slash_command.md) (1 shared connections)
- [query_agent.py](query_agent.py.md) (1 shared connections)

## Source Files

- `app/agents/heuristics.py`
- `app/api/chat_stream.py`

## Audit Trail

- EXTRACTED: 88 (95%)
- INFERRED: 5 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*