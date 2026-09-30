"""
Layer 6 Verification Tests — Geospatial Intelligence (Map & Anchor Areas)
=============================================================================
Tests:
  1. UNSUB Anchor Areas: 2D monotone chain convex hull & haversine radius property
  2. Dark-Zone Surface: coverage formula & monotonicity property
  3. District Cache Enrichment: open_unsubs_count & gap_count presence
  4. FastAPI Endpoints: /api/map/darkzones & /api/map/anchor_areas contract
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.services.geo_density import (
    compute_unsub_anchor_areas,
    compute_dark_zones,
    _haversine_km,
    _convex_hull_2d,
)
from app.services import district_cache

client = TestClient(app)


def test_convex_hull_2d_and_haversine():
    # Square with a center point
    points = [
        (12.90, 77.50),
        (12.90, 77.60),
        (13.00, 77.60),
        (13.00, 77.50),
        (12.95, 77.55),  # center point inside square
    ]
    hull = _convex_hull_2d(points)
    assert len(hull) >= 4, "Square convex hull should have at least 4 vertices"

    dist = _haversine_km(12.9716, 77.5946, 12.9716, 77.6046)
    assert 1.0 < dist < 1.2, f"Haversine distance for 0.01 degree lon should be ~1.1 km, got {dist}"


def test_compute_unsub_anchor_areas_property():
    rows = [
        {"District_Name": "Bengaluru Urban", "lat": 12.97, "lon": 77.59},
        {"District_Name": "Bengaluru Urban", "lat": 12.98, "lon": 77.60},
        {"District_Name": "Bengaluru Urban", "lat": 12.96, "lon": 77.58},
        {"District_Name": "Bengaluru Urban", "lat": 12.99, "lon": 77.61},
    ]
    areas = compute_unsub_anchor_areas(rows)
    assert len(areas) >= 1
    anchor = areas[0]
    assert "centroid" in anchor
    assert "convex_hull" in anchor
    assert anchor["radius_km"] > 0
    assert "description" in anchor

    # Property test: all points should be within radius_km of centroid
    c_lat = anchor["centroid"]["lat"]
    c_lon = anchor["centroid"]["lon"]
    for r in rows:
        dist = _haversine_km(c_lat, c_lon, r["lat"], r["lon"])
        assert dist <= anchor["radius_km"] + 0.1, f"Point {dist} km away exceeds radius {anchor['radius_km']} km"


def test_compute_dark_zones_monotonicity():
    rows = [
        {"District_Name": "Zone A", "AccusedName": "Unknown", "lat": 12.9, "lon": 77.5},
        {"District_Name": "Zone A", "AccusedName": "Unknown", "lat": 12.91, "lon": 77.51},
        {"District_Name": "Zone B", "AccusedName": "Ramesh", "lat": 13.0, "lon": 75.0},
    ]
    base_zones = compute_dark_zones(rows, gaps=[], silences=[])
    zone_a_base = next(z for z in base_zones if z["zone"] == "Zone A")

    # Add gap and silence counts to Zone A -> score should monotonically increase
    enriched_zones = compute_dark_zones(
        rows,
        gaps=[{"zone": "Zone A"}, {"zone": "Zone A"}],
        silences=[{"zone": "Zone A"}],
    )
    zone_a_enriched = next(z for z in enriched_zones if z["zone"] == "Zone A")

    assert zone_a_enriched["dark_score"] > zone_a_base["dark_score"], (
        f"Dark score should increase with gaps/silence: base={zone_a_base['dark_score']},"
        f" enriched={zone_a_enriched['dark_score']}"
    )
    assert zone_a_enriched["gap_count"] == 2
    assert zone_a_enriched["silence_count"] == 1


def test_district_cache_layer6_enrichment():
    all_districts = district_cache.get_all()
    assert len(all_districts) > 0
    d = all_districts[0]
    assert "open_unsubs_count" in d
    assert "gap_count" in d
    assert "dark_score" in d
    assert "dark_level" in d


def test_map_api_darkzones_and_anchor_areas():
    res_dark = client.get("/api/map/darkzones")
    assert res_dark.status_code == 200
    data_dark = res_dark.json()
    assert "zones" in data_dark
    assert "total" in data_dark

    res_anchor = client.get("/api/map/anchor_areas")
    assert res_anchor.status_code == 200
    data_anchor = res_anchor.json()
    assert "anchor_areas" in data_anchor
    assert "total" in data_anchor
