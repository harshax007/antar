"""
Antar — Relational SQL Miner  (self-healing RAG · WI-3)
==========================================================
A safe, dynamic query builder over the `crimes` view for when the fixed ZCQL templates
come back empty. Unlike a template, it can combine crime_type + zone + STATUS + date and
then PROGRESSIVELY RELAX those constraints until it finds rows — the deterministic core of
the self-heal loop.

Safety: every column is drawn from a fixed whitelist (CRIME_COLUMNS / CRIME_TEXT_COLUMNS);
every value is bound as a positional parameter. No user string is ever concatenated into
SQL. Read-only. Mirrors the executor's TRIM(UPPER(col)) matching so the messy real values
(' CYBER CRIME', 'under_investigation' vs 'Under Investigation') compare reliably.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from app.core.db_path import DB_PATH
from app.services.zcql_local import _dict_factory
from app.services.zcql_repo import resolve_period
from app.agents.system_catalog import resolve_zones_catalog, normalize_statuses
from app.core.db_path import registry_connect

# Relaxation ladder — drop the most specific constraint first so the officer's primary
# intent (the crime type / keywords) survives longest.
RELAX_STEPS = ["status", "date", "zone", "crime_type"]  # index i dropped at relax_level i+1


def _period_range(intent) -> tuple[Optional[str], Optional[str]]:
    if getattr(intent, "period", None):
        return resolve_period(intent.period)
    return (None, None)


def build_sql(intent, relax_level: int = 0, limit: int = 25) -> tuple[str, list]:
    """Build (sql, params) for the given relaxation level. Level 0 = all constraints;
    each higher level drops one more constraint per RELAX_STEPS, then falls back to a
    keyword-fragment LIKE match across the text columns."""
    drop = set(RELAX_STEPS[:relax_level])

    where: list[str] = []
    params: list = []
    joins = ""

    # Suspect linkage (never relaxed — it's the whole question when present).
    sid = getattr(intent, "suspect_id", None)
    if sid:
        joins = " JOIN crime_suspects cs ON c.crime_id = cs.crime_id"
        where.append("cs.suspect_id = ?")
        params.append(sid)

    if "crime_type" not in drop and getattr(intent, "crime_types", None):
        cts = [str(x).strip().upper() for x in intent.crime_types]
        where.append(f"TRIM(UPPER(c.crime_type)) IN ({','.join('?' * len(cts))})")
        params.extend(cts)

    if "zone" not in drop and getattr(intent, "zones", None):
        zs = [str(x).strip().upper() for x in resolve_zones_catalog(intent.zones)]
        if zs:
            where.append(f"TRIM(UPPER(c.zone)) IN ({','.join('?' * len(zs))})")
            params.extend(zs)

    if "status" not in drop and getattr(intent, "statuses", None):
        st = [str(x).strip().upper() for x in normalize_statuses(intent.statuses)]
        if st:
            where.append(f"TRIM(UPPER(c.status)) IN ({','.join('?' * len(st))})")
            params.extend(st)

    if "date" not in drop:
        df, dt = _period_range(intent)
        if df and dt:
            where.append("c.occurred_at BETWEEN ? AND ?")
            params.extend([df, dt + " 23:59"])

    # NB: keyword-fragment recall is handled by the in-memory BM25 hybrid index (Sc C),
    # NOT here — a SQL LIKE across text columns is a full-table scan and far too slow.

    sql = ("SELECT c.crime_id, c.fir_number, c.crime_type, c.act, c.acts_sections, "
           "c.zone, c.district, c.station_code, c.occurred_at, c.status, c.io_name "
           f"FROM crimes c{joins}")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY c.occurred_at DESC LIMIT {int(limit)}"
    return sql, params


def mine(intent, relax_level: int = 0, limit: int = 25) -> list[dict]:
    """Execute one relaxation level. Read-only; returns [] on any error.
    Never dumps arbitrary rows: if no constraint survived (empty WHERE), returns []."""
    sql, params = build_sql(intent, relax_level, limit)
    if " WHERE " not in sql:
        return []
    try:
        conn = registry_connect(DB_PATH)
        conn.row_factory = _dict_factory
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows
    except Exception as e:  # pragma: no cover - defensive
        print(f"sql_miner error: {e}")
        return []


def mine_until_hit(intent, limit: int = 25) -> tuple[list[dict], int, list[dict]]:
    """Try structured relaxation levels 0..N until rows are found.
    Returns (rows, relax_level_used, trace) where trace is a list of self_heal steps."""
    trace: list[dict] = []
    max_level = len(RELAX_STEPS)   # 0..N: drop status -> date -> zone -> crime_type
    for lvl in range(0, max_level + 1):
        rows = mine(intent, lvl, limit)
        dropped = ", ".join(RELAX_STEPS[:lvl]) or "none"
        trace.append({"step": "self_heal",
                      "detail": f"SQL miner (relax={lvl}, dropped: {dropped}) -> {len(rows)} row(s)"})
        if rows:
            return rows, lvl, trace
    return [], max_level, trace
