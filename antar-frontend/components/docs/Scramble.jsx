"use client";

// Text scramble-decode (reference hero, 0s): random glyphs resolve left→right
// into the real text. Reduced-motion renders the final text instantly.

import { useEffect, useState } from "react";

const GLYPHS = "!<>-_\\/[]{}—=+*^?#ABCDEFXZ0123456789";

export default function Scramble({ text, duration = 1200, className, style }) {
  const [out, setOut] = useState(text);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setOut(text);
      return;
    }
    const chars = [...String(text || "")];
    const t0 = performance.now();
    let raf;
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / duration);
      const solved = Math.floor(p * chars.length);
      setOut(chars.map((c, i) =>
        i < solved || c === " " ? c : GLYPHS[(Math.random() * GLYPHS.length) | 0]
      ).join(""));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [text, duration]);

  return <span className={className} style={style}>{out}</span>;
}
