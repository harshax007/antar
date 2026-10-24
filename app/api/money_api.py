"""
Antar - Money trail API
=======================
GET /api/money/overview               the accounts most worth a look, with the rules they trip
GET /api/money/search?q=              accounts by id, label, FIR id or suspect id
GET /api/money/trail?account=&depth=  accounts within N hops, money summed per pair
GET /api/money/account/{id}           one account: totals, flags, FIRs, transactions

Names suspects and follows money between people, so Inspector and above (mounted with that
dependency in main.py).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query

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
