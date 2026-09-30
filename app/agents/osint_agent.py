"""
Antar — OSINT Agent (A6)
=============================
Agent responsible for retrieving quarantined open-web intelligence.
"""

from app.services.osint import search_osint

async def osint_agent_run(user_text: str, params: dict) -> dict:
    """
    Called by the agentic spine to pull open web intelligence.
    """
    # The entity might be extracted in 'suspects' or 'persons' parameter.
    suspects = params.get("suspects", [])
    entity_name = suspects[0] if suspects else None
    
    # If no suspect was explicitly parsed, see if there's a raw string we can guess
    if not entity_name:
        words = user_text.split()
        for w in words:
            if w.istitle() and len(w) > 3:
                entity_name = w
                break
                
    if not entity_name:
        return {"summary": "No specific name found to perform OSINT.", "claims": []}

    result = await search_osint(entity_name)
    return result
