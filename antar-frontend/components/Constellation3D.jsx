"use client";

import { useEffect, useMemo, useRef } from "react";
import { buildConstellation, aliasFor, CATEGORIES, soften, AGENT_SHELL } from "@/lib/crimeGraph";

// 3D evidence globe - same data, order, grouping, colors and interactions as
// the 2D Constellation, rendered on 3d-force-graph (drag-rotate / zoom / click
// to select). Node/link semantics are identical; the flat leader-line group
// callouts are replaced by floating sprite labels on named nodes (WebGL-safe).

function linkWhy(l) {
  const key = l.key ? ` - ${l.key}` : "";
  if (l.kind === "repeat") return `Repeat offender: same accused${key}`;
  if (l.kind === "ring") return `Ring: shared place / vehicle${key}`;
  if (l.kind === "cyber") return `Cyber: shared UPI / IP${key}`;
  if (l.kind === "inferred") return `Predicted Edge (Inferred Link)${key}`;
  if (l.kind === "unsub") return `UNSUB Cluster Member${key}`;
  if (l.kind === "agent") return "Antar agent cluster - learns & predicts over this graph";
  return `Linked${key}`;
}

const ROLE_COLOR = {
  dust: "#566072", linked: "#2BB3A3", hub: "#E8A33D", top: "#18D69A",
  agent: "#FFFFFF", agentsat: "#00F5D4",
};
const LINK_BASE = "rgba(148,163,184,.22)";
const LINK_DIM = "rgba(148,163,184,.05)";
const LINK_AGENT = "rgba(0,245,212,.35)";
const golden = Math.PI * (3 - Math.sqrt(5));

// Tooltip HTML - identical to the 2D component so hover parity is preserved.
function nodeTooltip(n) {
  if (n.kind === "agent") {
    return `<div style="background:rgba(0,0,0,0.95); border:1px solid rgba(0,245,212,0.6); padding:10px 14px; border-radius:2px; box-shadow:0 8px 30px rgba(0,245,212,0.2); font:11px 'JetBrains Mono', monospace; color:#E2E8F0; text-transform:uppercase; letter-spacing:0.5px;">
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(0,245,212,0.3); padding-bottom:6px; margin-bottom:8px;">
        <b style="color:#00F5D4; font-size:13px; font-weight:700;">${n.label || "SYSTEM AGENT"}</b>
        <span style="color:#10B981; font-size:9px; font-weight:700;">● ACTIVE</span>
      </div>
      <div style="color:#94A3B8; font-size:10px; line-height:1.4;">Autonomous reasoning &amp; inference protocol.</div>
      <div style="margin-top:10px; background:rgba(0,245,212,0.1); border:1px solid rgba(0,245,212,0.3); padding:4px 8px; color:#00F5D4; font-weight:700; font-size:10px; text-align:center;">[ INSPECT LOGS ]</div>
    </div>`;
  }
  if (n.kind === "unsub") {
    return `<div style="background:rgba(15,10,25,0.96); border:1px solid rgba(168,85,247,0.6); padding:12px 15px; border-radius:8px; box-shadow:0 10px 30px rgba(0,0,0,0.9); font:12px Inter, sans-serif; color:#E9D5FF;"><b style="color:#C084FC; font-size:13px; font-family:'Chakra Petch', sans-serif;">${n.name || "UNSUB Profile"}</b><div style="margin-top:6px; color:#D8B4FE; font-size:11px;">SYNTHETIC INVESTIGATIVE PROFILE</div><div style="margin-top:6px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.1); font-size:11px; color:#CBD5E1;">Knowledge Boundary: <b>100% Gap (UNSUB)</b></div></div>`;
  }
  return `<div style="background:rgba(6,11,18,0.96); border:1px solid ${n.role === "top" ? "rgba(24,214,154,0.6)" : n.role === "hub" ? "rgba(232,163,61,0.6)" : "rgba(43,179,163,0.4)"}; padding:12px 15px; border-radius:8px; box-shadow:0 10px 30px rgba(0,0,0,0.9); font:12px Inter, sans-serif; color:#E2E8F0; max-width:300px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; gap:8px;">
        <b style="color:${n.role === "top" ? "#34EEB6" : n.role === "hub" ? "#FFC048" : "#22E6F0"}; font-size:13px; font-family:'Chakra Petch', sans-serif; text-transform:uppercase;">${n.crimeHead || n.crimeGroup || "FIR Record"}</b>
        ${n.stage ? `<span style="font-size:10px; background:rgba(255,255,255,0.08); padding:2px 6px; border-radius:4px; color:#A7F3D0; white-space:nowrap;">${n.stage}</span>` : ""}
      </div>
      <div style="color:#94A3B8; font-size:11px; margin-bottom:6px;">${n.zone || ""}${n.district && n.district !== n.zone ? `, ${n.district}` : ""} · ${n.year || "2026"}</div>
      ${n.accused ? `<div style="background:rgba(232,163,61,0.12); border-left:3px solid #E8A33D; padding:5px 8px; margin:6px 0; border-radius:0 4px 4px 0;"><span style="color:#FDE68A; font-weight:600;">${aliasFor(n.accused) || "Suspect"}</span> <span style="color:#94A3B8; font-family:'JetBrains Mono'; font-size:11px;">[${n.accused}]</span></div>` : ""}
      ${n.vehicle ? `<div style="color:#38BDF8; font-size:11px; margin-top:4px; font-family:'JetBrains Mono';">Getaway Veh: <b>${n.vehicle}</b></div>` : ""}
      ${n.mo ? `<div style="margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.1); font-size:11px; color:#CBD5E1; line-height:1.4;"><b>Explainable MO:</b><br/>${n.mo}</div>` : ""}
      ${n.role === "top" ? '<div style="margin-top:8px; font-size:11px; color:#34EEB6; font-weight:600;">MOST CONNECTED APEX HUB IN VIEW</div>' : n.role === "hub" ? '<div style="margin-top:8px; font-size:11px; color:#FFC048; font-weight:600;">KEY ACCUSED - HEAVILY LINKED IN SYNDICATE</div>' : n.comm ? '<div style="margin-top:8px; font-size:11px; color:#22E6F0; font-weight:600;">PART OF EVIDENCE-LINKED COMMUNITY</div>' : ""}
    </div>`;
}

