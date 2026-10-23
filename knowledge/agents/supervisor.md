---
type: Agent
title: supervisor — Intent classification and routing
description: Intent classification and routing
tags:
  - agent
  - system
generated:
  by: process:antar-okf-export
  at: "2026-10-23T12:47:17Z"
sources:
  - id: antar-agent-manifest
    resource: /AGENTS.md
    title: Antar agent manifest
    author: process:antar-okf-export
status: stable
---

# supervisor — Intent classification and routing

Runs as graph node `supervisor`.

* **Module**: `app/agents/supervisor.py::supervisor_node`
* **Guardrails**: zero_assumption
* **Human approval required**: no

**When it fails**: falls back to VAULT only; confidence below 0.8 also collapses to VAULT

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
