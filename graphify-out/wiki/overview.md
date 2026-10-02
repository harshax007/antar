# overview

> 9 nodes · cohesion 0.28

## Key Concepts

- **overview()** (8 connections) — `app/api/dashboard.py`
- **test_dashboard.py** (6 connections) — `tests/test_dashboard.py`
- **test_overview_contract_and_totals()** (3 connections) — `tests/test_dashboard.py`
- **test_overview_resilient_to_empty()** (3 connections) — `tests/test_dashboard.py`
- **get** (1 connections)
- **Overview KPIs + summary panels for the dashboard landing (N1). Composed from…** (1 connections) — `app/api/dashboard.py`
- **Overview dashboard endpoint (N1) — composed from whitelisted templates, local…** (1 connections) — `tests/test_dashboard.py`
- **Happy: KPIs + panels present; status counts partition the total crime count.** (1 connections) — `tests/test_dashboard.py`
- **Failure-mode: if a template returns nothing, the contract still holds (zeros,…** (1 connections) — `tests/test_dashboard.py`

## Relationships

- [build_spec](build_spec.md) (3 shared connections)
- [app_services](app_services.md) (1 shared connections)
- [asyncio](asyncio.md) (1 shared connections)

## Source Files

- `app/api/dashboard.py`
- `tests/test_dashboard.py`

## Audit Trail

- EXTRACTED: 15 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*