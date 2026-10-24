"""
Antar — Full Dataset API (Brain · Page 02 "Full Data Set" toggle)
=================================================================
Aggregates and paginated rows over the COMPLETE FIRs table (1,000,000 rows), so the
FIR Data Overview can switch from the loaded sample CSV (~2.7k) to the real
full dataset without shipping 1M rows to the browser.

SQL policy: these are FIXED, reviewed, fully-parameterised statements over columns
verified to exist on the FIRs table — never LLM-authored and never string-built from
user input. Filter columns come from an explicit allowlist (_FILTER_COLS); values are
always bound parameters. This mirrors the existing hand-written helpers in
app/services/zcql_local.py (scan_rows, data_today) — the ZCQL-template rule governs
the LLM query path, which never reaches this module.

Endpoints:
  GET /api/dataset/overview   — KPIs + stage split + crime-group/year/district counts
  GET /api/dataset/records    — paginated, searchable FIR rows for the table
"""

from __future__ import annotations

import os
import re
import sqlite3

from fastapi import APIRouter, HTTPException

from app.services.zcql_local import DB_PATH
from app.core.db_path import ensure_db_staged
from app.core.db_path import registry_connect

router = APIRouter()

# The Brain constellation ("Intelligent Data") is served from a small curated DB (3,500 rich,
# densely-linked FIRs), NOT the full main.db — the graph needs dense entity links, not volume.
# intelligent.db ships in the backend root. On Catalyst the runtime DB decompresses to
# /tmp, so we must NOT look next to DB_PATH — resolve from this file's location instead.
_BACKEND_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
INTEL_DB = os.path.join(_BACKEND_ROOT, "intelligent.db")

# Columns the caller may filter on → real FIRs columns (allowlist, never interpolated blind).
_FILTER_COLS = {"year": "FIR_YEAR", "district": "District_Name"}

# Free-text search columns (fixed list).
_SEARCH_COLS = ["District_Name", "UnitName", "CrimeGroup_Name", "CrimeHead_Name", "Place_of_Offence"]

# An accused id as typed into the search box — full ("ACC-KA-110413") or partway there.
_ACC_RE = re.compile(r"^\s*acc(-[a-z]{0,2}(-\d*)?)?\s*$", re.I)

# The seed data carries the same label in several shapes (" CYBER CRIME" / "Cyber Crime",
# "Under Investigation" / "under_investigation"). Normalise before grouping so the UI
# never shows the same thing twice as separate rows.
_NORM_GROUP = "TRIM(UPPER(CrimeGroup_Name))"
_NORM_STAGE = "TRIM(UPPER(REPLACE(FIR_Stage,'_',' ')))"


def _title(s: str | None) -> str:
    return " ".join(w.capitalize() for w in str(s or "Unknown").split()) or "Unknown"


def _conn() -> sqlite3.Connection:
    ensure_db_staged()
    c = registry_connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


# ── What a headline count is actually counting ───────────────────────────────
# Three surfaces report three different registry sizes, and all three are correct:
#
#   Full Data Set summary   1,000,000   every row, ungated - the true dataset size
#   Overview / charts         995,505   future-dated rows hidden (the query-path gate)
#   Crime Graph cycles        912,167   COMPLETE calendar years only
#
# Each exclusion is deliberate. Future-dated rows are seeded ahead of the wall clock and
# are not "on record" today; the radial clock drops partial years because half a year
# drawn on a 12-month dial invents a seasonal shape that does not exist.
#
# What was missing is that no surface SAID so. An officer clicking between two screens saw
# 995,505 and 1,000,000 with nothing to explain the gap, which reads as a system that
# cannot count - the opposite of the impression every other number here works to earn.
# `count_basis()` travels with the number so the UI can label it, and
# `tests/test_count_reconciliation.py` asserts the three still reconcile exactly.

def count_basis(total: int, *, gated: bool, synthetic_excluded: bool = False,
                scope_years: list[int] | None = None,
                partial_years: list[int] | None = None,
                excluded: int = 0) -> dict:
    """A machine-readable description of what `total` includes, for the UI to render."""
    rules: list[str] = []
    if gated:
        rules.append("future-dated rows excluded")
    else:
        rules.append("all rows including future-dated")
    if synthetic_excluded:
        rules.append("seeded rows excluded")
    if partial_years:
        rules.append("complete calendar years only (partial: "
                     + ", ".join(str(y) for y in sorted(partial_years)) + ")")
    return {
        "total": int(total),
        "counts": "FIRs",
        "rules": rules,
        "excluded_rows": int(excluded),
        "label": f"{int(total):,} FIRs — " + "; ".join(rules),
        "scope_years": sorted(scope_years) if scope_years else None,
    }


