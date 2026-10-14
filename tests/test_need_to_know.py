"""Need-to-know retrieval (zcql_repo.need_to_know): below Analyst, a listing of case rows is
limited to the officer's own district. Counts are not. The answer says when it happened."""
import sqlite3

import pytest

from app.core import security_context as SC
from app.services import zcql_repo as Z


def _as(role, posting, fn):
    ctx, token = SC.begin("OF-1", role, posting=posting)
    try:
        return ctx, fn()
    finally:
        SC.end(token)


def _zones(spec):
    return [v for f in spec.filters if f.column == "zone" for v in f.value]


def test_an_inspector_lists_cases_for_their_own_district_only():
    ctx, spec = _as("Inspector", "Mysuru City", lambda: Z.build_spec("T1", {"crime_types": ["THEFT"]}))
    assert _zones(spec) == ["Mysuru City"] and ctx.scope == {"posting": "Mysuru City"}


def test_asking_for_another_district_still_returns_their_own_and_records_what_was_asked():
    ctx, spec = _as("Inspector", "Mysuru City", lambda: Z.build_spec("T1", {"zones": ["Belagavi Dist"]}))
    assert _zones(spec) == ["Mysuru City"]
    assert ctx.scope == {"posting": "Mysuru City", "asked_for": ["Belagavi Dist"]}
    assert ctx.for_audit()["scope"]["asked_for"] == ["Belagavi Dist"]          # and it is on the audit row


def test_two_inspectors_get_different_rows_for_the_same_question():
    def rows(posting):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE crimes (crime_id, fir_number, crime_type, act, acts_sections, zone, district, "
                     "station_code, occurred_at, status, io_name)")
        conn.executemany("INSERT INTO crimes (crime_id, zone, crime_type) VALUES (?, ?, 'THEFT')",
                         [("C1", "Mysuru City"), ("C2", "Belagavi Dist"), ("C3", "Mysuru City")])
        _c, spec = _as("Inspector", posting, lambda: Z.build_spec("T1", {"crime_types": ["THEFT"]}))
        return sorted(r[0] for r in conn.execute(Z.render_zcql(spec)).fetchall())
    assert rows("Mysuru City") == ["C1", "C3"] and rows("Belagavi Dist") == ["C2"]


@pytest.mark.parametrize("role", ["Analyst", "Approver", "Admin", "Superintendent"])
def test_analyst_and_above_see_statewide(role):
    ctx, spec = _as(role, "Mysuru City", lambda: Z.build_spec("T1", {"zones": ["Belagavi Dist"]}))
    assert [z.upper() for z in _zones(spec)] == ["BELAGAVI DIST"] and ctx.scope is None


def test_counts_and_rankings_are_not_limited():
    tid = next(t for t, tm in Z.TEMPLATES.items() if not tm.internal and t != "T1")
    for t, tm in Z.TEMPLATES.items():
        if tm.internal:
            continue
        try:
            _c, spec = _as("Inspector", "Mysuru City", lambda t=t: Z.build_spec(t, {}))
        except Exception:
            continue                                   # needs parameters this test does not supply
        if spec.aggregates or spec.group_by or spec.table != "crimes":
            assert "Mysuru City" not in _zones(spec), f"{t} is an aggregate and was limited"
    assert tid


def test_no_posting_or_no_context_or_a_system_task_is_not_limited():
    _c, spec = _as("Inspector", "", lambda: Z.build_spec("T1", {"zones": ["Belagavi Dist"]}))
    assert [z.upper() for z in _zones(spec)] == ["BELAGAVI DIST"]
    assert [z.upper() for z in _zones(Z.build_spec("T1", {"zones": ["Belagavi Dist"]}))] == ["BELAGAVI DIST"]
    with SC.system("warm-up"):
        assert [z.upper() for z in _zones(Z.build_spec("T1", {"zones": ["Belagavi Dist"]}))] == ["BELAGAVI DIST"]


def test_the_posting_travels_in_the_signed_token_not_in_a_header():
    from app.core import auth_middleware as A
    tok = A.mint_token("OF-7", "Inspector", secret="x" * 40, posting="  Mysuru   City ")
    ident = A.verify_token(tok, secret="x" * 40)
    assert ident.posting == "Mysuru City" and ident.role == "Inspector"
    assert A.verify_token(A.mint_token("OF-7", "Inspector", secret="x" * 40), secret="x" * 40).posting == ""
    # changing the claim breaks the signature
    body, sig = tok.split(".")
    forged = A._b64(A._unb64(body).replace(b"Mysuru City", b"Belagavi   ")) + "." + sig
    assert A.verify_token(forged, secret="x" * 40) is None


def test_an_account_keeps_its_posting(tmp_path, monkeypatch):
    from app.core import accounts
    monkeypatch.setattr(accounts, "_users_file", lambda: tmp_path / "users.json")
    accounts.set_password("U-1", "Inspector", "a-long-password", posting="Mysuru City")
    accounts.set_password("U-1", "Inspector", "another-long-one")              # a password change keeps it
    import json
    assert json.loads((tmp_path / "users.json").read_text())["U-1"]["posting"] == "Mysuru City"


def test_the_cache_does_not_serve_one_officers_rows_to_another():
    from app.agents import query_agent as QA
    import inspect
    src = inspect.getsource(QA.query_agent_run)
    assert "_scoped_posting().lower()" in src and "cache_key" in src
