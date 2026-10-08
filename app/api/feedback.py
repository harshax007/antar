"""
Antar — Answer Feedback
============================
POST /api/feedback         {session_id, reasoning_id?, question, rating: "up"|"down", note?}
GET  /api/feedback/stats
GET  /api/feedback/signal  what the ratings have taught: questions to promote / avoid
GET  /api/feedback/review  the queue of poorly-rated answers, for an Admin to work through

The signal is the honest half of "self-improving": nothing is silently rewritten. A
down-rated question stops being SUGGESTED and lands in a review queue a human works
through; an up-rated one is offered sooner. The records and the templates never change
because of a rating.

Officer feedback on AI answers, persisted append-only (JSONL beside the db)
and mirrored into the audit trail so ratings are inspectable next to the
answers they rate.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth_middleware import require_role

router = APIRouter()

_FILE = Path(__file__).resolve().parents[2] / "data_feedback.jsonl"


class FeedbackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    reasoning_id: str | None = None
    question: str = Field(min_length=1, max_length=2000)
    rating: Literal["up", "down"]
    note: str | None = Field(default=None, max_length=2000)
    officer: str = "OF-1001"
    # Context, so a rating can be acted on later without guessing what was rated.
    lang: str | None = Field(default=None, max_length=8)
    template_id: str | None = Field(default=None, max_length=16)
    answer: str | None = Field(default=None, max_length=4000)


def _norm(q: str) -> str:
    return " ".join((q or "").strip().lower().split())


def _read() -> list[dict]:
    if not _FILE.exists():
        return []
    out = []
    for line in _FILE.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _tally() -> dict[str, dict]:
    """question -> {up, down, lang, last_ts, template_id, officers}"""
    agg: dict[str, dict] = {}
    for e in _read():
        q = _norm(e.get("question", ""))
        if not q:
            continue
        a = agg.setdefault(q, {"question": e.get("question", ""), "up": 0, "down": 0,
                               "lang": e.get("lang"), "template_id": e.get("template_id"),
                               "last_ts": 0, "officers": set()})
        if e.get("rating") in ("up", "down"):
            a[e["rating"]] += 1
        a["last_ts"] = max(a["last_ts"], int(e.get("ts") or 0))
        if e.get("lang"):
            a["lang"] = e["lang"]
        if e.get("template_id"):
            a["template_id"] = e["template_id"]
        if e.get("officer"):
            a["officers"].add(e["officer"])
    return agg


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

    The file is read on every call: it is small, the LLM call it feeds takes seconds, and
    a rating therefore counts from the next question on rather than the next restart.
    An example qualifies only when
      - officers rated that question up more often than down (a thumbs-down vetoes it),
      - it is in the language being answered,
      - it shares enough topic words with the question to be the same kind of answer, and
      - it carries no instruction-shaped text - the rating endpoint accepts free text, and
        what it stores is replayed into a prompt.
    """
    want = _terms(question)
    if not want:
        return []
    by_q: dict[str, dict] = {}
    for e in _read():
        q = _norm(e.get("question", ""))
        if not q or e.get("rating") not in ("up", "down"):
            continue
        g = by_q.setdefault(q, {"up": 0, "down": 0, "best": None})
        g[e["rating"]] += 1
        if e["rating"] == "up" and e.get("answer") and e.get("lang") == lang:
            g["best"] = e                       # append-only file: the last one is the newest
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


@router.post("")
@router.post("/")
async def submit_feedback(req: FeedbackRequest) -> dict:
    entry = {**req.model_dump(), "ts": int(time.time())}
    with _FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    try:
        from app.services import audit_store
        audit_store.record(req.officer, "Officer", "FEEDBACK",
                           f"/api/feedback:{req.rating}", 200)
    except Exception:
        pass
    return {"recorded": True, "rating": req.rating, "ts": entry["ts"]}


@router.get("/stats")
async def feedback_stats() -> dict:
    up = down = 0
    for e in _read():
        r = e.get("rating")
        if r == "up":
            up += 1
        elif r == "down":
            down += 1
    return {"up": up, "down": down, "total": up + down}


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
