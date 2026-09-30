# Map Forecasting — Implementation Plan (USP #2)

**Status:** Phases 1–6 built (2026-09-19); Phase 7 remains · see PROGRESS.md "Map forecasting — where it stands"
**Written:** 2026-09-18 · **For:** a new working session
**Branch:** `feat/agent-manifest-adversarial-review` · **Last commit when written:** `38e1084`

---

## 0. Start here (new session)

Paste this to begin:

> Read `docs/MAP_FORECASTING_PLAN.md`, `docs/ANTAR_CONSTITUTION.md` and `PROGRESS.md`.
> Confirm the four decisions in §3 with me, then implement Phase 1 onwards. Stop and ask
> after each phase. Run `python -m pytest -q` before every commit.

Context the new session needs:

- **Registry:** `main.db`, exactly 1,000,000 FIRs. The **real** KSP record ends
  **2024-03-10** (and its last month is truncated at 9.5k FIRs vs ~31k). Everything dated
  2025-01 → 2026-12 is seeded demo data (`is_synthetic_row = 1`, ~1.5k/month).
- **Antar's constitution** applies: a forecast is an **Inferred (I)** claim — calibrated
  words, stated basis, never about an individual, the officer decides.
- **Don't run two test suites at once** against `main.db` (see PROGRESS.md §7).
- The backend on `:8000` must be restarted to pick up backend changes.

---

## 1. The goal

An officer opens the map and gets, for next week:

> **"Where is crime most likely next week, how sure are we, and why?"** — at the level they
> actually deploy (police station and beat), with a measured accuracy they can trust, and a
> one-click route to *propose* a patrol through the existing approval flow.

The demo moment: *"The top 5% of beats caught 52% of next week's property crime in back-testing
— 10 points more than last month's hotspots, in every one of 23 weeks. Here's why each one is
flagged. Propose a patrol →"* (measured in Phase 3; statewide beat figures — a Mysuru-only
figure would need its own run).

---

## 2. What exists today — audit

### Worth keeping

| Asset | Where |
|---|---|
| Anomaly scan: MAD-z + seasonal residual + Bayesian reporting-silence check | `app/services/anomaly.py` `scan()` |
| Getis-Ord **Gi\*** spatial hotspot significance | `anomaly.py` `gi_star_surface()` (L532) |
| Split-**conformal** prediction bands (90%) | `anomaly.py` `_conformal_band()`, `forecast_band()` |
| ST-DBSCAN clustering, KDE contours | `app/services/geo_density.py` (`compute_kde_geojson` L128) |
| Prediction board / dashboard / scenario / reasoning endpoints | `app/api/pattern_predict.py` |
| Map endpoints (districts, heat, Gi\*, dark zones, anchor areas) | `app/api/map_api.py` |
| **HITL `patrol_redeployment` action** — the natural "act on a forecast" path | `app/core/hitl.py` L149 |
| Map and Predict screens | `antar-frontend/components/MapScreen.jsx`, `app/(app)/predict/PredictScreen.jsx` |

### Broken or misleading — must fix before demoing

| # | Problem | Where | Why it matters |
|---|---|---|---|
| A1 | **Every window anchors to the wall clock**, so it lands entirely in the seeded 2025-26 band | `anomaly.py` L349, L552, L630 · `map_api.py` L144, L170, L194 | Forecasts describe ~1.5k demo rows/month, not the real ~31k/month record. Same bug already fixed for trend lines (commit `424a7f5`). |
| A2 | **`/api/map/predicted` is not a prediction** — it returns the 3 zones with the most crime *this calendar month* | `map_api.py` L165-209 | Labelled "predicted hotspots". |
| A3 | **Fabricated "Surge detected … increase patrols"** text — no surge is measured | `map_api.py` L208 | A recommendation with no basis — breaks Law 2. |
| A4 | `/predicted` reads `monthly_trend`, a precomputed table covering only **2024-01 → 2026-06** and mixing seeded sub-zones | `map_api.py` L174 | Stale and mostly synthetic. |
| A5 | **Model card describes a model that doesn't run** ("DBSCAN + 30-day velocity"); the real engine is MAD-z + seasonal + Gi\* + conformal | `pattern_predict.py` L443-461 | Misrepresents the system to officers and judges. |
| A6 | Model card claims **"CCTNS live replica (updated nightly)"** | `pattern_predict.py` L460 | False provenance. |
| A7 | **Hardcoded `3.0–7.0 @ 90%` band** when no alert exists | `pattern_predict.py` L320 | Invented numbers presented as a confidence interval. |
| A8 | **No forecast accuracy has ever been measured** — no backtest anywhere | — | Can't claim a forecast works; judges will ask. |
| A9 | **14,512 FIRs have impossible coordinates** (lat up to 131, lon up to 777, zeros) | `FIRs.lat_r / lon_r` | Garbage points and distorted KDE/Gi\*. |
| A10 | Zones mix 41 real districts with seeded sub-zones (Rajajinagar, Indiranagar…) | `zone_summary` (56 rows) | Seeded zones have no arrest data and no real history. |

