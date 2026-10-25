"""
The new screens are reachable from where an officer already is: chat answers carry the next
screen (named for what it opens), social questions reach the district analysis, a money-trail
account exports, and a person's FIRs open as cases.
"""
import asyncio
import sqlite3

from fastapi.testclient import TestClient

from app.agents import social_answer
from app.agents.agentic_spine import _query_actions
from app.core.db_path import DB_PATH


def _ask(text):
    from app.agents.heuristics import heuristic_select
    from app.agents.query_agent import query_agent_run
    return asyncio.new_event_loop().run_until_complete(
        query_agent_run(text, lang="en", selector=heuristic_select, compose_llm=None))


class TestSocialQuestions:
    def test_recognised(self):
        assert social_answer.wants_social("Is alcohol linked to crimes against women?")
        assert social_answer.wants_social("which social factors go with violent crime")
        assert not social_answer.wants_social("theft cases in Mysuru City in 2025")
        assert not social_answer.wants_social("how many burglaries in Bengaluru City")

    def test_answered_with_numbers_and_the_limits(self):
        r = _ask("Is alcohol linked to crimes against women?")
        assert r["template_id"] == "SOCIAL" and r["rows"]
        assert "Spearman" in r["answer"] and "never a basis to target" in r["answer"]
        assert r["actions"][0]["payload"] == "/social"


class TestActions:
    def test_labels_name_the_screen_they_open(self):
        acts = _query_actions({"template_id": "T11", "params": {}})
        assert acts and acts[0]["payload"] == "/map" and "map" in acts[0]["label"].lower()
        assert _query_actions({"template_id": "T4", "params": {}})[0]["payload"] == "/antarBrain"

    def test_a_upi_answer_offers_the_money_trail_and_a_case(self):
        acts = _query_actions({"template_id": "T20", "params": {"key_type": "upi", "value": "pooja.swamy66@okicici"},
                               "citations": [{"fir": "1000", "id": "C16633"}]})
        payloads = [a["payload"] for a in acts]
        assert "/search?view=money&account=pooja.swamy66@okicici" in payloads and "/case/C16633" in payloads


def test_money_export_is_a_csv_ledger():
    from main import app
    from app.services import money_trail as m
    upi = m.overview(1)["top"][0]["account_id"]
    r = TestClient(app).get(f"/api/money/export?account={upi}", headers={"X-Role": "Inspector"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.splitlines()
    assert lines[0].startswith(f"account,{upi}") and any(l.startswith("txn_id,date_time,direction") for l in lines)
    assert TestClient(app).get(f"/api/money/export?account={upi}", headers={"X-Role": "Constable"}).status_code == 403


def test_a_persons_firs_open_as_cases():
    from main import app
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        sid = con.execute("SELECT suspect_id FROM crime_suspects GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1").fetchone()[0]
    finally:
        con.close()
    r = TestClient(app).get(f"/api/profile/{sid}/cases", headers={"X-Role": "Inspector"})
    d = r.json()
    assert r.status_code == 200 and d["count"] > 0
    assert all("_" not in (c["stage"] or "") for c in d["cases"])
    assert len({c["fir_id"] for c in d["cases"]}) == d["count"]


class TestOneFir:
    def test_every_register_id_shape_is_recognised(self):
        from app.agents import case_answer
        for q, fir in [("status of FIR C00026", "C00026"), ("show FIR K1026329", "K1026329"),
                       ("what happened in fir c00507", "C00507"), ("FIR SYN-c58fcac323e8 please", "SYN-c58fcac323e8")]:
            assert case_answer.fir_ids(q) == [fir]
        assert not case_answer.wants_case("what links FIR C00026 and FIR C00507")   # two: T29's question

    def test_a_question_about_one_fir_is_answered_from_that_case(self):
        r = _ask("status of FIR C273697")             # Amengad PS; was C00026 before the ids were made unique
        assert r["template_id"] == "CASE" and "Amengad PS" in r["answer"] and "Where it is now" in r["answer"]
        assert r["actions"][0] == {"type": "navigate", "payload": "/case/C273697", "label": "Open case timeline"}

    def test_a_closed_case_says_where_it_ended(self):
        r = _ask("show FIR K1026329")
        assert "Where it is now:** Investigation — Closed as undetected" in r["answer"]

    def test_an_unknown_id_says_so_instead_of_listing_other_cases(self):
        r = _ask("show FIR C99999999")
        assert r["template_id"] == "UNRESOLVED" and "No FIR C99999999" in r["answer"] and not r["rows"]


def test_a_persons_money_trail():
    from main import app
    from app.services import money_trail as m
    sid = next(a["suspect_id"] for a in m._snapshot()["accounts"].values() if a["suspect_id"])
    r = TestClient(app).get(f"/api/money/person/{sid}", headers={"X-Role": "Inspector"})
    d = r.json()
    assert r.status_code == 200 and d["accounts"] and d["accounts"][0]["how"] in ("held", "on_fir")
    assert TestClient(app).get(f"/api/money/person/{sid}", headers={"X-Role": "Constable"}).status_code == 403
