"""
Antar — Officer Long-Term Memory & Identity Store (SQLite)
============================================================
Persists officer profiles, preferences, bookmarked evidence/suspects, and
compressed prior session conclusions in `officer_memory` inside `main.db`.
Provides demo login identity out of the box for officers across ranks.
"""

from __future__ import annotations
import json
import time
import sqlite3
from typing import Any

from app.core.db_path import DB_PATH


def init_memory_db() -> None:
    """Initialize officer_memory table and seed demo login identities."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS officer_memory (
            officer_id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            full_name TEXT NOT NULL,
            station TEXT NOT NULL,
            preferences TEXT NOT NULL,
            conclusions TEXT NOT NULL,
            bookmarks TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """)
        
        # Seed default demo officers if not present
        demo_officers = [
            (
                "OF-1001", "Inspector", "Ramesh K.", "Rajajinagar PS",
                json.dumps({"lang": "en", "theme": "dark", "default_zone": "West", "expert_mode": True}),
                json.dumps([
                    "2026-07-14: Identified chain snatching surge in Rajajinagar linked to morning peak hours (06:00-08:30).",
                    "2026-07-12: Cross-referenced Raju K. (S0001) alias Yellappa across multiple property crimes."
                ]),
                json.dumps([{"type": "suspect", "id": "S0001", "name": "Raju K. (Yellappa)"}, {"type": "zone", "id": "Rajajinagar"}]),
                int(time.time())
            ),
            (
                "OF-1002", "Superintendent", "Priya S.", "Bengaluru City HQ",
                json.dumps({"lang": "en", "theme": "dark", "default_zone": "All Bengaluru", "expert_mode": True}),
                json.dumps([
                    "2026-07-15: Approved city-wide shift briefing adjustment for chain snatching hotspots."
                ]),
                json.dumps([{"type": "zone", "id": "West"}, {"type": "zone", "id": "South"}]),
                int(time.time())
            ),
            (
                "OF-1003", "Constable", "Kumar V.", "Whitefield PS",
                json.dumps({"lang": "kn", "theme": "dark", "default_zone": "East", "expert_mode": False}),
                json.dumps([]),
                json.dumps([{"type": "zone", "id": "Whitefield"}]),
                int(time.time())
            )
        ]
        
        for row in demo_officers:
            conn.execute("""
            INSERT OR IGNORE INTO officer_memory (officer_id, role, full_name, station, preferences, conclusions, bookmarks, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, row)
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing officer_memory DB: {e}")


def get_officer_memory(officer_id: str) -> dict[str, Any]:
    """Retrieve full memory profile for an officer, falling back to clean default if not found."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT officer_id, role, full_name, station, preferences, conclusions, bookmarks, updated_at FROM officer_memory WHERE officer_id = ?", (officer_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "officer_id": row[0],
                "role": row[1],
                "full_name": row[2],
                "station": row[3],
                "preferences": json.loads(row[4] or "{}"),
                "conclusions": json.loads(row[5] or "[]"),
                "bookmarks": json.loads(row[6] or "[]"),
                "updated_at": row[7]
            }
    except Exception as e:
        print(f"Error fetching officer memory for {officer_id}: {e}")
        
    # Default fallback
    return {
        "officer_id": officer_id or "OF-1001",
        "role": "Inspector",
        "full_name": "Officer",
        "station": "Bengaluru PS",
        "preferences": {"lang": "en", "theme": "dark", "expert_mode": True},
        "conclusions": [],
        "bookmarks": [],
        "updated_at": int(time.time())
    }


def list_officers() -> list[dict[str, Any]]:
    """List all registered officers for the demo login switcher."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT officer_id, role, full_name, station, preferences FROM officer_memory ORDER BY officer_id")
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "officer_id": r[0],
                "role": r[1],
                "full_name": r[2],
                "station": r[3],
                "preferences": json.loads(r[4] or "{}")
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Error listing officers: {e}")
        return []


def update_officer_preferences(officer_id: str, preferences: dict[str, Any]) -> None:
    """Update officer UI and analytical preferences."""
    try:
        cur = get_officer_memory(officer_id)
        cur_prefs = cur.get("preferences", {})
        cur_prefs.update(preferences)
        
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE officer_memory SET preferences = ?, updated_at = ? WHERE officer_id = ?",
                     (json.dumps(cur_prefs), int(time.time()), officer_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating preferences for {officer_id}: {e}")


def add_officer_conclusion(officer_id: str, conclusion_text: str) -> None:
    """Append a compressed analytical conclusion from a completed investigation turn or job."""
    if not conclusion_text or not conclusion_text.strip():
        return
    try:
        cur = get_officer_memory(officer_id)
        conclusions = cur.get("conclusions", [])
        # Keep latest 15 conclusions
        conclusions = [conclusion_text.strip()] + [c for c in conclusions if c != conclusion_text.strip()][:14]
        
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE officer_memory SET conclusions = ?, updated_at = ? WHERE officer_id = ?",
                     (json.dumps(conclusions), int(time.time()), officer_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error adding conclusion for {officer_id}: {e}")


def toggle_officer_bookmark(officer_id: str, item: dict[str, Any]) -> list[dict[str, Any]]:
    """Add or remove an item (suspect, zone, FIR, alert) from officer bookmarks."""
    try:
        cur = get_officer_memory(officer_id)
        bookmarks = cur.get("bookmarks", [])
        
        item_id = item.get("id")
        existing_idx = next((i for i, b in enumerate(bookmarks) if b.get("id") == item_id and b.get("type") == item.get("type")), None)
        if existing_idx is not None:
            bookmarks.pop(existing_idx)
        else:
            bookmarks.insert(0, item)
            bookmarks = bookmarks[:25]
            
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE officer_memory SET bookmarks = ?, updated_at = ? WHERE officer_id = ?",
                     (json.dumps(bookmarks), int(time.time()), officer_id))
        conn.commit()
        conn.close()
        return bookmarks
    except Exception as e:
        print(f"Error toggling bookmark for {officer_id}: {e}")
        return []
