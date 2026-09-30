import sqlite3, time
from contextlib import contextmanager
from app.obs.config import DB_PATH, ensure_dirs, NON_CONVERSATIONAL_SURFACES

_SCHEMA = """
-- one row per user turn (written once, at trace close)
CREATE TABLE IF NOT EXISTS traces (
  trace_id       TEXT PRIMARY KEY,
  session_id     TEXT,
  reasoning_id   TEXT,                    -- links to audit_store + feedback (V7/V8)
  ts_start       INTEGER,                 -- epoch ms
  ts_end         INTEGER,
  surface        TEXT,                    -- 'chat' | 'ask' | agent name (sentinel/corridor/...)
  question       TEXT,                    -- PII-redacted
  lang           TEXT,                    -- 'en' | 'kn'
  env            TEXT,                    -- 'local' | 'appsail' | ...
  mode           TEXT,                    -- 'llm' | 'offline' | 'demo' | 'guardrail'
  model          TEXT,                    -- e.g. GLM-4.7-Flash
  model_version  TEXT,                    -- settings hash / tag
  temperature    REAL,
  prompt_version TEXT,                    -- bump when SELECT/COMPOSE_SYSTEM changes
  template_id    TEXT,                    -- T1..T16 | NONE | CLARIFY
  answer         TEXT,                    -- PII-redacted
  n_rows         INTEGER DEFAULT 0,
  n_citations    INTEGER DEFAULT 0,
  latency_ms     INTEGER DEFAULT 0,
  tokens_in      INTEGER DEFAULT 0,
  tokens_out     INTEGER DEFAULT 0,
  cost_micros    INTEGER DEFAULT 0,       -- (tokens/1000)*OBS_COST_PER_1K, stored *1e6
  retries        INTEGER DEFAULT 0,
  error          TEXT,                    -- NULL when ok
  feedback       TEXT,                    -- 'up' | 'down' | NULL (joined from V8)
  failure_point  TEXT,                    -- P6 enum, NULL until triaged
  judge_state    TEXT DEFAULT 'none'      -- 'none' | 'pending' | 'done'
);
CREATE INDEX IF NOT EXISTS ix_traces_ts   ON traces(ts_start);
CREATE INDEX IF NOT EXISTS ix_traces_mode ON traces(mode);

-- what retrieval actually did + exactly what was sent to the model (P2)
CREATE TABLE IF NOT EXISTS trace_context (
  trace_id      TEXT PRIMARY KEY REFERENCES traces(trace_id),
  params_json   TEXT,                     -- template params
  row_ids_json  TEXT,                     -- ["2023-BLR-...","..."] (FIR numbers, not full rows)
  citations_json TEXT,                    -- [{fir,station,date,section}]
  system_sent   TEXT,                     -- PII-redacted system prompt
  prompt_sent   TEXT,                     -- PII-redacted user prompt actually sent
  rows_digest   TEXT                      -- short hash of the row set (for contradiction checks)
);

-- rule flags (P4) — 0..n per trace
CREATE TABLE IF NOT EXISTS flags (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id   TEXT REFERENCES traces(trace_id),
  rule       TEXT,                        -- 'F1'.. 'F8'
  severity   TEXT,                        -- 'high' | 'med' | 'low'
  detail     TEXT,
  ts         INTEGER
);
CREATE INDEX IF NOT EXISTS ix_flags_trace ON flags(trace_id);
CREATE INDEX IF NOT EXISTS ix_flags_rule  ON flags(rule);

-- LLM-judge scores (P4) — 0..1 per trace, only for flagged + sampled
CREATE TABLE IF NOT EXISTS scores (
  trace_id      TEXT PRIMARY KEY REFERENCES traces(trace_id),
  groundedness  REAL,                     -- 0..1
  answered      REAL,                     -- 0..1 did it answer the question
  hallucination REAL,                     -- 0..1 (higher = worse)
  safety        REAL,                     -- 0..1
  judged_by     TEXT,                     -- model id
  sampled       INTEGER,                  -- 1 = random-sample, 0 = flagged
  ts            INTEGER
);

-- rolling baselines for spike flags (P3) — one row per (surface,model)
CREATE TABLE IF NOT EXISTS baseline (
  key         TEXT PRIMARY KEY,           -- f"{surface}:{model}"
  p50_ms      REAL, p95_ms   REAL,
  p95_tokens  REAL, n        INTEGER,
  updated_ts  INTEGER
);

-- eval runs (P7)
CREATE TABLE IF NOT EXISTS eval_runs (
  run_id        TEXT PRIMARY KEY,
  prompt_version TEXT, model TEXT, ts INTEGER,
  n INTEGER, pass_rate REAL, avg_grounded REAL, p95_ms REAL
);
CREATE TABLE IF NOT EXISTS eval_cases (
  run_id   TEXT REFERENCES eval_runs(run_id),
  case_id  TEXT, question TEXT, expected TEXT, got TEXT,
  passed   INTEGER, grounded REAL
);

-- SDAR Tables (Self-Distilled Agentic Reinforcement Learning)
CREATE TABLE IF NOT EXISTS sdar_groups (
  group_id      TEXT PRIMARY KEY,         -- UUID for the GRPO rollout group
  session_id    TEXT,
  question      TEXT,
  ts            INTEGER,
  base_trace_id TEXT REFERENCES traces(trace_id) -- The live trace that spawned this group
);

CREATE TABLE IF NOT EXISTS sdar_tokens (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  group_id      TEXT REFERENCES sdar_groups(group_id),
  rollout_id    INTEGER,                  -- 1 to G
  token_idx     INTEGER,                  -- t
  token         TEXT,                     -- The actual generated token
  advantage     REAL,                     -- A^(i)
  log_p_student REAL,                     -- log \pi_S
  log_p_teacher REAL,                     -- log \pi_T
  gate          REAL,                     -- g_t
  ts            INTEGER
);
CREATE INDEX IF NOT EXISTS ix_sdar_tokens_group ON sdar_tokens(group_id);
"""

