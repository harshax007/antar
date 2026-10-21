# Antar: agent card

Written 2026-10-14 in the format of the AI Agent Index (Casper et al., arXiv:2502.01635): 33 fields in 6 categories. Where there is nothing to report the field says "None" or "Unknown", as the Index does. Every statement here can be checked against a file named beside it.

The Index found that of 67 deployed agent systems, 19.4% disclosed a formal safety policy and fewer than 10% reported external safety testing. This card is Antar's disclosure. It reports no external testing, because there has been none.

## 1. Basic information

| Field | |
|---|---|
| Website | None. Runs on the owner's machine and, for the demo, on Zoho Catalyst AppSail. |
| Short description | A crime-intelligence workspace over the Karnataka State Police FIR record: questions in English or Kannada answered from the register with citations, a map, forecasts of registered cases, and link analysis between cases and accused. |
| Intended uses | Decision support for police officers and analysts: finding and counting cases, seeing where and when they concentrate, a forecast for the next 7 and 28 days by station and beat, and leads to check. |
| Not intended for | Deciding anyone's guilt. Scoring or ranking individuals for risk of future offending. Targeting any group. Issuing an order without a supervising officer. Use as evidence in court without the underlying FIRs. |
| Date deployed | Demonstration build, October 2026 (KSP Datathon 2026). Not in operational use. |

## 2. Developer

| Field | |
|---|---|
| Website | None |
| Legal name | Unknown (a datathon team; no legal entity) |
| Entity type | Individual or team project |
| Country | India |
| Safety policies | `docs/ANTAR_CONSTITUTION.md` (four laws, evidence classes), `docs/SECURITY.md` (threat model, controls, known gaps), `AGENTS.md` (what each agent may read, emit and must pass), and this card. |

## 3. System components

| Field | |
|---|---|
| Backend model | A setting, not a dependency (`app/services/llm.py`). `quickml`: models hosted on Zoho Catalyst QuickML. `openai_compatible`: any `/chat/completions` server, including one on the same machine. `none`: no model; every answer is written from the records. |
| Publicly available model specification | This card, `AGENTS.md` and `docs/ANTAR_CONSTITUTION.md`. They are in the repository, which is not public. |
| Reasoning, planning and memory | A supervisor routes a question to worker agents in a fixed graph (`AGENTS.md`, Topology). Routing is by rules first; the model is consulted only when the rules cannot decide, and may pick only from the templates it is shown. Session state is checkpointed per conversation in SQLite. There is no long-term memory the model writes to. |
| Observation space | What it is handed for one question: the question, earlier turns of the same conversation, and the FIR rows a template returned, each fenced as untrusted data. It cannot browse, read files or query anything itself. |
| Action space and tools | **None.** No tool, function or plugin is offered to the model (`tests/test_assume_compromise.py::TestWordsCannotAct`). It never writes a query: questions map to 26 approved templates (T1-T30) with validated parameters. Two real-world effects exist in the system, a watchlist entry and a patrol redeployment; both are proposals that a different, supervising officer approves (`app/core/hitl.py`). |
| User interface | A web application: Chat, Brain, Map, Predict, Search, and Trace & Telemetry. |
| Development cost and compute | Unknown. The forecast is a Poisson regression fitted with scikit-learn on a laptop in about a minute. No model has been trained or fine-tuned for this build; `app/obs/sdar_generator.py` collects scored rollouts that could later be used for that. |

## 4. Guardrails and oversight

| Field | |
|---|---|
| Weights | Not applicable: no model of its own. |
| Data | Not available. One million FIR rows; the real record runs from 2016 to 10 March 2024, and rows after that are seeded for the demonstration and labelled as such. |
| Code | Not public. |
| Scaffolding | Not public. `AGENTS.md` is executable: a test fails when it and the running graph disagree. |
| Documentation | In the repository: `docs/`. |
| Controls and guardrails | Outside text reaches the model only inside a fence it cannot forge, with instruction-shaped text removed. One gateway for every model call adds the policy, redacts phone, Aadhaar, email and PAN, and checks the reply; a leaked system prompt is blocked. Numbers and identifiers in an answer must exist in the rows, or the answer is written from the rows instead. No future calendar date leaves the backend. Social analysis returns aggregates only. A separate agent with no model in it prices every inferred link against its base rate before an officer can confirm it. Full list: `docs/SECURITY.md` section 3. |
| Customer and usage restrictions | Sign-in with a signed token; roles from Constable to Superintendent; case data needs Inspector or above; uploads and the audit log need Admin; proposer and approver roles are disjoint. No know-your-customer process: accounts are created by an administrator. |
| Monitoring and shutdown | Every question is traced with the query that ran, the rows read and the flags raised (Trace & Telemetry). Every API call is on a hash-chained audit log. **To switch the model off:** set `ANTAR_LLM_PROVIDER=none`. **To stop everything leaving the machine:** set `ANTAR_EGRESS_ALLOW=none`. In both cases the system keeps answering from the records. A circuit breaker stops calling a model that is failing. |

## 5. Evaluations

| Field | |
|---|---|
| Notable benchmark evaluations | None of the public agent benchmarks apply. |
| Bespoke testing | Forecast: rolling-origin back-test over 23 weeks of the real record (`docs/FORECAST_BACKTEST.md`). Top 5% of beats caught 40.4% of all crime in the next 7 days against 38.0% for last-4-weeks hotspots; the 80% ranges held 80.1% of the time. At station level for all crime it does no better than recent history (22.9% against 22.8%). Answers: a set of golden questions with expected templates and counts. |
| Safety evaluations by the developer | `docs/SECURITY_SCORECARD.md`, generated by `scripts/security_scorecard.py`: 161 cases across four suites, including 50 in which the model is assumed fully compromised and its worst-case output is fed directly to each consumer. All 161 stopped at the time of writing. Writing those suites found weaknesses, which were closed; each is listed in `docs/SECURITY.md` sections 3.6 and 3.7. |
| External red-teaming or audit: personnel | None |
| External red-teaming or audit: scope and methods | None |
| External red-teaming or audit: findings | None |

## 6. Ecosystem

| Field | |
|---|---|
| Interoperability | Outbound calls are limited to an allow-list and counted by host and purpose (`app/core/egress.py`): the model endpoint and its token service, an open-web search for a named subject (results always labelled unverified), a speech service, a translation service and a public holiday calendar. No inbound integrations. |
| Usage statistics | None. Demonstration use only. |

## 7. Additional notes

Known limits, stated plainly:

- The forecast is of registered FIRs, not of crime. More policing in a place produces more registrations there, so a forecast can reflect where police already are. This feedback has not been measured yet.
- No screen can prove a model will ignore an instruction hidden in a record. The design claim is narrower: an obeyed instruction has nothing to reach. The scorecard tests that claim, written by the same team that built the controls.
- The audit chain in the demonstration database is broken at one entry from earlier test runs and has not been reset.
- A session token cannot be revoked before it expires, and is held in browser session storage (`docs/SECURITY.md` section 7).
- The Search page's reconnaissance panel shows simulated module output.
- Interface text added recently is in English only when Kannada is selected.
