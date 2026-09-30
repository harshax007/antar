"use client";

// Request a real-world action (patrol redeployment / watchlist add). Nothing here takes
// effect: it files a proposal that a supervising officer must approve (app/core/hitl.py).

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { fetchAPI } from "@/lib/api";
import { ShieldCheck, X, Send, CheckCircle2 } from "lucide-react";

const SHIFTS = [["morning", "Morning", "ಬೆಳಿಗ್ಗೆ"], ["evening", "Evening", "ಸಂಜೆ"], ["night", "Night", "ರಾತ್ರಿ"], ["all-day", "All day", "ದಿನವಿಡೀ"]];
const DURATIONS = [4, 8, 12, 24];

export default function ProposeAction({ open, onClose, type, defaults = {}, evidence = [], kn = false }) {
  const isPatrol = type === "patrol_redeployment";
  const [form, setForm] = useState({});
  const [justification, setJustification] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(null);

  useEffect(() => {
    if (!open) return;
    setForm(isPatrol
      ? { zone: defaults.zone || "", units: 2, shift: "night", duration_hours: 8, crime_focus: defaults.crime_focus || "all crimes" }
      : { watch_type: defaults.watch_type || "entity", target: defaults.target || "", label: defaults.label || "" });
    // A forecast-driven proposal arrives with the forecast as its draft justification;
    // the officer can edit it, and it still has to be approved.
    setJustification(defaults.justification || "");
    setError(null);
    setDone(null);
  }, [open, type]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape" && !busy) onClose?.(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onClose]);

  if (!open || typeof document === "undefined") return null;
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const justOk = justification.trim().length >= 12;

  async function submit() {
    if (!justOk || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetchAPI("/api/hitl/propose", {
        method: "POST",
        body: JSON.stringify({ action_type: type, payload: form, justification: justification.trim(), evidence }),
      });
      setDone(res);
    } catch (err) {
      const d = err.detail;
      setError({
        message: err.message,
        compliance: d?.compliance || null,
      });
    } finally {
      setBusy(false);
    }
  }

  return createPortal(
    <div className="pa-back" onMouseDown={(e) => { if (e.target === e.currentTarget && !busy) onClose?.(); }}>
      <div className="pa-dialog" role="dialog" aria-modal="true" aria-labelledby="pa-title">
        <header>
          <div>
            <span className="pa-kicker"><ShieldCheck size={12} aria-hidden="true" /> {kn ? "ಅನುಮೋದನೆ ಅಗತ್ಯ" : "Requires supervising officer approval"}</span>
            <h3 id="pa-title">{isPatrol ? (kn ? "ಗಸ್ತು ನಿಯೋಜನೆ ವಿನಂತಿ" : "Request patrol deployment") : (kn ? "ವೀಕ್ಷಣಾ ಪಟ್ಟಿ ವಿನಂತಿ" : "Request watchlist entry")}</h3>
          </div>
          <button className="pa-x" onClick={onClose} disabled={busy} aria-label="Close"><X size={16} /></button>
        </header>

        {done ? (
          <div className="pa-done">
            <CheckCircle2 size={28} aria-hidden="true" />
            <b>{done.duplicate ? (kn ? "ಈಗಾಗಲೇ ಬಾಕಿ ಇದೆ" : "Already awaiting approval") : (kn ? "ಅನುಮೋದನೆಗೆ ಕಳುಹಿಸಲಾಗಿದೆ" : "Sent for approval")}</b>
            <p>{done.title}</p>
            <code>{done.action_id}</code>
            <p className="pa-muted">
              {kn ? "ಮೇಲ್ವಿಚಾರಕ ಅಧಿಕಾರಿ ಅನುಮೋದಿಸುವವರೆಗೆ ಇದು ಜಾರಿಗೆ ಬರುವುದಿಲ್ಲ." : "Nothing takes effect until a supervising officer approves it."}
              {done.compliance?.status === "FLAGGED" && (kn ? " ಅನುಸರಣೆ ಎಚ್ಚರಿಕೆ ಲಗತ್ತಿಸಲಾಗಿದೆ." : " A compliance flag was attached for the reviewer.")}
            </p>
            <div className="pa-actions">
              <a className="pa-btn ghost" href="/approvals">{kn ? "ಸರತಿ ನೋಡಿ" : "View queue"}</a>
              <button className="pa-btn" onClick={onClose}>{kn ? "ಮುಗಿದಿದೆ" : "Done"}</button>
            </div>
          </div>
        ) : (
          <>
            <div className="pa-body">
              {isPatrol ? (
                <div className="pa-grid">
                  <label className="span2">{kn ? "ವಲಯ" : "Zone"}<input value={form.zone || ""} readOnly /></label>
                  <label>{kn ? "ಘಟಕಗಳು" : "Units"}
                    <input type="number" min={1} max={20} value={form.units ?? 2} onChange={(e) => set("units", Math.max(1, Math.min(20, Number(e.target.value) || 1)))} />
                  </label>
                  <label>{kn ? "ಅವಧಿ" : "Duration"}
                    <select value={form.duration_hours ?? 8} onChange={(e) => set("duration_hours", Number(e.target.value))}>
                      {DURATIONS.map((h) => <option key={h} value={h}>{h} {kn ? "ಗಂಟೆ" : "hours"}</option>)}
                    </select>
                  </label>
                  <label>{kn ? "ಪಾಳಿ" : "Shift"}
                    <select value={form.shift || "night"} onChange={(e) => set("shift", e.target.value)}>
                      {SHIFTS.map(([v, en, knl]) => <option key={v} value={v}>{kn ? knl : en}</option>)}
                    </select>
                  </label>
                  <label>{kn ? "ಅಪರಾಧ ಗಮನ" : "Crime focus"}<input value={form.crime_focus || ""} onChange={(e) => set("crime_focus", e.target.value)} /></label>
                </div>
              ) : (
                <div className="pa-grid">
                  <label>{kn ? "ಪ್ರಕಾರ" : "Watch type"}
                    <select value={form.watch_type || "entity"} onChange={(e) => set("watch_type", e.target.value)}>
                      <option value="entity">{kn ? "ವ್ಯಕ್ತಿ" : "Entity"}</option>
                      <option value="pattern">{kn ? "ಮಾದರಿ" : "Pattern"}</option>
                      <option value="corridor">{kn ? "ಕಾರಿಡಾರ್" : "Corridor"}</option>
                    </select>
                  </label>
                  <label>{kn ? "ಗುರಿ" : "Target"}<input value={form.target || ""} readOnly /></label>
                  <label className="span2">{kn ? "ಲೇಬಲ್" : "Label"}<input value={form.label || ""} onChange={(e) => set("label", e.target.value)} /></label>
                </div>
              )}

              {evidence.length > 0 && (
                <div className="pa-evidence">
                  <span>{kn ? "ಲಗತ್ತಿಸಿದ ಸಾಕ್ಷ್ಯ" : "Evidence attached for the reviewer"}</span>
                  <ul>{evidence.map((e, i) => <li key={i}><em>{e.label}</em> {e.value}</li>)}</ul>
                </div>
              )}

              <label className="pa-just">
                {kn ? "ಸಮರ್ಥನೆ (ಅಗತ್ಯ)" : "Justification (required)"}
                <textarea rows={3} value={justification} onChange={(e) => setJustification(e.target.value)}
                  placeholder={isPatrol ? (kn ? "ಈ ನಿಯೋಜನೆ ಏಕೆ ಅಗತ್ಯ?" : "Why is this deployment needed now?") : (kn ? "ಇದನ್ನು ಏಕೆ ವೀಕ್ಷಿಸಬೇಕು?" : "Why should this be placed under watch?")} />
                <small className={justOk ? "ok" : ""}>{justOk ? (kn ? "ಸಾಕು" : "Looks good") : (kn ? "ಕನಿಷ್ಠ 12 ಅಕ್ಷರಗಳು" : "At least 12 characters - the reviewer decides on this")}</small>
              </label>

              {error && (
                <div className="pa-error" role="alert">
                  <b>{error.message}</b>
                  {error.compliance?.explanation && <p>{error.compliance.explanation}</p>}
                  {error.compliance?.bnss_citation && <small>{error.compliance.bnss_citation}</small>}
                </div>
              )}
            </div>
            <footer>
              <span className="pa-muted">{kn ? "ನೀವು ಇದನ್ನು ಅನುಮೋದಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ." : "You cannot approve your own request."}</span>
              <button className="pa-btn ghost" onClick={onClose} disabled={busy}>{kn ? "ರದ್ದು" : "Cancel"}</button>
              <button className="pa-btn" onClick={submit} disabled={!justOk || busy}>
                <Send size={13} aria-hidden="true" /> {busy ? (kn ? "ಕಳುಹಿಸಲಾಗುತ್ತಿದೆ…" : "Submitting…") : (kn ? "ಅನುಮೋದನೆಗೆ ಕಳುಹಿಸಿ" : "Submit for approval")}
              </button>
            </footer>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}
