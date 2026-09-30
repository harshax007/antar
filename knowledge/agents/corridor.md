---
type: Agent
title: corridor — Corridor intelligence compiler
description: Corridor intelligence compiler
tags:
  - agent
  - worker
generated:
  by: process:antar-okf-export
  at: "2026-09-24T22:09:49Z"
sources:
  - id: antar-agent-manifest
    resource: /AGENTS.md
    title: Antar agent manifest
    author: process:antar-okf-export
status: stable
---

# corridor — Corridor intelligence compiler

No graph node — API and autonomous surfaces only.

* **Module**: `app/agents/corridor_agent.py::compile_corridors`
* **Guardrails**: verify_claims, date_guard
* **Human approval required**: no

**When it fails**: last compiled corridor set served with its original timestamp

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
