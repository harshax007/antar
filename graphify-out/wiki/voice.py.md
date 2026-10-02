# voice.py

> 22 nodes · cohesion 0.13

## Key Concepts

- **voice.py** (20 connections) — `app/api/voice.py`
- **query_dwani()** (5 connections) — `app/api/voice.py`
- **transcribe()** (5 connections) — `app/api/voice.py`
- **translate()** (5 connections) — `app/api/voice.py`
- **post** (4 connections)
- **text_to_speech()** (4 connections) — `app/api/voice.py`
- **transcribe_audio()** (4 connections) — `app/services/bhashini.py`
- **DwaniQueryRequest** (3 connections) — `app/api/voice.py`
- **get_status()** (3 connections) — `app/api/voice.py`
- **BaseModel** (3 connections)
- **TranslateRequest** (3 connections) — `app/api/voice.py`
- **TTSRequest** (3 connections) — `app/api/voice.py`
- **get** (1 connections)
- **UploadFile** (1 connections)
- **Antar — Voice & Language API (A6: Dwani Kannada · Phase 1)…** (1 connections) — `app/api/voice.py`
- **ASR: Convert uploaded audio to Kannada text with English normalization.** (1 connections) — `app/api/voice.py`
- **Translate text between Kannada and English.** (1 connections) — `app/api/voice.py`
- **Process a bilingual Kannada query and return compiled KN/EN intelligence.** (1 connections) — `app/api/voice.py`
- **Generate TTS audio from text.** (1 connections) — `app/api/voice.py`
- **Check Bhashini credentials and domain dictionary status.** (1 connections) — `app/api/voice.py`
- **ASR: Convert audio bytes to Kannada text with English translation.** (1 connections) — `app/services/bhashini.py`
- **gtts** (1 connections)

## Relationships

- [app_services](app_services.md) (2 shared connections)
- [pytest](pytest.md) (2 shared connections)
- [dwani_agent.py](dwani_agent.py.md) (2 shared connections)
- [heuristic_select](heuristic_select.md) (2 shared connections)
- [admin_data.py](admin_data.py.md) (1 shared connections)
- [pydantic](pydantic.md) (1 shared connections)
- [settings.py](settings.py.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [obs/store.py](obs-store.py.md) (1 shared connections)
- [main.py](main.py.md) (1 shared connections)

## Source Files

- `app/api/voice.py`
- `app/services/bhashini.py`

## Audit Trail

- EXTRACTED: 43 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*