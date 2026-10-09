"use client";

import { useState, useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { HelpCircle, X } from "lucide-react";
import { useLang } from "@/components/Providers";

// ─────────────────────────────────────────────────────────────────────────────
// Page guides. Every guide has the same shape so every screen reads the same way:
//   title · lead (one sentence: what this screen is for)
//   blocks: [{ h, items: [[term, explanation], …], warn? }]
//   examples (queries to type)  ·  tip (one sentence)  ·  note (a caveat)
// Every text is [English, Kannada].
// ─────────────────────────────────────────────────────────────────────────────
const L = (en, kn) => ({ en, kn });

const GUIDES = {
  chat: {
    title: L("Chat Guide", "ಚಾಟ್ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Interact with the FIR database using natural language in English or Kannada. Ask questions, request summaries, or trigger expert agents.",
            "ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಕನ್ನಡದಲ್ಲಿ ನೈಸರ್ಗಿಕ ಭಾಷೆಯನ್ನು ಬಳಸಿಕೊಂಡು FIR ಡೇಟಾಬೇಸ್‌ನೊಂದಿಗೆ ಸಂವಹನ ನಡೆಸಿ. ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ, ಸಾರಾಂಶಗಳನ್ನು ವಿನಂತಿಸಿ ಅಥವಾ ತಜ್ಞ ಏಜೆಂಟ್‌ಗಳನ್ನು ಬಳಸಿ."),
    blocks: [
      { h: L("Reading Responses", "ಪ್ರತ್ಯುತ್ತರಗಳನ್ನು ಅರ್ಥೈಸಿಕೊಳ್ಳುವುದು"), items: [
        [L("The Bottom Line First", "ಮೊದಲಿಗೆ ನೇರ ಉತ್ತರ"), L("Antar provides the direct answer immediately, followed by the supporting evidence and reasoning.", "ಅಂತರ ತಕ್ಷಣವೇ ನೇರ ಉತ್ತರವನ್ನು ನೀಡುತ್ತದೆ, ಅದರ ನಂತರ ಪೂರಕ ಸಾಕ್ಷ್ಯ ಮತ್ತು ತಾರ್ಕಿಕ ವಿವರಣೆಯನ್ನು ನೀಡುತ್ತದೆ.")],
        [L("Source Citations", "ಮೂಲ ಉಲ್ಲೇಖಗಳು"), L("Every factual claim is backed by specific FIR record numbers. Click them to view the original case file.", "ಪ್ರತಿಯೊಂದು ವಾಸ್ತವಿಕ ಹೇಳಿಕೆಯು ನಿರ್ದಿಷ್ಟ FIR ದಾಖಲೆ ಸಂಖ್ಯೆಗಳಿಂದ ಬೆಂಬಲಿತವಾಗಿದೆ. ಮೂಲ ಪ್ರಕರಣದ ಫೈಲ್ ಅನ್ನು ವೀಕ್ಷಿಸಲು ಅವುಗಳ ಮೇಲೆ ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("Evidence Badges (K-D-I)", "ಸಾಕ್ಷ್ಯ ಬ್ಯಾಡ್ಜ್‌ಗಳು (K-D-I)"), L("Answers are strictly tagged: K (Known fact from FIR), D (Derived calculation), or I (Inferred/Prediction).", "ಉತ್ತರಗಳನ್ನು ಕಟ್ಟುನಿಟ್ಟಾಗಿ ಟ್ಯಾಗ್ ಮಾಡಲಾಗಿದೆ: K (FIR ನಿಂದ ತಿಳಿದಿರುವ ವಾಸ್ತವ), D (ಪಡೆದ ಲೆಕ್ಕಾಚಾರ), ಅಥವಾ I (ಊಹಿಸಲಾದ/ಮುನ್ಸೂಚನೆ).")],
      ] },
      { h: L("Core Agent Commands", "ಮುಖ್ಯ ಏಜೆಂಟ್ ಆಜ್ಞೆಗಳು"), items: [
        [L("/query", "/query"), L("Forces a strict structural search of the database (e.g. '/query how many thefts in Koramangala').", "ಡೇಟಾಬೇಸ್‌ನ ಕಟ್ಟುನಿಟ್ಟಾದ ರಚನಾತ್ಮಕ ಹುಡುಕಾಟವನ್ನು ಒತ್ತಾಯಿಸುತ್ತದೆ (ಉದಾ. '/query ಕೋರಮಂಗಲದಲ್ಲಿ ಎಷ್ಟು ಕಳ್ಳತನಗಳಿವೆ').")],
        [L("/connect", "/connect"), L("Invokes the Linkage agent to build suspect networks and uncover hidden syndicates across cases.", "ಶಂಕಿತ ನೆಟ್‌ವರ್ಕ್‌ಗಳನ್ನು ನಿರ್ಮಿಸಲು ಮತ್ತು ಪ್ರಕರಣಗಳಾದ್ಯಂತ ಗುಪ್ತ ಸಿಂಡಿಕೇಟ್‌ಗಳನ್ನು ಬಹಿರಂಗಪಡಿಸಲು ಲಿಂಕೇಜ್ ಏಜೆಂಟ್ ಅನ್ನು ಕರೆಯುತ್ತದೆ.")],
        [L("/anticipate", "/anticipate"), L("Triggers the Forecast engine to run risk models on a specific zone or crime type.", "ನಿರ್ದಿಷ್ಟ ವಲಯ ಅಥವಾ ಅಪರಾಧದ ಪ್ರಕಾರದಲ್ಲಿ ಅಪಾಯದ ಮಾದರಿಗಳನ್ನು ಚಲಾಯಿಸಲು ಮುನ್ಸೂಚನೆ ಎಂಜಿನ್ ಅನ್ನು ಪ್ರಚೋದಿಸುತ್ತದೆ.")],
        [L("/osint", "/osint"), L("Scans open web sources for external intelligence (always explicitly flagged as UNVERIFIED).", "ಬಾಹ್ಯ ಗುಪ್ತಚರಕ್ಕಾಗಿ ಮುಕ್ತ ವೆಬ್ ಮೂಲಗಳನ್ನು ಸ್ಕ್ಯಾನ್ ಮಾಡುತ್ತದೆ (ಯಾವಾಗಲೂ UNVERIFIED ಎಂದು ಸ್ಪಷ್ಟವಾಗಿ ಫ್ಲ್ಯಾಗ್ ಮಾಡಲಾಗುತ್ತದೆ).")],
      ] },
      { h: L("Interaction Controls", "ಸಂವಹನ ನಿಯಂತ್ರಣಗಳು"), items: [
        [L("Voice Input (Mic)", "ಧ್ವನಿ ಇನ್‌ಪುಟ್ (ಮೈಕ್)"), L("Speak your query directly. The system automatically transcribes English and Kannada.", "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ನೇರವಾಗಿ ಮಾತನಾಡಿ. ಸಿಸ್ಟಮ್ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡವನ್ನು ಲಿಪ್ಯಂತರ ಮಾಡುತ್ತದೆ.")],
        [L("Audio Playback", "ಆಡಿಯೋ ಪ್ಲೇಬ್ಯಾಕ್"), L("Click the listen icon to have Antar read the intelligence brief aloud.", "ಅಂತರ ಇಂಟೆಲಿಜೆನ್ಸ್ ಬ್ರೀಫ್ ಅನ್ನು ಗಟ್ಟಿಯಾಗಿ ಓದುವುದನ್ನು ಕೇಳಲು ಆಲಿಸಿ ಐಕಾನ್ ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("Export to PDF", "PDF ಗೆ ರಫ್ತು ಮಾಡಿ"), L("Download the entire session as a tamper-evident, audit-ready PDF report for case files.", "ಪ್ರಕರಣದ ಫೈಲ್‌ಗಳಿಗಾಗಿ ಸಂಪೂರ್ಣ ಸೆಶನ್ ಅನ್ನು ಟ್ಯಾಂಪರ್-ಎವಿಡೆಂಟ್, ಆಡಿಟ್-ರೆಡಿ PDF ವರದಿಯಾಗಿ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ.")],
      ] },
      { h: L("Trust & Verification", "ನಂಬಿಕೆ ಮತ್ತು ಪರಿಶೀಲನೆ"), items: [
        [L("Zero Hallucination Guard", "ಶೂನ್ಯ ಭ್ರಮೆ ಕಾವಲು"), L("If no relevant FIR exists, Antar will explicitly state 'Nothing found' rather than guessing.", "ಯಾವುದೇ ಸಂಬಂಧಿತ FIR ಇಲ್ಲದಿದ್ದರೆ, ಊಹಿಸುವ ಬದಲು ಅಂತರ ಸ್ಪಷ್ಟವಾಗಿ 'ಏನೂ ಕಂಡುಬಂದಿಲ್ಲ' ಎಂದು ಹೇಳುತ್ತದೆ.")],
        [L("Reasoning Trace", "ತಾರ್ಕಿಕ ಜಾಡು"), L("Click the 'Thought for X seconds' pill to audit the exact steps the AI took to gather your answer.", "ನಿಮ್ಮ ಉತ್ತರವನ್ನು ಸಂಗ್ರಹಿಸಲು AI ತೆಗೆದುಕೊಂಡ ನಿಖರವಾದ ಹಂತಗಳನ್ನು ಆಡಿಟ್ ಮಾಡಲು 'X ಸೆಕೆಂಡುಗಳ ಕಾಲ ಯೋಚಿಸಿದೆ' ಪಿಲ್ ಅನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
      ] },
    ],
    examples: {
      en: ["how many vehicle thefts in Bengaluru City?", "show me the suspect network for FIR 2023-BLR-04412", "what is the forecast for chain snatching next week?"],
      kn: ["ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ವಾಹನ ಕಳ್ಳತನಗಳಾಗಿವೆ?", "FIR 2023-BLR-04412 ಗಾಗಿ ಶಂಕಿತ ನೆಟ್‌ವರ್ಕ್ ಅನ್ನು ನನಗೆ ತೋರಿಸಿ", "ಮುಂದಿನ ವಾರ ಚೈನ್ ಸ್ನ್ಯಾಚಿಂಗ್‌ನ ಮುನ್ಸೂಚನೆ ಏನು?"]
    }
  },

  predict: {
    title: L("Predict Guide", "ಮುನ್ಸೂಚನೆ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("I actively analyze historical FIRs across all zones to estimate crime risk for the next 7 days. Every forecast I generate is fully explainable.",
            "ಮುಂಬರುವ 7 ದಿನಗಳ ಅಪರಾಧ ಅಪಾಯವನ್ನು ಅಂದಾಜು ಮಾಡಲು ನಾನು ಐತಿಹಾಸಿಕ FIR ಗಳನ್ನು ಸಕ್ರಿಯವಾಗಿ ವಿಶ್ಲೇಷಿಸುತ್ತೇನೆ. ನನ್ನ ಪ್ರತಿಯೊಂದು ಮುನ್ಸೂಚನೆಯು ಸಂಪೂರ್ಣವಾಗಿ ವಿವರಿಸಬಲ್ಲದು."),
    blocks: [
      { h: L("My Capabilities", "ನನ್ನ ಸಾಮರ್ಥ್ಯಗಳು"), items: [
        [L("Spatiotemporal Clustering", "ನೈಜ-ಸಮಯದ ಸಮೂಹ ವಿಶ್ಲೇಷಣೆ"), L("I utilize ST-DBSCAN algorithms to instantly detect emerging crime clusters before they become trends.", "ಅಪರಾಧ ಸಮೂಹಗಳನ್ನು ಅವು ಟ್ರೆಂಡ್‌ಗಳಾಗುವ ಮುನ್ನವೇ ಪತ್ತೆಹಚ್ಚಲು ನಾನು ST-DBSCAN ಅಲ್ಗಾರಿದಮ್‌ಗಳನ್ನು ಬಳಸುತ್ತೇನೆ.")],
        [L("Anomaly Detection (MAD-z)", "ಅಸಂಗತತೆ ಪತ್ತೆ (MAD-z)"), L("I filter out statistical noise. A Z-score above 2.5 tells me a spike is a true anomaly, not a random fluctuation.", "ನಾನು ಸಾಂಖ್ಯಿಕ ಶಬ್ದವನ್ನು ಫಿಲ್ಟರ್ ಮಾಡುತ್ತೇನೆ. 2.5 ಕ್ಕಿಂತ ಹೆಚ್ಚಿನ Z-ಸ್ಕೋರ್ ನನಗೆ ಸ್ಪೈಕ್ ನಿಜವಾದ ಅಸಂಗತತೆ ಎಂದು ಹೇಳುತ್ತದೆ.")],
        [L("Split-Conformal Forecasting", "ಸ್ಪ್ಲಿಟ್-ಕಾನ್ಫಾರ್ಮಲ್ ಮುನ್ಸೂಚನೆ"), L("I do not just guess; I provide exact expected incident ranges (e.g., 6-9 cases) with 80% to 90% mathematical confidence.", "ನಾನು ಕೇವಲ ಊಹಿಸುವುದಿಲ್ಲ; 80% ರಿಂದ 90% ಗಣಿತದ ವಿಶ್ವಾಸದೊಂದಿಗೆ ನಿಖರವಾದ ನಿರೀಕ್ಷಿತ ಘಟನೆಗಳ ಶ್ರೇಣಿಯನ್ನು ನಾನು ಒದಗಿಸುತ್ತೇನೆ.")],
      ] },
      { h: L("What I Display", "ನಾನು ಪ್ರದರ್ಶಿಸುವುದು"), items: [
        [L("Forecast Board", "ಮುನ್ಸೂಚನೆ ಬೋರ್ಡ್"), L("My live recalculation of risk by zone and crime type, updating the moment a new FIR enters the registry.", "ಹೊಸ FIR ದಾಖಲಾದ ಕ್ಷಣವೇ ನವೀಕರಿಸುವ ಮೂಲಕ, ವಲಯ ಮತ್ತು ಅಪರಾಧದ ಪ್ರಕಾರದ ಮೂಲಕ ನನ್ನ ಲೈವ್ ಅಪಾಯದ ಮರು ಲೆಕ್ಕಾಚಾರ.")],
        [L("Silence Drops", "ಮೌನ ಕುಸಿತಗಳು"), L("If reports suddenly stop, I flag this as a 'silence drop', which often indicates under-reporting rather than increased safety.", "ವರದಿಗಳು ಇದ್ದಕ್ಕಿದ್ದಂತೆ ನಿಂತರೆ, ನಾನು ಇದನ್ನು 'ಮೌನ ಕುಸಿತ' ಎಂದು ಗುರುತಿಸುತ್ತೇನೆ, ಇದು ಹೆಚ್ಚಾಗಿ ಕಡಿಮೆಯಾದ ವರದಿಯನ್ನು ಸೂಚಿಸುತ್ತದೆ.")],
        [L("Agent Reasoning Trace", "ಏಜೆಂಟ್ ತಾರ್ಕಿಕ ಜಾಡು"), L("When you click a forecast, I show you exactly which signals, seasonal drivers, and historical patterns shaped my conclusion.", "ನೀವು ಮುನ್ಸೂಚನೆಯನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿದಾಗ, ಯಾವ ಸಂಕೇತಗಳು ಮತ್ತು ಐತಿಹಾಸಿಕ ಮಾದರಿಗಳು ನನ್ನ ತೀರ್ಮಾನವನ್ನು ರೂಪಿಸಿದವು ಎಂಬುದನ್ನು ನಾನು ನಿಖರವಾಗಿ ತೋರಿಸುತ್ತೇನೆ.")],
      ] },
    ],
    note: L("My forecasts are designed to optimize tactical patrol deployments. They are analytical assessments, not legal evidence.", "ನನ್ನ ಮುನ್ಸೂಚನೆಗಳನ್ನು ಯುದ್ಧತಂತ್ರದ ಗಸ್ತು ನಿಯೋಜನೆಗಳನ್ನು ಅತ್ಯುತ್ತಮವಾಗಿಸಲು ವಿನ್ಯಾಸಗೊಳಿಸಲಾಗಿದೆ. ಅವು ವಿಶ್ಲೇಷಣಾತ್ಮಕ ಮೌಲ್ಯಮಾಪನಗಳೇ ಹೊರತು ಕಾನೂನು ಪುರಾವೆಗಳಲ್ಲ."),
  },

  brain: {
    title: L("Brain Guide", "ಬ್ರೈನ್ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("A 3D view of crime events and the links Antar found between them: shared evidence, vehicles and accused.",
            "ಅಪರಾಧ ಘಟನೆಗಳು ಮತ್ತು ಅವುಗಳ ನಡುವೆ ಅಂತರ ಕಂಡುಹಿಡಿದ ಸಂಪರ್ಕಗಳ (ಸಾಕ್ಷ್ಯ, ವಾಹನ, ಆರೋಪಿ) 3D ನೋಟ."),
    blocks: [
      { h: L("Move around", "ಸಂಚರಿಸಿ"), items: [
        [L("Rotate", "ತಿರುಗಿಸಿ"), L("Drag with the mouse or one finger.", "ಮೌಸ್ ಅಥವಾ ಒಂದು ಬೆರಳಿನಿಂದ ಎಳೆಯಿರಿ.")],
        [L("Zoom", "ಝೂಮ್"), L("Scroll, or pinch on a touch screen.", "ಸ್ಕ್ರಾಲ್ ಮಾಡಿ, ಅಥವಾ ಟಚ್ ಪರದೆಯಲ್ಲಿ ಪಿಂಚ್ ಮಾಡಿ.")],
        [L("Focus", "ಕೇಂದ್ರೀಕರಿಸಿ"), L("Click a node to see its evidence trail and AI insight.", "ನೋಡ್ ಕ್ಲಿಕ್ ಮಾಡಿ ಅದರ ಸಾಕ್ಷ್ಯ ಹಾದಿ ಮತ್ತು AI ಒಳನೋಟ ನೋಡಿ.")],
      ] },
      { h: L("Narrow it down", "ಸೀಮಿತಗೊಳಿಸಿ"), items: [
        [L("Layers & Filters", "ಲೇಯರ್ ಮತ್ತು ಫಿಲ್ಟರ್"), L("Show only selected crime types or evidence.", "ಆಯ್ದ ಅಪರಾಧ ಪ್ರಕಾರ ಅಥವಾ ಸಾಕ್ಷ್ಯ ಮಾತ್ರ ತೋರಿಸಿ.")],
        [L("Case activity", "ಪ್ರಕರಣ ಚಟುವಟಿಕೆ"), L("Pick dates on the calendar (bottom left) to filter the graph.", "ಗ್ರಾಫ್ ಫಿಲ್ಟರ್ ಮಾಡಲು ಕೆಳ ಎಡದ ಕ್ಯಾಲೆಂಡರ್‌ನಲ್ಲಿ ದಿನಾಂಕ ಆರಿಸಿ.")],
        [L("Data overview", "ದತ್ತಾಂಶ ಅವಲೋಕನ"), L("Open the overview (bottom right) for statistics on what is shown.", "ತೋರಿಸಿದ ದಾಖಲೆಗಳ ಅಂಕಿಅಂಶಗಳಿಗೆ ಕೆಳ ಬಲದ ಅವಲೋಕನ ತೆರೆಯಿರಿ.")],
      ] },
    ],
  },

  map: {
    title: L("Map Guide", "ನಕ್ಷೆ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Karnataka by district: where crime concentrates, and which hotspots are statistically real.",
            "ಜಿಲ್ಲಾವಾರು ಕರ್ನಾಟಕ: ಅಪರಾಧ ಎಲ್ಲಿ ಕೇಂದ್ರೀಕೃತವಾಗಿದೆ ಮತ್ತು ಯಾವ ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳು ಸಂಖ್ಯಾಶಾಸ್ತ್ರೀಯವಾಗಿ ನಿಜವಾದವು."),
    blocks: [
      { h: L("Use the map", "ನಕ್ಷೆ ಬಳಸಿ"), items: [
        [L("Select a district", "ಜಿಲ್ಲೆ ಆರಿಸಿ"), L("Click a district to focus the side panel on it.", "ಬದಿಯ ಪ್ಯಾನೆಲ್ ಅನ್ನು ಆ ಜಿಲ್ಲೆಗೆ ಸೀಮಿತಗೊಳಿಸಲು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("Shading", "ಬಣ್ಣ"), L("A stronger colour means more FIRs in that district.", "ಗಾಢ ಬಣ್ಣ ಎಂದರೆ ಆ ಜಿಲ್ಲೆಯಲ್ಲಿ ಹೆಚ್ಚು FIR.")],
      ] },
      { h: L("Read the hotspots", "ಹಾಟ್‌ಸ್ಪಾಟ್ ಓದಿ"), items: [
        [L("Red zones", "ಕೆಂಪು ವಲಯ"), L("Dense clusters that need attention now.", "ತಕ್ಷಣ ಗಮನ ಬೇಕಾದ ದಟ್ಟ ಕ್ಲಸ್ಟರ್‌ಗಳು.")],
        [L("Cyan zones", "ನೀಲಿ ವಲಯ"), L("Emerging or scattered patterns to watch.", "ಗಮನಿಸಬೇಕಾದ ಉದಯಿಸುತ್ತಿರುವ ಅಥವಾ ಚದುರಿದ ಮಾದರಿಗಳು.")],
        [L("Gi* z-score", "Gi* z-ಸ್ಕೋರ್"), L("Above 1.96 means the cluster is real (95% confidence), not chance.", "1.96 ಕ್ಕಿಂತ ಹೆಚ್ಚು ಎಂದರೆ ಕ್ಲಸ್ಟರ್ ನಿಜವಾದದ್ದು (95% ವಿಶ್ವಾಸ), ಆಕಸ್ಮಿಕವಲ್ಲ.")],
      ] },
    ],
    tip: L("Click Bengaluru City, then a neighbouring district, and compare.", "Bengaluru City ಕ್ಲಿಕ್ ಮಾಡಿ, ನಂತರ ಪಕ್ಕದ ಜಿಲ್ಲೆಯೊಂದಿಗೆ ಹೋಲಿಸಿ."),
  },

  search: {
    title: L("Search Guide", "ಹುಡುಕಾಟ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Find a person, alias, phone number or vehicle across 10,00,000+ FIRs, even with spelling mistakes.",
            "ಹೆಸರು, ಉಪನಾಮ, ಫೋನ್ ಸಂಖ್ಯೆ ಅಥವಾ ವಾಹನವನ್ನು 4.25 ಲಕ್ಷಕ್ಕೂ ಹೆಚ್ಚು FIR ಗಳಲ್ಲಿ ಹುಡುಕಿ. ಕಾಗುಣಿತ ತಪ್ಪಿದ್ದರೂ ಸಿಗುತ್ತದೆ."),
    blocks: [
      { h: L("How matching works", "ಹೊಂದಾಣಿಕೆ ಹೇಗೆ"), items: [
        [L("Fuzzy match", "ಸಮೀಪ ಹೊಂದಾಣಿಕೆ"), L("Similar spellings still match.", "ಹೋಲುವ ಕಾಗುಣಿತವೂ ಹೊಂದುತ್ತದೆ.")],
        [L("Sound-alike", "ಉಚ್ಚಾರ ಹೊಂದಾಣಿಕೆ"), L("Names that sound the same match too (Soundex).", "ಒಂದೇ ರೀತಿ ಉಚ್ಚರಿಸುವ ಹೆಸರುಗಳೂ ಹೊಂದುತ್ತವೆ (Soundex).")],
        [L("Aliases", "ಉಪನಾಮಗಳು"), L("Known aliases lead to the same person.", "ತಿಳಿದಿರುವ ಉಪನಾಮಗಳು ಅದೇ ವ್ಯಕ್ತಿಗೆ ಕರೆದೊಯ್ಯುತ್ತವೆ.")],
      ] },
      { h: L("Reading results", "ಫಲಿತಾಂಶ ಓದಿ"), items: [
        [L("Risk index", "ಅಪಾಯ ಸೂಚ್ಯಂಕ"), L("Above 70 is high risk, based on how often and how seriously someone appears in cases.", "70 ಕ್ಕಿಂತ ಹೆಚ್ಚು ಎಂದರೆ ಹೆಚ್ಚಿನ ಅಪಾಯ. ಪ್ರಕರಣಗಳಲ್ಲಿ ಎಷ್ಟು ಬಾರಿ, ಎಷ್ಟು ಗಂಭೀರವಾಗಿ ಕಾಣಿಸಿಕೊಂಡಿದ್ದಾರೆ ಎಂಬುದರ ಆಧಾರ.")],
        [L("OSINT (preview)", "OSINT (ಪೂರ್ವನೋಟ)"), L("Open-web signals for admins. Unverified: always confirm manually.", "ನಿರ್ವಾಹಕರಿಗೆ ಮುಕ್ತ-ವೆಬ್ ಸಂಕೇತಗಳು. ಪರಿಶೀಲಿಸಿಲ್ಲ: ಯಾವಾಗಲೂ ಕೈಯಾರೆ ದೃಢೀಕರಿಸಿ.")],
      ] },
    ],
    examples: { en: ["Yelappa"], kn: ["Yelappa"] },
  },

  trace: {
    title: L("Trace & Telemetry Guide", "ಟ್ರೇಸ್ ಮತ್ತು ಟೆಲಿಮೆಟ್ರಿ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Every question asked in a session, and exactly how each answer was produced.",
            "ಸೆಷನ್‌ನಲ್ಲಿ ಕೇಳಿದ ಪ್ರತಿ ಪ್ರಶ್ನೆ, ಮತ್ತು ಪ್ರತಿ ಉತ್ತರ ನಿಖರವಾಗಿ ಹೇಗೆ ತಯಾರಾಯಿತು."),
    blocks: [
      { h: L("For each question", "ಪ್ರತಿ ಪ್ರಶ್ನೆಗೆ"), items: [
        [L("Route", "ಮಾರ್ಗ"), L("Which query template and agents handled it.", "ಯಾವ ಪ್ರಶ್ನೆ ಟೆಂಪ್ಲೇಟ್ ಮತ್ತು ಏಜೆಂಟ್‌ಗಳು ನಿರ್ವಹಿಸಿದವು.")],
        [L("Evidence", "ಸಾಕ್ಷ್ಯ"), L("How many records came back.", "ಎಷ್ಟು ದಾಖಲೆಗಳು ಬಂದವು.")],
        [L("Timing", "ಸಮಯ"), L("Latency of every step and of any model calls.", "ಪ್ರತಿ ಹಂತದ ಮತ್ತು ಮಾದರಿ ಕರೆಗಳ ಸಮಯ.")],
      ] },
      { h: L("Why it matters", "ಏಕೆ ಮುಖ್ಯ"), items: [
        [L("Quality", "ಗುಣಮಟ್ಟ"), L("Answers are scored for faithfulness, relevance and guardrail adherence.", "ಉತ್ತರಗಳಿಗೆ ನಿಷ್ಠೆ, ಪ್ರಸ್ತುತತೆ ಮತ್ತು ನಿಯಮ ಪಾಲನೆಯ ಅಂಕ ನೀಡಲಾಗುತ್ತದೆ.")],
        [L("Accountability", "ಹೊಣೆಗಾರಿಕೆ"), L("Audit exactly why an answer or a flag appeared.", "ಉತ್ತರ ಅಥವಾ ಎಚ್ಚರಿಕೆ ಏಕೆ ಬಂತು ಎಂದು ನಿಖರವಾಗಿ ಪರಿಶೀಲಿಸಿ.")],
      ] },
    ],
  },

  network: {
    title: L("Network Guide", "ಜಾಲ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Starting from one suspect, the graph shows every recorded link up to two steps away (up to 150 people).",
            "ಒಬ್ಬ ಶಂಕಿತನಿಂದ ಆರಂಭಿಸಿ, ಎರಡು ಹಂತದವರೆಗಿನ (150 ಜನರವರೆಗೆ) ದಾಖಲಾದ ಎಲ್ಲಾ ಸಂಪರ್ಕಗಳನ್ನು ಗ್ರಾಫ್ ತೋರಿಸುತ್ತದೆ."),
    blocks: [
      { h: L("Who matters", "ಯಾರು ಮುಖ್ಯ"), items: [
        [L("Influence", "ಪ್ರಭಾವ"), L("PageRank: the bigger the node, the more central the person.", "PageRank: ದೊಡ್ಡ ನೋಡ್ ಎಂದರೆ ಹೆಚ್ಚು ಕೇಂದ್ರೀಯ ವ್ಯಕ್ತಿ.")],
        [L("Broker", "ಮಧ್ಯವರ್ತಿ"), L("Betweenness: the person whose removal splits the network.", "Betweenness: ತೆಗೆದರೆ ಜಾಲವನ್ನು ವಿಭಜಿಸುವ ವ್ಯಕ್ತಿ.")],
        [L("Inner circle", "ಒಳ ವಲಯ"), L("k-core: the tightly connected core of the group.", "k-core: ಗುಂಪಿನ ಗಾಢವಾಗಿ ಜೋಡಿಸಿದ ಕೇಂದ್ರ.")],
      ] },
      { h: L("Lines", "ರೇಖೆಗಳು"), items: [
        [L("Solid", "ಘನ ರೇಖೆ"), L("A recorded relationship.", "ದಾಖಲಾದ ಸಂಬಂಧ.")],
        [L("Dashed", "ಚುಕ್ಕೆ ರೇಖೆ"), L("A predicted link (Adamic-Adar): a lead to verify, tagged INFERRED.", "ಊಹಿಸಿದ ಸಂಪರ್ಕ (Adamic-Adar): ಪರಿಶೀಲಿಸಬೇಕಾದ ಸುಳಿವು, INFERRED ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ.")],
      ] },
    ],
  },

  trends: {
    title: L("Trends Guide", "ಪ್ರವೃತ್ತಿ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Monthly FIR counts straight from the registry. Filter by crime type and district.",
            "ನೋಂದಣಿಯಿಂದ ನೇರವಾಗಿ ಮಾಸಿಕ FIR ಸಂಖ್ಯೆಗಳು. ಅಪರಾಧ ಪ್ರಕಾರ ಮತ್ತು ಜಿಲ್ಲೆಯಿಂದ ಫಿಲ್ಟರ್ ಮಾಡಿ."),
    blocks: [
      { h: L("Reading the chart", "ಚಾರ್ಟ್ ಓದಿ"), items: [
        [L("Latest month", "ಇತ್ತೀಚಿನ ತಿಂಗಳು"), L("Usually incomplete. A dip at the right edge is late registration, not less crime.", "ಸಾಮಾನ್ಯವಾಗಿ ಅಪೂರ್ಣ. ಬಲ ತುದಿಯ ಇಳಿಕೆ ತಡವಾದ ನೋಂದಣಿ, ಅಪರಾಧ ಕಡಿಮೆಯಾಗಿದೆ ಎಂದಲ್ಲ.")],
        [L("Trend vs anomaly", "ಪ್ರವೃತ್ತಿ ಮತ್ತು ಅಸಂಗತಿ"), L("A rising line is context. To test whether a rise is unusual, open Predict.", "ಏರುವ ರೇಖೆ ಸಂದರ್ಭ ಮಾತ್ರ. ಏರಿಕೆ ಅಸಾಮಾನ್ಯವೇ ಎಂದು ತಿಳಿಯಲು Predict ತೆರೆಯಿರಿ.")],
      ] },
    ],
  },

  profiles: {
    title: L("Profile Guide", "ಪ್ರೊಫೈಲ್ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("A suspect's case history and an explainable priority score.", "ಶಂಕಿತನ ಪ್ರಕರಣ ಇತಿಹಾಸ ಮತ್ತು ವಿವರಿಸಬಹುದಾದ ಆದ್ಯತಾ ಅಂಕ."),
    blocks: [
      { h: L("Risk score", "ಅಪಾಯ ಅಂಕ"), items: [
        [L("Formula", "ಸೂತ್ರ"), L("30% recency + 25% frequency + 25% severity + 20% network centrality.", "30% ಇತ್ತೀಚಿನತೆ + 25% ಆವರ್ತನ + 25% ಗಂಭೀರತೆ + 20% ಜಾಲ ಕೇಂದ್ರೀಯತೆ.")],
        [L("The bars", "ಬಾರ್‌ಗಳು"), L("The four bars are the full explanation. There is no hidden model.", "ನಾಲ್ಕು ಬಾರ್‌ಗಳೇ ಸಂಪೂರ್ಣ ವಿವರಣೆ. ಅಡಗಿದ ಮಾದರಿ ಇಲ್ಲ.")],
      ] },
      { h: L("Use with care", "ಎಚ್ಚರಿಕೆಯಿಂದ ಬಳಸಿ"), warn: true, items: [
        [L("Not a prediction", "ಭವಿಷ್ಯವಾಣಿ ಅಲ್ಲ"), L("It ranks investigative priority from past cases. It is not evidence.", "ಹಿಂದಿನ ಪ್ರಕರಣಗಳಿಂದ ತನಿಖಾ ಆದ್ಯತೆಯ ಶ್ರೇಣಿ. ಇದು ಸಾಕ್ಷ್ಯವಲ್ಲ.")],
        [L("Aliases", "ಉಪನಾಮಗಳು"), L("Synthetic names always show with the record ID. Verify against the FIR.", "ಕೃತಕ ಹೆಸರುಗಳು ಯಾವಾಗಲೂ ದಾಖಲೆ ID ಜೊತೆ ಕಾಣುತ್ತವೆ. FIR ನೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ.")],
      ] },
    ],
  },

  social: {
    title: L("Demographics Guide", "ಜನಸಂಖ್ಯಾ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Aggregate victim and offender demographics for resource planning and prevention programmes.",
            "ಸಂಪನ್ಮೂಲ ಯೋಜನೆ ಮತ್ತು ತಡೆಗಟ್ಟುವ ಕಾರ್ಯಕ್ರಮಗಳಿಗಾಗಿ ಸಂತ್ರಸ್ತರು ಮತ್ತು ಅಪರಾಧಿಗಳ ಒಟ್ಟು ಜನಸಂಖ್ಯಾ ಮಾಹಿತಿ."),
    blocks: [
      { h: L("Hard limit", "ಕಟ್ಟುನಿಟ್ಟಾದ ಮಿತಿ"), warn: true, items: [
        [L("Population level only", "ಒಟ್ಟು ಮಟ್ಟ ಮಾತ್ರ"), L("Never a basis to target, stop or suspect any person or community.", "ಯಾವುದೇ ವ್ಯಕ್ತಿ ಅಥವಾ ಸಮುದಾಯವನ್ನು ಗುರಿಯಾಗಿಸಲು, ತಡೆಯಲು ಅಥವಾ ಶಂಕಿಸಲು ಎಂದಿಗೂ ಆಧಾರವಲ್ಲ.")],
        [L("Monitored", "ನಿಗಾವಹಿಸಲಾಗಿದೆ"), L("The Vigil compliance agent flags any query that uses demographics as a suspect filter.", "ಜನಸಂಖ್ಯಾ ಗುಣಗಳನ್ನು ಶಂಕಿತ ಫಿಲ್ಟರ್ ಆಗಿ ಬಳಸುವ ಯಾವುದೇ ಪ್ರಶ್ನೆಯನ್ನು Vigil ಏಜೆಂಟ್ ಗುರುತಿಸುತ್ತದೆ.")],
      ] },
    ],
  },

  general: {
    title: L("Antar Guide", "ಅಂತರ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Use the top menu to move between modules.", "ಮಾಡ್ಯೂಲ್‌ಗಳ ನಡುವೆ ಸಾಗಲು ಮೇಲಿನ ಮೆನು ಬಳಸಿ."),
    blocks: [
      { h: L("Modules", "ಮಾಡ್ಯೂಲ್‌ಗಳು"), items: [
        [L("Chat", "ಚಾಟ್"), L("Ask questions in English or Kannada, by text or voice.", "ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಕನ್ನಡದಲ್ಲಿ, ಬರೆದು ಅಥವಾ ಮಾತನಾಡಿ ಪ್ರಶ್ನೆ ಕೇಳಿ.")],
        [L("Brain", "ಬ್ರೈನ್"), L("A 3D view of linked cases.", "ಸಂಪರ್ಕಿತ ಪ್ರಕರಣಗಳ 3D ನೋಟ.")],
        [L("Map", "ನಕ್ಷೆ"), L("District hotspots across Karnataka.", "ಕರ್ನಾಟಕದಾದ್ಯಂತ ಜಿಲ್ಲಾ ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳು.")],
        [L("Predict", "ಮುನ್ಸೂಚನೆ"), L("7-day risk forecasts with explanations.", "ವಿವರಣೆಯೊಂದಿಗೆ 7 ದಿನಗಳ ಅಪಾಯ ಮುನ್ಸೂಚನೆ.")],
        [L("Search", "ಹುಡುಕಾಟ"), L("Find people, aliases, phones and vehicles.", "ವ್ಯಕ್ತಿಗಳು, ಉಪನಾಮಗಳು, ಫೋನ್ ಮತ್ತು ವಾಹನಗಳನ್ನು ಹುಡುಕಿ.")],
      ] },
    ],
  },
};

function pickGuide(path, expertOn) {
  if (!path) return "general";
  if (path.startsWith("/antarBrain")) return "brain";
  if (path.startsWith("/antar")) return expertOn ? "expert" : "chat";
  for (const key of ["predict", "map", "search", "trace", "network", "trends", "profiles", "social"]) {
    if (path.startsWith(`/${key}`)) return key;
  }
  return "general";
}

function GuideBody({ g, kn }) {
  const t = (x) => (x ? (kn ? x.kn : x.en) : "");
  const examples = g.examples ? (kn ? g.examples.kn : g.examples.en) : [];
  return (
    <div className="gd">
      {g.lead && <p className="gd-lead">{t(g.lead)}</p>}
      <div className={`gd-blocks${g.blocks.length > 1 ? " gd-cols" : ""}`}>
        {g.blocks.map((b) => (
          <section key={b.h.en} className={`gd-block${b.warn ? " gd-warn" : ""}`}>
            <h4 className="gd-h">{t(b.h)}</h4>
            <dl className="gd-list">
              {b.items.map(([k, v]) => (
                <div key={k.en} className="gd-item">
                  <dt>{t(k)}</dt>
                  <dd>{t(v)}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>
      {(examples.length > 0 || g.tip) && (
        <section className="gd-try">
          <h4 className="gd-h">{kn ? "ಹೀಗೆ ಪ್ರಯತ್ನಿಸಿ" : "Try this"}</h4>
          {examples.length > 0 && (
            <ul>{examples.map((q) => <li key={q}><code>{q}</code></li>)}</ul>
          )}
          {g.tip && <p>{t(g.tip)}</p>}
        </section>
      )}
      {g.note && <p className="gd-note">{t(g.note)}</p>}
    </div>
  );
}

export default function GlobalGuide() {
  const rawPath = usePathname();
  // next.config.mjs sets trailingSlash:true, so usePathname can hand us "/antarBrain/".
  // Normalise once so prefix checks (and the /antarBrain vs /antar split) stay exact.
  const path = rawPath && rawPath.length > 1 ? rawPath.replace(/\/+$/, "") : rawPath;
  const { lang } = useLang();
  const kn = lang === "kn";
  const [open, setOpen] = useState(false);
  const [expertOn, setExpertOn] = useState(false);
  const dialogRef = useRef(null);
  const closeRef = useRef(null);

  useEffect(() => {
    try { setExpertOn(localStorage.getItem("antar_expert") === "1"); } catch {}
    const onExpert = (e) => setExpertOn(!!e.detail?.on);
    const onOpen = () => setOpen(true);
    window.addEventListener("antar-expert", onExpert);
    window.addEventListener("open-guide", onOpen);
    return () => {
      window.removeEventListener("antar-expert", onExpert);
      window.removeEventListener("open-guide", onOpen);
    };
  }, []);

  // While open: Escape closes, focus moves into the dialog, and the page behind stops
  // scrolling (on phones a scroll inside the sheet used to drag the page underneath).
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const prevFocus = document.activeElement;
    requestAnimationFrame(() => closeRef.current?.focus());
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
      try { prevFocus?.focus?.(); } catch {}
    };
  }, [open]);

  // The guide opens when the officer asks for it - never on its own. It used to pop open
  // on the first visit to /predict, which took the screen from someone who had not
  // clicked anything.

  if (path && (path.startsWith("/account") || path.startsWith("/about") || path.startsWith("/docs"))) return null;

  const g = GUIDES[pickGuide(path, expertOn)];
  const title = kn ? g.title.kn : g.title.en;
  const wide = g.blocks.length > 1;

  return (
    <>
      <button
        id="cx-guide-trigger"
        type="button"
        className={`cx-guide-btn ${open ? "hidden" : ""}`}
        onClick={() => setOpen(true)}
        title={kn ? "ಪುಟ ಮಾರ್ಗದರ್ಶಿ" : "Page Guide"}
        aria-label={kn ? "ಪುಟ ಮಾರ್ಗದರ್ಶಿ ತೆರೆಯಿರಿ" : "Open page guide"}
        style={{
          ...(expertOn && path?.startsWith("/antar") && path !== "/antarBrain" ? { display: "none" } : {}),
          ...(path === "/antarBrain" ? { bottom: "134px" } : {}),
        }}
      >
        <HelpCircle size={22} strokeWidth={1.5} />
      </button>

      {open && (
        <div className="cx-guide-modal-overlay" onClick={() => setOpen(false)}>
          <div
            ref={dialogRef}
            className={`cx-guide-modal cx-enter${wide ? " cx-guide-wide" : ""}${kn ? " cx-guide-kn" : ""}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="cx-guide-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="cx-guide-header">
              <h3 id="cx-guide-title">{title}</h3>
              <button ref={closeRef} type="button" className="cx-guide-close" onClick={() => setOpen(false)}
                      aria-label={kn ? "ಮುಚ್ಚಿ" : "Close guide"}>
                <X size={18} />
              </button>
            </div>
            <div className="cx-guide-content">
              <GuideBody g={g} kn={kn} />
            </div>
            <div className="cx-guide-footer">
              <span className="cx-guide-hint">
                {kn ? <>ಮುಚ್ಚಲು <kbd>Esc</kbd> ಒತ್ತಿ</> : <>Press <kbd>Esc</kbd> to close</>}
              </span>
              <button type="button" className="cx-guide-done" onClick={() => setOpen(false)}>
                {kn ? "ಅರ್ಥವಾಯಿತು" : "Got it"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
