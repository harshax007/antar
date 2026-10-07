---
type: Attested Computation
title: T8 — Crime counts by investigation status (filter by zone, crime type and period)
description: Crime counts by investigation status (filter by zone, crime type and period)
runtime: python
parameters:
  - name: zones
    type: list of str
    required: false
  - name: crime_types
    type: list of str
    required: false
  - name: date_from
    type: str
    required: false
  - name: date_to
    type: str
    required: false
  - name: period
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
  at: "2026-10-07T00:58:49Z"
status: stable
---

# T8 — Crime counts by investigation status (filter by zone, crime type and period)

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* how many cases are open in Jayanagar
* open theft cases by status in 2024

## Computation

`app/services/zcql_repo.py::TEMPLATES['T8']` builds a `QuerySpec` from the validated `CountByStatus` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