_schema_ready = False


def init_db() -> None:
    global _schema_ready
    ensure_dirs()
    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL;")
        c.executescript(_SCHEMA)
    _schema_ready = True

@contextmanager
def conn():
    # init_db() runs late in startup, but the HTTP middleware traces the very first
    # request — so the first writer can arrive before the directory exists and fail with
    # "unable to open database file" on every call. That is what happened when OBS_DIR
    # was repointed at a fresh path (2026-09-23). Creating the directory here is cheap
    # (mkdir exist_ok) and makes the store independent of startup ordering.
    #
    # The same ordering bites one level deeper on a FRESH store: the directory now
    # exists, so connecting succeeds, and the first request then fails with
    # "no such table: traces" because init_db() has not run yet. Seen on the first boot
    # of the D:\Project export (2026-09-24). Create the schema once per process here —
    # it is CREATE TABLE IF NOT EXISTS, so it is idempotent and costs one call.
    ensure_dirs()
    if not _schema_ready:
        try:
            init_db()
        except Exception:
            # Observability must never be the reason a request fails. If the schema
            # cannot be created the write below will raise and be handled where the
            # caller already handles it.
            pass
    c = sqlite3.connect(DB_PATH, timeout=5.0)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()

def _upsert(table: str, row: dict) -> None:
    """INSERT … ON CONFLICT(trace_id) upsert.

    When `trace_id` is the ONLY column there is nothing to update on conflict, and the
    generated SQL ended in a bare `DO UPDATE SET ` → sqlite3.OperationalError
    ('incomplete input'). That happened on every trace with no retrieval context (all
    HTTP middleware traces, plus any turn that never called set_context) and the raised
    error aborted the REST of trace.close() — so rolling baselines, rule flags and
    judge-state queueing were all silently skipped for those turns. Fall back to
    DO NOTHING when there is no update to make.
    """
    if not row:
        return
    cols = ",".join(row)
    ph = ",".join("?" for _ in row)
    upd = ",".join(f"{k}=excluded.{k}" for k in row if k != "trace_id")
    tail = f"DO UPDATE SET {upd}" if upd else "DO NOTHING"
    with conn() as c:
        c.execute(f"INSERT INTO {table} ({cols}) VALUES ({ph}) "
                  f"ON CONFLICT(trace_id) {tail}", list(row.values()))


