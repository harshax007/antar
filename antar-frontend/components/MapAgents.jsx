"use client";

// Agents on the Map.
//
// Three of Antar's agents work on a place rather than a person, so they are the three
// offered here: Geo, Forecast and Pattern. They sit in a dock on the map and an officer
// drags one onto a district; it runs on that district for the date selected in the
// calendar. A click does the same for the district already selected, which is also the
// path on a touch screen, where a drag does not exist.
//
// Nothing is computed in this file. The agents are the console agents
// (POST /api/console/run, app/agents/brain_console.py) and answer exactly as they do in
// the Brain terminal; the dated figures above their answer come from the map's own date
// window. MapScreen owns the run; this file is the dock, the drop target and the card.

import { useEffect, useMemo, useRef, useState } from "react";
import { GeoJSON, useMap } from "react-leaflet";
import { Mascot } from "@/components/SafeMascot";
import { asset } from "@/lib/assets";

export const MAP_AGENTS = [
  { id: "geo", face: "drone", name: "Geo", kn: "ಜಿಯೋ",
    does: "Ranks the beats in the district by cases expected in the next 7 days.",
    doesKn: "ಮುಂದಿನ 7 ದಿನಗಳ ನಿರೀಕ್ಷಿತ ಪ್ರಕರಣಗಳ ಪ್ರಕಾರ ಜಿಲ್ಲೆಯ ಬೀಟ್‌ಗಳನ್ನು ಶ್ರೇಣೀಕರಿಸುತ್ತದೆ." },
  { id: "forecast", face: "clockwork", name: "Forecast", kn: "ಮುನ್ಸೂಚನೆ",
    does: "Gives the likely range of cases at the district's busiest station.",
    doesKn: "ಜಿಲ್ಲೆಯ ಅತಿ ಕಾರ್ಯನಿರತ ಠಾಣೆಯಲ್ಲಿ ಸಂಭವನೀಯ ಪ್ರಕರಣಗಳ ವ್ಯಾಪ್ತಿಯನ್ನು ನೀಡುತ್ತದೆ." },
  { id: "pattern", face: "radio", name: "Pattern", kn: "ಮಾದರಿ",
    does: "Finds groups of the selected crime type, close in place and time.",
    doesKn: "ಆಯ್ಕೆ ಮಾಡಿದ ಅಪರಾಧದ, ಸ್ಥಳ ಮತ್ತು ಸಮಯದಲ್ಲಿ ಹತ್ತಿರವಿರುವ ಪ್ರಕರಣಗಳ ಗುಂಪುಗಳನ್ನು ಹುಡುಕುತ್ತದೆ." },
  { id: "research", face: "postbot", name: "Research", kn: "ಸಂಶೋಧನೆ",
    does: "Lists who is named on the most FIRs there, and opens a dossier on the one you pick.",
    doesKn: "ಅಲ್ಲಿ ಹೆಚ್ಚು FIR ಗಳಲ್ಲಿ ಹೆಸರಿರುವವರನ್ನು ಪಟ್ಟಿಮಾಡಿ, ನೀವು ಆರಿಸಿದವರ ದಾಖಲೆ ತೆರೆಯುತ್ತದೆ." },
];
const BY_ID = Object.fromEntries(MAP_AGENTS.map((a) => [a.id, a]));
const DRAG_TYPE = "application/x-antar-agent";

const Face = ({ agent, size }) => (
  <Mascot size={size} label={`${agent.name} agent`} directions={asset(`/mascots/sm/${agent.face}-directions.webp`)} reactions={asset(`/mascots/sm/${agent.face}-reactions.webp`)} />
);

