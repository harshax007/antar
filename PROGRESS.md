# Antar — Build Progress & Impact Log

A running record of what changed, why it mattered, and what it measurably did.
Newest work at the top. Numbers here are measured, not estimated.

**Current state:** 1,000,000 real FIRs · 1,170 tests passing · mean answer 656 ms · deploy artefact 84 MB

---

# Final demo brief — everything needed on the day

Written 2026-09-25. This section is the single page to read before presenting. Every number
in it was measured, and the "do not claim" list matters as much as the rest.

## 1. Start it

```powershell
cd D:\Project
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

```powershell
cd D:\Project\antar-frontend
npm run dev
```

Backend docs <http://127.0.0.1:8000/docs> · App <http://localhost:3000>

**Always call `D:\Project\.venv\Scripts\python.exe` by path.** A bare `python` resolves to
an unrelated tool's virtualenv on this machine.

**Boot takes 1-2 minutes.** `Application startup complete` appears within seconds and
`/api/health` answers immediately; the rest is background warm-up. Three lines look like
faults and are not: the two `SECURITY:` warnings (expected in `development`), and
`LLM decompose failed: TimeoutError` (QuickML cold). You are ready at
`Background warmup completed successfully!`.

Health check worth running before you present:

```bash
curl -s http://127.0.0.1:8000/api/health
```

`brain_backend` must read `onnx/fp32`, `case_file.durable` must be `true`, and
`brain_corpus.indexed_firs` must read `100000`.

## 2. The numbers, and where each comes from

| Claim | Value | Source |
|---|---|---|
| FIRs on record | **1,000,000** | `main.db`, rebuilt and `integrity_check` clean |
| Years covered | 2016-2026 (real record ends **2024-03**) | registry |
| Districts / stations | 56 / ~1,100 | registry |
| Crime groups | **113** (141 raw spellings) | `knowledge/taxonomy/` |
| Golden suite | **35/35** | `docs/golden_report.md` |
| Test suite | **1,135 passed, 3 skipped** | `python -m pytest -q` |
| Forecast: top 5% of beats catches | **40.4%** of crime | 23-week rolling back-test |
| Forecast: PAI @ 5% | **14.2** | same |
| Forecast: beats the last-4-week baseline | **22 of 23 weeks** | same |
| Brain corpus | **100,000 FIRs**, ~110 ms/query, +8.7 MB RSS | `docs/footprint/` |
| Live server peak RAM | **692 -> 446 MB** | `docs/footprint/after-step6-live.md` |
| Runtime environment | **509 MB**, torch-free | `D:\Project\.venv` |
| Mean answer latency | 656 ms | 17-question cold-cache set |

## 3. The demo, in the order that lands

1. **Think** — ask *"which district has the most kidnapping cases?"* Answer is
   `[VERIFIED]`/`[COMPUTED]` tagged, cites rows, ~650 ms, **no LLM required**. Then ask a
   follow-up, **restart the backend**, and ask another: the thread survives. That is the
   durable case file (P1-3), and it is a one-command proof.
2. **Connect** — *"chain snatching near a bus stand"* → the Brain returns comparable FIRs
   from the 100,000-row corpus in ~110 ms, each tagged **D**, labelled *"leads from similar
   records, not findings."*
3. **Anticipate** — the map's forecast layer, with the conformal range and the reasons.
   Say the back-test numbers out loud; they are the strongest thing in the build.
4. **WOW-3 — the spike** — the anomaly scan flags **Rajajinagar / chain_snatching**,
   8 cases against a baseline median of 2, MAD-z **4.05**, with its conformal band and the
   Gi\* hotspot check. Third in the list behind two real KSP anomalies, which is the right
   place for it to be.
5. **The adversary** — confirm an inferred hypothesis and let `advocate_agent` return
   **409** with the base-rate rebuttal. A system that argues with itself is the memorable
   moment.
6. **The export** — print `/report/{session_id}`: K/D/I/U badges, citations, per-turn
   audit hash, the document SHA-256, and a live **audit-chain verified** panel.
7. **The knowledge bundle** — `knowledge/`, an OKF v0.2 bundle with the query templates as
   `Attested Computation`. Nobody else will hand judges a standards-shaped knowledge
   package.

## 4. Say these before anyone finds them

* **`MO_Details` is populated on 651 of 1,000,000 rows.** This is why Antar does not offer
  behavioural profiling as a product claim.
* **The real record ends 2024-03.** Later data is seeded and labelled as such on screen.
* **Beat areas are Voronoi estimates** - no beat boundaries exist in the data - so PAI is
  approximate and labelled approximate.
* **Patrolling a flagged beat records more FIRs there.** The feedback loop is stated on
  every beat card; rotating patrols is the recommendation.
* **Near-repeat was measured and rejected** - 0 of 60 metrics moved. Volunteering this is
  more persuasive than any feature.
* **Identity is an unsigned header in `development`.** Set `ANTAR_AUTH_SECRET` before any
  claim about production security.

## 4b. Refresh the planted spike on the morning

WOW-3 is date-anchored, so check it before you present — on **both** trees if you use both:

```bash
cd D:\Project && .\.venv\Scripts\python.exe scripts/replant_p2.py --dry-run
```

If `w0` shows fewer than 8, drop `--dry-run`. It moves seeded row dates only, never
inserts, leaves the FIR count at exactly 1,000,000, and writes
`docs/p2_replant_revert.json` so `--revert` undoes it.

**The demo database is `D:\Project\data\main.db`.** The repo on E: uses a different file,
so re-planting on E: alone changes nothing an officer would see.

## 5. Known risks on the day

| Risk | Reality | Mitigation |
|---|---|---|
| **WOW-3 decays with the wall clock** | Re-planted 2026-09-25 and live: the scanner flags **Rajajinagar / chain_snatching, z = 4.05, 8 cases observed**, and `test_forecast_endpoint.py` no longer skips. The spike is anchored to the last 4 days of the current week, so it survives ~3 days unattended | On demo morning run `python scripts/replant_p2.py --dry-run`; if w0 is short, run it without the flag (5 seconds, FIR count unchanged) |
| QuickML cold start | 75 s cold, 4-6 s warm | Ask one throwaway question before presenting |
| `Dockerfile.onnx` is **unbuilt** | The OpenMP crash fix is in but unproven in a container | Demo from the laptop, not the container |
| Catalyst AppSail tier unconfirmed | `/tmp` capacity is unverified | Laptop is the primary; deployed link is the backup |
| **Repo lives on a failing HDD**, no git remote, 7 objects already lost | `D:\Project` holds code + data on the SSD | Push to a remote before the day |

## 6. If something breaks mid-demo

* **Frontend says "backend unreachable"** - check the port. `ALLOWED_ORIGINS` lists
  `localhost:3000` only; Next silently moves to **3001** when 3000 is taken, and every
  request is then blocked by CORS. Free port 3000 and restart.
* **An answer is slow** - the deterministic path always answers. `DEMO_MODE=true` and
  `ANTAR_BRAIN_BACKEND=torch` are the escape hatches; both are flags, nothing is rewritten.
* **The forecast looks empty** - `ANTAR_FORECAST_AS_OF=real` switches from the wall clock
  to the real record.

---

## One orchestration contract for both paths · 2026-09-26

Item #4 was "two orchestration paths, 727 lines duplicated". Measuring it first found
something sharper than duplication, and fixing that was worth far more than a rewrite.

```
orchestrator.run_agent() calls — chat_stream.py: 8   graph.py: 0
```

`AGENTS.md` declares a `timeout_s` and `retries` for every agent, and the orchestrator
registry is generated from it (verified: geo 8s, network 15s, alert_suggest 6s, all read
from the document at startup). `chat_stream` honoured that contract on every agent call.
**The graph honoured none of it** — it awaited the same agents directly:

```python
geo  = await geo_agent_run(state["user_text"], query.get("params", {}))
pred = await prediction_agent_run(...)
pat  = await pattern_agent_run(...)
sugg = await alert_suggest_agent_run(...)
```

No timeout, no retry, no circuit breaker, no degraded contract. So on `/api/chat/stream` a
hung agent cost 8 seconds; on `/api/chat` it hung the officer's entire turn, and the
declared budgets were documentation rather than behaviour.

This is exactly the failure `AGENTS.md` exists to kill — but in its most consequential
form. Not a label out of step with the code: **a protection that only half the product
actually had.**

### What changed

Every graph node now dispatches through a shared `_run()` helper: same registry, same
declared limits, same honest degraded reason. Nine call sites — geo, predict, pattern,
alert_suggest, network, profile, social, research, osint — plus both Brain tiers under the
manifest's 6s recall budget, because recall is an *enrichment* and must never be the reason
an officer waits for an answer that is already written.

Failures are now visible rather than silent. A failed sub-agent contributes nothing to
`results` instead of a `None` the writers would render as an empty panel, and the trail
carries `{"agent": "pattern", "step": "degraded", "detail": ...}` — honouring the line
AGENTS.md already promised: *"a failing sub-agent yields a degraded step, never a fabricated
band."*

### Tested as a contract, not as a refactor

`tests/test_graph_orchestration.py` asserts behaviour, not structure:

* a hung `geo` is cut off at its declared budget instead of holding the turn;
* a failing `pattern` degrades visibly **and its siblings still produce results** — one bad
  agent must not blank the composite node;
* a degraded node still returns a usable update, because LangGraph rejects a bare empty one;
* and a source check that no agent is ever awaited bare again, which is the regression that
  started this.

### What was NOT done, deliberately

The 727 lines are still two files. Collapsing `chat_stream` onto the compiled graph means
driving it with `astream` so the SSE step events come from the graph's own execution — a
genuine improvement, and a multi-day change to the one surface the demo runs on. The
divergence that could actually hurt an officer is closed; the cosmetic half of it can wait
for a week without a datathon in it.

---

### Two honesty defects cleared out with it

Found while deciding what was genuinely left to fix, and both were worth the few minutes:

**`get_reasoning_log()` returned a fabricated reasoning step.** For any session id,
including ones that never existed, it returned a hardcoded
`{"agent": "supervisor", "step": "intent_classification", "note": "Phase 1: wired to
NoSQL"}`. The reasoning trail is the evidence that an answer came from the record — a fake
one is a lie about how a police answer was reached, and it is the single worst thing this
system could invent. It had no callers, which is the only reason it never surfaced. It now
reads the real trail from `sessions` and returns an empty list when there is none.

**The last bare `except:`** (`admin_data.py`, date parsing) also swallowed
`KeyboardInterrupt` and `SystemExit`, so Ctrl-C during an ingest was absorbed by a date
parse. Narrowed to `(ValueError, TypeError)`. There are now no bare excepts in `app/`.

---

## The durable case file had three bugs, found by running the whole suite · 2026-09-26

P1-3 shipped with a clean full-suite run. It had not earned it: these paths only fail under
multi-turn concurrency, and the damage had to accumulate first. Three faults, each caused
by the one before it.

### 1. Every connection leaked

```python
with sqlite3.connect(...) as con:      # commits — does NOT close
```

A trap `sqlite3` sets deliberately: its context manager manages the **transaction**, not
the connection. Eight call sites, so every read and every write left an open handle holding
its lock. Under the graph's eight-node fan-out that becomes
`sqlite3.OperationalError: database is locked`.

Fixed at the `_connect` helper — commit, rollback on error, **close** — so the mistake
cannot return at a ninth call site.

### 2. The leak corrupted the store, and a corrupt store took down every request

`PRAGMA quick_check` on the live case file returned pages of errors:
`database disk image is malformed`. That explained a confusing mix of `DataError`,
`OperationalError` and `DatabaseError` — all downstream of one corruption.

**This made P1-3 worse than the `MemorySaver` it replaced.** An in-memory saver loses your
thread on restart; a corrupt file on disk loses the thread *and* 500s every turn forever.

Now: `quick_check(1)` on open, and a corrupt file is **quarantined** — renamed
`case_file.corrupt-<timestamp>.db` and kept, because it is the only evidence of how it
broke — while a fresh store starts. `get_tuple` degrades to "this is a new conversation"
instead of raising into the turn. Checkpoints are disposable by design (30-day TTL), so
losing a thread is acceptable; losing the product is not.

### 3. The recovery path crashed on its own warning

The quarantine message contained an emoji and raised `UnicodeEncodeError` on a cp1252
console — **inside the routine whose only job is to stop a corrupt file breaking things**.
Warnings now go through `_warn()`: ASCII only, and swallowed if even that fails. A warning
is never worth an exception.

### Tests

Four, aimed exactly at what broke: a corrupt file is quarantined rather than fatal; a
healthy file is never quarantined; an unreadable store loses the thread and not the turn;
and writing 40 checkpoints leaves fewer than five live `sqlite3.Connection` objects — the
leak, asserted directly.

**Full suite: 1,165 passed, 2 skipped.** Run time fell from 35 minutes to 11m50s, because
the leak had been throttling every test that touched the graph.

---

## Three registry sizes, three screens, no explanation · 2026-09-26

The startup log has been saying this for weeks and nobody read it as a problem:

```
Dataset overview cached —   995,505 FIRs
Dataset summary  cached — 1,000,000 FIRs
Dataset cycles   cached —   912,167 FIRs
```

**All three are correct.** Each exclusion is deliberate:

| surface | count | basis |
|---|---:|---|
| Full Data Set summary | 1,000,000 | every row, ungated — the true dataset size |
| Overview / charts | 995,505 | future-dated rows hidden (`_where(gate=True)`) |
| Crime Graph cycles | 912,167 | **complete calendar years only** — 2024 and 2026 are partial |

Future-dated rows are seeded ahead of the wall clock and are not "on record" today. The
radial clock drops partial years because half a year drawn on a 12-month dial invents a
seasonal shape that does not exist.

What was missing is that **no surface said so**. An officer clicking between two screens
saw 995,505 and 1,000,000 with nothing to explain the gap — which reads as a system that
cannot count, the opposite of what every other number here works to earn.

### `count_basis()` travels with the number

Each payload now carries a machine-readable descriptor the UI can render:

```
overview   995,505 FIRs — future-dated rows excluded
summary  1,000,000 FIRs — all rows including future-dated
cycles     912,167 FIRs — future-dated rows excluded; complete calendar years
                          only (partial: 2024, 2026)
```

Cycles was the worst offender: its `source` string named the future-date gate and stayed
silent about partial years, which drop **18x more rows** (83,338 against 4,495). Its
docstring was worse still — it claimed *"no future-date gate"* while the code immediately
below it gates, with a comment explaining why.

### Labels drift; arithmetic does not

`tests/test_count_reconciliation.py` reconciles the three against SQL rather than trusting
the labels:

```
summary  - future-dated  = overview
overview - partial-year  = cycles
```

If a future change alters one surface's filter without the others, the subtraction stops
balancing and the build fails — instead of the discrepancy reaching a demo. The basis must
also report the exact rows it dropped, not an estimate, and a year may not be both complete
and partial. **6 tests.**

---

## Resolution fidelity — the confidence score can finally say "I answered a broader question" · 2026-09-26

Two items from the improvement list, done together because they are the same fix.

### The blind spot

`query_agent.unresolved_filters()` enforces resolve-or-refuse properly, and its refusal
message even offers the nearest real crime types. But it runs on the **params**, so it can
only judge filters the selector actually extracted. A term the selector dropped is
invisible to it — which is how *"how many riots cases in Karnataka?"* returned **995,452
FIRs**, the whole registry, tagged `[VERIFIED]` at 0.99 confidence. There was nothing to
refuse, because `RIOTS` never arrived.

This is the failure mode that looks most like success: **a dropped filter always returns
MORE rows, never fewer, and more rows read as a confident answer.**

### `resolution_fidelity(user_text, params)`

Looks at the QUESTION against the RESOLVED params, and returns a 0–1 score plus the gaps
in plain words. It detects three things:

| gap | example message |
|---|---|
| named crime never applied | `crime type "riots" was not applied — this counts every crime type` |
| named crime only partly matched | `only part of "dacoity-by-drone" matched — answered as dacoity, ignoring "drone"` |
| year or place named but not applied | `year 2018 was not applied — this covers every year on record` |

**Deliberately not a second refusal path.** Refusing on a text heuristic would fire on
phrasings that are perfectly answerable — "how many cognizable cases", where the qualifier
is a FIR type rather than a crime group — and a system that refuses good questions is worse
than one that occasionally widens. The officer gets the answer, the score, and the reason.

### The score now discriminates

Fidelity **multiplies** the existing score, because a dropped filter does not make an answer
slightly worse — it makes it an answer to a different question.

| | score | label |
|---|---:|---|
| everything applied | **0.98** | High confidence |
| year dropped | **0.64** | Broader than asked — year 2018 was not applied |
| crime type dropped | **0.49** | Broader than asked — crime type "riots" was not applied |

That is the discrimination the measurement said was missing: before this, 99 of 102
answers scored 0.989 whether they were right or wrong. The gap also goes into the reasoning
trail, so `/explain` replays it.

### Two defects my own end-to-end check found

Written up because both passed the unit tests and only appeared on real questions:

* **"How many cases in Atlantis?"** reported a missing crime type called **"how many"** —
  the phrase regex matched the question's scaffolding. Fixed by treating interrogative
  words as non-crimes.
* **"dacoity-by-drone"** scored **0.99**. A filter *did* run — `DACOITY` matched inside the
  phrase — so every check passed while the answer was about a broader offence. Now the
  unmatched residue ("drone") is detected and reported, at a smaller penalty than a total
  drop, because a partial match is a partial answer rather than a wrong one.

**19 tests** in `tests/test_resolution_fidelity.py`, a third of them asserting what must
**not** be flagged: plain FIR counts, "cognizable"/"open"/"pending" qualifiers, bare numbers
that are not years, and connectors inside a real phrase like "crimes related to women". A
heuristic over free text earns its place only by being quiet on good questions.

### Also corrected: two false claims sitting in the code

* `_answer_confidence` still opened with **"Calibrated answer-confidence"** after the map
  was measured and rejected. It now states what was measured, what it still lacks, and
  points at `docs/CONFIDENCE_CALIBRATION.md`.
* **`425,015`** described the dataset as "the COMPLETE FIRs table" in **8 places** across
  `dataset.py` and `zcql_local.py`. The registry holds **1,000,000** — stale by 2.35x.

---

## Answer confidence measured for the first time — and what it exposed · 2026-09-25

`_answer_confidence` has always been documented as *"Calibrated answer-confidence"*.
Calibration is a testable claim — *of the answers given 0.8 confidence, 80% should be
right* — and nothing had ever tested it. `scripts/calibrate_confidence.py` now does.

### How it is measured, without a judge

Labels come from **SQL, not a model**. Each question is generated from the registry
together with its true count; the system answers through its real offline path; the label
is whether the stated number equals the number SQL computed. No LLM sits anywhere in the
measurement — the same rule `advocate_agent` follows, for the same reason.

Building it corrected my own error first. The initial ground truth scored the system at
25%, because it counted the raw table while Antar correctly **hides future-dated rows**
from every query path. Karnataka Railways theft: the system said 4,055, the ungated table
holds 4,179, and the system was right. A harness whose labels disagree with the product's
own semantics measures the harness.

### The result (n = 80, generated counting questions)

| | |
|---|---|
| Accuracy | **45.0%** |
| Mean reported confidence | **0.989** |
| Expected Calibration Error | **0.539** |
| Brier score | 0.538 |
| Bins occupied | **1 of 10** — every sample landed in 0.9–1.0 |

**The score is a constant.** The formula is
`0.40·min(1, cites/3) + 0.30·min(1, rows/3) + 0.30·routing_conf`, and a successful template
query always returns 10 rows and ≥3 citations, so the first two terms saturate at 1.0 and
the third rarely moves. It reports ~0.99 whether the answer is right or wrong, which means
it carries **no information at all** — and an isotonic map over a constant is still a
constant. Calibration was the wrong first fix; the score needs a signal that discriminates
before it is worth calibrating.

### What the failures actually are

Reading them is where this stopped being a calibration exercise. Two correctness bugs,
both confirmed from the resolved parameters, not inferred from the prose:

**1. An unresolved crime term is dropped, and the unfiltered answer is tagged `[VERIFIED]`.**

```
Q: "How many riots cases are on record in Karnataka?"
   params  -> {"crime_types": [], "zones": [], ...}
   answer  -> [VERIFIED] **995,452** FIRs are on record in Karnataka
   truth   -> 19,825      confidence -> 0.99
```

`RIOTS` is a real crime group with 19,825 rows. The term did not resolve, the filter
vanished, and the system answered **the size of the entire registry** with full confidence.
Same shape for `crpc` and `karnataka state local act`.

**2. A near-miss term is silently substituted for a different offence.**

```
Q: "How many attempt to murder cases in Kodagu in 2018?"
   params  -> {"crime_types": ["MURDER"], "zones": ["Kodagu"], "date_from": null}
   answer  -> [VERIFIED] **103** murder cases are on record in Kodagu (across all years)
   truth   -> 25          confidence -> 0.99
```

`ATTEMPT TO MURDER` is its own crime group. The answer is about murder, and the year was
dropped too. Also seen: *motor vehicle accidents fatal* answered as *non-fatal / vehicle
theft*.

This is the class of bug §2 of this log records as "the deepest correctness bug: silently
dropped filters" — back, for terms the selector never extracts. The guard that exists,
`query_agent.unresolved_filters()`, inspects the params **after** extraction and so never
sees a term the selector discarded. `resolve_crime_types` even documents the rule this
breaks: *"an unmatched crime term must NEVER be silently discarded, because a dropped
filter turns 'kidnapping in Mysuru' into 'every crime in Mysuru' and the answer looks
perfectly confident."* That is exactly what happens.

### The honest caveat on 45%

These are **machine-generated questions using literal registry labels** — "karnataka state
local act cases", "narcotic drugs & pshycotropic substances" — which are harsher than
anything a person would type. The golden suite of curated natural questions still passes
**35/35**. The finding is not "the system is 45% accurate"; it is that **the system handles
its curated set perfectly, degrades badly on unseen phrasing, and reports the same 0.99
either way**. The gap between those two numbers is the thing worth fixing.

### The fixes it led to: 45.0% -> 92.2%

Measuring the confidence score found two real bugs in entity extraction. Neither was a
calibration problem; both made the system answer a **different question** than the one
asked, confidently.

**1. Every registry crime label was unmatchable by its own name.**

```python
crime_types = [c for c in CRIME_TYPES if c.replace("_", " ") in low or c in low]
```

`low` is lowercased by `_norm`; every entry in `CRIME_TYPES` is the registry's UPPERCASE
label. `'RIOTS' in 'how many riots cases'` is **False**. That comparison never matched
anything, so all **115** registry labels were unreachable and only the **71** hand-written
synonyms worked. This is why the golden suite passed 35/35 — it is built from phrasings the
synonyms cover — while questions using the registry's own vocabulary silently lost their
filter.

**2. A synonym claimed a longer, more specific offence.** `murder` matched inside
"attempt to murder", so an answer about a distinct crime group came back as murder.

Both replaced by `_match_crime_terms()`: word-boundary matching over registry labels and
synonyms in one pass, **longest match first**, with claimed spans blocking shorter
overlaps. "attempt to murder" now beats "murder", and `RIOTS` / `CRPC` / `AFFRAY` are
reachable without anyone writing a synonym for them.

**3. A year before 2020 was silently dropped.**

```python
year_match = re.search(r"\b(202\d)\b", low)     # 202x only
```

The registry starts in **2016**. "in 2018" and "in 2016" matched nothing, so the officer
asked about one year and got every year. Measured: *attempt to murder in Kodagu in 2018*
answered **197** (all years) against a true **25**. A wider pattern further down the same
file already disagreed about what a year looks like.

### Result

| | before | after |
|---|---:|---:|
| Accuracy (n = 102) | 45.0% | **92.2%** |
| Expected Calibration Error | 0.539 | **0.080** |
| Brier | 0.538 | **0.082** |

Golden suite still **35/35**; 110 routing/query/template/heuristic tests green.

Two of my own measurement errors were corrected along the way, and both had scored the
system wrong for being right: ground truth must apply the **future-date gate** (the system
said 4,055, the raw table holds 4,179) and must match crime groups **case-insensitively**
(`expand_crime_types('THEFT')` returns `['THEFT', 'theft']`). I did not isolate how much of
the 45 -> 92 jump came from each fix versus each truth correction; the two product bugs are
demonstrated independently above.

### The map was fitted, tested, and REJECTED

With the bugs fixed, an isotonic map was fitted anyway and put through a 30% holdout:

```
holdout (31 unseen): ECE 0.038 -> 0.066
MAP REJECTED — no improvement. Nothing written; the raw score is used unchanged.
```

**It made calibration worse on data it had not seen.** In-sample it looked perfect
(0.080 -> 0.000), which is exactly the trap: the map was built from those labels. The raw
score is still nearly constant — 99 of 102 samples sit at 0.989 — so there is little for
isotonic regression to learn beyond noise in the tail.

`scripts/calibrate_confidence.py` now **refuses to write a map that fails its holdout**,
and says so. Shipping an unvalidated number about how trustworthy our numbers are is the
precise failure this work exists to catch.

The score is now well calibrated because the system became accurate, not because a curve
was bent to make it look so. What it still lacks is **discrimination** — it reports ~0.99
for almost everything, so it cannot warn an officer about the 8% it gets wrong. That needs
a resolution-fidelity signal (did every filter the officer named actually get applied?),
which is the next piece of work, not a curve.

---


## P2-4 — the export is evidence-grade, and the class no longer falls off it · 2026-09-25

The printable report at `/report/{session_id}` was already ~70% of an evidence-grade
export: per-turn audit-chain hash, citations to FIR rows, the reasoning chain, officer,
timestamp, and a SHA-256 over the whole document. It had one defect, and it was in the
worst possible place.

### The bug

`app/api/export_api.py::_answer_html` began by **deleting** the evidence class:

```python
text = re.sub(r"^\[(COMPUTED|VERIFIED|INFERRED)\]\s*", "", text, flags=re.M)
```

Every other part of Antar fights to keep that label attached to its claim. Synthesis tags
each line with it. The Brain tags corpus hits `D`. `advocate_agent` gates the
Inferred → Known transition and returns 409 until an officer overrides in writing. And the
printable report — the one artefact that leaves the system as a document, that an officer
signs and hands to someone who will never see Antar — **threw the class away**. A reader of
that PDF could not tell a row-level fact from a scored guess.

### What it does now

* **K / D / I / U badges** on every line that carries a class, colour-coded and titled.
  Caught by a test of my own: the marker also appears *after* a list prefix
  (`1. [COMPUTED] Bengaluru City …`), and matching only at position 0 dropped the class on
  exactly the ranked answers an officer is most likely to act on.
* **A legend inside the document**, because a badge nobody can decode is decoration and
  this report is read by people who have never seen the system.
* **A live audit-chain panel.** A per-turn hash proves nothing on its own; the question is
  whether the chain it belongs to still verifies. `verify_chain_report()` runs at render
  time and the document states the result — green with the verified/total counts, or red
  and explicit: *"AUDIT CHAIN BROKEN — this report must not be relied on"*, naming the
  entry index and whether it failed on digest or linkage. A test asserts the panel is
  capable of saying no, because a banner that is always green is a sticker.
* Escaping unchanged: record text is escaped, never executed (asserted).

**11 tests**, `tests/test_export_evidence_grade.py`.

---

## P2-1 — the knowledge layer as an OKF v0.2 bundle · 2026-09-25

`knowledge/` is now an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/open-knowledge-format)
v0.2 bundle: **207 files, 254 KB**, generated from the registry and the running code by
`scripts/build_okf_bundle.py`, with `tests/test_okf_bundle.py` failing the build when it
and the system disagree.

