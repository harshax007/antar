"use client";

import { useState, useEffect } from "react";
import { useLang } from "./Providers";
import { useRouter } from "next/navigation";

const API = (process.env.NEXT_PUBLIC_API_URL || "");

export default function SentinelWatchdog() {
  const { lang } = useLang();
  const router = useRouter();
  const kn = lang === "kn";
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    let active = true;
    async function checkAlerts() {
      try {
        const res = await fetch(`${API}/api/sentinel`);
        if (res.ok && active) {
          const data = await res.json();
          const newAlerts = data.alerts || [];
          setAlerts(newAlerts);
          // Auto-open if there is a critical alert we haven't seen yet
          // For now, keep it simple: just load them
        }
      } catch (err) {
        console.error("Sentinel fetch error:", err);
      }
    }
    
    checkAlerts();
    const timer = setInterval(checkAlerts, 30000); // poll every 30s
    return () => { active = false; clearInterval(timer); };
  }, []);

  if (alerts.length === 0) return null;

  return (
    <button
      onClick={() => router.push("/account?section=alerts")}
      style={{
        position: "fixed",
        bottom: "90px",
        left: "24px",
        zIndex: 500,
        background: "rgba(239, 68, 68, 0.15)",
        border: "1px solid rgba(239, 68, 68, 0.5)",
        color: "#FCA5A5",
        padding: "8px 14px",
        borderRadius: "999px",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: "12px",
        fontWeight: 700,
        cursor: "pointer",
        backdropFilter: "blur(10px)",
        boxShadow: "0 4px 12px rgba(239,68,68,0.2)",
        display: "flex",
        alignItems: "center",
        gap: "8px"
      }}
    >
      <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#EF4444", boxShadow: "0 0 8px #EF4444", animation: "pulse 2s infinite" }} />
      ANTAR ALERTS ({alerts.length})
    </button>
  );
}