// ── the dock ────────────────────────────────────────────────────────────────────
// A button on the map, and nothing else until it is pressed. Open, the agents stand on the
// map itself - no panel behind them - each with a line saying what it does, so a drag starts
// from the map and ends on it. `district`: the district already selected, if any (a click
// runs there). `onRun(id)`: run on the selected district. `onDrag(id | null)`: a drag
// began / ended.
export function MapAgentsMenu({ kn, district, dragging, onRun, onDrag }) {
  const [open, setOpen] = useState(false);
  const [nudge, setNudge] = useState(false);     // clicked with no district selected
  // On a narrow map there is no empty corner: the agents then take less room.
  const ref = useRef(null);
  const [tight, setTight] = useState(false);
  useEffect(() => {
    const frame = ref.current?.parentElement;
    if (!frame || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([e]) => setTight(e.contentRect.width < 640));
    ro.observe(frame);
    return () => ro.disconnect();
  }, []);
  useEffect(() => { if (district) setNudge(false); }, [district]);

  const pick = (id) => {
    if (!district) { setNudge(true); return; }
    onRun(id);
  };

  return (
    <aside ref={ref} className={`mxa${open ? " open" : ""}${tight ? " tight" : ""}${dragging ? " is-drag" : ""}`} aria-label={kn ? "ನಕ್ಷೆ ಏಜೆಂಟ್‌ಗಳು" : "Map agents"}>
      <button type="button" className="mxa-btn" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        {kn ? "ಏಜೆಂಟ್‌ಗಳು" : "Agents"} <span aria-hidden="true">{open ? "▴" : "▾"}</span>
      </button>
      {open && (
        <>
          <p className={`mxa-hint${nudge ? " nudge" : ""}`}>
            {nudge ? (kn ? "ಮೊದಲು ಒಂದು ಜಿಲ್ಲೆಯನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿ, ಅಥವಾ ಏಜೆಂಟ್ ಅನ್ನು ಜಿಲ್ಲೆಯ ಮೇಲೆ ಎಳೆದು ಬಿಡಿ." : "Click a district first, or drag the agent onto one.")
              : district ? (kn ? `ಒಂದನ್ನು ಜಿಲ್ಲೆಯ ಮೇಲೆ ಎಳೆದು ಬಿಡಿ, ಅಥವಾ ${district} ನಲ್ಲಿ ಚಲಾಯಿಸಲು ಕ್ಲಿಕ್ ಮಾಡಿ.` : `Drag one onto a district, or click to run it on ${district}.`)
              : (kn ? "ಒಂದನ್ನು ಜಿಲ್ಲೆಯ ಮೇಲೆ ಎಳೆದು ಬಿಡಿ." : "Drag one onto a district.")}
          </p>
          <div className="mxa-list" role="menu">
            {MAP_AGENTS.map((a, i) => (
              <div key={a.id} role="menuitem" tabIndex={0} draggable className="mxa-a" style={{ animationDelay: `${i * 45}ms` }}
                   onClick={() => pick(a.id)}
                   onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(a.id); } }}
                   onDragStart={(e) => {
                     e.dataTransfer.setData(DRAG_TYPE, a.id);
                     e.dataTransfer.setData("text/plain", a.name);
                     e.dataTransfer.effectAllowed = "copy";
                     const face = e.currentTarget.querySelector(".mxa-face");
                     if (face) e.dataTransfer.setDragImage(face, 24, 24);
                     // after the browser has taken its picture of the agent: the others fade back
                     setTimeout(() => onDrag(a.id), 0);
                   }}
                   onDragEnd={() => onDrag(null)}>
                <span className="mxa-face"><Face agent={a} size={tight ? 38 : 48} /></span>
                <span className="mxa-txt"><b>{kn ? a.kn : a.name}</b><em>{kn ? a.doesKn : a.does}</em></span>
              </div>
            ))}
          </div>
        </>
      )}
    </aside>
  );
}

// ── the drop target: lives inside <MapContainer> ────────────────────────────────
// Finds the district under the pointer from the boundary file itself, so it does not
// depend on which map layer happens to be on top.
function makeFinder(geo) {
  const feats = (geo?.features || []).map((f) => {
    const g = f.geometry || {};
    const polys = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
    const rings = polys.map((p) => p[0]).filter(Boolean);
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const r of rings) for (const [x, y] of r) {
      if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y;
    }
    return { f, rings, minX, minY, maxX, maxY };
  }).filter((x) => x.rings.length);
  const inRing = (x, y, r) => {
    let inside = false;
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const [xi, yi] = r[i], [xj, yj] = r[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  };
  return (lat, lon) => feats.find((x) => lon >= x.minX && lon <= x.maxX && lat >= x.minY && lat <= x.maxY
    && x.rings.some((r) => inRing(lon, lat, r)))?.f || null;
}
const nameOf = (f) => f?.properties?.district || f?.properties?.NAME_2 || null;

