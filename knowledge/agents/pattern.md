---
type: Agent
title: pattern — Sense - MO pattern detector
description: Sense - MO pattern detector
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

# pattern — Sense - MO pattern detector

Runs as graph node `forecast`. Hosted inside `forecast`'s node.

* **Module**: `app/agents/pattern_agent.py::pattern_agent_run`
* **Routes**: PATTERN
* **Guardrails**: verify_claims
* **Human approval required**: no

**When it fails**: pattern section omitted from synthesis

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
