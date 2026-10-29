# Antar — Demo Script (page by page)

Checked against the code and the live databases on 29 Oct 2026. Every number below was measured
or read from the code. Lines in **"quotes"** are written to be said out loud.

---

## 0. The 30-second opening

**"Antar is an investigation assistant for Karnataka Police. An officer asks in English or Kannada,
and Antar answers only from the FIR register: every number has a source, every answer can be
replayed, and anything that touches the real world needs a second officer's approval."**

**Numbers you can safely say**

| Claim | True value | Where |
|---|---|---|
| FIRs in the cloud register | **10 lakh** (1,000,000; 9.49 lakh real rows, 2016 to Mar 2024) | `main.db` |
| FIRs in the Lab register | **20.4 lakh** (2,040,002; 19.9 lakh real) | `main_lab.db` |
| Stress test | **1 crore** rows (a resampled copy of the Lab data, for speed only) | `scale/firs_stress_1cr/` |
| Agents | **20**, declared in `AGENTS.md`; 9 LangGraph nodes | `app/agents/manifest.py` |
| Query templates | **26** officer-facing whitelisted SQL templates (29 in the registry incl. 3 internal) — no free SQL | `app/services/zcql_repo.py` |
| Answer accuracy (Lab gold set) | **93.3%** (140 of 150 questions) | `docs/ACCURACY.md` |
| Latency (Lab, 20 lakh rows, after warm-up) | **~0.8–1.1 s** per question; the very first one ~3.5 s | measured 29 Oct |
| Brain GPU scan | **1.7 ms** for 100,000 vectors on the GTX 1650 (CPU: 62 ms), same top-10 | measured 29 Oct |

---

## 1. Login — `/login`

- **What it does:** signs the officer in. Officer and role travel inside a signed token, and every
  agent checks the role before it runs.
- **Backend:** `app/core/auth_middleware.py`, `app/core/policy.py`
- **Tech:** FastAPI, signed tokens, role ladder (Constable → Inspector → Approver → Superintendent)
- **Say:** **"Every agent checks your rank before it starts. A Constable can't open a suspect profile;
  the agent refuses before it touches the data."**

---

## 2. Ask Antar — `/antar` (`/ask` redirects here)

- **What it does:** chat in English or Kannada, by voice or text. It shows which agents ran, the rows
  behind the answer, a chart, and the citations.
- **Backend APIs:** `/api/chat/stream` (SSE), `/api/vigil/scan`, `/api/orchestrator/status`,
  `/api/translate`, `/api/voice/tts`, `/api/feedback`, `/api/session/save`, `/api/graph/`
- **Pipeline:**
  1. **Vigil** screens the question.
  2. The **supervisor** routes it.
  3. A **whitelisted template** runs.
  4. Agents fan out.
  5. **Synthesize** composes the answer.
  6. Guardrails check every number.
- **Tech:**
  - LangGraph with a SQLite checkpointer, so the case file survives a restart
  - Zoho Catalyst QuickML LLMs, one model per job:
    - chat = GLM-4.7-Flash
    - analysis = Qwen
    - vision = Qwen VL
  - Kannada/English handling, Whisper mic, TTS
- **Demo — click these:**

| Ask | What happens | Time |
|---|---|---|
| `How many murders in 2022?` | Count by district (cloud: Bengaluru City 68, Belagavi 30, Hassan 27; Lab counts are larger because it holds 20 lakh rows) | ~0.9 s warm |
| Same question in Kannada | Same template, same numbers | ~1 s |
| `Who is Raju K?` | T2 + profile agent; 25 matches, S0001 alias "Yellappa", risk 52/100 | 0.2 s |
| `Show thefts by <community>` | **Refused** by Vigil: Article 15, BNSS Sec 173 | 17 ms |
| `Any unusual spikes?` | Alerts: chain snatching, Rajajinagar, 8 vs usual 2 | ~2 s |
| `Which UPI IDs repeat across FIRs?` | T19; `rakesh.pay@ybl` in 18 FIRs across 4 districts | ~0.7 s (was 15 s and a clarifying question; fixed 29 Oct) |

