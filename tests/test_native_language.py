"""
Native KN⇄EN tests:
  1. The UI language toggle is authoritative for the OUTPUT language — asking in
     one language with the other selected still answers in the selected language.
  2. Deterministic fallback answers are emoji-free and render in the right script.
  3. POST /api/translate — passthrough / target / validation.
"""
import re

import pytest
from httpx import AsyncClient, ASGITransport

from app.agents.query_agent import _fallback_answer
from app.agents.heuristics import is_kannada

_EMOJI = re.compile(r"[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")


class TestForcedOutputLanguage:
    @pytest.mark.anyio
    async def test_english_question_kn_toggle_answers_kannada(self):
        # Question in English, UI toggle = kn → answer must be Kannada.
        from app.agents.query_agent import query_agent_run
        from app.agents.heuristics import heuristic_select
        res = await query_agent_run("show thefts in Rajajinagar", lang="kn",
                                    session_id="test-lang-1",
                                    select_llm=None, compose_llm=None,
                                    selector=heuristic_select)
        assert is_kannada(res["answer"]), res["answer"]

    @pytest.mark.anyio
    async def test_kannada_question_en_toggle_answers_english(self):
        from app.agents.query_agent import query_agent_run
        from app.agents.heuristics import heuristic_select
        res = await query_agent_run("ರಾಜಾಜಿನಗರದಲ್ಲಿ ಕಳ್ಳತನ ತೋರಿಸಿ", lang="en",
                                    session_id="test-lang-2",
                                    select_llm=None, compose_llm=None,
                                    selector=heuristic_select)
        assert not is_kannada(res["answer"]), res["answer"]


class TestFallbackClean:
    def test_trend_fallback_no_emoji_en(self):
        rows = [{"month": "2026-05", "n": 8}, {"month": "2026-06", "n": 3}]
        out = _fallback_answer(rows, "T3", "en")
        assert not _EMOJI.search(out), out
        assert "DOWNWARD" in out

    def test_trend_fallback_kannada_script(self):
        rows = [{"month": "2026-05", "n": 8}, {"month": "2026-06", "n": 3}]
        out = _fallback_answer(rows, "T3", "kn")
        assert not _EMOJI.search(out)
        assert is_kannada(out)


@pytest.fixture()
async def client():
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestTranslateEndpoint:
    @pytest.mark.anyio
    async def test_passthrough_same_language(self, client):
        # English text asked for English → passthrough, unchanged.
        r = await client.post("/api/translate",
                              json={"text": "[VERIFIED] 3 records found", "target_lang": "en"})
        assert r.status_code == 200
        body = r.json()
        assert body["engine"] == "passthrough"
        assert body["translated"] == "[VERIFIED] 3 records found"

    @pytest.mark.anyio
    async def test_kannada_text_to_kn_passthrough(self, client):
        r = await client.post("/api/translate",
                              json={"text": "ಕಳ್ಳತನ ಪ್ರಕರಣಗಳು", "target_lang": "kn"})
        assert r.status_code == 200
        assert r.json()["engine"] == "passthrough"

    @pytest.mark.anyio
    async def test_offline_en_to_kn_uses_dictionary_or_unavailable(self, client):
        # No LLM in tests → dictionary fallback or honest 'unavailable'; never crashes.
        r = await client.post("/api/translate",
                              json={"text": "Show theft cases", "target_lang": "kn"})
        assert r.status_code == 200
        assert r.json()["engine"] in ("dictionary", "unavailable", "llm")

    @pytest.mark.anyio
    async def test_bad_target_rejected(self, client):
        r = await client.post("/api/translate", json={"text": "hi", "target_lang": "fr"})
        assert r.status_code == 422


class TestThinkStrip:
    def test_strips_think_block(self):
        from app.services.quickml import _strip_reasoning
        raw = "<think>Let me analyze. The text says X.</think>[COMPUTED] ಮೂರು ಪ್ರಕರಣಗಳು."
        assert _strip_reasoning(raw) == "[COMPUTED] ಮೂರು ಪ್ರಕರಣಗಳು."

    def test_unterminated_think_removed(self):
        from app.services.quickml import _strip_reasoning
        assert _strip_reasoning("answer first <think>then rambling with no close") == "answer first"

    def test_no_think_passthrough(self):
        from app.services.quickml import _strip_reasoning
        assert _strip_reasoning("[VERIFIED] clean answer") == "[VERIFIED] clean answer"
