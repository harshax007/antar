"""
Antar — Dashboard / Overview API (UC2 "Explore" surface · feature N1)
=========================================================================
Role-aware Overview KPIs + summary panels for the dashboard landing page.

Read-only, and aggregated ONLY through whitelisted ZCQL templates (never free-form
SQL) — so the same anti-hallucination guarantee that protects chat also protects the
analytics surface. Local-first (seed JSON via the executor); swaps to Catalyst Data
Store with the USE_LOCAL flag, no code change here.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.services.zcql_repo import build_spec
from app.services.zcql_local import run_query
from app.services import alerts_store

router = APIRouter()


def _rows(template_id: str, params: dict) -> list[dict]:
    """Run one whitelisted template and return its rows (params are backend-owned)."""
    return run_query(build_spec(template_id, params))


@router.get("/overview")
async def overview() -> dict:
    """Overview KPIs + summary panels for the dashboard landing (N1).
    Composed from whitelisted templates: T13 (by type), T8 (by status),
    T11 (hotspots this month), T3 (12-month trend), T12 (recent crimes)."""
    # Point overview to the newly generated 2024-2026 data specifically
    base_params = {"date_from": "2024-01-01"}
    
    by_type = _rows("T13", base_params)                          # [{crime_type, n}]
    by_status = _rows("T8", base_params)                         # [{status, n}]
    hotspots = _rows("T11", {"date_from": "2026-06-01", "date_to": "2026-06-30"}) # this month (June 2026)
    trend = _rows("T3", {"months": 18})                 # covers all of 2025-2026
    recent = _rows("T12", {"limit": 8})                 # latest crime rows (automatically gets 2026)

    total = sum(r.get("n", 0) for r in by_status)
    status_map = {r.get("status"): r.get("n", 0) for r in by_status if r.get("status")}

    return {
        "kpis": {
            "total_crimes": total,
            "open_cases": status_map.get("under_investigation", 0),
            "charge_sheeted": status_map.get("charge_sheeted", 0),
            "disposed": status_map.get("disposed", 0),
            "active_alerts": alerts_store.active_count(),
            "top_zone_this_month": hotspots[0]["zone"] if hotspots else None,
        },
        "crime_by_type": by_type[:10],
        "by_status": by_status,
        "hotspots_this_month": hotspots[:6],
        "trend_12m": trend,
        "recent_crimes": recent,
    }