| | |
|---|---:|
| Crime groups | 113 |
| Statutes (top by volume) | 40 |
| Query templates, as **Attested Computations** | 22 |
| Agents | 20 |
| Vocabularies | 2 |

### Why bother, beyond "a standard exists"

The conformance bar is deliberately tiny — parseable YAML frontmatter with a non-empty
`type` — so a bundle can be worthless and still conform. Three things make this one worth
handing to someone:

**The templates are `type: Attested Computation`.** That is the spec's shape for a
parameterised query with an `executor`, a `receipt` and a deterministic `attester` — which
is exactly what the T-series whitelist is. Parameters are read from each template's
pydantic model, so the markdown IS the callable interface, and a test asserts the two never
drift. The deterministic spine stops being an implementation detail.

**The trust signals do the honesty for us.** Every concept derived from the database is
`generated: {by: process:antar-okf-export}` and carries **no** `verified` key, so OKF's own
tier derivation reports it as *unverified*. The constitution and the evidence classes —
the two things people wrote and own — carry `verified: {by: human:...}` and read as
*human-reviewed*. A test asserts that generated content never claims a `human:` actor,
because that prefix is what a consumer keys its trust tier off.

**The uncomfortable numbers are in it.** `registry.md` has a "What this record does not
contain" section (no event times, no accused-identity column). The MO vocabulary leads with
its coverage — **651 of 1,000,000 rows** — and is marked `status: draft` because OKF's
lifecycle signal is the honest place to say a field is not usable at scale yet. The
forecast model card carries a "What was tried and rejected" section for the near-repeat
null result, and a `stale_after` a year out, because a model card outlives its numbers.

### What building it found in the data

Generating the taxonomy from the registry surfaced a defect nobody had counted:

**`CrimeGroup_Name` holds 141 raw spellings for 113 actual crime groups.** Two kinds of
duplication, both carrying real volume, so neither side is dismissible as a typo:

| | |
|---|---|
| internal whitespace | `'CYBER CRIME'` 18,609 vs `'CYBER CRIME'` 49,399 |
| case | `'ASSAULT'` 159 vs `'assault'` 460 |

Anyone counting crime groups straight off that column gets an inflated number — and the
first two versions of this generator did exactly that, silently overwriting concepts whose
slugs collided. The bundle now canonicalises (single space, trimmed, upper case), sums the
counts, and **lists every raw spelling on the concept** rather than hiding the merge.

Also caught: a stray FIR row (`id NULL`, `District_Name 'Central'` — a district PROGRESS
records as never having been real) inflating the registry to 1,000,001 between test runs.
It is test pollution that `conftest` cleans up, not a defect in the shipped database, which
holds exactly **1,000,000**. The bundle asserts that count against the live database on
every run.

---

## P1-4 and P1-3 — both known gaps in AGENTS.md are closed · 2026-09-25

`AGENTS.md` exists so that a gap between the documentation and the running graph cannot
hide. It listed two, and both were the kind that look fine in a demo and are wrong in the
field. They are now closed, and the "Known gaps" table is empty for the first time.

### P1-4 — `brain` and `osint` were declared, routed to, and never ran

A route addressed to either folded into `unrouted_fallback: query`, and **query does not
run them**. So a BRAIN turn produced a reasoning trail naming the Brain on a turn where it
was never consulted, and an OSINT turn claimed an open-web check that never happened. The
trail was the product's honesty claim, and on those routes it was wrong.

Both are first-class graph nodes now (`brain_node`, `osint_node` in `app/agents/graph.py`),
declared in the manifest and asserted by `tests/test_agents_manifest.py`.

**`brain_node`** searches both Brain tiers and keeps them apart, because they carry
different evidence weight:

| Tier | What | Class |
|---|---|---|
| curated | summaries, MOs, patterns, investigations — full RRF hybrid → cross-encoder → MMR | as stored |
| corpus | the 100,000 FIRs indexed in P1-2, from the memory-mapped int8 store | **D (derived)** |

Corpus hits are tagged `D` and the class travels with the hit, so synthesis cannot promote
a similar FIR into a finding. Measured through the node: *"chain snatching near a bus
stand"* → 5 corpus hits, top one the Udupi `Near Gudri Bus Stop` FIR. An empty result is
reported as **"no comparable record"**, never as silence.

**`osint_node`** is the only agent that leaves the building, so it has two rules the
others do not: everything it returns stays labelled UNVERIFIED and is never merged into
the record, and it **refuses without a named subject** rather than scanning on a guess.
Searching the open web for whatever capitalised word happened to be in the sentence is how
an uninvolved member of the public ends up in a police work product.

`_synthesize` now renders Brain recall too — it had nothing to render before, because
nothing ever reached it on that route. The line ends *"These are leads from similar
records, not findings."*

### P1-3 — a durable case file

The graph ran on `MemorySaver`: an in-process dict. An officer's thread died with the
process — every restart, redeploy and crash. `app/agents/checkpoint_store.py` replaces it
with a `BaseCheckpointSaver` over stdlib `sqlite3`. `thread_id` is still `session_id`.

Two decisions worth recording:

- **No new dependency.** `langgraph-checkpoint-sqlite` would be one more package in an
  image that must fit 2 GB, and it puts retention — how long an officer's questions are
  kept — inside a third-party package. Under the DPDP Act that belongs to Antar, so
  `prune()` is ours: threads untouched for 30 days go at startup.
- **A connection per call, not a shared handle.** `sqlite3` objects are thread-affine and
  the graph runs nodes in a thread pool; a shared handle would need a lock serialising
  every node. WAL plus short-lived connections lets a fan-out of eight nodes write
  together.

Reversible per §2: `ANTAR_CHECKPOINT=memory` restores the old saver, and a store that
cannot be opened falls back to it with a warning rather than refusing to boot.

**Proved the only way it can honestly be proved.** Same-process reads demonstrate nothing
about durability — an in-memory dict passes those. `tests/test_checkpoint_store.py` writes
a checkpoint in one interpreter, lets it **exit**, and reads it back from a second. End to
end on the real graph: a full turn ran, the process ended, and a fresh process recovered
the thread — 5 checkpoints, the question, and the answer *"Bengaluru City has the most
kidnapping and abduction cases"* intact.

`/api/health` now reports `case_file: {backend, durable, threads, checkpoints, mb}`. The
difference between a durable thread and a disposable one is invisible until the day it
matters, so it is reported rather than assumed.

**14 new checkpoint tests + 19 manifest tests green.**

---

## P1 — corpus recall shipped, near-repeat rejected, clean copy exported · 2026-09-24

Two P1 items from `final_backend.md` §6 were built and **measured**. One shipped, one did
not. The measurement is the point: a plausible feature that does not move a back-test is
exactly what a back-test exists to catch.

### P1-2 — the Second Brain finally searches the actual FIR corpus (SHIPPED)

Before this, semantic recall only saw curated rows (summaries, MOs, patterns). The million
FIRs were invisible to it, so "find cases like this one" had nothing to find.

| | |
|---|---|
| Indexed | **100,000 FIRs** — composite doc: crime group, head, place, village, station, district, date, MO |
| Store | `brain_vectors.db` 81.6 MB int8 + packed memmap 36.6 MB (`.i8` / `.ids` / `.mult`) |
| Latency | **1,150 ms → ~110 ms** per query after packing the corpus into one memory-mapped array |
| Working set | **+8.7 MB RSS** across a run of searches — the pages are file-backed, so the OS can evict them |
| Surface | `GET /api/brain/similar` — hits, `corpus: {indexed_firs, mb}`, `evidence_class: "D"`, honest note when empty |
| Tests | `tests/test_brain_vec_store.py` — 8 pass, incl. packed-vs-scan parity and a stale-pack guard |

Real output, not a synthetic probe: *"chain snatching near a bus stand"* → **0.705 · Chain
Snatching — Near Gudri Bus Stop, Gulvady, Kundapura Rural PS, Udupi · 2024-03-05**.

One bug caught by my own parity test and worth recording: `pack()` originally re-quantized
vectors that were **already int8**, and the double rounding silently reordered near-ties.
It now copies the original int8 bytes unchanged and stores a per-row multiplier.

### P1-1 — near-repeat / self-excitation (MEASURED, NOT SHIPPED)

Mohler et al. (JASA 2011) report a self-exciting point process catching 660 of 2,627 crimes
against 547 for a prospective hotspot map at 10% of area flagged. The part a **weekly**
panel can carry honestly is spatial spillover: `nbr1` = neighbours' *last week*, against the
existing `nbr` = neighbours' *four-week mean*, which smooths the spike away.

Both arms ran the full rolling back-test — same 23 origins, same refit schedule, same PAI
and hit-rate definitions:

**0 of 60 metrics materially improved · 0 worsened · 60 within noise.** Fitting was **12%
slower** (390.9 s vs 349.1 s). The baseline arm reproduced the published numbers exactly
(beat · all crime: top-5% 0.4038, PAI 14.24, 22/23 weeks), so `docs/FORECAST_BACKTEST.md`
stands unchanged.

Why, honestly: near-repeat lives at the scale of **days and hundreds of metres**. Our cube
is weekly counts over stations and beats, and the registry has dates but no times. At that
resolution `nbr1` is largely collinear with `recent1` and `nbr`. A **data-resolution limit,
not a modelling failure** — so the code stays behind `ANTAR_FORECAST_NEAR_REPEAT` (off)
rather than being deleted. Full write-up: `docs/footprint/near-repeat-ab.md`.

