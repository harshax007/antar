# map_api.py

> 22 nodes · cohesion 0.14

## Key Concepts

- **map_api.py** (27 connections) — `app/api/map_api.py`
- **get** (10 connections)
- **_db()** (9 connections) — `app/api/map_api.py`
- **compute_kde_geojson()** (6 connections) — `app/services/geo_density.py`
- **anchor_areas()** (5 connections) — `app/api/map_api.py`
- **darkzones()** (5 connections) — `app/api/map_api.py`
- **heat()** (5 connections) — `app/api/map_api.py`
- **predicted()** (5 connections) — `app/api/map_api.py`
- **gi_star_hotspots()** (4 connections) — `app/api/map_api.py`
- **district_detail()** (3 connections) — `app/api/map_api.py`
- **districts_rich()** (3 connections) — `app/api/map_api.py`
- **flow()** (2 connections) — `app/api/map_api.py`
- **Connection** (1 connections)
- **Antar — Map API (UC2 "Explore" surface · feature N2 / F3)…** (1 connections) — `app/api/map_api.py`
- **All districts with precomputed aggregates — instant choropleth fill data.** (1 connections) — `app/api/map_api.py`
- **Single-district drill-down card (O(1) cache lookup, < 1 ms).** (1 connections) — `app/api/map_api.py`
- **Getis-Ord Gi* significance surface — spatial hotspot rings for the Map screen.…** (1 connections) — `app/api/map_api.py`
- **Top zones this month as predicted hotspots, enriched with spatial KDE contours.** (1 connections) — `app/api/map_api.py`
- **Returns the Dark-Zone Surface (Geography of the Unknown). Answers 'Where do we…** (1 connections) — `app/api/map_api.py`
- **Returns UNSUB Anchor Areas computed using 2D convex hull and haversine radius…** (1 connections) — `app/api/map_api.py`
- **Heatmap points sampled from individual FIR rows with valid coords.** (1 connections) — `app/api/map_api.py`
- **Computes 2D Gaussian KDE over coordinates. Returns a GeoJSON FeatureCollection…** (1 connections) — `app/services/geo_density.py`

## Relationships

- [test_map.py](test_map.py.md) (7 shared connections)
- [test_layer6_geospatial.py](test_layer6_geospatial.py.md) (5 shared connections)
- [district_cache.py](district_cache.py.md) (3 shared connections)
- [time](time.md) (2 shared connections)
- [gi_star_surface](gi_star_surface.md) (2 shared connections)
- [dataset.py](dataset.py.md) (2 shared connections)
- [typing](typing.md) (2 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)
- [get_product](get_product.md) (1 shared connections)
- [chat_stream.py](chat_stream.py.md) (1 shared connections)
- [zcql_local.py](zcql_local.py.md) (1 shared connections)

## Source Files

- `app/api/map_api.py`
- `app/services/geo_density.py`

## Audit Trail

- EXTRACTED: 61 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*