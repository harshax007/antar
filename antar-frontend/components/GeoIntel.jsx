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
import { useLang } from "@/components/Providers";
import { MaterialBackdrop, MaterialPanel } from "@/components/ui/MaterialPanel";

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
const people = (n, kn) => (kn ? `${n} ಆರೋಪಿಗಳು` : `${n} accused`);

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

const WORDS = {
  en: [
    ["FIR", "First Information Report: the record a police station opens when a crime is reported."],
    ["Accused", "A person named in an FIR as having committed the offence. Named is not the same as convicted."],
    ["Link", "Two districts are linked when the same accused is named in FIRs registered in both."],
    ["Stand-in name", "The record holds accused ids, not names. The names shown are made by the system so an id is easier to tell apart. Search by the id."],
    ["Hotspot", "An area with more cases than its neighbours, by a margin unlikely to be chance."],
    ["Above its usual level", "More cases of one crime type than that area normally records in the same period."],
  ],
  kn: [
    ["FIR", "ಪ್ರಥಮ ಮಾಹಿತಿ ವರದಿ: ಅಪರಾಧ ವರದಿಯಾದಾಗ ಪೊಲೀಸ್ ಠಾಣೆ ತೆರೆಯುವ ದಾಖಲೆ."],
    ["ಆರೋಪಿ", "ಅಪರಾಧ ಮಾಡಿದವರೆಂದು FIR ನಲ್ಲಿ ಹೆಸರಿಸಲಾದ ವ್ಯಕ್ತಿ. ಹೆಸರಿಸುವುದು ಶಿಕ್ಷೆಗೊಳಗಾಗುವುದಕ್ಕೆ ಸಮವಲ್ಲ."],
    ["ಸಂಪರ್ಕ", "ಒಂದೇ ಆರೋಪಿಯನ್ನು ಎರಡೂ ಜಿಲ್ಲೆಗಳ FIR ಗಳಲ್ಲಿ ಹೆಸರಿಸಿದಾಗ ಆ ಜಿಲ್ಲೆಗಳು ಸಂಪರ್ಕಿತ."],
    ["ಬದಲಿ ಹೆಸರು", "ದಾಖಲೆಯಲ್ಲಿ ಆರೋಪಿ ಐಡಿಗಳಿವೆ, ಹೆಸರುಗಳಲ್ಲ. ತೋರಿಸಿದ ಹೆಸರುಗಳನ್ನು ಐಡಿ ಗುರುತಿಸಲು ಸುಲಭವಾಗಲು ವ್ಯವಸ್ಥೆ ಮಾಡುತ್ತದೆ. ಐಡಿಯಿಂದ ಹುಡುಕಿ."],
    ["ಹಾಟ್‌ಸ್ಪಾಟ್", "ಆಕಸ್ಮಿಕವಲ್ಲದ ಅಂತರದಿಂದ ನೆರೆಯವರಿಗಿಂತ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳಿರುವ ಪ್ರದೇಶ."],
    ["ಸಾಮಾನ್ಯ ಮಟ್ಟಕ್ಕಿಂತ ಹೆಚ್ಚು", "ಅದೇ ಅವಧಿಯಲ್ಲಿ ಆ ಪ್ರದೇಶ ಸಾಮಾನ್ಯವಾಗಿ ದಾಖಲಿಸುವುದಕ್ಕಿಂತ ಒಂದು ಅಪರಾಧ ಪ್ರಕಾರದ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳು."],
  ],
};

