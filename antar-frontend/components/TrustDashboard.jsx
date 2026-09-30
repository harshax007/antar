"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity, AlertTriangle, ShieldCheck, Clock, CheckCircle, ChevronDown, ChevronRight,
  RefreshCw, MessageSquare, Database, Cpu, Search, Info, FileText, Layers, Zap
} from "lucide-react";
import { fetchAPI } from "@/lib/api";
import { useLang } from "@/components/Providers";

/* ────────────────────────────────────────────────────────────────────────────
   Trace & Telemetry
   Session-first: the officer picks a conversation, sees every question asked in
   it in order, and can open any single turn to get the whole derivation —
   which template ran, which FIR rows came back, which agents fired and for how
   long, what the compliance rules said, and how the judge scored it.
   ──────────────────────────────────────────────────────────────────────────── */

const C = {
  bg: "#03050C",
  panel: "rgba(6, 11, 24, 0.85)",
  panel2: "rgba(0, 0, 0, 0.35)",
  line: "rgba(255, 255, 255, 0.08)",
  cyan: "#22E6F0",
  text: "#F8FAFC",
  dim: "#94A3B8",
  dim2: "#64748B",
  red: "#F87171",
  amber: "#F59E0B",
  green: "#34D399",
  mono: "'JetBrains Mono', monospace",
  display: "'Chakra Petch', sans-serif",
};

const SEV = {
  high: { fg: "#F87171", bg: "rgba(239,68,68,0.15)", bd: "rgba(239,68,68,0.35)" },
  med: { fg: "#F59E0B", bg: "rgba(245,158,11,0.12)", bd: "rgba(245,158,11,0.3)" },
  low: { fg: "#94A3B8", bg: "rgba(148,163,184,0.12)", bd: "rgba(148,163,184,0.28)" },
};

// What each rule id actually means - the table used to show a bare "F6".
const RULE_LABEL = {
  F1: "Asserted a fact with no rows and no citation",
  F2: "Named entity absent from the retrieved rows",
  F3: "Latency or token spike vs. rolling baseline",
  F5: "Template returned 0 rows but the answer did not disclaim",
  F6: "LLM unavailable - answered from the offline path",
  F7: "Answer guardrail tripped",
};

