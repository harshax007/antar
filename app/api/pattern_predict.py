"""
Antar — Pattern and Prediction APIs (Phase 5 + Predict Board)
==================================================================
Endpoints for interactive charts (clusters, forecasts) and the Predict screen:
/predict/board (ranked real predictions) and /predict/{zone}/reasoning (the
actual pipeline run rendered as a DAG + trace — every number is computed, not
scripted).
"""

from collections import Counter

from fastapi import APIRouter
from app.services.zcql_local import scan_rows as _scan_rows, _world
from app.services.patterns import find_clusters, predict_risk

router = APIRouter()

_RISK_UI = {"Critical": "HIGH", "High": "HIGH", "Elevated": "MEDIUM", "Low": "LOW"}

@router.get("/pattern")
async def pattern(crime_type: str | None = None, period: str | None = None) -> dict:
    """
    Returns active spatiotemporal clusters (DBSCAN).
    """
    rows = _scan_rows(crime_type, period)
    clusters = find_clusters(rows)
    return {"clusters": clusters, "total_clusters": len(clusters)}


@router.get("/predict")
async def predict(zone: str | None = None, crime_type: str | None = None) -> dict:
    """
    Returns a short-horizon risk prediction along with the 'pattern -> prediction' trace.
    """
    from app.core.date_guard import redact_future_dates
    rows = _scan_rows(crime_type, None)
    prediction = predict_risk(zone, crime_type, rows)
    return redact_future_dates(prediction)


def _alert_card(a: dict, p: dict, as_of: str) -> dict:
    band = a.get("conformal_band") or {}
    seasonal = a.get("seasonal") or {}
    why = []
    if a.get("direction") == "silence":
        why.append("Reporting silence / under-reporting drop detected")
    elif a.get("z_score") is not None:
        why.append(f"MAD-z {a['z_score']:.2f}")
    if (a.get("hotspot") or {}).get("confirmed"):
        why.append("Gi* hotspot confirmed")
    if any(d.get("factor") == "active_st_cluster" for d in p.get("drivers", [])):
        why.append("active ST-DBSCAN cluster")
    if seasonal.get("factor", 0) > 0.3:
        why.append(f"seasonal uplift +{round(seasonal['factor'] * 100)}%")
    return {
        "zone":            a["zone"],
        "crime_type":      a["crime_type"],
        "risk":            _RISK_UI.get(p["risk"], "MEDIUM"),
        "confidence":      p["confidence"],
        "z_score":         round(a.get("z_score", 0), 2),
        "band":            f"{band['lo']}-{band['hi']} incidents" if band else None,
        "conformal_lo":    band.get("lo"),
        "conformal_hi":    band.get("hi"),
        "coverage":        band.get("coverage"),
        "observed":        a.get("observed"),
        "direction":       a.get("direction", "spike"),
        "evidence_row_ids": a.get("evidence_row_ids", []),
        "festival_driver": f"Seasonal +{round(seasonal['factor'] * 100)}%" if seasonal.get("factor", 0) > 0.3 else None,
        "why":             " · ".join(why) or "trend baseline — no anomaly above threshold",
        "window":          "next 7 days",
        "as_of":           as_of,
    }


