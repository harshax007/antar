# Near-repeat / self-excitation — measured, and NOT shipped

Measured 2026-09-23 · `scripts/ab_near_repeat.py` · raw arms in `near-repeat-ab.json`
Supports `final_backend.md` §6 P1-1.

## The hypothesis

Crime is partly self-exciting: an offence raises short-term risk *nearby*. Mohler, Short,
Brantingham, Schoenberg & Tita (*Self-Exciting Point Process Modeling of Crime*, JASA
106(493), 2011) report that with **10% of a city flagged, a point process caught 660 of
2,627 crimes against 547 for a prospective hotspot map** — about +21%, and it held even
where near-repeat effects are weaker. It is the best-evidenced improvement in this
literature, so it was worth testing against Antar's forecast.

## What was actually implementable

Antar's panel is **weekly counts per unit**, so a continuous space-time triggering kernel
is not available without a second data path. The part of the effect the weekly panel does
carry, and that no existing feature encodes, is short-horizon **spatial** spillover:

  `nbr1` = neighbours' **last week**, against their usual level

against the existing `nbr` = neighbours' **four-week mean**, which smooths away exactly
the spike a near-repeat is. Implemented in `app/forecast/features.py` behind
`ANTAR_FORECAST_NEAR_REPEAT`, entering the design as one more log-ratio column and, when
on, one more driver the officer sees.

## The result: no measurable effect

Both arms ran the full rolling back-test — same 23 weekly origins, same refit schedule,
same PAI and hit-rate definitions, real record only.

| Slice | Metric | Without | With | Δ |
|---|---|---|---|---|
| beat · all crime | top-5% caught | 0.4038 | 0.4039 | +0.0001 |
| beat · all crime | PAI @ 5% | 14.24 | 14.23 | −0.01 |
| beat · all crime | weeks beating last-4 | 22 / 23 | 22 / 23 | 0 |
| beat · property | top-5% caught | 0.5199 | 0.5196 | −0.0003 |
| beat · property | PAI @ 5% | 15.92 | 15.92 | 0 |
| station · all crime | top-5% caught | 0.2286 | 0.2286 | 0 |
| station · all crime | weeks beating last-4 | 14 / 23 | 15 / 23 | +1 |
| station · property | top-5% caught | 0.3275 | 0.3279 | +0.0004 |

**Across 60 metrics: 0 materially improved, 0 materially worsened, 60 within noise.**
("Material" is ≥0.005 on a hit rate, ≥0.25 PAI, ≥2 weeks — anything smaller is not
evidence on a 23-week window.) Fitting was also **12% slower** (390.9 s against 349.1 s).

## Why it did nothing here, honestly

The near-repeat effect lives at the scale of **days and hundreds of metres** — Mohler's
model is a continuous space-time point process over individual events. Antar's cube is
weekly counts over stations and beats, and the neighbour operator is a k-NN average (6
nearest within 3 km for beats). At that resolution `nbr1` is largely collinear with
features the model already has — `recent1` for the unit's own spike and `nbr` for the
neighbourhood level — so the GLM has no new information to extract.

This is a **data-resolution limit, not a modelling failure**. The registry has dates but
no times (`docs/MAP_FORECASTING_PLAN.md` §2), and 41% of FIRs carry usable coordinates.
A genuine triggering kernel would need event-level space-time points, which is a data
question before it is a model question.

## Decision

**Not shipped.** `ANTAR_FORECAST_NEAR_REPEAT` stays off; the forecast is unchanged, and
`docs/FORECAST_BACKTEST.md` keeps its published numbers because the baseline arm
reproduced them exactly (top-5% 0.4038, PAI 14.24, 22/23 weeks — matching `PROGRESS.md`).

The code stays behind the flag rather than being deleted: it is the honest starting point
if event-level times or finer coordinates ever arrive, and re-testing it is then one
command.

> A plausible-sounding feature that does not measure is exactly what a back-test exists to
> catch. The value here was the rejection, not the feature.
