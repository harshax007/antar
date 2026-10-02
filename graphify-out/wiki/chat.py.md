# chat.py

> 14 nodes · cohesion 0.20

## Key Concepts

- **chat.py** (32 connections) — `app/api/chat.py`
- **chat_diag.py** (13 connections) — `scripts/chat_diag.py`
- **compose_answer()** (12 connections) — `app/agents/query_agent.py`
- **select_template()** (10 connections) — `app/agents/query_agent.py`
- **main()** (6 connections) — `scripts/chat_diag.py`
- **_answer()** (5 connections) — `app/agents/query_agent.py`
- **_llm_available()** (4 connections) — `app/api/chat.py`
- **_hybrid_select()** (4 connections) — `app/api/chat_stream.py`
- **LLM** (3 connections)
- **LLM picks {template_id, params}. Returns parsed dict (may be…** (1 connections) — `app/agents/query_agent.py`
- **Deterministic answer: direct answer first (answer_writer), legacy formatter as…** (1 connections) — `app/agents/query_agent.py`
- **Write the NL answer from rows. Returns (text, used_llm, violations). Falls back…** (1 connections) — `app/agents/query_agent.py`
- **Antar — Chat API (POST /api/chat) Returns the Strategy §3.8 response shape.…** (1 connections) — `app/api/chat.py`
- **Diagnose the live LLM chat path — shows the routing decision (template +…** (1 connections) — `scripts/chat_diag.py`

## Relationships

- [query_agent.py](query_agent.py.md) (8 shared connections)
- [sessions.py](sessions.py.md) (7 shared connections)
- [heuristic_select](heuristic_select.md) (5 shared connections)
- [_run_pipeline](_run_pipeline.md) (4 shared connections)
- [chat_stream.py](chat_stream.py.md) (4 shared connections)
- [quickml.py](quickml.py.md) (4 shared connections)
- [test_templates_t19_t23.py](test_templates_t19_t23.py.md) (3 shared connections)
- [test_chat_api.py](test_chat_api.py.md) (3 shared connections)
- [build_layout](build_layout.md) (2 shared connections)
- [pydantic](pydantic.md) (2 shared connections)
- [map_and_ingest_csv](map_and_ingest_csv.md) (2 shared connections)
- [settings.py](settings.py.md) (2 shared connections)

## Source Files

- `app/agents/query_agent.py`
- `app/api/chat.py`
- `app/api/chat_stream.py`
- `scripts/chat_diag.py`

## Audit Trail

- EXTRACTED: 73 (96%)
- INFERRED: 3 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*