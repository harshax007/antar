// Builds docs/Antar_End_to_End_Guide.docx (14 pages, A4).
// Run:  npm install docx@9   (in any folder)   then   node scripts/build_end_to_end_guide.js docs/Antar_End_to_End_Guide.docx
// After changing content, check the page count stays at 14 (Word: File > Info, or export to PDF).

const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, BorderStyle, PageBreak, Header, Footer, PageNumber, LevelFormat, TabStopType,
  VerticalAlign, HeadingLevel, Tab,
} = require("docx");

// ── palette & page geometry (A4, 18 mm margins) ─────────────────────────────────
const INK = "0B1F2A", TEAL = "0A7E8C", MUTED = "5B6675", LINE = "D5DBE2";
const FILL = "EEF7F8", FILL2 = "F4F6F9", GREEN = "1E7F4F", AMBER = "9A6400", RED = "A12B2B";
const W = 11906 - 2 * 1020;              // text width in DXA
const FONT = "Calibri";

const r = (t, o = {}) => new TextRun({ text: t, font: FONT, size: o.size || 22, bold: o.bold, italics: o.italics, color: o.color || INK });
// inline **bold** support
function runs(text, o = {}) {
  return String(text).split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).filter(Boolean).map((s) =>
    s.startsWith("**") ? r(s.slice(2, -2), { ...o, bold: true })
      : (s.startsWith("*") && s.endsWith("*") && s.length > 2) ? r(s.slice(1, -1), { ...o, italics: true })
      : r(s, o));
}
const P = (text, o = {}) => new Paragraph({
  children: runs(text, o), spacing: { after: o.after ?? 110, before: o.before ?? 0, line: o.line || 300 },
  alignment: o.align,
});
const H1 = (num, text, sub) => [
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [r(`${num}  `, { size: 30, bold: true, color: TEAL }), r(text, { size: 30, bold: true })],
    spacing: { after: sub ? 40 : 140 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: TEAL, space: 4 } },
  }),
  ...(sub ? [new Paragraph({ children: [r(sub, { size: 19, italics: true, color: MUTED })], spacing: { after: 140 } })] : []),
];
const H2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [r(text, { size: 22, bold: true, color: TEAL })], spacing: { before: 140, after: 70 },
});
const B = (text, lvl = 0) => new Paragraph({
  children: runs(text), numbering: { reference: "bul", level: lvl }, spacing: { after: 70, line: 288 },
});
const N = (text) => new Paragraph({ children: runs(text), numbering: { reference: "num", level: 0 }, spacing: { after: 50, line: 252 } });
const BR = () => new Paragraph({ children: [new PageBreak()] });

function cell(content, width, o = {}) {
  const paras = (Array.isArray(content) ? content : [content]).map((c) =>
    c instanceof Paragraph ? c : new Paragraph({
      children: runs(c, { size: o.size || 20, color: o.color, bold: o.bold }),
      spacing: { after: 20, line: 264 }, alignment: o.align,
    }));
  return new TableCell({
    children: paras, width: { size: width, type: WidthType.DXA },
    shading: o.fill ? { type: ShadingType.CLEAR, color: "auto", fill: o.fill } : undefined,
    margins: { top: 70, bottom: 70, left: 110, right: 110 }, verticalAlign: o.valign || VerticalAlign.TOP,
    columnSpan: o.span,
  });
}
const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
function table(header, rows, widths, o = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const trs = [];
  if (header) trs.push(new TableRow({
    tableHeader: true,
    children: header.map((h, i) => cell(h, widths[i], { fill: TEAL, color: "FFFFFF", bold: true, size: o.size || 18 })),
  }));
  rows.forEach((row, ri) => trs.push(new TableRow({
    cantSplit: true,
    children: row.map((c, i) => cell(c, widths[i], {
      size: o.size || 18, fill: (o.firstColFill && i === 0) ? FILL : (o.zebra && ri % 2 ? FILL2 : undefined),
      bold: o.firstColBold && i === 0,
    })),
  })));
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths, rows: trs,
    borders: { top: border, bottom: border, left: border, right: border, insideHorizontal: border, insideVertical: border },
  });
}
// callout box: single shaded cell
function callout(lines, fill = FILL) {
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: [W],
    borders: { top: { style: BorderStyle.SINGLE, size: 4, color: TEAL }, bottom: { style: BorderStyle.SINGLE, size: 4, color: TEAL },
      left: { style: BorderStyle.SINGLE, size: 24, color: TEAL }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
      insideHorizontal: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, insideVertical: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } },
    rows: [new TableRow({ children: [new TableCell({
      width: { size: W, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, color: "auto", fill },
      margins: { top: 90, bottom: 90, left: 180, right: 180 },
      children: lines.map((l) => new Paragraph({ children: runs(l, { size: 21 }), spacing: { after: 60, line: 276 } })),
    })] })],
  });
}
const gap = (n = 80) => new Paragraph({ children: [], spacing: { after: n } });
const w = (...fr) => { const s = fr.reduce((a, b) => a + b, 0); const out = fr.map((f) => Math.floor((W * f) / s)); out[out.length - 1] += W - out.reduce((a, b) => a + b, 0); return out; };

// ═════════════════════════════════════════════════════════════════════════════
const C = [];

