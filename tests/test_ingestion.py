"""
Tests for Data-Agnostic Ingestion
"""
import pytest
from app.services.ingestion import map_and_ingest_csv

def test_ingestion_csv_mapping():
    # Test a CSV with unknown headers
    csv_content = b"Event_Timestamp,X_Coord,Y_Coord,Offense_Desc,Precinct\n" \
                  b"2023-10-15T12:00:00,77.59,12.97,Robbery,Central\n"
                  
    res = map_and_ingest_csv(csv_content)
    
    assert res["status"] == "success"
    assert res["records_ingested"] == 1
    mapping = res["mapped_columns"]
    
    # We expect our heuristic to map correctly
    assert mapping["occurred_at"] == "Event_Timestamp"
    assert mapping["lng"] == "X_Coord"
    assert mapping["lat"] == "Y_Coord"
    assert mapping["crime_type"] == "Offense_Desc"
    assert mapping["zone"] == "Precinct"
