---
type: Agent
title: geo — Lens - geo intelligence
description: Lens - geo intelligence
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

# geo — Lens - geo intelligence

Runs as graph node `forecast`. Hosted inside `forecast`'s node.

* **Module**: `app/agents/geo_agent.py::geo_agent_run`
* **Routes**: GEO
* **Guardrails**: date_guard
* **Human approval required**: no

**When it fails**: beat suggestions omitted; map falls back to unfiltered density

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
