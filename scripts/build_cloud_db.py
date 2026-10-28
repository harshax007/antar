"""
Antar - build the database the Cloud image ships
================================================

    python scripts/build_cloud_db.py                 # writes D:\\Project_Antar\\main.db.gz
    python scripts/build_cloud_db.py --out DIR       # somewhere else
    python scripts/build_cloud_db.py --keep-db       # also keep the uncompressed copy
    python scripts/build_cloud_db.py --slim          # the build that fits AppSail's disk

The register holds demonstration rows dated up to 31 Dec 2026. A FIR dated after today is
something a reader spots at once, and about twenty modules read the FIRs table directly, so
capping each query is fragile. In the Cloud copy the table is renamed FIRs_all and FIRs
becomes a view of the rows dated up to today, India time. SQLite evaluates the view on
every query, so on demo day that day's FIRs appear without a rebuild.

The view carries a real `rowid` column, which the change checks (MAX(rowid)) read. Every
row and every index is kept: the indexes live on FIRs_all and serve the view unchanged.

The working main.db is only read, never changed. The demo scripts that re-date rows by
rowid (demo_week, replant_p2, demo_day_volume) keep working there.

--slim: AppSail's disk is capped at 1024 MB and the full register expands to 1.6 GB, so
the Cloud copy keeps FIRs from SLIM_FROM on (the demo rows of 2025-26 included) and drops
the 2023 SYN duplicates, with the victims rows of the FIRs it drops. Every index is kept,
so the rows that remain are served as fast as before. Forecast tables are left whole: they
were computed over the full register, and Predict reads only them. The laptop keeps
everything.
"""
from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "main.db"
DEFAULT_OUT = Path(r"D:\Project_Antar")

# Rows dated up to the end of today in India (UTC + 5:30), whatever the server's zone.
TODAY_VIEW = (
    "CREATE VIEW FIRs AS SELECT rowid AS rowid, * FROM FIRs_all "
    "WHERE date < date('now', '+330 minutes', '+1 day')"
)


SLIM_FROM = "2022-01-01"
SLIM_DROP = f"date < '{SLIM_FROM}' OR (fir_id LIKE 'SYN%' AND date LIKE '2023%')"


def slim(con: sqlite3.Connection) -> None:
    t0 = time.time()
    con.execute(f"CREATE TEMP TABLE dropped AS SELECT fir_id FROM FIRs WHERE {SLIM_DROP}")
    con.execute("CREATE INDEX temp.ix_dropped ON dropped(fir_id)")
    victims = con.execute("DELETE FROM victims WHERE fir_id IN (SELECT fir_id FROM dropped)").rowcount
    firs = con.execute(f"DELETE FROM FIRs WHERE {SLIM_DROP}").rowcount
    con.execute("DROP TABLE IF EXISTS fir_geo_original")    # cleaning history, read only by scripts
    con.execute("DROP TABLE dropped")
    # Read by app/agents/self_heal.py: a question about an earlier period is told what
    # this copy holds instead of being answered from other years.
    con.execute("CREATE TABLE IF NOT EXISTS register_meta (key TEXT PRIMARY KEY, value TEXT)")
    con.execute("INSERT OR REPLACE INTO register_meta VALUES ('covers_from', ?)", (SLIM_FROM,))
    con.commit()
    print(f"slim: dropped {firs:,} FIRs and {victims:,} victims rows ({time.time() - t0:.0f}s)")
    t1 = time.time()
    con.execute("VACUUM")
    print(f"slim: vacuumed ({time.time() - t1:.0f}s)")


def forwarding_triggers(con: sqlite3.Connection) -> list[str]:
    """A view refuses writes, and ingestion (zcql_local, POST /api/admin/ingest) inserts into
    FIRs. These pass every insert, update and delete through to FIRs_all."""
    cols = [f'"{r[1]}"' for r in con.execute("PRAGMA table_info(FIRs_all)")]
    names, new = ", ".join(cols), ", ".join(f"NEW.{c}" for c in cols)
    sets = ", ".join(f"{c} = NEW.{c}" for c in cols)
    return [
        f"CREATE TRIGGER FIRs_insert INSTEAD OF INSERT ON FIRs BEGIN "
        f"INSERT INTO FIRs_all ({names}) VALUES ({new}); END",
        f"CREATE TRIGGER FIRs_update INSTEAD OF UPDATE ON FIRs BEGIN "
        f"UPDATE FIRs_all SET {sets} WHERE rowid = OLD.rowid; END",
        "CREATE TRIGGER FIRs_delete INSTEAD OF DELETE ON FIRs BEGIN "
        "DELETE FROM FIRs_all WHERE rowid = OLD.rowid; END",
    ]


