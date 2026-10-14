"""
Antar — Answer Feedback
============================
POST /api/feedback         {session_id, reasoning_id?, question, rating: "up"|"down", note?}
GET  /api/feedback/stats
GET  /api/feedback/signal  what the ratings have taught: questions to promote / avoid
GET  /api/feedback/review  the queue of poorly-rated answers, for an Admin to work through

What "learns from officers" means here, exactly - it is not reinforcement learning, and
nothing is retrained:
  - a question officers rate useful is offered sooner, one rated poor stops being
    suggested and lands in a review queue a human works through (no model involved);
  - when the language model writes an answer, up to two answers officers rated useful for
    similar questions are shown to it as examples of SHAPE (antar_identity.learned_block).
The records and the templates never change because of a rating.

Three rules keep a rating from being gamed or poisoned:
  - the officer is the signed-in officer from the token, never a field in the body;
  - one vote per officer per question - voting again replaces the earlier vote;
  - the answer kept with a rating is the one this server gave in that conversation,
    looked up by its reasoning id; text sent by the browser is never stored as an answer.
    A rating whose answer cannot be found still counts for suggestions, but never becomes
    an example.

Kept in the application database (it used to be a JSONL file beside the code, which a
read-only deploy cannot write to) and mirrored into the audit trail.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.auth_middleware import require_role

router = APIRouter()

# The old store. Read once into the table, then left alone (never deleted from here).
_LEGACY_FILE = Path(__file__).resolve().parents[2] / "data_feedback.jsonl"


class FeedbackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    reasoning_id: str | None = Field(default=None, max_length=64)
    question: str = Field(min_length=1, max_length=2000)
    rating: Literal["up", "down"]
    note: str | None = Field(default=None, max_length=2000)
    lang: str | None = Field(default=None, max_length=8)
    template_id: str | None = Field(default=None, max_length=16)
    # Accepted so older clients are not refused, and ignored: the officer comes from the
    # token and the answer from this server's own record of the conversation.
    officer: str | None = None
    answer: str | None = Field(default=None, max_length=4000)


def _norm(q: str) -> str:
    return " ".join((q or "").strip().lower().split())


# ── store ────────────────────────────────────────────────────────────────────

def _db_path() -> str:
    from app.core.db_path import DB_PATH, ensure_db_staged
    ensure_db_staged()
    return DB_PATH


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_db_path(), timeout=10)
    c.execute("""CREATE TABLE IF NOT EXISTS answer_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, officer TEXT NOT NULL,
        role TEXT, session_id TEXT, reasoning_id TEXT, question TEXT NOT NULL, qnorm TEXT NOT NULL,
        rating TEXT NOT NULL, note TEXT, lang TEXT, template_id TEXT, answer TEXT,
        answer_source TEXT NOT NULL DEFAULT 'none',          -- server | none | imported
        UNIQUE (officer, qnorm))""")
    _import_legacy(c)
    return c


def _import_legacy(c: sqlite3.Connection) -> None:
    """One-time move of data_feedback.jsonl into the table. Test entries (session ids
    starting "mock") are left behind, and a browser-sent answer is not carried over: it
    was never checked against what Antar said."""
    if c.execute("SELECT 1 FROM answer_feedback LIMIT 1").fetchone() or not _LEGACY_FILE.exists():
        return
    try:
        lines = _LEGACY_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    rows = []
    for line in lines:
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not isinstance(e, dict):
            continue
        q = _norm(e.get("question", ""))
        if not q or e.get("rating") not in ("up", "down") or str(e.get("session_id", "")).startswith("mock"):
            continue
        rows.append((int(e.get("ts") or 0), str(e.get("officer") or "unknown")[:64], None, e.get("session_id"),
                     e.get("reasoning_id"), e.get("question", "")[:2000], q, e["rating"], e.get("note"),
                     e.get("lang"), e.get("template_id")))
    c.executemany("INSERT OR REPLACE INTO answer_feedback (ts, officer, role, session_id, reasoning_id, question, "
                  "qnorm, rating, note, lang, template_id, answer, answer_source) "
                  "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'imported')", rows)
    c.commit()


def _read() -> list[dict]:
    """Every current vote (one per officer per question)."""
    try:
        c = _conn()
    except sqlite3.Error:
        return []
    try:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute("SELECT * FROM answer_feedback ORDER BY ts")]
    finally:
        c.close()


def _tally() -> dict[str, dict]:
    """question -> {up, down, lang, last_ts, template_id, officers, has_answer}"""
    agg: dict[str, dict] = {}
    for e in _read():
        q = e["qnorm"]
        a = agg.setdefault(q, {"question": e["question"], "up": 0, "down": 0, "lang": e.get("lang"),
                               "template_id": e.get("template_id"), "last_ts": 0, "officers": set(),
                               "has_answer": False})
        a[e["rating"]] += 1
        a["last_ts"] = max(a["last_ts"], int(e.get("ts") or 0))
        a["officers"].add(e["officer"])
        if e.get("lang"):
            a["lang"] = e["lang"]
        if e.get("template_id"):
            a["template_id"] = e["template_id"]
        if e["rating"] == "up" and e.get("answer") and e.get("answer_source") == "server":
            a["has_answer"] = True
    return agg


def _answer_for(session_id: str, reasoning_id: str | None, question: str) -> dict | None:
    """The answer this server gave in that conversation: by reasoning id, else the latest
    answer to the same question. None when the conversation is no longer held."""
    from app.core import sessions
    turns = sessions.all_turns(session_id)
    want = _norm(question)
    hit = None
    for i, t in enumerate(turns):
        if t.get("role") != "assistant":
            continue
        if reasoning_id and t.get("reasoning_id") == reasoning_id:
            return t
        asked = (t.get("meta") or {}).get("question")
        if asked is None and i and turns[i - 1].get("role") == "user":
            asked = turns[i - 1].get("text")
        if not reasoning_id and _norm(asked or "") == want:
            hit = t
    return hit


# ── what the ratings teach ───────────────────────────────────────────────────

# Words that carry no topic, so two questions are not "similar" for sharing them.
_STOP = frozenset(
    "a an and are by for from give has have how in is list many me of on show tell that "
    "the there these this to what which with".split())
_SPLIT_RE = re.compile(r"[\s,.;:?!()\"'/\-]+")


def _terms(q: str) -> set[str]:
    # Split on punctuation rather than \w+: \w breaks Kannada words at every vowel sign.
    return {t for t in _SPLIT_RE.split(_norm(q)) if len(t) > 2 and t not in _STOP}


def learned_examples(question: str, lang: str = "en", k: int = 2,
                     min_similarity: float = 0.3) -> list[dict]:
    """Answers officers rated useful for questions like this one, most similar first.

    An example qualifies only when
      - more officers rated that question up than down (each officer counts once),
      - its answer is one this server gave (never text a browser sent),
      - it is in the language being answered,
      - it shares enough topic words with the question to be the same kind of answer, and
      - it carries no instruction-shaped text.
    """
    want = _terms(question)
    if not want:
        return []
    by_q: dict[str, dict] = {}
    for e in _read():
        g = by_q.setdefault(e["qnorm"], {"up": 0, "down": 0, "best": None})
        g[e["rating"]] += 1
        if (e["rating"] == "up" and e.get("answer") and e.get("answer_source") == "server"
                and e.get("lang") == lang):
            g["best"] = e                       # ordered by time: the last one is the newest
    from app.core.rag_security import detect_injection
    scored = []
    for q, g in by_q.items():
        e = g["best"]
        if e is None or g["up"] <= g["down"]:
            continue
        have = _terms(q)
        sim = len(want & have) / len(want | have) if have else 0.0
        if sim < min_similarity or detect_injection(f"{e['question']}\n{e['answer']}"):
            continue
        scored.append((sim, int(e.get("ts") or 0),
                       {"question": e["question"], "answer": e["answer"],
                        "up": g["up"], "down": g["down"], "similarity": round(sim, 2)}))
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
    return [s[2] for s in scored[:k]]


# ── routes ───────────────────────────────────────────────────────────────────

@router.post("")
@router.post("/")
async def submit_feedback(req: FeedbackRequest, request: Request) -> dict:
    from app.core.auth_middleware import current_identity
    ident = current_identity(request)
    turn = _answer_for(req.session_id, req.reasoning_id, req.question)
    owner = ((turn or {}).get("meta") or {}).get("officer")
    if turn is not None and owner and owner != ident.officer:
        raise HTTPException(status_code=403, detail="That answer was given in another officer's conversation.")
    answer = (turn or {}).get("text") or None
    entry = {
        "ts": int(time.time()), "officer": ident.officer, "role": ident.role,
        "session_id": req.session_id, "reasoning_id": (turn or {}).get("reasoning_id") or req.reasoning_id,
        "question": req.question, "qnorm": _norm(req.question), "rating": req.rating, "note": req.note,
        "lang": (turn or {}).get("lang") or req.lang, "template_id": (turn or {}).get("template_id") or req.template_id,
        "answer": answer[:4000] if answer else None, "answer_source": "server" if answer else "none",
    }
    c = _conn()
    try:
        replaced = c.execute("SELECT 1 FROM answer_feedback WHERE officer = ? AND qnorm = ?",
                             (entry["officer"], entry["qnorm"])).fetchone() is not None
        c.execute(f"INSERT OR REPLACE INTO answer_feedback ({', '.join(entry)}) VALUES ({', '.join('?' * len(entry))})",
                  tuple(entry.values()))
        c.commit()
    finally:
        c.close()
    try:
        from app.services import audit_store
        audit_store.record(ident.officer, ident.role, "FEEDBACK", f"/api/feedback:{req.rating}", 200)
    except Exception:
        pass
    return {"recorded": True, "rating": req.rating, "ts": entry["ts"], "replaced_earlier_vote": replaced,
            "answer_kept": entry["answer_source"] == "server"}


@router.get("/stats")
async def feedback_stats() -> dict:
    rows = _read()
    up = sum(1 for e in rows if e["rating"] == "up")
    down = sum(1 for e in rows if e["rating"] == "down")
    return {"up": up, "down": down, "total": up + down,
            "officers": len({e["officer"] for e in rows}),
            "usable_as_examples": sum(1 for a in _tally().values() if a["up"] > a["down"] and a["has_answer"])}


@router.get("/signal")
async def feedback_signal(lang: str | None = None, limit: int = 12) -> dict:
    """What officers' ratings say about which questions to offer.

    promote — rated good more often than bad: offer these sooner.
    avoid   — rated bad and never recovered: stop suggesting until the review is done.
    Deterministic counting, no model involved, and it only ever changes what is
    SUGGESTED — never an answer.
    """
    agg = _tally()
    promote, avoid = [], []
    for q, a in agg.items():
        if lang and a.get("lang") and a["lang"] != lang:
            continue
        if a["down"] > a["up"]:
            avoid.append(q)
        elif a["up"] > a["down"]:
            promote.append({"question": a["question"], "up": a["up"], "down": a["down"],
                            "last_ts": a["last_ts"]})
    promote.sort(key=lambda r: (r["up"] - r["down"], r["last_ts"]), reverse=True)
    return {"promote": promote[:limit], "avoid": avoid[:200],
            "rated_questions": len(agg)}


@router.get("/review", dependencies=[Depends(require_role("Admin"))])
async def feedback_review(limit: int = 50) -> dict:
    """The queue of answers officers marked poor — what to fix next, newest first.

    This is the part that makes the loop real: a thumbs-down is a work item with the
    question, the template that produced it and the officers who hit it, not a counter.
    """
    rows = []
    for q, a in _tally().items():
        if a["down"] <= 0 or a["down"] < a["up"]:
            continue
        rows.append({"question": a["question"], "lang": a.get("lang"), "down": a["down"],
                     "up": a["up"], "template_id": a.get("template_id"),
                     "officers": len(a["officers"]), "last_ts": a["last_ts"]})
    rows.sort(key=lambda r: (r["down"], r["last_ts"]), reverse=True)
    return {"count": len(rows), "items": rows[:limit]}
