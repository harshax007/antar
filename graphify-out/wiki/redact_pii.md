# redact_pii

> 16 nodes · cohesion 0.19

## Key Concepts

- **redact_pii()** (15 connections) — `app/core/guardrails.py`
- **guardrails.py** (10 connections) — `app/core/guardrails.py`
- **test_guardrails.py** (10 connections) — `tests/test_guardrails.py`
- **evaluate_bias()** (7 connections) — `app/core/guardrails.py`
- **_mask_case_ids()** (4 connections) — `app/core/guardrails.py`
- **_restore_case_ids()** (2 connections) — `app/core/guardrails.py`
- **test_evaluate_bias_clean()** (2 connections) — `tests/test_guardrails.py`
- **test_evaluate_bias_flagged()** (2 connections) — `tests/test_guardrails.py`
- **test_redact_pii_aadhaar()** (2 connections) — `tests/test_guardrails.py`
- **test_redact_pii_phone()** (2 connections) — `tests/test_guardrails.py`
- **_hold()** (1 connections) — `app/core/guardrails.py`
- **Swap case identifiers for placeholders that no PII pattern can match.** (1 connections) — `app/core/guardrails.py`
- **Redacts sensitive PII (Aadhaar, Phone Numbers) leaving only the last 4 digits.…** (1 connections) — `app/core/guardrails.py`
- **Evaluates generated profile text for potentially biased terminology. Returns…** (1 connections) — `app/core/guardrails.py`
- **_aadhaar_repl()** (1 connections) — `app/core/guardrails.py`
- **_phone_repl()** (1 connections) — `app/core/guardrails.py`

## Relationships

- [quickml.py](quickml.py.md) (5 shared connections)
- [profile_agent.py](profile_agent.py.md) (4 shared connections)
- [trace.py](trace.py.md) (4 shared connections)
- [re](re.md) (1 shared connections)
- [flags.py](flags.py.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)

## Source Files

- `app/core/guardrails.py`
- `tests/test_guardrails.py`

## Audit Trail

- EXTRACTED: 36 (92%)
- INFERRED: 3 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*