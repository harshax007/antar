# test_audit_chain_persistence.py

> 37 nodes · cohesion 0.10

## Key Concepts

- **test_audit_chain_persistence.py** (25 connections) — `tests/test_audit_chain_persistence.py`
- **verify_chain_report()** (14 connections) — `app/services/audit_store.py`
- **load_from_db()** (12 connections) — `app/services/audit_store.py`
- **verify_chain()** (12 connections) — `app/services/audit_store.py`
- **_write_one_of_each()** (9 connections) — `tests/test_audit_chain_persistence.py`
- **_insert_legacy_row()** (6 connections) — `tests/test_audit_chain_persistence.py`
- **test_chain_verifies_after_reload()** (6 connections) — `tests/test_audit_chain_persistence.py`
- **test_new_entries_after_legacy_rows_still_verify()** (6 connections) — `tests/test_audit_chain_persistence.py`
- **test_tampering_after_a_legacy_gap_is_still_caught()** (6 connections) — `tests/test_audit_chain_persistence.py`
- **_payload_of()** (5 connections) — `app/services/audit_store.py`
- **test_edited_entry_is_detected_after_reload()** (5 connections) — `tests/test_audit_chain_persistence.py`
- **test_legacy_rows_are_reported_not_hidden()** (5 connections) — `tests/test_audit_chain_persistence.py`
- **test_legacy_rows_do_not_raise_a_false_tamper_alarm()** (5 connections) — `tests/test_audit_chain_persistence.py`
- **test_reloaded_payload_is_byte_identical_to_what_was_hashed()** (5 connections) — `tests/test_audit_chain_persistence.py`
- **test_verification_survives_in_memory_truncation()** (5 connections) — `tests/test_audit_chain_persistence.py`
- **test_deleted_entry_is_detected()** (4 connections) — `tests/test_audit_chain_persistence.py`
- **test_hypothesis_fields_survive_reload()** (4 connections) — `tests/test_audit_chain_persistence.py`
- **test_meta_keys_are_excluded_from_the_hashed_payload()** (4 connections) — `tests/test_audit_chain_persistence.py`
- **test_empty_ledger_verifies()** (3 connections) — `tests/test_audit_chain_persistence.py`
- **test_reordered_entries_are_detected()** (3 connections) — `tests/test_audit_chain_persistence.py`
- **test_tampering_with_the_stored_hash_is_detected()** (3 connections) — `tests/test_audit_chain_persistence.py`
- **Verify the ledger and say exactly what was checked. Two independent checks per…** (1 connections) — `app/services/audit_store.py`
- **True when no VERIFIABLE entry failed its digest or linkage check. When…** (1 connections) — `app/services/audit_store.py`
- **The dict that was (or would have been) hashed — chain bookkeeping stripped.** (1 connections) — `app/services/audit_store.py`
- **Antar — Audit chain integrity across the persistence boundary…** (1 connections) — `tests/test_audit_chain_persistence.py`
- *... and 12 more nodes in this community*

## Relationships

- [audit_store.py](audit_store.py.md) (21 shared connections)
- [FastAPI](FastAPI.md) (2 shared connections)
- [test_hitl.py](test_hitl.py.md) (2 shared connections)
- [time](time.md) (2 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [app_services](app_services.md) (1 shared connections)

## Source Files

- `app/services/audit_store.py`
- `tests/test_audit_chain_persistence.py`

## Audit Trail

- EXTRACTED: 96 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*