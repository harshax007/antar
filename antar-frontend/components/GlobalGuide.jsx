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
    lead: L("Where crime is likely to rise in the next 7 days, area by area, so patrols and bandobast can be planned before the cases come in. Read it top to bottom: the week's plan first, then the forecast behind it.",
            "ಮುಂದಿನ 7 ದಿನಗಳಲ್ಲಿ ಎಲ್ಲಿ ಅಪರಾಧ ಹೆಚ್ಚಾಗಬಹುದು, ಪ್ರದೇಶವಾರು - ಪ್ರಕರಣಗಳು ಬರುವ ಮೊದಲೇ ಗಸ್ತು ಮತ್ತು ಬಂದೋಬಸ್ತ್ ಯೋಜಿಸಲು. ಮೇಲಿನಿಂದ ಕೆಳಗೆ ಓದಿ: ಮೊದಲು ವಾರದ ಯೋಜನೆ, ನಂತರ ಅದರ ಹಿಂದಿನ ಮುನ್ಸೂಚನೆ."),
    blocks: [
      { h: L("The top of the page", "ಪುಟದ ಮೇಲ್ಭಾಗ"), items: [
        [L("See this week's plan", "ಈ ವಾರದ ಯೋಜನೆ ನೋಡಿ"), L("Jumps to 01, the actions for this week. How it works opens this guide.", "01 ಕ್ಕೆ, ಈ ವಾರದ ಕ್ರಮಗಳಿಗೆ ಹೋಗುತ್ತದೆ. “ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ” ಈ ಮಾರ್ಗದರ್ಶಿಯನ್ನು ತೆರೆಯುತ್ತದೆ.")],
        [L("The line under it", "ಅದರ ಕೆಳಗಿನ ಸಾಲು"), L("How many areas (and statewide units) are forecast, and “Range held in N% of tested weeks”: how often the real count fell inside the range on past weeks. Click it for the details.", "ಎಷ್ಟು ಪ್ರದೇಶಗಳು (ಮತ್ತು ರಾಜ್ಯಮಟ್ಟದ ಘಟಕಗಳು), ಮತ್ತು ಹಿಂದಿನ ವಾರಗಳಲ್ಲಿ ನಿಜವಾದ ಎಣಿಕೆ ವ್ಯಾಪ್ತಿಯೊಳಗೆ ಎಷ್ಟು ಬಾರಿ ಬಿತ್ತು. ವಿವರಕ್ಕೆ ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("The five figures", "ಐದು ಅಂಕಿಗಳು"), L("High-risk areas, Above normal, Reporting drops, Active alerts, Events in 3 weeks. Anything but zero needs a look: click it and the list below opens on just those.", "ಹೆಚ್ಚು ಅಪಾಯ, ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು, ವರದಿ ಇಳಿಕೆ, ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆ, 3 ವಾರಗಳಲ್ಲಿ ಉತ್ಸವ. ಸೊನ್ನೆ ಅಲ್ಲದ್ದನ್ನು ಗಮನಿಸಿ: ಕ್ಲಿಕ್ ಮಾಡಿದರೆ ಕೆಳಗಿನ ಪಟ್ಟಿ ಅವುಗಳನ್ನೇ ತೋರಿಸುತ್ತದೆ.")],
      ] },
      { h: L("01 · This week's plan", "01 · ಈ ವಾರದ ಯೋಜನೆ"), items: [
        [L("Up to four actions", "ನಾಲ್ಕು ಕ್ರಮಗಳವರೆಗೆ"), L("Strongest first: where to add beat visits, which station to check for a drop in reporting, which event to plan bandobast for. Open a line for the reason and the stations.", "ಮುಖ್ಯವಾದದ್ದು ಮೊದಲು: ಎಲ್ಲಿ ಹೆಚ್ಚು ಬೀಟ್ ಭೇಟಿ, ವರದಿ ಇಳಿಕೆಗೆ ಯಾವ ಠಾಣೆ ಪರಿಶೀಲಿಸಬೇಕು, ಯಾವ ಉತ್ಸವಕ್ಕೆ ಬಂದೋಬಸ್ತ್. ಕಾರಣ ಮತ್ತು ಠಾಣೆಗಳಿಗೆ ಸಾಲು ತೆರೆಯಿರಿ.")],
        [L("Copy for the briefing note", "ಬ್ರೀಫಿಂಗ್ ಟಿಪ್ಪಣಿ ನಕಲಿಸಿ"), L("The whole week as plain text, ready to paste into a roll-call or briefing note.", "ಇಡೀ ವಾರ ಸರಳ ಪಠ್ಯವಾಗಿ, ರೋಲ್-ಕಾಲ್ ಅಥವಾ ಬ್ರೀಫಿಂಗ್ ಟಿಪ್ಪಣಿಗೆ ಅಂಟಿಸಲು ಸಿದ್ಧ.")],
      ] },
      { h: L("02 · Forecast for the next 7 days", "02 · ಮುಂದಿನ 7 ದಿನಗಳ ಮುನ್ಸೂಚನೆ"), items: [
        [L("One card per area", "ಪ್ರತಿ ಪ್ರದೇಶಕ್ಕೆ ಒಂದು ಕಾರ್ಡ್"), L("The crime most likely to move there, the cases expected in the next 7 days as a range, rise or drop, and how confident the forecast is.", "ಅಲ್ಲಿ ಹೆಚ್ಚು ಬದಲಾಗಬಹುದಾದ ಅಪರಾಧ, ಮುಂದಿನ 7 ದಿನಗಳ ನಿರೀಕ್ಷಿತ ಪ್ರಕರಣಗಳ ವ್ಯಾಪ್ತಿ, ಏರಿಕೆ ಅಥವಾ ಇಳಿಕೆ, ಮತ್ತು ಮುನ್ಸೂಚನೆಯ ವಿಶ್ವಾಸ.")],
        [L("Filters", "ಫಿಲ್ಟರ್‌ಗಳು"), L("Opens on Needs attention (high risk, above normal, a reporting drop or an event). Also: High risk, All areas, Above normal, Reporting drops, Event this week, High confidence. Or find an area or crime type by name.", "“ಗಮನ ಬೇಕು” ಮೇಲೆ ತೆರೆಯುತ್ತದೆ (ಹೆಚ್ಚು ಅಪಾಯ, ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು, ವರದಿ ಇಳಿಕೆ ಅಥವಾ ಉತ್ಸವ). ಜೊತೆಗೆ: ಹೆಚ್ಚು ಅಪಾಯ, ಎಲ್ಲಾ ಪ್ರದೇಶ, ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು, ವರದಿ ಇಳಿಕೆ, ಈ ವಾರ ಉತ್ಸವ, ಹೆಚ್ಚು ವಿಶ್ವಾಸ. ಅಥವಾ ಪ್ರದೇಶ/ಅಪರಾಧವನ್ನು ಹೆಸರಿನಿಂದ ಹುಡುಕಿ.")],
        [L("Above normal", "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು"), L("The unusual-activity score is 2 or more: recent cases sit well above the area's usual level. 2 is unusual, 4 is rare.", "ಅಸಾಮಾನ್ಯತೆ ಅಂಕ 2 ಅಥವಾ ಹೆಚ್ಚು: ಇತ್ತೀಚಿನ ಪ್ರಕರಣಗಳು ಸಾಮಾನ್ಯ ಮಟ್ಟಕ್ಕಿಂತ ತುಂಬಾ ಹೆಚ್ಚು. 2 ಅಸಾಮಾನ್ಯ, 4 ಅಪರೂಪ.")],
        [L("Reporting drop", "ವರದಿ ಇಳಿಕೆ"), L("Far fewer FIRs than usual. Often slower registration, not less crime: check the station.", "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ತುಂಬಾ ಕಡಿಮೆ FIR. ಹೆಚ್ಚಾಗಿ ತಡವಾದ ದಾಖಲಾತಿ, ಕಡಿಮೆ ಅಪರಾಧ ಅಲ್ಲ: ಠಾಣೆ ಪರಿಶೀಲಿಸಿ.")],
        [L("Statewide units", "ರಾಜ್ಯಮಟ್ಟದ ಘಟಕಗಳು"), L("Units like CID or Railways register FIRs across the state. They are listed apart, not ranked with areas.", "CID, ರೈಲ್ವೆ ಮುಂತಾದ ಘಟಕಗಳು ರಾಜ್ಯಾದ್ಯಂತ FIR ದಾಖಲಿಸುತ್ತವೆ. ಪ್ರತ್ಯೇಕವಾಗಿ ಪಟ್ಟಿ, ಪ್ರದೇಶಗಳೊಂದಿಗೆ ಶ್ರೇಣಿ ಇಲ್ಲ.")],
      ] },
      { h: L("Opening a forecast", "ಮುನ್ಸೂಚನೆ ತೆರೆಯುವುದು"), items: [
        [L("Why this forecast", "ಏಕೆ ಈ ಮುನ್ಸೂಚನೆ"), L("Expected in the next 7 days, what the model saw, the case records used, range reliability, direction and any seasonal effect. Show the case records behind this lists the FIRs.", "ಮುಂದಿನ 7 ದಿನಗಳ ನಿರೀಕ್ಷೆ, ಮಾದರಿ ಕಂಡದ್ದು, ಬಳಸಿದ ಪ್ರಕರಣ ದಾಖಲೆಗಳು, ವ್ಯಾಪ್ತಿಯ ವಿಶ್ವಾಸಾರ್ಹತೆ, ದಿಕ್ಕು ಮತ್ತು ಋತುಮಾನ ಪರಿಣಾಮ. ಹಿಂದಿನ ಪ್ರಕರಣ ದಾಖಲೆಗಳನ್ನು ತೆರೆದರೆ FIR ಗಳು ಕಾಣುತ್ತವೆ.")],
        [L("Recommended action", "ಶಿಫಾರಸು ಮಾಡಿದ ಕ್ರಮ"), L("What to do this week and which stations to put it on. Mark as reviewed records that you have read it; Ask Antar takes the question to Chat.", "ಈ ವಾರ ಏನು ಮಾಡಬೇಕು ಮತ್ತು ಯಾವ ಠಾಣೆಗಳಲ್ಲಿ. “ಪರಿಶೀಲಿಸಲಾಗಿದೆ” ನೀವು ಓದಿದ್ದನ್ನು ದಾಖಲಿಸುತ್ತದೆ; “ಅಂತರ್‌ಗೆ ಕೇಳಿ” ಪ್ರಶ್ನೆಯನ್ನು ಚಾಟ್‌ಗೆ ಒಯ್ಯುತ್ತದೆ.")],
        [L("Quiet tools", "ಇತರ ಸಾಧನಗಳು"), L("How this was worked out (step by step), What if (a second range if the area's measured alert carries on; only where there is one), Audit trail, Open on map.", "ಹೇಗೆ ಲೆಕ್ಕ ಹಾಕಲಾಯಿತು (ಹಂತ ಹಂತವಾಗಿ), ಹೀಗಾದರೆ (ಅಳತೆಯಾದ ಎಚ್ಚರಿಕೆ ಮುಂದುವರಿದರೆ ಇನ್ನೊಂದು ವ್ಯಾಪ್ತಿ; ಇದ್ದಲ್ಲಿ ಮಾತ್ರ), ಆಡಿಟ್ ಜಾಡು, ನಕ್ಷೆಯಲ್ಲಿ ತೆರೆಯಿರಿ.")],
      ] },
      { h: L("03 · Active alerts", "03 · ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು"), items: [
        [L("Cases that broke a pattern", "ಮಾದರಿ ಮುರಿದ ಪ್ರಕರಣಗಳು"), L("Recent cases well above an area's usual level for that crime, with the unusual-activity score. Pick one to see why.", "ಆ ಅಪರಾಧಕ್ಕೆ ಪ್ರದೇಶದ ಸಾಮಾನ್ಯ ಮಟ್ಟಕ್ಕಿಂತ ತುಂಬಾ ಹೆಚ್ಚಿನ ಇತ್ತೀಚಿನ ಪ್ರಕರಣಗಳು, ಅಸಾಮಾನ್ಯತೆ ಅಂಕದೊಂದಿಗೆ. ಕಾರಣಕ್ಕೆ ಒಂದನ್ನು ಆರಿಸಿ.")],
      ] },
      { h: L("04 · Events ahead", "04 · ಮುಂಬರುವ ಉತ್ಸವಗಳು"), items: [
        [L("Festivals in the next 3 weeks", "ಮುಂದಿನ 3 ವಾರಗಳ ಉತ್ಸವಗಳು"), L("What each did to registered cases in past years, crime by crime. Copy a bandobast note, or Ask Antar about past years.", "ಹಿಂದಿನ ವರ್ಷಗಳಲ್ಲಿ ಪ್ರತಿಯೊಂದು ದಾಖಲಾದ ಪ್ರಕರಣಗಳ ಮೇಲೆ ಬೀರಿದ ಪರಿಣಾಮ, ಅಪರಾಧವಾರು. ಬಂದೋಬಸ್ತ್ ಟಿಪ್ಪಣಿ ನಕಲಿಸಿ, ಅಥವಾ ಹಿಂದಿನ ವರ್ಷಗಳ ಬಗ್ಗೆ ಅಂತರ್‌ಗೆ ಕೇಳಿ.")],
      ] },
      { h: L("At the bottom, opened on request", "ಕೆಳಭಾಗ, ಕೇಳಿದಾಗ ತೆರೆಯುವುದು"), items: [
        [L("Investigation leads", "ತನಿಖಾ ಸುಳಿವುಗಳು"), L("For the investigating officer. Pick a district in the forecast, then Look for links: possible links between accused, each tested against how many other pairs in the state would look as linked by chance. Confirm or reject each one.", "ತನಿಖಾಧಿಕಾರಿಗೆ. ಮುನ್ಸೂಚನೆಯಲ್ಲಿ ಜಿಲ್ಲೆ ಆರಿಸಿ, ನಂತರ “ಸಂಪರ್ಕ ಹುಡುಕಿ”: ಆರೋಪಿಗಳ ನಡುವಿನ ಸಾಧ್ಯ ಸಂಪರ್ಕಗಳು, ಪ್ರತಿಯೊಂದನ್ನೂ ಆಕಸ್ಮಿಕ ಹೋಲಿಕೆಯ ವಿರುದ್ಧ ಪರೀಕ್ಷಿಸಲಾಗಿದೆ. ಪ್ರತಿಯೊಂದನ್ನು ದೃಢೀಕರಿಸಿ ಅಥವಾ ತಿರಸ್ಕರಿಸಿ.")],
        [L("How reliable is this forecast", "ಮುನ್ಸೂಚನೆ ಎಷ್ಟು ವಿಶ್ವಾಸಾರ್ಹ"), L("FIRs registered each month (the history it is measured against), how often past ranges held, and the model card: what it is built on and what it is for.", "ಪ್ರತಿ ತಿಂಗಳು ದಾಖಲಾದ FIR (ಹೋಲಿಸುವ ಇತಿಹಾಸ), ಹಿಂದಿನ ವ್ಯಾಪ್ತಿಗಳು ಎಷ್ಟು ಬಾರಿ ಸರಿಯಾದವು, ಮತ್ತು ಮಾದರಿ ಕಾರ್ಡ್: ಆಧಾರ ಮತ್ತು ಉದ್ದೇಶ.")],
      ] },
    ],
    note: L("A forecast is a range to plan patrols with: decision support, not a verdict. It is not evidence and never a reason to act against any person or group.", "ಮುನ್ಸೂಚನೆ ಗಸ್ತು ಯೋಜನೆಗೆ ಒಂದು ವ್ಯಾಪ್ತಿ: ನಿರ್ಧಾರಕ್ಕೆ ಸಹಾಯ, ತೀರ್ಪಲ್ಲ. ಇದು ಸಾಕ್ಷ್ಯವಲ್ಲ, ಯಾವುದೇ ವ್ಯಕ್ತಿ ಅಥವಾ ಗುಂಪಿನ ವಿರುದ್ಧ ಕ್ರಮಕ್ಕೆ ಕಾರಣವಲ್ಲ."),
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
    lead: L("Search has four views, picked at the top: People finds a person in the FIR register, Money trail follows money between accounts named in FIRs, Social insights compares districts, and OSINT checks an identifier on the open web.",
            "ಹುಡುಕಾಟದಲ್ಲಿ ನಾಲ್ಕು ನೋಟಗಳು, ಮೇಲೆ ಆರಿಸಿ: ವ್ಯಕ್ತಿಗಳು FIR ದಾಖಲೆಯಲ್ಲಿ ವ್ಯಕ್ತಿಯನ್ನು ಹುಡುಕುತ್ತದೆ, ಹಣದ ಜಾಡು FIR ಖಾತೆಗಳ ನಡುವೆ ಹಣ ಅನುಸರಿಸುತ್ತದೆ, ಸಾಮಾಜಿಕ ಒಳನೋಟ ಜಿಲ್ಲೆಗಳನ್ನು ಹೋಲಿಸುತ್ತದೆ, OSINT ಒಂದು ಗುರುತನ್ನು ಮುಕ್ತ ವೆಬ್‌ನಲ್ಲಿ ಪರಿಶೀಲಿಸುತ್ತದೆ."),
    blocks: [
      { h: L("People · finding someone", "ವ್ಯಕ್ತಿಗಳು · ಹುಡುಕುವುದು"), items: [
        [L("The box", "ಹುಡುಕಾಟ ಪೆಟ್ಟಿಗೆ"), L("Type a name, alias, father's name, phone or vehicle plate, or press the mic and say it. Close spellings and sound-alike names match too.", "ಹೆಸರು, ಅಡ್ಡಹೆಸರು, ತಂದೆಯ ಹೆಸರು, ಫೋನ್ ಅಥವಾ ವಾಹನ ಸಂಖ್ಯೆ ಟೈಪ್ ಮಾಡಿ, ಅಥವಾ ಮೈಕ್ ಒತ್ತಿ ಹೇಳಿ. ಹತ್ತಿರದ ಕಾಗುಣಿತ ಮತ್ತು ಒಂದೇ ಉಚ್ಚಾರದ ಹೆಸರುಗಳೂ ಹೊಂದುತ್ತವೆ.")],
        [L("All · Name · Alias · Father (s/o) · Phone", "ಎಲ್ಲಾ · ಹೆಸರು · ಅಡ್ಡಹೆಸರು · ತಂದೆ · ಫೋನ್"), L("Search one field only, when a common name brings too many people.", "ಸಾಮಾನ್ಯ ಹೆಸರಿಗೆ ತುಂಬಾ ಜನ ಬಂದಾಗ, ಒಂದೇ ಕ್ಷೇತ್ರದಲ್ಲಿ ಹುಡುಕಿ.")],
        [L("Results", "ಫಲಿತಾಂಶಗಳು"), L("Highest risk first. Each row: name and alias, ID, area, risk and how many FIRs. Click one to open the record.", "ಹೆಚ್ಚು ಅಪಾಯ ಮೊದಲು. ಪ್ರತಿ ಸಾಲು: ಹೆಸರು, ಅಡ್ಡಹೆಸರು, ID, ಪ್ರದೇಶ, ಅಪಾಯ, FIR ಸಂಖ್ಯೆ. ದಾಖಲೆ ತೆರೆಯಲು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("No match", "ಹೊಂದಿಕೆ ಇಲ್ಲ"), L("Try fewer letters or an alias. A name that is not on record can be kept as an unknown lead.", "ಕಡಿಮೆ ಅಕ್ಷರ ಅಥವಾ ಅಡ್ಡಹೆಸರು ಪ್ರಯತ್ನಿಸಿ. ದಾಖಲೆಯಲ್ಲಿಲ್ಲದ ಹೆಸರನ್ನು ಅಜ್ಞಾತ ಸುಳಿವಾಗಿ ಇಡಬಹುದು.")],
      ] },
      { h: L("People · the record", "ವ್ಯಕ್ತಿಗಳು · ದಾಖಲೆ"), items: [
        [L("Risk score", "ಅಪಾಯ ಅಂಕ"), L("Out of 100: how recent, how frequent and how serious their cases are, and their links to others. Why this risk score shows each part.", "100 ರಲ್ಲಿ: ಪ್ರಕರಣಗಳು ಎಷ್ಟು ಇತ್ತೀಚಿನವು, ಎಷ್ಟು ಬಾರಿ, ಎಷ್ಟು ಗಂಭೀರ, ಮತ್ತು ಇತರರೊಂದಿಗಿನ ಸಂಪರ್ಕ. ಪ್ರತಿ ಭಾಗ “ಏಕೆ ಈ ಅಂಕ” ದಲ್ಲಿ.")],
        [L("What is inside", "ಒಳಗೆ ಏನಿದೆ"), L("Record details, how they operate (MO), the FIRs naming them, known associates, accounts they hold in the money trail, similar past cases and recommended next steps.", "ದಾಖಲೆ ವಿವರ, ಕಾರ್ಯವಿಧಾನ (MO), ಅವರನ್ನು ಹೆಸರಿಸುವ FIR ಗಳು, ಸಹಚರರು, ಹಣದ ಜಾಡಿನಲ್ಲಿ ಅವರ ಖಾತೆಗಳು, ಹೋಲುವ ಹಿಂದಿನ ಪ್ರಕರಣಗಳು, ಮುಂದಿನ ಹೆಜ್ಜೆಗಳು.")],
        [L("Actions", "ಕ್ರಮಗಳು"), L("Show in Brain, Ask Antar, Map. Request watchlist goes to a supervising officer, and nothing is watched until they approve.", "ಬ್ರೈನ್‌ನಲ್ಲಿ ತೋರಿಸಿ, ಅಂತರ್‌ಗೆ ಕೇಳಿ, ನಕ್ಷೆ. ವೀಕ್ಷಣಾ ಪಟ್ಟಿ ವಿನಂತಿ ಮೇಲ್ವಿಚಾರಕರಿಗೆ ಹೋಗುತ್ತದೆ; ಅವರು ಅನುಮೋದಿಸುವವರೆಗೆ ಏನೂ ವೀಕ್ಷಣೆಯಲ್ಲಿಲ್ಲ.")],
        [L("Same person?", "ಒಂದೇ ವ್ಯಕ್ತಿಯೇ?"), L("When two records may be one person, it is shown as a guess. An Inspector or above confirms or rejects it.", "ಎರಡು ದಾಖಲೆಗಳು ಒಬ್ಬರೇ ಇರಬಹುದಾದಾಗ ಊಹೆಯಾಗಿ ತೋರಿಸಲಾಗುತ್ತದೆ. ಇನ್ಸ್‌ಪೆಕ್ಟರ್ ಅಥವಾ ಮೇಲಿನವರು ದೃಢೀಕರಿಸುತ್ತಾರೆ ಅಥವಾ ತಿರಸ್ಕರಿಸುತ್ತಾರೆ.")],
      ] },
      { h: L("Money trail", "ಹಣದ ಜಾಡು"), items: [
        [L("What it shows", "ಏನು ತೋರಿಸುತ್ತದೆ"), L("Money from a complainant's account through the UPI IDs named in FIRs to where it ended up.", "ದೂರುದಾರರ ಖಾತೆಯಿಂದ FIR ಗಳಲ್ಲಿ ಹೆಸರಿಸಿದ UPI ಮೂಲಕ ಹಣ ಎಲ್ಲಿಗೆ ಹೋಯಿತು.")],
        [L("Accounts worth a look", "ಗಮನಿಸಬೇಕಾದ ಖಾತೆಗಳು"), L("Most warning signs first: collects from many accounts, passes money on within 48 hours, amounts just under Rs 50,000, named in several FIRs, cash taken out.", "ಹೆಚ್ಚು ಎಚ್ಚರಿಕೆ ಸೂಚನೆ ಮೊದಲು: ಹಲವು ಖಾತೆಗಳಿಂದ ಸಂಗ್ರಹ, 48 ಗಂಟೆಯೊಳಗೆ ಮುಂದೆ ಕಳುಹಿಸುವುದು, Rs 50,000 ಕ್ಕಿಂತ ಸ್ವಲ್ಪ ಕಡಿಮೆ ಮೊತ್ತ, ಹಲವು FIR ಗಳಲ್ಲಿ ಹೆಸರು, ನಗದು ಹಿಂಪಡೆತ.")],
        [L("The graph", "ಗ್ರಾಫ್"), L("Arrows go from payer to payee; thicker means more money. Show 1, 2 or 3 steps out, and click an account to read it.", "ಬಾಣಗಳು ಪಾವತಿದಾರರಿಂದ ಸ್ವೀಕರಿಸುವವರಿಗೆ; ದಪ್ಪ ಎಂದರೆ ಹೆಚ್ಚು ಹಣ. 1, 2 ಅಥವಾ 3 ಹಂತ ತೋರಿಸಿ, ಓದಲು ಖಾತೆ ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("The account", "ಖಾತೆ"), L("Money in and out, every FIR naming it, and a CSV export for a bank or financial-intelligence request.", "ಒಳಬಂದ ಮತ್ತು ಹೊರಹೋದ ಹಣ, ಅದನ್ನು ಹೆಸರಿಸುವ ಪ್ರತಿ FIR, ಮತ್ತು ಬ್ಯಾಂಕ್ ವಿನಂತಿಗೆ CSV ರಫ್ತು.")],
      ] },
      { h: L("Social insights", "ಸಾಮಾಜಿಕ ಒಳನೋಟ"), items: [
        [L("What it shows", "ಏನು ತೋರಿಸುತ್ತದೆ"), L("How crime in Karnataka's 30 districts lines up with things like urbanisation, education, child marriage and alcohol use (Census 2011, NFHS-5), and who the victims are by sex, age and occupation.", "30 ಜಿಲ್ಲೆಗಳ ಅಪರಾಧ ನಗರೀಕರಣ, ಶಿಕ್ಷಣ, ಬಾಲ್ಯವಿವಾಹ, ಮದ್ಯಪಾನ ಮುಂತಾದವುಗಳೊಂದಿಗೆ ಹೇಗೆ ಹೊಂದುತ್ತದೆ (ಜನಗಣತಿ 2011, NFHS-5), ಮತ್ತು ಸಂತ್ರಸ್ತರು ಲಿಂಗ, ವಯಸ್ಸು, ಉದ್ಯೋಗದ ಪ್ರಕಾರ.")],
        [L("Reading a link", "ಸಂಬಂಧ ಓದುವುದು"), L("ρ runs from -1 to +1: further from 0 is stronger. p below 0.05 means it is unlikely to be chance. \"Urbanisation held constant\" means it is not only a city effect.", "ρ -1 ರಿಂದ +1: 0 ಯಿಂದ ದೂರ ಎಂದರೆ ಬಲವಾದದ್ದು. p 0.05 ಕ್ಕಿಂತ ಕಡಿಮೆ ಎಂದರೆ ಆಕಸ್ಮಿಕವಲ್ಲ. “ನಗರೀಕರಣ ಸ್ಥಿರ” ಎಂದರೆ ಕೇವಲ ನಗರದ ಪರಿಣಾಮವಲ್ಲ.")],
        [L("Districts, not people", "ಜಿಲ್ಲೆಗಳು, ವ್ಯಕ್ತಿಗಳಲ್ಲ"), L("A link between districts says nothing about anyone living in them, and is never a reason to target, stop or suspect anyone.", "ಜಿಲ್ಲೆಗಳ ನಡುವಿನ ಸಂಬಂಧ ಅಲ್ಲಿ ವಾಸಿಸುವ ಯಾರ ಬಗ್ಗೆಯೂ ಏನನ್ನೂ ಹೇಳುವುದಿಲ್ಲ; ಯಾರನ್ನೂ ಗುರಿಯಾಗಿಸಲು, ತಡೆಯಲು ಅಥವಾ ಶಂಕಿಸಲು ಕಾರಣವಲ್ಲ.")],
      ] },
      { h: L("OSINT · open-source checks", "OSINT · ಮುಕ್ತ ಮೂಲ ಪರಿಶೀಲನೆ"), items: [
        [L("Where", "ಎಲ್ಲಿ"), L("The small grey OSINT at the top right, for Inspector and above. Read the card, then I understand · Start.", "ಮೇಲಿನ ಬಲದಲ್ಲಿ ಸಣ್ಣ ಬೂದು OSINT, ಇನ್ಸ್‌ಪೆಕ್ಟರ್ ಮತ್ತು ಮೇಲಿನವರಿಗೆ. ಕಾರ್ಡ್ ಓದಿ, ನಂತರ “ಅರ್ಥವಾಯಿತು · ಪ್ರಾರಂಭಿಸಿ”.")],
        [L("What you can check", "ಏನನ್ನು ಪರಿಶೀಲಿಸಬಹುದು"), L("A phone, UPI ID, vehicle number, bank account or IFSC, IMEI, website, email, username or name. Narrow it to Open web, News, Social media, Government, Marketplace or Court and legal pages.", "ಫೋನ್, UPI, ವಾಹನ ಸಂಖ್ಯೆ, ಬ್ಯಾಂಕ್ ಖಾತೆ/IFSC, IMEI, ವೆಬ್‌ಸೈಟ್, ಇಮೇಲ್, ಬಳಕೆದಾರ ಹೆಸರು ಅಥವಾ ಹೆಸರು. ಮುಕ್ತ ವೆಬ್, ಸುದ್ದಿ, ಸಾಮಾಜಿಕ ಮಾಧ್ಯಮ, ಸರ್ಕಾರ, ಮಾರುಕಟ್ಟೆ ಅಥವಾ ನ್ಯಾಯಾಲಯ ಪುಟಗಳಿಗೆ ಸೀಮಿತಗೊಳಿಸಿ.")],
        [L("What comes back", "ಏನು ಸಿಗುತ್ತದೆ"), L("What the identifier is, only pages that really contain it, live registry checks (IFSC branch, website age, IMEI), the official portals to check next and a drafted notice. Copy it all as a lead sheet.", "ಗುರುತು ಏನು, ಅದನ್ನು ನಿಜವಾಗಿ ಹೊಂದಿರುವ ಪುಟಗಳು ಮಾತ್ರ, ನೇರ ನೋಂದಣಿ ಪರಿಶೀಲನೆ (IFSC ಶಾಖೆ, ವೆಬ್‌ಸೈಟ್ ವಯಸ್ಸು, IMEI), ಮುಂದಿನ ಅಧಿಕೃತ ಪೋರ್ಟಲ್‌ಗಳು ಮತ್ತು ಕರಡು ನೋಟಿಸ್. ಎಲ್ಲವನ್ನೂ ಸುಳಿವು ಹಾಳೆಯಾಗಿ ನಕಲಿಸಿ.")],
        [L("Kept safe", "ಸುರಕ್ಷಿತ"), L("Only the identifier you type leaves Antar; no FIR is read. Everything found is unverified. Each search is logged against you, the identifier kept only as a fingerprint.", "ನೀವು ಟೈಪ್ ಮಾಡುವ ಗುರುತು ಮಾತ್ರ ಹೊರಹೋಗುತ್ತದೆ; ಯಾವುದೇ FIR ಓದುವುದಿಲ್ಲ. ಸಿಕ್ಕಿದ್ದೆಲ್ಲವೂ ಪರಿಶೀಲಿಸದ್ದು. ಪ್ರತಿ ಹುಡುಕಾಟ ನಿಮ್ಮ ಹೆಸರಿನಲ್ಲಿ ದಾಖಲಾಗುತ್ತದೆ, ಗುರುತನ್ನು ಬೆರಳಚ್ಚಾಗಿ ಮಾತ್ರ ಇಡಲಾಗುತ್ತದೆ.")],
      ] },
    ],
    examples: { en: ["Yelappa", "KA-05-EZ-7878"], kn: ["Yelappa", "KA-05-EZ-7878"] },
    tip: L("On Money trail and Social insights, the ? button opens that view's own longer guide.", "ಹಣದ ಜಾಡು ಮತ್ತು ಸಾಮಾಜಿಕ ಒಳನೋಟದಲ್ಲಿ, ? ಗುಂಡಿ ಆ ನೋಟದ ವಿವರವಾದ ಮಾರ್ಗದರ್ಶಿ ತೆರೆಯುತ್ತದೆ."),
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
    title: L("Social Insights Guide", "ಸಾಮಾಜಿಕ ಒಳನೋಟ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("How crime across Karnataka's 30 districts lines up with urbanisation, population growth, education, child marriage, household amenities and alcohol use, and who the victims are.",
            "ಕರ್ನಾಟಕದ 30 ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಅಪರಾಧವು ನಗರೀಕರಣ, ಜನಸಂಖ್ಯಾ ಬೆಳವಣಿಗೆ, ಶಿಕ್ಷಣ, ಬಾಲ್ಯ ವಿವಾಹ, ಗೃಹ ಸೌಲಭ್ಯ ಮತ್ತು ಮದ್ಯಪಾನದೊಂದಿಗೆ ಹೇಗೆ ಹೊಂದುತ್ತದೆ, ಮತ್ತು ಸಂತ್ರಸ್ತರು ಯಾರು."),
    blocks: [
      { h: L("Reading a link", "ಸಂಬಂಧ ಓದುವುದು"), items: [
        [L("The sentence", "ವಾಕ್ಯ"), L("What goes with more or less crime, and how strongly.", "ಯಾವುದು ಹೆಚ್ಚು ಅಥವಾ ಕಡಿಮೆ ಅಪರಾಧದೊಂದಿಗೆ ಬರುತ್ತದೆ, ಎಷ್ಟು ಬಲವಾಗಿ.")],
        [L("ρ and p", "ρ ಮತ್ತು p"), L("ρ runs from -1 to +1: the further from 0, the stronger. p below 0.05 means the link is unlikely to be chance.", "ρ -1 ರಿಂದ +1: 0 ಯಿಂದ ದೂರವಾದಷ್ಟು ಬಲ. p 0.05 ಕ್ಕಿಂತ ಕಡಿಮೆ ಎಂದರೆ ಆಕಸ್ಮಿಕವಲ್ಲ.")],
        [L("Urbanisation held constant", "ನಗರೀಕರಣ ಸ್ಥಿರ"), L("Cities report more crime. A link that holds once urbanisation is taken out is not only a city effect.", "ನಗರಗಳು ಹೆಚ್ಚು ವರದಿ ಮಾಡುತ್ತವೆ. ನಗರೀಕರಣ ತೆಗೆದರೂ ಉಳಿಯುವ ಸಂಬಂಧ ಕೇವಲ ನಗರ ಪರಿಣಾಮವಲ್ಲ.")],
        [L("Reading in italics", "ಓರೆ ಅಕ್ಷರದ ಅರ್ಥ"), L("What the link most likely means. Better-off districts recording more crime usually reflects reporting, not more offending.", "ಸಂಬಂಧದ ಸಂಭವನೀಯ ಅರ್ಥ. ಉತ್ತಮ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚು ದಾಖಲಾತಿ ಸಾಮಾನ್ಯವಾಗಿ ವರದಿಯ ಪರಿಣಾಮ.")],
      ] },
      { h: L("On the screen", "ಪರದೆಯಲ್ಲಿ"), items: [
        [L("Kind of crime", "ಅಪರಾಧದ ಪ್ರಕಾರ"), L("All crime, property, violent, against women, fraud and cyber, road accidents.", "ಎಲ್ಲ, ಆಸ್ತಿ, ಹಿಂಸಾತ್ಮಕ, ಮಹಿಳೆಯರ ವಿರುದ್ಧ, ವಂಚನೆ ಮತ್ತು ಸೈಬರ್, ರಸ್ತೆ ಅಪಘಾತ.")],
        [L("Each district", "ಪ್ರತಿ ಜಿಲ್ಲೆ"), L("Pick an indicator to see every district as a dot; Bengaluru Urban is outlined.", "ಸೂಚಕ ಆರಿಸಿ, ಪ್ರತಿ ಜಿಲ್ಲೆ ಒಂದು ಚುಕ್ಕೆ; ಬೆಂಗಳೂರು ನಗರ ಗುರುತಿಸಲಾಗಿದೆ.")],
        [L("Districts table", "ಜಿಲ್ಲಾ ಪಟ್ಟಿ"), L("Sort by any column. Rates are FIRs per lakh people a year, 2016-2022.", "ಯಾವುದೇ ಕಾಲಂ ಪ್ರಕಾರ ವಿಂಗಡಿಸಿ. ದರ: ವರ್ಷಕ್ಕೆ ಲಕ್ಷ ಜನರಿಗೆ FIR, 2016-2022.")],
        [L("Ask in Chat", "ಚಾಟ್‌ನಲ್ಲಿ ಕೇಳಿ"), L("“Is alcohol linked to crimes against women?” gets the same figures in Chat.", "“ಮದ್ಯಪಾನ ಮಹಿಳೆಯರ ವಿರುದ್ಧದ ಅಪರಾಧಕ್ಕೆ ಸಂಬಂಧಿಸಿದೆಯೇ?” ಚಾಟ್‌ನಲ್ಲೂ ಅದೇ ಅಂಕಿ.")],
      ] },
      { h: L("Hard limit", "ಕಟ್ಟುನಿಟ್ಟಾದ ಮಿತಿ"), warn: true, items: [
        [L("Districts, not people", "ಜಿಲ್ಲೆಗಳು, ವ್ಯಕ್ತಿಗಳಲ್ಲ"), L("A link between districts says nothing about any person in them, and is never a basis to target, stop or suspect anyone.", "ಜಿಲ್ಲೆಗಳ ನಡುವಿನ ಸಂಬಂಧ ಯಾವುದೇ ವ್ಯಕ್ತಿಯ ಬಗ್ಗೆ ಹೇಳುವುದಿಲ್ಲ; ಯಾರನ್ನೂ ಗುರಿಯಾಗಿಸಲು ಆಧಾರವಲ್ಲ.")],
        [L("Sources", "ಮೂಲಗಳು"), L("Census of India 2011 and NFHS-5 (2019-21) district factsheets.", "ಭಾರತದ ಜನಗಣತಿ 2011 ಮತ್ತು NFHS-5 (2019-21) ಜಿಲ್ಲಾ ಮಾಹಿತಿ.")],
      ] },
    ],
  },

  money: {
    title: L("Money Trail Guide", "ಹಣದ ಜಾಡು ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Follow money from a complainant's account through the UPI IDs named in FIRs to where it ended up, and see which accounts behave like collection points or mules.",
            "ದೂರುದಾರರ ಖಾತೆಯಿಂದ FIR ಗಳಲ್ಲಿನ UPI ಐಡಿಗಳ ಮೂಲಕ ಹಣ ಎಲ್ಲಿ ತಲುಪಿತು ಎಂದು ಅನುಸರಿಸಿ."),
    blocks: [
      { h: L("Accounts worth a look", "ಗಮನಿಸಬೇಕಾದ ಖಾತೆಗಳು"), items: [
        [L("Ranking", "ಶ್ರೇಣಿ"), L("Most warning signs first, then the most money received.", "ಹೆಚ್ಚು ಎಚ್ಚರಿಕೆಗಳು ಮೊದಲು, ನಂತರ ಹೆಚ್ಚು ಹಣ ಪಡೆದವು.")],
        [L("Warning signs", "ಎಚ್ಚರಿಕೆಗಳು"), L("Collects from many accounts; money passes straight through within 48 hours; amounts just under Rs 50,000; named in several FIRs; cash taken out. Each states its numbers.", "ಹಲವು ಖಾತೆಗಳಿಂದ ಸಂಗ್ರಹ; 48 ಗಂಟೆಯಲ್ಲಿ ಹಣ ಮುಂದೆ; ₹50,000 ಕ್ಕಿಂತ ಸ್ವಲ್ಪ ಕಡಿಮೆ; ಹಲವು FIR; ನಗದು ಹಿಂಪಡೆತ.")],
        [L("Find", "ಹುಡುಕಿ"), L("Search by UPI ID, account, FIR id or suspect id.", "UPI ಐಡಿ, ಖಾತೆ, FIR ಅಥವಾ ಶಂಕಿತ ಐಡಿಯಿಂದ ಹುಡುಕಿ.")],
      ] },
      { h: L("The graph", "ಗ್ರಾಫ್"), items: [
        [L("Colours", "ಬಣ್ಣಗಳು"), L("Complainant, UPI on an FIR, collector account, suspect, cash withdrawal: see the legend under the graph.", "ದೂರುದಾರ, FIR ನ UPI, ಸಂಗ್ರಹ ಖಾತೆ, ಶಂಕಿತ, ನಗದು: ಗ್ರಾಫ್ ಕೆಳಗಿನ ಸೂಚಿ ನೋಡಿ.")],
        [L("Arrows", "ಬಾಣಗಳು"), L("Payer to payee; the thicker the arrow, the more money. Hover for the amount and dates.", "ಪಾವತಿದಾರರಿಂದ ಸ್ವೀಕರಿಸುವವರಿಗೆ; ದಪ್ಪ ಬಾಣ = ಹೆಚ್ಚು ಹಣ.")],
        [L("Steps", "ಹಂತಗಳು"), L("1, 2 or 3 steps from the chosen account. Click an account to read it; “Follow the money from here” re-centres the graph.", "ಆಯ್ದ ಖಾತೆಯಿಂದ 1, 2 ಅಥವಾ 3 ಹಂತ. ಖಾತೆ ಕ್ಲಿಕ್ ಮಾಡಿ ಓದಿ.")],
      ] },
      { h: L("The account", "ಖಾತೆ"), items: [
        [L("Money in and out", "ಬಂದ ಮತ್ತು ಹೋದ ಹಣ"), L("Totals, how many accounts, and when it was active.", "ಒಟ್ಟು, ಎಷ್ಟು ಖಾತೆಗಳು, ಯಾವಾಗ ಸಕ್ರಿಯ.")],
        [L("FIRs", "FIR ಗಳು"), L("Every FIR naming the account; each opens the full case.", "ಖಾತೆಯನ್ನು ಹೆಸರಿಸುವ ಪ್ರತಿ FIR; ಪ್ರತಿಯೊಂದೂ ಪ್ರಕರಣ ತೆರೆಯುತ್ತದೆ.")],
        [L("Export", "ರಫ್ತು"), L("Download the account's transactions as CSV for a bank or financial-intelligence request.", "ಬ್ಯಾಂಕ್ ಅಥವಾ ಆರ್ಥಿಕ ಗುಪ್ತಚರ ವಿನಂತಿಗಾಗಿ ವಹಿವಾಟುಗಳನ್ನು CSV ಆಗಿ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ.")],
      ] },
    ],
  },

  case: {
    title: L("Case Guide", "ಪ್ರಕರಣ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("One FIR start to finish: a summary, the investigation timeline, the victims, how cases like it ended, and the accused's other FIRs.",
            "ಒಂದು FIR ಆರಂಭದಿಂದ ಕೊನೆಯವರೆಗೆ: ಸಾರಾಂಶ, ತನಿಖೆಯ ಕಾಲರೇಖೆ, ಸಂತ್ರಸ್ತರು, ಇಂತಹ ಪ್ರಕರಣಗಳು ಹೇಗೆ ಮುಗಿದವು."),
    blocks: [
      { h: L("Timeline", "ಕಾಲರೇಖೆ"), items: [
        [L("Steps", "ಹಂತಗಳು"), L("Registered, investigation, arrests, charge-sheet, court. The blue dot is where the case is now.", "ದಾಖಲು, ತನಿಖೆ, ಬಂಧನ, ದೋಷಾರೋಪಣೆ, ನ್ಯಾಯಾಲಯ. ನೀಲಿ ಚುಕ್ಕೆ = ಈಗಿನ ಹಂತ.")],
        [L("Date not recorded", "ದಿನಾಂಕ ದಾಖಲಾಗಿಲ್ಲ"), L("The register dates only the registration; later steps are counts, so no date is guessed.", "ದಾಖಲೆಯಲ್ಲಿ ನೋಂದಣಿಗೆ ಮಾತ್ರ ದಿನಾಂಕ; ನಂತರದ ಹಂತಗಳಿಗೆ ದಿನಾಂಕ ಊಹಿಸಲಾಗುವುದಿಲ್ಲ.")],
        [L("60 and 90 days", "60 ಮತ್ತು 90 ದಿನ"), L("An open case shows its BNSS s.187(3) clock: default bail if the investigation runs past these marks.", "ತೆರೆದ ಪ್ರಕರಣ BNSS s.187(3) ಗಡಿಯಾರ ತೋರಿಸುತ್ತದೆ.")],
      ] },
      { h: L("Around the case", "ಪ್ರಕರಣದ ಸುತ್ತ"), items: [
        [L("Cases like this", "ಇಂತಹ ಪ್ರಕರಣಗಳು"), L("Same crime at the same station, or the district or state when there are too few; no conviction rate under 10 verdicts.", "ಅದೇ ಠಾಣೆಯ ಅದೇ ಅಪರಾಧ; ಕಡಿಮೆ ಇದ್ದರೆ ಜಿಲ್ಲೆ ಅಥವಾ ರಾಜ್ಯ.")],
        [L("Follow the money", "ಹಣ ಅನುಸರಿಸಿ"), L("When the FIR names a UPI ID, it opens on the Money trail.", "FIR ನಲ್ಲಿ UPI ಐಡಿ ಇದ್ದರೆ ಹಣದ ಜಾಡಿನಲ್ಲಿ ತೆರೆಯುತ್ತದೆ.")],
        [L("Print or save as PDF", "ಮುದ್ರಿಸಿ ಅಥವಾ PDF"), L("A clean case sheet for the file.", "ಕಡತಕ್ಕೆ ಸ್ವಚ್ಛ ಪ್ರಕರಣ ಹಾಳೆ.")],
      ] },
    ],
  },

  governance: {
    title: L("Data Protection Guide", "ಮಾಹಿತಿ ಸಂರಕ್ಷಣೆ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("How Antar handles personal data: the law it follows, who sees what, what is kept and for how long, and how every step can be checked.",
            "ಅಂತರ್ ವೈಯಕ್ತಿಕ ಮಾಹಿತಿಯನ್ನು ಹೇಗೆ ನಿರ್ವಹಿಸುತ್ತದೆ."),
    blocks: [
      { h: L("Reading the page", "ಪುಟ ಓದುವುದು"), items: [
        [L("Numbered sections", "ಸಂಖ್ಯೆಯ ವಿಭಾಗಗಳು"), L("Jump to any from the list at the top.", "ಮೇಲಿನ ಪಟ್ಟಿಯಿಂದ ಯಾವುದಕ್ಕಾದರೂ ಹೋಗಿ.")],
        [L("File names", "ಕಡತದ ಹೆಸರುಗಳು"), L("Each claim names the part of the system that makes it true, so it can be checked.", "ಪ್ರತಿ ಹೇಳಿಕೆಯು ಅದನ್ನು ನಿಜ ಮಾಡುವ ಭಾಗವನ್ನು ಹೆಸರಿಸುತ್ತದೆ.")],
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
        [L("Search › Money trail", "ಹುಡುಕಾಟ › ಹಣದ ಜಾಡು"), L("Follow money between accounts named in FIRs.", "FIR ಗಳಲ್ಲಿನ ಖಾತೆಗಳ ನಡುವೆ ಹಣ ಅನುಸರಿಸಿ.")],
        [L("Social insights", "ಸಾಮಾಜಿಕ ಒಳನೋಟ"), L("District social indicators against crime; open it from Predict.", "ಜಿಲ್ಲಾ ಸಾಮಾಜಿಕ ಸೂಚಕಗಳು ಮತ್ತು ಅಪರಾಧ; Predict ನಿಂದ ತೆರೆಯಿರಿ.")],
        [L("Account", "ಖಾತೆ"), L("Your shift brief, alerts, approvals, settings and records.", "ನಿಮ್ಮ ಶಿಫ್ಟ್ ಬ್ರೀಫ್, ಎಚ್ಚರಿಕೆ, ಅನುಮೋದನೆ, ಸೆಟ್ಟಿಂಗ್ ಮತ್ತು ದಾಖಲೆಗಳು.")],
      ] },
    ],
  },
};

function pickGuide(path, expertOn) {
  if (!path) return "general";
  if (path.startsWith("/antarBrain")) return "brain";
  if (path.startsWith("/antar")) return expertOn ? "expert" : "chat";
  // the Money trail is a view of Search (/search?view=money)
  if (path.startsWith("/search") && typeof window !== "undefined" && /[?&]view=money/.test(window.location.search)) return "money";
  for (const key of ["predict", "map", "search", "trace", "approvals", "account", "network", "trends", "profiles", "social", "money", "case", "governance"]) {
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
