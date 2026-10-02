# test_agents_manifest.py

> 39 nodes · cohesion 0.06

## Key Concepts

- **test_agents_manifest.py** (30 connections) — `tests/test_agents_manifest.py`
- **_compiled_nodes()** (7 connections) — `tests/test_agents_manifest.py`
- **build_graph()** (6 connections) — `app/agents/state.py`
- **test_heuristic_router_emits_only_declared_labels()** (3 connections) — `tests/test_agents_manifest.py`
- **test_no_route_resolves_to_a_nonexistent_node()** (3 connections) — `tests/test_agents_manifest.py`
- **test_previously_dropped_labels_now_route()** (3 connections) — `tests/test_agents_manifest.py`
- **test_route_fn_still_routes_the_core_vocabulary()** (3 connections) — `tests/test_agents_manifest.py`
- **test_entry_node_is_never_dispatchable()** (2 connections) — `tests/test_agents_manifest.py`
- **test_every_agent_declares_a_real_module()** (2 connections) — `tests/test_agents_manifest.py`
- **test_every_graph_node_is_claimed_by_an_agent()** (2 connections) — `tests/test_agents_manifest.py`
- **test_fallback_fleet_does_not_name_undeclared_agents()** (2 connections) — `tests/test_agents_manifest.py`
- **test_fallback_graph_nodes_match_manifest()** (2 connections) — `tests/test_agents_manifest.py`
- **test_generated_route_map_covers_the_fallback()** (2 connections) — `tests/test_agents_manifest.py`
- **test_hitl_agents_are_explicit()** (2 connections) — `tests/test_agents_manifest.py`
- **test_manifest_topology_matches_compiled_graph()** (2 connections) — `tests/test_agents_manifest.py`
- **test_mode_primary_agents_are_all_declared()** (2 connections) — `tests/test_agents_manifest.py`
- **test_orchestrator_fleet_matches_manifest()** (2 connections) — `tests/test_agents_manifest.py`
- **test_supervisor_prompt_labels_are_declared()** (2 connections) — `tests/test_agents_manifest.py`
- **test_unreachable_agents_are_declared_as_such()** (2 connections) — `tests/test_agents_manifest.py`
- **Any** (1 connections)
- **Builds and compiles the LangGraph StateGraph. Called once at startup; result…** (1 connections) — `app/agents/state.py`
- **_noop()** (1 connections) — `tests/test_agents_manifest.py`
- **Antar — AGENTS.md drift tests ============================= These are the teeth…** (1 connections) — `tests/test_agents_manifest.py`
- **agent_modes injects primary_agents into the route list for /think /connect…** (1 connections) — `tests/test_agents_manifest.py`
- **The LLM supervisor is told it may emit these; all of them must route somewhere.** (1 connections) — `tests/test_agents_manifest.py`
- *... and 14 more nodes in this community*

## Relationships

- [chat_stream.py](chat_stream.py.md) (3 shared connections)
- [test_research_node.py](test_research_node.py.md) (3 shared connections)
- [manifest.py](manifest.py.md) (3 shared connections)
- [state.py](state.py.md) (2 shared connections)
- [orchestrator.py](orchestrator.py.md) (2 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [app_services](app_services.md) (1 shared connections)

## Source Files

- `app/agents/state.py`
- `tests/test_agents_manifest.py`

## Audit Trail

- EXTRACTED: 57 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*