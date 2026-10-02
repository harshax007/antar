# chat_stream

> 7 nodes · cohesion 0.29

## Key Concepts

- **chat_stream()** (9 connections) — `app/api/chat_stream.py`
- **run()** (2 connections) — `app/api/chat_stream.py`
- **generate()** (1 connections) — `app/api/chat_stream.py`
- **post** (1 connections)
- **Request** (1 connections)
- **POST /api/chat/stream — SSE streaming chat endpoint. Emits typed SSE events as…** (1 connections) — `app/api/chat_stream.py`
- **StreamingResponse** (1 connections)

## Relationships

- [SSEQueue](SSEQueue.md) (2 shared connections)
- [chat_stream.py](chat_stream.py.md) (1 shared connections)
- [_run_pipeline](_run_pipeline.md) (1 shared connections)

## Source Files

- `app/api/chat_stream.py`

## Audit Trail

- EXTRACTED: 9 (90%)
- INFERRED: 1 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*