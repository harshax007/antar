"""
Antar — Devil's Advocate tests
==============================
The point of this agent is to be RIGHT about weak evidence, so the tests are built
around hand-checkable arithmetic rather than snapshots. Every expected number here can
be recomputed from the counts the assertion cites.

Two properties matter most and get the most coverage:
  • a common attribute must NOT be treated as corroboration (the base-rate check)
  • a genuinely rare attribute must NOT be dismissed as a scan artefact (the bug where
    the likelihood ratio was wrongly used for the multiple-comparisons arithmetic)
"""

import math

import pytest

from app.agents import devils_advocate as da


# ── synthetic world: exact counts, so every LR is checkable by hand ───────────
def _world(n_common_zone: int = 400, total: int = 1000) -> dict:
    """`total` suspects. n_common_zone of them live in COMMONVILLE, the rest in RAREVILLE.
    Everyone is a 'farmer' except S0001/S0002, who share a unique phone hash."""
    suspects = []
    for i in range(1, total + 1):
        sid = f"S{i:04d}"
        suspects.append({
            "suspect_id": sid,
            "full_name": f"Person {i}",
            "address_zone": "COMMONVILLE" if i <= n_common_zone else "RAREVILLE",
            "occupation": "farmer",
            "phone_hash": "PH-SHARED" if i in (1, 2) else f"PH-{i:06d}",
        })
    return {"suspects": suspects, "crime_suspects": [], "crimes": []}


def _hyp(signals, *, kind="association", ids=("S0001", "S0002")):
    return {"id": "HYP-T", "kind": kind, "subject_ids": list(ids),
            "claim": "test claim", "score": 0.9, "signals": signals}


ZONE_SIG = [{"name": "spatiotemporal co-presence (same zone: commonville)", "weight": 0.25}]
MO_SIG = [{"name": "MO similarity (shared pattern: farmer)", "weight": 0.25}]
KEY_SIG = [{"name": "shared hard key (phone/vehicle/upi)", "weight": 0.55}]


# ── base-rate arithmetic ──────────────────────────────────────────────────────
def test_likelihood_ratio_matches_hand_calculation():
    """400 of 1000 share the zone -> p = 399/999, LR = 1/p, bits = log2(LR)."""
    w = _world()
    c = da.challenge(_hyp(ZONE_SIG), world=w)
    a = c["signals"][0]
    assert a["n_sharing"] == 400 and a["population"] == 1000
    assert a["p_coincidence"] == pytest.approx(399 / 999, rel=1e-3)
    assert a["likelihood_ratio"] == pytest.approx(999 / 399, rel=1e-2)
    assert a["bits"] == pytest.approx(math.log2(999 / 399), abs=0.01)


def test_common_attribute_is_negligible_and_collapses():
    """A 40%-of-population trait must never read as corroboration."""
    c = da.challenge(_hyp(ZONE_SIG), world=_world())
    assert c["signals"][0]["strength"] == "negligible"
    assert c["signals"][0]["load_bearing"] is False
    assert c["verdict"] == "COLLAPSES"
    assert not c["load_bearing_signals"]


def test_rarer_attribute_earns_more_bits_than_common_one():
    """Monotonicity: rarer must always score strictly higher."""
    common = da.challenge(_hyp(ZONE_SIG), world=_world(n_common_zone=400))["signals"][0]
    da.reset_index()
    rare = da.challenge(_hyp(ZONE_SIG), world=_world(n_common_zone=5))["signals"][0]
    assert rare["bits"] > common["bits"]
    assert rare["likelihood_ratio"] > common["likelihood_ratio"]


def test_unique_hard_key_is_decisive_and_not_a_scan_artefact():
    """Regression: the LR was once used for the selection effect, which made a 2-of-1000
    phone-hash match look like a scan artefact. A rare hard key must clear that check."""
    c = da.challenge(_hyp(KEY_SIG, kind="identity"), world=_world())
    a = c["signals"][0]
    assert a["n_sharing"] == 2
    assert a["strength"] in ("decisive", "strong")
    assert a["load_bearing"] is True
    assert c["selection_effect"]["expected_false_matches"] < 1.0
    assert c["selection_effect"]["prosecutors_fallacy_risk"] is False
    assert c["verdict"] != "COLLAPSES"


def test_single_identifier_against_its_own_prior_is_only_break_even():
    """One near-unique identifier (LR ~= N) against an identity prior of 1/N lands the
    posterior on ~50% BY CONSTRUCTION. That is a coin flip, not a finding, and must not
    be reported as SURVIVES — the verdict would otherwise turn on the 4th decimal."""
    c = da.challenge(_hyp(KEY_SIG, kind="identity"), world=_world())
    assert c["combined"]["posterior_probability"] == pytest.approx(0.5, abs=0.01)
    assert c["verdict"] == "WEAKENED"
    assert "Collect more" in c["verdict_reason"]


