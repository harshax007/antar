# auth_middleware.py

> 12 nodes · cohesion 0.18

## Key Concepts

- **auth_middleware.py** (12 connections) — `app/core/auth_middleware.py`
- **get_current_officer()** (4 connections) — `app/core/auth_middleware.py`
- **require_cron_secret()** (4 connections) — `app/core/auth_middleware.py`
- **require_role()** (4 connections) — `app/core/auth_middleware.py`
- **resolve_role()** (3 connections) — `app/core/auth_middleware.py`
- **_dep()** (2 connections) — `app/core/auth_middleware.py`
- **Any** (1 connections)
- **Antar — RBAC (F7 / M10) ============================ Role hierarchy + a…** (1 connections) — `app/core/auth_middleware.py`
- **Caller's role from the header (dev). Unknown/missing → Inspector.** (1 connections) — `app/core/auth_middleware.py`
- **Retrieve full officer profile and memory state for active session…** (1 connections) — `app/core/auth_middleware.py`
- **Dependency factory → 403 unless the caller's role rank >= `minimum`.** (1 connections) — `app/core/auth_middleware.py`
- **Dependency to secure cron-triggered endpoints. Returns True if valid.** (1 connections) — `app/core/auth_middleware.py`

## Relationships

- [run_agentic_spine](run_agentic_spine.md) (2 shared connections)
- [app_services](app_services.md) (2 shared connections)
- [second_brain/ingestion.py](second_brain-ingestion.py.md) (2 shared connections)
- [main.py](main.py.md) (2 shared connections)
- [typing](typing.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [settings.py](settings.py.md) (1 shared connections)

## Source Files

- `app/core/auth_middleware.py`

## Audit Trail

- EXTRACTED: 22 (96%)
- INFERRED: 1 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*