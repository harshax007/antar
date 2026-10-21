"""
Antar - OSINT checks an officer can act on
==========================================
Three things the open-web search alone could not give an investigator:

  1. The exact written forms of an identifier (`variants`), so a search looks for the
     identifier itself and a page counts only if it actually contains it.
  2. Live registry checks (`live_checks`) that answer from an authoritative public source,
     with no key and nothing about the case sent out - only the identifier:
        IFSC         -> bank, branch, address, UPI/IMPS support   (ifsc.razorpay.com)
        domain / URL -> registrar, registration date, age          (RDAP, the registries' own WHOIS)
                     -> TLS certificates ever issued               (crt.sh certificate transparency)
        IMEI         -> whether the number is well-formed (Luhn)   (computed here, nothing sent)
     Each one reports "found", "not found" or "could not be reached". Nothing is filled in.
  3. The official checks (`official_checks`) for the identifier type: the government portal,
     what it tells the officer, and how to use it. These are opened by the officer, in their own
     session; Antar does not log in to them or scrape them.

And `build_brief` turns all of it into the officer's summary: what this is, what the open web
shows, what was found live, and what to do next, in that order.

Outputs are leads, never findings: nothing here is written to the FIR record.
"""

from __future__ import annotations

import asyncio
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import httpx

_UA = {"User-Agent": "Antar-KSP-OSINT/1.0 (law-enforcement decision support)"}


# ── 1. exact written forms ─────────────────────────────────────────────────────

