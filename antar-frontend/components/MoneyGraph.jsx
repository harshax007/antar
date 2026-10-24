"use client";

import { useEffect, useRef } from "react";

// The money trail as a directed graph (vis-network): one node per account, one arrow per
// payer -> payee pair with the money between them summed. Colour says what an account is;
// arrow width says how much moved. Clicking an account selects it (onSelect).
export const KIND = {
  complainant: { en: "Complainant", kn: "ದೂರುದಾರ", bg: "#1b2a40", border: "#7C93B5" },
  upi: { en: "UPI on an FIR", kn: "FIR ನಲ್ಲಿನ UPI", bg: "#0b3440", border: "#22E6F0" },
  collector: { en: "Collector account", kn: "ಸಂಗ್ರಹ ಖಾತೆ", bg: "#3a2a08", border: "#F59E0B" },
  suspect: { en: "Suspect", kn: "ಶಂಕಿತ", bg: "#3d1414", border: "#F87171" },
  cash: { en: "Cash withdrawal", kn: "ನಗದು ಹಿಂಪಡೆಯುವಿಕೆ", bg: "#2a1d40", border: "#A78BFA" },
};

export const rupees = (n) => {
  const v = Number(n) || 0;
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(2)} L`;
  return `₹${v.toLocaleString("en-IN")}`;
};

export default function MoneyGraph({ data, selected, onSelect }) {
  const ref = useRef(null);
  const net = useRef(null);

  useEffect(() => {
    if (!data || !ref.current) return;
    let destroyed = false;
    (async () => {
      const vis = await import("vis-network/standalone");
      if (destroyed || !ref.current) return;
      const maxAmt = Math.max(1, ...data.edges.map((e) => e.amount));
      const nodes = data.nodes.map((n) => {
        const k = KIND[n.kind] || KIND.upi;
        const root = n.id === data.root;
        const short = n.kind === "complainant" ? "Complainant" : n.kind === "cash" ? "Cash" : n.id;
        return {
          id: n.id,
          label: `${short}\n${rupees(Math.max(n.in, n.out))}`,
          shape: n.kind === "suspect" ? "diamond" : n.kind === "cash" ? "square" : "dot",
          size: root ? 26 : n.kind === "complainant" ? 9 : 14,
          borderWidth: root ? 4 : 2,
          color: { background: k.bg, border: k.border, highlight: { background: k.bg, border: "#ffffff" }, hover: { background: k.bg, border: "#ffffff" } },
          font: { color: n.kind === "complainant" ? "#8FA3BD" : "#F2F5FA", size: root ? 14 : 11, multi: false },
          title: `${n.label}${n.district ? " · " + n.district : ""}\nIn ${rupees(n.in)} · out ${rupees(n.out)}${n.firs ? `\nNamed in ${n.firs} FIR${n.firs === 1 ? "" : "s"}` : ""}`,
        };
      });
      const edges = data.edges.map((e) => ({
        from: e.from, to: e.to, arrows: { to: { enabled: true, scaleFactor: 0.6 } },
        width: 1 + 7 * Math.sqrt(e.amount / maxAmt),
        color: { color: e.purposes.includes("payout") ? "rgba(248,113,113,.55)" : e.purposes.includes("cash_withdrawal") ? "rgba(167,139,250,.6)" : "rgba(148,163,184,.45)", highlight: "#22E6F0", hover: "#22E6F0" },
        title: `${rupees(e.amount)} in ${e.count} transaction${e.count === 1 ? "" : "s"}\n${e.first.slice(0, 10)} to ${e.last.slice(0, 10)} · ${e.channels.join(", ")}`,
        smooth: { type: "dynamic" },
      }));
      if (net.current) net.current.destroy();
      net.current = new vis.Network(ref.current, { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) }, {
        physics: { stabilization: { iterations: 220 }, barnesHut: { springLength: 120, gravitationalConstant: -5200, avoidOverlap: 0.2 } },
        interaction: { hover: true, tooltipDelay: 120, navigationButtons: false },
        layout: { improvedLayout: data.nodes.length < 90 },
      });
      net.current.on("click", (p) => { if (p.nodes?.[0]) onSelect?.(p.nodes[0]); });
      net.current.once("stabilizationIterationsDone", () => net.current?.setOptions({ physics: false }));
    })();
    return () => { destroyed = true; if (net.current) { net.current.destroy(); net.current = null; } };
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    try { if (net.current && selected) net.current.selectNodes([selected]); } catch {}
  }, [selected]);

  return <div ref={ref} className="mt-canvas" aria-label="Money trail graph" />;
}
