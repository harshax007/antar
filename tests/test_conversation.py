"""
Conversation memory (multi-turn, M1) + Explain capability (M9) tests.
Offline path; no Catalyst/LLM needed.
Run: python -m pytest tests/test_conversation.py -v
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import chat
from app.core import sessions

app = FastAPI()
app.include_router(chat.router, prefix="/api/chat")
client = TestClient(app)


def post(text, session_id, lang=None):
    body = {"text": text, "session_id": session_id}
    if lang:
        body["lang"] = lang
    return client.post("/api/chat", json=body).json()


def test_session_store_records_turns_and_reasoning():
    sessions.clear("s-unit")
    sessions.append_user_turn("s-unit", "hello", "en")
    sessions.append_assistant_turn("s-unit", "hi", "en", "T1", "r1",
                                   [{"step": "route", "detail": "classified as T1"}])
    turns = sessions.recent_turns("s-unit")
    assert len(turns) == 2 and turns[0]["role"] == "user"
    assert sessions.last_reasoning("s-unit")[0]["detail"] == "classified as T1"


def test_chat_stores_history_across_turns():
    sessions.clear("s-multi")
    post("show chain snatching in Rajajinagar", "s-multi")
    post("who are the repeat offenders", "s-multi")
    turns = sessions.recent_turns("s-multi")
    # 2 user + 2 assistant
    assert len(turns) == 4
    assert turns[0]["text"].startswith("show chain")


def test_explain_replays_reasoning():
    sessions.clear("s-explain")
    r1 = post("show chain snatching in Rajajinagar", "s-explain")
    assert r1["template_id"] == "T1"
    r2 = post("why did you say that?", "s-explain")
    assert r2["template_id"] == "EXPLAIN"
    assert r2["agents_used"] == ["explain"]
    assert "how i reached" in r2["answer"].lower()
    # the replay mentions the query step
    assert "database" in r2["answer"].lower()


def test_explain_with_no_history_is_graceful():
    sessions.clear("s-empty")
    r = post("why?", "s-empty")
    assert r["template_id"] == "EXPLAIN"
    assert "no previous answer" in r["answer"].lower()


def test_explain_kannada():
    sessions.clear("s-kn")
    post("show theft hotspots", "s-kn", lang="en")
    r = post("ಯಾಕೆ?", "s-kn")
    assert r["template_id"] == "EXPLAIN"
    assert r["lang"] == "kn"


def test_reasoning_returned_on_normal_answer():
    sessions.clear("s-reason")
    r = post("show robbery trend in Bengaluru North last 3 months", "s-reason")
    assert r["template_id"] == "T3"
    assert any(s["step"] == "query" for s in r.get("reasoning", []))
