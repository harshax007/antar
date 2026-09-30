import json
import time
from app.obs.config import SPANS_PATH, ensure_dirs
from app.core.settings import settings

def append_span(span: dict) -> None:
    """O(1) append. One line per span. No locks, no buffer. Crash-safe."""
    ensure_dirs()
    if SPANS_PATH.exists() and SPANS_PATH.stat().st_size > getattr(settings, "OBS_JSONL_MAX_MB", 64) * 1_048_576:
        SPANS_PATH.rename(SPANS_PATH.with_suffix(f".{int(time.time())}.jsonl"))
    with open(SPANS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(span, ensure_ascii=False) + "\n")

def read_spans(trace_id: str) -> list[dict]:
    """Dashboard drill-down only — never called on the hot path."""
    out = []
    if SPANS_PATH.exists():
        with open(SPANS_PATH, encoding="utf-8") as f:
            for line in f:
                try:
                    s = json.loads(line)
                    if s.get("trace_id") == trace_id:
                        out.append(s)
                except Exception:
                    continue
    return out
