"""
Tests for /think /connect /anticipate slash commands.

Covers:
  • parse_slash_command — parsing contract
  • /api/chat/stream pipeline — command step, forced routes, reasoning trail,
    bare-command usage help (no fabricated answer)
  • run_agentic_spine parity for the non-stream /api/chat path
"""
import json
import pytest

from app.agents.heuristics import parse_slash_command, SLASH_COMMANDS


async def _collect(text: str, session_id: str = "test-slash-ses"):
    from app.api.chat_stream import _run_pipeline, StreamChatRequest
    from app.core.sse import SSEQueue
    q = SSEQueue()
    req = StreamChatRequest(text=text, lang="en", session_id=session_id)
    await _run_pipeline(req, q)
    events = []
    async for line in q:
        events.append(json.loads(line.replace("data: ", "").strip()))
    return events


# ── parse_slash_command ───────────────────────────────────────────────────────
class TestParse:
    def test_plain_text_is_not_a_command(self):
        cmd, rest = parse_slash_command("thefts in Bengaluru")
        assert cmd is None
        assert rest == "thefts in Bengaluru"

    def test_think(self):
        cmd, rest = parse_slash_command("/think thefts in Bengaluru")
        assert cmd == "think"
        assert rest == "thefts in Bengaluru"

    def test_connect_case_insensitive(self):
        cmd, rest = parse_slash_command("/CONNECT Ravi Kumar")
        assert cmd == "connect"
        assert rest == "Ravi Kumar"

    def test_anticipate_with_colon(self):
        cmd, rest = parse_slash_command("/anticipate: robbery next week")
        assert cmd == "anticipate"
        assert rest == "robbery next week"

    def test_bare_command_returns_empty_rest(self):
        cmd, rest = parse_slash_command("/think")
        assert cmd == "think"
        assert rest == ""

    def test_unknown_command_passes_through(self):
        cmd, rest = parse_slash_command("/frobnicate xyz")
        assert cmd is None
        assert rest == "/frobnicate xyz"

    def test_slash_mid_text_is_not_a_command(self):
        cmd, _ = parse_slash_command("what is a /think command?")
        assert cmd is None

    def test_registry_shape(self):
        for name, spec in SLASH_COMMANDS.items():
            assert "forces" in spec and "label" in spec, name


# ── /api/chat/stream pipeline ─────────────────────────────────────────────────
class TestStreamPipeline:
    @pytest.mark.anyio
    async def test_command_step_emitted(self):
        events = await _collect("/anticipate robbery in Bengaluru")
        cmd_steps = [e for e in events if e["type"] == "step" and e.get("agent") == "command"]
        assert cmd_steps and cmd_steps[0]["command"] == "anticipate"

    @pytest.mark.anyio
    async def test_anticipate_forces_forecast_routes(self):
        events = await _collect("/anticipate robbery in Bengaluru")
        router = next(e for e in events if e["type"] == "step"
                      and e.get("agent") == "router" and e.get("status") == "done")
        for r in ("geo", "predict", "pattern"):
            assert r in router["routes"]

    @pytest.mark.anyio
    async def test_connect_forces_linkage_routes(self):
        events = await _collect("/connect thefts in Bengaluru")
        router = next(e for e in events if e["type"] == "step"
                      and e.get("agent") == "router" and e.get("status") == "done")
        for r in ("network", "profile"):
            assert r in router["routes"]

    @pytest.mark.anyio
    async def test_think_delivers_trail_as_data_not_in_the_answer(self):
        """CONTRACT CHANGE (2026-07-21): the reasoning trail ships as structured
        `reasoning` for the Expert terminal / "Why?" collapse — it is NOT concatenated
        into the answer. Previously it was, so build_layout promoted lines like
        "Classified as T11" / "Extracted: {...}" to `facts` and the pipeline internals
        became the visible answer body while the real answer hid behind "Show full
        answer". Answer = answer; trail = trail."""
        events = await _collect("/think thefts in Bengaluru")
        answer = "".join(e["content"] for e in events if e["type"] == "token")

        # the trail is still delivered — just as data
        complete = next(e for e in events if e["type"] == "complete")
        assert complete.get("reasoning"), "reasoning trail must still be delivered"

        # ...and never smuggled into the officer-facing prose
        for leak in ("Reasoning trail", "Classified as", "Extracted:",
                     "Queried the crime database", "Summarized using only"):
            assert leak not in answer, f"pipeline internal leaked into answer: {leak}"

    @pytest.mark.anyio
    async def test_bare_command_returns_usage_help(self):
        events = await _collect("/connect")
        complete = next(e for e in events if e["type"] == "complete")
        assert complete["template_id"] == "COMMAND_HELP"
        answer = "".join(e["content"] for e in events if e["type"] == "token")
        assert "Usage: /connect" in answer

    @pytest.mark.anyio
    async def test_complete_carries_command(self):
        events = await _collect("/anticipate robbery in Bengaluru")
        complete = next(e for e in events if e["type"] == "complete")
        assert complete["command"] == "anticipate"

    @pytest.mark.anyio
    async def test_plain_query_has_no_command(self):
        events = await _collect("thefts in Bengaluru")
        assert not any(e.get("agent") == "command" for e in events if e["type"] == "step")
        complete = next(e for e in events if e["type"] == "complete")
        assert complete.get("command") is None


# ── run_agentic_spine parity (non-stream /api/chat) ──────────────────────────
class TestSpineParity:
    @pytest.mark.anyio
    async def test_bare_command_help(self):
        from app.agents.agentic_spine import run_agentic_spine
        res = await run_agentic_spine("/anticipate", lang="en", session_id="test-slash-spine")
        assert res["template_id"] == "COMMAND_HELP"
        assert "Usage: /anticipate" in res["answer"]

    @pytest.mark.anyio
    async def test_think_delivers_trail_as_data_not_in_the_answer(self):
        """Spine parity with the stream contract — trail as data, never in the prose."""
        from app.agents.agentic_spine import run_agentic_spine
        res = await run_agentic_spine("/think thefts in Bengaluru",
                                      lang="en", session_id="test-slash-spine2")
        assert res.get("reasoning"), "reasoning trail must still be delivered"
        for leak in ("Reasoning trail", "Classified as", "Extracted:",
                     "Queried the crime database", "Summarized using only"):
            assert leak not in res["answer"], f"pipeline internal leaked into answer: {leak}"
