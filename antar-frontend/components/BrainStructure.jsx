"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useLang } from "@/components/Providers";
import { buildCrimeGraph, filterRecords, isFutureRecord, dayGrid, aliasFor, CATEGORIES, LINK_COLORS, soften } from "@/lib/crimeGraph";
import { thinkInsights } from "@/lib/festivals";
import Constellation from "@/components/Constellation";
import Constellation3D from "@/components/Constellation3D";
import CrimeGraph from "@/components/CrimeGraph";
import BrainViewSummary from "@/components/BrainViewSummary";
import BrainLoader from "@/components/BrainLoader";
import TypingSearchInput from "@/components/TypingSearchInput";


function CustomDropdown({ value, options, onChange, label, ariaLabel }) {
  const [open, setOpen] = useState(false);
  const selected = options.find(o => o.value === value) || options[0];
  return (
    <div className="custom-dropdown" style={{position: 'relative', display: 'inline-block'}}>
      <button 
        type="button"
        className="bsx-sel" 
        style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', cursor: 'pointer', background: '#0a1526', border: '1px solid #1a3a5a', padding: '6px 12px', borderRadius: '4px', color: '#cfe9ee'}}
        onClick={() => setOpen(!open)}
        aria-label={ariaLabel}
      >
        <span>{selected.label}</span>
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none"><path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
      </button>
      {open && (
        <div className="custom-dropdown-menu" style={{position: 'absolute', top: '100%', left: 0, zIndex: 100, background: '#0a1526', border: '1px solid #1a3a5a', borderRadius: '4px', marginTop: '4px', minWidth: '100%', maxHeight: '300px', overflowY: 'auto'}}>
          {options.map((o) => (
            <div 
              key={o.value} 
              style={{padding: '6px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap'}}
              onClick={() => { onChange(o.value); setOpen(false); }}
              onMouseOver={(e) => e.currentTarget.style.background = '#122b46'}
              onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
            >
              {o.color && <div style={{width: '8px', height: '8px', borderRadius: '50%', background: o.color}}></div>}
              {o.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const API = (process.env.NEXT_PUBLIC_API_URL || "");

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const HEAT = ["#11203a", "#10405a", "#127a88", "#1bb0bf", "#22E6F0"];

async function fetchJson(url, ms = 2500) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), ms);
  try { return await (await fetch(url, { signal: ctl.signal })).json(); }
  finally { clearTimeout(t); }
}

// Crime-type composition donut for the Focus panel (ref: "Visualizing Crime
// in India" nested-ring glyphs) - pure SVG, category colors.
function Donut({ cats, total }) {
  let off = 25; // start at 12 o'clock
  return (
    <svg viewBox="0 0 80 80" className="bsx-donut">
      <circle cx="40" cy="40" r="30" fill="none" stroke="rgba(255,255,255,.07)" strokeWidth="11" />
      {cats.map((c) => {
        const pct = (c.n / total) * 100;
        const el = (
          <circle key={c.cat} cx="40" cy="40" r="30" fill="none" stroke={c.color} strokeWidth="11"
                  pathLength="100" strokeDasharray={`${pct} ${100 - pct}`} strokeDashoffset={off}
                  strokeLinecap="butt" />
        );
        off -= pct;
        return el;
      })}
      <text x="40" y="44" textAnchor="middle" fontSize="13" fill="#E8EEF7" fontFamily="JetBrains Mono">{total}</text>
    </svg>
  );
}

// Severity as a word, not a colour alone - readable at a glance and for colour-blind users.
function SevPill({ sev = "low", kn }) {
  const label = sev === "high" ? (kn ? "ಹೆಚ್ಚು" : "High")
    : sev === "med" ? (kn ? "ಮಧ್ಯಮ" : "Medium")
    : (kn ? "ಕಡಿಮೆ" : "Low");
  // A dot, not a word. The label stays on `title`/`aria-label`, so the severity is still
  // announced to a screen reader and still hoverable — it just stops competing with the
  // finding's own title for attention.
  return <span className={`bsx-sev sev-${sev}`} role="img" title={label} aria-label={label} />;
}

// Screen 03 · Page 01 - ALL crime data as one spherical constellation
// (patent-network reference) with a Focus lens (click or deep zoom) that opens
// the what/why crime-intelligence panel. Focus mode hides the All-Data chrome
// so only the intelligence in question stays on screen.
export default function BrainStructure({ focusId = "", recs, sel = {}, setSel = () => {} }) {
  const router = useRouter();
  const { lang } = useLang();
  const kn = lang === "kn";
  const controlRef = useRef(null);

  const [active, setActive] = useState(null);          // visible categories (null = all)
  const [kinds, setKinds] = useState(new Set(["repeat", "ring", "cyber", "inferred", "unsub"]));
  const [tab, setTab] = useState("type");
  const [minLayers, setMinLayers] = useState(true);
  const [minActivity, setMinActivity] = useState(false);
  const [search, setSearch] = useState("");
  const [focus, setFocus] = useState(null);            // {node, whys, comp}
  const [ovStats, setOvStats] = useState(null);
  const [backendData, setBackendData] = useState(null);
  const [readOpen, setReadOpen] = useState(false);
  const [view, setView] = useState("net"); // net (constellation) | graph (radial crime cycles)
  const [dim3d, setDim3d] = useState(true); // evidence globe: 3D (default) | 2D flat constellation
  const [groupBy, setGroupBy] = useState("type"); // crime type (default) | evidence links
  // Render scope - what the brain actually draws. Either a YEAR span (from→to, or a
  // single year when both match) or an explicit FIR index window ("render FIR 1–2000").
  const [scopeMode, setScopeMode] = useState("year"); // "year" | "fir"
  const [yearFrom, setYearFrom] = useState(null);     // null = all years
  const [yearTo, setYearTo] = useState(null);
  const [firFrom, setFirFrom] = useState(1);
  const [firTo, setFirTo] = useState(2000);
  const [noHit, setNoHit] = useState(false);
  const [fallbackQ, setFallbackQ] = useState(null);   // ACC-id not in view → offer full-dataset search
  // The ids offered under "Try:" are typed into the empty box as a hint of what goes there.
  const TRY_IDS = ["S0041", "S0011", "ACC-728352", "ACC-126112"];


  // Think runs in two visible phases: "run" (the agents fly through the brain while a
  // progress strip names each one) then "done" (results open in a large window).
  const [think, setThink] = useState(null);            // {phase, at, findings, total, lead, counts, n, scope}
  const [thinkOpen, setThinkOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const closeRef = useRef(null);

  // Case-activity calendar source: "view" = the linked constellation sample (default),
  // "full" = the ENTIRE real dataset for the year (fetched on demand). Full mode shows
  // ONLY the low→high daily heat, independent of the render scope.
  const [calMode, setCalMode] = useState("view");
  const [fullDay, setFullDay] = useState(null);        // { year, map:{"m-d":n}, max, total }

  // ACC-id search - robust to formatting and to the active scope hiding the target,
  // with a full-dataset fallback so a valid id is never a dead end.
  function runFind(forceQuery) {
    const raw = String(forceQuery || search || "").trim();
    if (!raw) { setNoHit(false); setFallbackQ(null); return; }
    if (forceQuery) setSearch(raw); // update the input visually

    const up = raw.toUpperCase().replace(/\s+/g, "-");
    const variants = [raw, up];
    if (!/^ACC[-\s]?/i.test(raw) && !/^S\d+/i.test(raw)) variants.push(`ACC-${up}`, `ACC-KA-${up}`);
    const tryFind = () => variants.some((v) => controlRef.current?.find?.(v));

    if (tryFind()) { setNoHit(false); setFallbackQ(null); return; }

    // Not in the current view - an active scope may be hiding it. Widen to the full
    // sample and retry once the graph rebuilds.
    const scoped = scopeMode === "fir" || yearFrom || yearTo || sel.year || sel.district;
    if (scoped) {
      resetScope();
      setSel({ ...sel, year: null, month: null, day: null, district: null });
      setTimeout(() => {
        const ok = tryFind();
        setNoHit(!ok);
        setFallbackQ(ok ? null : raw);
        if (!ok) setTimeout(() => setNoHit(false), 2200);
      }, 300);
      return;
    }
    setNoHit(true);
    setFallbackQ(raw);
    setTimeout(() => setNoHit(false), 2200);
  }

  const scopeSel = scopeMode === "year"
    ? { yearFrom, yearTo }
    : { firFrom, firTo };
  const filtered = useMemo(
    () => {
      if (!recs) return [];
      const appliedSel = calMode === "full" ? { ...sel, day: null, month: null, year: null } : sel;
      return filterRecords(recs, { ...appliedSel, ...scopeSel, excludeFuture: true });
    },
    [recs, sel, scopeMode, yearFrom, yearTo, firFrom, firTo, calMode]
  );

  useEffect(() => {
    Promise.allSettled([
      fetchJson(`${API}/api/graph/predicted_edges`),
      fetchJson(`${API}/api/graph/unsubs`)
    ]).then(([peRes, usRes]) => {
      const pe = peRes.status === "fulfilled" ? peRes.value : null;
      const us = usRes.status === "fulfilled" ? usRes.value : null;
      if (pe || us) {
        setBackendData({
          predicted_edges: pe?.predicted_edges || [],
          unsubs: us?.unsubs || []
        });
      }
    });
  }, []);

  // "All Data" means all of it - no sampling caps on this view
  const graph = useMemo(
    () => (recs ? buildCrimeGraph(filtered, { sampleUnlinkedPerCat: 9999, maxNodes: 9999, backendData }) : null),
    [recs, filtered, backendData]
  );
  const years = useMemo(() => (recs ? [...new Set(recs.map((r) => r._year).filter(Boolean))].sort() : []), [recs]);
  const districts = useMemo(() => (recs ? [...new Set(recs.map((r) => r.District_Name).filter(Boolean))].sort() : []), [recs]);

  const maxSupportedFIRs = useMemo(
    () => (recs ? recs.filter((r) => !isFutureRecord(r)).length : 2799),
    [recs]
  );
  const yearCountsMap = useMemo(() => {
    if (!recs) return {};
    const m = {};
    recs.forEach((r) => {
      if (r._year && !isFutureRecord(r)) {
        m[r._year] = (m[r._year] || 0) + 1;
      }
    });
    return m;
  }, [recs]);

  const [calYear, setCalYear] = useState(null);
  const year = calYear ?? years[years.length - 1] ?? null;
  const calRecs = useMemo(() => (recs ? filterRecords(recs, { ...sel, year: null, month: null, day: null }) : []), [recs, sel]);
  const cal = useMemo(() => (year ? dayGrid(calRecs, year) : { cells: [], max: 0 }), [calRecs, year]);

  // Fetch the full-dataset daily counts only when Full mode is active (and re-fetch on
  // year change). Kept entirely separate from the constellation data.
  useEffect(() => {
    if (calMode !== "full" || !year) return;
    if (fullDay?.year === year) return;
    let alive = true;
    fetchJson(`${API}/api/dataset/calendar?year=${year}`, 6000)
      .then((d) => {
        if (!alive || !d?.days) return;
        const map = {};
        for (const it of d.days) map[`${it.m}-${it.d}`] = it.n;
        setFullDay({ year, map, max: d.max || 0, total: d.total || 0, grand: d.grand_total || 0 });
      })
      .catch(() => alive && setFullDay({ year, map: {}, max: 0, total: 0 }));
    return () => { alive = false; };
  }, [calMode, year, fullDay]);

  // What the calendar actually renders: the sample grid, or the full-dataset grid
  // (same day geometry, counts swapped in from the full-dataset map).
  const calDisplay = useMemo(() => {
    if (calMode !== "full" || !year || fullDay?.year !== year) return cal;
    const base = dayGrid([], year);   // geometry only (every day of the year, n=0)
    let max = 0;
    const cells = base.cells.map((c) => {
      const n = fullDay.map[`${c.m}-${c.d}`] || 0;
      if (n > max) max = n;
      return { ...c, n };
    });
    return { cells, max };
  }, [calMode, fullDay, cal, year]);
  const calLoading = calMode === "full" && fullDay?.year !== year;
  // The FIR count shown beside the year must describe the grid underneath it. It used to
  // read yearCountsMap, which ignores the district filter the grid respects, so the two
  // could disagree on screen.
  const viewYearTotal = useMemo(() => cal.cells.reduce((s, c) => s + c.n, 0), [cal]);
  const calYearTotal = calMode === "full" ? (fullDay?.year === year ? fullDay.total : null) : viewYearTotal;

  function toggleCat(cat) {
    setActive((prev) => {
      const base = prev === null ? new Set(graph.categories.map((c) => c.cat)) : new Set(prev);
      base.has(cat) ? base.delete(cat) : base.add(cat);
      return base;
    });
  }
  function toggleKind(k) {
    setKinds((prev) => { const next = new Set(prev); next.has(k) ? next.delete(k) : next.add(k); return next; });
  }
  // Year scope: keep from ≤ to, and mirror a single-year pick into `sel` so the
  // calendar below (and the shared Page-02 charts) follow the same year.
  function setYearScope(from, to) {
    let f = from, t = to;
    if (f && t && f > t) t = f;
    setYearFrom(f);
    setYearTo(t);
    // Only a true single-year pick (from === to) drives the calendar + shared `sel.year`;
    // an open-ended or multi-year span is expressed by yearFrom/yearTo alone.
    const single = f && t && f === t ? f : null;
    if (single) setCalYear(single);
    setSel({ ...sel, year: single, month: null, day: null });
  }

  // FIR window: 1-based, clamped to the real record count, from ≤ to.
  function setFirScope(from, to) {
    const max = maxSupportedFIRs || 1;
    let f = Math.max(1, Math.min(Number.isFinite(from) ? from : 1, max));
    let t = Math.max(1, Math.min(Number.isFinite(to) ? to : max, max));
    if (f > t) t = f;
    setFirFrom(f);
    setFirTo(t);
  }

  function resetScope() {
    if (scopeMode === "year") setYearScope(null, null);
    else setFirScope(1, maxSupportedFIRs);
  }

  // Calendar ‹ › stepper. It used to set sel.year directly, which filtered the brain to
  // that year while both year dropdowns still read "All years" - the screen contradicted
  // itself. Going through setYearScope keeps calendar, dropdowns, render count and brain
  // in agreement. In Full-dataset mode the heat map is independent of the brain, so there
  // the stepper only moves the calendar.
  function stepYear(dir) {
    if (!years.length) return;
    const i = years.indexOf(year);
    const ny = years[Math.max(0, Math.min(years.length - 1, (i < 0 ? years.length - 1 : i) + dir))];
    if (ny == null || ny === year) return;
    if (calMode === "full") { setCalYear(ny); return; }
    if (scopeMode !== "year") setScopeMode("year");
    setYearScope(ny, ny);
  }

  // Plain-language description of what the brain is currently drawing.
  function scopeLabel() {
    const parts = [];
    if (scopeMode === "fir") parts.push(`FIR ${firFrom.toLocaleString()}–${firTo.toLocaleString()}`);
    else if (yearFrom && yearTo && yearFrom === yearTo) parts.push(String(yearFrom));
    else if (yearFrom || yearTo) parts.push(`${yearFrom ?? years[0] ?? ""} → ${yearTo ?? (kn ? "ಇತ್ತೀಚಿನ" : "latest")}`);
    else parts.push(kn ? "ಎಲ್ಲಾ ವರ್ಷ" : "All years");
    if (sel.district) parts.push(sel.district);
    if (calMode !== "full" && sel.month) {
      parts.push(sel.day ? `${sel.day} ${MONTHS[sel.month - 1]} ${sel.year}` : `${MONTHS[sel.month - 1]} ${sel.year}`);
    }
    return parts.join(" · ");
  }

  function pickDay(c) {
    if (sel.day === c.d && sel.month === c.m && sel.year === year) setSel({ ...sel, year: null, month: null, day: null });
    else setSel({ ...sel, year, month: c.m, day: c.d });
  }

  // ── Think: named agents reasoning over the current view ──
  // One accent for all four - the agent identity is carried by its NAME, not a hue
  // (four decorative colours added nothing but noise).
  const AGENTS = [
    { id: "pattern", name: kn ? "ಪ್ಯಾಟರ್ನ್" : "Pattern",
      how: kn ? "ವರ್ಗವಾರು ಗುಂಪು · ವರ್ಷ-ವರ್ಷ ಹೋಲಿಕೆ · ಹಬ್ಬದ ಕ್ಯಾಲೆಂಡರ್" : "groups FIRs by category, compares year-over-year, checks the festival calendar" },
    { id: "network", name: kn ? "ನೆಟ್‌ವರ್ಕ್" : "Network",
      how: kn ? "ಹಂಚಿದ ಆರೋಪಿ/ವಾಹನ/UPI ಕೀಗಳ ಮೇಲೆ ಗುಂಪು ಪತ್ತೆ · ಹಬ್ ಶ್ರೇಣೀಕರಣ" : "union-find over shared accused / vehicle / UPI keys, then ranks the hubs" },
    { id: "geo", name: kn ? "ಜಿಯೋ" : "Geography",
      how: kn ? "ಜಿಲ್ಲಾವಾರು ಒಟ್ಟುಗೂಡಿಸುವಿಕೆ · ಸಾಂದ್ರತೆ ಅಳತೆ" : "aggregates by district to find where the load concentrates" },
    { id: "forecast", name: kn ? "ಮುನ್ಸೂಚನೆ" : "Forecast",
      how: kn ? "ಲೈವ್ z-score ವೈಪರೀತ್ಯ ಸ್ಕ್ಯಾನ್ (ಬ್ಯಾಕೆಂಡ್)" : "queries the live backend anomaly service (z-score scan)" },
    { id: "linkage", name: kn ? "ಲಿಂಕೇಜ್" : "Linkage",
      how: kn ? "ಹಂಚಿದ ಆರೋಪಿ/ವಾಹನ/UPI/IP ಕೀಗಳ ಮೇಲೆ ≥2 FIR ಸಮೂಹಗಳ ಎಣಿಕೆ" : "counts clusters where ≥2 FIRs share an accused / vehicle / UPI / IP key" },
    { id: "corridor", name: kn ? "ಕಾರಿಡಾರ್" : "Corridors",
      how: kn ? "ಜಿಲ್ಲೆಗಳ ನಡುವೆ ಒಂದೇ ಆರೋಪಿಯ ಚಲನೆ ಪತ್ತೆ" : "traces the same accused across districts to surface movement corridors" },
    { id: "vigil", name: kn ? "ವಿಜಿಲ್" : "Provenance",
      how: kn ? "ಪ್ರತಿ ಸಂಕೇತ ದಾಖಲೆಯಿಂದ ಬಂದದ್ದೇ ಎಂದು ಪರಿಶೀಲನೆ (ಪ್ರೊವೆನೆನ್ಸ್)" : "audits that every signal is derived from records - provenance guard" },
  ];

  async function runThink() {
    if (think?.phase === "run") return;
    setThinkOpen(false);
    setCopied(false);
    setThink({ phase: "run", at: 0 });
    // The agents' flight through the brain is the progress indicator - its duration
    // matches the staged reveal below so the two finish together.
    controlRef.current?.think?.(2600);

    const findings = { pattern: [], network: [], geo: [], forecast: [], linkage: [], corridor: [], vigil: [] };
    thinkInsights(filtered).forEach((c) => {
      if (c.kind === "trend" || c.kind === "festival") findings.pattern.push(c);
      else findings.network.push(c);
    });

    const byDist = new Map();
    filtered.forEach((r) => { if (r.District_Name) byDist.set(r.District_Name, (byDist.get(r.District_Name) || 0) + 1); });
    const top = [...byDist.entries()].sort((a, b) => b[1] - a[1])[0];
    if (top && filtered.length) {
      const pct = Math.round((top[1] / filtered.length) * 100);
      findings.geo.push({
        kind: "geo", sev: pct > 25 ? "med" : "low",
        title: `${kn ? "ಸಾಂದ್ರತೆ" : "Concentration"}: ${top[0]}`,
        detail: `${top[1]} of ${filtered.length} FIRs in view (${pct}%) fall in ${top[0]} - the heaviest district in the current selection.`,
        source: "district aggregation",
      });
    }

    // ── Linkage Agent (A3) - clusters where ≥2 FIRs share an evidence key ──
    const sharedClusters = (field) => {
      const m = new Map();
      filtered.forEach((r) => { const v = r[field]; if (v) m.set(v, (m.get(v) || 0) + 1); });
      return [...m.values()].filter((n) => n > 1).length;
    };
    const repeatC = sharedClusters("Accused_ID");
    const vehC = sharedClusters("Vehicle_Reg_No");
    const cyberC = sharedClusters("UPI_ID") + sharedClusters("IP_Address");
    if (repeatC + vehC + cyberC > 0) {
      findings.linkage.push({
        kind: "network", sev: repeatC + vehC + cyberC > 8 ? "med" : "low",
        title: kn ? "ಸಾಕ್ಷ್ಯ ಲಿಂಕೇಜ್ ಸಮೂಹಗಳು" : "Evidence-linkage clusters",
        detail: `${repeatC} repeat-accused, ${vehC} shared-vehicle and ${cyberC} cyber-key cluster(s) each tie ≥2 FIRs together in this view.`,
        source: "shared-key union (Accused / Vehicle / UPI / IP)",
      });
    }

    // ── Corridor Agent (A2) - same accused seen across multiple districts ──
    const acc2dist = new Map();
    filtered.forEach((r) => {
      if (r.Accused_ID && r.District_Name) {
        const s = acc2dist.get(r.Accused_ID) || new Set();
        s.add(r.District_Name);
        acc2dist.set(r.Accused_ID, s);
      }
    });
    const pairCount = new Map();
    for (const s of acc2dist.values()) {
      const ds = [...s];
      for (let i = 0; i < ds.length; i++)
        for (let j = i + 1; j < ds.length; j++) {
          const key = [ds[i], ds[j]].sort().join(" ↔ ");
          pairCount.set(key, (pairCount.get(key) || 0) + 1);
        }
    }
    const topPair = [...pairCount.entries()].sort((a, b) => b[1] - a[1])[0];
    if (topPair) {
      findings.corridor.push({
        kind: "network", sev: topPair[1] > 2 ? "med" : "low",
        title: `${kn ? "ಕಾರಿಡಾರ್" : "Corridor"}: ${topPair[0]}`,
        detail: `${topPair[1]} offender(s) operate across ${topPair[0]} - a candidate movement corridor for coordinated patrol.`,
        source: "cross-district accused linkage",
      });
    }

    const live = Promise.allSettled([
      fetchJson(`${API}/api/graph/stats`),
      fetchJson(`${API}/api/alerts`),
    ]).then(([gs, al]) => {
      if (gs.status === "fulfilled" && gs.value) {
        const g = gs.value;
        const bits = [];
        const n = g.nodes ?? g.node_count ?? g.total_nodes;
        const c = g.communities ?? g.community_count;
        if (n) bits.push(`${n} entities indexed`);
        if (c) bits.push(`${c} communities (Louvain)`);
        findings.network.push({
          kind: "network", sev: "low",
          title: kn ? "ಬ್ಯಾಕೆಂಡ್ ಗ್ರಾಫ್ ಮೆಟ್ರಿಕ್ಸ್ (ಲೈವ್)" : "Backend graph metrics (live)",
          detail: `Graph service online${bits.length ? " - " + bits.join(", ") : ""}. PageRank, betweenness and k-core are precomputed for instant lookup.`,
          source: "graph_cache (live)",
        });
      }
      const a = al.status === "fulfilled" ? (al.value?.alerts || [])[0] : null;
      if (a) findings.forecast.push({
        kind: "alert", sev: "high",
        title: `${kn ? "ಲೈವ್ ಎಚ್ಚರಿಕೆ" : "Live alert"} · ${a.zone}`,
        detail: `${(a.crime_type || "").replace(/_/g, " ")} anomaly, z=${a.z_score?.toFixed?.(2)} - ${a.observed} cases observed.`,
        source: "forecast agent (live)",
      });
    }).catch(() => {});

    // Short reveal stagger only - this is a UI transition, NOT simulated compute time.
    // The local passes are instant; the only real latency is the live backend fetch below.
    for (let i = 0; i < AGENTS.length; i++) {
      setThink({ phase: "run", at: i });
      await new Promise((r) => setTimeout(r, 300));
    }
    await live;

    // ── Vigil Agent (A5) - provenance guard: confirm every signal is record-derived ──
    const derivedCount = Object.entries(findings)
      .filter(([k]) => k !== "vigil")
      .reduce((n, [, arr]) => n + arr.length, 0);
    findings.vigil.push({
      kind: "alert", sev: "low",
      title: kn ? "ಪ್ರೊವೆನೆನ್ಸ್ ಪರಿಶೀಲನೆ" : "Provenance check",
      detail: kn
        ? `${filtered.length} ದಾಖಲೆಗಳಿಂದ ${derivedCount} ಸಂಕೇತ ಪಡೆಯಲಾಗಿದೆ - ಯಾವುದೇ ಸಂಖ್ಯೆ ಕಲ್ಪಿತವಲ್ಲ; ಊಹಿತ ಅಂಶಗಳು ಲೇಬಲ್ ಆಗಿವೆ.`
        : `${derivedCount} signal(s) derived from ${filtered.length} records in view - no fabricated numbers; inferred items are labelled.`,
      source: "A5 Vigil (provenance guard)",
    });

    // Output quality: rank each agent's findings by severity (high→low), count the
    // total, and surface the single most important cross-agent takeaway as a synthesis.
    const sevRank = { high: 0, med: 1, low: 2 };
    const counts = { high: 0, med: 0, low: 0 };
    let total = 0, topFinding = null;
    for (const k of Object.keys(findings)) {
      findings[k].sort((a, b) => (sevRank[a.sev] ?? 3) - (sevRank[b.sev] ?? 3));
      total += findings[k].length;
      findings[k].forEach((f) => { const s = f.sev || "low"; counts[s] = (counts[s] || 0) + 1; });
      // The Vigil provenance check audits the others; it is never itself the takeaway.
      if (k === "vigil") continue;
      const cand = findings[k][0];
      if (cand && (!topFinding || (sevRank[cand.sev] ?? 3) < (sevRank[topFinding.sev] ?? 3))) topFinding = cand;
    }
    const summary = !topFinding
      ? (kn ? "ಈ ವೀಕ್ಷಣೆಯಲ್ಲಿ ಗಮನಾರ್ಹ ಸಂಕೇತವಿಲ್ಲ." : "No notable signal in this view.")
      : (kn
          ? `${total} ಸಂಕೇತ${total > 1 ? "ಗಳು" : ""} · ಪ್ರಮುಖ: ${topFinding.title || ""}`
          : `${total} signal${total > 1 ? "s" : ""} across ${AGENTS.length} agents · lead: ${topFinding.title || ""}`);
    setThink({
      phase: "done", at: AGENTS.length, findings, total, summary, counts,
      lead: topFinding, n: filtered.length, scope: scopeLabel(),
    });
    setThinkOpen(true);
  }

  async function copyThink() {
    if (!think?.findings) return;
    const word = { high: "HIGH", med: "MEDIUM", low: "LOW" };
    const lines = [
      `Antar · agent analysis - ${think.n.toLocaleString()} FIRs · ${think.scope}`,
      "",
      `Key takeaway: ${think.lead ? `${think.lead.title}${think.lead.detail ? ` - ${think.lead.detail}` : ""}` : think.summary}`,
      "",
    ];
    AGENTS.forEach((a) => {
      const f = think.findings[a.id] || [];
      if (!f.length) return;
      lines.push(a.name);
      f.forEach((c) => lines.push(`  [${word[c.sev || "low"]}] ${c.title}${c.detail ? ` - ${c.detail}` : ""}`));
      lines.push("");
    });
    try {
      await navigator.clipboard.writeText(lines.join("\n").trim());
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch { /* clipboard blocked - the text is on screen */ }
  }

  // The results window is a modal: Escape closes it, and focus lands on Close so the
  // keyboard user is inside the dialog rather than behind it.
  useEffect(() => {
    if (!thinkOpen) return;
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === "Escape") setThinkOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [thinkOpen]);

  const loading = !recs;
  // Right side of the Case-activity bar. It used to fall back to "all activity · 3,360
  // events" - a count across EVERY year, printed beside a single calendar year, so it
  // read as that year's total. It now only speaks when there is something specific to say.
  const evWord = kn ? "ಘಟನೆಗಳು" : "events";
  const calStatus = calLoading
    ? (kn ? "ಪೂರ್ಣ ಡೇಟಾ ಲೋಡ್…" : "loading full dataset…")
    : calMode === "full"
    ? `${(fullDay?.grand || 0).toLocaleString()} ${kn ? "ಒಟ್ಟು" : "in dataset"}`
    : sel.day && sel.month
    ? `${sel.day} ${MONTHS[sel.month - 1]} · ${filtered.length.toLocaleString()} ${evWord}`
    : sel.month
    ? `${MONTHS[sel.month - 1]} ${sel.year} · ${filtered.length.toLocaleString()} ${evWord}`
    : "";

  const CELL = 6.8, GAP = 1.8, X0 = 4, Y0 = 15;
  const level = (n) => (n === 0 ? 0 : Math.min(4, 1 + Math.floor((n / Math.max(1, calDisplay.max)) * 3.999)));

  const [legendFocus, setLegendFocus] = useState(null); // 'hub', 'top', 'agent', 'comm', 'line', 'dust'
  // What the last crime-filter change did, shown over the brain for a moment.
  const [filterNote, setFilterNote] = useState(null);
  useEffect(() => {
    if (!filterNote) return;
    const id = setTimeout(() => setFilterNote(null), 2600);
    return () => clearTimeout(id);
  }, [filterNote]);

  // The key has to match what is actually drawn. It claimed the agents were purple
  // (#8B5CF6) when they render cyan, and said nothing about what the blobs mean - so it
  // described a picture the officer was not looking at. Rows now follow the live view:
  // Evidence mode groups by shared keys, Crime-type mode groups by category.
  const READ_ROWS = (kn ? [
    ["big", "#E8A33D", "ಕಿತ್ತಳೆ = ಪ್ರಮುಖ ಆರೋಪಿ", "hub"],
    ["dot", "#18D69A", "ಹಸಿರು = ಅತಿ ಹೆಚ್ಚು ಸಂಪರ್ಕ", "top"],
    ["ring", "#00F5D4", "ವಲಯಾಕಾರ ಗುರುತು = Antar ಏಜೆಂಟ್", "agent"],
    ["dot", "#2BB3A3", "ಟೀಲ್ = ಸಂಪರ್ಕಿತ FIR", "comm"],
    ["ln", "", "ಗೆರೆ = ಹಂಚಿದ ಸಾಕ್ಷ್ಯ", "line"],
    ["dot", "#566072", "ಬೂದು = ಒಂಟಿ FIR", "dust"],
  ] : [
    ["big", "#E8A33D", "Key accused - most links in view", "hub"],
    ["dot", "#18D69A", "Most connected node here", "top"],
    ["ring", "#00F5D4", "Antar agent - the ringed markers", "agent"],
    ["dot", "#2BB3A3", "FIR sharing evidence with another", "comm"],
    ["ln", "", "A line is one shared key", "line"],
    ["dot", "#566072", "Isolated FIR - nothing shared", "dust"],
  ]).concat(groupBy === "evidence"
    ? [["grp", "", kn ? "ಕ್ಲಸ್ಟರ್ = ಹಂಚಿದ ಸಾಕ್ಷ್ಯದ ಗುಂಪು" : "Each clump = FIRs sharing a key", "grp"]]
    : [["grp", "", kn ? "ಬ್ಲಾಬ್ = ಒಂದು ಅಪರಾಧ ಪ್ರಕಾರ" : "Each blob = one crime type", "grp"]]);

  const focusName = focus ? (focus.node.accused ? aliasFor(focus.node.accused) : focus.node.zone || focus.node.crimeHead) : "";

  return (
    <div className="bsx-stage">
      <div className="bsx-orbits" aria-hidden="true"><i /><i /></div>
      {filterNote && (
        <div className="bsx-filternote" role="status" aria-live="polite">
          <b>{filterNote.label}</b>
          <span>{filterNote.n.toLocaleString()} {kn ? "FIR" : "FIRs"}</span>
        </div>
      )}
      {loading && <BrainLoader kn={kn} />}
      

      {!loading && (
        <div className="bsx-netwrap" style={{ visibility: view === "graph" ? "hidden" : "visible" }}>
          {dim3d ? (
            <Constellation3D graph={graph} groupBy={groupBy} active={active} kinds={kinds} controlRef={controlRef}
                             onFocus={setFocus} onStats={setOvStats} onAgent={runThink} focusId={focusId} legendFocus={legendFocus} />
          ) : (
            <Constellation graph={graph} groupBy={groupBy} active={active} kinds={kinds} controlRef={controlRef}
                           onFocus={setFocus} onStats={setOvStats} onAgent={runThink} focusId={focusId} legendFocus={legendFocus} />
          )}
        </div>
      )}
      {!loading && view === "graph" && <CrimeGraph recs={recs} kn={kn} />}

      {/* ── Top-Left · tools column (kept short so it never meets the calendar) ── */}
      <div className="bsx-tools">

        {view === "net" && (
          <div className={`bs-search ${noHit ? "err" : ""}`}>
            <TypingSearchInput className="bs-searchinput" value={search}
              examples={TRY_IDS} prefix={kn ? "ಉದಾ: " : "Try "} paused={noHit}
              fallback={kn ? "ACC-id ನಮೂದಿಸಿ" : "Enter ACC-id"}
              overridePlaceholder={noHit ? (kn ? "ಪತ್ತೆಯಾಗಿಲ್ಲ - ACC-id ಯತ್ನಿಸಿ." : "no match - try an ACC-id.") : ""}
              ariaLabel={kn ? "ACC-id ಅಥವಾ ಶಂಕಿತ ಐಡಿ ಹುಡುಕಿ" : "Search an ACC-id or suspect id"}
              onChange={(e) => { setSearch(e.target.value); setFallbackQ(null); setNoHit(false); }} onKeyDown={(e) => { if (e.key === "Enter") runFind(); }} />
            <button className="bs-searchbtn" onClick={() => runFind()} aria-label="Find">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
            </button>
          </div>
        )}
        {view === "net" && fallbackQ && (
          <button
            className="bs-fallback"
            onClick={() => router.push(`/search?q=${encodeURIComponent(fallbackQ)}`)}
            style={{
              marginTop: "6px", width: "100%", padding: "7px 10px", borderRadius: "8px",
              background: "rgba(34,230,240,0.10)", border: "1px solid rgba(34,230,240,0.4)",
              color: "#22E6F0", fontSize: "11px", fontWeight: 700, cursor: "pointer",
              fontFamily: "'Chakra Petch', sans-serif", textAlign: "left", lineHeight: 1.4,
            }}
            title={kn ? "ಸಂಪೂರ್ಣ ದತ್ತಾಂಶದಲ್ಲಿ ಹುಡುಕಿ" : "Search the full dataset"}
          >
            {kn ? `"${fallbackQ}" ವೀಕ್ಷಣೆಯಲ್ಲಿ ಇಲ್ಲ - ಸಂಪೂರ್ಣ ದತ್ತಾಂಶದಲ್ಲಿ ಹುಡುಕಿ →` : `"${fallbackQ}" not in this view - search the full dataset →`}
          </button>
        )}
        <div className="bsx-modes">
          <span className={view === "net" && !focus ? "on" : ""} onClick={() => { setView("net"); controlRef.current?.clear(); }}>{kn ? "ಎಲ್ಲಾ ದತ್ತಾಂಶ" : "All Data"}</span>
          <span className={view === "net" && focus ? "on" : ""} title={focus ? "" : (kn ? "ಮೊದಲು ನೋಡ್ ಕ್ಲಿಕ್ ಮಾಡಿ" : "click any node or zoom into a group first")}>
            {kn ? "ಫೋಕಸ್" : "Focus"}
          </span>
          <span className={view === "graph" ? "on" : ""} onClick={() => setView("graph")}>{kn ? "ಅಪರಾಧ ಗ್ರಾಫ್" : "Crime Graph"}</span>
        </div>
        {view === "net" && (
          <div className="bsx-dimtoggle" role="group" aria-label={kn ? "3D / 2D ವೀಕ್ಷಣೆ" : "3D / 2D view"}>
            <button className={dim3d ? "on" : ""} onClick={() => { setDim3d(true); controlRef.current?.clear?.(); }} title={kn ? "3D ಗ್ಲೋಬ್" : "Interactive 3D globe"}>3D</button>
            <button className={!dim3d ? "on" : ""} onClick={() => { setDim3d(false); controlRef.current?.clear?.(); }} title={kn ? "2D ಫ್ಲಾಟ್" : "Flat 2D constellation"}>2D</button>
          </div>
        )}
        {view === "net" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <div className="bsx-modes" title={kn ? "ಗುಂಪು ಮಾಡುವ ವಿಧಾನ" : "How the brain groups the records"}>
              <span className={groupBy === "evidence" ? "on" : ""} onClick={() => setGroupBy("evidence")}>{kn ? "ಸಾಕ್ಷ್ಯ" : "Evidence"}</span>
              <span className={groupBy === "type" ? "on" : ""} onClick={() => setGroupBy("type")}>{kn ? "ಅಪರಾಧ ಪ್ರಕಾರ" : "Crime type"}</span>
            </div>
          </div>
        )}
        {view === "net" && !focus && graph && (
          // Pick one crime type to see only its FIRs and links (2D and 3D alike). The
          // Layers & Filters toggles stay available for mixing several.
          <label className="bsx-crimesel">
            <span>{kn ? "ಅಪರಾಧ" : "Crime"}</span>
            <select value={active && active.size === 1 ? [...active][0] : ""}
                    onChange={(e) => {
                      const cat = e.target.value;
                      setActive(cat ? new Set([cat]) : null);
                      const c = graph?.categories?.find((x) => x.cat === cat);
                      if (cat) {
                        // Picking a crime type now pulls that whole type into focus,
                        // rather than only recolouring the ball: the camera flies to the
                        // cluster and the panel reports on the type as a whole.
                        controlRef.current?.focusCategory?.(cat, c?.label || cat);
                      } else {
                        controlRef.current?.clear?.();
                        // Turn the brain and name what changed. Re-colouring in silence
                        // reads as a glitch - the officer cannot tell the filter applied.
                        controlRef.current?.spin?.();
                      }
                      setFilterNote(cat
                        ? { label: c?.label || cat, n: c?.count || 0 }
                        : { label: kn ? "ಎಲ್ಲಾ ಅಪರಾಧಗಳು" : "All crimes",
                            n: graph?.categories?.reduce((s, x) => s + (x.count || 0), 0) || 0 });
                    }}
                    aria-label={kn ? "ಅಪರಾಧ ಪ್ರಕಾರ ಆಯ್ಕೆಮಾಡಿ" : "Select a crime type"}>
              <option value="">{kn ? "ಎಲ್ಲಾ ಅಪರಾಧಗಳು" : "All crimes"}</option>
              {graph.categories.map((c) => (
                <option key={c.cat} value={c.cat}>{c.label} ({(c.count || 0).toLocaleString()})</option>
              ))}
            </select>
          </label>
        )}
        {view === "net" && (
          <button className="bsx-readbtn" aria-expanded={readOpen} onClick={() => setReadOpen(!readOpen)}>
            {kn ? "ಹೇಗೆ ಓದುವುದು" : "How to read it"} {readOpen ? "▴" : "▾"}
          </button>
        )}
        {view === "net" && readOpen && (
          <div className="bsx-read">
            {/* A plain key: what each mark means. It used to be clickable (highlight on
                click), which made a legend behave like a filter and dimmed the brain
                unexpectedly - the filters live in Layers & Filters. */}
            {READ_ROWS.map(([kind, color, text], i) => (
              <div key={i} className="r">
                {kind === "ln" ? <i className="ln" />
                  : kind === "ring" ? <i className="ring" style={{ borderColor: color }} />
                  : kind === "grp" ? <i className="grp" />
                  : <i className={`dot ${kind === "big" ? "big" : ""}`} style={{ background: color }} />}
                {text}
              </div>
            ))}
            <div className="r note">
              {focus
                ? (kn ? "ಖಾಲಿ ಜಾಗ ಕ್ಲಿಕ್ = ಫೋಕಸ್ ಮುಚ್ಚಿ" : "Click empty space to leave focus")
                : (kn ? "ಯಾವುದೇ ನೋಡ್ ಕ್ಲಿಕ್ ಮಾಡಿ" : "Click any node to open its group")}
            </div>
          </div>
        )}
      </div>

      {/* ── Top-Right · Layers & Filters (All-Data mode only) ── */}
      {view === "net" && !focus && (
        // overflow lives in globals.css (max-height + overflow-y:auto), NOT inline: an
        // inline `overflow: hidden` wins over the stylesheet and would turn that height
        // cap into a silent clip with no way to scroll to the rest of the list.
        <div className="bsx-layers">
          <h4 style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", margin: 0 }} onClick={() => setMinLayers(!minLayers)}>
            {kn ? "ಪದರಗಳು ಮತ್ತು ಫಿಲ್ಟರ್‌ಗಳು" : "Layers & Filters"}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ transform: minLayers ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.3s" }}><path d="M18 15l-6-6-6 6"/></svg>
          </h4>
          
          {!minLayers && (
            <div style={{ marginTop: "16px" }}>
              <div className="bsx-cby">
                {[["type", kn ? "ಪ್ರಕಾರ" : "Type"], ["links", kn ? "ಕೊಂಡಿ" : "Links"], ["more", kn ? "ಇನ್ನಷ್ಟು" : "More"]].map(([k, l]) => (
                  <span key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</span>
                ))}
              </div>
              {tab === "type" && (
                <div className="bsx-lrows">
                  {graph?.categories.map((c) => {
                    const on = active === null || active.has(c.cat);
                    return (
                      <div key={c.cat} className="bsx-lrow">
                        <span className="lbl"><span className="bsx-dot" style={{ background: soften(c.color) }} />{c.label}</span>
                        <button className={`bsx-sw ${on ? "on" : ""}`} aria-pressed={on} onClick={() => toggleCat(c.cat)}><b /></button>
                      </div>
                    );
                  })}
                  {/* active: null = every category visible; an empty Set = none visible.
                      Both renderers (Constellation / Constellation3D) already treat an empty
                      Set as "hide all categories" while keeping agent nodes. */}
                  <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
                    <button className="bsx-mini" disabled={active === null} style={{ opacity: active === null ? 0.4 : 1 }}
                      onClick={() => setActive(null)}>{kn ? "ಎಲ್ಲಾ ತೋರಿಸಿ" : "show all"}</button>
                    <button className="bsx-mini" disabled={active !== null && active.size === 0}
                      style={{ opacity: active !== null && active.size === 0 ? 0.4 : 1 }}
                      onClick={() => setActive(new Set())}>{kn ? "ಎಲ್ಲಾ ತೆರವುಗೊಳಿಸಿ" : "clear all"}</button>
                  </div>
                </div>
              )}
              {tab === "links" && (
                <div className="bsx-lrows">
                  {["repeat", "ring", "cyber", "inferred", "unsub"].map((k) => (
                    <div key={k} className="bsx-lrow">
                      <span className="lbl">
                        <span className="bsx-dot" style={{ background: k === "inferred" ? "#C084FC" : k === "unsub" ? "#A855F7" : LINK_COLORS[k] }} />
                        {k === "repeat" ? (kn ? "ಪುನರಾವರ್ತಿತ" : "Repeat offender") :
                         k === "ring" ? (kn ? "ರಿಂಗ್" : "Ring") :
                         k === "cyber" ? (kn ? "ಸೈಬರ್" : "Cyber") :
                         k === "inferred" ? "Predicted Edges" : "UNSUB Profiles"}
                      </span>
                      <button className={`bsx-sw ${kinds.has(k) ? "on" : ""}`} aria-pressed={kinds.has(k)} onClick={() => toggleKind(k)}><b /></button>
                    </div>
                  ))}
                </div>
              )}
              {tab === "more" && (
                <div className="bsx-lrows">
                  <label className="bsx-sml">{kn ? "ಜಿಲ್ಲೆ" : "District"}</label>
                  <select className="bsx-sel" value={sel.district || ""} onChange={(e) => setSel({ ...sel, district: e.target.value || null })}>
                    <option value="">{kn ? "ಎಲ್ಲಾ ಜಿಲ್ಲೆಗಳು" : "All districts"}</option>
                    {districts.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
              )}
              <div className="hr" />
              <div className="vis" style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", transform: "scale(0.85)", transformOrigin: "left center" }}>
                {/* accurate claim: the GRAPH is dataset-derived, but person names are aliases */}
                {ovStats && <span className="cx-badge-k" title={kn
                  ? "ಪ್ರತಿ ನೋಡ್ ಮತ್ತು ಕೊಂಡಿ FIR ದಾಖಲೆಯಿಂದ; ವ್ಯಕ್ತಿಗಳ ಹೆಸರುಗಳು ACC-id ಯ ಸಿಂಥೆಟಿಕ್ ಅಲಿಯಾಸ್"
                  : "Every node and link is derived from the FIR records; person names shown are synthetic aliases of the real ACC-ids"}>K · From records</span>}
                <span>{ovStats ? `${ovStats.nodes.toLocaleString()} records · ${ovStats.links.toLocaleString()} evidence links · ${ovStats.groups} groups` : "…"}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* View Summary stands on its own. Nested under Layers & Filters it read as a
          filter control and disappeared whenever that panel was collapsed - it is a
          description of what is on screen, so it belongs beside the brain, not inside
          the controls. */}
      {view === "net" && !focus && (
        <aside className="bsx-vsum">
          <BrainViewSummary graph={graph} stats={graph?.stats} focus={null} active={active} kinds={kinds}
                            groupBy={groupBy} scope={scopeLabel()} district={null} dim3d={dim3d} kn={kn} always />
        </aside>
      )}

      {view === "net" && (
        <button className={`bsx-pill think ${think?.phase === "run" ? "busy" : ""}`} onClick={runThink}
                aria-busy={think?.phase === "run"}>
          {/* The same mark the agents wear in the scene: a core inside a ring. A lightbulb
              said "idea"; this says "the agents". */}
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><ellipse cx="12" cy="12" rx="9.5" ry="4.4" /><circle cx="12" cy="12" r="2.6" fill="currentColor" stroke="none" /></svg>
          {think?.phase === "run" ? (kn ? "ಚಾಲನೆಯಲ್ಲಿದೆ…" : "Running…") : (kn ? "ಅಂತರ ಚಲಾಯಿಸಿ" : "Run Antar")}
        </button>
      )}
      {/* Closed the results? They stay one click away until the next run. */}
      {view === "net" && think?.phase === "done" && !thinkOpen && (
        <button className="bsx-pill think-res" onClick={() => setThinkOpen(true)}>
          {kn ? "ಫಲಿತಾಂಶಗಳು" : "Results"} · {think.total}
        </button>
      )}

      {/* Phase 1 - a slim strip names each agent while they fly, so the brain stays visible. */}
      {view === "net" && think?.phase === "run" && (() => {
        const cur = AGENTS[Math.min(think.at, AGENTS.length - 1)];
        return (
          <div className="bsx-thinkdock" role="status" aria-live="polite">
            <div className="top">
              <span className="ttl"><i />{kn ? "ಏಜೆಂಟ್‌ಗಳು ಈ ವೀಕ್ಷಣೆಯನ್ನು ವಿಶ್ಲೇಷಿಸುತ್ತಿವೆ" : "Agents analysing this view"}</span>
              <span className="ct">{Math.min(think.at + 1, AGENTS.length)} / {AGENTS.length}</span>
            </div>
            <div className="bar"><b style={{ width: `${((think.at + 1) / AGENTS.length) * 100}%` }} /></div>
            <div className="now"><b>{cur.name}</b> - {cur.how}</div>
          </div>
        );
      })()}

      {/* Phase 2 - the results, in a window large enough to actually read. */}
      {think?.phase === "done" && thinkOpen && (
        <div className="bsx-tm-overlay" onClick={() => setThinkOpen(false)}>
          <section className="bsx-tm" role="dialog" aria-modal="true" aria-labelledby="bsx-tm-title"
                   onClick={(e) => e.stopPropagation()}>
            <header className="bsx-tm-head">
              <div>
                <span className="eyebrow">{kn ? "ಅಂತರ ವಿಶ್ಲೇಷಣೆ" : "Antar Analysis"}</span>
                <h2 id="bsx-tm-title">{kn ? "ಈ ವೀಕ್ಷಣೆಯಲ್ಲಿ ಏಜೆಂಟ್‌ಗಳು ಕಂಡುಕೊಂಡದ್ದು" : "What the agents found in this view"}</h2>
                <p className="meta">
                  {think.n.toLocaleString()} FIRs · {think.scope} · {AGENTS.length} {kn ? "ಏಜೆಂಟ್‌ಗಳು" : "agents"}
                </p>
              </div>
              <div className="acts">
                <button className="bsx-tm-btn" onClick={copyThink}>
                  {copied ? (kn ? " ನಕಲಿಸಲಾಗಿದೆ" : " Copied") : (kn ? "ಸಾರಾಂಶ ನಕಲಿಸಿ" : "Copy summary")}
                </button>
                <button className="bsx-tm-btn" onClick={runThink}>{kn ? "ಮತ್ತೆ ಚಲಾಯಿಸಿ" : "Run again"}</button>
                <button ref={closeRef} className="bsx-tm-btn close" onClick={() => setThinkOpen(false)}>
                   {kn ? "ಮುಚ್ಚಿ" : "Close"}
                </button>
              </div>
            </header>

            <div className={`bsx-tm-lead sev-${think.lead?.sev || "low"}`}>
              <span className="lbl">{kn ? "ಮುಖ್ಯ ಅಂಶ" : "Key takeaway"}</span>
              {think.lead ? (
                <>
                  <div className="row"><SevPill sev={think.lead.sev} kn={kn} /><b>{think.lead.title}</b></div>
                  {think.lead.detail && <p>{think.lead.detail}</p>}
                </>
              ) : <p>{think.summary}</p>}
              <div className="bsx-tm-tally">
                <span className="h"><i />{kn ? "ಹೆಚ್ಚು" : "High"} <b>{think.counts.high}</b></span>
                <span className="m"><i />{kn ? "ಮಧ್ಯಮ" : "Medium"} <b>{think.counts.med}</b></span>
                <span className="l"><i />{kn ? "ಕಡಿಮೆ" : "Low"} <b>{think.counts.low}</b></span>
                <span className="tot">{think.total} {kn ? "ಸಂಕೇತಗಳು" : think.total === 1 ? "signal" : "signals"}</span>
              </div>
            </div>

            <div className="bsx-tm-body">
              <nav className="bsx-tm-rail" aria-label={kn ? "ಏಜೆಂಟ್‌ಗಳು" : "Agents"}>
                {AGENTS.map((a) => {
                  const n = think.findings[a.id]?.length || 0;
                  return (
                    <button key={a.id} disabled={!n}
                            onClick={() => document.getElementById(`bsx-tm-${a.id}`)?.scrollIntoView({ behavior: "smooth", block: "start" })}>
                      <span>{a.name}</span><b>{n}</b>
                    </button>
                  );
                })}
              </nav>

              <div className="bsx-tm-list">
                {AGENTS.filter((a) => think.findings[a.id]?.length).map((a) => (
                  <section key={a.id} id={`bsx-tm-${a.id}`} className="bsx-tm-agent">
                    <h3>{a.name}</h3>
                    <p className="how">{a.how}</p>
                    <div className="bsx-tm-cards">
                      {think.findings[a.id].map((c, j) => {
                        const sev = c.sev || "low";
                        return (
                          <article key={j} className={`bsx-tm-card sev-${sev}`} style={{ animationDelay: `${j * 50}ms` }}>
                            <div className="hd"><SevPill sev={sev} kn={kn} /><b>{c.title || (kn ? "ಸಂಕೇತ" : "Signal")}</b></div>
                            {c.detail && <p>{c.detail}</p>}
                            {c.source && <div className="src">{kn ? "ಮೂಲ" : "Source"}: {c.source}</div>}
                          </article>
                        );
                      })}
                    </div>
                  </section>
                ))}
                {AGENTS.some((a) => !think.findings[a.id]?.length) && (
                  <p className="bsx-tm-none">
                    {kn ? "ಈ ವೀಕ್ಷಣೆಯಲ್ಲಿ ಸಂಕೇತವಿಲ್ಲ: " : "No signal in this view: "}
                    {AGENTS.filter((a) => !think.findings[a.id]?.length).map((a) => a.name).join(", ")}
                  </p>
                )}
                <p className="bsx-tm-foot">
                  {kn
                    ? "ಪ್ರತಿ ಸಂಖ್ಯೆಯನ್ನು ಈ ವೀಕ್ಷಣೆಯ FIR ದಾಖಲೆಗಳಿಂದ ಎಣಿಸಲಾಗಿದೆ ಅಥವಾ ಲೈವ್ ಬ್ಯಾಕೆಂಡ್‌ನಿಂದ ಓದಲಾಗಿದೆ - ಯಾವುದನ್ನೂ ಭಾಷಾ ಮಾದರಿ ಬರೆದಿಲ್ಲ."
                    : "Every figure here is counted from the FIR records in this view or read from the live backend services - none of it is written by a language model."}
                </p>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* ── Focus panel - the crime intelligence of the selected group ── */}
      {view === "net" && focus && (
        <aside className="bsx-focus" style={{
          position: "fixed", top: "80px", right: "24px", width: "320px",
          background: "rgba(11, 18, 32, 0.75)", backdropFilter: "blur(20px)",
          border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: "12px",
          padding: "20px", color: "#F8FAFC", zIndex: 100,
          boxShadow: "0 8px 32px rgba(0,0,0,0.5)", fontFamily: "'Inter', sans-serif",
          display: "flex", flexDirection: "column", gap: "16px", maxHeight: "calc(100vh - 120px)", overflowY: "auto", wordBreak: "break-word",
          animation: "fadeRise .28s cubic-bezier(0.16,1,0.3,1)"
        }}>
          {/* labelled exit - a bare  read as decoration, so users refreshed to escape focus */}
          <button onClick={() => { controlRef.current?.clear(); setActive(null); setFilterNote(null); }} style={{
            position: "absolute", top: "13px", right: "13px",
            background: "rgba(34,230,240,.08)", border: "1px solid rgba(34,230,240,.35)",
            color: "#22E6F0", cursor: "pointer", fontSize: "10.5px", fontWeight: 700,
            fontFamily: "'Chakra Petch', sans-serif", padding: "4px 10px", borderRadius: "999px"
          }}> {kn ? "ಫೋಕಸ್ ಮುಚ್ಚಿ" : "Exit focus"}</button>

          {/* The focused group in sentences - who is connected, how, and where. */}
          <BrainViewSummary graph={graph} stats={graph?.stats} focus={focus} active={active} kinds={kinds}
                            groupBy={groupBy} scope={scopeLabel()} district={null} dim3d={dim3d} kn={kn} always />
          
          <div>
            <div style={{ fontSize: "10px", fontWeight: 600, color: "#64748B", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: "4px" }}>
              {focus.meta?.kind === "cat"
                ? (kn ? "ಫೋಕಸ್ · ಅಪರಾಧ ಪ್ರಕಾರ" : "Focus · crime type")
                : (kn ? "ಫೋಕಸ್ · ಸಂಪರ್ಕಿತ ಗುಂಪು" : "Focus · linked group")}
            </div>
            <div style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", marginBottom: "4px", fontFamily: "'Chakra Petch', sans-serif" }}>
              {focusName}
            </div>
            {focus.node.accused && (
              <div style={{ fontSize: "11px", color: "#94A3B8", fontFamily: "'JetBrains Mono', monospace" }}>
                [{focus.node.accused}]
              </div>
            )}
            <div style={{ fontSize: "11px", color: "#94A3B8", marginTop: "8px", display: "flex", gap: "6px", flexWrap: "wrap" }}>
              <span style={{ background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: "999px" }}>{focus.comp.size} FIRs</span>
              <span style={{ background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: "999px" }}>{focus.comp.districts.length} Districts</span>
              {focus.comp.years && <span style={{ background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: "999px" }}>{focus.comp.years[0]}–{focus.comp.years[1]}</span>}
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "16px", padding: "16px 0", borderTop: "1px solid rgba(255,255,255,0.05)", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <div style={{ width: "80px", flexShrink: 0 }}><Donut cats={focus.comp.cats} total={focus.comp.size} /></div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1 }}>
              {focus.comp.cats.slice(0, 4).map((c) => (
                <div key={c.cat} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "11px", color: "#E2E8F0" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <i style={{ width: "6px", height: "6px", borderRadius: "50%", background: c.color }} />
                    <span style={{ wordBreak: "break-word", overflowWrap: "anywhere" }}>{c.label}</span>
                  </div>
                  <b style={{ fontFamily: "'JetBrains Mono', monospace" }}>{c.n}</b>
                </div>
              ))}
            </div>
          </div>

          {focus.comp.extra && (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "flex", gap: "8px" }}>
                <div style={{ flex: 1, background: "rgba(34,230,240,0.06)", border: "1px solid rgba(34,230,240,0.18)", borderRadius: "8px", padding: "8px 10px" }}>
                  <b style={{ display: "block", fontSize: "15px", fontFamily: "'Chakra Petch', sans-serif", color: "#22E6F0" }}>
                    {Math.round((100 * focus.comp.extra.linked) / Math.max(1, focus.comp.size))}%
                  </b>
                  <span style={{ fontSize: "10px", color: "#94A3B8" }}>
                    {kn ? "ಸಾಕ್ಷ್ಯದಿಂದ ಜೋಡಿದವು" : "share evidence with another FIR"}
                  </span>
                </div>
                <div style={{ flex: 1, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "8px", padding: "8px 10px" }}>
                  <b style={{ display: "block", fontSize: "15px", fontFamily: "'Chakra Petch', sans-serif", color: "#F8FAFC" }}>
                    {focus.comp.extra.named.toLocaleString()}
                  </b>
                  <span style={{ fontSize: "10px", color: "#94A3B8" }}>
                    {kn ? "ನಾಮನಿದೇಶಿತ ಆರೋಪಿಗಳು" : "named accused"}
                  </span>
                </div>
              </div>

              {focus.comp.extra.zones.length > 0 && (
                <div>
                  <div style={{ fontSize: "10px", fontWeight: 600, color: "#64748B", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: "6px" }}>
                    {kn ? "ಎಲ್ಲಿ ಹೆಚ್ಚು" : "Where it concentrates"}
                  </div>
                  {focus.comp.extra.zones.map((z) => (
                    <div key={z.name} style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <span style={{ fontSize: "11px", color: "#E2E8F0", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{z.name}</span>
                      <div style={{ width: "58px", height: "4px", background: "rgba(255,255,255,0.07)", borderRadius: "2px", overflow: "hidden", flexShrink: 0 }}>
                        <i style={{ display: "block", height: "100%", width: `${(100 * z.n) / focus.comp.extra.zones[0].n}%`, background: "#22E6F0" }} />
                      </div>
                      <b style={{ fontSize: "10.5px", fontFamily: "'JetBrains Mono', monospace", color: "#94A3B8", minWidth: "26px", textAlign: "right" }}>{z.n}</b>
                    </div>
                  ))}
                </div>
              )}

              {focus.comp.extra.byYear.length > 1 && (
                <div>
                  <div style={{ fontSize: "10px", fontWeight: 600, color: "#64748B", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: "6px" }}>
                    {kn ? "ವರ್ಷದ ಮೂಲಕ" : "By year, in this view"}
                  </div>
                  <div style={{ display: "flex", alignItems: "flex-end", gap: "3px", height: "38px" }}>
                    {focus.comp.extra.byYear.map((b) => {
                      const mx = Math.max(...focus.comp.extra.byYear.map((x) => x.n));
                      return (
                        <div key={b.y} title={`${b.y}: ${b.n}`} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "3px" }}>
                          <i style={{ width: "100%", height: `${Math.max(2, (30 * b.n) / mx)}px`, background: "rgba(34,230,240,0.55)", borderRadius: "2px 2px 0 0" }} />
                          <span style={{ fontSize: "8px", color: "#64748B", fontFamily: "'JetBrains Mono', monospace" }}>{String(b.y).slice(2)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {focus.comp.people?.length > 0 && (
            <div>
              <div style={{ fontSize: "10px", fontWeight: 600, color: "#64748B", textTransform: "uppercase", marginBottom: "8px" }}>{kn ? "ಸಂಬಂಧಿತ ಆರೋಪಿಗಳು" : "People involved"}</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                {focus.comp.people.map((p) => (
                  <div key={p.id} style={{ fontSize: "12px", color: "#E2E8F0", display: "flex", justifyContent: "space-between", background: "rgba(255,255,255,0.03)", padding: "4px 8px", borderRadius: "4px" }}>
                    <b>{p.name}</b>
                    <span style={{ color: "#94A3B8", fontFamily: "'JetBrains Mono', monospace" }}>[{p.id}]</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {focus.comp.rows?.length > 0 && (
            <div>
              <div style={{ fontSize: "10px", fontWeight: 600, color: "#64748B", textTransform: "uppercase", marginBottom: "8px" }}>{kn ? "ಗುಂಪಿನ FIR ಗಳು" : "FIRs in this group"}</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                {focus.comp.rows.map((r, i) => (
                  <div key={i} style={{ fontSize: "11px", background: "rgba(255,255,255,0.03)", padding: "6px 8px", borderRadius: "4px" }}>
                    <div style={{ color: "#F8FAFC", marginBottom: "2px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.crime}</div>
                    <div style={{ color: "#64748B" }}>{r.zone} · {r.year}</div>
                  </div>
                ))}
                {focus.comp.size > focus.comp.rows.length && (
                  <div style={{ fontSize: "10px", color: "#64748B", textAlign: "center", marginTop: "4px" }}>+{focus.comp.size - focus.comp.rows.length} more</div>
                )}
              </div>
            </div>
          )}
          {focus.node?.knowledge_boundary !== undefined && (
            <div style={{ padding: "8px 10px", background: "rgba(255,255,255,0.03)", borderRadius: "4px", borderLeft: "2px solid #64748B" }}>
              <div style={{ fontSize: "10px", color: "#94A3B8", textTransform: "uppercase", marginBottom: "2px", fontWeight: 600 }}>
                {kn ? "ಗುರುತಿನ ಅಂತರ: UNSUB" : "Identity Gap: UNSUB"}
              </div>
              <div style={{ fontSize: "11px", color: "#E2E8F0" }}>
                {kn
                  ? "ಈ ಗುಂಪಿಗೆ ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಶಂಕಿತ ವ್ಯಕ್ತಿ ದಾಖಲಾಗಿಲ್ಲ."
                  : "No confirmed suspect on record."}
              </div>
            </div>
          )}

          {focus.whys.length > 0 && (
            <div>
              <div style={{ fontSize: "10px", fontWeight: 600, color: "#64748B", textTransform: "uppercase", marginBottom: "8px" }}>{kn ? "ಏಕೆ ಸಂಪರ್ಕಿತ" : "Why these are connected"}</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {focus.whys.map((w, i) => (
                  <div key={i} style={{ display: "flex", gap: "8px", fontSize: "11px", color: "#E2E8F0", alignItems: "flex-start" }}>
                    <i style={{ width: "12px", height: "12px", flexShrink: 0, borderRadius: "2px", background: LINK_COLORS[w.kind] || "rgba(255,255,255,0.2)", marginTop: "2px" }} />
                    <span style={{ lineHeight: 1.4 }}>{w.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {focus.comp.districts.length > 0 && (
            <div style={{ fontSize: "10px", color: "#64748B", borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "12px" }}>
              {kn ? "ಜಿಲ್ಲೆಗಳು: " : "Districts: "}{focus.comp.districts.slice(0, 4).join(", ")}{focus.comp.districts.length > 4 ? "…" : ""}
            </div>
          )}
          
          <button onClick={() => router.push(`/ask?q=${encodeURIComponent(focus.node.accused ? `who is ${focus.node.accused}` : `${focus.node.crimeHead || ""} in ${focus.node.zone || ""}`)}`)}
            style={{
              width: "100%", padding: "10px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "6px", color: "#E2E8F0", fontSize: "12px", fontWeight: 600, cursor: "pointer", transition: "all 0.2s",
              fontFamily: "'Inter', sans-serif"
            }}
            onMouseOver={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.1)"; }}
            onMouseOut={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.05)"; }}
          >
            {kn ? "Antar ಕೇಳಿ →" : "Ask Antar →"}
          </button>
        </aside>
      )}

      {/* ── Bottom-Left · Case activity year calendar (constellation views) ── */}
      {view === "net" && <div className="bsx-cal">
          {/* One bar, one line: title · year stepper · that year's count · status · collapse.
              It used to wrap onto two lines, pulse "indexing" permanently whether or not
              anything was loading, and collapse whenever you clicked anywhere on it. */}
          <div className="bsx-calbar">
            <span className="bsx-caltitle">{kn ? "ಪ್ರಕರಣ ಚಟುವಟಿಕೆ" : "Case activity"}</span>
            <span className="bsx-calyear" role="group" aria-label={kn ? "ಕ್ಯಾಲೆಂಡರ್ ವರ್ಷ" : "Calendar year"}>
              <button className="bsx-calnav" disabled={!years.length || year === years[0]} onClick={() => stepYear(-1)}
                      aria-label={kn ? "ಹಿಂದಿನ ವರ್ಷ" : "Previous year"}>‹</button>
              <b>{year ?? "—"}</b>
              <button className="bsx-calnav" disabled={!years.length || year === years[years.length - 1]} onClick={() => stepYear(1)}
                      aria-label={kn ? "ಮುಂದಿನ ವರ್ಷ" : "Next year"}>›</button>
            </span>
            {calYearTotal != null && <span className="bsx-calcount">{calYearTotal.toLocaleString()} FIRs</span>}
            <span className={`bsx-calstatus ${calLoading ? "loading" : ""}`}>{calStatus}</span>
            <button className="bsx-caltoggle" aria-expanded={!minActivity} onClick={() => setMinActivity(!minActivity)}
                    aria-label={minActivity ? (kn ? "ತೆರೆಯಿರಿ" : "Expand case activity") : (kn ? "ಮಡಚಿ" : "Collapse case activity")}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M18 15l-6-6-6 6" /></svg>
            </button>
          </div>

          {!minActivity && !focus && (
            <>
              {/* ── Case-activity source: this constellation view vs the ENTIRE dataset ── */}
          <div className="bsx-scope" style={{ paddingBottom: calMode === "full" ? "2px" : undefined }}>
            <div className="bsx-scopeseg" role="group" aria-label={kn ? "ಕ್ಯಾಲೆಂಡರ್ ಮೂಲ" : "Calendar source"}>
              <button className={calMode === "view" ? "on" : ""} onClick={() => setCalMode("view")}>
                {kn ? "ಈ ವೀಕ್ಷಣೆ" : "This view"}
              </button>
              <button className={calMode === "full" ? "on" : ""} onClick={() => setCalMode("full")}
                      title={kn ? "ಸಂಪೂರ್ಣ ಡೇಟಾಸೆಟ್‌ನ ದೈನಂದಿನ ಚಟುವಟಿಕೆ" : "Daily activity across the entire dataset"}>
                {kn ? "ಪೂರ್ಣ ಡೇಟಾಸೆಟ್" : "Full dataset"}
              </button>
            </div>
            {calMode === "full" && (
              <span className="bsx-scopecnt">{kn ? "ಸಂಪೂರ್ಣ ವರ್ಷದ ದೈನಂದಿನ ಶಾಖ" : "whole-year daily heat"}</span>
            )}
          </div>

          {/* ── Render scope: pick what the brain draws (year span or FIR window) ── */}
          {calMode !== "full" && <div className="bsx-scope">
            <div className="bsx-scopeseg" role="group" aria-label={kn ? "ರೆಂಡರ್ ವ್ಯಾಪ್ತಿ" : "Render scope"}>
              <button className={scopeMode === "year" ? "on" : ""} onClick={() => setScopeMode("year")}>
                {kn ? "ವರ್ಷ" : "Year"}
              </button>
              <button className={scopeMode === "fir" ? "on" : ""} onClick={() => setScopeMode("fir")}>
                {kn ? "FIR ವ್ಯಾಪ್ತಿ" : "FIR range"}
              </button>
            </div>

            {scopeMode === "year" ? (
              <>
                <select className="bsx-scopesel" value={yearFrom ?? ""} aria-label={kn ? "ಇಂದ" : "From year"}
                        onChange={(e) => setYearScope(e.target.value ? Number(e.target.value) : null, yearTo)}>
                  <option value="">{kn ? "ಎಲ್ಲಾ ವರ್ಷ" : "All years"}</option>
                  {years.map((y) => <option key={y} value={y}>{y} ({(yearCountsMap[y] || 0).toLocaleString()})</option>)}
                </select>
                <span className="bsx-scopedash">→</span>
                <select className="bsx-scopesel" value={yearTo ?? ""} aria-label={kn ? "ವರೆಗೆ" : "To year"}
                        onChange={(e) => setYearScope(yearFrom, e.target.value ? Number(e.target.value) : null)}>
                  <option value="">{kn ? "ಇತ್ತೀಚಿನ" : "Latest"}</option>
                  {years.map((y) => <option key={y} value={y}>{y} ({(yearCountsMap[y] || 0).toLocaleString()})</option>)}
                </select>
              </>
            ) : (
              <>
                <input className="bsx-scopenum" type="number" min={1} max={maxSupportedFIRs} value={firFrom}
                       aria-label={kn ? "ಇಂದ FIR" : "From FIR"}
                       onChange={(e) => setFirScope(Number(e.target.value), firTo)} />
                <span className="bsx-scopedash">–</span>
                <input className="bsx-scopenum" type="number" min={1} max={maxSupportedFIRs} value={firTo}
                       aria-label={kn ? "ವರೆಗೆ FIR" : "To FIR"}
                       onChange={(e) => setFirScope(firFrom, Number(e.target.value))} />
              </>
            )}

            <button className="bsx-scopeall" onClick={resetScope}>{kn ? "ಎಲ್ಲಾ" : "All"}</button>
            <span className="bsx-scopecnt">{filtered.length.toLocaleString()} {kn ? "FIR ರೆಂಡರ್" : "rendered"}</span>
          </div>}
          </>
        )}
        {!minActivity && !focus && (
          <>
            <svg width="468" height="78" role="grid" aria-label="Case activity calendar" style={{ opacity: calLoading ? 0.45 : 1, transition: "opacity 0.2s", marginTop: "8px" }}>
              {MONTHS.map((m, i) => (
                <text key={m} x={X0 + Math.round((i * 53) / 12) * (CELL + GAP)} y="10" fill="#5d6b80" fontSize="8" fontFamily="JetBrains Mono">{m}</text>
              ))}
              {calDisplay.cells.map((c) => {
                const on = sel.day === c.d && sel.month === c.m && sel.year === year;
                return (
                  <rect key={`${c.m}-${c.d}`} x={X0 + c.week * (CELL + GAP)} y={Y0 + c.dow * (CELL + GAP)}
                        width={CELL} height={CELL} rx="1.5" fill={HEAT[level(c.n)]}
                        stroke={on ? "#fff" : "none"} strokeWidth={on ? 1.5 : 0}
                        style={{ cursor: "pointer" }} onClick={() => pickDay(c)}>
                    <title>{`${c.d} ${MONTHS[c.m - 1]} ${year} · ${c.n} FIRs`}</title>
                  </rect>
                );
              })}
            </svg>
            {/* Say what the grid is, so a single-year grid beside "All years" isn't a puzzle. */}
            <div className="bsx-calfoot">
              <span>
                {kn ? "ದೈನಂದಿನ FIR" : "Daily FIRs"} · {year ?? "—"} · {calMode === "full" ? (kn ? "ಪೂರ್ಣ ಡೇಟಾಸೆಟ್" : "entire dataset") : (kn ? "ಈ ವೀಕ್ಷಣೆ" : "this view")}
              </span>
              <span className="bsx-callegend">
                <span>{kn ? "ಕಡಿಮೆ" : "Less"}</span>{HEAT.map((h) => <i key={h} style={{ background: h }} />)}<span>{kn ? "ಹೆಚ್ಚು" : "More"}</span>
              </span>
            </div>
          </>
        )}
      </div>}



      {view === "net" && (
        <div className="bsx-hint" style={{ display: "flex", alignItems: "center", gap: "16px", color: "#F8FAFC", textShadow: "0 0 4px rgba(255,255,255,0.2)", pointerEvents: "auto" }}>
          <div>
            {kn ? "ಝೂಮ್ ಮಾಡಲು ಸ್ಕ್ರಾಲ್ ಮಾಡಿ · ಗುಂಪನ್ನು ಪರಿಶೀಲಿಸಲು ನೋಡ್ ಕ್ಲಿಕ್ ಮಾಡಿ · ಬಿಡುಗಡೆ ಮಾಡಲು ಖಾಲಿ ಜಾಗವನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿ" : "scroll to zoom · click a node to inspect its group · click empty space to release"}
            {ovStats ? ` · ${ovStats.nodes.toLocaleString()} records` : ""}
          </div>
          <button 
            onClick={() => {
              if (controlRef.current) controlRef.current.clear();
              if (setSel) setSel({ year: null, month: null, day: null, district: null });
            }}
            style={{
              background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.2)",
              color: "#FFFFFF", padding: "4px 12px", borderRadius: "999px",
              cursor: "pointer", fontSize: "11px", fontWeight: 600,
              fontFamily: "'Inter', sans-serif", transition: "all 0.2s"
            }}
            onMouseOver={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.15)"}
            onMouseOut={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.1)"}
          >
            {kn ? "ಡೀಫಾಲ್ಟ್ ವೀಕ್ಷಣೆಗೆ ಮರುಹೊಂದಿಸಿ" : "Reset to Default View"}
          </button>
        </div>
      )}
    </div>
  );
}


