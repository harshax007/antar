# stratus.py

> 21 nodes · cohesion 0.15

## Key Concepts

- **stratus.py** (11 connections) — `app/services/stratus.py`
- **get_app()** (10 connections) — `app/core/catalyst.py`
- **catalyst.py** (7 connections) — `app/core/catalyst.py`
- **_bucket()** (6 connections) — `app/services/stratus.py`
- **round_trip_smoke()** (6 connections) — `app/services/stratus.py`
- **bucket_exists()** (4 connections) — `app/services/stratus.py`
- **download()** (4 connections) — `app/services/stratus.py`
- **presigned_get_url()** (4 connections) — `app/services/stratus.py`
- **upload()** (4 connections) — `app/services/stratus.py`
- **presigned_put_url()** (3 connections) — `app/services/stratus.py`
- **Antar — Catalyst App Singleton / Init Helper…** (1 connections) — `app/core/catalyst.py`
- **Return an authenticated CatalystApp. - In an AppSail request handler, pass the…** (1 connections) — `app/core/catalyst.py`
- **Antar — Stratus Object Storage Service…** (1 connections) — `app/services/stratus.py`
- **Upload an object. `key` is the path within the bucket, e.g.…** (1 connections) — `app/services/stratus.py`
- **Download an object's bytes.** (1 connections) — `app/services/stratus.py`
- **Pre-signed GET URL (so the browser can fetch a private object directly). Used…** (1 connections) — `app/services/stratus.py`
- **Pre-signed PUT URL (for direct browser uploads, if ever needed).** (1 connections) — `app/services/stratus.py`
- **Health/setup check — does the configured bucket exist?** (1 connections) — `app/services/stratus.py`
- **Phase 1, Step 1.8 smoke test: upload → download → presign a tiny object. Run…** (1 connections) — `app/services/stratus.py`
- **zcatalyst_sdk** (1 connections)
- **zcatalyst_sdk_credentials** (1 connections)

## Relationships

- [load.py](load.py.md) (4 shared connections)
- [settings.py](settings.py.md) (2 shared connections)
- [second_brain/store.py](second_brain-store.py.md) (2 shared connections)

## Source Files

- `app/core/catalyst.py`
- `app/services/stratus.py`

## Audit Trail

- EXTRACTED: 39 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*