# audit_store.py

> 25 nodes · cohesion 0.14

## Key Concepts

- **audit_store.py** (35 connections) — `app/services/audit_store.py`
- **record()** (13 connections) — `app/services/audit_store.py`
- **hash_event()** (11 connections) — `app/core/audit.py`
- **record_ai_reasoning()** (11 connections) — `app/services/audit_store.py`
- **record_hypothesis_event()** (11 connections) — `app/services/audit_store.py`
- **test_audit.py** (8 connections) — `tests/test_audit.py`
- **test_each_write_path_survives_reload_individually()** (8 connections) — `tests/test_audit_chain_persistence.py`
- **core/audit.py** (7 connections) — `app/core/audit.py`
- **_append()** (7 connections) — `app/services/audit_store.py`
- **record_hitl_event()** (5 connections) — `app/services/audit_store.py`
- **_sync_to_catalyst_placeholder()** (5 connections) — `app/services/audit_store.py`
- **test_audit_ledger_chain_integrity()** (5 connections) — `tests/test_audit.py`
- **clear()** (4 connections) — `app/services/audit_store.py`
- **_clean_ledger()** (3 connections) — `tests/test_audit_chain_persistence.py`
- **hashlib** (2 connections)
- **test_integrity_endpoint_reports_the_ledger_state()** (2 connections) — `tests/test_audit_chain_persistence.py`
- **test_audit_ledger_hashing()** (2 connections) — `tests/test_audit.py`
- **Cryptographically hashes a dictionary payload combined with the previous hash…** (1 connections) — `app/core/audit.py`
- **Antar — Audit log (M10 / F7) — Persistent SQLite + Catalyst Sync Hybrid. A row…** (1 connections) — `app/services/audit_store.py`
- **Record a hypothesis lifecycle event (proposed, shown, confirmed, rejected).…** (1 connections) — `app/services/audit_store.py`
- **Record one step of a human-in-the-loop approval on the hash chain.…** (1 connections) — `app/services/audit_store.py`
- **Hash `payload` onto the chain and append it in memory. The single place a chain…** (1 connections) — `app/services/audit_store.py`
- **fixture** (1 connections)
- **parametrize** (1 connections)
- **Isolated per path, so a future event type that forgets payload_json is pinned…** (1 connections) — `tests/test_audit_chain_persistence.py`

## Relationships

- [test_audit_chain_persistence.py](test_audit_chain_persistence.py.md) (21 shared connections)
- [FastAPI](FastAPI.md) (12 shared connections)
- [get_product](get_product.md) (4 shared connections)
- [export_api.py](export_api.py.md) (3 shared connections)
- [hitl.py](hitl.py.md) (3 shared connections)
- [SSEQueue](SSEQueue.md) (2 shared connections)
- [time](time.md) (2 shared connections)
- [typing](typing.md) (2 shared connections)
- [feedback.py](feedback.py.md) (2 shared connections)
- [chat.py](chat.py.md) (1 shared connections)
- [chat_stream.py](chat_stream.py.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)

## Source Files

- `app/core/audit.py`
- `app/services/audit_store.py`
- `tests/test_audit.py`
- `tests/test_audit_chain_persistence.py`

## Audit Trail

- EXTRACTED: 105 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*