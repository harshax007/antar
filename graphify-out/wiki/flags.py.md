# flags.py

> 24 nodes · cohesion 0.13

## Key Concepts

- **flags.py** (16 connections) — `app/obs/flags.py`
- **close()** (15 connections) — `app/obs/trace.py`
- **metrics.py** (13 connections) — `app/obs/metrics.py`
- **evaluate()** (7 connections) — `app/obs/flags.py`
- **from_query_result()** (5 connections) — `app/obs/flags.py`
- **_upsert()** (5 connections) — `app/obs/store.py`
- **is_conversational()** (4 connections) — `app/obs/config.py`
- **persist()** (4 connections) — `app/obs/flags.py`
- **update_baseline()** (4 connections) — `app/obs/metrics.py`
- **_f()** (3 connections) — `app/obs/flags.py`
- **baseline_for()** (3 connections) — `app/obs/metrics.py`
- **parse_usage()** (3 connections) — `app/obs/metrics.py`
- **upsert_context()** (3 connections) — `app/obs/store.py`
- **upsert_trace()** (3 connections) — `app/obs/store.py`
- **_asserts_number_or_id()** (2 connections) — `app/obs/flags.py`
- **_says_no_records()** (2 connections) — `app/obs/flags.py`
- **cost_micros()** (2 connections) — `app/obs/metrics.py`
- **in_sample()** (2 connections) — `app/obs/metrics.py`
- **True when a trace represents a user turn rather than a raw HTTP request.** (1 connections) — `app/obs/config.py`
- **Called from the close hook with the query_agent result to capture V5 signals…** (1 connections) — `app/obs/flags.py`
- **QuickML usage block (V2). Handle both {'usage':{...}} shapes; default 0,0.** (1 connections) — `app/obs/metrics.py`
- **EWMA-ish rolling p95 per (surface,model). Cheap approximation, no full history.** (1 connections) — `app/obs/metrics.py`
- **INSERT … ON CONFLICT(trace_id) upsert. When `trace_id` is the ONLY column there…** (1 connections) — `app/obs/store.py`
- **Finalize: persist trace + context, run FREE flags, mark judge-pending. Fail-…** (1 connections) — `app/obs/trace.py`

## Relationships

- [settings.py](settings.py.md) (9 shared connections)
- [obs/store.py](obs-store.py.md) (7 shared connections)
- [trace.py](trace.py.md) (6 shared connections)
- [time](time.md) (2 shared connections)
- [sessions.py](sessions.py.md) (2 shared connections)
- [quickml.py](quickml.py.md) (2 shared connections)
- [SSEQueue](SSEQueue.md) (1 shared connections)
- [chat.py](chat.py.md) (1 shared connections)
- [build_world](build_world.md) (1 shared connections)
- [redact_pii](redact_pii.md) (1 shared connections)

## Source Files

- `app/obs/config.py`
- `app/obs/flags.py`
- `app/obs/metrics.py`
- `app/obs/store.py`
- `app/obs/trace.py`

## Audit Trail

- EXTRACTED: 67 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*