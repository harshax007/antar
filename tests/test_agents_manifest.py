"""
Antar — AGENTS.md drift tests
=============================
These are the teeth behind the manifest. AGENTS.md is only worth writing if it cannot
quietly stop being true, and this module is what enforces that.

What it guards:
  1. The document parses and is structurally valid.
  2. Every graph node in the compiled LangGraph is claimed by an agent, and every
     graph_node an agent claims exists in the compiled graph. (The original bug was a
     route pointing at a node that was not registered.)
  3. Every route label any emitter can produce is declared. This is the direct
     regression test for "NETWORK silently became query".
  4. The generated route map does not regress against the hand-written fallback.
  5. The orchestrator fleet matches the manifest.
"""

import pytest

from app.agents import manifest
from app.agents.state import build_graph


@pytest.fixture(scope="module")
def man():
    return manifest.reload()


# ── 1. structural validity ────────────────────────────────────────────────────
def test_manifest_loads_without_errors(man):
    assert man.agents, "AGENTS.md produced no agents — is the file present and parseable?"
    assert not man.errors, "AGENTS.md is structurally invalid:\n  " + "\n  ".join(man.errors)


def test_every_agent_declares_a_real_module(man):
    """`module` must be path::entrypoint so the file stays navigable."""
    for a in man.agents.values():
        assert "::" in a.module, f"{a.agent}: module '{a.module}' is not 'path::entrypoint'"
        path = a.module.split("::", 1)[0]
        assert path.endswith(".py"), f"{a.agent}: module path '{path}' is not a .py file"
        assert (manifest.MANIFEST_PATH.parent / path).exists(), \
            f"{a.agent}: declared module '{path}' does not exist on disk"


# ── 2. manifest vs. compiled graph ────────────────────────────────────────────
def _compiled_nodes() -> set[str]:
    """Node names in the real compiled graph, built with stand-ins for the node fns.

    Importing app.agents.graph would drag in the whole agent stack; build_graph is the
    actual topology definition, so building it with no-op nodes tests the same structure.
    """
    async def _noop(state):                       # pragma: no cover - never invoked
        return {}

    # Every `*_node` parameter gets a stand-in, discovered from the signature rather than
    # listed here. Adding a node to build_graph then only requires an AGENTS.md entry —
    # this helper does not also need editing, so the drift test cannot be defeated by
    # forgetting to update the test itself.
    import inspect
    kwargs = {name: _noop for name in inspect.signature(build_graph).parameters
              if name.endswith("_node")}
    g = build_graph(route_fn=lambda s: ["query"], **kwargs)
    return {n for n in g.get_graph().nodes if n not in ("__start__", "__end__")}


def test_manifest_topology_matches_compiled_graph(man):
    assert man.graph_nodes() == _compiled_nodes(), (
        "AGENTS.md topology.nodes disagrees with state.build_graph().\n"
        f"  manifest: {sorted(man.graph_nodes())}\n"
        f"  compiled: {sorted(_compiled_nodes())}"
    )


def test_every_graph_node_is_claimed_by_an_agent(man):
    claimed = {a.graph_node for a in man.agents.values() if a.graph_node}
    orphans = _compiled_nodes() - claimed
    assert not orphans, (
        f"graph nodes with no agent in AGENTS.md: {sorted(orphans)} — "
        "a node nobody documents is a node nobody maintains"
    )


def test_no_route_resolves_to_a_nonexistent_node(man):
    """The exact shape of the original bug: a route pointing at an unregistered node."""
    nodes = _compiled_nodes()
    for label, node in man.route_map().items():
        assert node in nodes, f"route '{label}' resolves to '{node}', which is not a graph node"


# ── 3. every emitted route label is declared ──────────────────────────────────
def test_heuristic_router_emits_only_declared_labels(man):
    """agentic_spine._route() is the offline path — EVERY turn when the LLM is down.

    Its output is uppercased and fed to route_fn, so any agent name it can emit must be
    a declared route label. This is the regression test for the four-agents-never-ran bug.
    """
    from app.agents.agentic_spine import _route

    probes = [
        "show me the network of associates",          # network
        "who is Raju, profile him",                   # profile
        "any alerts or patrol suggestions?",          # alert_suggest
        "predict crime next month",                   # predict
        "victim gender demographic breakdown",        # social
        "where are the theft hotspots",               # geo
        "what patterns or clusters exist",            # pattern
        "osint background check open web",            # osint
        "deep research dossier on this case",         # research
        "second brain cross-case overlap",            # network/profile/brain
        "how many thefts in Bengaluru",               # query
        "hello",                                      # bare
    ]
    declared = set(man.route_map())
    undeclared: dict[str, str] = {}
    for p in probes:
        for agent in _route(p)[0]:
            label = agent.upper()
            if label not in declared:
                undeclared[label] = p
    assert not undeclared, (
        "_route() emits labels that AGENTS.md does not declare — these would be dropped "
        f"silently at route_fn: {undeclared}"
    )


def test_mode_primary_agents_are_all_declared(man):
    """agent_modes injects primary_agents into the route list for /think /connect /anticipate."""
    from app.agents.agent_modes import MODES

    declared_ids = set(man.alias_map())
    for mode_name, spec in MODES.items():
        for agent in spec["primary_agents"] + spec["secondary_agents"]:
            assert agent.lower() in declared_ids, (
                f"mode '{mode_name}' names agent '{agent}', which is not in AGENTS.md "
                "(add it, or add it as an alias of the agent it means)"
            )


