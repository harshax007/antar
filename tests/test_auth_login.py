"""
Sign-in - the one route that issues a token, and the gateway that then demands it.

Before this, the login page accepted any password and the frontend sent `X-Role` as a
header, so the role gates were a UX contract. These tests assert the boundary: no token,
no case data; a wrong password and an unknown id are indistinguishable; five failures
lock the id; and the pages mounted outside /api are behind the same gate.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.core import accounts
from app.core.settings import settings
from main import app

client = TestClient(app)
SECRET = "test-signing-secret-that-is-long-enough-0123456789"
PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def _signed_mode_with_one_account(monkeypatch, tmp_path):
    f = tmp_path / "users.json"
    monkeypatch.setattr(settings, "ANTAR_AUTH_SECRET", SECRET)
    monkeypatch.setattr(settings, "ANTAR_USERS", "")
    monkeypatch.setattr(settings, "ANTAR_USERS_FILE", str(f))
    monkeypatch.delenv("ANTAR_USERS", raising=False)
    accounts._failures.clear()
    accounts.set_password("U-7001", "Admin", PASSWORD, "Operations Officer")
    # The login limiter is per address and every TestClient call shares one.
    from app.core import rate_limiter
    monkeypatch.setattr(rate_limiter, "check_rate_limit", lambda *a, **k: True)
    yield
    accounts._failures.clear()


def _login(user="U-7001", password=PASSWORD):
    return client.post("/api/auth/login", json={"user_id": user, "password": password})


def test_only_a_hash_is_stored():
    stored = json.loads(open(settings.ANTAR_USERS_FILE, encoding="utf-8").read())
    assert set(stored["U-7001"]) == {"role", "name", "salt", "hash"}
    assert PASSWORD not in json.dumps(stored)


def test_the_right_password_gets_a_token_that_opens_the_api():
    r = _login()
    assert r.status_code == 200
    body = r.json()
    assert body["officer"] == "U-7001" and body["role"] == "Admin"
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200 and me.json() == {"officer": "U-7001", "role": "Admin", "verified": True}


def test_no_token_no_case_data():
    for path in ("/api/dataset/records", "/api/profile/registry", "/api/session/officers",
                 "/api/obs/sessions", "/trace", "/trust", "/report/anything"):
        assert client.get(path).status_code == 401, f"{path} answered without a token"
    # ...and a role header no longer counts for anything
    assert client.get("/api/audit", headers={"X-Role": "Admin"}).status_code == 401


def test_health_and_login_stay_reachable_without_a_token():
    assert client.get("/api/health").status_code == 200
    assert _login().status_code == 200


def test_wrong_password_and_unknown_id_get_the_same_answer():
    wrong, unknown = _login(password="not the password"), _login(user="U-0000")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_five_failures_lock_the_id_even_for_the_right_password():
    for _ in range(accounts.MAX_FAILURES):
        assert _login(password="guess").status_code == 401
    locked = _login()
    assert locked.status_code == 429 and "Retry-After" in locked.headers
    assert accounts.verify("U-7001", PASSWORD) is None, "a locked id must not verify"


def test_a_success_clears_the_failure_count():
    for _ in range(accounts.MAX_FAILURES - 1):
        _login(password="guess")
    assert _login().status_code == 200
    assert _login(password="guess").status_code == 401
    assert _login().status_code == 200


def test_login_refuses_to_issue_tokens_without_a_signing_secret(monkeypatch):
    monkeypatch.setattr(settings, "ANTAR_AUTH_SECRET", "")
    assert _login().status_code == 503


def test_accounts_can_come_from_the_environment(monkeypatch):
    salt, digest = accounts.hash_password("another passphrase")
    monkeypatch.setattr(settings, "ANTAR_USERS", json.dumps(
        {"u-9001": {"role": "Approver", "name": "Supervising Officer", "salt": salt, "hash": digest}}))
    r = _login("U-9001", "another passphrase")
    assert r.status_code == 200 and r.json()["role"] == "Approver"
    assert _login().status_code == 401, "the file must not be read when ANTAR_USERS is set"


def test_a_weak_password_is_refused():
    with pytest.raises(ValueError):
        accounts.set_password("U-7002", "Inspector", "short")


def test_a_refusal_tells_the_browser_it_was_a_refusal(monkeypatch):
    """The gateway answers from outside the CORS layer. Without the origin header on its
    401 a browser reports a network failure, and an expired session looks like an outage."""
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", "http://localhost:3000")
    ok = client.get("/api/dataset/records", headers={"Origin": "http://localhost:3000"})
    assert ok.status_code == 401 and ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    other = client.get("/api/dataset/records", headers={"Origin": "https://elsewhere.example"})
    assert other.status_code == 401 and "access-control-allow-origin" not in other.headers