// Floating text label as a camera-facing sprite (three CanvasTexture).
//
// 3d-force-graph re-runs nodeThreeObject for every node whenever ANY node accessor
// changes - every focus, filter toggle and search. Drawing a fresh canvas and uploading
// a new texture for each hub label on each of those was a visible stall. The texture and
// material depend only on the text, so build each one once and share it; a Sprite object
// itself is cheap and must stay unique per node (an Object3D has a single parent).
const LABEL_CACHE = new Map();

function makeLabelSprite(THREE, text, sub, color) {
  const key = `${text}|${sub}|${color}`;
  let entry = LABEL_CACHE.get(key);
  if (!entry) {
    if (LABEL_CACHE.size > 300) LABEL_CACHE.clear();   // bounded: labels change with the view
    const dpr = 2;
    const pad = 8 * dpr;
    const fs = 26 * dpr, subFs = 18 * dpr;
    const cvs = document.createElement("canvas");
    const ctx = cvs.getContext("2d");
    ctx.font = `600 ${fs}px Inter, sans-serif`;
    const w1 = ctx.measureText(text).width;
    ctx.font = `${subFs}px 'JetBrains Mono', monospace`;
    const w2 = sub ? ctx.measureText(`[${sub}]`).width : 0;
    const w = Math.max(w1, w2) + pad * 2;
    const h = (sub ? fs + subFs + 8 * dpr : fs) + pad * 2;
    cvs.width = w; cvs.height = h;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.shadowColor = "rgba(0,0,0,0.95)";
    ctx.shadowBlur = 6 * dpr;
    ctx.font = `600 ${fs}px Inter, sans-serif`;
    ctx.fillStyle = color || "#FFFFFF";
    ctx.fillText(text, w / 2, sub ? pad + fs / 2 : h / 2);
    if (sub) {
      ctx.font = `${subFs}px 'JetBrains Mono', monospace`;
      ctx.fillStyle = "#CBD5E1";
      ctx.fillText(`[${sub}]`, w / 2, pad + fs + 4 * dpr + subFs / 2);
    }
    const tex = new THREE.CanvasTexture(cvs);
    tex.minFilter = THREE.LinearFilter;
    const scale = 0.35;
    entry = {
      material: new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }),
      sx: (w / dpr) * scale,
      sy: (h / dpr) * scale,
    };
    LABEL_CACHE.set(key, entry);
  }
  const sprite = new THREE.Sprite(entry.material);
  sprite.scale.set(entry.sx, entry.sy, 1);
  return sprite;
}

// Physics settles in ~5s; it used to run for 9s after every rebuild.
const COOLDOWN_MS = 5000;

// ── Filled-ball layout ──────────────────────────────────────────────────────
// The original organic brain - crime-type clumps, evidence links that pull related FIRs
// together, live physics - but shaped as a solid ball instead of a flat disc. Clumps are
// placed THROUGH the volume (largest at the core, the rest on shells around it), each
// clump is itself a small 3D ball, and a soft wall keeps every node inside radius R.
const ballRadius = (n) => Math.max(200, Math.sqrt(n) * 5.6);   // 3.4k FIRs → ~325

// ── Size by role: what matters is big, what is context is small ─────────────
// Before, every node rendered at nearly the same size (radius ~4.6–8.3), so 3,000 dots
// competed equally for attention. Now the key accused and the most-connected node stand
// out, evidence-linked FIRs are small, and isolated FIRs are specks.
const NODE_REL_SIZE = 2.4;
function sizeFor(n) {
  if (n.kind === "agent") return n.role === "agent" ? 16 : 1.2;
  if (n.kind === "unsub") return 8;
  if (n.role === "top") return 60;      // most connected in view
  if (n.role === "hub") return 30;      // key accused
  if (n.comm || n.role === "linked") return 2.2;
  return 0.55;                          // isolated FIR (no shared evidence)
}

// Isolated FIRs keep their crime colour but at low strength, so the eye goes to the
// linked structure first - calmer, and the colour still says which crime it is.
const _dimCache = new Map();
function dimmed(hex, alpha) {
  const k = hex + alpha;
  if (_dimCache.has(k)) return _dimCache.get(k);
  const h = String(hex || "#566072").replace("#", "");
  const f = h.length === 3 ? h.split("").map((c) => c + c).join("") : h.padEnd(6, "0");
  const v = `rgba(${parseInt(f.slice(0, 2), 16)},${parseInt(f.slice(2, 4), 16)},${parseInt(f.slice(4, 6), 16)},${alpha})`;
  _dimCache.set(k, v);
  return v;
}

