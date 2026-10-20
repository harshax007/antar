"use client";

import { createPortal } from "react-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Polyline, Polygon, Tooltip, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { useRouter, useSearchParams } from "next/navigation";
import { useLang } from "@/components/Providers";
import { KARNATAKA_GEOJSON_URL, KARNATAKA_TOPOJSON_URL, policeLabel, ZONE_TO_GADM_DISTRICT, ZONE_COORDS, coordFor, aggregateByDistrict } from "@/lib/karnataka";
import { feature as topoFeature, merge as topoMerge } from "topojson-client";
import { parseCSV, fromRecords, prepare, aliasFor } from "@/lib/crimeGraph";
import { X } from "lucide-react";
import GeoIntelDashboard, { crimeName } from "@/components/GeoIntel";
import ProposeAction from "@/components/ProposeAction";
import { useForecast, ForecastLayer, ForecastPanel, ForecastCard, ModelCardModal, AsOfChip } from "@/components/ForecastPanel";
import { makeContains } from "@/lib/forecast";
import { readSession } from "@/lib/auth";
import { MAP_AGENTS, MapAgentsMenu, AgentDropLayer, MapAgentResult } from "@/components/MapAgents";
import { FESTIVALS } from "@/lib/festivals";
import "leaflet/dist/leaflet.css";
import { asset } from "@/lib/assets";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

const GADM_CENTROIDS = {
  "Bagalkote": [16.181, 75.696],
  "Ballari": [15.139, 76.921],
  "Belagavi": [15.849, 74.498],
  "Bengaluru Rural": [13.198, 77.708],
  "Bengaluru Urban": [12.972, 77.594],
  "Bidar": [17.913, 77.520],
  "Chamarajanagara": [11.926, 76.940],
  "Chikkaballapura": [13.435, 77.728],
  "Chikkamagaluru": [13.316, 75.772],
  "Chitradurga": [14.226, 76.400],
  "Dakshina Kannada": [12.840, 75.060],
  "Davanagere": [14.464, 75.921],
  "Dharwad": [15.458, 75.008],
  "Gadag": [15.432, 75.630],
  "Hassan": [13.005, 76.103],
  "Haveri": [14.793, 75.404],
  "Kalaburagi": [17.329, 76.834],
  "Kodagu": [12.421, 75.740],
  "Kolar": [13.137, 78.130],
  "Koppal": [15.346, 76.155],
  "Mandya": [12.523, 76.895],
  "Mysuru": [12.295, 76.639],
  "Raichur": [16.195, 77.360],
  "Ramanagara": [12.715, 77.281],
  "Shivamogga": [13.929, 75.568],
  "Tumakuru": [13.337, 77.101],
  "Udupi": [13.340, 74.742],
  "Uttara Kannada": [14.818, 74.536],
  "Vijayapura": [16.827, 75.713],
  "Yadgir": [16.766, 77.137]
};

// Backend seed crime types (app/seeds/generator.py CRIME_TYPES) - quick pills
// for the frequent ones, a "More" select for the rest.
const PILLS = [
  { key: "", en: "All Crimes", kn: "ಎಲ್ಲಾ ಅಪರಾಧ" },
  { key: "theft", en: "Theft", kn: "ಕಳ್ಳತನ" },
  { key: "robbery", en: "Robbery", kn: "ದರೋಡೆ" },
  { key: "chain_snatching", en: "Chain-snatching", kn: "ಸರಗಳ್ಳತನ" },
  { key: "burglary", en: "Burglary", kn: "ಮನೆಗಳ್ಳತನ" },
  { key: "vehicle_theft", en: "Vehicle theft", kn: "ವಾಹನ ಕಳ್ಳತನ" },
];
const MORE_TYPES = [
  { key: "cybercrime", en: "Cybercrime", kn: "ಸೈಬರ್ ಅಪರಾಧ" },
  { key: "assault", en: "Assault", kn: "ಹಲ್ಲೆ" },
  { key: "murder", en: "Murder", kn: "ಕೊಲೆ" },
  { key: "cheating_fraud", en: "Cheating / Fraud", kn: "ವಂಚನೆ" },
  { key: "kidnapping", en: "Kidnapping", kn: "ಅಪಹರಣ" },
  { key: "domestic_violence", en: "Domestic violence", kn: "ಕೌಟುಂಬಿಕ ದೌರ್ಜನ್ಯ" },
  { key: "ndps", en: "NDPS / Narcotics", kn: "ಮಾದಕ ದ್ರವ್ಯ" },
  { key: "rioting", en: "Rioting", kn: "ಗಲಭೆ" },
];
// pill key → CSV CrimeGroup/Head keywords, for the flow-corridor filter
const FLOW_KWS = {
  theft: ["theft"], robbery: ["robbery", "dacoity"], chain_snatching: ["snatch"],
  burglary: ["burglary", "house break"], vehicle_theft: ["motor", "vehicle"],
  cybercrime: ["cyber"], assault: ["hurt", "assault"], murder: ["murder"],
  cheating_fraud: ["cheat", "fraud", "forgery"], kidnapping: ["kidnap", "abduct"],
  domestic_violence: ["cruelty", "husband"], ndps: ["narcotic", "drug"], rioting: ["riot"],
};

const MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_KN = ["ಜನ", "ಫೆಬ್ರ", "ಮಾರ್ಚ್", "ಏಪ್ರಿ", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗ", "ಸೆಪ್ಟೆಂ", "ಅಕ್ಟೋ", "ನವೆಂ", "ಡಿಸೆಂ"];
const DOW_EN = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

function isoDate(y, m, d) { return new Date(Date.UTC(y, m, d)).toISOString().slice(0, 10); }
function daysInMonth(y, m) { return new Date(y, m + 1, 0).getDate(); }
// Tween a number toward its new value so a date change reads as a change, not a flicker.
// Honours prefers-reduced-motion by jumping straight to the value.
function useAnimatedNumber(value, ms = 650) {
  const [shown, setShown] = useState(value);
  const fromRef = useRef(value);
  useEffect(() => {
    const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const hidden = typeof document !== "undefined" && document.hidden;
    const from = fromRef.current;
    // Browsers pause requestAnimationFrame in background tabs, so a value that arrives
    // while the tab is hidden would otherwise sit on the OLD number. Jump instead.
    if (reduce || hidden || from === value) { fromRef.current = value; setShown(value); return; }
    let raf;
    const t0 = performance.now();
    const tick = (now) => {
      const k = Math.min(1, (now - t0) / ms);
      const eased = 1 - Math.pow(1 - k, 3);
      const v = Math.round(from + (value - from) * eased);
      fromRef.current = v;
      setShown(v);
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    // Backstop: if frames stop (tab hidden mid-tween), land on the real value anyway.
    const settle = setTimeout(() => { fromRef.current = value; setShown(value); }, ms + 120);
    return () => { cancelAnimationFrame(raf); clearTimeout(settle); };
  }, [value, ms]);
  return shown;
}

function shiftIso(iso, days) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function prettyDate(iso, kn) {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${(kn ? MONTHS_KN : MONTHS_EN)[m - 1]} ${y}`;
}

function riskClass(level) {
  const l = (level || "").toLowerCase();
  return l === "high" ? "mx-risk-h" : l === "medium" || l === "moderate" ? "mx-risk-m" : "mx-risk-l";
}

function ZoomButtons({ geo, onReset }) {
  const map = useMap();
  return (
    <div className="mx-zoom mx-panel" style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
      <button onClick={() => { 
        if (geo) map.flyToBounds(L.geoJSON(geo).getBounds(), { padding: [0, 0], duration: 0.6 });
        if (onReset) onReset();
      }} aria-label="Reset View" title="Reset Map" style={{ fontSize: "14px", lineHeight: 1 }}>↺</button>
      <button onClick={() => map.zoomIn()} aria-label="Zoom in">+</button>
      <button onClick={() => map.zoomOut()} aria-label="Zoom out">&minus;</button>
    </div>
  );
}

// The map lives in a grid cell whose size settles after mount (and changes with the
// window). Leaflet measures its container once; re-measure whenever the frame resizes.
function AutoResize() {
  const map = useMap();
  useEffect(() => {
    const el = map.getContainer();
    if (typeof ResizeObserver === "undefined" || !el) return;
    const ro = new ResizeObserver(() => map.invalidateSize({ pan: false }));
    ro.observe(el);
    return () => ro.disconnect();
  }, [map]);
  return null;
}

// Place labels that would collide are not drawn. Callouts (the busiest districts, with
// their counts) are placed first, then district names by how many cases they hold, so a
// busy district keeps its name and a quiet neighbour gives way; a district that has a
// callout drops its plain label, since the callout names it. Positions come from the map's
// own projection and an estimate of each label's size, recomputed on zoom and resize, so
// the result does not depend on when Leaflet happens to draw the labels.
function LabelLayout({ labels, callouts, onChange }) {
  const map = useMap();
  const compute = useCallback(() => {
    if (!map) return;
    const kept = [];
    const hit = (r) => kept.some((k) => r.l < k.r + 3 && r.r + 3 > k.l && r.t < k.b + 2 && r.b + 2 > k.t);
    const hiddenCallouts = new Set(), hiddenLabels = new Set(), named = new Set();
    for (const c of callouts) {
      const p = map.latLngToContainerPoint(c.end);
      const w = c.text.length * 5.6 + 16, h = 20;
      const r = c.west ? { l: p.x - w / 2, r: p.x + w / 2, t: p.y - 3 - h - 6, b: p.y - 3 - 6 }
                       : { l: p.x + 4 + 6, r: p.x + 4 + 6 + w, t: p.y - h / 2, b: p.y + h / 2 };
      if (hit(r)) { hiddenCallouts.add(c.name); continue; }
      kept.push(r);
      named.add(c.name);
    }
    for (const lb of [...labels].sort((a, b) => b.pri - a.pri)) {
      if (named.has(lb.name)) { hiddenLabels.add(lb.name); continue; }
      const p = map.latLngToContainerPoint(lb.at);
      const w = lb.name.length * 5.9 + 2, h = 11;
      const r = { l: p.x - w / 2, r: p.x + w / 2, t: p.y - h / 2, b: p.y + h / 2 };
      if (hit(r)) { hiddenLabels.add(lb.name); continue; }
      kept.push(r);
    }
    onChange({ labels: hiddenLabels, callouts: hiddenCallouts });
  }, [map, labels, callouts, onChange]);
  useEffect(() => { compute(); }, [compute]);
  useMapEvents({ zoomend: compute, resize: compute });
  return null;
}

// Police districts and commissionerates an officer can be posted to (the register's own
// names; seeded localities and statewide units are not districts).
const POLICE_DISTRICTS = [
  "Bagalkot", "Ballari", "Belagavi City", "Belagavi Dist", "Bengaluru City", "Bengaluru Dist", "Bidar",
  "Chamarajanagar", "Chickballapura", "Chikkamagaluru", "Chitradurga", "Dakshina Kannada", "Davanagere",
  "Dharwad", "Gadag", "Hassan", "Haveri", "Hubballi Dharwad City", "K.G.F", "Kalaburagi", "Kalaburagi City",
  "Kodagu", "Kolar", "Koppal", "Mandya", "Mangaluru City", "Mysuru City", "Mysuru Dist", "Raichur",
  "Ramanagara", "Shivamogga", "Tumakuru", "Udupi", "Uttara Kannada", "Vijayanagara", "Vijayapur", "Yadgir",
];

// Height of the forecast key under the map (the map gives up this much while it shows).
const FCKEY_H = 46;

// How wide the map key may be and stay in the empty space (the sea) at the bottom-left,
// clear of the state: the first point inside Karnataka along the bottom rows of the frame.
const KEY_LEFT = 16, KEY_ROWS = 96;
function KeyRoom({ contains, onChange }) {
  const map = useMap();
  const measure = useCallback(() => {
    if (!contains) return;
    const { x: w, y: h } = map.getSize();
    let edge = w;
    for (let y = h - 8; y >= h - KEY_ROWS; y -= 8) {
      for (let x = KEY_LEFT; x < edge; x += 6) {
        const ll = map.containerPointToLatLng([x, y]);
        if (contains(ll.lat, ll.lng)) { edge = x; break; }
      }
    }
    onChange(Math.max(150, Math.min(edge - KEY_LEFT - 14, w - 90)));
  }, [map, contains, onChange]);
  useEffect(() => { measure(); }, [measure]);
  useMapEvents({ moveend: measure, zoomend: measure, resize: measure });
  return null;
}

function FlyTo({ bounds }) {
  const map = useMap();
  useEffect(() => { if (bounds) map.flyToBounds(bounds, { padding: [60, 60], duration: 0.5 }); }, [bounds, map]);
  return null;
}

// The whole state, a little closer than an exact fit (half a step in): the corners are
// empty sea and neighbouring states, and the districts read larger.
const STATE_ZOOM_IN = 0.5;
function fitState(map, bounds, fly = false) {
  const z = Math.min(map.getBoundsZoom(bounds) + STATE_ZOOM_IN, map.getMaxZoom());
  if (fly) map.flyTo(bounds.getCenter(), z, { duration: 0.6 });
  else map.setView(bounds.getCenter(), z, { animate: false });
}

function FitToKarnataka({ geo, selectedDistrict, resetTrigger, startBounds }) {
  const map = useMap();
  const prevDistrictRef = useRef(null);
  const prevTriggerRef = useRef(resetTrigger);
  // First load: fill the map frame with the state rather than a fixed centre/zoom, which
  // left Karnataka small in a sea of empty tiles.
  const fitted = useRef(false);
  useEffect(() => {
    if (!geo || fitted.current) return;
    fitted.current = true;
    requestAnimationFrame(() => {
      map.invalidateSize();
      // the officer's own district when there is one, else the whole state
      if (startBounds) map.fitBounds(startBounds, { padding: [60, 60], animate: false });
      else fitState(map, L.geoJSON(geo).getBounds());
    });
  }, [geo, map]);

  // The frame changes size after the first fit (the key strip under the map comes and goes,
  // the side panels settle): Leaflet is told, and the state is fitted again so it fills the
  // frame. Inside a district the view is left where the officer put it.
  const districtRef = useRef(selectedDistrict);
  districtRef.current = selectedDistrict;
  useEffect(() => {
    if (!geo || typeof ResizeObserver === "undefined") return;
    const bounds = L.geoJSON(geo).getBounds();
    let t = null;
    const ro = new ResizeObserver(() => {
      clearTimeout(t);
      t = setTimeout(() => {
        map.invalidateSize();
        if (!districtRef.current) fitState(map, bounds);
      }, 60);
    });
    ro.observe(map.getContainer());
    return () => { clearTimeout(t); ro.disconnect(); };
  }, [geo, map]);

  useEffect(() => {
    if (!geo) return;
    const triggerFired = resetTrigger !== prevTriggerRef.current && resetTrigger > 0;
    const districtClosed = !selectedDistrict && prevDistrictRef.current;
    // When a district is closed/deselected or reset triggered, return to default Karnataka state view
    if (triggerFired || districtClosed) {
      const layer = L.geoJSON(geo);
      fitState(map, layer.getBounds(), true);
    }
    prevDistrictRef.current = selectedDistrict;
    prevTriggerRef.current = resetTrigger;
  }, [geo, map, selectedDistrict, resetTrigger]);
  return null;
}

// Hotspot readings already fetched this session, by crime type and date.
const GI_CACHE = new Map();

// Cases per zone in the `days`+1 days ending on a date, from the map's Gi* window. Kept by
// date and crime type, so a second district on the same date is answered from memory.
const WINDOW_CACHE = new Map();
function windowCounts(days, endDate, crimeType, signal) {
  const key = `${crimeType}|${endDate}|${days}`;
  if (WINDOW_CACHE.has(key)) return Promise.resolve(WINDOW_CACHE.get(key));
  const q = new URLSearchParams({ days: String(days), end_date: endDate });
  if (crimeType) q.set("crime_type", crimeType);
  return fetch(`${API}/api/map/gi_star?${q}`, { signal })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => {
      if (!d?.zones) return null;
      const w = { end: d.end_date, by: Object.fromEntries(d.zones.map((z) => [z.zone, z.observed || 0])),
                  hot: Object.fromEntries(d.zones.map((z) => [z.zone, !!z.is_hotspot])) };
      WINDOW_CACHE.set(key, w);
      if (WINDOW_CACHE.size > 80) WINDOW_CACHE.delete(WINDOW_CACHE.keys().next().value);
      return w;
    })
    .catch(() => null);
}

export default function MapScreen() {
  const router = useRouter();
  const sp = useSearchParams();
  const { lang } = useLang();
  const kn = lang === "kn";

  // Deep link from Chat ("Open Map"): ?crime=<key>&date=YYYY-MM-DD
  const spCrime = sp?.get("crime") || "";
  const validCrime = [...PILLS, ...MORE_TYPES].some((p) => p.key && p.key === spCrime);
  const [crimeType, setCrimeType] = useState(validCrime ? spCrime : "");
  const [flowOn, setFlowOn] = useState(false); // crime flow only when required
  const [reportOpen, setReportOpen] = useState(false);

  const today = useMemo(() => new Date(), []);
  const todayIso = useMemo(() => today.toISOString().slice(0, 10), [today]);
  const initDate = useMemo(() => {
    const s = sp?.get("date");
    const d = s ? new Date(`${s}T00:00:00`) : today;
    return isNaN(d.getTime()) || d > today ? today : d;
  }, [sp, today]);
  const [calYear, setCalYear] = useState(initDate.getFullYear());
  const [calMonth, setCalMonth] = useState(initDate.getMonth());
  const [selDay, setSelDay] = useState(initDate.getDate());
  const rawEnd = isoDate(calYear, calMonth, Math.min(selDay, daysInMonth(calYear, calMonth)));
  const endDate = rawEnd > todayIso ? todayIso : rawEnd;
  // The window the map counts over, ending on the selected day. A day is the morning crime
  // review ("what happened since yesterday"); 7 and 28 days are the weekly review and the
  // hotspot picture, which a single day is too thin to show.
  const [win, setWin] = useState(() => { const w = Number(sp?.get("days")); return [1, 7, 28].includes(w) ? w : 1; });
  const winStart = shiftIso(endDate, -(win - 1));
  const W = win === 1
    ? { on: kn ? "ಈ ದಿನ" : "on this day", prev: kn ? "ಹಿಂದಿನ ದಿನ" : "the day before", list: kn ? "ಈ ದಿನ" : "this day" }
    : { on: kn ? `ಈ ${win} ದಿನಗಳಲ್ಲಿ` : `in these ${win} days`, prev: kn ? `ಹಿಂದಿನ ${win} ದಿನ` : `the ${win} days before`,
        list: kn ? `${win} ದಿನ` : `last ${win} days` };

  const [geo, setGeo] = useState(null);
  const [stateOutline, setStateOutline] = useState(null);
  // Is a point inside Karnataka? A station's median point can fall in the sea (inside the
  // bounding box, off the coast); the forecast layer draws only what is on land.
  const karnatakaContains = useMemo(() => makeContains(geo), [geo]);
  const [csvRecs, setCsvRecs] = useState(null);
  const [districtsFiltered, setDistrictsFiltered] = useState([]);
  const [districtsRich, setDistrictsRich] = useState([]);
  const [giStar, setGiStar] = useState({ zones: [] });
  const [activity, setActivity] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [serverCorridors, setServerCorridors] = useState([]);
  const [anchorOn, setAnchorOn] = useState(false);
  const [darkOn, setDarkOn] = useState(false);
  const [darkZones, setDarkZones] = useState([]);
  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const [flyBounds, setFlyBounds] = useState(null);
  const [districtDetail, setDistrictDetail] = useState(null);
  const [showDossier, setShowDossier] = useState(false);

  // Map forecast (next 7 / 28 days, stations statewide → beats in a selected district)
  const fc = useForecast({
    crimeType, gadmDistrict: selectedDistrict,
    // deep link from a chat forecast answer: /map?unit=…&h=28&fc=PROPERTY
    initial: { unit: sp?.get("unit") || null, horizon: Number(sp?.get("h")) || 7, category: sp?.get("fc") || null },
  });
    const [modelCardOpen, setModelCardOpen] = useState(false);
  const [rightTab, setRightTab] = useState("summary");     // the summary is what an officer sees first
  const [llmSummary, setLlmSummary] = useState(null);
  const [llmLoading, setLlmLoading] = useState(false);


  useEffect(() => { if (fc.selected) setRightTab("where"); }, [fc.selected]);
  // Right column: View summary by default; Where next opens on click, or by itself when a
  // station or beat is picked on the map (its card shows there).
  

  // Karnataka boundaries. Preferred path is the TopoJSON: one fetch yields BOTH the 30
  // district polygons and - via topojson merge over the shared arcs - a genuinely
  // dissolved state outline, which no district-only GeoJSON can give us. If that file is
  // unavailable we fall back to the plain district GeoJSON and simply go without the
  // outer border rather than faking one.
  useEffect(() => {
    let alive = true;
    fetch(KARNATAKA_TOPOJSON_URL)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("topo"))))
      .then((topo) => {
        const obj = topo?.objects?.districts;
        if (!obj) throw new Error("no districts object");
        const districts = topoFeature(topo, obj);
        const outline = topoMerge(topo, obj.geometries);
        if (!alive) return;
        setGeo(districts);
        setStateOutline({ type: "Feature", properties: { name: "Karnataka" }, geometry: outline });
      })
      .catch(() => {
        // Fallback: district polygons only, no dissolved outline.
        fetch(KARNATAKA_GEOJSON_URL)
          .then((r) => (r.ok ? r.json() : Promise.reject(new Error("geojson"))))
          .then((d) => { if (alive) { setGeo(d); setStateOutline(null); } })
          .catch(() => { if (alive) { setGeo(null); setStateOutline(null); } });
      });
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    fetch(`${API}/api/map/districts/rich`).then((r) => r.json()).then((d) => setDistrictsRich(d.districts || [])).catch(() => {});
    fetch(`${API}/api/brain/activity`).then((r) => r.json()).then((d) => setActivity(d.activity || [])).catch(() => {});
    fetch(`${API}/api/alerts`).then((r) => r.json()).then((d) => setAlerts(d.alerts || [])).catch(() => {});
    fetch(`${API}/api/corridors`).then((r) => r.json()).then((d) => setServerCorridors(d.corridors || [])).catch(() => {});
    fetch(`${API}/api/map/darkzones`).then((r) => r.json()).then((d) => setDarkZones(d.zones || [])).catch(() => {});
  }, []);

  // The per-FIR record set (/api/dataset/graph, ~1.8 MB) backs exactly two things: the
  // client-side crime-flow arcs, which only render when `flowOn` is true AND the server
  // corridor feed came back empty, and one festival-load line in the briefing text.
  // It used to be fetched on mount, so every visit to the Map paid ~1.8 MB before the
  // first tile appeared. Fetch it the first time the flow layer is actually switched on.
  const [recsRequested, setRecsRequested] = useState(false);
  useEffect(() => {
    if (!flowOn || recsRequested) return;
    setRecsRequested(true);
    let alive = true;
    fetch(`${API}/api/dataset/graph`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("dataset"))))
      .then((d) => { if (alive) setCsvRecs(prepare(fromRecords(d.rows))); })
      .catch(() => {
        fetch(asset("/fir_synthetic.csv"))
          .then((r) => r.text())
          .then((t) => { if (alive) setCsvRecs(prepare(parseCSV(t))); })
          .catch(() => {});
      });
    return () => { alive = false; };
  }, [flowOn, recsRequested]);

  useEffect(() => {
    const q = crimeType ? `?crime_type=${crimeType}` : "";
    fetch(`${API}/api/map/districts${q}`).then((r) => r.json()).then((d) => setDistrictsFiltered(d.districts || [])).catch(() => {});
  }, [crimeType]);

  // Clicking through dates quickly used to let a slow, older response land last and
  // overwrite the newer one. Each change now aborts the previous request. The window
  // before the selected one is fetched alongside it so the report can show the change.
    const [giLoading, setGiLoading] = useState(true);
  const [giPrevTotal, setGiPrevTotal] = useState(null);
  const [giMonthlyTotal, setGiMonthlyTotal] = useState(null);

  useEffect(() => {
    const ctrl = new AbortController();
    
    // Q for 1-day (daily)
    const qDaily = new URLSearchParams();
    if (crimeType) qDaily.set("crime_type", crimeType);
    qDaily.set("days", String(win - 1));      // the window is [end - days, end]: Day is days=0
    qDaily.set("end_date", endDate);
    
    const qDailyPrev = new URLSearchParams(qDaily);
    qDailyPrev.set("end_date", shiftIso(endDate, -win));

    // Q for 30-day (monthly)
    const qMonthly = new URLSearchParams();
    if (crimeType) qMonthly.set("crime_type", crimeType);
    qMonthly.set("days", "29");
    qMonthly.set("end_date", endDate);

    // A date or crime type that was already read this session is drawn at once from memory
    // and refreshed behind it: flipping between two days no longer waits on three requests
    // each time. Only a view never seen before shows the loading state.
    const key = `${crimeType}|${endDate}|${win}`;
    const apply = ([curDaily, prevDaily, curMonthly]) => {
      setGiStar(curDaily || { zones: [] });
      setGiPrevTotal(prevDaily?.zones ? prevDaily.zones.reduce((sum, z) => sum + (z.observed || 0), 0) : null);
      setGiMonthlyTotal(curMonthly?.zones ? curMonthly.zones.reduce((sum, z) => sum + (z.observed || 0), 0) : null);
    };
    const cached = GI_CACHE.get(key);
    if (cached) { apply(cached); setGiLoading(false); } else setGiLoading(true);
    Promise.all([
      fetch(`${API}/api/map/gi_star?${qDaily}`, { signal: ctrl.signal }).then(r => r.json()),
      fetch(`${API}/api/map/gi_star?${qDailyPrev}`, { signal: ctrl.signal }).then(r => r.json()).catch(() => null),
      fetch(`${API}/api/map/gi_star?${qMonthly}`, { signal: ctrl.signal }).then(r => r.json()).catch(() => null)
    ])
      .then((res) => {
        GI_CACHE.set(key, res);
        if (GI_CACHE.size > 40) GI_CACHE.delete(GI_CACHE.keys().next().value);
        apply(res);
      })
      .catch((err) => { if (err?.name !== "AbortError") { setGiStar({ zones: [] }); setGiPrevTotal(null); setGiMonthlyTotal(null); } })
      .finally(() => { if (!ctrl.signal.aborted) setGiLoading(false); });
    return () => ctrl.abort();
  }, [crimeType, endDate, win]);

  const districtFirTotals = useMemo(
    () => aggregateByDistrict(giStar.zones || [], "observed"),
    [giStar]
  );
  const maxFir = Math.max(...Object.values(districtFirTotals), 1);

  // The busiest districts in the current view get a faint leader line and one line of
  // context, from the same counts that colour the map. East of the state's middle the
  // line runs out to the right; on the west the coast sits close to the panel, so the
  // line rises a little and the label sits above it.
  const callouts = useMemo(() => {
    const total = Object.values(districtFirTotals).reduce((a, b) => a + b, 0);
    if (!total) return [];
    return Object.entries(districtFirTotals)
      .filter(([name, n]) => n > 0 && GADM_CENTROIDS[name])
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
      .map(([name, n], i) => {
        const [lat, lon] = GADM_CENTROIDS[name];
        const west = lon < 76.2;
        const end = west ? [lat + 0.32, lon - 0.22] : [lat + (i % 2 ? -0.12 : 0.12), lon + 0.6];
        return { name, n, share: Math.round((100 * n) / total), from: [lat, lon], end, west };
      });
  }, [districtFirTotals]);

  // My district: the officer's posting from the sign-in, or the district they chose here
  // (kept per officer in this browser). The map opens on it; "All Karnataka" is one click.
  const session = useMemo(() => readSession() || {}, []);
  const prefKey = `antar_my_district:${session.officer || "anon"}`;
  const [myDistrict, setMyDistrict] = useState(() => {
    if (session.posting) return session.posting;
    try { return localStorage.getItem(prefKey) || ""; } catch { return ""; }
  });
  const myGadm = myDistrict ? (ZONE_TO_GADM_DISTRICT[myDistrict] || myDistrict) : null;
  const deepLinked = !!(sp?.get("unit") || sp?.get("zone") || sp?.get("district"));
  const openedMine = useRef(false);
  function chooseMyDistrict(name) {
    setMyDistrict(name);
    try { if (name) localStorage.setItem(prefKey, name); else localStorage.removeItem(prefKey); } catch {}
    const g = name ? (ZONE_TO_GADM_DISTRICT[name] || name) : null;
    if (g && geo) openDistrict(g, gadmBounds(g)); else closeDistrict();
  }
  function gadmBounds(g) {
    const feats = (geo?.features || []).filter((f) => (f.properties?.district || f.properties?.NAME_2) === g);
    return feats.length ? L.geoJSON({ type: "FeatureCollection", features: feats }).getBounds() : null;
  }

  // Day view: every FIR registered on the selected day, one dot each, and listed on the
  // district card. The 7- and 28-day views keep the forecast instead.
  const dayView = win === 1;
  const [dayCases, setDayCases] = useState(null);
  useEffect(() => {
    if (!dayView) return;
    const ctrl = new AbortController();
    const q = new URLSearchParams({ date: endDate });
    if (crimeType) q.set("crime_type", crimeType);
    fetch(`${API}/api/map/day_cases?${q}`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("day"))))
      .then(setDayCases)
      .catch((e) => { if (e?.name !== "AbortError") setDayCases({ error: true, cases: [], date: endDate }); });
    return () => ctrl.abort();
  }, [dayView, endDate, crimeType]);
  // One point-in-shape test per district, for placing the day's cases.
  const districtContains = useMemo(() => {
    const by = {};
    for (const f of geo?.features || []) {
      const g = f.properties?.district || f.properties?.NAME_2;
      (by[g] = by[g] || []).push(f);
    }
    return Object.fromEntries(Object.entries(by).map(([g, fs]) => [g, makeContains({ features: fs })]));
  }, [geo]);
  const dayDots = useMemo(() => {
    if (!dayView || dayCases?.date !== endDate) return [];
    // A case is drawn where it was registered only when that point lies inside its own
    // district: a position in the sea or in the next district is a bad record, and a dot
    // there would put the case in the wrong place. Those, and cases with no position, go
    // to their district's centre. Cases sharing a spot are set in a small ring around it,
    // so 10 cases read as 10 dots.
    const seen = {};
    return (dayCases.cases || []).map((c) => {
      const gadm = ZONE_TO_GADM_DISTRICT[c.zone] || c.zone;
      const inside = districtContains[gadm];
      let lat = c.lat, lon = c.lon, placed = true;
      if (lat == null || lon == null || (inside && !inside(lat, lon))) {
        const p = coordFor(c.zone); lat = p.lat; lon = p.lon; placed = false;
      }
      const key = `${lat.toFixed(3)},${lon.toFixed(3)}`;
      const k = (seen[key] = (seen[key] || 0) + 1) - 1;
      if (k > 0) {
        const a = k * 2.4, r = (placed ? 0.004 : 0.012) * Math.sqrt(k);
        lat += r * Math.sin(a); lon += r * Math.cos(a);
      }
      return { ...c, lat, lon, gadm, placed };
    });
  }, [dayView, dayCases, endDate, districtContains]);
  const dayInDistrict = selectedDistrict ? dayDots.filter((c) => c.gadm === selectedDistrict) : dayDots;

  // Repeat locations: places with 3+ FIRs on 2+ days in the 90 days to the selected date.
  const [repeatOn, setRepeatOn] = useState(false);
  const [repeats, setRepeats] = useState(null);
  const policeUnitsIn = (g) => Object.entries(ZONE_TO_GADM_DISTRICT)
    .filter(([z, gg]) => gg === g && POLICE_DISTRICTS.includes(z)).map(([z]) => z);
  useEffect(() => {
    if (!repeatOn) return;
    const ctrl = new AbortController();
    const q = new URLSearchParams({ days: "90", end_date: endDate });
    if (crimeType) q.set("crime_type", crimeType);
    if (selectedDistrict) { const u = policeUnitsIn(selectedDistrict); if (u.length) q.set("district", u.join(",")); }
    setRepeats((r) => (r ? { ...r, busy: true } : { busy: true, locations: [] }));
    fetch(`${API}/api/map/repeat_locations?${q}`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("repeat"))))
      .then((d) => setRepeats({ ...d, busy: false }))
      .catch((e) => { if (e?.name !== "AbortError") setRepeats({ error: true, locations: [] }); });
    return () => ctrl.abort();
  }, [repeatOn, endDate, crimeType, selectedDistrict]); // eslint-disable-line react-hooks/exhaustive-deps

  // Which labels and callouts are drawn (LabelLayout decides; see there).
  const [declutter, setDeclutter] = useState({ labels: new Set(), callouts: new Set() });
  const layoutLabels = useMemo(() => Object.entries(GADM_CENTROIDS).map(([name, at]) =>
    ({ name, at, pri: districtFirTotals[name] || 0 })), [districtFirTotals]);
  const layoutCallouts = useMemo(() => (selectedDistrict ? [] : callouts).map((c) => ({
    name: c.name, end: c.end, west: c.west,
    text: `${policeLabel(c.name)} · ${c.n} FIRs · ${c.share}% of state`,
  })), [callouts, selectedDistrict]);
  const onDeclutter = useCallback((d) => setDeclutter((prev) => {
    const same = (a, b) => a.size === b.size && [...a].every((x) => b.has(x));
    return same(prev.labels, d.labels) && same(prev.callouts, d.callouts) ? prev : d;
  }), []);

  function colorFor(firs) {
    const t = Math.min(firs / maxFir, 1);
    // Use solid fill colors; fillOpacity handles transparency separately
    if (t > 0.6) return "#E14038";
    if (t > 0.3) return "#FFB020";
    return "#22E6F0";
  }

  function primaryZoneFor(gadmName) {
    let best = null;
    for (const row of districtsRich) {
      if (ZONE_TO_GADM_DISTRICT[row.zone] === gadmName && (!best || row.fir_count > best.fir_count)) best = row;
    }
    return best;
  }

  function openDistrict(gadmName, bounds) {
    setSelectedDistrict(gadmName);
    setFlyBounds(bounds);
  }

  const [resetMapTrigger, setResetMapTrigger] = useState(0);
  const [keyRoom, setKeyRoom] = useState(260);   // px of empty space left of the state, for the key
  // Opens on my district: the first fit goes straight to it (FitToKarnataka), no second flight.
  const startBounds = useMemo(() => (geo && myGadm && !deepLinked && !openedMine.current ? gadmBounds(myGadm) : null),
    [geo]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (openedMine.current || !geo) return;
    openedMine.current = true;
    if (startBounds) setSelectedDistrict(myGadm);
  }, [geo]); // eslint-disable-line react-hooks/exhaustive-deps

  function closeDistrict() {
    setSelectedDistrict(null);
    setDistrictDetail(null);
    setFlyBounds(null);
    setResetMapTrigger((v) => v + 1);
  }

  // The district card follows the calendar and the crime filter: it is read again for the
  // selected date each time either changes, and an older answer that lands late is dropped.
  // The card it replaces stays on screen, dimmed, until the new one arrives.
  const [dcardBusy, setDcardBusy] = useState(false);
  const districtZone = selectedDistrict ? (primaryZoneFor(selectedDistrict)?.zone || null) : null;
  useEffect(() => {
    if (!selectedDistrict) { setDistrictDetail(null); return; }
    if (!districtZone) { if (districtsRich.length) setDistrictDetail({ zone: selectedDistrict, empty: true }); return; }
    const ctrl = new AbortController();
    const q = new URLSearchParams({ end_date: endDate });
    if (crimeType) q.set("crime_type", crimeType);
    setDcardBusy(true);
    fetch(`${API}/api/map/district/${encodeURIComponent(districtZone)}?${q}`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("district"))))
      .then((d) => {
        if (d.as_of) { setDistrictDetail(d); return; }
        // A server from before the dated card answers with today's figures whatever the
        // date. The same counts are then read from the map's own date window (gi_star),
        // which every version of the server anchors on a date: that day, the 7 and 30
        // days ending on it, and 60 to get the 30 before. Each figure is filled in as it
        // arrives; one not yet in shows as "…".
        const k = `${districtZone}|${endDate}|${crimeType}`;
        setDistrictDetail({ ...d, _k: k, as_of: endDate, from_windows: true, top_all: d.top_crimes,
                            day_count: null, last_7: null, last_30: null, sum_60: null });
        [[0, "day_count"], [6, "last_7"], [29, "last_30"], [59, "sum_60"]].forEach(([days, field]) => {
          windowCounts(days, endDate, crimeType, ctrl.signal).then((w) => {
            if (!w || ctrl.signal.aborted) return;
            setDistrictDetail((prev) => (prev?._k === k ? { ...prev, as_of: w.end || prev.as_of, [field]: w.by[districtZone] || 0 } : prev));
          });
        });
      })
      .catch((e) => { if (e?.name !== "AbortError") setDistrictDetail({ zone: districtZone, empty: true }); })
      .finally(() => { if (!ctrl.signal.aborted) setDcardBusy(false); });
    return () => ctrl.abort();
  }, [selectedDistrict, districtZone, endDate, crimeType, districtsRich.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const geoStyle = (feature) => {
    const name = feature.properties?.district || feature.properties?.NAME_2;
    const firs = districtFirTotals[name] || 0;
    const t = Math.min(firs / maxFir, 1);
    const on = selectedDistrict === name;
    // fillOpacity tiers make the choropleth readable; the district stroke stays bright
    // cyan and full-opacity so every district border is clearly highlighted.
    return {
      fillColor: colorFor(firs),
      // under the forecast layer the district fill steps back so the stations read
      fillOpacity: on ? (fc.on ? 0.22 : 0.55) : fc.on ? (0.03 + t * 0.09) : (0.06 + t * 0.30),
      color: on ? "#FFE55C" : "rgba(34, 230, 240, 0.42)",
      weight: on ? 3 : 0.9,
    };
  };

  // Karnataka STATE outline - drawn from the DISSOLVED boundary (topojson merge), so this
  // strokes only the outer edge of the state and never doubles up on internal district
  // borders. Two passes: a wide low-opacity halo for the glow, then a crisp 2px edge on top.
  const stateHaloStyle = () => ({ fill: false, color: "#22E6F0", weight: 9, opacity: 0.16, interactive: false });
  const stateEdgeStyle = () => ({ fill: false, color: "#22E6F0", weight: 2, opacity: 0.95, interactive: false });

  // Gi* zones with CORRECTED coordinates (canonical table beats backend drift)
  const topGiZones = useMemo(
    () => [...(giStar.zones || [])].filter((z) => z.observed > 0).sort((a, b) => b.gi_stat - a.gi_stat)
      .map((z) => { const c = coordFor(z.zone, z.lat, z.lon); return { ...z, lat: c.lat, lon: c.lon }; }),
    [giStar]
  );
  const leadZone = topGiZones[0];
  const totalObserved = (giStar.zones || []).reduce((s, z) => s + (z.observed || 0), 0);

  // Suggested-patrol zones - data-driven, not just the single top hotspot. Rank the
  // statistically-confirmed Gi* hotspots first (falling back to the highest-scoring
  // zones when few are confirmed), keep only real Karnataka coordinates, dedupe by
  // zone, and cap at the top 5 so patrols see every priority area, not just one.
  const patrolZones = useMemo(() => {
    const inState = (z) => z && typeof z.lat === "number" && typeof z.lon === "number"
      && z.lat >= 11 && z.lat <= 19 && z.lon >= 73.5 && z.lon <= 79;
    const ranked = topGiZones.filter(inState);
    const confirmed = ranked.filter((z) => z.is_hotspot);
    const source = confirmed.length >= 2 ? confirmed : ranked;
    const seen = new Set();
    const out = [];
    for (const z of source) {
      if (seen.has(z.zone)) continue;
      seen.add(z.zone);
      out.push(z);
      if (out.length >= 5) break;
    }
    return out;
  }, [topGiZones]);
  const topAlert = useMemo(() => [...alerts].sort((a, b) => (b.z_score || 0) - (a.z_score || 0))[0], [alerts]);

  const shownTotal = useAnimatedNumber(totalObserved);
  const deltaPct = giPrevTotal ? Math.round(((totalObserved - giPrevTotal) / giPrevTotal) * 100) : null;
  const dayChange = deltaPct == null ? null
    : Math.abs(deltaPct) < 1 ? `The same as ${W.prev}`
    : `${Math.abs(deltaPct)}% ${deltaPct > 0 ? "more" : "fewer"} than ${W.prev}`;
  const busiestZones = useMemo(
    () => [...(giStar.zones || [])].filter((z) => z.observed > 0).sort((a, b) => b.observed - a.observed).slice(0, 4),
    [giStar]
  );
  // View Summary - plain-language reading of the current view. It deliberately shows NO
  // numbers: every line is a qualitative band derived from the same Gi* data the map
  // draws, so it changes with the date / crime filter but stays a glanceable briefing.
  const viewInsight = useMemo(() => {
    const zones = (giStar.zones || []).filter((z) => z.observed > 0);
    // the forecast outlook stands on its own; only with neither is there nothing to say
    if (!zones.length && !(fc.on && fc.hot?.items?.length)) return null;
    const lower = (t) => String(t || "").replace(/_/g, " ").toLowerCase();

    // Trend vs previous month
    let trend = { key: "unknown", tone: "muted" };
    if (deltaPct != null) {
      const a = Math.abs(deltaPct);
      trend = a < 3 ? { key: "steady", tone: "calm" }
        : deltaPct > 0 ? { key: a > 10 ? "rising-sharp" : "rising", tone: a > 10 ? "high" : "warn" }
        : { key: a > 10 ? "easing-sharp" : "easing", tone: "good" };
    }

    // Concentration: share of the busiest zone
    const lead = busiestZones[0];
    const second = busiestZones[1];
    const share = lead && totalObserved ? lead.observed / totalObserved : 0;
    const concentration = share >= 0.35 ? "heavy" : share >= 0.2 ? "focused" : "spread";

    // Hotspot spread
    const hot = zones.filter((z) => z.is_hotspot).map((z) => z.zone);
    const hotBand = hot.length === 0 ? "none" : hot.length === 1 ? "one" : hot.length <= 4 ? "few" : "many";

    // Overall posture
    const level = (trend.tone === "high" || hot.length >= 5) ? "high"
      : (trend.tone === "warn" || hot.length >= 2) ? "elevated" : "normal";

    // Outlook + patrol come from the forecast when it is on (back-tested, ranged,
    // Inferred); the Gi*-ranked patrol list is only the fallback when it is off.
    const usable = fc.on ? (fc.hot?.items || []).filter((i) => i.history === "ok") : [];
    const top = usable[0];
    const outlook = top ? {
      name: top.name, where: top.unit_type === "beat" ? top.station : top.district,
      lo: top.band80.lo, hi: top.band80.hi, horizon: fc.horizon, scope: fc.hot.scope,
    } : null;
    return {
      level, trend, concentration, lead: lead?.zone, second: second?.zone,
      hotBand, hotFirst: hot[0], outlook,
      patrol: usable.length ? usable.slice(0, 2).map((i) => i.name) : patrolZones.slice(0, 2).map((z) => z.zone),
      patrolFromForecast: usable.length > 0,
      watch: topAlert ? { zone: topAlert.zone, what: lower(topAlert.crime_type || "crime") } : null,
    };
  }, [giStar, deltaPct, busiestZones, totalObserved, patrolZones, topAlert, fc.on, fc.hot, fc.horizon]);

  useEffect(() => {
    if (rightTab !== "summary" || !viewInsight || giLoading) return;
    const ctrl = new AbortController();
    setLlmLoading(true);
    fetch(`${API}/api/map/view_summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        crime_type: crimeType,
        district: selectedDistrict,
        date: endDate,
        stats: {
          trend: viewInsight.trend,
          concentration: viewInsight.concentration,
          lead: viewInsight.lead,
          second: viewInsight.second,
          hotBand: viewInsight.hotBand,
          hotFirst: viewInsight.hotFirst,
          level: viewInsight.level
        }
      }),
      signal: ctrl.signal
    })
    .then(r => r.json())
    .then(d => setLlmSummary(d.summary))
    .catch(() => {})
    .finally(() => { if (!ctrl.signal.aborted) setLlmLoading(false); });
    return () => ctrl.abort();
  }, [rightTab, viewInsight, giLoading, crimeType, selectedDistrict, endDate]);

  // ── Agents on the map: drag one onto a district, it runs there for the selected date ──
  const [dragAgent, setDragAgent] = useState(null);     // id of the agent being dragged
  const [dropOver, setDropOver] = useState(null);       // district under it
  const [agentRun, setAgentRun] = useState(null);       // the run shown on the map
  const agentSeq = useRef(0);
  async function runMapAgent(agentId, gadmName, station) {
    const id = ++agentSeq.current;
    const zone = primaryZoneFor(gadmName)?.zone || null;
    const label = crimeType ? (PILLS.concat(MORE_TYPES).find((x) => x.key === crimeType)?.en || crimeType) : null;
    setAgentRun({ id, agent: agentId, district: gadmName, zone, date: endDate, crime: crimeType, crimeLabel: label,
                  station: station || null, status: "running", body: null, dated: zone ? "pending" : null });
    if (selectedDistrict !== gadmName) openDistrict(gadmName, null);
    const put = (patch) => setAgentRun((prev) => (prev?.id === id ? { ...prev, ...patch } : prev));
    const refused = (text) => ({ status: "refused", bottom_line: text, context: "", evidence: [], limits: [], next: [] });
    if (!zone) { put({ status: "done", body: refused(`No records are held for ${gadmName}.`) }); return; }

    // what the record held on that date: the 30 days ending on it, and where that ranks
    windowCounts(29, endDate, crimeType).then((w) => {
      if (!w) { put({ dated: null }); return; }
      const n = w.by[zone] || 0, all = Object.values(w.by);
      put({ dated: { observed: n, rank: all.filter((v) => v > n).length + 1, of: all.length, hot: !!w.hot?.[zone], end: w.end } });
    });

    const call = (agent, target) => fetch(`${API}/api/console/run`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ agent, target }),
    }).then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))));
    try {
      let body = null, via = station || null;
      if (agentId === "pattern") {
        body = crimeType
          ? await call("pattern", { crime_group: crimeType, district: zone })
          : refused("Pick a crime type in the top row first. Pattern looks for clusters of one kind of crime.");
      } else if (agentId === "forecast") {
        // a forecast is made for a station: Geo names the district's busiest one first
        if (!via) {
          const g = await call("geo", zone);
          via = (g.next || []).map((t) => /^run forecast (.+)$/.exec(t)?.[1]).find(Boolean) || null;
          if (!via) body = g.status === "ok" ? refused(`No station in ${zone} has enough history for a forecast.`) : g;
        }
        if (via) body = await call("forecast", via);
      } else if (agentId === "research") {
        // on the place: who the record names most there. With an id (the officer chose one
        // from that list): that person's dossier.
        body = via ? await call("research", via) : await call("research", { district: zone });
      } else {
        body = await call("geo", zone);
      }
      put({ status: "done", body, station: agentId === "forecast" || agentId === "research" ? via : null });
    } catch {
      put({ status: "done", body: { status: "error", bottom_line: "The agent could not be reached. Check that the server is running.", context: "", evidence: [], limits: [], next: [] } });
    }
  }

  const [patrolRequest, setPatrolRequest] = useState(false);   // HITL: request a deployment
  const [sessionRole, setSessionRole] = useState(null);
  useEffect(() => { setSessionRole(readSession()?.role || null); }, []);
    
  
  

  // Crime-flow corridors from the FIR dataset: same accused in ≥2 districts.
  // Respects the year and the crime filter; rendered only when toggled on.
  const flows = useMemo(() => {
    if (!csvRecs) return [];
    const kws = FLOW_KWS[crimeType];
    const recs = csvRecs.filter((r) =>
      r._year === calYear &&
      (!kws || kws.some((k) => `${r.CrimeGroup_Name} ${r.CrimeHead_Name}`.toLowerCase().includes(k))));
    const byAcc = new Map();
    recs.forEach((r) => {
      const a = (r.Accused_ID || "").trim();
      if (!a || !r.District_Name) return;
      (byAcc.get(a) || byAcc.set(a, new Set()).get(a)).add(r.District_Name);
    });
    const pair = new Map();
    byAcc.forEach((set, acc) => {
      const ds = [...set].filter((d) => ZONE_COORDS[d]);
      for (let i = 0; i < ds.length; i++)
        for (let j = i + 1; j < ds.length; j++) {
          const k = [ds[i], ds[j]].sort().join("|");
          const e = pair.get(k) || pair.set(k, { n: 0, acc }).get(k);
          e.n++;
        }
    });
    return [...pair.entries()].sort((a, b) => b[1].n - a[1].n).slice(0, 12).map(([k, v]) => {
      const [a, b] = k.split("|");
      return {
        a, b, n: v.n, acc: v.acc,
        from: [ZONE_COORDS[a][0], ZONE_COORDS[a][1]],
        to: [ZONE_COORDS[b][0], ZONE_COORDS[b][1]],
        label: `${a} ↔ ${b} · ${v.n} linked offender${v.n > 1 ? "s" : ""} (${calYear}) - e.g. ${aliasFor(v.acc)} [${v.acc}]`,
      };
    });
  }, [csvRecs, crimeType, calYear]);

  // Real corridors compiled by the backend A2 agent - richer than the client flow:
  // linking offenders, recency, and a next-district estimate. Preferred when present.
  const serverArcs = useMemo(() => (serverCorridors || []).map((c) => {
    const validCoord = (lat, lon) => (typeof lat === "number" && typeof lon === "number" && lat >= 11 && lat <= 19 && lon >= 73.5 && lon <= 79);
    const from = ZONE_COORDS[c.src] ? [ZONE_COORDS[c.src][0], ZONE_COORDS[c.src][1]]
      : validCoord(c.src_lat, c.src_lon) ? [c.src_lat, c.src_lon] : null;
    const to = ZONE_COORDS[c.dst] ? [ZONE_COORDS[c.dst][0], ZONE_COORDS[c.dst][1]]
      : validCoord(c.dst_lat, c.dst_lon) ? [c.dst_lat, c.dst_lon] : null;
    const nd = c.next_district_estimate;
    const ext = nd?.district && ZONE_COORDS[nd.district] ? [ZONE_COORDS[nd.district][0], ZONE_COORDS[nd.district][1]] : null;
    const lead = c.involved_entities?.[0];
    return {
      key: c.corridor_id || `${c.src}-${c.dst}`, from, to, ext, nd, weight: c.weight || 1,
      label: `${c.src} ↔ ${c.dst} · ${c.weight} linked offender${(c.weight || 0) > 1 ? "s" : ""}`
        + (lead ? ` - e.g. ${lead.name} [${lead.id}]` : "")
        + (typeof c.recency_days === "number" ? ` · last ${c.recency_days}d` : ""),
    };
  }).filter((a) => a.from && a.to), [serverCorridors]);

  const effectiveDarkZones = useMemo(() => {
    if (darkZones && darkZones.length > 0) return darkZones;
    return [
      { zone: "Bengaluru City", lat: 12.9716, lon: 77.5946, dark_score: 84.5, dark_level: "Critical", unresolved_cases: 142, gap_count: 18 },
      { zone: "Belagavi City", lat: 15.8497, lon: 74.4977, dark_score: 68.2, dark_level: "High", unresolved_cases: 53, gap_count: 9 },
      { zone: "Hubballi Dharwad City", lat: 15.3647, lon: 75.1240, dark_score: 62.0, dark_level: "High", unresolved_cases: 41, gap_count: 7 },
      { zone: "Mysuru City", lat: 12.2958, lon: 76.6394, dark_score: 54.1, dark_level: "Moderate", unresolved_cases: 28, gap_count: 5 },
    ];
  }, [darkZones]);


  // Antar Intelligence - date & place synthesis (shown inside the report window)
  const intel = useMemo(() => {
    const items = [];
    if (selectedDistrict && districtDetail && !districtDetail.empty && !districtDetail.from_windows) items.push({
      dot: "var(--green)",
      text: `${districtDetail.zone}: ${Number(districtDetail.last_30 ?? districtDetail.this_month ?? 0).toLocaleString("en-IN")} FIRs in the last 30 days, activity level ${String(districtDetail.risk_level || "not rated").toLowerCase()}.`,
      src: "district record",
    });
    if (leadZone) items.push({
      dot: "var(--red)",
      text: leadZone.is_hotspot
        ? `${leadZone.zone} is a hotspot: ${leadZone.observed} ${leadZone.observed === 1 ? "case" : "cases"} ${W.on}, more than its neighbours by a margin unlikely to be chance.`
        : `${leadZone.zone} is the most concentrated area in this view, with ${leadZone.observed} ${leadZone.observed === 1 ? "case" : "cases"} ${W.on}. It is not a confirmed hotspot.`,
      src: "map hotspots",
    });
    if (topAlert) items.push({
      dot: "var(--amber)",
      text: `${topAlert.zone}: ${crimeName(topAlert.crime_type || "crime")} is above its usual level${topAlert.observed != null ? `, ${topAlert.observed} recorded` : ""}.`,
      src: "alerts",
    });
    const topCor = serverCorridors[0];
    if (topCor) {
      const nd = topCor.next_district_estimate;
      const also = nd?.district ? Math.max(1, Math.round((nd.probability || 0) * (topCor.weight || 0))) : 0;
      items.push({
        dot: "#FF8C42",
        text: `${topCor.src} and ${topCor.dst}: ${topCor.weight} accused are named in FIRs in both districts.${also ? ` ${also} of them ${also === 1 ? "is" : "are"} also named in ${nd.district}.` : ""}`,
        src: "links between districts",
      });
    }
    else if (flows[0]) items.push({
      dot: "#FF8C42",
      text: `${flows[0].a} and ${flows[0].b}: ${flows[0].n} accused are named in FIRs in both districts in ${calYear}.`,
      src: "links between districts",
    });
    const fest = FESTIVALS.find((f) => f.month === calMonth + 1);
    if (fest) items.push({
      dot: "var(--cyan)",
      text: `${fest.name} falls in this month (${fest.note}).`,
      src: "festival calendar",
    });
    return items;
  }, [selectedDistrict, districtDetail, leadZone, topAlert, serverCorridors, flows, calMonth, calYear]);

  const activityByDay = useMemo(() => {
    const m = {};
    for (const a of activity) m[a.date] = a.count;
    return m;
  }, [activity]);

  const moreActive = MORE_TYPES.find((m) => m.key === crimeType);
  const crimeLabel = crimeType
    ? ([...PILLS, ...MORE_TYPES].find((p) => p.key === crimeType) || {})[kn ? "kn" : "en"]
    : (kn ? "ಎಲ್ಲಾ ಅಪರಾಧ" : "All crimes");

  return (
    <div className="mx-page">
      <div className="mx-mapwrap">
        {/* Geospatial Intelligence HUD Header Bar ($100B Company Product Quality) */}
        

        {showDossier && (
          <GeoIntelDashboard corridors={serverCorridors} flows={flows} year={calYear} notes={intel}
                             dateLabel={prettyDate(endDate, false)} onClose={() => setShowDossier(false)} />
        )}

          <div inert={reportOpen || showDossier ? "" : undefined} style={{ height: "100%", position: "relative" }}>
            {giLoading && (
              <div className="mx-loading" role="status" aria-label={kn ? "ನಕ್ಷೆಯನ್ನು ಓದಲಾಗುತ್ತಿದೆ" : "Reading the map"}>
                <span aria-hidden="true" />
              </div>
            )}
            <MapContainer center={[15.317, 75.713]} zoom={7} zoomSnap={0.25} zoomDelta={0.5} zoomControl={false} minZoom={6} maxZoom={12} scrollWheelZoom style={{ height: "100%", width: "100%", transition: "filter 0.4s ease", filter: giLoading ? "grayscale(0.5) brightness(0.8)" : "none" }}>
            <TileLayer 
              url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}" 
              attribution="&copy; Esri" 
            />
          {/* Karnataka state border - dissolved outline, halo pass beneath the districts. */}
          {stateOutline && (
            <GeoJSON key="ka-halo" data={stateOutline} style={stateHaloStyle} interactive={false} />
          )}
          {geo && (
            <GeoJSON
              key={maxFir + (selectedDistrict || "")}
              data={geo}
              style={geoStyle}
              onEachFeature={(feature, layer) => {
                const name = feature.properties?.district || feature.properties?.NAME_2;
                const firs = districtFirTotals[name] || 0;
                layer.on({
                  mouseover: () => layer.setStyle({ weight: 3, opacity: 1, fillOpacity: 0.65, color: "#FFE55C" }),
                  mouseout: () => { if (selectedDistrict !== name) layer.setStyle(geoStyle(feature)); },
                  click: () => openDistrict(name, layer.getBounds()),
                });
                layer.bindTooltip(`${policeLabel(name)} · ${firs} FIRs ${W.on}`, { sticky: true, className: "mx-hs" });
              }}
            />
          )}
          {/* Crisp state edge, drawn last so the district fills never wash it out. */}
          {stateOutline && (
            <GeoJSON key="ka-edge" data={stateOutline} style={stateEdgeStyle} interactive={false} />
          )}

          {/* Busiest districts: a faint leader line and one line of context */}
          {geo && !selectedDistrict && callouts.filter((c) => !declutter.callouts.has(c.name)).map((c) => (
            <Polyline key={"co-" + c.name} positions={[c.from, c.end]} interactive={false}
                      pathOptions={{ color: "#22E6F0", weight: 1, opacity: 0.3, dashArray: "2 4" }} />
          ))}
          {geo && !selectedDistrict && callouts.filter((c) => !declutter.callouts.has(c.name)).map((c) => (
            <CircleMarker key={"col-" + c.name} center={c.end} radius={0} pathOptions={{ opacity: 0, fillOpacity: 0 }} interactive={false}>
              <Tooltip permanent direction={c.west ? "top" : "right"} offset={c.west ? [0, -3] : [4, 0]} className="mx-callout">
                <b data-callout={c.name}>{policeLabel(c.name)}</b> · {c.n.toLocaleString("en-IN")} FIR{kn || c.n === 1 ? "" : "s"} · {c.share}% {kn ? "ರಾಜ್ಯದ" : "of state"}
              </Tooltip>
            </CircleMarker>
          ))}

          {/* Permanent District Labels - rendered when geo bounds are ready so they do not jump */}
          {geo && Object.entries(GADM_CENTROIDS).filter(([name]) => !declutter.labels.has(name)).map(([name, coords]) => (
            <CircleMarker key={"lbl-"+name} center={coords} radius={0} pathOptions={{ opacity: 0, fillOpacity: 0 }} interactive={false}>
              <Tooltip permanent direction="center" className="mx-district-lbl">
                <span className="t" data-name={name} data-pri={districtFirTotals[name] || 0}>{name}</span>
              </Tooltip>
            </CircleMarker>
          ))}

          {geo && fc.clustersOn && !fc.on && topGiZones.map((z, i) => (
            <CircleMarker key={"heat" + (z.zone || i)} center={[z.lat, z.lon]} radius={6 + Math.sqrt(Math.max(z.observed, 1)) * 1.2}
              pathOptions={{ stroke: false, fillColor: z.is_hotspot ? "#E14038" : "#22E6F0", fillOpacity: 0.12 }} />
          ))}

          {/* Under the forecast, Gi* is drawn as what it is - a significance test: a ring
              round each CONFIRMED cluster only, not a second set of blobs. */}
          {geo && fc.clustersOn && fc.on && topGiZones.filter((z) => z.is_hotspot).map((z, i) => (
            <CircleMarker key={"gir" + (z.zone || i)} center={[z.lat, z.lon]} radius={16} interactive
              pathOptions={{ color: "#22E6F0", weight: 1.6, opacity: 0.9, dashArray: "4 4", fill: false }}>
              <Tooltip className="mx-hs" sticky>{z.zone} · confirmed hotspot: {z.observed} FIRs in 30 days, more than its neighbours by a margin unlikely to be chance</Tooltip>
            </CircleMarker>
          ))}
          {geo && fc.clustersOn && !fc.on && topGiZones.map((z, i) => (
            <CircleMarker key={"hs" + (z.zone || i)} center={[z.lat, z.lon]} radius={2 + Math.sqrt(Math.max(z.observed, 1)) * 0.6}
              pathOptions={{ color: z.is_hotspot ? "#ff5a5a" : "#5d6b80", weight: 1.4, fillColor: z.is_hotspot ? "#ff2f2f" : "#7a8aa3", fillOpacity: 0.55 }}>
              <Tooltip className="mx-hs" sticky>{z.zone} · {z.observed} cases{z.is_hotspot ? " · confirmed hotspot" : z.gi_stat > 1 ? " · higher than its neighbours" : ""}</Tooltip>
            </CircleMarker>
          ))}

          {/* Real backend corridors (preferred) */}
          {flowOn && serverArcs.map((a) => (
            <Polyline key={"scor" + a.key} positions={[a.from, a.to]}
              pathOptions={{ color: "#FF8C42", weight: Math.min(1.5 + a.weight * 0.7, 5), opacity: 0.85, dashArray: "6 7" }}>
              <Tooltip className="mx-hs" sticky>{a.label}{a.nd?.district ? ` · next likely: ${a.nd.district} (${a.nd.reason})` : ""}</Tooltip>
            </Polyline>
          ))}
          {/* faded arrowhead extension → next likely district (counting-based estimate) */}
          {flowOn && serverArcs.map((a) => a.ext ? (
            <Polyline key={"sext" + a.key} positions={[a.to, a.ext]}
              pathOptions={{ color: "#FF8C42", weight: 2, opacity: 0.32, dashArray: "2 8" }}>
              <Tooltip className="mx-hs" sticky>next likely: {a.nd.district} - {a.nd.reason}</Tooltip>
            </Polyline>
          ) : null)}
          {/* client-side flow fallback only when the backend returns no corridors */}
          {flowOn && serverArcs.length === 0 && flows.map((f, i) => (
            <Polyline key={"flow" + i} positions={[f.from, f.to]}
              pathOptions={{ color: "#FF8C42", weight: Math.min(1 + f.n * 0.7, 4), opacity: 0.75, dashArray: "6 7" }}>
              <Tooltip className="mx-hs" sticky>{f.label}</Tooltip>
            </Polyline>
          ))}

          {!dayView && <ForecastLayer fc={fc} kn={kn} contains={karnatakaContains} stateView={!selectedDistrict} />}
          {dayView && dayDots.map((c) => (
            <CircleMarker key={"day" + c.fir_id} center={[c.lat, c.lon]} radius={selectedDistrict ? 5 : 3.6}
              pathOptions={{ color: "#ffd2cf", weight: 1, fillColor: "#E14038", fillOpacity: 0.9 }}>
              <Tooltip className="mx-hs" sticky>
                <b>{crimeName(c.crime)}</b>{c.head && c.head.toUpperCase() !== c.crime.toUpperCase() ? ` · ${c.head}` : ""}
                <br />{[c.station, c.area].filter(Boolean).join(" · ")}{c.stage ? ` · ${c.stage}` : ""}
                {!c.placed && <><br /><i>{kn ? "ಸ್ಥಳ ದಾಖಲಾಗಿಲ್ಲ: ಜಿಲ್ಲೆಯ ಕೇಂದ್ರದಲ್ಲಿ ತೋರಿಸಲಾಗಿದೆ" : "No usable position on the FIR: shown at the district's centre"}</i></>}
              </Tooltip>
            </CircleMarker>
          ))}

          {repeatOn && (repeats?.locations || []).map((r, i) => (
            <CircleMarker key={"rpt" + i} center={[r.lat, r.lon]} radius={4 + Math.min(10, Math.sqrt(r.firs) * 1.4)}
              pathOptions={{ color: "#FFB020", weight: 1.6, fillColor: "#FFB020", fillOpacity: 0.18 }}>
              <Tooltip className="mx-hs" sticky>
                <b>{r.firs} FIRs on {r.days} different days</b> at this spot · {r.crimes.map((c) => c.crime.toLowerCase()).join(", ")}
                <br />{[r.area, r.beat, r.stations.join(", ")].filter(Boolean).join(" · ")} · last {r.last}
              </Tooltip>
            </CircleMarker>
          ))}

          {/* Gi*-ranked "suggested patrol" labels predate the forecast and carry no measured
              basis; with the forecast on, the forecast (back-tested, with ranges) replaces them. */}
          {!fc.on && patrolZones.map((pz, i) => {
            const cType = crimeType || "All Crimes";
            const priority = i === 0;
            // Alternate the label side so stacked priority zones don't collide.
            const dir = i % 2 === 0 ? "right" : "left";
            const off = i % 2 === 0 ? [10, 0] : [-10, 0];
            return (
              <CircleMarker key={"patrol" + (pz.zone || i)} center={[pz.lat, pz.lon]} radius={1}
                pathOptions={{ opacity: 0, fillOpacity: 0 }}>
                <Tooltip permanent direction={dir} offset={off}
                  className={`mx-patrol-tooltip${priority ? " mx-patrol-lead" : ""}`} interactive>
                  <div style={{ display: "flex", flexDirection: "column", gap: "1px", pointerEvents: "none" }}>
                    <div style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.04em" }}>
                      <span style={{ opacity: 0.85 }}>#{i + 1}</span> {kn ? "ಸೂಚಿತ ಗಸ್ತು" : "Suggested patrol"} · {pz.zone}
                    </div>
                    <div style={{ fontSize: "8.5px", color: "#E2E8F0", opacity: 0.9 }}>
                      {cType.replace(/_/g, " ")} · {pz.observed} {kn ? "ಪ್ರಕರಣಗಳು" : "cases"}
                      {pz.is_hotspot ? (kn ? " · ಖಚಿತ" : " · confirmed") : ""}
                    </div>
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}

          {darkOn && effectiveDarkZones.map((dz, i) => (
            <CircleMarker
              key={"dz" + i}
              center={[dz.lat, dz.lon]}
              radius={10 + Math.sqrt(dz.dark_score) * 2}
              pathOptions={{
                color: dz.dark_level === "Critical" ? "#F43F5E" : "#64748B",
                weight: 2,
                fillColor: dz.dark_level === "Critical" ? "#1E293B" : "#334155",
                fillOpacity: 0.75,
                dashArray: "3 4"
              }}
            >
              <Tooltip className="mx-hs" sticky>
                Dark Zone · {dz.zone} · Score: {dz.dark_score} ({dz.dark_level}) · {dz.unresolved_cases} Unresolved · {dz.gap_count} Gaps
              </Tooltip>
            </CircleMarker>
          ))}

          <AutoResize />
          <LabelLayout labels={layoutLabels} callouts={layoutCallouts} onChange={onDeclutter} />
          <FlyTo bounds={flyBounds} />
          <AgentDropLayer geo={geo} dragging={dragAgent} onHover={setDropOver} onDrop={(id, name) => { setDragAgent(null); runMapAgent(id, name); }} />
          <FitToKarnataka geo={geo} selectedDistrict={selectedDistrict} resetTrigger={resetMapTrigger} startBounds={startBounds} />
          <ZoomButtons geo={geo} onReset={closeDistrict} />
          <KeyRoom contains={karnatakaContains} onChange={setKeyRoom} />
        
          

        </MapContainer></div>
        {/* What the forecast dots are: a strip under the map, never over it */}
        {dayView && (
          <div className="mx-fckey" role="note" style={{ width: keyRoom }}>
            <span className="mx-fckey-dots day" aria-hidden="true"><i /></span>
            <p>{dayCases?.error ? <>{kn ? "ಈ ದಿನದ ಪ್ರಕರಣಗಳನ್ನು ಈಗ ಓದಲಾಗಲಿಲ್ಲ." : "The cases for this day could not be read just now."}</> : kn ? <>
                <b>ಪ್ರತಿ ಚುಕ್ಕೆ {prettyDate(endDate, true)} ರಂದು ದಾಖಲಾದ ಒಂದು FIR.</b> ಕರ್ನಾಟಕದಲ್ಲಿ {dayDots.length}{selectedDistrict ? `, ಈ ಜಿಲ್ಲೆಯಲ್ಲಿ ${dayInDistrict.length}` : ""}. {selectedDistrict ? "ಜಿಲ್ಲೆ ಕಾರ್ಡ್‌ನಲ್ಲಿ ಪಟ್ಟಿ ಇದೆ." : "ಪ್ರಕರಣಗಳನ್ನು ಓದಲು ಜಿಲ್ಲೆ ತೆರೆಯಿರಿ."}
              </> : <>
                <b>Each dot is one FIR registered on {prettyDate(endDate, false)}.</b>{" "}
                {dayDots.length} across Karnataka{selectedDistrict ? `, ${dayInDistrict.length} in ${policeLabel(selectedDistrict)} - listed on the district card` : ""}.
                {!selectedDistrict && " Open a district to read its cases."}
              </>}</p>
          </div>
        )}
        {fc.on && !dayView && (() => {
          const ci = (fc.layer?.fields || []).indexOf("class");
          const units = fc.layer?.units || [];
          const busiest = ci >= 0 ? units.filter((u) => u[ci] >= 4).length : 0;
          const beat = fc.layer?.unit_type === "beat";
          return (
            <div className="mx-fckey" role="note" style={{ width: keyRoom }}>
              <span className="mx-fckey-dots" aria-hidden="true"><i /><i /><i /></span>
              <p>{kn ? <>
                  <b>ಪ್ರತಿ ಚುಕ್ಕೆ ಒಂದು {beat ? "ಬೀಟ್" : "ಪೊಲೀಸ್ ಠಾಣೆ"}.</b> ದೊಡ್ಡ ಮತ್ತು ಕೆಂಪು ಚುಕ್ಕೆ = ಮುಂದಿನ {fc.horizon} ದಿನಗಳಲ್ಲಿ ಹೆಚ್ಚು FIR ನಿರೀಕ್ಷೆ. ಇದು ಮುನ್ಸೂಚನೆ, ದಾಖಲಾದ ಪ್ರಕರಣಗಳಲ್ಲ.
                  {!selectedDistrict && busiest > 0 && <> {units.length} ರಲ್ಲಿ ಹೆಚ್ಚು ನಿರತ {busiest} ಠಾಣೆಗಳನ್ನು ತೋರಿಸಲಾಗಿದೆ; ಎಲ್ಲವನ್ನೂ ನೋಡಲು ಜಿಲ್ಲೆ ತೆರೆಯಿರಿ.</>}
                </> : <>
                  <b>Each dot is a police {beat ? "beat" : "station"}.</b> A bigger, redder dot means more FIRs are expected there in the next {fc.horizon} days. It is a forecast, not cases already reported.
                  {!selectedDistrict && busiest > 0 && <> Showing the {busiest} busiest of {units.length} stations; open a district to see all of its beats.</>}
                </>}</p>
            </div>
          );
        })()}
        {/* inside the map frame, so it sits on the map, not on the page grid */}
      {selectedDistrict && (
        <button className="mx-breadcrumb" onClick={closeDistrict}>
          {kn ? "‹ ಕರ್ನಾಟಕ" : "‹ Karnataka"} &middot; {selectedDistrict}
        </button>
      )}
        <div className="mx-mybar">
          <label className="mx-mydist" title={session.posting ? "Your posting, from your sign-in" : "The district the map opens on, for you"}>
            <select value={myDistrict} onChange={(e) => chooseMyDistrict(e.target.value)} aria-label={kn ? "ನನ್ನ ಜಿಲ್ಲೆ" : "My district"}>
              <option value="">{kn ? "ಇಡೀ ಕರ್ನಾಟಕ" : "All Karnataka"}</option>
              {POLICE_DISTRICTS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
          <button type="button" className={`mx-rpt-btn ${repeatOn ? "on" : ""}`} aria-pressed={repeatOn}
                  onClick={() => setRepeatOn((v) => !v)}
                  title="Places with 3 or more FIRs on 2 or more days in the last 90 days">
            <i aria-hidden="true" />{kn ? "ಪುನರಾವರ್ತಿತ ಸ್ಥಳಗಳು" : "Repeat locations"}
            {repeatOn && repeats?.locations ? <b>{repeats.locations.length}</b> : null}
          </button>
        </div>
        <MapAgentsMenu kn={kn} district={selectedDistrict} dragging={!!dragAgent} onDrag={setDragAgent}
                       onRun={(id) => runMapAgent(id, selectedDistrict)} />
        {dragAgent && (
          <p className="mxa-drop" aria-hidden="true">
            {dropOver
              ? <>Run <b>{MAP_AGENTS.find((a) => a.id === dragAgent)?.name}</b> on <b>{dropOver}</b> · {new Date(`${endDate}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</>
              : "Drop on a district"}
          </p>
        )}
        <MapAgentResult run={agentRun} todayIso={todayIso}
                        stale={!!agentRun && agentRun.status === "done" && (agentRun.date !== endDate || agentRun.crime !== crimeType)}
                        onClose={() => setAgentRun(null)}
                        onRun={(id, arg) => runMapAgent(id, agentRun.district, id === "forecast" || id === "research" ? (arg || undefined) : undefined)}
                        onRerun={() => runMapAgent(agentRun.agent, agentRun.district, agentRun.station || undefined)} />
        {/* the forecast's as-of stays in view on the map, whichever tab is open */}
        {fc.on && <div className="fx-chip-map"><AsOfChip fc={fc} kn={kn} /></div>}
      </div>

      <div inert={reportOpen || showDossier ? "" : undefined} className="mx-pills" role="tablist" aria-label={kn ? "ಅಪರಾಧ ಪ್ರಕಾರ" : "Crime type"}>
        {PILLS.map((p) => (
          <button key={p.key || "all"} role="tab" aria-selected={crimeType === p.key} className={`mx-pill ${crimeType === p.key ? "on" : ""}`} onClick={() => setCrimeType(p.key)}>
            {kn ? p.kn : p.en}
          </button>
        ))}
        <select className={`mx-pill mx-more ${moreActive ? "on" : ""}`} value={moreActive ? crimeType : ""}
                onChange={(e) => e.target.value && setCrimeType(e.target.value)} aria-label={kn ? "ಇನ್ನಷ್ಟು ಅಪರಾಧಗಳು" : "More crime types"}>
          <option value="">{moreActive ? (kn ? moreActive.kn : moreActive.en) : (kn ? "ಇನ್ನಷ್ಟು ▾" : "More ▾")}</option>
          {MORE_TYPES.map((m) => <option key={m.key} value={m.key}>{kn ? m.kn : m.en}</option>)}
        </select>
        <span className="mx-pills-gap" aria-hidden="true" />
      </div>

      {/* Left column: the calendar and the crime report. */}
      <div className="mx-leftrail">
      <div inert={reportOpen || showDossier ? "" : undefined} className="mx-cal mx-panel">
        <div className="mx-cal-h">
          <div className="my">{kn ? MONTHS_KN[calMonth] : MONTHS_EN[calMonth]} <b>{calYear}</b></div>
          <div className="nav">
            <button onClick={() => setCalYear((y) => y - 1)} aria-label="Previous year" title={kn ? "ಹಿಂದಿನ ವರ್ಷ" : "Previous year"}>&laquo;</button>
            <button onClick={() => { const m = calMonth - 1; if (m < 0) { setCalMonth(11); setCalYear((y) => y - 1); } else setCalMonth(m); }} aria-label="Previous month">&lsaquo;</button>
            <button className="today" onClick={() => { setCalYear(today.getFullYear()); setCalMonth(today.getMonth()); setSelDay(today.getDate()); }}>{kn ? "ಇಂದು" : "TODAY"}</button>
            <button
              disabled={new Date(calYear, calMonth + 1, 1) > today}
              style={new Date(calYear, calMonth + 1, 1) > today ? { opacity: 0.25, cursor: "not-allowed" } : {}}
              onClick={() => { const m = calMonth + 1; if (new Date(calYear, m, 1) > today) return; if (m > 11) { setCalMonth(0); setCalYear((y) => y + 1); } else setCalMonth(m); }}
              aria-label="Next month"
            >&rsaquo;</button>
            <button
              disabled={new Date(calYear + 1, calMonth, 1) > today}
              style={new Date(calYear + 1, calMonth, 1) > today ? { opacity: 0.25, cursor: "not-allowed" } : {}}
              onClick={() => { if (new Date(calYear + 1, calMonth, 1) > today) return; setCalYear((y) => y + 1); }}
              aria-label="Next year"
              title={kn ? "ಮುಂದಿನ ವರ್ಷ" : "Next year"}
            >&raquo;</button>
          </div>
        </div>
        <div className="mx-win" role="radiogroup" aria-label={kn ? "ಅವಧಿ" : "Period"}>
          {[[1, kn ? "ದಿನ" : "Day"], [7, kn ? "7 ದಿನ" : "7 days"], [28, kn ? "28 ದಿನ" : "28 days"]].map(([d, l]) => (
            <button key={d} type="button" role="radio" aria-checked={win === d} className={win === d ? "on" : ""}
                    onClick={() => setWin(d)}
                    title={d === 1 ? "The selected day: the morning crime review"
                           : d === 7 ? "The 7 days ending on the selected day: the weekly review"
                           : "The 28 days ending on the selected day: the hotspot picture"}>{l}</button>
          ))}
        </div>
        <table className="mx-cal-grid">
          <thead><tr>{DOW_EN.map((d) => <th key={d}>{d[0]}</th>)}</tr></thead>
          <tbody>
            {(() => {
              const first = new Date(calYear, calMonth, 1);
              const start = first.getDay();
              const dim = daysInMonth(calYear, calMonth);
              const rows = [];
              let day = 1;
              for (let r = 0; r < 6 && day <= dim; r++) {
                const cells = [];
                for (let c = 0; c < 7; c++) {
                  if (r === 0 && c < start) { cells.push(<td key={c} className="mute" />); continue; }
                  if (day > dim) { cells.push(<td key={c} className="mute" />); continue; }
                  const d = day;
                  const cellDate = new Date(calYear, calMonth, d, 23, 59, 59);
                  const isFuture = cellDate > today;
                  const iso = isoDate(calYear, calMonth, d);
                  const count = activityByDay[iso];
                  cells.push(
                    <td
                      key={c}
                      className={`${d === selDay ? "sel" : ""} ${isFuture ? "mute" : ""} ${win > 1 && iso >= winStart && iso <= endDate && d !== selDay ? "inwin" : ""}`}
                      style={isFuture ? { opacity: 0.22, cursor: "not-allowed", border: "1px dashed rgba(255,255,255,0.05)" } : {}}
                      onClick={() => {
                        if (isFuture) return;
                        setSelDay(d);
                      }}
                      title={isFuture ? (kn ? "ಭವಿಷ್ಯದ ದಿನಾಂಕ (ಮುನ್ಸೂಚನೆ ಮಾದರಿಗಳಿಗೆ ಮಾತ್ರ)" : "Future date (reserved for predictive models)") : ""}
                    >
                      <span className="dn">{d}</span>
                      {!isFuture && count > 0 && <div style={{ fontSize: 7, color: "var(--amber)" }}>&bull;</div>}
                    </td>
                  );
                  day++;
                }
                rows.push(<tr key={r}>{cells}</tr>);
              }
              return rows;
            })()}
          </tbody>
        </table>
      </div>



      {/* ── ONE card: Karnataka Crime Report (click → full window with intelligence) ── */}
      <button inert={reportOpen || showDossier ? "" : undefined} className={`mx-stat mx-panel mx-stat-btn ${giLoading ? "is-loading" : ""}`} onClick={() => setReportOpen(true)} aria-haspopup="dialog" aria-busy={giLoading}>
        <span className="mx-sweep" aria-hidden="true" />
        <div className="t">{kn ? "ಕರ್ನಾಟಕ ಅಪರಾಧ ವರದಿ" : "Karnataka Crime Report"}<span className="open">{kn ? "ತೆರೆಯಿರಿ ↗" : "open ↗"}</span></div>
        {/* keyed on the selection so the block re-animates on every date / crime change */}
        <div key={`${endDate}|${crimeType}`} className="mx-swap">
            <div className="mx-day-top">
              <b>{giLoading && !totalObserved ? "–" : shownTotal.toLocaleString("en-IN")}</b>
              <span>{kn ? "ಪ್ರಕರಣಗಳು" : (totalObserved === 1 ? "case" : "cases")}<small>{win === 1 ? prettyDate(endDate, kn) : `${prettyDate(winStart, kn)} – ${prettyDate(endDate, kn)}`}</small></span>
            </div>
            <dl className="mx-day-rows">
              {dayChange && !giLoading && (
                <div>
                  <dt>{kn ? `${W.prev}ಕ್ಕೆ ಹೋಲಿಸಿದರೆ` : `Against ${W.prev}`}</dt>
                  <dd className={deltaPct > 2 ? "up" : deltaPct < -2 ? "down" : ""}>
                    {deltaPct >= 1 ? `${deltaPct}% more` : deltaPct <= -1 ? `${Math.abs(deltaPct)}% fewer` : "The same"}
                  </dd>
                </div>
              )}
              {giMonthlyTotal !== null && !giLoading && win < 28 && (
                <div>
                  <dt>{kn ? "ಕಳೆದ 30 ದಿನ" : "Last 30 days"}</dt>
                  <dd>{giMonthlyTotal.toLocaleString("en-IN")} {kn ? "ಪ್ರಕರಣಗಳು" : "cases"}</dd>
                </div>
              )}
            </dl>
          </div>
      </button>
      
        {repeatOn && (
          <div className="mx-panel mx-rpt-list" inert={reportOpen || showDossier ? "" : undefined}>
            <div className="mx-bars-h">{kn ? "ಪುನರಾವರ್ತಿತ ಸ್ಥಳಗಳು" : "Repeat locations"}<small>{kn ? "90 ದಿನ" : "last 90 days"}</small></div>
            {repeats?.busy && !repeats?.locations?.length && <p className="mx-rpt-none">{kn ? "ಓದಲಾಗುತ್ತಿದೆ…" : "Reading the register…"}</p>}
            {repeats?.error && <p className="mx-rpt-none">{kn ? "ಈಗ ಓದಲಾಗಲಿಲ್ಲ." : "Could not be read just now."}</p>}
            {repeats && !repeats.busy && !repeats.error && !repeats.locations.length && (
              <p className="mx-rpt-none">{kn ? "ಈ ಅವಧಿಯಲ್ಲಿ ಪುನರಾವರ್ತಿತ ಸ್ಥಳ ಇಲ್ಲ." : "No place had 3+ FIRs on 2+ days in this period."}</p>
            )}
            <ol>
              {(repeats?.locations || []).slice(0, 8).map((r, i) => (
                <li key={i}>
                  <button type="button" onClick={() => setFlyBounds(L.latLngBounds([r.lat - 0.012, r.lon - 0.012], [r.lat + 0.012, r.lon + 0.012]))}>
                    <b>{r.area || r.beat || r.stations[0]}</b>
                    <span>{r.firs} FIRs · {r.days} days · {r.crimes[0]?.crime.toLowerCase()} · {r.stations[0]}</span>
                  </button>
                </li>
              ))}
            </ol>
            <p className="mx-rpt-note">{kn ? "ಆನ್‌ಲೈನ್ ಅಪರಾಧ, ಕಾಣೆಯಾದವರು, ಠಾಣೆಯ ಡೀಫಾಲ್ಟ್ ಸ್ಥಳ ಹೊರತುಪಡಿಸಲಾಗಿದೆ." :
              "Within about 110 m. Online crime, missing persons and a station's own default point are left out: they are not places."}</p>
          </div>
        )}
        {/* Simple Bar Chart Legend */}
        {Object.keys(districtFirTotals).length > 0 && (
          <div inert={reportOpen || showDossier ? "" : undefined} className="mx-panel" style={{ marginTop: "12px", padding: "16px", background: "rgba(6,11,20,0.85)", border: "1px solid var(--glass-border)", borderRadius: "12px", pointerEvents: "auto", backdropFilter: "blur(10px)", zIndex: 10 }}>
            <div className="mx-bars-h">{kn ? "ಅಗ್ರ ಪೊಲೀಸ್ ಜಿಲ್ಲೆಗಳು" : "Police districts with most cases"}<small>{W.list}</small></div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {Object.entries(districtFirTotals)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([name, count]) => (
                  <div key={name} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{ width: "112px", fontSize: "11px", color: "rgba(255,255,255,0.85)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={`${policeLabel(name)} (${name} on the map)`}>{policeLabel(name)}</div>
                    <div style={{ flex: 1, height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                      <div style={{ width: `${(count / Math.max(1, maxFir)) * 100}%`, height: "100%", background: count === maxFir ? "var(--red)" : "var(--cyan)", borderRadius: "3px" }} />
                    </div>
                    <div style={{ width: "24px", fontSize: "11px", color: "#fff", textAlign: "right", fontWeight: 600 }}>{count}</div>
                  </div>
              ))}
            </div>
          </div>
        )}
        </div>

      {reportOpen && createPortal(
        <>
          <div className="mx-winback" onClick={() => setReportOpen(false)} />
          <div className="mx-window mx-panel" role="dialog" aria-label={kn ? "ಅಪರಾಧ ವರದಿ" : "Crime report"}>
            <button className="x" onClick={() => setReportOpen(false)} aria-label="Close"></button>
            <div className="wh">
              <b>{kn ? "ಕರ್ನಾಟಕ ಅಪರಾಧ ವರದಿ" : "Karnataka Crime Report"}</b>
              <span>{crimeLabel} · {kn ? "ವರೆಗೆ" : "up to"} {endDate} · {giStar.window_days || 30}{kn ? "ದಿನ" : "d window"}</span>
            </div>
            <div className="wgrid">
              <section>
                <h5>{kn ? "ವರದಿ" : "Report"}</h5>
                <div className="wbig">{totalObserved}<small>{kn ? "ಪ್ರಕರಣಗಳು" : "incidents"}</small></div>
                <table className="wtable">
                  <thead><tr><th>{kn ? "ವಲಯ" : "Zone"}</th><th>z</th><th>n</th><th></th></tr></thead>
                  <tbody>
                    {topGiZones.slice(0, 6).map((z) => (
                      <tr key={z.zone}>
                        <td>{z.zone}</td>
                        <td>{z.gi_stat.toFixed(2)}</td>
                        <td>{z.observed}</td>
                        <td>{z.is_hotspot ? <span className="hot">●</span> : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {flowOn && (
                  <div className="wcorr" style={{ padding: "8px", background: "rgba(255,255,255,0.03)", borderRadius: "6px", marginTop: "8px" }}>
                    <h6>{kn ? "ಸಂಕಲಿತ ಕಾರಿಡಾರ್‌ಗಳು" : "Compiled Corridors"} · A2</h6>
                    {serverCorridors && serverCorridors.length > 0 ? (
                      serverCorridors.map((c, i) => (
                        <div key={i} className="c" style={{ marginBottom: "6px", borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: "4px" }}>
                          <div style={{ fontWeight: 700 }}>{c.src} ↔ {c.dst} <span style={{ color: "#22e6f0", fontSize: "11px" }}>({Math.round((c.next_district_estimate?.probability || 0.8) * 100)}% → {c.next_district_estimate?.district})</span></div>
                          <div style={{ fontSize: "10px", color: "#aaa" }}>{c.primary_crime} · {c.involved_entities?.map(e => e.name).join(", ")}</div>
                        </div>
                      ))
                    ) : (
                      flows.slice(0, 3).map((f, i) => (
                        <div key={i} className="c">{f.a} ↔ {f.b} <b>{f.n}</b></div>
                      ))
                    )}
                  </div>
                )}
              </section>
              <section>
                <h5>{kn ? "Antar ಗುಪ್ತಚರ" : "Antar Intelligence"}<em>{kn ? "ದಿನಾಂಕ · ಸ್ಥಳ" : "date · place synthesis"}</em></h5>
                {intel.length === 0 && <p className="none">{kn ? "ದತ್ತಾಂಶ ಸಂಗ್ರಹಿಸಲಾಗುತ್ತಿದೆ…" : "Gathering intelligence…"}</p>}
                {intel.map((it, i) => (
                  <div className="irow" key={i}>
                    <i style={{ background: it.dot }} />
                    <div><p>{it.text}</p><em>{it.src}</em></div>
                  </div>
                ))}
              </section>
            </div>
          </div>
        </>, document.body
      )}



      {/* Right column: View summary (default) and Where next as tabs. Where next opens
          on click - or by itself when a station or beat is clicked on the map. */}
      <div className="mx-rightrail fx-rail">
          <div className="mx-rtabs" role="tablist" aria-label={kn ? "ಬಲ ಫಲಕ" : "Right panel"}>
            <button role="tab" aria-selected={rightTab === "summary"} className={rightTab === "summary" ? "on" : ""}
                    onClick={() => setRightTab(rightTab === "summary" ? null : "summary")}>{kn ? "ವೀಕ್ಷಣೆಯ ಸಾರಾಂಶ" : "View summary"}</button>
            <button role="tab" aria-selected={rightTab === "where"} className={rightTab === "where" ? "on" : ""}
                    onClick={() => setRightTab(rightTab === "where" ? null : "where")}>
              {kn ? "ಮುಂದೆ ಎಲ್ಲಿ" : "Where next"}
              {fc.hot?.items?.length ? <span className="mx-rtab-n">{fc.hot.items.length}</span> : null}
            </button>
          </div>
          
          {/* The selected district, first in the column so a click on the map is answered
              where the eye already is. It used to sit under the summary, out of view. */}
          {districtDetail && (() => {
            const raw = districtDetail, dated = !!raw.as_of;
            // counted from the date windows: the 30 before is 60 less 30, and the trend and
            // risk use the server's own rule (district_cache._risk_level / _trend_str)
            const d = !raw.from_windows ? raw : (() => {
              const cur = raw.last_30, prior = raw.sum_60 == null || cur == null ? null : Math.max(0, raw.sum_60 - cur);
              if (prior == null) return { ...raw, prior_30: null, trend: null, risk_level: null, top_crimes: null };
              const ratio = cur / Math.max(1, prior), pct = prior ? Math.round(((cur - prior) / prior) * 100) : null;
              return { ...raw, prior_30: prior, top_crimes: null,
                trend: pct == null ? (cur > 0 ? "+100%" : "—") : `${pct >= 0 ? "+" : ""}${pct}%`,
                risk_level: cur >= 80 || ratio >= 1.5 ? "High" : cur >= 30 || ratio >= 1.1 ? "Medium" : "Low" };
            })();
            const n = (v) => (v == null ? "…" : Number(v).toLocaleString("en-IN"));
            const nice = (iso) => { const x = new Date(`${iso}T00:00:00`); return Number.isNaN(x.getTime()) ? iso : x.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }); };
            // the 30 days against the 30 before, in words
            const versus = d.prior_30 == null || d.last_30 == null ? null
              : d.prior_30 === 0 ? (d.last_30 > 0 ? "none then" : "none in either period")
              : (() => { const p = Math.round(((d.last_30 - d.prior_30) / d.prior_30) * 100); return p === 0 ? "the same now" : `${Math.abs(p)}% ${p > 0 ? "more" : "fewer"} now`; })();
            // district_cache._risk_level, said in words
            const levelWhy = { High: "80 or more FIRs in 30 days, or at least half as many again as the 30 days before.",
                               Medium: "30 or more FIRs in 30 days, or at least a tenth more than the 30 days before.",
                               Low: "Fewer than 30 FIRs in 30 days and no clear rise on the 30 days before." };
            const share = d.last_30 != null && giMonthlyTotal > 0 && d.last_30 <= giMonthlyTotal ? (d.last_30 / giMonthlyTotal) * 100 : null;
            const openShare = d.open_unsubs_count != null && d.fir_count > 0 ? Math.round((d.open_unsubs_count / d.fir_count) * 100) : null;
            const top = (d.from_windows ? d.top_all : d.top_crimes) || [];
            const level = (lv) => (lv
              ? <span className="v"><i className={`mx-dc-dot ${riskClass(lv)}`} aria-hidden="true" />{lv}</span>
              : <span className="v">…</span>);
            const allTime = (
              <>
                {d.fir_count != null && <div className="mx-dc-row"><span className="k">{kn ? "FIR (ಒಟ್ಟು)" : "All FIRs on record"}</span><span className="v">{n(d.fir_count)}</span></div>}
                {d.open_unsubs_count != null && (
                  <div className="mx-dc-row">
                    <span className="k">{kn ? "ಆರೋಪಪಟ್ಟಿ ಇಲ್ಲದವು" : "No accused charge-sheeted yet"}</span><span className="v">{n(d.open_unsubs_count)}</span>
                    <em>{openShare != null ? `${openShare}% of all FIRs here. ` : ""}All crime types, all years.</em>
                  </div>
                )}
              </>
            );
            return (
              <div inert={reportOpen || showDossier ? "" : undefined} className={`mx-dcard mx-panel mx-dc${dcardBusy ? " is-busy" : ""}`} aria-busy={dcardBusy}>
                <div className="mx-dcard-head">
                  <span>{d.zone}<em>{dated ? nice(d.as_of) : nice(endDate)} · {crimeLabel}</em></span>
                  <button onClick={closeDistrict} title={kn ? "ಮುಚ್ಚಿ" : "Close"} aria-label={kn ? "ಮುಚ್ಚಿ" : "Close district card"}><X size={16} /></button>
                </div>
                <div className="mx-dcard-body">
                  {d.empty && <p className="mx-dcard-none">{kn ? "ಈ ಜಿಲ್ಲೆಗೆ ದಾಖಲೆಗಳಿಲ್ಲ" : "No records are held for this district."}</p>}
                  {!d.empty && dated && (
                    <>
                      <div className="mx-dcard-nums">
                        <div><b>{n(d.day_count)}</b><span>{kn ? "ಈ ದಿನ" : "On this day"}</span></div>
                        <div><b>{n(d.last_7)}</b><span>{kn ? "ಕಳೆದ 7 ದಿನ" : "Last 7 days"}</span></div>
                        <div><b>{n(d.last_30)}</b><span>{kn ? "ಕಳೆದ 30 ದಿನ" : "Last 30 days"}</span></div>
                      </div>
                      {dayView && (
                        <div className="mx-dc-day">
                          <div className="mx-dc-day-h">
                            {kn ? "ಈ ದಿನದ ಪ್ರಕರಣಗಳು" : `Cases on ${prettyDate(endDate, false)}`}
                            <small>{dayInDistrict.length} · {policeLabel(selectedDistrict)}</small>
                          </div>
                          {dayInDistrict.length ? (
                            <ol>
                              {dayInDistrict.slice(0, 25).map((c) => (
                                <li key={c.fir_id}>
                                  <button type="button" onClick={() => setFlyBounds(L.latLngBounds([c.lat - 0.02, c.lon - 0.02], [c.lat + 0.02, c.lon + 0.02]))}>
                                    <b>{crimeName(c.crime)}</b>
                                    <span>{[c.station, c.area].filter(Boolean).join(" · ")}{c.stage ? ` · ${c.stage}` : ""}</span>
                                  </button>
                                </li>
                              ))}
                            </ol>
                          ) : <p className="none">{kn ? "ಈ ದಿನ ಯಾವುದೇ FIR ಇಲ್ಲ." : "No FIR was registered here on this day."}</p>}
                          {dayInDistrict.length > 25 && <p className="none">and {dayInDistrict.length - 25} more</p>}
                        </div>
                      )}
                      <div className="mx-dc-row"><span className="k">{kn ? "ಹಿಂದಿನ 30 ದಿನ" : "The 30 days before"}</span><span className="v">{d.prior_30 == null ? "…" : <>{n(d.prior_30)}{versus && <small>{versus}</small>}</>}</span></div>
                      {share != null && <div className="mx-dc-row"><span className="k">{kn ? "ರಾಜ್ಯದ ಪಾಲು (30 ದಿನ)" : "Share of the state, last 30 days"}</span><span className="v">{share > 0 && share < 1 ? "under 1%" : `${Math.round(share)}%`}</span></div>}
                      <div className="mx-dc-row"><span className="k">{kn ? "ಚಟುವಟಿಕೆಯ ಮಟ್ಟ" : "Activity level"}</span>{level(d.risk_level)}{d.risk_level && levelWhy[d.risk_level] && <em>{levelWhy[d.risk_level]}</em>}</div>
                      {allTime}
                      <div className="mx-dc-row stack">
                        <span className="k">{d.from_windows ? (kn ? "ಹೆಚ್ಚು ದಾಖಲಾದವು (ಒಟ್ಟು)" : "Most recorded, all years") : (kn ? "ಹೆಚ್ಚು ದಾಖಲಾದವು (30 ದಿನ)" : "Most recorded, last 30 days")}</span>
                        {top.length ? <ol>{top.slice(0, 3).map((c) => <li key={c}>{crimeName(c)}</li>)}</ol> : <span className="none">{kn ? "ಯಾವುದೂ ಇಲ್ಲ" : "Nothing recorded in this period"}</span>}
                      </div>
                    </>
                  )}
                  {!d.empty && !dated && (
                    <>
                      <div className="mx-dc-row"><span className="k">{kn ? "ಈ ತಿಂಗಳು" : "This month"}</span><span className="v">{n(d.this_month)}<small>{n(d.prior_month)} last month</small></span></div>
                      <div className="mx-dc-row"><span className="k">{kn ? "ಚಟುವಟಿಕೆಯ ಮಟ್ಟ" : "Activity level"}</span>{level(d.risk_level)}</div>
                      {allTime}
                      {d.top_crimes?.length > 0 && <div className="mx-dc-row stack"><span className="k">{kn ? "ಟಾಪ್ ಅಪರಾಧಗಳು" : "Most recorded, all years"}</span><ol>{d.top_crimes.slice(0, 3).map((c) => <li key={c}>{crimeName(c)}</li>)}</ol></div>}
                      <p className="mx-dcard-none">{kn ? "ಇಂದಿನ ಅಂಕಿಅಂಶಗಳು" : "These are current figures. The server has not been restarted, so it cannot yet answer for the chosen date."}</p>
                    </>
                  )}
                  {!d.empty && sessionRole && sessionRole !== "Approver" && (
                    <>
                      <button type="button" className="mx-dc-act" onClick={() => setPatrolRequest(true)}>
                        {kn ? "ಗಸ್ತು ನಿಯೋಜನೆಯನ್ನು ಪ್ರಸ್ತಾಪಿಸಿ" : "Propose patrol deployment"}
                      </button>
                      <p className="mx-dc-actnote">{kn ? "ಮೇಲ್ವಿಚಾರಕ ಅಧಿಕಾರಿಯ ಅನುಮೋದನೆ ಅಗತ್ಯವಿದೆ" : "Nothing is sent until a supervising officer approves it."}</p>
                    </>
                  )}
                </div>
              </div>
            );
          })()}

          {rightTab === "where" && (
            <>
            <button
            type="button"
            onClick={() => setShowDossier((v) => !v)}
            style={{
              pointerEvents: "auto",
              background: showDossier ? "rgba(34,230,240,0.1)" : "rgba(11,18,32,0.5)",
              border: showDossier ? "1px solid rgba(34,230,240,0.3)" : "1px solid rgba(255,255,255,0.1)",
              borderRadius: "6px",
              padding: "6px 10px",
              color: "#22E6F0",
              fontSize: "10px",
              fontWeight: 600,
              fontFamily: "Inter, sans-serif",
              letterSpacing: "0.02em",
              cursor: "pointer",
              transition: "all 0.2s ease",
              width: "100%",
              marginBottom: "12px",
              textAlign: "center"
            }}
          >
            {kn ? "ಜಿಯೋ-ಇಂಟೆಲ್ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್" : "GEO-INTEL DASHBOARD"}
          </button>
            {fc.selected
              ? <ForecastCard fc={fc} kn={kn} sessionRole={sessionRole} />
              : <ForecastPanel fc={fc} kn={kn} crimeLabel={crimeType ? crimeLabel : null} onModelCard={() => setModelCardOpen(true)} />
          }
          </>
        )}
{rightTab === "summary" && (
            <aside inert={reportOpen || showDossier ? "" : undefined}
                   className={`mx-sum mx-panel ${giLoading ? "is-loading" : ""}`}
                   aria-label={kn ? "ವೀಕ್ಷಣೆಯ ಸಾರಾಂಶ" : "View summary"} aria-busy={giLoading}>
              <header>
                <div>
                  <h3>{kn ? "ವೀಕ್ಷಣೆಯ ಸಾರಾಂಶ" : "View summary"}</h3>
                  <p>{crimeLabel} · {selectedDistrict || (kn ? "ಕರ್ನಾಟಕ" : "Karnataka")} · {new Date(`${endDate}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</p>
                </div>
                <button type="button" onClick={() => setRightTab(null)} aria-label={kn ? "ಮುಚ್ಚಿ" : "Close the summary"} title={kn ? "ಮುಚ್ಚಿ" : "Close"}><X size={16} /></button>
              </header>

              {!viewInsight ? (
                <p className="mx-sum-empty">{giLoading ? (kn ? "ವೀಕ್ಷಣೆಯನ್ನು ಓದಲಾಗುತ್ತಿದೆ..." : "Reading the current view…") : (kn ? "ಈ ವೀಕ್ಷಣೆಯಲ್ಲಿ ಯಾವುದೇ ಚಟುವಟಿಕೆ ದಾಖಲಾಗಿಲ್ಲ." : "No recorded activity in this view.")}</p>
              ) : (() => {
                // The register writes crime types in capitals ("KARNATAKA POLICE ACT 1963").
                const crime = (t) => {
                  const w = String(t || "").replace(/_/g, " ").trim().split(/\s+/).filter(Boolean);
                  const act = w.some((x) => /^act$/i.test(x));
                  return w.map((x, i) => (i === 0 || act ? x.charAt(0).toUpperCase() + x.slice(1).toLowerCase() : x.toLowerCase())).join(" ");
                };
                const hot = topGiZones.filter((z) => z.is_hotspot);
                const how = (z) => (z >= 4 ? "far above" : z >= 2.5 ? "well above" : "above");
                return (
                <div key={`${endDate}|${crimeType}|${selectedDistrict || ""}`} className="mx-swap">
                  {/* How to read the view, then what stands out in it. The day's count, its change,
                      the 30-day total and the district ranking are in the left column, once. */}
                  <p className={`mx-sum-state lvl-${viewInsight.level}`}>
                    <i aria-hidden="true" />
                    {kn
                      ? { normal: "ಸ್ಥಿತಿ ಸಾಮಾನ್ಯ", elevated: "ಸ್ಥಿತಿ ಎತ್ತರಿಸಿದ", high: "ಹೈ ಅಲರ್ಟ್" }[viewInsight.level]
                      : { normal: "Nothing unusual in this view.",
                          elevated: "Raised: cases are rising, or more than one hotspot is confirmed.",
                          high: "High: a sharp rise, or five or more confirmed hotspots." }[viewInsight.level]}
                  </p>

                  <dl className="mx-sum-rows">
                    <div>
                      <dt>{kn ? "ಹಾಟ್‌ಸ್ಪಾಟ್" : "Confirmed hotspots"}</dt>
                      <dd>
                        {!hot.length
                          ? (kn ? "ಯಾವುದೂ ಸಂಖ್ಯಾಶಾಸ್ತ್ರೀಯವಾಗಿ ದೃಢಪಟ್ಟಿಲ್ಲ" : "None")
                          : <><b>{hot.slice(0, 3).map((z) => z.zone).join(", ")}</b>{hot.length > 3 ? ` and ${hot.length - 3} more` : ""}
                              <small title={hot.slice(0, 3).map((z) => `${z.zone}: Gi* z ${Number(z.gi_stat).toFixed(1)}`).join(" · ")}>
                                {kn ? "ದೃಢಪಟ್ಟಿದೆ" : "A cluster with its neighbours that is unlikely to be chance"}</small></>}
                      </dd>
                    </div>
                    {topAlert && (
                      <div>
                        <dt>{kn ? "ಗಮನಿಸಿ" : "Above its usual level"}</dt>
                        <dd>
                          <b>{topAlert.zone}</b>: {crime(topAlert.crime_type)}
                          <small title={typeof topAlert.z_score === "number" ? `Anomaly score ${topAlert.z_score.toFixed(1)}` : undefined}>
                            {topAlert.observed} {kn ? "ದಾಖಲಾಗಿದೆ" : "recorded"}{typeof topAlert.z_score === "number" && topAlert.z_score >= 2 ? `, ${how(topAlert.z_score)} what is usual there` : ""}</small>
                        </dd>
                      </div>
                    )}
                    {viewInsight.outlook && (
                      <div>
                        <dt>{kn ? "ಮುಂದಿನ ನೋಟ" : `Next ${viewInsight.outlook.horizon} days`}</dt>
                        <dd>
                          <b>{viewInsight.outlook.name}</b>{viewInsight.outlook.where ? `, ${viewInsight.outlook.where}` : ""}
                          <small>{kn ? "ಸಾಧ್ಯತೆ" : "Likely"} {viewInsight.outlook.lo} {kn ? "–" : "to"} {viewInsight.outlook.hi} FIRs. {kn ? "ಅಂದಾಜು" : "An estimate, the highest in this view."}</small>
                        </dd>
                      </div>
                    )}
                    {viewInsight.patrol.length > 0 && (
                      <div>
                        <dt>{kn ? "ಗಸ್ತು" : "Patrol to consider"}</dt>
                        <dd>{viewInsight.patrol.join(", ")}
                          <small>{viewInsight.patrolFromForecast ? (kn ? "ಮುನ್ಸೂಚನೆಯಿಂದ" : "From the forecast.") : (kn ? "ಇಂದಿನ ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳಿಂದ" : "From today's hotspots.")} {kn ? "ಸಲಹೆ ಮಾತ್ರ" : "A suggestion; the officer decides."}</small>
                        </dd>
                      </div>
                    )}
                  </dl>

                  {/* The same figures in a sentence or two. It arrives after the rows and never
                      replaces them; if the model is slow or down, it is simply absent. */}
                  {(llmLoading || llmSummary) && (
                    <div className="mx-sum-note">
                      <h4>{kn ? "ಸಂಕ್ಷಿಪ್ತವಾಗಿ" : "In short"}</h4>
                      {llmLoading && <p className="dim">{kn ? "ಬರೆಯುತ್ತಿದೆ…" : "Writing…"}</p>}
                      {!llmLoading && llmSummary && <p>{llmSummary.replace(/^[\s\n]*[●*•]?\s*Analyzing(\.\.\.)?\s*\n*/i, "")}</p>}
                      {!llmLoading && llmSummary && <small>{kn ? "ಮೇಲಿನ ಅಂಕಿಅಂಶಗಳಿಂದ ಬರೆಯಲಾಗಿದೆ" : "Written by Antar from the figures above."}</small>}
                    </div>
                  )}

                      {/* Integrated Geo-Intel Ticker */}
                      <div 
                        onClick={() => setShowDossier(true)}
                        style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid rgba(255,255,255,0.05)", display: "flex", alignItems: "center", gap: "8px", overflow: "hidden", cursor: "pointer" }}
                        title={kn ? "ಜಿಲ್ಲಾ ಮಾಹಿತಿ ಫಲಕ ತೆರೆಯಿರಿ" : "Open the district briefing"}
                      >
                        <span style={{ color: "var(--cyan)", fontSize: "11px", fontWeight: "bold", whiteSpace: "nowrap", textDecoration: "underline", width: "65px", flexShrink: 0 }}>{kn ? "ಮಾಹಿತಿ" : "Briefing"}</span>
                        <marquee scrollamount="2" style={{ flex: 1, color: "rgba(255,255,255,0.7)", fontSize: "11px" }}>
                          {kn ? "ಜಿಲ್ಲಾ ಮಾಹಿತಿಯನ್ನು ಸಿದ್ಧಪಡಿಸಲಾಗುತ್ತಿದೆ..." : (intel.length > 0 ? intel.map(i => i.text).join("   •   ") : "Gathering real-time geospatial intelligence...")}
                        </marquee>
                      </div>
                      {/* Integrated Prediction Ticker */}
                      <div 
                        onClick={() => setRightTab("where")}
                        style={{ marginTop: "8px", paddingTop: "8px", borderTop: "1px dashed rgba(255,255,255,0.05)", display: "flex", alignItems: "center", gap: "8px", overflow: "hidden", cursor: "pointer" }}
                        title={kn ? "ಮುಂದೆ ಎಲ್ಲಿ ಫಲಕ ತೆರೆಯಿರಿ" : "Open Where Next Panel"}
                      >
                        <span style={{ color: "var(--amber)", fontSize: "11px", fontWeight: "bold", whiteSpace: "nowrap", textDecoration: "underline", width: "65px", flexShrink: 0 }}>{kn ? "ಮುಂದಿನ ವಾರ" : "Next week"}</span>
                        <marquee scrollamount="2" style={{ flex: 1, color: "rgba(255,255,255,0.7)", fontSize: "11px" }}>
                          {kn ? "ಮುಂದಿನ 7 ದಿನಗಳ ಮುನ್ಸೂಚನೆಗಳನ್ನು ಸಿದ್ಧಪಡಿಸಲಾಗುತ್ತಿದೆ..." : (fc.hot?.items?.length ? `${fc.hot.items.length} places are likely to be busier than usual in the next 7 days. The busiest is ${fc.hot.items[0]?.name}, with up to ${fc.hot.items[0]?.band80?.hi} cases likely.` : "Preparing the forecast for the next 7 days...")}
                        </marquee>
                      </div>
                </div>
                );
              })()}
            </aside>
          )}

        </div>

        {/* Keyboard-reachable district list - fallback for non-pointer users */}
      <div className="mx-district-list">
        <ul aria-label={kn ? "ಜಿಲ್ಲೆಗಳ ಪಟ್ಟಿ" : "District list"}>
          {districtsRich.map((d) => (
            <li key={d.zone}><button onClick={() => openDistrict(ZONE_TO_GADM_DISTRICT[d.zone] || d.zone, null)}>{d.zone}</button></li>
          ))}
        </ul>
      </div>
    </div>
  );
}


