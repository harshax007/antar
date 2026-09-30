"use client";

import { useEffect, useRef, useState } from "react";

// Animated placeholder for a search box: types an example, holds it, erases it, moves to
// the next. It shows the officer WHAT to type ("ACC-KA-110413", "S0041") without taking
// the field over - it pauses the moment the box is focused or holds text, and honours
// prefers-reduced-motion by simply showing the first example.
//
//   const ph = useTypingPlaceholder(["S0041", "ACC-728352"], { prefix: "Try ", active: !focused && !value });
//   <input placeholder={ph || "Enter ACC-id"} … />
export default function useTypingPlaceholder(examples, { prefix = "", active = true, typeMs = 70, holdMs = 1600 } = {}) {
  const list = (examples || []).filter(Boolean);
  const key = list.join("|");
  const [text, setText] = useState("");
  const state = useRef({ i: 0, n: 0, dir: 1 });

  useEffect(() => {
    if (!active || list.length === 0) { setText(""); return; }
    const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { setText(prefix + list[0]); return; }
    let t;
    const tick = () => {
      const s = state.current;
      const word = list[s.i % list.length];
      s.n += s.dir;
      setText(prefix + word.slice(0, Math.max(0, s.n)));
      if (s.dir > 0 && s.n >= word.length) { s.dir = -1; t = setTimeout(tick, holdMs); return; }
      if (s.dir < 0 && s.n <= 0) { s.dir = 1; s.i += 1; t = setTimeout(tick, 350); return; }
      t = setTimeout(tick, s.dir > 0 ? typeMs : typeMs / 2);
    };
    t = setTimeout(tick, 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, key, prefix, typeMs, holdMs]);

  return text;
}
