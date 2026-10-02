# fastapi_testclient

> 11 nodes · cohesion 0.18

## Key Concepts

- **fastapi_testclient** (12 connections)
- **test_governance.py** (9 connections) — `tests/test_governance.py`
- **benchmark_llm.py** (7 connections) — `scripts/benchmark_llm.py`
- **test_constable_blocked_from_audit_admin_ok()** (2 connections) — `tests/test_governance.py`
- **test_export_and_report_render()** (2 connections) — `tests/test_governance.py`
- **test_inspector_default_allows_graph_constable_blocked()** (2 connections) — `tests/test_governance.py`
- **run_benchmarks()** (1 connections) — `scripts/benchmark_llm.py`
- **Governance (P6 · F7 RBAC + audit, F6 report/export) — via the HTTP layer…** (1 connections) — `tests/test_governance.py`
- **The live demo beat: Constable → 403 on /api/audit; Admin → 200.** (1 connections) — `tests/test_governance.py`
- **Inspector+ guard on /api/graph: default (no header) = Inspector → ok; Constable…** (1 connections) — `tests/test_governance.py`
- **F6: export returns a report URL and the report HTML renders.** (1 connections) — `tests/test_governance.py`

## Relationships

- [main.py](main.py.md) (3 shared connections)
- [sessions.py](sessions.py.md) (2 shared connections)
- [test_chat_api.py](test_chat_api.py.md) (1 shared connections)
- [test_hitl.py](test_hitl.py.md) (1 shared connections)
- [test_layer6_geospatial.py](test_layer6_geospatial.py.md) (1 shared connections)
- [live_stream.py](live_stream.py.md) (1 shared connections)
- [build_network](build_network.md) (1 shared connections)
- [app_api](app_api.md) (1 shared connections)
- [map_and_ingest_csv](map_and_ingest_csv.md) (1 shared connections)
- [jobs.py](jobs.py.md) (1 shared connections)
- [time](time.md) (1 shared connections)
- [embedder.py](embedder.py.md) (1 shared connections)

## Source Files

- `scripts/benchmark_llm.py`
- `tests/test_governance.py`

## Audit Trail

- EXTRACTED: 29 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*