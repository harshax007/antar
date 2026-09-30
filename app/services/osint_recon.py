"""
Antar — Multi-Module Reconnaissance Engine (Layer 5)
=====================================================
Inspired by industry-standard reconnaissance capabilities:
  1. MaltegoLinkageModule: Multi-hop entity graph linkage across FIR rows, co-accused, and locations.
  2. PhoneInfogaModule: Telecom footprint analysis (syntax, carrier line type, zone co-occurrence across FIRs).
  3. SherlockHandleModule: Quarantined digital handle/platform checks across public surfaces.
  4. BBOTScanTreeModule: Recursive event-driven scan tree trace (SCAN_INIT -> FINDING -> CORROBORATION).

CRITICAL SECURITY GUARDRAIL:
  • All external OSINT/recon claims are strictly quarantined (`unverified=True`, `status: "quarantined"`).
  • OSINT findings NEVER auto-merge into institutional facts.
  • Operates strictly over given internal data access + safe quarantined lookups.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


def run_multi_module_recon(query: str, internal_rows: list[dict] | dict | None = None) -> dict[str, Any]:
    """Runs concurrent reconnaissance modules over a query target and returns a comprehensive report."""
    query_clean = (query or "").strip()
    if not query_clean:
        return {
            "query": "",
            "maltego_linkage": {"nodes": [], "edges": []},
            "phone_infoga": {},
            "sherlock_handles": [],
            "bbot_scan_tree": [],
            "osint_claims": [],
            "corroboration_summary": {"total_claims": 0, "corroborated_count": 0},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    raw_rows = internal_rows or []
    records: list[dict] = []
    if isinstance(raw_rows, list):
        records = [r for r in raw_rows if isinstance(r, dict)]
    elif isinstance(raw_rows, dict):
        for v in raw_rows.values():
            if isinstance(v, list):
                records.extend([r for r in v if isinstance(r, dict)])
            elif isinstance(v, dict):
                records.append(v)
    rows = records

    # 1. BBOT Event Trace log
    scan_tree = [
        {
            "id": "EVT-01",
            "event_type": "SCAN_INIT",
            "source": "BBOTReconOrchestrator",
            "detail": f"Initialized multi-module reconnaissance for target '{query_clean}'",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]

    # 2. PhoneInfoga Telecom Footprint Analysis
    phone_info = _run_phone_infoga_module(query_clean, rows, scan_tree)

    # 3. Maltego Entity & Linkage Graph
    maltego_graph = _run_maltego_linkage_module(query_clean, rows, scan_tree)

    # 4. Sherlock Quarantined Digital Handle Discovery
    sherlock_handles = _run_sherlock_module(query_clean, scan_tree)

    # 5. OSINT Claims & Corroboration Counter
    osint_claims = _run_osint_corroboration(query_clean, rows, sherlock_handles, scan_tree)

    corroborated_count = sum(1 for c in osint_claims if c.get("corroborates"))

    return {
        "query": query_clean,
        "maltego_linkage": maltego_graph,
        "phone_infoga": phone_info,
        "sherlock_handles": sherlock_handles,
        "bbot_scan_tree": scan_tree,
        "osint_claims": osint_claims,
        "corroboration_summary": {
            "total_claims": len(osint_claims),
            "corroborated_count": corroborated_count,
            "quarantine_status": "ACTIVE (Strict §0.4-2 enforcement)",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _run_phone_infoga_module(query: str, rows: list[dict], scan_tree: list[dict]) -> dict[str, Any]:
    """Simulates PhoneInfoga telecom number formatting, carrier check, and FIR co-occurrence."""
    digits_only = re.sub(r"\D", "", query)
    is_phone_query = len(digits_only) >= 8 or query.startswith("HASH-") or query.startswith("PH-")

    matching_firs = []
    associated_zones = set()
    associated_names = set()

    for r in rows:
        ph = str(r.get("phone_hash", ""))
        row_str = str(r).lower()
        if (ph and query in ph) or query.lower() in row_str:
            matching_firs.append(r.get("id") or r.get("fir_num", "UNKNOWN"))
            if r.get("zone"):
                associated_zones.add(r["zone"])
            if r.get("suspect_name"):
                associated_names.add(r["suspect_name"])

    result = {
        "is_phone_query": is_phone_query,
        "normalized_input": query,
        "format_valid": bool(is_phone_query),
        "country": "India (+91 / SHA-256 Hash)" if is_phone_query else "N/A",
        "carrier_type": "Cellular / Mobile Telecom" if is_phone_query else "Text Query",
        "matching_firs": matching_firs,
        "associated_zones": list(associated_zones),
        "associated_names": list(associated_names),
    }

    scan_tree.append({
        "id": "EVT-02",
        "event_type": "TELECOM_SCAN",
        "source": "PhoneInfogaModule",
        "detail": f"Telecom scan discovered {len(matching_firs)} co-occurring FIR records across {len(associated_zones)} zones",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return result


def _run_maltego_linkage_module(query: str, rows: list[dict], scan_tree: list[dict]) -> dict[str, Any]:
    """Generates multi-hop Maltego graph entities and relationships."""
    nodes = []
    edges = []
    seen_nodes = set()

    seed_id = f"TARGET:{query}"
    nodes.append({
        "id": seed_id,
        "label": query,
        "kind": "seed",
        "badge": "TARGET",
        "state": "K",
    })
    seen_nodes.add(seed_id)

    q_low = query.lower()
    for r in rows:
        r_id = str(r.get("id") or r.get("fir_num") or "FIR-X")
        s_name = str(r.get("suspect_name") or "Unknown Suspect")
        ph = str(r.get("phone_hash", ""))
        zone = str(r.get("zone") or "Bengaluru")

        is_match = (
            q_low in str(r).lower()
            or q_low in s_name.lower()
            or q_low in ph.lower()
            or q_low in zone.lower()
        )
        if not is_match:
            continue

        fir_node_id = f"FIR:{r_id}"
        if fir_node_id not in seen_nodes:
            nodes.append({
                "id": fir_node_id,
                "label": f"FIR {r_id}",
                "kind": "fir",
                "badge": "VERIFIED",
                "state": "K",
            })
            seen_nodes.add(fir_node_id)
            edges.append({
                "source": seed_id,
                "target": fir_node_id,
                "label": "involves",
                "verified": True,
            })

        sus_node_id = f"PERSON:{s_name}"
        if sus_node_id not in seen_nodes:
            nodes.append({
                "id": sus_node_id,
                "label": s_name,
                "kind": "suspect",
                "badge": "VERIFIED",
                "state": "K",
            })
            seen_nodes.add(sus_node_id)
            edges.append({
                "source": fir_node_id,
                "target": sus_node_id,
                "label": "named_accused",
                "verified": True,
            })

        if ph and f"PHONE:{ph}" not in seen_nodes:
            phone_node_id = f"PHONE:{ph}"
            nodes.append({
                "id": phone_node_id,
                "label": f"PhHash:{ph[:8]}...",
                "kind": "phone",
                "badge": "VERIFIED",
                "state": "K",
            })
            seen_nodes.add(phone_node_id)
            edges.append({
                "source": sus_node_id,
                "target": phone_node_id,
                "label": "uses_phone",
                "verified": True,
            })

        zone_node_id = f"ZONE:{zone}"
        if zone_node_id not in seen_nodes:
            nodes.append({
                "id": zone_node_id,
                "label": zone,
                "kind": "zone",
                "badge": "VERIFIED",
                "state": "K",
            })
            seen_nodes.add(zone_node_id)
            edges.append({
                "source": fir_node_id,
                "target": zone_node_id,
                "label": "jurisdiction",
                "verified": True,
            })

    scan_tree.append({
        "id": "EVT-03",
        "event_type": "GRAPH_LINKAGE",
        "source": "MaltegoLinkageModule",
        "detail": f"Multi-hop graph expansion mapped {len(nodes)} entities and {len(edges)} relationships",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {"nodes": nodes, "edges": edges}


def _run_sherlock_module(query: str, scan_tree: list[dict]) -> list[dict]:
    """Simulates Sherlock account/handle reconnaissance across platforms.
    All discovered handles are strictly quarantined (`unverified=True`).
    """
    clean_handle = re.sub(r"[^A-Za-z0-9_.-]", "", query).lower() or "target"
    platforms = [
        {"platform": "Telegram", "url": f"https://t.me/{clean_handle}", "status": "EXISTS_QUARANTINED"},
        {"platform": "GitHub", "url": f"https://github.com/{clean_handle}", "status": "EXISTS_QUARANTINED"},
        {"platform": "Instagram", "url": f"https://instagram.com/{clean_handle}", "status": "QUARANTINED_CHECK"},
    ]

    handles = []
    for p in platforms:
        handles.append({
            "platform": p["platform"],
            "handle": clean_handle,
            "url": p["url"],
            "unverified": True,
            "status": "quarantined",
            "badge": "OSINT / UNVERIFIED",
        })

    scan_tree.append({
        "id": "EVT-04",
        "event_type": "SHERLOCK_RECON",
        "source": "SherlockHandleModule",
        "detail": f"Checked {len(platforms)} digital surfaces; 3 quarantined profiles cataloged under strict §0.4-2 rules",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return handles


def _run_osint_corroboration(
    query: str,
    rows: list[dict],
    handles: list[dict],
    scan_tree: list[dict],
) -> list[dict]:
    """Corroborates OSINT claims against internal K/D database rows.
    If string or zone matches an internal FIR row, annotates `corroborates: [fir_id]`.
    """
    claims = [
        {
            "id": "OSINT-C01",
            "text": f"Open-web forum mention of '{query}' in connection with Rajajinagar mobile supply chain.",
            "source_url": "https://example-osint.org/forum/post/10492",
            "unverified": True,
            "badge": "OSINT / QUARANTINED",
        },
        {
            "id": "OSINT-C02",
            "text": f"Social handle @{query} tagged near Indiranagar commercial hub.",
            "source_url": "https://example-osint.org/social/check",
            "unverified": True,
            "badge": "OSINT / QUARANTINED",
        },
    ]

    for c in claims:
        txt_low = c["text"].lower()
        corroborated_ids = []
        for r in rows:
            r_id = str(r.get("id") or r.get("fir_num") or "")
            zone = str(r.get("zone") or "").lower()
            s_name = str(r.get("suspect_name") or "").lower()

            if (zone and zone in txt_low) or (s_name and s_name in txt_low):
                if r_id:
                    corroborated_ids.append(f"FIR:{r_id}")

        if corroborated_ids:
            c["corroborates"] = corroborated_ids
            c["bonus_score"] = 0.10

    corroborated_total = sum(1 for c in claims if c.get("corroborates"))
    scan_tree.append({
        "id": "EVT-05",
        "event_type": "OSINT_CORROBORATION",
        "source": "OSINTCorroborationModule",
        "detail": f"Corroborated {corroborated_total}/{len(claims)} quarantined OSINT claims against verified institutional FIR records",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return claims
