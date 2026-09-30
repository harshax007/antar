"""
Full Dataset API — GET /api/dataset/overview and /api/dataset/records.

Covers:
  • overview: 200, KPI contract, non-negative counts, arrest_rate sane
  • overview: labels are normalised (no duplicate stage/group rows differing only by
    case or stray whitespace — the seed data really does contain both shapes)
  • overview: year/district filters narrow the total
  • records: pagination + limit clamp, row shape matches the frontend contract
  • records: search narrows the total
"""

import pytest
from httpx import AsyncClient, ASGITransport


async def _get(path: str):
    from main import app as fastapi_app
    async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                           base_url="http://test") as c:
        return await c.get(path)


class TestDatasetOverview:
    @pytest.mark.anyio
    async def test_contract_and_counts(self):
        resp = await _get("/api/dataset/overview")
        assert resp.status_code == 200
        d = resp.json()
        for k in ("total", "districts", "stations", "victims", "accused", "arrested",
                  "chargesheeted", "convictions", "arrest_rate", "stages",
                  "by_crime_group", "years", "top_districts", "source"):
            assert k in d, f"missing {k}"
        assert d["total"] > 0
        assert d["districts"] > 0 and d["stations"] > 0
        assert 0 <= d["arrest_rate"] <= 100
        for key in ("victims", "accused", "arrested", "chargesheeted", "convictions"):
            assert d[key] >= 0

    @pytest.mark.anyio
    async def test_labels_are_normalised(self):
        """Seed data holds 'Under Investigation' AND 'under_investigation', plus
        ' CYBER CRIME' with a leading space — grouping must collapse those."""
        d = (await _get("/api/dataset/overview")).json()
        stage_labels = [s["label"] for s in d["stages"]]
        assert len(stage_labels) == len(set(stage_labels))
        group_names = [g["name"] for g in d["by_crime_group"]]
        assert len(group_names) == len(set(group_names))
        for n in group_names:
            assert n == n.strip(), f"un-trimmed group name: {n!r}"

    @pytest.mark.anyio
    async def test_filters_narrow_total(self):
        base = (await _get("/api/dataset/overview")).json()
        year = base["years"][0]["year"]
        filt = (await _get(f"/api/dataset/overview?year={year}")).json()
        assert 0 < filt["total"] <= base["total"]

        district = base["top_districts"][0]["district"]
        fd = (await _get(f"/api/dataset/overview?district={district}")).json()
        assert 0 < fd["total"] <= base["total"]


class TestDatasetRecords:
    @pytest.mark.anyio
    async def test_row_shape_and_pagination(self):
        resp = await _get("/api/dataset/records?limit=5")
        assert resp.status_code == 200
        d = resp.json()
        assert d["limit"] == 5 and d["offset"] == 0
        assert d["total"] > 0
        assert len(d["rows"]) <= 5
        row = d["rows"][0]
        for k in ("_i", "_year", "_month", "District_Name", "UnitName", "CrimeGroup_Name",
                  "FIR_Stage", "Victim_Count", "Accused_Count", "Arrested_Count"):
            assert k in row, f"missing {k}"

        page2 = (await _get("/api/dataset/records?limit=5&offset=5")).json()
        assert [r["_i"] for r in page2["rows"]] != [r["_i"] for r in d["rows"]]

    @pytest.mark.anyio
    async def test_limit_clamped(self):
        d = (await _get("/api/dataset/records?limit=9999")).json()
        assert d["limit"] <= 200 and len(d["rows"]) <= 200

    @pytest.mark.anyio
    async def test_search_narrows(self):
        base = (await _get("/api/dataset/records?limit=1")).json()
        hit = (await _get("/api/dataset/records?limit=1&q=Bengaluru")).json()
        assert 0 < hit["total"] <= base["total"]


class TestDatasetCycles:
    # Contract (changed 2026-09-18). "All" used to mean COUNT(*) over the whole table, with
    # no date gate. That drew FIRs dated after today, and summing years that cover different
    # months invented seasonality (2024 stops in March, so Jan-Mar read ~30% above the rest
    # of the year). "All" now means every COMPLETE year, future-dated rows excluded; partial
    # years remain available on their own chips.

    @pytest.mark.anyio
    async def test_cycles_all_total_is_complete_years(self):
        """The "All" total equals an exact SQL count over the complete years it reports."""
        import sqlite3
        from app.services.zcql_local import DB_PATH
        from app.core.db_path import ensure_db_staged
        resp = await _get("/api/dataset/cycles")
        assert resp.status_code == 200
        d = resp.json()
        scope = d["scope_years"]
        assert scope, "no complete years in scope"
        cover = {y["year"]: y["months_covered"] for y in d["years"]}
        assert all(cover[y] == 12 for y in scope), "a partial year leaked into All"
        assert all(cover[y] < 12 for y in d["partial_years"])

        ensure_db_staged()
        con = sqlite3.connect(DB_PATH)
        ph = ",".join("?" * len(scope))
        sql_total = con.execute(
            "SELECT COUNT(*) FROM FIRs WHERE date <= date('now','localtime')"
            f" AND substr(date,1,4) IN ({ph})", [f"{y:04d}" for y in scope]).fetchone()[0]
        con.close()
        assert d["total"] == sql_total, f"cycles total {d['total']} != SQL {sql_total}"

    @pytest.mark.anyio
    async def test_per_year_sums(self):
        """Scope-year counts, group totals and bins all reconcile exactly with the total."""
        d = (await _get("/api/dataset/cycles")).json()
        by_year = {y["year"]: y["n"] for y in d["years"]}
        assert sum(by_year[y] for y in d["scope_years"]) == d["total"]
        assert sum(g["n"] for g in d["groups"]) == d["total"]
        assert sum(d["month_totals"]) == d["total"]

    @pytest.mark.anyio
    async def test_no_future_dated_rows(self):
        """The current year's clock stops at the current month — nothing after today."""
        from datetime import date
        today = date.today()
        d = (await _get(f"/api/dataset/cycles?year={today.year}")).json()
        later = d["month_totals"][today.month:]
        assert not any(later), f"future months carry FIRs: {later}"

    @pytest.mark.anyio
    async def test_groups_have_36_bins(self):
        d = (await _get("/api/dataset/cycles")).json()
        assert len(d["groups"]) > 0
        for g in d["groups"]:
            assert len(g["bins"]) == 36, f"group {g['name']} has {len(g['bins'])} bins"
            assert g["n"] > 0

    @pytest.mark.anyio
    async def test_year_filter(self):
        all_data = (await _get("/api/dataset/cycles")).json()
        year = all_data["scope_years"][0]          # a complete year, so it sits inside All
        filtered = (await _get(f"/api/dataset/cycles?year={year}")).json()
        assert 0 < filtered["total"] <= all_data["total"]
        assert filtered["scope_years"] == [year]
