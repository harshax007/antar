"use client";

import { useEffect, useState } from "react";
import Orb from "@/components/Orb";

// Brain loading state: a caption that steps through what is actually happening, cross-fading
// from one step to the next, over a thin bar that fills as the steps go by.
const STEPS = {
  en: ["Loading FIR records", "Linking shared evidence", "Grouping by crime type", "Building the brain"],
  kn: ["FIR ದಾಖಲೆಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ", "ಹಂಚಿಕೆಯ ಸಾಕ್ಷ್ಯ ಜೋಡಿಸಲಾಗುತ್ತಿದೆ", "ಅಪರಾಧ ಪ್ರಕಾರವಾರು ಗುಂಪು", "ಬ್ರೈನ್ ನಿರ್ಮಾಣ"],
};

// The page shows this loader three times in a row while the Brain comes up (the route, the
// hub, then the graph itself), each a new instance. The clock is shared, so every instance
// shows the step the first one would be on, and one that takes over from another does not
// fade in again. Each step stays long enough to read; the text cross-fades and the bar
// fills smoothly, instead of the caption being swapped and the dots snapping on.
const STEP_MS = 2400;
// The orb above the caption does what the caption says: reads, links, groups, builds.
const STEP_ORB = ["searching", "connecting", "shaping", "working"];
let startedAt = 0, lastSeen = 0;

// Other screens pass their own steps and orb states (the Map does); the Brain's are the default.
export const MAP_STEPS = {
  en: ["Loading the district map", "Reading the day's FIRs", "Finding hotspots", "Drawing the map"],
  kn: ["ಜಿಲ್ಲಾ ನಕ್ಷೆ ಲೋಡ್ ಆಗುತ್ತಿದೆ", "ದಿನದ FIR ಗಳನ್ನು ಓದಲಾಗುತ್ತಿದೆ", "ಹಾಟ್‌ಸ್ಪಾಟ್ ಹುಡುಕಲಾಗುತ್ತಿದೆ", "ನಕ್ಷೆ ರಚನೆ"],
};
export const MAP_ORBS = ["shaping", "searching", "solving", "working"];

export default function BrainLoader({ kn = false, fullscreen = false, steps: own, orbs = STEP_ORB, className = "" }) {
  const steps = (own || STEPS)[kn ? "kn" : "en"];
  // The steps run once and hold on the last: looping back to "Loading FIR records" while
  // the graph is being drawn said something that was no longer true.
  const at = () => Math.min(steps.length - 1, Math.floor((Date.now() - startedAt) / STEP_MS));
  const [handover] = useState(() => {
    const now = Date.now(), taking = now - lastSeen < 600;
    if (!taking) startedAt = now;
    lastSeen = now;
    return taking;
  });
  const [i, setI] = useState(at);
  useEffect(() => {
    const t = setInterval(() => { lastSeen = Date.now(); setI(at()); }, 200);
    return () => { lastSeen = Date.now(); clearInterval(t); };
  }, [steps.length]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className={`brl ${fullscreen ? "brl-full" : ""}${handover ? " brl-on" : ""}${className ? ` ${className}` : ""}`} role="status" aria-live="polite">
      <Orb state={orbs[i] || "working"} size={64} label={steps[i]} />
      <div className="brl-cap">
        <div className="brl-steps">
          {steps.map((s, k) => (
            <span key={k} className={`brl-step${k === i ? " on" : ""}`} aria-hidden={k !== i}>{s}…</span>
          ))}
        </div>
        <div className="brl-bar" aria-hidden="true">
          <i style={{ width: `${((i + 1) / steps.length) * 100}%` }} />
        </div>
      </div>
    </div>
  );
}
