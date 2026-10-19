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


def _build_dork_query(entity_name: str, sources: list[str] | None, depth: str) -> str:
    if not sources:
        return f"{entity_name} crime OR arrest OR suspect"
    valid = [s.strip().lower().replace(" ", "_").replace("-", "_") for s in sources if s]
    clauses = [_SOURCE_DORKS[s] for s in valid if s in _SOURCE_DORKS]
    if not clauses or len(clauses) >= 5:
        base = f'"{entity_name}" (crime OR arrest OR suspect OR police OR court OR fraud OR karnataka)'
    else:
        base = f'"{entity_name}" ({" OR ".join(clauses)})'
    if depth in ("deep", "full") and "karnataka" not in base.lower():
        base = f"{base} India"
    return base


async def search_osint(
    entity_name: str,
    sources: list[str] | None = None,
    depth: str = "standard",
) -> dict:
    """
    Searches DuckDuckGo HTML for the target entity/identifier.
    Extracts and sanitizes results as strictly 'unverified' open-web claims.
    Never touches FIR records or invents fallback data.
    """
    entity_name = normalize_untrusted(entity_name, max_len=120)
    if not entity_name or detect_injection(entity_name):
        return {
            "claims": [],
            "risk_flags": [],
            "summary": "No entity provided for OSINT.",
            "reached": False,
        }

    depth_key = (depth or "standard").strip().lower()
    max_results = _DEPTH_LIMITS.get(depth_key, 5)
    dork_query = _build_dork_query(entity_name, sources, depth_key)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    url = "https://html.duckduckgo.com/html/"
    params = {"q": dork_query}

    claims = []
    risk_flags = []
    matched_risk_terms: list[str] = []
    reached = True

    try:
        from app.core import egress
        egress.check(url, "open_web_search")  # blocked -> "could not be reached", nothing invented
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, data=params, headers=headers)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.find_all("div", class_="result__body")

            for res in results[:max_results]:
                title_elem = res.find("a", class_="result__url") or res.find("a", class_="result__a")
                snippet_elem = res.find("a", class_="result__snippet")
                if not (title_elem and snippet_elem):
                    continue

                href = title_elem.get("href", "")
                if href.startswith("//duckduckgo.com/l/?uddg="):
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    href = parsed.get("uddg", [href])[0]
                href = safe_url(href)

                claim_text = normalize_untrusted(snippet_elem.get_text(" ", strip=True), max_len=500)
                if detect_injection(claim_text):
                    claim_text = neutralize(claim_text)
                if not claim_text or not href:
                    continue

                heading_elem = res.find("a", class_="result__a") or title_elem
                title_text = normalize_untrusted(heading_elem.get_text(" ", strip=True), max_len=160)
                if detect_injection(title_text):
                    title_text = neutralize(title_text)

                domain = (urllib.parse.urlparse(href).hostname or "open-web").lower()
                category = _classify_domain(href)
                snippet_hash = hashlib.sha256(f"{href}|{claim_text}".encode("utf-8")).hexdigest()[:16]

                hit_words = [w for w in _RISK_WORDS if w in claim_text.lower()]
                for w in hit_words:
                    if w not in matched_risk_terms:
                        matched_risk_terms.append(w)

                claims.append({
                    "title": title_text or domain,
                    "claim": claim_text,
                    "source_url": href,
                    "domain": domain,
                    "category": category,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "confidence": 0.6,  # External implies lower baseline confidence (quarantined)
                    "status": "unverified",
                    "unverified": True,
                    "matched_keywords": hit_words,
                    "evidence_sha256": snippet_hash,
                })

                if any(word in claim_text.lower() for word in _RISK_WORDS):
                    if "High-risk keywords found in OSINT" not in risk_flags:
                        risk_flags.append("High-risk keywords found in OSINT")
        else:
            reached = False
    except Exception:
        reached = False

    if not claims:
        return {
            "claims": [],
            "risk_flags": [],
            "summary": (
                f"No open-web result was found for {entity_name}."
                if reached
                else "The open-web search could not be reached. Nothing was checked."
            ),
            "reached": reached,
            "query_executed": dork_query,
            "depth": depth_key,
            "active_sources": sources or list(_SOURCE_DORKS.keys()),
            "isolation_mode": "STANDALONE_NO_FIR_ACCESS",
        }

    return {
        "claims": claims,
        "risk_flags": risk_flags,
        "matched_risk_terms": matched_risk_terms,
        "summary": f"Found {len(claims)} unverified open-web claims for {entity_name}.",
        "reached": True,
        "query_executed": dork_query,
        "depth": depth_key,
        "active_sources": sources or list(_SOURCE_DORKS.keys()),
        "isolation_mode": "STANDALONE_NO_FIR_ACCESS",
    }

