# test_hitl.py

> 39 nodes · cohesion 0.11

## Key Concepts

- **test_hitl.py** (41 connections) — `tests/test_hitl.py`
- **_propose()** (20 connections) — `tests/test_hitl.py`
- **_approve()** (11 connections) — `tests/test_hitl.py`
- **list_watches()** (8 connections) — `app/agents/sentinel_agent.py`
- **_events()** (7 connections) — `tests/test_hitl.py`
- **test_every_step_is_on_a_verifiable_chain_that_survives_reload()** (6 connections) — `tests/test_hitl.py`
- **test_tampered_stored_payload_cannot_be_approved()** (6 connections) — `tests/test_hitl.py`
- **register_watch()** (5 connections) — `app/agents/sentinel_agent.py`
- **test_approval_executes_the_watch()** (5 connections) — `tests/test_hitl.py`
- **test_expired_proposal_cannot_be_approved()** (5 connections) — `tests/test_hitl.py`
- **test_failed_execution_is_recorded_not_hidden()** (5 connections) — `tests/test_hitl.py`
- **test_rejection_is_recorded_and_executes_nothing()** (5 connections) — `tests/test_hitl.py`
- **test_sentinel_watch_endpoint_now_requires_approval()** (5 connections) — `tests/test_hitl.py`
- **test_stats_and_filters()** (5 connections) — `tests/test_hitl.py`
- **active_deployments()** (4 connections) — `app/core/hitl.py`
- **test_approval_issues_a_patrol_order()** (4 connections) — `tests/test_hitl.py`
- **test_decisions_are_final()** (4 connections) — `tests/test_hitl.py`
- **test_non_approver_roles_cannot_decide()** (4 connections) — `tests/test_hitl.py`
- **test_proposal_is_parked_not_executed()** (4 connections) — `tests/test_hitl.py`
- **test_stale_review_hash_is_refused()** (4 connections) — `tests/test_hitl.py`
- **Any** (3 connections)
- **_client()** (3 connections) — `tests/test_hitl.py`
- **_h()** (3 connections) — `tests/test_hitl.py`
- **parametrize** (3 connections)
- **test_decision_reason_is_required()** (3 connections) — `tests/test_hitl.py`
- *... and 14 more nodes in this community*

## Relationships

- [hitl.py](hitl.py.md) (22 shared connections)
- [typing](typing.md) (4 shared connections)
- [time](time.md) (3 shared connections)
- [app_services](app_services.md) (2 shared connections)
- [test_audit_chain_persistence.py](test_audit_chain_persistence.py.md) (2 shared connections)
- [evidence_ledger.py](evidence_ledger.py.md) (1 shared connections)
- [hitl_api.py](hitl_api.py.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [fastapi_testclient](fastapi_testclient.md) (1 shared connections)
- [chat_stream.py](chat_stream.py.md) (1 shared connections)
- [audit_store.py](audit_store.py.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)

## Source Files

- `app/agents/sentinel_agent.py`
- `app/core/hitl.py`
- `tests/test_hitl.py`

## Audit Trail

- EXTRACTED: 118 (98%)
- INFERRED: 2 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*