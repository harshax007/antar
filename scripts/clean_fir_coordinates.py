"""
Clean FIR coordinates at the source
===================================
Many FIR points are not where the offence happened: some are out at sea or across the
state border, some sit in a different district from the one the FIR is registered in, some
are typed-in placeholders (13.000, 77.000), and many are the police station's own position,
used when no location was entered. Every screen that draws or groups points by place
(heat, hotspots, repeat locations, the Day dots) is misled by them.

This script finds them and clears the coordinates of those rows at the source, so
`geo_lat` / `geo_lon` (generated from Latitude / Longitude, or lat_r / lon_r) become NULL and
every consumer treats the FIR as "no usable position" - the same as the 56% of FIRs that never
had one. Nothing is moved or invented.

Reversible: the original values and the reason are kept in `fir_geo_original`
(fir rowid, Latitude, Longitude, lat_r, lon_r, reason, cleaned_at). `--revert` puts them back.

    python scripts/clean_fir_coordinates.py              # dry run: counts only, changes nothing
    python scripts/clean_fir_coordinates.py --apply      # clear the bad points (keeps originals)
    python scripts/clean_fir_coordinates.py --revert     # restore every original value

Rules, in order (a row gets the first reason that applies):
  outside_state     the point is not on land inside Karnataka (any district polygon)
  wrong_district    inside Karnataka but more than ~5 km outside its own police district
                    (cross-border jurisdictions included: JURISDICTION_EXTRA)
  placeholder       round or repeated digits (x.000, x.500, x.123, lat frac == lon frac)
  station_default   the single point holding a fifth or more of a station's FIRs (20+ FIRs):
                    the station's own position, not a place of offence

Statewide units (CID, Railways, Coastal Security, ISD ...) have no district, so for them only
outside_state and placeholder apply.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.db_path import DB_PATH  # noqa: E402

GEOJSON = ROOT / "antar-frontend" / "public" / "karnataka_new.geojson"
KARNATAKA_JS = ROOT / "antar-frontend" / "lib" / "karnataka.js"
NEAR_DEG = 0.045         # ~5 km: a point this close to its own district's edge is accepted

# Police districts whose jurisdiction crosses revenue-district (map) borders: a point in any of
# these map districts is in the police district. Bengaluru District police cover Anekal and
# Sarjapura (Bengaluru Urban on the map); the City commissionerate reaches into Bengaluru Rural;
# Vijayanagara took Harapanahalli from Davanagere, which these map shapes predate; Ramanagara
# (Bengaluru South) borders both Bengaluru districts.
JURISDICTION_EXTRA = {
    "Bengaluru Dist": ["Bengaluru Urban", "Ramanagara"],
    "Bengaluru City": ["Bengaluru Rural"],
    "Vijayanagara": ["Davanagere"],
    "Ramanagara": ["Bengaluru Urban", "Bengaluru Rural"],
    "Chickballapura": ["Bengaluru Rural"],
}


def zone_to_gadm() -> dict[str, str]:
    """The police district -> map district table the frontend uses (one source of truth)."""
    js = KARNATAKA_JS.read_text(encoding="utf-8")
    block = js[js.index("export const ZONE_TO_GADM_DISTRICT"):]
    block = block[block.index("{") + 1: block.index("};")]
    return {k: v for k, v in re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', block)}


def load_shapes() -> dict[str, list[np.ndarray]]:
    g = json.loads(GEOJSON.read_text(encoding="utf-8"))
    shapes: dict[str, list[np.ndarray]] = {}
    for f in g["features"]:
        name = f["properties"].get("district") or f["properties"].get("NAME_2")
        geo = f["geometry"]
        polys = [geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]
        for poly in polys:
            shapes.setdefault(name, []).append(np.asarray(poly[0], dtype=float))   # outer ring [lon, lat]
    return shapes


def inside(rings: list[np.ndarray], lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Vectorised ray casting: which points fall inside any of the rings."""
    out = np.zeros(lon.shape, dtype=bool)
    for r in rings:
        x0, y0 = r[:, 0], r[:, 1]
        x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
        minx, maxx, miny, maxy = x0.min(), x0.max(), y0.min(), y0.max()
        cand = (lon >= minx) & (lon <= maxx) & (lat >= miny) & (lat <= maxy) & ~out
        if not cand.any():
            continue
        px, py = lon[cand][:, None], lat[cand][:, None]
        crosses = ((y0 > py) != (y1 > py)) & (px < (x1 - x0) * (py - y0) / np.where(y1 - y0 == 0, 1e-12, y1 - y0) + x0)
        out[np.flatnonzero(cand)] = (crosses.sum(axis=1) % 2) == 1
    return out


