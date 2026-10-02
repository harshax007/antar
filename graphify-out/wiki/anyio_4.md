# anyio

> 12 nodes · cohesion 0.24

## Key Concepts

- **anyio** (8 connections)
- **TestBhashiniService** (4 connections) — `tests/test_dwani_agent.py`
- **TestVoiceEndpoints** (4 connections) — `tests/test_dwani_agent.py`
- **TestDwaniAgent** (3 connections) — `tests/test_dwani_agent.py`
- **.test_english_to_kannada_translation()** (2 connections) — `tests/test_dwani_agent.py`
- **.test_kannada_to_english_translation()** (2 connections) — `tests/test_dwani_agent.py`
- **.test_transcribe_audio_fallback()** (2 connections) — `tests/test_dwani_agent.py`
- **.test_process_kannada_query_chain_snatching()** (2 connections) — `tests/test_dwani_agent.py`
- **.test_process_kannada_query_suspect_resolution()** (2 connections) — `tests/test_dwani_agent.py`
- **.test_dwani_endpoint_200()** (2 connections) — `tests/test_dwani_agent.py`
- **.test_status_endpoint_200()** (2 connections) — `tests/test_dwani_agent.py`
- **.test_translate_endpoint_200()** (2 connections) — `tests/test_dwani_agent.py`

## Relationships

- [pytest](pytest.md) (3 shared connections)

## Source Files

- `tests/test_dwani_agent.py`

## Audit Trail

- EXTRACTED: 19 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*