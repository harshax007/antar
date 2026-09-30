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
    lead: L("Ask anything about the FIR records in English or Kannada, by typing or speaking. The answer comes first, then the proof.",
            "FIR ದಾಖಲೆಗಳ ಬಗ್ಗೆ ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಕನ್ನಡದಲ್ಲಿ, ಬರೆದು ಅಥವಾ ಮಾತನಾಡಿ ಏನು ಬೇಕಾದರೂ ಕೇಳಿ. ಮೊದಲು ಉತ್ತರ, ನಂತರ ಸಾಕ್ಷ್ಯ."),
    blocks: [
      { h: L("Reading an answer", "ಉತ್ತರವನ್ನು ಓದುವುದು"), items: [
        [L("Top line", "ಮೊದಲ ಸಾಲು"), L("The direct answer with the key number.", "ಮುಖ್ಯ ಸಂಖ್ಯೆಯೊಂದಿಗೆ ನೇರ ಉತ್ತರ.")],
        [L("Direction", "ಪ್ರವೃತ್ತಿ"), L("UPWARD, DOWNWARD or STABLE against recent months.", "ಇತ್ತೀಚಿನ ತಿಂಗಳುಗಳಿಗೆ ಹೋಲಿಸಿದರೆ ಏರಿಕೆ, ಇಳಿಕೆ ಅಥವಾ ಸ್ಥಿರ.")],
        [L("Evidence badge", "ಸಾಕ್ಷ್ಯ ಬ್ಯಾಡ್ಜ್"), L("One letter - K, D, I or U - for how the answer is known. See below.", "ಉತ್ತರ ಹೇಗೆ ತಿಳಿದಿದೆ ಎಂಬುದಕ್ಕೆ ಒಂದು ಅಕ್ಷರ - K, D, I ಅಥವಾ U. ಕೆಳಗೆ ನೋಡಿ.")],
        [L("Thought for …", "ಯೋಚಿಸಿದ ಸಮಯ"), L("How long it took. Click it to see every step.", "ಉತ್ತರಕ್ಕೆ ತೆಗೆದುಕೊಂಡ ಸಮಯ. ಪ್ರತಿ ಹಂತ ನೋಡಲು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
      ] },
      // The four evidence classes (ICD 203). This is the single most important thing an
      // officer must be able to read off an answer: what is record, and what is judgment.
      { h: L("What the badge means (K · D · I · U)", "ಬ್ಯಾಡ್ಜ್ ಅರ್ಥ (K · D · I · U)"), items: [
        [L("K - Known", "K - ತಿಳಿದಿರುವುದು"), L("Read straight from a record. \"FIR 2023-BLR-04412 was registered on 12 March.\" Check it in Evidence.",
                                                  "ನೇರವಾಗಿ ದಾಖಲೆಯಿಂದ ಓದಿದ್ದು. \"FIR 2023-BLR-04412 ಮಾರ್ಚ್ 12 ರಂದು ದಾಖಲಾಗಿದೆ.\" ಸಾಕ್ಷ್ಯದಲ್ಲಿ ಪರಿಶೀಲಿಸಿ.")],
        [L("D - Derived", "D - ಗಣಿಸಿದ್ದು"), L("Counted or calculated from records - totals, shares, trends. The arithmetic is shown, not guessed.",
                                                  "ದಾಖಲೆಗಳಿಂದ ಎಣಿಸಿದ್ದು ಅಥವಾ ಲೆಕ್ಕ ಹಾಕಿದ್ದು - ಒಟ್ಟು, ಪಾಲು, ಪ್ರವೃತ್ತಿ. ಲೆಕ್ಕಾಚಾರ ತೋರಿಸಲಾಗಿದೆ, ಊಹೆಯಲ್ಲ.")],
        [L("I - Inferred", "I - ಊಹಿಸಿದ್ದು"), L("A judgment with its basis and its confidence - a forecast, a link, a risk. Treat as a lead, not a fact.",
                                                  "ಆಧಾರ ಮತ್ತು ವಿಶ್ವಾಸದೊಂದಿಗೆ ತೀರ್ಮಾನ - ಮುನ್ಸೂಚನೆ, ಕೊಂಡಿ, ಅಪಾಯ. ಸತ್ಯವಲ್ಲ, ಸುಳಿವಾಗಿ ಪರಿಗಣಿಸಿ.")],
        [L("U - Unknown", "U - ಗೊತ್ತಿಲ್ಲ"), L("The record does not say. Antar names the gap instead of filling it.",
                                                  "ದಾಖಲೆಯಲ್ಲಿ ಇಲ್ಲ. ಅಂತರ್ ಅದನ್ನು ತುಂಬದೆ, ಕೊರತೆಯನ್ನು ಹೇಳುತ್ತದೆ.")],
      ] },
      { h: L("What Antar checks before answering", "ಉತ್ತರಿಸುವ ಮೊದಲು ಪರಿಶೀಲನೆ"), items: [
        [L("Every number", "ಪ್ರತಿ ಸಂಖ್ಯೆ"), L("Must exist in the records behind the answer, or the sentence is dropped.", "ಉತ್ತರದ ಹಿಂದಿನ ದಾಖಲೆಗಳಲ್ಲಿ ಇರಬೇಕು, ಇಲ್ಲದಿದ್ದರೆ ವಾಕ್ಯ ತೆಗೆಯಲಾಗುತ್ತದೆ.")],
        [L("Every FIR id", "ಪ್ರತಿ FIR ಸಂಖ್ಯೆ"), L("Must appear in the cited rows - no invented case numbers or names.", "ಉಲ್ಲೇಖಿತ ಸಾಲುಗಳಲ್ಲಿ ಇರಬೇಕು - ಸೃಷ್ಟಿಸಿದ ಪ್ರಕರಣ ಸಂಖ್ಯೆ ಅಥವಾ ಹೆಸರು ಇಲ್ಲ.")],
        [L("Nothing found", "ಏನೂ ಸಿಗದಿದ್ದರೆ"), L("You are told plainly. A related answer is never passed off as the one you asked for.", "ಸ್ಪಷ್ಟವಾಗಿ ತಿಳಿಸಲಾಗುತ್ತದೆ. ಸಂಬಂಧಿತ ಉತ್ತರವನ್ನು ನೀವು ಕೇಳಿದ್ದೆಂದು ತೋರಿಸುವುದಿಲ್ಲ.")],
        [L("Records only", "ದಾಖಲೆಗಳು ಮಾತ್ರ"), L("Text inside a record is evidence, never an instruction Antar will follow.", "ದಾಖಲೆಯೊಳಗಿನ ಪಠ್ಯ ಸಾಕ್ಷ್ಯ, ಅಂತರ್ ಪಾಲಿಸುವ ಸೂಚನೆಯಲ್ಲ.")],
      ] },
      { h: L("Questions offered to you", "ನಿಮಗೆ ನೀಡಲಾದ ಪ್ರಶ್ನೆಗಳು"), items: [
        [L("Next", "ಮುಂದೆ"), L("The single most useful step after this answer.", "ಈ ಉತ್ತರದ ನಂತರದ ಅತ್ಯಂತ ಉಪಯುಕ್ತ ಹೆಜ್ಜೆ.")],
        [L("Related", "ಸಂಬಂಧಿತ"), L("Checked against the database first - each one has data behind it.", "ಮೊದಲು ಡೇಟಾಬೇಸ್‌ನಲ್ಲಿ ಪರಿಶೀಲಿಸಲಾಗಿದೆ - ಪ್ರತಿಯೊಂದಕ್ಕೂ ಮಾಹಿತಿ ಇದೆ.")],
        [L("For your role", "ನಿಮ್ಮ ಪಾತ್ರಕ್ಕೆ"), L("Chosen for the work you do - operations or supervising approval.", "ನೀವು ಮಾಡುವ ಕೆಲಸಕ್ಕೆ ಆಯ್ಕೆ - ಕಾರ್ಯಾಚರಣೆ ಅಥವಾ ಮೇಲ್ವಿಚಾರಣೆ.")],
        [L(" / ", " / "), L("Rating an answer teaches Antar: poor ones go to a review queue, good ones guide what is suggested next.",
                                     "ಉತ್ತರಕ್ಕೆ ರೇಟಿಂಗ್ ನೀಡಿದರೆ ಅಂತರ್ ಕಲಿಯುತ್ತದೆ: ಕಳಪೆ ಉತ್ತರ ಪರಿಶೀಲನೆಗೆ, ಉತ್ತಮವಾದವು ಮುಂದಿನ ಸಲಹೆಗಳಿಗೆ ದಾರಿ.")],
      ] },
      { h: L("Controls", "ನಿಯಂತ್ರಣಗಳು"), items: [
        [L("Mic", "ಮೈಕ್"), L("Speak your question in English or Kannada.", "ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಕನ್ನಡದಲ್ಲಿ ಪ್ರಶ್ನೆಯನ್ನು ಹೇಳಿ.")],
        [L("Listen", "ಆಲಿಸಿ"), L("Hear the answer read aloud.", "ಉತ್ತರವನ್ನು ಗಟ್ಟಿಯಾಗಿ ಕೇಳಿ.")],
        [L("Export", "ರಫ್ತು"), L("Download a sealed, audit-ready PDF of the session.", "ಸೆಷನ್‌ನ ಮುದ್ರೆಯುಳ್ಳ, ಆಡಿಟ್-ಸಿದ್ಧ PDF ಪಡೆಯಿರಿ.")],
        [L("Expert", "ತಜ್ಞ"), L("Watch the reasoning appear step by step.", "ತರ್ಕವನ್ನು ಹಂತ ಹಂತವಾಗಿ ನೋಡಿ.")],
      ] },
      { h: L("Shortcuts", "ಶಾರ್ಟ್‌ಕಟ್‌ಗಳು"), items: [
        [L("/think", "/think"), L("Show the full reasoning trail.", "ಸಂಪೂರ್ಣ ತರ್ಕದ ಹಾದಿ ತೋರಿಸಿ.")],
        [L("/connect", "/connect"), L("Bring in the network and profile agents.", "ಜಾಲ ಮತ್ತು ಪ್ರೊಫೈಲ್ ಏಜೆಂಟ್‌ಗಳನ್ನು ಸೇರಿಸಿ.")],
        [L("/anticipate", "/anticipate"), L("Bring in the forecast and map agents.", "ಮುನ್ಸೂಚನೆ ಮತ್ತು ನಕ್ಷೆ ಏಜೆಂಟ್‌ಗಳನ್ನು ಸೇರಿಸಿ.")],
        [L("why?", "ಯಾಕೆ?"), L("Explain how the last answer was reached.", "ಹಿಂದಿನ ಉತ್ತರ ಹೇಗೆ ಬಂತು ಎಂದು ವಿವರಿಸಿ.")],
      ] },
    ],
    examples: {
      en: ["most crimes?", "how many murders in Bengaluru City?", "which UPI IDs are used in more than one district",
           "cases for accused ACC-KA-500777", "conviction rate by district in 2023", "top beats for theft in Bengaluru City"],
      kn: ["ಅತಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ಎಲ್ಲಿ?", "ಹಲವು ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಬಳಸಿದ UPI ಐಡಿಗಳು", "ಜಿಲ್ಲಾವಾರು ಶಿಕ್ಷೆ ಪ್ರಮಾಣ",
           "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಬೀಟ್‌ಗಳು"],
    },
  },

  expert: {
    title: L("Expert Workspace Guide", "ತಜ್ಞ ಕಾರ್ಯಕ್ಷೇತ್ರ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Expert mode runs deeper multi-agent investigations and keeps a working dossier beside the chat.",
            "ತಜ್ಞ ಮೋಡ್ ಆಳವಾದ ಬಹು-ಏಜೆಂಟ್ ತನಿಖೆ ನಡೆಸುತ್ತದೆ ಮತ್ತು ಚಾಟ್ ಪಕ್ಕದಲ್ಲಿ ಡಾಸಿಯರ್ ಇರಿಸುತ್ತದೆ."),
    blocks: [
      { h: L("The Brief", "ಸಾರಾಂಶ"), items: [
        [L("Bottom line", "ಮುಖ್ಯ ತೀರ್ಮಾನ"), L("The answer, with its K/D/I/U badge.", "K/D/I/U ಬ್ಯಾಡ್ಜ್‌ನೊಂದಿಗೆ ಉತ್ತರ.")],
        [L("Sources & method", "ಆಧಾರ ಮತ್ತು ವಿಧಾನ"), L("The method that produced the answer, how many records it read, the FIRs cited, and its integrity hash.",
                                                         "ಉತ್ತರ ನೀಡಿದ ವಿಧಾನ, ಓದಿದ ದಾಖಲೆಗಳು, ಉಲ್ಲೇಖಿತ FIR ಮತ್ತು ಸಮಗ್ರತಾ ಹ್ಯಾಶ್.")],
        [L("Insights", "ಒಳನೋಟಗಳು"), L("Concentration and gaps calculated from the table (D) - arithmetic you can check, never generated.",
                                        "ಕೋಷ್ಟಕದಿಂದ ಲೆಕ್ಕ ಹಾಕಿದ ಕೇಂದ್ರೀಕರಣ ಮತ್ತು ಅಂತರ (D) - ಪರಿಶೀಲಿಸಬಹುದಾದ ಲೆಕ್ಕ, ಉತ್ಪಾದಿಸಿದ್ದಲ್ಲ.")],
      ] },
      { h: L("Background tasks", "ಹಿನ್ನೆಲೆ ಕಾರ್ಯಗಳು"), items: [
        [L("Choose, then Run", "ಆಯ್ಕೆ, ನಂತರ ಚಲಾಯಿಸಿ"), L("OSINT search, AI/ML forecast, deep research, network, pattern, threat or a custom task. Nothing starts until you click Run.",
                                                         "OSINT, AI/ML ಮುನ್ಸೂಚನೆ, ಆಳವಾದ ಸಂಶೋಧನೆ, ಜಾಲ, ಮಾದರಿ, ಬೆದರಿಕೆ ಅಥವಾ ಕಸ್ಟಮ್. ಚಲಾಯಿಸಿ ಒತ್ತುವವರೆಗೆ ಏನೂ ಆರಂಭವಾಗುವುದಿಲ್ಲ.")],
        [L("Trust level", "ನಂಬಿಕೆಯ ಮಟ್ಟ"), L("Each task shows its class: OSINT and forecasts are I - leads and ranges, not facts.",
                                             "ಪ್ರತಿ ಕಾರ್ಯ ತನ್ನ ವರ್ಗ ತೋರಿಸುತ್ತದೆ: OSINT ಮತ್ತು ಮುನ್ಸೂಚನೆ I - ಸುಳಿವು ಮತ್ತು ವ್ಯಾಪ್ತಿ, ಸತ್ಯವಲ್ಲ.")],
        [L("Launch", "ಪ್ರಾರಂಭಿಸಿ"), L("Start a heavy analysis without blocking the chat.", "ಚಾಟ್ ನಿಲ್ಲಿಸದೆ ಭಾರೀ ವಿಶ್ಲೇಷಣೆ ಆರಂಭಿಸಿ.")],
        [L("Results", "ಫಲಿತಾಂಶ"), L("Pull finished analysis into the workspace.", "ಮುಗಿದ ವಿಶ್ಲೇಷಣೆಯನ್ನು ಕಾರ್ಯಕ್ಷೇತ್ರಕ್ಕೆ ತನ್ನಿ.")],
        [L("Stop", "ನಿಲ್ಲಿಸಿ"), L("Cancel a job you no longer need.", "ಅಗತ್ಯವಿಲ್ಲದ ಕಾರ್ಯವನ್ನು ರದ್ದುಗೊಳಿಸಿ.")],
      ] },
      { h: L("Dossier", "ಡಾಸಿಯರ್"), items: [
        [L("Notes", "ಟಿಪ್ಪಣಿಗಳು"), L("The right panel is your live report. Add notes and evidence as you go.", "ಬಲ ಪ್ಯಾನೆಲ್ ನಿಮ್ಮ ಲೈವ್ ವರದಿ. ಟಿಪ್ಪಣಿ ಮತ್ತು ಸಾಕ್ಷ್ಯ ಸೇರಿಸುತ್ತಾ ಹೋಗಿ.")],
        [L("Brief", "ವರದಿ"), L("Compile the final intelligence brief from what you collected.", "ಸಂಗ್ರಹಿಸಿದ ಮಾಹಿತಿಯಿಂದ ಅಂತಿಮ ಗುಪ್ತಚರ ವರದಿ ತಯಾರಿಸಿ.")],
      ] },
      { h: L("Agents", "ಏಜೆಂಟ್‌ಗಳು"), items: [
        [L("Specialists", "ತಜ್ಞರು"), L("Network, profile, forecast, map and alert agents work on the same question.", "ಜಾಲ, ಪ್ರೊಫೈಲ್, ಮುನ್ಸೂಚನೆ, ನಕ್ಷೆ ಮತ್ತು ಎಚ್ಚರಿಕೆ ಏಜೆಂಟ್‌ಗಳು ಒಂದೇ ಪ್ರಶ್ನೆಯ ಮೇಲೆ ಕೆಲಸ ಮಾಡುತ್ತವೆ.")],
        [L("Live steps", "ಲೈವ್ ಹಂತಗಳು"), L("Each step appears as it runs, so you can see what was checked.", "ಪ್ರತಿ ಹಂತ ನಡೆಯುತ್ತಿದ್ದಂತೆ ಕಾಣುತ್ತದೆ, ಏನು ಪರಿಶೀಲಿಸಲಾಯಿತು ಎಂದು ತಿಳಿಯುತ್ತದೆ.")],
      ] },
    ],
  },

  predict: {
    title: L("Predict Guide", "ಮುನ್ಸೂಚನೆ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Estimates crime risk for the next 7 days from historical FIRs, and explains each forecast.",
            "ಐತಿಹಾಸಿಕ FIR ಗಳಿಂದ ಮುಂದಿನ 7 ದಿನಗಳ ಅಪರಾಧ ಅಪಾಯವನ್ನು ಅಂದಾಜಿಸುತ್ತದೆ ಮತ್ತು ಪ್ರತಿ ಮುನ್ಸೂಚನೆಯನ್ನು ವಿವರಿಸುತ್ತದೆ."),
    blocks: [
      { h: L("On this screen", "ಈ ಪರದೆಯಲ್ಲಿ"), items: [
        [L("Forecast board", "ಮುನ್ಸೂಚನೆ ಫಲಕ"), L("Risk by zone and crime type, recalculated from live FIRs.", "ಲೈವ್ FIR ಗಳಿಂದ ಲೆಕ್ಕಹಾಕಿದ ವಲಯ ಮತ್ತು ಅಪರಾಧವಾರು ಅಪಾಯ.")],
        [L("Hypotheses", "ಊಹೆಗಳು"), L("Likely scenarios from past patterns, place and season.", "ಹಿಂದಿನ ಮಾದರಿ, ಸ್ಥಳ ಮತ್ತು ಋತುವಿನ ಆಧಾರದ ಸಂಭಾವ್ಯ ಸನ್ನಿವೇಶಗಳು.")],
        [L("Explanation graph", "ವಿವರಣೆ ಗ್ರಾಫ್"), L("Which signals shaped each forecast and its confidence.", "ಪ್ರತಿ ಮುನ್ಸೂಚನೆ ಮತ್ತು ಅದರ ವಿಶ್ವಾಸವನ್ನು ರೂಪಿಸಿದ ಸಂಕೇತಗಳು.")],
      ] },
      { h: L("Key terms", "ಪ್ರಮುಖ ಪದಗಳು"), items: [
        [L("Z-score", "Z-ಸ್ಕೋರ್"), L("How far a spike is from normal. 2.5 or more is unusual, not noise.", "ಏರಿಕೆ ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಎಷ್ಟು ದೂರ. 2.5 ಅಥವಾ ಹೆಚ್ಚು ಎಂದರೆ ಅಸಾಮಾನ್ಯ, ಆಕಸ್ಮಿಕವಲ್ಲ.")],
        [L("Forecast band", "ಮುನ್ಸೂಚನೆ ವ್ಯಾಪ್ತಿ"), L("The expected range of cases (e.g. 6–9) with its coverage (e.g. 90%).", "ನಿರೀಕ್ಷಿತ ಪ್ರಕರಣಗಳ ವ್ಯಾಪ್ತಿ (ಉದಾ. 6–9) ಮತ್ತು ಅದರ ವಿಶ್ವಾಸ (ಉದಾ. 90%).")],
        [L("Silence drop", "ಮೌನ ಕುಸಿತ"), L("Reports suddenly stop. This can mean under-recording, not safety.", "ವರದಿಗಳು ಇದ್ದಕ್ಕಿದ್ದಂತೆ ನಿಲ್ಲುತ್ತವೆ. ಇದು ಕಡಿಮೆ ದಾಖಲಾತಿಯ ಸೂಚನೆ ಆಗಿರಬಹುದು, ಸುರಕ್ಷತೆಯದ್ದಲ್ಲ.")],
        [L("Seasonal driver", "ಋತುಮಾನ ಕಾರಣ"), L("A rise explained by a festival or yearly pattern, such as Dasara.", "ದಸರಾದಂತಹ ಹಬ್ಬ ಅಥವಾ ವಾರ್ಷಿಕ ಮಾದರಿಯಿಂದಾದ ಏರಿಕೆ.")],
      ] },
    ],
    note: L("Forecasts support patrol planning. They are not evidence.", "ಮುನ್ಸೂಚನೆಗಳು ಗಸ್ತು ಯೋಜನೆಗೆ ನೆರವು. ಅವು ಸಾಕ್ಷ್ಯವಲ್ಲ."),
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
