"use client";

import { useEffect, useRef } from "react";

// Renders a criminal-network graph with vis-network.
// Cross-case nodes/edges use AMBER (reserved for the Second Brain); seed is a blue star.
export default function NetworkGraph({ data }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!data || !ref.current) return;
    let network;
    let destroyed = false;

    (async () => {
      const vis = await import("vis-network/standalone");
      if (destroyed || !ref.current) return;

      const AMBER = "#F59E0B";
      const nodes = data.nodes.map((n) => ({
        id: n.id,
        label: n.label + (n.alias ? `\n«${n.alias}»` : ""),
        shape: n.type === "seed" ? "star" : "dot",
        size: n.type === "seed" ? 30 : 12 + (n.centrality || 0.0) * 160,
        borderWidth: n.cross_case ? 3 : 1,
        color:
          n.type === "seed"
            ? { background: "#3B82F6", border: "#93c5fd" }
            : n.cross_case
            ? { background: "#3a2a08", border: AMBER }
            : { background: "#16233f", border: "#33456e" },
        font: { color: "#F2F5FA", size: 13, multi: true },
        title: `${n.label}${n.zone ? " · " + n.zone : ""} · PageRank ${n.centrality || 0.0} · risk ${n.risk}`,
      }));

      const edges = data.edges.map((e) => ({
        from: e.a,
        to: e.b,
        label: (e.rel_type || "").replace(/_/g, " "),
        dashes: e.cross_case,
        width: e.cross_case ? 3 : 1,
        color: { color: e.cross_case ? AMBER : "#46587f" },
        font: { color: "#9AA8C7", size: 10, strokeWidth: 0 },
        smooth: { type: "continuous" },
      }));

      // Add Jaccard predicted link edges dynamically as dashed cyan lines
      const predictedEdges = (data.predicted_links || []).map((p) => ({
        from: p.a,
        to: p.b,
        label: `predicted (${Math.round(p.probability * 100)}%)`,
        dashes: [4, 4],
        width: 1.5,
        color: { color: "rgba(0, 240, 255, 0.4)" }, // Cyan primary tint
        font: { color: "rgba(0, 240, 255, 0.7)", size: 9, strokeWidth: 0 },
        smooth: { type: "continuous" },
      }));

      const allEdges = [...edges, ...predictedEdges];

      network = new vis.Network(
        ref.current,
        { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(allEdges) },
        {
          physics: { stabilization: true, barnesHut: { springLength: 130, gravitationalConstant: -6000 } },
          interaction: { hover: true, tooltipDelay: 120 },
          nodes: { shadow: false },
        }
      );
    })();

    return () => {
      destroyed = true;
      if (network) network.destroy();
    };
  }, [data]);

  return <div ref={ref} className="graph-canvas" />;
}
