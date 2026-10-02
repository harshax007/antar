# conftest.py

> 8 nodes · cohesion 0.32

## Key Concepts

- **conftest.py** (7 connections) — `tests/conftest.py`
- **_keep_main_db_clean()** (4 connections) — `tests/conftest.py`
- **_rowid_marks()** (3 connections) — `tests/conftest.py`
- **_force_offline()** (2 connections) — `tests/conftest.py`
- **fixture** (2 connections)
- **Pytest config — force tests into deterministic OFFLINE mode regardless of the…** (1 connections) — `tests/conftest.py`
- **Highest rowid per table, so anything inserted after this point is identifiable.** (1 connections) — `tests/conftest.py`
- **Remove rows the test run leaves behind in main.db. The suite runs against the…** (1 connections) — `tests/conftest.py`

## Relationships

- [pytest](pytest.md) (1 shared connections)
- [time](time.md) (1 shared connections)
- [settings.py](settings.py.md) (1 shared connections)

## Source Files

- `tests/conftest.py`

## Audit Trail

- EXTRACTED: 12 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*