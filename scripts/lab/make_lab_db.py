"""
make_lab_db.py — Create main_lab.db from main.db for Antar Lab build (Phase L0.2).

Copies main.db (opened read-only) into main_lab.db using SQLite's online backup API.
Falls back to scripts/rebuild_db.py if backup encounters unreadable pages.
Never modifies main.db.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

# Ensure UTF-8 output
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SRC = ROOT / "main.db"
DEFAULT_DST = ROOT / "main_lab.db"


def make_lab_db(source: Path = DEFAULT_SRC, dest: Path = DEFAULT_DST, force: bool = False) -> int:
    if not source.exists():
        print(f"Error: Source database does not exist: {source}", file=sys.stderr)
        return 1

    if dest.exists():
        if not force:
            print(f"Refusing to overwrite existing {dest} without --force", file=sys.stderr)
            return 2
        print(f"Removing existing {dest} (--force specified)...")
        dest.unlink()

    src_mtime_before = source.stat().st_mtime
    t0 = time.time()
    print(f"Backing up {source.name} -> {dest.name} using SQLite Online Backup API...")

    backup_success = False
    try:
        # Open source in read-only mode via URI
        src_uri = f"file:{source.as_posix()}?mode=ro"
        src_conn = sqlite3.connect(src_uri, uri=True, timeout=60.0)
        dst_conn = sqlite3.connect(str(dest), timeout=60.0)

        # Optimize destination PRAGMAs for speed during creation
        dst_conn.execute("PRAGMA synchronous = OFF")
        dst_conn.execute("PRAGMA journal_mode = OFF")

        def progress(status, remaining, total):
            done = total - remaining
            pct = (done / total * 100) if total > 0 else 100
            print(f"\r  Pages: {done:,} / {total:,} ({pct:5.1f}%)", end="", flush=True)

        src_conn.backup(dst_conn, pages=4096, progress=progress)
        print()  # newline after progress
        dst_conn.close()
        src_conn.close()
        backup_success = True
        print(f"Online backup completed in {time.time() - t0:.2f}s")
    except sqlite3.DatabaseError as exc:
        print(f"\nOnline backup failed: {exc}")
        print("Falling back to table-by-table rebuild via scripts.rebuild_db...")
        if dest.exists():
            dest.unlink()
        from scripts.rebuild_db import rebuild
        code = rebuild(source=source, dest=dest, keep_derived=False)
        if code != 0:
            print("Fallback rebuild failed!", file=sys.stderr)
            return code
        backup_success = True

    # Check source mtime unchanged
    src_mtime_after = source.stat().st_mtime
    if src_mtime_before != src_mtime_after:
        print("WARNING: Source database mtime changed! This violates Rule R4.", file=sys.stderr)

    # Acceptance verification
    check_conn = sqlite3.connect(f"file:{dest.as_posix()}?mode=ro", uri=True)
    count = check_conn.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
    max_id = check_conn.execute("SELECT MAX(id) FROM FIRs").fetchone()[0]
    check_conn.close()

    print(f"\nVerification on {dest.name}:")
    print(f"  SELECT COUNT(*) FROM FIRs = {count:,} (Expected: 1,000,000)")
    print(f"  SELECT MAX(id) FROM FIRs   = {max_id:,} (Expected: 1,526,329)")

    if count == 1_000_000 and max_id == 1_526_329:
        print("\nPhase L0.2 Acceptance Passed!")
        return 0
    else:
        print("\nPhase L0.2 Acceptance Failed: counts do not match expected values.", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Create main_lab.db from main.db using SQLite backup API")
    parser.add_argument("--source", type=Path, default=DEFAULT_SRC, help="Source database (default: main.db)")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DST, help="Destination database (default: main_lab.db)")
    parser.add_argument("--force", action="store_true", help="Overwrite destination if it exists")
    args = parser.parse_args()

    sys.exit(make_lab_db(source=args.source, dest=args.dest, force=args.force))


if __name__ == "__main__":
    main()
