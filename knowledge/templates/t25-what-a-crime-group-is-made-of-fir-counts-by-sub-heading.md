---
type: Attested Computation
title: "T25 — What a crime group is made of: FIR counts by sub-heading (two-wheeler, house theft, jewellery, extortion …) or by day vs night"
description: "What a crime group is made of: FIR counts by sub-heading (two-wheeler, house theft, jewellery, extortion …) or by day vs night"
runtime: python
parameters:
  - name: crime_types
    type: list of str
    required: false
  - name: zones
    type: list of str
    required: false
  - name: stations
    type: list of str
    required: false
  - name: heads
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
  - name: by
    type: "Literal of 'head', 'group'"
    required: false
  - name: limit
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
  at: "2026-10-23T12:47:17Z"
status: stable
---

# T25 — What a crime group is made of: FIR counts by sub-heading (two-wheeler, house theft, jewellery, extortion …) or by day vs night

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* what share of thefts are two-wheelers
* breakdown of theft by type
* are burglaries more frequent by night or by day

## Computation

`app/services/zcql_repo.py::TEMPLATES['T25']` builds a `QuerySpec` from the validated `SubHeadBreakdown` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
