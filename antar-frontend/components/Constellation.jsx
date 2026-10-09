"use client";

import { useEffect, useMemo, useRef } from "react";
import { buildConstellation, aliasFor, CATEGORIES , soften } from "@/lib/crimeGraph";

// Every drawn edge exists because two FIRs share a real key - name it.
function linkWhy(l) {
  const key = l.key ? ` - ${l.key}` : "";
  if (l.kind === "repeat") return `Repeat offender: same accused${key}`;
  if (l.kind === "ring") return `Ring: shared place / vehicle${key}`;
  if (l.kind === "cyber") return `Cyber: shared UPI / IP${key}`;
  if (l.kind === "inferred") return `Predicted Edge (Inferred Link)${key}`;
  if (l.kind === "unsub") return `UNSUB Cluster Member${key}`;
  if (l.kind === "agent") return "Antar intelligence cluster - learns & predicts over this graph";
  return `Linked${key}`;
}

// Node palette per the constellation reference: teal linked records, orange
// named hubs, gray dust, green apex, purple Antar agents.
const ROLE_COLOR = {
  dust: "#566072", linked: "#2BB3A3", hub: "#E8A33D", top: "#18D69A",
  agent: "#8B5CF6", agentsat: "#A78BFA",
};
const LINK_BASE = "rgba(148,163,184,.16)";
const LINK_DIM = "rgba(148,163,184,.04)";
const LINK_AGENT = "rgba(139,92,246,.4)";

// Screen 03 canvas - the "All Data" spherical constellation (2,719 FIRs) with
// a Focus lens: click a node, or zoom deep into a group, and its component
// isolates while the parent shows the what/why analytics panel.
function bubbleRadius(ms, cx, cy) {
  const d = ms.map((m) => Math.hypot(m.x - cx, m.y - cy)).sort((a, b) => a - b);
  return d.length ? d[Math.min(d.length - 1, Math.floor(d.length * 0.85))] : 0;
}

