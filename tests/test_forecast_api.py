"""Map forecasting, Phase 4 — /api/forecast/* and the fixed map endpoints.

Two layers: the service on the synthetic registry (every answer known), and the HTTP
contract on the real app (skipped until the backend has computed its forecasts).
"""
import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.forecast import asof, run, service as S
from tests.test_forecast_model import _registry

AS_OF = "2024-03-10"


@pytest.fixture(scope="module")
def reg():
    con = _registry(seed=5)
    run.compute(con, asof.resolve(con, AS_OF), cats=["ALL", "PROPERTY"])
    yield con
    con.close()


def _check_item(it):
    assert it["evidence_class"] == "I"
    assert it["band90"]["lo"] <= it["band80"]["lo"] <= it["expected"] <= it["band80"]["hi"] <= it["band90"]["hi"] \
        or it["band90"]["lo"] <= it["expected"] <= it["band90"]["hi"]
    assert it["band80"]["words"] == "likely" and it["band90"]["words"] == "very likely"
    assert 0 <= it["p_any"] <= 1
    assert it["summary"]


# ── service ──────────────────────────────────────────────────────────────────

def test_hotspots_contract(reg):
    r = S.hotspots(reg, horizon=7, category="theft", unit_type="beat", limit=10, as_of=AS_OF)
    assert r["as_of"]["as_of"] == AS_OF and r["as_of"]["real_share"] == 1.0
    assert r["category"] == "PROPERTY" and r["evidence_class"] == "I"
    exp = [i["expected"] for i in r["items"]]
    assert exp == sorted(exp, reverse=True) and [i["rank"] for i in r["items"]] == list(range(1, len(exp) + 1))
    for it in r["items"]:
        _check_item(it)
    assert r["bottom_line"].startswith(r["items"][0]["name"])
    assert r["target_weeks"] == ["2024-03-11"]


def test_28_day_forecasts_cover_four_weeks(reg):
    r = S.hotspots(reg, horizon=28, category="PROPERTY", unit_type="station", as_of=AS_OF)
    assert len(r["target_weeks"]) == 4
    week = S.hotspots(reg, horizon=7, category="PROPERTY", unit_type="station", as_of=AS_OF)
    assert r["expected_total"] > 2.5 * week["expected_total"]


def test_filters_narrow_and_never_widen(reg):
    d = S.hotspots(reg, category="PROPERTY", district="D1", unit_type="beat", limit=100, as_of=AS_OF)
    assert d["items"] and all(i["district"] == "D1" for i in d["items"])
    s = S.hotspots(reg, category="PROPERTY", station="S02 PS", unit_type="beat", limit=100, as_of=AS_OF)
    assert {i["station"] for i in s["items"]} == {"S02 PS"} and len(s["items"]) == 3


@pytest.mark.parametrize("kw,field", [
    ({"district": "Atlantis"}, "district"),
    ({"category": "jaywalking"}, "category"),
    ({"horizon": 14}, "horizon"),
    ({"unit_type": "grid"}, "unit"),
    ({"station": "Nowhere PS"}, "unit"),
])
def test_unknown_filters_are_refused(reg, kw, field):
    with pytest.raises(S.Refusal) as e:
        S.hotspots(reg, as_of=AS_OF, **kw)
    assert e.value.field == field and e.value.message


def test_refusals_offer_the_nearest_real_names(reg):
    with pytest.raises(S.Refusal) as e:
        S.resolve_district(reg, "D 1")
    assert "D1" in e.value.options


def test_a_date_with_no_forecast_is_not_ready_rather_than_guessed(reg, monkeypatch):
    monkeypatch.setattr(S, "_prepare_async", lambda override: None)
    with pytest.raises(S.NotReady):
        S.hotspots(reg, as_of="2023-06-18")


def test_unit_detail(reg):
    d = S.unit_detail(reg, "S00 PS | BEAT 0", category="PROPERTY", as_of=AS_OF)
    assert d["unit_type"] == "beat" and d["station"] == "S00 PS"
    assert len(d["history"]) == 26 and d["history"][-1]["week_start"] == "2024-03-04"
    assert sum(h["firs"] for h in d["history"]) > 0
    assert d["ahead"][0]["week_start"] == "2024-03-11"
    assert d["forecast"]["7"] and d["forecast"]["28"]
    assert d["top_crime_heads"] and d["evidence_class"] == "I"
    # a unit name alone is enough; the type follows from the " | "
    assert S.unit_detail(reg, "S00 PS", as_of=AS_OF)["unit_type"] == "station"


