"""
Antar — Audit log (M10 / F7) — Persistent SQLite + Catalyst Sync Hybrid.
A row is written for EVERY /api call by the audit middleware in main.py.
Integrates cryptographic hash chaining to prevent administrative tampering.

Chain integrity across restarts
-------------------------------
The hash covers a payload dict. Until this was fixed, each write path built its own
payload shape while `load_from_db` reconstructed a DIFFERENT shape from fixed columns,
so the dict that got re-hashed on verification was never the dict that was hashed on
write. `verify_chain()` returned True in-process and False after any restart — for
EVERY event type, not just one:

  record()                 hashed {ts,officer,role,method,path,status,type}
                           reload added session_id/user_text/answer as None
  record_ai_reasoning()    hashed {...,session_id,user_text,answer,agents_used,...}
                           reload added role/method/path/status as None
  record_hypothesis_event() hashed {...,hypothesis_id,reason,...}
                           reload returned user_text/answer instead

Two changes stop this recurring:

  1. `payload_json` — the exact bytes that were hashed are stored alongside the digest,
     so verification rehydrates the original dict instead of guessing at it. New event
     fields can never silently fall outside the hash again.
  2. `prev_hash` — each row now carries the link it was chained from, so a row is
     independently verifiable and a break can be located rather than just detected.

Rows written before this change cannot be made to verify (the hashed bytes were never
recorded). They load with `chain_verifiable: False`, are reported separately by
`verify_chain_report()`, and the chain re-bases on them rather than reporting a
false tamper alert. `verify_chain()` means "no VERIFIABLE entry failed" — read the
report, not the bool, when the legacy count is non-zero.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from app.core.audit import hash_event

_log: list[dict] = []
_MAX = 2000
_MAX_TRACE_STEPS = 500
_last_hash: str = "0" * 64
_GENESIS = "0" * 64

# Bookkeeping attached to an entry that is NOT part of the hashed payload. Anything
# added here must be excluded from _payload_of, or it changes the digest.
_META_KEYS = ("hash", "prev_hash", "chain_verifiable")

from app.core.db_path import DB_PATH


def _payload_of(entry: dict) -> dict:
    """The dict that was (or would have been) hashed — chain bookkeeping stripped."""
    return {k: v for k, v in entry.items() if k not in _META_KEYS}


def _append(payload: dict) -> dict:
    """Hash `payload` onto the chain and append it in memory.

    The single place a chain link is formed. Every write path goes through here so the
    hashed shape and the persisted shape cannot drift apart again.
    """
    global _last_hash
    prev = _last_hash
    digest = hash_event(prev, payload)
    _last_hash = digest
    entry = {**payload, "prev_hash": prev, "hash": digest, "chain_verifiable": True}
    _log.append(entry)
    if len(_log) > _MAX:
        del _log[: len(_log) - _MAX]
    return entry

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            officer TEXT,
            role TEXT,
            method TEXT,
            path TEXT,
            status INTEGER,
            type TEXT NOT NULL,
            session_id TEXT,
            user_text TEXT,
            answer TEXT,
            agents_used TEXT,
            citations TEXT,
            hash TEXT NOT NULL
        );
        """)
        
        # Phase 5: Observability Upgrade
        try:
            conn.execute("ALTER TABLE audit_log ADD COLUMN reasoning_id TEXT;")
        except sqlite3.OperationalError:
            pass # Column already exists

        # Chain integrity (see module docstring). payload_json holds the EXACT dict that
        # was hashed; prev_hash holds the link it chained from. Both are nullable so rows
        # written before this change still load — they just cannot be verified.
        for _col in ("payload_json TEXT", "prev_hash TEXT"):
            try:
                conn.execute(f"ALTER TABLE audit_log ADD COLUMN {_col};")
            except sqlite3.OperationalError:
                pass  # Column already exists

        conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_reasoning_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reasoning_id TEXT NOT NULL UNIQUE,
            trace_json TEXT NOT NULL,
            ts TEXT NOT NULL
        );
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing audit DB: {e}")

def load_from_db():
    global _log, _last_hash
    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM audit_log ORDER BY log_id ASC").fetchall()
        conn.close()
        
        _log.clear()
        for r in rows:
            cols = r.keys()
            raw = r["payload_json"] if "payload_json" in cols else None
            payload = None
            if raw:
                try:
                    payload = json.loads(raw)
                except (TypeError, ValueError):
                    payload = None

            if payload is not None:
                # Post-fix row: the exact hashed dict round-trips, so it verifies.
                entry = {
                    **payload,
                    "prev_hash": r["prev_hash"] if "prev_hash" in cols else None,
                    "hash": r["hash"],
                    "chain_verifiable": True,
                }
            else:
                # Legacy row: reconstruct what we can for display. The bytes that were
                # hashed were never stored, so this can never be verified — say so
                # rather than letting it read as a tamper alert.
                entry = {
                    "ts": r["ts"], "officer": r["officer"], "role": r["role"],
                    "method": r["method"], "path": r["path"], "status": r["status"],
                    "type": r["type"], "session_id": r["session_id"],
                    "user_text": r["user_text"], "answer": r["answer"],
                    "hash": r["hash"], "prev_hash": None, "chain_verifiable": False,
                }
                if r["agents_used"]:
                    entry["agents_used"] = json.loads(r["agents_used"])
                if r["citations"]:
                    entry["citations"] = json.loads(r["citations"])
                if "reasoning_id" in cols and r["reasoning_id"]:
                    entry["reasoning_id"] = r["reasoning_id"]

            _log.append(entry)
            _last_hash = r["hash"]

        if len(_log) > _MAX:
            del _log[: len(_log) - _MAX]
    except Exception as e:
        print(f"Error loading audit log from DB: {e}")

