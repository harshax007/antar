"""
Antar — Event Calendar Service (Phase 7)
=============================================
Maps dates/zones to known local events (festivals, sports, politics)
to provide context for anomalies.
"""

from datetime import datetime, timedelta

# Static mock calendar for the Datathon (Ponytail approach for deterministic demos)
# Dates are left slightly generic (month/day) or specific to the demo's 2023-2026 range.
MOCK_EVENTS = [
    {"name": "Dasara Festival", "month": 10, "zones": ["All", "Mysuru", "Central"], "risk_types": ["theft", "chain snatching", "robbery"]},
    {"name": "Diwali Festivities", "month": 11, "zones": ["All"], "risk_types": ["theft", "burglary"]},
    {"name": "New Year's Eve", "month": 12, "day": 31, "zones": ["Central", "Indiranagar", "Koramangala"], "risk_types": ["assault", "theft", "dui"]},
    {"name": "IPL Match at Chinnaswamy", "month": 4, "zones": ["Central", "Cubbon Park"], "risk_types": ["theft", "vandalism", "assault"]},
    {"name": "Election Rally", "month": 5, "zones": ["North", "South"], "risk_types": ["riot", "assault", "vandalism"]}
]

def get_events_for_date(target_date_str: str = None, zone: str = None) -> list[dict]:
    """
    Returns relevant upcoming or ongoing events for a given date and zone.
    """
    try:
        if target_date_str:
            dt = datetime.fromisoformat(target_date_str[:10])
        else:
            dt = datetime.now()
    except ValueError:
        dt = datetime.now()

    matched = []
    for evt in MOCK_EVENTS:
        # Check month match (simplistic window)
        if evt["month"] == dt.month or evt["month"] == (dt + timedelta(days=7)).month:
            # Check zone match if requested
            if not zone or "All" in evt["zones"] or zone in evt["zones"]:
                matched.append(evt)
                
    return matched
