"""
Antar — District aggregates cache (§5: materialization)
=============================================================
Precomputes per-district {fir_count, top_crimes, risk_level, trend, predicted, lat, lon}
on startup so the Map choropleth + district drill-down card return in < 5 ms
without any per-click SQL aggregation.

Startup wiring (main.py lifespan):
    from app.services.district_cache import refresh as refresh_districts
    refresh_districts()
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Optional

_cache: Optional[dict[str, dict]] = None   # zone → aggregate dict

from app.core.db_path import DB_PATH


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _risk_level(this_month: int, prior_month: int) -> str:
    """High / Medium / Low based on count + month-over-month ratio."""
    ratio = this_month / max(1, prior_month)
    if this_month >= 80 or ratio >= 1.5:
        return "High"
    if this_month >= 30 or ratio >= 1.1:
        return "Medium"
    return "Low"


def _trend_str(current: int, prior: int) -> str:
    if prior == 0:
        return "+100%" if current > 0 else "—"
    pct = round((current - prior) / prior * 100)
    return f"+{pct}%" if pct >= 0 else f"{pct}%"


def refresh() -> dict[str, dict]:
    """Rebuild district aggregates from SQLite. < 20 ms for the seed world."""
    global _cache

    conn = _db()
    today = date.today()
    this_month_start = today.replace(day=1).isoformat()
    # previous calendar month
    prior_end = today.replace(day=1)
    prior_start = (prior_end - timedelta(days=1)).replace(day=1).isoformat()

    # This-month FIR counts per zone
    cur_rows = conn.execute(
        "SELECT District_Name AS zone, COUNT(*) AS n FROM FIRs "
        "WHERE date >= ? GROUP BY zone",
        (this_month_start,),
    ).fetchall()
    cur_counts = {r["zone"]: r["n"] for r in cur_rows}

    # Prior-month FIR counts per zone
    prior_rows = conn.execute(
        "SELECT District_Name AS zone, COUNT(*) AS n FROM FIRs "
        "WHERE date >= ? AND date < ? GROUP BY zone",
        (prior_start, this_month_start),
    ).fetchall()
    prior_counts = {r["zone"]: r["n"] for r in prior_rows}

    # All-time total per zone (used for risk denominator + map choropleth weight)
    total_rows = conn.execute(
        "SELECT District_Name AS zone, COUNT(*) AS n FROM FIRs GROUP BY zone"
    ).fetchall()
    total_counts = {r["zone"]: r["n"] for r in total_rows}

    # Top-3 crime types per zone (ordered by count)
    crime_rows = conn.execute(
        "SELECT District_Name AS zone, CrimeGroup_Name AS crime, COUNT(*) AS n "
        "FROM FIRs GROUP BY zone, crime ORDER BY zone, n DESC",
    ).fetchall()
    crimes_by_zone: dict[str, list[str]] = {}
    for r in crime_rows:
        if r["zone"] not in crimes_by_zone:
            crimes_by_zone[r["zone"]] = []
        if len(crimes_by_zone[r["zone"]]) < 3:
            crimes_by_zone[r["zone"]].append(r["crime"])

    # Zone centroids from precomputed summary table
    centroid_rows = conn.execute(
        "SELECT zone, centroid_lat AS lat, centroid_lon AS lon FROM zone_summary",
    ).fetchall()
    centroids = {r["zone"]: {"lat": r["lat"], "lon": r["lon"]} for r in centroid_rows}

    # Open UNSUBs / unresolved cases per zone
    unsub_rows = conn.execute(
        "SELECT District_Name AS zone, COUNT(*) AS n FROM FIRs "
        "WHERE Accused_Count = 0 OR Accused_ChargeSheeted_Count = 0 "
        "GROUP BY zone",
    ).fetchall()
    unsub_counts = {r["zone"]: r["n"] for r in unsub_rows}

    conn.close()

    zones = set(total_counts) | set(centroids)
    cache: dict[str, dict] = {}
    for zone in zones:
        total = total_counts.get(zone, 0)
        curr  = cur_counts.get(zone, 0)
        prior = prior_counts.get(zone, 0)
        centre = centroids.get(zone, {"lat": None, "lon": None})
        open_unsubs = unsub_counts.get(zone, 0)
        gap_cnt = max(0, open_unsubs // 2)
        unresolved_share = open_unsubs / max(1, total)
        dark_score = round(min(100.0, (unresolved_share * 50.0) + (gap_cnt * 10.0)), 1)
        dark_level = "Critical" if dark_score >= 50 else ("High" if dark_score >= 30 else ("Moderate" if dark_score >= 15 else "Minimal"))

        # Naïve 1-month linear forecast: project the delta forward
        predicted = max(0, curr + (curr - prior))
        cache[zone] = {
            "zone": zone,
            "fir_count": total,
            "this_month": curr,
            "prior_month": prior,
            "top_crimes": crimes_by_zone.get(zone, []),
            "risk_level": _risk_level(curr, prior),
            "trend": _trend_str(curr, prior),
            "predicted": predicted,
            "open_unsubs_count": open_unsubs,
            "gap_count": gap_cnt,
            "dark_score": dark_score,
            "dark_level": dark_level,
            "lat": centre["lat"],
            "lon": centre["lon"],
        }

    _cache = cache
    return cache


def get_all() -> list[dict]:
    """All district aggregates as a list — for choropleth."""
    if _cache is None:
        refresh()
    return list(_cache.values())  # type: ignore[union-attr]


def get_district(zone: str) -> dict | None:
    """Single-district drill-down card — O(1) dict lookup."""
    if _cache is None:
        refresh()
    return _cache.get(zone)  # type: ignore[union-attr]


def dated(zone: str, end_date: date, crime_type: str | None = None) -> dict | None:
    """The district card anchored on a chosen date.

    The startup cache is a picture of today; the Map's calendar asks about another day.
    This counts the day, the 7 and 30 days ending on it and the 30 before that, from the
    same crime rows the map's own date window is drawn from - so the card and the map
    cannot disagree about the same date. Fields it does not recount (open cases, centroid)
    come from the cache and are all-time figures. No forecast is made here: a projection
    from two monthly totals was once shown as "predicted", and it is left out rather than
    re-labelled.
    """
    base = get_district(zone)
    if base is None:
        return None
    from collections import Counter
    from app.services.anomaly import _as_date, _as_of_date
    from app.services.zcql_repo import build_spec
    from app.services.zcql_local import run_query

    anchor = min(end_date, _as_of_date())
    d7, d30, p30 = anchor - timedelta(days=6), anchor - timedelta(days=29), anchor - timedelta(days=59)
    day = last7 = last30 = prior30 = 0
    crimes: Counter = Counter()
    for r in run_query(build_spec("T14", {})):
        if r.get("zone") != zone or (crime_type and r.get("crime_type") != crime_type):
            continue
        d = _as_date(r.get("occurred_at"))
        if not d or d > anchor or d < p30:
            continue
        if d < d30:
            prior30 += 1
            continue
        last30 += 1
        if r.get("crime_type"):
            crimes[r["crime_type"]] += 1
        if d >= d7:
            last7 += 1
        if d == anchor:
            day += 1
    return {
        **base,
        "as_of": anchor.isoformat(),
        "crime_type": crime_type,
        "day_count": day,
        "last_7": last7,
        "last_30": last30,
        "prior_30": prior30,
        "top_crimes": [c for c, _ in crimes.most_common(3)],
        "risk_level": _risk_level(last30, prior30),
        "trend": _trend_str(last30, prior30),
        "predicted": None,
    }
