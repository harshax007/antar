"use client";

import { useEffect, useMemo, useState } from "react";
import TypingSearchInput from "@/components/TypingSearchInput";
import { SummaryToggle } from "@/components/BrainViewSummary";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  AreaChart, Area, CartesianGrid,
} from "recharts";
import { useLang } from "@/components/Providers";
import { CATEGORIES, categorize, filterRecords, overviewStats } from "@/lib/crimeGraph";

// The FIR list closes the page: a short page of rows, with the pager to go further.
const PAGE = 8;
const CYAN = "#22E6F0";
const API = (process.env.NEXT_PUBLIC_API_URL || "");

const AXIS = { fontSize: 11, fill: "#8492A6", fontFamily: "Inter, system-ui, sans-serif" };
const TIP = {
  contentStyle: { background: "#0B1220", border: "1px solid rgba(255,255,255,.1)", borderRadius: 10, fontSize: 12 },
  labelStyle: { color: "#F2F5FA" }, itemStyle: { color: CYAN }, cursor: { fill: "rgba(34,230,240,.06)" },
};
// Single-hue sequential ramp (magnitude, not identity) - keeps the page to one accent.
const ramp = (i, n) => 0.92 - (n > 1 ? (i / (n - 1)) * 0.6 : 0);
const nf = (v) => (v || 0).toLocaleString();
// Axis ticks as 12k / 1.2L - full numbers ("300000") were clipped at the chart edge.
const compact = (v) => (v >= 100000 ? `${+(v / 100000).toFixed(1)}L` : v >= 1000 ? `${+(v / 1000).toFixed(1)}k` : String(v));
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const monLabel = (ym) => { const [y, m] = String(ym).split("-"); return `${MON[Number(m) - 1]} ${String(y).slice(2)}`; };

// Screen 03 · Page 02 - FIR Data Overview. Every number here is computed from the
// loaded FIR records (no hardcoded totals). Same records + shared selection as the
// globe above: click a chart element and the globe morphs; the globe's timeline
// filters drive these charts and the table.
// Linked records: what joins them. An identifier on two or more FIRs is a link an officer can
// follow - the same accused, vehicle, UPI ID or IP address - and one that spans districts is
// where one station's case is another station's lead.
const LINK_KEYS = [
  ["Accused_ID", "accused"], ["UPI_ID", "upi"], ["Vehicle_Reg_No", "vehicle"], ["IP_Address", "ip"],
];

function linkStats(rows) {
  const out = { linkedFirs: 0, crossDistrict: 0, top: {} };
  const linkedIdx = new Set();
  for (const [field, kind] of LINK_KEYS) {
    const groups = new Map();
    rows.forEach((r, i) => {
      const v = String(r[field] || "").trim();
      if (v) (groups.get(v) || groups.set(v, []).get(v)).push(i);
    });
    let shared = 0, best = null;
    for (const [v, idx] of groups) {
      if (idx.length < 2) continue;
      shared += 1;
      idx.forEach((i) => linkedIdx.add(i));
      const districts = new Set(idx.map((i) => rows[i].District_Name).filter(Boolean));
      if (districts.size > 1) out.crossDistrict += 1;
      const cand = { value: v, firs: idx.length, districts: districts.size, names: [...districts].sort() };
      if (!best || cand.firs > best.firs || (cand.firs === best.firs && cand.districts > best.districts)) best = cand;
    }
    out[kind] = shared;
    out.top[kind] = best;
  }
  out.linkedFirs = linkedIdx.size;
  out.demo = rows.filter((r) => r.has_synthetic_link === 1 || r.has_synthetic_link === "1").length;
  return out;
}

