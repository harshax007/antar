"""
QuickML LLM client — HTTP behaviour (success, retry/error surfacing) and shared-client
reuse. Uses httpx.MockTransport, so NO network or credentials are needed (conftest forces
offline; here we set auth_mode=none + a dummy endpoint, so no token fetch happens).

Run: python -m pytest tests/test_quickml.py -v
"""

import asyncio

import httpx
import pytest

from app.services import quickml
from app.core.settings import settings


@pytest.fixture
def quickml_env(monkeypatch):
    """No token fetch (auth=none), a dummy endpoint, instant backoff, clean shared client."""
    monkeypatch.setattr(settings, "QUICKML_AUTH_MODE", "none", raising=False)
    monkeypatch.setattr(settings, "QUICKML_LLM_ENDPOINT_URL", "https://mock.test/llm/chat", raising=False)
    monkeypatch.setattr(settings, "QUICKML_ORG_ID", "", raising=False)

    async def _no_sleep(_seconds):   # don't actually wait during retry tests
        return None
    monkeypatch.setattr(quickml, "_sleep", _no_sleep)
    # the provider is read from settings (app/services/llm.py); unset, the call stops before
    # the mocked endpoint is reached
    from app.services import llm as _llm
    monkeypatch.setattr(_llm, "provider", lambda: "quickml")

    quickml._client = None
    yield
    # tidy up the mock client so it can't leak into other tests
    if quickml._client is not None and not quickml._client.is_closed:
        try:
            asyncio.run(quickml.aclose_client())
        except Exception:
            pass
    quickml._client = None


def _install(handler):
    """Point the shared client at an in-process MockTransport (no real network)."""
    quickml._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_generate_success_and_client_is_reused(quickml_env):
    """200 + {response} → trimmed text; the shared client is a reused singleton."""
    def handler(request):
        return httpx.Response(200, json={"response": "  hello from qwen  "})
    _install(handler)

    out = asyncio.run(quickml.quickml_generate(system="s", user="u"))
    assert out == "hello from qwen"
    assert quickml._get_client() is quickml._get_client()   # not recreated per call


def test_generate_retries_then_raises(quickml_env):
    """Persistent HTTP 500 → retried, then RuntimeError surfacing the status code."""
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(500, text="overloaded")
    _install(handler)

    with pytest.raises(RuntimeError) as ei:
        asyncio.run(quickml.quickml_generate(system="s", user="u", retries=1))
    assert calls["n"] == 2          # initial attempt + 1 retry
    assert "500" in str(ei.value)
