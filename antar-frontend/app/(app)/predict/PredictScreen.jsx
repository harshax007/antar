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
import { AnimatePresence, AnimatePresence as PlanPresence, motion } from "framer-motion";
import { MaterialBackdrop, MaterialPanel, SPRING } from "@/components/ui/MaterialPanel";
import EngineOverall from "@/components/EngineOverall";
import CaseLeads from "@/components/CaseLeads";

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
// What the anomaly scan calls each alert, in words an officer uses.
const ALERT_KIND = {
  spike: "Sudden rise",
  seasonal_surge: "Seasonal rise",
  hotspot: "Hotspot",
  spatial_spike: "Sudden rise in a hotspot",
};
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

// The register's heads that are a law's name or a legal term, said in plain words: what
// cases are filed under it. Shown beside the name wherever it appears, so a reader who has
// never seen "Karnataka Police Act 1963" knows it is mostly gambling and public nuisance.
const CRIME_PLAIN = [
  [/KARNATAKA POLICE ACT/, "Public-order cases: mostly gambling (cards, matka), public nuisance and drunken disorder"],
  [/KARNATAKA STATE LOCAL ACT/, "Cases under Karnataka's local laws, such as excise and liquor sale"],
  [/COTPA|CIGARETTES/, "Tobacco law: smoking in public places, sale near schools or to minors"],
  [/NDPS|NARCOTIC/, "Drugs: possession, sale or use of narcotics"],
  [/POCSO/, "Sexual offences against children"],
  [/^CRPC$|CRIMINAL PROCEDURE/, "Preventive cases filed by the police to stop a breach of peace"],
  [/MOTOR VEHICLES ACT/, "Traffic law cases, such as driving without a licence"],
  [/MOTOR VEHICLE ACCIDENTS NON-FATAL/, "Road accidents where people were hurt"],
  [/MOTOR VEHICLE ACCIDENTS FATAL/, "Road accidents where someone died"],
  [/NEGLIGENT ACT/, "Careless acts that endangered or harmed someone"],
  [/CASES OF HURT/, "Assault that caused injury"],
  [/CRIMINAL INTIMIDATION/, "Threatening a person"],
  [/CRIMINAL TRESPASS/, "Entering property unlawfully"],
  [/MISCHIEF/, "Damaging someone's property"],
  [/AFFRAY/, "A public fight that disturbs the peace"],
  [/RIOTS/, "Violence by a group of five or more"],
  [/DACOITY/, "Robbery by a gang of five or more"],
  [/MOLESTATION/, "Sexual harassment or assault on a woman"],
  [/CRIMES RELATED TO WOMEN|ASSAULT ON WOMEN/, "Offences against women, such as harassment and cruelty"],
  [/PUBLIC SAFETY/, "Acts that put the public at risk, such as rash conduct in public places"],
  [/ARMS ACT/, "Carrying or keeping weapons without a licence"],
  [/EXCISE/, "Illegal liquor: making, carrying or selling it"],
  [/IT ACT|CYBER/, "Online crime: fraud, hacking or misuse of a phone or computer"],
  [/\bSC\b.?\bST\b|ATROCIT/,"Offences against Scheduled Castes and Scheduled Tribes"],
  [/DOWRY/, "Demanding or giving dowry"],
  [/OFFENCES PROMOTING ENEMITY/, "Spreading hatred between groups"],
];
const plainCrime = (name) => {
  const k = String(name || "").replace(/_/g, " ").trim().toUpperCase();
  const hit = CRIME_PLAIN.find(([re]) => re.test(k));
  return hit ? hit[1] : null;
};
// A crime name with its plain meaning on hover (a dotted underline says there is one).
function CrimeName({ name, className }) {
  const plain = plainCrime(name);
  return plain
    ? <span className={`px-term${className ? ` ${className}` : ""}`} title={plain}>{cap(name)}</span>
    : <span className={className}>{cap(name)}</span>;
}
const RISK_WORD = { HIGH: "High risk", MEDIUM: "Medium risk", LOW: "Low risk" };
// Statewide police units register FIRs under their own name, so they arrive in the board
// beside the districts. They are not areas: no beat goes to "CID". The server tags them
// (`unit`); the names are the fallback for a board cached before it did.
const UNIT_NAMES = { "CID": "Criminal Investigation Department", "Coastal Security Police": "Coastal Security Police",
  "Karnataka Railways": "Railway Police", "ISD Bengaluru": "Internal Security Division" };
