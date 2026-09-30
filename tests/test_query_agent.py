"""
Query Agent tests — full path (select → execute → compose) with a FAKE llm,
so the whole agent is verified WITHOUT Catalyst or a live LLM.
Run: python -m pytest tests/test_query_agent.py -v
"""

import asyncio
import json

from app.agents.query_agent import (
    query_agent_run, run_template, extract_citations,
    _slim_rows_for_compose, NO_RECORDS_EN, _QUERY_CACHE,
)


def fake_select(template_id: str, params: dict):
    """Return a fake select_llm that always picks the given template+params."""
    async def _llm(system, user, json_mode=True, max_tokens=256, temperature=0.1):
        return json.dumps({"template_id": template_id, "params": params, "answer_lang": "en"})
    return _llm


async def _echo_compose(system, user, json_mode=False, max_tokens=300, temperature=0.3):
    return "Composed answer from rows."


def test_full_path_suspect_lookup_yellappa():
    out = asyncio.run(query_agent_run(
        "find Yellappa", lang="en",
        select_llm=fake_select("T2", {"name_or_alias": "Yellappa"}),
        compose_llm=None,  # deterministic summary
    ))
    assert out["template_id"] == "T2"
    assert len(out["rows"]) >= 2  # Raju K. + Yellappa M.
    assert out["suggested_followups"]  # follow-ups returned


def test_no_records_rule():
    # WI-3 (self-healing RAG): an impossible-date filter no longer dead-ends with a bare
    # "No matching records". It heals to the closest RELATED rows (clearly labelled) or gives
    # an honest message — but it never fabricates and never presents related rows as an exact
    # match. The invariant "never fabricate" is preserved; the give-up sentence is not.
    out = asyncio.run(query_agent_run(
        "ndps in Mysuru-Devaraja from 1999", lang="en",
        select_llm=fake_select("T1", {"crime_types": ["ndps"], "zones": ["Mysuru-Devaraja"],
                                       "date_from": "1999-01-01", "date_to": "1999-12-31"}),
        compose_llm=None,
    ))
    assert out["answer"] and out["answer"] != NO_RECORDS_EN, "no bare give-up sentence"
    # If it healed to rows, they must be REAL database rows (grounded), never fabricated.
    assert all(r.get("crime_id") for r in out["rows"])


def test_none_template_returns_clarification():
    out = asyncio.run(query_agent_run(
        "what's the weather", lang="en",
        select_llm=fake_select("NONE", {}),
        compose_llm=None,
    ))
    assert out["template_id"] == "NONE"
    assert "rephrase" in out["answer"].lower()


def test_citations_present_for_crime_query():
    out = asyncio.run(query_agent_run(
        "chain snatching in Rajajinagar", lang="en",
        select_llm=fake_select("T1", {"crime_types": ["chain_snatching"], "zones": ["Rajajinagar"]}),
        compose_llm=_echo_compose,
    ))
    assert out["rows"]
    assert out["citations"]
    c = out["citations"][0]
    assert c["fir"] and "station" in c and "date" in c and "section" in c


def test_compose_llm_used_when_provided():
    _QUERY_CACHE.clear()  # prevent cross-test collision: prior test caches same prefix
    out = asyncio.run(query_agent_run(
        "chain snatching in Rajajinagar uniquely", lang="en",
        select_llm=fake_select("T1", {"crime_types": ["chain_snatching"], "zones": ["Rajajinagar"]}),
        compose_llm=_echo_compose,
    ))
    # Contract: compose_llm IS called when provided (rows are non-empty).
    # Guardrails may legitimately rewrite the LLM output, so we check the flag not the exact string.
    assert out["llm_answer"] is True, "compose_llm should have been called"
    assert out["rows"]  # grounded answer requires rows


def test_run_template_is_pure_no_llm():
    # The deterministic core needs no LLM at all.
    rows, cites = run_template("T1", {"crime_types": ["chain_snatching"], "zones": ["Rajajinagar"]})
    assert rows and cites
    assert all(r["crime_type"] == "chain_snatching" for r in rows)


def test_slim_rows_caps_count_and_drops_bulky_keys():
    """Compose input: capped to 3 rows; bulky/non-narrative keys dropped; useful fields kept."""
    rows = [{"fir_number": f"F{i}", "zone": "Rajajinagar", "phone_hash": "x",
             "lat": 12.9, "lon": 77.5} for i in range(20)]
    slim = _slim_rows_for_compose(rows)
    assert len(slim) == 3                       # capped (caller still passes the true N)
    assert all("phone_hash" not in r and "lat" not in r and "lon" not in r for r in slim)
    assert slim[0]["fir_number"] == "F0" and slim[0]["zone"] == "Rajajinagar"  # kept


def test_slim_rows_handles_empty_nondict_and_all_dropped():
    """Edge: empty → empty; non-dict passes through; an all-dropped row → {} (no crash)."""
    assert _slim_rows_for_compose([]) == []
    assert _slim_rows_for_compose(["raw", {"phone_hash": "x", "lat": 1}]) == ["raw", {}]
