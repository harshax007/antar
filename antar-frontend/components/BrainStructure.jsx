"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useLang } from "@/components/Providers";
import { buildCrimeGraph, filterRecords, isFutureRecord, dayGrid, aliasFor, CATEGORIES, LINK_COLORS, soften } from "@/lib/crimeGraph";
import { fastRun } from "@/lib/fastRun";
import { AnimatePresence } from "framer-motion";
import { MaterialBackdrop, MaterialPanel } from "@/components/ui/MaterialPanel";
import Constellation from "@/components/Constellation";
import Constellation3D from "@/components/Constellation3D";
import CrimeGraph from "@/components/CrimeGraph";
import BrainViewSummary from "@/components/BrainViewSummary";
import BrainLoader from "@/components/BrainLoader";
import TypingSearchInput from "@/components/TypingSearchInput";
import AgentMascot from "@/components/AgentMascot";
import Orb from "@/components/Orb";


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
const EVIDENCE_CLASS = { K: "Known", D: "Derived", I: "Inferred", U: "Unknown" };
// Fast Run says what each line is in words an officer uses, not the K/D/I/U letters.
const EVIDENCE_PLAIN = {
  en: { K: "From the record", D: "Calculated", I: "Inferred", U: "Not in the record" },
  kn: { K: "ದಾಖಲೆಯಿಂದ", D: "ಲೆಕ್ಕ ಹಾಕಿದ್ದು", I: "ಊಹಿಸಿದ್ದು", U: "ದಾಖಲೆಯಲ್ಲಿಲ್ಲ" },
};

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
  // "Near serious cases": people not named in a serious crime but closest to those who are
  // (Personalized PageRank in app/services/graph_cache.py). Loaded when the tab is opened.
  const [nearSerious, setNearSerious] = useState(null);       // null = not loaded, [] = none
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
  const consoleRef = useRef(null);                     // { run(cmd) } - the Brain terminal
  const [frView, setFrView] = useState("agent");       // Fast Run results: by agent | by priority
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
    if (tab !== "serious" || nearSerious !== null) return;
    fetchJson(`${API}/api/graph/stats`, 5000)
      .then((st) => setNearSerious(Array.isArray(st?.hidden_near_serious) ? st.hidden_near_serious : []))
      .catch(() => setNearSerious([]));
  }, [tab, nearSerious]);

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
  // What an agent may point the officer at: the Fast Run findings for this view that have
  // a next step, each put forward by the agent that would take it.
  const suggestions = useMemo(() => {
    const f = fastRun(filtered || []);
    return ["network", "linkage", "geo"].flatMap((k) => (f[k] || []).filter((c) => c.next?.length)
      .map((c) => ({ agent: /^run (\w+)/.exec(c.next[0].cmd)?.[1] || k, text: c.title, ask: c.next[0].label, cmd: c.next[0].cmd })));
  }, [filtered]);
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
    // `name` is the agent (the run strip and the terminal use it); `ask` is the question its
    // section answers, which is what the results show an officer.
    { id: "pattern", name: kn ? "ಪ್ಯಾಟರ್ನ್" : "Pattern", ask: kn ? "ಏನು ಬದಲಾಗುತ್ತಿದೆ" : "What is changing",
      how: kn ? "ಕಳೆದ ವರ್ಷದ ಅದೇ ತಿಂಗಳುಗಳಿಗೆ ಹೋಲಿಸಿ ಏರುತ್ತಿರುವ ಅಥವಾ ಇಳಿಯುತ್ತಿರುವ ಅಪರಾಧ ಪ್ರಕಾರಗಳು, ಮತ್ತು ಮುಂದಿನ ಹಬ್ಬ" : "Crime types rising or falling against the same months last year, and the next festival" },
    { id: "network", name: kn ? "ನೆಟ್‌ವರ್ಕ್" : "Network", ask: kn ? "ಹಲವು ಪ್ರಕರಣಗಳಲ್ಲಿರುವ ಆರೋಪಿಗಳು" : "Accused on many cases",
      how: kn ? "ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು FIR ನಲ್ಲಿ ಹೆಸರಿಸಲಾದ ಆರೋಪಿಗಳು" : "Accused named in more than one FIR" },
    { id: "geo", name: kn ? "ಜಿಯೋ" : "Geography", ask: kn ? "ಪ್ರಕರಣಗಳು ಎಲ್ಲಿ ಹೆಚ್ಚು" : "Where the cases are",
      how: kn ? "ಈ ವೀಕ್ಷಣೆಯಲ್ಲಿ ಹೆಚ್ಚು FIR ಇರುವ ಜಿಲ್ಲೆ ಮತ್ತು ಠಾಣೆಗಳು" : "The district and stations with the most FIRs in this view" },
    { id: "forecast", name: kn ? "ಮುನ್ಸೂಚನೆ" : "Forecast", ask: kn ? "ಈಗ ಅಸಾಮಾನ್ಯವಾದದ್ದು" : "Unusual right now",
      how: kn ? "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ತುಂಬಾ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳು ದಾಖಲಾಗುತ್ತಿರುವ ಸ್ಥಳಗಳು (ಲೈವ್ ಸ್ಕ್ಯಾನ್)" : "Places recording far more cases than usual (live scan)" },
    { id: "linkage", name: kn ? "ಲಿಂಕೇಜ್" : "Linkage", ask: kn ? "ಒಂದೇ ಸುಳಿವಿನಿಂದ ಸಂಪರ್ಕಿತ ಪ್ರಕರಣಗಳು" : "Cases linked by the same clue",
      how: kn ? "ಒಂದೇ ಆರೋಪಿ, ವಾಹನ, UPI ಐಡಿ ಅಥವಾ IP ಹಂಚಿಕೊಂಡ FIR ಗಳು" : "FIRs that share an accused, vehicle, UPI id or IP address" },
    { id: "corridor", name: kn ? "ಕಾರಿಡಾರ್" : "Corridors", ask: kn ? "ಆರೋಪಿಗಳನ್ನು ಹಂಚಿಕೊಂಡ ಜಿಲ್ಲೆಗಳು" : "Districts sharing accused",
      how: kn ? "ಒಂದೇ ಆರೋಪಿ ಎರಡೂ ಕಡೆ FIR ನಲ್ಲಿರುವ ಜಿಲ್ಲಾ ಜೋಡಿಗಳು" : "District pairs where the same accused is named in FIRs in both" },
    { id: "vigil", name: kn ? "ಕೊರತೆಗಳು" : "Gaps", ask: kn ? "ಈ ವೀಕ್ಷಣೆ ತೋರಿಸಲಾಗದ್ದು" : "What this view cannot show",
      how: kn ? "ಲಿಂಕ್ ಮಾಡಲು ಏನೂ ಇಲ್ಲದ FIR ಗಳು" : "FIRs with nothing to link them on" },
  ];

  async function runThink() {
    if (think?.phase === "run") return;
    setThinkOpen(false);
    setCopied(false);
    setThink({ phase: "run", at: 0 });
    // Fast Run flight indicator matches the agent stagger
    controlRef.current?.think?.(1200);

    // Counted from the records in view - see lib/fastRun.js for what each finding claims.
    const findings = fastRun(filtered);

    // The one finding that is not counted from the view: the top live anomaly alert.
    // (The size of the whole suspect graph used to be listed too; it says nothing about
    // this view, so it is no longer fetched.)
    const live = fetchJson(`${API}/api/alerts`).then((al) => {
      const a = (al?.alerts || [])[0];
      if (a) findings.forecast.push({
        kind: "alert", cls: "D", sev: "high",
        title: `${a.zone}: ${(a.crime_type || "").replace(/_/g, " ").toLowerCase().replace(/\b[a-z]/g, (ch) => ch.toUpperCase())} above usual`,
        detail: `${a.observed} FIRs recorded, well above the usual level for this place${a.z_score?.toFixed ? ` (spike score ${a.z_score.toFixed(1)}; 3 or more is unusual)` : ""}. Worth checking with the station.`,
        source: "live scan for unusual activity",
      });
    }).catch(() => {});

    // Fast, crisp agent scan reveal stagger (120ms instead of sluggish 300ms)
    for (let i = 0; i < AGENTS.length; i++) {
      setThink({ phase: "run", at: i });
      await new Promise((r) => setTimeout(r, 120));
    }
    await live;

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
    const word = { high: "HIGH PRIORITY", med: "MEDIUM PRIORITY", low: "FOR INFORMATION" };
    const lines = [
      `Antar Fast Run - ${think.n.toLocaleString()} FIRs · ${think.scope}`,
      "",
      `Look at this first: ${think.lead ? `${think.lead.title}${think.lead.detail ? ` - ${think.lead.detail}` : ""}` : think.summary}`,
      "",
    ];
    AGENTS.forEach((a) => {
      const f = think.findings[a.id] || [];
      lines.push(a.ask);
      if (!f.length) lines.push("  Nothing stands out in this view.");
      f.forEach((c) => {
        lines.push(`  [${word[c.sev || "low"]}]${c.cls ? ` [${EVIDENCE_PLAIN.en[c.cls] || c.cls}]` : ""} ${c.title}${c.detail ? ` - ${c.detail}` : ""}`);
        (c.evidence || []).forEach((e) => lines.push(`      ${e}`));
        if (c.source) lines.push(`      Based on: ${c.source}`);
      });
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

  const [graphReady, setGraphReady] = useState(false);
  const handleGraphReady = () => setGraphReady(true);
  const isReady = !!recs && graphReady;

  // Fallback safety: lift the curtain even if the graph never reports ready. Only a
  // safety net - the 3D brain lays itself out under the curtain (a few seconds on a slow
  // machine) and says when it is ready; lifting at 800 ms showed an empty screen.
  useEffect(() => {
    if (!recs) { setGraphReady(false); return; }
    const t = setTimeout(() => setGraphReady(true), 6000);
    return () => clearTimeout(t);
  }, [recs]);

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

  const READ_ROWS = kn ? [
    ["big", "#E8A33D", "ಕಿತ್ತಳೆ = ಪ್ರಮುಖ ಆರೋಪಿ", "hub"],
    ["dot", "#18D69A", "ಹಸಿರು = ಅತಿ ಹೆಚ್ಚು ಸಂಪರ್ಕ", "top"],
    ["big", "#8B5CF6", "ನೇರಳೆ = Antar ಏಜೆಂಟ್", "agent"],
    ["dot", "#2BB3A3", "ಟೀಲ್ = ಸಂಪರ್ಕಿತ FIR", "comm"],
    ["ln", "", "ಗೆರೆ = ಹಂಚಿದ ಸಾಕ್ಷ್ಯ", "line"],
    ["dot", "#566072", "ಬೂದು = ಒಂಟಿ FIR", "dust"],
  ] : [
    ["big", "#E8A33D", "Key accused", "hub"],
    ["dot", "#18D69A", "Most connected here", "top"],
    ["big", "#8B5CF6", "Antar agent", "agent"],
    ["dot", "#2BB3A3", "Linked FIR", "comm"],
    ["ln", "", "Shared evidence", "line"],
    ["dot", "#566072", "Isolated FIR", "dust"],
  ];

  const focusName = focus ? (focus.node.accused ? aliasFor(focus.node.accused) : focus.node.zone || focus.node.crimeHead) : "";

  return (
    <div className="bsx-stage">
      <AgentMascot controlRef={controlRef} apiRef={consoleRef} focus={focus} onThink={runThink} kn={kn}
                   agentsOn={isReady && view === "net"} consoleOn={view === "net"} suggestions={suggestions}
                   flying={think?.phase === "run"} flyAgent={think?.phase === "run" ? AGENTS[Math.min(think.at, AGENTS.length - 1)].id : null} />
      <div className="bsx-orbits" aria-hidden="true"><i /><i /></div>
      {filterNote && (
        <div className="bsx-filternote" role="status" aria-live="polite">
          <b>{filterNote.label}</b>
          <span>{filterNote.n.toLocaleString()} {kn ? "FIR" : "FIRs"}</span>
        </div>
      )}

      {/* Smooth Loading Curtain over the stage */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "#03050c",
          zIndex: 25,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          transition: "opacity 1.2s ease",
          opacity: isReady ? 0 : 1,
          pointerEvents: isReady ? "none" : "auto",
        }}
        aria-hidden={isReady}
      >
        <BrainLoader kn={kn} />
      </div>

      {recs && (
        <div className="bsx-netwrap" style={{ visibility: view === "graph" ? "hidden" : "visible" }}>
          {dim3d ? (
            <Constellation3D graph={graph} groupBy={groupBy} active={active} kinds={kinds} controlRef={controlRef}
                             onFocus={setFocus} onStats={setOvStats} onAgent={runThink} focusId={focusId} legendFocus={legendFocus}
                             onReady={handleGraphReady} />
          ) : (
            <Constellation graph={graph} groupBy={groupBy} active={active} kinds={kinds} controlRef={controlRef}
                           onFocus={setFocus} onStats={setOvStats} onAgent={runThink} focusId={focusId} legendFocus={legendFocus}
                           onReady={handleGraphReady} />
          )}
        </div>
      )}
      {recs && view === "graph" && <CrimeGraph recs={recs} kn={kn} />}

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
                      controlRef.current?.clear?.();
                      // Turn the brain and name what changed. Re-colouring the ball in
                      // silence reads as a glitch — the officer cannot tell the filter
                      // applied. The spin is the acknowledgement; the chip is the answer.
                      controlRef.current?.spin?.();
                      const c = graph?.categories?.find((x) => x.cat === cat);
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
        {view === "net" && !focus && (
          <button className="bsx-readbtn" aria-expanded={readOpen} onClick={() => setReadOpen(!readOpen)}>
            {kn ? "ಹೇಗೆ ಓದುವುದು" : "How to read it"} {readOpen ? "▴" : "▾"}
          </button>
        )}
        {view === "net" && !focus && readOpen && (
          <div className="bsx-read">
            {/* A plain key: what each mark means. It used to be clickable (highlight on
                click), which made a legend behave like a filter and dimmed the brain
                unexpectedly - the filters live in Layers & Filters. */}
            {READ_ROWS.map(([kind, color, text], i) => (
              <div key={i} className="r">
                {kind === "ln" ? <i className="ln" /> : <i className={`dot ${kind === "big" ? "big" : ""}`} style={{ background: color }} />}
                {text}
              </div>
            ))}
            <div className="r note">
              {kn ? "ಯಾವುದೇ ನೋಡ್ ಕ್ಲಿಕ್ ಮಾಡಿ" : "Click any node to open its group"}
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
                {[["type", kn ? "ಪ್ರಕಾರ" : "Type"], ["links", kn ? "ಕೊಂಡಿ" : "Links"], ["serious", kn ? "ಗಂಭೀರ" : "Serious"], ["more", kn ? "ಇನ್ನಷ್ಟು" : "More"]].map(([k, l]) => (
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
              {tab === "serious" && (
                <div className="bsx-lrows bsx-ns">
                  <p className="bsx-ns-lede">{kn
                    ? "ಗಂಭೀರ ಪ್ರಕರಣದಲ್ಲಿ ಹೆಸರಿಲ್ಲದ, ಆದರೆ ಅಂಥ ಪ್ರಕರಣದ ಆರೋಪಿಗಳಿಗೆ ಅತಿ ಹತ್ತಿರವಿರುವವರು."
                    : "Not named in a serious case themselves, but closest to people who are."}</p>
                  {nearSerious === null && <p className="bsx-ns-wait">{kn ? "ಲೋಡ್ ಆಗುತ್ತಿದೆ…" : "Loading…"}</p>}
                  {nearSerious?.length === 0 && <p className="bsx-ns-wait">{kn ? "ಯಾರೂ ಇಲ್ಲ." : "No one stands out."}</p>}
                  {(nearSerious || []).map((h) => {
                    // "MURDER" -> "Murder", but acts stay as written: POCSO, NDPS
                    const crime = String(h.nearest_serious_crime || "").replace(/_/g, " ").split(/\s+/)
                      .map((w) => /^(POCSO|NDPS|IPC|BNS)$/i.test(w) ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
                      .join(" ");
                    const how = h.steps === 1
                      ? (kn ? `${h.nearest_serious_name} ಅವರೊಂದಿಗೆ ನೇರ ಸಂಪರ್ಕ` : `Directly linked to ${h.nearest_serious_name}`)
                      : (kn ? `${h.nearest_serious_name} ಅವರಿಂದ ${h.steps} ಹಂತ${h.via?.length ? `, ${h.via.join(", ")} ಮೂಲಕ` : ""}`
                            : `${h.steps} links from ${h.nearest_serious_name}${h.via?.length ? `, via ${h.via.join(", ")}` : ""}`);
                    return (
                      <button key={h.id} type="button" className="bsx-ns-row" onClick={() => router.push(`/search?q=${encodeURIComponent(h.id)}`)}
                              title={kn ? "ಹುಡುಕಾಟದಲ್ಲಿ ತೆರೆಯಿರಿ" : "Open in Search"}>
                        <span className="nm">{h.name} <em>{h.id}</em></span>
                        <span className="how">{how}</span>
                        {crime && <span className="crime">{crime}</span>}
                      </button>
                    );
                  })}
                  <p className="bsx-ns-note">{kn
                    ? "ಪರಿಶೀಲಿಸಬೇಕಾದ ಸುಳಿವು, ತೀರ್ಮಾನವಲ್ಲ. ದಾಖಲಾದ ಸಂಬಂಧಗಳು, ಹಂಚಿದ ಫೋನ್‌ಗಳು ಮತ್ತು ಖಾತೆಗಳಿಂದ."
                    : "A lead to check, not a finding. Built from recorded relationships, shared phones and shared accounts."}</p>
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
          <BrainViewSummary graph={graph} stats={graph?.stats} focus={null} active={active} kinds={kinds}
                            groupBy={groupBy} scope={scopeLabel()} district={null} dim3d={dim3d} kn={kn} />
        </div>
      )}

      {view === "net" && (
        <button className={`bsx-pill think ${think?.phase === "run" ? "busy" : ""}`} onClick={runThink}
                aria-busy={think?.phase === "run"}>
          {think?.phase === "run"
            ? <Orb agent={AGENTS[Math.min(think.at, AGENTS.length - 1)].id} label={kn ? "ಚಾಲನೆಯಲ್ಲಿದೆ" : "Running"} />
            : <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 2a7 7 0 0 1 7 7c0 2.4-1.2 4-2.5 5.4-.9 1-1.5 1.8-1.5 3.1V19h-6v-1.5c0-1.3-.6-2.1-1.5-3.1C6.2 13 5 11.4 5 9a7 7 0 0 1 7-7z" /><path d="M9 22h6" strokeLinecap="round" /></svg>}
          {think?.phase === "run" ? (kn ? "ಚಾಲನೆಯಲ್ಲಿದೆ…" : "Running…") : (kn ? "ಫಾಸ್ಟ್ ರನ್" : "Fast Run")}
        </button>
      )}
      {/* Closed the results? They stay one click away until the next run. */}
      {view === "net" && think?.phase === "done" && !thinkOpen && (
        <button className="bsx-pill think-res" onClick={() => setThinkOpen(true)}>
          {kn ? "ಫಲಿತಾಂಶಗಳು" : "Results"} · {think.total}
        </button>
      )}

      {/* While it runs: one line, so the brain stays visible. */}
      {view === "net" && think?.phase === "run" && (
        <div className="bsx-thinkdock" role="status" aria-live="polite">
          <div className="top">
            <span className="ttl"><Orb agent={AGENTS[Math.min(think.at, AGENTS.length - 1)].id} label={AGENTS[Math.min(think.at, AGENTS.length - 1)].name} />{kn ? "ಫಾಸ್ಟ್ ರನ್" : "Fast Run"} · {AGENTS[Math.min(think.at, AGENTS.length - 1)].name}</span>
            <span className="ct">{Math.min(think.at + 1, AGENTS.length)} / {AGENTS.length}</span>
          </div>
          <div className="bar"><b style={{ width: `${((think.at + 1) / AGENTS.length) * 100}%` }} /></div>
        </div>
      )}

      {/* The results: one line per finding, worst first. The headline and its number are
          all that shows; the records behind it and the next step open on demand. */}
      <AnimatePresence>
      {think?.phase === "done" && thinkOpen && (() => {
        const rank = { high: 0, med: 1, low: 2 };
        const sevName = kn ? { high: "ಹೆಚ್ಚಿನ ಆದ್ಯತೆ", med: "ಮಧ್ಯಮ ಆದ್ಯತೆ", low: "ಮಾಹಿತಿಗಾಗಿ" } : { high: "High priority", med: "Medium priority", low: "For information" };
        const plain = EVIDENCE_PLAIN[kn ? "kn" : "en"];
        const groups = AGENTS.map((a) => ({ ...a, items: think.findings[a.id] || [] }));
        const rows = groups.flatMap((g) => g.items.map((c) => ({ ...c, agent: g.ask })))
          .sort((x, y) => (rank[x.sev] ?? 3) - (rank[y.sev] ?? 3));
        const reported = groups.filter((g) => g.items.length).length;
        const none = kn ? "ಈ ವೀಕ್ಷಣೆಯಲ್ಲಿ ಗಮನಾರ್ಹ ಸಂಕೇತವಿಲ್ಲ." : "Nothing stands out in this view.";
        // One finding, written out in full: nothing an officer needs is behind a click.
        const finding = (c, key, withAgent) => (
          <li key={key} className={`sev-${c.sev || "low"}`}>
            <div className="hd">
              <i className="dot" title={sevName[c.sev || "low"]} />
              <b>{c.title}</b>
              {c.cls && <em title={EVIDENCE_CLASS[c.cls]}>{plain[c.cls] || EVIDENCE_CLASS[c.cls]}</em>}
            </div>
            {c.detail && <p>{c.detail}</p>}
            {c.evidence?.length > 0 && <ul>{c.evidence.map((e, k) => <li key={k}>{e}</li>)}</ul>}
            <div className="ft">
              <span><b className="pri">{sevName[c.sev || "low"]}</b>{withAgent ? ` · ${c.agent}` : ""}{c.source ? ` · ${kn ? "ಆಧಾರ" : "Based on"}: ${c.source}` : ""}</span>
              {/* Hands the record to a console agent: the finding says what is there, the agent works it. */}
              {(c.next || []).map((x) => (
                <button key={x.cmd} onClick={() => { setThinkOpen(false); consoleRef.current?.run(x.cmd); }}>{x.label}</button>
              ))}
            </div>
          </li>
        );
        return (
          <MaterialBackdrop key="fast-run" className="bsx-tm-overlay" onClick={() => setThinkOpen(false)}>
            <MaterialPanel as="section" className="bsx-fr" role="dialog" aria-modal="true" aria-labelledby="bsx-fr-title" onClick={(e) => e.stopPropagation()}>
              <header>
                <h2 id="bsx-fr-title">{kn ? "ಫಾಸ್ಟ್ ರನ್" : "Fast Run"}</h2>
                <span>{think.n.toLocaleString()} FIRs · {think.scope}</span>
                <div className="seg" role="group" aria-label={kn ? "ವೀಕ್ಷಣೆ" : "View"}>
                  <button className={frView === "agent" ? "on" : ""} aria-pressed={frView === "agent"} onClick={() => setFrView("agent")}>{kn ? "ಏಜೆಂಟ್‌ವಾರು" : "By agent"}</button>
                  <button className={frView === "rank" ? "on" : ""} aria-pressed={frView === "rank"} onClick={() => setFrView("rank")}>{kn ? "ಆದ್ಯತೆವಾರು" : "By priority"}</button>
                </div>
                <button onClick={copyThink}>{copied ? (kn ? "ನಕಲಿಸಲಾಗಿದೆ" : "Copied") : (kn ? "ನಕಲಿಸಿ" : "Copy")}</button>
                <button onClick={runThink}>{kn ? "ಮತ್ತೆ" : "Again"}</button>
                <button ref={closeRef} className="x" onClick={() => setThinkOpen(false)} aria-label={kn ? "ಮುಚ್ಚಿ" : "Close"}>×</button>
              </header>

              {think.lead && (
                <div className={`lead sev-${think.lead.sev || "low"}`}>
                  <small><i className="dot" />{kn ? "ಮೊದಲು ನೋಡಬೇಕಾದದ್ದು" : "Look at this first"}</small>
                  <b>{think.lead.title}</b>
                  {think.lead.detail && <p>{think.lead.detail}</p>}
                  {think.lead.next?.[0] && (
                    <div className="lead-next">
                      <span>{kn ? "ಮುಂದಿನ ಹೆಜ್ಜೆ:" : "Next step:"}</span>
                      <button onClick={() => { setThinkOpen(false); consoleRef.current?.run(think.lead.next[0].cmd); }}>{think.lead.next[0].label}</button>
                    </div>
                  )}
                </div>
              )}

              <div className="sum">
                <span><b>{think.total}</b>{kn ? "ಅಂಶಗಳು" : think.total === 1 ? "finding" : "findings"}</span>
                {["high", "med", "low"].map((k) => (
                  <span key={k} className={`sev-${k}`}><i className="dot" /><b>{think.counts?.[k] || 0}</b>{sevName[k]}</span>
                ))}
                <span>{kn ? `${AGENTS.length} ರಲ್ಲಿ ${reported} ಪರಿಶೀಲನೆಗಳಲ್ಲಿ ಅಂಶಗಳಿವೆ` : `${reported} of ${AGENTS.length} checks found something`}</span>
              </div>

              {!rows.length && <p className="none">{none}</p>}
              {frView === "agent" ? (
                <div className="grid">
                  {groups.map((g) => (
                    <article key={g.id} className={g.items.length ? "" : "quiet"}>
                      <h3 title={g.name}>{g.ask}<em>{g.items.length}</em></h3>
                      <p className="how">{g.how}</p>
                      {g.items.length ? <ol>{g.items.map((c, i) => finding(c, i, false))}</ol> : <p className="none">{none}</p>}
                    </article>
                  ))}
                </div>
              ) : (
                <ol className="flat">{rows.map((c, i) => finding(c, i, true))}</ol>
              )}

              <footer>
                {kn
                  ? "ಎಲ್ಲವೂ ಈ ವೀಕ್ಷಣೆಯ FIR ಗಳಿಂದ ಎಣಿಸಲಾಗಿದೆ; \"ಈಗ ಅಸಾಮಾನ್ಯವಾದದ್ದು\" ಲೈವ್ ಸ್ಕ್ಯಾನ್‌ನಿಂದ ಬರುತ್ತದೆ. ಇವು ಸುಳಿವುಗಳು: ಕ್ರಮ ಕೈಗೊಳ್ಳುವ ಮೊದಲು FIR ಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."
                  : "Everything is counted from the FIRs in this view; \"Unusual right now\" comes from the live scan. These are leads: check the FIRs before acting on them."}
              </footer>
            </MaterialPanel>
          </MaterialBackdrop>
        );
      })()}
      </AnimatePresence>

      {/* ── Focus panel - the crime intelligence of the selected group ── */}
      {view === "net" && focus && (() => {
        const c = focus.comp, total = c.size || 1;
        const pct = (n) => Math.round((n / total) * 100);
        const yMax = Math.max(1, ...(c.byYear || []).map((y) => y.n));
        const people = c.accused?.length ? c.accused : (c.people || []).map((p) => ({ ...p, n: null }));
        const lines = c.lines?.length ? c.lines : (c.rows || []).map((r) => ({ ...r, n: 1 }));
        const shownLines = lines.slice(0, 6);
        const restFirs = c.size - shownLines.reduce((t, l) => t + (l.n || 1), 0);
        const stations = (c.byStation || []).length;
        // "CYBER CRIME" -> "Cyber crime": the register's capitals, read as a phrase
        const nice = (t) => { const w = String(t || "").replace(/_/g, " ").trim(); return w === w.toUpperCase() ? w.charAt(0) + w.slice(1).toLowerCase() : w; };
        return (
        <aside className="bsx-focus" aria-label={kn ? "ಫೋಕಸ್" : "Focused group"}>
          <header className="bf-head">
            <div>
              <span className="bf-k">{kn ? "ಫೋಕಸ್ · ಸಂಪರ್ಕಿತ ಗುಂಪು" : "Focus · linked group"}</span>
              <h3>{focusName}</h3>
              {focus.node.accused && <code>{focus.node.accused}</code>}
            </div>
            {/* labelled exit - a bare cross read as decoration, so users refreshed to escape focus */}
            <button className="bf-exit" onClick={() => controlRef.current?.clear()}>{kn ? "ಫೋಕಸ್ ಮುಚ್ಚಿ" : "Exit focus"}</button>
          </header>

          <div className="bf-chips">
            <span><b>{c.size}</b> {c.size === 1 ? "FIR" : "FIRs"}</span>
            <span><b>{c.districts.length}</b> {c.districts.length === 1 ? "district" : "districts"}</span>
            {stations > 0 && <span><b>{stations}</b> {stations === 1 ? "station" : "stations"}</span>}
            {c.years && <span>{c.years[0] === c.years[1] ? c.years[0] : `${c.years[0]} to ${c.years[1]}`}</span>}
          </div>

          {/* The focused group in sentences - who is connected, how, and where. */}
          <BrainViewSummary graph={graph} stats={graph?.stats} focus={focus} active={active} kinds={kinds}
                            groupBy={groupBy} scope={scopeLabel()} district={null} dim3d={dim3d} kn={kn} />

          <section className="bf-mix">
            <div className="bf-donut"><Donut cats={c.cats} total={c.size} /></div>
            <ul>
              {c.cats.slice(0, 5).map((x) => (
                <li key={x.cat}><i style={{ background: x.color }} /><span>{x.label}</span><b>{x.n}</b><em>{pct(x.n)}%</em></li>
              ))}
            </ul>
          </section>

          {c.byYear?.length > 1 && (
            <section>
              <h4>{kn ? "ವರ್ಷವಾರು" : "By year"}</h4>
              <div className="bf-years">
                {c.byYear.map((y) => (
                  <div key={y.name} title={`${y.name}: ${y.n} FIRs`}>
                    <b>{y.n}</b><i style={{ height: `${Math.max(6, (y.n / yMax) * 44)}px` }} /><span>{String(y.name).slice(2)}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {c.byDistrict?.length > 0 && (
            <section>
              <h4>{kn ? "ಎಲ್ಲಿ ದಾಖಲಾಗಿದೆ" : "Where it was registered"}</h4>
              <ul className="bf-bars">
                {c.byDistrict.slice(0, 5).map((d) => (
                  <li key={d.name}><span>{d.name}</span><i><u style={{ width: `${Math.max(4, pct(d.n))}%` }} /></i><b>{d.n}</b></li>
                ))}
              </ul>
              {c.byDistrict.length > 5 && <p className="bf-more">and {c.byDistrict.length - 5} more: {c.byDistrict.slice(5, 9).map((d) => d.name).join(", ")}{c.byDistrict.length > 9 ? "…" : ""}</p>}
            </section>
          )}

          {people.length > 0 && (
            <section>
              <h4>{kn ? "ಸಂಬಂಧಿತ ಆರೋಪಿಗಳು" : "People involved"}<em>{people.length}</em></h4>
              <ul className="bf-people">
                {people.slice(0, 5).map((p) => (
                  <li key={p.id}><b>{p.name}</b><code>{p.id}</code>{p.n != null && <span>{p.n} {p.n === 1 ? "FIR" : "FIRs"}</span>}</li>
                ))}
              </ul>
              {people.length > 5 && <p className="bf-more">and {people.length - 5} more named accused</p>}
              {c.noAccused > 0 && <p className="bf-more">{c.noAccused} {c.noAccused === 1 ? "FIR names" : "FIRs name"} no accused.</p>}
            </section>
          )}

          {c.sharedKeys?.length > 0 && (
            <section>
              <h4>{kn ? "ಹಂಚಿಕೊಂಡ ಗುರುತುಗಳು" : "Shared identifiers"}</h4>
              <ul className="bf-keys">
                {c.sharedKeys.map((k) => <li key={k.kind + k.name}><span>{k.kind}</span><code>{k.name}</code><b>in {k.n} FIRs</b></li>)}
              </ul>
            </section>
          )}

          {shownLines.length > 0 && (
            <section>
              <h4>{kn ? "ಗುಂಪಿನ FIR ಗಳು" : "FIRs in this group"}</h4>
              <ul className="bf-firs">
                {shownLines.map((r, i) => (
                  <li key={i}>
                    <div><span>{nice(r.crime)}</span>{r.n > 1 && <b>{r.n} FIRs</b>}</div>
                    <em>{[r.head && nice(r.head), r.zone, r.year].filter(Boolean).join(" · ")}</em>
                  </li>
                ))}
              </ul>
              {restFirs > 0 && <p className="bf-more">and {restFirs} more {restFirs === 1 ? "FIR" : "FIRs"} in this group</p>}
            </section>
          )}

          {focus.node?.knowledge_boundary !== undefined && (
            <section className="bf-gap">
              <h4>{kn ? "ಗುರುತಿನ ಅಂತರ: UNSUB" : "Identity gap: UNSUB"}</h4>
              <p>{kn ? "ಈ ಗುಂಪಿಗೆ ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಶಂಕಿತ ವ್ಯಕ್ತಿ ದಾಖಲಾಗಿಲ್ಲ." : "No confirmed suspect on record."}</p>
            </section>
          )}

          {focus.whys.length > 0 && (
            <section>
              <h4>{kn ? "ಏಕೆ ಸಂಪರ್ಕಿತ" : "Why these are connected"}</h4>
              <ul className="bf-whys">
                {focus.whys.map((w, i) => <li key={i}><i style={{ background: LINK_COLORS[w.kind] || "rgba(255,255,255,0.2)" }} /><span>{w.text}</span></li>)}
              </ul>
            </section>
          )}

          <button className="bf-ask" onClick={() => router.push(`/ask?q=${encodeURIComponent(focus.node.accused ? `who is ${focus.node.accused}` : `${focus.node.crimeHead || ""} in ${focus.node.zone || ""}`)}`)}>
            {kn ? "Antar ಕೇಳಿ →" : "Ask Antar →"}
          </button>
        </aside>
        );
      })()}

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
            <span className="bsx-scopecnt">{filtered.length.toLocaleString()} {kn ? "FIR ತೋರಿಸಲಾಗಿದೆ" : "shown"}</span>
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
            {kn ? "ಝೂಮ್ ಮಾಡಲು ಸ್ಕ್ರಾಲ್ ಮಾಡಿ · ಗುಂಪನ್ನು ಪರಿಶೀಲಿಸಲು ನೋಡ್ ಕ್ಲಿಕ್ ಮಾಡಿ · ಬಿಡುಗಡೆ ಮಾಡಲು ಖಾಲಿ ಜಾಗವನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿ" : "scroll to zoom · click a dot to see its group · click empty space to go back"}
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
              fontFamily: "'Inter', sans-serif", transition: "color 0.2s, background-color 0.2s, border-color 0.2s, box-shadow 0.2s, opacity 0.2s, transform 0.2s, scale 0.2s"
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



