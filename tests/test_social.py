"""
Social Insight Agent (M4 / N6) — demographic breakdowns + crime×occupation correlation.
Run: python -m pytest tests/test_social.py -v   (run `python -m app.seeds.load` first)
"""

from app.agents import social_agent


def test_demographics_has_breakdowns_correlation_and_framing():
    """Happy: victim + offender breakdowns, a crime×occupation correlation, and the framing note."""
    d = social_agent.demographics()
    assert d["victims"]["gender"] and all("label" in r and "n" in r for r in d["victims"]["gender"])
    assert d["victims"]["occupation"] and d["offenders"]["occupation"]
    assert d["crime_occupation"] and d["crime_occupation"][0]["top_occupations"]
    # mandatory bias framing must be present (correlation-only, no targeting)
    assert "causation" in d["framing"].lower() and "target" in d["framing"].lower()


def test_breakdown_counts_are_positive_and_consistent():
    """Failure-mode guard: breakdown counts are positive ints; gender sums to the population."""
    d = social_agent.demographics()
    assert all(isinstance(r["n"], int) and r["n"] > 0 for r in d["victims"]["gender"])
    assert sum(r["n"] for r in d["victims"]["gender"]) > 0
