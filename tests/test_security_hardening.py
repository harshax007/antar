"""
HTTP / identity hardening (app/core/security.py, auth_middleware.py, rate_limiter.py).

The contract under test: nothing a caller receives contains an exception message, a
file path, an upstream URL or a credential; identity cannot be forged once signed mode
is on; one officer cannot read another's saved conversation.
"""

import time

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core import security
from app.core import auth_middleware as A
from app.core.settings import settings

BS = chr(92)
LEAKY = ('sqlite3.OperationalError: unable to open database file E:' + BS + 'Antar_FinalBuild_Dev'
         + BS + 'main.db at https://api.catalyst.zoho.in/quickml/v2/project/47053000000046003 '
         'Bearer 1000.0123456789abcdef0123.0123456789abcdef0123 client_secret=s3cr3t '
         'File "/app/app/core/db_path.py", line 42')


def _assert_clean(text: str, allow_type: bool = False):
    needles = ["Antar_FinalBuild_Dev", "main.db", "catalyst.zoho", "47053000000046003",
               "0123456789abcdef", "s3cr3t", "db_path.py", "Traceback"]
    if not allow_type:
        needles.append("OperationalError")      # public messages carry no exception detail at all
    for needle in needles:
        assert needle not in text, f"leaked {needle!r}: {text}"


@pytest.fixture()
def mini():
    """A fresh app with only the security layer — isolates handler behaviour."""
    app = FastAPI()

    @app.get("/api/boom")
    async def boom():
        raise RuntimeError(LEAKY)

    @app.get("/api/http500")
    async def http500():
        raise HTTPException(status_code=500, detail=LEAKY)

    @app.get("/api/http400")
    async def http400():
        raise HTTPException(status_code=400, detail="bad file at C:" + BS + "Users" + BS + "x" + BS + "a.csv")

    class Body(BaseModel):
        n: int

    @app.post("/api/echo")
    async def echo(b: Body):
        return {"n": b.n}

    @app.get("/api/ok")
    async def ok():
        return {"ok": True}

    security.install(app)
    return TestClient(app, raise_server_exceptions=False)


class TestErrorHygiene:
    def test_unhandled_exception_is_generic_with_reference(self, mini):
        r = mini.get("/api/boom")
        assert r.status_code == 500
        _assert_clean(r.text)
        assert r.json()["error_id"].startswith("ERR-") and r.json()["error_id"] in r.json()["detail"]

    def test_http_500_detail_replaced(self, mini):
        r = mini.get("/api/http500")
        assert r.status_code == 500
        _assert_clean(r.text)

    def test_4xx_detail_kept_but_scrubbed(self, mini):
        r = mini.get("/api/http400")
        assert r.status_code == 400 and "bad file at" in r.json()["detail"]
        assert "Users" not in r.text

    def test_validation_error_does_not_echo_input(self, mini):
        r = mini.post("/api/echo", json={"n": "Aadhaar 1234 5678 9012"})
        assert r.status_code == 422
        assert "1234" not in r.text and r.json()["detail"][0]["loc"] == ["body", "n"]

    def test_security_headers(self, mini):
        h = mini.get("/api/ok").headers
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert h["cache-control"] == "no-store"
        assert "default-src 'none'" in h["content-security-policy"]

    def test_body_ceiling(self, mini, monkeypatch):
        monkeypatch.setattr(settings, "ANTAR_MAX_BODY_MB", 1)
        r = mini.post("/api/echo", content=b"x" * (1024 * 1024 + 10),
                      headers={"content-type": "application/json"})
        assert r.status_code == 413

    def test_scrub_text_covers_the_usual_suspects(self):
        # scrub_text keeps the exception type (useful in internal records); it must still
        # remove every path, host, URL and credential.
        _assert_clean(security.scrub_text(LEAKY, limit=2000), allow_type=True)

    def test_public_error_never_contains_exception_text(self):
        e = security.public_error(RuntimeError(LEAKY), "llm")
        _assert_clean(e["message"])