### Clean runnable copy exported off the failing drive

`scripts/make_clean_copy.py --dest D:/Project` — **367 files · 1,844 MB**, onto D: (SSD),
away from the HDD that is losing sectors.

- Takes: `app/`, `scripts/`, `tests/`, `docs/`, `models/onnx/`, entry points, requirements,
  Docker and Catalyst config — and the databases it actually reads (**rebuilt** `main.db`,
  `brain_vectors.db` + its packed sidecars).
- Leaves: the damaged repo `main.db`, `node_modules`, `.next`, `__pycache__`, `.git`,
  `*.bak`, scratch sessions.
- Drops the **int8 ONNX weights** (54 MB): their own `meta.json` records a parity failure
  (0.990 against a 0.995 gate), so the loader never selects them. A weight file the code
  will not load is not a file required to run the code.
- Rewrites `.env` so `ANTAR_DB`, `OBS_DIR` and `ANTAR_BRAIN_DB` all point **inside** the
  destination — a copy that still reached back to E: would look fine right up until it did not.

Verified in place: `quick_check` **ok**, **1,000,000** FIR rows, 163 routes import, ONNX
embedder loads `onnx/fp32`, and corpus search returns the Udupi chain-snatching FIR in
**122 ms**.

> ⚠ The exported `.env` carries the real QuickML client secret and refresh token. It is
> fine on a local disk; it must not be committed or handed to anyone outside the team.

### First boot of the copy found one real bug

`obs/store.py` created the observability **directory** on demand but not the **schema**:
on a fresh `OBS_DIR` every request logged `obs_close_failed: no such table: traces`,
because `init_db()` runs late in startup and the HTTP middleware traces the very first
request. Same ordering problem as the directory fix a day earlier, one level deeper.
`conn()` now creates the schema once per process (`CREATE TABLE IF NOT EXISTS`, so it is
idempotent) and swallows a failure rather than letting observability break a request.
After the fix: **0 errors**, `traces` populated on first boot. 15 obs tests pass.

Verified over HTTP from `D:\Project`: `/api/health` ok on the ONNX backend, a real chat
answer (*"Bengaluru City has the most kidnapping and abduction cases — 5,951 FIRs, 37% of
the Karnataka total"*), `/api/forecast/status` serving 72 models, and `/api/brain/similar`
returning three real chain-snatching FIRs from Udupi, Mandya and Vijayapura.

Known and unchanged: boot spends 20 s on the Catalyst Data Store fetch before falling back
to the 3 planted summaries, because the local store holds only the `fir` tier. Documented
behaviour, not a regression.

### Dedicated environment — and the crash it exposed · 2026-09-24

The project had been running under an unrelated tool's virtualenv that happened to sit
first on `PATH` (`hermes-agent`). It now has its own: **`D:\Project\.venv`**, Python
3.11.15, built from `requirements-runtime.txt` — **509 MB against ~2.5 GB** for the
torch-bearing environment. That gap is the ONNX work made concrete.

First boot in the clean environment **died at exit 139** — `Application startup complete`,
then nothing after `Loading Second Brain embedder`. No traceback. Bisected to two lines:

```python
import sklearn; import onnxruntime   # Windows fatal exception: access violation
import onnxruntime; import sklearn   # fine
```

scikit-learn 1.4.1.post1 and onnxruntime 1.30.0 each ship their own OpenMP runtime. When
scikit-learn's loads first, onnxruntime's `capi/_pybind_state` import hits an access
violation inside `create_module` and the interpreter is killed outright.

**This was not a new-environment problem.** It reproduces identically in the old one; it
stayed invisible because torch loads a compatible OpenMP first and wins the race.
`Dockerfile.onnx` installs no torch, so **the image we are about to deploy is exactly the
configuration that crashes** — it would have surfaced as a container that starts, reports
healthy, and vanishes a minute into warm-up.

Fixed by importing `onnxruntime` up front in `main.py` and `tests/conftest.py`, guarded so
a torch-only environment still boots. Warm-up now runs through to
`🎉 Background warmup completed successfully!`.

**Suite in the clean environment: 1,096 passed, 4 skipped** (12m11s). The three extra skips
against the torch run are all correct: two torch-parity tests with no torch to compare
against, and the working-set guard, which needs `psutil`. `psutil` is now installed —
that test asserts RSS stays under 25 MB across 20k rows and is the reason a 100k-FIR corpus
fits in a 2 GB box, so it must never be allowed to skip quietly. `RUN.md` documents all of
this.

Also found, not acted on: the `hermes-agent` venv declares `numpy==2.4.3` and
`fastapi==0.133.1` in its own `requires.txt` but currently holds Antar's pins (1.26.4 /
0.115.5). Installing Antar downgraded that tool's dependencies underneath it. Left alone —
it is a separate application and nothing about Antar touches it any more.

### Suite re-verified after all of the above

**1,099 passed, 1 skipped** in 10m23s — +8 over the pre-P1 run (the `vec_store` tests),
nothing regressed by the near-repeat plumbing, the ONNX backend or the rebuilt database.

---

## ⚠ The repo drive is failing · 2026-09-23

`main.db` has **5 unreadable 4 KiB pages** at byte 1,352,183,808 (`quick_check`: error
266 = `SQLITE_IOERR_READ`). Windows logged `disk` Event ID 7 — *"The device
\Device\Harddisk0\DR0 has a bad block"* — 15 times at 03:44; `E:` is Disk 0, a
ST1000LM049 **HDD**. The :8000 backend died at ~03:33 and has not been restarted.

