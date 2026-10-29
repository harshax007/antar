# Antar — Demo Flow & Sample Inputs / Outputs
**Source 6: Step-by-Step Presentation Playbook, Live Prompts, Expected Outputs & Benchmarks**

---

## 1. Hackathon / Datathon Live Demo Playbook

Follow this precise sequence to present Antar to evaluators, police officials, and hackathon judges:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LIVE DEMONSTRATION PLAYBOOK                         │
├───────┬───────────────────┬─────────────────────────────────────────────────┤
│ STEP  │ SCREEN / ROUTE    │ DEMONSTRATION OBJECTIVE                         │
├───────┼───────────────────┼─────────────────────────────────────────────────┤
│ 1     │ /login            │ Sovereign Auth Gate · U-7001 Operations Officer │
│ 2     │ /demo             │ Minimal White Presentation · Technical Manifesto│
│ 3     │ /antar (Chat)     │ Deterministic Vault Query · 38 ms Provenance    │
│ 4     │ /antar (Bilingual)│ Native Kannada Morphological Normalization      │
│ 5     │ /predict          │ Model League: Champion GLM vs Challenger LightGBM│
│ 6     │ /scale            │ 1-Crore Row Analytical Stress Test (10M rows)   │
│ 7     │ /antarBrain       │ 3D Constellation (10,000 records) + 4.1 ms CUDA │
└───────┴───────────────────┴─────────────────────────────────────────────────┘
```

---

## 2. Step-by-Step Demonstration Script

### Step 1: Secure Authentication Gate (`http://localhost:3000/`)
- **Action:** Open `http://localhost:3000/`. The system immediately routes to `/login`.
- **Narration:** *"Antar enforces a strict constitutional role split. We log in as Officer U-7001 (Admin / Operations Officer)."*
- **Click:** Select demo badge `U-7001` and click **Authenticate**. Status updates to *"Access granted"* and transitions directly to `/demo`.

---

### Step 2: Architecture Presentation & Launchpad (`/demo`)
- **Action:** Displays the clean, pristine white minimal interface with signature Antar product cyan accents (`#0A7E8C`).
- **Narration:** *"Police departments cannot rely on probabilistic chatbots that hallucinate penal sections or fabricate suspect links. Antar is a System 1 deterministic engine: 20-agent LangGraph orchestrator, zero free SQL, native Kannada NLP, and mathematical conformal coverage."*
- **Point out:** The Core USPs & Architectural Advantages (Secure AI & PII stripping, AGENTS.md executable specification, C/C++ core computational engines, DAG state machine, Zero-hallucination templates, and System 1 approach) and the Right Column (Why our solution? How we are achieving it? What we are achieving?).
- **Click:** Click **"Explore Antar →"** to launch into the operations console (`/antar`).

---

### Step 3: Deterministic Vault Query (English & GD Provenance)
- **Input Prompt:**
  ```
  Show top 5 police stations by pending FIRs in Bengaluru City
  ```
- **Execution:**
  - Route: Dispatched to `VAULT` (`app/agents/query_agent.py`, Template `T4`).
  - Latency: **~38 ms**.
  - Execution Path: Deterministic fast-path bypasses LLM merge; outputs zero hallucinated figures.
- **Expected Output:**
  ```markdown
  ### Top 5 Police Stations by Pending FIRs — Bengaluru City

  | Rank | Police Station (Unit) | Pending Cases | Oldest Unresolved GD |
  |---|---|---|---|
  | 1 | Madiwala Police Station | 1,428 | FIR-2019-00412 |
  | 2 | Whitefield Police Station | 1,215 | FIR-2020-00891 |
  | 3 | Electronic City PS | 1,142 | FIR-2019-01104 |
  | 4 | Indiranagar PS | 986 | FIR-2021-00234 |
  | 5 | Koramangala PS | 894 | FIR-2020-00561 |

  *Data grounded in verified KSP CaseMaster registry. 100% citation provenance to General Diary entries.*
  ```

