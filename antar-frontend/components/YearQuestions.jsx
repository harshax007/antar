"use client";
// Questions by year, 2016 to 2026, on the empty chat. Picking a year replaces the
// suggested questions above with that year's; picking it again brings the usual ones back.
// Every question shape here was run for every year through the router and the answer
// writer (tests/test_suggestions_real.py runs them all again). None asks for a raw count.
// An answer about a year after the real record says so itself (answer_writer).

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

export function yearQuestions(year, lang = "en") {
  return (TEMPLATES[lang] || TEMPLATES.en).map((t) => t.replace("{y}", String(year)));
}

export default function YearQuestions({ lang = "en", year = null, onYear }) {
  const kn = lang === "kn";
  return (
    <div className="yq-years" role="group" aria-label={kn ? "ವರ್ಷವಾರು ಪ್ರಶ್ನೆಗಳು" : "Questions by year"}>
      <span className="yq-lbl">{kn ? "ವರ್ಷ:" : "By year:"}</span>
      {YEARS.map((y) => (
        <button key={y} type="button" className={y === year ? "on" : ""} aria-pressed={y === year}
                onClick={() => onYear?.(y === year ? null : y)}>{y}</button>
      ))}
      <style jsx>{`
        .yq-years { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 6px; margin-top: 10px; max-width: 760px; }
        .yq-lbl { font-size: 11px; color: rgba(255, 255, 255, 0.42); margin-right: 2px; font-family: 'Inter', sans-serif; }
        .yq-years button { font: 500 11px 'Inter', sans-serif; color: rgba(255, 255, 255, 0.6); background: rgba(255, 255, 255, 0.04);
          border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 9999px; padding: 3px 9px; cursor: pointer; transition: all 0.15s; }
        .yq-years button:hover { color: #fff; border-color: rgba(255, 255, 255, 0.2); }
        .yq-years button.on { color: #fff; background: rgba(96, 165, 250, 0.16); border-color: rgba(96, 165, 250, 0.45); }
      `}</style>
    </div>
  );
}
