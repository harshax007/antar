---
type: Agent
title: linkage — MO case-matcher
description: MO case-matcher
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

# linkage — MO case-matcher

No graph node — API and autonomous surfaces only.

* **Module**: `app/agents/linkage_agent.py::compile_linkage`
* **Guardrails**: verify_claims
* **Human approval required**: no

**When it fails**: no linkage returned; never asserts a match on a missing shared key

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
