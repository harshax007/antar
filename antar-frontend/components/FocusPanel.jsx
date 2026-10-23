"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { SPRING } from "@/components/ui/MaterialPanel";
import "./FocusPanel.css";

// The Brain's focus card: one linked group of FIRs, read the way a case officer reads a
// file. First the brief (what this group is, why it matters, what to check next), then
// the figures, then each detail in a section that opens on demand. Everything is counted
// from the group the graph focused - nothing is generated or fetched, so the card can
// never disagree with the picture beside it.

// "CYBER CRIME" -> "Cyber crime": the register's capitals, read as a phrase
const nice = (t) => { const w = String(t || "").replace(/_/g, " ").trim(); return w === w.toUpperCase() ? w.charAt(0) + w.slice(1).toLowerCase() : w; };
const plural = (n, one, many = `${one}s`) => `${n.toLocaleString()} ${n === 1 ? one : many}`;
function listJoin(a) {
  const x = a.filter(Boolean);
  return x.length <= 1 ? (x[0] || "") : `${x.slice(0, -1).join(", ")} and ${x[x.length - 1]}`;
}

// What an officer can do with each kind of shared identifier. Procedural, not legal advice:
// the officer decides; the card only names the usual first request.
const KEY_STEP = {
  "UPI ID": (k) => ({ en: `Ask the bank / payment app for the KYC and transaction trail of ${k} (BNSS Sec 94 notice).`, kn: `${k} ಗಾಗಿ ಬ್ಯಾಂಕ್‌ನಿಂದ KYC ಮತ್ತು ವಹಿವಾಟು ವಿವರ ಕೇಳಿ (BNSS ಸೆಕ್ಷನ್ 94).` }),
  "IP address": (k) => ({ en: `Ask the ISP who held ${k} on the offence dates.`, kn: `ಅಪರಾಧದ ದಿನಗಳಲ್ಲಿ ${k} ಯಾರದ್ದು ಎಂದು ISP ಯಿಂದ ಕೇಳಿ.` }),
  vehicle: (k) => ({ en: `Check ${k} on VAHAN for the registered owner, then ANPR / toll records for its movement.`, kn: `${k} ಮಾಲೀಕರನ್ನು VAHAN ನಲ್ಲಿ ಪರಿಶೀಲಿಸಿ, ನಂತರ ಟೋಲ್ / ANPR ದಾಖಲೆಗಳು.` }),
};
const KEY_LABEL = { "UPI ID": ["UPI ID", "UPI ಐಡಿ"], "IP address": ["IP address", "IP ವಿಳಾಸ"], vehicle: ["Vehicle", "ವಾಹನ"] };

