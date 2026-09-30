"""
Antar — Pattern Analyst Agent (A7)
=======================================
Agent responsible for discovering spatiotemporal clusters and MO signatures.
"""

import asyncio

from app.services.zcql_local import scan_rows as _scan_rows
from app.services.patterns import find_clusters


def _scan_and_cluster(crime_type, period):
    return find_clusters(_scan_rows(crime_type, period))


async def pattern_agent_run(user_text: str, params: dict) -> dict:
    """
    Called by the agentic spine when intent is 'pattern'.
    """
    ct = params.get("crime_types", [])
    period = params.get("period")
    crime_type = ct[0] if ct else None

    # The scan + clustering is seconds of synchronous CPU/SQLite work. Run inline it froze
    # the event loop, so the NEXT chat question waited ~6s before its first SSE step.
    clusters = await asyncio.to_thread(_scan_and_cluster, crime_type, period)

    return {
        "clusters": clusters,
        "summary": f"Found {len(clusters)} active spatiotemporal clusters." if clusters else "No active clusters found."
    }
