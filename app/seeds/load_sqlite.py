"""
Antar — Seed Loader for SQLite (antar.db)
=========================================
Loads JSON seed files from app/seeds/out/ into the local SQLite database (antar.db).
This completes the synthetic data pipeline (TRAIN.md Step 3), aligning the local DB
with the generated named-suspect world.

Usage:
  python -m app.seeds.load_sqlite
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.db_path import DB_PATH as _DBP
DB_PATH = Path(_DBP)
OUT_DIR = Path(__file__).parent / "out"


def load_into_sqlite(db_path: Path = DB_PATH, out_dir: Path = OUT_DIR) -> None:
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return
    if not out_dir.exists():
        print(f"❌ Seeds directory not found at {out_dir}")
        return

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    tables = [
        "suspects",
        "relationships",
        "crime_suspects",
        "financial_links",
        "victims",
        "property",
        "stations",
        "officers",
    ]
    print(f"🌱 Loading seed JSONs from {out_dir} into {db_path.name} ...\n")

    for table in tables:
        json_path = out_dir / f"{table}.json"
        if not json_path.exists():
            print(f"  ⚠️  Skipping {table}: {json_path.name} not found")
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        if not records:
            print(f"  ⚠️  Skipping {table}: empty JSON")
            continue

        # Get column names from SQLite pragma
        cur.execute(f"PRAGMA table_info({table})")
        cols_info = cur.fetchall()
        if not cols_info:
            print(f"  ⚠️  Skipping {table}: table does not exist in DB")
            continue

        cols = [c[1] for c in cols_info]
        placeholders = ",".join(["?"] * len(cols))

        # Clear old table
        cur.execute(f"DELETE FROM {table}")

        # Build rows
        rows = []
        for r in records:
            rows.append([str(r.get(c, "")) if r.get(c) is not None else "" for c in cols])

        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
        cur.executemany(sql, rows)
        conn.commit()
        print(f"  ✅ Loaded {len(rows):>6} rows -> {table:<16}")

    # ── Update FIRs table with synthetic crimes ──
    crimes_path = out_dir / "crimes.json"
    if crimes_path.exists():
        with open(crimes_path, "r", encoding="utf-8") as f:
            crimes = json.load(f)
        if crimes:
            cids = [str(r.get("crime_id")) for r in crimes if r.get("crime_id")]
            if cids:
                placeholders_cids = ",".join(["?"] * len(cids))
                cur.execute(f"DELETE FROM FIRs WHERE fir_id IN ({placeholders_cids})", cids)
                conn.commit()
            conn.close()
            from app.services.zcql_local import insert_crimes
            insert_crimes(crimes)
            print(f"  ✅ Updated {len(crimes):>6} rows -> FIRs (crimes view)")
    else:
        conn.close()

    print("\n🎯 SQLite database enrichment complete!")


if __name__ == "__main__":
    load_into_sqlite()
