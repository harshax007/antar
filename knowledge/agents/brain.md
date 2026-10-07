---
type: Agent
title: brain — Vault - semantic recall
description: Vault - semantic recall
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

# brain — Vault - semantic recall

Runs as graph node `brain`.

* **Module**: `app/agents/graph.py::brain_node`
* **Routes**: BRAIN
* **Guardrails**: confidence_decay, verify_claims
* **Human approval required**: no

**When it fails**: recall skipped when index is empty or the embedder failed to load

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
