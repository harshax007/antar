"""
Antar — Alerts store (dev stand-in for the Catalyst `alerts` Data Store table)
===================================================================================
In-memory now (resets on restart; a scan repopulates). Same shape as the `alerts`
table (05_Backend_Schema §1) so it swaps to Data Store later with no caller change.
"""

from __future__ import annotations

_alerts: list[dict] = []


def replace_all(alerts: list[dict]) -> None:
    """A scan recomputes the whole picture, so replace the set (idempotent re-scan)."""
    global _alerts
    _alerts = list(alerts)


def list_recent(limit: int = 50) -> list[dict]:
    return sorted(_alerts, key=lambda a: a.get("z_score", 0), reverse=True)[:limit]


def active_count() -> int:
    return sum(1 for a in _alerts if a.get("status") == "new")


def clear() -> None:
    global _alerts
    _alerts = []


def _same(a: dict, b: dict) -> bool:
    """One standing condition, however often it is re-detected: the same watch, or the
    same kind of alert on the same area and crime."""
    if a.get("watch_id") or b.get("watch_id"):
        return a.get("watch_id") == b.get("watch_id")
    return all(a.get(k) == b.get(k) for k in ("alert_type", "zone", "crime_type"))


def add_alert(alert: dict) -> None:
    """Add a single alert (e.g. from Sentinel tripwire).

    A watch that is still tripped is re-detected on every scan. Each scan used to add a
    fresh copy, so one watch filled the list (44 of 50 alerts were three watches). A
    repeat now replaces the alert it repeats, refreshed and moved to the top.
    """
    global _alerts
    alert.setdefault("status", "new")
    _alerts = [a for a in _alerts if not _same(a, alert)]
    _alerts.insert(0, alert)
    
    # Proactively push alert to live_stream WebSockets
    try:
        import asyncio
        from app.api.live_stream import broadcast_event
        ws_event = {
            "type": "emergency_dispatch",
            "timestamp": alert.get("timestamp"),
            "crime_type": alert.get("crime_type", "SYSTEM_ALERT"),
            "zone": alert.get("zone", "System"),
            "message": alert.get("message", "New proactive alert triggered."),
            "dispatch_status": alert.get("severity", "high")
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(broadcast_event(ws_event))
        except RuntimeError:
            # If no running loop, we can't easily push. Safe fallback.
            pass
    except Exception as e:
        print(f"Failed to push alert to websocket: {e}")
