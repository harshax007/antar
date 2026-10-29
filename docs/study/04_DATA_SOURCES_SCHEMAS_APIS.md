# Antar — Data Sources, Schemas, APIs & Integrations
**Source 4: Ground Truth Database Schemas, Official KSP Tables, and API Specifications**

---

## 1. Ground Truth Data Stores

Antar is backed by three distinct data storage tiers, each tailored to specific operational requirements:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             ANTAR DATA STORAGE TIERS                         │
├─────────────────────────┬─────────────────────────┬─────────────────────────┤
│ TIER 1: SQLite OLTP     │ TIER 2: DuckDB Parquet  │ TIER 3: Intelligent DB  │
│ main_lab.db (2.3 GB)    │ scale/firs_stress_1cr/  │ intelligent.db (10k)    │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ • 2,040,002 Real FIRs   │ • 10,000,000 Stress Rows│ • 10,000 Linked Records │
│ • WAL mode enabled      │ • 10 ZSTD Partitions    │ • 8,417 Multi-Hop Links │
│ • 1,075 Police Stations │ • 206.5 MB Compressed   │ • Cross-district MO     │
│ • Full ER Schema Tables │ • Vectorized Scan Engine│ • Shared Vehicles & UPI │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

---

## 2. Official Entity-Relationship (ER) Schema Tables

Implemented in `main_lab.db` (verified via `tests/test_er_tables.py` with zero foreign-key errors):

### 2.1 Core Relational Tables
1. **`District`:**
   - Primary Key: `District_CD` (INTEGER)
   - Columns: `District_Name` (TEXT), `State_CD` (INTEGER, set to `29` for Karnataka).
   - Contains all 30 Karnataka revenue/police districts plus `ISD Bengaluru` (Internal Security Division).
2. **`Unit`:**
   - Primary Key: `Unit_CD` (INTEGER)
   - Foreign Key: `District_CD` $\rightarrow$ `District.District_CD`
   - Columns: `Unit_Name` (TEXT), `Unit_Type` (TEXT e.g., 'Law & Order', 'Traffic', 'Cyber Crime').
   - Contains all **1,075 police stations** across Karnataka.
3. **`CaseMaster` (2,040,002 rows):**
   - Primary Key: `FIR_ID` (INTEGER)
   - Foreign Keys: `District_CD`, `Unit_CD`
   - Columns:
     - `CrimeNoOfficial` (VARCHAR 18): Strict official 18-digit identifier: `1{did:04}{uid:04}{yr:04}{serial:05}`.
     - `Registration_Date` (DATE), `Incident_Date` (DATE).
     - `Status` (TEXT: 'Pending', 'Chargesheeted', 'Convicted', 'Disposed').
     - `Brief_Facts` (TEXT): Bilingual General Diary narrative.
4. **`ActSectionAssociation` (2,040,002 parsed rows):**
   - Foreign Key: `FIR_ID` $\rightarrow$ `CaseMaster.FIR_ID`
   - Columns: `Act_Description` (TEXT), `Section_Description` (TEXT), `Punishment_Type` (TEXT).
   - Maps statutory legal penal sections (IPC sections 302, 379, 420; BNS sections 103, 303, 318; Arms Act, NDPS Act). Resolution rate $> 99.8\%$.
5. **`Employee` (53,881 records):**
   - Columns: `Employee_ID` (INTEGER), `Name` (TEXT), `Rank` (TEXT: 'PSI', 'PI', 'DySP'), `Unit_CD` (INTEGER).
6. **`CaseInvestigatingOfficer`:**
   - Connects `CaseMaster` to `Employee`, tracking assignment history and chargesheet pendency.

### 2.2 Honest Anonymization & Aggregate Views
- **`arrest_counts` & `case_person_counts`:** Real per-FIR statistical counts of arrested persons and suspects.
- **Honestly Empty Person Tables (`Accused`, `Victim`, `ComplainantDetails`):** In strict adherence to the datathon challenge rules and personal privacy regulations, direct civilian identifiers are omitted. Instead, metadata notes in `ext_schema_notes` document that official FIRs carry masked token references (`P-XXXX`) rather than fabricated civilian names.

