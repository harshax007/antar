# Antar — Demo day, Thursday 29 October 2026

Everything in this document was run on 23 Oct 2026 against the live build and the register as
set up for the demo. Answers quoted below are what the system returned, not what we hope it
returns. Before the demo, `python scripts/demo_check.py --date 2026-10-29 --full` must print
**READY**; it re-checks every scenario here.

---

## 1. The proof pack: every claim, and how to prove it live

| Claim | Measured | Prove it live |
|---|---|---|
| Answers come from the record, not the model | 26 fixed query templates, no free SQL; every answer cites its FIR rows | Chat → any answer → "How this was answered" |
| Routing is deterministic | Golden questions **23/23 English, 12/12 Kannada** | `python scripts/release_check.py` (eval line) |
| Works without the AI model | Offline writer answers every template question | Same answers with the model off (Expert off) |
| Forecast beats "patrol where it was busy" | Top 5% of beats caught **40.4%** of crime vs **38.0%**; better in **22 of 23** weeks | Predict → Engine confidence; `docs/FORECAST_BACKTEST.md` |
| Stronger for property crime | **52.0% vs 41.8%**, better in **23 of 23** weeks | same |
| The ranges are honest | 80% ranges held **80.1%**; 90% held **93.9%** (beats) | Predict → Why this forecast → range |
| Unusual activity is caught | Rajajinagar chain snatching: **8 cases vs usual ~2, z 4.05** | Predict → Active alerts |
| Bilingual, Kannada first-class | Kannada Brain recall **0.73** vs English **0.72** on the same question | `python scripts/demo_check.py --full` |
| Indian names found however spelt | 18 spelling pairs match (Kumar/Coomar, Mohd/Mohammed, ಯಲ್ಲಪ್ಪ/Yellappa); 10 different names stay apart | Search: type `ಯಲ್ಲಪ್ಪ` or `Coomar` |
| Repeat locations without rounding errors | H3 hexagons: top-40 locations hold **1,219** FIRs (was 1,053 with rounding) | Map → Repeat locations |
| The model can read, but it cannot act | A patrol move needs a **second, named officer**; self-approval refused; approver signs the exact payload hash | Predict → Shift plan → Propose |
| Prohibited targeting is refused | "Which community…" → **refused, Article 15**, no data agent runs | Chat (see run sheet 11:00) |
| Bulk personal data is flagged | "all phone numbers in zone…" → **flagged, BNSS §94/106** | Chat |
| Personal data never reaches the model | Aadhaar (Verhoeff), mobiles, UPI, accounts, email, PAN redacted; case numbers kept | `tests/test_guardrails.py` |
| Tamper-evident audit | **11,499 / 11,499** audit entries verified on the hash chain | `python scripts/demo_check.py` (audit line) |
| It is tested | **1,910** automated tests pass (2 known failures, neither on the demo path); release check **READY** | `python scripts/release_check.py` |
| Scale | **10,00,000 FIRs**, 41 districts, 1,155 stations, 113 crime types; median answer ~1.5–3 s | Chat timings ("Thought for …") |

**Say this before anyone asks:** the real KSP record ends in March 2024. Rows after that are
demonstration rows, marked `is_synthetic_row = 1` and labelled on screen. Beat areas are
estimated (the data has no beat boundaries). Patrolling a flagged beat records more FIRs there,
so the advice is to rotate. Near-repeat prediction was measured and rejected.

---

## 2. What was set up in the data (23 Oct)

Only demonstration rows were re-dated; nothing was inserted, the register is still exactly
**10,00,000 FIRs**, and a full backup was taken first (`main.db.bak-20261023-before-demo-week`).

| Change | Why | Undo |
|---|---|---|
| 29–31 Oct filled to a normal day (15 → 51, 19 → 50, 17 → 50 FIRs) from December padding | The seed put a third of the usual FIRs on month-ends: on demo day the Map/Predict would have shown a false "two-thirds drop" | `python scripts/demo_week.py --revert` |
| Rajajinagar chain-snatching spike planted for the week ending 29 Oct (8 cases, 26–29 Oct) | WOW moment: the scanner finds it live (z 4.05) | `python scripts/replant_p2.py --revert` |
| C3 UPI mule ring: newest case dated **27 Oct** (`suman68@ybl`) | Linkage works on something "new": 12 FIRs, 4 districts | `demo_week.py --revert` |
| C4 "digital arrest" scam: newest case **28 Oct** (`103.32.58.79`) | 9 FIRs, 4 districts | same |
| C2 chain-snatching crew: newest case **29 Oct** (vehicle `KA-06-AH-5331`) | 8 FIRs, 3 districts | same |
| Demo-day volume (applied 26 Oct): **28 Oct → 300 FIRs** (build-up), **29 Oct → 670 FIRs**, from Nov–Dec background padding; concentrated in Bengaluru City (388 on the 29th), then Mangaluru City and Mysuru City | A busy demo day that reads as a hotspot on the Map, not an even rise. Story rows, entity-key rows and the P2 spike pair were not used as donors. `demo_check.py --date 2026-10-29` still READY (spike z 4.05) | `python scripts/demo_day_volume.py --revert` |

