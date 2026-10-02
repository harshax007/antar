# TaskWorker

> 10 nodes · cohesion 0.22

## Key Concepts

- **TaskWorker** (7 connections) — `app/core/worker.py`
- **.start()** (3 connections) — `app/core/worker.py`
- **._run_loop()** (2 connections) — `app/core/worker.py`
- **.stop()** (2 connections) — `app/core/worker.py`
- **.submit_task()** (2 connections) — `app/core/worker.py`
- **Starts the background worker loop.** (1 connections) — `app/core/worker.py`
- **Stops the background worker loop.** (1 connections) — `app/core/worker.py`
- **Submit an async function to run in the background.** (1 connections) — `app/core/worker.py`
- **.get_result()** (1 connections) — `app/core/worker.py`
- **.__init__()** (1 connections) — `app/core/worker.py`

## Relationships

- [typing](typing.md) (1 shared connections)

## Source Files

- `app/core/worker.py`

## Audit Trail

- EXTRACTED: 11 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*