---

## 3. High-Performance Columnar Parquet (`scale/`)

To stress-test Antar at massive enterprise scale, a 1-Crore dataset was synthesized using PyArrow:
- **Location:** `d:\Project\scale\firs_stress_1cr/`
- **Volume:** **10,000,000 rows** partitioned into 10 ZSTD-compressed Parquet files (`part_0.parquet` to `part_9.parquet`).
- **File Footprint:** **206.5 MB** on disk (representing a ~91% compression ratio compared to raw tabular SQL).
- **Execution Performance (DuckDB 1.5.6):**
  - **Q1 (District Ranking):** Scans 10M rows in **16.1 ms** (150× faster than SQLite).
  - **Q4 (Pendency Scan):** Scans 10M rows in **29.3 ms** (773× faster than SQLite).
  - **Q6 (2-Key Entity Join):** Scans 10M rows in **49.4 ms** (224× faster than SQLite).
  - **Overall Average Latency:** **241.60 ms** across the analytical query suite.
  - **Test Pass Rate:** **100% (6/6 tests passed)**.

---

## 4. Production API Route Specifications

All endpoints are mounted on the FastAPI gateway at `http://127.0.0.1:8000`:

| Endpoint | Method | Role Required | Request Payload / Params | Response Summary |
|---|---|---|---|---|
| `/api/chat_stream` | `POST` | `Constable` | `{ "prompt": str, "session_id": str }` | Server-Sent Events (SSE) stream of agent reasoning, tokens, and citations |
| `/api/accuracy` | `GET` | `Constable` | None | Returns the 150-question bilingual gold benchmark summary (93.3% accuracy, 38 ms median latency) |
| `/api/accuracy/run` | `POST` | `Admin` | `{ "category": Optional[str] }` | Executes gold suite benchmark tests on demand |
| `/api/scale/benchmark`| `GET`| `Constable` | None | Returns latest 1-Crore stress test benchmark metrics and engine comparisons |
| `/api/scale/run` | `POST` | `Admin` | `{ "engine": "duckdb" \| "sqlite" }` | Runs live analytical queries against 1-Crore Parquet or SQLite |
| `/api/forecast/league`| `GET`| `Constable` | `?unit_cd=...&horizon=7` | Champion vs Challenger tournament table, PEI index, and crowned winner |
| `/api/forecast/league/explain`| `GET`| `Constable` | `?unit_cd=...&horizon=7` | Exact TreeSHAP feature attributions grouped into operational drivers |
| `/api/dataset/graph` | `GET` | `Constable` | `?limit=10000` | Returns 10,000 linked FIR records, nodes, and edges for the 3D Brain |
| `/api/schema/er` | `GET` | `Constable` | None | Official ER schema table status and fill-rate metrics |
| `/api/hitl/propose` | `POST` | `Admin` | `{ "action_type": str, "payload": dict }`| Proposes real-world action (patrol redeploy, watch); returns SHA-256 proposal hash |
| `/api/hitl/approve` | `POST` | `Approver` | `{ "proposal_id": str, "payload_hash": str }`| Cryptographically signs and executes an approved action |
| `/api/hitl/deployments`| `GET`| `Constable` | None | Returns immutable audit log of executed redeployments |
| `/api/hypothesis/{id}/challenge`| `GET`| `Inspector`| `id: str` | Read-only preview of Advocate Agent Bayesian rebuttal and base-rate check |
| `/api/hypothesis/{id}/confirm`| `POST`| `Inspector`| `{ "acknowledge_challenge": bool, "reason": str }` | Gates Inferred $\rightarrow$ Known hypothesis promotion |
| `/api/auth/login` | `POST` | Public | `{ "user_id": str, "password": str }` | Issues signed Bearer token with expiration |
| `/api/health` | `GET` | Public | None | System status, database health, and edition metadata (`lab`) |