// ── PAGE 1 · COVER ──────────────────────────────────────────────────────────
C.push(gap(900));
C.push(new Paragraph({ children: [r("ANTAR", { size: 72, bold: true, color: TEAL })], spacing: { after: 60 } }));
C.push(new Paragraph({ children: [r("Intelligent Conversational AI & Crime Analytics Platform", { size: 30, bold: true })], spacing: { after: 40 } }));
C.push(new Paragraph({ children: [r("for Karnataka State Police · State Crime Records Bureau", { size: 24, color: MUTED })], spacing: { after: 300 } }));
C.push(new Paragraph({ children: [r("End-to-End Guide — Operational and Technical", { size: 26, bold: true })], spacing: { after: 40 } }));
C.push(new Paragraph({ children: [r("Datathon 2026 · Final-day reference · 21 September 2026", { size: 20, color: MUTED })], spacing: { after: 360 } }));
const KPI = [["10,00,000", "FIRs searchable"], ["1,155", "police stations"], ["0.66 s", "mean answer time"],
             ["903", "automated tests"], ["EN + ಕನ್ನಡ", "text and voice"]];
const kw = w(1, 1, 1, 1, 1);
C.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: kw,
  borders: { top: border, bottom: border, left: border, right: border, insideHorizontal: border, insideVertical: border },
  rows: [new TableRow({ children: KPI.map(([v, l], i) => new TableCell({
    width: { size: kw[i], type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, color: "auto", fill: FILL },
    margins: { top: 120, bottom: 120, left: 80, right: 80 },
    children: [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [r(v, { size: 28, bold: true, color: TEAL })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 }, children: [r(l, { size: 16, color: MUTED })] }),
    ],
  })) })],
}));
C.push(gap(360));
C.push(new Paragraph({ children: [r("Contents", { size: 24, bold: true, color: TEAL })], spacing: { after: 80 } }));
const toc = [
  ["1", "Executive summary", "2"], ["2", "The problem and the people", "3"], ["3", "Antar's constitution", "4"],
  ["4", "Operational: an investigation, end to end", "5"], ["5", "Operational: the screens", "6"],
  ["6", "Operational: asking Antar and reading answers", "7"], ["7", "Technical: architecture", "8"],
  ["8", "Technical: how a question becomes an answer", "9"], ["9", "Technical: data, scale and performance", "10"],
  ["10", "Technical: the intelligence agents", "11"], ["11", "Governance, security and trust", "12"],
  ["12", "Requirements coverage and measured impact", "13"], ["13", "Final-day kit", "14"],
];
toc.forEach(([n, t, p]) => C.push(new Paragraph({
  children: [r(`${n}   ${t}`, { size: 20 }), new TextRun({ children: [new Tab(), p], font: FONT, size: 20, color: MUTED })],
  tabStops: [{ type: TabStopType.RIGHT, position: W, leader: "dot" }], spacing: { after: 40 },
})));
C.push(BR());

// ── PAGE 2 · EXECUTIVE SUMMARY ──────────────────────────────────────────────
C.push(...H1("1", "Executive summary"));
C.push(P("**The problem.** Karnataka's State Crime Records Bureau holds crime records from 1,100+ police stations, but officers reach them through static dashboards and manual queries. A simple question — *which district has the most kidnapping cases, and is it rising?* — needs a report request, a spreadsheet and time an officer under pressure does not have. Nothing links cases, offenders, places and money, nothing warns early, and nothing answers in Kannada."));
C.push(P("**What Antar is.** An analyst colleague that reads the FIR registry so officers don't have to. An officer asks in plain English or Kannada — typed or spoken — and gets a direct answer in under a second, with the evidence, the FIRs it came from, what it cannot see, and a next step. Behind the chat sit the Brain (full-dataset analytics and crime cycles), the Map, Predict, Search, and an Approvals flow where a supervising officer signs off any real-world action."));
C.push(H2("Why it is different"));
C.push(B("**It never answers a different question.** If Antar cannot apply part of a question — an unknown crime type, a time word, a place without the data — it says so. It never quietly widens the search and returns a confident wrong number."));
C.push(B("**Every number is traceable.** The language model never writes database queries; it picks from 19 reviewed query templates. Every answer carries an evidence class — Known, Derived, Inferred or Unknown — and its source FIRs."));
C.push(B("**The officer decides.** Antar recommends; patrol deployments and watchlist changes go to a supervising officer for approval, and every step is written to a tamper-evident audit chain."));
C.push(B("**It keeps working without the LLM.** A deterministic answer writer handles every question type, so answers stay fast and correct when the cloud model is slow or offline."));
C.push(H2("Measured impact"));
C.push(table(["What", "Before", "After"], [
  ["Searchable FIR registry", "4,25,022 rows (part cloned)", "**10,00,000** — 5.75 lakh real KSP records added"],
  ["Mean time to answer (17 representative questions)", "9.4 s (worst 57 s)", "**0.66 s** (worst 4.8 s)"],
  ["FIRs reachable by crime name", "33 crime names; 2,32,674 FIRs unreachable", "**121 concepts over all 142 crime groups**"],
  ["Silently dropped filters (wrong-question answers)", "Crime types, time words, 'absconding'", "**Refused with nearest options**"],
  ["Full Data Set table, per page", "11.2 s", "**0.005 s**"],
  ["Deployment package", "1.27 GB database", "**84 MB** (indexes self-build)"],
  ["Automated tests", "835", "**903**, incl. 51 that enforce Antar's rules"],
], w(4, 3, 4), { firstColBold: true, zebra: true }));
C.push(gap(60));
C.push(callout(["**Ready for the final:** chat (EN/ಕನ್ನಡ, voice), resolve-or-refuse, evidence classes, Expert console, Brain analytics and crime cycles, absconding accused, network analysis, HITL approvals with audit chain, observability.",
  "**In progress:** beat-level forecasting with measured accuracy (see §12–13) and the Catalyst deployment check."]));
