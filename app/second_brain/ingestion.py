"""
Antar — Second Brain ingestion / demo seeding
==================================================
`seed_demo_brain()` embeds the load-bearing planted summaries
(`planted_patterns.BRAIN_SEED`) into the in-memory cosine index, so cross-case
enrichment (WOW2), the Forecast resolved-pattern match (WOW3) and Profile
similar-cases all work locally. Idempotent (deterministic row_ids).

`embed_fn` is injectable so unit tests don't have to load MiniLM. Durable Data Store
insert is the Catalyst path (store.insert_embedding) — index-only when offline.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import numpy as np

from app.seeds.planted_patterns import BRAIN_SEED
from app.second_brain.index import brain_index


def _embed_one(embed_fn, text: str, terms: list[str] | None = None) -> np.ndarray:
    """Embed one text, optionally with entity terms."""
    if terms:
        prefix = " | ".join(t for t in terms if t)
        text = f"{prefix} — {text}" if prefix else text
    try:
        arr = np.asarray(embed_fn(text), dtype=np.float32)
        return arr[0] if arr.ndim == 2 else arr
    except RuntimeError:
        try:
            from app.second_brain.embedder import load_embedder
            load_embedder()
            arr = np.asarray(embed_fn(text), dtype=np.float32)
            return arr[0] if arr.ndim == 2 else arr
        except Exception:
            return np.zeros(384, dtype=np.float32)


def _admit(text: str, source: str, meta: dict) -> str | None:
    """Poisoning gate in front of the index (OWASP RAG: scan before embedding, hash for
    provenance). Returns the normalised text to embed, or None when the chunk carries
    injection markers — it is then QUARANTINED: logged with its hash, never indexed, so
    it can never be retrieved into another officer's prompt."""
    from app.core.rag_security import screen_for_index
    sc = screen_for_index(text, source=source)
    if sc.quarantined:
        return None
    meta["summary_text"] = sc.text
    meta["sha256"] = sc.sha256
    meta.setdefault("ingested_at", datetime.utcnow().isoformat())
    meta.setdefault("source", source)
    return sc.text


def seed_demo_brain(embed_fn=None) -> int:
    """Embed BRAIN_SEED into the hot index. Idempotent. Returns rows newly added."""
    if embed_fn is None:
        from app.second_brain.embedder import embed as embed_fn   # real BGE (app runtime)
    added = 0
    for i, item in enumerate(BRAIN_SEED):
        row_id = f"SEED-{i:03d}"
        if row_id in brain_index._row_ids:        # already seeded → skip (idempotent)
            continue
        meta = {
            "kind": item["kind"],
            "summary_text": item["summary_text"],
            "suspect_ids_json": json.dumps(item.get("suspect_ids", [])),
            "crime_ids_json": "[]",
            "station_code": item.get("station_code"),
        }
        terms = item.get("terms", [])
        text = _admit(item["summary_text"], "seed", meta)
        if text is None:
            continue
        brain_index.append(_embed_one(embed_fn, text, terms), row_id, meta)
        added += 1
    return added


def index_mo_fields(embed_fn=None, world: dict | None = None, limit: int = 500) -> int:
    """Index MO_Details free-text from crime records into the Second Brain.

    Each crime with a non-trivial MO string becomes a searchable brain entry.
    This lets semantic_recall() surface cases by modus operandi (e.g. 'spike
    strips', 'rear ventilator entry', 'two-rider motorcycle snatch') without
    needing a ZCQL template for every possible MO phrase.

    Idempotent: row_id = 'MO-{crime_id}' — re-running skips already-indexed rows.
    Capped at `limit` rows to bound startup time (full 2800-row CSV ≈ 4s on CPU).

    Returns: count of newly added rows.
    """
    if embed_fn is None:
        from app.second_brain.embedder import embed as embed_fn
    if world is None:
        from app.services.zcql_local import _world
        world = _world() if callable(_world) else _world

    crimes = world.get("crimes", [])
    added = 0

    for crime in crimes:
        if added >= limit:
            break

        mo = str(crime.get("mo_details") or crime.get("MO_Details") or "").strip()
        # Skip trivial / template-only MO strings (< 30 chars or pure boilerplate)
        if len(mo) < 30 or mo.lower().endswith("investigation in progress."):
            continue

        crime_id = crime.get("crime_id", "")
        row_id = f"MO-{crime_id}"
        if row_id in brain_index._row_ids:   # idempotent
            continue

        # Build a rich document: MO text + key metadata so reranker has context
        crime_type = crime.get("crime_type", "")
        zone = crime.get("zone") or crime.get("station_code") or ""
        fir = crime.get("fir_number", crime_id)
        doc = f"{crime_type} | {zone} | FIR {fir}: {mo}"

        terms = [t for t in [crime_type, zone, fir] if t]
        meta = {
            "kind": "fir_mo",
            "summary_text": doc,
            "suspect_ids_json": json.dumps(
                [cs["suspect_id"] for cs in world.get("crime_suspects", [])
                 if cs.get("crime_id") == crime_id][:5]
            ),
            "crime_ids_json": json.dumps([crime_id]),
            "station_code": zone or None,
            "fir_number": fir,
            "crime_type": crime_type,
        }
        text = _admit(doc, "fir_mo", meta)
        if text is None:
            continue
        brain_index.append(_embed_one(embed_fn, text, terms), row_id, meta)
        added += 1

    return added


