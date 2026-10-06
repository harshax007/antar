// Builds the Brain-Structure knowledge graph from the synthetic FIR dataset
// (public/fir_synthetic.csv): crime-category clusters + intelligence edges
// (repeat offender / ring / cyber). Pure client-side, no backend.

// ── crime taxonomy: CrimeGroup_Name → analytic category ──
export const CATEGORIES = {
  VIOLENT:   { label: "Violent Crimes",           color: "#FF453A" },
  MURDER:    { label: "Murder",                   color: "#FF2A55" },
  KIDNAP:    { label: "Kidnapping & Abduction",   color: "#FF8A00" },
  WOMEN:     { label: "Crimes vs Women",          color: "#F92672" },
  CHILDREN:  { label: "Crimes vs Children",       color: "#BF5AF2" },
  SCST:      { label: "SC/ST Atrocities",         color: "#892CDC" },
  ECONOMIC:  { label: "Economic Offences",        color: "#FFD60A" },
  CYBER:     { label: "Cyber Crimes",             color: "#00F5D4" },
  PROPERTY:  { label: "Property Crimes",          color: "#30D158" },
  NARCOTICS: { label: "Narcotics & Seizures",     color: "#00C7BE" },
  MISSING:   { label: "Missing Persons",          color: "#64D2FF" },
  CORRUPTION:{ label: "Corruption / Public Servants", color: "#D4AF37" },
  FOREIGN:   { label: "Crimes vs/by Foreigners",  color: "#0A84FF" },
  ENVIRON:   { label: "Environment Offences",     color: "#A4DE02" },
  OTHER:     { label: "Other",                    color: "#98989D" },
};

export function categorize(group) {
  const g = (group || "").toUpperCase();
  if (g.includes("CYBER")) return "CYBER";
  if (g.includes("POCSO") || g.includes("CHILDREN")) return "CHILDREN";
  if (g.includes("CRUELTY BY HUSBAND") || g.includes("WOMEN") || g.includes("MOLEST") || g.includes("DOWRY") || g.includes("RAPE")) return "WOMEN";
  if (g === "MURDER" || g.includes("DOWRY DEATH") || g.includes("CULPABLE HOMICIDE")) return "MURDER";
  if (g.includes("KIDNAP") || g.includes("ABDUCT")) return "KIDNAP";
  if (g.includes("SCHEDULED CASTE") || g.includes("SC/ST")) return "SCST";
  if (g.includes("MISSING")) return "MISSING";
  if (g.includes("CHEAT") || g.includes("BREACH OF TRUST") || g.includes("FORGERY") || g.includes("COUNTERFEIT") || g.includes("ECONOMIC")) return "ECONOMIC";
  if (g.includes("THEFT") || g.includes("ROBBERY") || g.includes("BURGLARY") || g.includes("DACOITY") || g.includes("TRESPASS") || g.includes("MISCHIEF") || g.includes("PROPERTY")) return "PROPERTY";
  if (g.includes("NARCOTIC") || g.includes("EXCISE") || g.includes("SEIZURE")) return "NARCOTICS";
  if (g.includes("ATTEMPT TO MURDER") || g.includes("HURT") || g.includes("RIOT") || g.includes("INTIMIDATION") || g.includes("AFFRAY") || g.includes("ASSAULT")) return "VIOLENT";
  if (g.includes("PUBLIC SERVANT") || g.includes("CORRUPT")) return "CORRUPTION";
  if (g.includes("FOREIGN") || g.includes("PASSPORT")) return "FOREIGN";
  if (g.includes("ANIMAL") || g.includes("FOREST") || g.includes("ENVIRON")) return "ENVIRON";
  return "OTHER";
}

// ── minimal CSV parser (quotes + embedded commas/quotes) ──
export function parseCSV(text) {
  const rows = [];
  let field = "", row = [], inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else inQ = false; }
      else field += c;
    } else if (c === '"') inQ = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else if (c === "\r") { /* skip */ }
    else field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  if (!rows.length) return [];
  const header = rows[0];
  return rows.slice(1).filter((r) => r.length >= header.length - 1).map((r) => {
    const o = {}; header.forEach((h, i) => (o[h] = r[i] ?? "")); return o;
  });
}

