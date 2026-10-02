# Graph Report - Antar_FinalBuild_Dev  (2026-09-18)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 4116 nodes · 9015 edges · 182 communities (159 shown, 23 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 175 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3f1d3dd9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- zcql_repo.py
- BrainStructure.jsx
- typing
- build_network
- antar/page.jsx
- test_anomaly_v2.py
- anomaly.py
- gi_star_surface
- get_product
- build_layout
- react
- useLang
- heuristic_select
- test_self_heal.py
- test_answer_guardrails.py
- fuzzy_match_suspects
- test_devils_advocate.py
- query_agent.py
- second_brain/ingestion.py
- sessions.py
- app_services
- SSEQueue
- obs/store.py
- test_bilingual_chat.py
- _rand_unit
- chat_stream.py
- search/page.jsx
- test_hitl.py
- test_agents_manifest.py
- embedder.py
- MapScreen.jsx
- run_multi_module_recon
- evidence_ledger.py
- build_spec
- pattern_predict.py
- test_audit_chain_persistence.py
- quickml.py
- profile.py
- BrainIndex
- RefStrip.jsx
- run_agentic_spine
- test_templates_t19_t23.py
- ungrounded_entity
- redact_future_dates
- hitl.py
- test_research_node.py
- settings.py
- semantic_recall
- jobs.py
- AppShell.jsx
- intent_parser.py
- FastAPI
- dataset.py
- session_api.py
- pytest
- PredictScreen.jsx
- parse_json_response
- anyio
- Constellation3D.jsx
- docs/page.jsx
- TrustDashboard.jsx
- intent_flow.py
- map_and_ingest_csv
- package.json
- devils_advocate.py
- audit_store.py
- index.py
- answer_writer.py
- manifest.py
- Manifest
- admin_data.py
- orchestrator.py
- flags.py
- CrossEncoderReranker
- Any
- test_evidence_ledger.py
- test_research_dossier_fields.py
- _total_like
- profile_agent.py
- test_chat_api.py
- asyncio
- zcql_local.py
- pydantic
- workspace.py
- map_api.py
- voice.py
- re
- trace.py
- stratus.py
- dependencies
- corridor_agent.py
- _get
- anyio
- _fmt
- main.py
- anyio
- asset
- hitl_api.py
- sys
- time
- scan
- test_layer6_geospatial.py
- _get
- export_api.py
- redact_pii
- build_world
- _run_pipeline
- vigil.py
- devils_advocate_api.py
- load.py
- _collect
- _crime_word
- chat.py
- retrieval.py
- second_brain/store.py
- district_cache.py
- test_product_store.py
- _w_trend
- _date
- linkage_agent.py
- app_api
- soundex
- TestGraphCache
- live_stream.py
- auth_middleware.py
- _concept_map
- anyio
- test_session_api.py
- parse_slash_command
- test_geo.py
- fastapi_testclient
- test_linkage_agent.py
- TestDistrictCache
- challenge_dossier
- display_names.py
- test_map.py
- products.py
- TaskWorker
- registry.py
- alert_suggest_agent.py
- _answer_confidence
- overview
- lifespan
- test_briefing_agent.py
- run_research
- state.py
- feedback.py
- conftest.py
- test_predict_dashboard.py
- test_generate_retries_then_raises
- dwani_agent.py
- chat_stream
- health.py
- ops.py
- TestJobs
- AccountPage
- evidence.py
- _strip_reasoning
- TestEntityBridgeEndpoints
- TestMaterializationEndpoints
- next.config.mjs
- get_hypothesis
- evaluator.py
- compilerOptions
- load_sqlite.py
- forensics.py
- TestCorridorEndpoints
- TestSentinelEndpoints
- .__init__
- add_alert

## God Nodes (most connected - your core abstractions)
1. `_run_pipeline()` - 63 edges
2. `react` - 59 edges
3. `useLang()` - 57 edges
4. `query_agent_run()` - 54 edges
5. `_world()` - 51 edges
6. `build_network()` - 51 edges
7. `build_spec()` - 51 edges
8. `get_product()` - 44 edges
9. `put_product()` - 42 edges
10. `run_template()` - 40 edges

## Surprising Connections (you probably didn't know these)
- `TestHNSWIndex` --uses--> `BrainIndex`  [INFERRED]
  tests/test_brain_scale.py → app/second_brain/index.py
- `_reference_bm25()` --uses--> `BrainIndex`  [INFERRED]
  tests/test_brain_hybrid_fusion.py → app/second_brain/index.py
- `test_legacy_rebuild_padding()` --calls--> `BrainIndex`  [EXTRACTED]
  tests/test_vision_integration.py → app/second_brain/index.py
- `TestCircuitBreaker` --uses--> `AgentSpec`  [INFERRED]
  tests/test_orchestrator.py → app/core/orchestrator.py
- `TestRunAgent` --uses--> `AgentSpec`  [INFERRED]
  tests/test_orchestrator.py → app/core/orchestrator.py

## Import Cycles
- None detected.

## Communities (182 total, 23 thin omitted)

### Community 0 - "zcql_repo.py"
Cohesion: 0.06
Nodes (82): AccusedHistory, ActSplit, Aggregate, ast_to_spec(), ASTAggregate, ASTFilter, ASTParams, BeatHotspots (+74 more)

### Community 1 - "BrainStructure.jsx"
Cohesion: 0.05
Nodes (48): BrainHub(), BrainStructure, DataOverview, BrainStructure(), resetScope(), runFind(), runThink(), scopeLabel() (+40 more)