class TestRealAppLeaks:
    @pytest.fixture(autouse=True)
    def _fresh_limiter(self):
        # earlier suites share the "testclient" bucket; start these with a full one
        from app.core.rate_limiter import _buckets
        _buckets.clear()
        yield
        _buckets.clear()

    def test_stream_error_event_is_generic(self, monkeypatch):
        from main import app
        from app.api import chat_stream

        async def explode(*a, **k):
            raise RuntimeError(LEAKY)

        monkeypatch.setattr(chat_stream, "_run_pipeline", explode)
        r = TestClient(app).post("/api/chat/stream", json={"text": "hello"})
        assert '"error"' in r.text and "ERR-" in r.text
        _assert_clean(r.text)

    def test_forensic_failure_is_generic(self, monkeypatch):
        from main import app
        from app.api import forensic

        async def explode(**k):
            raise RuntimeError(LEAKY)

        monkeypatch.setattr(forensic, "analyze_forensic_evidence", explode)
        r = TestClient(app, raise_server_exceptions=False).post("/api/forensic/analyze", json={})
        assert r.status_code == 500
        _assert_clean(r.text)

    def test_real_app_sends_security_headers(self):
        from main import app
        h = TestClient(app).get("/api/health").headers
        assert h["x-content-type-options"] == "nosniff" and h["cache-control"] == "no-store"


class TestSignedIdentity:
    SECRET = "t" * 48

    def test_roundtrip(self):
        tok = A.mint_token("U-7001", "Admin", secret=self.SECRET)
        ident = A.verify_token(tok, secret=self.SECRET)
        assert ident.officer == "U-7001" and ident.role == "Admin" and ident.verified

    def test_tampered_role_rejected(self):
        import base64, json
        tok = A.mint_token("U-1", "Constable", secret=self.SECRET)
        body, sig = tok.split(".")
        claims = json.loads(base64.urlsafe_b64decode(body + "=="))
        claims["role"] = "Superintendent"
        forged = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        assert A.verify_token(f"{forged}.{sig}", secret=self.SECRET) is None

    def test_wrong_secret_and_expiry_rejected(self):
        assert A.verify_token(A.mint_token("U-1", "Admin", secret=self.SECRET), secret="x" * 48) is None
        assert A.verify_token(A.mint_token("U-1", "Admin", ttl_s=-1, secret=self.SECRET), secret=self.SECRET) is None

    def test_gateway_requires_token_and_ignores_headers(self, monkeypatch):
        from main import app
        monkeypatch.setattr(settings, "ANTAR_AUTH_SECRET", self.SECRET)
        c = TestClient(app)
        # no token: refused before any router, even with a claimed Admin header
        assert c.get("/api/audit", headers={"X-Role": "Admin"}).status_code == 401
        # health stays public
        assert c.get("/api/health").status_code == 200
        # a Constable token cannot become Admin by adding X-Role
        tok = A.mint_token("OF-9", "Constable")
        r = c.get("/api/audit", headers={"Authorization": f"Bearer {tok}", "X-Role": "Admin"})
        assert r.status_code == 403
        tok = A.mint_token("OF-9", "Admin")
        assert c.get("/api/audit", headers={"Authorization": f"Bearer {tok}"}).status_code == 200

    def test_hitl_uses_token_identity(self, monkeypatch):
        from main import app
        monkeypatch.setattr(settings, "ANTAR_AUTH_SECRET", self.SECRET)
        c = TestClient(app)
        tok = A.mint_token("U-7001", "Admin")
        # an Approver header must not let an Admin token decide anything
        r = c.post("/api/hitl/NOPE/approve", json={},
                   headers={"Authorization": f"Bearer {tok}", "X-Role": "Approver", "X-Officer": "U-9001"})
        assert r.status_code in (403, 404)


