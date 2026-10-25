"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { buildConstellation, aliasFor, CATEGORIES, groupProfile } from "@/lib/crimeGraph";

// 3D evidence globe — same data, order, grouping, colors and interactions as
// the 2D Constellation, rendered on 3d-force-graph (drag-rotate / zoom / click
// to select). Node/link semantics are identical; the flat leader-line group
// callouts are replaced by floating sprite labels on named nodes (WebGL-safe).

function linkWhy(l) {
  const key = l.key ? ` — ${l.key}` : "";
  if (l.kind === "repeat") return `Repeat offender: same accused${key}`;
  if (l.kind === "ring") return `Ring: shared place / vehicle${key}`;
  if (l.kind === "cyber") return `Cyber: shared UPI / IP${key}`;
  if (l.kind === "inferred") return `Predicted Edge (Inferred Link)${key}`;
  if (l.kind === "unsub") return `UNSUB Cluster Member${key}`;
  if (l.kind === "agent") return "Antar agent cluster — learns & predicts over this graph";
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

// Tooltip HTML — identical to the 2D component so hover parity is preserved.
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
      ${n.role === "top" ? '<div style="margin-top:8px; font-size:11px; color:#34EEB6; font-weight:600;">MOST CONNECTED APEX HUB IN VIEW</div>' : n.role === "hub" ? '<div style="margin-top:8px; font-size:11px; color:#FFC048; font-weight:600;">KEY ACCUSED — HEAVILY LINKED IN SYNDICATE</div>' : n.comm ? '<div style="margin-top:8px; font-size:11px; color:#22E6F0; font-weight:600;">PART OF EVIDENCE-LINKED COMMUNITY</div>' : ""}
    </div>`;
}

// Cache for label sprites so we don't recreate Three.js CanvasTextures on every frame/selection
const spriteCache = new Map();

function getCachedLabelSprite(THREE, text, sub, color) {
  const key = `${text}|${sub || ""}|${color || ""}`;
  if (spriteCache.has(key)) return spriteCache.get(key).clone();
  const sprite = makeLabelSprite(THREE, text, sub, color);
  spriteCache.set(key, sprite);
  return sprite.clone();
}

// Floating text label as a camera-facing sprite (three CanvasTexture).
function makeLabelSprite(THREE, text, sub, color) {
  const dpr = 1.5;
  const padX = 14 * dpr;
  const padY = 7 * dpr;
  const fs = 18 * dpr, subFs = 13 * dpr;
  const cvs = document.createElement("canvas");
  const ctx = cvs.getContext("2d");
  
  ctx.font = `600 ${fs}px Inter, sans-serif`;
  const w1 = ctx.measureText(text).width;
  ctx.font = `${subFs}px 'JetBrains Mono', monospace`;
  const w2 = sub ? ctx.measureText(`[${sub}]`).width : 0;
  
  const w = Math.max(w1, w2) + padX * 2;
  const h = (sub ? fs + subFs + 6 * dpr : fs) + padY * 2;
  cvs.width = w; cvs.height = h;
  
  ctx.fillStyle = "rgba(4, 7, 14, 0.88)";
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(0, 0, w, h, 8 * dpr);
  else ctx.rect(0, 0, w, h);
  ctx.fill();
  ctx.strokeStyle = "rgba(34, 230, 240, 0.35)";
  ctx.lineWidth = 1 * dpr;
  ctx.stroke();

  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  
  ctx.font = `600 ${fs}px Inter, sans-serif`;
  ctx.fillStyle = color || "#FFFFFF";
  ctx.fillText(text, w / 2, sub ? padY + fs / 2 : h / 2);
  
  if (sub) {
    ctx.font = `${subFs}px 'JetBrains Mono', monospace`;
    ctx.fillStyle = "#94A3B8";
    ctx.fillText(`[${sub}]`, w / 2, padY + fs + 4 * dpr + subFs / 2);
  }
  
  const tex = new THREE.CanvasTexture(cvs);
  tex.minFilter = THREE.LinearFilter;
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false });
  const sprite = new THREE.Sprite(mat);
  const scale = 0.55; 
  sprite.scale.set((w / dpr) * scale, (h / dpr) * scale, 1);
  return sprite;
}

const INTRO_MS = 3500;      // length of the opening zoom-in

export default function Constellation3D({ graph, groupBy = "evidence", active, kinds, controlRef, onFocus, onStats, onAgent, focusId, legendFocus, onReady }) {
  const containerRef = useRef(null);
  const fgRef = useRef(null);
  const introUntil = useRef(0);      // until when the arrival owns the camera
  const appliedRef = useRef(null);   // the constellation the graph is currently drawing
  const [lateTick, setLateTick] = useState(0);   // bumps when the arrival lands, to apply held data
  const lateTickSeen = useRef(0);
  const threeRef = useRef(null);
  const focusRef = useRef(null);
  const activeRef = useRef(active);
  const kindsRef = useRef(kinds);
  const groupByRef = useRef(groupBy);
  const dataRef = useRef(null);
  const flightRef = useRef(null);

  const constel = useMemo(() => (graph ? buildConstellation(graph, { groupBy }) : null), [graph, groupBy]);

  useEffect(() => { activeRef.current = active; refreshVisuals(); }, [active]);      // eslint-disable-line
  useEffect(() => { kindsRef.current = kinds; refreshVisuals(); }, [kinds]);         // eslint-disable-line
  useEffect(() => { groupByRef.current = groupBy; }, [groupBy]);
  useEffect(() => { if (constel) onStats?.(constel.stats); }, [constel, onStats]);

  const nodeColor = (n) => {
    if (focusRef.current && !focusRef.current.has(n.id)) return "rgba(77,90,112,0.12)";
    return n.color || ROLE_COLOR[n.role] || ROLE_COLOR.dust;
  };
  const nodeVisible = (n) => n.kind === "agent" || activeRef.current == null || activeRef.current.has(n.cat);
  const linkColor = (l) => {
    if (l.kind === "agent") return LINK_AGENT;
    if (l.kind === "inferred") return "rgba(192,132,252,0.85)";
    if (l.kind === "unsub") return "rgba(168,85,247,0.85)";
    const s = typeof l.source === "object" ? l.source : null;
    return focusRef.current && s && !focusRef.current.has(s.id) ? LINK_DIM : LINK_BASE;
  };
  const linkVisible = (l) => l.kind === "agent" || kindsRef.current?.has(l.kind);

  function refreshVisuals() {
    const fg = fgRef.current;
    if (!fg) return;
    fg.nodeColor(nodeColor).nodeVisibility(nodeVisible).linkColor(linkColor).linkVisibility(linkVisible);
  }

  // `seeds`: every FIR an exact search matched - the focus is exactly those FIRs, so it
  // counts the same records as the table that asked for them
  function focusComponent(n, seeds) {
    const fg = fgRef.current;
    if (!fg || !dataRef.current) return;
    const members = seeds?.length > 1 ? seeds
      : n.comm ? dataRef.current.nodes.filter((m) => m.comm === n.comm) : [n];
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
      comp: { size: members.length, cats, people, rows, districts: [...districts], years: yMin <= yMax ? [yMin, yMax] : null,
              ...groupProfile(members) },
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
    fgRef.current?.cameraPosition({ x: 0, y: 0, z: 980 }, { x: 0, y: 0, z: 0 }, 800);
  }

  function flyAgents(duration = 1400) {
    const fg = fgRef.current;
    if (!fg || !dataRef.current) return;
    if (flightRef.current) cancelAnimationFrame(flightRef.current);
    const hubs = dataRef.current.nodes.filter((m) => m.role === "agent");
    if (!hubs.length) return;
    const home = hubs.map((h) => ({ h, r0: Math.hypot(h.x || 0, h.y || 0, h.z || 0) || h.ring, a0: Math.atan2(h.y || 0, h.x || 0), e0: Math.asin((h.z || 0) / (Math.hypot(h.x || 0, h.y || 0, h.z || 0) || 1)) }));
    const t0 = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - t0) / duration);
      home.forEach(({ h, r0, a0, e0 }, i) => {
        const a = a0 + t * Math.PI * 4 * (i % 2 ? -1 : 1);
        const r = r0 - (r0 - 140) * Math.sin(Math.PI * t);
        h.fx = Math.cos(a) * Math.cos(e0) * r;
        h.fy = Math.sin(a) * Math.cos(e0) * r;
        h.fz = Math.sin(e0) * r;
      });
      if (t < 1) {
        flightRef.current = requestAnimationFrame(tick);
      } else {
        home.forEach(({ h }) => { delete h.fx; delete h.fy; delete h.fz; });
        flightRef.current = null;
      }
    };
    flightRef.current = requestAnimationFrame(tick);
  }

  // Build once
  useEffect(() => {
    if (!constel || !containerRef.current || fgRef.current) return;
    let destroyed = false;
    let zoomTimer = null;
    let rotateTimer = null;
    Promise.all([import("3d-force-graph"), import("three"), import("d3-force-3d")]).then(([{ default: ForceGraph3D }, THREE, d3f]) => {
      if (destroyed || !containerRef.current || fgRef.current) return;
      threeRef.current = THREE;

      const validNodeIds = new Set(constel.nodes.map(n => n.id));
      appliedRef.current = constel;
      dataRef.current = {
        nodes: constel.nodes.map((n) => ({ ...n, z: (n.z != null ? n.z : Math.sin((n._i || 0) * 0.7) * (n.ring || 200) * 0.6) })),
        links: constel.links.filter((l) => validNodeIds.has(l.source?.id || l.source) && validNodeIds.has(l.target?.id || l.target)).map((l) => ({ ...l, source: l.source.id || l.source, target: l.target.id || l.target })),
      };

      // Antialiasing is what separates a scatter of specks from a crawling set of
      // stair-stepped dots, and it costs little at this node count.
      const fg = ForceGraph3D({ rendererConfig: { antialias: true, powerPreference: "high-performance" } })(containerRef.current)
        .width(containerRef.current.offsetWidth)
        .height(containerRef.current.offsetHeight)
        .backgroundColor("rgba(0,0,0,0)")
        .showNavInfo(false)
        .nodeId("id")
        .nodeVal((n) => n.vsize)
        .nodeColor(nodeColor)
        .nodeVisibility(nodeVisible)
        .nodeOpacity(0.92)
        .nodeLabel(nodeTooltip)
        .nodeThreeObjectExtend(true)
        .nodeThreeObject((n) => {
          if (focusRef.current && !focusRef.current.has(n.id)) return null;
          let text = "", sub = "", color = "#FFFFFF";
          if (n.kind === "agent" && n.label) { text = n.label; color = "#00F5D4"; }
          else if (n.kind === "unsub") { text = n.name || "UNSUB"; color = "#E9D5FF"; }
          else if (n.role === "top" || n.role === "hub") {
            text = n.label || ""; sub = n.sub || "";
            color = n.role === "top" ? "#34EEB6" : "#FFFFFF";
          }
          if (!text) return null;
          const sprite = getCachedLabelSprite(THREE, text, sub, color);
          sprite.position.set(0, (n.vsize || 2) + 6, 0);
          return sprite;
        })
        .linkColor(linkColor)
        .linkVisibility(linkVisible)
        .linkWidth((l) => (l.kind === "agent" ? 0.5 : l.kind === "inferred" || l.kind === "unsub" ? 0.6 : 0.8))
        .linkOpacity(0.55)
        .linkDirectionalParticles((l) => l.kind === "agent" ? 1 : 0)
        .linkDirectionalParticleSpeed(0.012)
        .linkDirectionalParticleWidth(1.4)
        .linkDirectionalParticleColor(() => "rgba(255,255,255,0.85)")
        .linkLabel((l) => `<div style="background:rgba(6,11,18,0.94); border:1px solid rgba(255,140,66,0.4); padding:5px 9px; border-radius:6px; font:11px 'JetBrains Mono', monospace; color:#FFB020; box-shadow:0 6px 16px rgba(0,0,0,0.85);">${linkWhy(l)}</div>`)
        .onNodeClick((n) => {
          if (n.kind === "agent") { onAgent?.(n.agent); return; }
          focusComponent(n);
        })
        .onBackgroundClick(() => { if (focusRef.current) clearFocus(); })
        .warmupTicks(0)
        .cooldownTicks(0)   // laid out in advance (below); the live engine is switched on once the camera lands
        .cooldownTime(4000);

      // Cap the pixel ratio at 2: past that a 4K/retina panel renders four times the
      // pixels for a difference nobody can see, and that alone makes rotation choppy.
      try {
        const r = fg.renderer?.();
        if (r?.setPixelRatio) r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      } catch {}

      // Bloom: the hubs and the agent tethers are the only things bright enough to trip
      // the threshold, so they glow and the thousands of context specks do not. Loaded
      // lazily so it never enters the first bundle, and the threshold is high enough
      // that the near-white labels stay crisp instead of wearing a halo.
      if (!(typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches)) {
        import("three/examples/jsm/postprocessing/UnrealBloomPass.js")
          .then(({ UnrealBloomPass }) => {
            if (destroyed || fgRef.current !== fg) return;
            const el = containerRef.current;
            const bloom = new UnrealBloomPass(
              new THREE.Vector2(el?.offsetWidth || 1280, el?.offsetHeight || 720),
              0.55, 0.80, 0.86,
            );
            fg.postProcessingComposer().addPass(bloom);
          })
          .catch(() => {});   // a missing post-processing module must never break the graph
      }

      fg.d3Force("charge").strength(-45);
      const linkForce = fg.d3Force("link");
      if (linkForce) linkForce.distance(40);
      // 3D shell layout: evidence mode → sphere of radius n.ring; type mode →
      // pull to the category-blob target (n.tx/n.ty) and flatten toward z=0.
      const radial3 = (alpha) => {
        const ns = dataRef.current?.nodes || [];
        for (const m of ns) {
          if (groupByRef.current === "type" && m.tx != null) {
            const k = alpha * 0.12;
            m.vx += (m.tx - m.x) * k;
            m.vy += (m.ty - m.y) * k;
            m.vz += (0 - (m.z || 0)) * k * 0.6;
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

      // Lay the brain out BEFORE it is shown. Each step of the layout costs ~100 ms here
      // (thousands of nodes repelling each other); run live, it made every frame of the
      // zoom-in a 100-300 ms stall. The same forces are run here in small slices while the
      // loader is still up - so the loader keeps moving - and the graph is handed over
      // already settled. The zoom then moves only the camera.
      const SETTLE_TICKS = 60, SETTLE_BUDGET_MS = 2500;   // ~ the old 30 warm-up ticks on a slow machine, more on a fast one
      const sim = d3f.forceSimulation(dataRef.current.nodes, 3).stop()
        .force("charge", d3f.forceManyBody().strength(-45))
        .force("link", d3f.forceLink(dataRef.current.links.map((l) => ({ ...l }))).id((d) => d.id).distance(40))
        .force("radial3", radial3);
      const settleStart = performance.now();
      let ticks = 0;
      const settle = () => {
        if (destroyed) return;
        const sliceEnd = performance.now() + 28;
        while (ticks < SETTLE_TICKS && performance.now() < sliceEnd) { sim.tick(); ticks++; }
        if (ticks < SETTLE_TICKS && performance.now() - settleStart < SETTLE_BUDGET_MS) { setTimeout(settle, 0); return; }
        // Hand over on a frame: a frame only comes while the tab is on screen. Started in a
        // background tab, the arrival ran on timers with no frames to draw it, and the
        // officer came back to a brain collapsed into flat bubbles, seen from far out.
        requestAnimationFrame(() => { if (!destroyed) start(); });
      };
      setTimeout(settle, 0);

      const start = () => {
      fg.graphData(dataRef.current);
      fgRef.current = fg;
      onReady?.();
      
      // The brain arrives: one unbroken glide to its working distance (z 820). It starts
      // with the whole brain on screen (z 2600) and moves from the first frame - it used to
      // wait 300 ms first and then creep out of a slow-start tween, so the screen read as blank while the loader
      // faded. The glide is slow and eases in and out (sine), with no jolt at either end,
      // drawn every frame rather than handed to the library's slow-start tween. Nothing
      // else may move the camera until it lands - the data effect below waits for it.
      // It holds on the whole brain for HOLD_MS first - the loader is still fading over it
      // until then, and a glide that ran behind the loader was a zoom nobody saw.
      const HOLD_MS = 1300;
      introUntil.current = Date.now() + HOLD_MS + INTRO_MS + 400;
      const START_Z = 2600, END_Z = 820;
      fg.cameraPosition({ x: 0, y: 0, z: START_Z }, { x: 0, y: 0, z: 0 }, 0);
      const t0 = performance.now() + HOLD_MS;
      const easeOut = (t) => (1 - Math.cos(Math.PI * t)) / 2;   // gentle start, gentle landing
      const glide = (now) => {
        if (destroyed || !fg) return;
        const t = Math.max(0, Math.min(1, (now - t0) / INTRO_MS));
        fg.cameraPosition({ x: 0, y: 0, z: START_Z + (END_Z - START_Z) * easeOut(t) }, { x: 0, y: 0, z: 0 }, 0);
        flightRef.current = t < 1 ? requestAnimationFrame(glide) : null;
      };
      flightRef.current = requestAnimationFrame(glide);

      rotateTimer = setTimeout(() => {
        if (destroyed || !fg) return;
        if (fg.controls) {
          const controls = fg.controls();
          controls.autoRotate = true;
          controls.autoRotateSpeed = 0.45;
        }
        fg.cooldownTicks(Infinity);   // live layout back on for filters and focus
        setLateTick((k) => k + 1);    // apply any data that changed while the brain was being laid out
      }, HOLD_MS + INTRO_MS + 400);
      };
    });
    return () => {
      destroyed = true;
      if (zoomTimer) clearTimeout(zoomTimer);
      if (rotateTimer) clearTimeout(rotateTimer);
      if (flightRef.current) cancelAnimationFrame(flightRef.current);
      try { fgRef.current?._destructor?.(); } catch {}
      fgRef.current = null;
    };
  }, [constel === null]); // eslint-disable-line

  // Morph on data change (timeline / filters / groupBy)
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || !constel) return;
    // Data that lands mid-arrival (the predicted links come a moment after the records)
    // waits until the camera has landed: rebuilding thousands of nodes mid-glide is a
    // visible stall in the zoom. Only the latest data is applied.
    const wait = introUntil.current - Date.now();
    if (wait > 0) {
      const t = setTimeout(() => setLateTick((k) => k + 1), wait);
      return () => clearTimeout(t);
    }
    const landed = lateTick !== lateTickSeen.current;  // this run is the arrival landing
    lateTickSeen.current = lateTick;
    if (appliedRef.current === constel) return;        // already drawn - nothing held back
    appliedRef.current = constel;
    focusRef.current = null;
    onFocus?.(null);
    const validNodeIds = new Set(constel.nodes.map(n => n.id));
    dataRef.current = {
      nodes: constel.nodes.map((n) => ({ ...n, z: (n.z != null ? n.z : Math.sin((n._i || 0) * 0.7) * (n.ring || 200) * 0.6) })),
      links: constel.links.filter((l) => validNodeIds.has(l.source?.id || l.source) && validNodeIds.has(l.target?.id || l.target)).map((l) => ({ ...l, source: l.source.id || l.source, target: l.target.id || l.target })),
    };
    fg.graphData(dataRef.current);
    refreshVisuals();
    onReady?.();
    if (landed) return;                                // just landed: the camera is already framed
    if (groupByRef.current === "type") {
      fg.cameraPosition({ x: 0, y: 0, z: 820 }, { x: 0, y: 0, z: 0 }, 900);
    } else {
      setTimeout(() => fg.zoomToFit(700, 90), 800);
    }
  }, [constel, lateTick]); // eslint-disable-line

  // Parent controls (parity with the 2D component)
  useEffect(() => {
    if (!controlRef) return;
    controlRef.current = {
      clear: clearFocus,
      refit: () => fgRef.current?.zoomToFit(700, 90),
      think: flyAgents,
      // A window covering the brain stops it drawing: a full WebGL frame under a scrolling
      // window was what made the window's scroll stutter.
      pause: () => fgRef.current?.pauseAnimation?.(),
      resume: () => fgRef.current?.resumeAnimation?.(),
      // The FIR drawn nearest a screen point, for dropping a console agent on a record.
      nodeAt: (cx, cy, radius = 26) => {
        const fg = fgRef.current, el = containerRef.current;
        if (!fg || !el || !dataRef.current) return null;
        const box = el.getBoundingClientRect();
        const px = cx - box.left, py = cy - box.top;
        let best = null, bestD = radius * radius;
        for (const m of dataRef.current.nodes) {
          if (m.kind !== "fir" || m.x == null) continue;
          const s = fg.graph2ScreenCoords(m.x, m.y, m.z || 0);
          const d = (s.x - px) ** 2 + (s.y - py) ** 2;
          if (d < bestD) { best = m; bestD = d; }
        }
        return best;
      },
      focus: (n) => { if (n) focusComponent(n); },
      find: (q) => {
        const needle = String(q || "").trim().toLowerCase();
        if (!needle || !dataRef.current) return false;
        const score = (m) => (m.role === "hub" || m.role === "top" ? 2 : m.comm ? 1 : 0);
        let found = null;
        const exact = [];
        dataRef.current.nodes.forEach((m) => {
          if (m.kind === "agent") return;
          // a shared key (vehicle, UPI ID, IP address) finds its FIRs too - the Data overview's
          // "Show the N FIRs" focuses the Brain on one of these
          const keyHit = [m.vehicle, m.upi, m.ip].some((v) => v && String(v).trim().toLowerCase() === needle);
          const hay = [m.accused, m.accused && aliasFor(m.accused), m.zone, m.district, m.crimeHead, m.crimeGroup];
          if (!keyHit && !hay.some((v) => v && String(v).toLowerCase().includes(needle))) return;
          if (keyHit || String(m.accused || "").trim().toLowerCase() === needle) exact.push(m);
          if (!found || score(m) > score(found)) found = m;
        });
        if (found) focusComponent(found, exact);
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
