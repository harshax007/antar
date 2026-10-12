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
import { Mascot } from "page-mascot";

export const MAP_AGENTS = [
  { id: "geo", face: "drone", name: "Geo", does: "Where in the area to look next" },
  { id: "forecast", face: "clockwork", name: "Forecast", does: "What to expect at its busiest station" },
  { id: "pattern", face: "radio", name: "Pattern", does: "Is the selected crime clustering here" },
];
const BY_ID = Object.fromEntries(MAP_AGENTS.map((a) => [a.id, a]));
const DRAG_TYPE = "application/x-antar-agent";
const CLASS_WORD = { K: "Known", D: "Derived", I: "Inferred", U: "Unknown" };

const Face = ({ agent, size }) => (
  <Mascot size={size} label={`${agent.name} agent`} directions={`/mascots/sm/${agent.face}-directions.webp`} reactions={`/mascots/sm/${agent.face}-reactions.webp`} />
);

// ── the dock ────────────────────────────────────────────────────────────────────
// Sits on the map itself, in the corner east of the state where there is nothing to
// cover. The agents are always in view there, so a drag starts from the map and ends on
// it. `district`: the district already selected, if any (a click runs there).
// `onRun(id)`: run on the selected district. `onDrag(id | null)`: a drag began / ended.
const DOCK_KEY = "antar_map_agents_closed";

export function MapAgentsMenu({ kn, district, dragging, onRun, onDrag }) {
  const [open, setOpen] = useState(true);
  const [hot, setHot] = useState(null);          // the agent under the pointer
  const [nudge, setNudge] = useState(false);     // clicked with no district selected
  // On a narrow map the state fills the frame and there is no empty corner: the dock
  // then shrinks to the three faces so it covers as little of the districts as it can.
  const ref = useRef(null);
  const [tight, setTight] = useState(false);
  useEffect(() => {
    const frame = ref.current?.parentElement;
    if (!frame || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([e]) => setTight(e.contentRect.width < 640));
    ro.observe(frame);
    return () => ro.disconnect();
  }, []);
  useEffect(() => { try { if (localStorage.getItem(DOCK_KEY) === "1") setOpen(false); } catch { /* opens */ } }, []);
  const toggle = () => setOpen((v) => { try { localStorage.setItem(DOCK_KEY, v ? "1" : "0"); } catch { /* not kept */ } return !v; });
  useEffect(() => { if (district) setNudge(false); }, [district]);

  const pick = (id) => {
    if (!district) { setNudge(true); return; }
    onRun(id);
  };
  const says = hot ? BY_ID[hot].does
    : nudge ? "Click a district first, or drag the agent onto one."
    : district ? `Drag onto a district, or click to run on ${district}.`
    : "Drag an agent onto a district.";

  return (
    <aside ref={ref} className={`mxa${open ? " open" : ""}${tight ? " tight" : ""}${dragging ? " is-drag" : ""}`} aria-label={kn ? "ನಕ್ಷೆ ಏಜೆಂಟ್‌ಗಳು" : "Map agents"}>
      <button type="button" className="mxa-btn" aria-expanded={open} onClick={toggle}>
        {kn ? "ಏಜೆಂಟ್‌ಗಳು" : "Agents"} <span aria-hidden="true">{open ? "▴" : "▾"}</span>
      </button>
      {open && (
        <>
          <div className="mxa-row" role="menu">
            {MAP_AGENTS.map((a) => (
              <div key={a.id} role="menuitem" tabIndex={0} draggable className="mxa-a" title={a.does}
                   onMouseEnter={() => setHot(a.id)} onMouseLeave={() => setHot(null)}
                   onFocus={() => setHot(a.id)} onBlur={() => setHot(null)}
                   onClick={() => pick(a.id)}
                   onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(a.id); } }}
                   onDragStart={(e) => {
                     e.dataTransfer.setData(DRAG_TYPE, a.id);
                     e.dataTransfer.setData("text/plain", a.name);
                     e.dataTransfer.effectAllowed = "copy";
                     const face = e.currentTarget.querySelector(".mxa-face");
                     if (face) e.dataTransfer.setDragImage(face, 26, 26);
                     // after the browser has taken its picture of the agent: the dock fades back
                     setTimeout(() => onDrag(a.id), 0);
                   }}
                   onDragEnd={() => onDrag(null)}>
                <span className="mxa-face"><Face agent={a} size={tight ? 38 : 52} /></span>
                <b>{a.name}</b>
              </div>
            ))}
          </div>
          <p className={`mxa-hint${nudge && !hot ? " nudge" : ""}`}>{says}</p>
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
const nice = (iso) => { const d = new Date(`${iso}T00:00:00`); return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }); };
const ordinal = (n) => { const s = ["th", "st", "nd", "rd"], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };

