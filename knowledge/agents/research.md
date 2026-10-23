---
type: Agent
title: research — Trace - K/D/I/U dossier
description: Trace - K/D/I/U dossier
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

# research — Trace - K/D/I/U dossier

Runs as graph node `research`.

* **Module**: `app/agents/graph.py::research_node`
* **Routes**: TRACE, RESEARCH
* **Guardrails**: verify_claims, vigil, kdiu_tagging, adversarial_review
* **Human approval required**: no

**When it fails**: no-op when no researchable subject is named; never researches an empty anchor

Declared in [the agent index](/agents/index.md) and in `AGENTS.md`, which is executable: `app/agents/manifest.py` parses it at import time and a test fails the build when it disagrees with the compiled graph.
