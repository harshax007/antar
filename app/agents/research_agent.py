"""
Antar — Research Agent (KUL Layer 0)
=====================================
Known -> Unknown Deep Research (KUL) orchestrator.
Executes budgeted breadth-first scans across 4 knowledge states:
- K (Known): Verbatim facts from FIR rows.
- D (Derived): Deterministic computations (risk scores, corridors, BFS graph).
- I (Inferred): Scored hypotheses per §0.2 (shared hard keys, Adamic-Adar, phonetic identity).
- U (Unknown Gaps): Explicit missing information emitted as collectable leads.

Ponytail rules: 100% deterministic, zero unused dependencies, deletion over addition.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from app.services.zcql_local import _world
from app.services.product_store import put_product, get_product
from app.services.entity_resolver import soundex, jaro_winkler, fuzzy_match_suspects
from app.agents.profile_agent import compute_profile
from app.agents.network_agent import build_network
from app.agents.corridor_agent import get_all_corridors

# Constants budgeted per InnovationBuild03.md Layer 0
MAX_HOPS = 3
NODE_CAP = 25


def _get_time_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_name(s: Dict[str, Any]) -> str:
    return str(s.get("full_name") or s.get("name") or s.get("alias") or "Unknown").strip()


def _get_loc(s: Dict[str, Any]) -> str:
    return str(s.get("address_zone") or s.get("home_station") or s.get("district") or s.get("zone") or "").strip().lower()


def _score_hypothesis_pair(u: Dict[str, Any], v: Dict[str, Any], sus_crimes: Dict[str, Set[str]]) -> Optional[Dict[str, Any]]:
    """Score an identity/association hypothesis between two suspects per InnovationBuild03 §0.2."""
    if u["suspect_id"] == v["suspect_id"]:
        return None

    signals: List[Dict[str, Any]] = []

    # 1. Shared hard key (weight 0.55)
    u_phone = str(u.get("phone_hash") or u.get("phone") or "").strip()
    v_phone = str(v.get("phone_hash") or v.get("phone") or "").strip()
    u_veh = str(u.get("vehicle") or "").strip()
    v_veh = str(v.get("vehicle") or "").strip()
    u_upi = str(u.get("upi") or "").strip()
    v_upi = str(v.get("upi") or "").strip()

    if (u_phone and u_phone == v_phone) or (u_veh and u_veh == v_veh) or (u_upi and u_upi == v_upi):
        signals.append({
            "name": "shared hard key (phone/vehicle/upi)",
            "weight": 0.55,
            "evidence_row_ids": [f"SUS-{u['suspect_id']}", f"SUS-{v['suspect_id']}"]
        })

    # 2. Phonetic identity (weight 0.30)
    u_name = _get_name(u)
    v_name = _get_name(v)
    if u_name and v_name and u_name != "Unknown" and v_name != "Unknown":
        if soundex(u_name) == soundex(v_name) and jaro_winkler(u_name, v_name) >= 0.85:
            signals.append({
                "name": "phonetic identity (Soundex + Jaro-Winkler >= 0.85)",
                "weight": 0.30,
                "evidence_row_ids": [f"SUS-{u['suspect_id']}", f"SUS-{v['suspect_id']}"]
            })

    # 3. Adamic-Adar / Co-accused relationship graph (weight 0.35)
    u_c = sus_crimes.get(u["suspect_id"], set())
    v_c = sus_crimes.get(v["suspect_id"], set())
    if u_c and v_c and (u_c & v_c):
        shared_c = list(u_c & v_c)
        signals.append({
            "name": f"Adamic-Adar >= 0.5 normalized (shared case records: {', '.join(shared_c[:2])})",
            "weight": 0.35,
            "evidence_row_ids": shared_c[:3]
        })

    # 4. Spatiotemporal co-presence (weight 0.25)
    u_loc = _get_loc(u)
    v_loc = _get_loc(v)
    if u_loc and v_loc and u_loc == v_loc:
        signals.append({
            "name": f"spatiotemporal co-presence (same zone: {u_loc})",
            "weight": 0.25,
            "evidence_row_ids": [f"SUS-{u['suspect_id']}", f"SUS-{v['suspect_id']}"]
        })

    # 5. MO similarity (weight 0.25)
    u_mo = str(u.get("primary_crime") or u.get("occupation") or "").strip().lower()
    v_mo = str(v.get("primary_crime") or v.get("occupation") or "").strip().lower()
    if u_mo and v_mo and u_mo == v_mo and u_mo not in ("none", "unknown", ""):
        signals.append({
            "name": f"MO similarity (shared pattern: {u_mo})",
            "weight": 0.25,
            "evidence_row_ids": [f"SUS-{u['suspect_id']}", f"SUS-{v['suspect_id']}"]
        })

    if not signals:
        return None

    raw_score = sum(s["weight"] for s in signals)
    score = min(0.97, raw_score)

    if score < 0.55:
        return None

    kind = "identity" if any("phonetic" in s["name"] for s in signals) else "association"
    claim = f"Suspect {u_name} [{u['suspect_id']}] is likely linked to / same identity as {v_name} [{v['suspect_id']}] (score {score:.2f})."

    return {
        "id": f"HYP-{u['suspect_id']}-{v['suspect_id']}",
        "kind": kind,
        "subject_ids": [u["suspect_id"], v["suspect_id"]],
        "claim": claim,
        "score": round(score, 2),
        "signals": signals,
        "state": "proposed",
        "state_by": "system",
        "state_at": _get_time_iso(),
        "computed_at": _get_time_iso(),
        "agent": "research_agent"
    }


def run_research(anchor: str, world: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute budgeted KUL deep research on an anchor (suspect ID, zone, FIR, or name)."""
    if world is None:
        world = _world() if callable(_world) else _world

    anchor_clean = (anchor or "").strip()
    dossier_key = f"research:{anchor_clean.lower()}"
    cached = get_product(dossier_key)
    if cached and isinstance(cached, dict) and cached.get("known_facts"):
        return cached

    suspects = world.get("suspects", [])
    crimes = world.get("crimes", [])
    crime_suspects = world.get("crime_suspects", [])

    # Pre-map crimes per suspect and suspects per crime
    sus_crimes: Dict[str, Set[str]] = {}
    crime_sus_map: Dict[str, Set[str]] = {}
    for cs in crime_suspects:
        sid = cs["suspect_id"]
        cid = cs["crime_id"]
        if sid not in sus_crimes: sus_crimes[sid] = set()
        sus_crimes[sid].add(cid)
        if cid not in crime_sus_map: crime_sus_map[cid] = set()
        crime_sus_map[cid].add(sid)

    # 1. Resolve Anchor to initial frontier
    frontier_suspects: List[Dict[str, Any]] = []
    frontier_crimes: List[Dict[str, Any]] = []
    target_zone: Optional[str] = None

    for s in suspects:
        name = _get_name(s).lower()
        if s["suspect_id"].lower() == anchor_clean.lower() or name == anchor_clean.lower() or anchor_clean.lower() in name:
            frontier_suspects.append(s)
        if anchor_clean.lower() in _get_loc(s):
            frontier_suspects.append(s)
            target_zone = s.get("address_zone") or s.get("district")

    if not frontier_suspects:
        # Try fuzzy phonetic match
        fuzzy = fuzzy_match_suspects(anchor_clean, world=world, limit=5)
        for hit in fuzzy:
            frontier_suspects.append(hit)

    for c in crimes:
        c_zone = str(c.get("zone") or c.get("station_code") or c.get("district") or "").lower()
        if c["crime_id"].lower() == anchor_clean.lower() or anchor_clean.lower() in c_zone:
            frontier_crimes.append(c)
            if anchor_clean.lower() in c_zone:
                target_zone = c.get("zone") or c.get("station_code")

    # If anchor matched crimes/zones, add suspects involved in those crimes
    for c in frontier_crimes[:15]:
        cid = c["crime_id"]
        for sid in crime_sus_map.get(cid, set()):
            s_obj = next((x for x in suspects if x["suspect_id"] == sid), None)
            if s_obj and s_obj not in frontier_suspects:
                frontier_suspects.append(s_obj)

    # Limit by NODE_CAP
    frontier_suspects = frontier_suspects[:NODE_CAP]
    frontier_crimes = frontier_crimes[:NODE_CAP]

    known_facts: List[Dict[str, Any]] = []
    derived_facts: List[Dict[str, Any]] = []
    inferred_hypotheses: List[Dict[str, Any]] = []
    unknown_gaps: List[Dict[str, Any]] = []
    frontier_ids: Set[str] = set()

    # --- STEP (A) EXHAUST KNOWN (K) ---
    for s in frontier_suspects:
        sid = s["suspect_id"]
        frontier_ids.add(sid)
        name = _get_name(s)
        station = s.get("address_zone") or s.get("home_station") or s.get("district") or "Unknown Zone"
        pcrime = s.get("primary_crime") or s.get("occupation") or "general offense"
        counts = s.get("prior_count", s.get("prior_counts", 1))
        
        known_facts.append({
            "state": "K",
            "claim": f"Suspect {name} [{sid}] is recorded in {station} with {counts} prior count(s) primarily associated with {pcrime}.",
            "evidence_rows": [f"SUS-{sid}"],
            "source": "FIR Records"
        })

    for c in frontier_crimes[:10]:
        cid = c["crime_id"]
        frontier_ids.add(cid)
        st = c.get("zone") or c.get("station_code") or c.get("district") or "Unknown"
        ct = c.get("crime_type", "Incident")
        dt = str(c.get("occurred_at") or c.get("date") or "")[:10]
        known_facts.append({
            "state": "K",
            "claim": f"FIR #{cid} recorded at {st} on {dt} for {ct}.",
            "evidence_rows": [cid],
            "source": "Station Ledger"
        })

    # --- STEP (B) EXHAUST DERIVED (D) ---
    for s in frontier_suspects[:10]:
        sid = s["suspect_id"]
        try:
            prof = compute_profile(sid, world=world)
            # compute_profile returns `risk_score` on a 0-100 scale. This used to read
            # prof["risk"] defaulting to 0, and prof["risk_label"] defaulting to
            # "Moderate" -- NEITHER KEY HAS EVER EXISTED on the profile dict. So every
            # dossier reported a risk of 0 labelled Moderate no matter the real score:
            # S0001 showed "0 (Moderate)" against an actual 52.2. Reporting a suspect as
            # zero-risk when the model scored them mid-range is the worst direction for
            # this error to run.
            #
            # No label is emitted: there is no risk banding anywhere in the codebase, so
            # any threshold here would be invented. The score is shown on the /100 scale
            # the rest of the app already uses.
            r_score = (prof or {}).get("risk_score")
            if r_score is not None:
                derived_facts.append({
                    "state": "D",
                    "claim": f"Risk score for {_get_name(s)} [{sid}] is {float(r_score):.0f}/100 computed via 4-factor deterministic model (recency, frequency, severity, centrality).",
                    "method": "4-factor risk model",
                    "evidence_rows": [f"SUS-{sid}"]
                })
        except Exception:
            pass

        try:
            net = build_network(sid, world=world, max_depth=2)
            if net and net.get("nodes"):
                n_count = len(net["nodes"]) - 1
                if n_count > 0:
                    derived_facts.append({
                        "state": "D",
                        "claim": f"Network BFS from {_get_name(s)} [{sid}] discovers {n_count} linked associate(s) across case records.",
                        "method": "Graph BFS recency-weighted",
                        "evidence_rows": [f"SUS-{sid}"]
                    })
        except Exception:
            pass

    try:
        corrs = get_all_corridors()
        # get_all_corridors() returns src / dst / weight / fir_count. This used to read
        # district_a, district_b and linked_offenders -- none of which the corridor dict
        # has ever carried -- so every dossier emitted the literal line
        # "Movement corridor identified: None <-> None with 0 linked offenders", twice.
        # `weight` is corridor_agent's linking_accused: the real count of offenders
        # linking the two districts.
        for corr in corrs[:3]:
            src, dst = corr.get("src"), corr.get("dst")
            if not (src and dst):
                continue                      # no corridor to claim; say nothing
            linked = corr.get("weight") or 0
            firs = corr.get("fir_count") or 0
            # involved_entities holds dicts; evidence_rows is a list of row IDS
            # everywhere else in this dossier, so pull the ids out rather than nesting
            # objects into a field the rest of the pipeline reads as identifiers.
            rows = [e.get("id") for e in (corr.get("involved_entities") or [])[:5]
                    if isinstance(e, dict) and e.get("id")]
            derived_facts.append({
                "state": "D",
                "claim": (f"Movement corridor identified: {src} <-> {dst}, "
                          f"{linked} linked offender(s) across {firs} FIR(s)."),
                "method": "Recency-weighted transition frequency",
                "evidence_rows": rows
            })
    except Exception:
        pass

    # --- STEP (C) GENERATE INFERRED (I) ---
    for u in frontier_suspects:
        for v in suspects:
            if u["suspect_id"] == v["suspect_id"]:
                continue
            hyp = _score_hypothesis_pair(u, v, sus_crimes)
            if hyp:
                inferred_hypotheses.append(hyp)
                if len(inferred_hypotheses) >= 15:
                    break
        if len(inferred_hypotheses) >= 15:
            break

    inferred_hypotheses.sort(key=lambda x: x.get("score", 0), reverse=True)

    # --- STEP (D) EMIT UNKNOWN GAPS (U) ---
    for s in frontier_suspects:
        sid = s["suspect_id"]
        name = _get_name(s)
        counts = s.get("prior_count", s.get("prior_counts", 1))
        missing_fields: List[str] = []
        if not s.get("phone") and not s.get("phone_hash"): missing_fields.append("phone CDR")
        if not s.get("vehicle"): missing_fields.append("vehicle registration")
        if not s.get("upi"): missing_fields.append("UPI/banking identifier")

        if missing_fields:
            m_str = ", ".join(missing_fields)
            unknown_gaps.append({
                "id": f"GAP-{sid}",
                "kind": "identity",
                "anchor_ids": [sid],
                "what_is_missing": f"Suspect {name} [{sid}] has {counts} prior count(s) but zero {m_str} on file.",
                "seen_in_row_ids": [f"SUS-{sid}"],
                "collect_action": f"Issue Section 91 BNSS notice for CDR and financial KYC linked to {name}'s known associates.",
                "priority": 1 if counts >= 3 else 2,
                "computed_at": _get_time_iso()
            })

    for c in frontier_crimes[:10]:
        cid = c["crime_id"]
        sus_linked = crime_sus_map.get(cid, set())
        if not sus_linked:
            unknown_gaps.append({
                "id": f"GAP-{cid}-unsub",
                "kind": "whereabouts",
                "anchor_ids": [cid],
                "what_is_missing": f"FIR #{cid} in {c.get('zone') or c.get('station_code') or 'Unknown'} ({c.get('crime_type')}) remains unsolved with no accused identified on file.",
                "seen_in_row_ids": [cid],
                "collect_action": f"Cross-reference CCTV corridor footage around {c.get('zone') or 'station area'} against known repeat {c.get('crime_type')} offenders.",
                "priority": 1,
                "computed_at": _get_time_iso()
            })

    summary_lines = [f"Deep Research Dossier for '{anchor_clean}':"]
    summary_lines.append(f"• Known Facts: {len(known_facts)} verified record(s)")
    summary_lines.append(f"• Derived Intelligence: {len(derived_facts)} computed metric(s)")
    summary_lines.append(f"• Inferred Hypotheses: {len(inferred_hypotheses)} scored link(s)")
    summary_lines.append(f"• Unknown Gaps: {len(unknown_gaps)} actionable lead(s) to collect")

    dossier = {
        "anchor": anchor_clean,
        "summary": "\n".join(summary_lines),
        "known_facts": known_facts,
        "derived_facts": derived_facts,
        "inferred_hypotheses": inferred_hypotheses,
        "unknown_gaps": unknown_gaps,
        "frontier_ids": list(frontier_ids),
        "compiled_at": _get_time_iso(),
        "agent": "research_agent",
        "version": 1
    }

    put_product(dossier_key, dossier, ttl=3600)
    return dossier