- **Say:**
  - **"The model never writes SQL. It picks one of 26 approved templates; the database answers, and
    the model only words the answer."**
  - **"Kannada or English gives the same template and the same numbers."**
  - On the refusal: **"Antar won't target a community. That's Article 15, and it refuses before any
    data is touched."**
- ⚠ Raju K and the UPI IDs are **demonstration records seeded into the register**. Say "a
  demonstration suspect", never "a real accused".

---

## 3. Brain — `/antarBrain` (`/brain` redirects here)

- **What it does:** semantic recall, i.e. "find FIRs like this one". Two tiers kept apart:
  - a **curated** tier (summaries, MOs, patterns);
  - the **100,000-FIR** corpus, whose hits are tagged *Derived*, meaning a lead, not a finding.
- **Backend APIs:**
  - `/api/dataset/graph`, `/api/brain/activity`, `/api/brain/related`, `/api/pattern`
  - `/api/graph/stats`, `/api/graph/predicted_edges`, `/api/stream/events`
- **Tech:**
  - Retrieval:
    - ONNX embedder (BAAI bge-small-en-v1.5, 384-d)
    - BM25 + vectors merged with Reciprocal Rank Fusion
    - ONNX cross-encoder rerank (ms-marco-MiniLM)
    - MMR for variety
  - Storage: int8 memory-mapped index (38.4 MB for 100k vectors)
  - UI: Three.js constellation
- **Say:** **"A similar FIR is a lead, not evidence, and the label travels with it so the answer can't
  promote it."**
- ✅ **GPU is live on your laptop.** PyTorch 2.5.1 + CUDA 12.1 is in `.venv`. Measured on the
  GTX 1650: **1.7 ms** for 100,000 vectors (CPU: 62 ms), with an identical top-10. At startup the
  log prints `Brain vector search on: cuda:NVIDIA GeForce GTX 1650`; point at it.
  - **Say:** **"A hundred thousand FIR vectors searched on the GPU in under 2 milliseconds, and
    the result is identical to the CPU, so speed never changes the answer."**
  - On the cloud (no GPU) the same code falls back to the CPU automatically.

---

## 4. Map — `/map`

- **What it does:**
  - district map of Karnataka;
  - hotspots, dark zones and **repeat locations**;
  - click any dot to see that day's FIRs, then **"Open the case flow →"**.
- **Backend APIs:**
  - `/api/map/districts`, `/api/map/districts/rich`, `/api/map/district/{id}`, `/api/map/day_cases`
  - `/api/map/repeat_locations`, `/api/map/gi_star`, `/api/map/darkzones`, `/api/map/view_summary`
  - `/api/corridors`, `/api/alerts`
- **Tech:**
  - Leaflet
  - **Uber H3** hex grid at res 10 (~76 m cells)
  - Getis-Ord **Gi\*** hotspot statistics
- **Demo:** zoom into Bengaluru → Repeat Locations → click a dot → Open the case flow.
- **Say:**
  - **"A repeat location is three or more FIRs on two or more days within one ~76-metre hex. That's
    a beat to patrol, not a guess."**
  - **"Hotspots are Gi-star statistics. Red means statistically significant, not just busy."**

---

## 5. Case flow — `/case?id=…`

- **What it does:** one FIR end to end:
  - how it was done;
  - investigation timeline and stage on record;
  - the accused's other FIRs;
  - how similar cases ended;
  - print the case sheet.
- **Backend:** `/api/case/{id}`
- **Demo:** open C00418 (a demonstration record) from the map or from chat.
- **Say:** **"From a dot on the map to the full case history in one click."**

---

## 6. Predict — `/predict`

