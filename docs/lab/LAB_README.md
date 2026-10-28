# Antar Lab Edition — Architecture, Benchmarks & Presentation Guide

Antar Lab is the high-performance local evaluation edition of Antar, operating directly on the workstation with **2,040,002 real FIR records** (`main_lab.db`), 1-crore row analytical scaling via DuckDB, dual-engine risk forecasting (Poisson GLM vs. LightGBM), and the official Karnataka Police ER schema.

---

## 1. How to Run Antar Lab

### Environment Variables
Configure your environment or use `.env.lab.example`:
```powershell
$env:ANTAR_EDITION = "lab"
$env:ANTAR_DB = "main_lab.db"
$env:ANTAR_TODAY = "real"
$env:ANTAR_FORECAST_AS_OF = "real"
$env:ANTAR_SCALE_DIR = "D:\Project\scale"
$env:TMP = "D:\tmp"
$env:TEMP = "D:\tmp"
```

### Start the Backend
Always use the dedicated project virtualenv:
```powershell
cd D:\Project
D:\Project\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/health` (returns `"edition": "lab"`, `"today": "2024-03-31"`)

### Start the Frontend
```powershell
cd D:\Project\antar-frontend
npm run dev
```
- Web Application: `http://localhost:3000`

---

## 2. Benchmark Regeneration Commands

Every benchmark number in Antar is measured directly from code execution:

| Benchmark | Script / Command | Target Output |
|---|---|---|
| **Gold Accuracy (150 Qs)** | `D:\Project\.venv\Scripts\python.exe scripts/eval_gold.py --mode offline` | `docs/ACCURACY.md`, `public/lab/accuracy.json` |
| **Model League (Forecasting)** | `D:\Project\.venv\Scripts\python.exe -m app.forecast.backtest --challengers lgbm` | `docs/lab/MODEL_LEAGUE.md`, `public/lab/league.json` |
| **Scale Benchmarking (Q1–Q6)** | `D:\Project\.venv\Scripts\python.exe scripts/lab/bench_all.py` | `docs/SCALE.md`, `public/lab/scale.json` |
| **Official ER Tables Rebuild** | `D:\Project\.venv\Scripts\python.exe scripts/lab/build_er_tables.py --db main_lab.db` | Rebuilds `CaseMaster`, `ActSectionAssociation`, etc. |
| **Unit Test Suite** | `D:\Project\.venv\Scripts\python.exe -m pytest tests/test_challenger.py tests/test_scale_bench.py tests/test_er_tables.py` | All pass |
| **Agent Fingerprint Lock** | `D:\Project\.venv\Scripts\python.exe scripts/lock_agents.py` | Updates `agents.lock.json` |

---

## 3. Measured Findings & Numbers for Presentation

### A. Execution Accuracy & Integrity (Phase L4)
- **150-Item Bilingual Suite:** 75 English + 75 Kannada pairs covering all 11 SCRB analytical quotas.
- **Accuracy:** **93.3%** execution accuracy (140/150 passed; 70/75 EN, 70/75 KN).
- **100% Accuracy on Key Workflows:**
  - Entity Ranking (24/24)
  - Monthly Crime Trends (16/16)
  - Inter-District Comparisons (16/16)
  - Case File Lookups (16/16)
  - Cross-Case Multi-Hop Entity Links (8/8)
  - Demographics & Age Distributions (8/8)
  - Relative Temporal Windows (10/10)
- **No Hallucinations:** Zero invented numbers. Prohibited demographic profiling queries (Article 15) and raw SQL injection attempts are intercepted with strict statutory refusals.
- **Latency:** p50 of **38 ms**, with template-driven answers executing in 20–50 ms.

### B. Champion vs. Challenger Forecasting (Phase L3)
- **Champion:** Unit-level Negative Binomial / Poisson GLM with seasonal harmonic terms and spatial smoothing.
- **Challenger:** Global LightGBM model utilizing `init_score = log(exposure)` offset, Mondrian split-conformal coverage bands, and TreeSHAP driver attributions.
- **Metrics Evaluated:** MAE, Deviance Gain, 90% Conformal Band Coverage, Top 5% Crime Capture, PAI@5%, and PEI@5% (Prediction Efficiency Index = PAI / PAI_max).
- **Interactive League Table:** Crowned winner with side-by-side SHAP vs. GLM multiplier drawer in `PredictScreen.jsx`.

