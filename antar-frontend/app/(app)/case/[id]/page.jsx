"use client";
// One case, start to finish: an automated summary, the investigation timeline, how cases
// like it have ended, and the accused's other FIRs. Every line comes from GET /api/case/{id}
// (app/services/case_timeline.py), which reads the FIR row and counts the register; nothing
// here is written by a model. Only the registration is dated in the register, so later steps
// say "date not recorded" instead of showing a date.
import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useLang } from "@/components/Providers";
import "@/components/editorial-case.css";

const API = process.env.NEXT_PUBLIC_API_URL || "";

const nice = (iso) => {
  if (!iso) return "";
  const d = new Date(`${String(iso).slice(0, 10)}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
};

const STATE_WORD = {
  done: ["Done", "ಮುಗಿದಿದೆ"], current: ["Now", "ಈಗ"], pending: ["Next", "ಮುಂದೆ"], none: ["Not reached", "ತಲುಪಿಲ್ಲ"],
};

export default function CasePage() {
  const { id } = useParams();
  const sp = useSearchParams();
  const router = useRouter();
  const { lang } = useLang();
  const kn = lang === "kn";
  const L = (en, k) => (kn ? k : en);
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setData(null); setErr(null);
    const q = sp?.get("station") ? `?station=${encodeURIComponent(sp.get("station"))}` : "";
    fetch(`${API}/api/case/${encodeURIComponent(decodeURIComponent(id))}${q}`, { signal: ctrl.signal })
      .then(async (r) => {
        if (r.ok) return r.json();
        const body = await r.json().catch(() => ({}));
        throw Object.assign(new Error(body.detail || "error"), { status: r.status });
      })
      .then(setData)
      .catch((e) => { if (e.name !== "AbortError") setErr({ status: e.status, text: e.message }); });
    return () => ctrl.abort();
  }, [id, sp]);

  if (err) {
    return (
      <main className="cs-page">
        <div className="cs-wrap">
          <button type="button" className="cs-back" onClick={() => router.back()}>‹ {L("Back", "ಹಿಂದೆ")}</button>
          <h1 className="cs-title">{L("Case not available", "ಪ್ರಕರಣ ಲಭ್ಯವಿಲ್ಲ")}</h1>
          <p className="cs-lede">{err.status === 404 ? L(`No FIR ${decodeURIComponent(id)} in the register.`, `ದಾಖಲೆಯಲ್ಲಿ FIR ${decodeURIComponent(id)} ಇಲ್ಲ.`)
            : err.status === 403 ? err.text : L("The case could not be read just now.", "ಪ್ರಕರಣವನ್ನು ಈಗ ಓದಲಾಗಲಿಲ್ಲ.")}</p>
        </div>
      </main>
    );
  }
  if (!data) {
    return <main className="cs-page"><div className="cs-wrap"><p className="cs-lede" aria-busy="true">{L("Reading the case…", "ಪ್ರಕರಣ ಓದಲಾಗುತ್ತಿದೆ…")}</p></div></main>;
  }

  const c = data.counts || {};
  const sim = data.similar;
  const same = data.same_accused;
  const vb = c.victims_by || {};
  const victimsBy = [["men", "ಪುರುಷರು"], ["women", "ಮಹಿಳೆಯರು"], ["boys", "ಹುಡುಗರು"], ["girls", "ಹುಡುಗಿಯರು"]]
    .filter(([k]) => vb[k] > 0).map(([k, kk]) => `${vb[k]} ${kn ? kk : k}`);

  return (
    <main className="cs-page">
      <div className="cs-wrap">
        <div className="cs-top">
          <button type="button" className="cs-back" onClick={() => router.back()}>‹ {L("Back", "ಹಿಂದೆ")}</button>
          <button type="button" className="ui-btn ui-btn--secondary ui-btn--sm cs-print" onClick={() => window.print()}>
            {L("Print or save as PDF", "ಮುದ್ರಿಸಿ ಅಥವಾ PDF ಉಳಿಸಿ")}
          </button>
        </div>

        <header className="cs-head">
          <span className="cs-eyebrow">{L("Case", "ಪ್ರಕರಣ")} · FIR {data.fir_id}{data.crime_no ? ` · ${L("Crime no.", "ಅಪರಾಧ ಸಂ.")} ${data.crime_no}` : ""}</span>
          <h1 className="cs-title">{data.crime_head}</h1>
          <p className="cs-meta">{[data.station, data.district, `${L("registered", "ದಾಖಲು")} ${nice(data.registered)}`, data.stage].filter(Boolean).join(" · ")}</p>
          {data.demonstration && <span className="cs-demo">{L("Demonstration record, not a registered FIR", "ಪ್ರದರ್ಶನ ದಾಖಲೆ, ನೋಂದಾಯಿತ FIR ಅಲ್ಲ")}</span>}
        </header>

        <section className="cs-summary" aria-label={L("Case summary", "ಪ್ರಕರಣ ಸಾರಾಂಶ")}>
          <h2>{L("Case summary", "ಪ್ರಕರಣ ಸಾರಾಂಶ")}</h2>
          <p>{data.summary}</p>
        </section>

        <div className="cs-grid">
          <section className="cs-block">
            <h2>{L("Investigation timeline", "ತನಿಖೆಯ ಕಾಲರೇಖೆ")}</h2>
            <ol className="cs-steps">
              {data.steps.map((s) => (
                <li key={s.key} className={`cs-step ${s.state}`}>
                  <span className="dot" aria-hidden="true" />
                  <div className="body">
                    <div className="row">
                      <b>{s.title}</b>
                      <span className={`cs-state ${s.state}`}>{L(...STATE_WORD[s.state])}</span>
                    </div>
                    <span className="when">{s.date ? nice(s.date) : s.date_missing ? L("Date not recorded", "ದಿನಾಂಕ ದಾಖಲಾಗಿಲ್ಲ") : ""}</span>
                    {s.detail && <p>{s.detail}</p>}
                    {s.note && <small>{s.note}</small>}
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <div className="cs-side">
            <section className="cs-block">
              <h2>{L("In this case", "ಈ ಪ್ರಕರಣದಲ್ಲಿ")}</h2>
              <dl className="cs-facts">
                <div><dt>{L("Accused named", "ಹೆಸರಿಸಿದ ಆರೋಪಿಗಳು")}</dt><dd>{c.accused}</dd></div>
                <div><dt>{L("Arrested", "ಬಂಧಿತರು")}</dt><dd>{c.arrested}</dd></div>
                <div><dt>{L("Charge-sheeted", "ದೋಷಾರೋಪಣೆ")}</dt><dd>{c.chargesheeted}</dd></div>
                <div><dt>{L("Convicted", "ಶಿಕ್ಷೆ")}</dt><dd>{c.convicted}</dd></div>
                <div><dt>{L("Victims", "ಸಂತ್ರಸ್ತರು")}</dt><dd>{c.victims}{victimsBy.length > 0 && <small>{victimsBy.join(", ")}</small>}</dd></div>
                {data.sections?.length > 0 && <div><dt>{L("Sections", "ಸೆಕ್ಷನ್‌ಗಳು")}</dt><dd className="wrap">{data.sections.join(", ")}</dd></div>}
                {data.place && <div><dt>{L("Place", "ಸ್ಥಳ")}</dt><dd className="wrap">{data.place}</dd></div>}
                {data.io && <div><dt>{L("Investigating officer", "ತನಿಖಾಧಿಕಾರಿ")}</dt><dd className="wrap">{data.io}</dd></div>}
                {data.upi && <div><dt>{L("UPI ID on the FIR", "FIR ನಲ್ಲಿನ UPI ಐಡಿ")}</dt><dd className="wrap">
                  <button type="button" className="cs-link" onClick={() => router.push(`/search?view=money&account=${encodeURIComponent(data.upi)}`)}>{data.upi} · {L("Follow the money →", "ಹಣವನ್ನು ಅನುಸರಿಸಿ →")}</button></dd></div>}
              </dl>
            </section>

            {data.victims?.length > 0 && (
              <section className="cs-block">
                <h2>{L("Victims", "ಸಂತ್ರಸ್ತರು")}</h2>
                <ul className="cs-victims">
                  {data.victims.map((v) => (
                    <li key={v.id}>
                      <b>{v.sex}{v.age_group === "child" ? L(", child", ", ಮಗು") : ""} · {v.age_band}</b>
                      <span>{[v.occupation, v.relation ? L(`${v.relation} to the accused`, `ಆರೋಪಿಗೆ ${v.relation}`) : null].filter(Boolean).join(" · ")}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {sim && (
              <section className="cs-block">
                <h2>{L("How cases like this ended", "ಇಂತಹ ಪ್ರಕರಣಗಳು ಹೇಗೆ ಮುಗಿದವು")}</h2>
                <p className="cs-sub">{L(`${sim.cases.toLocaleString("en-IN")} other ${sim.crime_head} cases ${sim.scope === "state" ? "across Karnataka" : `at ${sim.where}`}.`,
                                          `${sim.scope === "state" ? "ಕರ್ನಾಟಕದಾದ್ಯಂತ" : sim.where} ${sim.cases.toLocaleString("en-IN")} ಇತರ ${sim.crime_head} ಪ್ರಕರಣಗಳು.`)}</p>
                <ul className="cs-bars">
                  {[[L("Reached court", "ನ್ಯಾಯಾಲಯ ತಲುಪಿದವು"), sim.reached_court],
                    [L("Still under investigation", "ಇನ್ನೂ ತನಿಖೆಯಲ್ಲಿ"), sim.still_under_investigation],
                    [L("Closed as undetected", "ಪತ್ತೆಯಾಗದೆ ಮುಚ್ಚಿದವು"), sim.undetected],
                    [L(`Convicted, of ${sim.decided} decided`, `ತೀರ್ಮಾನವಾದ ${sim.decided} ರಲ್ಲಿ ಶಿಕ್ಷೆ`), sim.convicted_of_decided]]
                    .filter(([, v]) => v != null).map(([label, v]) => (
                      <li key={label}><span>{label}</span><i style={{ "--w": `${v}%` }} /><b>{v}%</b></li>
                    ))}
                </ul>
                {sim.convicted_of_decided == null && sim.decided > 0 && (
                  <p className="cs-sub cs-few">{L(`Only ${sim.decided} of them have a verdict (${sim.convicted} convicted): too few for a conviction rate.`,
                                                   `ಅವುಗಳಲ್ಲಿ ${sim.decided} ಕ್ಕೆ ಮಾತ್ರ ತೀರ್ಪು (${sim.convicted} ಶಿಕ್ಷೆ): ಶಿಕ್ಷೆಯ ದರಕ್ಕೆ ತುಂಬಾ ಕಡಿಮೆ.`)}</p>
                )}
              </section>
            )}

            {same && same.count > 0 && (
              <section className="cs-block">
                <h2>{L("The accused's other FIRs", "ಆರೋಪಿಯ ಇತರ FIR ಗಳು")}</h2>
                <p className="cs-sub">{L(`${same.accused_id} is named in ${same.count} other ${same.count === 1 ? "FIR" : "FIRs"}${same.districts?.length ? `, in ${same.districts.join(", ")}` : ""}.`,
                                          `${same.accused_id} ಅನ್ನು ${same.count} ಇತರ FIR ಗಳಲ್ಲಿ ಹೆಸರಿಸಲಾಗಿದೆ.`)}</p>
                <ul className="cs-others">
                  {same.firs.map((f) => (
                    <li key={f.fir_id}>
                      <button type="button" onClick={() => router.push(`/case/${encodeURIComponent(f.fir_id)}`)}>
                        <b>FIR {f.fir_id}</b><span>{[nice(f.date), f.district, f.crime, f.stage].filter(Boolean).join(" · ")}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        </div>

        <p className="cs-note">{data.recorded} {L("Counts are of registered FIRs. A named accused is not a convicted person.", "ಎಣಿಕೆಗಳು ನೋಂದಾಯಿತ FIR ಗಳದ್ದು. ಹೆಸರಿಸಿದ ಆರೋಪಿ ಶಿಕ್ಷಿತ ವ್ಯಕ್ತಿಯಲ್ಲ.")}</p>
      </div>
    </main>
  );
}
