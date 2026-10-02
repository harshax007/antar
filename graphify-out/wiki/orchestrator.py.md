# orchestrator.py

> 24 nodes · cohesion 0.12

## Key Concepts

- **orchestrator.py** (28 connections) — `app/core/orchestrator.py`
- **AgentSpec** (13 connections) — `app/core/orchestrator.py`
- **register_default_fleet()** (8 connections) — `app/core/orchestrator.py`
- **run_agent()** (6 connections) — `app/core/orchestrator.py`
- **_autonomous_tick()** (5 connections) — `app/core/orchestrator.py`
- **register()** (5 connections) — `app/core/orchestrator.py`
- **reset()** (5 connections) — `app/core/orchestrator.py`
- **start_autonomous()** (5 connections) — `app/core/orchestrator.py`
- **_scan()** (4 connections) — `app/core/orchestrator.py`
- **_spec()** (4 connections) — `app/core/orchestrator.py`
- **_AgentState** (3 connections) — `app/core/orchestrator.py`
- **_autonomous_loop()** (3 connections) — `app/core/orchestrator.py`
- **client()** (3 connections) — `tests/test_jobs.py`
- **_clean_state()** (3 connections) — `tests/test_orchestrator.py`
- **Any** (1 connections)
- **Antar — Production Orchestrator ==================================== The…** (1 connections) — `app/core/orchestrator.py`
- **Run one agent call under orchestration. Returns (ok, result, meta). On failure…** (1 connections) — `app/core/orchestrator.py`
- **One tick: proactively refresh soon-to-expire products + Sentinel scan.** (1 connections) — `app/core/orchestrator.py`
- **Start the background loop (idempotent). Called from app lifespan.** (1 connections) — `app/core/orchestrator.py`
- **Test helper — clear all runtime state (registry survives).** (1 connections) — `app/core/orchestrator.py`
- **Register every agent declared in AGENTS.md (kind: worker | service). The…** (1 connections) — `app/core/orchestrator.py`
- **Task** (1 connections)
- **fixture** (1 connections)
- **fixture** (1 connections)

## Relationships

- [anyio](anyio.md) (8 shared connections)
- [manifest.py](manifest.py.md) (3 shared connections)
- [SSEQueue](SSEQueue.md) (3 shared connections)
- [evidence_ledger.py](evidence_ledger.py.md) (2 shared connections)
- [typing](typing.md) (2 shared connections)
- [jobs.py](jobs.py.md) (2 shared connections)
- [ops.py](ops.py.md) (2 shared connections)
- [test_agents_manifest.py](test_agents_manifest.py.md) (2 shared connections)
- [pytest](pytest.md) (2 shared connections)
- [anomaly.py](anomaly.py.md) (2 shared connections)
- [dataset.py](dataset.py.md) (2 shared connections)
- [asyncio](asyncio.md) (1 shared connections)

## Source Files

- `app/core/orchestrator.py`
- `tests/test_jobs.py`
- `tests/test_orchestrator.py`

## Audit Trail

- EXTRACTED: 64 (90%)
- INFERRED: 7 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*