"""
Antar — Prediction Agent (A9)
==================================
Agent responsible for short-horizon risk prediction using trend and pattern signals.
"""

from app.services.zcql_local import scan_rows as _scan_rows
from app.services.patterns import predict_risk

async def prediction_agent_run(user_text: str, params: dict) -> dict:
    """
    Called by the agentic spine when intent is 'predict'.
    """
    ct = params.get("crime_types", [])
    crime_type = ct[0] if ct else None
    
    zones = params.get("zones", [])
    zone = zones[0] if zones else None
    
    # Prediction always needs enough data for trends, we don't apply tight time filters initially.
    rows = _scan_rows(crime_type, None)
    
    prediction = predict_risk(zone, crime_type, rows)
    
    # We now have structured traces in predict_risk: prediction["trace"] is a list of dicts.
    trace_steps = " ".join([t.get("description", "") for t in prediction.get("trace", [])])
    
    return {
        "prediction": prediction,
        "summary": f"Risk for {zone or 'all zones'} ({crime_type or 'all crimes'}) is {prediction['risk']}. {trace_steps}"
    }


def compute_scenario_band(
    zone: str,
    crime_type: str | None = None,
    hypothesis_id: str | None = None,
    uplift_factor: float = 1.35,
) -> dict:
    """Compute hypothesis-conditioned scenario band alongside baseline conformal band.
    Strictly labeled 'scenario (inferred)', purple-badged, never rendered alone.
    """
    from app.services.anomaly import scan as anomaly_scan
    from app.services.product_store import put_product

    alerts = anomaly_scan()
    alert = next(
        (a for a in alerts if a["zone"] == zone and (not crime_type or a["crime_type"] == crime_type)),
        None
    )

    band = (alert or {}).get("conformal_band") or {"lo": 3.0, "hi": 7.0, "coverage": "90%"}
    baseline_lo = float(band.get("lo", 3.0))
    baseline_hi = float(band.get("hi", 7.0))
    baseline_point = round((baseline_lo + baseline_hi) / 2.0, 1)

    hyp_id = hypothesis_id or "HYP-CORRIDOR-S0001"
    scenario_lo = round(max(0.0, baseline_lo * uplift_factor), 1)
    scenario_hi = round(baseline_hi * uplift_factor, 1)

    payload = {
        "zone": zone,
        "crime_type": crime_type or (alert or {}).get("crime_type", "THEFT"),
        "hypothesis_id": hyp_id,
        "baseline": {
            "lo": baseline_lo,
            "hi": baseline_hi,
            "point": baseline_point,
            "coverage": band.get("coverage", "90%"),
            "label": "Baseline (90% Conformal)",
        },
        "scenario": {
            "lo": scenario_lo,
            "hi": scenario_hi,
            "point": round((scenario_lo + scenario_hi) / 2.0, 1),
            "coverage": band.get("coverage", "90%"),
            "label": "scenario (inferred)",
            "badge": "INFERRED",
            "never_rendered_alone": True,
        },
        "narrative": f"IF corridor active ({hyp_id}), expect {scenario_lo}-{scenario_hi} incidents vs baseline {baseline_lo}-{baseline_hi}.",
        "evidence_row_ids": (alert or {}).get("evidence_row_ids", []),
    }
    put_product(f"warning_ledger:scenario:{zone}:{hyp_id}", payload, ttl=3600)
    return payload
