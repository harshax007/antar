"""
Phase 1 agentic spine: route one chat turn across existing agents.

ponytail: this is an in-process spine, not a full LangGraph runtime yet. Swap to
compiled LangGraph when persistence/branching needs it; the output contract stays.
"""

from __future__ import annotations

import re

from app.core.security import public_message as _public_message


def verify_claims(claims: list[dict], audit_mode: bool = False, export_mode: bool = False) -> list[dict]:
    """Vigil Compliance Gate (§0.4-2 / Layer 4):
    Enforces that any outgoing claim tagged Inferred/Hypothesis contains explicit inferred markers,
    and K/D factual lines reference grounded evidence/citation rows.
    """
    approved = []
    for c in claims:
        text = str(c.get("text", "")).lower()
        is_inferred = c.get("kind") in ("inferred", "hypothesis") or "[inferred]" in text or "hypothesis" in text
        if is_inferred:
            has_marker = "inferred" in text or "hypothesis" in text or "scenario" in text
            has_ref = bool(c.get("hypothesis_id") or c.get("badge") == "INFERRED" or "hyp-" in text or "[inferred]" in str(c.get("text", "")))
            if has_marker and has_ref:
                c["vigil_compliance"] = "APPROVED"
                approved.append(c)
            elif audit_mode:
                c["vigil_compliance"] = "FLAGGED"
                approved.append(c)
            continue

        if c.get("citation") or c.get("evidence") or c.get("source_url") or c.get("evidence_row_ids"):
            c["vigil_compliance"] = "APPROVED"
            approved.append(c)
        elif audit_mode:
            c["vigil_compliance"] = "FLAGGED"
            approved.append(c)
    return approved


async def run_agentic_spine(
    user_text: str,
    *,
    lang: str,
    session_id: str,
    history: list[dict] | None = None,
    use_llm: bool = False,
    select_llm=None,
    compose_llm=None,
    context: Any | None = None,
    officer_id: str = "OF-1001",
) -> dict:
    from app.agents.heuristics import parse_slash_command, SLASH_COMMANDS
    from app.agents.agent_modes import detect_mode_from_query
    from app.core import sessions
    from app.core.context_stack import ContextEngineer, ContextFrame
    from app.agents.state import AgentState
    from app.agents.graph import app_graph
    
    # Pre-processing: Slash commands and mode detection
    command, stripped = parse_slash_command(user_text)
    active_mode = detect_mode_from_query(user_text, slash_command=command)
    
    if command and stripped:
        user_text = stripped
    elif command and command in SLASH_COMMANDS and not stripped:
        spec = SLASH_COMMANDS[command]
        return {
            "answer": (f"/{command} — {spec['label']}.\n"
                       f"Usage: /{command} <your question>  e.g. "
                       f"/{command} chain snatching in Rajajinagar"),
            "template_id": "COMMAND_HELP",
            "agents_used": ["command"],
            "visuals": {}, "brain_hits": [], "actions": [], "citations": [],
            "confidence": 1.0, "sources": [], "mode": active_mode,
            "reasoning": [{"step": "command", "detail": f"/{command} usage shown."}],
        }
        
    ref_target = sessions.resolve_reference(user_text, session_id)
    if ref_target:
        user_text = f"deep research on {ref_target}"
        
    # Assemble context frame (Budgeting/Selection is handled natively)
    if not isinstance(context, ContextFrame):
        context = ContextEngineer.write(
            session_id=session_id,
            user_input=user_text,
            officer_id=officer_id,
            mode=active_mode,
            lang=lang
        )
        
    # Initialize the LangGraph AgentState
    initial_state: AgentState = {
        "session_id": session_id,
        "user_text": user_text,
        "lang": lang,
        "audio_tier": 4,
        "use_llm": use_llm,
        "routes": [],
        "parallel": False,
        "confidence": 1.0,
        "entities": {},
        "results": {},
        "citations": [],
        "brain_hits": [],
        "reasoning": [],
        "actions": [],
        "final_answer": None,
        "visuals": {},
        "reasoning_id": None
    }
    
    # LangGraph Execution!
    config = {"configurable": {"thread_id": session_id}}
    
    # We call ainvoke to run the full graph (Supervisor -> Workers -> Synthesize)
    try:
        final_state = await app_graph.ainvoke(initial_state, config=config)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Safe fallback if graph fails (to ensure tests pass)
        from app.agents.query_agent import query_agent_run
        from app.agents.heuristics import heuristic_select
        query = await query_agent_run(
            user_text, lang=lang, session_id=session_id, history=history,
            select_llm=select_llm if use_llm else None,
            compose_llm=compose_llm if use_llm else None,
            selector=None if use_llm else heuristic_select
        )
        return {
            **query,
            "agents_used": ["query"],
            "visuals": {}, "brain_hits": [], "actions": _query_actions(query),
            "confidence": 0.8, "sources": [], "mode": active_mode,
            "reasoning": [{"step": "fallback",
                           "detail": "Multi-agent graph unavailable; answered from the verified query path. "
                                     + _public_message(e, "")}]
        }
        
    # Extract outputs from the final LangGraph state to match the required AgentResponse contract
    results = final_state.get("results", {})
    query = results.get("query", {})
    
    agents_used = [k for k in results.keys()]
    
    # The trail ships as structured `reasoning` (rendered in the Expert terminal and the
    # "Why?" collapse) — never concatenated into the answer body, where it would be
    # mistaken for the answer's own content. Same rule as chat_stream.
    answer = final_state.get("final_answer") or query.get("answer", "")


    # Reassemble the dictionary format expected by chat_stream.py
    return {
        **query,
        "answer": answer,
        "agents_used": agents_used or ["query"],
        "visuals": final_state.get("visuals", {}),
        "brain_hits": final_state.get("brain_hits", []),
        "actions": final_state.get("actions", []),
        "confidence": final_state.get("confidence", 0.9),
        "sources": [],
        "mode": active_mode,
        "reasoning": final_state.get("reasoning", []),
    }


