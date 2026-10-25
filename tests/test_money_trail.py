"""
Money trail (app/services/money_trail.py, /api/funds/*): accounts, transactions, the rules
that flag an account, and the FIRs behind each UPI ID.
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.services import money_trail as m

pytestmark = pytest.mark.skipif(not m.available(), reason="money trail not built (scripts/seed_money_trail.py)")


def test_nothing_is_dated_after_today():
    snap = m._snapshot()
    assert snap["txns"] and max(t["ts"][:10] for t in snap["txns"]) <= date.today().isoformat()


def test_money_only_moves_forward_in_time_along_a_hop():
    # a layering hop never leaves an account before the payment that fed it arrived
    snap = m._snapshot()
    for t in snap["txns"]:
        if t["purpose"] == "layering":
            fed = [p for p in snap["to"][t["from_account"]] if p["fir_id"] == t["fir_id"] and p["purpose"] == "payment"]
            assert any(p["ts"] <= t["ts"] for p in fed)


def test_the_overview_ranks_flagged_accounts_first():
    o = m.overview(20)
    assert o["transactions"] > 0 and o["flagged"] > 0
    flags = [len(r["flags"]) for r in o["top"]]
    assert flags == sorted(flags, reverse=True)


def test_each_flag_says_what_tripped_it():
    top = m.overview(5)["top"][0]["account_id"]
    a = m.account(top)
    assert a["flags"] and all(f["title"] and any(ch.isdigit() for ch in f["detail"]) for f in a["flags"])
    assert a["total_in"] >= a["total_out"] * 0 and a["senders"] >= 1


def test_a_trail_holds_the_root_and_only_edges_between_its_nodes():
    root = m.overview(5)["top"][0]["account_id"]
    t = m.trail(root, depth=2)
    ids = {n["id"] for n in t["nodes"]}
    assert root in ids and t["edges"]
    assert all(e["from"] in ids and e["to"] in ids and e["amount"] > 0 for e in t["edges"])


def test_search_finds_an_account_by_the_fir_it_is_named_in():
    snap = m._snapshot()
    upi, firs = next((u, fs) for u, fs in snap["firs"].items() if u in snap["accounts"])
    assert upi in [r["account_id"] for r in m.search(firs[0]["fir_id"])]


def test_unknown_account_is_none():
    assert m.account("no-such-account") is None and m.trail("no-such-account") is None


class TestEndpoint:
    def test_inspector_reads_it_and_a_constable_does_not(self):
        from main import app
        c = TestClient(app)
        assert c.get("/api/funds/overview", headers={"X-Role": "Inspector"}).status_code == 200
        assert c.get("/api/funds/overview", headers={"X-Role": "Constable"}).status_code == 403

    def test_account_ids_with_an_at_sign_resolve(self):
        from main import app
        upi = next(a for a, v in m._snapshot()["accounts"].items() if v["kind"] == "upi")
        r = TestClient(app).get(f"/api/funds/account/{upi}", headers={"X-Role": "Inspector"})
        assert r.status_code == 200 and r.json()["account"]["account_id"] == upi
        assert TestClient(app).get("/api/funds/trail?account=nope", headers={"X-Role": "Inspector"}).status_code == 404
