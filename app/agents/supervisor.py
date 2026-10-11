"""
Antar — Supervisor Agent
Intent classification + routing. One QuickML LLM call, JSON output only.
Routes to specialist agents; parallel fan-out when routes are independent.
"""

import json
import time
from app.agents.state import AgentState
from app.core.reasoning_logger import log_step

# ── System Prompt (paste-ready for Claude Code refinement) ─────────────────────
SUPERVISOR_SYSTEM_PROMPT = """You are the routing supervisor of Antar, a police intelligence system for Karnataka State Police.

Your ONLY job is to classify the user's message and decide which specialist agents to call.

Available agents:
- VAULT: structured crime data lookup (FIRs, suspects by name/zone/time, counts, trends)
- LINK: criminal network analysis, relationship mapping, who knows whom
- MOTIVE: individual suspect profile, risk assessment, MO analysis
- CORE: crime patterns, anomalies, hotspot prediction, trend alerts
- SENSE: sociological/demographic insights about crime patterns
- TRACE: deep research across known facts, derived metrics, inferred hypotheses, and unknown gaps (KUL / K/D/I/U dossier)
- EXPLAIN: the user wants to understand a previous answer ("why did you say that?", "explain")
- CHITCHAT: greetings, off-topic, out-of-scope requests

Rules:
1. Respond ONLY with valid JSON — no prose, no markdown, no explanation.
2. If multiple agents are needed AND they are independent (don't need each other's output), set parallel=true.
3. If confidence < 0.8, or if the intent is ambiguous, route to VAULT only and add a polite clarifying question in your entities. DO NOT assume intent or guess what the user meant.
4. CHITCHAT → do NOT route to any data agent; just flag it.
5. Extract entities carefully — suspect names, zones, crime types, date ranges.
6. CRITICAL RULE: Zero Assumptions. Do not assume the user is asking for general data if they asked for specific data. If they ask for something specific, only extract those exact entities.
"""

SUPERVISOR_USER_TEMPLATE = """
Conversation history (last 3 turns):
{LAST_3_TURNS}

Current user message (language: {DETECTED_LANG}):
{USER_TEXT}

Respond ONLY with this JSON structure:
{{
  "routes": ["VAULT"],
  "parallel": false,
  "confidence": 0.95,
  "entities": {{
    "suspect_names": [],
    "zones": [],
    "crime_types": [],
    "date_range": null
  }},
  "chitchat_response": null
}}
"""

# ── Routing function (used by LangGraph add_conditional_edges) ─────────────────
# TWO vocabularies reach route_fn and both have to work:
#
#  1. The LLM supervisor's semantic labels (VAULT / LINK / MOTIVE / …), from the prompt.
#  2. The OFFLINE heuristic path, which calls agentic_spine._route() and uppercases the
#     node-ish names it returns (QUERY / NETWORK / PROFILE / GEO / PATTERN / …).
#
# Only vocabulary 1 used to be mapped, and the lookup fell back to "query" for anything
# unrecognised. So on the offline path — which is EVERY turn whenever the LLM is
# unavailable — "NETWORK" and "PROFILE" silently became "query", and the network,
# profile, forecast and social agents never ran at all. The fan-out looked healthy in the
# reasoning trail (the supervisor logged the routes it wanted) while the graph executed a
# single node.
#
# BOTH vocabularies are now DECLARED IN AGENTS.md and generated from it, so a label can
# no longer exist in an emitter without existing here. The two dicts below are the
# fail-open fallback for a missing or malformed AGENTS.md: the request path must survive
# it (tests/test_agents_manifest.py is what fails loudly instead). Keep them in sync —
# the same test asserts they match the manifest.
_FALLBACK_GRAPH_NODES = {"query", "network", "profile", "forecast", "social", "research",
                         "brain", "osint", "synthesize"}
_FALLBACK_ROUTE_MAP = {
    # semantic labels (LLM supervisor)
    "VAULT": "query",
    "LINK": "network",
    "MOTIVE": "profile",
    "CORE": "forecast",
    "SENSE": "social",
    "TRACE": "research",
    "EXPLAIN": "query",        # Explain replays the reasoning log — routes via query
    "CHITCHAT": "synthesize",  # skip straight to synthesize for a polite redirect
    # node-name labels (offline heuristic path, agentic_spine._route)
    "QUERY": "query",
    "NETWORK": "network",
    "PROFILE": "profile",
    "SOCIAL": "social",
    # forecast_node already runs geo + prediction + pattern + alert_suggest internally
    "FORECAST": "forecast",
    "GEO": "forecast",
    "PATTERN": "forecast",
    "PREDICT": "forecast",
    "ALERT_SUGGEST": "forecast",
    "RESEARCH": "research",
    # Both have their own node now. They used to fold into "query", which does NOT run
    # them, so a BRAIN or OSINT route produced a trail claiming work that never happened.
    "OSINT": "osint",
    "BRAIN": "brain",
}


def _routing_tables() -> tuple[dict[str, str], set[str]]:
    """(route_map, dispatchable_nodes) from AGENTS.md, falling back to the literals above.

    Dispatchable excludes the entry node: route_fn must never return "supervisor", which
    would edge the supervisor back into itself.
    """
    try:
        from app.agents import manifest
        m = manifest.load()
        rm, nodes = m.route_map(), m.dispatchable_nodes()
        if rm and nodes:
            return rm, nodes
    except Exception:            # noqa: BLE001 — routing must never fail on a doc read
        pass
    return dict(_FALLBACK_ROUTE_MAP), set(_FALLBACK_GRAPH_NODES)


