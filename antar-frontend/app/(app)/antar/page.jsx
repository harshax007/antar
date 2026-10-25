"use client";

import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, memo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Orb from "@/components/Orb";
import LangToggle from "@/components/LangToggle";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Paperclip, Globe, ArrowUp, X, Mic, MicOff, Brain, Network, Share2, Compass, CheckCircle2, Sparkles, RefreshCw, Copy, Download, ThumbsUp, ThumbsDown, Map as MapIcon, Search as SearchIcon, Languages, Square, Volume2, Loader2, Activity } from "lucide-react";
import NetworkGraph from "@/components/NetworkGraph";
import ExpertWorkspace from "@/components/ExpertWorkspace";
import { useLang } from "@/components/Providers";
import CinematicBackground from "@/components/CinematicBackground";

import { SLASH_COMMANDS as SLASH_HINTS } from "@/lib/chatStream";
import { WhisperMicButton, WhisperWaveform } from "@/components/WhisperMic";
import { getActiveOfficerId } from "@/components/OfficerSelector";
import { asset } from "@/lib/assets";
import { openReport, readSession } from "@/lib/auth";
import AgentStrip, { AGENTS as STRIP_AGENTS, LENS } from "@/components/AgentStrip";
import YearQuestions, { yearQuestions } from "@/components/YearQuestions";
import { FACE as AGENT_FACE } from "@/components/WorkspaceAgents";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

function getAuthHeaders() {
  const headers = {
    "Content-Type": "application/json",
    "X-Officer": getActiveOfficerId(),
  };
  try {
    const session = readSession();
    if (session?.token) {
      headers["Authorization"] = `Bearer ${session.token}`;
    }
  } catch {}
  return headers;
}

// Questions offered by ROLE, beside the data-checked "Related" follow-ups the backend
// returns. Operations (Admin / Inspector) works cases and proposes real-world action;
// the Approver supervises those proposals and needs outcome and accountability figures.
// Every one of these is a shape the template layer answers from records - they are not
// LLM-invented, so a chip never leads to a dead end.
const ROLE_QUESTIONS = {
  operations: {
    en: [
      "Which districts had the most theft in 2022?",
      "Which police stations recorded the most cybercrime in 2022?",
      "Top beats for burglary in Bengaluru City",
      "Top areas for theft in Mysuru City",
      "Which districts had the most murders in 2022?",
    ],
    kn: [
      "2022 ರಲ್ಲಿ ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ನಡೆದಿದೆ?",
      "2022 ರಲ್ಲಿ ಸೈಬರ್ ಅಪರಾಧ ಹೆಚ್ಚು ದಾಖಲಾದ ಠಾಣೆಗಳು",
      "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಮನೆಗಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಬೀಟ್‌ಗಳು",
      "ಮೈಸೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಪ್ರದೇಶಗಳು",
      "2022 ರಲ್ಲಿ ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚು ಕೊಲೆಗಳು ದಾಖಲಾಗಿವೆ?",
    ],
  },
  approver: {
    en: [
      "Conviction rate by district in 2022",
      "What share of 2022 FIRs reached chargesheet?",
      "Crimes against women by district in 2022",
      "IPC/BNS vs SLL split for 2022?",
      "Which districts had the most murders in 2022?",
    ],
    kn: [
      "2022 ರಲ್ಲಿ ಜಿಲ್ಲಾವಾರು ಶಿಕ್ಷೆ ಪ್ರಮಾಣ",
      "2022 ರ ಎಷ್ಟು ಎಫ್‌ಐಆರ್‌ಗಳು ದೋಷಾರೋಪ ಪಟ್ಟಿ ತಲುಪಿದವು?",
      "2022 ರಲ್ಲಿ ಜಿಲ್ಲಾವಾರು ಮಹಿಳೆಯರ ಮೇಲಿನ ಅಪರಾಧ",
      "2022 ರ IPC/BNS ಮತ್ತು SLL ಹಂಚಿಕೆ",
      "2022 ರಲ್ಲಿ ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚು ಕೊಲೆಗಳು ದಾಖಲಾಗಿವೆ?",
    ],
  },
};

// Starters on the empty chat. Each one is answered from the real KSP record and was run
// through the router and the answer writer before it was put here (2026-10-16). They used
// to name people, vehicles and localities that exist only in seeded demo rows ("Ravi living
// in Jayanagar", "KA-02-M-2093", "Bheema the Butcher"). They rank, compare and rate; none
// headlines a raw count. 2016-2022 is a partial extract (about a third of each year), so its
// counts are low while its shares and rankings hold; 2023-24 holds 100,000 duplicated rows
// (PROGRESS.md, open risks).
const STARTERS = {
  en: [
    "Cognizable FIRs registered in Karnataka in 2022?",
    "IPC/BNS vs SLL split for 2022?",
    "Which police stations recorded the most cybercrime in 2022?",
    "Which districts had the most murders in 2022?",
    "Crimes against women 2022 + top districts?",
    "Fastest-growing crime groups 2021 to 2022?",
    "Which districts had the most theft in 2022?",
    "Top areas for theft in Mysuru City",
    "Which district had the most road accident cases in 2022?",
    "Conviction rate by district in 2022",
    "Top beats for burglary in Bengaluru City",
  ],
  kn: [
    "2022 ರಲ್ಲಿ ಕರ್ನಾಟಕದಲ್ಲಿ ದಾಖಲಾದ ಕಾಗ್ನಿಜೇಬಲ್ FIR ಗಳು ಎಷ್ಟು?",
    "2022 ರ IPC/BNS ಮತ್ತು SLL ಹಂಚಿಕೆ",
    "2022 ರಲ್ಲಿ ಸೈಬರ್ ಅಪರಾಧ ಹೆಚ್ಚು ದಾಖಲಾದ ಠಾಣೆಗಳು",
    "2022 ರಲ್ಲಿ ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚು ಕೊಲೆಗಳು ದಾಖಲಾಗಿವೆ?",
    "2022 ರ ಮಹಿಳೆಯರ ಮೇಲಿನ ಅಪರಾಧಗಳು + ಪ್ರಮುಖ ಜಿಲ್ಲೆಗಳು",
    "2021 ರಿಂದ 2022 ಕ್ಕೆ ವೇಗವಾಗಿ ಬೆಳೆಯುತ್ತಿರುವ ಅಪರಾಧ ಗುಂಪುಗಳು",
    "2022 ರಲ್ಲಿ ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ನಡೆದಿದೆ?",
    "ಮೈಸೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಪ್ರದೇಶಗಳು",
    "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಮನೆಗಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಬೀಟ್‌ಗಳು",
  ],
};

// An answer that is still streaming outlives the page that asked for it. Leaving the chat
// mid-answer used to lose it: the stream kept arriving, but into a page that was gone, and
// on return the half-built reply came back as "Stopped". The stream now writes to whichever
// chat page is on screen, or, while none is, straight into the saved conversation; a page
// that opens while it is still running picks it up where it is.
const LIVE = { setMessages: null, setLoading: null, setSessionId: null, inflight: false };

function liveUpdateLast(fn) {
  if (LIVE.setMessages) {
    LIVE.setMessages((m) => {
      if (m.length === 0) return m;
      const next = [...m];
      next[next.length - 1] = fn(next[next.length - 1]);
      return next;
    });
    return;
  }
  try {
    const m = JSON.parse(sessionStorage.getItem("antar_chat_msgs") || "[]");
    if (m.length) {
      m[m.length - 1] = fn(m[m.length - 1]);
      sessionStorage.setItem("antar_chat_msgs", JSON.stringify(m));
    }
  } catch {}
}

function liveSessionId(id) {
  if (!id) return;
  try { sessionStorage.setItem("antar_chat_id", id); } catch {}
  LIVE.setSessionId?.(id);
}

function newAssistantMsg(lang) {
  return {
    role: "assistant",
    lang,
    ts: Date.now(),
    streaming: true,
    steps: [],
    text: "",
    citations: [],
    custody: null,
    confidence: null,
    brainBanner: null,
    brainHits: [],
    visuals: {},
    suspects: [],
    actions: [],
    suggested: [],
    template: null,
    reasoning: [],
    whyOpen: false,
    error: false,
    retryText: null,
  };
}

// Deep-link into the Map pre-filtered to what was asked (heatmap reflects the query).
function mapUrl(p) {
  const q = new URLSearchParams();
  if (p?.crime_type) q.set("crime", String(p.crime_type).toLowerCase().trim());
  if (p?.date_to) q.set("date", p.date_to);
  // a forecast answer opens the map on the unit it named, at its horizon and category
  if (p?.forecast_unit) q.set("unit", p.forecast_unit);
  if (p?.forecast_horizon) q.set("h", String(p.forecast_horizon));
  if (p?.forecast_category) q.set("fc", p.forecast_category);
  const s = q.toString();
  return s ? `/map?${s}` : "/map";
}

function searchUrl(name) {
  return name ? `/search?q=${encodeURIComponent(name)}` : "/search";
}

// Renders answer text as scannable lines: "• " items get a cyan bullet,
// "Label: …" agent add-ons (Profile/Network/Geo-Intel/…) get a bold label,
// everything else is a plain paragraph. Backends emit \n-structured text.
const ANS_LABEL = /^(Profile|Network|Geo-Intel|Patterns|Prediction|OSINT Flags|OSINT|Alerts & Deployment|Second Brain|Research Dossier):\s*(.*)$/;

// No emoji anywhere in rendered output (req #7) - covers pictographs, symbols,
// dingbats and variation selectors.



// Subtle key-info highlight: FIR/ID/section codes get
// a faint cyan emphasis so the eye lands on the facts.
// Order matters: identifiers and dates are listed BEFORE the bare-number alternative so
// "2026-07-20" / "2026-BLR-P2-2780" match as one token instead of being shredded into
// separate highlighted digits. Single digits are deliberately not highlighted (noise).
let GLOBAL_HL_COUNT = 0;
const HILITE_RE = /(?<![-\w])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?%|\d{2,})(?![-\w])/g;

function Highlighted({ text }) {
  const parts = String(text || "").split(HILITE_RE);
  return parts.map((p, i) => {
    if (i % 2 === 1) {
      if (/^\d{4}$/.test(p)) {
        const prev = parts[i - 1] || "";
        if (/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+$/i.test(prev)) {
          return p;
        }
      }
      return <b key={i} className="cx-hl">{p}</b>;
    }
    return <span key={i}>{p}</span>;
  });
}

// Minimal inline chart (pure SVG) - one accent color, no gridlines/legend clutter.
function MiniChart({ chart, kn }) {
  if (!chart?.points?.length) return null;
  const pts = chart.points.filter((p) => typeof p.value === "number");
  
  const total = pts.reduce((sum, p) => sum + p.value, 0);
  const max = pts.length > 0 ? Math.max(...pts.map((p) => p.value), 1) : 1;

  if (pts.length < 3 || max >= total * 0.70) {
    // Compact bar list
    return (
      <div className="cx-chart-list">
        {pts.map((p, i) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", padding: "2px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <span style={{ color: "var(--muted)" }}>{p.label}</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--text)" }}>{p.value.toLocaleString()}</span>
          </div>
        ))}
      </div>
    );
  }

  const W = 460, H = 84, pad = 4, bw = (W - pad * 2) / pts.length;
  return (
    <div className="cx-chart" aria-label={kn ? "ಡೇಟಾ ಚಿತ್ರ" : "Inline data chart"}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: 84 }}>
        {chart.kind === "line" ? (
          <>
            <polyline
              fill="none" stroke="var(--cyan)" strokeWidth="1.6" vectorEffect="non-scaling-stroke"
              points={pts.map((p, i) => `${pad + i * ((W - pad * 2) / (pts.length - 1))},${H - pad - (p.value / max) * (H - pad * 2)}`).join(" ")}
            />
            {pts.map((p, i) => (
              <circle key={i} r="2" fill="var(--cyan)"
                cx={pad + i * ((W - pad * 2) / (pts.length - 1))}
                cy={H - pad - (p.value / max) * (H - pad * 2)} />
            ))}
          </>
        ) : (
          pts.map((p, i) => {
            const h = Math.max(2, (p.value / max) * (H - pad * 2));
            return <rect key={i} x={pad + i * bw + bw * 0.18} y={H - pad - h}
              width={bw * 0.64} height={h} rx="1.5" fill="var(--cyan)" opacity={0.55 + 0.45 * (p.value / max)} />;
          })
        )}
      </svg>
      <div className="cx-chart-x">
        {pts.map((p, i) => (
          <span key={i} title={`${p.label}: ${p.value}`}>{String(p.label).slice(0, 8)}</span>
        ))}
      </div>
    </div>
  );
}

