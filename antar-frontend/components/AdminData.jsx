"use client";

// Admin · Data: add FIRs from a KSP export file, in three steps so nothing reaches the
// register that an admin has not looked at - check the file, add the rows that passed,
// and remove an upload again if it was wrong. Every add and remove is on the audit chain
// (app/services/fir_upload.py).

import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

const fmtDate = (d, kn) => {
  if (!d) return "—";
  const x = new Date(`${String(d).slice(0, 10)}T00:00:00`);
  return isNaN(x) ? d : x.toLocaleDateString(kn ? "kn-IN" : "en-IN", { day: "numeric", month: "short", year: "numeric" });
};
const fmtWhen = (ts, kn) => {
  const x = new Date(ts);
  return isNaN(x) ? ts : x.toLocaleString(kn ? "kn-IN" : "en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
};

export default function AdminData({ kn }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(null);           // "check" | "add" | "template" | batch_id
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null);
  const [added, setAdded] = useState(null);
  const [history, setHistory] = useState(null);
  const [undoing, setUndoing] = useState(null);     // batch_id with the reason box open
  const [reason, setReason] = useState("");
  const [showAll, setShowAll] = useState(false);

  const loadHistory = () => fetchAPI("/api/upload/history")
    .then((d) => setHistory(d.uploads || []))
    .catch(() => setHistory([]));
  useEffect(() => { loadHistory(); }, []);

  async function downloadTemplate() {
    setBusy("template"); setError(null);
    try {
      const res = await fetch(`${API}/api/upload/template`);
      if (!res.ok) throw new Error(res.status === 403 ? (kn ? "ನಿರ್ವಾಹಕರಿಗೆ ಮಾತ್ರ." : "Admins only.") : `HTTP ${res.status}`);
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url; a.download = "antar_fir_upload_template.csv"; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (e) { setError(e.message); }
    setBusy(null);
  }

  async function check() {
    if (!file) return;
    setBusy("check"); setError(null); setPreview(null); setAdded(null); setShowAll(false);
    try {
      const form = new FormData();
      form.append("file", file);
      setPreview(await fetchAPI("/api/upload/preview", { method: "POST", body: form }));
    } catch (e) { setError(e.detail || e.message); }
    setBusy(null);
  }

  async function add() {
    if (!preview) return;
    setBusy("add"); setError(null);
    try {
      const r = await fetchAPI("/api/upload/commit", { method: "POST", body: JSON.stringify({ preview_id: preview.preview_id }) });
      setAdded(r); setPreview(null); setFile(null);
      loadHistory();
    } catch (e) { setError(e.detail || e.message); }
    setBusy(null);
  }

  async function undo(batch) {
    setBusy(batch); setError(null);
    try {
      await fetchAPI(`/api/upload/${encodeURIComponent(batch)}/undo`, { method: "POST", body: JSON.stringify({ reason }) });
      setUndoing(null); setReason("");
      loadHistory();
    } catch (e) { setError(e.detail || e.message); }
    setBusy(null);
  }

  const p = preview;
  const missingCols = p ? p.columns.filter((c) => !c.found) : [];
  const rejected = p ? (showAll ? p.rejected : p.rejected.slice(0, 8)) : [];

  return (
    <div className="ac-block ad-wrap">
      <div className="ac-block-hd"><span className="ac-block-t">{kn ? "FIR ಗಳನ್ನು ಸೇರಿಸಿ" : "Add FIRs from a file"}</span></div>
      <p className="ad-sub">
        {kn
          ? "KSP FIR ರಫ್ತು ಸ್ವರೂಪದ CSV ಫೈಲ್. ಮೊದಲು ಫೈಲ್ ಪರಿಶೀಲಿಸಿ: ಪ್ರತಿ ಸಾಲನ್ನು ನೋಂದಣಿಯೊಂದಿಗೆ ಹೋಲಿಸಲಾಗುತ್ತದೆ, ಏನನ್ನೂ ಬರೆಯಲಾಗುವುದಿಲ್ಲ. ನಂತರ ಉತ್ತೀರ್ಣವಾದ ಸಾಲುಗಳನ್ನು ಸೇರಿಸಿ. ಪ್ರತಿ ಅಪ್‌ಲೋಡ್ ಅನ್ನು ಲೆಕ್ಕಪರಿಶೋಧನಾ ಸರಪಳಿಯಲ್ಲಿ ದಾಖಲಿಸಲಾಗುತ್ತದೆ ಮತ್ತು ತೆಗೆದುಹಾಕಬಹುದು."
          : "A CSV in the KSP FIR export format. Check the file first: every row is compared with the register and nothing is written. Then add the rows that passed. Every upload is recorded on the audit chain and can be removed again."}
      </p>

      <ol className="ad-steps">
        <li>
          <span className="ad-n">1</span>
          <div>
            <b>{kn ? "ಮಾದರಿ ಫೈಲ್" : "Get the template"}</b>
            <span>{kn ? "ಸರಿಯಾದ ಕಾಲಂ ಹೆಸರುಗಳು ಮತ್ತು ಎರಡು ಮಾದರಿ ಸಾಲುಗಳು." : "The exact column names, with two sample rows to overwrite."}</span>
          </div>
          <button className="ac-btn-ghost ad-btn" onClick={downloadTemplate} disabled={busy === "template"}>
            {busy === "template" ? "…" : (kn ? "ಡೌನ್‌ಲೋಡ್ CSV" : "Download CSV")}
          </button>
        </li>
        <li>
          <span className="ad-n">2</span>
          <div>
            <b>{kn ? "ಫೈಲ್ ಆಯ್ಕೆ ಮಾಡಿ ಮತ್ತು ಪರಿಶೀಲಿಸಿ" : "Choose the file and check it"}</b>
            <span>{kn ? "5 MB ಮತ್ತು 5,000 ಸಾಲುಗಳವರೆಗೆ." : "Up to 5 MB and 5,000 rows."}</span>
          </div>
          <div className="ad-pick">
            <label className="ac-btn-ghost ad-btn ad-file">
              <input type="file" accept=".csv" onChange={(e) => { setFile(e.target.files?.[0] || null); setPreview(null); setAdded(null); setError(null); }} />
              <span>{file ? file.name : (kn ? "CSV ಆಯ್ಕೆ" : "Choose CSV")}</span>
            </label>
            <button className="ac-btn-primary ad-btn" onClick={check} disabled={!file || busy === "check"}>
              {busy === "check" ? (kn ? "ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…" : "Checking…") : (kn ? "ಫೈಲ್ ಪರಿಶೀಲಿಸಿ" : "Check file")}
            </button>
          </div>
        </li>
      </ol>

      {error && <div className="ad-msg ad-bad" role="alert">{error}</div>}
      {added && (
        <div className="ad-msg ad-good" role="status">
          {kn
            ? `${added.rows_added.toLocaleString("en-IN")} FIR ಗಳನ್ನು ಸೇರಿಸಲಾಗಿದೆ (${added.first_fir} – ${added.last_fir}), ${fmtDate(added.first_date, kn)} ರಿಂದ ${fmtDate(added.last_date, kn)}. ಅಪ್‌ಲೋಡ್ ${added.batch_id}.`
            : `${added.rows_added.toLocaleString("en-IN")} FIRs added (${added.first_fir} – ${added.last_fir}), dated ${fmtDate(added.first_date, kn)} to ${fmtDate(added.last_date, kn)}. Upload ${added.batch_id}. Answers use them from the next question.`}
        </div>
      )}

      {p && (
        <div className="ad-preview">
          <div className="ad-cards">
            <div><b>{p.rows_read.toLocaleString("en-IN")}</b><span>{kn ? "ಸಾಲುಗಳು ಓದಲಾಗಿದೆ" : "rows read"}</span></div>
            <div className="ok"><b>{p.rows_ready.toLocaleString("en-IN")}</b><span>{kn ? "ಸೇರಿಸಲು ಸಿದ್ಧ" : "ready to add"}</span></div>
            <div className={p.rows_rejected ? "bad" : ""}><b>{p.rows_rejected.toLocaleString("en-IN")}</b><span>{kn ? "ತಿರಸ್ಕರಿಸಲಾಗಿದೆ" : "refused"}</span></div>
            <div className={p.warnings.length ? "warn" : ""}><b>{p.warnings.length}</b><span>{kn ? "ಎಚ್ಚರಿಕೆಗಳು" : "warnings"}</span></div>
          </div>
          <p className="ad-line">
            {p.first_date
              ? (kn ? `ದಿನಾಂಕಗಳು ${fmtDate(p.first_date, kn)} – ${fmtDate(p.last_date, kn)}.` : `Dates ${fmtDate(p.first_date, kn)} – ${fmtDate(p.last_date, kn)}.`)
              : ""}
            {" "}
            {kn ? `ಬೇಕಾದ ಸ್ಥಳ ${p.space.needed_mb < 1 ? "1 MB ಗಿಂತ ಕಡಿಮೆ" : `~${p.space.needed_mb} MB`}, ಲಭ್ಯ ${p.space.free_mb.toLocaleString("en-IN")} MB.`
                : `Needs ${p.space.needed_mb < 1 ? "under 1 MB" : `about ${p.space.needed_mb} MB`}; ${p.space.free_mb.toLocaleString("en-IN")} MB free.`}
            {!p.space.fits && <b className="ad-red"> {kn ? "ಸ್ಥಳ ಸಾಕಾಗುವುದಿಲ್ಲ — ಕಡಿಮೆ ಸಾಲುಗಳನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ." : "Not enough space — upload fewer rows."}</b>}
          </p>

          {p.lasts_until_restart && (
            <p className="ad-msg ad-warn">
              {kn ? "ಇದು ಆನ್‌ಲೈನ್ ಪ್ರತಿ: ಇಲ್ಲಿ ಸೇರಿಸಿದ FIR ಗಳು ಸರ್ವರ್ ಮರುಪ್ರಾರಂಭವಾಗುವವರೆಗೆ ಮಾತ್ರ ಇರುತ್ತವೆ. ಶಾಶ್ವತವಾಗಿ ಸೇರಿಸಲು ಮುಖ್ಯ Antar ವ್ಯವಸ್ಥೆಯನ್ನು ಬಳಸಿ."
                  : "This is the online copy: FIRs added here last until the server restarts. To add them for good, use the main Antar system."}
            </p>
          )}
          <details className="ad-det">
            <summary>
              {kn ? "ಕಾಲಂ ಹೊಂದಾಣಿಕೆ" : "Column check"} · {p.columns.length - missingCols.length}/{p.columns.length} {kn ? "ಕಂಡುಬಂದಿದೆ" : "found"}
              {p.ignored_columns.length ? ` · ${p.ignored_columns.length} ${kn ? "ನಿರ್ಲಕ್ಷಿಸಲಾಗಿದೆ" : "ignored"}` : ""}
            </summary>
            <div className="ad-cols">
              {p.columns.map((c) => (
                <span key={c.column} className={c.found ? "ok" : c.required ? "bad" : ""} title={c.required ? (kn ? "ಅಗತ್ಯ" : "required") : ""}>
                  {c.found ? "✓" : "–"} {c.column.replace("\t", " ")}
                </span>
              ))}
            </div>
            {p.ignored_columns.length > 0 && (
              <p className="ad-line">{kn ? "ಈ ಕಾಲಂಗಳನ್ನು ಓದಲಾಗಿಲ್ಲ: " : "Not read (not part of the format): "}{p.ignored_columns.join(", ")}</p>
            )}
          </details>

          {p.sample.length > 0 && (
            <>
              <h4 className="ad-h">{kn ? "ಸೇರಿಸಲಾಗುವ ಮೊದಲ ಸಾಲುಗಳು" : "First rows to be added"}</h4>
              <div className="ac-table-wrap">
                <table className="ac-table ad-table">
                  <thead><tr>
                    <th>{kn ? "ದಿನಾಂಕ" : "Date"}</th><th>{kn ? "ಜಿಲ್ಲೆ" : "District"}</th><th>{kn ? "ಠಾಣೆ" : "Station"}</th>
                    <th>{kn ? "ಅಪರಾಧ" : "Crime"}</th><th>{kn ? "ಹಂತ" : "Stage"}</th>
                  </tr></thead>
                  <tbody>
                    {p.sample.map((r, i) => (
                      <tr key={i}>
                        <td>{fmtDate(r.date, kn)}</td><td>{r.District_Name}</td><td>{r.UnitName}</td>
                        <td>{r.CrimeGroup_Name}{r.CrimeHead_Name ? ` · ${r.CrimeHead_Name}` : ""}</td><td>{r.FIR_Stage || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {p.rejected.length > 0 && (
            <>
              <h4 className="ad-h">{kn ? "ತಿರಸ್ಕರಿಸಿದ ಸಾಲುಗಳು ಮತ್ತು ಕಾರಣ" : "Refused rows, and why"}</h4>
              <ul className="ad-list bad">
                {rejected.map((r) => (
                  <li key={r.row}><span className="ad-row">{kn ? "ಸಾಲು" : "Row"} {r.row}</span><span>{r.reasons.join("; ")}</span></li>
                ))}
              </ul>
              {p.rejected.length > 8 && (
                <button className="ad-link" onClick={() => setShowAll(!showAll)}>
                  {showAll ? (kn ? "ಕಡಿಮೆ ತೋರಿಸಿ" : "Show fewer") : (kn ? `ಎಲ್ಲಾ ${p.rejected.length} ತೋರಿಸಿ` : `Show all ${p.rejected.length}`)}
                </button>
              )}
            </>
          )}

          {p.warnings.length > 0 && (
            <>
              <h4 className="ad-h">{kn ? "ಎಚ್ಚರಿಕೆಗಳು (ಸಾಲುಗಳನ್ನು ಸೇರಿಸಲಾಗುತ್ತದೆ)" : "Warnings (these rows are still added)"}</h4>
              <ul className="ad-list warn">
                {p.warnings.slice(0, 12).map((w, i) => (
                  <li key={i}><span className="ad-row">{kn ? "ಸಾಲು" : "Row"} {w.row}</span><span>{w.issue}</span></li>
                ))}
              </ul>
            </>
          )}

          <div className="ad-actions">
            <button className="ac-save-btn ad-btn" onClick={add} disabled={!p.rows_ready || !p.space.fits || busy === "add"}>
              {busy === "add" ? (kn ? "ಸೇರಿಸಲಾಗುತ್ತಿದೆ…" : "Adding…")
                : (kn ? `${p.rows_ready.toLocaleString("en-IN")} FIR ಸೇರಿಸಿ` : `Add ${p.rows_ready.toLocaleString("en-IN")} FIRs`)}
            </button>
            <button className="ac-btn-ghost ad-btn" onClick={() => setPreview(null)}>{kn ? "ರದ್ದುಮಾಡಿ" : "Cancel"}</button>
            <span className="ad-note">{kn ? "ಈ ಪರಿಶೀಲನೆ 15 ನಿಮಿಷ ಮಾನ್ಯ." : "This check is valid for 15 minutes."}</span>
          </div>
        </div>
      )}

      <h4 className="ad-h ad-hist-h">{kn ? "ಹಿಂದಿನ ಅಪ್‌ಲೋಡ್‌ಗಳು" : "Past uploads"}</h4>
      {history === null ? (
        <p className="ad-line">{kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Loading…"}</p>
      ) : history.length === 0 ? (
        <p className="ad-line">{kn ? "ಇನ್ನೂ ಯಾವುದೇ ಅಪ್‌ಲೋಡ್ ಇಲ್ಲ." : "No uploads yet."}</p>
      ) : (
        <ul className="ad-hist">
          {history.map((h) => (
            <li key={h.batch_id} className={h.status === "removed" ? "gone" : ""}>
              <div className="ad-hist-top">
                <b>{h.rows_added.toLocaleString("en-IN")} FIRs</b>
                <span>{h.filename}</span>
                <span className="ad-tag">{h.status === "removed" ? (kn ? "ತೆಗೆದುಹಾಕಲಾಗಿದೆ" : "removed") : (kn ? "ನೋಂದಣಿಯಲ್ಲಿ" : "in the register")}</span>
              </div>
              <div className="ad-hist-meta">
                {fmtWhen(h.created_at, kn)} · {h.officer} · {fmtDate(h.first_date, kn)} – {fmtDate(h.last_date, kn)}
                {h.rows_rejected ? ` · ${h.rows_rejected} ${kn ? "ತಿರಸ್ಕೃತ" : "refused"}` : ""} · <code>{h.batch_id}</code>
              </div>
              {h.status === "removed" && (
                <div className="ad-hist-meta">{kn ? "ತೆಗೆದವರು" : "Removed by"} {h.undone_by}, {fmtWhen(h.undone_at, kn)}: “{h.undo_reason}”</div>
              )}
              {h.status === "added" && (undoing === h.batch_id ? (
                <div className="ad-undo">
                  <input className="ac-input" value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)}
                    placeholder={kn ? "ತೆಗೆದುಹಾಕಲು ಕಾರಣ" : "Reason for removing (recorded)"} />
                  <button className="ac-btn-primary ad-btn" onClick={() => undo(h.batch_id)} disabled={reason.trim().length < 5 || busy === h.batch_id}>
                    {busy === h.batch_id ? "…" : (kn ? `${h.rows_added} FIR ತೆಗೆದುಹಾಕಿ` : `Remove ${h.rows_added} FIRs`)}
                  </button>
                  <button className="ac-btn-ghost ad-btn" onClick={() => { setUndoing(null); setReason(""); }}>{kn ? "ಬೇಡ" : "Keep"}</button>
                </div>
              ) : (
                <button className="ad-link" onClick={() => { setUndoing(h.batch_id); setReason(""); }}>{kn ? "ಈ ಅಪ್‌ಲೋಡ್ ತೆಗೆದುಹಾಕಿ" : "Undo this upload"}</button>
              ))}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
