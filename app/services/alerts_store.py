"""
Antar — Alerts store (dev stand-in for the Catalyst `alerts` Data Store table)
===================================================================================
Durable: the list in memory is the hot copy, and every change is written through to a
small SQLite file of its own (`obs/alerts.db`, or ANTAR_ALERTS_DB), so a restart no longer
empties the Alerts screen until the next scan. It is kept apart from main.db on purpose:
alerts are derived, not FIR records. ANTAR_ALERTS=memory restores the old in-process
behaviour (the test suite uses it). Same shape as the `alerts` table (05_Backend_Schema §1)
so it still swaps to Data Store later with no caller change.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time

_alerts: list[dict] = []
_loaded = False
_db_lock = threading.Lock()
_db: sqlite3.Connection | None = None
_db_failed = False


def _store() -> sqlite3.Connection | None:
    """The alerts file, opened once. None when persistence is off or the file cannot be used
    (alerts then live in memory only, as they always did)."""
    global _db, _db_failed
    if _db is not None or _db_failed or (os.getenv("ANTAR_ALERTS") or "").lower() == "memory":
        return _db
    try:
        path = os.getenv("ANTAR_ALERTS_DB")
        if not path:
            from app.obs.config import OBS_DIR
            os.makedirs(OBS_DIR, exist_ok=True)
            path = str(OBS_DIR / "alerts.db")
        con = sqlite3.connect(path, check_same_thread=False, timeout=5)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("CREATE TABLE IF NOT EXISTS alerts (pos INTEGER PRIMARY KEY, data TEXT NOT NULL, saved_at REAL NOT NULL)")
        con.commit()
        _db = con
    except Exception:
        _db_failed = True
    return _db


def _ensure_loaded() -> None:
    """Read the saved set back once, on first use after a start."""
    global _alerts, _loaded
    if _loaded:
        return
    _loaded = True
    con = _store()
    if con is None:
        return
    try:
        with _db_lock:
            rows = con.execute("SELECT data FROM alerts ORDER BY pos").fetchall()
        _alerts = [json.loads(r[0]) for r in rows] + _alerts
    except Exception:
        pass


def _save() -> None:
    con = _store()
    if con is None:
        return
    try:
        now = time.time()
        rows = [(i, json.dumps(a, default=str, ensure_ascii=False), now) for i, a in enumerate(_alerts)]
        with _db_lock:
            con.execute("DELETE FROM alerts")
            con.executemany("INSERT INTO alerts (pos, data, saved_at) VALUES (?, ?, ?)", rows)
            con.commit()
    except Exception:
        pass          # a failed write must never break a scan; memory still has it


def replace_all(alerts: list[dict]) -> None:
    """A scan recomputes the whole picture, so replace the set (idempotent re-scan)."""
    global _alerts, _loaded
    _loaded = True
    _alerts = list(alerts)
    _save()


def list_recent(limit: int = 50) -> list[dict]:
    _ensure_loaded()
    return sorted(_alerts, key=lambda a: a.get("z_score", 0), reverse=True)[:limit]


def active_count() -> int:
    _ensure_loaded()
    return sum(1 for a in _alerts if a.get("status") == "new")


def clear() -> None:
    global _alerts, _loaded
    _loaded = True
    _alerts = []
    _save()


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
    _ensure_loaded()
    alert.setdefault("status", "new")
    _alerts = [a for a in _alerts if not _same(a, alert)]
    _alerts.insert(0, alert)
    _save()
    
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
