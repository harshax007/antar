"""
Antar — research graph node
===========================
`research` had no graph node: TRACE/RESEARCH routes folded into `query`, so the dossier
never ran in a chat turn and the adversarial layer was reachable only through direct API
calls. AGENTS.md flagged it as a GAP; this closes it.

Two things are under test:
  1. the node itself — anchor resolution, dossier, and the attached rebuttal
  2. the route actually reaching it, end to end through the compiled graph
"""

import asyncio

import pytest

from app.agents.graph import research_node, _research_anchor
from app.agents.supervisor import route_fn


def _state(text: str, **over) -> dict:
    return {"session_id": "t-research", "user_text": text, "lang": "en",
            "use_llm": False, "results": {}, "entities": {}, **over}


# ── anchor resolution ─────────────────────────────────────────────────────────
def test_known_suspect_name_resolves_to_a_suspect_id():
    assert _research_anchor(_state("deep research on Raju")) == "S0001"


def test_framing_words_are_stripped_to_recover_a_free_text_anchor():
    anchor = _research_anchor(_state("deep research on Ramanagara Traders"))
    assert anchor and "research" not in anchor.lower()
    assert "Ramanagara" in anchor


def test_zone_entity_is_used_as_an_anchor():
    anchor = _research_anchor(_state("dossier", entities={"zones": ["Whitefield"]}))
    assert anchor == "Whitefield"


@pytest.mark.parametrize("text", ["deep research", "dossier", "investigate", "research on",
                                  "", "   ", "?"])
def test_bare_request_yields_no_anchor(text):
    """run_research substring-matches the anchor against every suspect, so an empty
    anchor matches the whole table and produces a confident dossier about nobody.
    Returning None is the honest answer."""
    assert _research_anchor(_state(text)) is None


def test_too_short_anchor_is_rejected():
    assert _research_anchor(_state("research on ab")) is None


# ── the node ──────────────────────────────────────────────────────────────────
def test_node_without_an_anchor_is_an_honest_no_op():
    out = asyncio.run(research_node(_state("deep research")))
    assert "results" not in out, "must not fabricate a dossier with no subject"
    assert out["reasoning"], "a skipped dossier must still say why in the trail"
    assert "No researchable subject" in out["reasoning"][0]["detail"]


def test_node_produces_a_dossier_for_a_real_anchor():
    out = asyncio.run(research_node(_state("deep research on Raju")))
    d = out["results"]["research"]
    assert d["anchor"]
    assert d["known_facts"]
    assert out["visuals"]["research"] is d
    assert out["actions"][0]["type"] == "open_dossier"


def test_dossier_carries_its_own_rebuttal():
    """THE point of this node: inferred hypotheses never ship without the base-rate check."""
    out = asyncio.run(research_node(_state("deep research on Raju")))
    results = out["results"]
    if not results["research"].get("inferred_hypotheses"):
        pytest.skip("anchor produced no inferred hypotheses in the current dataset")

    challenge = results.get("advocate_agent")
    assert challenge, "a dossier with inferred hypotheses must carry its challenge"
    assert challenge["challenges"]
    assert sum(challenge["tally"].values()) == len(challenge["challenges"])
    assert any(s.get("agent") == "advocate_agent" for s in out["reasoning"])


def test_broken_adversary_still_yields_a_dossier_but_says_so(monkeypatch):
    """A dossier without its rebuttal is still useful, but the trail must not imply the
    check ran."""
    def _boom(*_a, **_k):
        raise RuntimeError("index corrupt")
    monkeypatch.setattr("app.agents.advocate_agent.challenge_dossier", _boom)

    out = asyncio.run(research_node(_state("deep research on Raju")))
    assert out["results"]["research"]
    assert "advocate_agent" not in out["results"]
    trail = [s["detail"] for s in out["reasoning"] if s.get("agent") == "advocate_agent"]
    assert trail and "unavailable" in trail[0]


def test_node_output_is_msgpack_safe():
    """Node returns are written to the LangGraph checkpointer, which cannot serialise
    numpy scalars — the same trap that bit forecast_node."""
    out = asyncio.run(research_node(_state("deep research on Raju")))

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        else:
            assert type(v).__module__ == "builtins" or v is None, \
                f"non-native {type(v)} would break the checkpointer"
    walk(out)


# ── routing ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("label", ["TRACE", "RESEARCH"])
def test_research_labels_now_reach_the_research_node(label):
    """Regression: both folded into `query`, so the agent never ran in a graph turn."""
    assert route_fn({"routes": [label]}) == ["research"]


def test_research_fans_out_alongside_query():
    assert route_fn({"routes": ["QUERY", "RESEARCH"]}) == ["query", "research"]


def test_heuristic_router_emits_research_for_a_research_question():
    from app.agents.agentic_spine import _route
    routes, _ = _route("deep research dossier on this case")
    assert "research" in routes


# ── end to end through the compiled graph ─────────────────────────────────────
def test_research_runs_end_to_end_in_a_chat_turn():
    from app.agents.agentic_spine import run_agentic_spine

    res = asyncio.run(run_agentic_spine("deep research on Raju", lang="en",
                                        session_id="t-research-e2e"))
    assert "research" in res["agents_used"], \
        "research did not execute in the graph — the route is not reaching the node"
    assert "Research Dossier" in res["answer"]


def test_challenged_hypotheses_are_marked_in_the_answer():
    """A collapsed hypothesis rendered as a plain [INFERRED] line is how an officer gets
    anchored on a bad lead. The verdict must travel with the claim, not below it."""
    from app.agents.agentic_spine import run_agentic_spine

    res = asyncio.run(run_agentic_spine("deep research on Raju", lang="en",
                                        session_id="t-research-marked"))
    answer = res["answer"]
    if "[INFERRED]" not in answer:
        pytest.skip("no inferred hypotheses surfaced for this anchor")

    assert "CHALLENGED" in answer or "Survives adversarial review" in answer
    for line in answer.splitlines():
        if line.startswith("    -> CHALLENGED"):
            idx = answer.splitlines().index(line)
            assert "[INFERRED]" in "\n".join(answer.splitlines()[max(0, idx - 3):idx]), \
                "a verdict must sit directly under the claim it challenges"
            break


def test_answer_text_is_ascii_safe_for_export():
    """Answers reach CSV/PDF export and Windows consoles; a decorative non-ASCII glyph
    in the challenge markup raised UnicodeEncodeError under cp1252."""
    from app.agents.agentic_spine import run_agentic_spine

    res = asyncio.run(run_agentic_spine("deep research on Raju", lang="en",
                                        session_id="t-research-ascii"))
    for marker in ("CHALLENGED", "Alternative:", "To disprove:"):
        for line in res["answer"].splitlines():
            if marker in line:
                line.encode("cp1252")   # raises if a stray glyph creeps back in


def test_manifest_declares_research_as_reachable():
    """AGENTS.md must no longer describe this agent as a GAP."""
    from app.agents import manifest

    a = manifest.reload().agents.get("research")
    assert a and a.reachable, "research should now have a graph node"
    assert a.graph_node == "research"
    assert a not in manifest.load().unreachable()
    assert "advocate_agent" in a.hosts
