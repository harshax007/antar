"""
Antar — OSINT Service (Phase 6)
====================================
Open-web intelligence fetching and parsing.
Quarantines all external claims (unverified=True).

Everything that comes back is text written by whoever owns the page. It is shown to an
officer and can be carried into a prompt, so each snippet is reduced to visible text,
instruction-shaped spans are removed, and a link is kept only if it is an http(s) link.
Nothing is invented: a search that fails or finds nothing returns no claims and says so.
"""

import urllib.parse
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.core.rag_security import normalize_untrusted, detect_injection, neutralize, safe_url

_RISK_WORDS = ("arrest", "wanted", "guilty", "convict", "charge")


async def search_osint(entity_name: str) -> dict:
    """
    Searches DuckDuckGo HTML for the entity name.
    Extracts the first 3 results as 'unverified' claims.
    """
    entity_name = normalize_untrusted(entity_name, max_len=120)
    if not entity_name or detect_injection(entity_name):
        return {"claims": [], "risk_flags": [], "summary": "No entity provided for OSINT."}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    url = "https://html.duckduckgo.com/html/"
    params = {"q": f"{entity_name} crime OR arrest OR suspect"}

    claims = []
    risk_flags = []
    reached = True

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, data=params, headers=headers)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.find_all("div", class_="result__body")

            for res in results[:3]:
                title_elem = res.find("a", class_="result__url")
                snippet_elem = res.find("a", class_="result__snippet")
                if not (title_elem and snippet_elem):
                    continue

                href = title_elem.get("href", "")
                # DuckDuckGo sometimes prepends an internal redirect
                if href.startswith("//duckduckgo.com/l/?uddg="):
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    href = parsed.get("uddg", [href])[0]
                href = safe_url(href)

                claim_text = normalize_untrusted(snippet_elem.get_text(" ", strip=True), max_len=500)
                if detect_injection(claim_text):
                    claim_text = neutralize(claim_text)
                if not claim_text or not href:
                    continue

                claims.append({
                    "claim": claim_text,
                    "source_url": href,
                    "fetched_at": datetime.now().isoformat(),
                    "confidence": 0.6,  # External implies lower baseline confidence
                    "status": "unverified",
                })

                # Simple heuristic risk flag
                if any(word in claim_text.lower() for word in _RISK_WORDS):
                    if "High-risk keywords found in OSINT" not in risk_flags:
                        risk_flags.append("High-risk keywords found in OSINT")
        else:
            reached = False
    except Exception:
        reached = False

    # No result is reported as no result. This used to return an invented line - "<name>
    # mentioned in local news regarding petty theft", with an example.com link - whenever
    # the search failed or found nothing: a made-up allegation about a named person,
    # labelled as an open-web claim.
    if not claims:
        return {
            "claims": [], "risk_flags": [],
            "summary": (f"No open-web result was found for {entity_name}." if reached
                        else "The open-web search could not be reached. Nothing was checked."),
            "reached": reached,
        }

    return {
        "claims": claims,
        "risk_flags": risk_flags,
        "summary": f"Found {len(claims)} unverified open-web claims for {entity_name}.",
        "reached": True,
    }
