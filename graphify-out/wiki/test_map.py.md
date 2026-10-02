# test_map.py

> 10 nodes · cohesion 0.27

## Key Concepts

- **test_map.py** (8 connections) — `tests/test_map.py`
- **hotspots()** (7 connections) — `app/api/map_api.py`
- **districts()** (6 connections) — `app/api/map_api.py`
- **test_hotspots_theft_surfaces_planted_hot_zones()** (3 connections) — `tests/test_map.py`
- **test_districts_drilldown()** (2 connections) — `tests/test_map.py`
- **test_hotspots_returns_points_and_clusters()** (2 connections) — `tests/test_map.py`
- **Pre-aggregated zone hotspots — instant query from zone_summary table.** (1 connections) — `app/api/map_api.py`
- **District-level choropleth data — instant from summary tables.** (1 connections) — `app/api/map_api.py`
- **Map API (N2 / F3) — hotspot aggregation + district drill-down over the seed…** (1 connections) — `tests/test_map.py`
- **P3: Rajajinagar / Gandhinagar are planted theft hot zones → near the top by…** (1 connections) — `tests/test_map.py`

## Relationships

- [map_api.py](map_api.py.md) (7 shared connections)
- [asyncio](asyncio.md) (1 shared connections)

## Source Files

- `app/api/map_api.py`
- `tests/test_map.py`

## Audit Trail

- EXTRACTED: 20 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*