---
type: Attested Computation
title: T20 — All FIRs linked to one UPI ID, IP address or modus-operandi code (identifier lookup)
description: All FIRs linked to one UPI ID, IP address or modus-operandi code (identifier lookup)
runtime: python
parameters:
  - name: value
    type: str
    required: false
  - name: key_type
    type: "Literal of 'any', 'upi', 'ip', 'vehicle', 'accused', 'mo'"
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

# T20 — All FIRs linked to one UPI ID, IP address or modus-operandi code (identifier lookup)

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* FIRs for UPI user1101@bank
* cases linked to IP 103.87.106.22
* FIRs sharing modus operandi MO-A1-festival-lockedhouse

## Computation

`app/services/zcql_repo.py::TEMPLATES['T20']` builds a `QuerySpec` from the validated `IdentifierLookup` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
