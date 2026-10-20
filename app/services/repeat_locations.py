"""
Antar — Repeat locations
========================
The places where cases keep being registered: the same spot (about 110 m, three decimal
places of latitude/longitude) with several FIRs on different days in the window. This is
what a commander's review asks for beside the hotspot picture ("which addresses keep
coming back?"), and what a beat officer can be sent to.

A point on the register is not always a place. Three kinds are left out, because sending
a patrol to them would be sending it to a police station or to a typing default:

  * online-crime stations (CEN, Cyber, CID): their FIRs carry the station's own position;
  * a station's default point: the single point holding a large share of everything a
    station has ever registered (where a location was not entered);
  * placeholder coordinates (13.0, 77.0 or 12.123, 75.123).

Read-only. Parameterised SQL; no user text reaches a query.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta
from functools import lru_cache

from app.core.db_path import DB_PATH

_ONLINE = re.compile(r"\b(CEN|CYBER|CID)\b", re.I)
GRID = 3                    # decimal places: ~110 m in latitude
MIN_FIRS, MIN_DAYS = 3, 2   # a repeat: at least 3 FIRs, on at least 2 different days


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _placeholder(lat: float, lon: float) -> bool:
    """13.0, 77.0 / 12.5, 76.5 / 12.123, 75.123: coordinates no one measured."""
    for v in (lat, lon):
        frac = f"{abs(v):.3f}".split(".")[1]
        if frac in ("000", "500", "123") or len(set(frac)) == 1:
            return True
    return f"{abs(lat):.3f}".split(".")[1] == f"{abs(lon):.3f}".split(".")[1]


@lru_cache(maxsize=1)
def station_default_points() -> frozenset:
    """(station, lat, lon) points that are a station's default rather than a place: the
    station's most common point when it holds a fifth or more of all the station's FIRs."""
    con = _connect()
    try:
        rows = con.execute(
            f"SELECT station, ROUND(geo_lat, {GRID}) la, ROUND(geo_lon, {GRID}) lo, COUNT(*) n "
            f"FROM FIRs WHERE geo_lat IS NOT NULL AND station IS NOT NULL GROUP BY 1, 2, 3").fetchall()
    finally:
        con.close()
    tot: dict[str, int] = {}
    top: dict[str, tuple] = {}
    for r in rows:
        tot[r["station"]] = tot.get(r["station"], 0) + r["n"]
        if r["n"] > (top.get(r["station"]) or (0,))[0]:
            top[r["station"]] = (r["n"], r["la"], r["lo"])
    out = set()
    for st, (n, la, lo) in top.items():
        if tot[st] >= 20 and n / tot[st] >= 0.2:
            out.add((st, la, lo))
    return frozenset(out)


def repeat_locations(end: date, days: int = 90, crime_filter: tuple[str, list] | None = None,
                     districts: list[str] | None = None, limit: int = 40) -> dict:
    """The repeat locations in the `days` ending on `end`, most FIRs first."""
    start = end - timedelta(days=days - 1)
    # Online crime has no place: a cyber FIR carries the registering station's position.
    where = ["geo_lat IS NOT NULL", "geo_lon IS NOT NULL", "date >= ?", "date <= ?",
             "UPPER(COALESCE(crime_type, '')) NOT LIKE '%CYBER%'",
             # nor does a missing-person report or a preventive (CrPC) case: both are filed
             # at the station or the complainant's address, not where something happened
             "UPPER(COALESCE(crime_type, '')) NOT LIKE '%MISSING%'",
             "UPPER(TRIM(COALESCE(crime_type, ''))) NOT IN ('CRPC')"]
    args: list = [start.isoformat(), end.isoformat() + " 23:59"]
    if crime_filter:
        sql, cargs = crime_filter
        where.append(sql)
        args += cargs
    if districts:
        where.append(f"UPPER(TRIM(district_norm)) IN ({', '.join('?' * len(districts))})")
        args += [d.strip().upper() for d in districts]
    sql = (f"SELECT ROUND(geo_lat, {GRID}) la, ROUND(geo_lon, {GRID}) lo, COUNT(DISTINCT fir_id) n, "
           f"COUNT(DISTINCT SUBSTR(date, 1, 10)) days, MAX(SUBSTR(date, 1, 10)) last, MIN(SUBSTR(date, 1, 10)) first, "
           f"GROUP_CONCAT(DISTINCT station) stations, MIN(district_norm) district, "
           f"GROUP_CONCAT(crime_type, '|') crimes, GROUP_CONCAT(DISTINCT Beat_Name) beats, "
           f"GROUP_CONCAT(DISTINCT Village_Area_Name) areas "
           f"FROM FIRs WHERE {' AND '.join(where)} GROUP BY 1, 2 "
           f"HAVING COUNT(DISTINCT fir_id) >= ? AND COUNT(DISTINCT SUBSTR(date, 1, 10)) >= ? "
           f"ORDER BY n DESC, days DESC LIMIT 400")
    con = _connect()
    try:
        rows = con.execute(sql, args + [MIN_FIRS, MIN_DAYS]).fetchall()
        # each station's FIRs in the same window, to spot a point that is its own position
        st_tot = {r["station"]: r["n"] for r in con.execute(
            f"SELECT station, COUNT(DISTINCT fir_id) n FROM FIRs WHERE {' AND '.join(where)} GROUP BY station", args)}
    finally:
        con.close()
    defaults = station_default_points()
    out, dropped = [], {"online_station": 0, "station_default": 0, "placeholder": 0}
    for r in rows:
        stations = [s for s in (r["stations"] or "").split(",") if s]
        if stations and all(_ONLINE.search(s) for s in stations):
            dropped["online_station"] += 1
            continue
        # a station's default point: its usual one overall, or one holding a quarter or more
        # of everything the station registered in this window
        if any((s, r["la"], r["lo"]) in defaults for s in stations) or (
                r["n"] >= 15 and len(stations) == 1 and r["n"] >= 0.25 * (st_tot.get(stations[0]) or 1)):
            dropped["station_default"] += 1
            continue
        if _placeholder(r["la"], r["lo"]):
            dropped["placeholder"] += 1
            continue
        crimes: dict[str, int] = {}
        for c in (r["crimes"] or "").split("|"):
            if c:
                crimes[c.strip().upper()] = crimes.get(c.strip().upper(), 0) + 1
        mix = sorted(crimes.items(), key=lambda kv: -kv[1])[:3]
        beats = [b for b in (r["beats"] or "").split(",") if b and b.strip().upper() not in ("OTHER", "OTHERS", "OTHER BEAT")]
        areas = [a for a in (r["areas"] or "").split(",") if a]
        out.append({"lat": r["la"], "lon": r["lo"], "firs": r["n"], "days": r["days"], "first": r["first"],
                    "last": r["last"], "stations": stations[:3], "district": r["district"],
                    "crimes": [{"crime": c, "n": n} for c, n in mix],
                    "beat": beats[0] if beats else None, "area": areas[0] if areas else None})
        if len(out) >= limit:
            break
    return {"locations": out, "window_days": days, "from": start.isoformat(), "to": end.isoformat(),
            "rule": f"{MIN_FIRS}+ FIRs on {MIN_DAYS}+ different days within ~110 m",
            "left_out": dropped}
