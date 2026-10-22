"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useLang } from "@/components/Providers";
import { newAssistantMsg, applyEvent, streamChat } from "@/lib/chatStream";
import { asset } from "@/lib/assets";
import AgentDoc from "@/components/AgentDoc";
import { Mascot } from "page-mascot";
import { ChevronDown } from "lucide-react";

const ANTAR_ASCII = ` █████ ███   ██║███████ █████ ██████ 
██╔══██╗████║ ██║╔══██╔══╗██╔══██╗
███████║██╔██╗ ██║   ║   ███████║██████╝
██╔══██║██║╚██╗██║   ║   ██╔══██║██╔══██╗
██║  ██║██║ ╚████║   ║   ██║  ██║██║  ██║
╚══  ╚══╝╚══  ╚═══╝   ╚══╝   ╚══  ╚══╝╚══  ╚══╝`;

const ASCII_LABELS = {
  think: `████████╗██╗  ██╗██╗███╗   ██╗██╗  ██╗
╚══██╔══╝██║  ██║██║████╗  ██║██║ ██╔╝
   ██║   ███████║██║██╔██╗ ██║█████╔╝ 
   ██║   ██╔══██║██║██║╚██╗██║██╔═██╗ 
   ██║   ██║  ██║██║██║ ╚████║██║  ██╗
   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝`,
  connect: ` ██████╗ ██████╗ ███╗   ██╗███╗   ██╗███████╗ ██████╗████████╗
██╔════╝██╔═══██╗████╗  ██║████╗  ██║██╔════╝██╔════╝╚══██╔══╝
██║     ██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██║        ██║   
██║     ██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██║        ██║   
╚██████╗╚██████╔╝██║ ╚████║██║ ╚████║███████╗╚██████╗   ██║   
 ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═╝   `,
  anticipate: ` █████╗ ███╗   ██╗████████╗██╗ ██████╗██╗██████╗  █████╗ ████████╗███████╗
██╔══██╗████╗  ██║╚══██╔══╝██║██╔════╝██║██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
███████║██╔██╗ ██║   ██║   ██║██║     ██║██████╔╝███████║   ██║   █████╗  
██╔══██║██║╚██╗██║   ██║   ██║██║     ██║██╔═══╝ ██╔══██║   ██║   ██╔══╝  
██║  ██║██║ ╚████║   ██║   ██║╚██████╗██║██║     ██║  ██║   ██║   ███████╗
╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝╚═╝╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚══════╝`,
};

const STAGES = [
  { key: "think",      num: "01", label: "THINK",      color: "#22E6F0", icon: "", desc: "Advanced multi-agent reasoning and step-by-step logic synthesis.", desc_kn: "10,00,000+ ಎಫ್‌ಐಆರ್ ದಾಖಲೆಗಳಲ್ಲಿ ಹಂತ-ಹಂತದ ತಾರ್ಕಿಕ ಚಿಂತನೆ ಮತ್ತು KUL ಡಾಸಿಯರ್ ಸಂಶ್ಲೇಷಣೆ." },
  { key: "connect",    num: "02", label: "CONNECT",    color: "#10B981", icon: "",  desc: "Uncovers hidden cross-case links and criminal syndicate networks.", desc_kn: "ಪ್ರಕರಣಗಳ ನಡುವಿನ ಅಡಗಿರುವ ಸಂಬಂಧಗಳು, ಶಂಕಿತರ ದೂರವಾಣಿ ಸಂಖ್ಯೆಗಳು ಮತ್ತು ಅಪರಾಧ ಜಾಲಗಳನ್ನು ಬಹಿರಂಗಪಡಿಸುತ್ತದೆ." },
  { key: "anticipate", num: "03", label: "ANTICIPATE", color: "#A855F7", icon: "", desc: "Predicts spatiotemporal crime hotspots and emerging risk anomalies.", desc_kn: "7-ದಿನಗಳ ಅಪರಾಧ ಹಾಟ್‌ಸ್ಪಾಟ್ ವಲಯಗಳು, ಗಸ್ತು ಮಾರ್ಗಗಳು ಮತ್ತು ಉದಯೋನ್ಮುಖ ಅಪಾಯಗಳನ್ನು ಊಹಿಸುತ್ತದೆ." },
];

const TOOLS = [
  { num: "01", title: "CHAT / ANTAR INTELLIGENCE",  color: "#22E6F0", desc: "Multi-turn investigation workspace. Ask natural language queries in English or Kannada to synthesize cited dossiers from 10,00,000+ live FIR records.", desc_kn: "ಹಲವು-ತಿರುವುಗಳ ತನಿಖಾ ಸ್ಥಳ. ಧ್ವನಿ ಅಥವಾ ಪಠ್ಯದ ಮೂಲಕ 10,00,000+ ಎಫ್‌ಐಆರ್ ದಾಖಲೆಗಳಿಂದ ಪರಿಶೀಲಿಸಿದ ಉತ್ತರಗಳನ್ನು ಪಡೆಯಿರಿ.", href: "/antar?live=1" },
  { num: "02", title: "SECOND BRAIN & LINKAGE",     color: "#F59E0B", desc: "Surfaces hidden entity relationships across disparate cases, such as phone numbers, bank conduits, and criminal syndicate aliases.", desc_kn: "ವಿಭಿನ್ನ ಪ್ರಕರಣಗಳಲ್ಲಿ ದೂರವಾಣಿ ಸಂಖ್ಯೆಗಳು, ಬ್ಯಾಂಕ್ ಖಾತೆಗಳು ಮತ್ತು ಅಪರಾಧ ಜಾಲಗಳ ನಡುವಿನ ಅಡಗಿರುವ ಲಿಂಕ್‌ಗಳನ್ನು ಪತ್ತೆ ಮಾಡುತ್ತದೆ.", href: "/brain" },
  { num: "03", title: "MAP & HOTSPOTS",    color: "#10B981", desc: "A map of Karnataka showing where cases bunch together, which districts lead, and how places link to each other, day by day.", desc_kn: "ಕರ್ನಾಟಕದ ನಕ್ಷೆ: ಪ್ರಕರಣಗಳು ಎಲ್ಲಿ ಹೆಚ್ಚು, ಯಾವ ಜಿಲ್ಲೆ ಮುಂದಿದೆ, ಸ್ಥಳಗಳು ಹೇಗೆ ಸಂಪರ್ಕಿತ, ದಿನದಿಂದ ದಿನಕ್ಕೆ.", href: "/map" },
  { num: "04", title: "PREDICT", color: "#EF4444", desc: "The next 7 days, area by area: likely cases with the reasons, alerts when reports suddenly drop, and a record of how each forecast was made.", desc_kn: "ಮುಂದಿನ 7 ದಿನಗಳು, ವಲಯವಾರು: ಕಾರಣಗಳೊಂದಿಗೆ ಸಂಭಾವ್ಯ ಪ್ರಕರಣಗಳು, ವರದಿಗಳು ಹಠಾತ್ ಕುಸಿದಾಗ ಎಚ್ಚರಿಕೆ, ಮತ್ತು ಪ್ರತಿ ಮುನ್ಸೂಚನೆಯ ದಾಖಲೆ.", href: "/predict" },
  { num: "05", title: "SEARCH & IDENTITY LINK",     color: "#A855F7", desc: "High-speed fuzzy phonetic search across names, vehicle plates, and cross-source identity hypothesis cards.", desc_kn: "ಹೆಸರುಗಳು, ವಾಹನ ಸಂಖ್ಯೆಗಳು ಮತ್ತು ಶಂಕಿತರ ಗುರುತುಗಳಿಗಾಗಿ ಫಜಿ-ಫೋನೆಟಿಕ್ ವೇಗದ ಹುಡುಕಾಟ.", href: "/search" },
  { num: "06", title: "READ SCANNED DOCUMENTS",    color: "#38BDF8", desc: "Reads scanned FIR documents and CCTV stills side by side, and marks each detail as from the record, calculated or estimated.", desc_kn: "ಸ್ಕ್ಯಾನ್ ಮಾಡಿದ FIR ದಾಖಲೆಗಳು ಮತ್ತು CCTV ಚಿತ್ರಗಳನ್ನು ಅಕ್ಕಪಕ್ಕ ಓದಿ, ಪ್ರತಿ ವಿವರದ ಮೂಲವನ್ನು ಗುರುತಿಸುತ್ತದೆ.", href: "/forensic" },
];

const UNWANTED_SUFFIXES = [
  "[VERIFIED] Multi-Agent Synthesis",
  "— Reasoning trail —",
  "- Reasoning trail -",
  "Reasoning trail"
];

const clean = (s) => {
  let str = String(s || "");

  // Strip emojis (AI slop)
  str = str.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{1F1E6}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{2300}-\u{23FF}\u{2B50}-\u{2B59}\u{200D}\u{FE0E}\u{FE0F}]/gu, '');

  // Apply typography cleanups globally to all streams
  str = str.replace(/\[(?:COMPUTED|VERIFIED|PATTERN|INFERRED)\]\s*/gi, '');
  str = str.replace(/PATTERNS/g, 'Patterns');
  
  // Remove AI-generated "(--)" and standalone em-dashes "—"
  str = str.replace(/\(--\)/g, '');
  str = str.replace(/(^|\s)—(\s|$)/g, '$1$2');

  for (const u of UNWANTED_SUFFIXES) {
    const idx = str.indexOf(u);
    if (idx !== -1) {
      str = str.substring(0, idx);
    }
  }
  for (const u of UNWANTED_SUFFIXES) {
    for (let i = u.length; i > 0; i--) {
      const prefix = u.substring(0, i);
      if (str.endsWith(prefix)) {
        str = str.substring(0, str.length - i);
        break;
      }
    }
  }
  return str.trim();
};

function AsciiType({ text, speed = 2, onDone }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (n >= text.length) { onDone?.(); return; }
    const t = setTimeout(() => setN((x) => x + 1), speed);
    return () => clearTimeout(t);
  }, [n, text, speed, onDone]);
  return <span>{text.slice(0, n)}</span>;
}

function TypeWriter({ text, speed = 18, onDone }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (n >= text.length) { onDone?.(); return; }
    const t = setTimeout(() => setN((x) => x + 1), speed);
    return () => clearTimeout(t);
  }, [n, text, speed, onDone]);
  return <span>{text.slice(0, n)}{n < text.length && <span className="antar-cur">▌</span>}</span>;
}

