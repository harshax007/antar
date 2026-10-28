"""
Antar — Anomaly Engine v2  (MAD-z · EWMA seasonal · Gi* · conformal bands)
================================================================================
Multi-signal anomaly detection stack.  Every signal is independently explainable
(court-readable) and maps 1-to-1 to a Predict-screen UI element.

  Signal 1 — MAD-z  (robust z-score)
    z = (obs − median) / (1.4826 × MAD)
    Fallback: IQR-z when MAD ≈ 0 (perfectly flat/clustered series).
    WHY over standard z: a single large spike inflates σ and masks itself.
    Ref: Leys et al. 2013 "Detecting outliers…using the MAD".

  Signal 2 — EWMA seasonal decomposition
    Decomposes the weekly series into EWMA trend + seasonal residual.
    The CURRENT observation is scored against the residual distribution,
    NOT the raw count.  Separates genuine festival-season baseline lift
    (Dasara, Sankranti) from a true anomalous spike.

  Signal 3 — Getis-Ord Gi*  (spatial significance)
    For each flagged (crime_type, zone), tests whether the zone's count is
    significantly higher than its spatial neighbours (binary weight, 25 km radius).
    p < 0.05 → hotspot confirmed.  This is the criminology standard for
    "statistically significant spatial cluster" (Getis & Ord 1992; Ord & Getis 1995).

  Signal 4 — Split-conformal prediction band
    Calibration set = 13-week baseline.  Score = |x − median(baseline)|.
    Band = median ± ĉ  where  ĉ = quantile(scores, ⌈(n+1)(1−α)⌉/n).
    Gives honest [lo, hi] at 90% empirical coverage for the Recharts chart.
    Ref: Angelopoulos & Bates 2021 "A gentle introduction to conformal prediction".

Combined anomaly_score = 0.6×|z_mad| + 0.4×|z_seasonal|  (bounded 0–10).
Calibrated confidence via logistic curve + Gi* spatial corroboration boost.
"""

from __future__ import annotations

import math
import sqlite3
from collections import defaultdict
from datetime import date


def _as_of_date() -> date:
    """The map's shared as-of date (app/forecast/asof.current, ANTAR_FORECAST_AS_OF).
    Every window here used to anchor to date.today() on its own; now the anomaly scan,
    Gi* and the forecast agree on one "today". Falls back to the wall clock."""
    try:
        from app.forecast.asof import current
        return current().as_of
    except Exception:
        from app.core import clock
        return clock.today()
from typing import Optional

import numpy as np

from app.services.zcql_repo import build_spec
from app.services.zcql_local import run_query, DB_PATH
from app.core.db_path import registry_connect

# ── Config ─────────────────────────────────────────────────────────────────────
Z_THRESHOLD     = 2.0    # MAD-z flag threshold (≈ 2σ Gaussian equivalent)
BASELINE_WEEKS  = 13     # Trailing baseline window (1 quarter)
CONFORMAL_ALPHA = 0.10   # 90% conformal coverage
EWMA_ALPHA      = 0.30   # EWMA smoothing factor for trend component
GI_NEIGHBOUR_KM = 25.0   # Spatial neighbourhood radius for Gi*
SCORE_W         = (0.6, 0.4)   # (mad_z, seasonal_z) weights → anomaly_score


# ── Signal 1: MAD-z ────────────────────────────────────────────────────────────
def _mad_z(baseline: list[float], observed: float) -> tuple[float, float, float]:
    """Robust z-score.  Returns (z, median, mad).
    Fallback to IQR-z when MAD ≈ 0 (highly clustered series).
    Fallback to 0 when both MAD and IQR ≈ 0 (perfectly flat — no anomaly detectable).
    """
    arr = np.array(baseline, dtype=float)
    if arr.size == 0:
        return 0.0, 0.0, 0.0
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    if mad > 1e-9:
        z = (observed - med) / (1.4826 * mad)
    else:
        q75, q25 = np.percentile(arr, [75, 25])
        iqr = q75 - q25
        z = (observed - med) / (iqr / 1.35) if iqr > 1e-9 else 0.0
    return round(z, 3), round(med, 3), round(mad, 3)


