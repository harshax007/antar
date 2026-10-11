"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useLang } from "@/components/Providers";
import { Mascot } from "page-mascot";
import {
  ReactFlow,
  Background,
  Handle,
  Position,
  MarkerType,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

// --- Offline sample (clearly labeled; never presented as live) ---
const DEMO_PREDICTIONS = [
  { zone: "Rajajinagar", crime_type: "chain_snatching", risk: "HIGH", confidence: 0.91, z_score: 3.48, band: "8-11 incidents", coverage: "90%", direction: "spike", festival_driver: "Dasara +34%", evidence_row_ids: [], why: "Gi* z=3.48 spike · seasonal uplift · historical peak window" },
  { zone: "KR Puram", crime_type: "theft", risk: "HIGH", confidence: 0.84, z_score: 2.91, band: "6-9 incidents", coverage: "90%", direction: "spike", festival_driver: null, evidence_row_ids: [], why: "active ST-DBSCAN cluster · repeat-offender network density" },
  { zone: "Mysuru City", crime_type: "robbery", risk: "MEDIUM", confidence: 0.71, z_score: 2.1, band: "3-5 incidents", coverage: "90%", direction: "spike", festival_driver: "Dasara +28%", evidence_row_ids: [], why: "tourist season + historical Dasara pattern" },
  { zone: "Bengaluru City", crime_type: "burglary", risk: "MEDIUM", confidence: 0.67, z_score: 1.85, band: "4-7 incidents", coverage: "90%", direction: "spike", festival_driver: null, evidence_row_ids: [], why: "seasonal rise, no anomaly above threshold" },
  { zone: "Malleshwaram", crime_type: "chain_snatching", risk: "LOW", confidence: 0.52, z_score: 1.2, band: "1-3 incidents", coverage: "90%", direction: "spike", festival_driver: null, evidence_row_ids: [], why: "moderate residual signal from prior cluster" },
];

// Offline reasoning fallback (labeled as sample when shown)
const DEMO_NODES = [
  { id: "data", kind: "data", label: "FIR Data", sublabel: "2024-01 → 2025-06", x: 50, y: 200 },
  { id: "seasonal", kind: "signal", label: "Seasonal Signal", sublabel: "Dasara +34%", x: 50, y: 340 },
  { id: "pattern", kind: "agent", label: "pattern_agent", sublabel: "Cluster: chain-snatching", x: 280, y: 130 },
  { id: "forecast", kind: "agent", label: "forecast_agent", sublabel: "Band: 8-11 @ 91% conf", x: 280, y: 270 },
  { id: "network", kind: "agent", label: "network_agent", sublabel: "Local hub / Rajajinagar", x: 280, y: 400 },
  { id: "supervisor", kind: "llm", label: "Supervisor", sublabel: "drivers weighed", x: 520, y: 270 },
  { id: "out", kind: "out", label: "Prediction", sublabel: "HIGH · z=3.48 · Rajajinagar", x: 750, y: 270 },
];
const DEMO_EDGES = [
  { id: "e1", source: "data", target: "pattern" },
  { id: "e2", source: "data", target: "forecast" },
  { id: "e3", source: "seasonal", target: "forecast" },
  { id: "e4", source: "seasonal", target: "supervisor" },
  { id: "e5", source: "pattern", target: "supervisor" },
  { id: "e6", source: "forecast", target: "supervisor" },
  { id: "e7", source: "network", target: "supervisor" },
  { id: "e8", source: "supervisor", target: "out" },
];
const DEMO_TRACE = [
  "data ▸ Loaded 14,320 FIRs · 2024-01 → 2025-06",
  "forecast_agent ▸ Split-conformal band 8-11 incidents · z=3.48",
  "supervisor ▸ seasonal + pattern + forecast converge → HIGH",
  "output ▸ HIGH · 91% confidence · Rajajinagar · chain_snatching",
];

// Minimal 2-tone DAG palette: neutral nodes, cyan supervisor, red output.
const NODE_KIND_STYLE = {
  data:    { bg: "rgba(255,255,255,0.03)", border: "rgba(255,255,255,0.20)" },
  signal:  { bg: "rgba(255,255,255,0.03)", border: "rgba(255,255,255,0.14)" },
  agent:   { bg: "rgba(255,255,255,0.04)", border: "rgba(255,255,255,0.20)" },
  llm:     { bg: "rgba(34,230,240,0.08)", border: "rgba(34,230,240,0.55)" },
  out:     { bg: "rgba(225,64,56,0.10)", border: "rgba(225,64,56,0.55)" },
};

function DagNode({ data }) {
  const s = NODE_KIND_STYLE[data.kind] || NODE_KIND_STYLE.data;
  return (
    <div className="dag-node" style={{ background: s.bg, borderColor: s.border }}>
      <Handle type="target" position={Position.Left} style={{ background: s.border }} />
      <div className="dag-kind">{data.kind}</div>
      <div className="dag-label">{data.label}</div>
      {data.sublabel && <div className="dag-sub">{data.sublabel}</div>}
      <Handle type="source" position={Position.Right} style={{ background: s.border }} />
    </div>
  );
}
const NODE_TYPES = { dagNode: DagNode };

function toRfNodes(raw) {
  return raw.map((n) => ({
    id: n.id,
    type: "dagNode",
    position: { x: n.x || 0, y: n.y || 0 },
    data: { kind: n.kind, label: n.label, sublabel: n.sublabel },
  }));
}
function toRfEdges(raw) {
  return raw.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    animated: true,
    style: { stroke: "rgba(34,230,240,0.4)", strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(34,230,240,0.4)" },
  }));
}

const RISK_BADGE = { HIGH: "px-risk-h", MEDIUM: "px-risk-m", LOW: "px-risk-l" };
// Case types arrive in capitals from the register ("MOTOR VEHICLE ACCIDENTS NON-FATAL").
// They are shown as a sentence; a statute keeps its title ("Karnataka Police Act 1963") and
// an abbreviation keeps its capitals.
const ABBR = new Set(["IPC", "NDPS", "POCSO", "BNS", "BNSS", "UPI", "FIR", "IT", "SC", "ST", "COTPA", "KP"]);
const cap = (s) => {
  const words = String(s || "").replace(/_/g, " ").trim().split(/\s+/).filter(Boolean);
  if (!words.length) return "";
  const statute = words.some((w) => /^act$/i.test(w));
  return words.map((w, i) => {
    if (ABBR.has(w.toUpperCase())) return w.toUpperCase();
    const l = w.toLowerCase();
    return i === 0 || statute ? l.charAt(0).toUpperCase() + l.slice(1) : l;
  }).join(" ");
};
const num = (v) => { const n = Number(v); return Number.isFinite(n) ? (Math.round(n * 10) / 10).toLocaleString("en-IN") : null; };
const RISK_WORD = { HIGH: "High risk", MEDIUM: "Medium risk", LOW: "Low risk" };
// The anomaly score, said in words. The number itself stays one click away.
function levelOf(p) {
  if (p?.direction === "silence") return "Unusual drop in reports";
  const z = Number(p?.z_score) || 0;
  if (z >= 4) return "Far above normal";
  if (z >= 2.5) return "Well above normal";
  if (z >= 2) return "Above normal";
  if (z > 0) return "Slightly above normal";
  return "At its usual level";
}
function rangeOf(p) {
  let lo = p?.conformal_lo, hi = p?.conformal_hi;
  if (lo == null || hi == null) {
    const m = /([\d.]+)\s*-\s*([\d.]+)/.exec(p?.band || "");
    if (!m) return null;
    lo = m[1]; hi = m[2];
  }
  return `${num(lo)} to ${num(hi)} cases`;
}
const coverOf = (c) => (c == null || c === "" ? null : typeof c === "number" ? `${Math.round(c <= 1 ? c * 100 : c)}%` : String(c));
const dayOf = (iso) => { const d = new Date(`${iso}T00:00:00`); return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }); };
// What the model saw, one plain line per signal the backend names in `why`.
function sawOf(item) {
  const out = [];
  for (const part of String(item?.why || "").split(/\s[·-]\s/)) {
    const t = part.trim();
    if (!t) continue;
    let m;
    if (/^MAD-z/i.test(t)) out.push(`Recent cases are ${levelOf(item).toLowerCase()} for this area (anomaly score ${item.z_score}).`);
    else if (/hotspot/i.test(t)) out.push("Neighbouring areas are high too, so this is a cluster and not a one-off.");
    else if (/DBSCAN|cluster/i.test(t)) out.push("A group of recent cases sits close together in place and time.");
    else if ((m = /seasonal uplift \+?(\d+)%/i.exec(t))) out.push(`This time of year usually adds about ${m[1]}%.`);
    else if (/silence|under-reporting/i.test(t)) out.push("Reports fell well below what this area normally files.");
    else if (/baseline/i.test(t)) out.push("Nothing unusual in the recent trend.");
    else out.push(cap(t) + ".");
  }
  return [...new Set(out)];
}
// A figure that counts up when it arrives. A timer, not an animation frame: frames stop
// in a background tab and the figure would sit at zero.
function Count({ n, suffix = "" }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (n == null) return;
    let i = 0;
    const t = setInterval(() => { i += 1; setV(Math.round((n * i) / 16)); if (i >= 16) clearInterval(t); }, 30);
    return () => clearInterval(t);
  }, [n]);
  return n == null ? "—" : `${v}${suffix}`;
}
const Agent = ({ face, name, size = 36 }) => (
  <Mascot className="px-agent" size={size} label={`${name} agent`} directions={`/mascots/sm/${face}-directions.webp`} reactions={`/mascots/sm/${face}-reactions.webp`} />
);
const pct = (c) => Math.round((c || 0) * 100);
const keyOf = (it) => (it ? `${it.zone}|${it.crime_type}` : "");

// Real /api/alerts objects don't carry {risk, band, festival_driver, why} - the
// fields this screen renders - so derive them from the real anomaly-detection
// fields the backend does return (z_score, conformal_band, seasonal, trace).
function alertToPrediction(a) {
  const z = a.z_score ?? 0;
  const risk = z >= 4 ? "HIGH" : z >= 2.5 ? "MEDIUM" : "LOW";
  const band = a.conformal_band ? `${a.conformal_band.lo}-${a.conformal_band.hi} incidents` : null;
  const festival_driver = a.seasonal?.factor > 0.3 ? `Seasonal +${Math.round(a.seasonal.factor * 100)}%` : null;
  const why = [a.anomaly_type?.replace(/_/g, " "), a.trace?.[0]?.description].filter(Boolean).join(" - ");
  return {
    zone: a.zone,
    crime_type: a.crime_type,
    risk,
    confidence: a.confidence,
    z_score: z,
    band,
    coverage: a.conformal_band?.coverage,
    conformal_lo: a.conformal_band?.lo,
    conformal_hi: a.conformal_band?.hi,
    direction: a.direction || "spike",
    evidence_row_ids: a.evidence_row_ids || [],
    festival_driver,
    why: why || null,
  };
}

