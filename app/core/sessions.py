"""
Antar — Conversation & Reasoning Store (dev: in-memory)
===========================================================
Holds per-session conversation turns (for context-aware follow-ups, M1) and the
per-turn reasoning trail (for the "why?" Explain capability, M9).

Phase 3 status: IN-MEMORY (a dict). This is the dev stand-in for Catalyst NoSQL
collections `chat_sessions` + `agent_reasoning_logs`. The interface below is what
the NoSQL version will implement — swap the body, keep the signatures, and nothing
upstream changes. In-memory means history resets when the server restarts (fine for dev).
"""

from __future__ import annotations

import time

# session_id -> {"turns": [...], "entities": {...}, "topic_thread": {...}}
_SESSIONS: dict[str, dict] = {}
_MAX_TURNS = 50  # cap memory per session


def _session(session_id: str) -> dict:
    s = _SESSIONS.setdefault(session_id, {
        "turns": [],
        "entities": {"suspects": [], "zones": [], "crime_types": []},
        "topic_thread": {"current_topic": "general", "turns_on_topic": 0}
    })
    return s


def get_session_entities(session_id: str) -> dict:
    """Retrieve tracked entities (suspects, zones, crime types) mentioned across recent turns."""
    return _session(session_id).get("entities", {"suspects": [], "zones": [], "crime_types": []})


def update_session_entities(session_id: str, entities: dict) -> None:
    """Merge newly detected entities into session state for cross-turn continuity."""
    s = _session(session_id)
    cur = s.setdefault("entities", {"suspects": [], "zones": [], "crime_types": []})
    for k in ("suspects", "zones", "crime_types"):
        new_items = entities.get(k, [])
        if new_items:
            # deduplicate while preserving order (newest first or appended)
            merged = list(dict.fromkeys(list(new_items) + list(cur.get(k, []))))[:15]
            cur[k] = merged


def append_user_turn(session_id: str, text: str, lang: str) -> None:
    s = _session(session_id)
    s["turns"].append({"role": "user", "text": text, "lang": lang, "ts": time.time()})
    s["turns"] = s["turns"][-_MAX_TURNS:]
    
    # Basic topic detection updating
    low = (text or "").casefold()
    new_topic = "general"
    if any(w in low for w in ("network", "link", "who knows whom", "associate")):
        new_topic = "network"
    elif any(w in low for w in ("profile", "suspect", "mo", "risk score")):
        new_topic = "profile"
    elif any(w in low for w in ("map", "hotspot", "zone", "where")):
        new_topic = "map"
    elif any(w in low for w in ("predict", "forecast", "warning", "mad-z")):
        new_topic = "forecast"
        
    thread = s.setdefault("topic_thread", {"current_topic": "general", "turns_on_topic": 0})
    if thread["current_topic"] == new_topic:
        thread["turns_on_topic"] += 1
    else:
        thread["current_topic"] = new_topic
        thread["turns_on_topic"] = 1


def append_assistant_turn(session_id: str, text: str, lang: str, template_id: str,
                          reasoning_id: str, steps: list[dict], meta: dict | None = None) -> None:
    """`meta` carries what the audit report needs beyond the text: the question, evidence
    (citations, row count, method), confidence, response time, engine and audit hash."""
    s = _session(session_id)
    turn = {
        "role": "assistant", "text": text, "lang": lang,
        "template_id": template_id, "reasoning_id": reasoning_id,
        "steps": steps, "ts": time.time(),
    }
    if meta:
        turn["meta"] = meta
    s["turns"].append(turn)
    s["turns"] = s["turns"][-_MAX_TURNS:]


def all_turns(session_id: str) -> list[dict]:
    """Full turns of a session (for the intelligence report / export)."""
    return list(_session(session_id)["turns"])


def recent_turns(session_id: str, n: int = 6) -> list[dict]:
    """Last n turns as lightweight context for the LLM (role + text only)."""
    return [{"role": t["role"], "text": t["text"]} for t in _session(session_id)["turns"][-n:]]


def last_reasoning(session_id: str) -> list[dict]:
    """Reasoning steps of the most recent assistant turn (for 'why?'). [] if none."""
    for t in reversed(_session(session_id)["turns"]):
        if t["role"] == "assistant":
            return t.get("steps", [])
    return []


def has_assistant_turn(session_id: str) -> bool:
    """True once this session has an answer that an 'explain' could refer back to."""
    return any(t["role"] == "assistant" for t in _session(session_id)["turns"])


