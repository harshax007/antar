# test_chat_api.py

> 23 nodes · cohesion 0.15

## Key Concepts

- **test_chat_api.py** (18 connections) — `tests/test_chat_api.py`
- **demo_mode.py** (17 connections) — `app/core/demo_mode.py`
- **scripted_query_result()** (8 connections) — `app/core/demo_mode.py`
- **post()** (8 connections) — `tests/test_chat_api.py`
- **clear_demo_cache()** (5 connections) — `app/core/demo_mode.py`
- **test_demo_mode_uses_scripted_cache()** (4 connections) — `tests/test_chat_api.py`
- **cache_info()** (3 connections) — `app/core/demo_mode.py`
- **_load_question_bank()** (3 connections) — `app/core/demo_mode.py`
- **_normalize()** (3 connections) — `app/core/demo_mode.py`
- **test_demo_mode_miss_falls_back_to_offline()** (3 connections) — `tests/test_chat_api.py`
- **DemoScript** (2 connections) — `app/core/demo_mode.py`
- **copy** (2 connections)
- **test_chat_detects_kannada()** (2 connections) — `tests/test_chat_api.py`
- **test_chat_hotspot_query_routes_t11()** (2 connections) — `tests/test_chat_api.py`
- **test_chat_returns_contract_shape()** (2 connections) — `tests/test_chat_api.py`
- **test_chat_suspect_lookup_yellappa()** (2 connections) — `tests/test_chat_api.py`
- **test_chat_trend_query_routes_t3()** (2 connections) — `tests/test_chat_api.py`
- **Any** (1 connections)
- **Deterministic DEMO_MODE response cache. This is not a second query engine.…** (1 connections) — `app/core/demo_mode.py`
- **Test helper and operational escape hatch.** (1 connections) — `app/core/demo_mode.py`
- **Return a cached scripted result for known demo lines, otherwise None.** (1 connections) — `app/core/demo_mode.py`
- **/api/chat HTTP contract test — mounts the chat router in isolation (no main.py…** (1 connections) — `tests/test_chat_api.py`
- **test_chat_session_id_assigned_and_stable()** (1 connections) — `tests/test_chat_api.py`

## Relationships

- [heuristic_select](heuristic_select.md) (3 shared connections)
- [query_agent.py](query_agent.py.md) (3 shared connections)
- [chat.py](chat.py.md) (3 shared connections)
- [re](re.md) (1 shared connections)
- [manifest.py](manifest.py.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [sessions.py](sessions.py.md) (1 shared connections)
- [audit_store.py](audit_store.py.md) (1 shared connections)
- [app_api](app_api.md) (1 shared connections)
- [settings.py](settings.py.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [fastapi_testclient](fastapi_testclient.md) (1 shared connections)

## Source Files

- `app/core/demo_mode.py`
- `tests/test_chat_api.py`

## Audit Trail

- EXTRACTED: 54 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*