def _where(year: int | None, district: str | None, groups: list[str] | None,
           q: str | None, exclude_synthetic: bool = False, gate: bool = True,
           year_from: int | None = None, year_to: int | None = None,
           id_from: int | None = None, id_to: int | None = None) -> tuple[str, list]:
    """Build the shared WHERE clause. Every value is a bound parameter.

    gate=True (default) hides future-dated rows from query/chart paths. The 'Full Data Set'
    summary passes gate=False + exclude_synthetic=False to report the TRUE dataset size.

    year_from/year_to bound the FIR year (inclusive); id_from/id_to bound the FIR row id
    (the "FIR range" filter). All optional and independently combinable.
    """
    clauses: list[str] = []
    params: list = []
    # PROTECTION: never surface future-dated FIRs on query paths. Rows dated after today stay
    # hidden and "unlock" automatically at midnight. Null dates pass.
    if gate:
        clauses.append("(date IS NULL OR date <= date('now','localtime'))")
    if exclude_synthetic:
        clauses.append("is_synthetic_row = 0")
    if year:
        clauses.append(f"{_FILTER_COLS['year']} = ?")
        params.append(str(year))
    if year_from is not None:
        clauses.append(f"CAST({_FILTER_COLS['year']} AS INTEGER) >= ?")
        params.append(int(year_from))
    if year_to is not None:
        clauses.append(f"CAST({_FILTER_COLS['year']} AS INTEGER) <= ?")
        params.append(int(year_to))
    if id_from is not None:
        clauses.append("id >= ?")
        params.append(int(id_from))
    if id_to is not None:
        clauses.append("id <= ?")
        params.append(int(id_to))
    if district:
        clauses.append(f"{_FILTER_COLS['district']} = ?")
        params.append(district)
    if groups:
        # match on the normalised form so " CYBER CRIME" / "Cyber Crime" resolve alike
        clauses.append(f"{_NORM_GROUP} IN (%s)" % ",".join("?" * len(groups)))
        params.extend([g.strip().upper() for g in groups])
    if q:
        term = q.strip()
        if _ACC_RE.match(term):
            # The search box asks for an ACC-id, but Accused_ID was not among the searched
            # columns, so the one thing it invited you to type never matched anything. An
            # id (or its prefix, as it is being typed) is now a range on an indexed column:
            # exact, and instant instead of a leading-wildcard scan of every row.
            lo = term.upper()
            clauses.append("(Accused_ID >= ? AND Accused_ID < ?)")
            params.extend([lo, lo[:-1] + chr(ord(lo[-1]) + 1)])
        else:
            like = f"%{term}%"
            cols = _SEARCH_COLS + ["Accused_ID"]
            clauses.append("(" + " OR ".join(f"{c} LIKE ?" for c in cols) + ")")
            params.extend([like] * len(cols))
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def _split(v: str | None) -> list[str] | None:
    if not v:
        return None
    out = [s.strip() for s in v.split(",") if s.strip()]
    return out or None


@router.get("/overview")
async def dataset_overview(year: int | None = None, district: str | None = None,
                           groups: str | None = None) -> dict:
    """Full-dataset KPIs + distributions. `groups` = comma-separated CrimeGroup_Name
    values (the frontend expands its crime-category selection into real group names,
    so categorisation stays defined in one place — lib/crimeGraph.js)."""
    glist = _split(groups)

    # Six aggregate scans over 1M FIR rows, and the stage/group normalisation
    # expressions mean SQLite cannot use an index for them — measured at ~10.7s. The
    # corpus is read-only between deploys, so the answer for a given filter set never
    # changes; serve it from the product store and pay the scan once. The unfiltered
    # variant (what the Brain screen requests on load) is pre-warmed at startup.
    from app.services import product_store
    # _split() returns None (not []) when the param is absent — join defensively.
    _cache_key = f"dataset:overview:{year or ''}:{district or ''}:{','.join(glist or [])}"
    _cached = product_store.get_product(_cache_key)
    if _cached:
        return _cached

    where, params = _where(year, district, glist, None)
    con = _conn()
    try:
        kpi = con.execute(
            "SELECT COUNT(*) AS total,"
            " COUNT(DISTINCT district_norm) AS districts,"
            " COUNT(DISTINCT UnitName) AS stations,"
            " COALESCE(SUM(VICTIM_COUNT),0) AS victims,"
            " COALESCE(SUM(Accused_Count),0) AS accused,"
            " COALESCE(SUM(Arrested_Count_No_),0) AS arrested,"
            " COALESCE(SUM(Accused_ChargeSheeted_Count),0) AS chargesheeted,"
            " COALESCE(SUM(Conviction_Count),0) AS convictions"
            f" FROM FIRs{where}", params).fetchone()

        stages = [{"label": _title(r["s"]), "n": r["n"]} for r in con.execute(
            f"SELECT {_NORM_STAGE} AS s, COUNT(*) AS n FROM FIRs"
            f"{where} GROUP BY s ORDER BY n DESC LIMIT 6", params).fetchall()]

        # `name` is the normalised group (what the frontend categorises + filters on)
        by_group = [{"name": r["g"] or "UNKNOWN", "label": _title(r["g"]), "n": r["n"]}
                    for r in con.execute(
            f"SELECT {_NORM_GROUP} AS g, COUNT(*) AS n FROM FIRs"
            f"{where} GROUP BY g ORDER BY n DESC", params).fetchall()]

        # non-numeric / NULL years are dropped in Python so the SQL stays one fixed shape
        years = [{"year": int(r["FIR_YEAR"]), "n": r["n"]} for r in con.execute(
            "SELECT FIR_YEAR, COUNT(*) AS n FROM FIRs"
            f"{where} GROUP BY FIR_YEAR ORDER BY FIR_YEAR", params).fetchall()
            if r["FIR_YEAR"] is not None and str(r["FIR_YEAR"]).isdigit()]

        top_districts = [{"district": r["District_Name"], "n": r["n"]} for r in con.execute(
            "SELECT District_Name, COUNT(*) AS n FROM FIRs"
            f"{where} GROUP BY District_Name ORDER BY n DESC LIMIT 10", params).fetchall()]
    finally:
        con.close()

    accused = kpi["accused"] or 0
    payload = {
        "source": "main.db · FIRs",
        "basis": count_basis(kpi["total"], gated=True),
        "total": kpi["total"],
        "districts": kpi["districts"],
        "stations": kpi["stations"],
        "victims": kpi["victims"],
        "accused": accused,
        "arrested": kpi["arrested"],
        "chargesheeted": kpi["chargesheeted"],
        "convictions": kpi["convictions"],
        "arrest_rate": round((kpi["arrested"] / accused) * 100) if accused else 0,
        "stages": stages,
        "by_crime_group": by_group,
        "years": years,
        "top_districts": top_districts,
    }
    # 6h TTL: the shipped database only changes on deploy.
    product_store.put_product(_cache_key, payload, ttl=21600)
    return payload


