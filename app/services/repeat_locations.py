"""
Antar — Repeat locations
========================
The places where cases keep being registered: the same spot (within about 100 m) with
several FIRs on different days in the window. This is what a commander's review asks for
beside the hotspot picture ("which addresses keep coming back?"), and what a beat officer
can be sent to.

How a spot is found. Each FIR is put in its H3 hexagon (resolution 10: ~76 m edge,
~15,000 m2 - about the size of the old three-decimal cell). The busiest hexagon is taken
first and claims every FIR within SPOT_M of its centre, including the ones just across its
edge in a neighbouring hexagon; then the next busiest, and so on. Rounding to three decimal
places used to split two FIRs five metres apart across a rounding line into two cells, so a
real repeat could fall under the threshold; claiming across the edge removes that. A
location's point is the coordinate recorded most often inside it - a real recorded point,
so placeholder and station-default checks see what the register holds.

A point on the register is not always a place. Three kinds are left out, because sending
a patrol to them would be sending it to a police station or to a typing default:

  * online-crime stations (CEN, Cyber, CID): their FIRs carry the station's own position;
  * a station's default point: the single point holding a large share of everything a
    station has ever registered (where a location was not entered);
  * placeholder coordinates (13.0, 77.0 or 12.123, 75.123);
  * a unit's own position: rows filed under a unit code ("BLR-YPR-02", "SCRB-HQ") with no
    area, and the generic "<City> Central PS / City Beat 1" point the demonstration rows
    are placed on. Neither names a place a patrol could go to.

Read-only. Parameterised SQL; no user text reaches a query.
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from datetime import date, timedelta
from functools import lru_cache

import h3

from app.core.db_path import DB_PATH

_ONLINE = re.compile(r"\b(CEN|CYBER|CID)\b", re.I)
_UNIT_CODE = re.compile(r"^[A-Z0-9]+(-[A-Z0-9]+)+$")     # BLR-YPR-02, KLB-01, SCRB-HQ
ACTIVE_DAYS = 14            # a repeat location is "active" when its last FIR is this recent
GRID = 3                    # decimal places: how a station's default point is recognised
H3_RES = 10                 # ~76 m hexagon edge, ~15,000 m2
SPOT_M = 100                # a spot: FIRs within this many metres of its hexagon's centre
MIN_FIRS, MIN_DAYS = 3, 2   # a repeat: at least 3 FIRs, on at least 2 different days


def _metres(a: tuple, b: tuple) -> float:
    """Great-circle distance; at 100 m the flat-earth error is far below a GPS fix."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12_742_000 * math.asin(math.sqrt(x))


# columns of a FIR row as fetched for spotting (plain tuples: sqlite3.Row on 50k+ rows was
# a third of the run)
ID, LAT, LON, DAY, STATION, DISTRICT, CRIME, BEAT, AREA = range(9)


