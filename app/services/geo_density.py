"""
Antar — Geo-Density Service
================================
Math/heuristic logic for the Geo-Intelligence layer.
Uses ponytail simplicity: raw coordinates for Leaflet.heat, sequential linking for flow,
and basic density-window prediction for hotspots.
"""

from collections import defaultdict
import numpy as np
from datetime import datetime

def compute_heat(rows: list[dict]) -> list[dict]:
    """
    Returns raw points for frontend Leaflet.heat rendering.
    Bins identical coordinates to reduce payload size.
    """
    binned = defaultdict(int)
    for r in rows:
        lat_v, lon_v = r.get("lat"), r.get("lon")
        try:
            lat = float(lat_v) if lat_v else None
            lon = float(lon_v) if lon_v else None
        except (ValueError, TypeError):
            lat = lon = None
            
        if lat is not None and lon is not None:
            # truncate to ~11m resolution to bin nearby incidents
            key = (round(lat, 4), round(lon, 4))
            binned[key] += 1
            
    return [{"lat": k[0], "lon": k[1], "weight": v} for k, v in binned.items()]


def compute_flow(rows: list[dict], crime_suspects: list[dict] = None) -> list[dict]:
    """
    Given a list of crime rows (with lat, lon, occurred_at, crime_id), and optional mapping
    of crime_id -> suspect_id, builds flow paths for suspects with >= 2 incidents.
    """
    if not crime_suspects:
        return []
        
    # Map crime_id -> list of suspect_ids
    c2s = defaultdict(list)
    for cs in crime_suspects:
        c2s[cs["crime_id"]].append(cs["suspect_id"])

    # Group crimes by suspect_id
    suspect_crimes = defaultdict(list)
    for r in rows:
        lat_v, lon_v, dt, cid = r.get("lat"), r.get("lon"), r.get("occurred_at"), r.get("crime_id")
        try:
            lat = float(lat_v) if lat_v else None
            lon = float(lon_v) if lon_v else None
        except (ValueError, TypeError):
            lat = lon = None
            
        if lat is not None and lon is not None and dt and cid:
            for sid in c2s.get(cid, []):
                suspect_crimes[sid].append({"lat": lat, "lon": lon, "date": dt})
                
    flow = []
    for sid, crimes in suspect_crimes.items():
        if len(crimes) >= 2:
            # Sort chronologically to form a path
            crimes.sort(key=lambda x: x["date"])
            flow.append({
                "suspect_id": sid,
                "path": [{"lat": c["lat"], "lon": c["lon"]} for c in crimes]
            })
            
    return flow


