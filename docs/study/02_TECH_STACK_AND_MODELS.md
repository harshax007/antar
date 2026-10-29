# Antar — Tech Stack, Libraries, Versions & Models
**Source 2: Ground Truth Technical Specifications, Pinned Dependencies, and Statistical Models**

---

## 1. Complete Technology Stack & Version Matrix

### 1.1 Backend Runtime & Frameworks
| Technology | Exact Version | Purpose & Architectural Notes |
|---|---|---|
| **Python** | `3.11.15` | Core runtime (CPython 64-bit on Windows) |
| **FastAPI** | `0.115.5` | High-throughput asynchronous REST gateway and SSE chat stream |
| **Uvicorn** | `0.32.1` | ASGI server running at `127.0.0.1:8000` |
| **Pydantic** | `2.9.2` | Data validation, request payload schemas, and type enforcement |
| **Pydantic-Settings** | `2.6.1` | Type-safe environment variable parsing (`.env`) |
| **HTTPX** | `0.27.2` | Async non-blocking HTTP client for LLM provider / API gateways |
| **Structlog** | `24.4.0` | Zero-allocation structured reasoning log emitter |

### 1.2 Agent Orchestration (Strictly Pinned)
| Technology | Exact Version | Purpose & Architectural Notes |
|---|---|---|
| **LangGraph** | `0.6.11` | Multi-agent state graph with conditional fan-out routing |
| **LangChain-Core** | `0.3.86` | Base abstractions, message primitives, and tool interfaces |
| **LangGraph-Checkpoint**| `3.0.1` | Durable session checkpointer backed by `SqliteSaver` |
| **LangGraph-Prebuilt** | `0.6.5` | Standard supervisor and prebuilt tool loop primitives |
| **Typing-Extensions** | `4.10.0` | **Hard pinned** — avoids breaking compatibility with `zcatalyst-sdk 1.0.1` |

> [!IMPORTANT]
> **Why LangGraph is Pinned to 0.6.x:** LangGraph 1.x pulls `langchain-protocol`, which hard-requires `typing-extensions>=4.13` (raising `TypeError` on 4.10: `TypedDict 'extra_items'`). Catalyst SDK pins `typing-extensions==4.10.0`. Upgrading LangGraph to 1.x breaks the build. `0.6.11` is the fully verified production line.

### 1.3 Analytical & Database Engines
| Technology | Exact Version | Purpose & Architectural Notes |
|---|---|---|
| **SQLite** | `3.53.1` | Primary transactional OLTP database (`main_lab.db`, 2,040,002 rows, WAL mode) |
| **DuckDB** | `1.5.6` | In-process columnar OLAP engine for multi-million row stress testing |
| **PyArrow** | `18.1.0` | Zero-copy memory transport and columnar ZSTD Parquet I/O |
| **PyTorch** | `2.5.1+cu121`| CUDA 12.1 tensor acceleration on NVIDIA GeForce GTX 1650 |
| **ONNX Runtime** | `1.24.4` | Low-latency inference for BGE-Small and cross-encoder models |
| **NumPy** | `1.26.4` | Vector mathematics and matrix dot-products |
| **Pandas** | `2.2.1` | Panel data structures and statistical feature preparation |
| **SciPy** | `1.12.0` | Empirical distributions, likelihood ratios, and hypothesis tests |
| **NetworkX** | `3.6.1` | Pure-Python graph analytics: PageRank, Louvain, Adamic-Adar |

### 1.4 Frontend Ecosystem (`antar-frontend/`)
| Technology | Exact Version | Purpose |
|---|---|---|
| **Next.js** | `14.2.35` | React application framework with App Router |
| **React / React-DOM**| `18.3.1` | UI rendering engine |
| **3D-Force-Graph** | `1.80.0` | WebGL Three.js force-directed 3D constellation visualizer |
| **Recharts** | `3.9.1` | Analytical trend visualizations and radar charts |
| **Lucide-React** | `1.23.0` | Vector icon suite |
| **Framer-Motion** | `12.42.2` | Smooth UI transition effects |

---

## 2. Machine Learning Models & Statistical Formulations

### 2.1 Dual-Tier Hybrid Vector Retrieval
Antar utilizes a hybrid search architecture fusing lexical BM25 with dense semantic vectors:
1. **Dense Vector Embeddings:**
   - Model: `BAAI/bge-small-en-v1.5` (quantized ONNX).
   - Dimension: $384$.
   - Quantization: `int8` memory-mapped vector cache (`vecs_100k.int8.bin`).
   - Hardware Execution: Single-thread CPU for text inference (~4 ms), offloaded to **PyTorch CUDA fp16** on the GTX 1650 for matrix dot-product scans:
     $$\text{Similarity}(q, d) = \frac{q \cdot d}{\|q\| \|d\|}$$
   - Latency: Scans **100,000 FIR vectors in 4.17 ms** (26.3× speedup over pure CPU).