@router.get("/summary")
async def dataset_summary(year: int | None = None, district: str | None = None,
                          groups: str | None = None, year_from: int | None = None,
                          year_to: int | None = None, id_from: int | None = None,
                          id_to: int | None = None) -> dict:
    """Full-dataset KPIs + distributions — the TRUE dataset size (all rows, ungated).

    Optional year_from/year_to and id_from/id_to narrow the dataset (Data Overview filters)."""
    glist = _split(groups)
    # Cached like /overview. This endpoint runs ~7 full aggregates over the registry and
    # nothing else on the page can render until it returns: at 1M FIRs that was 10.7 s on
    # every visit, during which the Full Data Set tab showed "0 FIRs TOTAL" — which reads
    # as an empty database, not a slow one. The data only changes on ingest or deploy.
    from app.services import product_store
    _cache_key = ("dataset:summary:" + ":".join(str(v or "") for v in (
        year, district, ",".join(glist or []), year_from, year_to, id_from, id_to)))
    _cached = product_store.get_product(_cache_key)
    if _cached:
        return _cached
    where, params = _where(year, district, glist, None, exclude_synthetic=False, gate=False,
                           year_from=year_from, year_to=year_to, id_from=id_from, id_to=id_to)
    con = _conn()
    try:
        kpi = con.execute(
            "SELECT COUNT(*) AS total,"
            " COUNT(DISTINCT district_norm) AS districts,"
            " COUNT(DISTINCT UnitName) AS stations,"
            " COALESCE(SUM(VICTIM_COUNT),0) AS victims,"
            " COALESCE(SUM(Accused_Count),0) AS accused,"
            " COALESCE(SUM(Arrested_Count_No_),0) AS arrested,"
            " COALESCE(SUM(Accused_ChargeSheeted_Count),0) AS chargesheeted,"
            " COALESCE(SUM(Conviction_Count),0) AS convictions"
            f" FROM FIRs{where}", params).fetchone()

        stages = [{"label": _title(r["s"]), "n": r["n"]} for r in con.execute(
            f"SELECT {_NORM_STAGE} AS s, COUNT(*) AS n FROM FIRs"
            f"{where} GROUP BY s ORDER BY n DESC LIMIT 6", params).fetchall()]

        by_group = [{"name": r["g"] or "UNKNOWN", "label": _title(r["g"]), "n": r["n"]}
                    for r in con.execute(
            f"SELECT {_NORM_GROUP} AS g, COUNT(*) AS n FROM FIRs"
            f"{where} GROUP BY g ORDER BY n DESC", params).fetchall()]

        # "partial" describes the DATASET's coverage of a year (2024 stops in March), not
        # the filter's — a quiet district must not flag a complete year as partial — so it
        # is measured unfiltered. One grouped pass instead of a query per year: that was
        # eleven extra full scans for an eleven-year registry.
        months_present = {str(r[0]): r[1] for r in con.execute(
            "SELECT FIR_YEAR, COUNT(DISTINCT FIR_MONTH) FROM FIRs"
            " WHERE FIR_MONTH IS NOT NULL GROUP BY FIR_YEAR").fetchall()}
        years = []
        for r in con.execute(
                "SELECT FIR_YEAR, COUNT(*) AS n FROM FIRs"
                f"{where} GROUP BY FIR_YEAR ORDER BY FIR_YEAR", params).fetchall():
            if r["FIR_YEAR"] is not None and str(r["FIR_YEAR"]).isdigit():
                years.append({"year": int(r["FIR_YEAR"]), "n": r["n"],
                              "partial": months_present.get(str(r["FIR_YEAR"]), 0) < 12})

        top_districts = [{"district": r["District_Name"], "n": r["n"]} for r in con.execute(
            "SELECT District_Name, COUNT(*) AS n FROM FIRs"
            f"{where} GROUP BY District_Name ORDER BY n DESC LIMIT 10", params).fetchall()]
    finally:
        con.close()

    accused = kpi["accused"] or 0
    payload = {
        "source": "main.db · FIRs (real only)",
        "basis": count_basis(kpi["total"], gated=False),
        "total_real": kpi["total"],
        "total": kpi["total"],
        "districts": kpi["districts"],
        "stations": kpi["stations"],
        "victims": kpi["victims"],
        "accused": accused,
        "arrested": kpi["arrested"],
        "chargesheeted": kpi["chargesheeted"],
        "convictions": kpi["convictions"],
        "arrest_rate": round((kpi["arrested"] / accused) * 100) if accused else 0,
        "stages": stages,
        "by_crime_group": by_group,
        "years": years,
        "top_districts": top_districts,
    }
    product_store.put_product(_cache_key, payload, ttl=21600)
    return payload


_UI_STAGE = "UNDER INVESTIGATION"
# BNSS s.187(3): an accused in custody must be released on (default) bail if the
# investigation is not completed within 60 days, or 90 days for offences punishable with
# death, life imprisonment or ten years or more. The register does not record custody or
# offence gravity per FIR, so the clock is shown against BOTH limits, never classified.
_LIMIT_SHORT, _LIMIT_LONG, _DUE_SOON = 60, 90, 7
_NO_GROUP = "__no_such_group__"


def _raw_group_names(con: sqlite3.Connection, groups: list[str]) -> list[str]:
    """The stored spellings of the requested crime groups (" CYBER CRIME", "Cyber Crime"...).

    Filtering on TRIM(UPPER(CrimeGroup_Name)) forces a pass over every row; filtering on
    the raw values it maps to is a range scan of idx_firs_group_date. There are ~141
    distinct raw values, enumerated from the index itself.
    """
    want = {g.strip().upper() for g in groups}
    raw = [r[0] for r in con.execute("SELECT CrimeGroup_Name FROM FIRs GROUP BY CrimeGroup_Name")]
    return [v for v in raw if v is not None and str(v).strip().upper() in want]


