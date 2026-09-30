"""
The graph runs its agents under the same contract `chat_stream` does.

`AGENTS.md` declares a `timeout_s` and `retries` for every agent, and the orchestrator
registry is generated from it. `chat_stream` honoured that — eight calls through
`orchestrator.run_agent()`. The graph honoured none of it: it awaited the same agents
directly, so on `/api/chat` a hung agent hung the entire turn and the declared limits were
documentation rather than behaviour.

That is the four-places-can-disagree problem `AGENTS.md` exists to kill, in its most
consequential form — not a label out of step, but a protection only half the product had.

These tests assert the contract rather than the refactor: a slow agent is cut off at its
declared budget, a failing one degrades visibly instead of vanishing, and one failure does
not take its siblings down.
"""

from __future__ import annotations

import asyncio

import pytest

from app.agents import graph as G


def _state(**kw) -> dict:
    base = {"user_text": "crime forecast for Mysuru", "lang": "en", "session_id": "orch",
            "use_llm": False, "routes": [], "entities": {}, "results": {}, "visuals": {},
            "citations": [], "brain_hits": [], "reasoning": [], "actions": [],
            "final_answer": None, "reasoning_id": None}
    base.update(kw)
    return base


def test_every_node_runs_its_agents_through_the_orchestrator():
    """The regression that matters: a node calling an agent bare has no timeout at all."""
    import inspect
    src = inspect.getsource(G)
    # The agents the graph invokes directly, and the call that must wrap each one.
    for fn in ("geo_agent_run", "prediction_agent_run", "pattern_agent_run",
               "alert_suggest_agent_run", "build_network", "compute_profile",
               "run_research", "osint_agent_run", "demographics"):
        assert f"await {fn}(" not in src, (
            f"{fn} is awaited directly — it bypasses its declared timeout and retries")
    assert src.count("_run(") >= 9, "nodes should dispatch through the shared _run helper"


@pytest.mark.anyio
async def test_a_slow_agent_is_cut_off_at_its_declared_budget(monkeypatch):
    """A hung agent must cost its own timeout, not the officer's whole turn."""
    from app.core import orchestrator

    orchestrator.register_default_fleet()
    budget = orchestrator._spec("geo").timeout_s
    assert budget and budget < 30, "the manifest must declare a real budget for geo"

    async def hang(*_a, **_k):
        await asyncio.sleep(budget + 30)

    monkeypatch.setattr(G, "geo_agent_run", hang, raising=False)
    import app.agents.geo_agent as geo_mod
    monkeypatch.setattr(geo_mod, "geo_agent_run", hang)

    started = asyncio.get_event_loop().time()
    out = await G.forecast_node(_state())
    elapsed = asyncio.get_event_loop().time() - started

    # retries + 1 attempts, each capped at the budget, plus room for the other sub-agents.
    assert elapsed < (budget * (orchestrator._spec("geo").retries + 1)) + 25, (
        f"forecast_node ran {elapsed:.1f}s against a {budget}s geo budget — not timed out")
    assert "geo" not in (out.get("results") or {}), "a timed-out agent must not report data"


@pytest.mark.anyio
async def test_a_failing_sub_agent_degrades_visibly_and_spares_its_siblings(monkeypatch):
    """AGENTS.md: "a failing sub-agent yields a degraded step, never a fabricated band"."""
    import app.agents.pattern_agent as pat_mod

    async def boom(*_a, **_k):
        raise RuntimeError("pattern scan exploded")

    monkeypatch.setattr(pat_mod, "pattern_agent_run", boom)
    out = await G.forecast_node(_state())

    steps = out.get("reasoning") or []
    assert any(s.get("agent") == "pattern" and s.get("step") == "degraded" for s in steps), \
        "the failure must appear in the trail, not vanish"
    assert "pattern" not in (out.get("results") or {})
    # The siblings still ran — one bad agent does not empty the whole composite node.
    assert (out.get("results") or {}), "a single failure must not blank the forecast node"


@pytest.mark.anyio
async def test_a_degraded_node_returns_a_usable_update(monkeypatch):
    """LangGraph rejects a bare empty update, so a degraded node must still carry a step."""
    import app.agents.social_agent as soc_mod

    def boom():
        raise RuntimeError("demographics unavailable")

    monkeypatch.setattr(soc_mod, "demographics", boom)
    out = await G.social_node(_state())
    assert out, "a node must never return an empty update"
    assert out["reasoning"][0]["agent"] == "social"
    assert "unavailable" in out["reasoning"][0]["detail"]


def test_the_degraded_helper_names_the_agent_and_the_reason():
    d = G._degraded("geo", "timed out after 8.0s")
    step = d["reasoning"][0]
    assert step["agent"] == "geo" and step["step"] == "degraded"
    assert "geo" in step["detail"] and "timed out" in step["detail"]
