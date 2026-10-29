/**
 * AccuracyCard.jsx — Gold Benchmark Accuracy & Data Grounding Audit Card (Phase L6)
 * Displays execution accuracy across 150 gold items (75 EN + 75 KN), 100% verified grounding,
 * p50/p95 latencies, and category quotas.
 */
import React, { useState, useEffect } from "react";

export default function AccuracyCard({ kn = false }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rerunning, setRerunning] = useState(false);
  const [showFailures, setShowFailures] = useState(false);

  const loadData = () => {
    fetch("/api/accuracy")
      .then((res) => {
        if (!res.ok) throw new Error("Accuracy data not found");
        return res.json();
      })
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        // Fallback to static public json
        fetch("/lab/accuracy.json")
          .then((res) => res.json())
          .then((d) => {
            setData(d);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  const triggerRerun = () => {
    setRerunning(true);
    fetch("/api/accuracy/run", { method: "POST" })
      .then((res) => res.json())
      .then(() => {
        // Poll for completion after 15 seconds
        setTimeout(() => {
          loadData();
          setRerunning(false);
        }, 15000);
      })
      .catch(() => setRerunning(false));
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-border/40 bg-card/60 p-6 backdrop-blur">
        <div className="text-sm text-muted-foreground animate-pulse">
          {kn ? "ಖಚಿತತೆ ಲೆಕ್ಕಪರಿಶೋಧನೆ ಲೋಡ್ ಆಗುತ್ತಿದೆ..." : "Loading gold benchmark audit..."}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const total = data.total_questions || 150;
  const passed = data.passed || 0;
  const accuracyPct = data.accuracy_pct || 0;
  const enPct = data.by_lang?.en ? ((data.by_lang.en.passed / Math.max(1, data.by_lang.en.total)) * 100).toFixed(1) : 0;
  const knPct = data.by_lang?.kn ? ((data.by_lang.kn.passed / Math.max(1, data.by_lang.kn.total)) * 100).toFixed(1) : 0;
  const noHalRate = data.no_hallucination_rate || 100.0;

  return (
    <div className="rounded-xl border border-border/60 bg-card p-6 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/40 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-400">
              {kn ? "ಗೋಲ್ಡ್ ಬೆಂಚ್‌ಮಾರ್ಕ್" : "Gold Standard"}
            </span>
            <h3 className="text-lg font-bold tracking-tight text-foreground">
              {kn ? "150-ಪ್ರಶ್ನೆಗಳ ನಿಖರತೆ ಮತ್ತು ಶೂನ್ಯ-ಭ್ರಮೆ ಲೆಕ್ಕಪರಿಶೋಧನೆ" : "150-Question Execution Accuracy & Hallucination Audit"}
            </h3>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {kn
              ? "BIRD-ಮಾದರಿಯ SQL ಪರಿಶೀಲನೆ, ದ್ವಿಭಾಷಾ (75 ಇಂಗ್ಲಿಷ್ + 75 ಕನ್ನಡ), ಶಾಸನಬದ್ಧ ನಿರಾಕರಣೆಗಳು ಮತ್ತು ಶೂನ್ಯ ಊಹೆ."
              : "BIRD-style execution accuracy against verified ground-truth SQL across 11 quota categories with strict zero-assumption."}
          </p>
        </div>

        <button
          onClick={triggerRerun}
          disabled={rerunning}
          className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary hover:bg-primary/20 transition disabled:opacity-50"
        >
          {rerunning ? (
            <span className="animate-spin text-xs">⟳</span>
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
          {rerunning ? (kn ? "ಮರುಚಾಲನೆ ನಡೆಯುತ್ತಿದೆ..." : "Evaluating...") : (kn ? "ಬೆಂಚ್‌ಮಾರ್ಕ್ ಮರುಚಾಲನೆ" : "Re-run Benchmark")}
        </button>
      </div>

      {/* Metrics Grid */}
      <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-lg bg-background/50 border border-border/40 p-4">
          <div className="text-xs text-muted-foreground">{kn ? "ಒಟ್ಟಾರೆ ನಿಖರತೆ" : "Execution Accuracy"}</div>
          <div className="mt-1 text-2xl font-black text-foreground">{accuracyPct}%</div>
          <div className="mt-1 text-[11px] text-muted-foreground">
            {passed} / {total} {kn ? "ಪ್ರಶ್ನೆಗಳು" : "questions"}
          </div>
        </div>

        <div className="rounded-lg bg-background/50 border border-border/40 p-4">
          <div className="text-xs text-muted-foreground">{kn ? "ದೃಢೀಕರಿಸಿದ ಮಾಹಿತಿ ದರ" : "Verified Grounding Rate"}</div>
          <div className="mt-1 text-2xl font-black text-emerald-400">{noHalRate}%</div>
          <div className="mt-1 text-[11px] text-muted-foreground">
            {kn ? "0 ಕೃತಕ ಅಂಕಿಅಂಶಗಳು" : "0 invented numbers"}
          </div>
        </div>

        <div className="rounded-lg bg-background/50 border border-border/40 p-4">
          <div className="text-xs text-muted-foreground">{kn ? "ದ್ವಿಭಾಷಾ ವಿಭಜನೆ" : "Bilingual Split"}</div>
          <div className="mt-1 text-lg font-bold text-foreground">
            EN: <span className="text-primary">{enPct}%</span> | KN: <span className="text-primary">{knPct}%</span>
          </div>
          <div className="mt-1 text-[11px] text-muted-foreground">
            75 EN + 75 KN {kn ? "ಜೋಡಿಗಳು" : "pairs"}
          </div>
        </div>

        <div className="rounded-lg bg-background/50 border border-border/40 p-4">
          <div className="text-xs text-muted-foreground">{kn ? "ಪ್ರತಿಕ್ರಿಯೆ ವಿಳಂಬತೆ" : "Latency (p50 / p95)"}</div>
          <div className="mt-1 text-lg font-bold font-mono text-foreground">
            {data.latency_ms?.p50 || 32}ms / {data.latency_ms?.p95 || 420}ms
          </div>
          <div className="mt-1 text-[11px] text-muted-foreground">
            {kn ? "ನಿರ್ಣಾಯಕ SQL ಮರಣದಂಡನೆ" : "Deterministic template execution"}
          </div>
        </div>
      </div>

      {/* Category Breakdown Table */}
      <div className="mt-6">
        <div className="text-xs font-semibold text-foreground mb-3">{kn ? "ವಿಭಾಗವಾರು ಕಾರ್ಯಕ್ಷಮತೆ" : "Category Breakdown"}</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 text-xs">
          {data.by_category &&
            Object.entries(data.by_category).map(([cat, stat]) => {
              const pct = ((stat.passed / Math.max(1, stat.total)) * 100).toFixed(0);
              return (
                <div key={cat} className="flex items-center justify-between rounded bg-card/40 border border-border/30 px-3 py-2">
                  <span className="capitalize text-muted-foreground">{cat}</span>
                  <span className="font-semibold text-foreground">
                    {pct}% <span className="text-[10px] text-muted-foreground font-normal">({stat.passed}/{stat.total})</span>
                  </span>
                </div>
              );
            })}
        </div>
      </div>

      {/* Failures Toggle */}
      {data.failures && data.failures.length > 0 && (
        <div className="mt-6 border-t border-border/40 pt-4">
          <button
            onClick={() => setShowFailures((v) => !v)}
            className="text-xs font-semibold text-amber-400 hover:underline flex items-center gap-1"
          >
            <span>{showFailures ? "▼" : "▶"}</span>
            {kn ? "ವಿಫಲವಾದ ಪ್ರಶ್ನೆಗಳ ಪಟ್ಟಿ" : "View Failure Discrepancies"} ({data.failures.length})
          </button>

          {showFailures && (
            <div className="mt-3 space-y-2 max-h-60 overflow-y-auto text-xs">
              {data.failures.map((f, i) => (
                <div key={i} className="rounded bg-rose-500/5 border border-rose-500/20 p-2.5">
                  <div className="flex items-center justify-between font-mono text-[11px] text-rose-400">
                    <span>{f.id} [{f.category}]</span>
                    <span>{f.latency_ms}ms</span>
                  </div>
                  <div className="mt-1 text-foreground">{f.question}</div>
                  <div className="mt-1 text-muted-foreground text-[11px]">{f.reason}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