def variants(decoded: dict[str, Any]) -> list[str]:
    """The ways this identifier is written on a web page, most specific first."""
    t = decoded.get("target_type")
    if t == "phone":
        n = decoded.get("national_number") or ""
        if len(n) != 10:
            return [decoded.get("normalized") or ""]
        return [n, f"{n[:5]} {n[5:]}", f"+91{n}", f"+91 {n[:5]} {n[5:]}", f"{n[:3]}-{n[3:6]}-{n[6:]}"]
    if t == "vehicle_plate":
        norm = decoded.get("normalized") or ""
        parts = [p for p in norm.split("-") if p]
        if not parts:
            return [norm]
        return list(dict.fromkeys(["".join(parts), "-".join(parts), " ".join(parts)]))
    if t == "bank_account":
        return [decoded.get("account_number") or ""]
    if t in ("upi_vpa", "email", "domain", "ifsc", "imei"):
        return [decoded.get("normalized") or ""]
    if t == "handle":
        h = decoded.get("clean_handle") or ""
        return [f"@{h}", h] if h else []
    return [decoded.get("normalized") or ""]


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _alnum(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", s or "").upper()


def match(decoded: dict[str, Any], text: str) -> dict[str, Any] | None:
    """Does `text` (a page's title, snippet and address) actually contain the identifier?
    Returns how it matched, or None. A page that does not is not about the subject."""
    t = decoded.get("target_type")
    low = (text or "").lower()
    if t == "phone":
        n = decoded.get("national_number") or ""
        if len(n) == 10 and n in _digits(text):
            return {"strength": "exact", "on": f"the number {n[:5]} {n[5:]}"}
        return None
    if t == "vehicle_plate":
        a = _alnum("".join(decoded.get("normalized", "").split("-")))
        if a and a in _alnum(text):
            return {"strength": "exact", "on": f"the registration {decoded.get('normalized')}"}
        return None
    if t in ("upi_vpa", "email", "domain", "ifsc", "imei"):
        v = (decoded.get("normalized") or "").lower()
        if t == "imei":
            return {"strength": "exact", "on": "the IMEI"} if v and v in _digits(text) else None
        if t == "ifsc":
            return {"strength": "exact", "on": "the IFSC"} if v.upper() in (text or "").upper() else None
        return {"strength": "exact", "on": v} if v and v in low else None
    if t == "bank_account":
        acc = decoded.get("account_number") or ""
        return {"strength": "exact", "on": "the account number"} if acc and acc in _digits(text) else None
    if t == "handle":
        h = (decoded.get("clean_handle") or "").lower()
        if h and re.search(rf"(?<![a-z0-9_.]){re.escape(h)}(?![a-z0-9_])", low):
            return {"strength": "exact", "on": f"@{h}"}
        return None
    # a person, a company or a place: the full name as written, else every part of it
    name = re.sub(r"\s+", " ", (decoded.get("normalized") or "")).strip().lower()
    if not name:
        return None
    flat = re.sub(r"\s+", " ", low)
    if name in flat:
        return {"strength": "name", "on": f"the name \"{decoded.get('normalized')}\""}
    parts = [p for p in name.split(" ") if len(p) > 1]
    if len(parts) >= 2 and all(re.search(rf"\b{re.escape(p)}\b", flat) for p in parts):
        return {"strength": "partial", "on": "every part of the name, not together"}
    return None


# ── 2. live registry checks ────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get(client: httpx.AsyncClient, url: str, purpose: str = "registry_lookup") -> httpx.Response:
    from app.core import egress
    egress.check(url, purpose)
    r = await client.get(url, headers=_UA)
    # RDAP answers with a redirect to the registry that holds the domain. Followed once,
    # and only to a host the egress list accepts for registry lookups.
    if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
        nxt = urllib.parse.urljoin(url, r.headers["location"])
        if not nxt.startswith("https://"):
            raise httpx.HTTPError("redirect to a non-https address")
        egress.check(nxt, purpose)
        r = await client.get(nxt, headers=_UA)
    return r


async def _ifsc(client, code: str) -> dict:
    src = f"https://ifsc.razorpay.com/{code}"
    base = {"name": "Bank branch (IFSC registry)", "source": "ifsc.razorpay.com (RBI IFSC list)", "source_url": src, "checked_at": _now()}
    try:
        r = await _get(client, src)
    except Exception:
        return {**base, "status": "unreached", "facts": [], "say": "The IFSC registry could not be reached. Nothing was checked."}
    if r.status_code == 404:
        return {**base, "status": "none", "facts": [], "flag": "IFSC not in the RBI list",
                "say": f"{code} is not a valid IFSC in the RBI list. Check the code was copied correctly; a made-up IFSC on a payment request is a fraud sign."}
    if r.status_code != 200:
        return {**base, "status": "unreached", "facts": [], "say": "The IFSC registry did not answer. Nothing was checked."}
    d = r.json()
    modes = [m for m in ("UPI", "IMPS", "NEFT", "RTGS") if d.get(m)]
    facts = [
        {"label": "Bank", "value": d.get("BANK") or "-"},
        {"label": "Branch", "value": d.get("BRANCH") or "-"},
        {"label": "Address", "value": d.get("ADDRESS") or "-"},
        {"label": "District / State", "value": ", ".join(x for x in (d.get("DISTRICT"), d.get("STATE")) if x) or "-"},
        {"label": "Branch phone", "value": d.get("CONTACT") or "not listed"},
        {"label": "Payments it takes", "value": ", ".join(modes) or "not listed"},
    ]
    return {**base, "status": "found", "facts": facts,
            "bank": f"{d.get('BANK')}, {str(d.get('BRANCH', '')).title()} branch, {str(d.get('CITY') or d.get('DISTRICT') or '').title()}",
            "say": f"{d.get('BANK')}, {d.get('BRANCH')} branch ({d.get('CITY') or d.get('DISTRICT')}, {d.get('STATE')}). "
                   "This is the branch to send the account-holder notice to.",
            "do": f"Address the bank notice to the nodal officer of {d.get('BANK')}, {str(d.get('BRANCH', '')).title()} branch"
                  + (f" (branch phone {d['CONTACT']})." if d.get("CONTACT") else ".")}


async def _rdap(client, domain: str) -> dict:
    src = f"https://rdap.org/domain/{domain}"
    base = {"name": "Website registration (WHOIS)", "source": "RDAP, the domain registry's own record", "source_url": src, "checked_at": _now()}
    try:
        r = await _get(client, src)
    except Exception:
        return {**base, "status": "unreached", "facts": [], "say": "The domain registry could not be reached. Nothing was checked."}
    if r.status_code == 404:
        return {**base, "status": "none", "facts": [], "say": f"{domain} is not registered (or the registry does not publish it)."}
    if r.status_code != 200:
        return {**base, "status": "unreached", "facts": [], "say": "The domain registry did not answer. Nothing was checked."}
    d = r.json()
    ev = {e.get("eventAction"): e.get("eventDate") for e in d.get("events", []) if isinstance(e, dict)}
    created = ev.get("registration")
    age_days = None
    if created:
        try:
            age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))).days
        except ValueError:
            age_days = None
    registrar = "-"
    for ent in d.get("entities", []) or []:
        if "registrar" in (ent.get("roles") or []):
            vc = ent.get("vcardArray") or []
            for item in (vc[1] if len(vc) > 1 else []):
                if item and item[0] == "fn":
                    registrar = str(item[3]).rstrip(". ")
    ns = [n.get("ldhName", "").lower() for n in d.get("nameservers", []) or [] if n.get("ldhName")]
    facts = [
        {"label": "Registered on", "value": (created or "-")[:10]},
        {"label": "Age", "value": f"{age_days} days" if age_days is not None else "-"},
        {"label": "Expires", "value": (ev.get("expiration") or "-")[:10]},
        {"label": "Registrar", "value": registrar},
        {"label": "Name servers", "value": ", ".join(ns[:3]) or "-"},
    ]
    young = age_days is not None and age_days < 180
    out = {**base, "status": "found", "facts": facts,
           "say": (f"Registered {age_days} days ago through {registrar}. " if age_days is not None else f"Registered through {registrar}. ")
                  + ("A website this new is a common sign of a fraud site." if young else "Not a newly registered site.")
                  + " The registrar holds the registrant's details; ask it under Section 94 BNSS."}
    if young:
        out["flag"] = f"Website only {age_days} days old"
    out["do"] = f"Ask the registrar ({registrar}) for the registrant's name, email, phone and payment details."
    return out