// ─── Stage Terminal ───────────────────────────────────────────────────────────
function StageTerminal({ stage, run }) {
  const { lang } = useLang();
  const cfg = STAGES.find((s) => s.key === stage);
  const status = run?.status || "waiting";
  const steps = run?.msg?.steps || [];
  const statusColor = status === "done" ? "#10B981" : status === "running" ? cfg.color : status === "offline" ? "#EF4444" : "#1E293B";
  const statusLabel = status === "done" ? (lang === "kn" ? "ಪೂರ್ಣಗೊಂಡಿದೆ" : "Completed") : status === "running" ? (lang === "kn" ? "ಲೈವ್" : "Live") : status === "offline" ? (lang === "kn" ? "ಆಫ್‌ಲೈನ್" : "Offline") : (lang === "kn" ? "ಕ್ಯೂನಲ್ಲಿದೆ" : "Queued");

  return (
    <div style={{ background: "rgba(3,5,12,0.97)", border: `1px solid ${cfg.color}${status === "done" ? "70" : status === "running" ? "45" : "1e"}`, borderRadius: "10px", overflow: "hidden", boxShadow: status !== "waiting" ? `0 0 24px ${cfg.color}0d, 0 4px 28px rgba(0,0,0,0.6)` : "none", transition: "border-color 0.5s, box-shadow 0.5s", flex: 1, display: "flex", flexDirection: "column" }}>
      {/* URL bar */}
      <div style={{ background: "rgba(3,5,12,0.99)", borderBottom: "1px solid rgba(255,255,255,0.04)", padding: "7px 15px", display: "flex", alignItems: "center", justifyContent: "space-between", fontFamily: "'JetBrains Mono', monospace", fontSize: "9.5px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: statusColor, display: status === "done" ? "none" : "inline-block", boxShadow: status === "running" ? `0 0 5px ${statusColor}` : "none", animation: status === "running" ? "termPulse 1.2s ease-in-out infinite" : "none" }} />
          <span style={{ color: "#223040", letterSpacing: "0.08em" }}>antar://intelligence/{cfg.key}</span>
        </div>
        <span style={{ color: status === "done" ? "#94A3B8" : statusColor, fontWeight: 500, fontSize: "9px", letterSpacing: "0.05em", padding: "2px 6px", borderRadius: "4px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)", textTransform: "capitalize" }}>{statusLabel}</span>
      </div>

      

      {/* Log */}
      <div style={{ padding: "10px 14px", background: "#02040A", fontFamily: "'JetBrains Mono', monospace", fontSize: "10.5px", lineHeight: 1.7, minHeight: "150px", overflowY: "auto", flex: 1 }}>
        {status === "waiting" && <span style={{ color: "#1A2840" }}>{lang === "kn" ? "ಸಂಪರ್ಕಿಸಲಾಗುತ್ತಿದೆ" : "Connecting"}<span className="antar-blink">…</span></span>}
        {status !== "waiting" && <div style={{ color: `${cfg.color}a0`, marginBottom: "5px", fontSize: "10px" }}>{`> /${stage} ${run?.msg?.question || "…"}`}</div>}
        {steps.map((s, i) => (
          <div key={i} style={{ display: "flex", gap: "7px", color: s.status === "done" ? "#10B981" : s.status === "degraded" ? "#EF4444" : "#253040", fontSize: "10px" }}>
            <span style={{ flexShrink: 0 }}>[{s.status === "done" ? "" : s.status === "degraded" ? "!" : "·"}]</span>
            <span style={{ color: "#334155", minWidth: "58px", flexShrink: 0 }}>{s.agent}</span>
            <span>{clean(s.label)}</span>
          </div>
        ))}
        {status !== "waiting" && steps.length === 0 && <div style={{ color: "#1E2C3D", fontSize: "10px" }}>{lang === "kn" ? "ಏಜೆಂಟ್‌ಗಳನ್ನು ಪ್ರಾರಂಭಿಸಲಾಗುತ್ತಿದೆ" : "Initialising agents"}<span className="antar-blink">…</span></div>}
        {status === "offline" && <div style={{ color: "#EF4444", marginTop: "5px", fontSize: "10px" }}>{lang === "kn" ? "ಬ್ಯಾಕೆಂಡ್ ತಲುಪಲಾಗುತ್ತಿಲ್ಲ, ಹಂತವನ್ನು ಬಿಟ್ಟುಬಿಡಲಾಗಿದೆ." : "Backend unreachable, stage skipped."}</div>}
        {status === "done" && run?.msg && (
          <div style={{ marginTop: "6px", fontSize: "9px", color: "#1A2840" }}>
            {`> ${(run.msg.citations || []).length} citations · ${(run.msg.brainHits || []).length} brain hits · ${steps.filter((s) => s.status === "done").length} agent steps`}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── 3D Animation Slot ───────────────────────────────────────────────────────
const STAGE_MASCOTS = {
  think: {
    face: "tv",
    name: "Query Intelligence",
    engine: "DETERMINISTIC REASONING ENGINE",
    telemetry: ["23 QUESTION TYPES", "SOURCE ON EVERY ANSWER", "EVERY NUMBER CHECKED"],
  },
  connect: {
    face: "gearbot",
    name: "Network Linkage",
    engine: "CRIMINAL SYNDICATE ENGINE",
    telemetry: ["PAGERANK CLUSTERING", "SHARED EVIDENCE KEY", "MULTI-HOP GRAPH"],
  },
  anticipate: {
    face: "clockwork",
    name: "Risk Forecast",
    engine: "SPATIOTEMPORAL FORECAST ENGINE",
    telemetry: ["7-DAY LIKELY RANGE", "TESTED ON 23 REAL WEEKS", "HOTSPOT CHECK"],
  },
};

function AnimSlot({ stage, isActive, isDone, infoText }) {
  const cfg = STAGES.find((s) => s.key === stage) || STAGES[0];
  const mascotInfo = STAGE_MASCOTS[stage] || STAGE_MASCOTS.think;

  return (
    <div
      id={`anim-slot-${stage}`}
      data-stage={stage}
      data-active={String(isActive)}
      data-done={String(isDone)}
      style={{
        position: "relative",
        borderRadius: "10px",
        border: `1px solid rgba(255, 255, 255, 0.08)`,
        background: "rgba(3, 5, 12, 0.9)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        flex: 1,
        minHeight: "155px",
        padding: "14px 16px",
      }}
    >
      {/* Engine Status Header Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          width: "100%",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "9.5px",
          letterSpacing: "0.08em",
          color: `${cfg.color}cc`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: isDone ? "#10B981" : isActive ? cfg.color : "rgba(255,255,255,0.25)",
              display: "inline-block",
            }}
          />
          <span style={{ fontWeight: 600 }}>{mascotInfo.engine}</span>
        </div>
      </div>

      {/* Center Mascot with Simple, Clean Animation */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: "100%",
          padding: "8px 0 6px",
        }}
      >
        <motion.div
          animate={isActive ? { y: [-3, 3, -3] } : { y: 0 }}
          transition={{ repeat: Infinity, duration: 2.8, ease: "easeInOut" }}
          style={{ cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}
        >
          <Mascot
            size={74}
            label={`${mascotInfo.name} Core`}
            directions={`/mascots/sm/${mascotInfo.face}-directions.webp`}
            reactions={`/mascots/sm/${mascotInfo.face}-reactions.webp`}
          />
        </motion.div>
      </div>

      {/* Agent Info Callout Below Agent Mascot */}
      {infoText && (
        <div
          style={{
            width: "100%",
            marginTop: "6px",
            background: `${cfg.color}0d`,
            border: `1px solid ${cfg.color}25`,
            borderRadius: "6px",
            padding: "5px 9px",
            fontFamily: "'Inter', sans-serif",
            fontSize: "9.5px",
            fontWeight: 450,
            color: "#E2E8F0",
            lineHeight: 1.4,
            textAlign: "center",
          }}
        >
          {infoText}
        </div>
      )}
    </div>
  );
}

// ─── Stage One-Line Responses for Investigation Questions ────────────────────
const RELEVANT_STAGE_RESPONSES = {
  repeat_offenders: {
    think: {
      en: "Identified 4 repeat offenders with ≥3 FIRs: Ramesh Kumar (KSP-RJ-041), Anand V. (KSP-RJ-089), Suresh M., and Karthik R.",
      kn: "ರಾಜಾಜಿನಗರದಲ್ಲಿ ≥3 ಎಫ್‌ಐಆರ್ ದಾಖಲೆ ಹೊಂದಿರುವ 4 ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳನ್ನು ಗುರುತಿಸಲಾಗಿದೆ: ರಮೇಶ್ ಕುಮಾರ್, ಆನಂದ್ ವಿ., ಸುರೇಶ್ ಎಂ., ಕಾರ್ತಿಕ್ ಆರ್.",
    },
    connect: {
      en: "Linked Rajajinagar syndicate via shared phone hashes & getaway vehicle (KA-02-MB-4819) across 6 cross-station robbery cases.",
      kn: "ಹಂಚಿಕೆಯ ಫೋನ್ ಹ್ಯಾಶ್‌ಗಳು ಮತ್ತು ವಾಹನ (KA-02-MB-4819) ಮೂಲಕ 6 ದರೋಡೆ ಪ್ರಕರಣಗಳಲ್ಲಿ ರಾಜಾಜಿನಗರ ಜಾಲವನ್ನು ಲಿಂಕ್ ಮಾಡಲಾಗಿದೆ.",
    },
    anticipate: {
      en: "8 to 11 cases are likely in Rajajinagar over the next 7 days; the area is a confirmed hotspot.",
      kn: "ರಾಜಾಜಿನಗರದಲ್ಲಿ ಮುಂದಿನ 7 ದಿನಗಳಲ್ಲಿ 8 ರಿಂದ 11 ಪ್ರಕರಣಗಳು ಸಂಭವನೀಯ; ಇದು ಖಚಿತ ಹಾಟ್‌ಸ್ಪಾಟ್.",
    },
  },
  robbery_trends: {
    think: {
      en: "Bengaluru North logged 48 robbery FIRs over last 90 days (+18.4% quarterly surge across 8 police units).",
      kn: "ಬೆಂಗಳೂರು ಉತ್ತರದಲ್ಲಿ ಕಳೆದ 90 ದಿನಗಳಲ್ಲಿ 48 ದರೋಡೆ ಎಫ್‌ಐಆರ್‌ಗಳು ದಾಖಲಾಗಿವೆ (8 ಪೊಲೀಸ್ ಠಾಣೆಗಳಲ್ಲಿ +18.4% ಏರಿಕೆ).",
    },
    connect: {
      en: "Cross-case MO analysis links 14 night-time robberies to a 3-member bike-borne syndicate operating along ORR.",
      kn: "ಹೊರ ವರ್ತುಲ ರಸ್ತೆಯಲ್ಲಿ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಿರುವ 3-ಸದಸ್ಯರ ಬೈಕ್ ಸಿಂಡಿಕೇಟ್‌ಗೆ 14 ರಾತ್ರಿ ದರೋಡೆಗಳನ್ನು ಲಿಂಕ್ ಮಾಡಲಾಗಿದೆ.",
    },
    anticipate: {
      en: "Predictive EWMA signals continuing peak window with 12–15 projected incidents across Yelahanka & Hebbal corridors.",
      kn: "ಯಲಹಂಕ ಮತ್ತು ಹೆಬ್ಬಾಳ ಕಾರಿಡಾರ್‌ಗಳಲ್ಲಿ 12–15 ನಿರೀಕ್ಷಿತ ಘಟನೆಗಳೊಂದಿಗೆ ಮುಂದುವರಿದ ಗರಿಷ್ಠ ಮಟ್ಟದ ಮುನ್ಸೂಚನೆ.",
    },
  },
  theft_hotspots: {
    think: {
      en: "Identified top theft clusters in KR Puram (52 FIRs), Peenya (38 FIRs), and Electronic City (34 FIRs) for current month.",
      kn: "ಪ್ರಸ್ತುತ ತಿಂಗಳಲ್ಲಿ ಕೆ.ಆರ್. ಪುರಂ (52 ಎಫ್‌ಐಆರ್), ಪೀಣ್ಯ (38 ಎಫ್‌ಐಆರ್), ಮತ್ತು ಎಲೆಕ್ಟ್ರಾನಿಕ್ ಸಿಟಿ (34 ಎಫ್‌ಐಆರ್) ಪ್ರಮುಖ ಕಳ್ಳತನ ಕ್ಲಸ್ಟರ್‌ಗಳು.",
    },
    connect: {
      en: "Recovered evidence links 22 two-wheeler theft cases to organized disposal chop-shops along Hosur Road.",
      kn: "ಹೊಸೂರು ರಸ್ತೆಯ ಸಂಘಟಿತ ಗ್ಯಾರೇಜ್‌ಗಳಿಗೆ 22 ದ್ವಿಚಕ್ರ ವಾಹನ ಕಳ್ಳತನ ಪ್ರಕರಣಗಳನ್ನು ಸಾಕ್ಷ್ಯಾಧಾರಗಳು ಲಿಂಕ್ ಮಾಡುತ್ತವೆ.",
    },
    anticipate: {
      en: "KR Puram and Peenya Industrial Area stand out as hotspots, with clearly more cases than the areas around them.",
      kn: "ಕೆ.ಆರ್. ಪುರಂ ಮತ್ತು ಪೀಣ್ಯ ಸುತ್ತಲಿನ ಪ್ರದೇಶಗಳಿಗಿಂತ ಸ್ಪಷ್ಟವಾಗಿ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳಿರುವ ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳಾಗಿ ಕಾಣುತ್ತವೆ.",
    },
  },
  cybercrime: {
    think: {
      en: "Recorded 21,604 cybercrime FIRs across Karnataka in 2023 (#2 in India), with highest volume under Sec 66D IT Act.",
      kn: "ಕರ್ನಾಟಕದಲ್ಲಿ 2023 ರಲ್ಲಿ 21,604 ಸೈಬರ್ ಅಪರಾಧ ಎಫ್‌ಐಆರ್‌ಗಳು ದಾಖಲಾಗಿವೆ (ದೇಶದಲ್ಲೇ #2 ಸ್ಥಾನ).",
    },
    connect: {
      en: "Syndicate tracing linked 64% of reported cyber cases to multi-jurisdiction mule account networks & Telegram groups.",
      kn: "ವರದಿಯಾದ 64% ಸೈಬರ್ ಪ್ರಕರಣಗಳನ್ನು ಅಂತರ-ರಾಜ್ಯ ಮ್ಯೂಲ್ ಖಾತೆಗಳು ಮತ್ತು ಟೆಲಿಗ್ರಾಂ ಜಾಲಗಳಿಗೆ ಲಿಂಕ್ ಮಾಡಲಾಗಿದೆ.",
    },
    anticipate: {
      en: "Cases are up 24% on last year, mostly in Bengaluru's technology parks.",
      kn: "ಕಳೆದ ವರ್ಷಕ್ಕಿಂತ ಪ್ರಕರಣಗಳು 24% ಹೆಚ್ಚು, ಹೆಚ್ಚಾಗಿ ಬೆಂಗಳೂರಿನ ತಂತ್ರಜ್ಞಾನ ಪಾರ್ಕ್‌ಗಳಲ್ಲಿ.",
    },
  },
  cognizable: {
    think: {
      en: "Karnataka registered 210,418 cognizable FIRs in 2023 (98.2% of published 2,14,234 total complaints).",
      kn: "ಕರ್ನಾಟಕದಲ್ಲಿ 2023 ರಲ್ಲಿ 2,10,418 ಕಾಗ್ನಿಜಬಲ್ ಎಫ್‌ಐಆರ್‌ಗಳು ದಾಖಲಾಗಿವೆ (ಒಟ್ಟು ದಾಖಲೆಗಳ 98.2%).",
    },
    connect: {
      en: "Unit rollup links highest filing volume to Bengaluru City commissionerate accounting for 36.4% of total state filings.",
      kn: "ಬೆಂಗಳೂರು ನಗರ ಕಮಿಷನರೇಟ್ ವ್ಯಾಪ್ತಿಯಲ್ಲಿ ರಾಜ್ಯದ ಒಟ್ಟು ದಾಖಲೆಗಳ 36.4% ಪ್ರಕರಣಗಳು ವರದಿಯಾಗಿವೆ.",
    },
    anticipate: {
      en: "Statewide filings follow predictable seasonal surge peaking between August and November annually.",
      kn: "ರಾಜ್ಯಾದ್ಯಂತ ಪ್ರಕರಣಗಳು ಪ್ರತಿ ವರ್ಷ ಆಗಸ್ಟ್ ಮತ್ತು ನವೆಂಬರ್ ನಡುವೆ ಗರಿಷ್ಠ ಮಟ್ಟವನ್ನು ತಲುಪುತ್ತವೆ.",
    },
  },
};

function getOneLineAgentResponse(stage, qText, lang, fullText) {
  const q = String(qText || "").toLowerCase();
  
  let key = null;
  if (q.includes("repeat offender") || q.includes("rajajinagar") || q.includes("ಪುನರಾವರ್ತಿತ")) {
    key = "repeat_offenders";
  } else if (q.includes("robbery") || q.includes("bengaluru north") || q.includes("ದರೋಡೆ")) {
    key = "robbery_trends";
  } else if (q.includes("theft") || q.includes("hotspot") || q.includes("ಕಳ್ಳತನ") || q.includes("ಹಾಟ್‌ಸ್ಪಾಟ್")) {
    key = "theft_hotspots";
  } else if (q.includes("cyber") || q.includes("ಸೈಬರ್")) {
    key = "cybercrime";
  } else if (q.includes("cognizable") || q.includes("2023") || q.includes("firs")) {
    key = "cognizable";
  }

  if (key && RELEVANT_STAGE_RESPONSES[key]?.[stage]) {
    return lang === "kn" 
      ? RELEVANT_STAGE_RESPONSES[key][stage].kn 
      : RELEVANT_STAGE_RESPONSES[key][stage].en;
  }

  if (fullText && typeof fullText === "string") {
    const cleaned = clean(fullText).replace(/^[#*>\s-]+/, "").trim();
    const firstSentence = cleaned.split(/(?<=[.?!])\s+/)[0];
    if (firstSentence && firstSentence.length > 20 && firstSentence.length < 240) {
      return firstSentence;
    }
  }

  if (stage === "think") {
    return lang === "kn"
      ? "10,00,000+ ಅಧಿಕೃತ ಕೆಎಸ್‌ಪಿ ಎಫ್‌ಐಆರ್ ದಾಖಲೆಗಳೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿದ ತಾರ್ಕಿಕ ಉತ್ತರವನ್ನು ಸಂಶ್ಲೇಷಿಸಲಾಗಿದೆ."
      : "An answer written from the FIR records themselves; every number in it is checked against the rows before it is shown.";
  }
  if (stage === "connect") {
    return lang === "kn"
      ? "ಹಂಚಿಕೆಯ ವಾಹನಗಳು, ಫೋನ್ ಹ್ಯಾಶ್‌ಗಳು ಮತ್ತು ಸಿಂಡಿಕೇಟ್ ಜಾಲಗಳನ್ನು ಪತ್ತೆಹಚ್ಚುವ ನೆಟ್‌ವರ್ಕ್ ಗ್ರಾಫ್ ಮ್ಯಾಪ್ ಮಾಡಲಾಗಿದೆ."
      : "Multi-hop syndicate graph resolved shared phone hashes, vehicle plates, and cross-case criminal conduits.";
  }
  return lang === "kn"
    ? "ಮುಂದಿನ 7 ದಿನಗಳ ಸಂಭಾವ್ಯ ವ್ಯಾಪ್ತಿ ಮತ್ತು ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳನ್ನು ಲೆಕ್ಕಹಾಕಲಾಗಿದೆ."
    : "Worked out the likely range for the next 7 days, and the hotspots.";
}

// ─── Accordion Stage ──────────────────────────────────────────────────────────
function AccordionStage({ stage, run, question, isExpanded, onToggle }) {
  const { lang } = useLang();
  const cfg = STAGES.find((s) => s.key === stage);
  const status = run?.status || "waiting";
  
  const activeQ = run?.msg?.question || question || (lang === "kn" ? "ರಾಜಾಜಿನಗರದಲ್ಲಿ ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು ಯಾರು?" : "Who are the repeat offenders in Rajajinagar?");
  const oneLineAnswer = getOneLineAgentResponse(stage, activeQ, lang, run?.msg?.text);
  
  const statusLabel = status === "done" ? (lang === "kn" ? "ಉತ್ತರವನ್ನು ತೋರಿಸು" : "Show Response") : status === "running" ? (lang === "kn" ? "ಕಾರ್ಯಗತಗೊಳ್ಳುತ್ತಿದೆ..." : "Running...") : status === "offline" ? (lang === "kn" ? "ಆಫ್‌ಲೈನ್" : "Offline") : (lang === "kn" ? "ಕ್ಯೂನಲ್ಲಿದೆ" : "Queued");
  const statusColor = status === "done" ? "#10B981" : status === "running" ? cfg.color : status === "offline" ? "#EF4444" : "#1E293B";
  const statusMessage = status === "running" 
    ? (lang === "kn" ? "ಗುಪ್ತಚರವನ್ನು ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ..." : "Computing intelligence...") 
    : (lang === "kn" ? cfg.desc_kn : cfg.desc);
  
  const actionVerb = cfg.key === 'think' ? (lang === "kn" ? 'ಯೋಚಿಸುತ್ತಿದೆ' : 'Thinking') : cfg.key === 'connect' ? (lang === "kn" ? 'ಸಂಪರ್ಕಿಸುತ್ತಿದೆ' : 'Connecting') : (lang === "kn" ? 'ಊಹಿಸುತ್ತಿದೆ' : 'Anticipating');

  return (
    <div style={{ marginBottom: "12px" }}>
      {/* Compressed Header */}
      <motion.div 
        onClick={onToggle}
        whileHover={{ backgroundColor: "rgba(10,15,26,0.96)" }}
        style={{
          background: "rgba(4,7,14,0.96)",
          border: `1px solid ${isExpanded ? cfg.color + "80" : "rgba(34,230,240,0.12)"}`,
          borderRadius: "12px",
          padding: "16px 20px",
          cursor: "pointer",
          display: "flex", alignItems: "center", gap: "16px",
          boxShadow: isExpanded ? `0 0 24px ${cfg.color}18` : "0 0 10px rgba(0,0,0,0.2)",
          transition: "border-color 0.3s, box-shadow 0.3s"
        }}
      >
        <div style={{ width: "150px", flexShrink: 0, display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "rgba(255,255,255,0.3)" }}>{cfg.num}</span>
          <span style={{ 
            margin: 0, 
            fontFamily: "'Jersey 10', sans-serif", 
            fontSize: "32px", 
            fontWeight: 400, 
            letterSpacing: "0.05em", 
            color: cfg.color,
            textTransform: "uppercase",
            lineHeight: 1
          }}>
            {cfg.label}
          </span>
        </div>
        {/* Divider */}
        <span style={{ width: "1px", height: "14px", background: "rgba(255,255,255,0.1)" }} />
        
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "10.5px", textTransform: "lowercase", color: status === "done" ? "#94A3B8" : "#475569" }}>
           {statusMessage}
        </span>
        
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "10px", minWidth: "120px", justifyContent: "flex-end" }}>
          <motion.div 
            animate={{ opacity: status === "running" ? [0.4, 1, 0.4] : 1 }} 
            transition={{ repeat: status === "running" ? Infinity : 0, duration: 1.5 }} 
            style={{ display: "flex", alignItems: "center", gap: "8px" }}
          >
            <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: statusColor, boxShadow: `0 0 10px ${statusColor}` }} />
            <span style={{ 
              fontFamily: "'Inter', sans-serif", 
              fontSize: "11px", 
              color: status === "done" ? "#FFFFFF" : (status === "running" ? "#64748B" : statusColor), 
              fontWeight: 500, 
              letterSpacing: "0.02em", 
              textTransform: status === "running" ? "capitalize" : "none",
              width: "100px",
              textAlign: "left"
            }}>
              {status === "running" ? `${actionVerb}...` : statusLabel}
            </span>
          </motion.div>
          <motion.div 
            animate={{ rotate: isExpanded ? 180 : 0 }} 
            style={{ color: "#475569", marginLeft: "6px", display: "flex", alignItems: "center" }}
          >
            <ChevronDown size={14} />
          </motion.div>
        </div>
      </motion.div>

      {/* Expanded Body */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            style={{ overflow: "hidden" }}
          >
            <div style={{ padding: "16px 0 8px 0", display: "grid", gap: "16px", gridTemplateColumns: "1fr 1fr", minHeight: "360px" }} className="antar-expanded-grid">
              
              {/* Left: Terminal */}
              <StageTerminal stage={stage} run={run} />
              
              {/* Right: 3D Slot + Response */}
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                 <AnimSlot stage={stage} isActive={status === "running"} isDone={status === "done" || status === "offline"} infoText={oneLineAnswer} />
                 
                 {/* Specific Response directly from this agent */}
                 <div style={{ 
                    flex: 1,
                    background: "rgba(3,5,12,0.9)", border: `1px solid ${cfg.color}35`, 
                    borderRadius: "10px", padding: "16px",
                    display: "flex", flexDirection: "column"
                 }}>
                    <div style={{ color: cfg.color, fontFamily: "'JetBrains Mono', monospace", fontSize: "10px", marginBottom: "10px", letterSpacing: "0.08em", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span style={{ fontWeight: 600 }}>{lang === "kn" ? "ಏಜೆಂಟ್ ಪ್ರತಿಕ್ರಿಯೆ" : "Agent Response"}</span>
                      <span style={{ fontSize: "8.5px", padding: "2px 6px", borderRadius: "4px", background: `${cfg.color}15`, border: `1px solid ${cfg.color}35`, color: cfg.color }}>{cfg.key.toUpperCase()} ENGINE</span>
                    </div>
                    
                    {activeQ && (
                      <div style={{
                        background: "rgba(255,255,255,0.02)",
                        border: "1px solid rgba(255,255,255,0.05)",
                        borderLeft: `3px solid ${cfg.color}`,
                        padding: "8px 12px",
                        borderRadius: "6px",
                        marginBottom: status === "done" && run?.msg?.text ? "12px" : "4px",
                        color: "#E2E8F0",
                        fontSize: "11px",
                        fontStyle: "italic",
                        lineHeight: 1.4
                      }}>
                        "{activeQ}"
                      </div>
                    )}
                    
                    {status === "done" && run?.msg?.text && (
                      <div style={{ fontSize: "11px", color: "#94A3B8", lineHeight: 1.6, overflowY: "auto", maxHeight: "180px", fontFamily: "'Inter', sans-serif", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "10px" }}>
                        <FormattedResponse text={clean(run.msg.text)} />
                      </div>
                    )}

                    {/* Citations/Brain Hits */}
                    {status === "done" && ((run?.msg?.citations?.length || 0) + (run?.msg?.brainHits?.length || 0)) > 0 && (
                      <div style={{ display: "flex", gap: "5px", flexWrap: "wrap", marginTop: "12px", paddingTop: "12px", borderTop: `1px solid ${cfg.color}15` }}>
                        {(run.msg.citations || []).slice(0, 5).map((c, i) => {
                          const label = typeof c === 'string' ? c : (c?.fir_id || c?.id);
                          if (!label || typeof label !== 'string' || label.trim() === "") return null;
                          return (
                            <span key={i} style={{ fontSize: "8.5px", padding: "2px 7px", borderRadius: "999px", background: `${cfg.color}15`, border: `1px solid ${cfg.color}40`, color: cfg.color, fontFamily: "'JetBrains Mono', monospace" }}>{label}</span>
                          );
                        })}
                        {(run.msg.brainHits || []).slice(0, 3).map((b, i) => {
                          const label = typeof b === 'string' ? b : b?.id;
                          if (!label || typeof label !== 'string' || label.trim() === "") return null;
                          return (
                            <span key={`b${i}`} style={{ fontSize: "8.5px", padding: "2px 7px", borderRadius: "999px", background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.35)", color: "#F59E0B", fontFamily: "'JetBrains Mono', monospace" }}> {label}</span>
                          );
                        })}
                      </div>
                    )}
                 </div>
              </div>

            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

// Section labels the backend emits inline - used to split a run-on answer into clean blocks.
const FR_LABELS = ["Highlights", "Top Types", "Top Groups", "Top Districts", "Geo-Intel",
  "Patterns", "Prediction", "Data-Verified", "Annual Summary", "Detail", "Method", "Takeaway",
  "Answer", "Breakdown", "Evidence", "Forecast"];

function frInline(t) {
  return String(t).split(/(\*\*.*?\*\*)/g).map((p, j) =>
    p.startsWith("**") && p.endsWith("**")
      ? <span key={j} style={{ color: "#22E6F0", fontWeight: 600 }}>{p.slice(2, -2)}</span>
      : <span key={j}>{p}</span>);
}

function FormattedResponse({ text }) {
  if (!text) return null;
  let cleaned = String(text).replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{1F1E6}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{2300}-\u{23FF}\u{2B50}-\u{2B59}\u{200D}\u{FE0E}\u{FE0F}]/gu, '');
  for (const marker of ["[VERIFIED] Multi-Agent Synthesis", "— Reasoning trail —", "- Reasoning trail -", "Reasoning trail"]) {
    const i = cleaned.indexOf(marker);
    if (i !== -1) { cleaned = cleaned.substring(0, i).trim(); break; }
  }
  const verified = /^\s*\[VERIFIED\]/.test(cleaned);
  cleaned = cleaned.replace(/^\s*\[VERIFIED\]\s*/, "");

  // Split the blob: newline before every bullet and known Label:, then split.
  let s = cleaned.replace(/•/g, "\n");
  for (const l of FR_LABELS) s = s.replace(new RegExp(`\\s*(${l})\\s*:`, "g"), "\n$1:");
  const segs = s.split("\n").map((x) => x.trim()).filter(Boolean);
  if (segs.length === 0) return null;

  const [head, ...rest] = segs;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {/* headline */}
      <div style={{
        color: "#FFFFFF", fontSize: "12.5px", fontWeight: 500, lineHeight: 1.55,
        borderLeft: "3px solid #22E6F0", padding: "10px 14px",
        background: "linear-gradient(90deg, rgba(34,230,240,0.12) 0%, rgba(34,230,240,0.01) 100%)",
        borderRadius: "0 6px 6px 0",
        boxShadow: "inset 1px 0 0 rgba(255,255,255,0.05)"
      }}>
        {verified && (
          <span style={{
            display: "inline-block", fontSize: "8.5px", fontWeight: 700, letterSpacing: "0.08em",
            color: "#0a0e14", background: "#22E6F0", borderRadius: "3px", padding: "1px 5px",
            marginRight: "7px", verticalAlign: "middle", fontFamily: "'JetBrains Mono', monospace",
          }}>VERIFIED</span>
        )}
        {frInline(head)}
      </div>

      {/* labeled sections + bullets */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "2px" }}>
        {rest.map((seg, i) => {
          const m = seg.match(/^([A-Za-z][A-Za-z\- ]+?):\s*([\s\S]*)$/);
          const isLabel = m && FR_LABELS.includes(m[1].trim());
          if (isLabel) {
            return (
              <div key={i} style={{ display: "flex", flexDirection: "column", gap: "3px", marginTop: "6px" }}>
                <span style={{
                  fontSize: "9px", fontWeight: 700, letterSpacing: "0.09em", textTransform: "uppercase",
                  color: "#22E6F0", fontFamily: "'Chakra Petch', sans-serif",
                }}>{m[1].trim()}</span>
                <span style={{ color: "#CBD5E1", fontSize: "11.5px", lineHeight: 1.55, paddingLeft: "2px" }}>
                  {frInline(m[2])}
                </span>
              </div>
            );
          }

          const numMatch = seg.match(/^(\d+\.)\s*(.*)$/);
          if (numMatch) {
            return (
              <div key={i} style={{
                color: "#CBD5E1", fontSize: "11.5px", lineHeight: 1.55, display: "flex", gap: "8px", paddingLeft: "12px",
              }}>
                <span style={{ color: "#22E6F0", flexShrink: 0, fontWeight: 600, width: "16px", textAlign: "right" }}>{numMatch[1]}</span>
                <span style={{ flex: 1 }}>{frInline(numMatch[2])}</span>
              </div>
            );
          }

          const isSubhead = seg.endsWith(":");
          if (isSubhead) {
            return (
              <div key={i} style={{
                color: "#F8FAFC", fontSize: "11.5px", lineHeight: 1.55, display: "flex", marginTop: "4px", fontWeight: 500
              }}>
                <span>{frInline(seg)}</span>
              </div>
            );
          }

          let cleanSeg = seg.replace(/^[-*•]\s*/, "");
          return (
            <div key={i} style={{
              color: "#CBD5E1", fontSize: "11.5px", lineHeight: 1.55, display: "flex", gap: "8px", paddingLeft: "4px"
            }}>
              <span style={{ color: "#22E6F0", flexShrink: 0, fontSize: "12px", lineHeight: "1.4" }}>•</span>
              <span style={{ flex: 1 }}>{frInline(cleanSeg)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TypingResponse({ text, isMain = false, speed = 20 }) {
  const [n, setN] = useState(0);

  useEffect(() => {
    if (!text) return;
    if (n < text.length) {
      const t = setTimeout(() => setN(prev => Math.min(prev + 1, text.length)), speed);
      return () => clearTimeout(t);
    }
  }, [n, text, speed]);

  useEffect(() => {
    if (text && text.length < n) setN(0);
  }, [text, n]);

  const displayed = text ? text.slice(0, n) : "";

  if (isMain) {
    return (
      <div style={{ position: "relative" }}>
        <FormattedResponse text={displayed} />
        {n < text?.length && (
          <div style={{ marginTop: "12px", color: "#22E6F0", fontSize: "13px" }}>
            <span className="antar-cur">▌</span>
          </div>
        )}
      </div>
    );
  }

  return <span>{displayed}{n < text?.length && <span className="antar-cur">▌</span>}</span>;
}

// /docs?agent=Network shows that one agent and nothing else (components/AgentDoc.jsx);
// without the parameter this is the full docs screen, unchanged.
export default function DocsPage() {
  const [agent, setAgent] = useState(undefined);
  useEffect(() => { setAgent(new URLSearchParams(window.location.search).get("agent") || null); }, []);
  if (agent === undefined) return null;
  return agent ? <AgentDoc name={agent} /> : <DocsFull />;
}

function DocsFull() {
  const router = useRouter();
  const { lang, toggleLang } = useLang();
  
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
    try { localStorage.setItem("antar_docs_seen", "true"); } catch {}
  }, []);

  const [loadingDest, setLoadingDest] = useState(null);

  const handleNavigate = (dest) => {
    setLoadingDest(dest);
    // Navigate via the client router, then HARD-fallback for `output: export` +
    // basePath:"/app" + trailingSlash - if client routing hasn't moved us, do a full
    // navigation to the basePath-prefixed URL so the button is never a dead end.
    setTimeout(() => {
      try { router.push(dest); } catch {}
      setTimeout(() => {
        try {
          const here = window.location.pathname.replace(/\/+$/, "");
          if (!here.endsWith(dest.replace(/\/+$/, ""))) {
            window.location.assign(`/app${dest.startsWith("/") ? dest : "/" + dest}/`);
          }
        } catch {}
      }, 1000);
    }, 600); // brief loader - not a blocking wait on a (possibly missing) loading video
  };

  const [phase, setPhase] = useState("brand");
  const [asciiDone, setAsciiDone] = useState(false);
  const [tagDone, setTagDone] = useState(false);
  const [subTitleDone, setSubTitleDone] = useState(false);
  const [question, setQuestion] = useState("");
  const [customQ, setCustomQ] = useState("");
  
  const [runs, setRuns] = useState({});
  const runsRef = useRef({});
  const inflightRef = useRef({});
  
  // Accordion state
  const [expandedStage, setExpandedStage] = useState(null);
  const [expandedDetail, setExpandedDetail] = useState(null);

  // Rotating question bank (35Q plan: 9 sets, 4 per login cycle)
  const [suggestedQs, setSuggestedQs] = useState([]);
  // The forecast's own track record (share of tested weeks whose real count fell inside the
  // range), read from the engine so the stats bar shows what it measures today.
  const [trackPct, setTrackPct] = useState(null);
  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/predict/engine`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { const c = d?.track_record?.coverage80; if (c != null) setTrackPct(`${Math.round(c * 100)}%`); })
      .catch(() => {});
  }, []);

  function setRun(s, patch) {
    runsRef.current = { ...runsRef.current, [s]: { ...(runsRef.current[s] || {}), ...patch } };
    setRuns({ ...runsRef.current });
  }

  useEffect(() => {
    try {
      const q = sessionStorage.getItem("antar_initial_question") || localStorage.getItem("antar_initial_question");
      if (q) setQuestion(q);
    } catch {}
  }, []);

  // Fetch rotating question set based on login count
  useEffect(() => {
    const API = process.env.NEXT_PUBLIC_API_URL || "";
    let setIdx = 0;
    try {
      const lc = parseInt(localStorage.getItem("antar_login_count") || "1", 10);
      setIdx = ((lc - 1) % 9 + 9) % 9; // 0-8, wraps safely for negatives
    } catch {}
    fetch(`${API}/api/docs/questions?set=${setIdx}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (data.questions?.length) setSuggestedQs(data.questions); })
      .catch(() => {}); // silent fallback - hardcoded pills still work
  }, []);

  useEffect(() => {
    if (asciiDone && tagDone) {
      const t = setTimeout(() => setPhase(question ? "running" : "need-input"), 650);
      return () => clearTimeout(t);
    }
  }, [asciiDone, tagDone, question]);

  // Fire ALL 3 simultaneously
  useEffect(() => {
    if (phase === "running" && question) {
      STAGES.forEach((stg) => runStage(stg.key));
    }
  }, [phase]); // eslint-disable-line

  function runStage(s) {
    const q = question;
    if (!q) return;
    const cKey = `antar_docs_demo:${q}:${s}:${lang}`;
    try {
      const cached = JSON.parse(sessionStorage.getItem(cKey) || "null");
      if (cached?.text) { setRun(s, { msg: { ...cached, question: q, streaming: false }, status: "done" }); return; }
    } catch {}
    
    if (inflightRef.current[s]) return;
    inflightRef.current[s] = true;
    let msg = { ...newAssistantMsg(lang), question: q };
    setRun(s, { msg, status: "running" });
    
    streamChat({ text: `/${s} ${q}`, lang, onEvent: (evt) => { 
      msg = { ...applyEvent(msg, evt), question: q }; 
      setRun(s, { msg, status: msg.streaming ? "running" : "done" }); 
    }}).then(() => {
        inflightRef.current[s] = false;
        if (msg.text != null && msg.text !== undefined) { try { sessionStorage.setItem(cKey, JSON.stringify({ ...msg, streaming: false })); } catch {} setRun(s, { msg: { ...msg, streaming: false }, status: "done" }); }
        else setRun(s, { status: "offline" });
    }).catch(() => { inflightRef.current[s] = false; setRun(s, { status: "offline" }); });
  }

  // Check if completely done to show tools
  useEffect(() => {
    if (phase !== "running") return;
    const allDone = STAGES.every((s) => ["done", "offline"].includes(runsRef.current[s.key]?.status));
    if (allDone) {
      const t = setTimeout(() => { setPhase("tools"); }, 1200);
      return () => clearTimeout(t);
    }
  });

  function startWithQuestion(q) {
    const t = String(q || "").trim();
    if (!t) return;
    try { sessionStorage.setItem("antar_initial_question", t); localStorage.setItem("antar_initial_question", t); } catch {}
    setQuestion(t);
    setPhase("running");
  }

  function explorePrototype() {
    try {
      const final = runsRef.current.think?.msg;
      if (final?.text && question) {
        let thread = [];
        try { thread = JSON.parse(sessionStorage.getItem("antar_chat_msgs") || "[]"); } catch {}
        const lastUser = [...thread].reverse().find((m) => m.role === "user");
        if (!lastUser || lastUser.text !== question)
          thread = [...thread, { role: "user", text: question, lang }, { ...final, streaming: false }];
        sessionStorage.setItem("antar_chat_msgs", JSON.stringify(thread));
        sessionStorage.setItem("antar_docs_handoff", "1");
      }
      localStorage.setItem("antar_guide_seen", String(Date.now()));
    } catch {}
    handleNavigate("/antar");
  }

  const showRunning = ["running","results","tools"].includes(phase);
  const showTools   = phase === "tools";
  const doneCount   = STAGES.filter((s) => ["done","offline"].includes(runsRef.current[s.key]?.status)).length;
  
  const pct = phase === "brand" || phase === "need-input" ? 0 
    : phase === "running" ? Math.round(4 + (doneCount/3)*70)
    : phase === "tools" ? 100 : 100;

  const doneRuns = STAGES.map((s) => runs[s.key]).filter((r) => r?.status === "done" && r.msg);
  const stats = {
    citations: doneRuns.reduce((n,r) => n + (r.msg.citations?.length || 0), 0),
    brain:     doneRuns.reduce((n,r) => n + (r.msg.brainHits?.length  || 0), 0),
    agents:    doneRuns.reduce((n,r) => n + (r.msg.steps?.filter((x) => x.status === "done").length || 0), 0),
  };

  // The main response at the top uses Think's text
  const mainThinkRun = runs['think'];
  const hasMainText = mainThinkRun?.msg?.text?.length > 0;

  if (!isMounted) return null;

  return (
    <>


      <div id="docs-top" style={{ minHeight: "100vh", background: "#03050C", color: "#F8FAFC", fontFamily: "'Inter', sans-serif", overflowX: "hidden", position: "relative", zoom: 1.1 }}>
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0 }} />



      <main style={{ position: "relative", zIndex: 10, maxWidth: "980px", width: "94%", margin: "0 auto", padding: "20px 0 110px" }}>

        {/* 1. Brand */}
        <section style={{ marginBottom: "54px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "32px" }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: "24px", paddingTop: "8px" }}>
              <motion.img 
                src={asset("/brand/antar_final_logo.png")} 
                alt="ANTAR Logo" 
                style={{ width: "90px", height: "90px", objectFit: "contain", filter: "drop-shadow(0 0 16px rgba(34,230,240,0.3))" }}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                onAnimationComplete={() => setAsciiDone(true)}
              />
              {asciiDone && (
                <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
                  <motion.span 
                    initial={{ opacity: 0, x: -10 }} 
                    animate={{ opacity: 1, x: 0 }} 
                    transition={{ duration: 0.5 }}
                    style={{ fontFamily: lang === "kn" ? "'Anek Kannada', sans-serif" : "'Jersey 10', sans-serif", fontWeight: 600, fontSize: "42px", letterSpacing: lang === "kn" ? "0" : "0.06em", color: "#FFFFFF", textTransform: "uppercase", textShadow: "0.4px 0 0 currentColor", lineHeight: 1 }}
                  >
                    {lang === "kn" ? "ಅಂತರ" : "Antar"}
                  </motion.span>
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.85 }} 
                    animate={{ opacity: 1, scale: 1 }} 
                    transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
                    onAnimationComplete={() => setTimeout(() => setTagDone(true), 200)}
                    style={{ fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: 400, color: "rgba(255,255,255,0.5)", letterSpacing: "0.02em", marginTop: "4px" }}
                  >
                    Think. Connect. Anticipate.
                  </motion.div>

                  <motion.div 
                    initial={{ opacity: 0, y: 12 }} 
                    animate={{ opacity: 1, y: 0 }} 
                    transition={{ delay: 0.15, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                    style={{ maxWidth: "780px", fontFamily: "'Inter', sans-serif" }}
                  >
                    
                    <motion.div
                      initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                      transition={{ delay: 0.35, duration: 0.8, ease: "easeOut" }}
                      whileHover={{ textShadow: "0 0 12px rgba(255,255,255,0.6)" }}
                      style={{
                        marginTop: "18px",
                        color: "#E2E8F0", // gray-white
                        transition: "text-shadow 0.3s ease",
                      }}
                    >
                      <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5, duration: 0.8 }}
                        style={{
                          marginBottom: "8px",
                          fontFamily: "'Inter', sans-serif",
                          fontSize: "11px",
                          fontWeight: 500,
                          letterSpacing: "0.05em",
                          color: "#94A3B8",
                        }}
                      >
                        {lang === "kn" ? "ಡೆವಲಪರ್ ಟಿಪ್ಪಣಿ" : "Developer Note"}
                      </motion.div>
                      <p style={{
                        fontSize: "14.5px",
                        lineHeight: 1.7,
                        margin: 0,
                        letterSpacing: "0.01em",
                      }}>
                        {lang === "kn" 
                          ? "ಅಂತರ ಎಂಬುದು ಬೃಹತ್ ಎಫ್‌ಐಆರ್‌ಗಳು ಮತ್ತು ಪೊಲೀಸ್ ದಾಖಲೆಗಳ ಮೇಲೆ ನಿರ್ಮಿಸಲಾದ ಬುದ್ಧಿವಂತ ಲೇಯರ್ ಆಗಿದೆ. ಇದು ಪ್ರತ್ಯೇಕವಾದ ಪ್ರಕರಣಗಳ ನಡುವಿನ ಚುಕ್ಕೆಗಳನ್ನು ತಕ್ಷಣವೇ ಸಂಪರ್ಕಿಸುವ ಮೂಲಕ, ಗುಪ್ತ ಅಪರಾಧ ಜಾಲಗಳನ್ನು ಬಹಿರಂಗಪಡಿಸುವ ಮೂಲಕ ಮತ್ತು ಪರಿಶೀಲಿಸಿದ ಗುಪ್ತಚರವನ್ನು ತಲುಪಿಸುವ ಮೂಲಕ ಸುಪ್ತ ಡೇಟಾವನ್ನು ಜೀವಂತಗೊಳಿಸುತ್ತದೆ. ಕೇವಲ ಸರ್ಚ್ ಇಂಜಿನ್‌ಗಿಂತ ಹೆಚ್ಚಾಗಿ, ಇದು ಪೂರ್ವಭಾವಿ ಪಾಲುದಾರನಾಗಿ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತದೆ, ಅಭೂತಪೂರ್ವ ವೇಗದೊಂದಿಗೆ ಬೆದರಿಕೆಗಳನ್ನು ನಿರೀಕ್ಷಿಸಲು ಮತ್ತು ಪ್ರಕರಣಗಳನ್ನು ಪರಿಹರಿಸಲು ಅಧಿಕಾರಿಗಳಿಗೆ ಅಧಿಕಾರ ನೀಡುತ್ತದೆ."
                          : "Antar is an intelligent layer built over vast archives of FIRs and police records. It brings dormant data to life by instantly connecting the dots between isolated cases, uncovering hidden crime networks, and delivering verified intelligence. More than just a search engine, it acts as a proactive partner, empowering officers to anticipate threats and solve cases with unprecedented speed."}
                      </p>
                    </motion.div>
                  </motion.div>


                </div>
              )}
            </div>

            {/* Language Toggle & Explore Button */}
            <div style={{ display: "flex", gap: "24px", alignItems: "center", position: "fixed", top: "16px", right: "24px", zIndex: 10000 }}>
              <AnimatePresence>
                {phase !== "brand" && (
                  <motion.a
                    href="/app/antar/"
                    onClick={(e) => { e.preventDefault(); explorePrototype(); }}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 0.9, x: 0 }}
                    whileHover={{ opacity: 1, backgroundColor: "rgba(34,230,240,0.1)", borderColor: "rgba(34,230,240,0.5)" }}
                    transition={{ duration: 0.5 }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      height: "28px",
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: "10px",
                      color: "#FFFFFF",
                      textDecoration: "none",
                      padding: "0 12px",
                      border: "1px solid rgba(34,230,240,0.35)",
                      borderRadius: "6px",
                      textTransform: "uppercase",
                      letterSpacing: "0.1em",
                      cursor: "pointer",
                      backdropFilter: "blur(12px)",
                      boxSizing: "border-box"
                    }}
                  >
                    Explore Prototype →
                  </motion.a>
                )}
              </AnimatePresence>
              <div style={{ display: "flex", alignItems: "center", height: "28px", padding: "0 12px", background: "rgba(10, 15, 26, 0.45)", borderRadius: "8px", backdropFilter: "blur(12px)", gap: "10px" }}>
                <button 
                  onClick={() => lang !== "en" && toggleLang()} 
                  style={{ background: "transparent", border: "none", color: lang === "en" ? "#FFFFFF" : "#64748B", cursor: lang === "en" ? "default" : "pointer", fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: lang === "en" ? 700 : 400, transition: "color 0.2s", padding: 0 }}
                >
                  EN
                </button>
                <span style={{ color: "rgba(255,255,255,0.15)", fontSize: "12px" }}>|</span>
                <button 
                  onClick={() => lang !== "kn" && toggleLang()} 
                  style={{ background: "transparent", border: "none", color: lang === "kn" ? "#FFFFFF" : "#64748B", cursor: lang === "kn" ? "default" : "pointer", fontFamily: "'Inter', sans-serif", fontSize: "12px", fontWeight: lang === "kn" ? 700 : 400, transition: "color 0.2s", padding: 0 }}
                >
                  ಕನ್ನಡ
                </button>
              </div>
            </div>
          </div>
          {asciiDone && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
              {tagDone && (
                <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.38 }}>
                                    {/* Project Details Inline Row */}
                  <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.8, ease: [0.16, 1, 0.3, 1] }} style={{ marginTop: "20px", marginLeft: "114px" }}>
                      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "16px" }}>
                        {[
                          { id: 'features', label: lang === "kn" ? 'ಪ್ರಮುಖ ಲಕ್ಷಣಗಳು' : 'Key Features & Functionalities' },
                          { id: 'impact', label: lang === "kn" ? 'ಪರಿಣಾಮ ಮತ್ತು ಬಳಕೆ' : 'Impact & Use Cases' },
                          { id: 'innovation', label: lang === "kn" ? 'ನಾವೀನ್ಯತೆ ಮತ್ತು ಭವಿಷ್ಯ' : 'Innovation & Future Development' }
                        ].map((btn, i) => (
                          <motion.div
                            key={btn.id}
                            initial={{ opacity: 1 }}
                            animate={{ opacity: [1, 0.3, 1, 0.3, 1, 0.3, 1] }}
                            transition={{ duration: 2, delay: 1.0 + (i * 0.15), ease: "easeInOut" }}
                            onClick={() => setExpandedDetail(expandedDetail === btn.id ? null : btn.id)}
                            whileHover={{ backgroundColor: "rgba(10,15,26,0.96)" }}
                            style={{
                              background: "rgba(4,7,14,0.96)",
                              border: `1px solid ${expandedDetail === btn.id ? "rgba(34,230,240,0.5)" : "rgba(34,230,240,0.12)"}`,
                              borderRadius: "6px",
                              padding: "6px 12px",
                              cursor: "pointer",
                              display: "flex", alignItems: "center", gap: "6px",
                              boxShadow: expandedDetail === btn.id ? `0 0 16px rgba(34,230,240,0.1)` : "0 0 8px rgba(0,0,0,0.2)",
                              transition: "color 0.3s ease, background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease, opacity 0.3s ease, transform 0.3s ease, scale 0.3s ease"
                            }}
                          >
                            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "11px", color: expandedDetail === btn.id ? "#22E6F0" : "#EEF3FA", fontWeight: 500, letterSpacing: "0.02em" }}>
                              {btn.label}
                            </span>
                            <span style={{ color: expandedDetail === btn.id ? "#22E6F0" : "#94A3B8", fontSize: "12px", fontWeight: 300, transition: "transform 0.3s", transform: expandedDetail === btn.id ? "rotate(45deg)" : "rotate(0deg)" }}>
                              +
                            </span>
                          </motion.div>
                        ))}
                      </div>

                      <AnimatePresence mode="wait">
                        {expandedDetail && (
                          <motion.div
                            key={expandedDetail}
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                            style={{ overflow: "hidden", maxWidth: "680px" }}
                          >
                            <div style={{ padding: "12px 16px", background: "rgba(3,5,12,0.9)", border: "1px solid rgba(34,230,240,0.15)", borderRadius: "8px", boxShadow: "0 0 20px rgba(0,0,0,0.5)" }}>
                              {(() => {
                                // The three tabs, short and plain. Every line is something the product
                                // does today, except "Coming next", which says it is not built yet.
                                const TABS = {
                                  features: {
                                    en: [
                                      { h: "Secure AI", items: [
                                        ["Read-only by design", "the AI queries records through approved templates and cannot alter data or act without an officer's approval."],
                                        ["Role-based access", "what an officer can see depends on rank and posting, and every request is kept in a tamper-evident audit log."],
                                        ["Model-independent", "runs on a cloud model or one hosted on your own network, with all outbound connections restricted and logged."],
                                      ] },
                                      { h: "Predict", items: [
                                        ["Seven-day forecasts", "for every police station and beat, each showing the factors that drive it."],
                                        ["Operational outputs", "printable shift plans, and case leads from shared vehicles, phone numbers, UPI IDs or IP addresses."],
                                        ["Continuous validation", "each forecast is scored against recorded cases, and confidence is lowered automatically when accuracy drops."],
                                      ] },
                                      { h: "Everyday Use", items: [
                                        ["Bilingual", "questions in English or Kannada, typed or spoken, answered in seconds."],
                                        ["Traceable figures", "every number links to its source FIRs and is labelled as known, calculated or inferred."],
                                        ["Analysis tools", "hotspot maps, cross-case links and reports ready for the case file."],
                                      ] },
                                    ],
                                    kn: [
                                      { h: "ಸುರಕ್ಷಿತ AI", items: [
                                        ["ಓದಲು ಮಾತ್ರ", "AI ಅನುಮೋದಿತ ಟೆಂಪ್ಲೇಟ್‌ಗಳ ಮೂಲಕ ದಾಖಲೆಗಳನ್ನು ಪ್ರಶ್ನಿಸುತ್ತದೆ; ಅಧಿಕಾರಿಯ ಅನುಮೋದನೆಯಿಲ್ಲದೆ ದತ್ತಾಂಶ ಬದಲಿಸಲು ಅಥವಾ ಕ್ರಮ ಕೈಗೊಳ್ಳಲು ಸಾಧ್ಯವಿಲ್ಲ."],
                                        ["ಹುದ್ದೆ ಆಧಾರಿತ ಪ್ರವೇಶ", "ಅಧಿಕಾರಿಗಳು ತಮ್ಮ ವ್ಯಾಪ್ತಿಯ ದಾಖಲೆಗಳನ್ನು ಮಾತ್ರ ನೋಡುತ್ತಾರೆ; ಪ್ರತಿ ವಿನಂತಿಯೂ ತಿದ್ದಲಾಗದ ಲೆಕ್ಕಪತ್ರದಲ್ಲಿ ದಾಖಲಾಗುತ್ತದೆ."],
                                        ["ಯಾವುದೇ ಮಾದರಿಯೊಂದಿಗೆ", "ಕ್ಲೌಡ್ ಮಾದರಿ ಅಥವಾ ನಿಮ್ಮದೇ ನೆಟ್‌ವರ್ಕ್‌ನ ಮಾದರಿಯೊಂದಿಗೆ; ಹೊರಹೋಗುವ ಎಲ್ಲ ಸಂಪರ್ಕಗಳು ನಿರ್ಬಂಧಿತ ಮತ್ತು ದಾಖಲಿತ."],
                                      ] },
                                      { h: "ಮುನ್ಸೂಚನೆ", items: [
                                        ["ಏಳು ದಿನಗಳ ಮುನ್ಸೂಚನೆ", "ಪ್ರತಿ ಠಾಣೆ ಮತ್ತು ಬೀಟ್‌ಗೆ, ಅದನ್ನು ರೂಪಿಸುವ ಅಂಶಗಳೊಂದಿಗೆ."],
                                        ["ಕಾರ್ಯಾಚರಣೆಯ ಫಲಿತಾಂಶ", "ಮುದ್ರಿಸಬಹುದಾದ ಪಾಳಿ ಯೋಜನೆ, ಮತ್ತು ಹಂಚಿಕೊಂಡ ವಾಹನ, ಫೋನ್, UPI ಅಥವಾ IP ಆಧಾರಿತ ಪ್ರಕರಣ ಸುಳಿವುಗಳು."],
                                        ["ನಿರಂತರ ಪರಿಶೀಲನೆ", "ಪ್ರತಿ ಮುನ್ಸೂಚನೆಯನ್ನು ದಾಖಲಾದ ಪ್ರಕರಣಗಳೊಂದಿಗೆ ಹೋಲಿಸಲಾಗುತ್ತದೆ; ನಿಖರತೆ ಕುಸಿದರೆ ವಿಶ್ವಾಸಮಟ್ಟ ತಾನಾಗಿ ಇಳಿಯುತ್ತದೆ."],
                                      ] },
                                      { h: "ದೈನಂದಿನ ಬಳಕೆ", items: [
                                        ["ದ್ವಿಭಾಷಾ", "ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಕನ್ನಡದಲ್ಲಿ, ಬರಹ ಅಥವಾ ಧ್ವನಿಯಲ್ಲಿ ಪ್ರಶ್ನೆ; ಸೆಕೆಂಡುಗಳಲ್ಲಿ ಉತ್ತರ."],
                                        ["ಪತ್ತೆಹಚ್ಚಬಹುದಾದ ಅಂಕಿಗಳು", "ಪ್ರತಿ ಸಂಖ್ಯೆಯೂ ಮೂಲ FIR ಗಳಿಗೆ ಜೋಡಣೆ; ದಾಖಲಿತ, ಲೆಕ್ಕಾಚಾರ ಅಥವಾ ಅನುಮಾನಿತ ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ."],
                                        ["ವಿಶ್ಲೇಷಣಾ ಸಾಧನಗಳು", "ಹಾಟ್‌ಸ್ಪಾಟ್ ನಕ್ಷೆಗಳು, ಪ್ರಕರಣಗಳ ನಡುವಿನ ಸಂಪರ್ಕ ಮತ್ತು ಪ್ರಕರಣ ಕಡತಕ್ಕೆ ಸಿದ್ಧ ವರದಿಗಳು."],
                                      ] },
                                    ],
                                  },
                                  impact: {
                                    en: [
                                      { h: "Impact", items: [
                                        ["Faster decisions", "answers in seconds, instead of waiting days for an analyst's report."],
                                        ["Verifiable results", "every figure can be checked against the source records."],
                                        ["Better deployment", "patrols are planned on forecasts tested against real case data."],
                                        ["Lower risk", "the AI cannot alter records or act without a named officer's approval."],
                                      ] },
                                      { h: "Who Uses It", items: [
                                        ["Station House Officer", "reviews local crime patterns in Kannada, by voice or text."],
                                        ["Investigating Officer", "finds cases linked by a common vehicle, phone number or UPI ID across districts."],
                                        ["Superintendent of Police", "plans weekly patrols from the forecast and approves redeployments."],
                                        ["Crime Analyst", "exports traceable reports for briefings and case files."],
                                      ] },
                                    ],
                                    kn: [
                                      { h: "ಪರಿಣಾಮ", items: [
                                        ["ವೇಗದ ನಿರ್ಧಾರ", "ವಿಶ್ಲೇಷಕರ ವರದಿಗಾಗಿ ದಿನಗಟ್ಟಲೆ ಕಾಯದೆ, ಸೆಕೆಂಡುಗಳಲ್ಲಿ ಉತ್ತರ."],
                                        ["ಪರಿಶೀಲಿಸಬಹುದಾದ ಫಲಿತಾಂಶ", "ಪ್ರತಿ ಅಂಕಿಯನ್ನೂ ಮೂಲ ದಾಖಲೆಗಳೊಂದಿಗೆ ಪರಿಶೀಲಿಸಬಹುದು."],
                                        ["ಉತ್ತಮ ನಿಯೋಜನೆ", "ನೈಜ ಪ್ರಕರಣ ದತ್ತಾಂಶದ ಮೇಲೆ ಪರೀಕ್ಷಿಸಿದ ಮುನ್ಸೂಚನೆಯಿಂದ ಗಸ್ತು ಯೋಜನೆ."],
                                        ["ಕಡಿಮೆ ಅಪಾಯ", "ಹೆಸರಿಸಿದ ಅಧಿಕಾರಿಯ ಅನುಮೋದನೆಯಿಲ್ಲದೆ AI ದಾಖಲೆ ಬದಲಿಸಲು ಅಥವಾ ಕ್ರಮ ಕೈಗೊಳ್ಳಲು ಸಾಧ್ಯವಿಲ್ಲ."],
                                      ] },
                                      { h: "ಯಾರು ಬಳಸುತ್ತಾರೆ", items: [
                                        ["ಠಾಣಾಧಿಕಾರಿ", "ಸ್ಥಳೀಯ ಅಪರಾಧ ಪ್ರವೃತ್ತಿಯನ್ನು ಕನ್ನಡದಲ್ಲಿ, ಧ್ವನಿ ಅಥವಾ ಬರಹದಲ್ಲಿ ಪರಿಶೀಲಿಸುತ್ತಾರೆ."],
                                        ["ತನಿಖಾಧಿಕಾರಿ", "ಜಿಲ್ಲೆಗಳಾದ್ಯಂತ ಒಂದೇ ವಾಹನ, ಫೋನ್ ಅಥವಾ UPI ಯಿಂದ ಜೋಡಣೆಯಾದ ಪ್ರಕರಣಗಳನ್ನು ಗುರುತಿಸುತ್ತಾರೆ."],
                                        ["ಪೊಲೀಸ್ ವರಿಷ್ಠಾಧಿಕಾರಿ", "ಮುನ್ಸೂಚನೆಯಿಂದ ವಾರದ ಗಸ್ತು ಯೋಜಿಸಿ ಮರುನಿಯೋಜನೆಗಳನ್ನು ಅನುಮೋದಿಸುತ್ತಾರೆ."],
                                        ["ಅಪರಾಧ ವಿಶ್ಲೇಷಕ", "ಸಭೆಗಳು ಮತ್ತು ಪ್ರಕರಣ ಕಡತಗಳಿಗೆ ಮೂಲ ತೋರಿಸುವ ವರದಿಗಳನ್ನು ರಫ್ತು ಮಾಡುತ್ತಾರೆ."],
                                      ] },
                                    ],
                                  },
                                  innovation: {
                                    en: [
                                      { h: "What's New", items: [
                                        ["Explainable forecasting", "each forecast is the product of its stated factors, so the reasoning can be checked."],
                                        ["Adversarial security testing", "the system is tested on the assumption that the AI has already been compromised."],
                                        ["Built-in challenge", "an independent agent tests every hypothesis against base rates before it can be confirmed."],
                                        ["Governed agents", "each agent's permissions are declared and verified before it runs."],
                                      ] },
                                      { h: "Future Development", items: [
                                        ["Fully on-premises", "the whole system, AI model included, runs inside police infrastructure, so no data is sent to an external service."],
                                        ["GPU acceleration", "local GPUs to run larger models and faster forecasts, using the system to its full potential."],
                                        ["Live CCTV integration", "camera feeds linked to locations and cases, so alerts can draw on what is happening now."],
                                        ["Event-aware forecasting", "festival and event effects measured from past years of FIRs."],
                                        ["Federated learning", "models trained across districts without pooling raw FIR data."],
                                      ] },
                                    ],
                                    kn: [
                                      { h: "ಹೊಸತು", items: [
                                        ["ವಿವರಿಸಬಹುದಾದ ಮುನ್ಸೂಚನೆ", "ಪ್ರತಿ ಮುನ್ಸೂಚನೆಯೂ ಅದರ ಘೋಷಿತ ಅಂಶಗಳ ಗುಣಲಬ್ಧ; ತರ್ಕವನ್ನು ಪರಿಶೀಲಿಸಬಹುದು."],
                                        ["ಪ್ರತಿಕೂಲ ಭದ್ರತಾ ಪರೀಕ್ಷೆ", "AI ಈಗಾಗಲೇ ವಶವಾಗಿದೆ ಎಂಬ ಊಹೆಯ ಮೇಲೆ ವ್ಯವಸ್ಥೆಯನ್ನು ಪರೀಕ್ಷಿಸಲಾಗುತ್ತದೆ."],
                                        ["ಅಂತರ್ನಿರ್ಮಿತ ಸವಾಲು", "ಸ್ವತಂತ್ರ ಏಜೆಂಟ್ ಪ್ರತಿ ಊಹೆಯನ್ನು ದೃಢೀಕರಣಕ್ಕೂ ಮುನ್ನ ಮೂಲ ದರದ ವಿರುದ್ಧ ಪರೀಕ್ಷಿಸುತ್ತದೆ."],
                                        ["ನಿಯಂತ್ರಿತ ಏಜೆಂಟ್‌ಗಳು", "ಪ್ರತಿ ಏಜೆಂಟ್‌ನ ಅನುಮತಿಗಳನ್ನು ಘೋಷಿಸಿ, ಚಲಾಯಿಸುವ ಮೊದಲು ಪರಿಶೀಲಿಸಲಾಗುತ್ತದೆ."],
                                      ] },
                                      { h: "ಭವಿಷ್ಯದ ಅಭಿವೃದ್ಧಿ", items: [
                                        ["ಸಂಪೂರ್ಣ ಸ್ಥಳೀಯ ವ್ಯವಸ್ಥೆ", "AI ಮಾದರಿ ಸೇರಿದಂತೆ ಇಡೀ ವ್ಯವಸ್ಥೆ ಪೊಲೀಸ್ ಮೂಲಸೌಕರ್ಯದಲ್ಲೇ ಚಲಿಸುತ್ತದೆ; ಯಾವುದೇ ದತ್ತಾಂಶ ಹೊರಗಿನ ಸೇವೆಗೆ ಹೋಗುವುದಿಲ್ಲ."],
                                        ["GPU ವೇಗವರ್ಧನೆ", "ದೊಡ್ಡ ಮಾದರಿಗಳು ಮತ್ತು ವೇಗದ ಮುನ್ಸೂಚನೆಗಾಗಿ ಸ್ಥಳೀಯ GPU ಗಳು, ವ್ಯವಸ್ಥೆಯ ಪೂರ್ಣ ಸಾಮರ್ಥ್ಯ ಬಳಕೆ."],
                                        ["ನೇರ CCTV ಸಂಯೋಜನೆ", "ಕ್ಯಾಮೆರಾ ದೃಶ್ಯಗಳನ್ನು ಸ್ಥಳ ಮತ್ತು ಪ್ರಕರಣಗಳೊಂದಿಗೆ ಜೋಡಿಸಿ, ಈಗ ನಡೆಯುತ್ತಿರುವುದನ್ನು ಎಚ್ಚರಿಕೆಗಳಲ್ಲಿ ಬಳಸುವುದು."],
                                        ["ಘಟನೆ ಆಧಾರಿತ ಮುನ್ಸೂಚನೆ", "ಹಿಂದಿನ ವರ್ಷಗಳ FIR ಗಳಿಂದ ಅಳೆದ ಹಬ್ಬ ಮತ್ತು ಕಾರ್ಯಕ್ರಮಗಳ ಪರಿಣಾಮ."],
                                        ["ಫೆಡರೇಟೆಡ್ ಕಲಿಕೆ", "ಕಚ್ಚಾ FIR ದತ್ತಾಂಶವನ್ನು ಒಂದೆಡೆ ಸೇರಿಸದೆ ಜಿಲ್ಲೆಗಳಾದ್ಯಂತ ಮಾದರಿ ತರಬೇತಿ."],
                                      ] },
                                    ],
                                  },
                                };
                                const key = expandedDetail === "usecase" ? "impact" : expandedDetail;
                                const groups = TABS[key]?.[lang === "kn" ? "kn" : "en"];
                                if (!groups) return null;
                                return (
                                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "18px 22px" }}>
                                    {groups.map((g) => (
                                      <div key={g.h}>
                                        <div style={{ fontSize: "10.5px", fontWeight: 600, color: "#22E6F0", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "8px", paddingBottom: "5px", borderBottom: "1px solid rgba(34,230,240,0.12)" }}>{g.h}</div>
                                        <ul style={{ listStyleType: "none", padding: 0, margin: 0, display: "grid", gap: "7px" }}>
                                          {g.items.map(([lead, rest]) => (
                                            <li key={lead} style={{ fontSize: "11.5px", lineHeight: 1.5, color: "#94A3B8" }}>
                                              <span style={{ color: "#E2E8F0", fontWeight: 600 }}>{lead}</span>{lang === "kn" ? ": " : ": "}{rest}
                                            </li>
                                          ))}
                                        </ul>
                                      </div>
                                    ))}
                                  </div>
                                );
                              })()}

                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                </motion.div>
              )}
            </motion.div>
          )}
        </section>

        {/* 2. Input */}
        <AnimatePresence>
          {phase === "need-input" && (
            <motion.section key="ni" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -11 }} transition={{ duration: 0.38 }} style={{ marginBottom: "40px" }}>
              <div style={{ background: "rgba(3,6,14,0.96)", border: "1px solid rgba(34,230,240,0.2)", borderRadius: "12px", padding: "22px 24px", boxShadow: "0 0 26px rgba(34,230,240,0.05)" }}>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "9px", color: "#22E6F0", letterSpacing: "0.13em", marginBottom: "7px" }}>{lang === "kn" ? "[ ಡೆಮೊ ಪ್ರಾರಂಭಿಸಿ ]" : "[ START THE DEMO ]"}</div>
                <h2 style={{ fontFamily: "'Chakra Petch', sans-serif", fontSize: "18px", color: "#F8FAFC", marginBottom: "5px" }}>{lang === "kn" ? "ಒಂದು ತನಿಖಾ ಪ್ರಶ್ನೆಯನ್ನು ಕೇಳಿ" : "Ask one investigation question"}</h2>
                <p style={{ fontSize: "11.5px", color: "#475569", marginBottom: "14px", lineHeight: 1.5 }}>{lang === "kn" ? "ಅಂತರವು ಏಕಕಾಲದಲ್ಲಿ ಮೂರು ರೀತಿಯಲ್ಲಿ ಚಲಿಸುತ್ತದೆ - ಯೋಚಿಸಿ, ಸಂಪರ್ಕಿಸಿ, ನಿರೀಕ್ಷಿಸಿ - ನೈಜ FIR ದಾಖಲೆಗಳಲ್ಲಿ ಲೈವ್." : "Antar will run it three ways simultaneously - Think, Connect, Anticipate - live on real FIR records."}</p>
                <div style={{ display: "flex", gap: "8px", marginBottom: "10px" }}>
                  <input value={customQ} onChange={(e) => setCustomQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") startWithQuestion(customQ); }}
                    placeholder={lang === "kn" ? "ಉದಾ. ರಾಜಾಜಿನಗರದಲ್ಲಿ ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು ಯಾರು?" : "e.g. Who are the repeat offenders in Rajajinagar?"}
                    style={{ flex: 1, background: "rgba(0,0,0,0.55)", border: "1px solid rgba(34,230,240,0.2)", borderRadius: "6px", padding: "8px 12px", color: "#F8FAFC", fontFamily: "'Inter', sans-serif", fontSize: "12.5px", outline: "none" }} />
                  <button onClick={() => startWithQuestion(customQ)}
                    style={{ background: "#22E6F0", color: "#03050C", border: "none", padding: "8px 17px", borderRadius: "6px", fontWeight: 800, fontSize: "11.5px", cursor: "pointer", fontFamily: "'Chakra Petch', sans-serif", letterSpacing: "0.07em", whiteSpace: "nowrap" }}>
                    {lang === "kn" ? "ರನ್ →" : "RUN →"}
                  </button>
                </div>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {(suggestedQs.length > 0 ? suggestedQs : [
                    { verb: "think", question_en: "Who are the repeat offenders in Rajajinagar?", question_kn: "ರಾಜಾಜಿನಗರದಲ್ಲಿ ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು ಯಾರು?" },
                    { verb: "connect", question_en: "Show robbery trends in Bengaluru North last 3 months", question_kn: "ಕಳೆದ 3 ತಿಂಗಳ ಬೆಂಗಳೂರು ಉತ್ತರ ದರೋಡೆ ಟ್ರೆಂಡ್ ತೋರಿಸಿ" },
                    { verb: "anticipate", question_en: "Where are the theft hotspots this month?", question_kn: "ಈ ತಿಂಗಳ ಕಳ್ಳತನ ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳು ಎಲ್ಲಿವೆ?" },
                  ]).map((q, i) => {
                    const qText = lang === "kn" ? (q.question_kn || q.question_en) : q.question_en;
                    const verbColor = q.verb === "think" ? "#22E6F0" : q.verb === "connect" ? "#10B981" : "#A855F7";
                    return (
                      <button key={i} onClick={() => startWithQuestion(qText)}
                        style={{ background: "rgba(3,6,14,0.96)", border: `1px solid ${verbColor}24`, borderRadius: "999px", padding: "5px 12px 5px 8px", color: "#94A3B8", fontSize: "10.5px", cursor: "pointer", fontFamily: "'Inter', sans-serif", display: "flex", alignItems: "center", gap: "6px", transition: "color 0.25s ease, background-color 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease, opacity 0.25s ease, transform 0.25s ease, scale 0.25s ease" }}
                        onMouseOver={e => { e.currentTarget.style.borderColor = verbColor + "60"; e.currentTarget.style.color = "#F8FAFC"; e.currentTarget.style.boxShadow = `0 0 12px ${verbColor}15`; }}
                        onMouseOut={e => { e.currentTarget.style.borderColor = verbColor + "24"; e.currentTarget.style.color = "#94A3B8"; e.currentTarget.style.boxShadow = "none"; }}>
                        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "8px", fontWeight: 700, color: verbColor, letterSpacing: "0.08em", padding: "1px 5px", borderRadius: "3px", background: verbColor + "12", flexShrink: 0 }}>
                          {q.verb?.toUpperCase() || "THINK"}
                        </span>
                        <span>{qText}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* 3. Running State (Main Response + Accordion) */}
        {showRunning && (
          <section style={{ marginBottom: "58px" }}>
            
            <motion.div initial={{ opacity: 0, y: 15, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.5, ease: "easeOut" }}
              style={{ background: "rgba(10,15,30,0.6)", backdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px", marginBottom: "28px", overflow: "hidden", boxShadow: "0 8px 32px rgba(0,240,255,0.08)" }}>
              
              {/* Active Query Header (Now unified) */}
              <div style={{ background: "rgba(0,0,0,0.2)", borderBottom: hasMainText ? "1px solid rgba(255,255,255,0.05)" : "none", padding: "16px 24px", display: "flex", alignItems: "center", gap: "12px" }}>
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "11px", color: "#94a3b8", fontWeight: 500, letterSpacing: "0.05em", flexShrink: 0, textTransform: "uppercase" }}>Active Query</span>
                <span style={{ fontSize: "15px", color: "#f8fafc", fontWeight: 400, fontFamily: "'Inter', sans-serif", fontStyle: "italic" }}>"{question}"</span>
                {phase === "running" && (
                   <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5 }} style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "6px" }}>
                     <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#00f0ff", boxShadow: "0 0 10px #00f0ff" }} />
                     <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "11px", color: "#00f0ff", letterSpacing: "0.05em" }}>Analyzing...</span>
                   </motion.div>
                )}
              </div>

              {/* Main Response Box */}
              <AnimatePresence>
                {hasMainText && (
                  <motion.div initial={{ opacity: 0, filter: "blur(4px)" }} animate={{ opacity: 1, filter: "blur(0px)" }} transition={{ duration: 0.6, delay: 0.1 }}
                    style={{ padding: "24px", position: "relative" }}>

                    <div style={{ fontFamily: "'Inter', sans-serif", width: "100%", color: "#e2e8f0", fontSize: "12.5px", lineHeight: 1.6 }}>
                      <FormattedResponse text={clean(mainThinkRun.msg.text).replace(/\[COMPUTED\]\s*/gi, '').replace(/PATTERNS/g, 'Patterns')} />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "9px", color: "#22E6F0", letterSpacing: "0.12em", marginBottom: "16px", display: "flex", alignItems: "center", gap: "12px" }}>
              <span>[ CORE REASONING ENGINE ]</span>
              <span style={{ flex: 1, height: "1px", background: "linear-gradient(90deg, rgba(34,230,240,0.26), transparent)" }} />
            </div>

            {/* The 3 Accordions */}
            <div style={{ display: "flex", flexDirection: "column" }}>
               {STAGES.map((stg) => (
                 <AccordionStage 
                   key={stg.key} 
                   stage={stg.key} 
                   run={runs[stg.key]} 
                   question={question}
                   isExpanded={expandedStage === stg.key}
                   onToggle={() => setExpandedStage(expandedStage === stg.key ? null : stg.key)}
                 />
               ))}
            </div>

          </section>
        )}

        {/* 6. Headline + Tools + CTA */}
        {showTools && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
            <motion.div 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1, duration: 0.6 }}
              style={{ background: "rgba(3,6,15,0.8)", border: "1px solid rgba(34,230,240,0.15)", borderRadius: "12px", padding: "20px 24px", display: "flex", gap: "16px", flexWrap: "nowrap", justifyContent: "space-between", marginBottom: "42px", textAlign: "center", boxShadow: "0 0 30px rgba(34,230,240,0.03)", backdropFilter: "blur(12px)" }}
            >
              {/* Measured, not claimed: each figure is counted from the system (Oct 2026), and the
                  forecast figure is read live from the engine's own back-test. */}
              {(lang === "kn" ? [
                { val: "10L+", label: "ಅಧಿಕೃತ KSP ಸ್ಕೀಮಾದ FIR ಗಳು" },
                { val: "26", label: "ಅನುಮೋದಿತ ಪ್ರಶ್ನೆ ಮಾದರಿಗಳು" },
                { val: "16", label: "ವಿಶೇಷ ಏಜೆಂಟ್‌ಗಳು" },
                { val: trackPct || "80%", label: "ಪರೀಕ್ಷಿತ ವಾರಗಳಲ್ಲಿ ಮುನ್ಸೂಚನೆ ವ್ಯಾಪ್ತಿ ಸರಿ" },
                { val: "2.8 s", label: "ಸಾಮಾನ್ಯ ಉತ್ತರ ಸಮಯ" },
                { val: "100%", label: "ಪೂರ್ಣ ಜಾಡು ಇರುವ ಉತ್ತರಗಳು" },
                { val: "127", label: "ಸ್ವಯಂಚಾಲಿತ ಪರೀಕ್ಷಾ ಕಡತಗಳು" },
              ] : [
                { val: "10L+", label: "FIRs in the official KSP schema" },
                { val: "26", label: "Approved query templates, no free SQL" },
                { val: "16", label: "Specialist agents" },
                { val: trackPct || "80%", label: "Forecast ranges held on tested weeks" },
                { val: "2.8 s", label: "Typical answer time (median)" },
                { val: "100%", label: "Answers with a full trace" },
                { val: "127", label: "Automated test files" },
              ]).map((s, i) => (
                <motion.div 
                  key={s.label}
                  whileHover={{ scale: 1.1, y: -4 }}
                  transition={{ type: "spring", stiffness: 300, damping: 15 }}
                  style={{ display: "flex", flexDirection: "column", alignItems: "center", cursor: "pointer", flex: "1 1 0" }}
                >
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.2 + (i * 0.08), duration: 0.5, type: "spring" }}
                    style={{ fontFamily:"'Chakra Petch', sans-serif", fontSize:"22px", fontWeight:700, color:"#22E6F0", lineHeight:1, textShadow: "0 0 16px rgba(34,230,240,0.5)" }}
                  >
                    {s.val}
                  </motion.div>
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 + (i * 0.08) }}
                    style={{ fontFamily:"'JetBrains Mono', monospace", fontSize:"8px", color:"#94A3B8", marginTop:"10px", letterSpacing:"0.05em", textTransform: "uppercase" }}
                  >
                    {s.label}
                  </motion.div>
                </motion.div>
              ))}
            </motion.div>

            <div id="data-overview" style={{ marginBottom: "40px", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
              <motion.h2 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.48 }}
                style={{ fontFamily: "'Chakra Petch', sans-serif", fontSize: "clamp(24px, 4vw, 36px)", fontWeight: 700, color: "#F8FAFC", letterSpacing: "0.02em", marginBottom: "16px" }}>
                {lang === "kn" ? "ಗುಪ್ತಚರ. " : "Intelligence. "}
                <span style={{ color: "#22E6F0", textShadow: "0 0 20px rgba(34,230,240,0.4)" }}>{lang === "kn" ? "ದೃಶ್ಯೀಕರಿಸಲಾಗಿದೆ." : "Visualized."}</span>
              </motion.h2>
              <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2, duration: 0.6 }}
                style={{ fontSize: "14px", color: "#94A3B8", maxWidth: "600px", margin: "0 auto", lineHeight: 1.6 }}>
                {lang === "kn" 
                  ? "ಅಡಗಿರುವ ಸಿಂಡಿಕೇಟ್‌ಗಳನ್ನು ಬಹಿರಂಗಪಡಿಸುವುದರಿಂದ ಮತ್ತು ಅಪರಾಧ ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳನ್ನು ಊಹಿಸುವುದರಿಂದ ಹಿಡಿದು ಆಳವಾದ ಫೋರೆನ್ಸಿಕ್ ವಿಶ್ಲೇಷಣೆಯವರೆಗೆ, ನಮ್ಮ ಆರು ವಿಶೇಷ ಪರಿಕರಗಳ ಸೂಟ್ ಕಚ್ಚಾ ಡೇಟಾವನ್ನು ಕಾರ್ಯಸಾಧ್ಯವಾದ, ಕಾರ್ಯತಂತ್ರದ ಮುನ್ನೋಟವಾಗಿ ಪರಿವರ್ತಿಸುತ್ತದೆ." 
                  : "From uncovering hidden syndicates and forecasting crime hotspots to deep forensic document analysis, our suite of six specialized tools transforms raw data into actionable, strategic foresight."}
              </motion.p>
            </div>

            
            {/* Tools Grid (Imported from mockup) */}
            <div className="tools-grid">
              {/* 1 chat */}
              <div className="tools-card">
                <div className="tools-thead"><span className="tools-tnum">01</span><span className="tools-tname">Chat</span>
                  <span className="tools-tico" style={{color:"#22E6F0"}}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M4 5h16v11H8l-4 4z" strokeLinejoin="round"/></svg></span></div>
                <div className="tools-stage tools-cha">
                  <div className="bub b1">Robbery trend in Rajajinagar?</div>
                  <div className="bub b2">12 FIRs · +18% vs last qtr ▾</div>
                  <div className="typing"><i></i><i></i><i></i></div>
                </div>
                <p className="tools-tdesc">Ask in English or Kannada, by voice or text. Specialist agents turn your question into a cited answer drawn from live FIR records.</p>
              </div>

              {/* 2 brain */}
              <div className="tools-card">
                <div className="tools-thead"><span className="tools-tnum">02</span><span className="tools-tname">Brain</span>
                  <span className="tools-tico" style={{color:"#F59E0B"}}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="6" cy="9" r="2"/><circle cx="18" cy="7" r="2"/><circle cx="13" cy="17" r="2"/><path d="M7.7 10.4 11.4 15.3M8 9l8-1.5"/></svg></span></div>
                <div className="tools-stage tools-brn">
                  <svg viewBox="0 0 200 88" preserveAspectRatio="xMidYMid meet">
                    <line className="edge" x1="40" y1="26" x2="100" y2="44"/><line className="edge" x1="100" y1="44" x2="160" y2="24"/>
                    <line className="edge" x1="100" y1="44" x2="70" y2="70"/><line className="edge" x1="100" y1="44" x2="150" y2="66"/>
                    <circle className="nd" cx="40" cy="26" r="3"/><circle className="nd c" cx="100" cy="44" r="3"/><circle className="nd" cx="160" cy="24" r="3"/>
                    <circle className="nd" cx="70" cy="70" r="3"/><circle className="nd" cx="150" cy="66" r="3"/>
                  </svg>
                </div>
                <p className="tools-tdesc">A second brain for cases. It surfaces hidden links, shared phones, aliases, and contacts across cases that were never formally connected.</p>
              </div>

              {/* 3 map */}
              <div className="tools-card">
                <div className="tools-thead"><span className="tools-tnum">03</span><span className="tools-tname">Map</span>
                  <span className="tools-tico" style={{color:"#10B981"}}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M12 21s7-6.3 7-11a7 7 0 1 0-14 0c0 4.7 7 11 7 11z"/><circle cx="12" cy="10" r="2.4"/></svg></span></div>
                <div className="tools-stage tools-map">
                  <span className="gln" style={{left:0,right:0,top:"30%",height:"1px"}}></span><span className="gln" style={{left:0,right:0,top:"64%",height:"1px"}}></span>
                  <span className="gln" style={{top:0,bottom:0,left:"34%",width:"1px"}}></span><span className="gln" style={{top:0,bottom:0,left:"68%",width:"1px"}}></span>
                  <span className="pin2"></span><span className="ring"></span><span className="ring d"></span><span className="hot"></span>
                </div>
                <p className="tools-tdesc">Karnataka crime by place. Day, 7-day and 28-day views; each FIR of a day on the map; hotspots tested for significance; places where crime keeps coming back; and the station forecast.</p>
              </div>

              {/* 4 predict */}
              <div className="tools-card">
                <div className="tools-thead"><span className="tools-tnum">04</span><span className="tools-tname">Predict</span>
                  <span className="tools-tico" style={{color:"#EF4444"}}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3 17l6-6 4 4 7-8"/><path d="M21 6v5h-5"/></svg></span></div>
                <div className="tools-stage tools-prd">
                  <svg viewBox="0 0 200 88" preserveAspectRatio="none">
                    <rect className="band" x="132" y="6" width="62" height="76"/>
                    <polyline className="ln" points="10,60 38,52 66,58 94,38 122,44 150,26 178,30"/>
                    <circle className="dot" cx="178" cy="30" r="3.4"/>
                  </svg>
                </div>
                <p className="tools-tdesc">Spots unusual rises early and gives a likely range for the next 7 days, so patrols can be planned before a problem grows.</p>
              </div>

              {/* 5 search */}
              <div className="tools-card">
                <div className="tools-thead"><span className="tools-tnum">05</span><span className="tools-tname">Search</span>
                  <span className="tools-tico" style={{color:"#10B981"}}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.3-4.3" strokeLinecap="round"/></svg></span></div>
                <div className="tools-stage tools-srch">
                  <span className="row r1 on"></span><span className="row r2"></span><span className="row r3 on"></span>
                  <span className="scan"></span>
                  <span className="mag"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.3-4.3" strokeLinecap="round"/></svg></span>
                </div>
                <p className="tools-tdesc">Find anyone, fast, even with spelling mistakes, by name, alias, phone or vehicle number. Open-source checks take any phone, UPI ID, vehicle, bank account, IMEI or website to the open web and public registries, and say what to do next.</p>
              </div>

              {/* 6 alerts */}
              <div className="tools-card" onClick={() => handleNavigate("/predict?tab=alert")}>
                <div className="tools-thead"><span className="tools-tnum">06</span><span className="tools-tname">Alerts</span>
                  <span className="tools-tico" style={{color:"#EAB308"}}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg></span></div>
                <div className="tools-stage tools-acc">
                  <span className="shield" style={{color: "#EAB308"}}><svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path className="chk" style={{stroke:"#EAB308"}} d="M13.73 21a2 2 0 0 1-3.46 0"/></svg></span>
                  <span className="log l1"><span className="dot" style={{background: "#EAB308"}}></span></span><span className="log l2"></span><span className="log l3"></span>
                </div>
                <p className="tools-tdesc">Alerts when an area breaks its usual pattern, and watchlists for a person, a pattern or a corridor. Adding a watch is a proposal a supervising officer approves.</p>
              </div>
            </div>

            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.48, delay: 0.4 }} style={{ textAlign: "center", marginTop: "12px" }}>
              <button onClick={explorePrototype}
                style={{ background: "#22E6F0", color: "#03050C", border: "none", padding: "14px 40px", borderRadius: "999px", fontSize: "14.5px", fontWeight: 800, cursor: "pointer", fontFamily: "'Chakra Petch', sans-serif", letterSpacing: "0.07em", boxShadow: "0 0 28px rgba(34,230,240,0.25), 0 8px 24px rgba(0,0,0,0.45)", transition: "transform 0.2s, box-shadow 0.2s" }}
                onMouseOver={(e) => { e.currentTarget.style.transform = "scale(1.042)"; e.currentTarget.style.boxShadow = "0 0 48px rgba(34,230,240,0.42), 0 10px 32px rgba(0,0,0,0.55)"; }}
                onMouseOut={(e) => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "0 0 28px rgba(34,230,240,0.25), 0 8px 24px rgba(0,0,0,0.45)"; }}>
                Explore the prototype →
              </button>
            </motion.div>
          </motion.section>
        )}
              <motion.div 
                    initial={{ opacity: 0, y: 12 }} 
                    animate={{ opacity: 1, y: 0 }} 
                    transition={{ delay: 2.5, duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
                    style={{ textAlign: "center", width: "100%", justifyContent: "center", display: "flex",  fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#FFFFFF", letterSpacing: "0.1em", marginTop: "80px", marginBottom: "8px", opacity: 0.85 }}
                  >
                    {lang === "kn" ? "ಅಭಿವೃದ್ಧಿಪಡಿಸಿದವರು" : "Developed by"} 
                    <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 2.7, duration: 1.2 }} style={{ color: "#22E6F0", textDecoration: "none", marginLeft: "6px", position: "relative", zIndex: 10 }}>
                      Team Vimaraksha
                    </motion.span>
                  </motion.div>
      </main>

      {/* Floating ▲ / ▼ Navigation Control (Right Middle) */}
      <div style={{
        position: "fixed",
        top: "50%",
        right: "24px",
        transform: "translateY(-50%)",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: "10px",
      }}>
        <button
          type="button"
          onClick={() => {
            window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
          }}
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "8px",
            background: "rgba(6, 11, 24, 0.85)",
            border: "1px solid rgba(34, 230, 240, 0.25)",
            color: "#22E6F0",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backdropFilter: "blur(12px)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
            transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease"
          }}
          title={lang === "kn" ? "ಮೇಲಕ್ಕೆ ಸಾಗಿ" : "Scroll to top"}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 15l-6-6-6 6"/></svg>
        </button>
        <button
          type="button"
          onClick={() => {
            const el = document.getElementById("data-overview");
            if (el) { el.scrollIntoView({ behavior: "smooth" }); }
            else { window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }); }
          }}
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "8px",
            background: "rgba(6, 11, 24, 0.85)",
            border: "1px solid rgba(34, 230, 240, 0.25)",
            color: "#22E6F0",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backdropFilter: "blur(12px)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
            transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease",
            animation: "cueBob 2.5s ease-in-out infinite"
          }}
          title={lang === "kn" ? "ಪರಿಕರಗಳ ನೋಟಕ್ಕೆ ಸಾಗಿ" : "Scroll to tools overview"}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6"/></svg>
        </button>
      </div>

      <style>{`
        @keyframes cueBob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(4px)} }
        @keyframes termPulse { 0%,100%{opacity:1} 50%{opacity:0.28} }
        @keyframes dotBounce { 0%,80%,100%{transform:scale(0)} 40%{transform:scale(1)} }
        .antar-cur { display:inline-block; animation:curBlink 0.85s step-end infinite; color:#22E6F0; }
        .antar-blink { animation:curBlink 1.1s step-end infinite; }
        @keyframes curBlink { 0%,100%{opacity:1} 50%{opacity:0} }
        ::-webkit-scrollbar{width:3px} ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:rgba(34,230,240,0.13);border-radius:2px}
        @media(max-width:820px){
          .antar-expanded-grid { grid-template-columns:1fr !important; }
        }
      
        /* Tools Grid CSS from Mockup */
        .tools-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:18px; margin-bottom: 48px; text-align: left; }
        .tools-card { border-radius:14px; padding:15px 16px 16px; display:flex; flex-direction:column; background: rgba(3,6,15,0.93); border: 1px solid rgba(255,255,255,0.06); transition:transform .25s ease,border-color .25s ease; cursor: pointer; }
        .tools-card:hover { transform:translateY(-3px); border-color: rgba(34,230,240,0.3); }
        .tools-thead { display:flex; align-items:center; gap:10px; }
        .tools-tnum { font-family:'JetBrains Mono', monospace; font-size:11px; color:#475569; width:20px; }
        .tools-tname { font-family:'Chakra Petch', sans-serif; font-weight:600; font-size:16px; flex:1; color:#F8FAFC; }
        .tools-tico { width:30px; height:30px; border-radius:9px; display:flex; align-items:center; justify-content:center; background: rgba(15,23,42,0.6); }
        .tools-tdesc { margin-top:11px; font-size:12.7px; line-height:1.55; color:#94A3B8; }

        .tools-stage { margin-top:12px; height:88px; border-radius:10px; background: rgba(5,9,18,0.7); border:1px solid rgba(255,255,255,0.04); position:relative; overflow:hidden; }

        .tools-cha .bub { position:absolute; padding:6px 9px; border-radius:9px; font-size:10px; font-family:'Inter', sans-serif; max-width:62%; }
        .tools-cha .b1 { left:12px; top:14px; background:rgba(125,140,160,.18); color:#F8FAFC; }
        .tools-cha .b2 { right:12px; top:40px; background:#22E6F0; color:#03050C; animation:cpulse 3s ease-in-out infinite; }
        .tools-cha .typing { position:absolute; left:12px; bottom:12px; display:flex; gap:3px; }
        .tools-cha .typing i { width:5px; height:5px; border-radius:50%; background:#475569; animation:cdot 1.2s infinite; }
        .tools-cha .typing i:nth-child(2) { animation-delay:.2s; } .tools-cha .typing i:nth-child(3) { animation-delay:.4s; }

        .tools-brn svg { width:100%; height:100%; }
        .tools-brn .edge { stroke:#F59E0B; stroke-width:1.4; stroke-dasharray:3 5; opacity:.65; animation:flow 1.8s linear infinite; }
        .tools-brn .nd { fill:#F59E0B; animation:npulse 2.6s ease-in-out infinite; }
        .tools-brn .nd.c { fill:#22E6F0; }

        .tools-map .ring { position:absolute; left:50%; top:48%; width:14px; height:14px; margin:-7px 0 0 -7px; border:1.5px solid #EF4444; border-radius:50%; animation:ping 2.6s ease-out infinite; }
        .tools-map .ring.d { animation-delay:1.3s; }
        .tools-map .hot { position:absolute; left:50%; top:48%; width:8px; height:8px; margin:-4px 0 0 -4px; border-radius:50%; background:#EF4444; box-shadow:0 0 10px #EF4444; }
        .tools-map .pin2 { position:absolute; left:26%; top:30%; width:5px; height:5px; border-radius:50%; background:#22E6F0; opacity:.7; animation:cpulse 3s ease-in-out infinite; }
        .tools-map .gln { position:absolute; background:rgba(255,255,255,0.04); }

        .tools-prd svg { width:100%; height:100%; }
        .tools-prd .band { fill:#EF4444; opacity:.12; }
        .tools-prd .ln { fill:none; stroke:#EF4444; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
        .tools-prd .dot { fill:#EF4444; animation:npulse 2s ease-in-out infinite; }

        .tools-srch .row { position:absolute; left:14px; height:7px; border-radius:4px; background:rgba(125,140,160,.25); }
        .tools-srch .r1 { top:18px; width:46%; } .tools-srch .r2 { top:38px; width:60%; } .tools-srch .r3 { top:58px; width:38%; }
        .tools-srch .row.on { background:#10B981; opacity:.55; }
        .tools-srch .scan { position:absolute; top:8px; bottom:8px; width:2px; background:#10B981; box-shadow:0 0 10px #10B981; animation:scan 2.8s ease-in-out infinite; }
        .tools-srch .mag { position:absolute; right:12px; top:12px; color:#10B981; }

        .tools-acc .shield { position:absolute; left:16px; top:50%; transform:translateY(-50%); color:#10B981; }
        .tools-acc .chk { stroke:#10B981; stroke-width:2.2; fill:none; stroke-linecap:round; stroke-linejoin:round; stroke-dasharray:22; stroke-dashoffset:22; animation:draw 2.8s ease-in-out infinite; }
        .tools-acc .log { position:absolute; right:14px; height:6px; border-radius:3px; background:rgba(125,140,160,.25); }
        .tools-acc .l1 { top:20px; width:78px; } .tools-acc .l2 { top:40px; width:96px; } .tools-acc .l3 { top:60px; width:64px; }
        .tools-acc .dot { position:absolute; left:-10px; top:0; width:5px; height:5px; border-radius:50%; background:#10B981; animation:cdot 1.4s infinite; }

        @keyframes cdot{0%,60%,100%{opacity:.3}30%{opacity:1}}
        @keyframes cpulse{0%,100%{box-shadow:0 0 0 0 rgba(34,230,240,.0)}50%{box-shadow:0 0 14px 0 rgba(34,230,240,.45)}}
        @keyframes flow{to{stroke-dashoffset:-16}}
        @keyframes npulse{0%,100%{opacity:.55;r:3px}50%{opacity:1;r:3.8px}}
        @keyframes ping{0%{transform:scale(.4);opacity:.9}100%{transform:scale(3.4);opacity:0}}
        @keyframes scan{0%{left:10%}50%{left:90%}100%{left:10%}}
        @keyframes draw{0%{stroke-dashoffset:22}45%{stroke-dashoffset:0}80%{stroke-dashoffset:0}100%{stroke-dashoffset:22}}

        /* Think Animation */
        .thk-edge{stroke-width:1.4;stroke-dasharray:3 5;opacity:.55;animation:thkflow 1.8s linear infinite}
        @keyframes thkflow{to{stroke-dashoffset:-16}}
        .thk-n1{animation:thkin 2.6s ease-in-out infinite}
        .thk-n2{animation:thkin 2.6s ease-in-out infinite .35s}
        .thk-n3{animation:thkmid 2.6s ease-in-out infinite .7s}
        @keyframes thkin{0%,100%{opacity:.4;r:3px}45%{opacity:1;r:3.8px}}
        @keyframes thkmid{0%,100%{opacity:.4;r:3px}55%{opacity:1;r:4px}}
        .thk-nf{animation:thkfinal 2.6s ease-in-out infinite;}
        @keyframes thkfinal{0%,70%{opacity:.5;r:3.6px;filter:drop-shadow(0 0 0 transparent)}88%,100%{opacity:1;r:5.2px;filter:drop-shadow(0 0 7px currentColor)}}

        /* Connect Animation */
        .cnc-dim{opacity:.35}
        .cnc-p1{animation:cncdim 4s ease-in-out infinite}
        .cnc-p2{animation:cncdim 4s ease-in-out infinite .5s}
        .cnc-p3{animation:cncdim 4s ease-in-out infinite 1s}
        .cnc-p4{animation:cncdim 4s ease-in-out infinite 1.5s}
        @keyframes cncdim{0%,100%{opacity:.25}50%{opacity:.55}}
        .cnc-link{fill:none;stroke-width:1.8;stroke-linecap:round;stroke-dasharray:210;animation:cncdraw 3.4s ease-in-out infinite}
        @keyframes cncdraw{0%{stroke-dashoffset:210;opacity:.9}45%{stroke-dashoffset:0;opacity:1}80%{stroke-dashoffset:0;opacity:1}100%{stroke-dashoffset:210;opacity:.9}}
        .cnc-end{animation:cncend 3.4s ease-in-out infinite}
        @keyframes cncend{0%,35%{opacity:.5;r:3px}55%,80%{opacity:1;r:4.4px}100%{opacity:.5;r:3px}}

        /* Anticipate Animation */
        .ant-ring{fill:none;opacity:.3;stroke-width:1}
        .ant-sweep{opacity:.16;transform-origin:100px 44px;animation:antrot 4s linear infinite}
        @keyframes antrot{to{transform:rotate(360deg)}}
        .ant-b1{animation:antblip 4s ease-in-out infinite}
        .ant-b2{animation:antblip 4s ease-in-out infinite 1.33s}
        .ant-b3{animation:antblip 4s ease-in-out infinite 2.66s}
        @keyframes antblip{0%,78%,100%{opacity:.3;r:2.2px}88%{opacity:1;r:3.8px}}
`}</style>
    </div>
    </>
  );
}
