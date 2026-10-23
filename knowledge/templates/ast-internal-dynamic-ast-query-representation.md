---
type: Attested Computation
title: AST — (internal) Dynamic AST query representation
description: (internal) Dynamic AST query representation
runtime: python
parameters:
  - name: ast
    type: app.services.zcql_repo.ZCQLQueryAST
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

# AST — (internal) Dynamic AST query representation

A whitelisted, parameterised query over the FIR registry. Antar never executes free-form SQL: an officer's question is resolved to one of these templates, or it is refused.

## Questions this answers

* (internal)

## Computation

`app/services/zcql_repo.py::TEMPLATES['AST']` builds a `QuerySpec` from the validated `ASTParams` parameter model. The spec is compiled to parameterised SQL — every value is bound, never interpolated.

## Attestation

The receipt fields below are what a run must return for its result to be checkable: the template that answered, the bound parameters, and the row ids behind the number. `app/agents/agentic_spine.py::verify_claims` is the deterministic attester — it re-checks every figure in an answer against those rows, with no model in the loop.

*Internal template: used by analytics and scans, hidden from the selector.*
