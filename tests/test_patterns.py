"""
Tests for Phase 5 Pattern & Predict services.
"""
from app.services.patterns import find_clusters, predict_risk

def test_find_clusters():
    rows = [
        {"lat": 12.971, "lon": 77.594, "zone": "Central", "crime_type": "theft", "occurred_at": "2023-01-01"},
        {"lat": 12.972, "lon": 77.595, "zone": "Central", "crime_type": "theft", "occurred_at": "2023-01-02"},
        {"lat": 12.971, "lon": 77.593, "zone": "Central", "crime_type": "robbery", "occurred_at": "2023-01-03"},
        # Distant point
        {"lat": 13.500, "lon": 78.000, "zone": "North", "crime_type": "theft", "occurred_at": "2023-01-01"}
    ]
    
    # eps=0.02 should group the first three
    clusters = find_clusters(rows, eps=0.02, min_samples=3)
    assert len(clusters) == 1
    c = clusters[0]
    assert c["size"] == 3
    assert "Central" in c["zones"]
    assert "theft" in c["crime_types"]
    assert "robbery" in c["crime_types"]
    
def test_predict_risk():
    rows = []
    # 20 recent cases, 10 prior cases -> trend up
    for i in range(20):
        rows.append({"zone": "Z1", "crime_type": "theft", "lat": 12.0+i*0.0001, "lon": 77.0, "occurred_at": "2023-12-15T10:00:00"})
    for i in range(10):
        rows.append({"zone": "Z1", "crime_type": "theft", "lat": 12.0+i*0.0001, "lon": 77.0, "occurred_at": "2023-11-10T10:00:00"})
        
    pred = predict_risk("Z1", "theft", rows)
    assert pred["zone"] == "Z1"
    assert pred["crime_type"] == "theft"
    assert pred["risk"] in ("Critical", "High")
    # v2 trace uses Phase 7 Entropy / Transformer strings
    assert "52-week Sequence" in pred["trace"][0]["description"]
    assert "total_cases=30" in pred["trace"][0]["data_refs"]
