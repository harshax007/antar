---
type: Agent
title: synthesize — Answer composition and claim verification
description: Answer composition and claim verification
tags:
  - agent
  - system
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

# synthesize — Answer composition and claim verification

Runs as graph node `synthesize`.

* **Module**: `app/agents/graph.py::synthesize_node`
* **Routes**: CHITCHAT
* **Guardrails**: verify_claims, G1_numbers, G2_no_result_honesty, G4_slop, G6_length
* **Human approval required**: no

**When it fails**: deterministic _synthesize() when the LLM merge fails - always available

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
