"""
Antar — Scale & Performance API (/api/scale/*) (Phase L5.3)
Exposes endpoints for querying the analytical performance benchmark across SQLite and DuckDB.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.edition import is_lab
from app.services.scale_bench import BENCHMARK_QUERIES, run_benchmark_query

router = APIRouter()


class RunRequest(BaseModel):
    query_id: str
    engine: str = "duckdb"   # "sqlite" | "duckdb"
    dataset: str = "19lakh"  # "19lakh" | "1cr"
    n_runs: int = 3


@router.get("/queries")
async def list_scale_queries() -> Dict[str, Any]:
    """List the 6 benchmark analytical queries with their descriptions and SQL texts."""
    out = {}
    for qid, qdata in BENCHMARK_QUERIES.items():
        out[qid] = {
            "name": qdata["name"],
            "description": qdata["description"],
            "sqlite_sql": qdata["sqlite"].strip(),
            "duckdb_sql": qdata["duckdb"].strip(),
        }
    return {"queries": out, "engines": ["sqlite", "duckdb"], "datasets": ["19lakh", "1cr"]}


@router.get("/benchmark")
async def get_scale_benchmark() -> Dict[str, Any]:
    """Return the structured 19L and 1-Crore benchmark results and queries for the Scale screen."""
    import json
    from pathlib import Path

    json_path = Path(__file__).resolve().parent.parent.parent / "antar-frontend" / "public" / "lab" / "scale.json"
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Construct on the fly if scale.json is absent
    queries_list = [
        {"id": qid, "name": qdata["name"], "desc": qdata["description"]}
        for qid, qdata in BENCHMARK_QUERIES.items()
    ]
    return {
        "edition": "lab",
        "has_19l_parquet": True,
        "has_stress_1cr": True,
        "queries": queries_list,
        "benchmarks": {},
        "results": [],
    }


@router.post("/run")
async def run_scale_query(req: RunRequest) -> Dict[str, Any]:
    """Execute one benchmark query and return execution time and sample rows."""
    if not is_lab():
        raise HTTPException(
            status_code=403,
            detail="Scale benchmark execution is enabled in Lab edition only (ANTAR_EDITION=lab)."
        )
    try:
        return run_benchmark_query(
            engine=req.engine.lower(),
            dataset=req.dataset.lower(),
            query_id=req.query_id.upper(),
            n_runs=req.n_runs,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
