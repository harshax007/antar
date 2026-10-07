---
type: Agent
title: alert_suggest — Beacon - patrol advisor
description: Beacon - patrol advisor
tags:
  - agent
  - worker
  - hitl
generated:
  by: process:antar-okf-export
  at: "2026-10-07T00:58:49Z"
sources:
  - id: antar-agent-manifest
    resource: /AGENTS.md
    title: Antar agent manifest
    author: process:antar-okf-export
status: stable
---

# alert_suggest — Beacon - patrol advisor

Runs as graph node `forecast`. Hosted inside `forecast`'s node.

* **Module**: `app/agents/alert_suggest_agent.py::alert_suggest_agent_run`
* **Routes**: ALERT_SUGGEST, ALERTS
* **Guardrails**: date_guard, verify_claims
* **Human approval required**: yes

**When it fails**: honest 'no unusual activity right now' - never an invented spike

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
