"use client";

// Map forecast - "where is crime most likely next week, how sure are we, and why?"
// (docs/MAP_FORECASTING_PLAN.md, Phase 5). Everything shown is read from /api/forecast/*;
// every forecast number is Inferred (I), carries a range, and states its as-of date.
//
//   useForecast()   state + fetching, shared by the three pieces below
//   ForecastLayer   markers inside the Leaflet map (stations statewide, beats in a district)
//   ForecastPanel   right-rail panel: as-of chip, layers, controls, "where next", accuracy
//   ForecastCard    one station or beat: range, reasons, 26 weeks, record, Propose patrol

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { CircleMarker, Tooltip } from "react-leaflet";
import L from "leaflet";
import { ShieldCheck, X, Info } from "lucide-react";
import ProposeAction from "@/components/ProposeAction";
import {
  PILL_TO_CATEGORY, FORECAST_RAMP, forecastColor, markerRadius, policeDistrictsFor,
  getForecast, unitShortName, prettyIso, rangeText,
} from "@/lib/forecast";

const T = {
  title: ["Forecast", "ಮುನ್ಸೂಚನೆ"],
  next7: ["next 7 days", "ಮುಂದಿನ 7 ದಿನ"],
  next28: ["next 28 days", "ಮುಂದಿನ 28 ದಿನ"],
  asOf: ["as of", "ದಿನಾಂಕದಂತೆ"],
  inferred: ["Inferred", "ಅನುಮಾನಿತ"],
  where: ["Where next", "ಮುಂದೆ ಎಲ್ಲಿ"],
  stations: ["stations", "ಠಾಣೆಗಳು"],
  beats: ["beats", "ಬೀಟ್‌ಗಳು"],
  layers: ["Layers", "ಪದರಗಳು"],
  lForecast: ["Forecast", "ಮುನ್ಸೂಚನೆ"],
  lClusters: ["Gi* clusters", "Gi* ಗುಚ್ಛಗಳು"],
  lFirs: ["Recent FIRs", "ಇತ್ತೀಚಿನ FIR"],
  preparing: ["Forecast being prepared…", "ಮುನ್ಸೂಚನೆ ಸಿದ್ಧವಾಗುತ್ತಿದೆ…"],
  thin: ["thin history", "ಕಡಿಮೆ ಇತಿಹಾಸ"],
  propose: ["Propose patrol", "ಗಸ್ತು ಪ್ರಸ್ತಾಪಿಸಿ"],
  why: ["Why", "ಏಕೆ"],
  record: ["Track record", "ಹಿಂದಿನ ಸಾಧನೆ"],
  score: ["Scorecard", "ಅಂಕಪಟ್ಟಿ"],
  heads: ["What gets reported here", "ಇಲ್ಲಿ ದಾಖಲಾಗುವ ಅಪರಾಧಗಳು"],
  weeks26: ["Last 26 weeks · the week ahead", "ಕಳೆದ 26 ವಾರ · ಮುಂದಿನ ವಾರ"],
  limits: ["Limits", "ಮಿತಿಗಳು"],
  card: ["Model card", "ಮಾದರಿ ಕಾರ್ಡ್"],
  noReasons: ["Close to its usual level - no reason moves it by 10% or more.",
              "ಸಾಮಾನ್ಯ ಮಟ್ಟದ ಹತ್ತಿರ - ಯಾವ ಕಾರಣವೂ 10% ಕ್ಕಿಂತ ಹೆಚ್ಚು ಬದಲಿಸುವುದಿಲ್ಲ."],
};
const t = (k, kn) => T[k][kn ? 1 : 0];

// ── state ────────────────────────────────────────────────────────────────────