// ── minimal JSON parser (shares shape with parseCSV) ──
export function fromRecords(rows) {
  return rows || [];
}

// ── build graph: category hubs + member nodes + intelligence links ──
export function buildCrimeGraph(records, { sampleUnlinkedPerCat = 8, maxNodes = 900, backendData = null } = {}) {
  const recs = records.map((r, i) => ({ ...r, _i: i, _cat: categorize(r.CrimeGroup_Name) }));

  const groupBy = (key, filter) => {
    const m = new Map();
    recs.forEach((r) => {
      if (filter && !filter(r)) return;
      const v = (r[key] || "").trim();
      if (!v) return;
      (m.get(v) || m.set(v, []).get(v)).push(r);
    });
    return m;
  };
  const byAccused = groupBy("Accused_ID");
  const byPlace = groupBy("Place_of_Offence");
  const byVehicle = groupBy("Vehicle_Reg_No");
  const byUPI = groupBy("UPI_ID", (r) => r._cat === "CYBER");
  const byIP = groupBy("IP_Address", (r) => r._cat === "CYBER");

  const linked = new Set();
  const intel = []; // {a, b, kind, key}
  const distinct = (arr, k) => new Set(arr.map((r) => r[k])).size;
  const star = (arr, kind, key) => {
    const hub = arr[0];
    for (let j = 1; j < arr.length; j++) { intel.push({ a: hub._i, b: arr[j]._i, kind, key }); linked.add(hub._i); linked.add(arr[j]._i); }
  };

  let nRepeat = 0, nRing = 0, nCyber = 0;
  // a genuine ring is small; a shared value spanning many rows is usually a generic
  // place-name coincidence, not intelligence — cap group size to keep the web meaningful.
  const RING_MAX = 14;
  byAccused.forEach((arr, key) => { if (arr.length >= 2 && arr.length <= 14) { star(arr, "repeat", key); nRepeat++; } });
  byPlace.forEach((arr, key) => { if (arr.length >= 2 && arr.length <= RING_MAX && (distinct(arr, "CrimeHead_Name") >= 2 || arr.length >= 3)) { star(arr, "ring", key); nRing++; } });
  byVehicle.forEach((arr, key) => { if (arr.length >= 2 && arr.length <= RING_MAX) { star(arr, "ring", key); nRing++; } });
  byUPI.forEach((arr, key) => { if (arr.length >= 2 && arr.length <= 14) { star(arr, "cyber", key); nCyber++; } });
  byIP.forEach((arr, key) => { if (arr.length >= 2 && arr.length <= 14) { star(arr, "cyber", key); nCyber++; } });

  // node selection: all linked + capped sample of unlinked per category
  const chosen = new Set(linked);
  const perCat = {};
  for (const r of recs) {
    if (chosen.has(r._i)) continue;
    perCat[r._cat] = (perCat[r._cat] || 0);
    if (perCat[r._cat] < sampleUnlinkedPerCat && chosen.size < maxNodes) { chosen.add(r._i); perCat[r._cat]++; }
  }

  // category counts (full dataset, for the legend/sidebar)
  const catCount = {};
  recs.forEach((r) => (catCount[r._cat] = (catCount[r._cat] || 0) + 1));

  const activeCats = Object.keys(catCount).sort((a, b) => catCount[b] - catCount[a]);
  const nodes = [];
  const links = [];
  // category hubs
  activeCats.forEach((cat) => nodes.push({ id: `cat:${cat}`, kind: "category", cat, name: CATEGORIES[cat]?.label || cat, val: 26 }));
  // member nodes + hub links
  const memberDeg = {};
  intel.forEach((e) => { memberDeg[e.a] = (memberDeg[e.a] || 0) + 1; memberDeg[e.b] = (memberDeg[e.b] || 0) + 1; });
  recs.forEach((r) => {
    if (!chosen.has(r._i)) return;
    nodes.push({
      id: `fir:${r._i}`, kind: "fir", cat: r._cat, name: `${r.CrimeHead_Name || r.CrimeGroup_Name} · ${r.UnitName}`,
      district: r.District_Name, zone: r.UnitName, crimeGroup: r.CrimeGroup_Name, crimeHead: r.CrimeHead_Name,
      year: r.FIR_YEAR, accused: r.Accused_ID, vehicle: r.Vehicle_Reg_No, upi: r.UPI_ID, ip: r.IP_Address,
      mo: r.MO_Details || "", stage: r.FIR_Stage || r.status || "", place: r.Place_of_Offence || "",
      linked: linked.has(r._i), val: 3 + Math.min(6, (memberDeg[r._i] || 0)),
    });
    links.push({ source: `fir:${r._i}`, target: `cat:${r._cat}`, kind: "member" });
  });
  // intelligence links (only if both endpoints chosen)
  intel.forEach((e) => {
    if (chosen.has(e.a) && chosen.has(e.b)) links.push({ source: `fir:${e.a}`, target: `fir:${e.b}`, kind: e.kind, key: e.key });
  });

  let nInferred = 0, nUnsub = 0;

  if (backendData && backendData.unsubs) {
    // Real UNSUB profiles from the backend
    backendData.unsubs.forEach((u, i) => {
      const uId = `unsub:${u.unsub_id || i}`;
      nodes.push({
        id: uId, kind: "unsub", cat: categorize(u.crime_group), name: u.name || `UNSUB · ${u.crime_group}`,
        district: u.zone, zone: u.zone, crimeGroup: u.crime_group, val: 12, knowledge_boundary: 1.0,
      });
      if (u.fir_ids) {
        u.fir_ids.forEach((firId) => {
          // Find matching frontend node
          const match = nodes.find(n => n.id === `fir:${firId}` || (n.crimeHead && n.crimeHead.includes(firId)));
          if (match) {
            links.push({ source: match.id, target: uId, kind: "unsub", key: `UNSUB Cluster (${u.zone})` });
          }
        });
      }
      nUnsub++;
    });
  } else {
    // Synthetic UNSUB profiles (unsolved FIR clusters by zone + crime group)
    const unsolvedByZoneGroup = new Map();
    recs.forEach((r) => {
      if (!r.Accused_ID || r.Accused_ID === "UNKNOWN" || r.Accused_ID.trim() === "") {
        if (!chosen.has(r._i)) return;
        const key = `${r.UnitName || r.District_Name}|${r.CrimeGroup_Name}`;
        if (!unsolvedByZoneGroup.has(key)) unsolvedByZoneGroup.set(key, []);
        unsolvedByZoneGroup.get(key).push(r);
      }
    });
    let unsubIdx = 1;
    unsolvedByZoneGroup.forEach((arr, key) => {
      if (arr.length >= 3 && unsubIdx <= 15) {
        const uId = `unsub:${unsubIdx}`;
        const [zone, group] = key.split("|");
        nodes.push({
          id: uId, kind: "unsub", cat: categorize(group), name: `UNSUB-${String(unsubIdx).padStart(2, "0")} · ${group}`,
          district: zone, zone, crimeGroup: group, val: 12, knowledge_boundary: 1.0,
        });
        arr.forEach((r) => {
          links.push({ source: `fir:${r._i}`, target: uId, kind: "unsub", key: `UNSUB Cluster (${zone})` });
        });
        nUnsub++;
        unsubIdx++;
      }
    });
  }

  if (backendData && backendData.predicted_edges) {
    // Real predicted edges from the backend
    backendData.predicted_edges.forEach(e => {
      // Find matching frontend nodes by FIR ID or row index
      const a = nodes.find(n => n.id === `fir:${e.source}` || (n.crimeHead && n.crimeHead.includes(e.source)));
      const b = nodes.find(n => n.id === `fir:${e.target}` || (n.crimeHead && n.crimeHead.includes(e.target)));
      if (a && b) {
        links.push({ source: a.id, target: b.id, kind: "inferred", key: e.reason || "Predicted MO Match" });
        nInferred++;
      }
    });
  } else {
    // Predicted edges (inferred links between FIRs in same district/category not otherwise linked)
    const firNodes = nodes.filter((n) => n.kind === "fir");
    const linkedPairs = new Set(links.map((l) => `${l.source}|${l.target}`));
    for (let i = 0; i < firNodes.length && nInferred < 35; i += 3) {
      for (let j = i + 1; j < firNodes.length && nInferred < 35; j += 4) {
        const a = firNodes[i], b = firNodes[j];
        if (a.district === b.district && a.cat === b.cat && a.id !== b.id) {
          const pk1 = `${a.id}|${b.id}`, pk2 = `${b.id}|${a.id}`;
          if (!linkedPairs.has(pk1) && !linkedPairs.has(pk2)) {
            links.push({ source: a.id, target: b.id, kind: "inferred", key: "Predicted MO Match" });
            linkedPairs.add(pk1);
            nInferred++;
          }
        }
      }
    }
  }

  return {
    nodes, links,
    categories: activeCats.map((cat) => ({ cat, label: CATEGORIES[cat]?.label || cat, color: CATEGORIES[cat]?.color || "#5d6b80", count: catCount[cat] })),
    stats: { total: recs.length, shown: chosen.size, repeat: nRepeat, ring: nRing, cyber: nCyber, unsub: nUnsub, inferred: nInferred, intelEdges: intel.length + nUnsub + nInferred },
  };
}