def _spots(rows: list) -> list[list]:
    """Group FIR rows into spots: busiest hexagon first, each claiming the unclaimed rows
    within SPOT_M of its centre from itself and its six neighbours."""
    by_cell: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        by_cell.setdefault(h3.latlng_to_cell(r[LAT], r[LON], H3_RES), []).append(i)
    order = sorted(by_cell, key=lambda c: (-len({rows[i][ID] for i in by_cell[c]}), c))
    claimed: set[int] = set()
    spots = []
    for cell in order:
        if all(i in claimed for i in by_cell[cell]):
            continue
        centre = h3.cell_to_latlng(cell)
        members = []
        for c in h3.grid_disk(cell, 1):
            for i in by_cell.get(c, ()):
                if i not in claimed and (c == cell or _metres(centre, (rows[i][LAT], rows[i][LON])) <= SPOT_M):
                    members.append(i)
        claimed.update(members)
        if members:
            spots.append([rows[i] for i in members])
    return spots


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
    sql = (f"SELECT fir_id, geo_lat, geo_lon, SUBSTR(date, 1, 10) day, station, district_norm, crime_type, "
           f"Beat_Name, Village_Area_Name FROM FIRs WHERE {' AND '.join(where)}")
    con = _connect()
    try:
        cur = con.cursor()
        cur.row_factory = None
        fir_rows = cur.execute(sql, args).fetchall()
        # each station's FIRs in the same window, to spot a point that is its own position
        st_tot = {r["station"]: r["n"] for r in con.execute(
            f"SELECT station, COUNT(DISTINCT fir_id) n FROM FIRs WHERE {' AND '.join(where)} GROUP BY station", args)}
    finally:
        con.close()
    defaults = station_default_points()
    # Count every spot cheaply; the detail is built only for the ones read out below.
    cands = []
    for spot in _spots(fir_rows):
        firs = {m[ID]: m for m in spot}                           # one row per FIR
        days_seen = {m[DAY] for m in firs.values()}
        if len(firs) >= MIN_FIRS and len(days_seen) >= MIN_DAYS:
            cands.append((len(firs), len(days_seen), firs, days_seen))
    cands.sort(key=lambda c: (-c[0], -c[1]))

    def detail(n, nd, firs, days_seen):
        ms = list(firs.values())
        top = lambda col: ",".join(k for k, _ in Counter(m[col] for m in ms if m[col]).most_common())
        point = Counter((round(m[LAT], 5), round(m[LON], 5)) for m in ms).most_common(1)[0][0]
        return {"la": point[0], "lo": point[1], "n": n, "days": nd, "last": max(days_seen), "first": min(days_seen),
                # most frequent first, so the label is what most of the spot's FIRs say
                "stations": top(STATION), "beats": top(BEAT), "areas": top(AREA),
                "district": min((m[DISTRICT] for m in ms if m[DISTRICT]), default=None),
                "crimes": "|".join(m[CRIME] or "" for m in ms),
                # every recorded point in the spot, at the precision station defaults are kept in
                "points": {(round(m[LAT], GRID), round(m[LON], GRID)) for m in ms}}

    rows = (detail(*c) for c in cands)
    out, dropped = [], {"online_station": 0, "station_default": 0, "placeholder": 0, "unit_position": 0}
    for r in rows:
        stations = [s for s in (r["stations"] or "").split(",") if s]
        if stations and all(_ONLINE.search(s) for s in stations):
            dropped["online_station"] += 1
            continue
        # a station's default point: its usual one overall, or one holding a quarter or more
        # of everything the station registered in this window
        if any((s, la, lo) in defaults for s in stations for la, lo in r["points"]) or (
                r["n"] >= 15 and len(stations) == 1 and r["n"] >= 0.25 * (st_tot.get(stations[0]) or 1)):
            dropped["station_default"] += 1
            continue
        if _placeholder(r["la"], r["lo"]):
            dropped["placeholder"] += 1
            continue
        beats_raw = [b.strip().upper() for b in (r["beats"] or "").split(",") if b.strip()]
        if (stations and all(_UNIT_CODE.match(s.strip()) for s in stations) and not r["areas"]) or (
                beats_raw and all(b in ("BEAT 1", "CITY BEAT 1") for b in beats_raw)
                and all(s.strip().upper().endswith("CENTRAL PS") for s in stations)):
            dropped["unit_position"] += 1
            continue
        crimes: dict[str, int] = {}
        for c in (r["crimes"] or "").split("|"):
            if c:
                k = c.strip().upper().replace("_", " ")
                crimes[k] = crimes.get(k, 0) + 1
        mix = sorted(crimes.items(), key=lambda kv: -kv[1])[:3]
        beats = [b for b in (r["beats"] or "").split(",") if b and b.strip().upper() not in ("OTHER", "OTHERS", "OTHER BEAT")]
        areas = [a for a in (r["areas"] or "").split(",") if a]
        since = (end - date.fromisoformat(r["last"])).days if r["last"] else None
        out.append({"lat": r["la"], "lon": r["lo"], "firs": r["n"], "days": r["days"], "first": r["first"],
                    "last": r["last"], "days_since_last": since,
                    "active": since is not None and since < ACTIVE_DAYS,
                    "stations": stations[:3], "district": r["district"],
                    "crimes": [{"crime": c, "n": n} for c, n in mix],
                    "beat": beats[0] if beats else None, "area": areas[0] if areas else None})
        if len(out) >= limit:
            break
    return {"locations": out, "window_days": days, "from": start.isoformat(), "to": end.isoformat(),
            "rule": f"{MIN_FIRS}+ FIRs on {MIN_DAYS}+ different days within ~{SPOT_M} m",
            "active_days": ACTIVE_DAYS,
            "left_out": dropped}
