"""
Antar - demo-day volume: a build-up on 28 Oct 2026 and 670 FIRs on 29 Oct 2026
==============================================================================

    python scripts/demo_day_volume.py --dry-run     # show the plan, change nothing
    python scripts/demo_day_volume.py               # apply, writing docs/demo_day_volume_revert.json
    python scripts/demo_day_volume.py --revert      # put every moved row back

Like scripts/demo_week.py and scripts/replant_p2.py this MOVES the dates of existing
demonstration rows (is_synthetic_row = 1) and never inserts: the register stays at exactly
10,00,000 FIRs. A row that is not a demonstration row is refused.

Targets: 28 Oct -> 300 FIRs (the build-up), 29 Oct -> exactly 670 (demo day).
The extra rows are concentrated, so the map shows a hotspot rather than an even rise:
60% Bengaluru City, 15% Mysuru City, 10% Mangaluru City, 15% across the rest of the state.

Donors are background seed rows dated 1 Nov - 28 Dec 2026, which no screen shows before
November. Left alone: story rows (anything carrying an entity key or a story other than
the generic background ones), and the planted Rajajinagar chain-snatching pair the WOW-3
spike is built from.
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from datetime import date
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REVERT_FILE = ROOT / "docs" / "demo_day_volume_revert.json"

TARGETS = {"2026-10-28": 300, "2026-10-29": 670}
HOTSPOTS = [("Bengaluru City", 0.60), ("Mysuru City", 0.15), ("Mangaluru City", 0.10)]   # rest: statewide
DONORS = ("2026-11-01", "2026-12-28 23:59")
GENERIC_STORIES = ("", "bulk_densify", "BG", "FWD")


def _count(con, day: str) -> int:
    return con.execute("SELECT COUNT(*) FROM FIRs WHERE substr(date, 1, 10) = ?", (day,)).fetchone()[0]


def _donors(con) -> list[tuple]:
    marks = ", ".join("?" * len(GENERIC_STORIES))
    return con.execute(
        f"SELECT rowid, date, district_norm FROM FIRs WHERE is_synthetic_row = 1 AND date >= ? AND date <= ? "
        f"AND COALESCE(story_id, '') IN ({marks}) "
        f"AND NOT (zone = 'Rajajinagar' AND crime_type = 'chain_snatching') "
        f"AND id NOT IN (SELECT CaseMasterID FROM ext_entity_keys WHERE CaseMasterID IS NOT NULL)",
        (*DONORS, *GENERIC_STORIES)).fetchall()


def plan(con) -> list[tuple]:
    """[(rowid, old_date, new_date, why)]"""
    pool = _donors(con)
    random.Random(2910).shuffle(pool)                  # fixed, varied mix of stations and crimes
    by_district: dict[str, list] = {}
    for r in pool:
        by_district.setdefault(r[2], []).append(r)
    hot = {d for d, _ in HOTSPOTS}
    rest = [r for r in pool if r[2] not in hot]
    moves: list[tuple] = []
    for day, target in TARGETS.items():
        need = target - _count(con, day)
        if need <= 0:
            continue
        quota = [(d, round(need * w)) for d, w in HOTSPOTS]
        quota.append((None, need - sum(q for _, q in quota)))
        for district, q in quota:
            src = rest if district is None else by_district.get(district, [])
            for _ in range(q):
                row = src.pop() if src else (rest.pop() if rest else None)
                if row is None:
                    raise SystemExit(f"ran out of donor rows for {day}")
                moves.append((row[0], str(row[1]), day, f"{day} to {target}" + (f" ({district})" if district else "")))
    return moves


def apply(con, moves: list[tuple]) -> list[dict]:
    rec = []
    con.execute("BEGIN IMMEDIATE")
    try:
        for rowid, old, new, why in moves:
            synth = con.execute("SELECT is_synthetic_row FROM FIRs WHERE rowid = ?", (rowid,)).fetchone()
            if not synth or synth[0] != 1:
                raise SystemExit(f"refusing to move rowid {rowid}: not a demonstration row")
            y, m, d = new.split("-")
            con.execute("UPDATE FIRs SET date = ?, FIR_YEAR = ?, FIR_MONTH = ?, FIR_Day = ? WHERE rowid = ?",
                        (new, y, str(int(m)), str(int(d)), rowid))
            rec.append({"rowid": rowid, "from": old, "to": new, "why": why})
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    return rec


def revert(con) -> int:
    if not REVERT_FILE.exists():
        raise SystemExit(f"no revert file at {REVERT_FILE}")
    data = json.loads(REVERT_FILE.read_text(encoding="utf-8"))
    con.execute("BEGIN IMMEDIATE")
    for mv in data["moves"]:
        old = str(mv["from"])
        y, m, d = old[:10].split("-")
        con.execute("UPDATE FIRs SET date = ?, FIR_YEAR = ?, FIR_MONTH = ?, FIR_Day = ? WHERE rowid = ?",
                    (old, y, str(int(m)), str(int(d)), mv["rowid"]))
    con.execute("COMMIT")
    REVERT_FILE.unlink()
    return len(data["moves"])


def main() -> int:
    ap = argparse.ArgumentParser(description="Demo-day volume for 28-29 Oct 2026 (dates only).")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()
    from app.core.db_path import get_db_path
    con = sqlite3.connect(str(get_db_path()), timeout=60, isolation_level=None)
    try:
        if args.revert:
            print(f"reverted {revert(con)} row date(s)")
            return 0
        if REVERT_FILE.exists():
            raise SystemExit(f"already applied ({REVERT_FILE.name} exists): --revert first to re-plan")
        before = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        print("before:", {d: _count(con, d) for d in TARGETS})
        moves = plan(con)
        mix: dict[str, int] = {}
        for mv in moves:
            mix[mv[3]] = mix.get(mv[3], 0) + 1
        print(f"{len(moves)} row date(s) to move:")
        for k, v in sorted(mix.items()):
            print(f"  {v:4d}  {k}")
        if args.dry_run:
            return 0
        rec = apply(con, moves)
        REVERT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REVERT_FILE.write_text(json.dumps({"applied": date.today().isoformat(), "moves": rec}, indent=1), encoding="utf-8")
        after = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        print("after: ", {d: _count(con, d) for d in TARGETS})
        print(f"FIR count {before:,} -> {after:,} ({'unchanged' if before == after else 'CHANGED - investigate'})")
        print(f"revert file: {REVERT_FILE.relative_to(ROOT)}")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
