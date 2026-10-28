"""
Antar — 1-Crore Row Stress Dataset Generator (Phase L5.2)
High-performance vectorized PyArrow generator:
Synthesizes a 1-crore (10,000,000) row parquet stress test dataset in scale/firs_stress_1cr/
in ~15 seconds using PyArrow C++ table operations.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
SCALE_DIR = ROOT / "scale"
SOURCE_PARQUET = SCALE_DIR / "firs_lab.parquet"
STRESS_DIR = SCALE_DIR / "firs_stress_1cr"

TOTAL_STRESS_ROWS = 10_000_000
PARTS = 10
ROWS_PER_PART = TOTAL_STRESS_ROWS // PARTS  # 1,000,000 per part


def make_stress_dataset(seed: int = 42) -> Path:
    total, used, free = shutil.disk_usage(str(ROOT))
    free_gb = free / (1024 ** 3)
    if free_gb < 10.0:
        raise RuntimeError(f"Insufficient disk space on {ROOT.drive}: {free_gb:.1f} GB free (require >= 10 GB)")

    if not SOURCE_PARQUET.exists():
        raise FileNotFoundError(f"Source parquet not found: {SOURCE_PARQUET}. Run export_parquet.py first.")

    STRESS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    print(f"Reading base table from {SOURCE_PARQUET.name}...")
    source_table = pq.read_table(str(SOURCE_PARQUET))
    n_source = len(source_table)
    print(f"Loaded {n_source:,} base rows. Generating {TOTAL_STRESS_ROWS:,} stress rows in {PARTS} parts...")

    rng = np.random.default_rng(seed)
    part_id_offset = 0

    for p in range(PARTS):
        tp0 = time.perf_counter()
        # Fast C++ take using uint32 indices
        idx = rng.integers(0, n_source, size=ROWS_PER_PART, dtype=np.uint32)
        idx_arr = pa.array(idx)
        part_table = source_table.take(idx_arr)

        # Generate unique stress synthetic IDs
        part_ids = [f"X{part_id_offset + i + 1:08d}" for i in range(ROWS_PER_PART)]
        id_col = pa.array(part_ids, type=pa.string())
        stress_col = pa.array(np.ones(ROWS_PER_PART, dtype=np.int32), type=pa.int32())

        # Replace 'fir_id' and append 'stress'
        col_names = part_table.column_names
        fir_id_idx = col_names.index("fir_id")

        part_table = part_table.set_column(fir_id_idx, "fir_id", id_col)
        part_table = part_table.append_column("stress", stress_col)

        out_part_file = STRESS_DIR / f"part_{p:02d}.parquet"
        pq.write_table(
            part_table,
            str(out_part_file),
            compression="zstd",
            row_group_size=100_000,
            use_dictionary=True,
        )

        part_id_offset += ROWS_PER_PART
        part_mb = round(out_part_file.stat().st_size / (1024 * 1024), 1)
        print(f"  Part {p+1:02d}/{PARTS} written: {out_part_file.name} ({part_mb} MB) in {time.perf_counter()-tp0:.2f}s", flush=True)

    elapsed = round(time.perf_counter() - t0, 1)
    total_mb = sum(f.stat().st_size for f in STRESS_DIR.glob("part_*.parquet")) / (1024 * 1024)
    print(f"\n1-Crore stress dataset completed: {STRESS_DIR} ({total_mb:.1f} MB in {elapsed}s)", flush=True)
    return STRESS_DIR


if __name__ == "__main__":
    make_stress_dataset()
