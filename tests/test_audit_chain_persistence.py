"""
Antar — Audit chain integrity across the persistence boundary
=============================================================
`tests/test_audit.py` covers tampering with the IN-MEMORY log. It passed throughout the
period when `verify_chain()` returned False after every restart, because it never
crossed the persistence boundary — which is exactly where the bug lived.

These tests cross it. For each write path: write, reload from SQLite, verify.

Why the bug existed: each write path hashed its own payload shape while `load_from_db`
reconstructed a different one from fixed columns, so the dict being re-hashed was never
the dict that was hashed. The fix stores the hashed bytes (`payload_json`) and the chain
link (`prev_hash`) on the row.
"""

import sqlite3

import pytest

from app.core.db_path import DB_PATH
from app.services import audit_store


@pytest.fixture(autouse=True)
def _clean_ledger():
    audit_store.clear()
    yield
    audit_store.clear()


def _write_one_of_each():
    audit_store.record("OF-001", "Inspector", "GET", "/api/chat", 200)
    audit_store.record_ai_reasoning("OF-001", "ses-1", "who did it?", "The butler.",
                                    ["query"], ["case-1"])
    audit_store.record_hypothesis_event("hypothesis_confirmed", hypothesis_id="HYP-1",
                                        officer="OF-1", role="Inspector",
                                        reason="[adversarial:COLLAPSES] OVERRIDE - informant")


# ── the regression ────────────────────────────────────────────────────────────
def test_chain_verifies_after_reload():
    """THE regression. Every event type, written then reloaded, must still verify."""
    _write_one_of_each()
    assert audit_store.verify_chain() is True

    audit_store.load_from_db()
    assert audit_store.verify_chain() is True, \
        "chain broke across the persistence boundary — payload_json is not round-tripping"

    r = audit_store.verify_chain_report()
    assert r["verified"] == 3
    assert r["legacy_unverifiable"] == 0


@pytest.mark.parametrize("writer", ["http", "ai_reasoning", "hypothesis"])
def test_each_write_path_survives_reload_individually(writer):
    """Isolated per path, so a future event type that forgets payload_json is pinned to
    the path that broke rather than to a mixed ledger."""
    if writer == "http":
        audit_store.record("OF-1", "Inspector", "POST", "/api/x", 201)
    elif writer == "ai_reasoning":
        audit_store.record_ai_reasoning("OF-1", "s", "q", "a", ["query"], [])
    else:
        audit_store.record_hypothesis_event("hypothesis_rejected", hypothesis_id="H",
                                            officer="OF-1", role="ACP", reason="alibi")
    audit_store.load_from_db()
    assert audit_store.verify_chain() is True


def test_reloaded_payload_is_byte_identical_to_what_was_hashed():
    """The root cause in one assertion: the reloaded dict must equal the hashed dict."""
    entry = audit_store.record_hypothesis_event(
        "hypothesis_confirmed", hypothesis_id="HYP-EQ", officer="OF-9",
        role="Inspector", reason="because")
    before = audit_store._payload_of(entry)

    audit_store.load_from_db()
    after = audit_store._payload_of(audit_store._log[-1])
    assert after == before


def test_hypothesis_fields_survive_reload():
    """hypothesis_id / reason used to be persisted only as user_text / answer, so they
    came back under the wrong keys. The adversarial override record depends on these."""
    audit_store.record_hypothesis_event(
        "hypothesis_confirmed", hypothesis_id="HYP-FIELDS", officer="OF-2",
        role="Inspector", reason="[adversarial:WEAKENED] OVERRIDE - new witness")
    audit_store.load_from_db()

    e = audit_store._log[-1]
    assert e["hypothesis_id"] == "HYP-FIELDS"
    assert e["reason"] == "[adversarial:WEAKENED] OVERRIDE - new witness"
    assert e["type"] == "hypothesis_confirmed"


# ── tamper detection still works, and now locates the break ──────────────────
def test_edited_entry_is_detected_after_reload():
    """Persistence must not become a laundering path for edits."""
    _write_one_of_each()
    audit_store.load_from_db()
    audit_store._log[1]["officer"] = "OF-IMPOSTOR"

    r = audit_store.verify_chain_report()
    assert r["ok"] is False
    assert r["broken_at_index"] == 1
    assert "digest" in r["broken_reason"]


def test_deleted_entry_is_detected():
    """Deleting a row leaves the surviving digests intact — only the prev_hash linkage
    catches it. This was undetectable before prev_hash was stored."""
    _write_one_of_each()
    del audit_store._log[1]

    r = audit_store.verify_chain_report()
    assert r["ok"] is False
    assert "linkage" in r["broken_reason"]


