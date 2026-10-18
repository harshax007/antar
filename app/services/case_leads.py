"""
Antar - case leads
==================
Crime intelligence applied to cases, not only to places. Three kinds of lead for a district,
each counted from the record and each shown with what would make it weaker:

  shared_keys    FIRs that carry the same vehicle number, UPI id or IP address. The key is
                 named. A key on two or three FIRs is specific; one on thirty is more
                 likely a common value or a data artefact than a link, and is marked so.
  cross_border   accused named in FIRs in this district and in another (the same count the
                 Map's "Links between districts" uses).
  near_repeat    after a burglary, is another one nearby within days more common than
                 chance? MEASURED here on the real record (a Knox test with a permutation
                 check), not assumed from the literature. The lead is offered only when
                 the district's own record shows it.

No language model is involved. A lead is Derived or Inferred, never a finding: it tells an
investigating officer where to look, and the page says what would settle it.
"""
from __future__ import annotations

import math
import random
import sqlite3
import time
from collections import defaultdict

KEYS = (("Vehicle_Reg_No", "vehicle"), ("UPI_ID", "UPI id"), ("IP_Address", "IP address"))
SPECIFIC_MAX = 5              # a key on more FIRs than this is marked weak
_cache: dict = {}
_TTL = 600


def _cached(key, fn):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    val = fn()
    _cache[key] = (time.time(), val)
    return val


# ── 1. shared hard keys ──────────────────────────────────────────────────────

