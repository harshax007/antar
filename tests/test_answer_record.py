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


# ── Antar Insights ────────────────────────────────────────────────────────────
from app.services import answer_insights


def _register(tmp_path, rows):
    con = sqlite3.connect(tmp_path / "reg.db")
    cols = [c.strip() for c in answer_insights._COLS.split(",")]
    con.execute(f"CREATE TABLE FIRs ({', '.join(cols)})")
    for r in rows:
        base = {c: None for c in cols}
        base.update(r)
        con.execute(f"INSERT INTO FIRs VALUES ({','.join('?' * len(cols))})", [base[c] for c in cols])
    con.commit()
    return con


def test_insights_are_arithmetic_over_the_cited_firs(tmp_path):
    answer_insights._baseline.clear()
    rows = [dict(fir_id=f"F{i}", station="Whitefield PS", district_norm="Bengaluru City", crime_type="THEFT",
                 date=f"2026-01-{i + 1:02d}", FIR_Stage="Under Investigation", Accused_Count=2, Arrested_Count_No_=0,
                 Vehicle_Reg_No="KA01AB1234" if i < 2 else "", Girl=1 if i == 0 else 0) for i in range(4)]
    rows.append(dict(fir_id="F9", station="Other PS", district_norm="Mysuru", crime_type="THEFT", date="2026-01-09",
                     FIR_Stage="Convicted", Accused_Count=1, Arrested_Count_No_=1))
    con = _register(tmp_path, rows)
    out = answer_insights.compute(["F0", "F1", "F2", "F3", "F9", "MISSING"], con=con)
    by = {i["kind"]: i for i in out["items"]}
    assert out["basis"] == 5
    assert by["victims"]["firs"] == ["F0"] and out["items"][0]["kind"] == "victims"   # child victims first
    assert by["shared"]["firs"] == ["F0", "F1"] and "KA01AB1234" in by["shared"]["text"]
    assert "9 accused named across 5 FIRs; 1 arrested (11%)" in by["arrests"]["text"]
    assert by["place"]["title"] == "4 at Whitefield PS"
    assert all(set(i["firs"]) <= {"F0", "F1", "F2", "F3", "F9"} for i in out["items"])   # only what was cited


def test_no_insight_without_enough_firs(tmp_path):
    con = _register(tmp_path, [dict(fir_id="F0", station="X", date="2026-01-01")])
    assert answer_insights.compute(["F0"], con=con)["items"] == []
    assert answer_insights.compute([], con=con)["items"] == []
