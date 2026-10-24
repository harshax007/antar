"""Map forecasting API — /api/forecast/* (Phase 4 of docs/MAP_FORECASTING_PLAN.md).

Every route reads precomputed tables (forecast_output, geo_units, forecast_cube,
forecast_meta) through app/forecast/service.py. Unknown filters are refused with 422 and
the nearest valid values; a forecast not yet computed for the requested as-of is 503
while it is prepared in the background.
"""
from __future__ import annotations

import asyncio
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.db_path import DB_PATH, ensure_db_staged
from app.forecast import backtest as BT
from app.forecast import service as S
from app.core.db_path import registry_connect

router = APIRouter()


def _ro() -> sqlite3.Connection:
    ensure_db_staged()
    return registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)


async def _call(fn, *args, **kw) -> dict:
    def work():
        con = _ro()
        try:
            return fn(con, *args, **kw)
        finally:
            con.close()
    try:
        return await asyncio.to_thread(work)
    except S.Refusal as r:
        raise HTTPException(status_code=422, detail=r.to_dict())
    except S.NotReady as n:
        raise HTTPException(status_code=503, detail={"preparing": True, "message": str(n)})
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            raise HTTPException(status_code=503, detail={
                "preparing": True, "message": "The forecast store is being built (about a minute)."})
        raise


@router.get("/hotspots")
async def hotspots(horizon: int = 7, category: Optional[str] = None,
                   district: Optional[str] = None, station: Optional[str] = None,
                   unit: str = "beat", limit: int = Query(25, ge=1, le=500),
                   as_of: Optional[str] = None) -> dict:
    """Ranked stations or beats by expected FIRs over the next 7 or 28 days — each with
    its 80/90% range, P(at least one), the reasons, a Gi* district flag (all crime) and
    evidence class I. `as_of`: omit for the configured date, or "real" / YYYY-MM-DD."""
    out = await _call(S.hotspots, horizon=horizon, category=category, district=district,
                      station=station, unit_type=unit, limit=limit, as_of=as_of)
    _keep(out)
    return out


_kept_weeks: set = set()


def _keep(out: dict) -> None:
    """Keep this week's station forecasts the first time they are served, so they can be
    scored once the week is in (app/services/forecast_outcomes.py). Never blocks or fails
    the request."""
    try:
        basis = out.get("as_of") or {}
        if basis.get("mode") != "wallclock":
            return                           # a look back at another date is not this week's forecast
        from datetime import date, timedelta
        through = basis.get("history_through")
        week = (date.fromisoformat(through) - timedelta(days=6)).isoformat() if through else None
        if week and week not in _kept_weeks:
            _kept_weeks.add(week)
            from app.services import forecast_outcomes
            asyncio.get_running_loop().run_in_executor(None, forecast_outcomes.snapshot, week)
    except Exception:
        pass


class ForecastFeedback(BaseModel):
    kind: str = Field(pattern="^(forecast|shift_plan|lead)$")
    unit: str = Field(min_length=1, max_length=160)
    useful: bool
    reason: str = Field(default="", max_length=500)


@router.post("/feedback")
async def feedback(req: ForecastFeedback, request: Request) -> dict:
    """An officer marks a forecast, a shift plan or a lead useful or not. "Not useful" needs
    a reason: that is the part worth reading."""
    from app.core.auth_middleware import current_identity
    from app.services import forecast_outcomes
    try:
        return await asyncio.to_thread(forecast_outcomes.feedback_add, current_identity(request).officer,
                                       req.kind, req.unit, req.useful, req.reason)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/outcomes")
async def outcomes(unit: Optional[str] = None) -> dict:
    """How the forecast is doing in use: kept weeks scored against what was recorded, one
    station's last scored forecast, and what officers said."""
    from app.services import forecast_outcomes as FO

    def work():
        tr = FO.trailing()
        return {"trailing": tr, "confidence": FO.confidence_cap(tr), "unit": FO.unit_last(unit) if unit else None,
                "feedback": FO.feedback_summary(),
                "note": (None if tr["weeks"] else
                         ("This week's forecasts are kept and will be scored once the week is complete."
                          if tr["kept_weeks"] else "No forecast has been kept yet; open the forecast list once to start."))}
    return await asyncio.to_thread(work)


@router.get("/layer")
async def layer(horizon: int = 7, category: Optional[str] = None,
                district: Optional[str] = None, unit: str = "station",
                as_of: Optional[str] = None) -> dict:
    """Every unit in scope, compact, for shading the map (quantile classes 0–4)."""
    return await _call(S.layer, horizon=horizon, category=category, district=district,
                       unit_type=unit, as_of=as_of)


@router.get("/explain")
async def explain(unit: str = "station", horizon: int = 7, as_of: Optional[str] = None) -> dict:
    """How the engine behaves overall: which reasons move forecasts, per crime category,
    where it is weakest by its own back-test, and what it does not use."""
    return await _call(S.global_explanation, unit_type=unit, horizon=horizon, as_of=as_of)


@router.get("/shift-plan")
async def shift_plan(station: str = Query(min_length=2, max_length=120), as_of: Optional[str] = None) -> dict:
    """One station's next shift on a page: beats to cover first, the kinds of case expected,
    the days that run busier, what is still open there, and any event the record has
    measured. Counted and templated - no model writes any of it."""
    from app.services import shift_plan as SP
    try:
        return await _call(SP.build, station, as_of=as_of)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/unit/{name:path}")
async def unit(name: str, unit_type: Optional[str] = None, category: Optional[str] = None,
               as_of: Optional[str] = None) -> dict:
    """One station or beat ("Station PS | BEAT 3"): 26-week history, the week ahead with
    its ranges, the reasons, top crime heads, other categories, and its back-test record."""
    return await _call(S.unit_detail, name, unit_type=unit_type, category=category, as_of=as_of)


@router.get("/backtest")
async def backtest(unit: Optional[str] = None, category: Optional[str] = None) -> dict:
    """The latest rolling-origin back-test (docs/FORECAST_BACKTEST.md). Per-unit records
    are left out unless both `unit` (station|beat) and `category` are given."""
    def work(con):
        bt = BT.load(con)
        if not bt:
            raise S.NotReady("The back-test has not been run yet — python -m app.forecast.backtest.")
        res = bt["results"]
        if unit or category:
            ut = S._check_unit_type(unit or "beat")
            cat = S.resolve_category(category)
            return {**{k: v for k, v in bt.items() if k != "results"},
                    "results": {ut: {cat: res.get(ut, {}).get(cat, {})}}}
        slim = {ut: {c: {h: {k: v for k, v in m.items() if k not in ("units", "units_fields")}
                         for h, m in hs.items()} for c, hs in cs.items()}
                for ut, cs in res.items()}
        return {**{k: v for k, v in bt.items() if k != "results"}, "results": slim}
    return await _call(work)


@router.get("/scorecard")
async def scorecard(unit: str = "beat", category: Optional[str] = None) -> dict:
    """The 7-day forecast graded week by week against what was then recorded, on the
    real record: forecast vs actual, share of FIRs in the top 5% vs last-4-weeks
    hotspots, and how often the 80% ranges held."""
    return await _call(S.scorecard, unit_type=unit, category=category)


@router.get("/refit")
async def refit_state() -> dict:
    """Whether this week stands on real record or seeded rows, when the weekly job last
    ran, and what it would do now (app/forecast/refit.py)."""
    from app.forecast import refit
    return await _call(refit.state)


@router.get("/status")
async def status() -> dict:
    """The configured as-of, the forecast runs on file, and the back-test headline."""
    return await _call(S.status)
