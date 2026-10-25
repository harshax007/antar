"""
Give every FIR row its own fir_id.

    python scripts/dedupe_fir_ids.py            # C00026 (Amengad PS) -> C273672 ..., everywhere
    python scripts/dedupe_fir_ids.py --revert   # put the old ids back, from the saved map

2,933 fir_ids (C00001-C05000) were each carried by two rows: a register row from
Bagalkot/Ballari (is_synthetic_row = 0, has a CrimeNo) and a seeded demo row (BLR-*, MYS-*,
... stations, no CrimeNo). Every lookup by id got both, so a Bangalore suspect's linked cases
included a Bagalkot FIR that only shared the number.

The demo rows keep their ids: crime_suspects, property, relationships and the seed files all
point at them. The register rows get fresh ids above the highest C number in use, and the
rows that belong to them follow:

    FIRs.fir_id (register row only), victims.fir_id, money_transactions.fir_id

Victims of these ids are all on the register side. Money rows follow the register row when
it carries the UPI id the money trail starts from (the demo row has none).

Deterministic (sorted by id) and done in one transaction. The mapping is written to
data/fir_id_rename_map.csv, which is what --revert reads. The audit log is NOT touched: its
rows are a hash-chained record of what was asked and answered at the time.
"""
from __future__ import annotations

import csv
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.core.db_path import DB_PATH  # noqa: E402

MAP_PATH = os.path.join(ROOT, "data", "fir_id_rename_map.csv")
C_NUM = re.compile(r"^C(\d+)$")


def build_map(con: sqlite3.Connection) -> dict[str, str]:
    """old id -> new id, for the register row of every id two rows share."""
    dups = sorted(r[0] for r in con.execute(
        "SELECT fir_id FROM FIRs GROUP BY fir_id HAVING COUNT(*) > 1 "
        "AND SUM(is_synthetic_row = 0) = 1 AND SUM(is_synthetic_row = 1) = COUNT(*) - 1"))
    taken = {r[0] for r in con.execute("SELECT DISTINCT fir_id FROM FIRs WHERE fir_id LIKE 'C%'")}
    n = max(int(m.group(1)) for m in (C_NUM.match(t) for t in taken) if m)
    out: dict[str, str] = {}
    for old in dups:
        n += 1
        while f"C{n}" in taken:
            n += 1
        out[old] = f"C{n}"
    return out


def _apply(con: sqlite3.Connection, pairs: dict[str, str], *, revert: bool = False) -> dict:
    con.execute("CREATE TEMP TABLE fir_map (old TEXT PRIMARY KEY, new TEXT NOT NULL)")
    con.executemany("INSERT INTO fir_map VALUES (?, ?)", pairs.items())
    n = {}
    if revert:
        # the new ids are unique, so the register row is the only one carrying each
        n["FIRs.fir_id"] = con.execute(
            "UPDATE FIRs SET fir_id = (SELECT old FROM fir_map WHERE new = FIRs.fir_id) "
            "WHERE fir_id IN (SELECT new FROM fir_map)").rowcount
        for t in ("victims", "money_transactions"):
            n[f"{t}.fir_id"] = con.execute(
                f"UPDATE {t} SET fir_id = (SELECT old FROM fir_map WHERE new = {t}.fir_id) "
                f"WHERE fir_id IN (SELECT new FROM fir_map)").rowcount
    else:
        # money first: which side it belongs to is read off the register row before it moves
        n["money_transactions.fir_id"] = con.execute(
            "UPDATE money_transactions SET fir_id = (SELECT new FROM fir_map WHERE old = money_transactions.fir_id) "
            "WHERE fir_id IN (SELECT old FROM fir_map) AND EXISTS (SELECT 1 FROM FIRs f "
            "WHERE f.fir_id = money_transactions.fir_id AND f.is_synthetic_row = 0 AND COALESCE(f.UPI_ID, '') <> '')"
        ).rowcount
        n["victims.fir_id"] = con.execute(
            "UPDATE victims SET fir_id = (SELECT new FROM fir_map WHERE old = victims.fir_id) "
            "WHERE fir_id IN (SELECT old FROM fir_map)").rowcount
        n["FIRs.fir_id"] = con.execute(
            "UPDATE FIRs SET fir_id = (SELECT new FROM fir_map WHERE old = FIRs.fir_id) "
            "WHERE fir_id IN (SELECT old FROM fir_map) AND is_synthetic_row = 0").rowcount
    con.execute("DROP TABLE fir_map")
    return n


def rename(db_path: str = DB_PATH, map_path: str = MAP_PATH) -> dict:
    con = sqlite3.connect(db_path, timeout=60, isolation_level=None)
    try:
        con.execute("BEGIN IMMEDIATE")
        m = build_map(con)
        if not m:
            con.execute("ROLLBACK")
            return {"renamed": 0}
        counts = _apply(con, m)
        left = con.execute("SELECT COUNT(*) FROM (SELECT fir_id FROM FIRs GROUP BY fir_id HAVING COUNT(*) > 1)").fetchone()[0]
        if left:
            raise RuntimeError(f"{left} fir_ids still shared after the rename; rolled back")
        con.execute("COMMIT")
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    os.makedirs(os.path.dirname(map_path), exist_ok=True)
    with open(map_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["old_id", "new_id"])
        w.writerows(sorted(m.items()))
    return {"renamed": len(m), **counts}


def revert(db_path: str = DB_PATH, map_path: str = MAP_PATH) -> dict:
    with open(map_path, newline="", encoding="utf-8") as f:
        m = {r["old_id"]: r["new_id"] for r in csv.DictReader(f)}
    con = sqlite3.connect(db_path, timeout=60, isolation_level=None)
    try:
        con.execute("BEGIN IMMEDIATE")
        counts = _apply(con, m, revert=True)
        con.execute("COMMIT")
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    return {"reverted": len(m), **counts}


if __name__ == "__main__":
    print(revert() if "--revert" in sys.argv[1:] else rename())