def build(out_dir: Path, keep_db: bool, slim_rows: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # VACUUM writes a temporary copy of the whole database to TEMP, which on this laptop
    # is C: and nearly full. Keep it on the output drive.
    os.environ["TMP"] = os.environ["TEMP"] = str(out_dir)
    db = out_dir / "main.db.build"
    for stale in (db, Path(f"{db}-wal"), Path(f"{db}-shm"), Path(f"{db}-journal")):
        if stale.exists():
            stale.unlink()

    t0 = time.time()
    src = sqlite3.connect(f"file:{SOURCE}?mode=ro", uri=True)
    total = src.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
    src.execute("VACUUM INTO ?", (str(db),))
    src.close()
    print(f"copied {SOURCE.name}: {total:,} FIRs, {db.stat().st_size / 1048576:.0f} MB ({time.time() - t0:.0f}s)")

    con = sqlite3.connect(db)
    try:
        if slim_rows:
            slim(con)
            total = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        crimes_sql = con.execute("SELECT sql FROM sqlite_master WHERE name = 'crimes'").fetchone()
        con.execute("DROP VIEW IF EXISTS crimes")
        con.execute("ALTER TABLE FIRs RENAME TO FIRs_all")
        con.execute(TODAY_VIEW)
        for sql in forwarding_triggers(con):
            con.execute(sql)
        if crimes_sql:
            con.execute(crimes_sql[0])          # unchanged text: it reads FIRs, now the view
        # The view's row count moves every day, which the forecast store reads as a changed
        # register and refits for: a child process of ~1 GB, on the rows this copy holds.
        # Serve the forecasts fitted on the full register instead (app/forecast/store.py).
        con.execute("INSERT OR REPLACE INTO forecast_meta (key, value) "
                    "SELECT 'frozen_signature', value FROM forecast_meta WHERE key = 'signature'")
        con.commit()

        kept = con.execute("SELECT COUNT(*) FROM FIRs_all").fetchone()[0]
        shown = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        newest = con.execute("SELECT MAX(date) FROM FIRs").fetchone()[0]
        top = con.execute("SELECT MAX(rowid) FROM FIRs").fetchone()[0]
        if kept != total:
            raise SystemExit(f"row count changed: {total:,} -> {kept:,}")
        print(f"FIRs_all {kept:,} rows; FIRs (up to today, IST) {shown:,} rows, newest {newest}, max rowid {top}")
        plan = " ".join(r[3] for r in con.execute(
            "EXPLAIN QUERY PLAN SELECT zone, COUNT(*) FROM crimes WHERE TRIM(UPPER(zone)) = 'BENGALURU CITY' GROUP BY zone"))
        print(f"query plan through the view: {plan}")
        con.execute("PRAGMA journal_mode=DELETE")    # a single file; staging switches it to WAL
    finally:
        con.close()

    gz = out_dir / "main.db.gz"
    tmp = out_dir / "main.db.gz.tmp"
    t1 = time.time()
    with open(db, "rb") as f_in, gzip.open(tmp, "wb", 6) as f_out:
        shutil.copyfileobj(f_in, f_out, 8 * 1024 * 1024)
    os.replace(tmp, gz)
    print(f"wrote {gz} ({gz.stat().st_size / 1048576:.0f} MB, {time.time() - t1:.0f}s); "
          f"expands to {db.stat().st_size / 1048576:.0f} MB")
    if keep_db:
        os.replace(db, out_dir / "main.db.cloud")
        print(f"kept {out_dir / 'main.db.cloud'}")
    else:
        db.unlink()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the Cloud image's database.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--keep-db", action="store_true")
    ap.add_argument("--slim", action="store_true", help=f"keep FIRs from {SLIM_FROM} on (fits 1024 MB)")
    args = ap.parse_args()
    if not SOURCE.exists():
        raise SystemExit(f"no {SOURCE}")
    build(args.out, args.keep_db, args.slim)
    return 0


if __name__ == "__main__":
    sys.exit(main())
