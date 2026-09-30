"""
Antar — Analytics API (UC2 "Explore" surface · feature N4)
==============================================================
Read-only trend + breakdown + conformal-forecast aggregations for dashboard charts.
All queries go through whitelisted ZCQL templates (no free-form SQL).

Endpoints:
  GET /api/analytics/trends            — monthly trend series
  GET /api/analytics/breakdown         — count breakdown by type / zone / status
  GET /api/analytics/forecast          — observed + calibrated conformal bands (Recharts)
  GET /api/analytics/forecast/top      — top-N anomalies for Predict screen alert cards
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services.zcql_repo import build_spec
from app.services.zcql_local import run_query

router = APIRouter()


def _rows(template_id: str, params: dict) -> list[dict]:
    return run_query(build_spec(template_id, params))


def _as_date(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v or "")[:10])
    except (ValueError, TypeError):
        return None


@router.get("/trends")
async def trends(crime_type: str | None = None, zone: str | None = None, months: int = 12) -> dict:
    """Monthly crime trend, optionally filtered by type / zone (template T3)."""
    params: dict = {"months": months}
    if crime_type:
        params["crime_types"] = crime_type
    if zone:
        params["zones"] = zone
    return {"crime_type": crime_type, "zone": zone, "months": months,
            "series": _rows("T3", params)}


# breakdown dimension → (template, label column)
_BREAKDOWN = {"type": ("T13", "crime_type"), "zone": ("T11", "zone"), "status": ("T8", "status")}


@router.get("/breakdown")
async def breakdown(by: str = "type", zone: str | None = None, period: str | None = None) -> dict:
    """Crime counts grouped by `type` | `zone` | `status` (unknown → type)."""
    key = (by or "type").lower()
    tid, label_key = _BREAKDOWN.get(key, _BREAKDOWN["type"])
    params: dict = {}
    if zone:
        params["zones"] = zone
    if period and tid != "T8":          # T8 (status) has no period param
        params["period"] = period
    rows = _rows(tid, params)
    return {"by": key, "rows": [{"label": r.get(label_key), "n": r.get("n", 0)} for r in rows]}


# ── /forecast/top must be declared BEFORE /forecast (FastAPI: static before parameterised)

@router.get("/forecast/top")
async def forecast_top(limit: int = 10) -> dict:
    """Top anomalies by score — Predict screen alert cards.
    Re-uses the live anomaly scan so the list is always fresh.
    Each result carries its conformal_band, trace, and full MAD-z / Gi* / seasonal breakdown.
    """
    from app.core.date_guard import redact_future_dates
    from app.services.anomaly import scan as _scan
    results = _scan()
    return redact_future_dates({
        "count": len(results),
        "anomalies": results[:max(1, limit)],
    })


@router.get("/forecast")
async def forecast(crime_type: str, zone: str, horizon_weeks: int = 4) -> dict:
    """Recharts-ready combined series: 13-week observed history + calibrated conformal bands.

    Response shape:
      series: list of data points, each {week, label, date?, observed?, forecast?, lo?, hi?}
        • week ≤ 0  → historical (observed filled, forecast/lo/hi = null)
        • week > 0  → future     (forecast/lo/hi filled, observed = null)
      meta:   {baseline_med, trend, seasonal_lift, coverage, horizon_weeks}
      anomaly: matching alert from the last scan, or null

    The amber confidence cone in Recharts is driven by lo / hi on the future points.
    """
    from app.services.anomaly import forecast_band as _fb, BASELINE_WEEKS

    if not crime_type or not zone:
        raise HTTPException(status_code=422, detail="crime_type and zone are required")

    # ── Historical weekly counts for this (crime_type, zone) series ──────────────
    all_rows = run_query(build_spec("T14", {}))
    dated = [
        _as_date(r.get("occurred_at"))
        for r in all_rows
        if r.get("crime_type") == crime_type and r.get("zone") == zone
    ]
    dated = [d for d in dated if d]

    if not dated:
        return {
            "crime_type": crime_type, "zone": zone,
            "meta": {}, "series": [], "anomaly": None,
        }

    ref_now = max(dated)
    weekly: dict[int, int] = defaultdict(int)
    for d in dated:
        w = (ref_now - d).days // 7
        if 0 <= w <= BASELINE_WEEKS:
            weekly[w] += 1

    # Historical series: week -BASELINE_WEEKS … 0 (chronological, oldest first)
    series = []
    for w in range(BASELINE_WEEKS, -1, -1):
        week_date = ref_now - timedelta(weeks=w)
        series.append({
            "week":     -w,
            "label":    "Now" if w == 0 else f"Wk-{w}",
            "date":     week_date.isoformat(),
            "observed": weekly.get(w, 0),
            "forecast": None,
            "lo":       None,
            "hi":       None,
        })

    # ── Conformal forecast bands for future weeks ─────────────────────────────────
    band_result = _fb(crime_type, zone, max(1, horizon_weeks))
    for band in band_result.get("bands", []):
        series.append({
            "week":     band["week"],
            "label":    band["label"],
            "date":     None,
            "observed": None,
            "forecast": band["forecast"],
            "lo":       band["lo"],
            "hi":       band["hi"],
        })

    # ── Current anomaly status from last in-memory scan ───────────────────────────
    from app.services.alerts_store import list_recent
    anomaly = next(
        (a for a in list_recent(200)
         if a.get("crime_type") == crime_type and a.get("zone") == zone),
        None,
    )

    from app.core.date_guard import redact_future_dates
    return redact_future_dates({
        "crime_type": crime_type,
        "zone":       zone,
        "meta": {
            "baseline_med":  band_result.get("baseline_med"),
            "trend":         band_result.get("trend"),
            "seasonal_lift": band_result.get("seasonal_lift"),
            "coverage":      "90%",
            "horizon_weeks": horizon_weeks,
        },
        "series":  series,
        "anomaly": anomaly,
    })