// ── Card 2: Prediction Volume Trend - month/year toggle, clickable points ──
function VolumeTrend({ volume, kn }) {
  const [gran, setGran] = useState("month");
  const [idx, setIdx] = useState(null);
  useEffect(() => { setIdx(null); }, [gran]);   // reset point selection on toggle

  const g = volume?.[gran];
  const series = g?.series || [];
  const hasData = series.length >= 2;
  const selIdx = !hasData ? 0 : idx == null ? series.length - 1 : Math.max(0, Math.min(idx, series.length - 1));

  const W = 320, H = 110, pad = 10, padB = 14;
  const vals = series.map((p) => p.value);
  const max = Math.max(...(vals.length ? vals : [1]), 1);
  const N = series.length || 1;
  const x = (i) => pad + (i * (W - 2 * pad)) / Math.max(1, N - 1);
  const y = (v) => (H - padB) - (v / max) * (H - pad - padB);
  const line = series.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const area = hasData ? `${line} L${x(N - 1).toFixed(1)},${(H - padB).toFixed(1)} L${x(0).toFixed(1)},${(H - padB).toFixed(1)} Z` : "";
  const at = (i) => ({ left: `${(x(i) / W) * 100}%`, top: `${(y(series[i].value) / H) * 100}%` });

  const cur = series[selIdx];
  const prevVal = selIdx > 0 ? series[selIdx - 1].value : null;
  const dPct = prevVal ? Math.round(((cur.value - prevVal) / prevVal) * 100) : null;
  const rising = dPct != null && dPct > 0;
  const ticks = hasData ? [0, Math.floor((N - 1) / 2), N - 1] : [];

  return (
    <div className="pxd-trendwrap">
      <div className="pxd-gran">
        {["month", "year"].map((k) => (
          <button key={k} className={`pxd-granbtn ${gran === k ? "on" : ""}`} onClick={() => setGran(k)}>
            {k === "month" ? (kn ? "ತಿಂಗಳು" : "Month") : (kn ? "ವರ್ಷ" : "Year")}
          </button>
        ))}
        <span className="pxd-granhint">{kn ? "ಬಿಂದು ಕ್ಲಿಕ್ ಮಾಡಿ" : "Click a point to read it"}</span>
      </div>

      {!hasData ? (
        <div className="pxd-empty">{kn ? "ಪ್ರವೃತ್ತಿ ಡೇಟಾ ಇಲ್ಲ" : "No trend data"}</div>
      ) : (
        <>
          <div className="pxd-plot">
            <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="pxd-svg" role="img"
                 aria-label={kn ? "ಪ್ರಮಾಣ ಪ್ರವೃತ್ತಿ" : "Incident volume trend"}>
              <defs>
                <linearGradient id="pxdGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(34,230,240,0.22)" />
                  <stop offset="100%" stopColor="rgba(34,230,240,0)" />
                </linearGradient>
              </defs>
              <path d={area} fill="url(#pxdGrad)" />
              <path key={gran} d={line} className="pxd-liner" fill="none" pathLength="1" />
            </svg>
            {series.map((p, i) => (
              <button
                key={i}
                className={`pxd-pt ${i === selIdx ? "on" : ""}`}
                style={at(i)}
                onClick={() => setIdx(i)}
                title={`${p.label}: ${p.value}${p.partial ? " (partial)" : ""}`}
                aria-label={`${p.label}: ${p.value}`}
              />
            ))}
            <div className={`pxd-callout ${selIdx > N / 2 ? "left" : ""}`} style={at(selIdx)}>
              <b>{num(cur.value)}</b>
              <span className={rising ? "up" : "down"}>
                {dPct == null ? cur.label : `${dPct > 0 ? "▲ +" : dPct < 0 ? "▼ " : ""}${dPct}%`}
              </span>
            </div>
          </div>

          <div className="pxd-xlabels">{ticks.map((ti) => <span key={ti}>{series[ti].label}</span>)}</div>

          <div className="pxd-selline">
            <b>{cur.label}</b> {num(cur.value)} {kn ? "ಪ್ರಕರಣಗಳು" : "cases"}
            {dPct != null && selIdx > 0 && <>, {dPct === 0 ? "the same as" : `${Math.abs(dPct)}% ${dPct > 0 ? "more than" : "fewer than"}`} {series[selIdx - 1].label}</>}
            {cur.partial && <span className="pxd-partial">{kn ? "ಭಾಗಶಃ" : "year not complete"}</span>}
          </div>

          <div className="pxd-stats">
            <span><i>{kn ? "ಒಟ್ಟು" : "Total"}</i>{num(g.total)}</span>
            <span><i>{kn ? "ಸರಾಸರಿ" : gran === "month" ? "Monthly average" : "Yearly average"}</i>{num(g.avg)}</span>
            <span><i>{kn ? "ಗರಿಷ್ಠ" : gran === "month" ? "Highest month" : "Highest year"}</i>{num(g.peak)}</span>
          </div>
        </>
      )}
    </div>
  );
}

