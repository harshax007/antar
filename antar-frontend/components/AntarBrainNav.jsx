"use client";

import Link from "next/link";
import { useLang } from "@/components/Providers";

export default function AntarBrainNav() {
  const { lang } = useLang();
  const kn = lang === "kn";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "12px",
        padding: "10px 24px",
        background: "rgba(11, 18, 32, 0.88)",
        borderBottom: "1px solid rgba(34, 230, 240, 0.25)",
        backdropFilter: "blur(12px)",
        position: "sticky",
        top: 0,
        zIndex: 50,
        boxShadow: "0 4px 20px rgba(0,0,0,0.35)"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <span
          style={{
            display: "inline-block",
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: "#22E6F0",
            boxShadow: "0 0 10px #22E6F0"
          }}
        />
        <span
          style={{
            fontFamily: "'Chakra Petch', sans-serif",
            fontWeight: 700,
            fontSize: "14px",
            color: "#FFFFFF",
            letterSpacing: "0.06em",
            textTransform: "uppercase"
          }}
        >
          {kn ? "ಅಂತರ ಬ್ರೇನ್ // ಅಪರಾಧ ಗುಪ್ತಚರ ಮತ್ತು ಸಾಕ್ಷ್ಯ ಜಾಲ" : "ANTAR BRAIN // CRIME INTELLIGENCE & EVIDENCE GRAPH"}
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <Link
          href="/antarBrain"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "6px 16px",
            borderRadius: "9999px",
            fontSize: "13px",
            fontWeight: 600,
            fontFamily: "'Inter', sans-serif",
            textDecoration: "none",
            background: "rgba(34, 230, 240, 0.18)",
            border: "1px solid #22E6F0",
            color: "#22E6F0",
            boxShadow: "0 0 14px rgba(34, 230, 240, 0.35)",
            transition: "all 0.2s ease"
          }}
        >
          <span>{kn ? "ಜ್ಞಾನ ಜಾಲ & ಅವಲೋಕನ" : "Knowledge Graph & Overview"}</span>
        </Link>
      </div>
    </div>
  );
}