def _fast_where(con, *, year=None, year_from=None, year_to=None, district=None,
                groups=None) -> tuple[str, list]:
    """Filters expressed on INDEXED columns: years as date ranges (idx_firs_outcomes and
    idx_firs_date_ct cover `date`), crime groups as raw values (idx_firs_group_date).
    Future-dated FIRs are always excluded. Every value is a bound parameter."""
    clauses = ["date IS NOT NULL", "date <= date('now','localtime')"]
    params: list = []
    lo = year or year_from
    hi = year or year_to
    if lo:
        clauses.append("date >= ?")
        params.append(f"{int(lo):04d}-01-01")
    if hi:
        clauses.append("date < ?")
        params.append(f"{int(hi) + 1:04d}-01-01")
    if district:
        clauses.append("District_Name = ?")
        params.append(district)
    if groups:
        raw = _raw_group_names(con, groups) or [_NO_GROUP]
        clauses.append("CrimeGroup_Name IN (%s)" % ",".join("?" * len(raw)))
        params.extend(raw)
    return " WHERE " + " AND ".join(clauses), params


def _statewide_months(con) -> set:
    """Months in which the register holds ANY FIR, statewide. A month outside this set is
    a gap in the data, not a month without crime, and is drawn as a gap."""
    return {r[0] for r in con.execute(
        "SELECT DISTINCT substr(date,1,7) FROM FIRs WHERE date IS NOT NULL "
        "AND date <= date('now','localtime')")}


@router.get("/officer_view")
async def dataset_officer_view(year: int | None = None, district: str | None = None,
                               groups: str | None = None, year_from: int | None = None,
                               year_to: int | None = None) -> dict:
    # A cold pass takes ~17 s at 1M FIRs. On a worker thread, so it never stalls the event
    # loop (and with it every other request) the way an inline sqlite call in an async
    # handler does.
    import asyncio
    return await asyncio.to_thread(_officer_view, year, district, groups, year_from, year_to)


def _officer_view(year, district, groups, year_from, year_to) -> dict:
    """What a station admin acts on, for the same filters as /summary:

    deadline -- open investigations aged against the 60/90-day limits, and which
                districts / stations hold the most cases past 90 days;
    outcomes -- of every 100 FIRs, how many saw an arrest, a chargesheet, a conviction;
    monthly  -- FIRs per month over the 24 months ending at the latest record in view.

    Future-dated FIRs are excluded here (an age or a month in the future is meaningless);
    the headline total on the page stays the full register, by the owner's decision.
    """
    glist = _split(groups)
    from app.services import product_store
    _cache_key = ("dataset:officer:v2:" + ":".join(str(v or "") for v in (
        year, district, ",".join(glist or []), year_from, year_to)))
    _cached = product_store.get_product(_cache_key)
    if _cached:
        return _cached

    age = "(julianday('now','localtime') - julianday(date))"
    ui = f"TRIM(UPPER(REPLACE(FIR_Stage,'_',' '))) = '{_UI_STAGE}'"   # a constant, never user input
    con = _conn()
    try:
        where, params = _fast_where(con, year=year, year_from=year_from, year_to=year_to,
                                    district=district, groups=glist)
        # ONE pass for the deadline clock and the outcome rates together.
        r = con.execute(
            "SELECT COUNT(*) AS firs,"
            " SUM(CASE WHEN COALESCE(Arrested_Count_No_,0) > 0 THEN 1 ELSE 0 END) AS with_arrest,"
            " SUM(CASE WHEN COALESCE(Accused_ChargeSheeted_Count,0) > 0 THEN 1 ELSE 0 END) AS with_cs,"
            " SUM(CASE WHEN COALESCE(Conviction_Count,0) > 0 THEN 1 ELSE 0 END) AS with_conv,"
            " COALESCE(SUM(Accused_Count),0) AS accused, COALESCE(SUM(Arrested_Count_No_),0) AS arrested,"
            " COALESCE(SUM(Accused_ChargeSheeted_Count),0) AS chargesheeted,"
            " COALESCE(SUM(Conviction_Count),0) AS convicted,"
            f" SUM(CASE WHEN {ui} THEN 1 ELSE 0 END) AS open_total,"
            f" SUM(CASE WHEN {ui} AND {age} <= {_LIMIT_SHORT} THEN 1 ELSE 0 END) AS within_60,"
            f" SUM(CASE WHEN {ui} AND {age} > {_LIMIT_SHORT} AND {age} <= {_LIMIT_LONG} THEN 1 ELSE 0 END) AS d61_90,"
            f" SUM(CASE WHEN {ui} AND {age} > {_LIMIT_LONG} THEN 1 ELSE 0 END) AS over_90,"
            f" SUM(CASE WHEN {ui} AND (({age} >= {_LIMIT_SHORT - _DUE_SOON} AND {age} < {_LIMIT_SHORT})"
            f"   OR ({age} >= {_LIMIT_LONG - _DUE_SOON} AND {age} < {_LIMIT_LONG})) THEN 1 ELSE 0 END) AS due_7,"
            f" MAX(CASE WHEN {ui} THEN CAST({age} AS INTEGER) END) AS oldest_days,"
            " MAX(date) AS last_date"
            f" FROM FIRs{where}", params).fetchone()

        over = f"{where} AND {ui} AND {age} > {_LIMIT_LONG}"
        by_station = con.execute(
            f"SELECT UnitName, District_Name, COUNT(*) n FROM FIRs{over}"
            " GROUP BY UnitName, District_Name", params).fetchall()
        dist_tot: dict = {}
        for u, d, n in by_station:
            if d:
                dist_tot[d] = dist_tot.get(d, 0) + n
        top_d = [{"name": d, "n": n} for d, n in sorted(dist_tot.items(), key=lambda kv: -kv[1])[:5]]
        top_s = [{"name": u, "district": d, "n": n}
                 for u, d, n in sorted(by_station, key=lambda x: -x[2])[:5] if u]

        last = r["last_date"]
        monthly = []
        if last:
            present = _statewide_months(con)
            mw = f"{where} AND date >= date(?, 'start of month', '-23 months')"
            got = {m: n for m, n in con.execute(
                f"SELECT substr(date,1,7) m, COUNT(*) FROM FIRs{mw} GROUP BY m", [*params, last])}
            y, m = int(last[:4]), int(last[5:7])
            for i in range(23, -1, -1):
                yy, mm = y, m - i
                while mm <= 0:
                    mm += 12
                    yy -= 1
                key = f"{yy:04d}-{mm:02d}"
                # None = no FIRs recorded anywhere that month: a data gap, drawn as a gap.
                monthly.append({"month": key, "n": got.get(key, 0) if key in present else None})
    finally:
        con.close()

    def pct(a, b):
        return round(100 * (a or 0) / b, 1) if b else 0.0

    firs = r["firs"] or 0
    payload = {
        "deadline": {
            "open_total": r["open_total"] or 0, "within_60": r["within_60"] or 0,
            "d61_90": r["d61_90"] or 0, "over_90": r["over_90"] or 0, "due_7": r["due_7"] or 0,
            "oldest_days": r["oldest_days"] or 0,
            "top_districts_over_90": top_d, "top_stations_over_90": top_s,
            "basis": "Under-investigation FIRs aged from registration date; limits per BNSS s.187(3).",
        },
        "outcomes": {
            "firs": firs,
            # Per 100 FIRs. These do NOT nest: a chargesheet can be filed against an accused
            # who was never arrested (absconding), so the second can exceed the first.
            "per_100": {"arrest": pct(r["with_arrest"], firs), "chargesheet": pct(r["with_cs"], firs),
                        "conviction": pct(r["with_conv"], firs)},
            "accused": {
                "accused": r["accused"], "arrested": r["arrested"],
                "chargesheeted": r["chargesheeted"], "convicted": r["convicted"],
                "arrest_rate": pct(r["arrested"], r["accused"]),
                "chargesheet_rate": pct(r["chargesheeted"], r["accused"]),
                "conviction_rate": pct(r["convicted"], r["chargesheeted"]),
            },
        },
        "monthly": monthly,
        "as_of": last,
        "evidence_class": "D",
    }
    product_store.put_product(_cache_key, payload, ttl=21600)
    return payload


