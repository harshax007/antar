from app.services import audit_store
from app.core.audit import hash_event
import pytest
import copy

def test_audit_ledger_chain_integrity():
    # Setup
    audit_store.clear()
    
    # Record some mock data
    audit_store.record("OF-001", "user", "GET", "/api/chat", 200)
    audit_store.record_ai_reasoning("OF-001", "ses-123", "who did it?", "The butler.", ["query"], ["case-1"])
    
    # Verify chain is valid
    assert audit_store.verify_chain() is True
    
    # Tamper with the ledger
    audit_store._log[0]["method"] = "POST"
    
    # Verify chain fails
    assert audit_store.verify_chain() is False

def test_audit_ledger_hashing():
    prev = "0" * 64
    payload = {"officer": "OF-001"}
    h = hash_event(prev, payload)
    
    assert len(h) == 64  # SHA-256 hex digest length
    assert h != prev
