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

    # No named subject, no search. This used to take the first capitalised word of the
    # sentence and search the open web for it - a guess that sends a word of an officer's
    # question outside the building and can attach a stranger to a police work product
    # (AGENTS.md, osint: "refuses without a named subject").
    if not entity_name:
        return {"summary": "No specific name found to perform OSINT.", "claims": []}

    result = await search_osint(entity_name)
    return result