def _extract_session_terms(turns: list[dict]) -> list[str]:
    """Pull entity-like tokens from session turns for embedding enrichment.

    Cheap heuristic: grab capitalised multi-word tokens and known patterns
    (S-prefixed IDs, zone names) from user questions and assistant findings.
    """
    terms = []
    for t in turns:
        text = t.get("text", "")
        # Suspect IDs like S0001
        import re
        for m in re.findall(r'\bS\d{4}\b', text):
            terms.append(m)
        # Zone-like capitalised words (2+ chars, not common English)
        for word in text.split():
            if len(word) > 3 and word[0].isupper() and word not in ("The", "What", "Where", "When", "How", "Who", "Show", "Find", "Details"):
                terms.append(word)
    # ponytail: cap at 10 terms, deduplicated, preserving order
    seen = set()
    unique = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)
        if len(unique) >= 10:
            break
    return unique


async def session_end_ingest(session_id: str, officer_role: str = "Inspector") -> bool:
    """
    Called when a session ends. Extracts the investigative trail, generates an
    intelligence fragment, and embeds it with lineage tracking.
    """
    from app.core.sessions import all_turns
    
    turns = all_turns(session_id)
    if not turns:
        return False
        
    # Naive extraction for fallback/demo mode: combine user intents and assistant summaries
    extracts = []
    for t in turns:
        if t["role"] == "user":
            extracts.append(f"Q: {t['text']}")
        elif t["role"] == "assistant":
            # Extract reasoning steps if any
            steps = [s["detail"] for s in t.get("steps", [])]
            if steps:
                extracts.append("Findings: " + " | ".join(steps))
                
    if not extracts:
        return False
        
    # In a full run, we'd pass this to QuickML for summarization. 
    # For now, deterministic chunking
    summary_text = "\\n".join(extracts)
    if len(summary_text) > 1000:
        summary_text = summary_text[:1000] + "..."
        
    row_id = f"MEM-{uuid.uuid4().hex[:8]}"
    terms = _extract_session_terms(turns)
    
    meta = {
        "kind": "session_trace",
        "summary_text": summary_text,
        "suspect_ids_json": "[]", # Could use heuristics to extract
        "crime_ids_json": "[]",
        "station_code": None,
        "ref_session_id": session_id,
        "verification_status": "unverified",
        "confidence": 0.6,  # Base confidence for unverified session intel
        "officer_role": officer_role,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Officers' own questions land here and are later retrieved into OTHER officers'
    # prompts — the classic stored-injection path. Screen before embedding.
    text = _admit(summary_text, "session_trace", meta)
    if text is None:
        return False
    from app.second_brain.embedder import embed
    brain_index.append(_embed_one(embed, text, terms), row_id, meta)
    
    # TODO: Sync to zcql_local/Catalyst Data Store
    return True


def ingest_confirmed_hypothesis(hypothesis_id: str, summary_text: str, embed_fn=None) -> str:
    """Ingest a human-confirmed hypothesis as a confirmed_link memory."""
    if embed_fn is None:
        from app.second_brain.embedder import embed as embed_fn
    row_id = f"CONF-{hypothesis_id}"
    meta = {
        "kind": "confirmed_link",
        "summary_text": f"CONFIRMED HYPOTHESIS {hypothesis_id}: {summary_text}",
        "suspect_ids_json": "[]",
        "crime_ids_json": "[]",
        "station_code": None,
        "ref_session_id": hypothesis_id,
        "verification_status": "verified",
        "confidence": 1.0,
        "created_at": datetime.utcnow().isoformat(),
    }
    text = _admit(meta["summary_text"], meta["kind"], meta)
    if text is None:
        return ""
    brain_index.append(_embed_one(embed_fn, text, [hypothesis_id]), row_id, meta)
    return row_id


def ingest_disproven_hypothesis(hypothesis_id: str, summary_text: str, reason: str = "", embed_fn=None) -> str:
    """Ingest a human-rejected hypothesis as a disproven_pattern memory so the system stops re-proposing it."""
    if embed_fn is None:
        from app.second_brain.embedder import embed as embed_fn
    row_id = f"DISP-{hypothesis_id}"
    meta = {
        "kind": "disproven_pattern",
        "summary_text": f"DISPROVEN HYPOTHESIS {hypothesis_id} (Reason: {reason}): {summary_text}",
        "suspect_ids_json": "[]",
        "crime_ids_json": "[]",
        "station_code": None,
        "ref_session_id": hypothesis_id,
        "verification_status": "disproven",
        "confidence": 0.0,
        "rejection_reason": reason,
        "created_at": datetime.utcnow().isoformat(),
    }
    text = _admit(meta["summary_text"], meta["kind"], meta)
    if text is None:
        return ""
    brain_index.append(_embed_one(embed_fn, text, [hypothesis_id]), row_id, meta)
    return row_id
