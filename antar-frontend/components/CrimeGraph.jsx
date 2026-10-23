"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CATEGORIES, categorize } from "@/lib/crimeGraph";
import { SummaryToggle } from "@/components/BrainViewSummary";

// Brain · "Crime Graph" view - radial year-clock of crime cycles (reference:
// CICLI DEL SONNO infographic). Jan at top, clockwise; each crime type is one
// polar waveform (10-day bins → 36 points), distance from the dial = FIR load.
// Click a trace or legend row to isolate its cycle and open the detail panel.
//
// DATA SOURCE: /api/dataset/cycles - real counts from the full FIRs table
// (no sampling, no scale factor). The headline total equals COUNT(*).
const CX = 500, CY = 500;
const RING_R = 210, RING_W = 30;
const R0 = 240, AMP = 138;
const BINS = 36; // 3 per month
const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MAX_SHOWN = 8; // top categories to draw as waveforms

const API = (process.env.NEXT_PUBLIC_API_URL || "");

const angleOf = (i, n = BINS) => (-90 + (i * 360) / n) * (Math.PI / 180);

function smoothClosed(pts) {
  const n = pts.length;
  let d = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`;
  for (let i = 0; i < n; i++) {
    const p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
    d += ` C ${(p1.x + (p2.x - p0.x) / 6).toFixed(1)} ${(p1.y + (p2.y - p0.y) / 6).toFixed(1)}, ${(p2.x - (p3.x - p1.x) / 6).toFixed(1)} ${(p2.y - (p3.y - p1.y) / 6).toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
  }
  return d + " Z";
}

