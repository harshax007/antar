"""
Antar — Chat API (POST /api/chat)
Returns the Strategy §3.8 response shape.

Routing (Phase 2): NL → Query Agent. The full LangGraph multi-agent supervisor
(network/profile/forecast/social fan-out) is wired in Phases 4–5 as those agents
land; for now `synthesize` is a single-agent passthrough (per the plan).

LLM vs offline: if QuickML credentials are configured, the LLM selects the template
and composes the answer. Otherwise (local dev before G4, or DEMO_MODE resilience) the
deterministic heuristic router + summary are used — so /api/chat works either way.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.agents.heuristics import is_kannada, is_explain_request
from app.agents.graph import app_graph
from app.services import audit_store
from app.core.settings import settings
from app.core import sessions
from app.core.demo_mode import scripted_query_result
from app.core.rate_limiter import rate_limit
from app.core.auth_middleware import current_identity

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=128)
    text: str = Field(max_length=4000)   # bounded: it is pattern-matched and may reach the model
    lang: str | None = Field(default=None, max_length=8)   # "en" | "kn"; auto-detected if omitted
    deep_think: bool = False


def _llm_available() -> bool:
    from app.services import llm
    return llm.provider() != "none"


def _explain_reply(session_id: str, lang: str) -> str:
    """Replay the previous answer's reasoning trail in plain language (Explain / M9)."""
    steps = sessions.last_reasoning(session_id)
    if not steps:
        return ("ವಿವರಿಸಲು ಹಿಂದಿನ ಉತ್ತರವಿಲ್ಲ." if lang == "kn"
                else "There's no previous answer in this conversation to explain yet.")
    
    trail_parts = []
    for i, s in enumerate(steps):
        detail = s.get('detail')
        if not detail:
            agent = s.get('agent', 'system')
            step = s.get('step', 'process')
            if agent == 'supervisor' and step == 'intent_classification':
                routes = s.get('routes', [])
                detail = f"Classified intent and routed to: {', '.join(routes)}."
            else:
                detail = f"Executed {agent} {step} step."
        trail_parts.append(f"{i+1}) {detail}")
        
    trail = " ".join(trail_parts)
    prefix = "ನಾನು ಈ ಉತ್ತರವನ್ನು ಹೇಗೆ ತಲುಪಿದೆ: " if lang == "kn" else "Here's how I reached that answer: "
    return prefix + trail


