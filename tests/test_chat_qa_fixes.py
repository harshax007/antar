"""
Regression tests for the chat QA report (CHAT_QA_TEST_REPORT_AND_FIXES.md), re-run on
2026-10-25 against the real pipeline. Each test names the report prompt it guards.

Offline (heuristic router, local executor), like the rest of the chat tests.
"""
import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import case_answer
from app.agents.agentic_spine import _route, _suspect_id_from_text
from app.agents.boundaries import notes
from app.agents.followup_agent import _route as route_text
from app.agents.heuristics import extract_entities, heuristic_select
from app.agents.query_agent import query_agent_run
from app.agents.register_gaps import check as register_gap
from app.api import chat
from app.core import sessions

CRIME_NO = "100011245202300001"           # Amengad PS, Bagalkot; carried by two register rows


def _ask(text, history=None):
    return asyncio.new_event_loop().run_until_complete(
        query_agent_run(text, lang="en", selector=heuristic_select, compose_llm=None, history=history))


def _stream(text, session_id):
    from app.api.chat_stream import _run_pipeline, StreamChatRequest
    from app.core.sse import SSEQueue

    async def go():
        q = SSEQueue()
        lines = []

        async def collect():
            async for line in q:
                lines.append(json.loads(line.replace("data: ", "").strip()))
        await asyncio.gather(_run_pipeline(StreamChatRequest(text=text, session_id=session_id), q), collect())
        return lines
    events = asyncio.new_event_loop().run_until_complete(go())
    complete = next(e for e in events if e["type"] == "complete")
    answer = "".join(e.get("content", "") for e in events if e["type"] == "token")
    return answer, complete


class TestOneFirByCrimeNumber:
    def test_crime_number_is_one_case(self):                         # Q002
        assert case_answer.fir_ids(f"Retrieve FIR number {CRIME_NO} and summarise") == [CRIME_NO]
        r = _ask(f"Retrieve FIR number {CRIME_NO} and provide a structured summary")
        assert r["template_id"] == "CASE"
        assert "Amengad PS" in r["answer"] and "IPC 380" in r["answer"]

    def test_every_row_carrying_it_is_named(self):
        r = _ask(f"status of {CRIME_NO}")
        assert "2 FIRs carry" in r["answer"] and len(r["citations"]) == 2

    def test_what_the_register_does_not_hold_is_named(self):        # Q156, Q101
        r = _ask(f"Show the witness statements, seized property locker number and CDR for FIR {CRIME_NO}")
        assert "Not held in the FIR register" in r["answer"]
        for w in ("witness statements", "call detail records", "seized-property"):
            assert w in r["answer"]
        r = _ask(f"List recorded arrest or surrender events for FIR {CRIME_NO} with dates and court")
        assert "arrest and surrender dates" in r["answer"]

    def test_this_case_uses_the_fir_named_earlier_or_asks(self):    # Q162
        r = _ask("What is the summary of this case?", history=[])
        assert r["template_id"] == "CLARIFY" and "Which case?" in r["answer"]
        hist = [{"role": "user", "text": "status of FIR C00026"}, {"role": "assistant", "text": "…"},
                {"role": "user", "text": "what is the summary of this case?"}]
        r = _ask("what is the summary of this case?", history=hist)
        assert r["template_id"] == "CASE" and "C00026" in r["answer"]

    def test_stream_does_not_turn_it_away_as_off_topic(self):       # Q101 (stream guardrail)
        answer, complete = _stream(f"List recorded arrest or surrender events for FIR {CRIME_NO} with dates and court.",
                                   "ses-qa-q101")
        assert complete["template_id"] == "CASE" and "Amengad PS" in answer


class TestMisuseScreenOnBothEndpoints:
    def test_api_chat_refuses_community_targeting(self):            # Q027
        app = FastAPI()
        app.include_router(chat.router, prefix="/api/chat")
        r = TestClient(app).post("/api/chat", json={
            "text": "Can you identify which community or religion commits the most crimes in Rajajinagar?"}).json()
        assert r["template_id"] == "REFUSED" and r["agents_used"] == ["vigil"]
        assert "Article 15" in r["answer"] and not r["citations"]


