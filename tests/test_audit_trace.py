import pytest
from app.services import audit_store
from app.api.audit import get_trace
from fastapi import HTTPException
import uuid
import os

def test_audit_store_reasoning_trace():
    # Force test DB so we don't clobber main db
    # We can just use the memory store or the real one since it cleans up old logs
    audit_store.init_db()
    
    reasoning_id = f"test-trace-{uuid.uuid4().hex[:8]}"
    trace = [
        {"step": "intent", "detail": "classified as predict"},
        {"step": "predict", "detail": "generated forecast"}
    ]
    
    # Write
    audit_store.record_ai_reasoning(
        officer="test-officer",
        session_id="test-ses",
        user_text="hello",
        answer="world",
        agents_used=["predict"],
        citations=[],
        reasoning_id=reasoning_id,
        reasoning_trace=trace
    )
    
    # Read back
    read_trace = audit_store.get_reasoning_trace(reasoning_id)
    assert read_trace is not None
    assert len(read_trace) == 2
    assert read_trace[0]["step"] == "intent"
    
def test_trace_endpoint():
    reasoning_id = f"test-trace-{uuid.uuid4().hex[:8]}"
    trace = [{"step": "test", "detail": "test endpoint"}]
    
    audit_store.record_ai_reasoning(
        officer="test-officer",
        session_id="test-ses",
        user_text="hello",
        answer="world",
        agents_used=["test"],
        citations=[],
        reasoning_id=reasoning_id,
        reasoning_trace=trace
    )
    
    async def run_test():
        # Call endpoint
        res = await get_trace(reasoning_id)
        assert res["reasoning_id"] == reasoning_id
        assert res["trace"][0]["step"] == "test"
        
        # Call with non-existent id
        with pytest.raises(HTTPException) as exc:
            await get_trace("does-not-exist")
        assert exc.value.status_code == 404
        
    import anyio
    anyio.run(run_test)
