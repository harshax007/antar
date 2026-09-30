"""Tests for Phase 4: Background Jobs & Workspace API."""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.api.jobs import _JOBS, JobRequest, create_job, get_unnotified_completed_jobs

client = TestClient(app)

def test_workspace_list():
    res = client.get("/api/workspace", headers={"X-Officer": "OF-1001"})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "bookmarks" in data
    assert "conclusions" in data

def test_job_creation_and_option_b_notification():
    # 1. Create a quick pattern_scan job via API
    res = client.post("/api/jobs", json={"type": "pattern_scan", "target": "Rajajinagar"})
    assert res.status_code == 200
    job_id = res.json()["job_id"]
    
    # Simulate completion
    _JOBS[job_id]["status"] = "done"
    _JOBS[job_id]["summary"] = "Detected spike in vehicle thefts."
    _JOBS[job_id]["notified"] = False
    
    # 2. Check unnotified jobs
    unnotified = get_unnotified_completed_jobs("OF-1001")
    assert any(j["job_id"] == job_id for j in unnotified)
    
    # Second call should return empty because notified flag is now set to True
    unnotified_after = get_unnotified_completed_jobs("OF-1001")
    assert not any(j["job_id"] == job_id for j in unnotified_after)

def test_workspace_note_addition():
    res = client.post("/api/workspace/prod-1/note", json={"item_id": "prod-1", "text": "Needs immediate verification by patrol team."})
    assert res.status_code == 200
    data = res.json()
    assert len(data["notes"]) >= 1
    assert data["notes"][0]["text"] == "Needs immediate verification by patrol team."
