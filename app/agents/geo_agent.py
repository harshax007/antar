"""
Antar — Geo-Intelligence Agent
===================================
A parallel agent invoked during orchestration to fetch geospatial contexts
for the interactive map overlay.
"""

from app.services.geo_density import compute_heat, compute_flow, predict_hotspots
from app.services.zcql_local import USE_LOCAL, _world, scan_rows as _scan_rows

async def geo_agent_run(user_text: str, params: dict) -> dict:
    """
    Called by the agentic spine when the intent requires geo-intelligence.
    Uses the parsed query parameters to compute heat, flow, and predicted.
    """
    ct = params.get("crime_types", [])
    period = params.get("period")
        
    crime_type = ct[0] if ct else None
    
    rows = _scan_rows(crime_type, period)
    
    heat_data = compute_heat(rows)
    
    if USE_LOCAL:
        cs = _world().get("crime_suspects", [])
    else:
        from app.core.catalyst import zcql_query
        try:
            cs = zcql_query("SELECT crime_id, suspect_id FROM crime_suspects")
        except Exception:
            cs = []
            
    from app.services.geo_density import compute_kde_geojson
    flow_data = compute_flow(rows, cs)
    pred_data, sugg_data = predict_hotspots(rows)
    contours = compute_kde_geojson(rows)
    
    return {
        "heat": heat_data,
        "flow": flow_data,
        "predicted": pred_data,
        "beat_suggestions": sugg_data,
        "contours": contours
    }