# Load existing audit chain on startup
load_from_db()

def _sync_to_catalyst_placeholder(payload: dict) -> None:
    # ponytail: placeholder for syncing to Zoho Catalyst Stratus / NoSQL Datastore
    # If the network or Catalyst SDK is available, this would push.
    import structlog
    structlog.get_logger().info("catalyst_sync_placeholder", record_hash=payload["hash"], synced=True)

def record(officer: str, role: str, method: str, path: str, status: int) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "officer": officer, "role": role, "method": method, "path": path, "status": status,
        "type": "HTTP"
    }
    entry = _append(payload)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO audit_log (ts, officer, role, method, path, status, type, hash,
                                   payload_json, prev_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (payload["ts"], officer, role, method, path, status, "HTTP", entry["hash"],
              json.dumps(payload, sort_keys=True), entry["prev_hash"]))
        conn.commit()
        conn.close()
        _sync_to_catalyst_placeholder(entry)
    except Exception as e:
        print(f"Audit SQLite write error: {e}")


def record_ai_reasoning(
    officer: str, session_id: str, user_text: str, answer: str, 
    agents_used: list, citations: list,
    reasoning_id: str | None = None,
    reasoning_trace: list[dict] | None = None
) -> str:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "officer": officer,
        "session_id": session_id,
        "user_text": user_text,
        "answer": answer,
        "agents_used": agents_used,
        "citations": citations,
        "type": "AI_REASONING",
        "reasoning_id": reasoning_id
    }
    entry = _append(payload)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO audit_log (ts, officer, session_id, user_text, answer, agents_used,
                                   citations, type, hash, reasoning_id, payload_json, prev_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (payload["ts"], officer, session_id, user_text, answer, json.dumps(agents_used),
              json.dumps(citations), "AI_REASONING", entry["hash"], reasoning_id,
              json.dumps(payload, sort_keys=True), entry["prev_hash"]))

        if reasoning_id and reasoning_trace:
            # A turn's trail is a few dozen steps. Anything past the cap is a runaway, and
            # on Catalyst this table lives in /tmp beside the database.
            if len(reasoning_trace) > _MAX_TRACE_STEPS:
                dropped = len(reasoning_trace) - _MAX_TRACE_STEPS
                reasoning_trace = reasoning_trace[:_MAX_TRACE_STEPS] + [
                    {"step": "truncated", "detail": f"{dropped} further step(s) not stored."}]
            conn.execute("""
                INSERT INTO agent_reasoning_logs (reasoning_id, trace_json, ts)
                VALUES (?, ?, ?)
            """, (reasoning_id, json.dumps(reasoning_trace), payload["ts"]))

        conn.commit()
        conn.close()
        _sync_to_catalyst_placeholder(entry)
    except Exception as e:
        print(f"Audit SQLite write error: {e}")

    return entry["hash"]


def get_reasoning_trace(reasoning_id: str) -> list[dict] | None:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT trace_json FROM agent_reasoning_logs WHERE reasoning_id = ?", (reasoning_id,)).fetchone()
        conn.close()
        if row:
            return json.loads(row["trace_json"])
    except Exception as e:
        print(f"Audit SQLite read error: {e}")
    return None


