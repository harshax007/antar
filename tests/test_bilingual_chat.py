"""
WI-5 — Bilingual EN ⇄ KN: when the toggle is Kannada, the ENTIRE chat output is Kannada
(answer + confidence label + suggested follow-ups), not just the answer text. Offline.
"""
import asyncio

from app.api.chat_stream import _answer_confidence
from app.agents.followup_agent import grounded_starters, grounded_followups
from app.agents.query_agent import query_agent_run
from app.agents.heuristics import heuristic_select


def _has_kn(s) -> bool:
    return any("ಀ" <= c <= "೿" for c in str(s))


def _run(q, lang):
    return asyncio.run(query_agent_run(q, lang=lang, selector=heuristic_select,
                                       select_llm=None, compose_llm=None))


def test_confidence_label_localized():
    assert not _has_kn(_answer_confidence(0.9, [1, 1, 1], [1, 1, 1], "en")["label"])
    assert _has_kn(_answer_confidence(0.9, [1, 1, 1], [1, 1, 1], "kn")["label"])


def test_starters_localized():
    en = grounded_starters(lang="en")
    kn = grounded_starters(lang="kn")
    assert (not en) or (not _has_kn(en[0]))
    assert (not kn) or _has_kn(kn[0])


def test_followups_localized():
    rows = [{"crime_type": "THEFT", "zone": "Rajajinagar", "fir_number": "F1"}]
    kn = grounded_followups("T3", {"crime_types": ["THEFT"], "zones": ["Rajajinagar"]},
                            rows, lang="kn")
    assert (not kn) or any(_has_kn(q) for q in kn)


def test_kn_query_returns_kn_answer_and_suggestions():
    r = _run("ಬೆಂಗಳೂರಿನಲ್ಲಿ ಸರಗಳ್ಳತನದ ಪ್ರವೃತ್ತಿ", "kn")
    assert _has_kn(r["answer"]), "KN toggle must yield a Kannada answer"
    if r.get("suggested_followups"):
        assert any(_has_kn(s) for s in r["suggested_followups"]), "suggestions should be Kannada"


def test_en_query_returns_en_answer():
    r = _run("chain snatching trend in Bengaluru", "en")
    assert not _has_kn(r["answer"])
