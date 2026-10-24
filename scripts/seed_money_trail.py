"""
Build the money-trail layer: accounts and transactions behind the UPI IDs on FIRs.

    python scripts/seed_money_trail.py            # (re)build money_accounts, money_transactions

Deterministic (fixed seed) and idempotent: both tables are dropped and rebuilt, nothing else
in the database is touched. Every row carries source='seeded' so the layer can be told
apart from the register, or removed, with one query.

Shape of a trail, the pattern financial-crime units describe for UPI fraud:

    complainant's account --(payment, on or just before the FIR date)--> UPI on the FIR
      --(within hours: most of it moved on)--> another UPI in the same ring
      --> a collector account --> a named suspect (from financial_links) / cash withdrawal

Rings are the UPI IDs that share an accused or a district on the FIRs, so a trail follows
the links the register already has. No date is later than today.
"""
from __future__ import annotations

import hashlib
import os
import random
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.db_path import DB_PATH  # noqa: E402

SEED = 20261024
BANKS = ["oksbi", "okhdfcbank", "okicici", "okaxis", "ybl", "paytm", "ibl", "upi"]
CHANNELS_IN = ["UPI", "UPI", "UPI", "IMPS", "NEFT"]
SCHEMA = """
DROP TABLE IF EXISTS money_transactions;
DROP TABLE IF EXISTS money_accounts;
CREATE TABLE money_accounts (
    account_id   TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,      -- upi | complainant | collector | suspect | cash
    label        TEXT,
    district     TEXT,
    bank         TEXT,
    suspect_id   TEXT,
    source       TEXT NOT NULL DEFAULT 'seeded'
);
CREATE TABLE money_transactions (
    txn_id        TEXT PRIMARY KEY,
    ts            TEXT NOT NULL,     -- ISO date-time
    from_account  TEXT NOT NULL,
    to_account    TEXT NOT NULL,
    amount_inr    INTEGER NOT NULL,
    channel       TEXT NOT NULL,
    purpose       TEXT NOT NULL,     -- payment | layering | collection | payout | cash_withdrawal
    fir_id        TEXT,              -- the FIR the money relates to, when there is one
    source        TEXT NOT NULL DEFAULT 'seeded'
);
CREATE INDEX idx_money_tx_from ON money_transactions(from_account);
CREATE INDEX idx_money_tx_to ON money_transactions(to_account);
CREATE INDEX idx_money_tx_fir ON money_transactions(fir_id);
"""


def _h(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()


def _ts(d: date, rnd: random.Random, hours_after: float = 0.0) -> str:
    base = datetime(d.year, d.month, d.day, rnd.randint(7, 21), rnd.randint(0, 59))
    t = base + timedelta(hours=hours_after)
    cap = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=23, minutes=59)
    return min(t, cap).isoformat(timespec="minutes")


def _amount(rnd: random.Random, head: str) -> int:
    h = (head or "").upper()
    if "CYBER" in h or "CHEAT" in h or "FRAUD" in h:
        base = rnd.choice([4999, 9999, 14999, 24999, 49000, 49999, 75000, 120000, 199999])
    else:
        base = rnd.choice([2000, 5000, 8000, 12000, 20000, 35000, 49500])
    return max(500, int(base * rnd.uniform(0.85, 1.0)))