C.push(BR());

// ── PAGE 3 · PROBLEM & PEOPLE ───────────────────────────────────────────────
C.push(...H1("2", "The problem and the people", "Designed for officers under time pressure, not for a dashboard audience."));
C.push(H2("What gets in the way today"));
C.push(table(["Gap", "What it costs an officer"], [
  ["Data sits behind reports and SQL", "Every question becomes a request to the records room and a wait."],
  ["Dashboards show what someone decided to chart", "The question actually asked usually isn't on the dashboard."],
  ["Cases, people, places and money are not linked", "Repeat offenders and organised networks stay invisible across stations and districts."],
  ["No early warning", "A rising pattern is noticed after it has happened, not while it is forming."],
  ["English-only tools", "Station staff working in Kannada are left out, or translate by hand."],
  ["No evidence trail", "A number without its source FIRs cannot go into a report, a briefing or a court file."],
], w(3, 5), { firstColBold: true, zebra: true }));
C.push(H2("Who Antar is for"));
C.push(table(["User", "What they need", "Where Antar serves them"], [
  ["**Crime Records Officer** (SCRB / DCRB analyst) — *primary*", "Exact counts, rankings, trends and case lists they can put in a report without re-checking", "Chat, Expert console, Brain, printable report"],
  ["**Station House Officer / station admin**", "What is happening in my jurisdiction and what to do next — fast", "Chat (EN/ಕನ್ನಡ, voice), Map, Predict"],
  ["**Senior officers** (SP / DCP / IGP)", "A bottom line to act on, with the evidence one tap away", "Chat bottom lines, Brain, Predict board"],
  ["**Supervising officer** (Approver role)", "Review and decide real-world actions others propose", "Approvals screen, audit chain"],
], w(3, 4, 3), { zebra: true }));
C.push(H2("Design principles that follow from this"));
C.push(B("**Answer first.** The first line answers the question as asked and can be read alone."));
C.push(B("**Show, don't claim.** Every figure links to FIRs; every judgment says what it rests on."));
C.push(B("**Say what you can't see.** Missing data is reported as missing, never as zero or as a clean record."));
C.push(B("**Both languages, same answer.** A Kannada question reaches exactly the logic its English twin does."));
C.push(B("**Humans act.** Antar proposes; a named supervising officer approves."));
C.push(BR());

// ── PAGE 4 · CONSTITUTION ───────────────────────────────────────────────────
C.push(...H1("3", "Antar's constitution", "Written in docs/ANTAR_CONSTITUTION.md and enforced in code (app/core/antar_identity.py) — not a prompt."));
C.push(P("**Identity.** Antar (ಅಂತರ್ — *within*) is the intelligence already inside the record: an analyst colleague that is confident about what the records say and plain about what they don't."));
C.push(H2("The four laws"));
C.push(table(["Law", "What it means in practice", "Enforced by"], [
  ["**1. Never answer a different question**", "A filter that cannot be applied is refused, never dropped.", "Resolve-or-refuse in the query agent"],
  ["**2. Evidence before opinion**", "Numbers only from reviewed query templates; judgments labelled with their basis.", "Template-only SQL; evidence classes"],
  ["**3. The officer decides**", "Antar informs and recommends; it never acts.", "HITL approvals"],
  ["**4. Protect the vulnerable**", "No victim identity in sexual offences or cases involving children (BNS §72, POCSO §23); no targeting individuals by caste, religion or community.", "Redaction on every answer; Vigil screening"],
], w(3, 5, 3), { zebra: true }));
C.push(H2("Evidence classes (aligned with ICD 203 analytic standards)"));
C.push(table(["Class", "Meaning", "Example"], [
  ["**K — Known**", "Read directly from a record", "5,950 kidnapping FIRs registered in Bengaluru City"],
  ["**D — Derived**", "Calculated from records: shares, rates, rankings, trends", "37% of the Karnataka total; down 9%"],
  ["**I — Inferred**", "Antar's judgment, in calibrated words, with its basis", "Likely (55–80%) to stay highest next quarter"],
  ["**U — Unknown**", "A gap — the data is absent or unrecorded", "Arrest counts aren't recorded for these FIRs"],
], w(2, 4, 5), { zebra: true }));
C.push(H2("Voice and answer template"));
C.push(B("Facts are stated as record; \"I\" appears only for limits and judgments. No salutations, no filler, exact numbers, calm register."));
C.push(B("Kannada: formal administrative Kannada; FIR, BNS/IPC sections, NDPS, POCSO, place names and numbers stay as on the FIR form."));
C.push(callout([
  "**Bottom line** — one sentence that answers the question, with the key number.",
  "**Context** — one line: direction, comparison or scope.   **Evidence** — ranked list or table (≤ 10 rows).",
  "**▸ Sources  ▸ Limits** — one tap away.   **Next** — one next step, plus 2–3 follow-ups checked against the data.",
]));
C.push(BR());

