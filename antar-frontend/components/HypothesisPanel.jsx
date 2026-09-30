"use client";

import { useState, useEffect } from "react";
import { useLang } from "./Providers";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

export default function HypothesisPanel() {
  const { lang } = useLang();
  const kn = lang === "kn";
  const [hypotheses, setHypotheses] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) fetchHypotheses();
  }, [open]);

  async function fetchHypotheses() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/hypothesis`);
      if (res.ok) {
        const data = await res.json();
        setHypotheses(data.hypotheses || []);
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  }

  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          position: "fixed",
          right: open ? "340px" : "20px",
          top: "80px",
          zIndex: 400,
          background: "rgba(11, 18, 32, 0.9)",
          border: "1px solid rgba(168, 85, 247, 0.5)",
          color: "#D8B4FE",
          padding: "8px 16px",
          borderRadius: "8px",
          fontFamily: "'Chakra Petch', sans-serif",
          fontWeight: 700,
          cursor: "pointer",
          boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
          transition: "right 0.3s ease",
          display: "flex",
          alignItems: "center",
          gap: "8px"
        }}
      >
        <span>{kn ? "ಊಹೆಗಳು" : "HYPOTHESES"}</span>
        <span style={{ 
          background: "rgba(168, 85, 247, 0.2)", 
          padding: "2px 6px", 
          borderRadius: "4px", 
          fontSize: "11px" 
        }}>
          {hypotheses.length > 0 ? hypotheses.length : "A3"}
        </span>
      </button>

      {/* Side Panel */}
      <div
        style={{
          position: "fixed",
          right: open ? 0 : "-340px",
          top: "64px", // Below navbar
          bottom: 0,
          width: "320px",
          background: "rgba(11, 18, 32, 0.95)",
          backdropFilter: "blur(12px)",
          borderLeft: "1px solid rgba(168, 85, 247, 0.4)",
          zIndex: 400,
          transition: "right 0.3s ease",
          boxShadow: "-8px 0 32px rgba(0,0,0,0.6)",
          display: "flex",
          flexDirection: "column",
          padding: "20px"
        }}
      >
        <h3 style={{ margin: "0 0 16px 0", color: "#F3E8FF", fontFamily: "'Chakra Petch', sans-serif", fontSize: "16px", letterSpacing: "0.05em", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{kn ? "ಸಕ್ರಿಯ ಊಹೆಗಳು" : "ACTIVE HYPOTHESES"}</span>
          <button onClick={fetchHypotheses} style={{ background: "transparent", border: "none", color: "#A855F7", cursor: "pointer" }}>↻</button>
        </h3>
        
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "12px" }}>
          {loading && hypotheses.length === 0 ? (
            <div style={{ color: "#94A3B8", fontSize: "12px", fontStyle: "italic" }}>Loading active hypotheses...</div>
          ) : hypotheses.length === 0 ? (
            <div style={{ color: "#94A3B8", fontSize: "12px", fontStyle: "italic" }}>No active hypotheses found. Ask the system to generate some.</div>
          ) : (
            hypotheses.map((h, i) => (
              <div key={i} style={{
                background: "rgba(168, 85, 247, 0.05)",
                border: "1px solid rgba(168, 85, 247, 0.2)",
                borderRadius: "8px",
                padding: "12px"
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span style={{ fontSize: "11px", color: "#D8B4FE", fontFamily: "JetBrains Mono", fontWeight: 700 }}>
                    {h.id || `HYP-${i+1}`}
                  </span>
                  <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "10px", background: "rgba(168,85,247,0.1)", color: "#C084FC" }}>
                    {h.status || "ACTIVE"}
                  </span>
                </div>
                <div style={{ fontSize: "13px", color: "#E2E8F0", lineHeight: 1.4, marginBottom: "8px", fontWeight: 500 }}>
                  {h.description || h.hypothesis || h.title || "Unknown Hypothesis"}
                </div>
                <div style={{ fontSize: "11px", color: "#94A3B8" }}>
                  {kn ? "ವಿಶ್ವಾಸ:" : "Confidence:"} <span style={{ color: "#A855F7" }}>{Math.round((h.confidence || 0) * 100)}%</span>
                </div>
                {(h.evidence || h.linked_entities) && (
                  <div style={{ marginTop: "8px", paddingTop: "8px", borderTop: "1px dashed rgba(255,255,255,0.1)", fontSize: "10px", color: "#64748B" }}>
                    {h.evidence?.length || h.linked_entities?.length || 0} linking data points
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}