def test_slash_command_forced_agents_are_declared(man):
    from app.agents.heuristics import SLASH_COMMANDS

    declared_ids = set(man.alias_map())
    for cmd, spec in SLASH_COMMANDS.items():
        for agent in spec["forces"]:
            assert agent.lower() in declared_ids, (
                f"/{cmd} forces agent '{agent}', which is not declared in AGENTS.md"
            )


def test_supervisor_prompt_labels_are_declared(man):
    """The LLM supervisor is told it may emit these; all of them must route somewhere."""
    from app.agents.supervisor import SUPERVISOR_SYSTEM_PROMPT

    declared = set(man.route_map())
    for label in ("VAULT", "LINK", "MOTIVE", "CORE", "SENSE", "TRACE", "EXPLAIN", "CHITCHAT"):
        assert label in SUPERVISOR_SYSTEM_PROMPT, \
            f"'{label}' vanished from the supervisor prompt — update AGENTS.md too"
        assert label in declared, \
            f"supervisor prompt offers '{label}' but AGENTS.md does not declare it"


# ── 4. no regression against the hand-written fallback ────────────────────────
def test_generated_route_map_covers_the_fallback(man):
    """The manifest may ADD labels; it must never drop or repoint an existing one."""
    from app.agents.supervisor import _FALLBACK_ROUTE_MAP

    generated = man.route_map()
    for label, node in _FALLBACK_ROUTE_MAP.items():
        assert label in generated, f"manifest lost route '{label}' present in the fallback"
        assert generated[label] == node, (
            f"manifest repoints '{label}': fallback -> {node}, manifest -> {generated[label]}"
        )


def test_fallback_graph_nodes_match_manifest(man):
    """The fallback set is what route_fn may RETURN, so it excludes the entry node."""
    from app.agents.supervisor import _FALLBACK_GRAPH_NODES

    assert _FALLBACK_GRAPH_NODES == man.dispatchable_nodes(), \
        "supervisor._FALLBACK_GRAPH_NODES has drifted from AGENTS.md topology"


def test_entry_node_is_never_dispatchable(man):
    """Returning the entry node from a conditional edge loops the supervisor into itself."""
    entry = man.topology.get("entry")
    assert entry, "AGENTS.md topology declares no entry node"
    assert entry not in man.dispatchable_nodes()
    assert entry not in man.route_map().values(), \
        f"a route resolves to the entry node '{entry}' — that is a routing loop"


def test_route_fn_still_routes_the_core_vocabulary():
    """End-to-end through the real route_fn, with the manifest in play."""
    from app.agents.supervisor import route_fn

    assert route_fn({"routes": ["NETWORK"]}) == ["network"]
    assert route_fn({"routes": ["PROFILE"]}) == ["profile"]
    assert route_fn({"routes": ["LINK", "MOTIVE"]}) == ["network", "profile"]
    assert route_fn({"routes": ["GEO"]}) == ["forecast"]
    assert route_fn({"routes": ["CHITCHAT", "VAULT"]}) == ["synthesize"]
    assert route_fn({"routes": []}) == ["query"]


def test_previously_dropped_labels_now_route():
    """PREDICTION (agent_modes) and ALERTS (orchestrator fleet) used to be dropped."""
    from app.agents.supervisor import route_fn

    assert route_fn({"routes": ["PREDICTION"]}) == ["forecast"]
    assert route_fn({"routes": ["ALERTS"]}) == ["forecast"]


def test_unknown_label_is_counted_not_silently_coerced():
    """The failure mode this whole manifest exists to prevent: silence."""
    from app.agents.supervisor import route_fn

    manifest.reset_unresolved()
    out = route_fn({"routes": ["TOTALLY_MADE_UP_AGENT"]})
    assert out == ["query"], "must still degrade safely to query"
    assert "TOTALLY_MADE_UP_AGENT" in manifest.unresolved_routes(), \
        "an unknown route label must be recorded, not silently coerced"
    manifest.reset_unresolved()


# ── 5. orchestrator fleet agrees with the manifest ────────────────────────────
def test_orchestrator_fleet_matches_manifest(man):
    from app.core import orchestrator

    orchestrator._registry.clear()
    orchestrator._state.clear()
    orchestrator.register_default_fleet()

    registered = set(orchestrator._registry)
    for a in man.fleet():
        assert a.agent in registered, f"manifest agent '{a.agent}' was not registered"
        assert orchestrator._registry[a.agent].role == a.role
        assert orchestrator._registry[a.agent].timeout_s == a.timeout_s


def test_fallback_fleet_does_not_name_undeclared_agents(man):
    """If AGENTS.md is unreadable we fall back to a literal list — it must agree too."""
    from app.core.orchestrator import _FALLBACK_FLEET

    declared = set(man.alias_map())
    for name, _role, _timeout in _FALLBACK_FLEET:
        assert name in declared, \
            f"orchestrator fallback registers '{name}', which AGENTS.md does not declare"


# ── documentation honesty ─────────────────────────────────────────────────────
def test_unreachable_agents_are_declared_as_such(man):
    """An agent with no graph node must SAY so, and must name where its routes land."""
    for a in man.unreachable():
        assert a.unrouted_fallback, \
            f"{a.agent} has routes but no graph node and no declared unrouted_fallback"
        assert "GAP" in a.notes.upper(), (
            f"{a.agent} is routed but never executed in a graph turn — its notes must say "
            "so, otherwise AGENTS.md is quietly misleading"
        )


def test_hitl_agents_are_explicit(man):
    """Any agent with a real-world effect must carry hitl and a degraded-path story."""
    for a in man.agents.values():
        if a.hitl:
            assert a.degraded, f"{a.agent} requires HITL but declares no degraded behaviour"
