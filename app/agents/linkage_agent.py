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
from app.core.db_path import registry_connect


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


# The hard keys a Brain-graph record can carry: (column, label).
BRAIN_KEYS = [("Accused_ID", "accused"), ("Vehicle_Reg_No", "vehicle"),
              ("UPI_ID", "UPI"), ("IP_Address", "IP")]


def brain_linkage(keys: dict[str, str], limit: int = 8) -> dict[str, Any]:
    """FIRs in the Brain dataset that carry any of the given hard keys.

    `keys` is {column: value} taken from the record itself - never a row number. A record
    on the Brain graph has no id the backend can use: the graph numbers its nodes by
    position in the list it was sent, the registry numbers rows its own way, and
    `compile_linkage` speaks 'EV-{i}', a row of the evidence CSV. Passing one numbering to
    another returns a confident answer about an unrelated case, so linkage for a graph
    record goes by the keys it carries and nothing else.

    Reads the same store the Brain screen draws from (/api/dataset/graph): the curated
    intelligent.db when it is present, otherwise the registry. Exact matches only; every
    row returned names the keys it shares. The counts INCLUDE the record the keys came from.
    """
    import os
    import sqlite3
    from app.core.db_path import DB_PATH, ensure_db_staged

    wanted = {c: str(keys.get(c) or "").strip() for c, _ in BRAIN_KEYS}
    wanted = {c: v for c, v in wanted.items() if v}
    if not wanted:
        return {"keys": {}, "by_key": {}, "total": 0, "rows": []}
    intel = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "intelligent.db"))
    if os.path.exists(intel):
        con = sqlite3.connect(f"file:{intel}?immutable=1", uri=True)
    else:
        ensure_db_staged()
        con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cols = ("rowid AS rid, District_Name, UnitName, FIR_YEAR, FIR_MONTH, CrimeGroup_Name, "
            "CrimeHead_Name, " + ", ".join(c for c, _ in BRAIN_KEYS))
    try:
        where = " OR ".join(f"{c} = ?" for c in wanted)
        found = con.execute(f"SELECT {cols} FROM FIRs WHERE {where} LIMIT 1000",
                            list(wanted.values())).fetchall()
    finally:
        con.close()

    labels = dict(BRAIN_KEYS)
    by_key = {c: 0 for c in wanted}
    rows = []
    for r in found:
        shared = [c for c, v in wanted.items() if str(r[c] or "").strip() == v]
        if not shared:
            continue
        for c in shared:
            by_key[c] += 1
        rows.append({"district": r["District_Name"] or "", "station": r["UnitName"] or "",
                     "crime_type": r["CrimeHead_Name"] or r["CrimeGroup_Name"] or "",
                     "when": f"{r['FIR_YEAR']}-{int(r['FIR_MONTH'] or 0):02d}" if r["FIR_YEAR"] else "",
                     "shares": [f"{labels[c]} {wanted[c]}" for c in shared], "n_shared": len(shared),
                     "rid": r["rid"]})
    rows.sort(key=lambda x: (-x["n_shared"], x["when"], x["rid"]), reverse=False)
    return {"keys": wanted, "by_key": {labels[c]: {"value": wanted[c], "firs": n} for c, n in by_key.items()},
            "total": len(rows), "rows": rows[:limit]}


def compile_all_linkages(limit: int = 10) -> list[dict[str, Any]]:
    """Compile linkage products for the highest-priority FIRs (most-active multi-FIR
    offenders) — real, deterministic set from the evidence ledger."""
    return [compile_linkage(ref) for ref in evidence_ledger.priority_fir_refs(limit=limit)]
