"""
Antar — re-anchor the WOW-3 demo spike (planted pattern P2) to the current week.

    python scripts/replant_p2.py --dry-run     # show the plan, change nothing
    python scripts/replant_p2.py               # apply, writing a revert file
    python scripts/replant_p2.py --revert      # put every moved row back

## What is wrong

`app/seeds/planted_patterns.py::P2` plants a Rajajinagar chain-snatching spike so the
anomaly scanner has something to find during the demo (WOW-3). The spike is **date
anchored**: `demo_week_count` cases land in "the 7 days ending now", and 13 trailing weeks
sit behind it. Once the wall clock moves past that week the spike is simply history, the
scanner stops flagging it, and `tests/test_forecast_endpoint.py` skips with a message
saying exactly this.

Measured 2026-09-25: the scanner found 4 anomalies — Dharwad MVA-fatal, Bengaluru City
narcotics, Bengaluru City theft, CID cyber — and none of them the planted pair.

## What this does, and what it deliberately does NOT do

It **moves existing rows' dates**. It does not insert anything.

That distinction matters. Inserting would push the registry past 1,000,000 and quietly
falsify a number that appears in the pitch, the model card, `PROGRESS.md`, the OKF bundle
and a drift test. Re-dating keeps the count *exactly* where every published claim says it
is, and the rows being moved are already `is_synthetic_row = 1` — seeded demo scaffolding,
not real KSP records. All 221 rows of this pair are synthetic, and the script refuses to
touch a row that is not.

Rows are drawn from the same pair OUTSIDE the 14-week window (future-dated ones first —
the seed world runs to 2026-12-28), and surplus rows inside the window are parked back
outside it. Every move is written to a revert file, so this is undoable in one command.

## After running

Re-run the scan, or just:

    python -m pytest tests/test_forecast_endpoint.py -q -k wow
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REVERT_FILE = ROOT / "docs" / "p2_replant_revert.json"

# Where surplus rows are parked: comfortably outside the scanner's 14-week window and
# inside the seeded era, so nothing lands in the real-record period.
PARK_DATE = date(2025, 6, 15)


def target_weeks() -> dict[int, int]:
    """{week_index: wanted count}, in the scanner's own indexing.

    `app/services/anomaly.py` buckets by `w = (ref_now - d).days // 7`, so w=0 is the
    current week and w=1..13 are the trailing baseline, newest first. P2 states its
    trailing counts oldest-to-newest, hence the reversal.
    """
    from app.seeds.planted_patterns import P2
    trailing = list(P2["trailing_weekly_counts"])
    want = {0: int(P2["demo_week_count"])}
    for i, n in enumerate(reversed(trailing), start=1):
        want[i] = int(n)
    return want


def week_bounds(ref_now: date, w: int) -> tuple[date, date]:
    """Inclusive date range whose rows fall in week index `w`."""
    return ref_now - timedelta(days=7 * w + 6), ref_now - timedelta(days=7 * w)


def _ref_now(con: sqlite3.Connection) -> date:
    """The scanner's reference date: min(latest row, as-of)."""
    from app.services.zcql_repo import data_today
    latest = con.execute("SELECT MAX(date) FROM FIRs WHERE date IS NOT NULL").fetchone()[0]
    latest_d = date.fromisoformat(str(latest)[:10])
    return min(latest_d, data_today())


def plan(con: sqlite3.Connection, zone: str, ctype: str) -> tuple[list[tuple], date, dict]:
    ref_now = _ref_now(con)
    want = target_weeks()

    rows = con.execute(
        "SELECT rowid, date, is_synthetic_row FROM FIRs "
        "WHERE zone = ? AND crime_type = ? ORDER BY date", (zone, ctype)).fetchall()
    if not rows:
        raise SystemExit(f"no rows for ({zone} / {ctype}) — nothing to re-plant")

    non_synth = [r for r in rows if r[2] != 1]
    if non_synth:
        raise SystemExit(
            f"refusing to move {len(non_synth)} row(s) that are not is_synthetic_row=1 — "
            "this script only re-dates seeded demo scaffolding")

    in_week: dict[int, list[int]] = {w: [] for w in want}
    outside: list[tuple[int, str]] = []
    for rowid, d, _ in rows:
        dd = date.fromisoformat(str(d)[:10])
        w = (ref_now - dd).days // 7
        if w in want and (ref_now - dd).days >= 0:
            in_week[w].append(rowid)
        else:
            outside.append((rowid, str(d)[:10]))

    # Future-dated rows are the best donors: they are seed-world padding the demo never
    # shows, and moving them removes an oddity rather than creating one.
    outside.sort(key=lambda t: (t[1] <= ref_now.isoformat(), t[1]))

    moves: list[tuple] = []          # (rowid, old_date, new_date, reason)
    donors = list(outside)
    for w in sorted(want):
        have, need = in_week[w], want[w]
        lo, hi = week_bounds(ref_now, w)
        # One counter, incremented once per move. An earlier version added the row to
        # `have` AND counted it again in the loop condition, so every week filled to half
        # its target — w0 reached 4 of 8 and the spike never crossed the threshold.
        count = len(have)
        if count > need:                          # park the surplus
            for rowid in have[need:]:
                moves.append((rowid, None, PARK_DATE.isoformat(), f"surplus in w{w}"))
            count = need
        placed = 0
        while count < need:
            if not donors:
                print(f"  ! ran out of donor rows filling w{w}", file=sys.stderr)
                break
            rowid, old = donors.pop(0)
            # The current week is packed against the END of its window, not the start.
            # `ref_now` follows the wall clock, so a row placed on day 1 of w0 drops into
            # w1 tomorrow and the spike bleeds away a row a day. Keeping them in the last
            # four days means the spike survives roughly three more days unattended —
            # enough to cover a demo, and `--dry-run` shows when it needs refreshing.
            # Trailing weeks are spread normally; nothing depends on their day pattern.
            new_date = (hi - timedelta(days=placed % 4) if w == 0
                        else lo + timedelta(days=placed % 7))
            moves.append((rowid, old, new_date.isoformat(), f"fill w{w}"))
            placed += 1
            count += 1
    return moves, ref_now, want


