"use client";
// Questions by year, 2016 to 2026, on the empty chat. Pick a year; its questions appear
// with one line on what that year's data can bear. Every question shape here was run for
// every year through the router and the answer writer before it was put here
// (tests/test_suggestions_real.py runs them all again). None asks for a raw count: the
// years differ in what the registry holds, and a count is the figure that misleads first.
import { useState } from "react";

export const YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];

export const TEMPLATES = {
  en: [
    "Which districts had the most theft in {y}?",
    "IPC/BNS vs SLL split for {y}?",
    "Peak month for cybercrime in {y}?",
    "Conviction rate by district in {y}",
    "Crimes against women by district in {y}",
  ],
  kn: [
    "{y} ರಲ್ಲಿ ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ನಡೆದಿದೆ?",
    "{y} ರ IPC/BNS ಮತ್ತು SLL ಹಂಚಿಕೆ",
    "{y}ರಲ್ಲಿ ಸೈಬರ್ ಅಪರಾಧದ ಗರಿಷ್ಠ ತಿಂಗಳು?",
    "{y} ರಲ್ಲಿ ಜಿಲ್ಲಾವಾರು ಶಿಕ್ಷೆ ಪ್ರಮಾಣ",
    "{y} ರಲ್ಲಿ ಜಿಲ್ಲಾವಾರು ಮಹಿಳೆಯರ ಮೇಲಿನ ಅಪರಾಧ",
  ],
};

// What each year's data can bear (PROGRESS.md, open risks).
function basis(y, kn) {
  if (y <= 2022) return kn ? "ಈ ವರ್ಷದ ಸುಮಾರು ಮೂರನೇ ಒಂದು ಭಾಗ ಮಾತ್ರ ದಾಖಲೆಯಲ್ಲಿದೆ: ಪಾಲು ಮತ್ತು ಶ್ರೇಣಿಯನ್ನು ಓದಿ, ಎಣಿಕೆಯನ್ನಲ್ಲ."
                            : "The registry holds about a third of this year: read the shares and rankings, not the counts.";
  if (y === 2023) return kn ? "ಪೂರ್ಣ ವರ್ಷ, ಆದರೆ 85,264 ಸಾಲುಗಳು ನಕಲು: ಎಣಿಕೆಗಳು ಸುಮಾರು 22% ಹೆಚ್ಚು."
                            : "A complete year, but 85,264 rows are duplicated: counts run about 22% high.";
  if (y === 2024) return kn ? "10 ಮಾರ್ಚ್ 2024 ರವರೆಗೆ ನೈಜ ದಾಖಲೆ (14,736 ನಕಲು ಸಾಲುಗಳೊಂದಿಗೆ); ಉಳಿದದ್ದು ಪ್ರಾತ್ಯಕ್ಷಿಕೆ ದತ್ತಾಂಶ."
                            : "Real record to 10 March 2024 (with 14,736 duplicated rows); the rest of the year is demonstration data.";
  const now = y === new Date().getFullYear();
  return kn ? `ಪ್ರಾತ್ಯಕ್ಷಿಕೆ ದತ್ತಾಂಶ, ನೋಂದಾಯಿತ FIR ಗಳಲ್ಲ.${now ? " ವರ್ಷ ಇನ್ನೂ ಮುಗಿದಿಲ್ಲ." : ""}`
            : `Demonstration data, not registered FIRs.${now ? " The year is still in progress." : ""}`;
}

export default function YearQuestions({ lang = "en", onAsk }) {
  const kn = lang === "kn";
  const [year, setYear] = useState(null);
  const qs = year ? (TEMPLATES[lang] || TEMPLATES.en).map((t) => t.replace("{y}", String(year))) : [];
  return (
    <div className="yq">
      <div className="yq-years" role="group" aria-label={kn ? "ವರ್ಷವಾರು ಪ್ರಶ್ನೆಗಳು" : "Questions by year"}>
        <span className="yq-lbl">{kn ? "ವರ್ಷ:" : "By year:"}</span>
        {YEARS.map((y) => (
          <button key={y} type="button" className={y === year ? "on" : ""} aria-pressed={y === year}
                  onClick={() => setYear(y === year ? null : y)}>{y}</button>
        ))}
      </div>
      {year && (
        <>
          <p className="yq-basis">{basis(year, kn)}</p>
          <div className="yq-qs">
            {qs.map((q) => <button key={q} type="button" onClick={() => onAsk?.(q)}>{q}</button>)}
          </div>
        </>
      )}
      <style jsx>{`
        .yq { display: flex; flex-direction: column; align-items: center; gap: 8px; margin-top: 10px; max-width: 760px; }
        .yq-years { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 6px; }
        .yq-lbl { font-size: 11px; color: rgba(255, 255, 255, 0.42); margin-right: 2px; font-family: 'Inter', sans-serif; }
        .yq-years button { font: 500 11px 'Inter', sans-serif; color: rgba(255, 255, 255, 0.6); background: rgba(255, 255, 255, 0.04);
          border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 9999px; padding: 3px 9px; cursor: pointer; transition: all 0.15s; }
        .yq-years button:hover { color: #fff; border-color: rgba(255, 255, 255, 0.2); }
        .yq-years button.on { color: #fff; background: rgba(96, 165, 250, 0.16); border-color: rgba(96, 165, 250, 0.45); }
        .yq-basis { margin: 2px 0 0; font: 400 11.5px/1.45 'Inter', sans-serif; color: rgba(227, 179, 65, 0.85); text-align: center; }
        .yq-qs { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px 14px; }
        .yq-qs button { background: transparent; border: none; color: rgba(255, 255, 255, 0.65); font: 400 13px/1.4 'Inter', sans-serif;
          cursor: pointer; padding: 4px 8px; text-align: left; transition: color 0.2s; }
        .yq-qs button:hover { color: #fff; }
      `}</style>
    </div>
  );
}
