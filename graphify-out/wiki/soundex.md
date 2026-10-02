# soundex

> 13 nodes · cohesion 0.24

## Key Concepts

- **soundex()** (18 connections) — `app/services/entity_resolver.py`
- **TestSoundex** (9 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_raju_raaju_same()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_yellappa_yellapa_same()** (3 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_different_names_different_code()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_empty_name()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_first_letter_preserved()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_four_char_output()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_krishnappa_krishna_same()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **.test_numeric_only_returns_z000()** (2 connections) — `tests/test_fuzzy_entity_resolver.py`
- **American Soundex code — first letter + up to 3 consonant-group digits. Vowels…** (1 connections) — `app/services/entity_resolver.py`
- **WOW-2 alias variant: Yellappa and Yellapa must share a Soundex code.** (1 connections) — `tests/test_fuzzy_entity_resolver.py`
- **Doubled-vowel variant: Raju / Raaju → same code.** (1 connections) — `tests/test_fuzzy_entity_resolver.py`

## Relationships

- [profile.py](profile.py.md) (4 shared connections)
- [advocate_agent.py](advocate_agent.py.md) (3 shared connections)
- [run_research](run_research.md) (1 shared connections)
- [fuzzy_match_suspects](fuzzy_match_suspects.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)

## Source Files

- `app/services/entity_resolver.py`
- `tests/test_fuzzy_entity_resolver.py`

## Audit Trail

- EXTRACTED: 29 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*