def _keyed_rows(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.execute(
        "SELECT fir_id, CrimeNo, District_Name, station, date, CrimeHead_Name, FIR_Stage, "
        "Vehicle_Reg_No, UPI_ID, IP_Address, is_synthetic_row, has_synthetic_link FROM FIRs "
        "WHERE COALESCE(Vehicle_Reg_No,'') <> '' OR COALESCE(UPI_ID,'') <> '' OR COALESCE(IP_Address,'') <> ''")
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def shared_keys(conn: sqlite3.Connection, zone: str, limit: int = 6) -> dict:
    rows = _cached("keyed", lambda: _keyed_rows(conn))
    by: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        for col, label in KEYS:
            v = (r.get(col) or "").strip()
            if v:
                by[(label, v)].append(r)
    z = zone.strip().upper()
    leads = []
    for (label, value), firs in by.items():
        if len(firs) < 2 or not any((f["District_Name"] or "").strip().upper() == z for f in firs):
            continue
        districts = sorted({f["District_Name"] for f in firs if f["District_Name"]})
        firs_sorted = sorted(firs, key=lambda f: str(f["date"]), reverse=True)
        leads.append({
            "key_type": label, "key": value, "firs": len(firs), "districts": districts,
            "specific": len(firs) <= SPECIFIC_MAX,
            "open": sum(1 for f in firs if str(f["FIR_Stage"] or "").lower() == "under investigation"),
            "seeded": any(f.get("is_synthetic_row") or f.get("has_synthetic_link") for f in firs),
            "examples": [{"fir": f["CrimeNo"] or f["fir_id"], "district": f["District_Name"], "station": f["station"],
                          "date": str(f["date"])[:10], "crime": (f["CrimeHead_Name"] or "").strip()}
                         for f in firs_sorted[:4]],
            "evidence_class": "D",
            "would_settle": f"Confirm the {label} on each FIR's seizure memo or statement; a shared {label} can be a "
                            "borrowed, resold or mistyped one.",
        })
    leads.sort(key=lambda d: (not d["specific"], d["firs"], d["key"]))
    total = len(leads)
    return {"total": total, "specific": sum(1 for d in leads if d["specific"]), "leads": leads[:limit],
            "note": (f"A detail on {SPECIFIC_MAX} FIRs or fewer points to a real link. One on many FIRs is more "
                     "likely a common value or a data-entry error than a link.")}


# ── 2. accused named across a district border ────────────────────────────────

def cross_border(zone: str, limit: int = 6) -> dict:
    try:
        from app.services import evidence_ledger
        corr = evidence_ledger.corridors(limit=200)
    except Exception:
        return {"total": 0, "links": [], "note": "The links between districts could not be read."}
    z = zone.strip().upper()
    links = []
    for c in corr:
        if z not in (str(c["src"]).upper(), str(c["dst"]).upper()):
            continue
        other = c["dst"] if str(c["src"]).upper() == z else c["src"]
        links.append({"with": other, "accused": c["linking_accused"], "firs": c["fir_count"],
                      "accused_ids": list(c["accused_ids"])[:5],
                      "evidence_class": "D",
                      "would_settle": f"Ask {other} for the case diaries; being named in both is a connection in "
                                      "the record, not proof of travel or of acting together."})
    links.sort(key=lambda d: (-d["accused"], -d["firs"], d["with"]))
    return {"total": len(links), "links": links[:limit]}


# ── 3. near repeat, measured ─────────────────────────────────────────────────

def knox(points: list[tuple[float, float, int]], km: float = 0.5, days: int = 14, perms: int = 199,
         seed: int = 7) -> dict:
    """Knox test for space-time clustering.

    `points` are (lat, lon, day number). Counts the pairs that are close in BOTH space
    (within `km`) and time (within `days`), and compares that with the same count after
    the dates are shuffled among the same places `perms` times. The ratio is observed over
    the shuffled mean; p is the share of shuffles that did at least as well. Shuffling
    keeps where burglaries happen and when they happen, and breaks only the link between
    the two - which is the thing being tested.

    Pairs at the SAME recorded point are left out of the test. In the register many FIRs
    share a point and a date - several FIRs for one incident, or a location recorded at
    the station - and counting those as "another burglary nearby" turned a ratio of about
    3 into one of about 13 in Belagavi. They are reported separately.
    """
    n = len(points)
    if n < 2:
        return {"n": n, "pairs_near_in_space": 0, "observed": 0, "expected": 0.0, "ratio": None, "p": None}
    # bucket by a grid of about `km` so only neighbouring cells are compared
    lat0 = sum(p[0] for p in points) / n
    kx, ky = 111.32 * math.cos(math.radians(lat0)), 110.57
    cell = defaultdict(list)
    xy = []
    for i, (la, lo, _d) in enumerate(points):
        x, y = lo * kx, la * ky
        xy.append((x, y))
        cell[(int(x // km), int(y // km))].append(i)
    near: list[tuple[int, int]] = []
    same: list[tuple[int, int]] = []
    for (cx, cy), idx in cell.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                other = cell.get((cx + dx, cy + dy))
                if not other:
                    continue
                for i in idx:
                    xi, yi = xy[i]
                    for j in other:
                        if j <= i:
                            continue
                        d2 = (xi - xy[j][0]) ** 2 + (yi - xy[j][1]) ** 2
                        if d2 <= _SAME_POINT:
                            same.append((i, j))          # the same recorded point: not "near", counted apart
                        elif d2 <= km * km:
                            near.append((i, j))
    day = [p[2] for p in points]
    count = lambda d: sum(1 for i, j in near if abs(d[i] - d[j]) <= days)   # noqa: E731
    observed = count(day)
    rng = random.Random(seed)
    sims = []
    shuffled = list(day)
    for _ in range(perms):
        rng.shuffle(shuffled)
        sims.append(count(shuffled))
    expected = sum(sims) / len(sims) if sims else 0.0
    p = (1 + sum(1 for s in sims if s >= observed)) / (len(sims) + 1) if sims else None
    return {"n": n, "pairs_near_in_space": len(near), "observed": observed, "expected": round(expected, 2),
            "ratio": round(observed / expected, 2) if expected > 0 else None, "p": round(p, 4) if p is not None else None,
            "same_point_same_day": sum(1 for i, j in same if day[i] == day[j])}


_SAME_POINT = 1e-8            # km squared: about 10 cm; the register's coordinates repeat exactly
MIN_POINTS = 150
MAX_POINTS = 3000


def near_repeat(conn: sqlite3.Connection, zone: str, *, km: float = 0.5, days: int = 14) -> dict:
    """Does this district's own record show burglaries clustering in space and time?"""
    def measure():
        rows = conn.execute(
            "SELECT Latitude, Longitude, date FROM FIRs WHERE District_Name = ? "
            "AND CrimeGroup_Name LIKE 'BURGLARY%' AND is_synthetic_row = 0 "
            "AND Latitude IS NOT NULL AND Longitude IS NOT NULL AND Latitude <> 0 AND Longitude <> 0 "
            "ORDER BY date DESC LIMIT ?", (zone, MAX_POINTS)).fetchall()
        from datetime import date as _date
        pts = []
        for la, lo, d in rows:
            try:
                pts.append((float(la), float(lo), _date.fromisoformat(str(d)[:10]).toordinal()))
            except (TypeError, ValueError):
                continue
        base = {"zone": zone, "km": km, "days": days, "crime": "burglary", "located_firs": len(pts),
                "distinct_points": len({(round(p[0], 5), round(p[1], 5)) for p in pts}),
                "basis": "the real register only; seeded rows are left out"}
        if len(pts) < MIN_POINTS:
            return {**base, "supported": False, "tested": False,
                    "text": f"Too few located burglaries in the real record here ({len(pts)}) to test for near repeats."}
        k = knox(pts, km=km, days=days)
        # offered as a lead only when the district's own record shows it clearly: at least
        # 20 such pairs, 20% above chance, and fewer than 1 shuffle in 20 doing as well
        supported = bool(k["observed"] >= 20 and k["ratio"] and k["ratio"] >= 1.2
                         and k["p"] is not None and k["p"] < 0.05)
        metres = int(km * 1000)
        text = (f"After a burglary here, another at a different point within {metres} m in the following {days} days was "
                f"{k['ratio']:g} times as common as chance would give ({k['observed']} such pairs against "
                f"{k['expected']:g} expected; {len(pts):,} located burglaries)."
                if supported else
                f"The record does not show burglaries here clustering in space and time: {k['observed']} pairs at different points within "
                f"{metres} m and {days} days against {k['expected']:g} expected by chance"
                + (f" (ratio {k['ratio']:g})" if k["ratio"] else "") + f"; {len(pts):,} located burglaries.")
        return {**base, **k, "supported": supported, "tested": True, "text": text,
                "caution": (f"Locations are recorded at {base['distinct_points']:,} distinct points for {len(pts):,} FIRs. "
                            f"{k['same_point_same_day']:,} pairs share a point and a date (likely one incident with several "
                            "FIRs) and are left out of the test.")}
    return _cached(("near_repeat", zone.upper(), km, days), measure)


def recent_burglaries(conn: sqlite3.Connection, zone: str, as_of: str, days: int = 14, limit: int = 6) -> list[dict]:
    """Burglaries registered in the last `days` up to `as_of`: where a near-repeat watch applies."""
    from datetime import date as _date, timedelta
    end = _date.fromisoformat(as_of[:10])
    rows = conn.execute(
        "SELECT CrimeNo, fir_id, station, Beat_Name, date, CrimeHead_Name FROM FIRs WHERE District_Name = ? "
        "AND CrimeGroup_Name LIKE 'BURGLARY%' AND date BETWEEN ? AND ? ORDER BY date DESC LIMIT ?",
        (zone, (end - timedelta(days=days)).isoformat(), end.isoformat(), limit)).fetchall()
    return [{"fir": r[0] or r[1], "station": r[2], "beat": (r[3] or "").strip() or "not recorded",
             "date": str(r[4])[:10], "crime": (r[5] or "").strip()} for r in rows]


def build(conn: sqlite3.Connection, zone: str, as_of: str | None = None) -> dict:
    zone = " ".join(str(zone or "").split())[:80]
    if not zone:
        return {"zone": "", "shared_keys": {"total": 0, "leads": []}, "cross_border": {"total": 0, "links": []},
                "near_repeat": None}
    from datetime import date as _date
    as_of = as_of or _date.today().isoformat()
    nr = near_repeat(conn, zone)
    out = {"zone": zone, "shared_keys": shared_keys(conn, zone), "cross_border": cross_border(zone),
           "near_repeat": dict(nr), "evidence_class": "D",
           "method": "counted from the FIR register; no language model"}
    if nr.get("supported"):
        out["near_repeat"]["watch"] = recent_burglaries(conn, zone, as_of, days=nr["days"])
    return out
