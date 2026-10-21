"""OSINT that an officer can act on: the identifier is recognised, only pages that contain it
count, the live registry checks say found / not found / not reached, and the summary says
what to do next. No network: every outside service is replaced."""
import asyncio
import json

import pytest

from app.core import egress
from app.services import osint_checks as oc
from app.services.osint_recon import _classify_and_decode_target as decode, run_multi_module_recon


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ── what the identifier is ─────────────────────────────────────────────────────

@pytest.mark.parametrize("q,kind", [
    ("SBIN0040071", "ifsc"),
    ("30881234567 SBIN0040071", "bank_account"),
    ("30881234567", "bank_account"),
    ("490154203237518", "imei"),
    ("paytm-kyc-update.xyz", "domain"),
    ("https://www.sbi-rewards.online/login?x=1", "domain"),
    ("r.k.sharma", "handle"),               # dots, but no real top-level domain: not a website
    ("+91 98450 67890", "phone"),
    ("919845067890", "phone"),
    ("9845012345@ybl", "upi_vpa"),
    ("x@gmail.com", "email"),
    ("KA-02-MJ-4821", "vehicle_plate"),
    ("Ramesh Gowda", "person_or_entity"),
])
def test_identifier_types(q, kind):
    assert decode(q)["target_type"] == kind


def test_bank_account_keeps_number_and_ifsc_apart():
    d = decode("30881234567 SBIN0040071")
    assert d["account_number"] == "30881234567" and d["ifsc"] == "SBIN0040071"
    assert oc.variants(d) == ["30881234567"]          # the web is searched for the account, not "a / b"


# ── only pages that contain it ─────────────────────────────────────────────────

def test_a_phone_matches_however_it_is_written():
    d = decode("+91 98450 67890")
    for text in ("Call 98450-67890 now", "+91 9845067890", "contact: 98450 67890"):
        assert oc.match(d, text)["strength"] == "exact"
    assert oc.match(d, "Arrest records, mugshots and warrants") is None
    assert "98450 67890" in oc.variants(d) and "9845067890" in oc.variants(d)


def test_a_plate_matches_with_or_without_separators():
    d = decode("KA-02-MJ-4821")
    assert oc.match(d, "Car KA 02 MJ 4821 seized") and oc.match(d, "ka02mj4821")
    assert oc.match(d, "KA-02-MJ-4822") is None


def test_a_name_must_appear_as_a_name():
    d = decode("Ramesh Gowda")
    assert oc.match(d, "Accused Ramesh Gowda was produced")["strength"] == "name"
    assert oc.match(d, "Gowda said Ramesh left")["strength"] == "partial"
    assert oc.match(d, "Ramesh Kumar and Suresh Gowda") ["strength"] == "partial"
    assert oc.match(d, "Microsoft Windows help") is None


def test_unrelated_handle_text_does_not_match():
    d = decode("@vinay_k")
    assert oc.match(d, "follow @vinay_k on x")
    assert oc.match(d, "@vinay_kumar is someone else") is None


# ── live registry checks ───────────────────────────────────────────────────────

class _R:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}

    def json(self):
        return self._body


def _client(routes):
    class C:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, **k):
            for prefix, resp in routes.items():
                if url.startswith(prefix):
                    if isinstance(resp, Exception):
                        raise resp
                    return resp
            raise RuntimeError(f"unexpected {url}")
    return C


def test_ifsc_found(monkeypatch):
    monkeypatch.setattr(oc.httpx, "AsyncClient", _client({"https://ifsc.razorpay.com/": _R(200, {
        "BANK": "State Bank of India", "BRANCH": "MIRLE", "ADDRESS": "MIRLE, MYSORE", "CITY": "MYSORE",
        "DISTRICT": "MYSORE", "STATE": "KARNATAKA", "CONTACT": "+918223282221", "UPI": True, "IMPS": True})}))
    [c] = run(oc.live_checks(decode("SBIN0040071")))
    assert c["status"] == "found" and "Mirle" in c["bank"] and "nodal officer" in c["do"]
    assert {"label": "Payments it takes", "value": "UPI, IMPS"} in c["facts"]


