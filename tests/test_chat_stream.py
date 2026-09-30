"""
Tests for chat SSE streaming — /api/chat/stream.

Tests cover:
  • SSEQueue: emit / iterate / close
  • token_stream: chunking + delay=0 for speed
  • sse_event: format contract
  • _answer_confidence: calibration math
  • _run_pipeline: event sequence + field contract (offline mode, no LLM)
  • HTTP endpoint: correct media-type + event stream structure
"""
import asyncio
import json
import pytest
from httpx import AsyncClient, ASGITransport

from app.core.sse import SSEQueue, token_stream, sse_event
from app.api.chat_stream import _answer_confidence


# ── SSEQueue ──────────────────────────────────────────────────────────────────
class TestSSEQueue:
    @pytest.mark.anyio
    async def test_emit_and_iterate(self):
        q = SSEQueue()
        await q.emit("step", agent="router", status="running")
        await q.emit("token", content="hello")
        await q.close()
        events = []
        async for line in q:
            events.append(json.loads(line.replace("data: ", "").strip()))
        assert events[0]["type"] == "step"
        assert events[0]["agent"] == "router"
        assert events[1]["type"] == "token"
        assert events[1]["content"] == "hello"
        assert len(events) == 2

    @pytest.mark.anyio
    async def test_close_stops_iteration(self):
        q = SSEQueue()
        await q.close()
        collected = []
        async for _ in q:
            collected.append(_)
        assert collected == []

    @pytest.mark.anyio
    async def test_emit_preserves_extra_kwargs(self):
        q = SSEQueue()
        await q.emit("visual", key="graph", data={"nodes": 5})
        await q.close()
        items = [line async for line in q]
        parsed = json.loads(items[0].replace("data: ", "").strip())
        assert parsed["key"] == "graph"
        assert parsed["data"]["nodes"] == 5


# ── sse_event ─────────────────────────────────────────────────────────────────
class TestSSEEvent:
    def test_format_starts_with_data(self):
        line = sse_event("step", agent="x")
        assert line.startswith("data: ")
        assert line.endswith("\n\n")

    def test_type_field_present(self):
        payload = json.loads(sse_event("complete", foo="bar").replace("data: ", "").strip())
        assert payload["type"] == "complete"
        assert payload["foo"] == "bar"

    def test_unicode_preserved(self):
        line = sse_event("token", content="ಕರ್ನಾಟಕ")
        assert "ಕರ್ನಾಟಕ" in line


# ── token_stream ──────────────────────────────────────────────────────────────
class TestTokenStream:
    @pytest.mark.anyio
    async def test_reassembled_text_matches_original(self):
        text = "Found 12 robbery cases in Bengaluru North."
        chunks = [c async for c in token_stream(text, delay_s=0)]
        assert "".join(chunks) == text

    @pytest.mark.anyio
    async def test_one_chunk_per_word(self):
        text = "hello world foo"
        chunks = [c async for c in token_stream(text, delay_s=0)]
        assert len(chunks) == 3

    @pytest.mark.anyio
    async def test_single_word(self):
        chunks = [c async for c in token_stream("ok", delay_s=0)]
        assert chunks == ["ok"]

    @pytest.mark.anyio
    async def test_empty_string(self):
        chunks = [c async for c in token_stream("", delay_s=0)]
        assert chunks == [""]  # "".split(" ") == [""]

    @pytest.mark.anyio
    async def test_kannada_text_preserved(self):
        text = "ದಾಖಲೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ"
        chunks = [c async for c in token_stream(text, delay_s=0)]
        assert "".join(chunks) == text


# ── _answer_confidence ────────────────────────────────────────────────────────
class TestAnswerConfidence:
    def test_high_confidence_all_signals(self):
        conf = _answer_confidence(0.92, [{}]*5, [{}]*4)
        assert conf["answer"] >= 0.75
        assert conf["label"] == "High confidence"

    def test_no_rows_no_citations(self):
        conf = _answer_confidence(0.86, [], [])
        # b=0, a=0, c=0.86 → 0.3*0.86=0.258
        assert conf["answer"] < 0.40

    def test_routing_conf_component(self):
        low  = _answer_confidence(0.50, [], [])
        high = _answer_confidence(0.95, [], [])
        assert high["answer"] > low["answer"]

    def test_keys_present(self):
        conf = _answer_confidence(0.80, [{}], [{}])
        assert "routing" in conf
        assert "answer"  in conf
        assert "label"   in conf

    def test_low_label_when_score_below_60(self):
        conf = _answer_confidence(0.40, [], [])
        assert "Low confidence" in conf["label"]

    def test_score_bounded_0_to_1(self):
        conf = _answer_confidence(1.0, [{}]*100, [{}]*100)
        assert 0.0 <= conf["answer"] <= 1.0


