"""
Phase P1 Acceptance Tests: Product Store & Compiled Intelligence Layer
======================================================================
Verifies that:
  • product_store caches and invalidates products cleanly
  • setup_default_products() initializes the 4 required P1 products
  • hitting registry:habitual 10 times in a row shows constant < 15 ms latency
  • /api/products endpoints respond correctly
"""

import time
import pytest
from httpx import AsyncClient, ASGITransport

from app.services import product_store


class TestProductStoreService:
    def test_lifecycle_and_ttl(self):
        product_store.put_product("test:val", {"foo": "bar"}, ttl=1)
        assert product_store.get_product("test:val") == {"foo": "bar"}
        
        # Test invalidation
        product_store.invalidate("test:")
        assert product_store.get_product("test:val") is None

    def test_generator_fallback(self):
        def _gen():
            return {"generated": True, "ts": time.time()}
            
        product_store.register_generator("test:gen", _gen, default_ttl=60)
        product_store.invalidate("test:gen")
        
        res1 = product_store.get_product("test:gen")
        assert res1["generated"] is True
        
        # Second call should return cached payload
        res2 = product_store.get_product("test:gen")
        assert res1["ts"] == res2["ts"]

    def test_setup_default_products(self):
        product_store.setup_default_products()
        for key in ("registry:habitual", "evidence:stats", "network:global_stats", "concurrency:districts"):
            val = product_store.get_product(key)
            assert val is not None, f"Default product {key} failed to generate"

    def test_registry_latency_under_15ms(self):
        """P1 Acceptance Criteria: hitting registry 10 times shows constant < 15 ms latency."""
        product_store.setup_default_products()
        
        latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            _ = product_store.get_product("registry:habitual")
            dt = (time.perf_counter() - t0) * 1000
            latencies.append(dt)
            
        max_lat = max(latencies)
        assert max_lat < 15.0, f"Max latency was {max_lat:.2f} ms, expected < 15 ms"


class TestProductStoreEndpoints:
    @pytest.mark.anyio
    async def test_list_products_200(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get("/api/products/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 4

    @pytest.mark.anyio
    async def test_get_product_endpoint_200(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.get("/api/products/registry:habitual")
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "registry:habitual"
        assert "offenders" in data["payload"]

    @pytest.mark.anyio
    async def test_refresh_endpoint_200(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
            resp = await c.post("/api/products/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "registry:habitual" in data["latencies_ms"]
