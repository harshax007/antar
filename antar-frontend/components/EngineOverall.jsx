"use client";
// How the forecast engine behaves overall: the global view that sits beside "Why this
// forecast". Which reasons move forecasts for each kind of crime, how each kind did in the
// back-test, where the engine is weakest by its own figures, and what it does not use.
// Read from /api/forecast/explain; nothing here is typed in.
import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";

const pct = (v) => (v == null ? "—" : `${Math.round(v * 100)}%`);

export default function EngineOverall() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    let alive = true;
    fetchAPI("/api/forecast/explain?unit=station&horizon=7")
      .then((x) => { if (alive) setD(x); })
      .catch((e) => { if (alive) setErr(e?.status === 404 ? "restart" : "failed"); });
    return () => { alive = false; };
  }, []);

  if (err) return <p className="eo-note">{err === "restart" ? "The overall view needs the server restarted to load it." : "The overall view could not be read just now."}</p>;
  if (!d) return <p className="eo-note">Reading how the engine behaves overall…</p>;
  const label = d.reason_labels || {};

  return (
    <div className="eo">
      <h4>How the engine behaves overall</h4>
      <p className="eo-lede">Station forecasts for the next 7 days. For each kind of crime: the reason that moves forecasts most, and how the engine did on 23 weeks of the real record it had not seen.</p>
      <div className="eo-wrap">
        <table className="eo-table">
          <thead>
            <tr><th>Kind of crime</th><th>What moves it most</th><th>Top 5% of stations caught</th><th>Weeks it beat recent history</th><th>Likely range held</th></tr>
          </thead>
          <tbody>
            {d.categories.map((c) => {
              const r = c.reasons?.[0], b = c.backtest;
              return (
                <tr key={c.category}>
                  <td><b>{c.label}</b><small>{c.units.toLocaleString("en-IN")} stations</small></td>
                  <td>{r ? <>{label[r.key] || r.key}<small>typically moves a forecast {pct(r.typical_move)}; by 10% or more at {pct(r.share_notable)} of stations</small></> : "—"}</td>
                  <td>{b ? <>{pct(b.top5_share_caught)}<small>recent history: {pct(b.top5_share_caught_last4)}</small></> : "not tested"}</td>
                  <td>{b ? `${b.weeks_better_than_last4} of ${b.weeks}` : "—"}</td>
                  <td>{b ? pct(b.coverage80) : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="eo-two">
        <div>
          <h5>Where it is weakest</h5>
          {d.weakest?.length ? (
            <ul>{d.weakest.map((w) => <li key={w.category}><b>{w.label}</b>: {w.why.join("; ")}.</li>)}</ul>
          ) : <p>No category falls outside the back-test's own limits.</p>}
        </div>
        <div>
          <h5>What it does not use</h5>
          <ul>{(d.not_used || []).map((x) => <li key={x}>{x}</li>)}</ul>
        </div>
      </div>
      {d.fairness && (
        <div className="eo-fair">
          <h4>Fairness and feedback</h4>
          <p className="eo-lede">Measured on the back-test's own flags (the top 5% of stations each week, {d.fairness.weeks} weeks). A forecast of registered cases can keep sending attention to the same places; this is how far it does.</p>
          <ul className="eo-find">{d.fairness.findings.map((x) => <li key={x}>{x}</li>)}</ul>
          <div className="eo-two">
            <div>
              <h5>Not measured</h5>
              <ul>{d.fairness.not_measured.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
            <div>
              <h5>How to use a flag</h5>
              <ul>{d.fairness.what_to_do.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
          </div>
        </div>
      )}
      <p className="eo-note">{d.method}</p>
    </div>
  );
}