### Data realities

| Fact | Value | Consequence |
|---|---|---|
| Real FIRs with coordinates | **391,054 (41%)**, 52,610 distinct 0.01° cells | Enough for beat- and grid-level work |
| …by year | 2023: 192k · 2024: 70k · 2019–22: 21–34k · 2016–18: 5–7k | Train on 2019+; 2023–24 is the dense core |
| Real stations / beats | **1,054 / 6,384** | Beat is the operational unit — forecast here |
| Time of day | **Not in the data** (date only) | Never claim hour-of-day patterns; day-of-week at most |
| Real horizon | 2024-03-10 | "Next week" = the week after the as-of date |

---

## 3. Decisions to confirm at the start (recommendations first)

| # | Decision | Recommended | Alternatives |
|---|---|---|---|
| **D1** | **As-of date** for forecasts | **Real horizon — "as of 10 Mar 2024"**, shown on screen. Forecasts are then back-testable and honest. | Wall clock → forecasts built on seeded data; keeps the planted Rajajinagar "WOW-3" spike story |
| **D2** | **Spatial unit** | **Police station → beat** (drill-down), with a 1-km grid only as a heat layer | District only (too coarse to act on) · grid only (not how officers deploy) |
| **D3** | **Horizons** | **Next 7 days and next 28 days** | 7 only · add 90 |
| **D4** | **What is forecast** | **FIR count per beat per week, by crime category** (the 16 categories in `lib/crimeGraph.js`) | All crime only · individual crime heads |

D1 is the one that changes the demo narrative — ask it first.

---

## 4. Design

### 4.1 Data layer (Phase 1)

1. **Coordinate hygiene** — flag, don't delete: add `geo_ok` (Karnataka bbox 11.5–18.5 N,
   74.0–78.6 E; also try the lat/lon swap and accept it if it lands inside). Every spatial
   query uses `geo_ok = 1`. Record the counts in PROGRESS.md.
2. **Beat & station centroids** — `geo_units(unit_type, unit_name, district, lat, lon, n_firs)`
   as the median of `geo_ok` points (median, not mean — robust to stray points).
3. **Weekly cube** — materialised table `forecast_cube(unit, unit_type, category, week_start,
   n)` over **real rows only** (`is_synthetic_row = 0`), ISO weeks. This is what makes every
   forecast query instant; rebuild on ingest. Index `(unit_type, category, week_start)`.
4. Code-owned, created in `zcql_local.ensure_indexes()` style so the deployed DB self-builds.

### 4.2 Model (Phase 2) — defensible over clever

Standard in the crime-forecasting literature and cheap on CPU:

