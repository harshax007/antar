"""
Map API (N2 / F3) — hotspot aggregation + district drill-down over the seed world.
Run: python -m pytest tests/test_map.py -v   (run `python -m app.seeds.load` first)
"""

import asyncio

from app.api.map_api import hotspots, districts


def test_hotspots_returns_points_and_clusters():
    out = asyncio.run(hotspots())
    assert out["total"] > 0
    assert out["clusters"] and all("weight" in c for c in out["clusters"])
    assert isinstance(out["points"], list)
    assert "seasonal_note" in out


def test_hotspots_theft_surfaces_planted_hot_zones():
    """P3: Rajajinagar / Gandhinagar are planted theft hot zones → near the top by volume."""
    out = asyncio.run(hotspots(crime_type="theft"))
    top = [c["zone"] for c in out["clusters"][:4]]
    assert "Rajajinagar" in top or "Gandhinagar" in top


def test_districts_drilldown():
    out = asyncio.run(districts())
    assert out["districts"] and all("district" in d and "weight" in d for d in out["districts"])
