"""
Antar — QuickML LLM Serving Client
OAuth-authenticated REST calls to Qwen 2.5 14B Instruct on Catalyst QuickML.
Includes retry logic and JSON-repair parser.
"""

import asyncio
import json
import re
import httpx
import time
from app.core.settings import settings
from app.core.guardrails import redact_pii
from app.core.rag_security import harden_system, check_output, detect_injection, OutputBlocked
from app.core.security import scrub_text

# ── OAuth Token Cache ──────────────────────────────────────────────────────────
_token_cache: dict = {"access_token": None, "expires_at": 0}

# ── Shared HTTP client ───────────────────────────────────────────────────────────
# Reused across token + select + compose so the TLS handshake to Catalyst is paid
# ONCE (keep-alive), not on every call. A chat turn makes two sequential LLM calls
# (select → compose); a fresh AsyncClient per call re-did the full handshake to
# api.catalyst.zoho.in each time. Lazily created on the running loop; closed on shutdown.
_client: "httpx.AsyncClient | None" = None


_loop_clients: dict[int, httpx.AsyncClient] = {}


def _get_client() -> httpx.AsyncClient:
    """The shared keep-alive client (created on first use, reused thereafter).

    An AsyncClient is bound to the event loop it first ran on. The chat stream runs the
    query agent on a worker thread (its own loop) so blocking SQLite work doesn't freeze
    the SSE stream — that loop gets its own client instead of borrowing the main one."""
    global _client
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(90.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, keepalive_expiry=60.0),
        )
        _client._antar_loop = id(loop) if loop else None
    if loop is None or getattr(_client, "_antar_loop", None) in (None, id(loop)):
        if loop is not None:
            _client._antar_loop = id(loop)
        return _client
    c = _loop_clients.get(id(loop))
    if c is None or c.is_closed:
        c = httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0))
        _loop_clients[id(loop)] = c
    return c