export function AgentDropLayer({ geo, dragging, onHover, onDrop }) {
  const map = useMap();
  const finder = useMemo(() => makeFinder(geo), [geo]);
  const [over, setOver] = useState(null);
  const overRef = useRef(null);
  const cb = useRef({ onHover, onDrop });
  cb.current = { onHover, onDrop };

  useEffect(() => {
    const el = map.getContainer();
    const set = (f) => {
      if (f === overRef.current) return;
      overRef.current = f; setOver(f); cb.current.onHover?.(nameOf(f));
    };
    const at = (e) => {
      const r = el.getBoundingClientRect();
      const ll = map.containerPointToLatLng([e.clientX - r.left, e.clientY - r.top]);
      return finder(ll.lat, ll.lng);
    };
    const mine = (e) => Array.from(e.dataTransfer?.types || []).includes(DRAG_TYPE);
    const onOver = (e) => {
      if (!mine(e)) return;
      const f = at(e);
      if (f) { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; }
      set(f);
    };
    const onLeave = (e) => { if (!el.contains(e.relatedTarget)) set(null); };
    const onDropEv = (e) => {
      if (!mine(e)) return;
      e.preventDefault();
      const f = at(e), id = e.dataTransfer.getData(DRAG_TYPE);
      set(null);
      if (f && id) cb.current.onDrop?.(id, nameOf(f));
    };
    el.addEventListener("dragover", onOver);
    el.addEventListener("dragleave", onLeave);
    el.addEventListener("drop", onDropEv);
    return () => { el.removeEventListener("dragover", onOver); el.removeEventListener("dragleave", onLeave); el.removeEventListener("drop", onDropEv); };
  }, [map, finder]);

  // a drag that ends anywhere else leaves nothing lit
  useEffect(() => { if (!dragging && overRef.current) { overRef.current = null; setOver(null); cb.current.onHover?.(null); } }, [dragging]);

  if (!over) return null;
  return <GeoJSON key={nameOf(over)} data={over} interactive={false}
                  style={() => ({ color: "#FFE55C", weight: 3, dashArray: "7 6", fillColor: "#FFE55C", fillOpacity: 0.2 })} />;
}

// ── the answer ──────────────────────────────────────────────────────────────────
// Written for the officer reading it, in English or Kannada. Where the agent returns its
// figures (`body.facts`), the card words them itself, in short plain sentences; otherwise
// it shows the agent's own lines. Nothing here computes a figure: every number is the
// agent's or the map's dated count.
const nice = (iso, kn) => { const d = new Date(`${String(iso).slice(0, 10)}T00:00:00`); return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(kn ? "kn-IN" : "en-IN", { day: "numeric", month: "short", year: "numeric" }); };
const ordinal = (n) => { const s = ["th", "st", "nd", "rd"], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };
const fmt = (n) => (n == null ? "?" : Number(n).toLocaleString("en-IN"));
// "about 5", or one decimal for a small expected count
const about = (x) => (x == null ? "?" : x >= 2 ? String(Math.round(x)) : String(Math.round(x * 10) / 10));
const T = (kn, en, k) => (kn ? k : en);

const CLASS_WORD = {
  K: ["Fact", "ದಾಖಲೆ"], D: ["Worked out", "ಲೆಕ್ಕಹಾಕಿದ್ದು"], I: ["Estimate", "ಅಂದಾಜು"], U: ["Unknown", "ತಿಳಿದಿಲ್ಲ"],
};
const ANSWER_TITLE = {
  forecast: ["Next 7 days", "ಮುಂದಿನ 7 ದಿನಗಳು"], geo: ["Where to look next", "ಮುಂದೆ ಎಲ್ಲಿ ಗಮನಿಸಬೇಕು"],
  pattern: ["Groups of cases", "ಪ್ರಕರಣಗಳ ಗುಂಪುಗಳು"], research: ["Who is named most", "ಹೆಚ್ಚು ಹೆಸರಿಸಲ್ಪಟ್ಟವರು"],
};
// the forecast's reasons, by key (the English label is the forecast's own)
const REASON_KN = {
  level: "ಸಾಮಾನ್ಯ ಮಟ್ಟದತ್ತ ಸೆಳೆತ", area: "ಇಡೀ ಪ್ರದೇಶದ ಮುನ್ಸೂಚನೆ", season: "ವರ್ಷದ ಈ ಸಮಯ",
  neighbours: "ನೆರೆಯ ಠಾಣೆಗಳು", recent: "ಕಳೆದ 4 ವಾರಗಳು", last_year: "ಕಳೆದ ವರ್ಷದ ಇದೇ ವಾರಗಳು",
};

