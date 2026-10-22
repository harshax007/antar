"use client";

import { useState, useEffect } from "react";
import { useLang } from "./Providers";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

export default function ShiftBriefingCard({ zone = "all", window = "12h" }) {
  const { lang } = useLang();
  const kn = lang === "kn";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function fetchBriefing() {
      try {
        const res = await fetch(`${API}/api/briefing/shift?zone=${encodeURIComponent(zone)}&window=${encodeURIComponent(window)}`);
        if (res.ok && isMounted) {
          const json = await res.json();
          setData(json);
        }
      } catch (err) {
        console.error("Failed to load shift briefing", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchBriefing();
    // Live polling every 60 seconds (P1/A4 requirement)
    const interval = setInterval(fetchBriefing, 60000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [zone, window]);

  if (loading && !data) {
    return (
      <div className="hx-card glass" style={{ marginBottom: "20px", padding: "16px", borderLeft: "4px solid #22E6F0" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div className="signal-pulse" style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#22E6F0" }} />
          <span style={{ fontSize: "13px", color: "#8B9BB4", fontFamily: "JetBrains Mono" }}>
            {kn ? "ಶಿಫ್ಟ್ ಬ್ರೀಫಿಂಗ್ ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ..." : "Compiling 12h Shift Briefing intelligence..."}
          </span>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="hx-card glass" style={{ marginBottom: "24px", padding: "18px 20px", borderLeft: "4px solid #22E6F0", background: "rgba(11, 18, 32, 0.7)", borderRadius: "12px", boxShadow: "0 4px 20px rgba(0,0,0,0.3)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "10px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "16px" }}>•</span>
          <span style={{ fontWeight: 700, fontSize: "15px", color: "#F2F5FA", letterSpacing: "0.03em" }}>
            {kn ? "ಶಿಫ್ಟ್ ಬ್ರೀಫಿಂಗ್" : "SHIFT BRIEFING"}
          </span>
          <span style={{ fontSize: "12px", padding: "2px 8px", borderRadius: "20px", background: "rgba(34,230,240,0.1)", color: "#22E6F0", fontFamily: "JetBrains Mono" }}>
            {data.zone} · {data.window_hours}h {kn ? "ವಿಂಡೋ" : "Window"}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "12px", padding: "2px 8px", borderRadius: "20px", background: "rgba(255, 69, 58, 0.15)", color: "#FF453A", fontFamily: "JetBrains Mono", fontWeight: 600 }}>
            {data.active_beacons} {kn ? "ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳು" : "Active Beacons"}
          </span>
          <span style={{ fontSize: "11px", color: "#7c8aa0", fontFamily: "JetBrains Mono" }}>
            {new Date(data.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>

      <p style={{ fontSize: "14px", lineHeight: "1.6", color: "#D1D5DB", marginBottom: "14px", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "12px" }}>
        {data.executive_summary}
      </p>

      <div>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          style={{
            background: "transparent",
            border: "1px solid rgba(34,230,240,0.3)",
            padding: "6px 12px",
            borderRadius: "6px",
            color: "#22E6F0",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease"
          }}
        >
          <span>{kn ? "ಆದ್ಯತೆಯ ಕ್ರಮಗಳು" : "Priority Actions"} ({data.priority_actions?.length || 0})</span>
          <span style={{ transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>▼</span>
        </button>

        {expanded && (
          <div style={{ marginTop: "14px", display: "flex", flexDirection: "column", gap: "10px" }}>
            {data.priority_actions?.map((act, i) => (
              <div key={i} style={{ background: "rgba(255,255,255,0.03)", padding: "10px 14px", borderRadius: "8px", borderLeft: "2px solid #22E6F0" }}>
                <div style={{ fontSize: "13px", fontWeight: 600, color: "#F2F5FA", marginBottom: "4px" }}>
                  #{act.rank} - {act.action}
                </div>
                <div style={{ fontSize: "12px", color: "#8B9BB4", fontStyle: "italic" }}>
                  {kn ? "ಕಾರಣ: " : "Rationale: "}{act.rationale}
                </div>
              </div>
            ))}
            
            {data.key_incidents?.length > 0 && (
              <div style={{ marginTop: "8px" }}>
                <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em", color: "#7c8aa0", marginBottom: "6px", fontFamily: "JetBrains Mono" }}>
                  {kn ? "ಪ್ರಮುಖ ಘಟನೆಗಳು" : "Key Incidents Monitored"}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {data.key_incidents.map((inc, j) => (
                    <span key={j} style={{ fontSize: "11px", background: "rgba(255,255,255,0.05)", padding: "3px 8px", borderRadius: "4px", color: "#A5B4FC", fontFamily: "JetBrains Mono" }}>
                      {inc.fir_no} ({inc.crime_type} @ {inc.time})
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


