# vigil.py

> 15 nodes · cohesion 0.15

## Key Concepts

- **vigil.py** (9 connections) — `app/api/vigil.py`
- **audit_request()** (8 connections) — `app/agents/vigil_agent.py`
- **get_receipt()** (5 connections) — `app/agents/vigil_agent.py`
- **run_vigil_scan()** (5 connections) — `app/api/vigil.py`
- **get_vigil_receipt()** (4 connections) — `app/api/vigil.py`
- **VigilScanRequest** (3 connections) — `app/api/vigil.py`
- **Any** (2 connections)
- **Retrieve a compiled compliance receipt by request ID.** (1 connections) — `app/agents/vigil_agent.py`
- **Audit a query or prompt for bias, prohibited targeting, and BNSS compliance.** (1 connections) — `app/agents/vigil_agent.py`
- **BaseModel** (1 connections)
- **get** (1 connections)
- **post** (1 connections)
- **Antar — Vigil API (A5: Bias & Compliance Auditor · Phase 1)…** (1 connections) — `app/api/vigil.py`
- **Audit a query/prompt for prohibited targeting, PII over-collection, and BNSS…** (1 connections) — `app/api/vigil.py`
- **Retrieve an existing compliance receipt from the Product Store.** (1 connections) — `app/api/vigil.py`

## Relationships

- [typing](typing.md) (4 shared connections)
- [hitl.py](hitl.py.md) (2 shared connections)
- [audit_store.py](audit_store.py.md) (1 shared connections)
- [get_product](get_product.md) (1 shared connections)
- [app_services](app_services.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [pydantic](pydantic.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)

## Source Files

- `app/agents/vigil_agent.py`
- `app/api/vigil.py`

## Audit Trail

- EXTRACTED: 28 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*