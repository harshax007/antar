"""
Absconding accused — the third dimension of the silently-dropped-filter bug.

"Absconding criminals in Indiranagar" used to lose the word "absconding" and list every
case in Indiranagar. These tests pin the contract that replaced it: the cue is read from
the question, the filter is a reviewed named predicate, templates that cannot carry it
refuse, and an empty result says WHICH kind of empty it is.
"""

import asyncio

import pytest

from app.agents.heuristics import heuristic_select
from app.agents.query_agent import (clear_query_cache, query_agent_run, run_template,
                                    wants_absconding)
from app.services.zcql_repo import build_spec, render_zcql

_OPEN = {"PENDING TRIAL", "UNDER INVESTIGATION", "TRANSFERRED - UNDER INVESTIGATION",
         "CHARGESHEETED", "CHARGE SHEETED"}


def _ask(q: str, lang: str = "en") -> dict:
    clear_query_cache()
    return asyncio.run(query_agent_run(q, lang=lang, selector=heuristic_select,
                                       select_llm=None, compose_llm=None))


@pytest.mark.parametrize("q", [
    "absconding criminals in Indiranagar", "accused still at large in Mysuru",
    "cases where the accused is not yet arrested", "fugitives this year",
    "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ತಲೆಮರೆಸಿಕೊಂಡ ಆರೋಪಿಗಳು", "ಬಂಧನವಾಗದ ಆರೋಪಿಗಳು",
])
def test_cue_detected(q):
    assert wants_absconding(q)


@pytest.mark.parametrize("q", ["most wanted suspects", "recent crimes in Mysuru City",
                               "arrest rate by district"])
def test_no_false_cue(q):
    assert not wants_absconding(q)


def test_predicate_is_a_reviewed_fragment_not_user_text():
    sql = render_zcql(build_spec("T11", {"arrest_status": "absconding"}))
    assert "accused > arrested" in sql and "PENDING TRIAL" in sql


def test_rows_really_are_absconding():
    rows, _ = run_template("T1", {"arrest_status": "absconding", "zones": ["Bengaluru City"],
                                  "limit": 50})
    assert rows, "expected absconding FIRs in Bengaluru City"
    for r in rows:
        assert r["accused"] > r["arrested"], r
        assert str(r["status"]).replace("_", " ").strip().upper() in _OPEN, r["status"]


def test_ranking_carries_the_filter():
    r = _ask("which district has the most absconding accused")
    assert r["params"].get("arrest_status") == "absconding"
    assert "still at large" in r["answer"]


def test_named_place_survives_relative_where():
    # "where" as a relative pronoun used to route to the district ranking and drop the place
    r = _ask("theft cases where accused not yet arrested in Mysuru City")
    assert r["template_id"] == "T1"
    assert any("Mysuru" in z for z in r["params"].get("zones", []))


def test_missing_arrest_data_is_not_reported_as_none_absconding():
    r = _ask("Show me the list of absconding criminals in Indiranagar")
    assert r["rows"] == []
    assert "aren't recorded" in r["answer"] or "not recorded" in r["answer"]


def test_unsupported_combination_refuses():
    r = _ask("absconding accused trend over time")
    assert r["template_id"] == "UNRESOLVED"
    assert r["rows"] == []


def test_unknown_arrest_status_refused():
    from app.agents.query_agent import unresolved_filters
    assert unresolved_filters({"arrest_status": "escaped-maybe"}) == {"arrest_status": ["escaped-maybe"]}
    assert unresolved_filters({"arrest_status": "absconding"}) == {}