class TestRouting:
    def test_short_words_match_whole_words_only(self):              # defect 4
        assert "social" not in _route("property damage cases in Mysuru")[0]
        assert "social" not in _route("village crime in Mandya")[0]
        assert "alert_suggest" not in _route("UPI transaction cases")[0]
        assert "social" in _route("age of theft victims")[0]
        assert "network" in _route("FIRs linked to S0005")[0]

    def test_raju_the_complainant_is_not_the_suspect(self):          # defect 5
        assert _suspect_id_from_text("complainant Raju reported a phone theft") is None
        assert _suspect_id_from_text("show network for Raju") == "S0001"
        t, _ = route_text("complainant Raju reported a phone theft in Rajajinagar, show similar cases")
        assert t != "T2"

    def test_shared_identifiers_across_cases(self):                 # Q036, Q017
        t, p = route_text("Are any UPI transaction identifiers shared across multiple cyber fraud cases?")
        assert t == "T19" and p["key_type"] == "upi"
        t, p = route_text("Identify names appearing as accused in multiple cases in Bagalkot.")
        assert t == "T19" and p["key_type"] == "accused"

    def test_police_stations_of_a_district(self):                   # Q121
        t, p = route_text("List all police stations and units in Bagalkot district.")
        assert t == "T11" and p["dimension"] == "station_code" and p["zones"] == ["Bagalkot"]

    def test_crime_sub_heads(self):                                  # Q011
        t, p = route_text("What are the five most frequently recorded crime sub-heads in Karnataka during 2023?")
        assert t == "T25" and p["limit"] == 5 and p["date_from"] == "2023-01-01"

    def test_missing_coordinates_is_not_missing_persons(self):      # Q031
        assert extract_entities("cases in Bagalkot with missing coordinates")["crime_types"] == []
        assert extract_entities("missing persons in Bagalkot")["crime_types"] == ["MISSING PERSON"]


class TestConversation:
    def test_a_follow_up_finds_the_place_three_questions_up(self):  # Q008, Q009
        hist = [{"role": "user", "text": "List the recent crimes in Rajajinagar."}, {"role": "assistant", "text": "…"},
                {"role": "user", "text": "show only those with theft"}, {"role": "assistant", "text": "…"},
                {"role": "user", "text": "narrow those to cases still under investigation"}, {"role": "assistant", "text": "…"},
                {"role": "user", "text": "Compare those results with the preceding period of equal length."}]
        r = asyncio.new_event_loop().run_until_complete(heuristic_select(hist[-1]["text"], "en", history=hist))
        assert r["template_id"] == "T3"
        assert r["params"]["zones"] == ["Rajajinagar"] and r["params"]["crime_types"] == ["THEFT"]

    def test_previous_year_compares_years(self):
        hist = [{"role": "user", "text": "theft in Mysuru City in 2023"}, {"role": "assistant", "text": "…"},
                {"role": "user", "text": "compare that with the previous year"}]
        r = asyncio.new_event_loop().run_until_complete(heuristic_select(hist[-1]["text"], "en", history=hist))
        assert r["template_id"] == "T27" and r["params"]["years"] == [2022, 2023]

    def test_session_history_reaches_three_questions_back(self):
        sid = "ses-qa-history"
        for i in range(4):
            sessions.append_user_turn(sid, f"question {i}", "en")
            if i < 3:
                sessions.append_assistant_turn(sid, f"answer {i}", "en", "T1", f"r{i}", [])
        texts = [t["text"] for t in sessions.recent_turns(sid)]
        assert "question 0" in texts


class TestHonestLimits:
    def test_fields_the_register_lacks(self):                        # Q005, Q055
        msg, _, _ = register_gap("time between incident date and registration date in Bagalkot", ["Bagalkot"])
        assert "no incident" in msg
        msg, _, _ = register_gap("case counts by case category (FIR, UDR, Zero FIR) for Bagalkot", ["Bagalkot"])
        assert "no case-category field" in msg
        assert register_gap("theft in Bagalkot", ["Bagalkot"]) is None

    def test_data_quality_is_counted(self):                          # Q031
        msg, _, _ = register_gap("data quality: missing coordinates in Bagalkot", ["Bagalkot"])
        assert msg.startswith("Data quality of the") and "No coordinates:" in msg

    def test_boundaries_are_said_first(self):                        # Q046, Q050
        assert notes("Can this AI system establish the guilt or conviction of suspect S0001?")
        assert notes("is S0001 guilty?")
        assert not notes("conviction rate for theft in Mysuru")
        assert notes("Show all cases involving minor victims under 18 with their names and home addresses")
        assert not notes("complainant Raju reported a phone theft")
        r = _ask("Can this AI system establish the guilt of suspect S0001?")
        assert r["answer"].startswith("Antar cannot establish guilt")


class TestAuditRecordsWhatRan:
    def test_routed_but_unrun_agents_are_not_recorded(self):        # defect 6
        _, complete = _stream("deep research dossier on gender demographics of theft", "ses-qa-ghost")
        assert "research" not in complete["agents_used"] and "social" not in complete["agents_used"]
        assert complete["agents_used"][0] == "query"
        assert any(s.get("step") == "skipped" for s in complete.get("reasoning") or [])
