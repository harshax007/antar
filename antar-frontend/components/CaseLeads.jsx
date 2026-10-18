"use client";
// Case leads for the district being explained: FIRs that share a vehicle, UPI id or IP
// address; accused named here and in another district; and a near-repeat check measured
// on this district's own burglaries. Counted by /api/predict/leads - no language model -
// and each lead says what would settle it.
import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";

const day = (iso) => {
  const x = new Date(`${iso}T00:00:00`);
  return Number.isNaN(x.getTime()) ? iso : x.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
};

export default function CaseLeads({ zone }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    setD(null); setErr(null);
    if (!zone) return;
    let alive = true;
    fetchAPI(`/api/predict/leads?zone=${encodeURIComponent(zone)}`)
      .then((x) => { if (alive) setD(x); })
      .catch((e) => { if (alive) setErr(e?.status === 404 ? "restart" : "failed"); });
    return () => { alive = false; };
  }, [zone]);

  if (!zone) return null;
  const sk = d?.shared_keys, cb = d?.cross_border, nr = d?.near_repeat;

  return (
    <section className="cl" aria-label="Case leads">
      <header>
        <h3>Case leads · {zone}</h3>
        <p>Where to look, counted from the register. A lead is not a finding; each one says what would settle it.</p>
      </header>
      {err && <p className="cl-empty">{err === "restart" ? "Case leads need the server restarted to load them." : "The leads could not be read just now."}</p>}
      {!d && !err && <p className="cl-empty">Counting…</p>}

      {d && (
        <div className="cl-grid">
          <div className="cl-col">
            <h4>FIRs that share a vehicle, UPI id or IP address</h4>
            {sk.leads.length === 0 ? <p className="cl-empty">No FIR registered here shares one of these with another FIR.</p> : (
              <>
                <p className="cl-count"><b>{sk.total}</b> shared {sk.total === 1 ? "detail" : "details"} (vehicle, phone, UPI or IP) touch this district; <b>{sk.specific}</b> appear on only a few FIRs.</p>
                <ul className="cl-list">
                  {sk.leads.map((l) => (
                    <li key={`${l.key_type}-${l.key}`}>
                      <div className="top"><code>{l.key}</code><span>{l.key_type} · on {l.firs} FIRs{l.districts.length > 1 ? ` in ${l.districts.length} districts` : ""}</span></div>
                      {!l.specific && <p className="weak">On {l.firs} FIRs: more likely a common value or a data-entry error than a real link.</p>}
                      <ol>{l.examples.map((e, i) => <li key={i}><code>{e.fir}</code> {e.crime || "Crime head not recorded"} · {e.station} · {day(e.date)}</li>)}</ol>
                      <p className="settle">{l.would_settle}{l.seeded ? " Some of these rows are seeded for the demonstration." : ""}</p>
                    </li>
                  ))}
                </ul>
                <p className="cl-note">{sk.note}</p>
              </>
            )}
          </div>

          <div className="cl-col">
            <h4>Accused named here and in another district</h4>
            {cb.links.length === 0 ? <p className="cl-empty">{cb.note || "No accused is named both here and in another district."}</p> : (
              <ul className="cl-list">
                {cb.links.map((l) => (
                  <li key={l.with}>
                    <div className="top"><b>{l.with}</b><span>{l.accused} accused · {l.firs} FIRs</span></div>
                    <p className="ids">{l.accused_ids.map((id) => <code key={id}>{id}</code>)}</p>
                    <p className="settle">{l.would_settle}</p>
                  </li>
                ))}
              </ul>
            )}

            <h4 className="gap">After a burglary: is another nearby more likely?</h4>
            {nr ? (
              <div className={`cl-nr${nr.supported ? " yes" : ""}`}>
                <p>{nr.text}</p>
                {nr.caution && <p className="settle">{nr.caution}</p>}
                {nr.supported && (nr.watch?.length ? (
                  <>
                    <p className="cl-count">Registered in the last {nr.days} days, so the next days are the ones to watch nearby:</p>
                    <ol>{nr.watch.map((w, i) => <li key={i}><code>{w.fir}</code> {w.station} · {w.beat} · {day(w.date)}</li>)}</ol>
                  </>
                ) : <p className="settle">No burglary was registered here in the last {nr.days} days.</p>)}
                <p className="settle">Measured on {nr.basis}. Registration date, not the time of the offence.</p>
              </div>
            ) : <p className="cl-empty">Not measured.</p>}
          </div>
        </div>
      )}
    </section>
  );
}