export default function DataOverview({ recs, sel, setSel, onJumpTop, onFocusBrain }) {
  const { lang } = useLang();
  const kn = lang === "kn";
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const [fir, setFir] = useState(null);   // clicked FIR record → detail card
  // "sample" = the CSV the brain renders; "full" = the whole antar.db FIRs table.
  // The brain above always keeps rendering the sample - only this page switches.
  const [source, setSource] = useState("full");
  const [full, setFull] = useState(null);        // /api/dataset/overview
  const [fullRows, setFullRows] = useState(null); // /api/dataset/records
  const [fullErr, setFullErr] = useState(false);
  const [officer, setOfficer] = useState(null);   // /api/dataset/officer_view
  const isFull = source === "full";
  // Full-dataset range filters (year span + FIR id window) - server-side.
  const [yFrom, setYFrom] = useState("");
  const [yTo, setYTo] = useState("");
  const [idFrom, setIdFrom] = useState("");
  const [idTo, setIdTo] = useState("");
  const YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];

  const filtered = useMemo(() => (recs ? filterRecords(recs, sel) : []), [recs, sel]);
  const stats = useMemo(() => overviewStats(filtered), [filtered]);

  const activeCat0 = sel.cats && sel.cats.size === 1 ? [...sel.cats][0] : null;

  // Crime-group names belonging to the selected category. Categorisation stays defined
  // in lib/crimeGraph (one source of truth); we just expand it into names the API filters on.
  const groupParam = useMemo(() => {
    if (!activeCat0 || !full?.by_crime_group) return "";
    return full.by_crime_group
      .filter((g) => categorize(g.name) === activeCat0)
      .map((g) => g.name).join(",");
  }, [activeCat0, full]);

  const filterQS = useMemo(() => {
    const p = new URLSearchParams();
    if (sel.year) p.set("year", sel.year);
    if (sel.district) p.set("district", sel.district);
    if (groupParam) p.set("groups", groupParam);
    if (isFull) {
      if (yFrom) p.set("year_from", yFrom);
      if (yTo) p.set("year_to", yTo);
      if (String(idFrom).trim()) p.set("id_from", String(idFrom).trim());
      if (String(idTo).trim()) p.set("id_to", String(idTo).trim());
    }
    return p.toString();
  }, [sel.year, sel.district, groupParam, isFull, yFrom, yTo, idFrom, idTo]);

  // Any range-filter change returns to page 1 so the table isn't stranded past the end.
  useEffect(() => { setPage(0); }, [yFrom, yTo, idFrom, idTo]);

  // Full-dataset aggregates (re-fetched when the shared filters change)
  useEffect(() => {
    if (!isFull) return;
    let alive = true;
    fetch(`${API}/api/dataset/summary${filterQS ? `?${filterQS}` : ""}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => { if (alive) { setFull(d); setFullErr(false); } })
      .catch(() => { if (alive) setFullErr(true); });
    return () => { alive = false; };
  }, [isFull, filterQS]);

  // What an officer acts on: the chargesheet-deadline clock, outcome rates and the
  // 24-month trend, for the same filters as the tiles above.
  useEffect(() => {
    if (!isFull) return;
    let alive = true;
    setOfficer(null);
    fetch(`${API}/api/dataset/officer_view${filterQS ? `?${filterQS}` : ""}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => { if (alive) setOfficer(d); })
      .catch(() => { if (alive) setOfficer({ error: true }); });
    return () => { alive = false; };
  }, [isFull, filterQS]);

  // Full-dataset table rows (server-side paging + search, debounced)
  useEffect(() => {
    if (!isFull) return;
    let alive = true;
    const t = setTimeout(() => {
      const p = new URLSearchParams(filterQS);
      p.set("limit", PAGE);
      p.set("offset", page * PAGE);
      if (q.trim()) p.set("q", q.trim());
      fetch(`${API}/api/dataset/records?${p.toString()}`)
        .then((r) => (r.ok ? r.json() : Promise.reject()))
        .then((d) => {
          if (!alive) return;
          setFullRows({ ...d, rows: d.rows.map((r) => ({ ...r, _cat: categorize(r.CrimeGroup_Name) })) });
          setFullErr(false);
        })
        .catch(() => { if (alive) setFullErr(true); });
    }, 280);
    return () => { alive = false; clearTimeout(t); };
  }, [isFull, filterQS, page, q]);

  function switchSource(next) {
    setSource(next);
    setPage(0);
  }

  // Real investigation-stage split (replaces the previously hardcoded counts).
  const sampleStages = useMemo(() => {
    const m = new Map();
    filtered.forEach((r) => {
      const s = String(r.FIR_Stage || "Unknown").trim() || "Unknown";
      m.set(s, (m.get(s) || 0) + 1);
    });
    return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([label, n]) => ({ label, n }));
  }, [filtered]);

  const links = useMemo(() => linkStats(filtered), [filtered]);

  // A use case's action: the FIRs behind it, both in the Brain above (focused on that key's
  // linked group) and in the FIR records table below. Not Chat or Search: those read the
  // 10-lakh register, where some of these identifiers do not exist, so a button there could
  // answer "no FIRs" for a link this page just showed.
  function showFirs(key) {
    setQ(key);
    setPage(0);
    if (onFocusBrain) onFocusBrain(key);
    else requestAnimationFrame(() => document.querySelector(".ov-tablewrap")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  const sampleRows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return filtered;
    return filtered.filter((r) =>
      [r.District_Name, r.UnitName, r.CrimeGroup_Name, r.CrimeHead_Name, r.Accused_ID, r.Place_of_Offence,
       r.Vehicle_Reg_No, r.UPI_ID, r.IP_Address]
        .some((v) => v && String(v).toLowerCase().includes(needle)));
  }, [filtered, q]);

  // Table: client-side slice for the sample, server-side paging for the full dataset.
  const tableTotal = isFull ? (fullRows?.total ?? 0) : sampleRows.length;
  const pages = Math.max(1, Math.ceil(tableTotal / PAGE));
  const pageRows = isFull ? (fullRows?.rows ?? []) : sampleRows.slice(page * PAGE, page * PAGE + PAGE);
  useEffect(() => { if (page >= pages) setPage(0); }, [pages, page]);

  // Full-dataset crime groups → the same 15 analytic categories the sample uses.
  const fullByCategory = useMemo(() => {
    if (!full?.by_crime_group) return [];
    const m = new Map();
    full.by_crime_group.forEach((g) => {
      const cat = categorize(g.name);
      m.set(cat, (m.get(cat) || 0) + g.n);
    });
    return [...m.entries()].sort((a, b) => b[1] - a[1])
      .map(([cat, n]) => ({ cat, label: CATEGORIES[cat]?.label || cat, n }));
  }, [full]);

  // One view model - every KPI, chart and bar below reads from this, so flipping the
  // source switches the whole page at once (the brain above is deliberately untouched).
  const view = isFull
    ? {
        total: full?.total ?? 0, districts: full?.districts ?? 0, stations: full?.stations ?? 0,
        victims: full?.victims ?? 0, accused: full?.accused ?? 0, arrested: full?.arrested ?? 0,
        chargesheeted: full?.chargesheeted ?? 0, convictions: full?.convictions ?? 0,
        arrestRate: full?.arrest_rate ?? 0, stages: full?.stages ?? [],
        byCategory: fullByCategory, years: full?.years ?? [], topDistricts: full?.top_districts ?? [],
      }
    : {
        total: stats.total, districts: stats.districts, stations: stats.stations,
        victims: stats.victims, accused: stats.accused, arrested: stats.arrested,
        chargesheeted: stats.chargesheeted, convictions: stats.convictions,
        arrestRate: stats.arrestRate, stages: sampleStages,
        byCategory: stats.byCategory, years: stats.years, topDistricts: stats.topDistricts,
      };

  const activeCat = activeCat0;

  function pickCat(cat) { setSel({ ...sel, cats: activeCat === cat ? null : new Set([cat]) }); }
  function pickYear(year) { setSel({ ...sel, year: sel.year === year ? null : year, month: null }); }
  function pickDistrict(district) { setSel({ ...sel, district: sel.district === district ? null : district }); }

  const chips = [
    sel.year && { k: "year", label: sel.month ? `${sel.year}-${String(sel.month).padStart(2, "0")}` : String(sel.year), clear: () => setSel({ ...sel, year: null, month: null }) },
    sel.district && { k: "district", label: sel.district, clear: () => setSel({ ...sel, district: null }) },
    activeCat && { k: "cat", label: CATEGORIES[activeCat]?.label || activeCat, clear: () => setSel({ ...sel, cats: null }) },
  ].filter(Boolean);

  // While the full-dataset summary is in flight `view` is built from `?? 0` fallbacks, so
  // every tile read "0 FIRs total · 0% arrest rate" - indistinguishable from an empty
  // database. Loading renders as a placeholder instead; a real zero stays a zero.
  const loadingFull = isFull && !full && !fullErr;

  const pctOf = (a, b) => (b ? Math.round((100 * a) / b) : 0);
  const kpis = !isFull ? [
    { v: nf(view.total), l: kn ? "ಈ ನೋಟದ FIR ಗಳು" : "FIRs in view", accent: true },
    { v: `${pctOf(links.linkedFirs, view.total)}%`, l: kn ? "ಇನ್ನೊಂದು ಪ್ರಕರಣಕ್ಕೆ ಸಂಪರ್ಕಿತ" : "Linked to another case",
      h: kn ? `${nf(links.linkedFirs)} FIR ಗಳು` : `${nf(links.linkedFirs)} FIRs share a key` },
    { v: nf(links.accused), l: kn ? "ಪುನರಾವರ್ತಿತ ಆರೋಪಿಗಳು" : "Repeat accused", h: kn ? "2+ FIR ಗಳಲ್ಲಿ" : "named in 2+ FIRs" },
    { v: nf(links.upi), l: kn ? "ಹಂಚಿದ UPI ಐಡಿಗಳು" : "Shared UPI IDs", h: kn ? "ಮ್ಯೂಲ್ ಖಾತೆಗಳಾಗಿರಬಹುದು" : "possible mule accounts" },
    { v: nf(links.vehicle), l: kn ? "ಹಂಚಿದ ವಾಹನಗಳು" : "Shared vehicles", h: kn ? "ಹಲವು ಪ್ರಕರಣಗಳಲ್ಲಿ" : "used in several cases" },
    { v: nf(links.ip), l: kn ? "ಹಂಚಿದ IP ವಿಳಾಸಗಳು" : "Shared IP addresses", h: kn ? "ಸೈಬರ್ ಪ್ರಕರಣಗಳು" : "behind cyber cases" },
    { v: nf(links.crossDistrict), l: kn ? "ಜಿಲ್ಲೆಗಳಾದ್ಯಂತ ಸಂಪರ್ಕಗಳು" : "Links across districts", accent: true,
      h: kn ? "ಇನ್ನೊಂದು ಠಾಣೆಯ ಸುಳಿವು" : "another station's lead" },
  ] : [
    { v: nf(view.total), l: isFull ? (kn ? "ಒಟ್ಟು FIR" : "Total FIRs") : (kn ? "FIR ಗಳು" : "FIRs in view"), accent: true },
    { v: nf(view.victims), l: kn ? "ಸಂತ್ರಸ್ತರು" : "Victims" },
    { v: nf(view.accused), l: kn ? "ಆರೋಪಿಗಳು" : "Accused" },
    { v: nf(view.arrested), l: kn ? "ಬಂಧಿತರು" : "Arrested" },
    { v: nf(view.chargesheeted), l: kn ? "ದೋಷಾರೋಪ" : "Charge-sheeted" },
    { v: nf(view.convictions), l: kn ? "ಶಿಕ್ಷೆಗಳು" : "Convictions" },
    { v: `${view.arrestRate}%`, l: kn ? "ಬಂಧನ ದರ" : "Arrest rate", accent: true },
  ];

  // Suggested searches, typed into the empty box: real accused ids from the rows on this
  // page (so every suggestion is guaranteed to hit), then a station name.
  const suggestIds = useMemo(() => {
    const ids = [...new Set((pageRows || []).map((r) => r.Accused_ID).filter(Boolean))].slice(0, 3);
    const st = (pageRows || []).find((r) => r.UnitName)?.UnitName;
    return st ? [...ids, st] : ids;
  }, [pageRows]);

  // View summary for this page - rebuilt whenever a filter or the data changes.
  const summaryLines = useMemo(() => {
    if (isFull && !full) return [];
    const out = [];
    const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);
    const scope = [
      sel.year ? String(sel.year) : (yFrom || yTo) ? `${yFrom || "…"}–${yTo || "…"}` : (kn ? "ಎಲ್ಲಾ ವರ್ಷಗಳು" : "all years"),
      sel.district, activeCat ? (CATEGORIES[activeCat]?.label || activeCat) : null,
    ].filter(Boolean).join(" · ");
    out.push(kn
      ? `ಈ ಪುಟ ${nf(view.total)} FIR ಗಳನ್ನು ತೋರಿಸುತ್ತದೆ - ${scope}${isFull ? "" : " (ಬ್ರೈನ್ ಮಾದರಿ)"}.`
      : `This page covers ${nf(view.total)} FIRs - ${scope}${isFull ? "" : " (the Brain's linked sample)"}.`);
    const c0 = view.byCategory[0], d0 = view.topDistricts[0];
    if (c0) out.push(kn ? `ದೊಡ್ಡ ಅಪರಾಧ ವರ್ಗ: ${c0.label} (${nf(c0.n)}, ${pct(c0.n, view.total)}%).` : `Largest crime category: ${c0.label} (${nf(c0.n)}, ${pct(c0.n, view.total)}%).`);
    if (d0) out.push(kn ? `ಹೆಚ್ಚು FIR ಇರುವ ಜಿಲ್ಲೆ: ${d0.district} (${nf(d0.n)}, ${pct(d0.n, view.total)}%).` : `Busiest district: ${d0.district} (${nf(d0.n)}, ${pct(d0.n, view.total)}%).`);
    const s0 = view.stages[0];
    if (s0) out.push(kn ? `ಹೆಚ್ಚಿನ ಪ್ರಕರಣಗಳು "${s0.label}" ಹಂತದಲ್ಲಿವೆ (${nf(s0.n)}).` : `Most cases are at "${s0.label}" (${nf(s0.n)}).`);
    const d = officer?.deadline;
    if (d && d.open_total) {
      const st = d.top_stations_over_90?.[0];
      out.push(kn
        ? `${nf(d.over_90)} ತನಿಖೆಗಳು 90 ದಿನ ದಾಟಿವೆ; ${nf(d.due_7)} ಈ ವಾರ ಗಡುವು ತಲುಪುತ್ತವೆ.${st ? ` ಹೆಚ್ಚು: ${st.name} (${nf(st.n)}).` : ""}`
        : `${nf(d.over_90)} open investigations are past the 90-day limit; ${nf(d.due_7)} reach a limit this week.${st ? ` Most overdue: ${st.name} (${nf(st.n)}).` : ""}`);
    }
    const per = officer?.outcomes?.per_100;
    if (per) out.push(kn
      ? `ಪ್ರತಿ 100 FIR ಗೆ: ${Math.round(per.arrest)} ಬಂಧನ, ${Math.round(per.chargesheet)} ದೋಷಾರೋಪ, ${Math.round(per.conviction)} ಶಿಕ್ಷೆ.`
      : `Of every 100 FIRs: ${Math.round(per.arrest)} saw an arrest, ${Math.round(per.chargesheet)} a chargesheet, ${Math.round(per.conviction)} a conviction.`);
    // Direction: last 3 complete months vs the 3 before (the running month is left out).
    const cur = new Date().toISOString().slice(0, 7);
    const m = (officer?.monthly || []).filter((x) => x.n != null && x.month !== cur);
    if (m.length >= 6) {
      const a = m.slice(-3).reduce((t, x) => t + x.n, 0), b = m.slice(-6, -3).reduce((t, x) => t + x.n, 0);
      if (b) {
        const ch = Math.round((100 * (a - b)) / b);
        out.push(kn
          ? `ಕೊನೆಯ 3 ಪೂರ್ಣ ತಿಂಗಳು ಹಿಂದಿನ 3 ಕ್ಕಿಂತ ${ch >= 0 ? `${ch}% ಹೆಚ್ಚು` : `${-ch}% ಕಡಿಮೆ`} (${nf(a)} vs ${nf(b)}).`
          : `The last 3 complete months are ${Math.abs(ch) < 3 ? "flat" : ch > 0 ? `up ${ch}%` : `down ${-ch}%`} on the 3 before (${nf(a)} vs ${nf(b)} FIRs).`);
      }
    }
    return out;
  }, [isFull, full, view, officer, sel.year, sel.district, activeCat, yFrom, yTo, kn]);

  const catN = view.byCategory.length;
  const distN = view.topDistricts.length;
  const stages = view.stages;
  const stageMax = Math.max(...stages.map((s) => s.n), 1);

  return (
    <section className="ov-page" id="data-overview" style={{ scrollMarginTop: "20px" }}>
      <div className="ov-head">
        <div>
          <div className="ov-eyebrow">{kn ? "02 · FIR ದತ್ತಾಂಶ ಅವಲೋಕನ" : "02 · FIR data overview"}</div>
          <h2 className="ov-title">
            {isFull 
              ? (kn ? "ಸಂಪೂರ್ಣ ದತ್ತಾಂಶದ ಒಳನೋಟ" : "The full dataset, in focus")
              : (kn ? "ಸಂಪರ್ಕಿತ ದಾಖಲೆಗಳು: ಒಂದಕ್ಕೊಂದು ಜೋಡಿಸುವ ಪ್ರಕರಣಗಳು" : "Linked records: the cases that connect")
            }
          </h2>

          {/* Source switch: sample (what the brain renders) ⇄ the whole antar.db */}
          <div className="ov-src">
            <div className="ov-srcseg">
              <button className={!isFull ? "on" : ""} onClick={() => switchSource("sample")}>
                {kn ? "ಮಾದರಿ (ಬ್ರೈನ್)" : "Linked records"}
              </button>
              <button className={isFull ? "on" : ""} onClick={() => switchSource("full")}>
                {kn ? "ಪೂರ್ಣ ದತ್ತಾಂಶ" : "Full Data Set"}
              </button>
            </div>
            <span className="ov-srcnote">
              {isFull
                ? (fullErr
                    ? (kn ? "ಬ್ಯಾಕೆಂಡ್ ತಲುಪಿಲ್ಲ - ಆಂತರ API ಪ್ರಾರಂಭಿಸಿ" : "Backend unreachable - start the Antar API")
                    : full
                      ? (
                          <span>
                            <b>
                              {kn ? "ಎಲ್ಲಾ FIR ದಾಖಲೆಗಳು" : "Every FIR record in the registry."}
                            </b>
                            <small>
                              {kn ? "ಫಿಲ್ಟರ್ ಮಾಡದ, ಸಂಪೂರ್ಣ ಡೇಟಾಬೇಸ್‌ಗೆ ಪ್ರವೇಶ. ಎಲ್ಲಾ ಐತಿಹಾಸಿಕ ದಾಖಲೆಗಳನ್ನು ಯಾವುದೇ ಮಾದರಿಯಿಲ್ಲದೆ ಪ್ರಕ್ರಿಯೆಗೊಳಿಸಲಾಗಿದೆ." : "Every row is counted, nothing is sampled. Years from 2016 to 2022 hold only part of each year, and rows after March 2024 are demonstration data."}
                            </small>
                          </span>
                        )
                      : (kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Loading full dataset…"))
                : (
                  <span>
                    <b>
                      {kn ? "ಬುದ್ಧಿವಂತ ದತ್ತಾಂಶ: ಇತರ ಪ್ರಕರಣಗಳಿಗೆ ಜೋಡಿಸುವ FIR ಗಳು." : "Intelligent data: FIRs that connect to other FIRs."}
                    </b>
                    <small>
                      {kn
                        ? `10 ಲಕ್ಷ FIR ರಿಜಿಸ್ಟರ್‌ನ ಅದೇ KSP ಸ್ವರೂಪದಲ್ಲಿರುವ ${nf(view.total)} FIR ಗಳ ಆಯ್ದ ಸಂಗ್ರಹ, ಪ್ರಕರಣಗಳು ಹೇಗೆ ಜೋಡಿಸುತ್ತವೆ ಎಂದು ತೋರಿಸಲು: ಇವುಗಳಲ್ಲಿ ${nf(links.linkedFirs)} ಒಂದೇ ಆರೋಪಿ, ವಾಹನ, UPI ಐಡಿ ಅಥವಾ IP ವಿಳಾಸವನ್ನು ಇಲ್ಲಿನ ಇನ್ನೊಂದು FIR ಜೊತೆ ಹಂಚಿಕೊಳ್ಳುತ್ತವೆ. ಬ್ರೈನ್ ಇವುಗಳನ್ನೇ ಮೇಲೆ ಚಿತ್ರಿಸುತ್ತದೆ.${links.demo ? ` ${pctOf(links.demo, view.total)}% ದಾಖಲೆಗಳಲ್ಲಿ ಪ್ರದರ್ಶನ ಸಂಪರ್ಕವಿದೆ.` : ""}`
                        : `A curated set of ${nf(view.total)} FIRs in the same KSP format as the 10-lakh FIR register, built to show how cases connect: ${nf(links.linkedFirs)} of them share an accused, vehicle, UPI ID or IP address with another FIR here - the links an investigation can follow across stations. The Brain above draws exactly these.${links.demo ? ` ${pctOf(links.demo, view.total)}% of records carry a demonstration link, marked as such.` : ""}`}
                    </small>
                  </span>
                )}
            </span>
          </div>

          {/* Full-dataset range filters: year span + FIR id window (server-side). */}
          {isFull && (
            <div className="ov-rangefilters ov-range">
              <label htmlFor="ov-yfrom">{kn ? "ವರ್ಷ ವ್ಯಾಪ್ತಿ" : "Year range"}</label>
              <select id="ov-yfrom" className="ov-rf-sel" value={yFrom} onChange={(e) => setYFrom(e.target.value)} aria-label={kn ? "ಇಂದ ವರ್ಷ" : "From year"}>
                <option value="">{kn ? "ಇಂದ" : "From"}</option>
                {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
              <span className="sep" aria-hidden="true">to</span>
              <select className="ov-rf-sel" value={yTo} onChange={(e) => setYTo(e.target.value)} aria-label={kn ? "ವರೆಗೆ ವರ್ಷ" : "To year"}>
                <option value="">{kn ? "ವರೆಗೆ" : "To"}</option>
                {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
              <span className="gap" aria-hidden="true" />
              <label htmlFor="ov-idfrom">{kn ? "FIR ವ್ಯಾಪ್ತಿ" : "FIR range"}</label>
              <input id="ov-idfrom" type="number" min={1} value={idFrom} onChange={(e) => setIdFrom(e.target.value)} placeholder={kn ? "ಇಂದ" : "From"} aria-label="FIR id from" />
              <span className="sep" aria-hidden="true">to</span>
              <input type="number" min={1} value={idTo} onChange={(e) => setIdTo(e.target.value)} placeholder={kn ? "ವರೆಗೆ" : "To"} aria-label="FIR id to" />
              {(yFrom || yTo || idFrom || idTo) && (
                <button onClick={() => { setYFrom(""); setYTo(""); setIdFrom(""); setIdTo(""); }}>
                  {kn ? "ವ್ಯಾಪ್ತಿ ತೆರವು" : "Clear range"}
                </button>
              )}
            </div>
          )}
        </div>
        <div className="ov-chips">
          <SummaryToggle lines={summaryLines} kn={kn} className="ov-summary"
                         footer={kn ? "D · ಈ ಪುಟದ ಎಣಿಕೆಗಳಿಂದ" : "D · counted from the FIRs on this page"} />
          {chips.map((c) => (
            <span key={c.k} className="ov-chip">{c.label}<button onClick={c.clear} aria-label="Clear"></button></span>
          ))}
          {chips.length > 0 && (
            <button className="ov-sync" onClick={() => setSel({ year: null, month: null, day: null, district: null, cats: null })}>
              {kn ? "ಎಲ್ಲಾ ತೆರವು" : "Clear all"}
            </button>
          )}
        </div>
      </div>

      <div className="ov-kpis">
        {kpis.map((k, i) => (
          <div key={i} className={`ov-kpi${loadingFull ? " is-loading" : ""}`} aria-busy={loadingFull}>
            {loadingFull
              ? <b className="ov-skel" aria-label={kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ" : "loading"}>&nbsp;</b>
              : <b className={k.accent ? "on" : ""}>{k.v}</b>}
            <span>{k.l}</span>
            {k.h && <small className="ov-kpi-h">{k.h}</small>}
          </div>
        ))}
      </div>

      {/* ── Linked records: what an officer can do with the links, from the records in view ── */}
      {!isFull && (() => {
        const t = links.top;
        const where = (x) => (x.districts > 1 ? (kn ? `${x.districts} ಜಿಲ್ಲೆಗಳಲ್ಲಿ` : `across ${x.districts} districts`) : (kn ? `${x.names[0] || ""} ನಲ್ಲಿ` : `in ${x.names[0] || "one district"}`));
        const cases = [
          t.accused && {
            k: "accused", tag: kn ? "ಪುನರಾವರ್ತಿತ ಆರೋಪಿ" : "Follow a repeat offender",
            fact: kn ? `${t.accused.value} ${t.accused.firs} FIR ಗಳಲ್ಲಿ, ${where(t.accused)}.` : `${t.accused.value} is named in ${t.accused.firs} FIRs ${where(t.accused)}.`,
            why: kn ? "ಎಲ್ಲಾ ಠಾಣೆಗಳ ಪ್ರಕರಣಗಳನ್ನು ಒಂದೇ ಕಡತದಲ್ಲಿ ನೋಡಿ." : "See every station's cases on one person, in one file.",
            act: kn ? `${t.accused.firs} FIR ಗಳನ್ನು ತೋರಿಸಿ` : `Show the ${t.accused.firs} FIRs`, go: () => showFirs(t.accused.value),
          },
          t.upi && {
            k: "upi", tag: kn ? "ಮ್ಯೂಲ್ ಖಾತೆ ಪತ್ತೆ" : "Trace a money-mule account",
            fact: kn ? `UPI ${t.upi.value} ${t.upi.firs} FIR ಗಳಲ್ಲಿ, ${where(t.upi)}.` : `UPI ID ${t.upi.value} appears in ${t.upi.firs} FIRs ${where(t.upi)}.`,
            why: kn ? "ಒಂದೇ ಖಾತೆಗೆ ಹಣ ಕಳುಹಿಸಿದ ಸಂತ್ರಸ್ತರು - ಬ್ಯಾಂಕ್‌ಗೆ ಒಂದೇ ನೋಟಿಸ್." : "Victims who paid one account - one notice to the bank covers them all.",
            act: kn ? `${t.upi.firs} FIR ಗಳನ್ನು ತೋರಿಸಿ` : `Show the ${t.upi.firs} FIRs`, go: () => showFirs(t.upi.value),
          },
          t.vehicle && {
            k: "vehicle", tag: kn ? "ವಾಹನ ಹಿಂಬಾಲಿಸಿ" : "Track a vehicle",
            fact: kn ? `${t.vehicle.value} ${t.vehicle.firs} FIR ಗಳಲ್ಲಿ, ${where(t.vehicle)}.` : `Vehicle ${t.vehicle.value} is in ${t.vehicle.firs} FIRs ${where(t.vehicle)}.`,
            why: kn ? "ಒಂದೇ ವಾಹನ, ಹಲವು ಘಟನೆಗಳು - ಚೆಕ್‌ಪೋಸ್ಟ್ ಎಚ್ಚರಿಕೆಗೆ ಯೋಗ್ಯ." : "One vehicle, several incidents - worth a checkpost alert.",
            act: kn ? `${t.vehicle.firs} FIR ಗಳನ್ನು ತೋರಿಸಿ` : `Show the ${t.vehicle.firs} FIRs`, go: () => showFirs(t.vehicle.value),
          },
          t.ip && {
            k: "ip", tag: kn ? "ಸೈಬರ್ ಜಾಲ" : "Join up cyber cases",
            fact: kn ? `IP ${t.ip.value} ${t.ip.firs} FIR ಗಳಲ್ಲಿ, ${where(t.ip)}.` : `IP address ${t.ip.value} is behind ${t.ip.firs} FIRs ${where(t.ip)}.`,
            why: kn ? "ಬೇರೆ ಬೇರೆ ದೂರುಗಳು, ಒಂದೇ ಮೂಲ - ಒಂದೇ ತನಿಖೆ." : "Separate complaints, one source - one investigation instead of many.",
            act: kn ? `${t.ip.firs} FIR ಗಳನ್ನು ತೋರಿಸಿ` : `Show the ${t.ip.firs} FIRs`, go: () => showFirs(t.ip.value),
          },
        ].filter(Boolean);
        if (!cases.length) return null;
        return (
          <div className="ov-uses">
            <div className="ov-ptitle" style={{ margin: 0 }}>
              {kn ? "ಇದರಿಂದ ಏನು ಮಾಡಬಹುದು" : "What you can do with this"}
              <span>{kn ? "ಈ ನೋಟದ ದಾಖಲೆಗಳಿಂದ, ಪ್ರತಿಯೊಂದೂ ಪರಿಶೀಲಿಸಬೇಕಾದ ಸುಳಿವು - ಬಟನ್ ಅದರ FIR ಗಳನ್ನು ಕೆಳಗಿನ ಪಟ್ಟಿಯಲ್ಲಿ ತೋರಿಸುತ್ತದೆ" : "from the records in view - each one a lead to check; the button lists its FIRs in the table below"}</span>
            </div>
            <div className="ov-uses-grid">
              {cases.map((c) => (
                <div key={c.k} className="ov-use">
                  <span className="ov-use-tag">{c.tag}</span>
                  <b>{c.fact}</b>
                  <p>{c.why}</p>
                  <button type="button" onClick={c.go}>{c.act} →</button>
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {stages.length > 0 && (
        <div className="ov-stages">
          <div className="ov-ptitle" style={{ margin: 0 }}>
            {isFull ? (kn ? "ತನಿಖಾ ಹಂತ" : "Investigation stage") : (kn ? "ಈ ಸಂಪರ್ಕಿತ ಪ್ರಕರಣಗಳು ಎಲ್ಲಿವೆ" : "Where these linked cases stand")} <span>{kn ? "ಈ ನೋಟದ ದಾಖಲೆಗಳಿಂದ" : "from records in view"}</span>
          </div>
          <div className="ov-stagerow">
            {stages.map((s) => (
              <div key={s.label} className="ov-stage">
                <div className="ov-stage-top"><span>{s.label}</span><b>{nf(s.n)}</b></div>
                <div className="ov-stage-track"><div className="ov-stage-fill" style={{ width: `${(s.n / stageMax) * 100}%` }} /></div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── What needs action: the chargesheet clock and outcome rates ─────────── */}
      {isFull && <OfficerPanels o={officer} kn={kn} />}

      <div className="ov-charts">
        <div className="ov-panel">
          <div className="ov-ptitle"> {kn ? "ವರ್ಗವಾರು ಹಂಚಿಕೆ" : "By crime category"} <span>{kn ? "ಕ್ಲಿಕ್ = ಫಿಲ್ಟರ್" : "click to filter"}</span></div>
          {/* Grows with the category count: 17 rows in 230px overlapped two-line labels. */}
          <ResponsiveContainer width="100%" height={Math.max(230, catN * 19 + 30)}>
            <BarChart data={view.byCategory} layout="vertical" margin={{ left: 8, right: 18, top: 4, bottom: 4 }}>
              <XAxis type="number" tick={AXIS} axisLine={false} tickLine={false} tickFormatter={compact} />
              {/* interval={0}: recharts drops every other label when rows are tight, which left
                  the largest bars unnamed. Every category is labelled now. */}
              <YAxis type="category" dataKey="label" width={150} interval={0} tick={{ ...AXIS, fontSize: 9.5, fill: "#c8d2e0" }} axisLine={false} tickLine={false} />
              <Tooltip {...TIP} />
              <Bar dataKey="n" isAnimationActive={false} radius={[0, 5, 5, 0]} onClick={(d) => { const cat = d?.cat ?? d?.payload?.cat; if (cat) pickCat(cat); }} cursor="pointer">
                {view.byCategory.map((c, i) => (
                  <Cell key={c.cat} fill={CYAN} fillOpacity={activeCat && activeCat !== c.cat ? 0.16 : ramp(i, catN)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {isFull ? (
        // Full register: the 24 months ending at the latest record - the window officers
        // act on. Months with no FIRs anywhere in the register are gaps, not zeros.
        <div className="ov-panel">
          <div className="ov-ptitle">
            {kn ? "ಮಾಸಿಕ ಪ್ರವೃತ್ತಿ · ಕೊನೆಯ 24 ತಿಂಗಳು" : "Monthly trend · last 24 months"}
            <span>
              {officer?.as_of ? `${kn ? "ತನಕ" : "to"} ${monLabel(officer.as_of.slice(0, 7))}` : ""}
              {/* The newest month is usually still running - its dip is not a drop in crime. */}
              {officer?.as_of && officer.as_of.slice(0, 7) === new Date().toISOString().slice(0, 7)
                ? (kn ? " · ಈ ತಿಂಗಳು ಇನ್ನೂ ನಡೆಯುತ್ತಿದೆ" : " · last month still in progress") : ""}
            </span>
          </div>
          {!officer || officer.error ? (
            <div className="ov-panel-wait">{officer?.error ? (kn ? "ಲಭ್ಯವಿಲ್ಲ" : "Unavailable") : (kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Loading…")}</div>
          ) : (
            <ResponsiveContainer width="100%" height={230}>
              <AreaChart data={(officer.monthly || []).map((d) => ({ ...d, label: monLabel(d.month) }))}
                         margin={{ left: 0, right: 18, top: 8, bottom: 4 }}>
                <defs>
                  <linearGradient id="ovMonthly" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CYAN} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={CYAN} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,.05)" vertical={false} />
                <XAxis dataKey="label" tick={AXIS} axisLine={false} tickLine={false} interval={2} />
                <YAxis tick={AXIS} axisLine={false} tickLine={false} width={44} tickFormatter={compact} />
                <Tooltip {...TIP} formatter={(v) => (v == null ? [kn ? "ದಾಖಲೆ ಇಲ್ಲ" : "no records", ""] : [nf(v), "FIRs"])} />
                <Area type="monotone" isAnimationActive={false} dataKey="n" stroke={CYAN} strokeWidth={2} fill="url(#ovMonthly)" connectNulls={false} activeDot={{ r: 4 }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
        ) : (
        <div className="ov-panel">
          <div className="ov-ptitle">{kn ? "ವಾರ್ಷಿಕ ಪ್ರವೃತ್ತಿ" : "Yearly trend"} <span>{kn ? "ಕ್ಲಿಕ್ = ವರ್ಷ" : "click a year"}</span></div>
          <ResponsiveContainer width="100%" height={230}>
            <AreaChart data={view.years.filter((y) => !y.partial)} margin={{ left: 0, right: 18, top: 8, bottom: 4 }}
                       onClick={(st) => { const y = st?.activeLabel ?? st?.activePayload?.[0]?.payload?.year; if (y) pickYear(Number(y)); }} style={{ cursor: "pointer" }}>
              <defs>
                <linearGradient id="ovTrend" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CYAN} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={CYAN} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,.05)" vertical={false} />
              <XAxis dataKey="year" tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS} axisLine={false} tickLine={false} width={40} />
              <Tooltip {...TIP} />
              <Area type="monotone" isAnimationActive={false} dataKey="n" stroke={CYAN} strokeWidth={2} fill="url(#ovTrend)" activeDot={{ r: 5 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        )}

        <div className="ov-panel">
          <div className="ov-ptitle">{kn ? "ಟಾಪ್ ಜಿಲ್ಲೆಗಳು" : "Top districts"} <span>{kn ? "ಕ್ಲಿಕ್ = ಜಿಲ್ಲೆ" : "click a district"}</span></div>
          <ResponsiveContainer width="100%" height={230}>
            <BarChart data={view.topDistricts} layout="vertical" margin={{ left: 8, right: 18, top: 4, bottom: 4 }}>
              <XAxis type="number" tick={AXIS} axisLine={false} tickLine={false} tickFormatter={compact} />
              <YAxis type="category" dataKey="district" width={120} interval={0} tick={{ ...AXIS, fontSize: 9.5, fill: "#c8d2e0" }} axisLine={false} tickLine={false} />
              <Tooltip {...TIP} />
              <Bar dataKey="n" isAnimationActive={false} radius={[0, 5, 5, 0]} onClick={(d) => { const dt = d?.district ?? d?.payload?.district; if (dt) pickDistrict(dt); }} cursor="pointer">
                {view.topDistricts.map((d, i) => (
                  <Cell key={d.district} fill={CYAN} fillOpacity={sel.district && sel.district !== d.district ? 0.16 : ramp(i, distN)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="ov-tablewrap">
        <div className="ov-tablebar">
          <div className="ov-ptitle" style={{ margin: 0 }}>{kn ? "FIR ದಾಖಲೆಗಳು" : "FIR records"} <span>{nf(tableTotal)}</span></div>
          <TypingSearchInput className="ov-search" examples={suggestIds} prefix={kn ? "ಉದಾ: " : "e.g. "}
                 fallback={kn ? "ACC-id ನಮೂದಿಸಿ" : "Enter ACC-id"}
                 ariaLabel={kn ? "ACC-id ಅಥವಾ ಸ್ಥಳದಿಂದ ಹುಡುಕಿ" : "Search by ACC-id, station or place"}
                 value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }} />
          <div className="ov-pager">
            <button disabled={page === 0} onClick={() => setPage(page - 1)} aria-label="Previous page">‹</button>
            <span>{page + 1} / {pages}</span>
            <button disabled={page >= pages - 1} onClick={() => setPage(page + 1)} aria-label="Next page">›</button>
          </div>
        </div>
        <table className="ov-table">
          <thead>
            <tr>
              <th>{kn ? "ದಿನಾಂಕ" : "Date"}</th><th>{kn ? "ಜಿಲ್ಲೆ" : "District"}</th><th>{kn ? "ಠಾಣೆ" : "Station"}</th>
              <th>{kn ? "ಅಪರಾಧ" : "Crime"}</th><th>{kn ? "ವರ್ಗ" : "Category"}</th>
              <th>{kn ? "ಆರೋಪಿ" : "Accused"}</th><th>{kn ? "ಬಂಧಿತ" : "Arrested"}</th><th>{kn ? "ಹಂತ" : "Stage"}</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((r) => (
              <tr key={r._i} className="ov-row" tabIndex={0} role="button"
                  aria-label={`${r.CrimeHead_Name || r.CrimeGroup_Name} · ${r.District_Name}`}
                  onClick={() => setFir(r)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setFir(r); } }}>
                <td className="mono">{r._year}-{String(r._month || 0).padStart(2, "0")}</td>
                <td>{r.District_Name}</td>
                <td>{r.UnitName}</td>
                <td className="crime">{r.CrimeHead_Name || r.CrimeGroup_Name}</td>
                <td>{CATEGORIES[r._cat]?.label || r._cat}</td>
                <td className="mono">{r.Accused_ID || "—"}</td>
                <td className="mono">{r.Arrested_Count || 0}</td>
                <td className="stage">{r.FIR_Stage}</td>
              </tr>
            ))}
            {pageRows.length === 0 && <tr><td colSpan={8} className="ov-none">{kn ? "ಹೊಂದಾಣಿಕೆಯ ದಾಖಲೆಗಳಿಲ್ಲ" : "No records match this view."}</td></tr>}
          </tbody>
        </table>
      </div>

      {/* Clicked FIR → small detail card. Only fields the record actually carries. */}
      {fir && <FirCard r={fir} kn={kn} onClose={() => setFir(null)} />}
    </section>
  );
}

// ── Officer panels ────────────────────────────────────────────────────────────
// Two things a station admin acts on, both computed server-side from the FIRs in view:
//   1. the chargesheet clock - open investigations aged against the 60/90-day limits of
//      BNSS s.187(3), and where the overdue ones sit;
//   2. outcomes - of every 100 FIRs, how many saw an arrest, a chargesheet, a conviction.
// The outcome figures are rates of FIRs, not a funnel: a chargesheet can be filed against
// an accused who was never arrested, so the second can be larger than the first.
function OfficerPanels({ o, kn }) {
  // Both panels start closed: the title and its one headline figure show, the rest opens
  // when the officer asks for it.
  const [open, setOpen] = useState({ clock: false, outcomes: false });
  const toggle = (k) => setOpen((s) => ({ ...s, [k]: !s[k] }));
  if (!o) {
    return (
      <div className="ov-officer">
        <div className="ov-panel ov-skelpanel" aria-busy="true" />
        <div className="ov-panel ov-skelpanel" aria-busy="true" />
      </div>
    );
  }
  if (o.error) return null;
  const d = o.deadline || {};
  const out = o.outcomes || {};
  const total = d.open_total || 0;
  const seg = (n) => (total ? `${(100 * n) / total}%` : "0%");
  const per = out.per_100 || {};
  const acc = out.accused || {};
  const years = d.oldest_days ? Math.floor(d.oldest_days / 365) : 0;

  return (
    <div className="ov-officer">
      <div className={`ov-panel ov-clock${open.clock ? "" : " shut"}`}>
        <button className="ov-ptitle ov-toggle" onClick={() => toggle("clock")} aria-expanded={open.clock}>
          {kn ? "ದೋಷಾರೋಪ ಗಡುವು" : "Chargesheet deadline"}
          <span>{open.clock
            ? (kn ? "ತನಿಖೆಯಲ್ಲಿರುವ ಪ್ರಕರಣಗಳು · BNSS §187(3)" : "open investigations · BNSS s.187(3)")
            : `${nf(d.over_90)} ${kn ? "90 ದಿನ ದಾಟಿದವು" : "past the 90-day limit"}`}</span>
          <i aria-hidden="true">{open.clock ? "–" : "+"}</i>
        </button>
        {open.clock && (<>
          <div className="ov-clock-head">
          <div>
            <b className="ov-clock-big">{nf(d.over_90)}</b>
            <span>{kn ? "90 ದಿನ ದಾಟಿದವು" : "past the 90-day limit"}</span>
          </div>
          <div>
            <b className="ov-clock-due">{nf(d.due_7)}</b>
            <span>{kn ? "7 ದಿನಗಳಲ್ಲಿ 60/90 ಗಡುವು" : "reach 60 or 90 days within a week"}</span>
          </div>
          <div>
            <b>{nf(total)}</b>
            <span>{kn ? "ತನಿಖೆಯಲ್ಲಿ (ಇಂದಿನವರೆಗೆ ದಾಖಲಾದವು)" : "under investigation, registered up to today"}</span>
          </div>
        </div>
        <div className="ov-clock-bar" role="img"
             aria-label={`${nf(d.within_60)} within 60 days, ${nf(d.d61_90)} between 61 and 90, ${nf(d.over_90)} over 90`}>
          <i className="ok" style={{ width: seg(d.within_60) }} />
          <i className="warn" style={{ width: seg(d.d61_90) }} />
          <i className="late" style={{ width: seg(d.over_90) }} />
        </div>
        <div className="ov-clock-key">
          <span><i className="ok" />{kn ? "≤60 ದಿನ" : "≤60 days"} · {nf(d.within_60)}</span>
          <span><i className="warn" />{kn ? "61–90 ದಿನ" : "61–90 days"} · {nf(d.d61_90)}</span>
          <span><i className="late" />{kn ? ">90 ದಿನ" : ">90 days"} · {nf(d.over_90)}</span>
        </div>
        {(d.top_stations_over_90 || []).length > 0 && (
          <div className="ov-clock-list">
            <div className="ov-clock-lh">{kn ? "90 ದಿನ ದಾಟಿದ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳಿರುವ ಠಾಣೆಗಳು" : "Stations holding the most cases past 90 days"}</div>
            {d.top_stations_over_90.map((s) => (
              <div key={`${s.name}-${s.district}`} className="ov-clock-row">
                <span>{s.name}<em>{s.district}</em></span><b>{nf(s.n)}</b>
              </div>
            ))}
          </div>
        )}
        <div className="ov-note">
          {kn
            ? `ನೋಂದಣಿ ದಿನಾಂಕದಿಂದ ಲೆಕ್ಕ. ಅತಿ ಹಳೆಯ ತೆರೆದ ತನಿಖೆ ${nf(d.oldest_days)} ದಿನ${years ? ` (~${years} ವರ್ಷ)` : ""}. ಇಂದಿನ ನಂತರದ ದಿನಾಂಕದ FIR ಗಳನ್ನು ಬಿಡಲಾಗಿದೆ. ಕಸ್ಟಡಿ ಮತ್ತು ಅಪರಾಧದ ತೀವ್ರತೆ FIR ನಲ್ಲಿ ದಾಖಲಾಗಿಲ್ಲ, ಆದ್ದರಿಂದ ಎರಡೂ ಮಿತಿಗಳನ್ನು ತೋರಿಸಲಾಗಿದೆ.`
            : `Aged from registration date. Oldest open investigation: ${nf(d.oldest_days)} days${years ? ` (~${years} yr)` : ""}. FIRs dated after today are left out (an age cannot be negative), so this can be lower than the stage count above. Custody and offence gravity are not recorded per FIR, so both limits are shown.`}
        </div>
        </>)}
      </div>

      <div className={`ov-panel ov-outcomes${open.outcomes ? "" : " shut"}`}>
        <button className="ov-ptitle ov-toggle" onClick={() => toggle("outcomes")} aria-expanded={open.outcomes}>
          {kn ? "ಪ್ರಕರಣ ಫಲಿತಾಂಶ" : "Case outcomes"}
          <span>{open.outcomes
            ? (kn ? `ಪ್ರತಿ 100 FIR ಗೆ · ${nf(out.firs)} FIR` : `per 100 FIRs · ${nf(out.firs)} FIRs`)
            : `${Math.round(per.conviction || 0)} ${kn ? "ಪ್ರತಿ 100 FIR ಗೆ ಶಿಕ್ಷೆ" : "of 100 FIRs ended in a conviction"}`}</span>
          <i aria-hidden="true">{open.outcomes ? "–" : "+"}</i>
        </button>
        {open.outcomes && (<>
        {[
          ["arrest", kn ? "ಕನಿಷ್ಠ ಒಬ್ಬ ಬಂಧನ" : "saw at least one arrest"],
          ["chargesheet", kn ? "ದೋಷಾರೋಪ ಪಟ್ಟಿ ಸಲ್ಲಿಕೆ" : "reached a chargesheet"],
          ["conviction", kn ? "ಶಿಕ್ಷೆಯಲ್ಲಿ ಕೊನೆಗೊಂಡಿತು" : "ended in a conviction"],
        ].map(([k, label]) => (
          <div key={k} className="ov-out-row">
            <b>{Math.round(per[k] || 0)}</b>
            <div className="ov-out-bar"><i style={{ width: `${Math.min(100, per[k] || 0)}%` }} /></div>
            <span>{label}</span>
          </div>
        ))}
        <div className="ov-out-acc">
          <div><b>{acc.arrest_rate ?? 0}%</b><span>{kn ? "ಆರೋಪಿಗಳ ಬಂಧನ" : "of accused arrested"}</span></div>
          <div><b>{acc.chargesheet_rate ?? 0}%</b><span>{kn ? "ಆರೋಪಿಗಳ ದೋಷಾರೋಪ" : "of accused chargesheeted"}</span></div>
          <div><b>{acc.conviction_rate ?? 0}%</b><span>{kn ? "ದೋಷಾರೋಪಿತರಲ್ಲಿ ಶಿಕ್ಷೆ" : "of chargesheeted convicted"}</span></div>
        </div>
        <div className="ov-note">
          {kn
            ? "ಇವು ಸ್ವತಂತ್ರ ದರಗಳು, ಹಂತ ಹಂತದ ಕೊಳವೆ ಅಲ್ಲ: ಬಂಧಿಸದ (ತಲೆಮರೆಸಿಕೊಂಡ) ಆರೋಪಿಯ ವಿರುದ್ಧವೂ ದೋಷಾರೋಪ ಪಟ್ಟಿ ಸಲ್ಲಿಸಬಹುದು."
            : "Independent rates, not a funnel: a chargesheet can be filed against an accused who was never arrested (absconding)."}
        </div>
        </>)}
      </div>
    </div>
  );
}

function FirCard({ r, kn, onClose }) {
  const date = [r._year, r._month && String(r._month).padStart(2, "0"), r._day && String(r._day).padStart(2, "0")]
    .filter(Boolean).join("-");
  const counts = [
    { l: kn ? "ಸಂತ್ರಸ್ತರು" : "Victims", v: r.Victim_Count },
    { l: kn ? "ಆರೋಪಿಗಳು" : "Accused", v: r.Accused_Count },
    { l: kn ? "ಬಂಧಿತರು" : "Arrested", v: r.Arrested_Count },
    { l: kn ? "ದೋಷಾರೋಪ" : "Chargesheeted", v: r.Accused_ChargeSheeted_Count },
    { l: kn ? "ಶಿಕ್ಷೆ" : "Convictions", v: r.Conviction_Count },
  ].filter((c) => c.v !== undefined && c.v !== null && String(c.v) !== "");
  const meta = [
    { l: kn ? "ಜಿಲ್ಲೆ" : "District", v: r.District_Name },
    { l: kn ? "ಠಾಣೆ" : "Station", v: r.UnitName },
    { l: kn ? "ವರ್ಗ" : "Category", v: CATEGORIES[r._cat]?.label || r._cat },
    { l: kn ? "ಹಂತ" : "Stage", v: r.FIR_Stage },
    { l: kn ? "ಸ್ಥಳ" : "Place", v: r.Place_of_Offence },
    { l: "Accused ID", v: r.Accused_ID },
  ].filter((m) => m.v);
  // Shared linkage keys - the same fields the brain draws its evidence edges from.
  const links = [
    { l: kn ? "ವಾಹನ" : "Vehicle", v: r.Vehicle_Reg_No },
    { l: "UPI", v: r.UPI_ID },
    { l: "IP", v: r.IP_Address },
  ].filter((l) => l.v);

  return (
    <>
      <div className="ov-firback" onClick={onClose} />
      <div className="ov-fir" role="dialog" aria-label="FIR record">
        <button className="ov-fir-x" onClick={onClose} aria-label="Close"></button>
        <div className="ov-fir-eyebrow">{kn ? "FIR ದಾಖಲೆ" : "FIR record"} · {date || "—"}</div>
        <h3 className="ov-fir-ttl">{r.CrimeHead_Name || r.CrimeGroup_Name || "—"}</h3>

        <div className="ov-fir-grid">
          {meta.map((m) => (
            <div key={m.l} className="ov-fir-cell"><span>{m.l}</span><b>{m.v}</b></div>
          ))}
        </div>

        {counts.length > 0 && (
          <div className="ov-fir-counts">
            {counts.map((c) => (
              <div key={c.l} className="ov-fir-count"><b>{c.v || 0}</b><span>{c.l}</span></div>
            ))}
          </div>
        )}

        {links.length > 0 && (
          <div className="ov-fir-links">
            <div className="ov-fir-lbl">{kn ? "ಹಂಚಿಕೆಯ ಕೀಗಳು" : "Shared linkage keys"}</div>
            {links.map((l) => <span key={l.l} className="ov-fir-key">{l.l}: <b>{l.v}</b></span>)}
          </div>
        )}

        {r.MO_Details && (
          <div className="ov-fir-mo">
            <div className="ov-fir-lbl">{kn ? "ಕಾರ್ಯವಿಧಾನ (MO)" : "Modus operandi"}</div>
            <p>{r.MO_Details}</p>
          </div>
        )}
      </div>
    </>
  );
}


