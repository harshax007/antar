"""
Victims linked to FIRs (scripts/seed_victims.py): one row per victim, matching each FIR's
recorded counts of men, women, boys and girls; queried by chat's victim template (T7) with the
crime and place asked about, and listed on the case page.
"""
import asyncio
import sqlite3

import pytest

from app.core.db_path import DB_PATH


def _con():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def _linked() -> bool:
    con = _con()
    try:
        return "fir_id" in {r[1] for r in con.execute("PRAGMA table_info(victims)")}
    finally:
        con.close()


pytestmark = pytest.mark.skipif(not _linked(), reason="victims not linked (scripts/seed_victims.py)")


def test_every_fir_has_exactly_the_victims_it_records():
    con = _con()
    try:
        bad = con.execute("""
            SELECT COUNT(*) FROM (SELECT fir_id, MAX(CAST(Male AS INT)) m, MAX(CAST(Female AS INT)) f,
                                         MAX(CAST(Boy AS INT)) b, MAX(CAST(Girl AS INT)) g FROM FIRs GROUP BY fir_id) f
            JOIN (SELECT fir_id, SUM(gender='M' AND age_group='adult') m, SUM(gender='F' AND age_group='adult') f,
                         SUM(gender='M' AND age_group='child') b, SUM(gender='F' AND age_group='child') g
                  FROM victims GROUP BY fir_id) v USING (fir_id)
            WHERE f.m + f.f + f.b + f.g BETWEEN 1 AND 25
              AND (v.m <> f.m OR v.f <> f.f OR v.b <> f.b OR v.g <> f.g)""").fetchone()[0]
    finally:
        con.close()
    assert bad == 0


def test_the_old_unlinked_rows_were_kept():
    con = _con()
    try:
        assert con.execute("SELECT COUNT(*) FROM victims_unlinked_20261024").fetchone()[0] > 0
    finally:
        con.close()


def _ask(text):
    from app.agents.heuristics import heuristic_select
    from app.agents.query_agent import query_agent_run
    return asyncio.new_event_loop().run_until_complete(
        query_agent_run(text, lang="en", selector=heuristic_select, compose_llm=None))


def test_victim_questions_apply_the_crime_and_the_place():
    r = _ask("age of theft victims in Mysuru City")
    assert r["template_id"] == "T7" and r["params"]["crime_types"] and r["params"]["zones"]
    assert "theft victims in mysuru city" in r["answer"].lower()


def test_relation_to_the_accused_reads_as_words():
    r = _ask("how were murder victims related to the accused")
    assert r["params"]["dimension"] == "relation" and "aged" not in r["answer"].split("\n")[0]


def test_the_case_page_lists_its_victims():
    from app.services import case_timeline as ct
    con = _con()
    try:
        fir, n = con.execute("SELECT fir_id, COUNT(*) FROM victims GROUP BY fir_id HAVING COUNT(*) = 2 LIMIT 1").fetchone()
    finally:
        con.close()
    assert len(ct.timeline(fir)["victims"]) == n
