"""
Antar — Standalone OSINT API
============================
Strictly isolated Open-Source Intelligence & Forensic Reconnaissance endpoints
for the `/search` OSINT workbench.
NEVER accesses `main.db`, internal FIR records, or Antar core state.
"""

from fastapi import APIRouter, Depends, Query

from app.core.auth_middleware import require_role
from app.core.rate_limiter import rate_limit
from app.services.osint import search_osint
from app.services.osint_recon import run_multi_module_recon

# External search / recon is gated to Inspector and above and rate-limited.
router = APIRouter(dependencies=[Depends(require_role("Inspector")), Depends(rate_limit(20, 0.2))])


@router.get("/")
async def get_osint(
    entity: str = Query(min_length=2, max_length=120),
    sources: str | None = Query(default=None, max_length=300),
    depth: str = Query(default="standard", max_length=20),
):
    """
    Returns unverified open-web claims, domain classifications, and risk flags
    for the given entity/identifier. Strictly isolated from internal FIR data.
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    result = await search_osint(entity, sources=source_list, depth=depth)
    return result


@router.get("/recon")
async def get_osint_recon(
    entity: str = Query(min_length=2, max_length=120),
    sources: str | None = Query(default=None, max_length=300),
    depth: str = Query(default="standard", max_length=20),
):
    """
    Standalone Multi-Module OSINT & Indian Forensic Reconnaissance Endpoint.
    Operates with ZERO FIR database access (`internal_rows=None`).
    Returns:
      • Identifier decoder (Karnataka RTOs, UPI apps and banks, TRAI numbering)
      • BNSS §94 / §106 notice draft, only for an identifier with a holder to send it to
      • Link map built from the identifier itself
      • Phone-number decoder (circle first allocated; numbers can be ported)
      • Handle check links for an officer to open by hand
      • Step log
    Nothing here runs an outside tool or opens a page. Text that reads as an instruction is refused.
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    report = run_multi_module_recon(entity, internal_rows=None, sources=source_list, depth=depth)
    return report


@router.get("/investigate")
async def investigate(
    entity: str = Query(min_length=2, max_length=120),
    sources: str | None = Query(default=None, max_length=300),
    depth: str = Query(default="standard", max_length=20),
    lang: str = Query(default="en", max_length=5),
):
    """
    Everything an officer needs about one identifier, in one answer (lang=kn: in Kannada):
      • what it is (decoded: phone, UPI, vehicle, bank account / IFSC, IMEI, website, email,
        handle or name), and the drafted notice to whoever holds its records;
      • what the open web shows: only pages that actually contain it, each with what it
        matched on, and how many pages were checked and dropped;
      • live registry checks (IFSC branch, website registration and certificates, IMEI check
        digit), each "found", "not found" or "could not be reached";
      • the official portals to check next (I4C Suspect Registry, Sanchar Saathi, eChallan,
        eCourts ...), with what each tells and how to use it;
      • the officer's summary built from all of the above.
    Still no FIR access, and every result is an unverified lead.
    """
    import asyncio
    from datetime import datetime, timezone
    from app.services.osint_checks import build_brief, live_checks, official_checks

    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    report = run_multi_module_recon(entity, internal_rows=None, sources=source_list, depth=depth)
    if report.get("refused") or not report.get("query"):
        return {**report, "web": {"claims": [], "reached": False, "pages_checked": 0}, "live_checks": [],
                "official_checks": [], "brief": None}
    decoded = report["forensic_decoder"]
    web, live = await asyncio.gather(
        search_osint(report["query"], sources=source_list, depth=depth, decoded=decoded),
        live_checks(decoded),
    )
    official = official_checks(decoded)
    log = report.setdefault("bbot_scan_tree", [])
    now = datetime.now(timezone.utc).isoformat()
    log.append({"id": f"EVT-{len(log) + 1:02d}", "event_type": "OPEN_WEB", "source": "OpenWebSearch", "timestamp": now,
                "detail": f"Searched {', '.join(web.get('searched_forms') or [report['query']])}: {web.get('pages_checked', 0)} pages "
                          f"checked, {len(web.get('claims') or [])} contain it" + ("" if web.get("reached", True) else " (search not reached)")})
    for c in live:
        log.append({"id": f"EVT-{len(log) + 1:02d}", "event_type": "REGISTRY", "source": c["source"], "timestamp": c["checked_at"],
                    "detail": f"{c['name']}: {c['status']}. {c['say']}"})
    report.update({
        "web": web,
        "live_checks": live,
        "official_checks": official,
        "brief": build_brief(decoded, web, live, official, report.get("statutory_requisition") or {}),
    })
    if isinstance(lang, str) and lang.lower().startswith("kn"):    # called directly, lang is the Query default
        from app.services.osint_kn import to_kannada
        return to_kannada(report)
    return report