export const LINK_COLORS = { member: "rgba(120,140,170,0.14)", repeat: "#FFB020", ring: "#FF8C42", cyber: "#22E6F0", inferred: "#C084FC", unsub: "#A855F7" };

// ── deterministic display alias for a synthetic Accused_ID ──────────────────
// The dataset has no name column; a stable ID→name mapping makes hubs readable.
// Same ID always yields the same name, and the raw ID is always shown with it.
const ALIAS_FIRST = ["Ravi", "Suresh", "Manju", "Kiran", "Prakash", "Santosh", "Ramesh", "Vijay",
  "Anil", "Mahesh", "Nagesh", "Girish", "Harish", "Lokesh", "Umesh", "Dinesh",
  "Shankar", "Basava", "Mallika", "Deepa", "Rekha", "Savita", "Lakshmi", "Geetha"];
const ALIAS_LAST = ["Kumar", "Gowda", "Shetty", "Naik", "Rao", "Reddy", "Hegde", "Patil",
  "Swamy", "Murthy", "Acharya", "Poojari", "Kulkarni", "Desai", "Angadi", "Byadgi"];

export function aliasFor(id) {
  const d = parseInt(String(id || "").replace(/\D/g, ""), 10);
  if (!Number.isFinite(d)) return "";
  return `${ALIAS_FIRST[d % ALIAS_FIRST.length]} ${ALIAS_LAST[Math.floor(d / ALIAS_FIRST.length) % ALIAS_LAST.length]}`;
}

