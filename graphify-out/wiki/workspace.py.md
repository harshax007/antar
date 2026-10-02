# workspace.py

> 22 nodes · cohesion 0.13

## Key Concepts

- **workspace.py** (16 connections) — `app/api/workspace.py`
- **list_workspace_items()** (8 connections) — `app/api/workspace.py`
- **add_workspace_note()** (6 connections) — `app/api/workspace.py`
- **get_workspace_item()** (6 connections) — `app/api/workspace.py`
- **list_products()** (6 connections) — `app/services/product_store.py`
- **get_job_sync()** (5 connections) — `app/api/jobs.py`
- **list_jobs_sync()** (5 connections) — `app/api/jobs.py`
- **add_officer_conclusion()** (5 connections) — `app/core/memory.py`
- **Any** (3 connections)
- **NoteRequest** (3 connections) — `app/api/workspace.py`
- **Any** (3 connections)
- **get** (2 connections)
- **Synchronous accessor for workspace API listing.** (1 connections) — `app/api/jobs.py`
- **Synchronous single job lookup.** (1 connections) — `app/api/jobs.py`
- **BaseModel** (1 connections)
- **post** (1 connections)
- **Antar — Expert Workspace API (/api/workspace)…** (1 connections) — `app/api/workspace.py`
- **Add an analytical annotation or comment to a workspace item.** (1 connections) — `app/api/workspace.py`
- **Gather all completed jobs, dossiers, and compiled intelligence products for the…** (1 connections) — `app/api/workspace.py`
- **Get full payload, notes, and evidence trail for a specific workspace item.** (1 connections) — `app/api/workspace.py`
- **Append a compressed analytical conclusion from a completed investigation turn…** (1 connections) — `app/core/memory.py`
- **List stored product keys matching prefix.** (1 connections) — `app/services/product_store.py`

## Relationships

- [get_product](get_product.md) (4 shared connections)
- [jobs.py](jobs.py.md) (3 shared connections)
- [run_agentic_spine](run_agentic_spine.md) (3 shared connections)
- [time](time.md) (2 shared connections)
- [typing](typing.md) (2 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [pydantic](pydantic.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)
- [get_hypothesis](get_hypothesis.md) (1 shared connections)

## Source Files

- `app/api/jobs.py`
- `app/api/workspace.py`
- `app/core/memory.py`
- `app/services/product_store.py`

## Audit Trail

- EXTRACTED: 48 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*