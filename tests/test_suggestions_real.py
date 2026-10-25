"""Every role chip the chat offers must be answered
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
    # the empty-screen STARTERS are the officer questions (today, this week ...), asked
    # through the real stream in both languages by tests/test_officer_questions.py
    for block in ("const ROLE_QUESTIONS = {",):
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


def test_no_offered_question_headlines_a_raw_count():
    """2016-2022 is a partial extract: its counts are low, its rankings and shares hold."""
    for _lang, q in OFFERED:
        # "ಎಷ್ಟು" alone also asks for a share ("what share reached chargesheet"); a count of cases is "ಎಷ್ಟು … ಪ್ರಕರಣ".
        assert not q.lower().startswith("how many") and not ("ಎಷ್ಟು" in q and "ಪ್ರಕರಣ" in q), q


@pytest.mark.parametrize("text", ["2022ರಲ್ಲಿ ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಹೆಚ್ಚು ಕೊಲೆಗಳು ದಾಖಲಾಗಿವೆ?", "2022ರ IPC/BNS ವಿರುದ್ಧ SLL ವಿಭಜನೆ?"])
def test_a_year_fused_to_a_kannada_suffix_is_applied(text):
    from app.agents.heuristics import extract_entities
    e = extract_entities(text)
    assert e.get("date_from") == "2022-01-01" and e.get("date_to") == "2022-12-31", e


BANK = Path(__file__).resolve().parents[1] / "intelligent.db"


@pytest.mark.skipif(not BANK.exists(), reason="intelligent.db is not in git")
def test_the_documented_bank_names_no_2023_and_no_raw_count():
    import sqlite3
    con = sqlite3.connect(f"file:{BANK}?mode=ro", uri=True)
    rows = con.execute("SELECT question_en, question_kn FROM question_bank").fetchall()
    con.close()
    for en, kn in rows:
        assert "2023" not in (en or "") + (kn or "")
    assert not any((en or "").lower().startswith(("statewide murders", "cybercrime firs in")) for en, _ in rows)


# ── the four documented questions that used to answer something else ─────────
def _answer(question, lang="en"):
    from app.agents import heuristics as H
    from app.agents.answer_writer import write_answer
    from app.agents.query_agent import run_template
    r = asyncio.run(H.heuristic_select(question, lang, {}))
    rows, _ = run_template(r["template_id"], dict(r["params"]))
    return r["template_id"], r["params"], write_answer(rows, r["template_id"], lang, r["params"], question) or ""


@pytest.mark.parametrize("lang,q", [("en", "Cognizable FIRs registered in Karnataka in 2022?"),
                                    ("kn", "2022ರಲ್ಲಿ ಕರ್ನಾಟಕದಲ್ಲಿ ದಾಖಲಾದ ಸಂಜ್ಞೇಯ FIRಗಳು?")])
def test_cognizable_is_answered_as_a_share_beside_the_official_total(lang, q):
    tid, _p, text = _answer(q, lang)
    assert tid == "T16" and "195,170" in text
    assert ("Cognizable:" in text or "ಸಂಜ್ಞೇಯ:" in text) and "%" in text.split("\n")[1]


@pytest.mark.parametrize("lang,q", [("en", "Top 10 stations by FIR volume 2022?"),
                                    ("kn", "2022ರಲ್ಲಿ FIR ಪ್ರಮಾಣದ ಪ್ರಕಾರ ಟಾಪ್ 10 ಠಾಣೆಗಳು?")])
def test_stations_by_fir_volume_rank_all_crime(lang, q):
    tid, p, text = _answer(q, lang)
    assert tid == "T11" and p["dimension"] == "station_code" and not p.get("crime_types")
    assert p["date_from"] == "2022-01-01" and text


@pytest.mark.parametrize("lang,q,word", [("en", "Peak month for cybercrime in 2022?", "peaked in"),
                                         ("kn", "2022ರಲ್ಲಿ ಸೈಬರ್ ಅಪರಾಧದ ಗರಿಷ್ಠ ತಿಂಗಳು?", "ಗರಿಷ್ಠ")])
def test_peak_month_names_a_month_of_that_year(lang, q, word):
    tid, p, text = _answer(q, lang)
    first = text.split("\n")[0]
    assert tid == "T3" and p["date_from"] == "2022-01-01" and word in first and "2022" in first
    assert text.count("\n") == 12                       # the lead and the twelve months


@pytest.mark.parametrize("lang,q", [("en", "Share of 2022 FIRs that reached chargesheet?"),
                                    ("kn", "2022ರ FIRಗಳಲ್ಲಿ ಚಾರ್ಜ್\u200cಶೀಟ್ ತಲುಪಿದ ಪಾಲು?")])
def test_the_chargesheet_question_gets_the_chargesheet_rate_in_both_languages(lang, q):
    tid, _p, text = _answer(q, lang)
    assert tid == "T22" and "89%" in text.split("\n")[0]


# ── questions by year, 2016-2026 (components/YearQuestions.jsx) ──────────────
YQ = Path(__file__).resolve().parents[1] / "antar-frontend" / "components" / "YearQuestions.jsx"


def _year_questions():
    src = YQ.read_text(encoding="utf-8")
    years = [int(y) for y in re.findall(r"\b(20[12]\d)\b", src[src.index("export const YEARS"): src.index("];", src.index("export const YEARS"))])]
    body = src[src.index("export const TEMPLATES"): src.index("};", src.index("export const TEMPLATES"))]
    out = []
    for lang, items in re.findall(r"\b(en|kn): \[(.*?)\]", body, re.S):
        for t in re.findall(r'"([^"]+)"', items):
            out += [(lang, y, t.replace("{y}", str(y))) for y in years]
    return years, out


YEARS, YEAR_QS = _year_questions()


def test_every_year_from_2016_to_2026_is_offered():
    assert YEARS == list(range(2016, 2027)) and len(YEAR_QS) == 11 * 10


@pytest.mark.parametrize("lang,year,question", YEAR_QS)
def test_each_year_question_is_answered_for_that_year(lang, year, question):
    from app.agents import heuristics as H
    from app.agents.query_agent import run_template
    r = asyncio.run(H.heuristic_select(question, lang, {}))
    tid, p = r["template_id"], r.get("params") or {}
    assert tid not in ("CLARIFY", "NONE") and str(p.get("date_from", "")).startswith(str(year)), (tid, p)
    rows, _ = run_template(tid, dict(p))
    assert rows, question
    assert not question.lower().startswith("how many")


# ── answers about a period after the real record say they are demonstration data ──
@pytest.mark.parametrize("lang,q,label", [
    ("en", "Which districts had the most theft in 2026?", "these are demonstration records"),
    ("en", "Peak month for cybercrime in 2025?", "these are demonstration records"),
    ("kn", "2025 ರಲ್ಲಿ ಜಿಲ್ಲಾವಾರು ಶಿಕ್ಷೆ ಪ್ರಮಾಣ", "ಪ್ರಾತ್ಯಕ್ಷಿಕೆ ದಾಖಲೆಗಳು"),
    ("en", "IPC/BNS vs SLL split for 2024?", "rows after 10 Mar 2024 are demonstration records"),
])
def test_a_seeded_period_is_labelled(lang, q, label):
    _tid, _p, text = _answer(q, lang)
    assert label in text.split("\n")[1], text[:300]


@pytest.mark.parametrize("q", ["Which districts had the most theft in 2022?", "IPC/BNS vs SLL split for 2019?"])
def test_a_real_record_period_is_not(q):
    _tid, _p, text = _answer(q)
    assert "demonstration" not in text


def test_the_label_stays_beside_the_bottom_line():
    from app.core.antar_identity import present
    _tid, _p, text = _answer("Which districts had the most theft in 2026?")
    assert "demonstration records" in present(text, {}, "en")["sections"]["context"][0]


def test_a_model_worded_answer_about_2026_gets_the_label_too():
    from app.agents.query_agent import _with_seeded_note
    p = {"date_from": "2026-01-01", "date_to": "2026-12-31"}
    out = _with_seeded_note("Bengaluru City leads with 598 theft cases.", p, "T11", "en")
    assert out.endswith("The real KSP record ends on 10 Mar 2024.")
    assert _with_seeded_note("x", {"date_from": "2022-01-01", "date_to": "2022-12-31"}, "T11", "en") == "x"
