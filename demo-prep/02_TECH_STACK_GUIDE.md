# 02 — Complete Tech Stack Guide (Every Tool, Why It Was Chosen & Panel Defense)

> **Ground Rule:** Every technology below is verified directly from [`requirements.txt`](file:///d:/Project/requirements.txt), [`requirements-runtime.txt`](file:///d:/Project/requirements-runtime.txt), [`LabBuild_plan.md`](file:///d:/Project/LabBuild_plan.md) (`requirements-lab.txt`), [`antar-frontend/package.json`](file:///d:/Project/antar-frontend/package.json), [`Dockerfile`](file:///d:/Project/Dockerfile), and [`catalyst.json`](file:///d:/Project/catalyst.json). Jargon is explained in plain words on first use.

---

## 1. Backend Language, Web Framework & Streaming

### 1.1 Python `3.11`
- **One-line plain definition:** A readable, general-purpose programming language with the richest ecosystem for statistics, machine learning, and data engineering.
- **Where used:** Entire backend (`main.py`, `run.py`, `app/**`, `scripts/**`, `tests/**`); local `.venv` runs `Python 3.11.15`; [`Dockerfile`](file:///d:/Project/Dockerfile#L1) uses `python:3.11-slim`.
- **Under the hood:** Python `3.11` introduced the **Specializing Adaptive Interpreter** (PEP 659), speeding up function calls and dictionary lookups ~25% over Python 3.10 while keeping C-extension wheels (`numpy`, `scipy`, `onnxruntime`, `duckdb`, `lightgbm`) rock-solid.
- **Alternatives & why chosen:** Node.js/Go lack native statistical libraries (`scipy`, `scikit-learn`, `lightgbm`, `onnxruntime`); Python `3.12+` had slower binary wheel availability on slim Linux containers when Catalyst AppSail base images were pinned.
- **Likely Panel Q&As:**
  1. *Q: Python has the Global Interpreter Lock (GIL)—doesn't that bottleneck concurrent officers?*
     *A:* No, because our heavy operations—SQLite `mmap` reads, NumPy/SciPy math, ONNX Runtime C++ threads, LightGBM C++ trees, and DuckDB vectorized scans—all **release the GIL** in C/C++, while network I/O (`httpx`, SSE streaming) runs asynchronously on `asyncio`.
  2. *Q: Why force `_BLAS_VARS = 1` (`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`) at the top of [`main.py`](file:///d:/Project/main.py#L22-L26)?*
     *A:* Without single-thread BLAS caps, concurrent requests each spawn 8–16 OpenMP threads that thrash CPU caches ("thread oversubscription") and blow up container memory. Capping inner math threads lets request-level concurrency scale predictably.

### 1.2 FastAPI (`>=0.115`) + Uvicorn (`>=0.32`) + Pydantic v2 (`>=2.9`)
- **One-line plain definition:** **FastAPI** is a high-speed asynchronous Python web framework; **Uvicorn** is the **ASGI** (*Asynchronous Server Gateway Interface*—non-blocking web server) that runs it; **Pydantic** validates every incoming/outgoing JSON field in Rust.
- **Where used:** [`main.py`](file:///d:/Project/main.py), [`run.py`](file:///d:/Project/run.py#L45), 45+ routers in [`app/api/`](file:///d:/Project/app/api/), request models like [`StreamChatRequest`](file:///d:/Project/app/api/chat_stream.py#L67) and [`Settings`](file:///d:/Project/app/core/settings.py#L27).
- **Under the hood:** Uvicorn runs a single-process event loop handling hundreds of open **SSE** (*Server-Sent Events*) connections without blocking OS threads; synchronous SQLite/CPU functions are dispatched cleanly via threadpools (`asyncio.to_thread`). Pydantic v2 (`pydantic-core` in Rust) rejects malformed payloads (`HTTP 422`) before route logic runs.
- **Alternatives & why chosen:**
  - *Django:* Too heavy; ORM fights custom read-only `mmap` SQLite and DuckDB analytical queries; weak native SSE streaming.
  - *Flask:* Synchronous **WSGI** (*Web Server Gateway Interface*) blocks one worker thread per open SSE stream.
- **Likely Panel Q&As:**
  1. *Q: Why run Uvicorn with `workers=1` in [`run.py`](file:///d:/Project/run.py#L45)?*
     *A:* On Zoho Catalyst AppSail (`2 GB` RAM ceiling), each worker process would duplicate the Python interpreter + ONNX models + forecast matrices (~450 MB × N). One async worker with C-level GIL release serves concurrent streams inside ~500 MB RAM; horizontal scaling happens at the container replica level.
  2. *Q: Why write a custom [`_Compress`](file:///d:/Project/main.py#L204-L216) GZip wrapper instead of stock `GZipMiddleware`?*
     *A:* Standard GZip buffers chunks in memory until a minimum byte size is met, which freezes live word-by-word SSE tokens on `/api/chat/stream` and `/api/voice/*`. [`_Compress`](file:///d:/Project/main.py#L204) bypasses compression on streaming paths while compressing large JSON payloads (like GeoJSON maps) by ~80%.

### 1.3 Server-Sent Events (SSE) (`app/core/sse.py`)
- **One-line plain definition:** A standard HTTP stream (`text/event-stream`) where the server pushes live progress steps, words, and citations over one normal HTTP connection.
- **Where used:** [`app/core/sse.py`](file:///d:/Project/app/core/sse.py), [`app/api/chat_stream.py`](file:///d:/Project/app/api/chat_stream.py#L893), [`antar-frontend/lib/chatStream.js`](file:///d:/Project/antar-frontend/lib/chatStream.js#L79).
- **Under the hood:** Sends newline-delimited `data: {...}\n\n` JSON frames (`step`, `token`, `citations`, `brain_hits`, `visual`, `confidence`, `custody`, `complete`) plus periodic `: heartbeat` comments so reverse proxies never drop long multi-agent turns.
- **Alternatives & why chosen:** **WebSockets** require sticky stateful upgrades that corporate/police firewalls and CDN proxies frequently drop, and cannot easily carry standard `POST` JSON bodies. SSE works over plain HTTP/1.1 & HTTP/2. *(Note: a lightweight WebSocket endpoint exists in [`app/api/live_stream.py`](file:///d:/Project/app/api/live_stream.py) for optional live dispatch ticker demos, while primary chat uses SSE.)*
- **Likely Panel Q&As:**
  1. *Q: Why stream agent `step` events before the text answer?*
     *A:* Police officers don't trust a blank spinner. Showing *"Vault scanning FIRs → Brain checking 100k MOs → Adversary auditing hypothesis"* turns latency into visible chain-of-custody.
  2. *Q: What if the connection drops mid-stream?*
     *A:* Every turn is persisted atomically in `data/sessions.db` ([`app/core/sessions.py`](file:///d:/Project/app/core/sessions.py)) and [`antar-frontend/lib/api.js`](file:///d:/Project/antar-frontend/lib/api.js#L44) includes automatic server-wakeup retry (`waitForServer`).

---

## 2. Databases & Analytical Storage Engines

### 2.1 SQLite 3 (WAL Mode + 2 GB `mmap_size`)
- **One-line plain definition:** An ultra-reliable, zero-server relational SQL database stored in a single file on disk (`main.db` / `main_lab.db`), tuned for concurrent read-heavy workloads.
- **Where used:** [`app/core/db_path.py`](file:///d:/Project/app/core/db_path.py#L77-L225), [`app/services/zcql_local.py`](file:///d:/Project/app/services/zcql_local.py), [`app/services/zcql_repo.py`](file:///d:/Project/app/services/zcql_repo.py), [`app/services/audit_store.py`](file:///d:/Project/app/services/audit_store.py).
- **Under the hood:**
  - Configured with `PRAGMA journal_mode=WAL` (*Write-Ahead Logging*—readers never block writers and readers never block each other), `PRAGMA synchronous=NORMAL`, `PRAGMA temp_store=MEMORY`, and `PRAGMA mmap_size=2147483648` (2 GB **memory-mapped I/O**, letting the OS map disk pages directly into virtual address space with zero `read()` syscall copy overhead).
  - Backed by **30 covering B-Tree indexes** (`idx_firs_abs_cov`, `idx_firs_u_zone_ct`, `idx_firs_group_date`, etc.) so common station/district/date counts resolve via **index-only scans** in `<50 ms`.
  - Sidecar DBs isolate write contention: `brain_vectors.db` (vectors), `data/sessions.db` (chat turns), `data/obs/obs.db` (metrics), `data/obs/case_file.db` (forensic turn traces).
- **Alternatives & why chosen:**
  - *Zoho Catalyst Data Store (ZCQL):* Capped at 300 rows per page and adds network round-trips on 1M+ rows. We kept ZCQL compatibility in [`app/core/catalyst.py`](file:///d:/Project/app/core/catalyst.py) while executing analytics locally against staged SQLite.
  - *PostgreSQL:* Requires a separate managed DB daemon (impossible in air-gapped police stations or single-container Catalyst AppSail without extra cost/ops).
- **Likely Panel Q&As:**
  1. *Q: "SQLite is a toy database—how can it serve 19 lakh FIRs?"*
     *A:* SQLite is the world's most deployed database engine and handles terabyte datasets when used for **read-mostly analytical/lookup workloads** in WAL + `mmap` mode with covering indexes. Point lookups and indexed station counts take **10–45 ms**. And for multi-crore full-column scans, our Lab edition pairs SQLite with **DuckDB + Parquet**.
  2. *Q: How do you prevent accidental writes or SQL injection against `main.db`?*
     *A:* Forecast/brain readers open `file:...?mode=ro` (`uri=True`), queries use `?` bound parameters exclusively inside 26 whitelisted `QuerySpec` templates ([`zcql_repo.py`](file:///d:/Project/app/services/zcql_repo.py)), and hash-chain audit writes serialize safely with `BEGIN IMMEDIATE` ([`audit_store.py`](file:///d:/Project/app/services/audit_store.py#L84)).

### 2.2 DuckDB (`>=1.1`) + Apache Parquet / PyArrow (`>=17.0`) `[Lab L5]`
- **One-line plain definition:** **Parquet** is a compressed **columnar** file format (stores all dates together, all districts together); **DuckDB** is an in-process columnar **OLAP** (*Online Analytical Processing*) SQL engine ("SQLite for big-data analytics") that scans Parquet directly using CPU **SIMD** (*Single Instruction, Multiple Data*—processing 8–16 numbers per CPU clock cycle).
- **Where used:** `scripts/lab/export_parquet.py`, `app/services/scale_bench.py`, `app/api/scale_api.py`, `antar-frontend/app/(app)/scale/page.jsx`.
- **Under the hood:** Row-oriented SQLite must step over or index wide 48-column FIR rows; DuckDB reads **only** the 2–3 columns a query touches (`District_Name`, `CrimeGroup_Name`, `Year`) from ZSTD-compressed Parquet row-groups, pushing filters down into Parquet metadata min/max statistics to skip entire million-row blocks.
- **Alternatives & why chosen:**
  - *Apache Spark / ClickHouse / Snowflake:* Require JVM clusters, dedicated servers, or cloud data warehouses—completely impractical for an on-premise SP office or air-gapped SCRB server. DuckDB runs inside the exact same Python process with zero external daemon.
- **Likely Panel Q&As:**
  1. *Q: Why keep both SQLite and DuckDB in the Lab build instead of replacing SQLite?*
     *A:* Classic **OLTP + OLAP** (*Transactional + Analytical*) split: SQLite excels at sub-millisecond single-FIR lookups (`FIR_ID`), HITL transactions, session state, and hash-chained audit writes; DuckDB + Parquet excels at statewide multi-year aggregations across **19 lakh to 10 crore FIRs**.
  2. *Q: How much disk does 1 Crore (10 million) FIRs take in Parquet?*
     *A:* With ZSTD dictionary compression on repeated district/station/act strings, 19 lakh FIRs compress from `~3 GB` SQLite down to `~200–300 MB` Parquet, and 1 Crore rows fit comfortably in `~1–1.5 GB` (`[VERIFY exact MB in docs/SCALE.md]`).

---

## 3. Multi-Agent Orchestration & Executable Governance

### 3.1 LangGraph (`>=0.2.28`) + LangChain Core (`>=0.3`) + Custom SQLite Checkpointer
- **One-line plain definition:** A stateful graph framework that models multi-agent workflows as explicit nodes and conditional edges rather than unpredictable free-looping autonomous agents.
- **Where used:** [`app/agents/state.py`](file:///d:/Project/app/agents/state.py#L84), [`app/agents/graph.py`](file:///d:/Project/app/agents/graph.py), [`app/agents/supervisor.py`](file:///d:/Project/app/agents/supervisor.py), [`app/agents/checkpoint_store.py`](file:///d:/Project/app/agents/checkpoint_store.py#L217).
- **Under the hood:** Compiles a **Directed Acyclic Graph (DAG)**: `supervisor` → conditional fan-out (`route_fn`) to `[query, network, profile, forecast, social, research, brain]` → `synthesize` → `END`. [`checkpoint_store.py::SqliteSaver`](file:///d:/Project/app/agents/checkpoint_store.py#L217) persists per-`session_id` graph checkpoints in SQLite (`msgpack`-safe via [`_to_native()`](file:///d:/Project/app/agents/graph.py#L25)), while `CLEAR` sentinels wipe per-turn outputs so stale answers never bleed into new turns.
- **Alternatives & why chosen:**
  - *CrewAI / AutoGen:* Free-form agent chatter burns LLM tokens, loops unpredictably, and violates police determinism. LangGraph enforces fixed topology, bounded hops, and deterministic state reducers.
- **Likely Panel Q&As:**
  1. *Q: Why do you have both [`chat_stream.py::_run_pipeline`](file:///d:/Project/app/api/chat_stream.py#L195) and [`graph.py`](file:///d:/Project/app/agents/graph.py)?*
     *A:* `/api/chat` runs the compiled LangGraph `StateGraph` synchronously; `/api/chat/stream` runs an async streaming pipeline so granular SSE sub-steps and tokens reach the officer immediately. Crucially, **both** invoke the exact same [`orchestrator.run_agent()`](file:///d:/Project/app/core/orchestrator.py#L128), `AGENTS.md` policy checks, and `answer_guardrails.py`.
  2. *Q: How do you guarantee documentation and routing never drift?*
     *A:* [AGENTS.md](file:///d:/Project/AGENTS.md) is **executable YAML**: [`manifest.py`](file:///d:/Project/app/agents/manifest.py) parses it at import time to build the fleet registry and route table, and `tests/test_agents_manifest.py` fails the build if any node, route, or sensitivity tag mismatches.

---

## 4. Machine Learning, Statistics & Geospatial Stack

### 4.1 Scikit-Learn (`>=1.5`) + SciPy (`>=1.13`) + NumPy (`>=1.26`) — **Champion Forecaster & Anomaly Math**
- **One-line plain definition:** Industry-standard numerical, statistical, and regression libraries used for our **Poisson GLM** patrol forecaster, **split-conformal** uncertainty intervals, **MAD-z** spike detection, and **Getis-Ord $G_i^*$** spatial hotspot clustering.
- **Where used:** [`app/forecast/model.py`](file:///d:/Project/app/forecast/model.py), [`app/forecast/features.py`](file:///d:/Project/app/forecast/features.py), [`app/forecast/backtest.py`](file:///d:/Project/app/forecast/backtest.py), [`app/services/anomaly.py`](file:///d:/Project/app/services/anomaly.py).
- **Under the hood:**
  - Fits `PoissonRegressor(alpha=1.0)` on weekly count density $y_{u,t} / \text{exposure}_u$ across 15 causal past-only features (1–8 week lags, EWMA, annual Fourier sine/cosine harmonics, spatial neighbor lag).
  - Estimates Negative Binomial (`NB2`) overdispersion $\alpha$ via method-of-moments ([`_dispersion()`](file:///d:/Project/app/forecast/model.py#L123)) and calibrates **Mondrian split-conformal** quantiles per rate bin ([`_calibrate()`](file:///d:/Project/app/forecast/model.py#L147)) for finite-sample guaranteed 80%/90% count bands.
  - Reconciles beat forecasts top-down so beat predictions inside a station sum coherently to the station forecast.
- **Alternatives & why chosen:**
  - *Prophet / ARIMA per beat:* Fitting 1,134 beats × 5 crime groups = 5,670 separate ARIMA/Prophet models is slow, overfits sparse zero-inflated beats, and predicts negative crime counts! Pooled Poisson GLM shares statistical strength across stations, respects non-negative integer counts, and fits in seconds.
  - *Deep Learning (LSTM / Transformers):* Black-box, data-hungry on weekly count series, heavy RAM, and routinely loses to regularized GLMs/GBDTs on tabular count panels.
- **Likely Panel Q&As:**
  1. *Q: Did you test Hawkes self-exciting point processes or near-repeat kernels?*
     *A:* Yes—documented in [`docs/FORECAST_BACKTEST.md`](file:///d:/Project/docs/FORECAST_BACKTEST.md)! We implemented and backtested a causal spatio-temporal near-repeat kernel (`1 km`, `14-day` half-life) across 60 `(category, metric)` pairs and **rejected it** because ~70% missing/imprecise beat coordinates gave `0/60` improvement over station-lag GLM. We only ship features that win on out-of-sample backtests.
  2. *Q: How do you prove the forecast beats a seasoned officer's "last 4 weeks" rule of thumb?*
     *A:* Rolling-origin backtest across 23 held-out weeks: our Poisson GLM captures **40.4% of all crime** in the top 5% of beat area (**PAI@5% = 14.2**) vs **38.0%** for last-4-week average, winning **22 of 23 weeks** overall and **23 of 23 weeks** on property crime (`52.0%` capture).

### 4.2 LightGBM (`>=4.3`) + Native `TreeSHAP` `[Lab L3]` — **Challenger Forecaster**
- **One-line plain definition:** Microsoft's fast **Gradient Boosted Decision Tree (GBDT)** engine trained with a Poisson count loss (`objective="poisson"`), paired with exact **TreeSHAP** (*SHapley Additive exPlanations*) per-feature attributions.
- **Where used:** `app/forecast/challenger.py`, `app/forecast/league.py`, `antar-frontend/components/ModelLeague.jsx`.
- **Under the hood:** Builds shallow histogram-binned decision trees (`num_leaves=31`, `min_child_samples=50`) capturing non-linear interactions (e.g., *high spatial neighbor lag × festival month × commercial station*) that linear GLM misses, while `booster.predict(X, pred_contrib=True)` computes exact Shapley contributions in `<10 ms` without external `shap` package bloat.
- **Alternatives & why chosen:** *XGBoost / CatBoost:* Heavier wheel footprint and slower histogram training on sparse tabular panels than LightGBM.
- **Likely Panel Q&As:**
  1. *Q: Why ship a "Champion vs Challenger League" instead of just picking LightGBM?*
     *A:* Honest data science: on high-volume categories LightGBM captures non-linear interactions, while on sparse categories regularized Poisson GLM can generalize better (`[VERIFY per-category winner in docs/lab/MODEL_LEAGUE.md]`). Showing all 5 models (`naive_last_week`, `moving_avg_4w`, `seasonal_naive_52w`, `poisson_glm`, `lightgbm_poisson`) side-by-side proves scientific rigor.
  2. *Q: How can an SP trust a tree ensemble?*
     *A:* Every hotspot exposes its exact top-3 TreeSHAP drivers in plain words (e.g., *"+1.8 expected thefts from last-4-week station trend, +0.6 from neighbouring beat spillover"*).

### 4.3 ONNX Runtime (`>=1.19`) + HuggingFace `tokenizers` (`>=0.20`) — **Torch-Free Second Brain**
- **One-line plain definition:** **ONNX Runtime** executes exported neural network graphs in optimized C++ on CPU without installing the `2+ GB` PyTorch library.
- **Where used:** [`app/second_brain/onnx_backend.py`](file:///d:/Project/app/second_brain/onnx_backend.py), [`app/second_brain/embedder.py`](file:///d:/Project/app/second_brain/embedder.py), [`app/second_brain/reranker.py`](file:///d:/Project/app/second_brain/reranker.py), weights in `models/onnx/`.
- **Models run locally (`HF_HUB_OFFLINE=1`):**
  1. **Bi-Encoder:** `BAAI/bge-small-en-v1.5` (`384`-dimensional dense semantic embeddings).
  2. **Cross-Encoder:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (joint query+document pairwise precision reranker).
- **Under the hood:** Tokenizes text in Rust (`tokenizers`), runs ONNX `CPUExecutionProvider` with `intra_op_num_threads=2`, mean/CLS-pools and L2-normalizes vectors, then quantizes stored FIR vectors to **int8 + float32 scale** (`384 bytes/row`) in [`vec_store.py`](file:///d:/Project/app/second_brain/vec_store.py#L126).
- **Alternatives & why chosen:**
  - *PyTorch + `sentence-transformers`:* Adds ~1.5–2 GB disk and ~400 MB idle import RAM—fatal on a 2 GB cloud container. *(Kept only as fallback in [`embedder.py`](file:///d:/Project/app/second_brain/embedder.py#L45) if ONNX files are absent.)*
  - *External Embedding APIs (OpenAI / Cohere):* Sends sensitive FIR MO narratives over the internet, costs money per 100k rows, and breaks offline.
- **Likely Panel Q&As:**
  1. *Q: Why did [`onnx_backend.py`](file:///d:/Project/app/second_brain/onnx_backend.py#L19-L26) select `fp32` ONNX weights instead of dynamic `int8` ONNX model weights, while [`vec_store.py`](file:///d:/Project/app/second_brain/vec_store.py) uses `int8` vector storage?*
     *A:* Great distinction! Post-training dynamic `int8` quantization of transformer attention weights degraded `bge-small` cosine parity to `0.85` and collapsed `MiniLM` top-5 overlap (`1/5`), so our parity gate rejected `int8` *model weights* and kept `fp32` (`cosine = 1.000`). By contrast, quantizing **already-computed L2-normalized output vectors** to `int8 + scale` in `vec_store.py` has `<0.5%` cosine error and saves 75% storage (`81.6 MB` for 100k FIRs)!
  2. *Q: Why didn't you use FAISS, Pinecone, or Qdrant for vector search?*
     *A:* Pinecone requires cloud egress of police data; FAISS/sqlite-vec add native C++ binary portability risks across slim Linux containers. Scanning 100k int8 vectors in `8,192`-row NumPy chunks uses just **3 MB working RAM**, finishes in tens of milliseconds, and feeds our Cross-Encoder + MMR reranker with 100% exact recall!

### 4.4 H3 (`>=4.1`) — Uber Hexagonal Hierarchical Spatial Index
- **One-line plain definition:** Divides Karnataka's map into equal-area hexagonal cells so crime density isn't distorted by arbitrarily shaped district/station boundaries.
- **Where used:** [`requirements.txt`](file:///d:/Project/requirements.txt#L28), spatial density & `[Lab L3 stretch]` H3 resolution-8 (`~0.74 km²`) uniform-cell PAI verification.
- **Alternatives & why chosen:** Rectangular lat/lon grids warp cell area with latitude and have unequal corner-vs-edge neighbor distances; every H3 hexagon has 6 equidistant neighbors and uniform area.
- **Likely Panel Q&As:**
  1. *Q: Why report both Beat PAI and H3 Hex PAI?*
     *A:* Beat areas in SCRB data are approximated via Voronoi centroids (since official beat polygons aren't in the CSV). H3 cells have exact mathematical area, proving our forecast skill isn't an artifact of Voronoi area estimation.
  2. *Q: Why resolution 8?*
     *A:* Resolution 8 (`~0.74 km²`, ~500m edge) matches a realistic urban two-wheeler beat patrol radius.

---

## 5. External AI & Bilingual Integrations (Gracefully Degradable)

### 5.1 Zoho QuickML LLM (`app/services/quickml.py` & `app/services/llm.py`)
- **One-line plain definition:** Hosted OpenAI-compatible LLM inference endpoint on Zoho Catalyst (plus local Ollama/vLLM compatibility via `app/services/llm.py`), used **only** for multi-agent prose synthesis and ambiguous intent assistance—**never** for raw SQL generation or math.
- **Where used:** [`app/services/quickml.py`](file:///d:/Project/app/services/quickml.py#L186), [`app/services/llm.py`](file:///d:/Project/app/services/llm.py#L96), [`app/agents/supervisor.py`](file:///d:/Project/app/agents/supervisor.py).
- **Under the hood:** Manages OAuth2 refresh-token rotation (`_get_access_token`), request time budgets, and an automatic **circuit breaker** (`_breaker_active`) so if QuickML times out or hotel internet drops, Antar falls back in `<10 ms` to deterministic [`heuristics.py`](file:///d:/Project/app/agents/heuristics.py) routing and [`answer_writer.py`](file:///d:/Project/app/agents/answer_writer.py) / [`agentic_spine.py::_synthesize`](file:///d:/Project/app/agents/agentic_spine.py#L312).
- **Likely Panel Q&As:**
  1. *Q: What happens right now if you unplug the internet cable?*
     *A:* Every SQL template, forecast, 100k ONNX Second Brain search, Bayesian `advocate_agent` check, HITL queue, and SHA-256 audit report continues working 100% locally! Single-agent answers don't even call the LLM in normal operation (saving ~4.9s latency and eliminating drift).
  2. *Q: How do you stop prompt injection inside FIR text when the LLM does synthesize?*
     *A:* [`app/core/rag_security.py::fence`](file:///d:/Project/app/core/rag_security.py#L158) strips Unicode zero-width/bidi characters, neutralizes instruction overrides, wraps untrusted text inside random-nonce `<<<UNTRUSTED_EVIDENCE_xxxx>>>` tags, and runs canary leak detection.

### 5.2 Bhashini / Dwani + Local Kannada Transliteration & Stemmer
- **One-line plain definition:** India's national language AI stack (**Bhashini / Dwani**) for Kannada speech-to-text, text-to-speech, and neural translation, backed by a zero-latency offline Kannada morphological stemmer and script bridge.
- **Where used:** [`app/services/bhashini.py`](file:///d:/Project/app/services/bhashini.py), [`app/agents/dwani_agent.py`](file:///d:/Project/app/agents/dwani_agent.py), [`app/api/voice.py`](file:///d:/Project/app/api/voice.py), [`app/core/kn_translit.py`](file:///d:/Project/app/core/kn_translit.py), [`app/second_brain/kn_query.py`](file:///d:/Project/app/second_brain/kn_query.py), [`app/agents/heuristics.py::kn_bridge`](file:///d:/Project/app/agents/heuristics.py#L187).
- **Under the hood:** Strips Kannada case suffixes (*-ಲ್ಲಿ, -ನಲ್ಲಿ, -ಗಳ, -ಇಂದ* — e.g., `ಮೈಸೂರಿನಲ್ಲಿ` → `ಮೈಸೂರು` → `Mysuru City`) and maps Kannada crime/statute vocabulary deterministically before SQL execution, so Kannada factual accuracy does **not** depend on lossy neural translation!
- **Likely Panel Q&As:**
  1. *Q: Why build a local Kannada suffix stemmer instead of just translating Kannada → English via an API?*
     *A:* Generic translators mangle Karnataka police unit names (e.g., translating *"K.R. Pet"* or *"CEN Crime PS"* literally) and fail without internet. Our local [`kn_query.py`](file:///d:/Project/app/second_brain/kn_query.py) + [`kn_bridge`](file:///d:/Project/app/agents/heuristics.py#L187) maps Kannada inflections directly to official SCRB unit & crime-group keys.
  2. *Q: How are numbers verified on Kannada answers?*
     *A:* Guardrails verify numeric tokens before/across translation, and deterministic Kannada templates ([`forecast/service.py::summary_sentence_kn`](file:///d:/Project/app/forecast/service.py#L390)) inject verified digits directly into Kannada sentences.

---

## 6. Frontend Stack (`antar-frontend/`)

### 6.1 Next.js `14.2` (App Router) + React `18.3` + Tailwind CSS `3.4`
- **One-line plain definition:** Component-based web UI framework compiled to a static Single-Page Application (SPA) for CDN hosting (`D:\Project_Antar`) or local Node dev/prod server (`D:\Project`).
- **Where used:** [`antar-frontend/package.json`](file:///d:/Project/antar-frontend/package.json), `antar-frontend/app/`, `antar-frontend/components/`.
- **Alternatives & why chosen:** *Streamlit / Gradio:* Look like student prototypes, re-run whole Python scripts on every click, cannot render custom glassmorphic dark command-center UI, offline service-resilient waking states, or smooth 60fps MapLibre + SSE drawers.
- **Likely Panel Q&As:**
  1. *Q: Why static export (`output: 'export'`) for the Cloud build?*
     *A:* Deploying static HTML/JS/CSS to **Zoho Catalyst Slate CDN** costs zero server RAM, loads globally in `<200 ms`, and leaves 100% of the AppSail container's `2 GB` RAM for the Python AI/SQLite backend.
  2. *Q: How does the frontend handle Cloud cold-starts when a judge scans the QR code?*
     *A:* [`antar-frontend/lib/api.js`](file:///d:/Project/antar-frontend/lib/api.js#L44) (`waitForServer`) detects `502/503/504` wakeup responses, shows a calm *"Antar is waking up"* status instead of crashing, and automatically retries once healthy.

### 6.2 MapLibre GL JS (`^4.7`) + Lucide React (`^0.454`)
- **One-line plain definition:** **MapLibre GL** is an open-source, WebGL GPU-accelerated vector map engine (the open-source fork of Mapbox GL); **Lucide** provides crisp SVG iconography.
- **Where used:** `antar-frontend/app/(app)/map/`, `MapView.jsx`.
- **Alternatives & why chosen:**
  - *Mapbox GL v2+ / Google Maps JS:* Require proprietary billing keys, per-tile usage fees, and phone home to commercial servers.
  - *Leaflet:* DOM/Canvas-based; stutters above a few thousand crime points. MapLibre renders tens of thousands of WebGL heatmap/circle/polygon layers at 60 FPS with zero license cost and supports offline vector tiles for KSP intranet.
- **Likely Panel Q&As:**
  1. *Q: Can MapLibre run inside an air-gapped police intranet with zero internet?*
     *A:* Yes—point the style JSON to a local PMTiles / Martin tile file of Karnataka on the LAN; zero code changes required.
  2. *Q: What layers are rendered on `/map`?*
     *A:* District choropleths, KDE crime heatmaps, Getis-Ord $G_i^*$ statistically significant hotspot z-scores, repeat locations, and forecasted beat priority polygons.

---

## 7. Security, Testing, Load Benchmarking & Deployment Tools

| Tool / Standard | One-Line Purpose | Where Used in Repo | Alternatives & Why Chosen |
|---|---|---|---|
| **Custom HMAC-SHA256 Bearer Tokens + `scrypt`/`pbkdf2` Accounts** | Stateless signed officer session tokens (`12h` TTL) + SQLite revocation table. | [`auth_middleware.py`](file:///d:/Project/app/core/auth_middleware.py#L86), [`accounts.py`](file:///d:/Project/app/core/accounts.py), [`revocation.py`](file:///d:/Project/app/core/revocation.py). | Avoids `python-jose`/`PyJWT` algorithm-confusion vulnerabilities (`alg: none`); zero external dependencies (`hmac` + `hashlib` stdlib). |
| **`cryptography` (`Fernet` AES-128-CBC + HMAC)** | Encrypts saved officer workspace sessions at rest. | [`app/api/session_api.py::_fernet`](file:///d:/Project/app/api/session_api.py#L63). | Audited NIST-compliant symmetric authenticated encryption. |
| **Pytest (`>=8.3`) + `pytest-asyncio` + `httpx`** | Automated test runner verifying `1,988+` assertions across 149 test files. | [`pytest.ini`](file:///d:/Project/pytest.ini), [`tests/`](file:///d:/Project/tests/). | Fast fixture injection, async FastAPI `ASGITransport` testing without spinning up external ports. |
| **Locust (`>=2.31`)** `[Lab L5]` | Python load-testing tool simulating 25 concurrent police stations hitting chat, hotspots, and scale APIs. | `scripts/lab/locustfile.py`, `docs/SCALE.md`. | Written in Python (unlike JMeter XML), natively measures SSE stream completion and p50/p95 latencies. |
| **Docker + Zoho Catalyst (AppSail + Slate)** | Containerized cloud deployment (`Dockerfile` / `Dockerfile.onnx`) + static CDN (`catalyst.json`). | [`Dockerfile`](file:///d:/Project/Dockerfile), [`Dockerfile.onnx`](file:///d:/Project/Dockerfile.onnx), `D:\Project_Antar\DEPLOY.md`. | Official KSP Datathon cloud stack; portable standard OCI Docker image runs identically on KSP on-prem Linux servers. |

### Likely Panel Q&As on Security & Deployment Tooling
1. *Q: Why roll stdlib HMAC-SHA256 tokens in [`auth_middleware.py`](file:///d:/Project/app/core/auth_middleware.py#L86) instead of OAuth2 / Keycloak?*
   *A:* Standard JWT libraries have suffered repeated `alg: none` and RSA/HMAC key-confusion CVEs. Our 40-line `hmac.compare_digest` implementation pins `SHA-256` exclusively, checks SQLite token/officer revocation in $O(1)$ memory, and plugs cleanly behind KSP's existing SSO/SAML reverse proxy in production via trusted gateway headers.
2. *Q: Why is there both [`Dockerfile`](file:///d:/Project/Dockerfile) and [`Dockerfile.onnx`](file:///d:/Project/Dockerfile.onnx)?*
   *A:* [`Dockerfile`](file:///d:/Project/Dockerfile) was our battle-tested Cloud container; [`Dockerfile.onnx`](file:///d:/Project/Dockerfile.onnx) strips CPU PyTorch completely using a multi-stage export build (`models/onnx/` fp32), cutting image bloat and matching our local `.venv` torch-free runtime (`~450–510 MB` RAM).
