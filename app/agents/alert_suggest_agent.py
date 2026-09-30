"""
Antar — Alert & Suggestion Agent (A10) (Phase 7)
=====================================================
Fuses statistical anomalies with event context to provide actionable suggestions.
"""

from app.agents.forecast_agent import scan
from app.services.events import get_events_for_date
from datetime import datetime

async def alert_suggest_agent_run(user_text: str, params: dict) -> dict:
    """
    Called when user intent is related to alerts, deployment, or suggestions.
    """
    # 1. Fetch raw anomalies
    forecast_res = scan(session_id="alert_suggest")
    alerts = forecast_res.get("alerts", [])
    
    # 2. Fetch context
    current_date = datetime.now().isoformat()
    # We will enrich each alert
    enriched_alerts = []
    
    for a in alerts:
        zone = a.get("zone", "All")
        crime_type = a.get("crime_type", "unknown")
        z_score = a.get("z_score", 0)
        
        events = get_events_for_date(current_date, zone)
        
        # Build the fused suggestion
        suggestion = f"Monitor {zone} for {crime_type} (Z-score: {z_score}). "
        event_context = None
        
        if events:
            # Find an event that has related risk types
            for e in events:
                if crime_type.lower() in e["risk_types"] or crime_type == "unknown":
                    event_context = e["name"]
                    break
            
            if event_context:
                suggestion = f"{event_context} + {crime_type} anomaly → Saturate {zone} with targeted patrols."
            else:
                suggestion += f"Note: {events[0]['name']} is upcoming in this zone."
                
        # If brain match exists, incorporate it
        if a.get("brain_match_summary"):
            suggestion += f" Brain context: {a['brain_match_summary']}."
            
        enriched_alerts.append({
            "alert_id": a.get("alert_id"),
            "zone": zone,
            "crime_type": crime_type,
            "z_score": z_score,
            "brain_match_summary": a.get("brain_match_summary"),
            "event_context": event_context,
            "suggestion": suggestion
        })

    summary = f"Generated {len(enriched_alerts)} actionable deployment suggestions."
    if enriched_alerts:
        summary += f" Top alert: {enriched_alerts[0]['suggestion']}"

    return {
        "alerts": enriched_alerts,
        "summary": summary
    }
