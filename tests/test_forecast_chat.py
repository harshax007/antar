"""Map forecasting, Phase 6 — forecast questions in chat.

Golden questions from docs/MAP_FORECASTING_PLAN.md §6, answered through the real chat
path. Before this, every one of them was routed to the monthly TREND template: a question
about next week answered with last year's months.
"""
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.antar_identity import present
from app.forecast import chat as C


# ── detection ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("q", [
    "where should I patrol next week in Mysuru",
    "theft forecast Bengaluru City next 4 weeks",
    "predict burglary next month in Belagavi City",
    "ಮುಂದಿನ ವಾರ ಮೈಸೂರಿನಲ್ಲಿ ಕಳ್ಳತನ ಎಲ್ಲಿ",
    "ಅಪರಾಧ ಮುನ್ಸೂಚನೆ",
    "forecast for Indiranagar",
])
def test_forecast_questions_are_recognised(q):
    assert C.wants_forecast(q)


@pytest.mark.parametrize("q", [
    "theft trend in Mysuru",
    "how many thefts last week",
    "most crimes?",
    "which districts had the most predicted hotspots last month",
    "show chain snatching in Rajajinagar",
])
def test_other_questions_are_left_alone(q):
    assert not C.wants_forecast(q)


def test_horizon():
    assert C.horizon_of("where next week") == 7
    assert C.horizon_of("theft forecast next 4 weeks") == 28
    assert C.horizon_of("predict next month") == 28
    assert C.horizon_of("ಮುಂದಿನ ತಿಂಗಳು ಮುನ್ಸೂಚನೆ") == 28


def test_categories():
    assert C.categories_in("theft forecast") == ["PROPERTY"]
    assert C.categories_in("chain snatching next week") == ["PROPERTY"]
    assert C.categories_in("ಮುಂದಿನ ವಾರ ಕಳ್ಳತನ") == ["PROPERTY"]
    assert C.categories_in("where should I patrol next week") == []
    assert C.categories_in("attempt to murder next week") == ["VIOLENT"]
    assert set(C.categories_in("theft and murder next week")) == {"PROPERTY", "MURDER"}


# ── places (real registry) ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def con():
    import sqlite3
    from app.core.db_path import DB_PATH
    c = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name = 'forecast_output'").fetchone():
        pytest.skip("forecasts not computed yet (backend startup does it)")
    yield c
    c.close()


def test_places(con):
    s = C.resolve_scope(con, "where should I patrol next week in Mysuru")
    assert s.kind == "district" and s.districts == ["Mysuru City", "Mysuru Dist"]
    s = C.resolve_scope(con, "theft forecast Bengaluru City next 4 weeks")
    assert s.districts == ["Bengaluru City"]                  # not + Bengaluru Dist
    s = C.resolve_scope(con, "ಮುಂದಿನ ವಾರ ಮೈಸೂರಿನಲ್ಲಿ ಕಳ್ಳತನ ಎಲ್ಲಿ")
    assert s.districts == ["Mysuru City", "Mysuru Dist"]
    s = C.resolve_scope(con, "forecast theft in Mysore next week")      # old name
    assert "Mysuru City" in s.districts
    s = C.resolve_scope(con, "forecast for Indiranagar")
    assert s.kind == "station" and s.station == "Indiranagar PS"
    assert C.resolve_scope(con, "crime forecast for Karnataka next week").kind == "state"
    assert C.resolve_scope(con, "where will crime happen next week").kind == "state"


def test_an_unknown_place_is_refused_not_widened(con):
    from app.forecast.service import Refusal
    with pytest.raises(Refusal) as e:
        C.resolve_scope(con, "forecast theft in Atlantis next week")
    assert e.value.field == "place" and "Atlantis" in e.value.message


# ── answers, through the real chat path ──────────────────────────────────────

async def _ask(q, lang="en"):
    from app.agents.query_agent import clear_query_cache, query_agent_run
    from app.agents.heuristics import heuristic_select
    clear_query_cache()
    return await query_agent_run(q, lang=lang, selector=heuristic_select, compose_llm=None,
                                 select_llm=None)


@pytest.mark.anyio
async def test_patrol_question_in_mysuru(con):
    r = await _ask("where should I patrol next week in Mysuru")
    assert r["template_id"] == "FORECAST"
    p = present(r["answer"], r, "en")
    assert p["evidence_class"] == "I" and p["kind"] == "answer" and p["violations"] == []
    bottom = p["sections"]["bottom_line"]
    assert "Mysuru City and Mysuru Dist" in bottom and "likely" in bottom and "very likely" in bottom
    assert p["sections"]["limits"], "limits (reported FIRs, dates not times) must be stated"
    assert r["rows"] and all(row["evidence_class"] == "I" for row in r["rows"])
    assert any(a["payload"] == "/map" for a in r["actions"])


@pytest.mark.anyio
async def test_theft_28_days_bengaluru_city(con):
    r = await _ask("theft forecast Bengaluru City next 4 weeks")
    assert r["template_id"] == "FORECAST"
    assert r["params"]["horizon_days"] == 28 and r["params"]["category"] == "PROPERTY"
    p = present(r["answer"], r, "en")
    assert "next 28 days" in p["sections"]["bottom_line"] and p["evidence_class"] == "I"


@pytest.mark.anyio
async def test_kannada(con):
    r = await _ask("ಮುಂದಿನ ವಾರ ಮೈಸೂರಿನಲ್ಲಿ ಕಳ್ಳತನ ಎಲ್ಲಿ", "kn")
    assert r["template_id"] == "FORECAST"
    p = present(r["answer"], r, "kn")
    assert p["evidence_class"] == "I" and p["violations"] == []
    assert "ಸಂಭವನೀಯ" in p["text"] and "FIR" in p["text"]        # FIR stays in English
    assert "|" not in p["text"]                                   # no markdown tables in Kannada


@pytest.mark.anyio
async def test_thin_history_is_a_gap_not_a_quiet_place(con):
    r = await _ask("forecast for Indiranagar")
    p = present(r["answer"], r, "en")
    if r["rows"] and any(row["history"] == "ok" for row in r["rows"]):
        pytest.skip("Indiranagar PS has usable history at this as-of")
    assert p["evidence_class"] == "U" and p["kind"] == "gap"
    assert "not the same as a quiet place" in p["text"]


@pytest.mark.anyio
@pytest.mark.parametrize("q,field", [
    ("forecast theft in Atlantis next week", "place"),
    ("predict theft and murder next week in Mysuru", "category"),
])
async def test_refusals(con, q, field):
    r = await _ask(q)
    assert r["template_id"] == "UNRESOLVED" and not r["rows"]
    p = present(r["answer"], r, "en")
    assert p["kind"] == "refusal" and p["violations"] == []
    assert "different question" in r["answer"]


@pytest.mark.anyio
async def test_stream_answers_with_the_forecast_and_nothing_unmeasured(con):
    from main import app
    events = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        async with c.stream("POST", "/api/chat/stream",
                            json={"text": "where should I patrol next week in Mysuru", "lang": "en"}) as resp:
            buf = ""
            async for chunk in resp.aiter_text():
                buf += chunk
    for line in buf.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    done = [e for e in events if e["type"] == "complete"][0]
    assert done["template_id"] == "FORECAST"
    assert not {"predict", "pattern", "alert_suggest"} & set(done["agents_used"])
    text = "".join(e["content"] for e in events if e["type"] == "token")
    assert "likely" in text and "Risk:" not in text
    acts = [a for e in events if e["type"] == "actions" for a in e["data"]]
    assert any(a.get("payload") == "/map" and a.get("params", {}).get("forecast_unit") for a in acts)
