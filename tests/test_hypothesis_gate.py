"""
Antar — Adversarial gate on the hypothesis confirm endpoint
===========================================================
Confirming promotes a hypothesis from Inferred to Known, after which downstream agents
treat it as fact and the Second Brain ingests it as institutional memory. These tests
cover the gate that stands in front of that transition.

The auditor's arithmetic is tested in test_advocate_agent.py. Here the verdict is
mostly stubbed, because what is under test is the GATE's behaviour for each verdict —
the two concerns are kept separate on purpose.

The properties that matter:
  • a doubted hypothesis cannot be promoted silently
  • an override is possible, but only in writing
  • a failure of the auditor is never mistaken for approval
  • rejection is never blocked
"""

import pytest
from fastapi import HTTPException

from app.api import hypothesis as H
from app.api.hypothesis import (HypothesisActionRequest, confirm_hypothesis,
                                reject_hypothesis, challenge_hypothesis, GATED_VERDICTS)
from app.services.product_store import put_product, get_product


def _stub_review(monkeypatch, verdict: str, **extra):
    """Pin the adversarial verdict so the gate can be tested in isolation."""
    async def _fake(_hyp):
        return {
            "verdict": verdict,
            "verdict_reason": f"stubbed {verdict}",
            "load_bearing_signals": extra.get("load_bearing", []),
            "discarded_signals": extra.get("discarded", []),
            "alternatives": [{"claim": "a competing explanation", "strength": "competing"}],
            "falsification_tests": [{"test": "t", "would_disprove": "d",
                                     "collect_action": "a", "statute": "BNSS Sec 94"}],
            "selection_effect": {"expected_false_matches": 12.0},
            "combined": {"posterior_probability": 0.11},
            "compiled_at": "2026-01-01T00:00:00+00:00",
        }
    monkeypatch.setattr(H, "_review", _fake)


def _store(hyp_id: str, **over) -> str:
    put_product(f"hypothesis:{hyp_id}", {
        "id": hyp_id, "kind": "association", "claim": "A is linked to B",
        "score": 0.85, "subject_ids": ["S0001", "S0002"],
        "signals": [{"name": "spatiotemporal co-presence (same zone: x)", "weight": 0.25}],
        **over}, ttl=600)
    return hyp_id


def _req(**kw):
    return HypothesisActionRequest(**{"officer": "OF-1004", "role": "Inspector", **kw})


# ── the gate ──────────────────────────────────────────────────────────────────
@pytest.mark.anyio
@pytest.mark.parametrize("verdict", sorted(GATED_VERDICTS))
async def test_gated_verdict_blocks_unacknowledged_confirm(monkeypatch, verdict):
    _stub_review(monkeypatch, verdict)
    hid = _store(f"HYP-GATE-{verdict}")
    with pytest.raises(HTTPException) as e:
        await confirm_hypothesis(hid, _req(reason="looks right to me"))
    assert e.value.status_code == 409
    assert e.value.detail["error"] == "adversarial_review_not_acknowledged"
    assert e.value.detail["verdict"] == verdict
    assert get_product(f"hypothesis:{hid}").get("state") != "confirmed", \
        "a blocked confirm must not mutate state"


@pytest.mark.anyio
async def test_block_response_carries_the_actual_argument(monkeypatch):
    """A 409 that just says 'no' is useless — the officer needs the case against it."""
    _stub_review(monkeypatch, "COLLAPSES", discarded=[{"signal": "s", "reason": "weak"}])
    with pytest.raises(HTTPException) as e:
        await confirm_hypothesis(_store("HYP-GATE-BODY"), _req(reason="x"))
    d = e.value.detail
    assert d["alternatives"] and d["falsification_tests"]
    assert d["verdict_reason"] and d["discarded_signals"]
    assert "acknowledge_challenge=true" in d["how_to_proceed"]


@pytest.mark.anyio
async def test_override_requires_a_written_reason(monkeypatch):
    _stub_review(monkeypatch, "COLLAPSES")
    hid = _store("HYP-GATE-NOREASON")
    for blank in ("", "   "):
        with pytest.raises(HTTPException) as e:
            await confirm_hypothesis(hid, _req(reason=blank, acknowledge_challenge=True))
        assert e.value.status_code == 422
        assert e.value.detail["error"] == "override_reason_required"
    assert get_product(f"hypothesis:{hid}").get("state") != "confirmed"


