# test_self_heal.py

> 47 nodes · cohesion 0.08

## Key Concepts

- **test_self_heal.py** (32 connections) — `tests/test_self_heal.py`
- **self_heal.py** (25 connections) — `app/agents/self_heal.py`
- **parse_intent()** (18 connections) — `app/agents/intent_parser.py`
- **self_heal()** (18 connections) — `app/agents/self_heal.py`
- **sql_miner.py** (16 connections) — `app/services/sql_miner.py`
- **build_sql()** (8 connections) — `app/services/sql_miner.py`
- **extract_citations()** (7 connections) — `app/agents/query_agent.py`
- **mine()** (7 connections) — `app/services/sql_miner.py`
- **mine_until_hit()** (7 connections) — `app/services/sql_miner.py`
- **resolve_period()** (7 connections) — `app/services/zcql_repo.py`
- **_run()** (7 connections) — `tests/test_self_heal.py`
- **intent_to_template()** (6 connections) — `app/agents/self_heal.py`
- **_semantic_rows()** (6 connections) — `app/agents/self_heal.py`
- **test_miner_no_unconstrained_dump()** (5 connections) — `tests/test_self_heal.py`
- **_cites()** (3 connections) — `app/agents/self_heal.py`
- **_dead_end_message()** (3 connections) — `app/agents/self_heal.py`
- **_fetch_by_ids()** (3 connections) — `app/agents/self_heal.py`
- **_run_template_safe()** (3 connections) — `app/agents/self_heal.py`
- **_period_range()** (3 connections) — `app/services/sql_miner.py`
- **test_intent_suspect_id_routes_to_t9()** (3 connections) — `tests/test_self_heal.py`
- **test_intent_unsolved_does_not_include_solved()** (3 connections) — `tests/test_self_heal.py`
- **test_miner_finds_unsolved_burglary()** (3 connections) — `tests/test_self_heal.py`
- **SelfHealResult** (2 connections) — `app/agents/self_heal.py`
- **test_dead_end_is_honest_not_dump()** (2 connections) — `tests/test_self_heal.py`
- **test_direct_hit_does_not_self_heal()** (2 connections) — `tests/test_self_heal.py`
- *... and 22 more nodes in this community*

## Relationships

- [intent_parser.py](intent_parser.py.md) (19 shared connections)
- [query_agent.py](query_agent.py.md) (11 shared connections)
- [re](re.md) (6 shared connections)
- [zcql_local.py](zcql_local.py.md) (6 shared connections)
- [time](time.md) (4 shared connections)
- [zcql_repo.py](zcql_repo.py.md) (4 shared connections)
- [test_templates_t19_t23.py](test_templates_t19_t23.py.md) (3 shared connections)
- [heuristic_select](heuristic_select.md) (3 shared connections)
- [semantic_recall](semantic_recall.md) (2 shared connections)
- [typing](typing.md) (2 shared connections)
- [parse_json_response](parse_json_response.md) (1 shared connections)
- [manifest.py](manifest.py.md) (1 shared connections)

## Source Files

- `app/agents/intent_parser.py`
- `app/agents/query_agent.py`
- `app/agents/self_heal.py`
- `app/services/sql_miner.py`
- `app/services/zcql_repo.py`
- `tests/test_self_heal.py`

## Audit Trail

- EXTRACTED: 139 (96%)
- INFERRED: 6 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*