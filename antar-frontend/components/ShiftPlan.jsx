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

const day = (iso) => {
  const x = new Date(`${iso}T00:00:00`);
  return Number.isNaN(x.getTime()) ? iso : x.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
};

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

  const flash = (t) => { setNote(t); setTimeout(() => setNote(""), 2400); };
  const copy = async () => { try { await navigator.clipboard.writeText(p.text); flash("Copied"); } catch { flash("Copy is not available here."); } };
  const max = p ? Math.max(1, ...p.days.by_day.map((d) => d.firs)) : 1;

  return createPortal(
    <div className="sp-back" role="dialog" aria-modal="true" aria-label={`Shift plan for ${station}`}
         onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <section className="sp">
        <header>
          <div>
            <span className="sp-eyebrow">Shift plan</span>
            <h3>{p?.station || station}</h3>
            {p?.district && <p>{p.district} · next 7 days</p>}
          </div>
          <button type="button" className="sp-x" onClick={onClose} aria-label="Close this window" title="Close"><X size={18} /></button>
        </header>

        {err && <p className="sp-empty">{err === "restart" ? "The shift plan needs the server restarted to load it." : "The plan could not be read just now. Try again."}</p>}
        {!p && !err && <p className="sp-empty">Putting the plan together from the records…</p>}

        {p && (
          <div className="sp-body">
            {p.forecast && !p.forecast.thin ? (
              <div className="sp-top">
                <b>{p.forecast.likely}</b>
                <div>
                  <span>FIRs likely in the next 7 days</span>
                  <em>very likely {p.forecast.very_likely}; a usual week here is {Number(p.forecast.usual).toFixed(1)}</em>
                </div>
              </div>
            ) : <p className="sp-empty">Too little history here for a reliable forecast.</p>}

            <dl className="sp-rows">
              <div>
                <dt>Beats to cover first</dt>
                <dd>{p.beats.length ? (
                  <ol>{p.beats.map((b) => <li key={b.unit}><b>{b.name}</b> likely {b.likely}{b.reason && <small>{b.reason}</small>}</li>)}</ol>
                ) : "The forecast does not separate this station's beats."}</dd>
              </div>
              <div>
                <dt>Kinds of case expected</dt>
                <dd>{p.kinds.length ? p.kinds.map((k) => `${k.label} (${k.likely})`).join(", ") : "No kind of case is expected more than now and then."}</dd>
              </div>
              <div>
                <dt>Days of the week</dt>
                <dd>{p.days.text}
                  {p.days.firs >= 60 && (
                    <span className="sp-days" aria-hidden="true">
                      {p.days.by_day.map((d) => <i key={d.day} className={p.days.stands_out.includes(d.day) ? "on" : ""} title={`${d.day}: ${d.firs}`}>
                        <u style={{ height: `${Math.max(2, Math.round((d.firs / max) * 36))}px` }} /><s>{d.day[0]}</s></i>)}
                    </span>
                  )}
                  <small>By the day an FIR was registered. The register does not hold the hour.</small>
                </dd>
              </div>
              <div>
                <dt>Still open here</dt>
                <dd>{p.open_cases.total ? (
                  <>
                    <b>{p.open_cases.total.toLocaleString("en-IN")}</b> FIRs{p.open_cases.in_listed_beats ? `, ${p.open_cases.in_listed_beats} in the beats above` : ""}
                    <small>{p.open_cases.definition}</small>
                    <ul className="sp-open">{p.open_cases.newest.map((c, i) => (
                      <li key={`${c.fir}-${i}`}><code>{c.fir || "no number"}</code><span>{c.crime} · {c.beat}</span><time>{day(c.date)}</time></li>
                    ))}</ul>
                  </>
                ) : "No FIR from the past year is under investigation without a charge-sheet."}</dd>
              </div>
              {p.events.map((e) => (
                <div key={e.name}>
                  <dt>{e.name}</dt>
                  <dd>{e.when}.{e.effect ? ` ${e.effect}` : ""}
                    {e.watch?.length > 0 && <small>Less certain: {e.watch.join(", ")}.</small>}</dd>
                </div>
              ))}
            </dl>

            {p.accuracy && <p className="sp-acc"><b>How far to trust it.</b> {p.accuracy}</p>}
            <ul className="sp-limits">{p.limits.map((l) => <li key={l}>{l}</li>)}</ul>
            {p.basis && <p className="sp-basis">{p.basis}</p>}
          </div>
        )}

        {p && (
          <footer>
            <span className="sp-said" role="status">{note}</span>
            <button type="button" onClick={copy}>Copy for a briefing note</button>
            <button type="button" onClick={() => window.print()}>Print</button>
            <button type="button" className="go" onClick={() => setPropose(true)}>Propose patrol deployment</button>
          </footer>
        )}
      </section>

      {p && (
        <ProposeAction open={propose} onClose={() => setPropose(false)} type="patrol_redeployment" kn={kn}
                       defaults={{ zone: p.district || p.station, crime_focus: p.kinds[0]?.label || "all crimes",
                                   justification: p.text.split("\n").slice(0, 4).join(" ") }}
                       evidence={[{ label: "Shift plan", value: p.station }, ...(p.accuracy ? [{ label: "Back-test", value: p.accuracy }] : [])]} />
      )}
    </div>,
    document.body
  );
}