// What the forecast rests on, said once: demonstration data, reported FIRs, and the date.
function ForecastNotes({ f, run, kn }) {
  const share = f.real_share;
  const notes = [];
  if (share != null && share < 0.99) {
    notes.push(share <= 0
      ? T(kn, `Built on demonstration data: the real FIRs in this register end on ${nice(f.real_record_ends, kn)}. Read it as an example of the method, not as a real forecast.`,
             `ಪ್ರದರ್ಶನ ದತ್ತಾಂಶದ ಮೇಲೆ ಆಧಾರಿತ: ಈ ರಿಜಿಸ್ಟರ್‌ನ ನಿಜವಾದ FIR ಗಳು ${nice(f.real_record_ends, kn)} ರಂದು ಕೊನೆಗೊಳ್ಳುತ್ತವೆ. ಇದನ್ನು ವಿಧಾನದ ಉದಾಹರಣೆಯಾಗಿ ಓದಿ, ನಿಜವಾದ ಮುನ್ಸೂಚನೆಯಾಗಿ ಅಲ್ಲ.`)
      : T(kn, `${Math.round(share * 100)}% of the last 13 weeks behind it are real FIRs; the rest is demonstration data.`,
             `ಇದರ ಹಿಂದಿನ ಕೊನೆಯ 13 ವಾರಗಳಲ್ಲಿ ${Math.round(share * 100)}% ನಿಜವಾದ FIR ಗಳು; ಉಳಿದದ್ದು ಪ್ರದರ್ಶನ ದತ್ತಾಂಶ.`));
  }
  if (run.crime && f.crime === "All crime") {
    notes.push(T(kn, `This counts all crime, not only ${String(run.crimeLabel || "").toLowerCase()}.`,
                     `ಇದು ಎಲ್ಲಾ ಅಪರಾಧಗಳನ್ನು ಎಣಿಸುತ್ತದೆ, ${run.crimeLabel || ""} ಮಾತ್ರವಲ್ಲ.`));
  }
  if (f.as_of && run.date !== f.as_of) {
    notes.push(T(kn, `A forecast always starts from today (${nice(f.as_of, kn)}). The count above follows the date you picked.`,
                     `ಮುನ್ಸೂಚನೆ ಯಾವಾಗಲೂ ಇಂದಿನಿಂದ (${nice(f.as_of, kn)}) ಆರಂಭವಾಗುತ್ತದೆ. ಮೇಲಿನ ಎಣಿಕೆ ನೀವು ಆರಿಸಿದ ದಿನಾಂಕವನ್ನು ಅನುಸರಿಸುತ್ತದೆ.`));
  }
  notes.push(T(kn, "It counts FIRs that get reported, not every crime.", "ಇದು ದಾಖಲಾದ FIR ಗಳನ್ನು ಮಾತ್ರ ಎಣಿಸುತ್ತದೆ, ಎಲ್ಲಾ ಅಪರಾಧಗಳನ್ನಲ್ಲ."));
  return <ul className="mxr-notes">{notes.map((t, i) => <li key={i} className={i === 0 && share != null && share < 0.99 ? "warn" : ""}>{t}</li>)}</ul>;
}