# Module-level view, kept for callers that read the table directly (and for tests).
_ROUTE_MAP, _GRAPH_NODES = _routing_tables()


def route_fn(state: AgentState) -> list[str]:
    """Map supervisor routes to LangGraph node names, deduped and order-preserving.

    An unrecognised label is COUNTED and logged rather than silently coerced to "query" —
    that silence is what hid the four-agents-never-ran bug. See manifest.unresolved_routes().
    """
    route_map, graph_nodes = _routing_tables()
    routes = state.get("routes") or ["VAULT"]
    out: list[str] = []
    for r in routes:
        label = str(r).strip().upper()
        node = route_map.get(label)
        if node is None:
            try:
                from app.agents import manifest
                manifest.note_unresolved_route(label)
            except Exception:    # noqa: BLE001
                pass
            continue
        if node in graph_nodes and node not in out:
            out.append(node)
    # CHITCHAT goes straight to synthesize and must not be paired with data agents.
    if "synthesize" in out:
        return ["synthesize"]
    return out or ["query"]


# ── Supervisor Node ────────────────────────────────────────────────────────────
async def supervisor_node(state: AgentState) -> dict:
    """
    LangGraph node: classify intent, set routes + entities.
    One LLM call → JSON → validated → state updated.
    """
    t0 = time.time()

    # ── HEURISTIC FAST-PATH ──
    import re
    user_text = state["user_text"]
    if re.search(r'\b\d{4}-[A-Z]{3}-[\w-]+\b', user_text) or re.search(r'\bKA-\d{2}-[A-Z]{1,2}-\d{2,4}\b', user_text):
        parsed = {
            "routes": ["VAULT"],
            "parallel": False,
            "confidence": 1.0,
            "entities": {}
        }
    else:
        # Build prompt
        last_turns = _format_history(state.get("results", {}))
        prompt = SUPERVISOR_USER_TEMPLATE.format(
            LAST_3_TURNS=last_turns,
            DETECTED_LANG=state.get("lang", "en"),
            USER_TEXT=state["user_text"],
        )

        # Call local LLM intent classifier (Phase 2) or fallback to deterministic heuristic
        use_llm = state.get("use_llm", False)
        if use_llm:
            from app.tools.local_intent_classifier import classify_intent
            prompt_id = classify_intent(state["user_text"])
            
            # Map Phase 2 prompt IDs back to standard spine routes
            if prompt_id.startswith("inv_"):
                routes = ["LINK", "VAULT"]
            elif prompt_id.startswith("intel_"):
                routes = ["CORE"]
            elif prompt_id.startswith("cmp_"):
                routes = ["VAULT"]
            elif prompt_id.startswith("pub_"):
                routes = ["VAULT"]
            else:
                routes = ["VAULT"]
                
            parsed = {
                "routes": routes,
                "parallel": len(routes) > 1,
                "confidence": 0.95,
                "entities": {"prompt_id": prompt_id}
            }
        else:
            from app.agents.agentic_spine import _route
            r_list, r_conf = _route(state["user_text"])
            parsed = {
                "routes": [r.upper() for r in r_list],
                "parallel": len(r_list) > 1,
                "confidence": r_conf,
                "entities": {}
            }

    # Fallback: confidence < 0.8 → VAULT only
    if parsed.get("confidence", 1.0) < 0.8:
        parsed["routes"] = ["VAULT"]
        parsed["parallel"] = False

    ms = int((time.time() - t0) * 1000)
    log_step(state["session_id"], "supervisor", "classify", state["user_text"][:80], str(parsed["routes"]), ms)

    return {
        "routes": parsed.get("routes", ["VAULT"]),
        "parallel": parsed.get("parallel", False),
        "confidence": parsed.get("confidence", 0.7),
        "entities": parsed.get("entities", {}),
        # Reset the accumulating channels so this turn does not inherit the last
        # one's agent results, citations, brain hits or visuals from the
        # per-session checkpoint (see state.py).
        "actions": [{"CLEAR": True}],
        "results": {"__CLEAR__": True},
        "visuals": {"__CLEAR__": True},
        "citations": [{"__CLEAR__": True}],
        "brain_hits": [{"__CLEAR__": True}],
        # reasoning is reset the same way. It used to be `state.get("reasoning") + [...]`,
        # which the append reducer then added to the checkpointed list a second time:
        # the trail doubled every turn, and an 11-turn thread wrote a 612 MB trace row.
        "reasoning": [{"__CLEAR__": True}, {
            "agent": "supervisor",
            "step": "intent_classification",
            "routes": parsed.get("routes"),
            "confidence": parsed.get("confidence"),
            "ms": ms,
        }],
    }


def _format_history(results: dict) -> str:
    """Format last 3 agent results as context for supervisor."""
    if not results:
        return "(no prior turns in this session)"
    # Simple: join the last few final answers
    answers = [v.get("answer", "") for v in results.values() if v.get("answer")]
    return "\n".join(answers[-3:]) or "(no prior answers)"


def _parse_supervisor_json(raw: str, fallback_text: str) -> dict:
    """Parse supervisor JSON with repair. Returns valid dict or safe fallback."""
    # Strip markdown code blocks if present
    cleaned = raw.strip().strip("```json").strip("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try extracting the first {...} block
        import re
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    # Hard fallback
    return {
        "routes": ["VAULT"],
        "parallel": False,
        "confidence": 0.5,
        "entities": {"suspect_names": [], "zones": [], "crime_types": [], "date_range": None},
        "actions": [{"CLEAR": True}],
    }
