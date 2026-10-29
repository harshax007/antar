# Antar — Deployment, Configuration, Security & Limitations
**Source 5: Ground Truth Deployment Procedures, Security Architecture, and Statutory Boundaries**

---

## 1. Deployment & Environment Configuration

Antar is engineered to operate in sovereign, air-gapped on-premise police datacenters or secure government cloud infrastructure (Zoho Catalyst AppSail / NIC Cloud).

### 1.1 Quick Start Procedures
To launch the complete stack locally in the Lab edition:

#### Backend Startup:
```powershell
cd D:\Project
# Ensure temporary directories adhere to local volume paths
$env:TMP = "D:\tmp"
$env:TEMP = "D:\tmp"
# Launch Uvicorn ASGI server with Lab edition configuration
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

#### Frontend Startup:
```powershell
cd D:\Project\antar-frontend
npm run dev
```

- **Backend Gateway:** `http://127.0.0.1:8000` (OpenAPI Swagger docs at `/docs`)
- **Frontend Application:** `http://localhost:3000`

### 1.2 Core Environment Variables (`.env`)
```ini
# Operating Edition
ANTAR_EDITION=lab

# Database Paths
SQLITE_DB_PATH=d:\Project\main_lab.db
INTELLIGENT_DB_PATH=d:\Project\intelligent.db
SCALE_PARQUET_DIR=d:\Project\scale\firs_stress_1cr

# Hardware Acceleration
CUDA_VISIBLE_DEVICES=0
USE_CUDA_VECTOR_STORE=true

# LLM Gateway (Groq / Catalyst fallback)
GROQ_API_KEY=gsk_...
PRIMARY_MODEL=llama-3.3-70b-versatile

# Security & Tokens
JWT_SECRET_KEY=ksp_antar_lab_secure_master_key_2026
SESSION_LIFETIME_SECONDS=86400
```

---

## 2. Security Architecture & Threat Mitigation

Antar enforces an uncompromising defense-in-depth security model:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ANTAR DEFENSE-IN-DEPTH MODEL                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. INGESTION SANITIZATION: Verhoeff D5 Aadhaar Scrubbing + Vigil Article 15 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. QUERY SAFETY: Zero Free SQL · 26 Whitelisted Parameterized Templates    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. CONSTITUTIONAL RBAC: Constable (Aggregate) < Inspector (Case) < Approver│
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. HITL CRYPTOGRAPHIC GATE: SHA-256 Payload Hash Sign-Off · 12-Hour Expiry │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. REPRODUCIBLE AUDIT: Immutable Evidence Ledger & Hash-Chained Logs        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Zero Free-Form SQL Execution
Traditional text-to-SQL allows catastrophic SQL injection or schema manipulation. In Antar:
- LLMs **never generate SQL**.
- Requests map exclusively to 26 hardened templates (`T1–T30`).
- Every parameter (dates, section codes, district IDs) is coerced into strictly typed Pydantic primitives before SQLite or DuckDB binding.

### 2.2 Pre-Execution Compliance Auditor (`vigil_agent.py`)
- **Article 15 Constitutional Guardrail:** India's Constitution explicitly prohibits state discrimination on grounds of religion, race, caste, sex, or place of birth. Vigil screens every user prompt before execution; any query attempting demographic profiling or communal filtering is immediately blocked with statutory reasoning.
- **BNSS Statutory Compliance:** Attaches formal statutory citations (Bharatiya Nagarik Suraksha Sanhita, BNSS Sec 94/106) whenever search, seizure, or arrest warrants are referenced.

### 2.3 Cryptographic Human-in-the-Loop (HITL) Gate (`app/core/hitl.py`)
AI systems must never unilaterally redeploy armed patrols or place citizens on watchlists:
1. **Disjoint Roles:** Proposer and Approver roles are mutually exclusive.
   - Operations Officer (`U-7001 Admin`) can only **propose** actions (`POST /api/hitl/propose`).
   - Supervising Officer (`U-9001 Approver`) can only **review and decide** (`POST /api/hitl/approve`).
   - **Nobody can approve their own proposal.**
2. **Cryptographic Payload Verification:** The proposal endpoint generates an immutable SHA-256 digest of the action payload. The approver must submit the exact matching hash; if the payload was modified in transit, approval is rejected.
3. **12-Hour Expiration:** Stale proposals automatically expire after 12 hours.

---

## 3. Statutory Boundaries & System Limitations

Antar is explicitly engineered with operational boundaries to preserve evidentiary standards:

1. **Refusal of Creative Writing (Not a System 2 Chatbot):**
   Antar refuses to write speculative crime fiction, brainstorm hypothetical penal charges, or engage in unconstrained chit-chat. It operates strictly over registered General Diary rows and verified crime ledgers.
2. **Mandatory Anchor Resolution:**
   Antar will not perform broad, untargeted web or suspect scans. A valid anchor (registered FIR number, suspect identifier, or verified station code) is mandatory before dossier compilation commences.
3. **Strict Date Guard (`date_guard`):**
   No concrete future calendar date is permitted in forecasting output. Predicting that *"A robbery will happen on MG Road on November 12"* is unscientific and legally hazardous. Instead, Antar outputs calibrated relative risk windows (*"Elevated risk: Days +3 to +7, 83% conformal coverage"*).
4. **Adversarial Gate on Suspect Hypotheses:**
   An investigator cannot accept an inferred connection (`[I]`) into the official record without submitting to the Advocate Agent's base-rate challenge (`POST /api/hypothesis/{id}/confirm`), creating a permanent audit trail of whether the officer acknowledged the statistical counter-argument.
