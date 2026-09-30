"""
Layer 5 — Search & OSINT Intelligence Verification Suite
=========================================================
Verifies:
  1. Multi-Module Reconnaissance Engine (Maltego, PhoneInfoga, Sherlock, BBOT event trace)
  2. Constitutional OSINT Quarantine (§0.4-2 unverified=True guardrails)
  3. Cross-Source Identity Hypotheses (`suggest_identity_links`)
  4. Unknown-First Search Discovery Protocol
"""

import pytest
from app.services.osint_recon import run_multi_module_recon
from app.services.entity_resolver import suggest_identity_links


def test_multi_module_recon_and_quarantine():
    """Verify all 5 recon modules run and strictly quarantine external OSINT claims."""
    mock_rows = [
        {
            "id": "FIR-2026-101",
            "fir_num": "101/2026",
            "suspect_name": "Raja Kumar",
            "phone_hash": "HASH-998877",
            "zone": "Rajajinagar",
        },
        {
            "id": "FIR-2026-102",
            "fir_num": "102/2026",
            "suspect_name": "Raja K",
            "phone_hash": "HASH-998877",
            "zone": "Rajajinagar",
        },
    ]

    report = run_multi_module_recon("Rajajinagar", mock_rows)

    # 1. Check Maltego graph linkage
    assert "maltego_linkage" in report
    assert len(report["maltego_linkage"]["nodes"]) > 0
    assert len(report["maltego_linkage"]["edges"]) > 0

    # 2. Check PhoneInfoga
    assert "phone_infoga" in report

    # 3. Check Sherlock handles & quarantine
    for h in report["sherlock_handles"]:
        assert h["unverified"] is True
        assert h["status"] == "quarantined"
        assert "OSINT / UNVERIFIED" in h["badge"]

    # 4. Check BBOT event scan tree
    assert len(report["bbot_scan_tree"]) >= 4
    event_types = [e["event_type"] for e in report["bbot_scan_tree"]]
    assert "SCAN_INIT" in event_types
    assert "GRAPH_LINKAGE" in event_types

    # 5. Check OSINT Corroboration Counter
    corroborated = [c for c in report["osint_claims"] if c.get("corroborates")]
    assert len(corroborated) > 0


def test_suggest_identity_links():
    """Verify cross-source identity hypotheses generated from shared phone_hash and phonetic similarity."""
    mock_rows = [
        {
            "id": "SUS-1",
            "suspect_name": "Yellappa Gowda",
            "phone_hash": "HASH-881122",
            "zone": "Indiranagar",
        },
        {
            "id": "SUS-2",
            "suspect_name": "Yellapa G",
            "phone_hash": "HASH-881122",
            "zone": "Indiranagar",
        },
        {
            "id": "SUS-3",
            "suspect_name": "Unrelated Suresh",
            "phone_hash": "HASH-000000",
            "zone": "Mysuru",
        },
    ]

    links = suggest_identity_links(mock_rows, threshold=0.75)
    assert len(links) >= 1

    top_link = links[0]
    assert top_link["badge"] == "INFERRED (CROSS-SOURCE IDENTITY)"
    assert top_link["requires_rbac_rank"] == "Inspector"
    assert "Exact phone_hash co-occurrence" in top_link["reasons"] or any("Soundex" in r for r in top_link["reasons"])