---

### Step 4: Native Bilingual Kannada Processing
- **Input Prompt:**
  ```
  ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಅತಿ ಹೆಚ್ಚು ದಾಖಲಾದ ಅಪರಾಧಗಳು ಯಾವುವು?
  ```
- **Execution:**
  - Native Kannada morphological normalizer parses the question directly without translation API latency or data leakage.
  - Matches intent to crime category breakdown in Bengaluru City (`District_CD = 101`).
- **Expected Output:**
  ```markdown
  ### ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ದಾಖಲಾದ ಪ್ರಮುಖ ಅಪರಾಧ ವಿಭಾಗಗಳು (KSP ಅಧಿಕೃತ ವರದಿ)

  1. **ವಾಹನ ಕಳವು (Motor Vehicle Theft - IPC 379 / BNS 303):** 34.2%
  2. **ಮೋಸ ಮತ್ತು ಸೈಬರ್ ವಂಚನೆ (Cheating & Cyber Fraud - IPC 420 / BNS 318):** 22.8%
  3. **ಮನೆಗಳ್ಳತನ (House Breaking Theft):** 16.4%
  4. **ದರೋಡೆ ಮತ್ತು ಸುಲಿಗೆ (Robbery & Extortion):** 8.1%

  *ಮೂಲ: ಅಧಿಕೃತ ಪ್ರಕರಣಗಳ ನೋಂದಣಿ ವಹಿ (CaseMaster Registry). Article 15 ಅನುಸರಣೆ ದೃಢೀಕರಿಸಲಾಗಿದೆ.*
  ```

---

### Step 5: Spatio-Temporal Model League (`/predict`)
- **Action:** Navigate to **Predict** tab in primary navigation.
- **Narration:** *"Instead of trusting a single black-box forecast, Antar runs a continuous tournament between our Unit-Level Poisson GLM Champion and a Global LightGBM Challenger with TreeSHAP driver attribution."*
- **Key Visual Elements:**
  1. **Crowned Winner Badge:** Displays the algorithm with superior PAI@5% (Prediction Accuracy Index) and PEI (Prediction Efficiency Index).
  2. **Conformal Risk Interval:** Displays calibrated prediction intervals (e.g., $14 \pm 3$ incidents) guaranteeing $83\%+$ finite-sample coverage.
  3. **TreeSHAP Driver Drawer:** Exact additive decomposition showing whether risk is driven by recent trend (`last1`), seasonal recurrence (`usual`), or neighbor station spillover (`nbr4`).

---

### Step 6: 1-Crore Row Analytical Stress Test (`/scale`)
- **Action:** Navigate to **Scale** tab in navigation.
- **Narration:** *"To prove Antar can handle state-wide scale over a decade of policing, we stress-tested 10,000,000 FIR records across 10 ZSTD Parquet partitions using DuckDB."*
- **Key Metrics to Highlight:**
  - **Pass Rate:** **100% (6/6 PASS)** highlighted in emerald green.
  - **Average Latency:** **241.60 ms** across 10,000,000 rows (208× speedup over SQLite).
  - **Live Execution:** Click **"Run DuckDB (1-Crore)"** to execute live queries across the 10M-row dataset in real time.

---

### Step 7: 3D Brain Constellation (`/antarBrain`)
- **Action:** Navigate to **Brain** tab in primary navigation.
- **Narration:** *"Our Second Brain indexes 10,000 interconnected FIR records in 3D WebGL space, with vector search accelerated by PyTorch CUDA fp16 on our local GPU."*
- **Visual Features:**
  - **10,000 Connected FIRs:** Clusters by Modus Operandi and cross-case links.
  - **Energy Pulses:** Directional photon pulses traveling along inferred edges.
  - **4.17 ms GPU Recall:** 100,000 384d vector dot-products scanned in 4.1 ms on NVIDIA GeForce GTX 1650.
  - **Adversarial Gate:** Shows the Advocate Agent base-rate audit badge on inferred hypotheses.