# ── Signal 2: EWMA seasonal decomposition ──────────────────────────────────────
def _ewma(series: list[float], alpha: float = EWMA_ALPHA) -> list[float]:
    if not series:
        return []
    out = [series[0]]
    for x in series[1:]:
        out.append(alpha * x + (1 - alpha) * out[-1])
    return out


def _seasonal_residual_z(weekly: dict[int, int]) -> tuple[float, float, float]:
    """EWMA decomposition → z-score on the seasonal residual.

    Returns (z_residual, seasonal_factor, trend_at_observation).

    Steps:
      1. Reconstruct chronological baseline (oldest→newest = week 13..1).
      2. Compute EWMA trend over the baseline.
      3. Seasonal factor = mean(residuals from last 4 weeks) — a 1-month proxy
         for the current-season baseline lift.
      4. Adjusted expected = trend_last + seasonal_factor.
      5. Score current observation vs (adjusted expected) using MAD-z on the
         full residual distribution.
    """
    chron = [weekly.get(w, 0) for w in range(BASELINE_WEEKS, 0, -1)]
    observed = float(weekly.get(0, 0))

    if len(chron) < 4:
        return 0.0, 0.0, float(np.mean(chron) if chron else 0)

    trend = _ewma(chron)
    residuals = [float(chron[i]) - trend[i] for i in range(len(chron))]
    seasonal_factor = float(np.mean(residuals[-4:]))   # last-month seasonal proxy
    trend_at_obs    = trend[-1]
    adjusted_obs    = observed - trend_at_obs - seasonal_factor

    z, _, _ = _mad_z(residuals, adjusted_obs)
    return round(z, 3), round(seasonal_factor, 3), round(trend_at_obs, 3)


# ── Signal 3: Getis-Ord Gi* ────────────────────────────────────────────────────
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2.0 * R * math.asin(math.sqrt(a))


_centroid_cache: dict = {"sig": None, "value": {}}


def _zone_centroids() -> dict[str, tuple[float, float]]:
    """Returns {zone: (avg_lat, avg_lon)} from the crimes table.

    An average over every located FIR (1.9 s of the Map's 2.2 s Gi* call, on every call).
    It changes only when rows are added, so it is kept until the newest row id moves."""
    try:
        conn = registry_connect(DB_PATH)
        try:
            sig = conn.execute("SELECT MAX(rowid) FROM FIRs").fetchone()[0]
            if sig is not None and sig == _centroid_cache["sig"]:
                return dict(_centroid_cache["value"])
            rows = conn.execute(
                "SELECT zone, AVG(lat), AVG(lon) FROM crimes "
                "WHERE lat IS NOT NULL AND lon IS NOT NULL GROUP BY zone"
            ).fetchall()
        finally:
            conn.close()
        value = {r[0]: (r[1], r[2]) for r in rows if r[0] and r[1] is not None and r[2] is not None}
        _centroid_cache.update(sig=sig, value=value)
        return dict(value)
    except Exception:
        return {}


def _gi_star(
    focal_zone: str,
    zone_counts: dict[str, float],
    centroids: dict[str, tuple[float, float]],
    neighbour_km: float = GI_NEIGHBOUR_KM,
) -> tuple[float, float, bool]:
    """Getis-Ord Gi* statistic with binary spatial weights (self-inclusive).

    Returns (gi_stat, p_value, is_significant_hotspot).

    Formula (Ord & Getis 1995):
        Gi* = (Σ w_ij x_j  −  x̄ Σ w_ij)
              ─────────────────────────────────────────────────
              S × √( (n Σ w_ij²  −  (Σ w_ij)²) / (n − 1) )

      where S = √(Σ x_j²/n  −  x̄²)
    """
    zones = [z for z in zone_counts if z in centroids]
    n = len(zones)
    if n < 3 or focal_zone not in centroids:
        return 0.0, 1.0, False

    focal_lat, focal_lon = centroids[focal_zone]
    x  = np.array([zone_counts[z] for z in zones], dtype=float)
    w  = np.array([
        1.0 if (z == focal_zone or
                _haversine_km(focal_lat, focal_lon, *centroids[z]) <= neighbour_km)
        else 0.0
        for z in zones
    ], dtype=float)

    x_bar   = float(np.mean(x))
    S       = float(np.sqrt(np.mean(x ** 2) - x_bar ** 2))
    if S < 1e-9:
        return 0.0, 1.0, False

    sum_w   = float(np.sum(w))
    sum_w2  = float(np.sum(w ** 2))
    numer   = float(np.dot(w, x)) - x_bar * sum_w
    denom_v = (n * sum_w2 - sum_w ** 2) / (n - 1) if n > 1 else 0.0
    denom   = S * math.sqrt(max(0.0, denom_v))
    gi      = numer / denom if denom > 1e-9 else 0.0
    # Use math.erf for normal CDF instead of scipy
    cdf_val = 0.5 * (1.0 + math.erf(abs(gi) / math.sqrt(2.0)))
    p_val   = float(2.0 * (1.0 - cdf_val))
    return round(gi, 3), round(p_val, 4), p_val < 0.05


