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
import re

from fastapi import APIRouter, Depends, HTTPException

from app.core.rate_limiter import rate_limit

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
async def district_detail(zone: str, end_date: Optional[str] = None, crime_type: Optional[str] = None) -> dict:
    """Single-district drill-down card.

    Without end_date: the startup cache (O(1)). With it: the card recounted for that day
    and the windows ending on it, optionally for one crime type - what the Map's calendar
    asks for.
    """
    if end_date:
        from datetime import date as _date
        from app.services.district_cache import dated as dc_dated
        try:
            anchor = _date.fromisoformat(end_date[:10])
        except ValueError:
            raise HTTPException(status_code=422, detail="end_date must be an ISO date (YYYY-MM-DD)")
        data = dc_dated(zone, anchor, crime_type or None)
    else:
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


@router.get("/repeat_locations")
async def repeat_locations_api(crime_type: Optional[str] = None, days: int = 90, end_date: Optional[str] = None,
                               district: Optional[str] = None) -> dict:
    """Places where cases keep being registered: 3+ FIRs on 2+ different days within about
    100 m (H3 hexagons), in the `days` ending on `end_date`. Online-crime stations, a station's
    default point and placeholder coordinates are left out (see app/services/repeat_locations.py)."""
    import asyncio
    from datetime import date as _date
    from types import SimpleNamespace
    from app.forecast.asof import current
    from app.services.repeat_locations import repeat_locations
    from app.services.zcql_repo import _crime_head_filters, normalize_crime_types, resolve_zones
    today_dt = current().as_of
    try:
        anchor = _date.fromisoformat(end_date[:10]) if end_date else today_dt
    except ValueError:
        raise HTTPException(status_code=422, detail="end_date must be an ISO date (YYYY-MM-DD)")
    anchor = min(anchor, today_dt)
    days = max(7, min(int(days or 90), 365))
    crime_filter = None
    if crime_type:
        # the same crime resolution as the chat templates (chain snatching and vehicle theft
        # include the real register's sub-headings), rendered as parameterised SQL
        parts, args = [], []
        for f in _crime_head_filters(SimpleNamespace(crime_types=normalize_crime_types([crime_type]), heads=[]),
                                     "crime_type", "CrimeHead_Name"):
            if f.op == "in":
                parts.append(f"UPPER(TRIM({f.column})) IN ({', '.join('?' * len(f.value))})")
                args += [str(v).strip().upper() for v in f.value]
            elif f.op == "head_or":
                heads, labels, tc = f.value
                parts.append(f"(UPPER(TRIM(CrimeHead_Name)) IN ({', '.join('?' * len(heads))}) "
                             f"OR UPPER(TRIM({tc})) IN ({', '.join('?' * len(labels))}))")
                args += [str(v).strip().upper() for v in heads] + [str(v).strip().upper() for v in labels]
        if parts:
            crime_filter = (" AND ".join(parts), args)
    dists = None
    if district:
        from app.services.zcql_repo import POLICE_UNITS
        # one police district, or several (a map shape such as Belagavi holds City and Dist)
        names = [d.strip() for d in district.split(",") if d.strip()][:8]
        dists = [z for z in resolve_zones(names) if z not in POLICE_UNITS] or names
    return await asyncio.to_thread(repeat_locations, anchor, days, crime_filter, dists)


_FIR_NO = re.compile(r"^\d{4}-[A-Z]{2,5}-\d{1,6}$")


def _count(v) -> Optional[int]:
    try:
        return int(float(v)) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _stage(v) -> Optional[str]:
    return v.replace("_", " ").strip().capitalize() if v else None


def _details(r) -> dict:
    """The case-detail fields a dot opens, cleaned: no placeholder text, no names."""
    ftype = (r["FIR_Type"] or "").strip()
    place = (r["Place_of_Offence"] or "").strip()
    group = (r["CrimeGroup_Name"] or "").strip()
    return {
        "fir_no": ftype if _FIR_NO.match(ftype) else None,
        "gravity": ftype if ftype in ("Heinous", "Non Heinous") else None,
        "group": group if group and group.upper() != (r["crime_type"] or "").strip().upper() else None,
        "act": (r["ActSection"] or "").strip() or None,
        "place": place if place and not place.lower().startswith("random") else None,
        "distance": (r["Distance_from_PS"] or "").strip() or None,
        "victims": _count(r["VICTIM_COUNT"]), "accused": _count(r["Accused_Count"]),
        "arrested": _count(r["Arrested_Count_No_"]), "chargesheeted": _count(r["Accused_ChargeSheeted_Count"]),
    }


