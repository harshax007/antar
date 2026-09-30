"""
Antar's constitution, as tests (docs/ANTAR_CONSTITUTION.md).

The identity is not a prompt Antar may or may not follow — every answer passes through
app/core/antar_identity.present(). These tests fail the build when a real answer, from the
real pipeline, breaks the voice, loses the template, or leaks a protected identity.
"""

import asyncio
import re

import pytest

from app.agents.heuristics import heuristic_select
from app.agents.query_agent import COMPOSE_SYSTEM, clear_query_cache, query_agent_run
from app.core.antar_identity import LAWS, present, protect, system_prompt, validate

# A spread of real officer questions across every answer kind, both languages.
QUESTIONS = [
    ("which districts have the most kidnapping and abduction", "en", "ranking"),
    ("theft trend over time", "en", "trend"),
    ("how many murders in 2023", "en", "count"),
    ("absconding accused in Bengaluru City", "en", "list"),
    ("Show me the list of absconding criminals in Indiranagar", "en", "gap"),
    ("how many unicorn blockchain crimes", "en", "any"),
    ("ಕಳ್ಳತನ ಎಲ್ಲಿ ಹೆಚ್ಚು", "kn", "ranking"),
    ("ನಿನ್ನೆ ಕಳ್ಳತನ ಎಷ್ಟು", "kn", "count"),
]


def _answer(q: str, lang: str) -> tuple[dict, dict]:
    clear_query_cache()
    r = asyncio.run(query_agent_run(q, lang=lang, selector=heuristic_select,
                                    select_llm=None, compose_llm=None))
    return r, present(r["answer"], r, lang)


@pytest.mark.parametrize("q,lang,kind", QUESTIONS)
def test_every_answer_keeps_the_voice(q, lang, kind):
    _, p = _answer(q, lang)
    assert p["violations"] == [], f"{q!r}: {p['violations']}"


@pytest.mark.parametrize("q,lang,kind", QUESTIONS)
def test_every_answer_has_a_bottom_line(q, lang, kind):
    _, p = _answer(q, lang)
    bl = p["sections"]["bottom_line"]
    assert bl and len(bl) > 12, f"{q!r}: no usable bottom line"


@pytest.mark.parametrize("q,lang,kind", QUESTIONS)
def test_no_internal_tags_reach_the_officer(q, lang, kind):
    _, p = _answer(q, lang)
    assert not re.search(r"\[(VERIFIED|COMPUTED|INFERRED|GAP)\]", p["text"]), p["text"][:200]


@pytest.mark.parametrize("q,lang,kind", QUESTIONS)
def test_evidence_class_is_declared(q, lang, kind):
    _, p = _answer(q, lang)
    if p["kind"] == "refusal":
        return                                   # a refusal carries no evidence class
    assert p["evidence_class"] in ("K", "D", "I", "U"), (q, p["evidence_class"])


def test_classes_match_what_was_claimed():
    _, rank = _answer("which districts have the most kidnapping and abduction", "en")
    assert rank["evidence_class"] == "D"         # a ranking with shares is calculated
    _, gap = _answer("Show me the list of absconding criminals in Indiranagar", "en")
    assert gap["evidence_class"] == "U" and gap["kind"] == "gap"


def test_ranking_names_the_runners_up():
    _, p = _answer("which districts have the most kidnapping and abduction", "en")
    assert "followed by" in p["sections"]["bottom_line"]


def test_context_is_a_sentence_not_a_code_word():
    _, p = _answer("how many murders in 2023", "en")
    _, q = _answer("which districts have the most kidnapping and abduction", "en")
    for c in p["sections"]["context"] + q["sections"]["context"]:
        assert not re.search(r"\b(UPWARD|DOWNWARD|STABLE)\b", c), c


def test_trend_does_not_say_its_direction_twice():
    _, p = _answer("theft trend over time", "en")
    body = p["text"].lower()
    assert body.count("falling") + body.count("rising") + body.count("steady") <= 1, body[:300]


# ── the validator itself ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad,rule", [
    ("Sir, there are 39 thefts in Mysuru.", "salutation"),
    ("I found 39 thefts in Mysuru.", "first_person_bottom_line"),
    ("There are approximately 39 thefts.", "approximate_number"),
    ("It is worth noting that theft is up.", "filler:it is worth noting"),
    ("Theft is skyrocketing in Mysuru.", "sensational:skyrocket"),
    ("39 thefts in Mysuru!", "exclamation"),
])
def test_validator_catches(bad, rule):
    assert rule in validate(bad)


def test_limits_may_use_first_person():
    assert validate("I can't see victim ages on these FIRs.") == []


def test_salutation_is_removed_on_the_way_out():
    assert not present("Sir, 39 thefts are on record in Mysuru.")["text"].lower().startswith("sir")


# ── Law 4: protected identities ──────────────────────────────────────────────────

@pytest.mark.parametrize("line", [
    "FIR 12 — POCSO, Mysuru. Victim: Asha Kumari, aged 14.",
    "FIR 12 — Rape, Mysuru. VICTIM - Asha Kumari",
    "FIR 12 — Molestation. survivor Asha Kumari reported at 21:00",
    "FIR 12 — Sexual assault. Complainant: Asha K. Rao",
])
def test_victim_named_in_a_sexual_offence_is_redacted(line):
    out = protect(line)
    assert "Asha" not in out and "identity protected" in out, out


def test_victim_redaction_does_not_touch_other_offences():
    line = "FIR 12 — Theft, Mysuru. Complainant: Ravi Kumar."
    assert protect(line) == line


# ── one identity, everywhere ─────────────────────────────────────────────────────

def test_every_llm_prompt_is_built_from_the_constitution():
    for name, _ in LAWS:
        assert name.upper() in COMPOSE_SYSTEM
    assert "elite" not in COMPOSE_SYSTEM.lower()
    src = open("app/agents/graph.py", encoding="utf-8").read()
    assert "elite AI police intelligence assistant" not in src
    assert "_antar_prompt(\"synthesis\"" in src


def test_kannada_prompt_keeps_legal_terms_in_english():
    kn = system_prompt("answer", "kn")
    assert "FIR" in kn and "BNS" in kn and "POCSO" in kn
