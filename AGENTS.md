# Antar — Agent Manifest

**This file is executable.** `app/agents/manifest.py` parses every `yaml` block below at import
time. The orchestrator fleet registry and the supervisor's route table are *generated from it*.
A test (`tests/test_agents_manifest.py`) fails the build when this document and the compiled
graph disagree.

Do not describe an agent here that does not exist, and do not add an agent to the code without
adding it here. That is the whole point: documentation that cannot drift, because drift breaks
the build.

## Why this file exists

Agent identity used to live in four places that could silently disagree:

| Source | Declared |
|---|---|
| `orchestrator.register_default_fleet()` | name, role, timeout |
| `supervisor._ROUTE_MAP` | route label to graph node |
| `agent_modes.MODES` / `heuristics.SLASH_COMMANDS` | which agents a mode forces |
| the 30 modules under `app/agents/` | what actually runs |

They did disagree, and it cost real behaviour: `_ROUTE_MAP` fell back to `"query"` for any label
it did not recognise, so on the offline path `NETWORK` and `PROFILE` became `query` and four
agents never ran at all. The reasoning trail showed a healthy fan-out while the graph executed a
single node. See the comment at `app/agents/supervisor.py:63`.

This manifest makes that class of bug impossible to ship: an unknown route label is now a loud,
counted warning (`manifest.unresolved_routes()`), and a missing node fails a test.

## Contract

Every block below declares one agent. Fields:

| Field | Meaning |
|---|---|
| `agent` | canonical lowercase id — the ONE spelling the codebase uses |
| `kind` | `worker` (does intelligence work) / `service` (autonomous loop only) / `system` (graph infrastructure) |
| `role` | display role, shown in `/api/orchestrator/status` |
| `module` | `path::entrypoint` — where it actually lives |
| `graph_node` | the compiled LangGraph node that EXECUTES this agent. `null` = never runs inside the graph |
| `hosted_by` | set when another agent's node runs this one internally (e.g. `forecast_node` runs geo) |
| `unrouted_fallback` | node that absorbs routes addressed to this agent when `graph_node` is null. **A route landing here does NOT run this agent** |
| `aliases` | other spellings that reach the router and must resolve to this agent |
| `routes` | UPPERCASE route labels that dispatch here (both the LLM-supervisor vocabulary and the offline-heuristic one) |
| `timeout_s` / `retries` | orchestrator limits |
| `surfaces` | `graph` / `chat_stream` / `api` / `autonomous` |
| `guardrails` | validators this agent's output MUST pass before reaching an officer |
| `hitl` | true when a real-world effect requires a named officer's approval |
| `degraded` | what the officer sees when this agent fails — never fabricated data |
| `sensitivity` | what the output is about: `aggregate` (counts, areas), `case` (FIR rows), `person` (a named accused), `external` (the open web). **Required** — an agent without it fails the build |
| `min_role` | the lowest role that may run it; `app/core/policy.py` refuses a lower one before the agent starts |
| `obligations` | conditions applied to the result before it leaves the agent: `redact_pii`, `aggregate_only`, `label_unverified`, `row_cap:N` |

---

## Topology

```yaml
topology:
  entry: supervisor
  terminal: synthesize
  nodes: [supervisor, query, network, profile, forecast, social, research, brain, osint, synthesize]
  checkpointer: SqliteSaver          # thread_id = session_id; durable, survives restart
  fanout: conditional                # supervisor -> route_fn -> [worker...] -> synthesize -> END
```

---

## Workers with their own graph node

### query

The deterministic spine. Whitelisted templates (26 public, T1-T30) over the FIR registry; never free SQL.
Escalates through `self_heal` (template reroute, SQL miner relaxation, dense recall, hybrid
BM25, honest dead-end) rather than returning an empty answer.

```yaml
agent: query
kind: worker
sensitivity: case
min_role: Constable
obligations: []
role: Vault - template query
module: app/agents/query_agent.py::query_agent_run
graph_node: query
routes: [VAULT, QUERY, EXPLAIN]
timeout_s: 10.0
retries: 1
surfaces: [graph, chat_stream, api]
reads: [crimes, FIRs, suspects, crime_suspects]
emits: [results.query, citations, actions, reasoning]
guardrails: [G1_numbers, G2_no_result_honesty, G3_identifiers, G4_slop, G6_length, date_guard, zero_assumption]
hitl: false
degraded: "self_heal escalation; honest dead-end with nearest-match hint if every stage misses"
notes: >
  EXPLAIN has no agent of its own - it replays the stored reasoning trail through this node.
```

