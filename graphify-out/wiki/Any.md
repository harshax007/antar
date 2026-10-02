# Any

> 24 nodes · cohesion 0.10

## Key Concepts

- **Any** (18 connections)
- **resolve_identifier()** (13 connections) — `app/services/zcql_repo.py`
- **normalize_accused_id()** (9 connections) — `app/services/zcql_repo.py`
- **detect_identifier()** (6 connections) — `app/services/zcql_repo.py`
- **normalize_plate()** (6 connections) — `app/services/zcql_repo.py`
- **_as_crime_list()** (5 connections) — `app/services/zcql_repo.py`
- **_esc()** (4 connections) — `app/services/zcql_repo.py`
- **_like_prefix()** (4 connections) — `app/services/zcql_repo.py`
- **test_identifier_normalisation()** (4 connections) — `tests/test_templates_t19_t23.py`
- **_as_dimension()** (3 connections) — `app/services/zcql_repo.py`
- **_as_months()** (3 connections) — `app/services/zcql_repo.py`
- **_as_order()** (3 connections) — `app/services/zcql_repo.py`
- **_as_beat_dimension()** (2 connections) — `app/services/zcql_repo.py`
- **_as_geo_dimension()** (2 connections) — `app/services/zcql_repo.py`
- **ka02m2093', 'KA 02 M 2093' → 'KA-02-M-2093' (the format stored in…** (1 connections) — `app/services/zcql_repo.py`
- **acc ka 500777' / 'ACC-KA-500777' → 'ACC-KA-500777'.** (1 connections) — `app/services/zcql_repo.py`
- **Which identifier column a raw value belongs to, or None when it can't be told.** (1 connections) — `app/services/zcql_repo.py`
- **(key_type, normalised value) for a lookup. An explicit key_type wins; otherwise…** (1 connections) — `app/services/zcql_repo.py`
- **Coerce + normalize crime types (any language/synonym → canonical English).** (1 connections) — `app/services/zcql_repo.py`
- **Coerce the LLM's time spec into a month COUNT for trend windows. Accepts an…** (1 connections) — `app/services/zcql_repo.py`
- **Escape a literal for ZCQL. Numbers bare; strings single-quoted + escaped.** (1 connections) — `app/services/zcql_repo.py`
- **The uppercase literal prefix of a `prefix%` LIKE pattern, or None. Only a…** (1 connections) — `app/services/zcql_repo.py`
- **Coerce a loose LLM dimension to a valid one (e.g. 'age'→'age_band'); unknown →…** (1 connections) — `app/services/zcql_repo.py`
- **descending' / 'lowest' / 'ASC' → 'desc' | 'asc'. The LLM rarely emits the…** (1 connections) — `app/services/zcql_repo.py`

## Relationships

- [zcql_repo.py](zcql_repo.py.md) (16 shared connections)
- [answer_writer.py](answer_writer.py.md) (7 shared connections)
- [test_templates_t19_t23.py](test_templates_t19_t23.py.md) (4 shared connections)
- [query_agent.py](query_agent.py.md) (2 shared connections)
- [build_spec](build_spec.md) (2 shared connections)
- [_date](_date.md) (2 shared connections)
- [intent_parser.py](intent_parser.py.md) (1 shared connections)
- [_fmt](_fmt.md) (1 shared connections)
- [_concept_map](_concept_map.md) (1 shared connections)

## Source Files

- `app/services/zcql_repo.py`
- `tests/test_templates_t19_t23.py`

## Audit Trail

- EXTRACTED: 64 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*