// ── PAGE 5 · INVESTIGATION END TO END ──────────────────────────────────────
C.push(...H1("4", "Operational: an investigation, end to end", "The demo story — a Crime Records Officer from question to approved action."));
C.push(table(["#", "Step", "Where", "What the officer does → what Antar returns"], [
  ["1", "**Orient**", "Chat", "*\"Which districts have the most kidnapping and abduction?\"* → Bengaluru City leads — 5,950 FIRs, 37% of Karnataka, followed by Bengaluru Dist (953) and Belagavi Dist (640); steady within ±5%. Badge: Derived."],
  ["2", "**Narrow**", "Chat", "*\"Absconding accused in Bengaluru City\"* → 66,576 live cases with accused still at large, each FIR showing \"4 of 4 accused not arrested\"."],
  ["3", "**Verify**", "Expert console", "Opens side by side (50/50). Brief with every claim's evidence class, the cited FIRs, and the agent trace with timings and integrity hash."],
  ["4", "**Connect**", "Chat · Network", "Suspect and identifier questions (shared vehicle, UPI ID, IP, accused ID across districts) → linked FIRs and the network graph with its most central members."],
  ["5", "**Pattern**", "Brain", "Full Data Set (10 lakh FIRs) and the crime-cycle clock: seasonality by crime category, by year and month, e.g. crime peaking March–August over eight complete years."],
  ["6", "**Anticipate**", "Map · Predict", "Hotspot significance (Gi*) and the prediction board with ranges and reasons; a beat-level forecast is being finalised (§12)."],
  ["7", "**Propose**", "Chat / Map → Approvals", "Officer proposes a patrol redeployment with a written justification. Vigil screens it for prohibited targeting."],
  ["8", "**Decide**", "Approvals", "A supervising officer (Approver role — never the proposer) reviews the exact, hash-pinned proposal and approves or rejects with a reason."],
  ["9", "**Record**", "Audit · Export", "Every step is on the hash-chained audit ledger; the session exports as a printable report (Print → Save as PDF)."],
], w(0.5, 1.4, 1.7, 7), { zebra: true, size: 19 }));
C.push(gap(60));
C.push(H2("Demo accounts"));
C.push(table(["Account", "Role", "Does in the story"], [
  ["**U-7001** — Operations Officer", "Admin (operations)", "Asks questions, works the case, proposes the patrol (steps 1–7)"],
  ["**U-9001** — Supervising Officer", "Approver", "Reviews and approves or rejects the proposal (step 8); cannot approve own proposals"],
], w(3, 2, 5), { zebra: true, size: 19 }));
C.push(P("Sign in with the **[ OPERATIONS ACCESS ]** or **[ APPROVER ACCESS ]** shortcut on the login screen, then Authenticate. Keep one window per account so the hand-off in steps 7–8 is live.", { before: 80 }));
C.push(gap(40));
C.push(callout(["**Where Antar says no — and why that builds trust.** *\"Absconding criminals in Indiranagar\"* → \"Accused and arrest counts aren't recorded for the 205 FIRs in Indiranagar … this is missing data, not a clean record.\" *\"How many burgalry cases\"* → \"I could not match 'burgalry'. Closest: Burglary, Burglary – Day.\""]));
C.push(BR());

// ── PAGE 6 · SCREENS ────────────────────────────────────────────────────────
C.push(...H1("5", "Operational: the screens"));
C.push(table(["Screen", "What it is for", "Key things to use"], [
  ["**Chat** (Antar)", "Ask anything about FIRs in English or Kannada, typed or spoken.", "Mic for voice · EN | ಕನ್ನಡ toggle · answer card with badge, Sources, Limits, Next · Listen, Copy, Regenerate, Export, feedback"],
  ["**Expert console**", "Analyst view beside the chat — switch on Expert mode.", "Brief (bottom line, evidence by claim K/D/I/U, ranking table) · Evidence (cited FIRs) · Trace (agent steps) · Notes · Operations queue (pattern scan, network analysis, threat assessment, OSINT)"],
  ["**Brain**", "The whole registry at a glance.", "Full Data Set: KPIs, crime categories, yearly trend, top districts, searchable FIR table (ACC-id search) · Crime-cycle clock with year and month filters · Intelligent Data constellation"],
  ["**Map**", "Where crime concentrates.", "District choropleth and drill-down · Gi* hotspot rings (statistically confirmed clusters) · heat · dark zones (where the least is known: data gaps, reporting silence, unresolved cases) · anchor areas (likely home ground of an unidentified offender)"],
  ["**Predict**", "What may come next, with reasons.", "Prediction board ranked by risk · dashboard · scenario ranges · reasoning per zone · model card"],
  ["**Search**", "Find people and identifiers across FIRs.", "Name / alias / phone / vehicle search, tolerant of spelling mistakes · profiles and linked cases"],
  ["**Approvals**", "Human-in-the-loop decisions.", "Pending proposals with justification and Vigil screen · approve / reject with reason · expiry · pending-count badge in the nav"],
  ["**Docs · About · Account**", "Guides, product story, officer session.", "Operations and Approver demo accounts"],
], w(2, 3, 6), { zebra: true, size: 19 }));
C.push(H2("Everyday conveniences"));
C.push(B("**Answer-first scrolling:** each new question pins to the top of the screen and the answer streams beneath it."));
C.push(B("**Listen to answer:** spoken in English or Kannada; shows a spinner while preparing, a stop control while playing; replays are instant."));
C.push(B("**Follow-ups remember context** within a session, and every suggested question is checked against the data before it is offered."));
C.push(BR());

