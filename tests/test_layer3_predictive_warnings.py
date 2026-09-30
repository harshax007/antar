"""
Tests for Layer 3 — Warning & Predictive Crime Intelligence:
  1. Silence anomaly detection (symmetric check for under-reporting/displacement)
  2. Hypothesis-conditioned scenario bands (conditioned conformal intervals)
  3. Warning ledger provenance persistence (evidence_row_ids tracking)
"""

import pytest
from app.services.anomaly import scan as anomaly_scan
from app.api.pattern_predict import predict_scenario
from app.agents.forecast_agent import scan as forecast_scan
from app.services.product_store import get_product


def test_anomaly_scan_direction_and_provenance():
    anomalies = anomaly_scan()
    assert isinstance(anomalies, list)
    for a in anomalies:
        assert a.get("direction") in ("spike", "silence")
        assert "evidence_row_ids" in a
        assert isinstance(a["evidence_row_ids"], list)


@pytest.mark.anyio
async def test_hypothesis_conditioned_scenario_band():
    # Condition on a zone that really has a measured alert (the planted Rajajinagar spike
    # moves with the wall clock, so pick whatever the scan finds).
    alerts = [a for a in anomaly_scan() if a.get("conformal_band")]
    assert alerts, "anomaly scan produced no alert with a band"
    zone, ct = alerts[0]["zone"], alerts[0]["crime_type"]
    res = await predict_scenario(zone, crime_type=ct, hypothesis_id="HYP-TEST-123", uplift_factor=1.4)

    assert res["zone"] == zone
    assert res["hypothesis_id"] == "HYP-TEST-123"

    baseline = res["baseline"]
    scenario = res["scenario"]

    assert scenario["label"] == "scenario (inferred)"
    assert scenario["badge"] == "INFERRED"
    assert scenario["never_rendered_alone"] is True
    assert scenario["hi"] >= baseline["hi"]
    assert "IF corridor active" in res["narrative"]


@pytest.mark.anyio
async def test_no_alert_means_no_band_not_an_invented_one():
    """A7: with no measured alert the endpoint used to present a hardcoded 3.0–7.0 @ 90%
    as a conformal interval."""
    res = await predict_scenario("No Such Zone", crime_type="THEFT")
    assert res["baseline"] is None and res["scenario"] is None
    assert res["reason"] == "no_alert"
    assert "3.0" not in str(res) and "7.0" not in str(res)


def test_warning_ledger_provenance_persistence():
    scan_res = forecast_scan("pytest")
    alerts = scan_res.get("alerts", [])
    assert len(alerts) > 0
    
    for alert in alerts:
        alert_id = alert["alert_id"]
        product_key = f"warning_ledger:alert:{alert_id}"
        stored = get_product(product_key)
        assert stored is not None
        assert stored["alert_id"] == alert_id
        assert "evidence_row_ids" in stored
        assert stored["direction"] in ("spike", "silence")
