import json
import pathlib
from typing import Dict

# Lazy import of the LLM runtime – only imported when needed
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None  # Will trigger fallback

# Load the granular taxonomy (maps fine‑grained keys to prompt IDs)
_TAXONOMY_PATH = pathlib.Path(__file__).resolve().parents[1] / "config" / "intent_taxonomy.json"
with _TAXONOMY_PATH.open(encoding="utf-8") as f:
    _TAXONOMY: Dict[str, str] = json.load(f)

# Simple prompt template – list all keys and ask for the best match
_PROMPT_TEMPLATE = (
    "You are an intent classifier for a crime‑analysis system. "
    "Given the user query below, return ONLY the key from the following list that best matches the intent. "
    "Keys: {keys}\n"
    "Query: {query}\n"
    "Answer:" 
)

# Model path – can be overridden via env var for CI/CD
import os
_MODEL_PATH = os.getenv("MODEL_PATH", pathlib.Path(__file__).resolve().parents[2] / "models" / "phi2.ggml")

# Lazy‑loaded global model instance
_model_instance = None

def _load_model():
    global _model_instance
    if Llama is None:
        return None
    if _model_instance is None:
        # Use a modest context size suitable for classification
        _model_instance = Llama(
            model_path=str(_MODEL_PATH),
            n_ctx=512,
            n_threads=4,
            seed=42,
            n_gpu_layers=0,  # CPU only
        )
    return _model_instance

# Fallback to the original keyword‑based classifier (already present in the repo)
try:
    from .intent_classifier import classify_intent as _fallback_classify
except Exception:
    _fallback_classify = None

def _classify_with_llm(query: str) -> str:
    model = _load_model()
    if model is None:
        raise RuntimeError("LLM model could not be loaded")
    prompt = _PROMPT_TEMPLATE.format(keys=", ".join(_TAXONOMY.keys()), query=query)
    # Generate a short completion – stop at first newline
    output = model(prompt, max_tokens=16, stop=["\n"], echo=False)
    # The model may return extra whitespace; clean it up
    raw = output['choices'][0]['text'].strip().lower()
    # Find the first taxonomy key that appears in the output (exact match preferred)
    for key in _TAXONOMY:
        if key in raw:
            return _TAXONOMY[key]
    # If nothing matches, fallback to default
    return _TAXONOMY.get("default", "default")

def classify_intent(query: str) -> str:
    """Return the prompt ID for *query*.

    Primary path: use the local quantised LLM. If loading fails or the LLM does not return a
    recognizable key, gracefully fall back to the lightweight keyword‑map implementation.
    """
    try:
        return _classify_with_llm(query)
    except Exception:
        # Graceful degradation – use keyword fallback if available
        if _fallback_classify:
            return _fallback_classify(query)
        # Ultimate safety net – return default
        return _TAXONOMY.get("default", "default")
