"use client";

import { ThinkingOrb } from "thinking-orbs";

// The thinking orb (thinking-orbs, MIT). One animation per kind of work, so the orb says
// what the system is doing right now rather than just "busy": reading records searches,
// tracing links connects, a forecast solves, a dossier weaves, the answer composes.
const BY_AGENT = {
  query: "searching", vault: "searching", brain: "searching", recall: "searching", osint: "searching", search: "searching",
  network: "connecting", link: "connecting", linkage: "connecting", corridor: "connecting",
  forecast: "solving", predict: "solving", prediction: "solving", geo: "solving", pattern: "solving",
  alert_suggest: "solving", alerts: "solving", advocate_agent: "solving", adversary: "solving",
  research: "weaving", trace: "weaving",
  profile: "shaping", social: "shaping",
  synthesize: "composing", compose: "composing", answer: "composing", writer: "composing",
  voice: "listening", listen: "listening",
};

export function orbStateFor(agent) {
  return BY_AGENT[String(agent || "").toLowerCase()] || "working";
}

// size: 20 (inline with text) or 64 (avatar scale) - the two sizes the orbs are drawn for.
export default function Orb({ state, agent, size = 20, label, className, style }) {
  return (
    <ThinkingOrb
      state={state || orbStateFor(agent)}
      size={size}
      theme="dark"
      aria-label={label}
      className={className}
      style={{ flex: "none", ...style }}
    />
  );
}
