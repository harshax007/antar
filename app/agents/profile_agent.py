"""
Antar — Profile Agent (M5/M6, feature F5)
==============================================
Factor-transparent risk + grounded MO summary + brain-similar cases + rule-based leads.

  risk = 100 × (0.30·recency + 0.25·frequency + 0.25·severity + 0.20·centrality)

each factor min-max normalized over the whole dataset (Strategy §3.9). The score is
DETERMINISTIC and the four factor bars ARE the explanation — judges must see *why* 78.
No LLM required (works fully offline); the MO line is grounded in the suspect's rows.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from app.core.guardrails import evaluate_bias, calculate_shap_values

from app.services.zcql_local import _world

W = {"recency": 0.30, "frequency": 0.25, "severity": 0.25, "centrality": 0.20}


def _as_date(v):
    try:
        return date.fromisoformat(str(v or "")[:10])
    except ValueError:
        return None


def _raw_factors(world: dict) -> dict[str, dict]:
    """Per-suspect raw signals (pre-normalization)."""
    crimes_by_id = {c["crime_id"]: c for c in world["crimes"]}
    linked: dict[str, list] = {}
    for cs in world["crime_suspects"]:
        c = crimes_by_id.get(cs["crime_id"])
        if c:
            linked.setdefault(cs["suspect_id"], []).append(c)
    degree: dict[str, int] = {}
    for r in world["relationships"]:
        degree[r["suspect_a"]] = degree.get(r["suspect_a"], 0) + 1
        degree[r["suspect_b"]] = degree.get(r["suspect_b"], 0) + 1
    ref_now = max((_as_date(c["occurred_at"]) for c in world["crimes"] if _as_date(c["occurred_at"])),
                  default=date.today())
    raw = {}
    for s in world["suspects"]:
        sid = s["suspect_id"]
        cl = linked.get(sid, [])
        last = max((_as_date(c["occurred_at"]) for c in cl if _as_date(c["occurred_at"])), default=None)
        raw[sid] = {
            "frequency": len(cl),
            "severity": max((c.get("severity", 0) or 0 for c in cl), default=0),
            "centrality": degree.get(sid, 0),
            "recency_days": (ref_now - last).days if last else 99999,   # smaller = more recent
        }
    return raw


def _minmax(values: list[float]) -> tuple[float, float]:
    lo, hi = min(values), max(values)
    return lo, (hi - lo)


import time
_factors_cache = {"data": None, "ts": 0.0}

def _all_factors_and_risk(world: dict) -> dict[str, tuple]:
    global _factors_cache
    now = time.time()
    if _factors_cache["data"] is not None and (now - _factors_cache["ts"]) < 60.0:
        return _factors_cache["data"]

    raw = _raw_factors(world)
    f_lo, f_rng = _minmax([r["frequency"] for r in raw.values()])
    s_lo, s_rng = _minmax([r["severity"] for r in raw.values()])
    c_lo, c_rng = _minmax([r["centrality"] for r in raw.values()])
    r_lo, r_rng = _minmax([r["recency_days"] for r in raw.values()])

    def nz(v, lo, rng):
        return (v - lo) / rng if rng else 0.0

    out = {}
    for sid, r in raw.items():
        factors = {
            "frequency": round(nz(r["frequency"], f_lo, f_rng), 3),
            "severity": round(nz(r["severity"], s_lo, s_rng), 3),
            "centrality": round(nz(r["centrality"], c_lo, c_rng), 3),
            "recency": round(1 - nz(r["recency_days"], r_lo, r_rng), 3),   # recent → high risk
        }
        risk = round(100 * sum(W[k] * factors[k] for k in W), 1)
        out[sid] = (factors, risk, r)
    _factors_cache["data"] = out
    _factors_cache["ts"] = now
    return out


def risk_scores(world: dict | None = None) -> dict[str, float]:
    """{suspect_id: risk_score} for the whole dataset in one pass (used by the registry)."""
    return {sid: risk for sid, (f, risk, r) in _all_factors_and_risk(world or _world()).items()}


def _crimes_of(sid: str, world: dict) -> list[dict]:
    cids = {cs["crime_id"] for cs in world["crime_suspects"] if cs["suspect_id"] == sid}
    return [c for c in world["crimes"] if c["crime_id"] in cids]


def _mo_summary(s: dict, world: dict) -> str:
    crimes = _crimes_of(s["suspect_id"], world)
    if not crimes:
        return f"{s.get('full_name')} has no linked cases on record."
    from app.agents.display_names import display_crime
    types = ", ".join(display_crime(t, "en") for t, _ in Counter(c["crime_type"] for c in crimes).most_common(3))
    zones = ", ".join(z for z, _ in Counter(c["zone"] for c in crimes if c.get("zone")).most_common(2))
    return (f"{len(crimes)} linked case(s); primarily {types}"
            f"{f' in {zones}' if zones else ''}. Prior count {s.get('prior_count', 0)}; "
            f"arrest status {s.get('arrest_status', 'unknown')}.")


def _leads(sid: str, s: dict, world: dict) -> list[str]:
    leads: list[str] = []
    try:
        from app.second_brain.retrieval import find_cross_case_links
        for l in find_cross_case_links(sid, world).get("links", [])[:1]:
            if l.get("anchor_fir"):
                leads.append(f"Investigate cross-case link to FIR {l['anchor_fir']} "
                             f"({l.get('anchor_zone')}) — shared phone, "
                             f"{l.get('shared_contact_count', 0)} common contacts.")
    except Exception:
        pass
    if s.get("phone_hash"):
        leads.append("Request call records (CDR) for the suspect's phone number.")
    crimes = _crimes_of(sid, world)
    if crimes:
        zone = Counter(c["zone"] for c in crimes if c.get("zone")).most_common(1)
        if zone:
            leads.append(f"Check CCTV along the routes in {zone[0][0]} where the same method keeps repeating.")
    return leads[:4]


def _similar_cases(mo_text: str) -> list[dict]:
    """Top-3 similar past investigations from the brain (enrichment; [] if not seeded)."""
    try:
        from app.second_brain.retrieval import semantic_recall
        return [{"summary": h.get("summary_text"), "kind": h.get("kind"),
                 "score": round(h.get("score", 0), 3)}
                for h in (semantic_recall(mo_text, k=3) or [])][:3]
    except Exception:
        return []


def _associates(sid: str, world: dict) -> list[dict]:
    seen = set()
    assoc = []
    def get_name(s_id):
        from app.services import evidence_ledger
        s = {x["suspect_id"]: x for x in world["suspects"]}.get(s_id)
        if s: return s.get("full_name") or s.get("alias") or s_id
        ev = evidence_ledger.entity(s_id)
        if ev: return ev.get("alias") or s_id
        return s_id

    for r in world.get("relationships", []):
        if r["suspect_a"] == sid and r["suspect_b"] not in seen:
            seen.add(r["suspect_b"])
            assoc.append({"id": r["suspect_b"], "name": get_name(r["suspect_b"]), "reason": "Known relationship"})
        elif r["suspect_b"] == sid and r["suspect_a"] not in seen:
            seen.add(r["suspect_a"])
            assoc.append({"id": r["suspect_a"], "name": get_name(r["suspect_a"]), "reason": "Known relationship"})

    crimes = {cs["crime_id"] for cs in world.get("crime_suspects", []) if cs["suspect_id"] == sid}
    for c_id in crimes:
        for cs in world.get("crime_suspects", []):
            if cs["crime_id"] == c_id and cs["suspect_id"] != sid and cs["suspect_id"] not in seen:
                seen.add(cs["suspect_id"])
                assoc.append({"id": cs["suspect_id"], "name": get_name(cs["suspect_id"]), "reason": f"Co-accused in FIR {c_id}"})

    try:
        from app.services import evidence_ledger
        ev = evidence_ledger.entity(sid)
        if ev:
            all_ev = evidence_ledger._data()
            for other_id, other_data in all_ev.items():
                if other_id == sid or other_id in seen: continue
                reasons = []
                if set(ev.get("vehicles", [])) & set(other_data.get("vehicles", [])):
                    reasons.append("shared vehicle")
                if set(ev.get("upis", [])) & set(other_data.get("upis", [])):
                    reasons.append("shared UPI")
                if set(ev.get("phones", [])) & set(other_data.get("phones", [])):
                    reasons.append("shared phone")
                if reasons:
                    seen.add(other_id)
                    assoc.append({"id": other_id, "name": get_name(other_id), "reason": ", ".join(reasons)})
    except Exception:
        pass
    return assoc


def compute_profile(suspect_id: str, world: dict | None = None) -> dict | None:
    """Full profile for one suspect: risk + factors + MO + similar cases + leads."""
    world = world or _world()
    s = {x["suspect_id"]: x for x in world["suspects"]}.get(suspect_id)
    if not s:
        from app.services import evidence_ledger
        ev_entity = evidence_ledger.entity(suspect_id)
        if ev_entity:
            fir_count = ev_entity.get("fir_count", 1)
            risk = min(100, int(fir_count * 15))
            districts = ev_entity.get("districts", [])
            factors = {
                "frequency": round(min(1.0, fir_count / 10.0), 3),
                "severity": 0.5,
                "centrality": round(min(1.0, len(districts) / 5.0), 3),
                "recency": 0.8,
            }
            mo = f"Synthetic evidence ledger profile for {ev_entity['alias']}. Associated with {fir_count} FIR(s) across {', '.join(districts)}."
            bias_check = evaluate_bias(mo)
            risk_attributions = calculate_shap_values(factors, W)
            return {
                "suspect_id": suspect_id,
                "full_name": ev_entity["alias"],
                "alias": f"{ev_entity['alias']} (synthetic alias)",
                "risk_score": risk,
                "factors": factors,
                "raw_factors": {"frequency": fir_count, "severity": 5, "centrality": len(districts), "recency_days": 30},
                "risk_attributions": risk_attributions,
                "mo_summary": mo,
                "similar_cases": _similar_cases(mo),
                "leads": [f"Investigate {fir_count} linked FIR(s) in {', '.join(districts)}."] + ([f"Subpoena CDR / registration for associated vehicle/UPI."] if ev_entity.get("vehicles") or ev_entity.get("upis") else []),
                "associates": _associates(suspect_id, world),
                "anti_bias_cleared": bias_check["anti_bias_cleared"],
                "bias_warnings": bias_check["bias_warnings"],
                "source": "evidence",
                "evidence_details": ev_entity,
            }
        return None
    factors, risk, raw = _all_factors_and_risk(world)[suspect_id]
    mo = _mo_summary(s, world)
    bias_check = evaluate_bias(mo)
    
    if bias_check["bias_warnings"]:
        import structlog
        structlog.get_logger().warning("bias_detection_warning", suspect_id=suspect_id, warnings=bias_check["bias_warnings"])
        
    risk_attributions = calculate_shap_values(factors, W)
    
    return {
        "suspect_id": suspect_id, "full_name": s.get("full_name"), "alias": s.get("alias"),
        "risk_score": risk, "factors": factors, "raw_factors": raw,
        "risk_attributions": risk_attributions,
        "mo_summary": mo, "similar_cases": _similar_cases(mo), "leads": _leads(suspect_id, s, world),
        "associates": _associates(suspect_id, world),
        "anti_bias_cleared": bias_check["anti_bias_cleared"],
        "bias_warnings": bias_check["bias_warnings"]
    }
