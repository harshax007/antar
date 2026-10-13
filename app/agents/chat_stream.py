"""
Antar — Chat SSE Streaming  (POST /api/chat/stream)
=========================================================
Agentic streaming: the client sees each agent activate in real-time, then the
answer types out word-by-word, then citations / brain-hits / visuals / actions arrive.

SSE event sequence per query
─────────────────────────────
  step  {agent:"router",   status:"running", label:"…"}
  step  {agent:"router",   status:"done",    routes:[…], confidence:…}
  step  {agent:"query",    status:"running", label:"Searching crime database…"}
  step  {agent:"query",    status:"done",    rows:N, template_id:"T?"}
  step  {agent:"brain",    status:"running", label:"Checking Second Brain…"}
  step  {agent:"brain",    status:"done",    hits:N}
  step  {agent:"<X>",      status:"running", label:"…"}   # network/profile/geo/…
  step  {agent:"<X>",      status:"done",    …}
  step  {agent:"composer", status:"running", label:"Composing answer…"}
  token {content:"…"}   ×N           # word-by-word typewriter
  step  {agent:"composer", status:"done"}
  citations  {data:[…]}
  brain_hits {data:[…]}
  visual     {key:"graph"|"map"|…, data:{…}}   ×K
  confidence {routing:…, answer:…, label:"…"}
  actions    {data:[…]}
  suggested  {data:[…]}
  complete   {session_id, template_id, mode, lang, reasoning, …}

Client note
-----------
The browser EventSource API only supports GET.  Use fetch + ReadableStream for POST:

    const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text, session_id, lang}),
    });
    const reader = res.body.getReader();
    // decode and parse "data: {...}\\n\\n" lines
"""

from __future__ import annotations

import asyncio
import time
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.heuristics import is_kannada, is_explain_request
from app.core import orchestrator, sessions
from app.core.rate_limiter import rate_limit
from app.core.settings import settings
from app.core.security import public_message as _public_message
from app.core.sse import SSEQueue, token_stream
from app.services import audit_store

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


class StreamChatRequest(BaseModel):
    # Bounded: the text is matched by the router's patterns and can be sent to the model,
    # so its size is a cost an officer (or anyone holding a token) should not set freely.
    session_id: str | None = Field(default=None, max_length=128)
    text: str = Field(max_length=4000)
    lang: str | None = Field(default=None, max_length=8)
    deep_think: bool = False


_SSE_HEADERS = {
    "Cache-Control":    "no-cache",
    "X-Accel-Buffering": "no",     # disable nginx buffering
    "Connection":       "keep-alive",
    "Content-Type":     "text/event-stream; charset=utf-8",
}


def _L(lang: str, en: str, kn: str) -> str:
    """Pick the Kannada string when the (toggle-driven) lang is 'kn', else English."""
    return kn if lang == "kn" else en


def _answer_confidence(routing_conf: float, rows: list, citations: list, lang: str = "en",
                       fidelity: float = 1.0, gaps: list[str] | None = None) -> dict:
    """Answer-confidence score (plan §1.4). Three signals into a single [0,1] value:
      a = citation grounding  — how many citations found / expected min (3)
      b = row sufficiency     — rows / 3, capped at 1.0
      c = routing confidence  — how sure the router was about agent selection

    This docstring used to open with the word "Calibrated". It is not, and the claim is
    now measured rather than asserted: `docs/CONFIDENCE_CALIBRATION.md`, 2026-09-26.

    Where it stands. After the extraction fixes the score is *well* calibrated on counting
    questions — ECE 0.080 against 92.2% accuracy — but it has almost no DISCRIMINATION:
    a, b and c all saturate on any successful template query, so 99 of 102 measured
    answers scored 0.989 whether they were right or wrong. It cannot warn an officer about
    the ~8% it still gets wrong.

    An isotonic recalibration was fitted and REJECTED: it failed its 31-question holdout
    (ECE 0.038 -> 0.066), because there is nothing to learn from a near-constant input.
    The fix is a signal that actually varies — resolution fidelity, i.e. whether every
    filter the officer named was applied — not a curve over this one.
    """
    a = min(1.0, len(citations) / 3) if citations else 0.0
    b = min(1.0, len(rows) / 3)     if rows      else 0.0
    c = routing_conf
    # `fidelity` is the signal the other three lack. a, b and c all saturate on any
    # successful template query — 99 of 102 measured answers scored 0.989 whether they
    # were right or wrong — so the score could not discriminate. Fidelity asks a different
    # question, one that actually varies: did every filter the officer NAMED reach the
    # query? It multiplies rather than adds, because a dropped filter does not make an
    # answer slightly worse; it makes it an answer to a different question.
    score = round((0.40 * a + 0.30 * b + 0.30 * c) * max(0.0, min(1.0, fidelity)), 2)
    if score >= 0.80:
        label = _L(lang, "High confidence", "ಹೆಚ್ಚಿನ ವಿಶ್ವಾಸ")
    elif score >= 0.60:
        label = _L(lang, "Moderate confidence", "ಮಧ್ಯಮ ವಿಶ್ವಾಸ")
    else:
        label = _L(lang, "Low confidence — verify with source FIRs",
                   "ಕಡಿಮೆ ವಿಶ್ವಾಸ — ಮೂಲ ಎಫ್‌ಐಆರ್‌ಗಳೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ")
    out = {"routing": round(c, 2), "answer": score, "label": label}
    if gaps:
        # The officer is told WHICH part of their question did not run, not merely that
        # confidence is lower. A number that drops without saying why is not an
        # explanation, and this is the one place the system knows exactly why.
        out["fidelity"] = round(max(0.0, min(1.0, fidelity)), 2)
        out["gaps"] = list(gaps)
        out["label"] = _L(lang, "Broader than asked — " + gaps[0],
                          "ಕೇಳಿದ್ದಕ್ಕಿಂತ ವಿಶಾಲ — " + gaps[0])
    return out


