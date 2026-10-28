"""
Antar — LangGraph Topology Setup
Wraps existing standalone agents into LangGraph nodes.
"""

from __future__ import annotations

import asyncio
import re
import sys

from app.agents.state import AgentState, build_graph
from app.agents.supervisor import supervisor_node, route_fn
from app.agents.agentic_spine import (
    _suspect_id_from_query, _suspect_id_from_text, _query_actions,
    verify_claims, _claims
)
from app.agents.query_agent import query_agent_run
from app.agents.heuristics import heuristic_select
from app.services.quickml import quickml_generate, llm_for, model_for
from app.core.security import public_message as _public_message
from app.core import sessions


def _to_native(obj):
    """Recursively convert numpy scalars/arrays to plain Python types.

    Everything a node returns is written to the LangGraph checkpointer, which serialises
    with msgpack and raises `TypeError: Type is not msgpack serializable: numpy.float64`
    on anything numpy-typed. The forecast branch computes z-scores, Gi* statistics and
    conformal bands in numpy, so its results tripped this on every turn that reached it.
    That went unnoticed because the routing table never actually dispatched to the
    forecast node (see supervisor.route_fn) — fixing the routing surfaced it immediately.
    Coercing here keeps the agents free to use numpy internally, and also makes the same
    payloads safe for the JSON response the API returns.
    """
    # numpy is optional at runtime; only import it if it is already loaded.
    np = sys.modules.get("numpy")
    if np is not None:
        if isinstance(obj, np.generic):          # np.float64, np.int64, np.bool_, …
            return obj.item()
        if isinstance(obj, np.ndarray):
            return [_to_native(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    return obj

# ── One orchestration contract for both paths ────────────────────────────────
# `chat_stream` ran every agent through `orchestrator.run_agent()` — timeout, retries,
# circuit breaker, honest degraded reason. The graph called the same agents DIRECTLY:
# eight orchestrated calls on one path, zero on the other. So the timeouts AGENTS.md
# declares per agent (geo 8s, network 15s, alert_suggest 6s) were real on /api/chat/stream
# and fiction on /api/chat, where a hung agent hung the whole turn with nothing to stop it.
#
# That is the four-places-can-disagree problem the manifest exists to kill, in its most
# consequential form: not a label out of step, but a protection that only half the product
# actually has.
#
# `_run` closes it. Same registry, same declared limits, same degraded contract, and the
# reasoning trail says which agent failed and why instead of the step vanishing.


async def _run(name: str, factory, *, native: bool = True):
    """Run one agent under the orchestrator. Returns (ok, result, reason)."""
    from app.core import orchestrator
    ok, res, meta = await orchestrator.run_agent(name, factory)
    if not ok:
        return False, None, (meta or {}).get("reason") or "unavailable"
    return True, (_to_native(res) if native else res), None


def _degraded(agent: str, reason: str) -> dict:
    """A failed agent yields a visible, honest step — never a silent gap.

    LangGraph also rejects a bare empty update, so a no-op has to carry something; making
    that something the reason is free honesty.
    """
    return {"reasoning": [{"agent": agent, "step": "degraded",
                           "detail": f"{agent} unavailable: {reason}"}]}


def _sync(fn, *args):
    """Wrap a blocking agent so the orchestrator can time it out on a worker thread."""
    async def _call():
        return await asyncio.to_thread(fn, *args)
    return _call


async def query_node(state: AgentState) -> dict:
    use_llm = state.get("use_llm", False)
    query = await query_agent_run(
        state["user_text"],
        lang=state.get("lang", "en"),
        session_id=state.get("session_id", ""),
        history=sessions.recent_turns(state.get("session_id", "")),
        select_llm=llm_for("chat") if use_llm else None,
        compose_llm=llm_for("chat") if use_llm else None,
        selector=None if use_llm else heuristic_select,
    )
    
    actions = _query_actions(query)
    
    return {
        "results": {"query": query},
        "actions": actions,
        "reasoning": query.get("reasoning", [])
    }

async def network_node(state: AgentState) -> dict:
    query = state.get("results", {}).get("query", {})
    suspect_id = _suspect_id_from_query(query) or _suspect_id_from_text(state["user_text"])

    if not suspect_id:
        # LangGraph rejects a bare {} update — return a valid no-op instead.
        return {"reasoning": []}

    from app.agents.network_agent import build_network
    ok, graph, reason = await _run("network", _sync(build_network, suspect_id))
    if not ok:
        return _degraded("network", reason)

    return {
        "results": {"network": graph, "second_brain": {"hits": graph.get("brain_links", []), "banner": graph.get("brain_banner")}},
        "visuals": {"graph": graph},
        "brain_hits": graph.get("brain_links", []),
        # only offer "Show" when a real network exists (2+ connections)
        "actions": ([{"type": "show_network", "label": "Show network", "params": {"suspect_id": suspect_id}}]
                    if len(graph.get("edges", [])) >= 2 else [])
    }

async def profile_node(state: AgentState) -> dict:
    query = state.get("results", {}).get("query", {})
    suspect_id = _suspect_id_from_query(query) or _suspect_id_from_text(state["user_text"])

    if not suspect_id:
        # LangGraph rejects a bare {} update — return a valid no-op instead.
        return {"reasoning": []}

    from app.agents.profile_agent import compute_profile
    ok, prof, reason = await _run("profile", _sync(compute_profile, suspect_id))
    if not ok:
        return _degraded("profile", reason)
    if not prof:
        return {"reasoning": []}
        
    return {
        "results": {"profile": prof},
        "visuals": {"profile": prof},
        "actions": [{"type": "open_profile", "label": "Open profile", "params": {"suspect_id": suspect_id}}]
    }

async def forecast_node(state: AgentState) -> dict:
    # Actually mapped to 'alert_suggest' and 'predict' and 'geo' and 'pattern' in our old spine.
    # The supervisor maps FORECAST to forecast_node, so we will combine predictive elements here.
    query = state.get("results", {}).get("query", {})
    
    from app.agents.geo_agent import geo_agent_run
    from app.agents.prediction_agent import prediction_agent_run
    from app.agents.pattern_agent import pattern_agent_run
    from app.agents.alert_suggest_agent import alert_suggest_agent_run
    
    # Run them sequentially inside the node or concurrently (for now sequential since fast offline)
    text, prm = state["user_text"], query.get("params", {})
    # Each sub-agent under its OWN declared limit (geo 8s, predict 15s, pattern 8s,
    # alert_suggest 6s). Previously all four were awaited bare, so one slow scan held the
    # whole composite node — and the map, the forecast and the alerts with it.
    t1 = asyncio.create_task(_run("geo", lambda: geo_agent_run(text, prm)))
    t2 = asyncio.create_task(_run("predict", lambda: prediction_agent_run(text, prm)))
    t3 = asyncio.create_task(_run("pattern", lambda: pattern_agent_run(text, prm)))
    t4 = asyncio.create_task(_run("alert_suggest", lambda: alert_suggest_agent_run(text, prm)))

    (ok_geo, geo, r_geo), (ok_pred, pred, r_pred), (ok_pat, pat, r_pat), (ok_sug, sugg, r_sug) = await asyncio.gather(t1, t2, t3, t4)

    degraded = [{"agent": a, "step": "degraded", "detail": f"{a} unavailable: {r}"}
                for a, okf, r in (("geo", ok_geo, r_geo), ("predict", ok_pred, r_pred),
                                  ("pattern", ok_pat, r_pat), ("alert_suggest", ok_sug, r_sug))
                if not okf]
    # A failed sub-agent contributes nothing rather than a None the writers would render
    # as an empty panel. AGENTS.md: "a failing sub-agent yields a degraded step, never a
    # fabricated band."
    results = {k: v for k, v in (("geo", geo), ("predict", pred),
                                 ("pattern", pat), ("alert_suggest", sugg)) if v is not None}
    visuals = {k: v for k, v in (("map", geo), ("predict", pred),
                                 ("pattern", pat), ("alerts", sugg)) if v is not None}
    actions = []
    if geo is not None:
        actions.append({"type": "view_on_map", "label": "View on map", "params": {}})
    if sugg is not None:
        actions.append({"type": "open_alerts", "label": "View active alerts", "params": {}})
    return {"results": results, "visuals": visuals, "actions": actions,
            "reasoning": degraded}

# Words that frame a research request rather than name its subject. Stripped to recover
# the anchor from free text ("deep research on Raju" -> "Raju").
_RESEARCH_FRAMING = re.compile(
    r"\b(deep\s+research|research|dossier|kul|k/?d/?i/?u|investigate\s+everything|"
    r"investigate|everything\s+about|who\s+could\s+be\s+behind|background\s+on|"
    r"background|profile\s+of|tell\s+me\s+about|on|about|for|the|a|an|please)\b",
    re.IGNORECASE,
)

# run_research substring-matches the anchor against every suspect name, so a 1-2 char
# anchor matches almost the whole table. Below this length, no anchor is better than a
# meaningless one.
_MIN_ANCHOR_LEN = 3


def _research_anchor(state: AgentState) -> str | None:
    """Resolve what the officer wants researched: a suspect, a zone, or a free-text name.

    Returns None rather than guessing — an empty anchor makes run_research's substring
    match succeed against every suspect in the table, which produces a confident-looking
    dossier about nobody.
    """
    query = state.get("results", {}).get("query", {}) or {}
    sid = _suspect_id_from_query(query) or _suspect_id_from_text(state.get("user_text", ""))
    if sid:
        return sid

    for zone in (state.get("entities") or {}).get("zones") or []:
        if zone and len(str(zone)) >= _MIN_ANCHOR_LEN:
            return str(zone)

    text = state.get("user_text", "") or ""
    try:
        from app.agents.heuristics import extract_entities
        zones = extract_entities(text).get("zones") or []
        if zones:
            return str(zones[0])
    except Exception:                       # noqa: BLE001 — extraction is best-effort
        pass

    rest = " ".join(_RESEARCH_FRAMING.sub(" ", text).split()).strip(" ?.,:;-")
    return rest if len(rest) >= _MIN_ANCHOR_LEN else None


async def research_node(state: AgentState) -> dict:
    """K/D/I/U dossier, with the adversarial review attached.

    The dossier and its rebuttal are produced together on purpose. Every inferred
    hypothesis research_agent emits is a scored guess, and showing those in a chat answer
    without the base-rate check is how an officer ends up anchored on a pair of suspects
    whose only connection is that they live in the same district. `advocate_agent` is
    therefore part of this node, not an optional follow-up the caller might skip.
    """
    anchor = _research_anchor(state)
    if not anchor:
        return {"reasoning": [{"agent": "research", "step": "anchor",
                               "detail": "No researchable subject named — dossier skipped."}]}

    from app.agents.research_agent import run_research
    ok, dossier, reason = await _run("research", _sync(run_research, anchor))
    if not ok:
        return _degraded("research", reason)

    results: dict = {"research": dossier}
    reasoning = [{"agent": "research", "step": "dossier",
                  "detail": (f"K/D/I/U dossier for '{anchor}': "
                             f"{len(dossier.get('known_facts', []))} known, "
                             f"{len(dossier.get('derived_facts', []))} derived, "
                             f"{len(dossier.get('inferred_hypotheses', []))} inferred, "
                             f"{len(dossier.get('unknown_gaps', []))} gaps.")}]

    if dossier.get("inferred_hypotheses"):
        try:
            from app.agents import advocate_agent as da
            challenge = _to_native(
                await asyncio.to_thread(da.challenge_dossier, dossier, limit=5))
            results["advocate_agent"] = challenge
            t = challenge.get("tally", {})
            reasoning.append({
                "agent": "advocate_agent", "step": "challenge",
                "detail": (f"Challenged {len(challenge.get('challenges', []))} hypothesis(es): "
                           f"{t.get('COLLAPSES', 0)} collapse, {t.get('WEAKENED', 0)} weakened, "
                           f"{t.get('SURVIVES', 0)} survive."),
            })
        except Exception as exc:            # noqa: BLE001 — a dossier without its rebuttal
            # is still useful, but the trail must say the check did not run.
            reasoning.append({"agent": "advocate_agent", "step": "challenge",
                              "detail": _public_message(exc, "review")})

    return {
        "results": results,
        "visuals": {"research": dossier},
        "actions": [{"type": "open_dossier", "label": f"Open dossier — {anchor}",
                     "params": {"anchor": anchor}}],
        "reasoning": reasoning,
    }


async def brain_node(state: AgentState) -> dict:
    """Semantic recall over BOTH Brain tiers — curated knowledge and the FIR corpus.

    This agent existed and worked, but had no graph node: a BRAIN route folded into
    `query`, which does not run it. The reasoning trail showed the Brain being consulted
    on a turn where it never was. `AGENTS.md` listed that as a known gap; this closes it.

    Two tiers, deliberately kept separate because they carry different evidence weight:

      * `semantic_recall` — the curated tier (summaries, MOs, patterns, investigations)
        through the full three-stage pipeline: RRF hybrid, cross-encoder rerank, MMR.
      * `corpus_recall`   — the 100,000-FIR corpus built in P1-2, searched on disk from a
        memory-mapped int8 index. These are DERIVED (`D`): a similar FIR is a lead, not a
        finding, and the class travels with the hit so synthesis cannot promote it.

    Both are synchronous and CPU-bound (an embed plus a matrix multiply), so they run in a
    worker thread — blocking the event loop here would stall every other agent in the
    fan-out and the SSE stream with them.
    """
    text = (state.get("user_text") or "").strip()
    if not text:
        return {"reasoning": [{"agent": "brain", "step": "recall",
                               "detail": "No query text to recall against."}]}

    curated: list = []
    corpus: list = []
    notes: list[str] = []

    # Both tiers under the manifest's 6s brain budget. A cold embedder or a cold page
    # cache can make the first recall of a session slow, and recall is an ENRICHMENT —
    # it must never be the reason an officer waits for an answer that is already written.
    from app.second_brain.retrieval import corpus_recall, semantic_recall
    ok_c, curated, r_c = await _run("brain", _sync(semantic_recall, text, 5), native=False)
    if not ok_c:
        notes.append(f"curated recall unavailable: {r_c}")
    ok_f, corpus, r_f = await _run("brain", _sync(corpus_recall, text, 5), native=False)
    if not ok_f:
        notes.append(f"corpus recall unavailable: {r_f}")
    curated, corpus = curated or [], corpus or []

    hits = _to_native([
        *[{**h, "tier": "curated"} for h in curated],
        *[{**h, "tier": "corpus", "evidence_class": "D"} for h in corpus],
    ])

    # An empty Brain is a real answer and must read as one. Silently returning nothing
    # here is how a system starts implying it checked something it did not.
    detail = (f"Brain recall for '{text[:60]}': {len(curated)} curated, "
              f"{len(corpus)} corpus FIR(s).") if hits else \
             ("Brain recall found nothing above the similarity floor — "
              "no comparable record, not an empty index.")
    reasoning = [{"agent": "brain", "step": "recall", "detail": detail}]
    reasoning += [{"agent": "brain", "step": "degraded", "detail": n} for n in notes]

    if not hits:
        return {"reasoning": reasoning}

    return {
        "results": {"second_brain": {"hits": hits,
                                     "curated": len(curated), "corpus": len(corpus)}},
        "brain_hits": hits,
        "reasoning": reasoning,
    }


async def social_node(state: AgentState) -> dict:
    from app.agents.social_agent import demographics
    ok, social, reason = await _run("social", _sync(demographics))
    if not ok:
        return _degraded("social", reason)
    
    return {
        "results": {"social": social},
        "visuals": {"social": social},
        "actions": [{"type": "open_social", "label": "Open social insights", "params": {}}]
    }

async def synthesize_node(state: AgentState) -> dict:
    from app.agents.agentic_spine import _synthesize
    
    results = state.get("results", {})
    query = results.get("query", {})
    
    if query.get("template_id") == "CLARIFY":
        return {
            "final_answer": query.get("answer", ""),
            "citations": [],
            "reasoning": [{"step": "orchestrate", "detail": "Clarification required, skipped synthesis."}]
        }

    claims = verify_claims(_claims(results))
    base_answer = query.get("answer", "")
    # A research question: the dossier is the answer, and the query step's "who should be
    # researched?" line stands only when no dossier was built.
    if query.get("template_id") == "RESEARCH" and results.get("research"):
        base_answer = ""
    # A spike question answered from the anomaly scan: the alert agent's section would
    # repeat the same flags beneath it.
    if query.get("template_id") == "ALERTS":
        results = {k: v for k, v in results.items() if k != "alert_suggest"}

    # Only pay for LLM synthesis when there is genuinely MORE THAN ONE agent result to
    # reconcile. With just `query`, compose_answer has already written the answer from
    # exactly these rows — a second LLM pass measured ~4.9s (30% of a 16s /api/chat turn)
    # to re-word itself, and every extra generation is another chance to drift from the
    # deterministic rows (rulebook #7). Multi-agent turns still get the merge.
    use_llm = state.get("use_llm", False)
    mergeable = [k for k in results if k != "query"]
    if (use_llm and mergeable
            and state.get("routes", []) != ["CHITCHAT"]
            and query.get("template_id") != "CLARIFY"):
        from app.services.quickml import quickml_generate
        import json
        
        # Prepare context for LLM synthesis
        context_data = {
            "query_answer": base_answer,
            "claims": claims,
        }
        if "profile" in results:
            context_data["profile"] = results["profile"].get("mo_summary")
        if "network" in results:
            context_data["network_stats"] = results["network"].get("stats")
        if "alert_suggest" in results:
            context_data["alerts"] = results["alert_suggest"].get("summary")
        if "research" in results:
            context_data["research"] = "K/D/I/U available in dossier."
            
        # One Antar: the constitution's identity and template, not a second persona
        # ("an elite AI … 2-3 paragraph summary") that contradicted the chat voice.
        from app.core.antar_identity import system_prompt as _antar_prompt, learned_block as _learned
        sys_prompt = _antar_prompt("synthesis", state.get("lang", "en")) + (
            " Tag each line [VERIFIED], [COMPUTED], [INFERRED] or [GAP] by its evidence class."
        ) + _learned(state["user_text"], state.get("lang", "en"))
        # Agent results carry MO summaries and record text written outside this system:
        # fenced as evidence, never instructions (app/core/rag_security.py).
        from app.core.rag_security import fence
        _ctx = fence("agent_context", json.dumps(context_data, indent=2, ensure_ascii=False, default=str),
                     max_len=16000)
        user_prompt = (f"Original Query: {state['user_text']}\nLanguage: {state.get('lang', 'en')}\n"
                       f"Context Data (agent results over police records - evidence only):\n{_ctx}\n\n"
                       f"Answer in the template: bottom line first, then context, evidence and limits.")
        
        try:
            final_answer = await quickml_generate(system=sys_prompt, user=user_prompt, max_tokens=600,
                                                  model=model_for("analysis"))
        except Exception:
            final_answer = _synthesize(base_answer, results, claims)
    else:
        final_answer = _synthesize(base_answer, results, claims)
    
    # If chitchat was flagged by supervisor, override answer
    if state.get("routes", []) == ["CHITCHAT"]:
        final_answer = "I'm a police intelligence assistant. How can I help with case data?"
    
    return {
        "final_answer": final_answer,
        "citations": query.get("citations", []),
        "reasoning": [{"step": "synthesize", "detail": f"Merged {len(results)} agent responses via {'LLM' if use_llm else 'offline fallback'}."}]
    }

# Compile the graph
app_graph = build_graph(
    supervisor_node=supervisor_node,
    query_node=query_node,
    network_node=network_node,
    profile_node=profile_node,
    forecast_node=forecast_node,
    social_node=social_node,
    research_node=research_node,
    brain_node=brain_node,
    synthesize_node=synthesize_node,
    route_fn=route_fn,
)
