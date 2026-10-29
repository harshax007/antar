# Antar — Final Backend Lab Technical Specification & Winning Blueprint
**Edition:** Antar Lab (Offline High-Throughput Police Intelligence Framework)  
**Target:** 2026 Police Datathon — Production Grade  
**Version:** 3.0-Lab · **Anchored Date:** 2024-03-31 (`clock.today()`)  
**Hardware Profile:** Intel Core i7-9750H (12 logical cores) · 32 GB RAM · NVIDIA GeForce GTX 1650 (4 GB VRAM) · Windows 11

---

## 1. Executive Summary & Hybrid Execution Model

Antar Lab is an offline-first, mathematically calibrated intelligence layer engineered over Karnataka State Police First Information Report (FIR) records. It solves the critical failure modes of conventional police AI systems: **hallucinated case counts, confirmation bias anchoring, and uncalibrated risk predictions**.

### Core Architecture Philosophy
1. **Hybrid Compute Isolation:**
   - **Local Deterministic & Analytical Core:** All heavy computations—multi-million row columnar aggregations, spatio-temporal modeling, dense vector similarity, and hash-chained audit logging—execute locally on bare metal.
   - **Zero Local LLM Overhead:** Large Language Models are **not** run locally. Natural language generation is delegated exclusively to the **Catalyst / QuickLLM API**, preserving 100% of host RAM (32 GB) and GPU VRAM (4 GB) for deterministic database operations, high-throughput analytical scans, and GPU-accelerated 3D rendering.
2. **Offline Runtime Guardrails:**
   - `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` prevent unverified external network connections at runtime.
   - Single-thread BLAS limits (`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`) eliminate thread contention and thread-arena memory bloating.
   - Strict DLL import hierarchy: `onnxruntime` is imported before `scikit-learn` or `scipy` to guarantee clean OpenMP initialization.
   - Deterministic single-worker process model: Uvicorn runs with `workers=1` on port 8000.

---

## 2. Multi-Tier Database Architecture & Storage Tiering

Antar Lab separates transactional point lookups, semantic vector memory, and high-throughput columnar analytics across dedicated tiers:

| Tier | Target Dataset | Technology & Configuration | Workload Profile |
|---|---|---|---|
| **Transactional Tier** | `main_lab.db` (20,40,002 FIRs, 4,172 MB) | SQLite in Write-Ahead Logging (WAL) mode, 2 GB memory-mapped I/O (`PRAGMA mmap_size=2147483648`). | Single-case lookups, point queries, graph traversals, and transactional ACID updates. |
| **Vector Storage** | `brain_vectors.db` (81.60 MB) | SQLite table storing 100,000 384-dimensional int8-quantized vectors. | Sub-millisecond dense semantic vector similarity matching. |
| **Analytical Tier** | `scale/firs_lab.parquet` (30.91 MB) & `scale/firs_stress_1cr/*.parquet` (1.8 GB) | DuckDB querying columnar ZSTD-compressed Parquet files with dictionary-encoded string columns. | Multi-year trend rollups, group-by analytics over 20.4 Lakh and 1-Crore stress records. |
| **Operational Sidecars** | `sessions.db`, `obs.db`, `case_file.db` | Isolated SQLite databases with 30-day DPDP retention. | Telemetry tracking, session histories, LangGraph durable checkpoints (`SqliteSaver`). |

### Cryptographic Ingestion & Data Hygiene Protocol
- **13-Field Cryptographic De-duplication:**  
  $$\text{Signature} = \text{SHA1}(\text{District} \parallel \text{Unit} \parallel \text{Year} \parallel \text{Month} \parallel \text{Day} \parallel \text{Type} \parallel \text{CrimeGroup} \parallel \text{CrimeHead} \parallel \text{KGID} \parallel \text{Beat} \parallel \text{Village} \parallel \text{AccusedCount} \parallel \text{Place})$$
  Ensures zero duplicate FIR loading while maintaining raw historical fidelity.
- **Canonical Status Normalization:** Maps 343 raw text variations of case stages into 13 canonical `CaseStatusMaster` entities via alias dictionary and Levenshtein string distance matching.
- **Structured Statute Parsing:** Unstructured legal citations in `ActSection` decompose into relational records within `ActSectionAssociation`.

