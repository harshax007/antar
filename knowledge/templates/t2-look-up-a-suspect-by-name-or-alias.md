---
type: Attested Computation
title: T2 — Look up a suspect by name or alias
description: Look up a suspect by name or alias
runtime: python
parameters:
  - name: name_or_alias
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
  at: "2026-10-07T00:58:49Z"
status: stable
---

# T2 — Look up a suspect by name or alias

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* who is Raju K
* find suspect Yellappa

## Computation

`app/services/zcql_repo.py::TEMPLATES['T2']` builds a `QuerySpec` from the validated `SuspectLookup` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

Reachable from chat, `/api/chat` and `/api/chat/stream`.
