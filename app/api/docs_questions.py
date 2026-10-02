"""
Antar — Question Bank API for /docs rotating demo questions.

GET /api/docs/questions          → all 35 questions
GET /api/docs/questions?set=<n>  → the 3-4 questions for that set index (0-8)
"""
from __future__ import annotations
import os, sqlite3
from fastapi import APIRouter
from app.services.zcql_local import DB_PATH

router = APIRouter()

INTEL_DB = os.path.join(os.path.dirname(DB_PATH), "intelligent.db")


def _intel_conn() -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{INTEL_DB}?immutable=1", uri=True)
    c.row_factory = sqlite3.Row
    return c


@router.get("/questions")
async def get_questions(set: int | None = None) -> dict:
    """Return question bank. If `set` is given (0-8), return only that set's 3-4 questions."""
    con = _intel_conn()
    try:
        # Check table exists
        tables = {r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "question_bank" not in tables:
            return {"questions": [], "total": 0, "set": set}

        if set is not None:
            rows = con.execute(
                "SELECT * FROM question_bank WHERE set_index = ? ORDER BY id", [set]
            ).fetchall()
        else:
            rows = con.execute("SELECT * FROM question_bank ORDER BY id").fetchall()
    finally:
        con.close()

    questions = [{
        "id": r["id"],
        "verb": r["verb"],
        "tier": r["tier"],
        "set_index": r["set_index"],
        "question_en": r["question_en"],
        "question_kn": r["question_kn"],
        "expected_answer": r["expected_answer"],
        "mechanism": r["mechanism"],
        "story_id": r["story_id"],
    } for r in rows]

    return {
        "questions": questions,
        "total": len(questions),
        "set": set,
        "total_sets": 9,
    }