def upsert_trace(row: dict) -> None:
    _upsert("traces", row)


def upsert_context(row: dict) -> None:
    _upsert("trace_context", row)

def set_judge_state(trace_id: str, state: str) -> None:
    with conn() as c:
        c.execute("UPDATE traces SET judge_state=? WHERE trace_id=?", (state, trace_id))

def write_score(trace_id: str, score: dict, judged_by: str) -> None:
    if not score:
        return
    row = {
        "trace_id": trace_id,
        "groundedness": score.get("groundedness"),
        "answered": score.get("answered"),
        "hallucination": score.get("hallucination"),
        "safety": score.get("safety"),
        "judged_by": judged_by,
        "sampled": score.get("sampled", 0),
        "ts": int(time.time()*1000)
    }
    cols = ",".join(row)
    ph = ",".join("?" for _ in row)
    upd = ",".join(f"{k}=excluded.{k}" for k in row if k != "trace_id")
    with conn() as c:
        c.execute(f"INSERT INTO scores ({cols}) VALUES ({ph}) "
                  f"ON CONFLICT(trace_id) DO UPDATE SET {upd}", list(row.values()))

# ── Dashboard read model ──────────────────────────────────────────────────────
# Every read below defaults to conversational traces only. The HTTP middleware writes
# one trace per request, which outnumbers real turns ~9:1 and made the dashboard
# unreadable. Pass conversational_only=False to see the raw request telemetry.

def _surface_clause(conversational_only: bool, alias: str = "t") -> tuple[str, list]:
    if not conversational_only:
        return "", []
    ph = ",".join("?" for _ in NON_CONVERSATIONAL_SURFACES)
    return f" AND COALESCE({alias}.surface,'') NOT IN ({ph})", list(NON_CONVERSATIONAL_SURFACES)


def _fmt_ts(ms) -> str | None:
    if not ms:
        return None
    import datetime
    return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def get_metrics_summary(conversational_only: bool = True) -> dict:
    where, args = _surface_clause(conversational_only)
    with conn() as c:
        row = c.execute(f"""
            SELECT COUNT(*) total,
                   SUM(t.tokens_in + t.tokens_out) tokens,
                   AVG(t.latency_ms) latency,
                   MAX(t.latency_ms) max_latency,
                   SUM(t.n_citations) citations,
                   SUM(t.n_rows) rows_read,
                   SUM(CASE WHEN t.error IS NOT NULL AND t.error != '' THEN 1 ELSE 0 END) errors,
                   SUM(CASE WHEN t.mode = 'llm' THEN 1 ELSE 0 END) llm_turns,
                   SUM(CASE WHEN t.mode = 'offline' THEN 1 ELSE 0 END) offline_turns,
                   COUNT(DISTINCT NULLIF(t.session_id, '')) sessions
            FROM traces t WHERE 1=1{where}
        """, args).fetchone()
        flagged = c.execute(f"""
            SELECT COUNT(DISTINCT f.trace_id) flagged
            FROM flags f JOIN traces t ON t.trace_id = f.trace_id
            WHERE 1=1{where}
        """, args).fetchone()
        high = c.execute(f"""
            SELECT COUNT(DISTINCT f.trace_id) n
            FROM flags f JOIN traces t ON t.trace_id = f.trace_id
            WHERE f.severity = 'high'{where}
        """, args).fetchone()
        scores = c.execute(f"""
            SELECT AVG(s.groundedness) avg_g, COUNT(*) n
            FROM scores s JOIN traces t ON t.trace_id = s.trace_id
            WHERE 1=1{where}
        """, args).fetchone()
        # p95 latency without a window function — works on any SQLite build.
        lat = [r[0] for r in c.execute(
            f"SELECT t.latency_ms FROM traces t WHERE t.latency_ms IS NOT NULL{where} "
            f"ORDER BY t.latency_ms", args).fetchall()]
        by_rule = [dict(r) for r in c.execute(f"""
            SELECT f.rule, f.severity, COUNT(*) n
            FROM flags f JOIN traces t ON t.trace_id = f.trace_id
            WHERE 1=1{where}
            GROUP BY f.rule, f.severity ORDER BY n DESC
        """, args).fetchall()]

    total = row["total"] or 0
    p95 = lat[min(int(len(lat) * 0.95), len(lat) - 1)] if lat else 0
    judged = scores["n"] or 0
    return {
        "total_traces": total,
        "sessions": row["sessions"] or 0,
        "total_tokens": row["tokens"] or 0,
        "avg_latency_ms": row["latency"] or 0.0,
        "p95_latency_ms": p95,
        "max_latency_ms": row["max_latency"] or 0,
        "total_citations": row["citations"] or 0,
        "total_rows_read": row["rows_read"] or 0,
        "errors": row["errors"] or 0,
        "llm_turns": row["llm_turns"] or 0,
        "offline_turns": row["offline_turns"] or 0,
        "flagged_traces": flagged["flagged"] or 0,
        "high_severity_traces": high["n"] or 0,
        "clean_rate": round(100.0 * (total - (flagged["flagged"] or 0)) / total, 1) if total else 100.0,
        "judged_traces": judged,
        # Judge only runs on flagged + a 5% sample. Report the score AND its coverage so a
        # blank 0.0/5 reads as "not judged yet" rather than "scored zero".
        "avg_quality": ((scores["avg_g"] or 0) * 5) if judged else None,
        "flags_by_rule": by_rule,
        "conversational_only": conversational_only,
    }


