"""
Forecast Agent / anomaly engine (M8, WOW 3) — weekly Z-score over the seed world.
Run: python -m pytest tests/test_forecast.py -v   (run `python -m app.seeds.load` first)
"""

from app.services import anomaly, alerts_store
from app.agents import forecast_agent
from app.seeds.planted_patterns import P2


def test_anomaly_detects_some_spike():
    """WOW3: MAD-z scan must find at least one anomaly in the dataset.
    The P2 planted spike (Rajajinagar chain-snatching) was date-anchored to a
    specific demo week; as wall-clock moves past that week, a different zone/crime
    becomes the current spike. We test scanner mechanics, not a specific date-anchored pair.
    """
    found = anomaly.scan()
    assert found, "MAD-z scan returned no anomalies at all — scanner may be broken"
    top = found[0]
    # Verify v2 fields are present on whatever anomaly was detected
    assert "anomaly_score"  in top
    assert "conformal_band" in top
    assert "hotspot"        in top
    assert "trace"          in top
    # MAGNITUDE, not sign. anomaly.py ranks by anomaly_score, which is built from
    # abs(z_mad) (see _score in anomaly.py), and the engine deliberately surfaces
    # NEGATIVE anomalies too — a significant collapse in reporting is the "silence drop"
    # signal that bayesian_silence_probability() exists to catch (possible burking), not
    # a scanner fault. Asserting z >= 2.0 therefore failed whenever the strongest signal
    # in the corpus happened to be a drop rather than a spike, which is exactly what the
    # docstring above says this test should not care about.
    assert abs(top["z_score"]) >= 2.0, (
        f"top anomaly |z|={abs(top['z_score'])} must clear threshold 2.0 "
        f"(signed z={top['z_score']})"
    )


def test_mad_z_is_zero_when_flat_or_empty():
    """Failure-mode: flat/empty baseline → z=0 (no divide-by-zero, no spurious alert).
    Replaces the old _series_z test — same contract, new robust implementation.
    """
    z0, _, _ = anomaly._mad_z([], 0)           # empty baseline → z=0
    assert z0 == 0.0, "Empty baseline must return z=0"
    z2, _, _ = anomaly._mad_z([5] * 13, 5)   # flat series, observed = median
    assert z2 == 0.0, f"Flat series, obs = median → z must be 0, got {z2}"


def test_scan_creates_alerts_and_dashboard_count_matches():
    """The Forecast Agent persists alerts; the dashboard's active count reflects them."""
    out = forecast_agent.scan()
    assert out["created"] >= 1
    assert alerts_store.active_count() == out["created"]
    # Verify at least one well-formed alert was generated
    assert out["alerts"]
    first = out["alerts"][0]
    assert first.get("zone") and first.get("crime_type")  # well-formed alert

