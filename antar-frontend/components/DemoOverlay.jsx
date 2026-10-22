"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useLang } from "@/components/Providers";
import { X, Play, ArrowRight, ShieldCheck, Database, Compass, Cpu } from "lucide-react";

export function toggleDemoMode() {
  window.dispatchEvent(new CustomEvent("antar-demo-toggle-evt"));
}

const FEATURES = [
  {
    id: "AGENT_SPIN",
    titleEn: "Multi-Agent Investigation Spine",
    titleKn: "ಬಹು-ಏಜೆಂಟ್ ತನಿಖಾ ವ್ಯವಸ್ಥೆ",
    descEn: "Run active query routing across Network, Profile, and Pattern correlation agents with live reasoning spin.",
    descKn: "ನೆಟ್‌ವರ್ಕ್, ಪ್ರೊಫೈಲ್ ಮತ್ತು ಮಾದರಿ ಏಜೆಂಟ್‌ಗಳ ಮೂಲಕ ಲೈವ್ ತನಿಖಾ ಪ್ರಶ್ನೆಯನ್ನು ಚಲಾಯಿಸಿ.",
    route: "/antar?q=" + encodeURIComponent("Analyze cross-case links between Raju K. and Hubballi extortion pattern"),
    tagEn: "Agent Spin & New Query",
    tagKn: "ಏಜೆಂಟ್ ಸ್ಪಿನ್ ಹಾಗೂ ಹೊಸ ಪ್ರಶ್ನೆ",
    icon: Cpu,
    color: "#22E6F0"
  },
  {
    id: "UNSUB_PATROL",
    titleEn: "UNSUB Anchor & Dark Zone Radar",
    titleKn: "UNSUB ಆಂಕರ್ ಹಾಗೂ ಡಾರ್ಕ್ ಝೋನ್ ರಾಡಾರ್",
    descEn: "Explore spatial crime corridor predictions and unindexed geographical dark zones across Karnataka.",
    descKn: "ಕರ್ನಾಟಕದಾದ್ಯಂತ ಅಪರಾಧ ಕಾರಿಡಾರ್ ಮುನ್ಸೂಚನೆಗಳನ್ನು ಅನ್ವೇಷಿಸಿ.",
    route: "/map",
    tagEn: "Spatial Intelligence",
    tagKn: "ಪ್ರಾದೇಶಿಕ ಗುಪ್ತಚರ",
    icon: Compass,
    color: "#06B6D4"
  },
  {
    id: "DOSSIER_BRIEF",
    titleEn: "Investigation Briefing & Derivation Chain",
    titleKn: "ತನಿಖಾ ಬ್ರೀಫಿಂಗ್ ಹಾಗೂ ಸಾಕ್ಷ್ಯ ಸರಪಳಿ",
    descEn: "Review cryptographic derivation chains and CCTNS / ICJS verified evidence shift briefings.",
    descKn: "CCTNS ಪರಿಶೀಲಿತ ಸಾಕ್ಷ್ಯ ಸರಪಳಿಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
    route: "/docs",
    tagEn: "Investigation Blueprint",
    tagKn: "ತನಿಖಾ ನೀಲನಕ್ಷೆ",
    icon: ShieldCheck,
    color: "#10B981"
  }
];

