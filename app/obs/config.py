from pathlib import Path
from app.core.settings import settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]      # antar-backend/
OBS_DIR = BACKEND_ROOT / settings.OBS_DIR
DB_PATH = OBS_DIR / "obs.db"
SPANS_PATH = OBS_DIR / "obs_spans.jsonl"

def ensure_dirs() -> None:
    OBS_DIR.mkdir(parents=True, exist_ok=True)


# ── Surface classification ────────────────────────────────────────────────────
# A "conversational" trace is one user turn: a question went in, an answer came out.
# Those are the only traces the Trust dashboard, the rule flags and the LLM judge are
# meaningful for.
#
# The `_obs_mw` middleware in main.py ALSO opens a trace for every HTTP request, with
# question=<url path> and answer=<status code>. Those are useful as raw latency
# telemetry but they are not turns, and treating them as such broke two things:
#   • the dashboard drowned — 289 of 322 rows read "/api/workspace" instead of a question
#   • rule F1 ("asserts a number with no citation") fired on the answer "200", marking
#     every successful HTTP request as a HIGH-severity hallucination
# Keep writing them; just classify them.
CONVERSATIONAL_SURFACES = ("chat", "chat_stream", "ask", "voice", "agent")
NON_CONVERSATIONAL_SURFACES = ("http",)


def is_conversational(surface: str | None) -> bool:
    """True when a trace represents a user turn rather than a raw HTTP request."""
    return (surface or "") not in NON_CONVERSATIONAL_SURFACES
