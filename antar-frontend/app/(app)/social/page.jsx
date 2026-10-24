"use client";
// Social insights: how crime across Karnataka's 30 districts lines up with social indicators
// (Census 2011, NFHS-5), and who the victims are. Data from /api/social/indicators
// (app/services/social_indicators.py) and /api/social/demographics. Every link is a district-
// level rank correlation, shown with its number, with urbanisation held constant, and with
// what it cannot say.
import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
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

function Dot(props) {
  const { cx, cy, payload } = props;
  const big = payload.district === "Bengaluru Urban";
  return <circle cx={cx} cy={cy} r={big ? 6 : 4.5} fill={payload.hl ? "#22E6F0" : "rgba(148,163,184,.75)"} stroke={big ? "#fff" : "none"} />;
}

export default function SocialInsights() {
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

  const points = useMemo(() => (d?.table || []).map((r) => ({ district: r.district, x: r[indKey], y: r.rates[cat], hl: r.district === "Bengaluru Urban" })), [d, indKey, cat]);
  const table = useMemo(() => {
    const rows = [...(d?.table || [])];
    const val = (r) => (sort.key === "rate" ? r.rates[cat] : sort.key === "district" ? r.district : r[sort.key]);
    rows.sort((a, b) => (val(a) > val(b) ? 1 : val(a) < val(b) ? -1 : 0) * sort.dir);
    return rows;
  }, [d, cat, sort]);

  if (err) return <main className="so-page"><div className="so-wrap"><h1 className="so-title">{L("Social insights", "ಸಾಮಾಜಿಕ ಒಳನೋಟಗಳು")}</h1><p className="so-lede">{L("The district figures could not be read just now.", "ಜಿಲ್ಲಾ ಅಂಕಿಅಂಶಗಳನ್ನು ಈಗ ಓದಲಾಗಲಿಲ್ಲ.")}</p></div></main>;
  if (!d) return <main className="so-page"><div className="so-wrap"><p className="so-lede">{L("Reading district figures…", "ಜಿಲ್ಲಾ ಅಂಕಿಅಂಶಗಳನ್ನು ಓದಲಾಗುತ್ತಿದೆ…")}</p></div></main>;

  const head = (key, label) => (
    <th scope="col"><button type="button" onClick={() => setSort((s) => ({ key, dir: s.key === key ? -s.dir : -1 }))} aria-sort={sort.key === key ? (sort.dir < 0 ? "descending" : "ascending") : "none"}>
      {label}{sort.key === key ? (sort.dir < 0 ? " ↓" : " ↑") : ""}</button></th>
  );
  const vic = demo?.victims;
  const vTotal = vic?.gender?.reduce((a, r) => a + r.n, 0);

  return (
    <main className="so-page">
      <div className="so-wrap">
        <header className="so-head">
          <span className="so-eyebrow">{L("Sociological crime insights", "ಸಾಮಾಜಿಕ ಅಪರಾಧ ಒಳನೋಟಗಳು")}</span>
          <h1 className="so-title">{L("What goes with crime, district by district", "ಜಿಲ್ಲೆಯಿಂದ ಜಿಲ್ಲೆಗೆ ಅಪರಾಧದ ಜೊತೆ ಏನು ಬರುತ್ತದೆ")}</h1>
          <p className="so-lede">{L(`Crime rates in Karnataka's ${d.districts} districts set against urbanisation, population growth, education, child marriage, household amenities and alcohol use. Each link is a rank correlation across districts, with its number and whether it still holds once urbanisation is taken out.`,
                                   `ಕರ್ನಾಟಕದ ${d.districts} ಜಿಲ್ಲೆಗಳ ಅಪರಾಧ ದರಗಳು ನಗರೀಕರಣ, ಜನಸಂಖ್ಯಾ ಬೆಳವಣಿಗೆ, ಶಿಕ್ಷಣ, ಬಾಲ್ಯ ವಿವಾಹ, ಗೃಹ ಸೌಲಭ್ಯ ಮತ್ತು ಮದ್ಯಪಾನದ ಎದುರು.`)}</p>
          <ul className="so-caveats">{d.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
        </header>

        <nav className="so-cats" role="tablist" aria-label={L("Kind of crime", "ಅಪರಾಧದ ಪ್ರಕಾರ")}>
          {Object.entries(d.categories).map(([k, v]) => (
            <button key={k} role="tab" aria-selected={cat === k} className={cat === k ? "on" : ""} onClick={() => { setCat(k); setInd(null); }}>{kn ? CAT_KN[k] : v}</button>
          ))}
        </nav>

        <div className="so-grid">
          <section className="so-block">
            <h2>{L("Clear links", "ಸ್ಪಷ್ಟ ಸಂಬಂಧಗಳು")} <span>{clear.length}</span></h2>
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
            <h2>{L("Each district", "ಪ್ರತಿ ಜಿಲ್ಲೆ")}</h2>
            <label className="so-pick">
              <span>{L("Indicator", "ಸೂಚಕ")}</span>
              <select value={indKey} onChange={(e) => setInd(e.target.value)}>
                {d.indicators.filter((m) => m.key !== "population_2011").map((m) => <option key={m.key} value={m.key}>{m.label} ({m.year})</option>)}
              </select>
            </label>
            <div className="so-chart" aria-label={L("Scatter of districts", "ಜಿಲ್ಲೆಗಳ ಚದುರು ಚಿತ್ರ")}>
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 16, bottom: 34, left: 8 }}>
                  <CartesianGrid stroke="rgba(148,163,184,.12)" />
                  <XAxis type="number" dataKey="x" name={meta[indKey]?.label} tick={{ fill: "#8492A6", fontSize: 11 }} domain={["auto", "auto"]}
                         label={{ value: `${meta[indKey]?.label} (${meta[indKey]?.unit})`, position: "insideBottom", offset: -22, fill: "#8492A6", fontSize: 12 }} />
                  <YAxis type="number" dataKey="y" tick={{ fill: "#8492A6", fontSize: 11 }} width={44}
                         label={{ value: L("FIRs per lakh a year", "ವರ್ಷಕ್ಕೆ ಲಕ್ಷಕ್ಕೆ FIR"), angle: -90, position: "insideLeft", fill: "#8492A6", fontSize: 12 }} />
                  <ZAxis range={[60, 60]} />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} content={({ payload }) => {
                    const p = payload?.[0]?.payload;
                    return p ? <div className="so-tip"><b>{p.district}</b><span>{fmt(p.x, meta[indKey]?.unit)} · {p.y} {L("FIRs per lakh", "ಲಕ್ಷಕ್ಕೆ FIR")}</span></div> : null;
                  }} />
                  <Scatter data={points} shape={<Dot />} />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            {link && <p className="so-sub">{link.sentence} ρ {link.spearman.toFixed(2)}, p {link.p < 0.001 ? "< 0.001" : link.p.toFixed(3)}; {L("Pearson", "ಪಿಯರ್ಸನ್")} r {link.pearson.toFixed(2)}. {L("Bengaluru Urban is outlined.", "ಬೆಂಗಳೂರು ನಗರವನ್ನು ಗುರುತಿಸಲಾಗಿದೆ.")}</p>}
          </section>
        </div>

        <section className="so-block so-tablewrap">
          <h2>{L("Districts", "ಜಿಲ್ಲೆಗಳು")}</h2>
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
          <p className="so-sub">{L(`Rates are FIRs in the register per lakh people a year, ${d.years[0]}-${d.years[1]}, on 2011 population. Police districts are added into their revenue district (Bengaluru City into Bengaluru Urban, Hubballi-Dharwad City into Dharwad, and so on); statewide units (${d.excluded_units.join(", ")}) are left out. Ballari includes Vijayanagara, as both sources predate it.`, "")}</p>
        </section>

        {vic && (
          <section className="so-block">
            <h2>{L("Who the victims are", "ಸಂತ್ರಸ್ತರು ಯಾರು")}</h2>
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
