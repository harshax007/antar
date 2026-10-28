"""
schema_api.py — Official Karnataka Police ER Schema API (Phase L2).
===================================================================
Exposes the official ER schema structure, table row counts, fill rates,
and integrity notes via GET /api/schema/er.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List
from fastapi import APIRouter

from app.core.db_path import DB_PATH
from app.core.edition import is_lab

router = APIRouter()


@router.get("/er")
def get_er_schema() -> Dict[str, Any]:
    """
    Returns official ER schema tables, columns, row counts, fill rates, and notes.
    """
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        # Check if CaseMaster exists
        cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='CaseMaster'")
        has_er = bool(cur.fetchone())

        if not has_er:
            return {
                "edition": "lab" if is_lab() else "cloud",
                "available": False,
                "message": "Official ER tables are available in the Antar Lab edition.",
                "tables": [],
                "fill_rates": [],
                "notes": [],
            }

        # Query fill rates
        cur = con.execute("SELECT table_name, rows, columns, filled_pct, source, note FROM er_fill_rates")
        fill_rates = [dict(r) for r in cur.fetchall()]

        # Query notes from ext_schema_notes
        cur = con.execute("SELECT note_id, topic, note FROM ext_schema_notes ORDER BY note_id")
        notes = [dict(r) for r in cur.fetchall()]

        # List of official tables
        official_tables = [
            "CaseMaster",
            "ActSectionAssociation",
            "Section",
            "CrimeHeadActSection",
            "arrest_counts",
            "case_person_counts",
            "District",
            "Unit",
            "Employee",
            "CaseInvestigatingOfficer",
            "Accused",
            "Victim",
            "ComplainantDetails",
        ]

        tables_meta: List[Dict[str, Any]] = []
        for tname in official_tables:
            # Check if table exists
            t_check = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tname,)).fetchone()
            if not t_check:
                continue

            cnt_row = con.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()
            row_count = cnt_row[0] if cnt_row else 0

            cols_info = con.execute(f"PRAGMA table_info({tname})").fetchall()
            cols = [{"cid": c["cid"], "name": c["name"], "type": c["type"], "pk": c["pk"]} for c in cols_info]

            tables_meta.append({
                "table_name": tname,
                "rows": row_count,
                "column_count": len(cols),
                "columns": cols,
            })

        return {
            "edition": "lab" if is_lab() else "cloud",
            "available": True,
            "table_count": len(tables_meta),
            "tables": tables_meta,
            "fill_rates": fill_rates,
            "notes": notes,
        }

    finally:
        con.close()