- **What it does:**
  - risk forecast per district and unit, with alerts and a daily briefing;
  - hypotheses;
  - the **Model League** (baseline vs challenger);
  - **Propose patrol**, which goes for approval.
- **Backend APIs:**
  - Predict: `/api/predict/dashboard`, `/api/predict/board`, `/api/predict/briefing`,
    `/api/predict/engine`, `/api/predict/hypotheses`, `/api/predict/model-card`
  - Forecast: `/api/forecast/hotspots`, `/api/forecast/unit/{id}`, `/api/forecast/outcomes`,
    `/api/forecast/league`
  - Other: `/api/alerts`, `/api/derivation/{id}`, `/api/hitl/propose`
- **Tech:**
  - statistical baseline + **LightGBM Poisson challenger** (Lab only)
  - **conformal prediction bands**
  - every number replayable through `/api/derivation`
- **Say:**
  - **"Every forecast comes with a range, and the range is calibrated. Conformal bands mean that
    about 9 in 10 real outcomes land inside it."**
  - **"Antar suggests a patrol; it can't order one. A supervising officer has to approve it, and
    nobody can approve their own proposal."** Then click **Propose**.
  - **"It forecasts places and times, never people."**
- ✅ The League works in the Lab (LightGBM 4.7 installed; `/api/forecast/league` answers in 0.1 s).

---

## 7. Network — `/network`

- **What it does:** a link graph of accused, co-accused and shared keys (vehicle, phone, UPI).
- **Backend:** `/api/graph/{id}`, `/api/profile/registry`
- **Tech:** graph built from `crime_suspects` and the evidence ledger; force-directed layout.
- **Say:** **"Every link names the shared key. No key, no link."**

---

## 8. Profiles — `/profiles`

- **What it does:** suspect profile with a risk score and **why** (feature attribution) plus a bias
  screen.
- **Backend:** `/api/profile/{id}`, `/api/profile/registry`
- **Tech:** linear additive risk score, so the SHAP attribution is **exact**, not approximated.
  Bias check, PII masking.
- **Say:** **"The score shows exactly which factor added how many points. Nothing is a black box."**

---

## 9. Search & Workbench — `/search` (`/social` and `/money` open views here)

- **Views:**
  - **Profile search:** `/api/profile/search`
  - **Money trail:**
    - what it shows: UPI and account flows across FIRs
    - APIs: `/api/funds/overview`, `/api/funds/trail`, `/api/funds/account/{id}`
  - **Social insights:**
    - what it shows: **aggregate** demographics and district indicators
    - APIs: `/api/social/demographics`, `/api/social/indicators`
  - **OSINT Workbench:**
    - what it shows: open-web scan
    - APIs: `/api/osint/recon`, `/api/osint/investigate`
  - **Hypotheses + Propose:**
    - what it shows: officer hypotheses, a challenge check, and Propose for approval
    - APIs: `/api/hypothesis`, `/api/hitl/propose`
- **Say:**
  - On social: **"Social data is aggregate only, with a non-targeting disclaimer on every answer."**
  - On OSINT: **"This is the only part that leaves the building, and only the identifier the officer
    typed leaves. Everything it finds is labelled UNVERIFIED and never merged into the FIR record."**
  - On hypotheses: **"Before an officer confirms a hypothesis, the Advocate agent argues against it
    with base rates: how many other people would match the same signal by chance. It uses no LLM,
    so it can't hallucinate."**

---

## 10. Trends — `/trends`

- **What it does:** year-on-year and monthly crime trends by head and district.
- **Backend:** `/api/analytics/trends`, `/api/analytics/breakdown`
- **Say:** **"Same register, same numbers as the chat; this is just the chart view."**

---

## 11. Trace / Trust — `/trace`

- **What it does:** replays any answer step by step: which agent ran, which template, which rows,
  and how long each step took. Also checks the audit chain.
