"""
Antar — Production Orchestrator
====================================
The production-orchestration layer over the role-based agent fleet:

  • Agent registry        — every runtime agent declares a role + limits
  • Timeouts & retries    — no agent may hang or silently die a request
  • Circuit breakers      — repeatedly failing agents are short-circuited
                            (fail fast) until a cooldown elapses
  • Graceful degradation  — failures surface as honest "degraded" results,
                            never fabricated data, never silent drops
  • Autonomous loop       — background task that proactively refreshes
                            product_store products before TTL expiry and
                            runs the Sentinel watch scan
  • Telemetry             — per-agent counters exposed at
                            GET /api/orchestrator/status

Usage (chat pipeline):
    ok, result, meta = await orchestrator.run_agent("geo", lambda: geo_agent_run(text, params))
    if not ok:   # meta["reason"] explains — emit a degraded step, do not fake data
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger()


# ── Registry ──────────────────────────────────────────────────────────────────
@dataclass
class AgentSpec:
    name: str
    role: str
    timeout_s: float = 8.0
    retries: int = 1                 # extra attempts after the first failure
    breaker_threshold: int = 3       # consecutive failures that open the circuit
    breaker_cooldown_s: float = 60.0


@dataclass
class _AgentState:
    calls: int = 0
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    breaker_open_until: float = 0.0
    last_ms: float | None = None
    last_status: str = "idle"        # idle | ok | degraded | circuit_open
    last_error: str | None = None
    last_run_at: float | None = None


_registry: dict[str, AgentSpec] = {}
_state: dict[str, _AgentState] = {}


def register(spec: AgentSpec) -> None:
    _registry[spec.name] = spec
    _state.setdefault(spec.name, _AgentState())


def _spec(name: str) -> AgentSpec:
    if name not in _registry:
        register(AgentSpec(name=name, role="unregistered"))
    return _registry[name]


# ── Default fleet (role-based agents) ────────────────────────────────────────
# Fail-open fallback for a missing or malformed AGENTS.md. The manifest is authoritative;
# this list only keeps the orchestrator alive if the document cannot be read. Names here
# are the ORCHESTRATOR spellings — `alerts` is the fleet name for the `alert_suggest`
# agent, which is exactly the kind of divergence the manifest now records as an alias.
_FALLBACK_FLEET = [
    ("query",    "Vault - template query",                  10.0),
    ("brain",    "Vault - semantic recall",                   6.0),
    ("profile",  "Motive - suspect profiler",                15.0),
    ("network",  "Link - graph builder",                     15.0),
    ("geo",      "Lens - geo intelligence",                   8.0),
    ("pattern",  "Sense - MO pattern detector",               8.0),
    ("predict",  "Core - risk forecaster",                   15.0),
    ("alerts",   "Beacon - patrol advisor",                   6.0),
    ("osint",    "Scout - open-web scan",                    15.0),
    ("research", "Trace - K/D/I/U dossier",                  12.0),
    ("sentinel", "Breach - watchlist tripwires",             10.0),
    ("products", "Master Orchestrator - product compiler",   30.0),
]


def register_default_fleet() -> None:
    """Register every agent declared in AGENTS.md (kind: worker | service).

    The manifest is the single source of truth for name, role, timeout and retries —
    see AGENTS.md. Falls back to the literal list above if the document is unreadable,
    so a docs problem can never stop the orchestrator from running.
    """
    try:
        from app.agents import manifest
        fleet = manifest.load().fleet()
    except Exception as exc:                 # noqa: BLE001 — startup must not hard-fail
        logger.warning("fleet_manifest_unavailable", error=str(exc))
        fleet = []

    if fleet:
        for a in fleet:
            register(AgentSpec(name=a.agent, role=a.role,
                               timeout_s=a.timeout_s, retries=a.retries))
            # Register each alias as its own spec so a call under either spelling is
            # measured rather than silently creating an "unregistered" agent at runtime.
            for alias in a.aliases:
                register(AgentSpec(name=alias, role=a.role,
                                   timeout_s=a.timeout_s, retries=a.retries))
        logger.info("fleet_registered_from_manifest", agents=len(_registry))
        return

    logger.warning("fleet_registered_from_fallback", reason="AGENTS.md unavailable")
    for name, role, timeout in _FALLBACK_FLEET:
        register(AgentSpec(name=name, role=role, timeout_s=timeout))


# ── Execution wrapper ─────────────────────────────────────────────────────────
async def run_agent(
    name: str,
    coro_factory: Callable[[], Coroutine[Any, Any, Any]],
    *,
    timeout_s: float | None = None,
) -> tuple[bool, Any, dict]:
    """Run one agent call under orchestration.

    Returns (ok, result, meta). On failure result is None and meta["reason"]
    carries an honest, user-showable explanation. Never raises.
    """
    spec = _spec(name)
    st = _state[name]
    timeout = timeout_s or spec.timeout_s
    now = time.time()

    if now < st.breaker_open_until:
        remaining = int(st.breaker_open_until - now)
        st.last_status = "circuit_open"
        return False, None, {
            "agent": name, "status": "circuit_open",
            "reason": f"temporarily offline after repeated failures (retrying in {remaining}s)",
        }

    st.calls += 1
    st.last_run_at = now
    last_exc: str | None = None

    for attempt in range(spec.retries + 1):
        t0 = time.perf_counter()
        try:
            result = await asyncio.wait_for(coro_factory(), timeout=timeout)
            st.last_ms = round((time.perf_counter() - t0) * 1000, 1)
            st.successes += 1
            st.consecutive_failures = 0
            st.last_status = "ok"
            st.last_error = None
            return True, result, {"agent": name, "status": "ok", "ms": st.last_ms,
                                  "attempt": attempt + 1}
        except asyncio.TimeoutError:
            last_exc = f"timed out after {timeout:.0f}s"
        except Exception as exc:              # noqa: BLE001 — orchestration boundary
            # served by /api/orchestrator/status and job summaries — scrubbed at source
            from app.core.security import scrub_text
            last_exc = scrub_text(exc, limit=200) or exc.__class__.__name__
        logger.warning("agent_attempt_failed", agent=name, attempt=attempt + 1, error=last_exc)

    st.failures += 1
    st.consecutive_failures += 1
    st.last_status = "degraded"
    st.last_error = last_exc
    if st.consecutive_failures >= spec.breaker_threshold:
        st.breaker_open_until = time.time() + spec.breaker_cooldown_s
        logger.error("agent_circuit_opened", agent=name, cooldown_s=spec.breaker_cooldown_s)
    return False, None, {"agent": name, "status": "degraded", "reason": last_exc or "unknown failure"}


# ── Autonomous background loop ────────────────────────────────────────────────
_loop_state = {
    "running": False,
    "interval_s": 60,
    "ticks": 0,
    "last_tick_at": None,
    "last_refreshed": [],
    "last_sentinel_hits": 0,
    "last_error": None,
}
_loop_task: asyncio.Task | None = None


async def _autonomous_tick() -> None:
    """One tick: proactively refresh soon-to-expire products + Sentinel scan."""
    from app.services import product_store

    ok, refreshed, _ = await run_agent(
        "products",
        lambda: asyncio.to_thread(product_store.refresh_expiring, _loop_state["interval_s"] + 30),
    )
    _loop_state["last_refreshed"] = sorted(refreshed.keys()) if ok and refreshed else []

    async def _scan():
        from app.agents.sentinel_agent import scan_watches
        return await asyncio.to_thread(scan_watches)

    ok, hits, _ = await run_agent("sentinel", _scan)
    _loop_state["last_sentinel_hits"] = len(hits) if ok and hits else 0


async def _autonomous_loop(interval_s: int) -> None:
    _loop_state["running"] = True
    _loop_state["interval_s"] = interval_s
    while True:
        try:
            await _autonomous_tick()
            _loop_state["ticks"] += 1
            _loop_state["last_tick_at"] = time.time()
            _loop_state["last_error"] = None
        except asyncio.CancelledError:
            _loop_state["running"] = False
            raise
        except Exception as exc:             # noqa: BLE001 — loop must survive
            from app.core.security import scrub_text
            _loop_state["last_error"] = scrub_text(exc, limit=200) or exc.__class__.__name__
            logger.error("autonomous_tick_failed", error=str(exc))
        await asyncio.sleep(interval_s)


def start_autonomous(interval_s: int = 60) -> asyncio.Task:
    """Start the background loop (idempotent). Called from app lifespan."""
    global _loop_task
    if _loop_task is None or _loop_task.done():
        _loop_task = asyncio.create_task(_autonomous_loop(interval_s))
    return _loop_task


def stop_autonomous() -> None:
    global _loop_task
    if _loop_task is not None and not _loop_task.done():
        _loop_task.cancel()
    _loop_task = None
    _loop_state["running"] = False


# ── Telemetry / status ────────────────────────────────────────────────────────
def status() -> dict:
    now = time.time()
    agents = {}
    for name, spec in _registry.items():
        st = _state[name]
        agents[name] = {
            "role": spec.role,
            "timeout_s": spec.timeout_s,
            "calls": st.calls,
            "successes": st.successes,
            "failures": st.failures,
            "last_ms": st.last_ms,
            "last_status": st.last_status,
            "last_error": st.last_error,
            "circuit_open": now < st.breaker_open_until,
        }
    try:
        from app.agents import manifest
        man = manifest.status()
    except Exception as exc:                 # noqa: BLE001 — telemetry must not raise
        man = {"loaded": False, "errors": [exc.__class__.__name__]}
    if isinstance(man, dict) and man.get("errors"):
        from app.core.security import scrub_text
        man = {**man, "errors": [scrub_text(e) for e in man["errors"]]}
    return {"agents": agents, "autonomous": dict(_loop_state), "manifest": man}


def reset() -> None:
    """Test helper — clear all runtime state (registry survives)."""
    for name in list(_state):
        _state[name] = _AgentState()
    _loop_state.update({"ticks": 0, "last_tick_at": None, "last_refreshed": [],
                        "last_sentinel_hits": 0, "last_error": None})