def record_hypothesis_event(
    event_type: str,
    hypothesis_id: str,
    officer: str,
    role: str,
    reason: str = "",
) -> dict:
    """Record a hypothesis lifecycle event (proposed, shown, confirmed, rejected).
    Provides chargesheet-grade immutable audit tracking of human-in-the-loop decisions.
    """
    valid_events = {
        "hypothesis_proposed",
        "hypothesis_shown",
        "hypothesis_confirmed",
        "hypothesis_rejected",
    }
    if event_type not in valid_events:
        raise ValueError(f"Invalid hypothesis event type: {event_type}")

    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "officer": officer,
        "role": role,
        "hypothesis_id": hypothesis_id,
        "reason": reason,
        "type": event_type,
        "method": "HYPOTHESIS_LIFECYCLE",
        "path": f"/hypothesis/{hypothesis_id}/{event_type.replace('hypothesis_', '')}",
        "status": 200,
    }
    entry = _append(payload)

    try:
        conn = sqlite3.connect(DB_PATH)
        # hypothesis_id and reason are ALSO mirrored into user_text/answer so the existing
        # audit views keep rendering; payload_json is what verification actually reads.
        conn.execute("""
            INSERT INTO audit_log (ts, officer, role, method, path, status, type, user_text,
                                   answer, hash, payload_json, prev_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload["ts"], officer, role, payload["method"], payload["path"],
            200, event_type, hypothesis_id, reason, entry["hash"],
            json.dumps(payload, sort_keys=True), entry["prev_hash"]
        ))
        conn.commit()
        conn.close()
        _sync_to_catalyst_placeholder(entry)
    except Exception as e:
        print(f"Audit SQLite write error: {e}")

    return entry


HITL_EVENTS = {
    "hitl_proposed", "hitl_approved", "hitl_rejected", "hitl_withdrawn",
    "hitl_expired", "hitl_executed", "hitl_failed", "hitl_integrity_failure",
}


def record_hitl_event(event_type: str, *, action_id: str, action_type: str, payload_hash: str,
                      officer: str, role: str, reason: str = "") -> dict:
    """Record one step of a human-in-the-loop approval on the hash chain.

    `payload_hash` binds the event to the exact action content that was proposed, so the
    chain proves not just THAT an officer approved something but WHAT they approved.
    """
    if event_type not in HITL_EVENTS:
        raise ValueError(f"Invalid HITL event type: {event_type}")
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "officer": officer,
        "role": role,
        "type": event_type,
        "method": "HITL",
        "path": f"/hitl/{action_id}/{event_type.replace('hitl_', '')}",
        "status": 200,
        "action_id": action_id,
        "action_type": action_type,
        "payload_hash": payload_hash,
        "reason": reason,
    }
    entry = _append(payload)
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO audit_log (ts, officer, role, method, path, status, type, user_text,
                                   answer, hash, payload_json, prev_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (payload["ts"], officer, role, "HITL", payload["path"], 200, event_type, action_id,
              reason, entry["hash"], json.dumps(payload, sort_keys=True), entry["prev_hash"]))
        conn.commit()
        conn.close()
        _sync_to_catalyst_placeholder(entry)
    except Exception as e:
        print(f"Audit SQLite write error: {e}")
    return entry


def verify_chain_report() -> dict:
    """Verify the ledger and say exactly what was checked.

    Two independent checks per entry:
      • digest  — hash_event(prev_hash, payload) still equals the stored hash
                  (catches an edited field)
      • linkage — prev_hash equals the previous entry's hash
                  (catches a deleted or reordered entry)

    Legacy entries (written before payload_json existed) cannot be verified: the bytes
    that were hashed were never recorded. They are counted, not failed, and the chain
    re-bases on their stored hash — otherwise every restart would raise a false tamper
    alarm for the entire history.
    """
    total = len(_log)
    verified = legacy = 0
    broken_at: int | None = None
    broken_reason: str | None = None
    prev: str | None = None

    for i, entry in enumerate(_log):
        if not entry.get("chain_verifiable"):
            legacy += 1
            prev = entry.get("hash")          # re-base; cannot check across this gap
            continue

        stored_prev = entry.get("prev_hash")
        if prev is not None and stored_prev != prev:
            broken_at, broken_reason = i, "linkage: prev_hash does not match the previous entry"
            break
        if hash_event(stored_prev if stored_prev is not None else _GENESIS,
                      _payload_of(entry)) != entry.get("hash"):
            broken_at, broken_reason = i, "digest: entry content does not match its recorded hash"
            break

        verified += 1
        prev = entry["hash"]

    return {
        "ok": broken_at is None,
        "total_entries": total,
        "verified": verified,
        "legacy_unverifiable": legacy,
        "broken_at_index": broken_at,
        "broken_reason": broken_reason,
        "note": (
            f"{legacy} entr{'y predates' if legacy == 1 else 'ies predate'} the verifiable "
            "format and cannot be checked; 'ok' covers the verifiable entries only."
            if legacy else "every entry in the ledger was verified."
        ),
    }


def verify_chain() -> bool:
    """True when no VERIFIABLE entry failed its digest or linkage check.

    When `legacy_unverifiable` is non-zero this bool does not mean the whole history is
    proven — call verify_chain_report() and show the counts.
    """
    return verify_chain_report()["ok"]


def query(officer: str | None = None, limit: int = 100) -> list[dict]:
    rows = _log if not officer else [r for r in _log if r["officer"] == officer]
    return list(reversed(rows))[:limit]      # most recent first


def count() -> int:
    return len(_log)


def clear() -> None:
    global _last_hash
    _log.clear()
    _last_hash = "0" * 64
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM audit_log")
        conn.commit()
        conn.close()
    except Exception:
        pass
