"""
Antar — Planted Demo Patterns (P1, P2, P3)
====================================================
The three WOW moments are PLANTED, DETERMINISTIC patterns — not hoped-for
emergent ones (Strategy v4.0 §4.5). This module is the single source of truth
for every planted constant. The generator weaves them in; the validator
asserts them; the demo script depends on them.

NEVER tweak these values casually — the demo run-of-show, M2's brain
summaries, and the golden suite all reference them verbatim.
"""

# ── P1 — Cross-case alias link (guarantees WOW 2) ────────────────────────────
# Suspect "Raju K." (Bengaluru) carries alias "Yellappa". A Mysuru case cluster
# from ~8 months ago contains suspect "Yellappa" sharing phone_hash + 3 common
# contacts. The Second Brain pre-seed includes the Mysuru investigation summary.
P1 = {
    "bengaluru_suspect": {
        "suspect_id": "S0001",
        "full_name": "Raju K.",
        "alias": "Yellappa",
        "age": 34,
        "gender": "M",
        "phone_hash": "PH-7f3a9c-YEL",      # shared — the silent thread
        "address_zone": "Rajajinagar",
        "occupation": "lorry cleaner",
        "prior_count": 6,
    },
    "mysuru_suspect": {
        "suspect_id": "S0002",
        "full_name": "Yellappa M.",
        "alias": "Yella",
        "age": 35,
        "gender": "M",
        "phone_hash": "PH-7f3a9c-YEL",      # same hash as Raju K.
        "address_zone": "Mysuru-Devaraja",
        "occupation": "unknown",
        "prior_count": 4,
    },
    # The 3 common contacts (relationships to BOTH suspects)
    "common_contacts": ["S0003", "S0004", "S0005"],
    "mysuru_anchor_fir": "2025-MYS-0089",   # quoted verbatim in the banner
    "mysuru_case_months_ago": 8,
    "mysuru_cluster_size": 3,               # anchor + 2 related burglaries
    "bengaluru_recent_crime_type": "robbery",
}

# ── P2 — Rajajinagar chain-snatching spike (guarantees WOW 3) ────────────────
# Trailing 13 full weeks of weekly counts engineered so that:
#   μ ≈ 2.31, σ ≈ 1.81  →  z = (8 − 2.31) / 1.81 ≈ 3.14  (spec target z≈3.1)
# Demo week (the 7 days ending at --now) gets exactly DEMO_WEEK_COUNT cases.
# The Jan-2025 "gang surge" ALSO exists in the data (3 hot weeks) so the
# resolved_pattern brain match is grounded in real rows, not just a summary.
P2 = {
    "zone": "Rajajinagar",
    "crime_type": "chain_snatching",
    "trailing_weekly_counts": [0, 1, 2, 3, 5, 2, 0, 4, 2, 0, 3, 2, 6],  # oldest→newest
    "demo_week_count": 8,
    "expected_mu": 2.31,
    "expected_z_range": (2.5, 3.8),         # validator asserts z in this band
    "jan2025_surge_weekly": [8, 9, 7],      # 3 weeks starting Jan 6, 2025
    "evening_bias_hours": list(range(18, 23)),  # snatchings cluster 6–11 pm
}

# ── P3 — Evening theft concentration + festival bump (guarantees F3 map) ────
P3 = {
    "hot_zones": ["Rajajinagar", "Gandhinagar"],   # 2 zones glow on the heatmap
    "crime_type": "theft",
    "evening_hours": list(range(18, 24)),           # 6 pm – midnight
    "evening_share_in_hot_zones": 0.70,             # 70% of thefts there are evening
    "evening_share_elsewhere": 0.35,                # background realism
    "festival_week_start": "2025-09-29",            # Dasara week (Oct 2025)
    "festival_bump_multiplier": 1.4,                # +40% thefts that week, hot zones
}

# ── Second Brain pre-seed (the planted memory rows) ──────────────────────────
# M2 owns the full 50-summary corpus; these are the load-bearing ones the
# demo cannot run without. kind ∈ {investigation, resolved_pattern}.
BRAIN_SEED = [
    {
        "kind": "investigation",
        "station_code": "MYS-01",
        "suspect_ids": ["S0002"],
        "terms": ["Yellappa M.", "Yella", "Mysuru", "burglary", "2025-MYS-0089", "S0002"],
        "summary_text": (
            "Mysuru burglary cluster, case 2025-MYS-0089. Three night burglaries "
            "in Devaraja and Nazarbad localities over two weeks. Primary suspect "
            "one Yellappa M., alias Yella, age ~35, no fixed address, believed to "
            "work transport yards. Operated with two local associates; entry "
            "through rear ventilators, gold and cash only, sold through a "
            "Bengaluru receiver. Suspect absconding at case closure; phone "
            "switched off after the third incident. Associates detained and "
            "released; one mentioned the suspect 'goes by other names in "
            "Bengaluru side'. Case status: open, suspect untraced."
        ),
    },
    {
        "kind": "resolved_pattern",
        "station_code": "BLR-RJN-01",
        "suspect_ids": [],
        "terms": ["Rajajinagar", "chain_snatching", "chain-snatching", "BLR-RJN-01", "January 2025"],
        "summary_text": (
            "Resolved pattern: January 2025 chain-snatching surge, Rajajinagar. "
            "Weekly incidents rose from average two to eight-plus for three "
            "consecutive weeks. Signature: two-rider motorcycle teams, evening "
            "hours 6 to 10 pm, targets elderly women near temple streets and "
            "market exits, stolen chains moved within 48 hours through two known "
            "receivers. Resolved by vehicle-checkpoint saturation on four "
            "corridors plus receiver surveillance; five arrests, surge collapsed "
            "within ten days. Lesson: early checkpoint deployment at corridor "
            "chokepoints is the effective response to this signature."
        ),
    },
    {
        "kind": "investigation",
        "station_code": "BLR-RJN-01",
        "suspect_ids": ["S0001"],
        "terms": ["Raju K.", "Yellappa", "Rajajinagar", "robbery", "S0001", "BLR-RJN-01"],
        "summary_text": (
            "Rajajinagar robbery follow-up. Suspect Raju K., age 34, lorry "
            "cleaner, alias Yellappa, detained on suspicion in a street robbery "
            "near the metro works. Known associates include three local men from "
            "the goods-shed area. Modus operandi: targets pedestrians at dusk, "
            "uses two-wheeler getaway, avoids CCTV corridors. Released for want "
            "of evidence; phone records pending. Officer note: suspect evasive "
            "about travel history outside Bengaluru."
        ),
    },
]

# Demo officer accounts (mirror in Catalyst Authentication console — V: Jun 12)
DEMO_OFFICERS = [
    {"officer_id": "OF-1001", "name": "Arjun Devraj",   "rank": "Inspector",  "station_code": "BLR-RJN-01", "role_name": "Inspector"},
    {"officer_id": "OF-1002", "name": "Kavya Hegde",    "rank": "PC",         "station_code": "BLR-RJN-01", "role_name": "Constable"},
    {"officer_id": "OF-1003", "name": "Meera Kulkarni", "rank": "DySP",       "station_code": "SCRB-HQ",    "role_name": "Analyst"},
    {"officer_id": "OF-1004", "name": "Suresh Patil",   "rank": "SP",         "station_code": "SCRB-HQ",    "role_name": "Admin"},
]