def test_two_independent_strong_signals_survive():
    """SURVIVES has to be reachable, and this is what it takes: corroboration from a
    second genuinely discriminating signal, not from a population-typical one."""
    w = _world()
    w["crime_suspects"] = [{"crime_id": "C1", "suspect_id": "S0001"},
                           {"crime_id": "C1", "suspect_id": "S0002"}]
    c = da.challenge(_hyp(KEY_SIG + [{"name": "Adamic-Adar >= 0.5 normalized (shared case "
                                              "records: C1)", "weight": 0.35}],
                          kind="identity"), world=w)
    assert len(c["load_bearing_signals"]) == 2
    assert not c["discarded_signals"]
    assert c["combined"]["posterior_probability"] > 0.9
    assert c["verdict"] == "SURVIVES"


def test_collision_rate_is_not_the_inverse_likelihood_ratio():
    """The two probabilities are different quantities; conflating them was the bug.

    For a unique-ish hard key the collision rate is far below 1/LR, because most values
    in the column are unique while the LR only looks at the observed value.
    """
    c = da.challenge(_hyp(KEY_SIG, kind="identity"), world=_world())
    a = c["signals"][0]
    assert a["collision_p"] < (1.0 / a["likelihood_ratio"]) / 10


# ── the occupation-as-MO data defect ──────────────────────────────────────────
def test_occupation_masquerading_as_mo_is_flagged_and_stripped():
    """research_agent reads primary_crime then falls back to occupation. When it falls
    back, 'MO similarity' is comparing jobs and must not carry inferential load."""
    c = da.challenge(_hyp(MO_SIG), world=_world())
    a = c["signals"][0]
    assert a["attribute"] == "occupation"
    assert a["mislabelled_as_mo"] is True
    assert a["load_bearing"] is False, "a shared job title must never be load-bearing"
    assert "not a shared modus operandi" in a["why"]
    assert any("no MO evidence" in alt["claim"] for alt in c["alternatives"])


def test_real_mo_field_is_not_flagged():
    """When primary_crime IS populated, the signal is a genuine MO comparison."""
    w = _world()
    for s in w["suspects"][:2]:
        s["primary_crime"] = "chain_snatching"
    c = da.challenge(_hyp([{"name": "MO similarity (shared pattern: chain_snatching)",
                            "weight": 0.25}]), world=w)
    a = c["signals"][0]
    assert a["attribute"] == "primary_crime"
    assert a.get("mislabelled_as_mo") is False


def test_correlated_signals_are_priced_conditionally():
    """Zone and occupation correlate; pricing the MO signal at its global rate would
    double-count the zone signal. Sharing a zone switches it to the within-zone rate."""
    c = da.challenge(_hyp(ZONE_SIG + MO_SIG), world=_world())
    mo = next(a for a in c["signals"] if a["signal_kind"] == "mo")
    assert mo["conditional_on"] == "commonville"
    assert mo["population"] == 400, "must be priced within the zone, not over all 1000"


# ── selection effect / prosecutor's fallacy ───────────────────────────────────
def test_large_scan_flags_prosecutors_fallacy():
    c = da.challenge(_hyp(ZONE_SIG), world=_world(), pairs_examined=10_000_000)
    assert c["selection_effect"]["prosecutors_fallacy_risk"] is True
    assert c["verdict"] == "COLLAPSES"
    assert any("scan artefact" in alt["claim"] for alt in c["alternatives"])


def test_small_scan_does_not_flag():
    c = da.challenge(_hyp(KEY_SIG, kind="identity"), world=_world(), pairs_examined=10)
    assert c["selection_effect"]["prosecutors_fallacy_risk"] is False


def test_expected_false_matches_scales_with_scan_size():
    small = da.challenge(_hyp(KEY_SIG), world=_world(), pairs_examined=100)
    big = da.challenge(_hyp(KEY_SIG), world=_world(), pairs_examined=100_000)
    assert big["selection_effect"]["expected_false_matches"] > \
           small["selection_effect"]["expected_false_matches"]


# ── priors come from the data ─────────────────────────────────────────────────
def test_identity_prior_is_one_over_population():
    c = da.challenge(_hyp(KEY_SIG, kind="identity"), world=_world())
    assert c["prior"]["odds"] == pytest.approx(1 / 999, rel=1e-3)
    assert "same person" in c["prior"]["basis"]


def test_association_prior_is_derived_from_co_accusal_data():
    """Not a guessed constant — it must come from the mean co-accused degree."""
    w = _world()
    w["crime_suspects"] = [{"crime_id": "C1", "suspect_id": "S0001"},
                           {"crime_id": "C1", "suspect_id": "S0002"},
                           {"crime_id": "C2", "suspect_id": "S0003"},
                           {"crime_id": "C2", "suspect_id": "S0004"}]
    c = da.challenge(_hyp(KEY_SIG, kind="association"), world=w)
    assert c["prior"]["odds"] == pytest.approx(1.0 / 999, rel=1e-3)   # mean degree 1.0
    assert "co-accused" in c["prior"]["basis"]


