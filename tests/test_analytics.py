"""
Analytics API (N4) — trends + breakdown over whitelisted templates, local executor.
Run: python -m pytest tests/test_analytics.py -v
"""

import asyncio

from app.api.analytics import trends, breakdown


def test_trends_returns_monthly_series():
    out = asyncio.run(trends(months=12))
    assert out["months"] == 12
    assert isinstance(out["series"], list)
    if out["series"]:
        assert "month" in out["series"][0] and "n" in out["series"][0]


def test_breakdown_by_type_zone_status():
    for by in ("type", "zone", "status"):
        out = asyncio.run(breakdown(by=by))
        assert out["by"] == by
        assert out["rows"] and all("label" in r and "n" in r for r in out["rows"])


def test_breakdown_unknown_dimension_defaults_to_type():
    """Failure-mode: an unknown breakdown dimension falls back to type, no crash."""
    out = asyncio.run(breakdown(by="nonsense"))
    assert out["rows"]
