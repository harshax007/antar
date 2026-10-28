"""
topup_firs.py — Expand main_lab.db to ~19 lakh real FIR records (Phase L1.2).

Ingests E:\Datathon_2026\03_resources\FIR_Details_Data.csv insert-only into main_lab.db:
- Deduplicates within the extract (exact dups and signature dups)
- Cross-register deduplication against existing real rows in main_lab.db
- Validates dates (2016-01-01 to 2024-03-31) and required fields
- Derives sequential ids ('K' + id), CaseNo, CrimeNo, cognizable flag
- Dry run writes docs/lab/TOPUP_REPORT.md and pauses for owner review
- Apply mode inserts in batches of 50,000, updates fir_geo_clean and lab_loads
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from app.services.fir_clean import (
    canonical_stage,
    clean_coords,
    parse_act_section,
    signature,
    _norm_field,
)

# Ensure UTF-8 output
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_CSV = Path(r"E:\Datathon_2026\03_resources\FIR_Details_Data.csv")
DEFAULT_DB = ROOT / "main_lab.db"

NON_COGNIZABLE = {"MISSING PERSON", "FAILURE TO APPEAR TO COURT", "CRPC"}

# file spelling -> DB column name
_COL_MAP = {
    "District_Name": "District_Name",
    "UnitName": "UnitName",
    "FIR_YEAR": "FIR_YEAR",
    "FIR_MONTH": "FIR_MONTH",
    "Offence_Duration": "Offence_Duration",
    "FIR_Day": "FIR_Day",
    "FIR Type": "FIR_Type",
    "FIR_Stage": "FIR_Stage",
    "Complaint_Mode": "Complaint_Mode",
    "CrimeGroup_Name": "CrimeGroup_Name",
    "CrimeHead_Name": "CrimeHead_Name",
    "Latitude": "Latitude",
    "Longitude": "Longitude",
    "ActSection": "ActSection",
    "IOName": "IOName",
    "KGID": "KGID",
    "Internal_IO": "Internal_IO",
    "Place of Offence": "Place_of_Offence",
    "Distance from PS": "Distance_from_PS",
    "Beat_Name": "Beat_Name",
    "Village_Area_Name": "Village_Area_Name",
    "Male": "Male",
    "Female": "Female",
    "Boy": "Boy",
    "Girl": "Girl",
    "Age 0": "Age_0",
    "VICTIM COUNT": "VICTIM_COUNT",
    "Accused Count": "Accused_Count",
    "Arrested Male": "Arrested_Male",
    "Arrested Female": "Arrested_Female",
    "Arrested Count\tNo.": "Arrested_Count_No_",
    "Arrested Count No.": "Arrested_Count_No_",
    "Accused_ChargeSheeted Count": "Accused_ChargeSheeted_Count",
    "Conviction Count": "Conviction_Count",
    "Unit_ID": "Unit_ID",
}

_SIG_FIELDS = [
    "District_Name", "UnitName", "FIR_YEAR", "FIR_MONTH", "FIR_Day", "FIR_Type",
    "CrimeGroup_Name", "CrimeHead_Name", "KGID", "Beat_Name", "Village_Area_Name",
    "Accused_Count", "Place_of_Offence"
]


def _get_insert_cols(con: sqlite3.Connection) -> list[str]:
    """Retrieve all writable (non-generated) columns for FIRs."""
    return [r[1] for r in con.execute('PRAGMA table_xinfo("FIRs")') if r[-1] == 0]


def run_topup(
    csv_path: Path = DEFAULT_CSV,
    db_path: Path = DEFAULT_DB,
    dry_run: bool = True,
    limit: int | None = None,
    batch_size: int = 50000,
    force_main: bool = False,
) -> int:
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t_start = time.time()

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr, flush=True)
        return 1

    if db_path.name.lower() == "main.db" and not force_main:
        print("Refusing to run top-up directly on main.db without --force-main (violates Rule R4)!", file=sys.stderr, flush=True)
        return 2

    if not db_path.exists():
        print(f"Error: Database file not found: {db_path}", file=sys.stderr, flush=True)
        return 1

    print(f"{'=== DRY RUN MODE ===' if dry_run else '=== APPLY MODE ==='}", flush=True)
    print(f"Source CSV : {csv_path}", flush=True)
    print(f"Target DB  : {db_path}", flush=True)

    # Compute CSV SHA-256 for provenance
    print("\n[1/7] Computing CSV SHA-256...", flush=True)
    h = hashlib.sha256()
    with open(csv_path, "rb") as f:
        while chunk := f.read(2 * 1024 * 1024):
            h.update(chunk)
    csv_sha256 = h.hexdigest()
    print(f"  CSV SHA-256: {csv_sha256}", flush=True)

    # Read CSV
    print("\n[2/7] Reading CSV...", flush=True)
    try:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8")
    except UnicodeDecodeError:
        print("  Warning: utf-8 decode failed; falling back to latin-1", flush=True)
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="latin-1")

    rows_read = len(df)
    print(f"  Read {rows_read:,} rows from CSV", flush=True)

    # Normalize column names
    col_rename = {}
    for c in df.columns:
        norm_c = c.strip()
        if c in _COL_MAP:
            col_rename[c] = _COL_MAP[c]
        elif norm_c in _COL_MAP:
            col_rename[c] = _COL_MAP[norm_c]
        else:
            col_rename[c] = norm_c.replace(" ", "_").replace("\t", "_").replace(".", "_")
    df.rename(columns=col_rename, inplace=True)
    if "Offence_Duration" in df.columns:
        df.drop(columns=["Offence_Duration"], inplace=True)

    if limit and limit > 0:
        print(f"  Limiting to first {limit:,} rows for test run", flush=True)
        df = df.iloc[:limit].copy()

    # Intra-extract deduplication
    print("\n[3/7] Deduplicating within extract...", flush=True)
    # Exact duplicate rows
    initial_len = len(df)
    df.drop_duplicates(inplace=True)
    exact_dups = initial_len - len(df)
    print(f"  Dropped {exact_dups:,} exact intra-extract duplicate rows (Remaining: {len(df):,})", flush=True)

    # High-performance signature generation using itertuples
    print("  Computing SHA-1 signatures for extract rows...", flush=True)
    t0_sig = time.time()
    tuples = df[_SIG_FIELDS].itertuples(index=False, name=None)
    signatures = [
        hashlib.sha1(
            "|".join(_norm_field(v, is_int=(i in (2, 3, 4, 11))) for i, v in enumerate(t)).encode("utf-8")
        ).hexdigest()
        for t in tuples
    ]
    df["_sig"] = signatures
    print(f"  Signatures computed in {time.time() - t0_sig:.1f}s", flush=True)

    before_sig_dedup = len(df)
    df.drop_duplicates(subset=["_sig"], keep="first", inplace=True)
    sig_dups_extract = before_sig_dedup - len(df)
    print(f"  Dropped {sig_dups_extract:,} signature intra-extract duplicate rows (Remaining: {len(df):,})", flush=True)

    # Cross-register deduplication against main_lab.db
    print("\n[4/7] Cross-register deduplicating against database...", flush=True)
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    sig_fields = list(_SIG_FIELDS) + ["fir_id"]
    query = f"SELECT {', '.join(sig_fields)} FROM FIRs WHERE is_synthetic_row = 0"
    print("  Streaming existing real rows from database...", flush=True)
    cur = con.execute(query)

    existing_sigs: set[str] = set()
    k_rows_matched = 0
    k_rows_total = 0

    while True:
        rows = cur.fetchmany(100000)
        if not rows:
            break
        for r in rows:
            row_dict = dict(zip(sig_fields, r))
            s = signature(row_dict)
            existing_sigs.add(s)
            if str(row_dict.get("fir_id", "")).startswith("K"):
                k_rows_total += 1

    con.close()
    print(f"  Loaded {len(existing_sigs):,} distinct signatures from database (Existing K-rows: {k_rows_total:,})", flush=True)

    # Check match count of extract rows against existing DB signatures
    extract_sigs = set(df["_sig"])
    matched_existing_count = len(extract_sigs.intersection(existing_sigs))
    print(f"  Extract signatures matching existing DB rows: {matched_existing_count:,}", flush=True)

    if k_rows_total > 500000 and matched_existing_count < 500000 and not limit:
        print(f"WARNING: Matched existing count {matched_existing_count:,} is significantly below expected ~5.75L!", file=sys.stderr, flush=True)

    # Filter out records already in DB
    df = df[~df["_sig"].isin(existing_sigs)].copy()
    print(f"  New candidate records to evaluate: {len(df):,}", flush=True)

    # High-performance validation and filtering
    print("\n[5/7] Validating candidate records...", flush=True)
    refusal_reasons = Counter()
    passed_rows = []

    # Columns required for validation
    val_cols = ["District_Name", "UnitName", "CrimeGroup_Name", "FIR_YEAR", "FIR_MONTH", "FIR_Day"]
    all_cols = [c for c in df.columns if c != "_sig"]

    records = df.to_dict("records")
    for row in records:
        dist = str(row.get("District_Name") or "").strip()
        unit = str(row.get("UnitName") or "").strip()
        grp = str(row.get("CrimeGroup_Name") or "").strip()

        if not dist or dist.lower() == "nan":
            refusal_reasons["missing_District_Name"] += 1
            continue
        if not unit or unit.lower() == "nan":
            refusal_reasons["missing_UnitName"] += 1
            continue
        if not grp or grp.lower() == "nan":
            refusal_reasons["missing_CrimeGroup_Name"] += 1
            continue

        try:
            yr = int(float(str(row.get("FIR_YEAR") or "").strip()))
            mo = int(float(str(row.get("FIR_MONTH") or "").strip()))
            dy = int(float(str(row.get("FIR_Day") or "").strip()))
            row_date = datetime.date(yr, mo, dy)
        except Exception:
            refusal_reasons["invalid_date_format"] += 1
            continue

        if row_date < datetime.date(2016, 1, 1):
            refusal_reasons["date_before_2016"] += 1
            continue
        if row_date > datetime.date(2024, 3, 31):
            refusal_reasons["date_after_2024_03_31"] += 1
            continue

        passed_rows.append((row_date, row))

    total_refused = sum(refusal_reasons.values())
    print(f"  Passed validation : {len(passed_rows):,} rows", flush=True)
    print(f"  Refused           : {total_refused:,} rows", flush=True)
    for reason, cnt in refusal_reasons.items():
        print(f"    - {reason}: {cnt:,}", flush=True)

    # Sort passed rows by date to ensure proper chronological id and CaseNo derivation
    passed_rows.sort(key=lambda x: x[0])

    # Metadata analysis for report
    coord_reasons = Counter()
    by_year = Counter()
    by_district = Counter()

    for r_date, row in passed_rows:
        by_year[r_date.year] += 1
        by_district[str(row.get("District_Name") or "").strip()] += 1
        _, _, reason = clean_coords(row.get("Latitude"), row.get("Longitude"))
        coord_reasons[reason] += 1

    # Fetch max id and CaseNo sequences from DB
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    max_id = con.execute("SELECT MAX(id) FROM FIRs").fetchone()[0] or 0
    try:
        max_upload_id = con.execute("SELECT MAX(CAST(SUBSTR(fir_id, 2) AS INTEGER)) FROM upload_rows").fetchone()[0] or 0
    except Exception:
        max_upload_id = 0
    next_id = max(max_id, max_upload_id) + 1

    print("\n[6/7] Computing CaseNo sequences per (Unit_ID, Year)...", flush=True)
    case_serials: dict[tuple[str, int], int] = {}
    for uid_val, yr_val, max_case in con.execute(
        "SELECT CAST(Unit_ID AS TEXT), FIR_YEAR, MAX(CAST(CaseNo AS INTEGER)) FROM FIRs WHERE Unit_ID IS NOT NULL GROUP BY 1, 2"
    ).fetchall():
        try:
            y = int(float(yr_val))
            max_c = int(max_case) if max_case is not None else y * 100000
            serial = max(0, max_c - (y * 100000))
            case_serials[(str(uid_val), y)] = serial
        except Exception:
            pass

    writable_cols = _get_insert_cols(con)
    con.close()

    print(f"  Starting id: {next_id:,} (first fir_id: 'K{next_id}')", flush=True)

    # Build row dictionaries
    first_id = next_id
    last_id = next_id + len(passed_rows) - 1 if passed_rows else next_id

    rows_to_insert = []
    current_id = next_id

    for r_date, row in passed_rows:
        yr = r_date.year
        mo = r_date.month
        dy = r_date.day

        fir_id_str = f"K{current_id}"
        uid_raw = str(row.get("Unit_ID") or "").strip()
        try:
            uid_int = int(float(uid_raw))
            uid_str = str(uid_int)
        except Exception:
            uid_int = 0
            uid_str = "0"

        # Increment serial per (Unit_ID, Year)
        key = (uid_str, yr)
        cur_serial = case_serials.get(key, 0) + 1
        case_serials[key] = cur_serial

        case_no = f"{yr * 100000 + cur_serial}"
        crime_no = f"10001{uid_str}{case_no}"

        crime_grp = str(row.get("CrimeGroup_Name") or "").strip()
        is_cog = 0 if crime_grp.upper() in NON_COGNIZABLE else 1

        dist_val = str(row.get("District_Name") or "").strip()
        unit_val = str(row.get("UnitName") or "").strip()
        stage_val = str(row.get("FIR_Stage") or "").strip()

        conv_cnt = None
        try:
            if row.get("Conviction_Count"):
                conv_cnt = int(float(str(row.get("Conviction_Count")).strip()))
        except Exception:
            pass

        record = {
            "id": current_id,
            "fir_id": fir_id_str,
            "CrimeNo": crime_no,
            "CaseNo": case_no,
            "District_Name": dist_val,
            "UnitName": unit_val,
            "FIR_YEAR": str(yr),
            "FIR_MONTH": str(mo),
            "FIR_Day": str(dy),
            "FIR_Type": str(row.get("FIR_Type") or "").strip(),
            "FIR_Stage": stage_val,
            "Complaint_Mode": str(row.get("Complaint_Mode") or "").strip(),
            "CrimeGroup_Name": crime_grp,
            "CrimeHead_Name": str(row.get("CrimeHead_Name") or "").strip(),
            "Latitude": row.get("Latitude"),
            "Longitude": row.get("Longitude"),
            "ActSection": str(row.get("ActSection") or "").strip(),
            "IOName": str(row.get("IOName") or "").strip(),
            "KGID": str(row.get("KGID") or "").strip(),
            "Internal_IO": str(row.get("Internal_IO") or "").strip(),
            "Place_of_Offence": str(row.get("Place_of_Offence") or "").strip(),
            "Distance_from_PS": str(row.get("Distance_from_PS") or "").strip(),
            "Beat_Name": str(row.get("Beat_Name") or "").strip(),
            "Village_Area_Name": str(row.get("Village_Area_Name") or "").strip(),
            "Male": str(row.get("Male") or "0").strip(),
            "Female": str(row.get("Female") or "0").strip(),
            "Boy": str(row.get("Boy") or "0").strip(),
            "Girl": str(row.get("Girl") or "0").strip(),
            "Age_0": str(row.get("Age_0") or "0").strip(),
            "VICTIM_COUNT": str(row.get("VICTIM_COUNT") or "0").strip(),
            "Accused_Count": str(row.get("Accused_Count") or "0").strip(),
            "Arrested_Male": str(row.get("Arrested_Male") or "0").strip(),
            "Arrested_Female": str(row.get("Arrested_Female") or "0").strip(),
            "Arrested_Count_No_": str(row.get("Arrested_Count_No_") or "0").strip(),
            "Accused_ChargeSheeted_Count": str(row.get("Accused_ChargeSheeted_Count") or "0").strip(),
            "Conviction_Count": conv_cnt,
            "Unit_ID": uid_int if uid_int else None,
            "zone": dist_val,
            "station": unit_val,
            "date": r_date.isoformat(),
            "crime_type": crime_grp,
            "status": stage_val,
            "district_norm": dist_val,
            "is_cognizable": is_cog,
            "is_synthetic_row": 0,
            "has_synthetic_link": 0,
            # Null fields for K-rows
            "location_lat": None,
            "location_lon": None,
            "lat_r": None,
            "lon_r": None,
            "Vehicle_Reg_No": None,
            "UPI_ID": None,
            "IP_Address": None,
            "Accused_ID": None,
            "MO_Details": None,
            "story_id": None,
        }

        row_tuple = tuple(record.get(col) for col in writable_cols)
        rows_to_insert.append(row_tuple)
        current_id += 1

    # Generate Top-Up Report (docs/lab/TOPUP_REPORT.md)
    report_dir = ROOT / "docs" / "lab"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "TOPUP_REPORT.md"

    print("\n[7/7] Generating TOPUP_REPORT.md...", flush=True)
    report_md = f"""# Antar Lab: FIR Top-Up Ingestion Report