@router.get("/crime_profile")
async def dataset_crime_profile(groups: str, year: int | None = None,
                                district: str | None = None, years: str | None = None) -> dict:
    """years: comma-separated list — the chart's own scope ("All" = complete years only),
    so the panel counts exactly the FIRs the radial chart beside it draws."""
    import asyncio
    return await asyncio.to_thread(_crime_profile, groups, year, district, years)


def _crime_profile(groups, year, district, years=None) -> dict:
    """When and where one crime concentrates -- the Crime Graph detail.

    groups: comma-separated CrimeGroup_Name values (the UI expands its category).
    Returns the month curve, weekday split, early/mid/late-month split, and the top
    districts and stations with their share of THIS crime's total. Future-dated rows out.
    One indexed pass; the aggregation happens here rather than in four GROUP BYs.
    """
    glist = _split(groups)
    if not glist:
        raise HTTPException(status_code=422, detail="groups is required")
    from app.services import product_store
    ylist = sorted({int(y) for y in (_split(years) or []) if str(y).strip().isdigit()})
    _cache_key = f"dataset:crimeprofile:v3:{','.join(sorted(glist))}:{year or ''}:{district or ''}:{','.join(map(str, ylist))}"
    _cached = product_store.get_product(_cache_key)
    if _cached:
        return _cached
    import datetime as _dt
    months, weekdays = [0] * 12, [0] * 7
    thirds = {"early": 0, "mid": 0, "late": 0}
    dist: dict = {}
    stat: dict = {}
    total = 0
    # Same field and gate as /cycles (the radial chart this panel sits beside):
    # TRIM(UPPER(crime_type)) with future dates excluded. crime_type and CrimeGroup_Name
    # disagree on ~80k rows, and matching on the other one made the panel contradict the
    # chart (a different peak month, a different total). idx_firs_u_crime_type covers it.
    clauses = ["date IS NOT NULL", "date <= date('now','localtime')",
               "TRIM(UPPER(crime_type)) IN (%s)" % ",".join("?" * len(glist))]
    params: list = [g.strip().upper() for g in glist]
    if year:
        clauses.append("date >= ? AND date < ?")
        params += [f"{int(year):04d}-01-01", f"{int(year) + 1:04d}-01-01"]
    elif ylist:
        clauses.append("substr(date,1,4) IN (%s)" % ",".join("?" * len(ylist)))
        params += [f"{y:04d}" for y in ylist]
    if district:
        clauses.append("District_Name = ?")
        params.append(district)
    where = " WHERE " + " AND ".join(clauses)
    con = _conn()
    try:
        for d, dn, un in con.execute(f"SELECT date, District_Name, UnitName FROM FIRs{where}", params):
            total += 1
            try:
                y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
                months[m - 1] += 1
                weekdays[_dt.date(y, m, dd).weekday()] += 1       # Monday = 0
                thirds["early" if dd <= 10 else "mid" if dd <= 20 else "late"] += 1
            except (ValueError, TypeError, IndexError):
                pass
            if dn:
                dist[dn] = dist.get(dn, 0) + 1
            if un:
                stat[(un, dn)] = stat.get((un, dn), 0) + 1
    finally:
        con.close()
    MN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def share(n):
        return round(100 * n / total, 1) if total else 0.0

    peak_m = max(range(12), key=lambda i: months[i]) if total else None
    peak_w = max(range(7), key=lambda i: weekdays[i]) if total else None
    mean_m = sum(months) / 12 if total else 0
    payload = {
        "groups": glist, "total": total,
        "months": [{"m": MN[i], "n": months[i]} for i in range(12)],
        "weekdays": [{"d": WD[i], "n": weekdays[i]} for i in range(7)],
        "month_thirds": thirds,
        "peak_month": MN[peak_m] if peak_m is not None else None,
        "peak_month_vs_avg": round(100 * (months[peak_m] / mean_m - 1)) if peak_m is not None and mean_m else 0,
        "peak_weekday": WD[peak_w] if peak_w is not None else None,
        "top_districts": [{"name": k, "n": v, "share": share(v)}
                          for k, v in sorted(dist.items(), key=lambda kv: -kv[1])[:6]],
        "top_stations": [{"name": k[0], "district": k[1], "n": v, "share": share(v)}
                         for k, v in sorted(stat.items(), key=lambda kv: -kv[1])[:6]],
        "evidence_class": "D",
    }
    product_store.put_product(_cache_key, payload, ttl=21600)
    return payload


