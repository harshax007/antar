"use client";
// Social insights: how crime across Karnataka's 30 districts lines up with social indicators
// (Census 2011, NFHS-5), and who the victims are. Data from /api/social/indicators
// (app/services/social_indicators.py) and /api/social/demographics. Every link is a district-
// level rank correlation, shown with its number, with urbanisation held constant, and with
// what it cannot say.
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import BrainLoader from "@/components/BrainLoader";
import { useLang } from "@/components/Providers";
import "@/components/editorial-social.css";

const API = process.env.NEXT_PUBLIC_API_URL || "";
const fmt = (v, unit) => (v == null ? "–" : unit === "people" ? Number(v).toLocaleString("en-IN") : `${Number(v).toLocaleString("en-IN", { maximumFractionDigits: 1 })}${unit === "%" ? "%" : ""}`);
const CAT_KN = { all: "ಎಲ್ಲ ಅಪರಾಧ", property: "ಆಸ್ತಿ ಅಪರಾಧ", violent: "ಹಿಂಸಾತ್ಮಕ ಅಪರಾಧ", women: "ಮಹಿಳೆಯರ ವಿರುದ್ಧ ಅಪರಾಧ", fraud: "ವಂಚನೆ ಮತ್ತು ಸೈಬರ್", road: "ರಸ್ತೆ ಅಪಘಾತ" };
const TABLE_COLS = ["urban_pct", "literacy_2011", "women_10y_school", "child_marriage", "clean_fuel", "men_alcohol"];

function Bars({ rows, total }) {
  if (!rows?.length) return null;
  const max = Math.max(...rows.map((r) => r.n), 1);
  return (
    <ul className="so-bars">
      {rows.slice(0, 8).map((r) => (
        <li key={r.label}><span>{String(r.label).replace(/_/g, " ")}</span><i style={{ "--w": `${(r.n / max) * 100}%` }} /><b>{total ? `${Math.round((r.n / total) * 100)}%` : r.n.toLocaleString("en-IN")}</b></li>
      ))}
    </ul>
  );
}

// The loader the Map uses, with this screen's own steps
const SOCIAL_STEPS = {
  en: ["Reading the 30 districts' social indicators", "Lining them up with each district's crime", "Measuring which ones move together", "Counting victims by sex, age and occupation", "Almost ready"],
  kn: ["30 ಜಿಲ್ಲೆಗಳ ಸಾಮಾಜಿಕ ಸೂಚಕಗಳನ್ನು ಓದಲಾಗುತ್ತಿದೆ", "ಪ್ರತಿ ಜಿಲ್ಲೆಯ ಅಪರಾಧದೊಂದಿಗೆ ಹೋಲಿಸಲಾಗುತ್ತಿದೆ", "ಯಾವುವು ಜೊತೆಯಾಗಿ ಬದಲಾಗುತ್ತವೆ ಎಂದು ಅಳೆಯಲಾಗುತ್ತಿದೆ", "ಸಂತ್ರಸ್ತರನ್ನು ಲಿಂಗ, ವಯಸ್ಸು, ಉದ್ಯೋಗದ ಪ್ರಕಾರ ಎಣಿಸಲಾಗುತ್ತಿದೆ", "ಬಹುತೇಕ ಸಿದ್ಧ"],
};
const SOCIAL_ORBS = ["searching", "connecting", "solving", "searching", "working"];

