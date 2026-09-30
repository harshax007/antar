"""
Antar — Products API (P1: Compiled Intelligence Cache Layer)
=================================================================
Endpoints for inspecting, refreshing, and invalidating pre-compiled products.
"""

from fastapi import APIRouter, HTTPException
from app.services import product_store

router = APIRouter()


@router.get("/")
async def list_products() -> dict:
    """List all registered product keys and their cache status."""
    keys = list(product_store._generators.keys()) + list(product_store._products.keys())
    unique_keys = sorted(set(keys))
    status = []
    import time
    now = time.time()
    for k in unique_keys:
        exp = product_store._expires_at.get(k, 0)
        status.append({
            "key": k,
            "cached": k in product_store._products,
            "expires_in_sec": round(exp - now, 1) if exp != float("inf") and k in product_store._products else ("never" if k in product_store._products else "N/A"),
            "has_generator": k in product_store._generators
        })
    return {"products": status, "count": len(status)}


@router.get("/{key:path}")
async def get_product_endpoint(key: str) -> dict:
    """Retrieve the compiled payload for a specific product key."""
    payload = product_store.get_product(key)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Product '{key}' not found or not registered")
    return {"key": key, "payload": payload}


@router.post("/refresh")
async def refresh_products() -> dict:
    """Force re-compilation of all registered product generators."""
    latencies = product_store.refresh_all()
    return {"ok": True, "latencies_ms": latencies}
