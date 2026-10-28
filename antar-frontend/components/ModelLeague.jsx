/**
 * ModelLeague.jsx — Champion vs Challenger Forecast League Table (Phase L6)
 * Compares Poisson GLM (Champion) vs LightGBM (Challenger) with Mondrian
 * conformal coverage, PAI@5%, PEI@5%, and TreeSHAP driver attributions.
 */
import React, { useState, useEffect } from "react";

export default function ModelLeague({ kn = false }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [category, setCategory] = useState("ALL");
  const [unitType, setUnitType] = useState("station");
  const [horizon, setHorizon] = useState(7);
  const [explainOpen, setExplainOpen] = useState(false);
  const [explainData, setExplainData] = useState(null);
  const [explainLoading, setExplainLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    fetch("/api/forecast/league")
      .then((res) => {
        if (!res.ok) throw new Error("Forecast league data unavailable");
        return res.json();
      })
      .then((d) => {
        if (mounted) {
          setData(d);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const openExplain = () => {
    setExplainOpen(true);
    setExplainLoading(true);
    fetch(`/api/forecast/league/explain?category=${category}&unit=${unitType}&horizon=${horizon}`)
      .then((res) => res.json())
      .then((d) => {
        setExplainData(d);
        setExplainLoading(false);
      })
      .catch(() => {
        setExplainLoading(false);
      });
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-border/40 bg-card/60 p-6 backdrop-blur">
        <div className="flex items-center gap-3 text-muted-foreground animate-pulse text-sm">
          <span>{kn ? "ಮುನ್ಸೂಚನಾ ಲೀಗ್ ಲೋಡ್ ಆಗುತ್ತಿದೆ..." : "Loading forecast model league..."}</span>
        </div>
      </div>
    );
  }

  if (error || !data || !data.rows) {
    return null; // Cloud or unavailable fallback
  }

  // Filter rows for selected controls
  const activeRows = data.rows.filter(
    (r) => r.category === category && r.unit === unitType && r.horizon === horizon
  );

  const winnerRow = activeRows.find((r) => r.is_winner);

  return (
    <div className="mt-8 rounded-xl border border-primary/20 bg-card/80 p-6 backdrop-blur shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/40 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
              {kn ? "ಪ್ರಯೋಗಾಲಯ ಆವೃತ್ತಿ" : "Lab Benchmark"}
            </span>
            <h3 className="text-lg font-bold tracking-tight text-foreground">
              {kn ? "ಮಾದರಿ ಲೀಗ್: ಚಾಂಪಿಯನ್ vs ಚಾಲೆಂಜ್" : "Model League: Champion vs Challenger"}
            </h3>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {kn
              ? "ಪಾಯ್ಸನ್ ಜಿಎಲ್‌ಎಂ ವಿರುದ್ಧ ಲೈಟ್‌ಜಿಬಿಎಂ (ಟ್ರೀಶ್ಯಾಪ್ ಮತ್ತು ಮಾಂಡ್ರಿಯನ್ ಕಾನ್‌ಫಾರ್ಮಲ್ ಬ್ಯಾಂಡ್‌ಗಳು)"
              : "Rigorous head-to-head backtest: Poisson GLM vs LightGBM with Mondrian split-conformal bounds and TreeSHAP"}
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Category */}
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-lg border border-border/60 bg-background px-3 py-1.5 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="ALL">{kn ? "ಎಲ್ಲಾ ಅಪರಾಧಗಳು" : "ALL CRIME"}</option>
            <option value="PROPERTY">{kn ? "ಆಸ್ತಿ ಅಪರಾಧಗಳು" : "PROPERTY"}</option>
            <option value="VIOLENT">{kn ? "ಹಿಂಸಾತ್ಮಕ" : "VIOLENT"}</option>
          </select>

          {/* Unit */}
          <select
            value={unitType}
            onChange={(e) => setUnitType(e.target.value)}
            className="rounded-lg border border-border/60 bg-background px-3 py-1.5 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="station">{kn ? "ಠಾಣೆ ಮಟ್ಟ" : "Police Station"}</option>
            <option value="beat">{kn ? "ಬೀಟ್ ಮಟ್ಟ" : "Beat"}</option>
          </select>

          {/* Horizon */}
          <select
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
            className="rounded-lg border border-border/60 bg-background px-3 py-1.5 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value={7}>{kn ? "7 ದಿನಗಳು" : "7 Days"}</option>
            <option value={28}>{kn ? "28 ದಿನಗಳು" : "28 Days"}</option>
          </select>

          <button
            onClick={openExplain}
            className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary hover:bg-primary/20 transition"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {kn ? "ಕಾರಣಗಳ ವಿವರಣೆ" : "Explain Drivers"}
          </button>
        </div>
      </div>

      {/* Winner Banner */}
      {winnerRow && (
        <div className="mt-4 flex items-center justify-between rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-sm font-bold">
              ★
            </span>
            <div>
              <div className="text-xs font-semibold text-emerald-400">
                {kn ? "ವಿಜೇತ ಮುನ್ಸೂಚನಾ ಮಾದರಿ" : "Crowned Benchmark Winner"}
              </div>
              <div className="text-sm font-bold text-foreground">
                {winnerRow.model_name}{" "}
                <span className="text-xs font-normal text-muted-foreground">
                  (PAI@5%: {winnerRow.pai5.toFixed(2)}, PEI@5%: {(winnerRow.pei5 * 100).toFixed(1)}%, {kn ? "ಕವರೇಜ್" : "Coverage"}: {(winnerRow.cover90 * 100).toFixed(1)}%)
                </span>
              </div>
            </div>
          </div>
          <div className="text-xs text-muted-foreground text-right hidden sm:block">
            {winnerRow.weeks_better} {kn ? "ವಾರಗಳಲ್ಲಿ ಉತ್ತಮ ಫಲಿತಾಂಶ" : "weeks outperformed on capture"}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="mt-5 overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-border/40 text-muted-foreground">
              <th className="py-2.5 px-3 font-semibold">{kn ? "ಮಾದರಿ" : "Model"}</th>
              <th className="py-2.5 px-3 font-semibold text-right">MAE</th>
              <th className="py-2.5 px-3 font-semibold text-right">Deviance Gain</th>
              <th className="py-2.5 px-3 font-semibold text-right">90% Band Held</th>
              <th className="py-2.5 px-3 font-semibold text-right">Top 5% Capture</th>
              <th className="py-2.5 px-3 font-semibold text-right">PAI @ 5%</th>
              <th className="py-2.5 px-3 font-semibold text-right">PEI @ 5%</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/20">
            {activeRows.map((r, i) => (
              <tr
                key={i}
                className={`transition-colors ${
                  r.is_winner ? "bg-emerald-500/5 font-semibold text-foreground" : "text-muted-foreground hover:bg-card/40"
                }`}
              >
                <td className="py-3 px-3 flex items-center gap-2">
                  {r.is_winner && <span className="text-emerald-400">★</span>}
                  <span>{r.model_name}</span>
                  {r.is_champion && (
                    <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[10px] text-sky-400">
                      Champion
                    </span>
                  )}
                  {r.is_challenger && (
                    <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-400">
                      Challenger
                    </span>
                  )}
                </td>
                <td className="py-3 px-3 text-right">{r.mae.toFixed(2)}</td>
                <td className="py-3 px-3 text-right">
                  {r.deviance_gain > 0 ? `+${(r.deviance_gain * 100).toFixed(1)}%` : `${(r.deviance_gain * 100).toFixed(1)}%`}
                </td>
                <td className="py-3 px-3 text-right">
                  <span
                    className={
                      r.cover90 >= 0.88
                        ? "text-emerald-400"
                        : r.cover90 >= 0.82
                        ? "text-amber-400"
                        : "text-rose-400"
                    }
                  >
                    {(r.cover90 * 100).toFixed(1)}%
                  </span>
                </td>
                <td className="py-3 px-3 text-right">{(r.capture5 * 100).toFixed(1)}%</td>
                <td className="py-3 px-3 text-right font-mono">{r.pai5.toFixed(2)}</td>
                <td className="py-3 px-3 text-right font-mono">{(r.pei5 * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Explain Drawer Modal */}
      {explainOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-xl border border-border/60 bg-card p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border/40 pb-4">
              <h4 className="text-base font-bold text-foreground">
                {kn ? "ಮುನ್ಸೂಚನಾ ಕಾರಣಗಳ ವಿಶ್ಲೇಷಣೆ (SHAP vs GLM)" : "Forecast Driver Attribution: TreeSHAP vs GLM"}
              </h4>
              <button
                onClick={() => setExplainOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <div className="mt-4">
              {explainLoading ? (
                <div className="py-12 text-center text-sm text-muted-foreground animate-pulse">
                  {kn ? "ಕಾರಣಗಳನ್ನು ಗಣನೆ ಮಾಡಲಾಗುತ್ತಿದೆ..." : "Computing exact SHAP and GLM multipliers..."}
                </div>
              ) : explainData ? (
                <div className="space-y-4">
                  <p className="text-xs text-muted-foreground">
                    {explainData.summary ||
                      (kn
                        ? "ಪ್ರತಿ ವೈಶಿಷ್ಟ್ಯ ಗುಂಪಿನ ಸಾಪೇಕ್ಷ ಪ್ರಭಾವವನ್ನು ಕೆಳಗೆ ಪಟ್ಟಿಮಾಡಲಾಗಿದೆ (1.0 = ಸರಾಸರಿ ಮಟ್ಟ)."
                        : "Relative driver multipliers: values > 1.0 indicate elevated risk pressure over the baseline.")}
                  </p>
                  <div className="divide-y divide-border/20 text-xs">
                    {explainData.drivers &&
                      Object.entries(explainData.drivers).map(([group, val], idx) => (
                        <div key={idx} className="flex items-center justify-between py-2">
                          <span className="capitalize font-medium text-foreground">{group}</span>
                          <span className="font-mono text-primary font-semibold">
                            {typeof val === "number" ? `${val.toFixed(2)}x` : String(val)}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-muted-foreground">
                  {kn ? "ಯಾವುದೇ ವಿವರಣೆ ಲಭ್ಯವಿಲ್ಲ." : "Driver attributions unavailable."}
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setExplainOpen(false)}
                className="rounded-lg bg-secondary px-4 py-1.5 text-xs font-semibold text-secondary-foreground hover:bg-secondary/80"
              >
                {kn ? "ಮುಚ್ಚಿ" : "Close"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
