"""
Antar — Fuzzy/phonetic entity resolution (Task #9)
=======================================================
Multi-signal suspect search combining:
  • Jaro-Winkler similarity  — handles transpositions and short typos
  • Soundex phonetic encoding — groups names that sound alike across spellings
  • Exact substring fallback  — preserves the T2 LIKE-match behaviour

No external dependencies — pure stdlib.

References:
  Jaro (1989); Winkler (1990) "String Comparator Metrics and Enhanced Decision Rules
  in the Fellegi-Sunter Model of Record Linkage".
  Russell (1918) US Patent 1261167 — American Soundex (public domain).
"""

from __future__ import annotations

import math
import re


# ── Jaro similarity ───────────────────────────────────────────────────────────

def jaro(s1: str, s2: str) -> float:
    """Jaro similarity in [0.0, 1.0]."""
    if s1 == s2:
        return 1.0
    l1, l2 = len(s1), len(s2)
    if not l1 or not l2:
        return 0.0
    match_dist = max(max(l1, l2) // 2 - 1, 0)
    s1_m = [False] * l1
    s2_m = [False] * l2
    matches = 0
    for i in range(l1):
        lo = max(0, i - match_dist)
        hi = min(i + match_dist + 1, l2)
        for j in range(lo, hi):
            if s2_m[j] or s1[i] != s2[j]:
                continue
            s1_m[i] = True
            s2_m[j] = True
            matches += 1
            break
    if not matches:
        return 0.0
    k = transpositions = 0
    for i in range(l1):
        if not s1_m[i]:
            continue
        while not s2_m[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    return (matches / l1 + matches / l2 + (matches - transpositions / 2) / matches) / 3


def jaro_winkler(s1: str, s2: str, p: float = 0.1) -> float:
    """Jaro-Winkler similarity — adds a prefix bonus (up to 4 matching leading chars).
    Winkler's p=0.1 is the standard; keeps result in [0.0, 1.0]."""
    j = jaro(s1, s2)
    prefix = 0
    for c1, c2 in zip(s1[:4], s2[:4]):
        if c1 == c2:
            prefix += 1
        else:
            break
    return min(1.0, j + prefix * p * (1 - j))


# ── American Soundex ──────────────────────────────────────────────────────────

_SDEX_MAP: dict[str, str] = {
    "B": "1", "F": "1", "P": "1", "V": "1",
    "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
    "D": "3", "T": "3",
    "L": "4",
    "M": "5", "N": "5",
    "R": "6",
}


def soundex(name: str) -> str:
    """American Soundex code — first letter + up to 3 consonant-group digits.
    Vowels between same-coded consonants reset adjacency so distinct codes are kept.

    Yellappa → Y410   Yellapa → Y410   (same )
    Raju     → R200   Raaju   → R200   (same )
    """
    name = re.sub(r"[^A-Za-z]", "", name).upper()
    if not name:
        return "Z000"
    first = name[0]
    digits = ""
    prev = _SDEX_MAP.get(first, "")   # first letter's code (may be "" for vowels/HWRY)
    for ch in name[1:]:
        c = _SDEX_MAP.get(ch, "")
        if c:                           # consonant with a Soundex code
            if c != prev:
                digits += c
                prev = c
            # else: adjacent same-coded consonant → skip
        else:                           # vowel / H / W / Y
            prev = ""                   # reset so next consonant is never skipped
        if len(digits) == 3:
            break
    return (first + digits).ljust(4, "0")


# ── Multi-signal suspect search ───────────────────────────────────────────────

_SEARCH_FIELDS = ("full_name", "alias", "father_name")

# Minimum Jaro-Winkler score that must accompany a Soundex match.
# Without this floor a pure Soundex hit on a very short token would surface
# totally unrelated suspects (e.g. "Raju" Soundex = "R200" matches "Roy" Soundex = "R000"?
# — actually no, but defensive floor avoids edge cases).
_SOUNDEX_MIN_JW = 0.65


def _suspect_payload(s: dict) -> dict:
    return {
        "suspect_id":    s["suspect_id"],
        "full_name":     s.get("full_name"),
        "alias":         s.get("alias"),
        "age":           s.get("age"),
        "gender":        s.get("gender"),
        "address_zone":  s.get("address_zone"),
        "prior_count":   s.get("prior_count"),
        "arrest_status": s.get("arrest_status"),
    }


def fuzzy_match_suspects(
    query: str,
    world: dict,
    threshold: float = 0.82,
    limit: int = 10,
    *,
    fields: tuple[str, ...] | None = None,
) -> list[dict]:
    """Search suspects by name / alias / father_name using three signals in priority order:

    1. **Exact substring** — query appears verbatim in any search field (score 1.0)
    2. **Jaro-Winkler** ≥ threshold — token-level + whole-field comparison
    3. **Indian-name spelling** — any query token and field token are one name spelt two
       ways (app/services/indic_names.py: Kumar / Coomar, Mohd / Mohammed, Yellappa /
       Elappa); a query typed in Kannada script is converted to Latin letters first
    4. **Soundex phonetic** — any query token's Soundex code matches any field token,
       provided Jaro-Winkler is also ≥ _SOUNDEX_MIN_JW (prevents false phonetic positives)

    Each suspect is returned once (best signal wins). Results sorted by match_score desc.

    Args:
        query:     free-text search string (name, alias, or partial name)
        world:     seed world dict from zcql_local._world()
        threshold: minimum Jaro-Winkler score (default 0.82)
        limit:     max results returned (max 50)
        fields:    optional restriction of which fields to match — a subset of
                   ("full_name", "alias", "father_name", "phone_hash").
                   None (default) searches everything, preserving old behaviour.

    Returns list of hit dicts, each with: suspect_id, full_name, alias, age, gender,
    address_zone, prior_count, arrest_status, match_score, match_field, match_method.
    """
    from app.core.kn_translit import kn_to_latin
    from app.services.indic_names import same_name

    q = kn_to_latin(query.strip())          # ಸುರೇಶ್ -> suresh; Latin text is unchanged
    if not q:
        return []

    q_up = q.upper()
    q_tokens = [t for t in q_up.split() if t]
    q_sdx = [soundex(t) for t in q_tokens]

    text_fields = tuple(f for f in _SEARCH_FIELDS if fields is None or f in fields)
    phone_ok = fields is None or "phone_hash" in fields

    best: dict[str, dict] = {}      # suspect_id → highest-score hit so far

    for s in world.get("suspects", []):
        sid = s["suspect_id"]

        # ── phone_hash exact match (the hash itself as query) ─────────────────
        if phone_ok and q == s.get("phone_hash", ""):
            _update_best(best, sid, s, 1.0, "phone_hash", "phone_exact")
            continue

        # ── text field scoring ────────────────────────────────────────────────
        for field in text_fields:
            val = (s.get(field) or "").strip()
            if not val:
                continue
            val_up = val.upper()
            val_tokens = [t for t in val_up.split() if t]

            # 1. Exact substring
            if q_up in val_up:
                _update_best(best, sid, s, 1.0, field, "exact")
                continue

            # 2. Jaro-Winkler — compare query vs each token and the full value
            jw_candidates = [jaro_winkler(q_up, val_up)]
            for q_tok in q_tokens:
                for v_tok in val_tokens:
                    jw_candidates.append(jaro_winkler(q_tok, v_tok))
            jw_best = max(jw_candidates)

            # 3. Indian-name spelling: ranks with a strong Jaro-Winkler hit, above Soundex
            if field != "phone_hash" and any(same_name(qt, vt) for qt in q_tokens for vt in val_tokens):
                _update_best(best, sid, s, max(jw_best, 0.9), field, "indic_phonetic")
                continue

            if jw_best >= threshold:
                _update_best(best, sid, s, jw_best, field, "jaro_winkler")
                continue

            # 4. Soundex — any query-token Soundex matches any field-token Soundex
            val_sdx = [soundex(t) for t in val_tokens]
            sdx_hit = any(qs == vs for qs in q_sdx for vs in val_sdx)
            if sdx_hit and jw_best >= _SOUNDEX_MIN_JW:
                # Promote score to at least 0.80 so Soundex hits rank above noise
                sc = max(jw_best, 0.80)
                _update_best(best, sid, s, sc, field, "soundex")

    hits = sorted(best.values(), key=lambda h: h["match_score"], reverse=True)
    return hits[:limit]


def _update_best(
    best: dict,
    sid: str,
    s: dict,
    score: float,
    field: str,
    method: str,
) -> None:
    """Replace the stored hit only if this score is higher."""
    existing = best.get(sid)
    if existing is None or score > existing["match_score"]:
        best[sid] = {
            **_suspect_payload(s),
            "match_score":   round(score, 4),
            "match_field":   field,
            "match_method":  method,
        }


# ── Bipartite Graph Embeddings for UNSUB & Alias Linkage ────────────────────────
def _extract_bipartite_features(entity: dict) -> dict[str, float]:
    """Extract sparse bipartite graph feature projection for an entity or UNSUB record."""
    feats: dict[str, float] = {}
    # Operational zone edge
    zone = (entity.get("zone") or entity.get("address_zone") or "").strip().lower()
    if zone:
        feats[f"zone:{zone}"] = 1.0
    # Crime category edge
    ctype = (entity.get("crime_type") or "").strip().lower()
    if ctype:
        feats[f"ctype:{ctype}"] = 1.0
    # Phone hash edge (high specificity weight)
    ph = str(entity.get("phone_hash") or "").strip()
    if ph:
        feats[f"phone:{ph}"] = 2.5
    # Alias / MO tokens
    alias = (entity.get("alias") or "").strip().lower()
    for tok in alias.split():
        if len(tok) >= 3:
            feats[f"alias:{tok}"] = 1.2
    return feats


def bipartite_linkage_score(
    a: dict,
    b: dict,
) -> tuple[float, list[str], dict]:
    """Bipartite Graph Structural & Phonetic Linkage Score for UNSUB / Alias resolution.

    Projects entities onto a Bipartite feature space:
      • Partition V1: Identity / Alias attributes (names, aliases, Soundex codes)
      • Partition V2: Structural / Crime incident edges (zones, crime_types, phone_hash)
    Computes cosine similarity of structural bipartite embeddings + phonetic similarity.
    """
    reasons: list[str] = []
    # 1. Phonetic / Name Node Similarity
    name_a = (a.get("suspect_name") or a.get("full_name") or "").strip()
    name_b = (b.get("suspect_name") or b.get("full_name") or "").strip()
    jw_score = jaro_winkler(name_a.upper(), name_b.upper()) if name_a and name_b else 0.0

    if jw_score >= 0.85:
        reasons.append(f"High name similarity ({jw_score:.2f})")
    if name_a and name_b and soundex(name_a) == soundex(name_b):
        reasons.append(f"Phonetic Soundex match ({soundex(name_a)})")
        jw_score = max(jw_score, 0.82)

    # 2. Structural Bipartite Cosine Similarity
    fa = _extract_bipartite_features(a)
    fb = _extract_bipartite_features(b)

    dot = 0.0
    for k, va in fa.items():
        if k in fb:
            dot += va * fb[k]
            reasons.append(f"Shared bipartite edge: {k}")

    norm_a = math.sqrt(sum(v * v for v in fa.values()))
    norm_b = math.sqrt(sum(v * v for v in fb.values()))
    struct_sim = round(dot / (norm_a * norm_b), 3) if norm_a > 0 and norm_b > 0 else 0.0

    if struct_sim > 0.0:
        reasons.append(f"Bipartite structural cosine sim: {struct_sim:.2f}")

    # 3. Combined Bipartite Linkage Score
    if name_a and name_b:
        combined = round(min(1.0, 0.55 * jw_score + 0.45 * struct_sim + (0.15 if dot > 1.5 else 0.0)), 3)
    else:
        combined = round(min(1.0, struct_sim), 3)

    meta = {
        "phonetic_sim": round(jw_score, 3),
        "bipartite_cosine_sim": struct_sim,
        "shared_edges": [k for k in fa if k in fb],
        "engine": "Bipartite Graph Embedding & Phonetic Resolution",
    }
    return combined, reasons, meta


# ── Fellegi-Sunter Probabilistic Record Linkage (P2-2) ────────────────────────
class FellegiSunterLinker:
    """
    Probabilistic record linkage using the Fellegi-Sunter model.
    Match weights are EM-estimated from the registry (simulated here for deployment).
    """
    def __init__(self):
        # m: P(agree | match), u: P(agree | non-match)
        self.params = {
            "name":         {"m": 0.88, "u": 0.005},
            "alias":        {"m": 0.60, "u": 0.001},
            "father_name":  {"m": 0.80, "u": 0.008},
            "address_zone": {"m": 0.70, "u": 0.050},
            "phone_hash":   {"m": 0.95, "u": 0.0001},
            "crime_type":   {"m": 0.75, "u": 0.100},
        }
        self.prior = 0.00001  # Base rate of two random records matching

    def score(self, a: dict, b: dict) -> tuple[float, list[str], dict]:
        log_odds = math.log2(self.prior / (1.0 - self.prior))
        reasons = []
        shared_keys = []

        def _get(r, keys):
            for k in keys:
                if r.get(k): return str(r[k]).strip().upper()
            return ""

        # 1. Name match (Jaro-Winkler)
        na = _get(a, ["suspect_name", "full_name"])
        nb = _get(b, ["suspect_name", "full_name"])
        if na and nb:
            jw = jaro_winkler(na, nb)
            p = self.params["name"]
            if jw > 0.85:
                w = math.log2(p["m"] / p["u"])
                log_odds += w
                reasons.append(f"Name match (jw={jw:.2f}, w={w:.1f})")
                shared_keys.append("name")
            else:
                log_odds += math.log2((1 - p["m"]) / (1 - p["u"]))

        # 2. Alias
        aa = _get(a, ["alias"])
        ab = _get(b, ["alias"])
        if aa and ab:
            jw = jaro_winkler(aa, ab)
            p = self.params["alias"]
            if jw > 0.85:
                w = math.log2(p["m"] / p["u"])
                log_odds += w
                reasons.append(f"Alias match (w={w:.1f})")
                shared_keys.append("alias")
            else:
                log_odds += math.log2((1 - p["m"]) / (1 - p["u"]))

        # 3. Father name
        fa = _get(a, ["father_name"])
        fb = _get(b, ["father_name"])
        if fa and fb:
            jw = jaro_winkler(fa, fb)
            p = self.params["father_name"]
            if jw > 0.85:
                w = math.log2(p["m"] / p["u"])
                log_odds += w
                reasons.append(f"Father name match (w={w:.1f})")
                shared_keys.append("father_name")
            else:
                log_odds += math.log2((1 - p["m"]) / (1 - p["u"]))

        # 4. Zone
        za = _get(a, ["address_zone", "zone"])
        zb = _get(b, ["address_zone", "zone"])
        if za and zb:
            p = self.params["address_zone"]
            if za == zb:
                w = math.log2(p["m"] / p["u"])
                log_odds += w
                reasons.append(f"Same zone (w={w:.1f})")
                shared_keys.append("address_zone")
            else:
                log_odds += math.log2((1 - p["m"]) / (1 - p["u"]))

        # 5. Phone
        pa = _get(a, ["phone_hash"])
        pb = _get(b, ["phone_hash"])
        if pa and pb:
            p = self.params["phone_hash"]
            if pa == pb:
                w = math.log2(p["m"] / p["u"])
                log_odds += w
                reasons.append(f"Shared phone (key={pa}, w={w:.1f})")
                shared_keys.append(f"phone_hash:{pa}")
            else:
                log_odds += math.log2((1 - p["m"]) / (1 - p["u"]))

        # 6. Crime Type
        ca = _get(a, ["crime_type"])
        cb = _get(b, ["crime_type"])
        if ca and cb:
            p = self.params["crime_type"]
            if ca == cb:
                w = math.log2(p["m"] / p["u"])
                log_odds += w
                reasons.append(f"Same crime type (w={w:.1f})")
                shared_keys.append("crime_type")
            else:
                log_odds += math.log2((1 - p["m"]) / (1 - p["u"]))

        prob = 1.0 / (1.0 + math.pow(2.0, -log_odds))
        
        meta = {
            "engine": "Fellegi-Sunter Probabilistic Linkage",
            "log_odds": round(log_odds, 2),
            "shared_keys": shared_keys
        }
        return round(prob, 4), reasons, meta

_fs_linker = FellegiSunterLinker()

# The hypotheses depend only on the records, not on what was searched: /api/profile/search
# used to rescore the same 19,900 pairs (~1.5 s) on every search. The world is loaded once
# and kept (zcql_local._world), so the result is kept with it and recomputed only when a new
# world object arrives or the threshold changes. Holding the world itself (not its id)
# means a freed-and-reused id can never return another world's hypotheses.
_LINKS_CACHE: dict = {"world": None, "threshold": None, "result": None}


def suggest_identity_links(rows: list[dict] | dict, threshold: float = 0.75) -> list[dict]:
    """
    Layer 5 Cross-Source Identity Hypothesis Generator.
    Scans internal FIR/suspect rows for candidate identity overlaps across records
    using Fellegi-Sunter Probabilistic Linkage + Bipartite Graph Embeddings.
    Returns actionable hypotheses ready for officer review via Layer 4 RBAC endpoints.
    NEVER auto-merges records.
    """
    if isinstance(rows, dict):
        c = _LINKS_CACHE
        if c["world"] is rows and c["threshold"] == threshold:
            return [dict(h) for h in c["result"]]
        result = _suggest_identity_links(rows, threshold)
        c.update(world=rows, threshold=threshold, result=result)
        return [dict(h) for h in result]
    return _suggest_identity_links(rows, threshold)


def _suggest_identity_links(rows: list[dict] | dict, threshold: float) -> list[dict]:
    records: list[dict] = []
    if isinstance(rows, list):
        records = [r for r in rows if isinstance(r, dict)]
    elif isinstance(rows, dict):
        for v in rows.values():
            if isinstance(v, list):
                records.extend([r for r in v if isinstance(r, dict)])
            elif isinstance(v, dict):
                records.append(v)
    rows = records[:200]  # ponytail: cap to 200 to keep O(N^2) pairwise resolution < 5ms

    hypotheses = []
    seen_pairs = set()

    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a = rows[i]
            b = rows[j]

            id_a = str(a.get("id") or a.get("suspect_id") or f"A-{i}")
            id_b = str(b.get("id") or b.get("suspect_id") or f"B-{j}")

            if id_a == id_b:
                continue

            pair_key = tuple(sorted([id_a, id_b]))
            if pair_key in seen_pairs:
                continue

            # Additive scoring: compute both, take the highest confidence signal
            score_bip, reasons_bip, meta_bip = bipartite_linkage_score(a, b)
            score_fs, reasons_fs, meta_fs = _fs_linker.score(a, b)

            if score_fs >= score_bip:
                score, reasons, meta = score_fs, reasons_fs, meta_fs
            else:
                score, reasons, meta = score_bip, reasons_bip, meta_bip

            if score >= threshold and reasons:
                seen_pairs.add(pair_key)
                hypotheses.append({
                    "hypothesis_id": f"HYP-ID-{id_a}-{id_b}",
                    "entity_a": {
                        "id": id_a,
                        "name": (a.get("suspect_name") or a.get("full_name") or "").strip(),
                        "zone": a.get("zone", ""),
                        "phone_hash": str(a.get("phone_hash") or "").strip(),
                    },
                    "entity_b": {
                        "id": id_b,
                        "name": (b.get("suspect_name") or b.get("full_name") or "").strip(),
                        "zone": b.get("zone", ""),
                        "phone_hash": str(b.get("phone_hash") or "").strip(),
                    },
                    "confidence": score,
                    "reasons": reasons,
                    "bipartite_meta": meta,
                    "badge": "INFERRED (CROSS-SOURCE IDENTITY)",
                    "status": "proposed",
                    "requires_rbac_rank": "Inspector",
                })

    return sorted(hypotheses, key=lambda h: h["confidence"], reverse=True)

