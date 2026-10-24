"""
Antar - money trail
===================
Follows money between accounts: who paid whom, how fast it moved on, where it ended, and the
FIRs each account is named in. Reads money_accounts / money_transactions (built by
scripts/seed_money_trail.py) and the FIRs' UPI IDs. Deterministic: every flag is a rule over
counted transactions, stated in words beside the numbers that tripped it.

Flags, each a pattern financial-crime units look for:

  fan_in         money from many different accounts into one (a collection point)
  pass_through   most of what came in left again within 48 hours (a mule)
  near_limit     repeated amounts just under Rs 50,000, where extra checks start
  many_firs      the account is named in FIRs, in more than one district
  cash_out       large cash withdrawals soon after money arrived
"""
from __future__ import annotations

import sqlite3
import threading
import time
from collections import defaultdict
from datetime import datetime

from app.core.db_path import DB_PATH, registry_connect

FAN_IN_MIN = 5
PASS_THROUGH = 0.8
NEAR_LIMIT = (45000, 49999)


def _con() -> sqlite3.Connection:
    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def available() -> bool:
    try:
        con = _con()
        try:
            return con.execute("SELECT 1 FROM sqlite_master WHERE name = 'money_transactions'").fetchone() is not None
        finally:
            con.close()
    except sqlite3.Error:
        return False


def _hours(a: str, b: str) -> float:
    try:
        return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 3600
    except ValueError:
        return 1e9


# The layer is small (thousands of rows) and changes only when it is rebuilt, but the FIRs'
# UPI_ID column has no index: looking an account's FIRs up one by one scanned 10 lakh rows each
# time (83 s for the overview). One read, kept for a few minutes, answers every question.
_SNAP_TTL_S = 600
_snap: dict | None = None
_snap_at = 0.0
_snap_lock = threading.Lock()


def _snapshot() -> dict:
    global _snap, _snap_at
    with _snap_lock:
        if _snap is not None and time.time() - _snap_at < _SNAP_TTL_S:
            return _snap
        con = _con()
        try:
            accounts = {r["account_id"]: dict(r) for r in con.execute("SELECT * FROM money_accounts")}
            txns = [dict(r) for r in con.execute("SELECT * FROM money_transactions ORDER BY ts")]
            firs = defaultdict(list)
            for r in con.execute(
                    "SELECT TRIM(UPI_ID) AS u, fir_id, SUBSTR(date, 1, 10) AS d, "
                    "COALESCE(district_norm, District_Name) AS district, COALESCE(CrimeHead_Name, crime_type) AS head, "
                    "FIR_Stage, Accused_ID FROM FIRs WHERE COALESCE(UPI_ID, '') <> '' "
                    "AND date <= date('now','localtime') ORDER BY date DESC"):
                firs[r["u"]].append({"fir_id": r["fir_id"], "date": r["d"], "district": r["district"], "crime": r["head"],
                                     "stage": " ".join(str(r["FIR_Stage"] or "").replace("_", " ").split()).title(), "accused_id": r["Accused_ID"] or None})
            suspects = {r["suspect_id"]: dict(r) for r in con.execute(
                "SELECT suspect_id, full_name, alias, address_zone, prior_count FROM suspects "
                "WHERE suspect_id IN (SELECT suspect_id FROM money_accounts WHERE suspect_id IS NOT NULL)")}
        finally:
            con.close()
        by_from, by_to = defaultdict(list), defaultdict(list)
        for t in txns:
            by_from[t["from_account"]].append(t)
            by_to[t["to_account"]].append(t)
        _snap = {"accounts": accounts, "txns": txns, "from": by_from, "to": by_to, "firs": firs, "suspects": suspects}
        _snap_at = time.time()
        return _snap


