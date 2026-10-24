---
type: Attested Computation
title: "T19 — Identifiers (UPI ID, IP address, vehicle, accused ID) shared by FIRs in several districts: cross-station links"
description: "Identifiers (UPI ID, IP address, vehicle, accused ID) shared by FIRs in several districts: cross-station links"
runtime: python
parameters:
  - name: key_type
    type: "Literal of 'any', 'upi', 'ip', 'vehicle', 'accused', 'mo'"
    required: false
  - name: min_districts
    type: int
    required: false
  - name: zones
    type: list of str
    required: false
  - name: between
    type: list of str
    required: false
  - name: crime_types
    type: list of str
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
  at: "2026-10-24T15:11:41Z"
status: stable
---

# T19 — Identifiers (UPI ID, IP address, vehicle, accused ID) shared by FIRs in several districts: cross-station links

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* which UPI IDs are used in more than one district
* accused who appear across multiple districts
* vehicles linked to FIRs in 3 or more districts

## Computation

`app/services/zcql_repo.py::TEMPLATES['T19']` builds a `QuerySpec` from the validated `SharedIdentifiers` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
