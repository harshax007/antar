"""
Antar - Money trail API
=======================
GET /api/funds/overview               the accounts most worth a look, with the rules they trip
GET /api/funds/search?q=              accounts by id, label, FIR id or suspect id
GET /api/funds/trail?account=&depth=  accounts within N hops, money summed per pair
GET /api/funds/account/{id}           one account: totals, flags, FIRs, transactions
GET /api/funds/person/{suspect_id}    the accounts a person holds, and the UPI IDs on FIRs naming them
GET /api/funds/export?account=        one account's transactions as CSV, for a bank or
                                      financial-intelligence request (every export is on the audit log)

Names suspects and follows money between people, so Inspector and above (mounted with that
dependency in main.py).
"""
from __future__ import annotations

import asyncio
import csv
import io
import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services import money_trail

router = APIRouter()


def _ready() -> None:
    if not money_trail.available():
        raise HTTPException(status_code=503, detail="The money trail has not been built yet: run scripts/seed_money_trail.py.")


@router.get("/overview")
async def overview(limit: int = Query(30, ge=1, le=100)) -> dict:
    _ready()
    return await asyncio.to_thread(money_trail.overview, limit)


@router.get("/search")
async def search(q: str = Query(..., min_length=2, max_length=80)) -> dict:
    _ready()
    return {"results": await asyncio.to_thread(money_trail.search, q)}


@router.get("/trail")
async def trail(account: str = Query(..., min_length=2, max_length=80), depth: int = Query(2, ge=1, le=4)) -> dict:
    _ready()
    t = await asyncio.to_thread(money_trail.trail, account.strip(), depth)
    if t is None:
        raise HTTPException(status_code=404, detail=f"No account {account} in the money trail.")
    return t


@router.get("/account/{account_id:path}")
async def account(account_id: str) -> dict:
    _ready()
    a = await asyncio.to_thread(money_trail.account, account_id.strip())
    if a is None:
        raise HTTPException(status_code=404, detail=f"No account {account_id} in the money trail.")
    return a


@router.get("/export")
async def export(account: str = Query(..., min_length=2, max_length=80)) -> Response:
    _ready()
    a = await asyncio.to_thread(money_trail.account, account.strip(), None)
    if a is None:
        raise HTTPException(status_code=404, detail=f"No account {account} in the money trail.")
    acc = a["account"]["account_id"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["account", acc, "kind", a["account"]["kind"], "district", a["account"]["district"] or ""])
    w.writerow(["money_in_inr", a["total_in"], "money_out_inr", a["total_out"],
                "warning_signs", "; ".join(f["title"] for f in a["flags"])])
    w.writerow(["firs", " ".join(f["fir_id"] for f in a["firs"])])
    w.writerow([])
    w.writerow(["txn_id", "date_time", "direction", "counterparty", "amount_inr", "channel", "purpose", "fir_id"])
    for t in sorted(a["transactions"], key=lambda t: t["ts"]):
        inbound = t["to_account"] == acc
        w.writerow([t["txn_id"], t["ts"], "in" if inbound else "out", t["from_account"] if inbound else t["to_account"],
                    t["amount_inr"], t["channel"], t["purpose"], t["fir_id"] or ""])
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", acc)
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="money-trail-{name}.csv"'})


@router.get("/person/{suspect_id}")
async def person(suspect_id: str) -> dict:
    _ready()
    return await asyncio.to_thread(money_trail.for_person, suspect_id)
