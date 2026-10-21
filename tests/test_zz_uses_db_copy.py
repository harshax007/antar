"""The suite must never run on the live demo database (tests/conftest.py makes a copy)."""
import os


def test_the_suite_runs_on_a_copy_of_main_db():
    from app.core.db_path import DB_PATH
    if os.getenv("ANTAR_TEST_LIVE_DB") == "1":
        return
    assert "antar_test_db_" in str(DB_PATH), DB_PATH
