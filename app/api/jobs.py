"""
Antar — Long-Task Jobs  (admin Expert Workspace)
=====================================================
Background deep-tasks an admin can launch from the Expert Workspace and watch
run, without blocking the chat. Runs on the orchestrator; status is polled.

POST /api/jobs           {type, target?}     → {job_id}
GET  /api/jobs                               → [{job_id, type, status, …}]
GET  /api/jobs/{job_id}                       → full record incl. result summary

Job types (all real work, never mocked):
  • deep_research     — run the K/D/I/U research agent on a target (suspect/zone)
  • recompile_board   — recompute the full prediction board (rolling as_of)
  • pattern_scan      — repeating-signature scan
  • network_deep      — build the association graph around a target
  • threat_assessment — patrol / checkpoint recommendations
  • osint_recon       — open-web leads (unverified by definition)
  • ml_forecast       — Poisson GLM 7-day forecast with conformal ranges
  • corridor_analysis — transit corridors
  • shift_briefing    — compile a shift brief for a station/zone
  • custom            — a free-text instruction answered through the template spine

A job that fails says so. It never reports a canned success: four of these used to
ignore the orchestrator's `ok` flag and summarise a failed run as "completed".
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core import orchestrator

router = APIRouter()

_JOBS: dict[str, dict] = {}
_MAX = 50


class JobRequest(BaseModel):
    type: str = Field(pattern="^(deep_research|recompile_board|pattern_scan|network_deep|threat_assessment|osint_recon|ml_forecast|corridor_analysis|shift_briefing|custom)$")
    target: str | None = Field(default=None, max_length=120)
    instruction: str | None = Field(default=None, max_length=1000)


def _prune() -> None:
    if len(_JOBS) <= _MAX:
        return
    for jid in sorted(_JOBS, key=lambda k: _JOBS[k]["created_at"])[: len(_JOBS) - _MAX]:
        _JOBS.pop(jid, None)


def list_jobs_sync() -> dict[str, Any]:
    """Synchronous accessor for workspace API listing."""
    jobs = sorted(_JOBS.values(), key=lambda j: j["created_at"], reverse=True)
    return {"jobs": [{k: v for k, v in j.items() if k != "_task"} for j in jobs[:50]]}


def get_job_sync(job_id: str) -> dict[str, Any] | None:
    """Synchronous single job lookup."""
    return _JOBS.get(job_id)


def get_unnotified_completed_jobs(officer_id: str = "OF-1001") -> list[dict[str, Any]]:
    """Retrieve recently completed background jobs that haven't been shown to the user yet (Option B)."""
    completed = []
    for j in _JOBS.values():
        if j.get("status") == "done" and not j.get("notified"):
            j["notified"] = True
            completed.append(j)
    return completed


