---
type: Agent
title: profile — Motive - suspect profiler
description: Motive - suspect profiler
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

# profile — Motive - suspect profiler

Runs as graph node `profile`.

* **Module**: `app/agents/profile_agent.py::compute_profile`
* **Routes**: MOTIVE, PROFILE
* **Guardrails**: evaluate_bias, redact_pii, calculate_shap_values, verify_claims
* **Human approval required**: no

**When it fails**: no-op update when no suspect id resolves

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