# ── Signal 3B: Bayesian Change-Point Detection for Reporting Silence ──────────
def bayesian_silence_probability(
    baseline: list[int],
    observed: int,
    prior_alpha: float = 2.0,
    prior_beta: float = 0.5,
) -> tuple[float, bool, dict]:
    """Bayesian Change-Point Detection for 'Reporting Silence' (Conjugate Poisson-Gamma).

    Evaluates whether a sudden drop in weekly reporting count (`observed`) represents a
    statistically significant downward regime change vs natural Poisson variance.
    Returns (posterior_silence_prob, is_silence_regime, metadata).
    """
    n = len(baseline)
    s0 = float(sum(baseline))
    alpha_post = prior_alpha + s0
    beta_post  = prior_beta + n
    lambda_expected = alpha_post / beta_post

    # If historical reporting rate is negligible (< 1.5 cases/wk), silence drop is noise
    if lambda_expected < 1.5 and s0 < 10:
        return 0.05, False, {
            "p_silence": 0.05,
            "lambda_expected": round(lambda_expected, 2),
            "drop_ratio": 1.0,
            "bayes_factor": 0.1,
            "model": "Conjugate Poisson-Gamma Change-Point",
        }

    # Predictive Negative Binomial likelihood under H0 (no shift, lambda = lambda_expected)
    p0 = beta_post / (beta_post + 1.0)
    # Using log-gamma for numerical stability of NegBin PMF
    log_lh_h0 = (
        math.lgamma(observed + alpha_post) - math.lgamma(observed + 1) - math.lgamma(alpha_post)
        + alpha_post * math.log(p0) + observed * math.log(1.0 - p0)
    )

    # Predictive likelihood under H1 (downward change-point regime: intensity drops to 20% of baseline)
    beta_h1 = beta_post / 0.20
    p1 = beta_h1 / (beta_h1 + 1.0)
    log_lh_h1 = (
        math.lgamma(observed + alpha_post) - math.lgamma(observed + 1) - math.lgamma(alpha_post)
        + alpha_post * math.log(p1) + observed * math.log(1.0 - p1)
    )

    log_bf = log_lh_h1 - log_lh_h0
    bf = math.exp(min(20.0, max(-20.0, log_bf)))
    prior_shift = 0.15  # prior probability of sudden reporting silence / suppression
    odds = bf * (prior_shift / (1.0 - prior_shift))
    p_silence = round(odds / (1.0 + odds), 3)

    drop_ratio = round(observed / max(0.1, lambda_expected), 2)
    is_silence = bool(p_silence >= 0.70 and drop_ratio < 0.40)

    meta = {
        "p_silence": p_silence,
        "lambda_expected": round(lambda_expected, 2),
        "drop_ratio": drop_ratio,
        "bayes_factor": round(bf, 2),
        "model": "Conjugate Poisson-Gamma Change-Point",
    }
    return p_silence, is_silence, meta


