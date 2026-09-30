// Map forecast - client helpers for /api/forecast/* (docs/MAP_FORECASTING_PLAN.md, Phase 5).

import { ZONE_TO_GADM_DISTRICT } from "@/lib/karnataka";

const API = process.env.NEXT_PUBLIC_API_URL || "";

// The map's crime pills name offences; the forecast works on 16 categories. Where a pill
// maps to a wider category the panel SAYS so - widening a question silently is exactly
// what the constitution forbids (Law 1).
export const PILL_TO_CATEGORY = {
  "": "ALL",
  theft: "PROPERTY", robbery: "PROPERTY", chain_snatching: "PROPERTY",
  burglary: "PROPERTY", vehicle_theft: "PROPERTY",
  cybercrime: "CYBER", assault: "VIOLENT", murder: "MURDER", cheating_fraud: "ECONOMIC",
  kidnapping: "KIDNAP", domestic_violence: "WOMEN", ndps: "NARCOTICS", rioting: "VIOLENT",
};

// Sequential ramp for expected FIRs (quantile classes 0–4): low reads as quiet slate,
// high as ember. Distinct from the cyan/red used by the Gi* cluster layer.
export const FORECAST_RAMP = ["#3A4A5E", "#5E6B55", "#B7862A", "#E8872D", "#FF5A3C"];

export function forecastColor(cls) {
  return FORECAST_RAMP[Math.max(0, Math.min(4, cls | 0))];
}

export function markerRadius(expected, unitType) {
  const e = Math.max(0, expected || 0);
  return unitType === "beat"
    ? Math.min(3 + 3.2 * Math.sqrt(e), 16)
    : Math.min(3.5 + 2.2 * Math.sqrt(e), 20);
}

// A GADM map district ("Mysuru") is one or more police districts ("Mysuru City",
// "Mysuru Dist"). Returns the ones the forecast knows, joined for the API's "|" list.
export function policeDistrictsFor(gadmName, known) {
  if (!gadmName || !known?.length) return "";
  const set = new Set(known);
  const zones = Object.entries(ZONE_TO_GADM_DISTRICT)
    .filter(([, g]) => g === gadmName).map(([z]) => z).filter((z) => set.has(z));
  if (set.has(gadmName)) zones.push(gadmName);
  return [...new Set(zones)].join("|");
}

// Point-in-polygon against the district GeoJSON (Polygon / MultiPolygon, outer rings),
// with a bounding-box pre-check per feature. Returns null until the boundaries load.
export function makeContains(geo) {
  const feats = (geo?.features || []).map((f) => {
    const g = f.geometry || {};
    const polys = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
    const rings = polys.map((p) => p[0]).filter(Boolean);
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const r of rings) for (const [x, y] of r) {
      if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y;
    }
    return { rings, minX, minY, maxX, maxY };
  }).filter((f) => f.rings.length);
  if (!feats.length) return null;
  const inRing = (x, y, r) => {
    let inside = false;
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const [xi, yi] = r[i], [xj, yj] = r[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  };
  return (lat, lon) => feats.some((f) => lon >= f.minX && lon <= f.maxX && lat >= f.minY && lat <= f.maxY
    && f.rings.some((r) => inRing(lon, lat, r)));
}

export class ForecastError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : detail?.message || `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export async function getForecast(path, params = {}, signal) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") q.set(k, v);
  const r = await fetch(`${API}/api/forecast${path}${q.toString() ? `?${q}` : ""}`, { signal });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new ForecastError(r.status, body.detail);
  }
  return r.json();
}

export function unitShortName(unit) {
  return unit?.includes(" | ") ? unit.split(" | ")[1] : unit;
}

export function prettyIso(iso) {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function rangeText(lo, hi) {
  return lo === hi ? `${lo}` : `${lo}–${hi}`;
}