def get_recent_traces(limit: int = 50, conversational_only: bool = True,
                      flagged_only: bool = False, session_id: str | None = None,
                      q: str | None = None) -> list[dict]:
    where, args = _surface_clause(conversational_only)
    if session_id:
        where += " AND t.session_id = ?"
        args.append(session_id)
    if q:
        where += " AND (t.question LIKE ? OR t.answer LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if flagged_only:
        where += " AND EXISTS (SELECT 1 FROM flags f WHERE f.trace_id = t.trace_id)"
    with conn() as c:
        rows = c.execute(f"""
            SELECT t.trace_id, t.session_id, t.surface, t.ts_start, t.ts_end, t.question,
                   t.answer, t.lang, t.mode, t.model, t.template_id, t.n_rows, t.n_citations,
                   t.latency_ms, t.tokens_in, t.tokens_out, t.retries, t.error, t.judge_state,
                   s.groundedness, s.hallucination, s.answered, s.safety,
                   (SELECT json_group_array(json_object('rule', rule, 'severity', severity,
                                                        'detail', detail))
                      FROM flags WHERE trace_id = t.trace_id) AS flag_rows
            FROM traces t
            LEFT JOIN scores s ON t.trace_id = s.trace_id
            WHERE 1=1{where}
            ORDER BY t.ts_start DESC LIMIT ?
        """, args + [limit]).fetchall()
    return [_turn(r) for r in rows]


def _turn(r) -> dict:
    import json as _json
    try:
        flags = [f for f in _json.loads(r["flag_rows"] or "[]") if f and f.get("rule")]
    except Exception:
        flags = []
    answer = r["answer"] or ""
    return {
        "trace_id": r["trace_id"],
        "session_id": r["session_id"] or "",
        "surface": r["surface"],
        "created_at": _fmt_ts(r["ts_start"]),
        "ts_start": r["ts_start"],
        "question": r["question"],
        "answer_preview": answer[:280],
        "answer_len": len(answer),
        "lang": r["lang"],
        "mode": r["mode"],
        "model": r["model"],
        "template_id": r["template_id"],
        "n_rows": r["n_rows"],
        "n_citations": r["n_citations"],
        "latency_ms": r["latency_ms"],
        "total_ms": r["latency_ms"],          # legacy key the old table column used
        "tokens_in": r["tokens_in"],
        "tokens_out": r["tokens_out"],
        "retries": r["retries"],
        "error": r["error"],
        "judge_state": r["judge_state"],
        "quality_score": round(r["groundedness"] * 5, 1) if r["groundedness"] is not None else None,
        "groundedness": r["groundedness"],
        "hallucination": r["hallucination"],
        "answered": r["answered"],
        "safety": r["safety"],
        "flags": flags,
        "flag_rules": [f["rule"] for f in flags],
    }


