"""
Antar — OSINT API (Phase 6)
================================
Endpoints for the Profiles side-by-side OSINT panel.
"""

from fastapi import APIRouter, Depends, Query

from app.core.auth_middleware import require_role
from app.core.rate_limiter import rate_limit
from app.services.osint import search_osint

# A name typed here leaves the building as a web search. Inspector and above, and slowly.
router = APIRouter(dependencies=[Depends(require_role("Inspector")), Depends(rate_limit(20, 0.2))])

@router.get("/")
async def get_osint(entity: str = Query(min_length=2, max_length=120)):
    """
    Returns unverified open-web claims and risk flags for the given entity.
    """
    result = await search_osint(entity)
    return result


@router.get("/recon")
async def get_osint_recon(entity: str = Query(min_length=2, max_length=120)):
    """
    Layer 5 Multi-Module Reconnaissance Endpoint.
    Returns:
      • Maltego Linkage Graph (nodes & edges)
      • PhoneInfoga Telecom Footprint Analysis
      • Sherlock Quarantined Digital Handle Presence
      • BBOT Event Scan Tree
      • OSINT Corroboration Counter against internal K/D facts
    """
    from app.services.osint_recon import run_multi_module_recon
    from app.services.zcql_local import _world
    world = _world()
    report = run_multi_module_recon(entity, world)
    return report