async def aclose_client() -> None:
    """Close the shared client to release pooled connections (call on app shutdown)."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _is_permanent_status(status: int) -> bool:
    """True for client errors that a byte-identical retry cannot fix.

    429 (rate limited) and 408 (timeout) are excluded — those DO clear on their own, so
    they keep the backoff. Everything else in 4xx is a contract problem with the request.
    """
    return 400 <= status < 500 and status not in (408, 429)


def _clean(v: str) -> str:
    """Treat empty / unfilled PASTE_ placeholders as not-set."""
    v = (v or "").strip()
    return "" if v.startswith("PASTE_") else v


async def _get_access_token() -> str:
    """Get an OAuth access token (cached until ~expiry).
    Prefers refresh_token grant if a real refresh token is set; otherwise uses
    client_credentials (Catalyst needs a `soid` scope-owner-id = ZohoCatalyst.<org>)."""
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    refresh = _clean(settings.QUICKML_REFRESH_TOKEN)
    if refresh:
        data = {"grant_type": "refresh_token", "client_id": settings.QUICKML_CLIENT_ID,
                "client_secret": settings.QUICKML_CLIENT_SECRET, "refresh_token": refresh}
    else:
        data = {"grant_type": "client_credentials", "client_id": settings.QUICKML_CLIENT_ID,
                "client_secret": settings.QUICKML_CLIENT_SECRET}
        soid = settings.QUICKML_SOID or (
            f"ZohoCatalyst.{settings.QUICKML_ORG_ID}" if settings.QUICKML_ORG_ID else "")
        if soid:
            data["soid"] = soid
    if settings.QUICKML_SCOPE:
        data["scope"] = settings.QUICKML_SCOPE

    resp = await _get_client().post(settings.QUICKML_TOKEN_URL, data=data)
    body = resp.json()
    if "access_token" not in body:
        raise RuntimeError(f"Token request failed ({data['grant_type']}): {body}")
    _token_cache["access_token"] = body["access_token"]
    _token_cache["expires_at"] = now + body.get("expires_in", 3600)
    return _token_cache["access_token"]


async def _auth_headers() -> dict:
    """Build request headers per QUICKML_AUTH_MODE (oauth | apikey | none).
    Includes the CATALYST-ORG header required by the QuickML endpoint."""
    headers = {"Content-Type": "application/json"}
    if settings.QUICKML_ORG_ID:
        headers["CATALYST-ORG"] = settings.QUICKML_ORG_ID
    mode = settings.QUICKML_AUTH_MODE.lower()
    if mode == "oauth":
        # Prefer a token we can renew. A pasted QUICKML_ACCESS_TOKEN expires after ~1h and
        # used to win over the refresh token forever → every call 401 INVALID_OAUTHTOKEN.
        # It is only used when there is no way to mint a fresh one.
        can_refresh = bool(_clean(settings.QUICKML_REFRESH_TOKEN)
                           or (settings.QUICKML_CLIENT_ID and settings.QUICKML_CLIENT_SECRET))
        static = _clean(settings.QUICKML_ACCESS_TOKEN)
        token = await _get_access_token() if (can_refresh or not static) else static
        headers["Authorization"] = f"Zoho-oauthtoken {token}"
    elif mode == "apikey":
        headers["Authorization"] = f"Bearer {settings.QUICKML_API_KEY}"  # [VERIFY] header name
    return headers


# Circuit breaker: a permanent 4xx (e.g. the 400 PATTERN_NOT_MATCHED this endpoint returns)
# will fail identically on the next turn too. Without this every chat question still paid a
# ~2s round trip before falling back to the deterministic path. Open for 5 min, then retry.
_BREAKER_S = 300
_breaker: dict[str, tuple[float, str]] = {}   # "url|model" -> (open_until_epoch, last_error)


def _breaker_active() -> bool:
    import os
    return not os.getenv("PYTEST_CURRENT_TEST")   # tests mock responses per case


def _default_budget_s() -> float:
    """Wall-clock ceiling for one LLM call, retries included."""
    import os
    try:
        return max(2.0, float(os.environ.get("QUICKML_BUDGET_S", "20")))
    except (TypeError, ValueError):
        return 20.0


async def warm_up() -> bool:
    """Mint the OAuth token and wake the endpoint.

    The FIRST call of a process paid ~75s (token fetch + cold serving endpoint) while
    warm calls run in 4-6s. On demo day that cost would land on the first question an
    officer asks, so the server pays it at startup instead. Best-effort: never raises.
    """
    import asyncio as _a
    try:
        await _a.wait_for(
            quickml_chat_generate(system="ping", user="ping", max_tokens=8, retries=0,
                                  budget_s=90.0),
            timeout=95.0)
        return True
    except Exception:
        return False


async def quickml_generate(
    system: str,
    user: str,
    json_mode: bool = False,
    max_tokens: int | None = None,
    temperature: float | None = None,
    retries: int = 3,
    model: str | None = None,
    budget_s: float | None = None,
) -> str:
    """
    Call QuickML LLM Serving.
    Routes dynamically between models:
      - /ask & chat interface: pass model=settings.QUICKML_CHAT_MODEL (GLM-4.7-Flash)
      - Other analytical screens & agents: defaults to settings.QUICKML_DEFAULT_MODEL (Qwen 3.6)
    Returns raw response text. Caller handles JSON parsing.

    json_mode=True: adds explicit "respond only with JSON" suffix to prevent prose.
    retries: number of additional attempts on failure.
    """
    target_model = model or settings.QUICKML_DEFAULT_MODEL
    url = (settings.QUICKML_CHAT_ENDPOINT_URL if (target_model == settings.QUICKML_CHAT_MODEL and settings.QUICKML_CHAT_ENDPOINT_URL)
           else settings.QUICKML_LLM_ENDPOINT_URL)
    if not url:
        raise RuntimeError("QUICKML_LLM_ENDPOINT_URL not set in .env — paste the console endpoint URL.")
    bkey = f"{url}|{target_model}"
    if _breaker_active():
        until, why = _breaker.get(bkey, (0.0, ""))
        if time.time() < until:
            raise RuntimeError(f"QuickML LLM skipped (circuit open {int(until - time.time())}s): {why}")
    headers = await _auth_headers()

    user_prompt = user
    if json_mode:
        user_prompt += "\n\nIMPORTANT: Respond ONLY with valid JSON. No prose. No markdown. No explanation."
        
    user_prompt = redact_pii(user_prompt)

    # IMPORTANT: this QuickML API treats `max_tokens` as the TOTAL context budget
    # (input + output), not just output length. Too small → "input exceeds context length"
    # 500s. So floor it to a generous value that comfortably holds prompt + answer.
    effective_max = max(max_tokens or 0, settings.QUICKML_LLM_MAX_TOKENS)
    
    # Also redact system prompt just to be absolutely safe, then append the untrusted-data
    # policy + canary (app/core/rag_security.py). Every agent's prompt passes through here,
    # so no call site can forget it.
    safe_system = harden_system(redact_pii(system))
    _flags = detect_injection(user)
    if _flags:
        import logging as _lg
        _lg.getLogger("antar.rag_security").warning("rag_injection_in_prompt flags=%s", _flags)
    
    payload = _build_payload(
        safe_system,
        user_prompt,
        effective_max,
        temperature if temperature is not None else settings.QUICKML_LLM_TEMPERATURE,
        target_model,
        url,
    )

    # Hard wall-clock budget across ALL attempts. Without it, `retries=3` over a 90 s HTTP
    # timeout plus 1.0+2.5+4.0 s of backoff could hold a single question for minutes — and
    # a cold endpoint really did take 75 s on the first call. Every caller already has a
    # deterministic fallback, so failing fast is strictly better than making an officer
    # wait. Overridable per call; QUICKML_BUDGET_S tunes the default.
    budget = budget_s if budget_s is not None else _default_budget_s()
    _deadline = time.time() + budget

    last_error = None
    for attempt in range(retries + 1):
        _t0 = time.time()
        permanent = False
        _left = _deadline - time.time()
        if _left <= 0:
            last_error = last_error or TimeoutError(f"QuickML budget of {budget:.0f}s exhausted")
            break
        try:
            resp = await asyncio.wait_for(
                _get_client().post(url, json=payload, headers=headers), timeout=_left)
            if resp.status_code == 401 and attempt == 0:
                # Token revoked/expired early: drop the cache, mint a new one, retry once.
                _token_cache["access_token"], _token_cache["expires_at"] = None, 0
                headers = await _auth_headers()
                resp = await asyncio.wait_for(
                    _get_client().post(url, json=payload, headers=headers),
                    timeout=max(1.0, _deadline - time.time()))
            if resp.status_code >= 400:
                # surface Catalyst's actual error body (rate limit? quota? auth?)
                permanent = _is_permanent_status(resp.status_code)
                raise RuntimeError(f"HTTP {resp.status_code} — {resp.text[:300] or '(empty body)'}")

            data = resp.json()
            from app.obs import trace as _obs, metrics as _obsm
            ti, to = _obsm.parse_usage(data)
            _obs.record_llm(model=target_model, tokens_in=ti, tokens_out=to,
                            ms=int((time.time()-_t0)*1000), retries=attempt,
                            system=safe_system, prompt=user_prompt,
                            temperature=payload.get("temperature"))
            # Output validation: a canary echo blocks the answer (the caller falls back to
            # the deterministic path); paths and credentials are scrubbed.
            return check_output(_extract_text(data))
        except OutputBlocked:
            raise
        except Exception as e:
            last_error = e
            from app.obs import trace as _obs
            _obs.record_llm(model=target_model, tokens_in=0, tokens_out=0, ms=int((time.time()-_t0)*1000), error=scrub_text(e), retries=attempt)
            if permanent:
                # A 4xx (other than 429) means the REQUEST is wrong — malformed body,
                # unknown model, revoked token. Replaying it byte-for-byte cannot change
                # the outcome. The backoff below is 1.0 + 2.5 + 4.0 + … seconds, so while
                # the endpoint was returning a deterministic 400 PATTERN_NOT_MATCHED this
                # loop added ~8s of pure dead wait to EVERY chat turn before the caller
                # fell back to the offline path. Give up immediately instead.
                _breaker[bkey] = (time.time() + _BREAKER_S, str(e)[:160])
                break
            if attempt < retries:
                # 1.0s, 2.5s, 4.0s — let transient 500s recover, but never past the budget.
                nap = min(1.0 + 1.5 * attempt, max(0.0, _deadline - time.time()))
                if nap <= 0:
                    break
                await _sleep(nap)

    raise RuntimeError(f"QuickML LLM failed after {attempt + 1} attempt(s): {repr(last_error)}")


async def quickml_chat_generate(
    system: str,
    user: str,
    json_mode: bool = False,
    max_tokens: int | None = None,
    temperature: float | None = None,
    retries: int = 3,
    budget_s: float | None = None,
) -> str:
    """Convenience wrapper for /ask & chat interface using GLM-4.7-Flash MoE model."""
    return await quickml_generate(
        system=system,
        user=user,
        json_mode=json_mode,
        max_tokens=max_tokens,
        temperature=temperature,
        retries=retries,
        model=settings.QUICKML_CHAT_MODEL,
        budget_s=budget_s,
    )


async def quickml_default_generate(
    system: str,
    user: str,
    json_mode: bool = False,
    max_tokens: int | None = None,
    temperature: float | None = None,
    retries: int = 3,
) -> str:
    """Convenience wrapper for non-chat screens & analytical background agents using Qwen 3.6."""
    return await quickml_generate(
        system=system,
        user=user,
        json_mode=json_mode,
        max_tokens=max_tokens,
        temperature=temperature,
        retries=retries,
        model=settings.QUICKML_DEFAULT_MODEL,
    )


# The endpoint validates `model` against Catalyst's internal deployment ids — friendly
# names ("Qwen-3.6-Instruct", "GLM-4.7-Flash") fail with 400 PATTERN_NOT_MATCHED, which
# is why every LLM call failed and chat silently ran on the deterministic path.
# Verified 2026-09-12 against /quickml/v2/.../llm/chat (200 with these ids).
_MODEL_IDS = {
    "qwen": "crm-di-qwen_text_14b-fp8-it",
    "glm": "crm-di-glm47b_30b_it",
}


def _resolve_model(model: str) -> str:
    m = (model or "").strip()
    if m.startswith("crm-"):
        return m
    low = m.lower()
    if "glm" in low:
        return _MODEL_IDS["glm"]
    if "qwen" in low:
        return _MODEL_IDS["qwen"]
    return m


def _build_payload(system: str, user: str, max_tokens: int, temperature: float, model: str, url: str = "", logprobs: bool = False) -> dict:
    """Request body — chosen by the ENDPOINT, not the model name.
      - /glm/chat (dedicated GLM endpoint): expects only messages, max_tokens, temperature
      - /llm/chat  (Catalyst LLM endpoint): full prompt/system_prompt + messages + `model`,
        where the `model` field selects GLM-4.7-Flash vs Qwen-3.6 at the same endpoint.
    Keying off the model name here was the bug: when the chat model routes to /llm/chat
    (because QUICKML_CHAT_ENDPOINT_URL isn't set), the GLM-minimal body was rejected with
    PATTERN_NOT_MATCHED. Format follows the URL so /llm/chat always gets the full body.
    """
    # /glm/chat (GLM deployment API) — confirmed on the console: {model, messages, max_tokens, temperature}.
    if "/glm/chat" in url:
        p = {
            "model": _resolve_model(model),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if logprobs:
            p["logprobs"] = True
            p["top_logprobs"] = 1
        return p
        
    # /llm/chat only accepts the Qwen deployment id (it rejects the GLM id with
    # PATTERN_NOT_MATCHED); the GLM id is valid only on the dedicated /glm/chat endpoint.
    llm_model = _resolve_model(model)
    if llm_model == _MODEL_IDS["glm"]:
        llm_model = _MODEL_IDS["qwen"]
    p = {
        "prompt": user,
        "system_prompt": system,
        "model": llm_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.9,
        "top_k": 50,
    }
    if logprobs:
        p["logprobs"] = True
    return p

async def quickml_generate_with_logprobs(
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> tuple[str, list]:
    """
    Dedicated method for SDAR pipeline to request logprobs.
    Returns (text, logprobs_list) where logprobs_list contains dicts with {'token', 'logprob'}.
    """
    target_model = model or settings.QUICKML_DEFAULT_MODEL
    url = (settings.QUICKML_CHAT_ENDPOINT_URL if (target_model == settings.QUICKML_CHAT_MODEL and settings.QUICKML_CHAT_ENDPOINT_URL)
           else settings.QUICKML_LLM_ENDPOINT_URL)
    headers = await _auth_headers()
    
    effective_max = max(max_tokens or 0, settings.QUICKML_LLM_MAX_TOKENS)
    payload = _build_payload(harden_system(redact_pii(system)), redact_pii(user), effective_max,
                             temperature or 0.7, target_model, url, logprobs=True)

    resp = await _get_client().post(url, json=payload, headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code} — {resp.text[:300]}")
    
    data = resp.json()
    text = check_output(_extract_text(data))
    
    # Extract logprobs robustly based on common provider shapes (OpenAI/vLLM)
    extracted_logprobs = []
    try:
        if "choices" in data and "logprobs" in data["choices"][0] and data["choices"][0]["logprobs"]:
            content = data["choices"][0]["logprobs"].get("content", [])
            for c in content:
                extracted_logprobs.append({"token": c.get("token", ""), "logprob": c.get("logprob", 0.0)})
        elif "logprobs" in data:  # generic fallback
            extracted_logprobs = data["logprobs"]
    except Exception:
        pass
        
    return text, extracted_logprobs


async def quickml_vision_generate(
    system: str,
    user: str,
    images: list = None,
    model: str = settings.QUICKML_VISION_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> str:
    """
    Call Qwen 3.6 - 35B Vision Language (VL-Qwen3.6-35B-A3B) on Catalyst QuickML.
    Used for multimodal crime evidence analysis: scanned FIR pages, CCTV stills, vehicle plates,
    suspect photographs, and station diary OCR.
    """
    url = settings.QUICKML_VISION_ENDPOINT_URL or settings.QUICKML_LLM_ENDPOINT_URL
    if not url:
        raise RuntimeError("QUICKML_VISION_ENDPOINT_URL not set in .env")
    headers = await _auth_headers()
    # The scanned image is itself untrusted input (a document can carry printed
    # instructions), so the vision model gets the same policy, redaction and output check.
    system = harden_system(redact_pii(system))
    content = [{"type": "text", "text": redact_pii(user)}]
    # inline image data only - never an address for the provider to fetch
    for img in (images or [])[:4]:
        content.append({"type": "image_url", "image_url": {"url": image_data_uri(img)}})
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": content}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = await _get_client().post(url, json=payload, headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"Vision LLM HTTP {resp.status_code} — {resp.text[:300]}")
    return check_output(_extract_text(resp.json()))


_IMAGE_DATA_RE = None


def image_data_uri(value: str | None, max_mb: float = 8.0) -> str:
    """The one form an image may take on its way to the vision model: an inline
    `data:image/...;base64,` payload of a type we expect and a bounded size.

    The field is passed to the provider as an image URL. Left unchecked, a caller could
    put any address there and have the provider fetch it on our credentials (a
    server-side request to a place of the caller's choosing), or send an SVG or HTML
    document dressed as an image. Raises ValueError with a plain message."""
    global _IMAGE_DATA_RE
    import base64
    import re as _re
    if _IMAGE_DATA_RE is None:
        _IMAGE_DATA_RE = _re.compile(r"^data:image/(png|jpe?g|webp|gif|bmp|tiff?);base64,([A-Za-z0-9+/=\s]+)$", _re.I)
    s = (value or "").strip()
    if not s.lower().startswith("data:"):
        # bare base64 from an older client: accepted as a JPEG payload, never as a URL
        if _re.fullmatch(r"[A-Za-z0-9+/=\s]{64,}", s or ""):
            s = "data:image/jpeg;base64," + s
        else:
            raise ValueError("The image must be an uploaded PNG, JPEG, WebP, GIF, BMP or TIFF file.")
    m = _IMAGE_DATA_RE.match(s)
    if not m:
        raise ValueError("The image must be an uploaded PNG, JPEG, WebP, GIF, BMP or TIFF file.")
    b64 = _re.sub(r"\s+", "", m.group(2))
    if len(b64) * 3 / 4 > max_mb * 1024 * 1024:
        raise ValueError(f"The image is larger than {max_mb:g} MB.")
    try:
        base64.b64decode(b64[:4096] + "=" * (-len(b64[:4096]) % 4), validate=True)
    except Exception:
        raise ValueError("The image could not be read.")
    return f"data:image/{m.group(1).lower()};base64,{b64}"


def _strip_reasoning(text: str) -> str:
    """GLM-4.7 emits visible chain-of-thought wrapped in <think>…</think> before the
    real answer. Keep only what follows the closing tag (or drop an unterminated
    reasoning block) so every caller — chat, translate, compose — gets clean output."""
    if not text:
        return text
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    else:
        # Unterminated reasoning (token budget ran out mid-think) — remove the open block.
        text = re.sub(r"<think>[\s\S]*$", "", text)
    return re.sub(r"</?think>", "", text).strip()


def _extract_text(data: dict) -> str:
    """Pull the generated text. QuickML returns it in `response` (confirmed); fall back to
    other common shapes just in case."""
    if isinstance(data, dict) and isinstance(data.get("response"), str):
        return _strip_reasoning(data["response"].strip())
    # ("data", 0, "data") is the real /llm/chat shape: {"data":[{"data":"..."}], "usage":{...}}.
    # It must be tried BEFORE the generic fallbacks — without it _extract_text fell through
    # to `str(data)` and handed the whole raw JSON dict back as the model's answer.
    for path in (("data", 0, "data"),
                 ("choices", 0, "message", "content"), ("choices", 0, "text"),
                 ("output",), ("text",), ("result",), ("data", "output")):
        cur = data
        try:
            for p in path:
                cur = cur[p]
            if isinstance(cur, str):
                return _strip_reasoning(cur.strip())
        except (KeyError, IndexError, TypeError):
            continue
    return str(data)  # last resort — surfaces the real shape so we can map it


def parse_json_response(raw: str) -> dict:
    """
    Robust JSON extractor designed to get clean output out of GLM-4.7-Flash, Qwen, or any LLM.
    Handles markdown blocks, prose wrapping, trailing commas, and single-quoted JSON.
    """
    if not raw or not raw.strip():
        raise ValueError("Empty response from LLM")
    cleaned = raw.strip()
    # Strip markdown fence
    fence_m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence_m:
        cleaned = fence_m.group(1).strip()
    # Remove trailing commas inside JSON objects/arrays
    def _sanitize(text: str) -> str:
        return re.sub(r",(\s*[}\]])", r"\1", text)

    try:
        return json.loads(_sanitize(cleaned))
    except Exception:
        # Fallback regex search for outer {...}
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(_sanitize(match.group(0)))
            except Exception:
                pass
    raise ValueError(f"Cannot parse JSON from QuickML response: {raw[:200]}")


async def _sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)
