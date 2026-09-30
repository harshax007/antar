"""
/api/chat HTTP contract test — mounts the chat router in isolation (no main.py
lifespan / embedder), runs OFFLINE (heuristic router + local executor + seed JSON).
Proves the end-to-end request path works without Catalyst or a live LLM.
Run: python -m pytest tests/test_chat_api.py -v
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import chat
from app.core.demo_mode import cache_info, clear_demo_cache
from app.core.settings import settings

app = FastAPI()
app.include_router(chat.router, prefix="/api/chat")
client = TestClient(app)


def post(text, lang=None):
    body = {"text": text}
    if lang:
        body["lang"] = lang
    return client.post("/api/chat", json=body).json()


def test_chat_returns_contract_shape():
    r = post("chain snatching in Rajajinagar")
    for key in ["answer", "lang", "citations", "agents_used", "visuals",
                "brain_hits", "reasoning_id", "suggested", "session_id"]:
        assert key in r, f"missing {key}"
    assert r["mode"] == "offline"
    assert r["citations"]                 # crime query → citations present
    assert r["template_id"] == "T1"


def test_chat_detects_kannada():
    r = post("ರಾಜಾಜಿನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು")  # "chain snatching in Rajajinagar"
    assert r["lang"] == "kn"


def test_chat_trend_query_routes_t3():
    r = post("show robbery trend in Bengaluru North last 3 months")
    assert r["template_id"] == "T3"


def test_chat_hotspot_query_routes_t11():
    r = post("where are the theft hotspots this month")
    assert r["template_id"] == "T11"


def test_chat_suspect_lookup_yellappa():
    r = post("find suspect Yellappa")
    assert r["template_id"] == "T2"
    assert r["answer"]


def test_chat_session_id_assigned_and_stable():
    r = client.post("/api/chat", json={"text": "recent crimes", "session_id": "ses-fixed"}).json()
    assert r["session_id"] == "ses-fixed"


def test_demo_mode_uses_scripted_cache(monkeypatch):
    clear_demo_cache()
    monkeypatch.setattr(settings, "DEMO_MODE", True, raising=False)
    monkeypatch.setattr(settings, "QUICKML_CLIENT_ID", "demo-client", raising=False)
    monkeypatch.setattr(settings, "QUICKML_CLIENT_SECRET", "demo-secret", raising=False)

    first = post("show chain snatching in Rajajinagar")
    second = post("  SHOW   CHAIN SNATCHING   IN   RAJAJINAGAR  ")

    assert first["mode"] == "demo"
    assert first["template_id"] == "T1"
    assert first["demo_cache_key"] == "rajajinagar_chain_snatching:en"
    assert first["demo_cache_hit"] is False
    assert second["mode"] == "demo"
    assert second["demo_cache_hit"] is True
    assert second["answer"] == first["answer"]
    assert cache_info()["entries"] == 1


def test_demo_mode_miss_falls_back_to_offline(monkeypatch):
    clear_demo_cache()
    monkeypatch.setattr(settings, "DEMO_MODE", True, raising=False)

    r = post("recent crimes in Whitefield")

    assert r["mode"] == "offline"
    assert r["template_id"] == "T12"
    assert r["demo_cache_key"] is None
    assert r["demo_cache_hit"] is False