### network

```yaml
agent: network
kind: worker
sensitivity: person
min_role: Inspector
obligations: []
role: Link - graph builder
module: app/agents/network_agent.py::build_network
graph_node: network
routes: [LINK, NETWORK]
timeout_s: 15.0
retries: 1
surfaces: [graph, chat_stream, api]
reads: [crime_suspects, evidence_ledger, second_brain]
emits: [results.network, visuals.graph, brain_hits, actions]
guardrails: [verify_claims, date_guard]
hitl: false
degraded: "no-op update when no suspect id resolves; never invents a seed"
notes: >
  Requires a resolved suspect_id from the query result or the raw text. Returns a valid
  no-op (not an empty dict) when none resolves - LangGraph rejects a bare empty update.
```

### profile

```yaml
agent: profile
kind: worker
sensitivity: person
min_role: Inspector
obligations: []
role: Motive - suspect profiler
module: app/agents/profile_agent.py::compute_profile
graph_node: profile
routes: [MOTIVE, PROFILE]
timeout_s: 15.0
retries: 1
surfaces: [graph, chat_stream, api]
reads: [suspects, crime_suspects, crimes]
emits: [results.profile, visuals.profile, actions]
guardrails: [evaluate_bias, redact_pii, calculate_shap_values, verify_claims]
hitl: false
degraded: "no-op update when no suspect id resolves"
notes: >
  Risk score is linear-additive, so SHAP attribution is exact (100 * w_i * f_i), not
  approximated. Bias screen runs on the generated text before it leaves the agent.
```

### forecast

Composite node. `forecast_node` runs **four** agents internally — geo, predict, pattern and
alert_suggest — because they share the same statistical scan and splitting them into separate
graph nodes would quadruple the work.

```yaml
agent: forecast
kind: worker
sensitivity: aggregate
min_role: Constable
obligations: []
role: Core - risk forecaster (composite node)
module: app/agents/graph.py::forecast_node
graph_node: forecast
routes: [CORE, FORECAST]
timeout_s: 15.0
retries: 1
surfaces: [graph, autonomous]
hosts: [geo, predict, pattern, alert_suggest]
reads: [crimes, geo_density, anomaly, district_cache]
emits: [results.geo, results.predict, results.pattern, results.alert_suggest, visuals.map, visuals.predict, visuals.alerts]
guardrails: [date_guard, prediction_privacy, verify_claims]
hitl: false
degraded: "per-sub-agent; a failing sub-agent yields a degraded step, never a fabricated band"
notes: >
  Everything this node returns passes through _to_native() - numpy scalars are not
  msgpack-serialisable and the LangGraph checkpointer raises on them. date_guard is
  mandatory here: no concrete future calendar date may leave the backend.
```

### social

```yaml
agent: social
kind: worker
sensitivity: aggregate
min_role: Constable
obligations: [aggregate_only]
role: Sense - demographic insight
module: app/agents/social_agent.py::demographics
graph_node: social
routes: [SENSE, SOCIAL]
timeout_s: 8.0
retries: 1
surfaces: [graph, api]
reads: [suspects, crimes]
emits: [results.social, visuals.social, actions]
guardrails: [evaluate_bias, aggregate_only]
hitl: false
degraded: "omitted from synthesis"
notes: >
  Output is aggregate correlation ONLY. Every answer carrying social insight must append
  the non-targeting disclaimer (_synthesize does this) - it is never a basis to target
  any group.
```

---

## Workers hosted inside another node

These run, but not as their own graph node. A route addressed to them dispatches to their host,
which executes them.

### geo

```yaml
agent: geo
kind: worker
sensitivity: aggregate
min_role: Constable
obligations: []
role: Lens - geo intelligence
module: app/agents/geo_agent.py::geo_agent_run
graph_node: forecast
hosted_by: forecast
routes: [GEO]
timeout_s: 8.0
retries: 1
surfaces: [graph, chat_stream, api]
reads: [geo_density, district_cache, crimes]
emits: [results.geo, visuals.map]
guardrails: [date_guard]
hitl: false
degraded: "beat suggestions omitted; map falls back to unfiltered density"
```

### predict

