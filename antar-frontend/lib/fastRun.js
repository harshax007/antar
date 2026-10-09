// Fast Run - what the FIRs in the current view show, counted in the browser.
//
// Every finding follows Antar's answer template: a bottom line that names the record it
// is about, the count behind it, up to three lines of evidence, an evidence class, and -
// where an agent can take it further - the command that runs that agent on that record.
// Nothing here is a judgment: two cases sharing a vehicle is stated as a shared vehicle,
// not as one operation, and an accused id on FIRs in two districts is stated as that.
//
//   K  read from the records (an id that appears on n FIRs)
//   D  calculated from them (a share, a year-on-year change)
//   U  what this view cannot show (FIRs with nothing to link on)

import { CATEGORIES } from "@/lib/crimeGraph";
import { FESTIVALS } from "@/lib/festivals";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const num = (v) => v.toLocaleString();
const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);
const val = (r, f) => String(r[f] || "").trim();
const many = (k, one, more = `${one}s`) => `${num(k)} ${k === 1 ? one : more}`;

function tally(recs, field) {
  const m = new Map();
  recs.forEach((r) => { const v = val(r, field); if (v) (m.get(v) || m.set(v, []).get(v)).push(r); });
  return m;
}
// Largest first; ties broken by name so the same view always gives the same finding.
const ranked = (m) => [...m.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]));