async def _crtsh(client, domain: str) -> dict:
    src = f"https://crt.sh/?q={urllib.parse.quote(domain)}&output=json"
    base = {"name": "Security certificates issued", "source": "crt.sh certificate transparency log", "source_url": f"https://crt.sh/?q={urllib.parse.quote(domain)}", "checked_at": _now()}
    try:
        r = await _get(client, src)
    except Exception:
        return {**base, "status": "unreached", "facts": [], "say": "The certificate log could not be reached (it is often slow). Nothing was checked."}
    if r.status_code != 200:
        return {**base, "status": "unreached", "facts": [], "say": "The certificate log did not answer (it is often slow). Nothing was checked."}
    try:
        rows = r.json()
    except ValueError:
        rows = []
    if not rows:
        return {**base, "status": "none", "facts": [], "say": "No security certificate has ever been issued for this name."}
    names = set()
    first = None
    for row in rows:
        for n in str(row.get("name_value", "")).split("\n"):
            if n.strip():
                names.add(n.strip().lower())
        nb = row.get("not_before")
        if nb and (first is None or nb < first):
            first = nb
    facts = [
        {"label": "Certificates", "value": str(len(rows))},
        {"label": "First certificate", "value": (first or "-")[:10]},
        {"label": "Names covered", "value": ", ".join(sorted(names)[:6]) + (f" and {len(names) - 6} more" if len(names) > 6 else "")},
    ]
    return {**base, "status": "found", "facts": facts,
            "say": f"{len(rows)} certificates, the first on {(first or '-')[:10]}. Other names on them can be sister sites run by the same people."}


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _imei(decoded: dict) -> dict:
    n = decoded.get("normalized") or ""
    ok = luhn_ok(n)
    base = {"name": "IMEI check digit", "source": "computed here (GSMA Luhn check); nothing was sent", "source_url": None, "checked_at": _now()}
    facts = [
        {"label": "IMEI", "value": n},
        {"label": "Type allocation code (TAC)", "value": n[:8] + "  (identifies the make and model)"},
        {"label": "Serial number", "value": n[8:14]},
        {"label": "Check digit", "value": f"{n[14]} - {'correct' if ok else 'wrong'}"},
    ]
    if ok:
        return {**base, "status": "found", "facts": facts,
                "say": "A well-formed IMEI. Check it on Sanchar Saathi (CEIR) to see if it is blocked as lost or stolen, and KYM for its make and model."}
    return {**base, "status": "none", "facts": facts, "flag": "IMEI check digit is wrong",
            "say": "The check digit is wrong: either the IMEI was copied incorrectly or it is a fake or cloned IMEI. Recheck it from the handset (*#06#)."}


