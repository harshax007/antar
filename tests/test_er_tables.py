"""
test_er_tables.py — Unit tests for Official ER Schema Tables (Phase L2).
========================================================================
Asserts:
1. Foreign key integrity check returns no broken links.
2. CaseMaster row count matches FIRs row count.
3. Person tables (Accused, Victim, ComplainantDetails) exist, are honestly empty,
   and have accompanying notes in ext_schema_notes.
4. CrimeNoOfficial is strictly 18 characters long for every record.
5. ActSectionAssociation successfully parsed >= 99.5% of non-empty ActSection rows.
"""
from __future__ import annotations

import sqlite3
import pytest
from pathlib import Path

from app.core.db_path import DB_PATH


def er_tables_exist() -> bool:
    p = Path(DB_PATH)
    if not p.exists():
        return False
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='CaseMaster'")
        return bool(cur.fetchone())
    finally:
        con.close()


@pytest.mark.skipif(not er_tables_exist(), reason="Official ER tables not yet built in current DB")
def test_fk_check_clean():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        con.execute("PRAGMA foreign_keys = ON;")
        errors = con.execute("PRAGMA foreign_key_check;").fetchall()
        assert len(errors) == 0, f"Foreign key check returned {len(errors)} broken relationships: {errors[:5]}"
    finally:
        con.close()


@pytest.mark.skipif(not er_tables_exist(), reason="Official ER tables not yet built in current DB")
def test_casemaster_row_count():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        cm_count = con.execute("SELECT COUNT(*) FROM CaseMaster").fetchone()[0]
        firs_count = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        assert cm_count == firs_count, f"CaseMaster ({cm_count}) does not match FIRs count ({firs_count})"
    finally:
        con.close()


@pytest.mark.skipif(not er_tables_exist(), reason="Official ER tables not yet built in current DB")
def test_person_tables_empty_with_notes():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        for table in ("Accused", "Victim", "ComplainantDetails"):
            cnt = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert cnt == 0, f"Person table {table} should have 0 rows in extract (found {cnt})"

        notes = con.execute("SELECT topic FROM ext_schema_notes").fetchall()
        topics = {r[0] for r in notes}
        assert "Accused" in topics, "Missing ext_schema_notes entry for Accused"
        assert "Victim" in topics, "Missing ext_schema_notes entry for Victim"
        assert "ComplainantDetails" in topics, "Missing ext_schema_notes entry for ComplainantDetails"
    finally:
        con.close()


@pytest.mark.skipif(not er_tables_exist(), reason="Official ER tables not yet built in current DB")
def test_crimenoofficial_format():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        # Check lengths: must all be exactly 18 chars
        bad = con.execute("""
            SELECT CaseMasterID, CrimeNoOfficial, LENGTH(CrimeNoOfficial)
            FROM CaseMaster
            WHERE LENGTH(CrimeNoOfficial) != 18
            LIMIT 10
        """).fetchall()
        assert len(bad) == 0, f"Found CrimeNoOfficial values with length != 18: {bad}"

        # Sample check first character is '1'
        sample = con.execute("SELECT CrimeNoOfficial FROM CaseMaster LIMIT 100").fetchall()
        for r in sample:
            assert r[0].startswith("1"), f"CrimeNoOfficial must start with category '1': {r[0]}"
            assert r[0].isdigit(), f"CrimeNoOfficial must be numeric: {r[0]}"
    finally:
        con.close()


@pytest.mark.skipif(not er_tables_exist(), reason="Official ER tables not yet built in current DB")
def test_act_section_associations():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        firs_with_acts = con.execute("""
            SELECT COUNT(*) FROM FIRs WHERE ActSection IS NOT NULL AND TRIM(ActSection) != ''
        """).fetchone()[0]

        cases_with_assoc = con.execute("""
            SELECT COUNT(DISTINCT CaseMasterID) FROM ActSectionAssociation
        """).fetchone()[0]

        coverage = cases_with_assoc / max(1, firs_with_acts)
        assert coverage >= 0.995, f"ActSection parse coverage {coverage:.1%} < 99.5%"
    finally:
        con.close()
