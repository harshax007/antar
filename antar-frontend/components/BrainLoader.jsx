"use client";

import { useEffect, useState } from "react";

// Brain loading animation: a core that pulses while "neurons" orbit it on three tilted
// rings, and a caption that steps through what is actually happening. Pure SVG + CSS —
// nothing for the GPU to build while the real graph is being prepared - and it holds
// still under prefers-reduced-motion.
const STEPS = {
  en: ["Loading FIR records", "Linking shared evidence", "Grouping by crime type", "Building the brain"],
  kn: ["FIR ದಾಖಲೆಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ", "ಹಂಚಿಕೆಯ ಸಾಕ್ಷ್ಯ ಜೋಡಿಸಲಾಗುತ್ತಿದೆ", "ಅಪರಾಧ ಪ್ರಕಾರವಾರು ಗುಂಪು", "ಬ್ರೈನ್ ನಿರ್ಮಾಣ"],
};

export default function BrainLoader({ kn = false, fullscreen = false }) {
  const [i, setI] = useState(0);
  // SMIL ignores CSS, so reduced motion is honoured here: dots rest on their rings.
  const [still, setStill] = useState(false);
  useEffect(() => {
    try { setStill(!!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches); } catch {}
  }, []);
  const steps = STEPS[kn ? "kn" : "en"];
  useEffect(() => {
    const t = setInterval(() => setI((v) => (v + 1) % steps.length), 1300);
    return () => clearInterval(t);
  }, [steps.length]);

  return (
    <div className={`brl ${fullscreen ? "brl-full" : ""}`} role="status" aria-live="polite">
      <svg className="brl-svg" viewBox="-60 -60 120 120" aria-hidden="true">
        <defs>
          <radialGradient id="brlCore" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#8ff7ff" stopOpacity="0.95" />
            <stop offset="60%" stopColor="#22e6f0" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#22e6f0" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle className="brl-core" r="16" fill="url(#brlCore)" />
        {[0, 60, 120].map((tilt, k) => (
          <g key={tilt} transform={`rotate(${tilt})`}>
            <ellipse rx="44" ry="15" fill="none" stroke="rgba(34,230,240,.16)" strokeWidth="0.8" />
            {/* animateMotion keeps each dot round as it travels its ring */}
            {[0, 0.5].map((phase) => (
              <circle key={phase} r={phase ? 1.6 : 2.6}
                      fill={phase ? "rgba(226,232,240,.8)" : ["#22e6f0", "#86efac", "#fbbf24"][k]}
                      cx={still ? (phase ? -44 : 44) : 0} cy="0">
                {!still && (
                  <animateMotion dur={`${[2.4, 3.1, 3.8][k]}s`} repeatCount="indefinite"
                                 begin={`-${phase * [2.4, 3.1, 3.8][k]}s`}
                                 keyPoints={k === 1 ? "1;0" : "0;1"} keyTimes="0;1" calcMode="linear"
                                 path="M44,0 A44,15 0 1,1 -44,0 A44,15 0 1,1 44,0" />
                )}
              </circle>
            ))}
          </g>
        ))}
      </svg>
      <div className="brl-cap">
        <span key={i} className="brl-step">{steps[i]}…</span>
        <span className="brl-dots" aria-hidden="true">
          {steps.map((_, k) => <i key={k} className={k <= i ? "on" : ""} />)}
        </span>
      </div>
    </div>
  );
}
