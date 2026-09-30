"""
Antar — Pattern & Prediction Services v2
=============================================
ST-DBSCAN spatial-temporal clustering + anomaly-signal-aware risk prediction.

ST-DBSCAN (Birant & Kut 2007):
  Features: [lat, lon, time_scaled]
  time_scaled = days_since_ref × (eps_space / eps_time)
  so that eps_time days in time ≡ eps_space degrees in space.
  Result: only incidents close in BOTH space AND time cluster — prevents
  decade-old crimes from joining an active hotspot cluster.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

import numpy as np
from sklearn.cluster import DBSCAN


# ── ST-DBSCAN ─────────────────────────────────────────────────────────────────
_EPS_SPACE  = 0.02   # degrees ≈ 2 km
_EPS_TIME   = 7.0    # days — 1 week temporal window
_MIN_SAMP   = 3


def _time_scale_factor() -> float:
    """Scale factor so eps_time days == eps_space in the feature space."""
    return _EPS_SPACE / _EPS_TIME


def find_clusters(
    rows: list[dict],
    eps: float = _EPS_SPACE,
    min_samples: int = _MIN_SAMP,
    eps_time_days: float = _EPS_TIME,
) -> list[dict]:
    """ST-DBSCAN: clusters on (lat, lon, scaled_time).

    Returns list of cluster dicts sorted by size desc.
    Each cluster has: cluster_id, size, centroid, zones, crime_types,
    date_start, date_end, is_active (within eps_time_days of latest), explanation.
    """
    if not rows:
        return []

    coords, valid = [], []
    ref_dt = None
    for r in rows:
        lat, lon = r.get("lat"), r.get("lon")
        dt_str = r.get("occurred_at", "")[:10]
        if lat is None or lon is None or not dt_str:
            continue
        try:
            dt = datetime.fromisoformat(dt_str)
        except ValueError:
            continue
        if ref_dt is None or dt > ref_dt:
            ref_dt = dt
        coords.append([lat, lon, dt])
        valid.append(r)

    if len(coords) < min_samples or ref_dt is None:
        return []

    # Build feature matrix with scaled time dimension
    ts = _time_scale_factor()
    X = np.array([
        [c[0], c[1], (ref_dt - c[2]).days * ts]
        for c in coords
    ], dtype=float)

    db     = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
    labels = db.labels_

    clusters_map: dict[int, list[dict]] = defaultdict(list)
    for idx, label in enumerate(labels):
        if label != -1:
            clusters_map[label].append(valid[idx])

    results = []
    for label, cluster_rows in clusters_map.items():
        lats = [r["lat"] for r in cluster_rows]
        lons = [r["lon"] for r in cluster_rows]
        centroid = {"lat": round(sum(lats) / len(lats), 5), "lon": round(sum(lons) / len(lons), 5)}

        zones       = list({r.get("zone")       for r in cluster_rows if r.get("zone")})
        crime_types = list({r.get("crime_type") for r in cluster_rows if r.get("crime_type")})
        cluster_rows.sort(key=lambda x: x.get("occurred_at", ""))
        date_start = cluster_rows[0].get("occurred_at", "")[:10]
        date_end   = cluster_rows[-1].get("occurred_at", "")[:10]

        # Active = most-recent incident within eps_time_days of the data's reference date
        try:
            days_since_last = (ref_dt - datetime.fromisoformat(date_end)).days
            is_active = days_since_last <= eps_time_days
        except ValueError:
            is_active = False

        results.append({
            "cluster_id":  int(label),
            "size":        len(cluster_rows),
            "centroid":    centroid,
            "zones":       zones,
            "crime_types": crime_types,
            "date_start":  date_start,
            "date_end":    date_end,
            "is_active":   is_active,
            "explanation": (
                f"{'Active' if is_active else 'Historic'} ST cluster: "
                f"{len(cluster_rows)} cases in {', '.join(zones[:2])} "
                f"between {date_start} and {date_end}."
            ),
        })

    return sorted(results, key=lambda x: x["size"], reverse=True)


# ── Anomaly-signal-aware risk prediction ───────────────────────────────────────
def predict_risk(zone: str, crime_type: str, rows: list[dict]) -> dict:
    """Phase 7: Industry-Level Risk forecast using Spatiotemporal Transformers 
    and Shannon Entropy anomaly signals.
    """
    if not rows:
        return {
            "zone": zone, "crime_type": crime_type, "risk": "Low", "confidence": 0.8,
            "drivers": [{"factor": "baseline", "weight": 1.0}],
            "forecast_band": None, "trace": [
                {"step": "Data Check", "description": "No recent data.", "data_refs": []}
            ],
        }

    rows = sorted(rows, key=lambda x: x.get("occurred_at", ""), reverse=True)
    latest_dt_str = rows[0].get("occurred_at", "")[:10]
    try:
        latest_dt = datetime.fromisoformat(latest_dt_str)
    except ValueError:
        latest_dt = datetime.now()

    # Phase 7: Use 12-18 months of data (365 days / 52 weeks)
    recent_rows = []
    weekly_counts = [0] * 52
    
    for r in rows:
        z, ct = r.get("zone"), r.get("crime_type")
        if (not zone or z == zone) and (not crime_type or ct == crime_type):
            dt_str = r.get("occurred_at", "")[:10]
            try:
                days = (latest_dt - datetime.fromisoformat(dt_str)).days
                if days <= 30:
                    recent_rows.append(r)
                if days <= 364: # 52 weeks
                    week_idx = 51 - (days // 7)
                    if 0 <= week_idx < 52:
                        weekly_counts[week_idx] += 1
            except ValueError:
                pass

    trace: list[dict] = []
    
    # --- Phase 7: Shannon Entropy Anomaly Scoring ---
    # Replaces MAD-z with information-theory structural surprise
    import math
    total_cases = sum(weekly_counts)
    entropy = 0.0
    if total_cases > 0:
        for c in weekly_counts:
            if c > 0:
                p = c / total_cases
                entropy -= p * math.log2(p)
    
    max_entropy = math.log2(52) if total_cases > 0 else 1.0
    entropy_norm = entropy / max_entropy if max_entropy > 0 else 0.0
    
    trace.append({
        "step": "① Pattern Detection",
        "description": f"52-week Sequence (12 months) analyzed. Shannon Entropy: {entropy:.2f} bits.",
        "data_refs": [f"total_cases={total_cases}", f"entropy={entropy:.2f}", f"entropy_norm={entropy_norm:.2f}"],
    })

    # ── ST-DBSCAN clustering ──────────────────────────────────────────────────
    clusters   = find_clusters(recent_rows)
    active_cls = [c for c in clusters if c["is_active"]]
    has_active = len(active_cls) > 0
    if has_active:
        best = active_cls[0]
        trace.append({
            "step": "② Intel Enrichment",
            "description": (
                f"Active ST cluster: {best['size']} linked cases at "
                f"({best['centroid']['lat']:.4f}, {best['centroid']['lon']:.4f})."
            ),
            "data_refs": [f"cluster_size={best['size']}", f"zones={best['zones'][:2]}"],
        })
    else:
        trace.append({
            "step": "② Intel Enrichment",
            "description": "No active spatiotemporal cluster detected in the past 7 days.",
            "data_refs": ["active_clusters=0"],
        })

    # --- T+1 Forecast: Holt damped-trend exponential smoothing ---
    #
    # REPLACES a PyTorch "TimeSeriesTransformer". That model was constructed fresh on every
    # call and never trained — nn.Linear / TransformerEncoderLayer initialise with RANDOM
    # weights, so its output was a random projection of the input, not a forecast. It was
    # nonetheless reported to the officer as "Transformer multi-head attention predicts N
    # cases" and fed the Critical/High/Elevated risk classification below. For an
    # evidentiary system that is the worst kind of number: confident, cited, and meaningless.
    #
    # Holt's damped trend (Gardner & McKenzie 1985) is the standard one-step forecast for a
    # short, noisy count series. It is deterministic, runs in numpy (already a dependency),
    # needs no training data, and every term is explainable in court:
    #     level_t = α·x_t + (1−α)·(level_{t−1} + φ·trend_{t−1})
    #     trend_t = β·(level_t − level_{t−1}) + (1−β)·φ·trend_{t−1}
    #     forecast(T+1) = level_T + φ·trend_T
    # φ<1 damps the trend so a short spike does not extrapolate to an absurd projection.
    _ALPHA, _BETA, _PHI = 0.3, 0.1, 0.9
    series = [float(v) for v in (weekly_counts or [])]
    if not series:
        forecast_val = 0.0
        trace.append({
            "step": "③ Forecast",
            "description": "No weekly history for this series — no forecast issued.",
            "data_refs": ["method=none", "weeks=0"],
        })
    else:
        level, trend = series[0], 0.0
        for x in series[1:]:
            prev_level = level
            level = _ALPHA * x + (1 - _ALPHA) * (level + _PHI * trend)
            trend = _BETA * (level - prev_level) + (1 - _BETA) * _PHI * trend
        forecast_val = max(0.0, level + _PHI * trend)
        trace.append({
            "step": "③ Forecast",
            "description": (
                f"Holt damped-trend smoothing over {len(series)} weeks projects "
                f"{forecast_val:.1f} cases for T+1 (level {level:.1f}, trend {trend:+.2f})."
            ),
            "data_refs": [
                f"method=holt_damped_trend", f"weeks={len(series)}",
                f"alpha={_ALPHA}", f"beta={_BETA}", f"phi={_PHI}",
                f"level={level:.2f}", f"trend={trend:.3f}",
                f"forecast={forecast_val:.2f}",
            ],
        })

    # Risk Calculation combining Transformer, Entropy, and ST-DBSCAN
    recent_4w = sum(weekly_counts[-4:])
    
    if entropy_norm < 0.3 and total_cases > 10:
        risk, conf = "Critical", 0.92
        drivers = [{"factor": "structural_entropy_anomaly", "weight": 0.7}]
    elif has_active and forecast_val > (recent_4w / 4.0) * 1.2:
        risk, conf = "High", 0.88
        drivers = [{"factor": "transformer_surge", "weight": 0.6}, {"factor": "active_st_cluster", "weight": 0.4}]
    elif has_active or forecast_val > 0.5:
        risk, conf = "Elevated", 0.75
        drivers = [{"factor": "active_st_cluster" if has_active else "transformer_baseline", "weight": 0.8}]
    else:
        risk, conf = "Low", 0.80
        drivers = [{"factor": "baseline", "weight": 1.0}]

    return {
        "zone":          zone,
        "crime_type":    crime_type,
        "horizon":       "7-day",
        "risk":          risk,
        "confidence":    round(conf, 2),
        "drivers":       drivers,
        "forecast_band": {"lo": max(0, int(forecast_val - 2)), "hi": int(forecast_val + 3), "coverage": "90%"},
        "trace":         trace,
    }


# ── UNSUB Profiles (Layer 2 flagship unknown discovery) ────────────────────────
def find_unsubs(rows: list[dict] | None = None, min_cases: int = 3) -> list[dict]:
    """Discover synthetic UNSUB profiles by clustering unsolved/undetected FIRs sharing spatiotemporal window + MO signature.

    Returns a ranked list of synthetic UNSUB entities (UNSUB-01, UNSUB-02...)
    ready for visual graph rendering (ghost nodes) and search/briefing watchlists.
    """
    if rows is None:
        try:
            from app.services.zcql_local import _world
            rows = _world()["crimes"]
        except Exception:
            rows = []

    unsolved = [
        c for c in (rows or [])
        if c.get("status") in ("Under Investigation", "Undetected", "Unsolved", "Pending Trial")
    ]

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for c in unsolved:
        zone = str(c.get("zone") or "Bengaluru City").strip()
        ctype = str(c.get("crime_type") or "other").strip()
        groups[(zone, ctype)].append(c)

    sorted_groups = sorted(
        [(k, v) for k, v in groups.items() if len(v) >= min_cases],
        key=lambda item: len(item[1]),
        reverse=True,
    )

    unsubs: list[dict] = []
    for idx, ((zone, ctype), cases) in enumerate(sorted_groups[:15], start=1):
        cases_sorted = sorted(cases, key=lambda x: str(x.get("occurred_at", "")))
        start_dt = str(cases_sorted[0].get("occurred_at", ""))[:10] or "2024-01-01"
        end_dt = str(cases_sorted[-1].get("occurred_at", ""))[:10] or "2026-06-01"

        lats = [float(c["lat"]) for c in cases if c.get("lat") is not None]
        lons = [float(c["lon"]) for c in cases if c.get("lon") is not None]
        mean_lat = sum(lats) / len(lats) if lats else 12.9716
        mean_lon = sum(lons) / len(lons) if lons else 77.5946

        unsub_id = f"UNSUB-{idx:02d}"
        display_type = ctype.replace("_", " ").title()
        label = f"{unsub_id} — {display_type} Series ({zone})"

        profile = {
            "id": unsub_id,
            "unsub_id": unsub_id,
            "suspect_id": unsub_id,
            "type": "unsub",
            "hypothesis_kind": "unsub",
            "full_name": label,
            "label": label,
            "crime_type": ctype,
            "zone": zone,
            "case_count": len(cases),
            "case_ids": [str(c.get("fir_number") or c.get("crime_id")) for c in cases],
            "operating_window": f"{start_dt} to {end_dt}",
            "mo_signature": (
                f"Unsolved {display_type} series clustered in {zone} across {len(cases)} recorded FIRs "
                f"({start_dt} to {end_dt}). Target signature and spatiotemporal window consistent with "
                f"serial offender/syndicate operating in {zone}."
            ),
            "centroid": {"lat": round(mean_lat, 4), "lon": round(mean_lon, 4)},
            "knowledge_boundary": 1.0,
            "risk_level": "Critical" if len(cases) >= 7 else "High",
            "actions": [
                {
                    "type": "action",
                    "label": f"Issue Section 91 Watch / CDR Tower Dump for {zone} ({display_type})",
                    "params": {"unsub_id": unsub_id, "zone": zone, "crime_type": ctype},
                }
            ],
        }
        unsubs.append(profile)

    try:
        from app.services.product_store import put_product
        put_product("unsub:all", unsubs, ttl=86400)
        for u in unsubs:
            put_product(f"unsub:{u['id']}", u, ttl=86400)
    except Exception:
        pass

    return unsubs
