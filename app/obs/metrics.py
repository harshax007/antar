import random, time
from app.core.settings import settings
from app.obs import store

def cost_micros(total_tokens: int) -> int:
    return int((total_tokens / 1000.0) * getattr(settings, "OBS_COST_PER_1K", 0.0) * 1_000_000)

def in_sample() -> bool:
    return random.random() < getattr(settings, "OBS_JUDGE_SAMPLE", 0.05)

def parse_usage(raw_json: dict) -> tuple[int, int]:
    """QuickML usage block (V2). Handle both {'usage':{...}} shapes; default 0,0."""
    u = (raw_json or {}).get("usage") or {}
    ti = u.get("prompt_tokens") or u.get("input_tokens") or 0
    to = u.get("completion_tokens") or u.get("output_tokens") or 0
    return int(ti or 0), int(to or 0)

def update_baseline(d: dict) -> None:
    """EWMA-ish rolling p95 per (surface,model). Cheap approximation, no full history."""
    key = f"{d.get('surface')}:{d.get('model')}"
    with store.conn() as c:
        row = c.execute("SELECT * FROM baseline WHERE key=?", (key,)).fetchone()
        lat, tok = d.get("latency_ms", 0), d.get("tokens_in", 0) + d.get("tokens_out", 0)
        if row is None:
            c.execute("INSERT INTO baseline(key,p50_ms,p95_ms,p95_tokens,n,updated_ts)"
                      " VALUES (?,?,?,?,?,?)", (key, lat, lat, tok, 1, int(time.time()*1000)))
        else:
            a = 0.1  # smoothing
            p95 = max(row["p95_ms"]*(1-a), lat) if lat > row["p95_ms"] else row["p95_ms"]*(1-a)+lat*a
            p95t = max(row["p95_tokens"]*(1-a), tok) if tok > row["p95_tokens"] else row["p95_tokens"]*(1-a)+tok*a
            c.execute("UPDATE baseline SET p50_ms=?,p95_ms=?,p95_tokens=?,n=n+1,updated_ts=? WHERE key=?",
                      (row["p50_ms"]*(1-a)+lat*a, p95, p95t, int(time.time()*1000), key))

def baseline_for(surface, model) -> dict | None:
    with store.conn() as c:
        r = c.execute("SELECT * FROM baseline WHERE key=?", (f"{surface}:{model}",)).fetchone()
        return dict(r) if r else None
