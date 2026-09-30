"""
Antar — Standardized Agent & System Response Schemas
======================================================
Enforces a uniform, explainable, and UI-ready response envelope across all
specialist agents, multi-agent synthesis, and API streaming events.
"""

from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Grounded evidence supporting a claim or insight."""
    text: str = Field(description="Sentence explaining the evidence connection")
    citation: dict[str, Any] | None = Field(default=None, description="Structured citation (FIR, row data)")
    source: str | None = Field(default="official_db", description="Source origin: official_db, second_brain, osint, synthetic_ledger")
    row_id: str | None = Field(default=None, description="Exact database row ID or FIR number for audit trace")


class ReasoningStep(BaseModel):
    """Auditable step in the agent reasoning chain (Layer 4 Explainable AI)."""
    agent: str = Field(description="Name of the agent or component performing the step")
    step: str = Field(description="Short title or classification of the step")
    detail: str = Field(description="Detailed explanation of findings or decisions made")
    ms: float | None = Field(default=None, description="Execution time in milliseconds")


class ActionItem(BaseModel):
    """Interactive action button or navigation trigger for the frontend UI."""
    type: str = Field(description="Action type: navigate, open_profile, show_network, view_on_map, open_workspace, open_alerts")
    label: str = Field(description="Human-readable label shown on the button chip")
    payload: str | None = Field(default=None, description="Target URL path or route payload")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters needed when action is executed")


class WorkspaceSummary(BaseModel):
    """Metadata when a long-running background task or intelligence product is compiled."""
    job_id: str
    type: str
    title: str
    status: Literal["queued", "running", "done", "failed"] = "done"
    summary: str
    result_url: str | None = None


class AgentResponse(BaseModel):
    """Standardized response envelope returned by single agents and orchestrator synthesis."""
    answer: str = Field(description="Human-readable response formatted in Markdown (or Kannada if requested)")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Calibrated confidence score [0, 1]")
    mode: str = Field(default="general", description="Agenda mode (think/connect/anticipate/general) or execution engine mode (offline/llm)")
    knowledge_state: Literal["known", "derived", "inferred", "gap", "synthesized"] = Field(default="synthesized")
    
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Explicit grounding citations")
    reasoning_steps: list[ReasoningStep] = Field(default_factory=list, description="Auditable reasoning chain")
    actions: list[ActionItem] = Field(default_factory=list, description="Recommended UI interactive chips")
    suggested_queries: list[str] = Field(default_factory=list, description="Next analytical questions to ask")
    
    visuals: dict[str, Any] = Field(default_factory=dict, description="Visual data payloads (graph, map, profile, predict, alerts)")
    brain_hits: list[dict[str, Any]] = Field(default_factory=list, description="Second brain cross-case semantic links found")
    workspace_item: WorkspaceSummary | None = Field(default=None, description="Workspace job info if a task was spawned/completed")
    
    meta: dict[str, Any] = Field(default_factory=dict, description="Execution metadata (agents_used, latency_ms, tokens)")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict compatible with existing API and SSE streaming pipeline."""
        return self.model_dump(mode="json", exclude_none=True)
