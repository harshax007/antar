---
type: Agent
title: query — Vault - template query
description: Vault - template query
tags:
  - agent
  - worker
generated:
  by: process:antar-okf-export
  at: "2026-10-24T15:11:42Z"
sources:
  - id: antar-agent-manifest
    resource: /AGENTS.md
    title: Antar agent manifest
    author: process:antar-okf-export
status: stable
---

# query — Vault - template query

Runs as graph node `query`.

* **Module**: `app/agents/query_agent.py::query_agent_run`
* **Routes**: VAULT, QUERY, EXPLAIN
* **Guardrails**: G1_numbers, G2_no_result_honesty, G3_identifiers, G4_slop, G6_length, date_guard, zero_assumption
* **Human approval required**: no

**When it fails**: self_heal escalation; honest dead-end with nearest-match hint if every stage misses

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