// ── PAGE 7 · ASKING ANTAR ───────────────────────────────────────────────────
C.push(...H1("6", "Operational: asking Antar and reading answers"));
C.push(table(["Ask for…", "English example", "Kannada example"], [
  ["**Counts**", "How many murders in 2023?", "ನಿನ್ನೆ ಕಳ್ಳತನ ಎಷ್ಟು"],
  ["**Rankings / hotspots**", "Which district has the most narcotics cases?", "ಕಳ್ಳತನ ಎಲ್ಲಿ ಹೆಚ್ಚು"],
  ["**Trends**", "Theft trend in Mysuru City", "ದರೋಡೆ ಪ್ರವೃತ್ತಿ ತೋರಿಸಿ"],
  ["**Crime mix of a place**", "Which crime is most common in Mysuru City?", "—"],
  ["**Case lists / recent**", "Recent crimes in Belagavi Dist this week", "—"],
  ["**Absconding accused**", "Absconding accused in Bengaluru City", "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ತಲೆಮರೆಸಿಕೊಂಡ ಆರೋಪಿಗಳು"],
  ["**Outcomes**", "Conviction rate by district", "ಜಿಲ್ಲಾವಾರು ಶಿಕ್ಷೆ ಪ್ರಮಾಣ"],
  ["**Law split**", "IPC/BNS vs special and local laws", "—"],
  ["**Identifiers & people**", "FIRs linked to vehicle KA01AB1234 · history of ACC-KA-110413", "—"],
  ["**Patrol planning**", "Beat hotspots in Bengaluru City", "—"],
], w(2.4, 4.2, 3.4), { zebra: true, size: 19 }));
C.push(H2("What Antar understands"));
C.push(B("**Time:** today, yesterday, this week, last 7 / 30 days, last N weeks / months / years, this / last month or year, a named year."));
C.push(B("**Crime names:** 121 concepts covering all 142 crime groups in the registry, with everyday words (\"burglary\" covers day and night burglary; \"narcotics\" covers NDPS)."));
C.push(B("**Places:** all districts and cities in the data; Kannada place names map to the same places."));
C.push(H2("Reading an answer"));
C.push(B("**Bottom line** first, then **context** and **evidence**. The **badge** shows how the headline was obtained: Known, Derived, Inferred or Unknown."));
C.push(B("**Sources** lists the FIRs behind it; **Limits** lists anything missing (e.g. an incomplete month); **How this was answered** shows the steps."));
C.push(B("**Refusals are answers.** If a crime type, period or combination cannot be applied, Antar says so and offers the nearest valid options — it never guesses."));
C.push(callout(["**Tip for officers:** arrest and accused counts are not recorded for some areas. When Antar says data is missing, choose a district from the Karnataka registry (e.g. Bengaluru City, Mysuru City, Belagavi Dist)."]));
C.push(BR());

// ── PAGE 8 · ARCHITECTURE ───────────────────────────────────────────────────
C.push(...H1("7", "Technical: architecture"));
C.push(table(["Layer", "Components"], [
  ["**Presentation**", "Next.js 14 · React 18 · Leaflet / MapLibre maps · Recharts · SSE token streaming · bilingual UI (EN / ಕನ್ನಡ)"],
  ["**API**", "FastAPI (Python) · /api/chat/stream (Server-Sent Events) · map, predict, dataset, voice, HITL, audit, observability routes · role-based access middleware"],
  ["**Orchestration**", "LangGraph supervisor → fan-out to worker agents → synthesis. Agent fleet declared in an executable manifest (AGENTS.md) that the build verifies against the compiled graph"],
  ["**Identity layer**", "antar_identity.present(): every answer shaped to the template, evidence-classed, voice-checked and redacted before the first token streams"],
  ["**Intelligence**", "19 reviewed query templates · self-healing retrieval · Second Brain (dense + sparse hybrid search) · network analysis (NetworkX) · anomaly and hotspot engine · Dwani Kannada agent"],
  ["**Data**", "SQLite main.db: 10 lakh FIRs + official ER master tables (Act, CrimeHead, CrimeSubHead, District, Unit, Employee, Court, Rank, …) · code-owned query view · 20+ purpose-built indexes"],
  ["**Models**", "Catalyst QuickML: GLM-4.7-Flash (chat) and Qwen 3.6 35B vision-language · BAAI bge-small-en-v1.5 embeddings (384-d) · ms-marco MiniLM cross-encoder reranker · Bhashini transcription · gTTS speech"],
  ["**Governance**", "HITL approvals · SHA-256 hash-chained audit ledger · Vigil compliance screen · observability traces and evaluation set"],
], w(2, 8), { firstColFill: true, size: 19 }));
C.push(H2("Stack versions"));
C.push(table(null, [
  ["Next.js 14.2.18 · React 18.3.1", "FastAPI 0.115.5 · Uvicorn 0.32.1", "LangGraph 0.6.11 · Pydantic 2.9.2"],
  ["NetworkX 3.6.1 · scikit-learn 1.4", "sentence-transformers 3.0.1", "Leaflet 1.9 · MapLibre 5 · Recharts 3"],
], w(1, 1, 1), { size: 19 }));
C.push(H2("Deployment"));
C.push(B("**Target:** Zoho Catalyst AppSail. The database ships as a data-only **84 MB** archive, expands on first start, and builds its own indexes and query view — so the deployed index layout always matches the code."));
C.push(B("**Resilience:** the port binds immediately; heavy warm-ups (LLM token, analytics caches, every crime-graph year, heaviest queries) run in the background so the first officer never waits."));
C.push(B("**Latency guards:** every LLM call has a wall-clock budget (routing 8 s, composition 6 s, overall 20 s); on timeout the deterministic path answers."));
C.push(B("**Local / GPU path:** the template and model layers are provider-agnostic — the same pipeline runs against a local GPU-hosted model for on-premises deployment."));
C.push(BR());

