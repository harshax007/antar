"use client";

import { useEffect, useState, useRef } from "react";
import { Download, RefreshCw, X, Play, FileText, Maximize2, Minimize2, Copy, Check, FileSpreadsheet, Radio, ShieldCheck, Activity, Square, ArrowUpRight, CornerDownRight, Sparkles, HelpCircle, AlertTriangle, Link2, Fingerprint, ShieldAlert, UserX, Hourglass, MapPin, Route, CalendarClock, Calendar, Layers, BarChart3, ChevronDown } from "lucide-react";
import { getActiveOfficerId } from "@/components/OfficerSelector";
import { openReport } from "@/lib/auth";
import { fetchAPI } from "@/lib/api";
import WorkspaceAgents, { FACE, agentsUsed } from "@/components/WorkspaceAgents";
import { useRouter } from "next/navigation";
import Link from "next/link";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

function stripTags(t) {
  return String(t || "").replace(/^\[(?:VERIFIED|COMPUTED|INFERRED|GAP|K|D|I|U)\]\s*/i, "");
}

// Labels read as sentences, not shouted. ("NETWORK_DEEP" -> "Network deep")
function sentence(t) {
  const s = String(t || "").trim().toLowerCase();
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

const CLASS_HELP = {
  K: "Known - read directly from a record",
  D: "Derived - calculated from records",
  I: "Inferred - a judgment, with its basis",
  U: "Unknown - data absent or unrecorded",
};

// The evidence class in words an officer reads at a glance, instead of a letter and a key.
const CLASS_WORD = {
  K: ["From records", "ದಾಖಲೆಯಿಂದ"],
  D: ["Calculated", "ಲೆಕ್ಕಾಚಾರ"],
  I: ["Estimate", "ಅಂದಾಜು"],
  U: ["Not on record", "ದಾಖಲೆಯಲ್ಲಿಲ್ಲ"],
};
function ClassTag({ c, kn }) {
  if (!CLASS_WORD[c]) return null;
  return <span className={`c2-tag c2-tag-${c}`} title={CLASS_HELP[c]}>{CLASS_WORD[c][kn ? 1 : 0]}</span>;
}

// "How sure is this?" in one sentence, from the evidence classes the pipeline reported for
// THIS answer. Nothing is scored here: it only says what kind of evidence the answer rests on.
const SURE = {
  K: ["High: read straight from the FIR records. Open a cited FIR to confirm.",
      "ಹೆಚ್ಚು: FIR ದಾಖಲೆಗಳಿಂದ ನೇರವಾಗಿ. ಖಚಿತಪಡಿಸಲು ಉಲ್ಲೇಖಿತ FIR ತೆರೆಯಿರಿ."],
  D: ["Good: calculated from the FIR records. Spot-check a few cited FIRs before relying on it.",
      "ಉತ್ತಮ: FIR ದಾಖಲೆಗಳಿಂದ ಲೆಕ್ಕ ಹಾಕಿದ್ದು. ಬಳಸುವ ಮೊದಲು ಕೆಲವು FIR ಪರಿಶೀಲಿಸಿ."],
  I: ["Low: an estimate. Treat it as a lead, not as evidence.",
      "ಕಡಿಮೆ: ಅಂದಾಜು. ಇದನ್ನು ಸುಳಿವಾಗಿ ಬಳಸಿ, ಸಾಕ್ಷ್ಯವಾಗಿ ಅಲ್ಲ."],
  U: ["None: the records do not hold this. Do not act on it.",
      "ಇಲ್ಲ: ದಾಖಲೆಗಳಲ್ಲಿ ಇದು ಇಲ್ಲ. ಇದರ ಮೇಲೆ ಕ್ರಮ ಬೇಡ."],
};
function howSure(evidenceClass, claims, kn) {
  const tags = (claims || []).map((c) => c.tag).filter((t) => SURE[t]);
  const kinds = [...new Set(tags)];
  if (kinds.length > 1) {
    const n = (t) => tags.filter((x) => x === t).length;
    const parts = ["K", "D", "I", "U"].filter((t) => n(t)).map((t) => `${n(t)} ${CLASS_WORD[t][kn ? 1 : 0].toLowerCase()}`);
    const weakest = ["U", "I", "D", "K"].find((t) => n(t));
    return {
      cls: weakest,
      text: kn ? `ಮಿಶ್ರ: ${parts.join(", ")}. ಕ್ರಮಕ್ಕೆ ಮೊದಲು ಅಂದಾಜುಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.`
              : `Mixed: ${parts.join(", ")}. Check anything marked estimate before acting on it.`,
    };
  }
  const c = evidenceClass || kinds[0];
  return SURE[c] ? { cls: c, text: SURE[c][kn ? 1 : 0] } : null;
}

const plainText = (t) => stripTags(t).replace(/\*\*/g, "").replace(/`/g, "").trim();
const sameText = (a, b) => plainText(a).replace(/\s+/g, " ").toLowerCase() === plainText(b).replace(/\s+/g, " ").toLowerCase();

// Every shape of FIR id in the register (the chat uses the same list): an id written in the
// brief opens that case's timeline.
const FIR_ID_RE = /\b(K\d{7}|C\d{5,8}|SYN-[a-f0-9]{12}|SYN-20\d\d-\d{3,8}|(?:BG|HIST|FWD)-20\d\d-\d{3,8}|FIR-20\d\d-[\w-]{4,40})\b/g;

const XW_HILITE = /(\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?%|\bFIR[-\s]?\d[\w-]*|\b\d{4}\b|\b\d{2,}\b)/g;

function XwInline({ text }) {
  const str = String(text ?? "");
  if (FIR_ID_RE.test(str)) {
    FIR_ID_RE.lastIndex = 0;
    const out = [];
    let last = 0;
    for (const m of str.matchAll(FIR_ID_RE)) {
      if (m.index > last) out.push(<XwInline key={`t${last}`} text={str.slice(last, m.index)} />);
      out.push(<Link key={`f${m.index}`} href={`/case?id=${encodeURIComponent(m[1])}`} className="c2-firlink" title="Open the case timeline">{m[1]}</Link>);
      last = m.index + m[0].length;
    }
    if (last < str.length) out.push(<XwInline key={`t${last}`} text={str.slice(last)} />);
    return out;
  }
  FIR_ID_RE.lastIndex = 0;
  const parts = str.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    const b = p.match(/^\*\*([^*]+)\*\*$/);
    if (b) return <b key={i} className="xw-strong">{b[1]}</b>;
    const c = p.match(/^`([^`]+)`$/);
    if (c) return <code key={i} className="xw-code">{c[1]}</code>;
    const clean = p.replace(/\*\*/g, "").replace(/(^|\s)\*(\S)/g, "$1$2").replace(/(\S)\*(\s|$)/g, "$1$2");
    return clean.split(XW_HILITE).map((s, k) =>
      k % 2 === 1
        ? <span key={`${i}-${k}`} className="xw-hl">{s}</span>
        : <span key={`${i}-${k}`}>{s}</span>
    );
  });
}

