"use client";
// Case leads for the district being explained: FIRs that share a vehicle, UPI id or IP
// address; accused named here and in another district; and a near-repeat check measured
// on this district's own burglaries. Counted by /api/predict/leads - no language model -
// and each lead says what would settle it.
import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";
import { useLang } from "@/components/Providers";

const day = (iso) => {
  const x = new Date(`${iso}T00:00:00`);
  return Number.isNaN(x.getTime()) ? iso : x.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
};

export default function CaseLeads({ zone }) {
  const { lang } = useLang();
  const L = (en, kan) => (lang === "kn" ? kan : en);
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
    <section className="cl" aria-label={L("Case leads", "ಪ್ರಕರಣ ಸುಳಿವುಗಳು")}>
      <header>
        <h3>{L("Case leads", "ಪ್ರಕರಣ ಸುಳಿವುಗಳು")} · {zone}</h3>
        <p>{L("Where to look, counted from the register. A lead is not a finding; each one says what would settle it.",
              "ಎಲ್ಲಿ ನೋಡಬೇಕು, ದಾಖಲೆಯಿಂದ ಎಣಿಸಲಾಗಿದೆ. ಸುಳಿವು ಪತ್ತೆಯಲ್ಲ; ಪ್ರತಿಯೊಂದೂ ಅದನ್ನು ಏನು ದೃಢಪಡಿಸುತ್ತದೆ ಎಂದು ಹೇಳುತ್ತದೆ.")}</p>
      </header>
      {err && <p className="cl-empty">{err === "restart" ? L("Case leads need the server restarted to load them.", "ಸುಳಿವುಗಳಿಗೆ ಸರ್ವರ್ ಮರುಪ್ರಾರಂಭ ಬೇಕು.") : L("The leads could not be read just now.", "ಸುಳಿವುಗಳನ್ನು ಈಗ ಓದಲಾಗಲಿಲ್ಲ.")}</p>}
      {!d && !err && <p className="cl-empty">{L("Counting…", "ಎಣಿಸಲಾಗುತ್ತಿದೆ…")}</p>}

      {d && (
        <div className="cl-grid">
          <div className="cl-col">
            <h4>{L("FIRs that share a vehicle, UPI id or IP address", "ವಾಹನ, UPI ಐಡಿ ಅಥವಾ IP ವಿಳಾಸ ಹಂಚಿಕೊಳ್ಳುವ FIR ಗಳು")}</h4>
            {sk.leads.length === 0 ? <p className="cl-empty">{L("No FIR registered here shares one of these with another FIR.", "ಇಲ್ಲಿ ದಾಖಲಾದ ಯಾವುದೇ FIR ಇವುಗಳಲ್ಲಿ ಒಂದನ್ನು ಇನ್ನೊಂದು FIR ನೊಂದಿಗೆ ಹಂಚಿಕೊಂಡಿಲ್ಲ.")}</p> : (
              <>
                <p className="cl-count">{lang === "kn"
                  ? <>ಹಂಚಿಕೊಂಡ <b>{sk.total}</b> ವಿವರಗಳು (ವಾಹನ, ಫೋನ್, UPI ಅಥವಾ IP) ಈ ಜಿಲ್ಲೆಗೆ ಸಂಬಂಧಿಸಿವೆ; <b>{sk.specific}</b> ಕೆಲವೇ FIR ಗಳಲ್ಲಿವೆ.</>
                  : <><b>{sk.total}</b> shared {sk.total === 1 ? "detail" : "details"} (vehicle, phone, UPI or IP) touch this district; <b>{sk.specific}</b> appear on only a few FIRs.</>}</p>
                <ul className="cl-list">
                  {sk.leads.map((l) => (
                    <li key={`${l.key_type}-${l.key}`}>
                      <div className="top"><code>{l.key}</code><span>{l.key_type} · {L(`on ${l.firs} FIRs`, `${l.firs} FIR ಗಳಲ್ಲಿ`)}{l.districts.length > 1 ? L(` in ${l.districts.length} districts`, `, ${l.districts.length} ಜಿಲ್ಲೆಗಳಲ್ಲಿ`) : ""}</span></div>
                      {!l.specific && <p className="weak">{L(`On ${l.firs} FIRs: more likely a common value or a data-entry error than a real link.`, `${l.firs} FIR ಗಳಲ್ಲಿ: ನೈಜ ಸಂಪರ್ಕಕ್ಕಿಂತ ಸಾಮಾನ್ಯ ಮೌಲ್ಯ ಅಥವಾ ದಾಖಲೆ ತಪ್ಪು ಆಗಿರುವ ಸಾಧ್ಯತೆ ಹೆಚ್ಚು.`)}</p>}
                      <ol>{l.examples.map((e, i) => <li key={i}><code>{e.fir}</code> {e.crime || L("Crime head not recorded", "ಅಪರಾಧ ಶೀರ್ಷಿಕೆ ದಾಖಲಾಗಿಲ್ಲ")} · {e.station} · {day(e.date)}</li>)}</ol>
                      <p className="settle">{l.would_settle}{l.seeded ? L(" Some of these rows are seeded for the demonstration.", " ಇವುಗಳಲ್ಲಿ ಕೆಲವು ಪ್ರದರ್ಶನಕ್ಕಾಗಿ ಸೇರಿಸಿದ ಸಾಲುಗಳು.") : ""}</p>
                    </li>
                  ))}
                </ul>
                <p className="cl-note">{sk.note}</p>
              </>
            )}
          </div>

          <div className="cl-col">
            <h4>{L("Accused named here and in another district", "ಇಲ್ಲಿ ಮತ್ತು ಇನ್ನೊಂದು ಜಿಲ್ಲೆಯಲ್ಲಿ ಹೆಸರಿಸಲಾದ ಆರೋಪಿಗಳು")}</h4>
            {cb.links.length === 0 ? <p className="cl-empty">{cb.note || L("No accused is named both here and in another district.", "ಇಲ್ಲಿ ಮತ್ತು ಇನ್ನೊಂದು ಜಿಲ್ಲೆಯಲ್ಲಿ ಹೆಸರಿಸಲಾದ ಆರೋಪಿ ಇಲ್ಲ.")}</p> : (
              <ul className="cl-list">
                {cb.links.map((l) => (
                  <li key={l.with}>
                    <div className="top"><b>{l.with}</b><span>{l.accused} {L("accused", "ಆರೋಪಿಗಳು")} · {l.firs} FIR{L("s", "")}</span></div>
                    <p className="ids">{l.accused_ids.map((id) => <code key={id}>{id}</code>)}</p>
                    <p className="settle">{l.would_settle}</p>
                  </li>
                ))}
              </ul>
            )}

            <h4 className="gap">{L("After a burglary: is another nearby more likely?", "ಒಂದು ಮನೆಗಳ್ಳತನದ ನಂತರ: ಹತ್ತಿರ ಇನ್ನೊಂದರ ಸಾಧ್ಯತೆ ಹೆಚ್ಚೇ?")}</h4>
            {nr ? (
              <div className={`cl-nr${nr.supported ? " yes" : ""}`}>
                <p>{nr.text}</p>
                {nr.caution && <p className="settle">{nr.caution}</p>}
                {nr.supported && (nr.watch?.length ? (
                  <>
                    <p className="cl-count">{L(`Registered in the last ${nr.days} days, so the next days are the ones to watch nearby:`, `ಕಳೆದ ${nr.days} ದಿನಗಳಲ್ಲಿ ದಾಖಲಾದವು; ಆದ್ದರಿಂದ ಮುಂದಿನ ದಿನಗಳಲ್ಲಿ ಹತ್ತಿರ ಗಮನಿಸಬೇಕು:`)}</p>
                    <ol>{nr.watch.map((w, i) => <li key={i}><code>{w.fir}</code> {w.station} · {w.beat} · {day(w.date)}</li>)}</ol>
                  </>
                ) : <p className="settle">{L(`No burglary was registered here in the last ${nr.days} days.`, `ಕಳೆದ ${nr.days} ದಿನಗಳಲ್ಲಿ ಇಲ್ಲಿ ಯಾವುದೇ ಮನೆಗಳ್ಳತನ ದಾಖಲಾಗಿಲ್ಲ.`)}</p>)}
                <p className="settle">{L(`Measured on ${nr.basis}. Registration date, not the time of the offence.`, `${nr.basis} ಮೇಲೆ ಅಳೆಯಲಾಗಿದೆ. ದಾಖಲಾದ ದಿನಾಂಕ, ಅಪರಾಧದ ಸಮಯವಲ್ಲ.`)}</p>
              </div>
            ) : <p className="cl-empty">{L("Not measured.", "ಅಳೆಯಲಾಗಿಲ್ಲ.")}</p>}
          </div>
        </div>
      )}
    </section>
  );
}