def test_an_ifsc_not_in_the_rbi_list_is_flagged(monkeypatch):
    monkeypatch.setattr(oc.httpx, "AsyncClient", _client({"https://ifsc.razorpay.com/": _R(404)}))
    [c] = run(oc.live_checks(decode("ABCD0123456")))
    assert c["status"] == "none" and c["flag"] == "IFSC not in the RBI list"


def test_a_young_website_is_flagged_after_following_the_registry_redirect(monkeypatch):
    from datetime import datetime, timedelta, timezone
    made = (datetime.now(timezone.utc) - timedelta(days=12)).strftime("%Y-%m-%dT%H:%M:%SZ")
    monkeypatch.setattr(oc.httpx, "AsyncClient", _client({
        "https://rdap.org/domain/": _R(302, headers={"location": "https://rdap.centralnic.com/online/domain/sbi-rewards.online"}),
        "https://rdap.centralnic.com/": _R(200, {"events": [{"eventAction": "registration", "eventDate": made}],
                                                 "entities": [{"roles": ["registrar"], "vcardArray": ["vcard", [["fn", {}, "text", "Cheap Names Inc."]]]}]}),
        "https://crt.sh/": RuntimeError("slow"),
    }))
    rdap, crt = run(oc.live_checks(decode("sbi-rewards.online")))
    assert rdap["status"] == "found" and rdap["flag"] == "Website only 12 days old"
    assert "Cheap Names Inc" in rdap["do"] and "Inc.." not in rdap["say"]
    assert crt["status"] == "unreached" and crt["facts"] == []          # nothing filled in


def test_a_redirect_off_https_is_refused(monkeypatch):
    monkeypatch.setattr(oc.httpx, "AsyncClient", _client({
        "https://rdap.org/domain/": _R(302, headers={"location": "http://rdap.example.com/x"}),
        "https://crt.sh/": RuntimeError("slow")}))
    rdap, _ = run(oc.live_checks(decode("example.online")))
    assert rdap["status"] == "unreached"


def test_imei_check_digit_needs_no_network():
    assert oc.luhn_ok("490154203237518") and not oc.luhn_ok("490154203237519")
    [ok] = run(oc.live_checks(decode("490154203237518")))
    [bad] = run(oc.live_checks(decode("490154203237519")))
    assert ok["status"] == "found" and bad["status"] == "none" and bad["flag"] == "IMEI check digit is wrong"


def test_registry_servers_are_allowed_only_for_registry_lookups(monkeypatch):
    monkeypatch.setattr(egress, "_setting", lambda: "")
    assert egress.allowed("https://rdap.verisign.com/com/v1/domain/x.com", "registry_lookup")
    assert not egress.allowed("https://rdap.verisign.com/com/v1/domain/x.com", "open_web_search")
    assert not egress.allowed("https://evil.example.com/", "registry_lookup")
    assert egress.allowed("https://ifsc.razorpay.com/SBIN0040071", "registry_lookup")


# ── official checks and the summary ────────────────────────────────────────────

@pytest.mark.parametrize("q", ["+91 98450 67890", "9845012345@ybl", "KA-02-MJ-4821", "490154203237518",
                               "sbi-rewards.online", "Ramesh Gowda", "30881234567 SBIN0040071", "x@corp.in"])
def test_every_official_check_says_what_to_do(q):
    checks = oc.official_checks(decode(q))
    assert checks
    for c in checks:
        assert c["url"].startswith("https://") and c["step"] and c["what"] and c["how"]


def test_the_news_link_for_a_phone_uses_the_plain_number():
    news = [c for c in oc.official_checks(decode("+91 98450 67890")) if "news.google" in c["url"]][0]
    assert "%229845067890%22" in news["url"]


def test_profile_links_only_for_things_that_have_profiles():
    assert run_multi_module_recon("SBIN0040071")["sherlock_handles"] == []
    assert run_multi_module_recon("KA-02-MJ-4821")["sherlock_handles"] == []
    assert run_multi_module_recon("@vinay_k")["sherlock_handles"]


@pytest.mark.parametrize("q,recipient", [("30881234567 SBIN0040071", "IFSC SBIN0040071"), ("490154203237518", "Airtel"),
                                         ("sbi-rewards.online", "registrar"), ("x@corp.in", "corp.in")])
