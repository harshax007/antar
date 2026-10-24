"""
Antar - Saved findings
======================
What an officer chose to keep from the Brain console, for a later investigation.

A finding shown in a notice is gone when the notice closes. Saving one writes it here,
under the officer who saved it: the agent, the record it ran on, and the whole answer
as it was given - bottom line, scope, evidence, limits, method and suggested next steps.
It is read back by that officer only.

Stored in the application database, never on the officer's own disk: a finding names
accused ids and FIR details, and a text file in a downloads folder is outside every
control this system has (sign-in, roles, the audit ledger).

Each officer keeps at most MAX_PER_OFFICER findings; the oldest go first. Saving the same
finding twice returns the copy already held instead of adding another.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any

from app.core.db_path import DB_PATH, ensure_db_staged
from app.core.db_path import registry_connect

MAX_PER_OFFICER = 200
MAX_BYTES = 24_000            # one finding, serialised
_TEXT = 600                   # a single line of text inside one
_ready = False


def _db() -> sqlite3.Connection:
    global _ready
    ensure_db_staged()
    conn = registry_connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    if not _ready:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_findings (
                id         TEXT PRIMARY KEY,
                officer_id TEXT NOT NULL,
                saved_at   INTEGER NOT NULL,
                agent      TEXT NOT NULL,
                label      TEXT NOT NULL,
                title      TEXT NOT NULL,
                bottom     TEXT NOT NULL,
                payload    TEXT NOT NULL
            )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_saved_findings_officer "
                     "ON saved_findings (officer_id, saved_at DESC)")
        conn.commit()
        _ready = True
    return conn


def _s(v: Any, n: int = _TEXT) -> str:
    return " ".join(str(v or "").split())[:n]


def _lines(v: Any, most: int = 12) -> list[str]:
    return [_s(x) for x in (v if isinstance(v, list) else [])[:most] if _s(x)]


def _clean(finding: dict) -> dict:
    """Keep the fields a finding has, at a bounded size. Nothing else is stored - a client
    cannot use this as a place to put arbitrary data."""
    r = finding.get("result") if isinstance(finding.get("result"), dict) else {}
    return {
        "title": _s(finding.get("title"), 200),
        "agent": _s(finding.get("agent"), 32).lower(),
        "label": _s(finding.get("label"), 160),
        "result": {
            "status": _s(r.get("status"), 24),
            "evidence_class": _s(r.get("evidence_class"), 2).upper() or None,
            "bottom_line": _s(r.get("bottom_line"), 1200),
            "context": _s(r.get("context"), 600),
            "evidence": _lines(r.get("evidence")),
            "limits": _lines(r.get("limits"), 8),
            "method": _lines(r.get("method"), 8),
            "next": _lines(r.get("next"), 6),
        },
        "was": _s(finding.get("was"), 1200) or None,
        "was_at": _s(finding.get("was_at"), 24) or None,
        "received_at": int(finding.get("received_at") or 0) or None,
    }


def _row(r: sqlite3.Row) -> dict:
    try:
        body = json.loads(r["payload"])
    except Exception:
        body = {}
    return {"id": r["id"], "saved_at": r["saved_at"], **body}


def save(officer_id: str, finding: dict) -> dict:
    """Keep one finding for one officer. Returns it as stored, with `already` true when an
    identical one was held before."""
    officer = _s(officer_id, 64)
    if not officer:
        raise ValueError("no officer")
    body = _clean(finding if isinstance(finding, dict) else {})
    if not body["result"]["bottom_line"] and not body["title"]:
        raise ValueError("an empty finding cannot be saved")
    payload = json.dumps(body, ensure_ascii=False)
    if len(payload.encode("utf-8")) > MAX_BYTES:
        raise ValueError("this finding is too large to save")
    bottom = body["result"]["bottom_line"]
    conn = _db()
    try:
        held = conn.execute(
            "SELECT * FROM saved_findings WHERE officer_id = ? AND agent = ? AND label = ? AND bottom = ? "
            "ORDER BY saved_at DESC LIMIT 1", (officer, body["agent"], body["label"], bottom)).fetchone()
        if held:
            return {**_row(held), "already": True}
        fid = uuid.uuid4().hex[:16]
        now = int(time.time())
        conn.execute("INSERT INTO saved_findings (id, officer_id, saved_at, agent, label, title, bottom, payload) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (fid, officer, now, body["agent"], body["label"], body["title"], bottom, payload))
        # the oldest make room: an officer's list does not grow without end
        conn.execute("DELETE FROM saved_findings WHERE officer_id = ? AND id NOT IN ("
                     "SELECT id FROM saved_findings WHERE officer_id = ? ORDER BY saved_at DESC, rowid DESC LIMIT ?)",
                     (officer, officer, MAX_PER_OFFICER))
        conn.commit()
        return {"id": fid, "saved_at": now, **body, "already": False}
    finally:
        conn.close()


def list_for(officer_id: str, limit: int = 50) -> dict:
    """An officer's saved findings, newest first, and how many they hold in all."""
    officer = _s(officer_id, 64)
    conn = _db()
    try:
        rows = conn.execute("SELECT * FROM saved_findings WHERE officer_id = ? ORDER BY saved_at DESC, rowid DESC LIMIT ?",
                            (officer, max(1, min(int(limit), MAX_PER_OFFICER)))).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM saved_findings WHERE officer_id = ?", (officer,)).fetchone()[0]
        return {"items": [_row(r) for r in rows], "total": total, "max": MAX_PER_OFFICER}
    finally:
        conn.close()


def remove(officer_id: str, finding_id: str) -> bool:
    """Delete one of an officer's own findings. Another officer's id removes nothing."""
    conn = _db()
    try:
        n = conn.execute("DELETE FROM saved_findings WHERE officer_id = ? AND id = ?",
                         (_s(officer_id, 64), _s(finding_id, 32))).rowcount
        conn.commit()
        return n > 0
    finally:
        conn.close()
