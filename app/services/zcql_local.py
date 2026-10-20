"""
Antar - Local ZCQL Executor (SQLite Backed)
================================================
Replaces the old in-memory JSON simulator with a robust SQLite backend.
This provides millisecond query latencies over millions of rows and
bridges the gap perfectly to Catalyst ZCQL.
"""

import os
import sqlite3
from app.services.zcql_repo import QuerySpec, render_zcql

USE_LOCAL = os.getenv("USE_LOCAL", "1") not in ("0", "false", "False")
from app.core.db_path import DB_PATH, ensure_db_staged

# The `crimes` view every template queries. It used to exist only inside the shipped
# database, defined nowhere in code, so it could not be changed or reviewed. The code now
# owns it. `accused` / `arrested` back the "absconding" predicate (zcql_repo
# NAMED_PREDICATES); the counts are stored as a mix of INTEGER and TEXT, hence the CASTs.
CRIMES_VIEW_SQL = """CREATE VIEW crimes AS SELECT
  fir_id AS crime_id, COALESCE(CrimeNo, fir_id) AS fir_number, crime_type,
  ActSection AS act, ActSection AS acts_sections, CrimeHead_Name AS sub_head, zone, district_norm AS district,
  station AS station_code, date AS occurred_at, status, IOName AS io_name,
  geo_lat AS lat, geo_lon AS lon, is_synthetic_row,
  CAST(Accused_Count AS INTEGER) AS accused, CAST(Arrested_Count_No_ AS INTEGER) AS arrested
  FROM FIRs"""


def _ensure_crimes_view(conn) -> None:
    kind = conn.execute("SELECT type FROM sqlite_master WHERE name = 'crimes'").fetchone()
    if kind and kind[0] != "view":
        return                                  # a real table (older fixtures) — leave it
    # lat / lon come from the geo_* generated columns (app/forecast/store.py), which drop
    # the ~9k impossible coordinates. They must exist before the view can read them.
    from app.forecast.store import ensure_geo_columns
    ensure_geo_columns(conn)
    view_sql = CRIMES_VIEW_SQL
    if "geo_lat" not in {r[1] for r in conn.execute("PRAGMA table_xinfo(FIRs)")}:
        view_sql = view_sql.replace("geo_lat AS lat, geo_lon AS lon", "lat_r AS lat, lon_r AS lon")
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'crimes'").fetchone()
    if sql and sql[0] == view_sql:
        return
    conn.execute("DROP VIEW IF EXISTS crimes")
    conn.execute(view_sql)