// ── PAGE 9 · QUESTION → ANSWER ──────────────────────────────────────────────
C.push(...H1("8", "Technical: how a question becomes an answer", "Zero hallucination by design — the model never writes SQL and never chooses a number."));
C.push(table(["#", "Stage", "What happens"], [
  ["1", "**Language**", "Kannada detected; a Kannada→English bridge maps analytic terms so both languages reach the same logic."],
  ["2", "**Route**", "LLM selector picks one template and parameters (8 s budget); on timeout, a deterministic router takes over."],
  ["3", "**Resolve-or-refuse**", "Crime names, periods, places and qualifiers (e.g. absconding) must resolve — or the question is refused with nearest options."],
  ["4", "**Template**", "A reviewed, parameterised query — values are bound, never spliced in. Named predicates (e.g. absconding = accused not arrested in a live case) are fixed SQL fragments selected by key."],
  ["5", "**Execute**", "Indexed SQLite; results capped to today; future-dated rows never surface."],
  ["6", "**Self-heal**", "Only when a query returns nothing: repaired template → semantic recall → hybrid BM25 + dense (reciprocal rank fusion) → honest dead-end. Disabled where relaxing would change the question."],
  ["7", "**Compose**", "Deterministic writer (every template, EN + ಕನ್ನಡ) or the LLM (6 s budget) under the constitution's prompt."],
  ["8", "**Identity**", "Template shaping, evidence class, voice check, victim-identity redaction."],
  ["9", "**Deliver**", "Streamed over SSE with layout, citations, chain-of-custody and audit hash."],
], w(0.5, 2, 8), { zebra: true, size: 19 }));
C.push(H2("The 19 officer-facing templates"));
C.push(table(null, [
  ["T1 list by type / place / period", "T2 suspect by name or alias", "T3 monthly trend", "T4 top suspects in a zone"],
  ["T5 repeat offenders", "T7 victim / suspect demographics", "T8 counts by investigation status", "T9 crimes linked to a suspect"],
  ["T11 ranking by district / city", "T12 most recent crimes", "T13 crime-type breakdown", "T16 yearly summary"],
  ["T17 IPC/BNS vs special & local laws", "T18 FIRs by vehicle number", "T19 identifiers shared across districts", "T20 FIRs by UPI ID / IP address"],
  ["T21 accused history across districts", "T22 case outcomes & rates", "T23 beat / village hotspots", "T14, T15 internal (scan, map)"],
], w(1, 1, 1, 1), { size: 18 }));
C.push(BR());

// ── PAGE 10 · DATA & PERFORMANCE ────────────────────────────────────────────
C.push(...H1("9", "Technical: data, scale and performance"));
C.push(table(["Registry fact", "Value"], [
  ["FIRs", "**10,00,000** (2016–2026) — 5,74,978 real records added from the 16.7-lakh-row KSP extract, deduplicated on a 14-field signature and sampled evenly across districts and years; existing rows untouched"],
  ["Coverage", "56 district labels (41 normalised districts) · 1,155 stations · 6,384 beats · 4.42 lakh FIRs with coordinates"],
  ["Schema", "Official ER master tables: CrimeHead (99), CrimeSubHead (458), Act (138), Unit (1,056), Employee (15,585), Court, Rank, District, status and gender masters"],
  ["Crime vocabulary", "Read from the registry at start-up: 142 crime groups → 121 concepts, spelling variants merged, families expanded"],
], w(2, 8), { firstColFill: true, size: 19 }));
C.push(H2("Performance work (every rewrite verified to return identical rows)"));
C.push(table(["Change", "Why it was slow", "Result"], [
  ["LLM wall-clock budgets + startup warm-up", "Cold LLM call took 75 s; retries had no ceiling", "Worst answer 57 s → 4.8 s"],
  ["COUNT(*) instead of COUNT(column)", "Row lookup per row to test for NULL", "777 → 99 ms"],
  ["No UPPER() on date columns", "A wrapped column can't use its index", "265 → 61 ms"],
  ["Prefix LIKE → range predicate", "Function-call patterns never use an index", "5,839 → 158 ms"],
  ["Expression + covering indexes", "Filters and groupings scanned 10 lakh rows", "Ranking 798 → 94 ms; crime mix 3,210 → 117 ms"],
  ["rowid tiebreak on the date index", "Each table page sorted the whole registry", "11,230 → 5 ms per page"],
  ["Cached summaries, pre-warmed charts", "~17 scans per page visit", "10.7 s → instant after first load"],
], w(3.3, 3.7, 3), { zebra: true, size: 19 }));
C.push(H2("Data quality — handled, not hidden"));
C.push(table(null, [
  ["**Future-dated rows**", "Never surface in answers, tables or charts; they unlock automatically on their date."],
  ["**Spelling variants**", "\"CHAIN_SNATCHING\" / \"chain snatching\", \" CYBER CRIME\" / \"Cyber Crime\" merged into one concept."],
  ["**Truncated last month**", "The real record ends 10 Mar 2024; that month is excluded from trends and labelled incomplete."],
  ["**Impossible coordinates**", "14,512 FIRs carry out-of-state coordinates; the forecasting work flags and excludes them."],
  ["**Missing arrest data**", "Reported as missing (evidence class U), never as zero or as a clean record."],
], w(2.4, 7.6), { firstColFill: true, size: 19 }));
C.push(H2("Path to crores of FIRs"));
C.push(B("Materialised aggregate cubes for dashboards and forecasting; covering indexes for every template; the template layer already renders to Catalyst Data Store (ZCQL) as well as SQLite."));
C.push(B("Local GPU inference for the language model; the deterministic writer means scale never depends on LLM throughput."));
C.push(BR());

