import json
from pathlib import Path

def load_prompt_library() -> dict:
    """Load the prompt library JSON generated during the planning phase.
    Returns a dictionary keyed by task name.
    """
    # Assuming the JSON lives at the project root (E:/Datathon_2026/build03/prompt_lib.json)
    lib_path = Path(__file__).resolve().parents[2] / "prompt_lib.json"
    with lib_path.open('r', encoding='utf-8') as f:
        return json.load(f)
