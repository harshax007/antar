---
type: Attested Computation
title: T3 — Monthly crime trend (count per month)
description: Monthly crime trend (count per month)
runtime: python
parameters:
  - name: crime_types
    type: list of str
    required: false
  - name: zones
    type: list of str
    required: false
  - name: months
    type: int
    required: false
  - name: date_from
    type: str
    required: false
  - name: date_to
    type: str
    required: false
  - name: real_only
    type: bool
    required: false
  - name: stations
    type: list of str
    required: false
  - name: heads
    type: list of str
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
  at: "2026-10-23T12:47:17Z"
status: stable
---

# T3 — Monthly crime trend (count per month)

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* robbery trend in Bengaluru North last 3 months
* theft trend this year

## Computation

`app/services/zcql_repo.py::TEMPLATES['T3']` builds a `QuerySpec` from the validated `TrendByMonth` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
