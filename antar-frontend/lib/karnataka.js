import { asset } from "@/lib/assets";

// Maps InstiSight's police "zone" field (57 values - a mix of the ~30 revenue
// districts, Bengaluru City police sub-divisions, and statewide special units)
// onto the district polygons of the Karnataka district GeoJSON. Special statewide
// units (railways, coastal security, CID) have no single home district and are left
// unmapped: they still render as Gi* hotspot points, just don't contribute to the
// choropleth fill.
//
// FILE CHOICE - public/karnataka_new.geojson (2011 census boundaries, 30 districts,
// `properties.district` holds the modern Kannada-transliterated name). Every one of
// the 30 mapping targets below matches a feature in that file exactly.
//
// Do NOT switch back to public/karnataka.geojson: that is the GADM pre-2007 set with
// only 27 features and legacy English names ("Bangalore Urban", "Bellary", "Mysore",
// "Belgaum"…). 17 of the 30 targets below have no match there, so the choropleth
// silently renders empty. It is kept in public/ only as a historical reference.
//
// Vijayanagara (split from Ballari in 2021) has no polygon in the 2011 set, so it is
// mapped onto its parent Ballari below - the honest option until a 31-district
// boundary file is sourced.
//
// Routed through asset() so it lands inside the deployment's basePath: bare on
// localhost, "/app/..." in the Catalyst export. A raw fetch() is NOT basePath-prefixed
// by Next, and getting this wrong leaves the map with no state outline and no district
// borders at all - in exactly one of the two environments.
export const KARNATAKA_GEOJSON_URL = asset("/karnataka_new.geojson");

// PREFERRED SOURCE - public/karnataka.json is the same 30-district 2011 boundary set as a
// TopoJSON (72 KB vs 229 KB) whose shared borders are stored ONCE, as arcs. That is what
// lets topojson-client derive two layers from one file:
//   feature(topo, topo.objects.districts)            -> the 30 district polygons
//   merge(topo, topo.objects.districts.geometries)   -> the DISSOLVED Karnataka state outline
// The merge is the only honest way to draw the state border: the district file has no state
// polygon, and stroking all 30 districts heavily just thickens every internal border too.
// MapScreen falls back to KARNATAKA_GEOJSON_URL (districts only, no state outline) if this
// file fails to load.
export const KARNATAKA_TOPOJSON_URL = asset("/karnataka.json");

export const ZONE_TO_GADM_DISTRICT = {
  "Bagalkot": "Bagalkote",
  "Ballari": "Ballari",
  "Vijayanagara": "Ballari", // (If Vijayanagara isn't in the geojson, fallback to parent Ballari)
  "Banashankari": "Bengaluru Urban",
  "Belagavi": "Belagavi",
  "Belagavi City": "Belagavi",
  "Belagavi Dist": "Belagavi",
  "Bengaluru City": "Bengaluru Urban",
  "Bengaluru Dist": "Bengaluru Rural",
  "Bidar": "Bidar",
  "Chamarajanagar": "Chamarajanagara",
  "Chickballapura": "Chikkaballapura",
  "Chikkamagaluru": "Chikkamagaluru",
  "Chitradurga": "Chitradurga",
  "Dakshina Kannada": "Dakshina Kannada",
  "Mangaluru": "Dakshina Kannada",
  "Mangaluru City": "Dakshina Kannada",
  "Davanagere": "Davanagere",
  "Dharwad": "Dharwad",
  "Hubballi": "Dharwad",
  "Hubballi Dharwad City": "Dharwad",
  "Gadag": "Gadag",
  "Gandhinagar": "Bengaluru Urban",
  "Hassan": "Hassan",
  "Haveri": "Haveri",
  "Hebbal": "Bengaluru Urban",
  "ISD Bengaluru": "Bengaluru Urban",
  "Indiranagar": "Bengaluru Urban",
  "Jayanagar": "Bengaluru Urban",
  "K.G.F": "Kolar",
  "KR Puram": "Bengaluru Urban",
  "Kalaburagi": "Kalaburagi",
  "Kalaburagi City": "Kalaburagi",
  "Kodagu": "Kodagu",
  "Kolar": "Kolar",
  "Koppal": "Koppal",
  "Malleshwaram": "Bengaluru Urban",
  "Mandya": "Mandya",
  "Mysuru City": "Mysuru",
  "Mysuru Dist": "Mysuru",
  "Mysuru-Devaraja": "Mysuru",
  "Mysuru-Nazarbad": "Mysuru",
  "Raichur": "Raichur",
  "Rajajinagar": "Bengaluru Urban",
  "Ramanagara": "Ramanagara",
  "Shivamogga": "Shivamogga",
  "Tumakuru": "Tumakuru",
  "Udupi": "Udupi",
  "Uttara Kannada": "Uttara Kannada",
  "Vijayapur": "Vijayapura",
  "Whitefield": "Bengaluru Urban",
  "Yadgir": "Yadgir",
  "Yeshwanthpur": "Bengaluru Urban",
  // Statewide / non-geographic units - no district home, point-only:
  // "CID", "Central", "Karnataka Railways", "Coastal Security Police"
};

