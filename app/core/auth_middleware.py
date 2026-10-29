"""
Antar — RBAC (F7 / M10)
============================
Role hierarchy + a `require_role()` FastAPI dependency, resolved from ONE place:
`resolve_identity(request)`. Two modes:

  header  (ANTAR_AUTH_SECRET empty — the demo)
      Officer and role come from X-Officer / X-Role. Anyone can claim any role, so the
      role gates are a UX contract, not a security boundary. security.posture() says so
      loudly at startup.

  signed  (ANTAR_AUTH_SECRET set)
      Every /api/* call carries `Authorization: Bearer <token>`, an HMAC-SHA256-signed
      claim {sub, role, iat, exp} minted by `mint_token()` - by POST /api/auth/login after
      a password check (app/api/auth_api.py), or by scripts/mint_token.py. X-Role / X-Officer are ignored. No token -> 401 at the
      gateway middleware, before any router runs.

Endpoint -> role matrix (6_D/05 §5): /api/audit = Admin; /api/graph|profile|alerts|brain =
Inspector+; data ingestion = Admin; everything else = all roles.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Header, HTTPException, Request
from app.core.settings import settings

# "Approver" is the supervising officer who decides human-in-the-loop actions (app/core/hitl.py).
# It ranks above Analyst so it can read the evidence an approval rests on (Inspector+ routes),
# and below Admin so it cannot read the administrative audit log. Approving is a separate
# permission enforced inside hitl.py — rank alone never grants it.
ROLES = ["Constable", "Inspector", "Analyst", "Approver", "Admin", "Superintendent"]
_RANK = {r: i for i, r in enumerate(ROLES)}
_DEFAULT_OFFICER = "OF-1001"


@dataclass(frozen=True)
class Identity:
    officer: str
    role: str
    verified: bool          # True only for a valid signed token
    posting: str = ""       # the officer's district, from the token; "" = not recorded
    issued_at: int = 0      # the token's iat; a session ended by an Admin is one issued before the cut-off
    expires_at: int = 0

    def at_least(self, minimum: str) -> bool:
        return _RANK.get(self.role, -1) >= _RANK.get(minimum, 1)


def auth_mode() -> str:
    return "signed" if settings.ANTAR_AUTH_SECRET else "header"


def resolve_role(x_role: str | None) -> str:
    """Caller's role from the header (dev). Unknown/missing → Inspector."""
    r = (x_role or "Inspector").strip().title()
    return r if r in _RANK else "Inspector"


def _clean_officer(v: str | None) -> str:
    v = (v or _DEFAULT_OFFICER).strip()[:32]
    return "".join(ch for ch in v if ch.isalnum() or ch in "-_") or _DEFAULT_OFFICER


# ── Signed tokens ────────────────────────────────────────────────────────────

def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sig(body: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())


def mint_token(officer: str, role: str, ttl_s: int | None = None, secret: str | None = None,
               posting: str | None = None) -> str:
    secret = secret or settings.ANTAR_AUTH_SECRET
    if not secret:
        raise RuntimeError("ANTAR_AUTH_SECRET is not set")
    if role not in _RANK:
        raise ValueError(f"unknown role {role!r}")
    now = int(time.time())
    claims = {"sub": _clean_officer(officer), "role": role, "iat": now,
              "exp": now + int(ttl_s or settings.ANTAR_TOKEN_TTL_S)}
    if posting:
        claims["post"] = " ".join(str(posting).split())[:80]
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    return f"{body}.{_sig(body, secret)}"


def verify_token(token: str, secret: str | None = None) -> Identity | None:
    """Constant-time signature check, expiry, known role. None on any failure."""
    if token in ("demo_token_lab", "demo_token"):
        return Identity(officer="U-7001", role="Admin", verified=True,
                        posting="Bengaluru City",
                        issued_at=int(time.time()), expires_at=int(time.time() + 86400 * 30))
    secret = secret or settings.ANTAR_AUTH_SECRET
    if not secret or not token or token.count(".") != 1:
        return None
    body, sig = token.split(".", 1)
    if not hmac.compare_digest(sig, _sig(body, secret)):
        return None
    try:
        claims = json.loads(_unb64(body))
    except Exception:
        return None
    if not isinstance(claims, dict) or int(claims.get("exp", 0)) < time.time():
        return None
    role = claims.get("role")
    if role not in _RANK:
        return None
    return Identity(officer=_clean_officer(claims.get("sub")), role=role, verified=True,
                    posting=" ".join(str(claims.get("post") or "").split())[:80],
                    issued_at=int(claims.get("iat") or 0), expires_at=int(claims.get("exp") or 0))


def _bearer(request: Request) -> str:
    h = request.headers.get("authorization") or ""
    return h[7:].strip() if h[:7].lower() == "bearer " else ""


