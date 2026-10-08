"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useLang } from "@/components/Providers";
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
const cap = (s) => (s || "").replace(/_/g, " ").split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(" ");
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
        <span className="pxd-granhint">{kn ? "ಬಿಂದು ಕ್ಲಿಕ್ ಮಾಡಿ" : "click a point"}</span>
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
              <path d={line} className="pxd-liner" fill="none" />
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
              <b>{cur.value}</b>
              <span className={rising ? "up" : "down"}>
                {dPct == null ? cur.label : `${dPct > 0 ? "▲ +" : dPct < 0 ? "▼ " : ""}${dPct}%`}
              </span>
            </div>
          </div>

          <div className="pxd-xlabels">{ticks.map((ti) => <span key={ti}>{series[ti].label}</span>)}</div>

          <div className="pxd-selline">
            <b>{cur.label}</b> · {cur.value} {g.unit}
            {dPct != null && <> · {dPct > 0 ? "+" : ""}{dPct}% {kn ? "ಹಿಂದಿನ ಎದುರು" : "vs prev"}</>}
            {cur.partial && <span className="pxd-partial">{kn ? "ಭಾಗಶಃ" : "partial / YTD"}</span>}
          </div>

          <div className="pxd-stats">
            <span><i>{kn ? "ಒಟ್ಟು" : "Total"}</i>{g.total}</span>
            <span><i>{kn ? "ಸರಾಸರಿ" : "Avg"}</i>{g.avg}</span>
            <span><i>{kn ? "ಗರಿಷ್ಠ" : "Peak"}</i>{g.peak}</span>
          </div>
        </>
      )}
    </div>
  );
}

