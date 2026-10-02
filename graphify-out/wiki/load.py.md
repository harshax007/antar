# load.py

> 15 nodes · cohesion 0.18

## Key Concepts

- **load.py** (18 connections) — `app/seeds/load.py`
- **zcql_query()** (11 connections) — `app/core/catalyst.py`
- **main()** (5 connections) — `app/seeds/load.py`
- **push_to_datastore()** (5 connections) — `app/seeds/load.py`
- **validate()** (5 connections) — `app/seeds/load.py`
- **spot_check()** (4 connections) — `app/seeds/load.py`
- **_truncate_table()** (3 connections) — `app/seeds/load.py`
- **Run a ZCQL query and return plain dict rows. Aggregation / GROUP-BY-heavy reads…** (1 connections) — `app/core/catalyst.py`
- **Antar — Seed Loader CLI ================================= Usage (from antar-…** (1 connections) — `app/seeds/load.py`
- **Batch-insert into Catalyst Data Store using the real zcatalyst-sdk API:…** (1 connections) — `app/seeds/load.py`
- **Delete all rows from a table (paged read → delete_rows by id). [VERIFY] whether…** (1 connections) — `app/seeds/load.py`
- **Phase 1, Step 1.7 validation: 5 ZCQL spot-queries (incl. one OLAP aggregation)…** (1 connections) — `app/seeds/load.py`
- **Returns a list of failure strings. Empty list = all planted patterns hold.** (1 connections) — `app/seeds/load.py`
- **evening_share()** (1 connections) — `app/seeds/load.py`
- **argparse** (1 connections)

## Relationships

- [stratus.py](stratus.py.md) (4 shared connections)
- [build_world](build_world.md) (3 shared connections)
- [anomaly.py](anomaly.py.md) (2 shared connections)
- [zcql_local.py](zcql_local.py.md) (2 shared connections)
- [second_brain/store.py](second_brain-store.py.md) (2 shared connections)
- [chat_stream.py](chat_stream.py.md) (1 shared connections)
- [SSEQueue](SSEQueue.md) (1 shared connections)
- [parse_json_response](parse_json_response.md) (1 shared connections)
- [sys](sys.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [obs/store.py](obs-store.py.md) (1 shared connections)
- [second_brain/ingestion.py](second_brain-ingestion.py.md) (1 shared connections)

## Source Files

- `app/core/catalyst.py`
- `app/seeds/load.py`

## Audit Trail

- EXTRACTED: 39 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*