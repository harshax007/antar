---
type: Dataset
title: Karnataka State Police FIR registry
description: 1,000,000 First Information Reports, 2016-2026.
resource: urn:antar:registry:firs
tags:
  - dataset
  - fir
  - ksp
generated:
  by: process:antar-okf-export
  at: "2026-10-24T15:11:40Z"
sources:
  - id: ksp-fir-registry
    resource: urn:antar:registry:firs
    title: KSP FIR registry
    author: process:antar-okf-export
    usage_count: 1000000
status: stable
---

# Karnataka State Police FIR registry

The record everything else in Antar stands on.

| | |
|---|---:|
| FIRs | 1,000,000 |
| Years | 2016-2026 |
| Districts | 41 |
| Police stations | 1,155 |
| Crime groups | 113 |
| Distinct act strings | 259 |

## What this record does not contain

Stated here because a knowledge bundle that only lists strengths is marketing.

* **No event times.** FIRs carry a date, not a time of day. This is why the forecast is a
  weekly panel, and why a near-repeat triggering kernel was measured and rejected - see
  [the forecast model card](/forecast-model-card.md).
* **MO narrative on 651 rows** of 1,000,000. See
  [the MO vocabulary](/vocabulary/modus-operandi.md).
* **No accused-identity column** in the raw extract, so person-level linkage is derived,
  never asserted from a key the registry does not have.

## How it is queried

Never with free-form SQL. Questions resolve to one of the whitelisted
[query templates](/templates/index.md), or they are refused.