const PREDICT_MODERN_STYLES = `
/* Modern Industry-Ready Overrides for Predict Dashboard */
.px-page { background: #030712; color: #f8fafc; }
.px-title { background: linear-gradient(135deg, #22d3ee 0%, #818cf8 100%); -webkit-background-clip: text; color: transparent; font-size: 26px; }
.px-sub { font-size: 13px; color: #94a3b8; font-weight: 500; }
.px-howbtn { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); color: #cbd5e1; border-radius: 8px; font-weight: 600; padding: 6px 14px; transition: all 0.2s; }
.px-howbtn:hover { background: rgba(255,255,255,0.08); color: #fff; }

.px-dash { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; padding-bottom: 20px; }
.pxd-card { display: flex; flex-direction: column; min-height: 400px; max-height: 440px; border-radius: 20px; background: rgba(15, 23, 42, 0.4); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.06); box-shadow: 0 12px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05); padding: 20px; }
.pxd-hd { margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 12px; }
.pxd-ttl { font-size: 16px; font-weight: 700; color: #f1f5f9; letter-spacing: 0.02em; }
.pxd-sub { background: rgba(255,255,255,0.04); padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #94a3b8; }

.pxd-scroll { flex: 1; overflow-y: auto; padding-right: 6px; }
.pxd-scroll::-webkit-scrollbar { width: 4px; }
.pxd-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }

.px-card { display: flex; flex-direction: column; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 14px; padding: 14px; margin-bottom: 10px; cursor: pointer; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden; }
.px-card:hover { background: rgba(255,255,255,0.04); border-color: rgba(255,255,255,0.12); transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.2); }
.px-card.on { background: rgba(34,230,240,0.05); border-color: rgba(34,230,240,0.35); box-shadow: 0 4px 20px rgba(34,230,240,0.1); }
.px-card.on::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: #22d3ee; border-radius: 3px 0 0 3px; }

.px-card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.px-zone { font-size: 15px; font-weight: 600; color: #f8fafc; letter-spacing: -0.01em; }

.px-risk { font-family: "JetBrains Mono", monospace; font-size: 10px; font-weight: 700; padding: 4px 8px; border-radius: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
.px-risk-h { color: #fca5a5; background: rgba(248,113,113,0.1); border: 1px solid rgba(248,113,113,0.2); }
.px-risk-m { color: #fde047; background: rgba(250,204,21,0.1); border: 1px solid rgba(250,204,21,0.2); }
.px-risk-l { color: #94a3b8; background: rgba(148,163,184,0.1); border: 1px solid rgba(148,163,184,0.2); }

.px-crime-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.px-crime { font-size: 13px; color: #cbd5e1; font-weight: 500; }
.px-know { font-size: 10px; font-weight: 700; padding: 5px 12px; background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.2); border-radius: 8px; color: #7dd3dc; transition: all 0.2s; white-space: nowrap; }
.px-know:hover { background: rgba(56,189,248,0.2); border-color: rgba(56,189,248,0.4); color: #bae6fd; }

.px-confpct { color: #22d3ee; font-weight: 700; font-size: 12px; }
.px-meta { margin-top: 10px; font-size: 11px; color: #64748b; }
.px-tag { font-size: 10.5px; padding: 3px 8px; border-radius: 6px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); color: #94a3b8; }
.px-tag.ok { color: #22d3ee; border-color: rgba(34,230,240,0.25); background: rgba(34,230,240,0.06); }

/* Stats Row */
.px-statrow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 10px; margin-bottom: 24px; }
.px-statbox { display: flex; flex-direction: column; background: rgba(15, 23, 42, 0.4); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 20px 24px; box-shadow: 0 8px 24px rgba(0,0,0,0.2); transition: transform 0.2s; }
.px-statbox:hover { transform: translateY(-2px); }
.px-statbox .l { font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.08em; margin-bottom: 12px; }
.px-statbox .v { font-size: 34px; font-weight: 800; color: #f8fafc; }
.px-statbox .v.cyan { color: #22d3ee; }
.px-statbox .v.red { color: #f87171; }

/* Explanation Panel */
.px-explain { background: rgba(15, 23, 42, 0.5); backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; box-shadow: 0 16px 48px rgba(0,0,0,0.4); }
.px-panel-hd { padding: 18px 24px; border-bottom: 1px solid rgba(255,255,255,0.06); display: flex; justify-content: space-between; align-items: center; font-size: 15px; font-weight: 700; color: #f1f5f9; }
.px-hint { font-size: 12px; font-weight: 500; color: #64748b; }
.px-insp { padding: 24px; }
.px-insp-title { font-size: 22px; font-weight: 800; color: #fff; margin-bottom: 8px; }
.px-insp-why { font-size: 14px; color: #94a3b8; line-height: 1.6; margin-bottom: 20px; }
.px-big .n { font-size: 42px; font-weight: 800; color: #f8fafc; }
.px-big .z { font-size: 14px; font-weight: 700; color: #f87171; background: rgba(248,113,113,0.1); padding: 4px 10px; border-radius: 8px; margin-left: 12px; }

.px-bandbox { font-size: 14px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; color: #cbd5e1; }
.px-bandbox b { color: #22d3ee; font-size: 15px; font-weight: 700; }

.px-tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
.px-tile { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 16px; transition: background 0.2s; }
.px-tile:hover { background: rgba(255,255,255,0.04); }
.px-tile .tv { font-size: 18px; font-weight: 800; color: #f8fafc; margin-bottom: 4px; }
.px-tile .tl { font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }

.px-acts { display: flex; flex-wrap: wrap; gap: 10px; }
.px-actbtn { font-size: 13px; font-weight: 600; padding: 10px 18px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); color: #cbd5e1; transition: all 0.2s; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.px-actbtn:hover { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.2); color: #fff; transform: translateY(-1px); }
.px-actbtn.cy { background: rgba(34,230,240,0.08); border-color: rgba(34,230,240,0.3); color: #22d3ee; }
.px-actbtn.cy:hover { background: rgba(34,230,240,0.15); border-color: rgba(34,230,240,0.5); box-shadow: 0 4px 16px rgba(34,230,240,0.2); }

.px-suggest { background: linear-gradient(135deg, rgba(34,230,240,0.08) 0%, rgba(16,185,129,0.08) 100%); border: 1px solid rgba(34,230,240,0.25); border-radius: 16px; padding: 20px 24px; margin-bottom: 24px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 8px 24px rgba(0,0,0,0.15); }
.px-suggest-hd { font-family: "JetBrains Mono", monospace; font-size: 12px; font-weight: 700; color: #22d3ee; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 10px; }
.px-suggest-txt { font-size: 14px; color: #f8fafc; line-height: 1.6; }

.px-prov-hd { font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 8px; }
.px-prov-ids { font-family: "JetBrains Mono", monospace; font-size: 11px; color: #64748b; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 8px; border: 1px dashed rgba(255,255,255,0.1); }
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
            <div className="px-sub" style={{ fontSize: "13px", color: "rgba(255,255,255,0.7)" }}>
              {kn ? "ಮುಂದಿನ 7 ದಿನಗಳ ವಿಶ್ಲೇಷಣೆ • ಇಂಟೆಲಿಜೆನ್ಸ್ ಆಧಾರಿತ ಮುನ್ಸೂಚನೆ" : "7-Day Predictive Analysis • Intelligence-Driven Foresight and Risk Assessment"}
            </div>
        </div>
        <div className="px-head-r">
          {boardMeta && <span className="px-chip">{kn ? "ಮೌಲ್ಯಮಾಪನ" : "assessed"} <b>{boardMeta.as_of}</b></span>}
          {boardMeta?.zones_covered != null && <span className="px-chip"><b>{boardMeta.zones_covered}</b> {kn ? "ವಲಯ" : "zones"}</span>}
          {offlineSample && <span className="px-offline">{kn ? "ಆಫ್‌ಲೈನ್ · ಮಾದರಿ" : "OFFLINE · sample"}</span>}
          {modelCard && (
            <button className="px-howbtn" onClick={() => {
              const btn = document.getElementById("cx-guide-trigger");
              if (btn) btn.click();
            }}>
              ⓘ {kn ? "ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ" : "How it works"}
            </button>
          )}
        </div>
      </div>

      {/* Hero row: Predict next 7 days · Volume trend · Antar Alert */}
      <div className="px-dash">
        {/* 1 · Predict · Next 7 Days (scrollable) */}
        <div className="pxd-card">
          <div className="pxd-hd">
            <span className="pxd-ttl">{kn ? "ಮುನ್ಸೂಚನೆ · ಮುಂಬರುವ 7 ದಿನಗಳು" : "Forecast • Upcoming 7 Days"}</span>
            <span className="pxd-sub">{predictions?.length ?? 0} {kn ? "ವಲಯ" : "zones"}</span>
          </div>
          <div className="pxd-scroll" role="group" aria-label={kn ? "ಹಾಟ್‌ಸ್ಪಾಟ್ ಪ್ರಾಧಾನ್ಯ" : "Hotspot rankings"}>
            {predictions === null && (
              <div className="px-loading">{kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Loading…"}<div className="signal-pulse" style={{ marginTop: 10 }} /></div>
            )}
            {predictions?.length === 0 && (
              <div className="px-loading">{kn ? "ಸಕ್ರಿಯ ಮುನ್ಸೂಚನೆಗಳಿಲ್ಲ" : "no active predictions. the board is honest-empty."}</div>
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
                  <span className={`px-risk ${RISK_BADGE[p.risk] || ""}`}>{p.risk?.toLowerCase()}</span>
                  <span className="px-zone">{p.zone}</span>
                </div>
                <div className="px-crime-row">
                  <span className="px-crime">{cap(p.crime_type)}</span>
                  <button
                    type="button"
                    className="px-know" style={{ textTransform: "none", letterSpacing: "normal", fontWeight: 500 }}
                    onClick={(e) => { e.stopPropagation(); setFocusKind("prediction"); setSelected(i); setShowReasoning(true); }}
                    aria-label={`${kn ? "ತರ್ಕದಲ್ಲಿ ಇನ್ನಷ್ಟು ತಿಳಿಯಿರಿ" : "Know more in reasoning"} - ${p.zone}`}
                  >
                    {kn ? "ಸಂದರ್ಭವನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ" : "Understand Context"}
                  </button>
                </div>
                <div className="px-confbar">
                  <div className="px-conftrack"><div className="px-conffill" style={{ width: `${pct(p.confidence)}%` }} /></div>
                  <span className="px-confpct">{pct(p.confidence)}%</span>
                </div>
                <div className="px-meta">
                  {p.z_score ? <span>z = {p.z_score}</span> : null}
                  {p.band ? <span>{kn ? "ನಿರೀಕ್ಷಿತ" : "expected"} {p.band}</span> : null}
                </div>
                {p.direction === "silence" && <span className="px-tag">[{kn ? "ಅಸಂಗತಿ" : "anomaly"}] {kn ? "ಮೌನ ಇಳಿಕೆ" : "silence drop"}</span>}
                {p.festival_driver && <span className="px-tag">[{kn ? "ಘಟನೆ" : "event"}] {p.festival_driver}</span>}
                {acked.has(keyOf(p)) && <span className="px-tag ok"> {kn ? "ಪರಿಶೀಲಿಸಲಾಗಿದೆ" : "Reviewed"}</span>}
              </div>
            ))}
          </div>
        </div>

        {/* 2 · Prediction Volume Trend */}
        <div className="pxd-card">
          <div className="pxd-hd" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                <span className="pxd-ttl">{kn ? "ಮುನ್ಸೂಚನೆ ಪರಿಮಾಣದ ಪ್ರವೃತ್ತಿ" : "Prediction Volume Trend"}</span>
                <span className="pxd-sub" style={{ border: '1px solid rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px' }}>{dash && dash !== "offline" ? (kn ? "ಲೈವ್" : "live") : "—"}</span>
              </div>
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', fontWeight: 400, textTransform: 'none', letterSpacing: 'normal' }}>
                {kn ? "ಐತಿಹಾಸಿಕ ಡೇಟಾದ ವಿರುದ್ಧ ಊಹಿಸಲಾದ ಸಂಪುಟಗಳು" : "Predicted incident volumes charted against historical baselines"}
              </span>
            </div>
          {dash && dash !== "offline"
            ? <VolumeTrend volume={dash.volume} kn={kn} />
            : <div className="pxd-empty">{kn ? "ಬ್ಯಾಕೆಂಡ್ ಆಫ್‌ಲೈನ್" : "Backend offline - start the Antar API."}</div>}
        </div>

        {/* 3 · Antar Alert (all, scrollable, clickable) */}
        <div className="pxd-card">
          <div className="pxd-hd" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                <span className="pxd-ttl">{kn ? "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು" : "Active Alerts"}</span>
                <span className="pxd-sub" style={{ border: '1px solid rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px' }}>{alertList.length} {kn ? "ಸಕ್ರಿಯ" : "active"}</span>
              </div>
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', fontWeight: 400, textTransform: 'none', letterSpacing: 'normal' }}>
                {kn ? "ರಿಯಲ್-ಟೈಮ್ ಅಸಂಗತತೆಗಳು ಮತ್ತು ಪತ್ತೆಯಾದ ಅಪಾಯದ ಏರಿಕೆಗಳು" : "Real-time anomalies and localized risk spikes"}
              </span>
            </div>
          <div className="pxd-scroll pxd-alerts">
            {alertList.length === 0 && <div className="pxd-empty">{kn ? "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆ ಇಲ್ಲ" : "No active alerts"}</div>}
            {alertList.map((a, i) => {
              const z = a.z_score ?? 0;
              const hi = z >= 4;
              const sev = hi ? "hi" : "md";
              const sevlbl = hi ? "HIGH" : z >= 2.5 ? "MED" : "LOW";
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
                      {cap(a.crime_type)} · {a.zone}
                      <span className={`pxd-sev ${sev}`}>{sevlbl}</span>
                    </div>
                    <div className="pxd-alert-sub">
                      {a.anomaly_type ? cap(a.anomaly_type) : a.direction === "silence" ? (kn ? "ವರದಿ ಮೌನ" : "reporting silence") : (kn ? "ಅಸಂಗತಿ" : "anomaly")} · z = {Number(z).toFixed(2)}
                    </div>
                  </div>
                  <span className={`pxd-adot ${sev}`} />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Hotspots KPI strip */}
      <div className="px-statrow">
        <div className="px-stattile">
          <div className="l">{kn ? "ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳು" : "hotspots"}</div>
          <div className="v">{predictions?.length ?? "—"}</div>
        </div>
        <div className="px-stattile">
          <div className="l">{kn ? "ಹೆಚ್ಚಿನ ಅಪಾಯ" : "high risk"}</div>
          <div className="v red">{predictions?.filter((p) => p.risk === "HIGH").length ?? "—"}</div>
        </div>
        <div className="px-stattile">
          <div className="l">{kn ? "ಮೌನ ಎಚ್ಚರಿಕೆಗಳು" : "silence alerts"}</div>
          <div className="v">{predictions?.filter((p) => p.direction === "silence").length ?? 0}</div>
        </div>
        <div className="px-stattile">
          <div className="l">{kn ? "ಸರಾಸರಿ ವಿಶ್ವಾಸ" : "avg confidence"}</div>
          <div className="v cyan">{avgConf != null ? `${avgConf}%` : "—"}</div>
        </div>
      </div>

      {/* Explanation section - full width, drives off the focused prediction OR alert */}
      <div className="px-panel px-explain" ref={reasonRef}>
        <div className="px-panel-hd">
          <span>{kn ? "ಮುನ್ಸೂಚನೆ ವಿವರಣೆ" : "Prediction Explanation"}</span>
          <span className="px-hint">
            {focusKind === "alert" ? (kn ? "ಅಂತರ ಎಚ್ಚರಿಕೆಯಿಂದ" : "from Antar Alert") : (kn ? "ಮುಂದಿನ 7 ದಿನಗಳಿಂದ" : "from Predict · next 7 days")}
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
                <div>
                  <div className="px-insp-title">{focusItem.zone} - {cap(focusItem.crime_type)}</div>
                  <div className="px-insp-why">{focusItem.why || (kn ? "ಸ್ಪಟಿಯೊಟೆಂಪೊರಲ್ ಅಸಂಗತಿ ಪತ್ತೆ" : "Spatiotemporal hotspot anomaly detected.")}</div>

                  <div className="px-big">
                    <span className="n">{pct(focusItem.confidence)}%</span>
                    {focusItem.z_score
                      ? <span className="z">▲ z = {focusItem.z_score} {kn ? "ಅಸಂಗತಿ" : "anomaly"}</span>
                      : <span className="z base">{kn ? "ಬೇಸ್‌ಲೈನ್" : "baseline"}</span>}
                    <span className={`px-risk ${RISK_BADGE[focusItem.risk] || ""}`}>{focusItem.risk?.toLowerCase()}</span>
                  </div>

                  {focusItem.band && (
                    <div className="px-bandbox">
                      {kn ? "ನಿರೀಕ್ಷಿತ ಅವಧಿ" : "Expected window"} <b>{focusItem.band}</b>
                      {focusItem.coverage ? ` · ${focusItem.coverage} ${kn ? "ಕಾನ್ಫಾರ್ಮಲ್" : "conformal"}` : ""}
                      {focusItem.festival_driver ? ` · ${focusItem.festival_driver}` : ""}
                    </div>
                  )}

                  <div className="px-tiles">
                    <div className="px-tile"><div className="tv">{focusItem.evidence_row_ids?.length ?? 0} FIRs</div><div className="tl">{kn ? "ಸಾಕ್ಷ್ಯ ಸಾಲುಗಳು" : "Evidence rows"}</div></div>
                    <div className="px-tile"><div className="tv">{focusItem.coverage || "—"}</div><div className="tl">{kn ? "ಬ್ಯಾಂಡ್ ವ್ಯಾಪ್ತಿ" : "Band coverage"}</div></div>
                    <div className="px-tile"><div className="tv" style={{ textTransform: "capitalize" }}>{focusItem.direction || "spike"}</div><div className="tl">{kn ? "ದಿಕ್ಕು" : "Direction"}</div></div>
                    <div className="px-tile"><div className="tv">{focusItem.festival_driver ? (kn ? "ಹೌದು" : "yes") : (kn ? "ಇಲ್ಲ" : "none")}</div><div className="tl">{kn ? "ಋತುಮಾನ ಚಾಲಕ" : "Seasonal driver"}</div></div>
                  </div>

                  {focusItem.evidence_row_ids?.length > 0 && (
                    <div className="px-prov">
                      <div className="px-prov-hd"><span className="dot" />{kn ? "ವಾರ್ನಿಂಗ್ ಲೆಡ್ಜರ್" : "Warning Ledger"} · {focusItem.evidence_row_ids.length} {kn ? "ಇನ್‌ಪುಟ್ FIR ಸಾಲುಗಳು" : "input FIR rows persisted for audit"}</div>
                      <div className="px-prov-ids">
                        {focusItem.evidence_row_ids.slice(0, 4).join(" · ")}{focusItem.evidence_row_ids.length > 4 ? ` · +${focusItem.evidence_row_ids.length - 4}` : ""}
                      </div>
                    </div>
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
                      {kn ? "ತರ್ಕ" : "Reasoning"} {showReasoning ? "▾" : "▸"}
                    </button>
                    <button className={`px-actbtn ${showScenario ? "on" : ""}`} onClick={() => setShowScenario((v) => !v)}>
                      {kn ? "ಸನ್ನಿವೇಶ" : "Scenario"} {showScenario ? "▾" : "▸"}
                    </button>
                    <button className="px-actbtn" onClick={() => openDerivationModal(focusItem.id || focusItem.zone || "HYP-101")}>
                      {loadingDerivation ? "…" : (kn ? "ಡೆರಿವೇಷನ್ ಆಡಿಟ್ ▸" : "Derivation audit ▸")}
                    </button>
                    <button className="px-actbtn" onClick={() => router.push(`/map?zone=${encodeURIComponent(focusItem.zone)}&crime_type=${focusItem.crime_type}`)}>
                      {kn ? "ನಕ್ಷೆ ▸" : "Map ▸"}
                    </button>
                    <button className="px-actbtn ask" onClick={() => askAntar(focusItem)}>
                      {kn ? "ಅಂತರ‍ಗೆ ಕೇಳಿ ▸" : "Ask a question ▸"}
                    </button>
                    {isAcked
                      ? <span className="px-ackdone"> {kn ? "ಪರಿಶೀಲಿಸಲಾಗಿದೆ" : "Acknowledged"}</span>
                      : <button className="px-actbtn ack" onClick={() => acknowledge(focusItem)}>{kn ? "ಸ್ವೀಕರಿಸಿ" : "Acknowledge"}</button>}
                  </div>

                  {showScenario && (
                    scenarioBand?.scenario ? (
                      <div className="px-scn">
                        <div className="px-scn-row">
                          <span className="px-scn-badge">{scenarioBand.scenario.badge || "INFERRED"} · {kn ? "ಸನ್ನಿವೇಶ ಬ್ಯಾಂಡ್" : "scenario band"}</span>
                          <span className="px-scn-val">{scenarioBand.scenario.lo}–{scenarioBand.scenario.hi} {kn ? "ಘಟನೆಗಳು" : "incidents"}</span>
                          <span className="px-scn-base">({kn ? "ಬೇಸ್‌ಲೈನ್ ಎದುರು" : "vs baseline"} {scenarioBand.baseline?.lo}–{scenarioBand.baseline?.hi})</span>
                        </div>
                        <div className="px-scn-narr">{scenarioBand.narrative}</div>
                      </div>
                    ) : (
                      <div className="px-scn muted">{kn ? "ಈ ವಲಯಕ್ಕೆ ಸನ್ನಿವೇಶ ಬ್ಯಾಂಡ್ ಇಲ್ಲ" : "No scenario band available for this zone."}</div>
                    )
                  )}
                </div>
              </div>

              {/* Inline reasoning - DAG + live trace, right where the officer is looking */}
              {showReasoning && (
                <div className="px-reason">
                  <div className="px-drawer-hd">
                    <span className="px-dagttl">{kn ? "ಏಜೆಂಟ್ ತರ್ಕ ಗ್ರಾಫ್" : "Agent Reasoning Graph"} · <span className="px-dagzone">{focusItem.zone}</span></span>
                    {streaming && <span className="px-live"><span className="d" />{kn ? "ಲೈವ್" : "LIVE"}</span>}
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
                      <div className="px-consolehdr"><span className="px-consolettl">{kn ? "ತರ್ಕ ಟ್ರೇಸ್" : "Reasoning Trace"}</span></div>
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
        {kn ? "ನಿರ್ಧಾರ-ಬೆಂಬಲ ಮಾತ್ರ · ತೀರ್ಪು ಅಲ್ಲ · ಅಧಿಕಾರಿ ತೀರ್ಮಾನ ಕಡ್ಡಾಯ" : "Decision-support only · Not a verdict · Officer judgement required"}
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
          [LEDGER STATUS] {confirmToast}
        </div>
      )}
    </div>
  );
}


