"""
Antar — Scale & Performance Benchmark Service (Phase L5.3)
Compares sub-second execution speeds of SQLite vs DuckDB across 19-Lakh and 1-Crore datasets.
Implements Q1-Q6 analytic benchmark queries with cold/warm latency measurements.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb

from app.core import clock
from app.core.edition import is_lab

ROOT = Path(__file__).resolve().parent.parent.parent
SCALE_DIR = ROOT / "scale"
DB_PATH = ROOT / os.environ.get("ANTAR_DB", "main_lab.db")
FIRS_PARQUET = SCALE_DIR / "firs_lab.parquet"
STRESS_PARQUET_GLOB = str(SCALE_DIR / "firs_stress_1cr" / "part_*.parquet").replace("\\", "/")

# Six analytical queries
BENCHMARK_QUERIES = {
    "Q1": {
        "name": "District ranking",
        "description": "COUNT(*) by district, descending, top 10",
        "sqlite": "SELECT district_norm, COUNT(*) as c FROM FIRs WHERE district_norm IS NOT NULL AND district_norm != '' GROUP BY district_norm ORDER BY c DESC LIMIT 10",
        "duckdb": "SELECT district_norm, COUNT(*) as c FROM '{source}' WHERE district_norm IS NOT NULL AND district_norm != '' GROUP BY district_norm ORDER BY c DESC LIMIT 10",
    },
    "Q2": {
        "name": "Monthly trend",
        "description": "Aggregated monthly FIR volume across all years",
        "sqlite": "SELECT substr(date, 1, 7) as ym, COUNT(*) as c FROM FIRs WHERE date IS NOT NULL AND date != '' GROUP BY ym ORDER BY ym",
        "duckdb": "SELECT substr(date, 1, 7) as ym, COUNT(*) as c FROM '{source}' WHERE date IS NOT NULL AND date != '' GROUP BY ym ORDER BY ym",
    },
    "Q3": {
        "name": "Crime mix per station",
        "description": "Station volume breakdown across crime types, top 50",
        "sqlite": "SELECT station, crime_type, COUNT(*) as c FROM FIRs WHERE station IS NOT NULL AND crime_type IS NOT NULL GROUP BY station, crime_type ORDER BY c DESC LIMIT 50",
        "duckdb": "SELECT station, crime_type, COUNT(*) as c FROM '{source}' WHERE station IS NOT NULL AND crime_type IS NOT NULL GROUP BY station, crime_type ORDER BY c DESC LIMIT 50",
    },
    "Q4": {
        "name": "Pendency by district",
        "description": "Share of cases Under Investigation older than 90 days",
        "sqlite": "SELECT district_norm, CAST(SUM(CASE WHEN status LIKE '%Investigation%' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as pendency_rate FROM FIRs WHERE date <= date(:today, '-90 days') GROUP BY district_norm HAVING COUNT(*) > 50 ORDER BY pendency_rate DESC LIMIT 10",
        "duckdb": "SELECT district_norm, CAST(SUM(CASE WHEN status LIKE '%Investigation%' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as pendency_rate FROM '{source}' WHERE date <= strftime(date '{today}' - INTERVAL 90 DAY, '%Y-%m-%d') GROUP BY district_norm HAVING COUNT(*) > 50 ORDER BY pendency_rate DESC LIMIT 10",
    },
    "Q5": {
        "name": "Day of week pattern",
        "description": "Theft incidents grouped by day of week",
        "sqlite": "SELECT strftime('%w', date) as dow, COUNT(*) as c FROM FIRs WHERE UPPER(crime_type) = 'THEFT' AND date IS NOT NULL GROUP BY dow ORDER BY dow",
        "duckdb": "SELECT strftime(TRY_CAST(date AS DATE), '%w') as dow, COUNT(*) as c FROM '{source}' WHERE UPPER(crime_type) = 'THEFT' AND date IS NOT NULL GROUP BY dow ORDER BY dow",
    },
    "Q6": {
        "name": "2-Key CTE Join",
        "description": "District-year share of total annual crime (Self-join via CTE)",
        "sqlite": """
            WITH yr_totals AS (
                SELECT FIR_YEAR, COUNT(*) as total_yr FROM FIRs WHERE FIR_YEAR IS NOT NULL GROUP BY FIR_YEAR
            ),
            dist_yr AS (
                SELECT district_norm, FIR_YEAR, COUNT(*) as total_dy FROM FIRs WHERE district_norm IS NOT NULL GROUP BY district_norm, FIR_YEAR
            )
            SELECT d.district_norm, d.FIR_YEAR, d.total_dy, y.total_yr,
                   ROUND(CAST(d.total_dy AS FLOAT) / y.total_yr * 100, 2) as share_pct
            FROM dist_yr d JOIN yr_totals y ON d.FIR_YEAR = y.FIR_YEAR
            ORDER BY d.FIR_YEAR DESC, d.total_dy DESC LIMIT 20
        """,
        "duckdb": """
            WITH yr_totals AS (
                SELECT FIR_YEAR, COUNT(*) as total_yr FROM '{source}' WHERE FIR_YEAR IS NOT NULL GROUP BY FIR_YEAR
            ),
            dist_yr AS (
                SELECT district_norm, FIR_YEAR, COUNT(*) as total_dy FROM '{source}' WHERE district_norm IS NOT NULL GROUP BY district_norm, FIR_YEAR
            )
            SELECT d.district_norm, d.FIR_YEAR, d.total_dy, y.total_yr,
                   ROUND(CAST(d.total_dy AS FLOAT) / y.total_yr * 100, 2) as share_pct
            FROM dist_yr d JOIN yr_totals y ON d.FIR_YEAR = y.FIR_YEAR
            ORDER BY d.FIR_YEAR DESC, d.total_dy DESC LIMIT 20
        """,
    },
}

_duck_conn: Optional[duckdb.DuckDBPyConnection] = None


def get_duckdb_conn() -> duckdb.DuckDBPyConnection:
    global _duck_conn
    if _duck_conn is None:
        _duck_conn = duckdb.connect(":memory:")
        _duck_conn.execute("PRAGMA threads=4")
    return _duck_conn


def run_benchmark_query(
    engine: str,
    dataset: str,
    query_id: str,
    n_runs: int = 3,
) -> Dict[str, Any]:
    """Execute a benchmark query and return execution time (cold + warm median) and rows."""
    if query_id not in BENCHMARK_QUERIES:
        raise ValueError(f"Unknown query_id: {query_id}. Choices: {list(BENCHMARK_QUERIES.keys())}")

    qdef = BENCHMARK_QUERIES[query_id]
    today_iso = clock.today().isoformat()

    latencies_ms = []
    rows_out: List[Any] = []
    rows_scanned = 0

    if engine == "sqlite":
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        sql = qdef["sqlite"].replace(":today", f"'{today_iso}'")
        try:
            rows_scanned = conn.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
            for i in range(n_runs):
                t0 = time.perf_counter()
                res = conn.execute(sql).fetchall()
                latencies_ms.append(round((time.perf_counter() - t0) * 1000, 2))
                if i == 0:
                    rows_out = res
        finally:
            conn.close()

    elif engine == "duckdb":
        d_conn = get_duckdb_conn()
        if dataset in ("1cr", "stress", "stress_1cr", "1crore"):
            src = STRESS_PARQUET_GLOB
            rows_scanned = 10_000_000
        else:
            src = str(FIRS_PARQUET).replace("\\", "/")
            rows_scanned = 2_040_002

        raw_sql = qdef["duckdb"].format(source=src, today=today_iso)
        for i in range(n_runs):
            t0 = time.perf_counter()
            res = d_conn.execute(raw_sql).fetchall()
            latencies_ms.append(round((time.perf_counter() - t0) * 1000, 2))
            if i == 0:
                rows_out = res
    else:
        raise ValueError(f"Unknown engine: {engine}. Choices: sqlite, duckdb")

    cold_ms = latencies_ms[0]
    sorted_lats = sorted(latencies_ms)
    warm_median_ms = sorted_lats[len(sorted_lats) // 2]

    return {
        "query_id": query_id,
        "name": qdef["name"],
        "description": qdef["description"],
        "engine": engine,
        "dataset": dataset,
        "n_rows_scanned": rows_scanned,
        "cold_ms": cold_ms,
        "warm_median_ms": warm_median_ms,
        "all_runs_ms": latencies_ms,
        "result_count": len(rows_out),
        "sample_rows": [list(r) for r in rows_out[:5]],
    }