# ── falsification tests ───────────────────────────────────────────────────────
def test_every_challenge_offers_a_falsification_test():
    for sig in (ZONE_SIG, MO_SIG, KEY_SIG):
        c = da.challenge(_hyp(sig), world=_world())
        assert c["falsification_tests"], f"no falsification test for {sig[0]['name']}"
        for t in c["falsification_tests"]:
            assert t["test"] and t["would_disprove"] and t["collect_action"] and t["statute"]


def test_hard_key_falsification_names_the_statute():
    c = da.challenge(_hyp(KEY_SIG), world=_world())
    t = c["falsification_tests"][0]
    assert "BNSS" in t["statute"]
    assert "shared device" in t["would_disprove"] or "family" in t["would_disprove"]


# ── robustness ────────────────────────────────────────────────────────────────
def test_unresolvable_subjects_are_unassessable_not_approved():
    """Failure must never read as endorsement."""
    c = da.challenge(_hyp(KEY_SIG, ids=("S9999", "S8888")), world=_world())
    assert c["verdict"] == "UNASSESSABLE"
    assert c["verdict"] != "SURVIVES"


def test_unknown_signal_is_recorded_not_silently_ignored():
    c = da.challenge(_hyp([{"name": "astrological compatibility", "weight": 0.9}]),
                     world=_world())
    a = c["signals"][0]
    assert a["strength"] == "unassessed"
    assert a["load_bearing"] is False
    assert c["verdict"] == "COLLAPSES"


def test_empty_signal_list_collapses():
    c = da.challenge(_hyp([]), world=_world())
    assert c["verdict"] == "COLLAPSES"


def test_challenge_never_raises_on_malformed_input():
    for bad in ({}, {"subject_ids": []}, {"subject_ids": ["S0001"], "signals": None},
                {"subject_ids": ["S0001", "S0002"], "signals": [{}]}):
        c = da.challenge(bad, world=_world())
        assert c["verdict"] in ("COLLAPSES", "WEAKENED", "SURVIVES", "UNASSESSABLE")


def test_verdict_vocabulary_is_closed():
    c = da.challenge(_hyp(KEY_SIG), world=_world())
    assert c["verdict"] in {"SURVIVES", "WEAKENED", "COLLAPSES", "UNASSESSABLE"}


def test_output_is_deterministic():
    """Same input, same verdict and same arithmetic — no sampling, no LLM."""
    a = da.challenge(_hyp(ZONE_SIG + MO_SIG), world=_world())
    b = da.challenge(_hyp(ZONE_SIG + MO_SIG), world=_world())
    assert a["verdict"] == b["verdict"]
    assert a["combined"]["bits"] == b["combined"]["bits"]
    assert a["selection_effect"]["expected_false_matches"] == \
           b["selection_effect"]["expected_false_matches"]


def test_independence_caveat_is_always_stated():
    """The combination assumes conditional independence; that must never be silent."""
    c = da.challenge(_hyp(ZONE_SIG + MO_SIG), world=_world())
    assert "independent" in c["combined"]["independence_caveat"]
    assert "OVERSTATES" in c["combined"]["independence_caveat"]


# ── against the real dataset ──────────────────────────────────────────────────
def test_real_dossier_challenge_runs_end_to_end():
    da.reset_index()
    from app.agents.research_agent import run_research

    dossier = run_research("Raju")
    if not dossier.get("inferred_hypotheses"):
        pytest.skip("no hypotheses generated for this anchor in the current dataset")
    r = da.challenge_dossier(dossier, limit=3)
    assert r["tally"]
    assert len(r["challenges"]) <= 3
    assert sum(r["tally"].values()) == len(r["challenges"])
    for c in r["challenges"]:
        assert c["verdict"] in {"SURVIVES", "WEAKENED", "COLLAPSES", "UNASSESSABLE"}


def test_real_population_collision_rates_are_ordered_sensibly():
    """A shared hard key must be rarer than a shared district, in the real data."""
    da.reset_index()
    idx = da._index_cached()
    assert idx.collision["hard_key"] < idx.collision["co_accusal"] < idx.collision["zone"]


def test_manifest_declares_this_agent():
    """AGENTS.md is executable — a new agent that skips it is a build failure."""
    from app.agents import manifest

    a = manifest.reload().agents.get("devils_advocate")
    assert a, "devils_advocate is not declared in AGENTS.md"
    assert a.module.startswith("app/agents/devils_advocate.py")
    assert "no_llm" in a.guardrails