@pytest.mark.anyio
async def test_acknowledged_override_proceeds_and_is_recorded(monkeypatch):
    """The officer may overrule the system — but the overrule is the record."""
    _stub_review(monkeypatch, "COLLAPSES")
    hid = _store("HYP-GATE-OVERRIDE")
    res = await confirm_hypothesis(hid, _req(
        reason="Informant corroborates; source not in dataset", acknowledge_challenge=True))

    assert res["status"] == "confirmed"
    assert res["adversarial_override"] is True
    assert res["product"]["adversarial_review"]["verdict"] == "COLLAPSES"
    # verdict + override must both be inside the hashed audit reason
    assert "[adversarial:COLLAPSES]" in res["audit_entry"]["reason"]
    assert "OVERRIDE" in res["audit_entry"]["reason"]
    assert "Informant corroborates" in res["audit_entry"]["reason"]
    assert "hash" in res["audit_entry"]


@pytest.mark.anyio
async def test_surviving_verdict_confirms_without_acknowledgement(monkeypatch):
    """The gate must not stand in the way of well-evidenced work."""
    _stub_review(monkeypatch, "SURVIVES", load_bearing=["shared hard key"])
    res = await confirm_hypothesis(_store("HYP-GATE-OK"), _req(reason="corroborated"))
    assert res["status"] == "confirmed"
    assert res["adversarial_override"] is False
    assert res["product"]["adversarial_review"]["verdict"] == "SURVIVES"
    assert "[adversarial:SURVIVES]" in res["audit_entry"]["reason"]
    assert "OVERRIDE" not in res["audit_entry"]["reason"]


# ── failure must never read as approval ───────────────────────────────────────
@pytest.mark.anyio
async def test_unassessable_does_not_gate(monkeypatch):
    """No resolvable subjects means there is no argument to answer. Blocking there would
    be the system refusing on its own blind spot."""
    _stub_review(monkeypatch, "UNASSESSABLE")
    res = await confirm_hypothesis(_store("HYP-GATE-UNASSESS"), _req(reason="ok"))
    assert res["status"] == "confirmed"
    assert res["adversarial_override"] is False
    assert "UNASSESSABLE" not in GATED_VERDICTS


@pytest.mark.anyio
async def test_broken_auditor_degrades_to_unassessable_not_to_silence(monkeypatch):
    """If advocate_agent raises, the confirm proceeds (officers are not held hostage to
    a broken auditor) but the record must say the review did not happen."""
    def _boom(_h):
        raise RuntimeError("index corrupt")
    monkeypatch.setattr("app.agents.advocate_agent.challenge", _boom)

    res = await confirm_hypothesis(_store("HYP-GATE-BROKEN"), _req(reason="proceed"))
    assert res["status"] == "confirmed"
    assert res["adversarial_review"]["verdict"] == "UNASSESSABLE"
    assert "unavailable" in res["adversarial_review"]["verdict_reason"]
    # The cause is logged under a reference, not shown to the officer (docs/SECURITY.md §2).
    assert "index corrupt" not in res["adversarial_review"]["verdict_reason"]
    assert "ref ERR-" in res["adversarial_review"]["verdict_reason"]
    assert res["product"]["adversarial_review"]["verdict"] == "UNASSESSABLE"


# ── ordering and precedence ───────────────────────────────────────────────────
@pytest.mark.anyio
async def test_rbac_is_enforced_before_the_adversarial_gate(monkeypatch):
    """An unauthorised caller must get 403, never a 409 that leaks the review."""
    _stub_review(monkeypatch, "COLLAPSES")
    with pytest.raises(HTTPException) as e:
        await confirm_hypothesis(_store("HYP-GATE-RBAC"),
                                 _req(role="Constable", reason="x"))
    assert e.value.status_code == 403