### Community 2 - "typing"
Cohesion: 0.05
Nodes (57): Antar — Forecast Agent (M8, WOW 3) ======================================= Runs…, Antar — Network Agent (M2, M7) =================================== Builds a…, {suspect_id: risk_score} for the whole dataset in one pass (used by the…, risk_scores(), Antar — Research Agent (KUL Layer 0) =====================================…, Antar — Sentinel Agent (A1: Watchlists & Tripwires · honest)…, Antar — Vigil Agent (A5: Bias & Compliance Auditor · Phase 1)…, graph_refresh() (+49 more)

### Community 3 - "build_network"
Cohesion: 0.06
Nodes (37): build_network(), _components(), find(), union(), Connected components via union-find., Cheap risk proxy from prior offences (0–100). Real 4-factor score = Profile…, _risk(), get_graph() (+29 more)

### Community 4 - "antar/page.jsx"
Cohesion: 0.05
Nodes (37): AGENT_MAP, AgentStatusLine(), AnswerBody(), applyEvent(), ChatPage(), patchLast(), playTTS(), pushRecent() (+29 more)

### Community 5 - "test_anomaly_v2.py"
Cohesion: 0.05
Nodes (27): bayesian_silence_probability(), _calibrated_confidence(), _conformal_band(), _ewma(), _gi_star(), _haversine_km(), _mad_z(), Getis-Ord Gi* statistic with binary spatial weights (self-inclusive). Returns… (+19 more)

### Community 6 - "anomaly.py"
Cohesion: 0.05
Nodes (48): Antar — Grounded Follow-up Agent =====================================…, compute_scenario_band(), Antar — Prediction Agent (A9) ================================== Agent…, Compute hypothesis-conditioned scenario band alongside baseline conformal band.…, _breakdown(), demographics(), Antar — Social Insight Agent (M4 / feature N6)…, Victim + offender demographic breakdowns + crime×occupation correlation +… (+40 more)

### Community 7 - "gi_star_surface"
Cohesion: 0.06
Nodes (27): _db(), generate_shift_briefing(), get_shift_briefing(), Any, Connection, Antar — Briefing Agent (A4: Shift Briefings · Phase 1)…, Get shift briefing from Product Store or calculate and cache if missing/stale., Deterministic generator for shift briefings over FIRs and evidence ledger. (+19 more)

### Community 8 - "get_product"
Cohesion: 0.10
Nodes (51): Drop the cached population index (tests, and after a re-ingest)., reset_index(), challenge_hypothesis(), confirm_hypothesis(), _default_hypothesis(), _digest(), HypothesisActionRequest, BaseModel (+43 more)

### Community 9 - "build_layout"
Cohesion: 0.07
Nodes (21): build_custody(), build_layout(), _chart_from_rows(), _date_range(), _headline(), _is_internal(), _num(), Antar — Structured Answer Layout =====================================… (+13 more)

### Community 10 - "react"
Cohesion: 0.06
Nodes (14): DEFAULT_NOTIFS, DEFAULT_PREFS, METHOD_CLS, OFFICERS, clean(), DemoStage(), HoloStage(), ICONS (+6 more)

### Community 11 - "useLang"
Cohesion: 0.07
Nodes (29): AboutPage(), antar_frontend_app_globals, metadata, AlertsDrawer(), AntarBrainNav(), CaseBrain, BrainScreen(), buildDrill() (+21 more)

### Community 12 - "heuristic_select"
Cohesion: 0.07
Nodes (35): _db_places(), _extract_name(), heuristic_select(), is_kannada(), _match_places(), _norm(), Antar — Heuristic Router (offline / DEMO_MODE fallback)…, Whole-word synonym match that also accepts plurals ("robberies", "murders"). (+27 more)

### Community 13 - "test_self_heal.py"
Cohesion: 0.08
Nodes (44): parse_intent(), LLM, Parse `user_text` into a validated Intent. Deterministic first (always), then…, extract_citations(), Pull citation chips from crime rows: {fir, station, date, section} (CCTNS Acts…, _cites(), _dead_end_message(), _fetch_by_ids() (+36 more)

### Community 14 - "test_answer_guardrails.py"
Cohesion: 0.08
Nodes (25): _allowed_numbers(), walk(), apply_guardrails(), cap_length(), check_identifiers(), check_numbers(), enforce_no_result(), _norm_num() (+17 more)

### Community 15 - "fuzzy_match_suspects"
Cohesion: 0.07
Nodes (16): fuzzy_match_suspects(), jaro(), jaro_winkler(), Search suspects by name / alias / father_name using three signals in priority…, Jaro similarity in [0.0, 1.0]., Jaro-Winkler similarity — adds a prefix bonus (up to 4 matching leading chars).…, Exact substring 'Yellappa' matches both alias=Yellappa and full_name=Yellappa M., WOW-2: one-p typo 'Yellapa' must find the Yellappa suspects via Jaro-Winkler. (+8 more)

### Community 16 - "test_devils_advocate.py"
Cohesion: 0.12
Nodes (44): challenge(), Audit one hypothesis. Never raises; returns an 'unassessable' record instead., _hyp(), Antar — Devil's Advocate tests ============================== The point of this…, SURVIVES has to be reachable, and this is what it takes: corroboration from a…, The two probabilities are different quantities; conflating them was the bug.…, research_agent reads primary_crime then falls back to occupation. When it falls…, When primary_crime IS populated, the signal is a genuine MO comparison. (+36 more)

### Community 17 - "query_agent.py"
Cohesion: 0.07
Nodes (41): _adopt_heal_template(), drop_future_rows(), _execute(), _get_cached_query(), _nearest_crimes(), query_agent_run(), Antar — Query Agent (M1, M9) ================================= NL question →…, Say exactly what could not be matched, and offer the nearest real options. (+33 more)

### Community 18 - "second_brain/ingestion.py"
Cohesion: 0.07
Nodes (39): consolidate(), get_activity(), get_learnings(), ingest_session(), get, post, Antar — Brain API (Second Brain · M2)…, related() (+31 more)

### Community 19 - "sessions.py"
Cohesion: 0.08
Nodes (42): chat(), ChatRequest, _explain_reply(), BaseModel, post, Request, Replay the previous answer's reasoning trail in plain language (Explain / M9)., all_turns() (+34 more)

### Community 20 - "app_services"
Cohesion: 0.06
Nodes (30): app_agents, list_alerts(), get, Antar — Alerts API (M8 / F4) ================================= GET /api/alerts…, Antar — Linkage API (A3: MO Case-Matcher · Phase 1)…, create_watch(), get_sentinel_alerts(), get_watches() (+22 more)

### Community 21 - "SSEQueue"
Cohesion: 0.09
Nodes (17): BaseModel, StreamChatRequest, Async queue bridge between the pipeline coroutine and the SSE generator. Usage:…, SSEQueue, json, anyio, TestRunPipeline, TestSSEQueue (+9 more)

### Community 22 - "obs/store.py"
Cohesion: 0.08
Nodes (35): _check_enabled(), get_session(), get_trace(), get_trace_dashboard(), list_sessions(), get, Antar — Observability API (Trace & Telemetry screen)…, Summary KPIs + the most recent turns, newest first. (+27 more)

### Community 23 - "test_bilingual_chat.py"
Cohesion: 0.08
Nodes (28): _candidates(), _context(), grounded_followups(), grounded_starters(), _has_rows(), _most_common(), Empty-state starters, validated the same way (never a dead suggestion)., Dry-run a candidate query. Cheap (local SQLite) and side-effect free. (+20 more)

### Community 24 - "_rand_unit"
Cohesion: 0.09
Nodes (20): mmr(), Maximal Marginal Relevance — Carbonell & Goldstein (1998). Greedily selects k…, ndarray, _rand_unit(), kind_filter uses the numpy path — results must match the filter., After mutating _matrix[i] and calling sync_faiss(), search must reflect the…, _matrix must remain a real numpy ndarray (consolidation accesses it directly)., L2-normalised inner products must be in [-1, 1]. (+12 more)

### Community 25 - "chat_stream.py"
Cohesion: 0.10
Nodes (36): _claims(), _query_actions(), Phase 1 agentic spine: route one chat turn across existing agents. ponytail:…, Vigil Compliance Gate (§0.4-2 / Layer 4): Enforces that any outgoing claim…, The direct answer first, then each agent's contribution as a short headed…, _route(), _suspect_id_from_query(), _suspect_id_from_text() (+28 more)

### Community 26 - "search/page.jsx"
Cohesion: 0.08
Nodes (29): ago(), ApprovalsPage(), decide(), countdown(), FIELD_LABELS, fieldValue(), HistoryCard(), PendingCard() (+21 more)

### Community 27 - "test_hitl.py"
Cohesion: 0.11
Nodes (37): list_watches(), Any, Register a new watchlist tripwire., List active watches, optionally filtered by officer., register_watch(), active_deployments(), _exec_watch(), _approve() (+29 more)

### Community 28 - "test_agents_manifest.py"
Cohesion: 0.06
Nodes (35): build_graph(), Any, Builds and compiles the LangGraph StateGraph. Called once at startup; result…, _compiled_nodes(), Antar — AGENTS.md drift tests ============================= These are the teeth…, agent_modes injects primary_agents into the route list for /think /connect…, The LLM supervisor is told it may emit these; all of them must route somewhere., The manifest may ADD labels; it must never drop or repoint an existing one. (+27 more)

### Community 29 - "embedder.py"
Cohesion: 0.10
Nodes (30): anyio, embed(), embed_multimodal(), embed_query(), embed_query_with_terms(), embed_with_terms(), get_visual_description(), load_embedder() (+22 more)

### Community 30 - "MapScreen.jsx"
Cohesion: 0.08
Nodes (25): MapScreen, daysInMonth(), DOW_EN, FLOW_KWS, isoDate(), MapScreen(), openDistrict(), primaryZoneFor() (+17 more)

### Community 31 - "run_multi_module_recon"
Cohesion: 0.08
Nodes (31): Antar — OSINT Agent (A6) ============================= Agent responsible for…, get_osint(), get_osint_recon(), get, Antar — OSINT API (Phase 6) ================================ Endpoints for the…, Returns unverified open-web claims and risk flags for the given entity., Layer 5 Multi-Module Reconnaissance Endpoint. Returns: • Maltego Linkage Graph…, Antar — OSINT Service (Phase 6) ==================================== Open-web… (+23 more)

### Community 32 - "evidence_ledger.py"
Cohesion: 0.10
Nodes (36): Scan active watchlists against real ledger signals; emit watchhit products +…, scan_watches(), alias_for(), corridors(), crime_count(), _dataset_max_date(), _days_between(), _distinct() (+28 more)

### Community 33 - "build_spec"
Cohesion: 0.10
Nodes (35): Antar — Dashboard / Overview API (UC2 "Explore" surface · feature N1)…, Run one whitelisted template and return its rows (params are backend-owned)., _rows(), run_local(), build_spec(), Validate params for a template and build its QuerySpec. Raises on unknown id /…, Render a QuerySpec to a ZCQL string., render_zcql() (+27 more)

### Community 34 - "pattern_predict.py"
Cohesion: 0.08
Nodes (31): _alert_card(), _mlabel(), pattern(), _pp_date(), predict(), predict_board(), predict_dashboard(), predict_model_card() (+23 more)

### Community 35 - "test_audit_chain_persistence.py"
Cohesion: 0.10
Nodes (36): load_from_db(), _payload_of(), Verify the ledger and say exactly what was checked. Two independent checks per…, True when no VERIFIABLE entry failed its digest or linkage check. When…, The dict that was (or would have been) hashed — chain bookkeeping stripped., verify_chain(), verify_chain_report(), _insert_legacy_row() (+28 more)

### Community 36 - "quickml.py"
Cohesion: 0.09
Nodes (34): _auth_headers(), _breaker_active(), _build_payload(), _clean(), _default_budget_s(), _extract_text(), _get_access_token(), _get_client() (+26 more)

### Community 37 - "profile.py"
Cohesion: 0.08
Nodes (30): get_bridge_mapping(), profile(), BaseModel, get, post, Antar — Profile API (M5/M6, F5) + Repeat-Offender Registry (N7)…, Entity bridge table (P0): canonical ID mapping across seed suspects and…, Repeat-offender registry (N7): habitual offenders with risk, sorted high→low. (+22 more)

### Community 38 - "BrainIndex"
Cohesion: 0.10
Nodes (17): BrainIndex, ndarray, Coerce any embedding to the index width (_DIM), returning (1, _DIM). Documents…, Hot-append a new embedding without full rebuild., Index one document into the postings list. O(unique terms in doc)., Build the BM25 inverted index (term -> postings) across all summaries. The…, Build IndexHNSWFlat from self._matrix. No-op if FAISS unavailable., Rebuild FAISS & BM25 indices from current state. (+9 more)

### Community 39 - "RefStrip.jsx"
Cohesion: 0.08
Nodes (21): Admin(), load(), pick(), ROLES, NetworkPage(), FACTORS, Profiles(), riskColor() (+13 more)

### Community 40 - "run_agentic_spine"
Cohesion: 0.08
Nodes (28): detect_mode_from_query(), get_mode_spec(), ModeSpec, TypedDict, Antar — First-Class Agent Modes (Think · Connect · Anticipate)…, Retrieve the ModeSpec for a given mode name, defaulting to general., Determine appropriate operational mode from slash commands or natural language…, Any (+20 more)

### Community 41 - "test_templates_t19_t23.py"
Cohesion: 0.11
Nodes (34): _is_count_q(), Direct answer for `rows`, or None when this template has no writer., "how many…", "total…", "ಎಷ್ಟು…", or "<crime> FIRs in 2023" — the officer wants…, write_answer(), Deterministic: validate params → build spec → execute → (rows, citations).…, run_template(), parametrize, T19–T23 and the T8 / T12 extensions: routing, query results and the written… (+26 more)

### Community 42 - "ungrounded_entity"
Cohesion: 0.09
Nodes (14): Return a named entity that does NOT appear in `rows`, else None. Checks two…, ungrounded_entity(), Zero-assumption guard — a named entity that isn't in the rows must never be…, A real match must NOT get the not-found lead., No rows is a different (already-handled) state — don't double-report it., Must work with the LLM down — it takes no client and does no I/O., The reachable failure: the selector DROPS the id and picks a broad template, so…, Plain questions must never trip the guard — nagging on valid answers is worse. (+6 more)

### Community 43 - "redact_future_dates"
Cohesion: 0.09
Nodes (16): _dates_in(), find_future_dates(), walk(), Any, Antar — Future-Date Guard ============================== Policy: future-date…, Return every ISO date string strictly after *today* found in obj., Deep-copy *obj* with any future calendar date scrubbed. A string that IS a bare…, redact_future_dates() (+8 more)

### Community 44 - "hitl.py"
Cohesion: 0.14
Nodes (29): approve(), _audit(), _conn(), _db(), _decide_guard(), _exec_patrol(), _expire_due(), get() (+21 more)

### Community 45 - "test_research_node.py"
Cohesion: 0.11
Nodes (30): Resolve what the officer wants researched: a suspect, a zone, or a free-text…, K/D/I/U dossier, with the adversarial review attached. The dossier and its…, _research_anchor(), research_node(), (route_map, dispatchable_nodes) from AGENTS.md, falling back to the literals…, Map supervisor routes to LangGraph node names, deduped and order-preserving. An…, route_fn(), _routing_tables() (+22 more)

### Community 46 - "settings.py"
Cohesion: 0.09
Nodes (26): export_sdar_training_data(), get, Exports the Self-Distilled Agentic Reinforcement Learning (SDAR) dataset. This…, Antar — Application Settings Reads from .env file via pydantic-settings, CORS origins as a list (ALLOWED_ORIGINS is a comma-separated string in .env)., Settings, app_obs, Sweep judge-pending traces. Call from a periodic task or CLI. Never on the… (+18 more)

### Community 47 - "semantic_recall"
Cohesion: 0.11
Nodes (16): Embed BRAIN_SEED into the hot index. Idempotent. Returns rows newly added., seed_demo_brain(), Three-stage Brain recall: Decompose/Hybrid (HNSW+BM25) → cross-encoder rerank →…, semantic_recall(), run_benchmark(), _fake_embed(), anyio, Task #10: HNSW + Cross-Encoder Rerank + MMR (Brain Scale). Tests cover: • FAISS… (+8 more)

### Community 48 - "jobs.py"
Cohesion: 0.10
Nodes (26): alert_suggest_agent_run(), Called when user intent is related to alerts, deployment, or suggestions., osint_agent_run(), Called by the agentic spine to pull open web intelligence., pattern_agent_run(), Called by the agentic spine when intent is 'pattern'., cancel_job(), create_job() (+18 more)

### Community 49 - "AppShell.jsx"
Cohesion: 0.13
Nodes (22): COPY, DEMO, LoginPage(), handleSubmit(), AppShell(), checkSession(), NAV, DemoOverlay() (+14 more)

### Community 50 - "intent_parser.py"
Cohesion: 0.12
Nodes (27): extract_entities(), Pull crime_types, zones (incl. regions), months hint, geo dimensions, limits,…, _extract_deterministic(), Intent, _keywords(), _merge_llm(), BaseModel, Antar — Intent Parser (self-healing RAG · WI-3)… (+19 more)

### Community 51 - "FastAPI"
Cohesion: 0.10
Nodes (25): audit_integrity(), get_audit(), get_derivation_chain(), get_trace(), get, Antar — Audit API (M10 / F7) ================================= GET /api/audit →…, Tamper-evidence status of the audit ledger. Surfaced as an endpoint rather than…, Phase 5: Returns the LangGraph reasoning trace for a given session/turn. (+17 more)

### Community 52 - "dataset.py"
Cohesion: 0.13
Nodes (26): _conn(), dataset_calendar(), dataset_cycles(), dataset_graph(), dataset_overview(), dataset_records(), dataset_summary(), dataset_year_intel() (+18 more)

### Community 53 - "session_api.py"
Cohesion: 0.12
Nodes (28): BookmarkRequest, _fernet(), get_all_officers(), get_officer_profile(), list_saved(), load_session(), _path(), PreferencesRequest (+20 more)

### Community 54 - "pytest"
Cohesion: 0.08
Nodes (15): Antar — Bhashini Service (A6: Dwani Kannada Voice & Language)…, httpx, pytest, main(), AsyncClient, worker(), Phase 1 Acceptance Tests: A6 Dwani Kannada Voice & Language…, Phase P0 Acceptance Tests: Entity Bridge & Cross-World Unification… (+7 more)

### Community 55 - "PredictScreen.jsx"
Cohesion: 0.10
Nodes (20): PredictScreen, alertToPrediction(), cap(), DEMO_EDGES, DEMO_NODES, DEMO_PREDICTIONS, DEMO_TRACE, keyOf() (+12 more)

### Community 56 - "parse_json_response"
Cohesion: 0.10
Nodes (24): analyze_evidence(), ForensicAnalyzeRequest, get_forensic_presets(), BaseModel, get, post, Antar — Multimodal Forensic OCR & ML Victim Identification API Router Provides…, Returns available 1-click forensic evidence samples for instant testing. (+16 more)

### Community 57 - "anyio"
Cohesion: 0.13
Nodes (5): anyio, If an anomaly is present, it must carry all v2 fields., WOW-3: the planted Rajajinagar chain-snatching spike surfaces in the top…, TestForecastEndpoint, TestForecastTop

### Community 58 - "Constellation3D.jsx"
Cohesion: 0.13
Nodes (17): Constellation3D(), clearFocus(), focusComponent(), refreshVisuals(), LABEL_CACHE, linkWhy(), makeLabelSprite(), nodeTooltip() (+9 more)

### Community 59 - "docs/page.jsx"
Cohesion: 0.12
Nodes (18): AccordionStage(), ASCII_LABELS, clean(), DocsPage(), runStage(), setRun(), FormattedResponse(), FR_LABELS (+10 more)

### Community 60 - "TrustDashboard.jsx"
Cohesion: 0.10
Nodes (11): metadata, C, fmtMs(), fmtNum(), normFlags(), RULE_LABEL, SEV, TraceDetail() (+3 more)

### Community 61 - "intent_flow.py"
Cohesion: 0.11
Nodes (22): Any, Load the prompt definition and return a mock response that satisfies its…, run_prompt(), classify_node(), handle_query(), handle_query_async(), IntentState, Any (+14 more)

### Community 62 - "map_and_ingest_csv"
Cohesion: 0.10
Nodes (20): post, UploadFile, Antar — Upload API (Phase 8) ================================= Endpoints for…, Accepts a CSV file, heuristically maps its columns to the canonical schema, and…, upload_csv(), check_rate_limit(), rate_limit(), _dependency() (+12 more)

### Community 63 - "package.json"
Cohesion: 0.08
Nodes (20): GlobeMap(), KARNATAKA_POV, name, private, scripts, build, dev, lint (+12 more)

### Community 64 - "devils_advocate.py"
Cohesion: 0.20
Nodes (23): _alternatives(), _assess_co_accusal(), _assess_hard_key(), _assess_mo(), _assess_phonetic(), _assess_zone(), _assessment(), _band() (+15 more)

### Community 65 - "audit_store.py"
Cohesion: 0.14
Nodes (22): hash_event(), Cryptographically hashes a dictionary payload combined with the previous hash…, _append(), clear(), Antar — Audit log (M10 / F7) — Persistent SQLite + Catalyst Sync Hybrid. A row…, Record a hypothesis lifecycle event (proposed, shown, confirmed, rejected).…, Record one step of a human-in-the-loop approval on the hash chain.…, Hash `payload` onto the chain and append it in memory. The single place a chain… (+14 more)

### Community 66 - "index.py"
Cohesion: 0.13
Nodes (14): Antar — Second Brain HNSW + Brute-Force Fallback Index (Task #10)…, base64, faiss, _index(), ndarray, Second Brain hybrid retrieval — BM25 inverted index + Reciprocal Rank Fusion.…, A rare-ID query must return the lexical hit, whatever the vectors say., The pre-inverted-index implementation, kept here as the scoring oracle. (+6 more)

### Community 67 - "answer_writer.py"
Cohesion: 0.14
Nodes (22): _as_int(), _breakdown(), _cats(), _comparable(), no_hit_answer(), Antar — Direct-answer writer (deterministic · English + Kannada)…, Answer for identifier templates that found nothing: "not on record" IS the…, A second whitelisted query over the same filters — e.g. which districts a count… (+14 more)

### Community 68 - "manifest.py"
Cohesion: 0.11
Nodes (23): _build_agent(), load(), note_unresolved_route(), _parse(), Any, Antar — Agent Manifest Loader ============================= Parses AGENTS.md…, Parse AGENTS.md once per process. Never raises., Drop the cache and re-read (tests, and editing AGENTS.md during dev). (+15 more)

### Community 69 - "Manifest"
Cohesion: 0.10
Nodes (13): AgentDef, Manifest, {ROUTE_LABEL: agent_id} — which agent a label is *addressed* to., {alias: canonical_agent_id}, including each agent's own id., Every node in the compiled graph, entry node included., Nodes route_fn is allowed to RETURN — the compiled set minus the entry node.…, Agents the orchestrator registers (everything that does real work)., Workers with routes that no graph node executes — the honest gap list. (+5 more)

### Community 70 - "admin_data.py"
Cohesion: 0.10
Nodes (21): FIRRecord, get_schema(), ingest_dataset(), BaseModel, get, post, UploadFile, Antar — Admin Data Governance API =======================================… (+13 more)

### Community 71 - "orchestrator.py"
Cohesion: 0.12
Nodes (23): AgentSpec, _AgentState, _autonomous_loop(), _autonomous_tick(), _scan(), Any, Antar — Production Orchestrator ==================================== The…, Run one agent call under orchestration. Returns (ok, result, meta). On failure… (+15 more)

### Community 72 - "flags.py"
Cohesion: 0.13
Nodes (22): is_conversational(), True when a trace represents a user turn rather than a raw HTTP request., _asserts_number_or_id(), evaluate(), _f(), from_query_result(), persist(), Called from the close hook with the query_agent result to capture V5 signals… (+14 more)

### Community 73 - "CrossEncoderReranker"
Cohesion: 0.09
Nodes (12): CrossEncoderReranker, ndarray, Antar — Cross-Encoder Reranker + MMR Diversifier (Task #10)…, Lazy-loaded ms-marco cross-encoder for two-stage Brain retrieval. Call…, Download/load the cross-encoder. Returns True on success., Score (query, summary_text) pairs; sort descending; return top_n. Side-effect:…, _sigmoid(), Load a fresh reranker instance per class — avoids depending on app startup… (+4 more)

### Community 74 - "Any"
Cohesion: 0.10
Nodes (24): _as_beat_dimension(), _as_crime_list(), _as_dimension(), _as_geo_dimension(), _as_months(), _as_order(), detect_identifier(), _esc() (+16 more)

### Community 75 - "test_evidence_ledger.py"
Cohesion: 0.11
Nodes (8): _get(), anyio, Evidence Ledger (P0) — the synthetic FIR evidence layer + /api/evidence/*.…, TestAliasFor, TestEndpoints, TestEntity, TestSearch, TestStats

### Community 76 - "test_research_dossier_fields.py"
Cohesion: 0.10
Nodes (23): _claims(), dossier(), fixture, Antar — research dossier field-name regressions…, evidence_rows is a list of row identifiers everywhere else in the dossier; this…, A corridor missing src/dst must produce no claim at all — the old code emitted…, A missing key reaching an officer as the literal word 'None' is the signature…, Dossier text reaches CSV/PDF export and Windows consoles. (+15 more)

### Community 77 - "_total_like"
Cohesion: 0.11
Nodes (22): _band(), _blank(), _count_extra(), _is_women(), _law_name(), _pct(), A missing value, including the string forms a JSON round-trip leaves behind.…, T23 — beat or village/area hotspots, for patrol planning. (+14 more)

### Community 78 - "profile_agent.py"
Cohesion: 0.13
Nodes (20): display_crime(), Convert a raw CrimeGroup_Name to display form. - EN inside sentence: "cyber…, _all_factors_and_risk(), _as_date(), _associates(), compute_profile(), _crimes_of(), _leads() (+12 more)

### Community 79 - "test_chat_api.py"
Cohesion: 0.15
Nodes (20): cache_info(), clear_demo_cache(), DemoScript, _load_question_bank(), _normalize(), Any, Deterministic DEMO_MODE response cache. This is not a second query engine.…, Test helper and operational escape hatch. (+12 more)

### Community 80 - "asyncio"
Cohesion: 0.13
Nodes (12): Any, Antar — SSE utilities =========================== Tiny helpers for Server-Sent…, Format one SSE message: ``data: {...}\\n\\n``., Keep-alive comment line (invisible to the client)., Split *text* into word-level chunks and yield each with ultra-low latency. 2…, sse_event(), sse_heartbeat(), token_stream() (+4 more)

### Community 81 - "zcql_local.py"
Cohesion: 0.16
Nodes (19): Antar — Geo-Intelligence Agent =================================== A parallel…, Antar — Pattern Analyst Agent (A7) =======================================…, _scan_and_cluster(), clear_query_cache(), _cached_virtual(), _case_outcomes(), _dict_factory(), ensure_indexes() (+11 more)

### Community 82 - "pydantic"
Cohesion: 0.15
Nodes (19): ActionItem, AgentResponse, EvidenceItem, Any, BaseModel, Antar — Standardized Agent & System Response Schemas…, Grounded evidence supporting a claim or insight., Auditable step in the agent reasoning chain (Layer 4 Explainable AI). (+11 more)

### Community 83 - "workspace.py"
Cohesion: 0.13
Nodes (21): get_job_sync(), list_jobs_sync(), Any, Synchronous accessor for workspace API listing., Synchronous single job lookup., add_workspace_note(), get_workspace_item(), list_workspace_items() (+13 more)

### Community 84 - "map_api.py"
Cohesion: 0.14
Nodes (21): anchor_areas(), darkzones(), _db(), district_detail(), districts_rich(), flow(), gi_star_hotspots(), heat() (+13 more)

### Community 85 - "voice.py"
Cohesion: 0.13
Nodes (21): DwaniQueryRequest, get_status(), BaseModel, get, post, UploadFile, query_dwani(), Antar — Voice & Language API (A6: Dwani Kannada · Phase 1)… (+13 more)

### Community 86 - "re"
Cohesion: 0.13
Nodes (14): BM25, get_index(), HybridIndex, _load_corpus(), Antar — Hybrid Search Index (self-healing RAG · WI-3)…, Hybrid search: RRF-fuse BM25 (sparse) and dense ranks; return top-k crime rows., Lazily build (once) and return the hybrid index over a bounded crimes slice., Lowercase, unicode-aware word tokens (keeps Kannada), stopwords dropped. (+6 more)

### Community 87 - "trace.py"
Cohesion: 0.15
Nodes (17): broadcast_reasoning_step(), log_step(), add_span(), current(), _on(), Called by the log_step sink (V4). One JSONL line per span., Called from the quickml hook (§5.3). Accumulates onto the current trace., Called from the trace-close hook (§5.2) with retrieval facts. (+9 more)

### Community 88 - "stratus.py"
Cohesion: 0.15
Nodes (19): get_app(), Antar — Catalyst App Singleton / Init Helper…, Return an authenticated CatalystApp. - In an AppSail request handler, pass the…, _bucket(), bucket_exists(), download(), presigned_get_url(), presigned_put_url() (+11 more)

### Community 89 - "dependencies"
Cohesion: 0.10
Nodes (20): dependencies, 3d-force-graph, animate.css, force-graph, framer-motion, globe.gl, hls.js, leaflet (+12 more)

### Community 90 - "corridor_agent.py"
Cohesion: 0.14
Nodes (18): compile_corridors(), get_all_corridors(), get_corridor(), Any, Antar — Corridor Agent (A2: Movement Intelligence · Phase 1)…, Compile REAL inter-district corridor products from the evidence ledger. A…, Retrieve a specific corridor product from Product Store., Retrieve all active corridors. (+10 more)

### Community 91 - "_get"
Cohesion: 0.20
Nodes (9): _get(), anyio, Full Dataset API — GET /api/dataset/overview and /api/dataset/records. Covers:…, Sum of per-year counts from cycles.years equals cycles.total (or close — rows…, Seed data holds 'Under Investigation' AND 'under_investigation', plus ' CYBER…, The headline total from /cycles must equal SELECT COUNT(*) FROM FIRs., TestDatasetCycles, TestDatasetOverview (+1 more)

### Community 92 - "anyio"
Cohesion: 0.14
Nodes (6): anyio, TestCircuitBreaker, TestOpsEndpoint, TestRunAgent, boom(), work()

### Community 93 - "_fmt"
Cohesion: 0.15
Nodes (18): _cap1(), _fmt(), _metric_bullet(), _metric_parts(), _metric_sentence(), _outcome_metric(), _rate(), The rate the officer asked about; the answer leads with it and ranks by it. (+10 more)

### Community 94 - "main.py"
Cohesion: 0.12
Nodes (16): get_questions(), _intel_conn(), Connection, get, Antar — Question Bank API for /docs rotating demo questions. GET…, Return question bank. If `set` is given (0-8), return only that set's 3-4…, demographics(), get (+8 more)

### Community 95 - "anyio"
Cohesion: 0.17
Nodes (6): anyio, WOW-2: querying 'Yellapa' (one-p typo) must find the Yellappa suspects., A clearly nonsense query at default threshold should return empty, not 500., FastAPI must NOT route /search to the /{suspect_id} handler., TestProfileRegression, TestSearchEndpoint

### Community 96 - "asset"
Cohesion: 0.18
Nodes (10): HeaderStrip(), HeroBackdrop(), ALLOWED_3D_SCREENS, ScreenTransition3D(), LangCtx, NAV, Shell(), asset() (+2 more)

### Community 97 - "hitl_api.py"
Cohesion: 0.26
Nodes (17): approve(), _call(), DecisionRequest, deployments(), get_action(), propose(), ProposeRequest, BaseModel (+9 more)

### Community 98 - "sys"
Cohesion: 0.12
Nodes (11): dotenv, main(), Connection, One-off data fix — shift future-dated seed rows back by exactly one year.…, report(), One-time helper: exchange a Zoho self-client GRANT CODE for a refresh token.…, Antar — End-to-End Startup Script ======================================…, subprocess (+3 more)

### Community 99 - "time"
Cohesion: 0.15
Nodes (8): Antar — the single source of truth for the database location. The product ships…, Antar — Officer Long-Term Memory & Identity Store (SQLite)…, gzip, shutil, sqlite3, tempfile, threading, time

### Community 100 - "scan"
Cohesion: 0.14
Nodes (15): _brain_context(), Best-effort `resolved_pattern` match for an alert (the WOW-3 brain context).…, Run the scan → alerts. Returns {created, alerts}. Idempotent (replaces the…, scan(), post, scan_alerts(), inject_evidence(), Antar — Non-Cyber Evidence & Syndicate Data Injection… (+7 more)

### Community 101 - "test_layer6_geospatial.py"
Cohesion: 0.20
Nodes (13): compute_dark_zones(), compute_unsub_anchor_areas(), _convex_hull_2d(), _haversine_km(), Antar — Geo-Density Service ================================ Math/heuristic…, Haversine distance in kilometers between two lat/lon coordinates., Monotone chain 2D convex hull algorithm. Returns polygon coordinates [[lat,…, Computes UNSUB anchor areas (geographic profiling honest version). For each… (+5 more)

### Community 102 - "_get"
Cohesion: 0.26
Nodes (6): _get(), anyio, Predict screen backend — GET /api/predict/board, GET…, TestPredictBoard, TestPredictReasoning, TestSearchFieldScope

### Community 103 - "export_api.py"
Cohesion: 0.20
Nodes (15): _answer_html(), _e(), export(), get, post, Antar — Export / Intelligence Report (F6 / M9)…, One Q→A record per assistant turn — shared by the HTML report and the JSON…, Light markdown → HTML: **bold**, bullet/numbered lines, paragraphs; tags… (+7 more)

### Community 104 - "redact_pii"
Cohesion: 0.19
Nodes (11): evaluate_bias(), _mask_case_ids(), Swap case identifiers for placeholders that no PII pattern can match., Redacts sensitive PII (Aadhaar, Phone Numbers) leaving only the last 4 digits.…, Evaluates generated profile text for potentially biased terminology. Returns…, redact_pii(), _restore_case_ids(), test_evaluate_bias_clean() (+3 more)

### Community 105 - "build_world"
Cohesion: 0.17
Nodes (11): acts_and_sections(), build_world(), add_crime(), city_code(), next_fir(), pick_io(), Antar — Synthetic World Generator ===========================================…, Generate every table deterministically. Returns {table_name: rows}. (+3 more)

### Community 106 - "_run_pipeline"
Cohesion: 0.28
Nodes (14): is_explain_request(), True if the user is asking us to justify the previous answer (Explain / M9)., _L(), Full agentic pipeline that emits SSE events via *q* as it progresses. Mirrors…, Pick the Kannada string when the (toggle-driven) lang is 'kn', else English., _run_pipeline(), _degraded(), run_alerts_task() (+6 more)

### Community 107 - "vigil.py"
Cohesion: 0.15
Nodes (14): audit_request(), get_receipt(), Any, Retrieve a compiled compliance receipt by request ID., Audit a query or prompt for bias, prohibited targeting, and BNSS compliance., get_vigil_receipt(), BaseModel, get (+6 more)

### Community 108 - "devils_advocate_api.py"
Cohesion: 0.16
Nodes (13): base_rates(), challenge_anchor(), challenge_one(), challenge_stored(), HypothesisPayload, BaseModel, get, post (+5 more)

### Community 109 - "load.py"
Cohesion: 0.18
Nodes (13): Run a ZCQL query and return plain dict rows. Aggregation / GROUP-BY-heavy reads…, zcql_query(), main(), push_to_datastore(), Antar — Seed Loader CLI ================================= Usage (from antar-…, Batch-insert into Catalyst Data Store using the real zcatalyst-sdk API:…, Delete all rows from a table (paged read → delete_rows by id). [VERIFY] whether…, Phase 1, Step 1.7 validation: 5 ZCQL spot-queries (incl. one OLAP aggregation)… (+5 more)

### Community 110 - "_collect"
Cohesion: 0.26
Nodes (6): _collect(), anyio, Spine parity with the stream contract — trail as data, never in the prose., CONTRACT CHANGE (2026-07-21): the reasoning trail ships as structured…, TestSpineParity, TestStreamPipeline

### Community 111 - "_crime_word"
Cohesion: 0.23
Nodes (14): _crime_en(), _crime_word(), _in_loc(), _mix(), in Karnataka' / 'ಕರ್ನಾಟಕದಲ್ಲಿ' — Kannada attaches the case ending to the place., T13 — "which crime is most common?"., T9 — every case linked to one suspect., "how many theft cases in 2024?" — the number first, then where/what, then the… (+6 more)

### Community 112 - "chat.py"
Cohesion: 0.20
Nodes (12): _answer(), compose_answer(), LLM, LLM picks {template_id, params}. Returns parsed dict (may be…, Deterministic answer: direct answer first (answer_writer), legacy formatter as…, Write the NL answer from rows. Returns (text, used_llm, violations). Falls back…, select_template(), _llm_available() (+4 more)

### Community 113 - "retrieval.py"
Cohesion: 0.20
Nodes (13): _build_banner(), _city(), _crimes_of(), decompose_query(), find_cross_case_links(), _months_ago(), _neighbors(), Antar — Second Brain Cross-Case Retrieval (WOW 2) Given a suspect, surface… (+5 more)

### Community 114 - "second_brain/store.py"
Cohesion: 0.18
Nodes (12): b64_to_vec(), insert_embedding(), load_all_embeddings_from_store(), ndarray, Antar — Second Brain Durable Store (Data Store rows)…, Encode a float32 vector → base64 string for the Data Store text column., Return all brain_embeddings rows (paginated) for the boot index rebuild. Phase…, Persist one brain_embeddings row. `row` must include row_id, kind,… (+4 more)

### Community 115 - "district_cache.py"
Cohesion: 0.20
Nodes (13): _db(), get_all(), get_district(), Connection, Antar — District aggregates cache (§5: materialization)…, All district aggregates as a list — for choropleth., Single-district drill-down card — O(1) dict lookup., High / Medium / Low based on count + month-over-month ratio. (+5 more)

### Community 116 - "test_product_store.py"
Cohesion: 0.16
Nodes (5): anyio, Phase P1 Acceptance Tests: Product Store & Compiled Intelligence Layer…, P1 Acceptance Criteria: hitting registry 10 times shows constant < 15 ms…, TestProductStoreEndpoints, TestProductStoreService

### Community 117 - "_w_trend"
Cohesion: 0.18
Nodes (13): _complete(), _dir_line(), _direction(), _forecast_line(), _mon(), _partial_months(), Months that cannot be compared with a full one, because they are cut short. Two…, Split a monthly series into complete months and the one still in progress. (+5 more)

### Community 118 - "_date"
Cohesion: 0.23
Nodes (13): _date(), _fir_lines(), _fir_no(), _nice_status(), T1 / T12 — case lists ("theft cases in Rajajinagar", "recent crimes")., FIRs holds one row per accused; count and list each FIR (fir_id) once. CrimeNo…, T18 (vehicle) and T20 (UPI ID / IP address; vehicle and accused IDs also…, T21 — one accused ID's history: where, what, and how the cases ended. (+5 more)

### Community 119 - "linkage_agent.py"
Cohesion: 0.18
Nodes (12): compile_all_linkages(), compile_linkage(), Any, Antar — Linkage Agent (A3: MO Case-Matcher · Phase 1)…, Compile the REAL case-linkage product for one evidence FIR (an 'EV-{i}' ref).…, Compile linkage products for the highest-priority FIRs (most-active multi-FIR…, compile_linkages_endpoint(), get_fir_linkage() (+4 more)

### Community 120 - "app_api"
Cohesion: 0.18
Nodes (6): app_api, client(), anyio, fixture, Tests for POST /api/feedback — persisted, validated, counted., TestFeedback

### Community 121 - "soundex"
Cohesion: 0.24
Nodes (5): American Soundex code — first letter + up to 3 consonant-group digits. Vowels…, soundex(), WOW-2 alias variant: Yellappa and Yellapa must share a Soundex code., Doubled-vowel variant: Raju / Raaju → same code., TestSoundex

### Community 123 - "live_stream.py"
Cohesion: 0.21
Nodes (7): broadcast_event(), Simulates real-time emergency dispatch events., start_dispatch_simulator(), websocket_endpoint(), anyio, test_websocket_broadcast(), websocket

### Community 124 - "auth_middleware.py"
Cohesion: 0.18
Nodes (11): get_current_officer(), Any, Antar — RBAC (F7 / M10) ============================ Role hierarchy + a…, Caller's role from the header (dev). Unknown/missing → Inspector., Retrieve full officer profile and memory state for active session…, Dependency factory → 403 unless the caller's role rank >= `minimum`., Dependency to secure cron-triggered endpoints. Returns True if valid., require_cron_secret() (+3 more)

### Community 125 - "_concept_map"
Cohesion: 0.24
Nodes (12): _concept_map(), _crime_key(), data_crime_groups(), _lookup(), put(), _match_one(), Comparison key: case, '&' vs 'and', punctuation and spacing all stop mattering.…, Every CrimeGroup_Name actually present in the FIR registry. (+4 more)

### Community 126 - "anyio"
Cohesion: 0.24
Nodes (4): anyio, TestBhashiniService, TestDwaniAgent, TestVoiceEndpoints

### Community 127 - "test_session_api.py"
Cohesion: 0.23
Nodes (6): client(), anyio, fixture, Tests for encrypted session save/load (app/api/session_api.py). Contract:…, TestRoundtrip, TestValidation

### Community 128 - "parse_slash_command"
Cohesion: 0.29
Nodes (3): parse_slash_command(), Parse a leading /think, /connect or /anticipate command. Returns (command,…, TestParse

### Community 129 - "test_geo.py"
Cohesion: 0.24
Nodes (10): compute_flow(), compute_heat(), predict_hotspots(), Returns raw points for frontend Leaflet.heat rendering. Bins identical…, Given a list of crime rows (with lat, lon, occurred_at, crime_id), and optional…, Returns (predicted_points, beat_suggestions). A 'ponytail' heuristic:…, Tests for Phase 4 Geo-Intelligence (M7 Validation)., test_compute_flow() (+2 more)

### Community 130 - "fastapi_testclient"
Cohesion: 0.18
Nodes (8): fastapi_testclient, Governance (P6 · F7 RBAC + audit, F6 report/export) — via the HTTP layer…, The live demo beat: Constable → 403 on /api/audit; Admin → 200., Inspector+ guard on /api/graph: default (no header) = Inspector → ok; Constable…, F6: export returns a report URL and the report HTML renders., test_constable_blocked_from_audit_admin_ok(), test_export_and_report_render(), test_inspector_default_allows_graph_constable_blocked()

### Community 131 - "test_linkage_agent.py"
Cohesion: 0.25
Nodes (5): _priority_ref(), anyio, Acceptance Tests: A3 Linkage Agent (MO Case-Matcher) — REAL data.…, TestLinkageAgent, TestLinkageEndpoints

### Community 133 - "challenge_dossier"
Cohesion: 0.22
Nodes (9): challenge_dossier(), _Index, _index_cached(), _now(), Attribute value frequencies over the suspect population. Built once., Audit every inferred hypothesis in a research dossier. Returns a rebuttal…, A shared hard key must be rarer than a shared district, in the real data., test_real_dossier_challenge_runs_end_to_end() (+1 more)

### Community 134 - "display_names.py"
Cohesion: 0.22
Nodes (9): display_dimension(), display_direction(), _normalise(), Antar — Shared display-name helpers (sentence case, crime names, direction…, Trim, strip leading/trailing whitespace, collapse spaces., UPWARD/DOWNWARD/STABLE → Rising/Falling/Steady (EN) or Kannada equiv., zone/district/station_code → 'districts' / 'police stations' etc., Convert UPPERCASE text to sentence case, preserving known acronyms. (+1 more)

### Community 135 - "test_map.py"
Cohesion: 0.27
Nodes (9): districts(), hotspots(), Pre-aggregated zone hotspots — instant query from zone_summary table., District-level choropleth data — instant from summary tables., Map API (N2 / F3) — hotspot aggregation + district drill-down over the seed…, P3: Rajajinagar / Gandhinagar are planted theft hot zones → near the top by…, test_districts_drilldown(), test_hotspots_returns_points_and_clusters() (+1 more)

### Community 136 - "products.py"
Cohesion: 0.22
Nodes (9): get_product_endpoint(), list_products(), get, post, Antar — Products API (P1: Compiled Intelligence Cache Layer)…, List all registered product keys and their cache status., Retrieve the compiled payload for a specific product key., Force re-compilation of all registered product generators. (+1 more)

### Community 137 - "TaskWorker"
Cohesion: 0.22
Nodes (4): Starts the background worker loop., Stops the background worker loop., Submit an async function to run in the background., TaskWorker

### Community 138 - "registry.py"
Cohesion: 0.22
Nodes (7): CircuitBreakerOpenException, Exception, Antar — Reliable Tool Integration Registry…, Decorator to register a reliable tool., ToolRegistry, decorator(), wrapper()

### Community 139 - "alert_suggest_agent.py"
Cohesion: 0.31
Nodes (6): Antar — Alert & Suggestion Agent (A10) (Phase 7)…, get_events_for_date(), Antar — Event Calendar Service (Phase 7)…, Returns relevant upcoming or ongoing events for a given date and zone., Tests for Phase 7 Alerts and Suggestion, test_events_for_date()

### Community 140 - "_answer_confidence"
Cohesion: 0.36
Nodes (3): _answer_confidence(), Calibrated answer-confidence (plan §1.4). Three independent signals combined…, TestAnswerConfidence

### Community 141 - "overview"
Cohesion: 0.28
Nodes (8): overview(), get, Overview KPIs + summary panels for the dashboard landing (N1). Composed from…, Overview dashboard endpoint (N1) — composed from whitelisted templates, local…, Happy: KPIs + panels present; status counts partition the total crime count., Failure-mode: if a template returns nothing, the contract still holds (zeros,…, test_overview_contract_and_totals(), test_overview_resilient_to_empty()

### Community 142 - "lifespan"
Cohesion: 0.22
Nodes (8): stop_autonomous(), aclose_client(), Close the shared client to release pooled connections (call on app shutdown)., lifespan(), Startup: Yield immediately to bind port, run heavy loads in background., fixture, quickml_env(), No token fetch (auth=none), a dummy endpoint, instant backoff, clean shared…

### Community 143 - "test_briefing_agent.py"
Cohesion: 0.22
Nodes (4): anyio, Phase 1 Acceptance Tests: A4 Shift Briefings & Compiled Intelligence…, TestBriefingAgent, TestBriefingEndpoints

### Community 144 - "run_research"
Cohesion: 0.46
Nodes (8): _get_loc(), _get_name(), _get_time_iso(), Any, Execute budgeted KUL deep research on an anchor (suspect ID, zone, FIR, or…, Score an identity/association hypothesis between two suspects per…, run_research(), _score_hypothesis_pair()

### Community 145 - "state.py"
Cohesion: 0.25
Nodes (5): Antar — LangGraph Agent State Schema The spine of the multi-agent system. Build…, Append, unless the incoming update opens with the CLEAR sentinel., reduce_list(), langgraph_checkpoint_memory, operator

### Community 146 - "feedback.py"
Cohesion: 0.29
Nodes (7): feedback_stats(), FeedbackRequest, BaseModel, get, post, Antar — Answer Feedback ============================ POST /api/feedback…, submit_feedback()

### Community 147 - "conftest.py"
Cohesion: 0.32
Nodes (7): _force_offline(), _keep_main_db_clean(), fixture, Pytest config — force tests into deterministic OFFLINE mode regardless of the…, Highest rowid per table, so anything inserted after this point is identifiable., Remove rows the test run leaves behind in main.db. The suite runs against the…, _rowid_marks()

### Community 148 - "test_predict_dashboard.py"
Cohesion: 0.43
Nodes (4): _get(), anyio, Predict dashboard cards — GET /api/predict/dashboard (monthly aggregation).…, TestPredictDashboard

### Community 149 - "test_generate_retries_then_raises"
Cohesion: 0.29
Nodes (7): _install(), Point the shared client at an in-process MockTransport (no real network)., 200 + {response} → trimmed text; the shared client is a reused singleton., Persistent HTTP 500 → retried, then RuntimeError surfacing the status code., test_generate_retries_then_raises(), test_generate_success_and_client_is_reused(), handler()

### Community 150 - "dwani_agent.py"
Cohesion: 0.38
Nodes (6): _detect_crime(), _detect_place(), process_kannada_query(), Any, Antar — Dwani Agent (A6: Kannada Voice & Language · honest)…, Translate → answer from real data → render EN/KN. No fabricated numbers.

### Community 151 - "chat_stream"
Cohesion: 0.29
Nodes (6): chat_stream(), run(), post, Request, POST /api/chat/stream — SSE streaming chat endpoint. Emits typed SSE events as…, StreamingResponse

### Community 152 - "health.py"
Cohesion: 0.33
Nodes (6): health_check(), get, Antar — Health Check Endpoint /api/health — judges will probe this. Make it…, Liveness + readiness check. Returns system state visible to judges on Slide 13…, get_model(), SentenceTransformer

### Community 153 - "ops.py"
Cohesion: 0.29
Nodes (6): orchestrator_refresh(), orchestrator_status(), get, post, Antar — Orchestrator Ops API ================================= GET…, status()

### Community 156 - "evidence.py"
Cohesion: 0.47
Nodes (5): entity(), get, Antar/Antar — Evidence Ledger API (P0, build03_improveX)…, search(), stats()

### Community 157 - "_strip_reasoning"
Cohesion: 0.47
Nodes (3): GLM-4.7 emits visible chain-of-thought wrapped in <think>…</think> before the…, _strip_reasoning(), TestThinkStrip

### Community 161 - "get_hypothesis"
Cohesion: 0.40
Nodes (5): get_hypothesis(), list_hypotheses(), get, List stored hypotheses from product_store., Get a specific hypothesis by ID.

### Community 162 - "evaluator.py"
Cohesion: 0.40
Nodes (4): evaluate_response(), Any, Antar — Continuous Agent Evaluation (LLM-as-a-Judge)…, Evaluates an agent's response using standard RAG metrics. In a real production…

### Community 163 - "compilerOptions"
Cohesion: 0.50
Nodes (3): compilerOptions, baseUrl, paths

### Community 164 - "load_sqlite.py"
Cohesion: 0.50
Nodes (3): load_into_sqlite(), Antar — Seed Loader for SQLite (antar.db)…, Path

### Community 165 - "forensics.py"
Cohesion: 0.50
Nodes (3): parse_cellebrite_json(), Antar — Offline Forensics Parser ===================================== Parses…, Parses a simulated Cellebrite JSON export. Returns structured data ready for…

## Knowledge Gaps
- **106 isolated node(s):** `Template`, `HEAT`, `MONTHS`, `MONTH_NAMES`, `MONTHS` (+101 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1512 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_world()` connect `typing` to `devils_advocate.py`, `pattern_predict.py`, `build_network`, `challenge_dossier`, `anomaly.py`, `profile.py`, `get_product`, `_get`, `profile_agent.py`, `fuzzy_match_suspects`, `run_research`, `zcql_local.py`, `second_brain/ingestion.py`, `retrieval.py`, `second_brain/store.py`, `chat_stream.py`, `run_multi_module_recon`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `TestForecastEndpoint` connect `anyio` to `anomaly.py`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `build_custody()` connect `build_layout` to `zcql_repo.py`, `_run_pipeline`, `chat.py`, `sessions.py`, `chat_stream.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `_run_pipeline()` (e.g. with `_hybrid_select()` and `SSEQueue`) actually correct?**
  _`_run_pipeline()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Template`, `HEAT`, `MONTHS` to the rest of the system?**
  _106 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `zcql_repo.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05613951266125179 - nodes in this community are weakly interconnected._
- **Should `BrainStructure.jsx` be split into smaller, more focused modules?**
  _Cohesion score 0.05098934550989345 - nodes in this community are weakly interconnected._