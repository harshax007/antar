# 07 — One-Page Stage Pocket Cheatsheet (Print & Keep Beside Laptop!)

> **Harsha D B — Team Vimaraksha (`ANTAR`)** | **29 Oct 2026 | `12:30–12:45 PM` (`8m` Pitch/Demo + `5m` Q&A)**
> **Four Seasons Hotel Bengaluru — Main Hall (Grand Ballroom)** | **Gate Call: `12:20 PM`** | **USB-Tether Phone + Offline Lab!**

---

## 1. Architecture in 5 Crisp Lines
1. **Perimeter (`main.py`):** HMAC-SHA256 6-role RBAC (`Constable → Admin`) + **Vigil** Article 15 anti-bias screen + `security.py` secret/path scrubber.
2. **Manifest Router (`AGENTS.md`):** Executable YAML manifest compiles **18 agents** (`supervisor` → workers → `synthesize`) with fail-closed `policy.py` rank & obligation checks.
3. **Deterministic Spine (`zcql_repo` + `DuckDB`):** **26 parameterized SQL templates** (zero raw LLM SQL) over SQLite WAL/mmap (`~19L` FIRs) + **DuckDB ZSTD Parquet** (`1 Crore` FIRs).
4. **Brain & Forecast (`onnx_backend` + `forecast/`):** Torch-free CPU **ONNX fp32** (`bge-small` + `MiniLM` cross-encoder + MMR over `100k` int8 vectors) + **Poisson GLM Champion vs LightGBM TreeSHAP Challenger** with **Mondrian 80%/90% Conformal Bands**.
5. **Adversarial & Court Shield (`advocate_agent` + `hitl` + `audit_store`):** LLM-free **Bayesian Devil's Advocate** (`HTTP 409` confirm gate), **Guardrails `G1–G6`** + ICD-203 **K/D/I/U** tags, **2-Officer HITL**, and **SHA-256 Hash-Chained PDF Report**.

---

## 2. Core Tech Stack & Key Numbers Table

| Layer | Technology | Verified Baseline Metric (`main.db`) | Lab Final Metric *(Fill Pre-Stage!)* |
|---|---|---|---|
| **API & Stream** | Python `3.11`, FastAPI, Uvicorn ASGI, SSE | `45+` routers, `~450–510 MB` RAM | Locust 25-user p95: `[VERIFY docs/SCALE.md]` |
| **Operational DB** | SQLite 3 (`WAL` + `2 GB mmap` + `30` indexes) | `10,00,000` FIRs (`1.61 GB`), `<50 ms` idx | `main_lab.db`: `[VERIFY ~19L in TOPUP_REPORT.md]` |
| **Big-Data OLAP** | DuckDB + PyArrow ZSTD Parquet (`Lab L5`) | `19L` real + `1,00,00,000` (**1 Cr**) stress | 1Cr scan: `[VERIFY ms in docs/SCALE.md]` |
| **Forecasting** | Poisson GLM + NB2 + Conformal vs LightGBM + TreeSHAP | **PAI@5% = `14.2`** (`40.4%` all-crime in `22/23` wks; `52.0%` property in `23/23` wks) | League winner: `[VERIFY MODEL_LEAGUE.md]` |
| **Second Brain** | ONNX Runtime `fp32` (`bge-small` 384d + `MiniLM`) | `100,000` int8 vectors in `81.6 MB` (`3 MB` scan RAM) | Parity `cos = 1.000` (torch-free) |
| **Accuracy & QA** | `eval_gold.py` (`EN + ಕನ್ನಡ`) + `pytest` | `35/35` baseline gold; **`1,988+` tests** (`149` files) | 150-Q Gold: `[VERIFY % in docs/ACCURACY.md]` |

---

