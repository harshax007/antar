"""
WI-3 — Self-Healing RAG tests.

Covers: GLM-4/deterministic intent parsing, the relational SQL miner (progressive
relaxation + no unconstrained dump), the hybrid BM25 index, and the self-heal scenarios
end-to-end through query_agent_run. All OFFLINE (conftest forces the heuristic path).

Scenario map (per the WI-3 spec):
  Sc A — Direct hit: a query that resolves first try must NOT invoke self-heal.
  repair — structured heal (reroute + SQL miner) fixes empty/misrouted queries.
  Sc B/C — semantic gap / fragment: the dense + BM25 hybrid machinery (tested at unit level;
           end-to-end Sc B needs a populated Brain index which unit tests don't build).
  dead-end — a truly unanswerable query gets an honest message, never a bare NO_RECORDS
             and never an arbitrary row dump.
"""
import asyncio

from app.agents.intent_parser import parse_intent
from app.agents.self_heal import self_heal, intent_to_template
from app.services.sql_miner import mine, mine_until_hit, build_sql
from app.agents.query_agent import query_agent_run
from app.agents.heuristics import heuristic_select

NO_RECORDS = "No matching records found in the database."


def _run(q, lang="en"):
    return asyncio.run(query_agent_run(
        q, lang=lang, selector=heuristic_select, select_llm=None, compose_llm=None))


# ── Intent parser ──────────────────────────────────────────────────────────────

def test_intent_extracts_type_status_period():
    it = asyncio.run(parse_intent(
        "Show me all unsolved burglary cases from last month", "en"))
    assert "BURGLARY" in it.crime_types
    assert it.period == "last_month"
    assert it.statuses, "unsolved should map to open statuses"


def test_intent_unsolved_does_not_include_solved():
    """Regression: word-boundary scan so 'solved' does not fire inside 'unsolved'."""
    it = asyncio.run(parse_intent("unsolved theft cases", "en"))
    assert "Convicted" not in it.statuses
    assert "ChargeSheeted" not in it.statuses
    assert "Under Investigation" in it.statuses


def test_intent_suspect_id_routes_to_t9():
    it = asyncio.run(parse_intent("What crimes is S0005 linked to?", "en"))
    assert it.suspect_id == "S0005"
    assert it.intent_type == "suspect_crimes"
    assert intent_to_template(it) == ("T9", {"suspect_id": "S0005"})


def test_intent_kannada_chain_snatching():
    it = asyncio.run(parse_intent("ಸರಗಳ್ಳತನದ ಪ್ರವೃತ್ತಿ ತೋರಿಸಿ", "kn"))
    assert "CHAIN_SNATCHING" in it.crime_types
    assert it.intent_type == "trend"


# ── Relational SQL miner ────────────────────────────────────────────────────────

def test_miner_finds_unsolved_burglary():
    it = asyncio.run(parse_intent(
        "unsolved burglary cases from last month", "en"))
    rows, relax, _ = mine_until_hit(it)
    assert rows, "miner should find at least one row for a real type+status"


def test_miner_no_unconstrained_dump():
    """An intent with no constraints must NOT return arbitrary rows."""
    from app.agents.intent_parser import Intent
    empty = Intent(raw="", lang="en")
    assert mine(empty, relax_level=0) == []
    sql, _ = build_sql(empty, relax_level=0)
    assert " WHERE " not in sql


# ── Hybrid BM25 index (Sc C mechanism) ──────────────────────────────────────────

def test_hybrid_index_returns_fragment_matches():
    from app.services.hybrid_index import get_index, tokenize
    assert tokenize("THEFT Rajajinagar") == ["theft", "rajajinagar"]
    hits = get_index().search("theft rajajinagar", k=5, use_dense=False)
    assert hits and all("crime_id" in h for h in hits)


# ── Scenario A — direct hit must NOT self-heal ──────────────────────────────────

def test_direct_hit_does_not_self_heal():
    r = _run("Which zones have the most chain snatching?")
    heal = [s for s in r.get("reasoning", []) if s.get("step") == "self_heal"]
    assert r["rows"] and not heal


# ── Structured repair — empty/misrouted queries recover ─────────────────────────

def test_heals_trend_in_bengaluru():
    r = _run("Show the chain-snatching trend in Bengaluru over the last three months")
    assert r["rows"], "trend should heal to non-empty rows"
    assert NO_RECORDS not in r["answer"]


def test_heals_suspect_link_without_false_not_found():
    r = _run("What crimes is S0005 linked to?")
    assert r["rows"]
    # entity is satisfied by the T9/id-join reroute → no misleading "no record" lead
    assert r.get("entity_not_found") is None


def test_heals_unsolved_burglary():
    r = _run("Show me all unsolved burglary cases from last month in my jurisdiction")
    assert r["rows"]
    assert NO_RECORDS not in r["answer"]


# ── Self-heal unit: dead-end is honest, not a dump ──────────────────────────────

def test_dead_end_is_honest_not_dump():
    res = asyncio.run(self_heal(
        "xyzzy unicorn teleportation glorp", "en", "T1", {}, [], select_llm=None))
    assert res.scenario == "dead_end"
    assert res.rows == []
    assert res.dead_end_message and NO_RECORDS not in res.dead_end_message


def test_self_heal_repairs_structured_query():
    res = asyncio.run(self_heal(
        "unsolved burglary last month", "en", "T1", {}, [], select_llm=None))
    assert res.scenario == "repaired_direct"
    assert res.rows