```yaml
agent: predict
kind: worker
sensitivity: aggregate
min_role: Constable
obligations: []
role: Core - risk forecaster
module: app/agents/prediction_agent.py::prediction_agent_run
graph_node: forecast
hosted_by: forecast
aliases: [prediction]
routes: [PREDICT, PREDICTION]
timeout_s: 15.0
retries: 1
surfaces: [graph, chat_stream, api]
reads: [crimes, anomaly, quickml]
emits: [results.predict, visuals.predict]
guardrails: [date_guard, prediction_privacy, conformal_band]
hitl: false
degraded: "risk band withheld rather than widened; officer told the forecast is unavailable"
notes: >
  'prediction' is the spelling in agent_modes.MODES["anticipate"].primary_agents; 'predict'
  is the spelling in _route() and the orchestrator fleet. Both resolve here. Before this
  manifest, PREDICTION was unmapped and dropped silently.
```

### pattern

```yaml
agent: pattern
kind: worker
sensitivity: aggregate
min_role: Constable
obligations: []
role: Sense - MO pattern detector
module: app/agents/pattern_agent.py::pattern_agent_run
graph_node: forecast
hosted_by: forecast
routes: [PATTERN]
timeout_s: 8.0
retries: 1
surfaces: [graph, chat_stream, api]
reads: [crimes, patterns, second_brain]
emits: [results.pattern, visuals.pattern]
guardrails: [verify_claims]
hitl: false
degraded: "pattern section omitted from synthesis"
```

### alert_suggest

```yaml
agent: alert_suggest
kind: worker
sensitivity: aggregate
min_role: Constable
obligations: []
role: Beacon - patrol advisor
module: app/agents/alert_suggest_agent.py::alert_suggest_agent_run
graph_node: forecast
hosted_by: forecast
aliases: [alerts]
routes: [ALERT_SUGGEST, ALERTS]
timeout_s: 6.0
retries: 1
surfaces: [graph, chat_stream, api]
reads: [anomaly, alerts_store, geo_density]
emits: [results.alert_suggest, visuals.alerts, actions]
guardrails: [date_guard, verify_claims]
hitl: true
degraded: "honest 'no unusual activity right now' - never an invented spike"
notes: >
  hitl:true is ENFORCED. The agent only suggests; a patrol redeployment is proposed as a
  `patrol_redeployment` action (POST /api/hitl/propose) and executes only after a
  supervising officer (role Approver) approves it - never the proposer. Approval must
  echo the payload hash the approver reviewed; proposals expire after 12 hours. The
  executed order is readable at GET /api/hitl/deployments. See app/core/hitl.py.
```

---

## Workers that were once unreachable

This section used to hold agents with **no graph node**, whose routes folded into
`unrouted_fallback` — a node that does *not* run them, so in a graph turn they were
silently absent while the trail showed them working.

It is now empty of gaps. `research` was the first to get its own node; `brain` and `osint`
followed (2026-09-25), and both are declared and tested like any other worker. The section
is kept because the failure mode is worth remembering, not because anything still sits
here.

### osint

```yaml
agent: osint
kind: worker
sensitivity: external
min_role: Inspector
obligations: [label_unverified]
role: Scout - open-web scan
module: app/agents/graph.py::osint_node
graph_node: osint
routes: [OSINT]
timeout_s: 15.0
retries: 1
surfaces: [chat_stream, api]
reads: [osint_recon, external_web]
emits: [results.osint]
guardrails: [redact_pii, verify_claims, vigil]
hitl: false
degraded: "OSINT section omitted; never presents an unreachable source as checked"
notes: >
  Has its own graph node as of 2026-09-25 (it used to fold into query, which does not run
  it). The ONLY agent that leaves the building: everything it returns is UNVERIFIED and
  stays labelled that way - the open web is not the FIR record and is never merged into it.
  Refuses without a named subject rather than scanning on a guess; searching the open web
  for whatever capitalised word was in the sentence is how an uninvolved member of the
  public ends up in a police work product.
  chat_stream still strips "osint" from its own route list - that surface is unchanged.
```

### research

