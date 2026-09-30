// Open-data context for the "Think" re-think sequence: a small static Karnataka
// festival/event calendar (month-level - the dataset is month-granular) plus the
// pure aggregation that turns the loaded records into prediction/alert cards.
// No ML here: every number is a real count over the records passed in.

import { CATEGORIES } from "@/lib/crimeGraph";

export const FESTIVALS = [
  { month: 1,  name: "Makara Sankranti",   note: "crowded fairs & travel" },
  { month: 3,  name: "Holi / Ugadi",       note: "street celebrations" },
  { month: 8,  name: "Varamahalakshmi / Independence Day", note: "market rush, processions" },
  { month: 9,  name: "Ganesha Chaturthi",  note: "pandals, night processions" },
  { month: 10, name: "Mysuru Dasara",      note: "state festival - heavy footfall, tourist inflow" },
  { month: 11, name: "Deepavali",          note: "shopping surge, cash movement" },
  { month: 12, name: "Year-end season",    note: "travel + late-night events" },
];

const label = (cat) => CATEGORIES[cat]?.label || cat;

/** Derive 3–4 honest insight cards from the records in view (recs are prepared rows). */
export function thinkInsights(recs) {
  const cards = [];
  if (!recs?.length) return cards;

  // 1) Rising category - biggest YoY climb between the two most recent full years.
  const byCatYear = new Map();
  let maxYear = 0;
  recs.forEach((r) => {
    if (!r._year) return;
    maxYear = Math.max(maxYear, r._year);
    const k = `${r._cat}:${r._year}`;
    byCatYear.set(k, (byCatYear.get(k) || 0) + 1);
  });
  const prevYear = maxYear - 1;
  let best = null;
  for (const cat of Object.keys(CATEGORIES)) {
    const now = byCatYear.get(`${cat}:${maxYear}`) || 0;
    const before = byCatYear.get(`${cat}:${prevYear}`) || 0;
    if (before >= 5 && now > before) {
      const pct = Math.round(((now - before) / before) * 100);
      if (!best || pct > best.pct) best = { cat, now, before, pct };
    }
  }
  if (best) cards.push({
    kind: "trend", sev: best.pct >= 30 ? "high" : "med",
    title: `${label(best.cat)} rising`,
    detail: `${best.before} → ${best.now} FIRs (${prevYear} → ${maxYear}, +${best.pct}%). Watch for continuation into ${maxYear + 1}.`,
    source: "dataset trend",
  });

  // 2) Repeat-offender corridor - accused seen in the most districts.
  const byAccused = new Map();
  recs.forEach((r) => {
    const a = (r.Accused_ID || "").trim();
    if (!a) return;
    (byAccused.get(a) || byAccused.set(a, new Set()).get(a)).add(r.District_Name);
  });
  let corridor = null;
  byAccused.forEach((set, id) => {
    if (set.size >= 2 && (!corridor || set.size > corridor.n)) corridor = { id, n: set.size, districts: [...set] };
  });
  if (corridor) cards.push({
    kind: "network", sev: "high",
    title: "Cross-district repeat offender",
    detail: `${corridor.id} appears in ${corridor.n} districts (${corridor.districts.slice(0, 3).join(", ")}${corridor.n > 3 ? "…" : ""}). Correlate FIRs before the trail cools.`,
    source: "repeat-offender linkage",
  });

  // 3) Cyber concentration - shared UPI/IP cluster size.
  const byHandle = new Map();
  recs.forEach((r) => {
    const h = (r.UPI_ID || r.IP_Address || "").trim();
    if (h && r._cat === "CYBER") byHandle.set(h, (byHandle.get(h) || 0) + 1);
  });
  let cyber = null;
  byHandle.forEach((n, h) => { if (n >= 2 && (!cyber || n > cyber.n)) cyber = { h, n }; });
  if (cyber) cards.push({
    kind: "cyber", sev: "med",
    title: "Shared cyber infrastructure",
    detail: `${cyber.n} cyber FIRs share the same handle (${cyber.h}). Likely one operation - bundle for a single investigation.`,
    source: "UPI/IP linkage",
  });

  // 4) Festival horizon - next festival month with its historical load.
  const nowMonth = new Date().getMonth() + 1;
  const fest = FESTIVALS.find((f) => f.month >= nowMonth) || FESTIVALS[0];
  const monthLoad = recs.filter((r) => r._month === fest.month).length;
  cards.push({
    kind: "festival", sev: "low",
    title: `${fest.name} ahead`,
    detail: `Month ${fest.month} historically carries ${monthLoad} FIRs in this view (${fest.note}). Pre-position patrols in the top districts.`,
    source: "open data · festival calendar",
  });

  return cards;
}
