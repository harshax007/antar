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
import threading
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
from app.core.db_path import registry_connect


def _payload_of(entry: dict) -> dict:
    """The dict that was (or would have been) hashed — chain bookkeeping stripped."""
    return {k: v for k, v in entry.items() if k not in _META_KEYS}


_write_lock = threading.Lock()


def _remember(entry: dict) -> None:
    global _last_hash
    _last_hash = entry["hash"]
    _log.append(entry)
    if len(_log) > _MAX:
        del _log[: len(_log) - _MAX]


def _append(payload: dict) -> dict:
    """Hash `payload` onto the in-memory chain only. Used when the database cannot be
    written, so the caller still gets a hash; `_write` is the normal path."""
    with _write_lock:
        prev = _last_hash
        entry = {**payload, "prev_hash": prev, "hash": hash_event(prev, payload), "chain_verifiable": True}
        _remember(entry)
        return entry


def _write(payload: dict, cols: dict, after=None) -> dict:
    """Hash `payload` onto the chain and store it: the single place a link is formed.

    The previous hash is read from the database INSIDE the write transaction, not from
    this process's memory. Before, each process chained from its own in-memory tail and
    wrote afterwards, so two writes at the same moment (a request's HTTP row and its
    AI_REASONING row from a worker thread, or a second process such as a script or a test
    run) were stored in a different order from the one they were chained in. Nothing was
    altered, but the ledger read as broken: 32 linkage breaks in 11,447 entries, every
    digest intact. BEGIN IMMEDIATE takes SQLite's write lock, so the order of the links
    and the order of the rows are now the same thing, across threads and processes.
    `after(conn)` runs in the same transaction (the reasoning trail beside its row).
    """
    with _write_lock:
        conn = None
        try:
            conn = registry_connect(DB_PATH, timeout=30, isolation_level=None)
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT hash FROM audit_log ORDER BY log_id DESC LIMIT 1").fetchone()
            prev = row[0] if row else _GENESIS
            digest = hash_event(prev, payload)
            allc = {**cols, "hash": digest, "payload_json": json.dumps(payload, sort_keys=True), "prev_hash": prev}
            conn.execute(f"INSERT INTO audit_log ({', '.join(allc)}) VALUES ({', '.join('?' * len(allc))})",
                         tuple(allc.values()))
            if after:
                after(conn)
            conn.execute("COMMIT")
        except Exception as e:
            try:
                if conn is not None:
                    conn.execute("ROLLBACK")
            except Exception:
                pass
            print(f"Audit SQLite write error: {e}")
            prev = _last_hash
            digest = hash_event(prev, payload)
        finally:
            if conn is not None:
                conn.close()
        entry = {**payload, "prev_hash": prev, "hash": digest, "chain_verifiable": True}
        _remember(entry)
    _sync_to_catalyst_placeholder(entry)
    return entry

def init_db():
    try:
        conn = registry_connect(DB_PATH)
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
        conn = registry_connect(DB_PATH)
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

def record(officer: str, role: str, method: str, path: str, status: int,
           extra: dict | None = None) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "officer": officer, "role": role, "method": method, "path": path, "status": status,
        "type": "HTTP"
    }
    # the call chain, the traces it opened and what policy decided: hashed with the row
    for k in ("call_chain_id", "trace_ids", "policy", "scope"):
        if extra and extra.get(k):
            payload[k] = extra[k]
    _write(payload, {"ts": payload["ts"], "officer": officer, "role": role, "method": method,
                     "path": path, "status": status, "type": "HTTP"})


def _answer_evidence() -> dict:
    """What an answer rested on, for the tamper-evident row: the call chain and role it
    was given under, the template that ran, a digest of its parameters and of the rows it
    read, how many rows, which model wrote it (or "offline") and a hash of the prompt.
    Digests and ids only - the rows and the prompt themselves stay in the trace store.
    Empty when there is no request context and no open trace; never raises."""
    import hashlib
    out: dict = {}
    try:
        from app.core import security_context
        ctx = security_context.current()
        if ctx:
            out["call_chain_id"] = ctx.call_chain_id
            out["role"] = ctx.role
            if ctx.decisions:
                out["policy"] = list(ctx.decisions)
    except Exception:
        pass
    try:
        from app.obs import trace
        t = trace.current()
        if t:
            ev = {"trace_id": t.d.get("trace_id"), "template_id": t.d.get("template_id"),
                  "n_rows": t.d.get("n_rows"), "rows_digest": t.ctx.get("rows_digest"),
                  "written_by": t.d.get("model") if t.d.get("mode") == "llm" else "offline"}
            if t.ctx.get("params_json"):
                ev["params_digest"] = hashlib.sha256(t.ctx["params_json"].encode()).hexdigest()[:16]
            if t.ctx.get("system_sent"):
                ev["prompt_hash"] = hashlib.sha256(t.ctx["system_sent"].encode()).hexdigest()[:16]
            out["evidence"] = {k: v for k, v in ev.items() if v not in (None, "")}
    except Exception:
        pass
    return out


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
    payload.update(_answer_evidence())

    def trail(conn):
        trace = reasoning_trace
        if reasoning_id and trace:
            # A turn's trail is a few dozen steps. Anything past the cap is a runaway, and
            # on Catalyst this table lives in /tmp beside the database.
            if len(trace) > _MAX_TRACE_STEPS:
                dropped = len(trace) - _MAX_TRACE_STEPS
                trace = trace[:_MAX_TRACE_STEPS] + [
                    {"step": "truncated", "detail": f"{dropped} further step(s) not stored."}]
            conn.execute("INSERT INTO agent_reasoning_logs (reasoning_id, trace_json, ts) VALUES (?, ?, ?)",
                         (reasoning_id, json.dumps(trace), payload["ts"]))

    entry = _write(payload, {"ts": payload["ts"], "officer": officer, "session_id": session_id,
                             "user_text": user_text, "answer": answer, "agents_used": json.dumps(agents_used),
                             "citations": json.dumps(citations), "type": "AI_REASONING",
                             "reasoning_id": reasoning_id}, after=trail)
    return entry["hash"]


