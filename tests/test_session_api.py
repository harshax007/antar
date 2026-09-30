"""
Tests for encrypted session save/load (app/api/session_api.py).
Contract: sessions are unreadable on disk, roundtrip losslessly, ids validated.
"""
import json

import pytest
from httpx import AsyncClient, ASGITransport

from app.api import session_api


@pytest.fixture()
async def client():
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


THREAD = {"messages": [
    {"role": "user", "text": "Who are the repeat offenders in Rajajinagar?"},
    {"role": "assistant", "text": "Found 20 recidivists.", "citations": [{"fir": "2026-101"}]},
], "lang": "en"}


class TestRoundtrip:
    @pytest.mark.anyio
    async def test_save_then_load(self, client):
        r = await client.post("/api/session/save",
                              json={"session_id": "test-enc-001", "payload": THREAD})
        assert r.status_code == 200 and r.json()["encrypted"] is True
        r2 = await client.get("/api/session/load/test-enc-001")
        assert r2.status_code == 200
        assert r2.json()["payload"] == THREAD

    @pytest.mark.anyio
    async def test_ciphertext_is_not_plaintext(self, client):
        await client.post("/api/session/save",
                          json={"session_id": "test-enc-002", "payload": THREAD})
        raw = (session_api._STORE / "test-enc-002.enc").read_bytes()
        assert b"Rajajinagar" not in raw
        assert b"repeat offenders" not in raw

    @pytest.mark.anyio
    async def test_listed_after_save(self, client):
        await client.post("/api/session/save",
                          json={"session_id": "test-enc-003", "payload": THREAD})
        r = await client.get("/api/session/saved")
        ids = [s["session_id"] for s in r.json()["sessions"]]
        assert "test-enc-003" in ids


class TestValidation:
    @pytest.mark.anyio
    async def test_load_unknown_404(self, client):
        r = await client.get("/api/session/load/test-enc-none")
        assert r.status_code == 404

    @pytest.mark.anyio
    async def test_bad_id_rejected(self, client):
        r = await client.post("/api/session/save",
                              json={"session_id": "../../etc/passwd", "payload": {}})
        assert r.status_code == 400
