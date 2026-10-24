---
type: Agent
title: sentinel — Breach - watchlist tripwires
description: Breach - watchlist tripwires
tags:
  - agent
  - service
  - hitl
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

# sentinel — Breach - watchlist tripwires

No graph node — API and autonomous surfaces only.

* **Module**: `app/agents/sentinel_agent.py::scan_watches`
* **Guardrails**: vigil, redact_pii
* **Human approval required**: yes

**When it fails**: tick logged as degraded; watches are NOT silently dropped

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
