"""
Antar — Human-in-the-Loop (HITL) approvals
==========================================
Actions that change something in the real world — sending patrols, putting a person or
pattern on a watchlist — are never executed by the agent or officer that proposes them.
They are parked here until a SUPERVISING officer approves them.

Guarantees (each one is enforced below and covered by tests/test_hitl.py):

  1. Separation of duties. Proposers and approvers are different roles, and an officer
     can never decide on their own proposal. Two people, always.
  2. Approve exactly what was proposed. The payload is SHA-256 hashed at submission. The
     approver must send back the hash of the version they reviewed; if the stored
     payload no longer matches it, the approval is refused.
  3. Nothing is silent. A written justification is required to propose, and a written
     reason to approve, reject or withdraw.
  4. Compliance first. Every proposal is screened by Vigil (prohibited demographic
     targeting, PII over-collection). A REJECTED screen blocks the proposal outright; a
     FLAGGED one is carried to the approver.
  5. Decisions expire. A patrol request from twelve hours ago is not a decision anyone
     should still be taking; stale proposals move to EXPIRED and cannot be approved.
  6. Everything is on the record. Proposed / approved / rejected / withdrawn / expired /
     executed / failed each write a hash-chained audit entry (audit_store).

Lifecycle:
    PENDING ─approve→ APPROVED ─execute→ EXECUTED | FAILED
    PENDING ─reject→  REJECTED
    PENDING ─withdraw→ WITHDRAWN          (proposer only)
    PENDING ─ttl→     EXPIRED             (evaluated lazily on every read)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable

from app.core.db_path import DB_PATH  # noqa: F401 — module attribute, overridable in tests
import app.core.db_path as _db_path_mod

# ── roles ─────────────────────────────────────────────────────────────────────
PROPOSER_ROLES = {"Inspector", "Analyst", "Admin"}
APPROVER_ROLES = {"Approver", "Superintendent"}

MIN_JUSTIFICATION = 12   # characters — "ok" is not a justification
MIN_REASON = 8

STATUSES = ("PENDING", "APPROVED", "EXECUTED", "FAILED", "REJECTED", "WITHDRAWN", "EXPIRED")
TERMINAL = {"EXECUTED", "FAILED", "REJECTED", "WITHDRAWN", "EXPIRED"}


class HitlError(Exception):
    """A refused HITL operation. `code` maps to an HTTP status in the API layer."""

    def __init__(self, code: int, error: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code, self.error, self.message, self.extra = code, error, message, extra

    def detail(self) -> dict:
        return {"error": self.error, "message": self.message, **self.extra}


def _norm_role(role: str | None) -> str:
    return (role or "").strip().title()


# ── action types + executors ──────────────────────────────────────────────────
_DEPLOYMENTS: list[dict] = []          # executed patrol orders (process lifetime)
_lock = threading.Lock()


def _validate_watch(p: dict) -> dict:
    wt = str(p.get("watch_type") or "").strip().lower()
    target = str(p.get("target") or "").strip()
    label = str(p.get("label") or "").strip()
    if wt not in {"entity", "pattern", "corridor"}:
        raise HitlError(422, "invalid_payload", "watch_type must be entity, pattern or corridor")
    if not target:
        raise HitlError(422, "invalid_payload", "a watch target is required")
    return {"watch_type": wt, "target": target, "label": label or f"{wt.title()} watch · {target}"}


def _validate_patrol(p: dict) -> dict:
    zone = str(p.get("zone") or "").strip()
    if not zone:
        raise HitlError(422, "invalid_payload", "a zone is required for a patrol redeployment")
    try:
        units = int(p.get("units") or 0)
        hours = int(p.get("duration_hours") or 0)
    except (TypeError, ValueError):
        raise HitlError(422, "invalid_payload", "units and duration_hours must be whole numbers")
    if not 1 <= units <= 20:
        raise HitlError(422, "invalid_payload", "units must be between 1 and 20")
    if not 1 <= hours <= 72:
        raise HitlError(422, "invalid_payload", "duration_hours must be between 1 and 72")
    shift = str(p.get("shift") or "").strip().lower()
    if shift not in {"morning", "evening", "night", "all-day"}:
        raise HitlError(422, "invalid_payload", "shift must be morning, evening, night or all-day")
    return {"zone": zone, "units": units, "duration_hours": hours, "shift": shift,
            "crime_focus": str(p.get("crime_focus") or "all crimes").strip()}


def _exec_watch(p: dict, action: dict) -> dict:
    from app.agents import sentinel_agent
    return sentinel_agent.register_watch(
        watch_type=p["watch_type"], target=p["target"], label=p["label"],
        officer_id=action["proposed_by"],
    )


def _exec_patrol(p: dict, action: dict) -> dict:
    order = {
        "order_id": f"DEP-{uuid.uuid4().hex[:6].upper()}",
        **p,
        "requested_by": action["proposed_by"],
        "authorised_by": action["decided_by"],
        "action_id": action["action_id"],
        "issued_at": time.time(),
        "active_until": time.time() + p["duration_hours"] * 3600,
    }
    with _lock:
        _DEPLOYMENTS.append(order)
    try:
        from app.services.product_store import put_product
        put_product(f"deployment:{order['order_id']}", order, ttl=p["duration_hours"] * 3600)
    except Exception:  # noqa: BLE001 — the order record above is authoritative
        pass
    return order


def _title_watch(p: dict) -> str:
    return f"Add {p['watch_type']} watch · {p['target']}"


def _title_patrol(p: dict) -> str:
    return f"Deploy {p['units']} unit{'s' if p['units'] != 1 else ''} to {p['zone']} · {p['shift']}"


ACTION_TYPES: dict[str, dict[str, Any]] = {
    "watchlist_add": {
        "label": "Watchlist add", "agent": "sentinel", "risk": "medium", "ttl_hours": 72,
        "validate": _validate_watch, "execute": _exec_watch, "title": _title_watch,
    },
    "patrol_redeployment": {
        "label": "Patrol redeployment", "agent": "alert_suggest", "risk": "high", "ttl_hours": 12,
        "validate": _validate_patrol, "execute": _exec_patrol, "title": _title_patrol,
    },
}


# ── storage ───────────────────────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS hitl_actions (
    action_id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    agent TEXT,
    title TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    justification TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    compliance_json TEXT,
    risk TEXT NOT NULL,
    status TEXT NOT NULL,
    proposed_by TEXT NOT NULL,
    proposed_role TEXT NOT NULL,
    proposed_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    decided_by TEXT,
    decided_role TEXT,
    decided_at REAL,
    decision_reason TEXT,
    executed_at REAL,
    execution_json TEXT,
    error TEXT
)
"""


