---
type: Agent
title: vigil — A5 - bias and compliance auditor
description: A5 - bias and compliance auditor
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

# vigil — A5 - bias and compliance auditor

No graph node — API and autonomous surfaces only.

* **Module**: `app/agents/vigil_agent.py::audit_request`
* **Guardrails**: redact_pii
* **Human approval required**: no

**When it fails**: receipt marked unavailable; the query is NOT auto-approved on failure

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