function Section({ id, title, count, open, onToggle, children }) {
  return (
    <section className={`fp-sec ${open ? "open" : ""}`}>
      <button type="button" className="fp-sec-h" aria-expanded={open} aria-controls={`fp-${id}`} onClick={() => onToggle(id)}>
        <span>{title}</span>
        {count != null && <em>{count}</em>}
        <svg className="fp-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div id={`fp-${id}`} key="b" className="fp-sec-b"
                      initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                      transition={SPRING} style={{ overflow: "hidden" }}>
            <div className="fp-sec-in">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

export default function FocusPanel({ focus, name, kn, Donut, linkColors = {}, onExit, onAskRegister }) {
  const c = focus.comp;
  const total = c.size || 1;
  const pct = (n) => Math.round((n / total) * 100);
  const [wide, setWide] = useState(false);
  const [open, setOpen] = useState({ brief: true, mix: true, keys: true, people: true, where: false, time: false, firs: false, why: false });
  const [allFirs, setAllFirs] = useState(false);
  const [asked, setAsked] = useState([]);       // [{ q, a: { lead, rows } }] - answers about this group
  const [askText, setAskText] = useState("");
  const toggle = (id) => setOpen((o) => ({ ...o, [id]: !o[id] }));
  const allOpen = Object.values(open).every(Boolean);
  const setAll = (v) => setOpen((o) => Object.fromEntries(Object.keys(o).map((k) => [k, v])));

  const people = c.accused?.length ? c.accused : (c.people || []).map((p) => ({ ...p, n: null }));
  const lines = c.lines?.length ? c.lines : (c.rows || []).map((r) => ({ ...r, n: 1 }));
  const stations = c.byStation || [];
  const keys = c.sharedKeys || [];
  const yMax = Math.max(1, ...(c.byYear || []).map((y) => y.n));
  const years = c.years ? (c.years[0] === c.years[1] ? `${c.years[0]}` : `${c.years[0]} to ${c.years[1]}`) : null;
  const nowYear = new Date().getFullYear();

  // The brief: three short blocks an officer can read in ten seconds.
  const brief = useMemo(() => {
    const main = c.cats?.[0];
    const topKey = keys[0];
    const repeat = people.filter((p) => p.n >= 2)[0];
    const what = main ? `${main.n === c.size ? "all" : `${main.n} of ${c.size}`} ${nice(main.label).toLowerCase()}` : null;

    // what holds the group together, strongest link first
    let bond;
    if (topKey) bond = `${topKey.n === c.size ? `all ${topKey.n}` : `${topKey.n} of them`} share the ${KEY_LABEL[topKey.kind]?.[0] || topKey.kind} ${topKey.name}`;
    else if (repeat) bond = `${repeat.n === c.size ? `all ${repeat.n} name` : `${repeat.n} of them name`} the same accused, ${repeat.name} (${repeat.id})`;
    else if (focus.whys?.length) bond = `they are linked by ${focus.whys[0].text.split(" — ")[0].toLowerCase()}`;

    const headline = `${plural(c.size, "FIR")}${what ? ` (${what})` : ""} across ${plural(c.districts.length, "district")}`
      + `${stations.length ? ` and ${plural(stations.length, "station")}` : ""}${years ? `, ${years}` : ""}`
      + `${bond ? `: ${bond}.` : "."}`;
    const headlineKn = `${c.size} FIR, ${c.districts.length} ಜಿಲ್ಲೆ${stations.length ? `, ${stations.length} ಠಾಣೆ` : ""}${years ? `, ${years}` : ""}`
      + (topKey ? ` - ಒಂದೇ ${KEY_LABEL[topKey.kind]?.[1] || topKey.kind} ${topKey.name} (${topKey.n} FIR).` : repeat ? ` - ಒಂದೇ ಆರೋಪಿ ${repeat.name} (${repeat.n} FIR).` : ".");

    // why it matters: only signals the group actually carries
    const why = [];
    if (topKey) why.push({ t: "hard", en: `A shared ${KEY_LABEL[topKey.kind]?.[0] || topKey.kind} is a hard link: the same account or device appears in ${plural(topKey.n, "case")}.`, kn: `ಹಂಚಿಕೆಯ ${KEY_LABEL[topKey.kind]?.[1] || topKey.kind}: ಒಂದೇ ಖಾತೆ/ಸಾಧನ ${topKey.n} ಪ್ರಕರಣಗಳಲ್ಲಿ.` });
    if (repeat) why.push({ t: "person", en: `${repeat.name} is named in ${plural(repeat.n, "FIR")} - a possible repeat offender.`, kn: `${repeat.name} ${repeat.n} FIR ಗಳಲ್ಲಿ - ಪುನರಾವರ್ತಿತ ಆರೋಪಿ ಸಾಧ್ಯತೆ.` });
    if (stations.length > 1) why.push({ t: "spread", en: `Registered at ${plural(stations.length, "station")}${c.districts.length > 1 ? ` in ${plural(c.districts.length, "district")}` : ""}, so each station may be working its part alone.`, kn: `${stations.length} ಠಾಣೆಗಳಲ್ಲಿ ದಾಖಲಾಗಿದೆ - ಪ್ರತಿ ಠಾಣೆ ಪ್ರತ್ಯೇಕವಾಗಿ ತನಿಖೆ ಮಾಡುತ್ತಿರಬಹುದು.` });
    if (c.years && c.years[1] >= nowYear - 1) why.push({ t: "recent", en: `Recent: the latest FIR is from ${c.years[1]}.`, kn: `ಇತ್ತೀಚಿನದು: ಕೊನೆಯ FIR ${c.years[1]}.` });
    if (c.noAccused === c.size && c.size > 0) why.push({ t: "unknown", en: "No FIR names an accused: the offender is still unidentified.", kn: "ಯಾವ FIR ನಲ್ಲೂ ಆರೋಪಿ ಹೆಸರಿಲ್ಲ: ಅಪರಾಧಿ ಇನ್ನೂ ಗುರುತಿಸಿಲ್ಲ." });

    // next steps: what the officer would usually request first
    const steps = [];
    keys.slice(0, 2).forEach((k) => { const s = KEY_STEP[k.kind]?.(k.name); if (s) steps.push(s); });
    if (repeat) steps.push({ en: `Pull ${repeat.name}'s (${repeat.id}) record: arrests, bail status and any warrant across these stations.`, kn: `${repeat.name} (${repeat.id}) ಅವರ ದಾಖಲೆ: ಬಂಧನ, ಜಾಮೀನು, ವಾರಂಟ್.` });
    if (stations.length > 1) steps.push({ en: `Share this group with ${stations.length > 3 ? `${stations.slice(0, 3).map((s) => s.name).join(", ")} and ${stations.length - 3} more stations` : listJoin(stations.map((s) => s.name))} so the FIRs are worked as one case.`, kn: `ಈ ಗುಂಪನ್ನು ${stations.slice(0, 3).map((s) => s.name).join(", ")} ಠಾಣೆಗಳೊಂದಿಗೆ ಹಂಚಿಕೊಳ್ಳಿ.` });
    if (!steps.length) steps.push({ en: "Read the FIRs together for a common method, place or time.", kn: "ಸಾಮಾನ್ಯ ವಿಧಾನ, ಸ್ಥಳ, ಸಮಯಕ್ಕಾಗಿ FIR ಗಳನ್ನು ಒಟ್ಟಿಗೆ ಓದಿ." });
    return { headline, headlineKn, why, steps };
  }, [focus]); // eslint-disable-line

  // ── Ask about this group ──
  // Answered here, from the group's own records. Chat reads the 10-lakh register, which does
  // not hold these curated IDs, so sending "who is ACC-…" there came back with unrelated FIRs.
  const QUICK = [
    ["first", { en: "Who should I look at first?", kn: "ಮೊದಲು ಯಾರನ್ನು ನೋಡಬೇಕು?" }],
    ["links", { en: "What links these cases?", kn: "ಈ ಪ್ರಕರಣಗಳನ್ನು ಏನು ಜೋಡಿಸುತ್ತದೆ?" }],
    ["where", { en: "Where and when?", kn: "ಎಲ್ಲಿ ಮತ್ತು ಯಾವಾಗ?" }],
    ["active", { en: "Is it still active?", kn: "ಇನ್ನೂ ಸಕ್ರಿಯವೇ?" }],
    ["next", { en: "What should I do next?", kn: "ಮುಂದೆ ಏನು ಮಾಡಬೇಕು?" }],
  ];
  function intentOf(text) {
    const t = text.toLowerCase();
    if (/(who|person|people|accused|suspect|first|key|ಯಾರು|ಆರೋಪಿ)/.test(t)) return "first";
    if (/(link|connect|why|same|share|common|tie|ಜೋಡ|ಸಂಪರ್ಕ)/.test(t)) return "links";
    if (/(active|recent|latest|still|last|ongoing|now|ಸಕ್ರಿಯ|ಇತ್ತೀಚ)/.test(t)) return "active";
    if (/(where|station|district|place|when|year|time|month|ಎಲ್ಲಿ|ಯಾವಾಗ|ಠಾಣೆ|ಜಿಲ್ಲೆ)/.test(t)) return "where";
    if (/(do|next|action|step|plan|should|ಮುಂದೆ|ಕ್ರಮ)/.test(t)) return "next";
    return null;
  }
  function answer(intent) {
    const latestYear = c.byYear?.length ? c.byYear[c.byYear.length - 1] : null;
    const firsWord = (n) => `${n} ${n === 1 ? "FIR" : "FIRs"}`;
    if (intent === "first") {
      const ranked = [...people].filter((p) => p.n != null).sort((a, b) => b.n - a.n).slice(0, 3);
      if (!ranked.length) {
        const lead = keys[0]
          ? (kn ? `ಯಾವ FIR ನಲ್ಲೂ ಆರೋಪಿ ಹೆಸರಿಲ್ಲ. ${keys[0].name} (${keys[0].n} FIR) ಇಂದ ಆರಂಭಿಸಿ.` : `No FIR here names an accused. Start from the shared ${KEY_LABEL[keys[0].kind]?.[0] || keys[0].kind} ${keys[0].name}, which is in ${firsWord(keys[0].n)}.`)
          : (kn ? "ಯಾವ FIR ನಲ್ಲೂ ಆರೋಪಿ ಹೆಸರಿಲ್ಲ. ಹೆಚ್ಚು ಪ್ರಕರಣವಿರುವ ಠಾಣೆಯಿಂದ ಆರಂಭಿಸಿ." : `No FIR here names an accused. Start with ${stations[0]?.name || "the station"} , which holds the most of these cases.`);
        return { lead, rows: [] };
      }
      const top = ranked[0];
      return {
        lead: kn ? `${top.name} (${top.id}) - ${top.n} FIR ಗಳಲ್ಲಿ ಹೆಸರಿಸಲಾಗಿದೆ.` : `${top.name} (${top.id}), named in ${firsWord(top.n)} of the ${c.size} in this group${top.n >= 2 ? ", the strongest repeat link here" : ""}.`,
        rows: ranked.slice(1).map((p) => `${p.name} (${p.id}) · ${firsWord(p.n)}`)
          .concat(c.noAccused ? [kn ? `${c.noAccused} FIR ಗಳಲ್ಲಿ ಆರೋಪಿ ಹೆಸರಿಲ್ಲ` : `${firsWord(c.noAccused)} name no accused`] : []),
      };
    }
    if (intent === "links") {
      const rows = keys.map((k) => `${KEY_LABEL[k.kind]?.[kn ? 1 : 0] || k.kind} ${k.name} · ${kn ? `${k.n} FIR` : `in ${firsWord(k.n)}`}`);
      const why = (focus.whys || []).map((w) => w.text);
      return {
        lead: keys.length
          ? (kn ? `ಹಂಚಿಕೊಂಡ ${keys.length} ಗುರುತು ಈ ಪ್ರಕರಣಗಳನ್ನು ಜೋಡಿಸುತ್ತದೆ - ಇದು ಗಟ್ಟಿ ಸಂಪರ್ಕ.` : `${keys.length === 1 ? "One shared identifier" : `${keys.length} shared identifiers`} tie these cases together. That is a hard link: the same account, device or vehicle appears in more than one FIR.`)
          : (kn ? "ಈ ಪ್ರಕರಣಗಳು ಹೀಗೆ ಜೋಡಿಸಲ್ಪಟ್ಟಿವೆ:" : "These cases are grouped by:"),
        rows: rows.concat(why.slice(0, 3)),
      };
    }
    if (intent === "where") {
      const list = (xs) => xs.slice(0, 3).map((x) => `${x.name} (${x.n})`).join(", ");
      const topSt = stations[0];
      return {
        lead: kn
          ? `${c.size} FIR, ${c.districts.length} ಜಿಲ್ಲೆ, ${stations.length} ಠಾಣೆ${years ? `, ${years}` : ""}.${topSt ? ` ಹೆಚ್ಚು: ${topSt.name} (${topSt.n}).` : ""}`
          : `${firsWord(c.size)} across ${c.districts.length} ${c.districts.length === 1 ? "district" : "districts"} and ${stations.length} ${stations.length === 1 ? "station" : "stations"}${years ? `, ${years}` : ""}.${topSt ? ` The most at one station: ${topSt.name}, ${firsWord(topSt.n)}.` : ""}`,
        rows: [
          stations.length ? `${kn ? "ಠಾಣೆಗಳು" : "Stations"}: ${list(stations)}${stations.length > 3 ? (kn ? ` ಮತ್ತು ${stations.length - 3} ಇನ್ನಷ್ಟು` : ` and ${stations.length - 3} more`) : ""}` : null,
          (c.byDistrict || []).length ? `${kn ? "ಜಿಲ್ಲೆಗಳು" : "Districts"}: ${list(c.byDistrict)}` : null,
          (c.byYear || []).length > 1 ? `${kn ? "ವರ್ಷವಾರು" : "By year"}: ${c.byYear.map((y) => `${y.name} (${y.n})`).join(", ")}` : null,
        ].filter(Boolean),
      };
    }
    if (intent === "active") {
      if (!latestYear) return { lead: kn ? "ದಿನಾಂಕ ದಾಖಲಾಗಿಲ್ಲ." : "The FIRs here carry no date to judge it by.", rows: [] };
      const recent = latestYear.name >= nowYear - 1;
      return {
        lead: recent
          ? (kn ? `ಹೌದು - ಕೊನೆಯ FIR ${latestYear.name} ರಲ್ಲಿ, ಆ ವರ್ಷ ${latestYear.n}.` : `Yes. The latest FIRs are from ${latestYear.name} (${firsWord(latestYear.n)} that year), so this group is recent enough to act on.`)
          : (kn ? `ಇಲ್ಲ - ${latestYear.name} ನಂತರ ಹೊಸ FIR ಇಲ್ಲ.` : `Quiet since ${latestYear.name}: no FIR in this group after that year. Check whether the accused is in custody or has moved before spending patrol time.`),
        rows: [],
      };
    }
    if (intent === "next") return { lead: kn ? "ಸಲಹೆಯ ಹೆಜ್ಜೆಗಳು:" : "Suggested next steps, strongest first:", rows: brief.steps.map((x) => (kn ? x.kn : x.en)) };
    return {
      lead: kn ? "ಇದಕ್ಕೆ ಈ ಗುಂಪಿನ ದಾಖಲೆಗಳಲ್ಲಿ ಉತ್ತರವಿಲ್ಲ. ಕೆಳಗಿನ ಪ್ರಶ್ನೆಗಳಲ್ಲಿ ಒಂದನ್ನು ಕೇಳಿ, ಅಥವಾ ಪೂರ್ಣ ದಾಖಲೆಯನ್ನು ಚಾಟ್‌ನಲ್ಲಿ ಕೇಳಿ."
                : "This group's records don't answer that. Try one of the questions below, or ask Chat about the full register.",
      rows: [],
    };
  }
  function ask(q, intent) {
    const a = answer(intent ?? intentOf(q));
    setAsked((prev) => [...prev.slice(-3), { q, a }]);
    setAskText("");
  }
  // what Chat can answer about the wider picture: the group's main crime, where most of it is, latest year
  const registerQ = (() => {
    const crime = lines[0] ? nice(lines[0].crime).toLowerCase() : (c.cats?.[0]?.label || "crime").toLowerCase();
    const where = c.byDistrict?.[0]?.name || c.districts[0];
    const yr = c.byYear?.length ? c.byYear[c.byYear.length - 1].name : null;
    return `How many ${crime} cases were registered in ${where}${yr ? ` in ${yr}` : ""}?`;
  })();

  const shownLines = allFirs ? lines : lines.slice(0, wide ? 10 : 5);
  const restFirs = c.size - shownLines.reduce((t, l) => t + (l.n || 1), 0);
  const L = (en, k) => (kn ? k : en);

  return (
    <motion.aside className={`bsx-focus fp ${wide ? "wide" : ""}`} aria-label={L("Focused group", "ಫೋಕಸ್")}
                  layout transition={SPRING}>
      <header className="fp-head">
        <div className="fp-title">
          <span className="fp-eyebrow"><i aria-hidden="true" />{L("Linked group", "ಸಂಪರ್ಕಿತ ಗುಂಪು")}</span>
          <h3>{name}</h3>
          {focus.node.accused && <code>{focus.node.accused}</code>}
        </div>
        <div className="fp-actions">
          <button type="button" className="fp-icon" onClick={() => setWide(!wide)} aria-pressed={wide}
                  title={wide ? L("Narrow the card", "ಕಿರಿದಾಗಿಸಿ") : L("Widen the card", "ವಿಸ್ತರಿಸಿ")}
                  aria-label={wide ? L("Narrow the card", "ಕಿರಿದಾಗಿಸಿ") : L("Widen the card", "ವಿಸ್ತರಿಸಿ")}>
            {wide
              ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7" /></svg>
              : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" /></svg>}
          </button>
          <button type="button" className="fp-exit" onClick={onExit}>{L("Exit focus", "ಫೋಕಸ್ ಮುಚ್ಚಿ")}</button>
        </div>
      </header>

      {/* the figures, each with its word under it */}
      <div className="fp-stats">
        <div><b>{c.size}</b><span>{c.size === 1 ? "FIR" : "FIRs"}</span></div>
        <div><b>{c.districts.length}</b><span>{L(c.districts.length === 1 ? "District" : "Districts", "ಜಿಲ್ಲೆ")}</span></div>
        <div><b>{stations.length || "-"}</b><span>{L(stations.length === 1 ? "Station" : "Stations", "ಠಾಣೆ")}</span></div>
        <div><b>{people.length}</b><span>{L("Accused", "ಆರೋಪಿ")}</span></div>
        {years && <div><b className="yr">{years.replace(" to ", "–")}</b><span>{L("Period", "ಅವಧಿ")}</span></div>}
      </div>

      <div className="fp-tools">
        <button type="button" onClick={() => setAll(!allOpen)}>{allOpen ? L("Collapse all", "ಎಲ್ಲವನ್ನೂ ಮಡಚಿ") : L("Expand all", "ಎಲ್ಲವನ್ನೂ ತೆರೆಯಿರಿ")}</button>
      </div>

      <div className="fp-body">
        <Section id="brief" title={L("Summary", "ಸಾರಾಂಶ")} open={open.brief} onToggle={toggle}>
          <p className="fp-headline">{kn ? brief.headlineKn : brief.headline}</p>
          {brief.why.length > 0 && (
            <>
              <h5>{L("Why it matters", "ಏಕೆ ಮುಖ್ಯ")}</h5>
              <ul className="fp-why">
                {brief.why.map((w, i) => <li key={i} className={`t-${w.t}`}><i aria-hidden="true" />{kn ? w.kn : w.en}</li>)}
              </ul>
            </>
          )}
          <h5>{L("Suggested next steps", "ಮುಂದಿನ ಹೆಜ್ಜೆಗಳು")}</h5>
          <ol className="fp-steps">
            {brief.steps.map((s, i) => <li key={i}><span>{i + 1}</span>{kn ? s.kn : s.en}</li>)}
          </ol>
          <p className="fp-note">{L("These are record links, not proof of guilt. Read the FIRs before acting.", "ಇವು ದಾಖಲೆಗಳ ಸಂಪರ್ಕ, ಅಪರಾಧದ ಪುರಾವೆ ಅಲ್ಲ. ಕ್ರಮಕ್ಕೆ ಮೊದಲು FIR ಓದಿ.")}</p>
        </Section>

        <Section id="mix" title={L("Type of crime", "ಅಪರಾಧ ಪ್ರಕಾರ")} count={c.cats.length} open={open.mix} onToggle={toggle}>
          <div className="fp-mix">
            {Donut && <div className="fp-donut"><Donut cats={c.cats} total={c.size} /></div>}
            <ul>
              {c.cats.slice(0, 6).map((x) => (
                <li key={x.cat}><i style={{ background: x.color }} /><span>{x.label}</span><b>{x.n}</b><em>{pct(x.n)}%</em></li>
              ))}
            </ul>
          </div>
        </Section>

        {keys.length > 0 && (
          <Section id="keys" title={L("Shared identifiers", "ಹಂಚಿಕೊಂಡ ಗುರುತುಗಳು")} count={keys.length} open={open.keys} onToggle={toggle}>
            <ul className="fp-keys">
              {keys.map((k) => (
                <li key={k.kind + k.name}>
                  <span className="kind">{KEY_LABEL[k.kind]?.[kn ? 1 : 0] || k.kind}</span>
                  <code>{k.name}</code>
                  <b>{L(`in ${k.n} of ${c.size} FIRs`, `${c.size} ರಲ್ಲಿ ${k.n} FIR`)}</b>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {(people.length > 0 || c.noAccused > 0) && (
          <Section id="people" title={L("People involved", "ಸಂಬಂಧಿತ ಆರೋಪಿಗಳು")} count={people.length} open={open.people} onToggle={toggle}>
            {people.length > 0 && (
              <ul className="fp-people">
                {people.slice(0, wide ? 10 : 5).map((p) => (
                  <li key={p.id}>
                    <span className="av" aria-hidden="true">{String(p.name || "?").split(/\s+/).map((w) => w[0]).slice(0, 2).join("")}</span>
                    <div><b>{p.name}</b><code>{p.id}</code></div>
                    {p.n != null && <em className={p.n >= 2 ? "rep" : ""}>{plural(p.n, "FIR")}</em>}
                  </li>
                ))}
              </ul>
            )}
            {people.length > (wide ? 10 : 5) && <p className="fp-more">{L(`and ${people.length - (wide ? 10 : 5)} more named accused`, `ಇನ್ನೂ ${people.length - (wide ? 10 : 5)} ಆರೋಪಿಗಳು`)}</p>}
            {c.noAccused > 0 && <p className="fp-more">{L(`${plural(c.noAccused, "FIR")} ${c.noAccused === 1 ? "names" : "name"} no accused.`, `${c.noAccused} FIR ಗಳಲ್ಲಿ ಆರೋಪಿ ಹೆಸರಿಲ್ಲ.`)}</p>}
          </Section>
        )}

        {(c.byDistrict?.length > 0 || stations.length > 0) && (
          <Section id="where" title={L("Where it was registered", "ಎಲ್ಲಿ ದಾಖಲಾಗಿದೆ")} count={c.districts.length} open={open.where} onToggle={toggle}>
            <h5>{L("Districts", "ಜಿಲ್ಲೆಗಳು")}</h5>
            <ul className="fp-bars">
              {(c.byDistrict || []).slice(0, wide ? 8 : 5).map((d) => (
                <li key={d.name}><span>{d.name}</span><i><u style={{ width: `${Math.max(4, pct(d.n))}%` }} /></i><b>{d.n}</b></li>
              ))}
            </ul>
            {stations.length > 0 && (
              <>
                <h5>{L("Police stations", "ಪೊಲೀಸ್ ಠಾಣೆಗಳು")}</h5>
                <ul className="fp-bars st">
                  {stations.slice(0, wide ? 8 : 5).map((d) => (
                    <li key={d.name}><span>{d.name}</span><i><u style={{ width: `${Math.max(4, pct(d.n))}%` }} /></i><b>{d.n}</b></li>
                  ))}
                </ul>
                {stations.length > (wide ? 8 : 5) && <p className="fp-more">{L(`and ${stations.length - (wide ? 8 : 5)} more stations`, `ಇನ್ನೂ ${stations.length - (wide ? 8 : 5)} ಠಾಣೆಗಳು`)}</p>}
              </>
            )}
          </Section>
        )}

        {c.byYear?.length > 0 && (
          <Section id="time" title={L("When", "ಯಾವಾಗ")} count={years} open={open.time} onToggle={toggle}>
            <div className="fp-years">
              {c.byYear.map((y) => (
                <div key={y.name} title={`${y.name}: ${y.n} FIRs`}>
                  <b>{y.n}</b><i style={{ height: `${Math.max(6, (y.n / yMax) * 52)}px` }} /><span>{y.name}</span>
                </div>
              ))}
            </div>
          </Section>
        )}

        {lines.length > 0 && (
          <Section id="firs" title={L("FIRs in this group", "ಗುಂಪಿನ FIR ಗಳು")} count={c.size} open={open.firs} onToggle={toggle}>
            <ul className="fp-firs">
              {shownLines.map((r, i) => (
                <li key={i}>
                  <div><span>{nice(r.crime)}</span>{r.n > 1 && <b>{r.n} FIRs</b>}</div>
                  <em>{[r.head && nice(r.head), r.zone, r.year].filter(Boolean).join(" · ")}</em>
                </li>
              ))}
            </ul>
            {restFirs > 0 && !allFirs && (
              <button type="button" className="fp-link" onClick={() => setAllFirs(true)}>
                {L(`Show the other ${plural(restFirs, "FIR")}`, `ಇನ್ನೂ ${restFirs} FIR ತೋರಿಸಿ`)}
              </button>
            )}
          </Section>
        )}

        {focus.whys?.length > 0 && (
          <Section id="why" title={L("How they are connected", "ಹೇಗೆ ಸಂಪರ್ಕಿತ")} count={focus.whys.length} open={open.why} onToggle={toggle}>
            <ul className="fp-links">
              {focus.whys.map((w, i) => <li key={i}><i style={{ background: linkColors[w.kind] || "rgba(255,255,255,0.25)" }} /><span>{w.text}</span></li>)}
            </ul>
          </Section>
        )}

        {focus.node?.knowledge_boundary !== undefined && (
          <div className="fp-gap">
            <b>{L("Identity gap: UNSUB", "ಗುರುತಿನ ಅಂತರ: UNSUB")}</b>
            <span>{L("No confirmed suspect on record.", "ಯಾವುದೇ ದೃಢಪಡಿಸಿದ ಶಂಕಿತ ದಾಖಲಾಗಿಲ್ಲ.")}</span>
          </div>
        )}
      </div>

      <footer className="fp-foot">
        <section className="fp-askbox" aria-label={L("Ask about this group", "ಈ ಗುಂಪಿನ ಬಗ್ಗೆ ಕೇಳಿ")}>
          <h4>{L("Ask about this group", "ಈ ಗುಂಪಿನ ಬಗ್ಗೆ ಕೇಳಿ")}</h4>
          {asked.length > 0 && (
            <ol className="fp-answers" aria-live="polite">
              {asked.map((x, i) => (
                <li key={i}>
                  <p className="q">{x.q}</p>
                  <p className="a">{x.a.lead}</p>
                  {x.a.rows.length > 0 && <ul>{x.a.rows.map((r, j) => <li key={j}>{r}</li>)}</ul>}
                </li>
              ))}
            </ol>
          )}
          <div className="fp-quick">
            {QUICK.map(([k, label]) => (
              <button key={k} type="button" onClick={() => ask(kn ? label.kn : label.en, k)}>{kn ? label.kn : label.en}</button>
            ))}
          </div>
          <form className="fp-askform" onSubmit={(e) => { e.preventDefault(); if (askText.trim()) ask(askText.trim()); }}>
            <input value={askText} onChange={(e) => setAskText(e.target.value)} placeholder={L("Type a question about this group…", "ಈ ಗುಂಪಿನ ಬಗ್ಗೆ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ…")}
                   aria-label={L("Question about this group", "ಈ ಗುಂಪಿನ ಬಗ್ಗೆ ಪ್ರಶ್ನೆ")} />
            <button type="submit" className="fp-ask" disabled={!askText.trim()}>{L("Ask", "ಕೇಳಿ")}</button>
          </form>
        </section>
        <button type="button" className="fp-register" onClick={() => onAskRegister?.(registerQ)}
                title={registerQ}>
          {L("Ask Chat about the wider register", "ಪೂರ್ಣ ದಾಖಲೆಯ ಬಗ್ಗೆ ಚಾಟ್‌ನಲ್ಲಿ ಕೇಳಿ")} <span aria-hidden="true">→</span>
          <em>{registerQ}</em>
        </button>
        <small>{L("Answers come from the records on screen", "ಉತ್ತರಗಳು ತೆರೆಯ ಮೇಲಿನ ದಾಖಲೆಗಳಿಂದ")}</small>
      </footer>
    </motion.aside>
  );
}
