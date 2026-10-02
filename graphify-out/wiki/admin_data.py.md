# admin_data.py

> 24 nodes · cohesion 0.10

## Key Concepts

- **admin_data.py** (17 connections) — `app/api/admin_data.py`
- **ingest_dataset()** (7 connections) — `app/api/admin_data.py`
- **schema_registry.py** (7 connections) — `app/core/schema_registry.py`
- **get_table_schema()** (5 connections) — `app/core/schema_registry.py`
- **FIRRecord** (4 connections) — `app/api/admin_data.py`
- **get_schema()** (4 connections) — `app/api/admin_data.py`
- **trigger_summary_build()** (3 connections) — `app/api/admin_data.py`
- **get_db_schema_context()** (3 connections) — `app/core/schema_registry.py`
- **csv** (3 connections)
- **io** (3 connections)
- **.compute_derived_fields()** (2 connections) — `app/api/admin_data.py`
- **BaseModel** (1 connections)
- **get** (1 connections)
- **post** (1 connections)
- **UploadFile** (1 connections)
- **Antar — Admin Data Governance API =======================================…** (1 connections) — `app/api/admin_data.py`
- **Runs the summary build pipeline asynchronously.** (1 connections) — `app/api/admin_data.py`
- **Ingests a CSV dataset, validates it perfectly against the internal schema,…** (1 connections) — `app/api/admin_data.py`
- **Returns the live schema to internal tools/LLM agents.** (1 connections) — `app/api/admin_data.py`
- **Schema Registry Module Exposes live database schema to LLM agents dynamically…** (1 connections) — `app/core/schema_registry.py`
- **Dynamically fetches schema so LLMs don't hallucinate.** (1 connections) — `app/core/schema_registry.py`
- **Returns a markdown string of the schema for injection into LLM prompts.** (1 connections) — `app/core/schema_registry.py`
- **BackgroundTasks** (1 connections)
- **model_validator** (1 connections)

## Relationships

- [typing](typing.md) (6 shared connections)
- [time](time.md) (4 shared connections)
- [sys](sys.md) (1 shared connections)
- [pydantic](pydantic.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [evidence_ledger.py](evidence_ledger.py.md) (1 shared connections)
- [voice.py](voice.py.md) (1 shared connections)

## Source Files

- `app/api/admin_data.py`
- `app/core/schema_registry.py`

## Audit Trail

- EXTRACTED: 42 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*