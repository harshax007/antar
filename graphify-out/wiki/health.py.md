# health.py

> 7 nodes · cohesion 0.33

## Key Concepts

- **health.py** (6 connections) — `app/api/health.py`
- **get_model()** (5 connections) — `app/second_brain/embedder.py`
- **health_check()** (4 connections) — `app/api/health.py`
- **get** (1 connections)
- **Antar — Health Check Endpoint /api/health — judges will probe this. Make it…** (1 connections) — `app/api/health.py`
- **Liveness + readiness check. Returns system state visible to judges on Slide 13…** (1 connections) — `app/api/health.py`
- **SentenceTransformer** (1 connections)

## Relationships

- [embedder.py](embedder.py.md) (2 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [index.py](index.py.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)

## Source Files

- `app/api/health.py`
- `app/second_brain/embedder.py`

## Audit Trail

- EXTRACTED: 11 (92%)
- INFERRED: 1 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*