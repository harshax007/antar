"use client";
// Why this forecast: the engine's own arithmetic for one station or beat.
//
// The model is multiplicative, so the explanation is exact, not an estimate made after the
// fact: a usual week here, times each reason, is the forecast. Each reason also carries the
// forecast without it. Everything shown comes from /api/forecast/unit; nothing is worded
// by a language model.
import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";
import UsefulFeedback from "@/components/UsefulFeedback";
import { dateKn } from "@/lib/kn";

const LABEL = { recent: "The last 4 weeks", last_year: "The same weeks last year", neighbours: "Neighbouring stations",
                area: "The district as a whole", season: "The time of year", level: "Pull toward the district's level" };
const LABEL_KN = { recent: "ಕಳೆದ 4 ವಾರಗಳು", last_year: "ಕಳೆದ ವರ್ಷದ ಇದೇ ವಾರಗಳು", neighbours: "ಪಕ್ಕದ ಠಾಣೆಗಳು",
                   area: "ಇಡೀ ಜಿಲ್ಲೆ", season: "ವರ್ಷದ ಸಮಯ", level: "ಜಿಲ್ಲೆಯ ಮಟ್ಟದ ಕಡೆಗೆ ಎಳೆತ" };
const num = (v) => (v == null ? "—" : Number(v) >= 10 ? Math.round(v).toLocaleString("en-IN") : Number(v).toFixed(1).replace(/\.0$/, ""));
const range = (b, kn) => (b ? (b.lo === b.hi ? `${b.lo}` : kn ? `${b.lo}–${b.hi}` : `${b.lo} to ${b.hi}`) : "—");

// A server that predates the `why` block still sends the reasons and the usual level.
function fallbackWhy(f) {
  if (!f || !(f.usual > 0) || !(f.expected > 0)) return null;
  const steps = (f.drivers || []).map((d) => ({ key: d.key, label: LABEL[d.key] || d.key, factor: d.factor, notable: true, text: d.text,
                                               without: Math.round((f.expected / d.factor) * 100) / 100 }));
  return { usual: f.usual, expected: f.expected, steps, partial: true,
           plain: steps.length ? null : "Close to a usual week here: no single reason moves it by 10% or more." };
}

function Weeks({ history, ahead, kn }) {
  const past = (history || []).slice(-12);
  if (!past.length) return null;
  const a = ahead?.[0];
  const top = Math.max(1, ...past.map((w) => w.firs), a?.hi90 || 0);
  const W = 300, H = 70, n = past.length + 1, bw = W / n, y = (v) => H - (v / top) * (H - 6);
  return (
    <figure className="fw-weeks">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={kn ? `ಕಳೆದ ${past.length} ವಾರಗಳ ದಾಖಲಾದ ಪ್ರಕರಣಗಳು, ಮತ್ತು ಮುಂದಿನ ವಾರದ ಮುನ್ಸೂಚನೆ ವ್ಯಾಪ್ತಿ` : `Registered cases in the last ${past.length} weeks, and the range forecast for the week ahead`}>
        {past.map((w, i) => <rect key={w.week_start} x={i * bw + 2} y={y(w.firs)} width={bw - 4} height={H - y(w.firs)} rx="2" className="past"><title>{kn ? `${dateKn(w.week_start)} ರ ವಾರ: ${w.firs}` : `Week of ${w.week_start}: ${w.firs}`}</title></rect>)}
        {a && <>
          <rect x={past.length * bw + 2} y={y(a.hi90)} width={bw - 4} height={Math.max(2, y(a.lo90) - y(a.hi90))} rx="2" className="band90" />
          <rect x={past.length * bw + 2} y={y(a.hi80)} width={bw - 4} height={Math.max(2, y(a.lo80) - y(a.hi80))} rx="2" className="band80" />
          <line x1={past.length * bw + 2} x2={(past.length + 1) * bw - 2} y1={y(a.expected)} y2={y(a.expected)} className="mid" />
        </>}
      </svg>
      <figcaption>{kn ? `ಕಳೆದ ${past.length} ವಾರಗಳು, ನಂತರ ಮುಂದಿನ ವಾರ ವ್ಯಾಪ್ತಿಯಾಗಿ (ಗಾಢ: ಸಂಭಾವ್ಯ; ತಿಳಿ: ಬಹಳ ಸಂಭಾವ್ಯ).` : `Last ${past.length} weeks, then the week ahead as a range (darker: likely; lighter: very likely).`}</figcaption>
    </figure>
  );
}

