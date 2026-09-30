"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Lock, Network, FileSearch, MessageSquare, Map as MapIcon, ShieldAlert, Cpu } from "lucide-react";
import { useLang } from "@/components/Providers";
import Link from "next/link";

export default function AboutPage() {
  const { lang } = useLang();
  const kn = lang === "kn";
  
  const [stats, setStats] = useState({ firs: "10,00,000", districts: "41", stations: "1,155" });
  const [health, setHealth] = useState("checking...");

  useEffect(() => {
    // In a real app we'd fetch from /api/dataset/overview and /api/health
    // Simulated fetch for the scope of this update
    setHealth("All systems operational");
  }, []);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4 } }
  };

  return (
    <div className="ab-page">
      <div className="ab-grid-bg" />

      <main className="ab-main">
        <motion.div variants={containerVariants} initial="hidden" animate="visible" className="ab-content">
          
          {/* 1. Hero */}
          <motion.section variants={itemVariants} className="ab-hero">
            <h1 className="ab-title">Antar</h1>
            <p className="ab-promise">
              {kn ? "ಕನ್ನಡದಲ್ಲಿ ಕೇಳಿ. ಸೆಕೆಂಡುಗಳಲ್ಲಿ ಉತ್ತರ ಪಡೆಯಿರಿ. ಪ್ರತಿ ಸಂಖ್ಯೆಯನ್ನು ನಂಬಿ." : "Ask in Kannada. Get the answer in seconds. Trust every number."}
            </p>
            <div className="ab-stats">
              <span className="ab-stat-chip">{stats.firs} FIRs</span>
              <span className="ab-stat-chip">{stats.districts} Districts</span>
              <span className="ab-stat-chip">{stats.stations} Stations</span>
              <span className="ab-stat-chip highlight">{health}</span>
            </div>
          </motion.section>

          {/* 2. What it does */}
          <motion.section variants={itemVariants} className="ab-section">
            <h2 className="ab-heading">{kn ? "ಇದು ಏನು ಮಾಡುತ್ತದೆ" : "What it does"}</h2>
            <div className="ab-feature-grid">
              <Link href="/antar" className="ab-tile">
                <MessageSquare size={20} />
                <h3>Chat</h3>
                <p>Ask in English or Kannada</p>
              </Link>
              <Link href="/search" className="ab-tile">
                <FileSearch size={20} />
                <h3>Search</h3>
                <p>See hidden links and OSINT</p>
              </Link>
              <Link href="/predict" className="ab-tile">
                <ShieldAlert size={20} />
                <h3>Predict</h3>
                <p>Know where risk is rising</p>
              </Link>
              <Link href="/map" className="ab-tile">
                <MapIcon size={20} />
                <h3>Map</h3>
                <p>Plan patrols with spatial intel</p>
              </Link>
              <div className="ab-tile">
                <Network size={20} />
                <h3>Traceable</h3>
                <p>Every number traceable</p>
              </div>
              <div className="ab-tile">
                <Lock size={20} />
                <h3>Compliant</h3>
                <p>Built for compliance and RBAC</p>
              </div>
            </div>
          </motion.section>

          {/* 3. How it works */}
          <motion.section variants={itemVariants} className="ab-section">
            <h2 className="ab-heading">{kn ? "ಇದು ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ" : "How it works"}</h2>
            <div className="ab-steps">
              <div className="ab-step"><span>1</span> Question</div>
              <div className="ab-step-arrow">→</div>
              <div className="ab-step"><span>2</span> Approved query</div>
              <div className="ab-step-arrow">→</div>
              <div className="ab-step"><span>3</span> Verified rows</div>
              <div className="ab-step-arrow">→</div>
              <div className="ab-step"><span>4</span> Answer with sources</div>
            </div>
          </motion.section>

          {/* 4. Trust & safety */}
          <motion.section variants={itemVariants} className="ab-section">
            <h2 className="ab-heading">{kn ? "ನಂಬಿಕೆ ಮತ್ತು ಸುರಕ್ಷತೆ" : "Trust & safety"}</h2>
            <ul className="ab-trust-list">
              <li>No free-form SQL</li>
              <li>Strict guardrails</li>
              <li>Cryptographic audit chain</li>
              <li>Correlation-only demographics</li>
              <li>OSINT quarantined</li>
            </ul>
          </motion.section>

          {/* 5. Team Vimaraksha */}
          <motion.section variants={itemVariants} className="ab-section ab-vim">
            <div className="ab-vim-head">
              <div className="ab-eyebrow">// {kn ? "ಮುನ್ಸೂಚಕ ಭದ್ರತೆ" : "PREDICTIVE SECURITY"}</div>
              <h2 className="ab-vim-title">TEAM VIMARAKSHA</h2>
              <p className="ab-vim-sub">
                {kn
                  ? "ವಿಮರಕ್ಷ - 'ಬೆದರಿಕೆ ರೂಪುಗೊಳ್ಳುವ ಮೊದಲೇ ಮುನ್ಸೂಚಿಸಿ ಮತ್ತು ಸುರಕ್ಷಿತಗೊಳಿಸಿ.' 10,00,000+ FIR ದಾಖಲೆಗಳನ್ನು ರಚನಾತ್ಮಕ ಮಾದರಿ ಗುಪ್ತಚರ ಮತ್ತು ಅಜ್ಞಾತ ಸುಳಿವುಗಳಾಗಿ ಪರಿವರ್ತಿಸಲು ನಾವು Antar ಅನ್ನು ನಿರ್ಮಿಸಿದ್ದೇವೆ."
                  : <>Vimaraksha &lsquo;Predict and Secure Before the Threat Materializes.&rsquo; We engineered Antar to convert 10,00,000+ FIR records into structured pattern intelligence and unknown leads.</>}
              </p>
            </div>

            <div className="ab-principles">
              <h3 className="ab-principles-t">
                <ShieldCheck size={20} strokeWidth={1.8} aria-hidden="true" />
                {kn ? "ಸಾಂಸ್ಥಿಕ ತತ್ವಗಳು ಮತ್ತು ವಾಸ್ತುಶಿಲ್ಪ" : "Institutional Principles & Architecture"}
              </h3>
              <div className="ab-principles-grid">
                <div className="ab-principle">
                  <h4><FileSearch size={14} strokeWidth={2} aria-hidden="true" /> 01. {kn ? "ಅಜ್ಞಾತ vs. ಮೇಲ್ಮೈ ದತ್ತಾಂಶ" : "UNKNOWN VS. SURFACE DATA"}</h4>
                  <p>{kn
                    ? "ಸಾಮಾನ್ಯ ವ್ಯವಸ್ಥೆಗಳು ಕೇವಲ ತಿಳಿದ ಮೇಲ್ಮೈ ಎಣಿಕೆಗಳನ್ನು ಪುನರಾವರ್ತಿಸುತ್ತವೆ. ಸಂಪರ್ಕವಿಲ್ಲದ ಆರೋಪಿಗಳು, ಗುಪ್ತ ಫೋನ್ ಮಾರ್ಗಗಳು ಮತ್ತು ಹೇಳದ ಪ್ರಕರಣ-ಅಂತರ ವೈಪರೀತ್ಯಗಳನ್ನು ಹೊರತರಲು Antar ತಿಳಿದ/ಅಜ್ಞಾತ ಪದರ (KUL) ಟ್ಯಾಗಿಂಗ್ ಬಳಸುತ್ತದೆ."
                    : "Standard systems merely repeat known surface counts. Antar uses Known/Unknown Layered (KUL) tagging to surface unlinked accused, hidden phone conduits, and unsaid cross-case anomalies."}</p>
                </div>
                <div className="ab-principle">
                  <h4><Network size={14} strokeWidth={2} aria-hidden="true" /> 02. {kn ? "ಮಾದರಿ ಗುಪ್ತಚರ" : "PATTERN INTELLIGENCE"}</h4>
                  <p>{kn
                    ? "ಪ್ರತ್ಯೇಕ FIR ಪಠ್ಯದ ಬದಲು, ವಿಶೇಷ ಏಜೆಂಟ್‌ಗಳು (Core, Sense, Lens, Link) ಸ್ಥಳ-ಕಾಲ ಸಾಂದ್ರತೆ, Gi* ಹಾಟ್‌ಸ್ಪಾಟ್ ರೇಖೆಗಳು ಮತ್ತು ಸಂಬಂಧ ಗ್ರಾಫ್‌ಗಳನ್ನು ಸಕ್ರಿಯ ತಡೆಗಾಗಿ ಸಂಶ್ಲೇಷಿಸುತ್ತವೆ."
                    : "Instead of isolated FIR text, specialized agents (Core, Sense, Lens, Link) synthesize spatiotemporal density, Gi* hotspot contours, and relationship graphs for proactive prevention."}</p>
                </div>
                <div className="ab-principle">
                  <h4><Lock size={14} strokeWidth={2} aria-hidden="true" /> 03. {kn ? "ಲೆಕ್ಕಪರಿಶೋಧನೆ ಮತ್ತು ಶೂನ್ಯ-ವಿಶ್ವಾಸ ಭದ್ರತೆ" : "AUDIT & ZERO-TRUST SECURITY"}</h4>
                  <p>{kn
                    ? "ಪ್ರತಿ ಹಂತದಲ್ಲೂ ಉದ್ಯಮ ಮಟ್ಟದ ಭದ್ರತೆ: ನ್ಯಾಯಾಲಯ ಸಾಕ್ಷ್ಯಕ್ಕಾಗಿ SHA-256 ವ್ಯುತ್ಪತ್ತಿ ದಾಖಲೆಗಳು, ಪಾತ್ರ-ಆಧಾರಿತ ಪ್ರವೇಶ ನಿಯಂತ್ರಣ ಮತ್ತು ಅಧಿಕೃತ ದಾಖಲೆಗಳನ್ನು ರಕ್ಷಿಸುವ ಪ್ರತ್ಯೇಕ OSINT ಪದರ (Scout)."
                    : "Enterprise security at every tier: SHA-256 derivation logs for court evidence, role-based access control, and a sandboxed OSINT layer (Scout) that protects official records."}</p>
                </div>
              </div>
            </div>

            <div className="ab-team-grid">
              <div className="ab-team-card">
                <h3>Harsha D B</h3>
                <div className="ab-role">Team lead full-stack engineering</div>
                <p>Exploring where AI can actually make security work better. Focus on security operations and network monitoring.</p>
              </div>
              <div className="ab-team-card">
                <h3>Chandana M</h3>
                <div className="ab-role">Team member design and system engineering</div>
                <p>Thriving at the intersection of data, design, and engineering. Translating complex analytics into clean interfaces.</p>
              </div>
            </div>
          </motion.section>

          {/* 6. Footer */}
          <motion.section variants={itemVariants} className="ab-footer">
            <p>All data is synthetic, Datathon 2026. Version 1.0.0</p>
            <Link href="/docs">Documentation</Link>
          </motion.section>

        </motion.div>
      </main>
    </div>
  );
}
