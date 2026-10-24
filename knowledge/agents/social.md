---
type: Agent
title: social — Sense - demographic insight
description: Sense - demographic insight
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

# social — Sense - demographic insight

Runs as graph node `social`.

* **Module**: `app/agents/social_agent.py::demographics`
* **Routes**: SENSE, SOCIAL
* **Guardrails**: evaluate_bias, aggregate_only
* **Human approval required**: no

**When it fails**: omitted from synthesis

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
