import time, uuid, contextvars
from app.core.settings import settings
from app.core.guardrails import redact_pii
from app.obs import writer, store, metrics, flags
import structlog
_log = structlog.get_logger("obs")

_current = contextvars.ContextVar("obs_trace", default=None)

class _Trace:
    def __init__(self, session_id, surface, question, lang, env):
        self.d = dict(
            trace_id=f"trc-{uuid.uuid4().hex[:12]}", session_id=session_id,
            surface=surface, question=redact_pii(question or ""), lang=lang, env=env,
            ts_start=int(time.time()*1000), mode="offline",
            model=None, model_version=None, temperature=None,
            template_id=None, answer=None, n_rows=0, n_citations=0,
            latency_ms=0, tokens_in=0, tokens_out=0, retries=0, error=None,
        )
        self.ctx = {}          # -> trace_context row (P2)

def _on() -> bool:
    return getattr(settings, "OBS_ENABLED", False)

def start(session_id="", surface="chat", question="", lang="en", env="local"):
    if not _on():
        return None
    t = _Trace(session_id, surface, question, lang, env)
    _current.set(t)
    return t.d["trace_id"]

def current():
    return _current.get()

def add_span(agent, step, in_digest, out_digest, ms, **extra):
    """Called by the log_step sink (V4). One JSONL line per span."""
    if not _on():
        return
    t = current()
    tid = t.d["trace_id"] if t else "orphan"
    try:
        writer.append_span(dict(trace_id=tid, span_id=f"sp-{uuid.uuid4().hex[:8]}",
                                agent=agent, step=step, in_digest=str(in_digest)[:200],
                                out_digest=str(out_digest)[:200], ms=ms,
                                ts=int(time.time()*1000), **extra))
    except Exception as e:
        _log.warning("obs_span_failed", err=repr(e))

def record_llm(model, tokens_in, tokens_out, ms, retries=0, error=None,
               system=None, prompt=None, temperature=None):
    """Called from the quickml hook (§5.3). Accumulates onto the current trace."""
    if not _on():
        return
    t = current()
    if not t:
        return
    d = t.d
    d["model"] = model or d["model"]; d["mode"] = "llm"
    d["tokens_in"] += tokens_in or 0; d["tokens_out"] += tokens_out or 0
    d["latency_ms"] += ms or 0; d["retries"] += retries or 0
    if temperature is not None: d["temperature"] = temperature
    if error:
        from app.core.security import scrub_text
        d["error"] = scrub_text(error, limit=300)
    if system is not None:
        # stored without the canary: a trace is read by people, the canary must not be
        from app.core.rag_security import mask_internal
        t.ctx["system_sent"] = mask_internal(redact_pii(system))[:4000]
    if prompt is not None: t.ctx["prompt_sent"] = redact_pii(prompt)[:8000]

def set_context(template_id=None, params=None, rows=None, citations=None, mode=None):
    """Called from the trace-close hook (§5.2) with retrieval facts."""
    if not _on():
        return
    t = current()
    if not t:
        return
    import json, hashlib
    d = t.d
    if template_id is not None: d["template_id"] = template_id
    if mode is not None: d["mode"] = mode
    if rows is not None:
        d["n_rows"] = len(rows)
        ids = [r.get("fir_number") for r in rows if isinstance(r, dict) and r.get("fir_number")]
        t.ctx["row_ids_json"] = json.dumps(ids[:200])
        blob = "".join(sorted(ids))[:4000]
        t.ctx["rows_digest"] = hashlib.sha1(blob.encode()).hexdigest()[:16]
    if citations is not None:
        d["n_citations"] = len(citations)
        t.ctx["citations_json"] = json.dumps(citations[:50], ensure_ascii=False)
    if params is not None:
        t.ctx["params_json"] = json.dumps(params, ensure_ascii=False)

def close(answer="", reasoning_id=None, prompt_version="v1", model_version=None):
    """Finalize: persist trace + context, run FREE flags, mark judge-pending. Fail-open."""
    if not _on():
        return
    t = current()
    if not t:
        return
    try:
        d = t.d
        d["ts_end"] = int(time.time()*1000)
        d["answer"] = redact_pii(answer or "")[:8000]
        d["reasoning_id"] = reasoning_id
        d["prompt_version"] = prompt_version
        d["model_version"] = model_version
        d["cost_micros"] = metrics.cost_micros(d["tokens_in"] + d["tokens_out"])
        if not d.get("latency_ms"):
            d["latency_ms"] = d["ts_end"] - d["ts_start"]
        store.upsert_trace({k: v for k, v in d.items() if k != "session_id" or v} | {"session_id": d["session_id"]})
        store.upsert_context(t.ctx | {"trace_id": d["trace_id"]})   # add upsert_context in store.py
        metrics.update_baseline(d)                                  # rolling p50/p95
        fired = flags.evaluate(d, t.ctx)                            # FREE rule flags, 100%
        flags.persist(d["trace_id"], fired)
        judged_pending = bool(fired) or metrics.in_sample()         # flagged OR 5%
        store.set_judge_state(d["trace_id"], "pending" if judged_pending else "none")
    except Exception as e:
        _log.warning("obs_close_failed", err=repr(e))
    finally:
        _current.set(None)
