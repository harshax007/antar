---
type: Attested Computation
title: "T29 — What links two FIRs: the keys they share (accused, vehicle, UPI ID, IP address, modus operandi, station, district, crime)"
description: "What links two FIRs: the keys they share (accused, vehicle, UPI ID, IP address, modus operandi, station, district, crime)"
runtime: python
parameters:
  - name: fir_a
    type: str
    required: false
  - name: fir_b
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
  at: "2026-10-23T12:47:17Z"
status: stable
---

# T29 — What links two FIRs: the keys they share (accused, vehicle, UPI ID, IP address, modus operandi, station, district, crime)

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* what links FIR PRF-2025-909767 and FIR PRF-2025-909775

## Computation

`app/services/zcql_repo.py::TEMPLATES['T29']` builds a `QuerySpec` from the validated `FirPair` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