const fmtMs = (ms) => (ms == null ? "—" : ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${Math.round(ms)}ms`);
const fmtNum = (n) => (n == null ? "—" : Number(n).toLocaleString());

// Flags arrive as [{rule,severity,detail}]. An older backend sends a JSON *string* of
// bare rule ids ('["F6"]'), and a backend older still sends "[null]". Normalise all three
// - a shape mismatch here used to throw and blank the whole screen.
function normFlags(raw) {
  if (!raw) return [];
  if (typeof raw === "string") {
    try { return normFlags(JSON.parse(raw)); } catch { return []; }
  }
  if (!Array.isArray(raw)) return [];
  return raw
    .filter(Boolean)
    .map((f) => (typeof f === "string" ? { rule: f, severity: "med" } : f))
    .filter((f) => f && f.rule);
}

export default function TrustDashboard() {
  const { lang } = useLang();
  const kn = lang === "kn";

  const [metrics, setMetrics] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [recent, setRecent] = useState([]);
  const [activeSession, setActiveSession] = useState(null);   // null = "All turns"
  const [turns, setTurns] = useState([]);
  const [turnsLoading, setTurnsLoading] = useState(false);
  const [openTrace, setOpenTrace] = useState(null);
  const [detail, setDetail] = useState({});                   // trace_id -> detail
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [showHttp, setShowHttp] = useState(false);
  const [explainOpen, setExplainOpen] = useState(false);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ limit: "80" });
      if (showHttp) qs.set("all_surfaces", "true");
      if (flaggedOnly) qs.set("flagged_only", "true");
      if (query.trim()) qs.set("q", query.trim());
      let res;
      try {
        res = await fetchAPI(`/trace?${qs}`);
      } catch {
        res = await fetchAPI(`/trust?${qs}`);
      }
      setMetrics(res.metrics || null);
      setSessions(res.sessions || []);
      setRecent(res.traces || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [showHttp, flaggedOnly, query]);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  // Selecting a session pulls its full ordered turn list; "All turns" reuses the
  // recent list the dashboard call already returned.
  useEffect(() => {
    let alive = true;
    if (!activeSession) { setTurns(recent); return; }
    setTurnsLoading(true);
    fetchAPI(`/api/obs/session/${encodeURIComponent(activeSession)}${showHttp ? "?all_surfaces=true" : ""}`)
      .then((d) => { if (alive) setTurns(d.turns || []); })
      .catch(() => { if (alive) setTurns([]); })
      .finally(() => { if (alive) setTurnsLoading(false); });
    return () => { alive = false; };
  }, [activeSession, recent, showHttp]);

  async function toggleTrace(traceId) {
    if (openTrace === traceId) { setOpenTrace(null); return; }
    setOpenTrace(traceId);
    if (detail[traceId]) return;
    try {
      const d = await fetchAPI(`/api/obs/trace/${encodeURIComponent(traceId)}`);
      setDetail((prev) => ({ ...prev, [traceId]: d }));
    } catch (e) {
      setDetail((prev) => ({ ...prev, [traceId]: { __error: e.message } }));
    }
  }

  const shown = useMemo(() => {
    if (!query.trim() || activeSession === null) return turns;
    const q = query.toLowerCase();
    return turns.filter((t) => (t.question || "").toLowerCase().includes(q));
  }, [turns, query, activeSession]);

  if (loading && !metrics) return <Splash kn={kn} />;
  if (error && !metrics) return <Failed kn={kn} error={error} onRetry={loadDashboard} />;

  const m = metrics || {};

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, padding: "90px 24px 60px", fontFamily: "'Inter', sans-serif" }}>
      <div style={{ maxWidth: "1480px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "20px" }}>

        {/* ── Header ───────────────────────────────────────────────── */}
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: "14px" }}>
          <div>
            <h1 style={{ fontFamily: C.display, fontSize: "28px", fontWeight: 700, color: "#fff", letterSpacing: "0.02em", margin: 0 }}>
              {kn ? "ಟ್ರೇಸ್ & ಟೆಲಿಮೆಟ್ರಿ" : "Trace & Telemetry"}
            </h1>
            <p style={{ marginTop: "5px", color: C.dim2, fontSize: "13px", margin: 0 }}>
              {kn
                ? "ಪ್ರತಿ ಸೆಷನ್‌ನ ಪ್ರತಿ ಪ್ರಶ್ನೆಯ ಸಂಪೂರ್ಣ ತಾರ್ಕಿಕ ಜಾಡು"
                : "Every question, every session - the full derivation behind each answer"}
            </p>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <Toggle on={flaggedOnly} onClick={() => setFlaggedOnly((v) => !v)} label={kn ? "ಫ್ಲ್ಯಾಗ್ ಮಾತ್ರ" : "Flagged only"} />
            <Toggle on={showHttp} onClick={() => setShowHttp((v) => !v)} label={kn ? "HTTP ಟೆಲಿಮೆಟ್ರಿ" : "Include HTTP telemetry"} />
            <button
              onClick={loadDashboard}
              title="Refresh telemetry"
              style={{ background: "rgba(10,15,30,0.8)", border: `1px solid rgba(34,230,240,0.25)`, color: C.cyan, padding: "8px 14px", borderRadius: "8px", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontFamily: C.mono }}
            >
              <RefreshCw size={14} style={loading ? { animation: "spin 1s linear infinite" } : undefined} />
              <span>{kn ? "ರಿಫ್ರೆಶ್" : "REFRESH"}</span>
            </button>
          </div>
        </div>

        {/* ── KPI strip ────────────────────────────────────────────── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(168px, 1fr))", gap: "12px" }}>
          <Kpi title={kn ? "ಸಂಭಾಷಣೆ ತಿರುವುಗಳು" : "Conversation Turns"} value={fmtNum(m.total_traces)} icon={MessageSquare}
               sub={`${fmtNum(m.sessions)} ${kn ? "ಸೆಷನ್" : "sessions"}`} />
          <Kpi title={kn ? "ಸ್ವಚ್ಛ ದರ" : "Clean Rate"} value={`${m.clean_rate ?? 100}%`} icon={ShieldCheck}
               sub={`${fmtNum(m.flagged_traces)} ${kn ? "ಫ್ಲ್ಯಾಗ್" : "flagged"}`}
               tone={m.high_severity_traces > 0 ? "alert" : m.flagged_traces > 0 ? "warn" : "ok"} />
          <Kpi title={kn ? "ಹೆಚ್ಚಿನ ತೀವ್ರತೆ" : "High Severity"} value={fmtNum(m.high_severity_traces)} icon={AlertTriangle}
               tone={m.high_severity_traces > 0 ? "alert" : "ok"} sub={kn ? "ನಿಯಮ ಉಲ್ಲಂಘನೆ" : "rule violations"} />
          <Kpi title={kn ? "ಸರಾಸರಿ ಲೇಟೆನ್ಸಿ" : "Avg Latency"} value={fmtMs(m.avg_latency_ms)} icon={Clock}
               sub={`p95 ${fmtMs(m.p95_latency_ms)}`} />
          <Kpi title={kn ? "ಉಲ್ಲೇಖಗಳು" : "Citations"} value={fmtNum(m.total_citations)} icon={FileText}
               sub={`${fmtNum(m.total_rows_read)} ${kn ? "ಸಾಲುಗಳು" : "rows read"}`} />
          <Kpi title={kn ? "ಗುಣಮಟ್ಟ" : "Judge Score"}
               value={m.avg_quality == null ? (kn ? "ಇನ್ನೂ ಇಲ್ಲ" : "Not judged") : `${m.avg_quality.toFixed(1)}/5`}
               icon={CheckCircle}
               sub={m.judged_traces ? `${fmtNum(m.judged_traces)} ${kn ? "ಮೌಲ್ಯಮಾಪನ" : "scored"}` : (kn ? "ಜಡ್ಜ್ ನಿಷ್ಕ್ರಿಯ" : "judge idle")}
               muted={m.avg_quality == null} />
          <Kpi title={kn ? "ಎಂಜಿನ್" : "Engine Mix"} value={`${fmtNum(m.llm_turns)} / ${fmtNum(m.offline_turns)}`} icon={Cpu}
               sub={kn ? "LLM / ಆಫ್‌ಲೈನ್" : "LLM / offline"} />
        </div>

        {/* Rule breakdown - only when something actually fired. */}
        {m.flags_by_rule?.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
            <span style={{ fontSize: "10.5px", fontFamily: C.mono, color: C.dim2, letterSpacing: "0.08em", textTransform: "uppercase" }}>
              {kn ? "ನಿಯಮಗಳು" : "Rules fired"}
            </span>
            {m.flags_by_rule.map((f) => {
              const s = SEV[f.severity] || SEV.low;
              return (
                <span key={`${f.rule}-${f.severity}`} title={RULE_LABEL[f.rule] || f.rule}
                      style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: s.bg, border: `1px solid ${s.bd}`, color: s.fg, borderRadius: "999px", padding: "3px 11px", fontSize: "11px", fontFamily: C.mono }}>
                  <b>{f.rule}</b>
                  <span style={{ opacity: 0.75 }}>{RULE_LABEL[f.rule] || f.severity}</span>
                  <b>×{f.n}</b>
                </span>
              );
            })}
          </div>
        )}

        {/* ── Explainer (collapsed by default - it used to eat the fold) ── */}
        <div style={{ background: C.panel, border: `1px solid ${C.line}`, borderRadius: "12px", overflow: "hidden" }}>
          <button
            onClick={() => setExplainOpen((v) => !v)}
            style={{ width: "100%", background: "none", border: "none", color: C.text, padding: "13px 18px", display: "flex", alignItems: "center", gap: "9px", cursor: "pointer", fontFamily: C.display, fontSize: "14px", fontWeight: 700, textAlign: "left" }}
          >
            <Info size={16} color={C.cyan} />
            {kn ? "ಏಜೆಂಟಿಕ್ AI ಆಬ್ಸರ್ವಬಿಲಿಟಿ ಎಂದರೆ ಏನು?" : "What is Agentic AI Observability?"}
            <ChevronDown size={15} style={{ marginLeft: "auto", transform: explainOpen ? "rotate(180deg)" : "none", transition: "transform .2s" }} />
          </button>
          {explainOpen && (
            <div style={{ padding: "0 18px 18px", color: C.dim, fontSize: "13px", lineHeight: 1.65, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "14px" }}>
              <Note title={kn ? "ಇದು ಏನು" : "WHAT IT RECORDS"}>
                {kn ? "ಪ್ರತಿ ಪ್ರಶ್ನೆಗೆ: ಯಾವ ಟೆಂಪ್ಲೇಟ್ ಚಾಲನೆಯಾಯಿತು, ಯಾವ FIR ಸಾಲುಗಳು ಬಂದವು, ಯಾವ ಏಜೆಂಟ್‌ಗಳು ಕೆಲಸ ಮಾಡಿದವು." : "For every turn: the whitelisted template that ran, the exact FIR rows it returned, the agents that fired and their timings, and the citations attached to the answer."}
              </Note>
              <Note title={kn ? "ಏಕೆ ಮುಖ್ಯ" : "WHY IT MATTERS"}>
                {kn ? "ಒಬ್ಬ ಅಧಿಕಾರಿ 'ನೀವು ಇದನ್ನು ಏಕೆ ಹೇಳಿದಿರಿ?' ಎಂದು ಕೇಳಬಹುದು ಮತ್ತು ಪೂರ್ಣ ಉತ್ತರ ಪಡೆಯಬಹುದು." : "An officer can ask \"why did you say that?\" and replay the derivation - the same template and params always return the same rows, so an answer is reproducible in court."}
              </Note>
              <Note title={kn ? "ನಿಯಮಗಳು" : "AUTOMATIC RULES"}>
                {kn ? "ಪ್ರತಿ ಉತ್ತರವನ್ನು ನಿಯಮಗಳ ವಿರುದ್ಧ ಪರಿಶೀಲಿಸಲಾಗುತ್ತದೆ; ಸಂಶಯಾಸ್ಪದವಾದವುಗಳನ್ನು ಜಡ್ಜ್‌ಗೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ." : "Every turn is checked against the F-rules below at zero cost. Flagged turns plus a 5% random sample go to an LLM judge for groundedness scoring."}
              </Note>
            </div>
          )}
        </div>

        {/* ── Search ───────────────────────────────────────────────── */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", background: C.panel, border: `1px solid ${C.line}`, borderRadius: "10px", padding: "9px 14px" }}>
          <Search size={15} color={C.dim2} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={kn ? "ಪ್ರಶ್ನೆ ಅಥವಾ ಉತ್ತರದಲ್ಲಿ ಹುಡುಕಿ…" : "Search questions and answers…"}
            style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: C.text, fontSize: "13px", fontFamily: "inherit" }}
          />
          {query && (
            <button onClick={() => setQuery("")} style={{ background: "none", border: "none", color: C.dim2, cursor: "pointer", fontSize: "12px", fontFamily: C.mono }}>
              clear
            </button>
          )}
        </div>

        {/* ── Sessions ▸ Turns ─────────────────────────────────────── */}
        <div style={{ display: "grid", gridTemplateColumns: "minmax(240px, 320px) minmax(0, 1fr)", gap: "16px", alignItems: "start" }}>

          {/* Session rail */}
          <div style={{ background: C.panel, border: `1px solid rgba(34,230,240,0.15)`, borderRadius: "12px", overflow: "hidden" }}>
            <div style={{ padding: "13px 16px", borderBottom: `1px solid ${C.line}`, background: C.panel2, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h2 style={{ fontFamily: C.display, fontSize: "14px", fontWeight: 700, margin: 0 }}>
                {kn ? "ಸೆಷನ್‌ಗಳು" : "Sessions"}
              </h2>
              <span style={{ fontSize: "11px", fontFamily: C.mono, color: C.dim2 }}>{sessions.length}</span>
            </div>
            <div style={{ maxHeight: "620px", overflowY: "auto" }}>
              <SessionRow
                active={activeSession === null}
                onClick={() => { setActiveSession(null); setOpenTrace(null); }}
                title={kn ? "ಎಲ್ಲಾ ತಿರುವುಗಳು" : "All turns"}
                meta={`${recent.length} ${kn ? "ಇತ್ತೀಚಿನ" : "most recent"}`}
                icon={Layers}
              />
              {sessions.map((s) => (
                <SessionRow
                  key={s.session_id}
                  active={activeSession === s.session_id}
                  onClick={() => { setActiveSession(s.session_id); setOpenTrace(null); }}
                  title={s.last_question || s.session_id}
                  meta={`${s.turns} ${kn ? "ತಿರುವು" : s.turns === 1 ? "turn" : "turns"} · ${s.last_at || ""}`}
                  flagged={s.flagged}
                  id={s.session_id}
                />
              ))}
              {sessions.length === 0 && (
                <div style={{ padding: "26px 16px", textAlign: "center", color: C.dim2, fontSize: "12.5px" }}>
                  {kn ? "ಯಾವುದೇ ಸೆಷನ್ ಇಲ್ಲ." : "No sessions recorded yet. Ask a question in Chat to create one."}
                </div>
              )}
            </div>
          </div>

          {/* Turn stream */}
          <div style={{ background: C.panel, border: `1px solid rgba(34,230,240,0.15)`, borderRadius: "12px", overflow: "hidden" }}>
            <div style={{ padding: "13px 18px", borderBottom: `1px solid ${C.line}`, background: C.panel2, display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px", flexWrap: "wrap" }}>
              <h2 style={{ fontFamily: C.display, fontSize: "14px", fontWeight: 700, margin: 0 }}>
                {activeSession
                  ? (kn ? "ಸೆಷನ್ ಮರುಪ್ಲೇ" : "Session replay")
                  : (kn ? "ಇತ್ತೀಚಿನ ತಿರುವುಗಳು" : "Recent turns")}
              </h2>
              {activeSession && (
                <code style={{ fontSize: "11px", fontFamily: C.mono, color: C.cyan, background: "rgba(34,230,240,0.08)", border: `1px solid rgba(34,230,240,0.2)`, padding: "2px 9px", borderRadius: "5px" }}>
                  {activeSession}
                </code>
              )}
            </div>

            <div style={{ maxHeight: "820px", overflowY: "auto" }}>
              {turnsLoading && (
                <div style={{ padding: "30px", textAlign: "center", color: C.dim2, fontSize: "12.5px", fontFamily: C.mono }}>
                  {kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Loading turns…"}
                </div>
              )}
              {!turnsLoading && shown.map((t, i) => (
                <Turn
                  key={t.trace_id}
                  t={t}
                  n={activeSession ? (t.turn_no ?? i + 1) : null}
                  kn={kn}
                  open={openTrace === t.trace_id}
                  detail={detail[t.trace_id]}
                  onToggle={() => toggleTrace(t.trace_id)}
                />
              ))}
              {!turnsLoading && shown.length === 0 && (
                <div style={{ padding: "40px 20px", textAlign: "center", color: C.dim2, fontSize: "13px" }}>
                  {kn ? "ಯಾವುದೇ ತಿರುವು ಸಿಗಲಿಲ್ಲ." : "No turns match the current filters."}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

/* ── One turn ─────────────────────────────────────────────────────────────── */

function Turn({ t, n, kn, open, detail, onToggle }) {
  const flags = normFlags(t.flags);
  const worst = flags.reduce((acc, f) => (f.severity === "high" ? "high" : acc === "high" ? "high" : f.severity === "med" ? "med" : acc), null);
  const stripe = worst ? SEV[worst].fg : "rgba(34,230,240,0.35)";

  return (
    <div style={{ borderBottom: `1px solid ${C.line}` }}>
      <button
        onClick={onToggle}
        style={{
          width: "100%", background: open ? "rgba(34,230,240,0.04)" : "transparent", border: "none",
          borderLeft: `3px solid ${stripe}`, color: C.text, textAlign: "left", cursor: "pointer",
          padding: "13px 18px", display: "flex", gap: "12px", alignItems: "flex-start", fontFamily: "inherit",
        }}
      >
        <ChevronRight size={15} color={C.dim2} style={{ marginTop: "3px", flex: "none", transform: open ? "rotate(90deg)" : "none", transition: "transform .18s" }} />
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: "9px", flexWrap: "wrap" }}>
            {n != null && (
              <span style={{ fontFamily: C.mono, fontSize: "10.5px", color: C.cyan, flex: "none" }}>#{n}</span>
            )}
            <span style={{ fontWeight: 500, fontSize: "13.5px", color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "100%" }}>
              {t.question || <em style={{ color: C.dim2 }}>(no question recorded)</em>}
            </span>
          </div>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
            <Chip mono>{t.created_at}</Chip>
            {t.template_id && <Chip tone="cyan" mono title="Whitelisted ZCQL template">{t.template_id}</Chip>}
            <Chip mono title="FIR rows returned"><Database size={10} /> {t.n_rows ?? 0} rows</Chip>
            <Chip mono title="Citations attached"><FileText size={10} /> {t.n_citations ?? 0}</Chip>
            <Chip mono title="Turn latency"><Clock size={10} /> {fmtMs(t.latency_ms)}</Chip>
            <Chip mono tone={t.mode === "llm" ? "cyan" : "dim"} title={t.model || "no model - offline path"}>
              {t.mode === "llm" ? (t.model || "llm") : t.mode}
            </Chip>
            {t.lang && t.lang !== "en" && <Chip mono>{t.lang}</Chip>}
            {(t.tokens_in || t.tokens_out) > 0 && <Chip mono>{t.tokens_in}▸{t.tokens_out} tok</Chip>}
            {t.error && <Chip tone="red" mono>error</Chip>}
            {flags.map((f, i) => (
              <Chip key={i} tone={f.severity === "high" ? "red" : "amber"} mono title={f.detail || RULE_LABEL[f.rule]}>
                {f.rule}
              </Chip>
            ))}
            {flags.length === 0 && !t.error && <Chip tone="green" mono>clean</Chip>}
            {t.quality_score != null
              ? <Chip tone="green" mono title="LLM judge groundedness ×5">judge {t.quality_score}</Chip>
              : t.judge_state === "pending" && <Chip tone="amber" mono title="Queued for the LLM judge">judge pending</Chip>}
          </div>
        </div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            style={{ overflow: "hidden", background: "rgba(2,4,10,0.92)", borderLeft: `3px solid ${stripe}` }}
          >
            <TraceDetail t={t} d={detail} kn={kn} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function TraceDetail({ t, d, kn }) {
  if (!d) {
    return <div style={{ padding: "20px 22px", color: C.dim2, fontSize: "12.5px", fontFamily: C.mono }}>{kn ? "ವಿವರ ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Loading derivation…"}</div>;
  }
  if (d.__error) {
    return <div style={{ padding: "20px 22px", color: C.red, fontSize: "12.5px" }}>Could not load trace detail: {d.__error}</div>;
  }

  const r = d.retrieval || {};
  const cites = r.citations || [];
  const rowIds = r.row_ids || [];
  const params = r.params || {};
  const dFlags = normFlags(d.flags);

  return (
    <div style={{ padding: "18px 22px 22px", display: "flex", flexDirection: "column", gap: "16px", fontSize: "12.5px" }}>

      {/* Answer */}
      <Section title={kn ? "ಉತ್ತರ" : "Answer returned"} icon={MessageSquare}>
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", color: "#D1D5DB", fontFamily: "inherit", fontSize: "12.5px", lineHeight: 1.65, maxHeight: "260px", overflowY: "auto" }}>
          {d.answer || <em style={{ color: C.dim2 }}>(empty)</em>}
        </pre>
      </Section>

      {/* Retrieval - the anti-hallucination core */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))", gap: "12px" }}>
        <Section title={kn ? "ಪ್ರಶ್ನೆ ಟೆಂಪ್ಲೇಟ್" : "Query executed"} icon={Database}>
          <KV k="Template" v={d.template_id || "—"} mono />
          <KV k="Params" v={Object.keys(params).length ? JSON.stringify(params) : "—"} mono wrap />
          <KV k="Rows returned" v={fmtNum(d.n_rows)} mono />
          <KV k="Rows digest" v={r.rows_digest || "—"} mono />
          {rowIds.length > 0 && (
            <div style={{ marginTop: "8px" }}>
              <div style={{ color: C.dim2, fontSize: "10.5px", fontFamily: C.mono, textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "5px" }}>
                {kn ? "ಮೂಲ FIR ಸಾಲುಗಳು" : "Source FIR rows"} ({rowIds.length})
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", maxHeight: "110px", overflowY: "auto" }}>
                {rowIds.map((id, i) => (
                  <code key={i} style={{ fontSize: "10.5px", fontFamily: C.mono, background: "rgba(34,230,240,0.08)", border: `1px solid rgba(34,230,240,0.2)`, color: C.cyan, padding: "2px 7px", borderRadius: "4px" }}>{id}</code>
                ))}
              </div>
            </div>
          )}
        </Section>

        <Section title={kn ? "ಏಜೆಂಟ್ ಪೈಪ್‌ಲೈನ್" : "Agent pipeline"} icon={Zap}>
          {(d.spans || []).length === 0 && <div style={{ color: C.dim2 }}>{kn ? "ಯಾವುದೇ ಸ್ಪ್ಯಾನ್ ದಾಖಲಾಗಿಲ್ಲ." : "No agent spans recorded for this turn."}</div>}
          {(d.spans || []).map((s, i) => (
            <div key={s.span_id || i} style={{ display: "flex", gap: "10px", alignItems: "flex-start", padding: "6px 0", borderBottom: i < d.spans.length - 1 ? `1px solid rgba(255,255,255,0.05)` : "none" }}>
              <span style={{ fontFamily: C.mono, fontSize: "10px", color: C.cyan, minWidth: "78px", flex: "none" }}>{s.agent}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: C.text, fontSize: "11.5px" }}>{s.step}</div>
                {s.out_digest && <div style={{ color: C.dim2, fontSize: "11px", wordBreak: "break-word" }}>{s.out_digest}</div>}
              </div>
              <span style={{ fontFamily: C.mono, fontSize: "10.5px", color: C.dim, flex: "none" }}>{fmtMs(s.ms)}</span>
            </div>
          ))}
        </Section>
      </div>

      {/* Citations */}
      {cites.length > 0 && (
        <Section title={kn ? "ಉಲ್ಲೇಖಗಳು" : "Citations"} icon={FileText}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px", minWidth: "420px" }}>
              <thead>
                <tr style={{ color: C.dim2, fontFamily: C.mono, fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.07em" }}>
                  <th style={{ textAlign: "left", padding: "5px 10px 5px 0" }}>FIR</th>
                  <th style={{ textAlign: "left", padding: "5px 10px" }}>Station</th>
                  <th style={{ textAlign: "left", padding: "5px 10px" }}>Date</th>
                  <th style={{ textAlign: "left", padding: "5px 0" }}>Section</th>
                </tr>
              </thead>
              <tbody>
                {cites.slice(0, 25).map((c, i) => (
                  <tr key={i} style={{ borderTop: `1px solid rgba(255,255,255,0.05)` }}>
                    <td style={{ padding: "5px 10px 5px 0", fontFamily: C.mono, color: C.cyan }}>{c.fir || "—"}</td>
                    <td style={{ padding: "5px 10px", color: C.dim }}>{c.station || "—"}</td>
                    <td style={{ padding: "5px 10px", color: C.dim, fontFamily: C.mono }}>{c.date || "—"}</td>
                    <td style={{ padding: "5px 0", color: C.dim }}>{c.section || c.ipc || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {cites.length > 25 && <div style={{ color: C.dim2, fontSize: "11px", marginTop: "6px" }}>+{cites.length - 25} more</div>}
          </div>
        </Section>
      )}

      {/* Flags */}
      {dFlags.length > 0 && (
        <Section title={kn ? "ಅನುಸರಣೆ ಫ್ಲ್ಯಾಗ್‌ಗಳು" : "Compliance flags"} icon={AlertTriangle}>
          {dFlags.map((f, i) => {
            const s = SEV[f.severity] || SEV.low;
            return (
              <div key={i} style={{ display: "flex", gap: "10px", alignItems: "flex-start", padding: "7px 0", borderBottom: i < dFlags.length - 1 ? `1px solid rgba(255,255,255,0.05)` : "none" }}>
                <span style={{ background: s.bg, border: `1px solid ${s.bd}`, color: s.fg, borderRadius: "4px", padding: "1px 8px", fontFamily: C.mono, fontSize: "10.5px", fontWeight: 700, flex: "none" }}>
                  {f.rule}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ color: C.text, fontSize: "12px" }}>{RULE_LABEL[f.rule] || f.rule}</div>
                  {f.detail && <div style={{ color: C.dim2, fontSize: "11.5px", marginTop: "2px" }}>{f.detail}</div>}
                </div>
                <span style={{ color: s.fg, fontFamily: C.mono, fontSize: "10px", textTransform: "uppercase", flex: "none" }}>{f.severity || ""}</span>
              </div>
            );
          })}
        </Section>
      )}

      {/* Judge */}
      {d.scores && (
        <Section title={kn ? "ಜಡ್ಜ್ ಸ್ಕೋರ್" : "LLM judge scores"} icon={CheckCircle}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "10px" }}>
            <Score label="Groundedness" v={d.scores.groundedness} />
            <Score label="Answered" v={d.scores.answered} />
            <Score label="Hallucination" v={d.scores.hallucination} invert />
            <Score label="Safety" v={d.scores.safety} />
          </div>
          <div style={{ color: C.dim2, fontSize: "11px", marginTop: "8px", fontFamily: C.mono }}>
            {d.scores.judged_by} · {d.scores.sampled ? "random sample" : "flagged"} · {d.scores.judged_at}
          </div>
        </Section>
      )}

      {/* Prompt actually sent - only exists on LLM turns */}
      {(r.system_sent || r.prompt_sent) && (
        <Section title={kn ? "ಮಾದರಿಗೆ ಕಳುಹಿಸಿದ್ದು" : "Sent to the model"} icon={Cpu}>
          {r.system_sent && <Pre label="SYSTEM">{r.system_sent}</Pre>}
          {r.prompt_sent && <Pre label="USER">{r.prompt_sent}</Pre>}
        </Section>
      )}

      {/* Identity footer */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", fontFamily: C.mono, fontSize: "10px", color: C.dim2 }}>
        <Meta>trace {d.trace_id}</Meta>
        {d.session_id && <Meta>session {d.session_id}</Meta>}
        <Meta>surface {d.surface || "—"}</Meta>
        <Meta>mode {d.mode || "—"}</Meta>
        <Meta>model {d.model || "none (offline)"}</Meta>
        {d.prompt_version && <Meta>prompt {d.prompt_version}</Meta>}
        {d.reasoning_id && <Meta>reasoning {d.reasoning_id}</Meta>}
        {d.retries > 0 && <Meta>retries {d.retries}</Meta>}
        <Meta>started {d.created_at}</Meta>
      </div>

      {d.error && (
        <div style={{ background: "rgba(239,68,68,0.1)", border: `1px solid rgba(239,68,68,0.3)`, color: C.red, borderRadius: "6px", padding: "9px 12px", fontSize: "12px" }}>
          {d.error}
        </div>
      )}
    </div>
  );
}

/* ── Small pieces ─────────────────────────────────────────────────────────── */

function Kpi({ title, value, icon: Icon, sub, tone, muted }) {
  const accent = tone === "alert" ? C.red : tone === "warn" ? C.amber : tone === "ok" ? C.green : C.cyan;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      style={{
        background: C.panel,
        border: `1px solid ${tone === "alert" ? "rgba(239,68,68,0.4)" : "rgba(34,230,240,0.18)"}`,
        borderRadius: "11px", padding: "14px 16px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
        <span style={{ fontSize: "10px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: C.dim2 }}>{title}</span>
        <Icon style={{ width: "14px", height: "14px", color: accent, flex: "none" }} />
      </div>
      <div style={{ marginTop: "8px", fontFamily: C.display, fontSize: muted ? "17px" : "23px", fontWeight: 700, color: muted ? C.dim : (tone === "alert" ? C.red : "#fff"), lineHeight: 1.15 }}>
        {value}
      </div>
      {sub && <div style={{ marginTop: "3px", fontSize: "10.5px", fontFamily: C.mono, color: C.dim2 }}>{sub}</div>}
    </motion.div>
  );
}

function SessionRow({ active, onClick, title, meta, flagged, icon: Icon, id }) {
  return (
    <button
      onClick={onClick}
      style={{
        width: "100%", textAlign: "left", cursor: "pointer", fontFamily: "inherit",
        background: active ? "rgba(34,230,240,0.09)" : "transparent",
        border: "none", borderBottom: `1px solid ${C.line}`,
        borderLeft: `3px solid ${active ? C.cyan : "transparent"}`,
        padding: "11px 14px", display: "flex", flexDirection: "column", gap: "4px", color: C.text,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
        {Icon && <Icon size={13} color={active ? C.cyan : C.dim2} style={{ flex: "none" }} />}
        <span style={{ fontSize: "12.5px", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{title}</span>
        {flagged > 0 && (
          <span style={{ background: SEV.med.bg, border: `1px solid ${SEV.med.bd}`, color: SEV.med.fg, borderRadius: "999px", padding: "0 6px", fontSize: "9.5px", fontFamily: C.mono, flex: "none" }}>
            {flagged}
          </span>
        )}
      </div>
      <span style={{ fontSize: "10.5px", fontFamily: C.mono, color: C.dim2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{meta}</span>
      {id && <span style={{ fontSize: "9.5px", fontFamily: C.mono, color: "rgba(100,116,139,0.65)", overflow: "hidden", textOverflow: "ellipsis" }}>{id}</span>}
    </button>
  );
}

function Chip({ children, tone, mono, title }) {
  const map = {
    cyan: { fg: C.cyan, bg: "rgba(34,230,240,0.1)", bd: "rgba(34,230,240,0.28)" },
    red: { fg: C.red, bg: "rgba(239,68,68,0.14)", bd: "rgba(239,68,68,0.32)" },
    amber: { fg: C.amber, bg: "rgba(245,158,11,0.12)", bd: "rgba(245,158,11,0.3)" },
    green: { fg: C.green, bg: "rgba(16,185,129,0.1)", bd: "rgba(16,185,129,0.26)" },
    dim: { fg: C.dim, bg: "rgba(148,163,184,0.08)", bd: "rgba(148,163,184,0.2)" },
  };
  const s = map[tone] || { fg: C.dim2, bg: "rgba(255,255,255,0.04)", bd: "rgba(255,255,255,0.08)" };
  return (
    <span title={title} style={{ display: "inline-flex", alignItems: "center", gap: "4px", background: s.bg, border: `1px solid ${s.bd}`, color: s.fg, borderRadius: "5px", padding: "1.5px 7px", fontSize: "10.5px", fontFamily: mono ? C.mono : "inherit", whiteSpace: "nowrap" }}>
      {children}
    </span>
  );
}

function Section({ title, icon: Icon, children }) {
  return (
    <div style={{ background: "rgba(0,0,0,0.34)", border: `1px solid rgba(255,255,255,0.07)`, borderRadius: "9px", padding: "13px 15px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "7px", marginBottom: "10px" }}>
        {Icon && <Icon size={13} color={C.cyan} />}
        <span style={{ fontSize: "10.5px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.09em", color: C.cyan, fontFamily: C.mono }}>{title}</span>
      </div>
      {children}
    </div>
  );
}

function KV({ k, v, mono, wrap }) {
  return (
    <div style={{ display: "flex", gap: "10px", padding: "3px 0", alignItems: "baseline" }}>
      <span style={{ color: C.dim2, fontSize: "11px", minWidth: "104px", flex: "none" }}>{k}</span>
      <span style={{ color: C.text, fontFamily: mono ? C.mono : "inherit", fontSize: "11.5px", wordBreak: wrap ? "break-word" : "normal", overflowWrap: wrap ? "anywhere" : "normal" }}>{v}</span>
    </div>
  );
}

function Score({ label, v, invert }) {
  if (v == null) return null;
  const pct = Math.round(v * 100);
  const good = invert ? v < 0.3 : v > 0.7;
  const col = good ? C.green : invert ? (v > 0.6 ? C.red : C.amber) : v < 0.4 ? C.red : C.amber;
  return (
    <div>
      <div style={{ fontSize: "10px", color: C.dim2, textTransform: "uppercase", letterSpacing: "0.06em", fontFamily: C.mono }}>{label}</div>
      <div style={{ fontFamily: C.display, fontSize: "18px", fontWeight: 700, color: col, lineHeight: 1.2 }}>{pct}%</div>
      <div style={{ height: "3px", background: "rgba(255,255,255,0.07)", borderRadius: "2px", marginTop: "4px", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: col }} />
      </div>
    </div>
  );
}

function Pre({ label, children }) {
  return (
    <div style={{ marginBottom: "8px" }}>
      <div style={{ fontSize: "9.5px", fontFamily: C.mono, color: C.dim2, letterSpacing: "0.09em", marginBottom: "4px" }}>{label}</div>
      <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", background: "rgba(0,0,0,0.4)", border: `1px solid rgba(255,255,255,0.06)`, borderRadius: "5px", padding: "9px 11px", color: C.dim, fontFamily: C.mono, fontSize: "11px", lineHeight: 1.55, maxHeight: "200px", overflowY: "auto" }}>
        {children}
      </pre>
    </div>
  );
}

function Meta({ children }) {
  return <span style={{ background: "rgba(255,255,255,0.045)", border: `1px solid rgba(255,255,255,0.07)`, borderRadius: "4px", padding: "2px 7px" }}>{children}</span>;
}

function Note({ title, children }) {
  return (
    <div style={{ background: "rgba(0,0,0,0.3)", padding: "13px 15px", borderRadius: "8px", border: `1px solid rgba(255,255,255,0.05)` }}>
      <strong style={{ color: "#E2E8F0", fontSize: "10.5px", fontFamily: C.mono, letterSpacing: "0.06em", display: "block", marginBottom: "6px" }}>{title}</strong>
      {children}
    </div>
  );
}

function Toggle({ on, onClick, label }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: on ? "rgba(34,230,240,0.12)" : "rgba(10,15,30,0.8)",
        border: `1px solid ${on ? "rgba(34,230,240,0.45)" : "rgba(255,255,255,0.1)"}`,
        color: on ? C.cyan : C.dim2,
        padding: "7px 12px", borderRadius: "8px", cursor: "pointer", fontSize: "11.5px", fontFamily: C.mono,
        display: "flex", alignItems: "center", gap: "6px",
      }}
    >
      <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: on ? C.cyan : "rgba(148,163,184,0.4)", flex: "none" }} />
      {label}
    </button>
  );
}

function Splash({ kn }) {
  return (
    <div style={{ minHeight: "100vh", background: C.bg, display: "flex", alignItems: "center", justifyContent: "center", paddingTop: "80px" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
        <div style={{ width: "32px", height: "32px", borderRadius: "50%", border: `2px solid rgba(34,230,240,0.2)`, borderTopColor: C.cyan, animation: "spin 1s linear infinite" }} />
        <span style={{ fontFamily: C.mono, fontSize: "11px", color: C.cyan }}>
          {kn ? "ಆಬ್ಸರ್ವಬಿಲಿಟಿ ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ..." : "Loading AI Observability Telemetry..."}
        </span>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function Failed({ kn, error, onRetry }) {
  const disabled = /disabled|404|not found/i.test(error || "");
  return (
    <div style={{ minHeight: "100vh", background: C.bg, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "14px", paddingTop: "80px", color: C.dim, textAlign: "center", padding: "80px 24px 0" }}>
      <AlertTriangle style={{ width: "44px", height: "44px", color: C.red }} />
      <p style={{ fontSize: "14px", margin: 0 }}>
        {disabled
          ? (kn ? "ಆಬ್ಸರ್ವಬಿಲಿಟಿ ಆಫ್ ಆಗಿದೆ." : "Observability is switched off on this backend.")
          : (kn ? "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್ ಆಫ್‌ಲೈನ್." : "Telemetry dashboard offline.")}
      </p>
      <p style={{ fontSize: "12px", color: C.dim2, margin: 0, fontFamily: C.mono, maxWidth: "520px" }}>
        {disabled ? "Set OBS_ENABLED=true in the backend .env and restart." : error}
      </p>
      <button onClick={onRetry} style={{ background: "rgba(34,230,240,0.1)", border: `1px solid rgba(34,230,240,0.3)`, color: C.cyan, padding: "8px 16px", borderRadius: "6px", cursor: "pointer", fontFamily: C.display, fontSize: "12px", fontWeight: 700 }}>
        {kn ? "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ" : "RETRY CONNECTION"}
      </button>
    </div>
  );
}
