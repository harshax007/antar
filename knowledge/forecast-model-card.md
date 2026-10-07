---
type: Model Card
title: Weekly crime forecast - model card
description: Poisson GLM with split-conformal ranges, judged on a rolling 23-week back-test.
tags:
  - model-card
  - forecast
  - conformal
generated:
  by: process:antar-okf-export
  at: "2026-10-07T00:58:48Z"
sources:
  - id: rolling-back-test-report
    resource: /docs/FORECAST_BACKTEST.md
    title: Rolling back-test report
    author: process:antar-okf-export
status: stable
stale_after: "2027-09-18T20:31:56Z"
---

# Weekly crime forecast - model card

Poisson GLM over a weekly panel of counts per unit, with **split-conformal** prediction
ranges and a Getis-Ord Gi* hotspot term. Judged on a rolling back-test over 23 weekly
origins - the same protocol every time, so numbers stay comparable across changes.

| Measure | Value |
|---|---|
| Top-5% of beats catches | 741 |
| PAI @ 5% | . |
| Weeks beating the last-4 baseline | 22/23 |

## What was tried and rejected

A **near-repeat / self-exciting** term, the best-evidenced improvement in this literature
(Mohler et al., JASA 2011). Measured on the same back-test: **0 of 60 metrics moved**, and
fitting was 12% slower. Weekly counts over beats cannot express a day-and-metre triggering
kernel - a data-resolution limit, not a modelling failure. The code stays behind a flag
that is off.

This section is in the model card on purpose. A card that lists only what worked tells you
nothing about how the thing was decided.

## Limits an officer should know

* The record ends **2024-03**; anything later is seeded and labelled as such.
* Beat areas are Voronoi estimates - no beat boundaries exist in the data - so PAI is
  approximate and labelled approximate.
* Patrolling a flagged beat records more FIRs there. The feedback loop is stated on every
  beat card, and rotating patrols is the recommendation.

Full report: `docs/FORECAST_BACKTEST.md` in the Antar repository.
