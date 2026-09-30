"""
Tests for grounded suggested questions (app/agents/followup_agent.py).

Contract: every emitted suggestion must be answerable — built from the actual
result context and dry-run against the database (rows > 0) before showing.
"""
import pytest

from app.agents.followup_agent import (
    grounded_followups, grounded_starters, _has_rows, _context, _candidates,
)
from app.agents.query_agent import run_template


class TestValidation:
    def test_has_rows_true_for_real_query(self):
        assert _has_rows("T13", {}) is True

    def test_has_rows_false_for_empty_result(self):
        # A zone name that does not exist can never return rows.
        assert _has_rows("T4", {"zones": ["Atlantis Sector 9"]}) is False

    def test_has_rows_false_for_invalid_params(self):
        assert _has_rows("T9", {}) is False   # missing required suspect_id


class TestContext:
    def test_prefers_params_over_rows(self):
        ctx = _context({"zones": ["Rajajinagar"], "crime_types": ["theft"]},
                       [{"zone": "Whitefield", "crime_type": "robbery"}])
        assert ctx["zone"] == "Rajajinagar"
        assert ctx["crime_type"] == "theft"

    def test_falls_back_to_most_common_row_values(self):
        rows = [{"zone": "Jayanagar"}, {"zone": "Jayanagar"}, {"zone": "Whitefield"}]
        assert _context({}, rows)["zone"] == "Jayanagar"

    def test_suspect_id_extracted(self):
        rows = [{"crime_id": "C1"}, {"suspect_id": "S0001", "full_name": "X"}]
        assert _context({}, rows)["suspect_id"] == "S0001"


class TestCandidates:
    def test_never_resuggests_answered_template(self):
        ctx = {"zone": "Rajajinagar", "crime_type": "theft", "suspect_id": None}
        for _, tid, _p in _candidates("T11", ctx):
            assert tid != "T11"


class TestGroundedFollowups:
    def test_every_suggestion_is_answerable(self):
        rows, _ = run_template("T1", {"zones": ["Rajajinagar"], "limit": 20})
        suggestions = grounded_followups("T1", {"zones": ["Rajajinagar"]}, rows)
        assert 1 <= len(suggestions) <= 3
        # Re-resolve each suggestion's own candidate query — must have rows.
        ctx = _context({"zones": ["Rajajinagar"]}, rows)
        cand_map = {q: (t, p) for q, t, p in _candidates("T1", ctx)}
        for s in suggestions:
            assert s in cand_map, f"unknown suggestion {s!r}"
            tid, params = cand_map[s]
            assert _has_rows(tid, params), f"suggestion not answerable: {s!r}"

    def test_unanswerable_context_yields_only_valid_generics(self):
        # A fictional zone produces no zone-scoped suggestions; the validated
        # generic fillers (repeat offenders / type breakdown) still pass.
        suggestions = grounded_followups("T1", {"zones": ["Atlantis Sector 9"]}, [])
        for s in suggestions:
            assert "Atlantis" not in s

    def test_uses_real_context_values(self):
        rows, _ = run_template("T1", {"zones": ["Rajajinagar"], "limit": 20})
        suggestions = grounded_followups("T1", {"zones": ["Rajajinagar"]}, rows)
        assert any("Rajajinagar" in s for s in suggestions)


class TestStarters:
    def test_starters_are_validated_and_nonempty(self):
        starters = grounded_starters()
        assert 1 <= len(starters) <= 3


class TestQueryAgentIntegration:
    @pytest.mark.anyio
    async def test_followups_flow_through_query_agent(self):
        from app.agents.query_agent import query_agent_run
        from app.agents.heuristics import heuristic_select
        res = await query_agent_run("show thefts in Rajajinagar", lang="en",
                                    session_id="test-followups",
                                    select_llm=None, compose_llm=None,
                                    selector=heuristic_select)
        assert isinstance(res["suggested_followups"], list)
        assert len(res["suggested_followups"]) <= 3