---

## 3. 1-Crore (10,000,000 FIRs) Analytical Stress Benchmark

The ultimate test of an enterprise police backend is instantaneous, sub-second aggregation over multi-million row historical archives. Antar Lab benchmarks six mission-critical analytical queries (Q1–Q6) across SQLite (20.4 Lakh), DuckDB Parquet (20.4 Lakh), and DuckDB Stress (1-Crore / 10,000,000 records).

### Live Measured Benchmark Results
*(Directly measured on host hardware: Intel i7-9750H, 32 GB RAM, DuckDB 1.5.6, 10 ZSTD Parquet partitions)*

| # | Query Name | Analytical Workload | SQLite 20.4L (Warm) | DuckDB 20.4L (Warm) | DuckDB 1-Crore (10M Rows) | Speedup vs SQLite | Verification Status |
|---|---|---|---|---|---|---|---|
| **Q1** | **District ranking** | `COUNT(*)` by district, top 10 descending | 1,462.36 ms | 12.56 ms | **38.61 ms** | **116.4×** | **100% PASS** |
| **Q2** | **Monthly trend** | 10-year monthly volume aggregation (`YYYY-MM`) | 8,540.21 ms | 31.11 ms | **118.65 ms** | **274.5×** | **100% PASS** |
| **Q3** | **Crime mix per station** | Station × CrimeType breakdown, top 50 | 25,307.86 ms | 111.38 ms | **693.19 ms** | **227.2×** | **100% PASS** |
| **Q4** | **Pendency by district** | Share of cases > 90 days under investigation | 14,565.24 ms | 33.51 ms | **125.94 ms** | **434.7×** | **100% PASS** |
| **Q5** | **Day of week pattern** | Statewide incident distribution by weekday | 1,010.84 ms | 26.85 ms | **132.35 ms** | **37.6×** | **100% PASS** |
| **Q6** | **2-Key CTE Join** | District-year share of annual total (self-join CTE) | 5,994.94 ms | 56.97 ms | **340.88 ms** | **105.2×** | **100% PASS** |
| **ALL** | **Full Analytical Suite** | **Cumulative 60,000,000 Row Scans** | **56,881.45 ms** | **272.38 ms** | **1,449.62 ms** | **208.8× avg** | **6/6 (100% PASS)** |

### Analytical Performance Highlights
- **100% Passing Rate:** All 6 queries execute with identical, zero-drift row sets across both SQLite and DuckDB datasets.
- **Sub-Second Latency on 10 Million Records:** Average query execution time across 1-Crore rows is **241.60 ms**.
- **Compression Efficiency:** 20.4 Lakh FIRs compress from 4,172 MB uncompressed SQLite to **30.91 MB ZSTD Parquet** (a **135× storage reduction**).

---

## 4. Hardware Acceleration & GPU Utilization (GeForce GTX 1650)

By routing natural language generation to the Catalyst API, the local **NVIDIA GeForce GTX 1650 (4 GB VRAM)** is dedicated to heavy non-LLM operations:

1. **PyTorch CUDA Vector Acceleration:**
   - `torch 2.5.1+cu121` with `torch.cuda.is_available() == True`.
   - Batch similarity scans over the 100,000 384-dimensional embeddings in `brain_vectors.db` execute via half-precision matrix multiplication (`query @ corpus.T`) in **4.66 ms** (compared to 110 ms on CPU).
2. **GPU-Accelerated 3D WebGL Constellation Rendering:**
   - Chrome hardware acceleration routes the Three.js force-directed WebGL canvas to the discrete GPU, rendering thousands of constellation nodes, links, and volumetric lights at 60 FPS.
3. **LightGBM Poisson Challenger Acceleration:**
   - Fast histogram binning for Poisson tree building during forecast refits.

---

## 5. Hybrid RAG & Bilingual Kannada Processing Engine

Antar's retrieval system guarantees that queries in either English or Kannada retrieve exact factual FIR records without hallucination:

