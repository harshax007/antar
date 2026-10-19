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
      • Indian Forensic Identifier Decoder (70+ KA RTOs, 30+ UPI PSPs, TRAI E.164)
      • Statutory BNSS §94 / §106 Requisition Draft
      • Maltego Open-Source Entity Topology (nodes & edges)
      • PhoneInfoga Telecom Footprint Analysis
      • Sherlock Quarantined Digital Surface Matrix
      • BBOT Chronological Event Scan Tree
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    report = run_multi_module_recon(entity, internal_rows=None, sources=source_list, depth=depth)
    return report