@router.get("/graph")
async def dataset_graph(limit: int = 3000) -> dict:
    """Returns ONLY rows with linkage for the brain graph, in the shape crimeGraph.js expects."""
    limit = max(1, min(limit, 5000))
    # Read the curated intelligent_data.db (3,500 dense rows) if present; fall back to the
    # linked subset of the full DB so the endpoint still works before that DB is built.
    # Fail-soft: any DB error returns {"rows": []} (never a 500 that breaks the Brain),
    # and logs the real cause so it's visible in the Catalyst runtime logs.
    rows, con = [], None
    try:
        if os.path.exists(INTEL_DB):
            con = sqlite3.connect(f"file:{INTEL_DB}?immutable=1", uri=True)
            con.row_factory = sqlite3.Row
            query = (
                "SELECT id, District_Name, UnitName, FIR_YEAR, FIR_MONTH, FIR_Day, FIR_Stage,"
                " CrimeGroup_Name, CrimeHead_Name, Place_of_Offence, VICTIM_COUNT, Accused_Count,"
                " Arrested_Count_No_, Accused_ChargeSheeted_Count, Conviction_Count,"
                # has_synthetic_link travels with the row so the screen can say how much of the
                # linked view is demonstration links (DataOverview's Linked records note)
                " Vehicle_Reg_No, UPI_ID, IP_Address, MO_Details, Accused_ID, has_synthetic_link FROM FIRs"
                " ORDER BY has_synthetic_link DESC, id ASC LIMIT ?")
        else:
            con = _conn()
            query = (
                "SELECT id, District_Name, UnitName, FIR_YEAR, FIR_MONTH, FIR_Day, FIR_Stage,"
                " CrimeGroup_Name, CrimeHead_Name, Place_of_Offence, VICTIM_COUNT, Accused_Count,"
                " Arrested_Count_No_, Accused_ChargeSheeted_Count, Conviction_Count,"
                " Vehicle_Reg_No, UPI_ID, IP_Address, MO_Details, Accused_ID, has_synthetic_link FROM FIRs"
                " WHERE is_synthetic_row = 0 AND has_synthetic_link = 1"
                " ORDER BY FIR_YEAR DESC, FIR_MONTH DESC, id DESC LIMIT ?")
        rows = con.execute(query, [limit]).fetchall()
    except Exception as e:
        import structlog
        structlog.get_logger("dataset").warning(
            "dataset_graph_failed", err=repr(e), intel_db=INTEL_DB,
            intel_exists=os.path.exists(INTEL_DB), db_path=DB_PATH)
        rows = []
    finally:
        if con is not None:
            con.close()

    def _str(v): return str(v) if v is not None else ""

    out = [{
        "id": r["id"],
        "FIR_YEAR": _str(r["FIR_YEAR"]),
        "FIR_MONTH": _str(r["FIR_MONTH"]),
        "FIR_Day": _str(r["FIR_Day"]),
        "District_Name": _str(r["District_Name"]),
        "UnitName": _str(r["UnitName"]),
        "CrimeGroup_Name": _str(r["CrimeGroup_Name"]),
        "CrimeHead_Name": _str(r["CrimeHead_Name"]),
        "FIR_Stage": _str(r["FIR_Stage"]),
        "status": _str(r["FIR_Stage"]),
        "Place_of_Offence": _str(r["Place_of_Offence"]),
        "Victim_Count": _str(r["VICTIM_COUNT"]),
        "Accused_Count": _str(r["Accused_Count"]),
        "Arrested_Count": _str(r["Arrested_Count_No_"]),
        "Accused_ChargeSheeted_Count": _str(r["Accused_ChargeSheeted_Count"]),
        "Conviction_Count": _str(r["Conviction_Count"]),
        "Vehicle_Reg_No": _str(r["Vehicle_Reg_No"]),
        "UPI_ID": _str(r["UPI_ID"]),
        "IP_Address": _str(r["IP_Address"]),
        "MO_Details": _str(r["MO_Details"]),
        "Accused_ID": _str(r["Accused_ID"]),
    } for r in rows]

    return {"rows": out}

