"""
Antar - outbound calls
======================
One place that knows every address this process may call, and counts every call it makes.

A police system should be able to answer "what leaves the building?" from a list, not from
a search of the code. Each outbound client asks `check(url, purpose)` first:

    ANTAR_EGRESS_ALLOW unset     the hosts the deployment configured (the model endpoint, the
                                 token service, the event calendar) and the fixed services a
                                 feature names (open-web search, speech, translation). Calls
                                 are counted.
    ANTAR_EGRESS_ALLOW=none      nothing leaves. Every outbound feature degrades the way it
                                 already does when its service is down: the model's wording
                                 falls back to the record-based answer, open-web search says
                                 it was not reached, speech and the calendar are unavailable.
    ANTAR_EGRESS_ALLOW=a,b       only those hosts (a name also covers its sub-domains).

What is logged for a call is the host, the purpose and whether it was allowed. Never the
body, the path or a query string: those are where case text and credentials would be.

Not covered: calls made inside the Zoho Catalyst SDK (data store, file store, push) when the
app runs on Catalyst with USE_LOCAL off. Those go to Catalyst's own API and are listed in
`KNOWN` so the page that shows this list is complete.
"""
from __future__ import annotations

import logging
import threading
from urllib.parse import urlparse

from app.core.settings import settings

log = logging.getLogger("antar.egress")


class EgressBlocked(RuntimeError):
    """An outbound call to a host that is not on the allow-list. Callers treat it like any
    other failure of that service; the message carries the purpose, not the address."""


# purpose -> what leaves, in words. The page that lists outbound calls reads this.
KNOWN = {
    "language_model": "The question, the fenced rows and the system prompt, with phone, Aadhaar, email and PAN redacted.",
    "model_token": "The model service's client credentials, to obtain an access token.",
    "vision_model": "An uploaded scan and the investigator's notes.",
    "open_web_search": "A named subject, as a web search query.",
    "registry_lookup": "An identifier on its own (an IFSC code, a domain name) to a public registry: no case text.",
    "speech": "The text of an answer, to be read aloud.",
    "translation": "A piece of text to translate between Kannada and English.",
    "event_calendar": "Nothing about a case: a request for a public holiday calendar.",
    "catalyst_sdk": "On Catalyst only: record queries and file storage through Zoho's SDK.",
}

_lock = threading.Lock()
_counts: dict[tuple[str, str, bool], int] = {}


def _host(url: str) -> str:
    return (urlparse(url if "://" in str(url) else f"//{url}").hostname or "").lower()


def _setting() -> str:
    return (getattr(settings, "ANTAR_EGRESS_ALLOW", "") or "").strip()


def _configured_hosts() -> set[str]:
    """Hosts this deployment was pointed at by its own settings."""
    urls = [getattr(settings, k, "") for k in (
        "QUICKML_LLM_ENDPOINT_URL", "QUICKML_CHAT_ENDPOINT_URL", "QUICKML_VISION_ENDPOINT_URL",
        "QUICKML_TOKEN_URL", "ANTAR_LLM_BASE_URL", "ANTAR_EVENT_FEED_URL")]
    return {h for h in (_host(u) for u in urls if u) if h}


# fixed services a feature names in code
_FEATURE_HOSTS = {"html.duckduckgo.com", "translate.google.com", "dhruva-api.bhashini.gov.in",
                  "meity-auth.ulcacontrib.org",
                  "www.bing.com",                  # open-web search fallback when DuckDuckGo throttles
                  "api.search.brave.com",          # open-web search, when a Brave key is configured
                  # OSINT registry lookups: the RBI IFSC list, domain registration (RDAP), certificate log
                  "ifsc.razorpay.com", "rdap.org", "crt.sh"}


def _registry_host(host: str) -> bool:
    """rdap.org hands a domain lookup on to the registry that holds it (rdap.verisign.com,
    rdap.nixiregistry.in ...). Those are allowed for a registry lookup only."""
    first = host.split(".", 1)[0]
    return first == "rdap" or first.startswith("rdap-") or ".rdap." in host


def mode() -> str:
    s = _setting().lower()
    return "none" if s in ("none", "off", "block", "deny") else ("list" if s else "default")


def allowed(url: str, purpose: str | None = None) -> bool:
    host = _host(url)
    if not host:
        return False
    m = mode()
    if m == "none":
        return False
    if m == "list":
        names = {x.strip().lower() for x in _setting().split(",") if x.strip()}
        return any(host == n or host.endswith("." + n) for n in names)
    return (host in _configured_hosts() or host in _FEATURE_HOSTS or any(host.endswith("." + h) for h in _FEATURE_HOSTS)
            or (purpose == "registry_lookup" and _registry_host(host)))


def check(url: str, purpose: str) -> None:
    """Call before any outbound request. Raises EgressBlocked when the host is not allowed."""
    host, ok = _host(url), allowed(url, purpose)
    with _lock:
        key = (host or "(no host)", purpose, ok)
        _counts[key] = _counts.get(key, 0) + 1
    if not ok:
        log.warning("egress_blocked host=%s purpose=%s mode=%s", host or "-", purpose, mode())
        raise EgressBlocked(f"Outbound calls for {purpose.replace('_', ' ')} are not allowed on this server.")
    log.info("egress host=%s purpose=%s", host, purpose)


def snapshot() -> dict:
    """What has left, and what was stopped, since the process started."""
    with _lock:
        rows = [{"host": h, "purpose": p, "allowed": ok, "calls": n} for (h, p, ok), n in sorted(_counts.items())]
    return {
        "mode": mode(),
        "rule": {"default": "configured and feature hosts only", "none": "nothing leaves", "list": "listed hosts only"}[mode()],
        "allowed_hosts": (sorted(_configured_hosts() | _FEATURE_HOSTS) if mode() == "default"
                          else sorted(x.strip().lower() for x in _setting().split(",") if x.strip()) if mode() == "list" else []),
        "calls": rows,
        "sent": sum(r["calls"] for r in rows if r["allowed"]),
        "blocked": sum(r["calls"] for r in rows if not r["allowed"]),
        "purposes": KNOWN,
    }


def _reset_for_tests() -> None:
    with _lock:
        _counts.clear()