```
Officer Query (Kannada / English)
   │
   ├── Kannada Unicode Detection (U+0C80 - U+0CFF)
   ├── Morphological Suffix Stripping (-ದಲ್ಲಿ, -ನಲ್ಲಿ, -ಕ್ಕೆ)
   ├── Domain Lexicon Mapping ("ಕಳ್ಳತನ" -> "THEFT", "ಮೈಸೂರು ನಗರ" -> "Mysuru City")
   │
   ▼
Dual-Channel Candidate Retrieval
   ├── Sparse Lexical (BM25 with k1=1.5, b=0.75)
   └── Dense Semantic (BGE-small-en-v1.5 384-dim ONNX int8)
   │
   ▼
Reciprocal Rank Fusion (RRF, k=60)
   $$RRF\_Score(d \in D) = \sum_{r \in R} \frac{1}{60 + r(d)}$$
   │
   ▼
Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2)
   │
   ▼
Maximal Marginal Relevance (MMR, lambda=0.7)
   │
   ▼
Deterministic SQL Execution & Catalyst Synthesis
```

---

## 6. Spatio-Temporal Predictive Modeling (Champion vs. Challenger)

Antar Lab implements an objective, mathematically validated model league to forecast crime risks across beats and stations:

### 1. Panel Feature Construction
Incident counts aggregate across geographical units $u$, crime heads $c$, and ISO weeks $t$:
- **Autoregressive Lags:** $y_{t-1}, y_{t-4}, y_{t-13}, y_{t-52}$.
- **Moving Averages:** $EWMA_4(u, t)$ and historical spatial baselines $\bar{y}_u$.
- **Spatial Adjacency:** Immediate neighbor signals $Neighbor_1(u, t)$ and typical neighbor baseline $Neighbor_{usual}(u)$.
- **Fourier Harmonics:** $\sin\left(\frac{2\pi w_t}{52.18}\right), \cos\left(\frac{2\pi w_t}{52.18}\right), \sin\left(\frac{4\pi w_t}{52.18}\right), \cos\left(\frac{4\pi w_t}{52.18}\right)$.

### 2. The Model League
- **Champion (Poisson GLM):** Log-exposure offset model:
  $$\log(\mathbb{E}[Y_{u,t+h}]) = \beta_0 + \mathbf{\beta}^T X(u, t, h) + \log(\text{Exposure}_{u, h})$$
- **Challenger (LightGBM Poisson Regressor):** Objective `"poisson"`, `init_score = log(Exposure)`. TreeSHAP feature attributions exponentiated ($\exp(\phi_i)$) produce exact multiplicative risk drivers.
- **Mondrian Split-Conformal Calibration:** Calibrated on Pearson residuals to yield guaranteed 80% and 90% coverage bands.
- **Spatial Hotspot Targeting:**
  - **Predictive Accuracy Index (PAI):** $PAI = \frac{n / N}{a / A}$ (measures crime capture per unit area).
  - **Predictive Efficiency Index (PEI):** $PEI = \frac{n}{n^*}$ (efficiency relative to theoretical maximum).
  - **Getis-Ord $G_i^*$ Spatial Clustering:** Statistically significant hotspots ($z > +1.96, p < 0.05$).

---

## 7. Multi-Agent Governance & Cryptographic Audit Security

Security and statutory compliance are enforced at the architecture level:

1. **Dual Role-Based Access Control (RBAC):**
   - `Constable` $\rightarrow$ `Inspector` $\rightarrow$ `Approver (SP/DCP)` $\rightarrow$ `Admin`.
2. **Verhoeff Dihedral Group $D_5$ Aadhaar Masking:**
   - Any 12-digit sequence is validated against the Verhoeff multiplication ($D_5$) and permutation tables before redaction to `[AADHAAR:XXXX-XXXX-1234]`.
3. **Bayesian Base-Rate Falsification Engine (`advocate_agent`):**
   - For every inferred co-offender link, calculates background population co-occurrence frequencies across 2,365 suspects.
   - Computes Likelihood Ratios ($LR_i$) with multiple-comparisons adjustments.
   - If posterior probability drops below 0.90, returns **HTTP 409 Conflict** with Popperian falsification tests. An Inspector can override only with `acknowledge_challenge=True` and a written justification.
4. **Human-in-the-Loop (HITL) Separation of Duties:**
   - Action proposals (patrol redeployments, watchlist additions) enforce that the Approver is distinct from the Proposer (`proposer != approver`).
