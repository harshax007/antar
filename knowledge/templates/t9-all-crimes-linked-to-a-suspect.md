---
type: Attested Computation
title: T9 — All crimes linked to a suspect
description: All crimes linked to a suspect
runtime: python
parameters:
  - name: suspect_id
    type: str
    required: true
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

# T9 — All crimes linked to a suspect

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* what crimes is S0001 linked to

## Computation

`app/services/zcql_repo.py::TEMPLATES['T9']` builds a `QuerySpec` from the validated `SuspectCrimes` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