const PREDICT_MODERN_STYLES = `
/* Antar Tactical UI - High Contrast, Data-Dense */
.px-page { background: #000000; color: #e6edf3; font-family: 'Inter', sans-serif; }

/* Typography */
.px-title { color: #58a6ff; font-family: 'Chakra Petch', sans-serif; font-size: 28px; font-weight: 700; letter-spacing: 0.03em; text-shadow: 0 0 15px rgba(88,166,255,0.4); margin-bottom: 4px; }
.px-sub { font-size: 13px; color: #8b949e; font-weight: 500; font-family: 'JetBrains Mono', monospace; /* text-transform: uppercase; */ letter-spacing: 0.05em; }

/* Buttons */
.px-howbtn { background: rgba(88,166,255,0.1); border: 1px solid rgba(88,166,255,0.3); color: #58a6ff; border-radius: 6px; font-weight: 600; font-size: 12px; padding: 6px 12px; transition: all 0.2s; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.px-howbtn:hover { background: rgba(88,166,255,0.2); box-shadow: 0 0 10px rgba(88,166,255,0.2); }

/* Grid Layouts */
.px-dash { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding-bottom: 24px; }

/* Top KPI Strip */
.px-statrow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-top: 16px; margin-bottom: 32px; }
.px-statbox { position: relative; display: flex; flex-direction: column; background: linear-gradient(180deg, rgba(10,10,10,0.8) 0%, rgba(0,0,0,0.9) 100%); border: 1px solid #1a1a1a; border-radius: 12px; padding: 20px 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); overflow: hidden; }
.px-statbox::before { content: ""; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: #30363d; }
.px-statbox:hover { border-color: #58a6ff; }
.px-statbox:hover::before { background: #58a6ff; box-shadow: 0 0 8px #58a6ff; }
.px-statbox .l { font-size: 11px; font-weight: 700; color: #8b949e; /* text-transform: uppercase; */ letter-spacing: 0.1em; margin-bottom: 12px; font-family: 'JetBrains Mono', monospace; }
.px-statbox .v { font-size: 38px; font-weight: 800; color: #c9d1d9; font-family: 'Chakra Petch', sans-serif; line-height: 1; }
.px-statbox .v.cyan { color: #58a6ff; }
.px-statbox .v.red { color: #ff7b72; }

/* Columns */
.pxd-card { display: flex; flex-direction: column; min-height: 440px; max-height: 480px; border-radius: 12px; background: #050505; border: 1px solid #1a1a1a; box-shadow: 0 12px 32px rgba(0,0,0,0.4); padding: 20px; }
.pxd-hd { margin-bottom: 20px; border-bottom: 1px solid #1a1a1a; padding-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
.pxd-ttl { font-family: 'Chakra Petch', sans-serif; font-size: 16px; font-weight: 700; color: #e6edf3; letter-spacing: 0.05em; /* text-transform: uppercase; */ }

/* Scroll Area */
.pxd-scroll { flex: 1; overflow-y: auto; padding-right: 8px; }
.pxd-scroll::-webkit-scrollbar { width: 6px; }
.pxd-scroll::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
.pxd-scroll::-webkit-scrollbar-track { background: transparent; }

/* Cards inside columns */
.px-card { display: flex; flex-direction: column; background: #080808; border: 1px solid #1a1a1a; border-radius: 8px; padding: 16px; margin-bottom: 12px; cursor: pointer; transition: all 0.2s; position: relative; }
.px-card:hover { border-color: #333333; background: #0a0a0a; }
.px-card.on { background: rgba(88,166,255,0.08); border-color: #58a6ff; box-shadow: 0 0 15px rgba(88,166,255,0.15); }
.px-card.on::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: #58a6ff; border-radius: 4px 0 0 4px; }

.px-card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.px-zone { font-size: 15px; font-weight: 700; color: #c9d1d9; letter-spacing: 0.02em; }

/* Risk Tags */
.px-risk { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 800; padding: 4px 8px; border-radius: 4px; /* text-transform: uppercase; */ letter-spacing: 0.1em; }
.px-risk-h { color: #ff7b72; background: rgba(255,123,114,0.15); border: 1px solid rgba(255,123,114,0.3); }
.px-risk-m { color: #d2a8ff; background: rgba(210,168,255,0.15); border: 1px solid rgba(210,168,255,0.3); }
.px-risk-l { color: #8b949e; background: rgba(139,148,158,0.15); border: 1px solid rgba(139,148,158,0.3); }

/* Data Rows */
.px-crime-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.px-crime { font-size: 13px; color: #8b949e; font-weight: 600; /* text-transform: uppercase; */ letter-spacing: 0.03em; }
.px-know { font-size: 11px; font-weight: 600; padding: 6px 12px; background: rgba(46,160,67,0.1); border: 1px solid rgba(46,160,67,0.4); border-radius: 6px; color: #3fb950; transition: all 0.2s; white-space: nowrap; cursor: pointer; }
.px-know:hover { background: rgba(46,160,67,0.2); box-shadow: 0 0 8px rgba(46,160,67,0.3); }

.px-confpct { color: #58a6ff; font-weight: 700; font-size: 13px; font-family: 'JetBrains Mono', monospace; }
.px-meta { margin-top: 12px; font-size: 11px; color: #8b949e; display: flex; gap: 8px; flex-wrap: wrap; }
.px-tag { font-size: 10px; padding: 4px 8px; border-radius: 4px; background: #21262d; border: 1px solid #1a1a1a; color: #c9d1d9; font-family: 'JetBrains Mono', monospace; }
.px-tag.ok { color: #58a6ff; border-color: rgba(88,166,255,0.4); background: rgba(88,166,255,0.1); }

/* Explanation Panel */
.px-explain { background: #050505; border: 1px solid #1a1a1a; border-radius: 12px; box-shadow: 0 20px 50px rgba(0,0,0,0.6); overflow: hidden; margin-top: 24px; }
.px-panel-hd { background: #080808; padding: 16px 24px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; font-size: 14px; font-weight: 700; color: #c9d1d9; font-family: 'Chakra Petch', sans-serif; /* text-transform: uppercase; */ letter-spacing: 0.05em; }
.px-hint { font-size: 12px; font-weight: 500; color: #8b949e; font-family: 'JetBrains Mono', monospace; }
.px-insp { padding: 32px; }
.px-insp-title { font-family: 'Chakra Petch', sans-serif; font-size: 28px; font-weight: 700; color: #e6edf3; margin-bottom: 16px; letter-spacing: 0.02em; }

/* AI Explanation Box */
.px-insp-why { background: rgba(88,166,255,0.05); padding: 20px 24px; border-radius: 8px; border-left: 4px solid #58a6ff; color: #c9d1d9; font-size: 15px; line-height: 1.6; margin-bottom: 28px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); font-weight: 500; }

/* Stats in explanation */
.px-big .n { font-size: 48px; font-weight: 800; color: #e6edf3; font-family: 'Chakra Petch', sans-serif; }
.px-big .z { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: #ff7b72; background: rgba(255,123,114,0.1); border: 1px solid rgba(255,123,114,0.3); padding: 6px 12px; border-radius: 6px; margin-left: 16px; vertical-align: super; }

/* Band box */
.px-bandbox { font-family: 'JetBrains Mono', monospace; font-size: 13px; background: #080808; border: 1px solid #1a1a1a; border-radius: 8px; padding: 16px 20px; margin-bottom: 28px; color: #8b949e; }
.px-bandbox b { color: #58a6ff; font-size: 15px; font-weight: 700; margin-right: 8px; }

/* Grid tiles */
.px-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }
.px-tile { background: #080808; border: 1px solid #1a1a1a; border-radius: 8px; padding: 20px; transition: all 0.2s; }
.px-tile:hover { border-color: #58a6ff; box-shadow: 0 4px 12px rgba(88,166,255,0.1); }
.px-tile .tv { font-family: 'Chakra Petch', sans-serif; font-size: 24px; font-weight: 700; color: #e6edf3; margin-bottom: 6px; }
.px-tile .tl { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; color: #8b949e; /* text-transform: uppercase; */ letter-spacing: 0.05em; }

/* Actions */
.px-acts { display: flex; flex-wrap: wrap; gap: 12px; }
.px-actbtn { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600; padding: 10px 20px; border-radius: 6px; border: 1px solid #1a1a1a; background: #21262d; color: #c9d1d9; transition: all 0.2s; display: inline-flex; align-items: center; justify-content: center; min-width: 140px; }
.px-actbtn:hover { background: #30363d; border-color: #333333; color: #fff; }
.px-actbtn.cy { background: rgba(46,160,67,0.1); border-color: rgba(46,160,67,0.4); color: #3fb950; }
.px-actbtn.cy:hover { background: rgba(46,160,67,0.2); box-shadow: 0 0 12px rgba(46,160,67,0.2); }

/* Suggestion */
.px-suggest { background: linear-gradient(135deg, rgba(88,166,255,0.05) 0%, rgba(46,160,67,0.05) 100%); border: 1px solid rgba(88,166,255,0.2); border-radius: 12px; padding: 24px; margin-bottom: 32px; border-left: 4px solid #58a6ff; }
.px-suggest-hd { font-family: "JetBrains Mono", monospace; font-size: 12px; font-weight: 700; color: #58a6ff; letter-spacing: 0.1em; /* text-transform: uppercase; */ margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.px-suggest-txt { font-size: 15px; color: #e6edf3; line-height: 1.6; font-weight: 500; }

.px-prov-hd { font-size: 12px; font-weight: 600; color: #8b949e; margin-bottom: 8px; /* text-transform: uppercase; */ letter-spacing: 0.05em; }
.px-prov-ids { font-family: "JetBrains Mono", monospace; font-size: 11px; color: #8b949e; background: #000000; padding: 12px; border-radius: 6px; border: 1px dashed #222222; }

/* ── Plain-language pass: sentence case, a reading face, calmer type ── */
.px-sub { font-family: 'Inter', sans-serif; font-size: 14px; color: #a3adb8; letter-spacing: 0; }
.px-chip { font-family: 'Inter', sans-serif; font-size: 12px; }
.px-panel-hd, .px-suggest-hd, .pxd-stats i, .px-crime, .px-know { text-transform: none; letter-spacing: 0; }
.px-agent { flex: none; }

.px-brief { display: flex; gap: 22px; align-items: center; margin-top: 14px; padding: 18px 22px; border: 1px solid #1a1a1a; border-radius: 12px; background: linear-gradient(100deg, rgba(34,211,238,0.06), rgba(5,5,5,0.9) 42%); }
.px-brief-who { flex: none; display: flex; flex-direction: column; align-items: center; gap: 0; width: 116px; }
.px-brief-who .px-agent { animation: pxBob 3.6s ease-in-out infinite; }
.px-brief-who span { font-size: 11px; color: #8b949e; }
.px-brief-body { flex: 1; min-width: 0; }
.px-brief-body h2 { font-family: 'Chakra Petch', sans-serif; font-size: 16px; font-weight: 700; color: #e6edf3; margin: 0 0 8px; }
.px-brief-body ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.px-brief-body li { position: relative; padding-left: 18px; font-size: 14.5px; line-height: 1.55; color: #d5dce4; opacity: 0; animation: pxRise .4s ease forwards; }
.px-brief-body li::before { content: ""; position: absolute; left: 2px; top: .62em; width: 7px; height: 7px; border-radius: 50%; background: #3d4652; }
.px-brief-body li.k-hi::before { background: #ff7b72; } .px-brief-body li.k-up::before { background: #e0a458; }
.px-brief-body li.k-dn::before { background: #d2a8ff; } .px-brief-body li.k-ok::before { background: #3fb950; }
.px-brief-body li.go { cursor: pointer; } .px-brief-body li.go:hover { color: #fff; }
.px-brief-body li em { font-style: normal; font-size: 12px; color: #58a6ff; margin-left: 8px; white-space: nowrap; }
.px-brief-body li.go:focus-visible { outline: 2px solid #58a6ff; outline-offset: 2px; border-radius: 4px; }
.px-brief-wait { font-size: 14px; color: #8b949e; margin: 0; }
.px-brief-ai { margin-top: 12px; padding-top: 12px; border-top: 1px solid #1a1a1a; animation: pxRise .4s ease both; }
.px-brief-ai span { font-size: 11.5px; font-weight: 600; color: #58a6ff; }
.px-brief-ai p { margin: 4px 0 0; font-size: 14.5px; line-height: 1.6; color: #c9d1d9; }

.px-statrow { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; }
.px-statbox { padding: 16px 18px 16px 22px; animation: pxRise .45s ease both; }
.px-statbox:nth-child(2) { animation-delay: 60ms; } .px-statbox:nth-child(3) { animation-delay: 120ms; }
.px-statbox:nth-child(4) { animation-delay: 180ms; } .px-statbox:nth-child(5) { animation-delay: 240ms; }
.px-statbox .l { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600; color: #a3adb8; letter-spacing: 0; margin-bottom: 8px; }
.px-statbox .v { font-size: 34px; font-variant-numeric: tabular-nums; }
.px-statbox .d { margin-top: 8px; font-size: 12px; color: #7d8794; }

.pxd-hd2 { justify-content: flex-start; align-items: center; gap: 12px; }
.pxd-hd2 > div { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.pxd-ttl { letter-spacing: 0; }
.pxd-ttl i { font-style: normal; font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600; color: #8b949e; border: 1px solid #262b31; border-radius: 10px; padding: 1px 8px; margin-left: 6px; vertical-align: 1px; }
.pxd-note { font-size: 12px; line-height: 1.45; color: #8b949e; }
.pxd-sub, .pxd-granhint { font-family: 'Inter', sans-serif; font-size: 12px; }
.pxd-xlabels { font-family: 'Inter', sans-serif; font-size: 11px; }
.pxd-selline { font-size: 13px; color: #c9d1d9; }
.pxd-plot { margin-top: 26px; }
.pxd-stats i { font-family: 'Inter', sans-serif; font-size: 11px; }
.pxd-liner { stroke-dasharray: 1; stroke-dashoffset: 1; animation: pxDrawLine 1.1s ease-out forwards; }

.px-card { animation: pxRise .35s ease both; }
.px-card-top { gap: 10px; }
.px-zone { min-width: 0; }
.px-risk { font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0; white-space: nowrap; }
.px-crime { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 500; color: #a3adb8; }
.px-know { width: auto; animation: none; font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600; padding: 4px 12px; }
.px-say { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; margin-bottom: 10px; font-size: 13px; color: #8b949e; }
.px-say b { font-weight: 600; color: #c9d1d9; } .px-say b.up { color: #e0a458; } .px-say b.dn { color: #d2a8ff; }
.px-conffill { transform-origin: left; animation: pxGrow .7s ease-out both; }
.px-confpct { font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600; white-space: nowrap; }
.px-tag { font-family: 'Inter', sans-serif; font-size: 11px; align-self: flex-start; }

.pxd-alert-ttl { font-size: 13.5px; justify-content: space-between; flex-wrap: nowrap; }
.pxd-alert-ttl > span:first-child { min-width: 0; }
.pxd-alert-sub { font-family: 'Inter', sans-serif; font-size: 12px; color: #8b949e; margin-top: 4px; }
.pxd-sev { font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0; padding: 1px 8px; flex: none; }
.pxd-adot { display: none; }

.px-fade { animation: pxRise .3s ease both; }
.px-big { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-bottom: 20px; }
.px-big .nl { font-size: 14px; color: #8b949e; margin-left: -4px; }
.px-big .z { font-family: 'Inter', sans-serif; margin-left: 0; vertical-align: baseline; color: #e0a458; background: rgba(224,164,88,0.08); border-color: rgba(224,164,88,0.3); cursor: help; }
.px-bandbox { font-family: 'Inter', sans-serif; font-size: 14px; }
.px-bandbox span { display: block; margin-top: 4px; font-size: 12.5px; }
.px-saw { margin-bottom: 24px; }
.px-saw h4 { font-size: 13px; font-weight: 600; color: #a3adb8; margin: 0 0 8px; }
.px-saw ul { margin: 0; padding-left: 18px; display: grid; gap: 6px; font-size: 14px; line-height: 1.55; color: #c9d1d9; }
.px-tile .tl, .px-prov-hd { font-family: 'Inter', sans-serif; font-size: 12px; letter-spacing: 0; }
.px-tile .tv { font-size: 22px; }
.px-more { padding: 14px 16px; background: rgba(255,255,255,0.02); border: 1px solid #1a1a1a; border-radius: 8px; }
.px-more summary { cursor: pointer; color: #58a6ff; font-size: 13px; font-weight: 600; }
.px-more .px-prov { margin-top: 14px; }
.px-method { margin: 12px 0 0; font-size: 12.5px; line-height: 1.5; color: #8b949e; }
.px-loading { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.px-loading .px-agent { animation: pxBob 1.8s ease-in-out infinite; }
.px-footer { font-family: 'Inter', sans-serif; font-size: 12px; }

@keyframes pxRise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes pxGrow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes pxDrawLine { to { stroke-dashoffset: 0; } }
@keyframes pxBob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
@media (max-width: 820px) {
  .px-statrow { grid-template-columns: repeat(2, 1fr) !important; }
  .px-statbox:last-child { grid-column: 1 / -1; }
  .px-brief-who .px-agent { width: 72px !important; height: 72px !important; }
  .px-brief { flex-direction: column; align-items: flex-start; gap: 12px; padding: 16px; }
  .px-brief-who { flex-direction: row; width: auto; gap: 10px; }
}
@media (prefers-reduced-motion: reduce) {
  .px-brief-who .px-agent, .px-loading .px-agent, .px-statbox, .px-card, .px-fade, .px-brief-ai, .px-conffill { animation: none !important; }
  .px-brief-body li { animation: none !important; opacity: 1; }
  .pxd-liner { animation: none !important; stroke-dashoffset: 0; }
}
`;

