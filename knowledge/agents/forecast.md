---
type: Agent
title: forecast — Core - risk forecaster (composite node)
description: Core - risk forecaster (composite node)
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

# forecast — Core - risk forecaster (composite node)

Runs as graph node `forecast`.

* **Module**: `app/agents/graph.py::forecast_node`
* **Routes**: CORE, FORECAST
* **Guardrails**: date_guard, prediction_privacy, verify_claims
* **Human approval required**: no

**When it fails**: per-sub-agent; a failing sub-agent yields a degraded step, never a fabricated band

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