def test_layer_classes(reg):
    lay = S.layer(reg, category="PROPERTY", unit_type="beat", as_of=AS_OF)
    assert lay["fields"][0] == "unit" and len(lay["units"]) == 24
    classes = [u[lay["fields"].index("class")] for u in lay["units"]]
    assert min(classes) == 0 and max(classes) == 4


def test_drivers_are_words_and_multipliers(reg):
    r = S.hotspots(reg, category="PROPERTY", unit_type="beat", limit=24, as_of=AS_OF)
    seen = [d for it in r["items"] for d in it["drivers"]]
    assert seen, "no reasons shown on any beat"
    for d in seen:
        assert d["key"] in {"recent", "last_year", "neighbours", "area", "season", "level"}
        assert d["text"] and d["effect"][0] in "+−"


def test_calibrated_words():
    assert S._calibrated_chance(0.97) == "almost certain"
    assert S._calibrated_chance(0.6) == "likely"
    assert S._calibrated_chance(0.1) == "very unlikely"


# ── HTTP on the real app ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def live_ready():
    import sqlite3
    from app.core.db_path import DB_PATH
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        a = asof.resolve(con, "real")
        if not run.run_info(con, a.history_end.isoformat()):
            pytest.skip("real-record forecasts not computed yet (backend startup does it)")
    finally:
        con.close()


@pytest.mark.anyio
async def test_http_hotspots_contract_and_latency(live_ready):
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/forecast/hotspots", params={"as_of": "real", "unit": "beat",
                                                          "category": "PROPERTY", "limit": 25})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["as_of"]["as_of"] == "2024-03-10" and body["evidence_class"] == "I"
        for it in body["items"]:
            _check_item(it)
        assert body["accuracy"] is None or body["accuracy"]["top5_share_caught"] > 0
        times = []
        for params in ({"as_of": "real"}, {"as_of": "real", "district": "Mysuru City"},
                       {"as_of": "real", "unit": "station", "horizon": 28}) * 7:
            t = time.perf_counter()
            assert (await c.get("/api/forecast/hotspots", params=params)).status_code == 200
            times.append(time.perf_counter() - t)
        p95 = sorted(times)[int(0.95 * len(times)) - 1]
        assert p95 < 0.3, f"p95 {p95 * 1000:.0f} ms"


@pytest.mark.anyio
async def test_http_refusal_is_422_with_options(live_ready):
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/forecast/hotspots", params={"as_of": "real", "district": "Mysore"})
        assert r.status_code == 422
        d = r.json()["detail"]
        # "Mysore" is Mysuru — which is two police districts; both are offered, none picked
        assert d["refused"] and d["field"] == "district"
        assert {"Mysuru City", "Mysuru Dist"} <= set(d["options"])


@pytest.mark.anyio
async def test_http_unit_card(live_ready):
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        top = (await c.get("/api/forecast/hotspots", params={"as_of": "real", "limit": 1})).json()
        name = top["items"][0]["unit"]
        await c.get(f"/api/forecast/unit/{name}", params={"as_of": "real"})   # warm
        t = time.perf_counter()
        r = await c.get(f"/api/forecast/unit/{name}", params={"as_of": "real"})
        assert r.status_code == 200, r.text
        assert time.perf_counter() - t < 0.3
        d = r.json()
        assert d["unit"] == name and len(d["history"]) == 26 and d["evidence_class"] == "I"


@pytest.mark.anyio
async def test_http_predicted_is_a_forecast_not_a_fabrication():
    """A2–A4: no 'Surge detected', every hotspot carries a range and class I."""
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/map/predicted")
        assert r.status_code == 200
        body = r.json()
        assert "Surge detected" not in str(body)
        assert "contours" in body and "beat_suggestions" in body
        for h in body["predicted_hotspots"]:
            assert h["evidence_class"] == "I" and h["band90"]["lo"] <= h["expected"] <= h["band90"]["hi"]


@pytest.mark.anyio
async def test_http_status_and_backtest():
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        s = await c.get("/api/forecast/status")
        assert s.status_code == 200 and s.json()["horizons_days"] == [7, 28]
        b = await c.get("/api/forecast/backtest")
        assert b.status_code in (200, 503)
        if b.status_code == 200:
            assert not {"units", "units_fields"} & set(b.json()["results"]["beat"]["ALL"]["7"])