def apply(con: sqlite3.Connection, moves: list[tuple]) -> list[dict]:
    record = []
    for rowid, _old, new, _why in moves:
        cur = con.execute("SELECT date FROM FIRs WHERE rowid = ?", (rowid,)).fetchone()
        old_date = str(cur[0]) if cur else None
        y, m, d = new.split("-")
        con.execute(
            "UPDATE FIRs SET date = ?, FIR_YEAR = ?, FIR_MONTH = ?, FIR_Day = ? "
            "WHERE rowid = ?", (new, y, str(int(m)), str(int(d)), rowid))
        record.append({"rowid": rowid, "from": old_date, "to": new})
    con.commit()
    return record


def revert(con: sqlite3.Connection) -> int:
    if not REVERT_FILE.exists():
        raise SystemExit(f"no revert file at {REVERT_FILE}")
    data = json.loads(REVERT_FILE.read_text(encoding="utf-8"))
    n = 0
    for mv in data["moves"]:
        old = mv["from"]
        if not old:
            continue
        y, m, d = str(old)[:10].split("-")
        con.execute("UPDATE FIRs SET date = ?, FIR_YEAR = ?, FIR_MONTH = ?, FIR_Day = ? "
                    "WHERE rowid = ?", (old, y, str(int(m)), str(int(d)), mv["rowid"]))
        n += 1
    con.commit()
    REVERT_FILE.unlink()
    return n


def report(con: sqlite3.Connection, zone: str, ctype: str) -> None:
    ref_now = _ref_now(con)
    want = target_weeks()
    rows = con.execute("SELECT date FROM FIRs WHERE zone = ? AND crime_type = ?",
                       (zone, ctype)).fetchall()
    got = {w: 0 for w in want}
    for (d,) in rows:
        w = (ref_now - date.fromisoformat(str(d)[:10])).days // 7
        if w in got and w >= 0:
            got[w] += 1
    print(f"  week (ref_now = {ref_now})   want  have")
    for w in sorted(want):
        lo, hi = week_bounds(ref_now, w)
        mark = "" if got[w] == want[w] else "   <-"
        print(f"   w{w:<2} {lo}..{hi}   {want[w]:>4} {got[w]:>5}{mark}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10) + chr(10))[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    from app.core.db_path import get_db_path
    from app.seeds.planted_patterns import P2
    zone, ctype = P2["zone"], P2["crime_type"]

    con = sqlite3.connect(str(get_db_path()), timeout=30)
    try:
        if args.revert:
            n = revert(con)
            print(f"reverted {n} row date(s)")
            report(con, zone, ctype)
            return 0

        before = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        moves, ref_now, _want = plan(con, zone, ctype)
        print(f"P2 re-plant — {zone} / {ctype}, week ending {ref_now}")
        print("before:")
        report(con, zone, ctype)
        print(f"  {len(moves)} row date(s) to move")

        if args.dry_run:
            for rowid, old, new, why in moves[:12]:
                print(f"    rowid {rowid}: {old} -> {new}  ({why})")
            if len(moves) > 12:
                print(f"    … {len(moves) - 12} more")
            return 0

        record = apply(con, moves)
        REVERT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REVERT_FILE.write_text(json.dumps(
            {"zone": zone, "crime_type": ctype, "ref_now": ref_now.isoformat(),
             "moves": record}, indent=2), encoding="utf-8")

        after = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
        print("after:")
        report(con, zone, ctype)
        # The whole point of moving rather than inserting.
        print(f"  FIR count {before:,} -> {after:,} "
              f"({'unchanged' if before == after else 'CHANGED — investigate'})")
        print(f"  revert file: {REVERT_FILE.relative_to(ROOT)}")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