```yaml
agent: research
kind: worker
sensitivity: person
min_role: Inspector
obligations: []
role: Trace - K/D/I/U dossier
module: app/agents/graph.py::research_node
graph_node: research
routes: [TRACE, RESEARCH]
timeout_s: 12.0
retries: 1
surfaces: [graph, chat_stream, api]
reads: [crimes, suspects, evidence_ledger, second_brain]
emits: [results.research, results.advocate_agent, visuals.research]
hosts: [advocate_agent]
guardrails: [verify_claims, vigil, kdiu_tagging, adversarial_review]
hitl: false
degraded: "no-op when no researchable subject is named; never researches an empty anchor"
notes: >
  Runs advocate_agent over its own inferred hypotheses INSIDE the node. A dossier's
  [INFERRED] claims are scored guesses; shipping them into a chat answer without the
  base-rate check is how an officer gets anchored on a pair whose only connection is a
  shared district. The rebuttal is therefore not optional for a caller to skip.
  Every [INFERRED] claim must carry a hypothesis id and an explicit inferred marker or
  verify_claims drops it.
  Anchor resolution returns None rather than guessing - run_research substring-matches
  the anchor against every suspect, so an empty anchor yields a confident dossier about
  nobody.
```

### brain

```yaml
agent: brain
kind: worker
sensitivity: case
min_role: Inspector
obligations: []
role: Vault - semantic recall
module: app/agents/graph.py::brain_node
graph_node: brain
routes: [BRAIN]
timeout_s: 6.0
retries: 1
surfaces: [chat_stream, api]
reads: [brain_index, embeddings_store, hybrid_index]
emits: [brain_hits, results.second_brain]
guardrails: [confidence_decay, verify_claims]
hitl: false
degraded: "recall skipped when index is empty or the embedder failed to load"
notes: >
  Has its own graph node as of 2026-09-25. Searches BOTH Brain tiers and keeps them
  apart, because they carry different evidence weight: the curated tier (summaries, MOs,
  patterns) through the full RRF hybrid -> cross-encoder -> MMR pipeline, and the
  100,000-FIR corpus from a memory-mapped int8 index. Corpus hits are tagged DERIVED (D) -
  a similar FIR is a lead, not a finding, and the class travels with the hit so synthesis
  cannot promote it. Reranking is cross-encoder plus zero-parameter attention centrality
  (corroboration), not cosine alone. An empty result is reported as "no comparable record",
  never as silence.
```

---

## Adversarial layer

### advocate_agent

The only agent that argues *against* another agent's output. `research_agent` scores
hypotheses by summing signal weights; a weight sum says nothing about how many other people
in the population would produce the same signal. This one prices every signal against its
base rate, applies the multiple-comparisons correction for the size of the scan that
surfaced it, and states what evidence would falsify it.

```yaml
agent: advocate_agent
kind: worker
sensitivity: person
min_role: Inspector
obligations: []
role: Adversary - hypothesis falsification and base-rate audit
module: app/agents/advocate_agent.py::challenge
graph_node: research
hosted_by: research
routes: []
timeout_s: 12.0
retries: 1
surfaces: [graph, api, hypothesis_lifecycle]
reads: [suspects, crime_suspects, research_dossier]
emits: [advocate_agent_product, hypothesis.adversarial_review]
guardrails: [deterministic_only, no_llm]
gates: [hypothesis_confirm]
hitl: false
degraded: "returns UNASSESSABLE for unresolvable subjects - never silently approves a hypothesis"
notes: >
  GATES the Inferred -> Known transition. POST /api/hypothesis/{id}/confirm runs this
  agent first; a COLLAPSES or WEAKENED verdict returns 409 with the full rebuttal until
  the officer resubmits with acknowledge_challenge=true AND a written reason. The verdict
  and the officer's reason are written into the audit chain together. Rejection is never
  gated (it is the safe direction) but records whether the officer agreed with the
  verdict - that agreement rate is the calibration signal for this agent.
  GET /api/hypothesis/{id}/challenge is the read-only preview that belongs next to the
  Confirm button; its `would_gate_confirm` is asserted to match the gate's real behaviour.
  Deliberately LLM-FREE. An adversarial check that can hallucinate is worse than no check
  at all, and every likelihood ratio it reports must be reproducible by hand from the row
  counts it cites - GET /api/advocate-agent/base-rates exposes those counts.
  Two distinct probabilities are computed and must not be conflated: the per-signal
  likelihood ratio (conditional on the observed value, drives the Bayes update) and the
  unconditional pair-collision rate (drives the selection-effect arithmetic). Using the
  former for the latter makes a decisive hard-key match look like a scan artefact.
  Verdicts: SURVIVES / WEAKENED / COLLAPSES / UNASSESSABLE.
```

---

## Workers invoked directly (no route label)

