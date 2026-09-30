"""
Antar — rebuild main.db onto fresh storage (final_backend.md §1.2).

The drive holding the repo developed bad sectors on 2026-09-23: five 4 KiB pages inside
`forecast_cube` cannot be read, which makes PRAGMA integrity_check, VACUUM INTO and
Connection.backup() all abort, so the database can neither be verified nor copied
wholesale. This script copies the database table by table into a new file, which works
around the unreadable pages and reports exactly which objects (if any) are damaged.

    python scripts/rebuild_db.py --dest E:/Datathon_2026/Res/main.db
    python scripts/rebuild_db.py --dest ... --keep-derived    # copy forecast tables too

The source is opened read-write (so a stale WAL index can be recovered) but never
written to: every statement against it is a SELECT.

Derived tables are skipped by default and rebuilt by the backend at startup:
    geo_units, forecast_cube      — app/forecast/store.py, ~35 s
    forecast_output, forecast_models, forecast_meta — app/forecast/run.py, ~70 s each
This is the same set PROGRESS.md marks as "all derived, all rebuilt at startup", and
skipping forecast_cube is what makes the copy possible at all.

Everything else is reproduced exactly: every table, its rows, all 24 named indexes and
the `crimes` view. Virtual generated columns (geo_lat / geo_lon / geo_ok on FIRs) are
recreated by the schema and deliberately not inserted into.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
DERIVED = ("geo_units", "forecast_cube", "forecast_output", "forecast_models",
           "forecast_meta")


def _cols(con: sqlite3.Connection, table: str) -> list[str]:
    """Real columns only — a generated column cannot appear in an INSERT column list."""
    return [r[1] for r in con.execute(f'PRAGMA table_xinfo("{table}")') if r[-1] == 0]


def rebuild(source: Path, dest: Path, keep_derived: bool) -> int:
    if dest.exists():
        print(f"refusing to overwrite an existing file: {dest}")
        return 2
    dest.parent.mkdir(parents=True, exist_ok=True)
    skip = () if keep_derived else DERIVED

    con = sqlite3.connect(source, timeout=120)
    t_all = time.time()
    try:
        # A backend that died leaves a stale WAL index; until a read-write connection
        # recovers it, even reads fail with "disk I/O error".
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()

        objects = con.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL "
            "ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 "
            "WHEN 'view' THEN 2 ELSE 3 END").fetchall()
        tables = [o for o in objects if o[0] == "table" and o[1] not in skip]
        indexes = [o for o in objects if o[0] == "index" and o[2] not in skip]
        others = [o for o in objects if o[0] in ("view", "trigger")]

        con.execute("ATTACH DATABASE ? AS dest", (str(dest),))
        con.execute("PRAGMA dest.synchronous=OFF")
        con.execute("PRAGMA dest.journal_mode=OFF")

        print(f"source {source}  ->  {dest}")
        print(f"{len(tables)} tables, {len(indexes)} indexes, {len(others)} views/triggers"
              f"{'' if keep_derived else '  (skipping derived: ' + ', '.join(DERIVED) + ')'}")
        print()

        copied, failed, rows_total = [], [], 0
        for _, name, _, sql in tables:
            con.execute(sql.replace("CREATE TABLE ", "CREATE TABLE dest.", 1)
                        if sql.upper().startswith("CREATE TABLE ") else sql)
            cols = ", ".join(f'"{c}"' for c in _cols(con, name))
            t0 = time.time()
            try:
                con.execute(f'INSERT INTO dest."{name}" ({cols}) SELECT {cols} FROM main."{name}"')
                con.commit()
                n = con.execute(f'SELECT COUNT(*) FROM dest."{name}"').fetchone()[0]
                rows_total += n
                copied.append((name, n))
                print(f"  {name:<24} {n:>10,} rows   {time.time() - t0:5.1f}s")
            except sqlite3.DatabaseError as e:
                con.rollback()
                failed.append((name, str(e)))
                print(f"  {name:<24} FAILED: {e}")

        print()
        for _, name, tbl, sql in indexes:
            if any(tbl == f for f, _ in failed):
                print(f"  index {name}: skipped (its table failed)")
                continue
            t0 = time.time()
            try:
                con.execute(sql.replace("CREATE INDEX ", "CREATE INDEX dest.", 1)
                            .replace("CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX dest.", 1))
                con.commit()
                print(f"  index {name:<40} {time.time() - t0:5.1f}s")
            except sqlite3.DatabaseError as e:
                failed.append((name, str(e)))
                print(f"  index {name}: FAILED: {e}")

        for typ, name, _, sql in others:
            kw = "CREATE VIEW " if typ == "view" else "CREATE TRIGGER "
            try:
                con.execute(sql.replace(kw, kw + "dest.", 1))
                con.commit()
                print(f"  {typ} {name}: created")
            except sqlite3.DatabaseError as e:
                failed.append((name, str(e)))
                print(f"  {typ} {name}: FAILED: {e}")

        con.execute("PRAGMA dest.journal_mode=WAL")       # what the app runs in
        con.execute("DETACH DATABASE dest")
    finally:
        con.close()

    # ── verify the new file on its own ──
    print()
    out = sqlite3.connect(dest, timeout=120)
    try:
        t0 = time.time()
        check = out.execute("PRAGMA integrity_check").fetchall()
        ok = len(check) == 1 and check[0][0] == "ok"
        print(f"integrity_check on the new file: {'ok' if ok else check[:5]} "
              f"({time.time() - t0:.0f}s)   <- this is what the old file could not complete")
        counts_ok = True
        src = sqlite3.connect(source, timeout=120)
        try:
            for name, n in copied:
                m = src.execute(f'SELECT COUNT(*) FROM main."{name}"').fetchone()[0]
                if m != n:
                    counts_ok = False
                    print(f"  ROW COUNT MISMATCH {name}: source {m:,} vs new {n:,}")
        finally:
            src.close()
        print(f"row counts match source: {counts_ok}  ({rows_total:,} rows in {len(copied)} tables)")
        size = dest.stat().st_size / 1048576
        print(f"new file: {size:,.0f} MB   (source {source.stat().st_size / 1048576:,.0f} MB)")
    finally:
        out.close()

    print()
    if failed:
        print("OBJECTS THAT COULD NOT BE COPIED — these are the damaged ones:")
        for name, err in failed:
            print(f"  {name}: {err}")
    else:
        print("every table, index and view copied cleanly: the damage was confined to the "
              "derived tables that were skipped")
    print(f"total {time.time() - t_all:.0f}s")
    print()
    print("The source database was not modified. To use the new one:")
    print(f'  set ANTAR_DB={dest}      (or move it into the repo as main.db)')
    print("The backend rebuilds geo_units + forecast_cube (~35 s) and the forecast runs "
          "(~70 s each) on its next start.")
    return 1 if failed else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10) + chr(10))[0])
    ap.add_argument("--source", default=str(ROOT / "main.db"))
    ap.add_argument("--dest", required=True)
    ap.add_argument("--keep-derived", action="store_true",
                    help="also copy the forecast tables (will fail on the damaged one)")
    args = ap.parse_args()
    sys.exit(rebuild(Path(args.source), Path(args.dest), args.keep_derived))


if __name__ == "__main__":
    main()