// ── PAGE 11 · AGENTS ────────────────────────────────────────────────────────
C.push(...H1("10", "Technical: the intelligence agents", "Twenty agents declared in an executable manifest — the build fails if the documentation and the running graph disagree."));
C.push(table(["Agent", "Role", "Agent", "Role"], [
  ["**Vault** (query)", "Template queries over the registry", "**Link** (network)", "Graph builder: PageRank, betweenness, k-core, communities"],
  ["**Motive** (profile)", "Suspect profiling, repeat offenders", "**Sense** (social / pattern)", "Demographic insight · MO pattern detection"],
  ["**Lens** (geo)", "Geospatial intelligence", "**Core** (forecast / predict)", "Risk forecasting"],
  ["**Beacon** (alert_suggest)", "Patrol advice from alerts", "**Scout** (OSINT)", "Open-web scan"],
  ["**Trace** (research)", "K/D/I/U dossier on a case or subject", "**Vault** (brain)", "Semantic recall over the Second Brain"],
  ["**Adversary** (adversarial audit)", "Tries to falsify a hypothesis; base-rate audit", "**A5 Vigil**", "Bias and compliance screening"],
  ["**Corridor**", "Cross-district corridor intelligence", "**Linkage**", "MO-based case matching"],
  ["**Breach** (sentinel)", "Watchlist tripwires (service)", "**Products**", "Background product compiler (service)"],
  ["**Supervisor**", "Intent classification and routing", "**Synthesize**", "Answer composition, claim verification"],
], w(2, 3, 2, 3), { size: 19 }));
C.push(H2("Key techniques"));
C.push(B("**Second Brain retrieval:** BGE-small embeddings (384-d) for meaning, Okapi BM25 for exact fragments, fused by reciprocal rank fusion, then a cross-encoder reranker — CPU-only and offline-first."));
C.push(B("**Network analysis:** NetworkX over suspects, relationships and shared identifiers (vehicle, UPI ID, IP, accused ID) to surface brokers and organised groups."));
C.push(B("**Anomaly & hotspot engine:** robust MAD z-scores, seasonal residuals, a Bayesian reporting-silence check (possible under-reporting), Getis-Ord Gi* spatial significance, split-conformal ranges and space-time clustering."));
C.push(B("**Dwani:** the Kannada language agent — transcription (Bhashini) in, Kannada answers out, with every number counted from the evidence ledger."));
C.push(B("**Adversarial audit:** challenges a working hypothesis and asks what evidence would disprove it — built-in protection against confirmation bias."));
C.push(BR());

// ── PAGE 12 · GOVERNANCE ────────────────────────────────────────────────────
C.push(...H1("11", "Governance, security and trust"));
C.push(H2("Role-based access"));
C.push(P("Six roles — Constable, Inspector, Analyst, **Approver**, Admin, Superintendent. The Approver ranks above Analyst (to read the evidence a decision rests on) and below Admin (no access to the administrative audit log). Approval rights are enforced separately from rank."));
C.push(H2("Human-in-the-loop approvals — six guarantees"));
C.push(table(null, [
  ["**1. Two people, always**", "Proposers and approvers are different roles; no one decides their own proposal."],
  ["**2. Approve exactly what was proposed**", "The proposal is SHA-256 pinned; if it changes, the approval is refused."],
  ["**3. Nothing is silent**", "A written justification to propose; a written reason to approve, reject or withdraw."],
  ["**4. Compliance first**", "Vigil screens every proposal; prohibited demographic targeting is blocked outright."],
  ["**5. Decisions expire**", "Stale proposals move to Expired and cannot be approved."],
  ["**6. Everything on the record**", "Each state change writes a hash-chained audit entry."],
], w(3, 7), { firstColFill: true, size: 19 }));
C.push(H2("Audit, privacy and observability"));
C.push(B("**Tamper-evident audit ledger:** every answer and decision is hashed and chained to the previous entry; the chain survives restarts and can be verified end to end."));
C.push(B("**Privacy:** victim identities in sexual offences and cases involving children are redacted on every answer (BNS §72, POCSO §23); personal data is redacted before any text reaches the cloud model (DPDP Act 2023 principles); no individual-level predictions."));
C.push(B("**Explainability:** citations to FIRs, evidence class per claim, a reasoning trail per answer, and a chain-of-custody strip."));
C.push(B("**Observability:** per-answer traces and spans, a trust dashboard, and an evaluation set; the test suite (903 tests) includes 51 contract tests that fail the build if Antar breaks its own rules."));
C.push(B("**Verify it live:** audit chain integrity at /api/audit/integrity (Admin) · trust dashboard at /trust · traces at /api/obs/dashboard · how any figure was derived at /api/derivation/{id}."));
C.push(B("**Standards alignment:** ICD 203 analytic standards, BLUF, NIST AI RMF and EU AI Act principles for high-risk law-enforcement AI (human oversight, logging, accuracy, transparency)."));
C.push(BR());

