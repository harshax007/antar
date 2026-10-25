"""
Antar — LangGraph Agent State Schema
The spine of the multi-agent system. Build this first.
All agents read/write AgentState. The Supervisor node routes; specialist agents process.
"""

from typing import TypedDict, Literal, Optional, Any, Annotated
import operator
from langgraph.graph import StateGraph, END
# MemorySaver is no longer imported here — app/agents/checkpoint_store.py owns the choice
# of backend (SQLite by default, MemorySaver under ANTAR_CHECKPOINT=memory).

# The graph is checkpointed per session (thread_id = session_id) so that a follow-up turn
# can see the previous one. That also means the accumulating channels below are NOT reset
# between turns: `results` merges, `citations`/`brain_hits` append. Turn 2 in a session
# therefore inherited turn 1's agent results, so `agents_used` grew monotonically and a
# plain "hello" eventually reported nine agents and replayed the previous turn's visuals.
#
# `actions` already solved this with a CLEAR sentinel emitted by supervisor_node. The same
# sentinel now works for the other accumulating channels, so every turn starts clean while
# the checkpointer still provides continuity for anything the nodes read explicitly.
CLEAR = "__CLEAR__"


def merge_dicts(a: dict, b: dict) -> dict:
    if b and b.get(CLEAR):
        return {k: v for k, v in b.items() if k != CLEAR}
    if not a: return b
    if not b: return a
    return {**a, **b}


def reduce_list(a: list | None, b: list | None) -> list:
    """Append, unless the incoming update opens with the CLEAR sentinel."""
    if a is None: a = []
    if b is None: b = []
    if b and isinstance(b[0], dict) and b[0].get(CLEAR):
        return b[1:]
    return a + b


def reduce_actions(a: list[dict] | None, b: list[dict] | None) -> list[dict]:
    if a is None: a = []
    if b is None: b = []
    # historical sentinel key kept working alongside the shared one
    if b and (b[0].get("CLEAR") or b[0].get(CLEAR)):
        return b[1:]
    return a + b


class AgentState(TypedDict):
    """
    Shared state that flows through the LangGraph StateGraph.
    Every node reads from and writes to this.
    """
    # ── Input ────────────────────────────────────────────────────────────────
    session_id: str
    user_text: str                      # original user message
    lang: Literal["en", "kn"]          # detected language
    audio_tier: Optional[int]           # 1=Zia, 2=WebSpeech, 3=Bhashini, 4=typed
    use_llm: bool                       # if False, use offline heuristic path

    # ── Supervisor outputs ────────────────────────────────────────────────────
    routes: list[str]                   # e.g. ["QUERY", "NETWORK"]
    parallel: bool                      # if True → fan-out to all routes in parallel
    confidence: float                   # supervisor routing confidence
    entities: dict[str, Any]            # {suspect_names, zones, crime_types, date_range}

    # ── Agent results (keyed by agent name) ──────────────────────────────────
    results: Annotated[dict[str, dict], merge_dicts]            # e.g. {"query": {...}, "network": {...}}

    # ── Cross-cutting outputs ─────────────────────────────────────────────────
    citations: Annotated[list[dict], reduce_list]              # [{fir, station, date, ipc}]
    brain_hits: Annotated[list[dict], reduce_list]             # Second Brain cross-case links surfaced
    reasoning: Annotated[list[dict], reduce_list]              # [{agent, step, input_digest, output_digest, ms}]
    actions: Annotated[list[dict], reduce_actions]              # UI actions to dispatch (cleared via {"CLEAR": True})

    # ── Final output ─────────────────────────────────────────────────────────
    final_answer: Optional[str]         # composed NL answer in user's language
    visuals: Annotated[dict[str, Any], merge_dicts]             # {chart_data, graph_ref, map_ref, profile_data}
    reasoning_id: Optional[str]         # NoSQL doc ID for the Explain capability


def build_graph(
    supervisor_node,
    query_node,
    network_node,
    profile_node,
    forecast_node,
    social_node,
    research_node,
    brain_node,
    synthesize_node,
    route_fn,
) -> Any:
    """
    Builds and compiles the LangGraph StateGraph.
    Called once at startup; result stored as app_graph singleton.

    Graph topology:
        supervisor → [query | network | profile | forecast | social | research
                      | brain]
                   → synthesize → END
    Fan-out is parallel when supervisor sets parallel=True (independent routes).

    The node list here is the authority AGENTS.md declares against, and
    tests/test_agents_manifest.py fails the build if the two disagree — so a node added
    here without a manifest entry (or vice versa) cannot ship.
    """
    g = StateGraph(AgentState)

    # Add all nodes
    g.add_node("supervisor", supervisor_node)
    g.add_node("query", query_node)
    g.add_node("network", network_node)
    g.add_node("profile", profile_node)
    g.add_node("forecast", forecast_node)
    g.add_node("social", social_node)
    g.add_node("research", research_node)
    # brain used to have NO node: its routes folded into `query`, which does not run it, so
    # the reasoning trail showed a fan-out that never happened (AGENTS.md, "Known gaps").
    # osint deliberately has none: it is out of the FIR path and runs only when the OSINT
    # Workbench calls /api/osint/*, never from a chat question.
    g.add_node("brain", brain_node)
    g.add_node("synthesize", synthesize_node)

    # Entry point
    g.set_entry_point("supervisor")

    # Supervisor → conditional fan-out to routed agents
    g.add_conditional_edges("supervisor", route_fn)

    # All specialist agents → synthesize → END
    for name in ["query", "network", "profile", "forecast", "social", "research",
                 "brain"]:
        g.add_edge(name, "synthesize")
    g.add_edge("synthesize", END)

    # The case file. MemorySaver kept a session alive only until the process did — a
    # restart or redeploy silently dropped every officer's thread, which AGENTS.md listed
    # as a known gap. build_checkpointer() returns a SQLite-backed saver by default and
    # the old in-process one under ANTAR_CHECKPOINT=memory. thread_id is still session_id.
    from app.agents.checkpoint_store import build_checkpointer
    return g.compile(checkpointer=build_checkpointer())
