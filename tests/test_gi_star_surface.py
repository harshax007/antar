"""
Task 7: Gi* significance surface — GET /api/map/gi_star + gi_star_surface().
Tests cover:
  • gi_star_surface() function: field contract, ordering, hotspot vs p-value contract
  • crime_type filter reduces results to that type
  • WOW-3 zone: Rajajinagar is a confirmed hotspot for chain_snatching
  • HTTP endpoint: 200, field contract, confirmed_hotspots count, total_zones
  • days parameter: shorter window → fewer or equal observed counts
  • Existing map endpoints still pass (regression)
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.services.anomaly import gi_star_surface


# ── gi_star_surface() function ────────────────────────────────────────────────

class TestGiStarSurface:
    def test_returns_list(self):
        result = gi_star_surface()
        assert isinstance(result, list)

    def test_all_zones_have_required_fields(self):
        result = gi_star_surface()
        required = {"zone", "lat", "lon", "crime_type", "gi_stat", "p_value",
                    "is_hotspot", "observed"}
        for z in result:
            missing = required - set(z.keys())
            assert not missing, f"zone {z['zone']} missing fields: {missing}"

    def test_p_value_range(self):
        result = gi_star_surface()
        for z in result:
            assert 0.0 <= z["p_value"] <= 1.0, \
                f"{z['zone']} p_value {z['p_value']} out of [0,1]"

    def test_is_hotspot_consistent_with_p_value(self):
        """is_hotspot=True ↔ p_value < 0.05 (the criminology significance threshold)."""
        result = gi_star_surface()
        for z in result:
            if z["is_hotspot"]:
                assert z["p_value"] < 0.05, \
                    f"{z['zone']} flagged as hotspot but p={z['p_value']:.4f} >= 0.05"
            else:
                assert z["p_value"] >= 0.05, \
                    f"{z['zone']} not hotspot but p={z['p_value']:.4f} < 0.05"

    def test_sorted_by_gi_stat_desc(self):
        result = gi_star_surface()
        stats = [z["gi_stat"] for z in result]
        assert stats == sorted(stats, reverse=True), \
            "gi_star_surface must be sorted by gi_stat descending"

    def test_observed_non_negative(self):
        result = gi_star_surface()
        for z in result:
            assert z["observed"] >= 0

    def test_crime_type_all_when_no_filter(self):
        result = gi_star_surface()
        for z in result:
            assert z["crime_type"] == "all"

    def test_crime_type_filter_sets_field(self):
        result = gi_star_surface(crime_type="chain_snatching")
        for z in result:
            assert z["crime_type"] == "chain_snatching"

    def test_crime_type_filter_reduces_counts(self):
        """Filtering by a single crime type should give ≤ aggregate observed counts."""
        all_result = gi_star_surface()
        filtered   = gi_star_surface(crime_type="chain_snatching")
        all_total  = sum(z["observed"] for z in all_result)
        filt_total = sum(z["observed"] for z in filtered)
        assert filt_total <= all_total, \
            f"Filtered total {filt_total} > aggregate total {all_total}"

    def test_shorter_window_has_fewer_or_equal_observed(self):
        """days=7 should observe ≤ days=90 counts in total."""
        short = sum(z["observed"] for z in gi_star_surface(days=7))
        long  = sum(z["observed"] for z in gi_star_surface(days=90))
        assert short <= long, f"7-day total {short} > 90-day total {long}"

    def test_rajajinagar_chain_snatching_is_hotspot(self):
        """WOW-3: Rajajinagar chain-snatching must be a confirmed Gi* hotspot.
        Uses days=90 (≈ 13-week anomaly baseline) to capture the full planted spike.
        The 30-day window gives p≈0.065 (borderline); 90-day is robustly significant.
        """
        result = gi_star_surface(crime_type="chain_snatching", days=90)
        raj = next(
            (z for z in result if "Rajajinagar" in z["zone"]),
            None,
        )
        assert raj is not None, \
            "Rajajinagar not found in gi_star_surface(crime_type='chain_snatching')"
        assert raj["is_hotspot"], \
            (f"Rajajinagar chain_snatching not flagged as hotspot: "
             f"gi_stat={raj['gi_stat']:.3f}, p={raj['p_value']:.4f}")

    def test_lat_lon_non_null_for_all_zones(self):
        result = gi_star_surface()
        for z in result:
            assert z["lat"] is not None and z["lon"] is not None, \
                f"{z['zone']} has null lat/lon"

    def test_total_zone_count_positive(self):
        assert len(gi_star_surface()) > 0


# ── GET /api/map/gi_star ─────────────────────────────────────────────────────

class TestGiStarEndpoint:
    @pytest.mark.anyio
    async def test_200_ok(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            resp = await c.get("/api/map/gi_star")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_top_level_keys(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/map/gi_star")).json()
        for key in ("zones", "confirmed_hotspots", "total_zones",
                    "window_days", "crime_type"):
            assert key in data, f"missing top-level key: {key}"

    @pytest.mark.anyio
    async def test_total_zones_matches_zones_length(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/map/gi_star")).json()
        assert data["total_zones"] == len(data["zones"])

    @pytest.mark.anyio
    async def test_confirmed_hotspots_matches_flag_count(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/map/gi_star")).json()
        expected = sum(1 for z in data["zones"] if z["is_hotspot"])
        assert data["confirmed_hotspots"] == expected

    @pytest.mark.anyio
    async def test_crime_type_filter_param(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/map/gi_star",
                                params={"crime_type": "chain_snatching"})).json()
        assert data["crime_type"] == "chain_snatching"
        for z in data["zones"]:
            assert z["crime_type"] == "chain_snatching"

    @pytest.mark.anyio
    async def test_window_days_param(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/map/gi_star", params={"days": 7})).json()
        assert data["window_days"] == 7

    @pytest.mark.anyio
    async def test_zone_fields_in_response(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/map/gi_star")).json()
        required = {"zone", "lat", "lon", "gi_stat", "p_value", "is_hotspot", "observed"}
        for z in data["zones"]:
            missing = required - set(z.keys())
            assert not missing, f"zone {z['zone']} missing: {missing}"

    @pytest.mark.anyio
    async def test_hotspots_have_p_below_005(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/map/gi_star")).json()
        for z in data["zones"]:
            if z["is_hotspot"]:
                assert z["p_value"] < 0.05, \
                    f"Hotspot {z['zone']} has p={z['p_value']:.4f} >= 0.05"

    @pytest.mark.anyio
    async def test_default_crime_type_is_all(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/map/gi_star")).json()
        assert data["crime_type"] == "all"

    @pytest.mark.anyio
    async def test_rajajinagar_hotspot_via_endpoint(self):
        """WOW-3: Rajajinagar must surface as a confirmed hotspot via the endpoint."""
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            data = (await c.get("/api/map/gi_star",
                                params={"crime_type": "chain_snatching",
                                        "days": 90})).json()
        raj = next((z for z in data["zones"] if "Rajajinagar" in z["zone"]), None)
        assert raj is not None, "Rajajinagar missing from gi_star endpoint response"
        assert raj["is_hotspot"], \
            f"Rajajinagar not confirmed hotspot: gi={raj['gi_stat']:.3f} p={raj['p_value']:.4f}"


# ── Regression: existing map endpoints ───────────────────────────────────────

class TestMapRegression:
    @pytest.mark.anyio
    async def test_hotspots_still_works(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            resp = await c.get("/api/map/hotspots")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0

    @pytest.mark.anyio
    async def test_districts_rich_still_works(self):
        from main import app as fastapi_app
        async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                               base_url="http://test") as c:
            resp = await c.get("/api/map/districts/rich")
        assert resp.status_code == 200
        assert resp.json()["total"] > 0