// Canonical zone coordinates (lat, lng) - verified against real Karnataka
// geography. The backend seed has a few drifted points (e.g. Mangaluru showed
// inland); the frontend ALWAYS prefers these over backend lat/lon.
export const ZONE_COORDS = {
  "Bagalkot": [16.181, 75.696],
  "Ballari": [15.139, 76.921],
  "Vijayanagara": [15.269, 76.387],
  "Banashankari": [12.925, 77.546],
  "Belagavi": [15.849, 74.498],
  "Belagavi City": [15.852, 74.507],
  "Belagavi Dist": [15.75, 74.65],
  "Bengaluru City": [12.972, 77.594],
  "Bengaluru Dist": [13.198, 77.708],
  "Bidar": [17.913, 77.52],
  "Chamarajanagar": [11.926, 76.94],
  "Chickballapura": [13.435, 77.728],
  "Chikkamagaluru": [13.316, 75.772],
  "Chitradurga": [14.226, 76.4],
  "Dakshina Kannada": [12.84, 75.06],
  "Mangaluru": [12.87, 74.842],
  "Mangaluru City": [12.87, 74.856],
  "Davanagere": [14.464, 75.921],
  "Dharwad": [15.458, 75.008],
  "Hubballi": [15.364, 75.124],
  "Hubballi Dharwad City": [15.36, 75.09],
  "Gadag": [15.432, 75.63],
  "Gandhinagar": [12.977, 77.577],
  "Hassan": [13.005, 76.103],
  "Haveri": [14.793, 75.404],
  "Hebbal": [13.035, 77.597],
  "ISD Bengaluru": [12.954, 77.61],
  "Indiranagar": [12.971, 77.641],
  "Jayanagar": [12.925, 77.583],
  "K.G.F": [12.965, 78.273],
  "KR Puram": [13.007, 77.696],
  "Kalaburagi": [17.329, 76.834],
  "Kalaburagi City": [17.335, 76.83],
  "Kodagu": [12.421, 75.74],
  "Kolar": [13.137, 78.13],
  "Koppal": [15.35, 76.154],
  "Malleshwaram": [13.003, 77.57],
  "Mandya": [12.524, 76.897],
  "Mysuru City": [12.296, 76.639],
  "Mysuru Dist": [12.42, 76.55],
  "Mysuru-Devaraja": [12.309, 76.653],
  "Mysuru-Nazarbad": [12.298, 76.663],
  "Raichur": [16.207, 77.356],
  "Rajajinagar": [12.99, 77.555],
  "Ramanagara": [12.722, 77.281],
  "Shivamogga": [13.932, 75.568],
  "Tumakuru": [13.342, 77.101],
  "Udupi": [13.341, 74.747],
  "Uttara Kannada": [14.802, 74.129],
  "Vijayapur": [16.83, 75.71],
  "Whitefield": [12.97, 77.75],
  "Yadgir": [16.77, 77.138],
  "Yeshwanthpur": [13.025, 77.54],
  // statewide units - pinned to their HQ so points don't fall in the sea
  "CID": [12.977, 77.591],
  "Central": [12.977, 77.591],
  "Karnataka Railways": [12.978, 77.57],
  "Coastal Security Police": [13.35, 74.704],
};

/** Correct coordinates for a zone - canonical table first, backend fallback. */
export function coordFor(zone, fallbackLat, fallbackLon) {
  const c = ZONE_COORDS[zone];
  return c ? { lat: c[0], lon: c[1] } : { lat: fallbackLat, lon: fallbackLon };
}

// Aggregates a per-zone metric (e.g. fir_count) onto GADM district names for the choropleth.
export function aggregateByDistrict(zoneRows, valueKey) {
  const totals = {};
  for (const row of zoneRows) {
    const district = ZONE_TO_GADM_DISTRICT[row.zone];
    if (!district) continue;
    totals[district] = (totals[district] || 0) + (row[valueKey] || 0);
  }
  return totals;
}
