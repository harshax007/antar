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
import ForecastWhy from "@/components/ForecastWhy";
import ShiftPlan from "@/components/ShiftPlan";
import EngineOverall from "@/components/EngineOverall";

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
  { id: "pattern", kind: "agent", label: "Pattern scan", sublabel: "Cluster: chain-snatching", x: 280, y: 130 },
  { id: "forecast", kind: "agent", label: "Forecast model", sublabel: "Band: 8-11 @ 91% conf", x: 280, y: 270 },
  { id: "network", kind: "agent", label: "Network check", sublabel: "Local hub / Rajajinagar", x: 280, y: 400 },
  { id: "supervisor", kind: "llm", label: "Weighing", sublabel: "drivers weighed", x: 520, y: 270 },
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
  "Forecast model ▸ Range 8-11 incidents · z=3.48",
  "Weighing ▸ seasonal + pattern + forecast converge → HIGH",
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

// The server names its reasoning steps after the code that runs them ("forecast_agent").
// On this page they are shown as what they are: steps of one engine.
const STEP_KIND = { data: "records", signal: "signal", agent: "step", llm: "weighing", out: "result" };
const stepName = (t) => {
  const w = String(t || "").replace(/_agent$/i, "").replace(/_/g, " ").trim();
  return /^supervisor$/i.test(w) ? "Weighing" : w.charAt(0).toUpperCase() + w.slice(1);
};

