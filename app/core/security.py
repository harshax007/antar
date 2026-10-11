"""
Antar — HTTP security layer
===========================
Vimaraksha: predict and secure before the threat materialises. For an API that answers
questions over police records, the cheapest threat to predict is the one we hand to an
attacker ourselves — a stack trace, a file path, an upstream error body with a project
id in it. This module makes that impossible by construction:

  • An officer (or attacker) only ever sees a plain message and an `error_id`.
    The full exception is logged server-side under the same id, so support can find it.
  • Every error string that has to leave the process goes through `scrub_text()`,
    which removes filesystem paths, URLs, bearer tokens and key=value secrets.
  • Security headers on every response, a request-body ceiling, and API docs hidden
    in production.

`install(app)` wires all of it. Nothing here changes a successful response body.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from app.core.settings import settings

log = logging.getLogger("antar.security")


# ── Environment ──────────────────────────────────────────────────────────────

def is_production() -> bool:
    env = {(settings.ANTAR_ENV or "").strip().lower(), (settings.CATALYST_ENV or "").strip().lower()}
    return bool(env & {"production", "prod"})


# ── Scrubbing ────────────────────────────────────────────────────────────────
# Order matters: secrets before URLs (a token can sit in a query string), URLs before
# paths (a URL path looks like a Unix path).

_SECRET_PATTERNS = (
    # Authorization: Bearer xxx / bearer xxx
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), r"\1 [redacted]"),
    # key=value / key: value for anything that names itself a secret
    (re.compile(r"(?i)\b([\w-]*(?:api[_-]?key|secret|token|passw(?:or)?d|pwd|credential|"
                r"authorization|client[_-]?id|session[_-]?key)[\w-]*)(\s*[:=]\s*)"
                r"(\"[^\"]*\"|'[^']*'|[^\s,;&}]+)"), r"\1\2[redacted]"),
    # Zoho OAuth token shapes (1000.<hex>.<hex>) and long opaque hex / base64 blobs
    (re.compile(r"\b1000\.[0-9a-f]{16,}(?:\.[0-9a-f]{16,})?\b"), "[redacted]"),
    (re.compile(r"\b[A-Fa-f0-9]{32,}\b"), "[redacted]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "[redacted]"),
)
_URL_RE = re.compile(r"\b(?:https?|file|sqlite|postgres(?:ql)?|mysql|redis)://[^\s\"'<>)]+", re.I)
# Windows drive paths and UNC shares
_WIN_PATH_RE = re.compile(r"(?:\b[A-Za-z]:|\\\\[\w.$-]+)[\\/][^\s\"'<>|*?\n]*")
# Unix paths under roots a server really has — never bare "/api/chat" route names
_NIX_PATH_RE = re.compile(
    r"(?<![\w.:/])/(?:home|Users|usr|app|tmp|var|etc|opt|root|srv|mnt|proc|private|"
    r"workspace|site-packages|lib|data)(?:/[^\s\"'<>|:*?\n]*)?")
_TRACE_RE = re.compile(r'File "[^"]*", line \d+(?:, in \S+)?')
_IP_PORT_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b")


def scrub_text(text: Any, *, urls: bool = True, limit: int = 300) -> str:
    """Make a string safe to show outside the process: no paths, secrets, hosts or frames."""
    if text is None:
        return ""
    s = str(text)
    for pat, repl in _SECRET_PATTERNS:
        s = pat.sub(repl, s)
    if urls:
        s = _URL_RE.sub("[url]", s)
    s = _TRACE_RE.sub("[frame]", s)
    s = _WIN_PATH_RE.sub("[path]", s)
    s = _NIX_PATH_RE.sub("[path]", s)
    s = _IP_PORT_RE.sub("[host]", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def scrub_obj(obj: Any, depth: int = 0) -> Any:
    """scrub_text over every string inside a JSON-shaped value."""
    if depth > 6:
        return None
    if isinstance(obj, str):
        return scrub_text(obj)
    if isinstance(obj, dict):
        return {k: scrub_obj(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [scrub_obj(v, depth + 1) for v in obj]
    return obj


# ── Public errors ────────────────────────────────────────────────────────────

_PUBLIC_BY_STAGE = {
    "llm": "The language model is unavailable right now; the answer uses the verified records only.",
    "db": "The records store could not be read just now. Please retry in a moment.",
    "ingest": "The file could not be processed. Check that it is a valid CSV in the expected format.",
    "vision": "The document scan could not be analysed. A sample extraction is shown instead.",
    "stream": "Something went wrong while answering. Please try again.",
    "job": "The task failed. Please try again.",
    "review": "The adversarial review is unavailable right now.",
}
_GENERIC = "Something went wrong on our side."


def new_error_id() -> str:
    return "ERR-" + uuid.uuid4().hex[:10].upper()


def public_error(exc: BaseException | None, stage: str = "", *, log_it: bool = True) -> dict:
    """The only form an exception may take when it leaves the process.

    Returns {"message": <plain text>, "error_id": <id>} and logs the full exception —
    type, message, traceback — under the same id. The message never contains anything
    derived from the exception itself.
    """
    eid = new_error_id()
    if log_it and exc is not None:
        log.error("public_error %s stage=%s %s: %s", eid, stage or "-",
                  type(exc).__name__, exc, exc_info=exc)
    msg = _PUBLIC_BY_STAGE.get(stage, _GENERIC)
    return {"message": f"{msg} (ref {eid})", "error_id": eid}


def public_message(exc: BaseException | None, stage: str = "") -> str:
    return public_error(exc, stage)["message"]


# ── FastAPI wiring ───────────────────────────────────────────────────────────

_STATUS_TEXT = {
    400: "Bad request.", 401: "Authentication required.", 403: "Not permitted.",
    404: "Not found.", 405: "Method not allowed.", 409: "Conflict.",
    413: "Request too large.", 415: "Unsupported media type.", 422: "Invalid request.",
    429: "Too many requests. Please slow down.",
}


def _max_body_bytes() -> int:
    return max(1, int(settings.ANTAR_MAX_BODY_MB)) * 1024 * 1024


def _security_headers(path: str) -> dict[str, str]:
    h = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-site",
        "Permissions-Policy": "camera=(), microphone=(self), geolocation=(), payment=()",
    }
    # Case data must never sit in a shared or browser cache.
    if path.startswith("/api/"):
        h["Cache-Control"] = "no-store"
        h["Pragma"] = "no-cache"
    # The printable report (/report/...) is the one HTML page the API serves; it
    # inlines its own script and styles. Everything else is JSON and gets nothing.
    if not path.startswith(("/report", "/docs", "/redoc")):
        h["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if is_production():
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return h


def install(app) -> None:
    """Exception handlers + security-header / body-size middleware. Call once in main."""
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        detail = exc.detail
        if exc.status_code >= 500:
            # A handler that raised 500 with str(e) is exactly the leak we are closing.
            # Structured "preparing" payloads (503) are ours and safe once scrubbed.
            if isinstance(detail, dict) and detail.get("preparing"):
                detail = scrub_obj(detail)
            else:
                detail = public_error(None, log_it=False)["message"]
                log.error("http %s on %s: %s", exc.status_code, request.url.path, exc.detail)
        else:
            detail = scrub_obj(detail) if detail is not None else _STATUS_TEXT.get(exc.status_code, "")
        return JSONResponse({"detail": detail}, status_code=exc.status_code,
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        # Pydantic v2 echoes the offending INPUT back ("input", "ctx", "url"). For a
        # police API that input can be a victim's name or a phone number — keep only
        # where the problem is and what kind it is.
        errors = [{"loc": [str(p) for p in e.get("loc", ())], "msg": scrub_text(e.get("msg", ""), limit=160),
                   "type": e.get("type", "")} for e in exc.errors()[:20]]
        return JSONResponse({"detail": errors}, status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        err = public_error(exc, "")
        log.error("unhandled on %s %s ref=%s", request.method, request.url.path, err["error_id"])
        return JSONResponse({"detail": err["message"], "error_id": err["error_id"]}, status_code=500)

    class _Guard:
        """Pure ASGI: body ceiling + security headers. Pure ASGI (not BaseHTTPMiddleware)
        so SSE streams pass through untouched."""

        def __init__(self, app_):
            self.app = app_

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                return await self.app(scope, receive, send)
            path = scope.get("path", "")
            limit = _max_body_bytes()
            for k, v in scope.get("headers", []):
                if k == b"content-length":
                    try:
                        too_big = int(v) > limit
                    except ValueError:
                        too_big = True
                    if too_big:
                        resp = JSONResponse({"detail": _STATUS_TEXT[413]}, status_code=413,
                                            headers=_security_headers(path))
                        return await resp(scope, receive, send)

            seen = 0

            async def guarded_receive():
                nonlocal seen
                msg = await receive()
                if msg.get("type") == "http.request":
                    seen += len(msg.get("body", b""))
                    if seen > limit:
                        # chunked upload past the ceiling: stop reading
                        raise _BodyTooLarge()
                return msg

            extra = [(k.lower().encode(), v.encode()) for k, v in _security_headers(path).items()]
            started = False

            async def send_with_headers(message):
                nonlocal started
                if message["type"] == "http.response.start":
                    started = True
                    names = {k.lower() for k, _ in message.get("headers", [])}
                    message["headers"] = list(message.get("headers", [])) + [
                        (k, v) for k, v in extra if k not in names]
                await send(message)

            try:
                await self.app(scope, guarded_receive, send_with_headers)
            except _BodyTooLarge:
                # FastAPI usually converts this into its own 400 while parsing the body;
                # this branch covers routes that read the stream themselves.
                if not started:
                    resp = JSONResponse({"detail": _STATUS_TEXT[413]}, status_code=413)
                    await resp(scope, receive, send_with_headers)

    app.add_middleware(_Guard)


class _BodyTooLarge(Exception):
    pass


def posture() -> dict:
    """What an operator needs to know before exposing this process. Logged at startup;
    never served to unauthenticated callers."""
    from app.core.auth_middleware import auth_mode
    warnings = []
    prod = is_production()
    if auth_mode() == "header":
        warnings.append("identity is the unsigned X-Role/X-Officer header — any caller can claim Admin; "
                        "set ANTAR_AUTH_SECRET (or wire Catalyst Auth) before real use")
    else:
        from app.core import accounts
        if not accounts.load():
            warnings.append("no officer accounts are configured — nobody can sign in; "
                            "run scripts/set_password.py or set ANTAR_USERS")
    from app.core.auth_middleware import _PLACEHOLDER_SECRETS
    _cs = settings.CRON_SECRET_KEY or ""
    if len(_cs) < 24 or any(p in _cs.lower() for p in _PLACEHOLDER_SECRETS):
        warnings.append("CRON_SECRET_KEY is default/short" + (" — cron endpoints are REFUSED in production" if prod else ""))
    if "*" in settings.allowed_origins_list:
        warnings.append("ALLOWED_ORIGINS contains '*'")
    return {"production": prod, "auth_mode": auth_mode(), "warnings": warnings}