| Layer | What | Why |
|---|---|---|
| **Baseline** | Seasonal-naive + EWMA per unit × category | The bar any model must beat; reported beside it |
| **Model** | **Negative-binomial GLM** per category, features: counts in last 1 / 4 / 13 weeks, same week last year, week-of-year seasonality, **spatial lag** (neighbouring beats' last-4-week counts), unit fixed effect via shrinkage | Count data with over-dispersion; interpretable coefficients → "why" per forecast |
| **Uncertainty** | Reuse split-conformal (`anomaly._conformal_band`) on held-out residuals → honest 80/90% bands | Already in the codebase; calibrated, distribution-free |
| **Significance** | Keep **Gi\*** as a separate "confirmed cluster" layer, re-anchored to the as-of date | Distinguishes "busy" from "statistically clustered" |

No deep learning — the explanations and the backtest matter more than a few points of fit.
**`statsmodels` is not installed** — don't add it. `scikit-learn` 1.4 (`PoissonRegressor`,
`TweedieRegressor`), `scipy` 1.12 and `numpy` 1.26 are already in `requirements.txt`: fit a
Poisson/Tweedie GLM with sklearn and estimate the NB dispersion from residuals with scipy.

### 4.3 Evaluation (Phase 3) — the credibility layer

Rolling-origin backtest over **Oct 2023 → Feb 2024** (train strictly before each origin,
forecast the next 7 / 28 days):

| Metric | What it tells an officer |
|---|---|
| **PAI** — Predictive Accuracy Index (Chainey): % of crime caught ÷ % of area flagged | *The* standard for hotspot forecasts. "Top 5% of area caught X% of crime." |
| **Hit rate** at top 5% / 10% of beats | Plain-language version of PAI |
| **MAE** per station vs the baseline | Is the model actually better than "same as last month"? |
| **Interval coverage** | Do the 90% bands contain the outcome ~90% of the time? |

Results go into a real model card (replacing A5/A6) and `docs/golden_report`-style output,
regenerated by a script, never typed by hand.

### 4.4 API (Phase 4)

| Endpoint | Returns |
|---|---|
| `GET /api/forecast/hotspots?horizon=7&category=&district=&unit=beat` | Ranked units: expected count, 90% band, rank, **drivers** (top 3 model terms in words), Gi\* flag, evidence class `I`, as-of date |
| `GET /api/forecast/unit/{unit}` | One beat: 26-week history + forecast + band, drivers, top crime heads |
| `GET /api/forecast/backtest` | PAI / hit-rate / MAE / coverage per category & horizon |
| `GET /api/predict/model-card` | **Generated** from the backtest + actual model config |

Fix or retire `/api/map/predicted` (A2–A4): redirect its callers to `/api/forecast/hotspots`.
Remove the hardcoded band (A7): no alert → no band, and the UI says "not enough history".

### 4.5 Map UI (Phase 5)

- **As-of chip** always visible: "Forecast as of 10 Mar 2024 · next 7 days".
- **Layers** (toggle): Forecast risk (beats shaded by expected count, quantile colour scale) ·
  Confirmed clusters (Gi\*) · Recent FIRs (points, `geo_ok` only).
- **Controls:** horizon 7 / 28 · category · district.
- **Beat card** on click: expected range (*"likely 9–14 thefts"* — ICD 203 wording), the
  drivers in plain words, 26-week sparkline with the band, top crime heads, the beat's
  backtest hit rate, and **Propose patrol** → HITL `patrol_redeployment` with the forecast
  attached as the justification.
- **Accuracy strip:** "Back-tested on Oct 2023 – Feb 2024: top 5% of beats caught X% of crime
  (PAI Y)". Links to the model card.
- Constitution: every forecast number carries the **Inferred** badge; no hour-of-day claims.

### 4.6 Chat (Phase 6)

"Where should I patrol next week in Mysuru?" / "theft forecast for Bengaluru City" →
new template reading `/api/forecast/hotspots`; bottom line in ICD 203 language, top 5 beats as
evidence, as-of and backtest accuracy as context, `I` badge. Follows the resolve-or-refuse
contract (unknown place or category → refuse, never widen).

---

## 5. Phases, acceptance criteria, estimates