// Deterministic 0..1 from a node id, so the ball looks the same on every visit.
function unitHash(str, salt) {
  let h = 2166136261 ^ salt;
  for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
  return ((h >>> 0) % 100000) / 100000;
}

function pointInBall(id, r) {
  // uniform in a ball: direction from two hashes, radius by cube root
  const u = unitHash(id, 1), v = unitHash(id, 2), w = unitHash(id, 3);
  const th = 2 * Math.PI * u, ph = Math.acos(2 * v - 1), rr = r * Math.cbrt(w);
  return [rr * Math.sin(ph) * Math.cos(th), rr * Math.cos(ph), rr * Math.sin(ph) * Math.sin(th)];
}

// Camera distance at which a ball of radius r fills ~80% of the view height.
function fitDistance(r) {
  return (r * 1.25) / Math.tan((40 / 2) * (Math.PI / 180));
}

// Park the four agent clusters on a shell just outside the brain, spread over the sphere
// rather than around the equator.
//
// Two things were wrong before. The shell was a hardcoded 565 while the ball is ~331, so
// the agents sat far out in empty space; and every one of them had z=0, so from the
// default camera they were four specks pinned to the screen edges instead of bodies
// orbiting a brain. Fibonacci placement spreads the hubs evenly over a real sphere, and
// each cluster's satellites sit in a tight halo around ITS hub - so a cluster reads as one
// object with a tail, which is what the tethers are drawing.
function layoutAgents(nodes, R) {
  const hubs = nodes.filter((n) => n.role === "agent");
  const shell = R * AGENT_SHELL;
  hubs.forEach((hub, i) => {
    // Offset the polar angle by half a step so no hub lands exactly on a pole, where it
    // would overlap the camera's up-axis and look pinned.
    const y = 1 - (2 * (i + 0.5)) / Math.max(1, hubs.length);
    const rr = Math.sqrt(Math.max(0, 1 - y * y));
    const th = golden * i;
    const hx = Math.cos(th) * rr * shell, hy = y * shell, hz = Math.sin(th) * rr * shell;
    hub.x = hx; hub.y = hy; hub.z = hz;
    hub.ring = shell;

    const sats = nodes.filter((m) => m.role === "agentsat" && m.agent === hub.agent);
    sats.forEach((s, j) => {
      // A small ball around the hub, deterministic so the cluster looks the same on every
      // visit, and scaled to the hub's size so it stays a halo rather than a cloud.
      const [dx, dy, dz] = pointInBall(String(s.id), R * 0.085);
      s.x = hx + dx; s.y = hy + dy; s.z = hz + dz;
      s.ring = Math.hypot(s.x, s.y, s.z);
      s.homeX = s.x; s.homeY = s.y; s.homeZ = s.z;
      void j;
    });
    hub.homeX = hx; hub.homeY = hy; hub.homeZ = hz;
  });
}

function layoutBall(nodes, groupBy) {
  const firs = nodes.filter((n) => n.kind !== "agent");
  const R = ballRadius(firs.length || 1);
  layoutAgents(nodes, R);
  if (groupBy === "type") {
    const byCat = new Map();
    firs.forEach((n) => { (byCat.get(n.cat) || byCat.set(n.cat, []).get(n.cat)).push(n); });
    const cats = [...byCat.entries()].sort((a, b) => b[1].length - a[1].length);
    const golden = Math.PI * (3 - Math.sqrt(5));
    const outer = Math.max(1, cats.length - 1);
    cats.forEach(([, arr], i) => {
      // largest clump at the core; the others spread over a shell at 58% of the radius
      let cx = 0, cy = 0, cz = 0;
      if (i > 0) {
        const y = 1 - (2 * (i - 0.5)) / outer, rr = Math.sqrt(Math.max(0, 1 - y * y)), th = golden * i;
        cx = Math.cos(th) * rr * R * 0.58; cy = y * R * 0.58; cz = Math.sin(th) * rr * R * 0.58;
      }
      const blobR = Math.min(R * 0.42, 14 + Math.cbrt(arr.length) * 11);
      arr.forEach((n) => {
        const [dx, dy, dz] = pointInBall(String(n.id), blobR);
        n.tx = cx + dx; n.ty = cy + dy; n.tz = cz + dz;
        n.x = n.tx; n.y = n.ty; n.z = n.tz;
      });
    });
  } else {
    // Evidence: the original shells (core / ring / dust by n.ring), filled in depth.
    firs.forEach((n) => {
      delete n.tx; delete n.ty; delete n.tz;
      const [dx, dy, dz] = pointInBall(String(n.id), n.ring || R);
      const len = Math.hypot(dx, dy, dz) || 1, rr = Math.min(n.ring || R, R);
      n.x = (dx / len) * rr; n.y = (dy / len) * rr; n.z = (dz / len) * rr;
    });
  }
  return { nodes, R };
}
// d3-force's default; raised only while the agents fly so the rest of the brain holds still.
const VELOCITY_DECAY = 0.4;