@router.get("/day_cases")
async def day_cases(date: Optional[str] = None, crime_type: Optional[str] = None) -> dict:
    """The FIRs registered on one day across Karnataka, one row per FIR, for the Map's Day
    view: a dot per case, and the cases listed on a district's card. The same rows the
    day's counts come from (gi_star with days=0: FIRs.zone, the date, the exact crime type).

    No person is named: what the crime was, where, which station, and how far it has got.
    Complaint_Mode is never read (the seeded rows carry a complainant's name in it), and a
    field holding a placeholder ("Random Street in ...") is left empty rather than shown."""
    import asyncio
    from datetime import date as _date
    from app.forecast.asof import current
    today_dt = current().as_of
    try:
        day = _date.fromisoformat(date[:10]) if date else today_dt
    except ValueError:
        raise HTTPException(status_code=422, detail="date must be an ISO date (YYYY-MM-DD)")
    day = min(day, today_dt)

    def read() -> list[dict]:
        where, args = ["SUBSTR(date, 1, 10) = ?", "zone IS NOT NULL"], [day.isoformat()]
        if crime_type:
            where.append("crime_type = ?")
            args.append(crime_type)
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT fir_id, zone, district_norm, crime_type, CrimeHead_Name, station, geo_lat, geo_lon, "
                "Village_Area_Name, Beat_Name, FIR_Stage, status, FIR_Type, CrimeGroup_Name, ActSection, "
                "Place_of_Offence, Distance_from_PS, VICTIM_COUNT, Accused_Count, Arrested_Count_No_, "
                "Accused_ChargeSheeted_Count FROM FIRs WHERE " + " AND ".join(where) +
                " ORDER BY zone, station LIMIT 2000", args).fetchall()
        finally:
            con.close()
        return [{"fir_id": r["fir_id"], "zone": r["zone"], "district": r["district_norm"],
                 "crime": (r["crime_type"] or "").strip(), "head": r["CrimeHead_Name"],
                 "station": r["station"], "lat": r["geo_lat"], "lon": r["geo_lon"],
                 "area": r["Village_Area_Name"], "beat": r["Beat_Name"],
                 "stage": _stage(r["FIR_Stage"] or r["status"]), **_details(r)} for r in rows]

    cases = await asyncio.to_thread(read)
    return {"date": day.isoformat(), "crime_type": crime_type or "all", "total": len(cases), "cases": cases}


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


from pydantic import BaseModel, Field
class SummaryRequest(BaseModel):
    crime_type: str | None = Field(default=None, max_length=60)
    district: str | None = Field(default=None, max_length=80)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    stats: dict = Field(default_factory=dict)


# What the map is allowed to tell the model about a view. The page sends qualitative
# bands, not free text, so each one is checked against the values the page can produce;
# a place name is kept only if it looks like one. Anything else is dropped. Before this,
# the request body went into the prompt as written - any signed-in caller could use the
# endpoint to have the model write whatever they liked under "Written by Antar".
_SUMMARY_BANDS = {
    "trend": {"steady", "rising", "rising-sharp", "easing", "easing-sharp", "unknown"},
    "concentration": {"heavy", "focused", "spread"},
    "hotBand": {"none", "one", "few", "many"},
    "level": {"normal", "elevated", "high"},
}
_PLACE_RE = re.compile(r"^[A-Za-z\u0C80-\u0CFF][A-Za-z\u0C80-\u0CFF0-9 .&()'/-]{1,79}$")
_CRIME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 _&()/.,-]{1,59}$")


def _summary_facts(req: "SummaryRequest") -> dict:
    from app.core.rag_security import normalize_untrusted, detect_injection

    def place(v):
        s = normalize_untrusted(v, max_len=80) if isinstance(v, str) else ""
        return s if s and _PLACE_RE.match(s) and not detect_injection(s) else None

    st = req.stats if isinstance(req.stats, dict) else {}
    trend = st.get("trend")
    trend = trend.get("key") if isinstance(trend, dict) else trend
    crime = normalize_untrusted(req.crime_type, max_len=60) if req.crime_type else ""
    facts = {
        "crime_type": crime.replace("_", " ") if crime and _CRIME_RE.match(crime) else "all crimes",
        "location": place(req.district) or "Karnataka",
        "date": req.date,
        "trend": trend if isinstance(trend, str) and trend in _SUMMARY_BANDS["trend"] else "unknown",
        "busiest_area": place(st.get("lead")),
        "second_busiest_area": place(st.get("second")),
        "first_confirmed_hotspot": place(st.get("hotFirst")),
    }
    for key, out in (("concentration", "concentration"), ("hotBand", "confirmed_hotspots"), ("level", "overall_level")):
        if isinstance(st.get(key), str) and st[key] in _SUMMARY_BANDS[key]:
            facts[out] = st[key]
    return {k: v for k, v in facts.items() if v is not None}


@router.post("/view_summary", dependencies=[Depends(rate_limit(30, 0.2))])
async def view_summary(req: SummaryRequest):
    import json
    from app.core.rag_security import fence, detect_injection
    from app.services.quickml import quickml_generate
    facts = _summary_facts(req)
    system = ("You are a senior police analyst. In two or three plain sentences, say what the map view "
              "below shows and what deserves attention first. Use only the facts given: never add a "
              "number, a place or a cause that is not in them. Plain text, one paragraph, no markdown, "
              "no bullet points, no dramatic language.")
    prompt = ("Facts about the map view (qualitative bands the map computed):\n"
              + fence("map_view", json.dumps(facts, ensure_ascii=False), max_len=1200))
    try:
        summary = (await quickml_generate(system=system, user=prompt, temperature=0.3,
                                          max_tokens=300, retries=1) or "").strip()
        # the summary is prose about a map: no links, no markup, a bounded length
        if not summary or detect_injection(summary) or re.search(r"https?://|<[a-z/!]|```", summary, re.I):
            raise ValueError("summary rejected")
        return {"summary": re.sub(r"\s+", " ", summary)[:700]}
    except Exception:
        # no summary rather than an error message on screen: the page writes "In short"
        # from the rows it already shows
        return {"summary": None}
