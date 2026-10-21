"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Scan,
  ShieldAlert,
  UserCheck,
  Cpu,
  TrendingUp,
  X,
  CheckCircle2,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  Layers,
  Sparkles,
  GitBranch,
  Database,
  Terminal,
  Activity,
  Eye,
  Check,
  XCircle
} from "lucide-react";

export function PredictSubWindows({ activeModal, onClose }) {
  if (!activeModal) return null;

  return (
    <AnimatePresence>
      {activeModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 md:p-6"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 15 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 15 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            className="relative w-full max-w-6xl max-h-[90vh] flex flex-col rounded-2xl bg-[#070a0f] border border-white/15 shadow-[0_0_50px_rgba(34,230,240,0.12)] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/[0.02]">
              <div className="flex items-center gap-3">
                {activeModal === "ocr" && (
                  <>
                    <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                      <Scan className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-white tracking-wide">
                        Multimodal FIR & Scanned Evidence OCR Workbench
                      </h3>
                      <p className="text-xs text-white/60">
                        Qwen 3.6 Vision-Language (35B-A3B) · Forensic Extraction & K/D/I/U Derivation
                      </p>
                    </div>
                  </>
                )}
                {activeModal === "trends" && (
                  <>
                    <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                      <TrendingUp className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-white tracking-wide">
                        Deep Learning Trends & Crime Behavior Modeling
                      </h3>
                      <p className="text-xs text-white/60">
                        Spatio-Temporal Pattern Mining · Gi* Hotspot Uplift · Scenario Confidence Bands
                      </p>
                    </div>
                  </>
                )}
                {activeModal === "victim" && (
                  <>
                    <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-400">
                      <UserCheck className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-white tracking-wide">
                        Victim Identification ML & Cross-Source Matching
                      </h3>
                      <p className="text-xs text-white/60">
                        Biometric & Demographics Vector Resolver · Anonymized CCTNS Correlation
                      </p>
                    </div>
                  </>
                )}
                {activeModal === "agentic" && (
                  <>
                    <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
                      <Cpu className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-white tracking-wide">
                        System Architecture & Model Routing Inspector
                      </h3>
                      <p className="text-xs text-white/60">
                        Linear Workflow vs Autonomous Execution vs Role-Based Execution vs Product Orchestrator
                      </p>
                    </div>
                  </>
                )}
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 text-white/90">
              {activeModal === "ocr" && <EvidenceOCRContent />}
              {activeModal === "trends" && <TrendMiningContent />}
              {activeModal === "victim" && <VictimMLContent />}
              {activeModal === "agentic" && <AgenticArchitectureContent />}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between px-6 py-3 border-t border-white/10 bg-white/[0.015] text-xs text-white/50">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                Concept preview - live equivalents run in the chat & predict pipelines
              </span>
              <button
                onClick={onClose}
                className="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white font-medium transition-colors"
              >
                Close Sub-Window
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function EvidenceOCRContent() {
  const [zoom, setZoom] = useState(1);
  const [showBoundingBoxes, setShowBoundingBoxes] = useState(true);
  const [items, setItems] = useState([
    { id: 1, type: "K", code: "KNOWN", label: "Accused Entity Identified", value: "Raju K. (Alias: Rajna) · Habitual offender ID #KA-BLR-099", status: "confirmed" },
    { id: 2, type: "D", code: "DERIVED", label: "Corridor Linkage", value: "Rajajinagar 3rd Block → Chord Road Exit Route", status: "confirmed" },
    { id: 3, type: "I", code: "INFERRED", label: "Accomplice Hypothesis", value: "Deepa Biradar linked via mobile cell tower overlap at 23:14", status: "pending" },
    { id: 4, type: "U", code: "UNSUB", label: "Unsub Anchor Area", value: "Dark zone pocket detected around West of Chord Road", status: "pending" }
  ]);

  const handleToggleStatus = (id, newStatus) => {
    setItems((prev) =>
      prev.map((it) => (it.id === id ? { ...it, status: newStatus } : it))
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full min-h-[480px]">
      {/* Left Pane: Interactive Document & CCTV Viewer */}
      <div className="lg:col-span-6 flex flex-col rounded-xl border border-white/10 bg-black/40 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/10 bg-white/[0.03]">
          <span className="text-xs font-medium text-white/70">
            Source Document: Scanned FIR #0492/2024 (Rajajinagar PS)
          </span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setShowBoundingBoxes(!showBoundingBoxes)}
              className={`px-2 py-1 rounded text-xs border ${
                showBoundingBoxes
                  ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-300"
                  : "bg-white/5 border-white/10 text-white/50"
              }`}
            >
              OCR Overlay
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.75, z - 0.25))}
              className="p-1 rounded bg-white/5 hover:bg-white/10 text-white/70"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-xs font-mono text-cyan-400 w-10 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={() => setZoom((z) => Math.min(2.0, z + 0.25))}
              className="p-1 rounded bg-white/5 hover:bg-white/10 text-white/70"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Canvas Area */}
        <div className="flex-1 relative overflow-auto flex items-center justify-center p-6 bg-[#040609]">
          <div
            style={{ transform: `scale(${zoom})`, transformOrigin: "center center" }}
            className="relative transition-transform duration-200 w-full max-w-md bg-[#0d121c] border border-white/15 rounded-lg p-5 font-mono text-xs leading-relaxed text-white/80 shadow-2xl"
          >
            <div className="border-b border-white/10 pb-3 mb-3 flex justify-between items-center text-[10px] text-white/50">
              <span>FIRST INFORMATION REPORT (UNDER SECTION 154 Cr.P.C.)</span>
              <span>STATE OF KARNATAKA</span>
            </div>
            <p className="text-cyan-400 font-semibold mb-2">
              STATION: RAJAJINAGAR PS | CRIME NO: 492/2024
            </p>
            <p className="text-white/70 mb-3">
              DATE & TIME: 10/10/2024 22:45 HRS | OFFENCE: SECTION 309(4) BNS
            </p>
            <p className="text-white/60 mb-4">
              COMPLAINANT STATEMENT: Complainant Smt. Lakshmi R. reports that while walking near 3rd Block park, two unidentified persons on a black pulsar motorcycle snatched her gold chain weighing 35g and fled towards Mysore Road exit.
            </p>
            {showBoundingBoxes && (
              <div className="space-y-2 border-t border-white/10 pt-3">
                <div className="p-1.5 rounded bg-cyan-500/15 border border-cyan-500/40 text-cyan-300 text-[11px] flex justify-between">
                  <span>VEHICLE DETECTED: Pulsar Black (KA-04-EY-****)</span>
                  <span className="font-bold">98.4% OCR</span>
                </div>
                <div className="p-1.5 rounded bg-purple-500/15 border border-purple-500/40 text-purple-300 text-[11px] flex justify-between">
                  <span>MODUS OPERANDI: High-Speed Pillion Snatch</span>
                  <span className="font-bold">95.1% Conf</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right Pane: Live Structured Intelligence Extraction Tags */}
      <div className="lg:col-span-6 flex flex-col rounded-xl border border-white/10 bg-black/40 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-white/10 bg-white/[0.03] flex justify-between items-center">
          <span className="text-xs font-medium text-white/70">
            Forensic Intelligence Extraction (K/D/I/U Ledger)
          </span>
          <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            4 Elements Extracted
          </span>
        </div>

        <div className="p-4 space-y-3 overflow-y-auto flex-1">
          {items.map((it) => {
            const isConfirmed = it.status === "confirmed";
            const isRejected = it.status === "rejected";
            return (
              <div
                key={it.id}
                className={`p-3.5 rounded-xl border transition-all ${
                  isConfirmed
                    ? "bg-emerald-500/10 border-emerald-500/40"
                    : isRejected
                    ? "bg-red-500/10 border-red-500/40 opacity-50"
                    : "bg-white/[0.03] border-white/10"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold ${
                        it.type === "K"
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                          : it.type === "D"
                          ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40"
                          : it.type === "I"
                          ? "bg-purple-500/20 text-purple-400 border border-purple-500/40"
                          : "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                      }`}
                    >
                      {it.type}
                    </span>
                    <span className="text-xs font-semibold text-white">
                      {it.label}
                    </span>
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleToggleStatus(it.id, "confirmed")}
                      className={`p-1 rounded hover:bg-emerald-500/20 text-emerald-400 transition-colors ${
                        isConfirmed ? "bg-emerald-500/30" : ""
                      }`}
                      title="Confirm Hypothesis"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleToggleStatus(it.id, "rejected")}
                      className={`p-1 rounded hover:bg-red-500/20 text-red-400 transition-colors ${
                        isRejected ? "bg-red-500/30" : ""
                      }`}
                      title="Reject Hypothesis"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <p className="text-xs text-white/80 pl-8 leading-relaxed">
                  {it.value}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function TrendMiningContent() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="text-xs text-white/50 uppercase tracking-wider mb-1">
            Primary Trend Pattern
          </div>
          <div className="text-lg font-semibold text-cyan-400">
            Dasara Festival Surge (+34%)
          </div>
          <p className="text-xs text-white/60 mt-1">
            Confirmed across 3 historical cycles in Rajajinagar & West Division.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="text-xs text-white/50 uppercase tracking-wider mb-1">
            Spatial Anomaly Score
          </div>
          <div className="text-lg font-semibold text-emerald-400">
            Getis-Ord Gi* z = +3.48
          </div>
          <p className="text-xs text-white/60 mt-1">
            Statistically significant hotspot cluster (&gt;99.9% confidence interval).
          </p>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="text-xs text-white/50 uppercase tracking-wider mb-1">
            Prediction Interval
          </div>
          <div className="text-lg font-semibold text-purple-400">
            8 – 11 Incidents / Shift
          </div>
          <p className="text-xs text-white/60 mt-1">
            Conformal prediction band calibrated on empirical quantile regression.
          </p>
        </div>
      </div>

      <div className="p-5 rounded-xl border border-white/10 bg-black/40">
        <h4 className="text-xs font-semibold text-white/80 uppercase tracking-wider mb-4">
          Multi-Signal Correlation & Behavioral Drivers
        </h4>
        <div className="space-y-3">
          {[
            { label: "Festival Uplift Indicator (Dasara Calendar)", score: "94.2%", color: "bg-cyan-400" },
            { label: "Repeat Offender Co-Occurrence (Habitual Ledger)", score: "88.7%", color: "bg-emerald-400" },
            { label: "Exit Corridor Accessibility (Mysore Road Arterial)", score: "81.5%", color: "bg-purple-400" },
            { label: "Patrol Absence Anomaly (Dark Zone Silence)", score: "76.0%", color: "bg-amber-400" }
          ].map((bar, i) => (
            <div key={i} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-white/70">{bar.label}</span>
                <span className="font-mono text-white/90">{bar.score}</span>
              </div>
              <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
                <div
                  className={`h-full ${bar.color}`}
                  style={{ width: bar.score }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function VictimMLContent() {
  return (
    <div className="space-y-6">
      <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-start gap-3">
        <Sparkles className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
        <div>
          <h4 className="text-sm font-semibold text-purple-300">
            Privacy-Preserving Vector Linkage
          </h4>
          <p className="text-xs text-purple-200/70 mt-1">
            Matches missing person descriptors and FIR physical feature hashes without exposing unencrypted civilian PII.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          {
            matchId: "VIC-MATCH-8841",
            confidence: "96.4%",
            source: "Anonymized CCTNS Missing Record #KA-2024-881",
            features: "Height: 165cm · Tattoo: Right Wrist Symbol · Age Band: 28-32",
            status: "High Probability Match"
          },
          {
            matchId: "VIC-MATCH-3109",
            confidence: "82.1%",
            source: "Hospital ER Trauma Register (Anonymized Intake #992)",
            features: "Incident Proximity: 1.4 km · Time Delta: +22 mins",
            status: "Secondary Correlation"
          }
        ].map((v, i) => (
          <div
            key={i}
            className="p-4 rounded-xl border border-white/10 bg-white/[0.03] space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs text-purple-400 font-semibold">
                {v.matchId}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30">
                {v.confidence} Confidence
              </span>
            </div>
            <p className="text-xs font-medium text-white">{v.source}</p>
            <p className="text-xs text-white/60 font-mono">{v.features}</p>
            <div className="pt-2 border-t border-white/10 flex justify-between items-center">
              <span className="text-[11px] text-emerald-400">{v.status}</span>
              <button className="px-2.5 py-1 rounded text-xs bg-purple-500/20 hover:bg-purple-500/30 text-purple-200 transition-colors">
                Link Dossier
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AgenticArchitectureContent() {
  const tiers = [
    {
      title: "1. Linear Workflow (Deterministic Core)",
      desc: "Strict bilingual ZCQL database execution, zero-fabrication assertion check, and SHA-256 derivation chain logging.",
      badge: "Numbers checked against rows",
      color: "border-cyan-500/40 bg-cyan-500/10 text-cyan-300"
    },
    {
      title: "2. Autonomous Intelligence (Graph Discovery)",
      desc: "Breadth-first K/D/I/U graph hop traversal, UNSUB anchor discovery, and hypothesis scoring across entity edges.",
      badge: "BFS Discovery",
      color: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
    },
    {
      title: "3. Role-Based System (Police Specializations)",
      desc: "Dedicated roles: corridor_analyst (escape routes), briefing_compiler (shift handovers), vigil_guard (boundary guard).",
      badge: "Domain Expert",
      color: "border-purple-500/40 bg-purple-500/10 text-purple-300"
    },
    {
      title: "4. Product Orchestrator (KUL Layer)",
      desc: "Compiles verified products into cacheable 24h JSON artifacts and routes calls between GLM-4.7-Flash & Qwen 3.6.",
      badge: "High Concurrency",
      color: "border-amber-500/40 bg-amber-500/10 text-amber-300"
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {tiers.map((t, i) => (
        <div
          key={i}
          className="p-5 rounded-xl border border-white/10 bg-white/[0.03] flex flex-col justify-between space-y-3"
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-white">{t.title}</h4>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-medium border ${t.color}`}
              >
                {t.badge}
              </span>
            </div>
            <p className="text-xs text-white/70 leading-relaxed">{t.desc}</p>
          </div>
          <div className="pt-2 border-t border-white/10 flex items-center justify-between text-[11px] text-white/50">
            <span>Architecture layer</span>
            <span className="text-emerald-400">Live in backend</span>
          </div>
        </div>
      ))}
    </div>
  );
}
