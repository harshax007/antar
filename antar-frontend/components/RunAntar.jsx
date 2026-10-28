"use client";

// "Explore Antar", a slim tab on the left edge of the chat start screen: one click and Antar picks a question
// it can answer, shuffles to it, types it into the box and asks it - the quickest way to
// see the whole system work. The pool is the page's own starter questions (passed in),
// which are answered from the register; ones naming a single FIR are left out, since a
// copy of the register that starts later (the Cloud one holds 2022 on) may not hold it.

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const IDLE_MS = Number(process.env.NEXT_PUBLIC_RUN_IDLE_MS) || 150_000;   // 2.5 minutes
const reduced = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function RunAntar({ pool, kn, busy, onType, onRun }) {
  const [phase, setPhase] = useState("idle");      // idle | shuffle | type
  const [shown, setShown] = useState("");
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const timers = useRef([]);
  const runRef = useRef(null);
  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  // Left alone on the start screen (a demo screen, a kiosk), Antar runs itself after
  // IDLE_MS: any tap, key, scroll or typing starts the wait again, and a hidden tab waits.
  useEffect(() => {
    let t;
    const arm = () => { clearTimeout(t); t = setTimeout(fire, IDLE_MS); };
    const fire = () => (document.hidden ? arm() : runRef.current?.());
    const evs = ["pointerdown", "keydown", "wheel", "touchstart", "input"];
    evs.forEach((e) => window.addEventListener(e, arm, { passive: true, capture: true }));
    document.addEventListener("visibilitychange", arm);
    arm();
    return () => { clearTimeout(t); evs.forEach((e) => window.removeEventListener(e, arm, { capture: true })); document.removeEventListener("visibilitychange", arm); };
  }, []);

  const later = (fn, ms) => { timers.current.push(setTimeout(fn, ms)); };

  function run() {
    const qs = (pool || []).filter((q) => !/\bFIR\s+[A-Z]?\d{4,}|\bFIR\s+[A-Z]\d+/i.test(q));
    if (!qs.length || phase !== "idle" || busy) return;
    const pick = qs[Math.floor(Math.random() * qs.length)];
    if (reduced()) { onRun(pick); return; }

    // shuffle: fast at first, slowing like a wheel coming to rest, then land on the pick
    setPhase("shuffle");
    let t = 0;
    for (let i = 0; i < 11; i += 1) {
      t += 55 + i * i * 2.2;
      later(() => setShown(qs[Math.floor(Math.random() * qs.length)]), t);
    }
    t += 140;
    later(() => setShown(pick), t);

    // type it into the box, then ask it
    t += 520;
    later(() => setPhase("type"), t);
    const step = Math.max(14, Math.min(28, 900 / pick.length));
    for (let i = 1; i <= pick.length; i += 1) later(() => onType(pick.slice(0, i)), t + i * step);
    t += pick.length * step + 260;
    later(() => { setPhase("idle"); setShown(""); onRun(pick); }, t);
  }

  runRef.current = run;
  const running = phase !== "idle";
  // Portalled to <body>: the hero it sits in is animated with a transform, and a fixed
  // element inside a transformed parent is pinned to that parent, not to the screen.
  if (!mounted) return null;
  return createPortal(
    <div className={`cx-run${running ? " is-running" : ""}`}>
      <button type="button" className="cx-run-btn" onClick={run} disabled={running || busy}
              aria-label={kn ? "Antar ಅನ್ವೇಷಿಸಿ: ಒಂದು ಪ್ರಶ್ನೆಯನ್ನು ಆರಿಸಿ ಕೇಳುತ್ತದೆ" : "Explore Antar: picks a question and asks it"}>
        <span className="cx-run-ico" aria-hidden="true">▶</span>
        {running ? (kn ? "ಆರಿಸಲಾಗುತ್ತಿದೆ…" : "Picking…") : (kn ? "Antar ಅನ್ವೇಷಿಸಿ" : "Explore Antar")}
      </button>
      <div className="cx-run-ticker" aria-live="polite">
        {running && <span key={shown} className={phase === "type" ? "landed" : ""}>{shown}</span>}
      </div>
    </div>,
    document.body
  );
}