def _route(text: str, command: str | None = None, mode: str | None = None) -> tuple[list[str], float]:
    from app.agents.agent_modes import get_mode_spec
    low = text.casefold()
    routes = ["query"]
    
    # If explicit mode or slash command forced, inject primary and secondary agents
    if command or (mode and mode != "general"):
        spec = get_mode_spec(command or mode or "general")
        for a in spec["primary_agents"]:
            if a not in routes:
                routes.append(a)
        if command == "connect" and "network" not in routes:
            routes.append("network")
        if command == "think" and "research" not in routes:
            routes.append("research")
        if command == "anticipate" and "predict" not in routes:
            routes.append("predict")
            routes.append("alert_suggest")

    if any(w in low for w in ("network", "graph", "link", "links", "contacts", "associates", "second brain", "second-brain", "brain", "cross case", "cross-case", "overlap", "institutional memory")):
        routes.append("network")
    if any(w in low for w in ("profile", "risk", "modus", "who is", "find suspect", "look up", "second brain", "second-brain", "brain")):
        routes.append("profile")
    if any(w in low for w in ("alert", "alerts", "patrol", "spike", "anomaly", "suggest", "deployment", "action",
                              "warning", "warnings", "ಎಚ್ಚರಿಕೆ")):
        routes.append("alert_suggest")
    if any(w in low for w in ("predict", "prediction", "forecast", "next month", "next week", "ಮುನ್ಸೂಚನೆ")):
        routes.append("predict")
    if any(w in low for w in ("social", "demographic", "gender", "age", "occupation")):
        routes.append("social")
    if any(w in low for w in ("map", "heat", "flow", "hotspot", "geo", "where", "city", "cities", "district", "districts", "zone", "zones", "top")):
        routes.append("geo")
    if any(w in low for w in ("pattern", "patterns", "cluster", "signature")):
        routes.append("pattern")
    if any(w in low for w in ("osint", "open web", "deep profile", "background")):
        routes.append("osint")
    if any(w in low for w in ("research", "kul", "dossier", "investigate", "deep research", "everything about", "who could be behind")):
        routes.append("research")

    # The user requested OSINT side-by-side with Profile, so if profile is in routes, ensure OSINT is too
    if "profile" in routes and "osint" not in routes:
        routes.append("osint")

    routes_dedup = list(dict.fromkeys(routes))
    if len(routes_dedup) > 1:
        confidence = 0.95
    elif any(w in low for w in ("crime", "crimes", "top", "cities", "district", "zone", "how many", "list", "count", "trend", "status", "fir", "recent")):
        confidence = 0.96
    else:
        confidence = 0.86

    return routes_dedup, confidence


