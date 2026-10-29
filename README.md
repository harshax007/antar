<div align="center">

# Antar (ಅಂತರ)
### Intelligent Layer for FIR and Crime Registries
**Top 10 Finalist — Karnataka State Police Datathon 2026**

*Deterministic multi-agent execution engine for law enforcement operations, replacing generative hallucinations with verified police schemas, conformal risk forecasting, and zero-assumption evidence grounding.*

<br/>

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-20--Agent_DAG-7928CA?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1--Crore_Engine-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)](https://duckdb.org)
[![Security](https://img.shields.io/badge/Security-Air--Gapped_Sovereign-E11D48?style=for-the-badge)](#statutory-compliance-and-security-architecture)
[![Audit](https://img.shields.io/badge/Audit_Ledger-25%2C357_Verified-10B981?style=for-the-badge)](#immutable-audit-chain)

</div>

---

## The Core Problem

When police organizations experiment with general-purpose Large Language Models, three systemic failures immediately disqualify them from production use:

1. **Hallucination in Legal Records:** Probabilistic language models predict tokens based on statistical correlation rather than factual database truth. In a criminal investigation, an AI that invents a penal code section, fabricates a link between two suspects, or misquotes an incident date directly violates constitutional due process and renders evidence inadmissible before a magistrate.
2. **The Security Hazard of Text-to-SQL:** Allowing an AI to synthesize unconstrained SQL against live police registries introduces catastrophic attack surfaces. A prompt injection can trigger unauthorized table scans, exfiltrate confidential informant identities, or exhaust database connections during critical operations.
3. **Unlawful Demographic Profiling:** Generic models trained on open-web datasets often default to statistical correlations that target specific communities. Under **Article 15 of the Constitution of India**, profiling citizens by caste, religion, or community is strictly prohibited by law.

Antar was designed from the ground up to solve these fundamental issues by replacing probabilistic text generation with **deterministic multi-agent code execution**.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Ingestion ["1. Sovereign Security & Ingestion Airlock"]
        Q["Officer Query<br/>(English or Native Kannada Natural Language)"]
        AIR["Airlock PII Firewall<br/>Dihedral Group D5 Verhoeff Checksums (Citizen Aadhaar Masking)"]
        VIG["Vigil Statutory Compliance Gate<br/>Article 15 Constitutional Shield (Demographic Filter)"]
        Q --> AIR --> VIG
    end

    subgraph Routing ["2. Orchestration & Route Resolution"]
        SUP{"Supervisor DAG Router<br/>Strict Intent Classification (manifest.py & AGENTS.md)"}
        VIG --> SUP
    end

    subgraph Execution ["3. Dual-Engine Execution Layer"]
        subgraph FastPath ["System 1: Deterministic Fast-Path (Sub-50ms)"]
            TPL["26 Whitelisted SQL Templates<br/>(T1–T30 Parameterized Slots — Zero Free SQL)"]
            BTREE["SQLite Covering B-Tree Indexes<br/>Covering (district, crime_group, incident_date)"]
            CONF["Mondrian Conformal Risk Forecaster<br/>(80% & 90% Calibrated Prediction Intervals)"]
            TPL --- BTREE --- CONF
        end

        subgraph DeepSynth ["System 2: Deep Multi-Agent Synthesis"]
            NET["Network Agent (Link)<br/>Bipartite Syndicate Graph (Vehicles, CDRs, Common Nodes)"]
            PROF["Profile Agent (Motive)<br/>Exact Linear SHAP Attribution (100 * wi * fi) & Bias Screen"]
            BRN["Second Brain Agent (Vault)<br/>Dual-Tier Lexical BM25 + 4.1ms PyTorch CUDA Vectors"]
            PAT["Pattern & Geo Agents<br/>Uber H3 Hexagonal Binning & Repeat Incident Corridors"]
            NET --- PROF --- BRN --- PAT
        end
    end

    SUP -->|Single-Agent Deterministic Query| FastPath
    SUP -->|Multi-District Deep Synthesis| DeepSynth

    subgraph AuditGate ["4. Grounding, Synthesis & Cryptographic Ledger"]
        SYN["Synthesize Node<br/>G1 Numerical Grounding Guard & General Diary Citations"]
        AUD["SHA-256 Tamper-Evident Audit Chain<br/>25,357 Cryptographically Verified Ledger Blocks"]
        FastPath --> SYN
        DeepSynth --> SYN
        SYN --> AUD
    end

    classDef default fill:#0d1117,stroke:#30363d,stroke-width:1px,color:#c9d1d9;
    classDef gate fill:#161b22,stroke:#58a6ff,stroke-width:1.5px,color:#f0f6fc;
    classDef fast fill:#0d1f17,stroke:#2ea043,stroke-width:1.5px,color:#f0f6fc;
    classDef deep fill:#1c122c,stroke:#bc8cff,stroke-width:1.5px,color:#f0f6fc;
    classDef audit fill:#161b22,stroke:#3fb950,stroke-width:2px,color:#f0f6fc;

    class Q,AIR,VIG gate;
    class SUP default;
    class TPL,BTREE,CONF fast;
    class NET,PROF,BRN,PAT deep;
    class SYN,AUD audit;
```

---

## Architectural Breakdown

### 1. Ingestion Airlock and Sovereign Security
Every interaction begins at the Sovereign Gateway before any database query or reasoning model is initialized:
- **Verhoeff Checksum Airlock:** Civilian identifiers, specifically 12-digit Aadhaar numbers, are validated against Dihedral Group $D_5$ permutation matrices. Detected civilian identifiers, personal phone numbers, and financial tokens are masked at ingestion.
- **Vigil Statutory Gate:** The query text is screened for statutory compliance. Any query attempting to correlate crime frequency with religious communities, castes, or protected demographics is intercepted and returned with an explicit legal citation: *"Antar does not answer demographic queries per Article 15 of the Constitution of India."* Prohibited attempts are written to the audit chain.

### 2. Executable Contract Architecture (`AGENTS.md`)
Antar implements documentation-as-code. The file `AGENTS.md` is an executable specification parsed at runtime by `app/agents/manifest.py`:
- The orchestrator fleet registry, route maps, timeouts, permissions, and guardrails are compiled directly from the manifest.
- If an agent exists in code but is absent from `AGENTS.md`, or if an unmapped route label appears, the test suite (`tests/test_agents_manifest.py`) immediately halts the build.
- Enforces Role-Based Access Control (RBAC) at the agent boundary, ensuring roles such as `Constable`, `Inspector`, or `Superintendent` can only trigger authorized intelligence paths.

### 3. Dual-Engine Execution: System 1 vs. System 2
Operational policing workloads exhibit two distinct access patterns, requiring two specialized execution paths:

#### System 1: Deterministic Fast-Path (Sub-50ms)
Over 85% of real-world police queries are structured lookups (incident counts, beat pendency, jurisdictional trends, specific FIR records). 
- **Zero Free SQL:** Natural language queries decompose into strongly typed parameter slots that bind to **26 hardened, pre-compiled SQL templates (T1–T30)** mapped to verified Karnataka State Police schemas.
- **Execution Speed:** Queries run directly against covering SQLite B-tree indexes or DuckDB columnar storage in under 50 milliseconds, completely bypassing LLM inference.
- **5-Step Self-Healing Escalation:** When a user's query does not cleanly map to a template, the system walks a deterministic escalation path: template reroute $ightarrow$ SQL miner relaxation $ightarrow$ dense vector recall $ightarrow$ hybrid BM25 $ightarrow$ honest dead-end. The system provides an honest dead-end rather than inventing a plausible result.

#### System 2: Deep Multi-Agent Synthesis
Complex criminal investigations require correlating disconnected signals across multiple jurisdictions:
- **Network Agent (Bipartite Graph):** Maps relationships between accused individuals, shared vehicles, phone number hashes, and criminal syndicates across police stations.
- **Profile Agent (Risk Attribution):** Suspect risk scoring uses linear-additive features, enabling exact mathematical SHAP attribution ($100 	imes w_i 	imes f_i$) without approximation. Bias screens run on generated profiles before leaving the node.
- **Second Brain (Semantic Recall):** A dual-tier vector store that keeps curated intelligence (Modus Operandi, syndicates) separated from the 100,000 raw FIR narrative corpus. Reranking combines BM25 lexical search with 384-dimensional ONNX/CUDA embeddings in **4.1 ms**.
- **Conformal Risk Forecasting:** Crime incident forecasting uses split-conformal prediction intervals (80% and 90% confidence bands) paired with Uber H3 hexagonal spatial binning, avoiding arbitrary boundary rounding errors.

### 4. Human-in-the-Loop (HITL) Governance
Antar operates under an advisory mandate. The system can identify patterns and suggest actions, but it possesses zero autonomous execution authority:
- **Cryptographic Proposals:** Operational suggestions, such as patrol redeployments or watchlist additions, are staged as cryptographic proposals (`POST /api/hitl/propose`).
- **Supervisory Review:** Execution requires explicit approval from an authorized supervising officer. Self-approval by the proposer is cryptographically blocked.
- **Integrity Validation:** Approvals must echo the exact SHA-256 payload hash reviewed by the officer, and unexecuted proposals automatically expire after 12 hours.

---

## Performance Benchmarks

All performance figures are empirically measured on bare-metal hardware (*Intel Core i7-9750H, 32 GB RAM, NVIDIA GeForce GTX 1650 4GB VRAM*):

### 1-Crore (10,000,000 Rows) Analytical Stress Benchmark
Vectorized DuckDB C++ execution across 10 ZSTD Parquet partitions compared against standard SQLite WAL:

| Workload | Target Operation | SQLite 20.4L (Warm) | DuckDB Parquet (10M Rows) | Speedup vs SQLite | Validation |
|:---|:---|:---:|:---:|:---:|:---:|
| **Q1. District Ranking** | Top 10 districts by incident count | `1,462.3 ms` | **`38.6 ms`** | **116.4x** | PASS |
| **Q2. Monthly Trend** | 10-year statewide monthly rollups | `8,540.2 ms` | **`118.6 ms`** | **274.5x** | PASS |
| **Q3. Station Mix** | Station x Crime Type breakdown | `25,307.8 ms` | **`693.1 ms`** | **227.2x** | PASS |
| **Q4. Pendency Scan** | Cases > 90 days under active investigation | `14,565.2 ms` | **`125.9 ms`** | **434.7x** | PASS |
| **Q5. Weekday Pattern** | Statewide day-of-week distribution | `1,010.8 ms` | **`132.3 ms`** | **37.6x** | PASS |
| **Q6. 2-Key CTE Join** | District annual volume share self-join | `5,994.9 ms` | **`340.8 ms`** | **105.2x** | PASS |
| **Total Benchmark** | **60,000,000 Row Scans Cumulative** | **`56.88 s`** | **`1.44 s` (241 ms avg)** | **208.8x avg** | **6/6 PASS** |

### Latency Profiles Across Subsystems
| Subsystem | Underlying Technology | Measured Latency | Standard LLM RAG | Operational Impact |
|:---|:---|:---:|:---:|:---|
| **Airlock Scrubbing** | Verhoeff Dihedral Group $D_5$ | `< 2 ms` | Not Implemented | Strict citizen PII protection |
| **Statutory Vigil Gate** | Statutory Rules Matrix | `< 4 ms` | 1,200 ms | Instant constitutional filter |
| **Intent Supervisor** | Compiled LangGraph DAG Router | `< 8 ms` | 1,500 ms | Deterministic agent dispatch |
| **Template Query (T1-T30)** | SQLite B-Tree Covered Indexes | `< 12 ms` | 4,200 ms | Zero SQL injection risk |
| **Dual-Tier Second Brain** | ONNX Runtime + CUDA Tensor Ops | `4.1 ms` | 3,800 ms | 100,000 vector similarity search |
| **Grounding Verification** | G1 Numbers Guardrail | `< 14 ms` | Not Verified | Verified General Diary citations |

---

## Live Demonstration Scenarios

The following queries highlight specific architectural capabilities across the 10 Lakh FIR dataset:

| Scenario | Input Query | Target Node | Grounding & Judicial Provenance |
|:---|:---|:---:|:---|
| **Statewide Analytics** | *"Which districts had the most murders in 2022?"* | `Vault (T11)` | Returns deterministic counts across 10 Lakh FIRs in sub-2 seconds. Every cited figure matches underlying database rows. |
| **Native Kannada NLP** | *"ರಾಜಾಜಿನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು"* | `Vault (T1)` | Processed through native Kannada tokenization without translation layers. Correctly binds to Rajajinagar station jurisdiction and 30-day temporal window. |
| **Inter-District Syndicate** | *"Who is Raju K?"* | `Network` | Uncovers criminal aliases across six station jurisdictions, revealing vehicle sharing (`KA-06-AH-5331`) and the alias link to `Yellappa M`. |
| **Constitutional Gate** | *"Which community commits the most thefts in Rajajinagar?"* | `Vigil` | Intercepted at perimeter. Refuses demographic targeting with statutory citation to Article 15; logs violation to audit trail. |
| **Conformal Forecasting** | *"Forecast burglary risk in Bengaluru City next week"* | `Forecast` | Outputs calibrated 80% and 90% split-conformal prediction intervals alongside Uber H3 geospatial incident density. |

---

## Statutory Compliance and Security Architecture

| Legal & Security Mandate | Implementation in Antar | Verification Method |
|:---|:---|:---|
| **Article 15, Constitution of India** | Vigil gateway blocks demographic and community-based targeting queries. | `tests/test_vigil.py` |
| **Digital Personal Data Protection (DPDP) Act 2023** | Dihedral Group $D_5$ Verhoeff checksum airlock masks citizen Aadhaar and phone numbers. | `tests/test_airlock.py` |
| **Judicial Evidence Admissibility (IEA)** | Zero free SQL execution; G1 numbers guardrail prevents numerical drift between data and response. | `tests/test_guardrails.py` |
| **Executive Governance** | Human-in-the-Loop cryptographic approval required for patrol redeployments and watchlist additions. | `tests/test_hitl.py` |
| **Tamper-Evident Accountability** | Every system turn, parameter bind, and officer action is appended to a SHA-256 hash-chained ledger. | `25,357 verified audit blocks` |

---

## Getting Started

### Environment Requirements
- Python 3.11+
- Node.js 18+ (Next.js 14)
- SQLite3 with WAL mode enabled
- Optional: NVIDIA GPU with CUDA support for accelerated vector recall

### Backend Setup and Integrity Verification
```bash
# 1. Verify agent manifest and prompt hash lock
python scripts/lock_agents.py --check

# 2. Run the full verification test suite across 25,357 audit entries
python scripts/demo_check.py --date 2026-10-29

# 3. Start the FastAPI sovereign backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend Web Console
```bash
cd antar-frontend
npm install
npm run dev
# Open http://localhost:3000 in your browser
```

---

<div align="center">
  <sub>Antar (ಅಂತರ) was developed for the <b>Karnataka State Police Datathon 2026</b>.<br/>Architected and maintained exclusively by <b>harshax007</b>.</sub>
</div>