def _flags(account: str, kind: str, txin: list, txout: list, firs: list[dict]) -> list[dict]:
    out = []
    senders = {t["from_account"] for t in txin}
    if len(senders) >= FAN_IN_MIN:
        out.append({"key": "fan_in", "title": "Collects from many accounts",
                    "detail": f"Money came in from {len(senders)} different accounts."})
    tin, tout = sum(t["amount_inr"] for t in txin), sum(t["amount_inr"] for t in txout)
    if tin and kind != "complainant":
        # money that left within 48 hours of something arriving
        fast = sum(o["amount_inr"] for o in txout if any(0 <= _hours(t["ts"], o["ts"]) <= 48 for t in txin))
        share = min(fast, tin) / tin
        if share >= PASS_THROUGH:
            out.append({"key": "pass_through", "title": "Money passes straight through",
                        "detail": f"{round(100 * share)}% of what came in left again within 48 hours."})
    near = [t for t in txin + txout if NEAR_LIMIT[0] <= t["amount_inr"] <= NEAR_LIMIT[1]]
    if len(near) >= 2:
        out.append({"key": "near_limit", "title": "Amounts just under Rs 50,000",
                    "detail": f"{len(near)} transactions between Rs 45,000 and Rs 49,999."})
    districts = {f["district"] for f in firs if f["district"]}
    if len(firs) >= 2:
        out.append({"key": "many_firs", "title": "Named in several FIRs",
                    "detail": f"In {len(firs)} FIRs" + (f" across {len(districts)} districts." if len(districts) > 1 else ".")})
    cash = [t for t in txout if t["to_account"].startswith("CASH-")]
    if cash:
        out.append({"key": "cash_out", "title": "Cash taken out",
                    "detail": f"Rs {sum(t['amount_inr'] for t in cash):,} withdrawn in cash."})
    return out


def account(account_id: str, tx_limit: int | None = 60) -> dict | None:
    snap = _snapshot()
    a = snap["accounts"].get(account_id)
    if a is None:
        return None
    txin, txout = snap["to"].get(account_id, []), snap["from"].get(account_id, [])
    firs = snap["firs"].get(account_id, [])[:40] if a["kind"] == "upi" else []
    if a["kind"] == "complainant":
        firs = [{"fir_id": f} for f in sorted({t["fir_id"] for t in txout if t["fir_id"]})]
    suspect = None
    if a["suspect_id"]:
        suspect = snap["suspects"].get(a["suspect_id"]) or {"suspect_id": a["suspect_id"]}
    return {
        "account": dict(a), "suspect": suspect,
        "total_in": sum(t["amount_inr"] for t in txin), "total_out": sum(t["amount_inr"] for t in txout),
        "count_in": len(txin), "count_out": len(txout),
        "senders": len({t["from_account"] for t in txin}), "receivers": len({t["to_account"] for t in txout}),
        "first": min([t["ts"] for t in txin + txout], default=None),
        "last": max([t["ts"] for t in txin + txout], default=None),
        "flags": _flags(account_id, a["kind"], txin, txout, firs),
        "firs": firs,
        "transactions": sorted(txin + txout, key=lambda t: t["ts"], reverse=True)[:tx_limit],
    }


def trail(account_id: str, depth: int = 2, max_nodes: int = 70) -> dict | None:
    """Accounts within `depth` hops either way, with each pair's money summed into one edge."""
    snap = _snapshot()
    if account_id not in snap["accounts"]:
        return None
    seen, frontier, edges = {account_id: 0}, [account_id], {}
    for d in range(1, max(1, min(depth, 4)) + 1):
        nxt = []
        for acc in frontier:
            pairs = defaultdict(list)
            for t in snap["from"].get(acc, []) + snap["to"].get(acc, []):
                pairs[(t["from_account"], t["to_account"])].append(t)
            for key, ts in sorted(pairs.items(), key=lambda kv: -sum(t["amount_inr"] for t in kv[1]))[:40]:
                if key not in edges:
                    edges[key] = {"from": key[0], "to": key[1], "count": len(ts),
                                  "amount": sum(t["amount_inr"] for t in ts),
                                  "first": min(t["ts"] for t in ts), "last": max(t["ts"] for t in ts),
                                  "channels": sorted({t["channel"] for t in ts}),
                                  "purposes": sorted({t["purpose"] for t in ts}),
                                  "firs": sorted({t["fir_id"] for t in ts if t["fir_id"]})[:10]}
                for other in key:
                    if other not in seen and len(seen) < max_nodes:
                        seen[other] = d
                        nxt.append(other)
        frontier = nxt
    edges = {k: e for k, e in edges.items() if k[0] in seen and k[1] in seen}
    tot_in, tot_out = defaultdict(int), defaultdict(int)
    for e in edges.values():
        tot_out[e["from"]] += e["amount"]
        tot_in[e["to"]] += e["amount"]
    nodes = []
    for a in seen:
        v = snap["accounts"][a]
        nodes.append({"id": a, "kind": v["kind"], "label": v["label"], "district": v["district"], "hop": seen[a],
                      "in": tot_in[a], "out": tot_out[a], "firs": len(snap["firs"].get(a, [])),
                      "suspect_id": v["suspect_id"]})
    return {"root": account_id, "depth": depth, "nodes": nodes, "edges": list(edges.values()),
            "truncated": len(seen) >= max_nodes}


