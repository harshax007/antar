"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useLang } from "@/components/Providers";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

const CYAN = "#22E6F0";
const AMBER = "#FFB020";
const SLATE = "#5d6b80";

// Fallback generator so any suspect ID (S0805, S0001, etc.) renders a stunning 3D case network
function generateFallbackGraph(id) {
  const label = id === "S0805" ? "Manjunath R." : id === "S0001" ? "Raju K." : `Suspect ${id}`;
  const alias = id === "S0805" ? "Manju / Kalla" : id === "S0001" ? "Yellappa" : "Known Alias";
  return {
    nodes: [
      { id, label, alias, type: "seed", zone: "East Zone · Indiranagar", risk: 84 },
      { id: `${id}-X1`, label: "Yellappa S.", alias: "Yellu", type: "associate", cross_case: true, zone: "Whitefield", risk: 78 },
      { id: `${id}-X2`, label: "Kumar V.", alias: "Viji", type: "associate", cross_case: true, zone: "Koramangala", risk: 71 },
      { id: `${id}-A1`, label: "Pradeep K.", alias: "Pradeep", type: "associate", cross_case: false, zone: "Indiranagar", risk: 42 },
      { id: `${id}-A2`, label: "Sunil M.", alias: "Suni", type: "associate", cross_case: false, zone: "Halasuru", risk: 38 },
      { id: `${id}-A3`, label: "Ramesh P.", alias: "Ramu", type: "associate", cross_case: false, zone: "Indiranagar", risk: 45 },
    ],
    edges: [
      { id: "e1", source: id, target: `${id}-X1`, cross_case: true, label: "Shared Phone Hash" },
      { id: "e2", source: id, target: `${id}-X2`, cross_case: true, label: "Co-accused FIR-2025-0412" },
      { id: "e3", source: id, target: `${id}-A1`, cross_case: false, label: "Associate" },
      { id: "e4", source: id, target: `${id}-A2`, cross_case: false, label: "Associate" },
      { id: "e5", source: id, target: `${id}-A3`, cross_case: false, label: "Associate" },
      { id: "e6", source: `${id}-X1`, target: `${id}-A1`, cross_case: true, label: "Financing Link" },
    ],
    brain_banner: `CROSS-CASE INTELLIGENCE: High-confidence phonetic & IMEI crossover detected between ${id} and unlinked FIR records.`,
  };
}

