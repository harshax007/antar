# Antar — Project Brief (owner's answers)

The 10 planning questions asked at the start of the build session (2026-09-18), with the
owner's answers kept as given. Read this first in any new session, alongside `PROGRESS.md`,
`docs/ANTAR_CONSTITUTION.md` and `docs/MAP_FORECASTING_PLAN.md`.

---

## 1. What's the event, and who's judging?

**Datathon 2026 — Intelligent Conversational AI for KSP Crime Database.**

*The challenge:* Design and develop an Intelligent Conversational AI and Crime Analytics
Platform that enables investigators, analysts and policymakers to interact with the state
crime database using natural language queries, while providing advanced analytical
capabilities grounded in criminology and sociological insights. The platform should enable
users to discover hidden relationships between crimes, offenders, victims, locations and
socio-economic patterns, support investigative decision-making, and provide predictive and
preventive insights to strengthen proactive law enforcement.

*Core capabilities:* crime pattern discovery · criminal network analysis · socio-demographic
crime insights · behavioural and criminological profiling · proactive crime prevention
intelligence.

*Problem statement:* The State Crime Records Bureau (SCRB) manages a large and continuously
expanding repository of crime data from 1,100+ police stations across Karnataka. Current
systems rely on static dashboards and manual queries, limiting deep analysis and real-time
insights.

*Proposed solution framework:*

1. **Conversational Crime Intelligence Interface** — natural-language chatbot for querying
   crime records in English and Kannada; retrieve information about FIRs, accused, victims,
   locations, investigation status and criminal history; context-aware conversations allowing
   follow-up queries without repeating context; voice-enabled Q&A; local PDF export of
   conversation history.
2. **Criminal Network & Relationship Analysis** — identify links between accused, victims,
   locations, financial accounts and crime incidents; visualise criminal networks and
   associations; detect organised crime groups and repeat-offender networks.
3. **Crime Pattern & Trend Analytics** — analyse trends across time, geography, crime type
   and modus operandi; identify hotspots and emerging clusters; seasonal and event-based trend
   analysis.
4. **Sociological Crime Insights** — analyse patterns by age, gender and socio-economic
   background; identify social risk factors; correlate crime with urbanisation, migration,
   economic stress, education and other social indicators.
5. **Criminology-Based Offender Profiling** — identify repeat offenders and habitual
   criminals; analyse offender behaviour based on crime history and modus operandi; risk
   scoring of offenders to prioritise investigations.
6. **Investigator Decision Support** — automated case summaries and investigation timelines;
   similar past cases and investigation outcomes; potential investigative leads.
7. **Financial Crime & Transaction Link Analysis** — detect financial transactions linked to
   criminal activity; identify money trails and suspicious transaction networks; integrate
   financial crime analysis with investigation workflows.
8. **Crime Forecasting & Early Warning** — identify emerging patterns using AI-driven
   analytics; early warnings for repeat crimes, gang activity and organised crime; predict
   potential hotspots.
9. **Explainable AI & Transparent Analytics** — support AI responses with clear data
   references and evidence trails; visualise reasoning paths and analytical correlations;
   maintain transparency and accountability for law-enforcement use.
10. **Secure Role-Based Access & Governance** — role-based access for investigators,
    analysts, supervisors and policymakers; secure handling of sensitive data with audit logs
    and traceability; compliance with data-protection and law-enforcement governance
    frameworks.

**Judges:** police / government officers and technical judges. Weighting depends on the
police officer's use case and how well the solution fits the current problem.

---

## 2. Which USPs must land?

1. **An answer to every question (agent approach)** — self-healing retrieval, no dead ends,
   **0% hallucination rate**, and a RAG pipeline ready for large FIR volumes.
2. **Forecasting and hotspot prediction on the map** — with the best, most relevant
   information for geospatial intelligence.
3. **HITL approval flow and a tamper-evident audit chain**, agentic AI observability, and the
   rest: multilingual voice using **only Dwani**, and network / linkage analysis with
   PageRank and communities over suspects — all applicable.

---

## 3. How long is the demo, and who drives it?

The owner gives the live demo **using the deployed link on their own laptop**, planned for
**15–20 minutes**, covering the best USPs and the *why / what / who* of each.

---

## 4. What does "100% working RAG" mean?

Give Antar a **core value / soul in chat**: an identity, response templates, and standards and
protocols it always follows when answering. Specifically:

