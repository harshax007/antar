"""
Antar — Output Formatter & UI Response Standardization
======================================================
Transforms raw agent outputs into standardized `AgentResponse` payloads,
ensuring clean action chips, grounded citations, reasoning transparency,
and next-turn completed background job banners (Option B notification flow).
"""

from __future__ import annotations
from typing import Any
from app.agents.response_schema import AgentResponse, ActionItem, EvidenceItem, ReasoningStep, WorkspaceSummary
from app.api.jobs import get_unnotified_completed_jobs


def format_agent_response(
    raw_output: dict[str, Any] | str,
    mode: str = "general",
    officer_id: str = "OF-1001",
    lang: str = "en",
) -> dict[str, Any]:
    """Standardize raw dicts/strings into UI-ready payloads with next-turn job alerts."""
    if isinstance(raw_output, str):
        raw_output = {"answer": raw_output}
        
    answer = raw_output.get("answer", "")
    confidence = float(raw_output.get("confidence", 0.9))
    actions = raw_output.get("actions", [])
    visuals = raw_output.get("visuals", {})
    brain_hits = raw_output.get("brain_hits", [])
    reasoning = raw_output.get("reasoning", [])
    citations = raw_output.get("citations", [])
    
    # 1. Check if any background jobs completed recently and attach alert (Option B)
    completed_jobs = get_unnotified_completed_jobs(officer_id)
    workspace_item = None
    
    if completed_jobs:
        latest = completed_jobs[0]
        banner_title = "ಬ್ಯಾಕ್‌ಗ್ರೌಂಡ್ ಕೆಲಸ ಪೂರ್ಣಗೊಂಡಿದೆ" if lang == "kn" else "Background Investigation Completed"
        banner_msg = f"\n\n> [!TIP]\n> **{banner_title}**: `{latest.get('type')}` on **{latest.get('target')}** finished.\n> *{latest.get('summary')}*\n> [Open in Workspace](#/workspace/{latest['job_id']})"
        answer = f"{answer}{banner_msg}"
        
        workspace_item = WorkspaceSummary(
            job_id=latest["job_id"],
            type=str(latest.get("type", "job")),
            title=str(latest.get("target") or latest.get("type")),
            status="done",
            summary=str(latest.get("summary", "")),
            result_url=f"/workspace/{latest['job_id']}"
        )
        
        # Ensure 'open_workspace' chip exists
        if not any(isinstance(a, dict) and a.get("type") == "open_workspace" for a in actions):
            actions.append({
                "type": "open_workspace",
                "label": "Open in Workspace",
                "payload": f"/workspace/{latest['job_id']}",
                "params": {"item_id": latest["job_id"]}
            })

    # 2. Normalize actions into ActionItem
    norm_actions = []
    for a in actions:
        if isinstance(a, dict):
            norm_actions.append(ActionItem(
                type=str(a.get("type", "navigate")),
                label=str(a.get("label", "Action")),
                payload=a.get("payload"),
                params=a.get("params", {})
            ))
        elif isinstance(a, ActionItem):
            norm_actions.append(a)

    # 3. Normalize reasoning into ReasoningStep
    norm_reasoning = []
    for r in reasoning:
        if isinstance(r, dict):
            norm_reasoning.append(ReasoningStep(
                agent=str(r.get("agent", mode)),
                step=str(r.get("step", "reason")),
                detail=str(r.get("detail", r.get("step", ""))),
                ms=r.get("ms")
            ))
        elif isinstance(r, ReasoningStep):
            norm_reasoning.append(r)

    # 4. Normalize citations into EvidenceItem
    norm_evidence = []
    for c in citations:
        if isinstance(c, dict):
            norm_evidence.append(EvidenceItem(
                text=str(c.get("text", c.get("claim", ""))),
                citation=c,
                source=str(c.get("source", "official_db")),
                row_id=c.get("row_id") or c.get("id")
            ))
        elif isinstance(c, str):
            norm_evidence.append(EvidenceItem(text=c, source="official_db"))

    response_obj = AgentResponse(
        answer=answer,
        confidence=confidence,
        mode=mode,
        evidence=norm_evidence,
        reasoning_steps=norm_reasoning,
        actions=norm_actions,
        visuals=visuals,
        brain_hits=brain_hits,
        workspace_item=workspace_item,
        meta={"mode": mode, "officer_id": officer_id}
    )
    
    out = raw_output.copy()
    out.update(response_obj.to_dict())
    return out
