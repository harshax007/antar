"use client";
import React, { useState, useEffect } from "react";
import { useLang } from "./Providers";
import { apiFetch } from "@/lib/api";

export default function AlertsDrawer() {
  const { lang } = useLang();
  const kn = lang === "kn";
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [scanning, setScanning] = useState(false);

  const loadAlerts = async () => {
    try {
      const res = await apiFetch("/api/alerts?limit=15");
      if (res && res.alerts) {
        setAlerts(res.alerts);
      }
    } catch (e) {
      console.error("Failed to load alerts:", e);
    }
  };

  useEffect(() => {
    loadAlerts();
    const timer = setInterval(loadAlerts, 15000);
    return () => clearInterval(timer);
  }, []);

  const triggerScan = async () => {
    setScanning(true);
    try {
      await apiFetch("/api/sentinel/scan", { method: "POST" });
      await loadAlerts();
    } catch (e) {
      console.error("Scan failed:", e);
    } finally {
      setScanning(false);
    }
  };

  const highAlertsCount = alerts.filter(a => a.severity === "high" || a.alert_type === "sentinel_tripwire").length;

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <button 
        onClick={() => setOpen(!open)}
        style={{
          background: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.15)",
          borderRadius: "8px",
          padding: "6px 12px",
          cursor: "pointer",
          color: "#fff",
          display: "flex",
          alignItems: "center",
          gap: "6px",
          position: "relative",
          fontWeight: 600,
          fontFamily: "'Chakra Petch', sans-serif"
        }}
        title={kn ? "ಲೈವ್ ಎಚ್ಚರಿಕೆಗಳು" : "Live Alerts & Tripwires"}
      >
        <span style={{ fontSize: "16px" }}></span>
        {alerts.length > 0 && (
          <span style={{
            background: highAlertsCount > 0 ? "#ff3838" : "#22e6f0",
            color: highAlertsCount > 0 ? "#fff" : "#000",
            borderRadius: "12px",
            padding: "1px 6px",
            fontSize: "11px",
            fontWeight: 800
          }}>
            {alerts.length}
          </span>
        )}
      </button>

      {open && (
        <div style={{
          position: "absolute",
          top: "100%",
          right: 0,
          marginTop: "8px",
          width: "360px",
          maxHeight: "480px",
          overflowY: "auto",
          background: "rgba(10, 16, 28, 0.95)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(34, 230, 240, 0.3)",
          borderRadius: "12px",
          padding: "16px",
          boxShadow: "0 12px 32px rgba(0,0,0,0.6)",
          zIndex: 300,
          color: "#fff",
          textAlign: "left"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "8px" }}>
            <h4 style={{ margin: 0, fontSize: "14px", fontFamily: "'Chakra Petch'", color: "#22e6f0", textTransform: "uppercase" }}>
              {kn ? "ಲೈವ್ ಟ್ರಿಪ್‌ವೈರ್ ಎಚ್ಚರಿಕೆಗಳು" : "Antar Live Alerts"}
            </h4>
            <button 
              onClick={triggerScan}
              disabled={scanning}
              style={{
                background: "rgba(34,230,240,0.15)",
                border: "1px solid #22e6f0",
                color: "#22e6f0",
                borderRadius: "6px",
                padding: "4px 8px",
                fontSize: "11px",
                cursor: "pointer",
                fontWeight: 700
              }}
            >
              {scanning ? "..." : (kn ? "ಮರುಪರಿಶೀಲಿಸಿ" : "Run Scan")}
            </button>
          </div>

          {alerts.length === 0 ? (
            <p style={{ fontSize: "13px", color: "#888", textAlign: "center", margin: "20px 0" }}>
              {kn ? "ಯಾವುದೇ ಹೊಸ ಎಚ್ಚರಿಕೆಗಳಿಲ್ಲ" : "No active tripwire alerts."}
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {alerts.map((a, i) => (
                <div key={i} style={{
                  padding: "10px",
                  background: "rgba(255,255,255,0.04)",
                  borderLeft: `3px solid ${a.severity === "high" || a.alert_type === "sentinel_tripwire" ? "#ff3838" : "#f5a623"}`,
                  borderRadius: "6px",
                  fontSize: "12px"
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span style={{ fontWeight: 700, color: a.severity === "high" ? "#ff6b6b" : "#f5a623" }}>
                      {a.alert_type === "sentinel_tripwire" ? "ANTAR ALERT" : (a.crime_type || "ALERT")}
                    </span>
                    <span style={{ fontSize: "10px", color: "#888" }}>
                      {a.timestamp ? new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Just now"}
                    </span>
                  </div>
                  <p style={{ margin: "4px 0", lineHeight: "1.4", color: "#ddd" }}>
                    {a.message || a.suggestion}
                  </p>
                  {a.zone && (
                    <span style={{ display: "inline-block", background: "rgba(255,255,255,0.08)", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", color: "#bbb", marginTop: "4px" }}>
                      {a.zone}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
