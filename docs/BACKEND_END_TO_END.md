# Antar backend, end to end

What each part does, how it works, where it lives, and what is worth researching to improve it
before the build is finalised. Written from the code as of 2026-10-22, not from older docs.

Read it in this order: **1. the stack**, **2. the data**, **3. how a question is answered**, then
the feature sections (4-14), then **15. what to finalise**.

---

## 1. The stack

| Layer | Technology | Where |
|---|---|---|
| API server | Python 3.11, FastAPI, Uvicorn; 45 routers mounted under `/api/*` | `main.py`, `app/api/` |
| Agent graph | LangGraph 0.6 (supervisor -> workers -> synthesize), durable SQLite checkpointer | `app/agents/graph.py`, `state.py`, `checkpoint_store.py` |
| Agent contract | `AGENTS.md` is parsed at import; a test fails the build if the graph and the doc disagree | `app/agents/manifest.py`, `tests/test_agents_manifest.py` |
| Language model | Zoho Catalyst QuickML (Qwen 3.6 for analysis, GLM-4.7-Flash for chat, VL-Qwen 3.6 for scans); provider is a setting (`ANTAR_LLM_PROVIDER`: quickml or any OpenAI-compatible server) | `app/services/llm.py`, `quickml.py` |
| Data | SQLite locally (`main.db`, 1.5 GB); Catalyst Data Store (ZCQL) in the cloud, same templates | `app/services/zcql_local.py`, `zcql_repo.py`, `app/core/catalyst.py` |
| Retrieval | BGE-small embeddings (ONNX, 384-d), int8 memory-mapped vectors, BM25, cross-encoder rerank | `app/second_brain/`, `app/services/hybrid_index.py` |
| Statistics / ML | NumPy, SciPy, scikit-learn, pandas, NetworkX | `app/forecast/`, `app/services/anomaly.py`, `network_agent.py` |
| Speech and language | Bhashini (ASR + translation, with an offline dictionary fallback), gTTS | `app/services/bhashini.py`, `app/api/voice.py`, `translate.py` |
| Logging / tracing | structlog; own trace store, eval set, LLM judge | `app/obs/`, `app/core/reasoning_logger.py` |
| Deployment | Docker (`Dockerfile`, `Dockerfile.onnx`), Zoho Catalyst AppSail (`app-config.json`, `catalyst.json`) | repo root |
| Frontend (for context) | Next.js 14, React 18, Leaflet / react-leaflet, React Flow, Recharts, framer-motion | `antar-frontend/` |
| Tests | 131 test files (pytest) | `tests/` |

**Research:** whether to keep SQLite for the demo and Catalyst Data Store for production, or move
to Postgres + pgvector; ONNX Runtime vs PyTorch for the embedder on Catalyst's CPU; the QuickML
model choice (latency vs Kannada quality); LangGraph upgrade path.

---

## 2. The data

| Table / store | Rows | What it is |
|---|---|---|
| `FIRs` (exposed as the `crimes` view) | 1,000,000 | The FIR register in the official KSP schema: crime head, district, station, beat, area, date, stage, acts and sections, victims, accused, arrests, coordinates |
| Real register | 2016-2023 | Partial: about a third of each year is held, so shares are compared, not totals |
| Demonstration rows | 51,329 flagged `is_synthetic_row` (2024-2026) | Seeded so the "today" screens have data; flagged and labelled as demonstration data in answers |
| `suspects`, `crime_suspects`, `victims`, `property` | 2.4k / 6.6k / 2.7k / 3.4k | People and property linked to FIRs |
| `relationships`, `financial_links`, `ext_entity_keys` | 315 / 80 / 50.8k | Links: shared phone, vehicle, UPI, bank, IP keys (the evidence ledger) |
| `Unit`, `stations`, `geo_units` | 1,056 / 61 / 19.7k | Police units, stations, beats and their coordinates |
| `forecast_cube`, `forecast_output`, `forecast_models` | 1.03M / 303k / 144 | Weekly panels, forecasts and fitted models |
| `zone_summary`, `crime_zone_summary`, `monthly_trend`, `year_intel` | small | Pre-computed summaries for fast screens |
| `audit_log` (+ archive) | 9.8k + 11.9k | One hash-chained row per API call |
| `traces`, `agent_reasoning_logs` | 4.5k / 3.9k | How each answer was produced |
| `brain_vectors.db` | 85 MB | Embeddings for the Second Brain (curated tier + 100k-FIR corpus) |

**Research:** how far the demonstration rows can be told apart from real ones on every screen;
whether the 2016-2023 sampling (one third per year) biases any district; data refresh from CCTNS
(format, frequency, de-duplication); a proper data dictionary for the officer-facing fields.

