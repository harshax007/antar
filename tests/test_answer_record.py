"""
Antar - the Expert workspace's Copy is the audited answer, word for word
========================================================================
POST /api/answer-record/{hash}/copy builds the brief from the AI_REASONING entry in the
audit log, not from the screen, and records the copy (with the SHA-256 of the exact text)
on the chain. A missing or tampered entry is refused, never copied from somewhere else.
"""
import asyncio
import hashlib
import sqlite3

import pytest
from fastapi import HTTPException

from app.api import answer_record
from app.services import audit_store


@pytest.fixture(autouse=True)
def _ledger(tmp_path, monkeypatch):
    # Its own file: clear() deletes every row of audit_log.
    monkeypatch.setattr(audit_store, "DB_PATH", str(tmp_path / "ledger.db"))
    monkeypatch.setattr(audit_store, "_sync_to_catalyst_placeholder", lambda entry: None)
    audit_store.init_db()
    audit_store.clear()
    yield
    audit_store.clear()


class _Ident:
    def __init__(self, officer, role):
        self.officer, self.role = officer, role


def _as(monkeypatch, officer, role="Inspector"):
    monkeypatch.setattr(answer_record, "current_identity", lambda request: _Ident(officer, role))


ANSWER = "**996,894** cases are on record; here are the latest 25.\n- FIR SYN-2026-000708 · Pending trial"
CITES = [{"fir": "SYN-2026-000708", "station": "CID", "section": "BNS 106", "date": "2026-12-29"}]


def _answer():
    return audit_store.record_ai_reasoning("OFF-1", "sess-1", "Show the latest cases", ANSWER,
                                           ["query"], CITES, reasoning_id=None)


def test_copy_is_the_audited_text_and_is_recorded(monkeypatch):
    h = _answer()
    _as(monkeypatch, "OFF-1")
    out = asyncio.run(answer_record.copy_answer(h, request=None))
    assert ANSWER in out["text"]                              # verbatim, markdown and all
    assert "Show the latest cases" in out["text"] and h in out["text"]
    assert "FIR SYN-2026-000708, CID, BNS 106, 2026-12-29" in out["text"]
    assert out["copy_sha256"] == hashlib.sha256(out["text"].encode("utf-8")).hexdigest()
    ev = [e for e in audit_store.query(limit=10) if e["type"] == "ANSWER_COPIED"]
    assert len(ev) == 1 and ev[0]["answer_hash"] == h and ev[0]["copy_sha256"] == out["copy_sha256"]
    assert audit_store.verify_chain_report()["ok"]


def test_tampered_answer_is_not_copied(monkeypatch):
    h = _answer()
    conn = sqlite3.connect(audit_store.DB_PATH)
    raw = conn.execute("SELECT payload_json FROM audit_log WHERE hash = ?", (h,)).fetchone()[0]
    conn.execute("UPDATE audit_log SET payload_json = ? WHERE hash = ?", (raw.replace("996,894", "996,895"), h))
    conn.commit(); conn.close()
    _as(monkeypatch, "OFF-1")
    with pytest.raises(HTTPException) as e:
        asyncio.run(answer_record.copy_answer(h, request=None))
    assert e.value.status_code == 409
    assert not any(x["type"] == "ANSWER_COPIED" for x in audit_store.query(limit=10))


def test_unknown_hash_and_other_officer_are_refused(monkeypatch):
    h = _answer()
    _as(monkeypatch, "OFF-2")
    with pytest.raises(HTTPException) as e:
        asyncio.run(answer_record.copy_answer(h, request=None))
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        asyncio.run(answer_record.copy_answer("f" * 64, request=None))
    assert e.value.status_code == 404
    _as(monkeypatch, "ADMIN-1", "Admin")
    assert asyncio.run(answer_record.copy_answer(h, request=None))["answer_hash"] == h