- The bad pages belong to **`forecast_cube`** — derived, rebuilt at startup in ~35 s.
- **All 1,000,000 FIR rows read cleanly**; every other table returns its row count.
- But `integrity_check` and `VACUUM INTO` abort on the bad pages, so the file cannot
  currently be fully verified or copied, and anything reading the cube fails
  (forecast warm-up, `python -m app.forecast.run`, the footprint meter's RAM mode).

**Rebuilt the same day** with `scripts/rebuild_db.py` (table-by-table copy, which works
around the unreadable pages that defeat `backup()` / `VACUUM INTO`):

| | |
|---|---|
| New database | `E:\Datathon_2026\Res\main.db` — source left untouched |
| Copied | 51 tables · **1,113,356 rows, every count matching source** · 22 indexes · the `crimes` view |
| Skipped (derived, rebuilt at startup) | `geo_units`, `forecast_cube`, `forecast_output`, `forecast_models`, `forecast_meta` |
| **`PRAGMA integrity_check`** | **ok** — the check the damaged file could not complete |
| Failures | none: every object copied cleanly, so the damage was confined to the skipped tables |

Verified end to end against the new file: cube rebuilt (1,027,987 rows, 34 s), both
forecast runs (72 models each; the real-record run reproduced 257,345 rows exactly),
**golden suite 35/35**, `quick_check` still ok afterwards.

Still open: the repo — and its `main.db` — remain on the failing HDD, and the backend
still defaults to the damaged copy until `ANTAR_DB` points at the rebuilt one. `chkdsk
/scan E:` not yet run. Details in `final_backend.md` §1.2.

---

## Plan v2 — research-grounded roadmap to industry-ready · 2026-09-23

`final_backend.md` rewritten around **Think · Connect · Anticipate** after researching the
Catalyst AI toolkit, OKF, and the crime-analytics literature. Corrections worth knowing:

- **Context Serve is not a RAG service** — it serves Catalyst's *own docs* to LLMs
  (`llms-full.txt`, `/index.md`). Nothing to architect on.
- **Catalyst MCP does not wrap your APIs** — custom servers only bundle Catalyst's own
  tools. Publishing Antar over MCP means running our own server (plan P2-3).
- **NI CLI** (`catalyst appsail:add -ni …`) makes deployment scriptable — worth having
  when there is one demo window.
- **QuickML** stays the generative path: it is off-box compute, which is what a 2 GB
  container needs.

Research that **changes** the build: a self-exciting / near-repeat term for the forecast
(Mohler et al., JASA 2011 — +21% over a prospective hotspot at 10% of area), Fellegi-Sunter
probabilistic linkage instead of a hard 0.82 Jaro-Winkler cut-off, and an OKF v0.2
knowledge bundle. Research that **confirms** it: RRF hybrid retrieval is already
implemented exactly as the 2026 benchmarks recommend — do not touch it.

Gaps the research surfaced in our own code and manifest: no durable case file
(`MemorySaver` is in-memory — `AGENTS.md` says so), `brain` and `osint` have no graph node,
and the ingest path is CSV-only with no idempotency or provenance stamp.

---

## 2 GB plan — measured after the thread cap + ONNX · 2026-09-23

Backend restarted on the rebuilt database; `/api/health` reports
`"brain_backend": "onnx/fp32"`. Full suite **1,091 passed, 1 skipped**.

| Live server (`scripts/measure_footprint.py --pid`) | 2026-09-22 | Now | Change |
|---|---|---|---|
| RSS | 502.1 MB | 451.5 MB | −50.6 MB |
| Peak RSS | 691.8 MB | **445.9 MB** | −245.9 MB |
| Private (reserved) | 1,672.8 MB | **435.2 MB** | **−1,238 MB** |

| Fresh warm-up, in process | Baseline | Now | Change |
|---|---|---|---|
| RSS after warm-up | 634.1 MB | **437.1 MB** | −197.0 MB (−31%) |
| Peak | 649.3 MB | 439.3 MB | −210.0 MB |

**Disk is unchanged at 2,807 MB** and still 755 MB over budget: torch is still
*installed* locally, and only the torch-free image (`Dockerfile.onnx`, not yet built)
removes it. Reports: `docs/footprint/after-step6{,-live}.md`.

Fixed while measuring:
- `data_sessions/obs/obs.db` was **unreadable** (WinError 1392) — another file lost to the
  failing drive — so every request logged `obs_close_failed`. `OBS_DIR` now points at
  `E:\Datathon_2026\Res\obs`, and `app/obs/store.py` creates its directory on connect
  instead of depending on startup order. The corrupt file cannot be deleted until chkdsk.
- The ONNX parity test was going **online** and re-downloading an 88 MB snapshot:
  `tests/conftest.py` now forces `HF_HUB_OFFLINE` before anything imports the hub, which
  is what its own docstring already promised. Cache restored to one snapshot.
- The meter reported `main.db.gz` as 0 MB once the database moved; it now falls back to
  the repo copy instead of quietly shrinking the disk total.

---

## 2 GB plan — the Second Brain runs on ONNX, not torch (step 6) · 2026-09-23

The embedder and cross-encoder now run the **same weights** on onnxruntime, with no torch
and no transformers in the process. torch + transformers + sympy are 681 MB of the
1,118 MB package closure, against a budget the deployment is 755 MB over — and the
weights are only ~90 MB each. The framework was the cost.

| At one thread (production setting) | ONNX fp32 | torch |
|---|---|---|
| RSS with both models loaded | **195 MB** | 513 MB (−62%) |
| Load time | **0.7 s** | 15.9 s (23× faster) |
| Embed one query | **7.5 ms** | 16.6 ms |
| Rerank 20 passages | 184 ms | 188 ms |
| `torch` imported | **No** | Yes |

**Identical answers, proven, not assumed.** `scripts/export_onnx_models.py` checks every
export against the torch model that produced it and refuses to mark it good otherwise;
`tests/test_brain_onnx_parity.py` re-checks on every run. Embeddings match torch at
**cosine 1.000000**, and the reranker's ordering is identical (max logit difference 0.0),
including on Kannada, empty and 4,000-character inputs.

- **int8 is built but disabled.** Best config (QUInt8, per-channel) reaches cosine 0.987;
  the gate is 0.995. The Brain ranks by cosine, so ~1% drift can reorder near-ties. The
  loader consults the recorded parity, so the file existing is not enough to enable it.
- **Nothing is removed.** `ANTAR_BRAIN_BACKEND=torch` rolls back; a missing or broken
  export falls back to sentence-transformers on its own. `/api/health` now reports
  `brain_backend` so a silent fallback is visible.
- **The deploy image is prepared but NOT built**: `Dockerfile.onnx` (multi-stage: export
  with torch, serve without it) and `requirements-runtime.txt`, ≈−730 MB by package
  sizes. Docker Desktop was not running, so that figure is inferred, not measured.
  `tests/test_requirements_sync.py` stops the two requirement files drifting.
- Measurements: `docs/footprint/onnx-backend.md`.

Also fixed on the way: `.env` was setting `ANTAR_DB` with no effect — `db_path` reads the
environment at import, long before anything calls `load_dotenv()`. It now reads that one
key from `.env`, with a real environment variable still winning.

---

## 2 GB plan — BLAS thread cap (step 2b) · 2026-09-23

`main.py` now pins `OMP_NUM_THREADS` / `OPENBLAS_NUM_THREADS` / `MKL_NUM_THREADS` to 1,
and only when the operator set none of them. numpy and scipy each bundle OpenBLAS, which
reserves a workspace per CPU thread at import.

| | Before | After |
|---|---|---|
| `import main`, private (reserved) memory | 903 MB | **164 MB** |
| `import main`, RSS | 208 MB | 208 MB |
| Forecast fit, 72 models | 75.0 s | 76.2 s (+1.6%) |
| Golden suite, warm | 12.03 s, 35/35 | 12.00 s, **35/35** |

- **Production is unchanged**: the container already sets `OMP_NUM_THREADS=1`
  (`Dockerfile`, `app-config.json`). This makes local dev, tests and a deploy that lost
  the variable behave the same way.
- The saving is *reserved* memory, not resident — a Linux cgroup charges for resident
  pages, so it sees less than the headline. Kept because it costs nothing measurable.
- `tests/test_runtime_env.py` (3 tests) guards the cap, the operator override and the
  import ordering. It caught a real defect first time out: per-variable `setdefault`
  silently capped OpenBLAS for anyone who raised `OMP_NUM_THREADS`, because OpenBLAS
  prefers its own variable.
- Method and numbers: `scripts/bench_blas_threads.py`, `docs/footprint/blas-threads.md`
  (partial — the 2 and 4 settings are blocked by the drive fault above).

**Backend restart required** for the cap to take effect on :8000.

---

## 2 GB footprint plan — baseline measured · 2026-09-22

Plan: `final_backend.md`. New meter `scripts/measure_footprint.py` (read-only on the
database; RAM measured by running the real `background_warmup()`; `--pid` for a running
server; `--compare` for before/after). Reports are in `docs/footprint/`. No app code
changed.

| | Measured | vs 2 GB |
|---|---|---|
| Disk: db 1,415 + gz 84 + packages 1,118 + models 175 + code 12 | **2,803 MB** | over by 755 MB |
| …torch stack alone | 688 MB | ≈ the whole overage |
| …`main.db` that must ship (base tables) | 495 MB | the other 920 MB rebuilds at startup |
| RAM, live server (3 h) | 502 MB working set · 1,673 MB private · 692 MB peak | under |
| Embedder load | +306 MB working set | the largest single step |

- **BLAS thread buffers:** at 12 threads, importing numpy + scipy commits 758 MB private.
  At one thread it commits 20 MB. This is the cheapest lever found (plan step 2b, needs
  a timing check first).
- The embedder in use is `all-MiniLM-L6-v2` (`.env`), not BGE-small as documented.
- The local Brain holds 3 planted rows: the Data Store load hits its 20 s cap by design.

---

## Map forecasting (USP #2) — where it stands · 2026-09-19

Plan: `docs/MAP_FORECASTING_PLAN.md`. **Phases 1–6 built; Phase 7 (hardening, demo rehearsal)
remains.** Phase-by-phase detail follows below this summary.

> **"Where is crime most likely next week, how sure are we, and why?"** — answered for
> every police station and beat in Karnataka, 7 and 28 days ahead, as a range with its
> reasons, with an accuracy measured the way the field measures it, and a one-click route
> to *propose* a patrol through the existing approval flow.

### The numbers (back-test on the real record, 23 weeks, Oct 2023 – Mar 2024)

| Next 7 days | Top 5% caught | Last-4-weeks hotspots | Ceiling | Weeks better | PAI @ 5% land |
|---|---|---|---|---|---|
| **Beats — all crime** | **40.4%** | 38.0% | 56.3% | 22 / 23 | **14.2** (12.8) |
| **Beats — property crime** | **52.0%** | 41.8% | 99.1% | 23 / 23 | **15.9** (10.9) |
| Stations — all crime | 22.9% | 22.8% | 25.3% | 14 / 23 | 11.8 (11.8) |

- **Ranges hold what they say:** 80% ranges held 79.8–80.8%, 90% ranges 89.8–90.5%,
  wherever ≥ 0.5 FIRs are expected.
- **Beats the baseline on Poisson deviance in every fitted model** (64/64 real, 62/62 wall
  clock); by 20–40%.
- **Honest where it is weak:** at station level the ranking only matches last month's
  counts — the gain is at beat level, where officers deploy; station-level narcotics at 28
  days ranks worse than last-4-weeks hotspots (enforcement-driven).
- Full tables: `docs/FORECAST_BACKTEST.md` (generated by `python -m app.forecast.backtest`).

### What an officer gets

| Surface | What |
|---|---|
| **Map** | Forecast layer (stations → beats in a district), Gi\* clusters, recent FIRs; always-visible as-of chip with the real-history share; "where next" list; beat card with range, reasons, 26 weeks + the week ahead, crime heads, the beat's own back-test record; **Propose patrol → Approvals** with the forecast attached; accuracy strip → generated model card |
| **Chat** | "Where should I patrol next week in Mysuru?" · "theft forecast Bengaluru City next 4 weeks" · Kannada — bottom line as a range (class **I**), accuracy as context, top 5 beats as evidence, limits; refuses unknown places and mixed categories; "Open the forecast on the map" deep-links to the beat |
| **API** | `/api/forecast/hotspots · layer · unit/{name} · backtest · status`, p95 < 300 ms; `/api/predict/model-card` generated |

### Plan items A1–A10 — all closed

| # | Was | Now |
|---|---|---|
| A1 | Every window anchored to its own wall clock | One as-of for the whole map (`ANTAR_FORECAST_AS_OF`, default wall clock per D1) |
| A2–A4 | `/api/map/predicted` = most crime this month, labelled "predicted", with a fabricated "Surge detected … increase patrols" from a stale table | A view over the real forecast: ranges, class I, no invented surge |
| A5–A6 | Model card described DBSCAN (never ran) and a "CCTNS live replica" (not true) | Generated from code, fitted models and the back-test; says "not measured" when it isn't |
| A7 | Hardcoded "3.0–7.0 @ 90%" band shown as a conformal interval | No alert → no band, and it says why |
| A8 | No accuracy ever measured | Rolling back-test, PAI, coverage, per-unit track record |
| A9 | 14.5k impossible coordinates | `geo_ok` generated columns; every spatial query reads them |
| A10 | Seeded sub-zones mixed with real districts | Forecast units are real stations/beats; seeded rows are counted separately (`n` vs `n_real`) and disclosed |

### Decision D1 (wall clock) — its consequence, stated everywhere

The as-of is the wall clock by the owner's decision, so today's forecast stands on seeded
demonstration weeks (**0% real history** in the last 13 weeks; ~350 FIRs a week vs ~7,000 in
the real record). Accuracy is measured on the real record. Both facts are shown on the
map chip, in every chat answer and on the model card. One switch changes it:
`ANTAR_FORECAST_AS_OF=real` (or a date).

### How to run

```bash
python -m app.forecast.run               # forecasts for the configured as-of (~70 s)
python -m app.forecast.run real          # … as of the end of the real record
python -m app.forecast.backtest          # back-test + docs/FORECAST_BACKTEST.md (~5 min)
python -m pytest tests/test_forecast_*.py -q
```

Backend startup does the first two when stale (cube ~35 s, each run ~70 s), then warms Gi\*.

### Open

- **The map UI has not been seen on screen** — it compiles and its endpoints are verified
  live (40–60 ms), but the walkthrough needs a signed-in session.
- Phase 7: demo rehearsal; plan §8 demo lines now carry measured numbers.
- Deploy packaging must drop the derived forecast tables (they rebuild at startup).

---

## Session 2026-09-18 (evening) — map forecasting, Phase 1: data layer

Plan: `docs/MAP_FORECASTING_PLAN.md`. Decisions taken at the start: **D1 as-of = wall
clock** (overridable: `ANTAR_FORECAST_AS_OF=wallclock|real|YYYY-MM-DD`), **D2 station →
beat**, **D3 7 and 28 days**, **D4 FIR count per unit per week by the 16 crime-graph
categories**.

### Coordinate hygiene — flagged, never deleted

Three VIRTUAL generated columns on `FIRs` (`app/forecast/store.py`): `geo_lat`, `geo_lon`,
`geo_ok`. A point counts if it lies in Karnataka's bounding box (11.5–18.5 N, 74.0–78.6 E),
or lands there once latitude and longitude are swapped. Generated columns cost no storage,
need no backfill and re-judge a FIR the moment it is edited or ingested.

| | Real | Seeded |
|---|---|---|
| FIRs with coordinates | 391,054 | 51,329 |
| Usable (`geo_ok = 1`) | **383,325** | 50,220 |
| …of which rescued by swapping lat/lon | 5,492 | 199 |
| Rejected (lat 131, lon 777, zeros, India-bbox corners) | **7,729** | 1,109 |

Every spatial query now reads them: the `crimes` view (so Gi\*, zone centroids and the KDE
inherit clean points), all four map endpoints, the pattern-scan rows and the concurrency
map. Before, `MAX(lat)` on the `crimes` view was **131.43**.

### geo_units and the weekly cube

- `geo_units` — 1,155 stations and 18,513 beats (station + beat name; beat names repeat
  across stations, so "Beat 1" alone is not a place). Centroid = **median** of clean points.
  2,602 beats have no usable point at all.
- `forecast_cube` — FIR counts per unit × category × ISO week from 2018, with `n` (all
  rows) and `n_real` (real record only): **1,027,987 rows, built in 32.5 s** (target
  < 60 s). A beat-level ranking over 13 weeks reads it in 6 ms.
- Rebuilt at startup only when the registry changed (signature = row count + max rowid).
- Both tables are `WITHOUT ROWID`: the conftest guard deletes rows above each table's
  pre-run rowid mark, which would have silently truncated a cube rebuilt mid-run.
- Reconciles exactly with `FIRs` for sampled beats (`tests/test_forecast_data.py`).

### What D1 (wall clock) means for the forecast — measured

History available in the 13 weeks before the as-of date:

| As of | Stations averaging ≥ 1 FIR/week | Beats averaging ≥ 1 FIR/week | FIRs in window |
|---|---|---|---|
| **18 Sep 2026 (wall clock)** | 76 | 27 | 4,228 (seeded) |
| 10 Mar 2024 (real record end) | 983 | 1,731 | 91,870 (real) |

### Open

- Deploy packaging: drop `forecast_cube`, `geo_units`, `forecast_meta`, `forecast_output`,
  `forecast_models` from the data-only artefact like the indexes — all derived, all rebuilt
  at startup (~35 s cube + ~70 s per forecast run).

---

## Session 2026-09-19 — map forecasting, Phase 2: the model

`app/forecast/features.py`, `model.py`, `run.py`. One model per unit type (station,
beat) × 17 categories + all crime × horizon (7, 28 days) = **72 models, fitted in ~70 s
on CPU** (target < 2 min). No statsmodels, no deep learning.

### What was found on the way — and fixed

| Finding | Why it mattered | Fix |
|---|---|---|
| **The registry's volume jumps 5× on 1 Jan 2023** (≈1.4k → ≈7k FIRs a week) — how the extract was sampled, not crime. The seeded band is another ~20× step down. | "Same week last year" read as a fivefold surge; the first model lost to a plain EWMA at 28 days | Every week re-expressed at the **recording level as of the forecast** (step-preserving median of statewide volume, computed only from weeks the forecast could have seen) |
| Holes in the record (Mar–Dec 2024) | A hole read as "zero crime" teaches a model that crime vanishes | Weeks flagged uncovered; no training origin touches one |
| A log-linear volume term **extrapolated**: a seeded beat forecast 8.4 against its own station's 4.5 | Nonsense at exactly the units a demo zooms into | Every input clamped to its training range (0.5–99.5th pct) — deviance equal or better everywhere |
| Beat forecasts summed to **112–120%** of their stations' | Sparse beats each carried a floor from their area | **Top-down reconciliation**: a station's beats sum to its forecast × the share of its FIRs that name a beat; applied before calibration so the bands match what is shown. Now 0 of ~1,000 stations exceeded |

### Design

- **Baseline** = mean of seasonal-naive and EWMA (half-life 4 weeks) — the bar.
- **Model** = Poisson GLM with an offset: the unit's EWMA shrunk toward its share of the
  station/district is the level; the model learns multipliers from level-free log-ratios —
  recent weeks, last year vs usual, neighbouring units (k-NN on the median centroids),
  the wider area, and season (Fourier). Fitted as a rate with weights = exact offset.
- **Bands** = split-conformal on 8 held-out weeks the model never saw, Pearson-normalised
  (NB2 dispersion from residuals) and Mondrian by volume, so a quiet beat and a busy
  station each get honest 80% and 90% ranges. Integer bands, always containing the forecast.
- **The "why"** = the forecast built up from *a usual week here* one reason at a time
  (recent weeks → last year → neighbours → wider area → season); the multipliers
  multiply exactly to the forecast. E.g. North CEN Crime PS: usually 395 FIRs in 28 days,
  recent weeks ×0.56 → forecast 194 (80%: 125–263).
- Categories with too few FIRs (corruption, crimes involving foreigners) fall back to
  the baseline and say so in their model record.

### Held-out results (real record, as of 10 Mar 2024, 8 unseen weeks)

Poisson deviance is the primary score (the proper score for a count forecast; MAE
rewards predicting the median, which for a quiet beat is always zero).

| Unit | Category | Days | Deviance model | Deviance baseline | Better by | MAE model | MAE baseline |
|---|---|---|---|---|---|---|---|
| station | All crime | 7 | 2.136 | 2.770 | 23% | 2.590 | 3.006 |
| station | All crime | 28 | 3.322 | 4.645 | 28% | 6.138 | 7.230 |
| station | Property | 7 | 1.204 | 1.507 | 20% | 0.803 | 0.869 |
| station | Violent | 28 | 1.965 | 2.604 | 25% | 1.785 | 1.999 |
| beat | All crime | 7 | 0.866 | 1.150 | 25% | 0.423 | 0.450 |
| beat | All crime | 28 | 1.583 | 2.300 | 31% | 1.062 | 1.169 |
| beat | Property | 28 | 0.647 | 0.984 | 34% | 0.302 | 0.307 |
| beat | Violent | 28 | 0.753 | 1.225 | 39% | 0.306 | 0.306 |

- **Deviance: the model beats the baseline in every fitted model** — 64 of 64 (real
  record) and 62 of 62 (wall clock).
- **MAE: better or equal in 40 of 64** (real) and 48 of 62 (wall clock); where it loses,
  it is on sparse categories, where the median is zero.
- These are single-origin held-out scores. The rolling back-test (PAI, hit rate,
  interval coverage) is Phase 3.

### Persistence

`forecast_output` (one row per unit × category × horizon: expected, 80/90% bands,
P(at least one), baseline, the six multipliers) and `forecast_models` (parameters,
clamp ranges, held-out scores — the model card's source). Computed at startup for the
configured as-of and the real-record end; reused until the registry or as-of week
changes; older wall-clock weeks pruned.

Tests: `tests/test_forecast_model.py` (15) — a synthetic registry with known rates, a
5× recording step and a data hole, run through the real pipeline: the hole is missing
data, the step is normalised away, the model beats the baseline, bands nest and hold
≥ 80% coverage for the 90% band on 26 unseen weeks, reasons multiply to the forecast,
beats never exceed their station, inputs are clamped, rare categories fall back.

---

## Session 2026-09-19 — map forecasting, Phase 3: the back-test and a model card that cannot lie

`app/forecast/backtest.py`, `report.py`, `card.py`. Regenerate with
`python -m app.forecast.backtest` (~5 min) → `docs/FORECAST_BACKTEST.md` + `forecast_meta`.

**Method.** Real record only. 23 weekly origins whose targets fall between 2 Oct 2023
and the week of 4 Mar 2024; refitted every 4 weeks (6 refits) on data strictly before
each origin — the recording level too. Every ranking is compared with what an analyst
would draw without a model (last 4 weeks, last 52 weeks) and with the ceiling (what
actually happened). A test spies on every fit and fails if one ever trains on its future.

**Headline (next 7 days)**

| | Top 5% caught | Last-4-weeks hotspots | Ceiling | Weeks better | PAI @ 5% land (last 4 wk) |
|---|---|---|---|---|---|
| Beats — all crime | **40.4%** | 38.0% | 56.3% | 22 / 23 | **14.2** (12.8) |
| Beats — property crime | **52.0%** | 41.8% | 99.1% | 23 / 23 | **15.9** (10.9) |
| Stations — all crime | 22.9% | 22.8% | 25.3% | 14 / 23 | 11.8 (11.8) |
| Stations — property crime | 32.8% | 31.5% | 41.1% | 19 / 23 | 13.9 (13.6) |

- The gain is at **beat level** — where officers actually deploy. At station level the
  forecast ranks about as well as last month's counts (stations are stable); its value
  there is the range and the reasons, not the ranking.
- **Ranges hold what they claim** wherever ≥ 0.5 FIRs are expected: 79.8–80.8% inside the
  80% range, 89.8–90.5% inside the 90% range. Below that, an integer range cannot be
  tighter than 0–1, which already contains ~95% of outcomes.
- **Every fitted model beats the baseline on deviance** across the rolling window too.
- Hard cases, reported as they are: station-level narcotics at 28 days ranks worse than
  last-4-weeks hotspots (enforcement-driven — raids cluster where the last raid was).

**Found and fixed by the back-test**

| Finding | Fix |
|---|---|
| PAI flagged different amounts of land per ranking (beats differ in size), so rankings weren't comparable and the "ceiling" could lose | Flag exactly k% of land, last unit pro rata — ranking by true density is then provably the ceiling |
| Several categories forecast 1.2–2.3× too high (narcotics 2.26 at 28 days): the 2023 sampling step was not uniform across categories | Held-out level correction per station model (shrunk, capped ×0.5–2), inherited by beats through reconciliation. Narcotics 2.26 → 1.22, murder 1.55 → 0.96, SC/ST 1.28 → 0.99 — rankings unchanged |

**Beat areas.** The data carries no beat boundaries. Areas are Voronoi estimates: a 1-km
grid, cells within 3 km of a real FIR count as land (209,325 km² vs Karnataka's official
191,791 — the box takes in a border strip), each cell to the nearest centroid. Disclosed on
the card and in the report.

**Model card — generated (closes A5, A6, A8).** `/api/predict/model-card` is now built
from the code's configuration, the fitted models and the latest back-test. It used to
describe "DBSCAN + 30-day velocity" (never ran) and a "CCTNS live replica (updated
nightly)" (not true). Without a back-test it says *accuracy not yet measured*; it
discloses seeded history, fallback categories, reporting bias and the feedback loop. A
test asserts its numbers are the back-test's.

---

## Session 2026-09-19 — map forecasting, Phase 4: the API

`app/forecast/service.py`, `app/api/forecast_api.py`.

| Endpoint | Returns |
|---|---|
| `GET /api/forecast/hotspots?horizon=7\|28&category=&district=&station=&unit=beat\|station&limit=&as_of=` | Ranked units: expected, 80% ("likely") and 90% ("very likely") ranges, P(≥1) in ICD 203 words, usual level, top 3 reasons in words, Gi\* district flag, thin-history flag, class **I**, as-of + real-history share, the back-test accuracy of this kind of forecast |
| `GET /api/forecast/layer` | Every unit in scope, compact, quantile classes — for shading the map |
| `GET /api/forecast/unit/{name}` | 26-week history, the week ahead with its ranges, reasons, top crime heads, other categories, **the unit's own back-test record** |
| `GET /api/forecast/backtest` · `/status` | The back-test (per-unit records on request) · as-of, runs on file, headline |

- **Resolve or refuse:** unknown category, district, station, unit, horizon → 422 with
  the nearest real names; never widened to "everywhere". Everyday words resolve
  ("theft" → property crime).
- **Not ready is not a guess:** an as-of with no computed forecast → 503 while it is
  prepared in the background.
- **One "today" for the whole map (A1).** Under D1 the answer to A1 is not to move the
  anchors to 2024 but to make them agree: the anomaly scan, Gi\*, heat periods, the KDE and
  the forecast all read `app.forecast.asof.current()` (`ANTAR_FORECAST_AS_OF`).
- **`/api/map/predicted` (A2–A4)** is now a view over the forecast: top stations with
  ranges and class I. The fabricated "Surge detected … increase patrols" is gone, and so
  is the stale `monthly_trend` read.
- **Invented band removed (A7):** the scenario endpoint no longer presents a hardcoded
  "3.0–7.0 @ 90%" as a conformal interval when no alert exists — no alert, no band, and
  it says why.
- Gi\* (2.2 s) is cached per as-of and warmed at startup; a request never waits for it.

**Found on the way:** "Mysore" was being silently resolved to *Mysuru Dist* after the
old-name alias step — a different question. When a city is both a City and a Dist police
district, the API now refuses and offers both. Renamed-city aliases added (Mysore,
Bangalore, Belgaum, Gulbarga, Hubli, Shimoga …).

Tests: `tests/test_forecast_api.py` (19) — contract, 28-day totals, filters narrow and
never widen, refusals with the nearest names, not-ready instead of a guess, unit card,
layer classes, reasons in words; HTTP on the real app with **p95 < 300 ms** for hotspots
and **< 300 ms** for a warm unit card; `/api/map/predicted` carries no fabrication.

---

## Session 2026-09-19 — map forecasting, Phase 5: the map

`antar-frontend/components/ForecastPanel.jsx`, `lib/forecast.js`, mounted in `MapScreen.jsx`.

| Piece | What it does |
|---|---|
| **As-of chip** (always visible) | "Forecast as of 19 Sep 2026 · next 7 days", plus the real-history share when it is below 100% |
| **Layers** | Forecast (stations statewide; beats once a district is picked — a GADM district is mapped to its police districts, e.g. Mysuru → Mysuru City + Mysuru Dist), Gi\* clusters, recent FIRs (3 months to the as-of, clean points) |
| **Controls** | 7 / 28 days; category. A crime pill that maps to a wider category says so ("Theft is shown as Property Crimes, which includes it") — never a silent widening |
| **Where next** | Top 10 with the "likely" range; thin-history units labelled, not numbered |
| **Beat card** | Range in ICD 203 words with the Inferred badge; reasons in words; 26 weeks + the week ahead with 80/90% whiskers; what gets reported there; the unit's back-test record; basis and limits |
| **Propose patrol** | Files a HITL `patrol_redeployment` with the forecast, its reasons, track record and accuracy as evidence and a draft justification the officer can edit; a supervising officer approves |
| **Accuracy strip** | The back-test headline for the unit type and category in view → generated model card |

- Markers on one canvas renderer (as SVG, ~1,100 stations made panning sluggish). It has to
  be a creation option: react-leaflet applies `pathOptions` through `setStyle`, where a
  renderer is silently ignored.
- The older Gi\*-ranked "Suggested patrol" labels (no measured basis) are hidden while the
  forecast layer is on.
- Deep link `/map?unit=…&h=28&fc=PROPERTY` opens a unit's card — used by chat.
- **Status:** compiles (SWC); every endpoint it reads verified live. **Not yet walked
  through on screen** (needs a sign-in).

---

## Session 2026-09-19 — map forecasting, Phase 6: forecasts in chat

`app/forecast/chat.py`, intercepted at the top of `query_agent_run`.

**The bug it fixes:** a forecast question ("predict theft next month in Bengaluru City")
was routed to **T3, the monthly trend** — last year's months offered as an answer about
next week. A different question answered confidently (Law 1).

**Now:**

> **Beat 1 (Mysuru City Central PS)** has the highest crime forecast in Mysuru City and
> Mysuru Dist for the next 7 days (14 Sep – 20 Sep 2026): likely 2–6 FIRs, very likely 1–7.
> Forecast as of 2026-09-19; back-tested on the real record, the top 5% of beats caught 40%
> of the next 7 days' FIRs (last-4-weeks hotspots: 38%).
> 1. … each beat with its range and the reason that sets it apart
> *Note: forecasts count reported FIRs, not crime; the record has dates, not times. The map
> proposes; the officer decides.* · *Note: the recent weeks behind this forecast are seeded
> demonstration data (0% real record) …*

- **Class I** bottom line, ranges in ICD 203 words, accuracy as context, limits as **U**.
- **Place:** police district(s), a station, or Karnataka — resolved against the real
  registry (the generic parser expanded "Bengaluru City" into ten seeded sub-zones). A bare
  city is every police district carrying its name, **stated in the answer**. Kannada place
  stems ("ಮೈಸೂರಿನಲ್ಲಿ" → Mysuru) and renamed-city aliases.
- **Refuses** an unknown place ("Atlantis" → nearest real names) and two categories at once
  ("theft and murder") — never widened.
- **Thin history is a gap, not a quiet place:** "forecast for Indiranagar" (a real station
  with no recent FIRs at this as-of) answers class **U**: "Too few FIRs … which is not the
  same as a quiet place."
- **Kannada:** administrative Kannada, FIR and names in English, no tables.
- In the chat stream, the older predict / pattern / alert / geo agents no longer run under
  a forecast answer (their unmeasured "risk" sections could contradict it) unless forced by
  a slash command; the answer carries "Open the forecast on the map" (deep link).
- Beats named only by a number read "Beat 5"; the "pulled toward the station's level"
  reason (true of most beats) is listed after the ones that distinguish a beat.

Tests: `tests/test_forecast_chat.py` (22) — detection (and what it must leave alone),
horizon, categories, places (incl. Kannada and old names), the golden questions through
`query_agent_run`, refusals, thin history as a gap, and the full SSE stream.

---

## Session 2026-09-18 (afternoon) — interface, crime graph, voice

### A. Crime graph told the wrong story

| Problem | Impact | Fix |
|---|---|---|
| "Other" was the largest trace | 40.7% of all FIRs — road accidents (191k), Police Act (58k), Local Act (48k), CrPC (38k) — had no category | Added **Road accidents** and **Police & local acts**; "Other" is now **1.9%** |
| Mislabelled groups | 5,318 FIRs where a public servant was the *victim* shown as "Corruption"; immoral traffic and chain snatching in "Other" | Moved to Violent, Crimes vs women, Property |
| Fake winter surge on "All years" | 2024 stops in March, so summing raw years made Jan–Mar ~30% higher than the rest of the year | "All" now uses **complete years only** (2016–2023, 2025); partial years keep their own chips |
| 2026 plotted the future | ~4,400 FIRs dated Oct–Dec 2026 drawn as if they had happened | Future-dated rows excluded, as everywhere else |
| Year chips showed the wrong year | Chart relabelled instantly but drew the previous year until the fetch returned; stale responses could win | Labels follow the data actually shown; superseded requests dropped; visible loading state |
| Month filter only highlighted a wedge | Legend, centre figure and detail kept full-year numbers | Month now filters every number, including category × month |
| Slow chips | "All" 21.7 s cold, each year 1–3 s | Served from a covering index: All 7.3 s cold, years 0.7–3.3 s, **all pre-warmed at startup** |

> **Demo line:** "Crime in Karnataka peaks March to August — that's measured over eight
> complete years, not an artefact of when the data happens to stop."

The real seasonal shape is now visible: January 70k vs March 82k (it previously read the
other way round).

### B. Full Data Set page showed zeros

The data was always there. Every KPI rendered `0` while a ~17-scan summary ran for 10.7 s,
which reads as an empty database. Now: a loading skeleton (never a fake zero), the summary
is cached and pre-warmed (instant after first load), table paging went **11,230 ms → 5 ms**
(the `rowid` tiebreaker lets SQLite walk the date index), and records sort by true date
(the text month column put September ahead of December). The search box asked for an
ACC-id but never searched accused IDs — it now does, in 3 ms per keystroke.

### C. Chat and expert console

- **Equal split.** The console overlaid the chat; because the thread is rendered at
  `zoom: 0.81`, its reserved space was only 81% of the console width, so ~120 px of the
  conversation ran underneath. Both halves now start at exactly 50%; drag to resize,
  double-click to reset.
- **Answers open at their first line.** The thread used to follow every token to the
  bottom, so a long answer finished with its opening off-screen. The question now pins
  to the top and the answer streams beneath it.
- **Buttons that work.** Row memoisation froze each answer's handlers at first render —
  Regenerate and Export could act on stale state, and Export never appeared if the session
  arrived after the first answer. Fixed with stable handler wrappers; actions moved into
  the card footer, right-aligned and minimal.
- **Design.** One palette — near-black, three greys, brand cyan only for state — sentence
  case in the chat and console. The nav keeps its original pixel font and capitals.
- **Fixed in passing:** a literal `→` in the source cards; "425,000+" in 11 places;
  crime names printed as `Chain_snatching` (which also stopped Kannada answers finding
  ಸರಗಳ್ಳತನ).

### D. Listen to answer

~3 s with no feedback, a second click started a second overlapping request, and gTTS ran
on the event loop — **freezing the whole backend** while it spoke. Now: spinner → stop icon
→ speaker, one player, click to cancel, prefetch on hover, and cached audio (replay
**0.09 s**). Synthesis runs in a thread, so a chat stream keeps flowing during speech.

### E. Absconding accused

"Show me the list of absconding criminals in Indiranagar" lost the word "absconding" and
listed every case in Indiranagar — the silently-dropped filter, in a third dimension.

- **Definition:** a named accused not yet arrested **in a live case** (pending trial, under
  investigation, transferred). "Accused > arrested" alone was wrong — it also matched 60k
  convicted and 29k false cases. About 241k FIRs qualify.
- **Named predicates:** a reviewed SQL fragment selected by key; user text still never
  reaches SQL. The `crimes` view is now defined in code (it existed only inside the
  database file) and exposes `accused` / `arrested`.
- **Read from the question** in English and Kannada (absconding, at large, not yet arrested,
  fugitives, ತಲೆಮರೆಸಿ, ಬಂಧನವಾಗದ …) and applied deterministically whichever router ran. "Most
  wanted suspects" is correctly *not* treated as absconding.
- **Honest empties:** the seeded sub-zones (Indiranagar, Rajajinagar …) carry no accused or
  arrest counts, so the answer now says *"accused and arrest counts aren't recorded for the
  205 FIRs in Indiranagar … this is missing data, not a clean record"* instead of a false
  "none". Self-heal is disabled for these queries — relaxing the filter *is* the silent drop.
- **Refuses** combinations it can't carry (e.g. absconding trend), with examples that work.
- Lists show **"4 of 4 accused not arrested"** per FIR; the breakdown under a count carries
  the same filter, and the unfiltered trend line is suppressed rather than shown beside it.
- Also fixed: "theft cases *where* accused not yet arrested in Mysuru City" was routed to a
  district ranking (the router reads "where" as "rank the districts") and answered about
  Bengaluru.
- Ranking 8.1 s → 1.9 s: a covering index took the total count from 6,815 ms to 434 ms.

> **Demo line:** "Ask for absconding accused in Indiranagar and Antar tells you the arrest
> data isn't there — it won't invent a clean record. Ask for Bengaluru City and it lists
> 66,576 live cases with accused at large, FIR by FIR."

### F. Antar's identity — one standard, enforced in code

**Before:** six identities. The chat prompt had rules but no identity; the multi-agent
summary called Antar "an *elite* AI police intelligence assistant" and asked for 2–3
paragraphs; three mode briefings; `prompt_lib.json`; and the deterministic writer with its
own `[VERIFIED]`/`[COMPUTED]` tags — which is what answers *most* questions, because the LLM
is slow. An identity living only in a system prompt was absent from most answers.

**Now:** `docs/ANTAR_CONSTITUTION.md` (human-readable) and `app/core/antar_identity.py` (the
one that runs). Every answer, from either path, passes through `present()` before a token
is streamed.

| Decided | Choice |
|---|---|
| Voice | Hybrid colleague — facts as record, "I" only for limits and judgments |
| Default depth | Bottom line + context + evidence; Sources and Limits one tap away |
| Judgments | Allowed, labelled, calibrated (ICD 203 words), never about an individual's future |
| Address | No salutation |
| Evidence | One K/D/I/U badge per answer; per-claim in the Expert console |
| Kannada | Administrative Kannada; FIR, BNS/IPC, NDPS, POCSO, names and numbers in English |
| After answering | One next step + 2–3 database-checked follow-ups |

**The four laws**, each enforced in code: never answer a different question · evidence
before opinion · the officer decides · protect the vulnerable (BNS §72, POCSO §23).

**What changed on screen**
- *"**Bengaluru City** has the most kidnapping and abduction cases — **5,950** FIRs, 37% of
  the Karnataka total, followed by Bengaluru Dist (953) and Belagavi Dist (640)."* — the
  "followed by" phrasing requested on day one.
- Context reads as a sentence (*"Steady in Bengaluru City — within ±5%"*), not
  `STABLE` / `DOWNWARD` code words; trends no longer state their direction twice.
- One evidence badge — Known · Derived · Inferred · Unknown — replaces both the text tags
  and the separate "confidence %" bar. The Expert console lists every claim with its class.
- Every LLM prompt that writes to an officer is now built from the constitution.

**Enforced by tests** (`tests/test_antar_identity.py`, 51 tests): real answers across every
kind and both languages must keep the voice, carry a bottom line, declare a class, and leak
no internal tag. The suite caught a real Law 4 bug on its first run — a capitalised
"Victim: Asha Kumari" slipped past the redactor.

> **Demo line:** "Antar has a written constitution — four laws, a voice, an answer template —
> and it isn't a prompt. Every answer passes through it in code, and the build fails if
> Antar breaks its own rules. It's aligned with ICD 203, the intelligence community's
> analytic standard: every claim tells you whether it's a record, a calculation, a
> judgment, or a gap."

### Open

- **Backend restart required** for sections A–F to take effect on :8000.
- The identity work is verified by tests but **not yet seen on screen** — needs a sign-in.
- The district-ranking template has no place filter, so "which station in Mysuru has the
  most theft" can still rank across Karnataka. Guarded for absconding questions; a general
  fix is still open.

---

## Session 2026-09-18

### 1. Scaled the FIR registry to 10 lakh — with real records

**Before:** 425,022 rows, of which 102,578 were literal clones of other rows
(`add_exact_100k.py` duplicated 100k rows with fresh IDs) and 51,329 were seeded.

**What changed:** Appended 574,978 **real** KSP records from the 1.67M-row raw extract
(`FIR_Details_Data.csv`). Deduplicated against what was already loaded using a 14-field
signature, then sampled with an even stride so the additions span every district and year
rather than the head of the file. Existing rows were never modified — insert-only.

**Impact**

| | Before | After |
|---|---|---|
| FIRs | 425,022 | **1,000,000** |
| Years covered | 2016–2026 (2023-heavy) | 2016–2026 (evenly spread) |
| Districts / stations | 40 / 1,056 | **56 / 1,155** |
| Rows with coordinates | 265,190 | **442,383** |

> **Demo line:** "One million FIRs from 1,100+ stations, 2016–2026. District ranking in
> 127 ms, a full monthly trend across the million in 331 ms — on CPU, no GPU."

There are still **965,530 unused real rows** in the source extract, so scaling further is
a one-constant change, not a rewrite.

---

### 2. Fixed the deepest correctness bug: silently dropped filters

This is the most important change in the session and the strongest thing to talk about.

**The failure:** when the backend could not resolve a filter, it *dropped it silently* and
answered the unfiltered question — with real numbers, formatted confidently.

```
"which districts have the most kidnapping & abduction"
   '&' matched nothing  →  filter vanished  →  ranked ALL crime in Karnataka

"how many thefts yesterday"
   'yesterday' resolved to (None, None)  →  date filter vanished  →  all-time count
```

**Three root causes, all fixed:**

1. **The crime vocabulary was hand-written and 23% short of the data.** It listed 33 names;
   the registry holds 142 distinct `CrimeGroup_Name` values. 102 groups — **232,674 FIRs**
   — could not be named at all. Worse, `BURGLARY` existed in the vocabulary but matched
   only 837 seeded rows, while the real burglaries are filed under `BURGLARY - DAY` and
   `BURGLARY - NIGHT`. The vocabulary is now **read from the registry at startup**, so it
   cannot drift from the data again, and everyday words expand to every official name they
   cover.

2. **No day-level time words.** `yesterday`, `today`, `this week`, `last 7/30 days` and
   `last N days/weeks/months/years` now resolve — in English and Kannada (`ನಿನ್ನೆ`, `ಇಂದು`).

3. **No refusal path.** Added a **resolve-or-refuse contract**: a filter the officer named
   either resolves, or Antar says it could not resolve it and offers the nearest real
   options. It never widens the query instead.

**Impact**

| Question | Before | After |
|---|---|---|
| kidnapping **&** abduction | ranked *all* crime | 16,114 kidnapping FIRs |
| burglary | 837 rows (26,442 real ones invisible) | ~27,300 |
| narcotics | 420 rows | 19,953 |
| riots / attempt to murder / suicide / forgery | filter dropped → all-crime answer | correctly filtered |
| thefts yesterday | 104,419 (all time) | 10 |
| Vocabulary coverage | 33 names | **121 concepts over all 142 groups** |

> **Demo line:** "Our zero-hallucination guarantee isn't a prompt. The model never writes
> SQL and never picks a number. And when the system can't resolve what you asked for, it
> refuses — because answering without that filter would answer a different question."

---

### 3. Trend lines now describe the real record

**The problem:** every row dated 2025–2026 is seeded demo data (~1,500/month). The real
KSP extract ends **2024-03-10**. Trend windows measured from the wall clock landed entirely
inside the seeded band, so "theft is up 45%" described ~1,500 demo rows a month while
ignoring real months of 30,000.

**What changed:** trends now ask for the real series first and only fall back to the full
registry when a filter has no real rows at all — which preserves the seeded demo sub-zones
(Rajajinagar, Whitefield, Jayanagar are synthetic-only by design). The wall-clock anchor is
unchanged everywhere else.

Also fixed: the last month of the real extract is **truncated** (9,562 FIRs vs ~31,000),
and counting it as a complete month made every trend read as a steep fall that was purely
the data running out.

**Impact**

| Trend | Before | After |
|---|---|---|
| Theft, Karnataka | "up 45%" (Jun–Aug **2026**, seeded) | **down 9%** (Dec 2023–Feb 2024 vs Sep–Nov 2023, real) |
| All crime, Karnataka | seeded band | **stable, −4%** on real months |
| Truncation artefact | −26% / −32% false falls | removed; short month labelled and excluded |
| Rajajinagar (demo narrative) | up 48% | **up 48% — preserved** |

---

### 4. Query performance: 57 s worst case → 4.8 s

Profiling showed **SQLite was never the bottleneck** — 58.8 s of a 61 s question was spent
waiting on the network, 1.15 s in the database.

**Network (the real problem)**
- A cold QuickML call takes **75 s** (OAuth mint + endpoint cold start); warm calls are
  4–6 s and still sometimes exceed 20 s.
- `retries=3` over a 90 s HTTP timeout meant one question could hang for minutes with no
  ceiling. Added a hard wall-clock budget across all attempts (20 s, `QUICKML_BUDGET_S`),
  an 8 s cap on the routing call (which had **none**), and 6 s on intent enrichment.
- Startup warm-up gets a deliberate 90 s budget, so the **server** pays the cold start
  instead of the first officer question.

**SQL — four rewrites, every one proven result-identical (zero mismatches across 22
template/parameter combinations and 10 LIKE prefixes)**

| Rewrite | Why it was slow | Gain |
|---|---|---|
| `COUNT(crime_id)` → `COUNT(*)` | counting a column forces a table lookup per row to test for NULL | 777 → 99 ms |
| dropped no-op `UPPER()` on ISO dates | a column wrapped in a function cannot use its index | 265 → 61 ms |
| `LIKE 'IPC%'` → range predicate | SQLite only optimises *literal* patterns; ours was `UPPER('IPC%')`, a function call | 5,839 → 158 ms |
| expression indexes matching `TRIM(UPPER(col))` | filter expression had no matching index | see below |

Each index pairs the filter column with the column it is normally grouped by, so grouping
is index-ordered instead of building a temp B-tree.

**Impact (17 representative questions, cold cache)**

| | Before | After |
|---|---|---|
| Mean | 9,405 ms | **656 ms** |
| Worst | 56,998 ms | **4,764 ms** |
| Total | 131,666 ms | **11,154 ms** |
| District ranking | 798 ms | 94 ms |
| Crime mix | 3,210 ms | 117 ms |
| IPC vs SLL split | 22,882 ms | ~500 ms |

**Also fixed a production-only bug:** `ensure_indexes()` was only reachable from
`load_world()`, never from the query path — so a freshly staged database on Catalyst could
have served every question with full scans of a million rows, and none of this work would
have applied in production. It now runs from `run_local()`. Verified: a database with
indexes missing rebuilt them on the first query (11.7 s), then queried in 0.07 s.

---

### 5. Routing bug — a confident answer about the wrong district

`"most crimes in Bengaluru City"` hit a `CLARIFY` branch (the superlative rule was gated on
"no place named"), which cascaded into `self_heal`, burned ~12 s of LLM calls, and answered
about **a different district**. `"which crime is most common in Mysuru City"` returned a
Bengaluru answer.

Both now route to the crime-mix template with the named zone. `CLARIFY` still fires for
genuinely vague questions with no place to pin down — both golden-suite expectations kept.

| Question | Before | After |
|---|---|---|
| most crimes in Bengaluru City | 13,019 ms, wrong | **175 ms**, correct |
| which crime is most common in Mysuru City | 12,136 ms, **wrong city** | **79 ms**, correct |

---

### 6. Deployment artefact: 1.27 GB → 84 MB

The database is 59% indexes (752 MB of 1,272 MB), and indexes are pure derived data.

| Option | Package | `/tmp` needed | Cold start |
|---|---|---|---|
| Full DB, gzip | 187 MB | 1,272 MB | 5 s |
| **Data only, gzip (chosen)** | **84 MB** | 1,193 MB | 2 s + ~50 s index rebuild |
| Data only, xz | 58 MB | 1,193 MB | 5 s + ~50 s rebuild |

Data-only was chosen because it also **keeps the index layout in sync with the code** — a
pre-indexed artefact is a snapshot that goes stale the next time a query is tuned. The
build refuses to publish unless `PRAGMA integrity_check` passes and the row count matches,
then decompresses the result the way `ensure_db_staged()` will and re-checks.

`main.db.gz` also carried the **stale 425k dataset** and would have deployed old data.

---

### 7. The test suite was writing into the demo database

`conftest.py` forced offline mode but never isolated the database, so tests ran against the
real `main.db`. `test_ingestion_csv_mapping` genuinely ingests its sample row, so **every
run added a FIR to Karnataka's crime registry** — district "Central", station "Unknown", a
Robbery on 2023-10-15. 26 had accumulated.

Fixed with a session-scoped guard that marks every table's high-water rowid before the run
and deletes anything above those marks afterwards — rows that existed before are never
touched, and it warns loudly if the FIR count *drops*. The 26 artefacts were removed and
the registry topped back up to exactly 1,000,000 with real rows.

District count went 57 → **56**: "Central" was never a real KSP district.

---

### 8. Answer quality fixes

- **Five `NameError`s in `answer_writer.py`** were killing every ranked answer in English
  and every Kannada trend line — the good writer existed and had simply never executed.
  The answers fell back to a bullet dump that never stated the answer.
  Now: *"**Bengaluru City** has the most kidnapping and abduction cases — **5,950** FIRs,
  37% of the Karnataka total."*
- Kannada scope labels (`ನಿನ್ನೆ`, `ಇಂದು`) instead of English leaking into Kannada answers.
- `(null)` no longer prints as a time scope.
- "Mar 2024 is still in progress" → "The record for Mar 2024 is incomplete" (it is 2026;
  the month is not running, the data stops there).

---

## Open risks

| Risk | Why it matters | Status |
|---|---|---|
| **Catalyst `/tmp` capacity** | The container expands to 519 MB and builds indexes to ~1.2 GB. If AppSail gives less, the deployed app fails at staging — and the live demo runs off the deployed link. | **Unverified — needs a real deploy.** Fallback: smaller deployed dataset, laptop keeps the full million. |
| **QuickML latency** | 75 s cold, 4–6 s warm, occasionally >20 s. | Bounded by timeouts; deterministic path always answers. Warm the deployment before the demo. |
| **MO / behavioural profiling** | `MO_Details` is populated on 651 of 1,000,000 rows. | Thin evidence base — avoid over-claiming. |
| **Relationship layer** | `crime_suspects`, `financial_links`, `relationships` are partly seeded; the raw KSP extract has no accused-identity column. | Known. Not labelled in the UI by request. |
| **Trend horizon** | Real record ends 2024-03; 2025–26 is seeded. | Trends now use real data; seeded band only serves demo sub-zones. |
| **Forecast on seeded history (D1)** | With the wall-clock as-of, today's forecast stands on ~350 seeded FIRs a week; only 76 stations average ≥ 1 FIR a week. | Disclosed on the chip, in chat and on the card; accuracy measured on the real record. `ANTAR_FORECAST_AS_OF=real` switches it. |
| **Registry sampling steps** | The real extract jumps 5× on 2023-01-02 and the rate differs by category. | Recording-level normalisation + held-out level correction; calibration 0.96–1.22 across categories after it. |
| **100,000 duplicated FIRs (found 2026-10-14)** | Rows with ids `SYN-…` are marked real (`is_synthetic_row = 0`) and each is an exact copy (case number, date, crime type, station) of a real `C…` row: 85,264 dated 2023, 14,736 dated Jan-Mar 2024. Every 2023 count is inflated by about 22% (2023 murders show 2,029; 331 are copies, 1,698 unique), the forecast and back-test were fitted and graded on this period, and the registry holds about 9 lakh unique FIRs, not 10. Likely part of the 5× step on 2023-01-02. | **Left as is by the owner's decision (2026-10-14), labelled.** Not quoted at the demo. Fix when wanted: flag the copies, leave them out of the `crimes` view, refit and re-run the back-test. Find them with `SELECT … FROM FIRs WHERE fir_id LIKE 'SYN-%' AND is_synthetic_row = 0`. |
| **2016-2022 is a partial extract (found 2026-10-16)** | Each of those years holds 58k-84k rows against an official 175k-195k (2022: 70,451 of 195,170), so counts run about 2.5 times low: 2022 murders show 517 against roughly 1,300-1,400 recorded statewide. Shares, rankings and rates are representative. `year_intel` calls it a 1:100 sample; it is closer to one in three. | Suggestions and the documented question bank ask about 2022 and rank, compare or rate; none headlines a raw count. A yearly total quoted on screen comes from `year_intel` (the official figure). |
| **Beat areas** | No beat boundaries in the data. | Voronoi estimates (land mask 209,325 km² vs 191,791 official); PAI labelled approximate. |
| **Feedback loop** | Patrolling flagged beats records more FIRs there. | Stated on the model card and every beat card; recommend rotating patrols. |
| **Map UI unseen** | Built and compiled; not yet walked through on screen. | Needs a signed-in session. |

---

## How to verify any claim here

```bash
python -m pytest -q                 # 1,170 passed, 2 skipped
python -m app.forecast.backtest     # regenerates every forecast accuracy number
```

Benchmarks in this log come from cold-cache runs over the 17-question set; SQL equivalence
was checked by executing the old and new forms side by side and comparing rows exactly.

## 2026-09-25: YC gstack Deployment Review & Intelligent Data Fix
* **gstack Architecture Validation:** Applied the Garry Tan / YC gstack review methodology to the backend. Validated that main.db successfully hosts exactly 1,000,000 FIR records and the codebase passes security, concurrency, and SQL safety checks.
* **Intelligent Data Missing File Fix:** Located the missing 1.1MB curated intelligent.db graph in the E:\ backup drive and copied it to the backend root (D:\Project). Previously, a 0-byte ghost file in the data/ folder was causing silent failures and fallback queries. 
* **DB Pointer Alignment:** Fixed pp/api/docs_questions.py which was misaligned and pointing to data/intelligent.db. Updated it to use _BACKEND_ROOT, aligning with the deployment structure in dataset.py.

## In-Context RLHF & 21-Second Delay Fix - 2026-10-07

* **RLHF Loop (USP)**: Built a dynamic few-shot learning system into pp/core/antar_identity.py. Highly rated answers ('up' ratings) from the feedback store (data_feedback.jsonl) are automatically injected into the LLM's system prompt. This acts as a reinforcement learning loop, allowing Antar to continuously improve its response quality based on human officer feedback, without requiring a manual LLM retraining step.
* **Suggest Questions 21s Delay Fix**: 
  * Bypassed the 8.0s LLM router timeout in pp/api/chat_stream.py for predictive queries that the deterministic router already identifies.
  * Refactored pp/agents/graph.py orecast_node to run its four sub-agents (geo, predict, pattern, lert_suggest) concurrently via syncio.gather.
  * Optimized pp/agents/followup_agent.py to use limit=1 to prevent full table scans when evaluating suggested follow-up questions.
  * Reduced overall response latency for suggested forecasting questions from ~21s to ~7s.


## Identity and evolution as USPs, Brain console polish - 2026-10-11

* **Two USPs added** to `antar_identity.USPS` (now 10): *One identity on every answer* and *Its growth is on the record*. The constitution carries a version in code (`VERSION` 1.0, `SINCE` 2026-09-18).
* **Evolution record**: `GET /api/console/evolution` and the terminal command `evolution`. Six lines, each counted from the store that keeps it: identity, officer ratings, graded forecast weeks, hypothesis decisions, audit ledger, recall memory. A store that cannot be read says "not available"; it never shows a zero.
* **Reasoning trail doubled every turn on `/api/chat`** - fixed in `supervisor.py`, trace capped at 500 steps in `audit_store.py`. Eight runaway rows held 2.66 GB; `main.db` is back to 1.4 GB.
* **Brain corpus was not being found** (`brain_vectors.db` sat in `data/`, the live database in the root). Copied beside `main.db` and packed: 100,000 FIRs indexed again.
* **Brain agents** are page-mascot robot characters, fly two rings round the brain during a Fast Run, and the Fast Run results window lists every agent with its findings in full.
* **Known damage, not yet repaired**: running the test suite against the live database on 2026-10-11 cleared the audit log (`tests/test_audit*.py` and `test_governance.py` call `audit_store.clear()`), and a later run removed live audit rows through the `conftest.py` clean-up, so `/api/audit/integrity` reports the chain broken at entry 499. Do not run the suite while the backend is serving the demo database until the audit tests use their own file.

## Real sign-in, and the API closed to anonymous callers - 2026-10-12

* **Measured first**: with no identity at all, 75 of 79 parameter-free GET routes answered - FIR records, the suspect registry, the officer list, observability sessions - and `X-Role: Admin` opened the audit log. The login page accepted any password.
* **Sign-in**: `POST /api/auth/login` checks a salted scrypt hash (`app/core/accounts.py`) and issues the signed token the gateway already knew how to verify. Same answer for a wrong password and an unknown id; five failures lock the id for five minutes. Accounts are created with `scripts/set_password.py`; in a container they come from `ANTAR_USERS`.
* **Frontend**: the login page signs in for real, and `lib/auth.js` attaches the token to every backend request (96 call sites used a bare `fetch`). A 401 ends the session and returns the officer to sign-in. Reports are fetched with the token and opened as a page, since a new tab cannot carry one.
* **Gateway**: `/trace`, `/trust` and `/report/*` are now behind it (they sit outside `/api`), and its 401 carries the CORS origin so a browser can tell a refusal from an outage.
* **After**: 79 of 80 routes refuse without a token; only `/api/health` answers, and it no longer prints a server path.
* **Tests no longer touch the live audit ledger**: the suite's audit store points at a throwaway file, and `audit_log` / `agent_reasoning_logs` are excluded from the main.db clean-up.
* **Build**: `.dockerignore` and `.appignore` now exclude the second database copy in `data/` (1.5 GB), `gstack/` (207 MB), the one-off patch scripts and the accounts file.
* **Still open**: the live audit chain is broken at entry 499 from the 2026-10-11 test runs and has not been reset; Docker images run as root; `Dockerfile.onnx` is still unbuilt.


## Agents across the product, Brain terminal, responsive pass - 2026-10-12

* **Agents in chat**: the fifteen agents sit in a line above the chat box ("Antar Agents:"). Picking one asks the first question through that agent's mode (`/think`, `/connect`, `/anticipate`) and `/docs?agent=Name` shows that agent alone. The thought process shows the agents that ran.
* **Agents in the Expert workspace**: an Agents block with targets, starting points, run-all and follow-ups; the title row lists only the agents used for that answer and jumps to the block.
* **Agents answer for `ACC-KA` ids** that are on FIRs but have no profile (FIR-only path in `brain_console.py`).
* **Daily learnings**: `GET /api/console/learnings` (today's FIR counts, top district, mover, alerts, ratings; 60 s cache). Agents pass these to each other on the Brain screen and a click opens the detail in the terminal.
* **Brain terminal**: suggestions that fit the moment, `help <command>`, `history`, Tab completion, `/think /connect /anticipate`, `use <agent>` / `exit`. Opening it calls the agents into line. It always opens in the same place.
* **Terminal login**: the Terminal button asks for a login (user `root`). It is checked in the browser and is a demo step, not a control: what a command may read is still decided by the server from the officer's sign-in. Clicking an agent skips it and opens that agent's own session (`antar@brain@geo`), where a typed line is the agent's target.
* **Map**: summary tab open by default and written out, geo-intel cached, thin loading line, scrolling Geo Intel and Prediction lines restored.
* **Speed**: chat answers waited 16-19 s on LLM query expansion inside `semantic_recall`; it is now opt-in (`expand_with_llm`). One curtain covers sign-in to first screen; screen switches wait 200 ms instead of 600.
* **Responsive**: bottom tab bar at 820 px and below; Predict, Brain and Chat laid out for 375 and 768 px. Emojis removed from the UI.
* **Demo sign-in**: access links fill the password from `antar-frontend/.env.local` (git-ignored; must not ship in a public build).
* **Needs a backend restart to load**: learnings, `/api/console/targets`, `ACC-KA` support, the new console commands and the recall speed fix.
* **Still open**: audit chain broken at entry 499 (not reset); Docker images run as root; `Dockerfile.onnx` unbuilt; no git remote, so the history exists only on this machine.

## Predict: an engine an officer can check, and events measured from the record - 2026-10-12

* **Agents removed from the Predict page only.** No mascots; the reasoning graph names its steps ("Forecast model", "Weighing") instead of the code that runs them. The decorative "Forecast Engine v2.4" pod (a hand-drawn curve and chips, not data) is gone.
* **Engine panel** (`GET /api/predict/engine`): confidence as High / Moderate / Limited with its reasons, from a stated rule over three things - the back-test of the weekly forecast model (80% ranges held 80.1% over 23 graded weeks of the real register), how current the records are (the latest weeks in this build are demonstration records, which caps it at Moderate), and whether the event calendar was reached.
* **Event calendar from the internet** (`app/services/events.py`): festival DATES are read from a public iCalendar feed (`ANTAR_EVENT_FEED_URL`, India public holidays), checked daily, cached, with a built-in table as fallback. Only the date of a festival on a fixed list is taken; no text from the feed is stored or shown. Setting the URL to empty makes no outbound call.
* **Event effects are measured, not assumed.** For each past occurrence inside the real FIR record (2016-2023), cases registered in the event's window are compared with the 28 days either side, per district and crime group. The old file had a typed list of "risk types" per festival and the screen once showed "Dasara +34%". Measured: Mysuru registers 14% FEWER FIRs during Dasara (lower in 8 of 8 years), fatal road accidents run 36% higher (5 of 8 years, reported as less certain). Statewide the same method finds Karnataka Police Act cases +147% at Deepavali and +193% at Ugadi (8 of 8 years), affray +59% at Ganesha, robbery +42% at Sankranti, fatal accidents +28% at New Year.
* **A clear effect** needs: at least 4 past years, at least 10 expected cases, a change beyond week-to-week noise, and the same direction in most years. Scanning many crime groups uses a stricter bar. Only a clear effect produces a scenario range, shown beside the baseline range and marked Inferred.
* **Cards** carry `basis` (cases on record in 52 weeks), `confidence_level` with reasons, `events` and `scenario`. The numeric `confidence` is unchanged but no longer shown as "80% confident": it is a rule-table constant, not a measured probability.
* **No future date leaves the backend**: an event is "under way, 8 days left", never a calendar date (`date_guard`).
* `tests/test_events.py` rewritten (10 tests, no database, no network); run with `pytest --noconftest tests/test_events.py` while the backend is serving.
* **Still open**: the Hypotheses Engine panel on this page is canned text on a timer and should be wired to the real hypothesis API or removed.

## Chat: what a question names is applied, or said first - 2026-10-13

* **Trigger**: "IPC/BNS vs SLL split for 2028?" was answered with the split for every year. A year the register does not hold is now refused up front (`query_agent.outside_record`), with the same question offered for the nearest years it can answer.
* **Sweep**: 48 questions that each name a constraint were run through the query agent; about half had answered a different question. Fixed in three groups:
  * **Periods** (`app/agents/timespan.py`): day, month, run of months, quarter, half-year, run of years, since / before / after, N days-weeks-months-years back, a bare month (the latest one), a festival of a year ("during Dasara 2023", from the event calendar). The router used to read a four-digit year and nothing else.
  * **Dropped constraints** (`query_agent.unapplied`): a filter the chosen template has no room for, or something the register does not record (time of day, weapon, property value, day of week, age or gender of those involved, a count threshold). The answer's lead now opens with "This answers a broader question than you asked: ..." and the fidelity score counts each one.
  * **Added or widened constraints**: "vehicle" no longer adds vehicle theft to motor accidents; "women were arrested" no longer adds crimes against women; "under investigation" is that status only; a self-healed answer is headed by what was actually fetched, not by the size of the register.
* **Refused before any template runs**: a month, quarter or day that has not happened; "next year" / "tomorrow"; a place in another state.
* **Also**: T11 takes `zones` (stations ranked inside a district); "suspects with more than N cases" routes to the repeat-offender list; more statuses resolve (acquitted, pending trial, false case, compounded, abated, untraced); a status filter is named in the headline; "burglary at night" uses the register's own night-burglary group.
* **Evidence strip**: showed the number of groups returned ("400 records") under a headline about 996,000 FIRs; it now shows the count over the template's own filters.
* **Checked**: the 35 golden questions give identical answers before and after; 297 tests pass across the 16 test files covering this code (`tests/test_timespan.py` and `tests/test_outside_record.py` are new).
* **Left as it was**: `_date_range` still drops a future window that has no period keyword. That guard is for dates a model invents; an officer's future period is refused before it gets there.

## Predict page reordered for the officer reading it - 2026-10-13

* **Order**: forecast for the next 7 days, active alerts and the week in brief are the first row; the explanation of the selected area sits directly under them; then the figures, engine confidence, "what the forecast is built on" (known data, monthly history, internet calendar), events ahead, hypotheses.
* **Engine confidence** is one line (level, meaning, number of reasons) that opens on click; the rule that sets the level is shown beside its reasons.
* **Added**: filters and a search on the forecast list; the three stations to watch in the selected district (from `/api/forecast/hotspots`, hidden for areas that are not police districts); "Copy for a briefing note"; 90% range coverage, forecast-against-recorded total and where the real register ends.
* Nothing was removed from the page.

## Brain: saved findings, agents that look around, a fuller focus panel - 2026-10-13

* **Saved findings** (`app/services/saved_findings.py`, `GET/POST/DELETE /api/console/saved`): Save on a Brain notice keeps the whole finding in the database under the signed-in officer, for a later investigation. It is never written to the officer's disk: a finding names accused ids and FIR details, and a file in a downloads folder is outside sign-in, roles and the audit ledger. The officer comes from the token, not the request body; one officer cannot list or remove another's. 200 per officer, oldest first out; saving the same finding twice keeps one copy.
* **Saved** pill beside Terminal lists them, newest first; each reopens in the notice window, where it can be removed.
* **Notice window**: clicking a notice opens the whole finding (bottom line, scope, evidence, limits, method, suggested next) with Save, Copy, Open in terminal and Close.
* **Agents on the Brain screen** look around on their own instead of following the pointer.
* **Focus panel**: FIRs by year, where registered, every named accused with FIR counts, identifiers shared by two or more FIRs, and the FIR list grouped with counts.
* Needs a backend restart for the saved-findings endpoints; until then the page says so.

## FIR data overview: numbers in one readable face - 2026-10-13

* **Cause of the mixed fonts**: the four local `jetbrains-mono-*.woff2` files were one identical 11 KB subset with no Latin letters or digits, declared as weights 400 to 700. Bold monospace numbers therefore fell back to Times. The files and their `@font-face` rules are removed; JetBrains Mono now loads all four weights from the Google Fonts link in `app/layout.jsx` (offline it falls back to the system monospace, not a serif).
* **Overview restyle** (`components/DataOverview.jsx`, `.ov-*` in `globals.css`): figures in Inter with tabular digits, labels in sentence case ("Total FIRs", "Charge-sheeted"), a labelled year and FIR range row, larger stage and table text, chart axes in Inter. No figure or panel was removed.

## Map: agents on click, a Research agent, a plainer View summary - 2026-10-13

* **Agents** (`components/MapAgents.jsx`): no box on the map; one button opens the list, and each agent says what it does. Drag one onto a district to run it for the selected date.
* **Research** added to the map agents: on a district it lists the accused named most often there (`brain_console._research_place`). Needs a backend restart to load.
* **View summary** (`components/MapScreen.jsx`): one figure first, plain rows, a short "In short" line.

## Map: each figure shown once - 2026-10-13

* **Left card** holds the day's figures and nothing else: the count with its date, the change against the day before, the last 30 days. Gone from it: the second copy of the count ("generated FIRs"), the hotspot line with its z value (the summary and the map already show it), and the cursor coordinates marked "LIVE" (they also re-rendered the whole screen on every mouse move).
* **View summary** no longer repeats the count, the change, the 30-day total or a ranking of areas; it starts with how to read the view and keeps hotspots, what is above its usual level, the next 7 days and patrol.
* **District bars** are titled "Districts with most cases, this day". The calendar's "map updated" line is removed; the selected day is already marked.

## Map: district card in plain figures; Geo intel rebuilt on what the record supports - 2026-10-13

* **District card**: one quiet surface, no glow, gradient bar, icon or red and amber figures. Day, 7 and 30 day counts; the 30 days before with the change in words; share of the state; activity level with the rule that sets it written out; all FIRs on record; FIRs with no accused charge-sheeted yet and their share (this was labelled "Unsolved"; the count is `Accused_Count = 0 OR Accused_ChargeSheeted_Count = 0`); the three most recorded crime types. The patrol button says nothing is sent until a supervising officer approves.
* **Geo intel window** (`components/GeoIntel.jsx`) is now "Links between districts": a link is the same accused id named in FIRs in two districts, and the page says it does not show travel, a route or a gang. Each link opens to its counts, the accused ids (names marked as stand-in names), and how many are also named in a third district. Adds the districts on the most links, the lines the summary scrolls, and a "Words used here" list.
* **Removed because the record does not support them**: "Statutory Section 91" and the "Statutory Certification" line; "syndicate", "transit route", "Ring leader"; the canned "Inter-district ANPR Checkpoint" recommendation; and the "UNSUB operating zones" section. Those zones were the first 4,000 located FIRs grouped by district (hence a 457 km "radius"), not unknown offenders, and the page fell back to two invented syndicates when the server returned none.
* **Scrolling Geo Intel lines** rewritten in plain words (no z-scores, no "predictive modeling suggests").
* A most-recent-FIR date later than today is not shown (seeded demo rows).

## Trace & Telemetry: plain labels, colour only as a signal - 2026-10-13

* `components/TrustDashboard.jsx` moved from inline styles to `.tlm-*` rules in `globals.css`. No data, filter or request changed.
* **Figures** in sentence case and plain words: "Questions recorded", "Answered with no flag", "Serious flags", "Average answer time" (with "95% answered within"), "FIRs cited", "Judge score", "How answers were written".
* **Question rows**: one readable line of facts (time, template, rows, cited, time taken, how it was written) instead of eight monospace chips. Only flags and the judge state are tags. The left stripe is red for a serious flag or an error and is otherwise absent; it used to be amber on every row because F6 fires whenever the language model is down.
* **Opened record**: section headings in plain words ("Query that ran", "FIR rows it read", "Agents that worked on it", "Flags on this answer"), larger text, `**bold**` in the stored answer shown as bold.
* **Explainer** renamed "What this page records, and why" and now lists what each flag F1 to F7 means.
* The extra gap above the title is gone; panels use a slim scrollbar; sessions and questions stack on a phone (they used to stay side by side).

## LLM security pass: prompt injection and the surfaces around the model - 2026-10-13

Read every place that calls the model or shows what it wrote. The core layer (`app/core/rag_security.py`: fence, canary, ingestion screen) was already in place; these were the gaps. Full table in `docs/SECURITY.md` §3.6; `tests/test_llm_security.py` has a hostile input for each (64 tests).

* **Map view summary**: the browser's request body went into the prompt as written. Now an allow-list of the values the page can send, fenced, reply screened, rate-limited.
* **Trace API**: any signed-in officer could read every officer's questions and the system prompt with its leak marker. Now Inspector+; the prompt text is Admin only; the marker is never stored or returned.
* **Leak check**: the marker is recognised when spaced out or re-cased; a replayed prompt gets the live marker.
* **Judge**: inputs fenced, scores kept only as four numbers between 0 and 1.
* **Vision**: the image must be inline image data (it was passed on as a URL the provider would fetch); the extraction is reduced to the fields asked for.
* **Open-web search**: no longer invents a claim when the search fails or finds nothing; snippets screened; links http(s) only; no named subject, no search; Inspector+.
* **Also**: Kannada and Hindi override patterns; earlier turns fenced in template selection; query rewrites validated; Predict briefing facts fenced; chat question capped at 4,000 characters; a `javascript:` link from the open web is not made clickable.
* Needs a backend restart to take effect.

## USP plan: Secure AI and Predict - 2026-10-14

* `docs/USP01_02.md`: the two demo-day USPs, what the build already proves for each, the gaps against five papers the owner supplied (SMCP, a 50-study review of RAG security, a 142-study survey of crime prediction and explainability, Parallax, the AI Agent Index), work items S1-S10 and P1-P9 with files, steps and a "done when" test, a three-minute demo for each USP, claims to avoid, and a brief for handing an item to any coding model.
* No code changed. The P0 list (about 7 working days) starts with the Hypotheses Engine on the Predict page, which still shows prepared text.

## Predict: hypotheses are computed, not prepared (USP plan P1) - 2026-10-14

* The Hypotheses panel showed two prepared paragraphs ("HYP-001-COLD", a "Highway Robbery Syndicate") whatever district was selected. They are gone.
* `GET /api/predict/hypotheses?zone=` (`pattern_predict.hypotheses_for`): the research agent proposes links between accused in the district from shared signals; the advocate agent checks each against its base rate with no model. The panel shows what they share, the verdict in words, the chance the link is real after the check, and what would settle it. On the real data most proposals do not stand up (Raichur: 22.2 expected false matches across 59,125 compared pairs), and the panel says so.
* A district with no proposal says "No link ... scores high enough to propose." Needs a backend restart.

## Any language model, or none (USP plan S8) - 2026-10-14

* `app/services/llm.py`: the provider is a setting. `ANTAR_LLM_PROVIDER` = `quickml` (default when its credentials are set), `openai_compatible` (any `/chat/completions` server, hosted or local such as Ollama at `http://localhost:11434/v1`), or `none`. An unknown value or a missing address is treated as `none`.
* Every provider goes through the one choke point (`quickml_generate`): policy and canary added, PII redacted, reply checked, call traced, time budget. `tests/test_llm_provider.py` proves a local model gets the hardened prompt and that a leaked marker from it is blocked.
* Availability checks in chat, streaming chat, translate and start-up now ask `llm.available()` instead of looking for QuickML credentials. Scans go to the vision model only under `quickml`.
* `.env.example` documents the four settings. Needs a backend restart.

## Predict: "Why this forecast" (USP plan P2) - 2026-10-14

* `app/forecast/service.py::why`: every forecast taken apart exactly: a usual week here, times each of the six reasons, equals the forecast (checked on 400 stored station forecasts: worst gap 0.04%). Each reason carries the forecast without it. A forecast that does not reconcile is flagged.
* Predict page, "Stations to watch": each station opens to the arithmetic, the counterfactual for the largest reason, the last 12 weeks with the week ahead drawn as a range, and how the forecast did in the back-test (`components/ForecastWhy.jsx`). No language model is involved.
* Works against the running server from the reasons it already sends; the full six-reason breakdown needs a restart.

## Predict: shift plan (USP plan P4) - 2026-10-14

* `GET /api/forecast/shift-plan?station=` (`app/services/shift_plan.py`): one station's next shift on a page. Beats to cover first with their ranges and main reason; the kinds of case expected; which days of the week ran busier in the past year, named only when at least 60 FIRs exist and a day runs 25% above the average day; FIRs from the past year under investigation with no accused charge-sheeted, newest first; any event whose effect the record has measured for that district.
* No language model writes any of it: fixed sentences filled with the counts (a test fails if a model is called). The register holds an FIR's date, not its hour, so the plan names days and never a time; the page says so.
* Predict page: each station under "Stations to watch" has a "Shift plan" button. The window has Copy for a briefing note, Print, and Propose patrol deployment, which files a proposal for a supervising officer (`components/ShiftPlan.jsx`).
* Needs a backend restart. The filled window was checked in the browser with a plan produced by the new code; the live call was not, because the running server predates it.

## Security: model assumed compromised, and a scorecard (USP plan S5) - 2026-10-14

* `tests/test_assume_compromise.py` (50 cases): the model is not called; its worst-case output is fed into each consumer. `scripts/security_scorecard.py` runs the four pure security suites and writes `docs/SECURITY_SCORECARD.md`: 161 of 161 cases stopped, listed per control.
* Writing it found three real holes, fixed here: the model could select internal templates, including a free-form one that can read `audit_log` (`query_agent.model_choice`); an invented FIR number of the register's own shape passed the identifier check; an answer in which every sentence was unsupported was passed through unchanged (now rejected and written from the rows).
* The query connection is read-only. A false "delimiter spoof" log line on every fenced prompt is gone.
* Details in `docs/SECURITY.md` section 3.7. Needs a backend restart.

## Security: one allow-list for everything that leaves (USP plan S7) - 2026-10-14

* `app/core/egress.py`: every outbound client asks `egress.check(url, purpose)` first: the language model and its token service, the vision model, open-web search, translation, speech, the event calendar. `ANTAR_EGRESS_ALLOW` unset = configured endpoints and named feature services, counted; `none` = nothing leaves; or a list of hosts.
* With `none`, no token is fetched, open-web search reports it was not reached, speech returns "not available", and answers are written from the records (`tests/test_egress.py`). A test fails when a new outbound call does not ask first.
* `GET /api/orchestrator/egress` (Admin): what may be called, what was called and refused since start-up, by host and purpose only. The calendar feed no longer follows redirects.
* Noted, not changed: "Listen to answer" sends the answer's text to a speech service. Needs a backend restart.

## Agent card (USP plan S9) - 2026-10-14

* `docs/AGENT_CARD.md`: Antar described in the AI Agent Index's 33 fields: intended and unintended uses, the model as a setting, an empty action space, guardrails, how to switch the model or all outbound calls off, the back-test and the security scorecard, no external testing, and known limits. Not linked from the About page; it is a repository document.
* All seven P0 items of `docs/USP01_02.md` are done.

## Security context, declared policy, audit rows that carry the evidence (USP plan S1, S2, S4) - 2026-10-14

* **S1** `app/core/security_context.py`: one context per request (officer and role from the token, one `call_chain_id`), bound at the outermost middleware and carried by a context variable into agents, threads and traces. Returned as the `x-call-chain-id` header. The autonomous loop runs under a named system context. A call with no context (a script, a direct test) is counted as unbound, not refused.
* **S2** `app/core/policy.py` and three new required fields in every AGENTS.md block: `sensitivity`, `min_role`, `obligations`. `orchestrator.run_agent` asks `policy.decide` first: a Constable is refused a person- or case-level agent before it starts (no breaker penalty), and obligations are applied to the result by the orchestrator (`social` cannot return people; open-web results are labelled unverified). A block without a valid declaration fails the build.
* **S4** The request's audit row now carries the call chain, the traces it opened and each policy decision; an answer's row carries digests of what it rested on (template, parameter digest, rows digest, row count, model or "offline", prompt hash). Changing a recorded decision breaks the chain. The Trace page shows the ledger's own check to an Admin.
* `tests/test_policy_context.py` (31). Needs a backend restart.

## Pin what runs (USP plan S3) - 2026-10-14

* `app/agents/agent_lock.py` and `agents.lock.json`: a SHA-256 of every agent's module and of every system prompt (line endings normalised). `python scripts/lock_agents.py` writes it; `--check` says what changed.
* At start-up a mismatch is a warning in development and stops the server in production. `tests/test_agent_lock.py` fails when an agent or prompt was edited without re-locking, so the lock has to be committed with the change.
* The short hash of all prompts is stamped on each trace as its prompt version (it was the constant "v1").

## Need-to-know retrieval (USP plan S6) - 2026-10-14

* An account can hold a `posting` (the officer's district; `scripts/set_password.py --posting "Mysuru City"`). It travels inside the signed token, never in a header in signed mode.
* `zcql_repo.need_to_know`, called from `build_spec`: below Analyst, a query that returns case rows is limited to the posting. Counts, trends and rankings are not. If another district was asked for, the rows are still the officer's own, the answer says so first ("These case rows and their count are for Mysuru City only, your posting, not Belagavi Dist"), and what was asked goes on the audit row.
* The query cache key includes the scope, so one officer's rows are never served to another.
* Not limited: Analyst and above, system tasks, and an officer with no posting on record. The two existing accounts (Admin, Approver) are unaffected. Suspect-level tables are not scoped yet.
* `tests/test_need_to_know.py` (13). Needs a backend restart.

## Sessions: sign-out ends the token; a report belongs to its officers (USP plan S10, part) - 2026-10-14

* `app/core/revocation.py`: `POST /api/auth/logout` ends the presented token on the server (only its SHA-256 is kept, until it would have expired); `POST /api/auth/revoke/{officer}` (Admin) ends every session an officer holds. The gateway checks both on every request, and the list survives a restart. The frontend calls logout when it clears the session.
* `/report/{session_id}` and `/api/export/{session_id}` open for the officers who took part in the conversation and for an Admin. Another officer gets the same refusal whether or not the session exists. A conversation with no officer on record (the non-streaming chat route does not record one) is Admin only.
* **Not done from S10, each for a reason:** moving the token to an HttpOnly cookie (changes sign-in and every request; not safe to do untested this close to the demo); running the containers as a non-root user (needs an image build and a test on AppSail); rotating the session key and removing it from git history (rewrites history; needs the owner's go-ahead).

## Predict: how the engine behaves overall (USP plan P3) - 2026-10-14

* `GET /api/forecast/explain` (`service.global_explanation`): for each crime category, how much each of the six reasons typically moves a forecast and at what share of stations it moves it by 10% or more; that category's back-test figures; the engine's weak spots by its own back-test (a calibration 10% or more off, beating recent history in 65% of weeks or fewer, a range far from 80%); and what it does not use.
* Shown inside Engine confidence on the Predict page (`components/EngineOverall.jsx`). On the stored forecasts it names murder, cyber crime, narcotics and environment offences as weakest. Needs a backend restart.

## Predict: case leads (USP plan P5) - 2026-10-14

* `GET /api/predict/leads?zone=` (`app/services/case_leads.py`), shown as "Case leads" on the Predict page for the selected district. No language model; each lead says what would settle it.
* **Shared keys**: FIRs that carry the same vehicle number, UPI id or IP address, with the key named. A key on 5 FIRs or fewer is called specific; one on more is marked as more likely a common value or a data artefact, and listed last.
* **Across a border**: accused named in this district and another, from the same count the Map uses.
* **Near repeat, measured**: a Knox test with 199 date shuffles on the district's real burglaries. The first measurement gave Belagavi 12.85 times chance; 352 of its 399 pairs were FIRs at the same recorded point on the same day (one incident, several FIRs). Those are now left out and reported apart: Belagavi 2.85, Tumakuru 2.3, Bengaluru City 1.3. The lead is offered only with at least 20 such pairs, 20% above chance and p < 0.05; a district with under 150 located burglaries is said to be untested (Mysuru City, Raichur).
* `tests/test_case_leads.py` (12). Needs a backend restart.

## Forecast: fairness and feedback, measured (USP plan P6) - 2026-10-14

* `app/forecast/fairness.py`, `docs/FORECAST_FAIRNESS.md` (generated by `python -m app.forecast.fairness`), and a "Fairness and feedback" block inside Engine confidence on the Predict page. Measured from the stored back-test, no refit.
* What it found for stations: 69 of about 1,030 were ever in the top 5% over 23 weeks; 34 of the 52 flagged each week were the same every week (65% of all flags); 96% of flags fell in city commissionerates. The report says a stable pattern and a feedback loop look the same in this record and that it cannot tell them apart. Ranges held 80% to 90% across quiet and busy stations.
* It states what is not measured: error for units never flagged (the stored back-test keeps per-unit totals for flagged units only), and any effect of policing on registration.
* A test keeps the engine's code free of any field about a person or a community. Needs a backend restart.

## Forecast outcomes: kept, scored, and fed back (USP plan P7) - 2026-10-14

* `app/services/forecast_outcomes.py`: each week's station forecasts (all crime, next 7 days) are kept the first time they are served. A kept week is scored once its target week is complete: how many likely ranges held, forecast against recorded totals. A station's last scored forecast shows on its breakdown ("The week before: forecast 1 to 3, recorded 9").
* **Confidence moves by itself**: once four weeks are scored, range coverage under 70% or over 90% across the last eight caps Engine confidence at Moderate (Limited under 60%), with the reason listed beside the others.
* **Officer feedback**: "Was this useful?" on the forecast breakdown and the shift plan (`POST /api/forecast/feedback`); "No" needs a reason. `GET /api/forecast/outcomes` returns the scores and what officers said.
* Scoring starts with the first week kept after this goes live: earlier forecasts were not stored, and until a kept week is complete the endpoint says there is nothing to score. `tests/test_forecast_outcomes.py` (13). Needs a backend restart.

## Fresh data and refit (USP plan P9) - 2026-10-14

* **Label on the page**: the Predict page now opens with "Demonstration data. The real FIR record ends on 10 Mar 2024; the weeks after it are seeded..." whenever this week's forecast stands on seeded rows. It reads fields the engine endpoint already sent, so it shows without a restart, and disappears by itself once the recent weeks are real record.
* **Weekly job**: `python -m app.forecast.refit` (`app/forecast/refit.py`). It refits the forecasts when the week or the registry moved, re-runs the back-test only when the real record or the model changed (an unchanged record gives the same numbers), then regenerates `docs/FORECAST_BACKTEST.md` and `docs/FORECAST_FAIRNESS.md`. `--check` only says what is due; `--force` re-runs everything.
* **In the running app**: once an hour the orchestrator refits the forecasts if the week has moved, so a server left up over a Monday does not serve last week's forecast. It never runs the back-test (minutes of CPU); `GET /api/forecast/refit` says when that is due and what to run.
* Not done: the job is not scheduled on any machine. Schedule it weekly after Sunday, e.g. `schtasks /Create /SC WEEKLY /D MON /ST 05:00 /TN AntarForecastRefit /TR "D:\Project\.venv\Scripts\python.exe -m app.forecast.refit"` run from `D:\Project`, or a Catalyst cron job after deploy.
* `tests/test_forecast_refit.py` (16). The endpoint and the hourly refit need a backend restart.

## Deploy image: built and run locally - 2026-10-14

* `docker build -t antar-api:local .` succeeds: 867 MB compressed, 3.06 GB unpacked. Not pushed, not deployed.
* **Two bugs that would have broken the deployment, found by running the container:** (1) the first request opened the database path before the packed database was unpacked, sqlite created an empty file there and staging took it for the registry, so the app ran on no data; (2) the Brain's 100,000-FIR index shipped in the image but was looked for beside the staged database, so it was empty. Staging now runs before anything is served (about 3 seconds), checks for the FIR table rather than a non-empty file, and copies the index with it (`app/core/db_path.py`, `main.py`).
* **Non-root (S10):** the image runs as user `antar` (uid 10001). Confirmed locally; not confirmed on AppSail.
* Measured in the container with a 2 GB limit: warm-up completes in about 5 minutes (1,000,000 FIRs, forecasts fitted, 100,000 FIRs in the Brain index); memory 1.7 GB of 2 GB after warm-up; `/tmp` 1.5 GB. No out-of-memory kill.
* Open before a deploy: the container starts with unsigned header identity unless `ANTAR_AUTH_SECRET` and the accounts are set in the Catalyst console; `main.db.gz` is the 2026-09-18 snapshot; no language model is configured in the image; 1.7 GB of a 2 GB limit leaves little room.
* The audit integrity note no longer says "every entry was verified" beside a broken chain.

## Chat: a locality is no longer listed as a district - 2026-10-14

* **What was wrong:** "Which districts have the most vehicle theft?" answered "Jayanagar, 27 FIRs, 11% of the Karnataka total". Two causes. (1) Rankings grouped on `zone`, and 3,868 seeded rows carry a locality there (Jayanagar, Whitefield, Mysuru-Devaraja...). (2) "Vehicle theft" exists only in 286 seeded rows; the real register has no such head.
* **Fix:** district rankings (T11) now group on the district column, which holds the parent district for every row; the result key is unchanged, so no reader had to change (`QuerySpec.rename`). An answer about a crime type with no real rows now says so on its second line: demonstration records, not registered FIRs. This covers every template, including counts and trends. 17 crime-type spellings are seeded-only; most merge into a real head (theft into THEFT), and the ones that do not are vehicle theft, chain snatching and a few others.
* Now: Bengaluru City 175, Mysuru City 33, Belagavi Dist 22, with the note.
* Left as is: CID, ISD Bengaluru, Coastal Security Police and Karnataka Railways still appear in district rankings; they are police units in the KSP record, not districts. The Map and the Predict list still show the seeded localities, where they are called areas.
* `tests/test_zcql.py` (3 new). Needs a backend restart.

## Learning from officers, made honest and hard to game - 2026-10-14

* **What it is, stated plainly:** not reinforcement learning, and nothing is retrained. A question officers rate poor stops being suggested and goes to a review queue; when the language model writes an answer, up to two answers officers rated useful for similar questions are shown to it as examples of shape. The real closed loop is the forecast one (P7): forecasts are scored against what happened and lower the engine's confidence by themselves.
* **Fixed:** (1) the officer on a rating came from the request body (default "OF-1001"), so anyone could rate as anyone; it now comes from the token. (2) One officer could stack votes; now one vote per officer per question, and voting again replaces it. (3) The answer kept with a rating was the text the browser sent; it is now the answer this server gave in that conversation, found by its reasoning id, and an answer from another officer's conversation cannot be rated (403). A rating whose answer is no longer held still counts for suggestions but never becomes an example. (4) Ratings were written to `data_feedback.jsonl` beside the code, which a read-only deploy cannot write; they are now in the `answer_feedback` table. The old file is imported once and left in place; its test entry (`mock-rlhf-1`) and browser-sent answers are not carried over.
* **The Console's growth view** said "2 questions now have a rated answer that shapes the next similar one"; one of them was a test entry and the other had no answer. It now counts only answers that can be used, names how many officers rated, and has a new "Forecast, in use" line (range coverage in use and officer feedback on forecasts).
* The claim in `antar_identity.USPS` is now "It learns from use", naming both loops.
* The chat page sends the answer's reasoning id with a rating instead of the officer and the answer text.
* `tests/test_feedback.py` rewritten (10, no app or live store), `tests/test_chat_quality.py::TestFeedbackLearning` moved to the table (9). Needs a backend restart. On Catalyst the table lives in `/tmp` with the rest of the database, so ratings reset on a redeploy.

## Audit chain: the cause of the breaks, fixed - 2026-10-14

* **What was wrong:** walking all 11,447 stored entries found 32 linkage breaks and 0 digest mismatches: no entry's content was altered. 31 breaks were ordering: each write chained from this process's in-memory tail and was stored afterwards, so a request's HTTP row and its AI_REASONING row (written from a worker thread) could be stored in the opposite order to the one they were chained in. One break came from a second process writing to the same table.
* **Fix (`app/services/audit_store.py`):** one write path, `_write`. The previous hash is read from the database inside a `BEGIN IMMEDIATE` transaction, so the order of the links and the order of the rows are the same thing across threads and processes. The reasoning trail is written in the same transaction as its row. `verify_chain_report()` now checks every stored entry (it used to check this process's last 2,000 in memory) and says what it checked.
* **Archive, not rewrite:** `archive_and_restart()` / `scripts/audit_archive.py` copies every row unchanged into `audit_log_archive`, then starts the live chain with one CHAIN_ARCHIVED entry whose previous hash is the archived tail and which records the row count, a SHA-256 over the archived hashes and the breaks found. It needs a written reason and runs with the server stopped. **Not run yet:** the owner runs it.
* **Tests that wiped the live ledger:** `tests/test_audit.py` and `tests/test_audit_chain_persistence.py` call `audit_store.clear()` (deletes every row). They were safe only when `tests/conftest.py` loaded; run without it they pointed at main.db. Both now use their own file, and tamper with stored rows instead of memory. New tests: 80 concurrent writes stay in order, a second process does not fork the chain, archiving moves every row and links the new chain to it.
* `tests/test_hitl.py`: two tests that start the full app fail with 401 in signed-token mode; unrelated to this change.

## Speed pass - 2026-10-14

Measured every page-load endpoint against the running backend (`/api/*`, cold then warm), then fixed the four that cost the most.

| Endpoint | Before | After | Change |
|---|---|---|---|
| `/api/dataset/overview` (first load after a restart) | 47.8 s | 2.0 s | Data Overview products are kept on disk (`product_cache` table), tied to the registry's row count and newest row id, TTL unchanged; recomputed when rows change |
| `/api/dataset/officer_view` (same) | 43.9 s | 0.08 s | same |
| `/api/dataset/cycles` (same) | 13.9 s | 0.08 s | same |
| `/api/dataset/summary` (same) | 11.5 s | 1.1 s | same |
| `/api/map/gi_star` (every call) | 2.2-3.3 s | 0.36 s | district centre points (a full-table average) kept until the newest row id moves |
| `/api/dataset/graph` on the wire | 1.8 MB | 170 KB | responses over 1 KB are gzip-compressed; the chat stream and audio are not |

* The first restart after this change writes the disk copies during warm-up; the gain shows from the next restart on. On Catalyst the database is unpacked fresh on each cold start, so the disk copies help there only if `main.db.gz` is repacked after a warm-up.
* Still slow on first load after a restart, while warm-up runs: `/api/predict/board` (7 s, then 70 ms).
* Also: a count of demonstration records is now shown beside the bottom line, not folded under Limits.
* `tests/test_speed_fixes.py` (8).
* Not caused by this work, found while testing: `tests/test_hypothesis_gate.py` and two `tests/test_hitl.py` tests fail with 401 when run without `tests/conftest.py` (it turns signed tokens off).

## Chat suggestions from the real record - 2026-10-16

* The empty-chat starters named people, vehicles and localities that exist only in seeded demo rows ("background check for Ravi living in Jayanagar", "KA-02-M-2093", "Bheema the Butcher", "South Bengaluru"). They, the role chips and the server's starters (`followup_agent._STARTER_CANDIDATES`) are now questions answered from the real KSP record, in English and Kannada. The year asked about is 2022, before the duplicated 2023-24 rows.
* Removed because the answer was to a different question: "Which districts have the most vehicle theft?" and "Chain snatching trend" (demo-only types), "Which stations have the most pending investigations?" (ignored "pending"), "Which act-sections have the lowest conviction rate?" (gave the statewide rate), "How many cases are still pending investigation?" (gave a status breakdown).
* The demonstration-records note now appears only when the whole count is demonstration data. "Crimes against women" carries one seeded spelling beside ten real heads and was wrongly labelled.
* `tests/test_suggestions_real.py` runs every offered question through the router and the answer writer: rows found, nothing broadened, no demonstration count, no seeded name. The documented question bank behind Docs mode (`intelligent.db`) is unchanged.

## Documented questions moved to 2022, without raw counts - 2026-10-16

* The 50-question bank behind Docs mode (`intelligent.db`, not in git; backup `intelligent.db.bak-2026-10-16`): the 14 questions naming 2023 now name 2022 (the year-on-year one is 2021 to 2022). The two that headlined a raw count are rankings: "Which police stations recorded the most cybercrime in 2022?" and "Which districts had the most murders in 2022?". Expected answers that quoted published 2023 statistics are replaced by what Antar returns for 2022; published 2022 figures were not checked, so none is quoted.
* The chat starters, role chips and server starters no longer ask "how many murders"; they ask which districts had the most.
* **Kannada years were being dropped.** "2022ರಲ್ಲಿ" fuses the case suffix onto the year, so the date parser never saw it and the question was answered for every year on record (the old 2023 Kannada bank questions had the same fault). The seam is now split before the date is read (`heuristics.extract_entities`).
* Records-only routing gaps in the bank, unchanged and not caused by the year: "Cognizable FIRs" answers the total FIRs, "Top 10 stations by FIR volume" asks for a crime type, "Peak month for cybercrime" lists cases instead of a month, and the Kannada charge-sheet question returns the conviction rate. With the language model connected the selector may route these differently; not verified.
* Docs: the pitch script's three 2023 lines now use the 2022 answers; the product guide example moved to 2022.

## Four documented questions answered as asked - 2026-10-16

* **"Cognizable FIRs registered in Karnataka in 2022?"** gave the total only. It now gives the official total and, beside it, the cognizable share of the year's real-record rows (91%, 63,925 of 70,451 held), saying the registry holds part of the year so the share is the figure to read (`zcql_local.year_cognizable`, a fixed query: the `crimes` view has no cognizable column).
* **"Top 10 stations by FIR volume 2022?"** asked which crime type. "By FIR volume", "most FIRs", "busiest" and "ಪ್ರಮಾಣದ ಪ್ರಕಾರ" now rank all crime (`heuristics._volume_q`).
* **"Peak month for cybercrime in 2022?"** listed cases. A peak-month question is now a monthly series over the span asked (T3 takes `date_from`/`date_to`), led by the month: July 2022, 324 cases, 18% above the monthly average.
* **Kannada charge-sheet question** returned the conviction rate: the writer knew "ದೋಷಾರೋಪ" but not "ಚಾರ್ಜ್‌ಶೀಟ್" (which carries a zero-width joiner). Both now give 89%.
* The yearly answer called 2016-2022 a "1:100 representative sample"; it is about one in three of each year, and now says so.
* `tests/test_suggestions_real.py` covers all four in both languages.
* **Test entries in the live audit ledger:** `tests/test_slash_commands.py` and `tests/test_layout_composer.py` run the chat stream, which writes an audit entry and a trace per answer. Run without `tests/conftest.py` (as I ran them on 2026-10-14 and 2026-10-16) they wrote into the live ledger: 28 entries by officer "OF-stream", and 14 test sessions on the Trace page. The chain is intact; the entries were not removed. Both files now write to their own temporary files.

## Questions by year, 2016 to 2026 - 2026-10-16

* A "By year" row under the chat chips (`components/YearQuestions.jsx`): pick 2016 to 2026 and the suggested questions above are replaced by five for that year (picking it again, or the refresh button, brings the usual ones back) (most theft by district, IPC/BNS vs SLL split, peak month for cybercrime, conviction rate by district, crimes against women by district), in English or Kannada.
* (Removed 2026-10-16 at the owner's request: the line under the pills on what each year's data can bear. Answers about 2024-26 carry their own demonstration label.) It read: 2016-2022 about a third of each year held (read shares and rankings); 2023 complete but 85,264 duplicated rows; 2024 real to 10 March with 14,736 duplicates, the rest demonstration data; 2025 and 2026 demonstration data, 2026 still in progress.
* `tests/test_suggestions_real.py` runs all 110 (11 years, 5 questions, 2 languages): each routes to that year and returns rows; none asks for a raw count.
* Not done: an answer about 2025 or 2026 does not itself say it is demonstration data; only the line above the questions does.

## Answers about 2025-26 say they are demonstration data - 2026-10-16

* An answer whose period lies wholly after the real record (10 March 2024) now says, on its second line: "these are demonstration records, not registered FIRs. The real KSP record ends on 10 Mar 2024." A period that crosses the end (2024, or "last 12 months" when that reaches back) says rows after that date are demonstration records. No period named: nothing added. Real-record years are unchanged.
* Covers every template the writer answers (counts, rankings, trends, rates, yearly totals, "last 3 months") in English and Kannada, and is shown beside the bottom line, not under Limits. Model-worded answers get the same line appended (`query_agent._with_seeded_note`).
* Tests in `tests/test_suggestions_real.py`.

## Plain words on every screen - 2026-10-18

Read each screen as it renders and replaced the technical words an officer or a member of the public would not know. English and Kannada where both exist.

* **Predict:** "Anomaly score" is "Unusual-activity score (2 is unusual, 4 is rare)"; "inferred" tags are "estimate"; "Hypotheses" is "Possible links between accused" (Confirm/Reject link); the track record reads "of weeks fell inside the likely range"; alert types read "Sudden rise", "Seasonal rise", "Hotspot"; the footer no longer says "MAD-z → ST-DBSCAN → split-conformal band"; case leads say "shared details" and "data-entry error" instead of "keys" and "data artefact".
* **Map:** hover tips no longer show "Gi* … z=…"; the "Geo Intel" and "Prediction" tickers are "Briefing" and "Next week" in plain sentences.
* **Chat:** evidence badges are "From the records / Calculated / Estimate / Not on record" (were Known / Derived / Inferred / Unknown); "A5 Vigil compliance audit - APPROVED" is "Misuse check: passed"; the evidence line reads "FIR records · as of" with a tick, not "K · crimes · as-of".
* **Expert workspace:** "OSINT search", "AI/ML forecast (Poisson GLM)", "K/D/I/U dossier", "MO signatures", "Template", "Latency", "Integrity" are plain.
* **Search:** "Enable OSINT", "Fuzzy + phonetic engine", "Statutory § 91 Evidentiary Dossier", "Risk Index", "priors", "Network centrality", "FIR-linked ID", "Modus operandi" are plain; suggested steps say "Request call records (CDR)".
* **Brain / Data Overview:** "rendered", "click a node", "Intelligent Data", "ACC/Arr." are plain; the full-dataset blurb no longer claims "unfiltered … without sampling" and says which years are partial or demonstration data.
* **Account, Answer History (was Trace & Telemetry), Approvals, page guide, Docs, About:** jargon and two overclaims removed ("0.0% hallucination", "sandboxed OSINT layer").
* Not changed: names of the agents in the Brain strip; "Dis/acq", which is a value in the data; test sessions listed on Answer History. The evidence badge words come from the backend and need a restart.

## Query templates T24-T28 and the routing misses - 2026-10-20

Every question officers had asked (98 distinct, audit log) was run through the router; 16 got the wrong answer. All 16 now route to a template that answers them.

* **T24 Case stages and pendency:** under investigation / pending trial / convicted per station, district or crime type, with how long open investigations have been open (90 days, 1 year, or "more than N days"). "Stations with the most pending investigations in Mysuru", "POCSO cases that reached trial in 2023".
* **T25 What a crime is made of:** counts by sub-heading ("49% of thefts are two-wheelers"), and burglary by night vs day (filed as Burglary - Night / - Day; 4.1 to 1).
* **T26 Day-of-week / month-of-year pattern,** by registration date, saying the register has no time of the offence.
* **T27 Side by side:** two or more districts, stations or years, counts and outcome rates; year pairs across 2022/2023 carry the partial-extract note.
* **T28 Outcomes by Act or section** ("which act sections have the lowest conviction rate").
* **Sub-headings** (`zcql_repo.HEAD_ALIASES`): extortion, two-wheelers, house theft, jewellery, sand, cattle, matka … now narrow a question. **Vehicle theft and chain snatching** count the real register (Theft › automobiles, Robbery › Chain Snatching) as well as the seeded label: vehicle theft in Bengaluru City 175 → 29,224; chain snatching statewide ~300 → 3,548.
* **Police stations** (`zcql_repo.resolve_stations`): "thefts in Koramangala", "Koramangala PS" filter to the station instead of answering for all of Karnataka; "beats in Jayanagar" uses Jayanagar PS.
* **Places:** Mangaluru, Hubballi, Belagavi, Mysuru mean the real districts (the seeded localities stay included); Vijayapura, Gulbarga, Shimoga, Tumkur, Bellary, Coorg, KGF … and "Hubballi-Dharwad" are recognised; compared places keep the order asked.
* **Routing fixes:** monthly trend no longer becomes a ranking; "profile for suspect Saleem Malik" is a name lookup; phone-number links say phones are not a link key and show UPI/IP/vehicle/accused links; corridors between two districts; patrol deployment → beats over the last 12 months of the real register; "hotspots in Bengaluru" ranks its stations; "increase or decrease between 2024 and 2025" compares the years; "hours of the day" says the register has no time.
* **Speed:** cross-district links 23.5 s → 3.4 s; vehicle and accused lookups 8.8 s → 0.7 s; outcomes by section 38 s → 7 s.
* Tests: `tests/test_templates_t24_t28.py` (41). 265 existing routing, template and golden tests pass. Run read-only with `OBS_ENABLED=0 --noconftest`.
* Not changed: "assault" still maps to the seeded ASSAULT label only (the register files assaults under Cases of hurt and others; which heads count is the owner's call). Kannada routing for the new templates covers ಹೋಲಿಕೆ / ಬಾಕಿ / ತನಿಖೆಯಲ್ಲಿ only. Needs a backend restart.
