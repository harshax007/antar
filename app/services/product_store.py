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


# Products that take 10-45 s of full-table aggregates (the Data Overview's KPIs, officer
# view and crime cycles) are also kept on disk. In memory only, every restart made the
# first officers to open the Brain or Data Overview wait 30-48 s while warm-up recomputed
# them. On disk they are tied to the registry's signature (row count and newest row id):
# rows added or removed and they are recomputed, never served stale; the TTL still applies.
_PERSIST_PREFIXES = ("dataset:",)
_sig_cache: dict = {"value": None}


def _persisted(key: str) -> bool:
    return key.startswith(_PERSIST_PREFIXES)


def _registry_sig() -> str | None:
    if _sig_cache["value"] is None:
        try:
            import sqlite3
            from app.core.db_path import get_db_path
            conn = sqlite3.connect(get_db_path(), timeout=10)
            try:
                n, top = conn.execute("SELECT COUNT(*), COALESCE(MAX(rowid), 0) FROM FIRs").fetchone()
            finally:
                conn.close()
            _sig_cache["value"] = f"{n}:{top}"
        except Exception:
            return None
    return _sig_cache["value"]


def _disk():
    import sqlite3
    from app.core.db_path import get_db_path
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.execute("CREATE TABLE IF NOT EXISTS product_cache (key TEXT PRIMARY KEY, sig TEXT NOT NULL, "
                 "expires_at REAL NOT NULL, payload TEXT NOT NULL)")
    return conn


def _disk_put(key: str, payload: Any, expires_at: float) -> None:
    import json
    sig = _registry_sig()
    if sig is None:
        return
    try:
        body = json.dumps(payload)
        if json.loads(body) != payload:            # a tuple or a date would come back changed
            return
        conn = _disk()
        try:
            conn.execute("INSERT OR REPLACE INTO product_cache VALUES (?, ?, ?, ?)", (key, sig, expires_at, body))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:                         # the disk copy is a convenience, never a failure
        logger.debug("product_disk_put_failed", key=key, error=str(e))


def _disk_get(key: str) -> Any | None:
    import json
    sig = _registry_sig()
    if sig is None:
        return None
    try:
        conn = _disk()
        try:
            row = conn.execute("SELECT sig, expires_at, payload FROM product_cache WHERE key = ?", (key,)).fetchone()
        finally:
            conn.close()
    except Exception:
        return None
    if not row or row[0] != sig or row[1] < time.time():
        return None
    payload = json.loads(row[2])
    _products[key] = payload
    _expires_at[key] = row[1]
    logger.debug("product_loaded_from_disk", key=key)
    return payload


def put_product(key: str, payload: Any, ttl: int = 300) -> None:
    """Store a compiled product in memory with a specified TTL (in seconds)."""
    _products[key] = payload
    _expires_at[key] = time.time() + ttl if ttl > 0 else float("inf")
    if _persisted(key) and ttl > 0:
        _disk_put(key, payload, _expires_at[key])
    logger.debug("product_stored", key=key, ttl=ttl)


def get_product(key: str) -> Any | None:
    """Retrieve a compiled product. If missing or expired, attempts cold recalculation."""
    now = time.time()
    if key in _products and now <= _expires_at.get(key, 0):
        return _products[key]
    if _persisted(key):
        hit = _disk_get(key)
        if hit is not None:
            return hit

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
    if not prefix or _persisted(prefix) or any(p.startswith(prefix) for p in _PERSIST_PREFIXES):
        _sig_cache["value"] = None                 # rows may have changed: re-read the signature
        try:
            conn = _disk()
            try:
                conn.execute("DELETE FROM product_cache WHERE key LIKE ?", (prefix.replace("%", "") + "%",))
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass
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
