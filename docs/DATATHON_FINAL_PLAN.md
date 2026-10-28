# Antar: final plan for the KSP Datathon demo

Written Tue 27 Oct 2026, 05:00 IST. **Demo day is Thursday 29 Oct**, so there are about
two working days. This is a plan to approve, not work already done: nothing in the code or
the database has changed yet.

---

## 1. The short version

**Goal.** Judges should leave convinced of three things (your pick):

1. **Trustworthy answers.** Every number comes from FIRs, and we can show the accuracy as a
   measured percentage.
2. **Real predictive ML.** Several models compete, and they are scored on real months they
   never saw, using the metric criminologists use.
3. **Scale and speed.** 19 lakh real FIRs on a laptop, plus a 1-crore stress run, with
   timings shown live.

**Two systems, one codebase** (your decision):

| | **Antar Cloud** (the judges' link) | **Antar Lab** (your laptop, the live demo) |
|---|---|---|
| Runs on | Catalyst AppSail: 2 GB memory, **1 GB disk** | i7-9750H, 32 GB RAM, GTX 1650, Windows |
| Register | Today's 10,00,000 FIRs, demo-day surge removed | **~19 lakh** FIRs: today's plus ~9.4 lakh unused real rows |
| Schema | Today's | Today's **plus the official ER tables** derived from the real extract |
| ML | Today's forecast (Poisson GLM) and anomaly scan | **Champion vs challenger**: GLM vs LightGBM, scored with PAI/PEI on held-out real months |
| Scale proof | A recorded benchmark card | **Live Scale page**: SQLite vs DuckDB, 19 lakh real rows and a 1-crore stress copy |
| Accuracy proof | Accuracy card (same 150-question score) | Accuracy card, plus a re-run button |
| LLM | QuickML, with the record-based fallback | Same |
| Today's date | As now (wall clock, demo rows) | **As of 31 Mar 2024**, the end of the real data |

**The top risk is not ML. It is whether the judges' link works.** Today's register expands to
1.6 GB in `/tmp` and AppSail offers 1 GB of disk. Item C1 must be fixed first; see §4.

---

## 2. What you decided

| Question | Your answer | What it means for the plan |
|---|---|---|
| Register | Top up, don't remove | Lab gets ~9.4 lakh more real rows. Existing rows stay, including the ~1 lakh 2023 copies (labelled, not quoted) |
| Demo date | As of 31 Mar 2024 | Lab answers and forecasts run as of the last real week. Cloud keeps today's behaviour |
| Officer names (IOName, KGID) | Keep real names | Shown as they are. One caution in §8 |
| Scale proof | DuckDB + Scale page | New Lab page; Cloud shows the recorded result |
| Forecast ML | Champion vs challenger | GLM vs LightGBM; TimesFM only if time allows |
| Judges' link | Catalyst only | Cloud must fit 1 GB of disk. No tunnel |
| LLM | QuickML + record fallback | No change |
| Timeline | 3 days or less | Strict P0 / P1 / stretch order (§6) |
| AppSail disk | 1024 MB → build two systems | Slim Cloud build + full Lab build |
| ER person tables | Derive only what is real | Person-level tables stay empty, labelled "not in the extract" |
| Win theme | Trust + ML + Scale | Kannada voice gets no new work; it stays as it is |
| Cloud data | Keep it; remove the 29th surge; add what's required | Revert the demo-day volume script; keep the story cases |
| Gold question set | 150 questions | EN + KN, scored against SQL ground truth |
| Stress data | 1 crore only | ~2 GB of Parquet on D:, git-ignored |

---

## 3. What I found

### 3.1 The official extract (`E:\Datathon_2026\03_resources\FIR_Details_Data.csv`)

| Fact | Value |
|---|---|
| Rows / columns | **16,74,734** / 34 (573 MB). Loads in 13 s with pandas |
| Period | Jan 2016 to **Mar 2024**. 2024 has only Jan (17.9k), Feb (18.6k) and Mar (5.8k, a partial month) |
| Districts / stations / beats | 41 / 1,054 names (1,074 Unit_IDs) / 6,771 beats |
| Exact duplicate rows | 22,791. On an 11-field signature: 53,408 |
| Coordinates | 30% of rows have lat/lon. **21k of those fall outside Karnataka** (e.g. 6.75, 68.18), so they need a bounding-box filter |
| ActSection | 99.8% parse into Act + sections; 21% name more than one Act. The raw text is messy (thousands of spellings), so it needs normalising |
| FIR_Stage | 343 raw values. The top 12 cover 99%: Pending Trial 4.98 lakh, Convicted 3.44 lakh, Undetected 1.88 lakh … |
| Victim columns | Counts only (Male, Female, Boy, Girl). `VICTIM COUNT` is almost always 0, so don't use it |
| Officers | 24,422 IO names / 29,844 KGIDs |
| Persons | **No accused, victim or complainant names.** Counts only |

### 3.2 Today's register (`main.db`, 1,687 MB)

| Fact | Value |
|---|---|
| FIRs | 10,00,000 = 9,48,671 marked real + 51,329 synthetic |
| Real rows already taken from the extract | ~5.75 lakh (2026-09-18) on top of earlier loads. PROGRESS.md: **9,65,530 unused real rows** remain |
| Known issue | 1,00,000 `SYN-` rows are copies of real 2023 / Q1-2024 rows; 2023 shows 3.85 lakh against 2.31 lakh in the extract. You chose to keep them |
| Synthetic dates | 2025-01 to **2026-12-31**. 2,998 rows are dated after today |
| **The 29th surge** | 670 FIRs on 29 Oct and 300 on 28 Oct, against ~50 on a normal day. `scripts/demo_day_volume.py` moved them there from Nov–Dec (no inserts), and `docs/demo_day_volume_revert.json` exists, so **one command puts them back** |
| Space | FIRs 510 MB, **indexes ~900 MB** (several pairs duplicate each other), victims 106 MB + indexes, forecast cube 107 MB |

### 3.3 The official ER diagram vs today's schema

Today `main.db` has the ER **master** tables (Act, CrimeHead, CrimeSubHead, CaseStatusMaster,
Court, District, Unit, Employee, CasteMaster, ReligionMaster, OccupationMaster …), but **not**
the case-level tables. The FIR data sits in one flat `FIRs` table.

| ER table | In the extract? | Plan (Lab) |
|---|---|---|
| **CaseMaster** | Yes: district, unit, year/month/day, FIR type (→ GravityOffence), stage (→ CaseStatus), crime group/head, lat/lon | Build it. One row per FIR |
| CrimeNo / CaseNo | Not given | **Generate in the official format**: category (1) + DistrictID (4) + UnitID (4) + year (4) + running serial (5), e.g. `104430006202600001`. Real format, honestly derived |
| **ActSectionAssociation**, **Section**, **Act** | Yes (ActSection text) | Parse and normalise; keep Act and Section order |
| **CrimeHeadActSection** | Derivable | Which act/section pairs occur under each crime head |
| **Employee** (IO) | Yes (IOName, KGID, Internal_IO) | One row per officer, linked as PolicePersonID |
| Unit, District | Yes | Reconcile against the existing masters |
| ArrestSurrender | Counts only | A per-FIR count table (`arrest_counts`), not fake events |
| Accused, Victim, ComplainantDetails | **No** | **Left empty**, with a visible note: "not in the SCRB extract". Counts live in `case_person_counts` |

This is a strong, honest line for the judges: *"We implemented your ER design exactly. Where
the extract has the data, the table is full. Where it doesn't, we say so; we did not invent
people."*

---

## 4. Antar Cloud: the judges' link (fits in 1 GB)

### C0. Remove the 29th surge (5 minutes)

```bash
python scripts/demo_day_volume.py --revert
```

This moves the 970 rows back to Nov–Dec. The register stays at exactly 10,00,000. The story
cases (C2 snatching crew, C3 UPI mule ring, C4 "digital arrest") and the WOW-3 Rajajinagar
spike were never moved by this script, so they stay. Then run
`python scripts/demo_check.py --date 2026-10-29 --full` and refit nothing.

> Decision for you (§9, Q1): synthetic rows dated **after today** (2,998 rows, up to 31 Dec
> 2026) are still in counts. Recommendation: exclude dates after the wall clock from every
> count. This is a filter, not a deletion.

### C1. Make it fit and prove it fits (the most important item)

Today: `main.db.gz` (275 MB) expands to **1.6 GB in `/tmp`**. The AppSail disk is 1,024 MB.
Two unknowns decide the fix, so the first step is a **10-minute probe deploy** that logs
`df -h /tmp /app`, `mount | grep tmp` and free memory at start-up:

- Is `/tmp` counted against the 1 GB disk, or against the **2 GB memory** (tmpfs)? If it is
  tmpfs, a 1.6 GB file in `/tmp` plus Python is an out-of-memory crash, whatever the disk.
- Is the image's own filesystem readable at run time without counting? (Normally yes.)

Then choose:

| Option | How | Fits when | Effort |
|---|---|---|---|
| **A. Read-only register from the image** (recommended if the probe allows) | Ship `main.db` **uncompressed inside the image** and open it with `mode=ro&immutable=1`. Writes (audit log, sessions, HITL, feedback) go to a small `ops.db` in `/tmp`, attached at connect time | The image layer is not counted as disk. `/tmp` holds only ~50 MB | ~0.5 day; touches `db_path.registry_connect` and the few writers |
| **B. Slim the register** | Drop duplicate or unused indexes (find them with `EXPLAIN QUERY PLAN` over every template), drop the forecast cube (keep `forecast_output`), move long text columns (ActSection, Place_of_Offence, MO) to a side table, then `VACUUM` | Target **≤ 750 MB** expanded, with vectors ≤ 900 MB | ~0.5 day, plus a full test run |
| A + B | Both | Safest | ~1 day |

Acceptance for C1: AppSail logs show the database ready and `/api/health` green, and **a
cold start, 20 chat questions and every screen** work with no restart, at ≤ 1,900 MB memory.

### C2. Add what is required (Cloud)

These are small and add trust without adding size:

- **Accuracy card** (from L4): a static JSON with the score, shown in About/Docs and in chat
  for "how accurate are you?".
- **Scale card** (from L5): the recorded benchmark table and a chart.
- **ML card** (from L3): the champion/challenger league table and the PAI curve as a static
  result.
- The settings already listed in DEPLOY.md (`ALLOWED_ORIGINS`, `ANTAR_AUTH_SECRET`,
  `ANTAR_USERS` …).

---

## 5. Antar Lab: your laptop (everything)

### L1. Top up to ~19 lakh real FIRs

- Load the unused real rows from the extract with the same 14-field de-duplication used on
  18 Sep (PROGRESS.md §"Scaled the FIR registry"). That leaves an estimated **~9.1–9.4 lakh**
  new rows after signature de-duplication, for about **19 lakh FIRs**.
- Clean while loading: drop coordinates outside Karnataka, trim crime-head names, map the
  343 stages to the 12 canonical ones (keeping the raw value), and parse ActSection.
- Then rebuild the caches (district cache, graph cache, dataset overview), the Brain corpus
  index (optional, 1 lakh → 2 lakh), and the forecast cube.
- Work on a **copy** (`main_lab.db`), selected with `ANTAR_DB`. `main.db` and the Cloud build
  are untouched.

### L2. Official ER schema (derived, real only)

Build the tables in §3.3 as real tables beside `FIRs`, with foreign keys and indexes, plus a
**schema page** in the Docs screen that shows the ER diagram with fill rates per table. The
existing `FIRs` table remains the query surface, so no template has to change on demo eve.

### L3. Real predictive ML: champion vs challenger

| Model | Role | Tooling |
|---|---|---|
| Seasonal-naive / EWMA | Baseline: the bar to beat | Existing |
| **Poisson GLM** (today's) | Champion | Existing `app/forecast/model.py` |
| **LightGBM global model** | Challenger: one model across all stations and categories, using lags, rolling means, calendar, festival and neighbour features | Nixtla `mlforecast` + `lightgbm`, with conformal intervals |
| TimesFM 2.5 (zero-shot) | Stretch only: needs torch, a large download | Lab only |

**How they are scored.** This is what makes it credible:

- **Rolling-origin back-test** on real data. Last origin: forecast Jan–Mar 2024 from data up
  to Dec 2023. The model never sees those weeks.
- **Count metrics:** MAE and RMSE per unit-week, Poisson deviance, and **interval coverage**
  (does the 90% band really hold 90%?).
- **Hotspot metrics: PAI and PEI.** The Predictive Accuracy Index is the standard in
  crime-forecasting research: the share of crimes caught in the flagged area, divided by the
  share of area flagged. It is reported as a curve across coverage levels (Hu et al.; Crime
  Science 2020). Area units: H3 cells over the rows with valid coordinates, plus stations by
  FIR share. PEI rescales PAI against the best possible result.
- **Fairness check** with the existing `forecast/fairness.py`: does the challenger point at
  the same over-policed places harder?

**What the judges see** (Predict screen, Lab):

1. A **league table**: model × crime category, with MAE, coverage, PAI at 5% and 10% area,
   and the winner highlighted.
2. **Predicted vs actual** for Jan–Mar 2024, per district, which they can click.
3. **Why** for one forecast: the GLM's existing driver breakdown, and SHAP for LightGBM.

Honest claim to make: *"On Jan–Mar 2024, which no model saw, the champion flags X% of next
week's FIRs in 5% of the area (PAI = …)."* The numbers come from the run; nothing is quoted
before it exists.

### L4. Accuracy you can prove: the 150-question gold set

- Start from the 165 datathon prompts (`officer_questions.py` is drawn from them) and the 50
  in `intelligent.db.question_bank`. Pick **150**: 75 English, 75 Kannada, covering every
  template, case lookups, comparisons, spikes, register gaps and refusals.
- For each, write the **ground-truth SQL** by hand, plus the expected *kind* of answer (a
  number, a ranking, a refusal or a gap message).
- A harness (`scripts/eval_gold.py`) asks Antar each question, extracts the numbers and
  entities, and checks them against the SQL result. **Execution accuracy**, the BIRD-style
  method, rather than string matching.
- Output: overall score, per-category score, **no-hallucinated-number rate** (should be
  100%: the guardrails enforce it) and correct refusals. Published as `docs/ACCURACY.md`
  and as the Accuracy card.
- Context for the pitch: the best general text-to-SQL systems score about 82% on the BIRD
  leaderboard. Antar's template design aims higher on its own domain, and the harness is how
  we prove it rather than claim it.

### L5. Scale and speed you can see

- Export the Lab register to **Parquet** (columnar, compressed), and build a **1-crore
  stress copy** by resampling real rows with new ids and shifted dates, labelled
  `stress=true` (~2 GB on `D:\Project\scale\`, git-ignored).
- Add **DuckDB** (embedded, open source) as a read-only analytics engine over the Parquet
  files. SQLite stays the app database. Published comparisons show DuckDB aggregations about
  an order of magnitude faster than SQLite on large tables; we show *our own* measured numbers.
- New **Scale page** (Lab): six fixed queries (district ranking, monthly trend, crime mix
  per station, pendency, day-of-week, a 2-key join). Each runs on SQLite with 19 lakh rows,
  DuckDB with 19 lakh, and DuckDB with 1 crore, with the timing shown as it runs.
- A **concurrency test** with Locust against the Lab API (e.g. 50 simulated officers), with
  p50 and p95 latency recorded in `docs/SCALE.md`.

### L6. Things deliberately not done before Thursday

| Idea | Why not now |
|---|---|
| A full move to DuckDB as the app database | Every template and test would change two days before the demo |
| TimesFM / Chronos | Torch download plus CPU inference; only a stretch goal after L3 works |
| Splink entity resolution of IO names | Worth doing later (it de-duplicates millions of records on a laptop); not needed for the win themes |
| cosmos.gl million-node graph | The current Brain graph is enough; a GPU graph is a post-event upgrade |
| deck.gl H3 map | Pre-aggregated H3 cells would make the map faster; post-event |
| BGE-M3 multilingual embeddings | Better Kannada recall, but it means re-indexing; post-event |
| Kannada ASR (IndicConformer) | Voice is not in the chosen win themes |

---

## 6. Two-day schedule

The **P0** items must be done; P1 if time allows; stretch only if everything else is green.

### Tuesday 27 Oct

| # | Item | Pri | Est. | Done when |
|---|---|---|---|---|
| 1 | C0: revert the 29th surge; demo_check | P0 | 0.3 h | 28–29 Oct back to ~50 a day; demo_check READY |
| 2 | C1 probe deploy (`df`, `mount`, memory) | P0 | 1 h | We know what counts against disk |
| 3 | C1 fix (A, B or both) + test suite | P0 | 4 h | Image ≤ limits; all tests pass |
| 4 | C1 deploy + smoke test on Catalyst | P0 | 1 h | Judges' link works cold, all screens |
| 5 | L1 top-up into `main_lab.db` | P0 | 2 h (unattended) | ~19 lakh rows; caches rebuilt |
| 6 | L4 gold set: write 150 Q + SQL | P0 | 3 h | `docs/gold_questions.jsonl` |

### Wednesday 28 Oct

| # | Item | Pri | Est. | Done when |
|---|---|---|---|---|
| 7 | L4 harness + first score; fix the worst misses | P0 | 3 h | Score published; Accuracy card |
| 8 | L3 LightGBM challenger + PAI/PEI back-test | P0 | 4 h | League table + predicted vs actual |
| 9 | L5 Parquet + 1-crore copy + DuckDB + Scale page | P1 | 3 h | Live timings on screen |
| 10 | L2 ER tables + schema page | P1 | 2 h | Tables with fill rates |
| 11 | C2 cards on Cloud + redeploy | P1 | 1 h | Cards visible on the judges' link |
| 12 | Full rehearsal on both systems, phone included | P0 | 1 h | §7 script runs clean twice |
| 13 | Locust concurrency run | stretch | 1 h | p50/p95 in SCALE.md |
| 14 | TimesFM 2.5 zero-shot column | stretch | 2 h | Third row in the league table |

Each change is committed in its own group, with PROGRESS.md updated, `lock_agents.py` re-run
after any agent change, and the full test suite run before each deploy.

---

## 7. Demo script (8 minutes)

| Min | Where | Show | Say |
|---|---|---|---|
| 0–1 | Judges' phones | Open the Catalyst link, sign in with Demo Access | "This is live on Zoho Catalyst. Your phone, right now." |
| 1–3 | Lab · Chat | 3 questions: one ranking (EN), one Kannada, one case; then "why?" | "Every number links to FIRs. Ask it how it got there." |
| 3–4 | Lab · Accuracy card | 150-question score, no-hallucinated-number rate | "We don't claim accuracy, we measured it, in both languages." |
| 4–6 | Lab · Predict | League table, PAI curve, predicted vs actual for Mar 2024 | "Three models compete on months they never saw. The winner earns its place." |
| 6–7 | Lab · Scale | Run the six queries on 19 lakh and 1 crore | "Same laptop, no GPU, 1 crore FIRs." |
| 7–8 | Lab · Brain + HITL + audit | One linked group, one approval, the audit chain | "And nothing reaches the street without a second officer's sign-off." |

**Backup plan.** If Catalyst is down, use the recorded video of the same script. If the Lab
breaks, the Cloud link carries the chat, map and predict story. If QuickML is slow, the
record-based answers carry on unchanged.

---

## 8. Risks

| Risk | Likelihood | Effect | Mitigation |
|---|---|---|---|
| `/tmp` is memory-backed on AppSail | Medium | Cloud OOM at start | C1 probe first; option A avoids `/tmp` for the register |
| Top-up breaks a demo answer | Medium | Wrong number in the demo | Lab uses `main_lab.db`; Cloud untouched; gold set re-run after top-up |
| LightGBM doesn't beat the GLM | Possible | Less flashy story | That *is* the story: "the simpler model won on held-out data, so we ship it." Champion/challenger is honest either way |
| New package installs (lightgbm, mlforecast, duckdb, locust) | Low | Needs downloads | Asked before installing; installed into the project venv only, Lab only |
| 2023 copies inflate counts | Known | Judges notice 2023 | Labelled already; don't quote 2023 totals; the Lab top-up dilutes them further |
| Real officer names on a public link | Your call | Privacy question from a judge | Kept per your decision. Have the answer ready: "Officers, not accused; the Admin can pseudonymise with one setting." Easy to add later |
| Today's date vs as-of 2024 | Known | "Why 2024?" | "The SCRB extract ends in March 2024; we forecast the months the model never saw and show you how close we came." |

---

## 9. Questions left for you

| # | Question | My recommendation |
|---|---|---|
| Q1 | Cloud: exclude the 2,998 synthetic rows dated after today from every count (a filter, not a deletion)? | **Yes.** Future-dated FIRs are the kind of thing a judge spots |
| Q2 | May I install `lightgbm`, `mlforecast`, `duckdb`, `pyarrow` and `locust` into the venv (Lab only, not the Docker image)? | **Yes**, needed for L3 and L5 |
| Q3 | For C1, if the probe allows both, A (read-only register in the image) or B (slim)? | **A**, plus the cheap parts of B (drop duplicate indexes) |
| Q4 | Gold set: should I draft all 150 questions with SQL for you to review, or will you supply some? | **I draft, you review** the Kannada wording |
| Q5 | Commit the Lab work to the same `main` branch, or a `lab` branch? | **Same branch.** Lab-only parts are switched on by settings, so one codebase |
| Q6 | Should the Scale page also appear on Cloud (with recorded numbers only)? | **Yes**, as the Scale card in C2 |

Reply with "go" (and any changes), and I start with C0 → C1.

---

## 10. Research behind the choices

| Topic | Finding | Used in |
|---|---|---|
| Hotspot accuracy metric | PAI (with PEI) is the standard for hotspot maps. An ML comparison on Chicago data reports KDE at PAI 2.64 at 5% coverage | L3 |
| Forecast tooling | Nixtla `mlforecast` runs LightGBM / XGBoost globally with conformal intervals; HierarchicalForecast reconciles levels | L3 |
| Foundation models | TimesFM 2.5 leads Chronos-Bolt on the GIFT-Eval and Chronos II aggregates, but no count-data result exists, so it stays a stretch to test ourselves | L3 stretch |
| Analytics engine | Published comparisons (vendor and blog, not independent) show DuckDB aggregations roughly 8–35× faster than SQLite on large tables, while SQLite stays better for point lookups | L5 |
| Text-to-SQL accuracy | BIRD leaderboard top ≈ 82% execution accuracy; ~93% on the expert-verified Mini-Dev; gold labels themselves have errors, so we write our own ground truth | L4 |
| Entity resolution | Splink (Fellegi-Sunter, DuckDB backend) claims ~1 million records per minute on a laptop; used by the UK MoJ and ONS | Post-event |
| Graph at scale | cosmos.gl / Cosmograph (GPU, WebGL) handles hundreds of thousands to low millions of nodes; it degrades near 5 million | Post-event |
| Map at scale | deck.gl renders millions of points; aggregation layers move work to the GPU; pre-aggregate to H3 for phones | Post-event |
| Kannada | AI4Bharat IndicConformer Kannada ASR (120M, MIT); BGE-M3 leads dense retrieval in 8 of 13 Indic languages | Post-event |
| Local LLM | On a 4 GB GPU only ~4B models fit; CPU gives ~10–25 tok/s on high-end desktops, so slower here. QuickML stays | Decision |
| Sharing a laptop | Cloudflare quick tunnel (no account, random URL), Tailscale Funnel (stable, no login gate), ngrok free (warning page, 1 GB/month) | Not used: Cloud link chosen |
| PII | Presidio supports pseudonymisation with reusable mappings, but needs custom recognisers for Indian names | Option if names are masked later |

**Sources**

- [Hu et al., spatio-temporal KDE and the PAI curve (arXiv 2006.00272)](https://arxiv.org/abs/2006.00272v1)
- [Crime Science 2020: PAI as area-normalised Recall@k](https://doaj.org/article/de166f407ffd4357b558ccc27e0f379c)
- [(Looking) Back to the Future: space-time patterns and PAI](https://research-repository.griffith.edu.au/items/830a0d7a-8f28-5b5a-a3a4-43e3687f6150)
- [RIT thesis: KDE vs RF/GBM/XGBoost, PAI 2.64 at 5%](https://repository.rit.edu/theses/12419)
- [Nixtla mlforecast (PyPI)](https://pypi.org/project/mlforecast/) · [Nixtla ecosystem](https://www.nixtla.io/ecosystem.md)
- [Chronos-2 paper, with TimesFM-2.5 vs Chronos-Bolt tables](https://arxiv.org/pdf/2510.15821) · [LiveHouse-TS benchmark](https://arxiv.org/pdf/2608.17299)
- [MotherDuck: DuckDB vs SQLite](https://motherduck.com/learn-more/duckdb-vs-sqlite-databases) · [KDnuggets: DuckDB, SQLite, pandas on 1M rows](https://kdnuggets.com/we-benchmarked-duckdb-sqlite-and-pandas-on-1m-rows) · [Galaxy benchmark notes](https://www.getgalaxy.io/learn/glossary/duckdb-vs-sqlite-benchmarks)
- [BIRD leaderboard news (DataGallery)](https://technologymagazine.com/news/huawei-datagallery-tops-benchmark-for-enterprise-text2sql-ai) · [ReViSQL (arXiv 2603.20004)](https://arxiv.org/abs/2603.20004v1) · [BIRD gold-label errors](https://beancount.io/bean-labs/research-logs/2026/06/06/bird-benchmark-text-to-sql-real-database-gap)
- [Splink (PyPI)](https://pypi.org/project/splink) · [UK MoJ on Splink](https://www.gov.uk/government/publications/joined-up-data-in-government-the-future-of-data-linking-methods/splink-mojs-open-source-library-for-probabilistic-record-linkage-at-scale)
- [Cosmograph concept](https://cosmograph.app/docs-general/concept/) · [SC25 poster on Cosmograph at 5M nodes](https://sc25.supercomputing.org/proceedings/posters/poster_files/post113s2-file3.pdf)
- [Uber: deck.gl](https://www.uber.com/blog/visualizing-data-sets-deck-gl-framework/) · [deck.gl aggregation layers](https://tessl.io/registry/tessl/npm-deck-gl--aggregation-layers)
- [AIKosh: IndicConformer Kannada ASR](https://aikosh.indiaai.gov.in/home/models/details/ai4bharat_indicconformer_automatic_speech_recognition_asr_model_for_kannada.html) · [IndicRAGSuite (BGE-M3 on Indic retrieval)](https://arxiv.org/pdf/2506.01615)
- [Local LLMs in 2026 on consumer hardware](https://dev.to/studiomeyer_io/local-llms-in-2026-what-actually-works-on-consumer-hardware-50me)
- [Tunnel comparison: Cloudflare, Tailscale, ngrok](https://guides.happier.dev/cloudflare-tunnel-vs-tailscale-funnel-vs-ngrok-for-claude-code-codex-opencode) · [Tailscale on ngrok alternatives](https://tailscale.com/learn/ngrok-alternatives)
- [Microsoft Presidio guide](https://towardsdatascience.com/building-a-customized-pii-anonymizer-with-microsoft-presidio-b5c2ddfe523b)
