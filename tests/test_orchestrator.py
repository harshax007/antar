"""
Tests for the production orchestration layer (app/core/orchestrator.py).

Covers:
  • run_agent — success telemetry, timeout, retry, honest degraded result
  • circuit breaker — opens after N consecutive failures, fails fast, cooldown
  • status() shape + register_default_fleet
  • product_store.refresh_expiring — only refreshes soon-to-expire products
  • chat_stream pipeline — a failing sub-agent emits a "degraded" step,
    never fabricated data
  • GET /api/orchestrator/status endpoint
"""
import asyncio
import json
import time

import pytest
from httpx import AsyncClient, ASGITransport

from app.core import orchestrator
from app.core.orchestrator import AgentSpec


@pytest.fixture(autouse=True)
def _clean_state():
    orchestrator.reset()
    yield
    orchestrator.reset()


# ── run_agent ─────────────────────────────────────────────────────────────────
class TestRunAgent:
    @pytest.mark.anyio
    async def test_success_returns_result_and_telemetry(self):
        orchestrator.register(AgentSpec(name="t_ok", role="test"))

        async def work():
            return {"value": 42}

        ok, result, meta = await orchestrator.run_agent("t_ok", work)
        assert ok and result == {"value": 42}
        assert meta["status"] == "ok" and meta["ms"] >= 0
        st = orchestrator.status()["agents"]["t_ok"]
        assert st["calls"] == 1 and st["successes"] == 1

    @pytest.mark.anyio
    async def test_timeout_degrades_honestly(self):
        orchestrator.register(AgentSpec(name="t_slow", role="test", timeout_s=0.05, retries=0))

        async def slow():
            await asyncio.sleep(1)

        ok, result, meta = await orchestrator.run_agent("t_slow", slow)
        assert not ok and result is None
        assert "timed out" in meta["reason"]

    @pytest.mark.anyio
    async def test_retry_recovers_from_transient_failure(self):
        orchestrator.register(AgentSpec(name="t_flaky", role="test", retries=1))
        attempts = {"n": 0}

        async def flaky():
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RuntimeError("transient")
            return "recovered"

        ok, result, meta = await orchestrator.run_agent("t_flaky", flaky)
        assert ok and result == "recovered"
        assert meta["attempt"] == 2

    @pytest.mark.anyio
    async def test_failure_reason_is_surfaced(self):
        orchestrator.register(AgentSpec(name="t_fail", role="test", retries=0))

        async def boom():
            raise ValueError("index not warmed")

        ok, _, meta = await orchestrator.run_agent("t_fail", boom)
        assert not ok and "index not warmed" in meta["reason"]

    @pytest.mark.anyio
    async def test_unregistered_agent_autoregisters(self):
        async def work():
            return 1
        ok, result, _ = await orchestrator.run_agent("t_unknown", work)
        assert ok and result == 1
        assert orchestrator.status()["agents"]["t_unknown"]["role"] == "unregistered"


# ── circuit breaker ───────────────────────────────────────────────────────────
class TestCircuitBreaker:
    @pytest.mark.anyio
    async def test_opens_after_threshold_and_fails_fast(self):
        orchestrator.register(AgentSpec(name="t_break", role="test", retries=0,
                                        breaker_threshold=2, breaker_cooldown_s=60))
        calls = {"n": 0}

        async def boom():
            calls["n"] += 1
            raise RuntimeError("down")

        for _ in range(2):
            ok, _, _ = await orchestrator.run_agent("t_break", boom)
            assert not ok
        # Circuit now open — the factory must NOT be invoked again.
        ok, _, meta = await orchestrator.run_agent("t_break", boom)
        assert not ok and meta["status"] == "circuit_open"
        assert calls["n"] == 2
        assert orchestrator.status()["agents"]["t_break"]["circuit_open"] is True

    @pytest.mark.anyio
    async def test_cooldown_closes_circuit(self):
        orchestrator.register(AgentSpec(name="t_heal", role="test", retries=0,
                                        breaker_threshold=1, breaker_cooldown_s=0.05))

        async def boom():
            raise RuntimeError("down")

        await orchestrator.run_agent("t_heal", boom)
        await asyncio.sleep(0.08)

        async def fine():
            return "back"
        ok, result, _ = await orchestrator.run_agent("t_heal", fine)
        assert ok and result == "back"


# ── fleet + status ────────────────────────────────────────────────────────────
class TestFleet:
    def test_default_fleet_registers_all_roles(self):
        orchestrator.register_default_fleet()
        agents = orchestrator.status()["agents"]
        for name in ("query", "brain", "profile", "network", "geo", "pattern",
                     "predict", "alerts", "osint", "sentinel", "products"):
            assert name in agents, name
            assert agents[name]["role"]

    def test_status_includes_autonomous_block(self):
        s = orchestrator.status()
        assert "autonomous" in s
        for key in ("running", "ticks", "last_refreshed"):
            assert key in s["autonomous"]


# ── product_store.refresh_expiring ───────────────────────────────────────────
class TestRefreshExpiring:
    def test_only_refreshes_soon_to_expire(self):
        from app.services import product_store
        calls = {"fresh": 0, "stale": 0}
        product_store.register_generator("test:fresh", lambda: calls.__setitem__("fresh", calls["fresh"] + 1) or {"v": 1}, default_ttl=9999)
        product_store.register_generator("test:stale", lambda: calls.__setitem__("stale", calls["stale"] + 1) or {"v": 2}, default_ttl=9999)
        product_store.put_product("test:fresh", {"v": 1}, ttl=9999)   # far future
        product_store.put_product("test:stale", {"v": 2}, ttl=1)      # about to expire

        out = product_store.refresh_expiring(within_s=60)
        assert "test:stale" in out and "test:fresh" not in out
        assert calls["stale"] == 1 and calls["fresh"] == 0
        # cleanup
        product_store.invalidate("test:")
        product_store._generators.pop("test:fresh", None)
        product_store._generators.pop("test:stale", None)


# ── degraded step in the chat pipeline ───────────────────────────────────────
class TestPipelineDegradation:
    @pytest.mark.anyio
    async def test_failing_agent_emits_degraded_step_not_fake_data(self, monkeypatch):
        import app.agents.prediction_agent as pa

        async def broken(*a, **k):
            raise RuntimeError("model file missing")

        monkeypatch.setattr(pa, "prediction_agent_run", broken)

        from app.api.chat_stream import _run_pipeline, StreamChatRequest
        from app.core.sse import SSEQueue
        q = SSEQueue()
        await _run_pipeline(StreamChatRequest(
            text="/anticipate robbery in Bengaluru", lang="en",
            session_id="test-orch-degraded"), q)
        events = [json.loads(l.replace("data: ", "").strip()) async for l in q]

        degraded = [e for e in events if e["type"] == "step" and e.get("status") == "degraded"]
        assert any(e["agent"] == "predict" for e in degraded)
        # No predict visual may exist — degraded agents contribute nothing.
        assert not any(e["type"] == "visual" and e.get("key") == "predict" for e in events)
        # The pipeline still completes (graceful degradation).
        assert any(e["type"] == "complete" for e in events)


# ── HTTP endpoint ─────────────────────────────────────────────────────────────
class TestOpsEndpoint:
    @pytest.mark.anyio
    async def test_status_endpoint(self):
        from main import app
        orchestrator.register_default_fleet()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/orchestrator/status")
        assert r.status_code == 200
        body = r.json()
        assert "agents" in body and "autonomous" in body
        assert "geo" in body["agents"]
