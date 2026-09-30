"""
Tests for Phase 4 Geo-Intelligence (M7 Validation).
"""
import pytest
from app.services.geo_density import compute_heat, compute_flow, predict_hotspots

def test_compute_heat():
    rows = [
        {"lat": 12.97, "lon": 77.59},
        {"lat": 12.97, "lon": 77.59},
        {"lat": 12.98, "lon": 77.60},
        {"no_coords": True}
    ]
    heat = compute_heat(rows)
    assert len(heat) == 2
    # Binned exact matches should sum their weights
    binned_1297 = next(h for h in heat if h["lat"] == 12.97)
    assert binned_1297["weight"] == 2


def test_compute_flow():
    rows = [
        {"crime_id": "C1", "lat": 10.0, "lon": 20.0, "occurred_at": "2023-01-01T10:00:00"},
        {"crime_id": "C2", "lat": 10.1, "lon": 20.1, "occurred_at": "2023-01-02T10:00:00"},
        {"crime_id": "C3", "lat": 10.2, "lon": 20.2, "occurred_at": "2023-01-03T10:00:00"},
        {"crime_id": "C_NO_SUSPECT", "lat": 10.3, "lon": 20.3, "occurred_at": "2023-01-04"},
    ]
    crime_suspects = [
        {"crime_id": "C1", "suspect_id": "S1"},
        {"crime_id": "C2", "suspect_id": "S1"},
        {"crime_id": "C3", "suspect_id": "S2"},
    ]
    flow = compute_flow(rows, crime_suspects)
    
    # Only S1 has >= 2 crimes
    assert len(flow) == 1
    f = flow[0]
    assert f["suspect_id"] == "S1"
    assert len(f["path"]) == 2
    assert f["path"][0]["lat"] == 10.0
    assert f["path"][1]["lat"] == 10.1


def test_predict_hotspots():
    rows = [
        {"zone": "Rajajinagar", "lat": 12.0, "lon": 77.0, "occurred_at": "2023-12-15T00:00"},
        {"zone": "Rajajinagar", "lat": 12.0, "lon": 77.0, "occurred_at": "2023-12-14T00:00"},
        {"zone": "Indiranagar", "lat": 12.1, "lon": 77.1, "occurred_at": "2023-12-15T00:00"},
        {"zone": "Old", "lat": 12.2, "lon": 77.2, "occurred_at": "2022-01-01T00:00"}, # Too old, filtered
    ]
    pred, sugg = predict_hotspots(rows)
    
    assert len(pred) == 1
    assert pred[0]["zone"] == "Rajajinagar"
    assert pred[0]["risk"] == "High"
    
    assert len(sugg) == 1
    assert sugg[0]["zone"] == "Rajajinagar"
    assert "Saturate patrols" in sugg[0]["suggestion"]
