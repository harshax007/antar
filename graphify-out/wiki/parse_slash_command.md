# parse_slash_command

> 11 nodes · cohesion 0.29

## Key Concepts

- **parse_slash_command()** (14 connections) — `app/agents/heuristics.py`
- **TestParse** (9 connections) — `tests/test_slash_commands.py`
- **.test_anticipate_with_colon()** (2 connections) — `tests/test_slash_commands.py`
- **.test_bare_command_returns_empty_rest()** (2 connections) — `tests/test_slash_commands.py`
- **.test_connect_case_insensitive()** (2 connections) — `tests/test_slash_commands.py`
- **.test_plain_text_is_not_a_command()** (2 connections) — `tests/test_slash_commands.py`
- **.test_slash_mid_text_is_not_a_command()** (2 connections) — `tests/test_slash_commands.py`
- **.test_think()** (2 connections) — `tests/test_slash_commands.py`
- **.test_unknown_command_passes_through()** (2 connections) — `tests/test_slash_commands.py`
- **Parse a leading /think, /connect or /anticipate command. Returns (command,…** (1 connections) — `app/agents/heuristics.py`
- **.test_registry_shape()** (1 connections) — `tests/test_slash_commands.py`

## Relationships

- [chat_stream.py](chat_stream.py.md) (2 shared connections)
- [SSEQueue](SSEQueue.md) (2 shared connections)
- [run_agentic_spine](run_agentic_spine.md) (1 shared connections)
- [_run_pipeline](_run_pipeline.md) (1 shared connections)
- [heuristic_select](heuristic_select.md) (1 shared connections)

## Source Files

- `app/agents/heuristics.py`
- `tests/test_slash_commands.py`

## Audit Trail

- EXTRACTED: 23 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*