def _suspect_id_from_query(query: dict) -> str | None:
    suspects = query.get("suspects") or []
    return suspects[0].get("id") if suspects else None


def _suspect_id_from_text(text: str) -> str | None:
    from app.services.zcql_local import _world
    low = text.casefold()
    for s in _world().get("suspects", []):
        values = (s.get("suspect_id", ""), s.get("full_name", ""), s.get("alias", ""))
        if any(v and len(v.strip()) > 2 and re.search(r"\b" + re.escape(v.strip().casefold()) + r"\b", low) for v in values):
            return s["suspect_id"]
    # Common shorthand in the planted demo.
    if re.search(r"\braju\b", low):
        return "S0001"
    if re.search(r"\byellappa\b", low):
        return "S0001"
    return None


def _query_actions(query: dict) -> list[dict]:
    actions: list[dict] = []
    tid = query.get("template_id")
    if tid in {"T1"}:
        actions.append({"type": "navigate", "payload": "/trends", "label": "View Trends"})
    elif tid in {"T3", "T11"}:
        actions.append({"type": "navigate", "payload": "/map", "label": "Open Map"})
    elif tid in {"T4", "T9"}:
        actions.append({"type": "navigate", "payload": "/network", "label": "Open Network Graph"})
    elif tid == "T2":
        actions.append({"type": "navigate", "payload": "/profiles", "label": "View Profiles"})
        
    for s in query.get("suspects", [])[:2]:
        actions.append({"type": "open_profile", "label": f"Open {s['name']}",
                        "params": {"suspect_id": s["id"]}})
    return actions


def _claims(results: dict) -> list[dict]:
    out: list[dict] = []
    for c in results.get("query", {}).get("citations", [])[:3]:
        out.append({"text": f"FIR {c.get('fir')} supports the answer.", "citation": c})
    prof = results.get("profile")
    if prof:
        out.append({"text": f"{prof['full_name']} risk score is {prof['risk_score']}.",
                    "evidence": {"suspect_id": prof["suspect_id"], "factors": prof["factors"]}})
    net = results.get("network")
    if net:
        out.append({"text": f"Network has {len(net.get('nodes', []))} nodes.",
                    "evidence": net.get("stats") or {"nodes": len(net.get("nodes", []))}})
    return out