function ForecastAnswer({ f, run, kn }) {
  const [l0, l1] = f.likely || [], [v0, v1] = f.very_likely || [];
  const diff = f.usual ? f.expected / f.usual - 1 : 0;
  const pct = Math.round(Math.abs(diff) * 100);
  const lead = f.expected != null && f.expected < 1
    ? T(kn, `${f.station}: less than 1 FIR expected.`, `${f.station}: 1 ಕ್ಕಿಂತ ಕಡಿಮೆ FIR ನಿರೀಕ್ಷಿತ.`)
    : T(kn, `${f.station}: about ${about(f.expected)} FIRs expected.`, `${f.station}: ಸುಮಾರು ${about(f.expected)} FIR ಗಳು ನಿರೀಕ್ಷಿತ.`);
  return (
    <>
      <p className="mxr-line">{lead}</p>
      <ul className="mxr-facts">
        {l0 != null && <li>{T(kn, <>Likely <b>{l0} to {l1}</b> (8 times in 10).</>, <>ಸಾಧ್ಯತೆ <b>{l0} ರಿಂದ {l1}</b> (10 ರಲ್ಲಿ 8 ಬಾರಿ).</>)}</li>}
        {v0 != null && <li>{T(kn, <>Very likely <b>{v0} to {v1}</b> (9 times in 10).</>, <>ಹೆಚ್ಚು ಸಾಧ್ಯತೆ <b>{v0} ರಿಂದ {v1}</b> (10 ರಲ್ಲಿ 9 ಬಾರಿ).</>)}</li>}
        {f.usual != null && (
          <li>{pct < 10
            ? T(kn, `A usual week here has about ${about(f.usual)}, so this is a normal week.`, `ಇಲ್ಲಿ ಸಾಮಾನ್ಯ ವಾರದಲ್ಲಿ ಸುಮಾರು ${about(f.usual)}; ಇದು ಸಾಮಾನ್ಯ ವಾರ.`)
            : T(kn, `A usual week here has about ${about(f.usual)}; this week is ${pct}% ${diff > 0 ? "higher" : "lower"}.`,
                    `ಇಲ್ಲಿ ಸಾಮಾನ್ಯ ವಾರದಲ್ಲಿ ಸುಮಾರು ${about(f.usual)}; ಈ ವಾರ ${pct}% ${diff > 0 ? "ಹೆಚ್ಚು" : "ಕಡಿಮೆ"}.`)}</li>
        )}
      </ul>
      <h6 className="mxr-sub">{T(kn, "Why", "ಏಕೆ")}</h6>
      {f.reasons?.length
        ? <ul className="mxr-facts">{f.reasons.map((r) => <li key={r.key}>{kn ? (REASON_KN[r.key] || r.label) : r.label}: <b>{r.effect}</b></li>)}</ul>
        : <p className="mxr-dim">{T(kn, "No single reason moves it by 10% or more.", "ಯಾವುದೇ ಒಂದು ಕಾರಣ ಇದನ್ನು 10% ಅಥವಾ ಹೆಚ್ಚು ಬದಲಿಸುವುದಿಲ್ಲ.")}</p>}
      {f.tested_weeks ? (
        <>
          <h6 className="mxr-sub">{T(kn, "How it has done", "ಹಿಂದಿನ ಪರೀಕ್ಷೆ")}</h6>
          <p className="mxr-dim">
            {!f.busiest_weeks
              ? T(kn, `Checked against ${f.tested_weeks} past weeks: the forecast never put this station among the busiest 5%.`,
                      `ಹಿಂದಿನ ${f.tested_weeks} ವಾರಗಳೊಂದಿಗೆ ಪರೀಕ್ಷಿಸಲಾಗಿದೆ: ಮುನ್ಸೂಚನೆ ಈ ಠಾಣೆಯನ್ನು ಎಂದಿಗೂ ಅತಿ ಕಾರ್ಯನಿರತ 5% ರಲ್ಲಿ ಸೇರಿಸಲಿಲ್ಲ.`)
              : T(kn, `Checked against ${f.tested_weeks} past weeks: the forecast put it among the busiest 5% in ${f.busiest_weeks} of them${f.busiest_weeks_with_fir != null ? `, and it recorded at least one FIR in ${f.busiest_weeks_with_fir} of those` : ""}.`,
                      `ಹಿಂದಿನ ${f.tested_weeks} ವಾರಗಳೊಂದಿಗೆ ಪರೀಕ್ಷಿಸಲಾಗಿದೆ: ಮುನ್ಸೂಚನೆ ಇದನ್ನು ${f.busiest_weeks} ವಾರ ಅತಿ ಕಾರ್ಯನಿರತ 5% ರಲ್ಲಿ ಸೇರಿಸಿತ್ತು${f.busiest_weeks_with_fir != null ? `; ಅವುಗಳಲ್ಲಿ ${f.busiest_weeks_with_fir} ವಾರ ಕನಿಷ್ಠ ಒಂದು FIR ದಾಖಲಾಯಿತು` : ""}.`)}
          </p>
        </>
      ) : null}
      <ForecastNotes f={f} run={run} kn={kn} />
    </>
  );
}

function GeoAnswer({ f, run, kn }) {
  return (
    <>
      <p className="mxr-line">{T(kn, `Busiest beats in ${f.district}, next ${f.days} days:`, `${f.district} ನಲ್ಲಿ ಮುಂದಿನ ${f.days} ದಿನಗಳ ಅತಿ ಕಾರ್ಯನಿರತ ಬೀಟ್‌ಗಳು:`)}</p>
      <ol>
        {(f.beats || []).map((b, i) => (
          <li key={i}>
            <b>{b.name}</b>, {b.station}: {T(kn, <>likely <b>{b.likely?.[0]} to {b.likely?.[1]}</b> FIRs</>, <>ಸಾಧ್ಯತೆ <b>{b.likely?.[0]} ರಿಂದ {b.likely?.[1]}</b> FIR ಗಳು</>)}
          </li>
        ))}
      </ol>
      {f.beats_forecast ? <p className="mxr-dim">{T(kn, `${fmt(f.beats_forecast)} beats forecast in all.`, `ಒಟ್ಟು ${fmt(f.beats_forecast)} ಬೀಟ್‌ಗಳಿಗೆ ಮುನ್ಸೂಚನೆ.`)}</p> : null}
      <ForecastNotes f={f} run={run} kn={kn} />
    </>
  );
}

