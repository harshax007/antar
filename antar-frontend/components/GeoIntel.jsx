"use client";
// Geo intel: the links between districts, in plain words.
//
// A link exists because the SAME accused id is named in FIRs registered in two districts.
// Every figure here is a count from the FIR record (the corridor compiler, or the year's
// rows when the server has none). Nothing on this page is a model's guess, and nothing is
// shown that the count does not support: no "route", no "gang", no recommended operation.
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

// The register writes crime types in capitals ("KARNATAKA POLICE ACT 1963").
export function crimeName(t) {
  const w = String(t || "").replace(/_/g, " ").trim().split(/\s+/).filter(Boolean);
  const act = w.some((x) => /^act$/i.test(x));
  return w.map((x, i) => (i === 0 || act ? x.charAt(0).toUpperCase() + x.slice(1).toLowerCase() : x.toLowerCase())).join(" ");
}

// A date later than today is a row seeded for the demo, not a registered FIR: it is not shown.
const day = (iso) => {
  if (!iso) return null;
  const x = new Date(String(iso).length <= 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(x.getTime()) || x.getTime() > Date.now()) return null;
  return x.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
};
const people = (n) => `${n} accused`;

// One shape for both sources.
function asLinks(corridors, flows, year) {
  if (corridors?.length) return {
    fromServer: true,
    links: corridors.map((c) => {
      const nd = c.next_district_estimate;
      const n = c.weight || 0;
      return {
        key: c.corridor_id || `${c.src}-${c.dst}`, a: c.src, b: c.dst, n,
        firs: c.fir_count, head: c.primary_crime && c.primary_crime !== "mixed" ? crimeName(c.primary_crime) : null,
        last: day(c.last_date), ago: typeof c.recency_days === "number" ? c.recency_days : null,
        also: nd?.district ? { district: nd.district, count: Math.max(1, Math.round((nd.probability || 0) * n)) } : null,
        who: (c.involved_entities || []).map((e) => ({ id: e.id, name: e.name })),
      };
    }),
    compiled: corridors[0]?.provenance?.compiled_at || null,
  };
  return {
    fromServer: false,
    links: (flows || []).map((f) => ({ key: `${f.a}-${f.b}`, a: f.a, b: f.b, n: f.n, firs: null, head: null, last: null, ago: null, also: null,
                                       who: f.acc ? [{ id: f.acc, name: null }] : [], year })),
    compiled: null,
  };
}

const WORDS = [
  ["FIR", "First Information Report: the record a police station opens when a crime is reported."],
  ["Accused", "A person named in an FIR as having committed the offence. Named is not the same as convicted."],
  ["Link", "Two districts are linked when the same accused is named in FIRs registered in both."],
  ["Stand-in name", "The record holds accused ids, not names. The names shown are made by the system so an id is easier to tell apart. Search by the id."],
  ["Hotspot", "An area with more cases than its neighbours, by a margin unlikely to be chance."],
  ["Above its usual level", "More cases of one crime type than that area normally records in the same period."],
];

