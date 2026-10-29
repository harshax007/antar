"use client";

// Human-in-the-loop approvals queue.
//   Approver (U-9001): reviews and decides - approve / reject, with a required reason.
//   Operations (U-7001): sees the status of every request and can withdraw its own.
// All rules (separation of duties, payload integrity, expiry) are enforced server-side in
// app/core/hitl.py; this screen only presents them.

import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchAPI } from "@/lib/api";
import { readSession, isApprover, verifyOfficer, readApproverSession, saveApproverSession, clearApproverSession, APPROVER_ID } from "@/lib/auth";
import { useLang } from "@/components/Providers";
import "@/components/editorial-approvals.css";
import AccountSidebar from "@/components/AccountSidebar";
import {
  ShieldCheck, ShieldAlert, Clock, CheckCircle2, XCircle, Undo2, Siren, Eye, Fingerprint,
  RefreshCw, Inbox,
} from "lucide-react";

const POLL_MS = 6000;

function ago(sec, now, kn) {
  const d = Math.max(0, Math.round(now / 1000 - sec));
  if (d < 60) return kn ? "ಈಗಷ್ಟೇ" : "just now";
  if (d < 3600) return kn ? `${Math.floor(d / 60)} ನಿ ಹಿಂದೆ` : `${Math.floor(d / 60)}m ago`;
  if (d < 86400) return kn ? `${Math.floor(d / 3600)} ಗಂ ಹಿಂದೆ` : `${Math.floor(d / 3600)}h ago`;
  return kn ? `${Math.floor(d / 86400)} ದಿ ಹಿಂದೆ` : `${Math.floor(d / 86400)}d ago`;
}

