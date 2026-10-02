"""
Antar — Devil's Advocate (adversarial hypothesis auditor)
=========================================================
Every other agent in Antar pushes TOWARD an answer. This one pushes back.

For policing the catastrophic failure is not a wrong count — it is confirmation bias
anchoring an investigation on the wrong person. `research_agent` emits scored
hypotheses ("S0195 is likely linked to S0260, score 0.85") by summing signal weights.
A weight sum is not evidence strength: it says nothing about how many OTHER people in
the population would produce the same signal.

This module answers the question the score cannot:

    "How surprising is this match, really?"

Three checks, all deterministic and offline:

  1. BASE RATE — for every signal, how many of the N suspects share that attribute
     value? A shared phone hash (2 of 2365) and a shared district (464 of 2365) both
     read as "corroboration" in a weighted sum. One is decisive, the other is noise.
     Measured as a likelihood ratio, LR = (N-1)/(n-1), reported in bits: log2(LR).

  2. SELECTION EFFECT — research_agent scans up to NODE_CAP x N pairs. At that volume
     some pairs clear any threshold by chance. We report the expected number of false
     matches at this evidence strength. When it is >= 1, the hypothesis is a scan
     artefact and says so. This is the prosecutor's fallacy, made arithmetic.

  3. FALSIFICATION — the specific, collectable evidence that would DISPROVE the leading
     hypothesis, phrased as an action with its statutory basis. Popper, with a BNSS
     section number attached.

Bayes, stated plainly:
    posterior odds = prior odds x LR(combined)
Prior odds come from the data (how often ARE two suspects associated?), never assumed.

Deliberately LLM-free. An adversarial check that can hallucinate is worse than none,
and every number here must be reproducible by hand from the row counts it cites.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from app.services.zcql_local import _world

AGENT_NAME = "devils_advocate"

# Evidence strength bands, in bits (log2 of the likelihood ratio).
# Calibrated to the Jeffreys/Kass-Raftery scale for Bayes factors, which is the
# convention a forensic statistician would expect to see in court.
_BANDS: Tuple[Tuple[float, str], ...] = (
    (10.0, "decisive"),      # LR >= ~1000
    (5.0, "strong"),         # LR >= ~32
    (3.3, "moderate"),       # LR >= ~10
    (1.6, "weak"),           # LR >= ~3
    (0.0, "negligible"),     # LR < 3 — indistinguishable from coincidence
)

# Signals worth less than this carry no real inferential load. 1.6 bits = LR 3.
_LOAD_BEARING_BITS = 1.6

# Posterior required for a SURVIVES verdict.
#
# NOT 0.5. For an identity hypothesis the prior is 1/N, so a single near-unique
# identifier (LR ~= N) lands the posterior on almost exactly 50% — by construction, not
# by coincidence. Calling a coin flip "SURVIVES" would be precisely the overconfidence
# this agent exists to prevent, and the verdict would hinge on the fourth decimal place.
# A hypothesis has to clear the balance of probabilities by a real margin, or it is
# WEAKENED and the officer is told to collect more.
_SURVIVES_POSTERIOR = 0.90


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _band(bits: float) -> str:
    for threshold, label in _BANDS:
        if bits >= threshold:
            return label
    return "negligible"


def _norm(v: Any) -> str:
    return str(v or "").strip().casefold()


def _name_of(s: Dict[str, Any]) -> str:
    return str(s.get("full_name") or s.get("name") or s.get("alias") or "Unknown").strip()


def _zone_of(s: Dict[str, Any]) -> str:
    return _norm(s.get("address_zone") or s.get("home_station") or s.get("district") or s.get("zone"))


def _mo_of(s: Dict[str, Any]) -> str:
    """The value research_agent actually compares for its 'MO similarity' signal.

    NOTE: it reads `primary_crime` first and falls back to `occupation`. In the current
    dataset `primary_crime` is empty on every row, so this signal is comparing JOBS.
    _assess_mo reports that explicitly rather than letting it pass as modus operandi.
    """
    return _norm(s.get("primary_crime") or s.get("occupation"))


def _mo_field(s: Dict[str, Any]) -> str:
    return "primary_crime" if _norm(s.get("primary_crime")) else "occupation"


# ── population index ──────────────────────────────────────────────────────────
class _Index:
    """Attribute value frequencies over the suspect population. Built once."""

    def __init__(self, world: Dict[str, Any]) -> None:
        suspects = world.get("suspects", []) or []
        crime_suspects = world.get("crime_suspects", []) or []

        self.suspects_by_id: Dict[str, Dict[str, Any]] = {
            s["suspect_id"]: s for s in suspects if s.get("suspect_id")
        }
        self.N = len(self.suspects_by_id)

        self.zone_counts: Dict[str, int] = {}
        self.mo_counts: Dict[str, int] = {}
        self.soundex_counts: Dict[str, int] = {}
        self.hardkey_counts: Dict[str, Dict[str, int]] = {"phone_hash": {}, "vehicle": {}, "upi": {}}
        # zone -> mo -> count, for conditional base rates (zone and occupation correlate)
        self.zone_mo_counts: Dict[str, Dict[str, int]] = {}

        from app.services.entity_resolver import soundex

        for s in suspects:
            z, mo = _zone_of(s), _mo_of(s)
            if z:
                self.zone_counts[z] = self.zone_counts.get(z, 0) + 1
            if mo:
                self.mo_counts[mo] = self.mo_counts.get(mo, 0) + 1
            if z and mo:
                self.zone_mo_counts.setdefault(z, {})
                self.zone_mo_counts[z][mo] = self.zone_mo_counts[z].get(mo, 0) + 1
            nm = _name_of(s)
            if nm and nm != "Unknown":
                try:
                    code = soundex(nm)
                except Exception:                      # noqa: BLE001 — index build must not fail
                    code = ""
                if code:
                    self.soundex_counts[code] = self.soundex_counts.get(code, 0) + 1
            for field in ("phone_hash", "vehicle", "upi"):
                val = _norm(s.get(field) or (s.get("phone") if field == "phone_hash" else None))
                if val:
                    self.hardkey_counts[field][val] = self.hardkey_counts[field].get(val, 0) + 1

        # co-accusal graph, for the association prior and the Adamic-Adar assessment
        self.crime_to_suspects: Dict[str, set] = {}
        self.suspect_to_crimes: Dict[str, set] = {}
        for cs in crime_suspects:
            sid, cid = cs.get("suspect_id"), cs.get("crime_id")
            if not sid or not cid:
                continue
            self.crime_to_suspects.setdefault(cid, set()).add(sid)
            self.suspect_to_crimes.setdefault(sid, set()).add(cid)

        degrees = []
        for sid, cids in self.suspect_to_crimes.items():
            peers = set()
            for cid in cids:
                peers |= self.crime_to_suspects.get(cid, set())
            peers.discard(sid)
            degrees.append(len(peers))
        self.mean_co_accused = (sum(degrees) / len(degrees)) if degrees else 0.0

        # Unconditional collision rates, for the multiple-comparisons arithmetic only.
        # Keyed by signal kind; see _collision_p for why these are not 1/LR.
        self.collision: Dict[str, float] = {
            "zone": _collision_p(self.zone_counts, self.N),
            "mo": _collision_p(self.mo_counts, self.N),
            "phonetic": _collision_p(self.soundex_counts, self.N),
            "hard_key": max(_collision_p(c, self.N) for c in self.hardkey_counts.values()),
            "co_accusal": _collision_p(
                {cid: len(s) for cid, s in self.crime_to_suspects.items()}, self.N),
        }

    def co_accused_of(self, sid: str) -> set:
        peers = set()
        for cid in self.suspect_to_crimes.get(sid, set()):
            peers |= self.crime_to_suspects.get(cid, set())
        peers.discard(sid)
        return peers


@lru_cache(maxsize=1)
def _index_cached() -> _Index:
    return _Index(_world() if callable(_world) else _world)


def reset_index() -> None:
    """Drop the cached population index (tests, and after a re-ingest)."""
    _index_cached.cache_clear()


# ── likelihood ratio from a frequency count ───────────────────────────────────
def _collision_p(counts: Dict[str, int], population: int) -> float:
    """P(a RANDOM pair shares this attribute at all) = sum(n_v choose 2) / (N choose 2).

    This is NOT the same quantity as the per-signal likelihood ratio, and conflating the
    two is a real trap. The LR answers "given this suspect holds value v, how surprising
    is it that the other one does too" — conditional on v. The multiple-comparisons
    question is different: "sweeping a million pairs, how often does ANY pair collide on
    this attribute at all", which has to average over the whole value distribution.

    Using the LR here made a shared phone hash (2 of 2365, genuinely decisive) look like
    a scan artefact, because 1/LR treats every value as if it were as common as the one
    observed. Most phone hashes are unique, so real collisions are vanishingly rare.
    """
    if population <= 1:
        return 1.0
    pairs_total = population * (population - 1)
    colliding = sum(n * (n - 1) for n in counts.values() if n >= 2)
    return min(1.0, colliding / pairs_total) if pairs_total else 1.0


def _lr_from_count(n_sharing: int, population: int) -> Tuple[float, float, float]:
    """(p_coincidence, likelihood_ratio, bits) for an attribute held by n of N.

    p_coincidence = (n-1)/(N-1): given one suspect holds the value, the chance that a
    second, randomly chosen suspect also holds it. LR = 1/p under the (stated, and
    generous to the hypothesis) assumption P(signal | hypothesis true) = 1.

    Being generous here is deliberate: every modelling choice in this module favours
    the hypothesis, so a COLLAPSES verdict is conservative and hard to argue with.
    """
    if population <= 1:
        return 1.0, 1.0, 0.0
    n = max(2, int(n_sharing))                     # both subjects hold it, so n >= 2
    p = (n - 1) / (population - 1)
    p = min(1.0, max(p, 1.0 / (population - 1)))
    lr = 1.0 / p
    return p, lr, math.log2(lr)


def _assessment(*, signal: str, kind: str, attribute: str, shared_value: str,
                n_sharing: int, population: int, why: str, collision_p: float,
                conditional_on: Optional[str] = None) -> Dict[str, Any]:
    p, lr, bits = _lr_from_count(n_sharing, population)
    return {
        "signal": signal,
        "signal_kind": kind,
        "attribute": attribute,
        "shared_value": shared_value,
        "n_sharing": int(n_sharing),
        "population": int(population),
        "conditional_on": conditional_on,
        # evidential strength for the Bayes update (conditional on the observed value)
        "p_coincidence": round(p, 6),
        "likelihood_ratio": round(lr, 1),
        "bits": round(bits, 2),
        "strength": _band(bits),
        "load_bearing": bits >= _LOAD_BEARING_BITS,
        # unconditional pair-collision rate, for the selection-effect arithmetic only
        "collision_p": round(collision_p, 9),
        "why": why,
    }


# ── per-signal assessors ──────────────────────────────────────────────────────
def _assess_hard_key(u, v, idx, signal) -> Optional[Dict[str, Any]]:
    for field, label in (("phone_hash", "phone hash"), ("vehicle", "vehicle registration"),
                         ("upi", "UPI identifier")):
        a = _norm(u.get(field) or (u.get("phone") if field == "phone_hash" else None))
        b = _norm(v.get(field) or (v.get("phone") if field == "phone_hash" else None))
        if a and a == b:
            n = idx.hardkey_counts[field].get(a, 2)
            return _assessment(
                signal=signal, kind="hard_key", attribute=field, shared_value=a,
                n_sharing=n, population=idx.N, collision_p=idx.collision["hard_key"],
                why=(f"{n} of {idx.N} suspects carry this {label}. A hard identifier is "
                     "near-unique, so a match is genuinely surprising — this is real "
                     "evidence, not a coincidence of demographics."),
            )
    return None


def _assess_phonetic(u, v, idx, signal) -> Optional[Dict[str, Any]]:
    from app.services.entity_resolver import soundex
    try:
        code = soundex(_name_of(u))
    except Exception:                                  # noqa: BLE001
        return None
    if not code:
        return None
    n = idx.soundex_counts.get(code, 2)
    return _assessment(
        signal=signal, kind="phonetic", attribute="soundex(full_name)", shared_value=code,
        n_sharing=n, population=idx.N, collision_p=idx.collision["phonetic"],
        why=(f"{n} of {idx.N} suspects share the Soundex code '{code}'. Phonetic "
             "similarity is a SEARCH heuristic, not an identity finding — it cannot "
             "distinguish two different people who happen to have similar names."),
    )


def _assess_co_accusal(u, v, idx, signal) -> Optional[Dict[str, Any]]:
    shared = idx.suspect_to_crimes.get(u["suspect_id"], set()) & \
             idx.suspect_to_crimes.get(v["suspect_id"], set())
    if not shared:
        return None
    # Discriminating power = how many suspects are reachable as co-accused of u at all.
    peers = idx.co_accused_of(u["suspect_id"])
    n = max(2, len(peers) + 1)
    biggest = max((len(idx.crime_to_suspects.get(c, set())) for c in shared), default=0)
    mass = biggest >= 8
    why = (f"{_name_of(u)} is co-accused with {len(peers)} of {idx.N} suspects across the "
           f"record. Co-accusal on a specific FIR is a documented fact, not an inference.")
    if mass:
        why += (f" CAUTION: the shared FIR names {biggest} accused — a mass-accusal event "
                "(riot, raid, sweep) where co-accusal implies nothing about association.")
    a = _assessment(
        signal=signal, kind="co_accusal", attribute="shared FIR",
        shared_value=", ".join(sorted(shared)[:3]), n_sharing=n, population=idx.N, why=why,
        collision_p=idx.collision["co_accusal"],
    )
    a["shared_case_ids"] = sorted(shared)[:5]
    a["largest_shared_case_accused_count"] = biggest
    a["mass_accusal_warning"] = mass
    if mass:                       # a sweep is not evidence of association — strip the load
        a["load_bearing"] = False
    return a


def _assess_zone(u, v, idx, signal) -> Optional[Dict[str, Any]]:
    z = _zone_of(u)
    if not z or z != _zone_of(v):
        return None
    n = idx.zone_counts.get(z, 2)
    share = n / idx.N if idx.N else 0
    return _assessment(
        signal=signal, kind="zone", attribute="address_zone", shared_value=z,
        n_sharing=n, population=idx.N, collision_p=idx.collision["zone"],
        why=(f"{n} of {idx.N} suspects ({share:.1%}) are recorded in this zone. Two people "
             "living in the same district is the NORMAL case, not a link. Co-presence "
             "only becomes evidence when it is placed at a specific time and place."),
    )


def _assess_mo(u, v, idx, signal) -> Optional[Dict[str, Any]]:
    mo = _mo_of(u)
    if not mo or mo != _mo_of(v):
        return None
    field = _mo_field(u)
    zone = _zone_of(u)
    # Zone and occupation correlate, so scoring both at their global rates double-counts.
    # When the pair also shares a zone, price this signal at its WITHIN-ZONE rate.
    if zone and zone == _zone_of(v) and idx.zone_mo_counts.get(zone, {}).get(mo):
        n, pop, cond = idx.zone_mo_counts[zone][mo], idx.zone_counts.get(zone, 1), zone
    else:
        n, pop, cond = idx.mo_counts.get(mo, 2), idx.N, None

    why = (f"{n} of {pop} suspects{f' in {cond}' if cond else ''} share the value "
           f"'{mo}' in field `{field}`.")
    if field == "occupation":
        why += (" WARNING: this is labelled 'MO similarity' but `primary_crime` is empty on "
                "these records, so research_agent has fallen back to `occupation`. A shared "
                "JOB is not a shared modus operandi and must not be scored as one.")
    if cond:
        why += (" Priced at the within-zone rate because zone and occupation are correlated; "
                "the global rate would double-count the zone signal.")

    a = _assessment(signal=signal, kind="mo", attribute=field, shared_value=mo,
                    n_sharing=n, population=pop, why=why, conditional_on=cond,
                    collision_p=idx.collision["mo"])
    a["mislabelled_as_mo"] = (field == "occupation")
    if field == "occupation":
        a["load_bearing"] = False      # a job title is never load-bearing for association
    return a


_ASSESSORS = (
    ("shared hard key", _assess_hard_key),
    ("phonetic identity", _assess_phonetic),
    ("adamic-adar", _assess_co_accusal),
    ("spatiotemporal co-presence", _assess_zone),
    ("mo similarity", _assess_mo),
)


# ── falsification tests ───────────────────────────────────────────────────────
def _falsification_for(a: Dict[str, Any], u, v) -> Optional[Dict[str, Any]]:
    k, un, vn = a["signal_kind"], _name_of(u), _name_of(v)
    if k == "hard_key":
        return {
            "test": f"Establish whether the shared {a['attribute']} is a personal or a shared device/account.",
            "would_disprove": ("A family, employer, PCO or recycled-number subscriber record "
                               "explains the match with no association between the two."),
            "collect_action": f"Subscriber KYC and call-detail records for {a['shared_value']}.",
            "statute": "BNSS Sec 94 (production of documents)",
        }
    if k == "phonetic":
        return {
            "test": f"Compare father_name, age, and address history for {un} and {vn}.",
            "would_disprove": ("Different parentage or an age gap inconsistent with one person "
                               "refutes identity outright; the name similarity is then coincidence."),
            "collect_action": "Pull both suspect records and compare non-name identifiers.",
            "statute": "Internal record comparison — no warrant required",
        }
    if k == "co_accusal":
        base = {
            "test": f"Read the shared FIR(s) {', '.join(a.get('shared_case_ids', []))} and establish the ROLE of each accused.",
            "would_disprove": ("Co-accusal in a single incident with no prior or subsequent "
                               "contact is an event, not a relationship."),
            "collect_action": "Retrieve the case diary and charge-sheet roles for the shared FIR.",
            "statute": "BNSS Sec 193 (police report)",
        }
        if a.get("mass_accusal_warning"):
            base["test"] = (f"Confirm whether the shared FIR is a mass-accusal event "
                            f"({a.get('largest_shared_case_accused_count')} accused named).")
            base["would_disprove"] = ("If it is a sweep, riot or raid, co-accusal carries no "
                                      "information about association at all.")
        return base
    if k == "zone":
        return {
            "test": "Establish TEMPORAL overlap, not just shared residence.",
            "would_disprove": ("Without placing both at the same location at the same time, "
                               f"shared residence in a zone holding {a['n_sharing']} suspects "
                               "is not evidence of anything."),
            "collect_action": "Tower-dump or CCTV corridor correlation at the incident windows.",
            "statute": "BNSS Sec 94 / Sec 106 (electronic records) — requires authorisation",
        }
    if k == "mo":
        if a.get("mislabelled_as_mo"):
            return {
                "test": "Do not treat this signal as an MO match at all.",
                "would_disprove": (f"The shared value '{a['shared_value']}' is an occupation, not "
                                   "a modus operandi. `primary_crime` is empty on these records, "
                                   "so there is no MO evidence here to test."),
                "collect_action": ("Populate `primary_crime` from charge-sheet history before this "
                                   "signal is used, or disable it."),
                "statute": "Data-quality defect — not an investigative lead",
            }
        return {
            "test": "Compare MO SUB-FEATURES (entry method, timing, tool, target selection), not the crime-type label.",
            "would_disprove": ("Two offenders in the same crime category with different execution "
                               "signatures are not linked by MO."),
            "collect_action": "Extract MO sub-features from both case diaries and compare.",
            "statute": "Internal record comparison — no warrant required",
        }
    return None


# ── alternative explanations ──────────────────────────────────────────────────
def _alternatives(assessments, u, v, idx, selection) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    weak = [a for a in assessments if not a["load_bearing"]]
    strong = [a for a in assessments if a["load_bearing"]]
    un, vn = _name_of(u), _name_of(v)

    if weak and not strong:
        traits = "; ".join(f"{a['attribute']}={a['shared_value']} ({a['n_sharing']}/{a['population']})"
                           for a in weak)
        out.append({
            "claim": (f"{un} and {vn} are two unconnected people who share the modal profile of "
                      f"this population. Nothing links them beyond traits that thousands share."),
            "supported_by": traits,
            "strength": "stronger than the hypothesis",
        })

    # Fires on weak strength, not merely on non-load-bearing: an LR of ~5 clears the
    # load-bearing floor but a 1-in-5 base rate still deserves to be said out loud.
    zone = next((a for a in assessments if a["signal_kind"] == "zone"), None)
    if zone and zone["strength"] in ("weak", "negligible"):
        out.append({
            "claim": (f"The zone match is a sampling artefact: {zone['n_sharing']} of "
                      f"{zone['population']} suspects sit in '{zone['shared_value']}', so any pair "
                      "drawn from this dataset is likely to share it."),
            "supported_by": f"address_zone base rate {zone['n_sharing']}/{zone['population']}",
            "strength": "competing",
        })

    mo = next((a for a in assessments if a.get("mislabelled_as_mo")), None)
    if mo:
        out.append({
            "claim": (f"There is no MO evidence in this hypothesis. The 'MO similarity' signal "
                      f"resolved to the shared occupation '{mo['shared_value']}' because "
                      "`primary_crime` is empty on both records."),
            "supported_by": f"field `occupation`, {mo['n_sharing']}/{mo['population']}",
            "strength": "refutes the signal",
        })

    co = next((a for a in assessments if a["signal_kind"] == "co_accusal"), None)
    if co and co.get("mass_accusal_warning"):
        out.append({
            "claim": (f"Both were swept into the same mass-accusal event "
                      f"({co['largest_shared_case_accused_count']} accused named on one FIR); "
                      "they need never have met."),
            "supported_by": f"shared FIR {', '.join(co.get('shared_case_ids', []))}",
            "strength": "stronger than the hypothesis",
        })
    elif co:
        out.append({
            "claim": (f"{un} and {vn} were co-accused in a single incident and have no other "
                      "connection — an event, not an ongoing association."),
            "supported_by": f"shared FIR {', '.join(co.get('shared_case_ids', []))}",
            "strength": "competing",
        })

    if selection.get("prosecutors_fallacy_risk"):
        out.append({
            "claim": (f"This pair is a scan artefact. Up to {selection['pairs_examined']:,} pairs "
                      f"are swept; roughly {selection['expected_false_matches']:.1f} would reach "
                      "this evidence strength by chance alone."),
            "supported_by": "multiple-comparison arithmetic over the hypothesis scan",
            "strength": "stronger than the hypothesis",
        })
    return out


# ── main entry points ─────────────────────────────────────────────────────────
def challenge(hypothesis: Dict[str, Any], *, world: Optional[Dict[str, Any]] = None,
              pairs_examined: Optional[int] = None) -> Dict[str, Any]:
    """Audit one hypothesis. Never raises; returns an 'unassessable' record instead."""
    idx = _Index(world) if world is not None else _index_cached()
    subject_ids = hypothesis.get("subject_ids") or []
    u = idx.suspects_by_id.get(subject_ids[0]) if len(subject_ids) > 0 else None
    v = idx.suspects_by_id.get(subject_ids[1]) if len(subject_ids) > 1 else None

    base = {
        "hypothesis_id": hypothesis.get("id"),
        "original_claim": hypothesis.get("claim"),
        "original_score": hypothesis.get("score"),
        "kind": hypothesis.get("kind"),
        "population": idx.N,
        "agent": AGENT_NAME,
        "compiled_at": _now(),
        "method": "frequency-based likelihood ratios; no LLM, no sampling",
    }
    if not u or not v:
        return {**base, "verdict": "UNASSESSABLE",
                "verdict_reason": "one or both subjects are not resolvable in the suspect table",
                "signals": [], "alternatives": [], "falsification_tests": []}

    # 1. assess every declared signal
    assessments: List[Dict[str, Any]] = []
    for sig in hypothesis.get("signals") or []:
        nm = str(sig.get("name") or "")
        low = nm.casefold()
        matched = False
        for key, fn in _ASSESSORS:
            if key in low:
                a = fn(u, v, idx, nm)
                if a:
                    a["original_weight"] = sig.get("weight")
                    assessments.append(a)
                matched = True
                break
        if not matched:
            assessments.append({
                "signal": nm, "signal_kind": "unknown", "attribute": None,
                "shared_value": None, "n_sharing": 0, "population": idx.N,
                "p_coincidence": None, "likelihood_ratio": None, "bits": 0.0,
                "collision_p": 1.0,
                "strength": "unassessed", "load_bearing": False,
                "why": "no base rate is computable for this signal — it is not counted either way.",
                "original_weight": sig.get("weight"),
            })

    # 2. combine (independence is ASSUMED and declared; correlated pairs are already
    #    priced conditionally in _assess_mo)
    total_bits = sum(a["bits"] for a in assessments if a["load_bearing"])
    combined_lr = 2.0 ** total_bits

    # 3. prior odds FROM THE DATA, never assumed
    if hypothesis.get("kind") == "identity":
        prior_odds = 1.0 / max(1, idx.N - 1)
        prior_basis = (f"any specific pair of the {idx.N} suspects being the same person: "
                       f"1 in {idx.N - 1}")
    else:
        prior_odds = idx.mean_co_accused / max(1, idx.N - 1)
        prior_basis = (f"mean co-accused per suspect ({idx.mean_co_accused:.2f}) over "
                       f"{idx.N - 1} candidates")

    posterior_odds = prior_odds * combined_lr
    posterior_p = posterior_odds / (1.0 + posterior_odds)

    # 4. selection effect — the prosecutor's fallacy, as arithmetic
    from app.agents.research_agent import NODE_CAP
    pairs = int(pairs_examined or (NODE_CAP * idx.N))
    # Product of the UNCONDITIONAL collision rates of the load-bearing signals — not
    # 1/LR. Only load-bearing signals are multiplied: each extra factor drives the
    # estimate down, so including the weak ones would make the check less sceptical,
    # and correlated factors (zone x occupation) would compound that error.
    p_combined = 1.0
    for a in assessments:
        if a["load_bearing"] and a.get("collision_p"):
            p_combined *= a["collision_p"]
    expected_fp = pairs * p_combined
    selection = {
        # Upper bound on the scan space, not a count of executed comparisons:
        # research_agent stops early once it has collected enough hypotheses. The
        # selection pressure is a property of the space it sweeps, so the bound is the
        # right figure — but it is labelled as a bound rather than passed off as exact.
        "pairs_examined": pairs,
        "pairs_examined_is_upper_bound": True,
        "p_this_evidence_by_chance": round(p_combined, 10),
        "expected_false_matches": round(expected_fp, 2),
        "prosecutors_fallacy_risk": expected_fp >= 1.0,
        "basis": ("product of unconditional pair-collision rates over the load-bearing "
                  "signals; correlated signals make this an UNDER-estimate of chance matches"),
        "note": (f"Up to {pairs:,} pairs are swept to surface this hypothesis. At this evidence "
                 f"strength about {expected_fp:.1f} of them would match by chance alone."
                 + ("  A match this weak is EXPECTED in a scan this large and cannot be "
                    "treated as a finding." if expected_fp >= 1.0 else
                    "  Fewer than one chance match is expected, so the finding survives the scan.")),
    }

    # 5. verdict
    load_bearing = [a for a in assessments if a["load_bearing"]]
    discarded = [a for a in assessments if not a["load_bearing"]]
    if not load_bearing:
        verdict = "COLLAPSES"
        reason = ("No signal survives its base rate. Every shared attribute is common enough in "
                  "this population that the match carries no information.")
    elif selection["prosecutors_fallacy_risk"]:
        verdict = "COLLAPSES"
        reason = (f"Expected false matches at this strength is {expected_fp:.1f} across "
                  f"{pairs:,} compared pairs — this is a scan artefact, not a lead.")
    elif posterior_p < _SURVIVES_POSTERIOR:
        verdict = "WEAKENED"
        reason = (f"Evidence is real ({total_bits:.1f} bits) but does not clear the prior by a "
                  f"usable margin: posterior {posterior_p:.1%}, against the "
                  f"{_SURVIVES_POSTERIOR:.0%} required. Collect more before acting on this.")
    elif discarded:
        verdict = "WEAKENED"
        reason = (f"{len(load_bearing)} of {len(assessments)} signals carry the inference; "
                  f"{len(discarded)} look like corroboration but are population-typical.")
    else:
        verdict = "SURVIVES"
        reason = (f"{total_bits:.1f} bits of evidence, posterior {posterior_p:.1%}, and fewer "
                  "than one expected chance match. Every signal is genuinely discriminating.")

    tests, seen = [], set()
    for a in assessments:
        t = _falsification_for(a, u, v)
        if t and t["test"] not in seen:
            seen.add(t["test"])
            tests.append(t)

    return {
        **base,
        "subjects": [{"suspect_id": u["suspect_id"], "name": _name_of(u)},
                     {"suspect_id": v["suspect_id"], "name": _name_of(v)}],
        "prior": {"odds": round(prior_odds, 8),
                  "probability": round(prior_odds / (1 + prior_odds), 8),
                  "basis": prior_basis},
        "signals": assessments,
        "load_bearing_signals": [a["signal"] for a in load_bearing],
        "discarded_signals": [{"signal": a["signal"], "reason": a["strength"],
                               "base_rate": f"{a['n_sharing']}/{a['population']}"}
                              for a in discarded],
        "combined": {
            "bits": round(total_bits, 2),
            "likelihood_ratio": round(combined_lr, 1),
            "strength": _band(total_bits),
            "posterior_probability": round(posterior_p, 4),
            "independence_caveat": ("Signals are combined as if conditionally independent. "
                                    "Correlated pairs (zone x occupation) are already priced "
                                    "conditionally; any residual correlation means the combined "
                                    "figure OVERSTATES the evidence."),
        },
        "selection_effect": selection,
        "alternatives": _alternatives(assessments, u, v, idx, selection),
        "falsification_tests": tests,
        "verdict": verdict,
        "verdict_reason": reason,
    }


def challenge_dossier(dossier: Dict[str, Any], *,
                      world: Optional[Dict[str, Any]] = None,
                      limit: int = 10) -> Dict[str, Any]:
    """Audit every inferred hypothesis in a research dossier. Returns a rebuttal record."""
    hyps = (dossier.get("inferred_hypotheses") or [])[:limit]
    idx = _Index(world) if world is not None else _index_cached()
    pairs = len(dossier.get("frontier_ids") or []) * idx.N or None

    challenges = [challenge(h, world=world, pairs_examined=pairs) for h in hyps]
    tally = {"SURVIVES": 0, "WEAKENED": 0, "COLLAPSES": 0, "UNASSESSABLE": 0}
    for c in challenges:
        tally[c["verdict"]] = tally.get(c["verdict"], 0) + 1

    lines = [f"Adversarial review of '{dossier.get('anchor')}' — {len(challenges)} hypothesis(es) challenged:",
             f"• {tally['COLLAPSES']} collapse under their own base rates",
             f"• {tally['WEAKENED']} survive but rest on fewer signals than claimed",
             f"• {tally['SURVIVES']} withstand the challenge"]
    if tally["UNASSESSABLE"]:
        lines.append(f"• {tally['UNASSESSABLE']} could not be assessed (subjects unresolvable)")

    defects = sorted({a["why"].split(" WARNING: ")[1].split(".")[0] + "."
                      for c in challenges for a in c.get("signals", [])
                      if a.get("mislabelled_as_mo") and " WARNING: " in a.get("why", "")})
    if defects:
        lines.append("• data-quality defect detected — see `systemic_defects`")

    return {
        "anchor": dossier.get("anchor"),
        "summary": "\n".join(lines),
        "tally": tally,
        "challenges": challenges,
        "systemic_defects": defects,
        "population": idx.N,
        "agent": AGENT_NAME,
        "compiled_at": _now(),
    }


def run(anchor: str, *, world: Optional[Dict[str, Any]] = None,
        limit: int = 10) -> Dict[str, Any]:
    """Convenience: build the dossier for `anchor`, then argue against it."""
    from app.agents.research_agent import run_research
    from app.services.product_store import put_product

    dossier = run_research(anchor, world=world)
    rebuttal = challenge_dossier(dossier, world=world, limit=limit)
    try:
        put_product(f"devils_advocate:{(anchor or '').strip().lower()}", rebuttal, ttl=3600)
    except Exception:                                  # noqa: BLE001 — cache is best-effort
        pass
    return rebuttal