def build(con: sqlite3.Connection) -> dict:
    rnd = random.Random(SEED)
    today = date.today().isoformat()
    con.executescript(SCHEMA)
    firs = con.execute(
        "SELECT fir_id, TRIM(UPI_ID), COALESCE(district_norm, District_Name), SUBSTR(date, 1, 10), "
        "COALESCE(CrimeHead_Name, CrimeGroup_Name, crime_type), COALESCE(Accused_ID, '') FROM FIRs "
        "WHERE COALESCE(UPI_ID, '') <> '' AND date <= ? ORDER BY fir_id", (today,)).fetchall()
    links = con.execute("SELECT suspect_id, counterparty, CAST(txn_count AS INTEGER), amount_band, flag_reason "
                        "FROM financial_links ORDER BY link_id").fetchall()

    accounts: dict[str, tuple] = {}
    txns: list[tuple] = []

    def acct(aid, kind, label, district=None, bank=None, suspect_id=None):
        if aid not in accounts:
            accounts[aid] = (aid, kind, label, district, bank, suspect_id, "seeded")

    def tx(ts, a, b, amt, channel, purpose, fir=None):
        txns.append((f"TX-{_h(ts, a, b, amt, len(txns))[:12].upper()}", ts, a, b, int(amt), channel, purpose, fir, "seeded"))

    # rings: UPI IDs joined by a shared accused, else by district
    by_upi = defaultdict(list)
    for f in firs:
        by_upi[f[1]].append(f)
    parent = {u: u for u in by_upi}

    def find(u):
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u

    by_acc = defaultdict(set)
    for u, fs in by_upi.items():
        for f in fs:
            if f[5]:
                by_acc[f[5]].add(u)
    for us in by_acc.values():
        us = sorted(us)
        for u in us[1:]:
            parent[find(u)] = find(us[0])
    rings = defaultdict(list)
    for u in sorted(by_upi):
        rings[find(u)].append(u)
    # small rings in one district are joined up to 3-6 accounts, as mule rings run
    by_district = defaultdict(list)
    for root, members in sorted(rings.items()):
        d = by_upi[members[0]][0][2]
        by_district[d].append(members)
    final_rings = []
    for d, groups in sorted(by_district.items()):
        cur = []
        for g in groups:
            cur += g
            if len(cur) >= rnd.randint(3, 6):
                final_rings.append((d, cur))
                cur = []
        if cur:
            if final_rings and final_rings[-1][0] == d:
                final_rings[-1][1].extend(cur)
            else:
                final_rings.append((d, cur))

    # collectors, and the named suspects behind them (financial_links)
    suspects = [l for l in links]
    for i, (district, members) in enumerate(final_rings):
        col = f"COL-{_h('collector', district, i)[:6].upper()}"
        acct(col, "collector", f"Collector account · {district}", district, rnd.choice(["SBI", "Canara", "HDFC", "ICICI", "Axis"]))
        cash = f"CASH-{_h('atm', district)[:5].upper()}"
        acct(cash, "cash", f"Cash withdrawals · {district}", district)
        sus = suspects[i % len(suspects)] if suspects else None
        for u in members:
            acct(u, "upi", u, district, u.split("@")[-1] if "@" in u else None)
        for u in members:
            for (fir, upi, d, fdate, head, accused) in by_upi[u]:
                try:
                    fd = date.fromisoformat(fdate)
                except ValueError:
                    continue
                # the complainant(s) paid in on, or a day or two before, the FIR date
                for k in range(rnd.choice([1, 1, 2, 3])):
                    payer = f"cust.{_h('cmp', fir, k)[:7]}@{rnd.choice(BANKS)}"
                    acct(payer, "complainant", f"Complainant's account · FIR {fir}", d, payer.split("@")[1])
                    pay_day = fd - timedelta(days=rnd.choice([0, 0, 1, 2]))
                    amt = _amount(rnd, head)
                    t0 = _ts(pay_day, rnd)
                    tx(t0, payer, u, amt, rnd.choice(CHANNELS_IN), "payment", fir)
                    # within hours most of it moves on: to another ring member, or the collector
                    nxt = [m for m in members if m != u]
                    hop = rnd.choice(nxt) if nxt and rnd.random() < 0.6 else col
                    out = int(amt * rnd.uniform(0.82, 0.97))
                    t1 = _ts(pay_day, rnd, hours_after=rnd.uniform(0.3, 20))
                    tx(max(t0, t1), u, hop, out, "UPI", "layering" if hop != col else "collection", fir)
                    if hop != col:
                        out2 = int(out * rnd.uniform(0.9, 0.99))
                        t2 = _ts(pay_day, rnd, hours_after=rnd.uniform(20, 46))
                        tx(max(t1, t2), hop, col, out2, "IMPS", "collection", fir)
        # the collector pays out: cash, and the suspect behind the ring
        inflow = sum(t[4] for t in txns if t[3] == col)
        if inflow:
            last = max(t[1] for t in txns if t[3] == col)
            ld = date.fromisoformat(last[:10])
            tx(_ts(ld, rnd, hours_after=rnd.uniform(4, 30)), col, cash, int(inflow * rnd.uniform(0.35, 0.55)), "ATM", "cash_withdrawal")
            if sus:
                sid, cp, n, band, flag = sus
                acct(sid, "suspect", f"Suspect {sid}", district, None, sid)
                acct(cp, "collector", f"Account {cp} · {flag.replace('_', ' ')}", district, None)
                tx(_ts(ld, rnd, hours_after=rnd.uniform(6, 40)), col, cp, int(inflow * rnd.uniform(0.25, 0.4)), "NEFT", "payout")
                tx(_ts(ld, rnd, hours_after=rnd.uniform(40, 80)), cp, sid, int(inflow * rnd.uniform(0.15, 0.25)), "IMPS", "payout")

    # the remaining financial_links: suspect <-> counterparty, txn_count times, within the band
    band_rng = {"<10k": (1500, 9999), "10k-50k": (10000, 49999), "50k-1L": (50000, 99999), ">1L": (100000, 400000)}
    end = date.today()
    for sid, cp, n, band, flag in links:
        acct(sid, "suspect", f"Suspect {sid}", None, None, sid)
        acct(cp, "collector", f"Account {cp} · {str(flag).replace('_', ' ')}", None, None)
        lo, hi = band_rng.get(str(band), (5000, 50000))
        for k in range(max(1, min(int(n or 1), 20))):
            d = end - timedelta(days=rnd.randint(5, 360))
            a, b = (cp, sid) if rnd.random() < 0.7 else (sid, cp)
            tx(_ts(d, rnd), a, b, rnd.randint(lo, hi), rnd.choice(["UPI", "IMPS", "NEFT"]), "payout")

    con.executemany("INSERT INTO money_accounts VALUES (?,?,?,?,?,?,?)", accounts.values())
    con.executemany("INSERT INTO money_transactions VALUES (?,?,?,?,?,?,?,?,?)", txns)
    con.commit()
    return {"accounts": len(accounts), "transactions": len(txns), "rings": len(final_rings)}


if __name__ == "__main__":
    con = sqlite3.connect(DB_PATH, timeout=60)
    try:
        print(build(con))
    finally:
        con.close()
