"""
Antar — Encrypted Session Save/Load
========================================
POST /api/session/save          {session_id, payload}  → Fernet-encrypt → disk
GET  /api/session/saved         → [{session_id, saved_at, bytes}]
GET  /api/session/load/{id}     → decrypted payload

Sessions are encrypted at rest (AES-128-CBC + HMAC via cryptography.Fernet).
The key comes from env ANTAR_SESSION_KEY, else a generated key file beside the
database (kept out of the payload dir). Nothing about the conversation —
questions, answers, entities — is readable on disk.

Ownership: the encrypted envelope records the officer who saved it. Listing and loading
are limited to that officer (Admin+ may read any, for supervision and audit); an
envelope without an owner (saved before this rule) is Admin+ only. Officer profile
routes follow the same rule: your own record, or Admin+.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.auth_middleware import current_identity, require_self_or_role

router = APIRouter()

_BASE = Path(__file__).resolve().parents[2]          # antar-backend/
_STORE = _BASE / "data_sessions"
_KEY_FILE = _BASE / ".session_key"
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


_ENVELOPE = "antar.session.v2"


def _seal(owner: str, payload: Any) -> bytes:
    body = {"_v": _ENVELOPE, "owner": owner, "payload": payload}
    return _fernet().encrypt(json.dumps(body, ensure_ascii=False).encode("utf-8"))


def _open(token: bytes) -> tuple[str | None, Any]:
    """(owner, payload). Legacy files were the bare payload -> owner None."""
    body = json.loads(_fernet().decrypt(token).decode("utf-8"))
    if isinstance(body, dict) and body.get("_v") == _ENVELOPE:
        return body.get("owner"), body.get("payload")
    return None, body


def _may_read(owner: str | None, request: Request) -> bool:
    ident = current_identity(request)
    return (owner is not None and owner == ident.officer) or ident.at_least("Admin")


def _fernet() -> Fernet:
    key = os.environ.get("ANTAR_SESSION_KEY", "").strip()
    if not key:
        if _KEY_FILE.exists():
            key = _KEY_FILE.read_text().strip()
        else:
            key = Fernet.generate_key().decode()
            _KEY_FILE.write_text(key)
            try:
                os.chmod(_KEY_FILE, 0o600)      # owner-only where the OS supports it
            except OSError:
                pass
    return Fernet(key.encode())


def _path(session_id: str) -> Path:
    if not _ID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="invalid session_id")
    return _STORE / f"{session_id}.enc"


class SaveRequest(BaseModel):
    session_id: str
    payload: Any            # opaque client thread (messages, mode, lang, …)


@router.post("/save")
async def save_session(req: SaveRequest, request: Request) -> dict:
    _STORE.mkdir(exist_ok=True)
    me = current_identity(request).officer
    p = _path(req.session_id)
    if p.exists():
        # Saving over someone else's id would silently take their conversation over.
        # An ownerless legacy file may be re-saved (and so claimed): overwriting it
        # discloses nothing, and reading it stays Admin+ only.
        try:
            owner, _ = _open(p.read_bytes())
        except (InvalidToken, ValueError):
            owner = None
        if owner is not None and not _may_read(owner, request):
            raise HTTPException(status_code=403, detail="session id belongs to another officer")
    token = _seal(me, req.payload)
    p.write_bytes(token)
    return {"saved": True, "session_id": req.session_id,
            "bytes": len(token), "saved_at": int(time.time()), "encrypted": True}


@router.get("/saved")
async def list_saved(request: Request) -> dict:
    if not _STORE.exists():
        return {"sessions": []}
    out = []
    for p in sorted(_STORE.glob("*.enc"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            owner, _ = _open(p.read_bytes())
        except (InvalidToken, ValueError):
            continue
        if not _may_read(owner, request):
            continue
        out.append({"session_id": p.stem, "saved_at": int(p.stat().st_mtime),
                    "bytes": p.stat().st_size})
    return {"sessions": out}


@router.get("/load/{session_id}")
async def load_session(session_id: str, request: Request) -> dict:
    p = _path(session_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"no saved session {session_id}")
    try:
        owner, payload = _open(p.read_bytes())
    except InvalidToken:
        raise HTTPException(status_code=409, detail="session key mismatch — cannot decrypt")
    if not _may_read(owner, request):
        # 404, not 403: do not confirm that another officer's session id exists
        raise HTTPException(status_code=404, detail=f"no saved session {session_id}")
    return {"session_id": session_id, "payload": payload}


class PreferencesRequest(BaseModel):
    preferences: dict[str, Any]


class BookmarkRequest(BaseModel):
    item: dict[str, Any]


@router.get("/officers")
async def get_all_officers() -> dict:
    """List all available demo login identities and their roles."""
    from app.core.memory import list_officers
    return {"officers": list_officers()}


@router.get("/officer/{officer_id}")
async def get_officer_profile(officer_id: str, request: Request) -> dict:
    """Retrieve full memory, preferences, conclusions, and bookmarks for an officer profile."""
    require_self_or_role(officer_id, request)
    from app.core.memory import get_officer_memory
    return get_officer_memory(officer_id)


@router.post("/officer/{officer_id}/preferences")
async def update_preferences(officer_id: str, req: PreferencesRequest, request: Request) -> dict:
    """Update UI or analytical preferences for an officer."""
    require_self_or_role(officer_id, request)
    from app.core.memory import update_officer_preferences, get_officer_memory
    update_officer_preferences(officer_id, req.preferences)
    return get_officer_memory(officer_id)


@router.post("/officer/{officer_id}/bookmarks")
async def toggle_bookmark(officer_id: str, req: BookmarkRequest, request: Request) -> dict:
    """Add or remove an item from officer bookmarks."""
    require_self_or_role(officer_id, request)
    from app.core.memory import toggle_officer_bookmark, get_officer_memory
    toggle_officer_bookmark(officer_id, req.item)
    return get_officer_memory(officer_id)
