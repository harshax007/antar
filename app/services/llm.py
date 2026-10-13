"""
Antar - which language model, if any
====================================
Antar does not depend on one model. The model writes sentences from facts it is handed; it
never produces a number, a query or an action. So the provider is a setting:

    ANTAR_LLM_PROVIDER = quickml             Zoho Catalyst QuickML (the hosted default)
                       = openai_compatible   any server that speaks /chat/completions - most
                                             hosted models, and local servers such as Ollama,
                                             llama.cpp and vLLM (a model on the station's own
                                             machine: nothing leaves the building)
                       = none                no model. Every caller has a record-based answer.
                       = (unset)             quickml if its credentials are set, otherwise none

Every provider goes through the same choke point, `app.services.quickml.quickml_generate`:
the untrusted-data policy and canary are added, PII is redacted on the way out, the output
is checked on the way back, the call is traced, and it runs under a time budget. A backend
only sends bytes and returns text, so a new provider cannot forget a protection.

`generate` is the name new code should import. The older name stays because thirty call
sites use it; they are the same function.
"""
from __future__ import annotations

from urllib.parse import urlparse

from app.core.settings import settings

PROVIDERS = ("quickml", "openai_compatible", "none")


def provider() -> str:
    """The provider in force. An unknown value is treated as `none`: a typo in a setting
    must not send police text to an address nobody chose."""
    p = (getattr(settings, "ANTAR_LLM_PROVIDER", "") or "").strip().lower().replace("-", "_")
    if not p:
        return "quickml" if (settings.QUICKML_CLIENT_ID and settings.QUICKML_CLIENT_SECRET) else "none"
    if p in ("openai", "openai_compatible", "local", "ollama", "vllm", "llamacpp"):
        return "openai_compatible" if (getattr(settings, "ANTAR_LLM_BASE_URL", "") or "").strip() else "none"
    return p if p in PROVIDERS else "none"


def available() -> bool:
    """Is there a model to ask? DEMO_MODE keeps the scripted, record-only path."""
    return provider() != "none" and not settings.DEMO_MODE


def is_local() -> bool:
    """True when the model is on this machine or this network: no case text leaves it."""
    if provider() != "openai_compatible":
        return False
    host = (urlparse(_base_url()).hostname or "").lower()
    return (host in ("localhost", "127.0.0.1", "::1") or host.endswith((".local", ".lan", ".internal"))
            or host.startswith(("10.", "192.168.")) or any(host.startswith(f"172.{n}.") for n in range(16, 32)))


def _base_url() -> str:
    return (getattr(settings, "ANTAR_LLM_BASE_URL", "") or "").strip().rstrip("/")


def describe() -> dict:
    """What an operator, the agent card or a status page may say about the model. The host
    is named; the address, the key and the project id are not."""
    p = provider()
    if p == "none":
        return {"provider": "none", "model": None, "where": "no model: answers come from the records only"}
    if p == "openai_compatible":
        return {"provider": p, "model": settings.ANTAR_LLM_MODEL or "(server default)",
                "where": "on this machine or network" if is_local() else (urlparse(_base_url()).hostname or "remote server")}
    return {"provider": p, "model": settings.QUICKML_DEFAULT_MODEL, "chat_model": settings.QUICKML_CHAT_MODEL,
            "where": "Zoho Catalyst QuickML"}


def compatible_request(system: str, user: str, max_tokens: int | None, temperature: float,
                       model: str | None = None) -> tuple[str, dict, dict]:
    """(url, headers, body) for a /chat/completions server. `max_tokens` here is the length
    of the reply, as that API defines it - not QuickML's total-context meaning."""
    base = _base_url()
    url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
    headers = {"Content-Type": "application/json"}
    key = (getattr(settings, "ANTAR_LLM_API_KEY", "") or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = {
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": int(max_tokens or 1024),
        "temperature": temperature,
        "stream": False,
    }
    name = (settings.ANTAR_LLM_MODEL or "").strip()
    if name:
        body["model"] = name
    return url, headers, body


async def generate(system: str, user: str, **kw) -> str:
    """Ask the configured model. Raises when there is none or it fails; callers fall back."""
    from app.services.quickml import quickml_generate
    return await quickml_generate(system=system, user=user, **kw)
