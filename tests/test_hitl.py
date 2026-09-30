"""
Antar — Human-in-the-Loop approvals
===================================
Every guarantee listed in app/core/hitl.py has a test here. They run against a temporary
database so they never touch main.db or the real audit log.
"""

import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

import app.core.db_path as db_path_mod
from app.core import hitl
from app.services import audit_store

OPS = dict(officer="U-7001", role="Admin")
APPROVER = dict(officer="U-9001", role="Approver")
OTHER_APPROVER = dict(officer="U-9002", role="Approver")

WATCH = {"watch_type": "entity", "target": "ACC-831453", "label": "Habitual offender watch"}
PATROL = {"zone": "Bengaluru City", "units": 4, "duration_hours": 8, "shift": "night", "crime_focus": "chain snatching"}
JUST = "Three chain snatchings in 48 hours along the same corridor."


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    db = str(tmp_path / "hitl_test.db")
    monkeypatch.setattr(db_path_mod, "DB_PATH", db)
    monkeypatch.setattr(audit_store, "DB_PATH", db)
    audit_store.init_db()
    audit_store._log.clear()
    audit_store._last_hash = "0" * 64
    hitl._DEPLOYMENTS.clear()
    yield
    hitl._DEPLOYMENTS.clear()


def _propose(kind="watchlist_add", payload=None, **who):
    who = who or OPS
    return hitl.propose(kind, dict(payload or (WATCH if kind == "watchlist_add" else PATROL)),
                        justification=JUST, evidence=[{"k": "source", "v": "test"}], **who)


def _approve(a, reason="Corroborated by beat officer report.", **who):
    who = who or APPROVER
    return hitl.approve(a["action_id"], reason=reason, reviewed_hash=a["payload_hash"], **who)


def _events():
    return [e["type"] for e in audit_store._log if str(e.get("type", "")).startswith("hitl_")]


# ── proposing ─────────────────────────────────────────────────────────────────
def test_proposal_is_parked_not_executed():
    from app.agents import sentinel_agent
    before = len(sentinel_agent.list_watches())
    a = _propose()
    assert a["status"] == "PENDING"
    assert a["integrity_ok"] is True
    assert len(sentinel_agent.list_watches()) == before, "nothing may take effect before approval"
    assert "hitl_proposed" in _events()


def test_approver_role_cannot_propose():
    with pytest.raises(hitl.HitlError) as e:
        _propose(**APPROVER)
    assert e.value.code == 403 and e.value.error == "role_cannot_propose"


@pytest.mark.parametrize("just", ["", "   ", "ok", "because"])
def test_justification_is_required(just):
    with pytest.raises(hitl.HitlError) as e:
        hitl.propose("watchlist_add", dict(WATCH), justification=just, **OPS)
    assert e.value.error == "justification_required"


@pytest.mark.parametrize("bad", [
    {"zone": "", "units": 2, "duration_hours": 4, "shift": "night"},
    {"zone": "X", "units": 0, "duration_hours": 4, "shift": "night"},
    {"zone": "X", "units": 50, "duration_hours": 4, "shift": "night"},
    {"zone": "X", "units": 2, "duration_hours": 200, "shift": "night"},
    {"zone": "X", "units": 2, "duration_hours": 4, "shift": "lunch"},
])
def test_invalid_patrol_payloads_are_refused(bad):
    with pytest.raises(hitl.HitlError) as e:
        hitl.propose("patrol_redeployment", bad, justification=JUST, **OPS)
    assert e.value.code == 422


def test_unknown_action_type_is_refused():
    with pytest.raises(hitl.HitlError) as e:
        hitl.propose("launch_drone", {}, justification=JUST, **OPS)
    assert e.value.error == "unknown_action_type"


def test_identical_pending_proposal_is_not_queued_twice():
    a = _propose()
    b = _propose()
    assert b["action_id"] == a["action_id"] and b.get("duplicate") is True
    assert len(hitl.list_actions("pending")) == 1


def test_vigil_rejected_proposal_is_blocked():
    """Prohibited demographic targeting never even reaches the queue."""
    with pytest.raises(hitl.HitlError) as e:
        hitl.propose("watchlist_add", {"watch_type": "pattern", "target": "caste group X", "label": "caste watch"},
                     justification="Watch this caste community for theft.", **OPS)
    assert e.value.error == "compliance_rejected"
    assert hitl.list_actions("all") == []