| Phase | Deliverable | Done when | Est. |
|---|---|---|---|
| **1. Data** | `geo_ok`, `geo_units`, `forecast_cube` | Cube rebuilds in < 60 s; 0 spatial queries read `geo_ok = 0`; counts reconcile exactly with `FIRs` for 3 sampled beats | 2 h |
| **2. Model** | Baseline + NB-GLM + conformal bands | Fits all categories in < 2 min on CPU; beats baseline MAE on held-out weeks | 3 h |
| **3. Evaluation** | Backtest script + generated model card | PAI, hit rate, MAE, coverage per category; A5/A6/A8 closed | 2 h |
| **4. API** | `/api/forecast/*`; A1–A4, A7 fixed | p95 < 300 ms from the cube; every forecast carries as-of + class `I` | 2 h |
| **5. Map UI** | Layers, beat card, accuracy strip, Propose patrol | Clicking a beat → card in < 300 ms; Propose patrol lands in Approvals with the forecast attached | 4 h |
| **6. Chat** | Forecast template in chat | Golden questions below pass; refusals for unknown places | 1.5 h |
| **7. Hardening** | Tests, PROGRESS.md, demo script lines | Full suite green; demo walkthrough rehearsed | 1.5 h |

**Total ≈ 16 h.** If time is short, Phases 1–4 + a minimal beat card are the honest core;
the rest is presentation.

---

## 6. Tests to write

- `tests/test_forecast_data.py` — `geo_ok` excludes out-of-bbox points; cube totals equal
  `COUNT(*)` for sampled units/weeks; no synthetic rows in the cube.
- `tests/test_forecast_model.py` — deterministic fit on a fixture; bands contain the point
  forecast; model beats the seasonal-naive baseline on a held-out fixture.
- `tests/test_forecast_api.py` — every item has `as_of`, `evidence_class == "I"`, `band.lo ≤
  expected ≤ band.hi`; no hardcoded band when history is thin; unknown district refuses.
- `tests/test_model_card.py` — the card's metrics equal the latest backtest output (so it can
  never drift from reality again).
- Golden chat questions: *"where should I patrol next week in Mysuru"*, *"theft forecast
  Bengaluru City next 4 weeks"*, *"ಮುಂದಿನ ವಾರ ಮೈಸೂರಿನಲ್ಲಿ ಕಳ್ಳತನ ಎಲ್ಲಿ"*, *"forecast for
  Indiranagar"* (→ honest: no real history).

---

## 7. Guardrails (constitution)

- **Places and times, never people.** No individual risk scores, no "who will offend".
- **Show uncertainty every time** — a band, not just a number.
- **Show accuracy** — the backtest is part of the product, not an appendix.
- **Reporting ≠ crime.** Note in the model card and beat card: forecasts reflect *reported*
  FIRs; under-reporting areas can look safe (the existing Bayesian silence check helps flag this).
- **Feedback-loop caution.** Patrol where it's flagged → more FIRs recorded there → flagged
  again. State it in the model card; recommend rotating in low-forecast beats.
- **The officer decides.** The map proposes; HITL approves.

---

## 8. Demo lines (numbers measured in Phase 3 — `docs/FORECAST_BACKTEST.md`)

> "This isn't 'where crime was last month'. It's a forecast for next week, at the beat level
> officers actually patrol — as of the last day of the real record."
>
> "Every number is a range, not a guess, and it's labelled Inferred. Tap a beat and it tells
> you why: recent weeks, last year's same week, and what the neighbouring beats are doing."
>
> "We back-tested it the way the field does — Predictive Accuracy Index. On five months the
> model never saw, the top 5% of beats caught 40% of the next week's crime — 52% for
> property crime, against 42% for last month's hotspots, better in 23 weeks out of 23.
> Flagging 5% of the land caught 71% of crime: a PAI of 14."
>
> "And it doesn't act. It proposes a patrol; a supervising officer approves it."

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Real data ends 2024-03 — "next week" is in the past | Own it: "as of" chip; it's what makes the backtest possible |
| Sparse beats (few FIRs) give noisy forecasts | Shrink toward station level; show "insufficient history" rather than a number |
| NB fit fails to converge for rare categories | Fall back to the baseline and say so in the card |
| Seeded demo zones appear on the map | Exclude from the cube; show them only on the existing synthetic-narrative views if D1 keeps them |
| Map performance with 6k beats | Serve from the cube; vector tiles or simplified GeoJSON; lazy-load points |
