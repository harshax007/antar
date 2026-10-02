# district_cache.py

> 14 nodes · cohesion 0.20

## Key Concepts

- **district_cache.py** (14 connections) — `app/services/district_cache.py`
- **refresh()** (8 connections) — `app/services/district_cache.py`
- **get_all()** (7 connections) — `app/services/district_cache.py`
- **get_district()** (4 connections) — `app/services/district_cache.py`
- **_db()** (3 connections) — `app/services/district_cache.py`
- **_risk_level()** (3 connections) — `app/services/district_cache.py`
- **_trend_str()** (2 connections) — `app/services/district_cache.py`
- **test_district_cache_layer6_enrichment()** (2 connections) — `tests/test_layer6_geospatial.py`
- **Connection** (1 connections)
- **Antar — District aggregates cache (§5: materialization)…** (1 connections) — `app/services/district_cache.py`
- **All district aggregates as a list — for choropleth.** (1 connections) — `app/services/district_cache.py`
- **Single-district drill-down card — O(1) dict lookup.** (1 connections) — `app/services/district_cache.py`
- **High / Medium / Low based on count + month-over-month ratio.** (1 connections) — `app/services/district_cache.py`
- **Rebuild district aggregates from SQLite. < 20 ms for the seed world.** (1 connections) — `app/services/district_cache.py`

## Relationships

- [map_api.py](map_api.py.md) (3 shared connections)
- [typing](typing.md) (3 shared connections)
- [time](time.md) (2 shared connections)
- [test_layer6_geospatial.py](test_layer6_geospatial.py.md) (2 shared connections)
- [gi_star_surface](gi_star_surface.md) (1 shared connections)
- [anomaly.py](anomaly.py.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)

## Source Files

- `app/services/district_cache.py`
- `tests/test_layer6_geospatial.py`

## Audit Trail

- EXTRACTED: 31 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*