const median = (a) => { const v = a.filter((x) => x != null).sort((p, q) => p - q); const n = v.length; return n ? (n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2) : null; };
// A round axis that starts near the data, not at a tick far below it
const niceDomain = (vals) => {
  const v = vals.filter((x) => x != null); if (!v.length) return ["auto", "auto"];
  const lo = Math.min(...v), hi = Math.max(...v), pad = (hi - lo || 1) * 0.08;
  const step = Math.pow(10, Math.floor(Math.log10(hi - lo || 1))) / 2;
  return [Math.floor((lo - pad) / step) * step, Math.ceil((hi + pad) / step) * step];
};
// Straight-line fit, drawn as a guide to the direction, not as a forecast
const fit = (pts) => {
  const v = pts.filter((p) => p.x != null && p.y != null); const n = v.length; if (n < 3) return null;
  const mx = v.reduce((a, p) => a + p.x, 0) / n, my = v.reduce((a, p) => a + p.y, 0) / n;
  const sxx = v.reduce((a, p) => a + (p.x - mx) ** 2, 0); if (!sxx) return null;
  const b = v.reduce((a, p) => a + (p.x - mx) * (p.y - my), 0) / sxx;
  return { b, a: my - b * mx };
};
// How strong a rank correlation reads, in plain words
const strength = (r, kn) => { const a = Math.abs(r); return a >= 0.5 ? (kn ? "ಬಲವಾದ" : "Strong") : a >= 0.3 ? (kn ? "ಮಧ್ಯಮ" : "Moderate") : (kn ? "ದುರ್ಬಲ" : "Weak"); };

function Dot(props) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null) return null;
  const tone = payload.tag === "high" ? "#22E6F0" : payload.tag === "low" ? "#A78BFA" : "rgba(148,163,184,.55)";
  return (
    <g className="so-dot">
      {payload.tag === "high" && <circle cx={cx} cy={cy} r={11} fill="#22E6F0" opacity={0.12} />}
      <circle cx={cx} cy={cy} r={payload.tag ? 6 : 4.5} fill={tone} stroke={payload.hl ? "#fff" : "#060910"} strokeWidth={payload.hl ? 1.5 : 1} />
      {payload.name && <text x={cx + (payload.lpos === "left" ? -10 : payload.edge ? 6 : payload.lpos === "below" ? 0 : 10)} y={cy + (payload.lpos === "below" ? 16 : payload.lpos === "above" ? -10 : 4)}
        textAnchor={payload.lpos === "left" || payload.edge ? "end" : payload.lpos === "below" || payload.lpos === "above" ? "middle" : "start"}
        fill="#CBD5E1" fontSize={11} fontWeight={500} style={{ paintOrder: "stroke", stroke: "#060910", strokeWidth: 3 }}>{payload.name}</text>}
    </g>
  );
}

// What Chat is asked when an officer wants a link explained, by kind of crime
const ASK = {
  all: "Which social factors go with crime?", property: "Which social factors go with property crime?",
  violent: "Which social factors go with violent crime?", women: "Is alcohol linked to crimes against women?",
  fraud: "Which social factors go with fraud and cyber crime?", road: "Which social factors go with road accidents?",
};