function normalizeAnswerText(raw) {
  if (!raw) return "";
  let s = String(raw);

  // Strip emojis (AI slop)
  s = s.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{1F1E6}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{2300}-\u{23FF}\u{2B50}-\u{2B59}\u{200D}\u{FE0E}\u{FE0F}]/gu, '');
  
  // Strip common conversational AI slop from the beginning of the string
  s = s.replace(/^(?:(?:Certainly!?|Sure,?|Yes,?)\s*)+(?:Here is the (?:information|analysis)[^:]*:|Based on the (?:records|data|analysis)[^,]*,\s*)?/gi, "");
  s = s.replace(/^(?:Here is the (?:information|analysis|result)[^:]*:|Based on the (?:records|data|analysis|search)[^,]*,\s*)/gi, "");
  
  // Strip backend technical tags globally
  s = s.replace(/\[(?:COMPUTED|VERIFIED|PATTERN|INFERRED|GAP)\]\s*/gi, '');
  s = s.replace(/PATTERNS/g, 'Patterns');
  
  // Remove AI-generated "(--)" and standalone em-dashes "—"
  s = s.replace(/\(--\)/g, '');
  s = s.replace(/(^|\s)—(\s|$)/g, '$1$2');

  // Convert legacy flat ". Monthly: 2026-05 (8), 2026-06 (3)..." into structured bullet lines
  s = s.replace(/\.\s*Monthly:\s*([^\n]+)/i, (match, items) => {
    const list = items
      .split(",")
      .map((x) => x.trim().replace(/\.$/, ""))
      .filter(Boolean)
      .map((x) => `• ${x.replace(/(\d{4}-\d{2})\s*\(([0-9]+)\)/, "$1: $2 cases")}`)
      .join("\n");
    return `\n${list}`;
  });
  
  // Ensure standalone Data-Verified gets clean formatting without the [VERIFIED] tag
  s = s.replace(/(^|\s)Data-Verified$/i, "\nData-Verified against official FIR registry records.");
  
  // Ensure clean breaks before standard headers if smashed on one line
  s = s.replace(/\.\s+(Patterns|Profile|Network|Geo-Intel|Prediction|Alerts & Deployment|OSINT|Research Dossier):\s*/gi, "\n$1: ");
  
  // Robustness against messy LLM formatting: give markdown headings their own line,
  // collapse runaway blank lines, and strip stray leading whitespace per line so the
  // renderer sees clean, predictable structure regardless of what the model emitted.
  s = s.replace(/([^\n])\n(#{1,6}\s)/g, "$1\n\n$2");
  s = s.replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n");
  s = s.split("\n").map((ln) => ln.replace(/^[ \t]+/, "")).join("\n");
  return s.trim();
}

// Inline rendering for every piece of answer text: **bold** (the Phase-1 compose prompt
// leads with a bold verdict) PLUS entity/number highlighting, so counts, FIR numbers,
// sections and dates stand out wherever they appear - body, list items and table cells.
// Every shape of FIR id in the register (app/agents/case_answer.py keeps the same list): an id
// written anywhere in an answer opens that case's timeline.
const FIR_ID_RE = /\b(K\d{7}|C\d{5,8}|SYN-[a-f0-9]{12}|SYN-20\d\d-\d{3,8}|(?:BG|HIST|FWD)-20\d\d-\d{3,8}|FIR-20\d\d-[\w-]{4,40})\b/g;
function WithCaseLinks({ text }) {
  const s = String(text ?? "");
  const out = [];
  let last = 0;
  for (const m of s.matchAll(FIR_ID_RE)) {
    if (m.index > last) out.push(<Highlighted key={`t${last}`} text={s.slice(last, m.index)} />);
    out.push(<Link key={`f${m.index}`} href={`/case/${encodeURIComponent(m[1])}`} className="cx-firlink" title="Open the case timeline">{m[1]}</Link>);
    last = m.index + m[0].length;
  }
  if (!out.length) return <Highlighted text={s} />;
  if (last < s.length) out.push(<Highlighted key={`t${last}`} text={s.slice(last)} />);
  return <>{out}</>;
}

function MdInline({ text }) {
  // Robust to whatever the LLM emits: **bold**, `code`, and stray single-asterisk
  // emphasis are all normalized so raw markdown never leaks onto the screen.
  const parts = String(text ?? "").split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    const b = p.match(/^\*\*([^*]+)\*\*$/);
    // Use cx-hl instead of cx-strong so markdown bold becomes cyan highlight!
    if (b) return <b key={i} className="cx-hl">{b[1]}</b>;
    const c = p.match(/^`([^`]+)`$/);
    if (c) return <code key={i} className="cx-code">{c[1]}</code>;
    // Drop leftover unpaired markdown emphasis tokens that would otherwise render literally.
    const clean = p.replace(/\*\*/g, "").replace(/(^|\s)\*(\S)/g, "$1$2").replace(/(\S)\*(\s|$)/g, "$1$2");
    return <WithCaseLinks key={i} text={clean} />;
  });
}

const _TBL_ROW = /^\s*\|(.+)\|\s*$/;
const _TBL_SEP = /^\s*\|?[\s:|]*-[\s:|-]*\|?\s*$/;   // the |---|---| divider
const _splitCells = (ln) => ln.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim());

// Record-set answers are markdown tables (Phase 1) - render them as real tables so
// FIR rows scan, instead of dumping raw pipes.
function MdTable({ header, rows }) {
  return (
    <div className="cx-mdtable-wrap">
      <table className="cx-mdtable">
        <thead><tr>{header.map((h, i) => <th key={i}><MdInline text={h} /></th>)}</tr></thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr key={ri}>{header.map((_, ci) => <td key={ci}><MdInline text={r[ci] ?? ""} /></td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderLine(t, key, cursor) {
  if (/not listed|not found|no info|no records|no exact|not directly|not in the provided/i.test(t) || /^(Note|Disclaimer)/i.test(t)) {
    return (
      <div key={key} className="cx-disclaimer-box">
        <span className="disclaimer-icon">i</span>
        <span className="disclaimer-text">{t.replace(/^(Note:|Disclaimer:)\s*/i, "")}{cursor}</span>
      </div>
    );
  }
  const stateMatch = t.match(/^\[(VERIFIED|COMPUTED|INFERRED|GAP|K|D|I|U)\]\s*(.*)$/i);
  if (stateMatch) {
    const tag = stateMatch[1].toUpperCase();
    let badgeClass = "cx-badge-k", badgeText = "K";
    if (tag === "COMPUTED" || tag === "D") { badgeClass = "cx-badge-d"; badgeText = "D"; }
    else if (tag === "INFERRED" || tag === "I") { badgeClass = "cx-badge-i"; badgeText = "I"; }
    else if (tag === "GAP" || tag === "U") { badgeClass = "cx-badge-u"; badgeText = "U"; }
    return (
      <div key={key} className="cx-para" style={{ display: "flex", alignItems: "baseline", gap: "10px", margin: "5px 0" }}>
        <span className={badgeClass}>{badgeText}</span>
        <span style={{ flex: 1 }}><MdInline text={stateMatch[2]} />{cursor}</span>
      </div>
    );
  }
  // Markdown headings the model sometimes emits (### Summary) → a clean subheading, no hash.
  const heading = t.match(/^#{1,6}\s+(.*)$/);
  if (heading) return <div key={key} className="cx-subhead"><MdInline text={heading[1]} />{cursor}</div>;
  // Horizontal rule (---, ***, ___) → a hairline divider instead of literal dashes.
  if (/^([-*_]\s?){3,}$/.test(t)) return <div key={key} className="cx-rule" />;
  // List rows: NO bullet dots (owner req) - render as clean, lightly-indented lines.
  // "Label: value" items get a bold cyan label; numbered items keep their number.
  const listMatch = t.match(/^([•\-*]|\d+\.)\s+(.*)$/);
  if (listMatch) {
    const numbered = /\d/.test(listMatch[1]);
    const body = listMatch[2];
    const lbl = body.match(/^([A-Zಀ-೿][\wಀ-೿ /&()'’.-]{1,34}):\s+(.*)$/);
    return (
      <div key={key} className="cx-line">
        {numbered && <span className="cx-linenum">{listMatch[1]}</span>}
        {lbl
          ? <span><b className="cx-anslab">{lbl[1]}</b> <MdInline text={lbl[2]} />{cursor}</span>
          : <span><MdInline text={body} />{cursor}</span>}
      </div>
    );
  }
  const m = t.match(ANS_LABEL);
  if (m) return <div key={key} className="cx-para"><b className="cx-anslab">{m[1]}</b> - <MdInline text={m[2]} />{cursor}</div>;
  return <div key={key} className="cx-para"><MdInline text={t} />{cursor}</div>;
}

function AnswerBody({ text, streaming, headline }) {
  const normalized = normalizeAnswerText(text);
  const lines = normalized.split("\n");
  
  if (headline && lines.length > 0 && lines[0].trim() === headline.trim()) {
    lines.shift();
  }

  const out = [];
  for (let i = 0; i < lines.length; i++) {
    const t = lines[i].trim();
    // markdown table block: header row immediately followed by a |---| separator
    if (_TBL_ROW.test(t) && i + 1 < lines.length && _TBL_SEP.test(lines[i + 1].trim())) {
      const header = _splitCells(t);
      const rows = [];
      let j = i + 2;
      while (j < lines.length && _TBL_ROW.test(lines[j].trim()) && !_TBL_SEP.test(lines[j].trim())) {
        rows.push(_splitCells(lines[j].trim()));
        j++;
      }
      out.push(<MdTable key={`t${i}`} header={header} rows={rows} />);
      i = j - 1;
      continue;
    }
    const cursor = streaming && i === lines.length - 1 ? <span className="cx-cursor" /> : null;
    if (!t) { out.push(<div key={i} className="cx-gap" />); continue; }
    out.push(renderLine(t, i, cursor));
  }
  return <>{out}</>;
}

// Hook for animated terminal braille/radar spinner
function useTerminalSpinner(active = true, intervalMs = 85) {
  const [frame, setFrame] = useState(0);
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => setFrame((f) => (f + 1) % 10), intervalMs);
    return () => clearInterval(timer);
  }, [active, intervalMs]);
  const SPINNERS = ["\u280B", "\u2819", "\u2839", "\u2838", "\u283C", "\u2834", "\u2826", "\u2827", "\u2807", "\u280F"];
  return SPINNERS[frame];
}

// Helper to format step labels inline: when running show original label,
// once done show "...done searching...", "...clarifying...", "...found X records..."
function formatStepLabel(step, kn) {
  const raw = step?.label || "";
  if (!raw) return "";
  if (step?.status === "running") {
    return raw;
  }
  // When step is done:
  if (/^\.\.\./.test(raw)) return raw;
  if (/^found /i.test(raw)) {
    return `...${raw.toLowerCase()}...`;
  }
  if (/searching/i.test(raw)) {
    return `...done searching...`;
  }
  if (/analyzing|understanding/i.test(raw)) {
    return `...done analyzing...`;
  }
  if (/clarif/i.test(raw)) {
    return `...clarifying...`;
  }
  if (/ready/i.test(raw)) {
    return `...done composing answer...`;
  }
  return `...done ${raw.toLowerCase().replace(/…|\.\.\./g, "").trim()}...`;
}

// Terminal-style reasoning window (Expert Search only). Expanded while the
// answer is generating, auto-minimizes to a slim bar once it completes (req #3).
// Minimal Reasoning Terminal
// "Thought for 4.2s" / "Thought for 22s" / "Thought for 1m 5s" - from the server's
// measured elapsed_ms, so the number is fixed once the answer lands.
function fmtThought(ms) {
  if (ms == null || !isFinite(ms)) return "";
  const s = ms / 1000;
  if (s < 10) return `${Math.max(0.1, s).toFixed(1)}s`;
  if (s < 60) return `${Math.round(s)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

// Plain speakable text: no markdown, no [COMPUTED] tags, no tables; capped so gTTS stays fast.
function spokenTextOf(msg) {
  const raw = (msg?.showAlt && msg?.altText) ? msg.altText : (msg?.text || "");
  const lines = raw.split("\n")
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("|") && !/^([-*_]\s?){3,}$/.test(l))
    .map((l) => l.replace(/^\[(COMPUTED|VERIFIED|INFERRED)\]\s*/, "")
                 .replace(/\*\*|__|`|#+\s*/g, "")
                 .replace(/^[\-*•]\s+/, "")
                 .replace(/^(\d+)[.)]\s+/, "$1. "));
  let out = "";
  for (const l of lines) {
    if (out.length >= 600) break;
    out += (out ? ". " : "") + l.replace(/[.,?]$/, "");
  }
  return out.length > 600 ? out.substring(0, 600) : out;
}
// ── Listen to answer ─────────────────────────────────────────────────────────
// Synthesis is a ~3s round trip, and the button used to give no sign it had been pressed —
// so it looked broken, and a second click started a second request that could play over
// the first. Now: one shared player, a visible loading → playing state any button can
// subscribe to, a click on a loading or playing answer cancels it, audio is cached so a
// replay is instant, and hovering the button starts the fetch before the click lands.
const TTS_CACHE_MAX = 24;
const _ttsCache = new Map();                    // key -> Promise<objectURL>
const _ttsSubs = new Set();
let _ttsState = { key: "", phase: "idle" };     // phase: idle | loading | playing
let _ttsAudio = null;
let _ttsToken = 0;                              // bumps on every start/stop; stale loads bail

const ttsKey = (text, lang) => `${lang === "kn" ? "kn" : "en"}:${text}`;

function _ttsSet(key, phase) {
  _ttsState = { key, phase };
  _ttsSubs.forEach((fn) => fn(_ttsState));
}

function useTtsPhase(key) {
  const [s, setS] = useState(_ttsState);
  useEffect(() => { _ttsSubs.add(setS); return () => { _ttsSubs.delete(setS); }; }, []);
  return s.key === key ? s.phase : "idle";
}

function fetchTts(text, lang, apiBase = "") {
  const key = ttsKey(text, lang);
  if (!_ttsCache.has(key)) {
    const p = fetch(`${apiBase}/api/voice/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang: lang === "kn" ? "kn" : "en" }),
    })
      .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(`TTS ${r.status}`))))
      .then((b) => URL.createObjectURL(b));
    p.catch(() => _ttsCache.delete(key));       // a failure must not poison the cache
    _ttsCache.set(key, p);
    if (_ttsCache.size > TTS_CACHE_MAX) {
      const oldest = _ttsCache.keys().next().value;
      _ttsCache.get(oldest)?.then((u) => URL.revokeObjectURL(u)).catch(() => {});
      _ttsCache.delete(oldest);
    }
  }
  return _ttsCache.get(key);
}

function stopTts() {
  _ttsToken++;
  if (_ttsAudio) { try { _ttsAudio.pause(); } catch {} _ttsAudio = null; }
  _ttsSet("", "idle");
}

async function speakAnswer(text, lang, apiBase = "") {
  const key = ttsKey(text, lang);
  if (_ttsState.key === key && _ttsState.phase !== "idle") { stopTts(); return false; }  // toggle off
  stopTts();
  if (!text || !text.trim()) return false;
  const token = ++_ttsToken;
  _ttsSet(key, "loading");
  try {
    const url = await fetchTts(text, lang, apiBase);
    if (token !== _ttsToken) return false;      // cancelled, or another answer started
    const audio = new Audio(url);
    const done = () => { if (_ttsAudio === audio) { _ttsAudio = null; _ttsSet("", "idle"); } };
    audio.onended = done;
    audio.onerror = done;
    _ttsAudio = audio;
    await audio.play();
    if (token === _ttsToken) _ttsSet(key, "playing");
    return true;
  } catch (e) {
    console.warn("TTS unavailable", e);
    if (token === _ttsToken) _ttsSet("", "idle");
    return false;
  }
}

// The speaker button: shows loading / playing, and prefetches on approach.
function ListenButton({ text, lang, kn }) {
  const key = ttsKey(text, lang);
  const phase = useTtsPhase(key);
  const title = phase === "loading" ? (kn ? "ಧ್ವನಿ ಸಿದ್ಧವಾಗುತ್ತಿದೆ… (ನಿಲ್ಲಿಸಲು ಒತ್ತಿ)" : "Preparing audio… (click to cancel)")
    : phase === "playing" ? (kn ? "ನಿಲ್ಲಿಸಿ" : "Stop")
    : (kn ? "ಉತ್ತರವನ್ನು ಆಲಿಸಿ" : "Listen to answer");
  return (
    <button type="button" className={phase !== "idle" ? `on tts-${phase}` : ""}
            title={title} aria-label={title} aria-busy={phase === "loading"}
            onPointerEnter={() => { if (text?.trim()) fetchTts(text, lang, API).catch(() => {}); }}
            onFocus={() => { if (text?.trim()) fetchTts(text, lang, API).catch(() => {}); }}
            onClick={() => speakAnswer(text, lang, API)}>
      {phase === "loading" ? <Loader2 size={14} className="tts-spin" />
        : phase === "playing" ? <Square size={12} />
        : <Volume2 size={14} />}
    </button>
  );
}

// Reveals streamed steps one at a time (SSE often delivers several in one burst), so the
// Expert view reads as a thought process rather than a list that pops in whole.
function useStagger(count, active, stepMs = 220) {
  const [shown, setShown] = useState(active ? 0 : count);
  useEffect(() => {
    if (!active) { setShown(count); return; }
    if (shown >= count) return;
    const t = setTimeout(() => setShown((n) => Math.min(count, n + 1)), shown === 0 ? 60 : stepMs);
    return () => clearTimeout(t);
  }, [count, active, shown, stepMs]);
  return shown;
}