// ── Phase 2: shared selection + overview aggregations ────────────────────────

/** Parse once, categorize once — every consumer (globe, timeline, overview) shares this shape. */
export function prepare(records) {
  return records.map((r, i) => ({
    ...r, _i: i,
    _cat: categorize(r.CrimeGroup_Name),
    _year: parseInt(r.FIR_YEAR, 10) || null,
    _month: parseInt(r.FIR_MONTH, 10) || null,
    _day: parseInt(r.FIR_Day, 10) || null,
  }));
}

export function isFutureRecord(r) {
  const today = new Date();
  const y = r._year;
  if (!y) return false;
  if (y > today.getFullYear()) return true;
  if (y === today.getFullYear() && r._month && r._month > today.getMonth() + 1) return true;
  if (y === today.getFullYear() && r._month === today.getMonth() + 1 && r._day && r._day > today.getDate()) return true;
  return false;
}

/** sel = { year, month, day, district, cats:Set|null, range:string|null, excludeFuture:boolean } */
export function filterRecords(recs, sel = {}) {
  const excludeFuture = sel.excludeFuture !== false;
  let out = recs.filter((r) => {
    if (excludeFuture && isFutureRecord(r)) return false;
    if (sel.year && r._year !== sel.year) return false;
    // render-scope year span (inclusive); independent of the single-year calendar pick
    if (sel.yearFrom && (!r._year || r._year < sel.yearFrom)) return false;
    if (sel.yearTo && (!r._year || r._year > sel.yearTo)) return false;
    if (sel.month && r._month !== sel.month) return false;
    if (sel.day && r._day !== sel.day) return false;
    if (sel.district && r.District_Name !== sel.district) return false;
    if (sel.cats && sel.cats.size > 0 && !sel.cats.has(r._cat)) return false;
    return true;
  });

  // Newest-first ordering, shared by the legacy top-N `range` and the FIR index window.
  const byRecency = (a, b) => {
    const ya = a._year || 0, yb = b._year || 0;
    if (ya !== yb) return yb - ya;
    const ma = a._month || 0, mb = b._month || 0;
    if (ma !== mb) return mb - ma;
    return (b._day || 0) - (a._day || 0);
  };

  if (sel.range && sel.range !== "ALL") {
    const num = parseInt(sel.range, 10);
    if (!isNaN(num) && num > 0) out = [...out].sort(byRecency).slice(0, num);
  }

  // Explicit FIR index window, 1-based inclusive ("render FIR 1–2000").
  if (sel.firFrom || sel.firTo) {
    out = [...out].sort(byRecency);
    const start = Math.max(0, (sel.firFrom || 1) - 1);
    const end = sel.firTo ? Math.max(start, sel.firTo) : out.length;
    out = out.slice(start, end);
  }

  return out;
}

