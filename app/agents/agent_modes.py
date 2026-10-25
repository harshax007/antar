"""
Antar — First-Class Agent Modes (Think · Connect · Anticipate)
================================================================
Maps the core architectural pillars into operational mode specifications,
defining DAG dependency execution stages, primary/secondary agents, and
specialized instructions for the Context Engineering Stack.
"""

from __future__ import annotations
from typing import TypedDict


class ModeSpec(TypedDict):
    name: str
    label: str
    description: str
    primary_agents: list[str]
    secondary_agents: list[str]
    dag: dict[str, list[str]]  # agent -> list of dependency agents that must finish first
    instructions: str
    slash_command: str | None


MODES: dict[str, ModeSpec] = {
    "think": {
        "name": "think",
        "label": "Deep Analytical Reasoning & Dossier Mode",
        "description": "Performs deep multi-layer investigative research across K/D/I/U states, building evidence trails and hypotheses.",
        "primary_agents": ["query", "profile", "research"],
        "secondary_agents": ["vigil"],
        "dag": {
            "query": [],
            "profile": ["query"],
            "research": ["query"],
            "vigil": ["profile", "research"]
        },
        "instructions": (
            "You are operating in THINK mode (Deep Analytical & Dossier Research). "
            "Examine the query against known facts (FIR data), derived metrics (risk scores), "
            "and inferred hypotheses (UNSUB patterns). Explicitly cite every fact to official DB rows or Second Brain links. "
            "If information is missing, identify exact K/D/I/U intelligence gaps and state what collection actions are required."
        ),
        "slash_command": "think"
    },
    "connect": {
        "name": "connect",
        "label": "Network Linkage & Cross-Case Intelligence Mode",
        "description": "Uncovers hidden relationships, shared phone hashes/contacts, money trails, and cross-case overlaps.",
        "primary_agents": ["query", "network", "brain"],
        "secondary_agents": ["corridor", "linkage"],
        "dag": {
            "query": [],
            "network": ["query"],
            "brain": ["query"],
            "corridor": ["network"],
            "linkage": ["brain", "network"]
        },
        "instructions": (
            "You are operating in CONNECT mode (Network & Cross-Case Intelligence). "
            "Focus on relational graph topology, BFS multi-hop links, Adamic-Adar broker centrality, "
            "and Second Brain semantic overlaps (shared vehicle numbers, phone hashes, or bank accounts). "
            "Never assert a connection across cases without naming the shared evidence key."
        ),
        "slash_command": "connect"
    },
    "anticipate": {
        "name": "anticipate",
        "label": "Predictive Forecasting & Early Warning Mode",
        "description": "Computes spatial-temporal anomalies, MAD-z spikes, hotspot projections, and patrol beat recommendations.",
        "primary_agents": ["forecast", "prediction", "geo"],
        "secondary_agents": ["pattern", "alert_suggest", "sentinel"],
        "dag": {
            "forecast": [],
            "prediction": [],
            "geo": ["forecast"],
            "pattern": ["forecast"],
            "alert_suggest": ["prediction", "geo"],
            "sentinel": ["alert_suggest"]
        },
        "instructions": (
            "You are operating in ANTICIPATE mode (Predictive Forecasting & Early Warning). "
            "Focus on statistical anomaly detection (MAD-z scores), spatial-temporal clustering (ST-DBSCAN), "
            "and Gi* hotspot boundaries. Evaluate current shift deployment and provide actionable, grounded patrol suggestions "
            "to prevent imminent crime spikes."
        ),
        "slash_command": "anticipate"
    },
    "general": {
        "name": "general",
        "label": "General Crime Intelligence Mode",
        "description": "Responsive multi-agent routing based on user inquiry intent.",
        "primary_agents": ["query"],
        "secondary_agents": ["profile", "network", "geo"],
        "dag": {
            "query": [],
            "profile": ["query"],
            "network": ["query"],
            "geo": ["query"]
        },
        "instructions": (
            "You are operating in GENERAL crime intelligence mode. "
            "Provide direct, factual, and verified answers grounded strictly in KSP records. "
            "If the user asks for deeper analysis, suggest switching to /think, /connect, or /anticipate modes."
        ),
        "slash_command": None
    }
}


def get_mode_spec(mode_name: str) -> ModeSpec:
    """Retrieve the ModeSpec for a given mode name, defaulting to general."""
    clean = (mode_name or "general").casefold().strip().lstrip("/")
    return MODES.get(clean, MODES["general"])


def detect_mode_from_query(text: str, slash_command: str | None = None) -> str:
    """Determine appropriate operational mode from slash commands or natural language intent."""
    if slash_command and slash_command.casefold() in MODES:
        return slash_command.casefold()
        
    low = (text or "").casefold()
    if any(low.startswith(f"/{m}") for m in ("think", "connect", "anticipate")):
        for m in ("think", "connect", "anticipate"):
            if f"/{m}" in low:
                return m
                
    # High-signal semantic triggers
    if any(w in low for w in ("deep research", "dossier", "k/d/i/u", "kul", "investigate everything", "why and how")):
        return "think"
    if any(w in low for w in ("cross case", "cross-case", "network graph", "who knows whom", "shared contacts", "overlap between")):
        return "connect"
    if any(w in low for w in ("forecast", "predict", "hotspot warning", "patrol deployment", "early warning", "mad-z", "anomaly spike")):
        return "anticipate"
        
    return "general"
