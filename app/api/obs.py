"""
Antar — Observability API (Trace & Telemetry screen)
=====================================================
Read-only views over the obs store. Every endpoint defaults to CONVERSATIONAL traces
(one user turn = one trace); pass `all_surfaces=true` to include the raw per-request
HTTP telemetry the middleware writes.

  GET /trace | /trust                    → dashboard summary + recent turns (legacy paths)
  GET /api/obs/sessions                  → one row per chat session
  GET /api/obs/session/{session_id}      → every turn in that session, in order
  GET /api/obs/trace/{trace_id}          → full drill-down for one turn
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.settings import settings

router = APIRouter()


def _check_enabled():
    if not getattr(settings, "OBS_ENABLED", False):
        raise HTTPException(status_code=404, detail="Observability is disabled (OBS_ENABLED=false)")


@router.get("/trace", response_class=JSONResponse)
@router.get("/trust", response_class=JSONResponse)
@router.get("/api/obs/dashboard", response_class=JSONResponse)
def get_trace_dashboard(
    limit: int = Query(60, ge=1, le=500),
    all_surfaces: bool = False,
    flagged_only: bool = False,
    session_id: str | None = None,
    q: str | None = None,
):
    """Summary KPIs + the most recent turns, newest first."""
    _check_enabled()
    from app.obs import store

    conversational = not all_surfaces
    return {
        "metrics": store.get_metrics_summary(conversational_only=conversational),
        "traces": store.get_recent_traces(
            limit=limit,
            conversational_only=conversational,
            flagged_only=flagged_only,
            session_id=session_id,
            q=q,
        ),
        "sessions": store.get_sessions(limit=40, conversational_only=conversational),
    }


@router.get("/api/obs/sessions", response_class=JSONResponse)
def list_sessions(limit: int = Query(60, ge=1, le=300), all_surfaces: bool = False):
    """Chat sessions, most recently active first."""
    _check_enabled()
    from app.obs import store
    sessions = store.get_sessions(limit=limit, conversational_only=not all_surfaces)
    return {"sessions": sessions, "count": len(sessions)}


@router.get("/api/obs/session/{session_id}", response_class=JSONResponse)
def get_session(session_id: str, all_surfaces: bool = False):
    """Replay one session: every question asked in it, in order, with its telemetry."""
    _check_enabled()
    from app.obs import store

    turns = store.get_session_turns(session_id, conversational_only=not all_surfaces)
    if not turns:
        raise HTTPException(status_code=404, detail=f"No traces for session {session_id}")

    flagged = sum(1 for t in turns if t["flags"])
    return {
        "session_id": session_id,
        "turns": turns,
        "summary": {
            "turns": len(turns),
            "flagged": flagged,
            "errors": sum(1 for t in turns if t.get("error")),
            "tokens": sum((t.get("tokens_in") or 0) + (t.get("tokens_out") or 0) for t in turns),
            "total_ms": sum(t.get("latency_ms") or 0 for t in turns),
            "citations": sum(t.get("n_citations") or 0 for t in turns),
            "rows_read": sum(t.get("n_rows") or 0 for t in turns),
            "first_at": turns[0]["created_at"],
            "last_at": turns[-1]["created_at"],
        },
    }


@router.get("/api/obs/trace/{trace_id}", response_class=JSONResponse)
def get_trace(trace_id: str):
    """Everything recorded about one turn — the answer, the rows behind it, the prompt
    that was sent, the agents that ran, and every flag and judge score."""
    _check_enabled()
    from app.obs import store

    detail = store.get_trace_detail(trace_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Unknown trace {trace_id}")
    return detail