Already in the data (unchanged): the **Raju K. "Yellappa"** alias link (shares a phone with
Yellappa M. in Mysuru), five evidence syndicates (highway dacoity, robbery + pawnbroker,
drugs, antique/temple theft, border arms), festival locked-house burglaries (A1), payday ATM
thefts (A2), the Tumakuru→Mysuru→Bengaluru→Hassan corridor (A4). Deepavali is **8 Nov 2026**:
on demo day it is 10 days away and shows on Predict as an upcoming event.

The scheduled cases show from their own date: on 23–26 Oct `demo_check.py` reports them as
"scheduled". To rehearse the demo-day state on an earlier day, start the backend with
`ANTAR_FORECAST_AS_OF=2026-10-29` (Map, Predict and alerts then treat 29 Oct as today).

---

## 3. The demo week

| Day | Goal | Do |
|---|---|---|
| **Fri 23 Oct** | Data and proof ready | ✅ Data set up, backup taken, `demo_check --date 2026-10-29 --full` READY, release check READY. Restart the backend. |
| **Sat 24 Oct** | Rehearsal 1 — full run, timed | Backend with `ANTAR_FORECAST_AS_OF=2026-10-29`. Run the 15-min sheet end to end with a stopwatch; note every step over its time. Sign in once as an Approver in a second browser for the approval step. |
| **Sun 25 Oct** | Rehearsal 2 — Kannada and failure drills | Run the Kannada lines. Drill each fallback in §5: model off, backend restart mid-demo, open-web search unreachable. Write answers to the Q&A list in §6 in your own words. |
| **Mon 26 Oct** | Spike starts showing on the real date | `python scripts/demo_check.py` (spike cases from today). Rehearsal 3 on the real date. If a Brave key was obtained, add `BRAVE_SEARCH_API_KEY` to `.env` and restart. |
| **Tue 27 Oct** | C3 live; dress rehearsal with a "judge" | Someone who hasn't seen it plays judge and interrupts with questions. Record a full screen video as the backup. |
| **Wed 28 Oct** | C4 live; freeze | Code freeze at 18:00 — no commits after. `python scripts/demo_check.py --date 2026-10-29 --full` → READY. Copy `main.db` to a USB drive. Charge everything. |
| **Thu 29 Oct** | Demo | Morning checklist (§4), then the run sheet (§5). |

---

## 4. Demo morning checklist (T-90 min)

1. `python scripts/demo_check.py --full` → must print **READY for 2026-10-29**.
2. `python scripts/release_check.py --quick` → READY.
3. Start the backend, wait for "Identity links cached" and "Officer view cached" in its log.
4. Warm the model: ask one throwaway question in Chat (QuickML is ~75 s cold, 4–6 s warm).
5. Warm the OSINT examples: run `SBIN0040071`, `490154203237518` and `sbi-rewards.online` once
   in Search → Open-source checks (results are cached 30 min; the open web can be slow).
6. Open tabs in this order: Chat (New Session), Brain, Map, Predict, Search. Close everything else.
7. Browser zoom 100 %, notifications off, second browser signed in as the Approver.
8. Frontend on port **3000** (a different port fails CORS).

---

## 5. The 15-minute run sheet

Times are cumulative. **Say** = the line to speak; **Expect** = what the screen shows (verified).

**0:00 – 1:00 · Opening.** *Say:* "Karnataka registers about a lakh FIRs a year. The facts an
officer needs are in there, but they take days to dig out. Antar answers in seconds, in English
or Kannada, from the record itself — and it is built so the AI can read but never act."

**1:00 – 3:00 · THINK — Chat (New Session).**
1. Type *Which districts had the most murders in 2022?* — *Expect:* the question rises to the
   centre over the orb; then "**Bengaluru City** has the most murder cases — **68** FIRs, 13% of
   the Karnataka total, followed by Belagavi Dist (30) and Hassan (27), in 2022." (~1.8 s,
   badge *Calculated*). *Say:* "Every number is counted from FIR rows — open 'How this was answered'."
2. *Top beats for burglary in Bengaluru City* — *Expect:* "**Beat No 3 · Byadarahalli PS** … **62** FIRs";
   the key fact is highlighted for an officer short of time.
3. Kannada: *ರಾಜಾಜಿನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು* — *Expect:* the answer in Kannada, 200+ Rajajinagar
   chain-snatching cases, the newest dated this week. *Say:* "Same engine, same rows — Kannada
   is not a translation layer on top."

**3:00 – 5:30 · CONNECT — hidden links.**
4. *who is Raju K* — *Expect:* "**Raju K.** (S0001, alias “Yellappa”, 34, Rajajinagar)". Open
   the profile → network: Raju K. shares a phone with **Yellappa M.** in Mysuru and three common
   contacts. *Say:* "Two FIR systems, two spellings, one man."
5. *FIRs for UPI suman68@ybl* — *Expect:* **12** FIRs across **4** districts, the newest from
   **27 Oct**. *Say:* "A mule account collecting from victims in four districts — and it was used again two days ago."
