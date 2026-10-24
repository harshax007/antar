"""
The Policymaker role: counts, trends, rates and rankings, never an FIR row or a named person.

Enforced at four points, each tested here on its own:
  gateway      an allowlist of routes (auth_middleware.aggregate_path_ok)
  policy       aggregate-level agents only (policy.decide)
  templates    aggregate templates only (zcql_repo.build_spec)
  query agent  a plain refusal before self-heal can answer another way
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core import policy, security_context as SC
from app.core.auth_middleware import aggregate_path_ok


def _as(role, fn):
    ctx, token = SC.begin("OF-PM", role)
    try:
        return fn()
    finally:
        SC.end(token)


class TestGatewayAllowlist:
    @pytest.mark.parametrize("path", [
        "/api/health", "/api/chat/stream", "/api/dashboard/overview", "/api/analytics/trends",
        "/api/social/demographics", "/api/forecast/hotspots", "/api/forecast/unit/Mysuru City PS",
        "/api/map/districts", "/api/map/gi_star", "/api/map/view_summary",
        "/api/predict", "/api/predict/board", "/api/predict/Mysuru/scenario", "/report/abc",
    ])
    def test_aggregate_routes_are_open(self, path):
        assert aggregate_path_ok(path)

    @pytest.mark.parametrize("path", [
        "/api/profile/S0001", "/api/graph/network", "/api/brain/search", "/api/dataset/firs",
        "/api/evidence/entity/ACC-1", "/api/corridors", "/api/linkage/EV-1", "/api/osint/scan",
        "/api/map/day_cases", "/api/map/flow", "/api/predict/leads", "/api/predict/hypotheses",
        "/api/hypothesis", "/api/sentinel/watches", "/api/hitl/queue", "/api/workspace",
        "/api/console/ask", "/api/audit/log", "/trace", "/api/upload",
    ])
    def test_case_and_person_routes_are_closed(self, path):
        assert not aggregate_path_ok(path)

    def test_the_gateway_refuses_with_a_reason(self):
        from main import app
        c = TestClient(app)
        r = c.get("/api/dataset/firs", headers={"X-Role": "Policymaker"})
        assert r.status_code == 403 and "counts, trends and rates" in r.json()["detail"]
        assert c.get("/api/health", headers={"X-Role": "Policymaker"}).status_code == 200
        # nobody else is affected by the allowlist
        assert c.get("/api/dataset/firs", headers={"X-Role": "Inspector"}).status_code != 403


class TestPolicy:
    @pytest.mark.parametrize("agent", ["forecast", "social", "geo", "predict", "pattern"])
    def test_aggregate_agents_run_with_aggregate_only(self, agent):
        d = _as("Policymaker", lambda: policy.decide(SC.current(), agent))
        assert not d.denied and "aggregate_only" in d.obligations

    @pytest.mark.parametrize("agent", ["network", "profile", "research", "brain", "osint", "linkage", "vigil"])
    def test_case_and_person_agents_are_refused(self, agent):
        d = _as("Policymaker", lambda: policy.decide(SC.current(), agent))
        assert d.denied and "aggregates only" in d.reason

    def test_the_query_agent_runs_and_limits_itself(self):
        d = _as("Policymaker", lambda: policy.decide(SC.current(), "query"))
        assert not d.denied


class TestTemplates:
    def test_listing_templates_are_refused(self):
        from app.services.zcql_repo import AggregateOnlyError, build_spec
        for tid, params in (("T1", {}), ("T12", {}), ("T21", {"accused_id": "ACC-KA-100017"})):
            with pytest.raises(AggregateOnlyError):
                _as("Policymaker", lambda: build_spec(tid, params))

    def test_aggregate_and_internal_templates_run(self):
        from app.services.zcql_repo import build_spec
        _as("Policymaker", lambda: build_spec("T13", {}))
        _as("Policymaker", lambda: build_spec("T14", {}))      # the server's own aggregation

    def test_other_roles_are_untouched(self):
        from app.services.zcql_repo import build_spec
        _as("Inspector", lambda: build_spec("T1", {}))


class TestQueryAgent:
    def _ask(self, role, text):
        from app.agents.heuristics import heuristic_select
        from app.agents.query_agent import query_agent_run
        return _as(role, lambda: asyncio.new_event_loop().run_until_complete(
            query_agent_run(text, lang="en", selector=heuristic_select, compose_llm=None)))

    def test_a_person_question_is_refused_plainly(self):
        res = self._ask("Policymaker", "show the FIR history of accused ACC-KA-100017")
        assert res["template_id"] == "UNRESOLVED" and res["rows"] == []
        assert "counts, trends, rates" in res["answer"]
        assert res["suggested_followups"]

    def test_a_listing_question_is_counted_not_listed(self):
        res = self._ask("Policymaker", "show the latest theft FIRs in Mysuru City")
        assert res["template_id"] == "T8" and res["rows"]
        assert all(set(r) <= {"n", "status"} for r in res["rows"])     # counts, never an FIR row

    def test_a_count_question_is_answered(self):
        res = self._ask("Policymaker", "Which districts had the most FIRs in 2025?")
        assert res["template_id"] != "UNRESOLVED" and res["rows"]
