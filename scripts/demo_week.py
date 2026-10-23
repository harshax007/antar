"""
Antar — set the register up for the demo week (23-29 Oct 2026, demo day 29 Oct)
================================================================================

    python scripts/demo_week.py --dry-run     # show every move, change nothing
    python scripts/demo_week.py               # apply, writing docs/demo_week_revert.json
    python scripts/demo_week.py --revert      # put every moved row back

Like scripts/replant_p2.py, this MOVES the dates of existing demonstration rows
(is_synthetic_row = 1) and never inserts: the register stays at exactly 10,00,000 FIRs, the
number every published claim uses. A row that is not a demonstration row is never touched.

What it fixes or sets up
------------------------
1. Month-end gap. The seeded rows put about a third of the usual FIRs on the 29th-31st of
   every month (~15 a day against ~50). On demo day, 29 Oct, the Map and Predict would read
   that as a sudden two-thirds drop. 29-31 Oct are filled to the median day of 1-28 Oct
   from December 2026 rows - seed padding no screen shows before December.
2. Three story cases made "live" this week, so the linkage works on something new:
     C3  UPI mule ring          suman68@ybl      latest case -> 27 Oct
     C4  "digital arrest" scam  103.32.58.79     latest case -> 28 Oct
     C2  chain-snatching crew   KA-06-AH-5331    latest case -> 29 Oct
   Each story's other FIRs, in other districts and months, are what Linkage then finds.

The WOW-3 spike is separate: `python scripts/replant_p2.py --anchor 2026-10-29`.
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import statistics
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
REVERT_FILE = ROOT / "docs" / "demo_week_revert.json"

FILL_DAYS = [date(2026, 10, 29), date(2026, 10, 30), date(2026, 10, 31)]
BASE = (date(2026, 10, 1), date(2026, 10, 28))         # what a normal October day looks like
DONORS = (date(2026, 12, 1), date(2026, 12, 28))       # seed padding no screen shows yet
LIVE = [  # (story, key type, key value, new date)
    ("C3", "UPI_ID", "suman68@ybl", date(2026, 10, 27)),
    ("C4", "IP_Address", "103.32.58.79", date(2026, 10, 28)),
    ("C2", "Vehicle_Reg_No", "KA-06-AH-5331", date(2026, 10, 29)),
]


def _day_counts(con, lo: date, hi: date) -> dict[str, int]:
    return dict(con.execute(
        "SELECT substr(date,1,10), COUNT(*) FROM FIRs WHERE date >= ? AND date <= ? GROUP BY 1",
        (lo.isoformat(), hi.isoformat() + " 23:59")).fetchall())


def plan(con) -> list[tuple]:
    """[(rowid, old_date, new_date, why)]"""
    moves: list[tuple] = []
    used: set[int] = set()

    # 1. month-end gap
    base = _day_counts(con, *BASE)
    target = int(statistics.median(base.values()))
    have = _day_counts(con, FILL_DAYS[0], FILL_DAYS[-1])
    donors = [r for r in con.execute(
        "SELECT rowid, date FROM FIRs WHERE is_synthetic_row = 1 AND date >= ? AND date <= ? "
        "AND (story_id IS NULL OR story_id = '' OR story_id = 'bulk_densify') "
        "AND NOT (zone = 'Rajajinagar' AND crime_type = 'chain_snatching')",
        (DONORS[0].isoformat(), DONORS[1].isoformat() + " 23:59")).fetchall()]
    random.Random(29).shuffle(donors)                  # a fixed, varied mix of districts/crimes
    for d in FILL_DAYS:
        need = max(0, target - have.get(d.isoformat(), 0))
        for _ in range(need):
            if not donors:
                print("  ! ran out of December donors", file=sys.stderr)
                break
            rowid, old = donors.pop()
            moves.append((rowid, str(old), d.isoformat(), f"fill {d.isoformat()} to {target}"))
            used.add(rowid)

    # 2. live story cases: the latest FIR carrying the story's key
    for story, ktype, kval, new in LIVE:
        row = con.execute(
            "SELECT f.rowid, f.date, f.is_synthetic_row FROM ext_entity_keys k JOIN FIRs f ON f.id = k.CaseMasterID "
            "WHERE k.story_id = ? AND k.key_type = ? AND k.key_value = ? ORDER BY f.date DESC LIMIT 1",
            (story, ktype, kval)).fetchone()
        if not row:
            print(f"  ! no FIR found for {story} {kval}", file=sys.stderr)
            continue
        if row[2] != 1:
            raise SystemExit(f"refusing: {story} row {row[0]} is not a demonstration row")
        moves.append((row[0], str(row[1]), new.isoformat(), f"{story} live case ({kval})"))
    return moves


def apply(con, moves: list[tuple]) -> list[dict]:
    rec = []
    for rowid, old, new, why in moves:
        synth = con.execute("SELECT is_synthetic_row FROM FIRs WHERE rowid = ?", (rowid,)).fetchone()
        if not synth or synth[0] != 1:
            raise SystemExit(f"refusing to move rowid {rowid}: not a demonstration row")
        y, m, d = new.split("-")
        con.execute("UPDATE FIRs SET date = ?, FIR_YEAR = ?, FIR_MONTH = ?, FIR_Day = ? WHERE rowid = ?",
                    (new, y, str(int(m)), str(int(d)), rowid))
        rec.append({"rowid": rowid, "from": old, "to": new, "why": why})
    con.commit()
    return rec


def revert(con) -> int:
    if not REVERT_FILE.exists():
        raise SystemExit(f"no revert file at {REVERT_FILE}")
    data = json.loads(REVERT_FILE.read_text(encoding="utf-8"))
    for mv in data["moves"]:
        old = str(mv["from"])
        y, m, d = old[:10].split("-")
        con.execute("UPDATE FIRs SET date = ?, FIR_YEAR = ?, FIR_MONTH = ?, FIR_Day = ? WHERE rowid = ?",
                    (old, y, str(int(m)), str(int(d)), mv["rowid"]))
    con.commit()
    REVERT_FILE.unlink()
    return len(data["moves"])


def main() -> int:
    ap = argparse.ArgumentParser(description="Set the register up for the 29 Oct 2026 demo (dates only).")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()
    from app.core.db_path import get_db_path
    con = sqlite3.connect(str(get_db_path()), timeout=30)
    try:
        if args.revert:
            print(f"reverted {revert(con)} row date(s)")
            return 0
        if REVERT_FILE.exists():
            raise SystemExit(f"already applied ({REVERT_FILE.name} exists): --revert first to re-plan")
        before = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        print("days 26-31 Oct before:", _day_counts(con, date(2026, 10, 26), date(2026, 10, 31)))
        moves = plan(con)
        print(f"{len(moves)} row date(s) to move")
        for mv in [m for m in moves if "live case" in m[3]] + moves[:5]:
            print(f"  rowid {mv[0]}: {mv[1][:10]} -> {mv[2]}  ({mv[3]})")
        if args.dry_run:
            return 0
        rec = apply(con, moves)
        REVERT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REVERT_FILE.write_text(json.dumps({"applied": date.today().isoformat(), "moves": rec}, indent=1), encoding="utf-8")
        after = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        print("days 26-31 Oct after: ", _day_counts(con, date(2026, 10, 26), date(2026, 10, 31)))
        print(f"FIR count {before:,} -> {after:,} ({'unchanged' if before == after else 'CHANGED - investigate'})")
        print(f"revert file: {REVERT_FILE.relative_to(ROOT)}")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
