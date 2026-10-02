# lifespan

> 9 nodes · cohesion 0.22

## Key Concepts

- **lifespan()** (7 connections) — `main.py`
- **aclose_client()** (5 connections) — `app/services/quickml.py`
- **quickml_env()** (5 connections) — `tests/test_quickml.py`
- **stop_autonomous()** (2 connections) — `app/core/orchestrator.py`
- **Close the shared client to release pooled connections (call on app shutdown).** (1 connections) — `app/services/quickml.py`
- **Startup: Yield immediately to bind port, run heavy loads in background.** (1 connections) — `main.py`
- **fixture** (1 connections)
- **_no_sleep()** (1 connections) — `tests/test_quickml.py`
- **No token fetch (auth=none), a dummy endpoint, instant backoff, clean shared…** (1 connections) — `tests/test_quickml.py`

## Relationships

- [main.py](main.py.md) (2 shared connections)
- [orchestrator.py](orchestrator.py.md) (1 shared connections)
- [quickml.py](quickml.py.md) (1 shared connections)
- [live_stream.py](live_stream.py.md) (1 shared connections)
- [dataset.py](dataset.py.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)

## Source Files

- `app/core/orchestrator.py`
- `app/services/quickml.py`
- `main.py`
- `tests/test_quickml.py`

## Audit Trail

- EXTRACTED: 15 (94%)
- INFERRED: 1 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*