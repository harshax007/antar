---
type: Attested Computation
title: "T24 — Case stages and pendency: cases under investigation, pending trial, convicted, and how long open investigations have been open, by police station, district or crime type"
description: "Case stages and pendency: cases under investigation, pending trial, convicted, and how long open investigations have been open, by police station, district or crime type"
runtime: python
parameters:
  - name: zones
    type: list of str
    required: false
  - name: stations
    type: list of str
    required: false
  - name: crime_types
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
  - name: dimension
    type: "Literal of 'none', 'station', 'district', 'crime_type'"
    required: false
  - name: older_than_days
    type: int
    required: false
  - name: order
    type: "Literal of 'desc', 'asc'"
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

# T24 — Case stages and pendency: cases under investigation, pending trial, convicted, and how long open investigations have been open, by police station, district or crime type

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* stations with the most pending investigations in Mysuru
* cases under investigation for more than 90 days in Bengaluru City
* how many POCSO cases reached trial stage in 2023

## Computation

`app/services/zcql_repo.py::TEMPLATES['T24']` builds a `QuerySpec` from the validated `CaseStages` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