function PatternAnswer({ f, run, kn }) {
  const crime = kn ? (run.crimeLabel || f.crime) : String(run.crimeLabel || f.crime).toLowerCase();
  const place = f.place || run.district;
  return (
    <>
      <p className="mxr-line">
        {T(kn, `${fmt(f.clusters)} ${f.clusters === 1 ? "group" : "groups"} of ${crime} cases close together in place and time in ${place}. `,
               `${place} ನಲ್ಲಿ ಸ್ಥಳ ಮತ್ತು ಸಮಯದಲ್ಲಿ ಹತ್ತಿರವಿರುವ ${crime} ಪ್ರಕರಣಗಳ ${fmt(f.clusters)} ಗುಂಪುಗಳು. `)}
        {f.active
          ? T(kn, `${f.active} ${f.active === 1 ? "is" : "are"} still going on.`, `${f.active} ಇನ್ನೂ ಮುಂದುವರಿದಿವೆ.`)
          : T(kn, "None is still going on.", "ಯಾವುದೂ ಈಗ ಮುಂದುವರಿದಿಲ್ಲ.")}
      </p>
      <h6 className="mxr-sub">{T(kn, "The largest", "ಅತಿ ದೊಡ್ಡವು")}</h6>
      <ol>
        {(f.groups || []).slice(0, 3).map((g, i) => (
          <li key={i}>
            <b>{fmt(g.size)}</b> {T(kn, "cases", "ಪ್ರಕರಣಗಳು")}
            {g.zones?.length > 1 ? ` · ${g.zones.join(", ")}` : ""}
            {g.from ? ` · ${g.from === g.to ? nice(g.from, kn) : T(kn, `${nice(g.from, kn)} to ${nice(g.to, kn)}`, `${nice(g.from, kn)} ರಿಂದ ${nice(g.to, kn)}`)}` : ""}
            {g.active ? <span className="hot"> · {T(kn, "still going on", "ಮುಂದುವರಿದಿದೆ")}</span> : null}
          </li>
        ))}
      </ol>
      <ul className="mxr-notes">
        <li>{T(kn, `Looked at the latest ${fmt(f.scanned)} FIRs of this type here.`, `ಇಲ್ಲಿನ ಈ ಬಗೆಯ ಇತ್ತೀಚಿನ ${fmt(f.scanned)} FIR ಗಳನ್ನು ನೋಡಲಾಗಿದೆ.`)}</li>
        <li>{T(kn, "A group means cases near each other in place and time. It does not mean one offender.",
                   "ಗುಂಪು ಎಂದರೆ ಸ್ಥಳ ಮತ್ತು ಸಮಯದಲ್ಲಿ ಹತ್ತಿರವಿರುವ ಪ್ರಕರಣಗಳು. ಒಬ್ಬನೇ ಅಪರಾಧಿ ಎಂದು ಅರ್ಥವಲ್ಲ.")}</li>
      </ul>
    </>
  );
}

function ResearchPlaceAnswer({ f, kn }) {
  return (
    <>
      <p className="mxr-line">{T(kn, `Named on the most FIRs in ${f.place}:`, `${f.place} ನಲ್ಲಿ ಹೆಚ್ಚು FIR ಗಳಲ್ಲಿ ಹೆಸರಿರುವವರು:`)}</p>
      <ol>
        {(f.people || []).map((p) => (
          <li key={p.id}>
            <b>{p.id}</b>: {T(kn, `${p.firs} ${p.firs === 1 ? "FIR" : "FIRs"}`, `${p.firs} FIR ಗಳು`)}
            {" "}({p.from === p.to ? p.from : `${p.from}–${p.to}`}){p.groups?.length ? ` · ${p.groups.join(", ")}` : ""}
          </li>
        ))}
      </ol>
      <ul className="mxr-notes">
        <li>{T(kn, "Being named on many FIRs is a count, not a finding about the person.", "ಹಲವು FIR ಗಳಲ್ಲಿ ಹೆಸರಿರುವುದು ಒಂದು ಎಣಿಕೆ ಮಾತ್ರ, ವ್ಯಕ್ತಿಯ ಬಗ್ಗೆ ತೀರ್ಮಾನವಲ್ಲ.")}</li>
        <li>{T(kn, "Pick one below to open their dossier.", "ಅವರ ದಾಖಲೆ ತೆರೆಯಲು ಕೆಳಗೆ ಒಬ್ಬರನ್ನು ಆರಿಸಿ.")}</li>
      </ul>
    </>
  );
}

