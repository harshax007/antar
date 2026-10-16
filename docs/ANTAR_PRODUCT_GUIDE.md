# Antar — Product Guide

**Every screen, every feature, and how it works — in plain English, no code.**

| | |
|---|---|
| Who this is for | Anyone on the team: pitch, demo, design, product, new developers on day one |
| What it covers | Every screen from login to About, what you see, what you can do, and what happens behind it |
| Snapshot | Antar build of 15 September 2026 |
| Data | All crime data is synthetic (Datathon 2026). 425,015 FIR records. |
| Deeper technical detail | `docs/ANTAR_HANDBOOK.md` · Planned fixes: `docs/fixPlan.md` |

---

## Contents

1. [Antar in one page](#1-antar-in-one-page)
2. [The ideas that make Antar trustworthy](#2-the-ideas-that-make-antar-trustworthy)
3. [Getting around](#3-getting-around)
4. [Login](#4-login)
5. [Chat — ask anything](#5-chat--ask-anything)
6. [Expert Workspace](#6-expert-workspace)
7. [Brain — the evidence globe and data overview](#7-brain--the-evidence-globe-and-data-overview)
8. [Map — hotspots, heat and movement](#8-map--hotspots-heat-and-movement)
9. [Predict — what's likely in the next 7 days](#9-predict--whats-likely-in-the-next-7-days)
10. [Search — find a person](#10-search--find-a-person)
11. [Docs — the live product tour](#11-docs--the-live-product-tour)
12. [Trace & Telemetry — checking the AI's work](#12-trace--telemetry--checking-the-ais-work)
13. [Account — settings, briefings, uploads, audit](#13-account--settings-briefings-uploads-audit)
14. [About](#14-about)
15. [Older screens still available](#15-older-screens-still-available)
16. [Things that work quietly in the background](#16-things-that-work-quietly-in-the-background)
17. [Kannada and voice](#17-kannada-and-voice)
18. [Safety, privacy and fairness](#18-safety-privacy-and-fairness)
19. [Demo script: questions that show every feature](#19-demo-script-questions-that-show-every-feature)
20. [Frequently asked questions](#20-frequently-asked-questions)
21. [Current limitations](#21-current-limitations)
22. [Glossary](#22-glossary)

---

## 1. Antar in one page

**The problem.** Karnataka has hundreds of thousands of FIRs (First Information Reports). An officer on night shift can't "just ask" them a question — not in Kannada, not without an analyst, and not in time to act.

**What Antar does.** It lets an officer ask a question in plain English or Kannada and get an answer in seconds. Every number in the answer can be traced back to real records.

**Three things it helps with**

| Pillar | Question it answers | Where you'll see it |
|---|---|---|
| **Think** | "What do the records say?" | Chat, Expert Workspace, Docs |
| **Connect** | "Who and what is linked?" | Brain, Search, network views |
| **Anticipate** | "What's likely next, and where?" | Predict, Map, alerts |

**The journey of one question, in 7 steps**

1. The officer types or speaks a question.
2. A compliance check makes sure the question doesn't target a caste, religion or community.
3. Antar works out what kind of question it is and picks one of 19 pre-approved database questions ("templates").
4. That approved question runs against the records and returns real rows.
5. Specialist helpers ("agents") add extra views if needed — a map, a network, a forecast.
6. The answer is written from those rows: the direct answer first, then the evidence.
7. The whole exchange is sealed into a tamper-evident log and recorded for quality checks.

---

## 2. The ideas that make Antar trustworthy

These six ideas explain almost every design decision in the product.

### 2.1 The AI never writes database queries

Think of a receptionist who can only hand over forms from a locked drawer and fill in the blanks. The receptionist (the router or AI) chooses a form ("most cases by district") and fills in "cyber crime". The clerk (Antar's own code) runs the form. The receptionist never touches the records.

This is why Antar can't invent a number: the number comes from the database, not from the AI's imagination.

### 2.2 Answer first, proof second

Every answer opens with one sentence you could read aloud to a superior:

> Bengaluru City has the most cyber crime cases — 42,701 FIRs, 86% of the Karnataka total (across all years on record).

Then comes the direction of change, then the ranked list, then the sources.

### 2.3 Honest when there's nothing

- If nothing matches, Antar says so first: "No matching records found."
- If you name a person or ID that isn't in the results, it says: "No record matching 'X' was found. The following is related context, not a match."
- If you look up a UPI ID or vehicle with no FIRs, "not on record" *is* the verified answer.
- If a helper fails, the screen says it's unavailable — it never fills the gap with made-up data.

### 2.4 Every statement carries a label

| Label | Letter | Meaning | Example |
|---|---|---|---|
| Verified | **K** (Known) | Read straight from a record | "No FIR on record mentions this vehicle." |
| Computed | **D** (Derived) | Counted or calculated from records | "Bengaluru City has 26,334 theft FIRs." |
| Inferred | **I** | A scored guess that needs a human to confirm | "These two suspects are likely the same person (79%)." |
| Gap | **U** (Unknown) | Something missing, with how to get it | "No phone records on file — issue a Section 91 notice." |

### 2.5 Nothing can be quietly edited later

Every question, answer and important action is written into a log where each entry is fingerprinted together with the previous entry. Change one old entry and every fingerprint after it stops matching. Printed reports carry their own fingerprint ("seal").

### 2.6 It works without the AI model

Antar runs in two modes:

| Mode | When | What happens |
|---|---|---|
| **Offline** | No AI model connected (or it's slow/failing) | Rules route the question; answers are written by fixed templates. Fully predictable. |
| **AI-assisted** | AI model connected | Rules still go first; the AI only helps with unclear questions and phrasing for a few answer types. |

A **demo mode** also exists that replays saved answers for scripted demo questions, so a live demo looks the same every time.

---

## 3. Getting around

**Top navigation bar** (always visible):

| Left group | Right group |
|---|---|
| Chat · Brain · Map · Predict · Search | Account · Docs · About · (collapse button) |

**Other things that appear on every screen**

| Element | What it does |
|---|---|
| **Language switch (EN / ಕನ್ನಡ)** | Changes the whole interface and all answers to English or Kannada |
| **Help button (?)** | Opens a guide for the current screen: what it's for, how to read it, example questions |
| **Screen transition** | A short animation when you move between the five main screens |
| **Demo launcher** | Shortcuts that jump into prepared feature demos |

**Where things are saved**

| What | Where it lives | Lasts |
|---|---|---|
| Your login | This browser tab | Until you close the tab or sign out |
| Chat conversation | The server's memory | Until the server restarts (use Save to keep it) |
| Saved sessions | Encrypted files on the server | Permanently |
| Your preferences, bookmarks, notes | Officer memory in the database | Permanently |
| Recent questions | Your browser | Permanently on this device |

---

## 4. Login

**What you see:** Antar logo, "Think. Connect. Anticipate.", a clock, User ID and Password fields.

**How it works today (demo login)**

1. Enter any user ID and any password.
2. A short "Verifying credentials…" step runs.
3. If your ID starts with **A-** (for example `A-001`), you're an **Admin**. Anything else (for example `U-7001`) is an **Officer**.
4. You land in Chat.

**What the role changes**

| Feature | Officer | Admin |
|---|---|---|
| Chat, Brain, Map, Predict, Search | Yes | Yes |
| OSINT (open-web search) | No | Yes |
| Full audit log | No (access denied, on purpose) | Yes |
| Expert Workspace background jobs | Limited | Full |

> Real password checking (Catalyst Auth) is planned; today's login is for demos only.

Visiting the site's root address always clears the session and returns you to Login.

---

## 5. Chat — ask anything

**Address:** `/antar` · **Purpose:** ask a question about the FIR records and get a trustworthy answer.

### 5.1 What you see

| Area | What it shows |
|---|---|
| Conversation | Your questions on the right, Antar's answers on the left |
| Composer (bottom) | Text box "Ask anything you want…", microphone, send button, **Expert** toggle, model/system label |
| New Session | Starts a fresh conversation |
| Under each answer | Action buttons: retry, copy, listen, export, open map, thumbs up, thumbs down |

### 5.2 Anatomy of an answer

Reading top to bottom:

| Part | Meaning |
|---|---|
| **"Thought for 2.7s"** | How long the answer took. Click it to see every step. |
| **Agent steps** | Live progress while it works: "Analyzing your query…", "Searching crime database…", "Found 10 records → template T11", "Composing answer…" |
| **Lead sentence** | The direct answer with the key number |
| **Direction** | Whether it's rising, falling or steady compared with recent months |
| **Ranked list** | The top places, people or types with counts and shares |
| **Show full answer** | Long answers are collapsed; click to expand |
| **Mini chart** | A small bar or line chart when the answer is a ranking or trend |
| **Sources** | Citation chips: FIR number, police station, date, legal section |
| **Chain of custody** | How many records were used, from which table, over what dates, and by which method |
| **Confidence** | High / Moderate / Low, with a note to verify with source FIRs when low |
| **Why?** | The reasoning trail: which template, which filters, how many rows |
| **Suggested questions** | Three follow-ups — each one is tested against the database first, so it always has an answer |
| **Action chips** | Jump to Map, Network, Profile or Alerts for this answer |

### 5.3 How a question becomes an answer

1. **Compliance check (Vigil).** The question is scanned for prohibited targeting or bulk personal-data requests. You get a receipt: Approved, Flagged or Rejected.
2. **Understanding.** Antar spots the kind of question from keywords in English or Kannada:
   - an exact ID (accused ID, UPI, IP address, vehicle plate, suspect ID) wins first,
   - then words like "most", "trend", "how many", "recent", "beats", "conviction rate",
   - plus places ("Bengaluru City", "ಬೆಂಗಳೂರು ನಗರ"), crime types ("theft", "ಕಳ್ಳತನ") and time ("last month", "2023").
   - It also remembers your previous question, so "and in Mysuru?" keeps the crime type.
3. **Picking a template.** It chooses one of the approved questions — for example "rank districts by number of cases" — and fills in the details.
4. **Running it.** The template runs on the records. Records dated after today are always excluded.
5. **Self-repair if empty.** If nothing comes back, Antar tries, in order: a better-fitting template → loosening the filters (status, then date, then place, then crime type) → searching past cases by meaning → searching by keywords. Anything found this way is clearly labelled "closest related records". If still nothing, it says so and suggests what to change.
6. **Extra helpers in parallel.** Depending on the question, specialists join in: map (hotspots and patrol tip), network (who's connected), profile (risk score), pattern (clusters), prediction (7-day risk), alerts (unusual activity). Each has a time limit; a slow one is reported as unavailable rather than holding up the answer.
7. **Memory check.** Antar's "Second Brain" looks for past investigations that are genuinely similar (only strong matches are shown).
8. **Writing.** A fixed writer turns the rows into the answer (lead sentence, direction, list). The AI model is only used for question types with no fixed writer, and even then a checker removes any number or ID that isn't in the rows.
9. **Streaming.** Words appear as they're ready, followed by sources, visuals, confidence and suggestions.
10. **Sealing.** The exchange is added to the tamper-evident log and to Trace & Telemetry.

### 5.4 Types of questions Antar understands

| You ask | Example | You get |
|---|---|---|
| A list of cases | "chain snatching in Rajajinagar last month" | Matching FIRs with station, date and section |
| A count | "how many murders in Bengaluru City?" | The number, with scope |
| Who has the most | "which zones have the most cyber crime?" | Top place, count, share, ranked list |
| The least | "least crime district" | Lowest-ranked places |
| A trend | "theft trend in Bengaluru City" | Rising / falling / steady, month by month, peak |
| Next month | "predict theft next month in Bengaluru City" | Estimate from the last three full months, with range |
| Crime mix | "which crime types are most common?" | Top crime types with shares |
| Case status | "open theft cases by status in 2024" | Counts by investigation stage |
| Recent cases | "recent burglary cases in Whitefield" | Latest FIRs |
| Repeat offenders | "who are the repeat offenders?" | People with 5+ prior offences |
| A person | "who is Raju K?" / "find suspect Yellappa" | Matching suspects with aliases |
| A person's cases | "what crimes is S0001 linked to?" | All linked FIRs |
| Top suspects in an area | "top suspects in Rajajinagar" | People linked to the most cases there |
| Demographics | "victim gender breakdown" | Aggregate breakdown with a fairness note |
| A year | "Cognizable FIRs registered in Karnataka in 2022?" | Year total and highlights, or year-on-year comparison |
| Law split | "IPC/BNS vs SLL split for 2023?" | Cases by type of law |
| A vehicle | "check if vehicle KA-02-M-2093 has any FIRs" | Every FIR naming it, or "not on record" |
| Money or devices across districts | "which UPI IDs are used in more than one district?" | UPI IDs/IPs/vehicles/accused spanning several districts |
| One UPI or IP | "FIRs for UPI user1101@bank" | Every FIR with it |
| One accused's history | "cases for accused ACC-KA-500777" | Where, what, and how the cases ended |
| Case outcomes | "conviction rate by district in 2023" | Conviction, charge-sheet, arrest and undetected rates |
| Patrol beats | "top beats for theft in Bengaluru City" | Busiest beats with their police station |
| Villages/areas | "which villages in Mysuru Dist have the most crime?" | Busiest villages or areas |

If a trend or hotspot question has no crime type ("what is the trend?"), Antar asks which crime you mean. Off-topic questions get a polite redirect with example questions.

### 5.5 Shortcuts

| Type | What happens |
|---|---|
| `/think <question>` | Deeper analysis with the full reasoning trail |
| `/connect <question>` | Adds the network and profile helpers — who is linked to whom |
| `/anticipate <question>` | Adds the map, prediction and pattern helpers — what's likely next |
| `why?` or `explain` (or ಯಾಕೆ) | Replays exactly how the previous answer was reached |

### 5.6 Controls

| Control | What it does |
|---|---|
| **Microphone** | Speak in English or Kannada; your words fill the box |
| **Listen** | Reads the answer aloud (automatic when you spoke the question or use Kannada) |
| **Translate** | Flips one answer between English and Kannada, keeping FIR numbers and IDs unchanged |
| **Export** | Opens a printable, sealed report of the whole session |
| **Save session** | Stores the conversation encrypted on the server |
| **Thumbs up / down** | Rates the answer; ratings are logged for quality review |
| **Expert** | Opens the Expert Workspace beside the chat and adds deeper analysis |
| **Stop** | Stops an answer mid-stream; what arrived so far is kept |

### 5.7 The printable report

Clicking Export opens a page designed for A4 printing:

- A header with session, officer, time generated, and number of questions.
- For each question: the question, the answer, the method used, records used, confidence, response time, engine, helpers used, language, officer, and the log fingerprint.
- A table of cited FIRs and the reasoning steps.
- A "digital watermark" box with the document's fingerprint (SHA-256), proving it wasn't changed after printing.

The print dialog opens automatically so you can save it as a PDF.

---

## 6. Expert Workspace

**Where:** the panel that opens on the right of Chat when **Expert** is on.
**Purpose:** turn the current answer into a working intelligence document, and run heavier analysis without blocking the chat.

### 6.1 What you see

| Area | What it's for |
|---|---|
| Header buttons | **Expand** (full width), **Guide**, **Export**, **Close** |
| Document | The current answer as an editable document: title, body, highlighted numbers |
| Edit / Publish | Edit the text, then publish it as a read-only intelligence record |
| References | Numbered citations: FIR, station, section, date |
| Persistent notes & annotations | Notes you add; each is also saved into your long-term officer memory |
| Background jobs | Launch and watch long-running analyses |

### 6.2 Background jobs

| Job | What it produces |
|---|---|
| Deep research | A four-part dossier (Known / Derived / Inferred / Gaps) on a person, place or FIR |
| Recompile board | Rebuilds the whole 7-day prediction board |
| Pattern scan | Finds space-and-time crime clusters |
| Network deep dive | Builds a person's full network |
| Threat assessment | Patrol and checkpoint recommendations from current alerts |
| OSINT recon | Open-web reconnaissance (results always marked unverified) |
| Corridor analysis | Offender movement between districts |
| Shift briefing | A shift summary for a station or district |
| Custom | Runs your own instruction through the question pipeline |

**How jobs work:** you launch one → it's queued and runs in the background → the list shows queued / running / done / failed → when it finishes, your next chat answer shows a "Background investigation completed" banner with an "Open in Workspace" button. You can cancel any running job.

### 6.3 How the deep-research dossier is built

1. **Known:** facts copied from records about the person, their cases and places.
2. **Derived:** calculated facts — risk score, how many associates, movement corridors.
3. **Inferred:** pairs of people who might be linked or be the same person, scored from clues:
   - same phone, vehicle or UPI (strongest clue),
   - names that sound alike,
   - accused together in the same case,
   - same area,
   - same method of crime.
   Only pairs scoring at least 55% are shown, and never more than 97% — it's never "certain".
4. **Gaps:** what's missing (no phone records, no vehicle, unsolved FIR with no accused) and the exact action to collect it.

> A planned redesign makes the workspace read like a real document (question, summary, trend, ranking table, references, method, notes). See `docs/fixPlan.md`.

---

## 7. Brain — the evidence globe and data overview

**Address:** `/antarBrain` · **Purpose:** see how cases connect, and explore the whole dataset.

The Brain screen has two pages stacked vertically — use **Top brain** and **Bottom data overview** (bottom right) to jump between them.

### 7.1 Page 1 — the brain

Three views, chosen at the top left:

| View | What it shows |
|---|---|
| **All Data** | Every linked FIR as a glowing point on a 3D globe, grouped by crime category |
| **Focus** | One linked group at a time — the people and cases tied together |
| **Crime Graph** | A year-clock showing when each crime category peaks |

**How the globe is built**

1. Antar loads a curated set of densely linked FIRs (about 5,400 records chosen because they share keys).
2. Each FIR is placed in one of 13 colour-coded categories (property, crimes against women, cyber, violent, crimes against children, missing persons, economic offences, narcotics, and more).
3. Lines are drawn **only** when two FIRs share something real:
   - **Repeat offender** — the same accused person,
   - **Ring** — the same place or vehicle,
   - **Cyber** — the same UPI ID or IP address,
   - **Predicted link** — an inferred connection (clearly marked),
   - **Unknown offender cluster** — unsolved cases grouped by pattern.
4. Hover or click any line and it tells you *why* it exists ("Repeat offender: same accused — ACC-…").
5. Named hubs (big connectors) are labelled; Antar's agents appear as their own small cluster.
6. The graph is cached in your browser so it appears instantly next time.

**Controls:** drag to rotate, scroll or pinch to zoom, click a point to focus it, switch 3D/2D, filter by crime type, district, year or FIR range, and **Ask Antar →** to send the selection to Chat.

**Case activity calendar:** a daily heat calendar for a chosen year. Brighter days had more FIRs. It can use the full dataset or only the linked records.

**Focus panel** for a selected group: what category it is, how many FIRs, the people involved, the key linking evidence, a crime-mix donut, and "Why these are connected".

### 7.2 Crime Graph — the year clock

**How to read it**

- The ring is a calendar: January at the top, months running clockwise.
- Each coloured wave is one crime category.
- The further a wave bulges out at a point, the more FIRs that category had at that time of year.
- The year is split into 36 slices (about every 10 days), so seasonal peaks (festivals, holidays) stand out.
- The centre shows the total FIR records for the selected year.
- Click a wave or legend entry to isolate it and see its peak month, quietest month, change from last year, top districts and top crime heads.
- Year buttons along the bottom switch the year; **All** shows every year.

> Known issue being fixed: the centre currently shows **307,451** because it scales a sample up to an old total. The correct full-dataset total is **425,015**. The fix counts the real records directly (see `docs/fixPlan.md` §1).

### 7.3 Page 2 — FIR data overview

A dashboard of the dataset, switchable between **Intelligent Data** (the linked records) and **Full Data Set** (all 425,015 FIRs).

| Section | Shows |
|---|---|
| Headline figures | FIRs, districts, stations, victims, accused, arrested, charge-sheeted, convictions, arrest rate |
| By crime category | Bar chart; click a bar to filter |
| Investigation stage | Under investigation, pending trial, convicted, disposed… |
| Yearly trend | FIRs per year; click a year to filter |
| Top districts | Busiest districts; click to filter |
| Records table | 50 FIRs per page, searchable by district, station, crime, place; shows vehicle, UPI, IP and accused links |
| Filters | Year range, FIR range, accused ID |

Clicking something on the overview also updates the globe above, and filters set on the globe update the overview.

---

## 8. Map — hotspots, heat and movement

**Address:** `/map` · **Purpose:** see *where* crime concentrates across Karnataka's districts, whether that concentration is statistically real, and where patrols should go.

### 8.1 What you see

| Area | What it's for |
|---|---|
| **Crime type pills** (top) | All crimes, Theft, Robbery, Chain-snatching, Burglary, Vehicle theft, More… |
| **Calendar** (left) | Pick the date the analysis ends on; "Today" jumps back |
| **Karnataka map** | District outlines shaded by crime load, with hotspot markers and layers |
| **District card** (right) | Details for the district you click |
| **District list / report** | Ranked districts and a Karnataka crime report |
| **Corridors dossier** | Offender movement between districts and unknown-offender anchor areas |
| **Help (?)** | Map guide |

### 8.2 How the heat map works

The map combines several layers, each answering a different question.

**Layer 1 — District shading (how much crime?)**

1. When the server starts, it pre-counts FIRs per district: this month, last month, top crime types, and a risk level.
2. Each district is shaded from dark (few FIRs) to bright (many FIRs).
3. Because the counts are prepared in advance, clicking around is instant.

Risk level for a district:

| Level | Rule |
|---|---|
| High | 80+ FIRs this month, or 50% more than last month |
| Medium | 30+ FIRs this month, or 10% more than last month |
| Low | Otherwise |

**Layer 2 — Heat points (where exactly?)**

Individual FIR locations are sampled (up to 5,000 points) and drawn as a glow. Many cases close together make a bright patch. You can filter by crime type and by last 7 days, this month or last 3 months.

**Layer 3 — Hotspot significance, "Gi\*" (is this hotspot real or just a big city?)**

A big district always has more crime, so brightness alone can mislead. The hotspot test asks a fairer question: *is this district and its neighbours hotter than the state average?*

1. Take a window — 30 days ending on the date you picked in the calendar (never after today).
2. Count crimes in every district.
3. For each district, look at itself plus every district within 25 km.
4. Compare that neighbourhood's total with what you'd expect from the state average.
5. Turn the difference into a score and a probability that it happened by chance.

| Result | Shown as | Meaning |
|---|---|---|
| Probability under 5% and above average | **Red ring** — confirmed hotspot | A real, statistically significant cluster that needs attention now |
| Above average but not significant | Warm / cyan | Emerging or scattered pattern to watch |
| Below average | Cool | Quieter than its neighbours |

**Layer 4 — Predicted (next 7 days)**

1. Find the three districts with the most crime so far this month.
2. Draw density contours around the last 60 days of incidents there.
3. Add a patrol suggestion: "Surge detected (N cases). Increase patrols in X."

**Layer 5 — Suggested patrol**

A pulsing ring marks the single densest area of the past two weeks with a concrete patrol tip.

**Layer 6 — Crime flow / corridors (who moves between districts?)**

1. Antar looks for the same accused person appearing in FIRs from two different districts.
2. Each such pair of districts becomes a **corridor**; arcs connect them on the map.
3. Thicker arcs mean more offenders link the two districts.
4. Each corridor lists linked offenders, FIR count, days since last activity, and the most likely next district.
5. This layer is off by default and switched on when needed.

**Layer 7 — Unknown-offender anchor areas**

Unsolved cases of the same type in the same area are grouped into "unknown subject" series. Antar draws an outline around their locations to show the likely operating area.

**Layer 8 — Dark zones ("where do we know the least?")**

Areas where many cases have accused who were never charge-sheeted, or reporting has gone unusually quiet. These are intelligence gaps, not safe areas.

### 8.3 The district card

Click a district to see: FIRs in the last 30 days, this month versus last month, trend percentage, top crime types, open or unsolved share, risk index, hotspot status, predicted next 7 days, and a suggested patrol action.

### 8.4 The 3D globe

The map can also show Karnataka on a 3D globe: districts light up by FIR load, hotspot points rise from the surface, hexagon heat columns show density, and animated arcs show corridors. It starts over Karnataka and rotates slowly until you grab it.

> Known issue being fixed: the corridors dossier currently opens underneath the crime-type pills and calendar, so its title overlaps. See `docs/fixPlan.md` §4.

---

## 9. Predict — what's likely in the next 7 days

**Address:** `/predict` · **Purpose:** show where risk is rising, why, and how sure Antar is — before it happens.

### 9.1 What you see

| Area | What it shows |
|---|---|
| **Forecast board** | One card per district: crime type, risk (High / Medium / Low), confidence, expected number of incidents, and why |
| **Antar Alert** | Unusual activity detected this week (spikes and sudden silences) |
| **Incident volume trend** | Monthly or yearly incident totals with the latest value and change |
| **Activity heatmap** | Top crime types across recent months |
| **Prediction explanation** | For the selected card: the reasoning graph and step-by-step trace |
| **Scenario band** | "What if a suspected link is true?" — a second range shown beside the normal one |
| **Warning ledger** | Every warning stored with the records it was based on |
| **Hypotheses engine** | Suspected links to confirm or reject |
| **Model card** | What the model is for, its limits and bias disclosures |

### 9.2 How the 7-day forecast works

**Step 1 — Look for unusual weeks (the alert scan).** For every crime type in every district:

1. Count cases per week for the last 14 weeks.
2. Compare this week with the previous 13 using the **median** (the middle value), not the average — so one old spike can't hide a new one.
3. Allow for seasons: festivals naturally raise crime, so Antar removes the normal seasonal lift before judging.
4. Check whether the district is a real hotspot compared with its neighbours (the same test as the Map).
5. Check for **silence**: a normally busy series that suddenly goes quiet could mean under-reporting or displacement.
6. Work out an honest range for next week that should contain the true number about 90% of the time.
7. Combine into an anomaly score (0–10) and a confidence (between 50% and 99% — never 100%).

A week is flagged when it's about two "typical deviations" above normal with at least 4 cases (a **spike**), or sharply below a normally busy level (a **silence**).

**Step 2 — Forecast each district.** For each district and its main crime type:

1. Count cases per week over the last 52 weeks.
2. Measure how bunched-up the cases are — crime concentrated in a few weeks is a warning sign.
3. Check for a **live cluster**: several cases close together in both place (about 2 km) and time (about a week) in the last 7 days.
4. Forecast next week by following the recent level and trend, with the trend gently flattened so one bad week doesn't produce an absurd prediction.
5. Decide the risk:

| Risk | When |
|---|---|
| **High** (Critical) | Cases are unusually concentrated in a few weeks |
| **High** | A live cluster exists **and** the forecast is 20% above the recent weekly average |
| **Medium** (Elevated) | A live cluster exists **or** the forecast is above zero |
| **Low** | Neither |

**Step 3 — Build the board.**

1. Every district that had an alert gets a card from its strongest alert.
2. Every other district with data gets a baseline card.
3. Cards are sorted High → Medium → Low.
4. Each card says "next 7 days" and is stamped with today's date. Antar never shows a specific future date — only relative windows.
5. The board is stored and refreshed automatically.

**What a card tells you**

| Field | Meaning |
|---|---|
| Risk | High / Medium / Low |
| Confidence | How sure the model is |
| Expected window | "3–15 incidents" — the likely range |
| Why | The drivers in plain words: "unusual jump", "confirmed hotspot", "active cluster", "seasonal uplift +40%", or "trend baseline — no anomaly" |
| Direction | Spike, silence, or baseline |
| Evidence rows | The FIRs the warning is based on (stored for audit) |

### 9.3 The explanation graph

Click a card to see the actual run for that district as a flow diagram:

> FIR data (how many rows) → Seasonal signal → Pattern helper (cluster found or not) → Forecast helper (range and score) → Network helper (most-linked local offender) → Supervisor (drivers weighed) → **Prediction** (risk, confidence, district)

Every label shows real numbers from that run, and a written trace lists each step. **Derivation audit** opens a printable, sealed record of how the prediction was produced.

### 9.4 Scenario bands

If investigators suspect something — for example an offender corridor is active — Antar shows a second range ("if this is true, expect X–Y incidents"). It is always marked **Inferred**, shown in purple, and never shown without the normal range beside it.

### 9.5 Monthly volume and activity cards

- **Volume:** incidents per month (or year) with the latest complete month, previous month, change percentage, peak and average. Months still in progress are left out so the latest figure isn't artificially low.
- **Activity heatmap:** top crime types (rows) by recent months (columns); darker cells mean more incidents.

### 9.6 When the server is offline

The screen says so and shows a clearly labelled **sample** so the layout can still be demonstrated. It never passes the sample off as live data.

---

## 10. Search — find a person

**Address:** `/search` · **Purpose:** find suspects by name, alias, father's name or phone — even with spelling mistakes — and see their profile.

### 10.1 What you see

| Area | What it shows |
|---|---|
| Search box + microphone | Type or speak a name |
| Field filters | All · Name · Alias · Father (s/o) · Phone |
| Identity hypotheses | "These two records may be the same person" cards with Confirm / Reject |
| Results list | Matches with avatar, alias, district, FIR count, match type, risk |
| Profile panel | Details of the selected person |

### 10.2 How matching works

1. **Exact and partial text** — "Raju" finds "Raju K."
2. **Typos** — similarity scoring means "Yelapa" still finds "Yellappa".
3. **Sound-alike** — names that sound the same match across spellings ("Yellappa", "Yellapa", "Ylappa").
4. **Aliases** — a known alias leads to the same person.
5. **Two data sources at once** — named suspects and accused IDs from the evidence records are searched together.
6. Results are sorted by risk; each shows why it matched (exact, alias, phonetic, typo).

**When nothing matches:** Antar lowers the bar to suggest the nearest names, shows unsolved case series that match the words, and offers **Track this lead**, which records the unknown lead as a formal gap to follow up.

### 10.3 The profile panel

| Section | What it tells you |
|---|---|
| Identity | Name, alias, gender, age, area, status (for example "released on bail") |
| **Risk breakdown** | Four bars that explain the risk score |
| Known associates | People directly linked in the relationship records |
| Second Brain · linked cases | Similar past investigations |
| Modus operandi | How many linked cases, main crime types and places, prior count, arrest status |
| Leads | Suggested next steps (cross-case link to check, phone records to request, CCTV corridors) |

**How the risk score works (0–100)**

| Factor | Weight | What it measures |
|---|---|---|
| Recency | 30% | How recently the person was linked to a case |
| Frequency | 25% | How many cases they're linked to |
| Severity | 25% | The most serious crime they're linked to |
| Centrality | 20% | How connected they are in the network |

Each factor is scaled against everyone else, then added up. Because it's a simple weighted sum, the bars show exactly how much each factor contributed — for example Raju K. scores 52.2: recency +30, centrality +20, frequency +2.2, severity 0. It's a way to prioritise attention, not a prediction of guilt, and the text is automatically checked for biased terms.

### 10.4 Identity hypotheses

Antar compares records and suggests when two may be the same person — for example, "Raju K. (S0001) ≈ Yellappa M. (S0002), confidence 79%, shared phone". An inspector or higher can **Confirm** (the link becomes institutional memory) or **Reject** (Antar remembers not to suggest it again). Both decisions are logged.

### 10.5 OSINT (open-web search)

**Who can use it:** Admins only.

**How it works**

1. The admin turns OSINT mode on and accepts the consent notice.
2. A banner stays visible: "OSINT mode active · all queries are logged & audited · inferred data is never treated as verified".
3. Antar searches the public web for the name alongside words like "crime", "arrest", "suspect", and runs a recon report: a linkage graph, phone footprint, public handles and a scan timeline.
4. Everything found is **quarantined** — marked unverified and never merged into official records.
5. Findings are compared against internal records to show which, if any, are corroborated.

> Known issue being fixed: OSINT only appears for Admin logins *and* after a hidden toggle, so most users never see it. Associates are often empty because few relationships are recorded, and Confirm/Reject currently fails. See `docs/fixPlan.md` §5.

---

## 11. Docs — the live product tour

**Address:** `/docs` · **Purpose:** show what Antar does using real data, not slides.

**How it works**

1. The page opens with an animated title and picks a question from a bank of 50 prepared questions (English and Kannada), rotating so repeat visits show different ones.
2. It sends the **same question** through all three modes at once:
   - **Think** — deep reasoning,
   - **Connect** — links and network,
   - **Anticipate** — forecasts and hotspots.
3. Each mode plays in its own stage: a live terminal showing the real agent steps on the left, a small 3D icon animation on the right.
4. Answers type out as they arrive; results are cached for the browser tab so replays are instant.
5. A wrap-up shows real counts rising to their final values and buttons to continue in Chat.

If the backend is unavailable, each stage shows "offline" instead of a fake answer.

---

## 12. Trace & Telemetry — checking the AI's work

**Address:** `/trace` · **Purpose:** let supervisors and the team audit exactly what happened for every question — what ran, what data came back, how long it took, and whether anything looked wrong.

### 12.1 What it records for every question (a "trace")

| Recorded | Example |
|---|---|
| The question (personal numbers masked) | "which zones have the most cyber crime" |
| Session and language | Which conversation it belongs to, English or Kannada |
| Route | Which template and which helpers ran |
| Evidence | How many rows came back and which FIR numbers |
| Citations | The sources attached |
| The answer (masked) | What the officer saw |
| Engine | AI-assisted, offline, demo, or guardrail |
| Timing | Total response time and each step's time |
| AI usage | Model name, tokens in and out, retries, errors, and the exact prompt sent |
| Flags | Any automatic rule that fired |
| Judge score | A quality grade, if reviewed |

Personal numbers like Aadhaar and phone numbers are masked to their last 4 digits **before** anything is stored; FIR and vehicle numbers are kept intact so they can be looked up.

### 12.2 How it works, step by step

1. **A trace starts** the moment a question arrives.
2. **Every helper step is added** as it happens (for example "query · T11 · 10 rows · 420 ms"). Steps are written to a simple append-only log file.
3. **AI calls are recorded** — model, tokens, time, retries and the masked prompt.
4. **When the answer is ready, the trace closes** and is saved to the observability database.
5. **Automatic rules run on 100% of traces** (free and instant):

| Rule | Flags when | Severity |
|---|---|---|
| F1 | The answer states a number or FIR but no rows or citations back it | High |
| F2 | A person or ID the officer named isn't in the results | High |
| F3 | The response was more than twice as slow as normal | Medium |
| F5 | No rows came back but the answer doesn't admit it | High |
| F6 | The AI was expected but the answer came from the offline fallback | Medium |
| F7 | A guardrail had to remove something from the answer | Medium |

6. **"Normal" speed is learned** — Antar keeps a rolling picture of typical response times, so "slow" is judged against real history.
7. **Flagged traces, plus a random 5% of the rest, are queued for the judge.** A separate background process asks the AI to grade each one on four scores: groundedness (does it use only the rows?), answered (does it actually answer?), hallucination (did it invent anything?), and safety. Judging never slows down the officer's answer.
8. **Ordinary web requests** (loading a map, fetching a list) are also recorded for speed monitoring, but kept separate so they don't pollute the quality numbers.

### 12.3 What you see on the screen

| Area | What it shows |
|---|---|
| **Headline figures** | Conversation turns, clean rate (turns with no flags), average response time, high-severity flags, average judge score, engine mix (AI vs offline) |
| **Sessions** | One row per conversation: number of turns, time span, how many flagged |
| **Session replay** | Pick a session to see every question in order |
| **Turn detail** | Open one question to see: agent pipeline with timings, the query that ran, source FIR rows, what was sent to the model, the answer returned, rules fired, and judge scores |
| **Filters** | All turns / flagged only, include web-request telemetry, search text |
| **What it records / Why it matters** | Plain explanations for new users |

### 12.4 Why it matters

- **Quality:** catch answers that assert facts without evidence before they cause harm.
- **Accountability:** show exactly why an answer — or a warning — appeared.
- **Improvement:** each flag type points to the part to fix (wrong template, prompt issue, too much data sent, slow model, failing helper).

If tracing is switched off in the settings, this screen reports it as disabled.

---

## 13. Account — settings, briefings, uploads, audit

**Address:** `/account` · **Purpose:** personal settings plus officer tools.

| Section | What you can do |
|---|---|
| **Preferences** | Interface language, date format, default landing screen, display name for reports |
| **Notifications** | Choose alerts: Antar alerts, risk score updates, new corridors, patrol suggestions, system announcements |
| **Shift Brief** | A start-of-shift summary for a zone and window (8, 12, 24 or 48 hours) |
| **Antar Alerts** | Watchlist alerts that fired, with acknowledge |
| **Export Centre** | Download activity reports and case dossiers |
| **Upload** | Add new FIR data from a CSV file |
| **Security** | Change password, two-factor authentication, active devices, sign out (demo UI) |
| **Compliance & Guardrails** | What protections are active |
| **Activity Log** | Your recent actions |
| **Raw Audit Log** | The tamper-evident log — **Admin only** |

### 13.1 How the Shift Brief works

1. Take the 25 most recent FIRs for the chosen zone (or all districts).
2. Find the top two crime types among them.
3. Check the evidence records for an active accused in that zone.
4. Count confirmed hotspots ("active beacons") in that zone.
5. Write a two-sentence summary and two ranked priority actions with reasons (for example targeted night patrols, vehicle checkpoints).
6. Keep it for 5 minutes so a busy shift change doesn't recompute it for every officer.

### 13.2 How Upload works

1. Choose a CSV file (other formats are rejected).
2. Antar guesses which columns are the date, zone, crime type, latitude and longitude from the column names.
3. The rows are added to the records.
4. Cached query results are cleared so new data shows up.

### 13.3 Why an Officer sees "access denied" on the audit log

On purpose: the full audit log is restricted to Admins. Seeing the denial is itself proof that access control works.

---

## 14. About

**Address:** `/about` · **Purpose:** introduce the team and the product's principles.

Today it shows the team (Vimaraksha), the promise ("Predict and secure before the threat materializes"), three principles (finding unknown links beyond surface data, pattern intelligence, audit and zero-trust security) and team members.

> Planned: rework into a feature page in normal sentence case with live figures (425,015 FIRs), feature tiles linking to each screen, a "how it works" strip and a trust section. See `docs/fixPlan.md` §6.

---

## 15. Older screens still available

These early screens still work if you know the address. Their features live on in the main screens.

| Address | What it does | Now covered by |
|---|---|---|
| `/network` | Pick a repeat offender and draw their network (suspect as a star, influential people larger, cross-case links in amber) | Brain, Search |
| `/profiles` | Repeat-offender list with the four risk bars | Search |
| `/social` | Victim and offender demographic breakdowns, with a fairness notice | Chat (demographic questions) |
| `/trends` | Monthly trend chart and breakdown by type, zone or status | Chat, Predict |
| `/admin` | Audit log with a role switch to demonstrate access control | Account |
| `/ask`, `/brain`, `/guide`, `/info` | Old links that redirect to Chat, Brain or Docs | — |

---

## 16. Things that work quietly in the background

### 16.1 Server start-up

The server accepts requests immediately, then prepares in the background: unpacks the database, loads the language model used for similarity, builds the Second Brain memory, pre-computes network and district statistics, prepares the evidence records, pre-counts the dataset overview, runs the hotspot test, runs the alert scan, and starts the automatic loop. Early requests simply wait a moment for anything they need.

### 16.2 The automatic loop (every 60 seconds)

1. Refresh any prepared intelligence that's about to expire (the prediction board, offender registry, network stats, district heat points).
2. Scan every watchlist for new hits.

### 16.3 Prepared intelligence ("products")

Heavy results are prepared in advance and kept for a set time, so screens open instantly:

| Product | Kept for |
|---|---|
| Prediction board | 6 hours |
| Dataset overview | 6 hours |
| Network statistics, evidence stats | 1 hour |
| Offender registry, district heat points | 10 minutes |
| Shift briefings | 5 minutes |
| Alerts | 1 day |
| Confirmed/rejected hypotheses | 30 days |

### 16.4 Reliability rules for helpers

| Rule | Effect |
|---|---|
| Time limits | Each helper has 6–30 seconds |
| One retry | A failed helper gets one more try |
| Circuit breaker | Three failures in a row → the helper is skipped for 60 seconds with an honest message |
| AI model breaker | A permanent error from the AI service → it's skipped for 5 minutes; answers continue offline |
| Rate limit | About 60 rapid requests per user, then one per second |

### 16.5 Watchlists (Sentinel)

Officers register watches of three kinds:

| Watch | Fires when |
|---|---|
| Person | A named accused appears in new evidence |
| Pattern | A crime type appears in a chosen area ("theft in Bengaluru City") |
| Corridor | Offenders move through a chosen district |

Watches only fire when real data supports them. Hits become high-severity alerts and are pushed live to open screens.

### 16.6 Live feed

A live channel pushes events to open screens: simulated dispatch incidents every few seconds (for demos), each reasoning step as it happens, and watchlist alerts.

### 16.7 Second Brain (institutional memory)

A memory of past investigations, resolved crime patterns and confirmed links.

1. Each memory is turned into a "meaning fingerprint".
2. A question is matched both by meaning and by exact keywords (so an exact FIR or ID number still wins).
3. The best candidates are re-ranked by a more careful comparison.
4. Near-duplicates are removed so you see varied results.
5. Only strong matches are shown.
6. Unconfirmed memories lose confidence after 30 days; overlapping ones are merged.

Example: when Rajajinagar chain snatching spikes, the alert can recall "January 2025 chain-snatching surge in Rajajinagar — resolved by checkpoint saturation on four corridors", giving officers a proven response.

### 16.8 Hidden link discovery

Antar looks for suspects who share a phone number across different cities and count their common contacts. A shared phone plus several common contacts, in cases never formally connected, produces a banner such as "Second Brain: alias 'Yellappa' links Raju K. to a case in another district — shared phone number, 3 common contacts."

---

## 17. Kannada and voice

| Capability | How it works |
|---|---|
| Kannada detection | Any Kannada script in your question switches the answer to Kannada |
| Language switch | The EN / ಕನ್ನಡ switch decides the answer language even if you type in English |
| Kannada understanding | Crime words (ಕಳ್ಳತನ = theft, ದರೋಡೆ = robbery, ಸರಗಳ್ಳತನ = chain snatching), places (ಬೆಂಗಳೂರು ನಗರ) and time words (ಕಳೆದ ತಿಂಗಳು = last month) are recognised |
| Kannada answers | Every answer type has a native Kannada version; tables become lists for readability |
| Speaking | The microphone uses the browser's speech recognition in Kannada or English |
| Listening | Answers are converted to speech and played back |
| Translation | Flip any answer between languages; FIR numbers, IDs, sections and vehicle numbers stay unchanged |
| Offline fallback | If the translation service is unavailable, a police-domain dictionary is used, and the screen says which method was used |

---

## 18. Safety, privacy and fairness

| Protection | What it does |
|---|---|
| Approved questions only | The AI can't run its own database queries |
| Answer checks | Numbers or IDs not found in the records are removed from AI-written text |
| Honest no-results | Empty searches are stated plainly, never padded |
| No future dates | Forecasts use "next 7 days", never a specific future date; future-dated records are excluded |
| Personal data masking | Aadhaar and phone numbers are masked before storage or sending to the AI |
| Compliance receipts | Questions targeting caste, religion or community are rejected with the legal reason; bulk personal-data requests are flagged |
| Fairness framing | Demographic views always state they show correlation, not cause, and must not target any group |
| Bias check | Profiles are scanned for restricted demographic terms |
| OSINT quarantine | Open-web findings are never treated as verified |
| Human confirmation | Inferred links need an inspector to confirm before they count |
| Tamper-evident log | Every action and answer is chained and fingerprinted |
| Sealed reports | Printed reports carry a document fingerprint |
| Encrypted saves | Saved conversations are unreadable on disk |
| Role-based access | Sensitive views require Inspector or Admin |

---

## 19. Demo script: questions that show every feature

| Feature | Say or type | Look for |
|---|---|---|
| Direct answer | "Which zones have the most cyber crime?" | "Bengaluru City has the most cyber crime cases — 42,701 FIRs, 86% …" |
| Kannada | "ಅತಿ ಹೆಚ್ಚು ಕಳ್ಳತನ ಎಲ್ಲಿ?" | Native Kannada answer with Bengaluru City on top |
| Voice | Click the mic, say "who are the repeat offenders" | Answer read aloud |
| Patrol beats | "top beats for theft in Bengaluru City" | Busiest beats with police stations |
| Trend and estimate | "predict theft next month in Bengaluru City" | Steady/rising/falling, next-month estimate, in-progress month excluded |
| Money trail | "which UPI IDs are used in more than one district" | UPI IDs across 4 districts |
| Honest no-hit | "FIRs for UPI nobody@bank" | "No FIR on record mentions UPI ID nobody@bank." |
| Case outcomes | "conviction rate by district in 2023" | Highest conviction rate district and overall rate |
| Links | "/connect show network of S0001" | Network plus hidden cross-case link banner |
| Forecast mode | "/anticipate theft in Bengaluru City" | Map, 7-day risk outlook, patterns |
| Explain | "why?" | Step-by-step reasoning replay |
| Report | Click Export | Sealed printable report |
| Globe | Brain → All Data → click a hub | "Why these are connected" |
| Heat map | Map → pick a date → click a red-ring district | District card with hotspot status and patrol tip |
| Forecast board | Predict → click a High card | Reasoning graph with real numbers |
| Fuzzy search | Search → "Yelapa" | Yellappa found despite spelling |
| Quality audit | Trace → open the last session | Every step, rows, timing, flags |
| Access control | Log in as `U-7001` → Account → Raw Audit Log | Access denied |

---

## 20. Frequently asked questions

**Can Antar make up a number?**
Numbers come from the approved database questions. When the AI writes text, a checker removes any number not found in the returned records.

**Why does it sometimes ask which crime type I mean?**
Trends and hotspots differ hugely by crime type. Ask "most crimes?" to rank all types together.

**Why does an answer say "related context, not a match"?**
You named something (a person, ID or plate) that isn't in the results. Antar shows what it found but refuses to present it as your answer.

**Is the prediction a guarantee?**
No. It gives a risk level, a likely range and the reasons. Confidence is capped below 100%, and inferred scenarios are always labelled.

**Why is a big city always bright on the map but not always a red ring?**
Brightness shows volume. The red ring means the area is significantly hotter than its neighbours — a fairer test.

**What does "silence" mean on Predict?**
A normally busy crime series suddenly dropped. That can mean real improvement, displacement elsewhere, or under-reporting — worth checking.

**Does it work without internet or the AI service?**
Yes. Offline mode answers every question type with fixed writers; only translation quality and a few phrasing features depend on the AI.

**Why can't officers see OSINT?**
Open-web data is unverified and sensitive, so it's restricted to Admins with a consent step. (Its visibility is being improved — see limitations.)

**What happens to my conversation?**
It stays in server memory until restart, and is sealed into the audit log. Use Save to keep an encrypted copy, or Export for a printable record.

**Is this real police data?**
No. All records are synthetic, created for Datathon 2026.

---

## 21. Current limitations

Planned fixes are detailed in `docs/fixPlan.md`.

| Area | Limitation today |
|---|---|
| Brain › Crime Graph | Centre total shows 307,451; correct total is 425,015 |
| Chat | Some labels still appear in capitals ("CYBER CRIME", "DOWNWARD"); highlighted numbers look spaced; skewed rankings show a one-bar chart |
| Expert Workspace | Reads like a list, repeats the headline, uses a display font |
| Map | Corridors dossier opens under the filter pills and calendar |
| Search | OSINT hidden for most logins; associates often empty; Confirm/Reject not working |
| About | All-caps headings; not yet a feature page |
| Login and access | Demo login accepts any password; roles are not yet enforced by real authentication |
| Memory | Conversations, alerts and jobs reset when the server restarts |
| Background jobs | Corridor analysis and shift briefing jobs finish without results |
| Research dossiers | Network facts and risk values can be missing |
| Repeated questions | Identical questions may return an earlier answer until the server restarts |
| Speed | Some screens load many fonts and large graphics libraries up front |

---

## 22. Glossary

| Term | Meaning |
|---|---|
| **FIR** | First Information Report — the record opened when a crime is reported |
| **District / zone / police station / beat** | Area levels, from large to small; a beat is a patrol area |
| **IPC / BNS / SLL** | Indian Penal Code (old), Bharatiya Nyaya Sanhita (new from 1 July 2024), Special and Local Laws |
| **Charge-sheet** | The police report filed in court naming the accused |
| **Conviction rate** | Convicted accused ÷ charge-sheeted accused |
| **Accused / suspect** | Person named in an FIR / person of interest |
| **Unknown subject (UNSUB)** | The unidentified person behind a series of unsolved cases |
| **Modus operandi (MO)** | The method a criminal uses |
| **UPI ID** | Payment ID like `name@bank` |
| **CDR** | Call detail records from a phone company |
| **Template** | One of Antar's pre-approved database questions |
| **Agent / helper** | A specialist that adds one type of analysis (map, network, forecast…) |
| **Offline mode** | Antar answering without the AI model |
| **Citation** | The FIR, station, date and section behind an answer |
| **Chain of custody** | How many records, from where, over what dates, by which method |
| **K / D / I / U** | Known, Derived, Inferred, Unknown (gap) |
| **Confidence** | How sure Antar is, from sources found, rows returned and routing certainty |
| **Hotspot (Gi\*)** | An area significantly hotter than its neighbours |
| **Heat map** | Glow showing where individual incidents cluster |
| **Choropleth** | Districts shaded by how many FIRs they have |
| **Corridor** | Offenders linking two districts |
| **Dark zone** | Area where Antar knows the least |
| **Anomaly** | A week that's unusually high (spike) or low (silence) |
| **Forecast band** | The likely range of incidents (about 90% coverage) |
| **Scenario band** | An "if this suspicion is true" range, always marked inferred |
| **Live cluster** | Several cases close in place and time recently |
| **Risk score** | 0–100 attention score from recency, frequency, severity and connections |
| **Second Brain** | Antar's memory of past investigations and patterns |
| **Hypothesis** | A suggested link or identity waiting for an inspector's decision |
| **OSINT** | Open-source intelligence from the public web, always unverified |
| **Vigil** | The compliance checker for every question |
| **Sentinel** | The watchlist scanner |
| **Trace** | The full record of one question and answer |
| **Flag** | An automatic warning about a trace |
| **Judge** | The AI reviewer that grades flagged and sampled traces |
| **Product** | Prepared intelligence kept ready for a set time |
| **Audit log** | The tamper-evident history of actions and answers |
| **Seal / fingerprint** | A code that proves a record or report wasn't changed |

---

*Antar Product Guide · build of 15 September 2026 · for the full technical reference see `docs/ANTAR_HANDBOOK.md`.*
