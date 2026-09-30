"use client";

import { useEffect, useState } from "react";
import NetworkGraph from "@/components/NetworkGraph";
import RefStrip from "@/components/RefStrip";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

export default function NetworkPage() {
  const [picks, setPicks] = useState([{ id: "S0001", name: "Raju K. (cross-case demo)" }]);
  const [sel, setSel] = useState(null);
  const [graph, setGraph] = useState(null);

  useEffect(() => {
    // Suspect picker from the repeat-offender registry; default-load Raju K. (WOW2).
    fetch(`${API}/api/profile/registry?min_priors=5&limit=12`)
      .then((r) => r.json())
      .then((d) => {
        const reg = (d.offenders || [])
          .filter((o) => o.suspect_id !== "S0001")
          .map((o) => ({ id: o.suspect_id, name: o.full_name }));
        setPicks([{ id: "S0001", name: "Raju K. (cross-case demo)" }, ...reg]);
      })
      .catch(() => {});
    const qid = new URLSearchParams(window.location.search).get("suspect_id");
    load(qid || "S0001", qid && qid !== "S0001" ? qid : "Raju K.");

    const handler = (e) => {
      if (e.detail?.wow === 2) {
        load("S0001", "Raju K. (cross-case demo)");
      }
    };
    window.addEventListener("antar-demo-trigger", handler);
    return () => window.removeEventListener("antar-demo-trigger", handler);
  }, []);

  async function load(id, name) {
    setSel({ id, name });
    setGraph({ loading: true });
    try {
      setGraph({ data: await (await fetch(`${API}/api/graph/${id}`)).json() });
    } catch {
      setGraph({ error: true });
    }
  }

  return (
    <div className="page">
      <div className="section-header">
        <h1>Link-Analysis Explorer</h1>
        <span className="sub">criminal networks · Second-Brain cross-case links (amber)</span>
      </div>

      {graph?.data?.nodes && (
        <RefStrip
          tag="K"
          title={`Network for ${sel?.name || sel?.id} - built from recorded case links only`}
          chips={[
            { value: graph.data.stats?.node_count, label: "nodes" },
            { value: graph.data.stats?.edge_count, label: "links" },
            graph.data.brain_banner ? { value: "1", label: "cross-case bridge" } : null,
          ]}
          detailTitle="How this graph is built"
          detail={<p style={{ margin: 0, fontSize: "12px", color: "#9fb3cc", lineHeight: 1.55 }}>
            Edges come from co-accusal records and stored relationships (Adamic-Adar scored,
            k-core flagged). Amber edges are Second-Brain cross-case links; nothing is inferred
            without a recorded connection.
          </p>}
          style={{ marginBottom: 14 }}
        />
      )}

      <div className="panel">
        <div className="suggested" style={{ marginBottom: 6 }}>
          {picks.map((p) => (
            <button key={p.id}
              style={{ borderColor: sel?.id === p.id ? "var(--primary)" : "", color: sel?.id === p.id ? "var(--text-primary)" : "" }}
              onClick={() => load(p.id, p.name)}>
              {p.name}
            </button>
          ))}
        </div>

        {graph?.loading && <div className="loading-block">Building graph…</div>}
        {graph?.error && <div className="loading-block">Could not load that network. Is the backend running?</div>}
        {graph?.data?.brain_banner && <div className="brain-banner">{graph.data.brain_banner}</div>}
        {graph?.data?.nodes && <NetworkGraph data={graph.data} />}
        {graph?.data?.nodes && (
          <div className="graph-legend">
            <span><i className="sw seed" /> queried suspect</span>
            <span><i className="sw cross" /> cross-case (Second Brain)</span>
            <span><i className="sw normal" /> associate</span>
            <span>· {graph.data.stats?.node_count} nodes, {graph.data.stats?.edge_count} links</span>
          </div>
        )}
      </div>
    </div>
  );
}