// `run`: { agent, district, zone, date, crime, crimeLabel, station, status, body, dated }
// `stale`: the calendar or the crime filter moved since this was run.
export function MapAgentResult({ run, stale, kn, onClose, onRun, onRerun }) {
  if (!run) return null;
  const a = BY_ID[run.agent] || MAP_AGENTS[0];
  const name = kn ? a.kn : a.name;
  const b = run.body, d = run.dated, f = b?.facts;
  const working = run.status === "running";
  // "run forecast Chitradurga Central PS" -> a button; an agent the map does not carry is left out
  const next = (b?.next || []).map((t) => /^run (geo|forecast|pattern|research)\b\s*(.*)$/i.exec(t)).filter(Boolean)
    .map((m) => ({ id: m[1].toLowerCase(), arg: m[2].trim() })).filter((n) => n.id !== run.agent || n.arg);
  const crimeName = run.crimeLabel || T(kn, "All crimes", "ಎಲ್ಲಾ ಅಪರಾಧ");
  const notRun = b && (b.status === "refused" || b.status === "error");
  const cls = notRun ? null : (b?.evidence_class || "U");
  // A Pattern run that found nothing, worded here so it reads in Kannada too.
  const patternEmpty = run.agent === "pattern" && b?.status === "empty";

  return (
    <section className={`mxr${working ? " is-working" : ""}`} aria-live="polite" aria-busy={working}>
      <header>
        <span className="mxr-face"><Face agent={a} size={52} /></span>
        <div>
          <b>{name}{run.station ? <i> · {run.station}</i> : null}</b>
          <span>{run.district} · {nice(run.date, kn)} · {crimeName}</span>
        </div>
        <button type="button" onClick={onClose} aria-label={T(kn, "Close", "ಮುಚ್ಚಿ")} title={T(kn, "Close", "ಮುಚ್ಚಿ")}>&times;</button>
      </header>

      {run.zone && (
        <div className="mxr-rec">
          <h6>{T(kn, "What the record shows", "ದಾಖಲೆಯಲ್ಲಿ ಇರುವುದು")} <em>{CLASS_WORD.K[kn ? 1 : 0]}</em></h6>
          {d === "pending" && <p className="mxr-dim">{T(kn, `Counting the 30 days up to ${nice(run.date, kn)}…`, `${nice(run.date, kn)} ವರೆಗಿನ 30 ದಿನಗಳನ್ನು ಎಣಿಸಲಾಗುತ್ತಿದೆ…`)}</p>}
          {d && d !== "pending" && (
            <>
              <p>
                {T(kn, <><b>{fmt(d.observed)}</b> {d.observed === 1 ? "case" : "cases"} in the 30 days up to {nice(d.end || run.date, kn)}.</>,
                       <>{nice(d.end || run.date, kn)} ವರೆಗಿನ 30 ದಿನಗಳಲ್ಲಿ <b>{fmt(d.observed)}</b> ಪ್ರಕರಣಗಳು.</>)}
                {d.observed > 0 && d.of > 1
                  ? " " + (d.rank === 1
                      ? T(kn, `The busiest of ${d.of} areas.`, `${d.of} ಪ್ರದೇಶಗಳಲ್ಲಿ ಅತಿ ಹೆಚ್ಚು.`)
                      : T(kn, `${ordinal(d.rank)} busiest of ${d.of} areas.`, `${d.of} ಪ್ರದೇಶಗಳಲ್ಲಿ ${d.rank}ನೇ ಸ್ಥಾನ.`))
                  : null}
              </p>
              {d.observed > 0 && (
                <p className="mxr-dim">
                  {d.hot
                    ? <span className="hot">{T(kn, "Hotspot: this area and the areas around it are all unusually busy.", "ಹಾಟ್‌ಸ್ಪಾಟ್: ಈ ಪ್ರದೇಶ ಮತ್ತು ಸುತ್ತಲಿನ ಪ್ರದೇಶಗಳು ಎಲ್ಲವೂ ಅಸಾಮಾನ್ಯವಾಗಿ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳನ್ನು ಹೊಂದಿವೆ.")}</span>
                    : T(kn, "Not a hotspot: the areas around it are not busy as well.", "ಹಾಟ್‌ಸ್ಪಾಟ್ ಅಲ್ಲ: ಸುತ್ತಲಿನ ಪ್ರದೇಶಗಳಲ್ಲಿ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳಿಲ್ಲ.")}
                </p>
              )}
            </>
          )}
          {d === null && <p className="mxr-dim">{T(kn, "The count for this date could not be read.", "ಈ ದಿನಾಂಕದ ಎಣಿಕೆಯನ್ನು ಓದಲಾಗಲಿಲ್ಲ.")}</p>}
        </div>
      )}

      <div className="mxr-ans">
        {working && <p className="mxr-work">{T(kn, `${name} is working on ${run.district}`, `${name} ${run.district} ಮೇಲೆ ಕೆಲಸ ಮಾಡುತ್ತಿದೆ`)}<span className="mxr-dots" aria-hidden="true" /></p>}
        {!working && b && (
          <>
            <h6>
              {(ANSWER_TITLE[run.agent] || ["Answer", "ಉತ್ತರ"])[kn ? 1 : 0]}
              {notRun
                ? <em className="no">{T(kn, "Not run", "ಚಲಾಯಿಸಲಿಲ್ಲ")}</em>
                : <em className={`c-${cls}`}>{(CLASS_WORD[cls] || CLASS_WORD.U)[kn ? 1 : 0]}</em>}
            </h6>
            {f?.kind === "forecast" ? <ForecastAnswer f={f} run={run} kn={kn} />
              : f?.kind === "geo" ? <GeoAnswer f={f} run={run} kn={kn} />
              : f?.kind === "pattern" ? <PatternAnswer f={f} run={run} kn={kn} />
              : f?.kind === "research_place" ? <ResearchPlaceAnswer f={f} kn={kn} />
              : patternEmpty ? (
                <p className="mxr-line">{T(kn, `No group of ${String(crimeName).toLowerCase()} cases close together in place and time is on record in ${run.district}.`,
                                             `${run.district} ನಲ್ಲಿ ಸ್ಥಳ ಮತ್ತು ಸಮಯದಲ್ಲಿ ಹತ್ತಿರವಿರುವ ${crimeName} ಪ್ರಕರಣಗಳ ಯಾವುದೇ ಗುಂಪು ದಾಖಲೆಯಲ್ಲಿ ಇಲ್ಲ.`)}</p>
              ) : (
                <>
                  <p className="mxr-line">{b.bottom_line}</p>
                  {b.context ? <p className="mxr-dim">{b.context}</p> : null}
                  {b.evidence?.length > 0 && <ol>{b.evidence.slice(0, 5).map((t, i) => <li key={i}>{String(t).replace(/^\d+\.\s*/, "")}</li>)}</ol>}
                  {b.limits?.length > 0 && <p className="mxr-note">{b.limits.slice(0, 2).join(" ")}</p>}
                  {kn && b.status === "ok" && <p className="mxr-note">ಈ ಉತ್ತರ ಸದ್ಯಕ್ಕೆ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಮಾತ್ರ ಲಭ್ಯ.</p>}
                </>
              )}
          </>
        )}
      </div>

      {!working && (next.length > 0 || stale) && (
        <footer>
          {stale && <button type="button" className="again" onClick={onRerun}>{T(kn, "Run again for the new date or crime", "ಹೊಸ ದಿನಾಂಕ ಅಥವಾ ಅಪರಾಧಕ್ಕೆ ಮತ್ತೆ ಚಲಾಯಿಸಿ")}</button>}
          {next.map((n, i) => (
            <button type="button" key={i} onClick={() => onRun(n.id, n.arg)}>
              {n.id === "research" && n.arg
                ? T(kn, `Open dossier: ${n.arg}`, `ದಾಖಲೆ ತೆರೆಯಿರಿ: ${n.arg}`)
                : `${kn ? BY_ID[n.id].kn : BY_ID[n.id].name}${n.arg ? `: ${n.arg}` : ""}`}
            </button>
          ))}
        </footer>
      )}
    </section>
  );
}
