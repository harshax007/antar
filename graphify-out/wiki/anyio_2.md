# anyio

> 20 nodes · cohesion 0.14

## Key Concepts

- **anyio** (9 connections)
- **TestRunAgent** (7 connections) — `tests/test_orchestrator.py`
- **.test_cooldown_closes_circuit()** (6 connections) — `tests/test_orchestrator.py`
- **.test_opens_after_threshold_and_fails_fast()** (5 connections) — `tests/test_orchestrator.py`
- **TestCircuitBreaker** (4 connections) — `tests/test_orchestrator.py`
- **.test_failure_reason_is_surfaced()** (4 connections) — `tests/test_orchestrator.py`
- **.test_retry_recovers_from_transient_failure()** (4 connections) — `tests/test_orchestrator.py`
- **.test_success_returns_result_and_telemetry()** (4 connections) — `tests/test_orchestrator.py`
- **.test_timeout_degrades_honestly()** (4 connections) — `tests/test_orchestrator.py`
- **.test_unregistered_agent_autoregisters()** (4 connections) — `tests/test_orchestrator.py`
- **boom()** (3 connections) — `tests/test_orchestrator.py`
- **TestOpsEndpoint** (2 connections) — `tests/test_orchestrator.py`
- **.test_status_endpoint()** (2 connections) — `tests/test_orchestrator.py`
- **work()** (2 connections) — `tests/test_orchestrator.py`
- **boom()** (1 connections) — `tests/test_orchestrator.py`
- **fine()** (1 connections) — `tests/test_orchestrator.py`
- **boom()** (1 connections) — `tests/test_orchestrator.py`
- **flaky()** (1 connections) — `tests/test_orchestrator.py`
- **slow()** (1 connections) — `tests/test_orchestrator.py`
- **work()** (1 connections) — `tests/test_orchestrator.py`

## Relationships

- [orchestrator.py](orchestrator.py.md) (8 shared connections)
- [SSEQueue](SSEQueue.md) (4 shared connections)

## Source Files

- `tests/test_orchestrator.py`

## Audit Trail

- EXTRACTED: 29 (74%)
- INFERRED: 10 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*