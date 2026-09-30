"""
Overview dashboard endpoint (N1) — composed from whitelisted templates, local executor.
Run: python -m pytest tests/test_dashboard.py -v
"""

import asyncio

import app.api.dashboard as dash
from app.api.dashboard import overview


def test_overview_contract_and_totals():
    """Happy: KPIs + panels present; status counts partition the total crime count."""
    out = asyncio.run(overview())
    k = out["kpis"]
    assert k["total_crimes"] > 0
    assert k["total_crimes"] == sum(r["n"] for r in out["by_status"])   # status partitions all crimes
    assert out["crime_by_type"]                                         # non-empty all-time breakdown
    for key in ("hotspots_this_month", "trend_12m", "recent_crimes"):
        assert isinstance(out[key], list)


def test_overview_resilient_to_empty(monkeypatch):
    """Failure-mode: if a template returns nothing, the contract still holds (zeros, no crash)."""
    monkeypatch.setattr(dash, "run_query", lambda spec: [])
    out = asyncio.run(overview())
    assert out["kpis"]["total_crimes"] == 0
    assert out["kpis"]["top_zone_this_month"] is None
    assert out["recent_crimes"] == [] and out["hotspots_this_month"] == []