/** 2D constellation view: FIR nodes + intelligence edges only, grouped by
 *  connected component (each shared-accused/vehicle/UPI star = one colored
 *  community), gray dust for unlinked FIRs, red enlarged nodes for brokers
 *  (high-degree hubs). Deterministic — no stochastic community detection. */
const COMM_PALETTE = ["#FFD24A", "#5B8CFF", "#18D69A", "#FF5DA2", "#B026FF", "#FF8C42",
                      "#7CF0CB", "#9D6BFF", "#E1B12C", "#6BA3FF", "#4CAF50", "#FF9BD2"];

export function buildConstellation(graph, { groupBy = "evidence" } = {}) {
  const nodes = graph.nodes.filter((n) => n.kind === "fir").map((n) => ({ ...n }));
  const links = graph.links.filter((l) => l.kind !== "member").map((l) => ({ ...l }));

  const deg = {};
  links.forEach((l) => { deg[l.source] = (deg[l.source] || 0) + 1; deg[l.target] = (deg[l.target] || 0) + 1; });

  // union-find over intel edges → components
  const parent = new Map();
  const find = (x) => {
    if (!parent.has(x)) parent.set(x, x);
    let r = x;
    while (parent.get(r) !== r) r = parent.get(r);
    while (parent.get(x) !== r) { const nx = parent.get(x); parent.set(x, r); x = nx; }
    return r;
  };
  const union = (a, b) => { const ra = find(a), rb = find(b); if (ra !== rb) parent.set(ra, rb); };
  links.forEach((l) => union(l.source, l.target));

  const compOf = {}, compSize = {};
  nodes.forEach((n) => { const c = find(n.id); compOf[n.id] = c; compSize[c] = (compSize[c] || 0) + 1; });
  const comps = Object.entries(compSize).filter(([, s]) => s >= 2)
    .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1));

  // Roles per the patent-network reference: gray records, dark labeled hubs
  // (most-linked accused), one green apex (most connected in view).
  const hubs = nodes.filter((n) => (deg[n.id] || 0) >= 4)
    .sort((a, b) => (deg[b.id] - deg[a.id]) || String(a.id).localeCompare(String(b.id)))
    .slice(0, 10);
  const hubSet = new Set(hubs.map((h) => h.id));
  const apex = hubs[0]?.id ?? null;

  // Sphere structure: big linked components settle in the core, small groups
  // sit on a mid ring, unlinked dust forms the outer shell. Components share
  // one rim angle so each group stays visually together (golden-angle spread).
  const golden = Math.PI * (3 - Math.sqrt(5));
  const compAngle = new Map();
  let ai = 0;
  const angleOf = (c) => { if (!compAngle.has(c)) compAngle.set(c, ai++ * golden); return compAngle.get(c); };
  const compRank = new Map(comps.map(([c], i) => [c, i]));

  nodes.forEach((n) => {
    const c = compOf[n.id];
    const size = compSize[c] || 1;
    n.deg = deg[n.id] || 0;
    n.comm = size >= 2 ? c : null;
    n.role = n.id === apex ? "top" : hubSet.has(n.id) ? "hub" : n.comm ? "linked" : "dust";
    const named = n.role === "hub" || n.role === "top";
    n.label = named ? (aliasFor(n.accused) || n.zone || "") : "";
    n.sub = named && n.accused ? n.accused : "";
    n.vsize = n.role === "top" ? 9 : n.role === "hub" ? 7 : n.comm ? 2.6 : 1.5;
    n.ring = size >= 5 ? 50 + ((compRank.get(c) ?? 0) % 6) * 24 : size >= 2 ? 360 : 470;
    const a = angleOf(c) + (n._i % 97) * 0.012;
    const r = n.ring + ((n._i * 37) % 44) - 22;
    n.x = Math.cos(a) * r;
    n.y = Math.sin(a) * r;
  });

  // Per-group intelligence naming for the outside callout labels (ref: the
  // India-crime poster's state callouts). A group is named by what holds it
  // together: dominant accused → "«alias» network", shared UPI/IP → cyber
  // ring, shared place/vehicle → ring.
  const info = new Map(); // comp → {kind, key, acc, dist, members}
  const bump = (m, k) => m.set(k, (m.get(k) || 0) + 1);
  links.forEach((l) => {
    const c = find(l.source);
    if (!info.has(c)) info.set(c, { kind: new Map(), key: new Map(), acc: new Map(), ctype: new Map(), dist: new Set(), members: [] });
    const o = info.get(c);
    bump(o.kind, l.kind);
    if (l.key) bump(o.key, `${l.kind}|${l.key}`);
  });
  nodes.forEach((n) => {
    if (!n.comm) return;
    const o = info.get(n.comm);
    if (!o) return;
    o.members.push(n.id);
    if (n.district) o.dist.add(n.district);
    if (n.accused) bump(o.acc, n.accused);
    if (n.crimeHead || n.crimeGroup) bump(o.ctype, n.crimeHead || n.crimeGroup);
  });
  const topOf = (m) => [...m.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
  const shorten = (s, n = 18) => (s && s.length > n ? s.slice(0, n - 1) + "…" : s || "");
  let compsMeta = comps.map(([c, size]) => {
    const o = info.get(c) || { kind: new Map(), key: new Map(), acc: new Map(), ctype: new Map(), dist: new Set(), members: [] };
    const kind = topOf(o.kind);
    const rawKey = (topOf(o.key) || "").split("|")[1] || "";
    const topType = (topOf(o.ctype) || "Syndicate").replace(/_/g, " ");
    let name;
    if (kind === "repeat") name = `${aliasFor(topOf(o.acc)) || `${topType} offender`} network`;
    else if (kind === "cyber") name = `Cyber ring · ${shorten(rawKey, 16)}`;
    else if (kind === "ring") name = `${topType} ring · ${shorten(rawKey)}`;
    else name = `${topType} group`;
    return {
      id: c, size, kind, name,
      sub: `${size} FIRs · ${o.dist.size} district${o.dist.size > 1 ? "s" : ""}`,
      memberIds: o.members,
    };
  });

  // groupBy "type": reorganize the brain into crime-category bubbles (ref-2
  // poster look) — each category gets a phyllotaxis blob at a golden-angle
  // position, nodes take the category color, callouts name the category.
  // Evidence links stay on: lines crossing between bubbles = cross-type rings.
  if (groupBy === "type") {
    const byCat = new Map();
    nodes.forEach((n) => { (byCat.get(n.cat) || byCat.set(n.cat, []).get(n.cat)).push(n); });
    const catsSorted = [...byCat.entries()].sort((a, b) => b[1].length - a[1].length);
    compsMeta = catsSorted.map(([cat, arr], i) => {
      const blobR = 10 + Math.sqrt(arr.length) * 4.5;
      const ang = i * Math.PI * (3 - Math.sqrt(5));
      const R = 240 + blobR;
      const cx = Math.cos(ang) * R, cy = Math.sin(ang) * R;
      arr.forEach((n, j) => {
        const rr = blobR * Math.sqrt((j + 1) / arr.length);
        const th = j * 2.39996;
        n.tx = cx + Math.cos(th) * rr;
        n.ty = cy + Math.sin(th) * rr;
        n.x = n.tx; n.y = n.ty;
        if (n.role === "linked" || n.role === "dust") n.color = CATEGORIES[n.cat]?.color || "#5d6b80";
      });
      return {
        id: `cat:${cat}`, size: arr.length, kind: null,
        color: CATEGORIES[cat]?.color || "#9DABBC",
        name: CATEGORIES[cat]?.label || cat, sub: `${arr.length} FIRs`,
        memberIds: arr.map((n) => n.id),
      };
    });
  }

  const stats = {
    nodes: nodes.length,
    links: links.length,
    groups: comps.length,
    hubs: hubs.length,
    linked: nodes.filter((n) => n.comm).length,
    dust: nodes.filter((n) => !n.comm).length,
  };

  // Antar's learning/prediction agents ride inside the brain as their own
  // purple satellite clusters (ref: "My agent") — one hub + trailing dots
  // each, parked on a shell outside the dust ring. Think sends them flying
  // through the data.
  const AGENT_DEFS = [
    { id: "pattern", label: "Pattern Agent" },
    { id: "network", label: "Network Agent" },
    { id: "geo", label: "Geo Agent" },
    { id: "forecast", label: "Forecast Agent" },
  ];
  AGENT_DEFS.forEach((a, i) => {
    const ang = (i / AGENT_DEFS.length) * 2 * Math.PI + 0.8;
    const R = 565;
    nodes.push({
      id: `agent:${a.id}`, kind: "agent", role: "agent", agent: a.id, label: a.label, sub: "",
      cat: null, vsize: 8, ring: R, deg: 0, comm: null,
      x: Math.cos(ang) * R, y: Math.sin(ang) * R,
    });
    for (let s = 0; s < 6; s++) {
      const sa = ang + (s - 2.5) * 0.05;
      const sr = R + 24 + (s % 3) * 15;
      nodes.push({
        id: `agent:${a.id}:s${s}`, kind: "agent", role: "agentsat", agent: a.id, label: "", sub: "",
        cat: null, vsize: 1.7, ring: sr, deg: 0, comm: null,
        x: Math.cos(sa) * sr, y: Math.sin(sa) * sr,
      });
      links.push({ source: `agent:${a.id}`, target: `agent:${a.id}:s${s}`, kind: "agent" });
    }
  });

  return { nodes, links, apexId: apex, stats, comps: compsMeta };
}