async def _run_pipeline(req: StreamChatRequest, q: SSEQueue, officer: str = "OF-stream") -> None:
    """Full agentic pipeline that emits SSE events via *q* as it progresses.
    Mirrors agentic_spine.run_agentic_spine() but with live event emission.
    """
    # Server-side stopwatch for the "Thought for Ns" line. The UI used to compute this
    # itself as Date.now() − message time, which kept growing after the answer arrived.
    t_start     = time.perf_counter()
    session_id  = req.session_id or f"ses-{uuid.uuid4().hex[:12]}"
    lang        = req.lang or ("kn" if is_kannada(req.text) else "en")
    reasoning_id = f"rsn-{uuid.uuid4().hex[:12]}"
    use_llm     = bool(settings.QUICKML_CLIENT_ID and settings.QUICKML_CLIENT_SECRET
                       and not settings.DEMO_MODE)

    sessions.append_user_turn(session_id, req.text, lang)

    # ── Slash commands (/think /connect /anticipate) ─────────────────────────
    from app.agents.heuristics import parse_slash_command, SLASH_COMMANDS
    command, stripped = parse_slash_command(req.text)
    query_text = stripped if (command and stripped) else req.text

    if command and not stripped:
        # Bare command → usage help, no fabricated answer.
        spec = SLASH_COMMANDS[command]
        answer = (f"/{command} — {spec['label']}.\n"
                  f"Usage: /{command} <your question>  e.g. "
                  f"/{command} chain snatching in Rajajinagar")
        await q.emit("step", agent="command", status="done",
                     command=command, label=f"/{command} usage")
        async for chunk in token_stream(answer):
            await q.emit("token", content=chunk)
        await q.emit("complete", session_id=session_id, template_id="COMMAND_HELP",
                     mode="command", lang=lang, reasoning_id=reasoning_id,
                     agents_used=["command"])
        sessions.append_assistant_turn(session_id, answer, lang, "COMMAND_HELP",
                                       reasoning_id, [{"step": "command", "detail": f"/{command} usage shown."}])
        await q.close()
        return

    if command:
        await q.emit("step", agent="command", status="done", command=command,
                     label=f"/{command} — {SLASH_COMMANDS[command]['label']}")

    # ── Explain shortcut ──────────────────────────────────────────────────────
    if command is None and is_explain_request(req.text, sessions.has_assistant_turn(session_id)):
        steps = sessions.last_reasoning(session_id)
        if steps:
            trail = "\n".join(
                f"{i+1}. {s.get('detail', s.get('step', ''))}"
                for i, s in enumerate(steps)
            )
            prefix = "ನಾನು ಈ ಉತ್ತರವನ್ನು ಹೇಗೆ ತಲುಪಿದೆ:\n" if lang == "kn" else "Here's how I reached that answer:\n"
            answer = prefix + trail
        else:
            answer = ("ವಿವರಿಸಲು ಹಿಂದಿನ ಉತ್ತರವಿಲ್ಲ." if lang == "kn"
                      else "There's no previous answer in this session to explain yet.")

        await q.emit("step", agent="explain", status="done", label="Replaying execution trace")
        async for chunk in token_stream(answer):
            await q.emit("token", content=chunk)
        await q.emit("complete", session_id=session_id, template_id="EXPLAIN",
                     mode="explain", lang=lang, reasoning_id=reasoning_id,
                     agents_used=["explain"])
        sessions.append_assistant_turn(session_id, answer, lang, "EXPLAIN",
                                       reasoning_id, [{"step": "explain", "detail": "Replayed trail."}])
        await q.close()
        return

    history = sessions.recent_turns(session_id)

    # ── Guardrail: Fast Intent Check ──────────────────────────────────────────────────────────
    from app.agents.heuristics import heuristic_select
    hs_res = await heuristic_select(query_text, lang, history=history)
    # Questions answered by an agent rather than a query template ("any early warnings?",
    # "forecast theft") have no template — they must not be turned away as off-topic.
    from app.agents.agentic_spine import _route as _route_fn
    _agent_ask = [a for a in _route_fn(query_text)[0]
                  if a in ("network", "profile", "alert_suggest", "predict", "pattern")]
    from app.forecast.chat import wants_forecast as _wants_forecast
    _is_forecast = _wants_forecast(query_text)
    if hs_res.get("template_id") == "NONE" and not command and not req.deep_think and not _agent_ask             and not _is_forecast:
        answer = ("I'm built for crime-data questions, so I can't answer that one.\n"
                  "Try asking:\n• most crimes?\n• theft trend in Bengaluru City\n"
                  "• how many murders in 2023?\n• who are the repeat offenders?"
                  if lang == "en" else
                  "ನಾನು ಅಪರಾಧ ದತ್ತಾಂಶದ ಪ್ರಶ್ನೆಗಳಿಗೆ ಮಾತ್ರ ಉತ್ತರಿಸುತ್ತೇನೆ.\n"
                  "ಹೀಗೆ ಕೇಳಿ ನೋಡಿ:\n• ಅತಿ ಹೆಚ್ಚು ಅಪರಾಧ ಎಲ್ಲಿ?\n• ದರೋಡೆ ಪ್ರವೃತ್ತಿ ತೋರಿಸಿ\n"
                  "• ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು ಯಾರು?")
        await q.emit("step", agent="guardrail", status="done",
                     label=_L(lang, "Intent verification", "ಉದ್ದೇಶ ಪರಿಶೀಲನೆ"))
        async for chunk in token_stream(answer):
            await q.emit("token", content=chunk)
        await q.emit("complete", session_id=session_id, template_id="NONE",
                     mode="guardrail", lang=lang, reasoning_id=reasoning_id,
                     agents_used=["guardrail"])
        sessions.append_assistant_turn(session_id, answer, lang, "NONE",
                                       reasoning_id, [{"step": "guardrail", "detail": "Intercepted off-topic query."}])
        await q.close()
        return

    # ━━ Step 1: Router ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    await q.emit("step", agent="router", status="running",
                 label=_L(lang, "Analyzing your query…", "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ…"))

    from app.agents.agentic_spine import _route
    from app.agents.heuristics import heuristic_select
    from app.services.quickml import quickml_generate

    routes, routing_conf = _route(query_text)
    if command:
        forced = SLASH_COMMANDS[command]["forces"]
        routes = list(dict.fromkeys(list(routes) + forced))
    if req.deep_think:
        for _agent in ["network", "pattern"]:
            if _agent not in routes:
                routes.append(_agent)
    if "osint" in routes:
        routes.remove("osint")
    await q.emit("step", agent="router", status="done",
                 routes=routes, confidence=routing_conf,
                 label=_L(lang, "Routed to ", "ರವಾನಿಸಲಾಗಿದೆ: ") + ", ".join(routes)
                       + (f" (/{command})" if command and SLASH_COMMANDS[command]["forces"] else "")
                       + (_L(lang, " (Expert Deep Think)", " (ವಿಸ್ತೃತ ಚಿಂತನೆ)") if req.deep_think else ""))

    # ── Step 2: Query Agent ───────────────────────────────────────────────────
    await q.emit("step", agent="query", status="running",
                 label=_L(lang, "Searching crime database…", "ಅಪರಾಧ ಡೇಟಾಬೇಸ್‌ನಲ್ಲಿ ಹುಡುಕಲಾಗುತ್ತಿದೆ…"))

    from app.agents.query_agent import query_agent_run
    # The query agent does seconds of synchronous SQLite work. Awaited on this loop it
    # blocked the SSE writer, so "Analyzing…/Searching…" only reached the screen together
    # with the answer. On a worker thread (own loop) the steps stream as they happen.
    #
    # Routing is deterministic-first. The QuickML endpoint (GLM behind it, with hidden
    # reasoning) takes 14–45s per call, so it cannot sit on every question's critical path.
    # The whitelisted router resolves the question; the LLM is consulted only when the
    # router can't (CLARIFY/NONE), under a hard cap, and only a valid template is accepted.
    async def _hybrid_select(text, lng, entities=None, history=None):
        choice = await heuristic_select(text, lng, entities or {}, history=history)
        if choice.get("template_id") == "NONE" and _agent_ask:
            # An agent question ("any early warnings this week?"): the agent's section is the
            # answer. Left as NONE, self-heal substituted an unrelated 419k-case list.
            return {"template_id": "CLARIFY", "answer_lang": lng,
                    "params": {"missing": "crime_types", "intent": "alerts"}}
        if use_llm and choice.get("template_id") in ("CLARIFY", "NONE") and not _agent_ask:
            try:
                from app.agents.query_agent import select_template
                from app.services.zcql_repo import TEMPLATES as _T
                llm_choice = await asyncio.wait_for(
                    select_template(text, lng, entities or {}, quickml_generate, history), 8.0)
                if llm_choice.get("template_id") in _T:
                    return llm_choice
            except Exception as e:
                logger.warning("llm_select_fallback", error=f"{type(e).__name__}: {e}"[:200])
        return choice

    query = await asyncio.to_thread(lambda: asyncio.run(query_agent_run(
        query_text,
        lang=lang,
        session_id=session_id,
        history=history,
        select_llm=None,            # self-heal stays deterministic (an LLM here cost 40s+)
        compose_llm=None,           # compose handled below with token streaming
        selector=_hybrid_select,
    )))
    template_id = query.get("template_id", "NONE")
    rows        = query.get("rows", [])
    citations   = query.get("citations", [])

    await q.emit("step", agent="query", status="done",
                 rows=len(rows), template_id=template_id,
                 label=_L(lang, f"Found {len(rows)} records → template {template_id}",
                          f"{len(rows)} ದಾಖಲೆಗಳು ಸಿಕ್ಕಿವೆ → {template_id}"))

    # Surface the self-healing RAG loop when it kicked in (empty/ungrounded first query).
    heal_steps = [s for s in query.get("reasoning", []) if s.get("step") == "self_heal"]
    if heal_steps:
        await q.emit("step", agent="self_heal", status="done",
                     label=heal_steps[-1].get("detail", "Self-healing applied"))

    # ── Step 3: Second Brain ──────────────────────────────────────────────────
    await q.emit("step", agent="brain", status="running",
                 label=_L(lang, "Checking Second Brain for linked cases…",
                          "ಸಂಬಂಧಿತ ಪ್ರಕರಣಗಳಿಗಾಗಿ ಸೆಕೆಂಡ್ ಬ್ರೈನ್ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…"))

    # Relevance gates: the Brain always returns SOMETHING on a tiny index, so
    # only attach hits that are actually about this query — and only banner
    # the top hit when it is clearly related. No decoration for its own sake.
    _BRAIN_HIT_FLOOR = 0.35
    _BRAIN_BANNER_MIN = 0.45

    brain_hits: list[dict] = []
    brain_banner: str | None = None
    brain_notes: list[dict] = []        # folded into extra_reasoning below
    try:
        from app.second_brain.retrieval import semantic_recall
        # Both recalls are CPU-bound (an embed plus a matrix multiply) and were being
        # awaited inline on the event loop, stalling every other request on the server
        # for their duration. Measured ~110 ms for the corpus search alone.
        hits = await asyncio.to_thread(semantic_recall, query_text, 3) or []
        brain_hits = [h for h in hits if h.get("kind") in
                      ("resolved_pattern", "case_summary", "suspect_profile")
                      and h.get("score", 0.0) >= _BRAIN_HIT_FLOOR]
        top = brain_hits[0] if brain_hits else None
        if top and top.get("score", 0.0) >= _BRAIN_BANNER_MIN:
            brain_banner = top.get("summary_text")
    except Exception as exc:                # noqa: BLE001
        # This used to be a bare `pass`. A Brain that failed and a Brain that found
        # nothing then looked identical to the officer, and identical in the trace.
        brain_notes.append({"agent": "brain", "step": "curated",
                            "detail": _public_message(exc, "recall")})

    # The 100,000-FIR corpus (P1-2) was INVISIBLE on this surface until now — which is the
    # surface the app actually streams. `semantic_recall` reads the in-memory index, and
    # the filter above only admits three curated kinds, so corpus rows (kind "fir") were
    # excluded twice over. The headline Brain capability was reachable from /api/brain and
    # from a BRAIN-routed graph turn, and from nowhere the officer was looking.
    #
    # Kept as a separate list rather than merged into `brain_hits`: a similar FIR is
    # DERIVED evidence — a lead — and must not be presented with the weight of a curated,
    # human-confirmed pattern. The class travels with the hit.
    corpus_hits: list[dict] = []
    try:
        from app.second_brain.retrieval import corpus_recall
        _corpus = await asyncio.to_thread(corpus_recall, query_text, 3) or []
        corpus_hits = [{**h, "tier": "corpus", "evidence_class": "D"}
                       for h in _corpus
                       if h.get("score", 0.0) >= _BRAIN_HIT_FLOOR]
    except Exception as exc:                # noqa: BLE001
        brain_notes.append({"agent": "brain", "step": "corpus",
                            "detail": _public_message(exc, "corpus recall")})

    _corpus_n = len(corpus_hits)
    _corpus_label = (_L(lang, f" · {_corpus_n} similar FIR(s)",
                        f" · {_corpus_n} ಹೋಲುವ FIR") if _corpus_n else "")
    await q.emit("step", agent="brain", status="done",
                 hits=len(brain_hits),
                 corpus=_corpus_n,
                 banner=brain_banner,
                 label=_L(lang, f"{len(brain_hits)} Second Brain match(es)",
                          f"{len(brain_hits)} ಸೆಕೆಂಡ್ ಬ್ರೈನ್ ಹೊಂದಾಣಿಕೆ(ಗಳು)") + _corpus_label)

    # ── Step 4: Parallel sub-agents (triggered by route) ─────────────────────
    results: dict = {"query": query,
                     "second_brain": {"hits": brain_hits, "banner": brain_banner,
                                      "corpus": corpus_hits}}
    visuals: dict = {}
    actions: list = list(query.get("reasoning", []))   # reuse query actions later
    extra_reasoning: list = list(brain_notes)

    from app.agents.agentic_spine import (
        _suspect_id_from_query, _suspect_id_from_text, _query_actions
    )
    suspect_id = _suspect_id_from_query(query) or _suspect_id_from_text(query_text)
    actions = _query_actions(query) + list(query.get("actions") or [])
    if template_id in ("FORECAST", "UNRESOLVED") and _is_forecast and not command:
        # The forecast answer is measured (back-tested, ranged, Inferred). The older predict /
        # pattern / alert / geo agents would append unmeasured "risk" sections beneath it that
        # can contradict it, so they don't run for a forecast question.
        routes = [r for r in routes if r not in ("predict", "pattern", "alert_suggest", "geo")]
    params = query.get("params", {})
    tasks = []

    async def _degraded(agent: str, meta: dict) -> None:
        # Honest degradation: the agent is reported unavailable — never fake data.
        await q.emit("step", agent=agent, status="degraded",
                     label=_L(lang, f"{agent} agent unavailable — {meta.get('reason', 'unknown failure')}",
                              f"{agent} ಏಜೆಂಟ್ ಲಭ್ಯವಿಲ್ಲ — {meta.get('reason', 'unknown')}"))

    async def run_profile_task():
        await q.emit("step", agent="profile", status="running",
                     label=_L(lang, "Building suspect profile…", "ಶಂಕಿತ ವ್ಯಕ್ತಿಯ ವಿವರ ರಚಿಸಲಾಗುತ್ತಿದೆ…"))
        from app.agents.profile_agent import compute_profile
        ok, prof, meta = await orchestrator.run_agent(
            "profile", lambda: asyncio.to_thread(compute_profile, suspect_id))
        if not ok:
            return await _degraded("profile", meta)
        if prof:
            results["profile"] = prof
            visuals["profile"] = prof
            actions.append({"type": "open_profile", "label": "Open profile", "params": {"suspect_id": suspect_id}})
        _rs = prof.get('risk_score', 'N/A') if prof else 'N/A'
        await q.emit("step", agent="profile", status="done",
                     label=_L(lang, f"Risk score: {_rs}", f"ಅಪಾಯ ಸ್ಕೋರ್: {_rs}"))

    async def run_network_task():
        nonlocal brain_banner
        await q.emit("step", agent="network", status="running",
                     label=_L(lang, "Mapping criminal network…", "ಅಪರಾಧ ಜಾಲವನ್ನು ಮ್ಯಾಪ್ ಮಾಡಲಾಗುತ್ತಿದೆ…"))
        from app.agents.network_agent import build_network
        ok, graph, meta = await orchestrator.run_agent(
            "network", lambda: asyncio.to_thread(build_network, suspect_id))
        if not ok:
            return await _degraded("network", meta)
        results["network"] = graph
        visuals["graph"] = graph
        brain_hits.extend(graph.get("brain_links", []))
        if graph.get("brain_banner"):
            brain_banner = graph["brain_banner"]
        # Rebuild, but KEEP the corpus tier — this line used to replace the whole dict
        # and silently drop it whenever the network agent ran.
        results["second_brain"] = {"hits": brain_hits, "banner": brain_banner,
                                   "corpus": corpus_hits}
        actions.append({"type": "show_network", "label": "Show network", "params": {"suspect_id": suspect_id}})
        nodes = len(graph.get("nodes", []))
        await q.emit("step", agent="network", status="done", nodes=nodes, edges=len(graph.get("edges", [])), brain_banner=brain_banner,
                     label=_L(lang, f"{nodes} nodes · Second Brain {'hit' if brain_banner else 'no match'}",
                              f"{nodes} ನೋಡ್‌ಗಳು · ಸೆಕೆಂಡ್ ಬ್ರೈನ್ {'ಹೊಂದಾಣಿಕೆ' if brain_banner else 'ಇಲ್ಲ'}"))

    async def run_geo_task():
        await q.emit("step", agent="geo", status="running",
                     label=_L(lang, "Geo-intelligence analysis…", "ಭೌಗೋಳಿಕ ಗುಪ್ತಚರ ವಿಶ್ಲೇಷಣೆ…"))
        from app.agents.geo_agent import geo_agent_run
        ok, geo, meta = await orchestrator.run_agent("geo", lambda: geo_agent_run(query_text, params))
        if not ok:
            return await _degraded("geo", meta)
        results["geo"] = geo
        visuals["map"] = geo
        actions.append({"type": "view_on_map", "label": "View on map", "params": {}})
        await q.emit("step", agent="geo", status="done",
                     label=_L(lang, "Hotspots and beat suggestions ready", "ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳು ಮತ್ತು ಗಸ್ತು ಸಲಹೆಗಳು ಸಿದ್ಧ"))

    async def run_pattern_task():
        await q.emit("step", agent="pattern", status="running",
                     label=_L(lang, "Detecting crime patterns…", "ಅಪರಾಧ ಮಾದರಿಗಳನ್ನು ಪತ್ತೆ ಮಾಡಲಾಗುತ್ತಿದೆ…"))
        from app.agents.pattern_agent import pattern_agent_run
        ok, pat, meta = await orchestrator.run_agent("pattern", lambda: pattern_agent_run(query_text, params))
        if not ok:
            return await _degraded("pattern", meta)
        results["pattern"] = pat
        visuals["pattern"] = pat
        actions.append({"type": "open_pattern", "label": "Open patterns", "params": {}})
        await q.emit("step", agent="pattern", status="done", label=pat.get("summary", "Patterns ready"))

    async def run_predict_task():
        await q.emit("step", agent="predict", status="running",
                     label=_L(lang, "Computing risk forecast…", "ಅಪಾಯದ ಮುನ್ಸೂಚನೆ ಲೆಕ್ಕಹಾಕಲಾಗುತ್ತಿದೆ…"))
        from app.agents.prediction_agent import prediction_agent_run
        ok, pred, meta = await orchestrator.run_agent("predict", lambda: prediction_agent_run(query_text, params))
        if not ok:
            return await _degraded("predict", meta)
        results["predict"] = pred
        visuals["predict"] = pred
        actions.append({"type": "open_predict", "label": "Open predictions", "params": {}})
        await q.emit("step", agent="predict", status="done", label=pred.get("summary", "Forecast ready"))

    async def run_alerts_task():
        await q.emit("step", agent="alerts", status="running",
                     label=_L(lang, "Generating patrol recommendations…", "ಗಸ್ತು ಶಿಫಾರಸುಗಳನ್ನು ರಚಿಸಲಾಗುತ್ತಿದೆ…"))
        from app.agents.alert_suggest_agent import alert_suggest_agent_run
        ok, sugg, meta = await orchestrator.run_agent("alerts", lambda: alert_suggest_agent_run(query_text, params))
        if not ok:
            return await _degraded("alerts", meta)
        results["alert_suggest"] = sugg
        visuals["alerts"] = sugg
        actions.append({"type": "open_alerts", "label": "View active alerts", "params": {}})
        await q.emit("step", agent="alerts", status="done", label=sugg.get("summary", "Recommendations ready"))

    async def run_osint_task():
        await q.emit("step", agent="osint", status="running",
                     label=_L(lang, "OSINT open-web scan…", "OSINT ಮುಕ್ತ-ವೆಬ್ ಸ್ಕ್ಯಾನ್…"))
        from app.agents.osint_agent import osint_agent_run
        ok, osint_res, meta = await orchestrator.run_agent("osint", lambda: osint_agent_run(query_text, params))
        if not ok:
            return await _degraded("osint", meta)
        results["osint"] = osint_res
        visuals["osint"] = osint_res
        actions.append({"type": "open_osint", "label": "Open OSINT panel", "params": {}})
        await q.emit("step", agent="osint", status="done", label=osint_res.get("summary", "OSINT ready"))

    if command == "connect" and not suspect_id:
        # Honest: /connect forced linkage agents but no entity resolved from the query.
        await q.emit("step", agent="network", status="done",
                     label="No entity resolved in query — showing database links only")
    if "profile" in routes and suspect_id:
        tasks.append(run_profile_task())
    if "network" in routes and suspect_id:
        tasks.append(run_network_task())
    if "geo" in routes or (template_id in ("T11", "T12", "T1", "T15") and not _is_forecast):
        tasks.append(run_geo_task())
    if "pattern" in routes:
        tasks.append(run_pattern_task())
    if "predict" in routes:
        tasks.append(run_predict_task())
    if "alert_suggest" in routes:
        tasks.append(run_alerts_task())
    if "osint" in routes:
        tasks.append(run_osint_task())

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    # ── Step 5: Synthesize answer ─────────────────────────────────────────────
    await q.emit("step", agent="composer", status="running",
                 label=_L(lang, "Composing answer…", "ಉತ್ತರವನ್ನು ರಚಿಸಲಾಗುತ್ತಿದೆ…"))

    from app.agents.agentic_spine import _claims, _synthesize, verify_claims
    claims  = verify_claims(_claims(results))
    base    = query.get("answer", "")
    # The geo agent runs automatically for list/ranking templates so the map visual and
    # "View on map" action are ready — but its one-line beat suggestion belongs in the
    # ANSWER TEXT only when geo was actually asked for. Appended under every ranking it
    # read as noise beneath a direct answer ("Geo-Intel: Recent spike (16 cases)…").
    # Same for pattern clusters and network size: when the query already answered directly
    # ("most crimes?" → the ranking), "Patterns: Found 336 clusters" / "Network: 6 nodes"
    # is background telemetry, not an answer. Keep them in text only when they ARE the
    # answer (no rows) or the officer asked for them by name.
    _asked = query_text.casefold()
    def _keep(k: str) -> bool:
        if k == "geo":
            # The geo route also fires on words like "city"; a patrol tip only belongs under
            # a where / hotspot / patrol question, not under "how many murders in Bengaluru City".
            return "geo" in routes and any(w in _asked for w in (
                "hotspot", "patrol", "where", "map", "beat", "deploy", "ಎಲ್ಲಿ", "ಗಸ್ತು", "ಹಾಟ್"))
        if k == "pattern":
            return not rows or any(w in _asked for w in ("pattern", "cluster", "ಮಾದರಿ"))
        if k == "network":
            return not rows or bool(suspect_id) and template_id == "T2" or any(
                w in _asked for w in ("network", "link", "associate", "ಜಾಲ"))
        return True
    text_results = {k: v for k, v in results.items() if _keep(k)}
    # When the router couldn't pin a data question (NONE/CLARIFY) but an agent answered it —
    # "any early warnings?", "show network of S0005" — the agent's section IS the answer;
    # a "could you rephrase?" above it would contradict it.
    if template_id in ("NONE", "CLARIFY") and any(k in text_results for k in
                                                   ("alert_suggest", "network", "profile", "predict")):
        base = ""
    answer  = _synthesize(base, text_results, claims, lang=lang)

    # If the LLM compose path is available, use it for a richer answer — but only for
    # templates the deterministic writer does not cover. Where it does, its answer is the
    # verified one (every number computed from the rows) and the LLM rewrite never beat
    # its 6s timeout anyway, so calling it only added 6s of dead wait to every question.
    _has_writer = False
    if use_llm and rows:
        try:
            from app.agents.answer_writer import write_answer
            _has_writer = bool(write_answer(rows, template_id, lang, params, query_text))
        except Exception:
            _has_writer = False
    if use_llm and rows and not _has_writer:
        from app.agents.query_agent import compose_answer
        try:
            llm_answer, used, _viol = await compose_answer(query_text, rows, lang, template_id,
                                                           quickml_generate, params=params)
            if used:
                answer = _synthesize(llm_answer, text_results, claims, lang=lang)
        except Exception as e:
            logger.error("composer_fallback", error=str(e))
            # Fall back to offline `base` answer gracefully

    # The reasoning trail is NEVER appended to the answer. It is already delivered as
    # structured `reasoning` (the UI renders it in the Expert terminal and the "Why?"
    # collapse), so appending it here put pipeline internals — "Classified as T11",
    # "Extracted: {'crime_types': ...}" — into the officer-facing answer body, where
    # build_layout then promoted them to `facts` and they became the visible content
    # while the real answer hid behind "Show full answer". Answer = answer. Trail = trail.

    mode = "llm" if (use_llm and query.get("llm_answer")) else "offline"

    # Apply Option B notification flow (check recently completed background jobs)
    from app.core.output_formatter import format_agent_response
    fmt_res = format_agent_response(
        {"answer": answer, "actions": actions, "citations": citations, "visuals": visuals},
        mode=mode, lang=lang
    )
    answer = fmt_res["answer"]
    actions = [a if isinstance(a, dict) else a.to_dict() for a in fmt_res["actions"]]

    # Antar's identity is applied HERE, to whichever path produced the answer (the LLM or
    # the deterministic writer): shaped into the response template, evidence-classed,
    # voice-checked and protected — before a single token is streamed.
    from app.core.antar_identity import present as _present
    identity = _present(answer, query, lang)
    answer = identity["text"]
    if identity["violations"]:
        logger.warning("antar_voice_violation", violations=identity["violations"])

    # ── Step 6: Token stream ──────────────────────────────────────────────────
    async for chunk in token_stream(answer, delay_s=0.002):
        await q.emit("token", content=chunk)

    await q.emit("step", agent="composer", status="done",
                 label=_L(lang, "Answer ready", "ಉತ್ತರ ಸಿದ್ಧ"))

    # ── Step 7: Metadata events ───────────────────────────────────────────────
    if citations:
        await q.emit("citations", data=citations)

    if brain_hits or corpus_hits:
        # `corpus` rides alongside rather than inside `data`: the client must be able to
        # render a curated, human-confirmed hit differently from a DERIVED similar FIR.
        await q.emit("brain_hits", data=brain_hits, banner=brain_banner,
                     corpus=corpus_hits)

    for key, payload in visuals.items():
        await q.emit("visual", key=key, data=payload)

    from app.agents.layout_composer import build_layout, build_custody, with_identity as _with_identity
    layout = build_layout(answer, query, results)
    layout = _with_identity(layout, identity)
    if layout.get("headline"):
        await q.emit("layout", data=layout)

    # Chain-of-custody strip — the evidentiary provenance of this answer (collapsed in UI).
    custody = build_custody(query, mode=mode)
    if custody:
        await q.emit("custody", data=custody)

    # Resolution fidelity: did every filter the officer named actually reach the query?
    # Computed from the question and the RESOLVED params, so it sees a term the selector
    # dropped — the blind spot that let "how many riots cases" return the whole registry.
    try:
        from app.agents.query_agent import resolution_fidelity
        _fid, _gaps = resolution_fidelity(query_text, query.get("params") or {})
    except Exception:                       # noqa: BLE001 — never fail an answer on this
        _fid, _gaps = 1.0, []
    conf = _answer_confidence(routing_conf, rows, citations, lang, _fid, _gaps)
    await q.emit("confidence", **conf)
    if _gaps:
        # Say it in the trail as well as the score, so /explain replays it.
        extra_reasoning.append({"agent": "query", "step": "resolution",
                                "detail": "Answered broader than asked: " + "; ".join(_gaps)})

    if actions:
        await q.emit("actions", data=actions)

    suggested = query.get("suggested_followups", [])
    if suggested:
        await q.emit("suggested", data=suggested)

    # ── Step 8: Persist & complete ────────────────────────────────────────────
    reasoning = query.get("reasoning", []) + [{
        "step": "orchestrate",
        "detail": f"Streamed to {', '.join(routes)} with confidence {routing_conf}.",
    }]
    elapsed_ms = int((time.perf_counter() - t_start) * 1000)
    audit_hash = audit_store.record_ai_reasoning(
        officer=officer,
        session_id=session_id,
        user_text=req.text,
        answer=answer,
        agents_used=routes,
        citations=citations,
        reasoning_id=reasoning_id,
        reasoning_trace=reasoning
    )
    try:
        from app.services.zcql_repo import TEMPLATES
        method = TEMPLATES[template_id].description if template_id in TEMPLATES else template_id
    except Exception:
        method = template_id
    sessions.append_assistant_turn(
        session_id, answer, lang, template_id, reasoning_id, reasoning,
        meta={
            "question": req.text, "officer": officer, "citations": (citations or [])[:50],
            "rows": len(rows or []), "template_id": template_id, "method": method,
            "confidence": conf, "elapsed_ms": elapsed_ms, "audit_hash": audit_hash,
            "mode": mode, "agents": routes, "lang": lang,
        })

    await q.emit("complete",
                 session_id=session_id,
                 reasoning_id=reasoning_id,
                 command=command,
                 template_id=template_id,
                 lang=lang,
                 mode=mode,
                 agents_used=routes,
                 # What the Expert workspace states under "Sources": the named method that
                 # produced the answer and how many records it stands on. Both were already
                 # written to the session meta below — the screen just could not see them.
                 method=method,
                 rows=len(rows or []),
                 confidence=conf,
                 reasoning=reasoning,
                 elapsed_ms=elapsed_ms,
                 audit_hash=audit_hash,
                 suspects=query.get("suspects", []),
                 demo_cache_hit=query.get("demo_cache_hit", False))

    await q.close()


