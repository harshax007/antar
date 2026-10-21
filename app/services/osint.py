"""
Antar — Standalone Open-Source Intelligence (OSINT) Service
===========================================================
Standalone open-web intelligence fetching, dork scoping, and parsing.
Strictly isolated from internal FIR databases (`main.db`) and Antar core state.
Quarantines all external claims (`status="unverified"`, `unverified=True`).

Everything that comes back is text written by whoever owns the page.Each snippet is
reduced to visible text, instruction-shaped spans are removed, and a link is kept
only if it is a validated http(s) link. Nothing is invented: a search that fails or
finds nothing returns no claims and says so.
"""

import hashlib
import re
import urllib.parse
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.core.rag_security import normalize_untrusted, detect_injection, neutralize, safe_url

_RISK_WORDS = (
    "arrest", "wanted", "guilty", "convict", "charge",
    "fraud", "scam", "fir", "seized", "syndicate", "extortion", "absconding", "bail",
)

_SOURCE_DORKS: dict[str, str] = {
    "public_records": '(registry OR notification OR gazette OR "public record" OR rto OR mca)',
    "social_media": '(telegram OR instagram OR twitter OR facebook OR profile OR handle)',
    "court_records": '(court OR bail OR judgment OR tribunal OR indiankanoon OR ecourts)',
    "news_archives": '(news OR police OR arrested OR chargesheet OR investigation OR crime)',
    "marketplace": '(classifieds OR listing OR seller OR marketplace OR indiamart OR justdial)',
    "geo_tagged": '(karnataka OR bengaluru OR mysuru OR mangaluru OR hubballi OR belagavi)',
}

_DEPTH_LIMITS: dict[str, int] = {
    "surface": 3,
    "standard": 5,
    "deep": 8,
    "full": 12,
}


def _classify_domain(url: str) -> str:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if any(k in host for k in ("indiankanoon", "ecourts", "sci.gov", "karnatakajudiciary", "law", "court")):
        return "Court / Legal Archive"
    if any(k in host for k in ("gov.in", "nic.in", "parivahan", "mca.gov", "rbi.org")):
        return "Public / Govt Registry"
    if any(k in host for k in ("t.me", "telegram", "instagram", "twitter", "x.com", "facebook", "linkedin", "github", "reddit")):
        return "Social / Digital Surface"
    if any(k in host for k in ("indiamart", "justdial", "olx", "quikr", "tradeindia")):
        return "Commercial / Marketplace"
    if any(k in host for k in ("news", "times", "hindu", "deccan", "indianexpress", "ndtv", "prajavani", "udayavani", "daijiworld")):
        return "News / Media Archive"
    return "Open Web Surface"


_INDIA = ("karnataka", "bengaluru", "bangalore", "mysuru", "mysore", "mangaluru", "mangalore", "hubballi",
          "belagavi", "india", "kannada", "rupees", "rs.", "₹", "police station", "lakh", "crore")
_SOURCE_WEIGHT = {"Court / Legal Archive": 0.12, "Public / Govt Registry": 0.12, "News / Media Archive": 0.08,
                  "Social / Digital Surface": 0.04, "Commercial / Marketplace": 0.04, "Open Web Surface": 0.0}


def _build_dork_query(entity_name: str, sources: list[str] | None, depth: str, forms: list[str] | None = None) -> str:
    """The identifier itself, in quotes, in each way it is written. A source chosen by the
    officer narrows the search to that kind of page; nothing generic ("crime OR arrest") is
    added, because that is what used to bring back arrest-record sites about other people."""
    forms = [f for f in (forms or [entity_name]) if f][:5]
    exact = " OR ".join(f'"{f}"' for f in forms)
    base = f"({exact})" if len(forms) > 1 else exact
    valid = [s.strip().lower().replace(" ", "_").replace("-", "_") for s in (sources or []) if s]
    clauses = [_SOURCE_DORKS[s] for s in valid if s in _SOURCE_DORKS]
    if clauses and len(clauses) < 5:
        base = f"{base} ({' OR '.join(clauses)})"
    return base