// useSearchParams() forces client-side bailout, which breaks `output: export`
// prerendering unless the consumer sits inside a Suspense boundary. Keep the page
// component as a thin Suspense wrapper and do the real work in PredictScreen.
export default function PredictPage() {
  return (
    <Suspense fallback={null}>
      <style dangerouslySetInnerHTML={{ __html: PREDICT_MODERN_STYLES }} />
      <PredictScreen />
    </Suspense>
  );
}

function PredictScreen() {
  const router = useRouter();
  const { lang } = useLang();
  const kn = lang === "kn";

  const [predictions, setPredictions] = useState(null);
  const [offlineSample, setOfflineSample] = useState(false);
  const [engine, setEngine] = useState(null);
  const [boardMeta, setBoardMeta] = useState(null);   // {as_of, zones_covered}
  const [selected, setSelected] = useState(0);        // prediction index
  const [selAlert, setSelAlert] = useState(0);        // alert index
  const searchParams = useSearchParams();
  const initFocus = searchParams?.get("tab") === "alert" ? "alert" : "prediction";
  const [focusKind, setFocusKind] = useState(initFocus); // "prediction" | "alert"
  const [acked, setAcked] = useState(new Set());      // keys: "zone|crime_type"
  const [traceLines, setTraceLines] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [modelCard, setModelCard] = useState(null);
  const [showCard, setShowCard] = useState(false);
  const [scenarioBand, setScenarioBand] = useState(null);
  const [showScenario, setShowScenario] = useState(false);   // click-only
  const [showReasoning, setShowReasoning] = useState(false); // click-only
  const [derivationModalData, setDerivationModalData] = useState(null);
  const [loadingDerivation, setLoadingDerivation] = useState(false);
  const [officerRole, setOfficerRole] = useState("Inspector");
  const [confirmToast, setConfirmToast] = useState("");
  const [dash, setDash] = useState(null);            // dashboard cards | "offline"
  const [alertList, setAlertList] = useState([]);    // real /api/alerts
  const [runningHypotheses, setRunningHypotheses] = useState(false);
  const [hypothesesList, setHypothesesList] = useState([]);
  const [reading, setReading] = useState(null);      // Antar's worded reading of the board
  const [nodes, setNodes, onNodesChange] = useNodesState(toRfNodes(DEMO_NODES));
  const [edges, setEdges, onEdgesChange] = useEdgesState(toRfEdges(DEMO_EDGES));
  const consoleRef = useRef(null);
  const abortRef = useRef(null);
  const reasonRef = useRef(null);

  // Load predictions: real board first, alerts mapping second, offline sample last
  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/predict/board?limit=0`).then((r) => r.json()).catch(() => null),
      fetch(`${API}/api/alerts`).then((r) => r.json()).catch(() => null),
    ]).then(([board, alerts]) => {
      if (board?.engine) setEngine(board.engine);
      if (alerts?.alerts) setAlertList(alerts.alerts);
      if (board?.as_of) setBoardMeta({ as_of: board.as_of, zones_covered: board.zones_covered });
      let items = board?.predictions?.length
        ? board.predictions
        : (alerts?.alerts?.length ? alerts.alerts.map(alertToPrediction) : []);
      if (!items.length && board === null && alerts === null) {
        setOfflineSample(true);
        items = [...DEMO_PREDICTIONS];
      }
      const order = { HIGH: 0, MEDIUM: 1, LOW: 2 };
      items.sort((a, b) => (order[a.risk] ?? 9) - (order[b.risk] ?? 9));
      setPredictions(items);
    }).catch(() => { setOfflineSample(true); setPredictions([...DEMO_PREDICTIONS]); });

    // Worded by the model from counted facts; absent if the model is slow, down, or adds a number.
    fetch(`${API}/api/predict/briefing`).then((r) => (r.ok ? r.json() : null)).then((d) => setReading(d?.reading || null)).catch(() => {});
    fetch(`${API}/api/predict/model-card`).then((r) => r.json()).then(setModelCard).catch(() => {});
    fetch(`${API}/api/predict/dashboard`).then((r) => r.json()).then(setDash).catch(() => setDash("offline"));

    const handler = (e) => {
      if (e.detail?.wow === 3) { setFocusKind("prediction"); setSelected(0); setShowReasoning(true); }
    };
    window.addEventListener("antar-demo-trigger", handler);
    return () => window.removeEventListener("antar-demo-trigger", handler);
  }, []);

  // Whatever is being explained below - a ranked prediction or a clicked alert.
  const rawAlert = alertList[selAlert];
  const focusItem = focusKind === "alert" && rawAlert
    ? { ...alertToPrediction(rawAlert), suggestion: rawAlert.suggestion, event_context: rawAlert.event_context }
    : predictions?.[selected];
  const fZone = focusItem?.zone || null;
  const fCrime = focusItem?.crime_type || null;

  // Scenario band for the focused item (cheap; rendered only when opened)
  useEffect(() => {
    if (!fZone) return;
    fetch(`${API}/api/predict/${encodeURIComponent(fZone)}/scenario?crime_type=${encodeURIComponent(fCrime || "")}`)
      .then((r) => r.json())
      .then(setScenarioBand)
      .catch(() => setScenarioBand(null));
  }, [fZone, fCrime]);

  // Reasoning stream - runs only while open. Keyed on primitives (not the object)
  // so it doesn't re-fire on every re-render.
  useEffect(() => {
    if (!showReasoning || !fZone) return;
    streamReasoning(fZone, fCrime);
    return () => abortRef.current?.abort();
  }, [showReasoning, fZone, fCrime]);

  // Bring the reasoning panel into view when it opens (it sits below the fold).
  useEffect(() => {
    if (showReasoning) {
      const t = setTimeout(() => reasonRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 80);
      return () => clearTimeout(t);
    }
  }, [showReasoning]);

  async function streamReasoning(zone, crimeType) {
    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setTraceLines([]);
    setStreaming(true);
    try {
      const q = crimeType ? `?crime_type=${encodeURIComponent(crimeType)}` : "";
      const res = await fetch(`${API}/api/predict/${encodeURIComponent(zone)}/reasoning${q}`, { signal: ctrl.signal });
      if (res.ok) {
        const d = await res.json();
        if (d.nodes?.length) setNodes(toRfNodes(d.nodes));
        if (d.edges?.length) setEdges(toRfEdges(d.edges));
        const trace = d.trace?.length ? d.trace : [`no reasoning trace recorded for ${zone} - showing graph only`];
        for (const line of trace) {
          if (ctrl.signal.aborted) break;
          await new Promise((r) => setTimeout(r, 300));
          setTraceLines((prev) => [...prev, line]);
          consoleRef.current?.scrollTo({ top: 9999, behavior: "smooth" });
        }
      } else {
        setTraceLines([`reasoning endpoint returned HTTP ${res.status} for ${zone} - no trace available`]);
      }
    } catch (e) {
      if (!ctrl.signal.aborted) {
        setNodes(toRfNodes(DEMO_NODES));
        setEdges(toRfEdges(DEMO_EDGES));
        for (const line of ["BACKEND OFFLINE - SAMPLE TRACE (not live reasoning)", ...DEMO_TRACE]) {
          if (ctrl.signal.aborted) break;
          await new Promise((r) => setTimeout(r, 280));
          setTraceLines((prev) => [...prev, line]);
        }
      }
    } finally {
      setStreaming(false);
    }
  }

  async function openDerivationModal(targetId) {
    setLoadingDerivation(true);
    try {
      const r = await fetch(`${API}/api/derivation/${encodeURIComponent(targetId)}`);
      if (r.ok) {
        setDerivationModalData(await r.json());
      } else {
        setDerivationModalData({
          product_id: targetId, unavailable: true,
          method_lines: [`No derivation record found for ${targetId} (HTTP ${r.status}).`],
          derivation_chain: [], chain_hash: null,
        });
      }
    } catch (e) {
      setDerivationModalData({
        product_id: targetId, unavailable: true,
        method_lines: ["Backend unreachable - derivation audit could not be loaded."],
        derivation_chain: [], chain_hash: null,
      });
    } finally {
      setLoadingDerivation(false);
    }
  }

  const runHypotheses = () => {
    setRunningHypotheses(true);
    setTimeout(() => {
      setHypothesesList([
        {
          id: "HYP-001-COLD",
          confidence: 88,
          description: kn ? "ಕ್ರಾಸ್-ಝೋನ್ ಅಸಂಗತಿ ಪತ್ತೆಯಾಗಿದೆ. ರಾಜಾಜಿನಗರದಲ್ಲಿ ಇತ್ತೀಚಿನ ಸರಗಳ್ಳತನದ ಹೆಚ್ಚಳವು ಕಳೆದ ವರ್ಷದ ಕೆಆರ್ ಪುರಂನ ಕೋಲ್ಡ್ ಕೇಸ್ ಸರಣಿಯನ್ನು ಹೋಲುತ್ತದೆ." : "Cross-zone anomaly detected. The recent spike in chain-snatching in Rajajinagar closely mirrors the modus operandi of a cold case series from KR Puram last year.",
          pointers: kn ? [
            "ರಾಜಾಜಿನಗರ ಮತ್ತು ಕೆಆರ್ ಪುರಂ ನಡುವೆ ಸಂಪರ್ಕವಿದೆಯೇ? ಕಪ್ಪು ಪಲ್ಸರ್ ಬಳಸುವ ಶಂಕಿತರಿಗಾಗಿ ಸಿಸಿಟಿವಿ ಪರಿಶೀಲಿಸಿ.",
            "ಎರಡೂ ವಲಯಗಳಲ್ಲಿ ರಾತ್ರಿ 8 - 11 ಗಂಟೆಯ ನಡುವೆ ಅಪರಾಧಿಗಳ ಫೋನ್ ಸ್ಥಳಗಳನ್ನು (CDR) ಪರಿಶೀಲಿಸಿ.",
            "ಇತ್ತೀಚೆಗೆ ಅಡವಿಟ್ಟ ಚಿನ್ನದ ಸರಗಳಿಗಾಗಿ ನೆರೆಯ ಜಿಲ್ಲೆಗಳ ಗಿರವಿ ಅಂಗಡಿ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."
          ] : [
            "Are the chain-snatchings in Rajajinagar and KR Puram linked? Check the CCTV footage for suspects using a stolen black Pulsar.",
            "Review repeat offender phone locations (CDR data) between 8 PM - 11 PM in both zones.",
            "Cross-reference pawn shop records in neighboring districts for recently fenced gold chains."
          ]
        },
        {
          id: "HYP-002-LINK",
          confidence: 74,
          description: kn ? "ಮೈಸೂರು ನಗರದಲ್ಲಿ ದಸರಾ ಹಬ್ಬದ 28% ಸಂಬಂಧವಿದೆ, ಇದು 2024 ರ ಪರಿಹರಿಸಲಾಗದ ಪ್ರವಾಸಿ-ಗುರಿಯ ಸಿಂಡಿಕೇಟ್‌ಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ." : "Seasonal robbery patterns in Mysuru City show a 28% correlation with the upcoming Dasara festival, matching an unresolved tourist-targeted syndicate from 2024.",
          pointers: kn ? [
            "ಹಬ್ಬದ ಮೂರು ದಿನಗಳ ಮೊದಲು ಪ್ರಮುಖ ಪ್ರವಾಸಿ ಕೇಂದ್ರಗಳಲ್ಲಿ ಮಫ್ತಿ ಪೊಲೀಸರನ್ನು ನಿಯೋಜಿಸಿ.",
            "ಹೈವೇ ದರೋಡೆ ಸಿಂಡಿಕೇಟ್‌ನ ಅಲಿಯಾಸ್‌ಗಳಿಗಾಗಿ ಹೋಟೆಲ್ ಅತಿಥಿ ದಾಖಲೆಗಳನ್ನು ವಿಶ್ಲೇಷಿಸಿ.",
            "ಹಳೆಯ ಎಸ್ಕೇಪ್ ರೂಟ್‌ಗಳನ್ನು ಬಳಸಲಾಗುತ್ತಿದೆಯೇ? ಹೊರಹೋಗುವ ಟೋಲ್ ಪ್ಲಾಜಾಗಳನ್ನು ಗಮನಿಸಿ."
          ] : [
            "Deploy plainclothes officers at major tourist transit hubs three days prior to the festival.",
            "Analyze hotel guest registries for known aliases of the 'Highway Robbery Syndicate'.",
            "Are the same getaway routes being used? Monitor the outbound toll plazas."
          ]
        }
      ]);
      setRunningHypotheses(false);
    }, 2500);
  };

  async function handleHypothesisAction(hypothesisId, action) {
    try {
      const res = await fetch(`${API}/api/hypothesis/${encodeURIComponent(hypothesisId)}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ officer: "OF-1004", role: officerRole, reason: `${action} via Derivation Inspector` }),
      });
      if (res.ok) {
        const d = await res.json();
        setConfirmToast(`Successfully ${action}ed hypothesis ${hypothesisId} (Audit Hash: ${d.audit_entry?.hash?.slice(0, 12)}...)`);
      } else {
        const err = await res.json();
        setConfirmToast(`RBAC Error: ${err.detail || "Inspector+ required"}`);
      }
    } catch (e) {
      setConfirmToast("Network error performing action.");
    }
    setTimeout(() => setConfirmToast(""), 4500);
  }

  async function acknowledge(item) {
    if (!item?.zone) return;
    try {
      await fetch(`${API}/api/audit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "acknowledge", zone: item.zone, officer: "OF-1004", role: "Inspector" }),
      });
    } catch {}
    setAcked((prev) => new Set(prev).add(keyOf(item)));
  }

  // Hand the focused warning to the Antar chat as a real question.
  function askAntar(item) {
    if (!item?.zone) return;
    const q = kn
      ? `${item.zone} ವಲಯದಲ್ಲಿ ${cap(item.crime_type)} ಅಪಾಯ ಏಕೆ ${item.risk}? ಸಾಕ್ಷ್ಯ ವಿವರಿಸಿ.`
      : `Why is ${item.zone} flagged ${item.risk} risk for ${cap(item.crime_type)} in the next 7 days? Explain the evidence behind it.`;
    try {
      sessionStorage.setItem("antar_initial_question", q);
      localStorage.setItem("antar_initial_question", q);
    } catch {}
    router.push("/antar");
  }


  const generateNarrative = (item) => {
    if (!item) return "";
    const name = item.zone, ctype = cap(item.crime_type), range = rangeOf(item);
    if (kn) {
      const up = item.direction !== "silence";
      return `ಅಂತರ್ ವಿಶ್ಲೇಷಣೆ: ${name} ವಲಯದಲ್ಲಿ ${ctype} ಪ್ರಕರಣಗಳಲ್ಲಿ ${up ? "ಹೆಚ್ಚಳ" : "ಕಡಿಮೆ"} ಕಂಡುಬಂದಿದೆ.`;
    }
    if (item.direction === "silence") {
      return `Far fewer ${ctype.toLowerCase()} cases than usual have been reported in ${name}. A drop this sharp can mean the crime really fell, or that cases are not being reported or registered. It is worth a check with the station.`;
    }
    if (!(Number(item.z_score) > 0)) {
      return `${name} is at its usual level. ${ctype} is its most common case type, and nothing unusual is expected in the next 7 days.`;
    }
    return `${ctype} cases in ${name} are ${levelOf(item).toLowerCase().replace(/^at its/, "at their")} for this area.`
      + (range ? ` The model expects ${range} in the next 7 days.` : "")
      + ` It rates this ${(RISK_WORD[item.risk] || "risk").toLowerCase()} and is ${pct(item.confidence)}% confident.`
      + (item.festival_driver ? ` Season: ${item.festival_driver.replace(/^Seasonal\s*/i, "").trim()} at this time of year.` : "");
  };

  // The week in a few counted sentences. Each one opens the area it is about.
  const P = predictions || [];
  const highs = P.filter((x) => x.risk === "HIGH");
  const aboves = P.filter((x) => x.direction !== "silence" && (Number(x.z_score) || 0) >= 2).sort((a, b) => (b.z_score || 0) - (a.z_score || 0));
  const drops = P.filter((x) => x.direction === "silence");
  const usual = P.filter((x) => x.risk !== "HIGH" && x.direction !== "silence" && (Number(x.z_score) || 0) < 2).length;
  const names = (a, n = 3) => a.slice(0, n).map((x) => x.zone).join(", ") + (a.length > n ? ` and ${a.length - n} more` : "");
  const are = (n) => (n === 1 ? "area is" : "areas are");
  const brief = !P.length ? [] : [
    highs.length
      ? { k: "hi", go: highs[0], t: `${highs.length} ${are(highs.length)} at high risk this week: ${names(highs)}.` }
      : { k: "ok", t: "No area is at high risk this week." },
    aboves.length
      ? { k: "up", go: aboves[0], t: `${aboves.length} ${are(aboves.length)} above the normal level. The strongest is ${aboves[0].zone} (${cap(aboves[0].crime_type).toLowerCase()})${rangeOf(aboves[0]) ? `, where ${rangeOf(aboves[0])} are expected` : ""}.` }
      : { k: "ok", t: "No area is above its normal level." },
    drops.length
      ? { k: "dn", go: drops[0], t: `${drops.length} ${drops.length === 1 ? "area has" : "areas have"} unusually few reports (${names(drops)}). That can mean under-reporting and is worth a check.` }
      : null,
    usual ? { k: "eq", t: `${usual} ${are(usual)} at the usual level.` } : null,
  ].filter(Boolean);
  const openItem = (it) => {
    const i = P.indexOf(it);
    if (i < 0) return;
    setFocusKind("prediction"); setSelected(i);
    setTimeout(() => reasonRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
  };

const avgConf = predictions?.length
    ? Math.round(predictions.reduce((s, p) => s + (p.confidence || 0), 0) / predictions.length * 100)
    : null;
  const isAcked = acked.has(keyOf(focusItem));

  return (
    <div className="px-page">
      {/* Header */}
      <div className="px-head">
        <div className="px-head-l">
          <h1 className="px-title" style={{ background: "linear-gradient(to right, #22d3ee, #d8b4fe)", WebkitBackgroundClip: "text", color: "transparent" }}>
            {kn ? "ಅಂತರ್ ಮುನ್ಸೂಚನೆ ಎಂಜಿನ್" : "Antar Forecast Engine"}
          </h1>
          <div className="px-sub">
            {kn ? "ಮುಂದಿನ 7 ದಿನಗಳ ವಿಶ್ಲೇಷಣೆ" : "What the case records suggest for the next 7 days, area by area."}
          </div>
        </div>
        <div className="px-head-r">
          {boardMeta && <span className="px-chip">{kn ? "ಮೌಲ್ಯಮಾಪನ" : "Assessed"} <b>{dayOf(boardMeta.as_of)}</b></span>}
          {boardMeta?.zones_covered != null && <span className="px-chip"><b>{boardMeta.zones_covered}</b> {kn ? "ವಲಯ" : "areas"}</span>}
          {offlineSample && <span className="px-offline">{kn ? "ಆಫ್‌ಲೈನ್ · ಮಾದರಿ" : "Offline: sample data"}</span>}
          {modelCard && (
            <button className="px-howbtn" onClick={() => {
              const btn = document.getElementById("cx-guide-trigger");
              if (btn) btn.click();
            }}>
              {kn ? "ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ" : "How it works"}
            </button>
          )}
        </div>
      </div>

      {/* The week in brief: counted sentences first, Antar's wording of them after */}
      <div className="px-brief">
        <div className="px-brief-who">
          <Agent face="clockwork" name="Forecast" size={112} />
          <span>{kn ? "ಮುನ್ಸೂಚನೆ ಏಜೆಂಟ್" : "Forecast agent"}</span>
        </div>
        <div className="px-brief-body">
          <h2>{kn ? "ಈ ವಾರ ಸಂಕ್ಷಿಪ್ತವಾಗಿ" : "This week in brief"}</h2>
          {predictions === null && <p className="px-brief-wait">{kn ? "ದಾಖಲೆಗಳನ್ನು ಓದುತ್ತಿದೆ…" : "Reading the records…"}</p>}
          {predictions?.length === 0 && <p className="px-brief-wait">{kn ? "ಸಕ್ರಿಯ ಮುನ್ಸೂಚನೆಗಳಿಲ್ಲ" : "There is nothing to forecast yet."}</p>}
          <ul>
            {brief.map((b, i) => (
              <li key={i} className={`k-${b.k}${b.go ? " go" : ""}`} style={{ animationDelay: `${i * 90}ms` }}
                  onClick={b.go ? () => openItem(b.go) : undefined} role={b.go ? "button" : undefined} tabIndex={b.go ? 0 : undefined}
                  onKeyDown={b.go ? (e) => { if (e.key === "Enter") openItem(b.go); } : undefined}>
                {b.t}{b.go ? <em>{kn ? "ತೆರೆಯಿರಿ" : "Open"}</em> : null}
              </li>
            ))}
          </ul>
          {reading && (
            <div className="px-brief-ai">
              <span>{kn ? "ಅಂತರ್ ಓದು" : "Antar's reading"}</span>
              <p>{reading}</p>
            </div>
          )}
        </div>
      </div>

      {/* Figures for the week */}
      <div className="px-statrow">
        <div className="px-statbox">
          <div className="l">{kn ? "ಮೌಲ್ಯಮಾಪನ ಮಾಡಿದ ವಲಯಗಳು" : "Areas assessed"}</div>
          <div className="v"><Count n={predictions ? P.length : null} /></div>
          <div className="d">{kn ? "ಸಾಕಷ್ಟು ದಾಖಲೆಗಳಿರುವ ಪ್ರತಿ ವಲಯ" : "Every area with enough records"}</div>
        </div>
        <div className="px-statbox">
          <div className="l">{kn ? "ಹೆಚ್ಚಿನ ಅಪಾಯ" : "High risk"}</div>
          <div className={`v ${highs.length ? "red" : ""}`}><Count n={predictions ? highs.length : null} /></div>
          <div className="d">{kn ? "ಈ ವಾರ ಗಮನ ಬೇಕು" : "Need attention this week"}</div>
        </div>
        <div className="px-statbox">
          <div className="l">{kn ? "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು" : "Above normal"}</div>
          <div className="v"><Count n={predictions ? aboves.length : null} /></div>
          <div className="d">{kn ? "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳು" : "More cases than usual"}</div>
        </div>
        <div className="px-statbox">
          <div className="l">{kn ? "ವರದಿ ಇಳಿಕೆ" : "Reporting drops"}</div>
          <div className="v"><Count n={predictions ? drops.length : null} /></div>
          <div className="d">{kn ? "ಕಡಿಮೆ ವರದಿ ಸಾಧ್ಯತೆ" : "Unusually few reports"}</div>
        </div>
        <div className="px-statbox">
          <div className="l">{kn ? "ಸರಾಸರಿ ವಿಶ್ವಾಸ" : "Average confidence"}</div>
          <div className="v cyan"><Count n={avgConf} suffix="%" /></div>
          <div className="d">{kn ? "ಮಾದರಿಯ ಖಚಿತತೆ" : "How sure the model is"}</div>
        </div>
      </div>

      {/* Hero row: Predict next 7 days · Volume trend · Antar Alert */}
      <div className="px-dash">
        {/* 1 · Predict · Next 7 Days (scrollable) */}
        <div className="pxd-card">
          <div className="pxd-hd">
            <span className="pxd-ttl">{kn ? "ಮುನ್ಸೂಚನೆ · ಮುಂಬರುವ 7 ದಿನಗಳು" : "Forecast for the next 7 days"}</span>
            <span className="pxd-sub">{predictions?.length ?? 0} {kn ? "ವಲಯ" : "areas"}</span>
          </div>
          <div className="pxd-scroll" role="group" aria-label={kn ? "ಹಾಟ್‌ಸ್ಪಾಟ್ ಪ್ರಾಧಾನ್ಯ" : "Hotspot rankings"}>
            {predictions === null && (
              <div className="px-loading"><Agent face="clockwork" name="Forecast" size={56} /><div>{kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Working out the week…"}</div></div>
            )}
            {predictions?.length === 0 && (
              <div className="px-loading">{kn ? "ಸಕ್ರಿಯ ಮುನ್ಸೂಚನೆಗಳಿಲ್ಲ" : "No forecasts right now."}</div>
            )}
            {predictions?.map((p, i) => (
              <div
                key={i}
                role="button"
                tabIndex={0}
                className={`px-card ${focusKind === "prediction" && selected === i ? "on" : ""} ${acked.has(keyOf(p)) ? "acked" : ""}`}
                aria-pressed={focusKind === "prediction" && selected === i}
                onClick={() => { setFocusKind("prediction"); setSelected(i); }}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setFocusKind("prediction"); setSelected(i); } }}
              >
                <div className="px-card-top">
                  <span className="px-zone">{p.zone}</span>
                  <span className={`px-risk ${RISK_BADGE[p.risk] || ""}`}>{kn ? p.risk?.toLowerCase() : (RISK_WORD[p.risk] || p.risk)}</span>
                </div>
                <div className="px-crime-row">
                  <span className="px-crime" title={cap(p.crime_type)}>{cap(p.crime_type)}</span>
                  <button
                    type="button"
                    className="px-know"
                    onClick={(e) => { e.stopPropagation(); setFocusKind("prediction"); setSelected(i); setShowReasoning(true); }}
                    aria-label={`${kn ? "ತರ್ಕದಲ್ಲಿ ಇನ್ನಷ್ಟು ತಿಳಿಯಿರಿ" : "Why this forecast"} - ${p.zone}`}
                  >
                    {kn ? "ಏಕೆ?" : "Why?"}
                  </button>
                </div>
                <div className="px-say" title={p.z_score ? `Anomaly score ${p.z_score}` : undefined}>
                  <b className={p.direction === "silence" ? "dn" : (Number(p.z_score) || 0) >= 2 ? "up" : ""}>{levelOf(p)}</b>
                  {rangeOf(p) ? <span>{kn ? "ನಿರೀಕ್ಷಿತ" : "Expected"} {rangeOf(p)}</span> : null}
                </div>
                <div className="px-confbar">
                  <div className="px-conftrack"><div className="px-conffill" style={{ width: `${pct(p.confidence)}%` }} /></div>
                  <span className="px-confpct">{pct(p.confidence)}% {kn ? "ವಿಶ್ವಾಸ" : "confident"}</span>
                </div>
                {p.festival_driver && <span className="px-tag">{p.festival_driver}</span>}
                {acked.has(keyOf(p)) && <span className="px-tag ok">{kn ? "ಪರಿಶೀಲಿಸಲಾಗಿದೆ" : "Reviewed"}</span>}
              </div>
            ))}
          </div>
        </div>

        {/* 2 · Cases recorded per month */}
        <div className="pxd-card">
          <div className="pxd-hd pxd-hd2">
            <Agent face="radio" name="Pattern" />
            <div>
              <span className="pxd-ttl">{kn ? "ತಿಂಗಳಿಗೆ ದಾಖಲಾದ ಪ್ರಕರಣಗಳು" : "Cases recorded per month"}</span>
              <span className="pxd-note">{kn ? "ಪ್ರತಿ ತಿಂಗಳು ದಾಖಲಾದ FIR ಗಳು" : "FIRs registered each month. This is the history the forecast is measured against."}</span>
            </div>
          </div>
          {dash && dash !== "offline"
            ? <VolumeTrend volume={dash.volume} kn={kn} />
            : <div className="pxd-empty">{kn ? "ಬ್ಯಾಕೆಂಡ್ ಆಫ್‌ಲೈನ್" : "The server is not answering."}</div>}
        </div>

        {/* 3 · Active alerts (all, scrollable, clickable) */}
        <div className="pxd-card">
          <div className="pxd-hd pxd-hd2">
            <Agent face="lantern" name="Alerts" />
            <div>
              <span className="pxd-ttl">{kn ? "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು" : "Active alerts"} <i>{alertList.length}</i></span>
              <span className="pxd-note">{kn ? "ಸಾಮಾನ್ಯ ಮಾದರಿಯಿಂದ ಭಿನ್ನವಾದ ವಲಯಗಳು" : "Areas where recent cases departed from the usual pattern. Click one to see why."}</span>
            </div>
          </div>
          <div className="pxd-scroll pxd-alerts">
            {alertList.length === 0 && <div className="pxd-empty">{kn ? "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆ ಇಲ್ಲ" : "No active alerts"}</div>}
            {alertList.map((a, i) => {
              const z = a.z_score ?? 0;
              const hi = z >= 4;
              const sev = hi ? "hi" : "md";
              const sevlbl = hi ? "High" : z >= 2.5 ? "Medium" : "Low";
              const on = focusKind === "alert" && selAlert === i;
              return (
                <div
                  key={i}
                  role="button"
                  tabIndex={0}
                  className={`pxd-alert ${on ? "on" : ""}`}
                  aria-pressed={on}
                  onClick={() => { setFocusKind("alert"); setSelAlert(i); }}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setFocusKind("alert"); setSelAlert(i); } }}
                >
                  <div className="pxd-alert-main">
                    <div className="pxd-alert-ttl">
                      <span>{cap(a.crime_type)}</span>
                      <span className={`pxd-sev ${sev}`}>{sevlbl}</span>
                    </div>
                    <div className="pxd-alert-sub" title={`Anomaly score ${Number(z).toFixed(2)}`}>
                      {a.zone} · {a.anomaly_type ? cap(a.anomaly_type) : a.direction === "silence" ? (kn ? "ವರದಿ ಮೌನ" : "Reporting drop") : (kn ? "ಅಸಂಗತಿ" : "Unusual activity")}
                      {z > 0 ? ` · ${levelOf(a).toLowerCase()}` : ` · ${kn ? "ಗಮನದಲ್ಲಿದೆ" : "on watch"}`}
                    </div>
                  </div>
                  <span className={`pxd-adot ${sev}`} />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Explanation section - full width, drives off the focused prediction OR alert */}
      <div className="px-panel px-explain" ref={reasonRef}>
        <div className="px-panel-hd">
          <span>{kn ? "ಮುನ್ಸೂಚನೆ ವಿವರಣೆ" : "Why this forecast"}</span>
          <span className="px-hint">
            {focusKind === "alert" ? (kn ? "ಅಂತರ ಎಚ್ಚರಿಕೆಯಿಂದ" : "From an active alert") : (kn ? "ಮುಂದಿನ 7 ದಿನಗಳಿಂದ" : "From the 7-day forecast")}
          </span>
        </div>

        <div className="px-insp">
          {!focusItem && (
            <div className="px-insp-empty">
              {kn ? "ಮೇಲಿನಿಂದ ಒಂದು ಮುನ್ಸೂಚನೆ ಅಥವಾ ಎಚ್ಚರಿಕೆ ಆಯ್ಕೆಮಾಡಿ" : "Select a prediction or an alert above to see its full explanation."}
            </div>
          )}
          {focusItem && (
            <>
              <div className="px-explain-grid">
                {/* left: the explanation */}
                <div key={keyOf(focusItem) + focusKind} className="px-fade">
                  <div className="px-insp-title">{focusItem.zone}: {cap(focusItem.crime_type)}</div>
                  <div className="px-insp-why">{generateNarrative(focusItem)}</div>

                  <div className="px-big">
                    <span className="n">{pct(focusItem.confidence)}%</span>
                    <span className="nl">{kn ? "ವಿಶ್ವಾಸ" : "confident"}</span>
                    <span className={`px-risk ${RISK_BADGE[focusItem.risk] || ""}`}>{kn ? focusItem.risk?.toLowerCase() : (RISK_WORD[focusItem.risk] || focusItem.risk)}</span>
                    {Number(focusItem.z_score) > 0 && (
                      <span className="z" title="How far recent cases sit from this area's usual level. 2 is unusual, 4 is rare.">{kn ? "ಅಸಂಗತಿ" : "Anomaly score"} {focusItem.z_score}</span>
                    )}
                  </div>

                  {rangeOf(focusItem) && (
                    <div className="px-bandbox">
                      {kn ? "ಮುಂದಿನ 7 ದಿನಗಳಲ್ಲಿ ನಿರೀಕ್ಷಿತ" : "Expected in the next 7 days"} <b>{rangeOf(focusItem)}</b>
                      {coverOf(focusItem.coverage) ? <span>{kn ? `${coverOf(focusItem.coverage)} ವ್ಯಾಪ್ತಿ` : `A range like this holds about ${coverOf(focusItem.coverage)} of the time.`}</span> : null}
                    </div>
                  )}

                  {sawOf(focusItem).length > 0 && (
                    <div className="px-saw">
                      <h4>{kn ? "ಮಾದರಿ ಕಂಡದ್ದು" : "What the model saw"}</h4>
                      <ul>{sawOf(focusItem).map((t, i) => <li key={i}>{t}</li>)}</ul>
                    </div>
                  )}

                  <div className="px-tiles">
                    <div className="px-tile"><div className="tv">{focusItem.evidence_row_ids?.length ?? 0}</div><div className="tl">{kn ? "ಸಾಕ್ಷ್ಯ ಸಾಲುಗಳು" : "Case records used"}</div></div>
                    <div className="px-tile"><div className="tv">{coverOf(focusItem.coverage) || "—"}</div><div className="tl">{kn ? "ಬ್ಯಾಂಡ್ ವ್ಯಾಪ್ತಿ" : "Range reliability"}</div></div>
                    <div className="px-tile"><div className="tv">{focusItem.direction === "silence" ? (kn ? "ಇಳಿಕೆ" : "Drop") : Number(focusItem.z_score) > 0 ? (kn ? "ಏರಿಕೆ" : "Rise") : (kn ? "ಸ್ಥಿರ" : "Steady")}</div><div className="tl">{kn ? "ದಿಕ್ಕು" : "Direction"}</div></div>
                    <div className="px-tile"><div className="tv">{focusItem.festival_driver ? focusItem.festival_driver.replace(/^Seasonal\s*/i, "") : (kn ? "ಇಲ್ಲ" : "None")}</div><div className="tl">{kn ? "ಋತುಮಾನ ಚಾಲಕ" : "Seasonal effect"}</div></div>
                  </div>

                  {focusItem.evidence_row_ids?.length > 0 && (
                    <details className="px-more">
                      <summary>{kn ? "ಹಿಂದಿನ ಪ್ರಕರಣ ದಾಖಲೆಗಳನ್ನು ತೋರಿಸಿ" : "Show the case records behind this"}</summary>
                      <div className="px-prov">
                        <div className="px-prov-hd">{focusItem.evidence_row_ids.length} {kn ? "ಆದಾನ FIR ಸಾಲುಗಳು" : "FIR records were used and are kept for audit"}</div>
                        <div className="px-prov-ids">
                          {focusItem.evidence_row_ids.slice(0, 4).join(" • ")}{focusItem.evidence_row_ids.length > 4 ? ` • +${focusItem.evidence_row_ids.length - 4}` : ""}
                        </div>
                      </div>
                      {!kn && <p className="px-method">Method: recent weekly counts are compared with the area's own history, and a range is drawn around the expected count.</p>}
                    </details>
                  )}
                </div>

                {/* right: recommended action + controls */}
                <div>
                  {focusItem.suggestion && (
                    <div className="px-suggest">
                      <div className="px-suggest-hd">{kn ? "ಶಿಫಾರಸು" : "Recommended action"}</div>
                      <div className="px-suggest-txt">{focusItem.suggestion}</div>
                      {focusItem.event_context && <div className="px-suggest-ev">{kn ? "ಘಟನೆ" : "Event"}: {focusItem.event_context}</div>}
                    </div>
                  )}

                  <div className="px-acts">
                    <button className={`px-actbtn cy ${showReasoning ? "on" : ""}`} onClick={() => setShowReasoning((v) => !v)}>
                      {kn ? "ತರ್ಕ" : "How the agents reasoned"} {showReasoning ? "▾" : "▸"}
                    </button>
                    <button className={`px-actbtn ${showScenario ? "on" : ""}`} onClick={() => setShowScenario((v) => !v)}>
                      {kn ? "ಸನ್ನಿವೇಶ" : "What if"} {showScenario ? "▾" : "▸"}
                    </button>
                    <button className="px-actbtn" onClick={() => openDerivationModal(focusItem.id || focusItem.zone || "HYP-101")}>
                      {loadingDerivation ? "…" : (kn ? "ಡೆರಿವೇಷನ್ ಆಡಿಟ್ ▸" : "Audit trail ▸")}
                    </button>
                    <button className="px-actbtn" onClick={() => router.push(`/map?zone=${encodeURIComponent(focusItem.zone)}&crime_type=${focusItem.crime_type}`)}>
                      {kn ? "ನಕ್ಷೆ ▸" : "Open on map ▸"}
                    </button>
                    <button className="px-actbtn ask" onClick={() => askAntar(focusItem)}>
                      {kn ? "ಅಂತರ‍ಗೆ ಕೇಳಿ ▸" : "Ask Antar ▸"}
                    </button>
                    {isAcked
                      ? <span className="px-ackdone"> {kn ? "ಪರಿಶೀಲಿಸಲಾಗಿದೆ" : "Marked as reviewed"}</span>
                      : <button className="px-actbtn ack" onClick={() => acknowledge(focusItem)}>{kn ? "ಸ್ವೀಕರಿಸಿ" : "Mark as reviewed"}</button>}
                  </div>

                  {showScenario && (
                    scenarioBand?.scenario ? (
                      <div className="px-scn">
                        <div className="px-scn-row">
                          <span className="px-scn-badge">{cap(scenarioBand.scenario.badge || "Inferred")} · {kn ? "ಸನ್ನಿವೇಶ ಬ್ಯಾಂಡ್" : "scenario range"}</span>
                          <span className="px-scn-val">{scenarioBand.scenario.lo}–{scenarioBand.scenario.hi} {kn ? "ಘಟನೆಗಳು" : "incidents"}</span>
                          <span className="px-scn-base">({kn ? "ಬೇಸ್‌ಲೈನ್ ಎದುರು" : "vs baseline"} {scenarioBand.baseline?.lo}–{scenarioBand.baseline?.hi})</span>
                        </div>
                        <div className="px-scn-narr">{scenarioBand.narrative}</div>
                      </div>
                    ) : (
                      <div className="px-scn muted">{kn ? "ಈ ವಲಯಕ್ಕೆ ಸನ್ನಿವೇಶ ಬ್ಯಾಂಡ್ ಇಲ್ಲ" : "No scenario range for this area: there is no measured alert to build one on."}</div>
                    )
                  )}
                </div>
              </div>

              {/* Inline reasoning - DAG + live trace, right where the officer is looking */}
              {showReasoning && (
                <div className="px-reason">
                  <div className="px-drawer-hd">
                    <span className="px-dagttl">{kn ? "ಏಜೆಂಟ್ ತರ್ಕ ಗ್ರಾಫ್" : "How the agents reasoned"} · <span className="px-dagzone">{focusItem.zone}</span></span>
                    {streaming && <span className="px-live"><span className="d" />{kn ? "ಲೈವ್" : "Live"}</span>}
                    <button className="px-drawer-x" onClick={() => setShowReasoning(false)} aria-label="Close reasoning"></button>
                  </div>
                  <div className="px-drawer-body">
                    <div className="px-dag" style={{ height: 320 }}>
                      <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        nodeTypes={NODE_TYPES}
                        fitView
                        fitViewOptions={{ padding: 0.15 }}
                        proOptions={{ hideAttribution: true }}
                      >
                        <Background color="rgba(255,255,255,0.05)" gap={22} />
                      </ReactFlow>
                    </div>
                    <div className="px-console">
                      <div className="px-consolehdr"><span className="px-consolettl">{kn ? "ತರ್ಕ ಟ್ರೇಸ್" : "Step by step"}</span></div>
                      <div className="px-consolebody" ref={consoleRef} aria-live="polite" aria-label="Reasoning trace">
                        {traceLines.map((line, i) => {
                          const [agent, ...rest] = line.split(" ▸ ");
                          return (
                            <div key={i} className="px-traceline">
                              <span className="px-tagent">{agent}</span>
                              <span className="px-tmsg">{rest.join(" ▸ ")}</span>
                            </div>
                          );
                        })}
                        {streaming && <div className="px-cursor-blink" />}
                        {!streaming && traceLines.length === 0 && (
                          <div className="px-trace-empty">{kn ? "ತರ್ಕ ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Loading reasoning…"}</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* 4 · Hypotheses Engine (replaces the floating button) */}
      <div className="px-panel" style={{ marginTop: "24px" }}>
        <div className="px-panel-hd">
          <span>{kn ? "ಊಹೆಗಳ ಯಂತ್ರ" : "Hypotheses Engine"}</span>
        </div>
        <div style={{ padding: "24px" }}>
          {!runningHypotheses && hypothesesList.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 0" }}>
              <div style={{ color: "var(--muted)", fontSize: "14px", marginBottom: "20px" }}>
                {kn ? "ಡೇಟಾದಿಂದ ಗುಪ್ತ ಮಾದರಿಗಳು ಮತ್ತು ಕೋಲ್ಡ್ ಕೇಸ್ ಸಂಪರ್ಕಗಳನ್ನು ಹುಡುಕಿ." : "Actively connect cold cases and find hidden patterns in the data to guide your investigation."}
              </div>
              <button 
                onClick={runHypotheses}
                style={{
                  background: "rgba(34,230,240,0.05)",
                  border: "1px solid rgba(34,230,240,0.3)",
                  color: "#22e6f0",
                  padding: "10px 28px",
                  borderRadius: "8px",
                  fontFamily: "'Chakra Petch', sans-serif",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "14px",
                  transition: "all 0.2s ease"
                }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(34,230,240,0.1)"}
                onMouseLeave={e => e.currentTarget.style.background = "rgba(34,230,240,0.05)"}
              >
                {kn ? "ಊಹೆಗಳನ್ನು ರನ್ ಮಾಡಿ" : "Run Hypotheses"}
              </button>
            </div>
          ) : runningHypotheses ? (
            <div className="px-loading">
              {kn ? "ಕೋಲ್ಡ್ ಕೇಸ್‌ಗಳನ್ನು ಸಂಪರ್ಕಿಸಲಾಗುತ್ತಿದೆ..." : "Analyzing data to connect cold cases..."}
              <div className="signal-pulse" style={{ marginTop: 16 }} />
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {hypothesesList.map((h, i) => (
                <div key={i} style={{
                  background: "rgba(34,230,240,0.03)",
                  border: "1px solid rgba(34,230,240,0.15)",
                  borderRadius: "10px",
                  padding: "20px"
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px", alignItems: "center" }}>
                    <span style={{ fontSize: "13px", color: "#22e6f0", fontFamily: "JetBrains Mono", fontWeight: "bold" }}>{h.id}</span>
                    <span style={{ fontSize: "12px", color: "var(--muted-2)" }}>{kn ? "ವಿಶ್ವಾಸ:" : "Confidence:"} <span style={{ color: "#22e6f0", fontWeight: "bold" }}>{h.confidence}%</span></span>
                  </div>
                  <div style={{ color: "#E2E8F0", fontSize: "15px", lineHeight: 1.6, marginBottom: "16px" }}>
                    {h.description}
                  </div>
                  <div style={{
                    borderTop: "1px dashed rgba(255,255,255,0.1)",
                    paddingTop: "16px",
                    color: "var(--muted)",
                    fontSize: "14px"
                  }}>
                    <b style={{ color: "#9DABBC", display: "block", marginBottom: "10px" }}>{kn ? "ತನಿಖಾ ಸೂಚಕಗಳು:" : "Investigative Pointers:"}</b>
                    <ul style={{ margin: "0", paddingLeft: "24px", display: "flex", flexDirection: "column", gap: "8px", lineHeight: 1.5 }}>
                      {h.pointers.map((p, j) => (
                        <li key={j}>{p}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="px-footer">
        {engine ? `${kn ? "ಎಂಜಿನ್" : "engine"}: ${engine} · ` : ""}
        {kn ? "ನಿರ್ಧಾರ-ಬೆಂಬಲ ಮಾತ್ರ · ತೀರ್ಪು ಅಲ್ಲ · ಅಧಿಕಾರಿ ತೀರ್ಮಾನ ಕಡ್ಡಾಯ" : "Decision support only. Not a verdict. The officer decides."}
      </div>

      {/* Model card modal - real /model-card */}
      {showCard && modelCard && (
        <>
          <div className="px-cardback" onClick={() => setShowCard(false)} />
          <div className="px-modelcard" role="dialog" aria-label="Model card">
            <button className="x" onClick={() => setShowCard(false)} aria-label="Close"></button>
            <b>{modelCard.model_name}</b>
            <span className="ty">{modelCard.type}</span>
            <div className="sec"><h6>{kn ? "ವಾಸ್ತುಶಿಲ್ಪ" : "Architecture"}</h6><p>{modelCard.architecture}</p></div>
            {modelCard.layer3_additions?.length > 0 && (
              <div className="sec">
                <h6>{kn ? "ಲೇಯರ್ 3 ಗುಪ್ತಚರ" : "Layer 3 Predictive Intelligence"}</h6>
                {modelCard.layer3_additions.map((item, i) => <p key={i}>{item}</p>)}
              </div>
            )}
            <div className="sec"><h6>{kn ? "ಉದ್ದೇಶಿತ ಬಳಕೆ" : "Intended use"}</h6><p>{modelCard.intended_use}</p></div>
            {modelCard.bias_disclosure?.length > 0 && (
              <div className="sec">
                <h6>{kn ? "ಪಕ್ಷಪಾತ ಬಹಿರಂಗ" : "Bias disclosure"}</h6>
                {modelCard.bias_disclosure.map((b, i) => <p key={i} className="bias">{b}</p>)}
              </div>
            )}
            <div className="sec"><h6>{kn ? "ತಪ್ಪು-ಧನಾತ್ಮಕ ರಕ್ಷಣೆ" : "False-positive mitigation"}</h6><p>{modelCard.false_positive_mitigation}</p></div>
            <div className="prov">{modelCard.data_provenance}</div>
          </div>
        </>
      )}

      {/* Derivation & audit modal - real /api/derivation */}
      {derivationModalData && (
        <>
          <div className="px-cardback" onClick={() => setDerivationModalData(null)} />
          <div className="px-modelcard" role="dialog" aria-label="Derivation & Audit Inspector" style={{ maxWidth: "680px", width: "92%" }}>
            <button className="x" onClick={() => setDerivationModalData(null)} aria-label="Close"></button>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
              <span style={{ fontSize: "10px", fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", background: "rgba(34,230,240,0.14)", color: "#22E6F0", padding: "4px 8px", borderRadius: "4px", border: "1px solid rgba(34,230,240,0.45)" }}>[AUDIT-GATE]</span>
              <div>
                <b style={{ fontSize: "16px" }}>{kn ? "ಚಾರ್ಜ್‌ಶೀಟ್ ಡೆರಿವೇಷನ್ ಮತ್ತು ಆಡಿಟ್" : "Chargesheet Derivation & Audit Inspector"}</b>
                <div style={{ fontSize: "11px", color: "#22E6F0", fontFamily: "monospace" }}>ID: {derivationModalData.product_id}</div>
              </div>
            </div>

            {(derivationModalData.derivation_chain || []).length > 0 && (
              <div className="sec">
                <h6>{kn ? "ಡೆರಿವೇಷನ್ ಹಂತಗಳು" : "Derivation Pipeline Stages"}</h6>
                {derivationModalData.derivation_chain.map((step, i) => (
                  <p key={i}><b style={{ color: "#22E6F0" }}>[{step.stage}]</b> {step.detail}</p>
                ))}
              </div>
            )}

            <div className="sec">
              <h6>{kn ? "ವಿಧಾನಗಳು ಮತ್ತು ಸೂತ್ರಗಳು" : "Methodology & Algorithms"}</h6>
              {(derivationModalData.method_lines || []).map((m, i) => (
                <p key={i} style={{ color: "var(--muted)" }}> {m}</p>
              ))}
            </div>

            {derivationModalData.chain_hash && (
              <div className="sec" style={{ background: "var(--field-bg)", border: "1px solid rgba(34,230,240,0.25)", padding: "10px", borderRadius: "8px" }}>
                <h6>{kn ? "ಡಿಜಿಟಲ್ ವಾಟರ್‌ಮಾರ್ಕ್ (SHA-256)" : "Evidentiary Cryptographic Watermark"}</h6>
                <div style={{ fontFamily: "monospace", fontSize: "10px", color: "var(--muted-2)", wordBreak: "break-all" }}>SHA-256: {derivationModalData.chain_hash}</div>
              </div>
            )}

            <div className="sec" style={{ borderTop: "1px solid var(--glass-border)", paddingTop: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "11px", color: "var(--muted)" }}>{kn ? "ಅಧಿಕಾರಿ ಪಾತ್ರ:" : "Officer Rank:"}</span>
                  <select value={officerRole} onChange={(e) => setOfficerRole(e.target.value)}
                    style={{ background: "var(--field-bg)", color: "var(--text)", border: "1px solid var(--glass-border)", borderRadius: "6px", padding: "4px 8px", fontSize: "12px" }}>
                    <option value="Inspector">Inspector (Authorized)</option>
                    <option value="ACP">ACP / SP (Authorized)</option>
                    <option value="Constable">Constable (RBAC Guard / Demo Block)</option>
                  </select>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button onClick={() => handleHypothesisAction(derivationModalData.product_id, "confirm")}
                    style={{ background: "rgba(34,230,240,0.14)", color: "#22E6F0", border: "1px solid rgba(34,230,240,0.5)", padding: "6px 12px", borderRadius: "7px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>
                     {kn ? "ಖಚಿತಪಡಿಸಿ" : "Confirm Hypothesis"}
                  </button>
                  <button onClick={() => handleHypothesisAction(derivationModalData.product_id, "reject")}
                    style={{ background: "rgba(225,64,56,0.14)", color: "#ff8089", border: "1px solid rgba(225,64,56,0.5)", padding: "6px 12px", borderRadius: "7px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>
                     {kn ? "ತಿರಸ್ಕರಿಸಿ" : "Reject Hypothesis"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {confirmToast && (
        <div style={{
          position: "fixed", bottom: "24px", right: "24px", zIndex: 99999,
          background: "var(--surface)", color: "var(--text)", border: "1px solid rgba(34,230,240,0.5)",
          padding: "12px 18px", borderRadius: "8px", boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
          fontSize: "13px", fontWeight: 500,
        }}>
          {confirmToast}
        </div>
      )}
    </div>
  );
}


