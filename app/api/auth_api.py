"""
Antar - sign-in API
===================
POST /api/auth/login   {user_id, password} -> a signed token for that officer and role
GET  /api/auth/me      who the presented token belongs to

The token is the one `auth_middleware` already verifies on every other route; this is the
only place one is issued to a browser. A wrong id and a wrong password get the same answer
in the same time, five failures lock the id for five minutes (app/core/accounts.py), and
the endpoint is rate-limited per address on top of that.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core import accounts
from app.core.auth_middleware import _bearer, _clean_officer, auth_mode, current_identity, mint_token, require_role
from app.core.rate_limiter import rate_limit
from app.core.settings import settings

router = APIRouter()


class LoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login", dependencies=[Depends(rate_limit(10, 0.1))])
async def login(req: LoginRequest) -> dict:
    if auth_mode() != "signed":
        # Without a signing secret there is nothing to issue. Say so rather than hand back
        # a token-shaped string no route would check.
        raise HTTPException(status_code=503, detail="Sign-in is not configured on this server.")
    wait = accounts.locked_for(req.user_id)
    if wait:
        raise HTTPException(status_code=429, headers={"Retry-After": str(wait)},
                            detail=f"Too many failed attempts. Try again in {max(1, round(wait / 60))} minute(s).")
    # scrypt is deliberately slow: keep it off the event loop.
    acct = await asyncio.to_thread(accounts.verify, req.user_id, req.password)
    if not acct:
        raise HTTPException(status_code=401, detail="User ID or password is incorrect.")
    return {"token": mint_token(acct["id"], acct["role"], posting=acct.get("posting")), "officer": acct["id"], "role": acct["role"],
            "name": acct["name"], "expires_at": int(time.time()) + int(settings.ANTAR_TOKEN_TTL_S)}


@router.post("/logout")
async def logout(request: Request) -> dict:
    """End this session on the server. The token stops working at once, here and in any
    copy of it - signing out used to make only the browser forget it."""
    ident = current_identity(request)
    if ident.verified:
        from app.core import revocation
        revocation.revoke_token(_bearer(request), ident.expires_at)
    return {"signed_out": True}


@router.post("/revoke/{officer}", dependencies=[Depends(require_role("Admin"))])
async def revoke_officer(officer: str, request: Request) -> dict:
    """End every session an officer holds now (a lost device, a changed role). They can
    sign in again; tokens issued before this moment are refused."""
    from app.core import revocation
    target = _clean_officer(officer)
    revocation.revoke_officer(target, by=current_identity(request).officer)
    return {"officer": target, "sessions_ended": True}


@router.get("/me")
async def me(request: Request) -> dict:
    ident = current_identity(request)
    return {"officer": ident.officer, "role": ident.role, "verified": ident.verified}
