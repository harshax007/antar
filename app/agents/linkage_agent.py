"""
Antar — Linkage Agent (A3: MO Case-Matcher · Phase 1)
==========================================================
Compiles 'linkage:{fir_id}' products linking candidate same-offender
and same-ring cases ranked by transparent scoring:
  1. Shared hard keys (accused ID, phone, vehicle, UPI ID)
  2. Modus Operandi (MO) similarity
  3. Spatiotemporal adjacency (ST-DBSCAN / zone proximity)
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from app.services import product_store, evidence_ledger


def compile_linkage(fir_id: str) -> dict[str, Any]:
    """Compile the REAL case-linkage product for one evidence FIR (an 'EV-{i}' ref).

    Candidates are other evidence FIRs sharing a hard key — same accused, vehicle, UPI,
    IP, or place — scored transparently by `evidence_ledger.linkage()`. Every candidate
    cites the exact shared key. An official 'FIR-2026-xxxx' id (no accused/vehicle data
    in that table) honestly yields zero candidates rather than a fabricated match.
    """
    ts = datetime.now(timezone.utc).isoformat()
    key = f"linkage:{fir_id.upper()}"

    res = evidence_ledger.linkage(fir_id)
    candidates = res["candidates"] if res else []

    payload = {
        "fir_id": fir_id.upper(),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "provenance": {
            "agent": "A3: Linkage MO Case-Matcher",
            "method": "shared hard-key matching over evidence ledger (accused / vehicle / UPI / IP / place)",
            "compiled_at": ts,
        },
    }

    product_store.put_product(key, payload, ttl=3600)
    return payload


def compile_all_linkages(limit: int = 10) -> list[dict[str, Any]]:
    """Compile linkage products for the highest-priority FIRs (most-active multi-FIR
    offenders) — real, deterministic set from the evidence ledger."""
    return [compile_linkage(ref) for ref in evidence_ledger.priority_fir_refs(limit=limit)]
