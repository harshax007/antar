import time, json
from app.core.settings import settings
from app.obs import metrics, store
from app.obs.config import is_conversational

def evaluate(d: dict, ctx: dict) -> list[dict]:
    # Answer-quality rules only make sense for a user turn. An HTTP middleware trace
    # carries answer="200" and zero rows, which trips F1 ("asserts a number with no
    # citation") on EVERY successful request — the dashboard's flag count was almost
    # entirely these false positives.
    if not is_conversational(d.get("surface")):
        return []
    fired, ans = [], (d.get("answer") or "")
    cites = json.loads(ctx.get("citations_json") or "[]")
    # F1: asserts a fact but has no source
    if _asserts_number_or_id(ans) and not cites and d.get("n_rows", 0) == 0:
        fired.append(_f("F1", "high", "Answer asserts a fact with zero rows and zero citations"))
    # F5: confident answer on empty rows
    if d.get("n_rows", 0) == 0 and d.get("template_id") not in (None, "NONE", "CLARIFY") \
       and not _says_no_records(ans):
        fired.append(_f("F5", "high", "template returned 0 rows but answer does not disclaim"))
    # F6: silent degradation (LLM expected, went offline)
    if d.get("mode") == "offline" and getattr(settings, "OBS_JUDGE_ENABLED", True) and d.get("model") is None:
        fired.append(_f("F6", "med", "LLM path unavailable — answered from offline fallback"))
    # F3: latency / token spike vs baseline
    b = metrics.baseline_for(d.get("surface"), d.get("model"))
    spike_k = getattr(settings, "OBS_SPIKE_K", 2.0)
    if b and b["n"] > 20:
        if d.get("latency_ms", 0) > b["p95_ms"] * spike_k:
            fired.append(_f("F3", "med", f"latency {d['latency_ms']}ms > {spike_k}x p95"))
    return fired

def persist(trace_id, fired):
    if not fired:
        return
    with store.conn() as c:
        c.executemany("INSERT INTO flags(trace_id,rule,severity,detail,ts) VALUES (?,?,?,?,?)",
                      [(trace_id, f["rule"], f["severity"], f["detail"], f["ts"]) for f in fired])

def from_query_result(trace_id, qr: dict):
    """Called from the close hook with the query_agent result to capture V5 signals cheaply."""
    fired = []
    if qr.get("entity_not_found"):                       # F2 — chunks contradict / entity absent
        fired.append(_f("F2", "high", f"named entity not in rows: {qr['entity_not_found']}"))
    if qr.get("guardrail_violations"):                   # F7 — guardrail tripped
        fired.append(_f("F7", "med", f"guardrail: {qr['guardrail_violations']}"))
    persist(trace_id, fired)

def _f(rule, sev, detail): return {"rule": rule, "severity": sev, "detail": detail, "ts": int(time.time()*1000)}
def _asserts_number_or_id(a): 
    import re; return bool(re.search(r"\d{2,}|\bFIR\b|KA\d{2}", a or ""))
def _says_no_records(a):
    a = (a or "").lower(); return "no matching" in a or "no record" in a or "ದಾಖಲೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ" in a
