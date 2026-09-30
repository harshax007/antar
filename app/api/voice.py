"""
Antar — Voice & Language API (A6: Dwani Kannada · Phase 1)
===============================================================
Endpoints for Kannada speech recognition, text translation,
and bilingual crime query processing.
"""

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import io
from collections import OrderedDict
from gtts import gTTS

from app.services import bhashini
from app.agents import dwani_agent
from app.core.settings import settings

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "kn"
    target_lang: str = "en"


class DwaniQueryRequest(BaseModel):
    query_kn: str

class TTSRequest(BaseModel):
    text: str
    lang: str = "kn"


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(None), source_lang: str = Form("kn")):
    """ASR: Convert uploaded audio to Kannada text with English normalization."""
    audio_bytes = await file.read() if file else b""
    res = await bhashini.transcribe_audio(audio_bytes, source_lang=source_lang)
    res["text"] = res.get("transcription_kn") if source_lang == "kn" else res.get("normalized_en", res.get("transcription_kn"))
    return res


@router.post("/translate")
async def translate(req: TranslateRequest):
    """Translate text between Kannada and English."""
    translated = await bhashini.translate_text(req.text, req.source_lang, req.target_lang)
    return {"original": req.text, "translated": translated, "source": req.source_lang, "target": req.target_lang}


@router.post("/dwani")
async def query_dwani(req: DwaniQueryRequest):
    """Process a bilingual Kannada query and return compiled KN/EN intelligence."""
    return await dwani_agent.process_kannada_query(req.query_kn)


# Synthesised answers, keyed by (lang, text). "Listen to answer" is usually pressed more
# than once for the same answer, and each synthesis is a ~3s round trip to Google.
_TTS_CACHE: "OrderedDict[tuple[str, str], bytes]" = OrderedDict()
_TTS_CACHE_MAX = 64


def _synthesise(text: str, lang: str) -> bytes:
    fp = io.BytesIO()
    gTTS(text=text, lang=lang).write_to_fp(fp)
    return fp.getvalue()


@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    """Generate TTS audio from text."""
    text_to_speak = req.text.strip()
    if not text_to_speak:
        text_to_speak = "ಖಾಲಿ ಸಂದೇಶ" if req.lang == "kn" else "Empty message"

    key = (req.lang, text_to_speak)
    audio = _TTS_CACHE.get(key)
    if audio is None:
        # gTTS does blocking network I/O. Called directly inside this async handler it
        # stalled the whole event loop for the ~3s it takes — every other request,
        # including a running chat stream, waited behind the speech. Run it in a thread.
        audio = await asyncio.to_thread(_synthesise, text_to_speak, req.lang)
        _TTS_CACHE[key] = audio
        if len(_TTS_CACHE) > _TTS_CACHE_MAX:
            _TTS_CACHE.popitem(last=False)
    else:
        _TTS_CACHE.move_to_end(key)

    return StreamingResponse(io.BytesIO(audio), media_type="audio/mpeg",
                             headers={"Cache-Control": "private, max-age=3600"})


@router.get("/status")
async def get_status():
    """Check Bhashini credentials and domain dictionary status."""
    has_creds = bool(settings.BHASHINI_API_KEY and settings.BHASHINI_USER_ID)
    return {
        "bhashini_configured": has_creds,
        "fallback_dictionary_active": True,
        "supported_languages": ["en", "kn"],
        "agent": "A6: Dwani Kannada Voice & Language"
    }