function countdown(sec, now) {
  const d = Math.max(0, Math.round(sec - now / 1000));
  const h = Math.floor(d / 3600), m = Math.floor((d % 3600) / 60);
  return { text: h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m ${String(d % 60).padStart(2, "0")}s`, urgent: d < 3600 };
}

const FIELD_LABELS = {
  zone: ["Zone", "ವಲಯ"], units: ["Units", "ಘಟಕಗಳು"], shift: ["Shift", "ಪಾಳಿ"], duration_hours: ["Duration", "ಅವಧಿ"],
  crime_focus: ["Crime focus", "ಅಪರಾಧ ಗಮನ"], watch_type: ["Watch type", "ಪ್ರಕಾರ"], target: ["Target", "ಗುರಿ"], label: ["Label", "ಲೇಬಲ್"],
};

function fieldValue(k, v) {
  if (k === "duration_hours") return `${v} h`;
  return String(v);
}

const STATUS_TONE = { EXECUTED: "ok", APPROVED: "ok", REJECTED: "bad", FAILED: "bad", WITHDRAWN: "muted", EXPIRED: "muted", PENDING: "warn" };

export default function ApprovalsPage() {
  const { lang } = useLang();
  const kn = lang === "kn";
  const [session, setSession] = useState(null);
  const [tab, setTab] = useState("pending");
  const [items, setItems] = useState(null);
  const [stats, setStats] = useState(null);
  const [now, setNow] = useState(() => Date.now());
  const [reasons, setReasons] = useState({});
  const [busy, setBusy] = useState({});
  const [errors, setErrors] = useState({});
  const [flash, setFlash] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const [approverSession, setApproverSession] = useState(null);   // the supervising officer, signed in on this page
  useEffect(() => {
    setSession(readSession());
    const a = readApproverSession();
    if (isApprover(a)) setApproverSession(a); else if (a) clearApproverSession();
  }, []);
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);

  // Who decides: the tab's own officer if they are an approver, else the supervising
  // officer who signed in on this page. Approve / reject go out with that officer's token.
  const acting = isApprover(session) ? session : (isApprover(approverSession) ? approverSession : null);
  const approver = !!acting;
  const me = acting?.officer || session?.officer;
  const asApprover = acting && acting !== session
    ? { Authorization: `Bearer ${acting.token}`, "X-Role": acting.role, "X-Officer": acting.officer } : undefined;

  function signOutApprover() {
    clearApproverSession();
    setApproverSession(null);
  }

  const load = useCallback(async () => {
    try {
      const status = tab === "pending" ? "pending" : "decided";
      const [q, s] = await Promise.all([
        fetchAPI(`/api/hitl/queue?status=${status}&limit=100`, { headers: asApprover }),
        fetchAPI("/api/hitl/stats", { headers: asApprover }),
      ]);
      setItems(q.items || []);
      setStats(s);
      setLoadError(null);
      window.dispatchEvent(new CustomEvent("antar-hitl", { detail: s }));
    } catch (err) {
      setLoadError(err.message || "Could not reach the approvals service.");
      setItems((prev) => prev ?? []);
    }
  }, [tab, acting?.token]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setItems(null);
    load();
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [load]);

  async function decide(a, verb) {
    const reason = (reasons[a.action_id] || "").trim();
    setBusy((b) => ({ ...b, [a.action_id]: verb }));
    setErrors((e) => ({ ...e, [a.action_id]: null }));
    try {
      const body = verb === "approve" ? { reason, payload_hash: a.payload_hash } : { reason };
      const res = await fetchAPI(`/api/hitl/${a.action_id}/${verb}`, {
        method: "POST", body: JSON.stringify(body), headers: verb === "withdraw" ? undefined : asApprover,
      });
      const msg = {
        approve: res.status === "EXECUTED" ? (kn ? "ಅನುಮೋದಿಸಲಾಗಿದೆ ಮತ್ತು ಜಾರಿಗೊಳಿಸಲಾಗಿದೆ" : "Approved and executed")
          : res.status === "FAILED" ? (kn ? "ಅನುಮೋದಿಸಲಾಗಿದೆ, ಆದರೆ ಜಾರಿ ವಿಫಲ" : "Approved, but execution failed")
          : (kn ? "ಅನುಮೋದಿಸಲಾಗಿದೆ" : "Approved"),
        reject: kn ? "ತಿರಸ್ಕರಿಸಲಾಗಿದೆ" : "Rejected",
        withdraw: kn ? "ಹಿಂಪಡೆಯಲಾಗಿದೆ" : "Withdrawn",
      }[verb];
      setFlash({ tone: res.status === "FAILED" ? "bad" : verb === "approve" ? "ok" : "muted", text: `${msg} · ${res.title}` });
      setTimeout(() => setFlash(null), 5000);
      setReasons((r) => ({ ...r, [a.action_id]: "" }));
      load();
    } catch (err) {
      if (err.status === 401 && asApprover) signOutApprover();   // the approver's sign-in expired
      setErrors((e) => ({ ...e, [a.action_id]: err.message }));
      if (err.detail?.error === "stale_review" || err.detail?.error === "not_pending") load();
    } finally {
      setBusy((b) => ({ ...b, [a.action_id]: null }));
    }
  }

  const pendingN = stats?.pending ?? 0;
  const headline = useMemo(() => approver
    ? (kn ? "ನಿಮ್ಮ ನಿರ್ಧಾರಕ್ಕಾಗಿ ಕಾಯುತ್ತಿರುವ ಕ್ರಮಗಳು" : "Actions awaiting your decision")
    : (kn ? "ನಿಮ್ಮ ವಿನಂತಿಗಳ ಸ್ಥಿತಿ" : "Status of requested actions"), [approver, kn]);

  return (
    <div className="ac-page">
      <AccountSidebar activeSection="approvals" hitlBadge={pendingN} />
      <div className="ac-main ap-page" style={{ padding: "var(--sp-8) var(--sp-6) var(--sp-10)", overflowY: "auto" }}>
        <div className="ap-wrap">
        <header className="ap-head">
          <div className="ap-hero">
            <p className="ap-kicker">{kn ? "ಅಧಿಕಾರಿ ನಿರ್ಧಾರದ ಸರಪಳಿಯಲ್ಲಿ · ಎರಡನೇ ಅಧಿಕಾರಿಯ ಅನುಮೋದನೆ" : "Officer in the loop · two-person approval"}</p>
            <h1>{approver
              ? (pendingN > 0
                  ? (kn ? <>ನೀವೇ ನಿರ್ಧಾರಕರು: <em>{pendingN}</em> ಕ್ರಮ ಕಾಯುತ್ತಿದೆ.</> : <>Officer in the loop: <em>{pendingN} {pendingN === 1 ? "action" : "actions"}</em> need your decision.</>)
                  : (kn ? "ಅಧಿಕಾರಿ ನಿರ್ಧಾರದ ಸರಪಳಿಯಲ್ಲಿ. ಈಗ ಏನೂ ಬಾಕಿ ಇಲ್ಲ." : "Officer in the loop. Nothing is waiting for you right now."))
              : (kn ? <>ಅಧಿಕಾರಿ ನಿರ್ಧಾರದ ಸರಪಳಿಯಲ್ಲಿ: <em>ಎರಡನೇ ಅಧಿಕಾರಿಗಾಗಿ</em> ಕಾಯುತ್ತಿರುವ ಕ್ರಮಗಳು</> : <>Officer in the loop: actions waiting for <em>a second officer</em></>)}</h1>
            <p>{kn
              ? "ಅಧಿಕಾರಿಯ ಅನುಮೋದನೆಯಿಲ್ಲದೆ ಏನೂ ಜಾರಿಯಾಗುವುದಿಲ್ಲ. ಗಸ್ತು ಮರುನಿಯೋಜನೆ ಮತ್ತು ವೀಕ್ಷಣಾ ಪಟ್ಟಿ ನವೀಕರಣಗಳಿಗೆ ಸ್ವತಂತ್ರ ಮೇಲ್ವಿಚಾರಕ ಅಧಿಕಾರಿಯ ಲಿಖಿತ ಸಹಿ ಅಗತ್ಯ."
              : "Nothing executes without an officer's approval. Patrol redeployments and watchlist updates require written sign-off from an independent supervising officer."}</p>
            <div className="ap-next">
              {approver && pendingN > 0 && (
                <button type="button" className="ui-btn ui-btn--primary ap-cta" onClick={() => { setTab("pending"); setTimeout(() => { try { document.querySelector(".ap-list")?.scrollIntoView({ behavior: "smooth", block: "start" }); } catch {} }, 60); }}>
                  {kn ? "ಮೊದಲ ವಿನಂತಿ ನೋಡಿ" : "Review the first request"} <span aria-hidden="true">↓</span>
                </button>
              )}
              <span>{approver
                ? (pendingN > 0 ? (kn ? "ಕಾರಣ ಬರೆಯಿರಿ, ನಂತರ ಅನುಮೋದಿಸಿ ಅಥವಾ ತಿರಸ್ಕರಿಸಿ. ನೀವು ಸಲ್ಲಿಸಿದುದನ್ನು ನೀವೇ ನಿರ್ಧರಿಸಲಾಗದು." : "Write a reason, then approve or reject. You cannot decide a request you filed yourself.")
                    : (kn ? "ಹೊಸ ವಿನಂತಿಗಳು ಇಲ್ಲಿ ತಕ್ಷಣ ಕಾಣಿಸುತ್ತವೆ." : "New requests appear here as soon as they are filed."))
                : (kn ? "ಬಾಕಿ ಇರುವ ಕ್ರಮಗಳನ್ನು ನಿರ್ಧರಿಸಲು ಮೇಲ್ವಿಚಾರಕ ಅಧಿಕಾರಿಯಾಗಿ ಸೈನ್ ಇನ್ ಮಾಡಿ." : "Sign in below with supervisor credentials to review and decide pending requests.")}</span>
            </div>
          </div>
          <div className="ap-identity">
            <span className={`ap-role ${approver ? "approver" : "ops"}`}>{approver ? (kn ? "ಅನುಮೋದಕ" : "APPROVER") : (kn ? "ಕಾರ್ಯಾಚರಣೆ" : "OPERATIONS")}</span>
            <code>{me || "—"}</code>
            {approverSession && acting === approverSession && (
              <button type="button" className="ap-signout" onClick={signOutApprover}>
                {kn ? "ಅನುಮೋದಕ ನಿರ್ಗಮನ" : "Approver sign out"}
              </button>
            )}
          </div>
        </header>

        {!approver && session && (
          <ApproverSignIn kn={kn} onSignedIn={(s) => { saveApproverSession(s); setApproverSession(s); }} />
        )}

        {approver && (
          <>
            <div className="ap-stats">
          <div><b>{stats?.pending ?? "–"}</b><span>{kn ? "ಬಾಕಿ" : "pending"}</span></div>
          <div className={stats?.pending_high_risk ? "hot" : ""}><b>{stats?.pending_high_risk ?? "–"}</b><span>{kn ? "ಹೆಚ್ಚಿನ ಅಪಾಯ" : "high risk"}</span></div>
          <div className={stats?.expiring_within_2h ? "warn" : ""}><b>{stats?.expiring_within_2h ?? "–"}</b><span>{kn ? "2 ಗಂಟೆಯಲ್ಲಿ ಅವಧಿ ಮುಗಿಯುತ್ತದೆ" : "expiring < 2h"}</span></div>
          <div><b>{stats?.by_status?.EXECUTED ?? "–"}</b><span>{kn ? "ಜಾರಿಗೊಳಿಸಲಾಗಿದೆ" : "carried out"}</span></div>
        </div>

        <div className="ap-toolbar">
          <div className="ap-tabs" role="tablist">
            {[["pending", kn ? "ಬಾಕಿ" : "Pending"], ["history", kn ? "ಇತಿಹಾಸ" : "History"]].map(([k, l]) => (
              <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>
            ))}
          </div>
          <button className="ap-refresh" onClick={load} title={kn ? "ನವೀಕರಿಸಿ" : "Refresh"}><RefreshCw size={13} /></button>
        </div>

        {flash && <div className={`ap-flash ${flash.tone}`} role="status">{flash.text}</div>}
        {loadError && <div className="ap-flash bad" role="alert">{loadError}</div>}

        {items === null ? (
          <div className="ap-empty"><div className="signal-pulse" style={{ width: 160 }} /></div>
        ) : items.length === 0 ? (
          <div className="ap-empty">
            <Inbox size={28} aria-hidden="true" />
            <b>{tab === "pending" ? (kn ? "ಬಾಕಿ ಇರುವ ಕ್ರಮಗಳಿಲ್ಲ" : "Nothing awaiting a decision") : (kn ? "ಇನ್ನೂ ನಿರ್ಧಾರಗಳಿಲ್ಲ" : "No decisions yet")}</b>
            <span>{tab === "pending"
              ? (kn ? "ಗಸ್ತು ನಿಯೋಜನೆ ಮತ್ತು ವೀಕ್ಷಣಾ ಪಟ್ಟಿ ವಿನಂತಿಗಳು ಇಲ್ಲಿ ಕಾಣಿಸುತ್ತವೆ." : "Patrol deployments and watchlist requests appear here as soon as they are filed.")
              : (kn ? "ಅನುಮೋದಿತ, ತಿರಸ್ಕೃತ ಮತ್ತು ಅವಧಿ ಮುಗಿದ ಕ್ರಮಗಳು ಇಲ್ಲಿ ದಾಖಲಾಗುತ್ತವೆ." : "Approved, rejected, withdrawn and expired actions are kept here.")}</span>
          </div>
        ) : (
          <div className="ap-list">
            {items.map((a) => tab === "pending"
              ? <PendingCard key={a.action_id} a={a} kn={kn} now={now} me={me} approver={approver}
                  reason={reasons[a.action_id] || ""} setReason={(v) => setReasons((r) => ({ ...r, [a.action_id]: v }))}
                  busy={busy[a.action_id]} error={errors[a.action_id]} decide={decide} />
              : <HistoryCard key={a.action_id} a={a} kn={kn} now={now} />)}
          </div>
        )}
          </>
        )}
        </div>
      </div>
    </div>
  );
}

function Badges({ a, kn }) {
  const c = a.compliance || {};
  return (
    <div className="ap-badges">
      <span className={`ap-risk ${a.risk}`}>{a.risk === "high" ? <Siren size={11} /> : <Eye size={11} />} {a.risk.toUpperCase()} {kn ? "ಅಪಾಯ" : "RISK"}</span>
      <span className="ap-type">{a.type_label}</span>
      <span className={`ap-chip ${a.integrity_ok ? "ok" : "bad"}`} title={a.payload_hash}>
        <Fingerprint size={11} /> {a.integrity_ok ? (kn ? "ಅಖಂಡ" : "Integrity verified") : (kn ? "ಬದಲಾಯಿಸಲಾಗಿದೆ" : "Integrity FAILED")}
      </span>
      {c.status && (
        <span className={`ap-chip ${c.status === "APPROVED" ? "ok" : c.status === "FLAGGED" ? "warn" : "muted"}`} title={c.explanation || ""}>
          {c.status === "FLAGGED" ? <ShieldAlert size={11} /> : <ShieldCheck size={11} />} Vigil · {c.status}
        </span>
      )}
      <code className="ap-id">{a.action_id}</code>
    </div>
  );
}

// The supervising officer signs in here to decide. A form the browser recognises as a
// sign-in (username + current-password), so a saved password can be filled in by the
// browser; "Fill demo approver" fills the demo account when this build carries one.
function ApproverSignIn({ kn, onSignedIn }) {
  const [id, setId] = useState(APPROVER_ID);
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (!id.trim() || !pw) { setErr(kn ? "ಐಡಿ ಮತ್ತು ಪಾಸ್‌ವರ್ಡ್ ನಮೂದಿಸಿ." : "Enter the approver's ID and password."); return; }
    setBusy(true); setErr("");
    try {
      const s = await verifyOfficer(id, pw);
      if (!isApprover(s)) {
        setErr(kn ? "ಈ ಖಾತೆ ಅನುಮೋದಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ಮೇಲ್ವಿಚಾರಕ ಅಧಿಕಾರಿಯ ಖಾತೆ ಬಳಸಿ." : "This account cannot approve. Use a supervising officer's account.");
        return;
      }
      setPw("");
      onSignedIn(s);
    } catch (e2) {
      setErr(e2.status === 401 ? (kn ? "ಐಡಿ ಅಥವಾ ಪಾಸ್‌ವರ್ಡ್ ತಪ್ಪಾಗಿದೆ." : "ID or password is incorrect.")
           : e2.status === 429 ? (kn ? "ಹಲವು ಪ್ರಯತ್ನಗಳು. ಸ್ವಲ್ಪ ನಂತರ ಪ್ರಯತ್ನಿಸಿ." : "Too many attempts. Try again in a few minutes.")
           : (kn ? "ಈಗ ಪರಿಶೀಲಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ." : "Could not check the password just now."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="ap-signin" onSubmit={submit} autoComplete="on">
      <div className="ap-signin-hd">
        <Fingerprint size={15} aria-hidden="true" />
        <div>
          <b>{kn ? "ಮೇಲ್ವಿಚಾರಕ ಅಧಿಕಾರಿ ಪ್ರವೇಶ" : "Supervising officer sign-in"}</b>
          <span>{kn ? "ಕ್ರಮಗಳನ್ನು ಪರಿಶೀಲಿಸಲು ನಿಮ್ಮ ಮೇಲ್ವಿಚಾರಕ ಐಡಿ ಮತ್ತು ಪಾಸ್‌ವರ್ಡ್ ನಮೂದಿಸಿ." : "Enter your supervisor ID and password to review and approve actions."}</span>
        </div>
      </div>
      <div className="ap-signin-row">
        <label>
          <span>{kn ? "ಅನುಮೋದಕ ಐಡಿ" : "Approver ID"}</span>
          <input name="username" autoComplete="username" value={id} onChange={(e) => setId(e.target.value)} disabled={busy} />
        </label>
        <label>
          <span>{kn ? "ಪಾಸ್‌ವರ್ಡ್" : "Password"}</span>
          <input name="password" type="password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)}
                 disabled={busy} autoFocus placeholder={kn ? "ಪಾಸ್‌ವರ್ಡ್" : "Password"} />
        </label>
        <button type="submit" className="ap-btn approve" disabled={busy}>
          {busy ? "…" : (kn ? "ಪ್ರವೇಶಿಸಿ" : "Sign in")}
        </button>
      </div>
      <div className="ap-signin-ft">
        <button type="button" className="ap-fill" disabled={busy} onClick={() => {
          setId(APPROVER_ID);
          // Filled only when this build carries a demo password (.env.local); otherwise typed.
          setPw(process.env.NEXT_PUBLIC_DEMO_PW_APPROVER || "");
          setErr("");
        }}>[ {kn ? "ಡೆಮೊ ಅನುಮೋದಕ ತುಂಬಿಸಿ" : "Fill demo approver"} ]</button>
        {err && <em role="alert">{err}</em>}
      </div>
    </form>
  );
}

function PendingCard({ a, kn, now, me, approver, reason, setReason, busy, error, decide }) {
  const cd = countdown(a.expires_at, now);
  const mine = a.proposed_by === me;
  const reasonOk = reason.trim().length >= 8;
  const flags = a.compliance?.status === "FLAGGED" ? (a.compliance.flags || []) : [];

  return (
    <article className={`ap-card risk-${a.risk} ${!a.integrity_ok ? "tampered" : ""}`}>
      <Badges a={a} kn={kn} />
      <h2>{a.title}</h2>
      <div className="ap-meta">
        <span>{kn ? "ವಿನಂತಿಸಿದವರು" : "Requested by"} <b>{a.proposed_by}</b> · {a.proposed_role} · {ago(a.proposed_at, now, kn)}</span>
        <span className={`ap-expiry ${cd.urgent ? "urgent" : ""}`}><Clock size={12} /> {kn ? "ಅವಧಿ" : "Expires in"} {cd.text}</span>
      </div>

      <div className="ap-grid">
        <section>
          <h4>{kn ? "ಸಮರ್ಥನೆ" : "Justification"}</h4>
          <blockquote>{a.justification}</blockquote>
        </section>
        <section>
          <h4>{kn ? "ವಿವರಗಳು" : "What will happen"}</h4>
          <dl>
            {Object.entries(a.payload || {}).map(([k, v]) => (
              <div key={k}><dt>{(FIELD_LABELS[k] || [k, k])[kn ? 1 : 0]}</dt><dd>{fieldValue(k, v)}</dd></div>
            ))}
          </dl>
        </section>
      </div>

      {a.evidence?.length > 0 && (
        <section className="ap-evidence">
          <h4>{kn ? "ಸಾಕ್ಷ್ಯ" : "Evidence"}</h4>
          <ul>{a.evidence.map((e, i) => <li key={i}><em>{e.label}</em><span>{e.value}</span></li>)}</ul>
        </section>
      )}

      {flags.length > 0 && (
        <div className="ap-flags"><ShieldAlert size={14} /> <div>{flags.map((f, i) => <p key={i}>{f}</p>)}{a.compliance.bnss_citation && <small>{a.compliance.bnss_citation}</small>}</div></div>
      )}

      {!a.integrity_ok && (
        <div className="ap-flags bad"><ShieldAlert size={14} /> <div><p>{kn ? "ಸಂಗ್ರಹಿಸಿದ ಕ್ರಮವು ಸಲ್ಲಿಸಿದ ಆವೃತ್ತಿಗೆ ಹೊಂದಿಕೆಯಾಗುವುದಿಲ್ಲ. ಇದನ್ನು ಅನುಮೋದಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ." : "The stored action no longer matches what was proposed. It cannot be approved."}</p></div></div>
      )}

      <footer className="ap-decide">
        {approver && !mine ? (
          <>
            <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} disabled={!!busy}
              placeholder={kn ? "ನಿರ್ಧಾರದ ಕಾರಣ (ಅಗತ್ಯ, ಆಡಿಟ್‌ನಲ್ಲಿ ದಾಖಲಾಗುತ್ತದೆ)" : "Reason for your decision (required - recorded in the audit chain)"} />
            <div className="ap-btns">
              {error && <span className="ap-err" role="alert">{error}</span>}
              <button className="ap-btn reject" disabled={!reasonOk || !!busy} onClick={() => decide(a, "reject")}>
                <XCircle size={14} /> {busy === "reject" ? "…" : (kn ? "ತಿರಸ್ಕರಿಸಿ" : "Reject")}
              </button>
              <button className="ap-btn approve" disabled={!reasonOk || !!busy || !a.integrity_ok} onClick={() => decide(a, "approve")}>
                <CheckCircle2 size={14} /> {busy === "approve" ? "…" : (kn ? "ಅನುಮೋದಿಸಿ ಮತ್ತು ಜಾರಿಗೊಳಿಸಿ" : "Approve & execute")}
              </button>
            </div>
          </>
        ) : mine ? (
          <>
            <p className="ap-note">{kn ? "ನೀವು ಈ ವಿನಂತಿಯನ್ನು ಸಲ್ಲಿಸಿದ್ದೀರಿ - ಬೇರೊಬ್ಬ ಮೇಲ್ವಿಚಾರಕ ಅಧಿಕಾರಿ ನಿರ್ಧರಿಸಬೇಕು." : "You filed this request - a different supervising officer must decide it."}</p>
            <div className="ap-btns">
              <input className="ap-inline" value={reason} onChange={(e) => setReason(e.target.value)} disabled={!!busy}
                placeholder={kn ? "ಹಿಂಪಡೆಯಲು ಕಾರಣ" : "Reason to withdraw"} />
              {error && <span className="ap-err" role="alert">{error}</span>}
              <button className="ap-btn ghost" disabled={!reasonOk || !!busy} onClick={() => decide(a, "withdraw")}>
                <Undo2 size={14} /> {kn ? "ಹಿಂಪಡೆಯಿರಿ" : "Withdraw"}
              </button>
            </div>
          </>
        ) : (
          <p className="ap-note">{kn ? "ಮೇಲ್ವಿಚಾರಕ ಅಧಿಕಾರಿಯ ನಿರ್ಧಾರಕ್ಕಾಗಿ ಕಾಯುತ್ತಿದೆ." : "Awaiting a supervising officer's decision."}</p>
        )}
      </footer>
    </article>
  );
}

function HistoryCard({ a, kn, now }) {
  const tone = STATUS_TONE[a.status] || "muted";
  const ex = a.execution || {};
  const outcome = ex.order_id ? `${kn ? "ಆದೇಶ" : "Order"} ${ex.order_id}` : ex.watch_id ? `${kn ? "ವೀಕ್ಷಣೆ" : "Watch"} ${ex.watch_id}` : null;
  return (
    <article className="ap-card compact">
      <div className="ap-hrow">
        <span className={`ap-status ${tone}`}>{a.status}</span>
        <h3>{a.title}</h3>
        <code className="ap-id">{a.action_id}</code>
      </div>
      <div className="ap-meta">
        <span>{kn ? "ವಿನಂತಿ" : "Requested"} <b>{a.proposed_by}</b> · {ago(a.proposed_at, now, kn)}</span>
        {a.decided_by && <span>{a.status === "WITHDRAWN" ? (kn ? "ಹಿಂಪಡೆದವರು" : "Withdrawn by") : (kn ? "ನಿರ್ಧರಿಸಿದವರು" : "Decided by")} <b>{a.decided_by}</b>{a.decided_at ? ` · ${ago(a.decided_at, now, kn)}` : ""}</span>}
        {outcome && <span className="ap-outcome"><CheckCircle2 size={12} /> {outcome}</span>}
      </div>
      {a.decision_reason && <blockquote className="small">{a.decision_reason}</blockquote>}
      {a.error && <p className="ap-err">{a.error}</p>}
    </article>
  );
}
