"use client";
// Geo intel: the links between districts, in plain words.
//
// A link exists because the SAME accused id is named in FIRs registered in two districts.
// Every figure here is a count from the FIR record (the corridor compiler, or the year's
// rows when the server has none). Nothing on this page is a model's guess, and nothing is
// shown that the count does not support: no "route", no "gang", no recommended operation.
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
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
// Days from the most recent FIR to today. The server's recency_days counts back from the
// newest row in its data, which can be a future-dated demo row, so it is not used here.
const daysAgo = (iso) => {
  if (!day(iso)) return null;
  return Math.floor((Date.now() - new Date(String(iso).length <= 10 ? `${iso}T00:00:00` : iso).getTime()) / 86400000);
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
        last: day(c.last_date), ago: daysAgo(c.last_date),
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

// How fresh a link is, from the days since its most recent FIR.
const fresh = (ago) => (ago == null || ago < 0 ? null : ago <= 90 ? "active" : ago <= 365 ? "recent" : "older");
const FRESH = {
  active: ["Active", "ಸಕ್ರಿಯ", "An FIR on this link in the last 90 days", "ಕಳೆದ 90 ದಿನಗಳಲ್ಲಿ ಈ ಸಂಪರ್ಕದಲ್ಲಿ FIR"],
  recent: ["This year", "ಈ ವರ್ಷ", "Most recent FIR 3 to 12 months ago", "ಇತ್ತೀಚಿನ FIR 3 ರಿಂದ 12 ತಿಂಗಳ ಹಿಂದೆ"],
  older: ["Older", "ಹಳೆಯದು", "No FIR on this link for over a year", "ಒಂದು ವರ್ಷಕ್ಕೂ ಹೆಚ್ಚು ಕಾಲ FIR ಇಲ್ಲ"],
};

export default function GeoIntelDashboard({ corridors, flows, year, notes = [], dateLabel, onClose }) {
  const { lang } = useLang();
  const router = useRouter();
  const kn = lang === "kn";
  const L = (en, kan) => (kn ? kan : en);
  const [open, setOpen] = useState(null);
  const [all, setAll] = useState(false);
  const [district, setDistrict] = useState("");
  const [sort, setSort] = useState("strength");
  const [copied, setCopied] = useState(null);
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
    return [...m.values()].sort((p, q) => q.links - p.links || q.accused - p.accused);
  }, [links]);

  const districts = useMemo(() => hubs.map((h) => h.name).sort((p, q) => p.localeCompare(q)), [hubs]);
  const active = links.filter((l) => fresh(l.ago) === "active").length;
  const newest = links.filter((l) => l.last && l.ago != null && l.ago >= 0).sort((p, q) => p.ago - q.ago)[0];

  const list = useMemo(() => {
    const xs = district ? links.filter((l) => l.a === district || l.b === district) : links.slice();
    if (sort === "recent") xs.sort((p, q) => (p.ago ?? 1e9) - (q.ago ?? 1e9) || q.n - p.n);
    else xs.sort((p, q) => q.n - p.n || (q.firs || 0) - (p.firs || 0));
    return xs;
  }, [links, district, sort]);
  const shown = all ? list : list.slice(0, 6);

  // With a district picked, the other end of each link is the district to contact.
  const other = (l) => (!district ? null : l.b === district ? l.a : l.b);
  const pick = (d) => { setDistrict(d); setOpen(null); setAll(false); };
  const copy = (id) => {
    try { navigator.clipboard?.writeText(id); } catch {}
    setCopied(id); setTimeout(() => setCopied((c) => (c === id ? null : c)), 1400);
  };
  // S-ids are suspect records Search can open; other accused ids are only in the corridor data.
  const searchable = (id) => /^S\d+$/i.test(id || "");
  const them = (n) => (n === 1 ? L("this accused", "ಈ ಆರೋಪಿ") : L(`these ${n} accused`, `ಈ ${n} ಆರೋಪಿಗಳು`));

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
          {L("The same accused named in FIRs in two districts. Use it to find which other district already holds cases on a person you are investigating.",
             "ಒಂದೇ ಆರೋಪಿಯನ್ನು ಎರಡು ಜಿಲ್ಲೆಗಳ FIR ಗಳಲ್ಲಿ ಹೆಸರಿಸಲಾಗಿದೆ. ನೀವು ತನಿಖೆ ಮಾಡುತ್ತಿರುವ ವ್ಯಕ್ತಿಯ ಪ್ರಕರಣಗಳು ಯಾವ ಇನ್ನೊಂದು ಜಿಲ್ಲೆಯಲ್ಲಿವೆ ಎಂದು ತಿಳಿಯಲು ಇದನ್ನು ಬಳಸಿ.")}
        </p>
        <p className="gi-caveat">
          {L("A link is a match in the record. It does not by itself show travel, a route or a gang.",
             "ಸಂಪರ್ಕ ದಾಖಲೆಯಲ್ಲಿನ ಹೊಂದಾಣಿಕೆ ಮಾತ್ರ. ಅದು ಸ್ವತಃ ಪ್ರಯಾಣ, ಮಾರ್ಗ ಅಥವಾ ಗ್ಯಾಂಗ್ ಅನ್ನು ತೋರಿಸುವುದಿಲ್ಲ.")}
        </p>

        {links.length === 0 ? (
          <p className="gi-none">{L("No accused is named in more than one district in the records now loaded.", "ಲೋಡ್ ಆಗಿರುವ ದಾಖಲೆಗಳಲ್ಲಿ ಯಾವುದೇ ಆರೋಪಿ ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು ಜಿಲ್ಲೆಯಲ್ಲಿ ಹೆಸರಿಸಲಾಗಿಲ್ಲ.")}</p>
        ) : (
          <>
            <div className="gi-stats">
              <div><b>{links.length}</b><span>{L(links.length === 1 ? "link between districts" : "links between districts", "ಜಿಲ್ಲೆಗಳ ನಡುವಿನ ಸಂಪರ್ಕಗಳು")}</span></div>
              <div><b>{districts.length}</b><span>{L("districts involved", "ಒಳಗೊಂಡ ಜಿಲ್ಲೆಗಳು")}</span></div>
              {fromServer && <div><b className={active ? "hot" : ""}>{active}</b><span>{L("active, an FIR in the last 90 days", "ಸಕ್ರಿಯ, ಕಳೆದ 90 ದಿನಗಳಲ್ಲಿ FIR")}</span></div>}
              {newest?.last && <div><b className="d">{newest.last}</b><span>{L(`latest FIR, ${newest.a} and ${newest.b}`, `ಇತ್ತೀಚಿನ FIR, ${newest.a} ಮತ್ತು ${newest.b}`)}</span></div>}
            </div>

            <div className="gi-tools">
              <label className="gi-pick">
                <span>{L("My district", "ನನ್ನ ಜಿಲ್ಲೆ")}</span>
                <select value={district} onChange={(e) => pick(e.target.value)}>
                  <option value="">{L(`All districts, ${links.length} links`, `ಎಲ್ಲ ಜಿಲ್ಲೆಗಳು, ${links.length}`)}</option>
                  {districts.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </label>
              {fromServer && (
                <div className="gi-sort" role="group" aria-label={L("Sort links", "ವಿಂಗಡಿಸಿ")}>
                  <button type="button" className={sort === "strength" ? "on" : ""} aria-pressed={sort === "strength"} onClick={() => setSort("strength")}>{L("Most accused", "ಹೆಚ್ಚು ಆರೋಪಿಗಳು")}</button>
                  <button type="button" className={sort === "recent" ? "on" : ""} aria-pressed={sort === "recent"} onClick={() => setSort("recent")}>{L("Latest FIR", "ಇತ್ತೀಚಿನ FIR")}</button>
                </div>
              )}
            </div>

            {district && (
              <p className="gi-scope">
                <span>{list.length
                  ? L(`${district} shares accused with ${list.length} ${list.length === 1 ? "district" : "districts"}. Open one to see who, and whom to contact.`,
                      `${district} ${list.length} ಜಿಲ್ಲೆಗಳೊಂದಿಗೆ ಆರೋಪಿಗಳನ್ನು ಹಂಚಿಕೊಂಡಿದೆ. ಯಾರು ಮತ್ತು ಯಾರನ್ನು ಸಂಪರ್ಕಿಸಬೇಕು ಎಂದು ನೋಡಲು ಒಂದನ್ನು ತೆರೆಯಿರಿ.`)
                  : L(`No link touches ${district}.`, `${district} ಗೆ ಯಾವುದೇ ಸಂಪರ್ಕವಿಲ್ಲ.`)}</span>
                <button type="button" onClick={() => pick("")}>{L("Show all", "ಎಲ್ಲ ತೋರಿಸಿ")}</button>
              </p>
            )}

            <ul className="gi-list">
              {shown.map((l) => {
                const on = open === l.key;
                const f = fresh(l.ago);
                const o = other(l);
                const facts = [l.head && L(`crime head: ${l.head}`, `ಅಪರಾಧ ಶೀರ್ಷಿಕೆ: ${l.head}`), l.last && L(`last FIR ${l.last}`, `ಕೊನೆಯ FIR ${l.last}`), l.also && L(`also in ${l.also.district}`, `${l.also.district} ನಲ್ಲೂ`),
                               l.year && L(`counted for ${l.year}`, `${l.year} ಕ್ಕೆ ಎಣಿಸಲಾಗಿದೆ`)].filter(Boolean);
                return (
                  <li key={l.key} className={on ? "on" : ""}>
                    <button type="button" className="gi-row" aria-expanded={on} onClick={() => setOpen(on ? null : l.key)}>
                      <span className="t">
                        {o ? <>{o}<em>{L(`with ${district}`, `${district} ಜೊತೆ`)}</em></> : <>{l.a}<i aria-hidden="true">↔</i>{l.b}</>}
                        {f && <span className={`gi-tag ${f}`} title={L(FRESH[f][2], FRESH[f][3])}>{L(FRESH[f][0], FRESH[f][1])}</span>}
                      </span>
                      <span className="n">
                        <b>{l.n}</b> {L("accused", "ಆರೋಪಿ")}
                        {l.firs != null && <><span className="sep">·</span><b>{l.firs}</b> {kn || l.firs === 1 ? "FIR" : "FIRs"}</>}
                      </span>
                      {facts.length > 0 && <span className="s">{facts.join(" · ")}</span>}
                      <span className="chev" aria-hidden="true">{on ? "−" : "+"}</span>
                    </button>
                    {on && (
                      <div className="gi-more">
                        <div className="gi-todo">
                          <span>{L("Next step", "ಮುಂದಿನ ಹೆಜ್ಜೆ")}</span>
                          <p>{o
                            ? L(`Ask ${o} for its FIRs naming ${them(l.n)}, and share yours.`, `${them(l.n)} ಹೆಸರಿಸುವ FIR ಗಳನ್ನು ${o} ನಿಂದ ಕೇಳಿ, ನಿಮ್ಮದನ್ನೂ ಹಂಚಿಕೊಳ್ಳಿ.`)
                            : L(`${l.a} and ${l.b} both hold FIRs on ${them(l.n)}. The investigating officers on each side should compare them.`,
                                `${l.a} ಮತ್ತು ${l.b} ಎರಡರಲ್ಲೂ ${them(l.n)} FIR ಗಳಿವೆ. ಎರಡೂ ಕಡೆಯ ತನಿಖಾಧಿಕಾರಿಗಳು ಅವನ್ನು ಹೋಲಿಸಬೇಕು.`)}
                            {l.also && L(` ${l.also.count} of them ${l.also.count === 1 ? "is" : "are"} also named in ${l.also.district}; include it.`,
                                         ` ಅವರಲ್ಲಿ ${l.also.count} ಜನರನ್ನು ${l.also.district} ನಲ್ಲೂ ಹೆಸರಿಸಲಾಗಿದೆ; ಅದನ್ನೂ ಸೇರಿಸಿ.`)}</p>
                        </div>
                        <dl>
                          <div><dt>{L("Accused named in both districts", "ಎರಡೂ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಸರಿಸಲಾದ ಆರೋಪಿಗಳು")}</dt><dd>{l.n}</dd></div>
                          {l.firs != null && <div><dt>{L("FIRs naming them, both districts together", "ಎರಡೂ ಕಡೆ ಅವರನ್ನು ಹೆಸರಿಸಿದ FIR ಗಳು")}</dt><dd>{l.firs}</dd></div>}
                          {l.head && <div><dt>{L("Most common crime head", "ಹೆಚ್ಚಾಗಿ ಬರೆದ ಅಪರಾಧ ಶೀರ್ಷಿಕೆ")}</dt><dd>{l.head}</dd></div>}
                          {l.last && <div><dt>{L("Most recent FIR", "ಇತ್ತೀಚಿನ FIR")}</dt><dd>{l.last}{f && <small>{L(FRESH[f][2], FRESH[f][3])}</small>}</dd></div>}
                          {fromServer && <div><dt>{L("Also named in a third district", "ಮೂರನೇ ಜಿಲ್ಲೆಯಲ್ಲೂ ಹೆಸರಿಸಲಾಗಿದೆ")}</dt>
                            <dd>{l.also ? L(`${l.also.count} of ${l.n}, in ${l.also.district}`, `${l.n} ರಲ್ಲಿ ${l.also.count}, ${l.also.district} ನಲ್ಲಿ`) : L("None of them", "ಯಾರೂ ಇಲ್ಲ")}</dd></div>}
                        </dl>
                        {l.who.length > 0 && (
                          <>
                            <h5>{l.n > l.who.length ? L(`Accused with the most FIRs on this link, ${l.who.length} of ${l.n}`, `ಈ ಸಂಪರ್ಕದಲ್ಲಿ ಹೆಚ್ಚು FIR ಇರುವ ಆರೋಪಿಗಳು, ${l.n} ರಲ್ಲಿ ${l.who.length}`) : L("Accused on this link", "ಈ ಸಂಪರ್ಕದ ಆರೋಪಿಗಳು")}</h5>
                            <ul className="gi-who">
                              {l.who.map((p) => (
                                <li key={p.id}>
                                  <div><code>{p.id}</code>{p.name && <span>{p.name}<em>{L("stand-in name", "ಬದಲಿ ಹೆಸರು")}</em></span>}</div>
                                  {searchable(p.id)
                                    ? <button type="button" onClick={() => router.push(`/search?q=${encodeURIComponent(p.id)}`)}>{L("Open in Search", "ಹುಡುಕಾಟದಲ್ಲಿ ತೆರೆಯಿರಿ")}</button>
                                    : <button type="button" onClick={() => copy(p.id)}>{copied === p.id ? L("Copied", "ನಕಲಿಸಲಾಗಿದೆ") : L("Copy id", "ಐಡಿ ನಕಲಿಸಿ")}</button>}
                                </li>
                              ))}
                            </ul>
                            <p className="gi-next">{L("The record holds ids, not names; the names are made by the system to tell ids apart. Quote the id when you contact the other district.",
                                                      "ದಾಖಲೆಯಲ್ಲಿ ಐಡಿಗಳಿವೆ, ಹೆಸರುಗಳಲ್ಲ; ಐಡಿ ಗುರುತಿಸಲು ಹೆಸರುಗಳನ್ನು ವ್ಯವಸ್ಥೆ ಮಾಡುತ್ತದೆ. ಇನ್ನೊಂದು ಜಿಲ್ಲೆಯನ್ನು ಸಂಪರ್ಕಿಸುವಾಗ ಐಡಿ ತಿಳಿಸಿ.")}</p>
                          </>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
            {list.length > 6 && (
              <button type="button" className="gi-all" onClick={() => setAll((v) => !v)}>{all ? L("Show the first 6", "ಮೊದಲ 6 ತೋರಿಸಿ") : L(`Show all ${list.length} links`, `ಎಲ್ಲ ${list.length} ಸಂಪರ್ಕಗಳನ್ನು ತೋರಿಸಿ`)}</button>
            )}

            {!district && hubs.some((h) => h.links > 1) && (
              <>
                <h4>{L("Districts on the most links", "ಹೆಚ್ಚು ಸಂಪರ್ಕಗಳಿರುವ ಜಿಲ್ಲೆಗಳು")}</h4>
                <ul className="gi-hubs">
                  {hubs.filter((h) => h.links > 1).slice(0, 5).map((h) => (
                    <li key={h.name}>
                      <button type="button" onClick={() => pick(h.name)} title={L(`Show only the links of ${h.name}`, `${h.name} ಸಂಪರ್ಕಗಳನ್ನು ಮಾತ್ರ ತೋರಿಸಿ`)}>
                        <b>{h.name}</b><span>{h.links} {L("links", "ಸಂಪರ್ಕಗಳು")}</span>
                        <small>{L("with", "ಇವುಗಳೊಂದಿಗೆ:")} {h.with.slice(0, 5).join(", ")}{h.with.length > 5 ? L(` and ${h.with.length - 5} more`, ` ಮತ್ತು ಇನ್ನೂ ${h.with.length - 5}`) : ""}</small>
                      </button>
                    </li>
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
