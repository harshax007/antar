# _run_pipeline()

> God node · 63 connections · `app/api/chat_stream.py`

**Community:** [_run_pipeline](_run_pipeline.md)

## Connections by Relation

### calls
- [query_agent_run()](query_agent_run.md) `EXTRACTED`
- heuristic_select() `EXTRACTED`
- semantic_recall() `EXTRACTED`
- build_layout() `EXTRACTED`
- write_answer() `EXTRACTED`
- is_kannada() `EXTRACTED`
- build_custody() `EXTRACTED`
- parse_slash_command() `EXTRACTED`
- geo_agent_run() `EXTRACTED`
- alert_suggest_agent_run() `EXTRACTED`
- format_agent_response() `EXTRACTED`
- _answer_confidence() `EXTRACTED`
- _L() `EXTRACTED`
- compose_answer() `EXTRACTED`
- pattern_agent_run() `EXTRACTED`
- record_ai_reasoning() `EXTRACTED`
- _collect() `EXTRACTED`
- token_stream() `EXTRACTED`
- _route() `EXTRACTED`
- select_template() `EXTRACTED`
- *…and 24 more `calls` connection(s) not listed (lowest-degree first to go)*

### contains
- [chat_stream.py](chat_stream.py.md) `EXTRACTED`
- _degraded() `EXTRACTED`
- run_profile_task() `EXTRACTED`
- run_network_task() `EXTRACTED`
- run_geo_task() `EXTRACTED`
- run_pattern_task() `EXTRACTED`
- run_predict_task() `EXTRACTED`
- run_alerts_task() `EXTRACTED`
- run_osint_task() `EXTRACTED`
- _keep() `EXTRACTED`

### imports
- test_orchestrator.py `EXTRACTED`
- test_chat_stream.py `EXTRACTED`
- test_slash_commands.py `EXTRACTED`
- test_layout_composer.py `EXTRACTED`

### indirect_call
- quickml_generate() `INFERRED`
- _hybrid_select() `INFERRED`

### rationale_for
- Full agentic pipeline that emits SSE events via *q* as it progresses. Mirrors… `EXTRACTED`

### references
- StreamChatRequest `EXTRACTED`

### uses
- [SSEQueue](SSEQueue.md) `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*