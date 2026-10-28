"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";

export default function HookPresentation() {
  const router = useRouter();

  // Clean accordion states - matching reference screenshot (console.typesafe.ai/hook)
  const [openItems, setOpenItems] = useState({
    "prop-2": true, // Consistent, calibrated, probabilistic results
    "lim-2": true,  // Not an autonomous generative chat model
    "ben-2": true   // Frontier-level intelligence for System 1 tasks
  });

  const toggleItem = (key) => {
    setOpenItems(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Ensure body background is clean white on mount and reset on unmount
  useEffect(() => {
    const prevBg = document.body.style.backgroundColor;
    const prevColor = document.body.style.color;
    document.body.style.backgroundColor = "#FFFFFF";
    document.body.style.color = "#111827";
    return () => {
      document.body.style.backgroundColor = prevBg;
      document.body.style.color = prevColor;
    };
  }, []);

  const navigateToConsole = () => {
    try {
      localStorage.setItem("antar_hook_seen", "true");
    } catch {}
    router.push("/antar");
  };

  return (
    <div className="hook-page-root">
      {/* Top Header - Ultra Minimal Brand + Direct Entry */}
      <header className="hook-header">
        <div className="hook-brand">
          <svg width="24" height="24" viewBox="0 0 44 44" fill="none" style={{ color: "#111827" }}>
            <path d="M22 2L4 12V32L22 42L40 32V12L22 2Z" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M22 22L40 12" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
            <path d="M22 22V42" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
            <path d="M22 22L4 12" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
            <circle cx="22" cy="22" r="3.5" fill="currentColor"/>
          </svg>
          <span style={{ fontWeight: 800, fontSize: "14px", letterSpacing: "-0.01em" }}>ANTAR</span>
        </div>

        <button onClick={navigateToConsole} className="hook-skip-btn">
          <span>Enter console</span>
          <ArrowRight size={14} />
        </button>
      </header>

      {/* Main Split Screen */}
      <div className="hook-main">

        {/* LEFT COLUMN: The Editorial Manifesto (1:1 with reference) */}
        <div className="hook-left">
          <div>
            {/* Geometric Isometric Logo Mark */}
            <div className="hook-logo-box">
              <svg width="42" height="42" viewBox="0 0 44 44" fill="none" style={{ color: "#111827" }}>
                <path d="M22 2L4 12V32L22 42L40 32V12L22 2Z" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M22 22L40 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                <path d="M22 22V42" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                <path d="M22 22L4 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                <circle cx="22" cy="22" r="3" fill="currentColor"/>
              </svg>
            </div>

            <div className="hook-kicker">WELCOME INSIDE ANTAR</div>
            <h1 className="hook-title">Meet Antar</h1>
            <h2 className="hook-subhead">Our first (public) System One model for Law Enforcement</h2>

            <div className="hook-copy">
              <p>
                We&apos;re excited to share with you a new class of intelligence architecture optimized for official police operations. Think: <strong>Mission-critical deterministic code execution, not probabilistic chatbot guesses.</strong>
              </p>
              <p>
                For the last two years, police engineering teams struggled with modern LLMs: hallucinated FIR charges, ungrounded suspect links, mode dropping, and the complete lack of reproducibility inherent to free-form generation. Antar replaces black-box SQL queries with a 20-agent deterministic orchestrator, Mondrian conformal forecasting, and zero-assumption evidence grounding.
              </p>
              <p>
                Our claims may sound bold—<strong>38 ms median gold-suite latency</strong> across 20.4 Lakh FIRs, 84.2% synthetically linked graph resolution, and 100% citation provenance to official General Diary entries—but the bitter lesson in policing AI is that optimizing for immutable grounding gets you an unfair advantage.
              </p>
            </div>

            <div className="hook-closing">
              May your investigations be ever grounded in truth,
            </div>

            {/* Handwritten Signature SVG */}
            <div className="hook-signature-box">
              <svg width="220" height="50" viewBox="0 0 220 50" fill="none" style={{ color: "#111827" }}>
                <path d="M12 36C25 24 38 12 55 18C72 24 45 42 35 34C25 26 62 10 78 20C94 30 70 45 95 38C120 31 140 16 160 22C180 28 175 40 195 32C205 28 212 20 215 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M42 22C60 22 75 18 90 26" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <div className="hook-sig-title">
                TEAM VIMARAKSHA · KARNATAKA POLICE LAB
              </div>
            </div>
          </div>

          <div className="hook-officer-pill">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#10B981" }} />
              <span>Officer: <strong style={{ color: "#111827" }}>U-7001 (Admin)</strong></span>
            </div>
            <span>Status: <strong>Ready</strong></span>
          </div>
        </div>

        {/* RIGHT COLUMN: Pure Minimal Accordion (No extra boxes) */}
        <div className="hook-right">
          <div className="hook-view-content">

            {/* 1. Properties */}
            <div className="hook-section">
              <h3 className="hook-section-title">Properties</h3>
              <p className="hook-section-desc">
                Antar has a fundamentally different architecture with locked schemas, zero free SQL, and deterministic verification.
              </p>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("prop-0")} className="hook-acc-header">
                  <span className="hook-acc-name">Structured, machine-native outputs</span>
                  <span className="hook-acc-icon">{openItems["prop-0"] ? "−" : "+"}</span>
                </button>
                {openItems["prop-0"] && (
                  <div className="hook-acc-body">
                    Antar never generates free-form or unconstrained SQL. Every query maps directly to whitelisted analytical templates (T1–T30) over verified KSP schema tables, guaranteeing zero SQL injection and zero schema fabrication.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("prop-1")} className="hook-acc-header">
                  <span className="hook-acc-name">Parallel sampling for fast decisions</span>
                  <span className="hook-acc-icon">{openItems["prop-1"] ? "−" : "+"}</span>
                </button>
                {openItems["prop-1"] && (
                  <div className="hook-acc-body">
                    The LangGraph supervisor classifies officer intent into canonical route labels (VAULT, LINK, MOTIVE, CORE, LENS, TRACE, BRAIN). Specialist agents execute concurrently in parallel threads, bounded by strict orchestrator timeouts.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("prop-2")} className="hook-acc-header">
                  <span className="hook-acc-name">Consistent, calibrated, probabilistic results</span>
                  <span className="hook-acc-icon">{openItems["prop-2"] ? "−" : "+"}</span>
                </button>
                {openItems["prop-2"] && (
                  <div className="hook-acc-body">
                    Antar tells you when it&apos;s uncertain with a confidence value and Mondrian conformal risk interval (83% coverage). Each decision is a calibrated probability, so similar inputs give similar, auditable outputs.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("prop-3")} className="hook-acc-header">
                  <span className="hook-acc-name">Bilingual native intelligence (Kannada & English)</span>
                  <span className="hook-acc-icon">{openItems["prop-3"] ? "−" : "+"}</span>
                </button>
                {openItems["prop-3"] && (
                  <div className="hook-acc-body">
                    Trained directly on Kannada (ಕನ್ನಡ) General Diary narratives, crime classification taxonomies, and statutory legal penal sections (IPC and BNS), ensuring zero translation friction during field inquiries.
                  </div>
                )}
              </div>
            </div>

            {/* 2. Limitations */}
            <div className="hook-section">
              <h3 className="hook-section-title">Limitations</h3>
              <p className="hook-section-desc">
                Our model is powerful, but there are real tradeoffs and statutory guardrails we want to be honest about.
              </p>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("lim-0")} className="hook-acc-header">
                  <span className="hook-acc-name">Not good at System 2 creative writing</span>
                  <span className="hook-acc-icon">{openItems["lim-0"] ? "−" : "+"}</span>
                </button>
                {openItems["lim-0"] && (
                  <div className="hook-acc-body">
                    Antar refuses to generate speculative fiction or hypothetical charges. It requires grounding in registered FIR numbers, suspect ledgers, or crime patterns.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("lim-1")} className="hook-acc-header">
                  <span className="hook-acc-name">Not trained for demographic profiling</span>
                  <span className="hook-acc-icon">{openItems["lim-1"] ? "−" : "+"}</span>
                </button>
                {openItems["lim-1"] && (
                  <div className="hook-acc-body">
                    The Vigil compliance agent strictly audits all prompts before execution. Any attempt to target or profile by religion, caste, or protected demographics is immediately blocked under Article 15 of the Indian Constitution.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("lim-2")} className="hook-acc-header">
                  <span className="hook-acc-name">Not an autonomous generative chat model</span>
                  <span className="hook-acc-icon">{openItems["lim-2"] ? "−" : "+"}</span>
                </button>
                {openItems["lim-2"] && (
                  <div className="hook-acc-body">
                    Antar doesn&apos;t generate ungrounded prose, so you can&apos;t chat aimlessly with it. To ask it questions, requests map to structured legal parameters and verified FIR registries. Patrol redeployments and watchlist additions require written cryptographic sign-off by a supervising officer.
                  </div>
                )}
              </div>
            </div>

            {/* 3. Benefits */}
            <div className="hook-section">
              <h3 className="hook-section-title">Benefits</h3>
              <p className="hook-section-desc">
                We get that these are big claims, and we&apos;re excited to prove them to you across 20.4 Lakh FIRs.
              </p>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("ben-0")} className="hook-acc-header">
                  <span className="hook-acc-name">20–200× faster decisions (38 ms median latency)</span>
                  <span className="hook-acc-icon">{openItems["ben-0"] ? "−" : "+"}</span>
                </button>
                {openItems["ben-0"] && (
                  <div className="hook-acc-body">
                    Deterministic ZCQL fast paths resolve complex statutory queries in 38 ms, compared to 15-second multi-turn reasoning loops in standard generic LLMs.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("ben-1")} className="hook-acc-header">
                  <span className="hook-acc-name">Adversarial hypothesis falsification</span>
                  <span className="hook-acc-icon">{openItems["ben-1"] ? "−" : "+"}</span>
                </button>
                {openItems["ben-1"] && (
                  <div className="hook-acc-body">
                    Before an officer accepts an inferred suspect connection, the Advocate Agent calculates population base rates and false-discovery corrections, actively arguing against suspect links before confirmation bias can settle.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("ben-2")} className="hook-acc-header">
                  <span className="hook-acc-name">Frontier-level intelligence for System 1 tasks</span>
                  <span className="hook-acc-icon">{openItems["ben-2"] ? "−" : "+"}</span>
                </button>
                {openItems["ben-2"] && (
                  <div className="hook-acc-body">
                    On tasks that call for instinctive judgment and deterministic pattern recognition over large official police datasets, Antar gives verified answers with 100% citation provenance to General Diary numbers.
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* PINNED BOTTOM ACTION BAR (1:1 with console.typesafe.ai/hook) */}
          <div className="hook-bottom-bar">
            <div className="hook-bottom-prompt">
              Ready to test our claims?
            </div>

            <button onClick={navigateToConsole} className="hook-enter-btn">
              <span>Enter console</span>
              <ArrowRight size={17} />
            </button>
          </div>

        </div>

      </div>
    </div>
  );
}