export function useForecast({ crimeType, gadmDistrict, initial = {} }) {
  const [on, setOn] = useState(true);
  const [clustersOn, setClustersOn] = useState(true);
  const [firsOn, setFirsOn] = useState(false);
  const [horizon, setHorizon] = useState(initial.horizon === 28 ? 28 : 7);
  const [category, setCategory] = useState(initial.category || PILL_TO_CATEGORY[crimeType] || "ALL");
  const [status, setStatus] = useState(null);
  const [layer, setLayer] = useState(null);
  const [hot, setHot] = useState(null);
  const [score, setScore] = useState(null);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(initial.unit || null);     // unit name
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [firPoints, setFirPoints] = useState([]);
  const [tick, setTick] = useState(0);                // retry while the backend prepares

  // the map's crime pill drives the forecast category (the panel says when it widens);
  // a deep link from chat (?fc=) wins on first render
  const firstPill = useRef(true);
  useEffect(() => {
    if (firstPill.current && initial.category) { firstPill.current = false; return; }
    firstPill.current = false;
    setCategory(PILL_TO_CATEGORY[crimeType] || "ALL");
  }, [crimeType]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    getForecast("/status").then(setStatus).catch(() => setStatus(null));
  }, [tick]);

  const districts = useMemo(
    () => policeDistrictsFor(gadmDistrict, status?.districts), [gadmDistrict, status]);
  const unitType = gadmDistrict && districts ? "beat" : "station";

  useEffect(() => {
    if (!on) return;
    const ctrl = new AbortController();
    const params = { horizon, category, unit: unitType, district: districts || undefined };
    setError(null);
    Promise.all([
      getForecast("/layer", params, ctrl.signal),
      getForecast("/hotspots", { ...params, limit: 10 }, ctrl.signal),
    ]).then(([lay, hs]) => { setLayer(lay); setHot(hs); })
      .catch((e) => {
        if (e.name === "AbortError") return;
        setError(e);
        if (e.status === 503) setTimeout(() => setTick((n) => n + 1), 8000);
      });
    return () => ctrl.abort();
  }, [on, horizon, category, unitType, districts, tick]);

  // Scorecard: the 7-day forecast graded week by week on the real record. It has no
  // as-of and no horizon, so it only follows the unit type and category; absent (503,
  // or a category that was never graded) the strip is simply not drawn.
  useEffect(() => {
    const ctrl = new AbortController();
    getForecast("/scorecard", { unit: unitType, category }, ctrl.signal)
      .then(setScore).catch((e) => { if (e.name !== "AbortError") setScore(null); });
    return () => ctrl.abort();
  }, [unitType, category, tick]);

  // Recent FIRs: the 3 months up to the shared as-of date, clean coordinates only
  useEffect(() => {
    if (!firsOn || firPoints.length) return;
    const API = process.env.NEXT_PUBLIC_API_URL || "";
    fetch(`${API}/api/map/heat?period=last_3_months`).then((r) => r.json())
      .then((d) => setFirPoints(d.points || [])).catch(() => {});
  }, [firsOn, firPoints.length]);

  const openUnit = useCallback((unit) => { setSelected(unit); }, []);
  useEffect(() => {
    if (!selected) { setDetail(null); return; }
    const ctrl = new AbortController();
    setDetailLoading(true);
    getForecast(`/unit/${encodeURIComponent(selected)}`, { category }, ctrl.signal)
      .then(setDetail).catch((e) => { if (e.name !== "AbortError") setDetail({ error: e.message }); })
      .finally(() => setDetailLoading(false));
    return () => ctrl.abort();
  }, [selected, category]);

  return {
    on, setOn, clustersOn, setClustersOn, firsOn, setFirsOn, horizon, setHorizon,
    category, setCategory, status, layer, hot, score, error, unitType, districts,
    selected, openUnit, close: () => setSelected(null), detail, detailLoading, firPoints,
  };
}

// ── map layer ────────────────────────────────────────────────────────────────

// One canvas renderer for every forecast marker: ~1,100 stations (or a district's beats)
// as SVG nodes would make panning sluggish. It must be a creation option - react-leaflet
// applies pathOptions later through setStyle, where a renderer is ignored.
const canvas = typeof window !== "undefined" ? L.canvas({ padding: 0.4 }) : undefined;

// Visual weight by quantile class: the quiet 40% recede to small faint dots so the
// busiest units stand out; only the top two classes get an outline.
const CLASS_OPACITY = [0.14, 0.22, 0.42, 0.62, 0.82];

