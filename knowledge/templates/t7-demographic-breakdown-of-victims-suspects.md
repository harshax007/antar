---
type: Attested Computation
title: T7 — Demographic breakdown of victims/suspects
description: Demographic breakdown of victims/suspects
runtime: python
parameters:
  - name: entity
    type: "Literal of 'victims', 'suspects'"
    required: false
  - name: dimension
    type: "Literal of 'age_band', 'gender', 'occupation', 'zone', 'address_zone'"
    required: false
executor:
  resource: /app/services/zcql_repo.py
  receipt:
    - template_id
    - params
    - row_ids
    - rows
attester:
  resource: /app/agents/agentic_spine.py
tags:
  - query-template
  - deterministic
  - whitelist
generated:
  by: process:antar-okf-export
  at: "2026-09-24T22:09:48Z"
status: stable
---

# T7 — Demographic breakdown of victims/suspects

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* age and gender of theft victims
* victim gender breakdown

## Computation

`app/services/zcql_repo.py::TEMPLATES['T7']` builds a `QuerySpec` from the validated `DemographicBreakdown` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
