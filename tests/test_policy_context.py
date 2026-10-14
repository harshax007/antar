"""Security context and policy (app/core/security_context.py, app/core/policy.py): one call
chain per request, a declared rule per agent, enforced before the agent runs and applied
to what it returns, and written on the tamper-evident row."""
import asyncio
import json
import sqlite3

import pytest

from app.core import orchestrator, policy, security_context as SC


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


async def _person_rows():
    return {"rows": [{"suspect_id": "S0001"}], "offenders": {"male": 3}, "note": "call 9876543210"}


def _as(role, fn):
    ctx, token = SC.begin("OF-1", role)
    try:
        return ctx, fn()
    finally:
        SC.end(token)


class TestContext:
    def test_one_call_chain_reaches_the_agent_and_its_result(self):
        ctx, (ok, _res, meta) = _as("Inspector", lambda: run(orchestrator.run_agent("network", _person_rows)))
        assert ok and meta["call_chain_id"] == ctx.call_chain_id and ctx.call_chain_id.startswith("cc-")
        assert ctx.decisions == [{"agent": "network", "outcome": "PERMIT"}]

    def test_the_context_follows_work_into_a_thread(self):
        async def work():
            return await asyncio.to_thread(lambda: SC.current().call_chain_id)
        ctx, seen = _as("Inspector", lambda: run(work()))
        assert seen == ctx.call_chain_id

    def test_it_does_not_leak_into_the_next_request(self):
        _as("Admin", lambda: None)
        assert SC.current() is None

    def test_system_work_is_named_and_never_an_officer(self):
        with SC.system("autonomous") as ctx:
            assert ctx.origin == "system" and ctx.officer == "system:autonomous"
            ok, _r, meta = run(orchestrator.run_agent("sentinel", _person_rows))
            assert ok and meta["call_chain_id"] == ctx.call_chain_id
        assert SC.current() is None

    def test_what_goes_on_the_audit_row_is_ids_and_decisions_only(self):
        ctx, _ = _as("Inspector", lambda: run(orchestrator.run_agent("network", _person_rows)))
        ctx.note_trace("trc-abc")
        row = ctx.for_audit()
        assert set(row) == {"call_chain_id", "trace_ids", "policy"}
        assert "9876543210" not in json.dumps(row) and "S0001" not in json.dumps(row)


class TestPolicy:
    @pytest.mark.parametrize("agent", ["network", "profile", "research", "osint", "brain", "linkage", "advocate_agent"])
    def test_a_constable_cannot_run_a_person_or_case_level_agent(self, agent):
        ran = []

        async def work():
            ran.append(1)
            return {}
        ctx, (ok, res, meta) = _as("Constable", lambda: run(orchestrator.run_agent(agent, work)))
        assert not ok and res is None and ran == []                 # refused before it started
        assert meta["status"] == "denied" and "Inspector" in meta["reason"]
        assert ctx.decisions[0]["outcome"] == "DENY"

    def test_a_refusal_does_not_count_against_the_agent(self):
        before = orchestrator._state["profile"].failures
        _as("Constable", lambda: run(orchestrator.run_agent("profile", _person_rows)))
        assert orchestrator._state["profile"].failures == before

    @pytest.mark.parametrize("agent", ["forecast", "geo", "pattern", "social", "query"])
    def test_a_constable_can_run_what_is_declared_for_them(self, agent):
        _ctx, (ok, _res, meta) = _as("Constable", lambda: run(orchestrator.run_agent(agent, _person_rows)))
        assert ok and meta["status"] == "ok"

    def test_an_aggregate_agent_cannot_return_people_whatever_its_code_does(self):
        _ctx, (ok, res, meta) = _as("Inspector", lambda: run(orchestrator.run_agent("social", _person_rows)))
        assert ok and "rows" not in res and res["offenders"] == {"male": 3}
        assert meta["policy"] == "PERMIT_WITH_OBLIGATIONS"

    def test_open_web_results_are_labelled_by_the_orchestrator(self):
        async def claims():
            return {"claims": [{"claim": "x"}]}
        _ctx, (ok, res, _m) = _as("Inspector", lambda: run(orchestrator.run_agent("osint", claims)))
        assert ok and res["unverified"] is True

    def test_obligations(self):
        r = {"rows": [1, 2, 3, 4], "note": "call 9876543210", "nested": {"names": ["a"], "k": [9, 8, 7]}}
        assert "9876543210" not in json.dumps(policy.apply_obligations(r, ("redact_pii",)))
        capped = policy.apply_obligations(r, ("row_cap:2",))
        assert capped["rows"] == [1, 2] and capped["nested"]["k"] == [9, 8]
        assert policy.apply_obligations(r, ("row_cap:not-a-number", "unknown")) == r

    def test_a_call_with_no_context_is_counted_not_refused(self):
        before = policy.counters()["unbound"]
        ok, _res, meta = run(orchestrator.run_agent("network", _person_rows))
        assert ok and meta["call_chain_id"] is None and policy.counters()["unbound"] == before + 1

    def test_an_alias_is_decided_as_its_agent(self):
        assert policy.decide(None, "prediction").outcome == policy.PERMIT
        ctx, d = _as("Constable", lambda: policy.decide(SC.current(), "alerts"))
        assert d.outcome == policy.PERMIT


