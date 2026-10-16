"""Every question the chat offers (empty-state starters and role chips) must be answered
from the real KSP record: rows found, the question it asked actually applied, and no count
of demonstration records. Read-only against the registry."""
import asyncio
import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[1] / "antar-frontend" / "app" / "(app)" / "antar" / "page.jsx"


def _offered() -> list[tuple[str, str]]:
    src = PAGE.read_text(encoding="utf-8")
    out = []
    for block in ("const ROLE_QUESTIONS = {", "const STARTERS = {"):
        body = src[src.index(block): src.index("};", src.index(block))]
        for lang, items in re.findall(r"\b(en|kn): \[(.*?)\]", body, re.S):
            out += [(lang, q) for q in re.findall(r'"([^"]+)"', items)]
    return sorted(set(out))


OFFERED = _offered()


def test_the_page_offers_something():
    assert len(OFFERED) >= 15


@pytest.mark.parametrize("lang,question", OFFERED)
def test_each_offered_question_is_answered_from_the_real_record(lang, question):
    from app.agents import heuristics as H
    from app.agents.answer_writer import write_answer
    from app.agents.query_agent import run_template
    r = asyncio.run(H.heuristic_select(question, lang, {}))
    tid, p = r["template_id"], r.get("params") or {}
    assert tid not in ("CLARIFY", "NONE"), r
    rows, _ = run_template(tid, dict(p))
    assert rows, f"no rows for {question!r}"
    text = write_answer(rows, tid, lang, p, question) or ""
    assert "demonstration records" not in text and "ಪ್ರಾತ್ಯಕ್ಷಿಕೆ" not in text
    assert "broader question" not in text


def test_no_seeded_names_are_offered():
    seeded = ("KA-02-M-2093", "Ravi", "Raju", "Bheema", "Jayanagar", "Rajajinagar", "Indiranagar",
              "Bengaluru North", "South Bengaluru", "vehicle theft", "chain", "ಜಯನಗರ", "ರಾಜಾಜಿನಗರ")
    for _lang, q in OFFERED:
        assert not any(s.lower() in q.lower() for s in seeded), q


def test_the_server_starters_have_rows():
    from app.agents.followup_agent import grounded_starters
    assert len(grounded_starters(max_out=4)) >= 3
