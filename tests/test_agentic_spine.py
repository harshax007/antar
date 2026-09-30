from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents.agentic_spine import verify_claims
from app.api import chat
from app.core import sessions


app = FastAPI()
app.include_router(chat.router, prefix="/api/chat")
client = TestClient(app)


def post(text: str) -> dict:
    sessions.clear("s-agentic")
    return client.post("/api/chat", json={"text": text, "session_id": "s-agentic"}).json()


def test_agentic_spine_fans_out_to_profile_and_network():
    r = post("profile Raju and show his network links")

    assert r["mode"] == "offline"
    assert {"query", "profile", "network"}.issubset(set(r["agents_used"]))
    assert r["confidence"] >= 0.9
    # Profile data is in results["profile"] or visuals["profile"] depending on graph version
    profile_data = r.get("visuals", {}).get("profile") or {}
    graph_data = r.get("visuals", {}).get("graph") or {}
    # Core invariant: the response includes suspects from Raju's T2 query (S0001)
    suspects = r.get("suspects", [])
    rows = r.get("rows", [])
    has_raju = (
        (profile_data and profile_data.get("suspect_id") == "S0001") or
        any(s.get("id") == "S0001" for s in suspects) or
        any(r.get("suspect_id") == "S0001" for r in rows)
    )
    assert has_raju, "S0001 (Raju K.) should appear in profile/rows/suspects"
    assert any(a["type"] == "show_network" for a in r["actions"])


def test_verify_claims_drops_unsupported_claims():
    kept = verify_claims([
        {"text": "unsupported"},
        {"text": "internal", "evidence": {"crime_id": "C1"}},
        {"text": "external", "source_url": "https://example.test/source"},
    ])

    assert [c["text"] for c in kept] == ["internal", "external"]


def test_grilling_clarify_on_missing_crime_type():
    r = post("what is the trend?")
    assert r["template_id"] == "CLARIFY"
    assert "crime type" in r["answer"]
    assert "query" in r["agents_used"]


def test_entity_carryover_multi_turn():
    sessions.clear("s-agentic-turn")
    # Turn 1: establish crime_type
    r1 = client.post("/api/chat", json={"text": "chain snatching cases", "session_id": "s-agentic-turn"}).json()
    assert r1["template_id"] == "T1"

    # Turn 2: ask for trend, should inherit 'chain snatching' and not ask to clarify
    r2 = client.post("/api/chat", json={"text": "show the monthly trend for those", "session_id": "s-agentic-turn"}).json()
    assert r2["template_id"] == "T3"
