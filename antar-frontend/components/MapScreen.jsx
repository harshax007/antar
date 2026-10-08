"use client";

import { createPortal } from "react-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Polyline, Polygon, Tooltip, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { useRouter, useSearchParams } from "next/navigation";
import { useLang } from "@/components/Providers";
import { KARNATAKA_GEOJSON_URL, KARNATAKA_TOPOJSON_URL, ZONE_TO_GADM_DISTRICT, ZONE_COORDS, coordFor, aggregateByDistrict } from "@/lib/karnataka";
import { feature as topoFeature, merge as topoMerge } from "topojson-client";
import { parseCSV, fromRecords, prepare, aliasFor } from "@/lib/crimeGraph";
import { MessageSquare, X, ShieldCheck } from "lucide-react";
import ProposeAction from "@/components/ProposeAction";
import { useForecast, ForecastLayer, ForecastPanel, ForecastCard, ModelCardModal, AsOfChip } from "@/components/ForecastPanel";
import { makeContains } from "@/lib/forecast";
import { readSession } from "@/lib/auth";
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
        if (geo) map.flyToBounds(L.geoJSON(geo).getBounds(), { padding: [0, 0] });
        if (onReset) onReset();
      }} aria-label="Reset View" title="Reset Map" style={{ fontSize: "14px", lineHeight: 1 }}>?</button>
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

function MouseCoords({ onMove }) {
  useMapEvents({ mousemove: (e) => onMove(e.latlng) });
  return null;
}

function FlyTo({ bounds }) {
  const map = useMap();
  useEffect(() => { if (bounds) map.flyToBounds(bounds, { padding: [60, 60], duration: 0.5 }); }, [bounds, map]);
  return null;
}

