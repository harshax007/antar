"""
Antar — Alerts API (M8 / F4)
=================================
GET  /api/alerts        → latest alerts (incl. z-score + brain match)   [Inspector+]
POST /api/alerts/scan   → run the Forecast Agent Z-scan → {created}     [Cron secret header]

RBAC + the Cron secret-header check are enforced in Phase 6 (auth_middleware); open in
local dev. The "Run scan now" Admin button hits the same /scan path (demo insurance #3).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from app.core.auth_middleware import require_cron_secret

from app.agents import forecast_agent
from app.services import alerts_store

router = APIRouter()


@router.get("")
@router.get("/")
async def list_alerts(limit: int = 50) -> dict:
    alerts = alerts_store.list_recent(limit)
    
    # Enrich with event context and suggestions on the fly
    from app.services.events import get_events_for_date
    from datetime import datetime
    
    current_date = datetime.now().isoformat()
    for a in alerts:
        zone = a.get("zone", "All")
        crime_type = a.get("crime_type", "unknown")
        events = get_events_for_date(current_date, zone)
        
        suggestion = f"Monitor {zone} for {crime_type}. "
        if events:
            for e in events:
                if crime_type.lower() in e["risk_types"] or crime_type == "unknown":
                    a["event_context"] = e["name"]
                    break
            if a.get("event_context"):
                suggestion = f"{a['event_context']} + {crime_type} anomaly → Saturate {zone} with targeted patrols."
        a["suggestion"] = suggestion

    return {"alerts": alerts, "active": alerts_store.active_count()}


@router.post("/scan", dependencies=[Depends(require_cron_secret)])
@router.post("/scan/", dependencies=[Depends(require_cron_secret)])
async def scan_alerts() -> dict:
    return forecast_agent.scan()
