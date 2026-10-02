# quickml.py

> 37 nodes · cohesion 0.09

## Key Concepts

- **quickml.py** (43 connections) — `app/services/quickml.py`
- **quickml_generate()** (33 connections) — `app/services/quickml.py`
- **quickml_vision_generate()** (9 connections) — `app/services/quickml.py`
- **_get_client()** (8 connections) — `app/services/quickml.py`
- **quickml_generate_with_logprobs()** (8 connections) — `app/services/quickml.py`
- **_auth_headers()** (7 connections) — `app/services/quickml.py`
- **_get_access_token()** (7 connections) — `app/services/quickml.py`
- **quickml_ping.py** (7 connections) — `scripts/quickml_ping.py`
- **quickml_token_test.py** (7 connections) — `scripts/quickml_token_test.py`
- **_extract_text()** (6 connections) — `app/services/quickml.py`
- **_build_payload()** (5 connections) — `app/services/quickml.py`
- **_clean()** (4 connections) — `app/services/quickml.py`
- **_default_budget_s()** (3 connections) — `app/services/quickml.py`
- **_is_permanent_status()** (3 connections) — `app/services/quickml.py`
- **quickml_default_generate()** (3 connections) — `app/services/quickml.py`
- **_breaker_active()** (2 connections) — `app/services/quickml.py`
- **_resolve_model()** (2 connections) — `app/services/quickml.py`
- **_sleep()** (2 connections) — `app/services/quickml.py`
- **main()** (2 connections) — `scripts/quickml_ping.py`
- **main()** (2 connections) — `scripts/quickml_token_test.py`
- **AsyncClient** (1 connections)
- **Antar — QuickML LLM Serving Client OAuth-authenticated REST calls to Qwen 2.5…** (1 connections) — `app/services/quickml.py`
- **Build request headers per QUICKML_AUTH_MODE (oauth | apikey | none). Includes…** (1 connections) — `app/services/quickml.py`
- **Wall-clock ceiling for one LLM call, retries included.** (1 connections) — `app/services/quickml.py`
- **Call QuickML LLM Serving. Routes dynamically between models: - /ask & chat…** (1 connections) — `app/services/quickml.py`
- *... and 12 more nodes in this community*

## Relationships

- [settings.py](settings.py.md) (8 shared connections)
- [parse_json_response](parse_json_response.md) (7 shared connections)
- [redact_pii](redact_pii.md) (5 shared connections)
- [chat_stream.py](chat_stream.py.md) (4 shared connections)
- [chat.py](chat.py.md) (4 shared connections)
- [asyncio](asyncio.md) (3 shared connections)
- [query_agent.py](query_agent.py.md) (3 shared connections)
- [test_generate_retries_then_raises](test_generate_retries_then_raises.md) (3 shared connections)
- [pytest](pytest.md) (2 shared connections)
- [time](time.md) (2 shared connections)
- [flags.py](flags.py.md) (2 shared connections)
- [trace.py](trace.py.md) (2 shared connections)

## Source Files

- `app/services/quickml.py`
- `scripts/quickml_ping.py`
- `scripts/quickml_token_test.py`

## Audit Trail

- EXTRACTED: 115 (97%)
- INFERRED: 4 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*