"""
Antar — Offline Forensics Parser
=====================================
Parses offline digital forensics reports (e.g., Cellebrite UFDR JSON exports).
Extracts nodes (Contacts) and relationships (SMS/Calls) for ingestion.
"""

import json

def parse_cellebrite_json(filepath: str) -> dict:
    """
    Parses a simulated Cellebrite JSON export.
    Returns structured data ready for Antar DB ingestion.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading forensics file {filepath}: {e}")
        return {"nodes": [], "relationships": []}
    
    nodes = []
    relationships = []

    # 1. Extract Contacts (Nodes)
    contacts = data.get("contacts", [])
    for c in contacts:
        # Cellebrite often has multiple numbers per contact
        primary_phone = c.get("phone_numbers", [""])[0] if c.get("phone_numbers") else ""
        nodes.append({
            "type": "contact",
            "name": c.get("name", "Unknown"),
            "phone": primary_phone,
            "source": "Cellebrite_Extraction"
        })

    # 2. Extract Messages/Calls (Relationships)
    messages = data.get("messages", [])
    for m in messages:
        sender = m.get("from")
        receiver = m.get("to")
        if sender and receiver:
            relationships.append({
                "type": "communication",
                "suspect_a": sender,
                "suspect_b": receiver,
                "timestamp": m.get("timestamp"),
                "content": m.get("body", ""),
                "source": "Cellebrite_Extraction"
            })

    # 3. Extract GPS Locations (Nodes/Events)
    locations = data.get("locations", [])
    for loc in locations:
        nodes.append({
            "type": "location",
            "lat": loc.get("lat"),
            "lon": loc.get("lon"),
            "timestamp": loc.get("timestamp"),
            "source": "Cellebrite_Extraction"
        })

    return {
        "nodes": nodes,
        "relationships": relationships
    }
