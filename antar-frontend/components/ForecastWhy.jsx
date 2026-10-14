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

const LABEL = { recent: "The last 4 weeks", last_year: "The same weeks last year", neighbours: "Neighbouring stations",
                area: "The district as a whole", season: "The time of year", level: "Pull toward the district's level" };
const num = (v) => (v == null ? "—" : Number(v) >= 10 ? Math.round(v).toLocaleString("en-IN") : Number(v).toFixed(1).replace(/\.0$/, ""));
const range = (b) => (b ? (b.lo === b.hi ? `${b.lo}` : `${b.lo} to ${b.hi}`) : "—");

// A server that predates the `why` block still sends the reasons and the usual level.
function fallbackWhy(f) {
  if (!f || !(f.usual > 0) || !(f.expected > 0)) return null;
  const steps = (f.drivers || []).map((d) => ({ key: d.key, label: LABEL[d.key] || d.key, factor: d.factor, notable: true, text: d.text,
                                               without: Math.round((f.expected / d.factor) * 100) / 100 }));
  return { usual: f.usual, expected: f.expected, steps, partial: true,
           plain: steps.length ? null : "Close to a usual week here: no single reason moves it by 10% or more." };
}

function Weeks({ history, ahead }) {
  const past = (history || []).slice(-12);
  if (!past.length) return null;
  const a = ahead?.[0];
  const top = Math.max(1, ...past.map((w) => w.firs), a?.hi90 || 0);
  const W = 300, H = 70, n = past.length + 1, bw = W / n, y = (v) => H - (v / top) * (H - 6);
  return (
    <figure className="fw-weeks">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Registered cases in the last ${past.length} weeks, and the range forecast for the week ahead`}>
        {past.map((w, i) => <rect key={w.week_start} x={i * bw + 2} y={y(w.firs)} width={bw - 4} height={H - y(w.firs)} rx="2" className="past"><title>{`Week of ${w.week_start}: ${w.firs}`}</title></rect>)}
        {a && <>
          <rect x={past.length * bw + 2} y={y(a.hi90)} width={bw - 4} height={Math.max(2, y(a.lo90) - y(a.hi90))} rx="2" className="band90" />
          <rect x={past.length * bw + 2} y={y(a.hi80)} width={bw - 4} height={Math.max(2, y(a.lo80) - y(a.hi80))} rx="2" className="band80" />
          <line x1={past.length * bw + 2} x2={(past.length + 1) * bw - 2} y1={y(a.expected)} y2={y(a.expected)} className="mid" />
        </>}
      </svg>
      <figcaption>Last {past.length} weeks, then the week ahead as a range (darker: likely; lighter: very likely).</figcaption>
    </figure>
  );
}

export default function ForecastWhy({ unit, unitType = "station" }) {
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

  if (err) return <p className="fw-note">The reasons for this forecast could not be read just now.</p>;
  if (!d) return <p className="fw-note">Reading the reasons…</p>;
  const f = d.forecast?.["7"];
  if (!f) return <p className="fw-note">No forecast is held for this station.</p>;
  if (f.history === "thin") return <p className="fw-note">{f.summary}</p>;
  const w = f.why || fallbackWhy(f);
  const lead = w?.steps?.find((s) => s.notable);
  const acc = d.accuracy;

  return (
    <div className="fw">
      {w && (
        <>
          <ol className="fw-steps">
            <li className="base"><span>A usual week here</span><b>{num(w.usual)}</b></li>
            {w.steps.map((s) => (
              <li key={s.key} className={s.notable ? "on" : ""}>
                <span>{s.label}{s.text ? <small>{s.text}</small> : <small>little change</small>}</span>
                <b>×{Number(s.factor).toFixed(2)}</b>
              </li>
            ))}
            {w.partial && <li><span>Other, smaller effects<small>each under 10%</small></span><b>×{(w.expected / (w.usual * w.steps.reduce((p, s) => p * s.factor, 1))).toFixed(2)}</b></li>}
            <li className="total"><span>Forecast for the next 7 days<small>likely {range(f.band80)}, very likely {range(f.band90)}</small></span><b>{num(w.expected)}</b></li>
          </ol>
          {w.plain && <p className="fw-note">{w.plain}</p>}
          {lead && (
            <p className="fw-cf">
              <b>What would change it.</b> {lead.label === LABEL.recent || lead.key === "recent" ? "Had the last 4 weeks been usual" : `Without "${lead.label.toLowerCase()}"`},
              the forecast would be {num(lead.without)}, not {num(w.expected)}.
            </p>
          )}
          {w.reconciles === false && <p className="fw-note">These reasons do not multiply to the forecast shown. Treat this breakdown as incomplete.</p>}
        </>
      )}
      <Weeks history={d.history} ahead={d.ahead} />
      {acc && (
        <p className="fw-acc">
          <b>How far to trust it.</b> Tested on {acc.weeks} weeks of the real record: the likely range held {Math.round((acc.coverage80 || 0) * 100)}% of the time,
          and ranking stations by this forecast beat ranking them by their last 4 weeks in {acc.weeks_better_than_last4} of {acc.weeks} weeks.
          {d.track_record?.text ? ` ${d.track_record.text}` : ""}
        </p>
      )}
      {last && <p className="fw-acc"><b>In use.</b> {last.text} {last.held ? "Inside the likely range." : "Outside the likely range."}</p>}
      <p className="fw-limit">A forecast of registered FIRs, not of crime. Where more is policed, more is registered.</p>
      <UsefulFeedback kind="forecast" unit={unit} />
    </div>
  );
}
