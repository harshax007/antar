import re
from typing import Dict

# Simple keyword‑based intent classifier (ponytail: fast, no external deps)
# Mapping of keywords (lowercase) to prompt IDs
KEYWORD_MAP: Dict[str, str] = {
    # Category A
    "fir": "int_01",
    "incident": "int_01",
    "translation": "int_01",
    "ipc": "int_02",
    "gazette": "int_02",
    "mahazar": "int_03",
    "panchanama": "int_03",
    "alias": "int_04",
    "profile": "int_04",
    # Category B
    "economic": "inv_05",
    "smurfing": "inv_05",
    "organized": "inv_06",
    "syndicate": "inv_06",
    "cdr": "inv_07",
    "geo": "inv_07",
    "cyber": "inv_08",
    "malware": "inv_08",
    # Category C
    "evidence": "cmp_09",
    "penalty": "cmp_09",
    "arrest": "cmp_10",
    "timeline": "cmp_11",
    "certificate": "cmp_12",
    # Category D
    "risk": "intel_13",
    "heatmap": "intel_13",
    "deepfake": "intel_14",
    "hate": "intel_15",
    "mule": "intel_16",
    # Category E
    "citizen": "pub_17",
    "victim": "pub_18",
    "traffic": "pub_19",
    "escalation": "pub_20",
    # Generic defaults
    "summarise": "summarise_crime",
    "trend": "predict_trend",
}

def classify_intent(query: str) -> str:
    """Return the best‑match prompt ID for *query*.
    Simple heuristic: first keyword match (case‑insensitive). If none match, return "default".
    """
    lowered = query.lower()
    for kw, intent in KEYWORD_MAP.items():
        if re.search(rf"\b{re.escape(kw)}\b", lowered):
            return intent
    return "default"
