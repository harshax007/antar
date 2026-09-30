"""
Antar — Dwani Agent (A6: Kannada Voice & Language · honest)
================================================================
Bilingual by construction: translate the Kannada query (via the Bhashini dictionary),
then answer from REAL data — top repeat offenders, real crime counts (optionally by
place), or an entity resolved through the unified bridge. Every number is counted from
the evidence ledger; the language layer never invents facts. Facts real, wording bilingual.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services import bhashini, entity_bridge, evidence_ledger

# normalized-English crime phrase → ledger crime-text substring
_CRIME_KW = {
    "chain snatching": "snatch", "snatching": "snatch", "snatch": "snatch",
    "house breaking": "break", "burglary": "burglary", "theft": "theft",
    "robbery": "robbery", "dacoity": "dacoit", "murder": "murder",
    "vehicle theft": "vehicle", "cheating": "cheat", "fraud": "fraud", "cyber": "cyber",
}
_KNOWN_PLACES = [
    "Rajajinagar", "Koramangala", "Indiranagar", "Malleswaram",
    "Bengaluru North", "Bengaluru South", "Bengaluru City",
    "Belagavi", "Hubballi", "Dharwad", "Mysuru City", "Mysuru", "Mandya", "Tumakuru", "Hassan",
]


def _detect_place(text: str) -> str | None:
    tl = text.lower()
    for p in _KNOWN_PLACES:
        if p.lower() in tl:
            return p
    return None


def _detect_crime(text: str) -> tuple[str | None, str | None]:
    tl = text.lower()
    for label, kw in _CRIME_KW.items():
        if label in tl:
            return label, kw
    return None, None


async def process_kannada_query(query_kn: str) -> dict[str, Any]:
    """Translate → answer from real data → render EN/KN. No fabricated numbers."""
    norm_en = await bhashini.translate_text(query_kn, source_lang="kn", target_lang="en")
    lower = norm_en.lower()
    citations: list[dict] = []
    suspect: dict | None = None
    ans_en = ""
    ans_kn = ""

    # A) repeat / habitual offenders → real top offenders from the ledger
    if "repeat offender" in lower or "habitual" in lower:
        top = evidence_ledger.top_offenders(3)
        if top:
            suspect = evidence_ledger.entity(top[0]["accused_id"])
            lines = [f"{i + 1}. {o['alias']} [{o['accused_id']}] — {o['fir_count']} linked FIRs across "
                     f"{len(o['districts'])} district(s)" for i, o in enumerate(top)]
            ans_en = "Top repeat offenders on record:\n• " + "\n• ".join(lines)
            klines = [f"{i + 1}. {o['alias']} [{o['accused_id']}] — {o['fir_count']} FIR, "
                      f"{len(o['districts'])} ಜಿಲ್ಲೆ" for i, o in enumerate(top)]
            ans_kn = "ದಾಖಲೆಯಲ್ಲಿನ ಪ್ರಮುಖ ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು:\n• " + "\n• ".join(klines)
            citations = [{"entity": o["accused_id"], "fir_count": o["fir_count"], "source": "evidence ledger"}
                         for o in top]

    # B) crime type (+ optional place) → real count
    if not ans_en:
        label, kw = _detect_crime(norm_en)
        if kw:
            place = _detect_place(norm_en)
            n, refs = evidence_ledger.crime_count(kw, place)
            where = place or "all districts"
            ans_en = f"{n} {label} case(s) on record in {where} (evidence ledger)."
            ans_kn = f"{where} — {n} ಪ್ರಕರಣ(ಗಳು) ದಾಖಲೆಯಲ್ಲಿವೆ."
            citations = [{"ref": r, "source": "evidence ledger"} for r in refs]

    # C) name / entity lookup → unified bridge
    if not ans_en and any(w in lower for w in ("find", "suspect", "who is", "network")):
        name = norm_en
        for w in ("find", "suspect", "network", "who is", "the"):
            name = name.replace(w, "").replace(w.title(), "")
        hits = entity_bridge.search_all(name.strip(), limit=1)
        if hits:
            h = hits[0]
            suspect = h
            disp = h.get("full_name") or h.get("alias")
            ans_en = (f"{disp} — {h.get('prior_count', 0)} record(s), area {h.get('address_zone') or '—'}. "
                      f"Source: {h.get('source')} record.")
            ans_kn = f"{disp} — {h.get('prior_count', 0)} ದಾಖಲೆ, ಪ್ರದೇಶ {h.get('address_zone') or '—'}."
            citations = [{"entity": h.get("suspect_id"), "source": h.get("source")}]
        else:
            ans_en = f"No record matches '{name.strip()}'."
            ans_kn = f"'{name.strip()}' ಗೆ ಹೊಂದಾಣಿಕೆಯ ದಾಖಲೆ ಇಲ್ಲ."

    # D) honest fallback — no fabricated stats
    if not ans_en:
        ans_en = f"Understood as: '{norm_en}'. No specific records matched — use Chat for a detailed query."
        ans_kn = f"'{query_kn}' — ನಿರ್ದಿಷ್ಟ ದಾಖಲೆ ಸಿಗಲಿಲ್ಲ. ವಿವರಗಳಿಗೆ ಚಾಟ್ ಬಳಸಿ."

    return {
        "query_kn": query_kn,
        "normalized_en": norm_en,
        "answer_en": ans_en,
        "answer_kn": ans_kn,
        "suspect_resolved": suspect,
        "citations": citations,
        "provenance": {
            "agent": "A6: Dwani Kannada",
            "method": "deterministic answer over evidence ledger + entity bridge (facts real; language via Bhashini dictionary)",
            "compiled_at": datetime.now(timezone.utc).isoformat(),
        },
    }