_indexes_checked = False
def ensure_indexes():
    global _indexes_checked
    # On Catalyst the database is expanded from main.db.gz on first use. Block here rather
    # than at import so the container can bind its port immediately; a request that beats
    # the warmup waits for the staging instead of failing on a missing file.
    ensure_db_staged()
    if _indexes_checked or not os.path.exists(DB_PATH):
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        _ensure_crimes_view(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_group_date ON FIRs(CrimeGroup_Name, date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_district ON FIRs(District_Name)")
        # The `crimes` view exposes crime_type / zone / district_norm — SEPARATE columns from
        # CrimeGroup_Name / District_Name, so the two indexes above never covered the queries
        # the templates actually run. At 1M rows that was a full scan per question.
        # Composite + covering, ordered filter-first then group-by column.
        # ── Analytics indexes ────────────────────────────────────────────────
        # Two things made every aggregate question scan all 1M rows:
        #   1. render_zcql filters on `TRIM(UPPER(col))`, and a column wrapped in a
        #      function cannot use an ordinary index. Hence the EXPRESSION indexes below,
        #      which match that expression exactly.
        #   2. A filter index alone still leaves a temp B-tree for the GROUP BY, so each
        #      pairs the filter column with the column it is normally grouped by —
        #      making the index covering and the grouping index-ordered.
        # Measured on 1M FIRs: ranking 798→94 ms, crime mix 3210→117 ms, status 1434→61 ms.
        for col in ("zone", "crime_type", "status", "district_norm", "station"):
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_firs_u_{col} "
                         f"ON FIRs(TRIM(UPPER({col})), date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_u_ct_zone "
                     "ON FIRs(TRIM(UPPER(crime_type)), zone, date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_u_zone_ct "
                     "ON FIRs(TRIM(UPPER(zone)), crime_type, date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_u_zone_status "
                     "ON FIRs(TRIM(UPPER(zone)), status, date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_u_zone_beat "
                     "ON FIRs(TRIM(UPPER(zone)), Beat_Name, UnitName, date)")
        # Plain indexes for the unfiltered GROUP BYs, which read the raw column.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_status ON FIRs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_act_date ON FIRs(ActSection, date)")
        # UPPER(ActSection) serves the IPC/BNS prefix ranges render_zcql now emits for
        # `act LIKE 'IPC%'`; `date` makes it covering under the bound-to-today filter.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_u_act_date "
                     "ON FIRs(UPPER(ActSection), date)")
        # T22 rebuilds one row per FIR before aggregating (≈2.9k fir_ids repeat with
        # different stages, and summing the raw rows double-counted their accused).
        # Covering that subquery keeps it off the table entirely.
        # The Data Overview search box takes an ACC-id; api/dataset.py turns it into a
        # range on this column.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_accused ON FIRs(Accused_ID)")
        # Crime graph (api/dataset.py cycles): year range on date, bins from date, group
        # from crime_type — all served from this one covering index.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_date_ct ON FIRs(date, crime_type)")
        # Absconding (NAMED_PREDICATES): the predicate reads accused, arrested and status on
        # every row in range. Covering them keeps the count off the table — 6,815 → 434 ms.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_firs_abs_cov ON FIRs("
                     "date, status, Accused_Count, Arrested_Count_No_, zone, crime_type)")
        conn.execute("""CREATE INDEX IF NOT EXISTS idx_firs_outcomes ON FIRs(
            fir_id, date, district_norm, crime_type, FIR_Stage,
            Accused_Count, Arrested_Count_No_, Accused_ChargeSheeted_Count,
            Conviction_Count)""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_crime_suspects_sid ON crime_suspects(suspect_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_a ON relationships(suspect_a)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_b ON relationships(suspect_b)")
        conn.commit()
        conn.close()
        _indexes_checked = True
    except Exception:
        pass

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        name = col[0]
        val = row[idx]
        if name in {"prior_count", "age", "severity", "value_inr", "n", "crime_count", "txn_count", "strength"}:
            if val is not None:
                try:
                    if "." in str(val):
                        val = float(val)
                    else:
                        val = int(val)
                except ValueError:
                    pass
        d[name] = val
    return d

def _virtual_table(spec: QuerySpec) -> list[dict]:
    # __suspect_crimes__ logic
    if spec.table == "__suspect_crimes__":
        sid = next(f.value for f in spec.filters if f.column == "suspect_id")
        sql = "SELECT c.* FROM crimes c JOIN crime_suspects cs ON c.crime_id = cs.crime_id WHERE cs.suspect_id = ?"
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = _dict_factory
        rows = conn.execute(sql, (sid,)).fetchall()
        conn.close()
        return rows
        
    if spec.table == "__top_suspects_by_zone__":
        zones = None
        for f in spec.filters:
            if f.column == "zone" and f.op == "in":
                zones = tuple(f.value)
        
        sql = """
            SELECT s.suspect_id, s.full_name, s.alias as alias, s.address_zone, COUNT(cs.crime_id) as crime_count
            FROM suspects s
            JOIN crime_suspects cs ON s.suspect_id = cs.suspect_id
            JOIN crimes c ON c.crime_id = cs.crime_id
        """
        params = []
        if zones:
            placeholders = ",".join(["?"] * len(zones))
            sql += f" WHERE c.zone IN ({placeholders})"
            params.extend(zones)
        sql += " GROUP BY s.suspect_id ORDER BY crime_count DESC LIMIT 10"
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = _dict_factory
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows
    if spec.table == "__shared_identifiers__":
        return _cached_virtual(spec, _shared_identifiers)
    if spec.table == "__case_outcomes__":
        return _cached_virtual(spec, _case_outcomes)
    if spec.table == "__case_stages__":
        return _cached_virtual(spec, _case_stages)
    if spec.table == "__time_pattern__":
        return _cached_virtual(spec, _time_pattern)
    if spec.table == "__fir_link__":
        return _fir_link(spec)
    if spec.table == "__event_effect__":
        return _cached_virtual(spec, _event_effect)
    return []


# ── Virtual tables for T19 / T22 ──────────────────────────────────────────────
# Parameterised SQL only: user values travel as ? parameters; the only names spliced
# into SQL are column names taken from zcql_repo.IDENTIFIER_COLUMNS (a fixed whitelist).
_VIRTUAL_CACHE: dict = {}


def _fval(spec: QuerySpec, column: str, op: str | None = None, default=None):
    for f in spec.filters:
        if f.column == column and (op is None or f.op == op):
            return f.value
    return default


def _cached_virtual(spec: QuerySpec, fn):
    key = (spec.table, tuple((f.column, f.op, repr(f.value)) for f in spec.filters),
           spec.limit, spec.order_by)
    hit = _VIRTUAL_CACHE.get(key)
    if hit is not None:
        return [dict(r) for r in hit]
    rows = fn(spec)
    if len(_VIRTUAL_CACHE) >= 128:
        _VIRTUAL_CACHE.pop(next(iter(_VIRTUAL_CACHE)))
    _VIRTUAL_CACHE[key] = [dict(r) for r in rows]
    return rows


def _today_cap() -> str:
    from datetime import date
    return date.today().isoformat() + " 23:59"


def _in_clause(col_sql: str, values) -> tuple[str | None, list]:
    vals = [str(v).strip().upper() for v in (values or []) if str(v).strip()]
    if not vals:
        return None, []
    return f"UPPER(TRIM({col_sql})) IN ({', '.join('?' * len(vals))})", vals


def _shared_identifiers(spec: QuerySpec) -> list[dict]:
    """T19: per identifier type, every value seen in FIRs from min_districts+ districts,
    most widespread first. Each row carries type_total = how many values qualified."""
    from app.services.zcql_repo import IDENTIFIER_COLUMNS
    kt = _fval(spec, "key_type", default="any")
    min_d = int(_fval(spec, "min_districts", default=2) or 2)
    zones = _fval(spec, "zone", "in") or []
    cts = _fval(spec, "crime_type", "in") or []
    limit = int(spec.limit or 10)
    types = list(IDENTIFIER_COLUMNS) if kt == "any" else [kt]
    out: list[dict] = []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    try:
        for t in types:
            col = IDENTIFIER_COLUMNS[t]
            # "+date": without the unary plus SQLite drove this through the date index — a
            # million row lookups for the ~1k rows that carry an identifier (6 s per type).
            where = [f"{col} IS NOT NULL", f"TRIM({col}) <> ''", "+date <= ?"]
            args: list = [_today_cap()]
            c_sql, c_args = _in_clause("crime_type", cts)
            if c_sql:
                where.append(c_sql)
                args += c_args
            if zones:
                z_sql, z_args = _in_clause("zone", zones)
                where.append(f"TRIM({col}) IN (SELECT TRIM({col}) FROM FIRs WHERE {z_sql} AND {col} IS NOT NULL)")
                args += z_args
            # "between A and B": the value must turn up on FIRs in each place named. Read the
            # (value, place) pairs once and intersect here; an IN-subquery per side took 37 s.
            sides = _fval(spec, "between") or ()
            if sides:
                pairs = conn.execute(f"SELECT DISTINCT TRIM({col}), UPPER(TRIM(zone)) FROM FIRs "
                                     f"WHERE {col} IS NOT NULL AND TRIM({col}) <> ''").fetchall()
                seen: dict[str, set] = {}
                for r in pairs:
                    v, z = list(r.values()) if isinstance(r, dict) else r
                    seen.setdefault(v, set()).add(z)
                want = [{str(x).strip().upper() for x in side} for side in sides]
                keep = [v for v, zs in seen.items() if all(zs & w for w in want)][:900]
                if not keep:
                    continue
                where.append(f"TRIM({col}) IN ({', '.join('?' * len(keep))})")
                args += keep
            sql = (f"SELECT ? AS key_type, TRIM({col}) AS key_value, "
                   f"COUNT(DISTINCT fir_id) AS firs, COUNT(DISTINCT district_norm) AS districts, "
                   f"GROUP_CONCAT(DISTINCT district_norm) AS district_list, "
                   f"MIN(date) AS first_date, MAX(date) AS last_date "
                   f"FROM FIRs WHERE {' AND '.join(where)} "
                   f"GROUP BY TRIM({col}) HAVING COUNT(DISTINCT district_norm) >= ? "
                   f"ORDER BY districts DESC, firs DESC, last_date DESC")
            rows = conn.execute(sql, [t] + args + [min_d]).fetchall()
            for r in rows[:limit]:
                r["type_total"] = len(rows)
                out.append(r)
    finally:
        conn.close()
    return out


# FIR_Stage holds ~18 raw spellings; these are the outcome buckets they map to.
_STAGE_BUCKETS = {
    "under_investigation": ("under investigation", "transferred - under investigation"),
    "pending_trial": ("pending trial", "chargesheeted", "charge sheeted"),
    "convicted": ("convicted",),
    "disposed": ("dis/acq", "disposed", "other disposal", "compounded", "abated", "boundover", "closed"),
    "undetected": ("undetected", "un traced"),
    "traced": ("traced",),
    "false_case": ("false case",),
}


# What each grouping reads, per FIR. The act is the text before " U/s" in ActSection
# ("IPC 1860 U/s: 379" → "IPC 1860"); the section adds the first section number after it
# ("IPC 1860 s.379"). A multi-act entry ("IT ACT … && IT ACT …") is filed under its first.
_ACT_RAW = "UPPER(REPLACE(TRIM(ActSection), '  ', ' '))"
_ACT_EXPR = (f"TRIM(CASE WHEN INSTR({_ACT_RAW}, ' U/S') > 0 "
             f"THEN SUBSTR({_ACT_RAW}, 1, INSTR({_ACT_RAW}, ' U/S') - 1) ELSE {_ACT_RAW} END)")
_SEC_REST = f"TRIM(SUBSTR({_ACT_RAW}, INSTR({_ACT_RAW}, 'U/S:') + 4))"
_SEC_FIRST = (f"TRIM(SUBSTR({_SEC_REST}, 1, CASE WHEN INSTR({_SEC_REST}, ',') > 0 "
              f"THEN INSTR({_SEC_REST}, ',') - 1 ELSE LENGTH({_SEC_REST}) END))")
_SEC_EXPR = (f"CASE WHEN INSTR({_ACT_RAW}, 'U/S:') > 0 THEN {_ACT_EXPR} || ' s.' || "
             f"TRIM(SUBSTR({_SEC_FIRST}, 1, CASE WHEN INSTR({_SEC_FIRST}, ' ') > 0 "
             f"THEN INSTR({_SEC_FIRST}, ' ') - 1 ELSE LENGTH({_SEC_FIRST}) END)) ELSE {_ACT_EXPR} END")
_GROUP_EXPR = {
    "district": "MIN(district_norm)", "crime_type": "MIN(UPPER(TRIM(crime_type)))",
    "station": "MIN(station)", "year": "MIN(SUBSTR(date, 1, 4))",
    "act": f"MIN({_ACT_EXPR})", "section": f"MIN({_SEC_EXPR})",
}


def _fir_where(spec: QuerySpec) -> tuple[list[str], list]:
    """The WHERE clause every per-FIR virtual table shares: zone, crime type, station,
    sub-heading, years and a date range — all as ? parameters."""
    where, args = ["date <= ?"], [_today_cap()]
    for col, vals in (("zone", _fval(spec, "zone", "in")), ("crime_type", _fval(spec, "crime_type", "in")),
                      ("station", _fval(spec, "station", "in")), ("CrimeHead_Name", _fval(spec, "sub_head", "in"))):
        c_sql, c_args = _in_clause(col, vals)
        if c_sql:
            where.append(c_sql)
            args += c_args
    ho = _fval(spec, "sub_head", "head_or")
    if ho:
        heads, labels, _tc = ho
        h_sql, h_args = _in_clause("CrimeHead_Name", heads)
        l_sql, l_args = _in_clause("crime_type", labels)
        parts = [x for x in (h_sql, l_sql) if x]
        if parts:
            where.append("(" + " OR ".join(parts) + ")")
            args += h_args + l_args
    years = _fval(spec, "year", "in")
    if years:
        where.append(f"SUBSTR(date, 1, 4) IN ({', '.join('?' * len(years))})")
        args += [str(y) for y in years]
    between = _fval(spec, "date", "between")
    if between:
        where.append("date BETWEEN ? AND ?")
        args += [between[0], between[1]]
    return where, args


def _act_of(raw: str | None, section: bool) -> str:
    """'IPC 1860 U/s: 379,34 ' → 'IPC 1860' (act) or 'IPC 1860 s.379' (section). A multi-act
    entry ('A U/s: x && B U/s: y') is filed under its first act."""
    t = " ".join(str(raw or "").upper().split())
    if not t:
        return "NOT RECORDED"
    first = t.split("&&")[0].strip()
    i = first.find(" U/S")
    act = (first[:i] if i > 0 else first).strip(" ,") or "NOT RECORDED"
    if not section or "U/S:" not in first:
        return act
    sec = first.split("U/S:", 1)[1].strip()
    sec = sec.split(",")[0].strip().split(" ")[0].strip()
    return f"{act} s.{sec}" if sec else act


def _case_outcomes(spec: QuerySpec) -> list[dict]:
    """T22 / T27 / T28: FIR stage buckets plus accused-level arrest / charge-sheet / conviction
    totals and rates — overall, or by district, crime type, station, year, act or section."""
    dim = _fval(spec, "dimension", default="none")
    fold = dim in ("act", "section")
    # Act and section are folded from the raw ActSection text in Python: ~144k distinct
    # values, where string surgery in SQL on a million rows took 38 s.
    grp_expr = "MIN(ActSection)" if fold else _GROUP_EXPR.get(dim, "'ALL'")
    bucket_sql, bucket_args = [], []
    for name, values in _STAGE_BUCKETS.items():
        bucket_sql.append(f"SUM(CASE WHEN st IN ({', '.join('?' * len(values))}) THEN 1 ELSE 0 END) AS {name}")
        bucket_args += list(values)
    where, args = _fir_where(spec)
    # One row per FIR first: ~2k fir_ids repeat with different stages / counts, and summing the
    # raw rows put those FIRs in two stage buckets and double-counted their accused.
    # CAST because ~5.7k rows store the counts as text.
    num = lambda c: f"MAX(CAST(COALESCE({c}, 0) AS INTEGER))"
    per_fir = (f"SELECT fir_id, {grp_expr} AS g, "
               f"MAX(LOWER(REPLACE(TRIM(FIR_Stage), '_', ' '))) AS st, "
               f"{num('Accused_Count')} AS acc, {num('Arrested_Count_No_')} AS arr, "
               f"{num('Accused_ChargeSheeted_Count')} AS chs, {num('Conviction_Count')} AS conv "
               f"FROM FIRs WHERE {' AND '.join(where)} GROUP BY fir_id")
    sql = (f"SELECT g AS grp, COUNT(*) AS firs, {', '.join(bucket_sql)}, "
           f"SUM(acc) AS accused, SUM(arr) AS arrested, SUM(chs) AS chargesheeted, SUM(conv) AS convicted_accused "
           f"FROM ({per_fir}) GROUP BY g ORDER BY firs DESC")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    try:
        rows = conn.execute(sql, bucket_args + args).fetchall()
    finally:
        conn.close()
    if fold:
        merged: dict[str, dict] = {}
        for r in rows:
            key = _act_of(r.get("grp"), dim == "section")
            m = merged.setdefault(key, {"grp": key})
            for k, v in r.items():
                if k != "grp" and isinstance(v, (int, float)):
                    m[k] = (m.get(k) or 0) + v
        rows = sorted(merged.values(), key=lambda r: -(r.get("firs") or 0))
    for r in rows:
        acc, cs = r.get("accused") or 0, r.get("chargesheeted") or 0
        cv, ar, firs = r.get("convicted_accused") or 0, r.get("arrested") or 0, r.get("firs") or 0
        r["arrest_rate"] = round(100 * min(ar, acc) / acc, 1) if acc else None
        r["chargesheet_rate"] = round(100 * min(cs, acc) / acc, 1) if acc else None
        r["conviction_rate"] = round(100 * min(cv, cs) / cs, 1) if cs else None
        r["undetected_share"] = round(100 * (r.get("undetected") or 0) / firs, 1) if firs else None
    return [r for r in rows if r.get("grp") is not None]


_OPEN_INV = ("under investigation", "transferred - under investigation")


def _case_stages(spec: QuerySpec) -> list[dict]:
    """T24: per station / district / crime type (or overall), how many FIRs sit at each stage
    and how long the open investigations have been open (days since registration)."""
    from app.services.zcql_repo import data_today
    dim = _fval(spec, "dimension", default="none")
    grp_expr = {"station": "MIN(station)", "district": "MIN(district_norm)",
                "crime_type": "MIN(UPPER(TRIM(crime_type)))"}.get(dim, "'ALL'")
    older = int(_fval(spec, "older_than_days", default=0) or 0)
    today = data_today().isoformat()
    where, args = _fir_where(spec)
    bucket_sql, bucket_args = [], []
    for name, values in _STAGE_BUCKETS.items():
        bucket_sql.append(f"SUM(CASE WHEN st IN ({', '.join('?' * len(values))}) THEN 1 ELSE 0 END) AS {name}")
        bucket_args += list(values)
    ui = ", ".join("?" * len(_OPEN_INV))
    per_fir = (f"SELECT fir_id, {grp_expr} AS g, MIN(district_norm) AS dist, MIN(date) AS dt, "
               f"MAX(LOWER(REPLACE(TRIM(FIR_Stage), '_', ' '))) AS st "
               f"FROM FIRs WHERE {' AND '.join(where)} GROUP BY fir_id")
    age = "(julianday(?) - julianday(SUBSTR(dt, 1, 10)))"
    sql = (f"SELECT g AS grp, MIN(dist) AS district, COUNT(*) AS firs, {', '.join(bucket_sql)}, "
           f"SUM(CASE WHEN st IN ({ui}) AND {age} > 90 THEN 1 ELSE 0 END) AS ui_over_90, "
           f"SUM(CASE WHEN st IN ({ui}) AND {age} > 365 THEN 1 ELSE 0 END) AS ui_over_365, "
           f"SUM(CASE WHEN st IN ({ui}) AND {age} > ? THEN 1 ELSE 0 END) AS ui_older, "
           f"MIN(CASE WHEN st IN ({ui}) THEN SUBSTR(dt, 1, 10) END) AS oldest_open "
           f"FROM ({per_fir}) GROUP BY g")
    q_args = (bucket_args + list(_OPEN_INV) + [today] + list(_OPEN_INV) + [today]
              + list(_OPEN_INV) + [today, older] + list(_OPEN_INV) + args)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    try:
        rows = conn.execute(sql, q_args).fetchall()
    finally:
        conn.close()
    key = "ui_older" if older else "under_investigation"
    asc = bool(spec.order_by and spec.order_by[1] == "asc")
    rows = [r for r in rows if r.get("grp") is not None]
    rows.sort(key=lambda r: (r.get(key) or 0), reverse=not asc)
    for r in rows:
        r["older_than_days"] = older
    return rows


_WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


def _time_pattern(spec: QuerySpec) -> list[dict]:
    """T26: FIRs per day of the week (0 = Sunday) or per calendar month, with the number of
    such days/months in the span, so a count can be read as a per-day average."""
    dim = _fval(spec, "dimension", default="weekday")
    where, args = _fir_where(spec)
    fmt = {"weekday": "%w", "month": "%m", "monthday": "%d"}.get(dim, "%w")
    sql = (f"SELECT strftime('{fmt}', SUBSTR(date, 1, 10)) AS k, COUNT(DISTINCT fir_id) AS n, "
           f"COUNT(DISTINCT SUBSTR(date, 1, 10)) AS days, MIN(SUBSTR(date, 1, 10)) AS first_date, "
           f"MAX(SUBSTR(date, 1, 10)) AS last_date "
           f"FROM FIRs WHERE {' AND '.join(where)} AND date IS NOT NULL GROUP BY k ORDER BY k")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    try:
        rows = conn.execute(sql, args).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        if r.get("k") is None:
            continue
        i = int(r["k"])
        if dim == "monthday":
            label = str(i)
        else:
            label = _WEEKDAYS[i] if dim == "weekday" else ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                                                             "Aug", "Sep", "Oct", "Nov", "Dec")[i - 1]
        out.append({"slot": label, "slot_index": i, "n": int(r.get("n") or 0), "days": int(r.get("days") or 0),
                    "first_date": r.get("first_date"), "last_date": r.get("last_date"), "dimension": dim})
    return out


# T29: the keys two FIRs share. Each key is a column the FIR records; a shared value is
# named with the column it came from, so the answer says WHAT links the two cases.
_LINK_KEYS = (("Accused_ID", "accused ID"), ("Vehicle_Reg_No", "vehicle"), ("UPI_ID", "UPI ID"),
              ("IP_Address", "IP address"), ("MO_Details", "modus operandi"), ("station", "police station"),
              ("district_norm", "district"), ("Beat_Name", "beat"), ("crime_type", "crime group"),
              ("CrimeHead_Name", "sub-heading"))


def _fir_link(spec: QuerySpec) -> list[dict]:
    a, b = _fval(spec, "fir_a"), _fval(spec, "fir_b")
    cols = ", ".join(c for c, _ in _LINK_KEYS) + ", fir_id, CrimeNo, date, ActSection, FIR_Stage"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    out = []
    try:
        for fid in (a, b):
            # exact first (index-backed); a lower-case id typed by hand falls back to UPPER()
            rows = conn.execute(f"SELECT {cols} FROM FIRs WHERE fir_id = ? OR CrimeNo = ?", (fid, fid)).fetchall() \
                or conn.execute(f"SELECT {cols} FROM FIRs WHERE UPPER(fir_id) = ?", (fid,)).fetchall()
            keys = {}
            for c, _ in _LINK_KEYS:
                vals = sorted({str(r.get(c)).strip() for r in rows if r.get(c) not in (None, "") and str(r.get(c)).strip()})
                keys[c] = vals
            r0 = rows[0] if rows else {}
            out.append({"fir": fid, "found": bool(rows), "keys": keys, "date": (r0.get("date") or "")[:10],
                        "act": r0.get("ActSection"), "stage": r0.get("FIR_Stage")})
    finally:
        conn.close()
    if len(out) == 2 and out[0]["found"] and out[1]["found"]:
        shared = []
        for c, label in _LINK_KEYS:
            common = sorted(set(out[0]["keys"][c]) & set(out[1]["keys"][c]))
            if common:
                shared.append({"key": c, "label": label, "values": common})
        out[0]["shared"] = shared
        try:
            from datetime import date as _d
            out[0]["days_apart"] = abs((_d.fromisoformat(out[1]["date"]) - _d.fromisoformat(out[0]["date"])).days)
        except Exception:
            out[0]["days_apart"] = None
    return out


def _event_effect(spec: QuerySpec) -> list[dict]:
    """T30: what the record shows an event did, measured by app/services/events.py (the same
    numbers the Predict page shows), plus when it next falls, in relative words only."""
    from datetime import date as _d
    from app.services import events as EV
    key = _fval(spec, "event") or ""
    if key not in EV.EVENTS:
        return []
    e = EV.EVENTS[key]
    zones = _fval(spec, "zone", "in")
    place = tuple(zones) if zones else (tuple(e.places) or None)
    try:
        overall = EV.effect(key, place)
        mv = EV.movers(key, place)
    except Exception:
        return []
    nxt = next((u for u in EV.upcoming(_d.today(), horizon_days=380) if u["key"] == key), None)
    return [{"event": key, "name": e.name, "what": e.what, "measured_in": ", ".join(zones) if zones else e.area,
             "overall": overall, "rises": mv.get("rises") or [], "falls": mv.get("falls") or [],
             "watch": mv.get("watch") or [], "when": (nxt or {}).get("when"),
             "years": len(EV._measure(key)["years"])}]


def _connect_ro() -> sqlite3.Connection:
    try:
        return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        return sqlite3.connect(DB_PATH)      # a path a URI cannot express (tests, odd mounts)


def year_cognizable(year: int) -> tuple[int, int]:
    """(cognizable, all) real-record FIRs held in the registry for one calendar year. A fixed query on
    a validated integer, not a template: the `crimes` view does not carry the flag."""
    y = int(year)
    con = _connect_ro()
    try:
        row = con.execute("SELECT COALESCE(SUM(is_cognizable = 1), 0), COUNT(*) FROM FIRs "
                          "WHERE is_synthetic_row = 0 AND date >= ? AND date <= ?", (f"{y}-01-01", f"{y}-12-31")).fetchone()
    finally:
        con.close()
    return int(row[0] or 0), int(row[1] or 0)


def run_local(spec: QuerySpec) -> list[dict]:
    rows = _run_local(spec)
    rn = getattr(spec, "rename", None)
    if rn and rows and isinstance(rows[0], dict):
        rows = [{rn.get(k, k): v for k, v in r.items()} for r in rows]
    return rows


def _run_local(spec: QuerySpec) -> list[dict]:
    # Every query path goes through here, so this is where the index set is guaranteed to
    # exist. It used to be reachable only via load_world(), which meant a freshly staged
    # database on Catalyst (expanded from main.db.gz, no secondary indexes) could serve
    # officer questions with full table scans of a million rows. After the first call the
    # `_indexes_checked` flag makes it free.
    ensure_indexes()
    if spec.table.startswith("__"):
        return _virtual_table(spec)

    sql = render_zcql(spec)
    
    # SQLite fix for 'month' derived column
    if "month" in sql and "SUBSTR" not in sql:
        sql = sql.replace("SELECT month,", "SELECT SUBSTR(occurred_at, 1, 7) AS month,")
        sql = sql.replace("SELECT month FROM", "SELECT SUBSTR(occurred_at, 1, 7) AS month FROM")
        sql = sql.replace("GROUP BY month", "GROUP BY SUBSTR(occurred_at, 1, 7)")
        sql = sql.replace("ORDER BY month", "ORDER BY SUBSTR(occurred_at, 1, 7)")

    # SQLite fix for full_name|alias multi-column filter
    if "UPPER(full_name|alias)" in sql:
        import re
        match = re.search(r"UPPER\(full_name\|alias\)\s+(LIKE|=)\s+(.*)", sql)
        if match:
            op = match.group(1)
            rest = match.group(2).strip()
            if rest.startswith("UPPER("):
                count = 1
                idx = 6
                while idx < len(rest) and count > 0:
                    if rest[idx] == '(':
                        count += 1
                    elif rest[idx] == ')':
                        count -= 1
                    idx += 1
                val_expr = rest[:idx]
                suffix = rest[idx:]
            else:
                parts = rest.split(maxsplit=1)
                val_expr = parts[0]
                suffix = " " + parts[1] if len(parts) > 1 else ""
            
            new_clause = f"(UPPER(full_name) {op} {val_expr} OR UPPER(alias) {op} {val_expr})"
            sql = sql[:match.start()] + new_clause + suffix

    # Result cache: the FIR table only changes through insert_crimes (which clears it), and a
    # single chat turn re-issues the same aggregate probes (answer writer totals, direction
    # trend, follow-up row checks) — each a scan over 1M rows.
    hit = _RESULT_CACHE.get(sql)
    if hit is not None:
        return [dict(r) for r in hit]
    # Read-only: a template only ever reads. If a value ever got past the escaping, the
    # connection itself could still not change a row.
    conn = _connect_ro()
    conn.row_factory = _dict_factory
    ok = True
    try:
        rows = conn.execute(sql).fetchall()
    except Exception as e:
        print(f"SQLite Error: {e} on query: {sql}")
        rows, ok = [], False
    finally:
        conn.close()
    if ok and len(rows) <= 2000:
        if len(_RESULT_CACHE) >= _RESULT_CACHE_MAX:
            _RESULT_CACHE.pop(next(iter(_RESULT_CACHE)))
        _RESULT_CACHE[sql] = [dict(r) for r in rows]
    return rows


_RESULT_CACHE: dict[str, list[dict]] = {}
_RESULT_CACHE_MAX = 512

def run_query(spec: QuerySpec) -> list[dict]:
    if USE_LOCAL:
        return run_local(spec)
    from app.core.catalyst import zcql_query
    return zcql_query(render_zcql(spec), olap=spec.olap)

def insert_crimes(records: list[dict]):
    from app.agents.query_agent import clear_query_cache
    clear_query_cache()
    _RESULT_CACHE.clear()
    _VIRTUAL_CACHE.clear()
    if USE_LOCAL:
        if not records: return
        conn = sqlite3.connect(DB_PATH)
        
        # We need to map keys to FIRs columns
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(FIRs)")
        fir_table_cols = [col[1] for col in cursor.fetchall() if col[1] != "id"]
        fir_placeholders = ",".join(["?"] * len(fir_table_cols))
        
        fir_data = []
        for r in records:
            dt = r.get("occurred_at", "") or ""
            date_str = dt[:10] if len(dt) >= 10 else "2026-06-19"
            try:
                year = date_str[:4]
                month = str(int(date_str[5:7]))
                day = str(int(date_str[8:10]))
            except Exception:
                year, month, day = "2026", "6", "19"
                
            mapping = {
                "fir_id": r.get("crime_id"),
                "District_Name": r.get("zone", "Unknown"),
                "UnitName": r.get("station_code") or r.get("station") or r.get("district") or "Unknown",
                "FIR_YEAR": year,
                "FIR_MONTH": month,
                "FIR_Day": day,
                "FIR_Stage": r.get("status", "Closed"),
                "CrimeGroup_Name": r.get("crime_type", "Unknown"),
                "Latitude": str(r.get("lat") or r.get("location_lat") or "0"),
                "Longitude": str(r.get("lng") or r.get("lon") or r.get("location_lon") or "0"),
                "date": date_str,
                "lat_r": float(r.get("lat") or 0.0),
                "lon_r": float(r.get("lng") or r.get("lon") or 0.0),
                "status": r.get("status", "Closed"),
                "crime_type": r.get("crime_type", "Unknown"),
                "zone": r.get("zone", "Unknown"),
                "station": r.get("station_code") or r.get("station") or "Unknown",
                "FIR_Type": r.get("fir_number") or r.get("crime_id")
            }
            
            row = [mapping.get(col) for col in fir_table_cols]
            fir_data.append(row)
            
        sql = f"INSERT INTO FIRs ({','.join(fir_table_cols)}) VALUES ({fir_placeholders})"
        conn.executemany(sql, fir_data)
        conn.commit()
        conn.close()

import time
_world_cache = {"data": None, "ts": 0.0}

def _world() -> dict:
    """Compatibility layer for local agents that depended on the old in-memory JSON world."""
    global _world_cache
    now = time.time()
    if _world_cache["data"] is not None and (now - _world_cache["ts"]) < 60.0:
        return _world_cache["data"]

    ensure_indexes()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    
    world = {}
    tables = ["suspects", "relationships", "crime_suspects", "financial_links", "officers", "property", "victims", "stations"]
    for t in tables:
        try:
            world[t] = conn.execute(f"SELECT * FROM {t}").fetchall()
        except Exception:
            world[t] = []
            
    try:
        # ONLY load crimes that are actually linked to suspects to save memory (3.6k rows vs 1.6M rows)
        world["crimes"] = conn.execute("SELECT * FROM crimes WHERE crime_id IN (SELECT DISTINCT crime_id FROM crime_suspects)").fetchall()
    except Exception as e:
        print("Error loading crimes:", e)
        world["crimes"] = []
            
    conn.close()
    _world_cache["data"] = world
    _world_cache["ts"] = now
    return world


def scan_rows(crime_type: str | None = None, period: str | None = None) -> list[dict]:
    """Shared helper: fetch lat/lon crime rows for geo/pattern agents using fast numeric columns."""
    from datetime import date, timedelta
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    where = ["geo_ok = 1"]
    params: list = []
    if crime_type:
        where.append("UPPER(CrimeGroup_Name) = UPPER(?)")
        params.append(crime_type)
    if period == "last_7_days":
        where.append("date >= ?")
        params.append((date.today() - timedelta(days=7)).isoformat())
    elif period == "this_month":
        where.append("date >= ?")
        params.append(date.today().replace(day=1).isoformat())
    elif period in ("last_3_months", "last_3months"):
        m = date.today().month - 3
        y = date.today().year
        if m <= 0:
            m += 12; y -= 1
        where.append("date >= ?")
        params.append(date.today().replace(year=y, month=m, day=1).isoformat())
    sql = (
        "SELECT geo_lat AS lat, geo_lon AS lon, District_Name AS zone, "
        "CrimeGroup_Name AS crime_type, date AS occurred_at "
        f"FROM FIRs WHERE {' AND '.join(where)} ORDER BY RANDOM() LIMIT 10000"
    )
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows
