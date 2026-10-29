# Antar — Master Study Handbook & Ground Truth Reference
**The Comprehensive Technical, Architectural, and Operational Manual for Karnataka Police Intelligence**

---

## Navigation & Study Guide Sources
This master guide consolidates the 6 authoritative ground truth study documents created for Antar:

1. [**01_ARCHITECTURE_AND_COMPONENTS.md**](file:///d:/Project/docs/study/01_ARCHITECTURE_AND_COMPONENTS.md): System topology, Next.js frontend, LangGraph 20-agent orchestrator, agent roles, compute engines, and single-agent fast-path synthesis.
2. [**02_TECH_STACK_AND_MODELS.md**](file:///d:/Project/docs/study/02_TECH_STACK_AND_MODELS.md): Complete library version matrix (FastAPI 0.115.5, LangGraph 0.6.11, DuckDB 1.5.6, PyTorch 2.5.1+cu121), models (BGE-Small ONNX, LightGBM Poisson GBDT, Unit Poisson GLM), TreeSHAP attributions, and Mondrian split-conformal calibration ($83\%+$ coverage).
3. [**03_CODE_MODULES_AND_AGENT_WORKFLOWS.md**](file:///d:/Project/docs/study/03_CODE_MODULES_AND_AGENT_WORKFLOWS.md): Codebase directory tree, execution lifecycle sequence, supervisor routing logic, Query Agent self-healing ladder, Advocate Agent falsification, and G1–G6 deterministic guardrails.
4. [**04_DATA_SOURCES_SCHEMAS_APIS.md**](file:///d:/Project/docs/study/04_DATA_SOURCES_SCHEMAS_APIS.md): Storage tiers (`main_lab.db` with 2,040,002 rows, `scale/firs_stress_1cr/` with 10M rows, `intelligent.db` with 10k nodes), official KSP ER schema tables (`District`, `Unit`, `CaseMaster`, `ActSectionAssociation`), and full FastAPI REST/SSE endpoints.
5. [**05_DEPLOYMENT_SECURITY_LIMITATIONS.md**](file:///d:/Project/docs/study/05_DEPLOYMENT_SECURITY_LIMITATIONS.md): Startup commands, environment configuration, zero free SQL threat mitigation, Vigil Article 15 compliance screening, Verhoeff $D_5$ Aadhaar masking, disjoint HITL approval ledger, and statutory boundaries.
6. [**06_DEMO_FLOW_AND_SAMPLE_IO.md**](file:///d:/Project/docs/study/06_DEMO_FLOW_AND_SAMPLE_IO.md): Complete Datathon Demo Day presentation script, sample English/Kannada inputs and outputs, Model League tour, 1-Crore stress test demo, and 3D Brain WebGL walkthrough.

---

## Executive Summary & Core Numbers (Empirically Measured)

| Metric | Measured Value | Benchmark Ground Truth |
|---|---|---|
| **Gold Suite Accuracy** | **93.3%** | 140/150 passed on bilingual gold benchmark (`docs/ACCURACY.md`) |
| **Gold Suite Latency** | **38 ms** (p50) / **3.89s** (p95) | Tested across 2,040,002 official KSP FIR records |
| **1-Crore Stress Pass Rate** | **100% (6/6 PASS)** | Analytical query suite over 10,000,000 Parquet rows (`scale/`) |
| **1-Crore Average Latency** | **241.60 ms** | 208.8× average speedup over SQLite |
| **GPU Vector Scan Latency** | **4.17 ms** | 100,000 384d int8 vectors on NVIDIA GeForce GTX 1650 |
| **Bilingual Support** | **Native Kannada & English** | Direct morphological normalization without external API latency |
| **Link Intelligence** | **84.2%** | 8,417 synthetically linked records across 10,000 dense FIRs |
| **Human-In-The-Loop Security** | **Cryptographic SHA-256** | Disjoint Proposer (Admin) vs Approver (Supervising Officer) |