async def live_checks(decoded: dict[str, Any]) -> list[dict]:
    t = decoded.get("target_type")
    if t == "imei":
        return [_imei(decoded)]
    jobs = []
    async with httpx.AsyncClient(timeout=9.0, follow_redirects=False) as client:
        if t in ("ifsc", "bank_account") and decoded.get("ifsc"):
            jobs.append(_ifsc(client, decoded["ifsc"]))
        if t == "domain":
            jobs.append(_rdap(client, decoded["domain"]))
            jobs.append(_crtsh(client, decoded["domain"]))
        if t == "email" and decoded.get("domain") and decoded["domain"] not in _FREE_MAIL:
            jobs.append(_rdap(client, decoded["domain"]))
        if not jobs:
            return []
        return list(await asyncio.gather(*jobs))


_FREE_MAIL = {"gmail.com", "yahoo.com", "yahoo.co.in", "outlook.com", "hotmail.com", "rediffmail.com",
              "icloud.com", "proton.me", "protonmail.com", "live.com", "aol.com", "zoho.com"}


# ── 3. official checks the officer opens ───────────────────────────────────────

_I4C = {"name": "I4C Suspect Registry", "url": "https://cybercrime.gov.in/",
        "step": "Check it on the I4C Suspect Registry for cyber-fraud complaints anywhere in India.",
        "what": "Whether this has been reported in a cyber-fraud complaint anywhere in India (the national registry I4C shares with banks).",
        "how": "Open the portal, choose 'Report & Check Suspect', then 'Check Suspect', pick the type and paste the value. A match is a complaint, not proof; no match does not clear it."}
_NCRP = {"name": "NCRP / 1930 helpline", "url": "https://cybercrime.gov.in/",
         "step": "If a victim has just paid, report on 1930 / NCRP now so the bank can hold the money.",
         "what": "Where money lost to fraud is reported so the bank can put the proceeds on hold.",
         "how": "If a victim has just paid, call 1930 or file on the portal first; the hold works only in the first hours."}


