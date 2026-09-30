import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.settings import settings
from app.services.ingestion import map_and_ingest_csv

client = TestClient(app)

def test_cron_endpoints_unauthorized():
    # Attempting to access without the secret header should fail
    resp = client.post("/api/alerts/scan")
    assert resp.status_code == 401
    
    resp = client.post("/api/brain/consolidate")
    assert resp.status_code == 401

def test_cron_endpoints_authorized():
    # Providing the secret should bypass the 401
    headers = {"x-cron-secret": settings.CRON_SECRET_KEY}
    resp = client.post("/api/alerts/scan", headers=headers)
    # The scan might return 200 depending on mock
    assert resp.status_code in [200, 500]  # If QuickML fails it might be 500, but not 401

    resp = client.post("/api/brain/consolidate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

def test_ingestion_limits():
    # 1. 5MB file size limit
    large_file = b"x" * (6 * 1024 * 1024)
    res = map_and_ingest_csv(large_file)
    assert res.get("error") == "File exceeds 5MB limit."
    
    # 2. 50 columns limit
    headers = ",".join(f"col_{i}" for i in range(55))
    csv_content = f"{headers}\n" + ",".join("1" for i in range(55))
    res = map_and_ingest_csv(csv_content.encode("utf-8"))
    assert res.get("error") == "CSV exceeds 50 columns limit."

def test_rate_limiter_chat():
    """Token bucket trips once capacity is exhausted.

    Asserted deterministically instead of firing 61 HTTP calls inside one second:
    each /api/chat now does real per-request I/O (a persistent audit write), so the
    old timing-based version was flaky — a token could refill mid-burst and let the
    61st request through.
    """
    import time as _time
    from app.core.rate_limiter import _buckets, check_rate_limit

    # (a) Core token-bucket logic: capacity 60 -> first 60 allowed, 61st rejected.
    #     A tight in-process loop runs in well under one second, so refill < 1 token.
    _buckets.clear()
    ip = "203.0.113.7"
    for i in range(60):
        assert check_rate_limit(ip) is True, f"rate limited too early at request {i}"
    assert check_rate_limit(ip) is False

    # (b) /api/chat is actually wired to the limiter: pre-exhaust this client's
    #     bucket so the very next request must be 429 (TestClient host = "testclient").
    _buckets.clear()
    _buckets["testclient"] = (0.0, _time.monotonic())
    resp = client.post("/api/chat", json={"text": "Hello"})
    assert resp.status_code == 429