class TestManifestDeclaration:
    def _block(self, **over):
        d = {"agent": "t", "kind": "worker", "role": "r", "module": "m::f", "graph_node": None, "routes": [],
             "sensitivity": "case", "min_role": "Inspector", "obligations": []}
        d.update(over)
        return d

    def test_every_agent_declares_its_sensitivity(self):
        from app.agents import manifest
        m = manifest.load()
        assert not m.errors
        assert all(a.sensitivity in policy.SENSITIVITIES and a.min_role for a in m.agents.values())

    @pytest.mark.parametrize("bad", [{"sensitivity": ""}, {"sensitivity": "secret"}, {"min_role": "Emperor"},
                                     {"obligations": ["delete_everything"]}])
    def test_a_block_without_a_valid_declaration_fails_the_build(self, bad):
        from app.agents import manifest
        errors = []
        assert manifest._build_agent(self._block(**bad), errors) is None and errors


class TestAuditRow:
    @pytest.fixture
    def ledger(self, tmp_path, monkeypatch):
        from app.services import audit_store as A
        db = str(tmp_path / "audit.db")
        monkeypatch.setattr(A, "DB_PATH", db)
        monkeypatch.setattr(A, "_log", [])
        monkeypatch.setattr(A, "_last_hash", A._GENESIS)
        monkeypatch.setattr(A, "_sync_to_catalyst_placeholder", lambda entry: None)
        A.init_db()
        return A, db

    def test_the_request_row_carries_the_chain_the_traces_and_the_decisions(self, ledger):
        A, db = ledger
        ctx, _ = _as("Constable", lambda: run(orchestrator.run_agent("profile", _person_rows)))
        ctx.note_trace("trc-1")
        A.record("OF-1", "Constable", "POST", "/api/chat/stream", 200, extra=ctx.for_audit())
        payload = json.loads(sqlite3.connect(db).execute("SELECT payload_json FROM audit_log").fetchone()[0])
        assert payload["call_chain_id"] == ctx.call_chain_id and payload["trace_ids"] == ["trc-1"]
        assert payload["policy"][0]["outcome"] == "DENY"
        assert A.verify_chain_report()["ok"] and A.verify_chain_report()["verified"] == 1

    def test_changing_a_recorded_decision_breaks_the_chain(self, ledger):
        A, _db = ledger
        A.record("OF-1", "Inspector", "GET", "/api/x", 200, extra={"call_chain_id": "cc-1", "policy": [{"agent": "profile", "outcome": "DENY"}]})
        A.record("OF-1", "Inspector", "GET", "/api/y", 200, extra={"call_chain_id": "cc-2"})
        A._log[0]["policy"] = [{"agent": "profile", "outcome": "PERMIT"}]
        rep = A.verify_chain_report()
        assert rep["ok"] is False and rep["broken_at_index"] == 0

    def test_an_answer_row_carries_digests_of_what_it_rested_on(self, ledger, monkeypatch):
        A, db = ledger
        from app.obs import trace
        monkeypatch.setattr(trace.settings, "OBS_ENABLED", True, raising=False)
        ctx, token = SC.begin("OF-1", "Inspector")
        try:
            trace.start(session_id="s1", surface="chat", question="thefts in Mysuru")
            trace.set_context(template_id="T1", params={"zones": ["Mysuru City"]},
                              rows=[{"fir_number": "SYN-2026-908137"}], citations=[])
            A.record_ai_reasoning("OF-1", "s1", "thefts in Mysuru", "1 theft.", ["query"], [], reasoning_id=None)
        finally:
            trace._current.set(None)
            SC.end(token)
        payload = json.loads(sqlite3.connect(db).execute("SELECT payload_json FROM audit_log").fetchone()[0])
        ev = payload["evidence"]
        assert payload["call_chain_id"] == ctx.call_chain_id and payload["role"] == "Inspector"
        assert ev["template_id"] == "T1" and ev["n_rows"] == 1 and ev["written_by"] == "offline"
        assert len(ev["rows_digest"]) == 16 and len(ev["params_digest"]) == 16
        assert "SYN-2026-908137" not in json.dumps(ev) and "Mysuru City" not in json.dumps(ev)   # digests, not the rows
        assert ev["trace_id"] in ctx.trace_ids
