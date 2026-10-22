"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Brain, Network, TrendingUp, ArrowRight } from "lucide-react";

export default function ThreePillarsCards({ lang = "en", onSelectPillar }) {
  const kn = lang === "kn";
  const [activeCard, setActiveCard] = useState(null);

  const pillars = [
    {
      id: "sec-think",
      number: "01",
      titleEn: "THINK // COGNITIVE ENGINE",
      titleKn: "ಆಲೋಚನೆ // ಬೌದ್ಧಿಕ ಎಂಜಿನ್",
      taglineEn: "Multi-Agent Synthesis & 4-Section RAG",
      taglineKn: "ಮಲ್ಟಿ-ಏಜೆಂಟ್ ಸಂಶ್ಲೇಷಣೆ ಮತ್ತು 4-ವಿಭಾಗ RAG",
      descEn: "Deconstructs free-form queries in English and Kannada across 18 specialized intelligence agents with live audit trail.",
      descKn: "ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡದ ಪ್ರಶ್ನೆಗಳನ್ನು 18 ವಿಶೇಷ ತನಿಖಾ ಏಜೆಂಟ್‌ಗಳ ಮೂಲಕ ಲೈವ್ ಆಡಿಟ್‌ನೊಂದಿಗೆ ವಿಶ್ಲೇಷಿಸುತ್ತದೆ.",
      icon: Brain,
      color: "#22E6F0",
      glow: "rgba(34, 230, 240, 0.22)",
      borderColor: "rgba(34, 230, 240, 0.35)",
      stats: [
        { labelEn: "Agents", labelKn: "ಏಜೆಂಟ್‌ಗಳು", val: "18 Active" },
        { labelEn: "Latency", labelKn: "ಪ್ರತಿಕ್ರಿಯೆ", val: "< 400ms" },
      ],
    },
    {
      id: "sec-connect",
      number: "02",
      titleEn: "CONNECT // CROSS-CASE LINKAGE",
      titleKn: "ಸಂಪರ್ಕ // ಪ್ರಕರಣಗಳ ಜೋಡಣೆ",
      taglineEn: "Bipartite Graph & Phonetic Resolution",
      taglineKn: "ಬೈಪಾರ್ಟೈಟ್ ಜಾಲ ಮತ್ತು ಧ್ವನಿ ಸಾಮ್ಯತೆ",
      descEn: "Bridges unlinked FIRs, aliases, and phone hashes using O(1) bipartite structural cosine similarity and Soundex matching.",
      descKn: "ಸಂಪರ್ಕವಿಲ್ಲದ FIR ಗಳು ಮತ್ತು ಅಡ್ಡಹೆಸರುಗಳನ್ನು ಬೈಪಾರ್ಟೈಟ್ ಜಾಲ ಮತ್ತು ಧ್ವನಿ ಸಾಮ್ಯತೆಯ ಮೂಲಕ ಜೋಡಿಸುತ್ತದೆ.",
      icon: Network,
      color: "#FFB020",
      glow: "rgba(255, 176, 32, 0.22)",
      borderColor: "rgba(255, 176, 32, 0.35)",
      stats: [
        { labelEn: "Graph Engine", labelKn: "ಜಾಲ ಎಂಜಿನ್", val: "Bipartite" },
        { labelEn: "Resolution", labelKn: "ನಿಖರತೆ", val: "99.2%" },
      ],
    },
    {
      id: "sec-anticipate",
      number: "03",
      titleEn: "ANTICIPATE // PREDICTIVE ARCHITECTURE",
      titleKn: "ಮುನ್ಸೂಚನೆ // ಭವಿಷ್ಯಸೂಚಕ ಎಂಜಿನ್",
      taglineEn: "Bayesian Silence & Adaptive Conformal Bands",
      taglineKn: "ಬೇಸಿಯನ್ ಮೌನ ಪತ್ತೆ ಮತ್ತು ಅಡಾಪ್ಟಿವ್ ಬ್ಯಾಂಡ್‌ಗಳು",
      descEn: "Flags statistically anomalous reporting drops using conjugate Poisson-Gamma change-points and dynamically calibrated ACI bounds.",
      descKn: "ವರದಿಗಳಲ್ಲಿನ ಅಸಹಜ ಇಳಿಕೆಯನ್ನು ಬೇಸಿಯನ್ ಮಾದರಿ ಮತ್ತು ಅಡಾಪ್ಟಿವ್ ಕಾನ್ಫಾರ್ಮಲ್ ಬ್ಯಾಂಡ್‌ಗಳ ಮೂಲಕ ಪತ್ತೆಮಾಡುತ್ತದೆ.",
      icon: TrendingUp,
      color: "#18D69A",
      glow: "rgba(24, 214, 154, 0.22)",
      borderColor: "rgba(24, 214, 154, 0.35)",
      stats: [
        { labelEn: "Change-Point", labelKn: "ಬದಲಾವಣೆ ಪತ್ತೆ", val: "BF10 > 3.0" },
        { labelEn: "Conformal Coverage", labelKn: "ಭರವಸೆ", val: "90% ACI" },
      ],
    },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.12,
        delayChildren: 0.05,
      },
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 24, scale: 0.96 },
    show: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 110,
        damping: 15,
      },
    },
  };

  return (
    <div style={{ width: "100%", margin: "24px 0 36px" }}>
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))",
          gap: "20px",
          width: "100%",
        }}
      >
        {pillars.map((pillar) => {
          const IconComponent = pillar.icon;
          const isHovered = activeCard === pillar.id;

          return (
            <motion.div
              key={pillar.id}
              variants={cardVariants}
              whileHover={{
                y: -6,
                scale: 1.015,
                transition: { duration: 0.2, ease: "easeOut" },
              }}
              onMouseEnter={() => setActiveCard(pillar.id)}
              onMouseLeave={() => setActiveCard(null)}
              onClick={() => onSelectPillar && onSelectPillar(pillar.id)}
              style={{
                position: "relative",
                cursor: "pointer",
                borderRadius: "20px",
                padding: "24px",
                background: isHovered
                  ? "linear-gradient(145deg, rgba(17, 26, 54, 0.88) 0%, rgba(10, 15, 30, 0.95) 100%)"
                  : "linear-gradient(145deg, rgba(11, 18, 32, 0.76) 0%, rgba(6, 10, 18, 0.85) 100%)",
                backdropFilter: "blur(20px)",
                WebkitBackdropFilter: "blur(20px)",
                border: isHovered
                  ? `1px solid ${pillar.color}`
                  : `1px solid ${pillar.borderColor}`,
                boxShadow: isHovered
                  ? `0 16px 40px rgba(0,0,0,0.65), 0 0 28px ${pillar.glow}`
                  : "0 10px 30px rgba(0,0,0,0.45)",
                transition: "color 0.25s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.25s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.25s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.25s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1), transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), scale 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                overflow: "hidden",
              }}
            >
              {/* Subtle top accent beam */}
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: "15%",
                  right: "15%",
                  height: "2px",
                  background: `linear-gradient(90deg, transparent, ${pillar.color}, transparent)`,
                  opacity: isHovered ? 1 : 0.6,
                  transition: "opacity 0.25s",
                }}
              />

              {/* Card Header */}
              <div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: "16px",
                  }}
                >
                  <div
                    style={{
                      fontFamily: "'Chakra Petch', monospace",
                      fontSize: "13px",
                      fontWeight: 700,
                      color: pillar.color,
                      letterSpacing: "0.15em",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <span>{pillar.number}</span>
                    <span style={{ opacity: 0.4 }}>//</span>
                    <span>{kn ? pillar.titleKn : pillar.titleEn}</span>
                  </div>

                  <div
                    style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      background: "rgba(255, 255, 255, 0.05)",
                      border: `1px solid ${pillar.borderColor}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: pillar.color,
                      boxShadow: isHovered ? `0 0 14px ${pillar.glow}` : "none",
                      transition: "box-shadow 0.25s",
                    }}
                  >
                    <IconComponent size={18} />
                  </div>
                </div>

                {/* Subtitle / Tagline */}
                <div
                  style={{
                    fontSize: "16px",
                    fontWeight: 700,
                    color: "#FFFFFF",
                    marginBottom: "10px",
                    lineHeight: 1.35,
                    fontFamily: "'Outfit', sans-serif",
                  }}
                >
                  {kn ? pillar.taglineKn : pillar.taglineEn}
                </div>

                {/* Description */}
                <p
                  style={{
                    fontSize: "13.5px",
                    color: "#94A3B8",
                    lineHeight: 1.6,
                    margin: "0 0 20px 0",
                  }}
                >
                  {kn ? pillar.descKn : pillar.descEn}
                </p>
              </div>

              {/* Footer KPI Row */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  paddingTop: "14px",
                  borderTop: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <div style={{ display: "flex", gap: "16px" }}>
                  {pillar.stats.map((stat, i) => (
                    <div key={i}>
                      <div
                        style={{
                          fontSize: "10px",
                          textTransform: "uppercase",
                          letterSpacing: "0.08em",
                          color: "#64748B",
                        }}
                      >
                        {kn ? stat.labelKn : stat.labelEn}
                      </div>
                      <div
                        style={{
                          fontSize: "13px",
                          fontWeight: 700,
                          fontFamily: "'JetBrains Mono', monospace",
                          color: pillar.color,
                        }}
                      >
                        {stat.val}
                      </div>
                    </div>
                  ))}
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: isHovered ? pillar.color : "#94A3B8",
                    transition: "color 0.2s",
                  }}
                >
                  <span>{kn ? "ಅನ್ವೇಷಿಸಿ" : "Explore"}</span>
                  <ArrowRight size={14} />
                </div>
              </div>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