def get_sessions(limit: int = 60, conversational_only: bool = True) -> list[dict]:
    """One row per chat session: turn count, span, cost, and where it went wrong."""
    where, args = _surface_clause(conversational_only)
    with conn() as c:
        rows = c.execute(f"""
            SELECT t.session_id,
                   COUNT(*)                              AS turns,
                   MIN(t.ts_start)                       AS first_ts,
                   MAX(t.ts_start)                       AS last_ts,
                   SUM(t.tokens_in + t.tokens_out)       AS tokens,
                   AVG(t.latency_ms)                     AS avg_ms,
                   SUM(t.latency_ms)                     AS total_ms,
                   SUM(t.n_citations)                    AS citations,
                   SUM(t.n_rows)                         AS rows_read,
                   SUM(CASE WHEN t.error IS NOT NULL AND t.error != '' THEN 1 ELSE 0 END) AS errors,
                   SUM(CASE WHEN t.mode='llm' THEN 1 ELSE 0 END) AS llm_turns,
                   (SELECT COUNT(DISTINCT f.trace_id) FROM flags f
                     WHERE f.trace_id IN (SELECT trace_id FROM traces
                                           WHERE session_id = t.session_id)) AS flagged,
                   (SELECT question FROM traces q
                     WHERE q.session_id = t.session_id AND COALESCE(q.question,'') != ''
                     ORDER BY q.ts_start DESC LIMIT 1)   AS last_question,
                   (SELECT question FROM traces q
                     WHERE q.session_id = t.session_id AND COALESCE(q.question,'') != ''
                     ORDER BY q.ts_start ASC LIMIT 1)    AS first_question,
                   (SELECT group_concat(DISTINCT lang) FROM traces q
                     WHERE q.session_id = t.session_id) AS langs
            FROM traces t
            WHERE COALESCE(t.session_id,'') != ''{where}
            GROUP BY t.session_id
            ORDER BY last_ts DESC
            LIMIT ?
        """, args + [limit]).fetchall()

    out = []
    for r in rows:
        span_s = round(((r["last_ts"] or 0) - (r["first_ts"] or 0)) / 1000)
        out.append({
            "session_id": r["session_id"],
            "turns": r["turns"],
            "first_at": _fmt_ts(r["first_ts"]),
            "last_at": _fmt_ts(r["last_ts"]),
            "first_ts": r["first_ts"],
            "last_ts": r["last_ts"],
            "duration_s": span_s,
            "tokens": r["tokens"] or 0,
            "avg_latency_ms": round(r["avg_ms"] or 0),
            "total_ms": r["total_ms"] or 0,
            "citations": r["citations"] or 0,
            "rows_read": r["rows_read"] or 0,
            "errors": r["errors"] or 0,
            "llm_turns": r["llm_turns"] or 0,
            "flagged": r["flagged"] or 0,
            "first_question": r["first_question"],
            "last_question": r["last_question"],
            "langs": [x for x in (r["langs"] or "").split(",") if x],
        })
    return out


def get_session_turns(session_id: str, conversational_only: bool = True) -> list[dict]:
    """Every turn in one session, oldest first — the replay of that conversation."""
    where, args = _surface_clause(conversational_only)
    with conn() as c:
        rows = c.execute(f"""
            SELECT t.trace_id, t.session_id, t.surface, t.ts_start, t.ts_end, t.question,
                   t.answer, t.lang, t.mode, t.model, t.template_id, t.n_rows, t.n_citations,
                   t.latency_ms, t.tokens_in, t.tokens_out, t.retries, t.error, t.judge_state,
                   s.groundedness, s.hallucination, s.answered, s.safety,
                   (SELECT json_group_array(json_object('rule', rule, 'severity', severity,
                                                        'detail', detail))
                      FROM flags WHERE trace_id = t.trace_id) AS flag_rows
            FROM traces t
            LEFT JOIN scores s ON t.trace_id = s.trace_id
            WHERE t.session_id = ?{where}
            ORDER BY t.ts_start ASC
        """, [session_id] + args).fetchall()
    turns = [_turn(r) for r in rows]
    for i, t in enumerate(turns, start=1):
        t["turn_no"] = i
    return turns