export function fastRun(recs) {
  const out = { pattern: [], network: [], geo: [], forecast: [], linkage: [], corridor: [], vigil: [] };
  const total = recs?.length || 0;
  if (!total) return out;

  // ── Pattern: like-for-like change, the same months of the two latest years ──
  const maxYear = Math.max(...recs.map((r) => r._year || 0));
  const maxMonth = Math.max(...recs.filter((r) => r._year === maxYear).map((r) => r._month || 0));
  if (maxYear && maxMonth) {
    const span = maxMonth === 12 ? "" : maxMonth === 1 ? "Jan " : `Jan–${MONTHS[maxMonth - 1]} `;
    const now = new Map(), before = new Map();
    recs.forEach((r) => {
      if (r._year === maxYear) now.set(r._cat, (now.get(r._cat) || 0) + 1);
      else if (r._year === maxYear - 1 && r._month <= maxMonth) before.set(r._cat, (before.get(r._cat) || 0) + 1);
    });
    const moves = [...before.entries()].filter(([, b]) => b >= 5)
      .map(([cat, b]) => ({ cat, b, n: now.get(cat) || 0, p: Math.round((((now.get(cat) || 0) - b) / b) * 100) }))
      .sort((x, y) => y.p - x.p || x.cat.localeCompare(y.cat));
    // A percentage on a handful of FIRs is not a headline: 9 to 14 is +56% and five cases.
    const weight = (m) => (m.b >= 30 && m.p >= 30 ? "high" : m.b >= 15 ? "med" : "low");
    const card = (m, dir) => ({
      kind: "trend", cls: "D", sev: dir === "up" ? weight(m) : "low",
      title: `${CATEGORIES[m.cat]?.label || m.cat} ${dir} ${Math.abs(m.p)}% on last year`,
      detail: `${many(m.n, "FIR")} in ${span}${maxYear}, ${num(m.b)} in ${span}${maxYear - 1}.`
        + (m.b < 15 ? " Small numbers: go by the count." : ""),
      source: "like-for-like year comparison",
    });
    if (moves[0]?.p > 0) out.pattern.push(card(moves[0], "up"));
    const fall = moves[moves.length - 1];
    if (fall && fall.p < 0 && fall !== moves[0]) out.pattern.push(card(fall, "down"));
  }
  const nowMonth = new Date().getMonth() + 1;
  const fest = FESTIVALS.find((f) => f.month >= nowMonth) || FESTIVALS[0];
  if (fest) {
    const load = recs.filter((r) => r._month === fest.month).length;
    out.pattern.push({
      kind: "festival", cls: "D", sev: "low",
      title: `${fest.name} is in ${MONTHS[fest.month - 1]}`,
      detail: `${MONTHS[fest.month - 1]} holds ${pct(load, total)}% of the FIRs in view (${num(load)}). An even month would be 8%.`,
      source: "festival calendar · FIR dates",
    });
  }

  // ── Network: the accused ids that recur ──
  const byAcc = ranked(tally(recs, "Accused_ID"));
  const districts = (rows) => [...new Set(rows.map((r) => val(r, "District_Name")).filter(Boolean))].sort();
  const repeat = byAcc.filter(([, rows]) => rows.length > 1);
  if (repeat.length) {
    const [id, rows] = repeat[0];
    out.network.push({
      kind: "network", cls: "K", sev: rows.length >= 5 ? "high" : "med",
      title: `${id} is on ${num(rows.length)} FIRs`,
      detail: `${many(repeat.length, "accused id")} repeat in this view.`,
      evidence: repeat.slice(0, 3).map(([a, rs]) => { const d = districts(rs); return `${a} · ${many(rs.length, "FIR")} · ${d.slice(0, 3).join(", ")}${d.length > 3 ? ` +${d.length - 3}` : ""}`; }),
      next: [{ label: `Run Linkage on ${id}`, cmd: `run linkage ${id}` }],
      source: "accused ids on FIRs",
    });
    const wide = repeat.map(([a, rs]) => ({ a, d: districts(rs) })).sort((x, y) => y.d.length - x.d.length || x.a.localeCompare(y.a))[0];
    if (wide && wide.d.length >= 2 && wide.a !== id) out.network.push({
      kind: "network", cls: "K", sev: wide.d.length >= 3 ? "high" : "med",
      title: `${wide.a} appears in ${wide.d.length} districts`,
      detail: `${wide.d.slice(0, 5).join(", ")}${wide.d.length > 5 ? ` and ${wide.d.length - 5} more` : ""}.`,
      next: [{ label: `Run Linkage on ${wide.a}`, cmd: `run linkage ${wide.a}` }],
      source: "accused ids across districts",
    });
  }

  // ── Linkage: FIRs tied together by a hard key ──
  // `as` is how the terminal names the key: run linkage upi:name@bank
  const keys = [["Vehicle_Reg_No", "vehicle", "vehicle"], ["UPI_ID", "UPI id", "upi"], ["IP_Address", "IP address", "ip"]]
    .map(([f, name, as]) => ({ name, as, groups: ranked(tally(recs, f)).filter(([, rs]) => rs.length > 1) }));
  const hard = keys.reduce((s, k) => s + k.groups.length, 0);
  if (hard + repeat.length) {
    const biggest = keys.filter((k) => k.groups.length).map((k) => ({ name: k.name, as: k.as, v: k.groups[0][0], rs: k.groups[0][1] }))
      .sort((x, y) => y.rs.length - x.rs.length);
    out.linkage.push({
      kind: "network", cls: "K", sev: hard + repeat.length > 8 ? "med" : "low",
      title: `${many(hard + repeat.length, "group")} of FIRs share a key`,
      detail: `${num(repeat.length)} by accused · ${keys.map((k) => `${num(k.groups.length)} by ${k.name}`).join(" · ")}.`,
      evidence: biggest.slice(0, 3).map((b) => `${b.name} ${b.v} · ${many(b.rs.length, "FIR")}`),
      next: biggest[0] ? [{ label: `Run Linkage on the ${biggest[0].name} group`, cmd: `run linkage ${biggest[0].as}:${biggest[0].v}` }] : [],
      source: "shared accused / vehicle / UPI / IP",
    });
  }

  // ── Geography: where the view's FIRs sit ──
  const byDist = ranked(tally(recs, "District_Name"));
  if (byDist.length) {
    const [d, rows] = byDist[0];
    const stations = ranked(tally(rows, "UnitName")).slice(0, 3);
    const share = pct(rows.length, total);
    out.geo.push({
      kind: "geo", cls: "D", sev: share > 25 ? "med" : "low",
      title: `${d} has ${share}% of the FIRs in view`,
      detail: `${num(rows.length)} of ${num(total)}.` + (byDist.length > 1 ? ` Next: ${byDist.slice(1, 3).map(([x, rs]) => `${x} (${num(rs.length)})`).join(", ")}.` : ""),
      evidence: stations.map(([s, rs]) => `${s} · ${many(rs.length, "FIR")}`),
      next: [{ label: `Run Geo on ${d}`, cmd: `run geo ${d}` },
             ...(stations[0] ? [{ label: `Run Forecast on ${stations[0][0]}`, cmd: `run forecast ${stations[0][0]}` }] : [])],
      source: "district and station counts",
    });
  }

  // ── Corridors: district pairs that share accused ids ──
  const pairs = new Map();
  byAcc.forEach(([, rows]) => {
    const ds = districts(rows);
    for (let i = 0; i < ds.length; i++) for (let j = i + 1; j < ds.length; j++) {
      const k = `${ds[i]} ↔ ${ds[j]}`;
      pairs.set(k, (pairs.get(k) || 0) + 1);
    }
  });
  const topPairs = [...pairs.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 3);
  if (topPairs.length) {
    const [pair, k] = topPairs[0];
    out.corridor.push({
      kind: "network", cls: "D", sev: k > 2 ? "med" : "low",
      title: `${many(k, "accused id")} ${k === 1 ? "appears" : "appear"} in both ${pair.replace(" ↔ ", " and ")}`,
      detail: `The busiest of ${many(pairs.size, "district pair")} that share an accused id.`,
      evidence: topPairs.map(([p, c]) => `${p} · ${many(c, "accused id")}`),
      source: "accused ids across district pairs",
    });
  }

  // ── What the view cannot show ──
  const noAcc = recs.filter((r) => !val(r, "Accused_ID")).length;
  const noKey = recs.filter((r) => !["Accused_ID", "Vehicle_Reg_No", "UPI_ID", "IP_Address"].some((f) => val(r, f))).length;
  out.vigil.push({
    kind: "alert", cls: "U", sev: "low",
    title: `${pct(noAcc, total)}% of FIRs name no accused`,
    detail: `${num(noAcc)} of ${num(total)}. ${num(noKey)} have nothing to link on, so they show as unlinked - not proven unconnected.`,
    source: "missing fields on FIRs",
  });

  return out;
}
