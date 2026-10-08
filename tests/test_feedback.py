"""Tests for POST /api/feedback — persisted, validated, counted."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.api import feedback as fb


@pytest.fixture(autouse=True)
def _own_feedback_file(tmp_path, monkeypatch):
    # These tests POST real ratings. Against the live file they left 77 of its 78 rows
    # ("repeat offenders?" up, "q" down), which the app then counted as officer feedback.
    monkeypatch.setattr(fb, "_FILE", tmp_path / "fb.jsonl")


@pytest.fixture()
async def client():
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestFeedback:
    @pytest.mark.anyio
    async def test_submit_up_is_persisted(self, client):
        before = (await client.get("/api/feedback/stats")).json()["up"]
        r = await client.post("/api/feedback", json={
            "session_id": "test-fb-1", "question": "repeat offenders?", "rating": "up"})
        assert r.status_code == 200 and r.json()["recorded"] is True
        after = (await client.get("/api/feedback/stats")).json()["up"]
        assert after == before + 1
        assert fb._FILE.exists()

    @pytest.mark.anyio
    async def test_down_counted(self, client):
        before = (await client.get("/api/feedback/stats")).json()["down"]
        await client.post("/api/feedback", json={
            "session_id": "test-fb-2", "question": "q", "rating": "down", "note": "wrong zone"})
        after = (await client.get("/api/feedback/stats")).json()["down"]
        assert after == before + 1

    @pytest.mark.anyio
    async def test_invalid_rating_rejected(self, client):
        r = await client.post("/api/feedback", json={
            "session_id": "x", "question": "q", "rating": "meh"})
        assert r.status_code == 422