def official_checks(decoded: dict[str, Any]) -> list[dict]:
    t = decoded.get("target_type")
    n = decoded.get("normalized") or ""
    q = urllib.parse.quote(n)
    out: list[dict] = []
    if t == "phone":
        out += [
            {**_I4C, "value": decoded.get("national_number")},
            {"name": "Sanchar Saathi - Chakshu", "url": "https://sancharsaathi.gov.in/",
             "step": "If it was used for fraud calls or messages, report it on Sanchar Saathi (Chakshu) for disconnection.",
             "what": "Report a number used for fraud calls or messages so DoT can verify and disconnect it.",
             "how": "Open 'Chakshu', report the number with the call or message details."},
            {"name": "WhatsApp profile (by hand)", "url": f"https://wa.me/91{decoded.get('national_number', '')}",
             "step": "Open its WhatsApp profile on an official device and note the name and photo shown.",
             "what": "Whether the number has a WhatsApp account, and its public name and photo.",
             "how": "Open on an official device; note what is shown and when. Do not message the number."},
        ]
    elif t == "upi_vpa":
        out += [{**_I4C, "value": n}, _NCRP]
    elif t in ("bank_account", "ifsc"):
        out += [{**_I4C, "value": decoded.get("account_number") or n}, _NCRP]
    elif t == "imei":
        out += [
            {"name": "Sanchar Saathi - CEIR", "url": "https://www.ceir.gov.in/",
             "step": "Check the IMEI on CEIR: if it is blocked as stolen, the blocking station has the owner's complaint.",
             "what": "Whether this IMEI is blocked as lost or stolen, and the police station that blocked it.",
             "how": "Open 'Request status' or ask the CEIR nodal officer of the district; a stolen phone seen on the network is traceable."},
            {"name": "Sanchar Saathi - Know Your Mobile", "url": "https://sancharsaathi.gov.in/",
             "step": "Check the make and model on Know Your Mobile (SMS 'KYM <IMEI>' to 14422) against the handset seized.",
             "what": "The make and model the IMEI belongs to, and whether it is genuine.",
             "how": "Open 'Know Genuineness of Your Mobile' and enter the IMEI (or SMS 'KYM <IMEI>' to 14422)."},
        ]
    elif t == "vehicle_plate":
        out += [
            {"name": "eChallan (Parivahan)", "url": "https://echallan.parivahan.gov.in/",
             "step": "Look up its challans on eChallan: each one is a dated place where the vehicle was seen.",
             "what": "Pending and paid traffic challans: each one says where and when a camera or officer caught the vehicle.",
             "how": "Open 'Check Online Services' then 'Get Challan Details', choose vehicle number and enter it."},
            {"name": "Vahan / mParivahan (RC)", "url": "https://vahan.parivahan.gov.in/vahanservice/",
             "step": "Pull the registration record on Vahan: owner, make, colour and financier.",
             "what": "The registration record: owner, make and model, colour, insurance and fitness, and finance (hypothecation).",
             "how": "Police access through the Vahan / CCTNS login; the citizen view shows only part of it."},
        ]
    elif t == "domain":
        out += [
            {**_I4C, "name": "I4C - Check website / app", "value": decoded.get("domain"),
             "step": "Check the site on the I4C portal (Check Suspect: Website/App) for fraud complaints.",
             "what": "Whether this website or app has been reported in a cyber-fraud complaint.",
             "how": "On the portal choose 'Report & Check Suspect', then 'Check Suspect (Website/App)'."},
            {"name": "URLhaus malware check", "url": f"https://urlhaus.abuse.ch/browse.php?search={urllib.parse.quote(decoded.get('domain', ''))}",
             "step": "Check URLhaus for whether the site has spread malware.",
             "what": "Whether the site has been seen spreading malware.",
             "how": "Opens the public search for this domain."},
            {"name": "Wayback Machine", "url": f"https://web.archive.org/web/*/{urllib.parse.quote(decoded.get('domain', ''))}",
             "step": "Save the site's archived pages from the Wayback Machine before it is taken down.",
             "what": "What the site looked like before, even if it has since been taken down.",
             "how": "Save the archived pages you rely on (date and address) for the case diary."},
        ]
    elif t == "email":
        out += [{**_I4C, "value": n}]
    if t in ("person_or_entity", "handle"):
        name = decoded.get("normalized") or ""
        out += [
            {"name": "eCourts - case status by party", "url": "https://services.ecourts.gov.in/ecourtindia_v6/",
             "step": "Search the name as a party on eCourts for cases in Karnataka's district courts.",
             "what": "Cases in any district court where this name is a party: case number, court, next date.",
             "how": "Open 'Case Status', choose 'Party Name', select Karnataka and the district, type the name."},
            {"name": "Indian Kanoon", "url": f"https://indiankanoon.org/search/?formInput={urllib.parse.quote(chr(34) + name + chr(34))}",
             "step": "Search Indian Kanoon for High Court judgments and bail orders naming them.",
             "what": "High Court and Supreme Court judgments that name this person, including bail orders.",
             "how": "Opens the search for the exact name; check each judgment is about the same person (father's name, address)."},
            {"name": "MCA - company and director search", "url": "https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do",
             "step": "If a company is involved, look it up on MCA for its directors and registered address.",
             "what": "Companies and directors of that name: useful when fraud runs through a registered company.",
             "how": "Search by company name or director; note the CIN or DIN for a notice to the Registrar of Companies."},
        ]
        if t == "handle":
            out.insert(0, {**_I4C, "value": decoded.get("normalized")})
    if t in ("phone", "upi_vpa", "email", "handle", "person_or_entity", "vehicle_plate", "domain", "bank_account"):
        news_q = (variants(decoded) or [n])[0]
        out.append({"name": "News search (English and Kannada)", "url": f"https://news.google.com/search?q={urllib.parse.quote(chr(34) + news_q + chr(34))}&hl=en-IN&gl=IN",
                    "step": "Search the news for it.",
                    "what": "News reports that mention this exactly.",
                    "how": "Opens the news search for the exact text."})
    return out


