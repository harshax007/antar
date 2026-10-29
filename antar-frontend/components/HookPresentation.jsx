"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, ShieldCheck, Box, Eye } from "lucide-react";
import { DEMO_SESSION } from "@/lib/auth";
import { asset } from "@/lib/assets";
import Architecture3D from "@/components/Architecture3D";

export default function HookPresentation() {
  const router = useRouter();

  // Active 3D Advantage index (0 to 5)
  const [activeAdvantage, setActiveAdvantage] = useState(0);

  // Accordion open states for: Why our solution? How we are achieving it? What we are achieving?
  const [openItems, setOpenItems] = useState({
    "why-0": true,  // The LLM hallucination crisis in policing
    "why-1": false,
    "why-2": false,
    "why-3": false,
    "how-0": true,  // Compiled Directed Acyclic Graph (DAG) state machine
    "how-1": false,
    "how-2": false,
    "how-3": false,
    "how-4": false,
    "what-0": true, // 38 ms Median latency across 20.4 Lakh FIRs
    "what-1": true, // 100% Pass rate on 1-Crore row stress test
    "what-2": false,
    "what-3": false,
    "what-4": false,
  });

  const toggleItem = (key) => {
    setOpenItems(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Ensure body background is pristine white on mount and cleanly reset on unmount
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

  const navigateToConsole = (e) => {
    if (e && e.preventDefault) e.preventDefault();
    try {
      localStorage.setItem("antar_demo_seen", "true");
      localStorage.setItem("antar_hook_seen", "true");
      sessionStorage.setItem("antar_session", JSON.stringify(DEMO_SESSION));
    } catch {}
    window.location.href = "/antar";
  };

  return (
    <div className="hook-page-root">
      {/* Top Header - Minimalist Action Bar */}
      <header className="hook-header">
        <button onClick={navigateToConsole} className="hook-skip-btn">
          <span>Explore Antar</span>
          <ArrowRight size={14} />
        </button>
      </header>

      {/* Main Split Screen */}
      <div className="hook-main">

        {/* LEFT COLUMN: The Editorial Manifesto & Architectural Advantages */}
        <div className="hook-left">
          <div className="hook-manifesto-container">
            {/* Official Brand Logo Mark */}
            <div className="hook-logo-box">
              <img
                src={asset("/brand/antar_final_logo.png")}
                alt="Antar Brand Logo"
                className="hook-hero-logo"
              />
            </div>

            <div className="hook-kicker">WELCOME INSIDE ANTAR</div>
            <h1 className="hook-title">Meet Antar</h1>
            <h2 className="hook-subhead">Intelligent layer for FIR data</h2>

            <div className="hook-copy">
              <p className="hook-lead">
                Law enforcement cannot run on probabilistic guesses. When generic AI hallucinates charges or invents suspect links, evidence falls apart in court.
              </p>

              <p>
                Antar is engineered for verified truth: a <strong>20-agent deterministic orchestrator</strong> that executes exact code over official FIR records, backed by mathematically calibrated forecasting and zero-assumption evidence grounding.
              </p>

              {/* Architectural Advantages Section */}
              <div className="hook-tech-stack">
                <div className="hook-tech-header">
                  <ShieldCheck size={14} className="hook-tech-icon" />
                  <span>Architectural Advantages</span>
                </div>

                {/* 4 Core Pillars with Live 3D & Full Visible Info (No clicking needed) */}
                <Architecture3D />
              </div>

              <p>
                Our claims are empirical and fully reproducible: <strong>93.3% accuracy</strong> on a 150-question gold set, <strong>38 ms median latency</strong> across 20.4 Lakh FIRs, <strong>100% test pass rate</strong> across 1-Crore stress-test records in 241 ms via DuckDB columnar Parquet, and <strong>100% citation provenance</strong> to official General Diary entries.
              </p>

              <p className="hook-closing-note">
                In law enforcement AI, optimizing for immutable grounding and zero hallucination is not just an engineering choice—it is the only standard that withstands legal scrutiny.
              </p>
            </div>
          </div>

          <div className="hook-officer-pill">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span className="hook-status-dot" />
              <span>Officer: <strong>U-7001 (Admin)</strong></span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <ShieldCheck size={13} style={{ color: "#0A7E8C" }} />
              <span>Status: <strong style={{ color: "#0A7E8C" }}>Ready</strong></span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Why our solution? How we are achieving it? What we are achieving? */}
        <div className="hook-right">
          <div className="hook-view-content">

            {/* SECTION 1: Why our solution? (20% Pitch Focus) */}
            <div className="hook-section">
              <div className="hook-section-header-row">
                <h3 className="hook-section-title">1. Why our solution?</h3>
              </div>
              <p className="hook-section-desc">
                Reinterpreting the problem from our team&apos;s perspective: why traditional police software and generic LLMs fail in mission-critical law enforcement.
              </p>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("why-0")} className="hook-acc-header">
                  <span className="hook-acc-name">The evidentiary crisis: Chatbots guess, courtrooms demand proof</span>
                  <span className="hook-acc-icon">{openItems["why-0"] ? "−" : "+"}</span>
                </button>
                {openItems["why-0"] && (
                  <div className="hook-acc-body">
                    General-purpose LLMs are probabilistic word predictors. In official policing and trial litigation, a <mark className="hook-hl">hallucinated penal section</mark>, invented suspect link, or conflation of BNS with IPC <mark className="hook-hl">destroys evidence admissibility</mark> and violates legal due process. Law enforcement cannot run on temperature sampling.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("why-1")} className="hook-acc-header">
                  <span className="hook-acc-name">The security hazard: Why free text-to-SQL is barred in policing</span>
                  <span className="hook-acc-icon">{openItems["why-1"] ? "−" : "+"}</span>
                </button>
                {openItems["why-1"] && (
                  <div className="hook-acc-body">
                    Letting an AI write raw SQL creates catastrophic attack surfaces: <mark className="hook-hl">prompt injection, schema exfiltration</mark>, unindexed full-table scans crashing servers, and unauthorized access across confidential registers. Real-world policing demands <mark className="hook-hl">zero-assumption, parameterized database lookups</mark>.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("why-2")} className="hook-acc-header">
                  <span className="hook-acc-name">Constitutional civil liberties: Stopping algorithmic demographic bias</span>
                  <span className="hook-acc-icon">{openItems["why-2"] ? "−" : "+"}</span>
                </button>
                {openItems["why-2"] && (
                  <div className="hook-acc-body">
                    Predictive policing historically defaulted to biased demographic targeting. Under <mark className="hook-hl">Article 15</mark> of the Constitution of India, profiling citizens by community, religion, or caste is unlawful. Antar enforces pre-execution statutory filters that <mark className="hook-hl">refuse prohibited targeting at the gateway</mark>.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("why-3")} className="hook-acc-header">
                  <span className="hook-acc-name">The evidentiary reproducibility requirement</span>
                  <span className="hook-acc-icon">{openItems["why-3"] ? "−" : "+"}</span>
                </button>
                {openItems["why-3"] && (
                  <div className="hook-acc-body">
                    An investigation query executed by an officer today must yield the <mark className="hook-hl">exact same deterministic numbers</mark>, section references, and General Diary citations when presented before a court magistrate months later. Only deterministic execution meets this judicial standard.
                  </div>
                )}
              </div>
            </div>

            {/* SECTION 2: How we create value (30% Pitch Focus) */}
            <div className="hook-section">
              <div className="hook-section-header-row">
                <h3 className="hook-section-title">2. How we create value</h3>
              </div>
              <p className="hook-section-desc">
                Moving up to the higher architectural level: how our multi-agent engineering architecture, mathematical calibration, and sovereign security controls solve the problem.
              </p>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("how-0")} className="hook-acc-header">
                  <span className="hook-acc-name">Compiled Directed Acyclic Graph (DAG) state machine</span>
                  <span className="hook-acc-icon">{openItems["how-0"] ? "−" : "+"}</span>
                </button>
                {openItems["how-0"] && (
                  <div className="hook-acc-body">
                    Instead of one monolithic model trying to do everything, we orchestrate <mark className="hook-hl">20 specialized micro-agents</mark> via a compiled LangGraph DAG. An intent supervisor routes tasks to discrete specialist nodes (Vault, Network, Motive, Brain) with turn-level state isolation and zero stale memory.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("how-1")} className="hook-acc-header">
                  <span className="hook-acc-name"><mark className="hook-hl">26 Parameterized templates</mark> over verified FIR schemas (Zero Free SQL)</span>
                  <span className="hook-acc-icon">{openItems["how-1"] ? "−" : "+"}</span>
                </button>
                {openItems["how-1"] && (
                  <div className="hook-acc-body">
                    Every natural language question decomposes into strongly typed parameter slots and binds to <mark className="hook-hl">26 hardened templates (T1–T30)</mark>. If every template misses, Antar escalates through an honest <mark className="hook-hl">5-step self-healing ladder</mark>, returning an honest dead-end over an invented record.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("how-2")} className="hook-acc-header">
                  <span className="hook-acc-name">Cryptographic Human-in-the-Loop (AI advises, only named officers act)</span>
                  <span className="hook-acc-icon">{openItems["how-2"] ? "−" : "+"}</span>
                </button>
                {openItems["how-2"] && (
                  <div className="hook-acc-body">
                    To eliminate autonomous policing risks, the AI can propose patrol moves or watchlist additions, but cannot execute them. A supervising officer must review and sign the <mark className="hook-hl">exact SHA-256 payload digest</mark>. Proposals <mark className="hook-hl">expire in 12 hours</mark>, and <mark className="hook-hl">self-approval is cryptographically barred</mark>.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("how-3")} className="hook-acc-header">
                  <span className="hook-acc-name">Native bilingual Kannada NLP pipeline</span>
                  <span className="hook-acc-icon">{openItems["how-3"] ? "−" : "+"}</span>
                </button>
                {openItems["how-3"] && (
                  <div className="hook-acc-body">
                    <mark className="hook-hl">Direct Kannada (ಕನ್ನಡ)</mark> morphological normalization and phonetic stemming parses General Diary narratives and statutory penal sections directly. This eliminates third-party cloud translation latency and ensures sovereign police data <mark className="hook-hl">never leaves the local perimeter</mark>.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("how-4")} className="hook-acc-header">
                  <span className="hook-acc-name">Adversarial Bayesian hypothesis falsification</span>
                  <span className="hook-acc-icon">{openItems["how-4"] ? "−" : "+"}</span>
                </button>
                {openItems["how-4"] && (
                  <div className="hook-acc-body">
                    Confirmation bias is the leading cause of wrongful investigations. Our <mark className="hook-hl">LLM-free Advocate Agent</mark> calculates population base rates and false-discovery corrections, actively arguing against inferred suspect links before an officer anchors on a coincidence.
                  </div>
                )}
              </div>
            </div>

            {/* SECTION 3: What we specifically deliver (50% Pitch Focus) */}
            <div className="hook-section">
              <div className="hook-section-header-row">
                <h3 className="hook-section-title">3. What we specifically deliver</h3>
              </div>
              <p className="hook-section-desc">
                Concrete, measured capabilities and benchmarks across <mark className="hook-hl">20.4 Lakh official FIRs and 1-Crore stress datasets</mark>, with <mark className="hook-hl">93.3% execution accuracy</mark> on a 150-question English and Kannada gold set.
              </p>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("what-0")} className="hook-acc-header">
                  <span className="hook-acc-name"><mark className="hook-hl">38 ms</mark> Median latency <mark className="hook-hl">across 20.4 Lakh official FIRs</mark></span>
                  <span className="hook-acc-icon">{openItems["what-0"] ? "−" : "+"}</span>
                </button>
                {openItems["what-0"] && (
                  <div className="hook-acc-body">
                    Deterministic single-agent fast paths resolve statutory queries in <mark className="hook-hl">38 milliseconds</mark>, directly citing General Diary rows while legacy LLMs spend 15 seconds in hallucination loops.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("what-1")} className="hook-acc-header">
                  <span className="hook-acc-name">1-Crore Row Analytical Stress Benchmark: <mark className="hook-hl">241 ms average</mark> via DuckDB Parquet</span>
                  <span className="hook-acc-icon">{openItems["what-1"] ? "−" : "+"}</span>
                </button>
                {openItems["what-1"] && (
                  <div className="hook-acc-body">
                    Vectorized DuckDB queries scan <mark className="hook-hl">10,000,000 Parquet rows</mark> across 10 ZSTD partitions in an <mark className="hook-hl">average of 241 ms</mark> (<mark className="hook-hl">208× faster than SQLite</mark>), passing <mark className="hook-hl">6 out of 6</mark> analytical stress queries with zero errors.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("what-2")} className="hook-acc-header">
                  <span className="hook-acc-name">Autonomous Spatio-Temporal Anomaly Flagging (<mark className="hook-hl">z = 4.05</mark> Live Spike)</span>
                  <span className="hook-acc-icon">{openItems["what-2"] ? "−" : "+"}</span>
                </button>
                {openItems["what-2"] && (
                  <div className="hook-acc-body">
                    Automatically flags localized crime spikes (such as the Rajajinagar chain-snatching surge) using Mondrian split-conformal prediction intervals that statistically hold <mark className="hook-hl">80%+ of the time</mark>, replacing ungrounded calendar date guesses.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("what-3")} className="hook-acc-header">
                  <span className="hook-acc-name">Cross-District Criminal Syndicate Resolution: <mark className="hook-hl">one UPI ID on 18 FIRs in 4 districts</mark></span>
                  <span className="hook-acc-icon">{openItems["what-3"] ? "−" : "+"}</span>
                </button>
                {openItems["what-3"] && (
                  <div className="hook-acc-body">
                    Discovers hidden organized crime syndicates by connecting repeat phone numbers, mule UPI handles and shared vehicle numbers across multiple police jurisdictions. <mark className="hook-hl">Every link names its shared key</mark>, and gangs are grouped by Louvain community detection.
                  </div>
                )}
              </div>

              <div className="hook-acc-item">
                <button onClick={() => toggleItem("what-4")} className="hook-acc-header">
                  <span className="hook-acc-name">GPU-Accelerated Semantic Vector Recall: 100,000 vectors scanned in <mark className="hook-hl">1.7 ms</mark></span>
                  <span className="hook-acc-icon">{openItems["what-4"] ? "−" : "+"}</span>
                </button>
                {openItems["what-4"] && (
                  <div className="hook-acc-body">
                    PyTorch CUDA similarity scans over 100,000 FIR vectors on a local GTX 1650 GPU in <mark className="hook-hl">1.7 milliseconds</mark> (62 ms on CPU), with <mark className="hook-hl">identical top-10 results</mark> on both.
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* PINNED BOTTOM ACTION BAR */}
          <div className="hook-bottom-bar">
            <div className="hook-bottom-prompt">
              Ready to explore Antar?
            </div>

            <button onClick={navigateToConsole} className="hook-enter-btn">
              <span>Explore Antar</span>
              <ArrowRight size={17} />
            </button>
          </div>

        </div>

      </div>
    </div>
  );
}