def predict_hotspots(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Returns (predicted_points, beat_suggestions).
    A 'ponytail' heuristic: identifies the single most dense zone in the past 14 days,
    and returns its centroid as the predicted hotspot, with a concrete patrol suggestion.
    """
    if not rows:
        return [], []
        
    zone_counts = defaultdict(int)
    zone_coords = defaultdict(lambda: {"lat": 0.0, "lon": 0.0, "n": 0})
    
    # Sort descending by date to find newest
    rows = sorted(rows, key=lambda x: x.get("occurred_at", ""), reverse=True)
    if not rows:
        return [], []
        
    # We don't have absolute 'today', so we use the most recent crime in the dataset as 'today'
    latest_date_str = rows[0].get("occurred_at", "")[:10]
    
    for r in rows:
        lat_v, lon_v, z = r.get("lat"), r.get("lon"), r.get("zone")
        try:
            lat = float(lat_v) if lat_v else None
            lon = float(lon_v) if lon_v else None
        except (ValueError, TypeError):
            lat = lon = None
            
        if z and lat is not None and lon is not None:
            # Rough 30 day window relative to latest
            if r.get("occurred_at", "") >= latest_date_str[:7]: # same month roughly
                zone_counts[z] += 1
                zc = zone_coords[z]
                zc["lat"] += lat
                zc["lon"] += lon
                zc["n"] += 1
                
    if not zone_counts:
        return [], []

    top_zone = max(zone_counts.items(), key=lambda x: x[1])[0]
    zc = zone_coords[top_zone]
    centroid = {"lat": round(zc["lat"] / zc["n"], 4), "lon": round(zc["lon"] / zc["n"], 4)}

    predicted = [{"lat": centroid["lat"], "lon": centroid["lon"], "zone": top_zone, "risk": "High"}]
    suggestions = [{
        "zone": top_zone,
        "suggestion": f"Recent spike ({zone_counts[top_zone]} cases). Saturate patrols in {top_zone}.",
    }]

    return predicted, suggestions


def compute_kde_geojson(rows: list[dict]) -> dict:
    """
    Computes 2D Gaussian KDE over coordinates.
    Returns a GeoJSON FeatureCollection of density contour polygons.
    """
    coords = []
    for r in rows:
        lat_v, lon_v = r.get("lat"), r.get("lon")
        try:
            if lat_v and lon_v:
                coords.append((float(lon_v), float(lat_v), r))
        except (ValueError, TypeError):
            continue
            
    if len(coords) < 5:
        # Not enough points for KDE; return empty FeatureCollection
        return {"type": "FeatureCollection", "features": []}
        
    data = np.array([(c[0], c[1]) for c in coords]).T  # shape (2, N) - lons, lats
    lons = data[0]
    lats = data[1]
    
    # Grid limits
    min_lon, max_lon = lons.min() - 0.01, lons.max() + 0.01
    min_lat, max_lat = lats.min() - 0.01, lats.max() + 0.01
    
    # 15x15 Grid
    grid_size = 15
    lon_grid = np.linspace(min_lon, max_lon, grid_size)
    lat_grid = np.linspace(min_lat, max_lat, grid_size)
    
    d_lon = lon_grid[1] - lon_grid[0]
    d_lat = lat_grid[1] - lat_grid[0]
    
    # Evaluate KDE using simple numpy broadcasting (no scipy)
    try:
        # Meshgrid coordinates for grid centers
        lon_centers = lon_grid[:-1] + d_lon/2
        lat_centers = lat_grid[:-1] + d_lat/2
        
        grid_coords = []
        for lat in lat_centers:
            for lon in lon_centers:
                grid_coords.append((lon, lat))
                
        eval_points = np.array(grid_coords).T
        
        # Simple KDE implementation
        bw = 0.05 # bandwidth
        densities = []
        for gx, gy in zip(eval_points[0], eval_points[1]):
            # distance squared
            d2 = ((data[0] - gx)**2 + (data[1] - gy)**2) / (bw**2)
            densities.append(np.sum(np.exp(-0.5 * d2)))
        densities = np.array(densities)
        
        # Percentiles
        p50 = np.percentile(densities, 50)
        p80 = np.percentile(densities, 80)
        
        features = []
        idx = 0
        for lat in lat_centers:
            for lon in lon_centers:
                d = densities[idx]
                idx += 1
                if d < p50:
                    continue
                    
                risk = "High" if d >= p80 else "Medium"
                color = "#ef4444" if risk == "High" else "#f97316"
                
                # Grid cell corners
                x1, x2 = lon - d_lon/2, lon + d_lon/2
                y1, y2 = lat - d_lat/2, lat + d_lat/2
                
                # Categorize temporal drift for crimes inside this cell
                cell_crimes = []
                for cx, cy, orig_r in coords:
                    if x1 <= cx <= x2 and y1 <= cy <= y2:
                        cell_crimes.append(orig_r)
                
                time_of_day_counts = defaultdict(int)
                day_of_week_counts = defaultdict(int)
                
                for cr in cell_crimes:
                    dt_str = cr.get("occurred_at", "")
                    if dt_str:
                        # parse time
                        try:
                            # Parse hour from e.g. "2026-05-09 14:30:00" or ISO format
                            if "T" in dt_str:
                                time_part = dt_str.split("T")[1]
                            elif " " in dt_str:
                                time_part = dt_str.split(" ")[1]
                            else:
                                time_part = ""
                            
                            if time_part:
                                hour = int(time_part.split(":")[0])
                                if 6 <= hour < 12:
                                    time_of_day_counts["Morning"] += 1
                                elif 12 <= hour < 18:
                                    time_of_day_counts["Afternoon"] += 1
                                elif 18 <= hour < 24:
                                    time_of_day_counts["Evening"] += 1
                                else:
                                    time_of_day_counts["Night"] += 1
                            
                            # parse day of week
                            date_part = dt_str.split("T")[0].split(" ")[0]
                            dt_obj = datetime.fromisoformat(date_part)
                            # 5, 6 is Saturday, Sunday
                            if dt_obj.weekday() >= 5:
                                day_of_week_counts["Weekend"] += 1
                            else:
                                day_of_week_counts["Weekday"] += 1
                        except Exception:
                            pass
                
                peak_tod = max(time_of_day_counts.items(), key=lambda x: x[1])[0] if time_of_day_counts else "Unknown"
                peak_dow = max(day_of_week_counts.items(), key=lambda x: x[1])[0] if day_of_week_counts else "Unknown"
                
                polygon = [
                    [x1, y1],
                    [x2, y1],
                    [x2, y2],
                    [x1, y2],
                    [x1, y1]
                ]
                
                features.append({
                    "type": "Feature",
                    "properties": {
                        "risk": risk,
                        "density": float(d),
                        "color": color,
                        "fillOpacity": 0.4 if risk == "High" else 0.2,
                        "peak_time_of_day": peak_tod,
                        "peak_day_of_week": peak_dow,
                        "incident_count": len(cell_crimes)
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [polygon]
                    }
                })
        return {"type": "FeatureCollection", "features": features}
    except Exception:
        return {"type": "FeatureCollection", "features": []}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in kilometers between two lat/lon coordinates."""
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _convex_hull_2d(points: list[tuple[float, float]]) -> list[list[float]]:
    """
    Monotone chain 2D convex hull algorithm.
    Returns polygon coordinates [[lat, lon], ...] enclosing all input coordinates.
    """
    pts = sorted(set(points))
    if len(pts) <= 2:
        return [[round(lat, 5), round(lon, 5)] for lat, lon in pts]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3 and len(pts) >= 3:
        hull = pts
    return [[round(lat, 5), round(lon, 5)] for lat, lon in hull]


def compute_unsub_anchor_areas(rows: list[dict], unsubs: list[dict] = None) -> list[dict]:
    """
    Computes UNSUB anchor areas (geographic profiling honest version).
    For each UNSUB series / cluster of coordinates, computes:
      - centroid: mean lat/lon of case coordinates
      - convex_hull: polygon coordinates enclosing all case points
      - radius_km: max distance from centroid to furthest case point
      - anchor_area: geometry object + human-readable operating envelope
    """
    # Group coordinates by zone or explicit unsub_id
    clusters: dict[str, list[tuple[float, float, str]]] = defaultdict(list)

    if unsubs:
        for u in unsubs:
            uid = u.get("id") or u.get("unsub_id") or "UNSUB-1"
            pts = u.get("points") or []
            for p in pts:
                try:
                    lat = float(p["lat"])
                    lon = float(p["lon"])
                    clusters[uid].append((lat, lon, u.get("zone", "Karnataka")))
                except (KeyError, ValueError, TypeError):
                    pass
    else:
        # Build cluster from rows by zone for high-density crime groups
        for r in rows:
            try:
                lat = float(r.get("lat") or r.get("lat_r"))
                lon = float(r.get("lon") or r.get("lon_r"))
                zone = r.get("District_Name") or r.get("zone") or "Bengaluru Urban"
                clusters[f"UNSUB-{zone.replace(' ', '-').upper()}"].append((lat, lon, zone))
            except (ValueError, TypeError):
                pass

    anchor_areas = []
    for uid, pts in sorted(clusters.items()):
        if not pts:
            continue
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        zones = [p[2] for p in pts]
        primary_zone = max(set(zones), key=zones.count) if zones else "Karnataka"

        centroid_lat = round(sum(lats) / len(lats), 5)
        centroid_lon = round(sum(lons) / len(lons), 5)

        max_dist_km = 0.0
        for lat, lon, _ in pts:
            dist = _haversine_km(centroid_lat, centroid_lon, lat, lon)
            if dist > max_dist_km:
                max_dist_km = dist

        radius_km = max(1.5, round(max_dist_km, 2))
        hull_coords = _convex_hull_2d([(lat, lon) for lat, lon, _ in pts])

        anchor_areas.append({
            "unsub_id": uid,
            "label": f"Anchor Area — {uid}",
            "primary_zone": primary_zone,
            "centroid": {"lat": centroid_lat, "lon": centroid_lon},
            "convex_hull": hull_coords,
            "radius_km": radius_km,
            "case_count": len(pts),
            "description": f"Operates within {radius_km:.1f} km of {primary_zone} centroid",
        })

    return anchor_areas


def compute_dark_zones(rows: list[dict], gaps: list[dict] = None, silences: list[dict] = None) -> list[dict]:
    """
    Computes the Dark-Zone Surface (Geography of the Unknown).
    Per zone, computes coverage sparse-score = f(gap_count, silence_alerts, unresolved_share).
    Answers: 'Where do we know the least?' — the geographic complement of the hotspot layer.
    """
    zone_stats = defaultdict(lambda: {"total": 0, "unresolved": 0, "lat_sum": 0.0, "lon_sum": 0.0, "coords_count": 0})

    for r in rows:
        zone = r.get("District_Name") or r.get("zone") or "Bengaluru Urban"
        st = zone_stats[zone]
        st["total"] += 1
        accused = str(r.get("AccusedName", "") or r.get("suspect_id", "") or "").strip().lower()
        ac_cnt = r.get("Accused_Count")
        if not accused or accused in ("unknown", "unsub", "none", "nil", "") or ac_cnt == 0 or ac_cnt == "0":
            st["unresolved"] += 1

        try:
            lat = float(r.get("lat") or r.get("lat_r"))
            lon = float(r.get("lon") or r.get("lon_r"))
            st["lat_sum"] += lat
            st["lon_sum"] += lon
            st["coords_count"] += 1
        except (ValueError, TypeError):
            pass

    # Count gaps per zone
    gap_counts = defaultdict(int)
    if gaps:
        for g in gaps:
            z = g.get("zone") or "Bengaluru Urban"
            gap_counts[z] += 1

    # Count silences per zone
    silence_counts = defaultdict(int)
    if silences:
        for s in silences:
            z = s.get("zone") or "Bengaluru Urban"
            silence_counts[z] += 1

    dark_zones = []
    for zone, st in sorted(zone_stats.items()):
        total = max(1, st["total"])
        unresolved_share = st["unresolved"] / total
        g_cnt = gap_counts[zone]
        s_cnt = silence_counts[zone]

        dark_score = round(min(100.0, (unresolved_share * 45.0) + (g_cnt * 15.0) + (s_cnt * 20.0)), 1)

        if dark_score >= 60.0:
            dark_level = "Critical"
        elif dark_score >= 40.0:
            dark_level = "High"
        elif dark_score >= 20.0:
            dark_level = "Moderate"
        else:
            dark_level = "Minimal"

        lat = round(st["lat_sum"] / st["coords_count"], 5) if st["coords_count"] > 0 else 12.9716
        lon = round(st["lon_sum"] / st["coords_count"], 5) if st["coords_count"] > 0 else 77.5946

        dark_zones.append({
            "zone": zone,
            "dark_score": dark_score,
            "dark_level": dark_level,
            "unresolved_cases": st["unresolved"],
            "total_cases": st["total"],
            "unresolved_share": round(unresolved_share, 3),
            "gap_count": g_cnt,
            "silence_count": s_cnt,
            "lat": lat,
            "lon": lon,
        })

    dark_zones.sort(key=lambda x: x["dark_score"], reverse=True)
    return dark_zones
