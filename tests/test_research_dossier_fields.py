"""
Antar — research dossier field-name regressions
===============================================
Both bugs here were the same mistake: `run_research` read keys off another agent's
return value that that agent has never produced, and `.get(key, default)` turned the
miss into a plausible-looking default instead of an error.

  prof.get("risk", 0)                 -> compute_profile returns `risk_score`
  prof.get("risk_label", "Moderate")  -> no such key exists, anywhere
  corr.get("district_a" / "district_b" / "linked_offenders")
                                      -> get_all_corridors returns src / dst / weight

So every dossier reported "Risk score ... is 0 (Moderate)" for a suspect the model
scored 52.2, and "Movement corridor identified: None <-> None with 0 linked offenders".
Neither surfaced for a long time because both read as ordinary output.

These tests pin the CONTRACT between the agents, not the wording, so the next rename
fails loudly here instead of silently degrading a dossier.
"""

import pytest

from app.agents.corridor_agent import get_all_corridors
from app.agents.profile_agent import compute_profile
from app.agents.research_agent import run_research


@pytest.fixture(scope="module")
def dossier():
    return run_research("Raju")


def _claims(dossier, needle):
    return [f["claim"] for f in dossier["derived_facts"] if needle in f["claim"]]


# ── the contracts that were broken ────────────────────────────────────────────
def test_compute_profile_exposes_risk_score_and_no_risk_label():
    """The upstream shape research_agent depends on. If this changes, the dossier must
    be updated with it — that is the whole point of asserting it here."""
    prof = compute_profile("S0001")
    assert prof is not None
    assert "risk_score" in prof, "research_agent reads risk_score"
    assert isinstance(prof["risk_score"], (int, float))
    assert "risk" not in prof, "the key the dossier used to read has (still) never existed"
    assert "risk_label" not in prof, "no risk banding exists in this codebase"


def test_corridor_exposes_src_dst_weight_and_no_district_a_b():
    corrs = get_all_corridors()
    if not corrs:
        pytest.skip("no corridors compiled in the current dataset")
    c = corrs[0]
    for key in ("src", "dst", "weight", "fir_count", "involved_entities"):
        assert key in c, f"research_agent reads corridor['{key}']"
    for absent in ("district_a", "district_b", "linked_offenders"):
        assert absent not in c, f"the key the dossier used to read ('{absent}') does not exist"


# ── risk score ────────────────────────────────────────────────────────────────
def test_risk_claim_reports_the_real_score(dossier):
    """S0001 scores ~52. The dossier said 0. Reporting a mid-range suspect as zero-risk
    is the worst direction for this error to run."""
    expected = round(float(compute_profile("S0001")["risk_score"]))
    claims = _claims(dossier, "Risk score for")
    assert claims, "no risk claim in the dossier"
    s0001 = [c for c in claims if "[S0001]" in c]
    assert s0001, "S0001 should be in the frontier for anchor 'Raju'"
    assert f"{expected}/100" in s0001[0], f"expected {expected}/100 in: {s0001[0]}"


def test_risk_claim_invents_no_label(dossier):
    """'Moderate' was a .get() default that printed regardless of the score. There is no
    banding in the codebase, so no label may be asserted."""
    for claim in _claims(dossier, "Risk score for"):
        for invented in ("(Moderate)", "(High)", "(Low)", "(Critical)"):
            assert invented not in claim


def test_zero_risk_is_only_reported_when_it_is_real(dossier):
    """Guards the specific failure: a 0 that came from a missing key, not the model."""
    for claim in _claims(dossier, "Risk score for"):
        sid = claim.split("[")[1].split("]")[0]
        actual = round(float(compute_profile(sid)["risk_score"]))
        assert f"{actual}/100" in claim


# ── corridors ─────────────────────────────────────────────────────────────────
def test_corridor_claims_name_real_districts(dossier):
    claims = _claims(dossier, "Movement corridor")
    if not claims:
        pytest.skip("no corridor facts in this dossier")
    for c in claims:
        assert "None <-> None" not in c
        assert "None" not in c


def test_corridor_claims_report_real_counts(dossier):
    """'0 linked offenders' was the missing-key default. A corridor with zero linked
    offenders is not a corridor."""
    claims = _claims(dossier, "Movement corridor")
    if not claims:
        pytest.skip("no corridor facts in this dossier")
    assert any("0 linked offender" not in c for c in claims)
    for c in claims:
        assert "linked offender(s) across" in c


def test_corridor_evidence_rows_are_ids_not_objects(dossier):
    """evidence_rows is a list of row identifiers everywhere else in the dossier; this
    entry was nesting whole entity dicts into it."""
    facts = [f for f in dossier["derived_facts"] if "Movement corridor" in f["claim"]]
    if not facts:
        pytest.skip("no corridor facts in this dossier")
    for f in facts:
        assert f["evidence_rows"], "a corridor claim with no evidence rows"
        for row in f["evidence_rows"]:
            assert isinstance(row, str), f"evidence row should be an id, got {type(row)}"


def test_corridor_without_endpoints_is_skipped_not_claimed():
    """A corridor missing src/dst must produce no claim at all — the old code emitted
    'None <-> None' rather than staying silent."""
    import app.agents.research_agent as ra

    original = ra.get_all_corridors
    ra.get_all_corridors = lambda: [{"src": None, "dst": None, "weight": 0,
                                     "fir_count": 0, "involved_entities": []}]
    try:
        from app.services.product_store import put_product
        put_product("research:__corridor_probe__", {}, ttl=1)   # avoid a cached dossier
        d = ra.run_research("__corridor_probe__")
        assert not [f for f in d["derived_facts"] if "Movement corridor" in f["claim"]]
    finally:
        ra.get_all_corridors = original


# ── the class of bug ──────────────────────────────────────────────────────────
def test_no_derived_claim_renders_a_none(dossier):
    """A missing key reaching an officer as the literal word 'None' is the signature of
    this whole class of bug."""
    for f in dossier["derived_facts"]:
        assert "None" not in f["claim"], f"unresolved value in: {f['claim']}"


def test_dossier_claims_are_cp1252_safe(dossier):
    """Dossier text reaches CSV/PDF export and Windows consoles."""
    for group in ("known_facts", "derived_facts"):
        for f in dossier.get(group, []):
            f["claim"].encode("cp1252")