async def _run_job(job_id: str) -> None:
    job = _JOBS[job_id]
    job["status"] = "running"
    job["started_at"] = int(time.time())
    try:
        jtype = job["type"]
        target = job.get("target") or "general"
        
        if jtype == "deep_research":
            async def _work():
                from app.agents.research_agent import run_research
                return await asyncio.to_thread(run_research, str(target))

            ok, res, meta = await orchestrator.run_agent("research", _work)
            if not ok:
                raise RuntimeError(meta.get("reason", "research failed"))
            job["result"] = {
                "anchor": res.get("anchor"),
                "known": len(res.get("known_facts", [])),
                "derived": len(res.get("derived_facts", [])),
                "inferred": len(res.get("inferred_hypotheses", [])),
                "gaps": len(res.get("unknown_gaps", [])),
            }
            job["summary"] = (f"Dossier for {res.get('anchor', target)}: "
                              f"{job['result']['known']} known · {job['result']['derived']} derived · "
                              f"{job['result']['inferred']} inferred · {job['result']['gaps']} gaps")
        elif jtype == "recompile_board":
            async def _work():
                from app.api.pattern_predict import compile_board
                return await asyncio.to_thread(compile_board, 0)

            ok, res, meta = await orchestrator.run_agent("products", _work, timeout_s=300)
            if not ok:
                raise RuntimeError(meta.get("reason", "recompile failed"))
            job["result"] = {"zones": res.get("zones_covered"), "count": res.get("count"),
                             "as_of": res.get("as_of")}
            job["summary"] = (f"Prediction board recompiled: {res.get('count')} cards across "
                              f"{res.get('zones_covered')} zones (as of {res.get('as_of')})")
        elif jtype == "pattern_scan":
            async def _work():
                from app.agents.pattern_agent import pattern_agent_run
                return await pattern_agent_run(f"pattern scan across {target}", {})
            ok, res, meta = await orchestrator.run_agent("pattern", _work)
            if not ok:
                raise RuntimeError(meta.get("reason", "pattern scan failed"))
            job["result"] = res
            _pats = res.get("patterns") or res.get("signatures") or []
            job["summary"] = (f"Pattern scan for {target}: {len(_pats)} signature(s) found."
                              if _pats else f"Pattern scan for {target}: no repeating signature stood out.")
        elif jtype == "network_deep":
            async def _work():
                from app.agents.network_agent import build_network
                return await asyncio.to_thread(build_network, str(target))
            ok, res, meta = await orchestrator.run_agent("network", _work)
            if not ok:
                raise RuntimeError(meta.get("reason", "network analysis failed"))
            job["result"] = res
            job["summary"] = (f"Network for {target}: {len(res.get('nodes', []))} nodes, "
                              f"{len(res.get('edges', []))} links.")
        elif jtype == "threat_assessment":
            async def _work():
                from app.agents.alert_suggest_agent import alert_suggest_agent_run
                return await alert_suggest_agent_run(f"threat assessment {target}", {})
            ok, res, meta = await orchestrator.run_agent("alert_suggest", _work)
            if not ok:
                raise RuntimeError(meta.get("reason", "threat assessment failed"))
            job["result"] = res
            _sugg = res.get("suggestions") or res.get("alerts") or []
            job["summary"] = (f"Threat assessment for {target}: {len(_sugg)} recommendation(s)."
                              if _sugg else f"Threat assessment for {target}: nothing met the alert threshold.")
        elif jtype == "osint_recon":
            async def _work():
                from app.agents.osint_agent import osint_agent_run
                return await osint_agent_run(f"deep osint recon on {target}", {})
            ok, res, meta = await orchestrator.run_agent("osint", _work)
            if not ok:
                raise RuntimeError(meta.get("reason", "OSINT recon failed"))
            job["result"] = res
            _claims = res.get("claims") or res.get("leads") or []
            job["summary"] = (f"OSINT recon on {target}: {len(_claims)} unverified open-web claim(s) — "
                              f"treat as leads, not evidence."
                              if _claims else f"OSINT recon on {target}: no open-web claims found.")
        elif jtype == "ml_forecast":
            # The measured forecast: Poisson GLM with conformal ranges (app/forecast).
            # District is optional — without one it ranks the whole state.
            async def _work():
                import sqlite3
                from app.core.db_path import DB_PATH, ensure_db_staged
                from app.forecast import service as _S, asof as _asof
                def _run():
                    ensure_db_staged()
                    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
                    try:
                        district = None if str(target).lower() in ("general", "", "none") else str(target)
                        return _S.hotspots(con, horizon=7, category=None, district=district,
                                           unit_type="station", limit=10,
                                           as_of=_asof.current().as_of)
                    finally:
                        con.close()
                return await asyncio.to_thread(_run)

            ok, res, meta = await orchestrator.run_agent("forecast", _work, timeout_s=300.0)
            if not ok:
                raise RuntimeError(meta.get("reason", "forecast failed"))
            job["result"] = res
            _items = (res or {}).get("items") or []
            _top = _items[0] if _items else None
            job["summary"] = (
                f"7-day forecast ({len(_items)} units ranked): {_top.get('name', 'top unit')} highest at "
                f"{_top.get('expected', '?')} expected FIRs. Inferred — a range, not a certainty."
                if _top else "Forecast ran but ranked no units for this scope.")
        elif jtype == "corridor_analysis":
            async def _work():
                from app.agents.corridor_agent import get_all_corridors
                return await asyncio.to_thread(get_all_corridors)
            ok, res, meta = await orchestrator.run_agent("corridors", _work)
            if not ok:
                raise RuntimeError(meta.get("reason", "corridor analysis failed"))
            job["result"] = res if isinstance(res, dict) else {"corridors": res}
            job["summary"] = f"Corridor analysis completed for transit paths across {target}."
        elif jtype == "shift_briefing":
            async def _work():
                from app.agents.briefing_agent import get_shift_briefing
                return await asyncio.to_thread(get_shift_briefing, zone=str(target))
            ok, res, meta = await orchestrator.run_agent("briefing", _work)
            if not ok:
                raise RuntimeError(meta.get("reason", "shift briefing failed"))
            job["result"] = res
            job["summary"] = f"Shift briefing generated for station/zone {target}."
        elif jtype == "custom":
            async def _work():
                from app.agents.query_agent import query_agent_run
                return await query_agent_run(f"Execute custom job. Target: {target}. Instruction: {job.get('instruction', '')}")
            ok, res, meta = await orchestrator.run_agent("custom", _work, timeout_s=300.0)
            if not ok:
                raise RuntimeError(meta.get("reason", "custom job failed"))
            job["result"] = res
            job["summary"] = f"Custom job completed: {job.get('instruction', 'no instruction')[:40]}..."
        else:
            job["result"] = {"error": "unknown job type"}
            job["summary"] = "Unknown job type"
        
        job["status"] = "done"
    except Exception as exc:
        job["status"] = "failed"
        from app.core.security import public_message
        job["summary"] = public_message(exc, "job")
        if isinstance(exc, asyncio.CancelledError):
            job["status"] = "cancelled"
            job["summary"] = "Cancelled by user."
    job["finished_at"] = int(time.time())


@router.post("")
@router.post("/")
async def create_job(req: JobRequest) -> dict:
    job_id = f"job-{uuid.uuid4().hex[:10]}"
    _JOBS[job_id] = {
        "job_id": job_id, "type": req.type, "target": req.target,
        "instruction": req.instruction,
        "status": "queued", "summary": None, "result": None,
        "created_at": int(time.time()), "started_at": None, "finished_at": None,
        "notified": False
    }
    _prune()
    task = asyncio.create_task(_run_job(job_id))
    _JOBS[job_id]["_task"] = task
    return {"job_id": job_id, "status": "queued", "type": req.type}


@router.get("")
@router.get("/")
async def list_jobs() -> dict:
    jobs = sorted(_JOBS.values(), key=lambda j: j["created_at"], reverse=True)
    return {"jobs": [{k: v for k, v in j.items() if k != "_task"} for j in jobs[:30]]}


@router.get("/{job_id}")
async def get_job(job_id: str) -> dict:
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"no job {job_id}")
    # Don't serialize the asyncio task
    return {k: v for k, v in job.items() if k != "_task"}


@router.delete("/{job_id}")
async def cancel_job(job_id: str) -> dict:
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"no job {job_id}")
    
    if job["status"] not in ["done", "failed", "cancelled"]:
        job["status"] = "cancelled"
        job["summary"] = "Cancelled by user."
        job["finished_at"] = int(time.time())
        if "_task" in job and not job["_task"].done():
            job["_task"].cancel()
    
    return {"status": "cancelled"}