// `run`: { agent, district, zone, date, crimeLabel, station, status, body, dated }
// `stale`: the calendar or the crime filter moved since this was run.
export function MapAgentResult({ run, stale, todayIso, onClose, onRun, onRerun }) {
  if (!run) return null;
  const a = BY_ID[run.agent] || MAP_AGENTS[0];
  const b = run.body, d = run.dated;
  const working = run.status === "running";
  // "run forecast Chitradurga Central PS" -> a button; an agent the map does not carry is left out
  const next = (b?.next || []).map((t) => /^run (geo|forecast|pattern)\b\s*(.*)$/i.exec(t)).filter(Boolean)
    .map((m) => ({ id: m[1].toLowerCase(), arg: m[2].trim() })).filter((n) => n.id !== run.agent || n.arg);
  const looksAhead = run.agent !== "pattern" && b?.status === "ok" && run.date !== todayIso;

  return (
    <section className={`mxr${working ? " is-working" : ""}`} aria-live="polite" aria-busy={working}>
      <header>
        <span className="mxr-face"><Face agent={a} size={52} /></span>
        <div>
          <b>{a.name}{run.station ? <i> · {run.station}</i> : null}</b>
          <span>{run.district} · {nice(run.date)} · {run.crimeLabel || "All crimes"}</span>
        </div>
        <button type="button" onClick={onClose} aria-label="Close agent result" title="Close">&times;</button>
      </header>

      {run.zone && (
        <div className="mxr-rec">
          <h6>On record to this date <em>Known</em></h6>
          {d === "pending" && <p className="mxr-dim">Counting the 30 days to {nice(run.date)}…</p>}
          {d && d !== "pending" && (
            <p>
              <b>{d.observed}</b> {d.observed === 1 ? "case" : "cases"} in the 30 days to {nice(d.end || run.date)}
              {d.observed > 0 && d.of > 1 ? <>, {ordinal(d.rank)} of {d.of} areas</> : null}.{" "}
              {d.hot ? <span className="hot">A confirmed hotspot on this date.</span> : "Not a statistical hotspot on this date."}
            </p>
          )}
          {d === null && <p className="mxr-dim">The dated count could not be read.</p>}
        </div>
      )}

      <div className="mxr-ans">
        {working && <p className="mxr-work">{a.name} is working on {run.district}<span className="mxr-dots" aria-hidden="true" /></p>}
        {!working && b && (
          <>
            <h6>
              {a.name}'s answer
              {b.status === "refused" || b.status === "error"
                ? <em className="no">Not run</em>
                : <em className={`c-${b.evidence_class || "U"}`}>{CLASS_WORD[b.evidence_class] || "Unknown"}</em>}
            </h6>
            <p className="mxr-line">{b.bottom_line}</p>
            {b.context ? <p className="mxr-dim">{b.context}</p> : null}
            {b.evidence?.length > 0 && <ol>{b.evidence.slice(0, 5).map((t, i) => <li key={i}>{String(t).replace(/^\d+\.\s*/, "")}</li>)}</ol>}
            {looksAhead && <p className="mxr-note">A forecast looks ahead from the latest record, so it does not move with the calendar. The recorded count above does.</p>}
            {b.limits?.length > 0 && <p className="mxr-note">{b.limits.slice(0, 2).join(" ")}</p>}
          </>
        )}
      </div>

      {!working && (next.length > 0 || stale) && (
        <footer>
          {stale && <button type="button" className="again" onClick={onRerun}>Run again for the new selection</button>}
          {next.map((n, i) => (
            <button type="button" key={i} onClick={() => onRun(n.id, n.arg)}>
              {BY_ID[n.id].name}{n.arg ? `: ${n.arg}` : ""}
            </button>
          ))}
        </footer>
      )}
    </section>
  );
}
