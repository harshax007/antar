"""
Antar — Context Engineering Stack (Write · Select · Compress · Isolate)
========================================================================
Implements the 4-step context engineering framework across all modes
(Think · Connect · Anticipate) calibrated for Qwen 3.6 Vision & GLM-4.7-Flash.

Token budget allocation (16,000 token working ceiling):
  • Instructions:       1,200 tokens max
  • Retrieved Facts:    6,000 tokens max (RAG rows, citations, brain hits)
  • Short-Term Notes:   2,500 tokens max (recent turns, topic thread, entity state)
  • Long-Term Memory:   1,000 tokens max (officer preferences, past conclusions)
  • Tools & Format:     1,000 tokens max (available tools, output schema envelope)
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any

from app.agents.agent_modes import get_mode_spec, detect_mode_from_query


# Estimated token counting utility (~4 chars per token for English/JSON, ~2.5 chars for Kannada)
def estimate_tokens(text: str | dict | list) -> int:
    if not text:
        return 0
    if isinstance(text, (dict, list)):
        raw = json.dumps(text, ensure_ascii=False)
    else:
        raw = str(text)
    # Simple, fast estimation that is conservative enough for budget gating
    return max(1, len(raw) // 3)


@dataclass
class ContextFrame:
    """Structured context payload injected cleanly into specialized agents."""
    instructions: str
    user_input: str
    retrieved_facts: list[dict[str, Any]] = field(default_factory=list)
    available_tools: list[dict[str, Any]] = field(default_factory=list)
    short_term_notes: list[dict[str, Any]] = field(default_factory=list)
    long_term_memory: dict[str, Any] = field(default_factory=dict)
    output_format: dict[str, Any] = field(default_factory=dict)
    mode: str = "general"
    officer_id: str = "OF-1001"
    session_id: str = "default"
    lang: str = "en"
    budget: dict[str, int] = field(default_factory=lambda: {
        "instructions": 1200,
        "retrieved_facts": 6000,
        "short_term_notes": 2500,
        "long_term_memory": 1000,
        "output_format": 1000,
        "total_ceiling": 16000,
    })

    def to_prompt_string(self) -> str:
        """Render the isolated, compressed ContextFrame into a structured LLM prompt block."""
        parts = []
        if self.instructions:
            parts.append(f"### OPERATIONAL INSTRUCTIONS ({self.mode.upper()} MODE)\n{self.instructions}")
        
        if self.long_term_memory:
            mem_str = json.dumps(self.long_term_memory, ensure_ascii=False, indent=2)
            parts.append(f"### OFFICER LONG-TERM MEMORY & CONCLUSIONS\n{mem_str}")
            
        if self.short_term_notes:
            notes_str = json.dumps(self.short_term_notes, ensure_ascii=False, indent=2)
            parts.append(f"### SHORT-TERM CONTEXT & RECENT TURNS\n{notes_str}")
            
        if self.retrieved_facts:
            facts_str = json.dumps(self.retrieved_facts, ensure_ascii=False, indent=2)
            parts.append(f"### RETRIEVED GROUNDED FACTS & EVIDENCE\n{facts_str}")
            
        if self.available_tools:
            tools_str = json.dumps([t.get("name", str(t)) for t in self.available_tools], ensure_ascii=False)
            parts.append(f"### AVAILABLE AGENT TOOLS\n{tools_str}")
            
        parts.append(f"### CURRENT USER QUERY (Language: {self.lang})\n{self.user_input}")
        
        if self.output_format:
            fmt_str = json.dumps(self.output_format, ensure_ascii=False)
            parts.append(f"### REQUIRED OUTPUT ENVELOPE (Strict JSON/Structure)\n{fmt_str}")
            
        return "\n\n".join(parts)


class ContextEngineer:
    """Orchestrates the 4-Step Context Engineering Pipeline (Write -> Select -> Compress -> Isolate)."""

    @classmethod
    def write(
        cls,
        session_id: str,
        user_input: str,
        officer_id: str = "OF-1001",
        mode: str | None = None,
        lang: str = "en",
        raw_facts: list[dict[str, Any]] | None = None,
    ) -> ContextFrame:
        """Step 1: WRITE — assemble raw context from all session, memory, and retrieval sources."""
        from app.core import sessions
        
        # Detect mode if not explicitly forced
        active_mode = mode or detect_mode_from_query(user_input)
        mode_spec = get_mode_spec(active_mode)
        
        # Gather short-term session turns and KUL state
        recent_turns = sessions.recent_turns(session_id, n=8)
        kul_state = sessions.get_kul_state(session_id)
        short_term_notes = [
            {"type": "recent_turns", "data": recent_turns},
            {"type": "kul_frontier", "data": {
                "frontier_ids": kul_state.get("frontier_ids", [])[:10],
                "last_anchor": kul_state.get("last_anchor")
            }}
        ]
        
        # Gather officer long-term memory (from SQLite or fallback if module not initialized yet)
        long_term = {}
        try:
            from app.core.memory import get_officer_memory
            long_term = get_officer_memory(officer_id)
        except Exception:
            long_term = {"officer_id": officer_id, "role": "Inspector", "preferences": {"lang": lang}}
            
        # Define output format schema sample based on AgentResponse
        output_sample = {
            "answer": "String (Markdown/Kannada)",
            "confidence": 0.95,
            "mode": active_mode,
            "evidence": [{"text": "FIR 2025-... supports claim", "row_id": "..."}],
            "actions": [{"type": "open_profile", "label": "Open Profile", "params": {"suspect_id": "S0001"}}]
        }
        
        return ContextFrame(
            instructions=mode_spec["instructions"],
            user_input=user_input,
            retrieved_facts=raw_facts or [],
            available_tools=[{"name": a} for a in (mode_spec["primary_agents"] + mode_spec["secondary_agents"])],
            short_term_notes=short_term_notes,
            long_term_memory=long_term,
            output_format=output_sample,
            mode=active_mode,
            officer_id=officer_id,
            session_id=session_id,
            lang=lang,
        )

    @classmethod
    def select(cls, frame: ContextFrame, target_agent: str) -> ContextFrame:
        """Step 2: SELECT — filter retrieved facts and notes specifically for the target specialist agent."""
        selected_facts = []
        for fact in frame.retrieved_facts:
            kind = str(fact.get("kind", "") or fact.get("type", "")).casefold()
            
            # Agent-specific selection rules
            if target_agent in ("profile", "research") and any(k in kind for k in ("suspect", "profile", "fir", "mo", "case")):
                selected_facts.append(fact)
            elif target_agent in ("network", "linkage") and any(k in kind for k in ("network", "relationship", "link", "contact", "phone", "vehicle")):
                selected_facts.append(fact)
            elif target_agent in ("geo", "forecast", "pattern") and any(k in kind for k in ("hotspot", "zone", "district", "trend", "anomaly", "pattern", "beat")):
                selected_facts.append(fact)
            elif target_agent in ("osint",) and any(k in kind for k in ("osint", "unverified", "web", "social")):
                selected_facts.append(fact)
            elif target_agent in ("query", "supervisor"):
                # Query/supervisor get high-priority summary facts
                selected_facts.append(fact)
            elif not kind:
                selected_facts.append(fact)
                
        # If selection filtered out everything, keep up to 10 general facts so agent has grounding
        if not selected_facts and frame.retrieved_facts:
            selected_facts = frame.retrieved_facts[:10]

        return ContextFrame(
            instructions=frame.instructions,
            user_input=frame.user_input,
            retrieved_facts=selected_facts,
            available_tools=frame.available_tools,
            short_term_notes=frame.short_term_notes,
            long_term_memory=frame.long_term_memory,
            output_format=frame.output_format,
            mode=frame.mode,
            officer_id=frame.officer_id,
            session_id=frame.session_id,
            lang=frame.lang,
            budget=frame.budget,
        )

    @classmethod
    def compress(cls, frame: ContextFrame, target_agent: str) -> ContextFrame:
        """Step 3: COMPRESS — enforce strict token ceilings per section to fit Qwen/GLM budgets."""
        budget = frame.budget
        
        # 1. Compress retrieved facts if over budget (6,000 tokens ceiling)
        compressed_facts = []
        facts_tokens = 0
        for f in frame.retrieved_facts:
            ft = estimate_tokens(f)
            if facts_tokens + ft <= budget["retrieved_facts"]:
                compressed_facts.append(f)
                facts_tokens += ft
            else:
                # Summarize/truncate large fact row
                summary = {
                    "id": f.get("id") or f.get("suspect_id") or f.get("FIR_YEAR") or "row",
                    "summary": str(f.get("summary") or f.get("claim") or f.get("mo_summary") or f)[:180] + "..."
                }
                st = estimate_tokens(summary)
                if facts_tokens + st <= budget["retrieved_facts"]:
                    compressed_facts.append(summary)
                    facts_tokens += st
                else:
                    break
                    
        # 2. Compress short-term notes if over budget (2,500 tokens ceiling)
        compressed_notes = []
        notes_tokens = 0
        for n in frame.short_term_notes:
            nt = estimate_tokens(n)
            if notes_tokens + nt <= budget["short_term_notes"]:
                compressed_notes.append(n)
                notes_tokens += nt
            elif n.get("type") == "recent_turns" and isinstance(n.get("data"), list):
                # Keep only the last 3 turns instead of 8
                compact_turns = n["data"][-3:]
                compressed_notes.append({"type": "recent_turns_compressed", "data": compact_turns})
                break

        # 3. Compress long-term memory if needed (1,000 tokens ceiling)
        compressed_memory = frame.long_term_memory
        if estimate_tokens(compressed_memory) > budget["long_term_memory"]:
            compressed_memory = {
                "officer_id": frame.long_term_memory.get("officer_id"),
                "role": frame.long_term_memory.get("role"),
                "conclusions_summary": "Prior session conclusions compressed due to token budget."
            }

        return ContextFrame(
            instructions=frame.instructions[:4000],  # Ensure instructions stay tight
            user_input=frame.user_input,
            retrieved_facts=compressed_facts,
            available_tools=frame.available_tools,
            short_term_notes=compressed_notes,
            long_term_memory=compressed_memory,
            output_format=frame.output_format,
            mode=frame.mode,
            officer_id=frame.officer_id,
            session_id=frame.session_id,
            lang=frame.lang,
            budget=frame.budget,
        )

    @classmethod
    def isolate(cls, frame: ContextFrame, target_agent: str) -> ContextFrame:
        """Step 4: ISOLATE — produce clean, specialized context slice for exact agent invocation."""
        # First Select, then Compress
        selected = cls.select(frame, target_agent)
        compressed = cls.compress(selected, target_agent)
        
        # Customize instructions slightly for the specialist agent role
        agent_prefix = f"[AGENT ROLE: {target_agent.upper()}]\n"
        compressed.instructions = agent_prefix + compressed.instructions
        
        return compressed
