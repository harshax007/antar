# Antar - Reasoning Logger
# Every agent appends a step here. "why?" replays this - the Explain capability (M9).

import time
import structlog

log = structlog.get_logger()


def log_step(session_id, agent, step, input_digest, output_digest, ms):
    entry = {
        "session_id": session_id,
        "agent": agent,
        "step": step,
        "input_digest": str(input_digest)[:120],
        "output_digest": str(output_digest)[:120],
        "ms": ms,
        "ts": int(time.time() * 1000),
    }
    log.info("agent_step", **entry)
    
    from app.obs import trace as _obs
    _obs.add_span(agent, step, input_digest, output_digest, ms)
    
    # Broadcast step via WebSocket if loop is running
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            from app.api.live_stream import broadcast_reasoning_step
            loop.create_task(broadcast_reasoning_step(entry))
    except RuntimeError:
        pass
        


async def get_reasoning_log(session_id):
    """The stored reasoning trail for a session, or an empty list.

    This used to return a HARDCODED step —
    `{"agent": "supervisor", "step": "intent_classification", "note": "Phase 1: wired to
    NoSQL"}` — for any session id, including ones that never existed. A fabricated
    reasoning trail is the worst possible thing for this system to invent: the trail is the
    evidence that an answer came from the record, and a fake one is a lie about how a
    police answer was reached. It had no callers, which is the only reason it never
    surfaced.

    The live trail is kept per session by `app/core/sessions.py` and replayed by the
    EXPLAIN route; read it from there. Returning nothing is the honest answer here.
    """
    try:
        from app.core import sessions
        return sessions.last_reasoning(session_id) or []
    except Exception:                       # noqa: BLE001 — a trail read must not raise
        return []