def test_reordered_entries_are_detected():
    _write_one_of_each()
    audit_store._log[0], audit_store._log[1] = audit_store._log[1], audit_store._log[0]
    assert audit_store.verify_chain() is False


def test_tampering_with_the_stored_hash_is_detected():
    _write_one_of_each()
    audit_store._log[2]["hash"] = "0" * 64
    assert audit_store.verify_chain() is False


# ── legacy rows: counted, never silently passed or falsely failed ────────────
def _insert_legacy_row():
    """A row exactly as the pre-fix code wrote it: no payload_json, no prev_hash."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO audit_log (ts, officer, role, method, path, status, type, hash) "
        "VALUES (?,?,?,?,?,?,?,?)",
        ("2020-01-01T00:00:00+00:00", "OF-OLD", "Inspector", "GET", "/legacy", 200,
         "HTTP", "ab" * 32))
    conn.commit()
    conn.close()


def test_legacy_rows_do_not_raise_a_false_tamper_alarm():
    """Pre-fix rows can never verify — the hashed bytes were not recorded. Failing the
    whole ledger for them would cry wolf on every restart."""
    _insert_legacy_row()
    audit_store.load_from_db()

    r = audit_store.verify_chain_report()
    assert r["legacy_unverifiable"] == 1
    assert r["ok"] is True
    assert r["broken_at_index"] is None


def test_legacy_rows_are_reported_not_hidden():
    """`ok: true` alongside unverifiable entries would overstate the guarantee, so the
    count and an explanatory note must travel with it."""
    _insert_legacy_row()
    audit_store.load_from_db()

    r = audit_store.verify_chain_report()
    assert r["legacy_unverifiable"] > 0
    assert "cannot be checked" in r["note"]
    assert r["verified"] < r["total_entries"]


def test_new_entries_after_legacy_rows_still_verify():
    """The chain must re-base across an unverifiable gap and keep checking after it."""
    _insert_legacy_row()
    audit_store.load_from_db()
    audit_store.record("OF-NEW", "Inspector", "GET", "/new", 200)
    audit_store.record("OF-NEW", "Inspector", "GET", "/newer", 200)

    r = audit_store.verify_chain_report()
    assert r["ok"] is True
    assert r["verified"] == 2
    assert r["legacy_unverifiable"] == 1


def test_tampering_after_a_legacy_gap_is_still_caught():
    """Re-basing must not create a blind spot an attacker could hide behind."""
    _insert_legacy_row()
    audit_store.load_from_db()
    audit_store.record("OF-NEW", "Inspector", "GET", "/new", 200)
    audit_store._log[-1]["path"] = "/tampered"

    assert audit_store.verify_chain() is False


# ── contract ──────────────────────────────────────────────────────────────────
def test_empty_ledger_verifies():
    assert audit_store.verify_chain() is True
    assert audit_store.verify_chain_report()["total_entries"] == 0


def test_verification_survives_in_memory_truncation():
    """_log is capped at _MAX, so the oldest entries are dropped and the first surviving
    entry's prev_hash points at something no longer present. That must verify (its own
    digest still checks out) without the missing predecessor reading as a break — the
    middleware writes one entry per API call, so the cap is hit in normal operation."""
    original = audit_store._MAX
    audit_store._MAX = 5
    try:
        for i in range(12):
            audit_store.record(f"OF-{i}", "Inspector", "GET", f"/api/x{i}", 200)
        assert len(audit_store._log) == 5

        r = audit_store.verify_chain_report()
        assert r["ok"] is True
        assert r["verified"] == 5

        audit_store._log[-1]["path"] = "/tampered"
        assert audit_store.verify_chain() is False
    finally:
        audit_store._MAX = original


def test_meta_keys_are_excluded_from_the_hashed_payload():
    """Chain bookkeeping must never leak into the digest, or adding a field to an entry
    would silently invalidate every prior hash."""
    audit_store.record("OF-1", "Inspector", "GET", "/api/x", 200)
    payload = audit_store._payload_of(audit_store._log[-1])
    for meta in audit_store._META_KEYS:
        assert meta not in payload


def test_integrity_endpoint_reports_the_ledger_state():
    from fastapi.testclient import TestClient
    from main import app

    audit_store.record("OF-1", "Admin", "GET", "/api/x", 200)
    res = TestClient(app).get("/api/audit/integrity",
                              headers={"x-role": "Admin", "x-officer": "OF-1"})
    assert res.status_code == 200
    body = res.json()
    assert set(body) >= {"ok", "total_entries", "verified", "legacy_unverifiable", "note"}
