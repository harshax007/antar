"""
Phase 1 Acceptance Tests: A6 Dwani Kannada Voice & Language
===========================================================
Verifies that:
  • Kannada text translates accurately to English normalized queries
  • English answers translate back to Kannada
  • /api/voice/dwani returns bilingual answers with citations and provenance
  • Suspect names (e.g., Yellappa) resolve correctly
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.services import bhashini
from app.agents import dwani_agent


class TestBhashiniService:
    @pytest.mark.anyio
    async def test_kannada_to_english_translation(self):
        res1 = await bhashini.translate_text("ರಾಜಾಜಿನಗರ", source_lang="kn", target_lang="en")
        assert res1 == "Rajajinagar"
        res2 = await bhashini.translate_text("ಸರಗಳ್ಳತನ", source_lang="kn", target_lang="en")
        assert res2 == "Chain Snatching"

    @pytest.mark.anyio
    async def test_english_to_kannada_translation(self):
        res = await bhashini.translate_text("Rajajinagar", source_lang="en", target_lang="kn")
        assert res == "ರಾಜಾಜಿನಗರ"

    @pytest.mark.anyio
    async def test_transcribe_audio_fallback(self):
        res = await bhashini.transcribe_audio(b"fake_audio_data", source_lang="kn")
        assert res["ok"] is True
        assert "ರಾಜಾಜಿನಗರ" in res["transcription_kn"]
        assert "Rajajinagar" in res["normalized_en"]


class TestDwaniAgent:
    @pytest.mark.anyio
    async def test_process_kannada_query_chain_snatching(self):
        from app.services import evidence_ledger as ev
        exp_n, _ = ev.crime_count("snatch", "Rajajinagar")   # the REAL count
        res = await dwani_agent.process_kannada_query("ರಾಜಾಜಿನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ತೋರಿಸಿ")
        assert res["normalized_en"] == "Show Chain Snatching cases in Rajajinagar"
        # answer reports the real count from the ledger, not a fabricated number
        assert str(exp_n) in res["answer_en"]
        assert "Rajajinagar" in res["answer_en"]
        assert len(res["citations"]) == min(exp_n, 3)
        assert res["provenance"]["agent"] == "A6: Dwani Kannada"

    @pytest.mark.anyio
    async def test_process_kannada_query_suspect_resolution(self):
        # a real alias name resolves through the unified bridge to a real ledger entity
        res = await dwani_agent.process_kannada_query("ರವಿ ಹುಡುಕಿ")
        assert res["suspect_resolved"] is not None
        assert res["suspect_resolved"].get("suspect_id"), "resolved suspect must be a real entity"


class TestVoiceEndpoints:
    @pytest.mark.anyio
    async def test_status_endpoint_200(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get("/api/voice/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["fallback_dictionary_active"] is True
        assert "kn" in data["supported_languages"]

    @pytest.mark.anyio
    async def test_translate_endpoint_200(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.post("/api/voice/translate", json={"text": "ಕೊರಮಂಗಲ", "source_lang": "kn", "target_lang": "en"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["translated"] == "Koramangala"

    @pytest.mark.anyio
    async def test_dwani_endpoint_200(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.post("/api/voice/dwani", json={"query_kn": "ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು ಯಾರು?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer_kn" in data
        assert "answer_en" in data
        assert len(data["citations"]) >= 1
