---
type: Agent
title: predict — Core - risk forecaster
description: Core - risk forecaster
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

# predict — Core - risk forecaster

Runs as graph node `forecast`. Hosted inside `forecast`'s node.

* **Module**: `app/agents/prediction_agent.py::prediction_agent_run`
* **Routes**: PREDICT, PREDICTION
* **Guardrails**: date_guard, prediction_privacy, conformal_band
* **Human approval required**: no

**When it fails**: risk band withheld rather than widened; officer told the forecast is unavailable

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