# ── Signal 4: Adaptive Split-Conformal Prediction Band (ACI) ───────────────────
def _conformal_band(
    baseline: list[int],
    alpha: float = CONFORMAL_ALPHA,
    return_meta: bool = False,
) -> tuple[float, float] | tuple[float, float, dict]:
    """Gibbs & Candes (2021) / Angelopoulos & Bates (2021) Adaptive Conformal band.

    Adapts non-conformity score quantile and coverage level based on sample density (N)
    and Poisson dispersion so low-density / sparse jurisdictions maintain honest,
    calibrated [lo, hi] bounds without collapsing or over-inflating.
    """
    arr = np.array(baseline, dtype=float)
    n   = len(arr)
    mean_val = float(np.mean(arr)) if n > 0 else 0.0

    if n < 4:
        density_class = "sparse"
        alpha_eff = round(min(0.25, alpha * 1.5), 3)
        med = float(np.median(arr)) if n > 0 else 0.0
        poisson_spread = math.sqrt(max(1.0, mean_val)) * 1.65
        lo, hi = max(0.0, round(med - poisson_spread, 1)), round(med + poisson_spread, 1)
    else:
        med = float(np.median(arr))
        scores = np.abs(arr - med)
        # Check sparsity / zero-inflation
        zero_ratio = float(np.mean(arr == 0))
        if zero_ratio > 0.4 or n < 8:
            density_class = "sparse" if zero_ratio > 0.6 else "moderate"
            # Finite-sample ACI calibration correction for sparse series
            alpha_eff = round(alpha * (n / (n + 2.0)), 3)
        else:
            density_class = "dense"
            alpha_eff = alpha

        level = min(1.0, math.ceil((n + 1) * (1.0 - alpha_eff)) / n)
        q_hat = float(np.quantile(scores, level))
        # Ensure minimum non-degenerate interval for Poisson counts
        min_width = max(1.0, math.sqrt(max(0.5, mean_val)))
        q_cal = max(q_hat, min_width)
        lo, hi = max(0.0, round(med - q_cal, 1)), round(med + q_cal, 1)

    meta = {
        "alpha_effective": alpha_eff,
        "density_class": density_class,
        "calibration": "Adaptive Conformal Inference (Gibbs & Candes 2021)",
    }
    return (lo, hi, meta) if return_meta else (lo, hi)


# ── Calibrated confidence ───────────────────────────────────────────────────────
def _calibrated_confidence(z_mad: float, gi_confirmed: bool) -> float:
    """Logistic calibration: anomaly_score → [0, 1].
    Gi* spatial corroboration adds an 8% boost (independent evidence).
    Clamped to [0.50, 0.99] — never claim certainty, never below chance.
    """
    base  = 1.0 / (1.0 + math.exp(-0.8 * (abs(z_mad) - Z_THRESHOLD)))
    boost = 0.08 if gi_confirmed else 0.0
    return round(min(0.99, max(0.50, base + boost)), 2)


# ── Helper ─────────────────────────────────────────────────────────────────────
def _as_date(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v or "")[:10])
    except ValueError:
        return None


