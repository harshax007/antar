"""
Antar — Export FIRs to Parquet (Phase L5.1)
Reads FIRs from main_lab.db in chunks and writes an optimized columnar Parquet file.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / os.environ.get("ANTAR_DB", "main_lab.db")
SCALE_DIR = ROOT / "scale"
OUT_PARQUET = SCALE_DIR / "firs_lab.parquet"

COLUMNS = [
    "fir_id", "date", "FIR_YEAR", "FIR_MONTH", "district_norm", "zone",
    "station", "Unit_ID", "Beat_Name", "Village_Area_Name", "crime_type",
    "CrimeHead_Name", "FIR_Type", "status", "Accused_Count", "Arrested_Count_No_",
    "Accused_ChargeSheeted_Count", "Conviction_Count", "Male", "Female",
    "Boy", "Girl", "Latitude", "Longitude", "is_synthetic_row",
]

SCHEMA = pa.schema([
    ("fir_id", pa.string()),
    ("date", pa.string()),
    ("FIR_YEAR", pa.int32()),
    ("FIR_MONTH", pa.int32()),
    ("district_norm", pa.string()),
    ("zone", pa.string()),
    ("station", pa.string()),
    ("Unit_ID", pa.string()),
    ("Beat_Name", pa.string()),
    ("Village_Area_Name", pa.string()),
    ("crime_type", pa.string()),
    ("CrimeHead_Name", pa.string()),
    ("FIR_Type", pa.string()),
    ("status", pa.string()),
    ("Accused_Count", pa.int32()),
    ("Arrested_Count_No_", pa.int32()),
    ("Accused_ChargeSheeted_Count", pa.int32()),
    ("Conviction_Count", pa.int32()),
    ("Male", pa.int32()),
    ("Female", pa.int32()),
    ("Boy", pa.int32()),
    ("Girl", pa.int32()),
    ("Latitude", pa.float32()),
    ("Longitude", pa.float32()),
    ("is_synthetic_row", pa.int32()),
])


def export_firs_to_parquet(chunk_size: int = 200_000) -> Path:
    SCALE_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    total_rows = conn.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
    print(f"Exporting {total_rows:,} rows from {DB_PATH.name} to {OUT_PARQUET.name}...")

    cols_str = ", ".join(COLUMNS)
    cursor = conn.cursor()
    cursor.execute(f"SELECT {cols_str} FROM FIRs")

    writer = pq.ParquetWriter(
        str(OUT_PARQUET),
        schema=SCHEMA,
        compression="zstd",
        use_dictionary=True,
    )

    rows_written = 0
    try:
        while True:
            batch = cursor.fetchmany(chunk_size)
            if not batch:
                break

            # Convert batch rows to dict of columns
            col_data = {c: [] for c in COLUMNS}
            for row in batch:
                for idx, c in enumerate(COLUMNS):
                    val = row[idx]
                    if c in ("FIR_YEAR", "FIR_MONTH", "Accused_Count", "Arrested_Count_No_",
                            "Accused_ChargeSheeted_Count", "Conviction_Count", "Male", "Female",
                            "Boy", "Girl", "is_synthetic_row"):
                        try:
                            col_data[c].append(int(val) if val is not None and str(val).strip() != "" else 0)
                        except (ValueError, TypeError):
                            col_data[c].append(0)
                    elif c in ("Latitude", "Longitude"):
                        try:
                            col_data[c].append(float(val) if val is not None and str(val).strip() != "" else 0.0)
                        except (ValueError, TypeError):
                            col_data[c].append(0.0)
                    else:
                        col_data[c].append(str(val) if val is not None else "")

            table = pa.Table.from_pydict(col_data, schema=SCHEMA)
            writer.write_table(table, row_group_size=100_000)
            rows_written += len(batch)
            print(f"  Written {rows_written:,} / {total_rows:,} rows ({(rows_written/total_rows)*100:.1f}%)")
    finally:
        writer.close()
        conn.close()

    elapsed = round(time.perf_counter() - t0, 2)
    size_mb = round(OUT_PARQUET.stat().st_size / (1024 * 1024), 2)
    print(f"\nParquet export completed in {elapsed}s: {OUT_PARQUET} ({size_mb} MB)")
    return OUT_PARQUET


if __name__ == "__main__":
    export_firs_to_parquet()