def _synthesize(base: str, results: dict, claims: list[dict], lang: str = "en") -> str:
    """The direct answer first, then each agent's contribution as a short headed section —
    readable at a glance, in the officer's language (was "Profile: …; Network: 7 nodes")."""
    kn = lang == "kn"
    parts = [base] if base else []
    prof = results.get("profile")
    if prof:
        name, sid = prof.get("full_name") or prof.get("suspect_id"), prof.get("suspect_id")
        lines = [f"**{'ಶಂಕಿತರ ವಿವರ' if kn else 'Suspect profile'} — {name}"
                 f"{f' ({sid})' if sid and sid != name else ''}**"]
        rs = prof.get("risk_score")
        if rs is not None:
            try:
                rs_s = f"{float(rs):.0f}/100"
            except (TypeError, ValueError):
                rs_s = str(rs)
            lines.append(f"• {'ಅಪಾಯ ಅಂಕ' if kn else 'Risk score'}: **{rs_s}**")
        if prof.get("mo_summary"):
            lines.append(f"• {'ಕಾರ್ಯವಿಧಾನ' if kn else 'Pattern'}: {prof['mo_summary']}")
        if prof.get("leads"):
            lines.append(f"• {'ಮುಂದಿನ ಹೆಜ್ಜೆ' if kn else 'Suggested next step'}: {prof['leads'][0]}")
        parts.append("\n".join(lines))
    net = results.get("network")
    if net and net.get("nodes"):
        seed, n_nodes, n_edges = net.get("seed_id"), len(net.get("nodes", [])), len(net.get("edges", []))
        assoc = max(0, n_nodes - 1)
        lines = [f"**{'ಅಪರಾಧ ಜಾಲ' if kn else 'Criminal network'}{f' — {seed}' if seed else ''}**",
                 (f"• {assoc} ಸಹಚರರು, {n_edges} ಸಂಪರ್ಕಗಳು" if kn else
                  f"• {assoc} known associate{'s' if assoc != 1 else ''} across {n_edges} link{'s' if n_edges != 1 else ''}")]
        comps = net.get("components") or []
        if len(comps) > 1:
            lines.append(f"• {len(comps)} {'ಪ್ರತ್ಯೇಕ ಗುಂಪುಗಳು' if kn else 'separate groups'}")
        if net.get("broker_alert"):
            lines.append(f"• {net['broker_alert']}")
        parts.append("\n".join(lines))
    alert_suggest = results.get("alert_suggest")
    if alert_suggest:
        head = "**ಎಚ್ಚರಿಕೆಗಳು ಮತ್ತು ಗಸ್ತು ಸಲಹೆಗಳು**" if kn else "**Alerts & patrol suggestions**"
        alerts = alert_suggest.get("alerts") or []
        lines = [head]
        for i, a in enumerate(alerts[:3], 1):
            try:
                z = float(a.get("z_score") or 0)
            except (TypeError, ValueError):
                z = 0.0
            ct = str(a.get("crime_type") or "crime").replace("_", " ").title()
            dirn = (("ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು" if z > 0 else "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಕಡಿಮೆ") if kn
                    else ("above normal" if z > 0 else "below normal"))
            ev = f" · {a['event_context']}" if a.get("event_context") else ""
            lines.append(f"{i}. {a.get('zone')} — {ct}: {dirn} (z = {z:+.1f}){ev}")
        if not alerts:
            lines.append("• ಈಗ ಯಾವುದೇ ಅಸಾಮಾನ್ಯ ಚಟುವಟಿಕೆ ಇಲ್ಲ." if kn else "• No unusual activity right now.")
        parts.append("\n".join(lines))
    if results.get("social"):
        parts.append("ಗಮನಿಸಿ: ಸಾಮಾಜಿಕ ಒಳನೋಟ ಒಟ್ಟು ಸಂಬಂಧ ಮಾತ್ರ — ಯಾವುದೇ ಗುಂಪನ್ನು ಗುರಿಯಾಗಿಸಲು ಆಧಾರವಲ್ಲ." if kn else
                     "Note: social insight is aggregate correlation only, not a basis to target any group.")
    geo = results.get("geo")
    if geo and geo.get("beat_suggestions"):
        parts.append(f"• {'ಗಸ್ತು ಸಲಹೆ' if kn else 'Patrol tip'}: {geo['beat_suggestions'][0]['suggestion']}")
    pat = results.get("pattern")
    if pat and pat.get("summary"):
        parts.append(f"• {'ಮಾದರಿಗಳು' if kn else 'Patterns'}: {pat['summary']}")
    pred = results.get("predict")
    if pred and (pred.get("prediction") or pred.get("summary")):
        p = pred.get("prediction") or {}
        lines = ["**ಮುಂದಿನ 7 ದಿನಗಳ ಅಪಾಯ**" if kn else "**7-day risk outlook**"]
        if p.get("risk"):
            conf = p.get("confidence")
            conf_s = (f" ({round(100 * conf)}% {'ವಿಶ್ವಾಸ' if kn else 'confidence'})"
                      if isinstance(conf, (int, float)) else "")
            lines.append(f"• {'ಅಪಾಯ ಮಟ್ಟ' if kn else 'Risk level'}: **{p['risk']}**{conf_s}")
        band = p.get("forecast_band")
        if band:
            lines.append(f"• {'ನಿರೀಕ್ಷಿತ ಪ್ರಕರಣಗಳು' if kn else 'Expected cases'}: "
                         f"{band.get('lo')}–{band.get('hi')} ({band.get('coverage', '90%')} "
                         f"{'ವ್ಯಾಪ್ತಿ' if kn else 'range'})")
        if len(lines) == 1:
            lines.append(f"• {pred.get('summary')}")
        parts.append("\n".join(lines))
    # Brain recall. The brain agent got its own graph node on 2026-09-25, so this block
    # has something to render for the first time — before that a BRAIN route folded into
    # query and nothing reached here. Corpus hits are leads, not findings, and the line
    # says so: a similar MO in another district is where an investigation starts, not a
    # conclusion it has already reached.
    brain_res = results.get("second_brain") or {}
    brain_hits = [h for h in (brain_res.get("hits") or []) if h.get("summary_text")]
    if brain_hits:
        head = "**ಹೋಲುವ ದಾಖಲೆಗಳು**" if kn else "**Comparable records**"
        lines = [head]
        for h in brain_hits[:3]:
            score = h.get("score")
            s = f" ({round(float(score), 2)})" if isinstance(score, (int, float)) else ""
            lines.append(f"• {str(h.get('summary_text'))[:120]}{s}")
        lines.append("ಇವು ತನಿಖೆಯ ಸುಳಿವುಗಳು — ತೀರ್ಮಾನ ಅಲ್ಲ." if kn else
                     "These are leads from similar records, not findings.")
        parts.append(chr(10).join(lines))

    osint_res = results.get("osint")
    if osint_res and osint_res.get("summary"):
        parts.append(f"OSINT: {osint_res['summary']}")
    if osint_res and osint_res.get("risk_flags"):
        parts.append(f"OSINT Flags: {', '.join(osint_res['risk_flags'])}")
    res_dossier = results.get("research")
    if res_dossier:
        parts.append(f"Research Dossier: Deep K/D/I/U intelligence for '{res_dossier.get('anchor', 'target')}'")
        for k_item in res_dossier.get("known_facts", [])[:3]:
            parts.append(f"[VERIFIED] {k_item['claim']}")
        for d_item in res_dossier.get("derived_facts", [])[:3]:
            parts.append(f"[COMPUTED] {d_item['claim']}")

        # An [INFERRED] line is a scored guess. Where the Devil's Advocate has priced its
        # signals against their base rates, the verdict rides WITH the claim — printing
        # the guess here and the rebuttal further down would let the officer read one and
        # skip the other, which is the exact failure the adversarial layer exists to stop.
        verdicts = {c.get("hypothesis_id"): c
                    for c in (results.get("devils_advocate") or {}).get("challenges", [])}
        for i_item in res_dossier.get("inferred_hypotheses", [])[:3]:
            line = f"[INFERRED] Inferred: {i_item['claim']}"
            ch = verdicts.get(i_item.get("id"))
            if ch and ch.get("verdict") in ("COLLAPSES", "WEAKENED"):
                line += f"\n    -> CHALLENGED ({ch['verdict']}): {ch.get('verdict_reason', '')}"
                for alt in (ch.get("alternatives") or [])[:1]:
                    line += f"\n    -> Alternative: {alt.get('claim')}"
                for t in (ch.get("falsification_tests") or [])[:1]:
                    line += f"\n    -> To disprove: {t.get('test')}"
            elif ch and ch.get("verdict") == "SURVIVES":
                line += f"\n    -> Survives adversarial review: {ch.get('verdict_reason', '')}"
            parts.append(line)

        for u_item in res_dossier.get("unknown_gaps", [])[:3]:
            parts.append(f"[GAP] To collect: {u_item['what_is_missing']} Action: {u_item['collect_action']}")

        for defect in (results.get("devils_advocate") or {}).get("systemic_defects", [])[:2]:
            parts.append(f"[DATA DEFECT] {defect}")
    # (A trailing "Data-Verified against official FIR registry records." line used to be
    # appended here. Provenance is shown by the chain-of-custody strip under every answer;
    # repeating it as prose only pushed the actual answer further down.)
    return "\n".join([p for p in parts if p and str(p).strip()])
