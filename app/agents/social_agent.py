"""
Antar — Social Insight Agent (M4 / feature N6)
===================================================
Whitelisted demographic aggregations (via T7) + a crime×occupation correlation, with
MANDATORY framing: aggregate correlations only — never causal, never community-targeting
(Strategy §3.9; pre-empts the bias question §6.4 Q6). No LLM required (deterministic).
"""

from __future__ import annotations

from collections import Counter, defaultdict

from app.services.zcql_repo import build_spec
from app.services.zcql_local import run_query, _world

FRAMING = ("Aggregate correlations only. These patterns reflect crime reporting and socio-economic "
           "exposure — NOT causation — and must never be used to profile or target any individual or "
           "community. Intended for analysis and resource planning, not enforcement against groups.")


def _breakdown(entity: str, dimension: str, key: str) -> list[dict]:
    rows = run_query(build_spec("T7", {"entity": entity, "dimension": dimension}))
    return [{"label": r.get(key), "n": r.get("n", 0)} for r in rows if r.get(key) is not None]


def demographics() -> dict:
    """Victim + offender demographic breakdowns + crime×occupation correlation + framing."""
    world = _world()
    crimes = {c["crime_id"]: c for c in world["crimes"]}
    suspects = {s["suspect_id"]: s for s in world["suspects"]}

    corr: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    for cs in world["crime_suspects"]:
        c = crimes.get(cs["crime_id"])
        s = suspects.get(cs["suspect_id"])
        if c and s and s.get("occupation"):
            corr[c["crime_type"]][s["occupation"]] += 1
            totals[c["crime_type"]] += 1
    crime_occupation = [
        {"crime_type": t, "top_occupations": [{"label": o, "n": n} for o, n in corr[t].most_common(3)]}
        for t, _ in totals.most_common(6)
    ]

    return {
        "victims": {
            "gender": _breakdown("victims", "gender", "gender"),
            "age_band": _breakdown("victims", "age_band", "age_band"),
            "occupation": _breakdown("victims", "occupation", "occupation")[:8],
        },
        "offenders": {
            "gender": _breakdown("suspects", "gender", "gender"),
            "occupation": _breakdown("suspects", "occupation", "occupation")[:8],
        },
        "crime_occupation": crime_occupation,
        "framing": FRAMING,
    }
