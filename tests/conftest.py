"""
Pytest config — force tests into deterministic OFFLINE mode regardless of the
developer's .env. (Live LLM is validated separately via scripts/g4_battery, not here.)

Without this, a populated .env (real QuickML creds, DEMO_MODE=false) would make
/api/chat attempt live LLM calls during unit tests → non-deterministic / network-dependent.

The same applies to Hugging Face: main.py forces HF_HUB_OFFLINE before anything imports
the hub, but tests import app modules directly and never load main. A test that builds a
SentenceTransformer or CrossEncoder therefore went to the network and re-downloaded an
88 MB snapshot into the cache (observed 2026-09-23). Tests must never depend on the
network, and must never change the model cache they are measuring against.
"""

import os

# Must run before anything imports huggingface_hub: it reads these once, at import time.
if os.getenv("ANTAR_BRAIN_ONLINE") != "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Same reason main.py does this, and for the same reason it needs saying twice: tests
# import app modules directly and never load main. On a torch-free environment,
# scikit-learn's OpenMP runtime loading before onnxruntime's kills the interpreter with a
# Windows access violation (measured 2026-09-24 — see the comment in main.py). A test
# session that imported sklearn first would die with no traceback and no failing test.
try:
    import onnxruntime as _onnxruntime  # noqa: F401
except Exception:
    pass

import sqlite3

import pytest

# The suite runs against a COPY of main.db, taken once per session with SQLite's backup API
# (consistent even while the backend has the file open; ~7 s for 1.5 GB). Tests used to run
# on the live demo database: write paths persisted into it, and the clean-up below had to
# guess which rows were the suite's, so a backend writing at the same moment lost rows and
# "stop the backend before running pytest" was a rule. Must happen before anything imports
# app.core.db_path, which reads ANTAR_DB once. ANTAR_TEST_LIVE_DB=1 runs on the live file.
# Conversations stay in memory under test: the suite must not write the live session file.
os.environ.setdefault("ANTAR_SESSIONS", "memory")

if os.getenv("ANTAR_TEST_LIVE_DB") != "1":
    import atexit
    import shutil
    import tempfile
    from pathlib import Path

    _root = Path(__file__).resolve().parents[1]
    _src = Path(os.environ.get("ANTAR_DB") or "main.db")
    _src = _src if _src.is_absolute() else _root / _src
    if _src.exists():
        # On Windows the copy can still be open when the interpreter exits, so the atexit
        # removal may fail; a copy left by an earlier run is removed here instead.
        for _old in Path(tempfile.gettempdir()).glob("antar_test_db_*"):
            shutil.rmtree(_old, ignore_errors=True)
        _tmp = Path(tempfile.mkdtemp(prefix="antar_test_db_"))
        _copy = _tmp / "main.db"
        with sqlite3.connect(f"file:{_src}?mode=ro", uri=True) as _a, sqlite3.connect(_copy) as _b:
            _a.backup(_b, pages=20000)
        os.environ["ANTAR_DB"] = str(_copy)
        atexit.register(shutil.rmtree, _tmp, ignore_errors=True)

from app.core.settings import settings


# The FIR count as it stood BEFORE this test session touched the database. Set by the
# session fixture below; None outside a test run.
BASELINE_FIR_COUNT: int | None = None


