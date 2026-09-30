"""
Profile Agent (F5) + repeat-offender registry (N7) — deterministic risk over the seed world.
Run: python -m pytest tests/test_profile.py -v   (run `python -m app.seeds.load` first)
"""

import asyncio

import pytest
from fastapi import HTTPException

from app.agents import profile_agent
from app.api.profile import profile, registry


def test_profile_risk_and_factors_for_raju():
    """S0001 (Raju K.): risk in [0,100], 4 normalized factor bars, grounded MO + leads."""
    p = profile_agent.compute_profile("S0001")
    assert p and 0 <= p["risk_score"] <= 100
    assert set(p["factors"]) == {"recency", "frequency", "severity", "centrality"}
    assert all(0.0 <= v <= 1.0 for v in p["factors"].values())
    assert p["mo_summary"]
    assert p["leads"]   # S0001 has a phone_hash + cross-case link → at least one lead
    
    # SHAP validation
    assert "risk_attributions" in p
    assert set(p["risk_attributions"]) == {"recency", "frequency", "severity", "centrality"}
    # The sum of attributions should equal the risk score (allowing small float/round diffs <= 0.1)
    attrib_sum = sum(p["risk_attributions"].values())
    assert abs(attrib_sum - p["risk_score"]) <= 0.2


def test_profile_unknown_suspect_404():
    """Failure-mode: an unknown suspect id raises 404, never a fabricated profile."""
    with pytest.raises(HTTPException) as ei:
        asyncio.run(profile("S9999"))
    assert ei.value.status_code == 404


def test_registry_sorted_by_risk_desc():
    out = asyncio.run(registry(min_priors=5, limit=20))
    assert out["offenders"]
    risks = [o["risk_score"] or 0 for o in out["offenders"]]
    assert risks == sorted(risks, reverse=True)
    assert all("prior_count" in o and "zone" in o for o in out["offenders"])
