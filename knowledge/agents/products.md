---
type: Agent
title: products — Master Orchestrator - product compiler
description: Master Orchestrator - product compiler
tags:
  - agent
  - service
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

# products — Master Orchestrator - product compiler

No graph node — API and autonomous surfaces only.

* **Module**: `app/services/product_store.py::refresh_expiring`
* **Human approval required**: no

**When it fails**: stale product served with its original compiled_at timestamp, never re-stamped

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
