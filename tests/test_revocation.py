"""Ending a session before its token expires (app/core/revocation.py), and the printed
report bound to the officers in the conversation."""
import time

import pytest

from app.core import auth_middleware as A, revocation as R

SECRET = "x" * 40


class _Req:
    def __init__(self, token):
        self.headers = {"authorization": f"Bearer {token}"}

        class S:
            pass
        self.state = S()


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "DB_PATH", str(tmp_path / "rev.db"))
    monkeypatch.setattr(R, "ensure_db_staged", lambda: None)
    monkeypatch.setattr(A.settings, "ANTAR_AUTH_SECRET", SECRET, raising=False)
    R._reset_for_tests()
    yield
    R._reset_for_tests()


def test_a_signed_out_token_is_refused_and_another_officers_is_not():
    mine, theirs = A.mint_token("OF-1", "Inspector"), A.mint_token("OF-2", "Inspector")
    assert A.resolve_identity(_Req(mine)).officer == "OF-1"
    R.revoke_token(mine, int(time.time()) + 3600)
    assert A.resolve_identity(_Req(mine)) is None
    assert A.resolve_identity(_Req(theirs)).officer == "OF-2"


def test_only_a_hash_of_the_token_is_kept(tmp_path):
    import sqlite3
    tok = A.mint_token("OF-1", "Inspector")
    R.revoke_token(tok, int(time.time()) + 3600)
    stored = sqlite3.connect(R.DB_PATH).execute("SELECT token_hash FROM revoked_tokens").fetchone()[0]
    assert tok not in stored and len(stored) == 64


def test_a_revocation_survives_a_restart():
    tok = A.mint_token("OF-1", "Inspector")
    R.revoke_token(tok, int(time.time()) + 3600)
    R._reset_for_tests()                       # the process forgets; the database does not
    assert A.resolve_identity(_Req(tok)) is None


def test_an_admin_ends_every_session_an_officer_holds_and_they_can_sign_in_again(monkeypatch):
    old = A.mint_token("OF-1", "Inspector")
    R.revoke_officer("OF-1", by="U-7001")
    assert A.resolve_identity(_Req(old)) is None
    later = int(time.time()) + 5
    monkeypatch.setattr(A.time, "time", lambda: later)
    monkeypatch.setattr(R.time, "time", lambda: later)
    assert A.resolve_identity(_Req(A.mint_token("OF-1", "Inspector"))).officer == "OF-1"


def test_an_entry_is_dropped_once_the_token_would_have_expired_anyway():
    tok = A.mint_token("OF-1", "Inspector")
    R.revoke_token(tok, int(time.time()) - 10)
    assert R.is_revoked(tok, "OF-1", 0) is False and R._tokens == {}


class TestReportBinding:
    def _req(self, officer, role):
        r = _Req(A.mint_token(officer, role))
        return r

    @pytest.fixture
    def turns(self, monkeypatch):
        from app.api import export_api as E
        monkeypatch.setattr(E.sessions, "all_turns", lambda sid: [
            {"role": "user", "text": "q"}, {"role": "assistant", "text": "a", "meta": {"officer": "OF-1"}}] if sid == "s1" else [])
        return E

    def test_the_officer_in_the_conversation_and_an_admin_may_read_it(self, turns):
        turns._may_read("s1", self._req("OF-1", "Inspector"))
        turns._may_read("s1", self._req("U-7001", "Admin"))

    def test_another_officer_may_not_and_cannot_tell_whether_it_exists(self, turns):
        from fastapi import HTTPException
        for sid in ("s1", "no-such-session"):
            with pytest.raises(HTTPException) as e:
                turns._may_read(sid, self._req("OF-2", "Inspector"))
            assert e.value.status_code == 403 and "another officer" in e.value.detail