// stateView: the whole state is in view, so only the busiest fifth of the units is drawn
// (the top class); every unit shows once a district is open.
export function ForecastLayer({ fc, kn, contains, stateView = false }) {
  const lay = fc.layer;
  const f = useMemo(() => {
    const idx = Object.fromEntries((lay?.fields || []).map((k, i) => [k, i]));
    return (lay?.units || []).map((u) => ({
      unit: u[idx.unit], lat: u[idx.lat], lon: u[idx.lon], expected: u[idx.expected],
      lo: u[idx.lo90], hi: u[idx.hi90], cls: u[idx.class], thin: u[idx.thin],
    }))
      .filter((u) => !contains || contains(u.lat, u.lon))
      .filter((u) => !stateView || u.cls >= 4 || u.unit === fc.selected)
      .sort((a, b) => a.expected - b.expected);        // big ones drawn last, on top
  }, [lay, contains, stateView, fc.selected]);
  return (
    <>
      {fc.firsOn && fc.firPoints.map((p, i) => (
        <CircleMarker key={"fp" + i} center={[p.lat, p.lon]} radius={1.4} interactive={false}
          renderer={canvas} pathOptions={{ stroke: false, fillColor: "#9FB3C8", fillOpacity: 0.35 }} />
      ))}
      {fc.on && f.map((u) => (
        <CircleMarker key={u.unit} center={[u.lat, u.lon]}
          radius={u.cls <= 1 && fc.selected !== u.unit ? 2.4 : markerRadius(u.expected, lay.unit_type)}
          eventHandlers={{ click: () => fc.openUnit(u.unit) }}
          renderer={canvas}
          pathOptions={{
            color: fc.selected === u.unit ? "#FFE55C" : forecastColor(u.cls),
            stroke: fc.selected === u.unit || u.cls >= 3 || u.thin,
            weight: fc.selected === u.unit ? 2.5 : 1,
            opacity: u.thin ? 0.5 : 0.9,
            dashArray: u.thin ? "2 3" : undefined,
            fillColor: forecastColor(u.cls),
            fillOpacity: u.thin ? 0.06 : CLASS_OPACITY[u.cls] ?? 0.4,
          }}>
          <Tooltip className="mx-hs fx-tip" sticky>
            <b>{unitShortName(u.unit)}</b>
            {lay.unit_type === "beat" && <span> · {u.unit.split(" | ")[0]}</span>}
            <br />
            {u.thin ? t("thin", kn) : <>{u.expected.toFixed(1)} {kn ? "ನಿರೀಕ್ಷಿತ" : "expected"} · 90%: {rangeText(u.lo, u.hi)}</>}
            <span className="fx-i">I</span>
          </Tooltip>
        </CircleMarker>
      ))}
    </>
  );
}

// ── panel ────────────────────────────────────────────────────────────────────

export function AsOfChip({ fc, kn }) {
  return null;
}

