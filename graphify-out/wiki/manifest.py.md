# manifest.py

> 24 nodes · cohesion 0.11

## Key Concepts

- **manifest.py** (24 connections) — `app/agents/manifest.py`
- **load()** (9 connections) — `app/agents/manifest.py`
- **reload()** (7 connections) — `app/agents/manifest.py`
- **dataclasses** (7 connections)
- **status()** (5 connections) — `app/agents/manifest.py`
- **test_unknown_label_is_counted_not_silently_coerced()** (5 connections) — `tests/test_agents_manifest.py`
- **_build_agent()** (4 connections) — `app/agents/manifest.py`
- **_parse()** (4 connections) — `app/agents/manifest.py`
- **test_manifest_declares_research_as_reachable()** (4 connections) — `tests/test_research_node.py`
- **_tuple()** (3 connections) — `app/agents/manifest.py`
- **unresolved_routes()** (3 connections) — `app/agents/manifest.py`
- **man()** (3 connections) — `tests/test_agents_manifest.py`
- **test_manifest_declares_this_agent()** (3 connections) — `tests/test_advocate_agent.py`
- **note_unresolved_route()** (2 connections) — `app/agents/manifest.py`
- **reset_unresolved()** (2 connections) — `app/agents/manifest.py`
- **Any** (1 connections)
- **Antar — Agent Manifest Loader ============================= Parses AGENTS.md…** (1 connections) — `app/agents/manifest.py`
- **Parse AGENTS.md once per process. Never raises.** (1 connections) — `app/agents/manifest.py`
- **Drop the cache and re-read (tests, and editing AGENTS.md during dev).** (1 connections) — `app/agents/manifest.py`
- **Manifest health for /api/orchestrator/status.** (1 connections) — `app/agents/manifest.py`
- **fixture** (1 connections)
- **The failure mode this whole manifest exists to prevent: silence.** (1 connections) — `tests/test_agents_manifest.py`
- **AGENTS.md is executable — a new agent that skips it is a build failure.** (1 connections) — `tests/test_advocate_agent.py`
- **AGENTS.md must no longer describe this agent as a GAP.** (1 connections) — `tests/test_research_node.py`

## Relationships

- [Manifest](Manifest.md) (6 shared connections)
- [test_research_node.py](test_research_node.py.md) (5 shared connections)
- [orchestrator.py](orchestrator.py.md) (3 shared connections)
- [test_agents_manifest.py](test_agents_manifest.py.md) (3 shared connections)
- [test_advocate_agent.py](test_advocate_agent.py.md) (2 shared connections)
- [re](re.md) (1 shared connections)
- [trace.py](trace.py.md) (1 shared connections)
- [SSEQueue](SSEQueue.md) (1 shared connections)
- [heuristic_select](heuristic_select.md) (1 shared connections)
- [obs/store.py](obs-store.py.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [chat_stream.py](chat_stream.py.md) (1 shared connections)

## Source Files

- `app/agents/manifest.py`
- `tests/test_agents_manifest.py`
- `tests/test_advocate_agent.py`
- `tests/test_research_node.py`

## Audit Trail

- EXTRACTED: 63 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*