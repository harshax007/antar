---
type: Agent
title: osint — Scout - open-web scan
description: Scout - open-web scan
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

# osint — Scout - open-web scan

Runs as graph node `osint`.

* **Module**: `app/agents/graph.py::osint_node`
* **Routes**: OSINT
* **Guardrails**: redact_pii, verify_claims, vigil
* **Human approval required**: no

**When it fails**: OSINT section omitted; never presents an unreachable source as checked

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