function ReasoningTerminal({ msg, kn, send, deepThink }) {
  const [open, setOpen] = useState(false);
  const [now, setNow] = useState(Date.now());
  const steps = msg.steps || [];
  const shown = useStagger(steps.length, !!msg.streaming);

  // Live elapsed counter while thinking (display only; the final number is server-measured).
  useEffect(() => {
    if (!msg.streaming) return;
    const t = setInterval(() => setNow(Date.now()), 100);
    return () => clearInterval(t);
  }, [msg.streaming]);

  useEffect(() => {
    const checkExplain = () => {
      const p = sessionStorage.getItem("antar_initial_query");
      if (p) {
        sessionStorage.removeItem("antar_initial_query");
        setTimeout(() => {
          if (send) send(p);
        }, 350);
      }
    };
    checkExplain();
  }, [send]);

  const stepLabel = (s) => s.label || s.step || s.agent;
  const StepAgent = ({ id }) => {
    const face = AGENT_FACE[String(id || "").toLowerCase()];
    return (
      <span className="ag">
        {face && <i className="wa-face" aria-hidden="true" style={{ backgroundImage: `url(/mascots/sm/${face}-directions.webp)` }} />}
        {id}
      </span>
    );
  };
  const liveSecs = ((now - (msg.ts || now)) / 1000).toFixed(1);

  if (msg.streaming) {
    const visible = steps.slice(0, shown);
    const current = visible[visible.length - 1];
    if (!deepThink) {
      // Standard mode: one quiet live line - the step currently running.
      return (
        <div className="cx-think" aria-live="polite">
          <div className="cx-think-live">
            <Orb agent={current?.agent} label={current ? stepLabel(current) : "Thinking"} />
            <span className="cx-think-faces" aria-hidden="true">
              {[...new Set(visible.map((v) => String(v.agent || "").toLowerCase()))].filter((a) => AGENT_FACE[a]).map((a) => (
                <i key={a} className="wa-face" title={a} style={{ backgroundImage: `url(/mascots/sm/${AGENT_FACE[a]}-directions.webp)` }} />
              ))}
            </span>
            <span key={current ? stepLabel(current) : "start"} className="lbl">
              {current ? stepLabel(current) : (kn ? "ಯೋಚಿಸುತ್ತಿದೆ…" : "Thinking…")}
            </span>
          </div>
        </div>
      );
    }
    // Expert mode: the thought process, one step at a time.
    return (
      <div className="cx-think" aria-live="polite">
        <div className="cx-think-head live">
          <Orb agent={current?.agent} label={kn ? "ಯೋಚಿಸುತ್ತಿದೆ" : "Thinking"} />
          <span>{kn ? "ಯೋಚಿಸುತ್ತಿದೆ" : "Thinking"}</span>
          <span className="t">{liveSecs}s</span>
        </div>
        <ol className="cx-think-steps">
          {visible.map((s, i) => {
            const running = s.status === "running" || (i === visible.length - 1 && s.status !== "done");
            return (
              <li key={`${s.agent}-${i}`} className={running ? "running" : "done"}>
                <span className="dot" aria-hidden="true" />
                <StepAgent id={s.agent} />
                <span className="tx">{stepLabel(s)}</span>
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  const reasoning = msg.reasoning || [];
  if (steps.length === 0 && reasoning.length === 0) return null;
  const took = fmtThought(msg.thoughtMs);

  return (
    <div className="cx-think">
      <button type="button" className="cx-think-head" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <span>{took ? (kn ? `${took} ಯೋಚಿಸಿದೆ` : `Thought for ${took}`) : (kn ? "ಚಿಂತನೆ" : "Thought process")}</span>
        <span className="chev" aria-hidden="true">›</span>
      </button>
      {open && (
        <ol className="cx-think-steps">
          {steps.map((s, i) => (
            <li key={`s-${i}`} className="done">
              <span className="dot" aria-hidden="true" />
              <StepAgent id={s.agent} />
              <span className="tx">{stepLabel(s)}</span>
            </li>
          ))}
          {reasoning.map((r, i) => (
            <li key={`r-${i}`} className="detail">
              <span className="dot" aria-hidden="true" />
              <span className="tx">{r.detail || r.step || ""}</span>
            </li>
          ))}
        </ol>
      )}
      {(() => {
        // Who worked on the answer. The second half is what the pipeline does to every
        // answer before it is shown (the numbers and identifiers in it are checked against
        // the rows it was written from), stated once, plainly.
        const who = [...new Set(steps.map((x) => String(x.agent || "").toLowerCase()))].filter((a) => AGENT_FACE[a]);
        if (!who.length) return null;
        return (
          <p className="cx-think-check">
            {who.map((a) => <i key={a} className="wa-face" title={a} style={{ backgroundImage: `url(/mascots/sm/${AGENT_FACE[a]}-directions.webp)` }} />)}
            <span>{kn ? `${who.length} ಏಜೆಂಟ್‌ಗಳು ಕೆಲಸ ಮಾಡಿವೆ`
              : `${who.length} ${who.length === 1 ? "agent" : "agents"} worked on this`}</span>
          </p>
        );
      })()}
    </div>
  );
}

function fmtTime(ts) {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}

// Parse "YYYY-MM: N ..." fact lines into sparkline points - real trend data only.
function trendPoints(facts) {
  const pts = [];
  for (const f of facts || []) {
    const m = /^(\d{4}-\d{2}):\s*(\d+)/.exec(String(f).trim());
    if (m) pts.push({ label: m[1], n: parseInt(m[2], 10) });
  }
  return pts.length >= 3 ? pts : null;
}

// Inline SVG sparkline (no chart dependency) - NEO-style data row.
function Sparkline({ points }) {
  const W = 220, H = 44, pad = 4;
  const ns = points.map((p) => p.n);
  const max = Math.max(...ns, 1), min = Math.min(...ns, 0), rng = max - min || 1;
  const x = (i) => pad + (i / (points.length - 1)) * (W - 2 * pad);
  const y = (v) => H - pad - ((v - min) / rng) * (H - 2 * pad);
  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.n).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="nx-spark" aria-hidden="true">
      <path d={`M${x(0)},${H - pad} ${points.map((p, i) => `L${x(i).toFixed(1)},${y(p.n).toFixed(1)}`).join(" ")} L${x(points.length - 1)},${H - pad} Z`}
            fill="rgba(34,230,240,0.10)" />
      <path d={line} fill="none" stroke="var(--cyan)" strokeWidth="1.8" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

// NEO "Sources" panel: clickable FIR source cards + real data row (stat chips
// and, for trend answers, an inline sparkline with the period-over-period move).
function SourcesPanel({ msg, kn, router }) {
  const cites = (msg.citations || []).slice(0, 3);
  const stats = msg.layout?.stats || [];
  const pts = trendPoints(msg.layout?.facts);
  if (!cites.length && !stats.length && !pts) return null;
  const first = pts?.[0]?.n, last = pts?.[pts.length - 1]?.n;
  const delta = pts && first > 0 ? Math.round(((last - first) / first) * 100) : null;
  const ct = stats.find((s) => s.label === "crime type")?.value;
  return (
    <div className="nx-sources">
      <div className="nx-sources-h">{kn ? "ಮೂಲಗಳು" : "Sources"}</div>
      {cites.length > 0 && (
        <div className="nx-srcgrid">
          {cites.map((c, j) => (
            <button type="button" className="nx-srccard" key={j}
                    onClick={() => router.push(c.id ? `/case/${encodeURIComponent(c.id)}` : `/search?q=${encodeURIComponent(c.fir || "")}`)}
                    title={c.id ? (kn ? "ಪ್ರಕರಣದ ಕಾಲರೇಖೆ ತೆರೆಯಿರಿ" : "Open the case: summary and timeline") : (kn ? "ಮೂಲ ದಾಖಲೆ ಹುಡುಕಿ" : "Open this record in Search")}>
              <b>FIR {c.fir}</b>
              <span>{[c.station, c.section].filter(Boolean).join(" · ")}</span>
              <i>{c.date || ""}{c.date ? " · " : ""}{kn ? "ಮೂಲ ದಾಖಲೆ" : "Source record"} →</i>
            </button>
          ))}
        </div>
      )}
      {(pts || stats.length > 0) && (
        <div className="nx-datarow">
          {pts ? (
            <>
              <div className="nx-datalabel">
                <b>{ct || (kn ? "ಪ್ರವೃತ್ತಿ" : "Trend")}</b>
                <span>{pts.length} {kn ? "ತಿಂಗಳು" : "months"}</span>
              </div>
              <Sparkline points={pts} />
              {delta !== null && (
                <span className={`nx-delta ${delta <= 0 ? "down" : "up"}`}>{delta > 0 ? "+" : ""}{delta}%</span>
              )}
              <span className="nx-dataval">{last} {kn ? "ಪ್ರಕರಣ" : "cases"}</span>
            </>
          ) : (
            <div className="cx-statrow" style={{ marginTop: 0 }}>
              {stats.map((s, j) => (
                <span className="cx-statchip" key={j} style={{ animationDelay: `${j * 70}ms` }}>
                  <b>{s.value}</b><i>{s.label}</i>
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const AGENT_MAP = {
  query: "Vault",
  network: "Link",
  profile: "Motive",
  forecast: "Core",
  social: "Sense",
  research: "Trace",
  synthesize: "Synthesize",
  router: "Router"
};

// Live terminal agent status: surfaces the CURRENT pipeline step streamed by
// the backend - "Searching crime database...", "Composing answer..." - with animated
// terminal spinner and neon status glow.
function AgentStatusLine({ msg, kn }) {
  const spinner = useTerminalSpinner(msg.streaming);
  const running = [...msg.steps].reverse().find((s) => s.status === "running");
  const lastDone = [...msg.steps].reverse().find((s) => s.status === "done");
  const step = running || lastDone;
  const rawAgent = step?.agent || "router";
  const mappedAgent = AGENT_MAP[rawAgent.toLowerCase()] || rawAgent.charAt(0).toUpperCase() + rawAgent.slice(1);
  const label = step ? formatStepLabel(step, kn) : (kn ? "ಪ್ರಶ್ನೆಯನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳುತ್ತಿದೆ..." : "Understanding the query...");

  return (
    <div className="cx-statusline animated-term-status" role="status" aria-live="polite">
      <span className="term-spinner">{msg.streaming ? spinner : "\u2713"}</span>
      <span className="agent">using {mappedAgent}</span>
      <span className="lbl" key={`${rawAgent}·${label}`}>{label}</span>
      {msg.streaming && <span className="cx-cursor" />}
    </div>
  );
}

// Click-to-expand section for secondary content (req #17 - minimized by default).
function Collapse({ title, tone = "cyan", defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`cx-collapse ${tone}`}>
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span>{title}</span>
        <span className="chev">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="cx-collapse-body">{children}</div>}
    </div>
  );
}

// Chain-of-custody strip - evidentiary provenance of a factual answer.
// Collapsed by default (owner choice): one scannable line; expands to the FIR list.
function CustodyStrip({ custody, kn }) {
  if (!custody || !custody.record_count) return null;
  const firs = custody.firs || [];
  const extra = (custody.fir_total || firs.length) - firs.length;
  const summary = (
    <span className="cx-custody-sum">
      <span className="cx-custody-k" title={kn ? "ದಾಖಲೆಗಳಿಂದ ಪರಿಶೀಲಿಸಲಾಗಿದೆ" : "Checked against the FIR records, not written by the AI"}>✓</span>
      <b>{custody.record_count.toLocaleString()}</b> {kn ? "ದಾಖಲೆ" : custody.record_count === 1 ? "record" : "records"}
      <i>·</i> {custody.source === "crimes" || !custody.source ? (kn ? "FIR ದಾಖಲೆಗಳು" : "FIR records") : custody.source}
      <i>·</i> {kn ? "ದಿನಾಂಕದವರೆಗೆ" : "as of"} {custody.as_of}
    </span>
  );
  return (
    <div className="cx-custody">
      <Collapse title={<>{kn ? "ಸಾಕ್ಷ್ಯ ಸರಪಳಿ" : "Evidence"} - {summary}</>}>
        <div className="cx-custody-body">
          {custody.range && (
            <div className="row"><span className="lab">{kn ? "ಅವಧಿ" : "Period"}</span><span>{custody.range}</span></div>
          )}
          <div className="row"><span className="lab">{kn ? "ವಿಧಾನ" : "Method"}</span><span className="mono">{custody.method}</span></div>
          {firs.length > 0 && (
            <div className="row"><span className="lab">FIR</span>
              <span className="cx-custody-firs">
                {firs.map((f, i) => <code key={i}>{f}</code>)}
                {extra > 0 && <span className="more">+{extra} {kn ? "ಇನ್ನಷ್ಟು" : "more"}</span>}
              </span>
            </div>
          )}
        </div>
      </Collapse>
    </div>
  );
}

// (?) helper for non-self-evident components (req #14).
function HelpDot({ text }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="cx-helpdot" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" aria-label="What is this?" onClick={() => setOpen((v) => !v)}>?</button>
      {open && <span className="tip" role="tooltip">{text}</span>}
    </span>
  );
}

function applyEvent(msg, evt) {
  switch (evt.type) {
    case "step": {
      const steps = [...msg.steps];
      const i = steps.findIndex((s) => s.agent === evt.agent);
      const step = { agent: evt.agent, status: evt.status, label: evt.label };
      if (i >= 0) steps[i] = step; else steps.push(step);
      return { ...msg, steps };
    }
    case "token":
      return { ...msg, text: msg.text + evt.content };
    case "citations":
      return { ...msg, citations: evt.data || [] };
    case "brain_hits":
      return { ...msg, brainHits: evt.data || [], brainBanner: evt.banner || msg.brainBanner };
    case "visual":
      return { ...msg, visuals: { ...msg.visuals, [evt.key]: evt.data } };
    case "confidence":
      return { ...msg, confidence: { routing: evt.routing, answer: evt.answer, label: evt.label } };
    case "actions":
      return { ...msg, actions: evt.data || [] };
    case "suggested":
      return { ...msg, suggested: evt.data || [] };
    case "layout":
      return { ...msg, layout: evt.data || null };
    case "custody":
      return { ...msg, custody: evt.data || null };
    case "complete":
      return {
        ...msg,
        streaming: false,
        lang: evt.lang || msg.lang,
        suspects: evt.suspects || [],
        template: evt.template_id,
        reasoningId: evt.reasoning_id || null,
        reasoning: evt.reasoning || [],
        noResults: !!evt.no_results,
        thoughtMs: typeof evt.elapsed_ms === "number" ? evt.elapsed_ms : Date.now() - (msg.ts || Date.now()),
        auditHash: evt.audit_hash || null,
        traceId: evt.trace_id || null,   // opens this answer on the Observability & Trace page
        // Provenance for the Expert workspace's Sources block.
        method: evt.method || msg.method || null,
        rowCount: typeof evt.rows === "number" ? evt.rows : msg.rowCount,
        agents: evt.agents_used || msg.agents || [],
        mode: evt.mode || msg.mode || null,
        confidence: typeof evt.confidence === "number" ? evt.confidence : msg.confidence,
      };
    case "error":
      return { ...msg, streaming: false, error: true, text: msg.text || evt.message || "" };
    default:
      return msg;
  }
}



// ── Antar response template (docs/ANTAR_CONSTITUTION.md §5) ─────────────────────
// Bottom line → context → evidence, then Sources and Limits folded one tap away, then one
// next step. Rendered from `layout.sections`, which the backend builds for EVERY answer —
// LLM-written or deterministic - so the shape never depends on which path answered.
const CLASS_HELP = {
  K: "From the records: read directly from FIRs",
  D: "Calculated: worked out from FIRs (shares, rates, rankings, trends)",
  I: "Estimate: Antar's judgement, with the reason given",
  U: "Not on record: the information needed is missing",
};

// " — 62 (1%)": the count is the fact; the share in brackets is secondary, so it is muted.
function RankTail({ text }) {
  const m = String(text).match(/^(.*?)(\s*\([^)]*%[^)]*\))(.*)$/);
  if (!m) return <MdInline text={text} />;
  return <><MdInline text={m[1]} /><span className="ax-t-share">{m[2]}</span>{m[3] && <MdInline text={m[3]} />}</>;
}

// "Beat No 3 · Byadarahalli PS — 62 (1%)" -> ["Beat No 3 · Byadarahalli PS", " — 62 (1%)"].
// Rows without a " — <number>" tail are left whole.
function splitRankRow(t) {
  const m = String(t).match(/^(.+?)(\s+[—–-]\s+[\d,]+.*)$/);
  return m && !/\*\*/.test(m[1]) ? [m[1], m[2]] : [t, null];
}

// The first question from the landing screen: it rises from the chat box to the middle of
// the screen in large type, over the thinking orb, with the step the agents are on under it.
// It stays until the answer has something to show, then drifts up and away as the answer
// arrives. Reduced motion: a cross-fade only.
function LaunchStage({ q, msg, kn, onStop }) {
  const reduce = useReducedMotion();
  const running = [...(msg?.steps || [])].reverse().find((st) => st.status === "running");
  const label = running ? (running.label || running.step || running.agent) : (kn ? "ಯೋಚಿಸುತ್ತಿದೆ…" : "Thinking…");
  const qIn = reduce ? { opacity: 0 } : { opacity: 0, y: 170, scale: 0.92, filter: "blur(6px)" };
  const qOut = reduce ? { opacity: 0 } : { opacity: 0, y: -40, filter: "blur(4px)" };
  return (
    <motion.div className="cx-launch" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.35, ease: "easeOut" } }} transition={{ duration: 0.25 }}>
      <div className="cx-launch-orb" aria-hidden="true"><Orb agent={running?.agent} size={64} /></div>{/* the orb comes in 64/32/20 only; CSS enlarges it */}
      <motion.h2 className="cx-launch-q" initial={qIn} animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }} exit={qOut}
        transition={reduce ? { duration: 0.2 } : { type: "spring", bounce: 0, duration: 0.7 }}>
        {q}
      </motion.h2>
      <div className="cx-launch-step" role="status" aria-live="polite">
        <AnimatePresence mode="wait" initial={false}>
          <motion.span key={label} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.22 }}>{label}</motion.span>
        </AnimatePresence>
      </div>
      <button type="button" className="cx-launch-stop" onClick={onStop}>{kn ? "ನಿಲ್ಲಿಸಿ" : "Stop"}</button>
    </motion.div>
  );
}

function TemplateAnswer({ m, kn, send, router }) {
  const s = m.layout.sections;
  const [open, setOpen] = useState(null);          // "sources" | "limits" | null
  const [all, setAll] = useState(false);
  const cls = m.layout.evidence_class;
  const ev = (s.evidence || []).filter(Boolean);
  const isTable = ev.some((e) => e.trim().startsWith("|"));
  const shown = all || isTable ? ev : ev.slice(0, 10);
  const nSrc = (m.citations || []).length;
  const nLim = (s.limits || []).length;
  const toggle = (k) => setOpen((o) => (o === k ? null : k));
  return (
    <div className={`ax-t ax-t-${m.layout.kind || "answer"}`}>
      <div className="ax-t-head">
        <div className="ax-t-bottom"><MdInline text={s.bottom_line} /></div>
        {cls && (
          <span className={`ax-badge ax-badge-${cls}`} title={CLASS_HELP[cls]}>
            {m.layout.evidence_label || cls}
          </span>
        )}
      </div>
      {(s.context || []).map((c, j) => (
        <div key={j} className="ax-t-context"><MdInline text={c} /></div>
      ))}
      {shown.length > 0 && (isTable
        ? <div className="ax-t-evidence"><AnswerBody text={ev.join("\n")} streaming={false} /></div>
        : (
          <div className="ax-t-evidence">
            {shown.map((e, j) => {
              const isSub = /:\s*$/.test(e);
              const numMatch = e.match(/^(\d+\.)\s*(.*)$/);
              if (numMatch) {
                // A ranked row reads "Beat No 3 · Byadarahalli PS — 62 (1%)": the name is what an
                // officer acts on, so it is set in strong type; the first row is the answer itself.
                const [name, rest] = splitRankRow(numMatch[2]);
                return (
                  <div key={j} className={`ax-t-row ax-t-rank${numMatch[1] === "1." ? " ax-t-top" : ""}`} style={{ display: "flex", gap: "10px", paddingLeft: "4px" }}>
                    <span style={{ color: "var(--cyan)", fontWeight: 600, minWidth: "20px", textAlign: "right", flexShrink: 0, fontFamily: "'Chakra Petch', sans-serif" }}>{numMatch[1]}</span>
                    <span style={{ flex: 1 }}>
                      {rest != null ? <><span className="ax-t-name"><MdInline text={name} /></span><RankTail text={rest} /></> : <MdInline text={numMatch[2]} />}
                    </span>
                  </div>
                );
              }
              const bulletMatch = e.match(/^[•\-*]\s+(.*)$/);
              if (bulletMatch) {
                return (
                  <div key={j} className="ax-t-row" style={{ display: "flex", gap: "10px", paddingLeft: "4px" }}>
                    <span style={{ color: "var(--cyan)", flexShrink: 0, fontSize: "14px", lineHeight: "1.4" }}>•</span>
                    <span style={{ flex: 1 }}><MdInline text={bulletMatch[1]} /></span>
                  </div>
                );
              }
              return <div key={j} className={isSub ? "ax-t-sub" : "ax-t-row"}><MdInline text={e} /></div>;
            })}
          </div>
        ))}
      {!isTable && ev.length > 10 && !all && (
        <button type="button" className="ax-t-more" onClick={() => setAll(true)}>
          {kn ? `ಎಲ್ಲಾ ${ev.length} ತೋರಿಸಿ` : `Show all ${ev.length}`}
        </button>
      )}
      {(nSrc > 0 || nLim > 0) && (
        <div className="ax-t-folds">
          {nSrc > 0 && (
            <button type="button" aria-expanded={open === "sources"} onClick={() => toggle("sources")}>
              <span aria-hidden="true">{open === "sources" ? "▾" : "▸"}</span> {kn ? "ಮೂಲಗಳು" : "Sources"} <em>{nSrc}</em>
            </button>
          )}
          {nLim > 0 && (
            <button type="button" aria-expanded={open === "limits"} onClick={() => toggle("limits")}>
              <span aria-hidden="true">{open === "limits" ? "▾" : "▸"}</span> {kn ? "ಮಿತಿಗಳು" : "Limits"} <em>{nLim}</em>
            </button>
          )}
        </div>
      )}
      {open === "sources" && <SourcesPanel msg={m} kn={kn} router={router} />}
      {open === "limits" && (
        <div className="ax-t-limits">
          {s.limits.map((l, j) => <div key={j}><MdInline text={l.replace(/^(?:note|ಗಮನಿಸಿ)\s*:\s*/i, "")} /></div>)}
        </div>
      )}
      {s.next_step && (
        <button type="button" className="ax-t-next" onClick={() => send(s.next_step)}>
          <span className="lab">{kn ? "ಮುಂದೆ" : "Next"}</span> {s.next_step}
        </button>
      )}
    </div>
  );
}

const MessageRow = memo(({
  m, i, prevMessage, kn, lang, deepThink, sessionId,
  router, send, setMessages, showNetwork, exportReport,
  translateAnswer, rateAnswer, toggleWhy
}) => {
    GLOBAL_HL_COUNT = 0;
  // Verdict-first, but don't hide the substance: a record-set answer IS a table
  // (show it), and a short verdict ≈ the whole answer (no pointless toggle). Only
  // collapse to a headline-summary when there's genuinely more prose/facts below.
  const _hasTable = /\n\s*\|[^\n]*\|/.test(m.text || "");
  const _fullLen = (m.text || "").replace(/\s+/g, " ").trim().length;
  const _headLen = (m.layout?.headline || "").length;
  const _hasFacts = (m.layout?.facts?.length || 0) > 0 || !!m.layout?.chart;
  const worthSummary = !_hasTable && !!m.layout?.headline && (_hasFacts || _fullLen > _headLen + 80);
  return (
              <div key={i} className={`cx-row cx-row-${m.role}`} data-row={i} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {m.role === "user" ? (
                  <div style={{ display: "flex", justifyContent: "flex-end", width: "100%", margin: "6px 0" }}>
                    <div style={{
                      background: "rgba(25, 28, 38, 0.82)",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      borderRadius: "18px",
                      padding: "12px 18px",
                      color: "#F8FAFC",
                      fontSize: "15px",
                      lineHeight: 1.55,
                      maxWidth: "76%",
                      fontFamily: "'Inter', sans-serif"
                    }}>
                      {m.text}
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", width: "100%", margin: "8px 0" }}>
                    {/* Minimal reasoning terminal for all modes */}
                    <ReasoningTerminal msg={m} kn={kn} send={send} deepThink={deepThink} />
                    {m.streaming && !m.text ? null : (
                      <div className={`cx-card ${m.error ? "cx-error" : ""} ${m.lang === "kn" ? "kn" : ""}`}>
                        {m.streaming && <div className="cx-card-sp" />}
                        {m.showAlt && m.altText ? (
                          <div className="cx-ans">
                            <div className="cx-tr-banner">
                              {(m.altLang === "kn") ? "ಕನ್ನಡದಲ್ಲಿ ಅನುವಾದಿಸಲಾಗಿದೆ" : "Translated to English"}
                            </div>
                            <AnswerBody text={m.altText} streaming={false} headline={m.layout?.headline} />
                          </div>
                        ) : !m.streaming && m.layout?.sections?.bottom_line ? (
                          <TemplateAnswer m={m} kn={kn} send={send} router={router} />
                        ) : worthSummary && !m.showFull ? (
                          <div className="cx-structured">
                            <div className="cx-headrow">
                              {m.layout.kdiu?.some((k) => k.tag === "K") && <span className="cx-badge-k">K · Verified</span>}
                              <span className="cx-headline"><MdInline text={m.layout.headline} /></span>
                            </div>
                            {(m.layout.facts || []).slice(0, 6).map((f, j) => (
                              <div key={j} className="cx-line cx-line-rise" style={{ animationDelay: `${j * 60}ms` }}><MdInline text={f} /></div>
                            ))}
                            <button type="button" className="cx-showfull" onClick={() =>
                              setMessages((ms) => ms.map((x, j) => (j === i ? { ...x, showFull: true } : x)))
                            }>
                              {kn ? "ಪೂರ್ಣ ಉತ್ತರ ತೋರಿಸಿ" : "Show full answer"}
                            </button>
                          </div>
                        ) : (
                          <div className="cx-ans">
                            {/* Make sure the headline + badge is rendered even in full mode if it exists */}
                            {m.layout?.headline && (
                              <div className="cx-headrow" style={{ marginBottom: "12px" }}>
                                {m.layout.kdiu?.some((k) => k.tag === "K") && <span className="cx-badge-k">K · Verified</span>}
                                <span className="cx-headline"><MdInline text={m.layout.headline} /></span>
                              </div>
                            )}
                            <AnswerBody text={m.text} streaming={m.streaming} headline={m.layout?.headline} />
                            {!m.streaming && worthSummary && m.showFull && (
                              <button type="button" className="cx-showfull" onClick={() =>
                                setMessages((ms) => ms.map((x, j) => (j === i ? { ...x, showFull: false } : x)))
                              }>
                                {kn ? "ಸಾರಾಂಶ ತೋರಿಸಿ" : "Show summary"}
                              </button>
                            )}
                          </div>
                        )}
                        {/* Real aggregate data - render in BOTH the summary and full views,
                            otherwise a short answer (no summary branch) silently drops it. */}
                        {!m.streaming && !m.showAlt && m.layout?.chart && (
                          <MiniChart chart={m.layout.chart} kn={kn} />
                        )}
                        {!m.streaming && !m.noResults && !m.layout?.sections?.bottom_line && (
                          <SourcesPanel msg={m} kn={kn} router={router} />
                        )}
                        {m.vigil && m.vigil.status !== "APPROVED" && (
                          <div style={{
                            marginTop: "10px", padding: "8px 12px", borderRadius: "6px",
                            background: m.vigil.status === "REJECTED" ? "rgba(255,56,56,0.15)" : "rgba(245,166,35,0.15)",
                            border: `1px solid ${m.vigil.status === "REJECTED" ? "#ff3838" : "#f5a623"}`,
                            fontSize: "12px", color: "#fff"
                          }}>
                            <b style={{ color: m.vigil.status === "REJECTED" ? "#ff6b6b" : "#f5a623" }}>
                              {m.vigil.status === "REJECTED" ? (kn ? "ದುರ್ಬಳಕೆ ತಪಾಸಣೆ: ತಡೆಯಲಾಗಿದೆ" : "Misuse check: blocked")
                                : (kn ? "ದುರ್ಬಳಕೆ ತಪಾಸಣೆ: ಗಮನಿಸಿ" : "Misuse check: please review")}
                            </b>
                            <p style={{ margin: "4px 0", fontSize: "11px", color: "#ddd" }}>{m.vigil.explanation}</p>
                          </div>
                        )}
                        {m.vigil && m.vigil.status === "APPROVED" && !m.streaming && (
                          <Collapse title={kn ? "ದುರ್ಬಳಕೆ ತಪಾಸಣೆ: ಸರಿಯಾಗಿದೆ" : "Misuse check: passed"}>
                            <p style={{ margin: "4px 0", fontSize: "12px", color: "#cbd5e1" }}>{m.vigil.explanation}</p>
                            <div style={{ fontSize: "11px", color: "#8fa3bd" }}>{kn ? "ಕಾನೂನು" : "Law"}: <b style={{ color: "var(--cyan)" }}>{m.vigil.bnss_citation}</b>{m.vigil.receipt_id ? <span style={{ opacity: 0.6 }}> · {kn ? "ಉಲ್ಲೇಖ" : "ref"} {m.vigil.receipt_id}</span> : null}</div>
                          </Collapse>
                        )}
                        {m.error && m.retryText && (
                          <div className="cx-acts">
                            <button className="cx-act" onClick={() => send(m.retryText)}>↻ {kn ? "ಮರುಪ್ರಯತ್ನಿಸಿ" : "Retry"}</button>
                          </div>
                        )}
                        {/* User pressed Stop: partial output kept, clearly marked, one clear next move. */}
                        {m.stopped && (
                          <div className="cx-stopped" style={{ marginTop: (!m.text && !m.layout) ? "6px" : undefined }}>
                            <span className="lab">
                              {!m.text
                                ? (kn ? "ಉತ್ತರ ರಚನೆ ನಿಲ್ಲಿಸಲಾಗಿದೆ" : "Stopped before answer generated")
                                : (kn ? "ನಿಲ್ಲಿಸಲಾಗಿದೆ - ಭಾಗಶಃ ಉತ್ತರ" : "Stopped - partial answer")}
                            </span>
                            {m.retryText && (
                              <button className="cx-act" onClick={() => send(m.retryText)}>
                                ↻ {kn ? "ಮತ್ತೆ ರಚಿಸಿ" : "Regenerate"}
                              </button>
                            )}
                          </div>
                        )}
                        {!m.noResults && m.confidence && !m.layout?.evidence_class && (
                          <div className="cx-conf">
                            <span className="lab">{m.confidence.label || (kn ? "ವಿಶ್ವಾಸ" : "Confidence")}</span>
                            <span className="track"><span className="fill" style={{ width: `${Math.round((m.confidence.answer ?? m.confidence.routing ?? 0) * 100)}%` }} /></span>
                            <span className="pct">{Math.round((m.confidence.answer ?? m.confidence.routing ?? 0) * 100)}%</span>
                          </div>
                        )}
                        {!m.noResults && !m.streaming && m.custody && (
                          <CustodyStrip custody={m.custody} kn={kn} />
                        )}
                        {!m.noResults && !m.streaming && m.brainBanner && (
                          <Collapse title={kn ? "ಎರಡನೇ ಮೆದುಳು - ಸಂಬಂಧಿತ ಪ್ರಕರಣ" : "Second Brain - related case found"}>
                            <p style={{ margin: "2px 0 6px", fontSize: "12.5px", color: "#cbd5e1", lineHeight: 1.55 }}>{m.brainBanner}</p>
                            {m.suspects?.[0] && (
                              <a style={{ fontFamily: "'Chakra Petch'", fontSize: "11px", color: "var(--amber)", cursor: "pointer" }}
                                 onClick={() => router.push(`/brain/structure?kpi=${encodeURIComponent(m.suspects[0].id || m.suspects[0].name)}`)}>
                                {kn ? "ಮೆದುಳಿನಲ್ಲಿ ವೀಕ್ಷಿಸಿ →" : "View in brain →"}
                              </a>
                            )}
                          </Collapse>
                        )}
                        {!m.noResults && m.suspects?.length > 0 && m.visuals?.graph?.edges?.length >= 2 && (
                          <div className="cx-acts">
                            {m.suspects.map((s, j) => (
                              <button key={j} className="cx-act" onClick={() => showNetwork(s.id, s.name, m.visuals?.graph)}>{kn ? "ಜಾಲ" : "Network"}: {s.name}</button>
                            ))}
                          </div>
                        )}
                        {!m.noResults && m.actions?.length > 0 && (
                          <div className="cx-acts">
                            {m.actions.map((a, j) => {
                              if (a.type === "show_network") {
                                const sid = a.params?.suspect_id;
                                const sname = m.suspects?.find((s) => s.id === sid)?.name || sid;
                                return <button key={j} className="cx-act" onClick={() => showNetwork(sid, sname, m.visuals?.graph)}>{a.label}</button>;
                              }
                              if (a.type === "view_on_map") return null; /* map jump lives in the icon row */
                              if (a.type === "open_profile") {
                                const nm = a.params?.q || m.suspects?.find((s) => s.id === a.params?.suspect_id)?.name || "";
                                return <button key={j} className="cx-act" onClick={() => router.push(searchUrl(nm))}>{a.label} </button>;
                              }
                              if (a.type === "open_pattern") return <button key={j} className="cx-act" onClick={() => router.push("/predict")}>{a.label} </button>;
                              if (a.type === "open_predict") return <button key={j} className="cx-act" onClick={() => router.push("/predict")}>{a.label} </button>;
                              if (a.type === "follow_unknown" || a.type === "track_unknown") {
                                return (
                                  <button key={j} className="cx-act" style={{ borderColor: "#A855F7", color: "#E9D5FF" }} onClick={() => router.push("/search")}>
                                    {a.label || "Follow the unknown lead →"}
                                  </button>
                                );
                              }
                              if (a.type === "navigate") {
                                // legacy backend payloads → new IA
                                const dest = { "/trends": "/predict", "/network": "/brain", "/profiles": "/search" }[a.payload] || a.payload;
                                const url = dest === "/map" ? mapUrl(a.params) : dest === "/search" ? searchUrl(a.params?.q) : dest;
                                return <button key={j} className="cx-act" onClick={() => router.push(url)}>{a.label} </button>;
                              }
                              return null;
                            })}
                          </div>
                        )}
                        {!m.noResults && /\[(GAP|INFERRED|U|I)\]/i.test(m.text || "") && (
                          <div className="cx-acts" style={{ marginTop: 6 }}>
                            <button className="cx-act" style={{ borderColor: "#A855F7", color: "#E9D5FF" }} onClick={() => router.push("/search")}>
                              Follow the unknown lead (Search & Hypothesis) →
                            </button>
                          </div>
                        )}
                        {/* Footer: provenance on the left, actions on the right - inside the
                            card, so they read as part of this answer rather than a stray row. */}
                        {(m.reasoning?.length > 0 || (!m.streaming && m.text && !m.error)) && (
                          <div className="cx-foot">
                            {m.reasoning?.length > 0 ? (
                              <button className="cx-why" aria-expanded={!!m.whyOpen} onClick={() => toggleWhy(i)}>
                                <span aria-hidden="true">{m.whyOpen ? "▾" : "▸"}</span> {kn ? "ಏಕೆ?" : "How this was answered"}
                              </button>
                            ) : <span />}
                            {!m.streaming && m.text && !m.error && (
                      <div className="nx-iconrow" role="toolbar" aria-label={kn ? "ಉತ್ತರ ಕ್ರಿಯೆಗಳು" : "Answer actions"}>
                        {prevMessage?.role === "user" && (
                          <button type="button" title={kn ? "ಮರುರಚಿಸಿ" : "Regenerate answer"} onClick={() => send(prevMessage.text)}>
                            <RefreshCw size={14} />
                          </button>
                        )}
                        <button type="button" title={kn ? "ನಕಲಿಸಿ" : "Copy answer"}
                                onClick={() => { try { navigator.clipboard.writeText(m.text); } catch {} }}>
                          <Copy size={14} />
                        </button>
                        <ListenButton text={spokenTextOf(m)} lang={(m.showAlt ? m.altLang : m.lang) || lang} kn={kn} />
                        {m.traceId && (
                          <button type="button" title={kn ? "ಈ ಉತ್ತರದ ಜಾಡು ನೋಡಿ" : "See how this answer was produced (trace)"}
                                  onClick={() => router.push(`/trace?t=${encodeURIComponent(m.traceId)}`)}>
                            <Activity size={14} />
                          </button>
                        )}
                        {sessionId && (
                          <button type="button" title={kn ? "ವರದಿ ರಫ್ತು" : "Export intelligence report"} onClick={exportReport}>
                            <Download size={14} />
                          </button>
                        )}
                        {m.actions?.some((a) => a.type === "view_on_map") && (
                          <button type="button" title={kn ? "ನಕ್ಷೆಯಲ್ಲಿ ನೋಡಿ" : "View on map"} onClick={() => router.push(mapUrl({}))}>
                            <MapIcon size={14} />
                          </button>
                        )}
                        {m.suspects?.length > 0 && m.visuals?.graph?.nodes?.length > 0 && (
                          <button type="button" title={kn ? "ಜಾಲ ನಕ್ಷೆ" : "Open network graph"}
                                  onClick={() => showNetwork(m.suspects[0].id, m.suspects[0].name, m.visuals?.graph)}>
                            <Network size={14} />
                          </button>
                        )}
                        {m.suspects?.length > 0 && (
                          <button type="button" title={kn ? "ಹುಡುಕಾಟದಲ್ಲಿ ತೆರೆಯಿರಿ" : `Search ${m.suspects[0].name}`}
                                  onClick={() => router.push(searchUrl(m.suspects[0].name))}>
                            <SearchIcon size={14} />
                          </button>
                        )}

                        <button type="button" className={m.rated === "up" ? "on" : ""} disabled={!!m.rated}
                                title={kn ? "ಉತ್ತಮ ಉತ್ತರ" : "Good answer"} onClick={() => rateAnswer(i, "up")}>
                          <ThumbsUp size={14} />
                        </button>
                        <button type="button" className={m.rated === "down" ? "on" : ""} disabled={!!m.rated}
                                title={kn ? "ತಪ್ಪು ಉತ್ತರ" : "Poor answer"} onClick={() => rateAnswer(i, "down")}>
                          <ThumbsDown size={14} />
                        </button>
                      </div>
                            )}
                          </div>
                        )}
                        {m.whyOpen && m.reasoning?.length > 0 && (
                          <div className="cx-why-body">
                            {m.reasoning.map((r, k) => <div key={k}>{k + 1}) {r.detail || r.step}</div>)}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
  );
}, (prev, next) => {
  // Callbacks are NOT compared: the page passes stable wrappers that always call the
  // latest implementation (see `actions` in ChatPage). Comparing them would re-render
  // every row on every streamed token; ignoring them - as this comparator used to, with
  // raw per-render functions - froze each row's buttons on their first-render closures,
  // so Regenerate and Export could act on stale state.
  // sessionId IS compared: the Export button only renders once the session exists, and
  // it usually arrives after the first answer has already been drawn.
  return prev.m === next.m &&
         prev.prevMessage === next.prevMessage &&
         prev.sessionId === next.sessionId &&
         prev.kn === next.kn &&
         prev.lang === next.lang &&
         prev.deepThink === next.deepThink;
});

// Expert mode lives in the composer's toolbar, beside the mic and send, never over the text.
function ExpertSwitch({ on, onToggle, kn }) {
  return (
    <button type="button" className={`cx-expert-toggle ${on ? "on" : ""}`} aria-pressed={on}
            title="Expert - deep multi-agent investigation + workspace"
            onClick={(e) => { e.stopPropagation(); onToggle(); }}
            style={{ padding: "4px 10px", fontSize: "11px" }}>
      {kn ? "ತಜ್ಞ" : "Expert"}
    </button>
  );
}

export default function ChatPage() {
  const router = useRouter();
  const liveTriggeredRef = useRef(false);
  const { lang } = useLang();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const abortControllerRef = useRef(null);
  // Distinguishes a DELIBERATE stop from a real failure. Without it the AbortError
  // lands in the generic catch, which (a) flagged a user-initiated stop as an error
  // and (b) worse, re-sent the very request the officer just cancelled via the
  // non-stream fallback. A stop must preserve partial output and stop, full stop.
  const abortedRef = useRef(false);
  const stopChat = () => {
    abortedRef.current = true;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
  };
  const [isFocus, setIsFocus] = useState(false);
  const [atBottom, setAtBottom] = useState(true);   // scroll discipline (see effect below)
  const [loading, setLoading] = useState(false);
  const [launch, setLaunch] = useState(null);   // the first question, on stage while it is answered (at least 1.4 s, so it can be read)
  const [sessionId, setSessionId] = useState(null);
  const [askYear, setAskYear] = useState(null);      // year picked under the suggested questions
  const [mode, setMode] = useState(null);
  const [recording, setRecording] = useState(false);
  const [voiceOk, setVoiceOk] = useState(false);
  const [graph, setGraph] = useState(null);
  // Phase 4 - reduce typing: the officer's own recent questions (one tap to re-run)
  // and real entity chips that BUILD a query instead of forcing a full sentence.
  const [recentQ, setRecentQ] = useState([]);
  const [facets, setFacets] = useState(null);      // {crimes:[], zones:[]} from real data
  const [deepThink, setDeepThink] = useState(false);
  const [phIdx, setPhIdx] = useState(0);
  const [starterOffset, setStarterOffset] = useState(0);
  const [typedText, setTypedText] = useState("");
  const [hudOpen, setHudOpen] = useState(false);
  const [docsMode, setDocsMode] = useState(true);
  const [pipelineStep, setPipelineStep] = useState(null);
  const [saveState, setSaveState] = useState(null);   // null | saving | saved | error
  const [tourOpen, setTourOpen] = useState(false);
  const [navHidden, setNavHidden] = useState(false);
  const [ops, setOps] = useState(null);   // live orchestrator telemetry (proof, not decoration)
  // Expert (deep multi-agent investigation) toggle. The backend does not role-gate
  // deep_think, so this was a UI-only lock - and it was keyed to the literal demo badge
  // "U-7001", so any Officer signing in with a different ID silently lost the button.
  // Flip EXPERT_ADMIN_ONLY to true to limit it to Admin/Inspector again.
  const EXPERT_ADMIN_ONLY = false;
  const [canUseExpert, setCanUseExpert] = useState(!EXPERT_ADMIN_ONLY);
  const [suggestedQs, setSuggestedQs] = useState([]);
  const [allQs, setAllQs] = useState([]);
  // Which set of role questions to offer. The Approver supervises proposals; everyone
  // else is working the case.
  const [roleKey, setRoleKey] = useState("operations");
  // What officers' ratings have taught (GET /api/feedback/signal): questions rated poor
  // stop being suggested until someone reviews them. Refreshed after every rating.
  const [avoidQs, setAvoidQs] = useState(() => new Set());
  const loadSignal = useCallback(() => {
    fetch(`${API}/api/feedback/signal?lang=${lang}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setAvoidQs(new Set((d.avoid || []).map((q) => String(q).trim().toLowerCase()))); })
      .catch(() => {});
  }, [lang]);
  useEffect(() => { loadSignal(); }, [loadSignal]);
  useEffect(() => {
    const read = () => {
      try {
        const s = JSON.parse(sessionStorage.getItem("antar_session") || "null");
        setRoleKey(s?.role === "Approver" ? "approver" : "operations");
      } catch {}
    };
    read();
    window.addEventListener("antar-role", read);
    window.addEventListener("storage", read);
    return () => {
      window.removeEventListener("antar-role", read);
      window.removeEventListener("storage", read);
    };
  }, []);

  useEffect(() => {
    let setIdx = 0;
    try {
      const lc = parseInt(localStorage.getItem("antar_login_count") || "1", 10);
      setIdx = ((lc - 1) % 13 + 13) % 13; // 13 sets (0-12) for 50 questions
    } catch {}
    
    // Fetch 4 questions for the chips
    fetch(`${API}/api/docs/questions?set=${setIdx}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (data.questions?.length) setSuggestedQs(data.questions); })
      .catch(() => {});
      
    // Fetch all 45 questions for the input placeholder rotator
    fetch(`${API}/api/docs/questions`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (data.questions?.length) setAllQs(data.questions); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    function checkAdmin() {
      try {
        const s = JSON.parse(sessionStorage.getItem("antar_session") || "null");
        const allowed = !EXPERT_ADMIN_ONLY || s?.role === "Admin" || s?.role === "Inspector";
        setCanUseExpert(allowed);
        if (!allowed) {
          setDeepThink(false);
        }
      } catch {
        setCanUseExpert(!EXPERT_ADMIN_ONLY);
        if (EXPERT_ADMIN_ONLY) setDeepThink(false);
      }
    }
    checkAdmin();
    window.addEventListener("antar-role", checkAdmin);
    window.addEventListener("storage", checkAdmin);
    return () => {
      window.removeEventListener("antar-role", checkAdmin);
      window.removeEventListener("storage", checkAdmin);
    };
  }, []);

  // After each completed answer, pull real per-agent telemetry from the
  // orchestrator - a mocked pipeline has no ticking call counts.
  useEffect(() => {
    if (loading || messages.length === 0) return;
    fetch(`${API}/api/orchestrator/status`)
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => {
        if (!s?.agents) return;
        const calls = Object.values(s.agents).reduce((n, a) => n + (a.calls || 0), 0);
        setOps({ calls, queryMs: s.agents.query?.last_ms ?? null });
      })
      .catch(() => {});
  }, [loading, messages.length]);

  const [lens, setLens] = useState(null);            // the agent picked above the chat box, or none
  const recogRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const voiceTurnRef = useRef(false);   // true when the pending question was dictated → speak the answer
  const audioChunksRef = useRef([]);
  const isRecordingRef = useRef(false);
  const micTimeoutRef = useRef(null);
  const committedTextRef = useRef("");
  const scrollRef = useRef(null);

  // Stable action handlers for MessageRow. Each wrapper is created once and always calls
  // the CURRENT implementation, so rows stay memoised through streaming while their
  // buttons (regenerate, export, rate, translate, why) never act on stale state.
  const liveActions = useRef({});
  liveActions.current = { send, showNetwork, exportReport, translateAnswer, rateAnswer, toggleWhy };
  const actions = useMemo(() => ({
    send: (...a) => liveActions.current.send(...a),
    showNetwork: (...a) => liveActions.current.showNetwork(...a),
    exportReport: (...a) => liveActions.current.exportReport(...a),
    translateAnswer: (...a) => liveActions.current.translateAnswer(...a),
    rateAnswer: (...a) => liveActions.current.rateAnswer(...a),
    toggleWhy: (...a) => liveActions.current.toggleWhy(...a),
  }), []);
  const inputRef = useRef(null);
  const landInputRef = useRef(null);
  // Both chat boxes grow with what is typed, up to a cap, then scroll; no fixed two-line box.
  useLayoutEffect(() => {
    for (const [el, max] of [[inputRef.current, 200], [landInputRef.current, 220]]) {
      if (!el) continue;
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, max)}px`;
      el.style.overflowY = el.scrollHeight > max ? "auto" : "hidden";
    }
  }, [input]);
  const kn = lang === "kn";

  // Recent questions (this officer's own history) + entity facets for the quick-pick
  // chips. Facets come from the REAL breakdown endpoints - never a hardcoded list, so
  // a chip can never offer a crime type or zone the database doesn't have.
  useEffect(() => {
    try { setRecentQ(JSON.parse(localStorage.getItem("antar_recent") || "[]").slice(0, 6)); } catch {}
    let alive = true;
    Promise.all([
      fetch(`${API}/api/analytics/breakdown?by=type`).then((r) => r.json()).catch(() => null),
      fetch(`${API}/api/analytics/breakdown?by=zone`).then((r) => r.json()).catch(() => null),
    ]).then(([t, z]) => {
      if (!alive) return;
      // Seed labels are ALL-CAPS and some carry a leading space (" CYBER CRIME"), so
      // trim + lowercase before they become chip text. Very long heads make useless
      // chips, so cap the length rather than truncate mid-word.
      const pick = (d) => (d?.rows || [])
        .map((r) => String(r.label ?? "").trim().toLowerCase())
        .filter((s) => s && s.length <= 24)
        .slice(0, 4);
      const crimes = pick(t), zones = pick(z);
      if (crimes.length || zones.length) setFacets({ crimes, zones });
    });
    return () => { alive = false; };
  }, []);

  // Expert Mode lives in the header (AppShell, Admin only) - mirror it here.
  useEffect(() => {
    try { setDeepThink(localStorage.getItem("antar_expert") === "1"); } catch {}
    const onExpert = (e) => setDeepThink(!!e.detail?.on);
    window.addEventListener("antar-expert", onExpert);
    return () => window.removeEventListener("antar-expert", onExpert);
  }, []);

  useEffect(() => {
    LIVE.setMessages = setMessages;
    LIVE.setLoading = setLoading;
    LIVE.setSessionId = setSessionId;
    return () => {
      if (LIVE.setMessages === setMessages) { LIVE.setMessages = null; LIVE.setLoading = null; LIVE.setSessionId = null; }
    };
  }, []);

  useEffect(() => {
    setVoiceOk(true); // MediaRecorder is widely supported
    try {
      const savedMsg = sessionStorage.getItem("antar_chat_msgs");
      const savedSess = sessionStorage.getItem("antar_chat_id");
      const savedMode = sessionStorage.getItem("antar_chat_mode");
      if (savedMsg) {
        // An answer still streaming from before this page opened (the officer went to
        // another page and came back) is picked up as it is. Only a reload, which ends the
        // stream, leaves a message saved mid-answer: that one is marked interrupted, so
        // the Stopped strip offers Regenerate with the original question.
        const saved = JSON.parse(savedMsg);
        const filtered = Array.isArray(saved)
          ? saved.filter((m) => !m?.text?.startsWith("Welcome to Antar Crime Intelligence") && !m?.text?.startsWith("ನಮಸ್ಕಾರ. Antar ಅಪರಾಧ"))
          : [];
        if (LIVE.inflight) setLoading(true);
        setMessages(filtered.map((m, i) => (m && m.streaming && !LIVE.inflight)
          ? { ...m, streaming: false, stopped: true,
              retryText: m.retryText || (filtered[i - 1]?.role === "user" ? filtered[i - 1].text : undefined) }
          : m));
      }
      if (savedSess) setSessionId(savedSess);
      if (savedMode) setMode(savedMode);
      // Once the user has been through /docs, /antar stays a chat screen —
      // no more docs redirects (the footer pill can re-enable docs mode).
      if (localStorage.getItem("antar_docs_seen")) setDocsMode(false);
    } catch (e) {}
  }, []);

  // FirstChat: before the first message the app chrome hides (CSS on [data-first]).
  useEffect(() => {
    document.documentElement.setAttribute("data-first", messages.length === 0 ? "1" : "0");
    return () => document.documentElement.removeAttribute("data-first");
  }, [messages.length === 0]);

  // The chat screen replaces the app top nav with its own floating pill (req #8).
  useEffect(() => {
    document.documentElement.setAttribute("data-chatnav", "1");
    return () => document.documentElement.removeAttribute("data-chatnav");
  }, []);

  // Tour defaults closed - only opens on button click.

  // Rotate the inline suggested question while the thread is empty (give 7.5s before changing).
  useEffect(() => {
    if (messages.length > 0) return;
    const id = setInterval(() => setPhIdx((i) => i + 1), 7500);
    return () => clearInterval(id);
  }, [messages.length === 0]);

  // Typewriter style animation inside placeholder
  useEffect(() => {
    if (messages.length > 0 || input) return;
    const qList = allQs.length > 0
      ? allQs.map(q => kn ? (q.question_kn || q.question_en) : q.question_en)
      : (kn ? STARTERS.kn : STARTERS.en);
    const fullText = qList[phIdx % qList.length];
    let i = 0;
    setTypedText("");
    const typeTimer = setInterval(() => {
      i++;
      setTypedText(fullText.slice(0, i));
      if (i >= fullText.length) clearInterval(typeTimer);
    }, 25);
    return () => clearInterval(typeTimer);
  }, [phIdx, kn, messages.length, input]);

  useEffect(() => { if (messages.length > 0) sessionStorage.setItem("antar_chat_msgs", JSON.stringify(messages)); }, [messages]);
  useEffect(() => { if (sessionId) sessionStorage.setItem("antar_chat_id", sessionId); }, [sessionId]);
  useEffect(() => { if (mode) sessionStorage.setItem("antar_chat_mode", mode); }, [mode]);
  // Track whether the officer is pinned to the bottom. Previously auto-scroll ran on
  // `isNearBottom || loading`, so during streaming it yanked the view back down even
  // while they were scrolled up reading - the classic fight-the-user anti-pattern.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      setAtBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 120);
    };
    onScroll();
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [messages.length === 0]);

  // Answer-first scrolling. When a question is sent it is pinned to the top of the thread,
  // so the answer streams in directly beneath it and its FIRST line is what the officer
  // reads. This used to follow every token to the bottom, so a long answer finished with
  // its last line on screen and its opening scrolled out of view.
  //
  // A question can only reach the top if there is enough content below it, so a spacer
  // tops the thread up to one viewport and shrinks as the answer fills in (the pattern
  // ChatGPT and Claude use). All measurements are in the thread's own CSS pixels, which
  // is what scrollIntoView and clientHeight both use - the thread's `zoom` cancels out.
  const lastLen = messages[messages.length - 1]?.text?.length || 0;
  const [tailPad, setTailPad] = useState(0);
  const pinnedTurn = useRef(-1);
  const PIN_MARGIN = 92;   // keep the pinned question clear of the floating nav

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!messages.length) { pinnedTurn.current = -1; setTailPad(0); return; }
    if (!el) return;
    let q = -1;
    for (let k = messages.length - 1; k >= 0; k--) if (messages[k].role === "user") { q = k; break; }
    if (q < 0 || q === pinnedTurn.current) return;
    pinnedTurn.current = q;
    setTailPad(el.clientHeight);                       // room first …
    requestAnimationFrame(() => {                      // … then scroll once it has laid out
      el.querySelector(`[data-row="${q}"]`)?.scrollIntoView({ block: "start", behavior: "smooth" });
    });
  }, [messages.length]);

  useLayoutEffect(() => {
    const el = scrollRef.current, q = pinnedTurn.current;
    if (!el || q < 0) return;
    let used = 0;
    el.querySelectorAll(".cx-row").forEach((r) => { if (+r.dataset.row >= q) used += r.offsetHeight + 14; });
    setTailPad(Math.max(0, el.clientHeight - used - PIN_MARGIN));
  }, [lastLen, messages.length]);

  useEffect(() => {
    const checkDemo = () => {
      const p = sessionStorage.getItem("antar-demo-pending");
      if (p === "1") {
        sessionStorage.removeItem("antar-demo-pending");
        setTimeout(() => {
          send("ರಾಜಾಜಿನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನದ ಬಗ್ಗೆ ತಿಳಿಸಿ");
        }, 350);
      }
    };
    checkDemo();
    const handler = (e) => {
      if (e.detail?.wow === 1) checkDemo();
    };
    window.addEventListener("antar-demo-trigger", handler);

    // A question handed over in the address (/antar?q=..., used by Search, the Brain's focus
    // card and /ask) is asked straight away, like the live=1 hand-off below. It used to be
    // ignored, so "Ask Antar" opened an empty chat.
    if (typeof window !== "undefined" && !liveTriggeredRef.current) {
      try {
        const u = new URL(window.location.href);
        const q = (u.searchParams.get("q") || "").trim();
        if (q) {
          liveTriggeredRef.current = true;
          setDocsMode(false);
          u.searchParams.delete("q");
          window.history.replaceState({}, "", u.pathname + (u.search ? u.search : ""));
          setTimeout(() => send(q, true), 150);
        }
      } catch {}
    }

    if (typeof window !== "undefined" && !liveTriggeredRef.current && window.location.search.includes("live=1")) {
      liveTriggeredRef.current = true;
      setDocsMode(false);
      try {
        const u = new URL(window.location.href);
        u.searchParams.delete("live");
        window.history.replaceState({}, "", u.pathname + (u.search ? u.search : ""));
      } catch {}
      // /docs already streamed this answer and wrote it into antar_chat_msgs —
      // consume the handoff instead of re-asking the backend.
      let handoff = false;
      try {
        handoff = sessionStorage.getItem("antar_docs_handoff") === "1";
        if (handoff) sessionStorage.removeItem("antar_docs_handoff");
      } catch {}
      if (!handoff) {
        const savedQ = sessionStorage.getItem("antar_initial_question") || localStorage.getItem("antar_initial_question") || "Who is Saleem Malik and what is his active operating zone?";
        setTimeout(() => {
          send(savedQ, true);
        }, 150);
      }
    }

    return () => window.removeEventListener("antar-demo-trigger", handler);
  }, [loading]);

  function patchLast(fn) {
    liveUpdateLast(fn);
  }

  async function sendNonStream(q) {
    const res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ text: q, lang, session_id: sessionId, deep_think: deepThink }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const d = await res.json();
    
    if (!d.no_results && (d.lang === "kn" || lang === "kn")) {
      playTTS(d.answer || "", "kn");
    }

    setSessionId(d.session_id);
    setMode(d.mode);
    patchLast(() => ({
      ...newAssistantMsg(d.lang || lang),
      streaming: false,
      text: d.answer,
      citations: d.no_results ? [] : d.citations || [],
      custody: d.no_results ? null : d.custody || null,
      steps: (d.agents_used || []).map((a) => ({ agent: a, status: "done", label: a })),
      confidence: !d.no_results && typeof d.confidence === "number"
        ? { answer: d.confidence, routing: d.confidence, label: kn ? "ವಿಶ್ವಾಸ (ರೂಟಿಂಗ್)" : "Routing confidence" }
        : null,
      suspects: d.suspects || [],
      actions: d.actions || [],
      suggested: d.suggested || [],
      reasoning: d.reasoning || [],
      template: d.template_id,
      noResults: !!d.no_results,
    }));
  }

  // Tapping an entity chip APPENDS to the composer rather than sending - the officer
  // builds "theft rajajinagar" by tapping, then sends. The router already handles
  // keyword-style queries, so no full sentence is ever required.
  function addEntity(word) {
    setInput((prev) => {
      const cur = (prev || "").trim();
      if (cur.toLowerCase().includes(String(word).toLowerCase())) return cur;
      return cur ? `${cur} ${word}` : String(word);
    });
    try { inputRef.current?.focus(); } catch {}
  }

  function pushRecent(q) {
    try {
      const prev = JSON.parse(localStorage.getItem("antar_recent") || "[]");
      const next = [q, ...prev.filter((x) => x !== q)].slice(0, 6);
      localStorage.setItem("antar_recent", JSON.stringify(next));
      setRecentQ(next);
    } catch {}
  }

  async function send(text, skipDocs = false) {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    const spokenTurn = voiceTurnRef.current;
    voiceTurnRef.current = false;
    setInput("");
    pushRecent(q);
    setAtBottom(true);

    try {
      sessionStorage.setItem("antar_initial_question", q);
      localStorage.setItem("antar_initial_question", q);
      if (docsMode && !skipDocs) {
        setPipelineStep(1);
        setTimeout(() => setPipelineStep(2), 650);
        setTimeout(() => setPipelineStep(3), 1300);
        setTimeout(() => {
          router.push("/docs");
        }, 2050);
        return;
      }
    } catch {}

    if (messages.length === 0) setLaunch({ q, t: Date.now() });
    setMessages((m) => [...m, { role: "user", text: q, lang, ts: Date.now() }]);
    setMessages((m) => [...m, newAssistantMsg(lang)]);
    setLoading(true);

    let vigilRec = null;
    try {
      const vRes = await fetch(`${API}/api/vigil/scan`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ query: q, officer: getActiveOfficerId() })
      });
      if (vRes.ok) {
        const vData = await vRes.json();
        vigilRec = vData.receipt || vData;
        patchLast((msg) => ({ ...msg, vigil: vigilRec }));
      }
    } catch (ve) {
      console.warn("Vigil check bypassed:", ve);
    }

    let gotToken = false;
    try {
      abortedRef.current = false;          // fresh turn - a previous stop must not leak in
      abortControllerRef.current = new AbortController();
      LIVE.inflight = true;
      const res = await fetch(`${API}/api/chat/stream`, {
        method: "POST",
        headers: getAuthHeaders(),
        // With an agent picked on the landing screen, the first question is asked through
        // that agent's mode. Later questions are asked as typed.
        body: JSON.stringify({ text: (lens && messages.length === 0 && !q.startsWith("/")) ? `${LENS[lens]} ${q}` : q, lang, session_id: sessionId, deep_think: deepThink }),
        signal: abortControllerRef.current.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
      let buf = "";
      let fullText = "";
      let lastLang = lang;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += value;
        const parts = buf.split("\n\n");
        buf = parts.pop();
        for (const raw of parts) {
          if (!raw || raw.startsWith(":")) continue;
          const line = raw.replace(/^data: /, "").trim();
          if (!line) continue;
          let evt;
          try { evt = JSON.parse(line); } catch { continue; }
          if (evt.type === "token") {
             gotToken = true;
             fullText += evt.content || "";
          }
          if (evt.type === "session" && evt.session_id) liveSessionId(evt.session_id);
          if (evt.type === "complete") { liveSessionId(evt.session_id); setMode(evt.mode); if (evt.lang) lastLang = evt.lang; }
          patchLast((msg) => applyEvent(msg, evt));
        }
      }

      // Speak the answer when the question was dictated (either language) or the
      // conversation is in Kannada (existing behaviour) - and only if the chat is on screen.
      if (!abortedRef.current && LIVE.setMessages && fullText.trim() && (spokenTurn || lastLang === "kn" || lang === "kn")) {
        speakAnswer(spokenTextOf({ text: fullText }), lastLang === "kn" || lang === "kn" ? "kn" : "en", API);
      }
    } catch (e) {
      // Deliberate stop: keep whatever streamed, mark it interrupted, and do NOT
      // fall through to the non-stream path (that would re-send the cancelled query).
      if (abortedRef.current || e?.name === "AbortError") {
        patchLast((msg) => ({ ...msg, streaming: false, stopped: true, retryText: q }));
      } else if (gotToken) {
        patchLast((msg) => ({ ...msg, streaming: false, error: true, retryText: q }));
      } else {
        try {
          await sendNonStream(q);
        } catch (e2) {
          // Both stream and non-stream failed → backend unreachable. Honest
          // state only: no fabricated report, no fake citations/confidence.
          patchLast(() => ({
            ...newAssistantMsg(lang),
            streaming: false,
            error: true,
            retryText: q,
            noResults: true,
            text: kn
              ? `ಬ್ಯಾಕೆಂಡ್ ತಲುಪಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ (${API}). ಸರ್ವರ್ ಚಾಲನೆಯಲ್ಲಿದೆಯೇ ಎಂದು ಪರಿಶೀಲಿಸಿ ಮತ್ತು ಮರುಪ್ರಯತ್ನಿಸಿ.`
              : `Backend unreachable - the Antar API at ${API} did not respond, so this question was not answered. Check that the server is running, then retry.`,
          }));
        }
      }
    } finally {
      LIVE.inflight = false;
      (LIVE.setLoading || setLoading)(false);
    }
  }

  async function showNetwork(id, name, cachedGraph) {
    if (cachedGraph) { setGraph({ data: cachedGraph, name, loading: false }); return; }
    setGraph({ data: null, name, loading: true });
    try {
      const res = await fetch(`${API}/api/graph/${id}`);
      const d = await res.json();
      setGraph({ data: d, name, loading: false });
    } catch (e) {
      // Honest failure: no fabricated graph - say the backend is unreachable.
      setGraph({ data: null, name, loading: false, error: true });
    }
  }

  function playTTS(text, ttsLang) {
    return speakAnswer(spokenTextOf({ text }), ttsLang, API);
  }

  function newSession() {
    if (LIVE.inflight) stopChat();   // a running answer must not land in the new conversation
    stopTts();                       // a new session should not keep reading the old answer
    setDocsMode(true);
    setMessages([]);
    setSessionId(null);
    setGraph(null);
    setSaveState(null);
    try {
      sessionStorage.removeItem("antar_chat_msgs");
      sessionStorage.removeItem("antar_chat_id");
    } catch {}
  }

  async function rateAnswer(idx, rating) {
    const question = messages[idx - 1]?.role === "user" ? messages[idx - 1].text : "";
    setMessages((ms) => ms.map((x, j) => (j === idx ? { ...x, rated: rating } : x)));
    try {
      await fetch(`${API}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // The server takes the officer from the sign-in and the answer from its own record
        // of this conversation (found by reasoning_id), so neither is sent from here.
        body: JSON.stringify({
          session_id: sessionId || "local", question: question || "(unknown)", rating,
          reasoning_id: messages[idx]?.reasoningId || null,
          lang: messages[idx]?.lang || lang,
          template_id: messages[idx]?.template || null,
        }),
      });
      loadSignal();          // a poor rating stops that question being suggested right away
    } catch {}
  }

  // Per-message native translate flip (View in Kannada / English).
  async function translateAnswer(idx) {
    const m = messages[idx];
    if (!m) return;
    if (m.altText) {                                   // already fetched → just toggle
      setMessages((ms) => ms.map((x, j) => (j === idx ? { ...x, showAlt: !x.showAlt } : x)));
      return;
    }
    const target = (m.lang || lang) === "kn" ? "en" : "kn";
    setMessages((ms) => ms.map((x, j) => (j === idx ? { ...x, translating: true } : x)));
    try {
      const res = await fetch(`${API}/api/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: m.text, target_lang: target }),
      });
      const d = await res.json();
      setMessages((ms) => ms.map((x, j) => (j === idx
        ? { ...x, translating: false, altText: d.translated || x.text, altLang: target, showAlt: true }
        : x)));
    } catch {
      setMessages((ms) => ms.map((x, j) => (j === idx ? { ...x, translating: false } : x)));
    }
  }

  async function saveSession() {
    if (messages.length === 0 || saveState === "saving") return;
    setSaveState("saving");
    try {
      const sid = sessionId || `local-${Date.now().toString(36)}`;
      const res = await fetch(`${API}/api/session/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sid, payload: { messages, sessionId: sid, lang } }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSaveState("saved");
      setTimeout(() => setSaveState(null), 2500);
    } catch {
      setSaveState("error");
      setTimeout(() => setSaveState(null), 2500);
    }
  }

  // PillNav is now globally rendered by AppShell across all screens.

  function exportReport() {
    if (!sessionId) return;
    openReport(`/report/${sessionId}`);
  }

  async function toggleVoice() {
    if (recording || mediaRecorderRef.current) {
      if (micTimeoutRef.current) clearTimeout(micTimeoutRef.current);
      isRecordingRef.current = false;
      if (mediaRecorderRef.current) {
        try { mediaRecorderRef.current.stop(); } catch {}
        mediaRecorderRef.current = null;
      }
      setRecording(false);
      window.dispatchEvent(new CustomEvent("whisper-speech", { detail: { active: false } }));
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert(kn ? "ನಿಮ್ಮ ಬ್ರೌಸರ್ ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆಯನ್ನು ಬೆಂಬಲಿಸುವುದಿಲ್ಲ." : "Speech recognition is not supported in this browser.");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = lang === "kn" ? "kn-IN" : "en-US";
      recognition.continuous = true;
      recognition.interimResults = true;
      
      mediaRecorderRef.current = recognition;

      isRecordingRef.current = true;
      setRecording(true);
      window.dispatchEvent(new CustomEvent("whisper-speech", { detail: { active: true } }));

      recognition.onresult = (event) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
          voiceTurnRef.current = true;
          setInput((prev) => (prev ? prev + " " : "") + finalTranscript);
        }
      };

      recognition.onend = () => {
        if (isRecordingRef.current) {
           // It might have stopped due to pause in speaking, restart it
           try { recognition.start(); } catch {}
        } else {
           setRecording(false);
           window.dispatchEvent(new CustomEvent("whisper-speech", { detail: { active: false } }));
        }
      };

      recognition.onerror = (e) => {
         console.error("Speech Recognition Error:", e.error);
         if (e.error === "not-allowed") {
           alert("No mic permission. Please allow microphone access in your browser settings to use voice input.");
         }
         if (e.error !== "no-speech") {
             isRecordingRef.current = false;
             setRecording(false);
             window.dispatchEvent(new CustomEvent("whisper-speech", { detail: { active: false } }));
         }
      };

      if (micTimeoutRef.current) clearTimeout(micTimeoutRef.current);
      micTimeoutRef.current = setTimeout(() => {
        isRecordingRef.current = false;
        if (mediaRecorderRef.current) {
          try { mediaRecorderRef.current.stop(); } catch {}
          mediaRecorderRef.current = null;
        }
      }, 18000); // 18 seconds max timeout

      recognition.start();
    } catch (err) {
      alert("Microphone access denied or error: " + err.message);
      isRecordingRef.current = false;
      setRecording(false);
    }
  }

  function toggleWhy(i) {
    setMessages((m) => m.map((mm, k) => (k === i ? { ...mm, whyOpen: !mm.whyOpen } : mm)));
  }

  const last = messages[messages.length - 1];
  const showSuggestions = (messages.length === 0 ? STARTERS[lang] : last?.role === "assistant" && !last.error && !last.streaming && !last.noResults ? last.suggested : [])
    ?.filter((q) => q !== last?.layout?.sections?.next_step);   // already offered as "Next" in the card

  // Role questions sit beside the data-checked ones, so there is always somewhere useful
  // to go next - including after a "nothing found", where the backend returns none.
  // Anything already asked this session, already offered, or down-rated before is dropped.
  const askedThisSession = new Set(messages.filter((m) => m.role === "user").map((m) => (m.text || "").trim().toLowerCase()));
  const roleSuggestions = (messages.length === 0 ? [] : (ROLE_QUESTIONS[roleKey]?.[lang] || ROLE_QUESTIONS[roleKey]?.en || []))
    .filter((q) => !askedThisSession.has(q.trim().toLowerCase()))
    .filter((q) => !(showSuggestions || []).includes(q))
    .filter((q) => !avoidQs.has(q.trim().toLowerCase()))
    .slice(0, 2);
  const empty = messages.length === 0;
  const launchReady = !!launch && last?.role === "assistant"
    && (!last.streaming || !!(last.text || "").trim() || !!last.layout || !!last.error);
  useEffect(() => {
    if (!launchReady) return;
    const t = setTimeout(() => setLaunch(null), Math.max(0, 1400 - (Date.now() - launch.t)));
    return () => clearTimeout(t);
  }, [launchReady]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (empty) setLaunch(null); }, [empty]);
  const hasUserTurn = messages.some((m) => m.role === "user" && m.text?.trim());
  // Expert Search → Bench workspace (right pane).
  const workspaceOn = deepThink && !empty;
  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && !m.streaming && m.text);
  const hasAnswer = messages.some((m) => m.role === "assistant" && m.text?.trim() && !m.error);
  const lastUserQ = (() => { const i = messages.map((m) => m.role).lastIndexOf("user"); return i >= 0 ? messages[i].text : ""; })();

  const starters = suggestedQs.length > 0 
    ? suggestedQs.map(q => lang === 'kn' ? (q.question_kn || q.question_en) : q.question_en) 
    : STARTERS[lang];
    
  const rotatorStarters = allQs.length > 0 
    ? allQs.map(q => lang === 'kn' ? (q.question_kn || q.question_en) : q.question_en) 
    : starters;
    
  const rotator = empty && !input && !loading ? rotatorStarters[phIdx % rotatorStarters.length] : null;
  const searchBar = (
    <div style={{
      background: "rgba(13, 17, 28, 0.9)",
      border: "1px solid rgba(255, 255, 255, 0.12)",
      borderRadius: recording ? "32px" : "22px",
      padding: recording ? "8px 16px" : "14px 18px",
      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.45)",
      backdropFilter: "blur(20px)",
      display: "flex",
      flexDirection: recording ? "row" : "column",
      alignItems: recording ? "center" : "stretch",
      gap: "8px",
      width: "100%",
      minHeight: recording ? "60px" : "auto"
    }}>
      {recording ? (
        <>
          <span style={{ display: "flex", alignItems: "center", padding: "0 8px" }}>
            <Orb state="listening" label={kn ? "ಆಲಿಸುತ್ತಿದೆ" : "Listening"} />
          </span>
          
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
             <WhisperWaveform kn={kn} onStop={toggleVoice} onClear={() => { committedTextRef.current = ""; setInput(""); }} />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px", paddingRight: "4px" }}>
            <button onClick={toggleVoice} style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#1E293B", border: "none", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
              <div style={{ width: "12px", height: "12px", background: "#E2E8F0", borderRadius: "2px" }} />
            </button>
            <button
              type="button"
              disabled={!input.trim()}
              onClick={() => send(input)}
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                background: "#2563EB",
                border: "none",
                color: "#FFFFFF",
                cursor: input.trim() ? "pointer" : "default",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                opacity: input.trim() ? 1 : 0.6
              }}
            >
              <ArrowUp size={16} strokeWidth={2.5} />
            </button>
          </div>
        </>
      ) : (
        <>
      <div style={{ position: "relative" }}>
        {input.startsWith("/") && !loading && (
          <div style={{
            position: "absolute", bottom: "calc(100% + 10px)", left: 0, right: 0, zIndex: 60,
            background: "rgba(8,12,20,0.97)", border: "1px solid rgba(34,230,240,0.3)",
            borderRadius: "12px", padding: "6px", boxShadow: "0 12px 32px rgba(0,0,0,0.55)",
            fontFamily: "'JetBrains Mono', monospace"
          }}>
            {SLASH_HINTS.filter((c) => c.cmd.startsWith(input.split(/\s/)[0].toLowerCase()) || input.trim() === "/").map((c) => (
              <button
                key={c.cmd}
                type="button"
                onClick={() => { setInput(`${c.cmd} `); inputRef.current?.focus(); }}
                style={{
                  display: "flex", width: "100%", alignItems: "baseline", gap: "10px",
                  background: "transparent", border: "none", cursor: "pointer",
                  padding: "8px 10px", borderRadius: "8px", textAlign: "left"
                }}
              >
                <span style={{ color: c.color, fontSize: "12.5px", fontWeight: 700, flexShrink: 0 }}>{c.cmd}</span>
                <span style={{ color: "#94A3B8", fontSize: "11.5px" }}>{kn ? c.kn : c.en}</span>
              </button>
            ))}
          </div>
        )}
        {recording && (
          <div style={{ paddingBottom: "10px", display: "flex", alignItems: "center" }}>
            <WhisperWaveform kn={kn} onStop={toggleVoice} onClear={() => { committedTextRef.current = ""; setInput(""); }} />
          </div>
        )}
        <textarea
          ref={inputRef}
          className={`cx-input ${kn ? "kn" : ""}`}
          style={{
            width: "100%",
            minHeight: "56px",
            maxHeight: "200px",
            background: "transparent",
            border: "none",
            outline: "none",
            resize: "none",
            color: "#FFFFFF",
            fontSize: "15.5px",
            lineHeight: 1.5,
            fontFamily: "'Inter', sans-serif"
          }}
          rows={1}
          placeholder={kn ? "ಏನಾದರೂ ಕೇಳಿ..." : "Ask anything you want..."}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Tab" && !input && rotator) {
              e.preventDefault();
              setInput(rotator);
            } else if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          aria-label="Ask Antar"
          disabled={loading}
        />
      </div>
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        paddingTop: "10px",
        marginTop: "4px",
        borderTop: "1px solid rgba(255, 255, 255, 0.06)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "12.5px", fontFamily: "'Inter', sans-serif", flexWrap: "wrap", color: "rgba(255,255,255,0.4)" }}>
          {canUseExpert
            ? <ExpertSwitch on={deepThink} kn={kn} onToggle={() => {
                const next = !deepThink;
                setDeepThink(next);
                try { localStorage.setItem("antar_expert", next ? "1" : "0"); } catch {}
                window.dispatchEvent(new CustomEvent("antar-expert", { detail: { on: next } }));
              }} />
            : (kn ? "ಅಂತರ್ ಸಿಸ್ಟಮ್" : "Antar System")}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <WhisperMicButton recording={recording} onClick={toggleVoice} kn={kn} />

          {loading ? (
            <button
              onClick={stopChat}
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "10px",
                background: "rgba(255, 60, 60, 0.2)",
                border: "1px solid rgba(255, 60, 60, 0.5)",
                color: "#FF3C3C",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s"
              }}
              title={kn ? "ನಿಲ್ಲಿಸಿ" : "Abort"}
            >
              <Square size={14} fill="currentColor" />
            </button>
          ) : (
            <button
              onClick={() => send()}
              disabled={!input.trim()}
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "10px",
                background: input.trim() ? "#2563EB" : "rgba(255, 255, 255, 0.12)",
                border: "none",
                color: "#FFFFFF",
                cursor: input.trim() ? "pointer" : "default",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s"
              }}
              title={kn ? "ಕಳುಹಿಸಿ" : "Send"}
            >
              <ArrowUp size={17} strokeWidth={2.5} />
            </button>
          )}
        </div>
      </div>
        </>
      )}
    </div>
  );

  const HUD = (
    <div className={`cx-hud ${hudOpen ? "open" : ""}`}>
      <button type="button" className="cx-hud-pill" aria-expanded={hudOpen} onClick={() => setHudOpen((v) => !v)}>
        {kn ? "Antar ಏನು ಮಾಡಬಲ್ಲದು?" : "What can Antar do?"}
        <span className="c">{hudOpen ? "−" : "+"}</span>
      </button>
      {hudOpen && (
        <div className="cx-hud-panel fade-rise">
          <div className="cx-hud-sec">
            <b>{kn ? "ಏನು ಮಾಡಬಲ್ಲದು" : "What it can do"}</b>
            <p>{kn
              ? "FIR ದಾಖಲೆಗಳ ಮೇಲೆ ಪ್ರಶ್ನೆ, ಶಂಕಿತ ಜಾಲ, ಹಾಟ್‌ಸ್ಪಾಟ್ ನಕ್ಷೆ, ಮುನ್ಸೂಚನೆ - ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಕನ್ನಡದಲ್ಲಿ, ಧ್ವನಿ ಸಹಿತ."
              : "Ask live FIR records anything - suspect networks, hotspot maps, trends and forecasts - in English or Kannada, by voice or text."}</p>
          </div>
          <div className="cx-hud-sec">
            <b>{kn ? "ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ" : "How it works"}</b>
            <p>{kn
              ? "ಬಹು-ಏಜೆಂಟ್‌ಗಳು ಪ್ರಶ್ನೆಯನ್ನು ಸುರಕ್ಷಿತ ಟೆಂಪ್ಲೇಟ್‌ಗೆ ಜೋಡಿಸಿ, ದತ್ತಾಂಶದಿಂದ ಮಾತ್ರ ಉಲ್ಲೇಖ ಸಮೇತ ಉತ್ತರಿಸುತ್ತವೆ."
              : "Specialist agents route your question to a whitelisted query template and answer only from returned records - every claim cited."}</p>
          </div>
          <div className="cx-hud-sec">
            <b>{kn ? "ಪ್ರಯತ್ನಿಸಿ" : "Try it"}</b>
            <div className="cx-hud-try">
              {STARTERS[lang].slice(0, 3).map((s, i) => (
                <button key={i} className={`cx-chip ${kn ? "kn" : ""}`} onClick={() => { setHudOpen(false); send(s); }}>{s}</button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className={`cx-page ${workspaceOn ? "xw-on" : ""}`} style={{ height: "100vh", display: "flex", flexDirection: "column", position: "relative", background: "transparent" }}>
      <CinematicBackground />
      <div className="nx-glow" aria-hidden="true" />
      
      {/* EN / KN: in the top nav on every screen (components/LangToggle) */}

      {!empty && (
        <button
          type="button"
          onClick={newSession}
          style={{
            position: "fixed",
            top: "76px",
            left: "max(16px, calc((100vw - 1040px) / 2 - 240px))",   // well clear of the answer column
            zIndex: 10000,
            display: "inline-flex",
            alignItems: "center",
            gap: "7px",
            whiteSpace: "nowrap",
            flexShrink: 0,
            background: "rgba(15, 20, 30, 0.75)",
            border: "1px solid rgba(255, 255, 255, 0.16)",
            borderRadius: "9999px",
            padding: "7px 16px",
            color: "#FFFFFF",
            fontSize: "12.5px",
            fontWeight: 500,
            fontFamily: "'Inter', sans-serif",
            cursor: "pointer",
            boxShadow: "0 4px 14px rgba(0, 0, 0, 0.35)",
            backdropFilter: "blur(14px)",
            WebkitBackdropFilter: "blur(14px)",
            transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease"
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.background = "rgba(30, 41, 59, 0.85)";
            e.currentTarget.style.borderColor = "rgba(34, 230, 240, 0.4)";
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.background = "rgba(15, 20, 30, 0.75)";
            e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.16)";
          }}
          title={kn ? "ಹೊಸ ತನಿಖಾ ಚಾಟ್ ಪ್ರಾರಂಭಿಸಿ" : "Start a new intelligence investigation session"}
        >
          <span style={{ fontSize: "16px", lineHeight: 1, color: "var(--cyan, #22E6F0)", fontWeight: 400 }}>+</span>
          <span>{kn ? "ಹೊಸ ಸೆಶನ್" : "New Session"}</span>
        </button>
      )}


      {empty ? (
        <>
        <style>{`@media (min-width: 821px) { .cx-pillnav { display: none !important; } }`}</style>
        {/* the nav (and the switch in it) is hidden here on desktop, so the switch floats top right */}
        <LangToggle float />
        <div className="cx-land" style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          background: "var(--void, #060910)",
          fontFamily: "'Inter', sans-serif",
          display: "flex",
          flexDirection: "column",
          zIndex: 9999,
          overflow: "hidden"
        }}>

          {/* 2. Centered AI Chat / Question Bar */}
          <div className="cx-land-center" style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "0 24px"
          }}>


            {/* Impacting Hero Header + Subtext */}
            <motion.div
              initial={{ opacity: 0, y: -15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              style={{
                textAlign: "center",
                marginBottom: "36px",
                maxWidth: "860px",
                width: "100%"
              }}
            >
              <h1 className="cx-hero-h1" style={{
                fontSize: "clamp(26px, 5.5vw, 54px)",
                fontWeight: 800,
                color: "#FFFFFF",
                letterSpacing: "-0.03em",
                lineHeight: 1.15,
                marginBottom: "14px",
                fontFamily: kn ? "'Noto Sans Kannada', sans-serif" : "'Inter', sans-serif"
              }}>
                {kn ? <><span className="hover-brand">Antar</span> ಇಂದು ನಿಮಗೆ <span style={{ color: "rgba(255,255,255,0.45)" }}>ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?</span></>
                    : <>What can <span className="hover-brand">Antar</span> help you with <span style={{ color: "rgba(255,255,255,0.45)" }}>today?</span></>}
              </h1>
              <p
                className="whitespace-normal md:whitespace-nowrap"
                style={{
                  fontSize: "clamp(13px, 1.05vw, 14.5px)",
                  color: "rgba(255, 255, 255, 0.72)",
                  lineHeight: 1.55,
                  margin: 0,
                  fontWeight: 400,
                  letterSpacing: "0.01em",
                  fontFamily: kn ? "'Noto Sans Kannada', sans-serif" : "'Inter', sans-serif"
                }}
              >
                {kn ? (
                  <>ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಕನ್ನಡದಲ್ಲಿ ಪ್ರಶ್ನಿಸಿ. ಪ್ರತಿಯೊಂದು ಉತ್ತರವೂ ಅಧಿಕೃತ FIR ದಾಖಲೆಗಳಿಂದ ನೇರವಾಗಿ ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟಿದೆ.</>
                ) : (
                  <>Query in English or Kannada. Every response is verified and cited directly from official FIR records.</>
                )}
              </p>
            </motion.div>

            <AgentStrip selected={lens} onSelect={setLens} />
            {lens && (() => {
              const a = STRIP_AGENTS.find(([n]) => n === lens);
              return (
                <p className="ags-lens" role="status">
                  <b>{lens}</b> {a?.[2]} {kn ? "ಮೊದಲ ಪ್ರಶ್ನೆ" : "Your first question goes through"} <code>{LENS[lens]}</code>.
                  <button type="button" onClick={() => router.push(`/docs?agent=${encodeURIComponent(lens)}`)}>{kn ? "ಇದು ಏನು ಮಾಡುತ್ತದೆ" : "What it does"} →</button>
                  <button type="button" onClick={() => setLens(null)} aria-label="Clear the selected agent">×</button>
                </p>
              );
            })()}

            <motion.div
              initial={{ opacity: 0, y: 25, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              style={{
                width: "100%",
                maxWidth: "860px",
                boxSizing: "border-box",
                background: "rgba(255, 255, 255, 0.035)",
                backdropFilter: "blur(18px)",
                WebkitBackdropFilter: "blur(18px)",
                border: isFocus ? "1px solid rgba(255, 255, 255, 0.28)" : "1px solid rgba(255, 255, 255, 0.12)",
                boxShadow: isFocus
                  ? "0 0 45px rgba(255,255,255,0.07), 0 20px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.14)"
                  : "0 20px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.08)",
                borderRadius: recording ? "42px" : "28px",
                padding: recording ? "12px 22px" : "18px 22px 14px",
                display: "flex",
                flexDirection: recording ? "row" : "column",
                alignItems: recording ? "center" : "stretch",
                gap: "12px",
                transition: "color 0.3s ease, background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease, opacity 0.3s ease, transform 0.3s ease, scale 0.3s ease, padding 0.3s ease"
              }}
            >
              {recording ? (
                <>
                  <button type="button" onClick={() => {}} style={{ background: "transparent", border: "none", color: "rgba(255,255,255,0.6)", cursor: "pointer", fontSize: "26px", display: "flex", alignItems: "center", justifyContent: "center", padding: "0 10px", fontWeight: 300, lineHeight: 1 }}>
                    +
                  </button>
                  
                  <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                     <WhisperWaveform kn={kn} onStop={toggleVoice} onClear={() => { committedTextRef.current = ""; setInput(""); }} />
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "10px", paddingRight: "4px" }}>
                    <button onClick={toggleVoice} style={{ width: "34px", height: "34px", borderRadius: "50%", background: "#1E293B", border: "none", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
                      <div style={{ width: "12px", height: "12px", background: "#E2E8F0", borderRadius: "2px" }} />
                    </button>
                    <button
                      type="button"
                      disabled={!input.trim()}
                      onClick={() => send(input)}
                      style={{
                        width: "34px",
                        height: "34px",
                        borderRadius: "50%",
                        background: input.trim() ? "#2563EB" : "rgba(255, 255, 255, 0.12)",
                        border: "none",
                        color: "#FFFFFF",
                        cursor: input.trim() ? "pointer" : "default",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s"
                      }}
                    >
                      <ArrowUp size={16} strokeWidth={2.5} />
                    </button>
                  </div>
                </>
              ) : (
                <>


              {/* Prompt Field Wrapper with Typewriter Overlay */}
              <div style={{ position: "relative", width: "100%" }}>
                <textarea
                  ref={landInputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onFocus={() => setIsFocus(true)}
                  onBlur={() => setIsFocus(false)}
                  onKeyDown={(e) => {
                    if (e.key === "Tab" && !input.trim() && rotator) {
                      e.preventDefault();
                      setInput(rotator);
                    }
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      if (input.trim()) send(input);
                    }
                  }}
                  placeholder=""
                  className="cx-land-input"
                  style={{
                    width: "100%",
                    minHeight: "72px",
                    maxHeight: "220px",
                    background: "transparent",
                    border: "none",
                    outline: "none",
                    resize: "none",
                    color: "#FFFFFF",
                    fontSize: "17px",
                    lineHeight: 1.5,
                    fontFamily: "'Inter', sans-serif"
                  }}
                />

                {!input && (
                  <div
                    style={{
                      position: "absolute",
                      top: "2px",
                      left: 0,
                      right: 0,
                      pointerEvents: "none",
                      display: "flex",
                      alignItems: "center",
                      flexWrap: "wrap",
                      gap: "7px",
                      fontSize: "14.5px",
                      lineHeight: 1.5,
                      fontFamily: "'Inter', sans-serif"
                    }}
                  >
                    <span
                      style={{
                        color: "rgba(255, 255, 255, 0.55)",
                        cursor: "pointer",
                        pointerEvents: "auto",
                        transition: "color 0.2s"
                      }}
                      onClick={() => {
                        if (rotator) setInput(rotator);
                      }}
                      title={kn ? "ಆಯ್ಕೆ ಮಾಡಲು ಕ್ಲಿಕ್ ಮಾಡಿ ಅಥವಾ Tab ಒತ್ತಿ" : "Click or press Tab to select this question"}
                    >
                      {typedText}
                      <span style={{ opacity: 0.65, marginLeft: "2px" }}>|</span>
                    </span>
                    <span className="cx-tabhint"
                      style={{
                        fontSize: "10.5px",
                        color: "rgba(255, 255, 255, 0.45)",
                        background: "rgba(255, 255, 255, 0.08)",
                        padding: "2px 7px",
                        borderRadius: "5px",
                        pointerEvents: "auto",
                        cursor: "pointer",
                        letterSpacing: "0.02em"
                      }}
                      onClick={() => {
                        if (rotator) setInput(rotator);
                      }}
                      title={kn ? "ಆಯ್ಕೆ ಮಾಡಲು ಕ್ಲಿಕ್ ಮಾಡಿ ಅಥವಾ Tab ಒತ್ತಿ" : "Click or press Tab to select this question"}
                    >
                      Tab ⇆
                    </span>
                  </div>
                )}
              </div>

              {/* Bottom Toolbar - Updated to match Image 1 */}
              <div style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                paddingTop: "10px",
                marginTop: "4px",
                borderTop: "1px solid rgba(255, 255, 255, 0.06)"
              }}>
                {/* Left: Model Pill */}
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "12.5px", fontFamily: "'Inter', sans-serif", flexWrap: "wrap", color: "rgba(255,255,255,0.4)" }}>
                  {canUseExpert
                    ? <ExpertSwitch on={deepThink} kn={kn} onToggle={() => {
                        const next = !deepThink;
                        setDeepThink(next);
                        try { localStorage.setItem("antar_expert", next ? "1" : "0"); } catch {}
                        window.dispatchEvent(new CustomEvent("antar-expert", { detail: { on: next } }));
                      }} />
                    : (kn ? "ಅಂತರ್ ಸಿಸ್ಟಮ್" : "Antar System")}
                </div>

                {/* Right controls: Mic + Paperclip + Blue Rounded Square Send Button */}
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <WhisperMicButton recording={recording} onClick={toggleVoice} kn={kn} />
                  
                  <button
                    type="button"
                    disabled={!input.trim()}
                    onClick={() => send(input)}
                    style={{
                      width: "34px",
                      height: "34px",
                      borderRadius: "10px",
                      background: input.trim() ? "#2563EB" : "rgba(255, 255, 255, 0.12)",
                      border: "none",
                      color: "#FFFFFF",
                      cursor: input.trim() ? "pointer" : "default",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      transition: "color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s"
                    }}
                  >
                    <ArrowUp size={17} strokeWidth={2.5} />
                  </button>
                </div>
              </div>
              </>
            )}
            </motion.div>



            {/* Suggested questions: six small pills in two lines, a refresh, and the year row */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.4 }}
              // Inline, not in the scoped <style jsx> below: styled-jsx does not reach the
              // element a motion component renders, so its margin and gap were 0.
              style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "14px",
                       marginTop: "22px", maxWidth: "760px", width: "100%" }}
            >
              {(() => {
                // A year picked below replaces these with that year's questions.
                const list = askYear ? yearQuestions(askYear, lang) : rotatorStarters;
                const off = list.length ? starterOffset % list.length : 0;
                const shown = [...list.slice(off), ...list.slice(0, off)].slice(0, 6);
                return (
                  <div className="sq-row">
                    <div className="sq-grid">
                      {shown.map((s) => (
                        <button key={s} type="button" className="sq-q" title={s} onClick={() => send(s)}>{s}</button>
                      ))}
                    </div>
                    {list.length > 6 && (
                      <button type="button" className="sq-more" onClick={() => setStarterOffset((o) => o + 6)}
                              title={kn ? "ಇನ್ನಷ್ಟು ಪ್ರಶ್ನೆಗಳನ್ನು ತೋರಿಸಿ" : "Show more questions"}
                              aria-label={kn ? "ಇನ್ನಷ್ಟು ಪ್ರಶ್ನೆಗಳನ್ನು ತೋರಿಸಿ" : "Show more questions"}>
                        <RefreshCw size={11} />
                      </button>
                    )}
                  </div>
                );
              })()}
              <YearQuestions lang={lang} year={askYear} onYear={(y) => { setAskYear(y); setStarterOffset(0); }} />
              <style jsx>{`
                .sq-row { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; max-width: 740px; }
                .sq-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px 12px; flex: 1; min-width: 0; }
                @media (max-width: 640px) { .sq-grid { grid-template-columns: 1fr; } .sq-q { -webkit-line-clamp: unset; display: block; min-height: 0; } }
                .sq-q { min-width: 0; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
                  white-space: normal; text-align: center; background: transparent;
                  border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 12px; padding: 8px 12px; cursor: pointer; min-height: 44px; align-content: center;
                  font: 400 11.5px/1.4 'Inter', sans-serif; color: rgba(255, 255, 255, 0.55); transition: color 0.15s, border-color 0.15s; }
                .sq-q:hover { color: #fff; border-color: rgba(255, 255, 255, 0.2); }
                .sq-more { width: 22px; height: 22px; padding: 0; display: inline-flex; align-items: center; justify-content: center;
                  border-radius: 50%; border: none; background: rgba(255, 255, 255, 0.04); color: rgba(255, 255, 255, 0.5); cursor: pointer; }
                .sq-more:hover { background: rgba(255, 255, 255, 0.1); color: #fff; }
              `}</style>
            </motion.div>

            {/* Professional tiny footer note below prompt box */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              style={{
                marginTop: "16px",
                fontSize: "10px",
                color: docsMode ? "#60A5FA" : "rgba(255, 255, 255, 0.42)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
                fontFamily: "'Inter', sans-serif",
                cursor: "pointer",
                padding: "2px 10px",
                borderRadius: "9999px",
                background: docsMode ? "rgba(59, 130, 246, 0.1)" : "transparent",
                border: docsMode ? "1px solid rgba(59, 130, 246, 0.2)" : "1px solid transparent",
                transition: "color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s"
              }}
              onClick={() => setDocsMode(!docsMode)}
            >
              <span>
                {docsMode
                  ? "Questions are answered through Docs. Click to switch it off."
                  : "Direct Chat mode active. Click to enable Docs mode."}
              </span>
            </motion.div>


          </div>
        </div>
        </>
      ) : (
        <>
          <AnimatePresence>
            {launch && <LaunchStage key="launch" q={launch.q} msg={last} kn={kn} onStop={() => { stopChat(); setLaunch(null); }} />}
          </AnimatePresence>
          <div className="cx-thread cx-enter" ref={scrollRef} aria-live="polite" style={{ paddingTop: "68px" }}>
            <div className="cx-threadcol">
            {messages.map((m, i) => (
              <MessageRow key={i} m={m} i={i} prevMessage={messages[i - 1]} kn={kn} lang={lang} deepThink={deepThink} sessionId={sessionId} router={router} send={actions.send} setMessages={setMessages} showNetwork={actions.showNetwork} exportReport={actions.exportReport} translateAnswer={actions.translateAnswer} rateAnswer={actions.rateAnswer} toggleWhy={actions.toggleWhy} />
            ))}
            {/* Never while an answer is on its way ("Thinking..." or still streaming): a
                suggestion offered mid-answer invites a second question before the first lands. */}
            {!loading && !(last && (last.role === "user" || last.streaming)) && (showSuggestions?.length > 0 || roleSuggestions.length > 0) && (
              <div className="cx-suggwrap">
                {showSuggestions?.length > 0 && (
                  <div className="cx-chips" style={{ justifyContent: "flex-start" }}>
                    <span className="cx-sugg-lab">{kn ? "ಸಂಬಂಧಿತ" : "Related"}</span>
                    {showSuggestions.slice(0, 3).map((s, i) => (
                      <button key={s} className={`cx-chip cx-sugg ${kn ? "kn" : ""}`}
                              style={{ animationDelay: `${i * 110}ms` }} onClick={() => send(s)}>
                        {s}
                      </button>
                    ))}
                  </div>
                )}
                {roleSuggestions.length > 0 && (
                  <div className="cx-chips" style={{ justifyContent: "flex-start" }}>
                    <span className="cx-sugg-lab cx-sugg-lab-role">
                        {kn ? "ಸೂಚಿಸಲಾಗಿದೆ" : "Suggested"}
                      </span>
                    {roleSuggestions.map((s, i) => (
                      <button key={s} className={`cx-chip cx-sugg cx-sugg-role ${kn ? "kn" : ""}`}
                              style={{ animationDelay: `${(i + 3) * 110}ms` }} onClick={() => send(s)}>
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {/* Scrolled away mid-answer → offer the way back instead of yanking them down.
                Sticky (not absolute): .cx-thread is the scroll container, so an absolute
                child would scroll away with the content instead of hovering. */}
            {/* Room for the pinned question to reach the top (see answer-first scrolling). */}
            <div aria-hidden="true" className="cx-tail" style={{ height: tailPad }} />
            {/* Only offered once the answer is longer than the screen - before that the
                spacer is what sits below, and there is nothing further to jump to. */}
            {!atBottom && tailPad === 0 && (
              <button type="button" className="cx-jump"
                      onClick={() => { setAtBottom(true); scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }}>
                ↓ {kn ? "ಇತ್ತೀಚಿನದಕ್ಕೆ" : "Jump to latest"}
              </button>
            )}
            </div>
          </div>

          <div className="cx-composer-v2">
            <div className="cx-comprow">
              <span className="sp" />
              {sessionId && <button className="cx-export" onClick={exportReport} title="Export an intelligence report">{kn ? "ರಫ್ತು" : "Export"}</button>}
            </div>

            {/* Suggested questions: 6 pills grid with refresh and by-year filter, same as requested */}
            {!hasUserTurn && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "12px",
                  marginBottom: "16px",
                  maxWidth: "760px",
                  width: "100%"
                }}
              >
                {(() => {
                  const fallbackList = STARTERS[lang] || STARTERS.en;
                  const list = askYear ? yearQuestions(askYear, lang) : (rotatorStarters?.length ? rotatorStarters : fallbackList);
                  const off = list.length ? starterOffset % list.length : 0;
                  const shown = [...list.slice(off), ...list.slice(0, off)].slice(0, 6);
                  return (
                    <div className="sq-row">
                      <div className="sq-grid">
                        {shown.map((s) => (
                          <button key={s} type="button" className="sq-q" title={s} onClick={() => send(s)}>{s}</button>
                        ))}
                      </div>
                      {list.length > 6 && (
                        <button type="button" className="sq-more" onClick={() => setStarterOffset((o) => o + 6)}
                                title={kn ? "ಇನ್ನಷ್ಟು ಪ್ರಶ್ನೆಗಳನ್ನು ತೋರಿಸಿ" : "Show more questions"}
                                aria-label={kn ? "ಇನ್ನಷ್ಟು ಪ್ರಶ್ನೆಗಳನ್ನು ತೋರಿಸಿ" : "Show more questions"}>
                          <RefreshCw size={11} />
                        </button>
                      )}
                    </div>
                  );
                })()}
                <YearQuestions lang={lang} year={askYear} onYear={(y) => { setAskYear(y); setStarterOffset(0); }} />
              </div>
            )}
            <div className="cx-searchwrap">{searchBar}</div>
            <div className="cx-hint">
              {kn ? "ಕಳುಹಿಸಲು Enter · ಮಾತನಾಡಲು ಮೈಕ್" : "Enter to send · Shift+Enter = new line · tap the mic to speak"}
              {mode ? `  ·  ${mode === "llm" ? "Catalyst LLM" : "offline"}` : ""}
              {ops && (
                <span title={kn
                  ? "ಲೈವ್ ಆರ್ಕೆಸ್ಟ್ರೇಟರ್ ಟೆಲಿಮೆಟ್ರಿ - ನೈಜ ಏಜೆಂಟ್ ಕರೆಗಳು"
                  : "Live orchestrator telemetry - real agent calls measured on the backend, refreshed after every answer"}>
                  {`  ·  orchestrated: ${ops.calls} agent call(s)${ops.queryMs != null ? ` · query ${ops.queryMs}ms` : ""}`}
                </span>
              )}
              <span style={{ display: "block", marginTop: "2px", opacity: 0.7 }}>
                {kn ? "Antar ತಪ್ಪು ಮಾಡಬಹುದು - ಉಲ್ಲೇಖಿತ FIR ದಾಖಲೆಗಳೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ." : "Antar can make mistakes - verify with the cited FIR records."}
              </span>
            </div>
          </div>
          {workspaceOn && (
            <ExpertWorkspace
              answer={lastAssistant?.text || ""}
              question={lastUserQ}
              citations={lastAssistant?.citations || []}
              suspects={lastAssistant?.suspects || []}
              sessionId={sessionId}
              kn={kn}
              meta={{
                template_id: lastAssistant?.template || null,
                elapsed_ms: typeof lastAssistant?.thoughtMs === "number" ? lastAssistant.thoughtMs : null,
                hash: lastAssistant?.auditHash || null,
                method: lastAssistant?.method || null,
                rows: lastAssistant?.rowCount,
                agents: lastAssistant?.agents || [],
                mode: lastAssistant?.mode || null,
                confidence: lastAssistant?.confidence,
                lang: lastAssistant?.lang || lang,
                no_results: !!lastAssistant?.noResults,
              }}
              trace={[...(lastAssistant?.steps || []), ...(lastAssistant?.reasoning || [])]}
              claims={lastAssistant?.layout?.kdiu || []}
              evidenceClass={lastAssistant?.layout?.evidence_class || null}
              onClose={() => {
                setDeepThink(false);
                try { localStorage.setItem("antar_expert", "0"); } catch {}
                window.dispatchEvent(new CustomEvent("antar-expert", { detail: { on: false } }));
              }}
            />
          )}
        </>
      )}

      {/* Minimal One-Minute Guide Modal */}
      <AnimatePresence>
        {tourOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -6 }}
            style={{
              position: "fixed",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: "310px",
              maxWidth: "90vw",
              background: "rgba(15, 17, 23, 0.96)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "12px",
              padding: "14px 16px",
              boxShadow: "0 12px 36px rgba(0, 0, 0, 0.8)",
              backdropFilter: "blur(16px)",
              WebkitBackdropFilter: "blur(16px)",
              zIndex: 99999,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <span style={{ color: "#F8FAFC", fontWeight: 600, fontSize: "13px", fontFamily: "'Inter', sans-serif" }}>
                {kn ? "ಒಂದು ನಿಮಿಷದ ಮಾರ್ಗದರ್ಶಿ" : "One-Minute Guide"}
              </span>
              <button
                type="button"
                onClick={() => setTourOpen(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#71717A",
                  cursor: "pointer",
                  fontSize: "13px",
                  padding: "2px",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                
              </button>
            </div>

            <p style={{ fontSize: "11.5px", color: "#A1A1AA", lineHeight: 1.45, margin: "0 0 12px 0" }}>
              {kn
                ? "18 ಏಜೆಂಟ್‌ಗಳ ಮೂಲಕ ನೈಜ FIR ವಿಶ್ಲೇಷಣೆ ಮತ್ತು ಅಪರಾಧ ಮುನ್ಸೂಚನಾ ವ್ಯವಸ್ಥೆ."
                : "18-agent crime intelligence platform for live FIR analysis & forecasting."}
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
              {[
                { cmd: "/ask", desc: kn ? "ಆಳವಾದ ತನಿಖೆ" : "Deep investigation" },
                { cmd: "/connect", desc: kn ? "ಅಪರಾಧ ಜಾಲಗಳು" : "Syndicate networks" },
                { cmd: "/map", desc: kn ? "ಹಾಟ್‌ಸ್ಪಾಟ್ ನಕ್ಷೆ" : "Hotspot & patrol mapping" },
                { cmd: "/predict", desc: kn ? "ಪ್ರವೃತ್ತಿ ಮುನ್ಸೂಚನೆ" : "Crime trend forecast" },
                { cmd: "/search", desc: kn ? "ದಾಖಲೆಗಳ ಹುಡುಕಾಟ" : "Record search" },
              ].map((item) => (
                <div
                  key={item.cmd}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "4px 8px",
                    background: "rgba(255, 255, 255, 0.03)",
                    borderRadius: "6px",
                    fontSize: "11px",
                  }}
                >
                  <code style={{ color: "#E2E8F0", fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
                    {item.cmd}
                  </code>
                  <span style={{ color: "#71717A" }}>{item.desc}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {graph && (
        <div className="cx-overlay" onClick={() => setGraph(null)}>
          <div className="cx-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cx-modal-head">
              <strong>{kn ? "ಅಪರಾಧ ಜಾಲ" : "Criminal network"} - {graph.name}</strong>
              <button className="cx-export" onClick={() => setGraph(null)} aria-label="Close"></button>
            </div>
            {graph.loading && <div className="cx-thinking" style={{ padding: 30 }}><span className="animated-dots">{kn ? "ಜಾಲ ನಿರ್ಮಿಸಲಾಗುತ್ತಿದೆ" : "Building graph"}</span></div>}
            {graph.error && (
              <div className="cx-disclaimer-box" style={{ margin: 24 }}>
                <span className="disclaimer-icon">i</span>
                <span className="disclaimer-text">
                  {kn
                    ? "ಬ್ಯಾಕೆಂಡ್ ತಲುಪಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ - ಜಾಲ ಲಭ್ಯವಿಲ್ಲ. ಸರ್ವರ್ ಪ್ರಾರಂಭಿಸಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."
                    : "Backend unreachable - the network graph could not be loaded. Start the Antar API and try again."}
                </span>
              </div>
            )}
            {graph.data?.brain_banner && <div className="cx-brain-banner">{graph.data.brain_banner}</div>}
            {graph.data?.nodes && <NetworkGraph data={graph.data} />}
            {graph.data?.nodes && (
              <div className="cx-legend">
                <span>suspect (queried)</span><span>cross-case (Second Brain)</span><span>associate</span>
                <span>· {graph.data.stats?.node_count} nodes, {graph.data.stats?.edge_count} links</span>
              </div>
            )}
          </div>
        </div>
      )}


      {/* ScreenTransition3D Loading Overlay */}
      <AnimatePresence>
        {pipelineStep !== null && (
          <motion.div
            key="transition-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18, ease: "easeInOut" }}
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 999999,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "rgba(5, 8, 16, 0.45)",
              backdropFilter: "blur(12px)",
              WebkitBackdropFilter: "blur(12px)",
              overflow: "hidden"
            }}
          >
            {/* Central Video Container */}
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 1.05, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              style={{
                width: "180px", 
                height: "180px",
                borderRadius: "50%",
                overflow: "hidden",
                position: "relative",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 40px rgba(34, 230, 240, 0.3), inset 0 0 20px rgba(34, 230, 240, 0.2)",
                border: "1px solid rgba(34, 230, 240, 0.4)",
                background: "#000"
              }}
            >
              <video 
                src={asset("/brand/video/loading.mp4")}
                autoPlay
                loop
                muted
                playsInline
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                }}
              />
            </motion.div>
            
            {/* Outer Ring for extra polish */}
            <motion.div
              animate={{ rotateZ: 360 }}
              transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
              style={{
                position: "absolute",
                width: "210px",
                height: "210px",
                borderRadius: "50%",
                border: "1px dashed rgba(34, 230, 240, 0.4)",
                pointerEvents: "none"
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}


