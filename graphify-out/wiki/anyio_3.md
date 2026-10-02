# anyio

> 19 nodes · cohesion 0.17

## Key Concepts

- **anyio** (13 connections)
- **TestSearchEndpoint** (11 connections) — `tests/test_fuzzy_entity_resolver.py`
- **TestProfileRegression** (4 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_search_not_captured_as_suspect_id()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_no_results_returns_empty_hits()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_wow2_yellapa_typo_via_endpoint()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_registry_still_works()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_suspect_profile_still_works()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_200_ok()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_count_matches_hits_length()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_hit_fields_present()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_hits_sorted_by_score_desc()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_limit_param()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_missing_q_returns_422()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_query_echoed()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_top_level_keys()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **WOW-2: querying 'Yellapa' (one-p typo) must find the Yellappa suspects.** (1 connections) — `tests/test_fuzzy_entity_resolver.py`
- **A clearly nonsense query at default threshold should return empty, not 500.** (1 connections) — `tests/test_fuzzy_entity_resolver.py`
- **FastAPI must NOT route /search to the /{suspect_id} handler.** (1 connections) — `tests/test_fuzzy_entity_resolver.py`

## Relationships

- [profile.py](profile.py.md) (2 shared connections)

## Source Files

- `tests/test_fuzzy_entity_resolver.py`

## Audit Trail

- EXTRACTED: 31 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*