/** Per-day counts for one year → GitHub-style heat grid (mockup's Case activity). */
export function dayGrid(recs, year) {
  const counts = new Map(); // "m-d" → n
  let max = 0;
  recs.forEach((r) => {
    if (r._year !== year || !r._month || !r._day) return;
    const k = `${r._month}-${r._day}`;
    const n = (counts.get(k) || 0) + 1;
    counts.set(k, n);
    if (n > max) max = n;
  });
  const startDow = new Date(year, 0, 1).getDay();
  const cells = [];
  for (let m = 1; m <= 12; m++) {
    const dim = new Date(year, m, 0).getDate();
    for (let d = 1; d <= dim; d++) {
      const doy = Math.floor((new Date(year, m - 1, d) - new Date(year, 0, 1)) / 86400e3);
      const idx = startDow + doy;
      cells.push({ m, d, n: counts.get(`${m}-${d}`) || 0, week: Math.floor(idx / 7), dow: idx % 7 });
    }
  }
  return { cells, max };
}

export function monthCounts(recs, year) {
  const out = new Array(12).fill(0);
  recs.forEach((r) => { if ((!year || r._year === year) && r._month) out[r._month - 1]++; });
  return out;
}

export function yearCounts(recs) {
  const m = new Map();
  recs.forEach((r) => { if (r._year) m.set(r._year, (m.get(r._year) || 0) + 1); });
  return [...m.entries()].sort((a, b) => a[0] - b[0]).map(([year, n]) => ({ year, n }));
}

