"use client";
// Shift plan: one station's next shift on a page.
//
// Counted from the record and the back-tested forecast by /api/forecast/shift-plan. No
// sentence here is written by a language model. It suggests; "Propose patrol deployment"
// files a proposal that a supervising officer has to approve.
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { fetchAPI } from "@/lib/api";
import ProposeAction from "@/components/ProposeAction";
import UsefulFeedback from "@/components/UsefulFeedback";
import { MaterialBackdrop, MaterialPanel } from "@/components/ui/MaterialPanel";
import { crimeKn, dateKn } from "@/lib/kn";

const day = (iso, kn) => {
  const x = new Date(`${iso}T00:00:00`);
  return Number.isNaN(x.getTime()) ? iso : kn ? dateKn(x) : x.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
};
const DAY_KN = { Monday: "ಸೋಮ", Tuesday: "ಮಂಗಳ", Wednesday: "ಬುಧ", Thursday: "ಗುರು", Friday: "ಶುಕ್ರ", Saturday: "ಶನಿ", Sunday: "ಭಾನು" };

export default function ShiftPlan({ station, onClose, kn = false }) {
  const [p, setP] = useState(null);
  const [err, setErr] = useState(null);
  const [note, setNote] = useState("");
  const [propose, setPropose] = useState(false);

  useEffect(() => {
    let alive = true;
    setP(null); setErr(null);
    fetchAPI(`/api/forecast/shift-plan?station=${encodeURIComponent(station)}`)
      .then((d) => { if (alive) setP(d); })
      .catch((e) => { if (alive) setErr(e?.status === 404 ? "restart" : "failed"); });
    return () => { alive = false; };
  }, [station]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape" && !propose) onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, propose]);

  const L = (en, kan) => (kn ? kan : en);
  const flash = (t) => { setNote(t); setTimeout(() => setNote(""), 2400); };
  const copy = async () => { try { await navigator.clipboard.writeText(p.text); flash(L("Copied", "ನಕಲಿಸಲಾಗಿದೆ")); } catch { flash(L("Copy is not available here.", "ಇಲ್ಲಿ ನಕಲಿಸಲು ಆಗುವುದಿಲ್ಲ.")); } };
  const max = p ? Math.max(1, ...p.days.by_day.map((d) => d.firs)) : 1;

  return createPortal(
    <MaterialBackdrop className="sp-back" role="dialog" aria-modal="true" aria-label={kn ? `${station} ಪಾಳಿ ಯೋಜನೆ` : `Shift plan for ${station}`}
         onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <MaterialPanel as="section" className="sp">
        <header>
          <div>
            <span className="sp-eyebrow">{L("Shift plan", "ಪಾಳಿ ಯೋಜನೆ")}</span>
            <h3>{p?.station || station}</h3>
            {p?.district && <p>{p.district} · {L("next 7 days", "ಮುಂದಿನ 7 ದಿನಗಳು")}</p>}
          </div>
          <button type="button" className="sp-x" onClick={onClose} aria-label={L("Close this window", "ಮುಚ್ಚಿ")} title={L("Close", "ಮುಚ್ಚಿ")}><X size={18} /></button>
        </header>

        {err && <p className="sp-empty">{err === "restart" ? L("The shift plan needs the server restarted to load it.", "ಪಾಳಿ ಯೋಜನೆಗೆ ಸರ್ವರ್ ಮರುಪ್ರಾರಂಭ ಬೇಕು.") : L("The plan could not be read just now. Try again.", "ಯೋಜನೆಯನ್ನು ಈಗ ಓದಲಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.")}</p>}
        {!p && !err && <p className="sp-empty">{L("Putting the plan together from the records…", "ದಾಖಲೆಗಳಿಂದ ಯೋಜನೆ ಸಿದ್ಧಪಡಿಸಲಾಗುತ್ತಿದೆ…")}</p>}

        {p && (
          <div className="sp-body">
            {p.forecast && !p.forecast.thin ? (
              <div className="sp-top">
                <b>{p.forecast.likely}</b>
                <div>
                  <span>{L("FIRs likely in the next 7 days", "ಮುಂದಿನ 7 ದಿನಗಳಲ್ಲಿ ಸಂಭಾವ್ಯ FIR ಗಳು")}</span>
                  <em>{L(`very likely ${p.forecast.very_likely}; a usual week here is ${Number(p.forecast.usual).toFixed(1)}`,
                         `ಬಹಳ ಸಂಭವನೀಯ ${p.forecast.very_likely}; ಇಲ್ಲಿ ಸಾಮಾನ್ಯ ವಾರ ${Number(p.forecast.usual).toFixed(1)}`)}</em>
                </div>
              </div>
            ) : <p className="sp-empty">{L("Too little history here for a reliable forecast.", "ವಿಶ್ವಾಸಾರ್ಹ ಮುನ್ಸೂಚನೆಗೆ ಇಲ್ಲಿ ಸಾಕಷ್ಟು ಇತಿಹಾಸವಿಲ್ಲ.")}</p>}

            <dl className="sp-rows">
              <div>
                <dt>{L("Beats to cover first", "ಮೊದಲು ಗಮನಿಸಬೇಕಾದ ಬೀಟ್‌ಗಳು")}</dt>
                <dd>{p.beats.length ? (
                  <ol>{p.beats.map((b) => <li key={b.unit}><b>{b.name}</b> {L("likely", "ಸಂಭಾವ್ಯ")} {b.likely}{b.reason && <small>{(kn && b.reason_kn) || b.reason}</small>}</li>)}</ol>
                ) : L("The forecast does not separate this station's beats.", "ಮುನ್ಸೂಚನೆ ಈ ಠಾಣೆಯ ಬೀಟ್‌ಗಳನ್ನು ಪ್ರತ್ಯೇಕಿಸುವುದಿಲ್ಲ.")}</dd>
              </div>
              <div>
                <dt>{L("Kinds of case expected", "ನಿರೀಕ್ಷಿತ ಪ್ರಕರಣಗಳ ಬಗೆ")}</dt>
                <dd>{p.kinds.length ? p.kinds.map((k) => `${(kn && crimeKn(k.label)) || k.label} (${k.likely})`).join(", ") : L("No kind of case is expected more than now and then.", "ಯಾವುದೇ ಬಗೆಯ ಪ್ರಕರಣ ಆಗಾಗ ಮೀರಿ ನಿರೀಕ್ಷಿತವಿಲ್ಲ.")}</dd>
              </div>
              <div>
                <dt>{L("Days of the week", "ವಾರದ ದಿನಗಳು")}</dt>
                <dd>{(kn && p.days.text_kn) || p.days.text}
                  {p.days.firs >= 60 && (
                    <span className="sp-days" aria-hidden="true">
                      {p.days.by_day.map((d) => <i key={d.day} className={p.days.stands_out.includes(d.day) ? "on" : ""} title={`${kn ? DAY_KN[d.day] || d.day : d.day}: ${d.firs}`}>
                        <u style={{ height: `${Math.max(2, Math.round((d.firs / max) * 36))}px` }} /><s>{kn ? (DAY_KN[d.day] || d.day).slice(0, 2) : d.day[0]}</s></i>)}
                    </span>
                  )}
                  <small>{L("By the day an FIR was registered. The register does not hold the hour.", "FIR ದಾಖಲಾದ ದಿನದಿಂದ. ದಾಖಲೆಯಲ್ಲಿ ಸಮಯ ಇಲ್ಲ.")}</small>
                </dd>
              </div>
              <div>
                <dt>{L("Still open here", "ಇಲ್ಲಿ ಇನ್ನೂ ಬಾಕಿ")}</dt>
                <dd>{p.open_cases.total ? (
                  <>
                    <b>{p.open_cases.total.toLocaleString("en-IN")}</b> FIR{L("s", "")}{p.open_cases.in_listed_beats ? L(`, ${p.open_cases.in_listed_beats} in the beats above`, `, ಮೇಲಿನ ಬೀಟ್‌ಗಳಲ್ಲಿ ${p.open_cases.in_listed_beats}`) : ""}
                    <small>{(kn && p.open_cases.definition_kn) || p.open_cases.definition}</small>
                    <ul className="sp-open">{p.open_cases.newest.map((c, i) => (
                      <li key={`${c.fir}-${i}`}><code>{c.fir || L("no number", "ಸಂಖ್ಯೆ ಇಲ್ಲ")}</code><span>{(kn && crimeKn(c.crime)) || c.crime} · {c.beat}</span><time>{day(c.date, kn)}</time></li>
                    ))}</ul>
                  </>
                ) : L("No FIR from the past year is under investigation without a charge-sheet.", "ಕಳೆದ ವರ್ಷದ ಯಾವುದೇ FIR ಆರೋಪಪಟ್ಟಿ ಇಲ್ಲದೆ ತನಿಖೆಯಲ್ಲಿಲ್ಲ.")}</dd>
              </div>
              {p.events.map((e) => (
                <div key={e.name}>
                  <dt>{e.name}</dt>
                  <dd>{e.when}.{e.effect ? ` ${(kn && e.effect_kn) || e.effect}` : ""}
                    {e.watch?.length > 0 && <small>{L("Less certain:", "ಕಡಿಮೆ ಖಚಿತ:")} {e.watch.join(", ")}.</small>}</dd>
                </div>
              ))}
            </dl>

            {p.accuracy && <p className="sp-acc"><b>{L("How far to trust it.", "ಎಷ್ಟು ನಂಬಬಹುದು.")}</b> {p.accuracy}</p>}
            <ul className="sp-limits">{((kn && p.limits_kn) || p.limits).map((l) => <li key={l}>{l}</li>)}</ul>
            {p.basis && <p className="sp-basis">{p.basis}</p>}
            <UsefulFeedback kind="shift_plan" unit={p.unit} kn={kn} />
          </div>
        )}

        {p && (
          <footer>
            <span className="sp-said" role="status">{note}</span>
            <button type="button" onClick={copy}>{L("Copy for a briefing note", "ಬ್ರೀಫಿಂಗ್ ಟಿಪ್ಪಣಿಗೆ ನಕಲಿಸಿ")}</button>
            <button type="button" onClick={() => window.print()}>{L("Print", "ಮುದ್ರಿಸಿ")}</button>
            <button type="button" className="go" onClick={() => setPropose(true)}>{L("Propose patrol deployment", "ಗಸ್ತು ನಿಯೋಜನೆ ಪ್ರಸ್ತಾಪಿಸಿ")}</button>
          </footer>
        )}
      </MaterialPanel>

      {p && (
        <ProposeAction open={propose} onClose={() => setPropose(false)} type="patrol_redeployment" kn={kn}
                       defaults={{ zone: p.district || p.station, crime_focus: p.kinds[0]?.label || "all crimes",
                                   justification: p.text.split("\n").slice(0, 4).join(" ") }}
                       evidence={[{ label: "Shift plan", value: p.station }, ...(p.accuracy ? [{ label: "Back-test", value: p.accuracy }] : [])]} />
      )}
    </MaterialBackdrop>,
    document.body
  );
}
