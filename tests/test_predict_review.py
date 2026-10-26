"""Predict's "Mark as reviewed" and "Audit trail" buttons, end to end.

The review button used to POST to /api/audit, which has no POST route: the screen said
"Marked as reviewed" and nothing was recorded. The audit trail fell through to a generic
chain naming steps a forecast never runs.
"""
from fastapi.testclient import TestClient


def _client():
    from main import app
    return TestClient(app)


def test_a_review_is_written_to_the_audit_chain_and_shows_on_the_trail():
    from app.services.product_store import put_product
    from app.services import audit_store

    card = {"zone": "Testzone", "crime_type": "MISSING PERSON", "z_score": 5.4,
            "conformal_lo": 0, "conformal_hi": 3, "coverage": "91%",
            "evidence_row_ids": ["FIR-1", "FIR-2"], "confidence_level": "Medium",
            "confidence_reasons": ["40 cases of this type are on record here in the last 52 weeks."],
            "as_of": "2026-10-26"}
    put_product("warning_ledger:board:Testzone:MISSING PERSON", card, ttl=600)

    c = _client()
    h = {"X-Role": "Inspector", "X-Officer": "review-test"}
    r = c.post("/api/predict/Testzone/reviewed", params={"crime_type": "MISSING PERSON"}, headers=h)
    assert r.status_code == 200 and r.json()["reviewed"] is True
    row = audit_store.query("review-test", limit=1)[0]
    assert row["scope"]["forecast_review"] == {"zone": "Testzone", "crime_type": "MISSING PERSON"}

    t = c.get("/api/derivation/board:Testzone:MISSING PERSON", headers=h).json()
    assert t["kind"] == "forecast" and t["evidence_rows"] == ["FIR-1", "FIR-2"]
    text = " ".join(s["detail"] for s in t["derivation_chain"])
    assert "2 FIRs of missing person" in text and "0 to 3 cases" in text and "91%" in text
    assert "ZCQL" not in str(t) and "Vigil" not in str(t)
    assert any(e["officer"] == "review-test" for e in t["audit_events"])


def test_a_forecast_that_is_not_stored_says_so():
    t = _client().get("/api/derivation/board:Nowhere:THEFT", headers={"X-Role": "Inspector"}).json()
    assert t["unavailable"] is True and t["derivation_chain"] == []
