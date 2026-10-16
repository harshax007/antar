"""
Tests for the structured answer layout (app/agents/layout_composer.py) and
its emission on both chat paths.
"""
import json
import pytest

from app.agents.layout_composer import build_layout


ANSWER = """Found 12 theft cases in Rajajinagar this month.
• FIR 2026-101 — theft near market road
• FIR 2026-118 — two-wheeler theft
[VERIFIED] 12 records match the query filters.
[INFERRED] The cluster may indicate one repeat offender."""

QUERY = {
    "rows": [
        {"crime_id": "C1", "occurred_at": "2026-06-02", "zone": "Rajajinagar"},
        {"crime_id": "C2", "occurred_at": "2026-06-20", "zone": "Rajajinagar"},
    ],
    "citations": [{"fir": "2026-101"}, {"fir": "2026-118"}],
    "params": {"zones": ["Rajajinagar"], "crime_types": ["theft"]},
}


@pytest.fixture(autouse=True)
def _own_ledger_and_traces(tmp_path, monkeypatch):
    """These tests run the chat stream, which writes an audit entry and a trace per answer.
    tests/conftest.py redirects the audit store for a full run, but run on their own
    (pytest --noconftest) they wrote into the live ledger and the Trace page: 28 "OF-stream"
    entries by 2026-10-16. Each test now writes to its own files."""
    from app.obs import store as obs_store
    from app.services import audit_store
    monkeypatch.setattr(audit_store, "DB_PATH", str(tmp_path / "audit.db"))
    monkeypatch.setattr(audit_store, "_sync_to_catalyst_placeholder", lambda entry: None)
    audit_store.init_db()
    monkeypatch.setattr(obs_store, "DB_PATH", tmp_path / "obs.db")
    monkeypatch.setattr(obs_store, "_schema_ready", False)


class TestBuildLayout:
    def test_headline_is_first_sentence(self):
        lay = build_layout(ANSWER, QUERY)
        assert lay["headline"] == "Found 12 theft cases in Rajajinagar this month."

    def test_stats_carry_real_numbers_only(self):
        lay = build_layout(ANSWER, QUERY)
        by_label = {s["label"]: s["value"] for s in lay["stats"]}
        assert by_label["records"] == "2"
        assert by_label["citations"] == "2"
        assert by_label["zone"] == "Rajajinagar"
        assert by_label["crime type"] == "theft"
        assert by_label["period"] == "2026-06-02 → 2026-06-20"

    def test_facts_extracted_from_bullets(self):
        lay = build_layout(ANSWER, QUERY)
        assert len(lay["facts"]) == 2
        assert "FIR 2026-101" in lay["facts"][0]

    def test_kdiu_tags_canonicalized(self):
        lay = build_layout(ANSWER, QUERY)
        tags = [k["tag"] for k in lay["kdiu"]]
        assert tags == ["K", "I"]

    def test_network_stat_from_results(self):
        lay = build_layout(ANSWER, QUERY, {"network": {"nodes": [1, 2, 3], "edges": []}})
        assert any(s["value"] == "3 nodes" for s in lay["stats"])

    def test_empty_answer_never_raises(self):
        lay = build_layout("", {})
        assert lay["headline"] == "" and lay["stats"] == []


class TestChart:
    def test_trend_rows_make_line_chart(self):
        q = {"template_id": "T3",
             "rows": [{"month": "2026-05", "n": 8}, {"month": "2026-06", "n": 3},
                      {"month": "2026-07", "n": 1}],
             "citations": [], "params": {}}
        lay = build_layout("[COMPUTED] Trend", q)
        assert lay["chart"]["kind"] == "line"
        assert len(lay["chart"]["points"]) == 3
        assert lay["chart"]["points"][0] == {"label": "2026-05", "value": 8.0}

    def test_breakdown_rows_make_bar_chart(self):
        q = {"template_id": "T11",
             "rows": [{"zone": "Rajajinagar", "n": 12}, {"zone": "Jayanagar", "n": 7}],
             "citations": [], "params": {}}
        lay = build_layout("[COMPUTED] Hotspots", q)
        assert lay["chart"]["kind"] == "bar"
        assert lay["chart"]["points"][0]["label"] == "Rajajinagar"

    def test_non_aggregate_rows_no_chart(self):
        q = {"template_id": "T1",
             "rows": [{"fir_number": "2026-1", "zone": "X"}], "citations": [], "params": {}}
        assert build_layout("[VERIFIED] Cases", q)["chart"] is None

    def test_single_point_no_chart(self):
        q = {"template_id": "T3", "rows": [{"month": "2026-05", "n": 8}],
             "citations": [], "params": {}}
        assert build_layout("x", q)["chart"] is None


class TestStreamEmission:
    @pytest.mark.anyio
    async def test_layout_event_emitted(self):
        from app.api.chat_stream import _run_pipeline, StreamChatRequest
        from app.core.sse import SSEQueue
        q = SSEQueue()
        await _run_pipeline(StreamChatRequest(
            text="show thefts in Rajajinagar", lang="en",
            session_id="test-layout-ses"), q)
        events = [json.loads(l.replace("data: ", "").strip()) async for l in q]
        layouts = [e for e in events if e["type"] == "layout"]
        assert layouts, "no layout event emitted"
        lay = layouts[0]["data"]
        assert lay["headline"]
        assert isinstance(lay["stats"], list)
