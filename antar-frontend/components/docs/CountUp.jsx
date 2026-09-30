"use client";

// rAF count-up for the wrap-up stats - real values only, no easing libs.

import { useEffect, useState } from "react";

export default function CountUp({ value = 0, duration = 1400, className, style }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const target = Number(value) || 0;
    if (typeof window === "undefined" ||
        window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setN(target);
      return;
    }
    const t0 = performance.now();
    let raf;
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / duration);
      setN(Math.round(target * (1 - Math.pow(1 - p, 3))));   // ease-out cubic
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <span className={className} style={style}>{n.toLocaleString()}</span>;
}