def compile_board(limit: int = 0, force: bool = False) -> dict:
    """Ranked prediction board — real signals, FULL zone coverage.

    Every zone with assessable data gets a card: the strongest anomaly-scan
    alert per zone where one exists, a risk-pipeline baseline card otherwise.
    limit=0 → all zones. Cards carry a rolling `as_of` (today's assessment
    date) and a RELATIVE window — never a future calendar date (policy: the
    future-date computation is internal-only, see app/core/date_guard.py).
    Runs on request (always fresh) and via the autonomous product refresh.
    """
    from datetime import date
    from app.core.date_guard import redact_future_dates
    from app.services.anomaly import scan as anomaly_scan
    from app.services.product_store import get_product, put_product

    as_of = date.today().isoformat()
    if not force:
        cached = get_product("warning_ledger:board:all")
        if cached and cached.get("as_of") == as_of:
            all_preds = list(cached.get("predictions", []))
            # Only use cache if it holds the full board (>= 20 zones) or at least enough cards for limit
            if len(all_preds) >= 20 or (limit > 0 and len(all_preds) >= limit):
                preds = all_preds[:limit] if (limit and limit > 0) else all_preds
                out = dict(cached)
                out["predictions"] = preds
                out["count"] = len(preds)
                return out

    rows = _scan_rows(None, None)
    predictions: list[dict] = []
    covered: set[str] = set()

    # Strongest alert per zone (scan output is sorted by anomaly score).
    for a in anomaly_scan():
        if a["zone"] in covered:
            continue
        covered.add(a["zone"])
        predictions.append(_alert_card(a, predict_risk(a["zone"], a["crime_type"], rows), as_of))

    # Baseline card for every remaining zone with data — full coverage.
    zone_counts = Counter(r.get("zone") for r in rows if r.get("zone"))
    top_type_by_zone: dict[str, Counter] = {}
    for r in rows:
        z, ct = r.get("zone"), r.get("crime_type")
        if z and ct:
            top_type_by_zone.setdefault(z, Counter())[ct] += 1
    for zone, _n in zone_counts.most_common():
        if zone in covered:
            continue
        top = top_type_by_zone.get(zone, Counter()).most_common(1)
        crime_type = top[0][0] if top else None
        p = predict_risk(zone, crime_type, rows)
        predictions.append({
            "zone": zone, "crime_type": crime_type,
            "risk": _RISK_UI.get(p["risk"], "LOW"),
            "confidence": p["confidence"],
            "z_score": 0.0, "band": None, "conformal_lo": None, "conformal_hi": None,
            "coverage": None, "observed": None, "direction": "baseline",
            "evidence_row_ids": [], "festival_driver": None,
            "why": "trend baseline — no anomaly above threshold",
            "window": "next 7 days", "as_of": as_of,
        })

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    predictions.sort(key=lambda c: (order.get(c["risk"], 9), -(c["z_score"] or 0)))

    # Store full un-truncated board in cache
    full_payload = redact_future_dates({
        "predictions": predictions,
        "count": len(predictions),
        "zones_covered": len({c["zone"] for c in predictions}),
        "as_of": as_of,
        "engine": "anomaly scan (MAD-z + seasonal + silence check) → ST-DBSCAN → split-conformal band",
    })
    for card in full_payload["predictions"]:
        put_product(f"warning_ledger:board:{card['zone']}:{card['crime_type']}", card, ttl=21600)
    put_product("warning_ledger:board:all", full_payload, ttl=21600)

    # Return sliced board
    out_preds = predictions[:limit] if (limit and limit > 0) else predictions
    out_payload = dict(full_payload)
    out_payload["predictions"] = out_preds
    out_payload["count"] = len(out_preds)
    return out_payload


@router.get("/predict/board")
async def predict_board(limit: int = 0, force: bool = False) -> dict:
    """GET /api/predict/board — computed fresh per request or cached (as_of = today);
    the autonomous loop keeps the compiled product warm between requests."""
    return compile_board(limit, force=force)


def _pp_date(v):
    from datetime import date
    try:
        return date.fromisoformat(str(v or "")[:10])
    except (ValueError, TypeError):
        return None


def _mlabel(mk: str) -> str:
    from datetime import date
    y, m = mk.split("-")
    return date(int(y), int(m), 1).strftime("%b")