// Forecast against record, one column per graded week: the bar is what was recorded, the
// dot is what had been forecast the week before, and the tick underneath says whether the
// forecast's top 5% outranked last-4-weeks hotspots that week. Zero-based, so a small gap
// between dot and bar is a small miss and is not drawn as a large one.
function Scorecard({ sc, kn }) {
  const W = 262, H = 38, pad = 3, base = H - 7;
  const rows = sc.weeks, s = sc.summary;
  const max = Math.max(1, ...rows.map((r) => Math.max(r.forecast, r.actual)));
  const bw = (W - pad * 2) / rows.length;
  const y = (v) => base - (v / max) * (base - pad);
  const n = (v) => Math.round(v).toLocaleString("en-IN");
  const pct = (v) => `${(100 * v).toFixed(1)}%`;
  const units = sc.unit_type === "beat" ? t("beats", kn) : t("stations", kn);
  // The rail is one fixed-height window and the hotspot list is what flexes, so every
  // line here is a row taken from that list: four short rows, the rest in tooltips.
  const ranked = kn
    ? `ಮೇಲಿನ 5% ${units} ${s.weeks_ranked} ವಾರಗಳಲ್ಲಿ ${s.weeks_better_than_last4} ವಾರ ಕಳೆದ 4 ವಾರಗಳ ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳಿಗಿಂತ ಹೆಚ್ಚು FIR ಹಿಡಿದವು.`
    : `The top 5% of ${units} caught more FIRs than last-4-weeks hotspots in ${s.weeks_better_than_last4} of ${s.weeks_ranked} weeks.`;
  return (
    <div className="fx-score" title={ranked}>
      <header>
        <b>{t("score", kn)}<span className="fx-i" title={kn ? "ದಾಖಲೆಯಿಂದ ಲೆಕ್ಕಿಸಿದ್ದು" : "Derived from the record"}>D</span></b>
        <span className="fx-sub">{kn
          ? <>{s.weeks_ranked} ವಾರಗಳಲ್ಲಿ <b>{s.weeks_better_than_last4}</b> ಮುಂದೆ</>
          : <><b>{s.weeks_better_than_last4} of {s.weeks_ranked}</b> weeks ahead of last-4-weeks</>}</span>
      </header>
      <svg className="fx-weeks fx-score-weeks" viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label={`Forecast against recorded FIRs over ${rows.length} weeks`}>
        {rows.map((r, i) => {
          const x = pad + i * bw;
          return (
            <g key={r.week}>
              <rect x={x + 0.5} y={y(r.actual)} width={Math.max(bw - 1, 1)} height={base - y(r.actual)} className="bar" />
              <circle cx={x + bw / 2} cy={y(r.forecast)} r="2.2" className="fc" />
              {r.beat_last4 !== undefined && (
                <rect x={x + 0.5} y={base + 3} width={Math.max(bw - 1, 1)} height="3" className={r.beat_last4 ? "win" : "miss"} />)}
              <title>{`Week of ${prettyIso(r.week)}: forecast ${n(r.forecast)}, recorded ${n(r.actual)}`
                + (r.caught !== undefined ? ` · top 5% caught ${pct(r.caught)} (last-4-weeks ${pct(r.caught_last4)})` : "")}</title>
            </g>
          );
        })}
      </svg>
      <p className="fx-small">{kn
        ? <>ಮುನ್ಸೂಚನೆ <b>{n(s.forecast_total)}</b> · ದಾಖಲು <b>{n(s.actual_total)}</b> FIR</>
        : <>Forecast <b>{n(s.forecast_total)}</b> · recorded <b>{n(s.actual_total)}</b> FIRs</>}</p>
      <p className="fx-muted">{kn
        ? `ನೈಜ ದಾಖಲೆ ${prettyIso(sc.window.from)} – ${prettyIso(sc.window.to)} · 80% ವ್ಯಾಪ್ತಿ ${pct(s.coverage80)} ಸರಿ · ಪಟ್ಟಿ ದಾಖಲು · ಚುಕ್ಕೆ ಮುನ್ಸೂಚನೆ`
        : `Real record ${prettyIso(sc.window.from)} – ${prettyIso(sc.window.to)} · 80% ranges held ${pct(s.coverage80)} · bar recorded · dot forecast`}</p>
    </div>
  );
}

