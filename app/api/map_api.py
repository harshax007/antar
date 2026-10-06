"""
Antar — Map API (UC2 "Explore" surface · feature N2 / F3)
=============================================================
Hotspots, heat, choropleth and district drill-down.
/districts/rich and /district/{zone} read from the in-memory district_cache
(precomputed on startup) for instant response — no per-click SQL aggregation.
"""

from __future__ import annotations
import sqlite3
from typing import Optional
from fastapi import APIRouter, HTTPException

from app.services.district_cache import get_all as dc_all, get_district as dc_get

router = APIRouter()

from app.core.db_path import DB_PATH, ensure_db_staged


def _db() -> sqlite3.Connection:
    ensure_db_staged()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/hotspots")
async def hotspots(crime_type: Optional[str] = None, period: Optional[str] = None) -> dict:
    """Pre-aggregated zone hotspots — instant query from zone_summary table."""
    conn = _db()
    
    if crime_type:
        # Use crime_zone_summary for filtered results
        rows = conn.execute(
            "SELECT zone, SUM(n) AS weight, AVG(centroid_lat) AS lat, AVG(centroid_lon) AS lon "
            "FROM crime_zone_summary WHERE UPPER(crime_type) = UPPER(?) "
            "GROUP BY zone ORDER BY weight DESC LIMIT 40",
            (crime_type,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT zone, total_crimes AS weight, centroid_lat AS lat, centroid_lon AS lon "
            "FROM zone_summary WHERE centroid_lat IS NOT NULL "
            "ORDER BY weight DESC LIMIT 40"
        ).fetchall()
    conn.close()

    clusters = [dict(r) for r in rows if r["lat"]]
    points = [{"lat": c["lat"], "lon": c["lon"], "weight": c["weight"]} for c in clusters]
    note = (f"{sum(c['weight'] for c in clusters):,} incidents — hottest zone: {clusters[0]['zone']} ({clusters[0]['weight']:,} cases)."
            if clusters else "No incidents match this filter.")
    return {"points": points, "clusters": clusters, "seasonal_note": note, "total": len(points)}


@router.get("/districts")
async def districts(crime_type: Optional[str] = None, period: Optional[str] = None) -> dict:
    """District-level choropleth data — instant from summary tables."""
    conn = _db()
    if crime_type:
        rows = conn.execute(
            "SELECT zone AS district, SUM(n) AS weight, AVG(centroid_lat) AS lat, AVG(centroid_lon) AS lon "
            "FROM crime_zone_summary WHERE UPPER(crime_type) = UPPER(?) "
            "GROUP BY zone ORDER BY weight DESC LIMIT 60",
            (crime_type,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT zone AS district, total_crimes AS weight, centroid_lat AS lat, centroid_lon AS lon "
            "FROM zone_summary ORDER BY weight DESC LIMIT 60"
        ).fetchall()
    conn.close()
    return {"districts": [dict(r) for r in rows], "total": len(rows)}


@router.get("/heat")
async def heat(crime_type: Optional[str] = None, period: Optional[str] = None) -> dict:
    """Heatmap points sampled from individual FIR rows with valid coords."""
    if not crime_type and not period:
        from app.services import product_store
        cached = product_store.get_product("concurrency:districts")
        if cached:
            return cached
    conn = _db()
    where_parts = ["geo_ok = 1"]
    params: list = []
    if crime_type:
        where_parts.append("UPPER(CrimeGroup_Name) = UPPER(?)")
        params.append(crime_type)
    
    from datetime import timedelta
    from app.forecast.asof import current
    today = current().as_of              # the map's shared as-of, not each layer's own clock
    if period:
        where_parts.append("date <= ?")
        params.append(today.isoformat())
    if period == "last_7_days":
        where_parts.append("date >= ?")
        params.append((today - timedelta(days=7)).isoformat())
    elif period == "this_month":
        where_parts.append("date >= ?")
        params.append(today.replace(day=1).isoformat())
    elif period == "last_3_months":
        m = today.month - 3; y = today.year
        if m <= 0: m += 12; y -= 1
        where_parts.append("date >= ?")
        params.append(today.replace(year=y, month=m, day=1).isoformat())

    where = "WHERE " + " AND ".join(where_parts)
    rows = conn.execute(
        f"SELECT geo_lat AS lat, geo_lon AS lon FROM FIRs {where} ORDER BY RANDOM() LIMIT 5000",
        params
    ).fetchall()
    conn.close()
    return {"points": [{"lat": r["lat"], "lon": r["lon"], "weight": 1} for r in rows], "total": len(rows)}


@router.get("/districts/rich")
async def districts_rich() -> dict:
    """All districts with precomputed aggregates — instant choropleth fill data."""
    return {"districts": dc_all(), "total": len(dc_all())}


@router.get("/district/{zone}")
async def district_detail(zone: str) -> dict:
    """Single-district drill-down card (O(1) cache lookup, < 1 ms)."""
    data = dc_get(zone)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Zone '{zone}' not found in cache")
    return data


@router.get("/gi_star")
async def gi_star_hotspots(crime_type: Optional[str] = None, days: int = 30, end_date: Optional[str] = None) -> dict:
    """Getis-Ord Gi* significance surface — spatial hotspot rings for the Map screen.

    Returns ALL zones with their Gi* statistic and p-value so the frontend can render:
      • is_hotspot=True  → confirmed spatial cluster (p < 0.05), red ring
      • gi_stat > 0      → above-average concentration vs neighbours (warm)
      • gi_stat < 0      → below-average (cold spot)

    crime_type=None → aggregate across all crime types.
    days            → rolling window width (default 30 calendar days).
    end_date        → anchor the window here (ISO date, e.g. "2026-06-15") instead of
                      today — drives the Map screen's calendar date-select.
    """
    from datetime import date as _date
    from app.forecast.asof import current
    from app.services.anomaly import gi_star_surface
    today_dt = current().as_of           # the map's shared as-of (ANTAR_FORECAST_AS_OF)
    anchor = _date.fromisoformat(end_date) if end_date else today_dt
    if anchor > today_dt:
        anchor = today_dt
    zones     = gi_star_surface(crime_type=crime_type, days=days, end_date=anchor)
    confirmed = sum(1 for z in zones if z["is_hotspot"])
    return {
        "zones":              zones,
        "confirmed_hotspots": confirmed,
        "total_zones":        len(zones),
        "window_days":        days,
        "crime_type":         crime_type or "all",
        "end_date":           anchor.isoformat(),
    }


@router.get("/flow")
async def flow(crime_type: Optional[str] = None, period: Optional[str] = None) -> dict:
    return {"flow": []}


@router.get("/predicted")
async def predicted(crime_type: Optional[str] = None, period: Optional[str] = None) -> dict:
    """Forecast hotspots for the next 7 days — now a real forecast.

    This used to return the three zones with the most crime *this calendar month*,
    labelled "predicted", with a fabricated "Surge detected … increase patrols" line (no
    surge was ever measured), from a precomputed table that stopped in 2026-06. It is now
    a thin view over /api/forecast/hotspots (stations), which callers should prefer; the
    response keeps its old keys so the map keeps working.
    """
    import asyncio
    from datetime import timedelta
    from app.forecast import service as S
    from app.forecast.asof import current

    def work():
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            try:
                cat = S.resolve_category(crime_type)
            except S.Refusal as r:
                return {"refused": r.to_dict(), "items": []}
            try:
                return S.hotspots(con, horizon=7, category=cat, unit_type="station", limit=3)
            except (S.NotReady, sqlite3.OperationalError) as e:
                # NotReady text is ours; an OperationalError can name the db file
                return {"preparing": str(e) if isinstance(e, S.NotReady) else
                        "The forecast store is being built (about a minute).", "items": []}
        finally:
            con.close()

    fc = await asyncio.to_thread(work)
    items = fc.get("items", [])
    predicted_hotspots = [
        {"lat": i["lat"], "lon": i["lon"], "zone": i["unit"], "district": i["district"],
         "expected": i["expected"], "band80": i["band80"], "band90": i["band90"],
         "summary": i["summary"], "evidence_class": "I"}
        for i in items if i.get("lat") is not None]
    suggestions = [
        {"zone": i["unit"],
         "suggestion": f"Forecast for {i['unit']}: {i['summary'][0].lower()}{i['summary'][1:]} "
                       f"Inferred — a patrol can be proposed from the map for approval."}
        for i in items]

    # KDE of the 60 days of FIRs up to the as-of date (not the wall clock of this layer)
    today = current().as_of
    where = ["geo_ok = 1", "date BETWEEN ? AND ?"]
    params: list = [(today - timedelta(days=60)).isoformat(), today.isoformat()]
    if crime_type:
        where.append("UPPER(CrimeGroup_Name) = UPPER(?)")
        params.append(crime_type)
    conn = _db()
    fir_rows = conn.execute(
        f"SELECT geo_lat AS lat, geo_lon AS lon, date AS occurred_at, District_Name AS zone "
        f"FROM FIRs WHERE {' AND '.join(where)} ORDER BY date DESC LIMIT 2000", params).fetchall()
    conn.close()
    from app.services.geo_density import compute_kde_geojson
    contours = compute_kde_geojson([dict(r) for r in fir_rows])
    return {"predicted_hotspots": predicted_hotspots, "beat_suggestions": suggestions,
            "contours": contours, "as_of": fc.get("as_of"), "evidence_class": "I",
            "source": "/api/forecast/hotspots", **({"refused": fc["refused"]} if "refused" in fc else {}),
            **({"preparing": fc["preparing"]} if "preparing" in fc else {})}


@router.get("/darkzones")
async def darkzones() -> dict:
    """
    Returns the Dark-Zone Surface (Geography of the Unknown).
    Answers 'Where do we know the least?' by combining gap_count, silence_alerts,
    and unresolved_share across Karnataka SP zones.
    """
    conn = _db()
    rows = conn.execute(
        "SELECT District_Name AS zone, Accused_Count, Accused_ChargeSheeted_Count, geo_lat AS lat, geo_lon AS lon FROM FIRs WHERE geo_ok = 1 LIMIT 4000"
    ).fetchall()
    conn.close()

    from app.services.geo_density import compute_dark_zones
    row_dicts = [dict(r) for r in rows]
    zones = compute_dark_zones(row_dicts)
    return {
        "zones": zones,
        "total": len(zones),
        "most_critical": zones[0]["zone"] if zones else None,
    }


@router.get("/anchor_areas")
async def anchor_areas(unsub_id: Optional[str] = None) -> dict:
    """
    Returns UNSUB Anchor Areas computed using 2D convex hull and haversine radius
    around cluster coordinates.
    """
    conn = _db()
    rows = conn.execute(
        "SELECT District_Name AS zone, geo_lat AS lat, geo_lon AS lon FROM FIRs WHERE geo_ok = 1 LIMIT 4000"
    ).fetchall()
    conn.close()

    from app.services.geo_density import compute_unsub_anchor_areas
    row_dicts = [dict(r) for r in rows]
    areas = compute_unsub_anchor_areas(row_dicts)
    if unsub_id:
        areas = [a for a in areas if a["unsub_id"] == unsub_id]
    return {
        "anchor_areas": areas,
        "total": len(areas),
    }


from pydantic import BaseModel
class SummaryRequest(BaseModel):
    crime_type: str | None = None
    district: str | None = None
    date: str
    stats: dict

@router.post("/view_summary")
async def view_summary(req: SummaryRequest):
    from app.services.quickml import quickml_generate
    prompt = f"""
    You are an intelligence analyst. Summarize the following map view data.
    Provide a minimal, highly insightful 2-3 sentence paragraph that reads easily.
    Avoid overly colorful or dramatic language. Stick to crisp intelligence. Focus on actionable insights or notable patterns.
    
    Context:
    Crime Type: {req.crime_type or 'All Crimes'}
    Location: {req.district or 'Karnataka State'}
    Date: {req.date}
    
    Data Stats:
    {req.stats}
    """
    
    system = "You are a senior intelligence analyst. Provide brief, data-driven, actionable insights in plain text without markdown or bullet points. Output exactly 1 paragraph."
    
    try:
        summary = await quickml_generate(system=system, user=prompt, temperature=0.3)
        return {"summary": summary.strip()}
    except Exception as e:
        return {"summary": "Unable to generate summary at this time. Please check the data manually."}
