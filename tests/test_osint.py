"""
Tests for Phase 6 OSINT service. No network: the search client is replaced.
The hostile cases (poisoned snippet, script link, no invented claim) are in
tests/test_llm_security.py::TestOpenWeb.
"""
import asyncio

from app.services import osint


class _Resp:
    status_code = 200
    text = ('<div class="result__body"><a class="result__url" href="https://news.example.org/a">n</a>'
            '<a class="result__snippet">Man arrested in connection with a theft.</a></div>')


class _Client:
    def __init__(self, *a, **k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def post(self, *a, **k): return _Resp()


def test_search_osint(monkeypatch):
    monkeypatch.setattr(osint.httpx, "AsyncClient", _Client)
    res = asyncio.new_event_loop().run_until_complete(osint.search_osint("John Doe"))

    assert "claims" in res and "risk_flags" in res and "summary" in res
    assert len(res["claims"]) == 1
    claim = res["claims"][0]
    assert claim["source_url"] == "https://news.example.org/a"
    assert claim["status"] == "unverified"
    assert claim["confidence"] <= 0.6
    assert res["risk_flags"] == ["High-risk keywords found in OSINT"]