export default function GeoIntelDashboard({ corridors, flows, year, notes = [], dateLabel, onClose }) {
  const [open, setOpen] = useState(null);
  const [all, setAll] = useState(false);
  const { links, fromServer, compiled } = useMemo(() => asLinks(corridors, flows, year), [corridors, flows, year]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // which districts sit on the most links
  const hubs = useMemo(() => {
    const m = new Map();
    links.forEach((l) => [[l.a, l.b], [l.b, l.a]].forEach(([x, y]) => {
      const e = m.get(x) || m.set(x, { name: x, links: 0, accused: 0, with: [] }).get(x);
      e.links += 1; e.accused += l.n; e.with.push(y);
    }));
    return [...m.values()].filter((e) => e.links > 1).sort((p, q) => q.links - p.links || q.accused - p.accused).slice(0, 5);
  }, [links]);

  const top = links[0];
  const newest = links.filter((l) => l.last && l.ago != null).sort((p, q) => p.ago - q.ago)[0];
  const shown = all ? links : links.slice(0, 6);

  return createPortal(
    <div className="gi-back" role="dialog" aria-modal="true" aria-label="Geo intel: links between districts"
         onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <section className="gi">
        <header>
          <div>
            <span className="gi-eyebrow">Geo intel</span>
            <h3>Links between districts</h3>
          </div>
          <button type="button" className="gi-x" onClick={onClose} aria-label="Close this window" title="Close"><X size={18} /></button>
        </header>

        <p className="gi-lede">
          Two districts are linked when the same accused person is named in FIRs registered in both.
          A link is a connection in the record. By itself it does not show travel, a route or a gang;
          it tells an investigating officer which other district holds cases on the same person.
        </p>

        {links.length === 0 ? (
          <p className="gi-none">No accused is named in more than one district in the records now loaded.</p>
        ) : (
          <>
            <div className="gi-stats">
              <div><b>{links.length}</b><span>{links.length === 1 ? "link found" : "links found"}</span></div>
              <div><b>{top.a} and {top.b}</b><span>Strongest link, {people(top.n)} named in both</span></div>
              {newest?.last && <div><b>{newest.last}</b><span>Most recent FIR on any link ({newest.a} and {newest.b})</span></div>}
            </div>

            <h4>Links, strongest first</h4>
            <ul className="gi-list">
              {shown.map((l) => {
                const on = open === l.key;
                const facts = [l.firs != null && `${l.firs} ${l.firs === 1 ? "FIR" : "FIRs"}`,
                               l.last && `most recent ${l.last}`, l.year && `counted for ${l.year}`].filter(Boolean);
                return (
                  <li key={l.key} className={on ? "on" : ""}>
                    <button type="button" className="gi-row" aria-expanded={on} onClick={() => setOpen(on ? null : l.key)}>
                      <span className="t">{l.a} and {l.b}</span>
                      <span className="n">{people(l.n)} in both</span>
                      {facts.length > 0 && <span className="s">{facts.join(" · ")}</span>}
                    </button>
                    {on && (
                      <div className="gi-more">
                        <dl>
                          <div><dt>Accused named in both districts</dt><dd>{l.n}</dd></div>
                          {l.firs != null && <div><dt>FIRs these accused are named in, across the two</dt><dd>{l.firs}</dd></div>}
                          {l.head && <div><dt>Crime head written most often on these FIRs</dt><dd>{l.head}<small>As written in the record.</small></dd></div>}
                          {l.last && <div><dt>Most recent FIR</dt><dd>{l.last}</dd></div>}
                          <div><dt>Also named in a third district</dt>
                            <dd>{l.also ? <>{l.also.count} of {l.n} in {l.also.district}<small>Worth asking {l.also.district} as well. A count, not a forecast.</small></> : "None of them"}</dd></div>
                        </dl>
                        {l.who.length > 0 && (
                          <>
                            <h5>{l.n > l.who.length ? `Accused with the most FIRs on this link (${l.who.length} of ${l.n})` : "Accused on this link"}</h5>
                            <ul className="gi-who">
                              {l.who.map((p) => <li key={p.id}><code>{p.id}</code>{p.name && <span>{p.name}<em>stand-in name</em></span>}</li>)}
                            </ul>
                          </>
                        )}
                        <p className="gi-next">To follow one up, search the accused id in Search or Chat. It lists every FIR that names them.</p>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
            {links.length > 6 && (
              <button type="button" className="gi-all" onClick={() => setAll((v) => !v)}>{all ? "Show the first 6" : `Show all ${links.length} links`}</button>
            )}

            {hubs.length > 0 && (
              <>
                <h4>Districts on the most links</h4>
                <ul className="gi-hubs">
                  {hubs.map((h) => (
                    <li key={h.name}><b>{h.name}</b><span>{h.links} links</span><small>with {h.with.slice(0, 5).join(", ")}{h.with.length > 5 ? ` and ${h.with.length - 5} more` : ""}</small></li>
                  ))}
                </ul>
              </>
            )}
          </>
        )}

        {notes.length > 0 && (
          <>
            <h4>Also in this view{dateLabel ? `, ${dateLabel}` : ""}</h4>
            <ul className="gi-notes">
              {notes.map((n, i) => <li key={i}><p>{n.text}</p><small>From: {n.src}</small></li>)}
            </ul>
          </>
        )}

        <details className="gi-words">
          <summary>Words used here</summary>
          <dl>{WORDS.map(([w, m]) => <div key={w}><dt>{w}</dt><dd>{m}</dd></div>)}</dl>
        </details>

        <footer>
          {fromServer
            ? "Counted from the FIR record by matching accused ids across districts. No model is involved, and a link is not evidence of an offence."
            : `Counted in this browser from the ${year} FIR rows now loaded, by matching accused ids across districts. The server's fuller list was not available.`}
          {compiled && ` Compiled ${new Date(compiled).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}.`}
        </footer>
      </section>
    </div>,
    document.body
  );
}
