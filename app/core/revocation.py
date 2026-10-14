"""
Antar - ending a session before it expires
==========================================
A signed token is valid until its expiry (8 hours by default); the server holds no session
it could delete. So signing out only made the browser forget the token, and a copied token
kept working. This is the list the gateway checks:

  * one token, when its holder signs out (POST /api/auth/logout);
  * every token an officer was issued before a moment, when an Admin ends that officer's
    sessions (POST /api/auth/revoke/{officer}) - a lost device, a changed role.

Only a SHA-256 of a token is kept, never the token. Entries are dropped once the token
would have expired anyway. Stored in the application database so a restart does not bring
a revoked token back; held in memory so the check costs nothing per request.
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
import time

from app.core.db_path import DB_PATH, ensure_db_staged

_lock = threading.Lock()
_tokens: dict[str, int] = {}          # token hash -> the token's own expiry
_officers: dict[str, int] = {}        # officer -> tokens issued at or before this are dead
_loaded = False


def _conn() -> sqlite3.Connection:
    ensure_db_staged()
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.execute("CREATE TABLE IF NOT EXISTS revoked_tokens (token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS revoked_officers (officer TEXT PRIMARY KEY, not_after INTEGER NOT NULL, "
              "by_officer TEXT, at INTEGER)")
    return c


def _load() -> None:
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        try:
            c = _conn()
            now = int(time.time())
            c.execute("DELETE FROM revoked_tokens WHERE expires_at < ?", (now,))
            c.commit()
            _tokens.update(dict(c.execute("SELECT token_hash, expires_at FROM revoked_tokens")))
            _officers.update(dict(c.execute("SELECT officer, not_after FROM revoked_officers")))
            c.close()
        except sqlite3.Error:
            pass                       # an unreadable list must not lock everyone out; it is re-tried on write
        _loaded = True


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def revoke_token(token: str, expires_at: int) -> None:
    _load()
    key, exp = _h(token), int(expires_at or time.time() + 86400)
    with _lock:
        _tokens[key] = exp
        try:
            c = _conn()
            c.execute("INSERT OR REPLACE INTO revoked_tokens VALUES (?, ?)", (key, exp))
            c.commit()
            c.close()
        except sqlite3.Error:
            pass                       # still revoked for the life of this process


def revoke_officer(officer: str, by: str = "") -> int:
    """End every session this officer holds now. Returns the cut-off."""
    _load()
    now = int(time.time())
    with _lock:
        _officers[officer] = now
        try:
            c = _conn()
            c.execute("INSERT OR REPLACE INTO revoked_officers VALUES (?, ?, ?, ?)", (officer, now, by, now))
            c.commit()
            c.close()
        except sqlite3.Error:
            pass
    return now


def is_revoked(token: str, officer: str, issued_at: int) -> bool:
    _load()
    if not token:
        return False
    now = time.time()
    exp = _tokens.get(_h(token))
    if exp is not None:
        if exp >= now:
            return True
        _tokens.pop(_h(token), None)   # past its own expiry: the signature check refuses it anyway
    cut = _officers.get(officer)
    return cut is not None and int(issued_at or 0) <= cut


def _reset_for_tests() -> None:
    global _loaded
    with _lock:
        _tokens.clear()
        _officers.clear()
        _loaded = False
