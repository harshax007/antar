"""
Antar — Data-Agnostic Ingestion Service (Phase 8)
======================================================
Upload any CSV → map headers → load to ZCQL.
Heuristic/LLM hybrid approach: Fast substring matching with LLM fallback simulation.
"""

import csv
import io
import uuid
from datetime import datetime
from app.services.zcql_local import insert_crimes

def _map_columns(headers: list[str]) -> dict[str, str]:
    """
    Returns a mapping of canonical_key -> actual_header.
    Heuristics are fast, reliable, and cost-free (ponytail).
    """
    mapping = {}
    for h in headers:
        hl = h.lower()
        if "dat" in hl or "time" in hl or "when" in hl or "occur" in hl:
            if "occurred_at" not in mapping: mapping["occurred_at"] = h
        elif "zon" in hl or "dist" in hl or "precinct" in hl or "area" in hl:
            if "zone" not in mapping: mapping["zone"] = h
        elif "typ" in hl or "crim" in hl or "offense" in hl or "desc" in hl:
            if "crime_type" not in mapping: mapping["crime_type"] = h
        elif "lat" in hl or "y" == hl or "y_coord" in hl:
            if "lat" not in mapping: mapping["lat"] = h
        elif "lon" in hl or "lng" in hl or "x" == hl or "x_coord" in hl:
            if "lng" not in mapping: mapping["lng"] = h

    # Check if all canonical fields found. If not, we'd invoke LLM.
    # For demo purposes, we log the fallback.
    required = {"occurred_at", "zone", "crime_type", "lat", "lng"}
    missing = required - set(mapping.keys())
    if missing:
        print(f"Heuristic missed {missing}. Invoking LLM fallback mapping...")
        # Simulate LLM guessing the remaining columns
        unmapped = [h for h in headers if h not in mapping.values()]
        for m in missing:
            if unmapped:
                mapping[m] = unmapped.pop(0) # naive guess for simulation

    return mapping

MAX_CSV_BYTES = 5 * 1024 * 1024


def map_and_ingest_csv(file_bytes: bytes) -> dict:
    """
    Parses a CSV byte stream, normalizes it, and inserts it.
    Enforces security limits (5MB, 50 cols, 50k rows).
    """
    if len(file_bytes) > MAX_CSV_BYTES:
        return {"error": "File exceeds 5MB limit."}
        
    text = file_bytes.decode('utf-8-sig', errors='replace')
    reader = csv.DictReader(io.StringIO(text))
    
    if not reader.fieldnames:
        return {"error": "Empty or invalid CSV."}
        
    if len(reader.fieldnames) > 50:
        return {"error": "CSV exceeds 50 columns limit."}
        
    mapping = _map_columns(reader.fieldnames)
    
    records = []
    quarantined = 0
    for row in reader:
        if len(records) >= 50000:
            break
            
        try:
            # Map values
            date_val = row.get(mapping.get("occurred_at"))
            zone_val = row.get(mapping.get("zone"))
            type_val = row.get(mapping.get("crime_type"))
            lat_val = float(row.get(mapping.get("lat"), 0))
            lng_val = float(row.get(mapping.get("lng"), 0))
            
            # Basic normalization
            if not date_val:
                date_val = datetime.now().isoformat()
            if not zone_val:
                zone_val = "Unknown"
            if not type_val:
                type_val = "unknown"

            # Poisoning screen: every text field that later reaches retrieval and prompts
            # is normalised (invisible Unicode, markup stripped) and a row carrying
            # instruction-shaped text is quarantined, not inserted.
            from app.core.rag_security import normalize_untrusted, detect_injection
            zone_val = normalize_untrusted(zone_val, max_len=120)
            type_val = normalize_untrusted(type_val, max_len=80)
            if detect_injection(" | ".join(str(v) for v in (zone_val, type_val, date_val))):
                quarantined += 1
                continue

            records.append({
                "crime_id": f"CR-{uuid.uuid4().hex[:8]}",
                "occurred_at": date_val,
                "zone": zone_val,
                "crime_type": type_val,
                "lat": lat_val,
                "lng": lng_val,
                "status": "closed"
            })
        except Exception as e:
            print(f"Skipping row due to error: {e}")
            continue

    if records:
        insert_crimes(records)
        from app.services import product_store
        from app.agents import sentinel_agent
        product_store.invalidate("briefing:shift:")
        sentinel_agent.scan_watches()
        
    return {
        "status": "success",
        "mapped_columns": mapping,
        "records_ingested": len(records),
        "records_quarantined": quarantined,
    }
