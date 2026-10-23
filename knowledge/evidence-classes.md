---
type: Vocabulary
title: Evidence classes (K/D/I/U)
description: How Antar labels the standing of every claim it makes.
tags:
  - vocabulary
  - evidence
  - icd-203
generated:
  by: process:antar-okf-export
  at: "2026-10-23T12:47:16Z"
verified:
  - by: human:antar-team
    at: "2026-10-23T12:47:16Z"
status: stable
---

# Evidence classes (K/D/I/U)

Adapted from ICD 203 (US intelligence-community analytic standards). Every claim Antar
emits carries one, and the class travels with the claim through synthesis, the API and
the printable export.

| Class | Marker | Means |
|---|---|---|
| Known | `[VERIFIED]` | Read directly from FIR rows; the row ids are cited. |
| Derived | `[COMPUTED]` | Calculated from rows by a deterministic transform - a count, a rate, a conformal band, a similarity. Reproducible by hand from the cited rows. |
| Inferred | `[INFERRED]` | A scored hypothesis. Never presented without the base-rate audit from [advocate_agent](/agents/advocate-agent.md). |
| Unknown | `[GAP]` | Named as missing, with the collection action that would close it. |

The distinction that matters operationally: a **Derived** claim is as good as its inputs
and its arithmetic, both of which are checkable. An **Inferred** claim is a guess with a
number attached, and a number attached to a guess is how an officer gets anchored. That is
why the adversarial review is part of the research node rather than an optional follow-up.