5. **SHA-256 Tamper-Evident Audit Ledger:**
   - Every API invocation appends to a cryptographic hash chain:
     $$H_i = \text{SHA256}(H_{i-1} \parallel \text{Timestamp}_i \parallel \text{OfficerID}_i \parallel \text{EventType}_i \parallel \text{PayloadHash}_i)$$

---

## 8. Elevated 3D Brain Visual Architecture

The 3D Brain visualization (`Constellation3D.jsx`) preserves the minimal editorial aesthetic while delivering an immersive command-center visual experience:
- **Living Evidence Links:** Active directional energy particles flow across inferred links (cyan `#00F5D4`) and cross-case links (amber `#E8A33D`), revealing active intelligence pipelines in real-time.
- **Volumetric Dual-Rim Lighting:** Directional cyan rim lighting (`0x22E6F0`, 0.35 intensity) paired with warm amber fill (`0xE8A33D`, 0.18 intensity) provides true spherical volume shading.
- **Atmospheric Deep-Space Fog:** Three.js `FogExp2` (`0x040812`, density 0.0008) provides natural depth cueing, smoothly receding background dust nodes.
- **Cinematic Idle Auto-Orbit:** Seamless 0.35 deg/sec rotation when idle, instantly interrupted on any drag, zoom, or node selection.

---

## 9. Master Backend Endpoint Map

| Method | Endpoint | Min Role | Operational Function |
|---|---|---|---|
| `GET` | `/api/health` | Public | Node liveness, active edition (`lab`), DB status, ONNX corpus count. |
| `POST` | `/api/auth/login` | Public | Authenticates credentials and issues 12h HMAC-SHA256 JWT token. |
| `POST` | `/api/chat/stream` | Constable | Primary bilingual SSE intelligence pipeline with Catalyst/QuickLLM. |
| `GET` | `/api/forecast/hotspots` | Constable | Station/beat patrol risk forecasts with conformal coverage bands. |
| `GET` | `/api/forecast/league` | Constable | Champion (GLM) vs. Challenger (LightGBM) evaluation league table. |
| `GET` | `/api/brain/similar` | Inspector | Hybrid dense vector + BM25 search with cross-encoder reranking. |
| `GET` | `/api/profile/{id}` | Inspector | Suspect risk score, TreeSHAP driver factors, and co-accused network leads. |
| `GET` | `/api/graph/{id}` | Inspector | Subgraph extraction for suspect co-offenders and shared evidence. |
| `POST` | `/api/hypothesis/{id}/confirm` | Inspector | Promotes inferred links; enforces HTTP 409 rejection if proof is weak. |
| `POST` | `/api/hitl/propose` | Inspector | Submits redeployment or watchlist proposal for supervisory review. |
| `POST` | `/api/hitl/{id}/approve` | Approver | Executes pending action (strictly enforces `proposer != approver`). |
| `GET` | `/api/audit/integrity` | Admin | Validates cryptographic SHA-256 hash chain across all audit blocks. |
| `GET` | `/api/scale/benchmark` | Constable | Returns structured 20.4L vs 1-Crore DuckDB benchmark results. |
| `POST` | `/api/scale/run` | Constable | Live execution trigger for Q1–Q6 analytical benchmarks across engines. |

---

## 10. Datathon Rehearsal & Verification Playbook

### Step 1: Environment & Guardrails Check
```powershell
$env:TMP="D:\tmp"; $env:TEMP="D:\tmp"
$env:ANTAR_EDITION="lab"
$env:ANTAR_DB="main_lab.db"
D:\Project\.venv\Scripts\python.exe scripts\lock_agents.py --check
```

### Step 2: Start Backend Server
```powershell
$env:TMP="D:\tmp"; $env:TEMP="D:\tmp"
$env:ANTAR_EDITION="lab"
$env:ANTAR_DB="main_lab.db"
D:\Project\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Step 3: Start Frontend Dev Server
```powershell
cd D:\Project\antar-frontend
npm run dev
```

### Step 4: Verify 1-Crore Benchmark Live
Navigate to `http://localhost:3000/scale` to view:
- **100% Pass Rate (6/6 PASS)** badge.
- **208.8× average speedup** of DuckDB Parquet over SQLite.
- Click **"Run All Benchmarks"** to execute live 10,000,000 row aggregations across all 6 queries in ~1.4 seconds.