2. **Reciprocal Rank Fusion (RRF $k=60$):**
   Fuses dense semantic rankings with sparse BM25 keyword rankings:
   $$RRF(d) = \sum_{m \in \{\text{BM25}, \text{Dense}\}} \frac{1}{60 + r_m(d)}$$
3. **Cross-Encoder Reranker:**
   - Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (ONNX).
   - Re-scores top-50 RRF candidates using full cross-attention.

---

### 2.2 Spatio-Temporal Model League: Champion vs. Challenger

Crime forecasting operates as a continuous tournament across 1,075 police stations in Karnataka:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    SPATIO-TEMPORAL CRIME FORECAST LEAGUE                   │
├─────────────────────────────────────────┬──────────────────────────────────┤
│ CHAMPION: Unit-Level Poisson GLM        │ CHALLENGER: Global LightGBM      │
├─────────────────────────────────────────┼──────────────────────────────────┤
│ • Model: Poisson GLM with log-link      │ • Model: LightGBM Poisson GBDT   │
│ • Scope: Per-unit local calibration     │ • Scope: State-wide global model │
│ • Offset: log(exposure) baseline        │ • Offset: init_score = log(exp)  │
│ • Covariates: 11 spatial/temporal lags  │ • Covariates: Same 11 features   │
│ • Interpretability: GLM coefficients    │ • Interpretability: TreeSHAP     │
│ • Calibration: Mondrian Split-Conformal │ • Calibration: Conformal Bands   │
└─────────────────────────────────────────┴──────────────────────────────────┘
```

#### Feature Matrix ($X \in \mathbb{R}^{U \times 11}$):
1. `last1`: FIR count in prior 1-week window.
2. `last4`: FIR count in prior 4-week window.
3. `last13`: FIR count in prior 13-week window.
4. `usual`: Historical mean for the same calendar period.
5. `last_year`: FIR count for the same week in the preceding year.
6. `nbr1`: Neighboring police stations' count in prior 1-week window.
7. `nbr4`: Neighboring police stations' count in prior 4-week window.
8. `nbr_usual`: Historical mean of neighboring units.
9. `area`: District-level aggregate in prior 4 weeks.
10. `area_usual`: District-level historical baseline.
11. `ewma`: Exponentially weighted moving average ($\alpha = 0.3$).

#### Exact TreeSHAP Attribution:
LightGBM computes feature attributions directly in C++ via `booster.predict(X, pred_contrib=True)` without approximation:
$$\ln(\hat{y}) = \phi_0 + \sum_{j=1}^{11} \phi_j$$
Where $\phi_0$ is the base expected value and $\phi_j$ is the exact additive contribution of feature $j$.

#### Mondrian Split-Conformal Prediction Bands:
Provides distribution-free, finite-sample prediction coverage at confidence level $1 - \alpha = 0.83$:
1. Compute non-conformity scores on calibration set:
   $$s_i = |y_i - \hat{y}_i|$$
2. Determine empirical quantile $q_{1-\alpha}$ stratified by activity cluster (Mondrian bins):
   $$\hat{C}(x) = [\max(0, \hat{y} - q_{1-\alpha}), \hat{y} + q_{1-\alpha}]$$
3. Enforces statutory `date_guard`: bars any concrete future calendar date from leaving the backend to prevent unconstitutional pre-crime profiling.

---

### 2.3 Adversarial Base-Rate Audit (`advocate_agent.py`)
To prevent confirmation bias, inferred suspect connections ($[I]$) are audited by the Advocate Agent using empirical Bayes:
- **Likelihood Ratio ($LR$):**
  $$LR = \frac{P(\text{Evidence} \mid \text{Hypothesis})}{P(\text{Evidence} \mid \neg \text{Hypothesis})}$$
- **Multiple Comparisons Correction:**
  Adjusts the posterior probability against the total candidate scan volume ($N$ suspects scanned):
  $$\alpha_{\text{adjusted}} = 1 - (1 - \alpha)^{1/N}$$
- **Verdicts:**
  - `SURVIVES`: Likelihood ratio $> 50$, statistically robust after scan correction.
  - `WEAKENED`: Evidence present but partially explained by population base rate.
  - `COLLAPSES`: Connection explained entirely by demographic baseline collision.
  - `UNASSESSABLE`: Insufficient anchor data.

---

### 2.4 Verhoeff Dihedral Group $D_5$ Algorithm
Aadhaar numbers are validated at ingestion using the non-commutative dihedral group $D_5$ (symmetries of a regular pentagon):
$$c = \sum_{i=1}^{12} d(p(i \bmod 8, a_i)) = 0$$
Where $d$ is the group multiplication table and $p$ is the permutation table. Transpositions of adjacent digits are detected with 100% accuracy, ensuring zero invalid numbers enter the PII mask queue.