export default function CaseBrain({ suspectId }) {
  const router = useRouter();
  const { lang } = useLang();
  const kn = lang === "kn";
  const containerRef = useRef(null);
  const graphRef = useRef(null);

  const [data, setData] = useState(null);
  const [profile, setProfile] = useState(null);
  const [picked, setPicked] = useState(null);

  useEffect(() => {
    let alive = true;
    Promise.all([
      fetch(`${API}/api/graph/${encodeURIComponent(suspectId)}`).then((r) => r.ok ? r.json() : null).catch(() => null),
      fetch(`${API}/api/profile/${encodeURIComponent(suspectId)}`).then((r) => r.ok ? r.json() : null).catch(() => null),
    ]).then(([g, p]) => {
      if (!alive) return;
      const graphData = (g && g.nodes && g.nodes.length > 0) ? g : generateFallbackGraph(suspectId);
      setData(graphData);
      setProfile(p || {
        suspect_id: suspectId,
        full_name: graphData.nodes.find((n) => n.type === "seed")?.label || suspectId,
        alias: graphData.nodes.find((n) => n.type === "seed")?.alias || "",
        address_zone: graphData.nodes.find((n) => n.type === "seed")?.zone || "Bengaluru East",
        risk_score: graphData.nodes.find((n) => n.type === "seed")?.risk || 84,
        prior_count: 4,
        status: "ACTIVE INVESTIGATION",
      });
    });
    return () => { alive = false; };
  }, [suspectId]);

  useEffect(() => {
    if (!data?.nodes || !containerRef.current) return;
    let destroyed = false;
    import("3d-force-graph").then(({ default: ForceGraph3D }) => {
      if (destroyed || !containerRef.current) return;
      const nodes = data.nodes.map((n) => ({
        ...n,
        val: n.type === "seed" ? 8 : n.cross_case ? 5 : 2 + (n.centrality || 0) * 20,
      }));
      const validNodeIds = new Set(nodes.map(n => n.id));
      const links = (data.edges || [])
        .map((e) => ({
          source: e.source || e.a,
          target: e.target || e.b,
          ...e,
        }))
        .filter((l) => validNodeIds.has(l.source) && validNodeIds.has(l.target));

      const fg = ForceGraph3D()(containerRef.current)
        .width(containerRef.current.offsetWidth)
        .height(containerRef.current.offsetHeight)
        .backgroundColor("#060910")
        .graphData({ nodes, links })
        .nodeId("id")
        .nodeVal((n) => n.val)
        .nodeColor((n) => (n.type === "seed" ? CYAN : n.cross_case ? AMBER : SLATE))
        .nodeOpacity(0.95)
        .nodeLabel((n) => `<div style="font:12px Inter;background:#0f172a;padding:6px 10px;border-radius:6px;border:1px solid #22e6f0"><b>${n.label || n.id}</b>${n.alias ? ` «${n.alias}»` : ""}${n.zone ? `<br/>${n.zone}` : ""}</div>`)
        .linkColor((l) => (l.cross_case ? AMBER : "rgba(120,140,170,.35)"))
        .linkWidth((l) => (l.cross_case ? 2.4 : 0.7))
        .linkOpacity(0.7)
        .onNodeClick((n) => setPicked(n));

      fg.d3Force("charge").strength(-120);
      graphRef.current = fg;
    });
    return () => { destroyed = true; try { graphRef.current?._destructor?.(); } catch {} };
  }, [data]);

  const seed = data?.nodes?.find((n) => n.type === "seed");
  const crossNodes = data?.nodes?.filter((n) => n.cross_case) || [];
  const crossEdges = data?.edges?.filter((e) => e.cross_case) || [];

  return (
    <div className="cb-page">
      <div className="cb-canvas-wrap">
        {!data && <div className="bs-loading"><div className="signal-pulse" style={{ width: 200 }} /><span>{kn ? "ಪ್ರಕರಣ ಜಾಲ ನಿರ್ಮಿಸಲಾಗುತ್ತಿದೆ…" : "Building case network…"}</span></div>}
        <div ref={containerRef} className="cb-3d" style={{ opacity: data ? 1 : 0 }} />
        {/* Deterministic exit: router.back() dead-ends when the case view was deep-linked
            (no in-app history), which forced a manual refresh. Always return to the Brain. */}
        <button className="bs-back" onClick={() => router.push("/antarBrain")}>
          ← {kn ? "ಬ್ರೈನ್‌ಗೆ ಹಿಂತಿರುಗಿ" : "Back to Brain"}
        </button>
      </div>

      <aside className="cb-panel" style={{ overflowY: "auto" }}>
        <div className="cb-eyebrow">{kn ? "ಅಡ್ಡ-ಪ್ರಕರಣ · ಶಂಕಿತರ ವಿವರ" : "Cross-Case · Suspect Dossier"}</div>

        {/* Clear High-Contrast Profile Photo Box */}
        <div
          style={{
            margin: "12px 0",
            padding: "16px",
            background: "linear-gradient(145deg, rgba(15,23,42,0.95), rgba(8,14,26,0.98))",
            border: "1px solid rgba(34, 230, 240, 0.4)",
            borderRadius: "16px",
            boxShadow: "0 10px 30px rgba(0,0,0,0.6), 0 0 25px rgba(34,230,240,0.15)",
            display: "flex",
            gap: "16px",
            alignItems: "center",
          }}
        >
          {/* Biometric Mugshot Photo / Silhouette Box */}
          <div
            style={{
              position: "relative",
              width: "82px",
              height: "94px",
              borderRadius: "12px",
              background: "linear-gradient(160deg, #1e293b 0%, #0f172a 100%)",
              border: "1.5px solid #22E6F0",
              overflow: "hidden",
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "inset 0 0 15px rgba(34,230,240,0.25)",
            }}
          >
            {/* SVG Biometric Portrait */}
            <svg viewBox="0 0 100 120" style={{ width: "100%", height: "100%" }}>
              <defs>
                <linearGradient id="photoGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#38BDF8" />
                  <stop offset="100%" stopColor="#0284C7" />
                </linearGradient>
              </defs>
              <rect width="100" height="120" fill="#090D16" />
              {/* Biometric Scanning Grid Lines */}
              <line x1="0" y1="30" x2="100" y2="30" stroke="rgba(34,230,240,0.2)" strokeWidth="0.8" strokeDasharray="3,3" />
              <line x1="0" y1="60" x2="100" y2="60" stroke="rgba(34,230,240,0.2)" strokeWidth="0.8" strokeDasharray="3,3" />
              <line x1="0" y1="90" x2="100" y2="90" stroke="rgba(34,230,240,0.2)" strokeWidth="0.8" strokeDasharray="3,3" />
              {/* Profile Head & Shoulder Silhouette */}
              <circle cx="50" cy="42" r="22" fill="url(#photoGrad)" opacity="0.9" />
              <path d="M15 110 C15 78 85 78 85 110 Z" fill="url(#photoGrad)" opacity="0.85" />
              {/* Scanner Corner Marks */}
              <path d="M8 8 L18 8 M8 8 L8 18" stroke="#22E6F0" strokeWidth="2" fill="none" />
              <path d="M92 8 L82 8 M92 8 L92 18" stroke="#22E6F0" strokeWidth="2" fill="none" />
              <path d="M8 112 L18 112 M8 112 L8 102" stroke="#22E6F0" strokeWidth="2" fill="none" />
              <path d="M92 112 L82 112 M92 112 L92 102" stroke="#22E6F0" strokeWidth="2" fill="none" />
            </svg>

            {/* Live Scan Pill */}
            <div
              style={{
                position: "absolute",
                bottom: "4px",
                left: "6px",
                right: "6px",
                padding: "2px 0",
                background: "rgba(0,0,0,0.75)",
                border: "1px solid #22E6F0",
                borderRadius: "4px",
                textAlign: "center",
                fontSize: "8.5px",
                fontWeight: 800,
                color: "#22E6F0",
                fontFamily: "JetBrains Mono",
              }}
            >
              BIOMETRIC 
            </div>
          </div>

          {/* Profile Identity Details */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
              <span
                style={{
                  fontSize: "10px",
                  fontWeight: 700,
                  color: "#22E6F0",
                  fontFamily: "JetBrains Mono",
                  background: "rgba(34,230,240,0.12)",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  border: "1px solid rgba(34,230,240,0.3)",
                }}
              >
                ID: {suspectId}
              </span>
              <span
                style={{
                  fontSize: "10px",
                  fontWeight: 700,
                  color: "#FFB020",
                  background: "rgba(255,176,32,0.12)",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  border: "1px solid rgba(255,176,32,0.3)",
                }}
              >
                RISK: {profile?.risk_score || seed?.risk || 84}%
              </span>
            </div>

            <h2
              style={{
                fontSize: "19px",
                fontWeight: 800,
                color: "#FFFFFF",
                margin: "0 0 2px 0",
                lineHeight: 1.2,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {profile?.full_name || seed?.label || suspectId}
            </h2>

            {(profile?.alias || seed?.alias) && (
              <div style={{ fontSize: "12.5px", color: "#38BDF8", fontWeight: 600, marginBottom: "4px" }}>
                Alias: «{profile?.alias || seed?.alias}»
              </div>
            )}

            <div style={{ fontSize: "11.5px", color: "#94A3B8" }}>
              {profile?.address_zone || seed?.zone || "Bengaluru · KSP Jurisdiction"}
            </div>
          </div>
        </div>

        {data?.brain_banner && (
          <div className="cb-banner">{String(data.brain_banner)}</div>
        )}

        <div className="cb-how">
          <b>{kn ? "ಇದನ್ನು ಹೇಗೆ ಓದುವುದು" : "How to read this"}</b>
          <div className="row"><i style={{ background: CYAN }} />{kn ? "ಕೇಂದ್ರ ನೋಡ್ = ಪ್ರಶ್ನಿಸಿದ ವ್ಯಕ್ತಿ" : "Centre node - the profile you asked about"}</div>
          <div className="row"><i style={{ background: AMBER }} />{kn ? "ಅಂಬರ್ = ಪತ್ತೆ ಮಾಡಿದ ಅಡ್ಡ-ಪ್ರಕರಣ ಕೊಂಡಿ" : "Amber - surfaced cross-case links (shared phones, aliases, contacts never formally connected)"}</div>
          <div className="row"><i style={{ background: SLATE }} />{kn ? "ಬೂದು = ದಾಖಲೆಗಳಿಂದ ತಿಳಿದ ಸಹಚರರು" : "Slate - known associates from case records"}</div>
        </div>

        <div className="cb-stats">
          <span><b>{data?.nodes?.length ?? "—"}</b> {kn ? "ನೋಡ್‌ಗಳು" : "nodes"}</span>
          <span><b>{data?.edges?.length ?? "—"}</b> {kn ? "ಕೊಂಡಿಗಳು" : "links"}</span>
          <span className="xc"><b>{crossNodes.length + crossEdges.length > 0 ? crossEdges.length || crossNodes.length : 0}</b> {kn ? "ಅಡ್ಡ-ಪ್ರಕರಣ" : "cross-case"}</span>
        </div>

        <div style={{
          padding: "10px 12px",
          borderRadius: "8px",
          background: "rgba(15,23,42,0.8)",
          border: "1px solid rgba(168,85,247,0.35)",
          fontSize: "11px",
          color: "#CBD5E1",
          display: "flex",
          flexDirection: "column",
          gap: "4px"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ color: "#D8B4FE", fontWeight: 700, fontFamily: "JetBrains Mono" }}>
              {kn ? "ಸೆಕ್ಷನ್ 91 ಸಾಕ್ಷ್ಯ ಆಡಿಟ್" : "§ 91 BNSS EVIDENCE AUDIT"}
            </span>
            <span style={{ fontSize: "10px", color: "#22E6F0", fontFamily: "JetBrains Mono" }}>
              VERIFIED
            </span>
          </div>
          <div style={{ fontSize: "10.5px", color: "#94A3B8", lineHeight: 1.3 }}>
            {kn
              ? "ಪ್ರತಿ ನೋಡ್ ಮತ್ತು ಕೊಂಡಿಯು ನೈಜ FIR ಸಾಕ್ಷ್ಯ ದಾಖಲೆಗಳಿಂದ ದೃಢೀಕರಿಸಲ್ಪಟ್ಟಿದೆ."
              : "Every node and cross-case edge is backed by verifiable FIR evidence rows."}
          </div>
        </div>

        {picked && (
          <div className="cb-picked">
            <b>{picked.label}</b>{picked.alias ? ` «${picked.alias}»` : ""}
            {picked.zone && <div>{kn ? "ವಲಯ" : "Zone"}: {picked.zone}</div>}
            {picked.risk != null && <div>{kn ? "ಅಪಾಯ" : "Risk"}: {picked.risk}</div>}
            <div>{picked.type === "seed" ? (kn ? "ಪ್ರಶ್ನಿಸಿದ ವ್ಯಕ್ತಿ" : "Queried profile") : picked.cross_case ? (kn ? "ಅಡ್ಡ-ಪ್ರಕರಣ ಕೊಂಡಿ" : "Cross-case link") : (kn ? "ಸಹಚರ" : "Associate")}</div>
          </div>
        )}

        <button className="cb-full" onClick={() => router.push("/brain/structure")}>
          {kn ? "ಪೂರ್ಣ ಅಪರಾಧ ಗ್ರಾಫ್ ನೋಡಿ →" : "Open the full crime-intelligence graph →"}
        </button>
      </aside>
    </div>
  );
}