export default function GeoIntelDashboard({ corridors, flows, year, notes = [], dateLabel, onClose }) {
  const { lang } = useLang();
  const kn = lang === "kn";
  const L = (en, kan) => (kn ? kan : en);
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
    <MaterialBackdrop className="gi-back" role="dialog" aria-modal="true" aria-label={L("Geo intel: links between districts", "ಜಿಲ್ಲೆಗಳ ನಡುವಿನ ಸಂಪರ್ಕಗಳು")}
         onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <MaterialPanel as="section" className="gi">
        <header>
          <div>
            <span className="gi-eyebrow">{L("Geo intel", "ಭೌಗೋಳಿಕ ಮಾಹಿತಿ")}</span>
            <h3>{L("Links between districts", "ಜಿಲ್ಲೆಗಳ ನಡುವಿನ ಸಂಪರ್ಕಗಳು")}</h3>
          </div>
          <button type="button" className="gi-x" onClick={onClose} aria-label={L("Close this window", "ಮುಚ್ಚಿ")} title={L("Close", "ಮುಚ್ಚಿ")}><X size={18} /></button>
        </header>

        <p className="gi-lede">
          {L("Two districts are linked when the same accused person is named in FIRs registered in both. A link is a connection in the record. By itself it does not show travel, a route or a gang; it tells an investigating officer which other district holds cases on the same person.",
             "ಒಂದೇ ಆರೋಪಿಯನ್ನು ಎರಡೂ ಜಿಲ್ಲೆಗಳ FIR ಗಳಲ್ಲಿ ಹೆಸರಿಸಿದಾಗ ಆ ಜಿಲ್ಲೆಗಳು ಸಂಪರ್ಕಿತ. ಸಂಪರ್ಕ ದಾಖಲೆಯಲ್ಲಿನ ಸಂಬಂಧ ಮಾತ್ರ; ಅದು ಸ್ವತಃ ಪ್ರಯಾಣ, ಮಾರ್ಗ ಅಥವಾ ಗ್ಯಾಂಗ್ ಅನ್ನು ತೋರಿಸುವುದಿಲ್ಲ. ಅದೇ ವ್ಯಕ್ತಿಯ ಪ್ರಕರಣಗಳು ಯಾವ ಇನ್ನೊಂದು ಜಿಲ್ಲೆಯಲ್ಲಿವೆ ಎಂದು ತನಿಖಾಧಿಕಾರಿಗೆ ತಿಳಿಸುತ್ತದೆ.")}
        </p>

        {links.length === 0 ? (
          <p className="gi-none">{L("No accused is named in more than one district in the records now loaded.", "ಲೋಡ್ ಆಗಿರುವ ದಾಖಲೆಗಳಲ್ಲಿ ಯಾವುದೇ ಆರೋಪಿ ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು ಜಿಲ್ಲೆಯಲ್ಲಿ ಹೆಸರಿಸಲಾಗಿಲ್ಲ.")}</p>
        ) : (
          <>
            <div className="gi-stats">
              <div><b>{links.length}</b><span>{L(links.length === 1 ? "link found" : "links found", "ಸಂಪರ್ಕಗಳು ಸಿಕ್ಕಿವೆ")}</span></div>
              <div><b>{top.a} {L("and", "ಮತ್ತು")} {top.b}</b><span>{L(`Strongest link, ${people(top.n)} named in both`, `ಬಲವಾದ ಸಂಪರ್ಕ, ಎರಡರಲ್ಲೂ ${people(top.n, true)}`)}</span></div>
              {newest?.last && <div><b>{newest.last}</b><span>{L(`Most recent FIR on any link (${newest.a} and ${newest.b})`, `ಯಾವುದೇ ಸಂಪರ್ಕದ ಇತ್ತೀಚಿನ FIR (${newest.a} ಮತ್ತು ${newest.b})`)}</span></div>}
            </div>

            <h4>{L("Links, strongest first", "ಸಂಪರ್ಕಗಳು, ಬಲವಾದದ್ದು ಮೊದಲು")}</h4>
            <ul className="gi-list">
              {shown.map((l) => {
                const on = open === l.key;
                const facts = [l.firs != null && `${l.firs} ${kn || l.firs === 1 ? "FIR" : "FIRs"}`,
                               l.last && L(`most recent ${l.last}`, `ಇತ್ತೀಚಿನದು ${l.last}`), l.year && L(`counted for ${l.year}`, `${l.year} ಕ್ಕೆ ಎಣಿಸಲಾಗಿದೆ`)].filter(Boolean);
                return (
                  <li key={l.key} className={on ? "on" : ""}>
                    <button type="button" className="gi-row" aria-expanded={on} onClick={() => setOpen(on ? null : l.key)}>
                      <span className="t">{l.a} {L("and", "ಮತ್ತು")} {l.b}</span>
                      <span className="n">{L(`${people(l.n)} in both`, `ಎರಡರಲ್ಲೂ ${people(l.n, true)}`)}</span>
                      {facts.length > 0 && <span className="s">{facts.join(" · ")}</span>}
                    </button>
                    {on && (
                      <div className="gi-more">
                        <dl>
                          <div><dt>{L("Accused named in both districts", "ಎರಡೂ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಸರಿಸಲಾದ ಆರೋಪಿಗಳು")}</dt><dd>{l.n}</dd></div>
                          {l.firs != null && <div><dt>{L("FIRs these accused are named in, across the two", "ಎರಡೂ ಕಡೆ ಈ ಆರೋಪಿಗಳನ್ನು ಹೆಸರಿಸಿದ FIR ಗಳು")}</dt><dd>{l.firs}</dd></div>}
                          {l.head && <div><dt>{L("Crime head written most often on these FIRs", "ಈ FIR ಗಳಲ್ಲಿ ಹೆಚ್ಚು ಬರೆದ ಅಪರಾಧ ಶೀರ್ಷಿಕೆ")}</dt><dd>{l.head}<small>{L("As written in the record.", "ದಾಖಲೆಯಲ್ಲಿ ಬರೆದಂತೆ.")}</small></dd></div>}
                          {l.last && <div><dt>{L("Most recent FIR", "ಇತ್ತೀಚಿನ FIR")}</dt><dd>{l.last}</dd></div>}
                          <div><dt>{L("Also named in a third district", "ಮೂರನೇ ಜಿಲ್ಲೆಯಲ್ಲೂ ಹೆಸರಿಸಲಾಗಿದೆ")}</dt>
                            <dd>{l.also ? <>{L(`${l.also.count} of ${l.n} in ${l.also.district}`, `${l.n} ರಲ್ಲಿ ${l.also.count}, ${l.also.district} ನಲ್ಲಿ`)}<small>{L(`Worth asking ${l.also.district} as well. A count, not a forecast.`, `${l.also.district} ಅನ್ನೂ ಕೇಳುವುದು ಉಪಯುಕ್ತ. ಇದು ಎಣಿಕೆ, ಮುನ್ಸೂಚನೆಯಲ್ಲ.`)}</small></> : L("None of them", "ಯಾರೂ ಇಲ್ಲ")}</dd></div>
                        </dl>
                        {l.who.length > 0 && (
                          <>
                            <h5>{l.n > l.who.length ? L(`Accused with the most FIRs on this link (${l.who.length} of ${l.n})`, `ಈ ಸಂಪರ್ಕದಲ್ಲಿ ಹೆಚ್ಚು FIR ಇರುವ ಆರೋಪಿಗಳು (${l.n} ರಲ್ಲಿ ${l.who.length})`) : L("Accused on this link", "ಈ ಸಂಪರ್ಕದ ಆರೋಪಿಗಳು")}</h5>
                            <ul className="gi-who">
                              {l.who.map((p) => <li key={p.id}><code>{p.id}</code>{p.name && <span>{p.name}<em>{L("stand-in name", "ಬದಲಿ ಹೆಸರು")}</em></span>}</li>)}
                            </ul>
                          </>
                        )}
                        <p className="gi-next">{L("To follow one up, search the accused id in Search or Chat. It lists every FIR that names them.", "ಮುಂದುವರಿಸಲು, ಆರೋಪಿ ಐಡಿಯನ್ನು ಹುಡುಕಾಟ ಅಥವಾ ಚಾಟ್‌ನಲ್ಲಿ ಹುಡುಕಿ. ಅವರನ್ನು ಹೆಸರಿಸುವ ಎಲ್ಲ FIR ಗಳನ್ನು ಅದು ತೋರಿಸುತ್ತದೆ.")}</p>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
            {links.length > 6 && (
              <button type="button" className="gi-all" onClick={() => setAll((v) => !v)}>{all ? L("Show the first 6", "ಮೊದಲ 6 ತೋರಿಸಿ") : L(`Show all ${links.length} links`, `ಎಲ್ಲ ${links.length} ಸಂಪರ್ಕಗಳನ್ನು ತೋರಿಸಿ`)}</button>
            )}

            {hubs.length > 0 && (
              <>
                <h4>{L("Districts on the most links", "ಹೆಚ್ಚು ಸಂಪರ್ಕಗಳಿರುವ ಜಿಲ್ಲೆಗಳು")}</h4>
                <ul className="gi-hubs">
                  {hubs.map((h) => (
                    <li key={h.name}><b>{h.name}</b><span>{h.links} {L("links", "ಸಂಪರ್ಕಗಳು")}</span><small>{L("with", "ಇವುಗಳೊಂದಿಗೆ:")} {h.with.slice(0, 5).join(", ")}{h.with.length > 5 ? L(` and ${h.with.length - 5} more`, ` ಮತ್ತು ಇನ್ನೂ ${h.with.length - 5}`) : ""}</small></li>
                  ))}
                </ul>
              </>
            )}
          </>
        )}

        {notes.length > 0 && (
          <>
            <h4>{L("Also in this view", "ಈ ನೋಟದಲ್ಲಿ ಇನ್ನೂ")}{dateLabel ? `, ${dateLabel}` : ""}</h4>
            <ul className="gi-notes">
              {notes.map((n, i) => <li key={i}><p>{n.text}</p><small>{L("From:", "ಮೂಲ:")} {n.src}</small></li>)}
            </ul>
          </>
        )}

        <details className="gi-words">
          <summary>{L("Words used here", "ಇಲ್ಲಿ ಬಳಸಿದ ಪದಗಳು")}</summary>
          <dl>{WORDS[kn ? "kn" : "en"].map(([w, m]) => <div key={w}><dt>{w}</dt><dd>{m}</dd></div>)}</dl>
        </details>

        <footer>
          {fromServer
            ? L("Counted from the FIR record by matching accused ids across districts. No model is involved, and a link is not evidence of an offence.",
                "ಜಿಲ್ಲೆಗಳಾದ್ಯಂತ ಆರೋಪಿ ಐಡಿಗಳನ್ನು ಹೊಂದಿಸಿ FIR ದಾಖಲೆಯಿಂದ ಎಣಿಸಲಾಗಿದೆ. ಯಾವುದೇ ಮಾದರಿ ಬಳಸಿಲ್ಲ; ಸಂಪರ್ಕ ಅಪರಾಧದ ಸಾಕ್ಷ್ಯವಲ್ಲ.")
            : L(`Counted in this browser from the ${year} FIR rows now loaded, by matching accused ids across districts. The server's fuller list was not available.`,
                `ಲೋಡ್ ಆಗಿರುವ ${year} ರ FIR ಸಾಲುಗಳಿಂದ ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಎಣಿಸಲಾಗಿದೆ. ಸರ್ವರ್‌ನ ಪೂರ್ಣ ಪಟ್ಟಿ ಲಭ್ಯವಿರಲಿಲ್ಲ.`)}
          {compiled && ` ${L("Compiled", "ಸಂಕಲಿಸಿದ್ದು")} ${new Date(compiled).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}.`}
        </footer>
      </MaterialPanel>
    </MaterialBackdrop>,
    document.body
  );
}