def test_compliance_receipt_travels_with_the_proposal():
    a = _propose()
    assert a["compliance"] and a["compliance"]["status"] in {"APPROVED", "FLAGGED", "UNAVAILABLE"}


# ── deciding ──────────────────────────────────────────────────────────────────
def test_approval_executes_the_watch():
    from app.agents import sentinel_agent
    a = _propose(payload={"watch_type": "entity", "target": "ACC-HITL-TEST", "label": "t"})
    done = _approve(a)
    assert done["status"] == "EXECUTED"
    assert done["decided_by"] == "U-9001"
    assert any(w["target"] == "ACC-HITL-TEST" for w in sentinel_agent.list_watches())
    assert _events()[-3:] == ["hitl_proposed", "hitl_approved", "hitl_executed"]


def test_approval_issues_a_patrol_order():
    a = _propose("patrol_redeployment")
    done = _approve(a)
    assert done["status"] == "EXECUTED"
    orders = hitl.active_deployments()
    assert orders and orders[0]["zone"] == "Bengaluru City"
    assert orders[0]["authorised_by"] == "U-9001" and orders[0]["requested_by"] == "U-7001"


def test_self_approval_is_forbidden_even_with_an_approver_role():
    """Four eyes: the proposer can never be the decider, whatever role they claim."""
    a = _propose()
    with pytest.raises(hitl.HitlError) as e:
        hitl.approve(a["action_id"], officer="U-7001", role="Approver", reason="looks fine to me",
                     reviewed_hash=a["payload_hash"])
    assert e.value.error == "self_approval_forbidden"
    assert hitl.get(a["action_id"])["status"] == "PENDING"


@pytest.mark.parametrize("role", ["Admin", "Inspector", "Analyst", "Officer", ""])
def test_non_approver_roles_cannot_decide(role):
    a = _propose()
    with pytest.raises(hitl.HitlError) as e:
        hitl.approve(a["action_id"], officer="U-5555", role=role, reason="approving this", reviewed_hash=a["payload_hash"])
    assert e.value.code == 403


def test_decision_reason_is_required():
    a = _propose()
    with pytest.raises(hitl.HitlError) as e:
        _approve(a, reason="ok")
    assert e.value.error == "reason_required"


def test_stale_review_hash_is_refused():
    """The approver must be approving the exact version they looked at."""
    a = _propose()
    with pytest.raises(hitl.HitlError) as e:
        hitl.approve(a["action_id"], reason="Corroborated by patrol.", reviewed_hash="0" * 64, **APPROVER)
    assert e.value.error == "stale_review"


def test_tampered_stored_payload_cannot_be_approved():
    a = _propose("patrol_redeployment")
    conn = sqlite3.connect(db_path_mod.DB_PATH)
    conn.execute("UPDATE hitl_actions SET payload_json=? WHERE action_id=?",
                 ('{"zone":"Bengaluru City","units":20,"duration_hours":8,"shift":"night","crime_focus":"x"}', a["action_id"]))
    conn.commit(); conn.close()
    fresh = hitl.get(a["action_id"])
    assert fresh["integrity_ok"] is False
    with pytest.raises(hitl.HitlError) as e:
        _approve(a)
    assert e.value.error == "integrity_failure"
    assert "hitl_integrity_failure" in _events()
    assert hitl.active_deployments() == []


def test_decisions_are_final():
    a = _propose()
    _approve(a)
    with pytest.raises(hitl.HitlError) as e:
        hitl.reject(a["action_id"], reason="changed my mind", **OTHER_APPROVER)
    assert e.value.code == 409


def test_rejection_is_recorded_and_executes_nothing():
    from app.agents import sentinel_agent
    a = _propose(payload={"watch_type": "entity", "target": "ACC-REJECT-ME", "label": "t"})
    r = hitl.reject(a["action_id"], reason="Insufficient grounds for surveillance.", **APPROVER)
    assert r["status"] == "REJECTED" and r["decision_reason"].startswith("Insufficient")
    assert not any(w["target"] == "ACC-REJECT-ME" for w in sentinel_agent.list_watches())
    assert "hitl_rejected" in _events()


