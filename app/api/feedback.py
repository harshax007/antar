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
