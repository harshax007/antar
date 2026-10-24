---
type: Attested Computation
title: T21 — Full FIR history of one accused ID across districts, with arrests, charge-sheets and convictions
description: Full FIR history of one accused ID across districts, with arrests, charge-sheets and convictions
runtime: python
parameters:
  - name: accused_id
    type: str
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
  at: "2026-10-24T15:11:41Z"
status: stable
---

# T21 — Full FIR history of one accused ID across districts, with arrests, charge-sheets and convictions

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* cases for accused ACC-KA-500777
* history of ACC-KA-102883

## Computation

`app/services/zcql_repo.py::TEMPLATES['T21']` builds a `QuerySpec` from the validated `AccusedHistory` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