def _rowid_marks(con) -> dict[str, int]:
    """Highest rowid per table, so anything inserted after this point is identifiable."""
    marks: dict[str, int] = {}
    for (name,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'").fetchall():
        try:
            marks[name] = con.execute(f'SELECT COALESCE(MAX(rowid), 0) FROM "{name}"').fetchone()[0]
        except sqlite3.Error:
            pass          # WITHOUT ROWID table — nothing to mark
    return marks


# Tables the suite must never clean in main.db: the tests write these to a ledger of their
# own (see _audit_ledger_in_its_own_file), so any row above the mark was written by a
# backend that is serving the demo while the suite runs - deleting it breaks the hash chain.
_NEVER_CLEANED = {"audit_log", "agent_reasoning_logs"}


@pytest.fixture(scope="session", autouse=True)
def _audit_ledger_in_its_own_file(tmp_path_factory):
    """Point the audit store at a throwaway database for the whole session.

    The audit tests call `audit_store.clear()`, which deletes every row of `audit_log`.
    Against main.db that erased the demo's ledger (595 entries on 2026-10-11), and the
    clean-up below then removed rows a live backend wrote during the run, leaving
    /api/audit/integrity reporting a broken chain. A tamper-evident ledger that the test
    suite can wipe is not one, so the suite gets its own file and main.db is left alone.
    """
    from app.services import audit_store
    live = audit_store.DB_PATH
    audit_store.DB_PATH = str(tmp_path_factory.mktemp("audit") / "audit_ledger.db")
    audit_store._log.clear()
    audit_store._last_hash = "0" * 64
    audit_store.init_db()
    yield
    audit_store.DB_PATH = live


@pytest.fixture(scope="session", autouse=True)
def _keep_main_db_clean():
    """Remove rows the test run leaves behind in main.db.

    The suite runs against the real main.db — the same database the demo serves. Tests
    that exercise a write path therefore persist: `test_ingestion_csv_mapping` really
    ingests its sample row, so every run added one more FIR to Karnataka's crime registry
    ("Central" district, "Unknown" station, a Robbery on 2023-10-15). 25 of them had
    accumulated before this fixture existed.

    Copying a 1.2 GB database per session would cost more than the whole suite, so
    instead we mark the high-water rowid of every table up front and delete anything
    above those marks at the end. Rows that existed before the run are never touched.
    """
    from app.core.db_path import DB_PATH

    con = sqlite3.connect(str(DB_PATH))
    before = _rowid_marks(con)
    before_total = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
    con.close()

    # Published for tests that assert a registry-wide figure. Mid-session the live count
    # is NOT the registry count: the ingestion test really inserts a row and it is only
    # removed when this fixture tears down. A test that reads COUNT(*) directly is
    # therefore order-dependent, which is how tests/test_okf_bundle.py went green alone
    # and red in the full suite.
    global BASELINE_FIR_COUNT
    BASELINE_FIR_COUNT = before_total

    yield

    con = sqlite3.connect(str(DB_PATH))
    removed: dict[str, int] = {}
    try:
        for table, mark in before.items():
            if table in _NEVER_CLEANED:
                continue
            n = con.execute(f'DELETE FROM "{table}" WHERE rowid > ?', (mark,)).rowcount
            if n:
                removed[table] = n
        con.commit()

        # SQLite hands a freed rowid straight back to the next INSERT when the deleted row
        # was the highest one, so "rowid > mark" can miss a row that is genuinely new —
        # it lands exactly ON the mark. (Seen for real when two suites ran against this
        # database at once.) Fall back to removing the surplus newest rows so the registry
        # still balances.
        surplus = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0] - before_total
        if surplus > 0:
            con.execute("DELETE FROM FIRs WHERE rowid IN "
                        "(SELECT rowid FROM FIRs ORDER BY rowid DESC LIMIT ?)", (surplus,))
            con.commit()
            removed["FIRs"] = removed.get("FIRs", 0) + surplus
        after_total = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
    finally:
        con.close()

    if removed:
        print(f"\n[conftest] removed test-inserted rows: {removed}")
    if after_total < before_total:
        # Deleted rows cannot be restored from here; surface it loudly rather than
        # letting the demo dataset drift quietly.
        print(f"\n[conftest] WARNING: FIRs count fell {before_total:,} -> {after_total:,} "
              "— a test deleted pre-existing rows.")


@pytest.fixture(autouse=True)
def _force_offline(monkeypatch):
    # _llm_available() returns False → chat + agents use the heuristic/offline path.
    monkeypatch.setattr(settings, "QUICKML_CLIENT_ID", "", raising=False)
    monkeypatch.setattr(settings, "QUICKML_CLIENT_SECRET", "", raising=False)
    monkeypatch.setattr(settings, "QUICKML_ACCESS_TOKEN", "", raising=False)
    monkeypatch.setattr(settings, "QUICKML_REFRESH_TOKEN", "", raising=False)
    monkeypatch.setattr(settings, "DEMO_MODE", False, raising=False)
    # Header identity unless a test opts in: a developer's .env may now carry
    # ANTAR_AUTH_SECRET, which would put every TestClient call behind a token.
    monkeypatch.setattr(settings, "ANTAR_AUTH_SECRET", "", raising=False)
