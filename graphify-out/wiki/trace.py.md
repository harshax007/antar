# trace.py

> 21 nodes · cohesion 0.15

## Key Concepts

- **trace.py** (24 connections) — `app/obs/trace.py`
- **reasoning_logger.py** (9 connections) — `app/core/reasoning_logger.py`
- **log_step()** (9 connections) — `app/core/reasoning_logger.py`
- **current()** (7 connections) — `app/obs/trace.py`
- **add_span()** (6 connections) — `app/obs/trace.py`
- **_on()** (6 connections) — `app/obs/trace.py`
- **record_llm()** (6 connections) — `app/obs/trace.py`
- **structlog** (6 connections)
- **set_context()** (5 connections) — `app/obs/trace.py`
- **start()** (5 connections) — `app/obs/trace.py`
- **_obs_mw()** (5 connections) — `main.py`
- **broadcast_reasoning_step()** (4 connections) — `app/api/live_stream.py`
- **_Trace** (3 connections) — `app/obs/trace.py`
- **_audit()** (3 connections) — `main.py`
- **.__init__()** (2 connections) — `app/obs/trace.py`
- **middleware** (2 connections)
- **get_reasoning_log()** (1 connections) — `app/core/reasoning_logger.py`
- **Called by the log_step sink (V4). One JSONL line per span.** (1 connections) — `app/obs/trace.py`
- **Called from the quickml hook (§5.3). Accumulates onto the current trace.** (1 connections) — `app/obs/trace.py`
- **Called from the trace-close hook (§5.2) with retrieval facts.** (1 connections) — `app/obs/trace.py`
- **contextvars** (1 connections)

## Relationships

- [flags.py](flags.py.md) (6 shared connections)
- [typing](typing.md) (4 shared connections)
- [chat_stream.py](chat_stream.py.md) (4 shared connections)
- [redact_pii](redact_pii.md) (4 shared connections)
- [query_agent.py](query_agent.py.md) (3 shared connections)
- [obs/store.py](obs-store.py.md) (3 shared connections)
- [main.py](main.py.md) (3 shared connections)
- [sessions.py](sessions.py.md) (3 shared connections)
- [live_stream.py](live_stream.py.md) (2 shared connections)
- [time](time.md) (2 shared connections)
- [settings.py](settings.py.md) (2 shared connections)
- [quickml.py](quickml.py.md) (2 shared connections)

## Source Files

- `app/api/live_stream.py`
- `app/core/reasoning_logger.py`
- `app/obs/trace.py`
- `main.py`

## Audit Trail

- EXTRACTED: 75 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*