export default function ForecastWhy({ unit, unitType = "station", kn = false }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(false);
  const [last, setLast] = useState(null);          // this station's last forecast that could be scored
  useEffect(() => {
    let alive = true;
    setD(null); setErr(false); setLast(null);
    if (unitType === "station") {
      fetchAPI(`/api/forecast/outcomes?unit=${encodeURIComponent(unit)}`)
        .then((x) => { if (alive) setLast(x?.unit || null); })
        .catch(() => {});
    }
    fetchAPI(`/api/forecast/unit/${encodeURIComponent(unit)}?unit_type=${unitType}`)
      .then((x) => { if (alive) setD(x); })
      .catch(() => { if (alive) setErr(true); });
    return () => { alive = false; };
  }, [unit, unitType]);

  if (err) return <p className="fw-note">{kn ? "ಈ ಮುನ್ಸೂಚನೆಯ ಕಾರಣಗಳನ್ನು ಈಗ ಓದಲಾಗಲಿಲ್ಲ." : "The reasons for this forecast could not be read just now."}</p>;
  if (!d) return <p className="fw-note">{kn ? "ಕಾರಣಗಳನ್ನು ಓದುತ್ತಿದೆ…" : "Reading the reasons…"}</p>;
  const f = d.forecast?.["7"];
  if (!f) return <p className="fw-note">{kn ? "ಈ ಠಾಣೆಗೆ ಮುನ್ಸೂಚನೆ ಇಲ್ಲ." : "No forecast is held for this station."}</p>;
  if (f.history === "thin") return <p className="fw-note">{(kn && f.summary_kn) || f.summary}</p>;
  const w = f.why || fallbackWhy(f);
  const lead = w?.steps?.find((s) => s.notable);
  const acc = d.accuracy;

  return (
    <div className="fw">
      {w && (
        <>
          <ol className="fw-steps">
            <li className="base"><span>{kn ? "ಇಲ್ಲಿನ ಸಾಮಾನ್ಯ ವಾರ" : "A usual week here"}</span><b>{num(w.usual)}</b></li>
            {w.steps.map((s) => (
              <li key={s.key} className={s.notable ? "on" : ""}>
                <span>{kn ? LABEL_KN[s.key] || s.label : s.label}{(kn ? s.text_kn || (s.text && s.effect) : s.text)
                  ? <small>{kn ? s.text_kn || s.effect : s.text}</small> : <small>{kn ? "ಸ್ವಲ್ಪ ಬದಲಾವಣೆ" : "little change"}</small>}</span>
                <b>×{Number(s.factor).toFixed(2)}</b>
              </li>
            ))}
            {w.partial && <li><span>{kn ? "ಇತರ ಸಣ್ಣ ಪರಿಣಾಮಗಳು" : "Other, smaller effects"}<small>{kn ? "ಪ್ರತಿಯೊಂದೂ 10% ಕ್ಕಿಂತ ಕಡಿಮೆ" : "each under 10%"}</small></span><b>×{(w.expected / (w.usual * w.steps.reduce((p, s) => p * s.factor, 1))).toFixed(2)}</b></li>}
            <li className="total"><span>{kn ? "ಮುಂದಿನ 7 ದಿನಗಳ ಮುನ್ಸೂಚನೆ" : "Forecast for the next 7 days"}<small>{kn ? `ಸಂಭಾವ್ಯ ${range(f.band80, true)}, ಬಹಳ ಸಂಭಾವ್ಯ ${range(f.band90, true)}` : `likely ${range(f.band80)}, very likely ${range(f.band90)}`}</small></span><b>{num(w.expected)}</b></li>
          </ol>
          {w.plain && <p className="fw-note">{(kn && w.plain_kn) || w.plain}</p>}
          {lead && (kn ? (
            <p className="fw-cf">
              <b>ಯಾವುದು ಇದನ್ನು ಬದಲಿಸುತ್ತದೆ.</b> {lead.key === "recent" ? "ಕಳೆದ 4 ವಾರಗಳು ಸಾಮಾನ್ಯವಾಗಿದ್ದರೆ" : `"${LABEL_KN[lead.key] || lead.label}" ಇಲ್ಲದಿದ್ದರೆ`},
              ಮುನ್ಸೂಚನೆ {num(w.expected)} ಅಲ್ಲ, {num(lead.without)} ಆಗುತ್ತಿತ್ತು.
            </p>
          ) : (
            <p className="fw-cf">
              <b>What would change it.</b> {lead.label === LABEL.recent || lead.key === "recent" ? "Had the last 4 weeks been usual" : `Without "${lead.label.toLowerCase()}"`},
              the forecast would be {num(lead.without)}, not {num(w.expected)}.
            </p>
          ))}
          {w.reconciles === false && <p className="fw-note">{kn ? "ಈ ಕಾರಣಗಳ ಗುಣಲಬ್ಧ ತೋರಿಸಿದ ಮುನ್ಸೂಚನೆಗೆ ಸಮವಾಗಿಲ್ಲ. ಈ ವಿಭಜನೆಯನ್ನು ಅಪೂರ್ಣ ಎಂದು ಪರಿಗಣಿಸಿ." : "These reasons do not multiply to the forecast shown. Treat this breakdown as incomplete."}</p>}
        </>
      )}
      <Weeks history={d.history} ahead={d.ahead} kn={kn} />
      {acc && (kn ? (
        <p className="fw-acc">
          <b>ಎಷ್ಟು ನಂಬಬಹುದು.</b> ನೈಜ ದಾಖಲೆಯ {acc.weeks} ವಾರಗಳಲ್ಲಿ ಪರೀಕ್ಷಿಸಲಾಗಿದೆ: ಸಂಭಾವ್ಯ ವ್ಯಾಪ್ತಿ {Math.round((acc.coverage80 || 0) * 100)}% ಬಾರಿ ಸರಿಯಾಯಿತು,
          ಮತ್ತು ಈ ಮುನ್ಸೂಚನೆಯಿಂದ ಠಾಣೆಗಳ ಶ್ರೇಣಿ {acc.weeks} ರಲ್ಲಿ {acc.weeks_better_than_last4} ವಾರ ಕಳೆದ 4 ವಾರಗಳ ಶ್ರೇಣಿಗಿಂತ ಉತ್ತಮವಾಗಿತ್ತು.
        </p>
      ) : (
        <p className="fw-acc">
          <b>How far to trust it.</b> Tested on {acc.weeks} weeks of the real record: the likely range held {Math.round((acc.coverage80 || 0) * 100)}% of the time,
          and ranking stations by this forecast beat ranking them by their last 4 weeks in {acc.weeks_better_than_last4} of {acc.weeks} weeks.
          {d.track_record?.text ? ` ${d.track_record.text}` : ""}
        </p>
      ))}
      {last && (kn
        ? <p className="fw-acc"><b>ಬಳಕೆಯಲ್ಲಿ.</b> ಹಿಂದಿನ ವಾರ: ಮುನ್ಸೂಚನೆ {String(last.likely || "").replace(" to ", "–")}, ದಾಖಲಾದದ್ದು {last.recorded}. {last.held ? "ಸಂಭಾವ್ಯ ವ್ಯಾಪ್ತಿಯೊಳಗೆ." : "ಸಂಭಾವ್ಯ ವ್ಯಾಪ್ತಿಯ ಹೊರಗೆ."}</p>
        : <p className="fw-acc"><b>In use.</b> {last.text} {last.held ? "Inside the likely range." : "Outside the likely range."}</p>)}
      <p className="fw-limit">{kn ? "ಇದು ದಾಖಲಾದ FIR ಗಳ ಮುನ್ಸೂಚನೆ, ಅಪರಾಧದ್ದಲ್ಲ. ಹೆಚ್ಚು ಪೊಲೀಸಿಂಗ್ ಇರುವಲ್ಲಿ ಹೆಚ್ಚು ದಾಖಲಾಗುತ್ತದೆ." : "A forecast of registered FIRs, not of crime. Where more is policed, more is registered."}</p>
      <UsefulFeedback kind="forecast" unit={unit} kn={kn} />
    </div>
  );
}