export default function Constellation3D({ graph, groupBy = "evidence", active, kinds, controlRef, onFocus, onStats, onAgent, focusId, legendFocus }) {
  const containerRef = useRef(null);
  const fgRef = useRef(null);
  const threeRef = useRef(null);
  const focusRef = useRef(null);
  const activeRef = useRef(active);
  const kindsRef = useRef(kinds);
  const groupByRef = useRef(groupBy);
  const dataRef = useRef(null);
  const flightRef = useRef(null);
  const lastGroupRef = useRef(null);   // grouping the camera was last framed for
  const labelSetRef = useRef(null);    // hub ids allowed a floating name (see nodeThreeObject)
  const legendFocusRef = useRef(legendFocus);

  // External control imperative handle
  useEffect(() => {
    if (controlRef) {
      controlRef.current = {
        clear: clearFocus,
        fg: () => fgRef.current,
      };
    }
  }, [controlRef]); // eslint-disable-line

  const constel = useMemo(() => (graph ? buildConstellation(graph, { groupBy }) : null), [graph, groupBy]);

  // Which hubs get a floating name in the unfocused view: the apex, then the heaviest by
  // degree. Ten is what fits around a ball this size before names start crossing.
  const MAX_HUB_LABELS = 10;
  function pickLabels(nodes) {
    const named = nodes.filter((n) => (n.role === "top" || n.role === "hub") && n.label);
    named.sort((a, b) => (a.role === "top" ? -1 : b.role === "top" ? 1 : (b.deg || 0) - (a.deg || 0)));
    labelSetRef.current = new Set(named.slice(0, MAX_HUB_LABELS).map((n) => n.id));
  }

  useEffect(() => { activeRef.current = active; refreshVisuals(); }, [active]);      // eslint-disable-line
  useEffect(() => { kindsRef.current = kinds; refreshVisuals(); }, [kinds]);         // eslint-disable-line
  useEffect(() => { groupByRef.current = groupBy; }, [groupBy]);
  useEffect(() => { legendFocusRef.current = legendFocus; refreshVisuals(); }, [legendFocus]);
  useEffect(() => { if (constel) onStats?.(constel.stats); }, [constel, onStats]);

  const matchesLegend = (n) => {
    const lf = legendFocusRef.current;
    if (!lf) return true;
    if (lf === "comm") return n.comm === true;
    if (lf === "dust") return n.role === "dust" || !n.comm;
    if (lf === "agent") return n.kind === "agent";
    return n.role === lf;
  };

  const nodeColor = (n) => {
    const lf = legendFocusRef.current;
    if (lf && !matchesLegend(n)) return "rgba(77,90,112,0.05)";
    if (focusRef.current && !focusRef.current.has(n.id)) return "rgba(77,90,112,0.12)";
    // Softer palette: same hue per crime, less saturation (lib/crimeGraph soften).
    const base = soften(n.color || ROLE_COLOR[n.role] || ROLE_COLOR.dust);
    if (n.kind !== "agent" && n.role !== "top" && n.role !== "hub" && !n.comm && String(base).startsWith("#")) {
      return dimmed(base, 0.38);          // isolated FIR: present, not shouting
    }
    return base;
  };
  const nodeVisible = (n) => {
    // If filtering by legend, we still render nodes (but heavily dimmed via nodeColor) to keep the graph shape
    return n.kind === "agent" || activeRef.current == null || activeRef.current.has(n.cat);
  };
  const linkColor = (l) => {
    const lf = legendFocusRef.current;
    if (lf && lf !== "line" && lf !== "agent") return "rgba(77,90,112,0.05)";
    if (l.kind === "agent") return LINK_AGENT;
    if (l.kind === "inferred") return "rgba(192,132,252,0.85)";
    if (l.kind === "unsub") return "rgba(168,85,247,0.85)";
    const s = typeof l.source === "object" ? l.source : null;
    return focusRef.current && s && !focusRef.current.has(s.id) ? LINK_DIM : LINK_BASE;
  };
  const linkVisible = (l) => l.kind === "agent" || kindsRef.current?.has(l.kind);
  // A travelling particle is a mesh moved every frame. One on every evidence link meant
  // thousands of per-frame updates on the default view, mostly on links nobody was
  // looking at. Keep them where they carry meaning: the agent tethers, and the links
  // inside a focused group, where the flow is what you are reading.
  const particlesFor = (l) => {
    if (l.kind === "agent") return 2;
    const f = focusRef.current;
    if (!f) return 0;
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    return f.has(s) && f.has(t) ? 2 : 0;
  };

  function refreshVisuals() {
    const fg = fgRef.current;
    if (!fg) return;
    fg.nodeColor(nodeColor).nodeVisibility(nodeVisible).linkColor(linkColor).linkVisibility(linkVisible)
      .linkDirectionalParticles(particlesFor);
  }

  function focusComponent(n) {
    const fg = fgRef.current;
    if (!fg || !dataRef.current) return;
    const members = n.comm ? dataRef.current.nodes.filter((m) => m.comm === n.comm) : [n];
    focusRef.current = new Set(members.map((m) => m.id));

    const whys = [], seen = new Set();
    dataRef.current.links.forEach((l) => {
      const sid = typeof l.source === "object" ? l.source.id : l.source;
      const tid = typeof l.target === "object" ? l.target.id : l.target;
      if (!focusRef.current.has(sid) || !focusRef.current.has(tid)) return;
      const w = linkWhy(l);
      if (!seen.has(w)) { seen.add(w); whys.push({ kind: l.kind, text: w }); }
    });
    const catCount = new Map(); const districts = new Set();
    let yMin = Infinity, yMax = -Infinity;
    members.forEach((m) => {
      catCount.set(m.cat, (catCount.get(m.cat) || 0) + 1);
      if (m.district) districts.add(m.district);
      const y = parseInt(m.year, 10);
      if (y) { yMin = Math.min(yMin, y); yMax = Math.max(yMax, y); }
    });
    const cats = [...catCount.entries()].sort((a, b) => b[1] - a[1])
      .map(([cat, count]) => ({ cat, n: count, label: CATEGORIES[cat]?.label || cat, color: CATEGORIES[cat]?.color || "#5d6b80" }));
    const people = [...new Set(members.map((m) => m.accused).filter(Boolean))]
      .slice(0, 3).map((id) => ({ id, name: aliasFor(id) }));
    const rows = [...members].sort((a, b) => (b.deg || 0) - (a.deg || 0)).slice(0, 4)
      .map((m) => ({ crime: m.crimeHead || m.crimeGroup, zone: m.zone, year: m.year }));

    onFocus?.({
      node: n,
      whys: whys.slice(0, 4),
      comp: { size: members.length, cats, people, rows, districts: [...districts], years: yMin <= yMax ? [yMin, yMax] : null },
    });

    // Camera fly to the group centroid (3D)
    let cx = 0, cy = 0, cz = 0, r = 0;
    members.forEach((m) => { cx += m.x || 0; cy += m.y || 0; cz += m.z || 0; });
    cx /= members.length; cy /= members.length; cz /= members.length;
    members.forEach((m) => { r = Math.max(r, Math.hypot((m.x || 0) - cx, (m.y || 0) - cy, (m.z || 0) - cz)); });
    const dist = r * 2.4 + 90;
    const base = Math.hypot(cx, cy, cz) || 1;
    const ratio = (base + dist) / base;
    fg.cameraPosition({ x: cx * ratio, y: cy * ratio, z: cz * ratio }, { x: cx, y: cy, z: cz }, 800);
    refreshVisuals();
  }

  function clearFocus() {
    focusRef.current = null;
    onFocus?.(null);
    refreshVisuals();
    // Back to the framing the intro landed on, not a hardcoded 980 - which was right for
    // one graph size and wrong for every other, so releasing a focus could leave the brain
    // either clipped or a speck.
    const firs = (dataRef.current?.nodes || []).filter((m) => m.kind !== "agent").length;
    fgRef.current?.cameraPosition(
      { x: 0, y: 0, z: fitDistance(ballRadius(firs || 1) * AGENT_SHELL) }, { x: 0, y: 0, z: 0 }, 900);
  }

  // Think-flight: each agent hub dives through the data and back out, its satellites
  // trailing behind like a comet tail, and all of them land exactly where they started.
  //
  // The old loop called d3ReheatSimulation() every 400ms. A reheat resets alpha to 1 for
  // the WHOLE graph, so all ~3,400 nodes were shoved back into motion eight times per
  // flight - that was the stutter. Now the simulation is heated once, with velocity decay
  // raised so everything that isn't an agent barely moves, and the agents are steered by
  // pinning (fx/fy/fz) along a closed path each frame.
  function flyAgents(duration = 2600) {
    const fg = fgRef.current;
    if (!fg || !dataRef.current) return;
    if (flightRef.current) cancelAnimationFrame(flightRef.current);
    const movers = dataRef.current.nodes.filter((m) => m.kind === "agent");
    if (!movers.length) return;

    const hubOrder = new Map();
    movers.forEach((m) => { if (m.role === "agent" && !hubOrder.has(m.agent)) hubOrder.set(m.agent, hubOrder.size); });
    const plan = movers.map((m) => {
      const x = m.x || 0, y = m.y || 0, z = m.z || 0;
      const r0 = Math.hypot(x, y, z) || m.ring || 565;
      const sat = m.role === "agentsat" ? (Number(String(m.id).split(":s")[1]) || 0) + 1 : 0;
      return {
        m, r0,
        a0: Math.atan2(y, x),
        e0: Math.asin(Math.max(-1, Math.min(1, z / r0))),
        dir: (hubOrder.get(m.agent) ?? 0) % 2 ? -1 : 1,
        lag: sat * 0.035,          // satellites start later and catch up by the end
      };
    });

    const canDamp = typeof fg.d3VelocityDecay === "function";
    if (canDamp) fg.d3VelocityDecay(0.9);
    fg.cooldownTime(duration + 2500);   // keep ticking long enough to land them
    fg.d3ReheatSimulation();

    const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
    const t0 = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - t0) / duration);
      for (const p of plan) {
        const e = ease(Math.max(0, Math.min(1, (t - p.lag) / (1 - p.lag))));
        // Two full turns, a dive to r=150 and a vertical swing - every term returns to
        // its starting value at e=1, so nothing snaps when the pins are released.
        const a = p.a0 + e * Math.PI * 4 * p.dir;
        const r = p.r0 - (p.r0 - 150) * Math.sin(Math.PI * e);
        const el = p.e0 + Math.sin(Math.PI * 2 * e) * 0.45;
        p.m.fx = Math.cos(a) * Math.cos(el) * r;
        p.m.fy = Math.sin(a) * Math.cos(el) * r;
        p.m.fz = Math.sin(el) * r;
      }
      if (t < 1) { flightRef.current = requestAnimationFrame(tick); return; }
      plan.forEach(({ m }) => { delete m.fx; delete m.fy; delete m.fz; });
      if (canDamp) fg.d3VelocityDecay(VELOCITY_DECAY);
      flightRef.current = null;
      setTimeout(() => fgRef.current?.cooldownTime(COOLDOWN_MS), 2500);
    };
    flightRef.current = requestAnimationFrame(tick);
  }

  // A short orbit when the crime filter changes.
  //
  // Changing the crime type re-colours most of the ball at once, and a silent re-paint
  // reads as a glitch: the officer cannot tell whether the view responded or something
  // broke. A single smooth quarter-turn is the cheapest possible "yes, that applied" — the
  // brain turns, and the same dots arrive in their new colours while it is moving.
  //
  // It drives the camera around a fixed target rather than rotating the graph, so no node
  // position changes and the physics never has to re-settle.
  function spinToFilter(turns = 0.28, duration = 900) {
    const fg = fgRef.current;
    if (!fg) return;
    const reduce = typeof window !== "undefined"
      && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const cam = fg.cameraPosition();
    const r = Math.hypot(cam.x, cam.z) || fitDistance(ballRadius(1));
    if (reduce) return;                       // the colour change alone is the feedback
    const a0 = Math.atan2(cam.z, cam.x);
    const a1 = a0 + Math.PI * 2 * turns;
    fg.cameraPosition({ x: Math.cos(a1) * r, y: cam.y, z: Math.sin(a1) * r },
                      { x: 0, y: 0, z: 0 }, duration);
  }

  // Build once
  useEffect(() => {
    if (!constel || !containerRef.current || fgRef.current) return;
    let destroyed = false;
    Promise.all([import("3d-force-graph"), import("three")]).then(([{ default: ForceGraph3D }, THREE]) => {
      if (destroyed || !containerRef.current || fgRef.current) return;
      threeRef.current = THREE;

      const validNodeIds = new Set(constel.nodes.map(n => n.id));
      dataRef.current = {
        nodes: layoutBall(constel.nodes.map((n) => ({ ...n })), groupByRef.current).nodes,
        links: constel.links.filter((l) => validNodeIds.has(l.source?.id || l.source) && validNodeIds.has(l.target?.id || l.target)).map((l) => ({ ...l, source: l.source.id || l.source, target: l.target.id || l.target })),
      };
      pickLabels(dataRef.current.nodes);

      const fg = ForceGraph3D()(containerRef.current)
        .width(containerRef.current.offsetWidth)
        .height(containerRef.current.offsetHeight)
        .backgroundColor("rgba(0,0,0,0)")
        .showNavInfo(false)
        .nodeId("id")
        .nodeRelSize(NODE_REL_SIZE)
        .nodeVal(sizeFor)
        // ~3,400 spheres: 6 segments reads identically at this size and halves the
        // vertex count of the default 8.
        .nodeResolution(6)
        .nodeColor(nodeColor)
        .nodeVisibility(nodeVisible)
        // 1, not 0.92. A sub-1 opacity made EVERY node material transparent, which
        // costs a depth sort of all transparent meshes per frame. Focus-dimmed nodes
        // still fade: their colour carries its own alpha.
        .nodeOpacity(1)
        .nodeLabel(nodeTooltip)
        .nodeThreeObjectExtend(true)
        .nodeThreeObject((n) => {
          if (focusRef.current && !focusRef.current.has(n.id)) return null;
          let text = "", sub = "", color = "#FFFFFF";
          if (n.kind === "agent" && n.label) { text = n.label; color = "#00F5D4"; }
          else if (n.kind === "unsub") { text = n.name || "UNSUB"; color = "#E9D5FF"; }
          else if (n.role === "top" || n.role === "hub") {
            // Only the hubs that earned a name. Every hub carrying a label meant dozens of
            // sprites stacked over one ball, and the names crossed each other into an
            // unreadable smear - worse than no labels, because a half-covered name still
            // looks like it is telling you something. Outside a focused group the view
            // keeps the apex plus the few heaviest hubs; click a group and every name in
            // THAT group comes back, which is when an officer actually wants them.
            if (!focusRef.current && !labelSetRef.current?.has(n.id)) return null;
            text = n.label || ""; sub = n.sub || "";
            color = n.role === "top" ? "#34EEB6" : "#FFFFFF";
          }
          if (!text) return null;
          const sprite = makeLabelSprite(THREE, text, sub, color);
          // Clear the node's own drawn radius, not a guessed constant: 3d-force-graph draws
          // a sphere of cbrt(nodeVal) * nodeRelSize, so the apex (val 60) is ~9.4 units and
          // a `+6` offset put the text inside the ball it was naming.
          sprite.position.set(0, Math.cbrt(sizeFor(n)) * NODE_REL_SIZE + 7, 0);
          return sprite;
        })
        .linkColor(linkColor)
        .linkVisibility(linkVisible)
        .linkWidth((l) => (l.kind === "agent" ? 0.5 : l.kind === "inferred" || l.kind === "unsub" ? 0.6 : 0.8))
        .linkOpacity(0.55)
        .linkDirectionalParticles(particlesFor)
        .linkDirectionalParticleSpeed((l) => l.kind === "agent" ? 0.015 : 0.006)
        .linkDirectionalParticleWidth(1.8)
        .linkDirectionalParticleColor(() => "rgba(255,255,255,0.9)")
        .linkLabel((l) => `<div style="background:rgba(6,11,18,0.94); border:1px solid rgba(255,140,66,0.4); padding:5px 9px; border-radius:6px; font:11px 'JetBrains Mono', monospace; color:#FFB020; box-shadow:0 6px 16px rgba(0,0,0,0.85);">${linkWhy(l)}</div>`)
        .onNodeClick((n) => {
          if (n.kind === "agent") { onAgent?.(n.agent); return; }
          focusComponent(n);
        })
        .onBackgroundClick(() => { if (focusRef.current) clearFocus(); })
        // Nodes arrive pre-positioned on their targets (buildConstellation sets x/y), so
        // the synchronous warm-up - which blocks the main thread before first paint —
        // needs far fewer ticks than the 60 it had.
        .warmupTicks(30)
        .cooldownTime(COOLDOWN_MS);

      fg.d3Force("charge").strength(-45);
      const linkForce = fg.d3Force("link");
      if (linkForce) linkForce.distance(40);
      // Original organic physics, shaped as a ball: crime-type mode pulls each node to its
      // clump target in 3D (layoutBall), evidence mode keeps the core/ring/dust shells, and
      // a soft wall below keeps everything inside the ball's radius.
      // FIR count only. The agents live OUTSIDE this wall by design, so counting them
      // inflated the very radius they are placed relative to.
      const wallR = ballRadius((dataRef.current?.nodes || []).filter((m) => m.kind !== "agent").length || 1);
      const radial3 = (alpha) => {
        const ns = dataRef.current?.nodes || [];
        for (const m of ns) {
          if (m.kind === "agent") {
            // Hold each agent at the place layoutAgents put it. The radial pull below only
            // fixes distance, not direction, so charge repulsion from ~3.4k FIRs slowly
            // pushed the clusters apart and smeared the satellite halos. A weak spring to
            // home keeps a cluster a cluster, and it is released outright while Think is
            // flying them (fx/fy/fz pins win over any force).
            if (m.homeX != null && m.fx == null) {
              const k = alpha * 0.22;
              m.vx += (m.homeX - (m.x || 0)) * k;
              m.vy += (m.homeY - (m.y || 0)) * k;
              m.vz += (m.homeZ - (m.z || 0)) * k;
            }
            continue;
          }
          {
            // Hard boundary: a node past the wall is put back on it and loses its outward
            // speed. A soft push lost to ~3k repelling nodes and the ball overflowed the
            // screen on large displays.
            const r0 = Math.hypot(m.x || 0, m.y || 0, m.z || 0);
            if (r0 > wallR) {
              const k = wallR / r0;
              m.x *= k; m.y *= k; m.z = (m.z || 0) * k;
              const out = ((m.vx || 0) * m.x + (m.vy || 0) * m.y + (m.vz || 0) * m.z) / (wallR || 1);
              if (out > 0) {
                m.vx -= (m.x / wallR) * out; m.vy -= (m.y / wallR) * out; m.vz -= (m.z / wallR) * out;
              }
            }
          }
          if (groupByRef.current === "type" && m.tx != null) {
            const k = alpha * 0.12;
            m.vx += (m.tx - m.x) * k;
            m.vy += (m.ty - m.y) * k;
            m.vz += ((m.tz ?? 0) - (m.z || 0)) * k;
          } else {
            const r = Math.hypot(m.x || 0, m.y || 0, m.z || 0) || 1;
            const k = (((m.ring || 300) - r) / r) * alpha * 0.15;
            m.vx += (m.x || 0) * k;
            m.vy += (m.y || 0) * k;
            m.vz += (m.z || 0) * k;
          }
        }
      };
      radial3.initialize = () => {};
      fg.d3Force("center", null);
      fg.d3Force("radial3", radial3);

      fg.graphData(dataRef.current);
      fgRef.current = fg;
      lastGroupRef.current = groupByRef.current;

      // Intro. The camera used to start at z=3500 and crawl in over NINE SECONDS - the
      // "slow brain" on every visit, since Crime-type is the default grouping. A short
      // settle-in keeps the sense of arrival without making the officer wait for it.
      // Arrival: the brain fades in while the camera flies from deep space to a distance
      // that fits the whole ball (radius from the wall, 40° vertical field of view, with
      // margin for labels). Honours prefers-reduced-motion.
      // Frame the AGENT shell, not just the ball - the agents now orbit at AGENT_SHELL x
      // the radius, and framing the ball alone left them cropped at the edges of the view.
      const fitZ = fitDistance(wallR * AGENT_SHELL);
      const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      // Arrival: a single clean zoom IN to the brain. It starts further out and slightly
      // above the equator, so the ball reads as a sphere during the approach rather than a
      // flat disc that grows. The fade runs shorter than the flight, so the brain is fully
      // visible while it is still moving — the motion is the arrival, not a reveal.
      fg.cameraPosition(
        reduce ? { x: 0, y: 0, z: fitZ }
               : { x: 0, y: fitZ * 0.42, z: fitZ * 2.6 },
        { x: 0, y: 0, z: 0 }, 0);
      const canvasEl = containerRef.current;
      if (canvasEl && !reduce) {
        canvasEl.style.opacity = "0";
        canvasEl.style.transition = "opacity 520ms cubic-bezier(.22,.61,.36,1)";
        requestAnimationFrame(() => { canvasEl.style.opacity = "1"; });
      }

      // The arrival used to stutter because three things ran at once: the camera tween,
      // the force simulation still settling, and auto-rotate - which was switched on at
      // 100ms, i.e. DURING the fly-in. Auto-rotate moves the camera by mutating the same
      // controls the tween is driving, so the two fought each other every frame and the
      // approach visibly juddered. Now the flight happens alone, and the rotation starts
      // only once it has landed.
      // 1700ms reads as deliberate rather than slow, and the library eases the tween, so
      // the last third of the approach naturally settles instead of stopping dead.
      const FLY_MS = 1700;
      if (!reduce) {
        setTimeout(() => fg.cameraPosition({ x: 0, y: 0, z: fitZ }, { x: 0, y: 0, z: 0 },
                                           FLY_MS), 80);
      }
      setTimeout(() => {
        if (fg.controls) {
          const controls = fg.controls();
          controls.autoRotate = true;
          controls.autoRotateSpeed = 0.35;
          // Damping is what turns a drag into a glide instead of a snap. It has to be
          // enabled on the controls themselves, and it only takes effect if something
          // calls controls.update() each frame - 3d-force-graph's render loop does.
          controls.enableDamping = true;
          controls.dampingFactor = 0.12;
        }
      }, reduce ? 0 : 100 + FLY_MS + 120);

      // Bloom: the one change that makes this read as an instrument rather than a scatter
      // plot. The apex, the key accused and the agent tethers are the only things bright
      // enough to trip the threshold, so they glow and the 3,000 specks of context do not
      // - the emphasis lands exactly where the size ramp already puts it. Loaded lazily so
      // it never enters the first bundle, and skipped entirely under reduced-motion, where
      // a full-screen post pass is the wrong trade.
      if (!reduce) {
        import("three/examples/jsm/postprocessing/UnrealBloomPass.js")
          .then(({ UnrealBloomPass }) => {
            if (destroyed || fgRef.current !== fg) return;
            const el = containerRef.current;
            const bloom = new UnrealBloomPass(
              new THREE.Vector2(el?.offsetWidth || 1280, el?.offsetHeight || 720),
              0.72,   // strength - enough to halo the hubs, not enough to wash out labels
              0.85,   // radius
              0.62,   // threshold: only the bright nodes and tethers qualify
            );
            fg.postProcessingComposer().addPass(bloom);
          })
          .catch(() => {});   // a missing post-processing module must never break the graph
      }
    });
    return () => {
      destroyed = true;
      if (flightRef.current) cancelAnimationFrame(flightRef.current);
      try { fgRef.current?._destructor?.(); } catch {}
      fgRef.current = null;
    };
  }, [constel === null]); // eslint-disable-line

  // Morph on data change (timeline / filters / groupBy)
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || !constel) return;
    focusRef.current = null;
    onFocus?.(null);
    const validNodeIds = new Set(constel.nodes.map(n => n.id));
    dataRef.current = {
      nodes: layoutBall(constel.nodes.map((n) => ({ ...n })), groupByRef.current).nodes,
      links: constel.links.filter((l) => validNodeIds.has(l.source?.id || l.source) && validNodeIds.has(l.target?.id || l.target)).map((l) => ({ ...l, source: l.source.id || l.source, target: l.target.id || l.target })),
    };
    pickLabels(dataRef.current.nodes);
    fg.graphData(dataRef.current);
    refreshVisuals();

    // Re-frame only when it helps. Every year pick, day click and filter toggle used to
    // throw the camera back out to z=3500 and replay the nine-second crawl - including
    // the rebuild when predicted edges arrive from the backend a moment after load,
    // which restarted the intro the officer had just watched. In Crime-type mode the
    // category blobs sit in the same places across filters, so the camera stays put
    // unless the grouping itself changed. Evidence mode's radius depends on the data,
    // so that still refits - quickly.
    const groupChanged = lastGroupRef.current !== groupByRef.current;
    lastGroupRef.current = groupByRef.current;
    if (groupChanged) {
      const firCount = dataRef.current.nodes.filter((m) => m.kind !== "agent").length;
      fg.cameraPosition({ x: 0, y: 0, z: fitDistance(ballRadius(firCount || 1) * AGENT_SHELL) },
                        { x: 0, y: 0, z: 0 }, 900);
    }
  }, [constel]); // eslint-disable-line

  // Parent controls (parity with the 2D component)
  useEffect(() => {
    if (!controlRef) return;
    controlRef.current = {
      clear: clearFocus,
      refit: () => fgRef.current?.zoomToFit(700, 90),
      think: flyAgents,
      spin: spinToFilter,
      find: (q) => {
        const needle = String(q || "").trim().toLowerCase();
        if (!needle || !dataRef.current) return false;
        const score = (m) => (m.role === "hub" || m.role === "top" ? 2 : m.comm ? 1 : 0);
        let found = null;
        dataRef.current.nodes.forEach((m) => {
          if (m.kind === "agent") return;
          const hay = [m.accused, m.accused && aliasFor(m.accused), m.zone, m.district, m.crimeHead, m.crimeGroup];
          if (!hay.some((v) => v && String(v).toLowerCase().includes(needle))) return;
          if (!found || score(m) > score(found)) found = m;
        });
        if (found) focusComponent(found);
        return !!found;
      },
    };
  });

  useEffect(() => {
    if (!focusId || !constel) return;
    const t = setTimeout(() => controlRef?.current?.find?.(focusId), 1600);
    return () => clearTimeout(t);
  }, [focusId, constel]); // eslint-disable-line

  useEffect(() => {
    const onResize = () => {
      const el = containerRef.current;
      if (el && fgRef.current) fgRef.current.width(el.offsetWidth).height(el.offsetHeight);
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return <div ref={containerRef} className="bsx-3d-canvas" />;
}
