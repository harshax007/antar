"use client";

import { useEffect, useState } from "react";

// Brain loading state: a caption that steps through what is actually happening, and a
// row of step dots. (The orbiting-rings animation that used to sit above it was removed.)
const STEPS = {
  en: ["Loading FIR records", "Linking shared evidence", "Grouping by crime type", "Building the brain"],
  kn: ["FIR ದಾಖಲೆಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ", "ಹಂಚಿಕೆಯ ಸಾಕ್ಷ್ಯ ಜೋಡಿಸಲಾಗುತ್ತಿದೆ", "ಅಪರಾಧ ಪ್ರಕಾರವಾರು ಗುಂಪು", "ಬ್ರೈನ್ ನಿರ್ಮಾಣ"],
};

export default function BrainLoader({ kn = false, fullscreen = false }) {
  const [i, setI] = useState(0);
  const steps = STEPS[kn ? "kn" : "en"];
  useEffect(() => {
    const t = setInterval(() => setI((v) => (v + 1) % steps.length), 1300);
    return () => clearInterval(t);
  }, [steps.length]);

  return (
    <div className={`brl ${fullscreen ? "brl-full" : ""}`} role="status" aria-live="polite">
      <div className="brl-cap">
        <span key={i} className="brl-step">{steps[i]}…</span>
        <span className="brl-dots" aria-hidden="true">
          {steps.map((_, k) => <i key={k} className={k <= i ? "on" : ""} />)}
        </span>
      </div>
    </div>
  );
}
