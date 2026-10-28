"""
Case timeline (app/services/case_timeline.py, GET /api/case/{fir_id}).

The summary and every step are read from the FIR row; only the registration is dated, so a
later step is never given a date. Who may open a case follows the same rules as chat.
"""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.db_path import DB_PATH
from app.services import case_timeline as ct


def _fir(stage: str) -> str:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        return con.execute("SELECT fir_id FROM FIRs WHERE FIR_Stage = ? AND is_synthetic_row = 0 "
                           "AND date <= date('now') LIMIT 1", (stage,)).fetchone()[0]
    finally:
        con.close()


class TestTimeline:
    def test_a_convicted_case_reads_start_to_finish(self):
        d = ct.timeline(_fir("Convicted"))
        assert [s["key"] for s in d["steps"]] == ["registered", "investigation", "arrest", "chargesheet", "court"]
        assert d["steps"][0]["date"] == d["registered"]                     # the one recorded date
        assert all("date" not in s for s in d["steps"][1:])                 # never a guessed date
        assert d["steps"][-1]["title"] == "Convicted" and d["steps"][-1]["date_missing"]
        assert "Convicted." in d["summary"] and d["registered"]

    def test_an_open_case_carries_the_investigation_clock(self):
        d = ct.timeline(_fir("Under Investigation"))
        inv = next(s for s in d["steps"] if s["key"] == "investigation")
        assert inv["state"] == "current" and isinstance(inv["days_open"], int)
        assert "60" in inv["detail"] or "90" in inv["detail"]
        assert next(s for s in d["steps"] if s["key"] == "court")["state"] == "pending"

    def test_an_undetected_case_never_reaches_court(self):
        d = ct.timeline(_fir("Undetected"))
        assert next(s for s in d["steps"] if s["key"] == "court")["state"] == "none"
        assert "undetected" in d["summary"].lower()

    def test_similar_cases_are_counted_and_this_case_is_left_out(self):
        d = ct.timeline(_fir("Pending Trial"))
        sim = d["similar"]
        assert sim and sim["cases"] >= ct.MIN_SIMILAR or sim["scope"] == "state"
        assert all(0 <= v <= 100 for v in (sim["reached_court"], sim["undetected"]) if v is not None)

    def test_the_crime_label_reads_on_its_own(self):
        assert ct._crime_label("THEFT", "Of Cattle") == "Theft (of cattle)"
        assert ct._sections("IPC 1860 U/s: 338 && IPC 1860 U/s: 337") == ["IPC 338", "IPC 337"]

    def test_an_unknown_fir_is_none(self):
        assert ct.timeline("NO-SUCH-FIR") is None


class TestEndpoint:
    def test_an_officer_opens_a_case(self):
        from main import app
        r = TestClient(app).get(f"/api/case/{_fir('Convicted')}", headers={"X-Role": "Inspector"})
        assert r.status_code == 200 and r.json()["steps"] and "zone" not in r.json()

    def test_unknown_is_404(self):
        from main import app
        assert TestClient(app).get("/api/case/NO-SUCH-FIR", headers={"X-Role": "Inspector"}).status_code == 404

    def test_below_analyst_a_case_outside_the_posting_is_refused(self):
        from main import app
        fir = _fir("Convicted")
        d = ct.timeline(fir)
        other = "Mysuru City" if (d["district"] or "").upper() != "MYSURU CITY" else "Bagalkot"
        r = TestClient(app).get(f"/api/case/{fir}", headers={"X-Role": "Constable", "X-Posting": other})
        assert r.status_code == 403 and "posting" in r.json()["detail"]


class TestBrainRecords:
    """Records of the Brain's curated dataset open as cases too, as B-<id>."""

    def test_a_brain_record_reads_as_a_case(self):
        import os
        if not os.path.exists(ct.INTEL_DB):
            pytest.skip("intelligent.db not present")
        d = ct.timeline("B-1")
        assert d["source"] == "brain" and d["fir_id"] == "B-1"
        assert [s["key"] for s in d["steps"]] == ["registered", "investigation", "arrest", "chargesheet", "court"]
        assert d["victims"] == [] and "Brain" in d["recorded"]
        others = d["same_accused"]
        assert others is None or all(f["fir_id"].startswith("B-") for f in others["firs"])

    def test_an_unknown_brain_record_is_404(self):
        from main import app
        assert TestClient(app).get("/api/case/B-99999999", headers={"X-Role": "Inspector"}).status_code == 404


class TestKannada:
    def test_every_line_of_the_case_comes_in_kannada_too(self):
        for stage in ("Convicted", "Under Investigation", "Undetected", "Pending Trial"):
            d = ct.timeline(_fir(stage))
            assert d["summary_kn"] and d["recorded_kn"] and d["summary_kn"] != d["summary"]
            for s in d["steps"]:
                assert s["title_kn"] and s["title_kn"] != s["title"]
                assert bool(s["detail_kn"]) == bool(s["detail"])
                assert ("note" in s) == ("note_kn" in s)

    def test_the_open_case_clock_dates_the_60_and_90_day_marks(self):
        from datetime import date, timedelta
        d = ct.timeline(_fir("Under Investigation"))
        k = d["clock"]
        reg = date.fromisoformat(d["registered"])
        assert k["short_date"] == (reg + timedelta(days=60)).isoformat()
        assert k["long_date"] == (reg + timedelta(days=90)).isoformat()
        assert k["day"] == next(s for s in d["steps"] if s["key"] == "investigation")["days_open"]
        assert ct.timeline(_fir("Convicted"))["clock"] is None


def test_a_case_opens_by_its_crime_number_alone():
    # the case sheet prints the crime number and chat answers list FIRs by it; opening one
    # needed the station too, so every such link was a 404
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        fid, crime_no = con.execute("SELECT fir_id, CrimeNo FROM FIRs WHERE is_synthetic_row = 0 AND LENGTH(CrimeNo) >= 16 "
                                    "AND date <= date('now') LIMIT 1").fetchone()
    finally:
        con.close()
    d = ct.timeline(crime_no)
    assert d is not None and d["fir_id"] == fid
    assert ct.timeline("99999999999999999") is None


def test_the_layout_reaches_the_page_before_the_answer_text():
    # sent after the tokens, it made the page draw the streamed text and then redraw it in
    # the layout's shape: the answer visibly reformatted itself
    import inspect
    from app.api import chat_stream
    src = inspect.getsource(chat_stream)
    assert src.index('await q.emit("layout"') < src.index("async for chunk in token_stream(answer, delay_s=0.002)")