// Annular-sector path (used to highlight a selected month wedge on the dial).
function sectorPath(cx, cy, r0, r1, a0, a1) {
  const p = (r, a) => [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  const [x0, y0] = p(r0, a0), [x1, y1] = p(r1, a0), [x2, y2] = p(r1, a1), [x3, y3] = p(r0, a1);
  const large = (a1 - a0) % (2 * Math.PI) > Math.PI ? 1 : 0;
  return `M ${x0.toFixed(1)} ${y0.toFixed(1)} L ${x1.toFixed(1)} ${y1.toFixed(1)}`
    + ` A ${r1} ${r1} 0 ${large} 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`
    + ` L ${x3.toFixed(1)} ${y3.toFixed(1)}`
    + ` A ${r0} ${r0} 0 ${large} 0 ${x0.toFixed(1)} ${y0.toFixed(1)} Z`;
}

// When and where the selected crime concentrates (from /api/dataset/crime_profile).
// Plain sentences first, numbers underneath - the officer should be able to read the top
// line aloud at a briefing.
// What an officer plans from a crime's cycle: which month to get ahead of, which days and
// part of the month, and where. Every line is read off the counts already on screen; the
// one action asks Chat for that crime in that district, which the register can answer.
function CrimePlan({ c, p, kn, y, lastYear, onAsk }) {
  const prev = (c.peak + 11) % 12;
  const ready = p && !p.loading && !p.error && p.total;
  const t = ready ? (p.month_thirds || {}) : {};
  const third = Object.entries(t).sort((a, b) => b[1] - a[1])[0]?.[0];
  const thirdWord = { early: kn ? "ತಿಂಗಳ ಆರಂಭ (1–10)" : "early in the month (1st–10th)", mid: kn ? "ತಿಂಗಳ ಮಧ್ಯ (11–20)" : "mid-month (11th–20th)", late: kn ? "ತಿಂಗಳ ಕೊನೆ (21–31)" : "late in the month (21st on)" }[third];
  const td = ready ? p.top_districts?.[0] : null;
  const ts = ready ? p.top_stations?.[0] : null;
  const year = y === "All" ? lastYear : y;
  const crime = c.label.toLowerCase().replace(/ & /g, " and ");
  const q = td ? `How many ${crime} cases were registered in ${td.name}${year ? ` in ${year}` : ""}?` : null;
  return (
    <div className="cg-plan">
      <span className="cg-plan-h">{kn ? "ಇದಕ್ಕಾಗಿ ಯೋಜನೆ" : "Plan for it"}</span>
      <dl>
        <div><dt>{kn ? "ಯಾವಾಗ" : "When"}</dt><dd>{kn
          ? <>ಉತ್ತುಂಗ <b>{MONTH_NAMES[c.peak]}</b> - {MONTH_NAMES[prev]} ಕೊನೆಯಿಂದ ಗಸ್ತು ಹೆಚ್ಚಿಸಿ. ಶಾಂತ: {MONTH_NAMES[c.quiet]}.</>
          : <>Peaks in <b>{MONTH_NAMES[c.peak]}</b>: step up patrols from late {MONTH_NAMES[prev]}. Quietest in {MONTH_NAMES[c.quiet]}.</>}</dd></div>
        {ready && p.peak_weekday && <div><dt>{kn ? "ದಿನಗಳು" : "Days"}</dt><dd>{kn
          ? <>ಹೆಚ್ಚಾಗಿ <b>{p.peak_weekday}</b>{thirdWord ? `, ${thirdWord}` : ""}.</>
          : <>Most often on a <b>{p.peak_weekday}</b>{thirdWord ? `, ${thirdWord}` : ""}.</>}</dd></div>}
        {td && <div><dt>{kn ? "ಎಲ್ಲಿ" : "Where"}</dt><dd>{kn
          ? <><b>{td.name}</b> ({td.share}%){ts ? ` · ಹೆಚ್ಚು ದಾಖಲೆ ${ts.name}` : ""}.</>
          : <><b>{td.name}</b> holds {td.share}%{ts ? `; most are registered at ${ts.name}` : ""}.</>}</dd></div>}
        {p?.loading && <div><dt /><dd className="dim">{kn ? "ದಿನ ಮತ್ತು ಸ್ಥಳ ಲೆಕ್ಕ ಹಾಕಲಾಗುತ್ತಿದೆ…" : "Working out the days and places…"}</dd></div>}
      </dl>
      {q && (
        <button type="button" className="cg-plan-ask" onClick={() => onAsk(q)} title={q}>
          {kn ? `${td.name} ನಲ್ಲಿ ${year || ""} ಪ್ರಕರಣಗಳನ್ನು ಚಾಟ್‌ನಲ್ಲಿ ಕೇಳಿ` : `Ask Chat: ${td.name}${year ? `, ${year}` : ""}`} <span aria-hidden="true">→</span>
        </button>
      )}
    </div>
  );
}

function CrimeProfile({ p, kn, color }) {
  if (!p) return null;
  if (p.loading) return <div className="cg-prof-wait">{kn ? "ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ…" : "Analysing when and where…"}</div>;
  if (p.error || !p.total) return <div className="cg-prof-wait">{kn ? "ವಿವರ ಲಭ್ಯವಿಲ್ಲ." : "Detail unavailable for this selection."}</div>;
  const wMax = Math.max(1, ...p.weekdays.map((w) => w.n));
  const t = p.month_thirds || {};
  const tTot = (t.early || 0) + (t.mid || 0) + (t.late || 0) || 1;
  const thirdMax = Object.entries(t).sort((a, b) => b[1] - a[1])[0]?.[0];
  const thirdWord = { early: kn ? "ತಿಂಗಳ ಆರಂಭ (1–10)" : "early in the month (1–10)", mid: kn ? "ಮಧ್ಯ (11–20)" : "mid-month (11–20)", late: kn ? "ಕೊನೆ (21–31)" : "late in the month (21–31)" };
  const top = p.top_districts?.[0];
  const seasonal = Math.abs(p.peak_month_vs_avg || 0) >= 15;
  return (
    <div className="cg-prof">
      <div className="cg-prof-h">{kn ? "ಯಾವಾಗ" : "When it peaks"}</div>
      <p>{kn
        ? `ಉತ್ತುಂಗ ತಿಂಗಳು ${p.peak_month} (ಸರಾಸರಿಗಿಂತ ${p.peak_month_vs_avg}% ಹೆಚ್ಚು). ಹೆಚ್ಚು ದಾಖಲಾಗುವ ದಿನ ${p.peak_weekday}.`
        : `Peaks in ${p.peak_month}, ${p.peak_month_vs_avg}% above an average month${seasonal ? "" : " - a mild seasonal swing"}. Most often registered on a ${p.peak_weekday}.`}</p>
      <div className="cg-wd">
        {p.weekdays.map((w) => (
          <div key={w.d} title={`${w.d} · ${w.n.toLocaleString()}`}>
            <i style={{ height: `${Math.round((w.n / wMax) * 100)}%`, background: w.d === p.peak_weekday ? color : "rgba(157,171,188,.35)" }} />
            <em>{w.d[0]}</em>
          </div>
        ))}
      </div>
      <div className="cg-thirds">
        {["early", "mid", "late"].map((k) => (
          <span key={k} className={k === thirdMax ? "on" : ""}>{thirdWord[k]} · {Math.round((100 * (t[k] || 0)) / tTot)}%</span>
        ))}
      </div>

      <div className="cg-prof-h">{kn ? "ಎಲ್ಲಿ" : "Where it concentrates"}</div>
      {top && <p>{kn
        ? `${top.name} ನಲ್ಲಿ ${top.share}% (${top.n.toLocaleString()} FIR).`
        : `${top.name} holds ${top.share}% of these FIRs (${top.n.toLocaleString()}).`}</p>}
      <div className="cg-where">
        {(p.top_districts || []).map((d) => (
          <div key={d.name} className="row"><span>{d.name}</span><i><b style={{ width: `${Math.min(100, d.share)}%`, background: color }} /></i><em>{d.share}%</em></div>
        ))}
      </div>
      {(p.top_stations || []).length > 0 && (
        <>
          <div className="cg-prof-sh">{kn ? "ಹೆಚ್ಚು ದಾಖಲಾದ ಠಾಣೆಗಳು" : "Busiest stations"}</div>
          {p.top_stations.slice(0, 4).map((st) => (
            <div key={`${st.name}-${st.district}`} className="cg-st"><span>{st.name}<em>{st.district}</em></span><b>{st.n.toLocaleString()}</b></div>
          ))}
        </>
      )}
      <div className="cg-prof-k">D · {kn ? "ದಾಖಲೆಗಳಿಂದ ಲೆಕ್ಕ" : "counted from records"} · {p.total.toLocaleString()} FIRs</div>
    </div>
  );
}

/** Format a year chip label: show "(partial Mon–Mon)" when months_covered < 12 */
function yearLabel(yInfo) {
  if (!yInfo || yInfo.months_covered >= 12) return String(yInfo?.year ?? "");
  // We don't have exact month range from the API, just months_covered count.
  // Show "(partial)" generically.
  return `${yInfo.year} (partial)`;
}

export default function CrimeGraph({ recs, kn }) {
  const router = useRouter();
  // ── API data ──────────────────────────────────────────────────────────
  const [apiData, setApiData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [year, setYear] = useState("All");
  const [sel, setSel] = useState(null);       // category key or null
  const [selMonth, setSelMonth] = useState(null); // 0-11 highlighted month or null
  const [profile, setProfile] = useState(null);   // /api/dataset/crime_profile for the selected crime

  // Fetch cycles data from the API.
  // Two bugs lived here. The chart relabelled itself to the clicked year immediately but
  // kept drawing the PREVIOUS year until the fetch returned, so "2016" sat on top of 2023's
  // data for seconds. And nothing ignored a stale response, so clicking two chips quickly
  // could leave the older request's data on screen. The response now carries the year it
  // belongs to, labels read from that, and a superseded request is dropped.
  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    const url = year === "All"
      ? `${API}/api/dataset/cycles`
      : `${API}/api/dataset/cycles?year=${year}`;
    fetch(url)
      .then((r) => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then((d) => { if (!alive) return; setApiData({ ...d, _year: year }); setLoading(false); })
      .catch((e) => { if (!alive) return; setError(e.message); setLoading(false); });
    return () => { alive = false; };
  }, [year]);

  // Build year chips from API data (or fall back to recs)
  const years = useMemo(() => {
    if (apiData?.years) {
      return [...apiData.years.map((y) => y.year), "All"];
    }
    // Fallback to recs if API hasn't loaded
    const ys = [...new Set((recs || []).map((r) => r._year).filter(Boolean))].sort();
    return [...ys, "All"];
  }, [apiData, recs]);

  // Map of year → year info for chip labels
  const yearInfo = useMemo(() => {
    if (!apiData?.years) return {};
    const m = {};
    apiData.years.forEach((y) => { m[y.year] = y; });
    return m;
  }, [apiData]);

  // per-category 36-bin waveforms + totals from API data
  const model = useMemo(() => {
    if (!apiData) return null;
    const { groups, total, month_totals } = apiData;
    if (!groups || groups.length === 0) return null;

    // Map raw group names through categorize() and merge
    const catBins = new Map();   // cat → Float32Array(36)
    const catTotals = new Map(); // cat → n
    groups.forEach((g) => {
      const cat = categorize(g.name);
      if (!catBins.has(cat)) {
        catBins.set(cat, new Array(BINS).fill(0));
        catTotals.set(cat, 0);
      }
      const bins = catBins.get(cat);
      g.bins.forEach((v, i) => { bins[i] += v; });
      catTotals.set(cat, catTotals.get(cat) + g.n);
    });

    // Top MAX_SHOWN named categories; everything else - including categorize()'s own
    // "OTHER" - merges into ONE "Other". Previously a real OTHER in the top 8 was drawn
    // and a second merged "Other" appended: two traces, one React key, a double count.
    const sorted = [...catTotals.entries()].filter(([c]) => c !== "OTHER").sort((a, b) => b[1] - a[1]);
    const topCats = sorted.slice(0, MAX_SHOWN);
    const rest = [...sorted.slice(MAX_SHOWN), ...(catTotals.has("OTHER") ? [["OTHER", catTotals.get("OTHER")]] : [])];
    const otherN = rest.reduce((s, [, n]) => s + n, 0);

    const cats = topCats.map(([cat, n]) => {
      const wave = catBins.get(cat);
      return {
        cat,
        n,
        color: CATEGORIES[cat]?.color || "#5d6b80",
        label: CATEGORIES[cat]?.label || cat,
        wave,
      };
    });

    // Add "Other" if there are categories beyond the top 8
    if (otherN > 0) {
      const otherBins = new Array(BINS).fill(0);
      rest.forEach(([cat]) => {
        const bins = catBins.get(cat);
        bins.forEach((v, i) => { otherBins[i] += v; });
      });
      cats.push({
        cat: "OTHER",
        n: otherN,
        color: CATEGORIES.OTHER?.color || "#98989D",
        label: CATEGORIES.OTHER?.label || "Other",
        // so the legend can say what "Other" is made of
        members: rest.map(([cat]) => CATEGORIES[cat]?.label || cat),
        wave: otherBins,
      });
    }

    // Every category, for the selector - including the ones merged into "Other", so an
    // officer can pick ANY crime, not just the eight loudest.
    const allCats = [...catTotals.entries()].sort((a, b) => b[1] - a[1]).map(([cat, n]) => ({
      cat, n, wave: catBins.get(cat),
      color: CATEGORIES[cat]?.color || "#5d6b80", label: CATEGORIES[cat]?.label || cat,
      groups: groups.filter((g) => categorize(g.name) === cat).map((g) => g.name),
    }));
    const otherCat = cats.find((c) => c.cat === "OTHER");
    if (otherCat) otherCat.groups = allCats.filter((c) => !topCats.some(([t]) => t === c.cat)).flatMap((c) => c.groups);
    topCats.forEach(([cat], i) => { cats[i].groups = allCats.find((c) => c.cat === cat)?.groups || []; });

    // Compute polar paths
    const vmax = Math.max(1, ...cats.flatMap((c) => c.wave));
    const withPath = (c) => {
      c.pts = c.wave.map((v, i) => {
        const r = R0 + (Math.sqrt(v) / Math.sqrt(vmax)) * AMP;
        const a = angleOf(i);
        return { x: CX + Math.cos(a) * r, y: CY + Math.sin(a) * r };
      });
      c.path = smoothClosed(c.pts);
      return c;
    };
    allCats.forEach(withPath);
    cats.forEach((c) => {
      c.pts = c.wave.map((v, i) => {
        const r = R0 + (Math.sqrt(v) / Math.sqrt(vmax)) * AMP;
        const a = angleOf(i);
        return { x: CX + Math.cos(a) * r, y: CY + Math.sin(a) * r };
      });
      c.path = smoothClosed(c.pts);
    });

    return {
      cats,
      allCats,
      total,  // from API - the TRUE count
      vmax,
      monthTotals: month_totals || new Array(12).fill(0),
    };
  }, [apiData]);

  // A category's FIRs in one month = its three 10-day bins for that month.
  const inMonth = (c, m) => c.wave[m * 3] + c.wave[m * 3 + 1] + c.wave[m * 3 + 2];

  // detail stats for the isolated category
  const detail = useMemo(() => {
    if (!model || !sel) return null;
    const c = model.cats.find((m) => m.cat === sel) || model.allCats.find((m) => m.cat === sel);
    if (!c) return null;
    const byMonth = new Array(12).fill(0);
    c.wave.forEach((v, i) => { byMonth[Math.floor(i / 3)] += v; });
    // Peak / quietest over months that actually have data - a partial year's empty months
    // are "no records", not "the quietest month".
    const covered = byMonth.map((v, i) => [v, i]).filter(([, i]) => (model.monthTotals[i] || 0) > 0);
    const pool = covered.length ? covered : byMonth.map((v, i) => [v, i]);
    const peak = pool.reduce((a, b) => (b[0] > a[0] ? b : a))[1];
    const quiet = pool.reduce((a, b) => (b[0] < a[0] ? b : a))[1];
    const share = Math.round((c.n / Math.max(1, model.total)) * 100);
    return { ...c, byMonth, peak, quiet, share };
  }, [model, sel]);

  // When and where the selected crime concentrates - fetched only once a crime is chosen.
  useEffect(() => {
    if (!detail?.groups?.length) { setProfile(null); return; }
    let alive = true;
    setProfile({ loading: true });
    const p = new URLSearchParams({ groups: detail.groups.join(",") });
    const yy = apiData?._year;
    if (yy && yy !== "All") p.set("year", yy);
    // "All" on the dial = complete years only; count exactly those, so the panel can never
    // disagree with the chart beside it (a different peak month or total).
    else if (apiData?.scope_years?.length) p.set("years", apiData.scope_years.join(","));
    fetch(`${API}/api/dataset/crime_profile?${p.toString()}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => { if (alive) setProfile(d); })
      .catch(() => { if (alive) setProfile({ error: true }); });
    return () => { alive = false; };
  }, [detail?.cat, detail?.groups?.join(","), apiData?._year, apiData?.scope_years?.join(",")]);

  // ── Loading skeleton ──────────────────────────────────────────────────
  if (loading && !model) {
    return (
      <div className="bsx-cg" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 400 }}>
        <div style={{ textAlign: "center", color: "#9DABBC" }}>
          <div style={{ width: 80, height: 80, border: "3px solid rgba(34,230,240,0.2)", borderTop: "3px solid #22E6F0", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto 16px" }} />
          <span>{kn ? "ಡೇಟಾ ಲೋಡ್ ಆಗುತ್ತಿದೆ..." : "Loading crime cycle data..."}</span>
        </div>
      </div>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────
  if (error && !model) {
    return (
      <div className="bsx-cg" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 400 }}>
        <div style={{ textAlign: "center", color: "#FF453A", maxWidth: 400 }}>
          <p>{kn ? "ಡೇಟಾ ಲೋಡ್ ವಿಫಲವಾಗಿದೆ" : "Couldn't load full-dataset counts"}</p>
          <p style={{ color: "#9DABBC", fontSize: 13 }}>{kn ? "ಲಿಂಕ್ ಮಾಡಿದ ಮಾದರಿ ತೋರಿಸಲಾಗುತ್ತಿದೆ" : "Showing linked sample"}</p>
        </div>
      </div>
    );
  }

  if (!model) return null;
  // Label with the year the DATA belongs to, never the chip just clicked - see the fetch.
  const y = apiData?._year ?? year;
  const switching = loading && year !== y;
  const selc = detail;
  const mSel = selMonth;
  // The month filter narrows everything that shows a number, not just the wedge.
  const countOf = (c) => (mSel !== null ? inMonth(c, mSel) : c.n);
  const monthTotal = mSel !== null ? (model.monthTotals?.[mSel] || 0) : null;
  // A crime picked from the selector that is not among the eight drawn traces gets its
  // own trace, so the picture always shows what the detail panel describes.
  const drawn = selc && !model.cats.some((c) => c.cat === selc.cat) ? [...model.cats, selc] : model.cats;

  // View summary: what this clock is showing right now, in sentences. Rebuilt on every
  // change of year, month or crime, so it always describes the picture on screen.
  const scopeTxt = y === "All" && apiData?.scope_years?.length
    ? (kn ? `ಪೂರ್ಣ ವರ್ಷಗಳು ${apiData.scope_years[0]}–${apiData.scope_years[apiData.scope_years.length - 1]}` : `complete years ${apiData.scope_years[0]}–${apiData.scope_years[apiData.scope_years.length - 1]}`)
    : String(y);
  const mt = model.monthTotals || [];
  const covered = mt.map((v, i) => [v, i]).filter(([v]) => v > 0);
  const busiest = covered.length ? covered.reduce((a, b) => (b[0] > a[0] ? b : a)) : null;
  const quietest = covered.length ? covered.reduce((a, b) => (b[0] < a[0] ? b : a)) : null;
  const top3 = [...model.allCats].slice(0, 3);
  const sumLines = [];
  sumLines.push(kn
    ? `ಈ ಗಡಿಯಾರ ${scopeTxt} ರ ${model.total.toLocaleString()} FIR ಗಳನ್ನು ${model.allCats.length} ಅಪರಾಧ ಪ್ರಕಾರಗಳಲ್ಲಿ ತೋರಿಸುತ್ತದೆ (ಜನವರಿ ಮೇಲೆ, ಪ್ರದಕ್ಷಿಣೆ).`
    : `This clock shows ${model.total.toLocaleString()} FIRs across ${model.allCats.length} crime types for ${scopeTxt} (January at the top, clockwise).`);
  if (busiest && quietest) sumLines.push(kn
    ? `ಅತಿ ಹೆಚ್ಚು ತಿಂಗಳು ${MONTH_NAMES[busiest[1]]} (${busiest[0].toLocaleString()}); ಅತಿ ಕಡಿಮೆ ${MONTH_NAMES[quietest[1]]} (${quietest[0].toLocaleString()}).`
    : `Busiest month: ${MONTH_NAMES[busiest[1]]} (${busiest[0].toLocaleString()} FIRs); quietest: ${MONTH_NAMES[quietest[1]]} (${quietest[0].toLocaleString()}).`);
  if (top3.length) sumLines.push(kn
    ? `ದೊಡ್ಡ ಅಪರಾಧಗಳು: ${top3.map((c) => `${c.label} ${Math.round((100 * c.n) / Math.max(1, model.total))}%`).join(", ")}.`
    : `Largest: ${top3.map((c) => `${c.label} ${Math.round((100 * c.n) / Math.max(1, model.total))}%`).join(", ")}.`);
  if (mSel !== null) sumLines.push(kn
    ? `ಆಯ್ಕೆ ಮಾಡಿದ ತಿಂಗಳು ${MONTH_NAMES[mSel]}: ${monthTotal.toLocaleString()} FIR (${Math.round((100 * monthTotal) / Math.max(1, model.total))}%).`
    : `Selected month ${MONTH_NAMES[mSel]}: ${monthTotal.toLocaleString()} FIRs (${Math.round((100 * monthTotal) / Math.max(1, model.total))}% of the ${scopeTxt} total).`);
  if (selc) {
    sumLines.push(kn
      ? `${selc.label}: ${selc.n.toLocaleString()} FIR (${selc.share}%). ಉತ್ತುಂಗ ${MONTH_NAMES[selc.peak]}, ಶಾಂತ ${MONTH_NAMES[selc.quiet]}.`
      : `${selc.label}: ${selc.n.toLocaleString()} FIRs, ${selc.share}% of all crime here. Peaks in ${MONTH_NAMES[selc.peak]}, quietest in ${MONTH_NAMES[selc.quiet]}.`);
    const td = profile?.top_districts?.[0];
    if (profile?.peak_weekday && td) sumLines.push(kn
      ? `ಹೆಚ್ಚಾಗಿ ${profile.peak_weekday} ರಂದು ದಾಖಲು; ${td.name} ನಲ್ಲಿ ${td.share}%.`
      : `Most often registered on a ${profile.peak_weekday}; ${td.name} holds ${td.share}% of them.`);
  } else {
    sumLines.push(kn ? "ಒಂದು ಅಪರಾಧವನ್ನು ಆಯ್ಕೆ ಮಾಡಿ - ಅದು ಯಾವಾಗ ಮತ್ತು ಎಲ್ಲಿ ಹೆಚ್ಚು ಎಂದು ನೋಡಲು." : "Pick a crime to see when and where it concentrates.");
  }
  if (y === "All" && apiData?.partial_years?.length) sumLines.push(kn
    ? `${apiData.partial_years.join(", ")} ಅಪೂರ್ಣ ವರ್ಷಗಳು; ಅವುಗಳ ಚಿಪ್‌ಗಳಲ್ಲಿ ಪ್ರತ್ಯೇಕವಾಗಿ.`
    : `${apiData.partial_years.join(", ")} ${apiData.partial_years.length === 1 ? "is a partial year" : "are partial years"}, left out of "All" so they do not distort the seasons - each has its own chip.`);

  return (
    <div className={`bsx-cg${switching ? " is-switching" : ""}`} aria-busy={switching}>
      {switching && (
        <div className="bsx-cg-loading" role="status">
          {kn ? `${year} ಲೋಡ್ ಆಗುತ್ತಿದೆ…` : `Loading ${year === "All" ? "all years" : year}…`}
        </div>
      )}
      <svg viewBox="83.33 83.33 833.33 833.33" className="bsx-cg-svg" key={y}>
        <defs>
          <filter id="cgGlow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* dotted guide circles (reference texture) */}
        <circle cx={CX} cy={CY} r={R0} fill="none" stroke="rgba(157,171,188,.14)" strokeWidth="1" strokeDasharray="2 6" />
        <circle cx={CX} cy={CY} r={R0 + AMP * 0.66} fill="none" stroke="rgba(157,171,188,.09)" strokeWidth="1" strokeDasharray="2 6" />
        <circle cx={CX} cy={CY} r={R0 + AMP} fill="none" stroke="rgba(157,171,188,.05)" strokeWidth="1" strokeDasharray="2 6" />

        {/* segmented dial ring */}
        <circle cx={CX} cy={CY} r={RING_R} fill="none" stroke="#0d1526" strokeWidth={RING_W} />
        <circle cx={CX} cy={CY} r={RING_R - RING_W / 2} fill="#05070f" stroke="rgba(255,255,255,.05)" strokeWidth="1" />
        {MONTHS.map((_, m) => {
          const a = angleOf(m * 3);
          return (
            <line key={"t" + m}
              x1={CX + Math.cos(a) * (RING_R - RING_W / 2 - 4)} y1={CY + Math.sin(a) * (RING_R - RING_W / 2 - 4)}
              x2={CX + Math.cos(a) * (RING_R + RING_W / 2 + 4)} y2={CY + Math.sin(a) * (RING_R + RING_W / 2 + 4)}
              stroke="#020308" strokeWidth="6" />
          );
        })}
        {/* Highlighted wedge for the selected month (draws behind the traces). */}
        {selMonth !== null && (
          <path d={sectorPath(CX, CY, R0 - 12, R0 + AMP + 14, angleOf(selMonth * 3), angleOf((selMonth + 1) * 3))}
            fill="rgba(34,230,240,0.10)" stroke="rgba(34,230,240,0.5)" strokeWidth="1.2" style={{ pointerEvents: "none" }} />
        )}

        {/* Clickable month segments on the dial ring. */}
        {MONTHS.map((mLbl, m) => {
          const on = selMonth === m;
          return (
            <path key={"seg" + m}
              d={sectorPath(CX, CY, RING_R - RING_W / 2, RING_R + RING_W / 2, angleOf(m * 3), angleOf((m + 1) * 3))}
              fill={on ? "rgba(34,230,240,0.22)" : "transparent"} stroke="none"
              style={{ cursor: "pointer" }} onClick={() => setSelMonth(on ? null : m)}>
              <title>{mLbl} · {(model.monthTotals?.[m] || 0).toLocaleString()} FIRs · {y}</title>
            </path>
          );
        })}
        {MONTHS.map((mLbl, m) => {
          const a = angleOf(m * 3 + 1.5);
          const on = selMonth === m;
          return (
            <text key={"m" + m} x={CX + Math.cos(a) * RING_R} y={CY + Math.sin(a) * RING_R}
              textAnchor="middle" dominantBaseline="central" fill={on ? "#22E6F0" : "#ffffff"} fontSize="12.5"
              fontWeight={on ? 700 : 400} fontFamily="JetBrains Mono"
              style={{ cursor: "pointer" }} onClick={() => setSelMonth(on ? null : m)}>{mLbl}</text>
          );
        })}

        {/* crime-cycle waveforms (visual) */}
        {drawn.map((c) => {
          const active = sel === c.cat;
          const dim = sel && !active;
          return (
            <path key={c.cat} d={c.path} fill="none"
              stroke={c.color}
              strokeWidth={active ? 2.6 : 1.4}
              opacity={dim ? 0.14 : active ? 1 : 0.8}
              filter={active ? "url(#cgGlow)" : undefined}
              className="bsx-cg-trace"
              style={{ pointerEvents: "none" }} />
          );
        })}

        {/* invisible thick hit-areas for easy selection */}
        {drawn.map((c) => {
          const active = sel === c.cat;
          return (
            <path key={"hit-" + c.cat} d={c.path} fill="none"
              stroke="transparent"
              strokeWidth={40}
              style={{ cursor: "pointer" }}
              onClick={() => setSel(active ? null : c.cat)}>
              <title>{c.label} · {c.n.toLocaleString()} FIRs · {y}</title>
            </path>
          );
        })}

        {/* peak marker on the isolated trace */}
        {selc && (() => {
          const i = selc.wave.indexOf(Math.max(...selc.wave));
          const p = selc.pts[i];
          return (
            <g>
              <circle cx={p.x} cy={p.y} r="5" fill={selc.color} />
              <circle cx={p.x} cy={p.y} r="10" fill="none" stroke={selc.color} opacity=".5">
                <animate attributeName="r" values="6;14;6" dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values=".6;.1;.6" dur="2s" repeatCount="indefinite" />
              </circle>
            </g>
          );
        })()}
      </svg>

      {/* centre stat - month selection takes priority so the highlighted wedge reads clearly */}
      <div className="bsx-cg-center">
        <b>{selc
          ? countOf(selc).toLocaleString()
          : mSel !== null ? monthTotal.toLocaleString() : model.total.toLocaleString()}</b>
        <span className="l1">{selc
          ? (mSel !== null ? `${selc.label} · ${MONTH_NAMES[mSel]}` : selc.label)
          : mSel !== null ? MONTH_NAMES[mSel] : (kn ? "FIR ದಾಖಲೆಗಳು" : "FIR records")}</span>
        <span className="l2">{selc
          ? (mSel !== null
              ? `${Math.round((countOf(selc) / Math.max(1, monthTotal)) * 100)}% ${kn ? "ಆ ತಿಂಗಳ ಅಪರಾಧ" : `of ${MONTH_NAMES[mSel]} crime`} · ${y}`
              : `${selc.share}% ${kn ? "ಪಾಲು" : "of all crime"} · ${y}`)
          : mSel !== null
            ? `${MONTH_NAMES[mSel]} ${kn ? "ಒಟ್ಟು" : "total"} · ${y}`
            : (kn ? `${y} ರ ಸೀಸನಲ್ ಲಯ` : `seasonal rhythm · ${y}`)}</span>
      </div>

      {/* legend - top-left, leader-dot style, with a selector for EVERY crime type */}
      <div className="bsx-cg-legend">
        <label className="bsx-cg-pick">
          <span>{kn ? "ಅಪರಾಧ ಆಯ್ಕೆ" : "Select crime"}</span>
          <select value={sel || ""} onChange={(e) => setSel(e.target.value || null)}
                  aria-label={kn ? "ಅಪರಾಧ ಪ್ರಕಾರ ಆಯ್ಕೆಮಾಡಿ" : "Select a crime type to analyse"}>
            <option value="">{kn ? "ಎಲ್ಲಾ ಅಪರಾಧಗಳು" : "All crimes"}</option>
            {model.allCats.map((c) => (
              <option key={c.cat} value={c.cat}>{c.label} · {c.n.toLocaleString()}</option>
            ))}
          </select>
        </label>
        {model.cats.map((c) => (
          <button key={c.cat} className={`row ${sel === c.cat ? "on" : sel ? "off" : ""}`} onClick={() => setSel(sel === c.cat ? null : c.cat)}
                  title={c.members?.length ? `${c.label}: ${c.members.join(", ")}` : c.label}>
            <i style={{ background: c.color }} />
            <span className="ln" style={{ borderColor: c.color }} />
            <span className="nm">{c.label}</span>
            <span className="ct">{countOf(c).toLocaleString()}</span>
          </button>
        ))}
        {/* Under the legend: the free column, never covered by the crime detail panel. */}
        <SummaryToggle lines={sumLines} kn={kn} className="bsx-cg-summary"
                       footer={kn ? "D · ಈ ಗಡಿಯಾರದ ಎಣಿಕೆಗಳಿಂದ" : "D · counted from the FIRs on this clock"} />
      </div>

      {/* annotation - top-right (reference paragraph) */}
      <div className="bsx-cg-note" style={{ lineHeight: "1.6", width: "360px" }}>
        {kn
          ? <div><b style={{color: "#fff"}}>ಪ್ರತಿ ಗೆರೆ</b> = ಒಂದು ಅಪರಾಧ ಪ್ರಕಾರ. ಡಯಲ್‌ನಿಂದ ದೂರ = ಆ 10-ದಿನದ ಅವಧಿಯ FIR ಹೊರೆ. ಜನವರಿ ಮೇಲೆ, ಪ್ರದಕ್ಷಿಣೆ ದಿಕ್ಕು.<br/><br/><span style={{color: "#22E6F0"}}>ಗೆರೆ ಕ್ಲಿಕ್ ಮಾಡಿ</span> - ಅದರ ಚಕ್ರ ಪ್ರತ್ಯೇಕಗೊಳ್ಳುತ್ತದೆ.</div>
          : <div><b style={{color: "#fff"}}>When and where each crime happens.</b> Each trace is one crime type across the year (January at the top, clockwise); further from the dial means more FIRs in that 10-day window.<br/><br/><span style={{color: "#22E6F0"}}>Pick a crime</span> from the list or click its trace to see its peak month and weekday, and the districts and stations where it concentrates.</div>}
      </div>

      {/* title block - bottom-left */}
      <div className="bsx-cg-title">
        <b>{kn ? "ಅಪರಾಧ ಚಕ್ರಗಳು (ವರ್ಷ ಆಧಾರಿತ)" : "Crime Cycles based on Years"}</b>
        
        {y === "All" && apiData?.scope_years?.length > 0 && (
          <div className="bsx-cg-scope">
            {kn ? "ಪೂರ್ಣ ವರ್ಷಗಳು" : "Complete years"} {apiData.scope_years[0]}–{apiData.scope_years[apiData.scope_years.length - 1]}
            {apiData.partial_years?.length > 0 && (
              <> · {apiData.partial_years.join(", ")} {kn ? "ಅಪೂರ್ಣ - ಕೆಳಗೆ ಆಯ್ಕೆಮಾಡಿ" : "partial, shown on their own chips"}</>
            )}
          </div>
        )}
        {/* year navigation - moved under title */}
        <div className="bsx-cg-years">
          {years.map((yy) => {
            const info = yearInfo[yy];
            const chipLabel = yy === "All" ? "All"
              : info && info.months_covered < 12 ? yearLabel(info) : String(yy);
            return (
              <button key={yy} className={yy === year ? "on" : ""} aria-pressed={yy === year} onClick={() => { if (yy !== year) { setYear(yy); setSelMonth(null); setSel(null); } }}>{chipLabel}</button>
            );
          })}
        </div>
      </div>

      {/* detail panel - right, on selection */}
      {selc && (
        <aside className="bsx-cg-detail">
          <button className="bs-detail-close" onClick={() => setSel(null)}></button>
          <span className="eyebrow" style={{ color: selc.color }}>{kn ? "ಅಪರಾಧ ಚಕ್ರ" : "crime cycle"} · {y}</span>
          <b>{selc.label}</b>
          <CrimePlan c={selc} p={profile} kn={kn} y={y} lastYear={apiData?.scope_years?.[apiData.scope_years.length - 1]}
                     onAsk={(q) => router.push(`/antar?q=${encodeURIComponent(q)}`)} />
          <div className="stats">
            <div><span className="k">{kn ? "FIR ಗಳು" : "FIRs"}</span><span className="v">{selc.n.toLocaleString()}</span></div>
            <div><span className="k">{kn ? "ಪಾಲು" : "share"}</span><span className="v">{selc.share}%</span></div>
          </div>
          <div className="bars">
            {selc.byMonth.map((v, i) => (
              <div key={i} className="b" title={`${MONTHS[i]} · ${v.toLocaleString()}`}>
                <i style={{ height: `${Math.round((v / Math.max(1, ...selc.byMonth)) * 100)}%`,
                            background: i === selc.peak ? selc.color : "rgba(157,171,188,.35)",
                            outline: i === mSel ? "1px solid #fff" : "none", outlineOffset: 1 }} />
                <em>{MONTHS[i][0]}</em>
              </div>
            ))}
          </div>
          <div className="kv">{kn ? "ಉತ್ತುಂಗ" : "Peak"}: <b>{MONTH_NAMES[selc.peak]}</b> · {kn ? "ಶಾಂತ" : "quietest"}: <b>{MONTH_NAMES[selc.quiet]}</b></div>
          {mSel !== null && (
            <div className="kv">{MONTH_NAMES[mSel]}: <b>{selc.byMonth[mSel].toLocaleString()}</b> FIRs</div>
          )}
          <CrimeProfile p={profile} kn={kn} color={selc.color} />
        </aside>
      )}
    </div>
  );
}