export function ForecastPanel({ fc, kn, crimeLabel, onModelCard }) {
  const cats = fc.status?.categories || [];
  const hs = fc.hot;
  const widened = hs && crimeLabel && fc.category !== "ALL"
    && !String(hs.category_label).toLowerCase().includes(String(crimeLabel).toLowerCase());
  const acc = hs?.accuracy;
  const refusal = fc.error?.status === 422 ? fc.error.detail : null;
  return (
    <section className="fx-panel mx-panel" aria-label={kn ? "ಮುನ್ಸೂಚನೆ" : "Forecast"}>
      <header>
        <b>{t("where", kn)}</b>
        <span className="fx-sub">{hs ? `${hs.scope} · ${fc.unitType === "beat" ? t("beats", kn) : t("stations", kn)}` : ""}</span>
      </header>
      <AsOfChip fc={fc} kn={kn} />

      <div className="fx-controls">
        <div className="fx-seg" role="radiogroup" aria-label={kn ? "ಅವಧಿ" : "Horizon"}>
          {[7, 28].map((h) => (
            <button key={h} role="radio" aria-checked={fc.horizon === h} className={fc.horizon === h ? "on" : ""}
                    onClick={() => fc.setHorizon(h)}>{h} {kn ? "ದಿನ" : "days"}</button>
          ))}
        </div>
        <select value={fc.category} onChange={(e) => fc.setCategory(e.target.value)} aria-label={kn ? "ವರ್ಗ" : "Category"}>
          {cats.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </select>
      </div>
      {widened && (
        <p className="fx-note">{kn
          ? `ಮುನ್ಸೂಚನೆ ವರ್ಗಗಳ ಮಟ್ಟದಲ್ಲಿ: "${crimeLabel}" → ${hs.category_label}.`
          : <>The forecast works on categories: “{crimeLabel}” is shown as <b>{hs.category_label}</b>, which includes it.</>}</p>
      )}

      <div className="fx-layers" role="group" aria-label={t("layers", kn)}>
        {[["on", "setOn", "lForecast"], ["clustersOn", "setClustersOn", "lClusters"], ["firsOn", "setFirsOn", "lFirs"]].map(([k, set, label]) => (
          <label key={k}><input type="checkbox" checked={fc[k]} onChange={(e) => fc[set](e.target.checked)} /> {t(label, kn)}</label>
        ))}
      </div>

      {fc.error?.status === 503 && <p className="fx-muted">{t("preparing", kn)}</p>}
      {refusal && (
        <p className="fx-note">{refusal.message}{refusal.options?.length ? ` ${kn ? "ಆಯ್ಕೆಗಳು" : "Try"}: ${refusal.options.join(", ")}` : ""}</p>
      )}

      {fc.on && hs && (
        <>
          <ol className="fx-list">
            {hs.items.map((it) => (
              <li key={it.unit}>
                <button className={fc.selected === it.unit ? "on" : ""} onClick={() => fc.openUnit(it.unit)}>
                  <span className="r">{it.rank}</span>
                  <span className="n">
                    <b>{it.name}</b>
                    <em>{it.unit_type === "beat" ? it.station : it.district}</em>
                  </span>
                  <span className="v">
                    {it.history === "thin" ? <em>{t("thin", kn)}</em>
                      : <>{rangeText(it.band80.lo, it.band80.hi)}<em>{kn ? "ಸಂಭವನೀಯ" : "likely"}</em></>}
                  </span>
                </button>
              </li>
            ))}
          </ol>
          <div className="fx-legend" aria-hidden="true">
            <span>{kn ? "ಕಡಿಮೆ" : "fewer"}</span>
            {FORECAST_RAMP.map((c) => <i key={c} style={{ background: c }} />)}
            <span>{kn ? "ಹೆಚ್ಚು ನಿರೀಕ್ಷಿತ FIR" : "more expected FIRs"}</span>
          </div>
        </>
      )}

      {fc.score?.weeks?.length > 0 && <Scorecard sc={fc.score} kn={kn} />}

      {acc && (
        <button className="fx-acc" onClick={onModelCard} title={t("card", kn)}>
          <Info size={12} aria-hidden="true" />
          <span>{kn
            ? `ಹಿಂದಿನ ಪರೀಕ್ಷೆ (${acc.window}, ನೈಜ ದಾಖಲೆ): ಮೇಲಿನ 5% ${fc.unitType === "beat" ? "ಬೀಟ್‌ಗಳು" : "ಠಾಣೆಗಳು"} ಮುಂದಿನ ${fc.horizon} ದಿನಗಳ ${Math.round(acc.top5_share_caught * 100)}% FIR ಹಿಡಿದವು.`
            : <>Back-tested on {acc.window} (real record): the top 5% of {fc.unitType}s caught <b>{Math.round(acc.top5_share_caught * 100)}%</b> of the next {fc.horizon} days’ FIRs (last-4-weeks hotspots: {Math.round(acc.top5_share_caught_last4 * 100)}%){acc.pai5 ? <> · PAI {acc.pai5.toFixed(1)}</> : null}.</>}
          </span>
          <u>{t("card", kn)} ↗</u>
        </button>
      )}
    </section>
  );
}

// ── one unit ─────────────────────────────────────────────────────────────────

function Weeks({ history, ahead }) {
  const W = 262, H = 64, pad = 4;
  const all = [...history.map((h) => h.firs), ...(ahead || []).map((a) => a.hi90)];
  const max = Math.max(1, ...all);
  const n = history.length + (ahead?.length || 0);
  const bw = (W - pad * 2) / n;
  const y = (v) => H - pad - (v / max) * (H - pad * 2);
  return (
    <svg className="fx-weeks" viewBox={`0 0 ${W} ${H}`} role="img"
         aria-label={`Weekly FIRs over ${history.length} weeks, then the forecast week`}>
      {history.map((h, i) => (
        <rect key={h.week_start} x={pad + i * bw + 0.5} y={y(h.firs)} width={Math.max(bw - 1, 1)}
              height={H - pad - y(h.firs)} className="bar"><title>{h.week_start}: {h.firs}</title></rect>
      ))}
      {(ahead || []).map((a, j) => {
        const x = pad + (history.length + j) * bw + bw / 2;
        return (
          <g key={a.week_start} className="ahead">
            <line x1={x} x2={x} y1={y(a.hi90)} y2={y(a.lo90)} className="b90" />
            <line x1={x} x2={x} y1={y(a.hi80)} y2={y(a.lo80)} className="b80" />
            <circle cx={x} cy={y(a.expected)} r="2.6" />
            <title>Week of {a.week_start}: expected {a.expected}, 80% {a.lo80}–{a.hi80}, 90% {a.lo90}–{a.hi90}</title>
          </g>
        );
      })}
    </svg>
  );
}

export function ForecastCard({ fc, kn, sessionRole }) {
  const [propose, setPropose] = useState(false);
  const d = fc.detail;
  const panelRef = useRef(null);
  useEffect(() => { if (d && !d.error) panelRef.current?.focus(); }, [d]);
  if (!fc.selected) return null;
  const f = d?.forecast?.[String(fc.horizon)] || d?.forecast?.["7"];
  const canPropose = sessionRole && sessionRole !== "Approver";
  const say = (en, kan) => (kn ? kan : en);

  const evidence = f ? [
    { label: kn ? "ಮುನ್ಸೂಚನೆ (I)" : "Forecast (Inferred)", value: f.summary },
    { label: kn ? "ದಿನಾಂಕದಂತೆ" : "As of", value: `${d.as_of.as_of} · ${d.as_of.basis}` },
    ...f.drivers.slice(0, 3).map((r) => ({ label: `${kn ? "ಕಾರಣ" : "Reason"} ${r.effect}`, value: r.text })),
    d.track_record && { label: t("record", kn), value: d.track_record.text },
    d.accuracy && { label: kn ? "ನಿಖರತೆ" : "Accuracy", value: d.accuracy.text },
  ].filter(Boolean) : [];

  return (
    <section ref={panelRef} tabIndex={-1} className="fx-card mx-panel" aria-label={d?.name || fc.selected}
             aria-busy={fc.detailLoading}>
      <header>
        <div>
          <b>{d?.name || unitShortName(fc.selected)}</b>
          <em>{d ? [d.unit_type === "beat" ? d.station : null, d.district].filter(Boolean).join(" · ") : "…"}</em>
        </div>
        <button className="fx-back" onClick={fc.close} aria-label={kn ? "ಪಟ್ಟಿಗೆ ಹಿಂದಿರುಗಿ" : "Back to Where next"}>
          ‹ {kn ? "ಪಟ್ಟಿ" : "Where next"}
        </button>
      </header>

      {d?.error && <p className="fx-note">{d.error}</p>}
      {!d && <p className="fx-muted">…</p>}

      {f && (() => {
        const thin = f.history === "thin";
        const days = fc.horizon === 7 ? t("next7", kn) : t("next28", kn);
        const unitWord = d.category === "ALL" ? "FIRs" : d.category_label;
        // against a usual period here, in words: within 10% reads as usual
        const vs = typeof f.vs_usual === "number" ? f.vs_usual : null;
        const pct = vs == null ? null : Math.round(Math.abs(vs) * 100);
        const level = vs == null ? null : vs >= 0.1 ? "up" : vs <= -0.1 ? "down" : "same";
        const levelText = level === "up" ? say(`${pct}% above usual`, `ಸಾಮಾನ್ಯಕ್ಕಿಂತ ${pct}% ಹೆಚ್ಚು`)
          : level === "down" ? say(`${pct}% below usual`, `ಸಾಮಾನ್ಯಕ್ಕಿಂತ ${pct}% ಕಡಿಮೆ`)
          : level === "same" ? say("About usual", "ಸುಮಾರು ಸಾಮಾನ್ಯ") : null;
        // what the model weighed, largest effect first, when no single reason is notable
        const steps = (f.why?.steps || []).slice().sort((p, q) => Math.abs(q.factor - 1) - Math.abs(p.factor - 1)).slice(0, 4);
        // the 26 weeks, in one line
        const hist = d.history || [];
        const avg = hist.length ? hist.reduce((x, h) => x + h.firs, 0) / hist.length : null;
        const peak = hist.reduce((m, h) => (!m || h.firs > m.firs ? h : m), null);
        const byType = (d.by_category_7d || []).filter((c) => c.hi80 > 0);
        const heads = (d.top_crime_heads || []).filter((h) => !/^other$/i.test(h.crime_head));
        const tr = d.track_record;
        const seeded = typeof d.as_of?.real_share === "number" && d.as_of.real_share < 1 ? Math.round((1 - d.as_of.real_share) * 100) : null;
        return (
        <>
          <div className="fx-range">
            <span className="fx-i" title={say("Inferred: a forecast, not a record", "ಅನುಮಾನಿತ: ಮುನ್ಸೂಚನೆ, ದಾಖಲೆಯಲ್ಲ")}>I</span>
            {thin ? <p>{f.summary}</p> : (
              <>
                <span className="fx-when">{days}</span>
                <div className="big">{rangeText(f.band80.lo, f.band80.hi)}<small> {unitWord}</small></div>
                {levelText && <span className={`fx-level ${level}`}>{levelText}</span>}
                <dl className="fx-bands">
                  <div><dt>{say("Most likely", "ಹೆಚ್ಚು ಸಂಭವನೀಯ")}</dt><dd>{rangeText(f.band80.lo, f.band80.hi)}<small>{say("8 in 10 chance", "10 ರಲ್ಲಿ 8 ಅವಕಾಶ")}</small></dd></div>
                  <div><dt>{say("Wider range", "ವಿಶಾಲ ಶ್ರೇಣಿ")}</dt><dd>{rangeText(f.band90.lo, f.band90.hi)}<small>{say("9 in 10 chance", "10 ರಲ್ಲಿ 9 ಅವಕಾಶ")}</small></dd></div>
                  {f.usual > 0 && <div><dt>{fc.horizon === 7 ? say("A usual week", "ಸಾಮಾನ್ಯ ವಾರ") : say("A usual 28 days", "ಸಾಮಾನ್ಯ 28 ದಿನ")}</dt><dd>{Math.round(f.usual)}<small>{say("FIRs here", "ಇಲ್ಲಿ FIR")}</small></dd></div>}
                </dl>
              </>
            )}
          </div>

          <h6>{say("Why this number", "ಈ ಸಂಖ್ಯೆ ಏಕೆ")}</h6>
          {f.drivers.length ? (
            <ul className="fx-why">
              {f.drivers.slice(0, 4).map((r) => (
                <li key={r.key} className={r.factor > 1 ? "up" : "down"}><b>{r.effect}</b><span>{r.text}</span></li>
              ))}
            </ul>
          ) : (
            <>
              <p className="fx-plain">{say("Close to a usual period here. No single reason moves it by 10% or more.", t("noReasons", kn))}</p>
              {steps.length > 0 && (
                <ul className="fx-why fx-why-flat" aria-label={say("What the forecast weighed", "ಮುನ್ಸೂಚನೆ ಪರಿಗಣಿಸಿದ್ದು")}>
                  {steps.map((r) => <li key={r.key}><b>{r.effect}</b><span>{r.label}</span></li>)}
                </ul>
              )}
            </>
          )}

          <h6>{say("Last 26 weeks and the week ahead", t("weeks26", kn))}</h6>
          <Weeks history={hist} ahead={d.ahead} />
          <p className="fx-legend">
            <span><i className="sw bar" />{say("FIRs each week", "ಪ್ರತಿ ವಾರದ FIR")}</span>
            <span><i className="sw ahead" />{say("Week ahead, with its range", "ಮುಂದಿನ ವಾರ, ಶ್ರೇಣಿಯೊಂದಿಗೆ")}</span>
          </p>
          {avg != null && (
            <p className="fx-small">{say(`Average ${avg.toFixed(1)} a week. Busiest: ${peak.firs} in the week of ${prettyIso(peak.week_start)}.`,
                                       `ವಾರಕ್ಕೆ ಸರಾಸರಿ ${avg.toFixed(1)}. ಹೆಚ್ಚು: ${prettyIso(peak.week_start)} ವಾರದಲ್ಲಿ ${peak.firs}.`)}</p>
          )}

          {d.category === "ALL" && byType.length > 0 ? (
            <>
              <h6>{say("Next 7 days by type", "ಮುಂದಿನ 7 ದಿನ, ಪ್ರಕಾರದಂತೆ")}</h6>
              <ul className="fx-heads">
                {byType.map((c) => <li key={c.category}><span>{c.label}</span><b>{rangeText(c.lo80, c.hi80)}</b></li>)}
              </ul>
            </>
          ) : heads.length > 0 && (
            <>
              <h6>{say("Most reported here, last 52 weeks", t("heads", kn))}</h6>
              <ul className="fx-heads">
                {heads.map((h) => <li key={h.crime_head}><span>{h.crime_head}</span><b>{h.firs}</b></li>)}
              </ul>
            </>
          )}

          {tr && (
            <>
              <h6>{t("record", kn)}</h6>
              <p className="fx-plain">{tr.weeks_flagged
                ? say(`Flagged as a top-5% hotspot in ${tr.weeks_flagged} of the ${tr.weeks} weeks it was tested on.`,
                    `ಪರೀಕ್ಷಿಸಿದ ${tr.weeks} ವಾರಗಳಲ್ಲಿ ${tr.weeks_flagged} ವಾರ ಮೇಲಿನ 5% ಹಾಟ್‌ಸ್ಪಾಟ್ ಆಗಿತ್ತು.`)
                : say(`Not flagged as a top-5% hotspot in any of the ${tr.weeks} weeks it was tested on.`,
                    `ಪರೀಕ್ಷಿಸಿದ ${tr.weeks} ವಾರಗಳಲ್ಲಿ ಒಮ್ಮೆಯೂ ಮೇಲಿನ 5% ಹಾಟ್‌ಸ್ಪಾಟ್ ಆಗಿರಲಿಲ್ಲ.`)}</p>
            </>
          )}

          <div className="fx-datanote">
            {seeded != null && seeded > 0 && (
              <p><b>{say("Demonstration data.", "ಪ್ರದರ್ಶನ ದತ್ತಾಂಶ.")}</b> {say(`${seeded}% of the last 13 weeks here is seeded, not the real record.`,
                                                                          `ಇಲ್ಲಿನ ಕಳೆದ 13 ವಾರಗಳ ${seeded}% ಬೀಜ ದತ್ತಾಂಶ, ನೈಜ ದಾಖಲೆಯಲ್ಲ.`)}</p>
            )}
            {(d.limits || []).map((x, k) => <p key={k}>{x}</p>)}
          </div>

          {canPropose && (
            <button className="mx-hitl-btn fx-propose" onClick={() => setPropose(true)}
                    title={kn ? "ಮೇಲ್ವಿಚಾರಕರ ಅನುಮೋದನೆ ಅಗತ್ಯ" : "Requires supervising officer approval"}>
              <ShieldCheck size={13} aria-hidden="true" /> {t("propose", kn)}
            </button>
          )}
          <ProposeAction open={propose} onClose={() => setPropose(false)} type="patrol_redeployment" kn={kn}
            defaults={{
              zone: d.unit, crime_focus: String(d.category_label).toLowerCase(),
              justification: `Forecast (Inferred), ${d.as_of.as_of}: ${f.summary}${f.drivers[0] ? ` ${f.drivers[0].text}.` : ""}`,
            }}
            evidence={evidence} />
        </>
        );
      })()}
    </section>
  );
}

// ── model card ───────────────────────────────────────────────────────────────

export function ModelCardModal({ open, onClose, kn }) {
  const [card, setCard] = useState(null);
  useEffect(() => {
    if (!open || card) return;
    const API = process.env.NEXT_PUBLIC_API_URL || "";
    fetch(`${API}/api/predict/model-card`).then((r) => r.json()).then(setCard).catch(() => setCard({ error: true }));
  }, [open, card]);
  useEffect(() => {
    if (!open) return;
    const k = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [open, onClose]);
  if (!open || typeof document === "undefined") return null;
  return createPortal(
    <div className="pa-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="fx-modelcard mx-panel" role="dialog" aria-modal="true" aria-label={t("card", kn)}>
        <button className="x" onClick={onClose} aria-label="Close"><X size={16} /></button>
        {!card ? <p className="fx-muted">…</p> : card.error ? <p className="fx-note">Model card unavailable.</p> : (
          <>
            <b>{card.model_name}</b>
            <span className="ty">{card.type}</span>
            <h6>{kn ? "ಮೌಲ್ಯಮಾಪನ" : "How well it works"}</h6>
            <ul>{card.evaluation.map((e, i) => <li key={i}>{e}</li>)}</ul>
            <h6>{kn ? "ವಿನ್ಯಾಸ" : "How it works"}</h6>
            <p>{card.architecture}</p>
            <h6>{kn ? "ಉದ್ದೇಶಿತ ಬಳಕೆ" : "Intended use"}</h6>
            <p>{card.intended_use}</p>
            <h6>{kn ? "ಮಿತಿಗಳು ಮತ್ತು ಪಕ್ಷಪಾತ" : "Limits and bias"}</h6>
            <ul>{card.bias_disclosure.map((b, i) => <li key={i}>{b}</li>)}</ul>
            <p className="prov">{card.data_provenance}</p>
          </>
        )}
      </div>
    </div>, document.body);
}
