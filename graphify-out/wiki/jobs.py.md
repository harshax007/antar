# jobs.py

> 31 nodes · cohesion 0.10

## Key Concepts

- **jobs.py** (31 connections) — `app/api/jobs.py`
- **alert_suggest_agent_run()** (14 connections) — `app/agents/alert_suggest_agent.py`
- **pattern_agent_run()** (11 connections) — `app/agents/pattern_agent.py`
- **test_workspace_jobs.py** (11 connections) — `tests/test_workspace_jobs.py`
- **_work()** (10 connections) — `app/api/jobs.py`
- **osint_agent_run()** (9 connections) — `app/agents/osint_agent.py`
- **_run_job()** (8 connections) — `app/api/jobs.py`
- **get_unnotified_completed_jobs()** (7 connections) — `app/api/jobs.py`
- **create_job()** (6 connections) — `app/api/jobs.py`
- **test_alert_suggest.py** (5 connections) — `tests/test_alert_suggest.py`
- **JobRequest** (4 connections) — `app/api/jobs.py`
- **test_alert_suggest_agent_run()** (3 connections) — `tests/test_alert_suggest.py`
- **cancel_job()** (2 connections) — `app/api/jobs.py`
- **get_job()** (2 connections) — `app/api/jobs.py`
- **list_jobs()** (2 connections) — `app/api/jobs.py`
- **_prune()** (2 connections) — `app/api/jobs.py`
- **get** (2 connections)
- **test_job_creation_and_option_b_notification()** (2 connections) — `tests/test_workspace_jobs.py`
- **Called when user intent is related to alerts, deployment, or suggestions.** (1 connections) — `app/agents/alert_suggest_agent.py`
- **Called by the agentic spine to pull open web intelligence.** (1 connections) — `app/agents/osint_agent.py`
- **Called by the agentic spine when intent is 'pattern'.** (1 connections) — `app/agents/pattern_agent.py`
- **BaseModel** (1 connections)
- **post** (1 connections)
- **Antar — Long-Task Jobs (admin Expert Workspace)…** (1 connections) — `app/api/jobs.py`
- **Retrieve recently completed background jobs that haven't been shown to the user…** (1 connections) — `app/api/jobs.py`
- *... and 6 more nodes in this community*

## Relationships

- [chat_stream.py](chat_stream.py.md) (8 shared connections)
- [_run_pipeline](_run_pipeline.md) (6 shared connections)
- [typing](typing.md) (4 shared connections)
- [pydantic](pydantic.md) (4 shared connections)
- [alert_suggest_agent.py](alert_suggest_agent.py.md) (3 shared connections)
- [query_agent.py](query_agent.py.md) (3 shared connections)
- [workspace.py](workspace.py.md) (3 shared connections)
- [run_multi_module_recon](run_multi_module_recon.md) (2 shared connections)
- [zcql_local.py](zcql_local.py.md) (2 shared connections)
- [build_network](build_network.md) (2 shared connections)
- [corridor_agent.py](corridor_agent.py.md) (2 shared connections)
- [gi_star_surface](gi_star_surface.md) (2 shared connections)

## Source Files

- `app/agents/alert_suggest_agent.py`
- `app/agents/osint_agent.py`
- `app/agents/pattern_agent.py`
- `app/api/jobs.py`
- `tests/test_alert_suggest.py`
- `tests/test_workspace_jobs.py`

## Audit Trail

- EXTRACTED: 92 (93%)
- INFERRED: 7 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*