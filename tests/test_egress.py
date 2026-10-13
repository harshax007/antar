"""Outbound calls (app/core/egress.py): one allow-list, asked before anything leaves, and
with outbound switched off the product still works from the records."""
import asyncio

import pytest

from app.core import egress


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    egress._reset_for_tests()
    s = egress.settings
    for k in ("ANTAR_EGRESS_ALLOW", "QUICKML_LLM_ENDPOINT_URL", "QUICKML_CHAT_ENDPOINT_URL", "QUICKML_VISION_ENDPOINT_URL",
              "ANTAR_LLM_BASE_URL", "ANTAR_EVENT_FEED_URL"):
        monkeypatch.setattr(s, k, "", raising=False)
    monkeypatch.setattr(s, "QUICKML_TOKEN_URL", "https://accounts.zoho.in/oauth/v2/token", raising=False)
    yield
    egress._reset_for_tests()


def test_by_default_only_configured_and_named_hosts_are_reachable(monkeypatch):
    monkeypatch.setattr(egress.settings, "QUICKML_LLM_ENDPOINT_URL", "https://api.catalyst.zoho.in/quickml/v2/x/llm/chat", raising=False)
    assert egress.allowed("https://api.catalyst.zoho.in/quickml/v2/x/llm/chat")
    assert egress.allowed("https://accounts.zoho.in/oauth/v2/token")
    assert egress.allowed("https://html.duckduckgo.com/html/")
    for other in ("https://evil.example/collect", "http://169.254.169.254/latest/meta-data", "https://zoho.in.evil.example/x",
                  "https://duckduckgo.com.evil.example", "", "not a url"):
        assert not egress.allowed(other)


def test_none_means_nothing_leaves(monkeypatch):
    monkeypatch.setattr(egress.settings, "ANTAR_EGRESS_ALLOW", "none", raising=False)
    for url, purpose in (("https://accounts.zoho.in/oauth/v2/token", "model_token"),
                         ("https://html.duckduckgo.com/html/", "open_web_search"),
                         ("https://translate.google.com", "speech")):
        with pytest.raises(egress.EgressBlocked) as e:
            egress.check(url, purpose)
        assert "zoho" not in str(e.value) and "duckduckgo" not in str(e.value)     # the purpose, not the address
    snap = egress.snapshot()
    assert snap["mode"] == "none" and snap["sent"] == 0 and snap["blocked"] == 3 and snap["allowed_hosts"] == []


def test_a_list_allows_those_hosts_and_their_subdomains_only(monkeypatch):
    monkeypatch.setattr(egress.settings, "ANTAR_EGRESS_ALLOW", "localhost, models.ksp.example", raising=False)
    assert egress.allowed("http://localhost:11434/v1/chat/completions")
    assert egress.allowed("https://eu.models.ksp.example/v1")
    assert not egress.allowed("https://html.duckduckgo.com/html/")          # a named feature host is not on this list
    assert not egress.allowed("https://notmodels.ksp.example.evil.org/")


def test_what_is_counted_is_host_and_purpose_never_a_path_or_a_body():
    egress.check("https://html.duckduckgo.com/html/?q=Ramesh+Kumar+arrest", "open_web_search")
    snap = egress.snapshot()
    assert snap["calls"] == [{"host": "html.duckduckgo.com", "purpose": "open_web_search", "allowed": True, "calls": 1}]
    assert "Ramesh" not in str(snap) and "/html/" not in str(snap["calls"])


def test_with_outbound_off_the_model_is_not_called_and_no_token_is_fetched(monkeypatch):
    from app.services import quickml as Q
    s = Q.settings
    monkeypatch.setattr(s, "ANTAR_EGRESS_ALLOW", "none", raising=False)
    monkeypatch.setattr(s, "ANTAR_LLM_PROVIDER", "quickml", raising=False)
    monkeypatch.setattr(s, "QUICKML_LLM_ENDPOINT_URL", "https://api.catalyst.zoho.in/quickml/v2/x/llm/chat", raising=False)
    monkeypatch.setattr(Q, "_breaker_active", lambda: False)

    async def no_token():
        raise AssertionError("a token was requested with outbound calls switched off")
    monkeypatch.setattr(Q, "_auth_headers", no_token)
    monkeypatch.setattr(Q, "_get_client", lambda: (_ for _ in ()).throw(AssertionError("an HTTP client was opened")))
    with pytest.raises(egress.EgressBlocked):
        run(Q.quickml_generate(system="s", user="u", retries=0))


def test_with_outbound_off_the_open_web_search_says_it_was_not_reached(monkeypatch):
    from app.services import osint
    monkeypatch.setattr(egress.settings, "ANTAR_EGRESS_ALLOW", "none", raising=False)

    class Boom:
        def __init__(self, *a, **k):
            raise AssertionError("an HTTP client was opened")
    monkeypatch.setattr(osint.httpx, "AsyncClient", Boom)
    res = run(osint.search_osint("Ramesh Kumar"))
    assert res["claims"] == [] and res["reached"] is False


def test_an_answer_is_still_written_from_the_records_with_outbound_off(monkeypatch):
    """The compose step falls back to the record-based answer when the model cannot be reached."""
    from app.agents import query_agent as QA
    from app.services import quickml as Q
    monkeypatch.setattr(Q.settings, "ANTAR_EGRESS_ALLOW", "none", raising=False)
    monkeypatch.setattr(Q.settings, "ANTAR_LLM_PROVIDER", "quickml", raising=False)
    monkeypatch.setattr(Q.settings, "QUICKML_LLM_ENDPOINT_URL", "https://api.catalyst.zoho.in/x/llm/chat", raising=False)
    monkeypatch.setattr(Q, "_breaker_active", lambda: False)
    rows = [{"fir_number": "SYN-2026-908137", "crime_type": "THEFT", "zone": "Mysuru City", "district": "Mysuru City",
             "station_code": "MYS-01", "occurred_at": "2026-01-04", "status": "Convicted"}]
    text, used_model, _ = run(QA.compose_answer("thefts in Mysuru City", rows, "en", "T1", Q.quickml_generate))
    assert used_model is False and "SYN-2026-908137" in text
    assert egress.snapshot()["sent"] == 0


def test_every_outbound_client_in_the_backend_asks_first():
    """A new outbound call that forgets the allow-list fails here."""
    import pathlib
    import re
    call = re.compile(r"client\.(?:post|get)\(|_get_client\(\)\.(?:post|get)\(|httpx\.(?:get|post)\(|requests\.(?:get|post)\(|urlopen\(|gTTS\(")
    missing = []
    for f in pathlib.Path("app").rglob("*.py"):
        src = f.read_text(encoding="utf-8")
        if f.name == "egress.py" or not call.search(src):
            continue
        lines = src.splitlines()
        for i, line in enumerate(lines):
            if call.search(line) and not line.lstrip().startswith(("#", '"', "'")):
                # back to the start of the function this call is in
                j = i
                while j > 0 and not re.match(r"(?:async )?def ", lines[j]):
                    j -= 1
                if "egress.check(" not in "\n".join(lines[j:i + 1]):
                    missing.append(f"{f.as_posix()}:{i + 1}")
    assert missing == []