function parseAnswer(text) {
  if (!text) return { summary: "", trend: null, ranking: [], rest: [], rankCaption: "" };
  const lines = String(text).split('\n').map(l => l.trim()).filter(Boolean);

  let summary = "";
  let trend = null;
  const ranking = [];
  const rest = [];
  // The line that introduces the ranked list ("Most common crime types:"). It used to be
  // left behind in Detail while its list moved into the RANKING table, so the brief showed
  // a heading with nothing under it and a table with no title.
  let rankCaption = "";

  if (lines.length > 0) summary = stripTags(lines[0]);

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    const trendMatch = line.match(/^(?:Direction|Trend):\s*(.*)/i);
    if (trendMatch) {
      trend = stripTags(trendMatch[1]);
      continue;
    }
    
    // Ranked lists from answer_writer: "1. Bengaluru City - 42,701 (86%)"
    const rankMatch = line.match(/^\d+\.\s+(.*?)(?:\s+(?:—|-|:)\s+)([\d,]+)(?:\s*(?:FIRs|cases)?)?(?:\s*\((.*?)\))?$/i);
    if (rankMatch) {
      // The immediately preceding plain line is this list's caption, not loose detail.
      if (ranking.length === 0 && rest.length > 0) {
        const prev = rest[rest.length - 1];
        if ((prev.type === "text" || prev.type === "heading") && /[:：]\s*$/.test(prev.text)) {
          rankCaption = prev.text.replace(/[:：]\s*$/, "");
          rest.pop();
        }
      }
      ranking.push({ name: stripTags(rankMatch[1]), n: rankMatch[2], pct: rankMatch[3] || "" });
    } else {
      const heading = line.match(/^#{1,6}\s+(.*)/);
      if (heading) {
        rest.push({ type: "heading", text: stripTags(heading[1]) });
      } else {
        const bullet = line.match(/^([•\-*]|\d+\.)\s+(.*)/);
        if (bullet) {
          rest.push({ type: "bullet", text: stripTags(bullet[2] || bullet[1]) });
        } else {
          rest.push({ type: "text", text: stripTags(line) });
        }
      }
    }
  }
  return { summary, trend, ranking, rest, rankCaption };
}

// Insights are DERIVED from the ranked rows in front of us - concentration, the gap to
// second place, the length of the tail. Arithmetic only: nothing here is generated, so
// nothing here can be wrong in a way the officer cannot check against the table.
function deriveInsights(ranking, kn) {
  const rows = ranking.map((r) => ({ name: r.name, n: Number(String(r.n).replace(/,/g, "")) })).filter((r) => Number.isFinite(r.n));
  if (rows.length < 2) return [];
  const total = rows.reduce((a, r) => a + r.n, 0);
  if (!total) return [];
  const pct = (n) => Math.round((n / total) * 100);
  const fmt = (n) => n.toLocaleString("en-IN");
  const [a, b] = rows;
  const out = [];
  out.push(kn
    ? `**${a.name}** ಅತಿ ಹೆಚ್ಚು: ${fmt(a.n)}, ತೋರಿಸಿದ ಒಟ್ಟು ${fmt(total)} ರಲ್ಲಿ **${pct(a.n)}%**.`
    : `**${a.name}** is the largest: ${fmt(a.n)} of the ${fmt(total)} shown (**${pct(a.n)}%**).`);
  if (a.n > b.n) {
    const x = b.n ? a.n / b.n : 0;
    out.push(kn
      ? `ಎರಡನೆಯ ${b.name} ಗಿಂತ **${fmt(a.n - b.n)}** ಹೆಚ್ಚು${x >= 1.2 ? ` (${x.toFixed(1)}×)` : ""}.`
      : `${fmt(a.n - b.n)} more than the next, ${b.name}${x >= 1.2 ? ` (**${x.toFixed(1)}×**)` : ""}.`);
  }
  if (rows.length >= 4) {
    const top3 = pct(a.n + b.n + rows[2].n);
    out.push(kn
      ? `ಮೊದಲ ಮೂರು **${top3}%**; ಉಳಿದ ${rows.length - 3} ಸೇರಿ ${100 - top3}%.`
      : `The top three make up **${top3}%**; the other ${rows.length - 3} share ${100 - top3}%.`);
  }
  const last = rows[rows.length - 1];
  if (rows.length >= 3 && last.n > 0) out.push(kn
    ? `ಕಡಿಮೆ: ${last.name}, ${fmt(last.n)} (${pct(last.n)}%).`
    : `Smallest shown: ${last.name}, ${fmt(last.n)} (${pct(last.n)}%).`);
  return out;
}

// ── Antar insights ──────────────────────────────────────────────────────────
// What the FIRs behind this answer have in common, computed on the server from the FIRs
// the answer's AUDIT ENTRY cites (GET /api/answer-record/{hash}/insights): shared accused,
// vehicles or payment ids, a repeated method, child victims, arrests not yet made, cases
// stuck against the state rate, a station, beat or weekday that recurs. Arithmetic over
// rows, never generated, and every insight opens the FIRs it rests on.
const INSIGHT_ICON = {
  shared: Link2, method: Fingerprint, victims: ShieldAlert, arrests: UserX, progress: Hourglass,
  place: MapPin, beat: Route, timing: CalendarClock, span: Calendar, mix: Layers, ranking: BarChart3,
};
const INSIGHT_TONE = { shared: "lead", method: "lead", victims: "alert", arrests: "alert", progress: "alert" };