---

## 3. How a question is answered (Chat, end to end)

1. **Sign-in check.** Every request carries a signed token; the auth middleware verifies it,
   checks revocation, and sets the officer and role (`app/core/auth_middleware.py`,
   `security_context.py`, `revocation.py`).
2. **Screening.** Vigil checks the question for prohibited targeting (Article 15: caste,
   religion and the like) and over-collection of personal data before any data is touched
   (`app/agents/vigil_agent.py`). Text that reads as an instruction is refused
   (`app/core/rag_security.py`).
3. **Routing.** The deterministic router (`app/agents/heuristics.py`) maps the question to a
   whitelisted template and its parameters: crime type, district, station, sub-heading, year,
   window. The LLM supervisor (`supervisor.py`) is used for intent when it is available; the
   router is the guaranteed fallback.
4. **Policy.** `app/core/policy.py` decides per agent: DENY if the role is below the agent's
   `min_role`, else PERMIT with obligations (`redact_pii`, `aggregate_only`,
   `label_unverified`, `row_cap`).
5. **Query.** One of **26 public whitelisted templates (T1-T30)** runs; never free SQL
   (`app/services/zcql_repo.py`). Examples: T1 counts and rankings, T13 trends, T20 MO lookup,
   T24 case stages and pendency, T25 sub-headings, T26 weekday and payday patterns, T27
   side-by-side comparison, T28 outcomes by Act, T29 what links two FIRs, T30 festival effect.
6. **Self-heal** when a template comes back empty (`self_heal.py`): reroute to another
   template, relax constraints with the SQL miner (`sql_miner.py`), dense recall, BM25 hybrid
   (`hybrid_index.py`), and if all miss, an honest dead end with the nearest match.