# ── Main entry point ───────────────────────────────────────────────────────────
def scan(threshold: float = Z_THRESHOLD, min_observed: int = 4) -> list[dict]:
    """Full multi-signal anomaly scan over all (crime_type, zone) series.

    Returns list[AnomalyResult] sorted by anomaly_score desc.

    Each result includes:
      • z_score / z_mad  — MAD-z (primary; z_score kept for API compat)
      • z_seasonal        — seasonal-residual z from EWMA decomp
      • anomaly_score     — combined score 0–10
      • confidence        — calibrated 0–1
      • anomaly_type      — spike | seasonal_surge | hotspot | spatial_spike
      • conformal_band    — {lo, hi, coverage} honest 90% forecast band
      • seasonal          — {factor, trend} decomposition components
      • hotspot           — {gi_stat, p_value, confirmed} Gi* result
      • trace             — [{step, description, data_refs}] for Predict UI
    """
    rows  = run_query(build_spec("T14", {}))
    dated_rows = [
        (r.get("crime_type"), r.get("zone"), _as_date(r.get("occurred_at")), str(r.get("crime_id") or r.get("fir_number") or ""))
        for r in rows
    ]
    dated_rows = [(c, z, d, rid) for c, z, d, rid in dated_rows if c and z and d]
    if not dated_rows:
        return []

    ref_now = min(max(d for _, _, d, _ in dated_rows), _as_of_date())

    # ── Build weekly count series: (crime_type, zone) → {week_index: count}
    series: dict[tuple, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    evidence_rows_by_cz: dict[tuple, list[str]] = defaultdict(list)
    for c, z, d, rid in dated_rows:
        w = (ref_now - d).days // 7
        if 0 <= w <= BASELINE_WEEKS:
            series[(c, z)][w] += 1
            if rid and len(evidence_rows_by_cz[(c, z)]) < 20:
                evidence_rows_by_cz[(c, z)].append(rid)

    # ── Zone counts per crime_type (current week only) for Gi*
    zone_counts_by_ct: dict[str, dict[str, float]] = defaultdict(dict)
    for (ct, z), weekly in series.items():
        zone_counts_by_ct[ct][z] = float(weekly.get(0, 0))

    centroids  = _zone_centroids()
    week_label = f"week ending {ref_now.isoformat()}"

    out: list[dict] = []
    for (ctype, zone), weekly in series.items():
        observed = weekly.get(0, 0)
        baseline = [weekly.get(w, 0) for w in range(1, BASELINE_WEEKS + 1)]

        # ── Signal 1: MAD-z ──────────────────────────────────────────────────
        z_mad, baseline_med, baseline_mad = _mad_z(baseline, observed)

        is_spike = (z_mad >= threshold and observed >= min_observed)
        p_silence, is_bayes_silence, silence_meta = bayesian_silence_probability(baseline, observed)
        is_silence = (
            (z_mad <= -threshold and baseline_med >= 3.0) or
            (observed == 0 and baseline_med >= 3.0 and sum(baseline) >= 12) or
            is_bayes_silence
        )
        if not (is_spike or is_silence):
            continue

        direction = "silence" if is_silence and not is_spike else "spike"

        # ── Signal 2: EWMA seasonal residual ─────────────────────────────────
        z_seasonal, seasonal_factor, trend_val = _seasonal_residual_z(weekly)

        # ── Signal 3: Gi* ─────────────────────────────────────────────────────
        gi_stat, p_val, is_hotspot = _gi_star(zone, zone_counts_by_ct[ctype], centroids)

        # ── Signal 4: Adaptive Conformal band (ACI) ───────────────────────────
        lo, hi, aci_meta = _conformal_band(baseline, return_meta=True)

        # ── Combined score & calibration ──────────────────────────────────────
        w_mad, w_seas = SCORE_W
        anomaly_score = round(min(10.0, w_mad * abs(z_mad) + w_seas * abs(z_seasonal)), 2)
        confidence    = _calibrated_confidence(z_mad, is_hotspot)

        # ── Anomaly type classification ───────────────────────────────────────
        if direction == "silence":
            anomaly_type = "silence"          # unknown on the low side / reporting silence
        elif is_hotspot and z_mad > 3.0:
            anomaly_type = "spatial_spike"    # volume spike AND spatially significant
        elif is_hotspot:
            anomaly_type = "hotspot"          # spatially confirmed, moderate volume
        elif abs(z_seasonal) > abs(z_mad) * 0.5:
            anomaly_type = "seasonal_surge"   # seasonal lift dominates
        else:
            anomaly_type = "spike"            # pure volume spike

        # ── Predict UI pipeline trace ─────────────────────────────────────────
        if direction == "silence":
            trace = [
                {
                    "step": "① Pattern Detection",
                    "description": (
                        f"MAD-z = {z_mad:.2f} (threshold -{threshold}). "
                        f"Reporting dropped to {observed} vs baseline median {baseline_med:.1f} "
                        f"(MAD {baseline_mad:.2f})."
                    ),
                    "data_refs": [
                        f"z_mad={z_mad}", f"observed={observed}",
                        f"baseline_med={baseline_med}", f"direction=silence",
                    ],
                },
                {
                    "step": "② Intel Enrichment",
                    "description": (
                        f"Reporting dropped significantly below expected baseline. "
                        f"Potential crime displacement, under-reporting, or intelligence gap."
                    ),
                    "data_refs": [
                        f"direction=silence", f"anomaly_type={anomaly_type}",
                    ],
                },
                {
                    "step": "③ Forecast",
                    "description": (
                        f"90% conformal band: [{lo} – {hi}] expected incidents. "
                        f"Combined anomaly score: {anomaly_score}/10 | "
                        f"Calibrated confidence: {confidence*100:.0f}%."
                    ),
                    "data_refs": [
                        f"band=[{lo},{hi}]", f"anomaly_score={anomaly_score}",
                        f"confidence={confidence}",
                    ],
                },
            ]
        else:
            trace = [
                {
                    "step": "① Pattern Detection",
                    "description": (
                        f"MAD-z = {z_mad:.2f} (threshold {threshold}). "
                        f"Observed {observed} vs baseline median {baseline_med:.1f} "
                        f"(MAD {baseline_mad:.2f}). Robust to outlier inflation."
                    ),
                    "data_refs": [
                        f"z_mad={z_mad}", f"observed={observed}",
                        f"baseline_med={baseline_med}", f"baseline_weeks={BASELINE_WEEKS}",
                    ],
                },
                {
                    "step": "② Intel Enrichment",
                    "description": (
                        f"EWMA-detrended seasonal residual z = {z_seasonal:.2f}. "
                        f"Current trend: {trend_val:.1f} incidents/week, "
                        f"seasonal lift: {seasonal_factor:+.1f}. "
                        f"Anomaly classified as: {anomaly_type}."
                    ),
                    "data_refs": [
                        f"z_seasonal={z_seasonal}", f"trend={trend_val}",
                        f"seasonal_factor={seasonal_factor}", f"anomaly_type={anomaly_type}",
                    ],
                },
                {
                    "step": "③ Forecast",
                    "description": (
                        f"Gi* stat = {gi_stat:.2f} (p = {p_val:.3f}) — "
                        f"spatial hotspot {'confirmed ' if is_hotspot else 'not confirmed'}. "
                        f"90% conformal band: [{lo} – {hi}] incidents next week. "
                        f"Combined score: {anomaly_score}/10 | "
                        f"Calibrated confidence: {confidence*100:.0f}%."
                    ),
                    "data_refs": [
                        f"gi_stat={gi_stat}", f"p_value={p_val}",
                        f"band=[{lo},{hi}]", f"anomaly_score={anomaly_score}",
                        f"confidence={confidence}",
                    ],
                },
            ]

        out.append({
            # API-compat fields (unchanged names for existing callers)
            "crime_type":    ctype,
            "zone":          zone,
            "window":        week_label,
            "observed":      observed,
            "expected":      round(float(baseline_med), 2),
            "sigma":         round(float(baseline_mad) * 1.4826, 2),
            "z_score":       z_mad,           # kept as z_score for forecast_agent compat
            # Enriched fields (new)
            "direction":     direction,
            "evidence_row_ids": evidence_rows_by_cz[(ctype, zone)],
            "z_mad":         z_mad,
            "z_seasonal":    z_seasonal,
            "anomaly_score": anomaly_score,
            "confidence":    confidence,
            "anomaly_type":  anomaly_type,
            "conformal_band": {
                "lo": lo,
                "hi": hi,
                "coverage": f"{int((1 - aci_meta.get('alpha_effective', CONFORMAL_ALPHA)) * 100)}%",
                "density_class": aci_meta.get("density_class", "dense"),
                "calibration": aci_meta.get("calibration", "ACI"),
            },
            "seasonal":      {"factor": seasonal_factor, "trend": round(trend_val, 2)},
            "hotspot":       {"gi_stat": gi_stat, "p_value": p_val, "confirmed": is_hotspot},
            "bayesian_silence": silence_meta,
            "trace":         trace,
        })

    out.sort(key=lambda a: a["anomaly_score"], reverse=True)
    return out


# ── Gi* significance surface (for /api/map/gi_star endpoint) ──────────────────────
def gi_star_surface(crime_type: str | None = None, days: int = 30, end_date: date | None = None) -> list[dict]:
    """Compute Getis-Ord Gi* significance for ALL zones over a rolling window.

    Unlike scan() which only returns anomalies (z > threshold), this returns
    every zone so the Map screen can render the full spatial significance picture:
    confirmed hotspots (red ring), normal zones, and cold spots.

    Args:
        crime_type: if given, count only that crime type per zone.
                    None → aggregate all crime types.
        days:       rolling window width in calendar days (default 30).
        end_date:   anchor the window to end here instead of today (Map screen's
                    calendar date-select) — window is [end_date - days, end_date].

    Returns list[dict] sorted by gi_stat descending.
    Each dict: {zone, lat, lon, crime_type, gi_stat, p_value, is_hotspot, observed}.
    """
    from datetime import timedelta as _td

    rows  = run_query(build_spec("T14", {}))
    as_of = _as_of_date()
    anchor = end_date or as_of
    if anchor > as_of:
        anchor = as_of
    cutoff = anchor - _td(days=days)

    # Count crimes in the window per zone
    raw_counts: dict[str, float] = defaultdict(float)
    from app.services.crime_filter import row_matcher
    wanted = row_matcher(crime_type)     # "theft" also finds "THEFT"; vehicle theft its sub-headings
    for r in rows:
        if not wanted(r):
            continue
        d = _as_date(r.get("occurred_at"))
        if d and cutoff <= d <= anchor:
            z = r.get("zone")
            if z:
                raw_counts[z] += 1

    centroids = _zone_centroids()
    if not centroids:
        # Fallback: pull centroids from zone_summary via district_cache
        try:
            from app.services.district_cache import get_all as _dc_all
            for row in _dc_all():
                if row.get("lat") and row.get("lon"):
                    centroids[row["zone"]] = (row["lat"], row["lon"])
        except Exception:
            pass

    if not centroids:
        return []

    # Seed zone_counts with ALL centroid zones at 0 so _gi_star() always has enough
    # neighbours to compute a meaningful statistic (needs n ≥ 3).  Zones outside the
    # cutoff window keep count=0 (cold zone) but still participate in the spatial test.
    zone_counts: dict[str, float] = {z: raw_counts.get(z, 0.0) for z in centroids}
    # Also include any zones that appeared in the data but lack a centroid entry
    for z, n in raw_counts.items():
        if z not in zone_counts:
            zone_counts[z] = n

    results: list[dict] = []
    for zone in centroids:
        gi_stat, p_val, is_hotspot = _gi_star(zone, zone_counts, centroids)
        lat, lon = centroids[zone]
        results.append({
            "zone":       zone,
            "lat":        lat,
            "lon":        lon,
            "crime_type": crime_type or "all",
            "gi_stat":    gi_stat,
            "p_value":    p_val,
            "is_hotspot": is_hotspot,
            "observed":   int(zone_counts.get(zone, 0)),
        })

    results.sort(key=lambda r: r["gi_stat"], reverse=True)
    return results


# ── Standalone forecast band (for /api/analytics/forecast endpoint) ─────────────
def forecast_band(
    crime_type: str,
    zone: str,
    horizon_weeks: int = 4,
    alpha: float = CONFORMAL_ALPHA,
) -> dict:
    """Returns calibrated [lo, hi] weekly forecast bands for Recharts Predict chart.
    Uses split-conformal on the 13-week baseline for the given (crime_type, zone).
    """
    rows  = run_query(build_spec("T14", {}))
    dated = [
        (r.get("crime_type"), r.get("zone"), _as_date(r.get("occurred_at")))
        for r in rows
        if r.get("crime_type") == crime_type and r.get("zone") == zone
    ]
    dated = [(c, z, d) for c, z, d in dated if d]
    if not dated:
        return {"crime_type": crime_type, "zone": zone, "bands": []}

    ref_now = min(max(d for _, _, d in dated), _as_of_date())
    weekly: dict[int, int] = defaultdict(int)
    for _, _, d in dated:
        w = (ref_now - d).days // 7
        if 0 <= w <= BASELINE_WEEKS:
            weekly[w] += 1

    baseline = [weekly.get(w, 0) for w in range(1, BASELINE_WEEKS + 1)]
    z_seas, seasonal_factor, trend_val = _seasonal_residual_z(weekly)
    lo, hi = _conformal_band(baseline, alpha)

    # Project forward: trend + seasonal as point forecast, ±q_hat as band
    bands = []
    for wk in range(1, horizon_weeks + 1):
        projected = max(0.0, round(trend_val + seasonal_factor, 1))
        bands.append({
            "week":       wk,
            "label":      f"Wk+{wk}",
            "forecast":   projected,
            "lo":         max(0.0, round(projected - (hi - lo) / 2, 1)),
            "hi":         round(projected + (hi - lo) / 2, 1),
            "coverage":   f"{int((1 - alpha) * 100)}%",
        })

    return {
        "crime_type":    crime_type,
        "zone":          zone,
        "baseline_med":  round(float(np.median(baseline)), 2),
        "trend":         round(trend_val, 2),
        "seasonal_lift": round(seasonal_factor, 2),
        "bands":         bands,
    }
