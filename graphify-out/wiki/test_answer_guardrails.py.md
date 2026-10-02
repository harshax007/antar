# test_answer_guardrails.py

> 46 nodes · cohesion 0.08

## Key Concepts

- **test_answer_guardrails.py** (15 connections) — `tests/test_answer_guardrails.py`
- **apply_guardrails()** (14 connections) — `app/core/answer_guardrails.py`
- **answer_guardrails.py** (11 connections) — `app/core/answer_guardrails.py`
- **check_numbers()** (10 connections) — `app/core/answer_guardrails.py`
- **enforce_no_result()** (9 connections) — `app/core/answer_guardrails.py`
- **cap_length()** (6 connections) — `app/core/answer_guardrails.py`
- **check_identifiers()** (6 connections) — `app/core/answer_guardrails.py`
- **strip_slop()** (6 connections) — `app/core/answer_guardrails.py`
- **TestG2NoResult** (6 connections) — `tests/test_answer_guardrails.py`
- **TestApplyGuardrails** (5 connections) — `tests/test_answer_guardrails.py`
- **TestG1Numbers** (5 connections) — `tests/test_answer_guardrails.py`
- **_allowed_numbers()** (4 connections) — `app/core/answer_guardrails.py`
- **walk()** (4 connections) — `app/core/answer_guardrails.py`
- **_norm_num()** (3 connections) — `app/core/answer_guardrails.py`
- **.test_related_material_cannot_masquerade_as_answer()** (3 connections) — `tests/test_answer_guardrails.py`
- **TestG3Identifiers** (3 connections) — `tests/test_answer_guardrails.py`
- **TestG4Slop** (3 connections) — `tests/test_answer_guardrails.py`
- **TestG6Length** (3 connections) — `tests/test_answer_guardrails.py`
- **.test_clean_answer_passes_untouched()** (2 connections) — `tests/test_answer_guardrails.py`
- **.test_end_to_end_cleans_a_hostile_answer()** (2 connections) — `tests/test_answer_guardrails.py`
- **.test_never_raises_on_garbage_input()** (2 connections) — `tests/test_answer_guardrails.py`
- **.test_never_returns_empty()** (2 connections) — `tests/test_answer_guardrails.py`
- **.test_drops_sentence_with_invented_number()** (2 connections) — `tests/test_answer_guardrails.py`
- **.test_keeps_supported_numbers()** (2 connections) — `tests/test_answer_guardrails.py`
- **.test_no_rows_is_a_noop()** (2 connections) — `tests/test_answer_guardrails.py`
- *... and 21 more nodes in this community*

## Relationships

- [re](re.md) (1 shared connections)
- [chat.py](chat.py.md) (1 shared connections)
- [query_agent.py](query_agent.py.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)

## Source Files

- `app/core/answer_guardrails.py`
- `tests/test_answer_guardrails.py`

## Audit Trail

- EXTRACTED: 83 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*