"use client";
// How the forecast engine behaves overall: the global view that sits beside "Why this
// forecast". Which reasons move forecasts for each kind of crime, how each kind did in the
// back-test, where the engine is weakest by its own figures, and what it does not use.
// Read from /api/forecast/explain; nothing here is typed in.
import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";
import { crimeKn } from "@/lib/kn";

const REASON_KN = { recent: "ಕಳೆದ 4 ವಾರಗಳು", last_year: "ಕಳೆದ ವರ್ಷದ ಇದೇ ವಾರಗಳು", neighbours: "ಪಕ್ಕದ ಠಾಣೆಗಳು",
                    area: "ಇಡೀ ಜಿಲ್ಲೆ", season: "ವರ್ಷದ ಸಮಯ", level: "ಜಿಲ್ಲೆಯ ಮಟ್ಟದ ಕಡೆಗೆ ಎಳೆತ" };

const pct = (v) => (v == null ? "—" : `${Math.round(v * 100)}%`);

export default function EngineOverall({ kn = false }) {
  const L = (en, k) => (kn ? k : en);
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    let alive = true;
    fetchAPI("/api/forecast/explain?unit=station&horizon=7")
      .then((x) => { if (alive) setD(x); })
      .catch((e) => { if (alive) setErr(e?.status === 404 ? "restart" : "failed"); });
    return () => { alive = false; };
  }, []);

  if (err) return <p className="eo-note">{err === "restart" ? L("The overall view needs the server restarted to load it.", "ಒಟ್ಟಾರೆ ನೋಟ ಲೋಡ್ ಆಗಲು ಸರ್ವರ್ ಮರುಆರಂಭಿಸಬೇಕು.") : L("The overall view could not be read just now.", "ಒಟ್ಟಾರೆ ನೋಟವನ್ನು ಈಗ ಓದಲಾಗಲಿಲ್ಲ.")}</p>;
  if (!d) return <p className="eo-note">{L("Reading how the engine behaves overall…", "ಎಂಜಿನ್ ಒಟ್ಟಾರೆ ಹೇಗೆ ವರ್ತಿಸುತ್ತದೆ ಎಂದು ಓದುತ್ತಿದೆ…")}</p>;
  const label = d.reason_labels || {};

  return (
    <div className="eo">
      <h4>{L("How the engine behaves overall", "ಎಂಜಿನ್ ಒಟ್ಟಾರೆ ಹೇಗೆ ವರ್ತಿಸುತ್ತದೆ")}</h4>
      <p className="eo-lede">{L("Station forecasts for the next 7 days. For each kind of crime: the reason that moves forecasts most, and how the engine did on 23 weeks of the real record it had not seen.",
        "ಮುಂದಿನ 7 ದಿನಗಳ ಠಾಣಾ ಮುನ್ಸೂಚನೆಗಳು. ಪ್ರತಿ ಬಗೆಯ ಅಪರಾಧಕ್ಕೆ: ಮುನ್ಸೂಚನೆಯನ್ನು ಹೆಚ್ಚು ಬದಲಿಸುವ ಕಾರಣ, ಮತ್ತು ಎಂಜಿನ್ ಮೊದಲು ನೋಡಿರದ ನೈಜ ದಾಖಲೆಯ 23 ವಾರಗಳಲ್ಲಿ ಅದು ಹೇಗೆ ಮಾಡಿತು.")}</p>
      <div className="eo-wrap">
        <table className="eo-table">
          <thead>
            {kn
              ? <tr><th>ಅಪರಾಧದ ಬಗೆ</th><th>ಹೆಚ್ಚು ಬದಲಿಸುವುದು</th><th>ಹಿಡಿದ ಮೇಲಿನ 5% ಠಾಣೆಗಳು</th><th>ಇತ್ತೀಚಿನ ಇತಿಹಾಸಕ್ಕಿಂತ ಉತ್ತಮವಾದ ವಾರಗಳು</th><th>ಸಂಭಾವ್ಯ ವ್ಯಾಪ್ತಿ ಸರಿಯಾದದ್ದು</th></tr>
              : <tr><th>Kind of crime</th><th>What moves it most</th><th>Top 5% of stations caught</th><th>Weeks it beat recent history</th><th>Likely range held</th></tr>}
          </thead>
          <tbody>
            {d.categories.map((c) => {
              const r = c.reasons?.[0], b = c.backtest;
              return (
                <tr key={c.category}>
                  <td><b>{(kn && crimeKn(c.label)) || c.label}</b><small>{c.units.toLocaleString("en-IN")} {L("stations", "ಠಾಣೆಗಳು")}</small></td>
                  <td>{r ? <>{(kn && REASON_KN[r.key]) || label[r.key] || r.key}<small>{kn
                    ? `ಸಾಮಾನ್ಯವಾಗಿ ಮುನ್ಸೂಚನೆಯನ್ನು ${pct(r.typical_move)} ಬದಲಿಸುತ್ತದೆ; ${pct(r.share_notable)} ಠಾಣೆಗಳಲ್ಲಿ 10% ಅಥವಾ ಹೆಚ್ಚು`
                    : `typically moves a forecast ${pct(r.typical_move)}; by 10% or more at ${pct(r.share_notable)} of stations`}</small></> : "—"}</td>
                  <td>{b ? <>{pct(b.top5_share_caught)}<small>{L("recent history", "ಇತ್ತೀಚಿನ ಇತಿಹಾಸ")}: {pct(b.top5_share_caught_last4)}</small></> : L("not tested", "ಪರೀಕ್ಷಿಸಿಲ್ಲ")}</td>
                  <td>{b ? (kn ? `${b.weeks} ರಲ್ಲಿ ${b.weeks_better_than_last4}` : `${b.weeks_better_than_last4} of ${b.weeks}`) : "—"}</td>
                  <td>{b ? pct(b.coverage80) : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="eo-two">
        <div>
          <h5>{L("Where it is weakest", "ಎಲ್ಲಿ ಅತಿ ದುರ್ಬಲ")}</h5>
          {d.weakest?.length ? (
            <ul>{d.weakest.map((w) => <li key={w.category}><b>{(kn && crimeKn(w.label)) || w.label}</b>: {w.why.join("; ")}.</li>)}</ul>
          ) : <p>{L("No category falls outside the back-test's own limits.", "ಯಾವುದೇ ವರ್ಗ ಹಿನ್ನೋಟ ಪರೀಕ್ಷೆಯ ಮಿತಿಗಳ ಹೊರಗೆ ಬೀಳುವುದಿಲ್ಲ.")}</p>}
        </div>
        <div>
          <h5>{L("What it does not use", "ಇದು ಬಳಸದಿರುವುದು")}</h5>
          <ul>{(d.not_used || []).map((x) => <li key={x}>{x}</li>)}</ul>
        </div>
      </div>
      {d.fairness && (
        <div className="eo-fair">
          <h4>{L("Fairness and feedback", "ನ್ಯಾಯಸಮ್ಮತತೆ ಮತ್ತು ಪುನರಾವರ್ತನೆ")}</h4>
          <p className="eo-lede">{kn
            ? `ಹಿನ್ನೋಟ ಪರೀಕ್ಷೆಯ ತನ್ನದೇ ಗುರುತುಗಳ ಮೇಲೆ ಅಳೆಯಲಾಗಿದೆ (ಪ್ರತಿ ವಾರ ಮೇಲಿನ 5% ಠಾಣೆಗಳು, ${d.fairness.weeks} ವಾರಗಳು). ದಾಖಲಾದ ಪ್ರಕರಣಗಳ ಮುನ್ಸೂಚನೆ ಅದೇ ಸ್ಥಳಗಳಿಗೆ ಗಮನ ಕಳುಹಿಸುತ್ತಲೇ ಇರಬಹುದು; ಇದು ಎಷ್ಟರ ಮಟ್ಟಿಗೆ ಎಂಬುದು.`
            : `Measured on the back-test's own flags (the top 5% of stations each week, ${d.fairness.weeks} weeks). A forecast of registered cases can keep sending attention to the same places; this is how far it does.`}</p>
          <ul className="eo-find">{d.fairness.findings.map((x) => <li key={x}>{x}</li>)}</ul>
          <div className="eo-two">
            <div>
              <h5>{L("Not measured", "ಅಳೆಯದಿರುವುದು")}</h5>
              <ul>{d.fairness.not_measured.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
            <div>
              <h5>{L("How to use a flag", "ಗುರುತನ್ನು ಹೇಗೆ ಬಳಸುವುದು")}</h5>
              <ul>{d.fairness.what_to_do.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
          </div>
        </div>
      )}
      <p className="eo-note">{d.method}</p>
    </div>
  );
}