def clear(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
    _KUL_SESSIONS.pop(session_id, None)
    try:
        pass
        # NoSQL clear if possible
    except Exception:
        pass


# ── Layer 1 KUL Conversational Intelligence Store ─────────────────────────────
# Keyed session_id -> {frontier_ids[], shown_claim_ids[], shown_claims[], lang, last_anchor}
_KUL_SESSIONS: dict[str, dict] = {}


def get_kul_state(session_id: str) -> dict:
    """Retrieve KUL session state from NoSQL or fallback in-memory dict."""
    try:
        from app.services.product_store import get_product
        cached = get_product(f"session_kul:{session_id}")
        if cached and isinstance(cached, dict):
            _KUL_SESSIONS[session_id] = cached
            return cached
    except Exception:
        pass
    return _KUL_SESSIONS.setdefault(session_id, {
        "frontier_ids": [],
        "shown_claim_ids": [],
        "shown_claims": [],
        "lang": "en",
        "last_anchor": None,
    })


def save_kul_state(session_id: str, frontier_ids: list, shown_claims: list, last_anchor: str, lang: str = "en") -> None:
    """Persist KUL exploration state for multi-turn reference resolution."""
    state = {
        "frontier_ids": list(dict.fromkeys(frontier_ids or [])),
        "shown_claim_ids": [c.get("id", str(i)) for i, c in enumerate(shown_claims or [])],
        "shown_claims": shown_claims or [],
        "lang": lang,
        "last_anchor": last_anchor,
        "updated_at": time.time(),
    }
    _KUL_SESSIONS[session_id] = state
    try:
        from app.services.product_store import put_product
        put_product(f"session_kul:{session_id}", state, ttl=86400)
    except Exception:
        pass


def resolve_reference(user_text: str, session_id: str) -> str | None:
    """Resolve ordinal or contextual follow-up references ('the first one', 'go deeper on the second') against KUL state."""
    if not session_id:
        return None
    state = get_kul_state(session_id)
    shown = state.get("shown_claims") or []
    if not shown:
        return None

    low = (user_text or "").casefold()
    last_anchor = (state.get("last_anchor") or "").casefold()

    # 1. Check ordinal references
    idx = None
    if any(w in low for w in ("first", "1st", "number 1", "number one", "the 1 ")):
        idx = 0
    elif any(w in low for w in ("second", "2nd", "number 2", "number two", "the 2 ", "latter", "other one", "next one")):
        idx = 1
    elif any(w in low for w in ("third", "3rd", "number 3", "number three", "the 3 ")):
        idx = 2
    elif any(w in low for w in ("fourth", "4th", "number 4", "number four", "the 4 ")):
        idx = 3
    elif "last one" in low or "the last" in low:
        idx = len(shown) - 1

    if idx is not None and 0 <= idx < len(shown):
        target = shown[idx]
        sub_ids = target.get("subject_ids") or target.get("anchor_ids") or target.get("evidence_rows") or []
        for sid in sub_ids:
            if sid and str(sid).casefold() != last_anchor and not str(sid).startswith("SUS-"):
                return str(sid)
            elif sid and str(sid).startswith("SUS-"):
                clean_sid = str(sid)[4:]
                if clean_sid.casefold() != last_anchor:
                    return clean_sid
        if sub_ids:
            clean = str(sub_ids[0])
            return clean[4:] if clean.startswith("SUS-") else clean

    # 2. Check keyword/contextual references (e.g. 'vehicle', 'phone', 'upi', 'associate', or ID)
    for claim_obj in shown:
        claim_text = str(claim_obj.get("claim") or claim_obj.get("what_is_missing") or "").casefold()
        sub_ids = claim_obj.get("subject_ids") or claim_obj.get("anchor_ids") or []
        for sid in sub_ids:
            clean_sid = str(sid)[4:] if str(sid).startswith("SUS-") else str(sid)
            if clean_sid.casefold() in low:
                return clean_sid
        if "vehicle" in low and "vehicle" in claim_text:
            if sub_ids: return str(sub_ids[0])[4:] if str(sub_ids[0]).startswith("SUS-") else str(sub_ids[0])
        if "phone" in low and ("phone" in claim_text or "cdr" in claim_text):
            if sub_ids: return str(sub_ids[0])[4:] if str(sub_ids[0]).startswith("SUS-") else str(sub_ids[0])
        if "upi" in low and ("upi" in claim_text or "bank" in claim_text or "kyc" in claim_text):
            if sub_ids: return str(sub_ids[0])[4:] if str(sub_ids[0]).startswith("SUS-") else str(sub_ids[0])

    return None