6. *FIRs for IP 103.32.58.79* — *Expect:* **9** FIRs, 4 districts, newest **28 Oct** — the
   "digital arrest" scam. Then *which UPI IDs are used in more than one district* — *Expect:*
   "**114** UPI IDs appear in FIRs from 2 or more districts".
7. Brain → **Fast Run** → *Expect:* "Look at this first" with a next-step button, plain-language
   sections. Then Layers & Filters → **Serious**: five people not named in a serious case but
   closest to someone who is (e.g. *Lokesh Desai — directly linked to Manju Shetty, POCSO*).
   *Say:* "A lead to check, never a finding — the screen says so."

**5:30 – 8:30 · ANTICIPATE — Predict and Map.**
8. Predict → Active alerts → **Rajajinagar chain snatching** — *Expect:* 8 cases this week
   against a usual ~2, spike score 4.05. Open *Why this forecast*: the usual week × named
   reasons, with its range. *Say:* "It found the spike itself — nobody told it where to look."
9. *Engine confidence* — *Say the numbers:* "Tested on 23 weeks of real cases it never saw: the
   top 5% of beats caught 40% of crime against 38% for last month's hotspots, better in 22 of
   23 weeks — 52% against 42% for property crime. Its 80% ranges held 80% of the time."
10. Chat: *what spikes before Deepavali, and where* — *Expect:* "registered 6% **lower** cases
    overall during Deepavali … What goes up: **Karnataka Police Act 1963** 147% higher (8 of 8
    years)." *Say:* "Deepavali is in 10 days. The honest answer is not 'crime goes up' — it's this."
11. Map → **Repeat locations** (same spot, 3+ FIRs on 2+ days) and the district-links window.

**8:30 – 10:00 · SEARCH and OSINT.**
12. Search: type **ಯಲ್ಲಪ್ಪ** (Kannada) → Yellappa M. and Raju K. (alias). Type **Coomar** → Deepak Kumar.
13. Open-source checks: **SBIN0040071** → the live RBI lookup names the branch; the BNSS §94
    notice is drafted. **490154203237519** → *IMEI check digit is wrong* — "a fake or mistyped IMEI".
    *Say:* "Only the identifier leaves the building; the FIR record is never read here."

**10:00 – 13:00 · SECURE AI.**
14. Chat: *Which community commits the most thefts in Rajajinagar?* — *Expect:* "Antar does not
    answer this … (Article 15 …; BNSS Sec 173) … Ask about the crime instead". *Say:* "Refused
    before any data agent ran — and the refusal is on the audit chain."
15. Predict → shift plan → **Propose** a patrol move → in the Approver browser, approve it.
    Try approving your own: **refused** (self-approval forbidden). *Say:* "The AI suggests. A
    named supervising officer decides, on the exact version they reviewed."
16. Export the conversation report → *audit chain verified* panel, per-answer hashes.

**13:00 – 14:30 · Proof.** Show `scripts/release_check.py` output (READY; golden 23/23 + 12/12;
1,910 tests passing) and say the three numbers: **40.4% vs 38.0%**, **35/35 golden questions**, **11,499/11,499
audit entries verified**.

**14:30 – 15:00 · Close.** *Say:* "Think, Connect, Anticipate — from the record, in Kannada and
English, with a human deciding every action. Antar."

---

## 6. Likely questions

| Question | Answer |
|---|---|
| Is this real KSP data? | Real records to March 2024 (about 9 lakh FIRs); later rows are demonstration rows, marked and labelled on screen. The back-test runs only on real records. |
| Does the AI make things up? | The numbers come from fixed queries over the record; the model only words them, and a number not in the rows is discarded. With the model off, the same answers come back. |
| Can it be misused for profiling? | Questions targeting caste, religion or community are refused before any data is read (Article 15), and every refusal is audited. |
| Who acts on a forecast? | Nobody automatically. A patrol move is proposed, and a different, named supervising officer approves the exact version. |
| How accurate is the forecast? | 40.4% of crime in the top 5% of beats vs 38.0% for last month's hotspots, 22 of 23 weeks, measured on real data it never saw. |
| Won't patrolling flagged beats create more FIRs there? | Yes — the feedback loop is stated on every beat card; the advice is to rotate patrols. |
| Where does it run? | One server; Zoho Catalyst for deployment. The model has no network path and no credentials; outbound calls are allow-listed. |
| What does it cost to run? | Answers are deterministic queries; the model is optional and used only to word answers. |

## 7. If something breaks

| Problem | Do |
|---|---|
| Answer is slow | Keep talking about the previous answer; the record-based writer always answers. |
| Model unreachable | Switch Expert off; answers keep coming from the records ("works without the model" is itself a USP). |
| Backend down | Restart it (the conversation survives a restart — say so); meanwhile show the backup video. |
| OSINT web search slow / blocked | Use the cached examples from the morning; the registry checks and the notice still work. |
| Spike not flagged | `python scripts/replant_p2.py --anchor 2026-10-29`, restart, re-open Predict. |
| Port 3001 | Free port 3000 and restart the frontend. |