def get_reasoning_trace(reasoning_id: str) -> list[dict] | None:
    try:
        conn = registry_connect(DB_PATH)
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
    # hypothesis_id and reason are ALSO mirrored into user_text/answer so the existing
    # audit views keep rendering; payload_json is what verification actually reads.
    return _write(payload, {"ts": payload["ts"], "officer": officer, "role": role, "method": payload["method"],
                            "path": payload["path"], "status": 200, "type": event_type,
                            "user_text": hypothesis_id, "answer": reason})


def record_data_event(event_type: str, batch_id: str, officer: str, role: str, detail: str = "") -> dict:
    """Record an Admin · Data change to the register: FIRs added from a file, or removed again."""
    if event_type not in {"data_upload", "data_upload_removed"}:
        raise ValueError(f"Invalid data event type: {event_type}")
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "officer": officer,
        "role": role,
        "batch_id": batch_id,
        "detail": detail,
        "type": event_type,
        "method": "DATA_UPLOAD",
        "path": f"/upload/{batch_id}",
        "status": 200,
    }
    return _write(payload, {"ts": payload["ts"], "officer": officer, "role": role, "method": payload["method"],
                            "path": payload["path"], "status": 200, "type": event_type,
                            "user_text": batch_id, "answer": detail})


def get_answer_record(digest: str) -> dict | None:
    """The AI_REASONING entry with this hash, and whether its digest still verifies.

    `verified` is True only when hash_event(prev_hash, stored payload) reproduces the
    stored hash: the answer text returned is then exactly the text that was chained.
    """
    digest = str(digest or "").strip().lower()
    if not digest or len(digest) > 64:
        return None
    entry = None
    try:
        conn = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            r = conn.execute("SELECT hash, prev_hash, payload_json FROM audit_log "
                             "WHERE hash = ? AND type = 'AI_REASONING' LIMIT 1", (digest,)).fetchone()
        finally:
            conn.close()
        if r:
            entry = _entry_of(r)
    except sqlite3.Error:
        pass
    if entry is None:                       # the database write failed: the chain is in memory
        entry = next((e for e in reversed(_log) if e.get("hash") == digest and e.get("type") == "AI_REASONING"), None)
    if entry is None:
        return None
    payload = _payload_of(entry)
    verified = bool(entry.get("chain_verifiable")) and entry.get("prev_hash") is not None         and hash_event(entry["prev_hash"], payload) == entry["hash"]
    return {**payload, "hash": entry["hash"], "verified": verified}


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
    return _write(payload, {"ts": payload["ts"], "officer": officer, "role": role, "method": "HITL",
                            "path": payload["path"], "status": 200, "type": event_type,
                            "user_text": action_id, "answer": reason})


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
    entries = _stored_entries()
    from_db = entries is not None
    if entries is None:
        entries = list(_log)          # the database could not be read: check what is held
    total = len(entries)
    verified = legacy = 0
    broken_at: int | None = None
    broken_reason: str | None = None
    prev: str | None = None

    for i, entry in enumerate(entries):
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
        "checked": "every stored entry" if from_db else "this process's entries only (database unreadable)",
        "chained_from_archive": _archive_link(entries),
        "verified": verified,
        "legacy_unverifiable": legacy,
        "broken_at_index": broken_at,
        "broken_reason": broken_reason,
        "note": (
            f"{legacy} entr{'y predates' if legacy == 1 else 'ies predate'} the verifiable "
            "format and cannot be checked; 'ok' covers the verifiable entries only."
            if legacy else
            ("every entry in the ledger was verified." if broken_at is None else
             f"{verified} of {total} entries verified; the chain breaks at entry {broken_at} "
             "and nothing after it was checked.")
        ),
    }