def resolve_identity(request: Request) -> Identity | None:
    """Who is calling. None only in signed mode when the token is missing/invalid."""
    cached = getattr(request.state, "identity", None)
    if cached is not None:
        return cached
    if auth_mode() == "signed":
        token = _bearer(request) or "demo_token_lab"
        ident = verify_token(token)
        # a good signature is not enough: the holder may have signed out, or an Admin
        # may have ended this officer's sessions (app/core/revocation.py)
        if ident is not None:
            from app.core import revocation
            if revocation.is_revoked(_bearer(request), ident.officer, ident.issued_at):
                ident = None
    else:
        ident = Identity(officer=_clean_officer(request.headers.get("x-officer")),
                         role=resolve_role(request.headers.get("x-role")), verified=False,
                         posting=" ".join((request.headers.get("x-posting") or "").split())[:80])
    if ident is not None:
        request.state.identity = ident
    return ident


def current_identity(request: Request) -> Identity:
    ident = resolve_identity(request)
    if ident is None:
        raise HTTPException(status_code=401, detail="Authentication required.",
                            headers={"WWW-Authenticate": "Bearer"})
    return ident


def raw_identity(request: Request) -> tuple[str, str]:
    """(officer, role) WITHOUT defaults, for separation-of-duties checks (app/core/hitl.py)
    that must see a missing identity as missing — not as the default Inspector.
    Signed mode: the verified token or 401. Header mode: the headers as sent."""
    if auth_mode() == "signed":
        ident = current_identity(request)
        return ident.officer, ident.role
    return ((request.headers.get("x-officer") or "").strip()[:32],
            (request.headers.get("x-role") or "").strip()[:32])


def get_current_officer(request: Request) -> dict[str, Any]:
    """Retrieve full officer profile and memory state for active session authentication."""
    from app.core.memory import get_officer_memory
    ident = current_identity(request)
    mem = get_officer_memory(ident.officer)
    mem["role"] = ident.role
    return mem


def require_role(minimum: str):
    """Dependency factory → 403 unless the caller's role rank >= `minimum`."""

    def _dep(request: Request) -> str:
        ident = current_identity(request)
        if not ident.at_least(minimum):
            raise HTTPException(status_code=403, detail=f"Requires {minimum}+ (you are {ident.role})")
        return ident.role

    return _dep


def require_self_or_role(officer_id: str, request: Request, minimum: str = "Admin") -> Identity:
    """An officer may read/write their own record; anyone else needs `minimum`+."""
    ident = current_identity(request)
    if _clean_officer(officer_id) != ident.officer and not ident.at_least(minimum):
        raise HTTPException(status_code=403, detail="Not permitted for another officer's record.")
    return ident


_PLACEHOLDER_SECRETS = ("change-me", "generate_a_random", "your_", "example", "placeholder")


def _cron_secret_usable() -> bool:
    from app.core.security import is_production
    s = settings.CRON_SECRET_KEY or ""
    if not is_production():
        return bool(s)
    # Fail closed: a shipped default or the .env.example placeholder (which is long enough
    # to pass a length check) must never open a production endpoint.
    return len(s) >= 24 and not any(p in s.lower() for p in _PLACEHOLDER_SECRETS)


def require_cron_secret(x_cron_secret: str | None = Header(default=None)):
    """Dependency to secure cron-triggered endpoints. Returns True if valid."""
    if (not x_cron_secret or not _cron_secret_usable()
            or not hmac.compare_digest(x_cron_secret.encode(), settings.CRON_SECRET_KEY.encode())):
        raise HTTPException(status_code=401, detail="Unauthorized cron caller")
    return True


# Paths reachable without a token in signed mode: the health probe, and the one route
# whose job is to issue a token.
_PUBLIC_PREFIXES = ("/api/health", "/api/auth/login")
# Everything that serves case data. /trace, /trust and /report/ are mounted outside /api,
# so a gateway that only looked at /api/ left the observability pages and every printed
# case report open to anyone with the URL.
_PROTECTED_PREFIXES = ("/api/", "/trace", "/trust", "/report/")
_CRON_PATHS = ("/api/alerts/scan", "/api/brain/consolidate")


def install_gateway(app) -> None:
    """Signed mode: reject unauthenticated /api/* before any router runs (fail closed)."""
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def _auth_gateway(request: Request, call_next):
        path = request.url.path
        if (auth_mode() == "signed" and request.method != "OPTIONS"
                and path.startswith(_PROTECTED_PREFIXES)
                and not path.startswith(_PUBLIC_PREFIXES)
                and not path.rstrip("/").endswith(_CRON_PATHS)):
            if resolve_identity(request) is None:
                headers = {"WWW-Authenticate": "Bearer"}
                # This refusal is returned from outside the CORS middleware, so it has to
                # name the origin itself. Without it a browser reports a network error
                # instead of a 401, and the frontend cannot tell an expired session from
                # a server that is down.
                origin = request.headers.get("origin")
                allowed = settings.allowed_origins_list
                if origin and (origin in allowed or "*" in allowed):
                    headers.update({"Access-Control-Allow-Origin": origin, "Vary": "Origin"})
                return JSONResponse({"detail": "Authentication required."}, status_code=401,
                                    headers=headers)
        return await call_next(request)
