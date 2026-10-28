# 06 — Complete Jury Q&A Preparation (66 Questions Across 12 Categories)

> **How to use on stage (5-min Q&A window `12:38 – 12:43 PM`):** Always deliver the **30-Second Answer** first and stop talking! Only give the **Deeper Answer** if the judge nods for technical detail. Police officers reward brevity and operational honesty; technical judges reward naming the exact algorithm and trade-off.

---

## Category 1: Product & Policing Operations (Q1–Q6)

### Q1. How is Antar different from putting ChatGPT on top of an FIR CSV?
- **30s:** ChatGPT guesses SQL, hallucinates numbers, leaks prompts externally, and treats coincidences as crime links. Antar never lets an LLM write SQL or invent numbers—it uses 26 parameterized SQL templates, verifies every digit against SQLite rows (`G1`), runs an offline ONNX vector Brain, and includes a mathematical Devil's Advocate that blocks weak suspect links before an officer acts.
- **Deeper:** Single-agent turns bypass LLM rewriting altogether (`synthesize_node`), saving ~4.9s and preventing drift. Every claim is tagged ICD-203 Known/Derived/Inferred/Unknown and hash-chained in `audit_log`.
- **Evidence:** [`app/core/answer_guardrails.py::apply_guardrails`](file:///d:/Project/app/core/answer_guardrails.py#L173), [`app/agents/advocate_agent.py`](file:///d:/Project/app/agents/advocate_agent.py).

### Q2. Can a beat Constable in rural Karnataka use this without knowing English or SQL?
- **30s:** Yes. Constables can ask in Kannada script, transliterated Kannada, or Kannada voice. Our local Kannada suffix stemmer strips inflections like `-ನಲ್ಲಿ` (`ಮೈಸೂರಿನಲ್ಲಿ` → `Mysuru City`) and maps Kannada crime words directly to official SCRB categories without relying on brittle translation.
- **Deeper:** Even with zero internet, `kn_bridge` and `kn_query.py` resolve Kannada district/crime queries deterministically; when online, Bhashini/Dwani adds full voice STT/TTS.
- **Evidence:** [`app/agents/heuristics.py::kn_bridge`](file:///d:/Project/app/agents/heuristics.py#L187), [`app/second_brain/kn_query.py::to_english`](file:///d:/Project/app/second_brain/kn_query.py#L107).

### Q3. Can Antar's output be submitted or defended in court?
- **30s:** Antar is an **investigative decision-support tool**, not primary evidence—the FIR itself remains primary evidence. However, Antar's `/report/{session_id}` export preserves chain-of-custody: exact FIR citations, ICD-203 tags separating `[VERIFIED]` facts from `[INFERRED]` leads, officer identity, and a `DOC_ROOT` SHA-256 hash so any post-hoc edit is provable.
- **Deeper:** Older builds stripped `[INFERRED]` markers in HTML export; we explicitly rewrote `_answer_html()` so inferred hypotheses can never be printed looking like verified facts.
- **Evidence:** [`app/api/export_api.py::_answer_html`](file:///d:/Project/app/api/export_api.py#L115), [`CLAIM_CLASSES`](file:///d:/Project/app/api/export_api.py#L107).

### Q4. How do you stop an AI from profiling or targeting specific castes or religions?
- **30s:** Two hard walls: first, **Vigil** (`vigil_agent`) screens every prompt *before* execution and rejects demographic targeting under Article 15 of the Constitution. Second, our `social` agent carries an enforced `aggregate_only` obligation that strips person/case keys and appends a mandatory non-targeting disclaimer.
- **Deeper:** Forecast features (`app/forecast/features.py`) use **zero** demographic inputs—only historical crime counts, calendar harmonics, exposure, and spatial lag—audited across districts in `app/forecast/fairness.py`.
- **Evidence:** [`app/agents/vigil_agent.py::audit_request`](file:///d:/Project/app/agents/vigil_agent.py#L31), [`app/core/policy.py::apply_obligations`](file:///d:/Project/app/core/policy.py#L138), [`app/forecast/fairness.py::measure`](file:///d:/Project/app/forecast/fairness.py#L43).

### Q5. Why can't an Inspector immediately trigger a patrol redeployment or watchlist from Antar?
- **30s:** Because AI suggestions must never become unilateral field orders. Both `alert_suggest` and `sentinel` enforce `hitl: true`: an Inspector can only **propose** (`HTTP 202`), and a separate supervising officer (`Approver` — SP/DCP) must review and echo the SHA-256 payload hash to execute it.
- **Deeper:** Proposals expire automatically (`12h` for patrols, `72h` for watchlists), and `hitl.py` rejects self-approval even if an officer holds high rank.
- **Evidence:** [`app/core/hitl.py`](file:///d:/Project/app/core/hitl.py), [`AGENTS.md`](file:///d:/Project/AGENTS.md) (`alert_suggest`, `sentinel`).

### Q6. What happens if an officer asks about a crime date in 2025 when the official SCRB dataset ends March 2024?
- **30s:** In Lab real-data mode (`ANTAR_TODAY=real`), `clock.today()` anchors to `2024-03-31`—the exact last day of the official SCRB extract. Queries outside coverage are caught by `outside_record()` and `self_heal._coverage_message`, telling the officer the exact register cutoff instead of returning a misleading "0 crimes."
- **Deeper:** Returning `0` for an unloaded year looks like a crime-free year—a dangerous silent bug in police analytics. Antar distinguishes *"0 crimes occurred"* from *"outside loaded register window."*
- **Evidence:** `app/core/clock.py` `[Lab L1b]`, [`app/agents/query_agent.py::outside_record`](file:///d:/Project/app/agents/query_agent.py#L280), [`app/agents/self_heal.py::_coverage_message`](file:///d:/Project/app/agents/self_heal.py#L207).

---

## Category 2: System Architecture & Multi-Agent Design (Q7–Q12)

### Q7. Why do you have 18 agents instead of 1 LLM with tool-calling?
- **30s:** Because different policing tasks have completely different **legal sensitivities and minimum ranks**. Separating `query` (`Constable`, `case`), `profile` (`Inspector`, `person`), `forecast` (`Constable`, `aggregate`), and `osint` (`Inspector`, `external`, air-gapped) lets `policy.py` enforce rank gates, timeouts, and obligations per capability before code runs.
- **Deeper:** A single tool-calling LLM loop can chain tools in unintended ways (e.g., passing an FIR suspect name into a web search tool). Our architecture makes that physically impossible (`osint` has `graph_node: null`).
- **Evidence:** [`AGENTS.md`](file:///d:/Project/AGENTS.md), [`app/core/policy.py::decide`](file:///d:/Project/app/core/policy.py#L80).

### Q8. What makes `AGENTS.md` "executable documentation"?
- **30s:** Usually architecture docs rot within a week. In Antar, `app/agents/manifest.py` parses every YAML block inside `AGENTS.md` at Python import time to build the orchestrator fleet and supervisor route table, and `tests/test_agents_manifest.py` fails the build if any node, route, or sensitivity tag disagrees with the compiled LangGraph.
- **Deeper:** This eliminated a real production bug where offline route labels (`NETWORK`, `PROFILE`) silently fell back to `query`. Unknown routes now trigger `manifest.unresolved_routes()` and fail CI.
- **Evidence:** [`AGENTS.md`](file:///d:/Project/AGENTS.md), [`app/agents/manifest.py::load`](file:///d:/Project/app/agents/manifest.py#L293).

### Q9. Why does `forecast_node` host 4 sub-agents (`geo`, `predict`, `pattern`, `alert_suggest`) inside one node?
- **30s:** All four read the same statistical scan over the FIR panel. Splitting them into four separate LangGraph nodes would quadruple DB scan work and checkpoint serialization; running them together via `asyncio.gather` inside `forecast_node` shares cached district/panel state while preserving independent per-agent timeouts and degraded fallbacks.
- **Deeper:** Every output passes through `_to_native()` before returning to LangGraph because NumPy scalars break `msgpack` checkpointing.
- **Evidence:** [`app/agents/graph.py::forecast_node`](file:///d:/Project/app/agents/graph.py#L154) & [`_to_native`](file:///d:/Project/app/agents/graph.py#L25).

### Q10. Why do `/api/chat` and `/api/chat/stream` have separate pipelines?
- **30s:** Honest engineering trade-off: `/api/chat` invokes the compiled LangGraph `StateGraph` synchronously for clean API callers and evaluations, while `/api/chat/stream` runs `_run_pipeline()` so granular SSE sub-step events and tokens flush immediately to the UI. Both share the exact same `orchestrator.run_agent()`, `policy.decide()`, and `answer_guardrails`.
- **Deeper:** Unifying `chat_stream.py` onto `app_graph.astream_events()` is on our post-finale cleanup list (~700 lines deduplication), with zero change to agent logic or guardrails.
- **Evidence:** [`app/api/chat_stream.py::_run_pipeline`](file:///d:/Project/app/api/chat_stream.py#L195), [`app/api/chat.py::chat`](file:///d:/Project/app/api/chat.py#L72).

### Q11. How does multi-turn conversation memory avoid contaminating a new question with old citations?
- **30s:** Two mechanisms: `supervisor_node` emits `CLEAR` (`"__CLEAR__"`) reset sentinels on `results`, `visuals`, `citations`, `brain_hits`, and `actions` at the start of every turn, while `sessions.resolve_reference()` carries forward *only* explicit entity pronouns (*"there"*, *"that station"*, *"same year"*).
- **Deeper:** Without `CLEAR`, LangGraph's persistent `SqliteSaver` checkpointer merges previous turn dicts into the new turn's synthesis.
- **Evidence:** [`app/agents/state.py::merge_dicts`](file:///d:/Project/app/agents/state.py#L25), [`app/core/sessions.py::resolve_reference`](file:///d:/Project/app/core/sessions.py#L239).

### Q12. Why is `advocate_agent` strictly LLM-free?
- **30s:** An adversarial auditor that can hallucinate is worse than no auditor at all! Every likelihood ratio and scan-collision probability `advocate_agent` reports is pure arithmetic computed from live SQLite row counts—reproducible on a pocket calculator via `GET /api/advocate-agent/base-rates`.
- **Deeper:** It separates two quantities people often conflate: the **conditional per-signal likelihood ratio** (driving the Bayes posterior update) and the **unconditional pair-collision rate** across scan size $M$ (driving the multiple-testing correction).
- **Evidence:** [`app/agents/advocate_agent.py`](file:///d:/Project/app/agents/advocate_agent.py), [`app/api/advocate_agent_api.py::base_rates`](file:///d:/Project/app/api/advocate_agent_api.py#L65).

---

## Category 3: Backend & Guardrail Engineering (Q13–Q18)

### Q13. Walk me through how `answer_guardrails.py` catches a hallucinated number.
- **30s:** `check_numbers()` (`G1`) extracts every numeric token in the draft prose and compares it against `_allowed_numbers()`—the exact union of numbers present in the SQL result rows, date bounds, and verified counts. If an LLM synthesis invents even one extra number, `apply_guardrails` strips or replaces the prose with deterministic `_fallback_answer()`.
- **Deeper:** Similarly, `check_identifiers()` (`G3`) verifies every `FIR_ID` and `suspect_id` against retrieved records, `enforce_no_result()` (`G2`) blocks speculative filler on 0-row queries, and `date_guard.py` redacts concrete future calendar dates.
- **Evidence:** [`app/core/answer_guardrails.py`](file:///d:/Project/app/core/answer_guardrails.py#L58-L173), [`app/core/date_guard.py::redact_future_dates`](file:///d:/Project/app/core/date_guard.py#L52).

### Q14. What is the 5-stage `self_heal` ladder when a query returns 0 rows?
- **30s:** Instead of failing silently or guessing, `self_heal()` escalates cleanly: (1) check if the date falls outside register coverage, (2) re-route template if intent mismatched, (3) relax secondary filters one-by-one in `sql_miner.mine_until_hit`, (4) run dense ONNX + hybrid BM25 semantic recall, and (5) return an honest dead-end naming the nearest available district/crime match.
- **Deeper:** Crucially, if a filter is relaxed (e.g., widening a sub-head to a crime group), `unapplied()` discloses that adjustment explicitly in the answer and lowers `resolution_fidelity` in the confidence score!
- **Evidence:** [`app/agents/self_heal.py::self_heal`](file:///d:/Project/app/agents/self_heal.py#L217), [`app/agents/query_agent.py::resolution_fidelity`](file:///d:/Project/app/agents/query_agent.py#L164).

### Q15. How is the answer confidence score calculated—is the LLM just rating itself?
- **30s:** Never! LLMs are notoriously overconfident when wrong. `_answer_confidence()` in `chat_stream.py` computes confidence deterministically from **routing certainty**, **filter resolution fidelity** (did every place/crime phrase map cleanly to an SCRB key?), **row evidence support**, and **historical forecast hit-rate caps** (`forecast_outcomes.confidence_cap`).
- **Evidence:** [`app/api/chat_stream.py::_answer_confidence`](file:///d:/Project/app/api/chat_stream.py#L89), [`app/services/forecast_outcomes.py::confidence_cap`](file:///d:/Project/app/services/forecast_outcomes.py#L165).

### Q16. Why did you import `onnxruntime` before `scikit-learn` at line 31 of `main.py`?
- **30s:** Classic systems debugging catch: on Windows and slim Linux containers, `scikit-learn`/`scipy` load one OpenMP runtime (`libiomp5` / `libgomp`) that conflicts with `onnxruntime`'s threadpool initialization if loaded first, causing intermittent segfaults or deadlocks. Importing `onnxruntime` first with `OMP_NUM_THREADS=1` eliminates the collision completely.
- **Evidence:** [`main.py`](file:///d:/Project/main.py#L22-L35).

### Q17. Why does `/api/health` have `llm_ok = True` instead of pinging QuickML on every health check?
- **30s:** Cloud container orchestrators (Zoho AppSail / Kubernetes) hit `/api/health` every 5–10 seconds—that's 8,640 calls a day! Pinging a paid external LLM on every liveness probe would burn quota and kill containers during transient LLM hiccups even though 95% of Antar runs deterministically offline. Real LLM health is tracked passively in `observability.py` and `quickml._breaker_active()`.
- **Evidence:** [`app/api/health.py::health_check`](file:///d:/Project/app/api/health.py#L61), [`app/services/quickml.py::_breaker_active`](file:///d:/Project/app/services/quickml.py#L147).

### Q18. How does CSV upload (`upload_api.py`) safely add new monthly FIR extracts without corrupting the DB?
- **30s:** Two-phase commit with undo! `POST /api/upload/preview` validates schema, coordinates, and duplicate `FIR_ID`s without writing; `POST /api/upload/commit` ingests inside a tracked batch ID and invalidates stale caches (`product_store.invalidate`); and `POST /api/upload/undo` cleanly rolls back that exact batch if an admin spots a bad file.
- **Evidence:** [`app/api/upload_api.py`](file:///d:/Project/app/api/upload_api.py), [`app/services/fir_upload.py`](file:///d:/Project/app/services/fir_upload.py).

---

## Category 4: Database, Data Cleaning & SCRB Schema (Q19–Q24)

### Q19. Why does Cloud have 10 Lakh FIRs (`main.db`) while Lab has ~19 Lakh (`main_lab.db`)?
- **30s:** Zoho Catalyst AppSail has a strict `2 GB` RAM/container budget, so Cloud ships a compressed `10,00,000`-row slice (`main.db.gz` ~152 MB → 1.61 GB uncompressed). Our Lab Edition (`main_lab.db`) tops up all remaining unique `FIR_ID`s from the full `16.74L` SCRB CSV (`scripts/lab/topup_real_firs.py`) to reach the complete **`~19 Lakh`** corpus (`[VERIFY exact count in docs/lab/TOPUP_REPORT.md]`).
- **Deeper:** Top-up uses `INSERT OR IGNORE` on `FIR_ID` via shared normalizer `app/services/fir_clean.py`, keeping 100% of existing indexes and audit rows intact.
- **Evidence:** [`LabBuild_plan.md`](file:///d:/Project/LabBuild_plan.md) (§4 Phase L1), [`app/core/db_path.py`](file:///d:/Project/app/core/db_path.py).

### Q20. Why are `Accused`, `Victim`, and `ComplainantDetails` 0 rows in your derived ER schema?
- **30s:** Because the official Datathon `FIR_Details_Data.csv` released by SCRB strips citizen names and PII—it provides only aggregate gender counts (`Male`, `Female`). Rather than fabricating 19 lakh fake citizen names, we created the exact SCRB ER tables at `0` rows, exploded real multi-statute rows into `FIR_Acts`, rolled up `UnitJurisdiction`, and isolated synthetic demo personas clearly in `suspects` / `ext_synthetic_identity`.
- **Evidence:** `scripts/lab/derive_er_tables.py` `[Lab L2]`, `ext_schema_notes` table in `main.db`.

### Q21. Tell me about data dirty spots you found in the real SCRB CSV and how you handled them.
- **30s:** Four major real-world dirty spots: (1) ~70% of rows lacked valid Karnataka lat/lon (ocean `0,0` or swapped coordinates)—cleaned via Karnataka bounding-box checks (`_in_box`) while preserving raw values in `fir_geo_original`; (2) inconsistent district/unit spellings—canonicalized in `zcql_repo.py`; (3) `MO_Details` present on only ~651 rows—supplemented by crime-head/statute text in Brain indexing; and (4) `ActSection` packing multiple sections into one string—exploded into `FIR_Acts`.
- **Evidence:** [`app/forecast/store.py::_in_box`](file:///d:/Project/app/forecast/store.py#L56), `fir_geo_original` table, [`app/services/zcql_repo.py`](file:///d:/Project/app/services/zcql_repo.py).

### Q22. What are those `S`-prefixed FIR IDs (~1.02 lakh rows) in `main.db`?
- **30s:** Complete transparency: during early 10-lakh DB assembly, ~1.02 lakh `S`-prefixed rows cloned from 2023 records were included alongside synthetic multi-case storylines. We documented this explicitly in `LabBuild_plan.md` §3.1, preserved `main.db` immutably, and ensure we never quote inflated 2023 raw totals without disclosing that slice.
- **Evidence:** [`LabBuild_plan.md`](file:///d:/Project/LabBuild_plan.md#L70-L85).

### Q23. How do you prevent SQLite `database is locked` errors when autonomous background tasks and officers run simultaneously?
- **30s:** Three engineering choices: (1) `WAL` mode allows unlimited concurrent readers alongside one writer; (2) heavy analytical/forecast readers open strictly read-only connections (`mode=ro`); and (3) high-frequency writes (chat turns, request telemetry, case traces, vectors) live in **separate sidecar SQLite files** (`sessions.db`, `obs.db`, `case_file.db`, `brain_vectors.db`), while `audit_store.py` uses `BEGIN IMMEDIATE` with 30s busy timeout.
- **Evidence:** [`app/core/db_path.py`](file:///d:/Project/app/core/db_path.py), [`app/services/audit_store.py::_write`](file:///d:/Project/app/services/audit_store.py#L84).

### Q24. How do you link suspects across stations when Indian names are spelled five different ways?
- **30s:** `entity_resolver.py` combines **Indic phonetic normalization** (`indic_names.py` collapsing aspirated/unaspirated transliterations like *bh/b*, *ee/i*, *mohd/mohammed*), **Jaro-Winkler** string similarity, and **Fellegi-Sunter** probabilistic log-likelihood scoring—and crucially surfaces matches as **suggested leads**, never silently merging database records!
- **Evidence:** [`app/services/entity_resolver.py::FellegiSunterLinker`](file:///d:/Project/app/services/entity_resolver.py#L343), [`app/services/indic_names.py::name_key`](file:///d:/Project/app/services/indic_names.py#L61).

---

## Category 5: Forecasting, Statistics & ML Rigor (Q25–Q32)

### Q25. Why use PAI and PEI instead of RMSE or Accuracy % to evaluate crime forecasts?
- **30s:** Because 85% of beats have zero crimes in a given week—a dumb model predicting `0 everywhere` gets "85% accuracy" and low RMSE while catching **zero crime**! **PAI** (`% crime captured / % map area patrolled`) directly measures what an SP cares about: *if I send patrols to 5% of my jurisdiction, what share of next week's crime happens there?*
- **Deeper:** **PEI** (`PAI / PAI*`) normalizes PAI against a clairvoyant oracle for that exact week (`[0, 1]`), so sparse crime types and dense crime types can be compared fairly.
- **Evidence:** [`app/forecast/backtest.py::_area_hit`](file:///d:/Project/app/forecast/backtest.py#L93) & [`_metrics`](file:///d:/Project/app/forecast/backtest.py#L113).

### Q26. How do you guarantee zero future data leakage in your 23-week forecast backtest?
- **30s:** Rolling-origin cross-validation (`backtest.py`): for each test week $T+1$, feature lags, exposure baselines, GLM/LightGBM weights, NB2 dispersion, **and** split-conformal calibration quantiles are all computed strictly from weeks $\le T$. No future row is ever touched.
- **Evidence:** [`app/forecast/model.py::_valid_origins`](file:///d:/Project/app/forecast/model.py#L96), [`app/forecast/backtest.py`](file:///d:/Project/app/forecast/backtest.py).

### Q27. Why Poisson GLM + Mondrian Split-Conformal instead of standard Gaussian error bars?
- **30s:** Weekly beat crime counts are discrete, non-negative (`0, 1, 2...`), skewed, and overdispersed—Gaussian $\pm 1.96\sigma$ intervals absurdly predict `-3 to +5 burglaries` and undercover spikes! Poisson GLM respects count geometry, NB2 scales variance, and **Mondrian split-conformal** calibrates empirical quantiles per rate bin so 80% and 90% bands achieve true finite-sample coverage on both quiet rural beats and busy urban stations.
- **Evidence:** [`app/forecast/model.py::_calibrate`](file:///d:/Project/app/forecast/model.py#L147) & [`bands`](file:///d:/Project/app/forecast/model.py#L158).

### Q28. Did LightGBM beat your Poisson GLM across every crime category?
- **30s:** `[VERIFY exact category winners in docs/lab/MODEL_LEAGUE.md before stage]` We built the **Model League** specifically because no single model wins everywhere: LightGBM (`objective="poisson"`) captures non-linear lag × seasonal × neighbor interactions on high-volume categories, while regularized exposure-offset Poisson GLM resists overfitting on sparser slices. Showing all 5 models side-by-side lets the data pick the champion per category.
- **Evidence:** `app/forecast/challenger.py`, `app/forecast/league.py` `[Lab L3]`.

### Q29. What happens if patrol deployment actually deters crime in a hotspot—doesn't that create a feedback loop?
- **30s:** Sharpest question in predictive policing! Yes—if patrols deter crime in Beat A, raw counts drop, making a naive model think Beat A is suddenly "safe." Antar records patrol deployments (`hitl.py`) and officer hotspot feedback (`forecast_feedback` / `forecast_outcomes.py`) separately from baseline FIR counts so deterred weeks are flagged during outcome scoring rather than blindly erasing structural risk.
- **Evidence:** [`app/services/forecast_outcomes.py`](file:///d:/Project/app/services/forecast_outcomes.py), [`app/api/forecast_api.py::feedback`](file:///d:/Project/app/api/forecast_api.py#L94).

### Q30. How do you handle under-reporting ("dark figure of crime") in certain stations?
- **30s:** Every police forecast predicts **reported FIRs**, not unreported crime—and we state that upfront in UI disclaimers and `boundaries.py`. Moreover, `anomaly.py::bayesian_silence_probability()` explicitly detects **suspicious reporting drops** (when a busy station suddenly goes anomalously silent compared to its Poisson baseline), alerting supervisors to potential non-registration rather than celebrating a fake drop!
- **Evidence:** [`app/services/anomaly.py::bayesian_silence_probability`](file:///d:/Project/app/services/anomaly.py#L216), [`app/agents/boundaries.py`](file:///d:/Project/app/agents/boundaries.py).

---

## Category 6: Security, Privacy & Governance (Q31–Q37)

### Q31. What stops prompt injection hidden inside an uploaded FIR narrative or OSINT web snippet?
- **30s:** Five defenses in `rag_security.py`: (1) strip invisible zero-width/bidi Unicode control characters (`normalize_untrusted`), (2) scan for override patterns (`detect_injection`), (3) neutralize role-spoofing delimiters, (4) wrap text in per-call randomized `<<<UNTRUSTED_EVIDENCE_nonce>>>` fences (`fence()`), and (5) remember **LLMs cannot execute SQL or approve actions anyway**—the blast radius of prose is bounded by Guardrails `G1–G6` and HITL!
- **Evidence:** [`app/core/rag_security.py`](file:///d:/Project/app/core/rag_security.py#L54-L195).

### Q32. How do you ensure FIR or suspect names never leak to external search engines during OSINT?
- **30s:** Architectural air-gap: `osint` has `graph_node: null` and `routes: []` in `AGENTS.md`, plus `chat_stream.py` explicitly strips `"osint"` as a second guard. Chat **cannot** call OSINT. Only when an `Inspector+` manually types an identifier in `/osint` does it leave the building—and `osint_api.py` imports **zero** FIR/suspect tables, labels all output `UNVERIFIED`, and hashes the searched identifier in `audit_log`.
- **Evidence:** [`AGENTS.md`](file:///d:/Project/AGENTS.md) (`osint`), [`app/api/osint_api.py`](file:///d:/Project/app/api/osint_api.py#L1-L40).

### Q33. How do you redact Aadhaar numbers without accidentally redacting 12-digit case or property IDs?
- **30s:** Regex alone masks every 12-digit number and ruins police serial IDs. `app/core/guardrails.py::verhoeff_ok()` runs the official UIDAI **Verhoeff dihedral group $D_5$ checksum** on 12-digit candidates while protecting case IDs (`_mask_case_ids` / `_restore_case_ids`), redacting real Aadhaar numbers with surgical precision.
- **Evidence:** [`app/core/guardrails.py::verhoeff_ok`](file:///d:/Project/app/core/guardrails.py#L27) & [`redact_pii`](file:///d:/Project/app/core/guardrails.py#L75).

### Q34. What happens if `AGENTS.md` is corrupted or deleted—does your policy layer fail open or fail closed?
- **30s:** **Fails closed!** Check `app/core/policy.py` lines 82–90: if `manifest.load()` reports a broken/unreadable manifest, `decide()` returns `DENY ("agent policy unavailable")` for every non-system request rather than accidentally opening person-level agents to lower ranks.
- **Evidence:** [`app/core/policy.py::decide`](file:///d:/Project/app/core/policy.py#L80-L91).

### Q35. Can another signed-in officer guess a `session_id` URL and read an SP's confidential chat report?
- **30s:** No—`export_api.py::_may_read()` checks `current_identity(request)` against the session's recorded officer list and raises `HTTP 403` unless you are a participant in that conversation or an `Admin`—returning the identical `403` message whether the session exists or not to prevent ID enumeration.
- **Evidence:** [`app/api/export_api.py::_may_read`](file:///d:/Project/app/api/export_api.py#L74-L86).

### Q36. What if an attacker triggers a 500 error to scrape internal file paths or API keys?
- **30s:** `security.py` intercepts every HTTP error and unhandled exception, runs regex secret/URL/Windows-and-Linux-path scrubbing (`scrub_text()`), logs the real traceback internally under `ERR-<10HEX>`, and returns only a plain message + `error_id`. Swagger `/docs` OpenAPI schemas are also disabled automatically when `ANTAR_ENV=production`.
- **Evidence:** [`app/core/security.py::scrub_text`](file:///d:/Project/app/core/security.py#L65), [`public_error`](file:///d:/Project/app/core/security.py#L113), [`install`](file:///d:/Project/app/core/security.py#L168).

### Q37. What happens if an officer's laptop is lost while their 12-hour Bearer token is still active?
- **30s:** Although HMAC tokens are stateless, an Admin can call `POST /api/auth/revoke` (`revocation.py`), which records the token hash or officer ID in SQLite (`revoked_tokens` / `revoked_officers`) cached in memory, invalidating access immediately across the gateway on the very next request.
- **Evidence:** [`app/core/revocation.py::revoke_officer`](file:///d:/Project/app/core/revocation.py#L79), [`app/api/auth_api.py::revoke_officer`](file:///d:/Project/app/api/auth_api.py#L65).

---

## Category 7: Scalability & Performance (Q38–Q43)

### Q38. How does Antar run 100k semantic vectors + ML forecasting + 10L FIRs inside 2 GB RAM on Cloud?
- **30s:** Four memory engineering wins: (1) replaced 2 GB PyTorch with **ONNX Runtime**; (2) split Brain into small RAM index + disk-chunked **int8 `brain_vectors.db`** (`81.6 MB`, scanning 8,192 rows = **3 MB** working RAM); (3) SQLite `mmap` lets the OS page disk blocks cleanly; and (4) single-worker async Uvicorn with `OMP_NUM_THREADS=1` holds steady around **~450–510 MB RSS**.
- **Evidence:** [`app/second_brain/vec_store.py`](file:///d:/Project/app/second_brain/vec_store.py#L22-L63), [`main.py`](file:///d:/Project/main.py#L22-L35).

### Q39. What happens when Karnataka's registry grows from 19 Lakh to 1 Crore or 5 Crore FIRs?
- **30s:** That's exactly what our `/scale` benchmark proves live! Point lookups (`FIR_ID`) stay $O(\log N)$ (`<5 ms`) in SQLite B-Trees, while full-state analytical rollups run on **DuckDB over ZSTD Parquet** (`firs_1cr.parquet`), scanning 1 Crore rows in milliseconds using vectorized SIMD execution (`[VERIFY exact ms in docs/SCALE.md]`).
- **Evidence:** `app/services/scale_bench.py`, `scripts/lab/export_parquet.py` `[Lab L5]`.

### Q40. How many simultaneous officers can one node support under load?
- **30s:** `[VERIFY exact p50/p95 from Locust report in docs/SCALE.md]` Under our 25-concurrent-officer Locust benchmark (`scripts/lab/locustfile.py`) mixing chat, hotspot fetches, and analytical queries, a single node sustains station roll-call spikes cleanly; for statewide 1,049-station rollout, stateless horizontal replicas sit behind Nginx reading shared Parquet/PostgreSQL.
- **Evidence:** `scripts/lab/locustfile.py` `[Lab L5]`.

### Q41. Won't linear chunk scanning in `vec_store.py` get slow at 19 Lakh or 1 Crore vectors?
- **30s:** Great systems question! At `100k` 384-d int8 rows, NumPy dot-products take tens of milliseconds (`38 MB` math). Above ~500k–1M vectors, linear scan crosses ~200–400 ms—at which point we attach an **HNSW / IVF-PQ ANN index** (`usearch` / `sqlite-vec` / `DuckDB vss` partitioned by `Year` or `CrimeGroup`) as Stage 1 before our existing ONNX Cross-Encoder Stage 2. We intentionally avoided unverified native SQLite extensions in the 2 GB Catalyst container.
- **Evidence:** [`app/second_brain/vec_store.py`](file:///d:/Project/app/second_brain/vec_store.py#L28-L31) (documented right in the module docstring!).

### Q42. Why skip LLM synthesis on single-agent turns?
- **30s:** Measured latency & reliability win: when only `query` runs, `answer_writer.py` already writes crisp bilingual prose directly from verified SQL rows in `<50 ms`. Passing it through an external LLM cost an extra **~4.9 seconds** and added zero factual value—so `synthesize_node` invokes LLM merge *only* when $\ge 2$ agents contribute!
- **Evidence:** [`AGENTS.md`](file:///d:/Project/AGENTS.md) (`synthesize` notes), [`app/agents/graph.py`](file:///d:/Project/app/agents/graph.py).

### Q43. How do you prevent expensive weekly forecast refits from freezing live chat?
- **30s:** `app/forecast/child.py` & `refit.py` run model training inside a **separate low-priority subprocess** (`subprocess` isolation) and atomically swap updated rows into `forecast_output`, so the main FastAPI event loop never drops a frame.
- **Evidence:** [`app/forecast/child.py`](file:///d:/Project/app/forecast/child.py), [`app/forecast/refit.py::run_once`](file:///d:/Project/app/forecast/refit.py#L112).

---

## Category 8: "Why X Not Y?" Tech Choice Grill (Q44–Q49)

### Q44. Why 26 SQL Templates instead of fine-tuning a Text-to-SQL LLM (like SQLCoder or DIN-SQL)?
- **30s:** Fine-tuned Text-to-SQL models achieve ~80–88% execution accuracy—meaning **1 in 7 police answers has a subtle wrong `JOIN`, missing `DISTINCT`, or wrong date bound** while looking totally plausible! Whitelisted parameterized templates give **100% SQL validity, zero injection risk, `<50 ms` speed**, and cover virtually all operational police rollup patterns, backed by semantic Brain fallback for unstructured questions.
- **Evidence:** [`app/services/zcql_repo.py`](file:///d:/Project/app/services/zcql_repo.py), [`app/agents/query_agent.py`](file:///d:/Project/app/agents/query_agent.py).

### Q45. Why DuckDB + SQLite instead of PostgreSQL + PostGIS + pgvector?
- **30s:** Zero-daemon portability! An SP office laptop, a 2 GB AppSail container, or an air-gapped police server runs Antar with `python run.py`—no DB cluster admin required. When KSP deploys centrally at SCRB Data Centre, our repository layer (`zcql_repo.py`) swaps cleanly to PostgreSQL/Read-Replica while keeping DuckDB for columnar analytics.
- **Evidence:** [`app/core/db_path.py`](file:///d:/Project/app/core/db_path.py), `app/services/scale_bench.py`.

### Q46. Why `bge-small-en-v1.5` (384-d) instead of a 1024-d or 1536-d OpenAI embedding model?
- **30s:** Three reasons: (1) FIR narratives cannot be sent to external US commercial APIs; (2) `384` dims uses **4× less RAM/disk** than `1536` dims (`384 bytes/row` in int8); and (3) pairing fast `bge-small` recall with our **`ms-marco-MiniLM` Cross-Encoder** reranker beats standalone large bi-encoders on MTEB retrieval accuracy at a fraction of CPU cost.
- **Evidence:** [`app/second_brain/onnx_backend.py`](file:///d:/Project/app/second_brain/onnx_backend.py), [`app/second_brain/reranker.py`](file:///d:/Project/app/second_brain/reranker.py).

### Q47. Why LangGraph instead of CrewAI, AutoGen, or plain `if/else` scripts?
- **30s:** CrewAI/AutoGen rely on conversational agent loops that waste seconds and drift unpredictably; plain `if/else` lacks durable session checkpointing, typed state reducers, and manifest-verified graph topology. LangGraph gives us deterministic DAG execution with SQLite state persistence.
- **Evidence:** [`app/agents/state.py`](file:///d:/Project/app/agents/state.py), [`app/agents/checkpoint_store.py`](file:///d:/Project/app/agents/checkpoint_store.py).

### Q48. Why Next.js + MapLibre GL instead of Streamlit or PowerBI/Tableau?
- **30s:** PowerBI/Tableau can't run conversational Kannada agents, Bayesian hypothesis gates, or 2-officer HITL workflows; Streamlit re-renders whole scripts slowly and breaks on custom mobile/command-center UX. Next.js + WebGL MapLibre compiles to a zero-RAM static CDN bundle with 60fps vector maps.
- **Evidence:** [`antar-frontend/package.json`](file:///d:/Project/antar-frontend/package.json).

### Q49. Why custom HMAC-SHA256 tokens instead of Firebase Auth / Auth0?
- **30s:** Police systems cannot depend on external SaaS auth providers when operating on closed police networks (`KSWAN` / air-gapped LAN). Stdlib `hmac.compare_digest` has zero third-party CVEs, zero internet dependency, and sits cleanly behind KSP's internal SSO gateway.
- **Evidence:** [`app/core/auth_middleware.py`](file:///d:/Project/app/core/auth_middleware.py#L86-L120).

---

## Category 9: Testing, Verification & Quality Assurance (Q50–Q53)

### Q50. How do you know a code change doesn't break a guardrail or agent permission?
- **30s:** `149` automated `pytest` suites (`1,988+` tests) verify manifest-to-graph parity, RBAC denials, Verhoeff PII masking, prompt-injection fencing, split-conformal coverage math, Bayesian likelihood ratios, and hash-chain tamper detection on every change—plus `agent_lock.py` hashes system prompts so silent prompt edits are caught!
- **Evidence:** [`tests/`](file:///d:/Project/tests/), [`app/agents/agent_lock.py::enforce`](file:///d:/Project/app/agents/agent_lock.py#L118).

### Q51. How was your 150-question bilingual gold benchmark (`eval_gold.py`) graded—did an LLM grade itself?
- **30s:** Zero "LLM-as-a-judge" grading! Every gold question in `data/eval/gold_150.json` computes its ground-truth answer via a **direct independent SQL query against SQLite** and checks that Antar's answer contains the exact numeric value / station / statute—or properly refuses out-of-coverage dates.
- **Evidence:** `scripts/eval_gold.py`, `app/api/accuracy_api.py` `[Lab L4]`.

### Q52. How did you validate ONNX model conversion quality?
- **30s:** We ran numerical parity tests comparing PyTorch reference outputs against ONNX `fp32` and dynamic `int8` across real FIR sentences. When dynamic `int8` dropped cosine similarity to `0.85` and broke cross-encoder top-5 rank overlap (`1/5`), [`onnx_backend.py`](file:///d:/Project/app/second_brain/onnx_backend.py) automatically gated it out and pinned verified `fp32` (`cosine = 1.000`).
- **Evidence:** [`app/second_brain/onnx_backend.py`](file:///d:/Project/app/second_brain/onnx_backend.py#L19-L31).

### Q53. Can you prove right now that the audit log hasn't been edited?
- **30s:** Yes—hit `GET /api/audit/verify` (or click Verify on `/audit`). It walks every event from row 1, recomputing `SHA256(prev_hash + canonical_payload)`. Modifying even one character in SQLite flips `valid: false` and pinpoints the exact tampered row index.
- **Evidence:** [`app/api/audit.py::audit_integrity`](file:///d:/Project/app/api/audit.py#L30), [`app/services/audit_store.py`](file:///d:/Project/app/services/audit_store.py).

---

## Category 10: Deployment & KSP Integration (Q54–Q57)

### Q54. How would Karnataka State Police deploy this inside the SCRB Data Centre / KSWAN intranet?
- **30s:** Single Docker image (or bare Linux systemd service) inside SCRB's on-prem server: point `ANTAR_DB_PATH` / read-replica connector at a nightly read-only CCTNS mirror, serve static Next.js + local Karnataka PMTiles behind Nginx TLS (`HttpOnly` cookies + KSP LDAP/SSO), and optionally attach an on-prem GPU running Ollama/vLLM via `app/services/llm.py` (`OPENAI_BASE_URL`) so **zero bytes ever leave police premises**.
- **Evidence:** [`app/services/llm.py`](file:///d:/Project/app/services/llm.py#L48-L60) (`is_local`), [`Dockerfile.onnx`](file:///d:/Project/Dockerfile.onnx).

### Q55. Why maintain both Zoho Catalyst Cloud and Local Lab editions from one codebase?
- **30s:** One codebase, one environment flag (`ANTAR_EDITION=cloud|lab`): Cloud proves lightweight 2 GB edge/mobile viability for field officers right now via QR code, while Lab proves full 19-lakh + 1-croreSCRB data-centre capability without forking the repo.
- **Evidence:** `app/core/edition.py` `[Lab L0]`, `D:\Project` & `D:\Project_Antar`.

### Q56. What happens if Zoho Catalyst AppSail restarts—do you lose audit logs or sessions?
- **30s:** Container local `/tmp` storage is ephemeral across fresh deploys, which we document transparently: in Cloud demo mode, baseline DB stages from `main.db.gz` and audit/embeddings sync hooks (`_sync_to_catalyst_placeholder` / Catalyst Data Store / Stratus S3 bucket in `stratus.py`) back cloud persistence; on-prem mounts persistent NVMe volumes directly.
- **Evidence:** [`app/core/db_path.py::ensure_db_staged`](file:///d:/Project/app/core/db_path.py#L132), [`app/services/stratus.py`](file:///d:/Project/app/services/stratus.py).

### Q57. How does Antar handle cold starts when the Cloud container wakes up?
- **30s:** `main.py` finishes synchronous startup in `<1s` and runs heavy index/ONNX/forecast loading inside an async `background_warmup()` task so `/api/health` responds immediately, while `antar-frontend/lib/api.js` (`waitForServer`) gracefully queues and replays any request arriving during wakeup.
- **Evidence:** [`main.py::background_warmup`](file:///d:/Project/main.py#L46), [`antar-frontend/lib/api.js`](file:///d:/Project/antar-frontend/lib/api.js#L38-L50).

---

## Category 11: Honest Limitations & Future Work (Q58–Q61)

### Q58. Tell me honestly: what are the 3 biggest limitations of Antar today?
- **30s:** Three honest boundaries, all driven by public data or cloud constraints:
  1. **Coordinates & Beat Polygons:** Only ~30% of historical SCRB FIRs carry clean GPS points and beat areas use Voronoi centroid approximations—plugging in official KSP GIS beat shapefiles will sharpen spatial PAI further.
  2. **Sparse MO Text & Anonymized Persons:** Only ~651 SCRB rows populate `MO_Details` and person names are stripped by law—connecting live CCTNS MO narratives and `Accused` views unlocks full cross-station MO power.
  3. **Template Ceiling on Complex Ad-Hoc Joins:** Uncommon 4-way analytical questions outside our 26 templates fall back to semantic recall rather than arbitrary SQL—by deliberate safety choice.

### Q59. Why does `advocate_agent` point out that `research_agent`'s MO match fell back to `occupation`?
- **30s:** Because `suspects.primary_crime` is blank in the current table, `research_agent` falls back to `occupation`—and instead of hiding that limitation, `advocate_agent` catches it automatically, computes the massive population collision rate of common occupations, and flags the hypothesis `WEAKENED` or `COLLAPSES`!
- **Evidence:** [`app/agents/advocate_agent.py`](file:///d:/Project/app/agents/advocate_agent.py#L99-L112).

### Q60. What isn't live in the OSINT Workbench yet?
- **30s:** Public, legal checks (IFSC bank branch lookup, RDAP domain/IP ownership, `crt.sh` TLS certificate logs, Luhn IMEI/card validation, public web dorks, and automated BNSS Sec 94 requisition letters) work live today. Paid or restricted law-enforcement feeds (CDR tower dumps, NATGRID, commercial dark-web breach APIs) are shown only as workflow hooks awaiting official KSP credentials.
- **Evidence:** [`app/services/osint_checks.py`](file:///d:/Project/app/services/osint_checks.py), [`app/services/osint_recon.py`](file:///d:/Project/app/services/osint_recon.py#L492).

### Q61. What are your top 3 priorities for Phase 2 with KSP?
- **30s:** (1) Plug in **official KSP beat boundary GeoJSON polygons** and live nightly read-only CCTNS sync; (2) index full **Kannada + English FIR complaint narratives** on an on-prem SCRB server with HNSW vector partitions; and (3) run a **30-day controlled field pilot** in 2 Bengaluru divisions measuring patrol deterrence with SPs.

---

## Category 12: Hostile / Tricky "Gotcha" Panel Questions (Q62–Q66)

### Q62. *"Predictive policing in the US (like PredPol) was criticized as biased pseudoscience. Aren't you repeating the same mistake?"*
- **30s:** PredPol failed for three specific reasons we explicitly engineered out: (1) it was a proprietary black box—ours is open math with exact TreeSHAP/GLM weights and rolling-origin backtests; (2) it used arrest/stop data for drug/nuisance policing—our strongest signal (`52%` capture, `23/23` weeks) is **reported property crime** (citizen-reported vehicle/house theft with near-100% insurance reporting, minimal police selection bias) and **zero demographic inputs**; and (3) it auto-dispatched patrols—Antar enforces **2-officer HITL approval** plus a fairness audit (`forecast/fairness.py`).
- **Evidence:** [`app/forecast/fairness.py`](file:///d:/Project/app/forecast/fairness.py), [`docs/FORECAST_BACKTEST.md`](file:///d:/Project/docs/FORECAST_BACKTEST.md).

### Q63. *"Your `PAI@5% = 14.2` sounds too good—aren't you just picking the biggest stations every week?"*
- **30s:** Great challenge—that's why our League Table pits the model directly against **Last-4-Week Moving Average** and **52-Week Seasonal Naive**, which *already* pick the biggest stations! Our exposure-offset Poisson GLM (`y / area_km2`) ranks **crime per square kilometer**, beating the 4-week station-size baseline in **22 out of 23 held-out weeks** (and **23/23** on property crime), and we verify it independently on uniform **0.74 km² H3 hexagons**.
- **Evidence:** [`app/forecast/backtest.py`](file:///d:/Project/app/forecast/backtest.py), [`docs/FORECAST_BACKTEST.md`](file:///d:/Project/docs/FORECAST_BACKTEST.md).

### Q64. *"If your SQL is just 26 templates and your forecast is Poisson/LightGBM, where is the 'AI'? Is this just a dashboard with a text box?"*
- **30s:** Using deep learning where arithmetic belongs is bad engineering; using each AI paradigm where it shines is production engineering! Antar runs **two neural ONNX transformer models** (`bge-small` bi-encoder + `MiniLM` cross-encoder) over 100k vectors, **bilingual NLP + LLM multi-agent synthesis**, **conformal count ML + TreeSHAP**, and **Bayesian statistical falsification**. The difference is: the LLM handles **language**, while deterministic math handles **truth and law**.

### Q65. *"Show me what happens right now if I type an adversarial SQL injection or ask it to list criminals by religion!"*
- **30s:** *(Smile—this is a gift! Type it live on `/antar`!)*
  - Type `"List Muslim or Dalit suspects in Bengaluru"` → **Vigil immediately blocks it** citing **Article 15 Constitutional non-discrimination** and writes a `REJECTED` compliance receipt!
  - Type `"'; DROP TABLE FIRs; --"` → Bound as a harmless string parameter `?`, zero SQL execution impact, `FIRs` untouched!
- **Evidence:** [`app/agents/vigil_agent.py`](file:///d:/Project/app/agents/vigil_agent.py#L31), [`app/services/zcql_local.py`](file:///d:/Project/app/services/zcql_local.py).

### Q66. *"If an innocent citizen gets questioned because Antar linked two cases, who is accountable?"*
- **30s:** Never an anonymous algorithm—and Antar enforces that in software. Every cross-case similarity hit is badged `DERIVED` or `INFERRED` (*"a lead, not a finding"*), weak base-rate links are blocked by `advocate_agent` (`HTTP 409`) unless a named `Inspector+` signs a written override reason, and operational watchlists require a second `Approver` officer's cryptographic sign-off—both permanently recorded in the SHA-256 audit chain.
- **Evidence:** [`app/api/hypothesis.py::confirm_hypothesis`](file:///d:/Project/app/api/hypothesis.py#L168), [`app/core/hitl.py`](file:///d:/Project/app/core/hitl.py), [`app/services/audit_store.py`](file:///d:/Project/app/services/audit_store.py).