These are named in `agent_modes.MODES` as secondary agents and are called from their own
API surfaces, but no route label dispatches to them. They are declared here because
`agent_modes` references them by name, and a name in the code that is absent from this file
is exactly the drift this manifest exists to catch.

### vigil

```yaml
agent: vigil
kind: worker
sensitivity: case
min_role: Constable
obligations: []
role: A5 - bias and compliance auditor
module: app/agents/vigil_agent.py::audit_request
graph_node: null
routes: []
timeout_s: 6.0
retries: 1
surfaces: [api, chat_stream]
reads: [query_text, watches]
emits: [vigil_receipt, audit_log]
guardrails: [redact_pii]
hitl: false
degraded: "receipt marked unavailable; the query is NOT auto-approved on failure"
notes: >
  Runs ACROSS agents rather than beside them - it audits the officer's prompt before the
  data agents see it. Rejects prohibited demographic targeting (Article 15), flags PII
  over-collection without a BNSS Sec 94/106 warrant, and attaches statutory citations to
  arrest/raid/seizure language. Compiles to a 'vigil:{req_id}' receipt in product_store.
```

### corridor

```yaml
agent: corridor
kind: worker
sensitivity: case
min_role: Inspector
obligations: []
role: Corridor intelligence compiler
module: app/agents/corridor_agent.py::compile_corridors
graph_node: null
routes: []
timeout_s: 12.0
retries: 1
surfaces: [api, autonomous]
reads: [evidence_ledger, crimes, geo_density]
emits: [product_store]
guardrails: [verify_claims, date_guard]
hitl: false
degraded: "last compiled corridor set served with its original timestamp"
```

### linkage

```yaml
agent: linkage
kind: worker
sensitivity: case
min_role: Inspector
obligations: []
role: MO case-matcher
module: app/agents/linkage_agent.py::compile_linkage
graph_node: null
routes: []
timeout_s: 10.0
retries: 1
surfaces: [api]
reads: [evidence_ledger, second_brain, crimes]
emits: [product_store]
guardrails: [verify_claims]
hitl: false
degraded: "no linkage returned; never asserts a match on a missing shared key"
notes: >
  Must name the SHARED EVIDENCE KEY (vehicle, phone hash, UPI, IP) for every cross-case
  link it asserts - see the CONNECT mode instruction in agent_modes.py.
```

---

## Services (autonomous loop only — no routes)

### sentinel

```yaml
agent: sentinel
kind: service
sensitivity: person
min_role: Inspector
obligations: []
role: Breach - watchlist tripwires
module: app/agents/sentinel_agent.py::scan_watches
graph_node: null
routes: []
timeout_s: 10.0
retries: 1
surfaces: [autonomous, api]
reads: [watches, crimes, alerts_store]
emits: [alerts]
guardrails: [vigil, redact_pii]
hitl: true
degraded: "tick logged as degraded; watches are NOT silently dropped"
notes: >
  hitl:true is ENFORCED. POST /api/sentinel/watches no longer registers a watch: it
  proposes a `watchlist_add` action and returns 202. register_watch() runs only as the
  executor of an approved action. Every proposal is screened by vigil first - a REJECTED
  screen (e.g. demographic targeting) blocks it before it reaches the queue. Proposals
  expire after 72 hours.
```

### products

```yaml
agent: products
kind: service
sensitivity: aggregate
min_role: Constable
obligations: []
role: Master Orchestrator - product compiler
module: app/services/product_store.py::refresh_expiring
graph_node: null
routes: []
timeout_s: 30.0
retries: 1
surfaces: [autonomous, api]
reads: [all_compiled_products]
emits: [product_store]
guardrails: []
hitl: false
degraded: "stale product served with its original compiled_at timestamp, never re-stamped"
```

---

## System nodes

### supervisor

```yaml
agent: supervisor
kind: system
sensitivity: aggregate
min_role: Constable
obligations: []
role: Intent classification and routing
module: app/agents/supervisor.py::supervisor_node
graph_node: supervisor
routes: []
timeout_s: 8.0
retries: 0
surfaces: [graph]
emits: [routes, entities, confidence, reasoning]
guardrails: [zero_assumption]
hitl: false
degraded: "falls back to VAULT only; confidence below 0.8 also collapses to VAULT"
notes: >
  Emits CLEAR sentinels on results/visuals/citations/brain_hits/actions so a turn does not
  inherit the previous turn's agent output from the per-session checkpoint.
```

