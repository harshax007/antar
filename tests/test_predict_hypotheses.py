"""Predict hypotheses (app/api/pattern_predict.py::hypotheses_for): only what the research
agent proposed and the advocate agent checked is returned. No prepared text, no filler."""
import pytest

from app.api import pattern_predict as PP


def _hyp(a, b, score):
    return {"id": f"HYP-{a}-{b}", "kind": "association", "subject_ids": [a, b], "score": score,
            "claim": f"{a} is likely linked to {b}", "signals": [{"name": "shared zone", "weight": 0.3}]}


@pytest.fixture
def wired(monkeypatch):
    from app.agents import advocate_agent, research_agent
    from app.services import product_store
    state = {"proposed": [], "verdicts": {}, "stored": []}
    monkeypatch.setattr(research_agent, "run_research", lambda zone, world=None: {"inferred_hypotheses": state["proposed"]})
    monkeypatch.setattr(advocate_agent, "challenge", lambda h, world=None: {
        "verdict": state["verdicts"].get(h["id"], "COLLAPSES"), "verdict_reason": "22.2 expected false matches",
        "combined": {"posterior_probability": 0.04}, "selection_effect": {"expected_false_matches": 22.2},
        "falsification_tests": [{"test": "Read the shared FIR"}] * 9, "population": 1000})
    monkeypatch.setattr(product_store, "put_product", lambda key, value, ttl=0: state["stored"].append(key))
    return state


def test_a_district_with_no_proposal_returns_nothing(wired):
    assert PP.hypotheses_for("Raichur") == {"zone": "Raichur", "hypotheses": [], "examined": 0,
                                           "method": PP.hypotheses_for("Raichur")["method"]}
    assert PP.hypotheses_for("  ")["hypotheses"] == []


def test_each_proposal_carries_its_check_and_mirrors_are_one_link(wired):
    wired["proposed"] = [_hyp("S1", "S2", 0.6), _hyp("S2", "S1", 0.6), _hyp("S3", "S4", 0.9), _hyp("S5", "S6", 0.7)]
    wired["verdicts"] = {"HYP-S5-S6": "SURVIVES", "HYP-S3-S4": "WEAKENED"}
    out = PP.hypotheses_for("Mysuru City")
    assert out["examined"] == 3                                     # S1-S2 and S2-S1 are one link
    assert [h["id"] for h in out["hypotheses"]] == ["HYP-S5-S6", "HYP-S3-S4", "HYP-S1-S2"]   # what stands up comes first
    first = out["hypotheses"][0]
    assert first["verdict"] == "SURVIVES" and first["posterior_probability"] == 0.04
    assert first["expected_false_matches"] == 22.2 and len(first["falsification_tests"]) == 4
    assert first["signals"] == [{"name": "shared zone", "weight": 0.3}]
    # stored, so Confirm and Reject act on the record that was shown
    assert set(wired["stored"]) == {"hypothesis:HYP-S1-S2", "hypothesis:HYP-S3-S4", "hypothesis:HYP-S5-S6"}


def test_a_failing_check_is_not_an_endorsement(wired, monkeypatch):
    from app.agents import advocate_agent
    wired["proposed"] = [_hyp("S1", "S2", 0.6)]
    monkeypatch.setattr(advocate_agent, "challenge", lambda h, world=None: (_ for _ in ()).throw(RuntimeError("boom")))
    h = PP.hypotheses_for("Mysuru City")["hypotheses"][0]
    assert h["verdict"] == "UNASSESSABLE" and "boom" not in (h["verdict_reason"] or "")


def test_the_page_holds_no_prepared_hypothesis():
    import pathlib
    src = pathlib.Path("antar-frontend/app/(app)/predict/PredictScreen.jsx").read_text(encoding="utf-8")
    for canned in ("HYP-001-COLD", "HYP-002-LINK", "black Pulsar", "Highway Robbery Syndicate"):
        assert canned not in src
