---
type: Attested Computation
title: T16 — Overall yearly summary and total FIR counts for a specific year
description: Overall yearly summary and total FIR counts for a specific year
runtime: python
parameters:
  - name: year
    type: int
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
  at: "2026-10-07T00:58:49Z"
status: stable
---

# T16 — Overall yearly summary and total FIR counts for a specific year

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* Cognizable FIRs registered in Karnataka in 2023?
* what happened in 2022
* summary of 2021

## Computation

`app/services/zcql_repo.py::TEMPLATES['T16']` builds a `QuerySpec` from the validated `YearSummary` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
