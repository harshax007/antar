"""Tests for the long-task jobs API (admin Expert Workspace)."""
import asyncio

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture()
async def client():
    from main import app
    from app.core import orchestrator
    orchestrator.register_default_fleet()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestJobs:
    @pytest.mark.anyio
    async def test_launch_and_poll_deep_research(self, client):
        r = await client.post("/api/jobs", json={"type": "deep_research", "target": "Rajajinagar"})
        assert r.status_code == 200
        jid = r.json()["job_id"]
        for _ in range(60):
            g = await client.get(f"/api/jobs/{jid}")
            if g.json()["status"] in ("done", "failed"):
                break
            await asyncio.sleep(0.5)
        job = (await client.get(f"/api/jobs/{jid}")).json()
        assert job["status"] == "done", job
        assert job["result"] is not None and job["summary"]

    @pytest.mark.anyio
    async def test_recompile_launches(self, client):
        r = await client.post("/api/jobs", json={"type": "recompile_board"})
        assert r.status_code == 200
        assert r.json()["status"] == "queued"

    @pytest.mark.anyio
    async def test_list_includes_job(self, client):
        r = await client.post("/api/jobs", json={"type": "deep_research", "target": "Rajajinagar"})
        jid = r.json()["job_id"]
        lst = await client.get("/api/jobs")
        assert any(j["job_id"] == jid for j in lst.json()["jobs"])

    @pytest.mark.anyio
    async def test_bad_type_rejected(self, client):
        r = await client.post("/api/jobs", json={"type": "mine_bitcoin"})
        assert r.status_code == 422

    @pytest.mark.anyio
    async def test_unknown_job_404(self, client):
        r = await client.get("/api/jobs/job-nope")
        assert r.status_code == 404