def placeholder(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    def frac(v):
        return np.char.zfill(np.round((np.abs(v) % 1) * 1000).astype(int).astype(str), 3)
    fl, fo = frac(lat), frac(lon)
    bad = np.zeros(lat.shape, dtype=bool)
    for f in (fl, fo):
        bad |= np.isin(f, ["000", "500", "123"])
        bad |= np.array([len(set(s)) == 1 for s in f])
    return bad | (fl == fo)


def find(con: sqlite3.Connection) -> list[tuple[int, str]]:
    rows = con.execute("SELECT rowid, geo_lat, geo_lon, district_norm, station FROM FIRs WHERE geo_ok").fetchall()
    rid = np.array([r[0] for r in rows])
    lat = np.array([r[1] for r in rows], dtype=float)
    lon = np.array([r[2] for r in rows], dtype=float)
    dist = np.array([r[3] or "" for r in rows], dtype=object)
    stn = np.array([r[4] or "" for r in rows], dtype=object)
    reason = np.full(len(rows), "", dtype=object)

    shapes = load_shapes()
    z2g = zone_to_gadm()
    all_rings = [r for rings in shapes.values() for r in rings]

    # 1. on land inside Karnataka
    in_state = inside(all_rings, lon, lat)
    reason[~in_state] = "outside_state"

    # 2. inside its own district (or within ~3 km of it)
    for d in np.unique(dist):
        g = z2g.get(d, d)
        if g not in shapes:
            continue                      # a statewide unit: no district to be in
        m = (dist == d) & (reason == "")
        if not m.any():
            continue
        rings = [r for name in [g] + JURISDICTION_EXTRA.get(d, []) for r in shapes.get(name, [])]
        ok = inside(rings, lon[m], lat[m])
        if (~ok).any():
            tree = cKDTree(np.vstack(rings))
            idx = np.flatnonzero(m)[~ok]
            near, _ = tree.query(np.c_[lon[idx], lat[idx]], distance_upper_bound=NEAR_DEG)
            reason[idx[np.isinf(near)]] = "wrong_district"

    # 3. typed-in placeholders
    reason[(reason == "") & placeholder(lat, lon)] = "placeholder"

    # 4. a station's own default point
    key = np.char.add(np.char.add(np.round(lat, 3).astype(str), ","), np.round(lon, 3).astype(str))
    for s in np.unique(stn):
        if not s:
            continue
        m = stn == s
        if m.sum() < 20:
            continue
        vals, counts = np.unique(key[m], return_counts=True)
        top = counts.argmax()
        if counts[top] / m.sum() >= 0.2:
            hit = m & (key == vals[top]) & (reason == "")
            reason[hit] = "station_default"

    return [(int(r), str(x)) for r, x in zip(rid, reason) if x]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--revert", action="store_true")
    a = ap.parse_args()

    con = sqlite3.connect(DB_PATH, timeout=60)
    con.execute("CREATE TABLE IF NOT EXISTS fir_geo_original (fir_rowid INTEGER PRIMARY KEY, Latitude, Longitude, "
                "lat_r, lon_r, reason TEXT, cleaned_at TEXT)")

    if a.revert:
        n = con.execute("SELECT COUNT(*) FROM fir_geo_original").fetchone()[0]
        with con:
            con.execute("UPDATE FIRs SET Latitude = o.Latitude, Longitude = o.Longitude, lat_r = o.lat_r, lon_r = o.lon_r "
                        "FROM fir_geo_original o WHERE FIRs.rowid = o.fir_rowid")
            con.execute("DELETE FROM fir_geo_original")
        print(f"restored {n} FIR coordinates")
        return

    total_geo = con.execute("SELECT COUNT(*) FROM FIRs WHERE geo_ok").fetchone()[0]
    found = find(con)
    by: dict[str, int] = {}
    for _, r in found:
        by[r] = by.get(r, 0) + 1
    print(f"FIRs with a point: {total_geo:,}")
    for r in ("outside_state", "wrong_district", "placeholder", "station_default"):
        print(f"  {r:16s} {by.get(r, 0):>8,}  ({100 * by.get(r, 0) / max(total_geo, 1):.1f}%)")
    print(f"  {'kept':16s} {total_geo - len(found):>8,}")
    if not a.apply:
        print("dry run: nothing changed (use --apply)")
        return

    now = datetime.now(timezone.utc).isoformat()
    with con:
        con.executemany(
            "INSERT OR IGNORE INTO fir_geo_original (fir_rowid, Latitude, Longitude, lat_r, lon_r, reason, cleaned_at) "
            "SELECT rowid, Latitude, Longitude, lat_r, lon_r, ?, ? FROM FIRs WHERE rowid = ?",
            [(r, now, rid) for rid, r in found])
        con.executemany("UPDATE FIRs SET Latitude = NULL, Longitude = NULL, lat_r = NULL, lon_r = NULL WHERE rowid = ?",
                        [(rid,) for rid, _ in found])
    left = con.execute("SELECT COUNT(*) FROM FIRs WHERE geo_ok").fetchone()[0]
    print(f"cleared {len(found):,} points; {left:,} FIRs keep a usable point. Originals in fir_geo_original.")


if __name__ == "__main__":
    main()