### synthesize

```yaml
agent: synthesize
kind: system
sensitivity: aggregate
min_role: Constable
obligations: []
role: Answer composition and claim verification
module: app/agents/graph.py::synthesize_node
graph_node: synthesize
routes: [CHITCHAT]
timeout_s: 20.0
retries: 0
surfaces: [graph]
reads: [results]
emits: [final_answer, citations, reasoning]
guardrails: [verify_claims, G1_numbers, G2_no_result_honesty, G4_slop, G6_length]
hitl: false
degraded: "deterministic _synthesize() when the LLM merge fails - always available"
notes: >
  Pays for an LLM merge ONLY when more than one agent produced a result. A single-agent
  turn is already written from exactly its rows; a second pass cost ~4.9s and is another
  chance to drift. CHITCHAT routes straight here and must never be paired with a data agent.
```

---

## Known gaps this manifest makes visible

Run `python -m app.agents.manifest` to print the live version of this table.

**Both gaps this table used to list are closed (2026-09-25).** They are recorded here
because the point of this file is that a gap cannot hide, and a table that has only ever
been empty proves nothing:

| Was | Effect it had | Closed by |
|---|---|---|
| `osint` and `brain` had no graph node | Routes folded into `query`, which does not run them — the reasoning trail showed a fan-out that never happened | `brain_node` / `osint_node` in `app/agents/graph.py`; both declared above and asserted by `tests/test_agents_manifest.py` |
| `MemorySaver` checkpointer was in-memory | Session continuity reset on restart; there was no durable case file | `app/agents/checkpoint_store.py::SqliteSaver` — `tests/test_checkpoint_store.py` writes a thread in one process and reads it back in another |

| Gap | Effect |
|---|---|
| *(none currently known)* | |

## Human-in-the-loop contract

Any agent declared `hitl: true` produces a real-world effect, and that effect must go
through `app/core/hitl.py`:

| Rule | Enforced by |
|---|---|
| Proposer roles (Inspector, Analyst, Admin) and approver roles (Approver, Superintendent) are disjoint | `PROPOSER_ROLES` / `APPROVER_ROLES` |
| Nobody decides their own proposal | `_decide_guard` — `self_approval_forbidden` |
| The approver approves exactly the version they reviewed | payload SHA-256 at submit, echoed back on approve |
| Written justification to propose, written reason to decide or withdraw | `justification_required` / `reason_required` |
| Prohibited targeting never reaches the queue | vigil screen at submit |
| Stale requests cannot be approved | per-type TTL → `EXPIRED` |
| Every step is on the hash chain, bound to the payload hash | `audit_store.record_hitl_event` |

Adding a new real-world action means adding an entry to `hitl.ACTION_TYPES` (validator,
executor, risk, TTL) — never calling the effect directly from an agent or route.

## Policy

`sensitivity`, `min_role` and `obligations` are enforced, not descriptive. `orchestrator.run_agent`
asks `policy.decide(ctx, agent)` before an agent runs:

| Outcome | When | Effect |
|---|---|---|
| `DENY` | the caller's role ranks below `min_role` | the agent does not start; the officer sees the reason; nothing counts against the circuit breaker |
| `PERMIT_WITH_OBLIGATIONS` | the agent declares obligations | they are applied to the result by the orchestrator, whatever the agent's own code returned |
| `PERMIT` | otherwise | |

An aggregate-only role (`Policymaker`, `auth_middleware.AGGREGATE_ONLY_ROLES`) is decided before
rank: it is permitted every `sensitivity: aggregate` agent, with `aggregate_only` added to its
obligations, and the `query` agent, which runs only its aggregate templates for that role
(`zcql_repo.AGGREGATE_TEMPLATES`). Every other agent is `DENY`. See docs/SECURITY.md, section 4.

The caller is the request's security context (`app/core/security_context.py`): officer and role
from the verified token, one `call_chain_id` per request. Every decision is written on the
audit row for that request. Routers keep their own role checks; this is a second, independent one.

## Adding an agent

1. Add its block here — `agent`, `kind`, `role`, `module`, `graph_node`, `routes` are required.
2. If it gets its own node, add the node in `state.build_graph()` and the node fn in `graph.py`.
3. Run `pytest tests/test_agents_manifest.py`. It fails if the manifest and the compiled graph
   disagree, if two agents claim the same route, or if a route resolves to a node that does not
   exist.