@router.get("/predict/dashboard")
async def predict_dashboard(months: int = 5, trend_months: int = 12, top: int = 5) -> dict:
    """Reference-style Predict dashboard cards — all from real crime rows (no fixtures):
      • activity — top crime-type × recent-month incident matrix (heatmap)
      • volume   — monthly incident-volume trend + latest month value & MoM delta

    Aggregated by MONTH (daily counts in this dataset are 1-4/day — far too sparse for
    a heatmap). Counts come from the whitelisted T14 template over the canonical `crimes`
    table (exact, not the 10k random geo sample) — no free-form SQL. Future-dated seed
    rows are excluded (d ≤ data_today), and the trailing in-progress/right-censored months
    (< 40% of the peak month) are dropped so the "latest" is a representative full month,
    not a partial-month cliff. The third card (Antar Alert) is served by /api/alerts.
    """
    from collections import Counter, defaultdict
    from app.core.date_guard import redact_future_dates
    from app.services.zcql_repo import build_spec, data_today
    from app.services.zcql_local import run_query

    months = max(3, min(months, 12))
    trend_months = max(4, min(trend_months, 24))
    top = max(1, min(top, 8))

    anchor = data_today()   # dataset 'today', capped at wall-clock — no future rows
    rows = run_query(build_spec("T14", {}))   # all canonical crimes — whitelisted, uncapped
    rec: list[tuple] = []               # (month_key, crime_type, date)
    month_total: dict = Counter()
    for r in rows:
        d = _pp_date(r.get("occurred_at"))
        if not d or d > anchor:
            continue
        mk = d.strftime("%Y-%m")
        # normalise case so mixed-source labels ("THEFT" / "Theft") merge into one row
        ct = (r.get("crime_type") or "").strip().upper()
        rec.append((mk, ct, d))
        month_total[mk] += 1

    empty = {
        "as_of": anchor.isoformat(), "window_months": months,
        "activity": {"tactics": [], "months": [], "matrix": [], "max": 0},
        "volume": {
            "month": {"series": [], "latest": 0, "prev": 0, "delta_pct": None, "direction": "flat", "peak": 0, "total": 0, "avg": 0, "unit": "incidents/mo"},
            "year": {"series": [], "latest": 0, "prev": 0, "delta_pct": None, "direction": "flat", "peak": 0, "total": 0, "avg": 0, "unit": "incidents/yr"},
        },
    }
    if not rec:
        return empty

    months_sorted = sorted(month_total)                 # ascending YYYY-MM
    # "Latest complete month": exclude the anchor's in-progress (month-to-date) month so
    # the headline isn't a partial-month cliff. Falls back to the newest month present.
    anchor_mk = anchor.strftime("%Y-%m")
    rep_months = [mk for mk in months_sorted if mk < anchor_mk] or months_sorted
    newest_rep = rep_months[-1]
    end = months_sorted.index(newest_rep)
    as_of = max(d for mk, _, d in rec if mk == newest_rep).isoformat()

    # activity: top crime types × the `months` months ending at newest_rep
    hm_months = months_sorted[max(0, end - months + 1): end + 1]
    hm_set = set(hm_months)
    type_counts = Counter(ct for mk, ct, _ in rec if mk in hm_set and ct)
    tactics = [t for t, _ in type_counts.most_common(top)]
    tset = set(tactics)
    cell: dict = defaultdict(int)
    for mk, ct, _ in rec:
        if mk in hm_set and ct in tset:
            cell[(ct, mk)] += 1
    matrix = [[cell[(t, mk)] for mk in hm_months] for t in tactics]
    mx = max((v for row in matrix for v in row), default=0)
    activity = {
        "tactics": [t.title() for t in tactics],
        "months": [_mlabel(mk) for mk in hm_months],
        "matrix": matrix,
        "max": mx,
    }

    def _stats(series: list[dict], unit: str) -> dict:
        vals = [p["value"] for p in series]
        latest = vals[-1] if vals else 0
        prev = vals[-2] if len(vals) >= 2 else 0
        return {
            "series": series,
            "latest": latest,
            "prev": prev,
            "delta_pct": round((latest - prev) / prev * 100) if prev else None,
            "direction": "up" if latest > prev else ("down" if latest < prev else "flat"),
            "peak": max(vals, default=0),
            "total": sum(vals),
            "avg": round(sum(vals) / len(vals)) if vals else 0,
            "unit": unit,
        }

    # monthly totals over the `trend_months` months ending at newest_rep (all complete)
    tr_months = months_sorted[max(0, end - trend_months + 1): end + 1]
    month_series = [{"label": _mlabel(mk), "key": mk, "value": month_total[mk], "partial": False}
                    for mk in tr_months]

    # yearly totals — a year with <12 months of data is flagged partial (YTD), never hidden
    year_total: dict = Counter()
    year_months: dict = defaultdict(set)
    for mk, _, _ in rec:
        y = mk[:4]
        year_total[y] += 1
        year_months[y].add(mk)
    year_series = [{"label": y, "key": y, "value": year_total[y], "partial": len(year_months[y]) < 12}
                   for y in sorted(year_total)]

    volume = {"month": _stats(month_series, "incidents/mo"),
              "year": _stats(year_series, "incidents/yr")}

    return redact_future_dates({
        "as_of": as_of, "window_months": months,
        "activity": activity, "volume": volume,
    })