export default function DemoOverlay() {
  const router = useRouter();
  const { lang } = useLang();
  const kn = lang === "kn";

  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = () => setOpen((prev) => !prev);
    window.addEventListener("antar-demo-toggle-evt", handler);
    return () => window.removeEventListener("antar-demo-toggle-evt", handler);
  }, []);

  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 500,
        background: "rgba(3, 7, 18, 0.82)",
        backdropFilter: "blur(14px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px"
      }}
    >
      <div
        style={{
          background: "linear-gradient(145deg, rgba(15,23,42,0.96) 0%, rgba(11,18,32,0.98) 100%)",
          border: "1px solid rgba(34, 230, 240, 0.35)",
          borderRadius: "20px",
          width: "100%",
          maxWidth: "680px",
          boxShadow: "0 20px 60px rgba(0, 0, 0, 0.7)",
          overflow: "hidden"
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(255, 255, 255, 0.02)"
          }}
        >
          <div>
            <div
              style={{
                fontFamily: "'Chakra Petch', sans-serif",
                fontWeight: 700,
                fontSize: "16px",
                color: "#FFFFFF",
                letterSpacing: "0.05em",
                textTransform: "uppercase",
                display: "flex",
                alignItems: "center",
                gap: "10px"
              }}
            >
              <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#22E6F0", boxShadow: "0 0 10px #22E6F0" }} />
              {kn ? "ಅಂತರ್ ವೈಶಿಷ್ಟ್ಯಗಳನ್ನು ಪ್ರಯೋಗಿಸಿ" : "TRY ANTAR FEATURES // INTERACTIVE SUITE"}
            </div>
            <div style={{ fontSize: "12px", color: "#94A3B8", marginTop: "4px" }}>
              {kn
                ? "ಲೈವ್ ಏಜೆಂಟ್ ಸ್ಪಿನ್ ಮತ್ತು ನೈಜ-ಸಮಯದ ದತ್ತಾಂಶದೊಂದಿಗೆ ವೈಶಿಷ್ಟ್ಯಗಳನ್ನು ಪರೀಕ್ಷಿಸಿ"
                : "Launch active multi-agent investigation workflows and live evidence pipelines"}
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: "8px",
              padding: "6px",
              color: "#E2E8F0",
              cursor: "pointer"
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Features List */}
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: "14px" }}>
          {FEATURES.map((feat) => {
            const Icon = feat.icon;
            return (
              <div
                key={feat.id}
                onClick={() => {
                  setOpen(false);
                  router.push(feat.route);
                }}
                style={{
                  padding: "16px",
                  borderRadius: "14px",
                  background: "rgba(255, 255, 255, 0.03)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  cursor: "pointer",
                  transition: "color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease, transform 0.2s ease, scale 0.2s ease"
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: "14px", maxWidth: "80%" }}>
                  <div
                    style={{
                      padding: "10px",
                      borderRadius: "10px",
                      background: `${feat.color}15`,
                      border: `1px solid ${feat.color}40`,
                      color: feat.color,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center"
                    }}
                  >
                    <Icon size={20} />
                  </div>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                      <span style={{ fontSize: "14px", fontWeight: 700, color: "#FFFFFF" }}>
                        {kn ? feat.titleKn : feat.titleEn}
                      </span>
                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 600,
                          padding: "2px 8px",
                          borderRadius: "999px",
                          background: `${feat.color}20`,
                          color: feat.color,
                          border: `1px solid ${feat.color}40`
                        }}
                      >
                        {kn ? feat.tagKn : feat.tagEn}
                      </span>
                    </div>
                    <div style={{ fontSize: "12px", color: "#94A3B8", lineHeight: "1.4" }}>
                      {kn ? feat.descKn : feat.descEn}
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    padding: "8px 14px",
                    borderRadius: "8px",
                    background: "rgba(34, 230, 240, 0.12)",
                    border: "1px solid rgba(34, 230, 240, 0.35)",
                    color: "#22E6F0",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "12px",
                    fontWeight: 600
                  }}
                >
                  <span>{kn ? "ಪ್ರಯೋಗಿಸಿ" : "Try Now"}</span>
                  <ArrowRight size={14} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "14px 24px",
            background: "rgba(0, 0, 0, 0.25)",
            borderTop: "1px solid rgba(255, 255, 255, 0.06)",
            fontSize: "11px",
            color: "#64748B",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between"
          }}
        >
          <span>100% CCTNS / ICJS COMPLIANT ARCHITECTURE</span>
          <span>MULTI-AGENT REASONING SPINE</span>
        </div>
      </div>
    </div>
  );
}
