"""
Every question offered on the empty chat screen (app/agents/officer_questions.py) is asked
through the real chat stream, in English and in Kannada, and must be answered from the
register by the path it was chosen for: not turned away, not asked back, not answered in
the other language. A suggestion the officer clicks has to work.

Offline (heuristic router, local executor), like the rest of the chat tests.
"""
import re

import pytest

from app.agents.officer_questions import OFFICER_QUESTIONS
from tests.test_chat_qa_fixes import _stream

# the path each one is answered by; a change here is a change in what the officer gets
EXPECT = {
    "How many FIRs were registered today?": {"T1"},
    "Is today busier than usual?": {"COMPARE"},
    "Are there any unusual spikes right now?": {"ALERTS"},
    "Is crime rising in Bengaluru City this week?": {"COMPARE"},
    "Which police stations registered the most FIRs this week?": {"T11"},
    "Which crime types rose the most in the last 6 months?": {"COMPARE"},
    "Top 5 crime types in Karnataka this year with their share": {"T13"},
    "Where should the night patrol focus in Bengaluru City?": {"T23"},
    "Top areas for chain snatching in Bengaluru City": {"T23"},
    "Which day of the week has the most theft in Bengaluru City?": {"T26"},
    "Which districts have the most theft?": {"T11"},
    "Top beats for theft in Bengaluru City": {"T23"},
    "Top beats for burglary in Bengaluru City": {"T23"},
    "Conviction rate for theft in Bengaluru City": {"T22"},
    "Which police stations recorded the most cybercrime in 2022?": {"T11"},
    "Retrieve FIR 100011245202300001 and summarise it": {"CASE"},
    "Timeline of FIR C00418": {"CASE"},
    "Find cases similar to FIR C00418": {"CASE"},
    "Cases under investigation for more than 90 days in Mysuru City": {"T24"},
    "Case status breakdown in Bengaluru City this year": {"T24", "T8"},
    "Which districts have the highest charge-sheet rate this year?": {"T22"},
    "Are any UPI IDs shared across multiple cyber fraud cases?": {"T19"},
    "Which vehicles appear in FIRs across 3 or more districts?": {"T19"},
    "Accused age groups in theft cases": {"T7"},
    "Victims of crimes against women by age group": {"T7"},
    "FIRs with missing location coordinates": {"UNRESOLVED"},
    "Theft by hour of day in Bengaluru City": {"UNRESOLVED"},
    "Monthly burglary in Mysuru City in 2025": {"T3"},
}
_KANNADA = re.compile(r"[ಀ-೿]")
_CASES = [(q["en"], q["en"], "en") for q in OFFICER_QUESTIONS] + \
         [(q["en"], q["kn"], "kn") for q in OFFICER_QUESTIONS if q.get("kn")]


def test_every_question_has_an_expected_path():
    assert {q["en"] for q in OFFICER_QUESTIONS} == set(EXPECT)


@pytest.mark.parametrize("en,text,lang", _CASES, ids=[f"{lang}:{en[:40]}" for en, _, lang in _CASES])
def test_officer_question_is_answered(en, text, lang):
    answer, complete = _stream(text, f"t-officer-{lang}-{abs(hash(text)) % 10**8}")
    tpl = complete["template_id"]
    assert tpl in EXPECT[en], f"{text!r} went to {tpl}"
    assert answer.strip() and "built for crime-data" not in answer and "ಮಾತ್ರ ಉತ್ತರಿಸುತ್ತೇನೆ" not in answer
    if lang == "kn":
        assert _KANNADA.search(answer[:200]), f"{text!r} was answered in English"
    else:
        assert not _KANNADA.search(answer[:200])


def test_similar_cases_are_listed_and_not_called_links():
    answer, _ = _stream("Find cases similar to FIR C00418", "t-officer-similar")
    assert "similar cases" in answer and "not a link" in answer


def test_a_small_conviction_rate_is_not_rounded_to_zero():
    # 89 convicted of 18,225 charge-sheeted is 0.5%; "0%" told the officer nobody was convicted
    answer, _ = _stream("Conviction rate for theft in Bengaluru City", "t-officer-conv")
    assert "**0%**" not in answer and "**0.5%**" in answer


def test_hour_of_day_is_refused_honestly_not_listed():
    answer, complete = _stream("Theft by hour of day in Bengaluru City", "t-officer-hour")
    assert "no time of day" in answer and not complete.get("citations")


def test_the_chat_page_offers_exactly_these_questions():
    # the empty screen falls back to STARTERS in page.jsx when the API is slow; it must be
    # the same list, or a fallback chip is one nobody tested
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "antar-frontend" / "app" / "(app)" / "antar" / "page.jsx").read_text(encoding="utf-8")
    body = src[src.index("const STARTERS = {"):]
    body = body[: body.index("};")]
    page = dict(re.findall(r"\b(en|kn): \[(.*?)\]", body, re.S))
    assert re.findall(r'"([^"]+)"', page["en"]) == [q["en"] for q in OFFICER_QUESTIONS]
    assert re.findall(r'"([^"]+)"', page["kn"]) == [q["kn"] or q["en"] for q in OFFICER_QUESTIONS]
