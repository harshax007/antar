# 05 — Grand Finale Stage Script & Runbook (Team Vimaraksha)

> **Presenter:** Harsha D B | **Team:** **Vimaraksha** | **Project:** **Antar**
> **Venue:** Four Seasons Hotel Bengaluru at Embassy One — **Main Hall (Grand Ballroom)**
> **Date & Assigned Slot:** **29 October 2026 | `12:30 – 12:45 PM`**
> **Official Format:** **`8 Minutes` Pitch + Live Demo** + **`5 Minutes` Q&A** (+ `2 min` HDMI transition buffer = `15 min` total slot)
> **Mandatory Gate Time:** Stand outside Grand Ballroom by **`12:20 PM` sharp** (10 mins prior).
> **CRITICAL VENUE RULE:** **NO venue Wi-Fi/Internet is provided.** Use **USB-tethered mobile hotspot** (never Wi-Fi hotspot in a crowded ballroom) + **100% local Lab build (`D:\Project`)** on your laptop!

---

## 1. Your 3-Slide + QR Deck Blueprint (`0:00 – 2:10` Before Switching to Live App)

Keep your slide deck (`offline PDF + PPTX` on `D:\Project\demo-prep\` & Desktop) to **exactly 3 crisp visual slides** so you hit the live software by `2:10`!

### Slide 1 (`0:00 – 0:40`) — The Hook & Core Problem
- **Headline:** **ANTAR** — *Court-Defensible Crime Intelligence & Calibrated Patrol Forecasting for Karnataka State Police* (`Team Vimaraksha`)
- **3 Visual Callouts (Big Numbers, Zero Paragraphs):**
  1. **`16.74L+` (`~19 Lakh`) SCRB FIRs** across `41 Districts` & `~1,049 Police Stations` — locked behind technical SQL/spreadsheets.
  2. **Why Generic AI Fails Police:** Raw LLMs hallucinate counts, write unsafe SQL, anchor officers on base-rate coincidences, and fail offline.
  3. **Our Answer:** Deterministic bilingual intelligence (`EN + ಕನ್ನಡ`) + calibrated patrol risk + built-in **Bayesian Devil's Advocate**.

### Slide 2 (`0:40 – 1:35`) — Core Skills & USPs in a **3D Isometric Architecture Stack**
- **3D Visual Representation to Put on Slide 2 (3 Floating 3D Glass Layers — Bottom to Top):**
  - **Bottom 3D Slab — "THE DETERMINISTIC DATA VAULT (Scale & Speed)":**
    - SQLite `WAL + 2GB mmap` (`~19L` real FIRs) + **DuckDB & ZSTD Parquet** scaling to **1 Crore (`1,00,00,000`) FIRs** + `100,000` **ONNX fp32 Int8** MO embeddings (`81.6 MB`, torch-free, 100% offline-capable).
  - **Middle 3D Slab — "18 MANIFEST-GOVERNED AGENTS (`AGENTS.md`)":**
    - **Vault** (26 parameterized SQL templates, zero raw LLM SQL) | **Core** (Champion **Poisson GLM** `PAI@5% = 14.2` vs Challenger **LightGBM + TreeSHAP** with Mondrian Conformal Bands) | **Link & Motive** (Co-accused graph + exact SHAP risk) | **2nd Brain** (BM25 + Dense RRF + Cross-Encoder + MMR).
  - **Top 3D Shield — "VIMARAKSHA GOVERNANCE & ADVERSARIAL SHIELD":**
    - **Vigil** (Article 15 anti-bias pre-screen) → **Advocate Agent** (LLM-free Bayesian base-rate & scan-size `HTTP 409` gate) → **Guardrails `G1–G6`** (every digit & FIR ID verified, ICD-203 **K/D/I/U** tags) → **2-Officer HITL** + **SHA-256 Hash-Chained Court PDF**.

### Slide 3 (`1:35 – 2:10`) — Live Cloud QR Code + Transition to Full Lab Build
- **Centerpiece:** Huge high-contrast **QR Code** pointing to your live Zoho Catalyst Cloud URL (`https://antar-app.onslate.in/app/` — verify exact URL) + `Demo Access -> Inspector` hint underneath.
- **Two-Column Badge beside QR:**
  - **On Your Phone Right Now (Cloud Edition):** `10 Lakh` FIRs inside a `2 GB` Zoho Catalyst container.
  - **On This Screen Now (Full Lab Edition):** `~19 Lakh` full SCRB corpus + LightGBM League + `1 Crore` DuckDB engine running live on this laptop.

---

## 2. Minute-by-Minute Timeline (`8:00` Pitch/Demo + `5:00` Q&A = `13:00` Active + `2:00` Buffer)

### PART A — The 8-Minute Pitch & Live Demo (`0:00 – 8:00`)

| Clock | Stage Phase | What to CLICK / SHOW | Exact Words to SAY (Plain, Confident, Zero Fluff) | Backend / Tech Note Woven In Naturally |
|---|---|---|---|---|
| **0:00 – 0:40** *(40s)* | **Opening Hook** *(Slide 1)* | Show **Slide 1**. Make eye contact with IPS officers first, then tech judges. | *"Good afternoon respected officers and jury. I'm Harsha from Team Vimaraksha. Across Karnataka's 1,049 police stations, 19 lakh FIRs hold the answers to repeat offenders and next week's crime hotspots—but an SHO on morning roll-call doesn't write SQL, and a standard AI chatbot that guesses even one number or invents one suspect link is unacceptable in policing. We built **Antar** so every answer is mathematically grounded, bilingual, and court-auditable."* | Establishes why off-the-shelf RAG/Text-to-SQL is unsafe for KSP. |
| **0:40 – 1:35** *(55s)* | **3D Architecture & USPs** *(Slide 2)* | Advance to **Slide 2** (3D 3-layer stack). Gesture bottom → middle → top. | *"Antar runs in three hard-enforced layers: at the base, a dual SQLite WAL + DuckDB Parquet vault handling up to **1 Crore FIRs** plus 100,000 offline ONNX crime vectors. In the middle, **18 agents** governed by an executable YAML manifest—never free-form LLM SQL. And at the top, our **Vimaraksha Shield**: Article 15 bias screening, Mondrian conformal forecast bands, a **Bayesian Devil's Advocate** that mathematically challenges weak links, two-officer approval, and a SHA-256 hash chain."* | Names `AGENTS.md`, `ONNX fp32`, `DuckDB`, `Conformal`, `Bayes`, and `SHA-256` in 50 seconds. |
| **1:35 – 2:10** *(35s)* | **QR Code Judge Bridge** *(Slide 3 → `Alt+Tab`)* | Show **Slide 3** (QR). Pause 8 sec for phones to scan, then `Alt+Tab` to **Browser Tab 1 (`/antar` on localhost:3000)**. | *"You can scan this QR on your mobile network right now—that's our Zoho Catalyst Cloud edition serving 10 lakh FIRs inside 2 GB of RAM. Now let me switch to our full **Lab Edition** running live on this machine over the complete SCRB registry through March 2024."* | Proves zero smoke-and-mirrors: Cloud works on phones, Lab works local without venue Wi-Fi. |
| **2:10 – 3:35** *(1m 25s)* | **USP 1: Deterministic Bilingual Chat + Glass-Box "Why?" + Gold Accuracy** | 1. On `/antar`, click/run English query: *"Compare theft cases in Mysuru City between 2022 and 2023"* (or March 2024 summary).<br>2. Toggle **`ಕನ್ನಡ`** and ask: `ಮೈಸೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಪ್ರಕರಣಗಳು ಎಷ್ಟು?`<br>3. Click **`Why?`** drawer + point to `AccuracyCard` (`150` gold set). | *"Watch what happens as I ask in English and Kannada. You see live SSE steps—Vigil clears the query for Article 15 compliance, our local Kannada stemmer resolves `ಮೈಸೂರು ನಗರ` without losing station names to generic translation, and **Vault** executes one of **26 parameterized SQL templates**. Open **Why?**: here is the exact template ID, date window anchored to March 2024, rows scanned, and **Guardrail G1**, which verifies every digit against SQLite rows. Tested across our **150-question bilingual gold benchmark**, execution accuracy is measured deterministically—never LLM-judged."* | Explains SSE streaming, `kn_bridge`, parameterized `QuerySpec`, `check_numbers` (`G1`), and `eval_gold.py` while UI renders! |
| **3:35 – 5:00** *(1m 25s)* | **USP 2: Champion vs Challenger Forecast League + TreeSHAP + Map** | Click **`PREDICT`** tab (`/predict`). Show **Model League Table** (`Poisson GLM` vs `LightGBM` vs `4-Week Avg`), **80%/90% Conformal Bands**, **TreeSHAP** bars, and quick peek at **`MAP`** (`PAI@5% = 14.2`). | *"Most crime maps just paint big stations red. Antar runs a **23-week rolling-origin backtest** comparing naive baselines, an exposure-offset **Poisson GLM**, and a **LightGBM Poisson Challenger**. Concentrating patrol on the top **5% of beat area** captures **40.4% of all crime—PAI 14.2—and 52% of property crime**, beating a 4-week moving average in 22 of 23 weeks. Every hotspot shows **Mondrian split-conformal 80% and 90% count bands** plus exact **TreeSHAP** drivers so an SP sees *why* a beat rose."* | Covers `PoissonRegressor`, `LightGBM`, `TreeSHAP`, `Mondrian conformal`, and `PAI/PEI` leakage-free evaluation. |
| **5:00 – 6:35** *(1m 35s)* | **USP 3: Second Brain + Bayesian Devil's Advocate (`409` Gate) + 2-Officer HITL** | 1. Click **`BRAIN`** (`/brain`) → open an `[INFERRED]` suspect link → click **`Confirm Hypothesis`** → show **Red `409` Rebuttal Modal**.<br>2. Click **`APPROVALS`** (`/approvals`), switch `OfficerSelector` from `Inspector` → `Approver`, approve pending patrol redeployment. | *"Here is our favorite safety feature. Our torch-free **ONNX Second Brain** searches 100,000 MO vectors in 81 MB on disk. When Research proposes an **Inferred** link between two suspects, our **LLM-free Bayesian Devil's Advocate** prices that trait against population base rates and scan size. Watch when I try to confirm a weak district-and-occupation match: **HTTP 409 Blocked!** It proves mathematically that scanning thousands of rows produces this match by chance, and states what evidence would falsify it. Likewise, patrol redeployments require **two-officer HITL approval**—the proposer can never self-approve."* | Demonstrates `onnxruntime`, `int8 vec_store`, `advocate_agent` Bayes LR + multiple-testing, and `hitl.py` dual control. |
| **6:35 – 7:25** *(50s)* | **USP 4: Live 19-Lakh & 1-Crore DuckDB Scale + SHA-256 Court Report** | 1. Click **`SCALE`** (`/scale`) → click **`Run Live Benchmark`** (`SQLite` vs `DuckDB` on `19L` & `1 Crore` Parquet).<br>2. Click **Export Report** (`/report/{session_id}`) + `/audit` green `SHA-256 VALID` badge. | *"Can this scale statewide for the next decade? Watch a live scan right now: DuckDB over ZSTD Parquet aggregates **19 lakh real FIRs**—and a **1 Crore row** stress corpus—in milliseconds inside one process. Finally, one click exports a **court-ready report** keeping ICD-203 **Known / Derived / Inferred** tags intact and sealed with a **SHA-256 tamper-evident hash chain**."* | Proves OLTP+OLAP scale (`SQLite` + `DuckDB`) + forensic chain of custody (`audit_store.py`). |
| **7:25 – 8:00** *(35s)* | **Closing Statement** | Hold on the signed `/report/{session_id}` or `/antar` screen. Smile and pause cleanly before the 8:00 buzzer! | *"To summarize: Antar gives a Constable Kannada answers in seconds, gives an SP calibrated next-week patrol plans that beat 4-week baselines in 22 of 23 weeks, argues **against** its own weak hypotheses before an innocent person is flagged, and scales from a 2 GB cloud container to 1 Crore FIRs on-prem. Team Vimaraksha is ready for your questions."* | Lands right at `7:55`—leaves judges impressed by discipline and sets up the 5-min Q&A! |

---

### PART B — Mastering the 5-Minute Q&A + Live Bonus Reveals (`8:00 – 13:00`)
Keep these **4 pre-loaded tabs** ready in your browser window behind `/antar`—when a judge asks about any of them, **show, don't just tell** in 15 seconds:
1. **Tab 5 (`/osint`):** If asked *"How do you handle external web data / privacy?"* → Show the air-gapped OSINT Workbench (`graph_node: null`, zero FIR imports, `UNVERIFIED` badge, hashed audit subject, BNSS Sec 94 requisition generator).
2. **Tab 6 (`/docs` Schema / `AccuracyCard`):** If asked *"Did you use the full SCRB ER schema / why no suspect names?"* → Show the 21 SCRB master tables + `FIR_Acts` explosion + honest `0-row` `Accused`/`Victim` explanation.
3. **Tab 7 (`/audit`):** If asked *"Can an admin alter AI logs after an incident?"* → Click **Verify Hash Chain** (`GET /api/audit/verify`).
4. **Tab 8 (`AGENTS.md` in VS Code):** If asked *"How does your multi-agent system avoid spaghetti routing?"* → Flash executable YAML `AGENTS.md` + `1,988+` passing `pytest` count.

*(If a panel gives you a longer 15-minute uninterrupted demo window instead of 8+5, spend the extra minutes walking live through Tab 5 `/osint`, Tab 6 `/map` Getis-Ord $G_i^*$ hotspots + Shift Plan roster, and a live role-downgrade test switching `Inspector` → `Constable` to show `policy.py` blocking person-level profiles live!)*

---

## 3. Fallback Plan (If Anything Goes Wrong On Stage at Four Seasons)

| Failure Scenario | Why It Happens in Hotel Ballrooms | Exact Recovery Action (`<5 seconds`) | Exact Confident Line to Say |
|---|---|---|---|
| **Mobile Hotspot / Cellular Signal Drops to 0 Bars** | Grand Ballrooms are concrete/steel Faraday cages + 300 phones jamming 2.4/5 GHz Wi-Fi. | Keep going on `localhost:3000`! Local SQLite, DuckDB, ONNX Brain, Forecast League, Advocate `409`, HITL, and Audit need **zero internet**. Avoid voice mic if offline. | *"Grand Ballroom has zero venue Wi-Fi, which actually lets me show you Antar's core design requirement: our entire SQL, ONNX vector Brain, Forecast League, and Bayesian Adversary are running **100% offline** on this laptop right now."* (Turns a network outage into your biggest flex!) |
| **Judge Says Cloud QR App Is "Waking Up"** | Zoho Catalyst AppSail container cold-starts if idle >15 mins. | Pre-ping Cloud URL at **`12:18 PM`** outside the hall! If it still wakes, `lib/api.js` auto-retries cleanly. | *"Catalyst AppSail wakes from cold-standby in about 10 seconds—our client automatically polls health and replays your query without dropping it."* |
| **A Live Query Returns Honest "No Matching Records"** | Typo in station name or post-`2024-03-31` date filter under `ANTAR_TODAY=real`. | Point straight at the honest dead-end message & nearest-match suggestion! | *"Notice Guardrail G2 in action—because official SCRB records end 31 March 2024, Antar refuses to hallucinate post-cutoff numbers and tells the officer the exact coverage boundary."* |
| **HDMI Resolution / Port Glitch or Process Crash** | Projector scaling or accidental terminal close. | Have **6 numbered high-res screenshots** + a **90-sec MP4 screen recording** open in a paused VLC/Photos window on Desktop (`D:\Project\demo-prep\backup\`). | *"While the display handshakes, here is the exact live capture from this build—and let me show you the code behind it."* |

---

## 4. Pre-Demo Checklist — 29 October 2026 (Hour-by-Hour)

### Night Before (28 Oct Evening)
- [ ] Run full Lab verification suite: `D:\Project\.venv\Scripts\python.exe -m pytest -q` (confirm green).
- [ ] Record final `[VERIFY]` metrics from `docs/lab/TOPUP_REPORT.md`, `docs/lab/MODEL_LEAGUE.md`, `docs/ACCURACY.md`, and `docs/SCALE.md` onto printed [`07_CHEATSHEET.md`](file:///d:/Project/demo-prep/07_CHEATSHEET.md).
- [ ] Save 3-slide deck as **both `.pptx` and `.pdf`** locally + on a USB pen drive; capture backup screenshots/MP4.
- [ ] Pack: **Government Photo ID**, laptop + **original charger**, **HDMI adapter/dongle**, **USB-C/Lightning cable for wired phone USB tethering** (crucial—do NOT rely on Wi-Fi hotspot!), and printed `07_CHEATSHEET.md`.

### Morning at Four Seasons (`08:00 AM – 12:30 PM`)
- [ ] **`08:00 AM`:** Registration & breakfast at Four Seasons Embassy One. Test cellular data speed (Jio/Airtel) near Grand Ballroom entrance.
- [ ] **`11:30 AM` (Refreshment Break — T-60 min):**
  - Plug laptop into wall power; set Windows Power Mode to **Best Performance** and **Sleep / Screen Off = Never**; turn on **Do Not Disturb** (no WhatsApp/system popups!).
  - Connect phone via **USB Tethering** (disables ballroom Wi-Fi interference).
  - Start Backend in Terminal 1 (`ANTAR_EDITION=lab`, `ANTAR_DB_PATH=D:\Project\main_lab.db`, `ANTAR_TODAY=real`, port `8000`) and wait 20 seconds for `background_warmup()` to finish (`GET http://127.0.0.1:8000/api/health` → confirm `brain_backend: "onnx/fp32"`, `brain_corpus_rows: 100000`).
  - Start Frontend in Terminal 2 (`localhost:3000`); open `/antar`, `/predict`, `/brain`, `/approvals`, `/scale`, `/audit`, `/osint` once so Next.js pre-compiles every route!
  - Seed 1 pending HITL `patrol_redeployment` proposal as `Inspector` so `/approvals` has a live badge `1` ready for your 5-second `Approver` sign-off on stage!
- [ ] **`12:15 PM` (T-15 min):** Open `https://antar-app.onslate.in/app/` on your phone and run 1 query so Zoho Catalyst AppSail is **warm and awake** when judges scan your QR code at `12:32 PM`!
- [ ] **`12:20 PM` (T-10 min — MANDATORY):** Stand outside **Main Hall — Grand Ballroom** with laptop awake, Slide 1 full-screen (`125%` browser zoom behind it for back-row readability), ready to plug HDMI and own the room!