# ── rejection ─────────────────────────────────────────────────────────────────
@pytest.mark.anyio
async def test_reject_is_never_gated(monkeypatch):
    _stub_review(monkeypatch, "COLLAPSES")
    res = await reject_hypothesis(_store("HYP-GATE-REJ"), _req(reason="alibi verified"))
    assert res["status"] == "rejected"


@pytest.mark.anyio
async def test_reject_records_whether_officer_agreed_with_the_auditor(monkeypatch):
    """Agreement rate is the calibration signal for the adversarial layer itself."""
    _stub_review(monkeypatch, "COLLAPSES")
    agreed = await reject_hypothesis(_store("HYP-GATE-AGREE"), _req(reason="alibi"))
    assert agreed["adversarial_agreement"] is True

    _stub_review(monkeypatch, "SURVIVES")
    disagreed = await reject_hypothesis(_store("HYP-GATE-DISAGREE"), _req(reason="alibi"))
    assert disagreed["adversarial_agreement"] is False
    assert disagreed["product"]["adversarial_review"]["verdict"] == "SURVIVES"


# ── read-only preview ─────────────────────────────────────────────────────────
@pytest.mark.anyio
async def test_challenge_endpoint_is_read_only(monkeypatch):
    """This is what sits next to the Confirm button; it must not act."""
    _stub_review(monkeypatch, "COLLAPSES")
    hid = _store("HYP-GATE-PREVIEW")
    out = await challenge_hypothesis(hid)
    assert out["would_gate_confirm"] is True
    assert out["review"]["verdict"] == "COLLAPSES"
    assert get_product(f"hypothesis:{hid}").get("state") is None, \
        "previewing the challenge must not change hypothesis state"


@pytest.mark.anyio
async def test_challenge_preview_agrees_with_the_gate(monkeypatch):
    """would_gate_confirm must predict the confirm endpoint's actual behaviour."""
    for verdict in ("COLLAPSES", "WEAKENED", "SURVIVES", "UNASSESSABLE"):
        _stub_review(monkeypatch, verdict)
        hid = _store(f"HYP-GATE-PRED-{verdict}")
        predicted = (await challenge_hypothesis(hid))["would_gate_confirm"]
        try:
            await confirm_hypothesis(hid, _req(reason="x"))
            actually_gated = False
        except HTTPException as e:
            actually_gated = e.value.status_code if False else True
        assert predicted == actually_gated, f"preview disagreed with gate for {verdict}"


# ── against the real auditor, no stubbing ─────────────────────────────────────
@pytest.mark.anyio
async def test_real_weak_hypothesis_is_gated_end_to_end():
    """No monkeypatch: a hypothesis built only from population-typical traits must be
    refused by the live auditor."""
    from app.services.zcql_local import _world
    from app.agents import advocate_agent as da
    da.reset_index()

    common = [s for s in _world()["suspects"]
              if (s.get("address_zone") or "").strip().lower() == "bengaluru city"
              and s.get("occupation") == "farmer"][:2]
    if len(common) < 2:
        pytest.skip("dataset has no two suspects sharing zone and occupation")

    hid = _store("HYP-GATE-REAL",
                 subject_ids=[common[0]["suspect_id"], common[1]["suspect_id"]],
                 signals=[{"name": "spatiotemporal co-presence (same zone: bengaluru city)",
                           "weight": 0.25},
                          {"name": "MO similarity (shared pattern: farmer)", "weight": 0.25}])
    with pytest.raises(HTTPException) as e:
        await confirm_hypothesis(hid, _req(reason="hunch"))
    assert e.value.status_code == 409
    assert e.value.detail["verdict"] == "COLLAPSES"
    assert e.value.detail["falsification_tests"]


@pytest.mark.anyio
async def test_legacy_hypothesis_without_subjects_still_confirms():
    """Backwards compatibility: the pre-existing lifecycle test confirms an id that was
    never stored, so it has no subject_ids. That path must keep working."""
    from app.agents import advocate_agent as da
    da.reset_index()
    res = await confirm_hypothesis("HYP-LEGACY-NO-SUBJECTS", _req(reason="legacy path"))
    assert res["status"] == "confirmed"
    assert res["adversarial_review"]["verdict"] == "UNASSESSABLE"