def test_expired_proposal_cannot_be_approved():
    a = _propose()
    conn = sqlite3.connect(db_path_mod.DB_PATH)
    conn.execute("UPDATE hitl_actions SET expires_at=? WHERE action_id=?", (time.time() - 1, a["action_id"]))
    conn.commit(); conn.close()
    assert hitl.get(a["action_id"])["status"] == "EXPIRED"
    with pytest.raises(hitl.HitlError) as e:
        _approve(a)
    assert e.value.code == 409
    assert "hitl_expired" in _events()


def test_failed_execution_is_recorded_not_hidden(monkeypatch):
    def boom(p, a):
        raise RuntimeError("dispatch system offline")
    monkeypatch.setitem(hitl.ACTION_TYPES["patrol_redeployment"], "execute", boom)
    a = _propose("patrol_redeployment")
    done = _approve(a)
    assert done["status"] == "FAILED" and "offline" in done["error"]
    assert "hitl_failed" in _events()


# ── withdrawing ───────────────────────────────────────────────────────────────
def test_only_the_proposer_can_withdraw():
    a = _propose()
    with pytest.raises(hitl.HitlError) as e:
        hitl.withdraw(a["action_id"], officer="U-1234", role="Admin", reason="not needed anymore")
    assert e.value.error == "not_proposer"
    w = hitl.withdraw(a["action_id"], reason="Suspect already in custody.", **OPS)
    assert w["status"] == "WITHDRAWN"


# ── audit chain ───────────────────────────────────────────────────────────────
def test_every_step_is_on_a_verifiable_chain_that_survives_reload():
    a = _propose("patrol_redeployment")
    _approve(a)
    b = _propose()
    hitl.reject(b["action_id"], reason="Not proportionate to the evidence.", **APPROVER)

    hitl_rows = [e for e in audit_store._log if str(e.get("type", "")).startswith("hitl_")]
    assert all(e["payload_hash"] in (a["payload_hash"], b["payload_hash"]) for e in hitl_rows)
    audit_store.load_from_db()
    assert audit_store.verify_chain() is True


# ── stats + listing ───────────────────────────────────────────────────────────
def test_stats_and_filters():
    a = _propose("patrol_redeployment")
    _propose()
    s = hitl.stats()
    assert s["pending"] == 2 and s["pending_high_risk"] == 1
    _approve(a)
    assert len(hitl.list_actions("pending")) == 1
    assert len(hitl.list_actions("decided")) == 1
    assert len(hitl.list_actions("all", officer="U-7001")) == 2


# ── HTTP layer ────────────────────────────────────────────────────────────────
def _client():
    from main import app
    return TestClient(app)


def _h(who):
    return {"X-Officer": who["officer"], "X-Role": who["role"]}


def test_http_full_flow_and_status_codes():
    c = _client()
    r = c.post("/api/hitl/propose", headers=_h(OPS),
               json={"action_type": "patrol_redeployment", "payload": PATROL, "justification": JUST})
    assert r.status_code == 201, r.text
    a = r.json()

    assert c.post(f"/api/hitl/{a['action_id']}/approve", headers=_h(OPS),
                  json={"reason": "approving my own", "payload_hash": a["payload_hash"]}).status_code == 403
    assert c.post(f"/api/hitl/{a['action_id']}/approve", headers=_h(APPROVER),
                  json={"reason": "Corroborated by control room.", "payload_hash": "bad"}).status_code == 409

    ok = c.post(f"/api/hitl/{a['action_id']}/approve", headers=_h(APPROVER),
                json={"reason": "Corroborated by control room.", "payload_hash": a["payload_hash"]})
    assert ok.status_code == 200 and ok.json()["status"] == "EXECUTED"
    assert c.get("/api/hitl/deployments").json()["count"] == 1
    assert c.get("/api/hitl/stats").json()["by_status"]["EXECUTED"] == 1
    assert c.get("/api/hitl/NOPE").status_code == 404


def test_sentinel_watch_endpoint_now_requires_approval():
    """POST /api/sentinel/watches used to register instantly. It must now park the request."""
    from app.agents import sentinel_agent
    c = _client()
    r = c.post("/api/sentinel/watches", headers=_h(OPS),
               json={"watch_type": "entity", "target": "ACC-VIA-SENTINEL", "label": "t", "justification": JUST})
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "pending_approval"
    assert not any(w["target"] == "ACC-VIA-SENTINEL" for w in sentinel_agent.list_watches())