7. **Fan-out.** Other agents add to the answer when routed: network (links), profile (risk
   with exact SHAP attribution), forecast (geo, predict, pattern, alerts), social (aggregate
   only), research (K/D/I/U dossier with the Advocate's rebuttal), brain (semantic recall),
   OSINT (open web, labelled unverified).
8. **Writing.** The deterministic answer writer (`answer_writer.py`) writes the first sentence
   and the ranked evidence from the rows, in English or Kannada. The LLM is called only to merge
   when more than one agent produced a result (`synthesize_node`).
9. **Guardrails after writing** (`app/core/answer_guardrails.py`): every number in the answer
   must appear in the rows (G1), no-result honesty (G2), identifiers (G3), no filler (G4), length
   (G6), no concrete future date (`date_guard.py`).
10. **Streaming.** Server-sent events: each agent's step, then the answer word by word, then
    citations, evidence, visuals and next actions (`app/agents/chat_stream.py`, `app/core/sse.py`).
11. **Record.** Trace, reasoning trail, audit row (hash-chained), session checkpoint
    (`app/obs/trace.py`, `audit_store.py`, `checkpoint_store.py`).

**Research:** routing accuracy on real officer questions (the audit log has them); Kannada
question understanding; latency budget per stage (target under 2 s for single-agent answers);
whether the LLM supervisor adds accuracy over the deterministic router; answer quality via the
eval set and judge (section 13).

---

## 4. Agents (the graph)

Declared in `AGENTS.md`, enforced by `tests/test_agents_manifest.py`.

| Agent | Node | What it does | Role needed |
|---|---|---|---|
| supervisor | own | Intent and routing; clears last turn's state | Constable |
| query | own | Whitelisted templates + self-heal | Constable |
| network | own | Link graph from shared keys (phone, vehicle, UPI), k-core inner circle, brokers | Inspector |
| profile | own | Suspect risk score; linear, so SHAP attribution is exact; bias screen | Inspector |
| forecast | own (hosts geo, predict, pattern, alert_suggest) | Statistical scan shared by four agents | Constable |
| social | own | Aggregate demographic correlation only, with a non-targeting disclaimer | Constable |
| research | own (hosts advocate) | K/D/I/U dossier: Known, Derived, Inferred, Unknown | Inspector |
| advocate_agent | in research | Argues against hypotheses: base rates, multiple-comparisons correction, what would falsify; LLM-free; gates "confirm hypothesis" | Inspector |
| brain | own | Semantic recall over both Brain tiers | Inspector |
| osint | own | Open-web scan, always unverified | Inspector |
| synthesize | own | Composes the answer; LLM merge only for multi-agent turns | Constable |
| vigil, corridor, linkage | API only | Compliance screen; corridor compiler; MO case matcher (must name the shared key) | varies |
| sentinel, products | autonomous | Watchlist tripwires (HITL-gated); product refresh | varies |

**Orchestrator** (`app/core/orchestrator.py`): per-agent timeouts, retries, circuit breakers,
telemetry at `/api/orchestrator/status`.

**Research:** agent-level evaluation (does each agent improve answers?); circuit-breaker
thresholds; whether `social` should exist at all for a police product (fairness review).

---

## 5. Map

| Feature | How | Where |
|---|---|---|
| District choropleth and hotspots | Getis-Ord Gi* over zones for the chosen window (Day / 7 / 28 days) | `app/services/anomaly.py::gi_star_surface`, `/api/map/gi_star` |
| Day view: each FIR | One dot per FIR registered that day; case card (law, stage, victims / accused / arrested), no names | `/api/map/day_cases` |
| Repeat locations | Same ~110 m spot, 3+ FIRs on 2+ days in 90 days; drops online crime, missing persons, CrPC, station default points, unit positions, placeholders, points at sea | `app/services/repeat_locations.py`, `/api/map/repeat_locations` |
| Station / beat forecast layer | From the forecast engine (section 6) | `/api/forecast/layer`, `/hotspots` |
| District card | Day / 7 / 30-day counts, share of state, top crimes | `/api/map/district/{zone}`, `district_cache.py` |
| Corridors, dark zones, anchor areas, KDE | Movement between districts; under-reporting zones; unsolved-case anchors; density | `/api/map/flow`, `/darkzones`, `/anchor_areas`, `geo_density.py` |
| My district | Officer's posting from the token | `auth_api.py`, `accounts.py` |

**Research:** coordinate quality in the register (many points fall in the wrong district or at
the station); beat polygons instead of points; a proper spatial index (H3 or geohash) instead of
3-decimal rounding; what a beat officer needs on a phone at the start of a shift.

---

## 6. Predict (forecasting)

| Part | Method | Where |
|---|---|---|
| Panels | Weekly counts per unit (station or beat) x crime category | `app/forecast/features.py`, `store.py` |
| Baselines | Seasonal naive (same weeks last year), EWMA (half-life 4 weeks), their average | `model.py::baselines` |
| Model | Poisson GLM with a log link and an offset (the unit's shrunk EWMA), learning adjustments: recent vs base, last year, neighbours, season | `model.py::fit` |
| Spread | Over-dispersion estimated from residuals (negative binomial, method of moments) | `model.py::_dispersion` |
| Ranges | Split-conformal on held-out weeks, Pearson-normalised scores, calibrated per volume bin (Mondrian) | `model.py::_calibrate`, `bands` |
| Coherence | Beat forecasts reconciled to their station's | `model.py::reconcile` |
| Back-test and track record | Weekly forecasts graded on the real register; "held in 80% of tested weeks" | `backtest.py`, `docs/FORECAST_BACKTEST.md` |
| Fairness | Disparity checks by area | `fairness.py`, `docs/FORECAST_FAIRNESS.md` |
| Anomaly alerts | MAD-z (robust z), EWMA seasonal, Gi*, conformal bands | `app/services/anomaly.py`, `/api/alerts` |
| Events | Festival dates from a public calendar; the effect of each event measured from past FIRs (event window vs the 4 weeks either side) | `app/services/events.py` |
| Board, briefing, plan | Ranked areas; a worded reading from counted facts (absent if the model adds a number); shift plan per station | `/api/predict/*`, `briefing_agent.py`, `shift_plan.py` |
| Hypotheses | Possible links between accused, priced by the Advocate | `/api/predict/hypotheses`, `advocate_agent.py` |

**Research:** compare with gradient boosting or a hierarchical Bayesian model on the same
back-test; whether calibrated ranges hold for rare crimes; how predictive policing has been
criticised (feedback loops, over-policing) and how Antar answers that (it forecasts reported
FIRs, not people); what a station house officer does with a weekly forecast.

---

## 7. Brain (Second Brain and linkage)

| Part | Method | Where |
|---|---|---|
| Embeddings | BAAI bge-small-en-v1.5 (384-d), ONNX backend, loaded once | `app/second_brain/embedder.py`, `onnx_backend.py` |
| Corpus | Curated tier (summaries, MOs, patterns) + 100,000 FIRs in int8 memory-mapped vectors | `vec_store.py`, `brain_vectors.db` |
| Search | Hybrid: BM25 + dense, fused by reciprocal-rank fusion | `index.py`, `hybrid_index.py` |
| Rerank | Cross-encoder (ms-marco-MiniLM-L-6-v2) + MMR for diversity + zero-parameter attention centrality (corroboration) | `reranker.py`, `attention_rerank.py` |
| Evidence classes | K (known, from the record), D (derived), I (inferred), U (unknown); a similar FIR is D, never promoted | `research_agent.py`, `brain_node` |
| Cross-case links | Primary signal is data overlap (shared phone, contacts across stations); semantic recall enriches | `retrieval.py`, `entity_bridge.py` |
| Entity resolution | Jaro-Winkler + Soundex + substring (names spelled differently) | `app/services/entity_resolver.py` |
| MO matcher, corridors | Must name the shared evidence key | `linkage_agent.py`, `corridor_agent.py` |

**Research:** a multilingual embedder for Kannada text (e.g. multilingual-e5 or IndicBERT
variants); Fellegi-Sunter probabilistic record linkage for people; graph features
(community detection) for gangs; how to show a link's evidence strength to a court.

---

## 8. Search and OSINT

| Part | Method | Where |
|---|---|---|
| Person search | Fuzzy and sound-alike match on name, alias, father's name, phone, vehicle | `entity_resolver.py`, `/api/profile` |
| Identifier decoding | Phone (circle first given), UPI (app and bank), vehicle (RTO), IFSC, bank account, IMEI, website, email, username, name | `app/services/osint_recon.py` |
| Open web | The identifier's exact written forms, India region; a page is kept only if it contains it; weighted on evidence. Engines: Brave (with a key), DuckDuckGo, then Bing; 30-minute cache | `app/services/osint.py` |
| Live registry checks | RBI IFSC list (bank, branch, address), RDAP (website age, registrar), crt.sh (certificates), IMEI check digit | `app/services/osint_checks.py` |
| Official checks | I4C Suspect Registry, Sanchar Saathi (CEIR, KYM, Chakshu), eChallan, Vahan, eCourts, Indian Kanoon, MCA, NCRP 1930, URLhaus, Wayback | `osint_checks.py::official_checks` |
| Notices | Section 94 / 106 BNSS drafts to the record holder (operator, bank, RTO, registrar, email provider) | `osint_recon.py::_build_statutory_requisition` |
| One call | Summary, pages, live checks, official checks, notice, step log | `/api/osint/investigate` |

**Research:** a Brave Search API key (free tier) for reliable search; any API access to the I4C
registry or CEIR for law enforcement (it would turn "open the portal" into a live check); a
username search across platforms (WhatsMyName lists) done lawfully; the DPDP Act's law-enforcement
exemption and KSP's own OSINT SOP.

---

## 9. Voice, language and scanned documents

| Part | Method | Where |
|---|---|---|
| Kannada speech in | Bhashini ASR; offline dictionary fallback so a demo never fails | `bhashini.py`, `/api/voice` |
| Translation | Bhashini, else Google Translate; domain dictionary for police terms | `/api/translate` |
| Speech out | gTTS | `voice.py` |
| Kannada answers | Answer writer writes Kannada directly, not translated | `answer_writer.py`, `dwani_agent.py` |
| Scanned FIRs and CCTV stills | Vision model (VL-Qwen 3.6) OCR; each detail marked from the record, calculated or estimated; record linkage to victims | `forensic_ocr.py`, `forensics.py`, `/api/forensic` |

**Research:** Bhashini production access and latency; Kannada speech in noisy stations;
OCR accuracy on handwritten Kannada FIRs; a Kannada police glossary.

---

## 10. Alerts, watchlists and autonomous work

| Part | Method | Where |
|---|---|---|
| Alerts | Anomaly signals stored and grouped | `alerts_store.py`, `/api/alerts` |
| Sentinel watchlists | Entity, pattern or corridor tripwires; adding a watch is a proposal (HITL) screened by Vigil | `sentinel_agent.py`, `/api/sentinel` |
| Products | Pre-compiled outputs refreshed by the autonomous loop, served with their original timestamp | `product_store.py`, `app/core/worker.py`, `/api/products` |
| Push | Notifications on Catalyst | `push.py` |

**Research:** alert fatigue (how many alerts an officer acts on); deduplication rules; what the
autonomous loop should do overnight.

---

## 11. Human in the loop

Real-world actions (patrol redeployment, watchlist adds) are only proposed by an agent or officer
and executed after a supervising officer approves (`app/core/hitl.py`, `/api/hitl`):
proposer and approver roles are disjoint; no self-approval; the approver approves the exact
payload (SHA-256 echoed back); written reasons required; Vigil screens every proposal;
proposals expire (12 h for patrols, 72 h for watchlists); every step is on the audit hash chain.

**Research:** KSP's real approval hierarchy (who approves what); escalation when nobody approves.

---

## 12. Security and governance

| Control | How | Where |
|---|---|---|
| Sign-in | Accounts with scrypt-hashed passwords, 5-failure lockout, signed tokens with expiry, revocation (one token or all of an officer's) | `accounts.py`, `auth_api.py`, `auth_middleware.py`, `revocation.py` |
| Roles | Constable < Inspector < ... ; Admin, Approver; per-route `require_role` | `auth_middleware.py`, `main.py` |
| Policy | Per-agent sensitivity, minimum role and obligations, decided before the agent runs | `app/core/policy.py` |
| Rate limits | Per-route token buckets | `rate_limiter.py` |
| Outbound calls | Every outside call checked against an allow-list and counted by purpose; `ANTAR_EGRESS_ALLOW=none` stops everything | `app/core/egress.py` |
| Prompt injection | Untrusted text normalised, instruction-shaped spans removed or refused | `rag_security.py` |
| Personal data | PII redaction (phone, Aadhaar, email, PAN) before the model sees text | `guardrails.py` |
| Fair use | Vigil: Article 15 targeting screen, warrant check for PII over-collection | `vigil_agent.py` |
| Audit | One row per API call, hash-chained so tampering shows; archive table | `audit_store.py`, `/api/audit` |
| Sessions | Encrypted session store | `session_api.py`, `sessions.py` |
| Docs | `docs/SECURITY.md`, `docs/SECURITY_SCORECARD.md` | |

**Research:** CERT-In and MeitY guidance for government AI systems; data localisation on
Catalyst (India region); penetration test of the token and HITL flows; key rotation.

---

## 13. Observability and quality

| Part | What | Where |
|---|---|---|
| Traces | Every answer's steps, timings, rows used; shown on Observability & Trace | `app/obs/trace.py`, `/api/obs` |
| Reasoning trail | The "how this was answered" view | `reasoning_logger.py` |
| Eval set | Fixed questions with expected answers, run as a suite | `app/obs/eval.py`, `evalset.jsonl` |
| LLM judge | A strict rater scores answers against the rows the assistant was allowed to use | `app/obs/judge.py` |
| SDAR | Self-distilled training data export from judged answers | `sdar_generator.py`, `/api/obs/export/sdar` |
| Feedback | Thumbs up / down per answer, used to avoid bad suggestions | `/api/feedback` |
| Confidence | Answer confidence; a calibration attempt was rejected on holdout (documented) | `docs/CONFIDENCE_CALIBRATION.md` |

**Research:** grow the eval set from real officer questions in the audit log; measure routing
accuracy, number accuracy and Kannada quality separately; a release gate (no deploy if the
eval score drops).

---

## 14. Exports, jobs and admin

Reports and lead sheets (`/api/export`, printable report pages); long-running jobs
(`/api/jobs`); dataset and admin views (`/api/dataset`, `admin_data.py`); docs demo questions
(`/api/docs/questions`); health (`/api/health`).

---

## 15. What to finalise before calling the build done

Known gaps, most important first:

1. **Overclaims on the Docs stats bar.** It still says "0% hallucination rate" and "0 external
   dependencies". The second is now untrue (OSINT, Bhashini, the event calendar and the LLM all
   call out), and the first cannot be proven. Replace them with measured figures (eval score,
   forecast "held in 80% of tested weeks").
2. **Open-web search reliability.** Keyless engines throttle; set `BRAVE_SEARCH_API_KEY`.
3. **Demonstration data.** 2024-2026 rows are seeded; every screen should say so where it
   matters, and the demo script should lead with 2016-2023 facts.
4. **Coordinates.** Many FIR points are at the station or in the wrong district; the Map now
   works around it (centre placement, filters) but the data needs cleaning at source.
5. **Stale descriptions in code.** For example `quickml.py` still says "Qwen 2.5 14B" while
   settings use Qwen 3.6 / GLM-4.7-Flash. Sweep the module docstrings once.
6. **Kannada coverage.** Newer screens (OSINT tables, Docs tables, some Map cards) are English
   only.
7. **Catalyst deployment.** `main.db` is 1.5 GB: decide what ships to Catalyst Data Store and
   what stays local; check cold-start time with the embedder loaded.
8. **Tests and the live database.** Some tests write to `main.db`; run them only with the
   backend stopped, or point them at a copy.
9. **Eval gate.** Run the eval suite before each demo build and record the score.

Related documents: `AGENTS.md` (agent contract), `docs/MAP_FORECASTING_PLAN.md`,
`docs/FORECAST_BACKTEST.md`, `docs/FORECAST_FAIRNESS.md`, `docs/SECURITY.md`,
`docs/ANTAR_PRODUCT_GUIDE.md`, `PROGRESS.md` (change history).