- **Correct numbers** for count and aggregate questions over FIRs.
- **Grounded narrative answers** with clickable citations to FIR IDs.
- **No hallucinated names or cases.**
- **A Kannada question gets the right answer.**
- **Answer speed matched to the question type** (e.g. Kannada questions may take longer).
- The **best RAG pipeline for large FIR volumes**, and the **best chat interface** with every
  capability needed to win.

**Example that failed:** *"Which districts have the most kidnapping and abduction?"* returned
a bare *"Aggregated Breakdown (10 distinct groups) — Bengaluru City: 3002 cases, Belagavi
Dist: 414 cases…"*. It must work for all scenarios, and the final build should read like
*"Bengaluru City has the most kidnapping and … followed by …"* — more interactive, with
Antar as a person. **Antar did not understand "yesterday" / "today" — test it.**

---

## 5. Which LLM and what infrastructure?

**GLM-4.7-Flash** and **Qwen 3.6 35B vision-language**, both on **Catalyst QuickML**.
Currently **CPU only**; a **GPU for local deployment is planned** — be ready with that plan to
show in the demo.

---

## 6. What's the knowledge scope?

KSP holds a large FIR dataset; Antar must be the **intelligent layer and the data-fetching
layer**. For the demo, have a good volume of data and show the build can be tuned to handle
large data with local AI and GPU — **run the build on 10 lakh (1,000,000) FIRs** if possible,
with the best results for prediction and retrieval. Indexing of all FIRs must follow the
official **`E:\Datathon_2026\Police_FIR_ER_Diagram (1).pdf`**, stay compatible with the current
build, and may take reference from **`E:\Datathon_2026\01_planning\data_res\FRI_DATA_RAW`**.

---

## 7. Who is the primary user in the demo story?

**Yes** to an end-to-end investigation walkthrough — *case comes in → linked suspects →
pattern → forecast → approve action → audit*.

The primary users are **Crime Records officers**. The product is for **high-stress
environments** where police personnel need valuable information quickly. Prioritise user
personas — **senior police officers and station administrators** — over aesthetics; it is
meant to be **deployed for actual police use**. Research current police-intelligence
drawbacks, what is needed, and how it is asked for.

---

## 8. What's broken or embarrassing right now?

**"Ask me later."**
*(Later answered through screenshots: FIR data showing zeros on the Brain / Full Data Set
page, the chat vs Expert Workspace layout, the C2 console styling, capital letters, answer
scroll position, action buttons, the Listen-to-answer delay, and the crime graph and its
filters — all fixed on 2026-09-18.)*

---

## 9. What's the priority split, and how long?

**Harden and polish only; add new features only if needed. 3 days.**

---

## 10. How do we prove it on stage?

Improve the build and give the owner **the actually-implemented information** so they can
talk about it in the demo and **show it on screen with a working product**.

---

## Decisions made since (for context)

| Topic | Decision |
|---|---|
| Registry size | Scale to **1,000,000 FIRs**, keeping existing rows and adding only real ones |
| Seeded / synthetic data | **Do not label it in the UI**; brief the owner so they can speak to it |
| Time anchor | **Keep the wall clock** for relative periods; trend lines use the real record |
| Deploy artefact | Data-only `main.db.gz` (84 MB); indexes self-build on first query |
| Antar's voice | Hybrid colleague — facts as record, "I" only for limits and judgments |
| Default answer depth | Bottom line + context + evidence; Sources and Limits one tap away |
| Judgments | Allowed, labelled and calibrated (ICD 203), never about an individual |
| Address | No salutation |
| Evidence labels | One K/D/I/U badge per answer; per-claim in the Expert console |
| Kannada | Administrative Kannada; FIR, BNS/IPC, NDPS, POCSO, names and numbers in English |
| After answering | One next step + 2–3 database-checked follow-ups |
| Non-negotiable laws | Never answer a different question · evidence before opinion · the officer decides · protect the vulnerable |
| Nav bar | Keep the **original pixel font and capital letters** |
| Working style | **Stop and ask after each major task**; commit in logical groups; keep `PROGRESS.md` updated |

**Still open:** Catalyst deploy check (~1.2 GB `/tmp` needed), and decision **D1** in
`docs/MAP_FORECASTING_PLAN.md` (forecast "as of 10 Mar 2024" vs the wall clock).
