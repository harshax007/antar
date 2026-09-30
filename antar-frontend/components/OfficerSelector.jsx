"use client";

import React, { useState, useEffect } from "react";
import { Shield } from "lucide-react";
import { useLang } from "@/components/Providers";
import { useRouter } from "next/navigation";

export function getActiveOfficerId() {
  if (typeof window === "undefined") return "U-7001";
  try {
    const sessionStr = sessionStorage.getItem("antar_session");
    if (sessionStr) {
      const session = JSON.parse(sessionStr);
      return session.officer || "U-7001";
    }
  } catch {}
  return "U-7001";
}

export default function OfficerSelector({ pending = 0 }) {
  const { lang } = useLang();
  const kn = lang === "kn";
  const router = useRouter();
  
  const [officer, setOfficer] = useState("U-7001");
  const [role, setRole] = useState("Inspector");

  useEffect(() => {
    try {
      const sessionStr = sessionStorage.getItem("antar_session");
      if (sessionStr) {
        const session = JSON.parse(sessionStr);
        if (session.officer) setOfficer(session.officer);
        if (session.role) setRole(session.role);
      }
    } catch {}
  }, []);

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <button
        type="button"
        onClick={() => router.push("/account")}
        title={pending > 0
          ? (kn ? `ಖಾತೆ - ${pending} ಅನುಮೋದನೆ ಬಾಕಿ` : `Account - ${pending} approval${pending === 1 ? "" : "s"} waiting`)
          : (kn ? "ಖಾತೆ ಪುಟಕ್ಕೆ ಹೋಗಿ" : "Go to Account Page")}
        style={{
          background: "transparent",
          border: "none",
          color: "rgba(255, 255, 255, 0.55)",
          fontFamily: "'Inter', sans-serif",
          fontSize: "10.5px",
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          padding: "4px 8px",
          cursor: "pointer",
          transition: "all 0.2s ease",
          display: "flex",
          alignItems: "center",
          gap: "6px",
        }}
        onMouseOver={(e) => e.currentTarget.style.color = "#FFFFFF"}
        onMouseOut={(e) => e.currentTarget.style.color = "rgba(255, 255, 255, 0.55)"}
      >
        {kn ? "ಖಾತೆ" : "ACCOUNT"}
        {pending > 0 && (
          <span className="nav-badge" aria-label={kn ? `${pending} ಅನುಮೋದನೆ ಬಾಕಿ` : `${pending} pending approval${pending === 1 ? "" : "s"}`}>
            {pending > 99 ? "99+" : pending}
          </span>
        )}
      </button>
    </div>
  );
}