function DagNode({ data }) {
  const s = NODE_KIND_STYLE[data.kind] || NODE_KIND_STYLE.data;
  return (
    <div className="dag-node" style={{ background: s.bg, borderColor: s.border }}>
      <Handle type="target" position={Position.Left} style={{ background: s.border }} />
      <div className="dag-kind">{STEP_KIND[data.kind] || data.kind}</div>
      <div className="dag-label">{stepName(data.label)}</div>
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

const when = (iso) => { const d = new Date(iso); return Number.isNaN(d.getTime()) ? iso : `${d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}, ${d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false })}`; };
const monthOf = (iso) => { const d = new Date(`${iso}T00:00:00`); return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-IN", { month: "short", year: "numeric" }); };
const LEVELS = ["Limited", "Moderate", "High"];
const LEVEL_SAYS = {
  High: "The ranges have held against the real register and the data is current.",
  Moderate: "The method is graded; one limit on the data is stated below. Read the ranges as a guide.",
  Limited: "Treat this week's figures as indicative only.",
};

// ── How far to trust it ───────────────────────────────────────────────────────────
// One line until it is opened: the level, its meaning, and a count of the reasons. The
// reasons and the rule that sets the level are a click away, so the page opens on what
// to act on and not on a paragraph about the model.
function EngineConfidence({ eng, open, onToggle, anchor }) {
  if (eng === null) return <section className="px-conf is-wait" ref={anchor}><p>Reading the engine status…</p></section>;
  if (eng === "missing") {
    return (
      <section className="px-conf is-wait" ref={anchor}>
        <p><b>Engine status is not loaded.</b> This server was started before the engine status and the event calendar were added. Restart it to see how far the forecast can be trusted, and the events ahead.</p>
      </section>
    );
  }
  const c = eng.confidence || {};
  const at = Math.max(0, LEVELS.indexOf(c.level));
  const n = (c.reasons || []).length;
  return (
    <section className={`px-conf${open ? " open" : ""}`} ref={anchor} aria-label="Engine confidence">
      <button type="button" className="px-conf-bar" aria-expanded={open} onClick={onToggle}>
        <span className="px-conf-k">Engine confidence</span>
        <b className={`px-conf-lv l-${c.level}`}>{c.level || "—"}</b>
        <span className="px-eng-meter" role="img" aria-label={`Step ${at + 1} of 3`}>
          {LEVELS.map((l, i) => <i key={l} className={i <= at ? `on l-${c.level}` : ""} />)}
        </span>
        <span className="px-conf-says">{LEVEL_SAYS[c.level] || ""}</span>
        <span className="px-conf-more">{open ? "Hide the reasons" : `Show the ${n} reasons`}<i aria-hidden="true">{open ? "▴" : "▾"}</i></span>
      </button>
      {open && (
        <div className="px-conf-body">
          <ul className="px-eng-why">
            {(c.reasons || []).map((x, i) => <li key={i} className={x.ok ? "ok" : "no"}>{x.text}</li>)}
          </ul>
          <div className="px-conf-rule">
            <h4>How the level is set</h4>
            <p><b>High</b> needs the graded ranges to have held and the records to be current. It is capped at <b>Moderate</b> when the latest weeks are not real records, or when the ranges held less often than stated. It falls to <b>Limited</b> when the forecast has not been graded, or when too few cases are on record.</p>
            <p>A green mark is a reason that counts for the forecast; an amber one counts against it.</p>
          </div>
          <EngineOverall />
        </div>
      )}
    </section>
  );
}

// ── What it is built on: the records, and the calendar from the internet ──────────
function KnownData({ eng }) {
  const r = (eng && eng !== "missing" && eng.records) || {}, t = eng && eng !== "missing" ? eng.track_record : null;
  const ready = eng && eng !== "missing";
  return (
    <div className="pxd-card px-src">
      <div className="pxd-hd pxd-hd2"><div>
        <span className="pxd-ttl">Known data <i>FIR records</i></span>
        <span className="pxd-note">What the engine read, and how its forecasts held up against the real register.</span>
      </div></div>
      {!ready ? <div className="pxd-empty">{eng === null ? "Reading…" : "Not loaded. Restart the server."}</div> : (
        <dl>
          <div><dt>Cases read</dt><dd><b>{num(r.cases_13w)}</b> in the last 13 weeks<span>{num(r.cases_52w)} in the last 52 weeks</span></dd></div>
          <div><dt>Areas</dt><dd><b>{num(r.areas)}</b> with enough records</dd></div>
          <div><dt>Read through</dt><dd><b>{r.through ? dayOf(r.through) : "—"}</b></dd></div>
          {r.real_record_ends && (
            <div><dt>Real register</dt><dd>through <b>{dayOf(r.real_record_ends)}</b>
              {r.recent_real_share != null && r.recent_real_share < 0.5 ? <span>Weeks after that are demonstration records in this build.</span> : null}</dd></div>
          )}
          {t ? (
            <>
              <div><dt>Track record</dt><dd><b>{(t.coverage80 * 100).toFixed(1)}%</b> of the 80% ranges held<span>{t.weeks} weeks of the real register, {monthOf(t.from)} to {monthOf(t.to)}; station forecasts</span></dd></div>
              <div><dt>90% ranges</dt><dd><b>{(t.coverage90 * 100).toFixed(1)}%</b> held</dd></div>
              <div><dt>Total forecast</dt><dd><b>{num(Math.round(t.forecast_total))}</b> against <b>{num(t.actual_total)}</b> recorded<span>over the graded weeks</span></dd></div>
              <div><dt>Against a plain average</dt><dd><b>{t.weeks_better} of {t.weeks_ranked}</b> weeks better<span>than ranking stations by their last 4 weeks</span></dd></div>
            </>
          ) : <div><dt>Track record</dt><dd>Not graded yet</dd></div>}
        </dl>
      )}
    </div>
  );
}

function InternetData({ eng, onEvents }) {
  const ready = eng && eng !== "missing";
  const cal = (ready && eng.calendar) || {}, evs = (ready && eng.events) || [];
  return (
    <div className="pxd-card px-src">
      <div className="pxd-hd pxd-hd2"><div>
        <span className="pxd-ttl">Internet data <i>event calendar</i></span>
        <span className="pxd-note">Where festival dates come from. What a festival does to crime is never taken from the internet.</span>
      </div></div>
      {!ready ? <div className="pxd-empty">{eng === null ? "Reading…" : "Not loaded. Restart the server."}</div> : (
        <dl>
          <div><dt>Source</dt><dd><b>{cal.name || "—"}</b><span>{cal.note}</span></dd></div>
          <div><dt>Last checked</dt><dd><b>{cal.checked_at ? when(cal.checked_at) : "Not reached"}</b></dd></div>
          <div><dt>Events ahead</dt><dd><b>{evs.length}</b> under way or within 3 weeks
            {evs.length > 0 && <span>{evs.map((e) => e.name).join(", ")}</span>}</dd></div>
          <div><dt>What is taken</dt><dd>Only the date of a listed festival.<span>What an event does is measured from past FIRs: the cases registered during it against the 4 weeks either side.</span></dd></div>
          {evs.length > 0 && <div><dt /><dd><button type="button" className="px-linkbtn" onClick={onEvents}>See what past years show</button></dd></div>}
        </dl>
      )}
    </div>
  );
}

// One measured line: a bar that runs left of the centre for "lower", right for "higher".
function EffectRow({ label, ef, soft }) {
  if (!ef) return null;
  const w = Math.min(50, Math.abs(ef.percent) / 2);          // 100% = half the track
  return (
    <div className={`px-ef${soft ? " soft" : ""}`}>
      <span className="px-ef-l">{label}{soft ? <i>less certain</i> : null}</span>
      <span className="px-ef-bar" aria-hidden="true">
        <i className={ef.percent >= 0 ? "up" : "dn"} style={ef.percent >= 0 ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }} />
      </span>
      <span className="px-ef-v"><b className={ef.percent >= 0 ? "up" : "dn"}>{Math.abs(ef.percent)}% {ef.percent >= 0 ? "higher" : "lower"}</b>
        <em>{num(ef.seen)} cases against {num(ef.expected >= 20 ? Math.round(ef.expected) : ef.expected)} expected; higher in {ef.years_higher} of {ef.years} years</em></span>
    </div>
  );
}

function EventCard({ ev, areas, onOpen }) {
  const o = ev.overall, n = ev.occurrences_measured || 0;
  const ups = [...(ev.rises || []), ...(ev.watch || [])];
  const reading = !o ? "The record has too few past years to measure this event here."
    : o.clear && o.percent < 0 ? "Fewer cases are registered while this is on than in the weeks around it. The record does not say why: it can be less crime, or slower reporting and registration during the event."
    : o.clear && o.percent > 0 ? "More cases are registered while this is on than in the weeks around it."
    : "Registered cases overall do not move clearly with this event.";
  return (
    <article className="px-ev">
      <header>
        <div>
          <h4>{ev.name}</h4>
          <p>{ev.what}</p>
        </div>
        <span className={`px-ev-when ${ev.phase === "under way" ? "now" : ""}`}>{ev.when}</span>
      </header>
      {n >= 4 ? (
        <>
          <h5>What {n} past years show in {ev.measured_in}{o ? ` (${o.from_year} to ${o.to_year})` : ""}</h5>
          <EffectRow label="All registered cases" ef={o} />
          {(ev.rises || []).map((x) => <EffectRow key={x.crime} label={cap(x.crime)} ef={x} />)}
          {(ev.watch || []).map((x) => <EffectRow key={x.crime} label={cap(x.crime)} ef={x} soft />)}
          {(ev.falls || []).slice(0, 2).map((x) => <EffectRow key={x.crime} label={cap(x.crime)} ef={x} />)}
        </>
      ) : null}
      <p className="px-ev-read">{reading}{ups.length ? ` What goes up: ${ups.map((x) => cap(x.crime).toLowerCase()).join(", ")}.` : ""}</p>
      <footer>
        <span>Date: {ev.date_source === "internet" ? "internet calendar" : ev.date_source === "fixed date" ? "fixed each year" : "built-in calendar"}</span>
        <span>Effect: measured from FIRs, compared with the 4 weeks either side</span>
        {areas.map((a) => <button type="button" key={a.zone} onClick={() => onOpen(a)}>Open {a.zone}</button>)}
      </footer>
    </article>
  );
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

.px-brief { display: flex; gap: 22px; align-items: center; margin-top: 14px; padding: 18px 22px; border: 1px solid #1a1a1a; border-radius: 12px; background: linear-gradient(100deg, rgba(34,211,238,0.06), rgba(5,5,5,0.9) 42%); }
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
.px-footer { font-family: 'Inter', sans-serif; font-size: 12px; }

/* ── The engine panel ── */
.px-eng { display: grid; grid-template-columns: 1.15fr 1fr 1fr; margin-top: 14px; border: 1px solid #1a1a1a; border-radius: 12px; background: #050505; animation: pxRise .4s ease both; }
.px-eng.is-wait { display: block; padding: 18px 22px; }
.px-eng.is-wait p { margin: 0; font-size: 14px; line-height: 1.6; color: #a3adb8; max-width: 78ch; }
.px-eng.is-wait b { color: #e6edf3; }
.px-eng-col { padding: 18px 22px; min-width: 0; }
.px-eng-col + .px-eng-col { border-left: 1px solid #161b22; }
.px-eng h3 { margin: 0 0 10px; font: 600 12.5px 'Inter', sans-serif; color: #a3adb8; }
.px-eng h3 em { font-style: normal; font-weight: 500; color: #6b7684; margin-left: 6px; }
.px-eng-level { font: 700 34px/1 'Chakra Petch', sans-serif; color: #e6edf3; }
.px-eng-level.l-High, .px-lvl.l-High, .px-big .n.l-High { color: #3fb950; }
.px-eng-level.l-Moderate, .px-lvl.l-Medium, .px-big .n.l-Medium { color: #e0a458; }
.px-eng-level.l-Limited, .px-lvl.l-Low, .px-big .n.l-Low { color: #9aa5b1; }
.px-eng-meter { display: flex; gap: 4px; margin: 10px 0 8px; max-width: 220px; }
.px-eng-meter i { flex: 1; height: 5px; border-radius: 3px; background: #1c2128; }
.px-eng-meter i.on.l-High { background: #3fb950; } .px-eng-meter i.on.l-Moderate { background: #e0a458; } .px-eng-meter i.on.l-Limited { background: #9aa5b1; }
.px-eng-says { margin: 0 0 12px; font-size: 13.5px; line-height: 1.5; color: #c9d1d9; }
.px-eng-why { list-style: none; margin: 0; padding: 0; display: grid; gap: 7px; }
.px-eng-why li { position: relative; padding-left: 18px; font-size: 13px; line-height: 1.5; color: #a3adb8; }
.px-eng-why li::before { content: ""; position: absolute; left: 2px; top: .55em; width: 7px; height: 7px; border-radius: 50%; }
.px-eng-why li.ok::before { background: #3fb950; } .px-eng-why li.no::before { background: #e0a458; }
.px-eng dl { margin: 0; display: grid; gap: 10px; }
.px-eng dl > div { display: grid; grid-template-columns: 108px 1fr; gap: 10px; align-items: baseline; }
.px-eng dt { font-size: 12px; color: #6b7684; }
.px-eng dd { margin: 0; font-size: 13.5px; line-height: 1.45; color: #c9d1d9; }
.px-eng dd b { color: #e6edf3; font-weight: 600; }
.px-eng dd span { display: block; margin-top: 2px; font-size: 12px; color: #7d8794; }

/* ── Events ahead ── */
.px-evs { margin-bottom: 28px; scroll-margin-top: 90px; }
.px-evs-hd { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; margin-bottom: 12px; }
.px-evs-hd h2 { margin: 0; font: 700 16px 'Chakra Petch', sans-serif; color: #e6edf3; }
.px-evs-hd span, .px-evs-none { font-size: 13px; color: #8b949e; }
.px-evs-none { margin: 0; padding: 16px 20px; border: 1px dashed #1f242b; border-radius: 12px; }
.px-ev { border: 1px solid #1a1a1a; border-radius: 12px; background: #050505; padding: 18px 22px; animation: pxRise .4s ease both; }
.px-ev + .px-ev { margin-top: 12px; }
.px-ev header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.px-ev h4 { margin: 0; font: 700 18px 'Chakra Petch', sans-serif; color: #e6edf3; }
.px-ev header p { margin: 4px 0 0; font-size: 13.5px; color: #a3adb8; }
.px-ev-when { flex: none; font-size: 12.5px; font-weight: 600; color: #c9d1d9; border: 1px solid #262b31; border-radius: 999px; padding: 4px 12px; }
.px-ev-when.now { color: #e0a458; border-color: rgba(224,164,88,.45); background: rgba(224,164,88,.07); }
.px-ev h5 { margin: 16px 0 8px; font: 600 12.5px 'Inter', sans-serif; color: #a3adb8; }
.px-ef { display: grid; grid-template-columns: minmax(150px, 1.1fr) minmax(120px, 1fr) minmax(220px, 1.6fr); gap: 14px; align-items: center; padding: 7px 0; border-top: 1px solid #12161b; }
.px-ef-l { font-size: 13.5px; color: #d5dce4; }
.px-ef-l i { font-style: normal; font-size: 11px; color: #8b949e; border: 1px solid #262b31; border-radius: 999px; padding: 0 7px; margin-left: 8px; white-space: nowrap; }
.px-ef-bar { position: relative; height: 8px; border-radius: 4px; background: #12161b; }
.px-ef-bar::after { content: ""; position: absolute; left: 50%; top: -3px; bottom: -3px; width: 1px; background: #39424d; }
.px-ef-bar i { position: absolute; top: 0; bottom: 0; border-radius: 4px; transform-origin: left; animation: pxGrow .7s ease-out both; }
.px-ef-bar i.up { background: #e0a458; } .px-ef-bar i.dn { background: #58a6ff; transform-origin: right; }
.px-ef.soft .px-ef-bar i { opacity: .55; }
.px-ef-v b { font-size: 13.5px; font-weight: 600; } .px-ef-v b.up { color: #e0a458; } .px-ef-v b.dn { color: #79b8ff; }
.px-ef-v em { display: block; font-style: normal; font-size: 12px; color: #7d8794; }
.px-ev-read { margin: 12px 0 0; font-size: 13.5px; line-height: 1.55; color: #c9d1d9; max-width: 92ch; }
.px-ev footer { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; margin-top: 12px; font-size: 12px; color: #6b7684; }
.px-ev footer button { font: 600 12px 'Inter', sans-serif; color: #58a6ff; background: rgba(88,166,255,.08); border: 1px solid rgba(88,166,255,.3); border-radius: 6px; padding: 5px 12px; cursor: pointer; }
.px-ev footer button:hover { background: rgba(88,166,255,.16); }

/* confidence in words on a card, a scenario range, an event inside the explanation */
.px-conf2 { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; font-size: 12px; color: #8b949e; }
.px-lvl { font-weight: 600; }
.px-scn2 { margin-bottom: 8px; font-size: 12.5px; color: #a3adb8; }
.px-scn2 b { color: #e6edf3; font-weight: 600; }
.px-scn2 i, .px-evin i { font-style: normal; font-size: 11px; color: #d2a8ff; border: 1px solid rgba(210,168,255,.35); border-radius: 999px; padding: 0 7px; margin-left: 4px; white-space: nowrap; }
.px-tag.ev { color: #e0a458; border-color: rgba(224,164,88,.35); background: rgba(224,164,88,.07); margin-top: 8px; }
.px-big .n.lv { font-size: 38px; }
.px-evin { margin-bottom: 24px; padding: 14px 16px; border: 1px solid rgba(224,164,88,.25); border-left: 3px solid #e0a458; border-radius: 8px; background: rgba(224,164,88,.04); }
.px-evin h4 { margin: 0 0 6px; font: 600 14px 'Inter', sans-serif; color: #e6edf3; }
.px-evin h4 span { font-weight: 500; font-size: 12px; color: #e0a458; margin-left: 8px; }
.px-evin p { margin: 0; font-size: 13.5px; line-height: 1.55; color: #c9d1d9; }
.px-evin p + p { margin-top: 6px; }
.px-evin p.dim { color: #8b949e; font-size: 12.5px; }
.px-evin p b { color: #e6edf3; }
.px-brief-body li.k-ev::before { background: #e0a458; }
.px-brief { display: block; }
@media (max-width: 1100px) {
  .px-eng { grid-template-columns: 1fr 1fr; }
  .px-eng-col:first-child { grid-column: 1 / -1; border-bottom: 1px solid #161b22; }
  .px-eng-col:nth-child(2) { border-left: 0; }
}

/* ── Order of the page: act first, trust second, sources third ── */
.px-top { display: grid; grid-template-columns: 1.08fr 1fr 1fr; gap: 20px; margin-top: 16px; }
.px-top .pxd-card { min-height: 0; height: 560px; max-height: 560px; }
.px-sec { margin: 30px 0 12px; font: 600 13px 'Inter', sans-serif; color: #8b949e; }
.px-explain { margin-top: 20px; }
.px-linkbtn { font: 600 12px 'Inter', sans-serif; color: #58a6ff; background: none; border: 0; padding: 0; cursor: pointer; }
.px-linkbtn:hover { text-decoration: underline; } .px-linkbtn:disabled { color: #4b5563; cursor: default; text-decoration: none; }

.px-flt { display: flex; flex-wrap: wrap; gap: 6px; margin: -6px 0 12px; }
.px-flt button { font: 500 12px 'Inter', sans-serif; color: #a3adb8; background: #0b0d10; border: 1px solid #1f242b; border-radius: 999px; padding: 4px 10px; cursor: pointer; white-space: nowrap; }
.px-flt button i { font-style: normal; margin-left: 6px; color: #6b7684; font-variant-numeric: tabular-nums; }
.px-flt button:hover:not(:disabled) { color: #e6edf3; border-color: #39424d; }
.px-flt button.on { color: #e6edf3; background: rgba(88,166,255,.12); border-color: rgba(88,166,255,.5); }
.px-flt button.on i { color: #9ecbff; }
.px-flt button:disabled { opacity: .4; cursor: default; }
.px-flt input { flex: 1 1 150px; min-width: 0; font: 500 12.5px 'Inter', sans-serif; color: #e6edf3; background: #0b0d10; border: 1px solid #1f242b; border-radius: 999px; padding: 5px 12px; outline: none; }
.px-flt input:focus { border-color: rgba(88,166,255,.6); }
.px-flt input::placeholder { color: #5c6672; }

.px-briefcard .px-brief-body { padding-right: 8px; }
.px-briefcard .px-brief-body li { font-size: 14px; }
.px-trust { display: flex; align-items: center; gap: 10px; margin-top: 12px; padding: 10px 12px; width: 100%; text-align: left; cursor: pointer;
  border: 1px solid #1f242b; border-radius: 8px; background: #0b0d10; font: 500 12.5px 'Inter', sans-serif; color: #a3adb8; }
.px-trust:hover { border-color: #39424d; }
.px-trust b { font-size: 13.5px; }
.px-trust em { margin-left: auto; font-style: normal; font-weight: 600; color: #58a6ff; }

.px-conf { margin-top: 4px; border: 1px solid #1a1a1a; border-radius: 12px; background: #050505; overflow: hidden; scroll-margin-top: 90px; }
.px-conf.is-wait { padding: 16px 20px; } .px-conf.is-wait p { margin: 0; font-size: 14px; line-height: 1.6; color: #a3adb8; } .px-conf.is-wait b { color: #e6edf3; }
.px-conf-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; width: 100%; padding: 14px 20px; background: none; border: 0; cursor: pointer; text-align: left; font-family: 'Inter', sans-serif; }
.px-conf-bar:hover { background: rgba(255,255,255,.02); }
.px-conf-k { font-size: 13px; font-weight: 600; color: #a3adb8; }
.px-conf-lv { font: 700 20px 'Chakra Petch', sans-serif; }
.px-conf-lv.l-High { color: #3fb950; } .px-conf-lv.l-Moderate { color: #e0a458; } .px-conf-lv.l-Limited { color: #9aa5b1; }
.px-conf-bar .px-eng-meter { width: 120px; margin: 0; flex: none; }
.px-conf-says { flex: 1 1 260px; font-size: 13.5px; color: #c9d1d9; }
.px-conf-more { margin-left: auto; font-size: 12.5px; font-weight: 600; color: #58a6ff; white-space: nowrap; }
.px-conf-more i { font-style: normal; margin-left: 6px; }
.px-conf-body { display: grid; grid-template-columns: 1.4fr 1fr; gap: 28px; padding: 4px 20px 20px; border-top: 1px solid #161b22; animation: pxRise .25s ease both; }
.px-conf-body .px-eng-why { padding-top: 16px; }
.px-conf-rule { padding-top: 16px; }
.px-conf-rule h4 { margin: 0 0 6px; font: 600 12.5px 'Inter', sans-serif; color: #a3adb8; }
.px-conf-rule p { margin: 0 0 8px; font-size: 13px; line-height: 1.55; color: #a3adb8; }
.px-conf-rule b { color: #e6edf3; font-weight: 600; }

.px-built { display: grid; grid-template-columns: 1fr 1.1fr 1fr; gap: 20px; }
.px-built .pxd-card { min-height: 0; max-height: none; }
.px-src dl { margin: 0; display: grid; gap: 11px; }
.px-src dl > div { display: grid; grid-template-columns: 112px 1fr; gap: 10px; align-items: baseline; }
.px-src dt { font-size: 12px; color: #6b7684; }
.px-src dd { margin: 0; font-size: 13.5px; line-height: 1.45; color: #c9d1d9; }
.px-src dd b { color: #e6edf3; font-weight: 600; }
.px-src dd span { display: block; margin-top: 2px; font-size: 12px; color: #7d8794; }
.pxd-ttl i { font-style: normal; }

.px-stn { margin-bottom: 20px; padding: 14px 16px; border: 1px solid #1a1a1a; border-radius: 8px; background: #080808; }
.px-stn-hd { font: 600 13px 'Inter', sans-serif; color: #e6edf3; margin-bottom: 8px; }
.px-stn-hd i { font-style: normal; font-size: 11px; font-weight: 500; color: #d2a8ff; border: 1px solid rgba(210,168,255,.35); border-radius: 999px; padding: 0 7px; margin-left: 8px; }
.px-stn ol { margin: 0; padding-left: 20px; display: grid; gap: 8px; }
.px-stn li b { display: block; font-size: 13.5px; font-weight: 600; color: #e6edf3; }
.px-stn li span { font-size: 12.5px; line-height: 1.45; color: #a3adb8; }
.px-stn p { margin: 10px 0 0; font-size: 12px; color: #6b7684; }

@media (max-width: 1200px) {
  .px-top { grid-template-columns: 1fr 1fr; }
  .px-top .px-briefcard { grid-column: 1 / -1; height: auto; max-height: none; }
  .px-built { grid-template-columns: 1fr 1fr; }
  .px-built > :nth-child(2) { grid-column: 1 / -1; order: 3; }
}
@media (max-width: 820px) {
  .px-top, .px-built { grid-template-columns: 1fr; gap: 14px; }
  .px-top .pxd-card { height: auto; }
  .px-top .pxd-card:not(.px-briefcard) { max-height: 520px !important; }
  .px-conf-body { grid-template-columns: 1fr; gap: 4px; }
  .px-conf-more { margin-left: 0; }
  .px-src dl > div { grid-template-columns: 96px 1fr; }
}

@keyframes pxRise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes pxGrow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes pxDrawLine { to { stroke-dashoffset: 0; } }
@keyframes pxBob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
@media (max-width: 820px) {
  .px-statrow { grid-template-columns: repeat(2, 1fr) !important; }
  .px-statbox:last-child { grid-column: 1 / -1; }
  .px-eng { grid-template-columns: 1fr; gap: 0; padding: 4px 16px; }
  .px-eng-col { padding: 14px 0; border-left: 0 !important; border-top: 1px solid #161b22; }
  .px-eng-col:first-child { border-top: 0; }
  .px-ev header { flex-direction: column; gap: 8px; }
  .px-ef { grid-template-columns: 1fr; gap: 4px; }
  .px-ef-bar { order: 3; }
  .px-brief { flex-direction: column; align-items: flex-start; gap: 12px; padding: 16px; }
  .px-brief-who { flex-direction: row; width: auto; gap: 10px; }
}
@media (prefers-reduced-motion: reduce) {
  .px-statbox, .px-card, .px-fade, .px-brief-ai, .px-conffill, .px-eng, .px-ev, .px-ef-bar i { animation: none !important; }
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
  const [hypothesesList, setHypothesesList] = useState(null);   // null = not asked yet | { zone, hypotheses, examined } | { error }
  const [reading, setReading] = useState(null);      // Antar's worded reading of the board
  const [eng, setEng] = useState(null);              // engine status | "missing" (older server) | null while loading
  const eventsRef = useRef(null);
  const [engOpen, setEngOpen] = useState(false);     // the reasons behind the confidence level: closed until asked for
  const confRef = useRef(null);
  const [flt, setFlt] = useState("all");             // which forecasts are listed
  const [findArea, setFindArea] = useState("");
  const [whyUnit, setWhyUnit] = useState(null);       // the station whose forecast is taken apart
  const [planFor, setPlanFor] = useState(null);       // the station whose shift plan is open
  const [stations, setStations] = useState(null);    // station forecasts for the area being explained
  const [copied, setCopied] = useState(false);
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
    fetch(`${API}/api/predict/engine`).then((r) => (r.ok ? r.json() : "missing")).then(setEng).catch(() => setEng("missing"));
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

  // The stations to watch inside the area being explained: the back-tested station forecast
  // (the one the Map draws). An area that is not a police district has none, and shows none.
  useEffect(() => {
    setStations(null); setWhyUnit(null);
    if (!fZone) return;
    const ctrl = new AbortController();
    fetch(`${API}/api/forecast/hotspots?horizon=7&category=ALL&unit=station&limit=3&district=${encodeURIComponent(fZone)}`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setStations(d?.items?.length ? { zone: fZone, scope: d.scope, items: d.items.slice(0, 3) } : null))
      .catch(() => {});
    return () => ctrl.abort();
  }, [fZone]);

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

  // Proposed links between accused in the district being explained. The research agent
  // proposes them from shared signals; the advocate agent prices each against its base rate.
  // Nothing is shown that the server did not compute, and a district with none says so.
  const runHypotheses = () => {
    if (!fZone) return;
    setRunningHypotheses(true);
    fetch(`${API}/api/predict/hypotheses?zone=${encodeURIComponent(fZone)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d) => setHypothesesList({ zone: fZone, hypotheses: d.hypotheses || [], examined: d.examined || 0 }))
      .catch((st) => setHypothesesList({ zone: fZone, error: st === 404 ? "restart" : "failed" }))
      .finally(() => setRunningHypotheses(false));
  };
  // a result belongs to the district it was asked for
  useEffect(() => { setHypothesesList(null); }, [fZone]);

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
      + ` It rates this ${(RISK_WORD[item.risk] || "risk").toLowerCase()}`
      + (item.confidence_level ? `, with ${item.confidence_level.toLowerCase()} confidence.` : ` and is ${pct(item.confidence)}% confident.`)
      + (item.festival_driver ? ` Season: ${item.festival_driver.replace(/^Seasonal\s*/i, "").trim()} at this time of year.` : "");
  };

  // The week in a few counted sentences. Each one opens the area it is about.
  const P = predictions || [];
  const evsAhead = (eng && eng !== "missing" && eng.events) || [];
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
    ...evsAhead.filter((e) => e.in_forecast_window).map((e) => {
      const o = e.overall, up = (e.rises || [])[0] || (e.watch || [])[0];
      return { k: "ev", toEvents: true, t: `${e.name}: ${e.when.charAt(0).toLowerCase()}${e.when.slice(1)}.`
        + (o ? ` In ${o.years} past years ${e.measured_in} registered ${Math.abs(o.percent)}% ${o.percent < 0 ? "fewer" : "more"} cases in this window` : "")
        + (o && up ? `, while ${cap(up.crime).toLowerCase()} ran ${up.percent}% higher${(e.rises || []).length ? "" : " (less certain)"}.` : o ? "." : "") };
    }),
  ].filter(Boolean);
  const openItem = (it) => {
    const i = P.indexOf(it);
    if (i < 0) return;
    setFocusKind("prediction"); setSelected(i);
    setTimeout(() => reasonRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
  };

  const toEvents = () => eventsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  const toConfidence = () => { setEngOpen(true); setTimeout(() => confRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 60); };

  // The forecast list, narrowed. Each entry keeps its place in the full board, because the
  // selection is an index into it.
  const FILTERS = [
    ["all", "All", () => true],
    ["above", "Above normal", (x) => x.direction !== "silence" && (Number(x.z_score) || 0) >= 2],
    ["drops", "Reporting drops", (x) => x.direction === "silence"],
    ["event", "Event this week", (x) => (x.events || []).length > 0],
    ["sure", "High confidence", (x) => x.confidence_level === "High"],
  ];
  const needle = findArea.trim().toLowerCase();
  const passes = (FILTERS.find((f) => f[0] === flt) || FILTERS[0])[2];
  const shown = P.map((x, i) => ({ p: x, i })).filter(({ p: x }) => passes(x) && (!needle || String(x.zone).toLowerCase().includes(needle) || cap(x.crime_type).toLowerCase().includes(needle)));

  // The week as text an officer can paste into a briefing note.
  const copyBrief = async () => {
    const lines = [`Antar forecast for the next 7 days${boardMeta?.as_of ? `, assessed ${dayOf(boardMeta.as_of)}` : ""}`, ...brief.map((b) => `- ${b.t}`)];
    if (reading) lines.push("", reading);
    if (eng && eng !== "missing" && eng.confidence?.level) lines.push("", `Engine confidence: ${eng.confidence.level}. Decision support only; the officer decides.`);
    try { await navigator.clipboard.writeText(lines.join("\n")); setCopied(true); setTimeout(() => setCopied(false), 2200); } catch { /* clipboard not available */ }
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

      {/* What to act on, first: the forecast, the alerts, and the week in a few sentences */}
      <div className="px-top">
        {/* 1 · Predict · Next 7 Days (scrollable) */}
        <div className="pxd-card">
          <div className="pxd-hd">
            <span className="pxd-ttl">{kn ? "ಮುನ್ಸೂಚನೆ · ಮುಂಬರುವ 7 ದಿನಗಳು" : "Forecast for the next 7 days"}</span>
            <span className="pxd-sub">{shown.length === P.length ? P.length : `${shown.length} of ${P.length}`} {kn ? "ವಲಯ" : "areas"}</span>
          </div>
          <div className="px-flt" role="toolbar" aria-label="Narrow the forecast list">
            {FILTERS.map(([key, label, test]) => {
              const count = P.filter(test).length;
              return (
                <button type="button" key={key} className={flt === key ? "on" : ""} aria-pressed={flt === key}
                        disabled={key !== "all" && count === 0} onClick={() => setFlt(key)}>
                  {label}<i>{count}</i>
                </button>
              );
            })}
            <input type="search" value={findArea} onChange={(e) => setFindArea(e.target.value)}
                   placeholder="Find an area or crime type" aria-label="Find an area or crime type" />
          </div>
          <div className="pxd-scroll" role="group" aria-label={kn ? "ಹಾಟ್‌ಸ್ಪಾಟ್ ಪ್ರಾಧಾನ್ಯ" : "Hotspot rankings"}>
            {predictions === null && (
              <div className="px-loading"><div className="signal-pulse" /><div>{kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Working out the week…"}</div></div>
            )}
            {predictions?.length === 0 && (
              <div className="px-loading">{kn ? "ಸಕ್ರಿಯ ಮುನ್ಸೂಚನೆಗಳಿಲ್ಲ" : "No forecasts right now."}</div>
            )}
            {predictions?.length > 0 && shown.length === 0 && (
              <div className="px-loading">No area matches. <button type="button" className="px-linkbtn" onClick={() => { setFlt("all"); setFindArea(""); }}>Show all</button></div>
            )}
            {shown.map(({ p, i }) => (
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
                {p.scenario && (
                  <div className="px-scn2">With {p.scenario.event}: <b>{num(p.scenario.lo)} to {num(p.scenario.hi)} cases</b> <i>inferred</i></div>
                )}
                {p.confidence_level ? (
                  <div className="px-conf2">
                    <span className={`px-lvl l-${p.confidence_level}`}>{p.confidence_level} confidence</span>
                    <span>{num(p.basis?.cases_52w)} cases in 52 weeks</span>
                  </div>
                ) : (
                  <div className="px-confbar">
                    <div className="px-conftrack"><div className="px-conffill" style={{ width: `${pct(p.confidence)}%` }} /></div>
                    <span className="px-confpct">{pct(p.confidence)}% {kn ? "ವಿಶ್ವಾಸ" : "confident"}</span>
                  </div>
                )}
                {(p.events || []).map((e) => <span key={e.key} className="px-tag ev">{e.name}: {e.phase}</span>)}
                {p.festival_driver && <span className="px-tag">{p.festival_driver}</span>}
                {acked.has(keyOf(p)) && <span className="px-tag ok">{kn ? "ಪರಿಶೀಲಿಸಲಾಗಿದೆ" : "Reviewed"}</span>}
              </div>
            ))}
          </div>
        </div>

        {/* 3 · Active alerts (all, scrollable, clickable) */}
        <div className="pxd-card">
          <div className="pxd-hd pxd-hd2">
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

        {/* This week in brief: counted sentences, Antar's wording of them, and how far to trust it */}
        <div className="pxd-card px-briefcard">
          <div className="pxd-hd">
            <span className="pxd-ttl">{kn ? "ಈ ವಾರ ಸಂಕ್ಷಿಪ್ತವಾಗಿ" : "This week in brief"}</span>
            <button type="button" className="px-linkbtn" onClick={copyBrief} disabled={!brief.length}>{copied ? "Copied" : "Copy for a briefing note"}</button>
          </div>
          <div className="pxd-scroll px-brief-body">
          {predictions === null && <p className="px-brief-wait">{kn ? "ದಾಖಲೆಗಳನ್ನು ಓದುತ್ತಿದೆ…" : "Reading the records…"}</p>}
          {predictions?.length === 0 && <p className="px-brief-wait">{kn ? "ಸಕ್ರಿಯ ಮುನ್ಸೂಚನೆಗಳಿಲ್ಲ" : "There is nothing to forecast yet."}</p>}
          <ul>
            {brief.map((b, i) => (
              <li key={i} className={`k-${b.k}${b.go || b.toEvents ? " go" : ""}`} style={{ animationDelay: `${i * 90}ms` }}
                  onClick={b.go ? () => openItem(b.go) : b.toEvents ? toEvents : undefined} role={b.go || b.toEvents ? "button" : undefined} tabIndex={b.go || b.toEvents ? 0 : undefined}
                  onKeyDown={(e) => { if (e.key === "Enter") { if (b.go) openItem(b.go); else if (b.toEvents) toEvents(); } }}>
                {b.t}{b.go ? <em>{kn ? "ತೆರೆಯಿರಿ" : "Open"}</em> : b.toEvents ? <em>See what past years show</em> : null}
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
          <button type="button" className="px-trust" onClick={toConfidence}>
            <span>Engine confidence</span>
            <b className={`px-lvl l-${eng && eng !== "missing" ? ({ High: "High", Moderate: "Medium", Limited: "Low" }[eng.confidence?.level] || "Low") : "Low"}`}>
              {eng === null ? "…" : eng === "missing" ? "not loaded" : eng.confidence?.level}
            </b>
            <em>See why</em>
          </button>
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
                    {focusItem.confidence_level
                      ? <><span className={`n lv l-${focusItem.confidence_level}`}>{focusItem.confidence_level}</span><span className="nl">confidence</span></>
                      : <><span className="n">{pct(focusItem.confidence)}%</span><span className="nl">{kn ? "ವಿಶ್ವಾಸ" : "confident"}</span></>}
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

                  {focusItem.confidence_reasons?.length > 0 && (
                    <div className="px-saw">
                      <h4>Why this confidence</h4>
                      <ul>{focusItem.confidence_reasons.map((t, i) => <li key={i}>{t}</li>)}</ul>
                    </div>
                  )}

                  {(focusItem.events || []).map((e) => (
                    <div className="px-evin" key={e.key}>
                      <h4>{e.name} <span>{e.when}</span></h4>
                      {e.effect ? (
                        <p>
                          In {e.effect.years} past years, {cap(focusItem.crime_type).toLowerCase()} cases in {e.measured_in} were <b>{Math.abs(e.effect.percent)}% {e.effect.direction}</b> during the event
                          ({num(e.effect.seen)} against {num(e.effect.expected >= 20 ? Math.round(e.effect.expected) : e.effect.expected)} expected).
                          {e.effect.clear ? "" : " That is within ordinary week-to-week variation, so the range is not moved."}
                        </p>
                      ) : <p>Too few past cases of this type are on record to measure what the event does to it here.</p>}
                      {e.overall && <p className="dim">All registered cases in this window: {Math.abs(e.overall.percent)}% {e.overall.direction} than the weeks around it.</p>}
                      {focusItem.scenario && focusItem.scenario.event === e.name && (
                        <p className="scn">Baseline <b>{rangeOf(focusItem)}</b>. With the event <b>{num(focusItem.scenario.lo)} to {num(focusItem.scenario.hi)} cases</b> <i>inferred from {focusItem.scenario.years} past years</i></p>
                      )}
                    </div>
                  ))}

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
                  {stations && stations.zone === focusItem.zone && (
                    <div className="px-stn">
                      <div className="px-stn-hd">Stations to watch in {stations.scope || focusItem.zone}<i>inferred</i></div>
                      <ol>
                        {stations.items.map((it) => (
                          <li key={it.unit || it.name}>
                            <b>{it.name}</b>
                            <span>{it.summary}</span>
                            {it.unit && it.history !== "thin" && (
                              <button type="button" className="px-linkbtn px-why" aria-expanded={whyUnit === it.unit}
                                      onClick={() => setWhyUnit(whyUnit === it.unit ? null : it.unit)}>
                                {whyUnit === it.unit ? "Hide the reasons" : "Why this forecast"}
                              </button>
                            )}
                            {it.unit && (
                              <button type="button" className="px-linkbtn px-why" onClick={() => setPlanFor(it.unit)}>Shift plan</button>
                            )}
                            {whyUnit === it.unit && <ForecastWhy unit={it.unit} />}
                          </li>
                        ))}
                      </ol>
                      <p>From the station forecast for the next 7 days, all crime. <button type="button" className="px-linkbtn" onClick={() => router.push(`/map?zone=${encodeURIComponent(focusItem.zone)}`)}>Open on the map</button></p>
                    </div>
                  )}
                  {focusItem.suggestion && (
                    <div className="px-suggest">
                      <div className="px-suggest-hd">{kn ? "ಶಿಫಾರಸು" : "Recommended action"}</div>
                      <div className="px-suggest-txt">{focusItem.suggestion}</div>
                      {focusItem.event_context && <div className="px-suggest-ev">{kn ? "ಘಟನೆ" : "Event"}: {focusItem.event_context}</div>}
                    </div>
                  )}

                  <div className="px-acts">
                    <button className={`px-actbtn cy ${showReasoning ? "on" : ""}`} onClick={() => setShowReasoning((v) => !v)}>
                      {kn ? "ತರ್ಕ" : "How this was worked out"} {showReasoning ? "▾" : "▸"}
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
                    <span className="px-dagttl">{kn ? "ತರ್ಕ ಗ್ರಾಫ್" : "How this was worked out"} · <span className="px-dagzone">{focusItem.zone}</span></span>
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
                              <span className="px-tagent">{stepName(agent)}</span>
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

      {/* Figures for the week */}
      <div className="px-sec">Figures for the week</div>
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
        {eng && eng !== "missing" ? (
          <div className="px-statbox">
            <div className="l">Events ahead</div>
            <div className="v cyan"><Count n={evsAhead.length} /></div>
            <div className="d">Under way or within 3 weeks</div>
          </div>
        ) : (
          <div className="px-statbox">
            <div className="l">{kn ? "ಸರಾಸರಿ ವಿಶ್ವಾಸ" : "Average confidence"}</div>
            <div className="v cyan"><Count n={avgConf} suffix="%" /></div>
            <div className="d">{kn ? "ಮಾದರಿಯ ಖಚಿತತೆ" : "How sure the model is"}</div>
          </div>
        )}
      </div>

      {/* How far to trust it: one line until it is opened */}
      <EngineConfidence eng={eng} open={engOpen} onToggle={() => setEngOpen((v) => !v)} anchor={confRef} />

      {/* What the forecast is built on: the records, their history, the calendar */}
      <div className="px-sec">What the forecast is built on</div>
      <div className="px-built">
        <KnownData eng={eng} />
        {/* 2 · Cases recorded per month */}
        <div className="pxd-card">
          <div className="pxd-hd pxd-hd2">
            <div>
              <span className="pxd-ttl">{kn ? "ತಿಂಗಳಿಗೆ ದಾಖಲಾದ ಪ್ರಕರಣಗಳು" : "Cases recorded per month"}</span>
              <span className="pxd-note">{kn ? "ಪ್ರತಿ ತಿಂಗಳು ದಾಖಲಾದ FIR ಗಳು" : "FIRs registered each month. This is the history the forecast is measured against."}</span>
            </div>
          </div>
          {dash && dash !== "offline"
            ? <VolumeTrend volume={dash.volume} kn={kn} />
            : <div className="pxd-empty">{kn ? "ಬ್ಯಾಕೆಂಡ್ ಆಫ್‌ಲೈನ್" : "The server is not answering."}</div>}
        </div>

        <InternetData eng={eng} onEvents={toEvents} />
      </div>

      {/* Events ahead: when each falls, and what the real register shows it did before */}
      {eng && eng !== "missing" && (
        <section className="px-evs" ref={eventsRef} aria-label="Events ahead">
          <div className="px-evs-hd">
            <h2>Events ahead</h2>
            <span>Dates from the event calendar. What each one does is measured from past FIRs, not assumed.</span>
          </div>
          {evsAhead.length === 0 && <p className="px-evs-none">No listed event falls in the next 3 weeks.</p>}
          {evsAhead.map((e) => (
            <EventCard key={e.key} ev={e} areas={P.filter((x) => (e.places || []).includes(x.zone)).slice(0, 4)} onOpen={openItem} />
          ))}
        </section>
      )}

      {/* 4 · Hypotheses: links the record suggests, and the case against each */}
      <section className="px-hyp" aria-label="Hypotheses">
        <header>
          <div>
            <h3>{kn ? "ಊಹೆಗಳು" : "Hypotheses"}{fZone ? ` · ${fZone}` : ""}</h3>
            <p>Possible links between accused in this district, proposed from what they share in the record. Each one is then tested: how many other pairs in the state would look just as linked by chance?</p>
          </div>
          <button type="button" onClick={runHypotheses} disabled={!fZone || runningHypotheses}>
            {runningHypotheses ? "Checking…" : hypothesesList ? "Run again" : "Look for links"}
          </button>
        </header>

        {!fZone && <p className="px-hyp-empty">Select a district in the forecast list to look for links there.</p>}
        {fZone && !hypothesesList && !runningHypotheses && (
          <p className="px-hyp-empty">Nothing has been run for {fZone} yet.</p>
        )}
        {runningHypotheses && <p className="px-hyp-empty">Comparing accused in {fZone} and checking each link against its base rate…</p>}
        {hypothesesList?.error && !runningHypotheses && (
          <p className="px-hyp-empty">{hypothesesList.error === "restart"
            ? "This needs the server restarted to load it."
            : "The links could not be read just now. Try again."}</p>
        )}
        {hypothesesList && !hypothesesList.error && !runningHypotheses && hypothesesList.hypotheses.length === 0 && (
          <p className="px-hyp-empty">No link between accused in {hypothesesList.zone} scores high enough to propose. That is a result, not a failure.</p>
        )}

        {hypothesesList && !hypothesesList.error && !runningHypotheses && hypothesesList.hypotheses.length > 0 && (() => {
          const list = hypothesesList.hypotheses;
          const stands = list.filter((h) => h.verdict === "SURVIVES").length;
          const WORD = { SURVIVES: "Stands up", WEAKENED: "Weakened", COLLAPSES: "Does not stand up", UNASSESSABLE: "Could not be checked" };
          const pct = (p) => (p == null ? null : p < 0.01 ? "under 1%" : p > 0.99 ? "over 99%" : `${Math.round(p * 100)}%`);
          return (
            <>
              <p className="px-hyp-sum">
                {list.length} {list.length === 1 ? "link" : "links"} proposed{hypothesesList.examined > list.length ? ` (the strongest of ${hypothesesList.examined})` : ""}.{" "}
                {stands === 0 ? "None stands up to the base-rate check." : `${stands} ${stands === 1 ? "stands" : "stand"} up to the base-rate check.`}
              </p>
              <ul className="px-hyp-list">
                {list.map((h) => (
                  <li key={h.id} className={`v-${String(h.verdict || "").toLowerCase()}`}>
                    <div className="top">
                      <b>{(h.subject_ids || []).join(" and ") || h.id}</b>
                      <span className="verdict"><i aria-hidden="true" />{WORD[h.verdict] || h.verdict}</span>
                    </div>
                    <p className="claim">{h.claim}</p>
                    <dl>
                      <div>
                        <dt>What they share</dt>
                        <dd>{(h.signals || []).map((sg) => sg.name).join("; ") || "Not recorded"}</dd>
                      </div>
                      <div>
                        <dt>The check</dt>
                        <dd>{h.verdict_reason}
                          {h.posterior_probability != null && <small>Chance the link is real after the check: {pct(h.posterior_probability)}.</small>}
                        </dd>
                      </div>
                      {(h.falsification_tests || []).length > 0 && (
                        <div>
                          <dt>What would settle it</dt>
                          <dd>
                            <ol>{h.falsification_tests.slice(0, 3).map((t, i) => (
                              <li key={i}>{typeof t === "string" ? t : t.test}{t?.would_disprove && <small>{t.would_disprove}</small>}</li>
                            ))}</ol>
                          </dd>
                        </div>
                      )}
                    </dl>
                  </li>
                ))}
              </ul>
              <p className="px-hyp-foot">A proposed link is an inference, never a finding. Scored from shared signals in the record, then checked with counted base rates; no language model is involved in either step.</p>
            </>
          );
        })()}
      </section>

      {planFor && <ShiftPlan station={planFor} kn={kn} onClose={() => setPlanFor(null)} />}

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