- **Backend:** `/api/obs/trace/{id}`, `/api/obs/session/{id}`, `/api/audit/integrity`
- **Say:** **"Any answer can be replayed. If someone edits the audit log, the hash chain breaks and
  this page shows it."**

---

## 12. Approvals — `/approvals`

- **What it does:** the human-in-the-loop queue (patrol redeployments, watchlist adds).
- **Backend:** `/api/hitl/queue`, `/api/hitl/{id}`, `/api/hitl/stats`
- **Rules:**
  - proposer and approver roles are different;
  - no self-approval;
  - the approver signs the exact payload hash they reviewed;
  - written reasons are required;
  - proposals expire (12 h patrol, 72 h watchlist).
- **Say:** **"Two people, every time. And if the request changes after review, the approval doesn't
  match the hash and fails."**

---

## 13. Governance — `/governance`

- **What it does:** a plain-language page on how Antar handles data:
  - the law it works under;
  - masking;
  - retention;
  - what leaves the building;
  - what Antar does not do (forecast people, replace the investigating officer).
- **Say:** **"This is the page we'd hand a legal reviewer."**

## 14. Admin · Audit Log — `/admin`

- **Backend:** `/api/audit`
- **Say:** **"Every request: who asked, what the policy decided, and why."**

## 15. Account — `/account`

- **What it does:** officer home: shift briefing, own approvals, sentinel watches.
- **Backend:** `/api/briefing/shift`, `/api/hitl/stats`, `/api/sentinel`, `/api/audit`

## 16. Docs — `/docs` (`/guide`, `/info` redirect here)

- **What it does:**
  - agent documentation (from `AGENTS.md`);
  - data schema;
  - question bank;
  - the **live accuracy card**.
- **Backend:** `/api/docs/questions`, `/api/predict/engine`, `/api/accuracy`, `/api/accuracy/run`
- **Say:** **"The agent list is generated from a manifest; if the docs and the code disagree, the
  build fails."**

## 17. About — `/about`

- Project overview. No backend.

---

## 18. Lab-only pages (your laptop, not the cloud)

### Scale — `/scale`

- **Backend:** `/api/scale/benchmark`, `/api/scale/run` (results in `public/lab/scale.json`)
- **Tech:** SQLite vs **DuckDB + Parquet**. The 1-crore set is a resampled stress copy.
- **Measured (warm, median):**

| Query | SQLite 20.4 L | DuckDB 20.4 L | DuckDB 1 crore |
|---|---|---|---|
| Q1 District ranking | 2,418 ms | 16 ms | 54 ms |
| Q2 Monthly trend | 2,805 ms | 20 ms | 72 ms |
| Q3 | 5,980 ms | 139 ms | 702 ms |
| Q4 | 22,670 ms | 29 ms | 163 ms |
| Q5 | 1,364 ms | 27 ms | 202 ms |
| Q6 | 11,090 ms | 49 ms | 328 ms |

- **Say:** **"On 20 lakh rows the columnar engine is about a hundred times faster. On 1 crore rows,
  every query still finishes under a second."**
- ✅ The "Run" button works live (DuckDB 1.5.6). Re-measured 29 Oct: Q1 on 1 crore = 128 ms, on
  20 lakh = 18 ms.

### Presentation — `/hook` and `/demo`

- Full-screen Three.js presentation pages. No live backend.
- `/hook` has a "GPU 4.1 ms" card. On your laptop it is actually faster (1.7 ms), so the claim
  holds.

---

## 19. Q&A — short, true answers

**"How do you stop hallucination?"**
- **"Three layers."**
  1. **"The LLM never writes SQL; it picks one of 26 templates."**
  2. **"Every number in the answer is checked against the rows returned; a number that isn't there
     is removed."**
  3. **"If nothing matches, Antar says so instead of guessing."**
- **"On our 150-question gold set it gets 93.3% right."**

**"Is this real data?"**
- **"The FIR register is real Karnataka police data from 2016 to March 2024."**
- **"A small number of rows are clearly marked demonstration records, for example Raju K and the
  UPI cases, so we can demo safely."**
