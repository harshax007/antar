---
type: Agent
title: advocate_agent — Adversary - hypothesis falsification and base-rate audit
description: Adversary - hypothesis falsification and base-rate audit
tags:
  - agent
  - worker
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

# advocate_agent — Adversary - hypothesis falsification and base-rate audit

Runs as graph node `research`. Hosted inside `research`'s node.

* **Module**: `app/agents/advocate_agent.py::challenge`
* **Guardrails**: deterministic_only, no_llm
* **Human approval required**: no

**When it fails**: returns UNASSESSABLE for unresolvable subjects - never silently approves a hypothesis

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