const isUnit = (p) => !!(p?.unit || UNIT_NAMES[p?.zone]);
// What the card says about an area. "Low risk" beside "far above normal" read as a
// contradiction (few cases, but many more than usual), so the card leads with what to do.
function statusOf(p) {
  if (p?.risk === "HIGH") return { k: "hi", t: "High risk" };
  if (p?.direction === "silence") return { k: "dn", t: "Check reports" };
  const z = Number(p?.z_score) || 0;
  if (z >= 2) return { k: "up", t: "Above normal" };
  if ((p?.events || []).length) return { k: "ev", t: "Event" };
  return { k: "eq", t: "Usual" };
}
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
    if (/^MAD-z/i.test(t)) out.push(`Recent cases are ${levelOf(item).toLowerCase()} for this area (unusual-activity score ${item.z_score}; 2 is unusual, 4 is rare).`);
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
  const why = [ALERT_KIND[a.anomaly_type] || a.anomaly_type?.replace(/_/g, " "), a.trace?.[0]?.description].filter(Boolean).join(" - ");
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
            <div><dt>Real register</dt><dd>through <b>{dayOf(r.real_record_ends)}</b></dd></div>
          )}
          {t ? (
            <>
              <div><dt>Track record</dt><dd><b>{(t.coverage80 * 100).toFixed(1)}%</b> of weeks fell inside the likely range<span>{t.weeks} weeks of the real register, {monthOf(t.from)} to {monthOf(t.to)}; station forecasts</span></dd></div>
              <div><dt>Wider range</dt><dd><b>{(t.coverage90 * 100).toFixed(1)}%</b> of weeks inside it</dd></div>
              <div><dt>Total forecast</dt><dd><b>{num(Math.round(t.forecast_total))}</b> against <b>{num(t.actual_total)}</b> recorded<span>over the weeks tested</span></dd></div>
              <div><dt>Against a simple guess</dt><dd><b>{t.weeks_better} of {t.weeks_ranked}</b> weeks better<span>than ranking stations by their last 4 weeks</span></dd></div>
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
        <span className="pxd-ttl">Festival calendar <i>from the internet</i></span>
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

// An event ahead, for bandobast: when it falls, what past years say to brief on, and the
// measured detail on request. Everything is counted from FIRs in the event's own window
// against the four weeks either side; nothing here is a guess about this year.
function EventCard({ ev, kn, areas, onOpen, onAsk }) {
  const o = ev.overall, n = ev.occurrences_measured || 0;
  const [copied, setCopied] = useState(false);
  const day = (d) => { const t = new Date(); t.setDate(t.getDate() + d); return t.toLocaleDateString("en-IN", { day: "numeric", month: "short" }); };
  const starts = ev.starts_in_days, ends = ev.ends_in_days;
  const now = ev.phase === "under way";
  const dates = starts == null ? null : now ? (kn ? `ಈಗ ನಡೆಯುತ್ತಿದೆ, ${day(Math.max(0, ends ?? 0))} ವರೆಗೆ` : `On now, until ${day(Math.max(0, ends ?? 0))}`)
    : `${day(starts)}${ends != null && ends !== starts ? (kn ? ` ರಿಂದ ${day(ends)}` : ` to ${day(ends)}`) : ""}`;
  const brief = [...(ev.rises || []).map((x) => ({ ...x, sure: true })), ...(ev.watch || []).map((x) => ({ ...x, sure: false }))];
  const quieter = (ev.falls || []).slice(0, 3);
  const times = (x) => (x.ratio >= 1.5 ? (kn ? `ಸಾಮಾನ್ಯದ ${x.ratio.toFixed(1)}×` : `${x.ratio.toFixed(1)}× usual`)
                                         : (kn ? `${Math.abs(x.percent)}% ಹೆಚ್ಚು` : `${Math.abs(x.percent)}% more`));
  const where = ev.statewide ? (kn ? "ರಾಜ್ಯಾದ್ಯಂತ" : "Statewide") : (ev.places || []).join(", ") || ev.measured_in;
  const overallLine = !o ? (kn ? "ಅಳೆಯಲು ಸಾಕಷ್ಟು ಹಿಂದಿನ ವರ್ಷಗಳಿಲ್ಲ." : "Too few past years on record to measure this event.")
    : o.clear ? (kn ? `ಇದು ನಡೆಯುವಾಗ ಒಟ್ಟು ${Math.abs(o.percent)}% ${o.percent < 0 ? "ಕಡಿಮೆ" : "ಹೆಚ್ಚು"} ಪ್ರಕರಣಗಳು ದಾಖಲಾಗುತ್ತವೆ.`
                    : `${Math.abs(o.percent)}% ${o.percent < 0 ? "fewer" : "more"} cases registered overall while it is on.`)
    : (kn ? "ಒಟ್ಟು ದಾಖಲಾದ ಪ್ರಕರಣಗಳು ಇದರೊಂದಿಗೆ ಸ್ಪಷ್ಟವಾಗಿ ಬದಲಾಗುವುದಿಲ್ಲ." : "Registered cases overall do not move clearly with it.");
  const note = () => [
    `${ev.name} (${where}), ${dates || ev.when}.`,
    brief.length ? `Brief on: ${brief.map((x) => `${cap(x.crime)} (${times(x)}, higher in ${x.years_higher} of ${x.years} years)`).join("; ")}.` : null,
    o ? `Overall: ${overallLine}` : null,
    `Measured from FIRs ${o ? `${o.from_year} to ${o.to_year}` : ""}, the event window against the 4 weeks either side.`,
  ].filter(Boolean).join("\n");
  const copy = async () => { try { await navigator.clipboard.writeText(note()); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* no clipboard */ } };
  return (
    <article className={`px-ev${now ? " now" : ""}`}>
      <header>
        <div className="px-ev-count" aria-hidden="true">
          {now ? <b>{kn ? "ಈಗ" : "Now"}</b> : <><b>{starts}</b><span>{kn ? "ದಿನ" : starts === 1 ? "day" : "days"}</span></>}
        </div>
        <div className="px-ev-ttl">
          <h4>{ev.name}</h4>
          <p>{ev.what}</p>
          <div className="px-ev-meta">
            {dates && <span>{dates}</span>}
            {ev.window_days ? <span>{ev.window_days} {kn ? "ದಿನ" : ev.window_days === 1 ? "day" : "days"}</span> : null}
            <span>{where}</span>
            {ev.in_forecast_window && <span className="in">{kn ? "ಈ ವಾರದ ಮುನ್ಸೂಚನೆಯಲ್ಲಿ" : "In this week's forecast"}</span>}
          </div>
        </div>
      </header>

      <div className="px-ev-grid">
        <div className="px-ev-col">
          <h5>{kn ? "ಬ್ರೀಫ್ ಮಾಡಬೇಕಾದದ್ದು" : "Brief the force on"}</h5>
          {brief.length ? (
            <ul className="px-ev-up">
              {brief.map((x) => (
                <li key={x.crime} className={x.sure ? "" : "soft"}>
                  <b>{cap(x.crime)}</b>
                  {plainCrime(x.crime) && <small>{plainCrime(x.crime)}</small>}
                  <span>{times(x)} · {kn ? `${x.years} ರಲ್ಲಿ ${x.years_higher} ವರ್ಷ ಹೆಚ್ಚು` : `higher in ${x.years_higher} of ${x.years} years`}{x.sure ? "" : (kn ? " · ಕಡಿಮೆ ಖಚಿತ" : " · less certain")}</span>
                </li>
              ))}
            </ul>
          ) : <p className="px-ev-none">{kn ? "ಯಾವುದೇ ಅಪರಾಧ ಸ್ಪಷ್ಟವಾಗಿ ಏರುವುದಿಲ್ಲ." : "No crime type rises clearly during it in past years."}</p>}
        </div>
        <div className="px-ev-col">
          <h5>{kn ? "ಒಟ್ಟಾರೆ" : "Overall"}</h5>
          <p className="px-ev-all">{overallLine}{o ? <em> {kn ? `ನಿರೀಕ್ಷಿತ ${num(Math.round(o.expected))} ಕ್ಕೆ ಎದುರಾಗಿ ${num(o.seen)} ಪ್ರಕರಣಗಳು, ${o.years} ವರ್ಷಗಳು.` : `${num(o.seen)} cases against ${num(Math.round(o.expected))} expected, ${o.years} years.`}</em> : null}</p>
          {quieter.length > 0 && (
            <p className="px-ev-dn">{kn ? "ಸಾಮಾನ್ಯವಾಗಿ ಕಡಿಮೆ: " : "Usually fewer registered: "}{quieter.map((x) => cap(x.crime)).join(", ")}.
              <em> {kn ? "" : "Fewer FIRs can mean slower reporting during an event, not less crime."}</em></p>
          )}
        </div>
      </div>

      {n >= 4 && (
        <details className="px-ev-more">
          <summary>{kn ? "ವರ್ಷವಾರು ಅಳತೆ" : `How it was measured: ${n} past years in ${ev.measured_in}${o ? `, ${o.from_year} to ${o.to_year}` : ""}`}</summary>
          <EffectRow label="All registered cases" ef={o} />
          {(ev.rises || []).map((x) => <EffectRow key={x.crime} label={cap(x.crime)} ef={x} />)}
          {(ev.watch || []).map((x) => <EffectRow key={x.crime} label={cap(x.crime)} ef={x} soft />)}
          {(ev.falls || []).slice(0, 3).map((x) => <EffectRow key={x.crime} label={cap(x.crime)} ef={x} />)}
          <p className="px-ev-src">Date from the {ev.date_source === "internet" ? "internet calendar" : ev.date_source === "fixed date" ? "fixed annual date" : "built-in calendar"}. Effect: FIRs in the event window against the 4 weeks either side, each past year.</p>
        </details>
      )}

      <footer>
        <button type="button" className="ui-btn ui-btn--secondary ui-btn--sm" onClick={copy}>{copied ? "Copied" : (kn ? "ಬಂದೋಬಸ್ತ್ ಟಿಪ್ಪಣಿ ನಕಲಿಸಿ" : "Copy a bandobast note")}</button>
        <button type="button" className="ui-btn ui-btn--ghost ui-btn--sm" onClick={() => onAsk(`What did ${ev.name} do to crime in ${ev.measured_in} in past years?`)}>{kn ? "ಅಂತರ್‌ಗೆ ಕೇಳಿ" : "Ask Antar about past years"}</button>
        {areas.map((a) => <button type="button" className="ui-btn ui-btn--ghost ui-btn--sm" key={a.zone} onClick={() => onOpen(a)}>{kn ? "ತೆರೆಯಿರಿ" : "Open"} {a.zone}</button>)}
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
                {dPct == null ? cur.label : `${dPct > 0 ? "+" : dPct < 0 ? "-" : ""}${Math.abs(dPct)}%`}
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
.px-page { background: #070B14; color: #EEF3FA; font-family: 'Inter', sans-serif; }

/* Typography */
/* The title glowed at 0.4 alpha, which on a screen of severity colours made the page
   furniture the brightest thing on it. */
.px-title { color: #EEF3FA; font-family: 'Chakra Petch', sans-serif; font-size: 28px; font-weight: 700; letter-spacing: 0.02em; margin-bottom: 4px; }
.px-sub { font-size: 13px; color: #B4C2D6; font-weight: 500; font-family: 'JetBrains Mono', monospace; /* text-transform: uppercase; */ letter-spacing: 0.05em; }

/* Buttons */
.px-howbtn { background: rgba(34,230,240,0.1); border: 1px solid rgba(34,230,240,0.3); color: #22E6F0; border-radius: 8px; font-weight: 600; font-size: 12px; padding: 6px 12px; transition: color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.px-howbtn:hover { background: rgba(34,230,240,0.2); box-shadow: 0 0 10px rgba(34,230,240,0.2); }

/* Grid Layouts */
.px-dash { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; padding-bottom: 24px; }

/* Top KPI Strip */
.px-statrow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-top: 16px; margin-bottom: 32px; }
.px-statbox { position: relative; display: flex; flex-direction: column; background: linear-gradient(180deg, rgba(10,10,10,0.8) 0%, rgba(0,0,0,0.9) 100%); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); overflow: hidden; }
.px-statbox::before { content: ""; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: rgba(255,255,255,0.08); }
.px-statbox:hover { border-color: #22E6F0; }
.px-statbox:hover::before { background: #22E6F0; box-shadow: 0 0 8px #22E6F0; }
.px-statbox .l { font-size: 11px; font-weight: 700; color: #B4C2D6; /* text-transform: uppercase; */ letter-spacing: 0.1em; margin-bottom: 12px; font-family: 'JetBrains Mono', monospace; }
.px-statbox .v { font-size: 38px; font-weight: 800; color: #EEF3FA; font-family: 'Chakra Petch', sans-serif; line-height: 1; }
.px-statbox .v.cyan { color: #22E6F0; }
.px-statbox .v.red { color: #E14038; }

/* Columns */
.pxd-card { display: flex; flex-direction: column; min-height: 440px; max-height: 480px; border-radius: 12px; background: #070B14; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 12px 32px rgba(0,0,0,0.4); padding: 20px; }
.pxd-hd { margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
.pxd-ttl { font-family: 'Chakra Petch', sans-serif; font-size: 16px; font-weight: 700; color: #EEF3FA; letter-spacing: 0.05em; /* text-transform: uppercase; */ }

/* Scroll Area */
.pxd-scroll { flex: 1; overflow-y: auto; padding-right: 8px; }
.pxd-scroll::-webkit-scrollbar { width: 6px; }
.pxd-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 4px; }
.pxd-scroll::-webkit-scrollbar-track { background: transparent; }

/* Cards inside columns */
.px-card { display: flex; flex-direction: column; background: #070B14; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 16px; margin-bottom: 12px; cursor: pointer; transition: color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s; position: relative; }
.px-card:hover { border-color: rgba(255,255,255,0.08); background: #070B14; }
.px-card.on { background: rgba(34,230,240,0.08); border-color: #22E6F0; box-shadow: 0 0 15px rgba(34,230,240,0.15); }
.px-card-bar { position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: #22E6F0; border-radius: 4px 0 0 4px; }

.px-card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.px-zone { font-size: 16px; font-weight: 700; color: #EEF3FA; letter-spacing: 0.02em; }

/* Risk Tags */
.px-risk { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 800; padding: 4px 8px; border-radius: 4px; /* text-transform: uppercase; */ letter-spacing: 0.1em; }
.px-risk-h { color: #E14038; background: rgba(225,64,56,0.15); border: 1px solid rgba(225,64,56,0.3); }
/* Severity runs red -> amber -> slate here, the same as the brain's finding cards.
   The bulk palette swap turned MEDIUM cyan, which is this product's accent for things
   you can act on, not a severity. */
.px-risk-m { color: #FFB020; background: rgba(255,176,32,0.15); border: 1px solid rgba(255,176,32,0.3); }
.px-risk-l { color: #8A99AD; background: rgba(138,153,173,0.12); border: 1px solid rgba(138,153,173,0.26); }

/* Data Rows */
.px-crime-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.px-crime { font-size: 13px; color: #B4C2D6; font-weight: 600; /* text-transform: uppercase; */ letter-spacing: 0.03em; }
.px-know { font-size: 11px; font-weight: 600; padding: 6px 12px; background: rgba(24,214,154,0.1); border: 1px solid rgba(24,214,154,0.4); border-radius: 8px; color: #18D69A; transition: color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s; white-space: nowrap; cursor: pointer; }
.px-know:hover { background: rgba(24,214,154,0.2); box-shadow: 0 0 8px rgba(24,214,154,0.3); }

.px-confpct { color: #22E6F0; font-weight: 700; font-size: 13px; font-family: 'JetBrains Mono', monospace; }
.px-meta { margin-top: 12px; font-size: 11px; color: #B4C2D6; display: flex; gap: 8px; flex-wrap: wrap; }
.px-tag { font-size: 11px; padding: 4px 8px; border-radius: 4px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.08); color: #EEF3FA; font-family: 'JetBrains Mono', monospace; }
.px-tag.ok { color: #22E6F0; border-color: rgba(34,230,240,0.4); background: rgba(34,230,240,0.1); }

/* Explanation Panel */
.px-explain { background: #070B14; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; box-shadow: 0 20px 50px rgba(0,0,0,0.6); overflow: hidden; margin-top: 24px; }
.px-panel-hd { background: #070B14; padding: 16px 24px; border-bottom: 1px solid rgba(255,255,255,0.08); display: flex; justify-content: space-between; align-items: center; font-size: 14px; font-weight: 700; color: #EEF3FA; font-family: 'Chakra Petch', sans-serif; /* text-transform: uppercase; */ letter-spacing: 0.05em; }
.px-hint { font-size: 12px; font-weight: 500; color: #B4C2D6; font-family: 'JetBrains Mono', monospace; }
.px-insp { padding: 32px; }
.px-insp-title { font-family: 'Chakra Petch', sans-serif; font-size: 28px; font-weight: 700; color: #EEF3FA; margin-bottom: 16px; letter-spacing: 0.02em; }

/* AI Explanation Box */
.px-insp-why { background: rgba(34,230,240,0.05); padding: 20px 24px; border-radius: 8px; border-left: 4px solid #22E6F0; color: #EEF3FA; font-size: 16px; line-height: 1.6; margin-bottom: 28px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); font-weight: 500; }

/* Stats in explanation */
.px-big .n { font-size: 48px; font-weight: 800; color: #EEF3FA; font-family: 'Chakra Petch', sans-serif; }
.px-big .z { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: #E14038; background: rgba(225,64,56,0.1); border: 1px solid rgba(225,64,56,0.3); padding: 6px 12px; border-radius: 8px; margin-left: 16px; vertical-align: super; }

/* Band box */
.px-bandbox { font-family: 'JetBrains Mono', monospace; font-size: 13px; background: #070B14; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 16px 20px; margin-bottom: 28px; color: #B4C2D6; }
.px-bandbox b { color: #22E6F0; font-size: 16px; font-weight: 700; margin-right: 8px; }

/* Grid tiles */
.px-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }
.px-tile { background: #070B14; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 20px; transition: color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s; }
.px-tile:hover { border-color: #22E6F0; box-shadow: 0 4px 12px rgba(34,230,240,0.1); }
.px-tile .tv { font-family: 'Chakra Petch', sans-serif; font-size: 24px; font-weight: 700; color: #EEF3FA; margin-bottom: 6px; }
.px-tile .tl { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; color: #B4C2D6; /* text-transform: uppercase; */ letter-spacing: 0.05em; }

/* Actions */
.px-acts { display: flex; flex-wrap: wrap; gap: 12px; }
.px-actbtn { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600; padding: 12px 20px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.08); color: #EEF3FA; transition: color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s; display: inline-flex; align-items: center; justify-content: center; min-width: 140px; }
.px-actbtn:hover { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.08); color: #fff; }
.px-actbtn.cy { background: rgba(24,214,154,0.1); border-color: rgba(24,214,154,0.4); color: #18D69A; }
.px-actbtn.cy:hover { background: rgba(24,214,154,0.2); box-shadow: 0 0 12px rgba(24,214,154,0.2); }

/* Suggestion */
.px-suggest { background: linear-gradient(135deg, rgba(34,230,240,0.05) 0%, rgba(24,214,154,0.05) 100%); border: 1px solid rgba(34,230,240,0.2); border-radius: 12px; padding: 24px; margin-bottom: 32px; border-left: 4px solid #22E6F0; }
.px-suggest-hd { font-family: "JetBrains Mono", monospace; font-size: 12px; font-weight: 700; color: #22E6F0; letter-spacing: 0.1em; /* text-transform: uppercase; */ margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.px-suggest-txt { font-size: 16px; color: #EEF3FA; line-height: 1.6; font-weight: 500; }

.px-prov-hd { font-size: 12px; font-weight: 600; color: #B4C2D6; margin-bottom: 8px; /* text-transform: uppercase; */ letter-spacing: 0.05em; }
.px-prov-ids { font-family: "JetBrains Mono", monospace; font-size: 11px; color: #B4C2D6; background: #070B14; padding: 12px; border-radius: 8px; border: 1px dashed rgba(255,255,255,0.08); }

/* ── Plain-language pass: sentence case, a reading face, calmer type ── */
.px-sub { font-family: 'Inter', sans-serif; font-size: 14px; color: #B4C2D6; letter-spacing: 0; }
/* One shape for every provenance fact in the header: assessed date, area count,
   and whether the week is seeded. */
.px-chip { font-family: 'Inter', sans-serif; font-size: 12px; color: #B4C2D6;
  border: 1px solid rgba(255,255,255,0.08); border-radius: 999px; padding: 4px 12px;
  background: rgba(255,255,255,0.03); white-space: nowrap; }
.px-chip b { color: #EEF3FA; font-weight: 600; }
/* Amber, because it qualifies every number on the page - but a chip, not a billboard. */
.px-chip.is-seed { color: #FFB020; border-color: rgba(255,176,32,0.32); background: rgba(255,176,32,0.07); cursor: help; }
.px-panel-hd, .px-suggest-hd, .pxd-stats i, .px-crime, .px-know { text-transform: none; letter-spacing: 0; }

.px-brief { display: flex; gap: 24px; align-items: center; margin-top: 16px; padding: 20px 24px; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; background: linear-gradient(100deg, rgba(34,230,240,0.06), rgba(7,11,20,0.9) 42%); }
.px-brief-body { flex: 1; min-width: 0; }
.px-brief-body h2 { font-family: 'Chakra Petch', sans-serif; font-size: 16px; font-weight: 700; color: #EEF3FA; margin: 0 0 8px; }
.px-brief-body ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.px-brief-body li { position: relative; padding-left: 20px; font-size: 14px; line-height: 1.55; color: #EEF3FA; opacity: 0; animation: pxRise .4s ease forwards; }
.px-brief-body li::before { content: ""; position: absolute; left: 2px; top: .62em; width: 7px; height: 7px; border-radius: 50%; background: #39455A; }
.px-brief-body li.k-hi::before { background: #E14038; } .px-brief-body li.k-up::before { background: #FFB020; }
.px-brief-body li.k-dn::before { background: #22E6F0; } .px-brief-body li.k-ok::before { background: #18D69A; }
.px-brief-body li.go { cursor: pointer; } .px-brief-body li.go:hover { color: #fff; }
.px-brief-body li em { font-style: normal; font-size: 12px; color: #22E6F0; margin-left: 8px; white-space: nowrap; }
.px-brief-body li.go:focus-visible { outline: 2px solid #22E6F0; outline-offset: 2px; border-radius: 4px; }
.px-brief-wait { font-size: 14px; color: #B4C2D6; margin: 0; }
.px-brief-ai { margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.08); animation: pxRise .4s ease both; }
.px-brief-ai span { font-size: 12px; font-weight: 600; color: #22E6F0; }
.px-brief-ai p { margin: 4px 0 0; font-size: 14px; line-height: 1.6; color: #EEF3FA; }

.px-statrow { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; }
.px-statbox { padding: 16px 20px 16px 24px; animation: pxRise .45s ease both; }
.px-statbox:nth-child(2) { animation-delay: 60ms; } .px-statbox:nth-child(3) { animation-delay: 120ms; }
.px-statbox:nth-child(4) { animation-delay: 180ms; } .px-statbox:nth-child(5) { animation-delay: 240ms; }
.px-statbox .l { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600; color: #B4C2D6; letter-spacing: 0; margin-bottom: 8px; }
.px-statbox .v { font-size: 34px; font-variant-numeric: tabular-nums; }
.px-statbox .d { margin-top: 8px; font-size: 12px; color: #8A99AD; }

.pxd-hd2 { justify-content: flex-start; align-items: center; gap: 12px; }
.pxd-hd2 > div { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.pxd-ttl { letter-spacing: 0; }
.pxd-ttl i { font-style: normal; font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600; color: #B4C2D6; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 1px 8px; margin-left: 6px; vertical-align: 1px; }
.pxd-note { font-size: 12px; line-height: 1.45; color: #B4C2D6; }
.pxd-sub, .pxd-granhint { font-family: 'Inter', sans-serif; font-size: 12px; }
.pxd-xlabels { font-family: 'Inter', sans-serif; font-size: 11px; }
.pxd-selline { font-size: 13px; color: #EEF3FA; }
.pxd-plot { margin-top: 24px; }
.pxd-stats i { font-family: 'Inter', sans-serif; font-size: 11px; }
.pxd-liner { stroke-dasharray: 1; stroke-dashoffset: 1; animation: pxDrawLine 1.1s ease-out forwards; }

.px-card { animation: pxRise .35s ease both; }
.px-card-top { gap: 12px; }
.px-zone { min-width: 0; }
.px-risk { font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0; white-space: nowrap; }
.px-crime { font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 500; color: #B4C2D6; }
.px-know { width: auto; animation: none; font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600; padding: 4px 12px; }
.px-say { display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: baseline; margin-bottom: 12px; font-size: 13px; color: #B4C2D6; }
.px-say b { font-weight: 600; color: #EEF3FA; } .px-say b.up { color: #FFB020; } .px-say b.dn { color: #22E6F0; }
.px-conffill { transform-origin: left; animation: pxGrow .7s ease-out both; }
.px-confpct { font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600; white-space: nowrap; }
.px-tag { font-family: 'Inter', sans-serif; font-size: 11px; align-self: flex-start; }

.pxd-alert-ttl { font-size: 14px; justify-content: space-between; flex-wrap: nowrap; }
.pxd-alert-ttl > span:first-child { min-width: 0; }
.pxd-alert-sub { font-family: 'Inter', sans-serif; font-size: 12px; color: #B4C2D6; margin-top: 4px; }
.pxd-sev { font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0; padding: 1px 8px; flex: none; border-radius: 4px; }
/* One severity scale across the product: red, amber, slate. Stated here rather than
   inherited from a bare .hi/.md, so the alert badge cannot drift from the risk badge. */
.pxd-sev.hi { color: #E14038; background: rgba(225,64,56,0.13); border: 1px solid rgba(225,64,56,0.28); }
.pxd-sev.md { color: #FFB020; background: rgba(255,176,32,0.12); border: 1px solid rgba(255,176,32,0.26); }
.pxd-sev.lo { color: #8A99AD; background: rgba(138,153,173,0.10); border: 1px solid rgba(138,153,173,0.22); }
.pxd-adot { display: none; }

.px-fade { animation: pxRise .3s ease both; }
.px-big { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-bottom: 20px; }
.px-big .nl { font-size: 14px; color: #B4C2D6; margin-left: -4px; }
.px-big .z { font-family: 'Inter', sans-serif; margin-left: 0; vertical-align: baseline; color: #FFB020; background: rgba(255,176,32,0.08); border-color: rgba(255,176,32,0.3); cursor: help; }
.px-bandbox { font-family: 'Inter', sans-serif; font-size: 14px; }
.px-bandbox span { display: block; margin-top: 4px; font-size: 13px; }
.px-saw { margin-bottom: 24px; }
.px-saw h4 { font-size: 13px; font-weight: 600; color: #B4C2D6; margin: 0 0 8px; }
.px-saw ul { margin: 0; padding-left: 20px; display: grid; gap: 6px; font-size: 14px; line-height: 1.55; color: #EEF3FA; }
.px-tile .tl, .px-prov-hd { font-family: 'Inter', sans-serif; font-size: 12px; letter-spacing: 0; }
.px-tile .tv { font-size: 24px; }
.px-more { padding: 16px 16px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; }
.px-more summary { cursor: pointer; color: #22E6F0; font-size: 13px; font-weight: 600; }
.px-more .px-prov { margin-top: 16px; }
.px-method { margin: 12px 0 0; font-size: 13px; line-height: 1.5; color: #B4C2D6; }
.px-loading { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.px-footer { font-family: 'Inter', sans-serif; font-size: 12px; }

/* ── The engine panel ── */
.px-eng { display: grid; grid-template-columns: 1.15fr 1fr 1fr; margin-top: 16px; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; background: #070B14; animation: pxRise .4s ease both; }
.px-eng.is-wait { display: block; padding: 20px 24px; }
.px-eng.is-wait p { margin: 0; font-size: 14px; line-height: 1.6; color: #B4C2D6; max-width: 78ch; }
.px-eng.is-wait b { color: #EEF3FA; }
.px-eng-col { padding: 20px 24px; min-width: 0; }
.px-eng-col + .px-eng-col { border-left: 1px solid #0A111D; }
.px-eng h3 { margin: 0 0 12px; font: 600 13px 'Inter', sans-serif; color: #B4C2D6; }
.px-eng h3 em { font-style: normal; font-weight: 500; color: #8A99AD; margin-left: 6px; }
.px-eng-level { font: 700 34px/1 'Chakra Petch', sans-serif; color: #EEF3FA; }
.px-eng-level.l-High, .px-lvl.l-High, .px-big .n.l-High { color: #18D69A; }
.px-eng-level.l-Moderate, .px-lvl.l-Medium, .px-big .n.l-Medium { color: #FFB020; }
.px-eng-level.l-Limited, .px-lvl.l-Low, .px-big .n.l-Low { color: #8A99AD; }
.px-eng-meter { display: flex; gap: 4px; margin: 12px 0 8px; max-width: 220px; }
.px-eng-meter i { flex: 1; height: 5px; border-radius: 4px; background: #0A111D; }
.px-eng-meter i.on.l-High { background: #18D69A; } .px-eng-meter i.on.l-Moderate { background: #FFB020; } .px-eng-meter i.on.l-Limited { background: #8A99AD; }
.px-eng-says { margin: 0 0 12px; font-size: 14px; line-height: 1.5; color: #EEF3FA; }
.px-eng-why { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.px-eng-why li { position: relative; padding-left: 20px; font-size: 13px; line-height: 1.5; color: #B4C2D6; }
.px-eng-why li::before { content: ""; position: absolute; left: 2px; top: .55em; width: 7px; height: 7px; border-radius: 50%; }
.px-eng-why li.ok::before { background: #18D69A; } .px-eng-why li.no::before { background: #FFB020; }
.px-eng dl { margin: 0; display: grid; gap: 12px; }
.px-eng dl > div { display: grid; grid-template-columns: 108px 1fr; gap: 12px; align-items: baseline; }
.px-eng dt { font-size: 12px; color: #8A99AD; }
.px-eng dd { margin: 0; font-size: 14px; line-height: 1.45; color: #EEF3FA; }
.px-eng dd b { color: #EEF3FA; font-weight: 600; }
.px-eng dd span { display: block; margin-top: 2px; font-size: 12px; color: #8A99AD; }

/* ── Events ahead ── */
.px-evs { margin-bottom: 28px; scroll-margin-top: 90px; }
.px-evs-hd { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 16px; margin-bottom: 12px; }
.px-evs-hd h2 { margin: 0; font: 700 16px 'Chakra Petch', sans-serif; color: #EEF3FA; }
.px-evs-hd span, .px-evs-none { font-size: 13px; color: #B4C2D6; }
.px-evs-none { margin: 0; padding: 16px 20px; border: 1px dashed rgba(255,255,255,0.08); border-radius: 12px; }
.px-ev { border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; background: #070B14; padding: 20px 24px; animation: pxRise .4s ease both; }
.px-ev + .px-ev { margin-top: 12px; }
.px-ev header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.px-ev h4 { margin: 0; font: 700 18px 'Chakra Petch', sans-serif; color: #EEF3FA; }
.px-ev header p { margin: 4px 0 0; font-size: 14px; color: #B4C2D6; }
.px-ev-when { flex: none; font-size: 13px; font-weight: 600; color: #EEF3FA; border: 1px solid rgba(255,255,255,0.08); border-radius: 999px; padding: 4px 12px; }
.px-ev-when.now { color: #FFB020; border-color: rgba(255,176,32,.45); background: rgba(255,176,32,.07); }
.px-ev h5 { margin: 16px 0 8px; font: 600 13px 'Inter', sans-serif; color: #B4C2D6; }
.px-ef { display: grid; grid-template-columns: minmax(150px, 1.1fr) minmax(120px, 1fr) minmax(220px, 1.6fr); gap: 16px; align-items: center; padding: 8px 0; border-top: 1px solid #0A111D; }
.px-ef-l { font-size: 14px; color: #EEF3FA; }
.px-ef-l i { font-style: normal; font-size: 11px; color: #B4C2D6; border: 1px solid rgba(255,255,255,0.08); border-radius: 999px; padding: 0 8px; margin-left: 8px; white-space: nowrap; }
.px-ef-bar { position: relative; height: 8px; border-radius: 4px; background: #0A111D; }
.px-ef-bar::after { content: ""; position: absolute; left: 50%; top: -3px; bottom: -3px; width: 1px; background: rgba(255,255,255,0.10); }
.px-ef-bar i { position: absolute; top: 0; bottom: 0; border-radius: 4px; transform-origin: left; animation: pxGrow .7s ease-out both; }
.px-ef-bar i.up { background: #FFB020; } .px-ef-bar i.dn { background: #22E6F0; transform-origin: right; }
.px-ef.soft .px-ef-bar i { opacity: .55; }
.px-ef-v b { font-size: 14px; font-weight: 600; } .px-ef-v b.up { color: #FFB020; } .px-ef-v b.dn { color: #22E6F0; }
.px-ef-v em { display: block; font-style: normal; font-size: 12px; color: #8A99AD; }
.px-ev-read { margin: 12px 0 0; font-size: 14px; line-height: 1.55; color: #EEF3FA; max-width: 92ch; }
.px-ev footer { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; margin-top: 12px; font-size: 12px; color: #8A99AD; }
.px-ev footer button { font: 600 12px 'Inter', sans-serif; color: #22E6F0; background: rgba(34,230,240,.08); border: 1px solid rgba(34,230,240,.3); border-radius: 8px; padding: 4px 12px; cursor: pointer; }
.px-ev footer button:hover { background: rgba(34,230,240,.16); }

/* confidence in words on a card, a scenario range, an event inside the explanation */
.px-conf2 { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 12px; font-size: 12px; color: #B4C2D6; }
.px-lvl { font-weight: 600; }
.px-scn2 { margin-bottom: 8px; font-size: 13px; color: #B4C2D6; }
.px-scn2 b { color: #EEF3FA; font-weight: 600; }
.px-scn2 i, .px-evin i { font-style: normal; font-size: 11px; color: #22E6F0; border: 1px solid rgba(34,230,240,.35); border-radius: 999px; padding: 0 8px; margin-left: 4px; white-space: nowrap; }
.px-tag.ev { color: #FFB020; border-color: rgba(255,176,32,.35); background: rgba(255,176,32,.07); margin-top: 8px; }
.px-big .n.lv { font-size: 38px; }
.px-evin { margin-bottom: 24px; padding: 16px 16px; border: 1px solid rgba(255,176,32,.25); border-left: 3px solid #FFB020; border-radius: 8px; background: rgba(255,176,32,.04); }
.px-evin h4 { margin: 0 0 6px; font: 600 14px 'Inter', sans-serif; color: #EEF3FA; }
.px-evin h4 span { font-weight: 500; font-size: 12px; color: #FFB020; margin-left: 8px; }
.px-evin p { margin: 0; font-size: 14px; line-height: 1.55; color: #EEF3FA; }
.px-evin p + p { margin-top: 6px; }
.px-evin p.dim { color: #B4C2D6; font-size: 13px; }
.px-evin p b { color: #EEF3FA; }
.px-brief-body li.k-ev::before { background: #FFB020; }
.px-brief { display: block; }
@media (max-width: 1100px) {
  .px-eng { grid-template-columns: 1fr 1fr; }
  .px-eng-col:first-child { grid-column: 1 / -1; border-bottom: 1px solid #0A111D; }
  .px-eng-col:nth-child(2) { border-left: 0; }
}

/* ── Order of the page: act first, trust second, sources third ── */
.px-top { display: grid; grid-template-columns: 1.25fr 1fr; gap: 20px; margin-top: 16px; }
/* This week's plan */
.px-plan { margin-top: 20px; padding: 20px 20px; border-radius: 12px; background: linear-gradient(180deg, rgba(34,230,240,.05), rgba(34,230,240,.015)); border: 1px solid rgba(34,230,240,.16); }
.px-plan-hd { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.px-plan-hd h2 { margin: 0; font: 700 18px 'Chakra Petch', sans-serif; color: #EEF3FA; letter-spacing: .01em; }
.px-plan-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.px-act { text-align: left; display: flex; flex-direction: column; gap: 6px; padding: 16px 16px; border-radius: 12px; cursor: pointer;
  background: rgba(10,16,28,.72); border: 1px solid rgba(255,255,255,.07); border-left: 3px solid #39455A; color: #EEF3FA;
  opacity: 0; animation: pxRise .4s ease forwards; transition: border-color .2s, background .2s; font: inherit; }
.px-act:hover:not(:disabled) { background: rgba(16,24,40,.9); border-color: rgba(34,230,240,.28); }
.px-act:disabled { cursor: default; }
.px-act.k-hi { border-left-color: #E14038; } .px-act.k-up { border-left-color: #FFB020; } .px-act.k-dn { border-left-color: #22E6F0; }
.px-act.k-ev { border-left-color: #A78BFA; } .px-act.k-ok { border-left-color: #18D69A; }
.px-act-verb { font: 700 11px/1 'JetBrains Mono', monospace; letter-spacing: .1em; text-transform: uppercase; color: #8FA3BC; }
.px-act.k-hi .px-act-verb { color: #F87171; } .px-act.k-up .px-act-verb { color: #FFB020; } .px-act.k-dn .px-act-verb { color: #22E6F0; }
.px-act.k-ev .px-act-verb { color: #C4B5FD; } .px-act.k-ok .px-act-verb { color: #34D399; }
.px-act b { font-size: 14px; font-weight: 650; line-height: 1.3; }
.px-act-tx { font-size: 13px; line-height: 1.5; color: #B4C2D6; }
.px-act em { margin-top: auto; padding-top: 4px; font-style: normal; font-size: 12px; color: #22E6F0; }
.px-plan-more { margin-top: 12px; }
.px-plan-more summary { cursor: pointer; font-size: 13px; color: #8FA3BC; width: max-content; }
.px-plan-more summary:hover { color: #EEF3FA; }
.px-plan-brief { margin: 12px 0 0; padding-left: 20px; display: grid; gap: 4px; font-size: 14px; line-height: 1.55; color: #D5DEEA; }
.px-plan-ai { margin: 12px 0 0; font-size: 14px; line-height: 1.6; color: #D5DEEA; }
.px-plan-ai span { display: block; font: 600 11px 'JetBrains Mono', monospace; letter-spacing: .08em; text-transform: uppercase; color: #22E6F0; margin-bottom: 4px; }
/* Area status on a forecast card */
.px-st { flex: none; font: 600 11px/1 'Inter', sans-serif; padding: 4px 8px; border-radius: 999px; border: 1px solid rgba(255,255,255,.1); color: #8FA3BC; background: rgba(255,255,255,.03); }
.px-st.s-hi { color: #FCA5A5; border-color: rgba(225,64,56,.45); background: rgba(225,64,56,.12); }
.px-st.s-up { color: #FCD34D; border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.1); }
.px-st.s-dn { color: #67E8F9; border-color: rgba(34,230,240,.4); background: rgba(34,230,240,.08); }
.px-st.s-ev { color: #C4B5FD; border-color: rgba(167,139,250,.4); background: rgba(167,139,250,.08); }
/* Repeated alerts, and the "show all" under them */
/* Statewide units, listed apart from the areas */
.px-units { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 12px 16px 12px; border-top: 1px solid rgba(255,255,255,.06); }
.px-units-k { font: 600 11px 'JetBrains Mono', monospace; letter-spacing: .08em; text-transform: uppercase; color: #8FA3BC; margin-right: 4px; cursor: help; }
.px-units button { display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 999px; cursor: pointer;
  font: 500 12px 'Inter', sans-serif; color: #B4C2D6; background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.09); }
.px-units button:hover, .px-units button.on { color: #EEF3FA; border-color: rgba(34,230,240,.4); }
.px-units button i { width: 6px; height: 6px; border-radius: 50%; background: #39455A; }
.px-units button.s-hi i { background: #E14038; } .px-units button.s-up i { background: #FFB020; } .px-units button.s-dn i { background: #22E6F0; }
.pxd-rep { margin-left: 6px; font: 600 11px 'JetBrains Mono', monospace; color: #8FA3BC; }
.pxd-more { display: block; margin: 8px auto 4px; }
/* Sections folded until asked for */
.px-fold { margin-top: 24px; border-radius: 12px; border: 1px solid rgba(255,255,255,.07); background: rgba(10,16,28,.5); }
.px-fold > summary { list-style: none; cursor: pointer; display: flex; flex-direction: column; gap: 4px; padding: 16px 20px 16px 40px; position: relative; }
.px-fold > summary::-webkit-details-marker { display: none; }
.px-fold > summary::before { content: "▸"; position: absolute; left: 18px; top: 14px; color: #22E6F0; transition: transform .2s; }
.px-fold[open] > summary::before { transform: rotate(90deg); }
.px-fold > summary b { font: 650 14px 'Inter', sans-serif; color: #EEF3FA; }
.px-fold > summary span { font-size: 13px; line-height: 1.5; color: #8FA3BC; }
.px-fold > summary:hover b { color: #fff; }
.px-fold[open] { padding-bottom: 16px; }
.px-fold[open] > :not(summary) { margin-left: 16px; margin-right: 16px; }
.px-chip-btn { cursor: pointer; }
.px-chip-btn:hover { border-color: rgba(34,230,240,.4); color: #EEF3FA; }
.px-top .pxd-card { min-height: 0; height: 560px; max-height: 560px; }
.px-sec { margin: 32px 0 12px; font: 600 13px 'Inter', sans-serif; color: #B4C2D6; }
.px-explain { margin-top: 20px; }
.px-linkbtn { font: 600 12px 'Inter', sans-serif; color: #22E6F0; background: none; border: 0; padding: 0; cursor: pointer; }
.px-linkbtn:hover { text-decoration: underline; } .px-linkbtn:disabled { color: #8A99AD; cursor: default; text-decoration: none; }

.px-flt { display: flex; flex-wrap: wrap; gap: 6px; margin: -6px 0 12px; }
.px-flt button { font: 500 12px 'Inter', sans-serif; color: #B4C2D6; background: #070B14; border: 1px solid rgba(255,255,255,0.08); border-radius: 999px; padding: 4px 12px; cursor: pointer; white-space: nowrap; }
.px-flt button i { font-style: normal; margin-left: 6px; color: #8A99AD; font-variant-numeric: tabular-nums; }
.px-flt button:hover:not(:disabled) { color: #EEF3FA; border-color: rgba(255,255,255,0.10); }
.px-flt button { position: relative; isolation: isolate; }
.px-flt button.on { color: #EEF3FA; background: transparent; border-color: transparent; }
.px-flt-pill { position: absolute; inset: -1px; z-index: -1; border-radius: 999px; background: rgba(34,230,240,.12); border: 1px solid rgba(34,230,240,.5); }
.px-flt button.on i { color: #7FF0F7; }
.px-flt button:disabled { opacity: .4; cursor: default; }
.px-flt input { flex: 1 1 150px; min-width: 0; font: 500 13px 'Inter', sans-serif; color: #EEF3FA; background: #070B14; border: 1px solid rgba(255,255,255,0.08); border-radius: 999px; padding: 4px 12px; outline: none; }
.px-flt input:focus { border-color: rgba(34,230,240,.6); }
.px-flt input::placeholder { color: #8A99AD; }

.px-briefcard .px-brief-body { padding-right: 8px; }
.px-briefcard .px-brief-body li { font-size: 14px; }
.px-trust { display: flex; align-items: center; gap: 12px; margin-top: 12px; padding: 12px 12px; width: 100%; text-align: left; cursor: pointer;
  border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: #070B14; font: 500 13px 'Inter', sans-serif; color: #B4C2D6; }
.px-trust:hover { border-color: rgba(255,255,255,0.10); }
.px-trust b { font-size: 14px; }
.px-trust em { margin-left: auto; font-style: normal; font-weight: 600; color: #22E6F0; }

.px-conf { margin-top: 4px; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; background: #070B14; overflow: hidden; scroll-margin-top: 90px; }
.px-conf.is-wait { padding: 16px 20px; } .px-conf.is-wait p { margin: 0; font-size: 14px; line-height: 1.6; color: #B4C2D6; } .px-conf.is-wait b { color: #EEF3FA; }
.px-conf-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; width: 100%; padding: 16px 20px; background: none; border: 0; cursor: pointer; text-align: left; font-family: 'Inter', sans-serif; }
.px-conf-bar:hover { background: rgba(255,255,255,.02); }
.px-conf-k { font-size: 13px; font-weight: 600; color: #B4C2D6; }
.px-conf-lv { font: 700 20px 'Chakra Petch', sans-serif; }
.px-conf-lv.l-High { color: #18D69A; } .px-conf-lv.l-Moderate { color: #FFB020; } .px-conf-lv.l-Limited { color: #8A99AD; }
.px-conf-bar .px-eng-meter { width: 120px; margin: 0; flex: none; }
.px-conf-says { flex: 1 1 260px; font-size: 14px; color: #EEF3FA; }
.px-conf-more { margin-left: auto; font-size: 13px; font-weight: 600; color: #22E6F0; white-space: nowrap; }
.px-conf-more i { font-style: normal; margin-left: 6px; }
.px-conf-body { display: grid; grid-template-columns: 1.4fr 1fr; gap: 28px; padding: 4px 20px 20px; border-top: 1px solid #0A111D; animation: pxRise .25s ease both; }
.px-conf-body .px-eng-why { padding-top: 16px; }
.px-conf-rule { padding-top: 16px; }
.px-conf-rule h4 { margin: 0 0 6px; font: 600 13px 'Inter', sans-serif; color: #B4C2D6; }
.px-conf-rule p { margin: 0 0 8px; font-size: 13px; line-height: 1.55; color: #B4C2D6; }
.px-conf-rule b { color: #EEF3FA; font-weight: 600; }

.px-built { display: grid; grid-template-columns: 1fr 1.1fr 1fr; gap: 20px; }
.px-built .pxd-card { min-height: 0; max-height: none; }
.px-src dl { margin: 0; display: grid; gap: 12px; }
.px-src dl > div { display: grid; grid-template-columns: 112px 1fr; gap: 12px; align-items: baseline; }
.px-src dt { font-size: 12px; color: #8A99AD; }
.px-src dd { margin: 0; font-size: 14px; line-height: 1.45; color: #EEF3FA; }
.px-src dd b { color: #EEF3FA; font-weight: 600; }
.px-src dd span { display: block; margin-top: 2px; font-size: 12px; color: #8A99AD; }
.pxd-ttl i { font-style: normal; }

.px-stn { margin-bottom: 20px; padding: 16px 16px; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: #070B14; }
.px-stn-hd { font: 600 13px 'Inter', sans-serif; color: #EEF3FA; margin-bottom: 8px; }
.px-stn-hd i { font-style: normal; font-size: 11px; font-weight: 500; color: #22E6F0; border: 1px solid rgba(34,230,240,.35); border-radius: 999px; padding: 0 8px; margin-left: 8px; }
.px-stn ol { margin: 0; padding-left: 20px; display: grid; gap: 8px; }
.px-stn li b { display: block; font-size: 14px; font-weight: 600; color: #EEF3FA; }
.px-stn li span { font-size: 13px; line-height: 1.45; color: #B4C2D6; }
.px-stn p { margin: 12px 0 0; font-size: 12px; color: #8A99AD; }

@media (max-width: 1200px) {
  .px-top { grid-template-columns: 1fr 1fr; }
  .px-built { grid-template-columns: 1fr 1fr; }
  .px-built > :nth-child(2) { grid-column: 1 / -1; order: 3; }
}
@media (max-width: 820px) {
  .px-top, .px-built { grid-template-columns: 1fr; gap: 16px; }
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
  .px-eng-col { padding: 16px 0; border-left: 0 !important; border-top: 1px solid #0A111D; }
  .px-eng-col:first-child { border-top: 0; }
  .px-ev header { flex-direction: column; gap: 8px; }
  .px-ef { grid-template-columns: 1fr; gap: 4px; }
  .px-ef-bar { order: 3; }
  .px-brief { flex-direction: column; align-items: flex-start; gap: 12px; padding: 16px; }
  .px-brief-who { flex-direction: row; width: auto; gap: 12px; }
}
@media (prefers-reduced-motion: reduce) {
  .px-statbox, .px-card, .px-fade, .px-brief-ai, .px-conffill, .px-eng, .px-ev, .px-ef-bar i { animation: none !important; }
  .px-brief-body li { animation: none !important; opacity: 1; }
  .pxd-liner { animation: none !important; stroke-dashoffset: 0; }
}

/* ── production layout (2026-10-21) ── */
.px-kpis { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }
.px-kpi { text-align: left; display: grid; gap: 2px; padding: 12px 16px; border-radius: 12px; cursor: pointer; color: #EEF3FA;
  background: #070B14; border: 1px solid rgba(255,255,255,0.08); border-top: 2px solid #3A4A60; transition: background .15s, border-color .15s; }
.px-kpi:hover { background: #0C1322; border-color: rgba(34,230,240,.28); }
.px-kpi b { font: 700 24px/1.1 'JetBrains Mono', monospace; }
.px-kpi span { font-size: 12px; color: #B4C2D6; }
.px-kpi em { font-style: normal; font-size: 11px; color: #8A99AD; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.px-kpi.k-hi { border-top-color: #E14038; } .px-kpi.k-hi b { color: #F87171; }
.px-kpi.k-up { border-top-color: #FFB020; } .px-kpi.k-up b { color: #FFB020; }
.px-kpi.k-dn { border-top-color: #22E6F0; } .px-kpi.k-dn b { color: #22E6F0; }
.px-kpi.k-al { border-top-color: #60A5FA; } .px-kpi.k-al b { color: #93C5FD; }
.px-kpi.k-ev { border-top-color: #A78BFA; } .px-kpi.k-ev b { color: #C4B5FD; }
.px-kpi.zero b { color: #5B6B80; }
.px-top .pxd-card { scroll-margin-top: 90px; }
.px-explain { scroll-margin-top: 90px; animation: pxRise .3s ease both; }
.px-explain-x { margin-left: 12px; font: 600 12px 'Inter', sans-serif; color: #B4C2D6; background: none; border: 1px solid rgba(255,255,255,.12);
  border-radius: 8px; padding: 4px 12px; cursor: pointer; }
.px-explain-x:hover { color: #EEF3FA; border-color: rgba(34,230,240,.35); }

.px-plan { margin-top: 20px; }
.px-plan-hd h2 small { margin-left: 12px; font: 500 12px 'Inter', sans-serif; color: #8A99AD; }
.px-plan-list { display: grid; gap: 8px; }
.px-plan-list .px-act { padding: 0; display: block; cursor: default; }
.px-act-hd { width: 100%; display: grid; grid-template-columns: 96px minmax(0, 1fr) auto 14px; align-items: center; gap: 16px;
  padding: 12px 16px; background: none; border: 0; color: inherit; text-align: left; cursor: pointer; font: inherit; }
.px-act-hd b { font-size: 14px; font-weight: 650; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.px-act-short { font-size: 13px; color: #B4C2D6; white-space: nowrap; }
.px-act-hd i { width: 8px; height: 8px; border-right: 1.6px solid #8FA3BC; border-bottom: 1.6px solid #8FA3BC; transform: rotate(45deg); transition: transform .2s; justify-self: end; margin-top: -4px; }
.px-act.open .px-act-hd i { transform: rotate(-135deg); margin-top: 4px; }
.px-act-body { padding: 0 16px 16px 126px; display: grid; gap: 12px; animation: pxRise .25s ease both; }
.px-act-body p { margin: 0; font-size: 13px; line-height: 1.55; color: #D5DEEA; max-width: 80ch; }
.px-act-go { justify-self: start; font: 600 12px 'Inter', sans-serif; color: #22E6F0; background: rgba(34,230,240,.08);
  border: 1px solid rgba(34,230,240,.3); border-radius: 8px; padding: 4px 12px; cursor: pointer; }
.px-act-go:hover { background: rgba(34,230,240,.16); }

.px-evs { margin-top: 24px; }
.px-ev header { justify-content: flex-start; align-items: stretch; }
.px-ev.now { border-color: rgba(255,176,32,.35); }
.px-ev-count { flex: none; width: 64px; border-radius: 12px; display: grid; place-content: center; text-align: center;
  background: rgba(167,139,250,.08); border: 1px solid rgba(167,139,250,.3); }
.px-ev-count b { font: 700 24px/1 'JetBrains Mono', monospace; color: #C4B5FD; }
.px-ev-count span { font-size: 11px; color: #8A99AD; margin-top: 4px; }
.px-ev.now .px-ev-count { background: rgba(255,176,32,.08); border-color: rgba(255,176,32,.4); }
.px-ev.now .px-ev-count b { color: #FFB020; font-size: 18px; }
.px-ev-ttl { min-width: 0; }
.px-ev-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.px-ev-meta span { font-size: 12px; color: #B4C2D6; border: 1px solid rgba(255,255,255,.1); border-radius: 999px; padding: 2px 12px; }
.px-ev-meta span.in { color: #FFB020; border-color: rgba(255,176,32,.4); }
.px-ev-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,.06); }
.px-ev-col h5 { margin: 0 0 8px; font: 600 11px 'JetBrains Mono', monospace; letter-spacing: .08em; text-transform: uppercase; color: #8FA3BC; }
.px-ev-up { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.px-ev-up li { display: grid; gap: 1px; padding: 6px 12px; border-left: 2px solid #FFB020; background: rgba(255,176,32,.05); border-radius: 0 8px 8px 0; }
.px-ev-up li.soft { border-left-style: dashed; background: none; }
.px-ev-up b { font-size: 13px; color: #EEF3FA; }
.px-ev-up span { font-size: 12px; color: #B4C2D6; }
.px-ev-all, .px-ev-dn, .px-ev-none { margin: 0; font-size: 13px; line-height: 1.5; color: #D5DEEA; }
.px-ev-dn { margin-top: 8px; color: #B4C2D6; }
.px-ev-all em, .px-ev-dn em { font-style: normal; color: #8A99AD; font-size: 12px; }
.px-ev-more { margin-top: 12px; }
.px-ev-more summary { cursor: pointer; font-size: 13px; color: #8FA3BC; }
.px-ev-more summary:hover { color: #EEF3FA; }
.px-ev-src { margin: 8px 0 0; font-size: 12px; color: #8A99AD; }
@media (max-width: 860px) { .px-kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 1180px) { .px-kpi { padding: var(--sp-3); } .px-kpi b { font-size: 26px; } }
@media (max-width: 720px) {
  .px-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .px-act-hd { grid-template-columns: minmax(0, 1fr) 14px; gap: 4px 12px; }
  .px-act-hd .px-act-verb { grid-column: 1; } .px-act-hd b { grid-column: 1; white-space: normal; } .px-act-short { grid-column: 1; }
  .px-act-hd i { grid-column: 2; grid-row: 1 / span 3; }
  .px-act-body { padding: 0 16px 16px; }
  .px-ev-grid { grid-template-columns: 1fr; }
}

/* ── quiet colour (2026-10-21): neutral at rest, the meaning shows on hover ── */
.px-sec-note { margin: -4px 0 12px; font-size: 13px; line-height: 1.5; color: #8A99AD; max-width: 90ch; }
.pxd-card .px-sec-note { margin: 0 0 12px; padding: 0 2px; }
.px-head .px-howbtn { color: #B4C2D6; background: none; border-color: rgba(255,255,255,.14); }
.px-head .px-howbtn:hover { color: #22E6F0; border-color: rgba(34,230,240,.4); background: rgba(34,230,240,.06); box-shadow: none; }

.px-kpi, .px-kpi.k-hi, .px-kpi.k-up, .px-kpi.k-dn, .px-kpi.k-al, .px-kpi.k-ev { border-top-color: rgba(255,255,255,.1); }
.px-kpi b, .px-kpi.k-hi b, .px-kpi.k-up b, .px-kpi.k-dn b, .px-kpi.k-al b, .px-kpi.k-ev b { color: #EEF3FA; transition: color .15s; }
.px-kpi.zero b { color: #5B6B80; }
.px-kpi em { white-space: normal; line-height: 1.35; margin-top: 2px; }
.px-kpi:hover { background: #0B111D; }
.px-kpi.k-hi:hover { border-top-color: #E14038; } .px-kpi.k-hi:hover b { color: #F87171; }
.px-kpi.k-up:hover { border-top-color: #FFB020; } .px-kpi.k-up:hover b { color: #FFB020; }
.px-kpi.k-dn:hover { border-top-color: #22E6F0; } .px-kpi.k-dn:hover b { color: #22E6F0; }
.px-kpi.k-al:hover { border-top-color: #60A5FA; } .px-kpi.k-al:hover b { color: #93C5FD; }
.px-kpi.k-ev:hover { border-top-color: #A78BFA; } .px-kpi.k-ev:hover b { color: #C4B5FD; }

.px-st.s-hi, .px-st.s-up, .px-st.s-dn, .px-st.s-ev { color: #B4C2D6; border-color: rgba(255,255,255,.12); background: rgba(255,255,255,.03); transition: color .15s, background-color .15s, border-color .15s, box-shadow .15s, opacity .15s, transform .15s, scale .15s; }
.px-card:hover .px-st.s-hi, .px-card.on .px-st.s-hi { color: #FCA5A5; border-color: rgba(225,64,56,.45); background: rgba(225,64,56,.1); }
.px-card:hover .px-st.s-up, .px-card.on .px-st.s-up { color: #FCD34D; border-color: rgba(255,176,32,.4); background: rgba(255,176,32,.08); }
.px-card:hover .px-st.s-dn, .px-card.on .px-st.s-dn { color: #67E8F9; border-color: rgba(34,230,240,.4); background: rgba(34,230,240,.07); }
.px-card:hover .px-st.s-ev, .px-card.on .px-st.s-ev { color: #C4B5FD; border-color: rgba(167,139,250,.4); background: rgba(167,139,250,.07); }
.px-say b.up, .px-say b.dn { color: #EEF3FA; transition: color .15s; }
.px-card:hover .px-say b.up, .px-card.on .px-say b.up { color: #FFB020; }
.px-card:hover .px-say b.dn, .px-card.on .px-say b.dn { color: #22E6F0; }
.px-conf2 .px-lvl.l-High, .px-conf2 .px-lvl.l-Medium, .px-conf2 .px-lvl.l-Low { color: #B4C2D6; }
.px-card:hover .px-lvl.l-High { color: #18D69A; } .px-card:hover .px-lvl.l-Medium { color: #FFB020; }
.px-tag.ev { color: #B4C2D6; border-color: rgba(255,255,255,.12); background: rgba(255,255,255,.03); }
.px-card:hover .px-tag.ev { color: #FFB020; border-color: rgba(255,176,32,.35); background: rgba(255,176,32,.07); }
.px-know { color: #B4C2D6; background: none; border-color: rgba(255,255,255,.14); }
.px-know:hover { color: #22E6F0; background: rgba(34,230,240,.08); border-color: rgba(34,230,240,.4); box-shadow: none; }
.px-card:hover { border-color: rgba(255,255,255,.16); background: #0A101C; }
.px-card.on { background: rgba(34,230,240,.05); border-color: rgba(34,230,240,.45); box-shadow: none; }

.pxd-sev.hi, .pxd-sev.md, .pxd-sev.lo { color: #B4C2D6; background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.12); transition: color .15s, background-color .15s, border-color .15s, box-shadow .15s, opacity .15s, transform .15s, scale .15s; }
.pxd-alert:hover .pxd-sev.hi, .pxd-alert.on .pxd-sev.hi { color: #F87171; background: rgba(225,64,56,.12); border-color: rgba(225,64,56,.35); }
.pxd-alert:hover .pxd-sev.md, .pxd-alert.on .pxd-sev.md { color: #FFB020; background: rgba(255,176,32,.1); border-color: rgba(255,176,32,.3); }

.px-plan { background: #070B14; border-color: rgba(255,255,255,.08); }
.px-plan-list .px-act, .px-plan-list .px-act.k-hi, .px-plan-list .px-act.k-up, .px-plan-list .px-act.k-dn, .px-plan-list .px-act.k-ev, .px-plan-list .px-act.k-ok { border-left-color: rgba(255,255,255,.12); transition: border-color .15s, background .15s; }
.px-plan-list .px-act .px-act-verb { color: #8FA3BC; transition: color .15s; }
.px-plan-list .px-act.k-hi:hover, .px-plan-list .px-act.k-hi.open { border-left-color: #E14038; } .px-plan-list .px-act.k-hi:hover .px-act-verb, .px-plan-list .px-act.k-hi.open .px-act-verb { color: #F87171; }
.px-plan-list .px-act.k-up:hover, .px-plan-list .px-act.k-up.open { border-left-color: #FFB020; } .px-plan-list .px-act.k-up:hover .px-act-verb, .px-plan-list .px-act.k-up.open .px-act-verb { color: #FFB020; }
.px-plan-list .px-act.k-dn:hover, .px-plan-list .px-act.k-dn.open { border-left-color: #22E6F0; } .px-plan-list .px-act.k-dn:hover .px-act-verb, .px-plan-list .px-act.k-dn.open .px-act-verb { color: #22E6F0; }
.px-plan-list .px-act.k-ev:hover, .px-plan-list .px-act.k-ev.open { border-left-color: #A78BFA; } .px-plan-list .px-act.k-ev:hover .px-act-verb, .px-plan-list .px-act.k-ev.open .px-act-verb { color: #C4B5FD; }
.px-plan-list .px-act.k-ok:hover, .px-plan-list .px-act.k-ok.open { border-left-color: #18D69A; } .px-plan-list .px-act.k-ok:hover .px-act-verb, .px-plan-list .px-act.k-ok.open .px-act-verb { color: #34D399; }
.px-plan-list .px-act:hover { background: #0B111D; }
.px-act-go { color: #B4C2D6; background: none; border-color: rgba(255,255,255,.14); }
.px-act-go:hover { color: #22E6F0; border-color: rgba(34,230,240,.4); background: rgba(34,230,240,.06); }

.px-ev-count, .px-ev.now .px-ev-count { background: rgba(255,255,255,.03); border-color: rgba(255,255,255,.12); transition: color .15s, background-color .15s, border-color .15s, box-shadow .15s, opacity .15s, transform .15s, scale .15s; }
.px-ev-count b, .px-ev.now .px-ev-count b { color: #EEF3FA; transition: color .15s; }
.px-ev:hover .px-ev-count { background: rgba(167,139,250,.08); border-color: rgba(167,139,250,.35); }
.px-ev:hover .px-ev-count b { color: #C4B5FD; }
.px-ev.now:hover .px-ev-count { background: rgba(255,176,32,.08); border-color: rgba(255,176,32,.4); } .px-ev.now:hover .px-ev-count b { color: #FFB020; }
.px-ev.now { border-color: rgba(255,255,255,.08); }
.px-ev-meta span.in { color: #B4C2D6; border-color: rgba(255,255,255,.1); }
.px-ev:hover .px-ev-meta span.in { color: #FFB020; border-color: rgba(255,176,32,.4); }
.px-ev-up li, .px-ev-up li.soft { border-left-color: rgba(255,255,255,.14); background: rgba(255,255,255,.02); transition: color .15s, background-color .15s, border-color .15s, box-shadow .15s, opacity .15s, transform .15s, scale .15s; }
.px-ev:hover .px-ev-up li { border-left-color: #FFB020; background: rgba(255,176,32,.05); }
.px-ev footer button { color: #B4C2D6; background: none; border-color: rgba(255,255,255,.14); }
.px-ev footer button:hover { color: #22E6F0; border-color: rgba(34,230,240,.4); background: rgba(34,230,240,.06); }

/* ── meaning dots: a small coloured dot says the level at rest; the rest stays grey ── */
.px-st::before, .pxd-sev::before, .px-plan-list .px-act-verb::before, .px-kpi span::before {
  content: ""; display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; vertical-align: 1px; background: #5B6B80; }
.px-st.s-hi::before, .pxd-sev.hi::before, .px-plan-list .k-hi .px-act-verb::before, .px-kpi.k-hi span::before { background: #E14038; }
.px-st.s-up::before, .pxd-sev.md::before, .px-plan-list .k-up .px-act-verb::before, .px-kpi.k-up span::before { background: #FFB020; }
.px-st.s-dn::before, .px-plan-list .k-dn .px-act-verb::before, .px-kpi.k-dn span::before { background: #22E6F0; }
.px-st.s-ev::before, .px-plan-list .k-ev .px-act-verb::before, .px-kpi.k-ev span::before { background: #A78BFA; }
.px-plan-list .k-ok .px-act-verb::before { background: #18D69A; }
.px-kpi.k-al span::before { background: #60A5FA; }
.px-kpi.zero span::before { background: #3A4A60; }
/* plan verbs: plain words in sentence case, read at a glance */
.px-plan-list .px-act-verb { font: 600 12px/1.2 'Inter', sans-serif; letter-spacing: 0; text-transform: none; white-space: nowrap; }
.px-act-hd { grid-template-columns: 128px minmax(0, 1fr) auto 14px; }
.px-act-body { padding-left: 158px; }
@media (max-width: 720px) { .px-act-hd { grid-template-columns: minmax(0, 1fr) 14px; } .px-act-body { padding-left: 16px; } }
.px-term { text-decoration: underline dotted rgba(180,194,214,.5); text-underline-offset: 3px; cursor: help; }
.px-ev-up small { font-size: 12px; line-height: 1.4; color: #B4C2D6; }
.px-insp-plain { margin: -8px 0 16px; font-size: 13px; color: #B4C2D6; }
/* ── Hierarchy (design-tokens.css): what to look at first ──
   1 the page title  2 the week in five figures  3 this week's plan (start here)
   4 the forecast and the alerts  5 events  6 the fold-outs. One primary button per view. */
.px-page { gap: var(--sp-6); padding-top: 72px; }
.px-head { align-items: flex-end; gap: var(--sp-4); }
.px-title { font-size: var(--fs-h1); line-height: 1.15; letter-spacing: .01em; margin-bottom: var(--sp-2); color: var(--ink-1); }
.px-sub { font: 400 var(--fs-body)/1.55 'Inter', sans-serif; color: var(--ink-2); max-width: 72ch; letter-spacing: 0; }
.px-head-r { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-2); }
.px-chip { font-size: var(--fs-label); padding: var(--sp-1) var(--sp-3); border-radius: var(--r-pill); }

/* the week: figures that need attention keep their colour; zeros step back */
.px-kpis { gap: var(--sp-3); margin-top: 0; }
.px-kpi { padding: var(--sp-4); border-radius: var(--r-lg); gap: var(--sp-1); }
.px-kpi b { font: 700 var(--fs-figure)/1 'JetBrains Mono', monospace; letter-spacing: -.01em; }
.px-kpi span { font: 600 var(--fs-body-sm)/1.3 'Inter', sans-serif; color: var(--ink-1); }
.px-kpi em { font-size: var(--fs-label); color: var(--ink-3); }
.px-kpi.k-hi:not(.zero) b { color: #F87171; } .px-kpi.k-up:not(.zero) b { color: #FFB020; }
.px-kpi.k-dn:not(.zero) b { color: #22E6F0; } .px-kpi.k-al:not(.zero) b { color: #93C5FD; } .px-kpi.k-ev:not(.zero) b { color: #C4B5FD; }
.px-kpi.k-hi:not(.zero) { border-top-color: #E14038; } .px-kpi.k-up:not(.zero) { border-top-color: #FFB020; }
.px-kpi.k-dn:not(.zero) { border-top-color: #22E6F0; } .px-kpi.k-al:not(.zero) { border-top-color: #60A5FA; } .px-kpi.k-ev:not(.zero) { border-top-color: #A78BFA; }
.px-kpi.zero { background: transparent; border-color: var(--line-1); }
.px-kpi.zero b { color: var(--ink-4); } .px-kpi.zero span { color: var(--ink-3); font-weight: 500; }

/* the plan: the one section with weight */
.px-plan { margin-top: 0; padding: var(--sp-5) var(--sp-6); border-radius: var(--r-lg); border-color: rgba(34,230,240,.24);
  background: linear-gradient(180deg, rgba(34,230,240,.07), rgba(34,230,240,.015)); }
.px-plan-hd { align-items: flex-end; margin-bottom: var(--sp-2); }
.px-plan-hd h2, .px-evs-hd h2 { font: 700 var(--fs-h2)/1.2 'Chakra Petch', sans-serif; color: var(--ink-1); letter-spacing: .01em; }
.px-plan-hd h2 small { font-size: var(--fs-label); color: var(--ink-3); }
.px-plan .px-sec-note { margin: 0 0 var(--sp-4); }
.px-plan-list { display: grid; gap: var(--sp-2); }
.px-act-hd { padding: var(--sp-3) var(--sp-4); }
.px-act-hd b { font-size: var(--fs-body); color: var(--ink-1); }
.px-act-short { font-size: var(--fs-body-sm); color: var(--ink-2); }
.px-act-body p { font-size: var(--fs-body); line-height: 1.55; color: var(--ink-2); }
.px-act-go.ui-btn { color: var(--accent); background: rgba(34,230,240,.08); border-color: rgba(34,230,240,.38); }

/* every other section: same title, same note */
.px-top { margin-top: 0; gap: var(--sp-5); }
.pxd-card { padding: var(--sp-5); border-radius: var(--r-lg); }
.pxd-hd { margin-bottom: var(--sp-3); padding-bottom: var(--sp-3); }
.pxd-ttl { font: 700 var(--fs-h3)/1.25 'Chakra Petch', sans-serif; color: var(--ink-1); letter-spacing: .01em; }
.pxd-sub, .pxd-note { font-size: var(--fs-label); color: var(--ink-3); }
.px-sec-note, .px-evs-hd span { font-size: var(--fs-body-sm); line-height: 1.5; color: var(--ink-3); max-width: 80ch; }
.px-evs { margin: 0; }
.px-evs-hd { gap: var(--sp-1) var(--sp-4); margin-bottom: var(--sp-3); }
.px-fold { margin-top: 0; border-radius: var(--r-lg); }
.px-fold > summary { padding: var(--sp-4) var(--sp-5) var(--sp-4) var(--sp-10); }
.px-fold > summary::before { top: var(--sp-4); }
.px-fold > summary b { font: 600 var(--fs-lead) 'Inter', sans-serif; color: var(--ink-1); }
.px-fold > summary span { font-size: var(--fs-body-sm); color: var(--ink-3); }

/* the forecast cards: area first, then the crime, then the figure */
.px-zone { font-size: var(--fs-lead); font-weight: 600; color: var(--ink-1); }
.px-crime { font-size: var(--fs-body-sm); color: var(--ink-2); }
.px-say b { font-size: var(--fs-body-sm); }
.px-say span, .px-conf2 { font-size: var(--fs-label); color: var(--ink-3); }

/* the picked forecast's actions: done, ask, then the quiet tools */
.px-acts { align-items: center; gap: var(--sp-2); }
.px-acts-sep { width: 1px; height: 22px; margin: 0 var(--sp-1); background: var(--line-2); }
.px-actbtn.ui-btn { font-family: 'Inter', sans-serif; letter-spacing: 0; }
.px-actbtn.ui-btn--primary { background: var(--accent); color: var(--accent-ink); border-color: transparent; }
.px-actbtn.ui-btn--primary:hover { background: #5EF0F7; color: var(--accent-ink); }
.px-actbtn.ui-btn--secondary { background: rgba(34,230,240,.08); border-color: rgba(34,230,240,.38); color: var(--accent); }
.px-actbtn.ui-btn--ghost { background: transparent; border-color: var(--line-2); color: var(--ink-2); }
.px-actbtn.ui-btn--ghost.on { color: var(--accent); border-color: rgba(34,230,240,.45); }
.px-head .px-howbtn.ui-btn { font-family: 'Inter', sans-serif; letter-spacing: 0; }
@media (max-width: 860px) { .px-kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 1180px) { .px-kpi { padding: var(--sp-3); } .px-kpi b { font-size: 26px; } }
@media (max-width: 680px) { .px-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } .px-plan { padding: var(--sp-4); } .px-acts-sep { display: none; } }

/* the opened forecast: a panel title, then the area as its headline (below the page title) */
.px-panel-hd > span:first-child { font: 600 var(--fs-label)/1.2 'Inter', sans-serif; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }
html[lang="kn"] .px-panel-hd > span:first-child { letter-spacing: normal; text-transform: none; }
.px-hint { font-size: var(--fs-label); color: var(--ink-3); }
.px-insp-title { font-size: 24px; line-height: 1.25; color: var(--ink-1); }
.px-insp-why { font-size: var(--fs-body); line-height: 1.6; }
.px-saw h4, .px-evin h4 { font: 600 var(--fs-label) 'Inter', sans-serif; color: var(--ink-3); }
.px-saw li, .px-saw p { font-size: var(--fs-body-sm); color: var(--ink-2); }

/* ── Editorial layer: no AI look ──
   Rules, numbers and type carry the page; boxes, gradients, glows and pills are taken out.
   One accent (cyan) for the words that matter, one solid button for the next step. */
.px-page { gap: var(--sp-8); }

/* hero */
.px-hero { display: grid; gap: var(--sp-5); padding-bottom: var(--sp-6); border-bottom: 1px solid var(--line-2); }
.px-hero-main { max-width: 860px; }
.px-eyebrow { display: block; margin-bottom: var(--sp-3); font: 500 var(--fs-label)/1.3 'JetBrains Mono', monospace; letter-spacing: .12em; text-transform: uppercase; color: var(--ink-3); }
html[lang="kn"] .px-eyebrow { letter-spacing: normal; text-transform: none; font-family: inherit; }
.px-hero .px-title { margin: 0; font: 700 clamp(32px, 4.2vw, 52px)/1.04 'Chakra Petch', sans-serif; letter-spacing: -.02em; color: var(--ink-1); text-wrap: balance; }
.px-hero .px-title em { font-style: normal; color: var(--accent); }
.px-hero .px-sub { margin: var(--sp-4) 0 0; max-width: 62ch; font: 400 var(--fs-lead)/1.55 'Inter', sans-serif; color: var(--ink-2); }
.px-hero-cta { display: flex; flex-wrap: wrap; gap: var(--sp-3); margin-top: var(--sp-6); }
.px-hero-cta .ui-btn { min-height: 44px; padding: 0 var(--sp-5); font-size: var(--fs-body); }
.px-meta { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--sp-1) var(--sp-5); margin: 0; font: 500 var(--fs-label)/1.4 'JetBrains Mono', monospace; color: var(--ink-3); }
.px-meta b { color: var(--ink-1); font-weight: 600; }
.px-meta-btn { padding: 0; font: inherit; color: inherit; background: none; border: 0; border-bottom: 1px dashed var(--line-2); cursor: pointer; }
.px-meta-btn:hover { color: var(--ink-1); border-bottom-color: var(--accent); }
.px-meta .px-offline { color: #FFB020; }

/* solid primary: no glow, an arrow says "go" */
.px-page .ui-btn--primary { background: var(--ink-1); color: #050A12; box-shadow: none; }
.px-page .ui-btn--primary:hover:not(:disabled) { background: #FFFFFF; }
.px-actbtn.ui-btn--primary { background: var(--ink-1); color: #050A12; }
.px-actbtn.ui-btn--primary:hover { background: #fff; color: #050A12; }

/* the week: figures on a rule, divided by hairlines (no boxes) */
.px-stats { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); border-top: 1px solid var(--line-2); border-bottom: 1px solid var(--line-1); }
.px-stat { display: grid; gap: var(--sp-1); align-content: start; padding: var(--sp-4) var(--sp-5) var(--sp-5); text-align: left; background: none; border: 0; border-left: 1px solid var(--line-1); color: var(--ink-1); cursor: pointer; transition: background-color .18s ease; }
.px-stat:first-child { border-left: 0; padding-left: 0; }
.px-stat:hover { background: rgba(255,255,255,.025); }
.px-stat:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.px-stat b { font: 700 40px/1 'Chakra Petch', sans-serif; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
.px-stat span { font: 600 var(--fs-body-sm)/1.3 'Inter', sans-serif; color: var(--ink-1); }
.px-stat em { font-style: normal; font-size: var(--fs-label); line-height: 1.4; color: var(--ink-3); }
.px-stat.k-hi:not(.zero) b { color: #F87171; } .px-stat.k-up:not(.zero) b { color: #FFB020; } .px-stat.k-dn:not(.zero) b { color: var(--accent); }
.px-stat.k-al:not(.zero) b { color: #93C5FD; } .px-stat.k-ev:not(.zero) b { color: #C4B5FD; }
.px-stat.zero b { color: var(--ink-4); } .px-stat.zero span { color: var(--ink-3); font-weight: 500; }

/* numbered sections: a number, a title, a rule */
.px-secnum { margin-right: var(--sp-3); font: 500 var(--fs-label) 'JetBrains Mono', monospace; letter-spacing: .06em; color: var(--accent); vertical-align: .2em; }
.px-plan { padding: var(--sp-6) 0 0; border: 0; border-top: 1px solid var(--line-2); border-radius: 0; background: none; }
.px-plan .ui-eyebrow { display: none; }
.px-plan-hd h2, .px-evs-hd h2 { font-size: 24px; letter-spacing: -.01em; }
.px-act { border-radius: 0; background: none; border: 0; border-bottom: 1px solid var(--line-1); border-left: 0; }
.px-act:first-child { border-top: 1px solid var(--line-1); }
.px-act-hd { padding: var(--sp-4) 0; }
.px-act .px-act-verb { font: 500 var(--fs-label) 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: .06em; }
.px-act-body { padding: 0 0 var(--sp-4); }

/* the two lists: open columns with a top rule, not floating cards */
.pxd-card { background: none; border: 0; border-top: 1px solid var(--line-2); border-radius: 0; box-shadow: none; padding: var(--sp-5) 0 0; }
.pxd-hd { border-bottom: 0; padding-bottom: 0; }
.pxd-ttl { font-size: 24px; letter-spacing: -.01em; }
.px-top { gap: var(--sp-10); }
.px-card { border-radius: 0; border: 0; border-bottom: 1px solid var(--line-1); background: none; box-shadow: none; }
.px-card:hover { background: rgba(255,255,255,.025); }
.px-card.on { background: rgba(34,230,240,.05); }
.pxd-alert { border-radius: 0; border-bottom: 1px solid var(--line-1); }

/* filters: words with an underline, not pills */
.px-flt { gap: var(--sp-1) var(--sp-4); margin: 0 0 var(--sp-3); border-bottom: 1px solid var(--line-1); }
.px-flt button { padding: var(--sp-2) 0; border: 0; border-radius: 0; background: none; color: var(--ink-3); }
.px-flt button:hover:not(:disabled) { color: var(--ink-1); border: 0; }
.px-flt button.on { color: var(--ink-1); }
.px-flt-pill { inset: auto 0 -1px 0; height: 2px; border: 0; border-radius: 0; background: var(--accent); }
.px-flt input { flex: 1 1 180px; margin: var(--sp-1) 0; border-radius: var(--r-sm); background: transparent; }

/* events and fold-outs: the same rule-and-title rhythm */
.px-evs { padding-top: var(--sp-6); border-top: 1px solid var(--line-2); }
.px-fold { border: 0; border-top: 1px solid var(--line-1); border-radius: 0; background: none; }
.px-fold:last-of-type { border-bottom: 1px solid var(--line-1); }
.px-fold > summary { padding-left: var(--sp-8); }
.px-fold > summary::before { left: 0; }

/* the picked forecast: a plain panel with one rule on top */
.px-explain { border-radius: 0; border: 0; border-top: 2px solid var(--accent); background: rgba(255,255,255,.02); box-shadow: none; }

@media (max-width: 860px) {
  .px-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .px-stat:nth-child(4) { border-left: 0; padding-left: 0; }
  .px-stat:nth-child(n+4) { border-top: 1px solid var(--line-1); }
}
@media (max-width: 560px) {
  .px-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .px-stat:nth-child(odd) { border-left: 0; padding-left: 0; } .px-stat:nth-child(4) { border-left: 1px solid var(--line-1); padding-left: var(--sp-5); }
  .px-stat:nth-child(n+3) { border-top: 1px solid var(--line-1); }
  .px-hero-cta .ui-btn { flex: 1 1 100%; }
}

/* status reads as a coloured dot and a word, not a pill */
.px-st, .pxd-sev { display: inline-flex; align-items: center; gap: 6px; padding: 0 !important; border: 0 !important; background: none !important; border-radius: 0;
  font: 500 var(--fs-label)/1.2 'Inter', sans-serif; letter-spacing: 0; text-transform: none; }
.px-st::before, .pxd-sev::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; flex: none; }
.px-know { padding: 0; border: 0; background: none; border-radius: 0; font: 600 var(--fs-label) 'Inter', sans-serif; color: var(--accent); }
.px-know:hover { text-decoration: underline; background: none; }
.px-units { gap: var(--sp-1) var(--sp-4); padding-top: var(--sp-3); border-top: 1px solid var(--line-1); }
.px-units button { padding: 0; border: 0; background: none; border-radius: 0; font: 500 var(--fs-body-sm) 'Inter', sans-serif; color: var(--ink-2); }
.px-units button:hover, .px-units button.on { color: var(--ink-1); text-decoration: underline; text-underline-offset: 3px; }
.px-units-k { font: 500 var(--fs-caption) 'JetBrains Mono', monospace; letter-spacing: .1em; color: var(--ink-3); }
.px-tag { border-radius: var(--r-sm); }

/* events: an open row under the section rule, not a card in a card */
.px-ev { padding: var(--sp-5) 0 0; border: 0; border-radius: 0; background: none; box-shadow: none; }
.px-ev.now { border: 0; }
.px-ev + .px-ev { margin-top: var(--sp-6); border-top: 1px solid var(--line-1); }
.px-ev-count { width: 72px; border-radius: 0; background: none; border: 0; border-right: 1px solid var(--line-2); padding-right: var(--sp-4); }
.px-ev-count b { font: 700 40px/1 'Chakra Petch', sans-serif; letter-spacing: -.02em; color: #C4B5FD; }
.px-ev h4 { font-size: 24px; letter-spacing: -.01em; }
.px-ev-meta { gap: var(--sp-1) var(--sp-4); }
.px-ev-meta span, .px-ev-meta span.in { padding: 0; border: 0; border-radius: 0; font: 500 var(--fs-label) 'JetBrains Mono', monospace; color: var(--ink-3); }
.px-ev-meta span + span::before { content: "·"; margin-right: var(--sp-4); color: var(--ink-4); }
.px-ev-grid { gap: var(--sp-8); border-top-color: var(--line-1); }
.px-ev-up li { padding: 0 0 var(--sp-3); border: 0; border-radius: 0; background: none; border-bottom: 1px solid var(--line-1); }
.px-ev-up li + li { padding-top: var(--sp-3); }
.px-ev footer { margin-top: var(--sp-5); }
.px-ev footer .ui-btn--secondary { color: var(--accent); background: rgba(34,230,240,.08); border-color: rgba(34,230,240,.38); }
.px-ev footer .ui-btn--ghost { color: var(--ink-2); background: none; border-color: var(--line-2); }

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
  const planRef = useRef(null);
  const [engOpen, setEngOpen] = useState(false);     // the reasons behind the confidence level: closed until asked for
  const confRef = useRef(null);
  const [flt, setFlt] = useState("attention");       // which forecasts are listed: what needs attention first
  const [allAlerts, setAllAlerts] = useState(false);  // alerts beyond the strongest six
  const [relOpen, setRelOpen] = useState(false);      // "How reliable is this forecast", folded until asked for
  const [findArea, setFindArea] = useState("");
  const [whyUnit, setWhyUnit] = useState(null);       // the station whose forecast is taken apart
  const [planFor, setPlanFor] = useState(null);       // the station whose shift plan is open
  const [explainOpen, setExplainOpen] = useState(initFocus === "alert");  // "Why this forecast" opens only once something is picked
  const [planOpen, setPlanOpen] = useState(null);     // the plan action that is open
  const forecastRef = useRef(null);
  const alertsRef = useRef(null);
  const [stations, setStations] = useState(null);    // station forecasts for the area being explained
  const [copied, setCopied] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState(toRfNodes(DEMO_NODES));
  const [edges, setEdges, onEdgesChange] = useEdgesState(toRfEdges(DEMO_EDGES));
  const consoleRef = useRef(null);
  const abortRef = useRef(null);
  const reasonRef = useRef(null);

  // The outlook is for "the next 7 days from today": a page left open overnight must not
  // keep yesterday's week (an event that has ended, one that has started). It reloads every
  // 15 minutes, and at once when the officer comes back to the tab on a new day.
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let day = new Date().toDateString();
    const again = () => setTick((t) => t + 1);
    const iv = setInterval(again, 15 * 60 * 1000);
    const onVis = () => {
      if (document.visibilityState === "visible" && new Date().toDateString() !== day) { day = new Date().toDateString(); again(); }
    };
    document.addEventListener("visibilitychange", onVis);
    return () => { clearInterval(iv); document.removeEventListener("visibilitychange", onVis); };
  }, []);

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
      if (e.detail?.wow === 3) { setFocusKind("prediction"); setSelected(0); setExplainOpen(true); setShowReasoning(true); }
    };
    window.addEventListener("antar-demo-trigger", handler);
    return () => window.removeEventListener("antar-demo-trigger", handler);
  }, [tick]);

  // Whatever is being explained below - a ranked prediction or a clicked alert.
  const rawAlert = alertList[selAlert];
  const focusItem = !explainOpen ? null : focusKind === "alert" && rawAlert
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
  const A = P.filter((x) => !isUnit(x));                       // the areas
  const unitCards = P.map((x, i) => ({ p: x, i })).filter(({ p: x }) => isUnit(x));
  const evsAhead = (eng && eng !== "missing" && eng.events) || [];
  const highs = A.filter((x) => x.risk === "HIGH");
  const aboves = A.filter((x) => x.direction !== "silence" && (Number(x.z_score) || 0) >= 2).sort((a, b) => (b.z_score || 0) - (a.z_score || 0));
  const drops = A.filter((x) => x.direction === "silence");
  const usual = A.filter((x) => x.risk !== "HIGH" && x.direction !== "silence" && (Number(x.z_score) || 0) < 2).length;
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
  // The week as things to do. A forecast is only worth reading if it changes a decision:
  // where the beat staff go (patrol), which station is asked about its register (check),
  // and which event needs a bandobast plan. At most four, the strongest first.
  const plan = [];
  if (P.length) {
    for (const x of highs.slice(0, 2)) plan.push({ k: "hi", verb: kn ? "ಆದ್ಯತೆ" : "Act first", go: x,
      title: `${x.zone}: ${cap(x.crime_type)}`, plain: plainCrime(x.crime_type), short: rangeOf(x) ? `${rangeOf(x)} expected` : "High risk",
      text: `High risk${rangeOf(x) ? `, ${rangeOf(x)} expected` : ""}. Put extra beat visits on the stations listed under its forecast.` });
    for (const x of aboves.filter((a) => !highs.includes(a)).slice(0, Math.max(0, 2 - plan.length))) plan.push({ k: "up", verb: kn ? "ಗಸ್ತು" : "More patrols", go: x,
      title: `${x.zone}: ${cap(x.crime_type)}`, plain: plainCrime(x.crime_type), short: levelOf(x),
      text: `${levelOf(x)}${rangeOf(x) ? `; ${rangeOf(x)} expected` : ""}. Short, repeated beat visits to the stations named in its forecast.` });
    if (drops[0]) plan.push({ k: "dn", verb: kn ? "ಪರಿಶೀಲಿಸಿ" : "Check records", go: drops[0],
      title: `${drops[0].zone}: ${cap(drops[0].crime_type)}`, short: "Fewer reports than usual", text: "Far fewer reports than usual. Ask the station whether complaints are being registered before reading it as a fall in crime." });
    const ev = evsAhead.find((e) => e.in_forecast_window) || evsAhead[0];
    if (ev) {
      const up = (ev.rises || [])[0] || (ev.watch || [])[0];
      plan.push({ k: "ev", verb: kn ? "ಬಂದೋಬಸ್ತ್" : "Plan for event", toEvents: true, title: ev.name, short: ev.when,
        text: `${ev.when}.${up ? ` In past years ${cap(up.crime).toLowerCase()} ran ${up.percent}% higher during it.` : ""} Plan deployment for it.` });
    }
    if (!plan.length) plan.push({ k: "ok", verb: kn ? "ಸಾಮಾನ್ಯ" : "No change", title: "Every area is at its usual level", short: "Routine beats",
      text: "No area needs extra deployment this week. Routine beats as planned." });
  }

  // Alerts, with repeats grouped: the same area, crime and kind of signal is one alert,
  // however many times it was raised. Strongest first; six until the rest are asked for.
  const alertGroups = (() => {
    const by = new Map();
    alertList.forEach((a, i) => {
      const k = [a.zone, String(a.crime_type || "").toLowerCase(), a.anomaly_type || a.direction || ""].join("|");
      const g = by.get(k);
      if (g) g.count += 1; else by.set(k, { a, i, count: 1 });
    });
    return [...by.values()].sort((x, y) => (Number(y.a.z_score) || 0) - (Number(x.a.z_score) || 0));
  })();
  const shownAlerts = allAlerts ? alertGroups : alertGroups.slice(0, 6);

  const openItem = (it) => {
    const i = P.indexOf(it);
    if (i < 0) return;
    setFocusKind("prediction"); setSelected(i); setExplainOpen(true);
    setTimeout(() => reasonRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
  };
  // A forecast or an alert, picked: its explanation opens under the lists.
  const pick = (kind, i) => {
    setFocusKind(kind);
    if (kind === "alert") setSelAlert(i); else setSelected(i);
    setExplainOpen(true);
    setTimeout(() => reasonRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
  };
  const toPlan = () => planRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  const toForecast = () => forecastRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  const toAlerts = () => alertsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });

  const toEvents = () => eventsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  const toConfidence = () => { setRelOpen(true); setEngOpen(true); setTimeout(() => confRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 80); };
  const tr = eng && eng !== "missing" ? eng.track_record : null;
  const trackPct = tr?.coverage80 != null ? `${Math.round(tr.coverage80 * 100)}%` : null;

  // The forecast list, narrowed. Each entry keeps its place in the full board, because the
  // selection is an index into it.
  const needsAttention = (x) => x.risk === "HIGH" || x.direction === "silence" || (Number(x.z_score) || 0) >= 2 || (x.events || []).length > 0;
  const FILTERS = [
    ["attention", "Needs attention", needsAttention],
    ["high", "High risk", (x) => x.risk === "HIGH"],
    ["all", "All areas", () => true],
    ["above", "Above normal", (x) => x.direction !== "silence" && (Number(x.z_score) || 0) >= 2],
    ["drops", "Reporting drops", (x) => x.direction === "silence"],
    ["event", "Event this week", (x) => (x.events || []).length > 0],
    ["sure", "High confidence", (x) => x.confidence_level === "High"],
  ];
  useEffect(() => {
    if (predictions?.length && flt === "attention" && !predictions.some((x) => !isUnit(x) && needsAttention(x))) setFlt("all");
  }, [predictions]); // eslint-disable-line react-hooks/exhaustive-deps
  const needle = findArea.trim().toLowerCase();
  const passes = (FILTERS.find((f) => f[0] === flt) || FILTERS[0])[2];
  const shown = P.map((x, i) => ({ p: x, i })).filter(({ p: x }) => !isUnit(x) && passes(x) && (!needle || String(x.zone).toLowerCase().includes(needle) || cap(x.crime_type).toLowerCase().includes(needle)));

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
      {/* Hero: the first five seconds. What this is, who it is for, why it matters, and the
          one thing to do next, before any detail. */}
      <header className="px-hero">
        <div className="px-hero-main">
          <span className="px-eyebrow">{kn ? "7 ದಿನಗಳ ಅಪರಾಧ ಅಪಾಯ ಮುನ್ಸೂಚನೆ · ಠಾಣೆ ಮತ್ತು ಜಿಲ್ಲಾ ಅಧಿಕಾರಿಗಳಿಗೆ" : "7-Day Crime Risk Forecast · for station and district officers"}</span>
          <h1 className="px-title">
            {kn
              ? <>ಮುಂದಿನ 7 ದಿನಗಳಲ್ಲಿ ಅಪರಾಧ <em>ಎಲ್ಲಿ ಹೆಚ್ಚಾಗಬಹುದು.</em></>
              : <>Where crime is likely to <em>rise</em> in the next 7 days.</>}
          </h1>
          <p className="px-sub">
            {kn ? "ಪ್ರಕರಣಗಳು ಬರುವ ಮೊದಲೇ ಗಸ್ತು ಮತ್ತು ಬಂದೋಬಸ್ತ್ ಯೋಜಿಸಿ. ಪ್ರತಿ ಮುನ್ಸೂಚನೆಗೂ ನಿರೀಕ್ಷಿತ ವ್ಯಾಪ್ತಿ ಮತ್ತು ಅದನ್ನು ಲೆಕ್ಕ ಹಾಕಿದ FIR ಗಳು."
                : "Plan patrols and bandobast before the cases come in. Every forecast gives an expected range and the FIRs it was worked out from."}
          </p>
          <div className="px-hero-cta">
            <button type="button" className="ui-btn ui-btn--primary" onClick={toPlan}>
              {kn ? "ಈ ವಾರದ ಯೋಜನೆ ನೋಡಿ" : "See this week's plan"} <span aria-hidden="true">→</span>
            </button>
            {modelCard && (
              <button type="button" className="ui-btn ui-btn--ghost" onClick={() => {
                const btn = document.getElementById("cx-guide-trigger");
                if (btn) btn.click();
              }}>
                {kn ? "ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ" : "How it works"}
              </button>
            )}
          </div>
        </div>
        {/* provenance as one quiet line, not a row of pills */}
        <p className="px-meta">
          {boardMeta && <span>{kn ? "ಮೌಲ್ಯಮಾಪನ" : "Assessed"} <b>{dayOf(boardMeta.as_of)}</b></span>}
          {predictions?.length > 0 && <span><b>{A.length}</b> {kn ? "ವಲಯ" : "areas"}{unitCards.length ? <> · <b>{unitCards.length}</b> {kn ? "ಘಟಕ" : "statewide units"}</> : null}</span>}
          {trackPct && (
            // the forecast's own track record, up front: opens the details
            <button type="button" className="px-meta-btn" onClick={toConfidence}
                    title="How often the real count fell inside the forecast range, tested on past weeks of the real register">
              {kn ? "ದಾಖಲೆ" : "Range held in"} <b>{trackPct}</b> {kn ? "ವಾರಗಳಲ್ಲಿ" : "of tested weeks"}
            </button>
          )}
          {offlineSample && <span className="px-offline">{kn ? "ಆಫ್‌ಲೈನ್ · ಮಾದರಿ" : "Offline: sample data"}</span>}
        </p>
      </header>

      {/* The week in five figures: numbers on a rule, not five boxes. Each one takes the
          officer to it; a zero stays quiet. */}
      {predictions?.length > 0 && (() => {
        const nextEv = evsAhead[0];
        const stats = [
          { k: "hi", n: highs.length, l: kn ? "ಹೆಚ್ಚು ಅಪಾಯ" : "High-risk areas", hint: kn ? "ಮುಂದಿನ 7 ದಿನಗಳಿಗೆ ಹೆಚ್ಚು ಅಪಾಯ" : "Rated high risk for the week", go: () => { setFlt(highs.length ? "high" : "all"); toForecast(); } },
          { k: "up", n: aboves.length, l: kn ? "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು" : "Above normal", hint: kn ? "ಸಾಮಾನ್ಯ ಮಟ್ಟಕ್ಕಿಂತ ತುಂಬಾ ಹೆಚ್ಚು" : "Well above the area's usual level", go: () => { setFlt(aboves.length ? "above" : "all"); toForecast(); } },
          { k: "dn", n: drops.length, l: kn ? "ವರದಿ ಇಳಿಕೆ" : "Reporting drops", hint: kn ? "ದಾಖಲಾತಿ ಪರಿಶೀಲಿಸಿ" : "Far fewer reports: check registration", go: () => { setFlt(drops.length ? "drops" : "all"); toForecast(); } },
          { k: "al", n: alertGroups.length, l: kn ? "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು" : "Active alerts", hint: kn ? "ಸಾಮಾನ್ಯ ಮಾದರಿ ಮುರಿದ ಪ್ರಕರಣಗಳು" : "Cases that broke an area's pattern", go: toAlerts },
          { k: "ev", n: evsAhead.length, l: kn ? "ಮುಂಬರುವ ಉತ್ಸವ" : "Events in 3 weeks", hint: nextEv ? `${nextEv.name}, ${nextEv.when.toLowerCase()}` : (kn ? "ಮುಂಬರುವ ಉತ್ಸವ ಇಲ್ಲ" : "Nothing coming up"), go: toEvents },
        ];
        return (
          <div className="px-stats" role="list" aria-label={kn ? "ವಾರ ಒಂದು ನೋಟದಲ್ಲಿ" : "The week at a glance"}>
            {stats.map((t) => (
              <button type="button" role="listitem" key={t.k} className={`px-stat k-${t.k}${t.n ? "" : " zero"}`} onClick={t.go}>
                <b>{t.n}</b><span>{t.l}</span><em>{t.hint}</em>
              </button>
            ))}
          </div>
        );
      })()}

      {/* This week's plan: one line per action, opened for the detail */}
      <section className="px-plan" ref={planRef} aria-label="This week's plan">
        <div className="px-plan-hd">
          <div>
            <span className="ui-eyebrow">{kn ? "ಇಲ್ಲಿಂದ ಆರಂಭಿಸಿ" : "Start here"}</span>
            <h2><span className="px-secnum">01</span>{kn ? "ಈ ವಾರದ ಯೋಜನೆ" : "This week's plan"}{plan.length > 0 && <small>{Math.min(plan.length, 4)} {Math.min(plan.length, 4) === 1 ? "action" : "actions"}</small>}</h2>
          </div>
          <button type="button" className="ui-btn ui-btn--secondary" onClick={copyBrief} disabled={!brief.length}>
            {copied ? (kn ? "ನಕಲಿಸಲಾಗಿದೆ" : "Copied") : (kn ? "ಬ್ರೀಫಿಂಗ್ ಟಿಪ್ಪಣಿ ನಕಲಿಸಿ" : "Copy for the briefing note")}
          </button>
        </div>
        <p className="px-sec-note">{kn ? "ಈ ವಾರ ಮಾಡಬೇಕಾದದ್ದು, ಮುಖ್ಯವಾದದ್ದು ಮೊದಲು: ಎಲ್ಲಿ ಗಸ್ತು, ಯಾವ ಠಾಣೆ ಪರಿಶೀಲಿಸಬೇಕು, ಯಾವ ಉತ್ಸವಕ್ಕೆ ಯೋಜನೆ. ಕಾರಣ ಮತ್ತು ಠಾಣೆಗಳಿಗೆ ಸಾಲನ್ನು ತೆರೆಯಿರಿ."
          : "What to do this week, strongest first: where to patrol, which station to check, which event to plan for. Open a line for the reason and the stations."}</p>
        {predictions === null && <p className="px-brief-wait">{kn ? "ದಾಖಲೆಗಳನ್ನು ಓದುತ್ತಿದೆ…" : "Reading the records…"}</p>}
        {predictions?.length === 0 && <p className="px-brief-wait">{kn ? "ಸಕ್ರಿಯ ಮುನ್ಸೂಚನೆಗಳಿಲ್ಲ" : "There is nothing to forecast yet."}</p>}
        {plan.length > 0 && (
          <div className="px-plan-list">
            {plan.slice(0, 4).map((a, i) => {
              const open = planOpen === i;
              return (
                <div key={i} className={`px-act k-${a.k}${open ? " open" : ""}`} style={{ animationDelay: `${i * 60}ms` }}>
                  <button type="button" className="px-act-hd" aria-expanded={open} onClick={() => setPlanOpen(open ? null : i)}>
                    <span className="px-act-verb">{a.verb}</span>
                    <b title={a.plain || undefined}>{a.title}</b>
                    <span className="px-act-short">{a.short}</span>
                    <i aria-hidden="true" />
                  </button>
                  {open && (
                    <div className="px-act-body">
                      <p>{a.text}</p>
                      {(a.go || a.toEvents) && (
                        <button type="button" className="px-act-go ui-btn ui-btn--secondary ui-btn--sm" onClick={a.go ? () => openItem(a.go) : toEvents}>
                          {a.go ? (kn ? "ಕಾರಣ ಮತ್ತು ಠಾಣೆಗಳು" : "Why, and which stations") : (kn ? "ಹಿಂದಿನ ವರ್ಷಗಳು" : "What past years show")} →
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
        {(brief.length > 0 || reading) && (
          <details className="px-plan-more">
            <summary>{kn ? "ವಾರದ ಸಾರಾಂಶ" : "The whole week in brief"}</summary>
            <ul className="px-plan-brief">{brief.map((b, i) => <li key={i} className={`k-${b.k}`}>{b.t}</li>)}</ul>
            {reading && <p className="px-plan-ai"><span>{kn ? "ಅಂತರ್ ಓದು" : "Antar's reading"}</span>{reading}</p>}
          </details>
        )}
      </section>

      {/* The forecast, area by area, and the alerts behind it */}
      <div className="px-top">
        {/* 1 · Predict · Next 7 Days (scrollable) */}
        <div className="pxd-card" ref={forecastRef}>
          <div className="pxd-hd">
            <span className="pxd-ttl"><span className="px-secnum">02</span>{kn ? "ಮುನ್ಸೂಚನೆ · ಮುಂಬರುವ 7 ದಿನಗಳು" : "Forecast for the next 7 days"}</span>
            <span className="pxd-sub">{shown.length === A.length ? A.length : `${shown.length} of ${A.length}`} {kn ? "ವಲಯ" : "areas"}</span>
          </div>
          <p className="px-sec-note">{kn ? "ಪ್ರತಿ ಕಾರ್ಡ್ ಒಂದು ವಲಯ: ಅಲ್ಲಿ ಹೆಚ್ಚು ಬದಲಾಗಬಹುದಾದ ಅಪರಾಧ, ಸಾಮಾನ್ಯದಿಂದ ಎಷ್ಟು ದೂರ, ಮತ್ತು ಮುಂದಿನ 7 ದಿನಗಳ ನಿರೀಕ್ಷಿತ ಪ್ರಕರಣಗಳು. ಕಾರಣಕ್ಕಾಗಿ ಒಂದನ್ನು ಆರಿಸಿ."
            : "Each card is one area: the crime most likely to move, how far from normal, and the cases expected. Pick one for the reasons."}</p>
          <div className="px-flt" role="toolbar" aria-label="Narrow the forecast list">
            {FILTERS.map(([key, label, test]) => {
              const count = A.filter(test).length;
              return (
                <button type="button" key={key} className={flt === key ? "on" : ""} aria-pressed={flt === key}
                        disabled={key !== "all" && count === 0} onClick={() => setFlt(key)}>
                  {/* One highlight that slides between chips (it is the same element), so the
                      eye follows the choice instead of seeing one chip go out and another light. */}
                  {flt === key && <motion.span layoutId="px-flt-pill" className="px-flt-pill" transition={SPRING} />}
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
                className={`px-card ${explainOpen && focusKind === "prediction" && selected === i ? "on" : ""} ${acked.has(keyOf(p)) ? "acked" : ""}`}
                aria-pressed={explainOpen && focusKind === "prediction" && selected === i}
                onClick={() => pick("prediction", i)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick("prediction", i); } }}
              >
                {explainOpen && focusKind === "prediction" && selected === i && (
                  <motion.span layoutId="px-card-bar" className="px-card-bar" transition={SPRING} />
                )}
                <div className="px-card-top">
                  <span className="px-zone">{p.zone}</span>
                  <span className={`px-st s-${statusOf(p).k}`}>{statusOf(p).t}</span>
                </div>
                <div className="px-crime-row">
                  <CrimeName name={p.crime_type} className="px-crime" />
                  <button
                    type="button"
                    className="px-know"
                    onClick={(e) => { e.stopPropagation(); pick("prediction", i); setShowReasoning(true); }}
                    aria-label={`${kn ? "ತರ್ಕದಲ್ಲಿ ಇನ್ನಷ್ಟು ತಿಳಿಯಿರಿ" : "Why this forecast"} - ${p.zone}`}
                  >
                    {kn ? "ಏಕೆ?" : "Why?"}
                  </button>
                </div>
                <div className="px-say" title={p.z_score ? `Unusual-activity score ${p.z_score} (2 is unusual, 4 is rare)` : undefined}>
                  <b className={p.direction === "silence" ? "dn" : (Number(p.z_score) || 0) >= 2 ? "up" : ""}>{levelOf(p)}</b>
                  {rangeOf(p) ? <span>{kn ? "ನಿರೀಕ್ಷಿತ" : "Expected"} {rangeOf(p)}</span> : null}
                </div>
                {p.scenario && (
                  <div className="px-scn2">With {p.scenario.event}: <b>{num(p.scenario.lo)} to {num(p.scenario.hi)} cases</b> <i>estimate</i></div>
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
          {unitCards.length > 0 && (
            <div className="px-units" aria-label="Statewide police units">
              <span className="px-units-k" title="Units that register FIRs statewide under their own name. They are not areas, so they are not ranked with them or put in the plan.">
                {kn ? "ರಾಜ್ಯಮಟ್ಟದ ಘಟಕಗಳು" : "Statewide units"}
              </span>
              {unitCards.map(({ p, i }) => (
                <button type="button" key={p.zone} title={`${p.unit || UNIT_NAMES[p.zone]}: ${cap(p.crime_type)}, ${levelOf(p).toLowerCase()}`}
                        className={`${explainOpen && focusKind === "prediction" && selected === i ? "on" : ""} s-${statusOf(p).k}`}
                        onClick={() => pick("prediction", i)}>
                  <i aria-hidden="true" />{p.zone}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 3 · Active alerts (all, scrollable, clickable) */}
        <div className="pxd-card" ref={alertsRef}>
          <div className="pxd-hd pxd-hd2">
            <div>
              <span className="pxd-ttl"><span className="px-secnum">03</span>{kn ? "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು" : "Active alerts"} <i>{alertGroups.length}</i></span>
              <span className="pxd-note">{kn ? "ಸಾಮಾನ್ಯ ಮಾದರಿಯಿಂದ ಭಿನ್ನವಾದ ವಲಯಗಳು" : "Recent cases that broke from an area's usual pattern. Pick one to see why."}</span>
            </div>
          </div>
          <div className="pxd-scroll pxd-alerts">
            {alertList.length === 0 && <div className="pxd-empty">{kn ? "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆ ಇಲ್ಲ" : "No active alerts"}</div>}
            {shownAlerts.map(({ a, i, count }) => {
              const z = a.z_score ?? 0;
              const hi = z >= 4;
              // The label had three steps and the class only two, so every "Low" alert
              // was painted with the Medium style. Both come off the same test now.
              const sevlbl = hi ? "High" : z >= 2.5 ? "Medium" : "Low";
              const sev = hi ? "hi" : z >= 2.5 ? "md" : "lo";
              const on = explainOpen && focusKind === "alert" && selAlert === i;
              return (
                <div
                  key={i}
                  role="button"
                  tabIndex={0}
                  className={`pxd-alert ${on ? "on" : ""}`}
                  aria-pressed={on}
                  onClick={() => pick("alert", i)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick("alert", i); } }}
                >
                  <div className="pxd-alert-main">
                    <div className="pxd-alert-ttl">
                      <span><CrimeName name={a.crime_type} />{count > 1 && <small className="pxd-rep" title="Raised this many times">×{count}</small>}</span>
                      <span className={`pxd-sev ${sev}`}>{sevlbl}</span>
                    </div>
                    <div className="pxd-alert-sub" title={`Unusual-activity score ${Number(z).toFixed(2)} (2 is unusual, 4 is rare)`}>
                      {a.zone} · {a.anomaly_type ? (kn ? cap(a.anomaly_type) : (ALERT_KIND[a.anomaly_type] || cap(a.anomaly_type))) : a.direction === "silence" ? (kn ? "ವರದಿ ಮೌನ" : "Reporting drop") : (kn ? "ಅಸಂಗತಿ" : "Unusual activity")}
                      {z > 0 ? ` · ${levelOf(a).toLowerCase()}` : ` · ${kn ? "ಗಮನದಲ್ಲಿದೆ" : "on watch"}`}
                    </div>
                  </div>
                  <span className={`pxd-adot ${sev}`} />
                </div>
              );
            })}
            {alertGroups.length > 6 && (
              <button type="button" className="px-linkbtn pxd-more" onClick={() => setAllAlerts((v) => !v)}>
                {allAlerts ? "Show the strongest six" : `Show all ${alertGroups.length}`}
              </button>
            )}
          </div>
        </div>

      </div>

      {/* Why this forecast: opens when a forecast or an alert is picked, closes on request */}
      <AnimatePresence>
      {explainOpen && focusItem && (
      <motion.div key="explain" className="px-panel px-explain" ref={reasonRef} style={{ animation: "none" }}
        initial={{ opacity: 0, y: 14, filter: "blur(4px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        exit={{ opacity: 0, y: 14, filter: "blur(4px)" }} transition={SPRING}>
        <div className="px-panel-hd">
          <span>{kn ? "ಮುನ್ಸೂಚನೆ ವಿವರಣೆ" : "Why this forecast"}</span>
          <span className="px-hint">
            {focusKind === "alert" ? (kn ? "ಅಂತರ ಎಚ್ಚರಿಕೆಯಿಂದ" : "From an active alert") : (kn ? "ಮುಂದಿನ 7 ದಿನಗಳಿಂದ" : "From the 7-day forecast")}
            <button type="button" className="px-explain-x" onClick={() => { setExplainOpen(false); setShowReasoning(false); }}
                    aria-label={kn ? "ಮುಚ್ಚಿ" : "Close the explanation"}>{kn ? "ಮುಚ್ಚಿ" : "Close"} ×</button>
          </span>
        </div>

        <motion.div className="px-insp" key={`${focusKind}-${selected}`}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.22, ease: "easeOut" }}>
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
                  {plainCrime(focusItem.crime_type) && <p className="px-insp-plain">{cap(focusItem.crime_type)}: {plainCrime(focusItem.crime_type).toLowerCase()}.</p>}
                  <div className="px-insp-why">{generateNarrative(focusItem)}</div>

                  <div className="px-big">
                    {focusItem.confidence_level
                      ? <><span className={`n lv l-${focusItem.confidence_level}`}>{focusItem.confidence_level}</span><span className="nl">confidence</span></>
                      : <><span className="n">{pct(focusItem.confidence)}%</span><span className="nl">{kn ? "ವಿಶ್ವಾಸ" : "confident"}</span></>}
                    <span className={`px-risk ${RISK_BADGE[focusItem.risk] || ""}`}>{kn ? focusItem.risk?.toLowerCase() : (RISK_WORD[focusItem.risk] || focusItem.risk)}</span>
                    {Number(focusItem.z_score) > 0 && (
                      <span className="z" title="How far recent cases sit from this area's usual level. 2 is unusual, 4 is rare.">{kn ? "ಅಸಾಮಾನ್ಯತೆ ಅಂಕ" : "Unusual-activity score"} {focusItem.z_score}</span>
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
                      <div className="px-stn-hd">Stations to watch in {stations.scope || focusItem.zone}<i>estimate</i></div>
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
                    {isAcked
                      ? <span className="px-ackdone"> {kn ? "ಪರಿಶೀಲಿಸಲಾಗಿದೆ" : "Marked as reviewed"}</span>
                      : <button className="px-actbtn ack ui-btn ui-btn--primary" onClick={() => acknowledge(focusItem)}>{kn ? "ಸ್ವೀಕರಿಸಿ" : "Mark as reviewed"}</button>}
                    <button className="px-actbtn ask ui-btn ui-btn--secondary" onClick={() => askAntar(focusItem)}>
                      {kn ? "ಅಂತರ‍ಗೆ ಕೇಳಿ" : "Ask Antar"}
                    </button>
                    <span className="px-acts-sep" aria-hidden="true" />
                    <button className={`px-actbtn ui-btn ui-btn--ghost ui-btn--sm ${showReasoning ? "on" : ""}`} aria-expanded={showReasoning} onClick={() => setShowReasoning((v) => !v)}>
                      {kn ? "ತರ್ಕ" : "How this was worked out"} {showReasoning ? "▾" : "▸"}
                    </button>
                    <button className={`px-actbtn ui-btn ui-btn--ghost ui-btn--sm ${showScenario ? "on" : ""}`} aria-expanded={showScenario} onClick={() => setShowScenario((v) => !v)}>
                      {kn ? "ಸನ್ನಿವೇಶ" : "What if"} {showScenario ? "▾" : "▸"}
                    </button>
                    <button className="px-actbtn ui-btn ui-btn--ghost ui-btn--sm" onClick={() => openDerivationModal(focusItem.id || focusItem.zone || "HYP-101")}>
                      {loadingDerivation ? "…" : (kn ? "ಡೆರಿವೇಷನ್ ಆಡಿಟ್" : "Audit trail")}
                    </button>
                    <button className="px-actbtn ui-btn ui-btn--ghost ui-btn--sm" onClick={() => router.push(`/map?zone=${encodeURIComponent(focusItem.zone)}&crime_type=${focusItem.crime_type}`)}>
                      {kn ? "ನಕ್ಷೆ" : "Open on map"}
                    </button>
                  </div>

                  {showScenario && (
                    scenarioBand?.scenario ? (
                      <div className="px-scn">
                        <div className="px-scn-row">
                          <span className="px-scn-badge">{cap(scenarioBand.scenario.badge === "inferred" || !scenarioBand.scenario.badge ? "Estimate" : scenarioBand.scenario.badge)} · {kn ? "ಸನ್ನಿವೇಶ ಬ್ಯಾಂಡ್" : "scenario range"}</span>
                          <span className="px-scn-val">{scenarioBand.scenario.lo}–{scenarioBand.scenario.hi} {kn ? "ಘಟನೆಗಳು" : "incidents"}</span>
                          <span className="px-scn-base">({kn ? "ಸಾಮಾನ್ಯ ವ್ಯಾಪ್ತಿ" : "usual range"} {scenarioBand.baseline?.lo}–{scenarioBand.baseline?.hi})</span>
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
              <AnimatePresence initial={false}>
              {showReasoning && (
                <motion.div key="reason" className="px-reason" style={{ overflow: "hidden" }}
                  initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }} transition={SPRING}>
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
                </motion.div>
              )}
              </AnimatePresence>
            </>
          )}
        </motion.div>
      </motion.div>
      )}
      </AnimatePresence>

      {/* Events ahead, then the investigation leads and how far to trust the forecast */}
      {/* Events ahead: when each falls, and what the real register shows it did before */}
      {eng && eng !== "missing" && (
        <section className="px-evs" ref={eventsRef} aria-label="Events ahead">
          <div className="px-evs-hd">
            <h2><span className="px-secnum">04</span>{kn ? "ಮುಂಬರುವ ಉತ್ಸವಗಳು · ಬಂದೋಬಸ್ತ್" : "Events ahead"}</h2>
            <span>{kn ? "ಹಿಂದಿನ ವರ್ಷಗಳ FIR ಗಳಿಂದ ಅಳೆದದ್ದು." : "Festivals and events in the next 3 weeks, and what each did to registered cases in past years. Measured from FIRs, for bandobast planning."}</span>
          </div>
          {evsAhead.length === 0 && <p className="px-evs-none">No listed event falls in the next 3 weeks.</p>}
          {evsAhead.map((e) => (
            <EventCard key={e.key} ev={e} kn={kn} areas={P.filter((x) => (e.places || []).includes(x.zone)).slice(0, 4)} onOpen={openItem}
                       onAsk={(q) => { try { sessionStorage.setItem("antar_initial_question", q); localStorage.setItem("antar_initial_question", q); } catch {} router.push("/antar"); }} />
          ))}
        </section>
      )}

      {/* Investigation leads: person-level, so they open only when asked for */}
      <details className="px-fold">
        <summary>
          <b>{kn ? "ತನಿಖಾ ಸುಳಿವುಗಳು" : "Investigation leads"}{fZone ? ` · ${fZone}` : ""}</b>
          <span>{kn ? "ಆರೋಪಿಗಳ ಸಂಪರ್ಕ ಮತ್ತು ಹಂಚಿದ ವಾಹನ, ಫೋನ್, UPI. ಕೇಳಿದಾಗ ಮಾತ್ರ." : "Links between accused, and FIRs that share a vehicle, phone or UPI id. For the investigating officer; opens on request."}</span>
        </summary>
      <section className="px-hyp" aria-label="Possible links between accused">
        <header>
          <div>
            <h3>{kn ? "ಆರೋಪಿಗಳ ನಡುವಿನ ಸಾಧ್ಯ ಸಂಪರ್ಕಗಳು" : "Possible links between accused"}{fZone ? ` · ${fZone}` : ""}</h3>
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
        {runningHypotheses && <p className="px-hyp-empty">Comparing accused in {fZone} and checking how often each link would turn up by chance…</p>}
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
              <p className="px-hyp-foot">A possible link is a lead, never a finding. It is scored from what the accused share in the record, then checked against how often such a link turns up by chance. No AI model is used in either step.</p>
            </>
          );
        })()}
      </section>

      <CaseLeads zone={fZone} />
      </details>

      {/* How far to trust the forecast: one line until it is opened */}
      <details className="px-fold" open={relOpen} onToggle={(e) => setRelOpen(e.currentTarget.open)}>
        <summary>
          <b>{kn ? "ಈ ಮುನ್ಸೂಚನೆ ಎಷ್ಟು ವಿಶ್ವಾಸಾರ್ಹ" : "How reliable is this forecast"}</b>
          <span>
            {trackPct ? `The real count fell inside the forecast range in ${trackPct} of ${tr.weeks} tested weeks. ` : ""}
            {eng && eng !== "missing" && eng.confidence?.level ? `Engine confidence: ${eng.confidence.level}.` : ""}
            {" "}What it is built on, its record, and the festival calendar.
          </span>
        </summary>
        <EngineConfidence eng={eng} open={engOpen} onToggle={() => setEngOpen((v) => !v)} anchor={confRef} />
        <div className="px-built">
          <KnownData eng={eng} />
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
      </details>

      <PlanPresence>{planFor && <ShiftPlan key={planFor} station={planFor} kn={kn} onClose={() => setPlanFor(null)} />}</PlanPresence>

      <div className="px-footer">
        {engine ? `${engine} · ` : ""}
        {kn ? "ನಿರ್ಧಾರ-ಬೆಂಬಲ ಮಾತ್ರ · ತೀರ್ಪು ಅಲ್ಲ · ಅಧಿಕಾರಿ ತೀರ್ಮಾನ ಕಡ್ಡಾಯ" : "Decision support only. Not a verdict. The officer decides."}
      </div>

      {/* Model card modal - real /model-card */}
      <AnimatePresence>
      {showCard && modelCard && (
        <MaterialBackdrop key="model-card" className="px-cardback px-center" onClick={() => setShowCard(false)}>
          <MaterialPanel className="px-modelcard px-modelcard-m" role="dialog" aria-label="Model card" onClick={(e) => e.stopPropagation()}>
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
          </MaterialPanel>
        </MaterialBackdrop>
      )}
      </AnimatePresence>

      {/* Derivation & audit modal - real /api/derivation */}
      <AnimatePresence>
      {derivationModalData && (
        <MaterialBackdrop key="derivation" className="px-cardback px-center" onClick={() => setDerivationModalData(null)}>
          <MaterialPanel className="px-modelcard px-modelcard-m" role="dialog" aria-label="Derivation & Audit Inspector" style={{ maxWidth: "680px", width: "92%" }} onClick={(e) => e.stopPropagation()}>
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
                     {kn ? "ಖಚಿತಪಡಿಸಿ" : "Confirm link"}
                  </button>
                  <button onClick={() => handleHypothesisAction(derivationModalData.product_id, "reject")}
                    style={{ background: "rgba(225,64,56,0.14)", color: "#E14038", border: "1px solid rgba(225,64,56,0.5)", padding: "6px 12px", borderRadius: "7px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>
                     {kn ? "ತಿರಸ್ಕರಿಸಿ" : "Reject link"}
                  </button>
                </div>
              </div>
            </div>
          </MaterialPanel>
        </MaterialBackdrop>
      )}
      </AnimatePresence>

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