@router.post("/stream", dependencies=[Depends(rate_limit(60, 1.0))])
@router.post("/stream/", dependencies=[Depends(rate_limit(60, 1.0))])
async def chat_stream(req: StreamChatRequest, request: Request) -> StreamingResponse:
    """POST /api/chat/stream — SSE streaming chat endpoint.

    Emits typed SSE events as agents execute, then streams answer tokens,
    then pushes citations / visuals / confidence / complete.

    The caller must use fetch + ReadableStream (not EventSource, which is GET-only):

        const res  = await fetch('/api/chat/stream', {method:'POST', body:…});
        const rdr  = res.body.pipeThrough(new TextDecoderStream()).getReader();
        let   buf  = '';
        while (true) {
            const {done, value} = await rdr.read();
            if (done) break;
            buf += value;
            const events = buf.split('\\n\\n');
            buf = events.pop();              // last chunk may be incomplete
            for (const raw of events) {
                const line = raw.replace(/^data: /, '').trim();
                if (!line) continue;
                const evt = JSON.parse(line);
                dispatch(evt);               // update React state by evt.type
            }
        }
    """
    q = SSEQueue()
    from app.core.auth_middleware import current_identity
    from app.core.security import public_error
    officer = current_identity(request).officer

    async def run():
        try:
            await _run_pipeline(req, q, officer)
        except Exception as exc:
            # The officer gets a plain message and a reference; the exception (which can
            # carry an upstream error body, a file path or a project id) stays in the log.
            err = public_error(exc, "stream")
            await q.emit("error", message=err["message"], error_id=err["error_id"])
            await q.close()

    asyncio.create_task(run())

    async def generate():
        async for line in q:
            yield line

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers=_SSE_HEADERS)