Generated at: {started_at}
CSV Source: `{csv_path}`
CSV SHA-256: `{csv_sha256}`
Target Database: `{db_path.name}`

## 1. Executive Summary

| Metric | Count |
|---|---|
| Total Raw CSV Rows Read | **{rows_read:,}** |
| Exact Intra-Extract Duplicates Dropped | {exact_dups:,} |
| Signature Intra-Extract Duplicates Dropped | {sig_dups_extract:,} |
| Pre-Existing Register Rows Matched (Excluded) | {matched_existing_count:,} |
| Refused Rows (Validation Failed) | {total_refused:,} |
| **New Clean Real FIR Rows to Add** | **{len(rows_to_insert):,}** |
| Projected Total Database Size | **{1000000 + len(rows_to_insert):,}** |
| First Assigned ID | `K{first_id}` |
| Last Assigned ID | `K{last_id}` |

## 2. Refusal Breakdown
"""
    if refusal_reasons:
        for r_name, r_cnt in sorted(refusal_reasons.items(), key=lambda x: -x[1]):
            report_md += f"- **{r_name}**: {r_cnt:,}\n"
    else:
        report_md += "None (all clean rows passed validation)\n"

    report_md += "\n## 3. Rows to Add by Year\n\n| Year | Rows Added |\n|---|---|\n"
    for yr in sorted(by_year.keys()):
        report_md += f"| {yr} | {by_year[yr]:,} |\n"

    report_md += "\n## 4. Coordinate Quality Breakdown\n\n| Classification | Count | Pct |\n|---|---|---|\n"
    total_coord = sum(coord_reasons.values()) or 1
    for r_cls, r_cnt in coord_reasons.most_common():
        pct = (r_cnt / total_coord) * 100
        report_md += f"| `{r_cls}` | {r_cnt:,} | {pct:.1f}% |\n"

    report_md += "\n## 5. Top 15 Districts by Added Volume\n\n| District | Rows Added |\n|---|---|\n"
    for dist_name, dist_cnt in by_district.most_common(15):
        report_md += f"| {dist_name} | {dist_cnt:,} |\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"  Report written to: {report_path}", flush=True)

    if dry_run:
        print("\n" + "=" * 60, flush=True)
        print("DRY RUN COMPLETE — NO CHANGES WRITTEN TO DATABASE", flush=True)
        print(f"Rows ready to add: {len(rows_to_insert):,}", flush=True)
        print(f"Review the report at: {report_path}", flush=True)
        print("Run with --apply to execute write operations.", flush=True)
        print("=" * 60, flush=True)
        return 0

    # Apply Mode
    print("\n" + "=" * 60, flush=True)
    print("APPLY MODE: Writing to main_lab.db...", flush=True)
    print("=" * 60, flush=True)

    con = sqlite3.connect(str(db_path), timeout=300.0)
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous = OFF")
    con.execute("PRAGMA cache_size = -1000000")

    cols_str = ", ".join(f'"{c}"' for c in writable_cols)
    placeholders = ", ".join("?" for _ in writable_cols)
    insert_sql = f'INSERT INTO FIRs ({cols_str}) VALUES ({placeholders})'

    total_to_insert = len(rows_to_insert)
    inserted = 0
    t_insert_start = time.time()

    for i in range(0, total_to_insert, batch_size):
        batch = rows_to_insert[i:i + batch_size]
        t0 = time.time()
        con.execute("BEGIN TRANSACTION")
        con.executemany(insert_sql, batch)
        con.commit()
        inserted += len(batch)
        rate = len(batch) / max(0.001, time.time() - t0)
        print(f"  Inserted batch: {inserted:,} / {total_to_insert:,} ({rate:,.0f} rows/s)", flush=True)

    print(f"\nAll {inserted:,} rows inserted in {time.time() - t_insert_start:.1f}s", flush=True)

    # Side table: fir_geo_clean
    print("\nPopulating side table fir_geo_clean for all rows...", flush=True)
    con.execute("""
    CREATE TABLE IF NOT EXISTS fir_geo_clean (
        fir_id TEXT PRIMARY KEY,
        lat REAL,
        lon REAL,
        reason TEXT
    )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS ix_fir_geo_clean_reason ON fir_geo_clean(reason)")

    print("  Computing coordinates for all FIRs...", flush=True)
    geo_rows = []
    for fid, lat_val, lon_val in con.execute("SELECT fir_id, Latitude, Longitude FROM FIRs"):
        c_lat, c_lon, reason = clean_coords(lat_val, lon_val)
        geo_rows.append((fid, c_lat, c_lon, reason))

    con.execute("BEGIN TRANSACTION")
    con.execute("DELETE FROM fir_geo_clean")
    con.executemany("INSERT INTO fir_geo_clean VALUES (?, ?, ?, ?)", geo_rows)
    con.commit()
    print(f"  fir_geo_clean populated with {len(geo_rows):,} rows", flush=True)

    # Load record: lab_loads
    finished_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    load_id = f"LOAD-{int(time.time())}"
    con.execute("""
    CREATE TABLE IF NOT EXISTS lab_loads (
        load_id TEXT PRIMARY KEY,
        started_at TEXT,
        finished_at TEXT,
        csv_sha256 TEXT,
        rows_added INTEGER,
        first_id INTEGER,
        last_id INTEGER,
        signature_fields TEXT,
        report_path TEXT
    )
    """)
    sig_fields_json = json.dumps(_SIG_FIELDS)
    con.execute(
        "INSERT INTO lab_loads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (load_id, started_at, finished_at, csv_sha256, inserted, first_id, last_id, sig_fields_json, str(report_path))
    )
    con.commit()

    # Re-enable full safety pragmas and optimize
    print("\nOptimizing database and analyzing statistics...", flush=True)
    con.execute("PRAGMA synchronous = FULL")
    con.execute("ANALYZE")
    con.execute("PRAGMA optimize")
    con.close()

    total_time = time.time() - t_start
    print(f"\nTop-up apply finished successfully in {total_time:.1f}s ({total_time / 60:.1f}m)", flush=True)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Expand main_lab.db to ~19 lakh real FIR records")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to extract CSV")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Target SQLite database (default: main_lab.db)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=True, help="Simulate and write report (default ON)")
    parser.add_argument("--apply", dest="dry_run", action="store_false", help="Apply changes to the database")
    parser.add_argument("--limit", type=int, default=None, help="Limit rows for testing")
    parser.add_argument("--batch", type=int, default=50000, help="Batch size for insertion")
    parser.add_argument("--force-main", action="store_true", help="Allow running on main.db (normally forbidden)")

    args = parser.parse_args()
    sys.exit(run_topup(
        csv_path=args.csv,
        db_path=args.db,
        dry_run=args.dry_run,
        limit=args.limit,
        batch_size=args.batch,
        force_main=args.force_main,
    ))


if __name__ == "__main__":
    main()