export default function SocialInsights() {
  const router = useRouter();
  const { lang } = useLang();
  const kn = lang === "kn";
  const L = (en, k) => (kn ? k : en);
  const [d, setD] = useState(null);
  const [demo, setDemo] = useState(null);
  const [err, setErr] = useState(null);
  const [cat, setCat] = useState("all");
  const [ind, setInd] = useState(null);
  const [sort, setSort] = useState({ key: "rate", dir: -1 });
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/social/indicators`).then((r) => (r.ok ? r.json() : Promise.reject(r.status))).then(setD).catch((e) => setErr(e));
    fetch(`${API}/api/social/demographics`).then((r) => (r.ok ? r.json() : null)).then(setDemo).catch(() => {});
  }, []);

  const links = d?.correlations?.[cat]?.links || [];
  const clear = links.filter((l) => l.significant);
  const none = links.filter((l) => !l.significant);
  const meta = useMemo(() => Object.fromEntries((d?.indicators || []).map((m) => [m.key, m])), [d]);
  const indKey = ind || clear[0]?.key || "urban_pct";
  const link = links.find((l) => l.key === indKey);

  const points = useMemo(() => {
    const ps = (d?.table || []).map((r) => ({ district: r.district, x: r[indKey], y: r.rates[cat], hl: r.district === "Bengaluru Urban" })).filter((p) => p.x != null && p.y != null);
    // name the three highest rates and the lowest, so the eye knows where to look
    const byY = [...ps].sort((a, b) => b.y - a.y);
    byY.slice(0, 3).forEach((p) => { p.tag = "high"; });
    if (byY.length > 4) byY[byY.length - 1].tag = "low";
    ps.forEach((p) => { p.name = p.tag ? p.district : ""; p.y = Math.round(p.y * 10) / 10; });
    // names that would sit on top of each other: the lower one goes beneath its dot
    const xs = ps.map((p) => p.x), ys = ps.map((p) => p.y);
    const xr = (Math.max(...xs) - Math.min(...xs)) || 1, yr = (Math.max(...ys) - Math.min(...ys)) || 1;
    const named = ps.filter((p) => p.name).sort((a, b) => b.y - a.y);
    named.forEach((p, i) => {
      if (named.slice(0, i).some((q) => Math.abs(q.x - p.x) / xr < 0.25 && Math.abs(q.y - p.y) / yr < 0.08)) p.lpos = "below";
      p.edge = (p.x - Math.min(...xs)) / xr > 0.8;
      if (p.edge && !p.lpos) p.lpos = "left";
    });
    return ps;
  }, [d, indKey, cat]);
  const chart = useMemo(() => {
    const mx = median(points.map((p) => p.x)), my = median(points.map((p) => p.y));
    const unit = meta[indKey]?.unit;
    let xd = niceDomain(points.map((p) => p.x));
    if (unit === "%") xd = [Math.max(0, xd[0]), Math.min(100, xd[1])];
    const yd = [0, niceDomain(points.map((p) => p.y))[1]];
    const f = fit(points);
    const line = f ? [{ x: xd[0], y: f.a + f.b * xd[0] }, { x: xd[1], y: f.a + f.b * xd[1] }] : null;
    const top = [...points].sort((a, b) => b.y - a.y)[0];
    return { mx, my, xd, yd, line, top };
  }, [points, meta, indKey]);
  const table = useMemo(() => {
    const rows = [...(d?.table || [])];
    const val = (r) => (sort.key === "rate" ? r.rates[cat] : sort.key === "district" ? r.district : r[sort.key]);
    rows.sort((a, b) => (val(a) > val(b) ? 1 : val(a) < val(b) ? -1 : 0) * sort.dir);
    return rows;
  }, [d, cat, sort]);

  if (err) return <main className="so-page"><div className="so-wrap"><h1 className="so-title">{L(<>Search · <em>Social Insights</em></>, <>ಹುಡುಕಾಟ · <em>ಸಾಮಾಜಿಕ ಒಳನೋಟಗಳು</em></>)}</h1><p className="so-lede">{L("The district figures could not be read just now.", "ಜಿಲ್ಲಾ ಅಂಕಿಅಂಶಗಳನ್ನು ಈಗ ಓದಲಾಗಲಿಲ್ಲ.")}</p></div></main>;
  if (!d) return <main className="so-page is-loading" style={{ position: "relative" }}><BrainLoader kn={kn} steps={SOCIAL_STEPS} orbs={SOCIAL_ORBS} /></main>;

  const head = (key, label) => (
    <th key={key} scope="col"><button type="button" onClick={() => setSort((s) => ({ key, dir: s.key === key ? -s.dir : -1 }))} aria-sort={sort.key === key ? (sort.dir < 0 ? "descending" : "ascending") : "none"}>
      {label}{sort.key === key ? (sort.dir < 0 ? " ↓" : " ↑") : ""}</button></th>
  );
  const vic = demo?.victims;
  const vTotal = vic?.gender?.reduce((a, r) => a + r.n, 0);

  return (
    <main className="so-page">
      <div className="so-wrap">
        {/* heading on the left, its limits on the right */}
        <header className="so-head so-head--split">
          <div className="so-head-l">
          <h1 className="so-title">{L(<>Search · <em>Social Insights</em></>, <>ಹುಡುಕಾಟ · <em>ಸಾಮಾಜಿಕ ಒಳನೋಟಗಳು</em></>)}</h1>
          <p className="so-lede">{L(`How crime rates in Karnataka's ${d.districts} districts move with urbanisation, education, child marriage, household amenities and alcohol use. These are links between districts, not causes, and never a reason to target a group.`,
                                   `ಕರ್ನಾಟಕದ ${d.districts} ಜಿಲ್ಲೆಗಳ ಅಪರಾಧ ದರಗಳು ನಗರೀಕರಣ, ಶಿಕ್ಷಣ, ಬಾಲ್ಯ ವಿವಾಹ, ಗೃಹ ಸೌಲಭ್ಯ ಮತ್ತು ಮದ್ಯಪಾನದೊಂದಿಗೆ ಹೇಗೆ ಬದಲಾಗುತ್ತವೆ. ಇವು ಸಂಬಂಧಗಳು, ಕಾರಣಗಳಲ್ಲ; ಯಾವುದೇ ಗುಂಪನ್ನು ಗುರಿಯಾಗಿಸಲು ಆಧಾರವಲ್ಲ.`)}</p>
          </div>
          <div className="so-caveats">
            <h2>{L("What this cannot tell you", "ಇದು ಹೇಳಲಾಗದ್ದು")}</h2>
            <p>{d.caveats[0]}</p>
            {d.caveats.length > 1 && (
              <details>
                <summary>{L(`${d.caveats.length - 1} more limits`, `ಇನ್ನೂ ${d.caveats.length - 1} ಮಿತಿಗಳು`)}</summary>
                <ul>{d.caveats.slice(1).map((c) => <li key={c}>{c}</li>)}</ul>
              </details>
            )}
          </div>
        </header>

        <nav className="so-cats" role="tablist" aria-label={L("Kind of crime", "ಅಪರಾಧದ ಪ್ರಕಾರ")}>
          {Object.entries(d.categories).map(([k, v]) => (
            <button key={k} role="tab" aria-selected={cat === k} className={cat === k ? "on" : ""} onClick={() => { setCat(k); setInd(null); }}>{kn ? CAT_KN[k] : v}</button>
          ))}
        </nav>

        <div className="so-grid">
          <section className="so-block">
            <h2><span className="so-n">01</span>{L("Clear links", "ಸ್ಪಷ್ಟ ಸಂಬಂಧಗಳು")} <em>{clear.length}</em></h2>
            {clear.length === 0 && <p className="so-sub">{L("No indicator lines up clearly with this kind of crime across districts.", "ಯಾವುದೇ ಸೂಚಕ ಸ್ಪಷ್ಟವಾಗಿ ಹೊಂದುವುದಿಲ್ಲ.")}</p>}
            <ol className="so-links">
              {clear.map((l) => (
                <li key={l.key} className={l.key === indKey ? "on" : ""}>
                  <button type="button" onClick={() => setInd(l.key)}>
                    <span className="row">
                      <b>{l.sentence}</b>
                      <em className={l.spearman > 0 ? "up" : "down"}>ρ {l.spearman > 0 ? "+" : ""}{l.spearman.toFixed(2)}</em>
                    </span>
                    <span className="meta">
                      p {l.p < 0.001 ? "< 0.001" : `= ${l.p.toFixed(3)}`}
                      {l.partial_urban != null && (l.holds_without_urban
                        ? L(` · holds with urbanisation held constant (ρ ${l.partial_urban.toFixed(2)})`, ` · ನಗರೀಕರಣ ಸ್ಥಿರವಾಗಿಟ್ಟರೂ ಉಳಿಯುತ್ತದೆ`)
                        : L(" · fades once urbanisation is held constant", " · ನಗರೀಕರಣ ಸ್ಥಿರವಾಗಿಟ್ಟಾಗ ಮಾಯವಾಗುತ್ತದೆ"))}
                      {` · ${l.source.split(" (")[0]}, ${l.year}`}
                    </span>
                    {l.reading && <span className="reading">{l.reading}</span>}
                  </button>
                </li>
              ))}
            </ol>
            {none.length > 0 && (
              <>
                <button type="button" className="so-more" onClick={() => setShowAll((v) => !v)} aria-expanded={showAll}>
                  {showAll ? L("Hide", "ಮರೆಮಾಡಿ") : L(`No clear link: ${none.length} indicators`, `ಸ್ಪಷ್ಟ ಸಂಬಂಧವಿಲ್ಲ: ${none.length}`)}
                </button>
                {showAll && <ul className="so-none">{none.map((l) => <li key={l.key}><button type="button" onClick={() => setInd(l.key)}>{l.label}</button><span>ρ {l.spearman.toFixed(2)}, p {l.p.toFixed(2)}</span></li>)}</ul>}
              </>
            )}
          </section>

          <section className="so-block">
            <h2><span className="so-n">02</span>{L("Each district", "ಪ್ರತಿ ಜಿಲ್ಲೆ")}</h2>
            <label className="so-pick">
              <span>{L("Indicator", "ಸೂಚಕ")}</span>
              <select value={indKey} onChange={(e) => setInd(e.target.value)}>
                {d.indicators.filter((m) => m.key !== "population_2011").map((m) => <option key={m.key} value={m.key}>{m.label} ({m.year})</option>)}
              </select>
            </label>
            {link && (() => {
              const up = link.spearman > 0;
              const indL = meta[indKey]?.label || "";
              const crime = kn ? (CAT_KN[cat] || cat) : cat === "all" ? "crime" : (d.correlations?.[cat]?.label || cat).toLowerCase();
              const t = chart.top;
              const times = t && chart.my ? t.y / chart.my : null;
              return (
                <div className="so-finding">
                  <span className={`so-verdict ${link.significant ? "on" : ""}`}>
                    {link.significant ? `${strength(link.spearman, kn)} ${L("link", "ಸಂಬಂಧ")}` : L("No clear link", "ಸ್ಪಷ್ಟ ಸಂಬಂಧವಿಲ್ಲ")}
                  </span>
                  <p className="so-headline">
                    {link.significant
                      ? L(`Where ${indL.charAt(0).toLowerCase() + indL.slice(1)} is ${up ? "higher" : "lower"}, districts record more ${crime}.`, `${indL} ${up ? "ಹೆಚ್ಚು" : "ಕಡಿಮೆ"} ಇರುವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ${crime} ಹೆಚ್ಚು.`)
                      : L(`${indL} does not explain where ${crime} is higher.`, `${crime} ಎಲ್ಲಿ ಹೆಚ್ಚು ಎಂಬುದನ್ನು ${indL} ವಿವರಿಸುವುದಿಲ್ಲ.`)}
                    {t && times >= 1.5 && <> {L(`${t.district} stands apart at ${t.y} per lakh, ${times.toFixed(1)}× the state median.`, `${t.district} ಲಕ್ಷಕ್ಕೆ ${t.y}, ರಾಜ್ಯ ಮಧ್ಯಮದ ${times.toFixed(1)}×.`)}</>}
                  </p>
                  {Math.abs(link.pearson - link.spearman) > 0.35 && (
                    <p className="so-caveat">{L("One or two districts pull the straight-line figure; the rank figure, which they cannot sway, is the one to trust.", "ಒಂದೆರಡು ಜಿಲ್ಲೆಗಳು ನೇರ-ರೇಖೆಯ ಅಂಕಿಯನ್ನು ಎಳೆಯುತ್ತವೆ; ಶ್ರೇಣಿ ಅಂಕಿಯನ್ನು ನಂಬಿ.")}</p>
                  )}
                </div>
              );
            })()}
            <div className="so-chart" key={`${indKey}-${cat}`} aria-label={L("Scatter of districts", "ಜಿಲ್ಲೆಗಳ ಚದುರು ಚಿತ್ರ")}>
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 18, right: 24, bottom: 34, left: 8 }}>
                  <CartesianGrid stroke="rgba(148,163,184,.08)" vertical={false} />
                  <XAxis type="number" dataKey="x" name={meta[indKey]?.label} tick={{ fill: "#8492A6", fontSize: 11 }} domain={chart.xd} allowDataOverflow tickLine={false} axisLine={{ stroke: "rgba(148,163,184,.25)" }}
                         label={{ value: `${meta[indKey]?.label} (${meta[indKey]?.unit})`, position: "insideBottom", offset: -22, fill: "#8492A6", fontSize: 12 }} />
                  <YAxis type="number" dataKey="y" tick={{ fill: "#8492A6", fontSize: 11 }} width={44} domain={chart.yd} tickLine={false} axisLine={false}
                         label={{ value: L("FIRs per lakh a year", "ವರ್ಷಕ್ಕೆ ಲಕ್ಷಕ್ಕೆ FIR"), angle: -90, position: "insideLeft", fill: "#8492A6", fontSize: 12 }} />
                  <ZAxis range={[60, 60]} />
                  {chart.mx != null && <ReferenceLine x={chart.mx} stroke="rgba(148,163,184,.3)" strokeDasharray="2 4" label={{ value: L("median", "ಮಧ್ಯಮ"), position: "top", fill: "#64748B", fontSize: 10 }} />}
                  {chart.my != null && <ReferenceLine y={chart.my} stroke="rgba(148,163,184,.3)" strokeDasharray="2 4" label={{ value: L("state median", "ರಾಜ್ಯ ಮಧ್ಯಮ"), position: "insideTopRight", fill: "#64748B", fontSize: 10 }} />}
                  {chart.line && link?.significant && <ReferenceLine segment={chart.line} stroke="#22E6F0" strokeOpacity={0.55} strokeWidth={1.5} strokeDasharray="6 4" ifOverflow="hidden" />}
                  <Tooltip cursor={{ strokeDasharray: "3 3", stroke: "rgba(148,163,184,.3)" }} content={({ payload }) => {
                    const p = payload?.[0]?.payload;
                    if (!p) return null;
                    const vs = chart.my ? p.y / chart.my : null;
                    return <div className="so-tip"><b>{p.district}</b><span>{p.y} {L("FIRs per lakh a year", "ವರ್ಷಕ್ಕೆ ಲಕ್ಷಕ್ಕೆ FIR")}{vs ? ` · ${vs >= 1 ? vs.toFixed(1) + "×" : Math.round(vs * 100) + "%"} ${L("of the state median", "ರಾಜ್ಯ ಮಧ್ಯಮದ")}` : ""}</span><span>{meta[indKey]?.label}: {fmt(p.x, meta[indKey]?.unit)}</span></div>;
                  }} />
                  <Scatter data={points} shape={<Dot />} isAnimationActive animationBegin={150} animationDuration={900} animationEasing="ease-out">
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <p className="so-legend">
              <span><i style={{ background: "#22E6F0" }} />{L("Highest three", "ಹೆಚ್ಚಿನ ಮೂರು")}</span>
              <span><i style={{ background: "#A78BFA" }} />{L("Lowest", "ಕಡಿಮೆ")}</span>
              <span><i className="ring" />{L("Bengaluru Urban", "ಬೆಂಗಳೂರು ನಗರ")}</span>
              {link?.significant && <span><i className="dash" />{L("Trend", "ಪ್ರವೃತ್ತಿ")}</span>}
            </p>
            {link && <p className="so-sub">{L("Rank correlation", "ಶ್ರೇಣಿ ಸಹಸಂಬಂಧ")} ρ {link.spearman.toFixed(2)} · p {link.p < 0.001 ? "< 0.001" : link.p.toFixed(3)} · Pearson r {link.pearson.toFixed(2)} · {L(`${points.length} districts. A link between districts is not a cause, and says nothing about any one person.`, `${points.length} ಜಿಲ್ಲೆಗಳು. ಜಿಲ್ಲೆಗಳ ನಡುವಿನ ಸಂಬಂಧ ಕಾರಣವಲ್ಲ, ಯಾವುದೇ ವ್ಯಕ್ತಿಯ ಬಗ್ಗೆ ಏನೂ ಹೇಳುವುದಿಲ್ಲ.`)}</p>}
          </section>
        </div>

        <section className="so-block so-tablewrap">
          <h2><span className="so-n">03</span>{L("All districts", "ಎಲ್ಲ ಜಿಲ್ಲೆಗಳು")}</h2>
          <div className="so-scroll">
            <table className="so-table">
              <thead><tr>
                {head("district", L("District", "ಜಿಲ್ಲೆ"))}
                {head("rate", L(`${kn ? CAT_KN[cat] : d.categories[cat]}, per lakh`, "ಲಕ್ಷಕ್ಕೆ"))}
                {TABLE_COLS.map((k) => head(k, meta[k]?.label))}
              </tr></thead>
              <tbody>
                {table.map((r) => (
                  <tr key={r.district}>
                    <th scope="row">{r.district}</th>
                    <td className="n">{r.rates[cat]}</td>
                    {TABLE_COLS.map((k) => <td key={k} className="n">{fmt(r[k], meta[k]?.unit)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="so-sub">{L(`Rates are FIRs in the register per lakh people a year, ${d.years[0]}-${d.years[1]}, on 2011 population. Police districts are added into their revenue district (Bengaluru City into Bengaluru Urban, Hubballi-Dharwad City into Dharwad, and so on); statewide units (${d.excluded_units.join(", ")}) are left out. Ballari includes Vijayanagara, as both sources predate it.`,
            `ದರ: ದಾಖಲೆಯಲ್ಲಿನ FIR ಗಳು, ವರ್ಷಕ್ಕೆ ಲಕ್ಷ ಜನರಿಗೆ, ${d.years[0]}-${d.years[1]}, 2011 ರ ಜನಸಂಖ್ಯೆಯ ಮೇಲೆ. ಪೊಲೀಸ್ ಜಿಲ್ಲೆಗಳನ್ನು ಕಂದಾಯ ಜಿಲ್ಲೆಗೆ ಸೇರಿಸಲಾಗಿದೆ; ರಾಜ್ಯವ್ಯಾಪಿ ಘಟಕಗಳನ್ನು (${d.excluded_units.join(", ")}) ಹೊರಗಿಡಲಾಗಿದೆ. ಬಳ್ಳಾರಿಯಲ್ಲಿ ವಿಜಯನಗರವೂ ಸೇರಿದೆ.`)}</p>
        </section>

        {vic && (
          <section className="so-block">
            <h2><span className="so-n">04</span>{L("Who the victims are", "ಸಂತ್ರಸ್ತರು ಯಾರು")}</h2>
            <p className="so-sub">{L(`${vTotal?.toLocaleString("en-IN")} victims recorded on FIRs.`, `FIR ಗಳಲ್ಲಿ ದಾಖಲಾದ ${vTotal?.toLocaleString("en-IN")} ಸಂತ್ರಸ್ತರು.`)}</p>
            <div className="so-vic">
              <div><h3>{L("Sex", "ಲಿಂಗ")}</h3><Bars rows={vic.gender} total={vTotal} /></div>
              <div><h3>{L("Age", "ವಯಸ್ಸು")}</h3><Bars rows={vic.age_band} total={vTotal} /></div>
              <div><h3>{L("Occupation", "ಉದ್ಯೋಗ")}</h3><Bars rows={vic.occupation} total={vTotal} /></div>
            </div>
          </section>
        )}

        <footer className="so-foot">
          {L("Sources", "ಮೂಲಗಳು")}: {d.sources.map((s) => `${s.name} (via ${s.via})`).join("; ")}.
        </footer>
      </div>
    </main>
  );
}
