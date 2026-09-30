"""
Antar — Product Store (P1: Compiled Intelligence Cache Layer)
==================================================================
Shifts request-time calculation to background pre-compiled "Products".
In-memory singleton mirroring the `graph_cache.py` pattern with TTL,
invalidation hooks, and automatic cold recalculation fallback.

Core API:
  • get_product(key: str) -> dict | None
  • put_product(key: str, payload: dict, ttl: int = 300) -> None
  • invalidate(prefix: str = "") -> int
  • register_generator(key: str, gen_func: Callable[[], dict], default_ttl: int = 300) -> None
  • refresh_all() -> dict[str, int]
"""

from __future__ import annotations

import time
import structlog
from typing import Any, Callable

logger = structlog.get_logger()

_products: dict[str, Any] = {}
_expires_at: dict[str, float] = {}
_generators: dict[str, tuple[Callable[[], Any], int]] = {}
_recalculating: set[str] = set()


def register_generator(key: str, gen_func: Callable[[], Any], default_ttl: int = 300) -> None:
    """Register a generator function for automatic cold calculation / refresh."""
    _generators[key] = (gen_func, default_ttl)


def put_product(key: str, payload: Any, ttl: int = 300) -> None:
    """Store a compiled product in memory with a specified TTL (in seconds)."""
    _products[key] = payload
    _expires_at[key] = time.time() + ttl if ttl > 0 else float("inf")
    logger.debug("product_stored", key=key, ttl=ttl)


def get_product(key: str) -> Any | None:
    """Retrieve a compiled product. If missing or expired, attempts cold recalculation."""
    now = time.time()
    if key in _products and now <= _expires_at.get(key, 0):
        return _products[key]

    # Check if we can recalculate from a registered generator
    if key in _generators and key not in _recalculating:
        _recalculating.add(key)
        gen_func, default_ttl = _generators[key]
        try:
            t0 = time.perf_counter()
            payload = gen_func()
            dt = (time.perf_counter() - t0) * 1000
            put_product(key, payload, ttl=default_ttl)
            logger.info("product_recalculated", key=key, latency_ms=round(dt, 2))
            return payload
        except Exception as e:
            logger.error("product_recalculate_failed", key=key, error=str(e))
            # Fall back to stale product if available
        finally:
            _recalculating.discard(key)
    return _products.get(key)


def list_products(prefix: str = "") -> list[str]:
    """List stored product keys matching prefix."""
    now = time.time()
    return [k for k in _products if (not prefix or k.startswith(prefix)) and now <= _expires_at.get(k, 0)]


def invalidate(prefix: str = "") -> int:
    """Invalidate products matching prefix (or all products if prefix is empty). Returns count invalidated."""
    keys_to_remove = [k for k in _products if not prefix or k.startswith(prefix)]
    for k in keys_to_remove:
        _products.pop(k, None)
        _expires_at.pop(k, None)
    logger.info("products_invalidated", prefix=prefix, count=len(keys_to_remove))
    return len(keys_to_remove)


def refresh_expiring(within_s: int = 90) -> dict[str, float]:
    """Proactively refresh registered products whose TTL expires within *within_s*
    seconds (or that are already expired/missing). Returns {key: latency_ms}."""
    now = time.time()
    latencies: dict[str, float] = {}
    for key, (gen_func, default_ttl) in _generators.items():
        if _expires_at.get(key, 0) - now > within_s:
            continue
        try:
            t0 = time.perf_counter()
            payload = gen_func()
            dt = (time.perf_counter() - t0) * 1000
            put_product(key, payload, ttl=default_ttl)
            latencies[key] = round(dt, 2)
        except Exception as e:
            logger.error("product_refresh_failed", key=key, error=str(e))
            latencies[key] = -1.0
    return latencies


def refresh_all() -> dict[str, float]:
    """Force refresh all registered product generators. Returns {key: latency_ms}."""
    latencies = {}
    for key, (gen_func, default_ttl) in _generators.items():
        try:
            t0 = time.perf_counter()
            payload = gen_func()
            dt = (time.perf_counter() - t0) * 1000
            put_product(key, payload, ttl=default_ttl)
            latencies[key] = round(dt, 2)
        except Exception as e:
            logger.error("product_refresh_failed", key=key, error=str(e))
            latencies[key] = -1.0
    return latencies


# ── Initial Boot Generators (P1 step 2) ──────────────────────────────────────

def _gen_registry_habitual() -> dict:
    from app.services.zcql_repo import build_spec
    from app.services.zcql_local import run_query, _world
    from app.agents import profile_agent
    world = _world()
    rows = run_query(build_spec("T5", {"min_priors": 1, "limit": 1000}))
    risks = profile_agent.risk_scores(world)
    offenders = [{
        "suspect_id": r["suspect_id"], "full_name": r.get("full_name"), "alias": r.get("alias"),
        "prior_count": r.get("prior_count"), "zone": r.get("address_zone"),
        "risk_score": risks.get(r["suspect_id"]),
    } for r in rows]
    offenders.sort(key=lambda x: (x["risk_score"] or 0), reverse=True)
    return {"offenders": offenders, "count": len(offenders)}


def _gen_evidence_stats() -> dict:
    from app.services import evidence_ledger
    return evidence_ledger.stats()


def _gen_network_global_stats() -> dict:
    from app.services import graph_cache
    return graph_cache.get_cache()["stats"]


def _gen_concurrency_districts() -> dict:
    import sqlite3
    from app.core.db_path import get_db_path
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT geo_lat AS lat, geo_lon AS lon, District_Name AS zone "
        "FROM FIRs WHERE geo_ok = 1 ORDER BY RANDOM() LIMIT 1000"
    ).fetchall()
    conn.close()
    points = [{"lat": r["lat"], "lon": r["lon"], "zone": r["zone"], "weight": 1} for r in rows]
    return {"points": points, "total": len(points), "compiled": True}


def _gen_prediction_board() -> dict:
    # Rolling as_of: each autonomous recompile stamps today's assessment date,
    # so the board never shows a stale date even between user requests.
    from app.api.pattern_predict import compile_board
    return compile_board(0, force=True)


def setup_default_products() -> None:
    """Register initial P1 products and pre-compile them."""
    register_generator("registry:habitual", _gen_registry_habitual, default_ttl=600)
    register_generator("evidence:stats", _gen_evidence_stats, default_ttl=3600)
    register_generator("network:global_stats", _gen_network_global_stats, default_ttl=3600)
    register_generator("concurrency:districts", _gen_concurrency_districts, default_ttl=600)
    register_generator("warning_ledger:board:all", _gen_prediction_board, default_ttl=21600)
    refresh_all()
