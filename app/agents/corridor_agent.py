"""
Antar — Corridor Agent (A2: Movement Intelligence · Phase 1)
=================================================================
Promotes client-side corridor calculations into compiled server-side
'corridor:{A}:{B}' products.
Tracks linked-offender inter-district movement, recency weighting,
involved entities, and deterministic transition probability (next-district estimates).
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from app.services import product_store, evidence_ledger


def compile_corridors() -> list[dict[str, Any]]:
    """Compile REAL inter-district corridor products from the evidence ledger.

    A corridor exists because the SAME accused appears in two districts; every field
    (linking offenders, FIR count, recency, next-district estimate) is counted from the
    CSV rows by `evidence_ledger.corridors()` — no fixtures, no fabricated statistics.
    """
    ts = datetime.now(timezone.utc).isoformat()
    compiled: list[dict[str, Any]] = []

    for c in evidence_ledger.corridors(limit=20):
        src, dst = c["src"], c["dst"]
        key = f"corridor:{src.lower()}:{dst.lower()}"

        # involved offenders = the real accused linking the two districts (top by involvement)
        entities = []
        for rank, aid in enumerate(c["accused_ids"][:5]):
            entities.append({
                "id": aid,
                "name": evidence_ledger.alias_for(aid),
                "name_note": "synthetic alias",
                "role": "Ring leader" if rank == 0 else "Linked offender",
            })

        nd = c["next_district"]
        next_estimate = (
            {"district": nd["district"], "probability": nd["probability"], "reason": nd["reason"]}
            if nd else
            {"district": None, "probability": 0.0, "reason": "no onward district shared by these offenders"}
        )

        payload = {
            "corridor_id": f"COR-{src[:3].upper()}-{dst[:3].upper()}",
            "src": src,
            "dst": dst,
            "direction": f"{src} ↔ {dst}" + (f" → {nd['district']}" if nd else ""),
            "src_lat": c["src_lat"], "src_lon": c["src_lon"],
            "dst_lat": c["dst_lat"], "dst_lon": c["dst_lon"],
            "weight": c["linking_accused"],          # # of offenders linking the two districts (real)
            "fir_count": c["fir_count"],
            "recency_days": c["recency_days"],
            "last_date": c["last_date"],
            "next_district_estimate": next_estimate,
            "involved_entities": entities,
            "primary_crime": c["top_crime"] or "mixed",
            "provenance": {
                "agent": "A2: Corridor Movement Intelligence",
                "method": "shared-accused transition counting over evidence ledger",
                "compiled_at": ts,
                "input_accused": c["accused_ids"],
            },
        }
        compiled.append(payload)
        product_store.put_product(key, payload, ttl=3600)

    product_store.put_product("corridors:all", compiled, ttl=3600)
    return compiled


def get_corridor(src: str, dst: str) -> dict[str, Any] | None:
    """Retrieve a specific corridor product from Product Store."""
    key = f"corridor:{src.lower()}:{dst.lower()}"
    prod = product_store.get_product(key)
    if prod:
        return prod
    # If not found in cache, trigger compilation
    compile_corridors()
    return product_store.get_product(key)


def get_all_corridors() -> list[dict[str, Any]]:
    """Retrieve all active corridors."""
    prod = product_store.get_product("corridors:all")
    if prod:
        return prod
    return compile_corridors()
