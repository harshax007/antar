---
type: Attested Computation
title: T1 — List crimes by type / zone / date range
description: List crimes by type / zone / date range
runtime: python
parameters:
  - name: crime_types
    type: list of str
    required: false
  - name: zones
    type: list of str
    required: false
  - name: status
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
  - name: arrest_status
    type: str
    required: false
  - name: stations
    type: list of str
    required: false
  - name: heads
    type: list of str
    required: false
  - name: limit
    type: int
    required: false
  - name: order
    type: "Literal of 'desc', 'asc'"
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
  at: "2026-10-25T17:33:50Z"
status: stable
---

# T1 — List crimes by type / zone / date range

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* chain snatching in Rajajinagar last month
* show robberies in Bengaluru North

## Computation

`app/services/zcql_repo.py::TEMPLATES['T1']` builds a `QuerySpec` from the validated `TypeZonePeriod` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
