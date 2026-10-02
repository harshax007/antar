# test_generate_retries_then_raises

> 8 nodes · cohesion 0.29

## Key Concepts

- **test_generate_retries_then_raises()** (6 connections) — `tests/test_quickml.py`
- **test_generate_success_and_client_is_reused()** (6 connections) — `tests/test_quickml.py`
- **_install()** (4 connections) — `tests/test_quickml.py`
- **handler()** (2 connections) — `tests/test_quickml.py`
- **Point the shared client at an in-process MockTransport (no real network).** (1 connections) — `tests/test_quickml.py`
- **200 + {response} → trimmed text; the shared client is a reused singleton.** (1 connections) — `tests/test_quickml.py`
- **Persistent HTTP 500 → retried, then RuntimeError surfacing the status code.** (1 connections) — `tests/test_quickml.py`
- **handler()** (1 connections) — `tests/test_quickml.py`

## Relationships

- [pytest](pytest.md) (3 shared connections)
- [quickml.py](quickml.py.md) (3 shared connections)

## Source Files

- `tests/test_quickml.py`

## Audit Trail

- EXTRACTED: 12 (86%)
- INFERRED: 2 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*