export default function Constellation({ graph, groupBy = "evidence", active, kinds, controlRef, onFocus, onStats, onAgent, focusId, legendFocus }) {
  const containerRef = useRef(null);
  const fgRef = useRef(null);
  const focusRef = useRef(null);     // Set of node ids in the focused group
  const latchRef = useRef(false);    // one zoom-trigger per zoom-in
  const activeRef = useRef(active);
  const kindsRef = useRef(kinds);
  const dataRef = useRef(null);
  const flightRef = useRef(null);    // rAF id of the agent think-flight
  const metaRef = useRef(null);      // group callout metadata (live node refs)
  const hoverCompRef = useRef(null); // component id under the pointer
  const focusCompRef = useRef(null); // component id currently focused
  const legendFocusRef = useRef(legendFocus);

  const groupByRef = useRef(groupBy);
  // pack: non-overlapping crime-type bubbles (see packCircles in lib/crimeGraph.js).
  const constel = useMemo(() => (graph ? buildConstellation(graph, { groupBy, pack: true }) : null), [graph, groupBy]);

  useEffect(() => { activeRef.current = active; }, [active]);
  useEffect(() => { kindsRef.current = kinds; }, [kinds]);
  useEffect(() => { groupByRef.current = groupBy; }, [groupBy]);
  useEffect(() => { 
    legendFocusRef.current = legendFocus; 
    if (fgRef.current) {
      fgRef.current.nodeColor(fgRef.current.nodeColor());
      fgRef.current.linkColor(fgRef.current.linkColor());
    }
  }, [legendFocus]);
  useEffect(() => { if (constel) onStats?.(constel.stats); }, [constel, onStats]);

  function focusComponent(n) {
    const fg = fgRef.current;
    if (!fg || !dataRef.current) return;
    const members = n.kind === "category"
      ? dataRef.current.nodes.filter((m) => m.cat === n.cat)
      : n.comm
      ? dataRef.current.nodes.filter((m) => m.comm === n.comm)
      : [n];
    const focus = new Set(members.map((m) => m.id));
    focusRef.current = focus;
    focusCompRef.current = n.comm ?? null;

    // evidence: the shared keys holding this group together
    const whys = [], seen = new Set();
    dataRef.current.links.forEach((l) => {
      const sid = typeof l.source === "object" ? l.source.id : l.source;
      const tid = typeof l.target === "object" ? l.target.id : l.target;
      if (!focus.has(sid) || !focus.has(tid)) return;
      const w = linkWhy(l);
      if (!seen.has(w)) { seen.add(w); whys.push({ kind: l.kind, text: w }); }
    });

    // composition analytics for the Focus panel (ref-2 style what/why)
    const catCount = new Map();
    const districts = new Set();
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
    fg.centerAt(n.x, n.y, 700);
    fg.zoom(Math.max(fg.zoom(), 3), 700);
  }

  function clearFocus() {
    focusRef.current = null;
    focusCompRef.current = null;
    onFocus?.(null);
    const fg = fgRef.current;
    if (fg) fg.zoomToFit(700, 60);
  }

  useEffect(() => {
    if (!constel || !containerRef.current || fgRef.current) return;
    let destroyed = false;
    import("force-graph").then(({ default: ForceGraph }) => {
      if (destroyed || !containerRef.current || fgRef.current) return;

      const visible = (n) => n.kind === "agent" || activeRef.current === null || activeRef.current.has(n.cat);
      const dimmed = (n) => focusRef.current && !focusRef.current.has(n.id);

      const matchesLegend = (n) => {
        const lf = legendFocusRef.current;
        if (!lf) return true;
        if (lf === "comm") return n.comm === true;
        if (lf === "dust") return n.role === "dust" || !n.comm;
        if (lf === "agent") return n.kind === "agent";
        return n.role === lf;
      };

      const fg = ForceGraph()(containerRef.current)
        .width(containerRef.current.offsetWidth)
        .height(containerRef.current.offsetHeight)
        .backgroundColor("rgba(0,0,0,0)")
        .nodeId("id")
        .nodeVal((n) => n.vsize)
        .nodeColor((n) => {
          const lf = legendFocusRef.current;
          if (lf && !matchesLegend(n)) return "rgba(77,90,112,0.05)";
          return dimmed(n) ? "rgba(77,90,112,.10)" : soften(n.color || ROLE_COLOR[n.role] || ROLE_COLOR.dust);
        })
        .nodeVisibility(visible)
        .nodeLabel((n) => n.kind === "agent"
          ? `<div style="background:rgba(10,15,24,0.96); border:1px solid rgba(167,139,250,0.45); padding:10px 14px; border-radius:8px; box-shadow:0 8px 24px rgba(0,0,0,0.85); font:12px 'Chakra Petch', Inter, sans-serif; color:#E2E8F0;"><b style="color:#C4B5FD; font-size:13px; letter-spacing:0.5px;">${n.label || "Antar Intelligence"}</b><br/><span style="color:#94A3B8; font-size:11px;">Autonomous Intelligence & Forecasting</span><br/><div style="margin-top:6px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.1); color:#38BDF8; font-weight:600;">▶ Click to inspect reasoning logs</div></div>`
          : n.kind === "unsub"
          ? `<div style="background:rgba(15,10,25,0.96); border:1px solid rgba(168,85,247,0.6); padding:12px 15px; border-radius:8px; box-shadow:0 10px 30px rgba(0,0,0,0.9); font:12px Inter, sans-serif; color:#E9D5FF;"><b style="color:#C084FC; font-size:13px; font-family:'Chakra Petch', sans-serif;">${n.name || "UNSUB Profile"}</b><div style="margin-top:6px; color:#D8B4FE; font-size:11px;">SYNTHETIC INVESTIGATIVE PROFILE</div><div style="margin-top:6px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.1); font-size:11px; color:#CBD5E1;">Knowledge Boundary: <b>100% Gap (UNSUB)</b></div></div>`
          : `<div style="background:rgba(6,11,18,0.96); border:1px solid ${n.role === "top" ? "rgba(24,214,154,0.6)" : n.role === "hub" ? "rgba(232,163,61,0.6)" : "rgba(43,179,163,0.4)"}; padding:12px 15px; border-radius:8px; box-shadow:0 10px 30px rgba(0,0,0,0.9); font:12px Inter, sans-serif; color:#E2E8F0; max-width:300px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; gap:8px;">
                <b style="color:${n.role === "top" ? "#34EEB6" : n.role === "hub" ? "#FFC048" : "#22E6F0"}; font-size:13px; font-family:'Chakra Petch', sans-serif; text-transform:uppercase;">${n.crimeHead || n.crimeGroup || "FIR Record"}</b>
                ${n.stage ? `<span style="font-size:10px; background:rgba(255,255,255,0.08); padding:2px 6px; border-radius:4px; color:#A7F3D0; white-space:nowrap;">${n.stage}</span>` : ""}
              </div>
              <div style="color:#94A3B8; font-size:11px; margin-bottom:6px;">${n.zone || ""}${n.district && n.district !== n.zone ? `, ${n.district}` : ""} · ${n.year || "2026"}</div>
              ${n.accused ? `<div style="background:rgba(232,163,61,0.12); border-left:3px solid #E8A33D; padding:5px 8px; margin:6px 0; border-radius:0 4px 4px 0;"><span style="color:#FDE68A; font-weight:600;">${aliasFor(n.accused) || "Suspect"}</span> <span style="color:#94A3B8; font-family:'JetBrains Mono'; font-size:11px;">[${n.accused}]</span></div>` : ""}
              ${n.vehicle ? `<div style="color:#38BDF8; font-size:11px; margin-top:4px; font-family:'JetBrains Mono';">Getaway Veh: <b>${n.vehicle}</b></div>` : ""}
              ${n.mo ? `<div style="margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.1); font-size:11px; color:#CBD5E1; line-height:1.4;"><b>Explainable MO:</b><br/>${n.mo}</div>` : ""}
              ${n.role === "top" ? '<div style="margin-top:8px; font-size:11px; color:#34EEB6; font-weight:600;">MOST CONNECTED APEX HUB IN VIEW</div>' : n.role === "hub" ? '<div style="margin-top:8px; font-size:11px; color:#FFC048; font-weight:600;">KEY ACCUSED - HEAVILY LINKED IN SYNDICATE</div>' : n.comm ? '<div style="margin-top:8px; font-size:11px; color:#22E6F0; font-weight:600;">PART OF EVIDENCE-LINKED COMMUNITY</div>' : ""}
            </div>`)
        .linkColor((l) => {
          const lf = legendFocusRef.current;
          if (lf && lf !== "line" && lf !== "agent") return "rgba(77,90,112,0.05)";
          if (l.kind === "agent") return LINK_AGENT;
          if (l.kind === "inferred") return "rgba(192,132,252,0.85)";
          if (l.kind === "unsub") return "rgba(168,85,247,0.85)";
          const s = typeof l.source === "object" ? l.source : null;
          return focusRef.current && s && !focusRef.current.has(s.id) ? LINK_DIM : LINK_BASE;
        })
        .linkVisibility((l) => l.kind === "agent" || kindsRef.current.has(l.kind))
        .linkLineDash((l) => l.kind === "inferred" ? [4, 4] : l.kind === "unsub" ? [2, 3] : null)
        .linkWidth(() => 0.8)
        // Neural-synapse firing (reference: neurons-hero): white pulses travel
        // along REAL evidence links, so the brain visibly "fires" where cases
        // are actually connected. Agent/ghost edges stay pulse-free.
        .linkDirectionalParticles((l) => (l.kind === "agent" || l.kind === "unsub" || l.kind === "inferred") ? 0 : 1)
        .linkDirectionalParticleSpeed(0.0045)
        .linkDirectionalParticleWidth(2.2)
        .linkDirectionalParticleColor(() => "rgba(255,255,255,0.85)")
        .linkLabel((l) => `<div style="background:rgba(6,11,18,0.94); border:1px solid rgba(255,140,66,0.4); padding:5px 9px; border-radius:6px; font:11px 'JetBrains Mono', monospace; color:#FFB020; box-shadow:0 6px 16px rgba(0,0,0,0.85);">${linkWhy(l)}</div>`)
        .nodeCanvasObjectMode((n) => (n.kind === "unsub" || n.kind === "category") ? "replace" : (n.label && !dimmed(n) ? "after" : undefined))
        .nodeCanvasObject((n, ctx, scale) => {
          const fs = Math.max(3.2, 10 / scale);
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          if (n.kind === "category") {
            ctx.save();
            ctx.beginPath();
            ctx.arc(n.x, n.y, (n.vsize || 26) / scale, 0, 2 * Math.PI, false);
            ctx.fillStyle = (n.color || CATEGORIES[n.cat]?.color || "#FFFFFF") + "40";
            ctx.fill();
            ctx.lineWidth = 2 / scale;
            ctx.strokeStyle = n.color || CATEGORIES[n.cat]?.color || "#FFFFFF";
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(n.x, n.y, 3 / scale, 0, 2 * Math.PI, false);
            ctx.fillStyle = n.color || CATEGORIES[n.cat]?.color || "#FFFFFF";
            ctx.fill();
            ctx.font = `600 ${fs}px Inter`;
            ctx.fillStyle = "#FFFFFF";
            ctx.fillText(n.name, n.x, n.y - (n.vsize || 26) / scale - 6 / scale);
            ctx.restore();
            return;
          }
          if (n.kind === "unsub") {
            ctx.save();
            ctx.beginPath();
            ctx.arc(n.x, n.y, 8 / scale, 0, 2 * Math.PI);
            ctx.strokeStyle = "#A855F7";
            ctx.lineWidth = 2.5 / scale;
            ctx.setLineDash([3 / scale, 2 / scale]);
            ctx.stroke();
            ctx.fillStyle = "rgba(168,85,247,0.15)";
            ctx.fill();
            ctx.font = `600 ${fs}px Inter`;
            ctx.fillStyle = "#E9D5FF";
            ctx.fillText(n.name || "UNSUB", n.x, n.y - 16 / scale);
            ctx.restore();
            return;
          }
          if (n.role === "agent") {
            ctx.save();
            ctx.shadowColor = "rgba(0,0,0,0.95)";
            ctx.shadowBlur = 5;
            ctx.font = `600 ${fs * 0.92}px Inter`;
            ctx.fillStyle = "#C4B5FD";
            ctx.fillText(n.label, n.x, n.y + 11 / scale + fs * 0.7);
            ctx.restore();
            return;
          }
          ctx.save();
          ctx.shadowColor = "rgba(0,0,0,0.95)";
          ctx.shadowBlur = 6;
          ctx.font = `600 ${fs}px Inter`;
          const isRingNode = n.kind === "ring" || n.kind === "cyber" || String(n.label || "").toLowerCase().includes("ring");
          ctx.fillStyle = n.role === "top" ? "#34EEB6" : (isRingNode ? "#FEF08A" : "#FFFFFF");
          ctx.fillText(n.label, n.x, n.y - (n.sub ? fs * 0.44 : 0));
          if (n.sub) {
            ctx.font = `${fs * 0.72}px 'JetBrains Mono'`;
            ctx.fillStyle = n.role === "top" ? "#10B981" : (isRingNode ? "#FDE047" : "#CBD5E1");
            ctx.fillText(`[${n.sub}]`, n.x, n.y + fs * 0.52);
          }
          ctx.restore();
        })
        .onNodeClick((n) => {
          if (n.kind === "agent") { onAgent?.(n.agent); return; }
          focusComponent(n);
        })
        .onNodeHover((n) => {
          hoverCompRef.current = groupByRef.current === "type"
            ? (n?.cat ? `cat:${n.cat}` : null)
            : (n?.comm ?? null);
          if (containerRef.current) containerRef.current.style.cursor = n ? "pointer" : "";
        })
        .onRenderFramePost((ctx, scale) => {
          const metas = metaRef.current;
          if (!metas?.length) return;
          const maxLabels = metas[0]?.color ? metas.length
            : scale < 0.45 ? 8 : scale < 0.8 ? 14 : scale < 1.4 ? 24 : scale < 2.2 ? 40 : metas.length;
          const focused = focusCompRef.current;
          const hovered = hoverCompRef.current;
          const items = [];
          const count = Math.min(maxLabels, metas.length);
          for (let i = 0; i < count; i++) {
            const meta = metas[i];
            if (focused && meta.id !== focused) continue;
            const ms = meta.members;
            if (!ms?.length) continue;
            let cx = 0, cy = 0;
            ms.forEach((m) => { cx += m.x; cy += m.y; });
            cx /= ms.length; cy /= ms.length;
            // 85th-percentile radius, not the farthest member: a few nodes pulled out by
            // cross-crime evidence links used to drag the label far from its bubble.
            let r = bubbleRadius(ms, cx, cy);
            r += 6 / scale;
            const ang = Math.atan2(cy, cx) || 0.4;
            const gap = 24 / scale;
            items.push({ meta, cx, cy, r, ang, ex: cx + Math.cos(ang) * r, ey: cy + Math.sin(ang) * r, lx: cx + Math.cos(ang) * (r + gap), ly: cy + Math.sin(ang) * (r + gap), right: Math.cos(ang) >= 0 });
          }
          if (hovered) {
            const extra = metas.find((m) => m.id === hovered);
            if (extra && !items.some((it) => it.meta.id === hovered)) {
              const ms = extra.members;
              if (ms?.length) {
                let cx = 0, cy = 0;
                ms.forEach((m) => { cx += m.x; cy += m.y; });
                cx /= ms.length; cy /= ms.length;
                let r = bubbleRadius(ms, cx, cy);
                r += 6 / scale;
                const ang = Math.atan2(cy, cx) || 0.4;
                const gap = 24 / scale;
                items.push({ meta: extra, cx, cy, r, ang, ex: cx + Math.cos(ang) * r, ey: cy + Math.sin(ang) * r, lx: cx + Math.cos(ang) * (r + gap), ly: cy + Math.sin(ang) * (r + gap), right: Math.cos(ang) >= 0 });
              }
            }
          }
          const minGap = 22 / scale;
          const lefts = items.filter((it) => !it.right).sort((a, b) => a.ly - b.ly);
          const rights = items.filter((it) => it.right).sort((a, b) => a.ly - b.ly);
          [lefts, rights].forEach((side) => {
            for (let j = 1; j < side.length; j++) {
              if (side[j].ly - side[j - 1].ly < minGap) {
                side[j].ly = side[j - 1].ly + minGap;
              }
            }
          });
          const fs = 10.5 / scale;
          const pad = 5 / scale;
          items.forEach(({ meta, cx, cy, r, ex, ey, lx, ly, right }) => {
            const isHover = meta.id === hovered;
            ctx.save();
            ctx.setLineDash([3 / scale, 3 / scale]);
            ctx.strokeStyle = isHover ? "rgba(232,163,61,.75)" : "rgba(157,171,188,.35)";
            ctx.lineWidth = 1 / scale;
            ctx.beginPath(); ctx.moveTo(ex, ey); ctx.lineTo(lx, ly); ctx.stroke();
            if (isHover) { ctx.beginPath(); ctx.arc(cx, cy, r + 3 / scale, 0, 2 * Math.PI); ctx.stroke(); }
            ctx.setLineDash([]);
            ctx.textAlign = right ? "left" : "right";
            ctx.textBaseline = "middle";
            ctx.fillStyle = meta.color || { repeat: "#E8A33D", ring: "#FF8C42", cyber: "#22E6F0" }[meta.kind] || "#9DABBC";
            ctx.beginPath(); ctx.arc(lx + (right ? pad * 0.5 : -pad * 0.5), ly, 1.8 / scale, 0, 2 * Math.PI); ctx.fill();
            ctx.save();
            ctx.shadowColor = "rgba(0,0,0,0.95)";
            ctx.shadowBlur = 5;
            ctx.font = `${isHover ? 600 : 500} ${fs}px 'Chakra Petch'`;
            const isRing = meta.kind === "ring" || meta.kind === "cyber" || String(meta.name || "").toLowerCase().includes("ring");
            ctx.fillStyle = isHover ? "#FFFFFF" : (isRing ? "#FEF08A" : "#FFFFFF");
            ctx.fillText(meta.name, lx + (right ? pad + 3 / scale : -(pad + 3 / scale)), ly);
            if (isHover || scale >= 2.2) {
              ctx.font = `${fs * 0.78}px 'JetBrains Mono'`;
              ctx.fillStyle = isHover ? "#FFFBEB" : (isRing ? "#FDE047" : "#CBD5E1");
              ctx.fillText(meta.sub, lx + (right ? pad + 3 / scale : -(pad + 3 / scale)), ly + fs * 1.05);
            }
            ctx.restore();
            ctx.restore();
          });
        })
        .onZoom(({ k }) => {
          if (k >= 3.4 && !focusRef.current && !latchRef.current && containerRef.current) {
            latchRef.current = true;
            const { x, y } = fg.screen2GraphCoords(
              containerRef.current.offsetWidth / 2, containerRef.current.offsetHeight / 2);
            let best = null, bd = Infinity;
            dataRef.current?.nodes.forEach((m) => {
              if (!m.comm) return;
              const d = (m.x - x) ** 2 + (m.y - y) ** 2;
              if (d < bd) { bd = d; best = m; }
            });
            if (best && bd < 200 * 200) focusComponent(best);
          }
          if (k < 2.4) latchRef.current = false;
        })
        .warmupTicks(80)
        .cooldownTime(8000);

      // Crime-type mode: nodes must stay inside their category bubble, so repulsion is
      // gentle and the pull to the bubble strong. -80 across 3k+ nodes pushed every
      // bubble into its neighbours.
      fg.d3Force("charge").strength(groupByRef.current === "type" ? -14 : -80);
      const linkForce = fg.d3Force("link");
      if (linkForce) linkForce.distance(35);
      // custom layout force: evidence mode = radial shells (core / ring / dust),
      // type mode = pull to the node's category-blob target point (n.tx/n.ty)
      const radial = (alpha) => {
        const ns = dataRef.current?.nodes || [];
        for (const m of ns) {
          if (m.tx != null) {
            const k = alpha * (groupByRef.current === "type" ? 0.3 : 0.12);
            m.vx += (m.tx - m.x) * k;
            m.vy += (m.ty - m.y) * k;
          } else {
            const r = Math.hypot(m.x, m.y) || 1;
            const k = ((m.ring - r) / r) * alpha * 0.10;
            m.vx += m.x * k;
            m.vy += m.y * k;
          }
        }
      };
      radial.initialize = () => {};
      fg.d3Force("center", null);
      fg.d3Force("radial", radial);

      fgRef.current = fg;
      const validNodeIds = new Set(constel.nodes.map(n => n.id));
      dataRef.current = { 
        nodes: constel.nodes.map(n => ({...n})),
        links: constel.links.filter((l) => validNodeIds.has(l.source?.id || l.source) && validNodeIds.has(l.target?.id || l.target)).map(l => ({...l, source: l.source.id || l.source, target: l.target.id || l.target}))
      };
      fg.graphData(dataRef.current);
      buildMeta(constel);
      // 130px padding keeps the category labels on the rim clear of the tool column.
      setTimeout(() => fg.zoomToFit(600, 130), 900);
    });
    return () => {
      destroyed = true;
      if (flightRef.current) cancelAnimationFrame(flightRef.current);
      try { fgRef.current?._destructor?.(); } catch {}
      fgRef.current = null;
    };
  }, [constel === null]); // eslint-disable-line

  // live node refs per group so callouts track the simulation each frame
  function buildMeta(c) {
    if (!dataRef.current || !c?.comps) { metaRef.current = null; return; }
    const byId = new Map(dataRef.current.nodes.map((n) => [n.id, n]));
    metaRef.current = c.comps.map((m) => ({ ...m, members: m.memberIds.map((id) => byId.get(id)).filter(Boolean) }));
  }

  // morph on data change (timeline / filters), keep the mounted canvas
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || !constel) return;
    focusRef.current = null;
    focusCompRef.current = null;
    onFocus?.(null);
    const validNodeIds = new Set(constel.nodes.map(n => n.id));
    dataRef.current = { nodes: constel.nodes.map((n) => ({ ...n })), links: constel.links.filter((l) => validNodeIds.has(l.source?.id || l.source) && validNodeIds.has(l.target?.id || l.target)).map((l) => ({ ...l, source: l.source.id || l.source, target: l.target.id || l.target })) };
    fg.d3Force("charge")?.strength(groupByRef.current === "type" ? -14 : -80);
    fg.graphData(dataRef.current);
    buildMeta(constel);
    setTimeout(() => fg.zoomToFit(600, 130), 900);
  }, [constel]); // eslint-disable-line

  // Think-flight: agent hubs leave their shell, spiral through the data
  // (satellites trail behind via the link force), then glide home.
  function flyAgents(duration = 3400) {
    const fg = fgRef.current;
    if (!fg || !dataRef.current) return;
    if (flightRef.current) cancelAnimationFrame(flightRef.current);
    const hubs = dataRef.current.nodes.filter((m) => m.role === "agent");
    if (!hubs.length) return;
    const home = hubs.map((h) => ({ h, a0: Math.atan2(h.y, h.x), r0: Math.hypot(h.x, h.y) || h.ring }));
    const t0 = performance.now();
    let lastHeat = 0;
    const tick = (now) => {
      const t = Math.min(1, (now - t0) / duration);
      // radius dips into the core and back (sin envelope); two orbits on the way
      home.forEach(({ h, a0, r0 }, i) => {
        const a = a0 + t * Math.PI * 4 * (i % 2 ? -1 : 1);
        const r = r0 - (r0 - 130) * Math.sin(Math.PI * t);
        h.fx = Math.cos(a) * r;
        h.fy = Math.sin(a) * r;
      });
      if (now - lastHeat > 400) { fg.d3ReheatSimulation(); lastHeat = now; }
      if (t < 1) flightRef.current = requestAnimationFrame(tick);
      else {
        home.forEach(({ h }) => { delete h.fx; delete h.fy; });
        fg.d3ReheatSimulation();
        flightRef.current = null;
      }
    };
    flightRef.current = requestAnimationFrame(tick);
  }

  // parent controls: All Data chip, search find, think flight, deep-link focus
  useEffect(() => {
    if (!controlRef) return;
    controlRef.current = {
      clear: clearFocus,
      refit: () => fgRef.current?.zoomToFit(600, 60),
      think: flyAgents,
      // The FIR drawn nearest a screen point, for dropping a console agent on a record.
      nodeAt: (cx, cy, radius = 26) => {
        const fg = fgRef.current, el = containerRef.current;
        if (!fg || !el || !dataRef.current) return null;
        const box = el.getBoundingClientRect();
        const px = cx - box.left, py = cy - box.top;
        let best = null, bestD = radius * radius;
        for (const m of dataRef.current.nodes) {
          if (m.kind !== "fir" || m.x == null) continue;
          const s = fg.graph2ScreenCoords(m.x, m.y);
          const d = (s.x - px) ** 2 + (s.y - py) ** 2;
          if (d < bestD) { best = m; bestD = d; }
        }
        return best;
      },
      focus: (n) => { if (n) focusComponent(n); },
      find: (q) => {
        const needle = String(q || "").trim().toLowerCase();
        if (!needle || !dataRef.current) return false;
        // rank matches: named hubs first, then linked records, then dust
        const score = (m) => (m.role === "hub" || m.role === "top" ? 2 : m.comm ? 1 : 0);
        let found = null;
        dataRef.current.nodes.forEach((m) => {
          if (m.kind === "agent") return;
          // Only search by ACC-id (m.accused)
          const hay = [m.accused];
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
    const t = setTimeout(() => controlRef?.current?.find?.(focusId), 1500);
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

  return <div ref={containerRef} className="bsx-2d-canvas" />;
}