def _db() -> str:
    return getattr(_db_path_mod, "DB_PATH")


@contextmanager
def _conn():
    # Closed on exit, not just committed: sqlite3's own context manager leaves the
    # handle open, and lingering handles lock the database file on Windows.
    c = sqlite3.connect(_db())
    c.row_factory = sqlite3.Row
    try:
        c.execute(_SCHEMA)
        c.execute("CREATE INDEX IF NOT EXISTS ix_hitl_status ON hitl_actions(status, proposed_at)")
        yield c
    finally:
        c.close()


def payload_hash(action_type: str, payload: dict) -> str:
    canon = json.dumps({"action_type": action_type, "payload": payload}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["payload"] = json.loads(d.pop("payload_json"))
    d["evidence"] = json.loads(d.pop("evidence_json") or "[]")
    d["compliance"] = json.loads(d.pop("compliance_json") or "null")
    d["execution"] = json.loads(d.pop("execution_json") or "null")
    d["type_label"] = ACTION_TYPES.get(d["action_type"], {}).get("label", d["action_type"])
    # Integrity is re-verified on every read so the UI never shows a stale "intact".
    d["integrity_ok"] = payload_hash(d["action_type"], d["payload"]) == d["payload_hash"]
    return d


def _audit(event: str, action: dict, officer: str, role: str, reason: str = "") -> None:
    try:
        from app.services import audit_store
        audit_store.record_hitl_event(
            event, action_id=action["action_id"], action_type=action["action_type"],
            payload_hash=action["payload_hash"], officer=officer, role=role, reason=reason,
        )
    except Exception:  # noqa: BLE001 — audit failure must not strand the queue
        pass


def _expire_due(c: sqlite3.Connection) -> None:
    now = time.time()
    due = c.execute("SELECT * FROM hitl_actions WHERE status='PENDING' AND expires_at < ?", (now,)).fetchall()
    for r in due:
        c.execute("UPDATE hitl_actions SET status='EXPIRED', decided_at=? WHERE action_id=? AND status='PENDING'",
                  (now, r["action_id"]))
        a = _row(r)
        _audit("hitl_expired", a, "system", "System", "no decision before expiry")
    if due:
        c.commit()


# ── operations ────────────────────────────────────────────────────────────────
def propose(action_type: str, payload: dict, *, officer: str, role: str,
            justification: str, evidence: list | None = None) -> dict:
    role = _norm_role(role)
    officer = (officer or "").strip()
    if action_type not in ACTION_TYPES:
        raise HitlError(422, "unknown_action_type", f"'{action_type}' is not a reviewable action",
                        allowed=sorted(ACTION_TYPES))
    if role not in PROPOSER_ROLES:
        raise HitlError(403, "role_cannot_propose",
                        f"Role '{role or 'none'}' cannot propose actions. Approvers review; they do not request.")
    if not officer:
        raise HitlError(403, "officer_required", "An identified officer is required to propose an action.")
    just = (justification or "").strip()
    if len(just) < MIN_JUSTIFICATION:
        raise HitlError(422, "justification_required",
                        f"Explain why this action is needed (at least {MIN_JUSTIFICATION} characters).")

    spec = ACTION_TYPES[action_type]
    clean = spec["validate"](payload or {})
    h = payload_hash(action_type, clean)

    # Vigil compliance screen over what the approver will actually read.
    compliance = None
    try:
        from app.agents.vigil_agent import audit_request
        screened = " ".join([spec["title"](clean), clean.get("label", ""), just])
        rec = audit_request(screened, officer=officer)
        compliance = {k: rec.get(k) for k in ("receipt_id", "status", "flags", "bnss_citation", "explanation")}
    except Exception as exc:  # noqa: BLE001
        from app.core.security import public_message
        compliance = {"status": "UNAVAILABLE", "flags": ["Compliance screen unavailable. " + public_message(exc)]}
    if compliance.get("status") == "REJECTED":
        raise HitlError(422, "compliance_rejected",
                        "Vigil compliance screen rejected this proposal.", compliance=compliance)

    with _conn() as c:
        _expire_due(c)
        dup = c.execute("SELECT * FROM hitl_actions WHERE status='PENDING' AND payload_hash=?", (h,)).fetchone()
        if dup:
            out = _row(dup)
            out["duplicate"] = True          # idempotent: the same request is not queued twice
            return out
        now = time.time()
        action = {
            "action_id": f"HITL-{uuid.uuid4().hex[:8].upper()}",
            "action_type": action_type, "agent": spec["agent"], "title": spec["title"](clean),
            "payload_hash": h, "justification": just, "risk": spec["risk"], "status": "PENDING",
            "proposed_by": officer, "proposed_role": role, "proposed_at": now,
            "expires_at": now + spec["ttl_hours"] * 3600,
        }
        c.execute(
            """INSERT INTO hitl_actions (action_id, action_type, agent, title, payload_json, payload_hash,
               justification, evidence_json, compliance_json, risk, status, proposed_by, proposed_role,
               proposed_at, expires_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (action["action_id"], action_type, spec["agent"], action["title"], json.dumps(clean, sort_keys=True),
             h, just, json.dumps(evidence or [], ensure_ascii=False), json.dumps(compliance),
             spec["risk"], "PENDING", officer, role, now, action["expires_at"]))
        c.commit()
        row = c.execute("SELECT * FROM hitl_actions WHERE action_id=?", (action["action_id"],)).fetchone()
    out = _row(row)
    _audit("hitl_proposed", out, officer, role, just)
    return out


def get(action_id: str) -> dict:
    with _conn() as c:
        _expire_due(c)
        r = c.execute("SELECT * FROM hitl_actions WHERE action_id=?", (action_id,)).fetchone()
    if not r:
        raise HitlError(404, "not_found", f"No action '{action_id}'.")
    return _row(r)


def list_actions(status: str = "pending", officer: str | None = None, limit: int = 100) -> list[dict]:
    q, args = "SELECT * FROM hitl_actions", []
    s = (status or "all").lower()
    if s == "pending":
        q += " WHERE status='PENDING'"
    elif s == "decided":
        q += " WHERE status!='PENDING'"
    elif s.upper() in STATUSES:
        q += " WHERE status=?"
        args.append(s.upper())
    if officer:
        q += (" AND" if " WHERE " in q else " WHERE") + " proposed_by=?"
        args.append(officer)
    order = "expires_at ASC" if s == "pending" else "COALESCE(decided_at, proposed_at) DESC"
    q += f" ORDER BY {order} LIMIT ?"
    args.append(max(1, min(int(limit), 500)))
    with _conn() as c:
        _expire_due(c)
        rows = c.execute(q, args).fetchall()
    return [_row(r) for r in rows]


def stats() -> dict:
    with _conn() as c:
        _expire_due(c)
        by = {s: 0 for s in STATUSES}
        for r in c.execute("SELECT status, COUNT(*) n FROM hitl_actions GROUP BY status"):
            by[r["status"]] = r["n"]
        high = c.execute("SELECT COUNT(*) FROM hitl_actions WHERE status='PENDING' AND risk='high'").fetchone()[0]
        soon = c.execute("SELECT COUNT(*) FROM hitl_actions WHERE status='PENDING' AND expires_at < ?",
                         (time.time() + 2 * 3600,)).fetchone()[0]
    return {"by_status": by, "pending": by["PENDING"], "pending_high_risk": high, "expiring_within_2h": soon}


def _decide_guard(action: dict, officer: str, role: str, reason: str) -> None:
    if role not in APPROVER_ROLES:
        raise HitlError(403, "role_cannot_decide",
                        f"Role '{role or 'none'}' cannot decide actions. A supervising officer (Approver) must.")
    if not officer:
        raise HitlError(403, "officer_required", "An identified officer is required to decide.")
    if officer == action["proposed_by"]:
        raise HitlError(403, "self_approval_forbidden",
                        "You proposed this action. A different officer must decide it.")
    if action["status"] != "PENDING":
        raise HitlError(409, "not_pending", f"This action is already {action['status']}.", status=action["status"])
    if len((reason or "").strip()) < MIN_REASON:
        raise HitlError(422, "reason_required", f"Record the reason for this decision (at least {MIN_REASON} characters).")


def approve(action_id: str, *, officer: str, role: str, reason: str, reviewed_hash: str) -> dict:
    role, officer = _norm_role(role), (officer or "").strip()
    action = get(action_id)
    _decide_guard(action, officer, role, reason)
    if not action["integrity_ok"]:
        _audit("hitl_integrity_failure", action, officer, role, "stored payload does not match its hash")
        raise HitlError(409, "integrity_failure",
                        "The stored action no longer matches the version that was proposed. It cannot be approved.")
    if (reviewed_hash or "").strip() != action["payload_hash"]:
        raise HitlError(409, "stale_review",
                        "The action changed after you opened it. Reload and review the current version.",
                        current_hash=action["payload_hash"])

    now = time.time()
    with _conn() as c:
        cur = c.execute(
            """UPDATE hitl_actions SET status='APPROVED', decided_by=?, decided_role=?, decided_at=?,
               decision_reason=? WHERE action_id=? AND status='PENDING'""",
            (officer, role, now, reason.strip(), action_id))
        c.commit()
        if cur.rowcount != 1:   # someone else decided in between
            raise HitlError(409, "not_pending", "This action was decided by someone else a moment ago.")
    action = get(action_id)
    _audit("hitl_approved", action, officer, role, reason.strip())

    # Execute only after the approval is durably recorded.
    spec = ACTION_TYPES[action["action_type"]]
    try:
        result = spec["execute"](action["payload"], action)
        with _conn() as c:
            c.execute("UPDATE hitl_actions SET status='EXECUTED', executed_at=?, execution_json=? WHERE action_id=?",
                      (time.time(), json.dumps(result, default=str), action_id))
            c.commit()
        action = get(action_id)
        _audit("hitl_executed", action, "system", "System", action["title"])
    except Exception as exc:  # noqa: BLE001 — record the failure, never pretend it ran
        # The action record is served back to officers — store a scrubbed reason and the
        # log reference, never the raw exception.
        from app.core.security import public_error, scrub_text
        _err = public_error(exc, "job")
        _why = f"{type(exc).__name__}: {scrub_text(exc, limit=200)} ({_err['error_id']})"
        with _conn() as c:
            c.execute("UPDATE hitl_actions SET status='FAILED', error=? WHERE action_id=?", (_why[:500], action_id))
            c.commit()
        action = get(action_id)
        _audit("hitl_failed", action, "system", "System", _why[:200])
    return action


def reject(action_id: str, *, officer: str, role: str, reason: str) -> dict:
    role, officer = _norm_role(role), (officer or "").strip()
    action = get(action_id)
    _decide_guard(action, officer, role, reason)
    with _conn() as c:
        cur = c.execute(
            """UPDATE hitl_actions SET status='REJECTED', decided_by=?, decided_role=?, decided_at=?,
               decision_reason=? WHERE action_id=? AND status='PENDING'""",
            (officer, role, time.time(), reason.strip(), action_id))
        c.commit()
        if cur.rowcount != 1:
            raise HitlError(409, "not_pending", "This action was decided by someone else a moment ago.")
    action = get(action_id)
    _audit("hitl_rejected", action, officer, role, reason.strip())
    return action


def withdraw(action_id: str, *, officer: str, role: str, reason: str) -> dict:
    role, officer = _norm_role(role), (officer or "").strip()
    action = get(action_id)
    if officer != action["proposed_by"]:
        raise HitlError(403, "not_proposer", "Only the officer who proposed an action can withdraw it.")
    if action["status"] != "PENDING":
        raise HitlError(409, "not_pending", f"This action is already {action['status']}.", status=action["status"])
    if len((reason or "").strip()) < MIN_REASON:
        raise HitlError(422, "reason_required", f"Record why you are withdrawing it (at least {MIN_REASON} characters).")
    with _conn() as c:
        c.execute("""UPDATE hitl_actions SET status='WITHDRAWN', decided_by=?, decided_role=?, decided_at=?,
                     decision_reason=? WHERE action_id=? AND status='PENDING'""",
                  (officer, role, time.time(), reason.strip(), action_id))
        c.commit()
    action = get(action_id)
    _audit("hitl_withdrawn", action, officer, role, reason.strip())
    return action


def active_deployments() -> list[dict]:
    now = time.time()
    with _lock:
        return [d for d in reversed(_DEPLOYMENTS) if d["active_until"] > now]


def _reset_for_tests() -> None:
    with _lock:
        _DEPLOYMENTS.clear()
    with _conn() as c:
        c.execute("DELETE FROM hitl_actions")
        c.commit()