## 3. Your 8-Minute Stage Flow + 3 Core Code Flows
- **Stage Clock:** `0:00–1:35` **Slides 1–2** (Hook + 3D 3-Slab Stack) → `1:35–2:10` **Slide 3 QR Code** (Cloud 10L on phones) → `2:10–3:35` **Bilingual Chat + Why? + 150-Q Card** → `3:35–5:00` **Predict League + Conformal + TreeSHAP** → `5:00–6:35` **Brain + Advocate `409` Block + 2-Officer HITL** → `6:35–7:25` **Live 19L/1Cr DuckDB Scale + SHA-256 PDF** → `7:25–8:00` **Crisp Close**.
- **3 Flows to Cite:** (1) `chat_stream._run_pipeline` → `vigil` → `kn_bridge` → `query_agent` (`zcql_repo`) → `self_heal` → `answer_guardrails` (`G1`) → `audit_store`; (2) `research_node` → `advocate_agent.challenge` (Bayes LR + scan penalty) → `hypothesis.confirm_hypothesis` (`409`); (3) `forecast/model.fit` + `_calibrate` → `hitl.propose` (`202`) → `Approver` `decide` (payload hash echo).

---

## 4. Top 10 Jury Questions — One-Line Knockout Answers
1. **Why not Text-to-SQL LLM?** *85% SQL accuracy means 1 in 7 police counts is silently wrong; 26 parameterized templates give 100% valid SQL, `<50 ms` speed, and zero injection.*
2. **How do you stop hallucinated numbers?** *`answer_guardrails.check_numbers` (`G1`) checks every digit in prose against retrieved SQL rows and falls back to deterministic prose on any mismatch.*
3. **What if ballroom/station internet dies?** *SQLite, DuckDB, 100k ONNX vectors, Forecast League, Bayesian Advocate, HITL, and SHA-256 Audit all run **100% offline** on CPU.*
4. **How do you prevent caste/religion bias?** *`vigil_agent` blocks Article 15 targeting pre-query, forecast features use zero demographic columns, and `fairness.py` audits parity.*
5. **Isn't PAI 14.2 just picking big stations?** *No—exposure-offset GLM predicts rate per $\text{km}^2$ and beats the 4-week station-size baseline in **22/23 weeks** (`23/23` on property crime).*
6. **Why does `advocate_agent` block Confirm with `409`?** *It computes exact population base-rate Likelihood Ratios + multiple-comparisons scan penalties (zero LLM) so coincidences aren't marked `KNOWN`.*
7. **Why are `Accused`/`Victim` tables 0 rows?** *Official SCRB Datathon data strips citizen PII by law (counts only); we kept 0 rows rather than fabricating citizen names, using disclosed seeds for graph demos.*
8. **Does OSINT leak FIR names to Google?** *Impossible—`osint` has `graph_node: null` (unreachable from chat), imports zero FIR tables, hashes audit queries, and stamps `UNVERIFIED`.*
9. **Can SQLite handle 1 Crore FIRs?** *SQLite handles sub-5ms `FIR_ID` lookups & WAL transactions; **DuckDB + ZSTD Parquet** handles 1-Crore statewide analytical scans in milliseconds.*
10. **Who is accountable for a patrol/watchlist order?** *Dual-control HITL (`hitl.py`): an `Inspector` proposes, a separate `Approver` (SP/DCP) signs the SHA-256 payload hash, sealed in the tamper-evident hash chain.*

---

## 5. Tactical Phrases to Buy Time, Handle Curveballs, or Redirect Smoothly
- **To buy 4 calm seconds on a deep math question:** *"That touches a critical distinction between our retrieval stage and verification stage—let me give the short operational answer first, then the exact equation."*
- **When asked about a missing feature (live CCTNS / beat shapefiles / paid CDR):** *"By deliberate scope boundary, public SCRB data doesn't include [X], so we built the verified interface (`geo_units` / `Accused` ER / `osint_checks`) and kept the boundary transparent rather than mocking fake production data."*
- **To turn a hostile challenge into a live demo flex:** *"Instead of me claiming it works, I have that exact screen open in Tab [X]—may I show you in 10 seconds?"*