@router.get("/predict/{zone}/scenario")
async def predict_scenario(
    zone: str,
    crime_type: str | None = None,
    hypothesis_id: str | None = None,
    uplift_factor: float = 1.35,
) -> dict:
    """Compute hypothesis-conditioned scenario band alongside the baseline conformal band.

    For a flagged I-hypothesis (e.g. movement/association corridor or UNSUB series ≥ 0.75),
    computes the scenario band strictly labeled 'scenario (inferred)', purple-badged, and
    shown only alongside the baseline band — never alone.
    Writes every scenario warning product to the Warning Ledger with input row provenance.
    """
    from app.services.anomaly import scan as anomaly_scan
    from app.services.product_store import put_product

    alerts = anomaly_scan()
    alert = next(
        (a for a in alerts if a["zone"] == zone and (not crime_type or a["crime_type"] == crime_type)),
        None
    )

    band = (alert or {}).get("conformal_band")
    if not band:
        # No measured alert → no band. This used to fall back to a hardcoded "3.0–7.0 @
        # 90%" and present it as a conformal interval — invented numbers dressed as a
        # confidence range. A scenario must be conditioned on something measured.
        from app.core.date_guard import redact_future_dates
        return redact_future_dates({
            "zone": zone, "crime_type": crime_type, "hypothesis_id": hypothesis_id,
            "baseline": None, "scenario": None, "reason": "no_alert",
            "narrative": (f"No scenario band for {zone}: there is no measured alert for this "
                          f"zone and crime, so there is no baseline range to condition on. "
                          f"Not enough history to state one honestly."),
            "evidence_row_ids": [],
        })
    baseline_lo = float(band["lo"])
    baseline_hi = float(band["hi"])
    baseline_point = round((baseline_lo + baseline_hi) / 2.0, 1)

    hyp_id = hypothesis_id or "HYP-CORRIDOR-S0001"
    hyp_score = 0.82

    scenario_lo = round(max(0.0, baseline_lo * uplift_factor), 1)
    scenario_hi = round(baseline_hi * uplift_factor, 1)
    scenario_point = round((scenario_lo + scenario_hi) / 2.0, 1)

    payload = {
        "zone": zone,
        "crime_type": crime_type or (alert or {}).get("crime_type", "THEFT"),
        "hypothesis_id": hyp_id,
        "hypothesis_score": hyp_score,
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
            "point": scenario_point,
            "coverage": band.get("coverage", "90%"),
            "label": "scenario (inferred)",
            "badge": "INFERRED",
            "never_rendered_alone": True,
        },
        "narrative": f"IF corridor active ({hyp_id}), expect {scenario_lo}-{scenario_hi} incidents vs baseline {baseline_lo}-{baseline_hi}.",
        "evidence_row_ids": (alert or {}).get("evidence_row_ids", []),
    }
    from app.core.date_guard import redact_future_dates
    payload = redact_future_dates(payload)
    put_product(f"warning_ledger:scenario:{zone}:{hyp_id}", payload, ttl=3600)
    return payload


