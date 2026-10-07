---
type: Agent
title: network — Link - graph builder
description: Link - graph builder
tags:
  - agent
  - worker
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

# network — Link - graph builder

Runs as graph node `network`.

* **Module**: `app/agents/network_agent.py::build_network`
* **Routes**: LINK, NETWORK
* **Guardrails**: verify_claims, date_guard
* **Human approval required**: no

**When it fails**: no-op update when no suspect id resolves; never invents a seed

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