def test_new_identifier_types_get_a_notice_to_the_right_holder(q, recipient):
    n = run_multi_module_recon(q)["statutory_requisition"]
    assert n["available"] and recipient in n["recipient"] and n["template_text"]


def test_brief_says_nothing_was_found_and_how_much_was_checked():
    d = decode("+91 98450 67890")
    b = oc.build_brief(d, {"claims": [], "reached": True, "pages_checked": 10}, [], oc.official_checks(d),
                       {"available": True, "recipient": "Nodal Officer — TSP", "statute": "Section 94, BNSS"})
    assert b["web"] == "No public page mentions it: 10 pages checked, none contains it."
    assert b["next"][0].startswith("Check it on the I4C Suspect Registry")
    assert any("Send the drafted notice" in s for s in b["next"]) and "case diary" in b["next"][-1]


def test_brief_when_the_search_was_not_reached():
    d = decode("Ramesh Gowda")
    b = oc.build_brief(d, {"claims": [], "reached": False}, [], [], {})
    assert "could not be reached" in b["web"] and "many people" in b["what"]


def test_investigate_puts_it_together(monkeypatch):
    from app.api import osint_api
    from app.services import osint

    async def web(*a, **k):
        return {"claims": [], "reached": True, "pages_checked": 7, "searched_forms": ["9845067890"]}

    async def live(d):
        return []
    monkeypatch.setattr(osint_api, "search_osint", web)
    monkeypatch.setattr(oc, "live_checks", live)
    r = run(osint_api.investigate("+91 98450 67890", None, "standard"))
    assert r["brief"]["web"].startswith("No public page mentions it: 7 pages checked")
    assert r["official_checks"] and r["statutory_requisition"]["available"]
    assert any(e["event_type"] == "OPEN_WEB" and "7 pages" in e["detail"] for e in r["bbot_scan_tree"])
    json.dumps(r)                                                  # the API can serialise it


def test_investigate_in_kannada_keeps_the_facts(monkeypatch):
    """lang=kn rewrites what an officer reads; identifiers, counts and the notice stay as they are."""
    from app.api import osint_api

    async def web(*a, **k):
        return {"claims": [], "reached": True, "pages_checked": 9, "searched_forms": ["9845067890"]}

    async def live(d):
        return []
    monkeypatch.setattr(osint_api, "search_osint", web)
    monkeypatch.setattr(oc, "live_checks", live)
    en = run(osint_api.investigate("+91 98450 67890", None, "standard", "en"))
    kn = run(osint_api.investigate("+91 98450 67890", None, "standard", "kn"))
    assert kn["lang"] == "kn" and kn["forensic_decoder"]["target_label"] == "ಮೊಬೈಲ್ ಸಂಖ್ಯೆ"
    assert "9 ಪುಟಗಳನ್ನು" in kn["brief"]["web"]
    assert all(o["key"] for o in kn["official_checks"]) and kn["official_checks"][0]["name"] != en["official_checks"][0]["name"]
    assert [o["url"] for o in kn["official_checks"]] == [o["url"] for o in en["official_checks"]]
    assert kn["statutory_requisition"]["template_text"] == en["statutory_requisition"]["template_text"]


def test_kannada_live_check_is_rebuilt_from_its_facts():
    from app.services.osint_kn import _live
    c = {"name": "IMEI check digit", "status": "none", "facts": [{"label": "Check digit", "value": "9 - wrong"}], "say": "x"}
    k = _live(c)
    assert k["key"] == "IMEI check digit" and k["flag"] == "IMEI ಪರಿಶೀಲನಾ ಅಂಕಿ ತಪ್ಪಾಗಿದೆ"
    assert k["facts"][0]["label"] == "ಪರಿಶೀಲನಾ ಅಂಕಿ" and k["facts"][0]["value"] == "9 - wrong"


def test_kannada_says_what_a_page_matched_on():
    from app.services.osint_kn import to_kannada
    r = to_kannada({"web": {"claims": [{"matched_on": "the IMEI"}, {"matched_on": "the number 98450 67890"}]}})
    assert [c["matched_on"] for c in r["web"]["claims"]] == ["IMEI", "ಸಂಖ್ಯೆ 98450 67890"]
