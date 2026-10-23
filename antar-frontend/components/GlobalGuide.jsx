"use client";

import { useState, useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { HelpCircle, X } from "lucide-react";
import { useLang } from "@/components/Providers";

// ─────────────────────────────────────────────────────────────────────────────
// Page guides, one per working screen, written from what is on that screen now (update the
// guide when a screen changes). Every guide has the same shape so every screen reads the same way:
//   title · lead (one sentence: what this screen is for)
//   blocks: [{ h, items: [[term, explanation], …], warn? }]
//   examples (queries to type)  ·  tip (one sentence)  ·  note (a caveat)
// Every text is [English, Kannada].
// ─────────────────────────────────────────────────────────────────────────────
const L = (en, kn) => ({ en, kn });

const GUIDES = {
  chat: {
    title: L("Chat Guide", "ಚಾಟ್ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Ask the FIR register a question in English or Kannada, typed or spoken. Antar answers from the records and shows the FIRs behind every answer.",
            "FIR ದಾಖಲೆಗೆ ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಕನ್ನಡದಲ್ಲಿ, ಬರೆದು ಅಥವಾ ಮಾತನಾಡಿ ಪ್ರಶ್ನೆ ಕೇಳಿ. ಅಂತರ ದಾಖಲೆಗಳಿಂದ ಉತ್ತರಿಸುತ್ತದೆ ಮತ್ತು ಪ್ರತಿ ಉತ್ತರದ ಹಿಂದಿನ FIR ಗಳನ್ನು ತೋರಿಸುತ್ತದೆ."),
    blocks: [
      { h: L("Asking", "ಕೇಳುವುದು"), items: [
        [L("The question box", "ಪ್ರಶ್ನೆ ಪೆಟ್ಟಿಗೆ"), L("Type and press Enter, or press the mic and speak. Tab picks the suggested question shown in grey.", "ಟೈಪ್ ಮಾಡಿ Enter ಒತ್ತಿ, ಅಥವಾ ಮೈಕ್ ಒತ್ತಿ ಮಾತನಾಡಿ. ಬೂದು ಬಣ್ಣದ ಸಲಹೆ ಪ್ರಶ್ನೆಯನ್ನು Tab ಆರಿಸುತ್ತದೆ.")],
        [L("Suggested questions", "ಸಲಹೆ ಪ್ರಶ್ನೆಗಳು"), L("Click one to ask it. The refresh button shows more; a year below the list shows questions for that year.", "ಕೇಳಲು ಒಂದನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿ. ರಿಫ್ರೆಶ್ ಬಟನ್ ಇನ್ನಷ್ಟು ತೋರಿಸುತ್ತದೆ; ಕೆಳಗಿನ ವರ್ಷ ಆ ವರ್ಷದ ಪ್ರಶ್ನೆಗಳನ್ನು ತೋರಿಸುತ್ತದೆ.")],
        [L("Antar agents", "ಅಂತರ ಏಜೆಂಟ್‌ಗಳು"), L("Pick an agent in the row above the box to send your first question through it. What it does opens in Docs.", "ನಿಮ್ಮ ಮೊದಲ ಪ್ರಶ್ನೆಯನ್ನು ಅದರ ಮೂಲಕ ಕಳುಹಿಸಲು ಪೆಟ್ಟಿಗೆಯ ಮೇಲಿನ ಸಾಲಿನಲ್ಲಿ ಏಜೆಂಟ್ ಆರಿಸಿ.")],
        [L("Docs mode", "Docs ಮೋಡ್"), L("The line under the box says whether questions go to Docs or straight to Chat. Click it to switch.", "ಪ್ರಶ್ನೆಗಳು Docs ಗೆ ಹೋಗುತ್ತವೆಯೇ ಅಥವಾ ನೇರವಾಗಿ ಚಾಟ್‌ಗೆ ಎಂದು ಪೆಟ್ಟಿಗೆಯ ಕೆಳಗಿನ ಸಾಲು ಹೇಳುತ್ತದೆ. ಬದಲಿಸಲು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("New Session", "ಹೊಸ ಸೆಷನ್"), L("Starts a fresh conversation. Follow-up questions use the conversation you are in.", "ಹೊಸ ಸಂಭಾಷಣೆ ಆರಂಭಿಸುತ್ತದೆ. ಮುಂದಿನ ಪ್ರಶ್ನೆಗಳು ಈಗಿನ ಸಂಭಾಷಣೆಯನ್ನು ಬಳಸುತ್ತವೆ.")],
      ] },
      { h: L("Reading an answer", "ಉತ್ತರ ಓದುವುದು"), items: [
        [L("Bottom line first", "ಮೊದಲು ನೇರ ಉತ್ತರ"), L("The first sentence is the answer; the list or table under it shows the figures it came from. Key numbers are in cyan.", "ಮೊದಲ ವಾಕ್ಯವೇ ಉತ್ತರ; ಅದರ ಕೆಳಗಿನ ಪಟ್ಟಿ ಅಂಕಿಗಳ ಮೂಲ ತೋರಿಸುತ್ತದೆ. ಮುಖ್ಯ ಸಂಖ್ಯೆಗಳು ಸಯಾನ್ ಬಣ್ಣದಲ್ಲಿ.")],
        [L("Where it comes from", "ಉತ್ತರದ ಮೂಲ"), L("The badge says From the records, Calculated, Estimate, or Not on record.", "ಗುರುತು ಹೇಳುತ್ತದೆ: ದಾಖಲೆಯಿಂದ, ಲೆಕ್ಕಾಚಾರ, ಅಂದಾಜು, ಅಥವಾ ದಾಖಲೆಯಲ್ಲಿಲ್ಲ.")],
        [L("Thought for Ns", "ಯೋಚಿಸಿದ ಸಮಯ"), L("Above the answer, with how many agents worked on it. Click it to see each step.", "ಉತ್ತರದ ಮೇಲೆ, ಎಷ್ಟು ಏಜೆಂಟ್‌ಗಳು ಕೆಲಸ ಮಾಡಿದವು ಎಂಬುದರೊಂದಿಗೆ. ಪ್ರತಿ ಹಂತ ನೋಡಲು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("Evidence and checks", "ಸಾಕ್ಷ್ಯ ಮತ್ತು ಪರಿಶೀಲನೆ"), L("Evidence lists the FIR records used. Misuse check: passed means the question was screened before it ran.", "Evidence ಬಳಸಿದ FIR ದಾಖಲೆಗಳನ್ನು ಪಟ್ಟಿ ಮಾಡುತ್ತದೆ. Misuse check: passed ಎಂದರೆ ಪ್ರಶ್ನೆ ಚಾಲನೆಗೂ ಮೊದಲು ಪರಿಶೀಲಿಸಲಾಗಿದೆ.")],
        [L("How this was answered", "ಹೇಗೆ ಉತ್ತರಿಸಲಾಯಿತು"), L("Opens the query that ran and the rows it read.", "ಚಾಲನೆಯಾದ ಪ್ರಶ್ನಾವಳಿ ಮತ್ತು ಓದಿದ ಸಾಲುಗಳನ್ನು ತೆರೆಯುತ್ತದೆ.")],
        [L("Next", "ಮುಂದೆ"), L("A follow-up question that fits the answer. Click to ask it.", "ಉತ್ತರಕ್ಕೆ ಹೊಂದುವ ಮುಂದಿನ ಪ್ರಶ್ನೆ. ಕೇಳಲು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
      ] },
      { h: L("Under each answer", "ಪ್ರತಿ ಉತ್ತರದ ಕೆಳಗೆ"), items: [
        [L("Regenerate · Copy", "ಮರು-ರಚನೆ · ನಕಲು"), L("Ask again, or copy the answer text.", "ಮತ್ತೆ ಕೇಳಿ, ಅಥವಾ ಉತ್ತರದ ಪಠ್ಯ ನಕಲಿಸಿ.")],
        [L("Listen", "ಆಲಿಸಿ"), L("Reads the answer aloud. Click again to stop.", "ಉತ್ತರವನ್ನು ಗಟ್ಟಿಯಾಗಿ ಓದುತ್ತದೆ. ನಿಲ್ಲಿಸಲು ಮತ್ತೆ ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("Trace", "ಜಾಡು"), L("Opens this answer in Observability & Trace.", "ಈ ಉತ್ತರವನ್ನು ವೀಕ್ಷಣೆ ಮತ್ತು ಜಾಡಿನಲ್ಲಿ ತೆರೆಯುತ್ತದೆ.")],
        [L("Export report", "ವರದಿ ರಫ್ತು"), L("Opens the whole session as a printable report.", "ಸಂಪೂರ್ಣ ಸೆಷನ್ ಅನ್ನು ಮುದ್ರಿಸಬಹುದಾದ ವರದಿಯಾಗಿ ತೆರೆಯುತ್ತದೆ.")],
        [L("Good / poor answer", "ಉತ್ತಮ / ಕಳಪೆ ಉತ್ತರ"), L("Your rating is recorded and used to check answer quality.", "ನಿಮ್ಮ ಅಂಕ ದಾಖಲಾಗುತ್ತದೆ ಮತ್ತು ಉತ್ತರದ ಗುಣಮಟ್ಟ ಪರಿಶೀಲನೆಗೆ ಬಳಕೆಯಾಗುತ್ತದೆ.")],
      ] },
      { h: L("Commands and limits", "ಆಜ್ಞೆಗಳು ಮತ್ತು ಮಿತಿಗಳು"), items: [
        [L("/query", "/query"), L("A count or list straight from the register, e.g. /query thefts in Mysuru 2022.", "ದಾಖಲೆಯಿಂದ ನೇರ ಎಣಿಕೆ ಅಥವಾ ಪಟ್ಟಿ, ಉದಾ. /query ಮೈಸೂರು ಕಳ್ಳತನ 2022.")],
        [L("/connect", "/connect"), L("Links between accused, vehicles and phones across cases.", "ಪ್ರಕರಣಗಳಾದ್ಯಂತ ಆರೋಪಿ, ವಾಹನ, ಫೋನ್ ನಡುವಿನ ಸಂಪರ್ಕಗಳು.")],
        [L("/anticipate", "/anticipate"), L("A 7-day forecast for a district, station or crime type.", "ಜಿಲ್ಲೆ, ಠಾಣೆ ಅಥವಾ ಅಪರಾಧ ಪ್ರಕಾರಕ್ಕೆ 7 ದಿನಗಳ ಮುನ್ಸೂಚನೆ.")],
        [L("/osint", "/osint"), L("Open-web checks on an identifier. Always marked unverified.", "ಗುರುತಿನ ಮೇಲೆ ಮುಕ್ತ-ವೆಬ್ ಪರಿಶೀಲನೆ. ಯಾವಾಗಲೂ ಪರಿಶೀಲಿಸಿಲ್ಲ ಎಂದು ಗುರುತು.")],
        [L("No guessing", "ಊಹೆ ಇಲ್ಲ"), L("If no FIR matches, the answer says so. Questions that target a caste, religion or community are refused.", "ಯಾವ FIR ಹೊಂದದಿದ್ದರೆ ಉತ್ತರ ಹಾಗೆ ಹೇಳುತ್ತದೆ. ಜಾತಿ, ಧರ್ಮ ಅಥವಾ ಸಮುದಾಯವನ್ನು ಗುರಿಯಾಗಿಸುವ ಪ್ರಶ್ನೆಗಳನ್ನು ನಿರಾಕರಿಸಲಾಗುತ್ತದೆ.")],
      ] },
    ],
    examples: {
      en: ["Which police stations recorded the most cybercrime in 2022?", "Fastest-growing crime groups 2021 to 2022?", "/anticipate chain snatching in Bengaluru City"],
      kn: ["2022 ರಲ್ಲಿ ಹೆಚ್ಚು ಸೈಬರ್ ಅಪರಾಧ ದಾಖಲಿಸಿದ ಠಾಣೆಗಳು ಯಾವುವು?", "2021 ರಿಂದ 2022 ಕ್ಕೆ ವೇಗವಾಗಿ ಬೆಳೆದ ಅಪರಾಧ ಗುಂಪುಗಳು?", "/anticipate ಬೆಂಗಳೂರು ನಗರ ಸರಗಳ್ಳತನ"],
    },
  },

  predict: {
    title: L("Predict Guide", "ಮುನ್ಸೂಚನೆ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Where crime is likely to rise in the next 7 days, area by area, so patrols and bandobast can be planned before the cases come in.",
            "ಮುಂದಿನ 7 ದಿನಗಳಲ್ಲಿ ಎಲ್ಲಿ ಅಪರಾಧ ಹೆಚ್ಚಾಗಬಹುದು, ಪ್ರದೇಶವಾರು - ಪ್ರಕರಣಗಳು ಬರುವ ಮೊದಲೇ ಗಸ್ತು ಮತ್ತು ಬಂದೋಬಸ್ತ್ ಯೋಜಿಸಲು."),
    blocks: [
      { h: L("The top of the page", "ಪುಟದ ಮೇಲ್ಭಾಗ"), items: [
        [L("See this week's plan", "ಈ ವಾರದ ಯೋಜನೆ"), L("Jumps to 01, the actions for this week.", "01 ಕ್ಕೆ, ಈ ವಾರದ ಕ್ರಮಗಳಿಗೆ ಹೋಗುತ್ತದೆ.")],
        [L("The line under it", "ಅದರ ಕೆಳಗಿನ ಸಾಲು"), L("When it was assessed, how many areas, and how often past ranges held. Click the last to see the track record.", "ಯಾವಾಗ ಮೌಲ್ಯಮಾಪನ, ಎಷ್ಟು ಪ್ರದೇಶಗಳು, ಮತ್ತು ಹಿಂದಿನ ವ್ಯಾಪ್ತಿಗಳು ಎಷ್ಟು ಬಾರಿ ಸರಿಯಾದವು. ದಾಖಲೆ ನೋಡಲು ಕೊನೆಯದನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("The five figures", "ಐದು ಅಂಕಿಗಳು"), L("High-risk areas, above normal, reporting drops, active alerts and events in 3 weeks. Coloured means it needs a look; click one to go to it.", "ಹೆಚ್ಚು ಅಪಾಯ, ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು, ವರದಿ ಇಳಿಕೆ, ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆ, 3 ವಾರಗಳಲ್ಲಿ ಉತ್ಸವ. ಬಣ್ಣ ಇದ್ದರೆ ಗಮನಿಸಿ; ಹೋಗಲು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
      ] },
      { h: L("01 · This week's plan", "01 · ಈ ವಾರದ ಯೋಜನೆ"), items: [
        [L("One line per action", "ಪ್ರತಿ ಕ್ರಮಕ್ಕೆ ಒಂದು ಸಾಲು"), L("Strongest first: where to add patrols, which station to check, which event to plan for. Open a line for the reason and the stations.", "ಮುಖ್ಯವಾದದ್ದು ಮೊದಲು: ಎಲ್ಲಿ ಗಸ್ತು, ಯಾವ ಠಾಣೆ ಪರಿಶೀಲನೆ, ಯಾವ ಉತ್ಸವಕ್ಕೆ ಯೋಜನೆ. ಕಾರಣ ಮತ್ತು ಠಾಣೆಗಳಿಗೆ ಸಾಲು ತೆರೆಯಿರಿ.")],
        [L("Copy for the briefing note", "ಬ್ರೀಫಿಂಗ್ ಟಿಪ್ಪಣಿ ನಕಲಿಸಿ"), L("Copies the whole week as plain text for a briefing.", "ಇಡೀ ವಾರವನ್ನು ಸರಳ ಪಠ್ಯವಾಗಿ ನಕಲಿಸುತ್ತದೆ.")],
      ] },
      { h: L("02 · Forecast · 03 · Alerts", "02 · ಮುನ್ಸೂಚನೆ · 03 · ಎಚ್ಚರಿಕೆಗಳು"), items: [
        [L("Forecast cards", "ಮುನ್ಸೂಚನೆ ಕಾರ್ಡ್‌ಗಳು"), L("Each card is an area: the crime most likely to move, how far from normal, and the cases expected in the next 7 days.", "ಪ್ರತಿ ಕಾರ್ಡ್ ಒಂದು ಪ್ರದೇಶ: ಹೆಚ್ಚು ಬದಲಾಗಬಹುದಾದ ಅಪರಾಧ, ಸಾಮಾನ್ಯದಿಂದ ಎಷ್ಟು ದೂರ, ಮುಂದಿನ 7 ದಿನಗಳ ನಿರೀಕ್ಷಿತ ಪ್ರಕರಣಗಳು.")],
        [L("Filters and search", "ಫಿಲ್ಟರ್ ಮತ್ತು ಹುಡುಕಾಟ"), L("Needs attention, High risk, Above normal, Reporting drops, Event this week, High confidence; or type an area or crime.", "ಗಮನ ಬೇಕು, ಹೆಚ್ಚು ಅಪಾಯ, ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು, ವರದಿ ಇಳಿಕೆ, ಈ ವಾರ ಉತ್ಸವ, ಹೆಚ್ಚು ವಿಶ್ವಾಸ; ಅಥವಾ ಪ್ರದೇಶ/ಅಪರಾಧ ಟೈಪ್ ಮಾಡಿ.")],
        [L("Reporting drop", "ವರದಿ ಇಳಿಕೆ"), L("Far fewer FIRs than usual. Often slower registration, not less crime: check the station.", "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ತುಂಬಾ ಕಡಿಮೆ FIR. ಹೆಚ್ಚಾಗಿ ತಡವಾದ ದಾಖಲಾತಿ, ಕಡಿಮೆ ಅಪರಾಧ ಅಲ್ಲ: ಠಾಣೆ ಪರಿಶೀಲಿಸಿ.")],
        [L("Active alerts", "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು"), L("Recent cases that broke an area's usual pattern. Pick one to see why.", "ಪ್ರದೇಶದ ಸಾಮಾನ್ಯ ಮಾದರಿ ಮುರಿದ ಇತ್ತೀಚಿನ ಪ್ರಕರಣಗಳು. ಕಾರಣಕ್ಕೆ ಒಂದನ್ನು ಆರಿಸಿ.")],
        [L("Statewide units", "ರಾಜ್ಯಮಟ್ಟದ ಘಟಕಗಳು"), L("Units like CID or Railways register FIRs statewide. They are listed apart, not ranked with areas.", "CID, ರೈಲ್ವೆ ಮುಂತಾದ ಘಟಕಗಳು ರಾಜ್ಯಾದ್ಯಂತ FIR ದಾಖಲಿಸುತ್ತವೆ. ಪ್ರತ್ಯೇಕವಾಗಿ ಪಟ್ಟಿ, ಪ್ರದೇಶಗಳೊಂದಿಗೆ ಶ್ರೇಣಿ ಇಲ್ಲ.")],
      ] },
      { h: L("Opening a forecast", "ಮುನ್ಸೂಚನೆ ತೆರೆಯುವುದು"), items: [
        [L("Why this forecast", "ಏಕೆ ಈ ಮುನ್ಸೂಚನೆ"), L("The expected range, why the confidence is what it is, and what the model saw. Stations to watch and the recommended action sit on the right.", "ನಿರೀಕ್ಷಿತ ವ್ಯಾಪ್ತಿ, ವಿಶ್ವಾಸದ ಕಾರಣ, ಮಾದರಿ ಕಂಡದ್ದು. ಗಮನಿಸಬೇಕಾದ ಠಾಣೆಗಳು ಮತ್ತು ಶಿಫಾರಸು ಬಲಭಾಗದಲ್ಲಿ.")],
        [L("Mark as reviewed", "ಪರಿಶೀಲಿಸಲಾಗಿದೆ"), L("Records that you have looked at it. Ask Antar sends it to Chat.", "ನೀವು ನೋಡಿದ್ದೀರಿ ಎಂದು ದಾಖಲಿಸುತ್ತದೆ. Ask Antar ಅದನ್ನು ಚಾಟ್‌ಗೆ ಕಳುಹಿಸುತ್ತದೆ.")],
        [L("Quiet tools", "ಇತರ ಸಾಧನಗಳು"), L("How this was worked out (the reasoning graph), What if (an event's effect), Audit trail, Open on map.", "ಹೇಗೆ ಲೆಕ್ಕ ಹಾಕಲಾಯಿತು, ಹೀಗಾದರೆ (ಉತ್ಸವದ ಪರಿಣಾಮ), ಆಡಿಟ್ ಜಾಡು, ನಕ್ಷೆಯಲ್ಲಿ ತೆರೆಯಿರಿ.")],
      ] },
      { h: L("04 · Events and the fold-outs", "04 · ಉತ್ಸವಗಳು ಮತ್ತು ಇತರೆ"), items: [
        [L("Events ahead", "ಮುಂಬರುವ ಉತ್ಸವಗಳು"), L("Festivals in the next 3 weeks and what each did to registered cases in past years. Copy a bandobast note from here.", "ಮುಂದಿನ 3 ವಾರಗಳ ಉತ್ಸವಗಳು ಮತ್ತು ಹಿಂದಿನ ವರ್ಷಗಳಲ್ಲಿ ಅವುಗಳ ಪರಿಣಾಮ. ಇಲ್ಲಿಂದ ಬಂದೋಬಸ್ತ್ ಟಿಪ್ಪಣಿ ನಕಲಿಸಿ.")],
        [L("Investigation leads", "ತನಿಖಾ ಸುಳಿವುಗಳು"), L("FIRs that share an accused, vehicle, phone or UPI ID. Opens on request.", "ಆರೋಪಿ, ವಾಹನ, ಫೋನ್ ಅಥವಾ UPI ಹಂಚಿಕೊಳ್ಳುವ FIR ಗಳು. ಕೇಳಿದಾಗ ತೆರೆಯುತ್ತದೆ.")],
        [L("How reliable is this forecast", "ಮುನ್ಸೂಚನೆ ಎಷ್ಟು ನಂಬಲರ್ಹ"), L("How often the real count fell inside the range on past weeks, the engine's confidence and what it is built on.", "ಹಿಂದಿನ ವಾರಗಳಲ್ಲಿ ನಿಜವಾದ ಎಣಿಕೆ ವ್ಯಾಪ್ತಿಯೊಳಗೆ ಎಷ್ಟು ಬಾರಿ ಬಿತ್ತು, ಎಂಜಿನ್ ವಿಶ್ವಾಸ ಮತ್ತು ಆಧಾರ.")],
      ] },
    ],
    note: L("A forecast is an estimate to plan patrols with. It is not evidence and not a reason to act against any person.", "ಮುನ್ಸೂಚನೆ ಗಸ್ತು ಯೋಜನೆಗೆ ಅಂದಾಜು ಮಾತ್ರ. ಇದು ಸಾಕ್ಷ್ಯವಲ್ಲ, ಯಾವುದೇ ವ್ಯಕ್ತಿಯ ವಿರುದ್ಧ ಕ್ರಮಕ್ಕೆ ಕಾರಣವಲ್ಲ."),
  },

  brain: {
    title: L("Brain Guide", "ಬ್ರೈನ್ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("FIRs drawn as dots, joined where they share an accused, vehicle, UPI ID or IP address. Below the graph, the data overview counts what is on screen.",
            "FIR ಗಳನ್ನು ಚುಕ್ಕೆಗಳಾಗಿ, ಒಂದೇ ಆರೋಪಿ, ವಾಹನ, UPI ಅಥವಾ IP ಹಂಚಿಕೊಂಡಲ್ಲಿ ಜೋಡಿಸಲಾಗಿದೆ. ಗ್ರಾಫ್ ಕೆಳಗೆ, ದತ್ತಾಂಶ ಅವಲೋಕನ ಪರದೆಯಲ್ಲಿರುವುದನ್ನು ಎಣಿಸುತ್ತದೆ."),
    blocks: [
      { h: L("Moving around", "ಸಂಚರಿಸುವುದು"), items: [
        [L("Rotate · zoom", "ತಿರುಗಿಸಿ · ಝೂಮ್"), L("Drag to turn, scroll or pinch to zoom.", "ತಿರುಗಿಸಲು ಎಳೆಯಿರಿ, ಝೂಮ್‌ಗೆ ಸ್ಕ್ರಾಲ್ ಅಥವಾ ಪಿಂಚ್.")],
        [L("Click a dot", "ಚುಕ್ಕೆ ಕ್ಲಿಕ್ ಮಾಡಿ"), L("Focuses its linked group. Click empty space to go back; Reset to Default View starts over.", "ಅದರ ಸಂಪರ್ಕಿತ ಗುಂಪಿಗೆ ಕೇಂದ್ರೀಕರಿಸುತ್ತದೆ. ಹಿಂತಿರುಗಲು ಖಾಲಿ ಜಾಗ ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("Find", "ಹುಡುಕಿ"), L("The box at the top left finds an accused ID, a district or a crime type.", "ಮೇಲಿನ ಎಡದ ಪೆಟ್ಟಿಗೆ ಆರೋಪಿ ID, ಜಿಲ್ಲೆ ಅಥವಾ ಅಪರಾಧ ಪ್ರಕಾರವನ್ನು ಹುಡುಕುತ್ತದೆ.")],
        [L("Top Brain · Bottom data overview", "ಮೇಲೆ ಬ್ರೈನ್ · ಕೆಳಗೆ ಅವಲೋಕನ"), L("The links at the bottom right jump between the graph and the overview.", "ಕೆಳ ಬಲದ ಲಿಂಕ್‌ಗಳು ಗ್ರಾಫ್ ಮತ್ತು ಅವಲೋಕನದ ನಡುವೆ ಜಿಗಿಯುತ್ತವೆ.")],
      ] },
      { h: L("Controls on the left", "ಎಡಭಾಗದ ನಿಯಂತ್ರಣಗಳು"), items: [
        [L("All Data · Focus · Crime Graph", "ಎಲ್ಲಾ · ಫೋಕಸ್ · ಅಪರಾಧ ಗ್ರಾಫ್"), L("The whole graph, the focused group, or crime types as a chart.", "ಇಡೀ ಗ್ರಾಫ್, ಕೇಂದ್ರೀಕೃತ ಗುಂಪು, ಅಥವಾ ಅಪರಾಧ ಪ್ರಕಾರಗಳ ಚಾರ್ಟ್.")],
        [L("3D · 2D", "3D · 2D"), L("A globe, or a flat map of the same links.", "ಗ್ಲೋಬ್, ಅಥವಾ ಅದೇ ಸಂಪರ್ಕಗಳ ಸಮತಟ್ಟು ನಕ್ಷೆ.")],
        [L("Evidence · Crime type", "ಸಾಕ್ಷ್ಯ · ಅಪರಾಧ ಪ್ರಕಾರ"), L("Group the dots by what links them, or by the kind of crime. Crime narrows to one type.", "ಚುಕ್ಕೆಗಳನ್ನು ಸಂಪರ್ಕದ ಆಧಾರದ ಮೇಲೆ ಅಥವಾ ಅಪರಾಧ ಪ್ರಕಾರದಿಂದ ಗುಂಪು ಮಾಡಿ.")],
        [L("Case activity", "ಪ್ರಕರಣ ಚಟುವಟಿಕೆ"), L("Daily FIRs for a year. Step the year, choose a year span or FIR range, pick a day; This view or Full dataset; Reset puts it back.", "ವರ್ಷದ ದೈನಂದಿನ FIR. ವರ್ಷ ಬದಲಿಸಿ, ವ್ಯಾಪ್ತಿ ಆರಿಸಿ, ದಿನ ಆರಿಸಿ; Reset ಮೊದಲಿನಂತೆ ಮಾಡುತ್ತದೆ.")],
      ] },
      { h: L("The focus card", "ಫೋಕಸ್ ಕಾರ್ಡ್"), items: [
        [L("Summary", "ಸಾರಾಂಶ"), L("What the group is, why it matters, and suggested next steps (for example a KYC request for a shared UPI ID).", "ಗುಂಪು ಏನು, ಏಕೆ ಮುಖ್ಯ, ಮತ್ತು ಮುಂದಿನ ಹೆಜ್ಜೆಗಳು (ಉದಾ. ಹಂಚಿದ UPI ಗೆ KYC ವಿನಂತಿ).")],
        [L("Sections", "ವಿಭಾಗಗಳು"), L("Type of crime, shared identifiers, people, where registered, when, the FIRs, and how they connect. Expand all, or widen the card.", "ಅಪರಾಧ ಪ್ರಕಾರ, ಹಂಚಿದ ಗುರುತುಗಳು, ಜನರು, ಎಲ್ಲಿ, ಯಾವಾಗ, FIR ಗಳು, ಹೇಗೆ ಸಂಪರ್ಕ. ಎಲ್ಲವನ್ನೂ ತೆರೆಯಿರಿ ಅಥವಾ ಕಾರ್ಡ್ ವಿಸ್ತರಿಸಿ.")],
        [L("Record links, not proof", "ಸಂಪರ್ಕ, ಪುರಾವೆ ಅಲ್ಲ"), L("A link is a lead to check. Read the FIRs before acting.", "ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಬೇಕಾದ ಸುಳಿವು. ಕ್ರಮಕ್ಕೆ ಮೊದಲು FIR ಓದಿ.")],
      ] },
      { h: L("Agents, Terminal, Fast Run", "ಏಜೆಂಟ್, ಟರ್ಮಿನಲ್, ಫಾಸ್ಟ್ ರನ್"), items: [
        [L("Agents on the graph", "ಗ್ರಾಫ್ ಮೇಲಿನ ಏಜೆಂಟ್‌ಗಳು"), L("Click a record then an agent, or drag the agent onto it. An agent says so when a record gives it nothing to work on.", "ದಾಖಲೆ ಕ್ಲಿಕ್ ಮಾಡಿ ನಂತರ ಏಜೆಂಟ್, ಅಥವಾ ಏಜೆಂಟ್ ಅನ್ನು ಅದರ ಮೇಲೆ ಎಳೆಯಿರಿ.")],
        [L("Fast Run", "ಫಾಸ್ಟ್ ರನ್"), L("Scans the records in view and lists what stands out, agent by agent.", "ನೋಟದ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ ಗಮನಾರ್ಹವಾದುದನ್ನು ಏಜೆಂಟ್‌ವಾರು ಪಟ್ಟಿ ಮಾಡುತ್ತದೆ.")],
        [L("Terminal", "ಟರ್ಮಿನಲ್"), L("Commands for the agents after a login. help lists them; /think, /connect S0041 and /anticipate are the three modes.", "ಲಾಗಿನ್ ನಂತರ ಏಜೆಂಟ್ ಆಜ್ಞೆಗಳು. help ಪಟ್ಟಿ ಮಾಡುತ್ತದೆ; /think, /connect, /anticipate ಮೂರು ಮೋಡ್‌ಗಳು.")],
        [L("Layers & Filters · View summary", "ಲೇಯರ್ · ವೀಕ್ಷಣೆ ಸಾರಾಂಶ"), L("Top right: which links and crime types show, and the view in a few lines.", "ಮೇಲಿನ ಬಲ: ಯಾವ ಸಂಪರ್ಕ ಮತ್ತು ಅಪರಾಧ ಪ್ರಕಾರ ಕಾಣುತ್ತದೆ, ಮತ್ತು ನೋಟದ ಸಾರಾಂಶ.")],
      ] },
      { h: L("Data overview (below the graph)", "ದತ್ತಾಂಶ ಅವಲೋಕನ (ಗ್ರಾಫ್ ಕೆಳಗೆ)"), items: [
        [L("Linked records · Full Data Set", "ಸಂಪರ್ಕಿತ ದಾಖಲೆ · ಪೂರ್ಣ ದತ್ತಾಂಶ"), L("The curated set the Brain draws, or the whole 10-lakh FIR register.", "ಬ್ರೈನ್ ಚಿತ್ರಿಸುವ ಆಯ್ದ ಸಂಗ್ರಹ, ಅಥವಾ ಇಡೀ 10 ಲಕ್ಷ FIR ದಾಖಲೆ.")],
        [L("Show the N FIRs", "N FIR ತೋರಿಸಿ"), L("On Linked records: focuses the Brain on those FIRs and lists them in the table below.", "ಸಂಪರ್ಕಿತ ದಾಖಲೆಯಲ್ಲಿ: ಆ FIR ಗಳಿಗೆ ಬ್ರೈನ್ ಕೇಂದ್ರೀಕರಿಸಿ ಕೆಳಗಿನ ಪಟ್ಟಿಯಲ್ಲಿ ತೋರಿಸುತ್ತದೆ.")],
        [L("Chargesheet deadline", "ದೋಷಾರೋಪ ಗಡುವು"), L("Open investigations past 90 days (act now) and those reaching 60 or 90 days this week (due soon), with the stations holding most.", "90 ದಿನ ದಾಟಿದವು (ಈಗಲೇ ಕ್ರಮ) ಮತ್ತು ಈ ವಾರ 60/90 ದಿನ ತಲುಪುವವು (ಶೀಘ್ರ ಗಡುವು), ಹೆಚ್ಚು ಇರುವ ಠಾಣೆಗಳೊಂದಿಗೆ.")],
        [L("Case outcomes", "ಪ್ರಕರಣ ಫಲಿತಾಂಶ"), L("Out of every 100 FIRs: arrests, chargesheets, convictions; then the rates per accused.", "ಪ್ರತಿ 100 FIR ಗೆ: ಬಂಧನ, ದೋಷಾರೋಪ, ಶಿಕ್ಷೆ; ನಂತರ ಪ್ರತಿ ಆರೋಪಿಯ ದರ.")],
        [L("Charts and FIR records", "ಚಾರ್ಟ್ ಮತ್ತು FIR ದಾಖಲೆ"), L("Click a crime category or district to filter; click a row in the table to open that FIR.", "ಫಿಲ್ಟರ್‌ಗೆ ಅಪರಾಧ ವರ್ಗ ಅಥವಾ ಜಿಲ್ಲೆ ಕ್ಲಿಕ್ ಮಾಡಿ; FIR ತೆರೆಯಲು ಸಾಲು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
      ] },
    ],
  },

  map: {
    title: L("Map Guide", "ನಕ್ಷೆ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Karnataka by district for the day or period you pick: each dot is one FIR, and the panels say where crime is concentrated and where to look next.",
            "ನೀವು ಆರಿಸಿದ ದಿನ ಅಥವಾ ಅವಧಿಗೆ ಜಿಲ್ಲಾವಾರು ಕರ್ನಾಟಕ: ಪ್ರತಿ ಚುಕ್ಕೆ ಒಂದು FIR, ಮತ್ತು ಅಪರಾಧ ಎಲ್ಲಿ ಕೇಂದ್ರೀಕೃತ, ಮುಂದೆ ಎಲ್ಲಿ ನೋಡಬೇಕು ಎಂದು ಫಲಕಗಳು ಹೇಳುತ್ತವೆ."),
    blocks: [
      { h: L("Choose what to see", "ಏನನ್ನು ನೋಡಬೇಕು"), items: [
        [L("Crime types", "ಅಪರಾಧ ಪ್ರಕಾರ"), L("The words along the top: All Crimes, Theft, Robbery and more. More lists the rest.", "ಮೇಲಿನ ಪದಗಳು: ಎಲ್ಲಾ, ಕಳ್ಳತನ, ದರೋಡೆ ಇತ್ಯಾದಿ. More ಉಳಿದವು.")],
        [L("01 · Calendar", "01 · ಕ್ಯಾಲೆಂಡರ್"), L("Pick a day, then Day, 7 days or 28 days. TODAY jumps to the latest date.", "ದಿನ ಆರಿಸಿ, ನಂತರ ದಿನ, 7 ದಿನ ಅಥವಾ 28 ದಿನ. TODAY ಇತ್ತೀಚಿನ ದಿನಾಂಕಕ್ಕೆ.")],
        [L("District", "ಜಿಲ್ಲೆ"), L("Choose from the box on the map, or click a district. Its card opens on the right.", "ನಕ್ಷೆಯ ಪೆಟ್ಟಿಗೆಯಿಂದ ಆರಿಸಿ ಅಥವಾ ಜಿಲ್ಲೆ ಕ್ಲಿಕ್ ಮಾಡಿ. ಬಲಭಾಗದಲ್ಲಿ ಕಾರ್ಡ್ ತೆರೆಯುತ್ತದೆ.")],
      ] },
      { h: L("The left column", "ಎಡ ಕಾಲಮ್"), items: [
        [L("02 · Karnataka Crime Report", "02 · ಕರ್ನಾಟಕ ಅಪರಾಧ ವರದಿ"), L("Cases for the period, against the day before and the last 30 days. Open report gives the full breakdown.", "ಅವಧಿಯ ಪ್ರಕರಣಗಳು, ಹಿಂದಿನ ದಿನ ಮತ್ತು 30 ದಿನಗಳೊಂದಿಗೆ. Open report ಪೂರ್ಣ ವಿವರ.")],
        [L("03 · Police districts with most cases", "03 · ಹೆಚ್ಚು ಪ್ರಕರಣದ ಜಿಲ್ಲೆಗಳು"), L("The busiest districts for the period.", "ಅವಧಿಯ ಅತಿ ಹೆಚ್ಚು ಪ್ರಕರಣದ ಜಿಲ್ಲೆಗಳು.")],
        [L("Repeat locations", "ಪುನರಾವರ್ತಿತ ಸ್ಥಳಗಳು"), L("Spots with 3 or more FIRs on different days in 90 days. Active means a case in the last 14 days; click one for its card.", "90 ದಿನಗಳಲ್ಲಿ ಬೇರೆ ದಿನಗಳಲ್ಲಿ 3+ FIR ಇರುವ ಸ್ಥಳಗಳು. ಸಕ್ರಿಯ = ಕಳೆದ 14 ದಿನಗಳಲ್ಲಿ ಪ್ರಕರಣ.")],
      ] },
      { h: L("The right column", "ಬಲ ಕಾಲಮ್"), items: [
        [L("View summary", "ವೀಕ್ಷಣೆ ಸಾರಾಂಶ"), L("In short at the top, then confirmed hotspots, any place above its usual level, the next 7 days and patrol to consider.", "ಮೇಲೆ ಸಂಕ್ಷಿಪ್ತ, ನಂತರ ಖಚಿತ ಹಾಟ್‌ಸ್ಪಾಟ್, ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು, ಮುಂದಿನ 7 ದಿನ, ಗಸ್ತು ಸಲಹೆ.")],
        [L("Where next", "ಮುಂದೆ ಎಲ್ಲಿ"), L("The forecast on the map: the units likely to see the most cases, each with a range.", "ನಕ್ಷೆಯಲ್ಲಿ ಮುನ್ಸೂಚನೆ: ಹೆಚ್ಚು ಪ್ರಕರಣ ಸಾಧ್ಯತೆಯ ಘಟಕಗಳು, ವ್ಯಾಪ್ತಿಯೊಂದಿಗೆ.")],
        [L("Confirmed hotspot", "ಖಚಿತ ಹಾಟ್‌ಸ್ಪಾಟ್"), L("An area with clearly more cases than its neighbours, by a margin unlikely to be chance.", "ನೆರೆಯವುಗಳಿಗಿಂತ ಸ್ಪಷ್ಟವಾಗಿ ಹೆಚ್ಚು ಪ್ರಕರಣ, ಆಕಸ್ಮಿಕವಲ್ಲ.")],
      ] },
      { h: L("On the map", "ನಕ್ಷೆಯ ಮೇಲೆ"), items: [
        [L("Agents", "ಏಜೆಂಟ್‌ಗಳು"), L("Open Agents and drag one onto a district; it runs there for the selected date.", "Agents ತೆರೆದು ಒಂದನ್ನು ಜಿಲ್ಲೆಯ ಮೇಲೆ ಎಳೆಯಿರಿ; ಆಯ್ದ ದಿನಾಂಕಕ್ಕೆ ಅಲ್ಲಿ ನಡೆಯುತ್ತದೆ.")],
        [L("Dots and shading", "ಚುಕ್ಕೆ ಮತ್ತು ಬಣ್ಣ"), L("Each dot is one FIR; darker shading means more FIRs in the district.", "ಪ್ರತಿ ಚುಕ್ಕೆ ಒಂದು FIR; ಗಾಢ ಬಣ್ಣ ಎಂದರೆ ಜಿಲ್ಲೆಯಲ್ಲಿ ಹೆಚ್ಚು FIR.")],
        [L("Methodology & Exclusions", "ವಿಧಾನ ಮತ್ತು ಹೊರಗಿಡುವಿಕೆ"), L("At the foot of the left column: how points are placed and which records are left out.", "ಎಡ ಕಾಲಮ್ ಕೆಳಗೆ: ಚುಕ್ಕೆಗಳನ್ನು ಹೇಗೆ ಇಡಲಾಗಿದೆ, ಯಾವ ದಾಖಲೆ ಹೊರಗಿಡಲಾಗಿದೆ.")],
      ] },
    ],
    tip: L("Pick a district, switch to 28 days, then open Where next.", "ಜಿಲ್ಲೆ ಆರಿಸಿ, 28 ದಿನಕ್ಕೆ ಬದಲಿಸಿ, ನಂತರ ಮುಂದೆ ಎಲ್ಲಿ ತೆರೆಯಿರಿ."),
  },

  search: {
    title: L("Search Guide", "ಹುಡುಕಾಟ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Find a person in the FIR register by name, alias, father's name, phone or vehicle plate, even misspelt, and open their record.",
            "ಹೆಸರು, ಅಡ್ಡಹೆಸರು, ತಂದೆಯ ಹೆಸರು, ಫೋನ್ ಅಥವಾ ವಾಹನ ಸಂಖ್ಯೆಯಿಂದ FIR ದಾಖಲೆಯಲ್ಲಿ ವ್ಯಕ್ತಿಯನ್ನು ಹುಡುಕಿ, ಕಾಗುಣಿತ ತಪ್ಪಿದ್ದರೂ, ಮತ್ತು ಅವರ ದಾಖಲೆ ತೆರೆಯಿರಿ."),
    blocks: [
      { h: L("Searching", "ಹುಡುಕುವುದು"), items: [
        [L("The box", "ಪೆಟ್ಟಿಗೆ"), L("Type, or press the mic and say the name. Close spellings and sound-alike names match too.", "ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ಮೈಕ್ ಒತ್ತಿ ಹೆಸರು ಹೇಳಿ. ಹತ್ತಿರದ ಕಾಗುಣಿತ ಮತ್ತು ಒಂದೇ ಉಚ್ಚಾರದ ಹೆಸರುಗಳೂ ಹೊಂದುತ್ತವೆ.")],
        [L("All · Name · Alias · Father · Phone", "ಎಲ್ಲಾ · ಹೆಸರು · ಅಡ್ಡಹೆಸರು · ತಂದೆ · ಫೋನ್"), L("Limit the search to one field.", "ಹುಡುಕಾಟವನ್ನು ಒಂದು ಕ್ಷೇತ್ರಕ್ಕೆ ಸೀಮಿತಗೊಳಿಸಿ.")],
        [L("Results", "ಫಲಿತಾಂಶಗಳು"), L("Sorted by risk. Each row shows the alias, ID, area, risk tier and FIR count.", "ಅಪಾಯದ ಪ್ರಕಾರ. ಪ್ರತಿ ಸಾಲು ಅಡ್ಡಹೆಸರು, ID, ಪ್ರದೇಶ, ಅಪಾಯ, FIR ಸಂಖ್ಯೆ ತೋರಿಸುತ್ತದೆ.")],
        [L("No match", "ಹೊಂದಿಕೆ ಇಲ್ಲ"), L("Try fewer letters or an alias. A name that is not on record can be tracked as an unknown lead.", "ಕಡಿಮೆ ಅಕ್ಷರ ಅಥವಾ ಅಡ್ಡಹೆಸರು ಪ್ರಯತ್ನಿಸಿ. ದಾಖಲೆಯಲ್ಲಿಲ್ಲದ ಹೆಸರನ್ನು ಅಜ್ಞಾತ ಸುಳಿವಾಗಿ ಟ್ರ್ಯಾಕ್ ಮಾಡಬಹುದು.")],
      ] },
      { h: L("The record", "ದಾಖಲೆ"), items: [
        [L("Risk score", "ಅಪಾಯ ಅಂಕ"), L("Out of 100, from how recent, how frequent and how serious their cases are, and their links. Why this risk score shows each part.", "100 ರಲ್ಲಿ, ಪ್ರಕರಣಗಳು ಎಷ್ಟು ಇತ್ತೀಚಿನವು, ಎಷ್ಟು ಬಾರಿ, ಎಷ್ಟು ಗಂಭೀರ, ಮತ್ತು ಸಂಪರ್ಕಗಳಿಂದ. ಪ್ರತಿ ಭಾಗ 'ಏಕೆ ಈ ಅಂಕ' ದಲ್ಲಿ.")],
        [L("Key figures", "ಮುಖ್ಯ ಅಂಕಿಗಳು"), L("Linked cases, days since the last FIR, associates and prior counts.", "ಸಂಬಂಧಿತ ಪ್ರಕರಣ, ಕೊನೆಯ FIR ನಿಂದ ದಿನ, ಸಹಚರರು, ಹಿಂದಿನ ಪ್ರಕರಣ.")],
        [L("Numbered sections", "ಸಂಖ್ಯೆಯ ವಿಭಾಗಗಳು"), L("Record details, why this risk score, how they operate, recommended next steps, known associates, similar past cases.", "ದಾಖಲೆ ವಿವರ, ಏಕೆ ಈ ಅಂಕ, ಕಾರ್ಯವಿಧಾನ, ಮುಂದಿನ ಹೆಜ್ಜೆ, ಸಹಚರರು, ಹೋಲುವ ಪ್ರಕರಣಗಳು.")],
        [L("Actions", "ಕ್ರಮಗಳು"), L("Show in Brain, Ask Antar, Map, and Watchlist. A watchlist request needs a supervising officer's approval.", "ಬ್ರೈನ್‌ನಲ್ಲಿ, Antar ಕೇಳಿ, ನಕ್ಷೆ, ವೀಕ್ಷಣಾ ಪಟ್ಟಿ. ವೀಕ್ಷಣಾ ಪಟ್ಟಿಗೆ ಮೇಲ್ವಿಚಾರಕರ ಅನುಮೋದನೆ ಬೇಕು.")],
        [L("Identity hypotheses", "ಗುರುತಿನ ಊಹೆಗಳು"), L("When two records may be the same person, an Inspector or above can confirm or reject it.", "ಎರಡು ದಾಖಲೆ ಒಂದೇ ವ್ಯಕ್ತಿ ಇರಬಹುದಾದಾಗ, ಇನ್ಸ್‌ಪೆಕ್ಟರ್ ಅಥವಾ ಮೇಲಿನವರು ದೃಢೀಕರಿಸಬಹುದು ಅಥವಾ ತಿರಸ್ಕರಿಸಬಹುದು.")],
      ] },
      { h: L("Open-source checks (OSINT)", "ಮುಕ್ತ ಮೂಲ ಪರಿಶೀಲನೆ (OSINT)"), items: [
        [L("What you can check", "ಏನನ್ನು ಪರಿಶೀಲಿಸಬಹುದು"), L("A phone, UPI ID, vehicle number, bank account or IFSC, IMEI, website, email, username or name. Only the identifier leaves Antar.", "ಫೋನ್, UPI, ವಾಹನ ಸಂಖ್ಯೆ, ಬ್ಯಾಂಕ್ ಖಾತೆ/IFSC, IMEI, ವೆಬ್‌ಸೈಟ್, ಇಮೇಲ್, ಬಳಕೆದಾರ ಹೆಸರು ಅಥವಾ ಹೆಸರು. ಗುರುತು ಮಾತ್ರ ಹೊರಹೋಗುತ್ತದೆ.")],
        [L("Only real mentions", "ನೈಜ ಉಲ್ಲೇಖಗಳು ಮಾತ್ರ"), L("A page is kept only if it actually contains what you searched. Everything found is unverified.", "ನೀವು ಹುಡುಕಿದ್ದನ್ನು ನಿಜವಾಗಿ ಹೊಂದಿರುವ ಪುಟ ಮಾತ್ರ. ಸಿಕ್ಕಿದ್ದೆಲ್ಲವೂ ಪರಿಶೀಲಿಸಿಲ್ಲ.")],
        [L("Checks and notices", "ಪರಿಶೀಲನೆ ಮತ್ತು ನೋಟಿಸ್"), L("Live checks (IFSC branch, website age, IMEI), the official portals to check next, and a drafted notice to whoever holds the records.", "ನೇರ ಪರಿಶೀಲನೆ, ಮುಂದಿನ ಅಧಿಕೃತ ಪೋರ್ಟಲ್‌ಗಳು, ಮತ್ತು ದಾಖಲೆ ಹೊಂದಿರುವವರಿಗೆ ಕರಡು ನೋಟಿಸ್.")],
      ] },
    ],
    examples: { en: ["Yelappa", "KA-05-EZ-7878"], kn: ["Yelappa", "KA-05-EZ-7878"] },
  },

  trace: {
    title: L("Observability & Trace Guide", "ವೀಕ್ಷಣೆ ಮತ್ತು ಜಾಡು ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Every question asked in Antar, the query that ran, the FIR rows it read and the checks it passed. For supervisors and auditors checking an answer before it goes into a case file.",
            "ಅಂತರದಲ್ಲಿ ಕೇಳಿದ ಪ್ರತಿ ಪ್ರಶ್ನೆ, ಚಾಲನೆಯಾದ ಪ್ರಶ್ನಾವಳಿ, ಓದಿದ FIR ಸಾಲುಗಳು ಮತ್ತು ಪಾಸಾದ ಪರಿಶೀಲನೆಗಳು. ಉತ್ತರ ಪ್ರಕರಣ ಕಡತಕ್ಕೆ ಸೇರುವ ಮೊದಲು ಪರಿಶೀಲಿಸುವ ಮೇಲ್ವಿಚಾರಕರಿಗೆ."),
    blocks: [
      { h: L("The figures", "ಅಂಕಿಗಳು"), items: [
        [L("Questions · no flag", "ಪ್ರಶ್ನೆಗಳು · ಫ್ಲ್ಯಾಗ್ ಇಲ್ಲ"), L("How many questions were recorded, and the share answered with no flag.", "ಎಷ್ಟು ಪ್ರಶ್ನೆ ದಾಖಲಾಗಿವೆ, ಮತ್ತು ಫ್ಲ್ಯಾಗ್ ಇಲ್ಲದೆ ಉತ್ತರಿಸಿದ ಪಾಲು.")],
        [L("Serious flags", "ಗಂಭೀರ ಫ್ಲ್ಯಾಗ್"), L("High-severity rule breaks. Review these first.", "ಹೆಚ್ಚಿನ ತೀವ್ರತೆಯ ನಿಯಮ ಉಲ್ಲಂಘನೆ. ಮೊದಲು ಇವನ್ನು ಪರಿಶೀಲಿಸಿ.")],
        [L("Answer time · FIRs cited", "ಸಮಯ · ಉಲ್ಲೇಖಿತ FIR"), L("Average time and the time 95% are answered within; FIRs cited and rows read.", "ಸರಾಸರಿ ಸಮಯ ಮತ್ತು 95% ಉತ್ತರಿಸುವ ಸಮಯ; ಉಲ್ಲೇಖಿತ FIR ಮತ್ತು ಓದಿದ ಸಾಲುಗಳು.")],
        [L("Quality · how written", "ಗುಣಮಟ್ಟ · ಹೇಗೆ ಬರೆಯಲಾಗಿದೆ"), L("The reviewer's score when answers have been scored, and how many were written by the AI model or from the records alone.", "ಅಂಕ ನೀಡಿದ್ದರೆ ಗುಣಮಟ್ಟ, ಮತ್ತು ಎಷ್ಟು AI ಮಾದರಿಯಿಂದ ಅಥವಾ ದಾಖಲೆಗಳಿಂದ ಮಾತ್ರ ಬರೆಯಲಾಗಿದೆ.")],
      ] },
      { h: L("Flags and the ledger", "ಫ್ಲ್ಯಾಗ್ ಮತ್ತು ಲೆಡ್ಜರ್"), items: [
        [L("Flags raised", "ಫ್ಲ್ಯಾಗ್‌ಗಳು"), L("Each rule (F1, F5, F6…) with what it means and how many answers it caught. What each flag means is in the explainer.", "ಪ್ರತಿ ನಿಯಮ (F1, F5, F6…), ಅದರ ಅರ್ಥ ಮತ್ತು ಎಷ್ಟು ಉತ್ತರ ಹಿಡಿಯಿತು.")],
        [L("Audit ledger", "ಆಡಿಟ್ ಲೆಡ್ಜರ್"), L("Says whether every logged entry is unaltered. A break names the entry where it fails.", "ಪ್ರತಿ ದಾಖಲಾದ ನಮೂದು ಬದಲಾಗಿಲ್ಲವೇ ಎಂದು ಹೇಳುತ್ತದೆ. ಮುರಿದರೆ ಎಲ್ಲಿ ಎಂದು ಹೇಳುತ್ತದೆ.")],
        [L("What this page records, and why", "ಈ ಪುಟ ಏನು, ಏಕೆ"), L("Opens the explainer: what is recorded, why it matters, and the checks.", "ವಿವರಣೆ ತೆರೆಯುತ್ತದೆ: ಏನು ದಾಖಲಾಗುತ್ತದೆ, ಏಕೆ ಮುಖ್ಯ, ಪರಿಶೀಲನೆಗಳು.")],
      ] },
      { h: L("Finding an answer", "ಉತ್ತರ ಹುಡುಕುವುದು"), items: [
        [L("Review the flags", "ಫ್ಲ್ಯಾಗ್ ಪರಿಶೀಲಿಸಿ"), L("The solid button turns on Flagged only and takes you to the list.", "ಘನ ಬಟನ್ Flagged only ಆನ್ ಮಾಡಿ ಪಟ್ಟಿಗೆ ಕರೆದೊಯ್ಯುತ್ತದೆ.")],
        [L("Flagged only · page requests · Refresh", "ಫ್ಲ್ಯಾಗ್ ಮಾತ್ರ · ಪುಟ ವಿನಂತಿ · ರಿಫ್ರೆಶ್"), L("Narrow to flagged answers, include requests made by the pages, or read the latest figures.", "ಫ್ಲ್ಯಾಗ್ ಉತ್ತರಗಳಿಗೆ ಸೀಮಿತ, ಪುಟ ವಿನಂತಿಗಳನ್ನು ಸೇರಿಸಿ, ಅಥವಾ ಇತ್ತೀಚಿನ ಅಂಕಿ ಓದಿ.")],
        [L("01 Sessions · 02 Questions", "01 ಸೆಷನ್ · 02 ಪ್ರಶ್ನೆ"), L("Pick a session to replay it in order, or search questions and answers.", "ಕ್ರಮವಾಗಿ ಮರುಪ್ಲೇ ಮಾಡಲು ಸೆಷನ್ ಆರಿಸಿ, ಅಥವಾ ಪ್ರಶ್ನೆ-ಉತ್ತರ ಹುಡುಕಿ.")],
        [L("Each question", "ಪ್ರತಿ ಪ್ರಶ್ನೆ"), L("Open it for the template that ran, the agents and their timing, and the FIR rows it read.", "ಚಾಲನೆಯಾದ ಟೆಂಪ್ಲೇಟ್, ಏಜೆಂಟ್‌ಗಳು ಮತ್ತು ಸಮಯ, ಮತ್ತು ಓದಿದ FIR ಸಾಲುಗಳಿಗೆ ತೆರೆಯಿರಿ.")],
      ] },
    ],
  },

  approvals: {
    title: L("Approvals Guide", "ಅನುಮೋದನೆ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Patrol redeployments and watchlist additions wait here until a second, supervising officer approves them. Nothing on this list happens on its own.",
            "ಗಸ್ತು ಮರುನಿಯೋಜನೆ ಮತ್ತು ವೀಕ್ಷಣಾ ಪಟ್ಟಿ ಸೇರ್ಪಡೆ, ಎರಡನೇ ಮೇಲ್ವಿಚಾರಕ ಅಧಿಕಾರಿ ಅನುಮೋದಿಸುವವರೆಗೆ ಇಲ್ಲಿ ಕಾಯುತ್ತವೆ. ಈ ಪಟ್ಟಿಯಲ್ಲಿ ಯಾವುದೂ ತಾನಾಗಿ ಜಾರಿಯಾಗುವುದಿಲ್ಲ."),
    blocks: [
      { h: L("The rule", "ನಿಯಮ"), items: [
        [L("Two officers", "ಇಬ್ಬರು ಅಧಿಕಾರಿಗಳು"), L("One officer asks, a different supervising officer decides. Nobody can approve their own request.", "ಒಬ್ಬರು ಕೇಳುತ್ತಾರೆ, ಬೇರೊಬ್ಬ ಮೇಲ್ವಿಚಾರಕರು ನಿರ್ಧರಿಸುತ್ತಾರೆ. ತಮ್ಮ ವಿನಂತಿಯನ್ನು ಯಾರೂ ಅನುಮೋದಿಸಲಾಗದು.")],
        [L("Signing in to decide", "ನಿರ್ಧರಿಸಲು ಸೈನ್ ಇನ್"), L("A supervising officer enters their ID and password in the panel at the top.", "ಮೇಲ್ವಿಚಾರಕರು ಮೇಲಿನ ಫಲಕದಲ್ಲಿ ID ಮತ್ತು ಪಾಸ್‌ವರ್ಡ್ ನಮೂದಿಸುತ್ತಾರೆ.")],
        [L("Expiry", "ಅವಧಿ"), L("A request left too long expires and cannot be approved; the time left shows on each one.", "ತುಂಬಾ ಕಾಲ ಬಿಟ್ಟ ವಿನಂತಿ ಅವಧಿ ಮುಗಿದು ಅನುಮೋದಿಸಲಾಗದು; ಉಳಿದ ಸಮಯ ಪ್ರತಿಯೊಂದರಲ್ಲೂ.")],
      ] },
      { h: L("Reading a request", "ವಿನಂತಿ ಓದುವುದು"), items: [
        [L("The fact line", "ಮಾಹಿತಿ ಸಾಲು"), L("Risk, the kind of action, whether it is unaltered since it was filed, the misuse check, and its ID.", "ಅಪಾಯ, ಕ್ರಮದ ಪ್ರಕಾರ, ಸಲ್ಲಿಸಿದ ನಂತರ ಬದಲಾಗಿಲ್ಲವೇ, ದುರ್ಬಳಕೆ ಪರಿಶೀಲನೆ, ಮತ್ತು ID.")],
        [L("Justification · What will happen", "ಸಮರ್ಥನೆ · ಏನಾಗುತ್ತದೆ"), L("Why it was asked for, and exactly what runs if it is approved.", "ಏಕೆ ಕೇಳಲಾಗಿದೆ, ಮತ್ತು ಅನುಮೋದಿಸಿದರೆ ನಿಖರವಾಗಿ ಏನಾಗುತ್ತದೆ.")],
        [L("Evidence and flags", "ಸಾಕ್ಷ್ಯ ಮತ್ತು ಫ್ಲ್ಯಾಗ್"), L("The figures behind it, and any warning from the misuse check.", "ಹಿಂದಿನ ಅಂಕಿಗಳು, ಮತ್ತು ದುರ್ಬಳಕೆ ಪರಿಶೀಲನೆಯ ಎಚ್ಚರಿಕೆ.")],
      ] },
      { h: L("Deciding", "ನಿರ್ಧರಿಸುವುದು"), items: [
        [L("Write a reason", "ಕಾರಣ ಬರೆಯಿರಿ"), L("At least a short sentence. It is recorded with the decision.", "ಕನಿಷ್ಠ ಒಂದು ಚಿಕ್ಕ ವಾಕ್ಯ. ನಿರ್ಧಾರದೊಂದಿಗೆ ದಾಖಲಾಗುತ್ತದೆ.")],
        [L("Approve & execute · Reject", "ಅನುಮೋದಿಸಿ · ತಿರಸ್ಕರಿಸಿ"), L("Approve runs the action; Reject closes it. A request that was altered cannot be approved.", "ಅನುಮೋದನೆ ಕ್ರಮ ನಡೆಸುತ್ತದೆ; ತಿರಸ್ಕಾರ ಮುಚ್ಚುತ್ತದೆ. ಬದಲಾದ ವಿನಂತಿ ಅನುಮೋದಿಸಲಾಗದು.")],
        [L("Withdraw", "ಹಿಂಪಡೆಯಿರಿ"), L("The officer who asked can withdraw it, with a reason.", "ಕೇಳಿದ ಅಧಿಕಾರಿ ಕಾರಣ ಸಹಿತ ಹಿಂಪಡೆಯಬಹುದು.")],
        [L("History", "ಇತಿಹಾಸ"), L("Approved, rejected, withdrawn and expired requests, with who decided and why.", "ಅನುಮೋದಿತ, ತಿರಸ್ಕೃತ, ಹಿಂಪಡೆದ, ಅವಧಿ ಮುಗಿದವು, ಯಾರು ಮತ್ತು ಏಕೆ ಎಂಬುದರೊಂದಿಗೆ.")],
      ] },
    ],
  },

  account: {
    title: L("Account Guide", "ಖಾತೆ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Your shift brief, alerts, settings and records in one place. Each part opens with what it is for and the next step.",
            "ನಿಮ್ಮ ಶಿಫ್ಟ್ ಬ್ರೀಫ್, ಎಚ್ಚರಿಕೆಗಳು, ಸೆಟ್ಟಿಂಗ್‌ಗಳು ಮತ್ತು ದಾಖಲೆಗಳು ಒಂದೇ ಕಡೆ. ಪ್ರತಿ ಭಾಗವೂ ಅದರ ಉದ್ದೇಶ ಮತ್ತು ಮುಂದಿನ ಹೆಜ್ಜೆಯಿಂದ ಆರಂಭವಾಗುತ್ತದೆ."),
    blocks: [
      { h: L("Your work", "ನಿಮ್ಮ ಕೆಲಸ"), items: [
        [L("01 Shift Brief", "01 ಶಿಫ್ಟ್ ಬ್ರೀಫ್"), L("The last 8 to 48 hours for a district: a summary, the figures, priority actions and key incidents.", "ಜಿಲ್ಲೆಗೆ ಕಳೆದ 8 ರಿಂದ 48 ಗಂಟೆ: ಸಾರಾಂಶ, ಅಂಕಿಗಳು, ಆದ್ಯತಾ ಕ್ರಮಗಳು, ಪ್ರಮುಖ ಘಟನೆಗಳು.")],
        [L("02 Approvals", "02 ಅನುಮೋದನೆಗಳು"), L("Requests waiting for a second officer.", "ಎರಡನೇ ಅಧಿಕಾರಿಗಾಗಿ ಕಾಯುತ್ತಿರುವ ವಿನಂತಿಗಳು.")],
        [L("03 Antar Alerts", "03 ಅಂತರ ಎಚ್ಚರಿಕೆಗಳು"), L("Corridor, pattern and person watches that fired, each with a suggested step and a link. Acknowledge once someone is on it.", "ಮಾರ್ಗ, ಮಾದರಿ, ವ್ಯಕ್ತಿ ಕಣ್ಗಾವಲು ಎಚ್ಚರಿಕೆಗಳು, ಸಲಹೆ ಮತ್ತು ಲಿಂಕ್‌ನೊಂದಿಗೆ. ಕ್ರಮದ ನಂತರ ಸ್ವೀಕರಿಸಿ.")],
      ] },
      { h: L("Settings", "ಸೆಟ್ಟಿಂಗ್‌ಗಳು"), items: [
        [L("Preferences", "ಆದ್ಯತೆಗಳು"), L("Language, first screen, map view, date format and display name. Save to keep them.", "ಭಾಷೆ, ಮೊದಲ ಪರದೆ, ನಕ್ಷೆ ನೋಟ, ದಿನಾಂಕ ಸ್ವರೂಪ, ಪ್ರದರ್ಶನ ಹೆಸರು. ಉಳಿಸಿ.")],
        [L("Misuse Checks", "ದುರ್ಬಳಕೆ ತಪಾಸಣೆ"), L("The safeguards: evidence hashing, no automatic identity merge, location-only profiling of unknown suspects.", "ರಕ್ಷಣೆಗಳು: ಸಾಕ್ಷ್ಯ ಹ್ಯಾಶಿಂಗ್, ಸ್ವಯಂ ಗುರುತು ವಿಲೀನ ಇಲ್ಲ, ಅಪರಿಚಿತರಿಗೆ ಸ್ಥಳ-ಮಾತ್ರ ವಿಶ್ಲೇಷಣೆ.")],
        [L("Notifications · Security", "ಅಧಿಸೂಚನೆ · ಭದ್ರತೆ"), L("What Antar tells you about; your password and the devices signed in as you.", "ಅಂತರ ಏನು ತಿಳಿಸುತ್ತದೆ; ನಿಮ್ಮ ಪಾಸ್‌ವರ್ಡ್ ಮತ್ತು ಸೈನ್ ಇನ್ ಆದ ಸಾಧನಗಳು.")],
      ] },
      { h: L("Records", "ದಾಖಲೆಗಳು"), items: [
        [L("Observability & Trace", "ವೀಕ್ಷಣೆ ಮತ್ತು ಜಾಡು"), L("How every answer was produced.", "ಪ್ರತಿ ಉತ್ತರ ಹೇಗೆ ತಯಾರಾಯಿತು.")],
        [L("Activity Log", "ಚಟುವಟಿಕೆ ಲಾಗ್"), L("Every search, answer and approval under your ID, from the audit record.", "ನಿಮ್ಮ ID ಯಲ್ಲಿನ ಪ್ರತಿ ಹುಡುಕಾಟ, ಉತ್ತರ, ಅನುಮೋದನೆ.")],
        [L("Export Centre · Admin", "ರಫ್ತು · ನಿರ್ವಾಹಕ"), L("Reports to download; loading new FIR data (admins only, preview).", "ಡೌನ್‌ಲೋಡ್ ವರದಿಗಳು; ಹೊಸ FIR ದತ್ತಾಂಶ (ನಿರ್ವಾಹಕರಿಗೆ ಮಾತ್ರ).")],
      ] },
    ],
  },

  network: {
    title: L("Network Guide", "ಜಾಲ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Starting from one suspect, the graph shows every recorded link up to two steps away (up to 150 people).",
            "ಒಬ್ಬ ಶಂಕಿತನಿಂದ ಆರಂಭಿಸಿ, ಎರಡು ಹಂತದವರೆಗಿನ (150 ಜನರವರೆಗೆ) ದಾಖಲಾದ ಎಲ್ಲಾ ಸಂಪರ್ಕಗಳನ್ನು ಗ್ರಾಫ್ ತೋರಿಸುತ್ತದೆ."),
    blocks: [
      { h: L("Who matters", "ಯಾರು ಮುಖ್ಯ"), items: [
        [L("Influence", "ಪ್ರಭಾವ"), L("The bigger the circle, the more people this person is linked to.", "ವೃತ್ತ ದೊಡ್ಡದಾದಷ್ಟು ಆ ವ್ಯಕ್ತಿ ಹೆಚ್ಚು ಜನರೊಂದಿಗೆ ಸಂಪರ್ಕ ಹೊಂದಿದ್ದಾರೆ.")],
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
        [L("Trend or unusual rise", "ಪ್ರವೃತ್ತಿ ಅಥವಾ ಅಸಾಮಾನ್ಯ ಏರಿಕೆ"), L("A rising line is background. To see whether a rise is unusual, open Predict.", "ಏರುವ ರೇಖೆ ಹಿನ್ನೆಲೆ ಮಾತ್ರ. ಏರಿಕೆ ಅಸಾಮಾನ್ಯವೇ ಎಂದು ತಿಳಿಯಲು Predict ತೆರೆಯಿರಿ.")],
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
        [L("Monitored", "ನಿಗಾವಹಿಸಲಾಗಿದೆ"), L("The misuse check stops any search that picks suspects by caste, religion or community.", "ಜಾತಿ, ಧರ್ಮ ಅಥವಾ ಸಮುದಾಯದ ಆಧಾರದ ಮೇಲೆ ಶಂಕಿತರನ್ನು ಹುಡುಕುವ ಪ್ರಶ್ನೆಯನ್ನು ದುರ್ಬಳಕೆ ತಪಾಸಣೆ ತಡೆಯುತ್ತದೆ.")],
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
        [L("Account", "ಖಾತೆ"), L("Your shift brief, alerts, approvals, settings and records.", "ನಿಮ್ಮ ಶಿಫ್ಟ್ ಬ್ರೀಫ್, ಎಚ್ಚರಿಕೆ, ಅನುಮೋದನೆ, ಸೆಟ್ಟಿಂಗ್ ಮತ್ತು ದಾಖಲೆಗಳು.")],
      ] },
    ],
  },
};

function pickGuide(path, expertOn) {
  if (!path) return "general";
  if (path.startsWith("/antarBrain")) return "brain";
  if (path.startsWith("/antar")) return expertOn ? "expert" : "chat";
  for (const key of ["predict", "map", "search", "trace", "approvals", "account", "network", "trends", "profiles", "social"]) {
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

  // About and Docs explain themselves; every working screen, Account included, has a guide.
  if (path && (path.startsWith("/about") || path.startsWith("/docs"))) return null;

  // The Expert console has no guide of its own yet: it is the chat screen with more shown,
  // so the chat guide stands in. Without a fallback, a missing key crashed the page.
  const picked = pickGuide(path, expertOn);
  const g = GUIDES[picked] || (picked === "expert" ? GUIDES.chat : GUIDES.general);
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