@router.post("", dependencies=[Depends(rate_limit(60, 1.0))])
@router.post("/", dependencies=[Depends(rate_limit(60, 1.0))])
async def chat(req: ChatRequest, request: Request) -> dict:
    session_id = req.session_id or f"ses-{uuid.uuid4().hex[:12]}"
    lang = req.lang or ("kn" if is_kannada(req.text) else "en")
    reasoning_id = f"rsn-{uuid.uuid4().hex[:12]}"
    use_llm = _llm_available() and not settings.DEMO_MODE

    from app.obs import trace as _obs
    _obs.start(session_id=session_id, surface="chat", question=req.text, lang=lang, env="appsail")

    sessions.append_user_turn(session_id, req.text, lang)

    # ── Misuse screen (vigil) before any data agent sees the question ────────
    # The stream has refused REJECTED questions for a while; this endpoint (the app's
    # non-stream path, and any direct API caller) answered them. Same screen, same refusal.
    officer_id = current_identity(request).officer
    try:
        from app.agents.vigil_agent import audit_request
        _screen = audit_request(req.text, officer=officer_id)
    except Exception:
        _screen = {}
    if _screen.get("status") == "REJECTED":
        answer = ("Antar ಇದಕ್ಕೆ ಉತ್ತರಿಸುವುದಿಲ್ಲ. ಇದು ಜಾತಿ, ಧರ್ಮ ಅಥವಾ ಸಮುದಾಯದ ಆಧಾರದ ಮೇಲೆ ಜನರ ಬಗ್ಗೆ ಕೇಳುತ್ತದೆ; "
                  "ಪೊಲೀಸ್ ವಿಶ್ಲೇಷಣೆ ಹಾಗೆ ಮಾಡುವಂತಿಲ್ಲ (ಸಂವಿಧಾನದ ಅನುಚ್ಛೇದ 15; BNSS ಸೆಕ್ಷನ್ 173). ಬದಲಿಗೆ ಅಪರಾಧದ ಬಗ್ಗೆ "
                  "ಕೇಳಿ - ಉದಾ: \"ರಾಜಾಜಿನಗರದಲ್ಲಿ ಈ ತಿಂಗಳ ಕಳ್ಳತನ ಪ್ರಕರಣಗಳು\"." if lang == "kn" else
                  "Antar does not answer this. It asks about people by their caste, religion or community, "
                  "which police analysis may not do (Article 15 of the Constitution; BNSS Sec 173, "
                  "non-discriminatory investigation). Ask about the crime instead - for example "
                  "\"theft cases in Rajajinagar this month\" or \"top beats for theft in Rajajinagar\".")
        refusal_trace = [{"step": "vigil", "detail": "; ".join(_screen.get("flags") or []) or "prohibited targeting",
                          "citation": _screen.get("bnss_citation")}]
        try:
            audit_store.record_ai_reasoning(
                officer=officer_id, session_id=session_id, user_text=req.text, answer=answer,
                agents_used=["vigil"], citations=[], reasoning_id=reasoning_id, reasoning_trace=refusal_trace)
        except Exception:
            pass
        sessions.append_assistant_turn(session_id, answer, lang, "REFUSED", reasoning_id, refusal_trace)
        return {"answer": answer, "lang": lang, "citations": [], "agents_used": ["vigil"],
                "visuals": {}, "brain_hits": [], "reasoning_id": reasoning_id, "reasoning": refusal_trace,
                "suggested": [], "session_id": session_id, "template_id": "REFUSED", "mode": "refusal"}

    # ── Explain capability (M9): "why did you say that?" replays the last reasoning ──
    # `has_previous`: with nothing answered yet, a question that merely contains
    # "why" or "ಹೇಗೆ" is a real question, not a request to justify an earlier answer.
    if is_explain_request(req.text, sessions.has_assistant_turn(session_id)):
        answer = _explain_reply(session_id, lang)
        sessions.append_assistant_turn(session_id, answer, lang, "EXPLAIN", reasoning_id,
                                       [{"step": "explain", "detail": "Replayed the previous answer's reasoning."}])
        return {"answer": answer, "lang": lang, "citations": [], "agents_used": ["explain"],
                "visuals": {}, "brain_hits": [], "reasoning_id": reasoning_id,
                "suggested": [], "session_id": session_id, "template_id": "EXPLAIN",
                "mode": "llm" if use_llm else "offline"}

    history = sessions.recent_turns(session_id)
    actual_mode = "offline"
    result = None
    if settings.DEMO_MODE:
        demo_res = await scripted_query_result(req.text, lang=lang, session_id=session_id, history=history)
        if demo_res is not None:
            actual_mode = "demo"
            result = {
                "results": {"query": demo_res},
                "final_answer": demo_res.get("answer", ""),
                "citations": demo_res.get("citations", []),
                "reasoning": demo_res.get("reasoning", []),
                "routes": ["query"],
                "visuals": {},
                "brain_hits": []
            }
    if result is None and use_llm:
        from app.agents.heuristics import heuristic_select
        hs_res = await heuristic_select(req.text, lang, history=history)
        from app.agents.case_answer import wants_case
        from app.agents.briefing import wants_briefing
        if hs_res.get("template_id") == "NONE" and not req.deep_think and not wants_case(req.text) \
                and not wants_briefing(req.text):
            answer = "I can answer questions about crimes, suspects, trends, hotspots, and demographics." if lang == "en" else "ನಾನು ಅಪರಾಧಗಳು, ಶಂಕಿತರು, ಪ್ರವೃತ್ತಿಗಳು, ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳು ಮತ್ತು ಜನಸಂಖ್ಯಾಶಾಸ್ತ್ರದ ಬಗ್ಗೆ ಪ್ರಶ್ನೆಗಳಿಗೆ ಉತ್ತರಿಸಬಲ್ಲೆ."
            sessions.append_assistant_turn(session_id, answer, lang, "NONE", reasoning_id, [{"step": "guardrail", "detail": "Intercepted off-topic query."}])
            return {"answer": answer, "lang": lang, "citations": [], "agents_used": ["guardrail"],
                    "visuals": {}, "brain_hits": [], "reasoning_id": reasoning_id,
                    "suggested": [], "session_id": session_id, "template_id": "NONE",
                    "mode": "guardrail"}

        try:
            initial_state = {
                "session_id": session_id,
                "user_text": req.text,
                "lang": lang,
                "use_llm": True,
                "results": {},
                "citations": [],
                "brain_hits": [],
                "reasoning": [],
                "actions": [],
                "visuals": {},
                "routes": [],
            }
            final_state = await app_graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": session_id}}
            )
            result = final_state
            
            # "llm" only if the answer was actually written by the LLM
            query = result.get("results", {}).get("query", {})
            actual_mode = "llm" if query.get("llm_answer") else "offline"
        except Exception as e:
            print(f"LLM path failed ({e}); falling back to offline for this turn")
            result = None
    if result is None:
        initial_state = {
            "session_id": session_id,
            "user_text": req.text,
            "lang": lang,
            "use_llm": False,
            "results": {},
            "citations": [],
            "brain_hits": [],
            "reasoning": [],
            "actions": [],
            "visuals": {},
            "routes": [],
        }
        final_state = await app_graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": session_id}}
        )
        result = final_state

    query = result.get("results", {}).get("query", {})
    template_id = query.get("template_id", "NONE")
    
    sessions.append_assistant_turn(session_id, result.get("final_answer", ""), lang,
                                   template_id, reasoning_id,
                                   result.get("reasoning", []))

    agents_used = [r.lower() for r in result.get("routes", ["query"])]
    citations = result.get("citations", [])
    answer = result.get("final_answer", "")
    # Antar's identity: the same shaping the stream applies, before the audit record, so
    # the hash-chained audit stores exactly what the officer saw.
    from app.core.antar_identity import present as _present
    identity = _present(answer, query, lang)
    answer = identity["text"]

    _obs.set_context(template_id=template_id, params=query.get("params"),
                     rows=query.get("rows"), citations=citations, mode=actual_mode)
    from app.obs import flags as _obsf
    _obsf.from_query_result(_obs.current().d["trace_id"] if _obs.current() else "orphan", query)

    # A template ran and matched nothing → the answer window shows ONLY the
    # answer + Why? trail (no CTAs, banners, visuals or follow-up chips).
    no_results = not query.get("rows") and template_id not in ("CLARIFY", "NONE")
    if no_results:
        citations = []
        result = {**result, "visuals": {}, "brain_hits": [], "actions": []}

    # Phase P15: Hash into the immutable audit ledger
    audit_store.record_ai_reasoning(
        officer=current_identity(request).officer,
        session_id=session_id,
        user_text=req.text,
        answer=answer,
        agents_used=agents_used,
        citations=citations,
        reasoning_id=reasoning_id,
        reasoning_trace=result.get("reasoning", [])
    )

    _obs.close(answer=answer, reasoning_id=reasoning_id,
               prompt_version=getattr(settings, "PROMPT_VERSION", "v1"))

    from app.agents.layout_composer import build_layout
    from app.agents.layout_composer import with_identity
    layout = (with_identity(build_layout(answer, query, result.get("results", {})), identity)
              if not no_results else None)
    from app.agents.layout_composer import build_custody
    custody = build_custody(query, mode=actual_mode) if not no_results else None

    raw_ret = {
        "answer": answer,
        "lang": lang,
        "layout": layout,
        "custody": custody,
        "citations": citations,
        "agents_used": agents_used,
        "visuals": result.get("visuals", {}),
        "brain_hits": result.get("brain_hits", []),
        "reasoning_id": reasoning_id,
        "reasoning": result.get("reasoning", []),
        "no_results": no_results,
        "suggested": [] if no_results else query.get("suggested_followups", []),
        "suspects": [] if no_results else query.get("suspects", []),
        "actions": result.get("actions", []),
        "confidence": result.get("confidence", 0.0),
        "sources": result.get("sources", []),
        "session_id": session_id,
        "template_id": template_id,
        "mode": actual_mode,
        "demo_cache_key": query.get("demo_cache_key"),
        "demo_cache_hit": query.get("demo_cache_hit", False),
    }
    from app.core.output_formatter import format_agent_response
    officer_id = current_identity(request).officer
    return format_agent_response(raw_ret, mode=actual_mode, officer_id=officer_id, lang=lang)