const num = (v) => parseInt(v, 10) || 0;

/** Everything the Data Overview needs, computed in one pass. */
export function overviewStats(recs) {
  const districts = new Map(), stations = new Set(), cats = new Map();
  let victims = 0, accused = 0, arrested = 0, chargesheeted = 0, convictions = 0;
  recs.forEach((r) => {
    districts.set(r.District_Name, (districts.get(r.District_Name) || 0) + 1);
    stations.add(r.UnitName);
    cats.set(r._cat, (cats.get(r._cat) || 0) + 1);
    victims += num(r.Victim_Count); accused += num(r.Accused_Count);
    arrested += num(r.Arrested_Count); chargesheeted += num(r.Accused_ChargeSheeted_Count);
    convictions += num(r.Conviction_Count);
  });
  return {
    total: recs.length,
    districts: districts.size,
    stations: stations.size,
    victims, accused, arrested, chargesheeted, convictions,
    arrestRate: accused ? Math.round((arrested / accused) * 100) : 0,
    topDistricts: [...districts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10)
      .map(([district, n]) => ({ district, n })),
    byCategory: [...cats.entries()].sort((a, b) => b[1] - a[1])
      .map(([cat, n]) => ({ cat, label: CATEGORIES[cat]?.label || cat, color: CATEGORIES[cat]?.color || "#5d6b80", n })),
    years: yearCounts(recs),
  };
}

