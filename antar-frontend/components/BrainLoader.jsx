"use client";

import { useEffect, useState } from "react";

// Brain loading state: a caption that steps through what is actually happening, and a
// row of step dots. (The orbiting-rings animation that used to sit above it was removed.)
const STEPS = {
  en: ["Loading FIR records", "Linking shared evidence", "Grouping by crime type", "Building the brain"],
  kn: ["FIR ದಾಖಲೆಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ", "ಹಂಚಿಕೆಯ ಸಾಕ್ಷ್ಯ ಜೋಡಿಸಲಾಗುತ್ತಿದೆ", "ಅಪರಾಧ ಪ್ರಕಾರವಾರು ಗುಂಪು", "ಬ್ರೈನ್ ನಿರ್ಮಾಣ"],
};

// The page shows this loader three times in a row while the Brain comes up (the route, the
// hub, then the graph itself), each a new instance. Kept per instance, the caption started
// again from the first step every time and faded in afresh, which read as a stutter. The
// clock is shared instead: every instance shows the step the first one would be on, and
// one that takes over from another does not fade in again.
const STEP_MS = 1300;
let startedAt = 0, lastSeen = 0;

export default function BrainLoader({ kn = false, fullscreen = false }) {
  const steps = STEPS[kn ? "kn" : "en"];
  // The steps run once and hold on the last: looping back to "Loading FIR records" while
  // the graph is being drawn said something that was no longer true.
  const at = () => Math.min(steps.length - 1, Math.floor((Date.now() - startedAt) / STEP_MS));
  const [handover] = useState(() => {
    const now = Date.now(), taking = now - lastSeen < 400;
    if (!taking) startedAt = now;
    lastSeen = now;
    return taking;
  });
  const [i, setI] = useState(at);
  const [first] = useState(i);                      // the step it took over on is already on screen
  useEffect(() => {
    const t = setInterval(() => { lastSeen = Date.now(); setI(at()); }, 200);
    return () => { lastSeen = Date.now(); clearInterval(t); };
  }, [steps.length]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className={`brl ${fullscreen ? "brl-full" : ""}${handover ? " brl-on" : ""}`} role="status" aria-live="polite">
      <div className="brl-cap">
        <span key={i} className={`brl-step${handover && i === first ? " still" : ""}`}>{steps[i]}…</span>
        <span className="brl-dots" aria-hidden="true">
          {steps.map((_, k) => <i key={k} className={k <= i ? "on" : ""} />)}
        </span>
      </div>
    </div>
  );
}