# ── _run_pipeline (event sequence) ───────────────────────────────────────────
class TestRunPipeline:
    @pytest.mark.anyio
    async def test_produces_expected_event_types(self):
        from app.api.chat_stream import _run_pipeline, StreamChatRequest
        q   = SSEQueue()
        req = StreamChatRequest(text="Show robbery cases in Bengaluru", lang="en")
        await _run_pipeline(req, q)
        events = []
        async for line in q:
            events.append(json.loads(line.replace("data: ", "").strip()))
        types = [e["type"] for e in events]
        # Required sequence markers
        assert "step"     in types
        assert "token"    in types
        assert "complete" in types

    @pytest.mark.anyio
    async def test_router_step_has_routes(self):
        from app.api.chat_stream import _run_pipeline, StreamChatRequest
        q   = SSEQueue()
        req = StreamChatRequest(text="hotspots in Whitefield", lang="en")
        await _run_pipeline(req, q)
        events = [json.loads(l.replace("data: ", "").strip()) async for l in q]
        router_done = next((e for e in events if e["type"] == "step"
                            and e.get("agent") == "router" and e.get("status") == "done"), None)
        assert router_done is not None
        assert isinstance(router_done.get("routes"), list)
        assert len(router_done["routes"]) >= 1

    @pytest.mark.anyio
    async def test_tokens_reconstruct_to_nonempty_answer(self):
        from app.api.chat_stream import _run_pipeline, StreamChatRequest
        q   = SSEQueue()
        req = StreamChatRequest(text="How many thefts last month?", lang="en")
        await _run_pipeline(req, q)
        events = [json.loads(l.replace("data: ", "").strip()) async for l in q]
        tokens = [e["content"] for e in events if e["type"] == "token"]
        answer = "".join(tokens)
        assert len(answer) > 5

    @pytest.mark.anyio
    async def test_complete_event_has_session_id(self):
        from app.api.chat_stream import _run_pipeline, StreamChatRequest
        q   = SSEQueue()
        req = StreamChatRequest(text="Any alerts?", lang="en", session_id="test-ses-001")
        await _run_pipeline(req, q)
        events = [json.loads(l.replace("data: ", "").strip()) async for l in q]
        complete = next(e for e in events if e["type"] == "complete")
        assert complete["session_id"] == "test-ses-001"
        assert "template_id" in complete
        assert "mode"        in complete
        assert "lang"        in complete

    @pytest.mark.anyio
    async def test_confidence_event_emitted(self):
        from app.api.chat_stream import _run_pipeline, StreamChatRequest
        q   = SSEQueue()
        req = StreamChatRequest(text="top suspects in Rajajinagar", lang="en")
        await _run_pipeline(req, q)
        events = [json.loads(l.replace("data: ", "").strip()) async for l in q]
        conf_evt = next((e for e in events if e["type"] == "confidence"), None)
        assert conf_evt is not None
        assert "answer"  in conf_evt
        assert "routing" in conf_evt
        assert "label"   in conf_evt

    @pytest.mark.anyio
    async def test_step_order_router_before_query(self):
        from app.api.chat_stream import _run_pipeline, StreamChatRequest
        q   = SSEQueue()
        req = StreamChatRequest(text="crime trend Bengaluru", lang="en")
        await _run_pipeline(req, q)
        events = [json.loads(l.replace("data: ", "").strip()) async for l in q]
        step_agents = [e.get("agent") for e in events if e["type"] == "step"]
        assert step_agents.index("router") < step_agents.index("query")

    @pytest.mark.anyio
    async def test_kannada_query_lang_detected(self):
        from app.api.chat_stream import _run_pipeline, StreamChatRequest
        q   = SSEQueue()
        req = StreamChatRequest(text="ಬೆಂಗಳೂರಿನಲ್ಲಿ ಕಳ್ಳತನ")
        await _run_pipeline(req, q)
        events = [json.loads(l.replace("data: ", "").strip()) async for l in q]
        complete = next(e for e in events if e["type"] == "complete")
        assert complete.get("lang") == "kn"

    @pytest.mark.anyio
    async def test_complete_is_last_event(self):
        from app.api.chat_stream import _run_pipeline, StreamChatRequest
        q   = SSEQueue()
        req = StreamChatRequest(text="Show network for Raju", lang="en")
        await _run_pipeline(req, q)
        events = [json.loads(l.replace("data: ", "").strip()) async for l in q]
        assert events[-1]["type"] == "complete"


# ── HTTP endpoint ─────────────────────────────────────────────────────────────
class TestStreamEndpointHTTP:
    @pytest.mark.anyio
    async def test_content_type_is_event_stream(self):
        from main import app as fastapi_app
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as client:
            async with client.stream("POST", "/api/chat/stream",
                                     json={"text": "robbery trends", "lang": "en"}) as resp:
                assert "text/event-stream" in resp.headers["content-type"]

    @pytest.mark.anyio
    async def test_stream_contains_data_lines(self):
        from main import app as fastapi_app
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as client:
            lines = []
            async with client.stream("POST", "/api/chat/stream",
                                     json={"text": "top suspects", "lang": "en"}) as resp:
                async for chunk in resp.aiter_text():
                    lines.extend(chunk.split("\n"))
            data_lines = [l for l in lines if l.startswith("data: ")]
            assert len(data_lines) >= 3   # at minimum: one step, one token, one complete
            # Every data line must be valid JSON
            for dl in data_lines:
                parsed = json.loads(dl.replace("data: ", ""))
                assert "type" in parsed