@router.get("/records")
async def dataset_records(q: str | None = None, year: int | None = None,
                          district: str | None = None, groups: str | None = None,
                          limit: int = 50, offset: int = 0, year_from: int | None = None,
                          year_to: int | None = None, id_from: int | None = None,
                          id_to: int | None = None) -> dict:
    """Paginated FIR rows for the overview table. Keys are mapped to the same shape the
    frontend already uses for the CSV sample so one table renders both sources.
    year_from/year_to and id_from/id_to apply the Data Overview range filters."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    where, params = _where(year, district, _split(groups), q,
                           year_from=year_from, year_to=year_to, id_from=id_from, id_to=id_to)
    from app.services import product_store
    # The total only changes with the filter, not the page — so it is counted once per
    # filter instead of once per page turn (a full COUNT over 1M rows every click).
    _count_key = "dataset:records:count:" + repr((where, params))
    con = _conn()
    try:
        total = product_store.get_product(_count_key)
        if total is None:
            total = con.execute(f"SELECT COUNT(*) FROM FIRs{where}", params).fetchone()[0]
            product_store.put_product(_count_key, total, ttl=21600)
        # ORDER BY the ISO `date`, not FIR_YEAR / FIR_MONTH. FIR_MONTH is TEXT, so a
        # descending sort put '9' above '12' — September ahead of December in every full
        # year. The tiebreaker is `rowid`, not `id`: an index on `date` is implicitly
        # (date, rowid), so SQLite walks it backwards and stops after one page. With `id`
        # it had to sort the whole registry first — 11,230 ms → 9 ms per page.
        rows = con.execute(
            "SELECT id, District_Name, UnitName, FIR_YEAR, FIR_MONTH, FIR_Day, FIR_Stage,"
            " CrimeGroup_Name, CrimeHead_Name, Place_of_Offence, VICTIM_COUNT, Accused_Count,"
            " Arrested_Count_No_, Accused_ChargeSheeted_Count, Conviction_Count,"
            " Vehicle_Reg_No, UPI_ID, IP_Address, MO_Details, Accused_ID FROM FIRs"
            f"{where} ORDER BY date DESC, rowid DESC LIMIT ? OFFSET ?",
            params + [limit, offset]).fetchall()
    finally:
        con.close()

    def _int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    out = [{
        "_i": r["id"],
        "_year": _int(r["FIR_YEAR"]),
        "_month": _int(r["FIR_MONTH"]),
        "_day": _int(r["FIR_Day"]),
        "District_Name": r["District_Name"],
        "UnitName": r["UnitName"],
        "CrimeGroup_Name": r["CrimeGroup_Name"],
        "CrimeHead_Name": r["CrimeHead_Name"],
        "FIR_Stage": r["FIR_Stage"],
        "Place_of_Offence": r["Place_of_Offence"],
        "Accused_ID": r["Accused_ID"],
        "Victim_Count": r["VICTIM_COUNT"],
        "Accused_Count": r["Accused_Count"],
        "Arrested_Count": r["Arrested_Count_No_"],
        "Accused_ChargeSheeted_Count": r["Accused_ChargeSheeted_Count"],
        "Conviction_Count": r["Conviction_Count"],
        "Vehicle_Reg_No": r["Vehicle_Reg_No"],
        "UPI_ID": r["UPI_ID"],
        "IP_Address": r["IP_Address"],
        "MO_Details": r["MO_Details"],
    } for r in rows]

    return {"rows": out, "total": total, "limit": limit, "offset": offset}


@router.get("/year_intel")
async def dataset_year_intel(year: int | None = None) -> dict:
    """Per-year 'intelligent takeaway' — ACCURATE annual totals for RAG / year questions.

    Pre-2023 years hold the real annual total (the FIRs table stores a 1:100 representative
    sample for the graph shape, so this endpoint is the source of truth for 'show me 2020 data').
    Returns one year or the full 2016-2026 series.
    """
    con = _conn()
    try:
        if "year_intel" not in {r["name"] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}:
            return {"years": []}
        if year:
            rows = con.execute("SELECT * FROM year_intel WHERE year = ?", [year]).fetchall()
        else:
            rows = con.execute("SELECT * FROM year_intel ORDER BY year").fetchall()
    finally:
        con.close()
    return {"years": [{
        "year": r["year"], "fir_count": r["fir_count"], "is_real": bool(r["is_real"]),
        "top_categories": r["top_categories"], "summary": r["summary"],
    } for r in rows]}


@router.get("/calendar")
async def dataset_calendar(year: int) -> dict:
    """Per-day FIR counts over the FULL dataset for one year.

    Powers the Brain 'Case activity' calendar's Full-Dataset mode — the low→high daily
    heat reflects EVERY FIR that year (the complete 1,000,000-row main.db), not the ~3.5k
    linked constellation sample. Counts ALL rows: no synthetic filter and no future-date
    gate, so the yearly totals sum to the true dataset size. Fixed, fully-parameterised
    aggregate (same SQL policy as the rest of this module), grouped by month/day.
    """
    con = _conn()
    try:
        rows = con.execute(
            "SELECT FIR_MONTH AS m, FIR_Day AS d, COUNT(*) AS n FROM FIRs"
            " WHERE FIR_YEAR = ?"
            "   AND FIR_MONTH IS NOT NULL AND FIR_Day IS NOT NULL"
            " GROUP BY FIR_MONTH, FIR_Day", [str(year)]).fetchall()
        # Authoritative totals via COUNT(*) — unaffected by any odd month/day values,
        # so the year total (and the 325,001 grand total) are always exact.
        year_total = con.execute("SELECT COUNT(*) FROM FIRs WHERE FIR_YEAR = ?", [str(year)]).fetchone()[0]
        grand_total = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
    finally:
        con.close()

    days, mx = [], 0
    for r in rows:
        try:
            m, d = int(r["m"]), int(r["d"])
        except (TypeError, ValueError):
            continue
        if not (1 <= m <= 12 and 1 <= d <= 31):
            continue
        n = r["n"] or 0
        mx = max(mx, n)
        days.append({"m": m, "d": d, "n": n})

    return {"year": year, "days": days, "total": year_total, "grand_total": grand_total,
            "max": mx, "source": "main.db · FIRs (full dataset)"}


@router.get("/cycles")
async def dataset_cycles(year: int | None = None) -> dict:
    """Full-dataset crime-cycle data for the Crime Graph radial clock.

    Returns REAL counts from the full 1,000,000-row FIRs table — no sampling and no
    scale factor. Two exclusions apply and `basis` in the payload states both: future-dated
    rows are gated out, and only COMPLETE calendar years are in scope (a half-year drawn on
    a 12-month dial invents a seasonal shape that does not exist). `total` is therefore the
    count over `scope_years`, not over the whole table — measured 912,167 of 995,505.
    This docstring previously claimed "no future-date gate", which the code directly below
    contradicts.

    Bins: 36 per year (3 per month — 10-day intervals), used to build the
    polar waveforms.  Groups are normalised via TRIM(UPPER(CrimeGroup_Name)).

    Cached in product_store (key ``dataset:cycles:<year>``, TTL 6 h).
    Pre-warmed for ``year=None`` (all) at startup.
    """
    from app.services import product_store

    cache_key = f"dataset:cycles:v2:{year or 'all'}"
    cached = product_store.get_product(cache_key)
    if cached:
        return cached

    # Future-dated rows stay out, as on every other query path. Without this the 2026
    # clock drew October-December 2026 — ~4.4k FIRs that have not happened yet.
    #
    # Everything here reads the ISO `date` and `crime_type`, which carry exactly the same
    # values as FIR_YEAR/FIR_MONTH/FIR_Day and CrimeGroup_Name (verified: zero rows
    # disagree) but sit together in one narrow index — so a year chip is an index range
    # scan, not a pass over every row. Cold, "All" took ~22s this way round.
    gate = "date <= date('now','localtime')"
    grp = "TRIM(UPPER(crime_type))"

    con = _conn()
    try:
        # ── Per-year coverage (after the gate) ─────────────────────────────
        years = []
        for r in con.execute(
                "SELECT substr(date,1,4) AS y, COUNT(*) AS n, COUNT(DISTINCT substr(date,6,2)) AS mc"
                f" FROM FIRs WHERE {gate} GROUP BY y ORDER BY y").fetchall():
            if r["y"] and str(r["y"]).isdigit():
                years.append({"year": int(r["y"]), "n": r["n"], "months_covered": r["mc"] or 0})

        # ── Scope ──────────────────────────────────────────────────────────
        # One year: that year. "All": COMPLETE years only. Summing raw counts across
        # years that cover different months manufactures seasonality — the registry's
        # 2024 stops in March, so adding it made Jan-Mar look ~30% worse than the rest
        # of the year, a winter surge that does not exist. A partial year keeps its own
        # chip; it just does not bend the shape of "All".
        if year is not None:
            scope_years = [year]
            partial_years: list[int] = []
        else:
            scope_years = [y["year"] for y in years if y["months_covered"] >= 12]
            partial_years = [y["year"] for y in years if y["months_covered"] < 12]
        if not scope_years:
            scope_years = [-1]                       # matches nothing; keeps SQL shape
        if len(scope_years) == 1:
            y0 = int(scope_years[0])
            where = f" WHERE {gate} AND date >= ? AND date <= ?"
            params = [f"{y0:04d}-01-01", f"{y0:04d}-12-31"]
        else:
            ph = ",".join("?" * len(scope_years))
            where = f" WHERE {gate} AND substr(date,1,4) IN ({ph})"
            params = [f"{int(y):04d}" for y in scope_years]

        total = con.execute(f"SELECT COUNT(*) FROM FIRs{where}", params).fetchone()[0]

        # ── Per-group 36-bin waveforms ─────────────────────────────────────
        # bin = (month-1)*3 + MIN(2, (day-1)/10)  → 0..35
        bin_rows = con.execute(
            f"SELECT {grp} AS g,"
            " CAST(substr(date,6,2) AS INTEGER) AS m,"
            " MIN(2, (CAST(substr(date,9,2) AS INTEGER) - 1) / 10) AS b10,"
            " COUNT(*) AS n"
            f" FROM FIRs{where}"
            " GROUP BY g, m, b10", params).fetchall()

        group_bins: dict[str, list[int]] = {}
        group_totals: dict[str, int] = {}
        for r in bin_rows:
            g = r["g"] or "UNKNOWN"
            idx = (int(r["m"]) - 1) * 3 + min(2, int(r["b10"]))
            if g not in group_bins:
                group_bins[g] = [0] * 36
                group_totals[g] = 0
            group_bins[g][idx] += r["n"]
            group_totals[g] += r["n"]

        groups = sorted(
            [{"name": g, "bins": bins, "n": group_totals[g]} for g, bins in group_bins.items()],
            key=lambda x: x["n"], reverse=True)

        month_totals = [0] * 12
        for g_data in groups:
            for i, v in enumerate(g_data["bins"]):
                month_totals[i // 3] += v
    finally:
        con.close()

    _scope = [y for y in scope_years if y != -1]
    _all_gated = sum(y["n"] for y in years)
    payload = {
        "total": total,
        "basis": count_basis(total, gated=True, scope_years=_scope,
                             partial_years=partial_years,
                             excluded=max(0, _all_gated - total)),
        "years": years,
        "groups": groups,
        "month_totals": month_totals,
        "scope_years": _scope,
        "partial_years": partial_years,
        # The old string named the future-date gate and stayed silent about the much
        # larger exclusion: partial calendar years, which drop ~18x more rows here.
        "source": "main.db · FIRs (complete calendar years, future-dated rows excluded)",
    }
    product_store.put_product(cache_key, payload, ttl=21600)
    return payload