class TestCronSecret:
    def test_default_secret_refused_in_production(self, monkeypatch):
        monkeypatch.setattr(settings, "ANTAR_ENV", "production")
        monkeypatch.setattr(settings, "CRON_SECRET_KEY", "change-me-in-production")
        with pytest.raises(HTTPException):
            A.require_cron_secret("change-me-in-production")

    def test_env_example_placeholder_refused_in_production(self, monkeypatch):
        placeholder = "generate_a_random_32_char_string_here"     # verbatim from .env.example
        monkeypatch.setattr(settings, "ANTAR_ENV", "production")
        monkeypatch.setattr(settings, "CRON_SECRET_KEY", placeholder)
        with pytest.raises(HTTPException):
            A.require_cron_secret(placeholder)

    def test_strong_secret_accepted_in_production(self, monkeypatch):
        monkeypatch.setattr(settings, "ANTAR_ENV", "production")
        monkeypatch.setattr(settings, "CRON_SECRET_KEY", "k" * 40)
        assert A.require_cron_secret("k" * 40) is True


class TestRateLimiter:
    def _req(self, host, xff=None):
        from starlette.requests import Request
        headers = [(b"x-forwarded-for", xff.encode())] if xff else []
        return Request({"type": "http", "client": (host, 1), "headers": headers})

    def test_spoofed_leftmost_xff_ignored(self, monkeypatch):
        from app.core.rate_limiter import client_ip
        monkeypatch.setattr(settings, "ANTAR_TRUSTED_PROXY_HOPS", 1)
        # attacker sends "1.2.3.4"; the gateway appends the real peer
        assert client_ip(self._req("10.0.0.1", "1.2.3.4, 198.51.100.7")) == "198.51.100.7"
        assert client_ip(self._req("10.0.0.1", "9.9.9.9, 198.51.100.7")) == "198.51.100.7"

    def test_no_proxy_trust_uses_socket(self, monkeypatch):
        from app.core.rate_limiter import client_ip
        monkeypatch.setattr(settings, "ANTAR_TRUSTED_PROXY_HOPS", 0)
        assert client_ip(self._req("203.0.113.9", "1.2.3.4")) == "203.0.113.9"

    def test_bucket_table_bounded(self, monkeypatch):
        from app.core import rate_limiter as RL
        monkeypatch.setattr(RL, "_MAX_KEYS", 100)
        RL._buckets.clear()
        for i in range(500):
            RL.check_rate_limit(f"k{i}")
        assert len(RL._buckets) == 100
        RL._buckets.clear()


class TestOwnership:
    THREAD = {"messages": [{"role": "user", "text": "secret case notes"}]}

    def test_other_officer_cannot_list_or_load(self):
        from main import app
        c = TestClient(app)
        a = {"X-Officer": "OF-A1", "X-Role": "Inspector"}
        b = {"X-Officer": "OF-B2", "X-Role": "Inspector"}
        adm = {"X-Officer": "OF-AD", "X-Role": "Admin"}
        assert c.post("/api/session/save", json={"session_id": "test-own-001", "payload": self.THREAD},
                      headers=a).status_code == 200
        assert c.get("/api/session/load/test-own-001", headers=a).status_code == 200
        assert c.get("/api/session/load/test-own-001", headers=b).status_code == 404
        assert "test-own-001" not in str(c.get("/api/session/saved", headers=b).json())
        assert c.post("/api/session/save", json={"session_id": "test-own-001", "payload": {}},
                      headers=b).status_code == 403
        assert c.get("/api/session/load/test-own-001", headers=adm).status_code == 200

    def test_officer_profile_self_or_admin(self):
        from main import app
        c = TestClient(app)
        assert c.get("/api/session/officer/OF-B2", headers={"X-Officer": "OF-A1"}).status_code == 403
        assert c.get("/api/session/officer/OF-A1", headers={"X-Officer": "OF-A1"}).status_code == 200


class TestIngestionGates:
    def test_upload_requires_admin(self):
        from main import app
        c = TestClient(app)
        files = {"file": ("x.csv", b"date,zone\n2024-01-01,A\n", "text/csv")}
        assert c.post("/api/upload", files=files, headers={"X-Role": "Inspector"}).status_code == 403

    def test_brain_seed_requires_admin(self):
        from main import app
        assert TestClient(app).post("/api/brain/seed", headers={"X-Role": "Inspector"}).status_code == 403
