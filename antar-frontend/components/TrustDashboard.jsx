"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, ChevronDown, ChevronRight, RefreshCw, Search, Layers } from "lucide-react";
import { fetchAPI } from "@/lib/api";
import { useLang } from "@/components/Providers";

/* ────────────────────────────────────────────────────────────────────────────
   Trace & Telemetry
   Session-first: the officer picks a conversation, sees every question asked in
   it in order, and can open any single turn to get the whole derivation —
   which template ran, which FIR rows came back, which agents fired and for how
   long, what the compliance rules said, and how the judge scored it.

   Styles are the .tlm-* rules in app/globals.css. Colour is a signal here, not
   decoration: amber and red appear only on a flag, an error or a failing score.
   ──────────────────────────────────────────────────────────────────────────── */

// What each rule id actually means - the table used to show a bare "F6".
const RULE_LABEL = {
  F1: "Asserted a fact with no rows and no citation",
  F2: "Named entity absent from the retrieved rows",
  F3: "Latency or token spike against the rolling baseline",
  F5: "Template returned 0 rows but the answer did not say so",
  F6: "AI model not reachable, so the answer was written from the records alone",
  F7: "Answer guardrail tripped",
};

const fmtMs = (ms) => (ms == null ? "—" : ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`);
const fmtNum = (n) => (n == null ? "—" : Number(n).toLocaleString("en-IN"));
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
// "2026-10-13 05:25:06" as the server wrote it, re-set as "13 Oct, 05:25:06". No timezone shift.
const when = (s) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}:\d{2}(?::\d{2})?)/.exec(String(s || ""));
  return m ? `${Number(m[3])} ${MON[Number(m[2]) - 1]} ${m[1]}, ${m[4]}` : (s || "");
};
const sevOf = (s) => (s === "high" ? "high" : s === "low" ? "low" : "med");

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
  // The audit ledger's own check, for an Admin (the route refuses anyone else, and the line is then absent).
  const [chain, setChain] = useState(null);
  useEffect(() => { fetchAPI("/api/audit/integrity").then(setChain).catch(() => setChain(null)); }, []);

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
  const flagged = m.flagged_traces || 0;
  const serious = m.high_severity_traces || 0;

  return (
    <div className="tlm">
      <div className="tlm-wrap">

        {/* ── Header ───────────────────────────────────────────────── */}
        <header className="tlm-head">
          <div>
            <h1>{kn ? "ಉತ್ತರಗಳ ಇತಿಹಾಸ" : "Answer History"}</h1>
            <p>{kn
              ? "ಪ್ರತಿ ಸೆಷನ್‌ನ ಪ್ರತಿ ಪ್ರಶ್ನೆಯ ಸಂಪೂರ್ಣ ತಾರ್ಕಿಕ ಜಾಡು"
              : "Every question asked, and how each answer was produced: the query that ran, the FIR rows it read, and the checks it passed."}</p>
          </div>
          <div className="tlm-tools">
            <Toggle on={flaggedOnly} onClick={() => setFlaggedOnly((v) => !v)} label={kn ? "ಫ್ಲ್ಯಾಗ್ ಮಾತ್ರ" : "Flagged only"} />
            <Toggle on={showHttp} onClick={() => setShowHttp((v) => !v)} label={kn ? "HTTP ಟೆಲಿಮೆಟ್ರಿ" : "Include page requests"}
                    title="Also list requests the pages made to the server, not only questions asked in Chat" />
            <button type="button" className="tlm-btn" onClick={loadDashboard} title="Read the latest figures">
              <RefreshCw size={14} className={loading ? "spin" : ""} aria-hidden="true" />
              {kn ? "ರಿಫ್ರೆಶ್" : "Refresh"}
            </button>
          </div>
        </header>

        {/* ── Figures ──────────────────────────────────────────────── */}
        <div className="tlm-kpis">
          <Kpi title={kn ? "ಸಂಭಾಷಣೆ ತಿರುವುಗಳು" : "Questions recorded"} value={fmtNum(m.total_traces)}
               sub={`${kn ? "" : "in "}${fmtNum(m.sessions)} ${kn ? "ಸೆಷನ್" : m.sessions === 1 ? "session" : "sessions"}`} />
          <Kpi title={kn ? "ಸ್ವಚ್ಛ ದರ" : "Answered with no flag"} value={`${m.clean_rate ?? 100}%`}
               sub={`${fmtNum(flagged)} ${kn ? "ಫ್ಲ್ಯಾಗ್" : "flagged"}`} tone={serious > 0 ? "bad" : flagged > 0 ? "warn" : "ok"} />
          <Kpi title={kn ? "ಹೆಚ್ಚಿನ ತೀವ್ರತೆ" : "Serious flags"} value={fmtNum(serious)}
               sub={kn ? "ನಿಯಮ ಉಲ್ಲಂಘನೆ" : "high-severity rule violations"} tone={serious > 0 ? "bad" : "ok"} />
          <Kpi title={kn ? "ಸರಾಸರಿ ಲೇಟೆನ್ಸಿ" : "Average answer time"} value={fmtMs(m.avg_latency_ms)}
               sub={kn ? `p95 ${fmtMs(m.p95_latency_ms)}` : `95% answered within ${fmtMs(m.p95_latency_ms)}`} />
          <Kpi title={kn ? "ಉಲ್ಲೇಖಗಳು" : "FIRs cited"} value={fmtNum(m.total_citations)}
               sub={`${fmtNum(m.total_rows_read)} ${kn ? "ಸಾಲುಗಳು" : "rows read"}`} />
          <Kpi title={kn ? "ಗುಣಮಟ್ಟ" : "Quality score"}
               value={m.avg_quality == null ? (kn ? "ಇನ್ನೂ ಇಲ್ಲ" : "Not scored yet") : `${m.avg_quality.toFixed(1)} / 5`}
               sub={m.judged_traces ? `${fmtNum(m.judged_traces)} ${kn ? "ಮೌಲ್ಯಮಾಪನ" : "answers scored"}` : (kn ? "ಇನ್ನೂ ಯಾವುದೂ ಅಂಕಿತವಾಗಿಲ್ಲ" : "no answer has been reviewed")}
               quiet={m.avg_quality == null} />
          <Kpi title={kn ? "ಎಂಜಿನ್" : "How answers were written"} value={`${fmtNum(m.llm_turns)} / ${fmtNum(m.offline_turns)}`}
               sub={kn ? "AI ಮಾದರಿ / ದಾಖಲೆಗಳಿಂದ ಮಾತ್ರ" : "by the AI model / from records only"} />
        </div>

        {/* Which rules fired - only when something actually did. */}
        {m.flags_by_rule?.length > 0 && (
          <div className="tlm-rules">
            <span className="lbl">{kn ? "ನಿಯಮಗಳು" : "Flags raised"}</span>
            {m.flags_by_rule.map((f) => (
              <span key={`${f.rule}-${f.severity}`} className={`tlm-rule ${sevOf(f.severity)}`}>
                <i aria-hidden="true" /><b>{f.rule}</b>
                <span>{RULE_LABEL[f.rule] || f.severity}</span>
                <em>{fmtNum(f.n)}</em>
              </span>
            ))}
          </div>
        )}

        {chain && (
          <p className={`tlm-chain ${chain.ok ? "ok" : "bad"}`}>
            <i aria-hidden="true" />
            {chain.ok
              ? `Audit ledger: ${fmtNum(chain.verified)} entries checked, none altered.`
              : `Audit ledger: the chain breaks at entry ${fmtNum(chain.broken_at_index)}. Entries after it cannot be relied on until it is reset.`}
            {chain.legacy_unverifiable > 0 && ` ${fmtNum(chain.legacy_unverifiable)} older entries predate the checkable format.`}
          </p>
        )}

        {/* ── Explainer (collapsed by default - it used to eat the fold) ── */}
        <div className="tlm-explain">
          <button type="button" onClick={() => setExplainOpen((v) => !v)} aria-expanded={explainOpen}>
            {kn ? "ಏಜೆಂಟಿಕ್ AI ಆಬ್ಸರ್ವಬಿಲಿಟಿ ಎಂದರೆ ಏನು?" : "What this page records, and why"}
            <ChevronDown size={16} className={explainOpen ? "up" : ""} aria-hidden="true" />
          </button>
          {explainOpen && (
            <div className="tlm-notes">
              <Note title={kn ? "ಇದು ಏನು" : "What is recorded"}>
                {kn ? "ಪ್ರತಿ ಪ್ರಶ್ನೆಗೆ: ಯಾವ ಟೆಂಪ್ಲೇಟ್ ಚಾಲನೆಯಾಯಿತು, ಯಾವ FIR ಸಾಲುಗಳು ಬಂದವು, ಯಾವ ಏಜೆಂಟ್‌ಗಳು ಕೆಲಸ ಮಾಡಿದವು." : "For every question: the approved query template that ran, the exact FIR rows it returned, the agents that worked on it and how long each took, and the FIRs cited in the answer."}
              </Note>
              <Note title={kn ? "ಏಕೆ ಮುಖ್ಯ" : "Why it matters"}>
                {kn ? "ಒಬ್ಬ ಅಧಿಕಾರಿ 'ನೀವು ಇದನ್ನು ಏಕೆ ಹೇಳಿದಿರಿ?' ಎಂದು ಕೇಳಬಹುದು ಮತ್ತು ಪೂರ್ಣ ಉತ್ತರ ಪಡೆಯಬಹುದು." : "An officer can ask \"why did you say that?\" and replay the answer. The same template with the same inputs always returns the same rows, so an answer can be reproduced later."}
              </Note>
              <Note title={kn ? "ನಿಯಮಗಳು" : "The checks"}>
                {kn ? "ಪ್ರತಿ ಉತ್ತರವನ್ನು ನಿಯಮಗಳ ವಿರುದ್ಧ ಪರಿಶೀಲಿಸಲಾಗುತ್ತದೆ; ಸಂಶಯಾಸ್ಪದವಾದವುಗಳನ್ನು ಜಡ್ಜ್‌ಗೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ." : "Every answer is checked against the rules below, which cost nothing to run. Flagged answers and a random 5% of the rest go to a language-model judge, which scores whether the answer is supported by the rows."}
              </Note>
              <Note title={kn ? "ನಿಯಮ ಪಟ್ಟಿ" : "What each flag means"}>
                <dl className="tlm-ruledefs">
                  {Object.entries(RULE_LABEL).map(([id, label]) => <div key={id}><dt>{id}</dt><dd>{label}</dd></div>)}
                </dl>
              </Note>
            </div>
          )}
        </div>

        {/* ── Search ───────────────────────────────────────────────── */}
        <label className="tlm-search">
          <Search size={16} aria-hidden="true" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={kn ? "ಪ್ರಶ್ನೆ ಅಥವಾ ಉತ್ತರದಲ್ಲಿ ಹುಡುಕಿ…" : "Search questions and answers…"}
            aria-label={kn ? "ಹುಡುಕಿ" : "Search questions and answers"}
          />
          {query && <button type="button" onClick={() => setQuery("")}>{kn ? "ಅಳಿಸಿ" : "Clear"}</button>}
        </label>

        {/* ── Sessions ▸ Turns ─────────────────────────────────────── */}
        <div className="tlm-cols">

          {/* Session rail */}
          <section className="tlm-panel">
            <div className="tlm-panel-h">
              <h2>{kn ? "ಸೆಷನ್‌ಗಳು" : "Sessions"}</h2>
              <span>{fmtNum(sessions.length)}</span>
            </div>
            <div className="tlm-scroll tlm-sessions">
              <SessionRow
                active={activeSession === null}
                onClick={() => { setActiveSession(null); setOpenTrace(null); }}
                title={kn ? "ಎಲ್ಲಾ ತಿರುವುಗಳು" : "All questions"}
                meta={`${recent.length} ${kn ? "ಇತ್ತೀಚಿನ" : "most recent"}`}
                icon={Layers}
              />
              {sessions.map((s) => (
                <SessionRow
                  key={s.session_id}
                  active={activeSession === s.session_id}
                  onClick={() => { setActiveSession(s.session_id); setOpenTrace(null); }}
                  title={s.last_question || s.session_id}
                  meta={`${s.turns} ${kn ? "ತಿರುವು" : s.turns === 1 ? "question" : "questions"}${s.last_at ? ` · ${when(s.last_at)}` : ""}`}
                  flagged={s.flagged}
                  id={s.session_id}
                />
              ))}
              {sessions.length === 0 && (
                <p className="tlm-empty">{kn ? "ಯಾವುದೇ ಸೆಷನ್ ಇಲ್ಲ." : "No sessions recorded yet. Ask a question in Chat to create one."}</p>
              )}
            </div>
          </section>

          {/* Turn stream */}
          <section className="tlm-panel">
            <div className="tlm-panel-h">
              <h2>{activeSession
                ? (kn ? "ಸೆಷನ್ ಮರುಪ್ಲೇ" : "Session, in order")
                : (kn ? "ಇತ್ತೀಚಿನ ತಿರುವುಗಳು" : "Recent questions")}</h2>
              {activeSession ? <code>{activeSession}</code> : <span>{fmtNum(shown.length)}</span>}
            </div>

            <div className="tlm-scroll tlm-turns">
              {turnsLoading && <p className="tlm-empty">{kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Reading the questions…"}</p>}
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
                <p className="tlm-empty">{kn ? "ಯಾವುದೇ ತಿರುವು ಸಿಗಲಿಲ್ಲ." : "No question matches the current filters."}</p>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

/* ── One turn ─────────────────────────────────────────────────────────────── */

function Turn({ t, n, kn, open, detail, onToggle }) {
  const flags = normFlags(t.flags);
  const serious = flags.some((f) => f.severity === "high") || !!t.error;
  const facts = [
    when(t.created_at),
    t.template_id && `template ${t.template_id}`,
    `${fmtNum(t.n_rows ?? 0)} ${(t.n_rows ?? 0) === 1 ? "row" : "rows"}`,
    `${fmtNum(t.n_citations ?? 0)} cited`,
    fmtMs(t.latency_ms),
    t.mode === "llm" ? (t.model || "AI model") : t.mode === "offline" ? "records only" : t.mode,
    t.lang && t.lang !== "en" && t.lang,
    (t.tokens_in || t.tokens_out) > 0 && `${fmtNum(t.tokens_in)} in, ${fmtNum(t.tokens_out)} out tokens`,
  ].filter(Boolean);

  return (
    <div className={`tlm-turn${open ? " open" : ""}${serious ? " bad" : ""}`}>
      <button type="button" className="tlm-turn-h" onClick={onToggle} aria-expanded={open}>
        <ChevronRight size={16} className="chev" aria-hidden="true" />
        <span className="main">
          <span className="q">
            {n != null && <b>{n}</b>}
            {t.question || <em>(no question recorded)</em>}
          </span>
          <span className="facts">{facts.join(" · ")}</span>
        </span>
        <span className="tags">
          {t.error && <span className="tlm-tag high">Error</span>}
          {flags.map((f, i) => (
            <span key={i} className={`tlm-tag ${sevOf(f.severity)}`} title={f.detail || RULE_LABEL[f.rule]}>{f.rule}</span>
          ))}
          {flags.length === 0 && !t.error && <span className="tlm-tag ok">No flag</span>}
          {t.quality_score != null
            ? <span className="tlm-tag" title="Quality score: how well the answer is supported by the records, out of 5">Quality {t.quality_score}</span>
            : t.judge_state === "pending" && <span className="tlm-tag" title="Waiting for the language-model judge">Judge pending</span>}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            className="tlm-detail-wrap"
          >
            <TraceDetail t={t} d={detail} kn={kn} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function TraceDetail({ d, kn }) {
  if (!d) return <p className="tlm-empty left">{kn ? "ವಿವರ ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Reading how this answer was produced…"}</p>;
  if (d.__error) return <p className="tlm-empty left err">Could not load this record: {d.__error}</p>;

  const r = d.retrieval || {};
  const cites = r.citations || [];
  const rowIds = r.row_ids || [];
  const params = r.params || {};
  const dFlags = normFlags(d.flags);

  return (
    <div className="tlm-detail">

      {/* Answer */}
      <Section title={kn ? "ಉತ್ತರ" : "Answer returned"}>
        {/* the answer as stored; its **bold** marks are shown as bold, nothing else is interpreted */}
        <pre className="tlm-answer tlm-scroll">
          {d.answer
            ? String(d.answer).split(/(\*\*[^*\n]+\*\*)/g).map((part, i) => (/^\*\*[^*\n]+\*\*$/.test(part) ? <b key={i}>{part.slice(2, -2)}</b> : part))
            : <em>(empty)</em>}
        </pre>
      </Section>

      {/* Retrieval - the anti-hallucination core */}
      <div className="tlm-two">
        <Section title={kn ? "ಪ್ರಶ್ನೆ ಟೆಂಪ್ಲೇಟ್" : "Query that ran"}>
          <KV k="Template" v={d.template_id || "—"} mono />
          <KV k="Inputs" v={Object.keys(params).length ? JSON.stringify(params) : "—"} mono />
          <KV k="Rows returned" v={fmtNum(d.n_rows)} />
          <KV k="Rows fingerprint" v={r.rows_digest || "—"} mono title="A hash of the rows returned. The same query on the same data gives the same fingerprint." />
          {rowIds.length > 0 && (
            <>
              <h4>{kn ? "ಮೂಲ FIR ಸಾಲುಗಳು" : "FIR rows it read"} ({fmtNum(rowIds.length)})</h4>
              <div className="tlm-ids tlm-scroll">{rowIds.map((id, i) => <code key={i}>{id}</code>)}</div>
            </>
          )}
        </Section>

        <Section title={kn ? "ಏಜೆಂಟ್ ಪೈಪ್‌ಲೈನ್" : "Agents that worked on it"}>
          {(d.spans || []).length === 0 && <p className="tlm-dim">{kn ? "ಯಾವುದೇ ಸ್ಪ್ಯಾನ್ ದಾಖಲಾಗಿಲ್ಲ." : "No agent step was recorded for this question."}</p>}
          {(d.spans || []).map((s, i) => (
            <div key={s.span_id || i} className="tlm-span">
              <b>{s.agent}</b>
              <div>
                <span>{s.step}</span>
                {s.out_digest && <small>{s.out_digest}</small>}
              </div>
              <time>{fmtMs(s.ms)}</time>
            </div>
          ))}
        </Section>
      </div>

      {/* Citations */}
      {cites.length > 0 && (
        <Section title={`${kn ? "ಉಲ್ಲೇಖಗಳು" : "FIRs cited"} (${fmtNum(cites.length)})`}>
          <div className="tlm-tablewrap">
            <table className="tlm-table">
              <thead><tr><th>FIR</th><th>Station</th><th>Date</th><th>Section</th></tr></thead>
              <tbody>
                {cites.slice(0, 25).map((c, i) => (
                  <tr key={i}>
                    <td className="id">{c.fir || "—"}</td>
                    <td>{c.station || "—"}</td>
                    <td className="num">{c.date || "—"}</td>
                    <td>{c.section || c.ipc || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {cites.length > 25 && <p className="tlm-dim">and {cites.length - 25} more</p>}
        </Section>
      )}

      {/* Flags */}
      {dFlags.length > 0 && (
        <Section title={kn ? "ಅನುಸರಣೆ ಫ್ಲ್ಯಾಗ್‌ಗಳು" : "Flags on this answer"}>
          {dFlags.map((f, i) => (
            <div key={i} className="tlm-flagrow">
              <span className={`tlm-tag ${sevOf(f.severity)}`}>{f.rule}</span>
              <div>
                <span>{RULE_LABEL[f.rule] || f.rule}</span>
                {f.detail && <small>{f.detail}</small>}
              </div>
              <em>{{ high: "serious", med: "to note", low: "minor" }[sevOf(f.severity)]}</em>
            </div>
          ))}
        </Section>
      )}

      {/* Judge */}
      {d.scores && (
        <Section title={kn ? "ಗುಣಮಟ್ಟ ಅಂಕಗಳು" : "Quality scores"}>
          <div className="tlm-scores">
            <Score label="Supported by the rows" v={d.scores.groundedness} />
            <Score label="Answered the question" v={d.scores.answered} />
            <Score label="Unsupported claims" v={d.scores.hallucination} invert />
            <Score label="Safety" v={d.scores.safety} />
          </div>
          <p className="tlm-dim">Scored by {d.scores.judged_by} · {d.scores.sampled ? "picked at random" : "sent because it was flagged"} · {when(d.scores.judged_at)}</p>
        </Section>
      )}

      {/* Prompt actually sent - only exists on LLM turns */}
      {(r.system_sent || r.prompt_sent) && (
        <Section title={kn ? "ಮಾದರಿಗೆ ಕಳುಹಿಸಿದ್ದು" : "Sent to the language model"}>
          {r.system_sent && <Pre label="Instructions">{r.system_sent}</Pre>}
          {r.prompt_sent && <Pre label="Question and rows">{r.prompt_sent}</Pre>}
        </Section>
      )}

      {r.prompt_withheld && (
        <p className="tlm-dim">The text sent to the language model for this answer is shown to an Admin only.</p>
      )}

      {/* Identity footer */}
      <dl className="tlm-ident">
        <Meta k="Record" v={d.trace_id} />
        {d.session_id && <Meta k="Session" v={d.session_id} />}
        <Meta k="Asked from" v={d.surface || "—"} />
        <Meta k="Written by" v={d.mode === "offline" ? "records only" : d.mode === "llm" ? "AI model" : d.mode || "—"} />
        <Meta k="Model" v={d.model || "none"} />
        {d.prompt_version && <Meta k="Prompt version" v={d.prompt_version} />}
        {d.reasoning_id && <Meta k="Reasoning" v={d.reasoning_id} />}
        {d.retries > 0 && <Meta k="Retries" v={d.retries} />}
        <Meta k="Started" v={when(d.created_at)} />
      </dl>

      {d.error && <p className="tlm-error">{d.error}</p>}
    </div>
  );
}

/* ── Small pieces ─────────────────────────────────────────────────────────── */

function Kpi({ title, value, sub, tone, quiet }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`tlm-kpi${tone ? ` ${tone}` : ""}${quiet ? " quiet" : ""}`}>
      <span className="t">{tone && <i aria-hidden="true" />}{title}</span>
      <b>{value}</b>
      {sub && <span className="s">{sub}</span>}
    </motion.div>
  );
}

function SessionRow({ active, onClick, title, meta, flagged, icon: Icon, id }) {
  return (
    <button type="button" onClick={onClick} className={`tlm-session${active ? " on" : ""}`} aria-current={active ? "true" : undefined}>
      <span className="t">
        {Icon && <Icon size={14} aria-hidden="true" />}
        <span>{title}</span>
        {flagged > 0 && <em title={`${flagged} flagged`}>{flagged}</em>}
      </span>
      <span className="m">{meta}</span>
      {id && <span className="i">{id}</span>}
    </button>
  );
}

function Section({ title, children }) {
  return (
    <section className="tlm-sec">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function KV({ k, v, mono, title }) {
  return (
    <div className="tlm-kv" title={title}>
      <span>{k}</span>
      <span className={mono ? "mono" : ""}>{v}</span>
    </div>
  );
}

function Score({ label, v, invert }) {
  if (v == null) return null;
  const pct = Math.round(v * 100);
  const good = invert ? v < 0.3 : v > 0.7;
  const tone = good ? "ok" : invert ? (v > 0.6 ? "bad" : "warn") : v < 0.4 ? "bad" : "warn";
  return (
    <div className={`tlm-score ${tone}`}>
      <span>{label}</span>
      <b>{pct}%</b>
      <i><u style={{ width: `${pct}%` }} /></i>
    </div>
  );
}

function Pre({ label, children }) {
  return (
    <div className="tlm-pre">
      <h4>{label}</h4>
      <pre className="tlm-scroll">{children}</pre>
    </div>
  );
}

function Meta({ k, v }) {
  return <div><dt>{k}</dt><dd>{v}</dd></div>;
}

function Note({ title, children }) {
  return (
    <div className="tlm-note">
      <strong>{title}</strong>
      {children}
    </div>
  );
}

function Toggle({ on, onClick, label, title }) {
  return (
    <button type="button" onClick={onClick} className={`tlm-toggle${on ? " on" : ""}`} aria-pressed={on} title={title}>
      <i aria-hidden="true" />
      {label}
    </button>
  );
}

function Splash({ kn }) {
  return (
    <div className="tlm tlm-center">
      <div className="tlm-spinner" aria-hidden="true" />
      <p>{kn ? "ಆಬ್ಸರ್ವಬಿಲಿಟಿ ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ..." : "Reading the record of questions…"}</p>
    </div>
  );
}

function Failed({ kn, error, onRetry }) {
  const disabled = /disabled|404|not found/i.test(error || "");
  return (
    <div className="tlm tlm-center">
      <AlertTriangle size={36} className="warn" aria-hidden="true" />
      <p className="big">
        {disabled
          ? (kn ? "ಆಬ್ಸರ್ವಬಿಲಿಟಿ ಆಫ್ ಆಗಿದೆ." : "Recording is switched off on this server.")
          : (kn ? "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್ ಆಫ್‌ಲೈನ್." : "This page could not reach the server.")}
      </p>
      <p>{disabled ? "Set OBS_ENABLED=true in the backend .env and restart." : error}</p>
      <button type="button" className="tlm-btn" onClick={onRetry}>{kn ? "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ" : "Try again"}</button>
    </div>
  );
}