// ── PAGE 13 · COVERAGE & IMPACT ─────────────────────────────────────────────
C.push(...H1("12", "Requirements coverage and measured impact", "Against the Datathon solution framework. Status is stated honestly."));
const OK = "Delivered", PART = "Partial", PLAN = "In progress";
C.push(table(["Framework requirement", "Status", "How Antar meets it"], [
  ["1 Conversational interface (EN + KN, follow-ups, voice, PDF export)", OK, "Chat in both languages, session context, voice in and out, printable session report"],
  ["2 Network & relationship analysis", OK, "Network agent with centrality and communities; shared identifiers across districts (T19–T21)"],
  ["3 Pattern & trend analytics", OK, "Trends, rankings, beat hotspots, crime-cycle seasonality, Gi* clusters"],
  ["4 Sociological insights", PART, "Age / gender demographics (T7); socio-economic indicators are not in the FIR data"],
  ["5 Criminological profiling & risk", PART, "Repeat offenders, accused history, profiles; modus-operandi text is sparse in the data"],
  ["6 Investigator decision support", OK, "Case lists, K/D/I/U dossiers, similar-case linkage, adversarial-audit leads"],
  ["7 Financial crime & money trails", PART, "UPI ID / IP / vehicle links across districts; transaction data is limited"],
  ["8 Forecasting & early warning", PLAN, "Anomaly scan, Gi*, conformal ranges live; beat-level forecast with measured accuracy being finalised"],
  ["9 Explainable & transparent AI", OK, "Citations, evidence classes, reasoning trail, custody strip, model and agent traces"],
  ["10 Role-based access & governance", OK, "Six roles, HITL, hash-chained audit, privacy redaction, observability"],
], w(4.2, 1.3, 4.5), { zebra: true, size: 19 }));
C.push(H2("What changed for the officer"));
C.push(table(["Before", "With Antar"], [
  ["A records request and a wait", "An answer in under a second, with its FIRs"],
  ["A confident number that may answer a different question", "A refusal with the nearest valid options"],
  ["English dashboards", "Kannada text and voice, same logic as English"],
  ["Charts with no provenance", "Every claim labelled Known, Derived, Inferred or Unknown"],
  ["Actions taken without a record", "Two-person approval on a tamper-evident ledger"],
], w(5, 5), { zebra: true, size: 19 }));
C.push(BR());

// ── PAGE 14 · FINAL-DAY KIT ─────────────────────────────────────────────────
C.push(...H1("13", "Final-day kit"));
C.push(H2("Run of show (15–20 min)"));
C.push(table(["Min", "Beat", "Min", "Beat"], [
  ["0–2", "Problem and who it's for", "9–11", "Brain: 10 lakh FIRs, crime-cycle seasonality"],
  ["2–4", "Kidnapping ranking — bottom line, badge, followed-by", "11–13", "Network: shared identifiers across districts"],
  ["4–6", "Kannada: ನಿನ್ನೆ ಕಳ್ಳತನ ಎಷ್ಟು + Listen", "13–15", "Map / Predict: hotspots with reasons"],
  ["6–8", "Refusals: 'burgalry'; absconding in Indiranagar", "15–18", "Propose patrol → Approver approves → audit chain"],
  ["8–9", "Expert console: evidence by claim, trace", "18–20", "Close: four laws, 903 tests, scale path"],
], w(1, 4, 1, 4), { size: 19 }));
C.push(H2("Before going on stage"));
C.push(B("Open the deployed link 15 minutes early (warms the model and caches); sign in with both demo accounts in separate windows (Operations, Approver)."));
C.push(B("Ask each demo question once in advance — answers and spoken audio are then cached and instant."));
C.push(B("For arrest / absconding questions, use Karnataka districts (Bengaluru City, Mysuru City, Belagavi Dist)."));
C.push(H2("Likely judge questions"));
C.push(table(null, [
  ["**How do you stop hallucination?**", "The model never writes SQL or picks numbers; 19 reviewed templates, resolve-or-refuse, evidence classes — enforced by tests."],
  ["**What if the cloud model is down?**", "The deterministic writer answers every template in both languages; the LLM only improves wording."],
  ["**Can it scale to crores of FIRs?**", "Covering indexes, cached aggregates and cubes; ZCQL rendering for Catalyst Data Store; local GPU inference."],
  ["**Is the forecast accurate?**", "Ranges come from split-conformal intervals; beat-level accuracy is being measured with the Predictive Accuracy Index."],
  ["**Privacy?**", "Victim-identity redaction (BNS §72, POCSO §23), PII stripped before the cloud, no individual predictions, two-person approval."],
], w(3, 7), { firstColFill: true, size: 19 }));
C.push(H2("Honest notes for Q&A"));
C.push(B("The real KSP extract ends **10 March 2024**; later rows and some sub-zones (e.g. Indiranagar, Rajajinagar) are demonstration data without arrest counts — Antar says so when asked."));
C.push(B("Modus-operandi text, relationship and financial links are thin in the source extract; the pipelines are built for a full CCTNS feed."));
C.push(B("The Predict screen's model card is still a fixed description and will be regenerated from the forecast back-test — avoid opening it on stage until then."));
C.push(B("Roadmap: beat-level forecast with measured accuracy · CCTNS integration · local GPU model · full-text search · Catalyst deployment hardening."));

// ═════════════════════════════════════════════════════════════════════════════
const doc = new Document({
  creator: "Antar team", title: "Antar — End-to-End Guide", description: "Operational and technical guide, Datathon 2026",
  styles: {
    default: { document: { run: { font: FONT, size: 20, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 30, bold: true, font: FONT }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 22, bold: true, font: FONT }, paragraph: { outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } },
                                 { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 240 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 300 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1000, bottom: 900, left: 1020, right: 1020, header: 500, footer: 450 } }, titlePage: true },
    headers: {
      default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [r("Antar — End-to-End Guide", { size: 16, color: MUTED })] })] }),
      first: new Header({ children: [new Paragraph({ children: [] })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ text: "Datathon 2026 · Karnataka State Police · page ", font: FONT, size: 16, color: MUTED }),
        new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: MUTED }),
        new TextRun({ text: " of ", font: FONT, size: 16, color: MUTED }),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 16, color: MUTED }),
      ] })] }),
      first: new Footer({ children: [new Paragraph({ children: [] })] }),
    },
    children: C,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(process.argv[2], buf); console.log("written", process.argv[2], buf.length, "bytes"); });