def _score(match: dict, category: str, text: str, domain: str) -> float:
    """How much weight a page deserves, from what it shows: an exact identifier match counts
    most, a court, government or news page more than an unknown one, an Indian page more than
    a foreign one. Bounded 0.2 - 0.95; it is never certainty."""
    base = {"exact": 0.7, "name": 0.55, "partial": 0.3}.get(match.get("strength"), 0.3)
    base += _SOURCE_WEIGHT.get(category, 0.0)
    low = text.lower()
    if domain.endswith(".in") or any(w in low for w in _INDIA):
        base += 0.06
    elif match.get("strength") != "exact":
        base -= 0.1          # a foreign page that only shares a name is most likely someone else
    return round(max(0.2, min(0.95, base)), 2)


# The same search asked again within half an hour is answered from memory: an officer
# re-running a target (or a demo) does not hammer the engine into throttling us.
_CACHE: dict[str, tuple[float, str, list]] = {}
_CACHE_S = 1800


async def _bing(client, query: str) -> list:
    """Fallback engine: Bing's public RSS results, Indian market. Bing often ignores the
    quotes, which is safe here only because every result must then contain the identifier."""
    import html as _html
    import xml.etree.ElementTree as ET
    from app.core import egress
    url = "https://www.bing.com/search"
    egress.check(url, "open_web_search")
    resp = await client.get(url, params={"q": query, "format": "rss", "setmkt": "en-IN", "cc": "IN", "count": "20"},
                            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
    if resp.status_code != 200 or "xml" not in resp.headers.get("content-type", ""):
        raise httpx.HTTPError(f"fallback search answered {resp.status_code}")
    out = []
    for item in ET.fromstring(resp.content).iter("item"):
        get = lambda tag: _html.unescape((item.findtext(tag) or "").strip())
        out.append((get("link"), get("title"), get("description")))
    return out


async def _brave(client, query: str) -> list:
    """Brave Search API, Indian results. Used first when a key is configured."""
    from app.core import egress
    from app.core.settings import settings
    url = "https://api.search.brave.com/res/v1/web/search"
    egress.check(url, "open_web_search")
    resp = await client.get(url, params={"q": query, "country": "IN", "count": 20, "safesearch": "off"},
                            headers={"Accept": "application/json", "X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY})
    if resp.status_code != 200:
        raise httpx.HTTPError(f"Brave answered {resp.status_code}")
    res = (resp.json().get("web") or {}).get("results") or []
    return [(r.get("url", ""), r.get("title", ""), " ".join([r.get("description", "")] + (r.get("extra_snippets") or [])))
            for r in res]


async def _search(client, query: str) -> tuple[str, list]:
    """(engine, results): Brave when a key is set, else DuckDuckGo, and Bing when the one
    before it throttles or fails."""
    import time
    hit = _CACHE.get(query)
    if hit and time.time() - hit[0] < _CACHE_S:
        return hit[1], hit[2]
    from app.core.settings import settings
    engines = ([("Brave", _brave)] if settings.BRAVE_SEARCH_API_KEY else []) + [("DuckDuckGo", _ddg), ("Bing", _bing)]
    last: Exception | None = None
    for engine, fn in engines:
        try:
            rows = await fn(client, query)
            break
        except Exception as e:     # throttled, blocked by the egress list, or down: try the next
            last = e
    else:
        raise last or httpx.HTTPError("no search engine answered")
    if len(_CACHE) > 200:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[query] = (time.time(), engine, rows)
    return engine, rows


async def _ddg(client, query: str) -> list:
    """One search, Indian region, results as (href, title, snippet)."""
    from app.core import egress
    url = "https://html.duckduckgo.com/html/"
    egress.check(url, "open_web_search")  # blocked -> "could not be reached", nothing invented
    headers = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")}
    resp = await client.post(url, data={"q": query, "kl": "in-en"}, headers=headers)
    if resp.status_code != 200 or "anomaly" in resp.text[:4000].lower():
        raise httpx.HTTPError(f"search answered {resp.status_code}")   # 202 + a bot check = throttled
    soup = BeautifulSoup(resp.text, "html.parser")
    out = []
    for res in soup.find_all("div", class_="result__body"):
        a = res.find("a", class_="result__a") or res.find("a", class_="result__url")
        sn = res.find("a", class_="result__snippet")
        if not a:
            continue
        href = a.get("href", "")
        if href.startswith("//duckduckgo.com/l/?uddg="):
            href = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0]
        out.append((href, a.get_text(" ", strip=True), sn.get_text(" ", strip=True) if sn else ""))
    return out


async def search_osint(
    entity_name: str,
    sources: list[str] | None = None,
    depth: str = "standard",
    decoded: dict | None = None,
) -> dict:
    """
    Searches the open web for the identifier itself and keeps only pages that contain it.

    The identifier is searched in quotes, in each way it is written (98450 67890, 9845067890,
    +919845067890), with the region set to India. A result is kept only when its title,
    snippet or address actually contains the identifier (for a name: the full name); every
    other result is counted as checked and dropped. Each kept page says what it matched on and
    gets a weight from that, not a flat figure. Nothing is invented: a search that fails or
    finds nothing returns no claims and says how many pages were checked.
    """
    from app.services.osint_checks import match, variants
    from app.services.osint_recon import _classify_and_decode_target

    entity_name = normalize_untrusted(entity_name, max_len=120)
    if not entity_name or detect_injection(entity_name):
        return {"claims": [], "risk_flags": [], "summary": "No entity provided for OSINT.", "reached": False,
                "pages_checked": 0}

    decoded = decoded or _classify_and_decode_target(entity_name)
    forms = [f for f in variants(decoded) if f] or [entity_name]
    depth_key = (depth or "standard").strip().lower()
    max_results = _DEPTH_LIMITS.get(depth_key, 5)
    queries = [_build_dork_query(entity_name, sources, depth_key, forms)]
    if depth_key in ("deep", "full") and sources:
        queries.append(_build_dork_query(entity_name, None, depth_key, forms))   # also without the source filter

    claims: list[dict] = []
    risk_flags: list[str] = []
    matched_risk_terms: list[str] = []
    seen: set[str] = set()
    checked = 0
    reached = True
    engines: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for qy in queries:
                engine, rows = await _search(client, qy)
                engines.append(engine)
                for href, title, snippet in rows:
                    href = safe_url(href)
                    if not href or href in seen:
                        continue
                    seen.add(href)
                    checked += 1
                    claim_text = normalize_untrusted(snippet, max_len=500)
                    title_text = normalize_untrusted(title, max_len=160)
                    if detect_injection(claim_text):
                        claim_text = neutralize(claim_text)
                    if detect_injection(title_text):
                        title_text = neutralize(title_text)
                    m = match(decoded, f"{title_text} {claim_text} {urllib.parse.unquote(href)}")
                    if not m or len(claims) >= max_results:
                        continue
                    domain = (urllib.parse.urlparse(href).hostname or "open-web").lower()
                    category = _classify_domain(href)
                    hit_words = [w for w in _RISK_WORDS if re.search(rf"\b{w}(?:s|es|ed|ing)?\b", claim_text.lower())]
                    for w in hit_words:
                        if w not in matched_risk_terms:
                            matched_risk_terms.append(w)
                    if hit_words and "High-risk keywords found in OSINT" not in risk_flags:
                        risk_flags.append("High-risk keywords found in OSINT")
                    claims.append({
                        "title": title_text or domain,
                        "claim": claim_text or title_text,
                        "source_url": href,
                        "domain": domain,
                        "category": category,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "confidence": _score(m, category, f"{title_text} {claim_text}", domain),
                        "match_strength": m["strength"],
                        "matched_on": m["on"],
                        "status": "unverified",
                        "unverified": True,
                        "matched_keywords": hit_words,
                        "evidence_sha256": hashlib.sha256(f"{href}|{claim_text}".encode("utf-8")).hexdigest()[:16],
                    })
    except Exception:
        reached = bool(checked)

    claims.sort(key=lambda c: -c["confidence"])
    common = {
        "query_executed": " | ".join(queries),
        "engine": ", ".join(dict.fromkeys(engines)) or None,
        "searched_forms": forms,
        "depth": depth_key,
        "pages_checked": checked,
        "dropped_unrelated": max(0, checked - len(claims)),
        "active_sources": sources or list(_SOURCE_DORKS.keys()),
        "isolation_mode": "STANDALONE_NO_FIR_ACCESS",
    }
    if not claims:
        return {
            "claims": [], "risk_flags": [], "reached": reached,
            "summary": (f"No public page mentions {entity_name}: {checked} pages checked, none contains it."
                        if reached and checked else
                        f"No public page mentions {entity_name}." if reached else
                        "The open-web search could not be reached. Nothing was checked."),
            **common,
        }
    return {
        "claims": claims, "risk_flags": risk_flags, "matched_risk_terms": matched_risk_terms, "reached": True,
        "summary": f"{len(claims)} public {'page mentions' if len(claims) == 1 else 'pages mention'} {entity_name} "
                   f"(out of {checked} checked; the rest did not contain it).",
        **common,
    }