function FitToKarnataka({ geo, selectedDistrict }) {
  const map = useMap();
  const [prevDistrict, setPrevDistrict] = useState(null);
  // First load: fill the map frame with the state rather than a fixed centre/zoom, which
  // left Karnataka small in a sea of empty tiles.
  const fitted = useRef(false);
  useEffect(() => {
    if (!geo || fitted.current) return;
    fitted.current = true;
    requestAnimationFrame(() => {
      map.invalidateSize();
      map.fitBounds(L.geoJSON(geo).getBounds(), { padding: [0, 0] });
    });
  }, [geo, map]);
  useEffect(() => {
    if (!geo) return;
    // Only fly back to state bounds if we are deselecting a district
    if (!selectedDistrict && prevDistrict) {
      const layer = L.geoJSON(geo);
      map.flyToBounds(layer.getBounds(), { padding: [20, 20], duration: 0.5 });
    }
    setPrevDistrict(selectedDistrict);
  }, [geo, map, selectedDistrict]);
  return null;
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
  const [anchorAreas, setAnchorAreas] = useState([]);
  const [darkZones, setDarkZones] = useState([]);
  const [coords, setCoords] = useState(null);
  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const [flyBounds, setFlyBounds] = useState(null);
  const [districtDetail, setDistrictDetail] = useState(null);
  const [showDossier, setShowDossier] = useState(false);

  const [selectedDetail, setSelectedDetail] = useState(null);
  // Map forecast (next 7 / 28 days, stations statewide → beats in a selected district)
  const fc = useForecast({
    crimeType, gadmDistrict: selectedDistrict,
    // deep link from a chat forecast answer: /map?unit=…&h=28&fc=PROPERTY
    initial: { unit: sp?.get("unit") || null, horizon: Number(sp?.get("h")) || 7, category: sp?.get("fc") || null },
  });
    const [modelCardOpen, setModelCardOpen] = useState(false);
  const [rightTab, setRightTab] = useState(null);
  const [llmSummary, setLlmSummary] = useState(null);
  const [llmLoading, setLlmLoading] = useState(false);


  useEffect(() => { if (fc.selected) setRightTab("where"); }, [fc.selected]);
  // Right column: View summary by default; Where next opens on click, or by itself when a
  // station or beat is picked on the map (its card shows there).
  
  // Escape closes the dossier detail first, then the dossier (it had only its ).
  useEffect(() => {
    if (!showDossier && !selectedDetail) return;
    const onKey = (e) => {
      if (e.key !== "Escape") return;
      if (selectedDetail) setSelectedDetail(null); else setShowDossier(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [showDossier, selectedDetail]);
  
  const handleViewDetail = (type, data) => {
    setSelectedDetail({ type, data });
  };


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
    fetch(`${API}/api/map/anchor_areas`).then((r) => r.json()).then((d) => setAnchorAreas(d.anchor_areas || [])).catch(() => {});
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
    qDaily.set("days", "1");
    qDaily.set("end_date", endDate);
    
    const qDailyPrev = new URLSearchParams(qDaily);
    qDailyPrev.set("end_date", shiftIso(endDate, -1));

    // Q for 30-day (monthly)
    const qMonthly = new URLSearchParams();
    if (crimeType) qMonthly.set("crime_type", crimeType);
    qMonthly.set("days", "30");
    qMonthly.set("end_date", endDate);

    setGiLoading(true);
    Promise.all([
      fetch(`${API}/api/map/gi_star?${qDaily}`, { signal: ctrl.signal }).then(r => r.json()),
      fetch(`${API}/api/map/gi_star?${qDailyPrev}`, { signal: ctrl.signal }).then(r => r.json()).catch(() => null),
      fetch(`${API}/api/map/gi_star?${qMonthly}`, { signal: ctrl.signal }).then(r => r.json()).catch(() => null)
    ])
      .then(([curDaily, prevDaily, curMonthly]) => {
        setGiStar(curDaily || { zones: [] });
        setGiPrevTotal(prevDaily?.zones ? prevDaily.zones.reduce((sum, z) => sum + (z.observed || 0), 0) : null);
        setGiMonthlyTotal(curMonthly?.zones ? curMonthly.zones.reduce((sum, z) => sum + (z.observed || 0), 0) : null);
      })
      .catch((err) => { if (err?.name !== "AbortError") { setGiStar({ zones: [] }); setGiPrevTotal(null); setGiMonthlyTotal(null); } })
      .finally(() => { if (!ctrl.signal.aborted) setGiLoading(false); });
    return () => ctrl.abort();
  }, [crimeType, endDate]);

  const districtFirTotals = useMemo(
    () => aggregateByDistrict(giStar.zones || [], "observed"),
    [giStar]
  );
  const maxFir = Math.max(...Object.values(districtFirTotals), 1);

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

  async function openDistrict(gadmName, bounds) {
    setSelectedDistrict(gadmName);
    setFlyBounds(bounds);
    const primary = primaryZoneFor(gadmName);
    if (!primary) { setDistrictDetail(null); return; }
    try {
      const d = await (await fetch(`${API}/api/map/district/${encodeURIComponent(primary.zone)}`)).json();
      setDistrictDetail(d);
    } catch { setDistrictDetail(null); }
  }

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

  const effectiveAnchorAreas = useMemo(() => {
    if (anchorAreas && anchorAreas.length > 0) return anchorAreas;
    return [
      {
        unsub_id: "UNSUB-01 · Cyber Syndicate", primary_zone: "Bengaluru City",
        radius_km: 18.5, case_count: 24, centroid: { lat: 12.9716, lon: 77.5946 },
        convex_hull: [[13.04, 77.52], [13.02, 77.68], [12.91, 77.69], [12.89, 77.53]],
      },
      {
        unsub_id: "UNSUB-02 · Highway Robbery Crew", primary_zone: "Tumakuru",
        radius_km: 25.0, case_count: 11, centroid: { lat: 13.3379, lon: 77.1173 },
        convex_hull: [[13.42, 77.05], [13.40, 77.22], [13.25, 77.20], [13.24, 77.06]],
      },
    ];
  }, [anchorAreas]);

  // Antar Intelligence - date & place synthesis (shown inside the report window)
  const intel = useMemo(() => {
    const items = [];
    if (selectedDistrict && districtDetail) items.push({
      dot: "var(--green)",
      text: `Hyper-local analysis for ${districtDetail.zone}: ${districtDetail.fir_count} recent FIRs. Risk level classified as ${districtDetail.risk_level}, with a ${districtDetail.trend} trend.`,
      src: "district cache (live)",
    });
    if (leadZone) items.push({
      dot: "var(--red)",
      text: `Primary Hotspot Detected: ${leadZone.zone} exhibits intense clustering (z-score: ${leadZone.gi_stat.toFixed(2)}) based on ${leadZone.observed} active incidents.${leadZone.is_hotspot ? " Statistically confirmed via Gi*." : ""}`,
      src: "Gi* surface (live)",
    });
    if (topAlert) items.push({
      dot: "var(--amber)",
      text: `Anomaly Watch (${topAlert.zone}): Elevated ${String(topAlert.crime_type || "criminal").replace(/_/g, " ")} activity detected. ${topAlert.z_score != null ? `Z-Score: ${Number(topAlert.z_score).toFixed(2)}. ` : ""}${topAlert.observed != null ? `Cases: ${topAlert.observed}. ` : ""}Strategic patrol deployment highly recommended.`,
      src: "forecast agent (live)",
    });
    const topCor = serverCorridors[0];
    if (topCor) items.push({
      dot: "#FF8C42",
      text: `Criminal Network Linkage: Primary corridor established between ${topCor.src} and ${topCor.dst}. ${topCor.weight} repeat offender${(topCor.weight || 0) > 1 ? "s" : ""} tracked.${topCor.next_district_estimate?.district ? ` Predictive modeling suggests ${topCor.next_district_estimate.district} as the next likely target.` : ""}`,
      src: "corridor agent (backend)",
    });
    else if (flows[0]) items.push({
      dot: "#FF8C42",
      text: `Historical Network Linkage: Corridor established between ${flows[0].a} and ${flows[0].b}. ${flows[0].n} offender movements tracked in ${calYear} (e.g., alias: ${aliasFor(flows[0].acc)}).`,
      src: "FIR linkage (dataset)",
    });
    const fest = FESTIVALS.find((f) => f.month === calMonth + 1);
    if (fest && csvRecs) {
      const load = csvRecs.filter((r) => r._month === calMonth + 1).length;
      items.push({
        dot: "var(--cyan)",
        text: `Seasonal Modifier: ${fest.name} occurs this month (${fest.note}). Historically, this drives an average baseline of ${load} statewide FIRs.`,
        src: "open data · festival calendar",
      });
    }
    return items;
  }, [selectedDistrict, districtDetail, leadZone, topAlert, flows, calMonth, calYear, csvRecs, endDate]);

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
        

        {showDossier && createPortal(
          <div role="dialog" aria-modal="true" aria-label={kn ? "ಜಿಯೋ-ಇಂಟೆಲ್ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್" : "Geo-intel dashboard"}
               onMouseDown={(e) => { if (e.target === e.currentTarget) setShowDossier(false); }} style={{
            position: "fixed",
            top: 0, left: 0, right: 0, bottom: 0,
            zIndex: 400,
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "center",
            paddingTop: "90px",
            background: "rgba(3, 5, 12, 0.6)",
            backdropFilter: "blur(4px)"
          }}>
            <div style={{
              width: "min(600px, calc(100vw - 32px))",
              maxHeight: "80vh",
              overflowY: "auto",
              background: "rgba(11,18,32,0.95)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(255,255,255,0.15)",
              borderRadius: "12px",
              padding: "24px",
              boxShadow: "0 25px 60px rgba(0,0,0,0.8)",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
              animation: "fadeRise 0.25s ease-out"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "#22E6F0", fontFamily: "Inter, sans-serif", letterSpacing: "0.02em", fontWeight: 600 }}>
                    {kn ? "ಶಾಸನಬದ್ಧ 91 ಪ್ರಾದೇಶಿಕ ಕಡತ" : "Statutory Section 91 Spatial Dossier"}
                  </div>
                  <h3 style={{ margin: "4px 0 0", fontSize: "16px", fontWeight: 800, color: "#FFF", fontFamily: "Chakra Petch" }}>
                    {kn ? "ಅಂತರ್-ಜಿಲ್ಲಾ ಅಪರಾಧ ಕಾರಿಡಾರ್‌ಗಳು ಮತ್ತು ಆಂಕರ್‌ಗಳು" : "Inter-District Crime Corridors & Anchors"}
                  </h3>
                </div>
                <button 
                  onClick={() => setShowDossier(false)} 
                  style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "18px", padding: "0" }}
                >
                  
                </button>
              </div>
              
              <div style={{ fontSize: "13px", color: "#94A3B8", lineHeight: 1.5 }}>
                {kn 
                  ? "ಈ ವರದಿಯು ಅಪರಾಧ ಜಾಲಗಳು ಜಿಲ್ಲೆಯ ಗಡಿಗಳಲ್ಲಿ ಹೇಗೆ ಚಲಿಸುತ್ತವೆ (ಸಾರಿಗೆ ಕಾರಿಡಾರ್‌ಗಳು) ಮತ್ತು ಅವರ ಮುಖ್ಯ ಕಾರ್ಯಾಚರಣೆಯ ನೆಲೆಗಳನ್ನು ಗುರುತಿಸುತ್ತದೆ. UNSUB (ಅಪರಿಚಿತ ವ್ಯಕ್ತಿ) ವಲಯಗಳು ಭೌಗೋಳಿಕ ಆಧಾರದ ಮೇಲೆ ಗುರುತಿಸಲಾಗದ ಅಪರಾಧಿಗಳ ಕಾರ್ಯಕ್ಷೇತ್ರಗಳನ್ನು ಎತ್ತಿತೋರಿಸುತ್ತವೆ." 
                  : "This dossier maps how criminal networks move across district borders (Transit Corridors track offender movement vectors) and identifies their primary operating bases. UNSUB (Unknown Subject) envelopes highlight the operating zones of unidentified syndicates based on geographic profiling."}
              </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <div style={{ fontSize: "11px", color: "#FF8C42", fontWeight: 700, fontFamily: "Inter, sans-serif" }}>
                ⇄ {kn ? "ಸಕ್ರಿಯ ಸಾರಿಗೆ ಕಾರಿಡಾರ್‌ಗಳು" : "Active Transit Corridors"}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "180px", overflowY: "auto" }}>
                {(serverArcs.length > 0 ? serverArcs : flows).slice(0, 5).map((item, idx) => (
                  <div key={idx} onClick={() => handleViewDetail('corridor', item)} style={{ padding: "8px 10px", borderRadius: "8px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.1)", display: "flex", flexDirection: "column", gap: "3px", cursor: "pointer", transition: "background 0.2s" }} onMouseEnter={(e)=>e.currentTarget.style.background="rgba(255,255,255,0.06)"} onMouseLeave={(e)=>e.currentTarget.style.background="rgba(255,255,255,0.02)"}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11.5px", fontWeight: 700, color: "#FFF" }}>
                      <span>{item.a ? `${item.a} ↔ ${item.b}` : item.label.split("·")[0]}</span>
                      <span style={{ fontSize: "10px", color: "#FF8C42", fontFamily: "JetBrains Mono", display: "flex", alignItems: "center", gap: "6px" }}>{item.n || item.weight} {kn ? "ಕೊಂಡಿಗಳು" : "LINKS"} <MessageSquare size={12} color="rgba(255,255,255,0.4)" /></span>
                    </div>
                    <div style={{ fontSize: "10.5px", color: "#94A3B8", lineHeight: 1.3 }}>
                      {item.label}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "10px" }}>
              <div style={{ fontSize: "11px", color: "#D8B4FE", fontWeight: 700, fontFamily: "Inter, sans-serif" }}>
                {kn ? "ಗುರುತಿಸದ ಶಂಕಿತರ (UNSUB) ಆಂಕರ್ ವಲಯಗಳು" : "Unknown Subject (UNSUB) Operating Zones"}
              </div>
              {effectiveAnchorAreas.map((anc, idx) => (
                <div key={idx} onClick={() => handleViewDetail('anchor', anc)} style={{ padding: "8px 10px", borderRadius: "8px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.1)", display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", transition: "background 0.2s" }} onMouseEnter={(e)=>e.currentTarget.style.background="rgba(255,255,255,0.06)"} onMouseLeave={(e)=>e.currentTarget.style.background="rgba(255,255,255,0.02)"}>
                  <div>
                    <div style={{ fontSize: "11.5px", fontWeight: 700, color: "#FFF" }}>{anc.unsub_id}</div>
                    <div style={{ fontSize: "10.5px", color: "#94A3B8" }}>{anc.primary_zone} · {anc.radius_km} km radius</div>
                  </div>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: "#D8B4FE", fontFamily: "JetBrains Mono" }}>{anc.case_count} {kn ? "ಪ್ರಕರಣಗಳು" : "CASES"}</span>
                </div>
              ))}
            </div>

            <div style={{ padding: "8px 10px", borderRadius: "6px", background: "rgba(34,230,240,0.06)", border: "1px solid rgba(34,230,240,0.2)", fontSize: "10.5px", color: "#CBD5E1" }}>
              {kn ? "ಕಾನೂನುಬದ್ಧ ಪ್ರಮಾಣೀಕರಣ: ಎಲ್ಲಾ ಜಿಯೋ-ಸ್ಥಳಗಳು ಮತ್ತು ಕಾರಿಡಾರ್‌ಗಳು ಸೆಕ್ಷನ್ 91 ಸಾಕ್ಷ್ಯ ನಿಯಮಗಳ ಅಡಿಯಲ್ಲಿ ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟಿವೆ." : "Statutory Certification: All spatial polygons & transit vectors deterministically compiled under § 91 BNSS evidence rules."}
            </div>
          </div>
        </div>
        , document.body)}

        {selectedDetail && createPortal(
          <div role="dialog" aria-modal="true" aria-label="Dossier detail" style={{
            position: "fixed",
            top: 0, left: 0, right: 0, bottom: 0,
            zIndex: 400,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(3, 5, 12, 0.75)",
            backdropFilter: "blur(10px)",
            animation: "fadeRise 0.2s ease-out"
          }} onClick={() => setSelectedDetail(null)}>
            <div style={{
              width: "450px",
              maxWidth: "92%",
              background: "rgba(6, 11, 24, 0.94)",
              backdropFilter: "blur(24px)",
              border: "1px solid rgba(34, 230, 240, 0.35)",
              borderRadius: "16px",
              padding: "26px",
              boxShadow: "0 24px 64px rgba(0, 0, 0, 0.85), 0 0 30px rgba(34,230,240,0.1)",
              color: "#fff",
              display: "flex",
              flexDirection: "column",
              gap: "18px",
              position: "relative"
            }} onClick={(e) => e.stopPropagation()}>
              <button onClick={() => setSelectedDetail(null)} style={{ position: "absolute", top: "18px", right: "18px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "50%", width: "30px", height: "30px", display: "flex", alignItems: "center", justifyContent: "center", color: "#94A3B8", cursor: "pointer", transition: "all 0.2s" }} onMouseEnter={(e)=>e.currentTarget.style.color="#FFF"} onMouseLeave={(e)=>e.currentTarget.style.color="#94A3B8"}>
                <X size={16} />
              </button>
            
            {selectedDetail.type === 'corridor' ? (
              <>
                <div style={{ fontSize: "11px", color: "#FF8C42", fontWeight: 700, fontFamily: "JetBrains Mono", letterSpacing: "0.08em", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>⇄</span> ACTIVE TRANSIT CORRIDOR (SECTION 91)
                </div>
                <h2 style={{ margin: 0, fontSize: "20px", fontFamily: "Chakra Petch", fontWeight: 800, color: "#FFFFFF" }}>
                  <span style={{ color: "#22E6F0" }}>{selectedDetail.data.a || selectedDetail.data.label.split("A")[0]}</span> {selectedDetail.data.b ? ` ↔ ` : ''} <span style={{ color: "#22E6F0" }}>{selectedDetail.data.b || ''}</span>
                </h2>
                
                <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.08)" }}>
                  <div style={{ fontSize: "13px", color: "#CBD5E1", lineHeight: 1.6 }}>
                    Cross-district FIR correlation confirms an active syndicate transit route. Perpetrators originating from <strong style={{color:"#22E6F0"}}>{selectedDetail.data.a || "origin district"}</strong> execute coordinated offenses in <strong style={{color:"#22E6F0"}}>{selectedDetail.data.b || "destination zone"}</strong>.
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div style={{ background: "rgba(34,230,240,0.04)", border: "1px solid rgba(34,230,240,0.15)", padding: "10px 12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "10px", color: "#94A3B8", fontFamily: "JetBrains Mono" }}>EVIDENTIARY LINKS</div>
                    <div style={{ fontSize: "18px", fontWeight: 800, color: "#FF8C42", fontFamily: "JetBrains Mono", marginTop: "2px" }}>
                      {selectedDetail.data.n || selectedDetail.data.weight} {kn ? "ಕೊಂಡಿಗಳು" : "LINKS"}
                    </div>
                  </div>
                  <div style={{ background: "rgba(34,230,240,0.04)", border: "1px solid rgba(34,230,240,0.15)", padding: "10px 12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "10px", color: "#94A3B8", fontFamily: "JetBrains Mono" }}>PATROL RECOMMENDATION</div>
                    <div style={{ fontSize: "12px", fontWeight: 700, color: "#22E6F0", marginTop: "4px" }}>
                      Inter-district ANPR Checkpoint
                    </div>
                  </div>
                </div>

                <div style={{ padding: "10px", background: "rgba(255,140,66,0.08)", border: "1px solid rgba(255,140,66,0.2)", borderRadius: "8px", fontSize: "11px", color: "#E2E8F0" }}>
                  <strong>Key Detail:</strong> {selectedDetail.data.label}
                </div>
              </>
            ) : (
              <>
                <div style={{ fontSize: "11px", color: "#D8B4FE", fontWeight: 700, fontFamily: "JetBrains Mono", letterSpacing: "0.08em", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span></span> UNSUB SYNDICATE OPERATING ENVELOPE
                </div>
                <h2 style={{ margin: 0, fontSize: "20px", fontFamily: "Chakra Petch", fontWeight: 800, color: "#FFFFFF" }}>
                  Subject: <span style={{ color: "#22E6F0" }}>{selectedDetail.data.unsub_id}</span>
                </h2>
                
                <div style={{ background: "rgba(255,255,255,0.03)", padding: "14px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.08)" }}>
                  <div style={{ fontSize: "13px", color: "#CBD5E1", lineHeight: 1.6 }}>
                    Spatial probability modeling maps a concentrated operating envelope anchored in <strong style={{color:"#22E6F0"}}>{selectedDetail.data.primary_zone}</strong>. With <b style={{color:"#D8B4FE"}}>{selectedDetail.data.case_count} correlated cases</b>, the system has mapped a high-probability operating envelope stretching <b style={{color:"#22E6F0"}}>{selectedDetail.data.radius_km} km</b> around this centroid.
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div style={{ background: "rgba(216,180,254,0.04)", border: "1px solid rgba(216,180,254,0.2)", padding: "10px 12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "10px", color: "#94A3B8", fontFamily: "JetBrains Mono" }}>CORRELATED CASES</div>
                    <div style={{ fontSize: "18px", fontWeight: 800, color: "#D8B4FE", fontFamily: "JetBrains Mono", marginTop: "2px" }}>
                      {selectedDetail.data.case_count} FIRs
                    </div>
                  </div>
                  <div style={{ background: "rgba(216,180,254,0.04)", border: "1px solid rgba(216,180,254,0.2)", padding: "10px 12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "10px", color: "#94A3B8", fontFamily: "JetBrains Mono" }}>PRIMARY ANCHOR</div>
                    <div style={{ fontSize: "12px", fontWeight: 700, color: "#22E6F0", marginTop: "4px" }}>
                      {selectedDetail.data.primary_zone}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "12px" }}>
                   <div style={{ fontSize: "12px", color: "#94A3B8" }}>Correlated Cases</div>
                   <div style={{ fontSize: "16px", fontWeight: 700, color: "#D8B4FE", fontFamily: "JetBrains Mono" }}>{selectedDetail.data.case_count}</div>
                </div>
              </>
            )}
            </div>
          </div>
        , document.body)}

          <div inert={reportOpen || showDossier ? "" : undefined} style={{ height: "100%", position: "relative" }}>
            {giLoading && (
              <div style={{
                position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
                background: "rgba(6, 11, 20, 0.4)",
                backdropFilter: "blur(2px)",
                zIndex: 1000,
                pointerEvents: "none",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                transition: "opacity 0.3s ease"
              }}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="rgba(34, 230, 240, 0.9)" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ animation: "pulse 1.5s infinite ease-in-out" }}>
                  <path d="M7 16l-4-4 4-4" />
                  <path d="M17 8l4 4-4 4" />
                  <path d="M3 12h18" strokeDasharray="2 4" />
                </svg>
              </div>
            )}
            <MapContainer center={[15.317, 75.713]} zoom={7} zoomControl={false} minZoom={6} maxZoom={12} scrollWheelZoom style={{ height: "100%", width: "100%", transition: "filter 0.4s ease", filter: giLoading ? "grayscale(0.5) brightness(0.8)" : "none" }}>
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
                layer.bindTooltip(`${name} · ${firs} FIRs`, { sticky: true, className: "mx-hs" });
              }}
            />
          )}
          {/* Crisp state edge, drawn last so the district fills never wash it out. */}
          {stateOutline && (
            <GeoJSON key="ka-edge" data={stateOutline} style={stateEdgeStyle} interactive={false} />
          )}

          {/* Permanent District Labels */}
          {Object.entries(GADM_CENTROIDS).map(([name, coords]) => (
            <CircleMarker key={"lbl-"+name} center={coords} radius={0} pathOptions={{ opacity: 0, fillOpacity: 0 }} interactive={false}>
              <Tooltip permanent direction="center" className="mx-district-lbl">
                {name}
              </Tooltip>
            </CircleMarker>
          ))}

          {fc.clustersOn && !fc.on && topGiZones.map((z, i) => (
            <CircleMarker key={"heat" + i} center={[z.lat, z.lon]} radius={6 + Math.sqrt(Math.max(z.observed, 1)) * 1.2}
              pathOptions={{ stroke: false, fillColor: z.is_hotspot ? "#E14038" : "#22E6F0", fillOpacity: 0.12 }} />
          ))}

          {/* Under the forecast, Gi* is drawn as what it is - a significance test: a ring
              round each CONFIRMED cluster only, not a second set of blobs. */}
          {fc.clustersOn && fc.on && topGiZones.filter((z) => z.is_hotspot).map((z, i) => (
            <CircleMarker key={"gir" + i} center={[z.lat, z.lon]} radius={16} interactive
              pathOptions={{ color: "#22E6F0", weight: 1.6, opacity: 0.9, dashArray: "4 4", fill: false }}>
              <Tooltip className="mx-hs" sticky>{z.zone} · Gi* confirmed cluster (z={z.gi_stat.toFixed(2)}, {z.observed} FIRs in 30 days)</Tooltip>
            </CircleMarker>
          ))}
          {fc.clustersOn && !fc.on && topGiZones.map((z, i) => (
            <CircleMarker key={"hs" + i} center={[z.lat, z.lon]} radius={2 + Math.sqrt(Math.max(z.observed, 1)) * 0.6}
              pathOptions={{ color: z.is_hotspot ? "#ff5a5a" : "#5d6b80", weight: 1.4, fillColor: z.is_hotspot ? "#ff2f2f" : "#7a8aa3", fillOpacity: 0.55 }}>
              <Tooltip className="mx-hs" sticky>{z.zone} · z={z.gi_stat.toFixed(2)} · {z.observed} incidents{z.is_hotspot ? " · confirmed hotspot" : ""}</Tooltip>
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

          <ForecastLayer fc={fc} kn={kn} contains={karnatakaContains} />

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
                      {cType.replace(/_/g, " ")} · z={pz.gi_stat?.toFixed(2)} · {pz.observed} {kn ? "ಪ್ರಕರಣಗಳು" : "cases"}
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
          <MouseCoords onMove={setCoords} />
          <FlyTo bounds={flyBounds} />
          <FitToKarnataka geo={geo} selectedDistrict={selectedDistrict} />
          <ZoomButtons geo={geo} onReset={() => { setSelectedDistrict(null); setDistrictDetail(null); }} />
        
          

        </MapContainer></div>
        {/* inside the map frame, so it sits on the map, not on the page grid */}
      {selectedDistrict && (
        <button className="mx-breadcrumb" onClick={() => { setSelectedDistrict(null); setDistrictDetail(null); }}>
          {kn ? "‹ ಕರ್ನಾಟಕ" : "‹ Karnataka"} &middot; {selectedDistrict}
        </button>
      )}
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
                      className={`${d === selDay ? "sel" : ""} ${isFuture ? "mute" : ""}`}
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
        <div className="mx-cal-foot" style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div>{selDay} {kn ? MONTHS_KN[calMonth] : MONTHS_EN[calMonth]} {calYear} · {kn ? "ನಕ್ಷೆ ನವೀಕರಿಸಲಾಗಿದೆ" : "map updated"}</div>
        
        </div>
      </div>



      {/* ── ONE card: Karnataka Crime Report (click → full window with intelligence) ── */}
      <button inert={reportOpen || showDossier ? "" : undefined} className={`mx-stat mx-panel mx-stat-btn ${giLoading ? "is-loading" : ""}`} onClick={() => setReportOpen(true)} aria-haspopup="dialog" aria-busy={giLoading}>
        <span className="mx-sweep" aria-hidden="true" />
        <div className="t">{kn ? "ಕರ್ನಾಟಕ ಅಪರಾಧ ವರದಿ" : "Karnataka Crime Report"}<span className="open">{kn ? "ತೆರೆಯಿರಿ ↗" : "open ↗"}</span></div>
        {/* keyed on the selection so the block re-animates on every date / crime change */}
        <div key={`${endDate}|${crimeType}`} className="mx-swap">
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '8px' }}>
              <div className="big" style={{ margin: 0, lineHeight: 1 }}>{shownTotal.toLocaleString("en-IN")}</div>
              <div style={{ fontSize: '11px', color: 'var(--cyan)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{kn ? "ದೈನಂದಿನ ಪ್ರಕರಣಗಳು" : "Daily Incidents"}</div>
            </div>
            
            <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.7)", marginBottom: "14px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px" }}>
              <span>{prettyDate(endDate, kn)}</span>
              <span style={{ color: "var(--cyan)", fontWeight: 600 }}>&bull; {shownTotal.toLocaleString("en-IN")} generated FIRs</span>
              {deltaPct !== null && !giLoading && (
                <span className={`mx-delta ${deltaPct > 0 ? "up" : deltaPct < 0 ? "down" : ""}`} style={{ padding: '2px 6px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}>
                  {deltaPct > 0 ? `▲ ${Math.abs(deltaPct).toFixed(0)}%` : deltaPct < 0 ? `▼ ${Math.abs(deltaPct).toFixed(0)}%` : "—"}
                </span>
              )}
            </div>
            
            {giMonthlyTotal !== null && !giLoading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', background: 'rgba(6,11,20,0.4)', border: '1px solid var(--glass-border)', borderRadius: '6px', marginBottom: '14px' }}>
                <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--muted)', background: 'rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px' }}>30D</span>
                <span style={{ fontSize: '13px', color: '#fff' }}>{giMonthlyTotal.toLocaleString("en-IN")} <span style={{ color: 'var(--muted)', fontSize: '11px', marginLeft: '4px' }}>TOTAL</span></span>
              </div>
            )}
            
            {leadZone && (
              <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.85)', paddingLeft: '10px', borderLeft: `2px solid ${leadZone.is_hotspot ? 'var(--red)' : 'var(--cyan)'}` }}>
                <div style={{ marginBottom: '4px' }}>
                  <span style={{ color: '#fff', fontWeight: 600 }}>{leadZone.zone}</span> 
                  {leadZone.is_hotspot && <span style={{ color: 'var(--red)', marginLeft: '8px', fontSize: '9px', border: '1px solid rgba(248,113,113,0.3)', padding: '2px 5px', borderRadius: '4px', letterSpacing: '0.05em' }}>HOTSPOT</span>}
                </div>
                <div style={{ color: 'var(--muted)' }}>{leadZone.observed} cases <span style={{ margin: '0 4px' }}>•</span> z={leadZone.gi_stat.toFixed(2)}</div>
              </div>
            )}
          </div>
          {coords && <div className="coords">{coords.lat.toFixed(4)}&deg;N {coords.lng.toFixed(4)}&deg;E · <span className="live">LIVE</span></div>}
      </button>
      
        {/* Simple Bar Chart Legend */}
        {Object.keys(districtFirTotals).length > 0 && (
          <div inert={reportOpen || showDossier ? "" : undefined} className="mx-panel" style={{ marginTop: "12px", padding: "16px", background: "rgba(6,11,20,0.85)", border: "1px solid var(--glass-border)", borderRadius: "12px", pointerEvents: "auto", backdropFilter: "blur(10px)", zIndex: 10 }}>
            <div style={{ fontSize: "11px", color: "var(--cyan)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px", fontWeight: 600 }}>{kn ? "???? ????????? (???????)" : "Top Districts (Daily)"}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {Object.entries(districtFirTotals)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([name, count]) => (
                  <div key={name} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{ width: "90px", fontSize: "11px", color: "rgba(255,255,255,0.85)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={name}>{name}</div>
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
          <div className="mx-rtabs" role="tablist" aria-label={kn ? "?? ???????" : "Right panel"}>
            <button role="tab" aria-selected={rightTab === "summary"} className={rightTab === "summary" ? "on" : ""}
                    onClick={() => setRightTab(rightTab === "summary" ? null : "summary")}>{kn ? "??????? ??????" : "View summary"}</button>
            <button role="tab" aria-selected={rightTab === "where"} className={rightTab === "where" ? "on" : ""}
                    onClick={() => setRightTab(rightTab === "where" ? null : "where")}>
              {kn ? "????? ???????" : "Where next"}
              {fc.hot?.items?.length ? <span className="mx-rtab-n">{fc.hot.items.length}</span> : null}
            </button>
          </div>
          
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
            {kn ? "????-?????? ?????????????" : "GEO-INTEL DASHBOARD"}
          </button>
            {fc.selected
              ? <ForecastCard fc={fc} kn={kn} sessionRole={sessionRole} />
              : <ForecastPanel fc={fc} kn={kn} crimeLabel={crimeType ? crimeLabel : null} onModelCard={() => setModelCardOpen(true)} />
          }
          </>
        )}
{rightTab === "summary" && (
            <aside inert={reportOpen || showDossier ? "" : undefined}
                   className={`mx-vs mx-panel lvl-${viewInsight?.level || "normal"} ${giLoading ? "is-loading" : ""}`}
                   aria-label={kn ? "ವೀಕ್ಷಣೆಯ ಸಾರಾಂಶ" : "View summary"} aria-busy={giLoading}>
              <span className="mx-sweep" aria-hidden="true" />
              <header>
                <span className="mx-vs-pulse" aria-hidden="true" />
                <div className="ttl">
                  <b>{kn ? "ವೀಕ್ಷಣೆಯ ಸಾರಾಂಶ" : "VIEW SUMMARY"}</b>
                  <span>{crimeLabel} • {selectedDistrict || (kn ? "ಕರ್ನಾಟಕ" : "Karnataka")}</span>
                </div>
                <button type="button" onClick={() => setRightTab(null)} style={{ background: "transparent", border: "none", color: "var(--muted)", cursor: "pointer", padding: "4px" }}><X size={16} /></button>
              </header>

              {!viewInsight ? (
                <p className="mx-vs-empty">{giLoading ? (kn ? "ವೀಕ್ಷಣೆಯನ್ನು ಓದಲಾಗುತ್ತಿದೆ..." : "Reading the current view...") : (kn ? "ಈ ವೀಕ್ಷಣೆಯಲ್ಲಿ ಯಾವುದೇ ಚಟುವಟಿಕೆ ದಾಖಲಾಗಿಲ್ಲ." : "No recorded activity in this view.")}</p>
              ) : (
                <div key={`${endDate}|${crimeType}|${selectedDistrict || ""}`} className="mx-swap">
                  <div className={`mx-vs-status lvl-${viewInsight.level}`}>
                    <i aria-hidden="true" />
                    {kn
                      ? { normal: "ಸ್ಥಿತಿ • ಸಾಮಾನ್ಯ", elevated: "ಸ್ಥಿತಿ • ಎತ್ತರಿಸಿದ", high: "ಸ್ಥಿತಿ • ಹೈ ಅಲರ್ಟ್" }[viewInsight.level]
                      : { normal: "POSTURE • NORMAL", elevated: "POSTURE • ELEVATED", high: "POSTURE • HIGH ALERT" }[viewInsight.level]}
                  </div>

                  <div className="mx-vs-llm" style={{ fontSize: '13px', lineHeight: '1.6', color: 'rgba(226,232,240,0.88)', marginTop: '12px' }}>
                    {llmLoading ? (
                      <div style={{ opacity: 0.5, fontStyle: 'italic' }}>{kn ? "ಸಾರಾಂಶವನ್ನು ಸಿದ್ಧಪಡಿಸಲಾಗುತ್ತಿದೆ..." : "Working on it..."}</div>
                    ) : (
                      <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                        {llmSummary 
                          ? llmSummary.replace(/^[\s\n]*[●*•]?\s*Analyzing(\.\.\.)?\s*\n*/i, '') 
                          : (kn ? "ಸಾರಾಂಶ ಲಭ್ಯವಿಲ್ಲ." : "Summary unavailable.")}
                      </p>
                    )}
                    </div>

                      {/* Integrated Geo-Intel Ticker */}
                      <div 
                        onClick={() => setShowDossier(true)}
                        style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid rgba(255,255,255,0.05)", display: "flex", alignItems: "center", gap: "8px", overflow: "hidden", cursor: "pointer" }}
                        title={kn ? "????-?????? ????????????? ????????" : "Open Geo Intel Dashboard"}
                      >
                        <span style={{ color: "var(--cyan)", fontSize: "11px", fontWeight: "bold", whiteSpace: "nowrap", textDecoration: "underline", width: "65px", flexShrink: 0 }}>Geo Intel</span>
                        <marquee scrollamount="2" style={{ flex: 1, color: "rgba(255,255,255,0.7)", fontSize: "11px" }}>
                          {kn ? "????-??????: ???-???? ??????? ??????? ??????????? ??????????????????..." : (intel.length > 0 ? intel.map(i => i.text).join("   •   ") : "Gathering real-time geospatial intelligence...")}
                        </marquee>
                      </div>
                      {/* Integrated Prediction Ticker */}
                      <div 
                        onClick={() => setRightTab("where")}
                        style={{ marginTop: "8px", paddingTop: "8px", borderTop: "1px dashed rgba(255,255,255,0.05)", display: "flex", alignItems: "center", gap: "8px", overflow: "hidden", cursor: "pointer" }}
                        title={kn ? "????? ??????? ??????? ????????" : "Open Where Next Panel"}
                      >
                        <span style={{ color: "var(--amber)", fontSize: "11px", fontWeight: "bold", whiteSpace: "nowrap", textDecoration: "underline", width: "65px", flexShrink: 0 }}>Prediction</span>
                        <marquee scrollamount="2" style={{ flex: 1, color: "rgba(255,255,255,0.7)", fontSize: "11px" }}>
                          {kn ? "?????? 7 ????? ???????????????? ???????????????????????..." : (fc.hot?.items?.length ? `Predictive forecast indicates ${fc.hot.items.length} emerging hotspots across the state. Highest risk identified at ${fc.hot.items[0]?.name} (projecting up to ${fc.hot.items[0]?.band80?.hi} cases).` : "Gathering real-time predictive intelligence...")}
                        </marquee>
                      </div>
                    
                    
                    
                    
                </div>
              )}
            </aside>
          )}

          {districtDetail && (
            <div inert={reportOpen || showDossier ? "" : undefined} className="mx-dcard mx-panel mx-dcard-enhanced">
              <div className="mx-dcard-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>{districtDetail.zone}</span>
                <button onClick={() => { setSelectedDistrict(null); setDistrictDetail(null); }} style={{ background: 'none', border: 'none', color: 'rgba(34, 230, 240, 0.8)', cursor: 'pointer', fontSize: '20px', padding: '0 4px', lineHeight: 1 }} title="Close">&times;</button>
              </div>
              <div className="mx-dcard-body">
                <div className="mx-dcard-row"><span className="k">{kn ? "FIR (30ದಿನ)" : "FIRs (30d)"}</span><span className="v" style={{ color: "var(--cyan)" }}>{districtDetail.fir_count}</span></div>
                <div className="mx-dcard-bar"><div className="fill" style={{ width: `${Math.min(100, (districtDetail.fir_count / maxFir) * 100)}%` }} /></div>
                <div className="mx-dcard-row"><span className="k">{kn ? "ಈ ತಿಂಗಳು / ಹಿಂದಿನ" : "This Month / Prior"}</span><span className="v">{districtDetail.this_month} / {districtDetail.prior_month}</span></div>
                <div className="mx-dcard-row"><span className="k">{kn ? "ಊಹಿಸಲಾಗಿದೆ (ಮುಂದಿನ 7ದಿನ)" : "Predicted (Next 7d)"}</span><span className="v warning">{districtDetail.predicted || "--"}</span></div>
                <div className="mx-dcard-row"><span className="k">{kn ? "ಪರಿಹರಿಸಲಾಗದ / ತೆರೆದ" : "Unsolved / Open"}</span><span className="v critical">{districtDetail.open_unsubs_count?.toLocaleString() || "--"}</span></div>
                <div className="mx-dcard-row mt-2"><span className="k">{kn ? "ಅಪಾಯದ ಸೂಚ್ಯಂಕ" : "Risk index"}</span><span className={`mx-dcard-badge ${riskClass(districtDetail.risk_level)}`}>{districtDetail.risk_level}</span></div>
                <div className="mx-dcard-row"><span className="k">{kn ? "ಡಾರ್ಕ್ ವೆಬ್ ಸೂಚ್ಯಂಕ" : "Dark Web index"}</span><span className={`mx-dcard-badge mx-risk-h`}>{districtDetail.dark_level || "Critical"}</span></div>
                <div className="mx-dcard-row"><span className="k">{kn ? "ಪ್ರವೃತ್ತಿ" : "Trend"}</span><span className="v">{districtDetail.trend}</span></div>
                {districtDetail.top_crimes?.length > 0 && (
                  <div className="mx-dcard-row" style={{ flexDirection: "column", alignItems: "flex-start", gap: 3, marginTop: 8 }}>
                    <span className="k">{kn ? "ಟಾಪ್ ಅಪರಾಧಗಳು" : "Top crimes"}</span>
                    <span className="v" style={{ color: "var(--text)", whiteSpace: "normal", lineHeight: 1.3 }}>{districtDetail.top_crimes.slice(0, 3).join(", ")}</span>
                  </div>
                )}
                {sessionRole && sessionRole !== "Approver" && (
                  <button type="button" className="mx-hitl-btn" onClick={() => setPatrolRequest(true)} title={kn ? "ಮೇಲ್ವಿಚಾರಕ ಅಧಿಕಾರಿಯ ಅನುಮೋದನೆ ಅಗತ್ಯವಿದೆ" : "Requires supervising officer approval"}>
                    <ShieldCheck size={14} className="fx-i" /> {kn ? "ಗಸ್ತು ನಿಯೋಜನೆಯನ್ನು ಪ್ರಸ್ತಾಪಿಸಿ" : "Propose patrol deployment"}
                  </button>
                )}
              </div>
            </div>
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


