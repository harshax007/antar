# run_agentic_spine

> 35 nodes · cohesion 0.08

## Key Concepts

- **run_agentic_spine()** (18 connections) — `app/agents/agentic_spine.py`
- **get_officer_memory()** (16 connections) — `app/core/memory.py`
- **context_stack.py** (12 connections) — `app/core/context_stack.py`
- **ContextFrame** (9 connections) — `app/core/context_stack.py`
- **ContextEngineer** (8 connections) — `app/core/context_stack.py`
- **.write()** (8 connections) — `app/core/context_stack.py`
- **get_mode_spec()** (7 connections) — `app/agents/agent_modes.py`
- **agent_modes.py** (6 connections) — `app/agents/agent_modes.py`
- **detect_mode_from_query()** (6 connections) — `app/agents/agent_modes.py`
- **.compress()** (5 connections) — `app/core/context_stack.py`
- **.isolate()** (5 connections) — `app/core/context_stack.py`
- **.select()** (4 connections) — `app/core/context_stack.py`
- **ModeSpec** (3 connections) — `app/agents/agent_modes.py`
- **test_answer_text_is_ascii_safe_for_export()** (3 connections) — `tests/test_research_node.py`
- **test_challenged_hypotheses_are_marked_in_the_answer()** (3 connections) — `tests/test_research_node.py`
- **.to_prompt_string()** (2 connections) — `app/core/context_stack.py`
- **estimate_tokens()** (2 connections) — `app/core/context_stack.py`
- **test_research_runs_end_to_end_in_a_chat_turn()** (2 connections) — `tests/test_research_node.py`
- **TypedDict** (1 connections)
- **Antar — First-Class Agent Modes (Think · Connect · Anticipate)…** (1 connections) — `app/agents/agent_modes.py`
- **Retrieve the ModeSpec for a given mode name, defaulting to general.** (1 connections) — `app/agents/agent_modes.py`
- **Determine appropriate operational mode from slash commands or natural language…** (1 connections) — `app/agents/agent_modes.py`
- **Any** (1 connections)
- **Any** (1 connections)
- **Antar — Context Engineering Stack (Write · Select · Compress · Isolate)…** (1 connections) — `app/core/context_stack.py`
- *... and 10 more nodes in this community*

## Relationships

- [chat_stream.py](chat_stream.py.md) (8 shared connections)
- [session_api.py](session_api.py.md) (7 shared connections)
- [test_research_node.py](test_research_node.py.md) (4 shared connections)
- [workspace.py](workspace.py.md) (3 shared connections)
- [typing](typing.md) (2 shared connections)
- [sessions.py](sessions.py.md) (2 shared connections)
- [_collect](_collect.md) (2 shared connections)
- [SSEQueue](SSEQueue.md) (2 shared connections)
- [auth_middleware.py](auth_middleware.py.md) (2 shared connections)
- [query_agent.py](query_agent.py.md) (1 shared connections)
- [parse_slash_command](parse_slash_command.md) (1 shared connections)
- [manifest.py](manifest.py.md) (1 shared connections)

## Source Files

- `app/agents/agent_modes.py`
- `app/agents/agentic_spine.py`
- `app/core/context_stack.py`
- `app/core/memory.py`
- `tests/test_research_node.py`

## Audit Trail

- EXTRACTED: 83 (97%)
- INFERRED: 3 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*