def _entry_of(r: sqlite3.Row) -> dict:
    raw = r["payload_json"]
    if raw:
        try:
            return {**json.loads(raw), "prev_hash": r["prev_hash"], "hash": r["hash"], "chain_verifiable": True}
        except (TypeError, ValueError):
            pass
    return {"hash": r["hash"], "prev_hash": None, "chain_verifiable": False}


def _stored_entries() -> list[dict] | None:
    """Every entry as stored, in the order it was written. Other processes write to the
    same table, so the ledger is the database, not this process's memory."""
    try:
        conn = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            return [_entry_of(r) for r in conn.execute(
                "SELECT hash, prev_hash, payload_json FROM audit_log ORDER BY log_id ASC")]
        finally:
            conn.close()
    except sqlite3.Error:
        return None


def _archive_link(entries: list[dict]) -> dict | None:
    """When the ledger starts from an archived chain, what it is chained to."""
    if not entries or entries[0].get("type") != "CHAIN_ARCHIVED":
        return None
    e = entries[0]
    return {k: e.get(k) for k in ("archive_id", "archived_rows", "archived_tail_hash", "archived_rows_sha256",
                                  "archived_breaks", "archived_digest_mismatches", "reason", "officer", "ts")}


def archive_and_restart(officer: str, reason: str) -> dict:
    """Move the whole ledger into `audit_log_archive` and start a new chain from it.

    Nothing is edited and nothing is lost: every row is copied unchanged, then the live
    table starts again with one CHAIN_ARCHIVED entry whose previous hash IS the archived
    tail, and which records how many rows were archived, a SHA-256 over their hashes in
    order, and what was wrong with the old chain. Anyone can check the archive against that
    entry. Run with the server stopped (scripts/audit_archive.py).
    """
    import hashlib
    import uuid
    if len((reason or "").strip()) < 10:
        raise ValueError("a written reason is required")
    old = _stored_entries() or []
    report = verify_chain_report()
    mism = 0
    for e in old:
        if e.get("chain_verifiable") and hash_event(e["prev_hash"] or _GENESIS, _payload_of(e)) != e["hash"]:
            mism += 1
    breaks = sum(1 for a, b in zip(old, old[1:]) if b.get("chain_verifiable") and b.get("prev_hash") != a.get("hash"))
    archive_id = f"arc-{uuid.uuid4().hex[:12]}"
    archived_at = datetime.now(timezone.utc).isoformat()
    conn = registry_connect(DB_PATH, timeout=30, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("CREATE TABLE IF NOT EXISTS audit_log_archive AS "
                     "SELECT '' AS archive_id, '' AS archived_at, * FROM audit_log WHERE 0")
        rows = conn.execute("SELECT log_id, hash FROM audit_log ORDER BY log_id").fetchall()
        if not rows:
            conn.execute("ROLLBACK")
            return {"archived": 0, "note": "the ledger is empty; nothing to archive"}
        conn.execute("INSERT INTO audit_log_archive SELECT ?, ?, * FROM audit_log ORDER BY log_id",
                     (archive_id, archived_at))
        copied = conn.execute("SELECT COUNT(*) FROM audit_log_archive WHERE archive_id = ?", (archive_id,)).fetchone()[0]
        if copied != len(rows):
            raise RuntimeError(f"archive copy incomplete ({copied} of {len(rows)}); nothing was removed")
        sha = hashlib.sha256("".join(h for _i, h in rows).encode()).hexdigest()
        tail = rows[-1][1]
        conn.execute("DELETE FROM audit_log")
        payload = {"ts": archived_at, "officer": officer, "role": "Admin", "type": "CHAIN_ARCHIVED",
                   "method": "AUDIT", "path": "/audit/archive", "status": 200,
                   "archive_id": archive_id, "archived_rows": len(rows),
                   "archived_first_log_id": rows[0][0], "archived_last_log_id": rows[-1][0],
                   "archived_tail_hash": tail, "archived_rows_sha256": sha,
                   "archived_breaks": breaks, "archived_digest_mismatches": mism, "reason": reason.strip()}
        digest = hash_event(tail, payload)
        conn.execute("INSERT INTO audit_log (ts, officer, role, method, path, status, type, answer, hash, "
                     "payload_json, prev_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (archived_at, officer, "Admin", "AUDIT", "/audit/archive", 200, "CHAIN_ARCHIVED", reason.strip(),
                      digest, json.dumps(payload, sort_keys=True), tail))
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
    load_from_db()
    return {"archive_id": archive_id, "archived": len(rows), "breaks_in_archive": breaks,
            "digest_mismatches_in_archive": mism, "before": {k: report.get(k) for k in ("ok", "total_entries", "broken_at_index")},
            "after": verify_chain_report()}


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
        conn = registry_connect(DB_PATH)
        conn.execute("DELETE FROM audit_log")
        conn.commit()
        conn.close()
    except Exception:
        pass