function InsightRow({ it, kn }) {
  const [open, setOpen] = useState(false);
  const Icon = INSIGHT_ICON[it.kind] || Sparkles;
  const firs = it.firs || [];
  return (
    <li className={`c2-ins c2-ins-${INSIGHT_TONE[it.kind] || "note"}`}>
      <span className="c2-ins-ic" aria-hidden="true"><Icon size={12} /></span>
      <div className="c2-ins-b">
        {it.title && <b>{it.title}</b>}
        <p title={CLASS_HELP[it.cls]}>{it.kind === "ranking"
          ? it.text.split(/\*\*([^*]+)\*\*/g).map((t, i) => (i % 2 ? <strong key={i}>{t}</strong> : t))
          : <XwInline text={it.text} />}</p>
        {firs.length > 0 && (
        <div className="c2-ins-f">
          {(
            <button type="button" className="c2-ins-more" aria-expanded={open} onClick={() => setOpen(!open)}>
              {kn ? `${firs.length} FIR ತೋರಿಸಿ` : `${open ? "Hide" : "Show"} ${firs.length} ${firs.length === 1 ? "FIR" : "FIRs"}`}
              <ChevronDown size={12} aria-hidden="true" style={{ transform: open ? "rotate(180deg)" : "none" }} />
            </button>
          )}
        </div>
        )}
        {open && (
          <div className="c2-ins-firs">
            {firs.map((f) => (
              <Link key={f} href={`/case?id=${encodeURIComponent(f)}`} className="c2-firlink" title={kn ? "ಪ್ರಕರಣದ ಕಾಲರೇಖೆ ತೆರೆಯಿರಿ" : "Open the case timeline"}>{f}</Link>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

function AntarInsights({ state, extra, kn }) {
  const items = [...(state.data?.items || []), ...extra];
  const loading = state.status === "loading";
  return (
    <div className="c2-block c2-insblk" id="xw-insights">
      <div className="c2-block-t">
        <span className="c2-ins-h"><Sparkles size={13} aria-hidden="true" /> {kn ? "ಅಂತರ್ ಒಳನೋಟಗಳು" : "Antar insights"}</span>
        <span className="c2-ins-src">{kn ? "ಲೆಕ್ಕ ಹಾಕಿದ್ದು, ಉತ್ಪಾದಿಸಿದ್ದಲ್ಲ" : "Calculated, not generated"}</span>
      </div>
      {loading && (
        <ul className="c2-ins-list" aria-busy="true">
          {[0, 1, 2].map((i) => <li key={i} className="c2-ins c2-ins-skel"><span /><div><i /><i /></div></li>)}
        </ul>
      )}
      {!loading && items.length > 0 && (
        <ul className="c2-ins-list">
          {items.map((it, i) => <InsightRow key={`${it.kind}-${i}`} it={it} kn={kn} />)}
        </ul>
      )}
      {!loading && items.length === 0 && (
        <p className="c2-ins-empty">
          {state.status === "err" ? state.error
            : state.data?.note || (kn ? "ಈ ಉತ್ತರಕ್ಕೆ ಒಳನೋಟಗಳಿಲ್ಲ." : "Nothing stands out in the records behind this answer.")}
        </p>
      )}
      {!loading && items.length > 0 && (
        <div className="c2-srcnote">
          {state.data?.note || (kn ? "ಮೇಲಿನ ಕೋಷ್ಟಕದಿಂದ ಲೆಕ್ಕ ಹಾಕಿದ್ದು." : "Calculated from the ranked rows in this answer.")}
          {" "}{kn ? "ಇವು ಸುಳಿವುಗಳು, ತೀರ್ಮಾನಗಳಲ್ಲ." : "These are leads to check, not findings."}
        </div>
      )}
    </div>
  );
}

// Long-running work an officer can hand off without blocking the chat. Each maps to a
// real job type in app/api/jobs.py; the evidence class says how far to trust the output.
const BG_TASKS = [
  { type: "osint_recon", en: "Open-web search", kn: "ಮುಕ್ತ ಜಾಲ ಹುಡುಕಾಟ", cls: "I", needsTarget: true,
    hintEn: "Leads from the public internet on a person, phone, social-media handle or place. Not verified: check before use.",
    hintKn: "ವ್ಯಕ್ತಿ, ಫೋನ್, ಹ್ಯಾಂಡಲ್ ಅಥವಾ ಸ್ಥಳದ ಬಗ್ಗೆ ಮುಕ್ತ-ಜಾಲ ಸುಳಿವುಗಳು. ಪರಿಶೀಲಿಸದವು." },
  { type: "ml_forecast", en: "7-day forecast", kn: "7 ದಿನಗಳ ಮುನ್ಸೂಚನೆ", cls: "I", needsTarget: false,
    hintEn: "Likely cases in the next 7 days, with a likely and a wider range. Leave the target blank for the whole state, or name a district.",
    hintKn: "ಮುಂದಿನ 7 ದಿನಗಳ ಸಂಭಾವ್ಯ ಪ್ರಕರಣಗಳು, ಸಂಭಾವ್ಯ ಮತ್ತು ವಿಶಾಲ ವ್ಯಾಪ್ತಿಯೊಂದಿಗೆ. ಇಡೀ ರಾಜ್ಯಕ್ಕೆ ಖಾಲಿ ಬಿಡಿ, ಅಥವಾ ಜಿಲ್ಲೆ ನಮೂದಿಸಿ." },
  { type: "deep_research", en: "Deep research", kn: "ಆಳವಾದ ಸಂಶೋಧನೆ", cls: "D", needsTarget: true,
    hintEn: "A full profile of a suspect or area, with each point marked as from the records, calculated, estimated or not on record.",
    hintKn: "ಶಂಕಿತ ಅಥವಾ ವಲಯದ ಸಂಪೂರ್ಣ ವಿವರ, ಪ್ರತಿ ಅಂಶದ ಮೂಲದೊಂದಿಗೆ." },
  { type: "network_deep", en: "Map associates", kn: "ಜಾಲ ವಿಶ್ಲೇಷಣೆ", cls: "D", needsTarget: true,
    hintEn: "Associates and links around a suspect id or name.", hintKn: "ಶಂಕಿತರ ಸುತ್ತಲಿನ ಸಹಚರರು ಮತ್ತು ಕೊಂಡಿಗಳು." },
  { type: "pattern_scan", en: "Find repeat patterns", kn: "ಮಾದರಿ ಶೋಧ", cls: "D", needsTarget: false,
    hintEn: "The same way of committing a crime, repeated across an area or crime type.", hintKn: "ವಲಯ ಅಥವಾ ಅಪರಾಧ ಪ್ರಕಾರದಲ್ಲಿ ಪುನರಾವರ್ತಿತ ಅಪರಾಧ ವಿಧಾನ." },
  { type: "threat_assessment", en: "Patrol advice", kn: "ಬೆದರಿಕೆ ಮೌಲ್ಯಮಾಪನ", cls: "I", needsTarget: false,
    hintEn: "Patrol and checkpoint recommendations for a zone.", hintKn: "ವಲಯಕ್ಕೆ ಗಸ್ತು ಮತ್ತು ತಪಾಸಣಾ ಶಿಫಾರಸುಗಳು." },
  { type: "custom", en: "Custom task", kn: "ಕಸ್ಟಮ್ ಕಾರ್ಯ", cls: "D", needsTarget: false,
    hintEn: "Any question, answered from the records in the background.",
    hintKn: "ಯಾವುದೇ ಪ್ರಶ್ನೆ, ಪರಿಶೀಲಿತ ಮಾರ್ಗದಲ್ಲಿ ಹಿನ್ನೆಲೆಯಲ್ಲಿ." },
];

// A finished job, readable first: a ranked table when the result is a list (forecast
// units, patterns, claims), headline counts for a graph, and the raw data one click away.
const JobResultViewer = ({ data, kn }) => {
  const [raw, setRaw] = useState(false);
  if (!data) return null;
  const list = Array.isArray(data.items) ? data.items
    : Array.isArray(data.claims) ? data.claims
    : Array.isArray(data.patterns) ? data.patterns
    : Array.isArray(data.suggestions) ? data.suggestions : null;
  const label = (r) => r?.name || r?.claim || r?.title || r?.label || r?.signature || r?.zone || r?.text || "";
  const value = (r) => r?.expected ?? r?.count ?? r?.score ?? r?.confidence ?? "";
  return (
    <div className="c2-jobres">
      {data.bottom_line && <p className="c2-jobres-bl">{data.bottom_line}</p>}
      {Array.isArray(data.nodes) && (
        <p className="c2-jobres-bl">{data.nodes.length} {kn ? "ನೋಡ್‌ಗಳು" : "nodes"} · {(data.edges || []).length} {kn ? "ಕೊಂಡಿಗಳು" : "links"}</p>
      )}
      {list && list.length > 0 && (
        <table className="xw-table c2-table">
          <tbody>
            {list.slice(0, 15).map((r, i) => (
              <tr key={i}>
                <td>{String(i + 1).padStart(2, "0")}</td>
                <td>{typeof r === "string" ? r : label(r)}{r?.district ? ` · ${r.district}` : ""}</td>
                <td style={{ textAlign: "right" }}>{typeof r === "string" ? "" : String(value(r))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <button className="c2-mini" onClick={() => setRaw(!raw)}>{raw ? (kn ? "ಮರೆಮಾಡಿ" : "Hide raw data") : (kn ? "ಕಚ್ಚಾ ಡೇಟಾ" : "Show raw data")}</button>
      {raw && (
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#cbd5e1" }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
};

export default function ExpertWorkspace({ answer, question, citations = [], suspects = [], sessionId, kn, onClose, meta, trace = [], claims = [], evidenceClass = null, suggested = [], onAsk = null }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [showEditDisclaimer, setShowEditDisclaimer] = useState(false);
  const [draft, setDraft] = useState("");
  const [published, setPublished] = useState(false);
  const [newNote, setNewNote] = useState("");
  const [workspaceData, setWorkspaceData] = useState(null);
  const [activeTab, setActiveTab] = useState("document");
  const [jobsExpanded, setJobsExpanded] = useState(false);

  useEffect(() => { 
    setDraft(String(answer || "")); 
    setPublished(false); 
    setEditing(false); 
    setShowEditDisclaimer(false);
  }, [answer]);

  // ── Resizability ────────────────────────────────────────────────────────
  // The console used to be a fixed 620px overlay on top of the chat, so the conversation
  // ran underneath it and the officer's own question was clipped at the seam. It now
  // docks: it opens at an exact half of the viewport, publishes its width as --xw-w, and
  // the chat column reflows into the other half. Drag to resize; double-click the edge
  // to return to an even split.
  const half = () => (typeof window === "undefined" ? 720 : Math.round(window.innerWidth / 2));
  const [width, setWidth] = useState(half);
  const [isResizing, setIsResizing] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const userSized = useRef(false);
  const dockWidth = useRef(null);            // last docked width, kept while expanded

  useEffect(() => {
    const saved = parseInt(localStorage.getItem("antar_xw_w2") || "", 10);
    if (saved >= 320) { userSized.current = true; setWidth(saved); }
    else setWidth(half());
    const onResize = () => { if (!userSized.current) setWidth(half()); };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // The chat reads the DOCKED width. While expanded the console overlays instead, so the
  // conversation keeps its layout rather than collapsing to a 64px strip.
  useEffect(() => {
    if (!expanded) dockWidth.current = width;
    const root = document.documentElement;
    root.style.setProperty("--xw-w", `${dockWidth.current ?? width}px`);
    root.dataset.xw = "1";
  }, [width, expanded]);
  useEffect(() => () => {
    document.documentElement.style.removeProperty("--xw-w");
    delete document.documentElement.dataset.xw;
  }, []);

  const resetSplit = () => {
    userSized.current = false;
    try { localStorage.removeItem("antar_xw_w2"); } catch {}
    setExpanded(false);
    setWidth(half());
  };

  const toggleExpand = () => {
    if (expanded) {
      setWidth(dockWidth.current ?? half());
      setExpanded(false);
    } else {
      setWidth(window.innerWidth - 64);
      setExpanded(true);
    }
  };

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e) => {
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth >= 320 && newWidth <= window.innerWidth - 320) {
        userSized.current = true;
        setWidth(newWidth);
        localStorage.setItem("antar_xw_w2", newWidth);
      }
    };
    const handleMouseUp = () => setIsResizing(false);
    
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
    document.addEventListener("pointermove", handleMouseMove);
    document.addEventListener("pointerup", handleMouseUp);
    return () => {
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      document.removeEventListener("pointermove", handleMouseMove);
      document.removeEventListener("pointerup", handleMouseUp);
    };
  }, [isResizing]);

  useEffect(() => {
    document.documentElement.style.setProperty('--xw-width', `${width}px`);
    return () => document.documentElement.style.removeProperty('--xw-width');
  }, [width]);

  // ── Jobs & Workspace ──────────────────────────────────────────────────────
  const [jobs, setJobs] = useState([]);
  // Link health is derived from the real 2.5 s poll below, not decoration: a failed or
  // stale poll turns the LINK indicator amber/red so the officer knows the queue is not live.
  const [linkOk, setLinkOk] = useState(null);
  const [lastSync, setLastSync] = useState(null);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  const [customInstruction, setCustomInstruction] = useState("");
  const [viewingJob, setViewingJob] = useState(null);
  const pollRef = useRef(null);
  // Background task launcher. Nothing runs until Run is clicked - choosing a type or
  // typing a target only fills the form.
  const [bgType, setBgType] = useState("osint_recon");
  const [bgTarget, setBgTarget] = useState("");
  const [bgNote, setBgNote] = useState("");
  const [bgBusy, setBgBusy] = useState(false);
  const [bgErr, setBgErr] = useState("");

  const refreshJobsAndWorkspace = async () => {
    const headers = { "X-Officer": getActiveOfficerId() };
    try {
      const r = await fetch(`${API}/api/jobs`, { headers });
      if (!r.ok) throw new Error(String(r.status));
      const d = await r.json();
      setJobs(Array.isArray(d?.jobs) ? d.jobs : (Array.isArray(d) ? d : []));
      setLinkOk(true);
      setLastSync(Date.now());
    } catch {
      setLinkOk(false);
    }
    try {
      if (sessionId || suspects?.[0]?.id) {
        const itemId = suspects?.[0]?.id || sessionId;
        const w = await (await fetch(`${API}/api/workspace/${itemId}`, { headers })).json();
        setWorkspaceData(w);
      }
    } catch {}
  };

  // Poll every 2.5 s while a task is running (the officer is watching it), every 15 s
  // otherwise - enough to keep the Live indicator honest without a request storm.
  const busyRef = useRef(false);
  useEffect(() => { busyRef.current = jobs.some((j) => j.status === "running" || j.status === "queued"); }, [jobs]);
  useEffect(() => {
    refreshJobsAndWorkspace();
    let last = Date.now();
    pollRef.current = setInterval(() => {
      const due = busyRef.current ? 2500 : 15000;
      if (Date.now() - last >= due) { last = Date.now(); refreshJobsAndWorkspace(); }
    }, 2500);
    return () => clearInterval(pollRef.current);
  }, [sessionId, suspects]);

  const launch = async (type) => {
    const target = suspects[0]?.name || suspects[0]?.id || String(question || "").slice(0, 60);
    const payload = { type, target };
    if (type === "custom") {
      if (!customInstruction.trim()) return;
      payload.instruction = customInstruction.trim();
      setCustomInstruction("");
    }
    try {
      await fetch(`${API}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Officer": getActiveOfficerId() },
        body: JSON.stringify(payload),
      });
      setJobsExpanded(true);
      refreshJobsAndWorkspace();
    } catch {}
  };

  const runBackground = async () => {
    const spec = BG_TASKS.find((t) => t.type === bgType);
    const target = bgTarget.trim() || suspects[0]?.name || suspects[0]?.id || (spec?.needsTarget ? "" : "general");
    if (spec?.needsTarget && !target) { setBgErr(kn ? "ಗುರಿ ನಮೂದಿಸಿ." : "Enter a target first."); return; }
    if (bgType === "custom" && !bgNote.trim()) { setBgErr(kn ? "ಸೂಚನೆ ಬರೆಯಿರಿ." : "Describe the task first."); return; }
    setBgErr(""); setBgBusy(true);
    try {
      const body = { type: bgType, target: target.slice(0, 120) };
      if (bgType === "custom") body.instruction = bgNote.trim().slice(0, 1000);
      const r = await fetch(`${API}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Officer": getActiveOfficerId() },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(String(r.status));
      setBgNote("");
      setJobsExpanded(true);
      refreshJobsAndWorkspace();
    } catch {
      setBgErr(kn ? "ಕಾರ್ಯ ಆರಂಭವಾಗಲಿಲ್ಲ - ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ." : "The task did not start - please retry.");
    } finally {
      setBgBusy(false);
    }
  };

  const cancelJob = async (jobId) => {
    try {
      await fetch(`${API}/api/jobs/${jobId}`, {
        method: "DELETE",
        headers: { "X-Officer": getActiveOfficerId() },
      });
      refreshJobsAndWorkspace();
    } catch {}
  };

  const addNote = async () => {
    if (!newNote.trim()) return;
    const itemId = suspects[0]?.id || sessionId || "doc-1";
    try {
      await fetch(`${API}/api/workspace/${itemId}/note`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Officer": getActiveOfficerId() },
        body: JSON.stringify({ text: newNote.trim(), tags: ["expert-note"] }),
      });
      setNewNote("");
      refreshJobsAndWorkspace();
    } catch {}
  };

  function exportReport() {
    if (!sessionId) return;
    openReport(`/report/${sessionId}`);
  }


  const [ins, setIns] = useState({ status: "idle", data: null, error: "" });
  useEffect(() => {
    if (!meta?.hash) { setIns({ status: "idle", data: null, error: "" }); return; }
    let alive = true;
    setIns({ status: "loading", data: null, error: "" });
    fetchAPI(`/api/answer-record/${encodeURIComponent(meta.hash)}/insights`)
      .then((d) => { if (alive) setIns({ status: "ok", data: d, error: "" }); })
      .catch((e) => { if (alive) setIns({ status: "err", data: null, error: e?.message || "Insights are not available right now." }); });
    return () => { alive = false; };
  }, [meta?.hash]);

  // The header shortcuts open the Brief and bring that section into view.
  const jump = (id) => {
    setActiveTab("document");
    setTimeout(() => {
      const el = document.getElementById(id);
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      el.classList.remove("c2-flash"); void el.offsetWidth; el.classList.add("c2-flash");
    }, 60);
  };

  function copyCSV() {
    if (parsed.ranking.length > 0) {
      const csv = ["Name,FIRs,Share"];
      parsed.ranking.forEach(r => csv.push(`"${r.name}","${r.n}","${r.pct}"`));
      navigator.clipboard.writeText(csv.join('\n'));
    }
  }

  const running = jobs.filter((j) => j.status === "running" || j.status === "queued").length;
  const parsed = parseAnswer(editing ? draft : answer);
  const insights = deriveInsights(parsed.ranking, kn);
  const rankInsights = insights.map((t) => ({ kind: "ranking", title: "", text: t, cls: "D", firs: [] }));
  const insightCount = (ins.data?.items?.length || 0) + rankInsights.length;
  const showInsights = !!parsed.summary && (ins.status === "loading" || insightCount > 0 || !!meta?.hash);
  const sure = parsed.summary ? howSure(evidenceClass, claims, kn) : null;
  // A claim that only repeats the bottom line is not a second piece of evidence.
  const extraClaims = claims.filter((c) => !sameText(c.text, parsed.summary));
  const nextQs = (suggested || []).filter((q) => typeof q === "string" && q.trim() && q.trim() !== String(question || "").trim()).slice(0, 4);

  const stale = lastSync && now - lastSync > (running > 0 ? 8000 : 25000);   // idle poll is 15 s
  const link = linkOk === null ? "wait" : !linkOk ? "down" : stale ? "stale" : "up";
  const linkLabel = { wait: "Syncing", up: "Live", stale: "Stale", down: "Waking up" }[link];
  const elapsedS = meta?.elapsed_ms != null ? (meta.elapsed_ms / 1000).toFixed(1) : null;
  const tPlus = (sec) => {
    if (!sec) return "";
    const d = Math.max(0, Math.round(now / 1000 - sec));
    if (kn) return d < 10 ? "ಈಗ" : d < 60 ? `${d}ಸೆ ಹಿಂದೆ` : d < 3600 ? `${Math.floor(d / 60)}ನಿ ಹಿಂದೆ` : `${Math.floor(d / 3600)}ಗಂ ಹಿಂದೆ`;
    return d < 10 ? "just now" : d < 60 ? `${d}s ago` : d < 3600 ? `${Math.floor(d / 60)}m ago` : `${Math.floor(d / 3600)}h ago`;
  };
  const jobStatus = (st) => ({
    queued: kn ? "ಸರತಿಯಲ್ಲಿ" : "Waiting", running: kn ? "ಚಾಲನೆಯಲ್ಲಿ" : "Running", done: kn ? "ಮುಗಿದಿದೆ" : "Done",
    failed: kn ? "ವಿಫಲ" : "Failed", cancelled: kn ? "ನಿಲ್ಲಿಸಲಾಗಿದೆ" : "Stopped",
  }[st] || sentence(String(st || "")));
  const channels = [
    ["document", kn ? "ಸಾರಾಂಶ" : "Brief", null],
    ["references", kn ? "ಸಾಕ್ಷ್ಯ" : "Evidence", citations?.length || 0],
    ["trace", kn ? "ಜಾಡು" : "Trace", trace?.length || 0],
    ["notes", kn ? "ದಾಖಲೆ" : "Notes", null],
  ];

  return (
    <aside className="xw xw-c2" aria-label="Expert command console" style={{
      width: (typeof window !== "undefined" && window.innerWidth < 768) ? "100%" : `${width}px`,
      minWidth: (typeof window !== "undefined" && window.innerWidth < 768) ? "100%" : `${width}px`,
      transition: isResizing ? "none" : "width 0.2s ease-out, min-width 0.2s ease-out"
    }}>
      {(typeof window !== "undefined" && window.innerWidth >= 768) && (
        <div className="xw-resizer" title="Drag to resize · double-click for an even split"
          onPointerDown={(e) => { e.preventDefault(); e.currentTarget.setPointerCapture(e.pointerId); setIsResizing(true); }}
          onDoubleClick={resetSplit}
        />
      )}

      {/* ── Status bar ─────────────────────────────────────────────────────── */}
      <div className="c2-status">
        {/* The panel is about the ANSWER, not about Antar - the product name was taking
            the most prominent line of a screen an officer reads for evidence. */}
        <div className="c2-callsign">
          <span>{kn ? "ತಜ್ಞ ಕಾರ್ಯಕ್ಷೇತ್ರ" : "Expert workspace"}</span>
          {/* The agents that produced THIS answer, beside the title. One click goes to the
              Agents block below, where they can be run. Nothing is shown when the answer names none. */}
          {(() => {
            const used = agentsUsed(meta?.agents, trace).filter((a) => FACE[a]);
            if (!answer || !used.length) return null;
            return (
              <button type="button" className="c2-agents" onClick={() => {
                        // The Agents block lives in the Brief; go there and bring it into view.
                        setActiveTab("document");
                        setTimeout(() => document.getElementById("wa-block")?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
                      }}
                      title={`${kn ? "ಬಳಸಿದ ಏಜೆಂಟ್‌ಗಳು" : "Agents used"}: ${used.map((a) => a.replace(/_/g, " ")).join(", ")}`}
                      aria-label={`Agents used: ${used.join(", ")}. Go to the agents for this answer.`}>
                <em>{kn ? "ಬಳಸಿದ ಏಜೆಂಟ್‌ಗಳು" : "Agents used"}</em>
                {used.map((a, i) => (
                  <i key={a} className="wa-face" style={{ backgroundImage: `url(/mascots/sm/${FACE[a]}-directions.webp)`, animationDelay: `${i * -0.45}s` }} />
                ))}
              </button>
            );
          })()}
          {answer && (
            <div className="c2-quick" role="toolbar" aria-label={kn ? "ಶಾರ್ಟ್‌ಕಟ್‌ಗಳು" : "Shortcuts"}>
              <button type="button" onClick={() => jump("xw-next")} disabled={!nextQs.length || !onAsk}
                      title={nextQs.length ? (kn ? "ಮುಂದಿನ ಪ್ರಶ್ನೆಗಳು" : "Follow-up questions, one click asks them") : (kn ? "ಈ ಉತ್ತರಕ್ಕೆ ಮುಂದಿನ ಪ್ರಶ್ನೆಗಳಿಲ್ಲ" : "No follow-up questions for this answer")}>
                <CornerDownRight size={13} aria-hidden="true" /><span>{kn ? "ಮುಂದೆ ಕೇಳಿ" : "Ask next"}</span>
              </button>
              <button type="button" onClick={() => jump("xw-insights")} disabled={!showInsights}
                      title={kn ? "ಈ ಉತ್ತರದ FIRಗಳಲ್ಲಿ ಎದ್ದು ಕಾಣುವುದು" : "What stands out in the FIRs behind this answer"}>
                <Sparkles size={13} aria-hidden="true" /><span>{kn ? "ಅಂತರ್ ಒಳನೋಟಗಳು" : "Antar insights"}</span>
                {insightCount > 0 && <em className="c2-quick-n">{insightCount}</em>}
              </button>
              <button type="button" onClick={() => jump("xw-how")} disabled={!parsed.summary}
                      title={kn ? "ಈ ಉತ್ತರ ಹೇಗೆ ಬಂತು" : "How this was answered: method, agents, audit id"}>
                <HelpCircle size={13} aria-hidden="true" /><span>{kn ? "ಹೇಗೆ?" : "How?"}</span>
              </button>
              <button type="button" className="c2-quick-copy" onClick={exportReport} disabled={!sessionId}
                      title={sessionId ? (kn ? "PDF ವರದಿ ಡೌನ್‌ಲೋಡ್" : "Download the PDF report") : (kn ? "ವರದಿಗಾಗಿ ಮೊದಲು ಒಂದು ಪ್ರಶ್ನೆ ಕೇಳಿ" : "Ask a question first: the report is built from the conversation")}>
                <Download size={12} aria-hidden="true" /><span>PDF</span>
              </button>
            </div>
          )}
        </div>
        <div className="c2-leds" role="status" aria-live="polite">
          <span className={`c2-led ${link}`} title={lastSync ? `Last sync ${Math.round((now - lastSync) / 1000)}s ago` : "Waiting for first sync"}>
            <i /> {linkLabel}
          </span>
          {running > 0 && (
            <span className="c2-led busy" title={`${running} operation(s) in progress`}>
              <i /> {running} {kn ? "ಚಾಲನೆ" : "running"}
            </span>
          )}
        </div>
        <div className="c2-actions">
          <button onClick={toggleExpand} title={expanded ? "Restore width" : "Expand console"}>
            {expanded ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
          <button className="c2-x" onClick={onClose} aria-label="Close console"><X size={14} /></button>
        </div>
      </div>

      {/* ── Facts strip: what this answer rests on, in plain words. A value the pipeline
            did not report is left out rather than shown as a dash. ─────────────── */}
      {answer && (() => {
        const facts = [
          typeof meta?.rows === "number" && [kn ? "ಉತ್ತರದ ಸಾಲುಗಳು" : "Rows in answer", meta.rows.toLocaleString()],
          [kn ? "ಉಲ್ಲೇಖಿತ FIR" : "FIRs cited", (citations?.length || 0).toLocaleString()],
          elapsedS && [kn ? "ಉತ್ತರ ಸಮಯ" : "Answered in", `${elapsedS}s`],
          [kn ? "ಲೆಕ್ಕಪತ್ರ" : "Audit log", meta?.hash
            ? <span className="ok" title={`Audit log fingerprint ${meta.hash}`}><ShieldCheck size={13} aria-hidden="true" /> {kn ? "ದಾಖಲಾಗಿದೆ" : "Recorded"}</span>
            : (kn ? "ಇಲ್ಲ" : "Not recorded")],
        ].filter(Boolean);
        return (
          <div className="c2-sitrep" style={{ gridTemplateColumns: `repeat(${facts.length}, minmax(0, 1fr))` }}>
            {facts.map(([k, v]) => <div key={k}><span>{k}</span><b>{v}</b></div>)}
          </div>
        );
      })()}

      {/* ── Channels ──────────────────────────────────────────────────────── */}
      <div className="c2-channels" role="tablist">
        {channels.map(([k, label, n]) => (
          <button key={k} role="tab" aria-selected={activeTab === k} className={activeTab === k ? "on" : ""} onClick={() => setActiveTab(k)}>
            {label}{n != null && <em>{n}</em>}
          </button>
        ))}
        <span className="c2-spacer" />
        {activeTab === "document" && (editing || showEditDisclaimer ? (
          <>
            <button className="c2-mini" onClick={() => { setEditing(false); setShowEditDisclaimer(false); }}>{kn ? "ರದ್ದು" : "Cancel"}</button>
            {editing && <button className="c2-mini on" onClick={() => { setPublished(true); setEditing(false); }}>{kn ? "ಉಳಿಸಿ" : "Save"}</button>}
          </>
        ) : (
          <button className="c2-mini" onClick={() => setShowEditDisclaimer(true)} title={kn ? "ಅಧಿಕೃತ ವರದಿಯನ್ನು ರಫ್ತು ಮಾಡುವ ಮುನ್ನ ಜನರೇಟ್ ಆದ ಸಾರಾಂಶವನ್ನು ತಿದ್ದುಪಡಿ ಮಾಡಿ" : "Modify the AI-generated brief to add human context before exporting the official report"}>{kn ? "ತಿದ್ದು" : "Edit"}</button>
        ))}
      </div>

      <div className="xw-scroll c2-main">
        {/* BRIEF */}
        {activeTab === "document" && (
          <div className="xw-doc">
            {question && (
              <div className="c2-asked">
                <span>{kn ? "ನೀವು ಕೇಳಿದ್ದು" : "You asked"}</span>
                <p title={question}>{question}</p>
              </div>
            )}
            {published && <div className="xw-pub">● {kn ? "ಪ್ರಕಟಿಸಲಾಗಿದೆ" : "Published · read-only record"}</div>}

            {showEditDisclaimer ? (
              <div className="xw-disclaimer" style={{ padding: "20px", background: "rgba(34, 230, 240, 0.05)", borderLeft: "2px solid #22e6f0", borderRadius: "4px", marginBottom: "16px", marginTop: "16px" }}>
                <h3 style={{ fontSize: "14.5px", fontWeight: 600, color: "#22e6f0", marginBottom: "12px", letterSpacing: "0.01em" }}>
                  {kn ? "ತಿದ್ದುಪಡಿ ಆಯ್ಕೆಯ ಬಗ್ಗೆ" : "About the Edit Option"}
                </h3>
                <ul style={{ fontSize: "13px", color: "rgba(255,255,255,0.75)", paddingLeft: "20px", marginBottom: "20px", lineHeight: 1.6 }}>
                  <li style={{ marginBottom: "8px" }}>{kn ? "ಆಫ್‌ಲೈನ್ ಸಂದರ್ಭ, ಪ್ರಕರಣದ ಟಿಪ್ಪಣಿಗಳು ಅಥವಾ ಸಾಂಸ್ಥಿಕ ಜ್ಞಾನವನ್ನು ಸೇರಿಸಿ." : "Add offline context, case notes, or institutional knowledge."}</li>
                  <li style={{ marginBottom: "8px" }}>{kn ? "ಪ್ರಮಾಣಿತ ಪೊಲೀಸ್ ವರದಿ ಮಾಡುವ ಪ್ರೋಟೋಕಾಲ್‌ಗಳಿಗೆ ಸರಿಹೊಂದುವಂತೆ ಮಾತುಗಳನ್ನು ಪರಿಷ್ಕರಿಸಿ." : "Refine wording to fit standard police reporting protocols."}</li>
                  <li>{kn ? "ಅಧಿಕೃತ ಆಡಿಟ್-ಸಿದ್ಧ PDF ವರದಿಯನ್ನು ರಫ್ತು ಮಾಡುವ ಮೊದಲು ಅಂತಿಮಗೊಳಿಸಿ." : "Finalize text before exporting the official, audit-ready PDF report."}</li>
                </ul>
                <button className="c2-mini on" style={{ padding: "6px 16px", fontSize: "13px", letterSpacing: "0.02em" }} onClick={() => { setShowEditDisclaimer(false); setEditing(true); }}>
                  {kn ? "ನನಗೆ ಅರ್ಥವಾಗಿದೆ" : "I understand"}
                </button>
              </div>
            ) : editing ? (
              <textarea className="xw-editor" value={draft} onChange={(e) => setDraft(e.target.value)} spellCheck={false} />
            ) : (
              <div className="xw-body">
                {parsed.summary ? (
                  <div className="c2-block c2-bluf">
                    <div className="c2-block-t">
                      {kn ? "ಮುಖ್ಯ ತೀರ್ಮಾನ" : "Bottom line"}
                      <ClassTag c={evidenceClass} kn={kn} />
                    </div>
                    <p><XwInline text={parsed.summary} /></p>
                    {parsed.trend && <div className="c2-trend"><Activity size={12} aria-hidden="true" /> <XwInline text={parsed.trend} /></div>}
                    {sure && (
                      <div className={`c2-sure c2-sure-${sure.cls}`}>
                        <i aria-hidden="true" />
                        <span><b>{kn ? "ಎಷ್ಟು ಖಚಿತ" : "How sure"}</b> {sure.text}</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="xw-empty">{kn ? "ಎಡಭಾಗದಲ್ಲಿ ಪ್ರಶ್ನೆ ಕೇಳಿ - ಉತ್ತರ ಇಲ್ಲಿ ಸಾರಾಂಶವಾಗುತ್ತದೆ." : "Ask a question in the chat. The answer is turned into a brief here, with the FIRs it came from."}</p>
                )}

                {showInsights && <AntarInsights state={ins} extra={rankInsights} kn={kn} />}

                {/* Every claim with its evidence class - ICD 203: keep what the record says
                    apart from what was calculated, judged, or is simply unknown. */}
                {extraClaims.length > 0 && (
                  <div className="c2-block">
                    <div className="c2-block-t">{kn ? "ಪ್ರತಿ ಅಂಶ ಮತ್ತು ಅದರ ಮೂಲ" : "Each point and where it comes from"}</div>
                    {extraClaims.map((c, i) => (
                      <div key={i} className="c2-claim">
                        <span className="c2-claim-t"><XwInline text={c.text} /></span>
                        <ClassTag c={c.tag} kn={kn} />
                      </div>
                    ))}
                  </div>
                )}

                {parsed.ranking.length > 0 && (
                  <div className="c2-block">
                    <div className="c2-block-t">
                      <span>{parsed.rankCaption || (kn ? "ಶ್ರೇಣಿ" : "Ranking")}</span>
                      <button onClick={copyCSV} className="xw-icon-btn" title="Copy as CSV"><FileSpreadsheet size={13} /></button>
                    </div>
                    <table className="xw-table c2-table">
                      <thead><tr><th>#</th><th>{kn ? "ಘಟಕ" : "Entity"}</th><th style={{ textAlign: "right" }}>FIRs</th><th style={{ textAlign: "right" }}>{kn ? "ಪಾಲು" : "Share"}</th></tr></thead>
                      <tbody>
                        {parsed.ranking.map((r, i) => (
                          <tr key={i}>
                            <td>{String(i + 1).padStart(2, "0")}</td>
                            <td><XwInline text={r.name} /></td>
                            <td style={{ textAlign: "right" }}>{r.n}</td>
                            <td style={{ textAlign: "right" }}>{r.pct}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {parsed.rest.length > 0 && (
                  <div className="c2-block">
                    <div className="c2-block-t">{kn ? "ವಿವರಗಳು" : "Details"}</div>
                    {parsed.rest.map((r, i) => {
                      if (r.type === "heading") return <h3 key={i} className="xw-sh"><XwInline text={r.text} /></h3>;
                      if (r.type === "bullet") return <div key={i} className="xw-li"><XwInline text={r.text} /></div>;
                      return <p key={i}><XwInline text={r.text} /></p>;
                    })}
                  </div>
                )}

                {/* The agents: which ones worked on this answer, and the ones that can be run
                    from here on a record it names. */}
                {answer && <WorkspaceAgents answer={answer} question={question} suspects={suspects} usedAgents={meta?.agents || []} trace={trace} kn={kn} />}

                {/* What the answer is made of - stated, not implied. Every value here is
                    reported by the pipeline for THIS answer; a missing one reads "—"
                    rather than being filled in with something plausible. */}
                {parsed.summary && (
                  <div className="c2-block c2-srcblk" id="xw-how">
                    <div className="c2-block-t">{kn ? "ಆಧಾರ ಮತ್ತು ವಿಧಾನ" : "How this was answered"}</div>
                    <div className="c2-srcgrid">
                      <div><span>{kn ? "ವಿಧಾನ" : "Method"}</span><b>{meta?.method || meta?.template_id || "—"}</b></div>
                      <div><span>{kn ? "ದಾಖಲೆಗಳು" : "Records read"}</span><b>{typeof meta?.rows === "number" ? meta.rows.toLocaleString() : "—"}</b></div>
                      <div><span>{kn ? "ಉಲ್ಲೇಖಿತ FIR" : "FIRs cited"}</span><b>{citations?.length || 0}</b></div>
                      <div><span>{kn ? "ಬರೆದದ್ದು" : "Written by"}</span><b>{meta?.mode === "llm" ? (kn ? "ಭಾಷಾ ಮಾದರಿ" : "Language model, checked") : (kn ? "ನಿಗದಿತ ನಮೂನೆ" : "Fixed template")}</b></div>
                      <div><span>{kn ? "ಏಜೆಂಟ್‌ಗಳು" : "Agents"}</span><b>{(meta?.agents || []).length ? meta.agents.map((a) => sentence(String(a).replace(/_/g, " "))).join(", ") : "—"}</b></div>
                      <div><span>{kn ? "ಲೆಕ್ಕಪತ್ರ ಐಡಿ" : "Audit id"}</span><b title={meta?.hash || ""}>{meta?.hash ? meta.hash.slice(0, 12) : "—"}</b></div>
                    </div>
                    {citations?.length > 0 && (
                      <button className="c2-srclink" onClick={() => setActiveTab("references")}>
                        {kn ? `ಎಲ್ಲಾ ${citations.length} ಸಾಕ್ಷ್ಯ ಸಾಲುಗಳನ್ನು ನೋಡಿ →` : `See all ${citations.length} cited records →`}
                      </button>
                    )}
                    {!citations?.length && (
                      <div className="c2-srcnote">
                        {kn ? "ಇದು ಒಟ್ಟುಗೂಡಿಸಿದ ಎಣಿಕೆ - ಪ್ರತ್ಯೇಕ FIR ಉಲ್ಲೇಖಗಳಿಲ್ಲ."
                            : "An aggregate count over the registry - no single FIR to cite."}
                      </div>
                    )}
                  </div>
                )}

                {/* Where to go next: the follow-ups the pipeline checked against the data for
                    this answer. One click asks it in the chat. */}
                {nextQs.length > 0 && onAsk && (
                  <div className="c2-block c2-next" id="xw-next">
                    <div className="c2-block-t">{kn ? "ಮುಂದೆ ಕೇಳಿ" : "Ask next"}</div>
                    {nextQs.map((q) => (
                      <button key={q} type="button" onClick={() => onAsk(q)}>
                        <CornerDownRight size={13} aria-hidden="true" /><span>{q}</span>
                      </button>
                    ))}
                  </div>
                )}

                {parsed.summary && (
                  <div className="c2-report">
                    {sessionId && (
                      <button type="button" className="c2-report-main" onClick={exportReport}><Download size={14} aria-hidden="true" /> {kn ? "PDF ವರದಿ ಡೌನ್‌ಲೋಡ್" : "Download PDF report"}</button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* EVIDENCE */}
        {activeTab === "references" && (
          <div className="xw-refs c2-list">
            {(!citations || citations.length === 0) ? (
              <div className="xw-empty">{kn ? "ಈ ಉತ್ತರಕ್ಕೆ ಉಲ್ಲೇಖಗಳಿಲ್ಲ." : "No evidence rows cited for this answer."}</div>
            ) : citations.map((c, i) => (
              <Link key={i} href={`/case?id=${encodeURIComponent(c.id || c.fir)}`} className="xw-ref c2-row c2-firrow" title={kn ? "ಪ್ರಕರಣದ ಕಾಲರೇಖೆ ತೆರೆಯಿರಿ" : "Open the case timeline"}>
                <span className="c2-idx">{i + 1}</span>
                <div>
                  <b>FIR {c.fir}</b>{c.station ? <span className="c2-firstn"> · {c.station}</span> : ""}
                  <div className="xw-ref-sub">{[c.section, c.date].filter(Boolean).join(" · ")}</div>
                </div>
                <ArrowUpRight size={14} className="c2-firgo" aria-hidden="true" />
              </Link>
            ))}
          </div>
        )}

        {/* TRACE - the real agent/step trail for this answer */}
        {activeTab === "trace" && (
          <ol className="c2-trace">
            {(!trace || trace.length === 0) ? (
              <li className="xw-empty">{kn ? "ಈ ಉತ್ತರಕ್ಕೆ ಜಾಡು ಇಲ್ಲ." : "No agent trace recorded for this answer."}</li>
            ) : trace.map((t, i) => (
              <li key={i}>
                <span className="c2-idx">{String(i + 1).padStart(2, "0")}</span>
                <span className="ag">{sentence(String(t.agent || t.step || "step").replace(/_/g, " "))}</span>
                <span className="tx">{t.label || t.detail || t.step || ""}</span>
              </li>
            ))}
          </ol>
        )}

        {/* SUGGESTED */}
        {activeTab === "suggested" && (
          <div className="xw-refs c2-list">
             <div className="xw-empty">{kn ? "ಸಂಬಂಧಿತ ಪ್ರಶ್ನೆಗಳು ಮತ್ತು ಸಂಪರ್ಕಗಳು ಇಲ್ಲಿವೆ." : "Related questions and connections will appear here."}</div>
          </div>
        )}
        
        {/* LOG */}
        {activeTab === "notes" && (
          <div className="xw-notes">
            <div className="c2-input">
              <FileText size={13} aria-hidden="true" />
              <input type="text" placeholder={kn ? "ದಾಖಲೆಗೆ ಟಿಪ್ಪಣಿ ಸೇರಿಸಿ…" : "Add a note to this case…"}
                value={newNote} onChange={(e) => setNewNote(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addNote()} />
              <button onClick={addNote} disabled={!newNote.trim()}>{kn ? "ಸೇರಿಸಿ" : "Add"}</button>
            </div>
            {(Array.isArray(workspaceData?.items) ? workspaceData.items : []).filter((it) => Array.isArray(it.notes) && it.notes.length > 0).map((it) => (
              <div key={it.item_id}>
                {it.notes.map((n, idx) => (
                  <div key={idx} className="c2-logline">
                    <span className="ts">{n.ts ? new Date(n.ts * 1000).toISOString().slice(11, 19) + "Z" : "now"}</span>
                    <span>{n.text}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Ops dock: always-visible operations queue ─────────────────────── */}
      <section className={`c2-ops ${jobsExpanded ? "open" : ""}`} aria-label={kn ? "ಕಾರ್ಯಾಚರಣೆಗಳು" : "Operations"}>
        <button className="c2-ops-h" onClick={() => setJobsExpanded(!jobsExpanded)} aria-expanded={jobsExpanded}>
          <Radio size={13} aria-hidden="true" />
          <b>{kn ? "ಹಿನ್ನೆಲೆ ಕಾರ್ಯಗಳು" : "Background tasks"}</b>
          <span className="c2-ops-count">
            {running > 0 ? `${running} ${kn ? "ಚಾಲನೆಯಲ್ಲಿ" : "running"} · ` : ""}
            {kn ? "ನೀವು ಕೆಲಸ ಮುಂದುವರಿಸುವಾಗ ಓಡುತ್ತವೆ" : "run while you keep working"}
          </span>
          <span className="c2-spacer" />
          <span onClick={(e) => { e.stopPropagation(); refreshJobsAndWorkspace(); }} className="xw-refresh" role="button" title="Refresh" tabIndex={0}><RefreshCw size={12} /></span>
          <span className="chev">{jobsExpanded ? "▾" : "▴"}</span>
        </button>

        <div className="c2-task">
          {["pattern_scan", "network_deep", "threat_assessment", "osint_recon"].map((t) => {
            const spec = BG_TASKS.find((x) => x.type === t);
            return (
              <button key={t} onClick={() => launch(t)} title={kn ? spec.hintKn : spec.hintEn}>
                <Play size={10} aria-hidden="true" /> {kn ? spec.kn : spec.en}
              </button>
            );
          })}
        </div>

        {jobsExpanded && (
          <>
            {/* Background task - choose, fill, then Run. Nothing starts before the click. */}
            <div className="c2-bg" role="group" aria-label={kn ? "ಹಿನ್ನೆಲೆ ಕಾರ್ಯ" : "Background task"}>
              <div className="c2-bg-h">{kn ? "ಹೊಸ ಕಾರ್ಯ ಆರಂಭಿಸಿ" : "Start a task"}</div>
              <div className="c2-bg-types">
                {BG_TASKS.map((t) => (
                  <button key={t.type} type="button" className={bgType === t.type ? "on" : ""}
                          aria-pressed={bgType === t.type} onClick={() => { setBgType(t.type); setBgErr(""); }}>
                    {kn ? t.kn : t.en}
                  </button>
                ))}
              </div>
              <div className="c2-bg-hint">
                {(() => { const t = BG_TASKS.find((x) => x.type === bgType); return kn ? t?.hintKn : t?.hintEn; })()}
              </div>
              <div className="c2-input">
                                <input type="text"
                  placeholder={bgType === "custom"
                    ? (kn ? "ಕಾರ್ಯವನ್ನು ವಿವರಿಸಿ…" : "Describe the task…")
                    : (kn ? "ಗುರಿ - ಹೆಸರು, ಐಡಿ, ಜಿಲ್ಲೆ…" : `Target - name, id, district${suspects[0] ? ` (default: ${suspects[0].name || suspects[0].id})` : ""}`)}
                  value={bgType === "custom" ? bgNote : bgTarget}
                  maxLength={bgType === "custom" ? 1000 : 120}
                  onChange={(e) => (bgType === "custom" ? setBgNote(e.target.value) : setBgTarget(e.target.value))}
                  onKeyDown={(e) => e.key === "Enter" && !bgBusy && runBackground()} />
                <button onClick={runBackground} disabled={bgBusy}>{bgBusy ? (kn ? "ಆರಂಭ…" : "Starting…") : (kn ? "ಚಲಾಯಿಸಿ" : "Run")}</button>
              </div>
              {bgErr && <div className="c2-bg-err" role="alert">{bgErr}</div>}
            </div>
            <div className="c2-queue">
              {!Array.isArray(jobs) || jobs.length === 0 ? (
                <div className="xw-jobs-empty">{kn ? "ಇನ್ನೂ ಕಾರ್ಯಾಚರಣೆಗಳಿಲ್ಲ." : "No tasks yet. Start one above; the result appears here."}</div>
              ) : jobs.map((j) => (
                <div key={j.job_id} className={`c2-job ${j.status}`}>
                  <span className={`xw-dot ${j.status}`} />
                  <div className="xw-job-body">
                    <div className="xw-job-t">
                      {j.type === "custom" ? `Custom · ${j.instruction}` : `${(BG_TASKS.find((x) => x.type === j.type)?.[kn ? "kn" : "en"]) || sentence(String(j.type || "").replace(/_/g, " "))}${j.target ? ` · ${j.target}` : ""}`}
                    </div>
                    <div className="xw-job-s">{j.summary || j.status}</div>
                  </div>
                  <span className="c2-job-meta">
                    <span className="st">{jobStatus(j.status)}</span>
                    <span className="tp">{tPlus(j.started_at || j.created_at)}</span>
                  </span>
                  {j.status === "done" && <button onClick={() => setViewingJob(j)} className="xw-view-btn">View</button>}
                  {["queued", "running"].includes(j.status) && (
                    <button onClick={() => cancelJob(j.job_id)} title="Stop this task" className="xw-stop-btn"><Square size={9} /> Stop</button>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {viewingJob && (
        <div className="xw-job-modal">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h3 className="c2-modal-t">
              <span className="c2-led up"><i /></span>
              {(BG_TASKS.find((x) => x.type === viewingJob.type)?.[kn ? "kn" : "en"]) || sentence(String(viewingJob.type || "").replace(/_/g, " "))} · {kn ? "ಫಲಿತಾಂಶ" : "Result"}
            </h3>
            <button onClick={() => setViewingJob(null)} className="xw-icon-btn"><X size={16} /></button>
          </div>
          <div style={{ color: "var(--muted)", fontSize: "12px", marginBottom: "16px" }}>{viewingJob.summary}</div>
          <div className="xw-job-res">
            <JobResultViewer data={viewingJob.result} kn={kn} />
          </div>
        </div>
      )}
    </aside>
  );
}
