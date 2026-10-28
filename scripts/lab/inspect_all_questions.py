import sqlite3
import json
from pathlib import Path

# 1. Inspect question_bank
con = sqlite3.connect("intelligent.db")
con.row_factory = sqlite3.Row
qb_rows = con.execute("SELECT * FROM question_bank ORDER BY id").fetchall()
print(f"question_bank total: {len(qb_rows)}")
for r in qb_rows[:10]:
    d = dict(r)
    print(f"[{d['id']}] {d['tier']} | EN: {d['question_en']} | KN: {d['question_kn']}")
    print(f"      mechanism: {d['mechanism']} | expected: {d['expected_answer']}")
con.close()

# 2. Inspect officer_questions
from app.agents.officer_questions import OFFICER_QUESTIONS
print(f"\nofficer_questions total: {len(OFFICER_QUESTIONS)}")
for q in OFFICER_QUESTIONS[:10]:
    print(f"EN: {q['en']} | KN: {q['kn']} | suite: {q.get('suite')}")