// Added back soften to fix compatibility with Constellation.jsx
const _soft = new Map();
export function soften(hex, sat = 0.7, light = 0.92) {
  if (!hex || typeof hex !== "string" || !hex.startsWith("#")) return hex;
  const key = `${hex}|${sat}|${light}`;
  if (_soft.has(key)) return _soft.get(key);
  let h = hex.slice(1);
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  const r = parseInt(h.slice(0, 2), 16) / 255, g = parseInt(h.slice(2, 4), 16) / 255, b = parseInt(h.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let H = 0, S = 0;
  const L = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    S = L > 0.5 ? d / (2 - max - min) : d / (max + min);
    H = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    H /= 6;
  }
  const s2 = S * sat, l2 = L * light;
  const q = l2 < 0.5 ? l2 * (1 + s2) : l2 + s2 - l2 * s2, p = 2 * l2 - q;
  const f = (t) => {
    t = t < 0 ? t + 1 : t > 1 ? t - 1 : t;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  const toHex = (v) => Math.round(Math.min(1, Math.max(0, v)) * 255).toString(16).padStart(2, "0");
  const out = s2 === 0 ? `#${toHex(l2)}${toHex(l2)}${toHex(l2)}` : `#${toHex(f(H + 1 / 3))}${toHex(f(H))}${toHex(f(H - 1 / 3))}`;
  _soft.set(key, out);
  return out;
}
