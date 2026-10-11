"""
Antar - officer accounts
========================
Who may sign in, and with what role. The login endpoint (app/api/auth_api.py) checks a
password here and, if it matches, mints the signed token every other route requires.

Where accounts come from, first match wins:

  ANTAR_USERS       a JSON object in the environment - how a container is configured,
                    because nothing in the image should be a credential
  ANTAR_USERS_FILE  a JSON file beside the backend (default auth_users.json, git-ignored)

Both hold the same shape, written by scripts/set_password.py:

  {"U-7001": {"role": "Admin", "name": "Operations Officer", "salt": "...", "hash": "..."}}

Only a salted scrypt hash is stored. There is no default account and no default password:
with no accounts configured nobody can sign in, and the startup log says so.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path

from app.core.settings import settings

_ROOT = Path(__file__).resolve().parents[2]

# scrypt cost. ~50 ms and 16 MB per check on the deployment CPU: slow enough that a stolen
# file is expensive to attack, small enough for a 2 GB container to answer a login.
_N, _R, _P, _LEN = 2 ** 14, 8, 1, 32

# Sign-in attempts. Five wrong passwords lock that id for five minutes - per id, so one
# attacker cannot be slowed down by rotating addresses, and counted in memory because a
# lock that survived a restart would let anyone keep an officer out indefinitely.
MAX_FAILURES, LOCK_S = 5, 300
_failures: dict[str, tuple[int, float]] = {}       # id -> (consecutive failures, locked until)
_lock = threading.Lock()


def norm_id(user_id: str | None) -> str:
    return "".join(ch for ch in (user_id or "").strip().upper()[:32] if ch.isalnum() or ch in "-_")


def _users_file() -> Path:
    p = Path(settings.ANTAR_USERS_FILE or "auth_users.json")
    return p if p.is_absolute() else _ROOT / p


def load() -> dict[str, dict]:
    """Every configured account, keyed by id. Read on each call: the file is a few lines,
    and a password changed with set_password.py should count from the next sign-in."""
    raw = (settings.ANTAR_USERS or os.environ.get("ANTAR_USERS") or "").strip()
    try:
        if raw:
            data = json.loads(raw)
        else:
            f = _users_file()
            data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except (OSError, ValueError):
        return {}                                   # unreadable accounts admit nobody
    return {norm_id(k): v for k, v in data.items()
            if isinstance(v, dict) and v.get("salt") and v.get("hash") and v.get("role")}


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_LEN)
    return base64.b64encode(salt).decode(), base64.b64encode(digest).decode()


# Hashed against when the id is unknown, so an unknown id costs the same as a wrong
# password and the response time does not reveal which ids exist.
_DUMMY_SALT, _DUMMY_HASH = hash_password("antar-no-such-account", b"\x00" * 16)


def locked_for(user_id: str) -> int:
    """Seconds this id is still locked, or 0."""
    with _lock:
        n, until = _failures.get(norm_id(user_id), (0, 0.0))
    return max(0, int(until - time.time())) if n >= MAX_FAILURES else 0


def verify(user_id: str, password: str) -> dict | None:
    """The account if the password is right and the id is not locked, else None."""
    uid = norm_id(user_id)
    if locked_for(uid):
        return None
    acct = load().get(uid)
    salt, want = (acct["salt"], acct["hash"]) if acct else (_DUMMY_SALT, _DUMMY_HASH)
    try:
        _, got = hash_password(password or "", base64.b64decode(salt))
    except (ValueError, TypeError):
        got = ""
    ok = bool(acct) and hmac.compare_digest(got, want)
    with _lock:
        if ok:
            _failures.pop(uid, None)
        elif uid:
            n = _failures.get(uid, (0, 0.0))[0] + 1
            _failures[uid] = (n, time.time() + LOCK_S if n >= MAX_FAILURES else 0.0)
            if len(_failures) > 4096:               # ids are attacker-supplied: stay bounded
                _failures.pop(next(iter(_failures)))
    return {"id": uid, "role": acct["role"], "name": acct.get("name") or uid} if ok else None


def set_password(user_id: str, role: str, password: str, name: str = "") -> Path:
    """Create or update one account in the accounts file. Used by scripts/set_password.py."""
    from app.core.auth_middleware import ROLES
    uid = norm_id(user_id)
    if not uid:
        raise ValueError("a user id is required")
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; one of {', '.join(ROLES)}")
    if len(password) < 10:
        raise ValueError("a password needs at least 10 characters")
    f = _users_file()
    try:
        data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except ValueError:
        data = {}
    salt, digest = hash_password(password)
    data[uid] = {"role": role, "name": name or data.get(uid, {}).get("name") or uid,
                 "salt": salt, "hash": digest}
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return f