### C. Scale & Performance (Phase L5)
- **Data Footprint:**
  - SQLite Register: 2,040,002 rows, 2.3 GB uncompressed.
  - Lab Parquet: 2,040,002 rows, **30.91 MB** (75x zstd compression reduction).
  - 1-Crore Stress Parquet: **10,000,000 rows**, 206.5 MB partitioned across 10 files.
- **Speedup Benchmarks (Workstation Measured):**
  - **Q1 (District Ranking):** SQLite 2,418 ms $\to$ DuckDB Parquet **16.1 ms** (**150x faster**).
  - **Q4 (Pendency Scan):** SQLite 22,670 ms $\to$ DuckDB Parquet **29.3 ms** (**773x faster**).
  - **Q6 (2-Key Join):** SQLite 11,090 ms $\to$ DuckDB Parquet **49.4 ms** (**224x faster**).
- **Locust Concurrency:** 50 concurrent officers hitting streaming endpoints sustained over 3 minutes with **0.0% failure rate**.

### D. Official ER Schema & Integrity (Phase L2)
- **`CaseMaster`:** 2,040,002 rows with standard 18-digit `CrimeNoOfficial` (`1{DistrictID:04}{UnitID:04}{YEAR:04}{Serial:05}`).
- **`ActSectionAssociation`:** 2,040,002 parsed records with >99.8% statutory coverage.
- **`Employee` & `CaseInvestigatingOfficer`:** 53,881 unique investigating officers mapped to individual cases.
- **Zero-Row Person Tables:** `Accused`, `Victim`, and `ComplainantDetails` reflect schema compliance without fabricating unrecorded personal details; aggregate counts are preserved in `case_person_counts` and `arrest_counts`.
- **Integrity:** `PRAGMA foreign_key_check` verified clean (0 errors).

---

## 4. Eight-Minute Presentation Rehearsal Script

| Timestamp | Screen | Key Action & Demonstration | Core Presentation Message |
|---|---|---|---|
| **00:00–01:00** | **Mobile / Phone** | Open Catalyst URL on mobile device | *"This is live on the cloud right now. Accessible to patrol officers on their phones."* |
| **01:00–03:00** | **Lab · Chat** | 1. Ask district ranking in English.<br>2. Ask follow-up in Kannada.<br>3. Look up case `FIR C00026` and expand reasoning trail. | *"Every number is grounded in FIR records. The reasoning trail shows verified SQL templates without LLM hallucination."* |
| **03:00–04:00** | **Lab · Docs / Accuracy** | Open Accuracy Card in Docs | *"We don't claim accuracy—we measured it across 150 gold questions in English and Kannada: 93.3% execution accuracy, 100% no-hallucination rate."* |
| **04:00–05:30** | **Lab · Predict** | View Model League table, switch between Station and Beat, open "Explain Drivers" drawer. | *"Champion vs Challenger: Poisson GLM and LightGBM compete on held-out weeks. The winner earns its place, explained through TreeSHAP."* |
| **05:30–07:00** | **Lab · Scale** | Navigate to `/scale`. Click "Run All" across SQLite 20.4L, DuckDB 20.4L, and DuckDB 1-Crore. | *"Same laptop, no expensive GPU: DuckDB Parquet executes analytical queries across 1 crore FIRs in 53 milliseconds—up to 770x faster."* |
| **07:00–08:00** | **Lab · Brain & HITL** | View cross-case shared vehicle / UPI link, propose patrol redeployment, review audit log. | *"Deterministic cross-case linkage with strict Human-in-the-Loop approval: no operational action happens without an officer's sign-off."* |

---

## 5. Known Caveats (Honest Disclosures)

1. **Date Freeze ("Today" = 31 Mar 2024):** The official SCRB extract concludes on March 31, 2024. The Lab freezes the clock to this date so all relative queries, rolling backtests, and maps evaluate against real history without counting synthetic demonstration rows.
2. **2023 Clones:** 2023 in the raw register contains cloned rows that artificially elevate that specific year's volume. Antar labels this data reality clearly.
3. **Coordinates Coverage:** Approximately 30% of raw FIR rows carry usable GPS coordinates. Hotspot aggregation gracefully falls back to police station centroids when coordinates are absent.
4. **1-Crore Stress Dataset:** Synthesized via stratified bootstrap resampling of the real 20.4L extract to test query engine scalability, clearly labeled as stress benchmark data.
