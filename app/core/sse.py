"""
Antar — SSE utilities
===========================
Tiny helpers for Server-Sent Events responses.

Event format (spec-compliant, no extra package needed):
    data: <json>\n\n

Each event dict must have a "type" field. The frontend switches on type:
    step        — agent progress bar update
    token       — single answer word/chunk for typewriter effect
    citations   — citation chip array
    brain_hits  — Second Brain match array
    visual      — keyed visual payload (graph / map / predict)
    confidence  — calibrated confidence breakdown
    actions     — suggested action buttons
    suggested   — follow-up question chips
    complete    — final merged payload (session_id, template_id, mode, …)
    error       — something went wrong; streaming stops
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator


def sse_event(event_type: str, **kwargs: Any) -> str:
    """Format one SSE message: ``data: {...}\\n\\n``."""
    return f"data: {json.dumps({'type': event_type, **kwargs}, ensure_ascii=False)}\n\n"


def sse_heartbeat() -> str:
    """Keep-alive comment line (invisible to the client)."""
    return ": heartbeat\n\n"


class SSEQueue:
    """Async queue bridge between the pipeline coroutine and the SSE generator.

    Usage:
        q = SSEQueue()
        asyncio.create_task(pipeline(q.emit))
        async for line in q:
            yield line
    """

    def __init__(self, maxsize: int = 256) -> None:
        self._q: asyncio.Queue[str | None] = asyncio.Queue(maxsize=maxsize)

    async def emit(self, event_type: str, **kwargs: Any) -> None:
        await self._q.put(sse_event(event_type, **kwargs))

    async def close(self) -> None:
        await self._q.put(None)   # sentinel

    def __aiter__(self) -> "SSEQueue":
        return self

    async def __anext__(self) -> str:
        item = await self._q.get()
        if item is None:
            raise StopAsyncIteration
        return item


async def token_stream(text: str, delay_s: float = 0.002) -> AsyncGenerator[str, None]:
    """Split *text* into word-level chunks and yield each with ultra-low latency.

    2 ms/word ≈ 500 words/second — crisp, fast typewriter effect with zero sluggishness.
    """
    words = text.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == 0 else " " + word
        yield chunk
        if delay_s > 0:
            await asyncio.sleep(delay_s)


