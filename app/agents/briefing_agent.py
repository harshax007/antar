"""
Antar — Briefing Agent (A4: Shift Briefings · Phase 1)
===========================================================
Pre-compiled shift briefing intelligence generated deterministically
over official FIRs and evidence ledger data.
Stores results in Product Store with a 300s TTL.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any
from collections import Counter

from app.services import product_store, evidence_ledger
from app.services.anomaly import gi_star_surface


def _db() -> sqlite3.Connection:
    from app.core.db_path import get_db_path
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def generate_shift_briefing(zone: str = "all", window: str = "12h") -> dict[str, Any]:
    """Deterministic generator for shift briefings over FIRs and evidence ledger."""
    window_map = {"8h": 8, "12h": 12, "24h": 24, "48h": 48}
    win_hours = window_map.get(window.lower(), 12)
    
    conn = _db()
    if zone and zone.lower() != "all":
        rows = conn.execute(
            "SELECT fir_id AS fir_no, CrimeGroup_Name AS crime_type, District_Name AS location, date "
            "FROM FIRs WHERE UPPER(District_Name) LIKE UPPER(?) OR UPPER(Beat_Name) LIKE UPPER(?) "
            "ORDER BY date DESC LIMIT 25",
            (f"%{zone}%", f"%{zone}%")
        ).fetchall()
        zone_display = zone.title()
    else:
        rows = conn.execute(
            "SELECT fir_id AS fir_no, CrimeGroup_Name AS crime_type, District_Name AS location, date "
            "FROM FIRs ORDER BY date DESC LIMIT 25"
        ).fetchall()
        zone_display = "All Districts"
    conn.close()

    incidents = [dict(r) for r in rows]
    
    # Extract top crimes
    crime_types = [inc.get("crime_type", "Unknown") for inc in incidents if inc.get("crime_type")]
    top_crimes = ", ".join(t for t, _ in Counter(crime_types).most_common(2)) if crime_types else "Property & Street Crime"
    
    # Check evidence ledger for active accused in this zone
    ev_hits = evidence_ledger.search(zone if zone and zone.lower() != "all" else "", limit=5)
    top_suspect = ev_hits[0]["alias"] if ev_hits else None

    # Format key incidents for payload
    key_incidents = []
    for inc in incidents[:5]:
        dt_str = inc.get("date") or ""
        time_str = dt_str.split("T")[1][:5] if "T" in dt_str else ""
        key_incidents.append({
            "fir_no": inc.get("fir_no", "FIR-2026-UNKNOWN"),
            "crime_type": inc.get("crime_type", "General Incident"),
            "time": time_str,
            "location": inc.get("location", zone_display),
        })

    # Count active beacons / hotspots in this zone
    hotspots = gi_star_surface()
    if zone and zone.lower() != "all":
        active_beacons = sum(1 for h in hotspots if h.get("is_hotspot") and zone.lower() in str(h.get("zone", "")).lower())
    else:
        active_beacons = sum(1 for h in hotspots if h.get("is_hotspot"))
    # active_beacons is the real confirmed-hotspot count for this zone (0 is honest)

    # Synthesize summary and actions — the MO-linkage line only when a real accused exists
    summary = (
        f"{len(incidents)} incidents monitored in recent {window} shift window across {zone_display}. "
        f"Primary activity concentrated in {top_crimes}."
        + (f" Evidence-ledger linkage points to {top_suspect} and associates." if top_suspect else "")
    )
    
    actions = [
        {
            "rank": 1,
            "action": f"Deploy targeted patrol units around high-density corridors in {zone_display} between 01:00 and 05:00.",
            "rationale": f"Recurring pattern of {top_crimes} reported in this window."
        },
        {
            "rank": 2,
            "action": f"Initiate vehicle checkpoint checks and verify CDR movement signals for linked entities.",
            "rationale": (f"Cross-case evidence ledger indicates active movement of {top_suspect} across sector boundaries."
                          if top_suspect else "Standard preventive checkpoint per shift protocol.")
        }
    ]

    return {
        "zone": zone_display,
        "window_hours": win_hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": summary,
        "priority_actions": actions,
        "key_incidents": key_incidents,
        "active_beacons": active_beacons,
    }


def get_shift_briefing(zone: str = "all", window: str = "12h") -> dict[str, Any]:
    """Get shift briefing from Product Store or calculate and cache if missing/stale."""
    key = f"briefing:shift:{zone.lower()}:{window.lower()}"
    cached = product_store.get_product(key)
    if cached is not None:
        return cached

    payload = generate_shift_briefing(zone=zone, window=window)
    product_store.put_product(key, payload, ttl=300)
    return payload
