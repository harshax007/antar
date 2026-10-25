"use client";

// One auto-demo stage: left = live terminal (real /think|/connect|/anticipate
// stream), right = HoloStage 3D animation. Slide-swapped by the parent.

import { motion } from "framer-motion";
import HoloStage from "@/components/docs/HoloStage";

const EMOJI_RE = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}\u{200D}]/gu;
const clean = (s) => String(s || "").replace(EMOJI_RE, "").trim();

export default function DemoStage({ stage, accent, eyebrow, title, desc, msg, status, kn }) {
  const steps = msg?.steps || [];
  const streaming = !!msg?.streaming;
  return (
    <motion.div
      key={stage}
      className="dmo-stage"
      initial={{ opacity: 0, x: 42 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -42 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Left - terminal view (reference: typing feature panel) */}
      <div className="dmo-term" style={{ "--acc": accent }}>
        <div className="dmo-term-hd">
          <span className="dot" />
          <span className="ttl">{eyebrow}</span>
          <span className="st">
            {status === "running" ? (kn ? "[ ಲೈವ್ ]" : "[ RUNNING LIVE ]")
              : status === "done" ? (kn ? "[ ಪೂರ್ಣ ]" : "[ COMPLETE ]")
              : status === "offline" ? "[ WAKING UP ]" : "[ QUEUED ]"}
          </span>
        </div>
        <div className="dmo-term-bd" role="log" aria-live="polite">
          <div className="cmd">{`> /${stage} ${msg?.question || ""}`}</div>
          {steps.map((s, i) => (
            <div key={i} className={`stp ${s.status}`}>
              {`[${s.status === "done" ? "ok" : s.status === "degraded" ? "!!" : ".."}] ${s.agent.padEnd(9)} ${clean(s.label)}`}
            </div>
          ))}
          {msg?.text && (
            <div className="ans">
              {clean(msg.text)}
              {streaming && <span className="cur">▌</span>}
            </div>
          )}
          {status === "offline" && (
            <div className="stp degraded">
              {kn ? "ಸರ್ವರ್ ಎಚ್ಚರಗೊಳ್ಳುತ್ತಿದೆ - ಈ ಹಂತವನ್ನು ಬಿಟ್ಟುಬಿಡಲಾಗಿದೆ." : "Antar was still waking up on the server - stage skipped, nothing simulated."}
            </div>
          )}
          {status === "done" && msg && (
            <div className="fct">
              {`> ${(msg.citations || []).length} citation(s) · ${(msg.brainHits || []).length} Second-Brain match(es) · ${steps.filter((s) => s.status === "done").length} agent step(s)`}
            </div>
          )}
        </div>
      </div>

      {/* Right - simple 3D animation + editorial line */}
      <div className="dmo-side">
        <HoloStage stage={stage} accent={accent} label={title} />
        <div className="dmo-side-copy">
          <div className="eyebrow" style={{ color: accent }}>{eyebrow}</div>
          <h3>{title}</h3>
          <p>{desc}</p>
        </div>
      </div>
    </motion.div>
  );
}