def overview(limit: int = 30) -> dict:
    """The accounts most worth a look: ranked by how many flags they trip, then money received."""
    snap = _snapshot()
    ranked = []
    for aid, a in snap["accounts"].items():
        if a["kind"] not in ("upi", "collector") or aid not in snap["to"]:
            continue
        d = account(aid)
        ranked.append({"account_id": aid, "kind": a["kind"], "label": a["label"], "district": a["district"],
                       "total_in": d["total_in"], "total_out": d["total_out"], "senders": d["senders"],
                       "firs": len(d["firs"]), "flags": [f["key"] for f in d["flags"]],
                       "flag_titles": [f["title"] for f in d["flags"]]})
    ranked.sort(key=lambda r: (-len(r["flags"]), -r["total_in"], r["account_id"]))
    kinds = defaultdict(int)
    for a in snap["accounts"].values():
        kinds[a["kind"]] += 1
    return {"transactions": len(snap["txns"]), "amount": sum(t["amount_inr"] for t in snap["txns"]),
            "firs": len({t["fir_id"] for t in snap["txns"] if t["fir_id"]}),
            "accounts": dict(kinds), "flagged": sum(1 for r in ranked if r["flags"]), "top": ranked[:limit]}


def search(q: str, limit: int = 12) -> list[dict]:
    """Accounts whose id or label contains the text, or that a FIR id or suspect id leads to."""
    snap = _snapshot()
    q = " ".join(str(q or "").split()).lower()
    if not q:
        return []
    found = []
    for aid, a in snap["accounts"].items():
        if q in aid.lower() or q in (a["label"] or "").lower() or q == (a["suspect_id"] or "").lower():
            found.append(aid)
    for u, fs in snap["firs"].items():
        if u in snap["accounts"] and any(f["fir_id"].lower() == q for f in fs):
            found.append(u)
    seen, res = set(), []
    for aid in found:
        if aid in seen:
            continue
        seen.add(aid)
        a = snap["accounts"][aid]
        res.append({"account_id": aid, "kind": a["kind"], "label": a["label"], "district": a["district"]})
    return res[:limit]


def for_person(suspect_id: str) -> dict:
    """The money trail around one person: accounts they hold (suspect accounts), and the UPI IDs
    on the FIRs that name them (crime_suspects), each with its totals and warning signs."""
    snap = _snapshot()
    sid = str(suspect_id or "").strip()
    held = [aid for aid, a in snap["accounts"].items() if (a["suspect_id"] or "") == sid]
    con = _con()
    try:
        upis = [r[0] for r in con.execute(
            "SELECT DISTINCT TRIM(f.UPI_ID) FROM crime_suspects cs JOIN FIRs f ON f.fir_id = cs.crime_id "
            "WHERE cs.suspect_id = ? AND COALESCE(f.UPI_ID, '') <> ''", (sid,))]
    finally:
        con.close()
    out = []
    for aid, how in [(a, "held") for a in held] + [(u, "on_fir") for u in upis if u not in held]:
        d = account(aid, 0)
        if not d:
            continue
        # who paid this person's accounts, and who they paid: the counterparties one step out
        counter = {t["from_account"] for t in snap["to"].get(aid, [])} | {t["to_account"] for t in snap["from"].get(aid, [])}
        out.append({"account_id": aid, "how": how, "kind": d["account"]["kind"], "label": d["account"]["label"],
                    "total_in": d["total_in"], "total_out": d["total_out"], "count_in": d["count_in"],
                    "count_out": d["count_out"], "counterparties": len(counter), "first": d["first"], "last": d["last"],
                    "flags": [f["title"] for f in d["flags"]], "firs": len(d["firs"])})
    out.sort(key=lambda a: -(a["total_in"] + a["total_out"]))
    return {"suspect_id": sid, "accounts": out,
            "total_in": sum(a["total_in"] for a in out), "total_out": sum(a["total_out"] for a in out)}