# ── 4. the officer's summary ───────────────────────────────────────────────────

_WHAT = {
    "phone": lambda d: f"An Indian mobile number ({d.get('normalized')}). {d.get('circle', '')}.",
    "upi_vpa": lambda d: f"A UPI ID on {d.get('psp_app')}, settled by {d.get('sponsor_bank')}."
                         + (f" It carries the mobile number {d['linked_mobile']}." if d.get("linked_mobile") else ""),
    "vehicle_plate": lambda d: f"A vehicle registered at {d.get('rto_office')} ({d.get('district')}, {d.get('state')}).",
    "email": lambda d: f"An email address on {d.get('domain')}.",
    "domain": lambda d: f"A website: {d.get('domain')}.",
    "ifsc": lambda d: f"A bank branch code (IFSC) of {d.get('bank_code')}.",
    "bank_account": lambda d: "A bank account number" + (f" at the branch with IFSC {d['ifsc']}." if d.get("ifsc") else " (no IFSC given, so the bank is not known)."),
    "imei": lambda d: "A mobile handset's IMEI.",
    "handle": lambda d: f"An online username: {d.get('normalized')}.",
    "person_or_entity": lambda d: f"A name: {d.get('normalized')}. A name alone can belong to many people; match on father's name, address or age before relying on anything.",
}


_KIND = {"Court / Legal Archive": "court or legal page", "Public / Govt Registry": "government page",
         "News / Media Archive": "news report", "Social / Digital Surface": "social-media page",
         "Commercial / Marketplace": "marketplace listing", "Open Web Surface": "other website"}


def build_brief(decoded: dict, web: dict, live: list[dict], official: list[dict], notice: dict) -> dict:
    t = decoded.get("target_type", "person_or_entity")
    what = _WHAT.get(t, _WHAT["person_or_entity"])(decoded)
    bank = next((c.get("bank") for c in live if c.get("bank")), None)
    if bank and t == "ifsc":
        what = f"A bank branch code (IFSC): {bank}."
    elif bank and t == "bank_account":
        what = f"A bank account at {bank} (IFSC {decoded.get('ifsc')})."

    claims = web.get("claims") or []
    checked = web.get("pages_checked", 0)
    if not web.get("reached", True):
        web_line = "The open-web search could not be reached just now, so nothing was checked there. Run it again in a minute."
    elif not claims:
        web_line = (f"No public page mentions it: {checked} pages checked, none contains it." if checked
                    else "No public page mentions it.")
    else:
        kinds: dict[str, int] = {}
        for c in claims:
            k = _KIND.get(c.get("category"), "other website")
            kinds[k] = kinds.get(k, 0) + 1
        parts = ", ".join(f"{v} {k}{'' if v == 1 else 's'}" for k, v in kinds.items())
        risky = [c for c in claims if c.get("matched_keywords")]
        web_line = (f"{len(claims)} public {'page mentions' if len(claims) == 1 else 'pages mention'} it ({parts}), "
                    f"out of {checked} checked.")
        if risky:
            web_line += f" {len(risky)} of them also {'talks' if len(risky) == 1 else 'talk'} about " \
                        + ", ".join(sorted({w for c in risky for w in c["matched_keywords"]})[:4]) + "."

    flags = [c["flag"] for c in live if c.get("flag")]
    flags += [f"Named on a page with: {', '.join(c['matched_keywords'][:3])}" for c in claims[:3] if c.get("matched_keywords")]

    steps = []
    for c in live:
        if c.get("status") == "found" and c.get("do"):
            steps.append(c["do"])
    for o in official[:3]:
        steps.append(o.get("step") or f"{o['name']}: {o['what']}")
    if notice.get("available"):
        steps.append(f"Send the drafted notice to {notice.get('recipient', 'the record holder').split(' — ')[0]} ({notice.get('statute', '').split(',')[0]}).")
    steps.append("Note in the case diary what was checked, when and where; these are leads, not evidence, until confirmed.")

    return {"what": what, "web": web_line, "flags": flags, "next": steps[:6],
            "live": [{"name": c["name"], "status": c["status"], "say": c["say"]} for c in live]}