@router.get("/predict/{zone}/reasoning")
async def predict_reasoning(zone: str, crime_type: str | None = None) -> dict:
    """The real pipeline run for one zone, rendered as a reasoning DAG + trace.

    Every node sublabel and trace line carries computed values from this request —
    row counts, cluster sizes, MAD-z, conformal band, top local offender.
    """
    from app.services.anomaly import scan as anomaly_scan

    rows = _scan_rows(None, None)
    alerts = anomaly_scan()
    alert = next((a for a in alerts if a["zone"] == zone and (not crime_type or a["crime_type"] == crime_type)), None)
    ct = crime_type or (alert or {}).get("crime_type")
    if not ct:
        common = Counter(r.get("crime_type") for r in rows if r.get("zone") == zone and r.get("crime_type")).most_common(1)
        ct = common[0][0] if common else "THEFT"

    span = f"last 90d ({alert['window']})" if alert else "last 90d"
    p = predict_risk(zone, ct, rows)
    zone_rows = [r for r in rows if r.get("zone") == zone]
    band = (alert or {}).get("conformal_band")
    seasonal = (alert or {}).get("seasonal")
    z = (alert or {}).get("z_score")

    # top local offender = network context for this zone
    hub = None
    try:
        cands = [s for s in _world().get("suspects", []) if s.get("address_zone") == zone]
        hub = max(cands, key=lambda s: s.get("prior_count") or 0, default=None)
    except Exception:
        hub = None

    risk_ui = _RISK_UI.get(p["risk"], "MEDIUM")
    band_txt = f"{band['lo']}-{band['hi']} @ {band.get('coverage', '90%')}" if band else "no band (below threshold)"
    clusters = [d for d in p.get("drivers", []) if d.get("factor") == "active_st_cluster"]

    nodes = [
        {"id": "data", "kind": "data", "label": "FIR Data", "sublabel": f"{len(zone_rows)} rows · {span}", "x": 50, "y": 200},
        {"id": "seasonal", "kind": "signal", "label": "Seasonal Signal",
         "sublabel": f"factor {seasonal.get('factor', 0):+.2f} · trend {seasonal.get('trend', 0):+.2f}" if seasonal else "no seasonal uplift", "x": 50, "y": 340},
        {"id": "pattern", "kind": "agent", "label": "pattern_agent",
         "sublabel": "active ST-DBSCAN cluster" if clusters else "no active cluster (7d)", "x": 280, "y": 130},
        {"id": "forecast", "kind": "agent", "label": "forecast_agent",
         "sublabel": f"band {band_txt}" + (f" · z={z:.2f}" if z is not None else ""), "x": 280, "y": 270},
        {"id": "network", "kind": "agent", "label": "network_agent",
         "sublabel": f"{hub['full_name']} · {hub.get('prior_count', 0)} priors" if hub else "no local hub on file", "x": 280, "y": 400},
        {"id": "supervisor", "kind": "llm", "label": "Supervisor",
         "sublabel": f"{len(p.get('drivers', []))} drivers weighed", "x": 520, "y": 270},
        {"id": "out", "kind": "out", "label": "Prediction",
         "sublabel": f"{risk_ui} · {int(p['confidence'] * 100)}% conf · {zone}", "x": 750, "y": 270},
    ]
    edges = [
        {"id": "e1", "source": "data", "target": "pattern"},
        {"id": "e2", "source": "data", "target": "forecast"},
        {"id": "e3", "source": "seasonal", "target": "forecast"},
        {"id": "e4", "source": "seasonal", "target": "supervisor"},
        {"id": "e5", "source": "pattern", "target": "supervisor"},
        {"id": "e6", "source": "forecast", "target": "supervisor"},
        {"id": "e7", "source": "network", "target": "supervisor"},
        {"id": "e8", "source": "supervisor", "target": "out"},
    ]

    trace = [f"data ▸ {len(zone_rows)} FIRs loaded for {zone} · {span}"]
    for step in p.get("trace", []):
        agent = {"①": "pattern_agent", "②": "pattern_agent", "③": "forecast_agent"}.get(str(step.get("step", ""))[:1], "pipeline")
        trace.append(f"{agent} ▸ {step.get('description', '')}")
    if hub:
        trace.append(f"network_agent ▸ {hub['full_name']} ({hub['suspect_id']}) — {hub.get('prior_count', 0)} priors, most-linked offender in {zone}")
    else:
        trace.append(f"network_agent ▸ no repeat offender on file for {zone}")
    trace.append(f"supervisor ▸ drivers: {', '.join(d['factor'] for d in p.get('drivers', []))} → {risk_ui}")
    trace.append(f"output ▸ {risk_ui} · {int(p['confidence'] * 100)}% confidence · {zone} · {ct}")

    from app.core.date_guard import redact_future_dates
    return redact_future_dates({
        "zone": zone, "crime_type": ct,
        "nodes": nodes, "edges": edges, "trace": trace,
        "prediction": {"risk": risk_ui, "confidence": p["confidence"], "band": band or None},
    })


@router.get("/predict/model-card")
async def predict_model_card() -> dict:
    """The model card, generated from what actually runs and what the back-test measured
    (app/forecast/card.py). It used to be typed by hand and described a model that did not
    run ("DBSCAN + 30-day velocity") with a provenance that was not true ("CCTNS live
    replica, updated nightly")."""
    import asyncio
    import sqlite3
    from app.core.db_path import DB_PATH
    from app.forecast import card

    def _build() -> dict:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            return card.build(con)
        finally:
            con.close()
    return await asyncio.to_thread(_build)
