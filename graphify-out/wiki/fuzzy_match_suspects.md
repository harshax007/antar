# fuzzy_match_suspects

> 46 nodes · cohesion 0.07

## Key Concepts

- **fuzzy_match_suspects()** (24 connections) — `app/services/entity_resolver.py`
- **jaro_winkler()** (16 connections) — `app/services/entity_resolver.py`
- **TestFuzzyMatchSuspects** (16 connections) — `tests/test_fuzzy_entity_resolver.py`
- **jaro()** (12 connections) — `app/services/entity_resolver.py`
- **TestJaroWinkler** (9 connections) — `tests/test_fuzzy_entity_resolver.py`
- **TestJaro** (8 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_exact_match_returns_suspect()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_father_name_search()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_high_threshold_filters_jw_but_soundex_can_still_fire()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_soundex_raju_raaju()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_typo_yellapa_finds_yellappa()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_wow2_s0001_alias_yellappa()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_wow2_s0002_full_name_yellappa()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_prefix_bonus_raises_above_jaro()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.setup_method()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_all_hits_have_required_fields()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_empty_query_returns_empty()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_limit_respected()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_match_method_values()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_match_score_in_range()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_no_duplicate_suspect_ids()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_sorted_by_score_desc()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_both_empty()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_close_names()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_completely_different()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- *... and 21 more nodes in this community*

## Relationships

- [profile.py](profile.py.md) (11 shared connections)
- [typing](typing.md) (5 shared connections)
- [run_research](run_research.md) (2 shared connections)
- [soundex](soundex.md) (1 shared connections)

## Source Files

- `app/services/entity_resolver.py`
- `tests/test_fuzzy_entity_resolver.py`

## Audit Trail

- EXTRACTED: 91 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*