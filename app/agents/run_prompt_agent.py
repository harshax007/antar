import json, pathlib
from typing import Any

# Simple prompt runner (ponytail: stub returning dummy data matching the prompt's output_schema)

def run_prompt(prompt_id: str, query: str) -> Any:
    """Load the prompt definition and return a mock response that satisfies its output_schema.
    This placeholder avoids calling an external LLM; replace with real LLM invocation later.
    """
    # Resolve prompt_lib.json portably: it ships in the backend root (bundled for deploy);
    # fall back to the repo root for local dev. No hardcoded absolute paths (breaks on Linux/AppSail).
    _here = pathlib.Path(__file__).resolve()
    lib_path = next(
        (c for c in (_here.parents[2] / "prompt_lib.json", _here.parents[3] / "prompt_lib.json")
         if c.exists()),
        _here.parents[2] / "prompt_lib.json",
    )
    # Explicit UTF-8 decoding to handle Kannada characters
    with lib_path.open(encoding='utf-8') as f:
        lib = json.load(f)
    prompt = lib.get(prompt_id)
    if not prompt:
        raise ValueError(f"Prompt {prompt_id} not found")
    schema = prompt.get('output_schema', {})
    result: dict = {}
    for prop in schema.get('required', []):
        prop_type = schema['properties'][prop].get('type')
        if prop_type == 'array':
            result[prop] = [f"{query[:30]}..."]
        else:
            result[prop] = f"{query[:30]}..."
    return result