- **"The 1-crore set is a resampled copy, used only to test speed."**

**"What about privacy (DPDP)?"**
- **"Aadhaar, phone, email, UPI, bank account and PAN numbers are masked before any text reaches
  the language model, and again in every answer."**
- **"Aadhaar is detected with its Verhoeff checksum, so a random 12-digit number isn't masked by
  mistake and a real one isn't missed."**
- **"No complainant names, aggregates stay aggregates, and the open web is never mixed into the
  record."**

**"Can it target a community?"**
- **"No. Vigil refuses it under Article 15 before any data is read, and the refusal itself is
  logged."**

**"Can it act on its own?"**
- **"No. It only proposes. Patrols and watchlists need a second officer's approval, with a written
  reason, on a hash-locked payload."**

**"What runs where?"**
- **"Backend: FastAPI on Zoho Catalyst AppSail (Docker)."**
- **"Frontend: Next.js, a static export on Catalyst."**
- **"LLMs: Catalyst QuickML. GLM-4.7-Flash for chat, Qwen for analysis, Qwen VL for documents."**
- **"Search: ONNX models on CPU."**
- **"Agents: LangGraph."**

---

## 20. Fixes to the draft script — don't say these

| Draft said | Say instead |
|---|---|
| "26 templates" | ✅ correct: 26 officer-facing (29 in the registry, 3 are internal) |
| "PyTorch CUDA GPU 4.1 ms" | OK on the laptop: **1.7 ms** on the GTX 1650. On the cloud it runs on the CPU |
| "Sub-2 seconds across 10 lakh FIRs" | **about 1 second across 20 lakh FIRs** (Lab, after warm-up) |
| "Raju K" as a real person | a **demonstration** suspect |
| "Aadhaar scrubbed at ingestion" | masked **before text reaches the LLM and in every output** |
| "1-crore" as real FIRs | a resampled **stress copy** for speed testing |
| "No-hallucinated-number rate 14.7%" (`ACCURACY.md`) | **don't quote it**; the checker counts legal section numbers (IPC 323/504/506), "60/90-day" limits and per-station breakdowns as invented numbers |

---

## 21. Run the Lab demo: steps

1. **Close the other 3D tabs** (/hook, /demo, Brain) left over from earlier, or restart the
   browser. Each one holds a GPU context, and the browser stops at about 16.
2. **Start the Lab backend.** In the Claude app, use preview `antar-lab-backend`. Or in PowerShell:
   ```powershell
   $env:TMP="D:\tmp"; $env:TEMP="D:\tmp"; $env:ANTAR_EDITION="lab"; $env:ANTAR_DB="main_lab.db"; $env:ANTAR_TODAY="real"; $env:ANTAR_FORECAST_AS_OF="real"; $env:ANTAR_SCALE_DIR="D:\Project\scale"; D:\Project\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```
3. **Wait for `Background warmup completed successfully!`** (about 70 s). Check that the log shows:
   - `Brain vector search on: cuda:NVIDIA GeForce GTX 1650`
   - `LLM warm-up OK (chat model)` and `(analysis model)`
4. **Start the frontend** (only one `next dev`): preview `antar-frontend`, or
   `cd D:\Project\antar-frontend; $env:NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"; npm run dev`
5. **Check health:** `http://127.0.0.1:8000/api/health` must show `"edition": "lab"` and
   `"today": "2024-03-10"`.
6. **Ask one practice question** (`How many murders in 2022?`) before the audience arrives. It
   pulls the database pages into memory (~3.5 s once); after that every answer takes about 1 s.
7. **Open the pages in demo order:** /antar → /antarBrain → /map → /case → /predict → /approvals
   → /trace → /scale → /governance.
8. **Plug in the charger.** On battery, Windows may switch the GTX 1650 off and the Brain falls back
   to the CPU (still correct, just 62 ms).
