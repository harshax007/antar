"""
Give the placeholder UPI ids on the register realistic names.

    python scripts/rename_upi_ids.py            # user1050@bank -> ravi.gowda82@okaxis, everywhere
    python scripts/rename_upi_ids.py --revert   # put the old ids back, from the saved map

The synthetic FIRs carried UPI ids like `user1050@bank`. They read as test data on the
Money trail. This renames each one to a name-style id with a real UPI handle, and sets the
account's label to the holder's name, in every place the id is stored:

    FIRs.UPI_ID, money_accounts.account_id / label / bank,
    money_transactions.from_account / to_account

Deterministic (the same id always gets the same name) and done in one transaction. The
mapping is written to data/upi_rename_map.csv, which is what --revert reads. The audit log
is NOT touched: its rows are a hash-chained record of what was asked and answered at the
time, and rewriting them would break the chain.
"""
from __future__ import annotations

import csv
import hashlib
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.core.db_path import DB_PATH  # noqa: E402

MAP_PATH = os.path.join(ROOT, "data", "upi_rename_map.csv")
OLD_RE = re.compile(r"^user\d+@bank$")

FIRST = ["Ravi", "Suresh", "Mahesh", "Prakash", "Manjunath", "Naveen", "Kiran", "Santosh", "Raghu", "Vinod",
         "Harish", "Girish", "Shivakumar", "Basavaraj", "Mallikarjun", "Anil", "Sunil", "Praveen", "Deepak", "Arun",
         "Lakshmi", "Kavya", "Shwetha", "Pooja", "Divya", "Rekha", "Sudha", "Asha", "Meena", "Bhavya",
         "Nagaraj", "Chethan", "Yogesh", "Sachin", "Vijay", "Ramesh", "Umesh", "Dinesh", "Lokesh", "Sharath",
         "Anitha", "Sowmya", "Ranjitha", "Nandini", "Shruthi", "Veena", "Geetha", "Pavithra", "Rashmi", "Sindhu"]
LAST = ["Gowda", "Shetty", "Rao", "Hegde", "Naik", "Patil", "Kulkarni", "Reddy", "Murthy", "Bhat",
        "Kumar", "Prasad", "Shankar", "Swamy", "Desai", "Hiremath", "Pai", "Kamath", "Nayak", "Achar"]
HANDLES = ["oksbi", "okhdfcbank", "okicici", "okaxis", "ybl", "paytm", "ibl", "axl"]
HANDLE_BANK = {"oksbi": "SBI", "okhdfcbank": "HDFC Bank", "okicici": "ICICI Bank", "okaxis": "Axis Bank",
               "ybl": "PhonePe", "paytm": "Paytm", "ibl": "IndusInd Bank", "axl": "Axis Bank"}


def _pick(seq, key: str, salt: str):
    h = int(hashlib.sha256(f"{salt}:{key}".encode()).hexdigest(), 16)
    return seq[h % len(seq)], h


def build_map(old_ids: list[str], taken: set[str]) -> dict[str, tuple[str, str, str]]:
    """old id -> (new id, holder name, bank). Unique, and never an id already in use."""
    out: dict[str, tuple[str, str, str]] = {}
    used = set(taken)
    for old in sorted(old_ids):
        first, _ = _pick(FIRST, old, "first")
        last, _ = _pick(LAST, old, "last")
        handle, h = _pick(HANDLES, old, "handle")
        n = h % 90 + 10
        while True:
            new = f"{first.lower()}.{last.lower()}{n}@{handle}"
            if new not in used:
                break
            n = n + 1 if n < 99 else 10
        used.add(new)
        out[old] = (new, f"{first} {last}", HANDLE_BANK[handle])
    return out


def _apply(con: sqlite3.Connection, pairs: dict[str, str], labels: dict[str, tuple[str, str]]) -> dict:
    con.execute("CREATE TEMP TABLE upi_map (old TEXT PRIMARY KEY, new TEXT NOT NULL)")
    con.executemany("INSERT INTO upi_map VALUES (?, ?)", pairs.items())
    n = {}
    n["FIRs.UPI_ID"] = con.execute(
        "UPDATE FIRs SET UPI_ID = (SELECT new FROM upi_map WHERE old = FIRs.UPI_ID) "
        "WHERE UPI_ID IN (SELECT old FROM upi_map)").rowcount
    n["money_transactions.from_account"] = con.execute(
        "UPDATE money_transactions SET from_account = (SELECT new FROM upi_map WHERE old = from_account) "
        "WHERE from_account IN (SELECT old FROM upi_map)").rowcount
    n["money_transactions.to_account"] = con.execute(
        "UPDATE money_transactions SET to_account = (SELECT new FROM upi_map WHERE old = to_account) "
        "WHERE to_account IN (SELECT old FROM upi_map)").rowcount
    n["money_accounts"] = 0
    for old, new in pairs.items():
        label, bank = labels[old]
        n["money_accounts"] += con.execute("UPDATE money_accounts SET account_id = ?, label = ?, bank = ? WHERE account_id = ?",
                                           (new, label, bank, old)).rowcount
    con.execute("DROP TABLE upi_map")
    return n


def rename(db_path: str = DB_PATH, map_path: str = MAP_PATH) -> dict:
    con = sqlite3.connect(db_path, timeout=60, isolation_level=None)
    try:
        olds = {r[0] for r in con.execute("SELECT DISTINCT UPI_ID FROM FIRs WHERE UPI_ID LIKE 'user%@bank'")}
        olds |= {r[0] for r in con.execute("SELECT account_id FROM money_accounts WHERE account_id LIKE 'user%@bank'")}
        olds = {o for o in olds if o and OLD_RE.match(o)}
        if not olds:
            return {"renamed": 0}
        taken = {r[0] for r in con.execute("SELECT account_id FROM money_accounts")}
        taken |= {r[0] for r in con.execute("SELECT DISTINCT UPI_ID FROM FIRs WHERE UPI_ID IS NOT NULL AND UPI_ID <> ''")}
        m = build_map(sorted(olds), taken)
        con.execute("BEGIN IMMEDIATE")
        counts = _apply(con, {o: v[0] for o, v in m.items()}, {o: (v[1], v[2]) for o, v in m.items()})
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
        w.writerow(["old_id", "new_id", "holder", "bank"])
        for old, (new, holder, bank) in sorted(m.items()):
            w.writerow([old, new, holder, bank])
    return {"renamed": len(m), **counts}


def revert(db_path: str = DB_PATH, map_path: str = MAP_PATH) -> dict:
    with open(map_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    pairs = {r["new_id"]: r["old_id"] for r in rows}
    labels = {r["new_id"]: (r["old_id"], "bank") for r in rows}
    con = sqlite3.connect(db_path, timeout=60, isolation_level=None)
    try:
        con.execute("BEGIN IMMEDIATE")
        counts = _apply(con, pairs, labels)
        con.execute("COMMIT")
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    return {"reverted": len(pairs), **counts}


if __name__ == "__main__":
    print(revert() if "--revert" in sys.argv else rename())
