from app.services import audit_store
from app.core.audit import hash_event
import pytest
import copy

def test_audit_ledger_chain_integrity(tmp_path, monkeypatch):
    # Setup: its own file. clear() deletes every row; never point it at main.db.
    monkeypatch.setattr(audit_store, "DB_PATH", str(tmp_path / "ledger.db"))
    audit_store.init_db()
    audit_store.clear()
    
    # Record some mock data
    audit_store.record("OF-001", "user", "GET", "/api/chat", 200)
    audit_store.record_ai_reasoning("OF-001", "ses-123", "who did it?", "The butler.", ["query"], ["case-1"])
    
    # Verify chain is valid
    assert audit_store.verify_chain() is True
    
    # Tamper with the stored ledger
    import json
    import sqlite3
    conn = sqlite3.connect(audit_store.DB_PATH)
    log_id, pj = conn.execute("SELECT log_id, payload_json FROM audit_log ORDER BY log_id LIMIT 1").fetchone()
    conn.execute("UPDATE audit_log SET payload_json = ? WHERE log_id = ?",
                 (json.dumps({**json.loads(pj), "method": "POST"}, sort_keys=True), log_id))
    conn.commit()
    conn.close()
    
    # Verify chain fails
    assert audit_store.verify_chain() is False

def test_audit_ledger_hashing():
    prev = "0" * 64
    payload = {"officer": "OF-001"}
    h = hash_event(prev, payload)
    
    assert len(h) == 64  # SHA-256 hex digest length
    assert h != prev