def get_trace_detail(trace_id: str) -> dict | None:
    """Full drill-down for one turn: the answer, what was retrieved, what was sent to the
    model, which agents ran, and every flag/score attached to it."""
    import json as _json
    with conn() as c:
        r = c.execute("""
            SELECT t.*, s.groundedness, s.hallucination, s.answered, s.safety,
                   s.judged_by, s.sampled, s.ts AS judged_ts
            FROM traces t LEFT JOIN scores s ON s.trace_id = t.trace_id
            WHERE t.trace_id = ?
        """, (trace_id,)).fetchone()
        if not r:
            return None
        ctx = c.execute("SELECT * FROM trace_context WHERE trace_id = ?", (trace_id,)).fetchone()
        flag_rows = c.execute(
            "SELECT rule, severity, detail, ts FROM flags WHERE trace_id = ? ORDER BY ts",
            (trace_id,)).fetchall()

    def _j(v, default):
        try:
            return _json.loads(v) if v else default
        except Exception:
            return default

    d = dict(r)
    ctxd = dict(ctx) if ctx else {}

    # Agent spans come from the JSONL sidecar, not SQLite.
    spans = []
    try:
        from app.obs import writer
        spans = sorted(writer.read_spans(trace_id), key=lambda s: s.get("ts") or 0)
    except Exception:
        spans = []

    agents = []
    for s in spans:
        a = s.get("agent")
        if a and a not in agents:
            agents.append(a)

    return {
        "trace_id": d["trace_id"],
        "session_id": d.get("session_id") or "",
        "surface": d.get("surface"),
        "created_at": _fmt_ts(d.get("ts_start")),
        "ended_at": _fmt_ts(d.get("ts_end")),
        "question": d.get("question"),
        "answer": d.get("answer"),
        "lang": d.get("lang"),
        "env": d.get("env"),
        "mode": d.get("mode"),
        "model": d.get("model"),
        "model_version": d.get("model_version"),
        "temperature": d.get("temperature"),
        "prompt_version": d.get("prompt_version"),
        "reasoning_id": d.get("reasoning_id"),
        "template_id": d.get("template_id"),
        "n_rows": d.get("n_rows"),
        "n_citations": d.get("n_citations"),
        "latency_ms": d.get("latency_ms"),
        "tokens_in": d.get("tokens_in"),
        "tokens_out": d.get("tokens_out"),
        "cost_micros": d.get("cost_micros"),
        "retries": d.get("retries"),
        "error": d.get("error"),
        "judge_state": d.get("judge_state"),
        "retrieval": {
            "params": _j(ctxd.get("params_json"), {}),
            "row_ids": _j(ctxd.get("row_ids_json"), []),
            "citations": _j(ctxd.get("citations_json"), []),
            "rows_digest": ctxd.get("rows_digest"),
            # Present only on LLM turns; offline turns never build a prompt.
            "system_sent": ctxd.get("system_sent"),
            "prompt_sent": ctxd.get("prompt_sent"),
        },
        "agents": agents,
        "spans": [{
            "span_id": s.get("span_id"),
            "agent": s.get("agent"),
            "step": s.get("step"),
            "ms": s.get("ms"),
            "in_digest": s.get("in_digest"),
            "out_digest": s.get("out_digest"),
            "at": _fmt_ts(s.get("ts")),
        } for s in spans],
        "flags": [dict(f) for f in flag_rows],
        "scores": None if d.get("groundedness") is None else {
            "groundedness": d.get("groundedness"),
            "answered": d.get("answered"),
            "hallucination": d.get("hallucination"),
            "safety": d.get("safety"),
            "judged_by": d.get("judged_by"),
            "sampled": bool(d.get("sampled")),
            "judged_at": _fmt_ts(d.get("judged_ts")),
        },
    }
